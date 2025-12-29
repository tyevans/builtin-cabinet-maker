"""Unit tests for configuration adapter functions.

These tests verify:
- config_to_room correctly converts RoomConfig to Room domain entity
- config_to_room returns None when no room is configured (backward compatibility)
- config_to_section_specs includes wall field from section config
- Adapter functions maintain consistency between config and domain models
"""

import pytest

from cabinets.application.config import (
    CabinetConfig,
    CabinetConfiguration,
    CeilingConfig,
    CeilingSlopeConfig,
    OutsideCornerConfigSchema,
    RoomConfig,
    SectionConfig,
    SectionTypeConfig,
    SkylightConfig,
    WallSegmentConfig,
    config_to_ceiling_slope,
    config_to_outside_corner,
    config_to_room,
    config_to_section_specs,
    config_to_skylights,
)
from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.value_objects import CeilingSlope, OutsideCornerConfig, SectionType, Skylight


class TestConfigToRoom:
    """Tests for config_to_room function."""

    def test_returns_none_when_no_room_configured(self) -> None:
        """config_to_room should return None when config has no room."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        result = config_to_room(config)
        assert result is None

    def test_converts_single_wall_room(self) -> None:
        """config_to_room should convert a room with a single wall."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room_config = RoomConfig(name="closet", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room_config,
        )

        result = config_to_room(config)

        assert result is not None
        assert isinstance(result, Room)
        assert result.name == "closet"
        assert len(result.walls) == 1
        assert result.walls[0].length == 120.0
        assert result.walls[0].height == 96.0
        assert result.walls[0].angle == 0.0
        assert result.walls[0].depth == 12.0
        assert result.is_closed is False

    def test_converts_multi_wall_room(self) -> None:
        """config_to_room should convert a room with multiple walls."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0, name="north")
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=90, name="east")
        wall3 = WallSegmentConfig(length=120.0, height=96.0, angle=90, name="south")
        room_config = RoomConfig(name="l_shaped", walls=[wall1, wall2, wall3])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room_config,
        )

        result = config_to_room(config)

        assert result is not None
        assert result.name == "l_shaped"
        assert len(result.walls) == 3
        assert result.walls[0].name == "north"
        assert result.walls[1].name == "east"
        assert result.walls[2].name == "south"
        assert result.walls[0].angle == 0
        assert result.walls[1].angle == 90
        assert result.walls[2].angle == 90

    def test_preserves_wall_properties(self) -> None:
        """config_to_room should preserve all wall properties."""
        wall = WallSegmentConfig(
            length=144.0,
            height=108.0,
            angle=0,
            name="main_wall",
            depth=14.0,
        )
        room_config = RoomConfig(name="study", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room_config,
        )

        result = config_to_room(config)

        assert result is not None
        wall_segment = result.walls[0]
        assert isinstance(wall_segment, WallSegment)
        assert wall_segment.length == 144.0
        assert wall_segment.height == 108.0
        assert wall_segment.angle == 0
        assert wall_segment.name == "main_wall"
        assert wall_segment.depth == 14.0

    def test_converts_closed_room(self) -> None:
        """config_to_room should preserve is_closed flag."""
        wall1 = WallSegmentConfig(length=100.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=100.0, height=96.0, angle=90)
        wall3 = WallSegmentConfig(length=100.0, height=96.0, angle=90)
        wall4 = WallSegmentConfig(length=100.0, height=96.0, angle=90)
        room_config = RoomConfig(
            name="square", walls=[wall1, wall2, wall3, wall4], is_closed=True
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room_config,
        )

        result = config_to_room(config)

        assert result is not None
        assert result.is_closed is True
        assert len(result.walls) == 4

    def test_room_entity_is_functional(self) -> None:
        """Converted Room entity should work with domain methods."""
        wall1 = WallSegmentConfig(length=100.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=50.0, height=96.0, angle=90)
        room_config = RoomConfig(name="test_room", walls=[wall1, wall2])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room_config,
        )

        result = config_to_room(config)

        assert result is not None
        # Verify domain methods work
        assert result.total_length == 150.0
        positions = result.get_wall_positions()
        assert len(positions) == 2
        # First wall at origin
        assert positions[0].start.x == 0.0
        assert positions[0].start.y == 0.0

    def test_backward_compatibility_v1_0(self) -> None:
        """v1.0 configs without room should work correctly."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0), SectionConfig(width="fill")],
            ),
        )

        result = config_to_room(config)

        assert result is None


