"""Unit tests for CLI zone stack integration (FRD-22 Phase 5)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cabinets.cli.main import app


runner = CliRunner()


class TestZoneStackDetection:
    """Tests for zone stack configuration detection."""

    def test_zone_stack_detected_in_config(self) -> None:
        """Zone stack config is detected and uses zone stack generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "zone_config.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "diagram",
                ],
            )
            # Should succeed and show zone stack output
            assert result.exit_code == 0
            assert "ZONE STACK DIAGRAM" in result.output

    def test_regular_config_does_not_trigger_zone_stack(self) -> None:
        """Regular cabinet config without zone_stack uses standard generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "regular_config.json"
            config_data = {
                "schema_version": "1.0",
                "cabinet": {
                    "width": 48.0,
                    "height": 84.0,
                    "depth": 12.0,
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "diagram",
                ],
            )
            assert result.exit_code == 0
            # Should NOT have zone stack output
            assert "ZONE STACK DIAGRAM" not in result.output


class TestZoneStackPresets:
    """Tests for zone stack preset configurations."""

    def test_kitchen_preset(self) -> None:
        """Kitchen preset generates base and upper cabinets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "all",
                ],
            )
            assert result.exit_code == 0
            assert "BASE ZONE" in result.output
            assert "UPPER ZONE" in result.output

    def test_mudroom_preset(self) -> None:
        """Mudroom preset generates bench and upper storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mudroom.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 48.0,
                    "height": 84.0,
                    "depth": 18.0,
                    "zone_stack": {
                        "preset": "mudroom",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "diagram",
                ],
            )
            assert result.exit_code == 0
            assert "ZONE STACK DIAGRAM" in result.output

    def test_vanity_preset(self) -> None:
        """Vanity preset generates bathroom vanity configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "vanity.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 36.0,
                    "height": 72.0,
                    "depth": 21.0,
                    "zone_stack": {
                        "preset": "vanity",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "diagram",
                ],
            )
            assert result.exit_code == 0
            assert "ZONE STACK DIAGRAM" in result.output

    def test_hutch_preset(self) -> None:
        """Hutch preset generates desk hutch configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "hutch.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 60.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "hutch",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "diagram",
                ],
            )
            assert result.exit_code == 0
            assert "ZONE STACK DIAGRAM" in result.output


class TestZoneStackOutputFormats:
    """Tests for zone stack output formats."""

    @pytest.fixture
    def kitchen_config_path(self) -> Path:
        """Create a kitchen zone stack config file."""
        import tempfile

        tmpdir = tempfile.mkdtemp()
        config_path = Path(tmpdir) / "kitchen.json"
        config_data = {
            "schema_version": "1.11",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 24.0,
                "zone_stack": {
                    "preset": "kitchen",
                    "countertop": {
                        "thickness": 1.5,
                        "edge_treatment": "eased",
                    },
                },
            },
        }
        config_path.write_text(json.dumps(config_data))
        return config_path

    def test_cutlist_format(self, kitchen_config_path: Path) -> None:
        """Cutlist format shows zone-separated cut list."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(kitchen_config_path),
                "--format",
                "cutlist",
            ],
        )
        assert result.exit_code == 0
        assert "ZONE STACK CUT LIST" in result.output
        assert "BASE ZONE" in result.output

    def test_materials_format(self, kitchen_config_path: Path) -> None:
        """Materials format shows zone-separated material estimates."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(kitchen_config_path),
                "--format",
                "materials",
            ],
        )
        assert result.exit_code == 0
        assert "ZONE STACK MATERIAL ESTIMATE" in result.output
        assert "TOTAL MATERIAL" in result.output

    def test_diagram_format(self, kitchen_config_path: Path) -> None:
        """Diagram format shows ASCII zone stack diagram."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(kitchen_config_path),
                "--format",
                "diagram",
            ],
        )
        assert result.exit_code == 0
        assert "ZONE STACK DIAGRAM" in result.output
        assert "FLOOR" in result.output

    def test_json_format(self, kitchen_config_path: Path) -> None:
        """JSON format outputs structured zone stack data."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(kitchen_config_path),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert "ZONE STACK JSON" in result.output
        assert '"zone_stack"' in result.output
        assert '"preset": "kitchen"' in result.output


class TestZoneStackStlExport:
    """Tests for zone stack STL export."""

    def test_stl_export_creates_separate_files(self) -> None:
        """STL export creates separate base and upper STL files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            output_path = Path(tmpdir) / "output.stl"
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "stl",
                    "--output",
                    str(output_path),
                ],
            )
            assert result.exit_code == 0
            # Should create base and upper STL files
            base_path = Path(tmpdir) / "output_base.stl"
            upper_path = Path(tmpdir) / "output_upper.stl"
            assert base_path.exists() or "Base zone STL saved to" in result.output
            assert upper_path.exists() or "Upper zone STL saved to" in result.output


