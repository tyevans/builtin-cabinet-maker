"""Unit tests for configuration schema and loader.

These tests verify:
- Valid configurations are loaded correctly
- Missing required fields produce clear errors
- Invalid types are rejected with appropriate messages
- Unknown fields are rejected (extra="forbid")
- Schema version pattern validation
- Loader error handling (file not found, JSON parse errors)
- Obstacle configuration models
- Clearance configuration models
- Height mode enum values
"""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError

from cabinets.application.config import (
    BinPackingConfigSchema,
    CabinetConfig,
    CabinetConfiguration,
    CeilingConfig,
    CeilingSlopeConfig,
    ClearanceConfig,
    ConfigError,
    HeightMode,
    MaterialConfig,
    ObstacleConfig,
    ObstacleDefaultsConfig,
    ObstacleTypeConfig,
    OutsideCornerConfigSchema,
    OutputConfig,
    RoomConfig,
    RowConfig,
    SectionConfig,
    SectionTypeConfig,
    SheetSizeConfigSchema,
    SkylightConfig,
    SUPPORTED_VERSIONS,
    ValidationResult,
    WallSegmentConfig,
    config_to_bin_packing,
    load_config,
    load_config_from_dict,
    validate_config,
)
from cabinets.domain.value_objects import MaterialType


# Get path to test fixtures
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "configs"


class TestMaterialConfig:
    """Tests for MaterialConfig model."""

    def test_defaults(self) -> None:
        """MaterialConfig should have sensible defaults."""
        config = MaterialConfig()
        assert config.type == MaterialType.PLYWOOD
        assert config.thickness == 0.75

    def test_valid_material_types(self) -> None:
        """All MaterialType values should be accepted."""
        for material_type in MaterialType:
            config = MaterialConfig(type=material_type)
            assert config.type == material_type

    def test_thickness_constraints(self) -> None:
        """Thickness should be constrained between 0.25 and 2.0."""
        # Valid thickness values
        for thickness in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
            config = MaterialConfig(thickness=thickness)
            assert config.thickness == thickness

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            MaterialConfig(thickness=0.1)
        assert "greater than or equal to 0.25" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MaterialConfig(thickness=3.0)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            MaterialConfig(type="plywood", color="red")  # type: ignore
        assert "color" in str(exc_info.value)


class TestSectionConfig:
    """Tests for SectionConfig model."""

    def test_defaults(self) -> None:
        """SectionConfig should have sensible defaults."""
        config = SectionConfig()
        assert config.width == "fill"
        assert config.shelves == 0

    def test_valid_numeric_width(self) -> None:
        """Positive numeric widths should be accepted."""
        config = SectionConfig(width=24.0)
        assert config.width == 24.0

    def test_fill_width(self) -> None:
        """Literal 'fill' should be accepted for width."""
        config = SectionConfig(width="fill")
        assert config.width == "fill"

    def test_rejects_non_positive_width(self) -> None:
        """Zero and negative widths should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(width=0)
        assert "width must be positive" in str(exc_info.value)

        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(width=-10)
        assert "width must be positive" in str(exc_info.value)

    def test_shelves_constraints(self) -> None:
        """Shelves should be constrained between 0 and 20."""
        # Valid values
        config = SectionConfig(shelves=0)
        assert config.shelves == 0

        config = SectionConfig(shelves=20)
        assert config.shelves == 20

        # Negative
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(shelves=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(shelves=21)
        assert "less than or equal to 20" in str(exc_info.value)

    def test_wall_field_optional(self) -> None:
        """Wall field should be optional and default to None."""
        config = SectionConfig()
        assert config.wall is None

    def test_wall_field_accepts_string(self) -> None:
        """Wall field should accept string values."""
        config = SectionConfig(wall="north_wall")
        assert config.wall == "north_wall"

    def test_wall_field_accepts_int(self) -> None:
        """Wall field should accept integer values."""
        config = SectionConfig(wall=0)
        assert config.wall == 0

        config = SectionConfig(wall=2)
        assert config.wall == 2


class TestWallSegmentConfig:
    """Tests for WallSegmentConfig model."""

    def test_required_fields(self) -> None:
        """Length and height are required fields."""
        # Valid config with required fields
        config = WallSegmentConfig(length=120.0, height=96.0)
        assert config.length == 120.0
        assert config.height == 96.0

        # Missing length
        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(height=96.0)  # type: ignore
        assert "length" in str(exc_info.value)

        # Missing height
        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=120.0)  # type: ignore
        assert "height" in str(exc_info.value)

    def test_defaults(self) -> None:
        """WallSegmentConfig should have sensible defaults."""
        config = WallSegmentConfig(length=120.0, height=96.0)
        assert config.angle == 0.0
        assert config.name is None
        assert config.depth == 12.0

    def test_length_must_be_positive(self) -> None:
        """Length must be greater than 0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=0, height=96.0)
        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=-10.0, height=96.0)
        assert "greater than 0" in str(exc_info.value)

    def test_height_must_be_positive(self) -> None:
        """Height must be greater than 0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=120.0, height=0)
        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=120.0, height=-10.0)
        assert "greater than 0" in str(exc_info.value)

    def test_depth_must_be_positive(self) -> None:
        """Depth must be greater than 0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=120.0, height=96.0, depth=0)
        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=120.0, height=96.0, depth=-5.0)
        assert "greater than 0" in str(exc_info.value)

    def test_valid_angles(self) -> None:
        """Angle must be between -135 and 135 degrees."""
        for angle in [-135, -90, -45, 0, 45, 90, 120, 135]:
            config = WallSegmentConfig(length=120.0, height=96.0, angle=angle)
            assert config.angle == angle

    def test_invalid_angles(self) -> None:
        """Angles outside -135 to 135 range should be rejected."""
        for angle in [-180, -150, 150, 180]:
            with pytest.raises(PydanticValidationError) as exc_info:
                WallSegmentConfig(length=120.0, height=96.0, angle=angle)
            assert "Angle must be between -135 and 135 degrees" in str(exc_info.value)

    def test_name_optional(self) -> None:
        """Name should be optional."""
        config = WallSegmentConfig(length=120.0, height=96.0, name="north_wall")
        assert config.name == "north_wall"

        config = WallSegmentConfig(length=120.0, height=96.0)
        assert config.name is None

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            WallSegmentConfig(length=120.0, height=96.0, color="red")  # type: ignore
        assert "color" in str(exc_info.value)


class TestRoomConfig:
    """Tests for RoomConfig model."""

    def test_required_fields(self) -> None:
        """Name and walls are required fields."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        config = RoomConfig(name="living_room", walls=[wall])
        assert config.name == "living_room"
        assert len(config.walls) == 1

        # Missing name
        with pytest.raises(PydanticValidationError) as exc_info:
            RoomConfig(walls=[wall])  # type: ignore
        assert "name" in str(exc_info.value)

        # Missing walls
        with pytest.raises(PydanticValidationError) as exc_info:
            RoomConfig(name="test")  # type: ignore
        assert "walls" in str(exc_info.value)

    def test_defaults(self) -> None:
        """RoomConfig should have sensible defaults."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        config = RoomConfig(name="test", walls=[wall])
        assert config.is_closed is False

    def test_name_cannot_be_empty(self) -> None:
        """Name must have at least 1 character."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        with pytest.raises(PydanticValidationError) as exc_info:
            RoomConfig(name="", walls=[wall])
        assert "min_length" in str(exc_info.value) or "at least 1" in str(exc_info.value)

    def test_walls_cannot_be_empty(self) -> None:
        """Walls list must have at least 1 wall."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RoomConfig(name="test", walls=[])
        assert "min_length" in str(exc_info.value) or "at least 1" in str(exc_info.value)

    def test_first_wall_must_have_zero_angle(self) -> None:
        """First wall must have angle=0."""
        wall_with_angle = WallSegmentConfig(length=120.0, height=96.0, angle=90)
        with pytest.raises(PydanticValidationError) as exc_info:
            RoomConfig(name="test", walls=[wall_with_angle])
        assert "First wall must have angle=0" in str(exc_info.value)

    def test_subsequent_walls_can_have_angles(self) -> None:
        """Subsequent walls can have non-zero angles."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=90)
        wall3 = WallSegmentConfig(length=120.0, height=96.0, angle=-90)
        config = RoomConfig(name="l_shaped", walls=[wall1, wall2, wall3])
        assert len(config.walls) == 3
        assert config.walls[1].angle == 90
        assert config.walls[2].angle == -90

    def test_is_closed_flag(self) -> None:
        """is_closed flag should be settable."""
        wall1 = WallSegmentConfig(length=100.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=100.0, height=96.0, angle=90)
        wall3 = WallSegmentConfig(length=100.0, height=96.0, angle=90)
        wall4 = WallSegmentConfig(length=100.0, height=96.0, angle=90)
        config = RoomConfig(name="square", walls=[wall1, wall2, wall3, wall4], is_closed=True)
        assert config.is_closed is True

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        with pytest.raises(PydanticValidationError) as exc_info:
            RoomConfig(name="test", walls=[wall], floor_material="wood")  # type: ignore
        assert "floor_material" in str(exc_info.value)


class TestCabinetConfig:
    """Tests for CabinetConfig model."""

    def test_required_dimensions(self) -> None:
        """Width, height, and depth are required."""
        # All provided - should work
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0)
        assert config.width == 48.0
        assert config.height == 84.0
        assert config.depth == 12.0

        # Missing width
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfig(height=84.0, depth=12.0)  # type: ignore
        assert "width" in str(exc_info.value)

        # Missing height
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfig(width=48.0, depth=12.0)  # type: ignore
        assert "height" in str(exc_info.value)

        # Missing depth
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfig(width=48.0, height=84.0)  # type: ignore
        assert "depth" in str(exc_info.value)

    def test_dimension_constraints(self) -> None:
        """Dimensions should be within allowed ranges."""
        # Width constraints (6.0 - 240.0)
        config = CabinetConfig(width=6.0, height=10.0, depth=4.0)
        assert config.width == 6.0

        config = CabinetConfig(width=240.0, height=10.0, depth=4.0)
        assert config.width == 240.0

        with pytest.raises(PydanticValidationError):
            CabinetConfig(width=5.0, height=10.0, depth=4.0)

        with pytest.raises(PydanticValidationError):
            CabinetConfig(width=241.0, height=10.0, depth=4.0)

        # Height constraints (6.0 - 120.0)
        with pytest.raises(PydanticValidationError):
            CabinetConfig(width=48.0, height=5.0, depth=12.0)

        with pytest.raises(PydanticValidationError):
            CabinetConfig(width=48.0, height=121.0, depth=12.0)

        # Depth constraints (4.0 - 36.0)
        with pytest.raises(PydanticValidationError):
            CabinetConfig(width=48.0, height=84.0, depth=3.0)

        with pytest.raises(PydanticValidationError):
            CabinetConfig(width=48.0, height=84.0, depth=37.0)

    def test_default_material(self) -> None:
        """Material should default to standard plywood."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0)
        assert config.material.type == MaterialType.PLYWOOD
        assert config.material.thickness == 0.75

    def test_back_material_optional(self) -> None:
        """Back material should be optional."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0)
        assert config.back_material is None

        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            back_material=MaterialConfig(thickness=0.25),
        )
        assert config.back_material is not None
        assert config.back_material.thickness == 0.25

    def test_sections_default_empty(self) -> None:
        """Sections should default to empty list."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0)
        assert config.sections == []

    def test_sections_max_length(self) -> None:
        """Sections list should have maximum 20 sections."""
        sections = [SectionConfig() for _ in range(20)]
        config = CabinetConfig(width=240.0, height=84.0, depth=12.0, sections=sections)
        assert len(config.sections) == 20

        with pytest.raises(PydanticValidationError) as exc_info:
            sections = [SectionConfig() for _ in range(21)]
            CabinetConfig(width=240.0, height=84.0, depth=12.0, sections=sections)
        assert "20" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfig(width=48.0, height=84.0, depth=12.0, color="red")  # type: ignore
        assert "color" in str(exc_info.value)


class TestOutputConfig:
    """Tests for OutputConfig model."""

    def test_defaults(self) -> None:
        """OutputConfig should have sensible defaults."""
        config = OutputConfig()
        assert config.format == "all"
        assert config.stl_file is None

    def test_valid_formats(self) -> None:
        """All valid format values should be accepted."""
        for fmt in ["all", "cutlist", "diagram", "materials", "json", "stl", "cutlayout", "woodworking"]:
            config = OutputConfig(format=fmt)  # type: ignore
            assert config.format == fmt

    def test_invalid_format(self) -> None:
        """Invalid format values should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutputConfig(format="invalid")  # type: ignore
        assert "format" in str(exc_info.value)


class TestCabinetConfiguration:
    """Tests for root CabinetConfiguration model."""

    def test_minimal_valid_config(self) -> None:
        """Minimal valid configuration should load successfully."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.0"
        assert config.cabinet.width == 48.0

    def test_schema_version_required(self) -> None:
        """schema_version is required."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfiguration(
                cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0)
            )  # type: ignore
        assert "schema_version" in str(exc_info.value)

    def test_schema_version_pattern(self) -> None:
        """schema_version must match pattern major.minor."""
        # Valid patterns
        for version in ["1.0", "1.1", "2.0", "10.20"]:
            # Note: only 1.x is actually supported, but pattern validation comes first
            try:
                config = CabinetConfiguration(
                    schema_version=version,
                    cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
                )
                # Only 1.x should pass the version check
                if not version.startswith("1."):
                    pytest.fail(f"Expected unsupported version error for {version}")
            except PydanticValidationError as e:
                # For non-1.x versions, we should get unsupported version error
                if version.startswith("1."):
                    raise
                assert "Unsupported schema version" in str(e)

        # Invalid patterns
        for version in ["1", "v1.0", "1.0.0", "latest", ""]:
            with pytest.raises(PydanticValidationError) as exc_info:
                CabinetConfiguration(
                    schema_version=version,
                    cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
                )
            # Pattern validation error
            assert "schema_version" in str(exc_info.value) or "pattern" in str(exc_info.value).lower()

    def test_unsupported_version(self) -> None:
        """Unsupported schema versions should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfiguration(
                schema_version="2.0",
                cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            )
        assert "Unsupported schema version" in str(exc_info.value)

    def test_output_defaults(self) -> None:
        """Output should have default values if not specified."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.output.format == "all"
        assert config.output.stl_file is None

    def test_rejects_unknown_root_fields(self) -> None:
        """Unknown root fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfiguration(
                schema_version="1.0",
                cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
                metadata={"author": "test"},  # type: ignore
            )
        assert "metadata" in str(exc_info.value)

    def test_room_optional(self) -> None:
        """Room should be optional and default to None."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.room is None

    def test_room_with_single_wall(self) -> None:
        """Room with a single wall should be valid."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="closet", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        assert config.room is not None
        assert config.room.name == "closet"
        assert len(config.room.walls) == 1

    def test_room_with_multiple_walls(self) -> None:
        """Room with multiple walls including angles should be valid."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0, name="north")
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=90, name="east")
        wall3 = WallSegmentConfig(length=120.0, height=96.0, angle=90, name="south")
        room = RoomConfig(name="l_shaped_room", walls=[wall1, wall2, wall3])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        assert config.room is not None
        assert len(config.room.walls) == 3
        assert config.room.walls[0].name == "north"
        assert config.room.walls[1].angle == 90

    def test_backward_compatibility_v1_0_without_room(self) -> None:
        """v1.0 configurations without room should still work."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0), SectionConfig(width="fill")],
            ),
        )
        assert config.schema_version == "1.0"
        assert config.room is None
        assert len(config.cabinet.sections) == 2

    def test_v1_1_schema_version_valid(self) -> None:
        """v1.1 schema version should be accepted."""
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.1"

    def test_section_with_wall_reference(self) -> None:
        """Sections can reference walls by name or index."""
        wall = WallSegmentConfig(length=120.0, height=96.0, name="main_wall")
        room = RoomConfig(name="study", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, wall="main_wall"),
                    SectionConfig(width="fill", wall=0),
                ],
            ),
            room=room,
        )
        assert config.cabinet.sections[0].wall == "main_wall"
        assert config.cabinet.sections[1].wall == 0


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_minimal_config(self) -> None:
        """Valid minimal config file should load successfully."""
        config = load_config(FIXTURES_PATH / "valid_minimal.json")
        assert config.schema_version == "1.0"
        assert config.cabinet.width == 48.0
        assert config.cabinet.height == 84.0
        assert config.cabinet.depth == 12.0

    def test_load_valid_full_config(self) -> None:
        """Valid full config file should load with all values."""
        config = load_config(FIXTURES_PATH / "valid_full.json")
        assert config.schema_version == "1.0"
        assert config.cabinet.width == 72.0
        assert len(config.cabinet.sections) == 3
        assert config.cabinet.sections[0].width == 24.0
        assert config.cabinet.sections[2].width == "fill"
        assert config.output.format == "all"
        assert config.output.stl_file == "cabinet.stl"

    def test_file_not_found(self) -> None:
        """Non-existent file should raise ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            load_config(FIXTURES_PATH / "nonexistent.json")

        error = exc_info.value
        assert error.error_type == "file_not_found"
        assert "Config file not found" in error.message

    def test_invalid_json(self) -> None:
        """Invalid JSON should raise ConfigError with line/column info."""
        with pytest.raises(ConfigError) as exc_info:
            load_config(FIXTURES_PATH / "invalid_json.json")

        error = exc_info.value
        assert error.error_type == "json_parse"
        assert "Invalid JSON" in error.message
        assert "line" in error.message.lower()
        assert len(error.details) > 0
        assert "line" in error.details[0]

    def test_unknown_field_rejected(self) -> None:
        """Unknown fields should cause validation error."""
        with pytest.raises(ConfigError) as exc_info:
            load_config(FIXTURES_PATH / "unknown_field.json")

        error = exc_info.value
        assert error.error_type == "validation"
        # Check that the error mentions the unknown field
        assert "color" in error.message.lower() or any(
            "color" in str(d.get("path", "")).lower()
            or "color" in str(d.get("message", "")).lower()
            for d in error.details
        )


class TestLoadConfigFromDict:
    """Tests for load_config_from_dict function."""

    def test_valid_dict(self) -> None:
        """Valid dictionary should load successfully."""
        data: dict[str, Any] = {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config = load_config_from_dict(data)
        assert config.schema_version == "1.0"
        assert config.cabinet.width == 48.0

    def test_invalid_dict(self) -> None:
        """Invalid dictionary should raise ConfigError."""
        data: dict[str, Any] = {
            "schema_version": "1.0",
            "cabinet": {
                "width": -10.0,  # Invalid
                "height": 84.0,
                "depth": 12.0,
            },
        }
        with pytest.raises(ConfigError) as exc_info:
            load_config_from_dict(data)

        error = exc_info.value
        assert error.error_type == "validation"
        assert "cabinet.width" in error.message


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_empty_result_is_valid(self) -> None:
        """Empty result should be valid with exit code 0."""
        result = ValidationResult()
        assert result.is_valid
        assert not result.has_warnings
        assert result.exit_code == 0

    def test_with_errors(self) -> None:
        """Result with errors should have exit code 1."""
        result = ValidationResult()
        result.add_error("path", "message", "value")
        assert not result.is_valid
        assert result.exit_code == 1

    def test_with_warnings_only(self) -> None:
        """Result with only warnings should have exit code 2."""
        result = ValidationResult()
        result.add_warning("path", "message", "suggestion")
        assert result.is_valid
        assert result.has_warnings
        assert result.exit_code == 2

    def test_errors_take_precedence(self) -> None:
        """Errors should take precedence over warnings for exit code."""
        result = ValidationResult()
        result.add_warning("path", "warning")
        result.add_error("path", "error")
        assert result.exit_code == 1


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config_no_warnings(self) -> None:
        """Valid config with good practices should have no warnings."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=36.0,
                height=48.0,
                depth=12.0,
                sections=[SectionConfig(width=32.0, shelves=3)],
            ),
        )
        result = validate_config(config)
        assert result.is_valid
        # No warnings for a well-designed cabinet

    def test_shelf_span_warning(self) -> None:
        """Wide shelf span should trigger warning."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                sections=[SectionConfig(width=42.0, shelves=3)],
            ),
        )
        result = validate_config(config)
        assert result.is_valid  # Valid but with warning
        assert result.has_warnings
        assert any("span" in w.message.lower() for w in result.warnings)

    def test_thin_material_warning(self) -> None:
        """Very thin material should trigger warning."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=36.0,
                height=48.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.25),
            ),
        )
        result = validate_config(config)
        assert result.is_valid
        assert any("thin" in w.message.lower() or "thickness" in w.message.lower() for w in result.warnings)

    def test_aspect_ratio_warning(self) -> None:
        """Extreme height-to-depth ratio should trigger warning."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=36.0,
                height=84.0,  # Very tall
                depth=10.0,  # Very shallow - ratio > 4:1
            ),
        )
        result = validate_config(config)
        assert result.is_valid
        assert any("ratio" in w.message.lower() or "stability" in w.message.lower() for w in result.warnings)

    def test_fixed_sections_exceed_width_error(self) -> None:
        """Fixed section widths exceeding cabinet should error."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                sections=[
                    SectionConfig(width=25.0, shelves=3),
                    SectionConfig(width=25.0, shelves=3),
                ],
            ),
        )
        result = validate_config(config)
        # Total fixed width (50) exceeds available space (~44.25)
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("exceed" in e.message.lower() for e in result.errors)

    def test_section_depth_exceeds_cabinet_depth_error(self) -> None:
        """Section depth exceeding cabinet depth should error (FR-06.3)."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,  # Cabinet is 12" deep
                material=MaterialConfig(thickness=0.75),
                sections=[
                    SectionConfig(width=20.0, shelves=3, depth=15.0),  # 15" > 12"
                ],
            ),
        )
        result = validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("depth" in e.message.lower() and "exceed" in e.message.lower() for e in result.errors)
        assert any("sections[0].depth" in e.path for e in result.errors)

    def test_section_depth_at_cabinet_depth_valid(self) -> None:
        """Section depth equal to cabinet depth should be valid."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                sections=[
                    SectionConfig(width=20.0, shelves=3, depth=12.0),  # Equal to cabinet
                ],
            ),
        )
        result = validate_config(config)
        # Should be valid (no depth errors)
        depth_errors = [e for e in result.errors if "depth" in e.message.lower() and "exceed" in e.message.lower()]
        assert len(depth_errors) == 0

    def test_section_depth_below_cabinet_depth_valid(self) -> None:
        """Section depth below cabinet depth should be valid (shallower section)."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                sections=[
                    SectionConfig(width=20.0, shelves=3, depth=8.0),  # Shallower section
                ],
            ),
        )
        result = validate_config(config)
        # Should be valid (no depth errors)
        depth_errors = [e for e in result.errors if "depth" in e.message.lower() and "exceed" in e.message.lower()]
        assert len(depth_errors) == 0

    def test_multiple_sections_depth_validation(self) -> None:
        """Multiple sections with depth issues should all report errors."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                sections=[
                    SectionConfig(width=20.0, shelves=3, depth=8.0),   # Valid
                    SectionConfig(width=20.0, shelves=3, depth=15.0),  # Invalid
                    SectionConfig(width=20.0, shelves=3, depth=18.0),  # Invalid
                ],
            ),
        )
        result = validate_config(config)
        assert not result.is_valid
        depth_errors = [e for e in result.errors if "depth" in e.message.lower() and "exceed" in e.message.lower()]
        assert len(depth_errors) == 2  # sections[1] and sections[2]
        assert any("sections[1].depth" in e.path for e in depth_errors)
        assert any("sections[2].depth" in e.path for e in depth_errors)

    def test_multirow_section_depth_exceeds_cabinet_depth_error(self) -> None:
        """Section depth in multi-row layout exceeding cabinet depth should error (FR-06.3)."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(thickness=0.75),
                rows=[
                    RowConfig(
                        height=30.0,
                        sections=[
                            SectionConfig(width="fill", shelves=3, depth=10.0),  # Valid
                        ],
                    ),
                    RowConfig(
                        height="fill",
                        sections=[
                            SectionConfig(width=20.0, shelves=2, depth=8.0),   # Valid
                            SectionConfig(width="fill", shelves=2, depth=16.0),  # Invalid: 16 > 12
                        ],
                    ),
                ],
            ),
        )
        result = validate_config(config)
        assert not result.is_valid
        depth_errors = [e for e in result.errors if "depth" in e.message.lower() and "exceed" in e.message.lower()]
        assert len(depth_errors) == 1
        assert any("rows[1].sections[1].depth" in e.path for e in depth_errors)


class TestObstacleTypeConfig:
    """Tests for ObstacleTypeConfig enum."""

    def test_obstacle_type_values(self) -> None:
        """ObstacleTypeConfig should have all expected values."""
        assert ObstacleTypeConfig.WINDOW.value == "window"
        assert ObstacleTypeConfig.DOOR.value == "door"
        assert ObstacleTypeConfig.OUTLET.value == "outlet"
        assert ObstacleTypeConfig.SWITCH.value == "switch"
        assert ObstacleTypeConfig.VENT.value == "vent"
        assert ObstacleTypeConfig.SKYLIGHT.value == "skylight"
        assert ObstacleTypeConfig.CUSTOM.value == "custom"

    def test_obstacle_type_count(self) -> None:
        """ObstacleTypeConfig should have exactly 7 values."""
        assert len(ObstacleTypeConfig) == 7


class TestHeightMode:
    """Tests for HeightMode enum."""

    def test_height_mode_values(self) -> None:
        """HeightMode should have all expected values."""
        assert HeightMode.FULL.value == "full"
        assert HeightMode.LOWER.value == "lower"
        assert HeightMode.UPPER.value == "upper"
        assert HeightMode.AUTO.value == "auto"

    def test_height_mode_count(self) -> None:
        """HeightMode should have exactly 4 values."""
        assert len(HeightMode) == 4


class TestClearanceConfig:
    """Tests for ClearanceConfig model."""

    def test_defaults(self) -> None:
        """ClearanceConfig should default to zero on all sides."""
        config = ClearanceConfig()
        assert config.top == 0.0
        assert config.bottom == 0.0
        assert config.left == 0.0
        assert config.right == 0.0

    def test_custom_values(self) -> None:
        """ClearanceConfig should accept custom values."""
        config = ClearanceConfig(top=2.0, bottom=1.0, left=3.0, right=4.0)
        assert config.top == 2.0
        assert config.bottom == 1.0
        assert config.left == 3.0
        assert config.right == 4.0

    def test_rejects_negative_top(self) -> None:
        """ClearanceConfig should reject negative top value."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ClearanceConfig(top=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_negative_bottom(self) -> None:
        """ClearanceConfig should reject negative bottom value."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ClearanceConfig(bottom=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_negative_left(self) -> None:
        """ClearanceConfig should reject negative left value."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ClearanceConfig(left=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_negative_right(self) -> None:
        """ClearanceConfig should reject negative right value."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ClearanceConfig(right=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ClearanceConfig(side=2.0)  # type: ignore
        assert "side" in str(exc_info.value)


class TestObstacleConfig:
    """Tests for ObstacleConfig model."""

    def test_valid_obstacle_minimal(self) -> None:
        """ObstacleConfig with only required fields should be valid."""
        config = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        assert config.type == ObstacleTypeConfig.WINDOW
        assert config.wall == 0
        assert config.horizontal_offset == 24.0
        assert config.bottom == 36.0
        assert config.width == 48.0
        assert config.height == 36.0
        assert config.clearance is None
        assert config.name is None

    def test_valid_obstacle_full(self) -> None:
        """ObstacleConfig with all fields should be valid."""
        clearance = ClearanceConfig(top=3.0, bottom=3.0, left=3.0, right=3.0)
        config = ObstacleConfig(
            type=ObstacleTypeConfig.DOOR,
            wall=1,
            horizontal_offset=0.0,
            bottom=0.0,
            width=36.0,
            height=80.0,
            clearance=clearance,
            name="entry_door",
        )
        assert config.type == ObstacleTypeConfig.DOOR
        assert config.clearance == clearance
        assert config.name == "entry_door"

    def test_rejects_negative_wall_index(self) -> None:
        """ObstacleConfig should reject negative wall index."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=-1,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_negative_horizontal_offset(self) -> None:
        """ObstacleConfig should reject negative horizontal_offset."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=-5.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_negative_bottom(self) -> None:
        """ObstacleConfig should reject negative bottom."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=24.0,
                bottom=-5.0,
                width=48.0,
                height=36.0,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_zero_width(self) -> None:
        """ObstacleConfig should reject zero width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=0,
                height=36.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_negative_width(self) -> None:
        """ObstacleConfig should reject negative width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=-10.0,
                height=36.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_zero_height(self) -> None:
        """ObstacleConfig should reject zero height."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_negative_height(self) -> None:
        """ObstacleConfig should reject negative height."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=-5.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_allows_zero_offset_and_bottom(self) -> None:
        """ObstacleConfig should allow zero offset and bottom (corner placement)."""
        config = ObstacleConfig(
            type=ObstacleTypeConfig.DOOR,
            wall=0,
            horizontal_offset=0.0,
            bottom=0.0,
            width=36.0,
            height=80.0,
        )
        assert config.horizontal_offset == 0.0
        assert config.bottom == 0.0

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleConfig(
                type=ObstacleTypeConfig.WINDOW,
                wall=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
                color="red",  # type: ignore
            )
        assert "color" in str(exc_info.value)


