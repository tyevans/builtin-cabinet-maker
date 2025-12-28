"""Unit tests for the TemplateManager class.

This module tests the template management functionality including
listing templates, getting template content, and initializing templates.
"""

import json
from pathlib import Path

import pytest

from cabinets.application.templates import (
    TemplateManager,
    TemplateNotFoundError,
    TEMPLATE_METADATA,
)


class TestTemplateManager:
    """Test suite for TemplateManager class."""

    @pytest.fixture
    def manager(self) -> TemplateManager:
        """Create a TemplateManager instance for testing."""
        return TemplateManager()

    def test_list_templates_returns_all_templates(self, manager: TemplateManager) -> None:
        """Test that list_templates returns all available templates."""
        templates = manager.list_templates()

        assert len(templates) == 3
        names = [name for name, _ in templates]
        assert "simple-shelf" in names
        assert "bookcase" in names
        assert "cabinet-doors" in names

    def test_list_templates_returns_descriptions(self, manager: TemplateManager) -> None:
        """Test that list_templates includes descriptions."""
        templates = manager.list_templates()
        templates_dict = dict(templates)

        assert templates_dict["simple-shelf"] == "Basic wall shelf unit"
        assert templates_dict["bookcase"] == "Standard bookcase with adjustable shelves"
        assert templates_dict["cabinet-doors"] == "Base cabinet with door openings"

    def test_get_template_simple_shelf(self, manager: TemplateManager) -> None:
        """Test getting the simple-shelf template content."""
        content = manager.get_template("simple-shelf")

        # Verify it's valid JSON
        data = json.loads(content)

        # Verify expected structure
        assert data["schema_version"] == "1.0"
        assert data["cabinet"]["width"] == 36
        assert data["cabinet"]["height"] == 48
        assert data["cabinet"]["depth"] == 10
        assert len(data["cabinet"]["sections"]) == 1
        assert data["cabinet"]["sections"][0]["shelves"] == 4

    def test_get_template_bookcase(self, manager: TemplateManager) -> None:
        """Test getting the bookcase template content."""
        content = manager.get_template("bookcase")

        data = json.loads(content)

        assert data["schema_version"] == "1.0"
        assert data["cabinet"]["width"] == 72
        assert data["cabinet"]["height"] == 84
        assert data["cabinet"]["depth"] == 12
        assert data["cabinet"]["material"]["type"] == "plywood"
        assert data["cabinet"]["material"]["thickness"] == 0.75
        assert len(data["cabinet"]["sections"]) == 3
        assert data["output"]["format"] == "all"

    def test_get_template_cabinet_doors(self, manager: TemplateManager) -> None:
        """Test getting the cabinet-doors template content."""
        content = manager.get_template("cabinet-doors")

        data = json.loads(content)

        assert data["schema_version"] == "1.0"
        assert data["cabinet"]["width"] == 48
        assert data["cabinet"]["height"] == 34
        assert data["cabinet"]["depth"] == 24
        assert len(data["cabinet"]["sections"]) == 2

    def test_get_template_not_found(self, manager: TemplateManager) -> None:
        """Test that getting a non-existent template raises an error."""
        with pytest.raises(TemplateNotFoundError) as exc_info:
            manager.get_template("nonexistent")

        assert exc_info.value.name == "nonexistent"
        assert "nonexistent" in str(exc_info.value)

    def test_template_exists_true(self, manager: TemplateManager) -> None:
        """Test template_exists returns True for existing templates."""
        assert manager.template_exists("simple-shelf") is True
        assert manager.template_exists("bookcase") is True
        assert manager.template_exists("cabinet-doors") is True

    def test_template_exists_false(self, manager: TemplateManager) -> None:
        """Test template_exists returns False for non-existing templates."""
        assert manager.template_exists("nonexistent") is False
        assert manager.template_exists("") is False
        assert manager.template_exists("simple-shelf.json") is False

    def test_init_template_creates_file(
        self, manager: TemplateManager, tmp_path: Path
    ) -> None:
        """Test that init_template creates a file with template content."""
        output_path = tmp_path / "test-shelf.json"

        manager.init_template("simple-shelf", output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["schema_version"] == "1.0"
        assert data["cabinet"]["width"] == 36

    def test_init_template_not_found(
        self, manager: TemplateManager, tmp_path: Path
    ) -> None:
        """Test that init_template raises error for non-existent template."""
        output_path = tmp_path / "test.json"

        with pytest.raises(TemplateNotFoundError):
            manager.init_template("nonexistent", output_path)

        # File should not be created
        assert not output_path.exists()

    def test_init_template_overwrites_existing(
        self, manager: TemplateManager, tmp_path: Path
    ) -> None:
        """Test that init_template can overwrite an existing file."""
        output_path = tmp_path / "existing.json"
        output_path.write_text('{"old": "content"}', encoding="utf-8")

        manager.init_template("bookcase", output_path)

        content = output_path.read_text(encoding="utf-8")
        data = json.loads(content)
        # Should have new content
        assert data["cabinet"]["width"] == 72
        assert "old" not in data

    def test_init_template_creates_parent_directories(
        self, manager: TemplateManager, tmp_path: Path
    ) -> None:
        """Test that init_template works with nested paths."""
        output_path = tmp_path / "nested" / "dir" / "config.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        manager.init_template("simple-shelf", output_path)

        assert output_path.exists()


class TestTemplateMetadata:
    """Test the template metadata constant."""

    def test_metadata_contains_all_templates(self) -> None:
        """Test that TEMPLATE_METADATA contains entries for all templates."""
        expected_templates = {"simple-shelf", "bookcase", "cabinet-doors"}
        assert set(TEMPLATE_METADATA.keys()) == expected_templates

    def test_metadata_descriptions_are_strings(self) -> None:
        """Test that all descriptions are non-empty strings."""
        for name, description in TEMPLATE_METADATA.items():
            assert isinstance(description, str), f"{name} description should be string"
            assert len(description) > 0, f"{name} description should not be empty"


class TestTemplateNotFoundError:
    """Test the TemplateNotFoundError exception."""

    def test_error_stores_name(self) -> None:
        """Test that the error stores the template name."""
        error = TemplateNotFoundError("my-template")
        assert error.name == "my-template"

    def test_error_message_contains_name(self) -> None:
        """Test that the error message contains the template name."""
        error = TemplateNotFoundError("my-template")
        assert "my-template" in str(error)

    def test_error_message_format(self) -> None:
        """Test the error message format."""
        error = TemplateNotFoundError("my-template")
        assert str(error) == "Template not found: my-template"