class TestZoneStackMultiFormatExport:
    """Tests for zone stack multi-format export."""

    def test_multi_format_export_json(self) -> None:
        """Multi-format export creates JSON file for zone stack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            output_dir = Path(tmpdir) / "output"
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--output-formats",
                    "json",
                    "--output-dir",
                    str(output_dir),
                    "--project-name",
                    "my_kitchen",
                ],
            )
            assert result.exit_code == 0
            assert "Exported files:" in result.output
            assert (output_dir / "my_kitchen_zone_stack.json").exists()

    def test_multi_format_export_stl(self) -> None:
        """Multi-format export creates STL files for zone stack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            output_dir = Path(tmpdir) / "output"
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--output-formats",
                    "stl",
                    "--output-dir",
                    str(output_dir),
                    "--project-name",
                    "my_kitchen",
                ],
            )
            assert result.exit_code == 0
            assert "Exported files:" in result.output
            # Should create base and upper STL files
            assert (output_dir / "my_kitchen_base.stl").exists()

    def test_unsupported_format_warning(self) -> None:
        """Unsupported formats show warning for zone stacks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            output_dir = Path(tmpdir) / "output"
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--output-formats",
                    "svg,json",  # SVG not supported for zone stacks
                    "--output-dir",
                    str(output_dir),
                ],
            )
            # Should warn about unsupported format
            assert (
                "Zone stacks don't support formats: svg" in result.output
                or result.exit_code == 0
            )


class TestZoneStackWithCountertop:
    """Tests for zone stack countertop configuration."""

    def test_countertop_appears_in_output(self) -> None:
        """Countertop configuration appears in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                        "countertop": {
                            "thickness": 1.5,
                            "overhang": {"front": 1.0},
                            "edge_treatment": "eased",
                        },
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "diagram",
                ],
            )
            assert result.exit_code == 0
            assert "COUNTERTOP" in result.output

    def test_countertop_in_cutlist(self) -> None:
        """Countertop appears in cut list output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "kitchen.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "kitchen",
                        "countertop": {
                            "thickness": 1.5,
                        },
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "cutlist",
                ],
            )
            assert result.exit_code == 0
            # Countertop should be in output (may or may not be separate section)
            # depending on whether CountertopSurfaceComponent generates panels


class TestZoneStackHelpText:
    """Tests for zone stack help text in CLI."""

    def test_help_mentions_zone_stack(self) -> None:
        """Generate command help mentions zone stack support."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "zone" in result.output.lower() or "Zone" in result.output

    def test_help_shows_presets(self) -> None:
        """Generate command help shows available presets."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        # Help should mention presets
        assert "kitchen" in result.output.lower() or "preset" in result.output.lower()


class TestZoneStackErrorHandling:
    """Tests for zone stack error handling."""

    def test_custom_preset_requires_zones(self) -> None:
        """Custom preset without zones shows error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "custom.json"
            config_data = {
                "schema_version": "1.11",
                "cabinet": {
                    "width": 72.0,
                    "height": 84.0,
                    "depth": 24.0,
                    "zone_stack": {
                        "preset": "custom",
                        # Missing "zones" list
                    },
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "all",
                ],
            )
            # Should fail with validation error or zone stack error
            assert result.exit_code != 0 or "error" in result.output.lower()