class TestObstacleDefaultsConfig:
    """Tests for ObstacleDefaultsConfig model."""

    def test_all_none_by_default(self) -> None:
        """ObstacleDefaultsConfig should have all fields as None by default."""
        config = ObstacleDefaultsConfig()
        assert config.window is None
        assert config.door is None
        assert config.outlet is None
        assert config.switch is None
        assert config.vent is None
        assert config.skylight is None
        assert config.custom is None

    def test_set_specific_defaults(self) -> None:
        """ObstacleDefaultsConfig should accept specific clearance overrides."""
        window_clearance = ClearanceConfig(top=4.0, bottom=4.0, left=4.0, right=4.0)
        door_clearance = ClearanceConfig(top=0.0, bottom=0.0, left=3.0, right=3.0)
        config = ObstacleDefaultsConfig(window=window_clearance, door=door_clearance)
        assert config.window == window_clearance
        assert config.door == door_clearance
        assert config.outlet is None

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ObstacleDefaultsConfig(window_frame=ClearanceConfig())  # type: ignore
        assert "window_frame" in str(exc_info.value)


class TestSectionConfigHeightMode:
    """Tests for SectionConfig height_mode field."""

    def test_height_mode_default_none(self) -> None:
        """SectionConfig height_mode should default to None."""
        config = SectionConfig()
        assert config.height_mode is None

    def test_height_mode_full(self) -> None:
        """SectionConfig should accept full height mode."""
        config = SectionConfig(height_mode=HeightMode.FULL)
        assert config.height_mode == HeightMode.FULL

    def test_height_mode_lower(self) -> None:
        """SectionConfig should accept lower height mode."""
        config = SectionConfig(height_mode=HeightMode.LOWER)
        assert config.height_mode == HeightMode.LOWER

    def test_height_mode_upper(self) -> None:
        """SectionConfig should accept upper height mode."""
        config = SectionConfig(height_mode=HeightMode.UPPER)
        assert config.height_mode == HeightMode.UPPER

    def test_height_mode_auto(self) -> None:
        """SectionConfig should accept auto height mode."""
        config = SectionConfig(height_mode=HeightMode.AUTO)
        assert config.height_mode == HeightMode.AUTO

    def test_height_mode_from_string(self) -> None:
        """SectionConfig should accept height mode as string."""
        config = SectionConfig(height_mode="lower")  # type: ignore
        assert config.height_mode == HeightMode.LOWER


class TestRoomConfigObstacles:
    """Tests for RoomConfig obstacles field."""

    def test_obstacles_default_empty(self) -> None:
        """RoomConfig obstacles should default to empty list."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        config = RoomConfig(name="test", walls=[wall])
        assert config.obstacles == []

    def test_obstacles_with_single_obstacle(self) -> None:
        """RoomConfig should accept a single obstacle."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        config = RoomConfig(name="test", walls=[wall], obstacles=[obstacle])
        assert len(config.obstacles) == 1
        assert config.obstacles[0].type == ObstacleTypeConfig.WINDOW

    def test_obstacles_with_multiple_obstacles(self) -> None:
        """RoomConfig should accept multiple obstacles."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        window = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        outlet = ObstacleConfig(
            type=ObstacleTypeConfig.OUTLET,
            wall=0,
            horizontal_offset=10.0,
            bottom=12.0,
            width=4.0,
            height=4.0,
        )
        config = RoomConfig(name="test", walls=[wall], obstacles=[window, outlet])
        assert len(config.obstacles) == 2


class TestCabinetConfigurationObstacleDefaults:
    """Tests for CabinetConfiguration obstacle_defaults field."""

    def test_obstacle_defaults_optional(self) -> None:
        """obstacle_defaults should be optional and default to None."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.obstacle_defaults is None

    def test_obstacle_defaults_can_be_set(self) -> None:
        """obstacle_defaults should accept ObstacleDefaultsConfig."""
        defaults = ObstacleDefaultsConfig(
            window=ClearanceConfig(top=3.0, bottom=3.0, left=3.0, right=3.0)
        )
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            obstacle_defaults=defaults,
        )
        assert config.obstacle_defaults is not None
        assert config.obstacle_defaults.window is not None
        assert config.obstacle_defaults.window.top == 3.0

    def test_room_with_obstacles_and_defaults(self) -> None:
        """Full configuration with room, obstacles, and defaults should be valid."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        obstacle = ObstacleConfig(
            type=ObstacleTypeConfig.WINDOW,
            wall=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        room = RoomConfig(name="kitchen", walls=[wall], obstacles=[obstacle])
        defaults = ObstacleDefaultsConfig(
            window=ClearanceConfig(top=4.0, bottom=4.0, left=4.0, right=4.0)
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
            obstacle_defaults=defaults,
        )
        assert config.room is not None
        assert len(config.room.obstacles) == 1
        assert config.obstacle_defaults is not None


class TestSectionTypeConfig:
    """Tests for SectionTypeConfig enum (FRD-04)."""

    def test_section_type_config_values(self) -> None:
        """SectionTypeConfig should have all expected values."""
        assert SectionTypeConfig.OPEN.value == "open"
        assert SectionTypeConfig.DOORED.value == "doored"
        assert SectionTypeConfig.DRAWERS.value == "drawers"
        assert SectionTypeConfig.CUBBY.value == "cubby"

    def test_section_type_config_count(self) -> None:
        """SectionTypeConfig should have exactly 4 values."""
        assert len(SectionTypeConfig) == 4

    def test_section_type_config_from_value(self) -> None:
        """SectionTypeConfig should be creatable from string values."""
        assert SectionTypeConfig("open") == SectionTypeConfig.OPEN
        assert SectionTypeConfig("doored") == SectionTypeConfig.DOORED
        assert SectionTypeConfig("drawers") == SectionTypeConfig.DRAWERS
        assert SectionTypeConfig("cubby") == SectionTypeConfig.CUBBY


class TestSectionConfigFRD04:
    """Tests for SectionConfig new fields (FRD-04)."""

    def test_section_type_default(self) -> None:
        """SectionConfig section_type should default to OPEN."""
        config = SectionConfig()
        assert config.section_type == SectionTypeConfig.OPEN

    def test_section_type_open(self) -> None:
        """SectionConfig should accept OPEN section type."""
        config = SectionConfig(section_type=SectionTypeConfig.OPEN)
        assert config.section_type == SectionTypeConfig.OPEN

    def test_section_type_doored(self) -> None:
        """SectionConfig should accept DOORED section type."""
        config = SectionConfig(section_type=SectionTypeConfig.DOORED)
        assert config.section_type == SectionTypeConfig.DOORED

    def test_section_type_drawers(self) -> None:
        """SectionConfig should accept DRAWERS section type."""
        config = SectionConfig(section_type=SectionTypeConfig.DRAWERS)
        assert config.section_type == SectionTypeConfig.DRAWERS

    def test_section_type_cubby(self) -> None:
        """SectionConfig should accept CUBBY section type."""
        config = SectionConfig(section_type=SectionTypeConfig.CUBBY)
        assert config.section_type == SectionTypeConfig.CUBBY

    def test_section_type_from_string(self) -> None:
        """SectionConfig should accept section_type as string."""
        config = SectionConfig(section_type="doored")  # type: ignore
        assert config.section_type == SectionTypeConfig.DOORED

    def test_depth_default_none(self) -> None:
        """SectionConfig depth should default to None."""
        config = SectionConfig()
        assert config.depth is None

    def test_depth_with_valid_value(self) -> None:
        """SectionConfig should accept valid positive depth."""
        config = SectionConfig(depth=10.0)
        assert config.depth == 10.0

    def test_depth_zero_raises_error(self) -> None:
        """SectionConfig should reject zero depth."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(depth=0)
        assert "greater than 0" in str(exc_info.value)

    def test_depth_negative_raises_error(self) -> None:
        """SectionConfig should reject negative depth."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(depth=-5.0)
        assert "greater than 0" in str(exc_info.value)

    def test_min_width_default(self) -> None:
        """SectionConfig min_width should default to 6.0."""
        config = SectionConfig()
        assert config.min_width == 6.0

    def test_min_width_custom_value(self) -> None:
        """SectionConfig should accept custom min_width."""
        config = SectionConfig(min_width=12.0)
        assert config.min_width == 12.0

    def test_min_width_zero_raises_error(self) -> None:
        """SectionConfig should reject zero min_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(min_width=0)
        assert "greater than 0" in str(exc_info.value)

    def test_min_width_negative_raises_error(self) -> None:
        """SectionConfig should reject negative min_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(min_width=-5.0)
        assert "greater than 0" in str(exc_info.value)

    def test_max_width_default_none(self) -> None:
        """SectionConfig max_width should default to None."""
        config = SectionConfig()
        assert config.max_width is None

    def test_max_width_custom_value(self) -> None:
        """SectionConfig should accept custom max_width."""
        config = SectionConfig(max_width=36.0)
        assert config.max_width == 36.0

    def test_max_width_zero_raises_error(self) -> None:
        """SectionConfig should reject zero max_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(max_width=0)
        assert "greater than 0" in str(exc_info.value)

    def test_max_width_negative_raises_error(self) -> None:
        """SectionConfig should reject negative max_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(max_width=-5.0)
        assert "greater than 0" in str(exc_info.value)

    def test_max_width_less_than_min_width_raises_error(self) -> None:
        """SectionConfig should reject max_width < min_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SectionConfig(min_width=20.0, max_width=15.0)
        assert "max_width" in str(exc_info.value) and "min_width" in str(exc_info.value)

    def test_max_width_equal_to_min_width_valid(self) -> None:
        """SectionConfig should accept max_width equal to min_width."""
        config = SectionConfig(min_width=20.0, max_width=20.0)
        assert config.min_width == 20.0
        assert config.max_width == 20.0

    def test_all_new_fields_together(self) -> None:
        """SectionConfig should accept all new FRD-04 fields together."""
        config = SectionConfig(
            width=24.0,
            shelves=3,
            section_type=SectionTypeConfig.DOORED,
            depth=10.0,
            min_width=12.0,
            max_width=36.0,
        )
        assert config.width == 24.0
        assert config.shelves == 3
        assert config.section_type == SectionTypeConfig.DOORED
        assert config.depth == 10.0
        assert config.min_width == 12.0
        assert config.max_width == 36.0

    def test_section_type_with_fill_width(self) -> None:
        """SectionConfig should accept section_type with fill width."""
        config = SectionConfig(width="fill", section_type=SectionTypeConfig.DRAWERS)
        assert config.width == "fill"
        assert config.section_type == SectionTypeConfig.DRAWERS


class TestCabinetConfigDefaultShelves:
    """Tests for CabinetConfig default_shelves field (FRD-04)."""

    def test_default_shelves_defaults_to_zero(self) -> None:
        """CabinetConfig default_shelves should default to 0."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0)
        assert config.default_shelves == 0

    def test_default_shelves_valid_value(self) -> None:
        """CabinetConfig should accept valid default_shelves."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0, default_shelves=4)
        assert config.default_shelves == 4

    def test_default_shelves_zero_valid(self) -> None:
        """CabinetConfig should accept default_shelves of 0."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0, default_shelves=0)
        assert config.default_shelves == 0

    def test_default_shelves_max_value(self) -> None:
        """CabinetConfig should accept default_shelves up to 20."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0, default_shelves=20)
        assert config.default_shelves == 20

    def test_default_shelves_negative_raises_error(self) -> None:
        """CabinetConfig should reject negative default_shelves."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfig(width=48.0, height=84.0, depth=12.0, default_shelves=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_default_shelves_above_max_raises_error(self) -> None:
        """CabinetConfig should reject default_shelves above 20."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CabinetConfig(width=48.0, height=84.0, depth=12.0, default_shelves=21)
        assert "less than or equal to 20" in str(exc_info.value)

    def test_default_shelves_with_sections(self) -> None:
        """CabinetConfig should maintain default_shelves with sections."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            default_shelves=5,
            sections=[SectionConfig(width=24.0), SectionConfig(width="fill")],
        )
        assert config.default_shelves == 5
        assert len(config.sections) == 2

    def test_default_shelves_sections_can_override(self) -> None:
        """Sections can have their own shelf counts independent of default_shelves."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            default_shelves=3,
            sections=[
                SectionConfig(width=24.0, shelves=0),  # Uses default
                SectionConfig(width="fill", shelves=5),  # Overrides
            ],
        )
        assert config.default_shelves == 3
        assert config.sections[0].shelves == 0
        assert config.sections[1].shelves == 5


class TestCabinetConfigurationFRD04:
    """Tests for full CabinetConfiguration with FRD-04 features."""

    def test_full_config_with_frd04_features(self) -> None:
        """CabinetConfiguration should accept all FRD-04 features together."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                default_shelves=3,
                sections=[
                    SectionConfig(
                        width=24.0,
                        shelves=0,
                        section_type=SectionTypeConfig.OPEN,
                        min_width=12.0,
                    ),
                    SectionConfig(
                        width="fill",
                        shelves=5,
                        section_type=SectionTypeConfig.DOORED,
                        depth=10.0,
                        min_width=18.0,
                        max_width=36.0,
                    ),
                    SectionConfig(
                        width=18.0,
                        shelves=0,
                        section_type=SectionTypeConfig.DRAWERS,
                    ),
                ],
            ),
        )
        assert config.cabinet.default_shelves == 3
        assert config.cabinet.sections[0].section_type == SectionTypeConfig.OPEN
        assert config.cabinet.sections[1].section_type == SectionTypeConfig.DOORED
        assert config.cabinet.sections[1].depth == 10.0
        assert config.cabinet.sections[2].section_type == SectionTypeConfig.DRAWERS

    def test_config_with_cubby_sections(self) -> None:
        """CabinetConfiguration should support cubby section type."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=48.0,
                depth=12.0,
                sections=[
                    SectionConfig(
                        width=12.0,
                        section_type=SectionTypeConfig.CUBBY,
                    ),
                    SectionConfig(
                        width=12.0,
                        section_type=SectionTypeConfig.CUBBY,
                    ),
                    SectionConfig(
                        width="fill",
                        section_type=SectionTypeConfig.CUBBY,
                    ),
                ],
            ),
        )
        for section in config.cabinet.sections:
            assert section.section_type == SectionTypeConfig.CUBBY


class TestCeilingSlopeConfig:
    """Tests for CeilingSlopeConfig model (FRD-11)."""

    def test_valid_ceiling_slope(self) -> None:
        """CeilingSlopeConfig should accept valid parameters."""
        config = CeilingSlopeConfig(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert config.angle == 30.0
        assert config.start_height == 96.0
        assert config.direction == "left_to_right"
        assert config.min_height == 24.0  # default

    def test_valid_with_min_height(self) -> None:
        """CeilingSlopeConfig should accept custom min_height."""
        config = CeilingSlopeConfig(
            angle=45.0,
            start_height=84.0,
            direction="right_to_left",
            min_height=18.0,
        )
        assert config.min_height == 18.0

    def test_all_directions(self) -> None:
        """CeilingSlopeConfig should accept all valid directions."""
        for direction in ["left_to_right", "right_to_left", "front_to_back"]:
            config = CeilingSlopeConfig(
                angle=20.0,
                start_height=96.0,
                direction=direction,  # type: ignore
            )
            assert config.direction == direction

    def test_angle_at_minimum(self) -> None:
        """CeilingSlopeConfig should accept angle=0."""
        config = CeilingSlopeConfig(
            angle=0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert config.angle == 0

    def test_angle_at_maximum(self) -> None:
        """CeilingSlopeConfig should accept angle=60."""
        config = CeilingSlopeConfig(
            angle=60.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert config.angle == 60.0

    def test_angle_negative_raises_error(self) -> None:
        """CeilingSlopeConfig should reject negative angle."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=-5.0,
                start_height=96.0,
                direction="left_to_right",
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_angle_above_max_raises_error(self) -> None:
        """CeilingSlopeConfig should reject angle above 60."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=65.0,
                start_height=96.0,
                direction="left_to_right",
            )
        assert "less than or equal to 60" in str(exc_info.value)

    def test_start_height_zero_raises_error(self) -> None:
        """CeilingSlopeConfig should reject start_height=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=30.0,
                start_height=0,
                direction="left_to_right",
            )
        assert "greater than 0" in str(exc_info.value)

    def test_start_height_negative_raises_error(self) -> None:
        """CeilingSlopeConfig should reject negative start_height."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=30.0,
                start_height=-10.0,
                direction="left_to_right",
            )
        assert "greater than 0" in str(exc_info.value)

    def test_min_height_zero_valid(self) -> None:
        """CeilingSlopeConfig should accept min_height=0."""
        config = CeilingSlopeConfig(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
            min_height=0,
        )
        assert config.min_height == 0

    def test_min_height_negative_raises_error(self) -> None:
        """CeilingSlopeConfig should reject negative min_height."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=30.0,
                start_height=96.0,
                direction="left_to_right",
                min_height=-5.0,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_invalid_direction_raises_error(self) -> None:
        """CeilingSlopeConfig should reject invalid direction."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=30.0,
                start_height=96.0,
                direction="invalid_direction",  # type: ignore
            )
        assert "direction" in str(exc_info.value).lower()

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingSlopeConfig(
                angle=30.0,
                start_height=96.0,
                direction="left_to_right",
                color="red",  # type: ignore
            )
        assert "color" in str(exc_info.value)


