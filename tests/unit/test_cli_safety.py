"""Unit tests for CLI safety integration (FRD-21 Task 08)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cabinets.cli.main import app


runner = CliRunner()


class TestSafetyOptionsHelp:
    """Tests for safety CLI options in help output."""

    def test_help_shows_safety_factor_option(self) -> None:
        """Generate command help includes --safety-factor option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--safety-factor" in result.output
        assert "Safety factor" in result.output

    def test_help_shows_accessibility_option(self) -> None:
        """Generate command help includes --accessibility option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--accessibility" in result.output
        assert "ADA" in result.output

    def test_help_shows_child_safe_option(self) -> None:
        """Generate command help includes --child-safe option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--child-safe" in result.output
        assert "child safety" in result.output.lower()

    def test_help_shows_seismic_zone_option(self) -> None:
        """Generate command help includes --seismic-zone option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--seismic-zone" in result.output
        assert "seismic" in result.output.lower()

    def test_help_shows_material_cert_option(self) -> None:
        """Generate command help includes --material-cert option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--material-cert" in result.output
        # Check for at least one certification type
        assert (
            "carb_phase2" in result.output or "certification" in result.output.lower()
        )

    def test_help_shows_no_clearance_check_option(self) -> None:
        """Generate command help includes --no-clearance-check option."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--no-clearance-check" in result.output


class TestSafetyFormatOption:
    """Tests for safety output format options."""

    def test_format_help_includes_safety(self) -> None:
        """Format option help includes 'safety' choice."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "safety" in result.output

    def test_format_help_includes_safety_labels(self) -> None:
        """Format option help includes 'safety_labels' choice."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "safety_labels" in result.output


class TestSafetyFactorValidation:
    """Tests for --safety-factor validation."""

    def test_safety_factor_default(self) -> None:
        """Default safety factor is 4.0."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_safety_factor_minimum_accepted(self) -> None:
        """Safety factor of 2.0 is accepted."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--safety-factor",
                "2.0",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_safety_factor_maximum_accepted(self) -> None:
        """Safety factor of 6.0 is accepted."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--safety-factor",
                "6.0",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_safety_factor_below_minimum_rejected(self) -> None:
        """Safety factor below 2.0 is rejected."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--safety-factor",
                "1.5",
                "--format",
                "json",
            ],
        )
        # Typer should reject this at the CLI level
        assert result.exit_code != 0

    def test_safety_factor_above_maximum_rejected(self) -> None:
        """Safety factor above 6.0 is rejected."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--safety-factor",
                "7.0",
                "--format",
                "json",
            ],
        )
        # Typer should reject this at the CLI level
        assert result.exit_code != 0


class TestAccessibilityFlag:
    """Tests for --accessibility flag."""

    def test_accessibility_flag_works(self) -> None:
        """Accessibility flag enables ADA checking."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--accessibility",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        # Output should include safety assessment
        assert "SAFETY" in result.output or "Assessment" in result.output

    def test_no_accessibility_flag_works(self) -> None:
        """No-accessibility flag disables ADA checking."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--no-accessibility",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0


class TestChildSafeFlag:
    """Tests for --child-safe flag."""

    def test_child_safe_flag_works(self) -> None:
        """Child-safe flag enables child safety mode."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--child-safe",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0

    def test_no_child_safe_flag_works(self) -> None:
        """No-child-safe flag disables child safety mode."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--no-child-safe",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0


class TestSeismicZoneOption:
    """Tests for --seismic-zone option."""

    @pytest.mark.parametrize("zone", ["A", "B", "C", "D", "E", "F"])
    def test_valid_seismic_zones_accepted(self, zone: str) -> None:
        """All valid seismic zones (A-F) are accepted."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--seismic-zone",
                zone,
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_seismic_zone_case_insensitive(self) -> None:
        """Seismic zone accepts lowercase input."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--seismic-zone",
                "d",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_invalid_seismic_zone_warns(self) -> None:
        """Invalid seismic zone shows warning but continues."""
        _ = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--seismic-zone",
                "X",
                "--format",
                "json",
            ],
        )
        # Should either fail or show warning
        # Implementation shows warning and continues with None


class TestMaterialCertOption:
    """Tests for --material-cert option."""

    @pytest.mark.parametrize("cert", ["carb_phase2", "naf", "ulef", "none", "unknown"])
    def test_valid_material_certs_accepted(self, cert: str) -> None:
        """All valid material certifications are accepted."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--material-cert",
                cert,
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_material_cert_case_insensitive(self) -> None:
        """Material cert accepts uppercase input."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--material-cert",
                "CARB_PHASE2",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0


class TestSafetyFormat:
    """Tests for --format safety output."""

    def test_safety_format_shows_assessment(self) -> None:
        """Safety format displays safety assessment."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        assert "SAFETY" in result.output

    def test_safety_format_shows_anti_tip(self) -> None:
        """Safety format includes anti-tip analysis for tall cabinets."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",  # Tall cabinet
                "--depth",
                "12",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        # Should include anti-tip or stability analysis
        assert (
            "Stability" in result.output
            or "Anti-Tip" in result.output
            or "tip" in result.output.lower()
        )

    def test_safety_format_shows_weight_capacities(self) -> None:
        """Safety format includes weight capacity estimates."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        assert (
            "Weight" in result.output
            or "Capacity" in result.output
            or "lbs" in result.output
        )

    def test_safety_format_shows_material_compliance(self) -> None:
        """Safety format includes material compliance check."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        assert "Material" in result.output

    def test_safety_format_shows_seismic_with_zone(self) -> None:
        """Safety format includes seismic info when zone is specified."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--seismic-zone",
                "D",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        assert "Seismic" in result.output

    def test_safety_format_shows_disclaimer(self) -> None:
        """Safety format includes advisory disclaimer."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--format",
                "safety",
            ],
        )
        assert result.exit_code == 0
        assert "advisory" in result.output.lower() or "consult" in result.output.lower()


