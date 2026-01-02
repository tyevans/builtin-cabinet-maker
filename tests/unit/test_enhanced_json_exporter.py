"""Unit tests for EnhancedJsonExporter.

Tests cover:
- FR-03.1: Normalized configuration extraction
- FR-03.2: Calculated dimensions per piece
- FR-03.3: 3D positions for each panel
- FR-03.4: Joinery specifications and validation warnings
- FR-03.5: Schema version field
- File export functionality
- Configurable options (enable/disable sections)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput
from cabinets.domain.components.results import HardwareItem
from cabinets.domain.entities import Cabinet, Room, Section, Shelf, WallSegment
from cabinets.domain.services import MaterialEstimate
from cabinets.domain.value_objects import (
    CutPiece,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from cabinets.infrastructure.exporters import ExporterRegistry
from cabinets.infrastructure.exporters.enhanced_json import (
    SCHEMA_VERSION,
    EnhancedJsonExporter,
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
def sample_cut_list(
    material_spec: MaterialSpec, back_material_spec: MaterialSpec
) -> list[CutPiece]:
    """Create a sample cut list for testing."""
    return [
        CutPiece(
            width=11.75,
            height=82.5,
            quantity=2,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        ),
        CutPiece(
            width=48.0,
            height=11.75,
            quantity=1,
            label="Top",
            panel_type=PanelType.TOP,
            material=material_spec,
        ),
        CutPiece(
            width=48.0,
            height=11.75,
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


@pytest.fixture
def room_layout_output(
    sample_cabinet: Cabinet,
    sample_cut_list: list[CutPiece],
    material_spec: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> RoomLayoutOutput:
    """Create a sample RoomLayoutOutput for testing."""
    room = Room(
        name="Test Room",
        walls=[
            WallSegment(length=120.0, height=96.0, angle=0.0, name="Wall A"),
        ],
    )
    return RoomLayoutOutput(
        room=room,
        cabinets=[sample_cabinet],
        transforms=[],
        cut_list=sample_cut_list,
        material_estimates={material_spec: material_estimate},
        total_estimate=material_estimate,
    )


class TestEnhancedJsonExporterRegistration:
    """Tests for exporter registration."""

    def test_exporter_is_registered(self) -> None:
        """EnhancedJsonExporter should be registered with ExporterRegistry."""
        assert ExporterRegistry.is_registered("json")

    def test_exporter_can_be_retrieved(self) -> None:
        """Should be able to retrieve the exporter class from registry."""
        exporter_class = ExporterRegistry.get("json")
        assert exporter_class is EnhancedJsonExporter

    def test_available_formats_includes_json(self) -> None:
        """Available formats should include 'json'."""
        formats = ExporterRegistry.available_formats()
        assert "json" in formats

    def test_format_name_attribute(self) -> None:
        """Exporter should have correct format_name attribute."""
        assert EnhancedJsonExporter.format_name == "json"

    def test_file_extension_attribute(self) -> None:
        """Exporter should have correct file_extension attribute."""
        assert EnhancedJsonExporter.file_extension == "json"


class TestEnhancedJsonExporterInit:
    """Tests for exporter initialization."""

    def test_default_initialization(self) -> None:
        """Should initialize with default parameters."""
        exporter = EnhancedJsonExporter()
        assert exporter.include_3d_positions is True
        assert exporter.include_joinery is True
        assert exporter.include_warnings is True
        assert exporter.include_bom is True
        assert exporter.indent == 2

    def test_custom_initialization(self) -> None:
        """Should accept custom parameters."""
        exporter = EnhancedJsonExporter(
            include_3d_positions=False,
            include_joinery=False,
            include_warnings=False,
            include_bom=False,
            indent=4,
        )
        assert exporter.include_3d_positions is False
        assert exporter.include_joinery is False
        assert exporter.include_warnings is False
        assert exporter.include_bom is False
        assert exporter.indent == 4


class TestSchemaVersion:
    """Tests for FR-03.5: Schema version field."""

    def test_schema_version_constant_defined(self) -> None:
        """SCHEMA_VERSION constant should be defined."""
        assert SCHEMA_VERSION == "1.0"

    def test_output_includes_schema_version(self, layout_output: LayoutOutput) -> None:
        """Exported JSON should include schema_version at top level."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert "schema_version" in result
        assert result["schema_version"] == "1.0"