class TestSkylightConfig:
    """Tests for SkylightConfig model (FRD-11)."""

    def test_valid_skylight(self) -> None:
        """SkylightConfig should accept valid parameters."""
        config = SkylightConfig(
            x_position=24.0,
            width=36.0,
            projection_depth=12.0,
        )
        assert config.x_position == 24.0
        assert config.width == 36.0
        assert config.projection_depth == 12.0
        assert config.projection_angle == 90.0  # default

    def test_valid_with_projection_angle(self) -> None:
        """SkylightConfig should accept custom projection_angle."""
        config = SkylightConfig(
            x_position=24.0,
            width=36.0,
            projection_depth=12.0,
            projection_angle=75.0,
        )
        assert config.projection_angle == 75.0

    def test_x_position_zero_valid(self) -> None:
        """SkylightConfig should accept x_position=0."""
        config = SkylightConfig(
            x_position=0,
            width=36.0,
            projection_depth=12.0,
        )
        assert config.x_position == 0

    def test_x_position_negative_raises_error(self) -> None:
        """SkylightConfig should reject negative x_position."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=-5.0,
                width=36.0,
                projection_depth=12.0,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_width_zero_raises_error(self) -> None:
        """SkylightConfig should reject width=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=0,
                projection_depth=12.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_width_negative_raises_error(self) -> None:
        """SkylightConfig should reject negative width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=-10.0,
                projection_depth=12.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_projection_depth_zero_raises_error(self) -> None:
        """SkylightConfig should reject projection_depth=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=36.0,
                projection_depth=0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_projection_depth_negative_raises_error(self) -> None:
        """SkylightConfig should reject negative projection_depth."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=36.0,
                projection_depth=-5.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_projection_angle_at_max(self) -> None:
        """SkylightConfig should accept projection_angle=180."""
        config = SkylightConfig(
            x_position=24.0,
            width=36.0,
            projection_depth=12.0,
            projection_angle=180.0,
        )
        assert config.projection_angle == 180.0

    def test_projection_angle_zero_raises_error(self) -> None:
        """SkylightConfig should reject projection_angle=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=36.0,
                projection_depth=12.0,
                projection_angle=0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_projection_angle_above_max_raises_error(self) -> None:
        """SkylightConfig should reject projection_angle above 180."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=36.0,
                projection_depth=12.0,
                projection_angle=185.0,
            )
        assert "less than or equal to 180" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SkylightConfig(
                x_position=24.0,
                width=36.0,
                projection_depth=12.0,
                tint="dark",  # type: ignore
            )
        assert "tint" in str(exc_info.value)


class TestCeilingConfig:
    """Tests for CeilingConfig model (FRD-11)."""

    def test_empty_ceiling_config(self) -> None:
        """CeilingConfig should allow empty configuration."""
        config = CeilingConfig()
        assert config.slope is None
        assert config.skylights == []

    def test_with_slope_only(self) -> None:
        """CeilingConfig should accept slope without skylights."""
        slope = CeilingSlopeConfig(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
        )
        config = CeilingConfig(slope=slope)
        assert config.slope is not None
        assert config.slope.angle == 30.0
        assert config.skylights == []

    def test_with_skylights_only(self) -> None:
        """CeilingConfig should accept skylights without slope."""
        skylight1 = SkylightConfig(
            x_position=24.0,
            width=36.0,
            projection_depth=12.0,
        )
        skylight2 = SkylightConfig(
            x_position=84.0,
            width=24.0,
            projection_depth=8.0,
        )
        config = CeilingConfig(skylights=[skylight1, skylight2])
        assert config.slope is None
        assert len(config.skylights) == 2
        assert config.skylights[0].x_position == 24.0
        assert config.skylights[1].x_position == 84.0

    def test_with_slope_and_skylights(self) -> None:
        """CeilingConfig should accept both slope and skylights."""
        slope = CeilingSlopeConfig(
            angle=25.0,
            start_height=108.0,
            direction="front_to_back",
        )
        skylight = SkylightConfig(
            x_position=48.0,
            width=30.0,
            projection_depth=10.0,
        )
        config = CeilingConfig(slope=slope, skylights=[skylight])
        assert config.slope is not None
        assert config.slope.angle == 25.0
        assert len(config.skylights) == 1

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CeilingConfig(height=96.0)  # type: ignore
        assert "height" in str(exc_info.value)


class TestOutsideCornerConfigSchema:
    """Tests for OutsideCornerConfigSchema model (FRD-11)."""

    def test_default_values(self) -> None:
        """OutsideCornerConfigSchema should have sensible defaults."""
        config = OutsideCornerConfigSchema()
        assert config.treatment == "angled_face"
        assert config.filler_width == 3.0
        assert config.face_angle == 45.0

    def test_angled_face_treatment(self) -> None:
        """OutsideCornerConfigSchema should accept angled_face treatment."""
        config = OutsideCornerConfigSchema(treatment="angled_face", face_angle=30.0)
        assert config.treatment == "angled_face"
        assert config.face_angle == 30.0

    def test_butted_filler_treatment(self) -> None:
        """OutsideCornerConfigSchema should accept butted_filler treatment."""
        config = OutsideCornerConfigSchema(treatment="butted_filler", filler_width=4.0)
        assert config.treatment == "butted_filler"
        assert config.filler_width == 4.0

    def test_wrap_around_treatment(self) -> None:
        """OutsideCornerConfigSchema should accept wrap_around treatment."""
        config = OutsideCornerConfigSchema(treatment="wrap_around")
        assert config.treatment == "wrap_around"

    def test_invalid_treatment_raises_error(self) -> None:
        """OutsideCornerConfigSchema should reject invalid treatment."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(treatment="mitered")  # type: ignore
        assert "treatment" in str(exc_info.value).lower()

    def test_filler_width_zero_raises_error(self) -> None:
        """OutsideCornerConfigSchema should reject filler_width=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(filler_width=0)
        assert "greater than 0" in str(exc_info.value)

    def test_filler_width_negative_raises_error(self) -> None:
        """OutsideCornerConfigSchema should reject negative filler_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(filler_width=-2.0)
        assert "greater than 0" in str(exc_info.value)

    def test_face_angle_zero_raises_error(self) -> None:
        """OutsideCornerConfigSchema should reject face_angle=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(face_angle=0)
        assert "greater than 0" in str(exc_info.value)

    def test_face_angle_at_90_raises_error(self) -> None:
        """OutsideCornerConfigSchema should reject face_angle=90."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(face_angle=90.0)
        assert "less than 90" in str(exc_info.value)

    def test_face_angle_above_90_raises_error(self) -> None:
        """OutsideCornerConfigSchema should reject face_angle above 90."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(face_angle=95.0)
        assert "less than 90" in str(exc_info.value)

    def test_face_angle_near_limits(self) -> None:
        """OutsideCornerConfigSchema should accept face_angle near limits."""
        # Just above 0
        config1 = OutsideCornerConfigSchema(face_angle=0.1)
        assert config1.face_angle == 0.1
        # Just below 90
        config2 = OutsideCornerConfigSchema(face_angle=89.9)
        assert config2.face_angle == 89.9

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutsideCornerConfigSchema(material="wood")  # type: ignore
        assert "material" in str(exc_info.value)


class TestRoomConfigWithCeiling:
    """Tests for RoomConfig ceiling field (FRD-11)."""

    def test_ceiling_default_none(self) -> None:
        """RoomConfig ceiling should default to None."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        config = RoomConfig(name="test", walls=[wall])
        assert config.ceiling is None

    def test_room_with_ceiling_slope(self) -> None:
        """RoomConfig should accept ceiling with slope."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig(
            slope=CeilingSlopeConfig(
                angle=30.0,
                start_height=96.0,
                direction="left_to_right",
            )
        )
        config = RoomConfig(name="attic", walls=[wall], ceiling=ceiling)
        assert config.ceiling is not None
        assert config.ceiling.slope is not None
        assert config.ceiling.slope.angle == 30.0

    def test_room_with_skylights(self) -> None:
        """RoomConfig should accept ceiling with skylights."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig(
            skylights=[
                SkylightConfig(
                    x_position=48.0,
                    width=24.0,
                    projection_depth=8.0,
                )
            ]
        )
        config = RoomConfig(name="sunroom", walls=[wall], ceiling=ceiling)
        assert config.ceiling is not None
        assert len(config.ceiling.skylights) == 1


class TestRoomConfigWithOutsideCorner:
    """Tests for RoomConfig outside_corner field (FRD-11)."""

    def test_outside_corner_default_none(self) -> None:
        """RoomConfig outside_corner should default to None."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        config = RoomConfig(name="test", walls=[wall])
        assert config.outside_corner is None

    def test_room_with_outside_corner(self) -> None:
        """RoomConfig should accept outside_corner configuration."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=-90)
        outside_corner = OutsideCornerConfigSchema(
            treatment="butted_filler",
            filler_width=4.0,
        )
        config = RoomConfig(
            name="wraparound",
            walls=[wall1, wall2],
            outside_corner=outside_corner,
        )
        assert config.outside_corner is not None
        assert config.outside_corner.treatment == "butted_filler"
        assert config.outside_corner.filler_width == 4.0


class TestCabinetConfigurationWithFRD11:
    """Tests for full CabinetConfiguration with FRD-11 features."""

    def test_full_config_with_ceiling_and_corner(self) -> None:
        """CabinetConfiguration should accept all FRD-11 features."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0, name="north")
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=-90, name="west")
        ceiling = CeilingConfig(
            slope=CeilingSlopeConfig(
                angle=25.0,
                start_height=96.0,
                direction="front_to_back",
                min_height=30.0,
            ),
            skylights=[
                SkylightConfig(
                    x_position=48.0,
                    width=24.0,
                    projection_depth=10.0,
                    projection_angle=85.0,
                )
            ],
        )
        outside_corner = OutsideCornerConfigSchema(
            treatment="angled_face",
            face_angle=45.0,
        )
        room = RoomConfig(
            name="attic_nook",
            walls=[wall1, wall2],
            ceiling=ceiling,
            outside_corner=outside_corner,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        assert config.room is not None
        assert config.room.ceiling is not None
        assert config.room.ceiling.slope is not None
        assert config.room.ceiling.slope.angle == 25.0
        assert len(config.room.ceiling.skylights) == 1
        assert config.room.outside_corner is not None
        assert config.room.outside_corner.treatment == "angled_face"

    def test_backward_compatibility_without_frd11_features(self) -> None:
        """v1.0 configs without FRD-11 features should still work."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.room is None

    def test_v1_1_config_without_frd11_features(self) -> None:
        """v1.1 configs can omit FRD-11 features."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="simple_room", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        assert config.room is not None
        assert config.room.ceiling is None
        assert config.room.outside_corner is None


# =============================================================================
# FRD-12: Decorative Element Configuration Tests
# =============================================================================

from cabinets.application.config import (
    ArchTopConfigSchema,
    ArchTypeConfig,
    BaseZoneConfigSchema,
    CrownMoldingConfigSchema,
    EdgeProfileConfigSchema,
    EdgeProfileTypeConfig,
    FaceFrameConfigSchema,
    HardwareConfigSchema,
    JoineryConfigSchema,
    JoineryTypeConfig,
    LightRailConfigSchema,
    ScallopConfigSchema,
    SpanLimitsConfigSchema,
    WoodworkingConfigSchema,
)


class TestArchTypeConfig:
    """Tests for ArchTypeConfig enum (FRD-12)."""

    def test_arch_type_values(self) -> None:
        """ArchTypeConfig should have all expected values."""
        assert ArchTypeConfig.FULL_ROUND.value == "full_round"
        assert ArchTypeConfig.SEGMENTAL.value == "segmental"
        assert ArchTypeConfig.ELLIPTICAL.value == "elliptical"

    def test_arch_type_count(self) -> None:
        """ArchTypeConfig should have exactly 3 values."""
        assert len(ArchTypeConfig) == 3

    def test_arch_type_from_value(self) -> None:
        """ArchTypeConfig should be creatable from string values."""
        assert ArchTypeConfig("full_round") == ArchTypeConfig.FULL_ROUND
        assert ArchTypeConfig("segmental") == ArchTypeConfig.SEGMENTAL
        assert ArchTypeConfig("elliptical") == ArchTypeConfig.ELLIPTICAL


class TestJoineryTypeConfig:
    """Tests for JoineryTypeConfig enum (FRD-12, FRD-14)."""

    def test_joinery_type_values(self) -> None:
        """JoineryTypeConfig should have all expected values."""
        assert JoineryTypeConfig.DADO.value == "dado"
        assert JoineryTypeConfig.RABBET.value == "rabbet"
        assert JoineryTypeConfig.POCKET_SCREW.value == "pocket_screw"
        assert JoineryTypeConfig.MORTISE_TENON.value == "mortise_tenon"
        assert JoineryTypeConfig.DOWEL.value == "dowel"
        assert JoineryTypeConfig.BISCUIT.value == "biscuit"
        assert JoineryTypeConfig.BUTT.value == "butt"

    def test_joinery_type_count(self) -> None:
        """JoineryTypeConfig should have exactly 7 values (FRD-14 extended)."""
        assert len(JoineryTypeConfig) == 7


class TestEdgeProfileTypeConfig:
    """Tests for EdgeProfileTypeConfig enum (FRD-12)."""

    def test_edge_profile_type_values(self) -> None:
        """EdgeProfileTypeConfig should have all expected values."""
        assert EdgeProfileTypeConfig.CHAMFER.value == "chamfer"
        assert EdgeProfileTypeConfig.ROUNDOVER.value == "roundover"
        assert EdgeProfileTypeConfig.OGEE.value == "ogee"
        assert EdgeProfileTypeConfig.BEVEL.value == "bevel"
        assert EdgeProfileTypeConfig.COVE.value == "cove"
        assert EdgeProfileTypeConfig.ROMAN_OGEE.value == "roman_ogee"

    def test_edge_profile_type_count(self) -> None:
        """EdgeProfileTypeConfig should have exactly 6 values."""
        assert len(EdgeProfileTypeConfig) == 6


class TestFaceFrameConfigSchema:
    """Tests for FaceFrameConfigSchema model (FRD-12)."""

    def test_defaults(self) -> None:
        """FaceFrameConfigSchema should have sensible defaults."""
        config = FaceFrameConfigSchema()
        assert config.stile_width == 1.5
        assert config.rail_width == 1.5
        assert config.joinery == JoineryTypeConfig.POCKET_SCREW
        assert config.material_thickness == 0.75

    def test_custom_values(self) -> None:
        """FaceFrameConfigSchema should accept custom values."""
        config = FaceFrameConfigSchema(
            stile_width=2.0,
            rail_width=2.5,
            joinery=JoineryTypeConfig.MORTISE_TENON,
            material_thickness=1.0,
        )
        assert config.stile_width == 2.0
        assert config.rail_width == 2.5
        assert config.joinery == JoineryTypeConfig.MORTISE_TENON
        assert config.material_thickness == 1.0

    def test_joinery_from_string(self) -> None:
        """FaceFrameConfigSchema should accept joinery as string."""
        config = FaceFrameConfigSchema(joinery="dowel")  # type: ignore
        assert config.joinery == JoineryTypeConfig.DOWEL

    def test_stile_width_zero_raises_error(self) -> None:
        """FaceFrameConfigSchema should reject stile_width=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(stile_width=0)
        assert "greater than 0" in str(exc_info.value)

    def test_stile_width_negative_raises_error(self) -> None:
        """FaceFrameConfigSchema should reject negative stile_width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(stile_width=-1.0)
        assert "greater than 0" in str(exc_info.value)

    def test_stile_width_above_max_raises_error(self) -> None:
        """FaceFrameConfigSchema should reject stile_width above 6.0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(stile_width=7.0)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_rail_width_zero_raises_error(self) -> None:
        """FaceFrameConfigSchema should reject rail_width=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(rail_width=0)
        assert "greater than 0" in str(exc_info.value)

    def test_material_thickness_below_min_raises_error(self) -> None:
        """FaceFrameConfigSchema should reject material_thickness below 0.5."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(material_thickness=0.25)
        assert "greater than or equal to 0.5" in str(exc_info.value)

    def test_material_thickness_above_max_raises_error(self) -> None:
        """FaceFrameConfigSchema should reject material_thickness above 1.5."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(material_thickness=2.0)
        assert "less than or equal to 1.5" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """FaceFrameConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FaceFrameConfigSchema(color="red")  # type: ignore
        assert "color" in str(exc_info.value)


class TestCrownMoldingConfigSchema:
    """Tests for CrownMoldingConfigSchema model (FRD-12)."""

    def test_defaults(self) -> None:
        """CrownMoldingConfigSchema should have sensible defaults."""
        config = CrownMoldingConfigSchema()
        assert config.height == 3.0
        assert config.setback == 0.75
        assert config.nailer_width == 2.0

    def test_custom_values(self) -> None:
        """CrownMoldingConfigSchema should accept custom values."""
        config = CrownMoldingConfigSchema(
            height=4.0,
            setback=1.0,
            nailer_width=2.5,
        )
        assert config.height == 4.0
        assert config.setback == 1.0
        assert config.nailer_width == 2.5

    def test_height_zero_raises_error(self) -> None:
        """CrownMoldingConfigSchema should reject height=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CrownMoldingConfigSchema(height=0)
        assert "greater than 0" in str(exc_info.value)

    def test_height_above_max_raises_error(self) -> None:
        """CrownMoldingConfigSchema should reject height above 12."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CrownMoldingConfigSchema(height=15.0)
        assert "less than or equal to 12" in str(exc_info.value)

    def test_setback_zero_raises_error(self) -> None:
        """CrownMoldingConfigSchema should reject setback=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CrownMoldingConfigSchema(setback=0)
        assert "greater than 0" in str(exc_info.value)

    def test_setback_above_max_raises_error(self) -> None:
        """CrownMoldingConfigSchema should reject setback above 3."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CrownMoldingConfigSchema(setback=4.0)
        assert "less than or equal to 3" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """CrownMoldingConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CrownMoldingConfigSchema(profile="ogee")  # type: ignore
        assert "profile" in str(exc_info.value)


class TestBaseZoneConfigSchema:
    """Tests for BaseZoneConfigSchema model (FRD-12)."""

    def test_defaults(self) -> None:
        """BaseZoneConfigSchema should have sensible defaults."""
        config = BaseZoneConfigSchema()
        assert config.height == 3.5
        assert config.setback == 3.0
        assert config.zone_type == "toe_kick"

    def test_custom_values(self) -> None:
        """BaseZoneConfigSchema should accept custom values."""
        config = BaseZoneConfigSchema(
            height=4.0,
            setback=4.0,
            zone_type="base_molding",
        )
        assert config.height == 4.0
        assert config.setback == 4.0
        assert config.zone_type == "base_molding"

    def test_height_below_min_raises_error(self) -> None:
        """BaseZoneConfigSchema should reject height below 3."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BaseZoneConfigSchema(height=2.0)
        assert "greater than or equal to 3" in str(exc_info.value)

    def test_height_above_max_raises_error(self) -> None:
        """BaseZoneConfigSchema should reject height above 6."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BaseZoneConfigSchema(height=7.0)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_setback_zero_valid(self) -> None:
        """BaseZoneConfigSchema should accept setback=0 for flush base."""
        config = BaseZoneConfigSchema(setback=0)
        assert config.setback == 0

    def test_setback_above_max_raises_error(self) -> None:
        """BaseZoneConfigSchema should reject setback above 6."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BaseZoneConfigSchema(setback=7.0)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_invalid_zone_type_raises_error(self) -> None:
        """BaseZoneConfigSchema should reject invalid zone_type."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BaseZoneConfigSchema(zone_type="invalid")  # type: ignore
        assert "zone_type" in str(exc_info.value).lower()

    def test_rejects_unknown_fields(self) -> None:
        """BaseZoneConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BaseZoneConfigSchema(color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestLightRailConfigSchema:
    """Tests for LightRailConfigSchema model (FRD-12)."""

    def test_defaults(self) -> None:
        """LightRailConfigSchema should have sensible defaults."""
        config = LightRailConfigSchema()
        assert config.height == 1.5
        assert config.setback == 0.25
        assert config.generate_strip is True

    def test_custom_values(self) -> None:
        """LightRailConfigSchema should accept custom values."""
        config = LightRailConfigSchema(
            height=2.0,
            setback=0.5,
            generate_strip=False,
        )
        assert config.height == 2.0
        assert config.setback == 0.5
        assert config.generate_strip is False

    def test_height_zero_raises_error(self) -> None:
        """LightRailConfigSchema should reject height=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LightRailConfigSchema(height=0)
        assert "greater than 0" in str(exc_info.value)

    def test_height_above_max_raises_error(self) -> None:
        """LightRailConfigSchema should reject height above 4."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LightRailConfigSchema(height=5.0)
        assert "less than or equal to 4" in str(exc_info.value)

    def test_setback_zero_valid(self) -> None:
        """LightRailConfigSchema should accept setback=0."""
        config = LightRailConfigSchema(setback=0)
        assert config.setback == 0

    def test_setback_above_max_raises_error(self) -> None:
        """LightRailConfigSchema should reject setback above 2."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LightRailConfigSchema(setback=3.0)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """LightRailConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            LightRailConfigSchema(led_type="strip")  # type: ignore
        assert "led_type" in str(exc_info.value)


class TestArchTopConfigSchema:
    """Tests for ArchTopConfigSchema model (FRD-12)."""

    def test_defaults(self) -> None:
        """ArchTopConfigSchema should have sensible defaults."""
        config = ArchTopConfigSchema()
        assert config.arch_type == ArchTypeConfig.FULL_ROUND
        assert config.radius == "auto"
        assert config.spring_height == 0.0

    def test_custom_values(self) -> None:
        """ArchTopConfigSchema should accept custom values."""
        config = ArchTopConfigSchema(
            arch_type=ArchTypeConfig.SEGMENTAL,
            radius=12.0,
            spring_height=6.0,
        )
        assert config.arch_type == ArchTypeConfig.SEGMENTAL
        assert config.radius == 12.0
        assert config.spring_height == 6.0

    def test_arch_type_from_string(self) -> None:
        """ArchTopConfigSchema should accept arch_type as string."""
        config = ArchTopConfigSchema(arch_type="elliptical")  # type: ignore
        assert config.arch_type == ArchTypeConfig.ELLIPTICAL

    def test_radius_auto_literal(self) -> None:
        """ArchTopConfigSchema should accept radius='auto'."""
        config = ArchTopConfigSchema(radius="auto")
        assert config.radius == "auto"

    def test_radius_positive_float(self) -> None:
        """ArchTopConfigSchema should accept positive radius."""
        config = ArchTopConfigSchema(radius=15.0)
        assert config.radius == 15.0

    def test_radius_zero_raises_error(self) -> None:
        """ArchTopConfigSchema should reject radius=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ArchTopConfigSchema(radius=0)
        assert "radius must be positive" in str(exc_info.value)

    def test_radius_negative_raises_error(self) -> None:
        """ArchTopConfigSchema should reject negative radius."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ArchTopConfigSchema(radius=-5.0)
        assert "radius must be positive" in str(exc_info.value)

    def test_spring_height_zero_valid(self) -> None:
        """ArchTopConfigSchema should accept spring_height=0."""
        config = ArchTopConfigSchema(spring_height=0)
        assert config.spring_height == 0

    def test_spring_height_negative_raises_error(self) -> None:
        """ArchTopConfigSchema should reject negative spring_height."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ArchTopConfigSchema(spring_height=-2.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """ArchTopConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ArchTopConfigSchema(curve_type="bezier")  # type: ignore
        assert "curve_type" in str(exc_info.value)


class TestEdgeProfileConfigSchema:
    """Tests for EdgeProfileConfigSchema model (FRD-12)."""

    def test_required_fields(self) -> None:
        """EdgeProfileConfigSchema requires profile_type and size."""
        config = EdgeProfileConfigSchema(
            profile_type=EdgeProfileTypeConfig.ROUNDOVER,
            size=0.25,
        )
        assert config.profile_type == EdgeProfileTypeConfig.ROUNDOVER
        assert config.size == 0.25
        assert config.edges == "auto"

    def test_profile_type_from_string(self) -> None:
        """EdgeProfileConfigSchema should accept profile_type as string."""
        config = EdgeProfileConfigSchema(profile_type="chamfer", size=0.25)  # type: ignore
        assert config.profile_type == EdgeProfileTypeConfig.CHAMFER

    def test_all_profile_types(self) -> None:
        """EdgeProfileConfigSchema should accept all profile types."""
        for profile_type in EdgeProfileTypeConfig:
            config = EdgeProfileConfigSchema(profile_type=profile_type, size=0.25)
            assert config.profile_type == profile_type

    def test_edges_auto_default(self) -> None:
        """EdgeProfileConfigSchema edges should default to 'auto'."""
        config = EdgeProfileConfigSchema(
            profile_type=EdgeProfileTypeConfig.OGEE,
            size=0.375,
        )
        assert config.edges == "auto"

    def test_edges_explicit_list(self) -> None:
        """EdgeProfileConfigSchema should accept explicit edge list."""
        config = EdgeProfileConfigSchema(
            profile_type=EdgeProfileTypeConfig.ROUNDOVER,
            size=0.25,
            edges=["top", "front"],
        )
        assert config.edges == ["top", "front"]

    def test_edges_all_valid_values(self) -> None:
        """EdgeProfileConfigSchema should accept all valid edge values."""
        config = EdgeProfileConfigSchema(
            profile_type=EdgeProfileTypeConfig.BEVEL,
            size=0.5,
            edges=["top", "bottom", "left", "right", "front"],
        )
        assert len(config.edges) == 5

    def test_size_zero_raises_error(self) -> None:
        """EdgeProfileConfigSchema should reject size=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EdgeProfileConfigSchema(
                profile_type=EdgeProfileTypeConfig.ROUNDOVER,
                size=0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_size_negative_raises_error(self) -> None:
        """EdgeProfileConfigSchema should reject negative size."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EdgeProfileConfigSchema(
                profile_type=EdgeProfileTypeConfig.ROUNDOVER,
                size=-0.25,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_size_above_max_raises_error(self) -> None:
        """EdgeProfileConfigSchema should reject size above 1.0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EdgeProfileConfigSchema(
                profile_type=EdgeProfileTypeConfig.ROUNDOVER,
                size=1.5,
            )
        assert "less than or equal to 1" in str(exc_info.value)

    def test_missing_profile_type_raises_error(self) -> None:
        """EdgeProfileConfigSchema should require profile_type."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EdgeProfileConfigSchema(size=0.25)  # type: ignore
        assert "profile_type" in str(exc_info.value)

    def test_missing_size_raises_error(self) -> None:
        """EdgeProfileConfigSchema should require size."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EdgeProfileConfigSchema(profile_type=EdgeProfileTypeConfig.ROUNDOVER)  # type: ignore
        assert "size" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """EdgeProfileConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EdgeProfileConfigSchema(
                profile_type=EdgeProfileTypeConfig.ROUNDOVER,
                size=0.25,
                depth=0.5,  # type: ignore
            )
        assert "depth" in str(exc_info.value)


class TestScallopConfigSchema:
    """Tests for ScallopConfigSchema model (FRD-12)."""

    def test_required_fields(self) -> None:
        """ScallopConfigSchema requires depth and width."""
        config = ScallopConfigSchema(depth=1.5, width=4.0)
        assert config.depth == 1.5
        assert config.width == 4.0
        assert config.count == "auto"

    def test_count_auto_default(self) -> None:
        """ScallopConfigSchema count should default to 'auto'."""
        config = ScallopConfigSchema(depth=1.0, width=3.0)
        assert config.count == "auto"

    def test_count_explicit_integer(self) -> None:
        """ScallopConfigSchema should accept explicit count."""
        config = ScallopConfigSchema(depth=1.5, width=4.0, count=6)
        assert config.count == 6

    def test_depth_zero_raises_error(self) -> None:
        """ScallopConfigSchema should reject depth=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=0, width=4.0)
        assert "greater than 0" in str(exc_info.value)

    def test_depth_negative_raises_error(self) -> None:
        """ScallopConfigSchema should reject negative depth."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=-1.0, width=4.0)
        assert "greater than 0" in str(exc_info.value)

    def test_depth_above_max_raises_error(self) -> None:
        """ScallopConfigSchema should reject depth above 3.0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=4.0, width=4.0)
        assert "less than or equal to 3" in str(exc_info.value)

    def test_width_zero_raises_error(self) -> None:
        """ScallopConfigSchema should reject width=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=1.0, width=0)
        assert "greater than 0" in str(exc_info.value)

    def test_width_negative_raises_error(self) -> None:
        """ScallopConfigSchema should reject negative width."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=1.0, width=-2.0)
        assert "greater than 0" in str(exc_info.value)

    def test_count_zero_raises_error(self) -> None:
        """ScallopConfigSchema should reject count=0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=1.0, width=4.0, count=0)
        assert "count must be at least 1" in str(exc_info.value)

    def test_count_negative_raises_error(self) -> None:
        """ScallopConfigSchema should reject negative count."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=1.0, width=4.0, count=-5)
        assert "count must be at least 1" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """ScallopConfigSchema should reject unknown fields."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ScallopConfigSchema(depth=1.0, width=4.0, pattern="wave")  # type: ignore
        assert "pattern" in str(exc_info.value)