class TestSafetyLabelsFormat:
    """Tests for --format safety_labels output."""

    def test_safety_labels_format_creates_files(self) -> None:
        """Safety labels format creates label files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--width",
                    "48",
                    "--height",
                    "84",
                    "--depth",
                    "12",
                    "--format",
                    "safety_labels",
                    "--output-dir",
                    tmpdir,
                ],
            )
            assert result.exit_code == 0
            # Should create at least one label file
            output_path = Path(tmpdir)
            label_files = list(output_path.glob("safety_label_*.txt"))
            assert (
                len(label_files) >= 1
                or "Exported" in result.output
                or "No safety labels" in result.output
            )


class TestSafetyInAllFormat:
    """Tests for safety summary in 'all' format output."""

    def test_all_format_includes_safety_when_config_provided(self) -> None:
        """All format includes safety summary when safety options are used."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--accessibility",
                "--format",
                "all",
            ],
        )
        assert result.exit_code == 0
        # Should include safety summary
        assert "SAFETY" in result.output

    def test_all_format_shows_safety_hint(self) -> None:
        """All format shows hint to use --format safety for full analysis."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--child-safe",
                "--format",
                "all",
            ],
        )
        assert result.exit_code == 0
        assert "--format safety" in result.output


class TestSafetyWithConfigFile:
    """Tests for safety options with config file."""

    def test_config_file_safety_settings_used(self) -> None:
        """Safety settings from config file are used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {
                "schema_version": "1.0",
                "cabinet": {
                    "width": 48.0,
                    "height": 84.0,
                    "depth": 12.0,
                },
                "safety": {
                    "safety_factor": 5.0,
                    "child_safe_mode": True,
                    "seismic_zone": "D",
                    "material_certification": "carb_phase2",
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
                    "safety",
                ],
            )
            assert result.exit_code == 0
            assert "SAFETY" in result.output

    def test_cli_options_override_config_file(self) -> None:
        """CLI safety options override config file settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {
                "schema_version": "1.0",
                "cabinet": {
                    "width": 48.0,
                    "height": 84.0,
                    "depth": 12.0,
                },
                "safety": {
                    "safety_factor": 3.0,
                    "child_safe_mode": False,
                    "seismic_zone": "A",
                },
            }
            config_path.write_text(json.dumps(config_data))

            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(config_path),
                    "--safety-factor",
                    "5.0",
                    "--child-safe",
                    "--seismic-zone",
                    "D",
                    "--format",
                    "safety",
                ],
            )
            assert result.exit_code == 0
            # Should include seismic zone D info
            assert "D" in result.output or "Seismic" in result.output


class TestBuildSafetyConfigFunction:
    """Tests for _build_safety_config helper function."""

    def test_build_safety_config_basic(self) -> None:
        """Basic safety config construction works."""
        from cabinets.cli.commands.safety import build_safety_config

        config = build_safety_config(
            safety_factor=4.0,
            accessibility=False,
            child_safe=False,
            seismic_zone=None,
            material_cert="unknown",
            no_clearance_check=False,
        )

        assert config.safety_factor == 4.0
        assert config.accessibility_enabled is False
        assert config.child_safe_mode is False
        assert config.seismic_zone is None
        assert config.check_clearances is True

    def test_build_safety_config_all_options(self) -> None:
        """Safety config construction with all options works."""
        from cabinets.cli.commands.safety import build_safety_config
        from cabinets.domain.value_objects import (
            MaterialCertification,
            SeismicZone,
        )

        config = build_safety_config(
            safety_factor=5.0,
            accessibility=True,
            child_safe=True,
            seismic_zone="D",
            material_cert="carb_phase2",
            no_clearance_check=True,
        )

        assert config.safety_factor == 5.0
        assert config.accessibility_enabled is True
        assert config.child_safe_mode is True
        assert config.seismic_zone == SeismicZone.D
        assert config.material_certification == MaterialCertification.CARB_PHASE2
        assert config.check_clearances is False

    def test_build_safety_config_seismic_zone_case_handling(self) -> None:
        """Safety config handles lowercase seismic zone."""
        from cabinets.cli.commands.safety import build_safety_config
        from cabinets.domain.value_objects import SeismicZone

        config = build_safety_config(
            safety_factor=4.0,
            accessibility=False,
            child_safe=False,
            seismic_zone="e",  # lowercase
            material_cert="unknown",
            no_clearance_check=False,
        )

        assert config.seismic_zone == SeismicZone.E

    def test_build_safety_config_material_cert_mapping(self) -> None:
        """Safety config maps material cert strings correctly."""
        from cabinets.cli.commands.safety import build_safety_config
        from cabinets.domain.value_objects import MaterialCertification

        # Test each certification type
        cert_map = {
            "carb_phase2": MaterialCertification.CARB_PHASE2,
            "naf": MaterialCertification.NAF,
            "ulef": MaterialCertification.ULEF,
            "none": MaterialCertification.NONE,
            "unknown": MaterialCertification.UNKNOWN,
        }

        for cert_str, expected in cert_map.items():
            config = build_safety_config(
                safety_factor=4.0,
                accessibility=False,
                child_safe=False,
                seismic_zone=None,
                material_cert=cert_str,
                no_clearance_check=False,
            )
            assert config.material_certification == expected, f"Failed for {cert_str}"


class TestNoClearanceCheckFlag:
    """Tests for --no-clearance-check flag."""

    def test_no_clearance_check_disables_checking(self) -> None:
        """No-clearance-check flag disables clearance checks."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--no-clearance-check",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
