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
    RoomConfig,
    SectionConfig,
    WallSegmentConfig,
    config_to_room,
    config_to_section_specs,
)
from cabinets.domain.entities import Room, WallSegment


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