class TestCabinetConfigDecorativeFields:
    """Tests for CabinetConfig decorative fields (FRD-12)."""

    def test_decorative_fields_default_none(self) -> None:
        """CabinetConfig decorative fields should default to None."""
        config = CabinetConfig(width=48.0, height=84.0, depth=12.0)
        assert config.face_frame is None
        assert config.crown_molding is None
        assert config.base_zone is None
        assert config.light_rail is None

    def test_face_frame_config(self) -> None:
        """CabinetConfig should accept face_frame configuration."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            face_frame=FaceFrameConfigSchema(stile_width=1.5, rail_width=2.0),
        )
        assert config.face_frame is not None
        assert config.face_frame.stile_width == 1.5
        assert config.face_frame.rail_width == 2.0

    def test_crown_molding_config(self) -> None:
        """CabinetConfig should accept crown_molding configuration."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            crown_molding=CrownMoldingConfigSchema(height=4.0, setback=1.0),
        )
        assert config.crown_molding is not None
        assert config.crown_molding.height == 4.0
        assert config.crown_molding.setback == 1.0

    def test_base_zone_config(self) -> None:
        """CabinetConfig should accept base_zone configuration."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            base_zone=BaseZoneConfigSchema(height=4.0, zone_type="toe_kick"),
        )
        assert config.base_zone is not None
        assert config.base_zone.height == 4.0
        assert config.base_zone.zone_type == "toe_kick"

    def test_light_rail_config(self) -> None:
        """CabinetConfig should accept light_rail configuration."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            light_rail=LightRailConfigSchema(height=2.0, generate_strip=True),
        )
        assert config.light_rail is not None
        assert config.light_rail.height == 2.0
        assert config.light_rail.generate_strip is True

    def test_all_decorative_fields(self) -> None:
        """CabinetConfig should accept all decorative fields together."""
        config = CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            face_frame=FaceFrameConfigSchema(),
            crown_molding=CrownMoldingConfigSchema(),
            base_zone=BaseZoneConfigSchema(),
            light_rail=LightRailConfigSchema(),
        )
        assert config.face_frame is not None
        assert config.crown_molding is not None
        assert config.base_zone is not None
        assert config.light_rail is not None


class TestSectionConfigDecorativeFields:
    """Tests for SectionConfig decorative fields (FRD-12)."""

    def test_decorative_fields_default_none(self) -> None:
        """SectionConfig decorative fields should default to None."""
        config = SectionConfig()
        assert config.arch_top is None
        assert config.edge_profile is None
        assert config.scallop is None

    def test_arch_top_config(self) -> None:
        """SectionConfig should accept arch_top configuration."""
        config = SectionConfig(
            width=24.0,
            arch_top=ArchTopConfigSchema(arch_type=ArchTypeConfig.FULL_ROUND),
        )
        assert config.arch_top is not None
        assert config.arch_top.arch_type == ArchTypeConfig.FULL_ROUND

    def test_edge_profile_config(self) -> None:
        """SectionConfig should accept edge_profile configuration."""
        config = SectionConfig(
            width=24.0,
            edge_profile=EdgeProfileConfigSchema(
                profile_type=EdgeProfileTypeConfig.ROUNDOVER,
                size=0.25,
            ),
        )
        assert config.edge_profile is not None
        assert config.edge_profile.profile_type == EdgeProfileTypeConfig.ROUNDOVER
        assert config.edge_profile.size == 0.25

    def test_scallop_config(self) -> None:
        """SectionConfig should accept scallop configuration."""
        config = SectionConfig(
            width=24.0,
            scallop=ScallopConfigSchema(depth=1.5, width=4.0),
        )
        assert config.scallop is not None
        assert config.scallop.depth == 1.5
        assert config.scallop.width == 4.0

    def test_all_decorative_fields(self) -> None:
        """SectionConfig should accept all decorative fields together."""
        config = SectionConfig(
            width=24.0,
            arch_top=ArchTopConfigSchema(),
            edge_profile=EdgeProfileConfigSchema(
                profile_type=EdgeProfileTypeConfig.OGEE,
                size=0.375,
            ),
            scallop=ScallopConfigSchema(depth=1.0, width=3.0),
        )
        assert config.arch_top is not None
        assert config.edge_profile is not None
        assert config.scallop is not None


