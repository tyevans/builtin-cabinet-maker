"""Tests for the DXF exporter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import ezdxf
import pytest

from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput
from cabinets.domain import MaterialEstimate
from cabinets.domain.entities import Cabinet, Room, Section, WallSegment
from cabinets.domain.value_objects import (
    CutPiece,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
    Position3D,
    SectionTransform,
)
from cabinets.infrastructure.exporters import DxfExporter, ExporterRegistry, Exporter
from cabinets.infrastructure.exporters.dxf import LAYERS


# --- Helper Functions ---


def make_material_estimate(
    area_sqft: float = 32.0, sheets: int = 1
) -> MaterialEstimate:
    """Create a MaterialEstimate for testing."""
    return MaterialEstimate(
        total_area_sqin=area_sqft * 144.0,
        total_area_sqft=area_sqft,
        sheet_count_4x8=sheets,
        sheet_count_5x5=sheets,
        waste_percentage=0.1,
    )


# --- Fixtures ---


@pytest.fixture
def material_spec() -> MaterialSpec:
    """Create a standard material spec for testing."""
    return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sample_cut_pieces(material_spec: MaterialSpec) -> list[CutPiece]:
    """Create sample cut pieces for testing."""
    return [
        CutPiece(
            width=24.0,
            height=48.0,
            quantity=2,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        ),
        CutPiece(
            width=46.5,
            height=12.0,
            quantity=1,
            label="Top Panel",
            panel_type=PanelType.TOP,
            material=material_spec,
        ),
        CutPiece(
            width=22.5,
            height=11.25,
            quantity=4,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=material_spec,
        ),
    ]


@pytest.fixture
def cut_piece_with_dados(material_spec: MaterialSpec) -> CutPiece:
    """Create a cut piece with dado joinery metadata."""
    return CutPiece(
        width=12.0,
        height=36.0,
        quantity=1,
        label="Side with Dados",
        panel_type=PanelType.LEFT_SIDE,
        material=material_spec,
        cut_metadata={
            "joinery": [
                {
                    "type": "dado",
                    "position": 12.0,
                    "width": 0.75,
                    "depth": 0.375,
                    "orientation": "horizontal",
                },
                {
                    "type": "dado",
                    "position": 24.0,
                    "width": 0.75,
                    "depth": 0.375,
                    "orientation": "horizontal",
                },
            ]
        },
    )


@pytest.fixture
def simple_cabinet() -> Cabinet:
    """Create a simple cabinet for testing."""
    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        sections=[
            Section(
                width=24.0,
                height=84.0,
                depth=12.0,
                position=Position(x=0.0, y=0.0),
            ),
            Section(
                width=24.0,
                height=84.0,
                depth=12.0,
                position=Position(x=24.0, y=0.0),
            ),
        ],
    )


@pytest.fixture
def material_estimate() -> MaterialEstimate:
    """Create a material estimate for testing."""
    return MaterialEstimate(
        total_area_sqin=4608.0,  # 32 sq ft * 144 sq in
        total_area_sqft=32.0,
        sheet_count_4x8=1,
        sheet_count_5x5=1,
        waste_percentage=0.1,
    )


@pytest.fixture
def layout_output(
    simple_cabinet: Cabinet,
    sample_cut_pieces: list[CutPiece],
    material_spec: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> LayoutOutput:
    """Create a LayoutOutput for testing."""
    return LayoutOutput(
        cabinet=simple_cabinet,
        cut_list=sample_cut_pieces,
        material_estimates={material_spec: material_estimate},
        total_estimate=material_estimate,
    )


@pytest.fixture
def room_layout_output(
    simple_cabinet: Cabinet,
    sample_cut_pieces: list[CutPiece],
    material_spec: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> RoomLayoutOutput:
    """Create a RoomLayoutOutput for testing."""
    room = Room(
        name="Test Room",
        walls=[
            WallSegment(length=120.0, height=96.0, angle=0),
            WallSegment(length=96.0, height=96.0, angle=90),
            WallSegment(length=120.0, height=96.0, angle=90),
            WallSegment(length=96.0, height=96.0, angle=90),
        ],
    )
    return RoomLayoutOutput(
        room=room,
        cabinets=[simple_cabinet],
        transforms=[
            SectionTransform(
                section_index=0,
                wall_index=0,
                position=Position3D(x=0.0, y=0.0, z=0.0),
                rotation_z=0.0,
            )
        ],
        cut_list=sample_cut_pieces,
        material_estimates={material_spec: material_estimate},
        total_estimate=material_estimate,
    )


# --- Test Classes ---


class TestDxfExporterRegistration:
    """Tests for DXF exporter registration."""

    def test_dxf_exporter_is_registered(self) -> None:
        """DxfExporter should be registered as 'dxf'."""
        assert ExporterRegistry.is_registered("dxf")
        assert ExporterRegistry.get("dxf") is DxfExporter

    def test_available_formats_includes_dxf(self) -> None:
        """available_formats() should include 'dxf'."""
        formats = ExporterRegistry.available_formats()
        assert "dxf" in formats

    def test_dxf_exporter_implements_protocol(self) -> None:
        """DxfExporter should implement the Exporter protocol."""
        exporter = DxfExporter()
        assert isinstance(exporter, Exporter)


class TestDxfExporterAttributes:
    """Tests for DxfExporter class attributes."""

    def test_format_name(self) -> None:
        """DxfExporter should have format_name 'dxf'."""
        assert DxfExporter.format_name == "dxf"

    def test_file_extension(self) -> None:
        """DxfExporter should have file_extension 'dxf'."""
        assert DxfExporter.file_extension == "dxf"


class TestDxfExporterInit:
    """Tests for DxfExporter initialization."""

    def test_default_initialization(self) -> None:
        """DxfExporter should initialize with default values."""
        exporter = DxfExporter()
        assert exporter.mode == "combined"
        assert exporter.units == "inches"
        assert exporter.hole_pattern == "32mm"
        assert exporter.scale == 1.0

    def test_mm_units_sets_scale(self) -> None:
        """Setting units to 'mm' should set scale to 25.4."""
        exporter = DxfExporter(units="mm")
        assert exporter.scale == 25.4

    def test_per_panel_mode(self) -> None:
        """Mode can be set to 'per_panel'."""
        exporter = DxfExporter(mode="per_panel")
        assert exporter.mode == "per_panel"

    def test_invalid_mode_raises_error(self) -> None:
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DxfExporter(mode="invalid")
        assert "Invalid mode" in str(exc_info.value)

    def test_invalid_units_raises_error(self) -> None:
        """Invalid units should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DxfExporter(units="invalid")
        assert "Invalid units" in str(exc_info.value)

    def test_invalid_hole_pattern_raises_error(self) -> None:
        """Invalid hole pattern should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DxfExporter(hole_pattern="invalid")
        assert "Invalid hole_pattern" in str(exc_info.value)

    def test_custom_hole_diameter(self) -> None:
        """Custom hole diameter should be accepted."""
        exporter = DxfExporter(hole_diameter=0.25)
        assert exporter.hole_diameter == 0.25

    def test_no_hole_pattern(self) -> None:
        """Hole pattern can be set to 'none'."""
        exporter = DxfExporter(hole_pattern="none")
        assert exporter.hole_pattern == "none"


class TestDxfExporterLayers:
    """Tests for DXF layer creation."""

    def test_layers_constant_has_required_layers(self) -> None:
        """LAYERS constant should have all required layers."""
        assert "OUTLINE" in LAYERS
        assert "DADOS" in LAYERS
        assert "HOLES" in LAYERS
        assert "LABELS" in LAYERS

    def test_layers_have_colors(self) -> None:
        """Each layer should have a color defined."""
        for layer_name, props in LAYERS.items():
            assert "color" in props, f"Layer {layer_name} missing color"
            assert isinstance(props["color"], int)

    def test_layers_have_linetypes(self) -> None:
        """Each layer should have a linetype defined."""
        for layer_name, props in LAYERS.items():
            assert "linetype" in props, f"Layer {layer_name} missing linetype"

    def test_setup_layers_creates_layers(self) -> None:
        """_setup_layers should create all layers in the document."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)

        for layer_name in LAYERS:
            assert layer_name in doc.layers


