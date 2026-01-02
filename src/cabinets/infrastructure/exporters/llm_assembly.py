"""LLM-based assembly instruction exporter.

This module provides an exporter that generates assembly instructions
using LLM inference via pydantic-ai and Ollama.

Classes:
    LLMAssemblyExporter: Exporter for LLM-generated assembly instructions
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal

from cabinets.infrastructure.exporters.base import ExporterRegistry
from cabinets.infrastructure.llm.generator import LLMAssemblyGenerator

if TYPE_CHECKING:
    from cabinets.application.config.schemas import AssemblyOutputConfigSchema
    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput


logger = logging.getLogger(__name__)


@ExporterRegistry.register("llm-assembly")
class LLMAssemblyExporter:
    """Exporter for LLM-generated assembly instructions.

    Uses pydantic-ai with Ollama to generate skill-level-appropriate
    assembly instructions. Automatically falls back to template-based
    instructions when LLM is unavailable.

    Attributes:
        format_name: "llm-assembly"
        file_extension: "md"

    Example:
        >>> exporter = LLMAssemblyExporter(skill_level="beginner")
        >>> exporter.export(output, Path("assembly.md"))

        Or via ExporterRegistry:
        >>> exporter_class = ExporterRegistry.get("llm-assembly")
        >>> exporter = exporter_class()
        >>> exporter.export(output, Path("assembly.md"))
    """

    format_name: ClassVar[str] = "llm-assembly"
    file_extension: ClassVar[str] = "md"

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: float = 30.0,
        skill_level: Literal["beginner", "intermediate", "expert"] = "intermediate",
        include_troubleshooting: bool = True,
        include_time_estimates: bool = True,
    ) -> None:
        """Initialize the LLM assembly exporter.

        Args:
            ollama_url: Ollama server URL.
            model: Ollama model name.
            timeout: Generation timeout in seconds.
            skill_level: Target skill level for instructions.
            include_troubleshooting: Include troubleshooting section.
            include_time_estimates: Include time estimates per step.
        """
        self.generator = LLMAssemblyGenerator(
            ollama_url=ollama_url,
            model=model,
            timeout=timeout,
            skill_level=skill_level,
            include_troubleshooting=include_troubleshooting,
            include_time_estimates=include_time_estimates,
        )

    def export(self, output: "LayoutOutput | RoomLayoutOutput", path: Path) -> None:
        """Export LLM-generated assembly instructions to file.

        Args:
            output: Layout output containing cabinet and cut list.
            path: Path where the markdown file will be saved.

        Note:
            Falls back to template-based instructions if LLM unavailable.
        """
        content = self.export_string(output)
        path.write_text(content)
        logger.info(f"Exported LLM assembly instructions to {path}")

    def export_string(self, output: "LayoutOutput | RoomLayoutOutput") -> str:
        """Generate assembly instructions as string.

        Args:
            output: Layout output containing cabinet and cut list.

        Returns:
            Markdown-formatted assembly instructions.

        Note:
            Falls back to template-based instructions if LLM unavailable.
        """
        return self.generator.generate_sync(output)

    def format_for_console(self, output: "LayoutOutput | RoomLayoutOutput") -> str:
        """Format LLM assembly instructions for console display.

        The markdown format is already suitable for terminal display,
        so this delegates directly to export_string().

        Args:
            output: Layout output containing cabinet and cut list.

        Returns:
            Markdown-formatted assembly instructions.

        Note:
            Falls back to template-based instructions if LLM unavailable.
        """
        return self.export_string(output)

    @classmethod
    def from_config(
        cls,
        config: "AssemblyOutputConfigSchema | None",
    ) -> "LLMAssemblyExporter":
        """Create exporter from configuration schema.

        Factory method for creating an exporter with settings from
        the configuration file.

        Args:
            config: Assembly output configuration, or None for defaults.

        Returns:
            Configured LLMAssemblyExporter instance.
        """
        if config is None:
            return cls()

        return cls(
            ollama_url=config.ollama_url,
            model=config.llm_model,
            timeout=float(config.timeout_seconds),
            skill_level=config.skill_level,
            include_troubleshooting=config.include_troubleshooting,
            include_time_estimates=config.include_time_estimates,
        )


__all__ = ["LLMAssemblyExporter"]
