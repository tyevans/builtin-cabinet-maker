"""Unit tests for configuration merger and adapter.

These tests verify:
- CLI args override config values when provided
- CLI args are ignored when None
- Merged config maintains immutability
- Adapter correctly converts config to DTOs
"""

from pathlib import Path

import pytest

from cabinets.application.config import (
    CabinetConfig,
    CabinetConfiguration,
    MaterialConfig,
    OutputConfig,
    SectionConfig,
    config_to_dtos,
    merge_config_with_cli,
)
from cabinets.domain.value_objects import MaterialType


class TestMergeConfigWithCli:
    """Tests for merge_config_with_cli function."""

    @pytest.fixture
    def base_config(self) -> CabinetConfiguration:
        """Create a base configuration for testing."""
        return CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(type=MaterialType.PLYWOOD, thickness=0.75),
                sections=[
                    SectionConfig(width=20.0, shelves=3),
                    SectionConfig(width="fill", shelves=4),
                ],
            ),
            output=OutputConfig(format="all", stl_file="output.stl"),
        )

    def test_no_overrides_returns_equivalent_config(
        self, base_config: CabinetConfiguration
    ) -> None:
        """When no CLI args provided, merged config matches original."""
        merged = merge_config_with_cli(base_config)

        assert merged.schema_version == base_config.schema_version
        assert merged.cabinet.width == base_config.cabinet.width
        assert merged.cabinet.height == base_config.cabinet.height
        assert merged.cabinet.depth == base_config.cabinet.depth
        assert merged.cabinet.material.thickness == base_config.cabinet.material.thickness
        assert merged.output.format == base_config.output.format
        assert merged.output.stl_file == base_config.output.stl_file

    def test_override_width(self, base_config: CabinetConfiguration) -> None:
        """CLI width overrides config width."""
        merged = merge_config_with_cli(base_config, width=60.0)

        assert merged.cabinet.width == 60.0
        # Other values unchanged
        assert merged.cabinet.height == 84.0
        assert merged.cabinet.depth == 12.0

    def test_override_height(self, base_config: CabinetConfiguration) -> None:
        """CLI height overrides config height."""
        merged = merge_config_with_cli(base_config, height=96.0)

        assert merged.cabinet.height == 96.0
        assert merged.cabinet.width == 48.0

    def test_override_depth(self, base_config: CabinetConfiguration) -> None:
        """CLI depth overrides config depth."""
        merged = merge_config_with_cli(base_config, depth=16.0)

        assert merged.cabinet.depth == 16.0

    def test_override_material_thickness(
        self, base_config: CabinetConfiguration
    ) -> None:
        """CLI thickness overrides config material thickness."""
        merged = merge_config_with_cli(base_config, material_thickness=1.0)

        assert merged.cabinet.material.thickness == 1.0
        # Material type unchanged
        assert merged.cabinet.material.type == MaterialType.PLYWOOD

    def test_override_output_format(self, base_config: CabinetConfiguration) -> None:
        """CLI format overrides config output format."""
        merged = merge_config_with_cli(base_config, output_format="json")

        assert merged.output.format == "json"

    def test_override_stl_file_with_string(
        self, base_config: CabinetConfiguration
    ) -> None:
        """CLI stl_file as string overrides config stl_file."""
        merged = merge_config_with_cli(base_config, stl_file="new_output.stl")

        assert merged.output.stl_file == "new_output.stl"

    def test_override_stl_file_with_path(
        self, base_config: CabinetConfiguration
    ) -> None:
        """CLI stl_file as Path is converted to string."""
        merged = merge_config_with_cli(base_config, stl_file=Path("path/to/output.stl"))

        assert merged.output.stl_file == "path/to/output.stl"

    def test_multiple_overrides(self, base_config: CabinetConfiguration) -> None:
        """Multiple CLI args can override multiple values."""
        merged = merge_config_with_cli(
            base_config,
            width=72.0,
            height=96.0,
            depth=18.0,
            material_thickness=1.0,
            output_format="stl",
            stl_file="merged.stl",
        )

        assert merged.cabinet.width == 72.0
        assert merged.cabinet.height == 96.0
        assert merged.cabinet.depth == 18.0
        assert merged.cabinet.material.thickness == 1.0
        assert merged.output.format == "stl"
        assert merged.output.stl_file == "merged.stl"

    def test_sections_preserved(self, base_config: CabinetConfiguration) -> None:
        """Sections from config are preserved in merged config."""
        merged = merge_config_with_cli(base_config, width=60.0)

        assert len(merged.cabinet.sections) == 2
        assert merged.cabinet.sections[0].width == 20.0
        assert merged.cabinet.sections[0].shelves == 3
        assert merged.cabinet.sections[1].width == "fill"
        assert merged.cabinet.sections[1].shelves == 4

    def test_back_material_preserved(self) -> None:
        """Back material from config is preserved."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                back_material=MaterialConfig(type=MaterialType.PLYWOOD, thickness=0.25),
            ),
        )

        merged = merge_config_with_cli(config, width=60.0)

        assert merged.cabinet.back_material is not None
        assert merged.cabinet.back_material.thickness == 0.25

    def test_immutability_original_unchanged(
        self, base_config: CabinetConfiguration
    ) -> None:
        """Original config is not modified by merge."""
        original_width = base_config.cabinet.width
        merge_config_with_cli(base_config, width=100.0)

        # Original unchanged
        assert base_config.cabinet.width == original_width

    def test_none_stl_file_in_config(self) -> None:
        """Config with None stl_file doesn't cause issues."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            output=OutputConfig(format="all", stl_file=None),
        )

        merged = merge_config_with_cli(config)
        assert merged.output.stl_file is None

        # Override with value
        merged = merge_config_with_cli(config, stl_file="new.stl")
        assert merged.output.stl_file == "new.stl"


