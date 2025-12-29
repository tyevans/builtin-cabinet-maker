"""Unit tests for CLI multi-format export functionality (FRD-16 FR-06)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import ClassVar

import pytest
from typer.testing import CliRunner

from cabinets.cli.main import app
from cabinets.infrastructure.exporters import ExporterRegistry, SvgExporter


runner = CliRunner()


class TestOutputFormatsOption:
    """Tests for --output-formats CLI option."""

    def test_help_shows_output_formats_option(self) -> None:
        """Generate command help includes --output-formats option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--output-formats" in result.output
        assert "Comma-separated export formats" in result.output

    def test_help_shows_output_dir_option(self) -> None:
        """Generate command help includes --output-dir option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--output-dir" in result.output
        assert "Output directory" in result.output

    def test_help_shows_project_name_option(self) -> None:
        """Generate command help includes --project-name option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--project-name" in result.output
        assert "Project name" in result.output


class TestFormatParsing:
    """Tests for format string parsing."""

    def test_single_format_export(self) -> None:
        """Single format exports to correct file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl",
                    "--output-dir", tmpdir,
                    "--project-name", "test_cabinet",
                ],
            )
            assert result.exit_code == 0
            assert "Exported files:" in result.output
            assert "STL:" in result.output
            # Check file was created
            stl_file = Path(tmpdir) / "test_cabinet_stl.stl"
            assert stl_file.exists()

    def test_multiple_formats_comma_separated(self) -> None:
        """Multiple comma-separated formats export to correct files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl,json",
                    "--output-dir", tmpdir,
                    "--project-name", "multi",
                ],
            )
            assert result.exit_code == 0
            assert "STL:" in result.output
            assert "JSON:" in result.output
            # Check files were created
            assert (Path(tmpdir) / "multi_stl.stl").exists()
            assert (Path(tmpdir) / "multi_json.json").exists()

    def test_formats_with_spaces(self) -> None:
        """Formats with spaces are trimmed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl , json",  # Spaces around comma
                    "--output-dir", tmpdir,
                ],
            )
            assert result.exit_code == 0
            assert "STL:" in result.output
            assert "JSON:" in result.output

    def test_all_formats_keyword(self) -> None:
        """'all' keyword exports all registered formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "all",
                    "--output-dir", tmpdir,
                ],
            )
            # Should export all formats (except svg which requires --optimize)
            assert result.exit_code == 0
            assert "Exported files:" in result.output
            # At minimum should have stl, json, bom, assembly, dxf
            assert "STL:" in result.output
            assert "JSON:" in result.output

    def test_all_formats_case_insensitive(self) -> None:
        """'ALL' keyword works regardless of case."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "ALL",
                    "--output-dir", tmpdir,
                ],
            )
            assert result.exit_code == 0
            assert "Exported files:" in result.output


class TestInvalidFormatHandling:
    """Tests for invalid format handling."""

    def test_unknown_format_error(self) -> None:
        """Unknown format shows error with available formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "unknown_format",
                    "--output-dir", tmpdir,
                ],
            )
            assert result.exit_code == 1
            assert "Unknown formats: unknown_format" in result.output
            assert "Available formats:" in result.output

    def test_mixed_valid_invalid_formats(self) -> None:
        """Mix of valid and invalid formats shows error for invalid ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl,invalid_format",
                    "--output-dir", tmpdir,
                ],
            )
            assert result.exit_code == 1
            assert "Unknown formats: invalid_format" in result.output


class TestOutputDirectoryHandling:
    """Tests for output directory handling."""

    def test_creates_output_directory(self) -> None:
        """Output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "output" / "dir"
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl",
                    "--output-dir", str(nested_dir),
                ],
            )
            assert result.exit_code == 0
            assert nested_dir.exists()

    def test_default_output_directory(self) -> None:
        """Default output directory is current directory."""
        # We can't easily test this without changing cwd, but we can verify
        # the option is optional
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--output-formats", "json",
            ],
        )
        # Should succeed, output to current directory
        assert result.exit_code == 0


class TestFileNamingConvention:
    """Tests for file naming convention (FR-06.4)."""

    def test_file_naming_pattern(self) -> None:
        """Files are named {project_name}_{format}.{ext}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl,json",
                    "--output-dir", tmpdir,
                    "--project-name", "my_project",
                ],
            )
            assert result.exit_code == 0
            # Check file names
            assert (Path(tmpdir) / "my_project_stl.stl").exists()
            assert (Path(tmpdir) / "my_project_json.json").exists()

    def test_default_project_name(self) -> None:
        """Default project name is 'cabinet'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl",
                    "--output-dir", tmpdir,
                ],
            )
            assert result.exit_code == 0
            assert (Path(tmpdir) / "cabinet_stl.stl").exists()