class TestConfigToSectionSpecsWithWall:
    """Tests for wall field in config_to_section_specs."""

    def test_section_spec_includes_wall_none(self) -> None:
        """Section specs should have wall=None when not specified."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0, shelves=3)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].wall is None
        assert specs[0].width == 24.0
        assert specs[0].shelves == 3

    def test_section_spec_includes_wall_string(self) -> None:
        """Section specs should include wall name when specified."""
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=3, wall="north_wall"),
                    SectionConfig(width="fill", shelves=2, wall="east_wall"),
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 2
        assert specs[0].wall == "north_wall"
        assert specs[1].wall == "east_wall"

    def test_section_spec_includes_wall_index(self) -> None:
        """Section specs should include wall index when specified."""
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=3, wall=0),
                    SectionConfig(width=24.0, shelves=2, wall=1),
                    SectionConfig(width="fill", shelves=4, wall=2),
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 3
        assert specs[0].wall == 0
        assert specs[1].wall == 1
        assert specs[2].wall == 2

    def test_section_spec_mixed_wall_references(self) -> None:
        """Section specs should handle mixed wall references (names, indices, None)."""
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(
                width=96.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, wall="main_wall"),
                    SectionConfig(width=24.0, wall=1),
                    SectionConfig(width=24.0),  # wall=None
                    SectionConfig(width="fill", wall="side_wall"),
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 4
        assert specs[0].wall == "main_wall"
        assert specs[1].wall == 1
        assert specs[2].wall is None
        assert specs[3].wall == "side_wall"

    def test_default_section_has_no_wall(self) -> None:
        """Default section (when no sections specified) should have wall=None."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].wall is None
        assert specs[0].width == "fill"
        assert specs[0].shelves == 0

    def test_section_with_room_and_wall_reference(self) -> None:
        """Sections with wall references work alongside room configuration."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, name="north")
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=90, name="east")
        room_config = RoomConfig(name="corner", walls=[wall1, wall2])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=3, wall="north"),
                    SectionConfig(width="fill", shelves=2, wall="east"),
                ],
            ),
            room=room_config,
        )

        specs = config_to_section_specs(config)
        room = config_to_room(config)

        assert len(specs) == 2
        assert specs[0].wall == "north"
        assert specs[1].wall == "east"
        assert room is not None
        assert room.walls[0].name == "north"
        assert room.walls[1].name == "east"


class TestConfigToSectionSpecsFRD04:
    """Tests for config_to_section_specs conversion of FRD-04 fields."""

    def test_section_type_open_conversion(self) -> None:
        """config_to_section_specs should convert OPEN section type."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0, section_type=SectionTypeConfig.OPEN)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].section_type == SectionType.OPEN

    def test_section_type_doored_conversion(self) -> None:
        """config_to_section_specs should convert DOORED section type."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, section_type=SectionTypeConfig.DOORED)
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].section_type == SectionType.DOORED

    def test_section_type_drawers_conversion(self) -> None:
        """config_to_section_specs should convert DRAWERS section type."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, section_type=SectionTypeConfig.DRAWERS)
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].section_type == SectionType.DRAWERS

    def test_section_type_cubby_conversion(self) -> None:
        """config_to_section_specs should convert CUBBY section type."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=12.0, section_type=SectionTypeConfig.CUBBY)
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].section_type == SectionType.CUBBY

    def test_section_type_default_is_open(self) -> None:
        """config_to_section_specs should default section_type to OPEN."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].section_type == SectionType.OPEN

    def test_depth_override_conversion(self) -> None:
        """config_to_section_specs should convert depth override."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0, depth=10.0)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].depth == 10.0

    def test_depth_none_when_not_specified(self) -> None:
        """config_to_section_specs should have depth=None when not specified."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width=24.0)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].depth is None

    def test_min_width_conversion(self) -> None:
        """config_to_section_specs should convert min_width."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width="fill", min_width=12.0)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].min_width == 12.0

    def test_min_width_default_conversion(self) -> None:
        """config_to_section_specs should use default min_width (6.0)."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width="fill")],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].min_width == 6.0

    def test_max_width_conversion(self) -> None:
        """config_to_section_specs should convert max_width."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width="fill", max_width=36.0)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].max_width == 36.0

    def test_max_width_none_when_not_specified(self) -> None:
        """config_to_section_specs should have max_width=None when not specified."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width="fill")],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].max_width is None

    def test_min_and_max_width_together(self) -> None:
        """config_to_section_specs should convert both min_width and max_width."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[SectionConfig(width="fill", min_width=12.0, max_width=30.0)],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].min_width == 12.0
        assert specs[0].max_width == 30.0

    def test_all_frd04_fields_together(self) -> None:
        """config_to_section_specs should convert all FRD-04 fields together."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(
                        width=24.0,
                        shelves=3,
                        section_type=SectionTypeConfig.DOORED,
                        depth=10.0,
                        min_width=12.0,
                        max_width=36.0,
                    )
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].width == 24.0
        assert specs[0].shelves == 3
        assert specs[0].section_type == SectionType.DOORED
        assert specs[0].depth == 10.0
        assert specs[0].min_width == 12.0
        assert specs[0].max_width == 36.0

    def test_mixed_section_types(self) -> None:
        """config_to_section_specs should convert multiple sections with different types."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=96.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, section_type=SectionTypeConfig.OPEN),
                    SectionConfig(width=24.0, section_type=SectionTypeConfig.DRAWERS),
                    SectionConfig(width=24.0, section_type=SectionTypeConfig.DOORED),
                    SectionConfig(width="fill", section_type=SectionTypeConfig.CUBBY),
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 4
        assert specs[0].section_type == SectionType.OPEN
        assert specs[1].section_type == SectionType.DRAWERS
        assert specs[2].section_type == SectionType.DOORED
        assert specs[3].section_type == SectionType.CUBBY

    def test_sections_with_different_depths(self) -> None:
        """config_to_section_specs should convert sections with different depths."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, depth=10.0),
                    SectionConfig(width=24.0),  # Uses cabinet depth (None)
                    SectionConfig(width="fill", depth=8.0),
                ],
            ),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 3
        assert specs[0].depth == 10.0
        assert specs[1].depth is None
        assert specs[2].depth == 8.0

    def test_default_section_has_frd04_defaults(self) -> None:
        """Default section (when no sections specified) should have FRD-04 defaults."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        specs = config_to_section_specs(config)

        assert len(specs) == 1
        assert specs[0].width == "fill"
        assert specs[0].section_type == SectionType.OPEN
        assert specs[0].depth is None
        assert specs[0].min_width == 6.0
        assert specs[0].max_width is None


class TestConfigToCeilingSlope:
    """Tests for config_to_ceiling_slope function (FRD-11)."""

    def test_returns_none_when_no_room(self) -> None:
        """config_to_ceiling_slope should return None when no room configured."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        result = config_to_ceiling_slope(config)
        assert result is None

    def test_returns_none_when_no_ceiling(self) -> None:
        """config_to_ceiling_slope should return None when room has no ceiling."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="test", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        result = config_to_ceiling_slope(config)
        assert result is None

    def test_returns_none_when_ceiling_has_no_slope(self) -> None:
        """config_to_ceiling_slope should return None when ceiling has no slope."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig()  # No slope
        room = RoomConfig(name="test", walls=[wall], ceiling=ceiling)
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        result = config_to_ceiling_slope(config)
        assert result is None

    def test_converts_ceiling_slope(self) -> None:
        """config_to_ceiling_slope should convert slope to domain value object."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig(
            slope=CeilingSlopeConfig(
                angle=30.0,
                start_height=96.0,
                direction="left_to_right",
                min_height=24.0,
            )
        )
        room = RoomConfig(name="attic", walls=[wall], ceiling=ceiling)
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_ceiling_slope(config)

        assert result is not None
        assert isinstance(result, CeilingSlope)
        assert result.angle == 30.0
        assert result.start_height == 96.0
        assert result.direction == "left_to_right"
        assert result.min_height == 24.0

    def test_converts_all_directions(self) -> None:
        """config_to_ceiling_slope should correctly convert all direction values."""
        for direction in ["left_to_right", "right_to_left", "front_to_back"]:
            wall = WallSegmentConfig(length=120.0, height=96.0)
            ceiling = CeilingConfig(
                slope=CeilingSlopeConfig(
                    angle=25.0,
                    start_height=84.0,
                    direction=direction,  # type: ignore
                )
            )
            room = RoomConfig(name="test", walls=[wall], ceiling=ceiling)
            config = CabinetConfiguration(
                schema_version="1.1",
                cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
                room=room,
            )

            result = config_to_ceiling_slope(config)
            assert result is not None
            assert result.direction == direction


class TestConfigToSkylights:
    """Tests for config_to_skylights function (FRD-11)."""

    def test_returns_empty_list_when_no_room(self) -> None:
        """config_to_skylights should return empty list when no room configured."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        result = config_to_skylights(config)
        assert result == []

    def test_returns_empty_list_when_no_ceiling(self) -> None:
        """config_to_skylights should return empty list when room has no ceiling."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="test", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        result = config_to_skylights(config)
        assert result == []

    def test_returns_empty_list_when_no_skylights(self) -> None:
        """config_to_skylights should return empty list when ceiling has no skylights."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig()  # No skylights
        room = RoomConfig(name="test", walls=[wall], ceiling=ceiling)
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        result = config_to_skylights(config)
        assert result == []

    def test_converts_single_skylight(self) -> None:
        """config_to_skylights should convert a single skylight."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig(
            skylights=[
                SkylightConfig(
                    x_position=24.0,
                    width=36.0,
                    projection_depth=12.0,
                    projection_angle=90.0,
                )
            ]
        )
        room = RoomConfig(name="sunroom", walls=[wall], ceiling=ceiling)
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_skylights(config)

        assert len(result) == 1
        assert isinstance(result[0], Skylight)
        assert result[0].x_position == 24.0
        assert result[0].width == 36.0
        assert result[0].projection_depth == 12.0
        assert result[0].projection_angle == 90.0

    def test_converts_multiple_skylights(self) -> None:
        """config_to_skylights should convert multiple skylights."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        ceiling = CeilingConfig(
            skylights=[
                SkylightConfig(
                    x_position=24.0,
                    width=30.0,
                    projection_depth=10.0,
                ),
                SkylightConfig(
                    x_position=72.0,
                    width=24.0,
                    projection_depth=8.0,
                    projection_angle=75.0,
                ),
            ]
        )
        room = RoomConfig(name="sunroom", walls=[wall], ceiling=ceiling)
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_skylights(config)

        assert len(result) == 2
        assert result[0].x_position == 24.0
        assert result[0].width == 30.0
        assert result[1].x_position == 72.0
        assert result[1].projection_angle == 75.0


