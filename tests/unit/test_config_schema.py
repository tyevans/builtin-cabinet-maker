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
    CabinetConfig,
    CabinetConfiguration,
    ClearanceConfig,
    ConfigError,
    HeightMode,
    MaterialConfig,
    ObstacleConfig,
    ObstacleDefaultsConfig,
    ObstacleTypeConfig,
    OutputConfig,
    RoomConfig,
    SectionConfig,
    ValidationResult,
    WallSegmentConfig,
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
        """Angle must be -90, 0, or 90 degrees."""
        for angle in [-90, 0, 90]:
            config = WallSegmentConfig(length=120.0, height=96.0, angle=angle)
            assert config.angle == angle

    def test_invalid_angles(self) -> None:
        """Invalid angles should be rejected."""
        for angle in [-180, -45, 45, 180, 30]:
            with pytest.raises(PydanticValidationError) as exc_info:
                WallSegmentConfig(length=120.0, height=96.0, angle=angle)
            assert "Angle must be -90, 0, or 90" in str(exc_info.value)

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
        for fmt in ["all", "cutlist", "diagram", "materials", "json", "stl"]:
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
