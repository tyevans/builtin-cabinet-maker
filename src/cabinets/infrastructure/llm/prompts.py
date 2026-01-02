"""System prompts and skill-level templates for assembly generation.

This module contains the prompt engineering for LLM-based assembly
instruction generation, including skill-level-specific adaptations.

The prompt strategy uses a layered approach:
1. Base system prompt - Core woodworking knowledge and assembly principles
2. Skill level layer - Vocabulary, detail level, explanation depth adjustments
3. Context injection - Cabinet-specific details (dimensions, materials, joinery)
4. Output schema - JSON schema derived from Pydantic models (handled by pydantic-ai)

Constants:
    ASSEMBLY_SYSTEM_PROMPT: Base system prompt for cabinet assembly
    BEGINNER_PROMPT_ADDITIONS: Additions for beginner skill level
    INTERMEDIATE_PROMPT_ADDITIONS: Additions for intermediate skill level
    EXPERT_PROMPT_ADDITIONS: Additions for expert skill level
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet
    from cabinets.domain.services.woodworking import ConnectionJoinery
    from cabinets.domain.value_objects import CutPiece


# =============================================================================
# Base System Prompt
# =============================================================================

ASSEMBLY_SYSTEM_PROMPT = """You are an expert cabinet maker generating assembly instructions for a custom cabinet project.

## Your Role
You are a professional woodworker with decades of experience building custom cabinets. Your goal is to help the user successfully assemble their cabinet by providing clear, practical instructions.

## Assembly Philosophy
- Safety first: Always prioritize safe working practices
- Measure twice, cut once: Emphasize verification at each step
- Proper sequence: Follow the established build order for structural integrity
- Quality checkpoints: Include verification steps to catch errors early

## Standard Build Order
Follow this assembly sequence for structural integrity:
1. **Carcase Preparation** - Prepare side panels, mark dado/rabbet locations
2. **Horizontal Panel Assembly** - Attach top and bottom to sides
3. **Back Panel Installation** - Attach back panel to square the cabinet
4. **Divider Installation** - Install any vertical or horizontal dividers
5. **Fixed Shelf Installation** - Install permanently mounted shelves
6. **Adjustable Shelf Preparation** - Drill shelf pin holes, prepare adjustable shelves
7. **Door Installation** - Mount doors with hinges (if applicable)
8. **Drawer Installation** - Install drawer slides and drawers (if applicable)

## Output Requirements
Generate comprehensive assembly instructions that include:
- Context-aware safety warnings based on actual tools and materials
- Tool recommendations with alternatives where possible
- Step-by-step instructions with specific dimensions
- Quality checkpoints after critical steps
- Common mistakes to avoid
- Troubleshooting tips for likely issues

Always reference the specific dimensions and materials provided in the cabinet specifications."""


# =============================================================================
# Skill Level Prompt Additions
# =============================================================================

BEGINNER_PROMPT_ADDITIONS = """
## Skill Level: BEGINNER

Adjust your instructions for someone new to woodworking:

### Communication Style
- Use simple, everyday language
- Define woodworking terms the first time they appear (e.g., "A dado is a groove cut across the grain that allows another piece to fit into it")
- Explain WHY each step is important, not just what to do
- Be encouraging and reassuring

### Detail Level
- Break complex steps into smaller sub-steps
- Include time estimates for each step (e.g., "This step typically takes 15-20 minutes")
- Add difficulty ratings for each step (easy, moderate, challenging)
- Describe what success looks like at each stage

### Safety Emphasis
- Include detailed safety warnings for every power tool operation
- Explain proper body positioning and technique
- Recommend starting with practice cuts on scrap material
- Emphasize hearing and eye protection

### Additional Guidance
- Include tips for measuring accurately
- Suggest having a helper for handling large panels
- Explain how to recover from common mistakes
- Reference visual inspection criteria (e.g., "The joint should feel snug with no visible gaps")

### Tool Alternatives
- Always suggest hand tool alternatives where feasible
- Recommend jigs and guides that improve accuracy
- Note when professional help might be warranted"""


INTERMEDIATE_PROMPT_ADDITIONS = """
## Skill Level: INTERMEDIATE

Adjust your instructions for a hobbyist woodworker with some experience:

### Communication Style
- Use standard woodworking terminology without extensive definitions
- Focus on the "why" behind critical decisions
- Include efficiency tips and pro techniques
- Balance detail with conciseness

### Detail Level
- Group related steps logically
- Include quality verification at key milestones
- Note where precision is critical vs. where there's tolerance
- Mention time-saving techniques

### Safety Emphasis
- Include safety reminders for high-risk operations
- Assume familiarity with basic power tool safety
- Emphasize material-specific hazards (e.g., MDF dust)

### Additional Guidance
- Suggest workflow optimizations
- Include tips for batch processing similar operations
- Note where clamps or jigs improve results
- Mention setup steps that save time later

### Tool Recommendations
- Recommend the right tool for each job
- Note where specialized tools significantly improve results
- Include typical settings (e.g., router speed, blade height)"""


EXPERT_PROMPT_ADDITIONS = """
## Skill Level: EXPERT

Adjust your instructions for an experienced woodworker or professional:

### Communication Style
- Be concise and technical
- Assume familiarity with all standard joinery methods
- Focus on specifications and sequence
- Skip basic explanations

### Detail Level
- Provide dimensions and tolerances directly
- Group steps by phase without excessive narrative
- Include CNC-ready specifications where applicable
- Note critical dimensions requiring verification

### Safety Emphasis
- Include only critical hazard warnings
- Never omit DANGER-level warnings regardless of experience
- Focus on project-specific hazards

### Additional Guidance
- Support batch processing workflow
- Note optimal tool settings and speeds
- Include efficiency-focused sequences
- Reference industry standards where applicable

