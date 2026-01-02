"""Unit tests for LLM prompt templates.

Tests cover:
- System prompt constants (ASSEMBLY_SYSTEM_PROMPT)
- Skill level prompt additions (BEGINNER, INTERMEDIATE, EXPERT)
- get_skill_prompt() function
- build_context_prompt() function
- build_user_prompt() function
"""

from __future__ import annotations

import pytest

from cabinets.domain.entities import Cabinet, Section, Shelf
from cabinets.domain.value_objects import (
    CutPiece,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from cabinets.infrastructure.llm import (
    ASSEMBLY_SYSTEM_PROMPT,
    BEGINNER_PROMPT_ADDITIONS,
    EXPERT_PROMPT_ADDITIONS,
    INTERMEDIATE_PROMPT_ADDITIONS,
    build_context_prompt,
    build_user_prompt,
    get_skill_prompt,
)


# =============================================================================
# Test Class: System Prompts Constants
# =============================================================================


class TestSystemPrompts:
    """Tests for system prompt constants."""

    def test_base_prompt_contains_cabinet_maker(self) -> None:
        """Base prompt mentions cabinet maker role."""
        assert "cabinet maker" in ASSEMBLY_SYSTEM_PROMPT.lower()

    def test_base_prompt_contains_build_order(self) -> None:
        """Base prompt mentions build order sequence."""
        assert "build order" in ASSEMBLY_SYSTEM_PROMPT.lower()

    def test_base_prompt_contains_safety(self) -> None:
        """Base prompt emphasizes safety."""
        assert "safety" in ASSEMBLY_SYSTEM_PROMPT.lower()

    def test_base_prompt_contains_assembly_phases(self) -> None:
        """Base prompt includes assembly phases."""
        assert "Carcase" in ASSEMBLY_SYSTEM_PROMPT
        assert "Back Panel" in ASSEMBLY_SYSTEM_PROMPT

    def test_base_prompt_contains_output_requirements(self) -> None:
        """Base prompt specifies output requirements."""
        assert "Output Requirements" in ASSEMBLY_SYSTEM_PROMPT

    def test_beginner_prompt_has_beginner_label(self) -> None:
        """Beginner prompt has appropriate header."""
        assert "BEGINNER" in BEGINNER_PROMPT_ADDITIONS

    def test_beginner_prompt_defines_terms(self) -> None:
        """Beginner prompt asks for term definitions."""
        assert "define" in BEGINNER_PROMPT_ADDITIONS.lower()

    def test_beginner_prompt_emphasizes_explanation(self) -> None:
        """Beginner prompt emphasizes explanation."""
        assert "explain" in BEGINNER_PROMPT_ADDITIONS.lower()

    def test_beginner_prompt_has_safety_emphasis(self) -> None:
        """Beginner prompt has safety emphasis section."""
        assert "Safety Emphasis" in BEGINNER_PROMPT_ADDITIONS

    def test_intermediate_prompt_has_intermediate_label(self) -> None:
        """Intermediate prompt has appropriate header."""
        assert "INTERMEDIATE" in INTERMEDIATE_PROMPT_ADDITIONS

    def test_intermediate_prompt_mentions_efficiency(self) -> None:
        """Intermediate prompt mentions efficiency."""
        assert "efficiency" in INTERMEDIATE_PROMPT_ADDITIONS.lower()

    def test_intermediate_prompt_assumes_familiarity(self) -> None:
        """Intermediate prompt assumes some familiarity."""
        assert "familiarity" in INTERMEDIATE_PROMPT_ADDITIONS.lower()

    def test_expert_prompt_has_expert_label(self) -> None:
        """Expert prompt has appropriate header."""
        assert "EXPERT" in EXPERT_PROMPT_ADDITIONS

    def test_expert_prompt_is_concise(self) -> None:
        """Expert prompt emphasizes conciseness."""
        assert "concise" in EXPERT_PROMPT_ADDITIONS.lower()

    def test_expert_prompt_assumes_expertise(self) -> None:
        """Expert prompt assumes expertise."""
        assert "experienced" in EXPERT_PROMPT_ADDITIONS.lower()

    def test_prompt_length_ordering(self) -> None:
        """Beginner prompt is longest, expert is shortest."""
        assert len(BEGINNER_PROMPT_ADDITIONS) > len(INTERMEDIATE_PROMPT_ADDITIONS)
        assert len(INTERMEDIATE_PROMPT_ADDITIONS) > len(EXPERT_PROMPT_ADDITIONS)


# =============================================================================
# Test Class: get_skill_prompt Function
# =============================================================================


class TestGetSkillPrompt:
    """Tests for get_skill_prompt function."""

    def test_beginner_returns_correct_prompt(self) -> None:
        """Returns beginner prompt for 'beginner'."""
        prompt = get_skill_prompt("beginner")
        assert "BEGINNER" in prompt
        assert prompt == BEGINNER_PROMPT_ADDITIONS

    def test_intermediate_returns_correct_prompt(self) -> None:
        """Returns intermediate prompt for 'intermediate'."""
        prompt = get_skill_prompt("intermediate")
        assert "INTERMEDIATE" in prompt
        assert prompt == INTERMEDIATE_PROMPT_ADDITIONS

    def test_expert_returns_correct_prompt(self) -> None:
        """Returns expert prompt for 'expert'."""
        prompt = get_skill_prompt("expert")
        assert "EXPERT" in prompt
        assert prompt == EXPERT_PROMPT_ADDITIONS

    def test_invalid_returns_intermediate(self) -> None:
        """Returns intermediate for unknown skill level."""
        prompt = get_skill_prompt("unknown")  # type: ignore[arg-type]
        assert "INTERMEDIATE" in prompt
        assert prompt == INTERMEDIATE_PROMPT_ADDITIONS

    def test_empty_returns_intermediate(self) -> None:
        """Returns intermediate for empty string."""
        prompt = get_skill_prompt("")  # type: ignore[arg-type]
        assert "INTERMEDIATE" in prompt


# =============================================================================
# Fixtures for Context and User Prompt Tests
# =============================================================================


@pytest.fixture
def sample_material() -> MaterialSpec:
    """Create sample material specification."""
    return MaterialSpec(material_type=MaterialType.PLYWOOD, thickness=0.75)


@pytest.fixture
def sample_cabinet(sample_material: MaterialSpec) -> Cabinet:
    """Create sample cabinet for testing."""
    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=sample_material,
        sections=[
            Section(
                width=24.0,
                height=84.0,
                depth=12.0,
                position=Position(0.0, 0.0),
                shelves=[
                    Shelf(
                        width=23.5,
                        depth=11.5,
                        material=sample_material,
                        position=Position(0.25, 20.0),
                    ),
                ],
            ),
            Section(
                width=24.0,
                height=84.0,
                depth=12.0,
                position=Position(24.0, 0.0),
                shelves=[],
            ),
        ],
    )