class TestDxfExporterPanelOutline:
    """Tests for panel outline drawing."""

    def test_draw_outline_creates_polyline(self) -> None:
        """_draw_outline should create a closed polyline."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        exporter._draw_outline(msp, 0.0, 0.0, 24.0, 48.0)

        # Check that a polyline was added
        polylines = list(msp.query("LWPOLYLINE"))
        assert len(polylines) == 1

        # Check the polyline is on the OUTLINE layer
        assert polylines[0].dxf.layer == "OUTLINE"

    def test_draw_outline_with_offset(self) -> None:
        """_draw_outline should respect offset parameters."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        exporter._draw_outline(msp, 10.0, 20.0, 24.0, 48.0)

        polylines = list(msp.query("LWPOLYLINE"))
        assert len(polylines) == 1

        # Check that vertices include the offset
        vertices = list(polylines[0].get_points())
        # First vertex should be at the offset
        assert vertices[0][0] == pytest.approx(10.0)
        assert vertices[0][1] == pytest.approx(20.0)


class TestDxfExporterHoles:
    """Tests for shelf pin hole drawing."""

    def test_draw_holes_for_side_panel(self, material_spec: MaterialSpec) -> None:
        """_draw_holes should create circles for side panels."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Left Side",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        )

        exporter._draw_holes(msp, piece, 0.0, 0.0, 12.0, 36.0)

        # Check that circles were added
        circles = list(msp.query("CIRCLE"))
        assert len(circles) > 0

        # Check circles are on HOLES layer
        for circle in circles:
            assert circle.dxf.layer == "HOLES"

    def test_draw_holes_for_right_side_panel(self, material_spec: MaterialSpec) -> None:
        """_draw_holes should work for right side panels too."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Right Side",
            panel_type=PanelType.RIGHT_SIDE,
            material=material_spec,
        )

        exporter._draw_holes(msp, piece, 0.0, 0.0, 12.0, 36.0)

        circles = list(msp.query("CIRCLE"))
        assert len(circles) > 0

    def test_draw_holes_for_divider(self, material_spec: MaterialSpec) -> None:
        """_draw_holes should work for divider panels."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=12.0,
            height=48.0,
            quantity=1,
            label="Divider",
            panel_type=PanelType.DIVIDER,
            material=material_spec,
        )

        exporter._draw_holes(msp, piece, 0.0, 0.0, 12.0, 48.0)

        circles = list(msp.query("CIRCLE"))
        assert len(circles) > 0

    def test_no_holes_for_shelf(self, material_spec: MaterialSpec) -> None:
        """_draw_holes should not create holes for shelf panels."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=material_spec,
        )

        exporter._draw_holes(msp, piece, 0.0, 0.0, 24.0, 12.0)

        circles = list(msp.query("CIRCLE"))
        assert len(circles) == 0

    def test_no_holes_when_pattern_none(self, material_spec: MaterialSpec) -> None:
        """_draw_holes should not create holes when pattern is 'none'."""
        exporter = DxfExporter(hole_pattern="none")
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Left Side",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        )

        exporter._draw_holes(msp, piece, 0.0, 0.0, 12.0, 36.0)

        circles = list(msp.query("CIRCLE"))
        assert len(circles) == 0

    def test_hole_diameter_matches_setting(self, material_spec: MaterialSpec) -> None:
        """Holes should have the configured diameter."""
        exporter = DxfExporter(hole_diameter=0.25)
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Left Side",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        )

        exporter._draw_holes(msp, piece, 0.0, 0.0, 12.0, 36.0)

        circles = list(msp.query("CIRCLE"))
        assert len(circles) > 0
        # Check radius (diameter / 2)
        assert circles[0].dxf.radius == pytest.approx(0.125)


