"""Unit tests for SVG exporter (FRD-16 Phase 7)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cabinets.domain.value_objects import CutPiece, MaterialSpec, MaterialType, PanelType
from cabinets.infrastructure.bin_packing import (
    PackingResult,
    PlacedPiece,
    SheetConfig,
    SheetLayout,
)
from cabinets.infrastructure.exporters import SvgExporter, ExporterRegistry


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Standard 3/4 inch plywood."""
    return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sheet_config() -> SheetConfig:
    """Standard 4x8 sheet."""
    return SheetConfig(width=48, height=96, edge_allowance=0.5)


@pytest.fixture
def sample_piece(standard_material: MaterialSpec) -> CutPiece:
    """Sample cut piece for testing."""
    return CutPiece(
        width=24.0,
        height=48.0,
        quantity=1,
        label="Side Panel",
        panel_type=PanelType.LEFT_SIDE,
        material=standard_material,
    )


@pytest.fixture
def sample_placement(sample_piece: CutPiece) -> PlacedPiece:
    """Sample placed piece at origin."""
    return PlacedPiece(piece=sample_piece, x=0.0, y=0.0, rotated=False)


@pytest.fixture
def sample_layout(
    sheet_config: SheetConfig,
    standard_material: MaterialSpec,
    sample_placement: PlacedPiece,
) -> SheetLayout:
    """Sample sheet layout with one piece."""
    return SheetLayout(
        sheet_index=0,
        sheet_config=sheet_config,
        placements=(sample_placement,),
        material=standard_material,
    )


@pytest.fixture
def sample_packing_result(
    sample_layout: SheetLayout,
    standard_material: MaterialSpec,
) -> PackingResult:
    """Sample packing result for testing."""
    return PackingResult(
        layouts=(sample_layout,),
        offcuts=(),
        total_waste_percentage=50.0,
        sheets_by_material={standard_material: 1},
    )


class TestSvgExporterRegistration:
    """Tests for SVG exporter registration."""

    def test_is_registered(self) -> None:
        """SvgExporter is registered with 'svg' format name."""
        assert ExporterRegistry.is_registered("svg")

    def test_get_returns_svg_exporter(self) -> None:
        """ExporterRegistry.get('svg') returns SvgExporter."""
        assert ExporterRegistry.get("svg") is SvgExporter

    def test_format_name(self) -> None:
        """SvgExporter has format_name 'svg'."""
        assert SvgExporter.format_name == "svg"

    def test_file_extension(self) -> None:
        """SvgExporter has file_extension 'svg'."""
        assert SvgExporter.file_extension == "svg"

    def test_in_available_formats(self) -> None:
        """'svg' is in the list of available formats."""
        formats = ExporterRegistry.available_formats()
        assert "svg" in formats


class TestSvgExporterConfiguration:
    """Tests for SVG exporter configuration."""

    def test_default_configuration(self) -> None:
        """Default configuration has expected values."""
        exporter = SvgExporter()
        renderer = exporter.renderer
        assert renderer.scale == 10.0
        assert renderer.show_dimensions is True
        assert renderer.show_labels is True
        assert renderer.show_grain is False
        assert renderer.use_panel_colors is True

    def test_custom_configuration(self) -> None:
        """Custom configuration is passed to renderer."""
        exporter = SvgExporter(
            scale=5.0,
            show_dimensions=False,
            show_labels=False,
            show_grain=True,
            use_panel_colors=False,
        )
        renderer = exporter.renderer
        assert renderer.scale == 5.0
        assert renderer.show_dimensions is False
        assert renderer.show_labels is False
        assert renderer.show_grain is True
        assert renderer.use_panel_colors is False