@pytest.fixture
def sample_cut_list(sample_material: MaterialSpec) -> list[CutPiece]:
    """Create sample cut list."""
    return [
        CutPiece(
            label="Left Side",
            width=11.25,
            height=84.0,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.LEFT_SIDE,
        ),
        CutPiece(
            label="Right Side",
            width=11.25,
            height=84.0,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.RIGHT_SIDE,
        ),
        CutPiece(
            label="Top",
            width=46.5,
            height=11.25,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.TOP,
        ),
        CutPiece(
            label="Shelf",
            width=23.5,
            height=11.5,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.SHELF,
        ),
    ]


# =============================================================================
# Test Class: build_context_prompt Function
# =============================================================================


class TestBuildContextPrompt:
    """Tests for build_context_prompt function."""

    def test_includes_cabinet_specifications_header(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes Cabinet Specifications header."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "## Cabinet Specifications" in context

    def test_includes_dimensions(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes cabinet dimensions."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "48.00" in context
        assert "84.00" in context
        assert "12.00" in context

    def test_includes_material(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes material type."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "plywood" in context.lower()
        assert "0.75" in context

    def test_includes_section_count(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes number of sections."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "Number of Sections" in context
        assert "2" in context

    def test_includes_sections_header(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes Sections header when sections exist."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "### Sections" in context

    def test_includes_cut_list_summary(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes cut list summary."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "### Cut List Summary" in context
        assert "Total Pieces" in context

    def test_includes_cut_pieces(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes cut piece labels."""
        context = build_context_prompt(sample_cabinet, sample_cut_list, [])
        assert "Left Side" in context
        assert "Right Side" in context
        assert "Top" in context

    def test_handles_empty_cut_list(self, sample_cabinet: Cabinet) -> None:
        """Handles empty cut list gracefully."""
        context = build_context_prompt(sample_cabinet, [], [])
        assert "Cabinet Specifications" in context
        # Should not have cut list section
        assert "### Cut List Summary" not in context

    def test_includes_doors_flag(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes doors when flag is set."""
        context = build_context_prompt(
            sample_cabinet, sample_cut_list, [], has_doors=True
        )
        assert "doors" in context.lower()

    def test_includes_drawers_flag(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes drawers when flag is set."""
        context = build_context_prompt(
            sample_cabinet, sample_cut_list, [], has_drawers=True
        )
        assert "drawers" in context.lower()

    def test_includes_decorative_flag(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes decorative elements when flag is set."""
        context = build_context_prompt(
            sample_cabinet, sample_cut_list, [], has_decorative=True
        )
        assert "decorative" in context.lower()

    def test_includes_all_component_flags(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """Context includes all component flags when set."""
        context = build_context_prompt(
            sample_cabinet,
            sample_cut_list,
            [],
            has_doors=True,
            has_drawers=True,
            has_decorative=True,
        )
        assert "Components" in context
        assert "doors" in context.lower()
        assert "drawers" in context.lower()
        assert "decorative" in context.lower()

    def test_no_components_section_when_no_flags(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """No Components section when no flags set."""
        context = build_context_prompt(
            sample_cabinet,
            sample_cut_list,
            [],
            has_doors=False,
            has_drawers=False,
            has_decorative=False,
        )
        assert "**Components:**" not in context


# =============================================================================
# Test Class: build_user_prompt Function
# =============================================================================


class TestBuildUserPrompt:
    """Tests for build_user_prompt function."""

    def test_includes_skill_level(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt includes skill level."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "beginner")
        assert "BEGINNER" in prompt

    def test_includes_intermediate_skill_level(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt includes intermediate skill level."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "intermediate")
        assert "INTERMEDIATE" in prompt

    def test_includes_expert_skill_level(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt includes expert skill level."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "expert")
        assert "EXPERT" in prompt

    def test_includes_context(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt includes cabinet context."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "intermediate")
        assert "48.00" in prompt
        assert "plywood" in prompt.lower()

    def test_includes_instructions_request(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt requests instructions."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "expert")
        assert "assembly instructions" in prompt.lower()

    def test_includes_cabinet_title(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt includes cabinet title with dimensions."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "intermediate")
        assert '48"W' in prompt
        assert '84"H' in prompt
        assert '12"D' in prompt

    def test_includes_output_requirements(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt lists what to include."""
        prompt = build_user_prompt(sample_cabinet, sample_cut_list, [], "intermediate")
        assert "Safety warnings" in prompt
        assert "tool list" in prompt.lower()
        assert "Step-by-step" in prompt
        assert "Troubleshooting" in prompt

    def test_passes_component_flags(
        self, sample_cabinet: Cabinet, sample_cut_list: list[CutPiece]
    ) -> None:
        """User prompt passes component flags to context."""
        prompt = build_user_prompt(
            sample_cabinet,
            sample_cut_list,
            [],
            "intermediate",
            has_doors=True,
            has_drawers=True,
            has_decorative=True,
        )
        assert "doors" in prompt.lower()
        assert "drawers" in prompt.lower()
        assert "decorative" in prompt.lower()


# =============================================================================
# Test Class: Prompt Content Quality
# =============================================================================


class TestPromptContentQuality:
    """Tests for prompt content quality and completeness."""

    def test_base_prompt_has_assembly_sequence(self) -> None:
        """Base prompt has numbered assembly sequence."""
        assert "1." in ASSEMBLY_SYSTEM_PROMPT
        assert "2." in ASSEMBLY_SYSTEM_PROMPT
        assert "Carcase Preparation" in ASSEMBLY_SYSTEM_PROMPT

    def test_beginner_prompt_has_communication_style(self) -> None:
        """Beginner prompt has Communication Style section."""
        assert "Communication Style" in BEGINNER_PROMPT_ADDITIONS

    def test_beginner_prompt_has_detail_level(self) -> None:
        """Beginner prompt has Detail Level section."""
        assert "Detail Level" in BEGINNER_PROMPT_ADDITIONS

    def test_intermediate_prompt_has_communication_style(self) -> None:
        """Intermediate prompt has Communication Style section."""
        assert "Communication Style" in INTERMEDIATE_PROMPT_ADDITIONS

    def test_expert_prompt_has_format_preference(self) -> None:
        """Expert prompt has Format Preference section."""
        assert "Format Preference" in EXPERT_PROMPT_ADDITIONS

    def test_prompts_do_not_contain_html(self) -> None:
        """Prompts do not contain HTML tags."""
        for prompt in [
            ASSEMBLY_SYSTEM_PROMPT,
            BEGINNER_PROMPT_ADDITIONS,
            INTERMEDIATE_PROMPT_ADDITIONS,
            EXPERT_PROMPT_ADDITIONS,
        ]:
            assert "<div>" not in prompt
            assert "</div>" not in prompt
            assert "<p>" not in prompt

    def test_prompts_use_markdown_formatting(self) -> None:
        """Prompts use markdown formatting."""
        assert "##" in ASSEMBLY_SYSTEM_PROMPT
        assert "**" in ASSEMBLY_SYSTEM_PROMPT