class TestCabinetConfigurationWithFRD12:
    """Tests for full CabinetConfiguration with FRD-12 features."""

    def test_v1_3_schema_version_valid(self) -> None:
        """v1.3 schema version should be accepted."""
        config = CabinetConfiguration(
            schema_version="1.3",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.3"

    def test_full_config_with_decorative_elements(self) -> None:
        """CabinetConfiguration should accept all FRD-12 features."""
        config = CabinetConfiguration(
            schema_version="1.3",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                face_frame=FaceFrameConfigSchema(
                    stile_width=1.5,
                    rail_width=2.0,
                    joinery=JoineryTypeConfig.MORTISE_TENON,
                ),
                crown_molding=CrownMoldingConfigSchema(
                    height=4.0,
                    setback=1.0,
                    nailer_width=2.5,
                ),
                base_zone=BaseZoneConfigSchema(
                    height=4.0,
                    setback=3.0,
                    zone_type="toe_kick",
                ),
                sections=[
                    SectionConfig(
                        width=24.0,
                        shelves=3,
                        edge_profile=EdgeProfileConfigSchema(
                            profile_type=EdgeProfileTypeConfig.ROUNDOVER,
                            size=0.25,
                            edges=["front"],
                        ),
                    ),
                    SectionConfig(
                        width="fill",
                        arch_top=ArchTopConfigSchema(
                            arch_type=ArchTypeConfig.SEGMENTAL,
                            radius=12.0,
                            spring_height=6.0,
                        ),
                    ),
                ],
            ),
        )
        assert config.cabinet.face_frame is not None
        assert config.cabinet.crown_molding is not None
        assert config.cabinet.base_zone is not None
        assert config.cabinet.sections[0].edge_profile is not None
        assert config.cabinet.sections[1].arch_top is not None

    def test_backward_compatibility_without_frd12_features(self) -> None:
        """Configs without FRD-12 features should still work."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.cabinet.face_frame is None
        assert config.cabinet.crown_molding is None
        assert config.cabinet.base_zone is None
        assert config.cabinet.light_rail is None

    def test_v1_2_config_can_add_frd12_features(self) -> None:
        """v1.2 configs can optionally include FRD-12 features."""
        config = CabinetConfiguration(
            schema_version="1.2",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                face_frame=FaceFrameConfigSchema(),
            ),
        )
        assert config.cabinet.face_frame is not None


# =============================================================================
# Bin Packing Configuration Tests (FRD-13)
# =============================================================================


class TestSheetSizeConfigSchema:
    """Tests for SheetSizeConfigSchema model."""

    def test_defaults(self) -> None:
        """SheetSizeConfigSchema should have sensible defaults."""
        config = SheetSizeConfigSchema()
        assert config.width == 48.0
        assert config.height == 96.0

    def test_custom_values(self) -> None:
        """SheetSizeConfigSchema should accept custom values."""
        config = SheetSizeConfigSchema(width=60.0, height=60.0)
        assert config.width == 60.0
        assert config.height == 60.0

    def test_width_must_be_positive(self) -> None:
        """Width must be greater than 0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(width=0)
        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(width=-10.0)
        assert "greater than 0" in str(exc_info.value)

    def test_height_must_be_positive(self) -> None:
        """Height must be greater than 0."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(height=0)
        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(height=-10.0)
        assert "greater than 0" in str(exc_info.value)

    def test_width_max_constraint(self) -> None:
        """Width must be at most 120 inches."""
        # Valid at boundary
        config = SheetSizeConfigSchema(width=120.0)
        assert config.width == 120.0

        # Exceeds maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(width=121.0)
        assert "less than or equal to 120" in str(exc_info.value)

    def test_height_max_constraint(self) -> None:
        """Height must be at most 120 inches."""
        # Valid at boundary
        config = SheetSizeConfigSchema(height=120.0)
        assert config.height == 120.0

        # Exceeds maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(height=121.0)
        assert "less than or equal to 120" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            SheetSizeConfigSchema(width=48.0, thickness=0.75)  # type: ignore
        assert "thickness" in str(exc_info.value)


class TestBinPackingConfigSchema:
    """Tests for BinPackingConfigSchema model."""

    def test_defaults(self) -> None:
        """BinPackingConfigSchema should have sensible defaults."""
        config = BinPackingConfigSchema()
        assert config.enabled is True
        assert config.sheet_size.width == 48.0
        assert config.sheet_size.height == 96.0
        assert config.kerf == 0.125
        assert config.edge_allowance == 0.5
        assert config.min_offcut_size == 6.0

    def test_custom_values(self) -> None:
        """BinPackingConfigSchema should accept custom values."""
        config = BinPackingConfigSchema(
            enabled=False,
            sheet_size=SheetSizeConfigSchema(width=60.0, height=60.0),
            kerf=0.1875,
            edge_allowance=0.75,
            min_offcut_size=12.0,
        )
        assert config.enabled is False
        assert config.sheet_size.width == 60.0
        assert config.sheet_size.height == 60.0
        assert config.kerf == 0.1875
        assert config.edge_allowance == 0.75
        assert config.min_offcut_size == 12.0

    def test_kerf_constraints(self) -> None:
        """Kerf should be constrained between 0 and 0.5."""
        # Valid at boundaries
        config = BinPackingConfigSchema(kerf=0.0)
        assert config.kerf == 0.0

        config = BinPackingConfigSchema(kerf=0.5)
        assert config.kerf == 0.5

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            BinPackingConfigSchema(kerf=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            BinPackingConfigSchema(kerf=0.6)
        assert "less than or equal to 0.5" in str(exc_info.value)

    def test_edge_allowance_constraints(self) -> None:
        """Edge allowance should be constrained between 0 and 2.0."""
        # Valid at boundaries
        config = BinPackingConfigSchema(edge_allowance=0.0)
        assert config.edge_allowance == 0.0

        config = BinPackingConfigSchema(edge_allowance=2.0)
        assert config.edge_allowance == 2.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            BinPackingConfigSchema(edge_allowance=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            BinPackingConfigSchema(edge_allowance=2.5)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_min_offcut_size_constraints(self) -> None:
        """Min offcut size should be non-negative."""
        # Valid at boundary
        config = BinPackingConfigSchema(min_offcut_size=0.0)
        assert config.min_offcut_size == 0.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            BinPackingConfigSchema(min_offcut_size=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BinPackingConfigSchema(enabled=True, algorithm="best_fit")  # type: ignore
        assert "algorithm" in str(exc_info.value)


class TestCabinetConfigurationBinPacking:
    """Tests for bin_packing field in CabinetConfiguration."""

    def test_bin_packing_defaults_to_none(self) -> None:
        """bin_packing should default to None when not specified."""
        config = CabinetConfiguration(
            schema_version="1.4",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.bin_packing is None

    def test_bin_packing_with_defaults(self) -> None:
        """bin_packing can be specified with all defaults."""
        config = CabinetConfiguration(
            schema_version="1.4",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            bin_packing=BinPackingConfigSchema(),
        )
        assert config.bin_packing is not None
        assert config.bin_packing.enabled is True
        assert config.bin_packing.kerf == 0.125

    def test_bin_packing_with_custom_values(self) -> None:
        """bin_packing can be specified with custom values."""
        config = CabinetConfiguration(
            schema_version="1.4",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            bin_packing=BinPackingConfigSchema(
                enabled=True,
                sheet_size=SheetSizeConfigSchema(width=48.0, height=96.0),
                kerf=0.125,
                edge_allowance=0.5,
            ),
        )
        assert config.bin_packing is not None
        assert config.bin_packing.enabled is True
        assert config.bin_packing.sheet_size.width == 48.0
        assert config.bin_packing.sheet_size.height == 96.0
        assert config.bin_packing.kerf == 0.125

    def test_v1_4_in_supported_versions(self) -> None:
        """Schema version 1.4 should be in supported versions."""
        assert "1.4" in SUPPORTED_VERSIONS

    def test_schema_version_1_4_accepted(self) -> None:
        """Schema version 1.4 should be accepted."""
        config = CabinetConfiguration(
            schema_version="1.4",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.4"

    def test_backward_compatibility_without_bin_packing(self) -> None:
        """Old configs without bin_packing should still work."""
        # v1.0 config without bin_packing
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.bin_packing is None

        # v1.1 config without bin_packing
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.bin_packing is None

    def test_bin_packing_disabled(self) -> None:
        """bin_packing can be explicitly disabled."""
        config = CabinetConfiguration(
            schema_version="1.4",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            bin_packing=BinPackingConfigSchema(enabled=False),
        )
        assert config.bin_packing is not None
        assert config.bin_packing.enabled is False


class TestConfigToBinPackingAdapter:
    """Tests for config_to_bin_packing adapter function."""

    def test_none_input_returns_default_config(self) -> None:
        """config_to_bin_packing should return default config when input is None."""
        from cabinets.infrastructure.bin_packing import BinPackingConfig

        result = config_to_bin_packing(None)
        assert isinstance(result, BinPackingConfig)
        assert result.enabled is True
        assert result.sheet_size.width == 48.0
        assert result.sheet_size.height == 96.0
        assert result.kerf == 0.125
        assert result.min_offcut_size == 6.0

    def test_converts_pydantic_to_domain(self) -> None:
        """config_to_bin_packing should convert Pydantic model to domain dataclass."""
        from cabinets.infrastructure.bin_packing import BinPackingConfig, SheetConfig

        pydantic_config = BinPackingConfigSchema(
            enabled=False,
            sheet_size=SheetSizeConfigSchema(width=60.0, height=60.0),
            kerf=0.1875,
            edge_allowance=1.0,
            min_offcut_size=12.0,
        )

        result = config_to_bin_packing(pydantic_config)

        assert isinstance(result, BinPackingConfig)
        assert result.enabled is False
        assert isinstance(result.sheet_size, SheetConfig)
        assert result.sheet_size.width == 60.0
        assert result.sheet_size.height == 60.0
        assert result.sheet_size.edge_allowance == 1.0
        assert result.kerf == 0.1875
        assert result.min_offcut_size == 12.0

    def test_edge_allowance_passed_to_sheet_config(self) -> None:
        """edge_allowance from BinPackingConfigSchema should be passed to SheetConfig."""
        pydantic_config = BinPackingConfigSchema(
            edge_allowance=0.75,
        )

        result = config_to_bin_packing(pydantic_config)

        # edge_allowance is stored in SheetConfig, not BinPackingConfig
        assert result.sheet_size.edge_allowance == 0.75

    def test_usable_dimensions_account_for_edge_allowance(self) -> None:
        """Usable dimensions should account for edge allowance."""
        pydantic_config = BinPackingConfigSchema(
            sheet_size=SheetSizeConfigSchema(width=48.0, height=96.0),
            edge_allowance=0.5,
        )

        result = config_to_bin_packing(pydantic_config)

        # Usable dimensions = dimensions - (2 * edge_allowance)
        assert result.sheet_size.usable_width == 47.0  # 48 - 2*0.5
        assert result.sheet_size.usable_height == 95.0  # 96 - 2*0.5


# =============================================================================
# Woodworking Intelligence Configuration Tests (FRD-14)
# =============================================================================


class TestJoineryConfigSchema:
    """Tests for JoineryConfigSchema (FRD-14)."""

    def test_defaults(self) -> None:
        """JoineryConfigSchema should have sensible defaults."""
        config = JoineryConfigSchema()
        assert config.default_shelf_joint == JoineryTypeConfig.DADO
        assert config.default_back_joint == JoineryTypeConfig.RABBET
        assert config.dado_depth_ratio == pytest.approx(0.333, rel=0.01)
        assert config.rabbet_depth_ratio == 0.5
        assert config.dowel_edge_offset == 2.0
        assert config.dowel_spacing == 6.0
        assert config.pocket_hole_edge_offset == 4.0
        assert config.pocket_hole_spacing == 8.0

    def test_custom_joint_types(self) -> None:
        """JoineryConfigSchema should accept custom joint types."""
        config = JoineryConfigSchema(
            default_shelf_joint=JoineryTypeConfig.POCKET_SCREW,
            default_back_joint=JoineryTypeConfig.BUTT,
        )
        assert config.default_shelf_joint == JoineryTypeConfig.POCKET_SCREW
        assert config.default_back_joint == JoineryTypeConfig.BUTT

    def test_dado_depth_ratio_constraints(self) -> None:
        """JoineryConfigSchema should validate dado_depth_ratio."""
        # Valid ratio
        config = JoineryConfigSchema(dado_depth_ratio=0.25)
        assert config.dado_depth_ratio == 0.25

        # Invalid: too high
        with pytest.raises(PydanticValidationError):
            JoineryConfigSchema(dado_depth_ratio=0.6)

        # Invalid: zero or negative
        with pytest.raises(PydanticValidationError):
            JoineryConfigSchema(dado_depth_ratio=0)

    def test_rabbet_depth_ratio_constraints(self) -> None:
        """JoineryConfigSchema should validate rabbet_depth_ratio."""
        # Valid ratio
        config = JoineryConfigSchema(rabbet_depth_ratio=0.4)
        assert config.rabbet_depth_ratio == 0.4

        # Invalid: too high
        with pytest.raises(PydanticValidationError):
            JoineryConfigSchema(rabbet_depth_ratio=1.5)


class TestSpanLimitsConfigSchema:
    """Tests for SpanLimitsConfigSchema (FRD-14)."""

    def test_defaults(self) -> None:
        """SpanLimitsConfigSchema should have sensible defaults."""
        config = SpanLimitsConfigSchema()
        assert config.plywood_3_4 == 36.0
        assert config.mdf_3_4 == 24.0
        assert config.particle_board_3_4 == 24.0
        assert config.solid_wood_1 == 42.0

    def test_custom_values(self) -> None:
        """SpanLimitsConfigSchema should accept custom span limits."""
        config = SpanLimitsConfigSchema(
            plywood_3_4=40.0,
            mdf_3_4=28.0,
        )
        assert config.plywood_3_4 == 40.0
        assert config.mdf_3_4 == 28.0

    def test_minimum_constraint(self) -> None:
        """SpanLimitsConfigSchema should reject spans below 12 inches."""
        with pytest.raises(PydanticValidationError):
            SpanLimitsConfigSchema(plywood_3_4=10.0)


class TestHardwareConfigSchema:
    """Tests for HardwareConfigSchema (FRD-14)."""

    def test_defaults(self) -> None:
        """HardwareConfigSchema should have sensible defaults."""
        config = HardwareConfigSchema()
        assert config.add_overage is True
        assert config.overage_percent == 10.0
        assert config.case_screw_spacing == 8.0
        assert config.back_panel_screw_spacing == 6.0

    def test_overage_disabled(self) -> None:
        """HardwareConfigSchema should allow disabling overage."""
        config = HardwareConfigSchema(add_overage=False)
        assert config.add_overage is False

    def test_custom_overage_percent(self) -> None:
        """HardwareConfigSchema should accept custom overage percent."""
        config = HardwareConfigSchema(overage_percent=15.0)
        assert config.overage_percent == 15.0

    def test_overage_percent_max(self) -> None:
        """HardwareConfigSchema should reject overage above 50%."""
        with pytest.raises(PydanticValidationError):
            HardwareConfigSchema(overage_percent=60.0)


class TestWoodworkingConfigSchema:
    """Tests for WoodworkingConfigSchema (FRD-14)."""

    def test_defaults(self) -> None:
        """WoodworkingConfigSchema should have sensible defaults."""
        config = WoodworkingConfigSchema()
        assert config.joinery is None
        assert config.span_limits is None
        assert config.hardware is None
        assert config.warnings_enabled is True
        assert config.grain_recommendations_enabled is True
        assert config.capacity_estimates_enabled is True

    def test_with_joinery(self) -> None:
        """WoodworkingConfigSchema should accept joinery config."""
        config = WoodworkingConfigSchema(
            joinery=JoineryConfigSchema(
                default_shelf_joint=JoineryTypeConfig.POCKET_SCREW
            )
        )
        assert config.joinery is not None
        assert config.joinery.default_shelf_joint == JoineryTypeConfig.POCKET_SCREW

    def test_with_span_limits(self) -> None:
        """WoodworkingConfigSchema should accept span limits."""
        config = WoodworkingConfigSchema(
            span_limits=SpanLimitsConfigSchema(plywood_3_4=40.0)
        )
        assert config.span_limits is not None
        assert config.span_limits.plywood_3_4 == 40.0

    def test_with_hardware(self) -> None:
        """WoodworkingConfigSchema should accept hardware config."""
        config = WoodworkingConfigSchema(
            hardware=HardwareConfigSchema(overage_percent=15.0)
        )
        assert config.hardware is not None
        assert config.hardware.overage_percent == 15.0

    def test_warnings_disabled(self) -> None:
        """WoodworkingConfigSchema should allow disabling warnings."""
        config = WoodworkingConfigSchema(warnings_enabled=False)
        assert config.warnings_enabled is False


class TestCabinetConfigurationWoodworking:
    """Tests for woodworking configuration in CabinetConfiguration (FRD-14)."""

    def test_woodworking_defaults_to_none(self) -> None:
        """CabinetConfiguration should have woodworking=None by default."""
        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.woodworking is None

    def test_woodworking_with_defaults(self) -> None:
        """CabinetConfiguration should accept woodworking config."""
        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            woodworking=WoodworkingConfigSchema(),
        )
        assert config.woodworking is not None
        assert config.woodworking.warnings_enabled is True

    def test_v1_5_in_supported_versions(self) -> None:
        """SUPPORTED_VERSIONS should include '1.5'."""
        from cabinets.application.config.schema import SUPPORTED_VERSIONS

        assert "1.5" in SUPPORTED_VERSIONS

    def test_schema_version_1_5_accepted(self) -> None:
        """Schema version 1.5 should be accepted."""
        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.5"

    def test_full_woodworking_config(self) -> None:
        """Full woodworking configuration should work."""
        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            woodworking=WoodworkingConfigSchema(
                joinery=JoineryConfigSchema(
                    default_shelf_joint=JoineryTypeConfig.DADO,
                    dado_depth_ratio=0.333,
                ),
                span_limits=SpanLimitsConfigSchema(
                    plywood_3_4=36.0,
                    mdf_3_4=24.0,
                ),
                hardware=HardwareConfigSchema(
                    add_overage=True,
                    overage_percent=10.0,
                ),
                warnings_enabled=True,
            ),
        )
        assert config.woodworking is not None
        assert config.woodworking.joinery is not None
        assert config.woodworking.joinery.dado_depth_ratio == pytest.approx(0.333, rel=0.01)


class TestConfigToWoodworkingAdapter:
    """Tests for config_to_woodworking adapter function (FRD-14)."""

    def test_none_woodworking_returns_none(self) -> None:
        """config_to_woodworking should return None if no woodworking config."""
        from cabinets.application.config.adapter import config_to_woodworking

        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        result = config_to_woodworking(config)
        assert result is None

    def test_converts_to_domain_config(self) -> None:
        """config_to_woodworking should convert to domain WoodworkingConfig."""
        from cabinets.application.config.adapter import config_to_woodworking
        from cabinets.domain.value_objects import JointType

        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            woodworking=WoodworkingConfigSchema(
                joinery=JoineryConfigSchema(
                    default_shelf_joint=JoineryTypeConfig.DADO,
                    dado_depth_ratio=0.25,
                ),
            ),
        )
        result = config_to_woodworking(config)
        assert result is not None
        assert result.default_shelf_joint == JointType.DADO
        assert result.dado_depth_ratio == pytest.approx(0.25)

    def test_maps_joint_types_correctly(self) -> None:
        """config_to_woodworking should map all joint types correctly."""
        from cabinets.application.config.adapter import config_to_woodworking
        from cabinets.domain.value_objects import JointType

        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            woodworking=WoodworkingConfigSchema(
                joinery=JoineryConfigSchema(
                    default_shelf_joint=JoineryTypeConfig.BISCUIT,
                    default_back_joint=JoineryTypeConfig.BUTT,
                ),
            ),
        )
        result = config_to_woodworking(config)
        assert result is not None
        assert result.default_shelf_joint == JointType.BISCUIT
        assert result.default_back_joint == JointType.BUTT


# =============================================================================
# Infrastructure Integration Configuration Tests (FRD-15)
# =============================================================================


class TestInfrastructureEnums:
    """Tests for infrastructure-related enums."""

    def test_lighting_type_values(self) -> None:
        """LightingTypeConfig should have correct enum values."""
        from cabinets.application.config import LightingTypeConfig

        assert LightingTypeConfig.LED_STRIP.value == "led_strip"
        assert LightingTypeConfig.PUCK_LIGHT.value == "puck_light"
        assert LightingTypeConfig.ACCENT.value == "accent"

    def test_lighting_location_values(self) -> None:
        """LightingLocationConfig should have correct enum values."""
        from cabinets.application.config import LightingLocationConfig

        assert LightingLocationConfig.UNDER_CABINET.value == "under_cabinet"
        assert LightingLocationConfig.IN_CABINET.value == "in_cabinet"
        assert LightingLocationConfig.ABOVE_CABINET.value == "above_cabinet"

    def test_outlet_type_values(self) -> None:
        """OutletTypeConfig should have correct enum values."""
        from cabinets.application.config import OutletTypeConfig

        assert OutletTypeConfig.SINGLE.value == "single"
        assert OutletTypeConfig.DOUBLE.value == "double"
        assert OutletTypeConfig.GFI.value == "gfi"

    def test_cable_management_type_values(self) -> None:
        """CableManagementTypeConfig should have correct enum values."""
        from cabinets.application.config import CableManagementTypeConfig

        assert CableManagementTypeConfig.GROMMET.value == "grommet"
        assert CableManagementTypeConfig.CHANNEL.value == "channel"

    def test_ventilation_pattern_values(self) -> None:
        """VentilationPatternConfig should have correct enum values."""
        from cabinets.application.config import VentilationPatternConfig

        assert VentilationPatternConfig.GRID.value == "grid"
        assert VentilationPatternConfig.SLOT.value == "slot"
        assert VentilationPatternConfig.CIRCULAR.value == "circular"

    def test_conduit_direction_values(self) -> None:
        """ConduitDirectionConfig should have correct enum values."""
        from cabinets.application.config import ConduitDirectionConfig

        assert ConduitDirectionConfig.TOP.value == "top"
        assert ConduitDirectionConfig.BOTTOM.value == "bottom"
        assert ConduitDirectionConfig.LEFT.value == "left"
        assert ConduitDirectionConfig.RIGHT.value == "right"


class TestPositionConfigSchema:
    """Tests for PositionConfigSchema."""

    def test_required_fields(self) -> None:
        """PositionConfigSchema requires x and y."""
        from cabinets.application.config import PositionConfigSchema

        pos = PositionConfigSchema(x=10.0, y=20.0)
        assert pos.x == 10.0
        assert pos.y == 20.0

    def test_missing_x_raises_error(self) -> None:
        """PositionConfigSchema should raise error if x is missing."""
        from cabinets.application.config import PositionConfigSchema

        with pytest.raises(PydanticValidationError):
            PositionConfigSchema(y=20.0)  # type: ignore

    def test_missing_y_raises_error(self) -> None:
        """PositionConfigSchema should raise error if y is missing."""
        from cabinets.application.config import PositionConfigSchema

        with pytest.raises(PydanticValidationError):
            PositionConfigSchema(x=10.0)  # type: ignore

    def test_rejects_unknown_fields(self) -> None:
        """PositionConfigSchema should reject unknown fields."""
        from cabinets.application.config import PositionConfigSchema

        with pytest.raises(PydanticValidationError):
            PositionConfigSchema(x=10.0, y=20.0, z=30.0)  # type: ignore


class TestLightingConfigSchema:
    """Tests for LightingConfigSchema."""

    def test_required_fields(self) -> None:
        """LightingConfigSchema requires type, location, and section_indices."""
        from cabinets.application.config import (
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        lighting = LightingConfigSchema(
            type=LightingTypeConfig.PUCK_LIGHT,
            location=LightingLocationConfig.UNDER_CABINET,
            section_indices=[0, 1],
        )
        assert lighting.type == LightingTypeConfig.PUCK_LIGHT
        assert lighting.location == LightingLocationConfig.UNDER_CABINET
        assert lighting.section_indices == [0, 1]

    def test_led_strip_requires_length(self) -> None:
        """LightingConfigSchema should require length for LED strips."""
        from cabinets.application.config import (
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        with pytest.raises(PydanticValidationError) as exc_info:
            LightingConfigSchema(
                type=LightingTypeConfig.LED_STRIP,
                location=LightingLocationConfig.UNDER_CABINET,
                section_indices=[0],
            )
        assert "LED strip lighting requires 'length'" in str(exc_info.value)

    def test_led_strip_with_length_valid(self) -> None:
        """LightingConfigSchema should accept LED strip with length."""
        from cabinets.application.config import (
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        lighting = LightingConfigSchema(
            type=LightingTypeConfig.LED_STRIP,
            location=LightingLocationConfig.UNDER_CABINET,
            section_indices=[0],
            length=24.0,
        )
        assert lighting.length == 24.0

    def test_default_values(self) -> None:
        """LightingConfigSchema should have correct defaults."""
        from cabinets.application.config import (
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        lighting = LightingConfigSchema(
            type=LightingTypeConfig.PUCK_LIGHT,
            location=LightingLocationConfig.IN_CABINET,
            section_indices=[0],
        )
        assert lighting.diameter == 2.5
        assert lighting.channel_width == 0.5
        assert lighting.channel_depth == 0.25
        assert lighting.position is None

    def test_section_indices_min_length(self) -> None:
        """LightingConfigSchema should require at least one section index."""
        from cabinets.application.config import (
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        with pytest.raises(PydanticValidationError):
            LightingConfigSchema(
                type=LightingTypeConfig.PUCK_LIGHT,
                location=LightingLocationConfig.IN_CABINET,
                section_indices=[],
            )

    def test_rejects_unknown_fields(self) -> None:
        """LightingConfigSchema should reject unknown fields."""
        from cabinets.application.config import (
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        with pytest.raises(PydanticValidationError):
            LightingConfigSchema(
                type=LightingTypeConfig.PUCK_LIGHT,
                location=LightingLocationConfig.IN_CABINET,
                section_indices=[0],
                unknown_field="value",  # type: ignore
            )


class TestOutletConfigSchema:
    """Tests for OutletConfigSchema."""

    def test_required_fields(self) -> None:
        """OutletConfigSchema requires type, section_index, panel, and position."""
        from cabinets.application.config import (
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
        )

        outlet = OutletConfigSchema(
            type=OutletTypeConfig.DOUBLE,
            section_index=1,
            panel="back",
            position=PositionConfigSchema(x=10.0, y=12.0),
        )
        assert outlet.type == OutletTypeConfig.DOUBLE
        assert outlet.section_index == 1
        assert outlet.panel == "back"
        assert outlet.position.x == 10.0

    def test_default_conduit_direction(self) -> None:
        """OutletConfigSchema should default conduit_direction to BOTTOM."""
        from cabinets.application.config import (
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
            ConduitDirectionConfig,
        )

        outlet = OutletConfigSchema(
            type=OutletTypeConfig.SINGLE,
            section_index=0,
            panel="back",
            position=PositionConfigSchema(x=10.0, y=12.0),
        )
        assert outlet.conduit_direction == ConduitDirectionConfig.BOTTOM

    def test_valid_panel_values(self) -> None:
        """OutletConfigSchema should accept valid panel values."""
        from cabinets.application.config import (
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
        )

        for panel in ["back", "left_side", "right_side"]:
            outlet = OutletConfigSchema(
                type=OutletTypeConfig.SINGLE,
                section_index=0,
                panel=panel,
                position=PositionConfigSchema(x=10.0, y=12.0),
            )
            assert outlet.panel == panel

    def test_invalid_panel_raises_error(self) -> None:
        """OutletConfigSchema should reject invalid panel values."""
        from cabinets.application.config import (
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
        )

        with pytest.raises(PydanticValidationError):
            OutletConfigSchema(
                type=OutletTypeConfig.SINGLE,
                section_index=0,
                panel="front",  # Invalid
                position=PositionConfigSchema(x=10.0, y=12.0),
            )

    def test_negative_section_index_raises_error(self) -> None:
        """OutletConfigSchema should reject negative section_index."""
        from cabinets.application.config import (
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
        )

        with pytest.raises(PydanticValidationError):
            OutletConfigSchema(
                type=OutletTypeConfig.SINGLE,
                section_index=-1,
                panel="back",
                position=PositionConfigSchema(x=10.0, y=12.0),
            )


class TestGrommetConfigSchema:
    """Tests for GrommetConfigSchema."""

    def test_required_fields(self) -> None:
        """GrommetConfigSchema requires size, panel, and position."""
        from cabinets.application.config import (
            GrommetConfigSchema,
            PositionConfigSchema,
        )

        grommet = GrommetConfigSchema(
            size=2.5,
            panel="back",
            position=PositionConfigSchema(x=5.0, y=10.0),
        )
        assert grommet.size == 2.5
        assert grommet.panel == "back"
        assert grommet.position.x == 5.0

    def test_section_index_optional(self) -> None:
        """GrommetConfigSchema section_index should be optional."""
        from cabinets.application.config import (
            GrommetConfigSchema,
            PositionConfigSchema,
        )

        grommet = GrommetConfigSchema(
            size=2.0,
            panel="back",
            position=PositionConfigSchema(x=5.0, y=10.0),
        )
        assert grommet.section_index is None

        grommet_with_section = GrommetConfigSchema(
            size=2.0,
            panel="back",
            position=PositionConfigSchema(x=5.0, y=10.0),
            section_index=2,
        )
        assert grommet_with_section.section_index == 2

    def test_common_sizes_accepted(self) -> None:
        """GrommetConfigSchema should accept common grommet sizes."""
        from cabinets.application.config import (
            GrommetConfigSchema,
            PositionConfigSchema,
        )

        for size in [2.0, 2.5, 3.0]:
            grommet = GrommetConfigSchema(
                size=size,
                panel="back",
                position=PositionConfigSchema(x=5.0, y=10.0),
            )
            assert grommet.size == size

    def test_non_standard_size_in_range_accepted(self) -> None:
        """GrommetConfigSchema should accept non-standard sizes in reasonable range."""
        from cabinets.application.config import (
            GrommetConfigSchema,
            PositionConfigSchema,
        )

        grommet = GrommetConfigSchema(
            size=1.5,  # Non-standard but valid
            panel="back",
            position=PositionConfigSchema(x=5.0, y=10.0),
        )
        assert grommet.size == 1.5

    def test_size_too_small_raises_error(self) -> None:
        """GrommetConfigSchema should reject sizes below minimum."""
        from cabinets.application.config import (
            GrommetConfigSchema,
            PositionConfigSchema,
        )

        with pytest.raises(PydanticValidationError):
            GrommetConfigSchema(
                size=0.3,  # Below minimum
                panel="back",
                position=PositionConfigSchema(x=5.0, y=10.0),
            )


class TestCableChannelConfigSchema:
    """Tests for CableChannelConfigSchema."""

    def test_required_fields(self) -> None:
        """CableChannelConfigSchema requires start and end positions."""
        from cabinets.application.config import (
            CableChannelConfigSchema,
            PositionConfigSchema,
        )

        channel = CableChannelConfigSchema(
            start=PositionConfigSchema(x=0.0, y=10.0),
            end=PositionConfigSchema(x=20.0, y=10.0),
        )
        assert channel.start.x == 0.0
        assert channel.end.x == 20.0

    def test_default_values(self) -> None:
        """CableChannelConfigSchema should have correct defaults."""
        from cabinets.application.config import (
            CableChannelConfigSchema,
            PositionConfigSchema,
        )

        channel = CableChannelConfigSchema(
            start=PositionConfigSchema(x=0.0, y=10.0),
            end=PositionConfigSchema(x=20.0, y=10.0),
        )
        assert channel.width == 2.0
        assert channel.depth == 1.0

    def test_custom_dimensions(self) -> None:
        """CableChannelConfigSchema should accept custom dimensions."""
        from cabinets.application.config import (
            CableChannelConfigSchema,
            PositionConfigSchema,
        )

        channel = CableChannelConfigSchema(
            start=PositionConfigSchema(x=0.0, y=10.0),
            end=PositionConfigSchema(x=20.0, y=10.0),
            width=3.0,
            depth=1.5,
        )
        assert channel.width == 3.0
        assert channel.depth == 1.5


class TestVentilationConfigSchema:
    """Tests for VentilationConfigSchema."""

    def test_required_fields(self) -> None:
        """VentilationConfigSchema requires pattern, panel, position, width, height."""
        from cabinets.application.config import (
            VentilationConfigSchema,
            VentilationPatternConfig,
            PositionConfigSchema,
        )

        vent = VentilationConfigSchema(
            pattern=VentilationPatternConfig.GRID,
            panel="back",
            position=PositionConfigSchema(x=5.0, y=30.0),
            width=6.0,
            height=4.0,
        )
        assert vent.pattern == VentilationPatternConfig.GRID
        assert vent.width == 6.0
        assert vent.height == 4.0

    def test_default_hole_size(self) -> None:
        """VentilationConfigSchema should default hole_size to 0.25."""
        from cabinets.application.config import (
            VentilationConfigSchema,
            VentilationPatternConfig,
            PositionConfigSchema,
        )

        vent = VentilationConfigSchema(
            pattern=VentilationPatternConfig.SLOT,
            panel="back",
            position=PositionConfigSchema(x=5.0, y=30.0),
            width=6.0,
            height=4.0,
        )
        assert vent.hole_size == 0.25

    def test_zero_width_raises_error(self) -> None:
        """VentilationConfigSchema should reject zero width."""
        from cabinets.application.config import (
            VentilationConfigSchema,
            VentilationPatternConfig,
            PositionConfigSchema,
        )

        with pytest.raises(PydanticValidationError):
            VentilationConfigSchema(
                pattern=VentilationPatternConfig.CIRCULAR,
                panel="back",
                position=PositionConfigSchema(x=5.0, y=30.0),
                width=0.0,
                height=4.0,
            )


class TestWireRouteConfigSchema:
    """Tests for WireRouteConfigSchema."""

    def test_required_fields(self) -> None:
        """WireRouteConfigSchema requires waypoints with at least 2 points."""
        from cabinets.application.config import (
            WireRouteConfigSchema,
            PositionConfigSchema,
        )

        route = WireRouteConfigSchema(
            waypoints=[
                PositionConfigSchema(x=0.0, y=0.0),
                PositionConfigSchema(x=10.0, y=10.0),
            ],
        )
        assert len(route.waypoints) == 2

    def test_default_values(self) -> None:
        """WireRouteConfigSchema should have correct defaults."""
        from cabinets.application.config import (
            WireRouteConfigSchema,
            PositionConfigSchema,
        )

        route = WireRouteConfigSchema(
            waypoints=[
                PositionConfigSchema(x=0.0, y=0.0),
                PositionConfigSchema(x=10.0, y=10.0),
            ],
        )
        assert route.hole_diameter == 0.75
        assert route.panel_penetrations == []

    def test_waypoints_min_length(self) -> None:
        """WireRouteConfigSchema should require at least 2 waypoints."""
        from cabinets.application.config import (
            WireRouteConfigSchema,
            PositionConfigSchema,
        )

        with pytest.raises(PydanticValidationError):
            WireRouteConfigSchema(
                waypoints=[PositionConfigSchema(x=0.0, y=0.0)],  # Only 1 point
            )

    def test_panel_penetrations(self) -> None:
        """WireRouteConfigSchema should accept panel_penetrations list."""
        from cabinets.application.config import (
            WireRouteConfigSchema,
            PositionConfigSchema,
        )

        route = WireRouteConfigSchema(
            waypoints=[
                PositionConfigSchema(x=0.0, y=0.0),
                PositionConfigSchema(x=10.0, y=10.0),
                PositionConfigSchema(x=20.0, y=5.0),
            ],
            panel_penetrations=["back", "divider_0"],
        )
        assert route.panel_penetrations == ["back", "divider_0"]


class TestInfrastructureConfigSchema:
    """Tests for InfrastructureConfigSchema."""

    def test_defaults_to_empty_lists(self) -> None:
        """InfrastructureConfigSchema should default all lists to empty."""
        from cabinets.application.config import InfrastructureConfigSchema

        infra = InfrastructureConfigSchema()
        assert infra.lighting == []
        assert infra.outlets == []
        assert infra.grommets == []
        assert infra.cable_channels == []
        assert infra.ventilation == []
        assert infra.wire_routes == []

    def test_with_lighting(self) -> None:
        """InfrastructureConfigSchema should accept lighting configurations."""
        from cabinets.application.config import (
            InfrastructureConfigSchema,
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
        )

        infra = InfrastructureConfigSchema(
            lighting=[
                LightingConfigSchema(
                    type=LightingTypeConfig.PUCK_LIGHT,
                    location=LightingLocationConfig.IN_CABINET,
                    section_indices=[0, 1, 2],
                ),
            ],
        )
        assert len(infra.lighting) == 1
        assert infra.lighting[0].type == LightingTypeConfig.PUCK_LIGHT

    def test_with_outlets(self) -> None:
        """InfrastructureConfigSchema should accept outlet configurations."""
        from cabinets.application.config import (
            InfrastructureConfigSchema,
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
        )

        infra = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.GFI,
                    section_index=0,
                    panel="back",
                    position=PositionConfigSchema(x=10.0, y=36.0),
                ),
            ],
        )
        assert len(infra.outlets) == 1
        assert infra.outlets[0].type == OutletTypeConfig.GFI

    def test_rejects_unknown_fields(self) -> None:
        """InfrastructureConfigSchema should reject unknown fields."""
        from cabinets.application.config import InfrastructureConfigSchema

        with pytest.raises(PydanticValidationError):
            InfrastructureConfigSchema(unknown_field=[])  # type: ignore


class TestCabinetConfigurationInfrastructure:
    """Tests for infrastructure in CabinetConfiguration."""

    def test_infrastructure_defaults_to_none(self) -> None:
        """CabinetConfiguration infrastructure should default to None."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.infrastructure is None

    def test_infrastructure_with_defaults(self) -> None:
        """CabinetConfiguration should accept infrastructure with defaults."""
        from cabinets.application.config import InfrastructureConfigSchema

        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(),
        )
        assert config.infrastructure is not None
        assert config.infrastructure.lighting == []

    def test_v1_6_in_supported_versions(self) -> None:
        """Version 1.6 should be in SUPPORTED_VERSIONS."""
        assert "1.6" in SUPPORTED_VERSIONS

    def test_schema_version_1_6_accepted(self) -> None:
        """Schema version 1.6 should be accepted."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.6"

    def test_full_infrastructure_config(self) -> None:
        """CabinetConfiguration should accept full infrastructure config."""
        from cabinets.application.config import (
            InfrastructureConfigSchema,
            LightingConfigSchema,
            LightingTypeConfig,
            LightingLocationConfig,
            OutletConfigSchema,
            OutletTypeConfig,
            PositionConfigSchema,
            GrommetConfigSchema,
            VentilationConfigSchema,
            VentilationPatternConfig,
        )

        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=72.0, height=84.0, depth=24.0),
            infrastructure=InfrastructureConfigSchema(
                lighting=[
                    LightingConfigSchema(
                        type=LightingTypeConfig.LED_STRIP,
                        location=LightingLocationConfig.UNDER_CABINET,
                        section_indices=[0, 1],
                        length=36.0,
                    ),
                ],
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.DOUBLE,
                        section_index=1,
                        panel="back",
                        position=PositionConfigSchema(x=12.0, y=36.0),
                    ),
                ],
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=6.0, y=6.0),
                    ),
                ],
                ventilation=[
                    VentilationConfigSchema(
                        pattern=VentilationPatternConfig.GRID,
                        panel="back",
                        position=PositionConfigSchema(x=24.0, y=60.0),
                        width=8.0,
                        height=6.0,
                    ),
                ],
            ),
        )
        assert config.infrastructure is not None
        assert len(config.infrastructure.lighting) == 1
        assert len(config.infrastructure.outlets) == 1
        assert len(config.infrastructure.grommets) == 1
        assert len(config.infrastructure.ventilation) == 1

    def test_backward_compatibility_without_infrastructure(self) -> None:
        """Older schema versions should work without infrastructure field."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.infrastructure is None


# =============================================================================
# Output Format Configuration Tests (FRD-16)
# =============================================================================