class TestDxfExporterDados:
    """Tests for dado cut drawing."""

    def test_draw_dados_horizontal(self, cut_piece_with_dados: CutPiece) -> None:
        """_draw_dados should create lines for horizontal dados."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        exporter._draw_dados(msp, cut_piece_with_dados, 0.0, 0.0, 12.0, 36.0)

        # Should have lines for each dado (2 lines per dado for top/bottom edges)
        lines = list(msp.query("LINE"))
        # 2 dados * 2 lines = 4 lines
        assert len(lines) == 4

        # Check lines are on DADOS layer
        for line in lines:
            assert line.dxf.layer == "DADOS"

    def test_draw_dados_vertical(self, material_spec: MaterialSpec) -> None:
        """_draw_dados should handle vertical dados."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=48.0,
            height=12.0,
            quantity=1,
            label="Top with Vertical Dado",
            panel_type=PanelType.TOP,
            material=material_spec,
            cut_metadata={
                "joinery": [
                    {
                        "type": "dado",
                        "position": 24.0,
                        "width": 0.75,
                        "depth": 0.375,
                        "orientation": "vertical",
                    },
                ]
            },
        )

        exporter._draw_dados(msp, piece, 0.0, 0.0, 48.0, 12.0)

        lines = list(msp.query("LINE"))
        # 1 dado * 2 lines = 2 lines
        assert len(lines) == 2

    def test_no_dados_without_metadata(self, material_spec: MaterialSpec) -> None:
        """_draw_dados should not draw anything without metadata."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,
            height=48.0,
            quantity=1,
            label="Plain Side",
            panel_type=PanelType.LEFT_SIDE,
            material=material_spec,
        )

        exporter._draw_dados(msp, piece, 0.0, 0.0, 24.0, 48.0)

        lines = list(msp.query("LINE"))
        assert len(lines) == 0


class TestDxfExporterLabels:
    """Tests for label drawing."""

    def test_draw_label_creates_mtext(self, material_spec: MaterialSpec) -> None:
        """_draw_label should create an MTEXT entity."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,
            height=48.0,
            quantity=1,
            label="Test Panel",
            panel_type=PanelType.SHELF,
            material=material_spec,
        )

        exporter._draw_label(msp, piece, 0.0, 0.0, 24.0, 48.0)

        mtexts = list(msp.query("MTEXT"))
        assert len(mtexts) == 1
        assert mtexts[0].dxf.layer == "LABELS"

    def test_label_contains_panel_label(self, material_spec: MaterialSpec) -> None:
        """Label text should contain the piece label."""
        exporter = DxfExporter()
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,
            height=48.0,
            quantity=1,
            label="My Custom Panel",
            panel_type=PanelType.SHELF,
            material=material_spec,
        )

        exporter._draw_label(msp, piece, 0.0, 0.0, 24.0, 48.0)

        mtexts = list(msp.query("MTEXT"))
        assert "My Custom Panel" in mtexts[0].text

    def test_label_contains_dimensions_inches(
        self, material_spec: MaterialSpec
    ) -> None:
        """Label should contain dimensions in inches format."""
        exporter = DxfExporter(units="inches")
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,
            height=48.0,
            quantity=1,
            label="Panel",
            panel_type=PanelType.SHELF,
            material=material_spec,
        )

        exporter._draw_label(msp, piece, 0.0, 0.0, 24.0, 48.0)

        mtexts = list(msp.query("MTEXT"))
        # Should contain inch format with quotes
        assert '"' in mtexts[0].text

    def test_label_contains_dimensions_mm(self, material_spec: MaterialSpec) -> None:
        """Label should contain dimensions in mm format."""
        exporter = DxfExporter(units="mm")
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,
            height=48.0,
            quantity=1,
            label="Panel",
            panel_type=PanelType.SHELF,
            material=material_spec,
        )

        # Scale dimensions for mm
        width_mm = 24.0 * 25.4
        height_mm = 48.0 * 25.4

        exporter._draw_label(msp, piece, 0.0, 0.0, width_mm, height_mm)

        mtexts = list(msp.query("MTEXT"))
        assert "mm" in mtexts[0].text


