"""Integration tests for the templates CLI commands.

This module tests the `templates list` and `templates init` CLI commands
end-to-end using the Typer CliRunner.
"""

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from cabinets.cli.main import app

runner = CliRunner()


class TestTemplatesListCommand:
    """Test suite for the 'templates list' command."""

    def test_list_shows_all_templates(self) -> None:
        """Test that list command shows all available templates."""
        result = runner.invoke(app, ["templates", "list"])

        assert result.exit_code == 0
        assert "Available templates:" in result.output
        assert "simple-shelf" in result.output
        assert "bookcase" in result.output
        assert "cabinet-doors" in result.output

    def test_list_shows_descriptions(self) -> None:
        """Test that list command shows template descriptions."""
        result = runner.invoke(app, ["templates", "list"])

        assert result.exit_code == 0
        assert "Basic wall shelf unit" in result.output
        assert "Standard bookcase with adjustable shelves" in result.output
        assert "Base cabinet with door openings" in result.output

    def test_list_shows_usage_hint(self) -> None:
        """Test that list command shows usage hint."""
        result = runner.invoke(app, ["templates", "list"])

        assert result.exit_code == 0
        assert "cabinets templates init" in result.output


class TestTemplatesInitCommand:
    """Test suite for the 'templates init' command."""

    def test_init_creates_file_with_default_name(self, tmp_path: Path) -> None:
        """Test that init creates file with template name as default."""
        # Change to temp directory for the test
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["templates", "init", "simple-shelf"])

            assert result.exit_code == 0
            assert "Created: simple-shelf.json" in result.output

            # Verify file was created
            output_file = tmp_path / "simple-shelf.json"
            assert output_file.exists()

            # Verify content is valid
            content = json.loads(output_file.read_text())
            assert content["schema_version"] == "1.0"
            assert content["cabinet"]["width"] == 36
        finally:
            os.chdir(original_cwd)

    def test_init_creates_file_with_custom_output(self, tmp_path: Path) -> None:
        """Test that init creates file at custom output path."""
        output_path = tmp_path / "my-config.json"

        result = runner.invoke(
            app, ["templates", "init", "bookcase", "--output", str(output_path)]
        )

        assert result.exit_code == 0
        assert f"Created: {output_path}" in result.output
        assert output_path.exists()

        content = json.loads(output_path.read_text())
        assert content["cabinet"]["width"] == 72

    def test_init_with_short_output_flag(self, tmp_path: Path) -> None:
        """Test that init works with -o short flag."""
        output_path = tmp_path / "short-flag.json"

        result = runner.invoke(
            app, ["templates", "init", "cabinet-doors", "-o", str(output_path)]
        )

        assert result.exit_code == 0
        assert output_path.exists()

    def test_init_errors_on_nonexistent_template(self) -> None:
        """Test that init fails for non-existent template."""
        result = runner.invoke(app, ["templates", "init", "nonexistent"])

        assert result.exit_code == 1
        assert "Error: Template not found: nonexistent" in result.output
        assert "Available templates:" in result.output

    def test_init_errors_on_existing_file(self, tmp_path: Path) -> None:
        """Test that init fails if output file already exists."""
        output_path = tmp_path / "existing.json"
        output_path.write_text('{"existing": true}')

        result = runner.invoke(
            app, ["templates", "init", "simple-shelf", "--output", str(output_path)]
        )

        assert result.exit_code == 1
        assert "Error: File already exists:" in result.output
        assert "Use --force to overwrite" in result.output

        # Original content should be preserved
        assert json.loads(output_path.read_text()) == {"existing": True}

    def test_init_force_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test that init --force overwrites existing file."""
        output_path = tmp_path / "existing.json"
        output_path.write_text('{"existing": true}')

        result = runner.invoke(
            app,
            [
                "templates",
                "init",
                "simple-shelf",
                "--output",
                str(output_path),
                "--force",
            ],
        )

        assert result.exit_code == 0
        assert f"Created: {output_path}" in result.output

        # Content should be new template
        content = json.loads(output_path.read_text())
        assert content["cabinet"]["width"] == 36
        assert "existing" not in content

    def test_init_force_short_flag(self, tmp_path: Path) -> None:
        """Test that init -f short flag works for force."""
        output_path = tmp_path / "existing.json"
        output_path.write_text('{"existing": true}')

        result = runner.invoke(
            app,
            ["templates", "init", "bookcase", "-o", str(output_path), "-f"],
        )

        assert result.exit_code == 0
        content = json.loads(output_path.read_text())
        assert content["cabinet"]["width"] == 72

    def test_init_all_templates_produce_valid_configs(self, tmp_path: Path) -> None:
        """Test that all templates produce valid configuration files."""
        templates = ["simple-shelf", "bookcase", "cabinet-doors"]

        for template_name in templates:
            output_path = tmp_path / f"{template_name}.json"

            result = runner.invoke(
                app, ["templates", "init", template_name, "--output", str(output_path)]
            )

            assert result.exit_code == 0, f"Failed to init {template_name}"
            assert output_path.exists(), f"File not created for {template_name}"

            # Verify valid JSON
            content = json.loads(output_path.read_text())
            assert "schema_version" in content
            assert "cabinet" in content
            assert "width" in content["cabinet"]
            assert "height" in content["cabinet"]
            assert "depth" in content["cabinet"]


class TestTemplatesCommandHelp:
    """Test help text for templates commands."""

    def test_templates_help(self) -> None:
        """Test that templates --help shows subcommands."""
        result = runner.invoke(app, ["templates", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "init" in result.output

    def test_templates_list_help(self) -> None:
        """Test that templates list --help shows description."""
        result = runner.invoke(app, ["templates", "list", "--help"])

        assert result.exit_code == 0
        assert "List all available" in result.output

    def test_templates_init_help(self) -> None:
        """Test that templates init --help shows options."""
        result = runner.invoke(app, ["templates", "init", "--help"])

        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--force" in result.output
        assert "NAME" in result.output


class TestTemplatesIntegrationWithValidate:
    """Test that templates can be validated after initialization."""

    def test_initialized_template_passes_validation(self, tmp_path: Path) -> None:
        """Test that initialized templates pass the validate command."""
        templates = ["simple-shelf", "bookcase", "cabinet-doors"]

        for template_name in templates:
            output_path = tmp_path / f"{template_name}.json"

            # Initialize the template
            init_result = runner.invoke(
                app, ["templates", "init", template_name, "--output", str(output_path)]
            )
            assert init_result.exit_code == 0

            # Validate the created config
            validate_result = runner.invoke(app, ["validate", str(output_path)])

            # Should pass validation (exit code 0 or 2 for warnings-only)
            assert validate_result.exit_code in (0, 2), (
                f"Template {template_name} failed validation: {validate_result.output}"
            )