class TestDxfOutputConfigSchema:
    """Tests for DxfOutputConfigSchema model."""

    def test_defaults(self) -> None:
        """DxfOutputConfigSchema should have sensible defaults."""
        from cabinets.application.config import DxfOutputConfigSchema

        config = DxfOutputConfigSchema()
        assert config.mode == "combined"
        assert config.units == "inches"
        assert config.hole_pattern == "32mm"
        assert config.hole_diameter == 0.197

    def test_per_panel_mode(self) -> None:
        """DxfOutputConfigSchema should accept per_panel mode."""
        from cabinets.application.config import DxfOutputConfigSchema

        config = DxfOutputConfigSchema(mode="per_panel")
        assert config.mode == "per_panel"

    def test_mm_units(self) -> None:
        """DxfOutputConfigSchema should accept mm units."""
        from cabinets.application.config import DxfOutputConfigSchema

        config = DxfOutputConfigSchema(units="mm")
        assert config.units == "mm"

    def test_custom_hole_diameter(self) -> None:
        """DxfOutputConfigSchema should accept custom hole diameter."""
        from cabinets.application.config import DxfOutputConfigSchema

        config = DxfOutputConfigSchema(hole_diameter=0.25)
        assert config.hole_diameter == 0.25

    def test_rejects_invalid_mode(self) -> None:
        """DxfOutputConfigSchema should reject invalid mode."""
        from cabinets.application.config import DxfOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DxfOutputConfigSchema(mode="invalid")  # type: ignore
        assert "mode" in str(exc_info.value)

    def test_rejects_zero_hole_diameter(self) -> None:
        """DxfOutputConfigSchema should reject zero hole diameter."""
        from cabinets.application.config import DxfOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DxfOutputConfigSchema(hole_diameter=0)
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """DxfOutputConfigSchema should reject unknown fields."""
        from cabinets.application.config import DxfOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DxfOutputConfigSchema(color="red")  # type: ignore
        assert "color" in str(exc_info.value)


class TestSvgOutputConfigSchema:
    """Tests for SvgOutputConfigSchema model."""

    def test_defaults(self) -> None:
        """SvgOutputConfigSchema should have sensible defaults."""
        from cabinets.application.config import SvgOutputConfigSchema

        config = SvgOutputConfigSchema()
        assert config.scale == 10.0
        assert config.show_dimensions is True
        assert config.show_labels is True
        assert config.show_grain is False
        assert config.use_panel_colors is True

    def test_custom_scale(self) -> None:
        """SvgOutputConfigSchema should accept custom scale."""
        from cabinets.application.config import SvgOutputConfigSchema

        config = SvgOutputConfigSchema(scale=15.0)
        assert config.scale == 15.0

    def test_show_grain_enabled(self) -> None:
        """SvgOutputConfigSchema should allow enabling grain display."""
        from cabinets.application.config import SvgOutputConfigSchema

        config = SvgOutputConfigSchema(show_grain=True)
        assert config.show_grain is True

    def test_rejects_zero_scale(self) -> None:
        """SvgOutputConfigSchema should reject zero scale."""
        from cabinets.application.config import SvgOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            SvgOutputConfigSchema(scale=0)
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_negative_scale(self) -> None:
        """SvgOutputConfigSchema should reject negative scale."""
        from cabinets.application.config import SvgOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            SvgOutputConfigSchema(scale=-5.0)
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """SvgOutputConfigSchema should reject unknown fields."""
        from cabinets.application.config import SvgOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            SvgOutputConfigSchema(background="white")  # type: ignore
        assert "background" in str(exc_info.value)


class TestBomOutputConfigSchema:
    """Tests for BomOutputConfigSchema model."""

    def test_defaults(self) -> None:
        """BomOutputConfigSchema should have sensible defaults."""
        from cabinets.application.config import BomOutputConfigSchema

        config = BomOutputConfigSchema()
        assert config.format == "text"
        assert config.include_costs is False
        assert config.sheet_size == (48.0, 96.0)

    def test_csv_format(self) -> None:
        """BomOutputConfigSchema should accept csv format."""
        from cabinets.application.config import BomOutputConfigSchema

        config = BomOutputConfigSchema(format="csv")
        assert config.format == "csv"

    def test_json_format(self) -> None:
        """BomOutputConfigSchema should accept json format."""
        from cabinets.application.config import BomOutputConfigSchema

        config = BomOutputConfigSchema(format="json")
        assert config.format == "json"

    def test_include_costs_enabled(self) -> None:
        """BomOutputConfigSchema should allow enabling cost calculations."""
        from cabinets.application.config import BomOutputConfigSchema

        config = BomOutputConfigSchema(include_costs=True)
        assert config.include_costs is True

    def test_custom_sheet_size(self) -> None:
        """BomOutputConfigSchema should accept custom sheet size."""
        from cabinets.application.config import BomOutputConfigSchema

        config = BomOutputConfigSchema(sheet_size=(60.0, 60.0))
        assert config.sheet_size == (60.0, 60.0)

    def test_rejects_invalid_format(self) -> None:
        """BomOutputConfigSchema should reject invalid format."""
        from cabinets.application.config import BomOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            BomOutputConfigSchema(format="excel")  # type: ignore
        assert "format" in str(exc_info.value)

    def test_rejects_zero_sheet_width(self) -> None:
        """BomOutputConfigSchema should reject zero sheet width."""
        from cabinets.application.config import BomOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            BomOutputConfigSchema(sheet_size=(0.0, 96.0))
        assert "Sheet dimensions must be positive" in str(exc_info.value)

    def test_rejects_negative_sheet_height(self) -> None:
        """BomOutputConfigSchema should reject negative sheet height."""
        from cabinets.application.config import BomOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            BomOutputConfigSchema(sheet_size=(48.0, -10.0))
        assert "Sheet dimensions must be positive" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """BomOutputConfigSchema should reject unknown fields."""
        from cabinets.application.config import BomOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            BomOutputConfigSchema(currency="USD")  # type: ignore
        assert "currency" in str(exc_info.value)


class TestAssemblyOutputConfigSchema:
    """Tests for AssemblyOutputConfigSchema model."""

    def test_defaults(self) -> None:
        """AssemblyOutputConfigSchema should have sensible defaults."""
        from cabinets.application.config import AssemblyOutputConfigSchema

        config = AssemblyOutputConfigSchema()
        assert config.include_safety_warnings is True
        assert config.include_timestamps is True

    def test_disable_safety_warnings(self) -> None:
        """AssemblyOutputConfigSchema should allow disabling safety warnings."""
        from cabinets.application.config import AssemblyOutputConfigSchema

        config = AssemblyOutputConfigSchema(include_safety_warnings=False)
        assert config.include_safety_warnings is False

    def test_disable_timestamps(self) -> None:
        """AssemblyOutputConfigSchema should allow disabling timestamps."""
        from cabinets.application.config import AssemblyOutputConfigSchema

        config = AssemblyOutputConfigSchema(include_timestamps=False)
        assert config.include_timestamps is False

    def test_rejects_unknown_fields(self) -> None:
        """AssemblyOutputConfigSchema should reject unknown fields."""
        from cabinets.application.config import AssemblyOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            AssemblyOutputConfigSchema(author="test")  # type: ignore
        assert "author" in str(exc_info.value)


class TestJsonOutputConfigSchema:
    """Tests for JsonOutputConfigSchema model."""

    def test_defaults(self) -> None:
        """JsonOutputConfigSchema should have sensible defaults."""
        from cabinets.application.config import JsonOutputConfigSchema

        config = JsonOutputConfigSchema()
        assert config.include_3d_positions is True
        assert config.include_joinery is True
        assert config.include_warnings is True
        assert config.include_bom is True
        assert config.indent == 2

    def test_disable_3d_positions(self) -> None:
        """JsonOutputConfigSchema should allow disabling 3D positions."""
        from cabinets.application.config import JsonOutputConfigSchema

        config = JsonOutputConfigSchema(include_3d_positions=False)
        assert config.include_3d_positions is False

    def test_compact_json(self) -> None:
        """JsonOutputConfigSchema should allow compact JSON (indent=0)."""
        from cabinets.application.config import JsonOutputConfigSchema

        config = JsonOutputConfigSchema(indent=0)
        assert config.indent == 0

    def test_custom_indent(self) -> None:
        """JsonOutputConfigSchema should accept custom indent."""
        from cabinets.application.config import JsonOutputConfigSchema

        config = JsonOutputConfigSchema(indent=4)
        assert config.indent == 4

    def test_rejects_negative_indent(self) -> None:
        """JsonOutputConfigSchema should reject negative indent."""
        from cabinets.application.config import JsonOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            JsonOutputConfigSchema(indent=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """JsonOutputConfigSchema should reject unknown fields."""
        from cabinets.application.config import JsonOutputConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            JsonOutputConfigSchema(minify=True)  # type: ignore
        assert "minify" in str(exc_info.value)


class TestOutputConfigFRD16:
    """Tests for extended OutputConfig model (FRD-16)."""

    def test_legacy_defaults(self) -> None:
        """OutputConfig should maintain legacy default values."""
        config = OutputConfig()
        assert config.format == "all"
        assert config.stl_file is None

    def test_new_defaults(self) -> None:
        """OutputConfig should have sensible defaults for new fields."""
        config = OutputConfig()
        assert config.formats == []
        assert config.output_dir is None
        assert config.project_name == "cabinet"
        assert config.dxf is None
        assert config.svg is None
        assert config.bom is None
        assert config.assembly is None
        assert config.json_options is None

    def test_formats_list(self) -> None:
        """OutputConfig should accept a list of formats."""
        config = OutputConfig(formats=["stl", "dxf", "json"])
        assert config.formats == ["stl", "dxf", "json"]

    def test_all_valid_formats(self) -> None:
        """OutputConfig should accept all valid format names."""
        valid_formats = ["stl", "dxf", "json", "bom", "svg", "assembly", "cutlist", "diagram", "materials", "woodworking"]
        config = OutputConfig(formats=valid_formats)
        assert set(config.formats) == set(valid_formats)

    def test_formats_with_all(self) -> None:
        """OutputConfig should accept 'all' in formats list."""
        config = OutputConfig(formats=["all"])
        assert config.formats == ["all"]

    def test_rejects_invalid_formats(self) -> None:
        """OutputConfig should reject invalid format names."""
        with pytest.raises(PydanticValidationError) as exc_info:
            OutputConfig(formats=["stl", "pdf", "docx"])
        error_str = str(exc_info.value)
        assert "Invalid formats" in error_str
        assert "pdf" in error_str or "docx" in error_str

    def test_output_dir(self) -> None:
        """OutputConfig should accept output_dir path."""
        config = OutputConfig(output_dir="./output")
        assert config.output_dir == "./output"

    def test_project_name(self) -> None:
        """OutputConfig should accept custom project name."""
        config = OutputConfig(project_name="living_room_cabinet")
        assert config.project_name == "living_room_cabinet"

    def test_dxf_config(self) -> None:
        """OutputConfig should accept DXF configuration."""
        from cabinets.application.config import DxfOutputConfigSchema

        config = OutputConfig(dxf=DxfOutputConfigSchema(mode="per_panel", units="mm"))
        assert config.dxf is not None
        assert config.dxf.mode == "per_panel"
        assert config.dxf.units == "mm"

    def test_svg_config(self) -> None:
        """OutputConfig should accept SVG configuration."""
        from cabinets.application.config import SvgOutputConfigSchema

        config = OutputConfig(svg=SvgOutputConfigSchema(scale=15.0, show_grain=True))
        assert config.svg is not None
        assert config.svg.scale == 15.0
        assert config.svg.show_grain is True

    def test_bom_config(self) -> None:
        """OutputConfig should accept BOM configuration."""
        from cabinets.application.config import BomOutputConfigSchema

        config = OutputConfig(bom=BomOutputConfigSchema(format="csv"))
        assert config.bom is not None
        assert config.bom.format == "csv"

    def test_assembly_config(self) -> None:
        """OutputConfig should accept assembly configuration."""
        from cabinets.application.config import AssemblyOutputConfigSchema

        config = OutputConfig(assembly=AssemblyOutputConfigSchema(include_safety_warnings=False))
        assert config.assembly is not None
        assert config.assembly.include_safety_warnings is False

    def test_json_config_with_alias(self) -> None:
        """OutputConfig should accept json_options via 'json' alias."""
        # Test using the model directly with json_options
        from cabinets.application.config import JsonOutputConfigSchema

        config = OutputConfig(json_options=JsonOutputConfigSchema(indent=4))
        assert config.json_options is not None
        assert config.json_options.indent == 4


class TestCabinetConfigurationFRD16:
    """Tests for CabinetConfiguration with FRD-16 output options."""

    def test_v1_7_schema_version(self) -> None:
        """v1.7 schema version should be accepted."""
        config = CabinetConfiguration(
            schema_version="1.7",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.7"

    def test_full_output_config(self) -> None:
        """Full output configuration with all FRD-16 options should work."""
        from cabinets.application.config import (
            AssemblyOutputConfigSchema,
            BomOutputConfigSchema,
            DxfOutputConfigSchema,
            JsonOutputConfigSchema,
            SvgOutputConfigSchema,
        )

        config = CabinetConfiguration(
            schema_version="1.7",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            output=OutputConfig(
                formats=["stl", "dxf", "json", "bom", "svg", "assembly"],
                output_dir="./output",
                project_name="living_room_cabinet",
                dxf=DxfOutputConfigSchema(mode="per_panel", units="mm"),
                svg=SvgOutputConfigSchema(scale=15.0, show_grain=True),
                bom=BomOutputConfigSchema(format="csv"),
                assembly=AssemblyOutputConfigSchema(include_safety_warnings=True),
                json_options=JsonOutputConfigSchema(include_3d_positions=True, include_joinery=True),
            ),
        )
        assert config.output.formats == ["stl", "dxf", "json", "bom", "svg", "assembly"]
        assert config.output.output_dir == "./output"
        assert config.output.project_name == "living_room_cabinet"
        assert config.output.dxf is not None
        assert config.output.dxf.mode == "per_panel"
        assert config.output.svg is not None
        assert config.output.svg.show_grain is True
        assert config.output.bom is not None
        assert config.output.bom.format == "csv"
        assert config.output.assembly is not None
        assert config.output.json_options is not None

    def test_backward_compatibility_v1_0_output(self) -> None:
        """v1.0 output config should still work."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            output=OutputConfig(format="stl", stl_file="cabinet.stl"),
        )
        assert config.output.format == "stl"
        assert config.output.stl_file == "cabinet.stl"
        assert config.output.formats == []

    def test_mixed_legacy_and_new_output(self) -> None:
        """Both legacy format and new formats list can coexist."""
        config = CabinetConfiguration(
            schema_version="1.7",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            output=OutputConfig(
                format="all",
                formats=["stl", "json"],
                project_name="test_cabinet",
            ),
        )
        assert config.output.format == "all"
        assert config.output.formats == ["stl", "json"]


# =============================================================================
# Built-in Desk Configuration Tests (FRD-18)
# =============================================================================


class TestDeskTypeConfig:
    """Tests for DeskTypeConfig enum."""

    def test_desk_type_values(self) -> None:
        """DeskTypeConfig should have expected values."""
        from cabinets.application.config.schema import DeskTypeConfig

        assert DeskTypeConfig.SINGLE.value == "single"
        assert DeskTypeConfig.L_SHAPED.value == "l_shaped"
        assert DeskTypeConfig.CORNER.value == "corner"
        assert DeskTypeConfig.STANDING.value == "standing"

    def test_desk_type_count(self) -> None:
        """DeskTypeConfig should have 4 values."""
        from cabinets.application.config.schema import DeskTypeConfig

        assert len(DeskTypeConfig) == 4


class TestEdgeTreatmentConfig:
    """Tests for EdgeTreatmentConfig enum."""

    def test_edge_treatment_values(self) -> None:
        """EdgeTreatmentConfig should have expected values."""
        from cabinets.application.config.schema import EdgeTreatmentConfig

        assert EdgeTreatmentConfig.SQUARE.value == "square"
        assert EdgeTreatmentConfig.BULLNOSE.value == "bullnose"
        assert EdgeTreatmentConfig.WATERFALL.value == "waterfall"
        assert EdgeTreatmentConfig.EASED.value == "eased"

    def test_edge_treatment_count(self) -> None:
        """EdgeTreatmentConfig should have 4 values."""
        from cabinets.application.config.schema import EdgeTreatmentConfig

        assert len(EdgeTreatmentConfig) == 4


class TestPedestalTypeConfig:
    """Tests for PedestalTypeConfig enum."""

    def test_pedestal_type_values(self) -> None:
        """PedestalTypeConfig should have expected values."""
        from cabinets.application.config.schema import PedestalTypeConfig

        assert PedestalTypeConfig.FILE.value == "file"
        assert PedestalTypeConfig.STORAGE.value == "storage"
        assert PedestalTypeConfig.OPEN.value == "open"

    def test_pedestal_type_count(self) -> None:
        """PedestalTypeConfig should have 3 values."""
        from cabinets.application.config.schema import PedestalTypeConfig

        assert len(PedestalTypeConfig) == 3


class TestDeskMountingConfig:
    """Tests for DeskMountingConfig enum."""

    def test_desk_mounting_values(self) -> None:
        """DeskMountingConfig should have expected values."""
        from cabinets.application.config.schema import DeskMountingConfig

        assert DeskMountingConfig.PEDESTAL.value == "pedestal"
        assert DeskMountingConfig.FLOATING.value == "floating"
        assert DeskMountingConfig.LEGS.value == "legs"

    def test_desk_mounting_count(self) -> None:
        """DeskMountingConfig should have 3 values."""
        from cabinets.application.config.schema import DeskMountingConfig

        assert len(DeskMountingConfig) == 3


class TestDeskGrommetConfigSchema:
    """Tests for DeskGrommetConfigSchema model."""

    def test_valid_grommet(self) -> None:
        """Valid grommet configuration should be accepted."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        config = DeskGrommetConfigSchema(x_position=24.0, y_position=21.0)
        assert config.x_position == 24.0
        assert config.y_position == 21.0
        assert config.diameter == 2.5  # default

    def test_custom_diameter(self) -> None:
        """Custom diameter within range should be accepted."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        config = DeskGrommetConfigSchema(x_position=10.0, y_position=10.0, diameter=3.0)
        assert config.diameter == 3.0

    def test_diameter_at_minimum(self) -> None:
        """Diameter at minimum value should be accepted."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        config = DeskGrommetConfigSchema(x_position=10.0, y_position=10.0, diameter=1.5)
        assert config.diameter == 1.5

    def test_diameter_at_maximum(self) -> None:
        """Diameter at maximum value should be accepted."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        config = DeskGrommetConfigSchema(x_position=10.0, y_position=10.0, diameter=3.5)
        assert config.diameter == 3.5

    def test_diameter_below_minimum_raises_error(self) -> None:
        """Diameter below minimum should raise error."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskGrommetConfigSchema(x_position=10.0, y_position=10.0, diameter=1.0)
        assert "greater than or equal to 1.5" in str(exc_info.value)

    def test_diameter_above_maximum_raises_error(self) -> None:
        """Diameter above maximum should raise error."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskGrommetConfigSchema(x_position=10.0, y_position=10.0, diameter=5.0)
        assert "less than or equal to 3.5" in str(exc_info.value)

    def test_x_position_required(self) -> None:
        """x_position is required."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskGrommetConfigSchema(y_position=10.0)  # type: ignore
        assert "x_position" in str(exc_info.value)

    def test_y_position_required(self) -> None:
        """y_position is required."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskGrommetConfigSchema(x_position=10.0)  # type: ignore
        assert "y_position" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import DeskGrommetConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskGrommetConfigSchema(x_position=10.0, y_position=10.0, color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestDeskSurfaceConfigSchema:
    """Tests for DeskSurfaceConfigSchema model."""

    def test_defaults(self) -> None:
        """DeskSurfaceConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import (
            DeskMountingConfig,
            DeskSurfaceConfigSchema,
            EdgeTreatmentConfig,
        )

        config = DeskSurfaceConfigSchema()
        assert config.desk_height == 30.0
        assert config.depth == 24.0
        assert config.thickness == 1.0
        assert config.edge_treatment == EdgeTreatmentConfig.SQUARE
        assert config.grommets == []
        assert config.mounting == DeskMountingConfig.PEDESTAL
        assert config.exposed_left is False
        assert config.exposed_right is False

    def test_desk_height_range(self) -> None:
        """desk_height should accept values within range."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        # At minimum
        config = DeskSurfaceConfigSchema(desk_height=26.0)
        assert config.desk_height == 26.0

        # At maximum
        config = DeskSurfaceConfigSchema(desk_height=50.0)
        assert config.desk_height == 50.0

    def test_desk_height_below_minimum_raises_error(self) -> None:
        """desk_height below minimum should raise error."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSurfaceConfigSchema(desk_height=25.0)
        assert "greater than or equal to 26" in str(exc_info.value)

    def test_desk_height_above_maximum_raises_error(self) -> None:
        """desk_height above maximum should raise error."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSurfaceConfigSchema(desk_height=51.0)
        assert "less than or equal to 50" in str(exc_info.value)

    def test_depth_range(self) -> None:
        """depth should accept values within range."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        # At minimum
        config = DeskSurfaceConfigSchema(depth=18.0)
        assert config.depth == 18.0

        # At maximum
        config = DeskSurfaceConfigSchema(depth=36.0)
        assert config.depth == 36.0

    def test_depth_below_minimum_raises_error(self) -> None:
        """depth below minimum should raise error."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSurfaceConfigSchema(depth=17.0)
        assert "greater than or equal to 18" in str(exc_info.value)

    def test_thickness_range(self) -> None:
        """thickness should accept values within range."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        # At minimum
        config = DeskSurfaceConfigSchema(thickness=0.75)
        assert config.thickness == 0.75

        # At maximum
        config = DeskSurfaceConfigSchema(thickness=1.5)
        assert config.thickness == 1.5

    def test_edge_treatment_values(self) -> None:
        """All edge treatment values should be accepted."""
        from cabinets.application.config.schema import (
            DeskSurfaceConfigSchema,
            EdgeTreatmentConfig,
        )

        for treatment in EdgeTreatmentConfig:
            config = DeskSurfaceConfigSchema(edge_treatment=treatment)
            assert config.edge_treatment == treatment

    def test_mounting_values(self) -> None:
        """All mounting values should be accepted."""
        from cabinets.application.config.schema import (
            DeskMountingConfig,
            DeskSurfaceConfigSchema,
        )

        for mounting in DeskMountingConfig:
            config = DeskSurfaceConfigSchema(mounting=mounting)
            assert config.mounting == mounting

    def test_with_grommets(self) -> None:
        """Surface with grommets should be accepted."""
        from cabinets.application.config.schema import (
            DeskGrommetConfigSchema,
            DeskSurfaceConfigSchema,
        )

        config = DeskSurfaceConfigSchema(
            grommets=[
                DeskGrommetConfigSchema(x_position=24.0, y_position=21.0),
                DeskGrommetConfigSchema(x_position=48.0, y_position=21.0, diameter=3.0),
            ]
        )
        assert len(config.grommets) == 2
        assert config.grommets[0].x_position == 24.0
        assert config.grommets[1].diameter == 3.0

    def test_exposed_edges(self) -> None:
        """Exposed edge flags should be configurable."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        config = DeskSurfaceConfigSchema(exposed_left=True, exposed_right=True)
        assert config.exposed_left is True
        assert config.exposed_right is True

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import DeskSurfaceConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSurfaceConfigSchema(color="walnut")  # type: ignore
        assert "color" in str(exc_info.value)


class TestDeskPedestalConfigSchema:
    """Tests for DeskPedestalConfigSchema model."""

    def test_defaults(self) -> None:
        """DeskPedestalConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import (
            DeskPedestalConfigSchema,
            PedestalTypeConfig,
        )

        config = DeskPedestalConfigSchema()
        assert config.pedestal_type == PedestalTypeConfig.STORAGE
        assert config.width == 18.0
        assert config.position == "left"
        assert config.drawer_count == 3
        assert config.file_type == "letter"
        assert config.wire_chase is False

    def test_pedestal_type_values(self) -> None:
        """All pedestal type values should be accepted."""
        from cabinets.application.config.schema import (
            DeskPedestalConfigSchema,
            PedestalTypeConfig,
        )

        for pedestal_type in PedestalTypeConfig:
            config = DeskPedestalConfigSchema(pedestal_type=pedestal_type)
            assert config.pedestal_type == pedestal_type

    def test_width_range(self) -> None:
        """width should accept values within range."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        # At minimum
        config = DeskPedestalConfigSchema(width=12.0)
        assert config.width == 12.0

        # At maximum
        config = DeskPedestalConfigSchema(width=30.0)
        assert config.width == 30.0

    def test_width_below_minimum_raises_error(self) -> None:
        """width below minimum should raise error."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskPedestalConfigSchema(width=11.0)
        assert "greater than or equal to 12" in str(exc_info.value)

    def test_position_values(self) -> None:
        """Position should accept left and right."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        config = DeskPedestalConfigSchema(position="left")
        assert config.position == "left"

        config = DeskPedestalConfigSchema(position="right")
        assert config.position == "right"

    def test_drawer_count_range(self) -> None:
        """drawer_count should accept values within range."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        # At minimum
        config = DeskPedestalConfigSchema(drawer_count=1)
        assert config.drawer_count == 1

        # At maximum
        config = DeskPedestalConfigSchema(drawer_count=6)
        assert config.drawer_count == 6

    def test_drawer_count_below_minimum_raises_error(self) -> None:
        """drawer_count below minimum should raise error."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskPedestalConfigSchema(drawer_count=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_file_type_values(self) -> None:
        """file_type should accept letter and legal."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        config = DeskPedestalConfigSchema(file_type="letter")
        assert config.file_type == "letter"

        config = DeskPedestalConfigSchema(file_type="legal")
        assert config.file_type == "legal"

    def test_wire_chase_enabled(self) -> None:
        """wire_chase flag should be configurable."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        config = DeskPedestalConfigSchema(wire_chase=True)
        assert config.wire_chase is True

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import DeskPedestalConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskPedestalConfigSchema(color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestKeyboardTrayConfigSchema:
    """Tests for KeyboardTrayConfigSchema model."""

    def test_defaults(self) -> None:
        """KeyboardTrayConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        config = KeyboardTrayConfigSchema()
        assert config.width == 20.0
        assert config.depth == 10.0
        assert config.slide_length == 14
        assert config.enclosed is False
        assert config.wrist_rest is False

    def test_width_range(self) -> None:
        """width should accept values within range."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        # At minimum
        config = KeyboardTrayConfigSchema(width=15.0)
        assert config.width == 15.0

        # At maximum
        config = KeyboardTrayConfigSchema(width=30.0)
        assert config.width == 30.0

    def test_width_below_minimum_raises_error(self) -> None:
        """width below minimum should raise error."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            KeyboardTrayConfigSchema(width=14.0)
        assert "greater than or equal to 15" in str(exc_info.value)

    def test_depth_range(self) -> None:
        """depth should accept values within range."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        # At minimum
        config = KeyboardTrayConfigSchema(depth=8.0)
        assert config.depth == 8.0

        # At maximum
        config = KeyboardTrayConfigSchema(depth=14.0)
        assert config.depth == 14.0

    def test_slide_length_range(self) -> None:
        """slide_length should accept values within range."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        # At minimum
        config = KeyboardTrayConfigSchema(slide_length=10)
        assert config.slide_length == 10

        # At maximum
        config = KeyboardTrayConfigSchema(slide_length=20)
        assert config.slide_length == 20

    def test_slide_length_below_minimum_raises_error(self) -> None:
        """slide_length below minimum should raise error."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            KeyboardTrayConfigSchema(slide_length=9)
        assert "greater than or equal to 10" in str(exc_info.value)

    def test_enclosed_and_wrist_rest(self) -> None:
        """enclosed and wrist_rest flags should be configurable."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        config = KeyboardTrayConfigSchema(enclosed=True, wrist_rest=True)
        assert config.enclosed is True
        assert config.wrist_rest is True

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import KeyboardTrayConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            KeyboardTrayConfigSchema(color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestHutchConfigSchema:
    """Tests for HutchConfigSchema model."""

    def test_defaults(self) -> None:
        """HutchConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import HutchConfigSchema

        config = HutchConfigSchema()
        assert config.height == 24.0
        assert config.depth == 12.0
        assert config.head_clearance == 15.0
        assert config.shelf_count == 1
        assert config.doors is False
        assert config.task_light_zone is True

    def test_height_range(self) -> None:
        """height should accept values within range."""
        from cabinets.application.config.schema import HutchConfigSchema

        # At minimum
        config = HutchConfigSchema(height=12.0)
        assert config.height == 12.0

        # At maximum
        config = HutchConfigSchema(height=48.0)
        assert config.height == 48.0

    def test_height_below_minimum_raises_error(self) -> None:
        """height below minimum should raise error."""
        from cabinets.application.config.schema import HutchConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            HutchConfigSchema(height=11.0)
        assert "greater than or equal to 12" in str(exc_info.value)

    def test_depth_range(self) -> None:
        """depth should accept values within range."""
        from cabinets.application.config.schema import HutchConfigSchema

        # At minimum
        config = HutchConfigSchema(depth=6.0)
        assert config.depth == 6.0

        # At maximum
        config = HutchConfigSchema(depth=16.0)
        assert config.depth == 16.0

    def test_head_clearance_range(self) -> None:
        """head_clearance should accept values within range."""
        from cabinets.application.config.schema import HutchConfigSchema

        # At minimum
        config = HutchConfigSchema(head_clearance=12.0)
        assert config.head_clearance == 12.0

        # At maximum
        config = HutchConfigSchema(head_clearance=24.0)
        assert config.head_clearance == 24.0

    def test_shelf_count_range(self) -> None:
        """shelf_count should accept values within range."""
        from cabinets.application.config.schema import HutchConfigSchema

        # At minimum
        config = HutchConfigSchema(shelf_count=0)
        assert config.shelf_count == 0

        # At maximum
        config = HutchConfigSchema(shelf_count=4)
        assert config.shelf_count == 4

    def test_shelf_count_above_maximum_raises_error(self) -> None:
        """shelf_count above maximum should raise error."""
        from cabinets.application.config.schema import HutchConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            HutchConfigSchema(shelf_count=5)
        assert "less than or equal to 4" in str(exc_info.value)

    def test_doors_and_task_light_zone(self) -> None:
        """doors and task_light_zone flags should be configurable."""
        from cabinets.application.config.schema import HutchConfigSchema

        config = HutchConfigSchema(doors=True, task_light_zone=False)
        assert config.doors is True
        assert config.task_light_zone is False

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import HutchConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            HutchConfigSchema(color="white")  # type: ignore
        assert "color" in str(exc_info.value)


class TestMonitorShelfConfigSchema:
    """Tests for MonitorShelfConfigSchema model."""

    def test_defaults(self) -> None:
        """MonitorShelfConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        config = MonitorShelfConfigSchema()
        assert config.width == 24.0
        assert config.height == 6.0
        assert config.depth == 10.0
        assert config.cable_pass is True
        assert config.arm_mount is False

    def test_width_range(self) -> None:
        """width should accept values within range."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        # At minimum
        config = MonitorShelfConfigSchema(width=12.0)
        assert config.width == 12.0

        # At maximum
        config = MonitorShelfConfigSchema(width=60.0)
        assert config.width == 60.0

    def test_width_below_minimum_raises_error(self) -> None:
        """width below minimum should raise error."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            MonitorShelfConfigSchema(width=11.0)
        assert "greater than or equal to 12" in str(exc_info.value)

    def test_height_range(self) -> None:
        """height should accept values within range."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        # At minimum
        config = MonitorShelfConfigSchema(height=4.0)
        assert config.height == 4.0

        # At maximum
        config = MonitorShelfConfigSchema(height=12.0)
        assert config.height == 12.0

    def test_depth_range(self) -> None:
        """depth should accept values within range."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        # At minimum
        config = MonitorShelfConfigSchema(depth=6.0)
        assert config.depth == 6.0

        # At maximum
        config = MonitorShelfConfigSchema(depth=14.0)
        assert config.depth == 14.0

    def test_cable_pass_and_arm_mount(self) -> None:
        """cable_pass and arm_mount flags should be configurable."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        config = MonitorShelfConfigSchema(cable_pass=False, arm_mount=True)
        assert config.cable_pass is False
        assert config.arm_mount is True

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import MonitorShelfConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            MonitorShelfConfigSchema(color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestDeskSectionConfigSchema:
    """Tests for DeskSectionConfigSchema model."""

    def test_defaults(self) -> None:
        """DeskSectionConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            DeskTypeConfig,
        )

        config = DeskSectionConfigSchema()
        assert config.desk_type == DeskTypeConfig.SINGLE
        assert config.surface is not None
        assert config.pedestals == []
        assert config.keyboard_tray is None
        assert config.hutch is None
        assert config.monitor_shelf is None
        assert config.knee_clearance_width == 24.0
        assert config.modesty_panel is True

    def test_desk_type_values(self) -> None:
        """All desk type values should be accepted."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            DeskTypeConfig,
        )

        for desk_type in DeskTypeConfig:
            if desk_type != DeskTypeConfig.STANDING:
                config = DeskSectionConfigSchema(desk_type=desk_type)
                assert config.desk_type == desk_type

    def test_knee_clearance_width_minimum(self) -> None:
        """knee_clearance_width should accept values at or above minimum."""
        from cabinets.application.config.schema import DeskSectionConfigSchema

        # At minimum
        config = DeskSectionConfigSchema(knee_clearance_width=20.0)
        assert config.knee_clearance_width == 20.0

        # Above minimum
        config = DeskSectionConfigSchema(knee_clearance_width=30.0)
        assert config.knee_clearance_width == 30.0

    def test_knee_clearance_width_below_minimum_raises_error(self) -> None:
        """knee_clearance_width below minimum should raise error."""
        from cabinets.application.config.schema import DeskSectionConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSectionConfigSchema(knee_clearance_width=19.0)
        assert "greater than or equal to 20" in str(exc_info.value)

    def test_with_pedestals(self) -> None:
        """Desk with pedestals should be accepted."""
        from cabinets.application.config.schema import (
            DeskPedestalConfigSchema,
            DeskSectionConfigSchema,
        )

        config = DeskSectionConfigSchema(
            pedestals=[
                DeskPedestalConfigSchema(position="left"),
                DeskPedestalConfigSchema(position="right", width=20.0),
            ]
        )
        assert len(config.pedestals) == 2
        assert config.pedestals[0].position == "left"
        assert config.pedestals[1].width == 20.0

    def test_with_keyboard_tray(self) -> None:
        """Desk with keyboard tray should be accepted."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            KeyboardTrayConfigSchema,
        )

        config = DeskSectionConfigSchema(
            keyboard_tray=KeyboardTrayConfigSchema(width=22.0, enclosed=True)
        )
        assert config.keyboard_tray is not None
        assert config.keyboard_tray.width == 22.0
        assert config.keyboard_tray.enclosed is True

    def test_with_hutch(self) -> None:
        """Desk with hutch should be accepted."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            HutchConfigSchema,
        )

        config = DeskSectionConfigSchema(
            hutch=HutchConfigSchema(height=30.0, doors=True)
        )
        assert config.hutch is not None
        assert config.hutch.height == 30.0
        assert config.hutch.doors is True

    def test_with_monitor_shelf(self) -> None:
        """Desk with monitor shelf should be accepted."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            MonitorShelfConfigSchema,
        )

        config = DeskSectionConfigSchema(
            monitor_shelf=MonitorShelfConfigSchema(width=36.0, arm_mount=True)
        )
        assert config.monitor_shelf is not None
        assert config.monitor_shelf.width == 36.0
        assert config.monitor_shelf.arm_mount is True

    def test_standing_desk_requires_minimum_height(self) -> None:
        """Standing desk with height below 38\" should raise error."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            DeskSurfaceConfigSchema,
            DeskTypeConfig,
        )

        # Default height of 30.0 is too low for standing desk
        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSectionConfigSchema(
                desk_type=DeskTypeConfig.STANDING,
                surface=DeskSurfaceConfigSchema(desk_height=30.0),
            )
        error_str = str(exc_info.value)
        assert "at least 38" in error_str

    def test_standing_desk_valid_height(self) -> None:
        """Standing desk with height at or above 38\" should be accepted."""
        from cabinets.application.config.schema import (
            DeskSectionConfigSchema,
            DeskSurfaceConfigSchema,
            DeskTypeConfig,
        )

        # At minimum for standing desk
        config = DeskSectionConfigSchema(
            desk_type=DeskTypeConfig.STANDING,
            surface=DeskSurfaceConfigSchema(desk_height=38.0),
        )
        assert config.desk_type == DeskTypeConfig.STANDING
        assert config.surface.desk_height == 38.0

        # Above minimum
        config = DeskSectionConfigSchema(
            desk_type=DeskTypeConfig.STANDING,
            surface=DeskSurfaceConfigSchema(desk_height=42.0),
        )
        assert config.surface.desk_height == 42.0

    def test_modesty_panel_configurable(self) -> None:
        """modesty_panel flag should be configurable."""
        from cabinets.application.config.schema import DeskSectionConfigSchema

        config = DeskSectionConfigSchema(modesty_panel=False)
        assert config.modesty_panel is False

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        from cabinets.application.config.schema import DeskSectionConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            DeskSectionConfigSchema(color="walnut")  # type: ignore
        assert "color" in str(exc_info.value)

    def test_full_desk_configuration(self) -> None:
        """Full desk configuration with all components should be accepted."""
        from cabinets.application.config.schema import (
            DeskGrommetConfigSchema,
            DeskPedestalConfigSchema,
            DeskSectionConfigSchema,
            DeskSurfaceConfigSchema,
            DeskTypeConfig,
            EdgeTreatmentConfig,
            HutchConfigSchema,
            KeyboardTrayConfigSchema,
            MonitorShelfConfigSchema,
        )

        config = DeskSectionConfigSchema(
            desk_type=DeskTypeConfig.SINGLE,
            surface=DeskSurfaceConfigSchema(
                desk_height=30.0,
                depth=24.0,
                thickness=1.0,
                edge_treatment=EdgeTreatmentConfig.BULLNOSE,
                grommets=[
                    DeskGrommetConfigSchema(x_position=24.0, y_position=21.0, diameter=2.5)
                ],
                exposed_left=True,
            ),
            pedestals=[
                DeskPedestalConfigSchema(position="left", width=18.0, drawer_count=3),
                DeskPedestalConfigSchema(position="right", width=18.0, wire_chase=True),
            ],
            keyboard_tray=KeyboardTrayConfigSchema(width=20.0, enclosed=True),
            hutch=HutchConfigSchema(height=24.0, shelf_count=2, doors=True),
            monitor_shelf=MonitorShelfConfigSchema(width=36.0, cable_pass=True),
            knee_clearance_width=28.0,
            modesty_panel=True,
        )

        assert config.desk_type == DeskTypeConfig.SINGLE
        assert config.surface.edge_treatment == EdgeTreatmentConfig.BULLNOSE
        assert len(config.surface.grommets) == 1
        assert config.surface.exposed_left is True
        assert len(config.pedestals) == 2
        assert config.pedestals[1].wire_chase is True
        assert config.keyboard_tray is not None
        assert config.keyboard_tray.enclosed is True
        assert config.hutch is not None
        assert config.hutch.shelf_count == 2
        assert config.monitor_shelf is not None
        assert config.knee_clearance_width == 28.0