class TestDxfExporterUnitsConversion:
    """Tests for units conversion (inches to mm)."""

    def test_mm_scale_applied_to_dimensions(self, material_spec: MaterialSpec) -> None:
        """Panel dimensions should be scaled when using mm units."""
        exporter = DxfExporter(units="mm")
        doc = ezdxf.new("R2010")
        exporter._setup_layers(doc)
        msp = doc.modelspace()

        piece = CutPiece(
            width=24.0,  # inches
            height=48.0,  # inches
            quantity=1,
            label="Panel",
            panel_type=PanelType.SHELF,
            material=material_spec,
        )

        exporter._draw_panel(msp, piece, 0.0, 0.0)

        # Check the polyline dimensions are scaled
        polylines = list(msp.query("LWPOLYLINE"))
        assert len(polylines) == 1

        vertices = list(polylines[0].get_points())
        # Second vertex should be at width * 25.4 = 609.6mm
        assert vertices[1][0] == pytest.approx(24.0 * 25.4)
        # Third vertex height should be 48.0 * 25.4 = 1219.2mm
        assert vertices[2][1] == pytest.approx(48.0 * 25.4)


class TestDxfExporterCombinedMode:
    """Tests for combined mode export."""

    def test_export_combined_creates_single_file(
        self, layout_output: LayoutOutput
    ) -> None:
        """Combined mode should create a single DXF file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.dxf"
            exporter = DxfExporter(mode="combined")
            exporter.export(layout_output, path)

            assert path.exists()

    def test_export_combined_all_panels(
        self,
        sample_cut_pieces: list[CutPiece],
        simple_cabinet: Cabinet,
        material_spec: MaterialSpec,
    ) -> None:
        """Combined mode should include all panels from cut list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.dxf"

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=sample_cut_pieces,
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=32.0, sheets=1)
                },
                total_estimate=make_material_estimate(area_sqft=32.0, sheets=1),
            )

            exporter = DxfExporter(mode="combined")
            exporter.export(output, path)

            # Read the DXF and count panels
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()

            # Count polylines (one per panel instance)
            # 2 side panels + 1 top panel + 4 shelves = 7 total
            polylines = list(msp.query("LWPOLYLINE"))
            assert len(polylines) == 7