class TestSvgExporterExport:
    """Tests for SVG export functionality."""

    def test_export_creates_file(
        self, sample_packing_result: PackingResult
    ) -> None:
        """export() creates SVG file."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.svg"
            exporter = SvgExporter()
            exporter.export(mock_output, path)

            assert path.exists()
            content = path.read_text()
            assert content.startswith("<svg")
            assert content.endswith("</svg>")

    def test_export_valid_svg(
        self, sample_packing_result: PackingResult
    ) -> None:
        """Exported SVG is valid XML."""
        import xml.etree.ElementTree as ET
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.svg"
            exporter = SvgExporter()
            exporter.export(mock_output, path)

            content = path.read_text()
            root = ET.fromstring(content)
            assert root.tag == "{http://www.w3.org/2000/svg}svg"

    def test_export_without_packing_result_raises(self) -> None:
        """export() raises ValueError without packing result."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: None = None

        mock_output = MockOutput()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.svg"
            exporter = SvgExporter()

            with pytest.raises(ValueError) as exc_info:
                exporter.export(mock_output, path)
            assert "bin packing" in str(exc_info.value).lower()


class TestSvgExporterExportString:
    """Tests for SVG string export functionality."""

    def test_export_string_returns_svg(
        self, sample_packing_result: PackingResult
    ) -> None:
        """export_string() returns SVG content."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        exporter = SvgExporter()
        svg = exporter.export_string(mock_output)

        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_export_string_valid_xml(
        self, sample_packing_result: PackingResult
    ) -> None:
        """export_string() returns valid XML."""
        import xml.etree.ElementTree as ET
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        exporter = SvgExporter()
        svg = exporter.export_string(mock_output)

        root = ET.fromstring(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"

    def test_export_string_without_packing_result_raises(self) -> None:
        """export_string() raises ValueError without packing result."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: None = None

        mock_output = MockOutput()
        exporter = SvgExporter()

        with pytest.raises(ValueError) as exc_info:
            exporter.export_string(mock_output)
        assert "bin packing" in str(exc_info.value).lower()


class TestSvgExporterIndividualSheets:
    """Tests for individual sheet export."""

    def test_export_individual_sheets_single(
        self, sample_packing_result: PackingResult
    ) -> None:
        """export_individual_sheets() creates single file for single sheet."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "sheet.svg"
            exporter = SvgExporter()
            files = exporter.export_individual_sheets(mock_output, base_path)

            assert len(files) == 1
            assert files[0] == base_path
            assert base_path.exists()

    def test_export_individual_sheets_multiple(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        sample_placement: PlacedPiece,
    ) -> None:
        """export_individual_sheets() creates numbered files for multiple sheets."""
        from dataclasses import dataclass

        layout1 = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        layout2 = SheetLayout(
            sheet_index=1,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        result = PackingResult(
            layouts=(layout1, layout2),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 2},
        )

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=result)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "sheet.svg"
            exporter = SvgExporter()
            files = exporter.export_individual_sheets(mock_output, base_path)

            assert len(files) == 2
            assert files[0] == Path(tmpdir) / "sheet_1.svg"
            assert files[1] == Path(tmpdir) / "sheet_2.svg"
            assert files[0].exists()
            assert files[1].exists()

    def test_export_individual_sheets_without_packing_raises(self) -> None:
        """export_individual_sheets() raises ValueError without packing result."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: None = None

        mock_output = MockOutput()

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "sheet.svg"
            exporter = SvgExporter()

            with pytest.raises(ValueError) as exc_info:
                exporter.export_individual_sheets(mock_output, base_path)
            assert "bin packing" in str(exc_info.value).lower()


class TestSvgExporterContent:
    """Tests for SVG content generation."""

    def test_contains_piece_label(
        self, sample_packing_result: PackingResult
    ) -> None:
        """Generated SVG contains piece labels."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        exporter = SvgExporter()
        svg = exporter.export_string(mock_output)

        assert "Side Panel" in svg

    def test_contains_piece_dimensions(
        self, sample_packing_result: PackingResult
    ) -> None:
        """Generated SVG contains piece dimensions."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        exporter = SvgExporter()
        svg = exporter.export_string(mock_output)

        assert '24.0" x 48.0"' in svg

    def test_contains_sheet_header(
        self, sample_packing_result: PackingResult
    ) -> None:
        """Generated SVG contains sheet header information."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: PackingResult

        mock_output = MockOutput(packing_result=sample_packing_result)

        exporter = SvgExporter()
        svg = exporter.export_string(mock_output)

        assert "Sheet 1" in svg
        assert "plywood" in svg.lower()
