"""Unit tests for LLMAssemblyGenerator.

Tests cover:
- Fallback behavior when Ollama is unavailable
- Fallback behavior on timeout
- Fallback behavior on validation errors
- Markdown formatting of LLM output
- Dependencies building from LayoutOutput
- Sync wrapper functionality
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput
from cabinets.domain.entities import Cabinet, Room, Section, Shelf, WallSegment
from cabinets.domain.value_objects import (
    CutPiece,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from cabinets.domain import MaterialEstimate
from cabinets.infrastructure.llm.generator import LLMAssemblyGenerator
from cabinets.infrastructure.llm.models import (
    AssemblyInstructions,
    AssemblyStep,
    SafetyWarning,
    ToolRecommendation,
    TroubleshootingTip,
    WarningSeverity,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def material_spec() -> MaterialSpec:
    """Standard 3/4 inch plywood material specification."""
    return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def back_material_spec() -> MaterialSpec:
    """Standard 1/4 inch plywood for back panel."""
    return MaterialSpec(thickness=0.25, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sample_cabinet(
    material_spec: MaterialSpec, back_material_spec: MaterialSpec
) -> Cabinet:
    """Create a sample cabinet for testing."""
    cabinet = Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=material_spec,
        back_material=back_material_spec,
    )

    # Add a section with shelves
    section = Section(
        width=46.5,
        height=82.5,
        depth=11.75,
        position=Position(0.75, 0.75),
        shelves=[
            Shelf(
                width=46.5,
                depth=11.75,
                material=material_spec,
                position=Position(0.75, 20.0),
            ),
        ],
    )
    cabinet.sections.append(section)

    return cabinet


@pytest.fixture
def sample_cut_list(
    material_spec: MaterialSpec, back_material_spec: MaterialSpec
) -> list[CutPiece]:
    """Create a sample cut list for testing."""
    return [
        CutPiece(
            width=12.0,
            height=84.0,
            quantity=2,
            label="Side Panels",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        ),
        CutPiece(
            width=46.5,
            height=12.0,
            quantity=2,
            label="Top/Bottom",
            panel_type=PanelType.TOP,
            material=material_spec,
        ),
        CutPiece(
            width=46.5,
            height=83.5,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=back_material_spec,
        ),
        CutPiece(
            width=46.5,
            height=11.75,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=material_spec,
        ),
    ]


@pytest.fixture
def material_estimate() -> MaterialEstimate:
    """Create a sample material estimate."""
    return MaterialEstimate(
        total_area_sqin=7200.0,
        total_area_sqft=50.0,
        sheet_count_4x8=2,
        sheet_count_5x5=3,
        waste_percentage=0.1,
    )


@pytest.fixture
def sample_layout_output(
    sample_cabinet: Cabinet,
    sample_cut_list: list[CutPiece],
    material_spec: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> LayoutOutput:
    """Create a sample LayoutOutput for testing."""
    return LayoutOutput(
        cabinet=sample_cabinet,
        cut_list=sample_cut_list,
        material_estimates={material_spec: material_estimate},
        total_estimate=material_estimate,
        hardware=[],
    )


@pytest.fixture
def sample_room_layout_output(
    sample_cabinet: Cabinet,
    sample_cut_list: list[CutPiece],
    material_spec: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> RoomLayoutOutput:
    """Create a sample RoomLayoutOutput for testing."""
    room = Room(
        name="Test Room",
        walls=[WallSegment(length=48.0, height=84.0, angle=0, depth=12.0)],
    )
    return RoomLayoutOutput(
        room=room,
        cabinets=[sample_cabinet],
        transforms=[],
        cut_list=sample_cut_list,
        material_estimates={material_spec: material_estimate},
        total_estimate=material_estimate,
    )


@pytest.fixture
def sample_assembly_instructions() -> AssemblyInstructions:
    """Create sample AssemblyInstructions for testing."""
    return AssemblyInstructions(
        title='48"W x 84"H x 12"D Cabinet Assembly',
        skill_level="intermediate",
        cabinet_summary="A standard plywood cabinet with one section and one shelf.",
        estimated_time="2-3 hours",
        safety_warnings=[
            SafetyWarning(
                severity=WarningSeverity.DANGER,
                message="Always wear safety glasses when using power tools",
                context="When cutting or routing",
                mitigation="Keep eye protection on at all times",
            ),
            SafetyWarning(
                severity=WarningSeverity.WARNING,
                message="Ensure work area is well ventilated when applying finish",
                context="During finishing phase",
                mitigation="Work near an open window or use a fan",
            ),
        ],
        tools_needed=[
            ToolRecommendation(
                tool="Table Saw",
                purpose="Cutting panels to size",
                alternatives=["Track Saw", "Circular Saw with Guide"],
                required=True,
            ),
            ToolRecommendation(
                tool="Router",
                purpose="Cutting dados and rabbets",
                alternatives=["Table Saw with Dado Blade"],
                required=True,
            ),
            ToolRecommendation(
                tool="Orbital Sander",
                purpose="Surface preparation before finishing",
                alternatives=["Hand sanding"],
                required=False,
            ),
        ],
        materials_checklist=[
            "All cut pieces verified against cut list",
            "Wood glue (PVA or Titebond)",
            "Sandpaper (120, 180, 220 grit)",
        ],
        steps=[
            AssemblyStep(
                step_number=1,
                phase="Carcase Assembly",
                title="Prepare Side Panels",
                description="Lay out side panels with inside faces up. Mark dado positions.",
                pieces_involved=["Side Panels"],
                joinery_details='Cut dados 0.25" deep for shelf positions',
                time_estimate="15 minutes",
                difficulty="easy",
                quality_check="Verify dado positions match shelf locations",
                common_mistakes=["Cutting dados on wrong face"],
            ),
            AssemblyStep(
                step_number=2,
                phase="Carcase Assembly",
                title="Attach Top and Bottom",
                description="Apply glue to dados and insert top and bottom panels.",
                pieces_involved=["Side Panels", "Top/Bottom"],
                joinery_details="Use dado joints for strong connection",
                time_estimate="30 minutes",
                difficulty="moderate",
                quality_check="Check for square using diagonal measurements",
                common_mistakes=["Not checking for square before glue sets"],
            ),
        ],
        troubleshooting=[
            TroubleshootingTip(
                issue="Cabinet is not square",
                cause="Panels not aligned during glue-up",
                solution="Use clamps to pull cabinet into square before glue sets",
                prevention="Always check diagonals immediately after clamping",
            ),
        ],
        finishing_notes="After assembly, sand all surfaces and apply your chosen finish.",
        generated_by="llm",
    )


# =============================================================================
# Test Class: LLMAssemblyGenerator Initialization
# =============================================================================


class TestLLMAssemblyGeneratorInit:
    """Tests for LLMAssemblyGenerator initialization."""

    def test_default_initialization(self) -> None:
        """Test generator initializes with default values."""
        generator = LLMAssemblyGenerator()

        assert generator.ollama_url == "http://localhost:11434"
        assert generator.model == "llama3.2"
        assert generator.timeout == 30.0
        assert generator.skill_level == "intermediate"
        assert generator.include_troubleshooting is True
        assert generator.include_time_estimates is True

    def test_custom_initialization(self) -> None:
        """Test generator initializes with custom values."""
        generator = LLMAssemblyGenerator(
            ollama_url="http://custom:8080",
            model="llama3.1",
            timeout=60.0,
            skill_level="beginner",
            include_troubleshooting=False,
            include_time_estimates=False,
        )

        assert generator.ollama_url == "http://custom:8080"
        assert generator.model == "llama3.1"
        assert generator.timeout == 60.0
        assert generator.skill_level == "beginner"
        assert generator.include_troubleshooting is False
        assert generator.include_time_estimates is False

    def test_health_check_created(self) -> None:
        """Test that health check is created with correct URL."""
        generator = LLMAssemblyGenerator(ollama_url="http://test:1234")

        assert generator.health_check is not None
        assert generator.health_check.base_url == "http://test:1234"

    def test_fallback_generator_created(self) -> None:
        """Test that fallback generator is created."""
        generator = LLMAssemblyGenerator()

        assert generator.fallback is not None


# =============================================================================
# Test Class: Fallback Behavior
# =============================================================================


class TestFallbackBehavior:
    """Tests for fallback behavior when Ollama is unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_on_server_unavailable(
        self, sample_layout_output: LayoutOutput
    ) -> None:
        """Test fallback is triggered when Ollama server is unavailable."""
        generator = LLMAssemblyGenerator(ollama_url="http://localhost:99999")

        with patch.object(
            generator.health_check, "is_available", new_callable=AsyncMock
        ) as mock_available:
            mock_available.return_value = False

            result = await generator.generate(sample_layout_output)

            assert "template fallback" in result
            assert "Ollama server not available" in result
            mock_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_on_model_not_found(
        self, sample_layout_output: LayoutOutput
    ) -> None:
        """Test fallback is triggered when model is not found."""
        generator = LLMAssemblyGenerator(model="nonexistent-model")

        with (
            patch.object(
                generator.health_check, "is_available", new_callable=AsyncMock
            ) as mock_available,
            patch.object(
                generator.health_check, "has_model", new_callable=AsyncMock
            ) as mock_has_model,
        ):
            mock_available.return_value = True
            mock_has_model.return_value = False

            result = await generator.generate(sample_layout_output)

            assert "template fallback" in result
            assert "nonexistent-model" in result
            assert "not available" in result

    @pytest.mark.asyncio
    async def test_fallback_on_timeout(
        self, sample_layout_output: LayoutOutput
    ) -> None:
        """Test fallback is triggered on timeout."""
        generator = LLMAssemblyGenerator(timeout=0.001)

        async def slow_agent(*args: Any, **kwargs: Any) -> None:
            await asyncio.sleep(1.0)

        with (
            patch.object(
                generator.health_check, "is_available", new_callable=AsyncMock
            ) as mock_available,
            patch.object(
                generator.health_check, "has_model", new_callable=AsyncMock
            ) as mock_has_model,
            patch(
                "cabinets.infrastructure.llm.generator.run_assembly_agent",
                side_effect=slow_agent,
            ),
        ):
            mock_available.return_value = True
            mock_has_model.return_value = True

            result = await generator.generate(sample_layout_output)

            assert "template fallback" in result
            assert "timed out" in result

    @pytest.mark.asyncio
    async def test_fallback_on_unexpected_error(
        self, sample_layout_output: LayoutOutput
    ) -> None:
        """Test fallback is triggered on unexpected errors."""
        generator = LLMAssemblyGenerator()

        with (
            patch.object(
                generator.health_check, "is_available", new_callable=AsyncMock
            ) as mock_available,
            patch.object(
                generator.health_check, "has_model", new_callable=AsyncMock
            ) as mock_has_model,
            patch(
                "cabinets.infrastructure.llm.generator.run_assembly_agent",
                side_effect=RuntimeError("Unexpected error"),
            ),
        ):
            mock_available.return_value = True
            mock_has_model.return_value = True

            result = await generator.generate(sample_layout_output)

            assert "template fallback" in result
            assert "RuntimeError" in result

    def test_fallback_generate_includes_header(
        self, sample_layout_output: LayoutOutput
    ) -> None:
        """Test that fallback output includes proper header comments."""
        generator = LLMAssemblyGenerator()

        result = generator._fallback_generate(
            sample_layout_output, reason="Test reason"
        )

        assert "<!-- Generated using template fallback -->" in result
        assert "<!-- Reason: Test reason -->" in result
        assert "ollama pull" in result
        assert "## Assembly Steps" in result