class TestDxfExporterPerPanelMode:
    """Tests for per-panel mode export."""

    def test_export_per_panel_creates_multiple_files(
        self,
        sample_cut_pieces: list[CutPiece],
        simple_cabinet: Cabinet,
        material_spec: MaterialSpec,
    ) -> None:
        """Per-panel mode should create separate files for each panel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.dxf"

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=sample_cut_pieces,
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=32.0, sheets=1)
                },
                total_estimate=make_material_estimate(area_sqft=32.0, sheets=1),
            )

            exporter = DxfExporter(mode="per_panel")
            exporter.export(output, path)

            # Check that multiple files were created
            dxf_files = list(Path(tmpdir).glob("test_*.dxf"))
            # Should have one file per unique panel label
            assert len(dxf_files) == 3  # Side Panel, Top Panel, Shelf

    def test_per_panel_filenames_use_labels(
        self,
        sample_cut_pieces: list[CutPiece],
        simple_cabinet: Cabinet,
        material_spec: MaterialSpec,
    ) -> None:
        """Per-panel files should be named using the panel labels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cabinet.dxf"

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=sample_cut_pieces,
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=32.0, sheets=1)
                },
                total_estimate=make_material_estimate(area_sqft=32.0, sheets=1),
            )

            exporter = DxfExporter(mode="per_panel")
            exporter.export(output, path)

            # Check for expected filenames (spaces replaced with underscores)
            assert (Path(tmpdir) / "cabinet_Side_Panel.dxf").exists()
            assert (Path(tmpdir) / "cabinet_Top_Panel.dxf").exists()
            assert (Path(tmpdir) / "cabinet_Shelf.dxf").exists()


class TestDxfExporterStringExport:
    """Tests for export_string method."""

    def test_export_string_returns_dxf_content(
        self, layout_output: LayoutOutput
    ) -> None:
        """export_string should return valid DXF content."""
        exporter = DxfExporter()
        result = exporter.export_string(layout_output)

        # DXF files start with "0\nSECTION"
        assert result.startswith("  0\nSECTION")
        # Should contain EOF marker
        assert "EOF" in result

    def test_export_string_empty_cut_list(
        self, simple_cabinet: Cabinet, material_spec: MaterialSpec
    ) -> None:
        """export_string should return empty string for empty cut list."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[],
            material_estimates={
                material_spec: make_material_estimate(area_sqft=0.0, sheets=0)
            },
            total_estimate=make_material_estimate(area_sqft=0.0, sheets=0),
        )

        exporter = DxfExporter()
        result = exporter.export_string(output)
        assert result == ""


class TestDxfExporterRoomLayoutOutput:
    """Tests for RoomLayoutOutput export."""

    def test_export_room_layout_output(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """Export should work with RoomLayoutOutput."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "room.dxf"
            exporter = DxfExporter()
            exporter.export(room_layout_output, path)

            assert path.exists()

    def test_export_string_room_layout_output(
        self, room_layout_output: RoomLayoutOutput
    ) -> None:
        """export_string should work with RoomLayoutOutput."""
        exporter = DxfExporter()
        result = exporter.export_string(room_layout_output)

        assert result.startswith("  0\nSECTION")