class TestConfigToDtos:
    """Tests for config_to_dtos adapter function."""

    def test_basic_conversion(self) -> None:
        """Basic config converts to correct DTOs."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(type=MaterialType.MDF, thickness=0.75),
            ),
        )

        wall_input, params_input = config_to_dtos(config)

        # Check WallInput
        assert wall_input.width == 48.0
        assert wall_input.height == 84.0
        assert wall_input.depth == 12.0

        # Check LayoutParametersInput
        assert params_input.material_thickness == 0.75
        assert params_input.material_type == "mdf"

    def test_num_sections_from_sections_list(self) -> None:
        """num_sections is derived from sections list length."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(shelves=3),
                    SectionConfig(shelves=4),
                    SectionConfig(shelves=5),
                ],
            ),
        )

        _, params_input = config_to_dtos(config)

        assert params_input.num_sections == 3

    def test_shelves_from_first_section(self) -> None:
        """shelves_per_section uses first section's value."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(shelves=5),
                    SectionConfig(shelves=3),
                ],
            ),
        )

        _, params_input = config_to_dtos(config)

        assert params_input.shelves_per_section == 5

    def test_empty_sections_defaults(self) -> None:
        """Empty sections list uses defaults."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[],
            ),
        )

        _, params_input = config_to_dtos(config)

        assert params_input.num_sections == 1
        assert params_input.shelves_per_section == 0

    def test_back_material_thickness(self) -> None:
        """Back thickness uses back_material when specified."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                back_material=MaterialConfig(thickness=0.25),
            ),
        )

        _, params_input = config_to_dtos(config)

        assert params_input.back_thickness == 0.25
        assert params_input.material_thickness == 0.75

    def test_back_material_defaults_to_main_material(self) -> None:
        """Back thickness defaults to main material thickness."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=1.0),
                back_material=None,
            ),
        )

        _, params_input = config_to_dtos(config)

        assert params_input.back_thickness == 1.0

    def test_material_type_conversion(self) -> None:
        """Material type enum converts to string value."""
        for material_type in MaterialType:
            config = CabinetConfiguration(
                schema_version="1.0",
                cabinet=CabinetConfig(
                    width=48.0,
                    height=84.0,
                    depth=12.0,
                    material=MaterialConfig(type=material_type),
                ),
            )

            _, params_input = config_to_dtos(config)

            assert params_input.material_type == material_type.value

    def test_dtos_are_valid(self) -> None:
        """Converted DTOs should pass their own validation."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(type=MaterialType.PLYWOOD, thickness=0.75),
                sections=[SectionConfig(shelves=3)],
            ),
        )

        wall_input, params_input = config_to_dtos(config)

        # DTOs have validate() methods that return list of errors
        wall_errors = wall_input.validate()
        params_errors = params_input.validate()

        assert wall_errors == []
        assert params_errors == []