class TestConfigToOutsideCorner:
    """Tests for config_to_outside_corner function (FRD-11)."""

    def test_returns_none_when_no_room(self) -> None:
        """config_to_outside_corner should return None when no room configured."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        result = config_to_outside_corner(config)
        assert result is None

    def test_returns_none_when_no_outside_corner(self) -> None:
        """config_to_outside_corner should return None when room has no outside_corner."""
        wall = WallSegmentConfig(length=120.0, height=96.0)
        room = RoomConfig(name="test", walls=[wall])
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )
        result = config_to_outside_corner(config)
        assert result is None

    def test_converts_outside_corner_angled_face(self) -> None:
        """config_to_outside_corner should convert angled_face treatment."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=-90)
        outside_corner = OutsideCornerConfigSchema(
            treatment="angled_face",
            face_angle=45.0,
        )
        room = RoomConfig(
            name="corner",
            walls=[wall1, wall2],
            outside_corner=outside_corner,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_outside_corner(config)

        assert result is not None
        assert isinstance(result, OutsideCornerConfig)
        assert result.treatment == "angled_face"
        assert result.face_angle == 45.0
        assert result.filler_width == 3.0  # default

    def test_converts_outside_corner_butted_filler(self) -> None:
        """config_to_outside_corner should convert butted_filler treatment."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=-90)
        outside_corner = OutsideCornerConfigSchema(
            treatment="butted_filler",
            filler_width=4.0,
        )
        room = RoomConfig(
            name="corner",
            walls=[wall1, wall2],
            outside_corner=outside_corner,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_outside_corner(config)

        assert result is not None
        assert result.treatment == "butted_filler"
        assert result.filler_width == 4.0

    def test_converts_outside_corner_wrap_around(self) -> None:
        """config_to_outside_corner should convert wrap_around treatment."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=-90)
        outside_corner = OutsideCornerConfigSchema(treatment="wrap_around")
        room = RoomConfig(
            name="corner",
            walls=[wall1, wall2],
            outside_corner=outside_corner,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_outside_corner(config)

        assert result is not None
        assert result.treatment == "wrap_around"

    def test_converts_all_fields(self) -> None:
        """config_to_outside_corner should convert all fields correctly."""
        wall1 = WallSegmentConfig(length=120.0, height=96.0, angle=0)
        wall2 = WallSegmentConfig(length=60.0, height=96.0, angle=-90)
        outside_corner = OutsideCornerConfigSchema(
            treatment="angled_face",
            filler_width=5.0,
            face_angle=30.0,
        )
        room = RoomConfig(
            name="corner",
            walls=[wall1, wall2],
            outside_corner=outside_corner,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            room=room,
        )

        result = config_to_outside_corner(config)

        assert result is not None
        assert result.treatment == "angled_face"
        assert result.filler_width == 5.0
        assert result.face_angle == 30.0


class TestFRD11AdapterIntegration:
    """Integration tests for FRD-11 adapter functions."""

    def test_full_config_all_frd11_features(self) -> None:
        """All FRD-11 adapter functions should work together."""
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

        # Test all adapter functions
        slope = config_to_ceiling_slope(config)
        skylights = config_to_skylights(config)
        corner = config_to_outside_corner(config)

        # Verify slope
        assert slope is not None
        assert slope.angle == 25.0
        assert slope.start_height == 96.0
        assert slope.direction == "front_to_back"
        assert slope.min_height == 30.0

        # Verify skylights
        assert len(skylights) == 1
        assert skylights[0].x_position == 48.0
        assert skylights[0].width == 24.0
        assert skylights[0].projection_depth == 10.0
        assert skylights[0].projection_angle == 85.0

        # Verify corner
        assert corner is not None
        assert corner.treatment == "angled_face"
        assert corner.face_angle == 45.0

    def test_backward_compatibility(self) -> None:
        """FRD-11 adapter functions should handle v1.0 configs gracefully."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        slope = config_to_ceiling_slope(config)
        skylights = config_to_skylights(config)
        corner = config_to_outside_corner(config)

        assert slope is None
        assert skylights == []
        assert corner is None