### Format Preference
- Use tables and lists over prose where appropriate
- Include all measurements in a scannable format
- Minimize redundant information"""


# =============================================================================
# Context Building Functions
# =============================================================================


def get_skill_prompt(skill_level: Literal["beginner", "intermediate", "expert"]) -> str:
    """Get skill-level-specific prompt additions.

    Args:
        skill_level: Target skill level for instructions.

    Returns:
        Prompt additions appropriate for the skill level.
    """
    prompts = {
        "beginner": BEGINNER_PROMPT_ADDITIONS,
        "intermediate": INTERMEDIATE_PROMPT_ADDITIONS,
        "expert": EXPERT_PROMPT_ADDITIONS,
    }
    return prompts.get(skill_level, INTERMEDIATE_PROMPT_ADDITIONS)


def build_context_prompt(
    cabinet: "Cabinet",
    cut_list: list["CutPiece"],
    joinery: list["ConnectionJoinery"],
    has_doors: bool = False,
    has_drawers: bool = False,
    has_decorative: bool = False,
) -> str:
    """Build cabinet-specific context for the LLM prompt.

    Generates a detailed description of the cabinet being built,
    including all dimensions, materials, and components.

    Args:
        cabinet: The cabinet entity to describe.
        cut_list: List of cut pieces for the cabinet.
        joinery: List of joinery connections.
        has_doors: Whether the cabinet has doors.
        has_drawers: Whether the cabinet has drawers.
        has_decorative: Whether the cabinet has decorative elements.

    Returns:
        Formatted context string for injection into the prompt.
    """
    # Basic dimensions
    context_parts = [
        "## Cabinet Specifications",
        "",
        f'**Dimensions:** {cabinet.width:.2f}"W x {cabinet.height:.2f}"H x {cabinet.depth:.2f}"D',
        f'**Material:** {cabinet.material.material_type.value} at {cabinet.material.thickness}" thickness',
        f"**Number of Sections:** {len(cabinet.sections)}",
    ]

    # Section details
    if cabinet.sections:
        context_parts.append("")
        context_parts.append("### Sections")
        for i, section in enumerate(cabinet.sections, 1):
            section_type = getattr(section, "section_type", "open")
            if hasattr(section_type, "value"):
                section_type = section_type.value
            context_parts.append(
                f'- Section {i}: {section.width:.2f}"W, '
                f"type: {section_type}, "
                f"shelves: {len(section.shelves) if hasattr(section, 'shelves') else 0}"
            )

    # Component flags
    components = []
    if has_doors:
        components.append("doors")
    if has_drawers:
        components.append("drawers")
    if has_decorative:
        components.append("decorative elements (face frame, crown molding, etc.)")

    if components:
        context_parts.append("")
        context_parts.append(f"**Components:** {', '.join(components)}")

    # Cut list summary
    if cut_list:
        context_parts.append("")
        context_parts.append("### Cut List Summary")
        context_parts.append(f"**Total Pieces:** {sum(p.quantity for p in cut_list)}")
        context_parts.append("")

        # Group by panel type
        by_type: dict[str, list[CutPiece]] = {}
        for piece in cut_list:
            type_name = (
                piece.panel_type.value
                if hasattr(piece.panel_type, "value")
                else str(piece.panel_type)
            )
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(piece)

        for type_name, pieces in sorted(by_type.items()):
            context_parts.append(f"**{type_name.replace('_', ' ').title()}:**")
            for piece in pieces:
                context_parts.append(
                    f"  - {piece.label} ({piece.quantity}x): "
                    f'{piece.width:.3f}" x {piece.height:.3f}"'
                )

    # Joinery summary
    if joinery:
        context_parts.append("")
        context_parts.append("### Joinery Connections")

        joint_types = set()
        for joint in joinery:
            joint_type = joint.joint.joint_type
            if hasattr(joint_type, "value"):
                joint_types.add(joint_type.value)
            else:
                joint_types.add(str(joint_type))

        context_parts.append(
            f"**Joinery Methods Used:** {', '.join(sorted(joint_types))}"
        )
        context_parts.append("")

        for joint in joinery:
            from_panel = joint.from_panel
            to_panel = joint.to_panel
            joint_type = joint.joint.joint_type

            # Get string values (handles both enum and string types)
            from_panel_str: str = (
                from_panel.value if hasattr(from_panel, "value") else str(from_panel)
            )
            to_panel_str: str = (
                to_panel.value if hasattr(to_panel, "value") else str(to_panel)
            )
            joint_type_str: str = (
                joint_type.value if hasattr(joint_type, "value") else str(joint_type)
            )

            context_parts.append(
                f"- {from_panel_str.replace('_', ' ').title()} to "
                f"{to_panel_str.replace('_', ' ').title()}: {joint_type_str}"
            )

    return "\n".join(context_parts)


def build_user_prompt(
    cabinet: "Cabinet",
    cut_list: list["CutPiece"],
    joinery: list["ConnectionJoinery"],
    skill_level: Literal["beginner", "intermediate", "expert"],
    has_doors: bool = False,
    has_drawers: bool = False,
    has_decorative: bool = False,
) -> str:
    """Build the complete user prompt for assembly instruction generation.

    Combines cabinet context with skill-level-specific instructions
    to create the final prompt sent to the LLM.

    Args:
        cabinet: The cabinet entity.
        cut_list: List of cut pieces.
        joinery: List of joinery connections.
        skill_level: Target skill level.
        has_doors: Whether cabinet has doors.
        has_drawers: Whether cabinet has drawers.
        has_decorative: Whether cabinet has decorative elements.

    Returns:
        Complete user prompt string.
    """
    context = build_context_prompt(
        cabinet=cabinet,
        cut_list=cut_list,
        joinery=joinery,
        has_doors=has_doors,
        has_drawers=has_drawers,
        has_decorative=has_decorative,
    )

    title = f'{cabinet.width:.0f}"W x {cabinet.height:.0f}"H x {cabinet.depth:.0f}"D Cabinet'

    prompt = f"""Generate complete assembly instructions for the following cabinet:

{context}

## Instructions Request

Please generate comprehensive assembly instructions for this {title}.

Target skill level: **{skill_level.upper()}**

Include:
1. Safety warnings specific to the tools and materials used
2. Complete tool list with alternatives where possible
3. Materials checklist referencing specific cut pieces
4. Step-by-step assembly instructions following the standard build order
5. Quality checkpoints after critical steps
6. Common mistakes to avoid
7. Troubleshooting tips for likely issues
8. Finishing notes

Make all instructions specific to this cabinet's dimensions and specifications."""

    return prompt


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ASSEMBLY_SYSTEM_PROMPT",
    "BEGINNER_PROMPT_ADDITIONS",
    "INTERMEDIATE_PROMPT_ADDITIONS",
    "EXPERT_PROMPT_ADDITIONS",
    "get_skill_prompt",
    "build_context_prompt",
    "build_user_prompt",
]
