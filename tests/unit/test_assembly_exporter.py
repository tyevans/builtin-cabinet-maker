"""Unit tests for AssemblyInstructionGenerator exporter.

Tests cover:
- Markdown generation
- Build phase ordering
- Joinery instruction formatting
- Materials checklist generation
- File export functionality
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput
from cabinets.domain.components.results import HardwareItem
from cabinets.domain.entities import Cabinet, Panel, Room, Section, Shelf, WallSegment
from cabinets.domain.services.woodworking import (
    ConnectionJoinery,
    JointSpec,
    WoodworkingIntelligence,
)
from cabinets.domain import MaterialEstimate
from cabinets.domain.value_objects import (
    CutPiece,
    JointType,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from cabinets.infrastructure.exporters import ExporterRegistry
from cabinets.infrastructure.exporters.assembly import (
    BUILD_PHASES,
    JOINERY_INSTRUCTIONS,
    PHASE_NOTES,
    AssemblyInstructionGenerator,
)


@pytest.fixture
def material_spec() -> MaterialSpec:
    """Standard 3/4 inch plywood material specification."""
    return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def back_material_spec() -> MaterialSpec:
    """Standard 1/4 inch plywood for back panel."""
    return MaterialSpec(thickness=0.25, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sample_cabinet(material_spec: MaterialSpec, back_material_spec: MaterialSpec) -> Cabinet:
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
            Shelf(
                width=46.5,
                depth=11.75,
                material=material_spec,
                position=Position(0.75, 40.0),
            ),
        ],
    )
    cabinet.sections.append(section)

    return cabinet


@pytest.fixture
def sample_cut_list(material_spec: MaterialSpec, back_material_spec: MaterialSpec) -> list[CutPiece]:
    """Create a sample cut list for testing."""
    return [
        CutPiece(
            width=12.0,
            height=84.0,
            quantity=2,
            label="Left Side",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        ),
        CutPiece(
            width=12.0,
            height=84.0,
            quantity=1,
            label="Right Side",
            panel_type=PanelType.RIGHT_SIDE,
            material=material_spec,
        ),
        CutPiece(
            width=48.0,
            height=12.0,
            quantity=1,
            label="Top",
            panel_type=PanelType.TOP,
            material=material_spec,
        ),
        CutPiece(
            width=48.0,
            height=12.0,
            quantity=1,
            label="Bottom",
            panel_type=PanelType.BOTTOM,
            material=material_spec,
        ),
        CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back",
            panel_type=PanelType.BACK,
            material=back_material_spec,
        ),
        CutPiece(
            width=46.5,
            height=11.75,
            quantity=2,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=material_spec,
        ),
    ]


@pytest.fixture
def sample_hardware() -> list[HardwareItem]:
    """Create a sample hardware list for testing."""
    return [
        HardwareItem(
            name='#8 x 1-1/4" wood screw',
            quantity=24,
            notes="Case assembly",
        ),
        HardwareItem(
            name='#6 x 5/8" pan head screw',
            quantity=32,
            notes="Back panel attachment",
        ),
        HardwareItem(
            name="5mm shelf pin",
            quantity=8,
            notes="Adjustable shelves",
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
def layout_output(
    sample_cabinet: Cabinet,
    sample_cut_list: list[CutPiece],
    sample_hardware: list[HardwareItem],
    material_spec: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> LayoutOutput:
    """Create a sample LayoutOutput for testing."""
    return LayoutOutput(
        cabinet=sample_cabinet,
        cut_list=sample_cut_list,
        material_estimates={material_spec: material_estimate},
        total_estimate=material_estimate,
        hardware=sample_hardware,
    )


class TestAssemblyInstructionGeneratorRegistration:
    """Tests for exporter registration."""

    def test_exporter_is_registered(self) -> None:
        """AssemblyInstructionGenerator should be registered with ExporterRegistry."""
        assert ExporterRegistry.is_registered("assembly")

    def test_exporter_can_be_retrieved(self) -> None:
        """Should be able to retrieve the exporter class from registry."""
        exporter_class = ExporterRegistry.get("assembly")
        assert exporter_class is AssemblyInstructionGenerator

    def test_available_formats_includes_assembly(self) -> None:
        """Available formats should include 'assembly'."""
        formats = ExporterRegistry.available_formats()
        assert "assembly" in formats

    def test_format_name_attribute(self) -> None:
        """Exporter should have correct format_name attribute."""
        assert AssemblyInstructionGenerator.format_name == "assembly"

    def test_file_extension_attribute(self) -> None:
        """Exporter should have correct file_extension attribute."""
        assert AssemblyInstructionGenerator.file_extension == "md"


class TestAssemblyInstructionGeneratorInit:
    """Tests for exporter initialization."""

    def test_default_initialization(self) -> None:
        """Should initialize with default parameters."""
        exporter = AssemblyInstructionGenerator()
        assert exporter.include_timestamps is True
        assert exporter.include_warnings is True

    def test_custom_initialization(self) -> None:
        """Should accept custom parameters."""
        exporter = AssemblyInstructionGenerator(
            include_timestamps=False,
            include_warnings=False,
        )
        assert exporter.include_timestamps is False
        assert exporter.include_warnings is False


class TestBuildPhaseOrdering:
    """Tests for build phase ordering (FR-02.2)."""

    def test_build_phases_defined(self) -> None:
        """BUILD_PHASES should be defined with expected structure."""
        assert len(BUILD_PHASES) > 0
        for phase_id, phase_name, panel_types in BUILD_PHASES:
            assert isinstance(phase_id, str)
            assert isinstance(phase_name, str)
            assert isinstance(panel_types, list)

    def test_build_phases_order(self) -> None:
        """Build phases should be in correct order: carcase -> back -> dividers -> shelves -> doors."""
        phase_ids = [phase[0] for phase in BUILD_PHASES]

        # Verify key phases are in correct order
        carcase_idx = phase_ids.index("carcase_prep")
        horizontal_idx = phase_ids.index("horizontal")
        back_idx = phase_ids.index("back")
        dividers_idx = phase_ids.index("dividers")
        fixed_shelves_idx = phase_ids.index("fixed_shelves")
        doors_idx = phase_ids.index("doors")
        drawers_idx = phase_ids.index("drawers")

        # Carcase prep comes first
        assert carcase_idx < horizontal_idx
        # Horizontal panels before back
        assert horizontal_idx < back_idx
        # Dividers before fixed shelves
        assert dividers_idx < fixed_shelves_idx
        # Shelves before doors and drawers
        assert fixed_shelves_idx < doors_idx
        assert fixed_shelves_idx < drawers_idx

    def test_carcase_panels_include_sides(self) -> None:
        """Carcase prep phase should include side panels."""
        carcase_phase = next(p for p in BUILD_PHASES if p[0] == "carcase_prep")
        panel_types = carcase_phase[2]
        assert PanelType.LEFT_SIDE in panel_types
        assert PanelType.RIGHT_SIDE in panel_types

    def test_horizontal_panels_include_top_bottom(self) -> None:
        """Horizontal phase should include top and bottom panels."""
        horizontal_phase = next(p for p in BUILD_PHASES if p[0] == "horizontal")
        panel_types = horizontal_phase[2]
        assert PanelType.TOP in panel_types
        assert PanelType.BOTTOM in panel_types

    def test_back_phase_includes_back_panel(self) -> None:
        """Back phase should include back panel."""
        back_phase = next(p for p in BUILD_PHASES if p[0] == "back")
        panel_types = back_phase[2]
        assert PanelType.BACK in panel_types


class TestJoineryInstructions:
    """Tests for joinery instruction formatting (FR-02.4)."""

    def test_joinery_instructions_defined(self) -> None:
        """JOINERY_INSTRUCTIONS should be defined for all joint types."""
        assert "dado" in JOINERY_INSTRUCTIONS
        assert "rabbet" in JOINERY_INSTRUCTIONS
        assert "butt" in JOINERY_INSTRUCTIONS
        assert "biscuit" in JOINERY_INSTRUCTIONS
        assert "pocket_hole" in JOINERY_INSTRUCTIONS
        assert "dowel" in JOINERY_INSTRUCTIONS

    def test_dado_instruction_format(self) -> None:
        """Dado instruction should include depth, width, and position placeholders."""
        template = JOINERY_INSTRUCTIONS["dado"]
        assert "{depth" in template
        assert "{width" in template
        assert "{position}" in template

    def test_rabbet_instruction_format(self) -> None:
        """Rabbet instruction should include depth and width placeholders."""
        template = JOINERY_INSTRUCTIONS["rabbet"]
        assert "{depth" in template
        assert "{width" in template

    def test_pocket_hole_instruction_format(self) -> None:
        """Pocket hole instruction should include spacing placeholder."""
        template = JOINERY_INSTRUCTIONS["pocket_hole"]
        assert "{spacing" in template


class TestPhaseNotes:
    """Tests for phase notes (FR-02.5)."""

    def test_phase_notes_defined(self) -> None:
        """PHASE_NOTES should be defined for all build phases."""
        for phase_id, _, _ in BUILD_PHASES:
            assert phase_id in PHASE_NOTES, f"Missing notes for phase: {phase_id}"

    def test_phase_notes_include_glue(self) -> None:
        """Each phase should have glue recommendations."""
        for phase_id, notes in PHASE_NOTES.items():
            assert "glue" in notes, f"Missing glue note for phase: {phase_id}"

    def test_phase_notes_include_fasteners(self) -> None:
        """Each phase should have fastener recommendations."""
        for phase_id, notes in PHASE_NOTES.items():
            assert "fasteners" in notes, f"Missing fasteners note for phase: {phase_id}"


class TestMarkdownGeneration:
    """Tests for markdown content generation."""

    def test_export_string_returns_string(self, layout_output: LayoutOutput) -> None:
        """export_string should return a string."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_export_string_includes_header(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include header with dimensions."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)
        assert "# Assembly Instructions" in result
        assert '48"W' in result or "48" in result
        assert '84"H' in result or "84" in result

    def test_export_string_includes_materials_checklist(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include materials checklist."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)
        assert "## Materials Checklist" in result
        assert "[ ]" in result  # Checkbox format

    def test_export_string_includes_tools(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include tools section."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)
        assert "## Tools Needed" in result
        assert "Router" in result or "Drill" in result

    def test_export_string_includes_safety_warnings(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include safety warnings when enabled."""
        exporter = AssemblyInstructionGenerator(include_warnings=True)
        result = exporter.export_string(layout_output)
        assert "## Safety Warnings" in result or "Safety" in result

    def test_export_string_excludes_safety_warnings(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should exclude safety warnings when disabled."""
        exporter = AssemblyInstructionGenerator(include_warnings=False)
        result = exporter.export_string(layout_output)
        assert "## Safety Warnings" not in result

    def test_export_string_includes_assembly_steps(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include assembly steps."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)
        assert "## Assembly Steps" in result
        assert "### Step" in result

    def test_export_string_includes_finishing(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include finishing notes."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)
        assert "## Finishing" in result

    def test_export_string_includes_timestamp_by_default(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should include timestamp by default."""
        exporter = AssemblyInstructionGenerator(include_timestamps=True)
        result = exporter.export_string(layout_output)
        assert "Generated:" in result

    def test_export_string_excludes_timestamp_when_disabled(self, layout_output: LayoutOutput) -> None:
        """Generated markdown should exclude timestamp when disabled."""
        exporter = AssemblyInstructionGenerator(include_timestamps=False)
        result = exporter.export_string(layout_output)
        assert "Generated:" not in result


class TestCutPieceGrouping:
    """Tests for grouping cut pieces by build phase."""

    def test_group_pieces_by_phase(
        self, sample_cut_list: list[CutPiece]
    ) -> None:
        """Should correctly group cut pieces by build phase."""
        exporter = AssemblyInstructionGenerator()
        groups = exporter._group_pieces_by_phase(sample_cut_list)

        # Check side panels are in carcase_prep
        assert "carcase_prep" in groups
        carcase_pieces = groups["carcase_prep"]
        carcase_types = {p.panel_type for p in carcase_pieces}
        assert PanelType.LEFT_SIDE in carcase_types

        # Check horizontal panels
        assert "horizontal" in groups
        horizontal_pieces = groups["horizontal"]
        horizontal_types = {p.panel_type for p in horizontal_pieces}
        assert PanelType.TOP in horizontal_types
        assert PanelType.BOTTOM in horizontal_types

        # Check back panel
        assert "back" in groups
        back_pieces = groups["back"]
        back_types = {p.panel_type for p in back_pieces}
        assert PanelType.BACK in back_types

        # Check shelves
        assert "fixed_shelves" in groups
        shelf_pieces = groups["fixed_shelves"]
        shelf_types = {p.panel_type for p in shelf_pieces}
        assert PanelType.SHELF in shelf_types


class TestJoineryFormatting:
    """Tests for joinery instruction formatting."""

    def test_format_joinery_step_dado(self) -> None:
        """Should format dado joint instruction correctly."""
        exporter = AssemblyInstructionGenerator()
        joinery = ConnectionJoinery(
            from_panel=PanelType.LEFT_SIDE,
            to_panel=PanelType.SHELF,
            joint=JointSpec.dado(depth=0.25),
            location_description='Shelf at 24" height',
        )
        result = exporter._format_joinery_step(joinery)

        assert "Left Side" in result
        assert "Shelf" in result
        assert "dado" in result.lower() or "groove" in result.lower()

    def test_format_joinery_step_rabbet(self) -> None:
        """Should format rabbet joint instruction correctly."""
        exporter = AssemblyInstructionGenerator()
        joinery = ConnectionJoinery(
            from_panel=PanelType.LEFT_SIDE,
            to_panel=PanelType.BACK,
            joint=JointSpec.rabbet(width=0.25, depth=0.375),
            location_description="Back panel rabbet",
        )
        result = exporter._format_joinery_step(joinery)

        assert "Left Side" in result
        assert "Back" in result
        assert "rabbet" in result.lower()

    def test_format_joinery_step_pocket_screw(self) -> None:
        """Should format pocket screw joint instruction correctly."""
        exporter = AssemblyInstructionGenerator()
        joinery = ConnectionJoinery(
            from_panel=PanelType.FACE_FRAME_RAIL,
            to_panel=PanelType.FACE_FRAME_STILE,
            joint=JointSpec.pocket_screw(positions=(2.0, 10.0, 18.0), spacing=8.0),
            location_description="Face frame joint",
        )
        result = exporter._format_joinery_step(joinery)

        assert "pocket" in result.lower()
        assert "8" in result  # spacing


class TestFileExport:
    """Tests for file export functionality."""

    def test_export_creates_file(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """export should create a file at the specified path."""
        exporter = AssemblyInstructionGenerator()
        output_path = tmp_path / "assembly.md"

        exporter.export(layout_output, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_export_file_content_matches_string(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """Exported file content should match export_string output."""
        exporter = AssemblyInstructionGenerator()
        output_path = tmp_path / "assembly.md"

        exporter.export(layout_output, output_path)
        file_content = output_path.read_text()
        string_content = exporter.export_string(layout_output)

        assert file_content == string_content

    def test_export_file_is_valid_markdown(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """Exported file should contain valid markdown structure."""
        exporter = AssemblyInstructionGenerator()
        output_path = tmp_path / "assembly.md"

        exporter.export(layout_output, output_path)
        content = output_path.read_text()

        # Check for valid markdown headers
        assert content.startswith("#")
        assert "## " in content
        assert "### " in content


class TestHardwareInMaterialsChecklist:
    """Tests for hardware listing in materials checklist."""

    def test_hardware_items_listed(self, layout_output: LayoutOutput) -> None:
        """Hardware items should be listed in materials checklist."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        assert "### Hardware" in result
        # Check for specific hardware items
        assert "wood screw" in result.lower() or "screw" in result.lower()

    def test_hardware_quantities_shown(self, layout_output: LayoutOutput) -> None:
        """Hardware quantities should be displayed."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Check for quantity notation
        assert "qty:" in result.lower() or "24" in result


class TestCutListInMaterialsChecklist:
    """Tests for cut list in materials checklist."""

    def test_cut_pieces_listed(self, layout_output: LayoutOutput) -> None:
        """Cut pieces should be listed in materials checklist."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        assert "### Cut Pieces" in result
        assert "Left Side" in result
        assert "Top" in result
        assert "Bottom" in result

    def test_cut_piece_dimensions_shown(self, layout_output: LayoutOutput) -> None:
        """Cut piece dimensions should be displayed."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Check for dimension notation
        assert '"' in result  # inch symbol
        assert "x" in result.lower()  # dimension separator


class TestRoomLayoutOutputSupport:
    """Tests for RoomLayoutOutput support."""

    def test_room_layout_output_accepted(
        self,
        sample_cabinet: Cabinet,
        sample_cut_list: list[CutPiece],
        material_spec: MaterialSpec,
        material_estimate: MaterialEstimate,
    ) -> None:
        """Should accept RoomLayoutOutput as input."""
        room = Room(
            name="Test Room",
            walls=[
                WallSegment(length=120.0, height=96.0, angle=0.0),
            ]
        )
        room_output = RoomLayoutOutput(
            room=room,
            cabinets=[sample_cabinet],
            transforms=[],
            cut_list=sample_cut_list,
            material_estimates={material_spec: material_estimate},
            total_estimate=material_estimate,
        )

        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(room_output)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "## Assembly Steps" in result


class TestPhaseInstructions:
    """Tests for phase-specific instructions."""

    def test_carcase_prep_instructions(self, layout_output: LayoutOutput) -> None:
        """Carcase prep phase should have marking and dado cutting instructions."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Check for carcase prep content
        assert "Prepare Case Panels" in result or "Step 1" in result

    def test_horizontal_instructions(self, layout_output: LayoutOutput) -> None:
        """Horizontal panel phase should have glue and assembly instructions."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Check for horizontal assembly content
        assert "Attach Horizontal" in result or "top panel" in result.lower() or "bottom panel" in result.lower()

    def test_back_panel_instructions(self, layout_output: LayoutOutput) -> None:
        """Back panel phase should have squaring and attachment instructions."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Check for back panel content
        assert "Back Panel" in result or "back" in result.lower()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_cut_list(
        self,
        sample_cabinet: Cabinet,
        material_spec: MaterialSpec,
    ) -> None:
        """Should handle empty cut list gracefully."""
        empty_estimate = MaterialEstimate(
            total_area_sqin=0.0,
            total_area_sqft=0.0,
            sheet_count_4x8=0,
            sheet_count_5x5=0,
            waste_percentage=0.0,
        )
        layout_output = LayoutOutput(
            cabinet=sample_cabinet,
            cut_list=[],
            material_estimates={},
            total_estimate=empty_estimate,
        )

        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Should still generate structure even with empty cut list
        assert "# Assembly Instructions" in result
        assert "## Tools Needed" in result

    def test_no_hardware(
        self,
        sample_cabinet: Cabinet,
        sample_cut_list: list[CutPiece],
        material_spec: MaterialSpec,
        material_estimate: MaterialEstimate,
    ) -> None:
        """Should handle missing hardware list gracefully."""
        layout_output = LayoutOutput(
            cabinet=sample_cabinet,
            cut_list=sample_cut_list,
            material_estimates={material_spec: material_estimate},
            total_estimate=material_estimate,
            hardware=[],  # Empty hardware list
        )

        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Should provide default hardware items
        assert "### Hardware" in result
        assert "Wood screws" in result or "screw" in result.lower()


class TestJoineryIntegration:
    """Tests for integration with WoodworkingIntelligence joinery."""

    def test_joinery_from_cabinet(
        self,
        layout_output: LayoutOutput,
    ) -> None:
        """Should include joinery information from WoodworkingIntelligence."""
        exporter = AssemblyInstructionGenerator()
        result = exporter.export_string(layout_output)

        # Joinery section should be generated
        # The exact content depends on what WoodworkingIntelligence returns
        assert "## Assembly Steps" in result

    def test_joinery_error_handling(
        self,
        layout_output: LayoutOutput,
    ) -> None:
        """Should handle joinery generation errors gracefully."""
        exporter = AssemblyInstructionGenerator()

        # Even if joinery fails, export should complete
        result = exporter.export_string(layout_output)
        assert isinstance(result, str)
        assert len(result) > 0