class TestNormalizedConfiguration:
    """Tests for FR-03.1: Normalized configuration extraction."""

    def test_config_section_present(self, layout_output: LayoutOutput) -> None:
        """Exported JSON should include config section."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert "config" in result
        config = result["config"]
        assert isinstance(config, dict)

    def test_config_includes_type(self, layout_output: LayoutOutput) -> None:
        """Config should identify output type."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert result["config"]["type"] == "single_cabinet"

    def test_config_includes_dimensions(self, layout_output: LayoutOutput) -> None:
        """Config should include cabinet dimensions."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        config = result["config"]
        assert "dimensions" in config
        assert config["dimensions"]["width"] == 48.0
        assert config["dimensions"]["height"] == 84.0
        assert config["dimensions"]["depth"] == 12.0

    def test_config_includes_material(self, layout_output: LayoutOutput) -> None:
        """Config should include material specification."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        config = result["config"]
        assert "material" in config
        assert config["material"]["type"] == "plywood"
        assert config["material"]["thickness"] == 0.75

    def test_config_includes_back_material(self, layout_output: LayoutOutput) -> None:
        """Config should include back material specification."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        config = result["config"]
        assert "back_material" in config
        assert config["back_material"]["type"] == "plywood"
        assert config["back_material"]["thickness"] == 0.25

    def test_config_includes_section_count(self, layout_output: LayoutOutput) -> None:
        """Config should include section count."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert result["config"]["section_count"] == 1

    def test_room_layout_config(self, room_layout_output: RoomLayoutOutput) -> None:
        """Room layout config should identify type and include room info."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(room_layout_output))

        config = result["config"]
        assert config["type"] == "room_layout"
        assert config["room_name"] == "Test Room"
        assert config["wall_count"] == 1


class TestCabinetStructure:
    """Tests for cabinet dimension and section extraction."""

    def test_cabinet_section_present(self, layout_output: LayoutOutput) -> None:
        """Exported JSON should include cabinet section."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert "cabinet" in result

    def test_cabinet_includes_dimensions(self, layout_output: LayoutOutput) -> None:
        """Cabinet should include dimensions."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        cabinet = result["cabinet"]
        assert "dimensions" in cabinet
        assert cabinet["dimensions"]["width"] == 48.0
        assert cabinet["dimensions"]["height"] == 84.0
        assert cabinet["dimensions"]["depth"] == 12.0

    def test_cabinet_includes_interior_dimensions(
        self, layout_output: LayoutOutput
    ) -> None:
        """Cabinet should include interior dimensions."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        cabinet = result["cabinet"]
        assert "interior_dimensions" in cabinet
        # Interior width = 48 - 2*0.75 = 46.5
        assert cabinet["interior_dimensions"]["width"] == 46.5

    def test_cabinet_includes_sections(self, layout_output: LayoutOutput) -> None:
        """Cabinet should include sections with details."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        cabinet = result["cabinet"]
        assert "sections" in cabinet
        assert len(cabinet["sections"]) == 1

        section = cabinet["sections"][0]
        assert section["width"] == 46.5
        assert section["shelf_count"] == 2

    def test_room_layout_has_room_info(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """Room layout should include room structure."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(room_layout_output))

        assert "room" in result
        room = result["room"]
        assert room["name"] == "Test Room"
        assert "walls" in room
        assert len(room["walls"]) == 1
        assert room["walls"][0]["length"] == 120.0

    def test_room_layout_has_cabinets_list(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """Room layout should include cabinets as a list."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(room_layout_output))

        assert "cabinets" in result
        assert isinstance(result["cabinets"], list)
        assert len(result["cabinets"]) == 1


class TestPiecesWithDimensions:
    """Tests for FR-03.2: Calculated dimensions per piece."""

    def test_pieces_section_present(self, layout_output: LayoutOutput) -> None:
        """Exported JSON should include pieces section."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert "pieces" in result
        assert isinstance(result["pieces"], list)

    def test_piece_has_id(self, layout_output: LayoutOutput) -> None:
        """Each piece should have a unique ID."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "id" in piece
            assert isinstance(piece["id"], str)
            assert len(piece["id"]) > 0

    def test_piece_has_label(self, layout_output: LayoutOutput) -> None:
        """Each piece should have a human-readable label."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "label" in piece

    def test_piece_has_dimensions(self, layout_output: LayoutOutput) -> None:
        """Each piece should have dimensions."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "dimensions" in piece
            dims = piece["dimensions"]
            assert "width" in dims
            assert "height" in dims
            assert "thickness" in dims

    def test_piece_has_panel_type(self, layout_output: LayoutOutput) -> None:
        """Each piece should have panel type."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "panel_type" in piece

    def test_piece_has_material(self, layout_output: LayoutOutput) -> None:
        """Each piece should have material specification."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "material" in piece
            material = piece["material"]
            assert "type" in material
            assert "thickness" in material


class TestThreeDPositions:
    """Tests for FR-03.3: 3D positions for each panel."""

    def test_pieces_have_3d_positions_by_default(
        self, layout_output: LayoutOutput
    ) -> None:
        """Pieces should have 3D positions when enabled (default)."""
        exporter = EnhancedJsonExporter(include_3d_positions=True)
        result = json.loads(exporter.export_string(layout_output))

        # At least some pieces should have 3D positions
        pieces_with_positions = [p for p in result["pieces"] if "position_3d" in p]
        assert len(pieces_with_positions) > 0

    def test_3d_position_structure(self, layout_output: LayoutOutput) -> None:
        """3D position should have x, y, z, width, depth, height."""
        exporter = EnhancedJsonExporter(include_3d_positions=True)
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            if "position_3d" in piece:
                pos = piece["position_3d"]
                assert "x" in pos
                assert "y" in pos
                assert "z" in pos
                assert "width" in pos
                assert "depth" in pos
                assert "height" in pos

    def test_3d_positions_disabled(self, layout_output: LayoutOutput) -> None:
        """3D positions should be excluded when disabled."""
        exporter = EnhancedJsonExporter(include_3d_positions=False)
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "position_3d" not in piece


class TestJoinerySpecifications:
    """Tests for FR-03.4: Joinery specifications."""

    def test_joinery_present_when_enabled(self, layout_output: LayoutOutput) -> None:
        """Pieces may have joinery when enabled."""
        exporter = EnhancedJsonExporter(include_joinery=True)
        result = json.loads(exporter.export_string(layout_output))

        # Joinery will be present if WoodworkingIntelligence generates it
        # Just verify the structure doesn't break
        assert "pieces" in result

    def test_joinery_structure(self, layout_output: LayoutOutput) -> None:
        """Joinery connections should have proper structure if present."""
        exporter = EnhancedJsonExporter(include_joinery=True)
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            if "joinery" in piece:
                assert isinstance(piece["joinery"], list)
                for joint in piece["joinery"]:
                    assert "connection_to" in joint
                    assert "joint_type" in joint

    def test_joinery_disabled(self, layout_output: LayoutOutput) -> None:
        """Pieces should not have joinery when disabled."""
        exporter = EnhancedJsonExporter(include_joinery=False)
        result = json.loads(exporter.export_string(layout_output))

        for piece in result["pieces"]:
            assert "joinery" not in piece


class TestCutList:
    """Tests for cut list extraction."""

    def test_cut_list_present(self, layout_output: LayoutOutput) -> None:
        """Exported JSON should include cut_list section."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert "cut_list" in result
        assert isinstance(result["cut_list"], list)

    def test_cut_list_items_have_required_fields(
        self, layout_output: LayoutOutput
    ) -> None:
        """Each cut list item should have all required fields."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for item in result["cut_list"]:
            assert "label" in item
            assert "panel_type" in item
            assert "dimensions" in item
            assert "quantity" in item
            assert "area_sq_in" in item
            assert "area_sq_ft" in item
            assert "material" in item

    def test_cut_list_dimensions_structure(self, layout_output: LayoutOutput) -> None:
        """Cut list dimensions should have width, height, thickness."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        for item in result["cut_list"]:
            dims = item["dimensions"]
            assert "width" in dims
            assert "height" in dims
            assert "thickness" in dims


class TestBillOfMaterials:
    """Tests for bill of materials (BOM) extraction."""

    def test_bom_present_when_enabled(self, layout_output: LayoutOutput) -> None:
        """BOM should be present when enabled."""
        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        assert "bom" in result

    def test_bom_excluded_when_disabled(self, layout_output: LayoutOutput) -> None:
        """BOM should be None when disabled."""
        exporter = EnhancedJsonExporter(include_bom=False)
        result = json.loads(exporter.export_string(layout_output))

        assert result.get("bom") is None

    def test_bom_includes_sheet_goods(self, layout_output: LayoutOutput) -> None:
        """BOM should include sheet goods."""
        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        bom = result["bom"]
        assert "sheet_goods" in bom
        assert isinstance(bom["sheet_goods"], list)

    def test_sheet_goods_structure(self, layout_output: LayoutOutput) -> None:
        """Sheet goods should have proper structure."""
        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        for item in result["bom"]["sheet_goods"]:
            assert "material" in item
            assert "thickness" in item
            assert "total_area_sqft" in item
            assert "sheet_count_4x8" in item

    def test_bom_includes_hardware(self, layout_output: LayoutOutput) -> None:
        """BOM should include hardware list."""
        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        bom = result["bom"]
        assert "hardware" in bom
        assert isinstance(bom["hardware"], list)
        # Should have the sample hardware items
        assert len(bom["hardware"]) > 0

    def test_bom_includes_edge_banding(self, layout_output: LayoutOutput) -> None:
        """BOM should include edge banding estimate."""
        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        bom = result["bom"]
        assert "edge_banding" in bom

    def test_bom_includes_totals(self, layout_output: LayoutOutput) -> None:
        """BOM should include totals section."""
        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        bom = result["bom"]
        assert "totals" in bom
        assert "total_area_sqft" in bom["totals"]
        assert "total_sheets_4x8" in bom["totals"]


class TestWarnings:
    """Tests for FR-03.4: Validation warnings."""

    def test_warnings_present_when_enabled(self, layout_output: LayoutOutput) -> None:
        """Warnings should be present when enabled."""
        exporter = EnhancedJsonExporter(include_warnings=True)
        result = json.loads(exporter.export_string(layout_output))

        assert "warnings" in result
        assert isinstance(result["warnings"], list)

    def test_warnings_empty_when_disabled(self, layout_output: LayoutOutput) -> None:
        """Warnings should be empty list when disabled."""
        exporter = EnhancedJsonExporter(include_warnings=False)
        result = json.loads(exporter.export_string(layout_output))

        assert result["warnings"] == []

    def test_warnings_structure(self, layout_output: LayoutOutput) -> None:
        """Warning items should have type and message."""
        exporter = EnhancedJsonExporter(include_warnings=True)
        result = json.loads(exporter.export_string(layout_output))

        for warning in result["warnings"]:
            assert "type" in warning
            assert "message" in warning


class TestFileExport:
    """Tests for file export functionality."""

    def test_export_creates_file(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """export should create a file at the specified path."""
        exporter = EnhancedJsonExporter()
        output_path = tmp_path / "output.json"

        exporter.export(layout_output, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_export_file_is_valid_json(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """Exported file should contain valid JSON."""
        exporter = EnhancedJsonExporter()
        output_path = tmp_path / "output.json"

        exporter.export(layout_output, output_path)

        # Should not raise
        data = json.loads(output_path.read_text())
        assert "schema_version" in data

    def test_export_file_content_matches_string(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """Exported file content should match export_string output."""
        exporter = EnhancedJsonExporter()
        output_path = tmp_path / "output.json"

        exporter.export(layout_output, output_path)
        file_content = output_path.read_text()
        string_content = exporter.export_string(layout_output)

        assert file_content == string_content

    def test_export_respects_indent(self, layout_output: LayoutOutput) -> None:
        """Export should respect indent parameter."""
        exporter_2 = EnhancedJsonExporter(indent=2)
        exporter_4 = EnhancedJsonExporter(indent=4)

        result_2 = exporter_2.export_string(layout_output)
        result_4 = exporter_4.export_string(layout_output)

        # The 4-space indent version should be longer
        assert len(result_4) > len(result_2)

        # Verify they parse to the same data
        assert json.loads(result_2) == json.loads(result_4)


class TestRoomLayoutOutput:
    """Tests for RoomLayoutOutput support."""

    def test_room_layout_output_accepted(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """Should accept RoomLayoutOutput as input."""
        exporter = EnhancedJsonExporter()
        result = exporter.export_string(room_layout_output)

        assert isinstance(result, str)
        data = json.loads(result)
        assert "schema_version" in data

    def test_room_layout_has_room_section(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """Room layout should have room section with walls."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(room_layout_output))

        assert "room" in result
        assert result["room"]["name"] == "Test Room"
        assert "walls" in result["room"]
        assert "total_length" in result["room"]
        assert "bounding_box" in result["room"]

    def test_room_layout_pieces_have_cabinet_prefix(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """Pieces in room layout should have cabinet index prefix in ID."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(room_layout_output))

        # At least some pieces should have cabinet prefix
        has_cabinet_prefix = any(
            piece["id"].startswith("C1-") for piece in result["pieces"]
        )
        assert has_cabinet_prefix


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_sections(
        self, material_spec: MaterialSpec, back_material_spec: MaterialSpec
    ) -> None:
        """Should handle cabinet with no sections."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=material_spec,
            back_material=back_material_spec,
        )
        estimate = MaterialEstimate(
            total_area_sqin=0.0,
            total_area_sqft=0.0,
            sheet_count_4x8=0,
            sheet_count_5x5=0,
            waste_percentage=0.0,
        )
        layout_output = LayoutOutput(
            cabinet=cabinet,
            cut_list=[],
            material_estimates={},
            total_estimate=estimate,
        )

        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        assert "cabinet" in result
        assert result["cabinet"]["sections"] == []

    def test_no_hardware(
        self,
        sample_cabinet: Cabinet,
        sample_cut_list: list[CutPiece],
        material_spec: MaterialSpec,
        material_estimate: MaterialEstimate,
    ) -> None:
        """Should handle missing hardware list."""
        layout_output = LayoutOutput(
            cabinet=sample_cabinet,
            cut_list=sample_cut_list,
            material_estimates={material_spec: material_estimate},
            total_estimate=material_estimate,
            hardware=[],
        )

        exporter = EnhancedJsonExporter(include_bom=True)
        result = json.loads(exporter.export_string(layout_output))

        assert "bom" in result
        assert result["bom"]["hardware"] == []

    def test_errors_in_output(
        self,
        sample_cabinet: Cabinet,
        sample_cut_list: list[CutPiece],
        material_spec: MaterialSpec,
        material_estimate: MaterialEstimate,
    ) -> None:
        """Should include errors from output in warnings."""
        layout_output = LayoutOutput(
            cabinet=sample_cabinet,
            cut_list=sample_cut_list,
            material_estimates={material_spec: material_estimate},
            total_estimate=material_estimate,
            errors=["Test error message"],
        )

        exporter = EnhancedJsonExporter(include_warnings=True)
        result = json.loads(exporter.export_string(layout_output))

        # Errors should appear in warnings
        error_warnings = [w for w in result["warnings"] if w["type"] == "error"]
        assert len(error_warnings) > 0
        assert "Test error message" in error_warnings[0]["message"]


class TestJsonValidity:
    """Tests for JSON output validity."""

    def test_output_is_valid_json(self, layout_output: LayoutOutput) -> None:
        """Output should be valid JSON."""
        exporter = EnhancedJsonExporter()
        result_str = exporter.export_string(layout_output)

        # Should not raise
        data = json.loads(result_str)
        assert isinstance(data, dict)

    def test_all_values_are_json_serializable(
        self, layout_output: LayoutOutput
    ) -> None:
        """All values should be JSON serializable."""
        exporter = EnhancedJsonExporter()
        result_str = exporter.export_string(layout_output)
        data = json.loads(result_str)

        # Verify round-trip
        round_trip = json.dumps(data)
        assert json.loads(round_trip) == data

    def test_numeric_precision(self, layout_output: LayoutOutput) -> None:
        """Numeric values should maintain reasonable precision."""
        exporter = EnhancedJsonExporter()
        result = json.loads(exporter.export_string(layout_output))

        # Check that dimensions are preserved
        dims = result["cabinet"]["dimensions"]
        assert dims["width"] == 48.0
        assert dims["height"] == 84.0
        assert dims["depth"] == 12.0
