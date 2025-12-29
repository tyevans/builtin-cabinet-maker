"""Unit tests for the Bill of Materials (BOM) Generator.

Tests cover:
- BOM data model creation and properties
- Sheet goods calculation
- Hardware extraction
- Edge banding calculation
- Text format output
- CSV format output
- JSON format output
- Cost estimation
- File export functionality
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from cabinets.domain.components.results import HardwareItem
from cabinets.domain.value_objects import CutPiece, MaterialSpec, MaterialType, PanelType
from cabinets.infrastructure.exporters.bom import (
    BillOfMaterials,
    BomGenerator,
    EdgeBandingItem,
    HardwareBomItem,
    SheetGoodItem,
    VISIBLE_EDGES,
)


# --- Fixtures ---


@pytest.fixture
def sample_material() -> MaterialSpec:
    """Create a sample material specification."""
    return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sample_back_material() -> MaterialSpec:
    """Create a sample back panel material specification."""
    return MaterialSpec(thickness=0.25, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sample_cut_list(sample_material: MaterialSpec, sample_back_material: MaterialSpec) -> list[CutPiece]:
    """Create a sample cut list with various panel types."""
    return [
        CutPiece(
            width=11.25,
            height=84.0,
            quantity=2,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=sample_material,
        ),
        CutPiece(
            width=46.5,
            height=11.25,
            quantity=2,
            label="Top/Bottom Panel",
            panel_type=PanelType.TOP,
            material=sample_material,
        ),
        CutPiece(
            width=46.5,
            height=15.0,
            quantity=3,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=sample_material,
        ),
        CutPiece(
            width=47.25,
            height=83.25,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=sample_back_material,
        ),
    ]


@pytest.fixture
def sample_hardware() -> list[HardwareItem]:
    """Create a sample hardware list."""
    return [
        HardwareItem(
            name="#8 x 1-1/4\" wood screw",
            quantity=24,
            sku="WS-812",
            notes="Case assembly",
        ),
        HardwareItem(
            name="#6 x 5/8\" pan head screw",
            quantity=36,
            sku="PS-658",
            notes="Back panel attachment",
        ),
        HardwareItem(
            name="5mm shelf pin",
            quantity=20,
            sku="SP-5MM",
            notes="Adjustable shelf support",
        ),
        HardwareItem(
            name="European cup hinge 35mm",
            quantity=4,
            sku="ECH-35",
            notes="Door mounting",
        ),
    ]


@pytest.fixture
def mock_layout_output(
    sample_cut_list: list[CutPiece],
    sample_hardware: list[HardwareItem],
) -> MagicMock:
    """Create a mock LayoutOutput object."""
    mock = MagicMock()
    mock.cut_list = sample_cut_list
    mock.hardware = sample_hardware
    mock.packing_result = None
    return mock


@pytest.fixture
def mock_room_layout_output(sample_cut_list: list[CutPiece]) -> MagicMock:
    """Create a mock RoomLayoutOutput object."""
    mock = MagicMock()
    mock.cut_list = sample_cut_list
    # RoomLayoutOutput doesn't have hardware directly
    return mock


# --- SheetGoodItem Tests ---


class TestSheetGoodItem:
    """Tests for SheetGoodItem data model."""

    def test_creation(self) -> None:
        """Test basic SheetGoodItem creation."""
        item = SheetGoodItem(
            material="Plywood",
            thickness=0.75,
            sheet_size=(48.0, 96.0),
            quantity=2,
            square_feet=24.5,
        )

        assert item.material == "Plywood"
        assert item.thickness == 0.75
        assert item.sheet_size == (48.0, 96.0)
        assert item.quantity == 2
        assert item.square_feet == 24.5
        assert item.unit_cost is None

    def test_total_cost_with_unit_cost(self) -> None:
        """Test total cost calculation when unit cost is provided."""
        item = SheetGoodItem(
            material="Plywood",
            thickness=0.75,
            sheet_size=(48.0, 96.0),
            quantity=3,
            square_feet=30.0,
            unit_cost=45.00,
        )

        assert item.total_cost == 135.00

    def test_total_cost_without_unit_cost(self) -> None:
        """Test total cost is None when unit cost is not provided."""
        item = SheetGoodItem(
            material="Plywood",
            thickness=0.75,
            sheet_size=(48.0, 96.0),
            quantity=2,
            square_feet=24.5,
        )

        assert item.total_cost is None

    def test_sheet_area_sqft(self) -> None:
        """Test sheet area calculation in square feet."""
        item = SheetGoodItem(
            material="Plywood",
            thickness=0.75,
            sheet_size=(48.0, 96.0),
            quantity=1,
            square_feet=24.0,
        )

        # 48 x 96 = 4608 sq in / 144 = 32 sq ft
        assert item.sheet_area_sqft == 32.0

    def test_immutability(self) -> None:
        """Test that SheetGoodItem is immutable."""
        item = SheetGoodItem(
            material="Plywood",
            thickness=0.75,
            sheet_size=(48.0, 96.0),
            quantity=2,
            square_feet=24.5,
        )

        with pytest.raises(AttributeError):
            item.quantity = 5  # type: ignore


# --- EdgeBandingItem Tests ---


class TestEdgeBandingItem:
    """Tests for EdgeBandingItem data model."""

    def test_creation(self) -> None:
        """Test basic EdgeBandingItem creation."""
        item = EdgeBandingItem(
            material="Maple",
            thickness="3/4 inch",
            color="Natural",
            linear_feet=24.5,
        )

        assert item.material == "Maple"
        assert item.thickness == "3/4 inch"
        assert item.color == "Natural"
        assert item.linear_feet == 24.5
        assert item.unit_cost is None

    def test_total_cost_with_unit_cost(self) -> None:
        """Test total cost calculation for edge banding."""
        item = EdgeBandingItem(
            material="Oak",
            thickness="1/4 inch",
            color="Golden Oak",
            linear_feet=50.0,
            unit_cost=0.25,  # $0.25 per linear foot
        )

        assert item.total_cost == 12.50


# --- HardwareBomItem Tests ---


class TestHardwareBomItem:
    """Tests for HardwareBomItem data model."""

    def test_creation(self) -> None:
        """Test basic HardwareBomItem creation."""
        item = HardwareBomItem(
            name="Wood Screw",
            size="1-1/4 inch",
            quantity=100,
            category="fasteners",
        )

        assert item.name == "Wood Screw"
        assert item.size == "1-1/4 inch"
        assert item.quantity == 100
        assert item.category == "fasteners"
        assert item.sku == ""
        assert item.unit_cost is None

    def test_total_cost_with_unit_cost(self) -> None:
        """Test total cost calculation for hardware."""
        item = HardwareBomItem(
            name="European Hinge",
            size="35mm",
            quantity=4,
            category="hinges",
            unit_cost=5.50,
        )

        assert item.total_cost == 22.00

    def test_with_sku(self) -> None:
        """Test HardwareBomItem with SKU."""
        item = HardwareBomItem(
            name="Pocket Screw",
            size="1-1/4 inch",
            quantity=50,
            category="fasteners",
            sku="KR-PSCR-125",
        )

        assert item.sku == "KR-PSCR-125"


# --- BillOfMaterials Tests ---


class TestBillOfMaterials:
    """Tests for BillOfMaterials data model."""

    def test_empty_bom(self) -> None:
        """Test empty BOM creation."""
        bom = BillOfMaterials()

        assert bom.sheet_goods == ()
        assert bom.hardware == ()
        assert bom.edge_banding == ()
        assert bom.total_cost is None

    def test_bom_with_items(self) -> None:
        """Test BOM with all item types."""
        sheet_goods = (
            SheetGoodItem(
                material="Plywood",
                thickness=0.75,
                sheet_size=(48.0, 96.0),
                quantity=2,
                square_feet=24.0,
                unit_cost=50.00,
            ),
        )
        hardware = (
            HardwareBomItem(
                name="Screw",
                size="1 inch",
                quantity=100,
                category="fasteners",
                unit_cost=0.05,
            ),
        )
        edge_banding = (
            EdgeBandingItem(
                material="Maple",
                thickness="3/4 inch",
                color="Natural",
                linear_feet=25.0,
                unit_cost=0.30,
            ),
        )

        bom = BillOfMaterials(
            sheet_goods=sheet_goods,
            hardware=hardware,
            edge_banding=edge_banding,
        )

        # Sheet goods: 2 * $50 = $100
        # Hardware: 100 * $0.05 = $5
        # Edge banding: 25 * $0.30 = $7.50
        # Total: $112.50
        assert bom.total_cost == 112.50
        assert bom.sheet_goods_cost == 100.00
        assert bom.hardware_cost == 5.00
        assert bom.edge_banding_cost == 7.50

    def test_partial_cost_data(self) -> None:
        """Test BOM with only some items having costs."""
        sheet_goods = (
            SheetGoodItem(
                material="Plywood",
                thickness=0.75,
                sheet_size=(48.0, 96.0),
                quantity=2,
                square_feet=24.0,
                unit_cost=50.00,
            ),
        )
        hardware = (
            HardwareBomItem(
                name="Screw",
                size="1 inch",
                quantity=100,
                category="fasteners",
                # No unit_cost
            ),
        )

        bom = BillOfMaterials(
            sheet_goods=sheet_goods,
            hardware=hardware,
        )

        # Only sheet goods have cost
        assert bom.total_cost == 100.00
        assert bom.hardware_cost is None


# --- BomGenerator Tests ---


class TestBomGenerator:
    """Tests for BomGenerator class."""

    def test_default_initialization(self) -> None:
        """Test default BomGenerator initialization."""
        generator = BomGenerator()

        assert generator.output_format == "text"
        assert generator.include_costs is False
        assert generator.sheet_size == (48.0, 96.0)
        assert generator.file_extension == "txt"

    def test_csv_format_initialization(self) -> None:
        """Test BomGenerator with CSV format."""
        generator = BomGenerator(output_format="csv")

        assert generator.output_format == "csv"
        assert generator.file_extension == "csv"

    def test_json_format_initialization(self) -> None:
        """Test BomGenerator with JSON format."""
        generator = BomGenerator(output_format="json")

        assert generator.output_format == "json"
        assert generator.file_extension == "json"

    def test_generate_bom(self, mock_layout_output: MagicMock) -> None:
        """Test BOM generation from layout output."""
        generator = BomGenerator()
        bom = generator.generate(mock_layout_output)

        assert isinstance(bom, BillOfMaterials)
        assert len(bom.sheet_goods) > 0
        assert len(bom.hardware) > 0

    def test_generate_sheet_goods(
        self,
        mock_layout_output: MagicMock,
        sample_material: MaterialSpec,
    ) -> None:
        """Test sheet goods calculation."""
        generator = BomGenerator()
        bom = generator.generate(mock_layout_output)

        # Should have sheet goods for both main and back materials
        assert len(bom.sheet_goods) == 2

        # Find the main material
        main_sheet = next(
            (s for s in bom.sheet_goods if s.thickness == 0.75),
            None,
        )
        assert main_sheet is not None
        assert main_sheet.material == "Plywood"
        assert main_sheet.quantity >= 1

    def test_extract_hardware(
        self,
        mock_layout_output: MagicMock,
        sample_hardware: list[HardwareItem],
    ) -> None:
        """Test hardware extraction from layout output."""
        generator = BomGenerator()
        bom = generator.generate(mock_layout_output)

        assert len(bom.hardware) == len(sample_hardware)

        # Check that categories were assigned
        screw_items = [h for h in bom.hardware if h.category == "fasteners"]
        hinge_items = [h for h in bom.hardware if h.category == "hinges"]
        pin_items = [h for h in bom.hardware if h.category == "shelf_supports"]

        assert len(screw_items) >= 2  # Wood screws and pan head screws
        assert len(hinge_items) == 1  # European cup hinge
        assert len(pin_items) == 1  # Shelf pins

    def test_calculate_edge_banding(
        self,
        mock_layout_output: MagicMock,
        sample_material: MaterialSpec,
    ) -> None:
        """Test edge banding calculation."""
        generator = BomGenerator()
        bom = generator.generate(mock_layout_output)

        # Should have edge banding for visible edges
        assert len(bom.edge_banding) > 0

        # Check that linear feet is calculated
        total_linear_feet = sum(e.linear_feet for e in bom.edge_banding)
        assert total_linear_feet > 0

    def test_edge_banding_panels_included(self) -> None:
        """Test that correct panels are included in edge banding."""
        # Side panels have front edge
        assert "front" in VISIBLE_EDGES.get("left_side", [])
        assert "front" in VISIBLE_EDGES.get("right_side", [])

        # Shelves have front edge
        assert "front" in VISIBLE_EDGES.get("shelf", [])

        # Doors have all edges
        door_edges = VISIBLE_EDGES.get("door", [])
        assert "top" in door_edges
        assert "bottom" in door_edges
        assert "left" in door_edges
        assert "right" in door_edges

        # Back panel has no visible edges
        assert "back" not in VISIBLE_EDGES


class TestBomGeneratorFormatText:
    """Tests for text format output."""

    def test_format_text_basic(self, mock_layout_output: MagicMock) -> None:
        """Test basic text format output."""
        generator = BomGenerator(output_format="text")
        output = generator.export_string(mock_layout_output)

        assert "BILL OF MATERIALS" in output
        assert "SHEET GOODS" in output
        assert "HARDWARE" in output
        assert "EDGE BANDING" in output

    def test_format_text_with_costs(self, mock_layout_output: MagicMock) -> None:
        """Test text format with costs enabled."""
        generator = BomGenerator(output_format="text", include_costs=True)
        output = generator.export_string(mock_layout_output)

        # Costs section should not appear if no unit costs are provided
        # (since our mock data doesn't have costs)
        assert "BILL OF MATERIALS" in output

    def test_format_text_sheet_goods_details(
        self,
        mock_layout_output: MagicMock,
    ) -> None:
        """Test that sheet goods details are in text output."""
        generator = BomGenerator(output_format="text")
        output = generator.export_string(mock_layout_output)

        assert "Plywood" in output
        assert "sheet(s)" in output
        assert "sq ft" in output


class TestBomGeneratorFormatCsv:
    """Tests for CSV format output."""

    def test_format_csv_basic(self, mock_layout_output: MagicMock) -> None:
        """Test basic CSV format output."""
        generator = BomGenerator(output_format="csv")
        output = generator.export_string(mock_layout_output)

        # Check header row
        lines = output.strip().split("\n")
        assert len(lines) > 1  # Header + data rows

        header = lines[0]
        assert "Category" in header
        assert "Item" in header
        assert "Quantity" in header

    def test_format_csv_with_costs(self, mock_layout_output: MagicMock) -> None:
        """Test CSV format with costs columns."""
        generator = BomGenerator(output_format="csv", include_costs=True)
        output = generator.export_string(mock_layout_output)

        lines = output.strip().split("\n")
        header = lines[0]
        assert "Unit Cost" in header
        assert "Total Cost" in header

    def test_format_csv_parseable(self, mock_layout_output: MagicMock) -> None:
        """Test that CSV output is parseable."""
        import csv
        import io

        generator = BomGenerator(output_format="csv")
        output = generator.export_string(mock_layout_output)

        reader = csv.reader(io.StringIO(output))
        rows = list(reader)

        assert len(rows) > 1  # Header + data
        header = rows[0]
        assert len(header) >= 5  # Category, Item, Size, Quantity, Unit


class TestBomGeneratorFormatJson:
    """Tests for JSON format output."""

    def test_format_json_basic(self, mock_layout_output: MagicMock) -> None:
        """Test basic JSON format output."""
        generator = BomGenerator(output_format="json")
        output = generator.export_string(mock_layout_output)

        # Should be valid JSON
        data = json.loads(output)

        assert "sheet_goods" in data
        assert "hardware" in data
        assert "edge_banding" in data

    def test_format_json_structure(self, mock_layout_output: MagicMock) -> None:
        """Test JSON structure for sheet goods."""
        generator = BomGenerator(output_format="json")
        output = generator.export_string(mock_layout_output)

        data = json.loads(output)

        # Check sheet goods structure
        assert len(data["sheet_goods"]) > 0
        sheet = data["sheet_goods"][0]
        assert "material" in sheet
        assert "thickness" in sheet
        assert "sheet_size" in sheet
        assert "width" in sheet["sheet_size"]
        assert "height" in sheet["sheet_size"]
        assert "quantity" in sheet
        assert "square_feet" in sheet

    def test_format_json_with_costs(self, mock_layout_output: MagicMock) -> None:
        """Test JSON format with costs included."""
        generator = BomGenerator(output_format="json", include_costs=True)
        output = generator.export_string(mock_layout_output)

        data = json.loads(output)

        assert "cost_summary" in data
        cost_summary = data["cost_summary"]
        assert "sheet_goods" in cost_summary
        assert "hardware" in cost_summary
        assert "edge_banding" in cost_summary
        assert "total" in cost_summary


class TestBomGeneratorFileExport:
    """Tests for file export functionality."""

    def test_export_to_file(self, mock_layout_output: MagicMock) -> None:
        """Test exporting BOM to file."""
        generator = BomGenerator(output_format="text")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "bom.txt"
            generator.export(mock_layout_output, filepath)

            assert filepath.exists()
            content = filepath.read_text()
            assert "BILL OF MATERIALS" in content

    def test_export_csv_to_file(self, mock_layout_output: MagicMock) -> None:
        """Test exporting CSV BOM to file."""
        generator = BomGenerator(output_format="csv")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "bom.csv"
            generator.export(mock_layout_output, filepath)

            assert filepath.exists()
            content = filepath.read_text()
            assert "Category" in content

    def test_export_json_to_file(self, mock_layout_output: MagicMock) -> None:
        """Test exporting JSON BOM to file."""
        generator = BomGenerator(output_format="json")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "bom.json"
            generator.export(mock_layout_output, filepath)

            assert filepath.exists()
            content = filepath.read_text()
            data = json.loads(content)
            assert "sheet_goods" in data


class TestBomGeneratorRegistration:
    """Tests for exporter registry integration."""

    def test_registered_in_registry(self) -> None:
        """Test that BomGenerator is registered in ExporterRegistry."""
        from cabinets.infrastructure.exporters import ExporterRegistry

        assert ExporterRegistry.is_registered("bom")

    def test_available_formats_includes_bom(self) -> None:
        """Test that 'bom' appears in available formats."""
        from cabinets.infrastructure.exporters import ExporterRegistry

        formats = ExporterRegistry.available_formats()
        assert "bom" in formats

    def test_get_bom_exporter(self) -> None:
        """Test getting BomGenerator from registry."""
        from cabinets.infrastructure.exporters import ExporterRegistry

        exporter_cls = ExporterRegistry.get("bom")
        assert exporter_cls is BomGenerator


class TestBomGeneratorRoomLayout:
    """Tests for RoomLayoutOutput handling."""

    def test_generate_from_room_output(
        self,
        mock_room_layout_output: MagicMock,
    ) -> None:
        """Test BOM generation from RoomLayoutOutput."""
        generator = BomGenerator()
        bom = generator.generate(mock_room_layout_output)

        assert isinstance(bom, BillOfMaterials)
        assert len(bom.sheet_goods) > 0


class TestBomGeneratorEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_cut_list(self) -> None:
        """Test handling of empty cut list."""
        mock = MagicMock()
        mock.cut_list = []
        mock.hardware = []

        generator = BomGenerator()
        bom = generator.generate(mock)

        assert bom.sheet_goods == ()
        assert bom.hardware == ()
        assert bom.edge_banding == ()

    def test_no_visible_edges(self) -> None:
        """Test panel type with no visible edges."""
        material = MaterialSpec(thickness=0.25, material_type=MaterialType.PLYWOOD)
        cut_list = [
            CutPiece(
                width=48.0,
                height=84.0,
                quantity=1,
                label="Back Panel",
                panel_type=PanelType.BACK,
                material=material,
            ),
        ]

        mock = MagicMock()
        mock.cut_list = cut_list
        mock.hardware = []

        generator = BomGenerator()
        bom = generator.generate(mock)

        # Back panel has no visible edges
        assert len(bom.edge_banding) == 0

    def test_custom_sheet_size(self, mock_layout_output: MagicMock) -> None:
        """Test using custom sheet size."""
        generator = BomGenerator(sheet_size=(60.0, 60.0))  # 5x5 Baltic birch
        bom = generator.generate(mock_layout_output)

        for sheet in bom.sheet_goods:
            assert sheet.sheet_size == (60.0, 60.0)

    def test_size_extraction_from_hardware_name(self) -> None:
        """Test size extraction from various hardware name formats."""
        generator = BomGenerator()

        # Test various size formats
        test_cases = [
            ("#8 x 1-1/4\" wood screw", "#8 x 1-1/4\""),
            ("1-1/4 inch pocket screw", "1-1/4 inch"),
            ("35mm European hinge", "35mm"),
            ("Wood screw", ""),  # No size in name
        ]

        for name, expected_size in test_cases:
            result = generator._extract_size_from_name(name)
            assert result == expected_size, f"Failed for: {name}"

    def test_thickness_formatting(self) -> None:
        """Test thickness formatting to fractions."""
        generator = BomGenerator()

        assert generator._format_thickness(0.25) == "1/4 inch"
        assert generator._format_thickness(0.5) == "1/2 inch"
        assert generator._format_thickness(0.75) == "3/4 inch"
        assert generator._format_thickness(1.0) == "1 inch"
        assert generator._format_thickness(0.625) == "5/8 inch"
        # Non-standard thickness uses decimal
        assert '0.333"' in generator._format_thickness(0.333)

    def test_hardware_consolidation(self) -> None:
        """Test that duplicate hardware items are consolidated by summing quantities."""
        # Create hardware list with duplicates
        hardware_with_duplicates = [
            HardwareItem(
                name="#8 x 1-1/4\" wood screw",
                quantity=24,
                sku="WS-812",
                notes="Cabinet 1",
            ),
            HardwareItem(
                name="#8 x 1-1/4\" wood screw",
                quantity=24,
                sku="WS-812",
                notes="Cabinet 2",
            ),
            HardwareItem(
                name="#8 x 1-1/4\" wood screw",
                quantity=12,
                sku="WS-812",
                notes="Cabinet 3",
            ),
            HardwareItem(
                name="5mm shelf pin",
                quantity=20,
                sku="SP-5MM",
                notes="Cabinet 1",
            ),
            HardwareItem(
                name="5mm shelf pin",
                quantity=16,
                sku="SP-5MM",
                notes="Cabinet 2",
            ),
        ]

        mock = MagicMock()
        mock.cut_list = []
        mock.hardware = hardware_with_duplicates

        generator = BomGenerator()
        bom = generator.generate(mock)

        # Should have only 2 unique hardware items, not 5
        assert len(bom.hardware) == 2

        # Find the consolidated screw item
        screw_item = next(
            (h for h in bom.hardware if "wood screw" in h.name),
            None,
        )
        assert screw_item is not None
        assert screw_item.quantity == 60  # 24 + 24 + 12

        # Find the consolidated shelf pin item
        pin_item = next(
            (h for h in bom.hardware if "shelf pin" in h.name),
            None,
        )
        assert pin_item is not None
        assert pin_item.quantity == 36  # 20 + 16