class TestDxfExporterEdgeCases:
    """Tests for edge cases and error handling."""

    def test_export_invalid_output_type(self) -> None:
        """Export should raise TypeError for invalid output type."""
        exporter = DxfExporter()
        with pytest.raises(TypeError) as exc_info:
            exporter.export("invalid", Path("/tmp/test.dxf"))  # type: ignore
        assert "Expected LayoutOutput or RoomLayoutOutput" in str(exc_info.value)

    def test_export_string_invalid_output_type(self) -> None:
        """export_string should raise TypeError for invalid output type."""
        exporter = DxfExporter()
        with pytest.raises(TypeError) as exc_info:
            exporter.export_string({"invalid": "data"})  # type: ignore
        assert "Expected LayoutOutput or RoomLayoutOutput" in str(exc_info.value)

    def test_export_empty_cut_list_no_file(
        self, simple_cabinet: Cabinet, material_spec: MaterialSpec
    ) -> None:
        """Export should not create file for empty cut list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.dxf"

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=[],
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=0.0, sheets=0)
                },
                total_estimate=make_material_estimate(area_sqft=0.0, sheets=0),
            )

            exporter = DxfExporter()
            exporter.export(output, path)

            # No file should be created for empty cut list
            assert not path.exists()

    def test_label_sanitization_in_per_panel_mode(
        self, simple_cabinet: Cabinet, material_spec: MaterialSpec
    ) -> None:
        """Panel labels with special characters should be sanitized in filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.dxf"

            cut_list = [
                CutPiece(
                    width=24.0,
                    height=48.0,
                    quantity=1,
                    label="Side/Panel 1",  # Contains slash and space
                    panel_type=PanelType.LEFT_SIDE,
                    material=material_spec,
                ),
            ]

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=cut_list,
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=8.0, sheets=1)
                },
                total_estimate=make_material_estimate(area_sqft=8.0, sheets=1),
            )

            exporter = DxfExporter(mode="per_panel")
            exporter.export(output, path)

            # Filename should have sanitized label
            expected_file = Path(tmpdir) / "test_Side-Panel_1.dxf"
            assert expected_file.exists()


class TestDxfExporterIntegration:
    """Integration tests for the complete export workflow."""

    def test_full_export_with_all_features(
        self,
        cut_piece_with_dados: CutPiece,
        simple_cabinet: Cabinet,
        material_spec: MaterialSpec,
    ) -> None:
        """Test complete export with dados, holes, and labels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "full_test.dxf"

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=[cut_piece_with_dados],
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=3.0, sheets=1)
                },
                total_estimate=make_material_estimate(area_sqft=3.0, sheets=1),
            )

            exporter = DxfExporter()
            exporter.export(output, path)

            # Read back and verify all components
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()

            # Should have outline
            assert len(list(msp.query("LWPOLYLINE"))) == 1

            # Should have dado lines
            lines = list(msp.query("LINE"))
            dados_lines = [line for line in lines if line.dxf.layer == "DADOS"]
            assert len(dados_lines) == 4  # 2 dados * 2 lines

            # Should have holes (side panel)
            circles = list(msp.query("CIRCLE"))
            assert len(circles) > 0

            # Should have label
            assert len(list(msp.query("MTEXT"))) == 1

    def test_export_with_mm_units_complete(
        self,
        sample_cut_pieces: list[CutPiece],
        simple_cabinet: Cabinet,
        material_spec: MaterialSpec,
    ) -> None:
        """Test complete export with mm units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mm_test.dxf"

            output = LayoutOutput(
                cabinet=simple_cabinet,
                cut_list=sample_cut_pieces,
                material_estimates={
                    material_spec: make_material_estimate(area_sqft=32.0, sheets=1)
                },
                total_estimate=make_material_estimate(area_sqft=32.0, sheets=1),
            )

            exporter = DxfExporter(units="mm")
            exporter.export(output, path)

            assert path.exists()

            # Verify dimensions are scaled
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()

            polylines = list(msp.query("LWPOLYLINE"))
            assert len(polylines) > 0

            # First polyline should have mm-scaled dimensions
            vertices = list(polylines[0].get_points())
            # Check that dimensions are larger than inches would be
            # Original: 24" x 48", in mm: ~609.6 x 1219.2
            max_x = max(v[0] for v in vertices)
            assert max_x > 500  # Should be in mm range, not inches
