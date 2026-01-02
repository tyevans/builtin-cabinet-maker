"""Integration tests for configuration section specifications workflow.

This module tests the end-to-end workflow of loading configuration files
with section specifications and generating cabinets with the correct
section widths and shelf counts.
"""

import json
import pytest
from pathlib import Path

from cabinets.application.config import (
    CabinetConfiguration,
    config_to_dtos,
    config_to_section_specs,
    has_section_specs,
    load_config,
)
from cabinets.application.factory import get_factory


class TestConfigToSectionSpecs:
    """Tests for converting configuration to section specs."""

    def test_config_with_sections_creates_specs(self) -> None:
        """Test that config with sections creates correct section specs."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {"width": 24.0, "shelves": 3},
                    {"width": "fill", "shelves": 5},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)
        specs = config_to_section_specs(config)

        assert len(specs) == 2
        assert specs[0].width == 24.0
        assert specs[0].shelves == 3
        assert specs[1].width == "fill"
        assert specs[1].shelves == 5

    def test_config_without_sections_creates_default_spec(self) -> None:
        """Test that config without sections creates a default fill spec."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config = CabinetConfiguration.model_validate(config_data)
        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].width == "fill"
        assert specs[0].shelves == 0

    def test_has_section_specs_returns_true_when_sections_present(self) -> None:
        """Test has_section_specs returns True when sections are defined."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{"width": 24.0, "shelves": 3}],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)
        assert has_section_specs(config) is True

    def test_has_section_specs_returns_false_when_no_sections(self) -> None:
        """Test has_section_specs returns False when no sections are defined."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config = CabinetConfiguration.model_validate(config_data)
        assert has_section_specs(config) is False


class TestEndToEndSectionGeneration:
    """End-to-end tests for generating cabinets with section specs."""

    def test_generate_with_fixed_and_fill_sections(self) -> None:
        """Test generating cabinet with mixed fixed and fill sections."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "material": {"thickness": 0.75},
                "sections": [
                    {"width": 24.0, "shelves": 3},
                    {"width": "fill", "shelves": 5},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid
        assert len(result.cabinet.sections) == 2

        # First section should have fixed width of 24"
        assert result.cabinet.sections[0].width == pytest.approx(24.0, rel=1e-6)
        assert len(result.cabinet.sections[0].shelves) == 3

        # Second section should have fill width
        # 72" - 2*0.75" walls - 1*0.75" divider = 69.75"
        # Fill: 69.75 - 24 = 45.75"
        assert result.cabinet.sections[1].width == pytest.approx(45.75, rel=1e-6)
        assert len(result.cabinet.sections[1].shelves) == 5

    def test_generate_with_all_fill_sections(self) -> None:
        """Test generating cabinet with all fill sections."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "material": {"thickness": 0.75},
                "sections": [
                    {"width": "fill", "shelves": 3},
                    {"width": "fill", "shelves": 4},
                    {"width": "fill", "shelves": 5},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid
        assert len(result.cabinet.sections) == 3

        # 72" - 2*0.75" walls - 2*0.75" dividers = 69"
        # Each: 69 / 3 = 23"
        for section in result.cabinet.sections:
            assert section.width == pytest.approx(23.0, rel=1e-6)

        # Verify shelf counts
        assert len(result.cabinet.sections[0].shelves) == 3
        assert len(result.cabinet.sections[1].shelves) == 4
        assert len(result.cabinet.sections[2].shelves) == 5

    def test_generate_with_single_section(self) -> None:
        """Test generating cabinet with single fill section."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "material": {"thickness": 0.75},
                "sections": [{"shelves": 4}],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid
        assert len(result.cabinet.sections) == 1
        # 48" - 2*0.75" = 46.5"
        assert result.cabinet.sections[0].width == pytest.approx(46.5, rel=1e-6)
        assert len(result.cabinet.sections[0].shelves) == 4


class TestLoadConfigWithSections:
    """Tests for loading configuration files with sections."""

    def test_load_config_with_sections_from_file(self, tmp_path: Path) -> None:
        """Test loading a config file with section specifications."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {"width": 24.0, "shelves": 5},
                    {"width": 24.0, "shelves": 5},
                    {"width": "fill", "shelves": 5},
                ],
            },
        }
        config_file = tmp_path / "test_cabinet.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(config_file)

        assert len(config.cabinet.sections) == 3
        assert config.cabinet.sections[0].width == 24.0
        assert config.cabinet.sections[1].width == 24.0
        assert config.cabinet.sections[2].width == "fill"


