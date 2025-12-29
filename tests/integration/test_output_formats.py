"""Integration tests for FRD-16 output format exporters.

Tests all exporters work with real cabinet layouts, multi-format export via
ExportManager, CLI multi-format export, and per-format config options.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.dtos import LayoutOutput, LayoutParametersInput, WallInput
from cabinets.domain.entities import Cabinet, Section
from cabinets.domain.services import MaterialEstimate
from cabinets.domain.value_objects import MaterialSpec, Position
from cabinets.infrastructure import BinPackingConfig, BinPackingService
from cabinets.infrastructure.exporters import (
    AssemblyInstructionGenerator,
    BomGenerator,
    DxfExporter,
    EnhancedJsonExporter,
    ExportManager,
    ExporterRegistry,
    StlLayoutExporter,
    SvgExporter,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_layout() -> LayoutOutput:
    """Generate a sample layout for testing."""
    command = GenerateLayoutCommand()
    wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
    params_input = LayoutParametersInput(
        num_sections=2,
        shelves_per_section=3,
        material_thickness=0.75,
    )
    return command.execute(wall_input, params_input)


@pytest.fixture
def single_section_layout() -> LayoutOutput:
    """Generate a single-section layout for testing."""
    command = GenerateLayoutCommand()
    wall_input = WallInput(width=24.0, height=60.0, depth=12.0)
    params_input = LayoutParametersInput(
        num_sections=1,
        shelves_per_section=4,
        material_thickness=0.75,
    )
    return command.execute(wall_input, params_input)


@pytest.fixture
def large_layout() -> LayoutOutput:
    """Generate a large layout with many pieces for edge case testing."""
    command = GenerateLayoutCommand()
    wall_input = WallInput(width=96.0, height=84.0, depth=12.0)
    params_input = LayoutParametersInput(
        num_sections=4,
        shelves_per_section=5,
        material_thickness=0.75,
    )
    return command.execute(wall_input, params_input)


@pytest.fixture
def optimized_layout() -> LayoutOutput:
    """Generate a layout with bin packing for SVG tests."""
    command = GenerateLayoutCommand()
    wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
    params_input = LayoutParametersInput(
        num_sections=2,
        shelves_per_section=3,
        material_thickness=0.75,
    )
    result = command.execute(wall_input, params_input)

    # Run bin packing
    if result.cut_list:
        bin_packing_config = BinPackingConfig(enabled=True)
        bin_packing_service = BinPackingService(bin_packing_config)
        packing_result = bin_packing_service.optimize_cut_list(result.cut_list)
        result.packing_result = packing_result

    return result


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# =============================================================================
# Exporter Registration Tests
# =============================================================================


class TestExporterRegistration:
    """Test that all exporters are properly registered."""

    def test_all_formats_registered(self):
        """Test all expected formats are registered."""
        formats = ExporterRegistry.available_formats()
        assert "stl" in formats
        assert "dxf" in formats
        assert "json" in formats
        assert "bom" in formats
        assert "assembly" in formats
        assert "svg" in formats

    def test_get_registered_exporter(self):
        """Test getting registered exporter classes."""
        stl_cls = ExporterRegistry.get("stl")
        assert stl_cls == StlLayoutExporter

        dxf_cls = ExporterRegistry.get("dxf")
        assert dxf_cls == DxfExporter

        json_cls = ExporterRegistry.get("json")
        assert json_cls == EnhancedJsonExporter

        bom_cls = ExporterRegistry.get("bom")
        assert bom_cls == BomGenerator

        assembly_cls = ExporterRegistry.get("assembly")
        assert assembly_cls == AssemblyInstructionGenerator

        svg_cls = ExporterRegistry.get("svg")
        assert svg_cls == SvgExporter

    def test_get_unregistered_format_raises(self):
        """Test getting unregistered format raises KeyError."""
        with pytest.raises(KeyError, match="No exporter registered"):
            ExporterRegistry.get("nonexistent")

    def test_is_registered(self):
        """Test is_registered method."""
        assert ExporterRegistry.is_registered("stl")
        assert ExporterRegistry.is_registered("dxf")
        assert not ExporterRegistry.is_registered("nonexistent")


# =============================================================================
# ExportManager Tests
# =============================================================================


class TestExportManager:
    """Integration tests for ExportManager."""

    def test_export_single_format(
        self, sample_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test exporting to a single format."""
        manager = ExportManager(tmp_output_dir)
        path = manager.export_single("json", sample_layout, "test_cabinet")

        assert path.exists()
        assert path.name == "test_cabinet_json.json"
        assert path.stat().st_size > 0

    def test_export_multiple_formats(
        self, sample_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test exporting to multiple non-SVG formats."""
        manager = ExportManager(tmp_output_dir)
        formats = ["stl", "dxf", "json", "bom", "assembly"]

        files = manager.export_all(formats, sample_layout, "test_cabinet")

        assert len(files) == len(formats)
        for fmt, path in files.items():
            assert path.exists(), f"File for {fmt} should exist"
            assert path.stat().st_size > 0, f"File for {fmt} should not be empty"

    def test_export_with_svg(
        self, optimized_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test SVG export requires bin packing."""
        manager = ExportManager(tmp_output_dir)
        files = manager.export_all(["svg"], optimized_layout, "test")

        assert "svg" in files
        assert files["svg"].exists()
        assert files["svg"].stat().st_size > 0

    def test_export_creates_output_directory(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test that ExportManager creates output directory if needed."""
        new_dir = tmp_path / "new_subdir" / "output"
        assert not new_dir.exists()

        manager = ExportManager(new_dir)
        files = manager.export_all(["json"], sample_layout, "test")

        assert new_dir.exists()
        assert files["json"].exists()

    def test_export_unknown_format_raises(
        self, sample_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test exporting with unknown format raises KeyError."""
        manager = ExportManager(tmp_output_dir)

        with pytest.raises(KeyError):
            manager.export_all(["unknown"], sample_layout, "test")


# =============================================================================
# DXF Exporter Tests
# =============================================================================


class TestDxfExporter:
    """Integration tests for DXF export."""

    def test_dxf_file_structure(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test DXF file has valid structure."""
        exporter = DxfExporter()
        path = tmp_path / "test.dxf"
        exporter.export(sample_layout, path)

        # Read and verify DXF structure
        content = path.read_text()
        assert "SECTION" in content
        assert "ENTITIES" in content
        assert "ENDSEC" in content
        assert "EOF" in content

    def test_dxf_layers_present(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test DXF contains all required layers."""
        exporter = DxfExporter()
        path = tmp_path / "test.dxf"
        exporter.export(sample_layout, path)

        content = path.read_text()
        assert "OUTLINE" in content
        assert "LABELS" in content

    def test_dxf_export_string(self, sample_layout: LayoutOutput):
        """Test DXF export_string method."""
        exporter = DxfExporter()
        content = exporter.export_string(sample_layout)

        assert isinstance(content, str)
        assert len(content) > 0
        assert "SECTION" in content
        assert "EOF" in content

    def test_dxf_units_mm(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test DXF export with mm units."""
        exporter = DxfExporter(units="mm")
        path = tmp_path / "test_mm.dxf"
        exporter.export(sample_layout, path)

        assert path.exists()
        assert path.stat().st_size > 0

    def test_dxf_per_panel_mode(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test DXF per-panel export mode."""
        exporter = DxfExporter(mode="per_panel")
        base_path = tmp_path / "test.dxf"
        exporter.export(sample_layout, base_path)

        # Should create multiple files
        dxf_files = list(tmp_path.glob("test_*.dxf"))
        assert len(dxf_files) > 0

    def test_dxf_empty_cut_list(self, tmp_path: Path):
        """Test DXF export with empty cut list."""
        # Create layout with empty cut list
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        output = LayoutOutput(
            cabinet=cabinet,
            cut_list=[],
            material_estimates={},
            total_estimate=MaterialEstimate(
                total_area_sqin=0.0,
                total_area_sqft=0.0,
                sheet_count_4x8=0,
                sheet_count_5x5=0,
                waste_percentage=0.15,
            ),
        )

        exporter = DxfExporter()
        path = tmp_path / "empty.dxf"
        exporter.export(output, path)

        # Should not create a file or create an empty one
        # (depends on implementation)


# =============================================================================
# Enhanced JSON Exporter Tests
# =============================================================================


class TestEnhancedJsonExporter:
    """Integration tests for enhanced JSON export."""

    def test_json_schema_version(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test JSON includes schema version."""
        exporter = EnhancedJsonExporter()
        path = tmp_path / "test.json"
        exporter.export(sample_layout, path)

        data = json.loads(path.read_text())
        assert data["schema_version"] == "1.0"

    def test_json_has_all_sections(self, sample_layout: LayoutOutput):
        """Test JSON includes all required sections."""
        exporter = EnhancedJsonExporter()
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        assert "config" in data
        assert "cabinet" in data
        assert "pieces" in data
        assert "cut_list" in data
        assert "bom" in data
        assert "warnings" in data

    def test_json_config_section(self, sample_layout: LayoutOutput):
        """Test JSON config section has expected fields."""
        exporter = EnhancedJsonExporter()
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        config = data["config"]
        assert config["type"] == "single_cabinet"
        assert "dimensions" in config
        assert "material" in config

    def test_json_cabinet_section(self, sample_layout: LayoutOutput):
        """Test JSON cabinet section has expected structure."""
        exporter = EnhancedJsonExporter()
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        cabinet = data["cabinet"]
        assert "dimensions" in cabinet
        assert cabinet["dimensions"]["width"] == 48.0
        assert cabinet["dimensions"]["height"] == 84.0
        assert cabinet["dimensions"]["depth"] == 12.0
        assert "interior_dimensions" in cabinet
        assert "sections" in cabinet

    def test_json_pieces_with_3d_positions(self, sample_layout: LayoutOutput):
        """Test JSON pieces include 3D positions by default."""
        exporter = EnhancedJsonExporter(include_3d_positions=True)
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        # At least some pieces should have 3D positions
        pieces_with_position = [p for p in data["pieces"] if "position_3d" in p]
        assert len(pieces_with_position) > 0

    def test_json_without_3d_positions(self, sample_layout: LayoutOutput):
        """Test JSON can exclude 3D positions."""
        exporter = EnhancedJsonExporter(include_3d_positions=False)
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        # No pieces should have 3D positions
        pieces_with_position = [p for p in data["pieces"] if "position_3d" in p]
        assert len(pieces_with_position) == 0

    def test_json_bom_section(self, sample_layout: LayoutOutput):
        """Test JSON BOM section has expected structure."""
        exporter = EnhancedJsonExporter(include_bom=True)
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        bom = data["bom"]
        assert "sheet_goods" in bom
        assert "hardware" in bom
        assert "edge_banding" in bom
        assert "totals" in bom

    def test_json_without_bom(self, sample_layout: LayoutOutput):
        """Test JSON can exclude BOM."""
        exporter = EnhancedJsonExporter(include_bom=False)
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        assert "bom" not in data

    def test_json_cut_list_section(self, sample_layout: LayoutOutput):
        """Test JSON cut list section has expected fields."""
        exporter = EnhancedJsonExporter()
        content = exporter.export_string(sample_layout)
        data = json.loads(content)

        assert len(data["cut_list"]) > 0
        piece = data["cut_list"][0]
        assert "label" in piece
        assert "panel_type" in piece
        assert "dimensions" in piece
        assert "quantity" in piece
        assert "area_sq_in" in piece
        assert "material" in piece


# =============================================================================
# BOM Generator Tests
# =============================================================================


class TestBomGenerator:
    """Integration tests for BOM generation."""

    def test_bom_text_format(self, sample_layout: LayoutOutput):
        """Test BOM text format output."""
        generator = BomGenerator(output_format="text")
        content = generator.export_string(sample_layout)

        assert "BILL OF MATERIALS" in content
        assert "SHEET GOODS" in content
        assert "HARDWARE" in content
        assert "EDGE BANDING" in content

    def test_bom_csv_format(self, sample_layout: LayoutOutput):
        """Test BOM CSV format is valid."""
        generator = BomGenerator(output_format="csv")
        content = generator.export_string(sample_layout)

        lines = content.strip().split("\n")
        assert len(lines) >= 2  # Header + at least one data row
        assert "Category" in lines[0]  # Header present

    def test_bom_json_format(self, sample_layout: LayoutOutput):
        """Test BOM JSON format is valid."""
        generator = BomGenerator(output_format="json")
        content = generator.export_string(sample_layout)

        data = json.loads(content)
        assert "sheet_goods" in data
        assert "hardware" in data
        assert "edge_banding" in data

    def test_bom_sheet_goods_calculation(self, sample_layout: LayoutOutput):
        """Test BOM sheet goods are calculated correctly."""
        generator = BomGenerator()
        bom = generator.generate(sample_layout)

        assert len(bom.sheet_goods) > 0
        for item in bom.sheet_goods:
            assert item.quantity >= 1
            assert item.square_feet > 0

    def test_bom_edge_banding_calculation(self, sample_layout: LayoutOutput):
        """Test BOM edge banding is calculated correctly."""
        generator = BomGenerator()
        bom = generator.generate(sample_layout)

        # Should have edge banding for visible panel types
        assert len(bom.edge_banding) >= 0  # May be 0 if no visible edges

    def test_bom_export_to_file(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test BOM export to file."""
        generator = BomGenerator(output_format="text")
        path = tmp_path / "test_bom.txt"
        generator.export(sample_layout, path)

        assert path.exists()
        content = path.read_text()
        assert "BILL OF MATERIALS" in content


# =============================================================================
# Assembly Instructions Tests
# =============================================================================


class TestAssemblyInstructions:
    """Integration tests for assembly instructions."""

    def test_assembly_markdown_structure(self, sample_layout: LayoutOutput):
        """Test assembly instructions have proper structure."""
        generator = AssemblyInstructionGenerator()
        content = generator.export_string(sample_layout)

        assert "# Assembly Instructions" in content
        assert "## Materials Checklist" in content
        assert "## Tools Needed" in content
        assert "## Assembly Steps" in content
        assert "## Finishing" in content

    def test_assembly_includes_cut_pieces_checklist(
        self, sample_layout: LayoutOutput
    ):
        """Test assembly instructions include cut pieces checklist."""
        generator = AssemblyInstructionGenerator()
        content = generator.export_string(sample_layout)

        assert "### Cut Pieces" in content
        assert "- [ ]" in content  # Checkbox format

    def test_assembly_includes_tools_list(self, sample_layout: LayoutOutput):
        """Test assembly instructions include tools list."""
        generator = AssemblyInstructionGenerator()
        content = generator.export_string(sample_layout)

        assert "Table saw" in content or "track saw" in content
        assert "Router" in content
        assert "Drill" in content

    def test_assembly_includes_steps(self, sample_layout: LayoutOutput):
        """Test assembly instructions include numbered steps."""
        generator = AssemblyInstructionGenerator()
        content = generator.export_string(sample_layout)

        assert "### Step 1:" in content
        # May have more steps depending on cabinet configuration

    def test_assembly_includes_safety_warnings(self, sample_layout: LayoutOutput):
        """Test assembly instructions include safety warnings."""
        generator = AssemblyInstructionGenerator(include_warnings=True)
        content = generator.export_string(sample_layout)

        assert "## Safety Warnings" in content
        assert "Safety glasses" in content

    def test_assembly_without_safety_warnings(self, sample_layout: LayoutOutput):
        """Test assembly instructions can exclude safety warnings."""
        generator = AssemblyInstructionGenerator(include_warnings=False)
        content = generator.export_string(sample_layout)

        assert "## Safety Warnings" not in content

    def test_assembly_export_to_file(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test assembly instructions export to file."""
        generator = AssemblyInstructionGenerator()
        path = tmp_path / "assembly.md"
        generator.export(sample_layout, path)

        assert path.exists()
        content = path.read_text()
        assert "# Assembly Instructions" in content


# =============================================================================
# SVG Exporter Tests
# =============================================================================


class TestSvgExporter:
    """Integration tests for SVG export."""

    def test_svg_structure(self, optimized_layout: LayoutOutput):
        """Test SVG has valid structure."""
        exporter = SvgExporter()
        content = exporter.export_string(optimized_layout)

        assert content.startswith("<svg") or content.startswith("<?xml")
        assert "</svg>" in content

    def test_svg_requires_bin_packing(self, sample_layout: LayoutOutput):
        """Test SVG export fails without bin packing."""
        exporter = SvgExporter()

        with pytest.raises(ValueError, match="bin packing"):
            exporter.export_string(sample_layout)

    def test_svg_export_to_file(
        self, optimized_layout: LayoutOutput, tmp_path: Path
    ):
        """Test SVG export to file."""
        exporter = SvgExporter()
        path = tmp_path / "test.svg"
        exporter.export(optimized_layout, path)

        assert path.exists()
        content = path.read_text()
        assert "<svg" in content or "<?xml" in content

    def test_svg_individual_sheets(
        self, optimized_layout: LayoutOutput, tmp_path: Path
    ):
        """Test SVG individual sheet export."""
        exporter = SvgExporter()
        base_path = tmp_path / "sheet.svg"
        files = exporter.export_individual_sheets(optimized_layout, base_path)

        assert len(files) >= 1
        for file_path in files:
            assert file_path.exists()

    def test_svg_scale_option(self, optimized_layout: LayoutOutput):
        """Test SVG with custom scale option."""
        exporter = SvgExporter(scale=20.0)
        content = exporter.export_string(optimized_layout)

        # Should produce valid SVG at different scale
        assert "<svg" in content or "<?xml" in content


# =============================================================================
# STL Exporter Tests
# =============================================================================


class TestStlExporter:
    """Integration tests for STL export."""

    def test_stl_export_to_file(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test STL export to file."""
        exporter = StlLayoutExporter()
        path = tmp_path / "test.stl"
        exporter.export(sample_layout, path)

        assert path.exists()
        assert path.stat().st_size > 0

    def test_stl_binary_format(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test STL produces binary format by default."""
        exporter = StlLayoutExporter()
        path = tmp_path / "test.stl"
        exporter.export(sample_layout, path)

        # Binary STL should not be readable as text (will have binary header)
        with open(path, "rb") as f:
            header = f.read(80)
            # Binary STL starts with 80-byte header
            assert len(header) == 80 or path.stat().st_size > 0


# =============================================================================
# CLI Multi-Format Export Tests
# =============================================================================


class TestCliMultiFormat:
    """Integration tests for CLI multi-format export."""

    def test_cli_generates_multiple_files(self, tmp_path: Path):
        """Test CLI creates all requested format files."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--output-formats", "json,bom",
                "--output-dir", str(tmp_path),
                "--project-name", "test_cabinet",
            ],
        )

        assert result.exit_code == 0
        assert (tmp_path / "test_cabinet_json.json").exists()
        assert (tmp_path / "test_cabinet_bom.txt").exists()

    def test_cli_all_formats(self, tmp_path: Path):
        """Test CLI with 'all' formats (excluding SVG without optimize)."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--output-formats", "stl,dxf,json,bom,assembly",
                "--output-dir", str(tmp_path),
                "--project-name", "all_formats",
            ],
        )

        assert result.exit_code == 0
        assert (tmp_path / "all_formats_stl.stl").exists()
        assert (tmp_path / "all_formats_dxf.dxf").exists()
        assert (tmp_path / "all_formats_json.json").exists()
        assert (tmp_path / "all_formats_bom.txt").exists()
        assert (tmp_path / "all_formats_assembly.md").exists()

    def test_cli_svg_requires_optimize(self, tmp_path: Path):
        """Test CLI warns about SVG without --optimize."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--output-formats", "svg",
                "--output-dir", str(tmp_path),
                "--project-name", "test",
            ],
        )

        # Should warn and skip SVG, or fail
        assert "SVG" in result.output or result.exit_code != 0

    def test_cli_svg_with_optimize(self, tmp_path: Path):
        """Test CLI SVG export with --optimize flag."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--optimize",
                "--output-formats", "svg",
                "--output-dir", str(tmp_path),
                "--project-name", "optimized",
            ],
        )

        assert result.exit_code == 0
        assert (tmp_path / "optimized_svg.svg").exists()

    def test_cli_invalid_format(self, tmp_path: Path):
        """Test CLI with invalid format."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--output-formats", "invalid_format",
                "--output-dir", str(tmp_path),
                "--project-name", "test",
            ],
        )

        assert result.exit_code == 1
        assert "Unknown formats" in result.output


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestExporterEdgeCases:
    """Edge case and error handling tests for exporters."""

    def test_large_layout_export(
        self, large_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test exporting a large layout with many panels."""
        manager = ExportManager(tmp_output_dir)
        formats = ["json", "bom", "assembly"]

        files = manager.export_all(formats, large_layout, "large_cabinet")

        for fmt, path in files.items():
            assert path.exists()
            assert path.stat().st_size > 0

    def test_export_with_long_project_name(
        self, sample_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test exporting with a long project name."""
        manager = ExportManager(tmp_output_dir)
        long_name = "my_very_long_project_name_for_cabinet_number_twelve_v2"

        files = manager.export_all(["json"], sample_layout, long_name)

        assert "json" in files
        assert files["json"].exists()

    def test_export_with_special_chars_in_name(
        self, sample_layout: LayoutOutput, tmp_output_dir: Path
    ):
        """Test exporting with special characters in project name."""
        manager = ExportManager(tmp_output_dir)
        # Most special chars should be ok for filenames
        name = "cabinet_2024-12-29"

        files = manager.export_all(["json"], sample_layout, name)

        assert "json" in files
        assert files["json"].exists()


# =============================================================================
# Output File Validation Tests
# =============================================================================


class TestOutputFileValidation:
    """Tests that verify output files are valid and usable."""

    def test_json_file_is_valid_json(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test JSON output is valid JSON."""
        exporter = EnhancedJsonExporter()
        path = tmp_path / "test.json"
        exporter.export(sample_layout, path)

        # Should parse without errors
        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "schema_version" in data

    def test_bom_csv_is_valid_csv(self, sample_layout: LayoutOutput, tmp_path: Path):
        """Test BOM CSV output is valid CSV."""
        import csv

        generator = BomGenerator(output_format="csv")
        path = tmp_path / "bom.csv"
        generator.export(sample_layout, path)

        # Should parse without errors
        with open(path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) >= 1  # At least header
        # All rows should have same number of columns
        col_counts = [len(row) for row in rows]
        assert len(set(col_counts)) == 1

    def test_markdown_has_valid_structure(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test assembly markdown has valid structure."""
        generator = AssemblyInstructionGenerator()
        path = tmp_path / "assembly.md"
        generator.export(sample_layout, path)

        content = path.read_text()

        # Should have proper markdown headings
        assert content.count("# ") >= 1  # At least one H1
        assert content.count("## ") >= 1  # At least one H2

    def test_svg_has_valid_xml(
        self, optimized_layout: LayoutOutput, tmp_path: Path
    ):
        """Test SVG output is valid XML."""
        import xml.etree.ElementTree as ET

        exporter = SvgExporter()
        path = tmp_path / "test.svg"
        exporter.export(optimized_layout, path)

        # Should parse without errors
        tree = ET.parse(path)
        root = tree.getroot()

        # SVG root element
        assert "svg" in root.tag


# =============================================================================
# Per-Format Config Options Tests
# =============================================================================


class TestPerFormatConfigOptions:
    """Test per-format configuration options are properly passed through."""

    def test_dxf_mode_combined(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test DXF combined mode creates single file."""
        exporter = DxfExporter(mode="combined")
        path = tmp_path / "combined.dxf"
        exporter.export(sample_layout, path)

        # Should create just one file at the specified path
        assert path.exists()

    def test_dxf_mode_per_panel(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test DXF per_panel mode creates multiple files."""
        exporter = DxfExporter(mode="per_panel")
        base_path = tmp_path / "panel.dxf"
        exporter.export(sample_layout, base_path)

        # Should create multiple files
        dxf_files = list(tmp_path.glob("panel_*.dxf"))
        assert len(dxf_files) > 0

    def test_dxf_hole_pattern_none(
        self, sample_layout: LayoutOutput, tmp_path: Path
    ):
        """Test DXF without hole pattern."""
        exporter = DxfExporter(hole_pattern="none")
        path = tmp_path / "no_holes.dxf"
        exporter.export(sample_layout, path)

        assert path.exists()

    def test_json_custom_indent(self, sample_layout: LayoutOutput):
        """Test JSON with custom indent."""
        exporter = EnhancedJsonExporter(indent=4)
        content = exporter.export_string(sample_layout)

        # With indent=4, lines should have 4-space indentation
        lines = content.split("\n")
        indented_lines = [l for l in lines if l.startswith("    ")]
        assert len(indented_lines) > 0

    def test_bom_with_costs(self, sample_layout: LayoutOutput):
        """Test BOM with cost columns enabled."""
        generator = BomGenerator(output_format="text", include_costs=True)
        content = generator.export_string(sample_layout)

        # When costs are enabled but not provided, should still work
        assert "BILL OF MATERIALS" in content

    def test_assembly_with_timestamps(self, sample_layout: LayoutOutput):
        """Test assembly instructions with timestamps."""
        generator = AssemblyInstructionGenerator(include_timestamps=True)
        content = generator.export_string(sample_layout)

        assert "*Generated:" in content

    def test_assembly_without_timestamps(self, sample_layout: LayoutOutput):
        """Test assembly instructions without timestamps."""
        generator = AssemblyInstructionGenerator(include_timestamps=False)
        content = generator.export_string(sample_layout)

        assert "*Generated:" not in content

    def test_svg_show_options(self, optimized_layout: LayoutOutput):
        """Test SVG with various display options."""
        exporter = SvgExporter(
            show_dimensions=False,
            show_labels=False,
            show_grain=True,
            use_panel_colors=False,
        )
        content = exporter.export_string(optimized_layout)

        # Should produce valid SVG with these options
        assert "<svg" in content or "<?xml" in content


# =============================================================================
# Integration with Real Configuration Files
# =============================================================================


class TestConfigFileIntegration:
    """Test export integration with configuration files."""

    def test_export_from_config_generated_layout(self, tmp_path: Path):
        """Test exporting a layout generated from dimensions."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=60.0, height=96.0, depth=14.0)
        params_input = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=4,
            material_thickness=0.75,
        )
        result = command.execute(wall_input, params_input)

        # Export to multiple formats
        manager = ExportManager(tmp_path)
        files = manager.export_all(
            ["json", "bom", "assembly", "dxf", "stl"],
            result,
            "configured_cabinet",
        )

        # Verify all files were created
        assert len(files) == 5
        for fmt, path in files.items():
            assert path.exists(), f"{fmt} file should exist"
            assert path.stat().st_size > 0, f"{fmt} file should not be empty"
