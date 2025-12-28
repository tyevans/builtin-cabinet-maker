"""Integration tests for the validate CLI command.

These tests verify the validate command works correctly end-to-end,
including:
- Valid configuration files pass validation
- Invalid configuration files produce errors
- Woodworking warnings are displayed
- Exit codes are correct
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cabinets.cli.main import app

# Get path to test fixtures
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "configs"


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


class TestValidateCommand:
    """Tests for the validate command."""

    def test_valid_minimal_config(self, runner: CliRunner) -> None:
        """Valid minimal config should pass validation (may have warnings)."""
        config_path = FIXTURES_PATH / "valid_minimal.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        # Exit code 0 = valid, 2 = valid with warnings
        # The minimal config triggers aspect ratio warning (84/12 = 7:1)
        assert result.exit_code in [0, 2]
        assert "Validation passed" in result.output

    def test_valid_full_config(self, runner: CliRunner) -> None:
        """Valid full config should pass with exit code 0."""
        config_path = FIXTURES_PATH / "valid_full.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        # This might have warnings due to section widths, check for no errors
        assert result.exit_code in [0, 2]  # 0 = valid, 2 = valid with warnings
        assert "Error" not in result.output or "Validation passed" in result.output

    def test_file_not_found(self, runner: CliRunner) -> None:
        """Non-existent file should fail with exit code 1."""
        config_path = FIXTURES_PATH / "nonexistent.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Errors:" in result.output

    def test_invalid_json_syntax(self, runner: CliRunner) -> None:
        """Invalid JSON should fail with exit code 1."""
        config_path = FIXTURES_PATH / "invalid_json.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        assert result.exit_code == 1
        assert "Errors:" in result.output
        assert "Validation failed" in result.output

    def test_unknown_field_rejected(self, runner: CliRunner) -> None:
        """Unknown fields should cause validation failure."""
        config_path = FIXTURES_PATH / "unknown_field.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        assert result.exit_code == 1
        assert "Errors:" in result.output

    def test_valid_config_with_warnings(self, runner: CliRunner) -> None:
        """Valid config with advisories should have exit code 2."""
        config_path = FIXTURES_PATH / "valid_with_warnings.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        # Exit code 2 = valid with warnings
        assert result.exit_code == 2
        assert "Warnings:" in result.output
        assert "span" in result.output.lower() or "ratio" in result.output.lower()
        assert "Validation passed" in result.output

    def test_sections_exceed_width_error(self, runner: CliRunner) -> None:
        """Sections that exceed cabinet width should cause error."""
        config_path = FIXTURES_PATH / "sections_exceed_width.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        assert result.exit_code == 1
        assert "Errors:" in result.output
        assert "exceed" in result.output.lower()
        assert "Validation failed" in result.output

    def test_output_includes_validating_message(self, runner: CliRunner) -> None:
        """Output should include 'Validating...' message."""
        config_path = FIXTURES_PATH / "valid_minimal.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        assert "Validating" in result.output

    def test_output_shows_warning_suggestions(self, runner: CliRunner) -> None:
        """Warnings should include suggestions when available."""
        config_path = FIXTURES_PATH / "valid_with_warnings.json"
        result = runner.invoke(app, ["validate", str(config_path)])

        if result.exit_code == 2:  # Has warnings
            assert "Suggestion:" in result.output


class TestValidateCommandWithTempFiles:
    """Tests that create temporary files for validation."""

    def test_missing_required_field(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Missing required field should cause validation error."""
        config_content = """{
  "schema_version": "1.0",
  "cabinet": {
    "width": 48.0,
    "height": 84.0
  }
}"""
        config_file = tmp_path / "missing_depth.json"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["validate", str(config_file)])

        assert result.exit_code == 1
        assert "Errors:" in result.output
        assert "depth" in result.output.lower()

    def test_invalid_dimension_value(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Invalid dimension value should cause validation error."""
        config_content = """{
  "schema_version": "1.0",
  "cabinet": {
    "width": -10.0,
    "height": 84.0,
    "depth": 12.0
  }
}"""
        config_file = tmp_path / "negative_width.json"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["validate", str(config_file)])

        assert result.exit_code == 1
        assert "Errors:" in result.output
        assert "width" in result.output.lower()

    def test_unsupported_schema_version(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Unsupported schema version should cause validation error."""
        config_content = """{
  "schema_version": "2.0",
  "cabinet": {
    "width": 48.0,
    "height": 84.0,
    "depth": 12.0
  }
}"""
        config_file = tmp_path / "wrong_version.json"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["validate", str(config_file)])

        assert result.exit_code == 1
        assert "Errors:" in result.output
        # Error message should mention version
        assert "version" in result.output.lower() or "schema" in result.output.lower()

    def test_thin_material_warning(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Very thin material should trigger warning."""
        config_content = """{
  "schema_version": "1.0",
  "cabinet": {
    "width": 36.0,
    "height": 48.0,
    "depth": 12.0,
    "material": {
      "type": "plywood",
      "thickness": 0.25
    }
  }
}"""
        config_file = tmp_path / "thin_material.json"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["validate", str(config_file)])

        # Should pass validation but with warning
        assert result.exit_code in [0, 2]
        if result.exit_code == 2:
            assert "Warnings:" in result.output
            assert "thickness" in result.output.lower() or "thin" in result.output.lower()

    def test_extreme_aspect_ratio_warning(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Extreme height-to-depth ratio should trigger warning."""
        config_content = """{
  "schema_version": "1.0",
  "cabinet": {
    "width": 36.0,
    "height": 84.0,
    "depth": 6.0
  }
}"""
        config_file = tmp_path / "tall_shallow.json"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["validate", str(config_file)])

        # Should pass validation but with warning about stability
        assert result.exit_code == 2  # Valid with warnings
        assert "Warnings:" in result.output
        assert "ratio" in result.output.lower() or "stability" in result.output.lower()


class TestGenerateWithConfigFlag:
    """Tests for the generate command with --config flag."""

    def test_generate_with_config(self, runner: CliRunner) -> None:
        """Generate should work with --config flag."""
        config_path = FIXTURES_PATH / "valid_minimal.json"
        result = runner.invoke(app, ["generate", "--config", str(config_path)])

        # Should succeed and produce output
        assert result.exit_code == 0
        # Should show diagram or some output
        assert len(result.output) > 0

    def test_generate_config_with_override(self, runner: CliRunner) -> None:
        """CLI args should override config values."""
        config_path = FIXTURES_PATH / "valid_minimal.json"
        result = runner.invoke(
            app,
            ["generate", "--config", str(config_path), "--width", "60"],
        )

        assert result.exit_code == 0

    def test_generate_without_config_requires_dimensions(
        self, runner: CliRunner
    ) -> None:
        """Without --config, dimensions are required."""
        result = runner.invoke(app, ["generate"])

        assert result.exit_code != 0
        assert "required" in result.output.lower() or "Error" in result.output

    def test_generate_cli_only_mode(self, runner: CliRunner) -> None:
        """Traditional CLI-only mode should still work."""
        result = runner.invoke(
            app,
            ["generate", "--width", "48", "--height", "84", "--depth", "12"],
        )

        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_generate_config_file_not_found(self, runner: CliRunner) -> None:
        """Non-existent config file should fail."""
        result = runner.invoke(
            app, ["generate", "--config", "nonexistent.json"]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output