class TestSectionSpecsWithCutList:
    """Tests for verifying cut list generation with section specs."""

    def test_cut_list_reflects_different_section_widths(self) -> None:
        """Test that cut list contains shelves with correct widths."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "material": {"thickness": 0.75},
                "sections": [
                    {"width": 24.0, "shelves": 2},
                    {"width": "fill", "shelves": 3},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid

        # Find shelf cut pieces
        shelf_pieces = [p for p in result.cut_list if "Shelf" in p.label]

        # Should have shelves with two different widths
        shelf_widths = set(round(p.width, 2) for p in shelf_pieces)
        assert 24.0 in shelf_widths  # Fixed width shelves
        assert round(45.75, 2) in shelf_widths  # Fill width shelves

    def test_cut_list_total_shelf_count(self) -> None:
        """Test that cut list has correct total number of shelves."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {"width": 24.0, "shelves": 3},
                    {"width": "fill", "shelves": 5},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid

        # Count total shelves
        total_shelves = sum(p.quantity for p in result.cut_list if "Shelf" in p.label)
        assert total_shelves == 8  # 3 + 5 shelves


class TestSectionSpecsErrorHandling:
    """Tests for error handling with invalid section configurations."""

    def test_fixed_widths_exceeding_total_returns_error(self) -> None:
        """Test that fixed widths exceeding available space returns error."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {"width": 30.0, "shelves": 3},
                    {"width": 30.0, "shelves": 3},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert not result.is_valid
        assert len(result.errors) >= 1
        assert any("exceed" in e.lower() for e in result.errors)


class TestLegacyCompatibility:
    """Tests to ensure backward compatibility with legacy generation."""

    def test_without_section_specs_uses_legacy_generation(self) -> None:
        """Test that not providing section specs uses legacy uniform sections."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        # Override to 3 sections with 4 shelves each (legacy style)
        params_input.num_sections = 3
        params_input.shelves_per_section = 4

        command = get_factory().create_generate_command()
        # Not providing section_specs should use legacy method
        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert len(result.cabinet.sections) == 3

        # All sections should have equal width and shelf count
        first_width = result.cabinet.sections[0].width
        for section in result.cabinet.sections:
            assert section.width == pytest.approx(first_width, rel=1e-6)
            assert len(section.shelves) == 4

    def test_section_specs_none_uses_legacy(self) -> None:
        """Test that None section_specs uses legacy generation."""
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        params_input.num_sections = 2
        params_input.shelves_per_section = 3

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=None)

        assert result.is_valid
        assert len(result.cabinet.sections) == 2
        for section in result.cabinet.sections:
            assert len(section.shelves) == 3


class TestFRDExampleConfigurations:
    """Tests using example configurations from the FRD."""

    def test_frd_bookcase_with_sections_example(self) -> None:
        """Test the bookcase with sections example from FRD."""
        # From FRD example:
        # {
        #   "schema_version": "1.0",
        #   "cabinet": {
        #     "width": 72,
        #     "height": 84,
        #     "depth": 12,
        #     "material": {"type": "plywood", "thickness": 0.75},
        #     "sections": [
        #       {"width": 24, "shelves": 5},
        #       {"width": 24, "shelves": 5},
        #       {"width": "fill", "shelves": 5}
        #     ]
        #   }
        # }
        config_data = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 72,
                "height": 84,
                "depth": 12,
                "material": {"type": "plywood", "thickness": 0.75},
                "sections": [
                    {"width": 24, "shelves": 5},
                    {"width": 24, "shelves": 5},
                    {"width": "fill", "shelves": 5},
                ],
            },
        }
        config = CabinetConfiguration.model_validate(config_data)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid
        assert len(result.cabinet.sections) == 3

        # Verify dimensions
        assert result.cabinet.sections[0].width == pytest.approx(24.0, rel=1e-6)
        assert result.cabinet.sections[1].width == pytest.approx(24.0, rel=1e-6)
        # 72" - 2*0.75" - 2*0.75" - 24 - 24 = 72 - 3 - 48 = 21"
        assert result.cabinet.sections[2].width == pytest.approx(21.0, rel=1e-6)

        # All sections have 5 shelves
        for section in result.cabinet.sections:
            assert len(section.shelves) == 5
