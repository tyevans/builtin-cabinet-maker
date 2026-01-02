"""LLM-enhanced assembly instruction generator with fallback.

This module provides the main generator class that orchestrates
LLM-based instruction generation with automatic fallback to
template-based instructions when the LLM is unavailable.

Classes:
    LLMAssemblyGenerator: Main generator with fallback support
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import ValidationError

from cabinets.domain.value_objects import PanelType
from cabinets.infrastructure.exporters.assembly import AssemblyInstructionGenerator
from cabinets.infrastructure.llm.assembly_agent import run_assembly_agent
from cabinets.infrastructure.llm.models import (
    AssemblyDeps,
    AssemblyInstructions,
    WarningSeverity,
)
from cabinets.infrastructure.llm.ollama_client import OllamaHealthCheck

if TYPE_CHECKING:
    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput

logger = logging.getLogger(__name__)


class LLMAssemblyGenerator:
    """LLM-enhanced assembly instruction generator with fallback.

    Generates assembly instructions using an LLM via pydantic-ai and Ollama.
    Automatically falls back to template-based instructions when:
    - Ollama server is unavailable
    - LLM generation times out
    - LLM output fails schema validation

    Attributes:
        ollama_url: Ollama server URL
        model: Ollama model identifier
        timeout: Generation timeout in seconds
        skill_level: Target skill level for instructions
        include_troubleshooting: Whether to include troubleshooting section
        include_time_estimates: Whether to include time estimates

    Example:
        >>> generator = LLMAssemblyGenerator(skill_level="beginner")
        >>> content = await generator.generate(output)
        >>> print(content)  # Markdown assembly instructions
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 30.0,
        skill_level: Literal["beginner", "intermediate", "expert"] = "intermediate",
        include_troubleshooting: bool = True,
        include_time_estimates: bool = True,
    ) -> None:
        """Initialize the LLM assembly generator.

        Args:
            ollama_url: Ollama server URL (default: localhost:11434).
            model: Ollama model name without prefix (default: llama3.2).
            timeout: Generation timeout in seconds (default: 30).
            skill_level: Target skill level (default: intermediate).
            include_troubleshooting: Include troubleshooting tips (default: True).
            include_time_estimates: Include time estimates (default: True).
        """
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        self.skill_level = skill_level
        self.include_troubleshooting = include_troubleshooting
        self.include_time_estimates = include_time_estimates
        self.health_check = OllamaHealthCheck(ollama_url)
        self.fallback = AssemblyInstructionGenerator()

    async def generate(self, output: "LayoutOutput | RoomLayoutOutput") -> str:
        """Generate assembly instructions, with automatic fallback.

        Attempts to generate LLM-enhanced instructions. Falls back to
        template-based instructions on any failure.

        Args:
            output: Layout output containing cabinet and cut list.

        Returns:
            Markdown-formatted assembly instructions.
        """
        # Check Ollama availability first
        if not await self.health_check.is_available():
            logger.info("Ollama unavailable, using template fallback")
            return self._fallback_generate(output, reason="Ollama server not available")

        # Check model availability
        if not await self.health_check.has_model(self.model):
            logger.warning(
                f"Model '{self.model}' not found. Run: ollama pull {self.model}"
            )
            return self._fallback_generate(
                output, reason=f"Model '{self.model}' not available"
            )

        # Attempt LLM generation with timeout
        try:
            deps = self._build_deps(output)

            result = await asyncio.wait_for(
                run_assembly_agent(
                    deps=deps,
                    model=f"ollama:{self.model}",
                    ollama_url=self.ollama_url,
                ),
                timeout=self.timeout,
            )

            logger.info(
                f"LLM generated {len(result.steps)} steps "
                f"for skill_level={self.skill_level}"
            )
            return self._format_markdown(result)

        except asyncio.TimeoutError:
            logger.warning(f"LLM generation timed out after {self.timeout}s")
            return self._fallback_generate(
                output, reason=f"Generation timed out after {self.timeout}s"
            )

        except ValidationError as e:
            logger.warning(f"LLM output validation failed: {e.error_count()} errors")
            # One retry attempt
            try:
                logger.info("Retrying LLM generation...")
                result = await asyncio.wait_for(
                    run_assembly_agent(
                        deps=self._build_deps(output),
                        model=f"ollama:{self.model}",
                        ollama_url=self.ollama_url,
                    ),
                    timeout=self.timeout,
                )
                return self._format_markdown(result)
            except Exception as retry_error:
                logger.warning(f"Retry failed: {retry_error}")
                return self._fallback_generate(
                    output, reason="LLM output validation failed after retry"
                )

        except Exception as e:
            logger.error(f"Unexpected error during LLM generation: {e}")
            return self._fallback_generate(
                output, reason=f"Unexpected error: {type(e).__name__}"
            )

    def generate_sync(self, output: "LayoutOutput | RoomLayoutOutput") -> str:
        """Synchronous wrapper for generate().

        Args:
            output: Layout output containing cabinet and cut list.

        Returns:
            Markdown-formatted assembly instructions.
        """
        return asyncio.run(self.generate(output))

    def _build_deps(self, output: "LayoutOutput | RoomLayoutOutput") -> AssemblyDeps:
        """Build agent dependencies from layout output.

        Args:
            output: Layout output to extract data from.

        Returns:
            AssemblyDeps configured for the cabinet.
        """
        from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput
        from cabinets.domain.services.woodworking import WoodworkingIntelligence

        # Extract cabinet and cut list
        if isinstance(output, RoomLayoutOutput):
            cabinet = output.cabinets[0] if output.cabinets else None
            cut_list = output.cut_list
        elif isinstance(output, LayoutOutput):
            cabinet = output.cabinet
            cut_list = output.cut_list
        else:
            raise ValueError(f"Unsupported output type: {type(output)}")

        if cabinet is None:
            raise ValueError("No cabinet found in output")

        # Get joinery information
        joinery = []
        try:
            intel = WoodworkingIntelligence()
            joinery = intel.get_joinery(cabinet)
        except Exception as e:
            logger.debug(f"Could not get joinery: {e}")

        # Detect component types
        has_doors = any(piece.panel_type == PanelType.DOOR for piece in cut_list)
        has_drawers = any(
            piece.panel_type
            in (
                PanelType.DRAWER_FRONT,
                PanelType.DRAWER_SIDE,
                PanelType.DRAWER_BOX_FRONT,
                PanelType.DRAWER_BOTTOM,
            )
            for piece in cut_list
        )
        has_decorative = any(
            hasattr(piece.panel_type, "value")
            and "face_frame" in piece.panel_type.value.lower()
            for piece in cut_list
        )

        return AssemblyDeps(
            cabinet=cabinet,
            cut_list=cut_list,
            joinery=joinery,
            skill_level=self.skill_level,
            material_type=cabinet.material.material_type,
            has_doors=has_doors,
            has_drawers=has_drawers,
            has_decorative_elements=has_decorative,
        )

    def _fallback_generate(
        self,
        output: "LayoutOutput | RoomLayoutOutput",
        reason: str = "LLM unavailable",
    ) -> str:
        """Generate using template-based fallback.

        Args:
            output: Layout output to generate from.
            reason: Reason for fallback (for header comment).

        Returns:
            Markdown content with fallback indicator.
        """
        content = self.fallback.export_string(output)
        header = (
            f"<!-- Generated using template fallback -->\n"
            f"<!-- Reason: {reason} -->\n"
            f"<!-- Tip: Install Ollama (ollama.com) and run 'ollama pull {self.model}' "
            f"for AI-enhanced instructions -->\n\n"
        )
        return header + content

    def _format_markdown(self, instructions: AssemblyInstructions) -> str:
        """Format AssemblyInstructions as markdown.

        Args:
            instructions: Structured instructions from LLM.

        Returns:
            Markdown-formatted string.
        """
        lines: list[str] = []

        # Header
        lines.append(f"# {instructions.title}")
        lines.append("")
        lines.append(f"**Skill Level:** {instructions.skill_level.title()}")
        lines.append(f"**Estimated Time:** {instructions.estimated_time}")
        lines.append(
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} via AI-assisted generation*"
        )
        lines.append("")

        # Cabinet Summary
        lines.append("## Overview")
        lines.append("")
        lines.append(instructions.cabinet_summary)
        lines.append("")

        # Safety Warnings
        if instructions.safety_warnings:
            lines.append("---")
            lines.append("")
            lines.append("## Safety First")
            lines.append("")

            # Group by severity
            for severity in [
                WarningSeverity.DANGER,
                WarningSeverity.WARNING,
                WarningSeverity.CAUTION,
                WarningSeverity.INFO,
            ]:
                severity_warnings = [
                    w for w in instructions.safety_warnings if w.severity == severity
                ]
                if severity_warnings:
                    for warning in severity_warnings:
                        emoji = {
                            WarningSeverity.DANGER: "**DANGER:**",
                            WarningSeverity.WARNING: "**WARNING:**",
                            WarningSeverity.CAUTION: "**CAUTION:**",
                            WarningSeverity.INFO: "**Note:**",
                        }.get(severity, ">")
                        lines.append(f"> {emoji} {warning.message}")
                        lines.append(f"> - *When:* {warning.context}")
                        lines.append(f"> - *Mitigation:* {warning.mitigation}")
                        lines.append("")
            lines.append("")

        # Tools Needed
        if instructions.tools_needed:
            lines.append("---")
            lines.append("")
            lines.append("## Tools Needed")
            lines.append("")

            required = [t for t in instructions.tools_needed if t.required]
            optional = [t for t in instructions.tools_needed if not t.required]

            if required:
                lines.append("### Required")
                lines.append("")
                for tool in required:
                    lines.append(f"- [ ] **{tool.tool}**")
                    lines.append(f"  - *Purpose:* {tool.purpose}")
                    if tool.alternatives:
                        lines.append(
                            f"  - *Alternatives:* {', '.join(tool.alternatives)}"
                        )
                lines.append("")

            if optional:
                lines.append("### Optional")
                lines.append("")
                for tool in optional:
                    lines.append(f"- [ ] {tool.tool}")
                    lines.append(f"  - *Purpose:* {tool.purpose}")
                lines.append("")

        # Materials Checklist
        if instructions.materials_checklist:
            lines.append("---")
            lines.append("")
            lines.append("## Materials Checklist")
            lines.append("")
            for material in instructions.materials_checklist:
                lines.append(f"- [ ] {material}")
            lines.append("")

        # Assembly Steps
        lines.append("---")
        lines.append("")
        lines.append("## Assembly Steps")
        lines.append("")

        current_phase = ""
        for step in instructions.steps:
            # Phase header if changed
            if step.phase != current_phase:
                current_phase = step.phase
                lines.append(f"### {current_phase}")
                lines.append("")

            # Step header with optional metadata
            step_meta = []
            if self.include_time_estimates and step.time_estimate:
                step_meta.append(f"Time: {step.time_estimate}")
            if step.difficulty:
                step_meta.append(f"Difficulty: {step.difficulty.title()}")

            step_header = f"#### Step {step.step_number}: {step.title}"
            if step_meta:
                step_header += f" ({' | '.join(step_meta)})"
            lines.append(step_header)
            lines.append("")

            # Pieces involved
            if step.pieces_involved:
                lines.append("**Pieces:**")
                for piece in step.pieces_involved:
                    lines.append(f"- {piece}")
                lines.append("")

            # Instructions
            lines.append("**Instructions:**")
            lines.append(step.description)
            lines.append("")

            # Joinery details
            if step.joinery_details:
                lines.append("**Joinery:**")
                lines.append(step.joinery_details)
                lines.append("")

            # Quality check
            if step.quality_check:
                lines.append("**Quality Check:**")
                lines.append(f"- {step.quality_check}")
                lines.append("")

            # Common mistakes
            if step.common_mistakes:
                lines.append("**Common Mistakes to Avoid:**")
                for mistake in step.common_mistakes:
                    lines.append(f"- {mistake}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Troubleshooting
        if self.include_troubleshooting and instructions.troubleshooting:
            lines.append("## Troubleshooting")
            lines.append("")
            for tip in instructions.troubleshooting:
                lines.append(f"### {tip.issue}")
                lines.append("")
                lines.append(f"**Likely Cause:** {tip.cause}")
                lines.append("")
                lines.append(f"**Solution:** {tip.solution}")
                if tip.prevention:
                    lines.append("")
                    lines.append(f"**Prevention:** {tip.prevention}")
                lines.append("")

        # Finishing Notes
        lines.append("## Finishing")
        lines.append("")
        lines.append(instructions.finishing_notes)
        lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(
            "*Assembly instructions generated by Cabinet Layout Generator with AI assistance*"
        )
        lines.append("")

        return "\n".join(lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = ["LLMAssemblyGenerator"]