# =============================================================================
# Entertainment Center Configuration Tests (FRD-19)
# =============================================================================


class TestEquipmentTypeConfig:
    """Tests for EquipmentTypeConfig enum."""

    def test_equipment_type_values(self) -> None:
        """EquipmentTypeConfig should have all expected values."""
        from cabinets.application.config.schema import EquipmentTypeConfig

        assert EquipmentTypeConfig.RECEIVER.value == "receiver"
        assert EquipmentTypeConfig.CONSOLE_HORIZONTAL.value == "console_horizontal"
        assert EquipmentTypeConfig.CONSOLE_VERTICAL.value == "console_vertical"
        assert EquipmentTypeConfig.STREAMING.value == "streaming"
        assert EquipmentTypeConfig.CABLE_BOX.value == "cable_box"
        assert EquipmentTypeConfig.BLU_RAY.value == "blu_ray"
        assert EquipmentTypeConfig.TURNTABLE.value == "turntable"
        assert EquipmentTypeConfig.CUSTOM.value == "custom"

    def test_equipment_type_count(self) -> None:
        """EquipmentTypeConfig should have exactly 8 values."""
        from cabinets.application.config.schema import EquipmentTypeConfig

        assert len(EquipmentTypeConfig) == 8


class TestMediaVentilationTypeConfig:
    """Tests for MediaVentilationTypeConfig enum."""

    def test_media_ventilation_type_values(self) -> None:
        """MediaVentilationTypeConfig should have all expected values."""
        from cabinets.application.config.schema import MediaVentilationTypeConfig

        assert MediaVentilationTypeConfig.PASSIVE_REAR.value == "passive_rear"
        assert MediaVentilationTypeConfig.PASSIVE_BOTTOM.value == "passive_bottom"
        assert MediaVentilationTypeConfig.PASSIVE_SLOTS.value == "passive_slots"
        assert MediaVentilationTypeConfig.ACTIVE_FAN.value == "active_fan"
        assert MediaVentilationTypeConfig.NONE.value == "none"

    def test_media_ventilation_type_count(self) -> None:
        """MediaVentilationTypeConfig should have exactly 5 values."""
        from cabinets.application.config.schema import MediaVentilationTypeConfig

        assert len(MediaVentilationTypeConfig) == 5


class TestSoundbarTypeConfig:
    """Tests for SoundbarTypeConfig enum."""

    def test_soundbar_type_values(self) -> None:
        """SoundbarTypeConfig should have all expected values."""
        from cabinets.application.config.schema import SoundbarTypeConfig

        assert SoundbarTypeConfig.COMPACT.value == "compact"
        assert SoundbarTypeConfig.STANDARD.value == "standard"
        assert SoundbarTypeConfig.PREMIUM.value == "premium"
        assert SoundbarTypeConfig.CUSTOM.value == "custom"

    def test_soundbar_type_count(self) -> None:
        """SoundbarTypeConfig should have exactly 4 values."""
        from cabinets.application.config.schema import SoundbarTypeConfig

        assert len(SoundbarTypeConfig) == 4


class TestSpeakerTypeConfig:
    """Tests for SpeakerTypeConfig enum."""

    def test_speaker_type_values(self) -> None:
        """SpeakerTypeConfig should have all expected values."""
        from cabinets.application.config.schema import SpeakerTypeConfig

        assert SpeakerTypeConfig.CENTER_CHANNEL.value == "center_channel"
        assert SpeakerTypeConfig.BOOKSHELF.value == "bookshelf"
        assert SpeakerTypeConfig.SUBWOOFER.value == "subwoofer"

    def test_speaker_type_count(self) -> None:
        """SpeakerTypeConfig should have exactly 3 values."""
        from cabinets.application.config.schema import SpeakerTypeConfig

        assert len(SpeakerTypeConfig) == 3


class TestGrommetPositionConfig:
    """Tests for GrommetPositionConfig enum."""

    def test_grommet_position_values(self) -> None:
        """GrommetPositionConfig should have all expected values."""
        from cabinets.application.config.schema import GrommetPositionConfig

        assert GrommetPositionConfig.CENTER_REAR.value == "center_rear"
        assert GrommetPositionConfig.LEFT_REAR.value == "left_rear"
        assert GrommetPositionConfig.RIGHT_REAR.value == "right_rear"
        assert GrommetPositionConfig.NONE.value == "none"

    def test_grommet_position_count(self) -> None:
        """GrommetPositionConfig should have exactly 4 values."""
        from cabinets.application.config.schema import GrommetPositionConfig

        assert len(GrommetPositionConfig) == 4


class TestEntertainmentLayoutTypeConfig:
    """Tests for EntertainmentLayoutTypeConfig enum."""

    def test_entertainment_layout_type_values(self) -> None:
        """EntertainmentLayoutTypeConfig should have all expected values."""
        from cabinets.application.config.schema import EntertainmentLayoutTypeConfig

        assert EntertainmentLayoutTypeConfig.CONSOLE.value == "console"
        assert EntertainmentLayoutTypeConfig.WALL_UNIT.value == "wall_unit"
        assert EntertainmentLayoutTypeConfig.FLOATING.value == "floating"
        assert EntertainmentLayoutTypeConfig.TOWER.value == "tower"

    def test_entertainment_layout_type_count(self) -> None:
        """EntertainmentLayoutTypeConfig should have exactly 4 values."""
        from cabinets.application.config.schema import EntertainmentLayoutTypeConfig

        assert len(EntertainmentLayoutTypeConfig) == 4


class TestTVMountingConfig:
    """Tests for TVMountingConfig enum."""

    def test_tv_mounting_values(self) -> None:
        """TVMountingConfig should have all expected values."""
        from cabinets.application.config.schema import TVMountingConfig

        assert TVMountingConfig.WALL.value == "wall"
        assert TVMountingConfig.STAND.value == "stand"

    def test_tv_mounting_count(self) -> None:
        """TVMountingConfig should have exactly 2 values."""
        from cabinets.application.config.schema import TVMountingConfig

        assert len(TVMountingConfig) == 2