class TestSvgExportRequiresOptimize:
    """Tests for SVG export requiring bin packing."""

    def test_svg_without_optimize_shows_warning(self) -> None:
        """SVG export without --optimize shows warning and skips."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "svg",
                    "--output-dir", tmpdir,
                ],
            )
            # Should show warning about SVG requiring --optimize
            assert "SVG export requires --optimize flag" in result.output

    def test_svg_with_optimize_exports(self) -> None:
        """SVG export with --optimize creates SVG file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "svg",
                    "--output-dir", tmpdir,
                    "--optimize",
                ],
            )
            assert result.exit_code == 0
            assert "SVG:" in result.output
            assert (Path(tmpdir) / "cabinet_svg.svg").exists()

    def test_mixed_formats_with_svg_and_optimize(self) -> None:
        """Mixed formats with SVG work when --optimize is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--output-formats", "stl,svg,json",
                    "--output-dir", tmpdir,
                    "--optimize",
                ],
            )
            assert result.exit_code == 0
            assert "STL:" in result.output
            assert "SVG:" in result.output
            assert "JSON:" in result.output


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing --format option."""

    def test_format_option_still_works(self) -> None:
        """Existing --format option continues to work."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--format", "cutlist",
            ],
        )
        assert result.exit_code == 0
        assert "CUT LIST" in result.output

    def test_output_formats_takes_precedence(self) -> None:
        """--output-formats takes precedence over --format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width", "48",
                    "--height", "84",
                    "--depth", "12",
                    "--format", "cutlist",  # This should be ignored
                    "--output-formats", "stl",
                    "--output-dir", tmpdir,
                ],
            )
            assert result.exit_code == 0
            # Should export STL, not display cutlist
            assert "STL:" in result.output
            assert "CUT LIST" not in result.output


class TestSvgExporterRegistration:
    """Tests for SVG exporter registration."""

    def test_svg_exporter_is_registered(self) -> None:
        """SvgExporter is registered in ExporterRegistry."""
        assert ExporterRegistry.is_registered("svg")
        assert ExporterRegistry.get("svg") is SvgExporter

    def test_svg_exporter_format_attributes(self) -> None:
        """SvgExporter has correct format attributes."""
        assert SvgExporter.format_name == "svg"
        assert SvgExporter.file_extension == "svg"

    def test_svg_in_available_formats(self) -> None:
        """SVG is in the list of available formats."""
        formats = ExporterRegistry.available_formats()
        assert "svg" in formats


class TestSvgExporterFunctionality:
    """Tests for SvgExporter functionality."""

    def test_export_without_packing_raises_error(self) -> None:
        """SvgExporter.export raises error without packing result."""
        from dataclasses import dataclass

        # Create minimal output-like object without packing_result
        @dataclass
        class MockOutput:
            packing_result: None = None

        mock_output = MockOutput()

        exporter = SvgExporter()
        with pytest.raises(ValueError) as exc_info:
            exporter.export(mock_output, Path("/tmp/test.svg"))
        assert "bin packing" in str(exc_info.value).lower()

    def test_export_string_without_packing_raises_error(self) -> None:
        """SvgExporter.export_string raises error without packing result."""
        from dataclasses import dataclass

        @dataclass
        class MockOutput:
            packing_result: None = None

        mock_output = MockOutput()

        exporter = SvgExporter()
        with pytest.raises(ValueError) as exc_info:
            exporter.export_string(mock_output)
        assert "bin packing" in str(exc_info.value).lower()


class TestMultiFormatWithConfig:
    """Tests for multi-format export with config file."""

    def test_config_with_output_formats(self) -> None:
        """Config file works with --output-formats option."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a config file
            config_path = Path(tmpdir) / "config.json"
            config_data = {
                "schema_version": "1.0",
                "cabinet": {
                    "width": 48.0,
                    "height": 84.0,
                    "depth": 12.0,
                },
            }
            config_path.write_text(json.dumps(config_data))

            output_dir = Path(tmpdir) / "output"

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config", str(config_path),
                    "--output-formats", "stl,json",
                    "--output-dir", str(output_dir),
                ],
            )
            assert result.exit_code == 0
            assert (output_dir / "cabinet_stl.stl").exists()
            assert (output_dir / "cabinet_json.json").exists()