# =============================================================================
# Test Class: Successful LLM Generation
# =============================================================================


class TestSuccessfulGeneration:
    """Tests for successful LLM-based generation."""

    @pytest.mark.asyncio
    async def test_successful_generation(
        self,
        sample_layout_output: LayoutOutput,
        sample_assembly_instructions: AssemblyInstructions,
    ) -> None:
        """Test successful LLM generation returns formatted markdown."""
        generator = LLMAssemblyGenerator()

        with (
            patch.object(
                generator.health_check, "is_available", new_callable=AsyncMock
            ) as mock_available,
            patch.object(
                generator.health_check, "has_model", new_callable=AsyncMock
            ) as mock_has_model,
            patch(
                "cabinets.infrastructure.llm.generator.run_assembly_agent",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_available.return_value = True
            mock_has_model.return_value = True
            mock_agent.return_value = sample_assembly_instructions

            result = await generator.generate(sample_layout_output)

            assert "template fallback" not in result
            assert "**Skill Level:** Intermediate" in result
            assert "## Assembly Steps" in result
            assert "AI-assisted generation" in result


# =============================================================================
# Test Class: Markdown Formatting
# =============================================================================


class TestMarkdownFormatting:
    """Tests for markdown formatting of LLM output."""

    def test_format_title_and_header(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test title and header formatting."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert '# 48"W x 84"H x 12"D Cabinet Assembly' in result
        assert "**Skill Level:** Intermediate" in result
        assert "**Estimated Time:** 2-3 hours" in result

    def test_format_safety_warnings_by_severity(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test safety warnings are grouped by severity."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "## Safety First" in result
        assert "**DANGER:**" in result
        assert "**WARNING:**" in result
        # DANGER should appear before WARNING
        danger_pos = result.find("**DANGER:**")
        warning_pos = result.find("**WARNING:**")
        assert danger_pos < warning_pos

    def test_format_tools_required_and_optional(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test tools are separated into required and optional."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "## Tools Needed" in result
        assert "### Required" in result
        assert "### Optional" in result
        assert "**Table Saw**" in result
        assert "Orbital Sander" in result

    def test_format_materials_checklist(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test materials checklist formatting."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "## Materials Checklist" in result
        assert "- [ ]" in result
        assert "Wood glue" in result

    def test_format_assembly_steps_with_phases(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test assembly steps are grouped by phase."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "## Assembly Steps" in result
        assert "### Carcase Assembly" in result
        assert "#### Step 1: Prepare Side Panels" in result
        assert "#### Step 2: Attach Top and Bottom" in result

    def test_format_step_details(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test step details are included."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "**Pieces:**" in result
        assert "**Instructions:**" in result
        assert "**Joinery:**" in result
        assert "**Quality Check:**" in result
        assert "**Common Mistakes to Avoid:**" in result

    def test_format_troubleshooting(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test troubleshooting section formatting."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "## Troubleshooting" in result
        assert "### Cabinet is not square" in result
        assert "**Likely Cause:**" in result
        assert "**Solution:**" in result
        assert "**Prevention:**" in result

    def test_format_finishing_notes(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test finishing notes formatting."""
        generator = LLMAssemblyGenerator()

        result = generator._format_markdown(sample_assembly_instructions)

        assert "## Finishing" in result
        assert "sand all surfaces" in result

    def test_time_estimates_included_when_enabled(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test time estimates are included when enabled."""
        generator = LLMAssemblyGenerator(include_time_estimates=True)

        result = generator._format_markdown(sample_assembly_instructions)

        assert "Time: 15 minutes" in result or "Time: 30 minutes" in result

    def test_time_estimates_excluded_when_disabled(
        self, sample_assembly_instructions: AssemblyInstructions
    ) -> None:
        """Test time estimates are excluded when disabled."""
        generator = LLMAssemblyGenerator(include_time_estimates=False)

        result = generator._format_markdown(sample_assembly_instructions)

        # Time should not appear in step headers when disabled
        lines = result.split("\n")
        step_headers = [line for line in lines if line.startswith("#### Step")]
        for header in step_headers:
            assert "Time:" not in header

    def test_troubleshooting_excluded_when_disabled(self) -> None:
        """Test troubleshooting is excluded when disabled."""
        generator = LLMAssemblyGenerator(include_troubleshooting=False)

        instructions = AssemblyInstructions(
            title="Test",
            skill_level="beginner",
            cabinet_summary="Test cabinet",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[
                AssemblyStep(
                    step_number=1,
                    phase="Test",
                    title="Test Step",
                    description="Test description",
                    pieces_involved=[],
                ),
            ],
            troubleshooting=[
                TroubleshootingTip(
                    issue="Test issue",
                    cause="Test cause",
                    solution="Test solution",
                ),
            ],
            finishing_notes="Test notes",
        )

        result = generator._format_markdown(instructions)

        assert "## Troubleshooting" not in result


# =============================================================================
# Test Class: Build Dependencies
# =============================================================================


class TestBuildDeps:
    """Tests for building AssemblyDeps from LayoutOutput."""

    def test_build_deps_from_layout_output(
        self, sample_layout_output: LayoutOutput
    ) -> None:
        """Test building deps from LayoutOutput."""
        generator = LLMAssemblyGenerator(skill_level="beginner")

        with patch(
            "cabinets.domain.services.woodworking.WoodworkingIntelligence"
        ) as mock_intel_class:
            mock_intel = MagicMock()
            mock_intel.get_joinery.return_value = []
            mock_intel_class.return_value = mock_intel

            deps = generator._build_deps(sample_layout_output)

            assert deps.cabinet == sample_layout_output.cabinet
            assert deps.cut_list == sample_layout_output.cut_list
            assert deps.skill_level == "beginner"
            assert deps.material_type == MaterialType.PLYWOOD

    def test_build_deps_from_room_layout_output(
        self, sample_room_layout_output: RoomLayoutOutput
    ) -> None:
        """Test building deps from RoomLayoutOutput."""
        generator = LLMAssemblyGenerator(skill_level="expert")

        with patch(
            "cabinets.domain.services.woodworking.WoodworkingIntelligence"
        ) as mock_intel_class:
            mock_intel = MagicMock()
            mock_intel.get_joinery.return_value = []
            mock_intel_class.return_value = mock_intel

            deps = generator._build_deps(sample_room_layout_output)

            assert deps.cabinet == sample_room_layout_output.cabinets[0]
            assert deps.cut_list == sample_room_layout_output.cut_list
            assert deps.skill_level == "expert"

    def test_build_deps_detects_doors(self, sample_cabinet: Cabinet) -> None:
        """Test that doors are detected in cut list."""
        generator = LLMAssemblyGenerator()
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)

        cut_list_with_doors = [
            CutPiece(
                width=20.0,
                height=30.0,
                quantity=1,
                label="Door",
                panel_type=PanelType.DOOR,
                material=material,
            ),
        ]

        empty_estimate = MaterialEstimate(
            total_area_sqin=0,
            total_area_sqft=0,
            sheet_count_4x8=0,
            sheet_count_5x5=0,
            waste_percentage=0,
        )
        output = LayoutOutput(
            cabinet=sample_cabinet,
            cut_list=cut_list_with_doors,
            material_estimates={},
            total_estimate=empty_estimate,
        )

        with patch(
            "cabinets.domain.services.woodworking.WoodworkingIntelligence"
        ) as mock_intel_class:
            mock_intel = MagicMock()
            mock_intel.get_joinery.return_value = []
            mock_intel_class.return_value = mock_intel

            deps = generator._build_deps(output)

            assert deps.has_doors is True
            assert deps.has_drawers is False

    def test_build_deps_detects_drawers(self, sample_cabinet: Cabinet) -> None:
        """Test that drawers are detected in cut list."""
        generator = LLMAssemblyGenerator()
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)

        cut_list_with_drawers = [
            CutPiece(
                width=20.0,
                height=6.0,
                quantity=1,
                label="Drawer Front",
                panel_type=PanelType.DRAWER_FRONT,
                material=material,
            ),
            CutPiece(
                width=18.0,
                height=5.0,
                quantity=2,
                label="Drawer Side",
                panel_type=PanelType.DRAWER_SIDE,
                material=material,
            ),
        ]

        empty_estimate = MaterialEstimate(
            total_area_sqin=0,
            total_area_sqft=0,
            sheet_count_4x8=0,
            sheet_count_5x5=0,
            waste_percentage=0,
        )
        output = LayoutOutput(
            cabinet=sample_cabinet,
            cut_list=cut_list_with_drawers,
            material_estimates={},
            total_estimate=empty_estimate,
        )

        with patch(
            "cabinets.domain.services.woodworking.WoodworkingIntelligence"
        ) as mock_intel_class:
            mock_intel = MagicMock()
            mock_intel.get_joinery.return_value = []
            mock_intel_class.return_value = mock_intel

            deps = generator._build_deps(output)

            assert deps.has_doors is False
            assert deps.has_drawers is True


# =============================================================================
# Test Class: Sync Wrapper
# =============================================================================


class TestSyncWrapper:
    """Tests for synchronous wrapper."""

    def test_sync_wrapper_calls_async(self, sample_layout_output: LayoutOutput) -> None:
        """Test that sync wrapper calls async generate."""
        generator = LLMAssemblyGenerator()

        # Use unavailable server to trigger fast fallback
        with patch.object(
            generator.health_check, "is_available", new_callable=AsyncMock
        ) as mock_available:
            mock_available.return_value = False

            result = generator.generate_sync(sample_layout_output)

            assert isinstance(result, str)
            assert "template fallback" in result


# =============================================================================
# Test Class: Import and Export
# =============================================================================


class TestImportExport:
    """Tests for module imports and exports."""

    def test_import_from_llm_module(self) -> None:
        """Test that LLMAssemblyGenerator can be imported from llm module."""
        from cabinets.infrastructure.llm import (
            LLMAssemblyGenerator as ImportedGenerator,
        )

        assert ImportedGenerator is LLMAssemblyGenerator

    def test_generator_in_all_exports(self) -> None:
        """Test that LLMAssemblyGenerator is in __all__."""
        from cabinets.infrastructure.llm import __all__

        assert "LLMAssemblyGenerator" in __all__