class TestEquipmentConfigSchema:
    """Tests for EquipmentConfigSchema model."""

    def test_defaults(self) -> None:
        """EquipmentConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import (
            EquipmentConfigSchema,
            EquipmentTypeConfig,
            GrommetPositionConfig,
        )

        config = EquipmentConfigSchema()
        assert config.equipment_type == EquipmentTypeConfig.RECEIVER
        assert config.custom_dimensions is None
        assert config.depth is None
        assert config.vertical_clearance is None
        assert config.grommet_position == GrommetPositionConfig.CENTER_REAR
        assert config.grommet_diameter == 2.5

    def test_grommet_diameter_constraints(self) -> None:
        """EquipmentConfigSchema should enforce grommet diameter constraints."""
        from cabinets.application.config.schema import EquipmentConfigSchema

        # Valid values
        config = EquipmentConfigSchema(grommet_diameter=1.5)
        assert config.grommet_diameter == 1.5

        config = EquipmentConfigSchema(grommet_diameter=3.5)
        assert config.grommet_diameter == 3.5

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(grommet_diameter=1.0)
        assert "greater than or equal to 1.5" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(grommet_diameter=4.0)
        assert "less than or equal to 3.5" in str(exc_info.value)

    def test_depth_constraints(self) -> None:
        """EquipmentConfigSchema should enforce depth constraints."""
        from cabinets.application.config.schema import EquipmentConfigSchema

        # Valid values
        config = EquipmentConfigSchema(depth=12.0)
        assert config.depth == 12.0

        config = EquipmentConfigSchema(depth=30.0)
        assert config.depth == 30.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(depth=10.0)
        assert "greater than or equal to 12" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(depth=35.0)
        assert "less than or equal to 30" in str(exc_info.value)

    def test_vertical_clearance_constraints(self) -> None:
        """EquipmentConfigSchema should enforce vertical clearance constraints."""
        from cabinets.application.config.schema import EquipmentConfigSchema

        # Valid values
        config = EquipmentConfigSchema(vertical_clearance=4.0)
        assert config.vertical_clearance == 4.0

        config = EquipmentConfigSchema(vertical_clearance=24.0)
        assert config.vertical_clearance == 24.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(vertical_clearance=2.0)
        assert "greater than or equal to 4" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(vertical_clearance=30.0)
        assert "less than or equal to 24" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """EquipmentConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import EquipmentConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            EquipmentConfigSchema(color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestMediaVentilationConfigSchema:
    """Tests for MediaVentilationConfigSchema model."""

    def test_defaults(self) -> None:
        """MediaVentilationConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import (
            MediaVentilationConfigSchema,
            MediaVentilationTypeConfig,
            VentilationPatternConfig,
        )

        config = MediaVentilationConfigSchema()
        assert config.ventilation_type == MediaVentilationTypeConfig.PASSIVE_REAR
        assert config.vent_pattern == VentilationPatternConfig.GRID
        assert config.open_area_percent == 30.0
        assert config.fan_size_mm == 120
        assert config.has_equipment is True
        assert config.enclosed is True

    def test_open_area_percent_constraints(self) -> None:
        """MediaVentilationConfigSchema should enforce open area percentage constraints."""
        from cabinets.application.config.schema import MediaVentilationConfigSchema

        # Valid values
        config = MediaVentilationConfigSchema(open_area_percent=10.0)
        assert config.open_area_percent == 10.0

        config = MediaVentilationConfigSchema(open_area_percent=80.0)
        assert config.open_area_percent == 80.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaVentilationConfigSchema(open_area_percent=5.0)
        assert "greater than or equal to 10" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaVentilationConfigSchema(open_area_percent=90.0)
        assert "less than or equal to 80" in str(exc_info.value)

    def test_fan_size_mm_constraints(self) -> None:
        """MediaVentilationConfigSchema should enforce fan size constraints."""
        from cabinets.application.config.schema import MediaVentilationConfigSchema

        # Valid values
        config = MediaVentilationConfigSchema(fan_size_mm=80)
        assert config.fan_size_mm == 80

        config = MediaVentilationConfigSchema(fan_size_mm=140)
        assert config.fan_size_mm == 140

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaVentilationConfigSchema(fan_size_mm=60)
        assert "greater than or equal to 80" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaVentilationConfigSchema(fan_size_mm=160)
        assert "less than or equal to 140" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """MediaVentilationConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import MediaVentilationConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            MediaVentilationConfigSchema(filter_type="hepa")  # type: ignore
        assert "filter_type" in str(exc_info.value)


class TestSoundbarConfigSchema:
    """Tests for SoundbarConfigSchema model."""

    def test_defaults(self) -> None:
        """SoundbarConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import SoundbarConfigSchema, SoundbarTypeConfig

        config = SoundbarConfigSchema()
        assert config.soundbar_type == SoundbarTypeConfig.STANDARD
        assert config.soundbar_width == 36.0
        assert config.soundbar_height == 3.0
        assert config.soundbar_depth == 4.0
        assert config.dolby_atmos is False
        assert config.side_clearance == 12.0
        assert config.ceiling_clearance == 36.0
        assert config.include_mount is False

    def test_soundbar_width_constraints(self) -> None:
        """SoundbarConfigSchema should enforce width constraints."""
        from cabinets.application.config.schema import SoundbarConfigSchema

        # Valid values
        config = SoundbarConfigSchema(soundbar_width=18.0)
        assert config.soundbar_width == 18.0

        config = SoundbarConfigSchema(soundbar_width=72.0)
        assert config.soundbar_width == 72.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(soundbar_width=12.0)
        assert "greater than or equal to 18" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(soundbar_width=80.0)
        assert "less than or equal to 72" in str(exc_info.value)

    def test_soundbar_height_constraints(self) -> None:
        """SoundbarConfigSchema should enforce height constraints."""
        from cabinets.application.config.schema import SoundbarConfigSchema

        # Valid values
        config = SoundbarConfigSchema(soundbar_height=2.0)
        assert config.soundbar_height == 2.0

        config = SoundbarConfigSchema(soundbar_height=6.0)
        assert config.soundbar_height == 6.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(soundbar_height=1.5)
        assert "greater than or equal to 2" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(soundbar_height=8.0)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_soundbar_depth_constraints(self) -> None:
        """SoundbarConfigSchema should enforce depth constraints."""
        from cabinets.application.config.schema import SoundbarConfigSchema

        # Valid values
        config = SoundbarConfigSchema(soundbar_depth=2.0)
        assert config.soundbar_depth == 2.0

        config = SoundbarConfigSchema(soundbar_depth=8.0)
        assert config.soundbar_depth == 8.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(soundbar_depth=1.0)
        assert "greater than or equal to 2" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(soundbar_depth=10.0)
        assert "less than or equal to 8" in str(exc_info.value)

    def test_side_clearance_constraints(self) -> None:
        """SoundbarConfigSchema should enforce side clearance constraints."""
        from cabinets.application.config.schema import SoundbarConfigSchema

        # Zero is allowed
        config = SoundbarConfigSchema(side_clearance=0.0)
        assert config.side_clearance == 0.0

        config = SoundbarConfigSchema(side_clearance=24.0)
        assert config.side_clearance == 24.0

        # Negative not allowed
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(side_clearance=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(side_clearance=30.0)
        assert "less than or equal to 24" in str(exc_info.value)

    def test_ceiling_clearance_constraints(self) -> None:
        """SoundbarConfigSchema should enforce ceiling clearance constraints."""
        from cabinets.application.config.schema import SoundbarConfigSchema

        # Valid values
        config = SoundbarConfigSchema(ceiling_clearance=12.0)
        assert config.ceiling_clearance == 12.0

        config = SoundbarConfigSchema(ceiling_clearance=96.0)
        assert config.ceiling_clearance == 96.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(ceiling_clearance=8.0)
        assert "greater than or equal to 12" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(ceiling_clearance=100.0)
        assert "less than or equal to 96" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """SoundbarConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import SoundbarConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            SoundbarConfigSchema(brand="sonos")  # type: ignore
        assert "brand" in str(exc_info.value)


class TestSpeakerConfigSchema:
    """Tests for SpeakerConfigSchema model."""

    def test_defaults(self) -> None:
        """SpeakerConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import SpeakerConfigSchema, SpeakerTypeConfig

        config = SpeakerConfigSchema()
        assert config.speaker_type == SpeakerTypeConfig.CENTER_CHANNEL
        assert config.speaker_width == 24.0
        assert config.speaker_height == 8.0
        assert config.speaker_depth == 12.0
        assert config.alcove_height_from_floor == 36.0
        assert config.port_clearance == 4.0
        assert config.include_dampening is True
        assert config.include_top is True

    def test_speaker_width_constraints(self) -> None:
        """SpeakerConfigSchema should enforce width constraints."""
        from cabinets.application.config.schema import SpeakerConfigSchema

        # Valid values
        config = SpeakerConfigSchema(speaker_width=4.0)
        assert config.speaker_width == 4.0

        config = SpeakerConfigSchema(speaker_width=36.0)
        assert config.speaker_width == 36.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(speaker_width=2.0)
        assert "greater than or equal to 4" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(speaker_width=40.0)
        assert "less than or equal to 36" in str(exc_info.value)

    def test_alcove_height_from_floor_constraints(self) -> None:
        """SpeakerConfigSchema should enforce alcove height constraints."""
        from cabinets.application.config.schema import SpeakerConfigSchema

        # Valid values
        config = SpeakerConfigSchema(alcove_height_from_floor=6.0)
        assert config.alcove_height_from_floor == 6.0

        config = SpeakerConfigSchema(alcove_height_from_floor=72.0)
        assert config.alcove_height_from_floor == 72.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(alcove_height_from_floor=4.0)
        assert "greater than or equal to 6" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(alcove_height_from_floor=80.0)
        assert "less than or equal to 72" in str(exc_info.value)

    def test_port_clearance_constraints(self) -> None:
        """SpeakerConfigSchema should enforce port clearance constraints."""
        from cabinets.application.config.schema import SpeakerConfigSchema

        # Valid values
        config = SpeakerConfigSchema(port_clearance=2.0)
        assert config.port_clearance == 2.0

        config = SpeakerConfigSchema(port_clearance=12.0)
        assert config.port_clearance == 12.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(port_clearance=1.0)
        assert "greater than or equal to 2" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(port_clearance=15.0)
        assert "less than or equal to 12" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """SpeakerConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import SpeakerConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            SpeakerConfigSchema(brand="klipsch")  # type: ignore
        assert "brand" in str(exc_info.value)


class TestTVConfigSchema:
    """Tests for TVConfigSchema model."""

    def test_defaults(self) -> None:
        """TVConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import TVConfigSchema, TVMountingConfig

        config = TVConfigSchema()
        assert config.screen_size == 55
        assert config.mounting == TVMountingConfig.WALL
        assert config.center_height == 42.0
        assert config.cable_grommet is True

    def test_screen_size_literal_enforcement(self) -> None:
        """TVConfigSchema should only accept valid screen sizes."""
        from cabinets.application.config.schema import TVConfigSchema

        # Valid screen sizes
        for size in [50, 55, 65, 75, 85]:
            config = TVConfigSchema(screen_size=size)
            assert config.screen_size == size

        # Invalid screen size
        with pytest.raises(PydanticValidationError) as exc_info:
            TVConfigSchema(screen_size=60)  # type: ignore
        assert "screen_size" in str(exc_info.value)

    def test_center_height_constraints(self) -> None:
        """TVConfigSchema should enforce center height constraints."""
        from cabinets.application.config.schema import TVConfigSchema

        # Valid values
        config = TVConfigSchema(center_height=24.0)
        assert config.center_height == 24.0

        config = TVConfigSchema(center_height=72.0)
        assert config.center_height == 72.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            TVConfigSchema(center_height=20.0)
        assert "greater than or equal to 24" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            TVConfigSchema(center_height=80.0)
        assert "less than or equal to 72" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """TVConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import TVConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            TVConfigSchema(brand="samsung")  # type: ignore
        assert "brand" in str(exc_info.value)


class TestMediaStorageConfigSchema:
    """Tests for MediaStorageConfigSchema model."""

    def test_defaults(self) -> None:
        """MediaStorageConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import MediaStorageConfigSchema

        config = MediaStorageConfigSchema()
        assert config.storage_type == "mixed"
        assert config.drawer_count == 2
        assert config.include_dividers is True

    def test_storage_type_literal_enforcement(self) -> None:
        """MediaStorageConfigSchema should only accept valid storage types."""
        from cabinets.application.config.schema import MediaStorageConfigSchema

        # Valid storage types
        for stype in ["dvd_drawer", "game_cubbies", "controller_drawer", "mixed"]:
            config = MediaStorageConfigSchema(storage_type=stype)  # type: ignore
            assert config.storage_type == stype

        # Invalid storage type
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaStorageConfigSchema(storage_type="invalid")  # type: ignore
        assert "storage_type" in str(exc_info.value)

    def test_drawer_count_constraints(self) -> None:
        """MediaStorageConfigSchema should enforce drawer count constraints."""
        from cabinets.application.config.schema import MediaStorageConfigSchema

        # Valid values
        config = MediaStorageConfigSchema(drawer_count=1)
        assert config.drawer_count == 1

        config = MediaStorageConfigSchema(drawer_count=6)
        assert config.drawer_count == 6

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaStorageConfigSchema(drawer_count=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaStorageConfigSchema(drawer_count=8)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """MediaStorageConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import MediaStorageConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            MediaStorageConfigSchema(material="oak")  # type: ignore
        assert "material" in str(exc_info.value)


class TestMediaCableManagementConfigSchema:
    """Tests for MediaCableManagementConfigSchema model."""

    def test_defaults(self) -> None:
        """MediaCableManagementConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import MediaCableManagementConfigSchema

        config = MediaCableManagementConfigSchema()
        assert config.vertical_chase is False
        assert config.chase_width == 3.0
        assert config.grommets_per_shelf == 1
        assert config.grommet_diameter == 2.5

    def test_chase_width_constraints(self) -> None:
        """MediaCableManagementConfigSchema should enforce chase width constraints."""
        from cabinets.application.config.schema import MediaCableManagementConfigSchema

        # Valid values
        config = MediaCableManagementConfigSchema(chase_width=2.0)
        assert config.chase_width == 2.0

        config = MediaCableManagementConfigSchema(chase_width=6.0)
        assert config.chase_width == 6.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(chase_width=1.5)
        assert "greater than or equal to 2" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(chase_width=8.0)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_grommets_per_shelf_constraints(self) -> None:
        """MediaCableManagementConfigSchema should enforce grommets per shelf constraints."""
        from cabinets.application.config.schema import MediaCableManagementConfigSchema

        # Valid values
        config = MediaCableManagementConfigSchema(grommets_per_shelf=0)
        assert config.grommets_per_shelf == 0

        config = MediaCableManagementConfigSchema(grommets_per_shelf=3)
        assert config.grommets_per_shelf == 3

        # Negative not allowed
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(grommets_per_shelf=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(grommets_per_shelf=5)
        assert "less than or equal to 3" in str(exc_info.value)

    def test_grommet_diameter_constraints(self) -> None:
        """MediaCableManagementConfigSchema should enforce grommet diameter constraints."""
        from cabinets.application.config.schema import MediaCableManagementConfigSchema

        # Valid values
        config = MediaCableManagementConfigSchema(grommet_diameter=1.5)
        assert config.grommet_diameter == 1.5

        config = MediaCableManagementConfigSchema(grommet_diameter=3.5)
        assert config.grommet_diameter == 3.5

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(grommet_diameter=1.0)
        assert "greater than or equal to 1.5" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(grommet_diameter=4.0)
        assert "less than or equal to 3.5" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """MediaCableManagementConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import MediaCableManagementConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            MediaCableManagementConfigSchema(cable_type="hdmi")  # type: ignore
        assert "cable_type" in str(exc_info.value)


class TestMediaSectionConfigSchema:
    """Tests for MediaSectionConfigSchema model."""

    def test_defaults(self) -> None:
        """MediaSectionConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import MediaSectionConfigSchema

        config = MediaSectionConfigSchema()
        assert config.section_type == "equipment"
        assert config.equipment is None
        assert config.ventilation is None
        assert config.soundbar is None
        assert config.speaker is None
        assert config.storage is None

    def test_section_type_literal_enforcement(self) -> None:
        """MediaSectionConfigSchema should only accept valid section types."""
        from cabinets.application.config.schema import MediaSectionConfigSchema

        # Valid section types
        for stype in ["equipment", "soundbar", "speaker", "storage", "ventilated"]:
            config = MediaSectionConfigSchema(section_type=stype)  # type: ignore
            assert config.section_type == stype

        # Invalid section type
        with pytest.raises(PydanticValidationError) as exc_info:
            MediaSectionConfigSchema(section_type="invalid")  # type: ignore
        assert "section_type" in str(exc_info.value)

    def test_with_equipment_config(self) -> None:
        """MediaSectionConfigSchema should accept equipment configuration."""
        from cabinets.application.config.schema import (
            EquipmentConfigSchema,
            EquipmentTypeConfig,
            MediaSectionConfigSchema,
        )

        config = MediaSectionConfigSchema(
            section_type="equipment",
            equipment=EquipmentConfigSchema(
                equipment_type=EquipmentTypeConfig.RECEIVER, grommet_diameter=2.0
            ),
        )
        assert config.section_type == "equipment"
        assert config.equipment is not None
        assert config.equipment.equipment_type == EquipmentTypeConfig.RECEIVER

    def test_with_ventilation_config(self) -> None:
        """MediaSectionConfigSchema should accept ventilation configuration."""
        from cabinets.application.config.schema import (
            MediaSectionConfigSchema,
            MediaVentilationConfigSchema,
            MediaVentilationTypeConfig,
        )

        config = MediaSectionConfigSchema(
            section_type="ventilated",
            ventilation=MediaVentilationConfigSchema(
                ventilation_type=MediaVentilationTypeConfig.ACTIVE_FAN, fan_size_mm=120
            ),
        )
        assert config.section_type == "ventilated"
        assert config.ventilation is not None
        assert config.ventilation.ventilation_type == MediaVentilationTypeConfig.ACTIVE_FAN

    def test_with_soundbar_config(self) -> None:
        """MediaSectionConfigSchema should accept soundbar configuration."""
        from cabinets.application.config.schema import (
            MediaSectionConfigSchema,
            SoundbarConfigSchema,
            SoundbarTypeConfig,
        )

        config = MediaSectionConfigSchema(
            section_type="soundbar",
            soundbar=SoundbarConfigSchema(
                soundbar_type=SoundbarTypeConfig.PREMIUM, dolby_atmos=True
            ),
        )
        assert config.section_type == "soundbar"
        assert config.soundbar is not None
        assert config.soundbar.soundbar_type == SoundbarTypeConfig.PREMIUM
        assert config.soundbar.dolby_atmos is True

    def test_with_speaker_config(self) -> None:
        """MediaSectionConfigSchema should accept speaker configuration."""
        from cabinets.application.config.schema import (
            MediaSectionConfigSchema,
            SpeakerConfigSchema,
            SpeakerTypeConfig,
        )

        config = MediaSectionConfigSchema(
            section_type="speaker",
            speaker=SpeakerConfigSchema(
                speaker_type=SpeakerTypeConfig.SUBWOOFER, port_clearance=6.0
            ),
        )
        assert config.section_type == "speaker"
        assert config.speaker is not None
        assert config.speaker.speaker_type == SpeakerTypeConfig.SUBWOOFER

    def test_with_storage_config(self) -> None:
        """MediaSectionConfigSchema should accept storage configuration."""
        from cabinets.application.config.schema import MediaSectionConfigSchema, MediaStorageConfigSchema

        config = MediaSectionConfigSchema(
            section_type="storage",
            storage=MediaStorageConfigSchema(storage_type="game_cubbies", drawer_count=4),
        )
        assert config.section_type == "storage"
        assert config.storage is not None
        assert config.storage.storage_type == "game_cubbies"

    def test_rejects_unknown_fields(self) -> None:
        """MediaSectionConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import MediaSectionConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            MediaSectionConfigSchema(color="black")  # type: ignore
        assert "color" in str(exc_info.value)


class TestEntertainmentCenterConfigSchema:
    """Tests for EntertainmentCenterConfigSchema model."""

    def test_defaults(self) -> None:
        """EntertainmentCenterConfigSchema should have sensible defaults."""
        from cabinets.application.config.schema import (
            EntertainmentCenterConfigSchema,
            EntertainmentLayoutTypeConfig,
            TVMountingConfig,
        )

        config = EntertainmentCenterConfigSchema()
        assert config.layout_type == EntertainmentLayoutTypeConfig.CONSOLE
        assert config.tv is not None
        assert config.tv.screen_size == 55
        assert config.tv.mounting == TVMountingConfig.WALL
        assert config.sections == []
        assert config.cable_management is not None
        assert config.flanking_storage is True
        assert config.flanking_width == 18.0

    def test_layout_type_enum_values(self) -> None:
        """EntertainmentCenterConfigSchema should accept all layout types."""
        from cabinets.application.config.schema import (
            EntertainmentCenterConfigSchema,
            EntertainmentLayoutTypeConfig,
        )

        for layout in EntertainmentLayoutTypeConfig:
            config = EntertainmentCenterConfigSchema(layout_type=layout)
            assert config.layout_type == layout

    def test_flanking_width_constraints(self) -> None:
        """EntertainmentCenterConfigSchema should enforce flanking width constraints."""
        from cabinets.application.config.schema import EntertainmentCenterConfigSchema

        # Valid values
        config = EntertainmentCenterConfigSchema(flanking_width=12.0)
        assert config.flanking_width == 12.0

        config = EntertainmentCenterConfigSchema(flanking_width=36.0)
        assert config.flanking_width == 36.0

        # Below minimum
        with pytest.raises(PydanticValidationError) as exc_info:
            EntertainmentCenterConfigSchema(flanking_width=10.0)
        assert "greater than or equal to 12" in str(exc_info.value)

        # Above maximum
        with pytest.raises(PydanticValidationError) as exc_info:
            EntertainmentCenterConfigSchema(flanking_width=40.0)
        assert "less than or equal to 36" in str(exc_info.value)

    def test_with_custom_tv(self) -> None:
        """EntertainmentCenterConfigSchema should accept custom TV configuration."""
        from cabinets.application.config.schema import (
            EntertainmentCenterConfigSchema,
            TVConfigSchema,
            TVMountingConfig,
        )

        config = EntertainmentCenterConfigSchema(
            tv=TVConfigSchema(screen_size=75, mounting=TVMountingConfig.STAND, center_height=48.0)
        )
        assert config.tv.screen_size == 75
        assert config.tv.mounting == TVMountingConfig.STAND
        assert config.tv.center_height == 48.0

    def test_with_media_sections(self) -> None:
        """EntertainmentCenterConfigSchema should accept media sections list."""
        from cabinets.application.config.schema import (
            EntertainmentCenterConfigSchema,
            EquipmentConfigSchema,
            EquipmentTypeConfig,
            MediaSectionConfigSchema,
            SoundbarConfigSchema,
        )

        config = EntertainmentCenterConfigSchema(
            sections=[
                MediaSectionConfigSchema(
                    section_type="soundbar", soundbar=SoundbarConfigSchema()
                ),
                MediaSectionConfigSchema(
                    section_type="equipment",
                    equipment=EquipmentConfigSchema(equipment_type=EquipmentTypeConfig.RECEIVER),
                ),
            ]
        )
        assert len(config.sections) == 2
        assert config.sections[0].section_type == "soundbar"
        assert config.sections[1].section_type == "equipment"

    def test_with_custom_cable_management(self) -> None:
        """EntertainmentCenterConfigSchema should accept custom cable management."""
        from cabinets.application.config.schema import (
            EntertainmentCenterConfigSchema,
            MediaCableManagementConfigSchema,
        )

        config = EntertainmentCenterConfigSchema(
            cable_management=MediaCableManagementConfigSchema(
                vertical_chase=True, chase_width=4.0, grommets_per_shelf=2
            )
        )
        assert config.cable_management.vertical_chase is True
        assert config.cable_management.chase_width == 4.0
        assert config.cable_management.grommets_per_shelf == 2

    def test_rejects_unknown_fields(self) -> None:
        """EntertainmentCenterConfigSchema should reject unknown fields."""
        from cabinets.application.config.schema import EntertainmentCenterConfigSchema

        with pytest.raises(PydanticValidationError) as exc_info:
            EntertainmentCenterConfigSchema(color="mahogany")  # type: ignore
        assert "color" in str(exc_info.value)

    def test_full_entertainment_center_configuration(self) -> None:
        """Full entertainment center configuration with all components should be accepted."""
        from cabinets.application.config.schema import (
            EntertainmentCenterConfigSchema,
            EntertainmentLayoutTypeConfig,
            EquipmentConfigSchema,
            EquipmentTypeConfig,
            MediaCableManagementConfigSchema,
            MediaSectionConfigSchema,
            MediaVentilationConfigSchema,
            MediaVentilationTypeConfig,
            SoundbarConfigSchema,
            SoundbarTypeConfig,
            SpeakerConfigSchema,
            SpeakerTypeConfig,
            TVConfigSchema,
            TVMountingConfig,
        )

        config = EntertainmentCenterConfigSchema(
            layout_type=EntertainmentLayoutTypeConfig.WALL_UNIT,
            tv=TVConfigSchema(
                screen_size=65, mounting=TVMountingConfig.WALL, center_height=48.0, cable_grommet=True
            ),
            sections=[
                MediaSectionConfigSchema(
                    section_type="soundbar",
                    soundbar=SoundbarConfigSchema(
                        soundbar_type=SoundbarTypeConfig.STANDARD,
                        dolby_atmos=True,
                        side_clearance=12.0,
                    ),
                ),
                MediaSectionConfigSchema(
                    section_type="equipment",
                    equipment=EquipmentConfigSchema(
                        equipment_type=EquipmentTypeConfig.RECEIVER,
                        grommet_diameter=2.5,
                    ),
                    ventilation=MediaVentilationConfigSchema(
                        ventilation_type=MediaVentilationTypeConfig.PASSIVE_REAR,
                        open_area_percent=30.0,
                    ),
                ),
                MediaSectionConfigSchema(
                    section_type="speaker",
                    speaker=SpeakerConfigSchema(
                        speaker_type=SpeakerTypeConfig.CENTER_CHANNEL,
                        alcove_height_from_floor=36.0,
                        include_dampening=True,
                    ),
                ),
            ],
            cable_management=MediaCableManagementConfigSchema(
                vertical_chase=True, chase_width=3.0, grommets_per_shelf=1
            ),
            flanking_storage=True,
            flanking_width=18.0,
        )

        assert config.layout_type == EntertainmentLayoutTypeConfig.WALL_UNIT
        assert config.tv.screen_size == 65
        assert config.tv.mounting == TVMountingConfig.WALL
        assert len(config.sections) == 3
        assert config.sections[0].soundbar is not None
        assert config.sections[0].soundbar.dolby_atmos is True
        assert config.sections[1].equipment is not None
        assert config.sections[1].ventilation is not None
        assert config.sections[2].speaker is not None
        assert config.cable_management.vertical_chase is True
        assert config.flanking_storage is True
