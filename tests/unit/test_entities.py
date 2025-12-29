"""Unit tests for domain entities.

These tests verify:
- WallSegment creation and validation
- WallConstraints type alias for backward compatibility
- Wall entity validation
- Room aggregate with geometry calculations
"""

import math

import pytest

from cabinets.domain.entities import Cabinet, Room, Section, Wall, WallConstraints, WallSegment
from cabinets.domain.value_objects import (
    GeometryError,
    MaterialSpec,
    Point2D,
    Position,
    SectionType,
    WallPosition,
)


class TestWall:
    """Tests for Wall entity."""

    def test_valid_wall_creation(self) -> None:
        """Valid wall should be created successfully."""
        wall = Wall(width=120.0, height=96.0, depth=12.0)
        assert wall.width == 120.0
        assert wall.height == 96.0
        assert wall.depth == 12.0

    def test_wall_is_frozen(self) -> None:
        """Wall should be immutable (frozen dataclass)."""
        wall = Wall(width=120.0, height=96.0, depth=12.0)
        with pytest.raises(AttributeError):
            wall.width = 100.0  # type: ignore

    def test_wall_rejects_zero_width(self) -> None:
        """Wall should reject zero width."""
        with pytest.raises(ValueError) as exc_info:
            Wall(width=0, height=96.0, depth=12.0)
        assert "must be positive" in str(exc_info.value)

    def test_wall_rejects_negative_height(self) -> None:
        """Wall should reject negative height."""
        with pytest.raises(ValueError) as exc_info:
            Wall(width=120.0, height=-10.0, depth=12.0)
        assert "must be positive" in str(exc_info.value)

    def test_wall_rejects_zero_depth(self) -> None:
        """Wall should reject zero depth."""
        with pytest.raises(ValueError) as exc_info:
            Wall(width=120.0, height=96.0, depth=0)
        assert "must be positive" in str(exc_info.value)

    def test_to_dimensions(self) -> None:
        """Wall should convert to Dimensions value object."""
        wall = Wall(width=120.0, height=96.0, depth=12.0)
        dimensions = wall.to_dimensions()
        assert dimensions.width == 120.0
        assert dimensions.height == 96.0
        assert dimensions.depth == 12.0


class TestWallConstraints:
    """Tests for WallConstraints type alias."""

    def test_wall_constraints_is_wall(self) -> None:
        """WallConstraints should be the same as Wall."""
        assert WallConstraints is Wall

    def test_wall_constraints_usage(self) -> None:
        """WallConstraints should work identically to Wall."""
        constraints = WallConstraints(width=120.0, height=96.0, depth=12.0)
        assert isinstance(constraints, Wall)
        assert constraints.width == 120.0
        assert constraints.height == 96.0
        assert constraints.depth == 12.0


class TestWallSegment:
    """Tests for WallSegment entity."""

    def test_valid_wall_segment_minimal(self) -> None:
        """Valid wall segment with only required fields."""
        segment = WallSegment(length=120.0, height=96.0)
        assert segment.length == 120.0
        assert segment.height == 96.0
        assert segment.angle == 0.0  # default
        assert segment.name is None  # default
        assert segment.depth == 12.0  # default

    def test_valid_wall_segment_full(self) -> None:
        """Valid wall segment with all fields specified."""
        segment = WallSegment(
            length=120.0,
            height=96.0,
            angle=90,
            name="north_wall",
            depth=18.0,
        )
        assert segment.length == 120.0
        assert segment.height == 96.0
        assert segment.angle == 90
        assert segment.name == "north_wall"
        assert segment.depth == 18.0

    def test_valid_angles(self) -> None:
        """Wall segment should accept valid angles in range -135 to 135."""
        for angle in (-135, -90, -45, 0, 45, 90, 120, 135):
            segment = WallSegment(length=100.0, height=96.0, angle=angle)
            assert segment.angle == angle

    def test_angle_as_float(self) -> None:
        """Wall segment should accept angle as float."""
        segment = WallSegment(length=100.0, height=96.0, angle=90.0)
        assert segment.angle == 90.0

    def test_rejects_zero_length(self) -> None:
        """Wall segment should reject zero length."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=0, height=96.0)
        assert "Wall dimensions must be positive" in str(exc_info.value)

    def test_rejects_negative_length(self) -> None:
        """Wall segment should reject negative length."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=-10.0, height=96.0)
        assert "Wall dimensions must be positive" in str(exc_info.value)

    def test_rejects_zero_height(self) -> None:
        """Wall segment should reject zero height."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=0)
        assert "Wall dimensions must be positive" in str(exc_info.value)

    def test_rejects_negative_height(self) -> None:
        """Wall segment should reject negative height."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=-10.0)
        assert "Wall dimensions must be positive" in str(exc_info.value)

    def test_rejects_zero_depth(self) -> None:
        """Wall segment should reject zero depth."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=96.0, depth=0)
        assert "Depth must be positive" in str(exc_info.value)

    def test_rejects_negative_depth(self) -> None:
        """Wall segment should reject negative depth."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=96.0, depth=-5.0)
        assert "Depth must be positive" in str(exc_info.value)

    def test_rejects_angle_above_135(self) -> None:
        """Wall segment should reject angles above 135 degrees."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=96.0, angle=150)
        assert "Angle must be between -135 and 135 degrees" in str(exc_info.value)

    def test_rejects_angle_180(self) -> None:
        """Wall segment should reject 180 degree angle."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=96.0, angle=180)
        assert "Angle must be between -135 and 135 degrees" in str(exc_info.value)

    def test_rejects_angle_below_negative_135(self) -> None:
        """Wall segment should reject angles below -135 degrees."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=96.0, angle=-150)
        assert "Angle must be between -135 and 135 degrees" in str(exc_info.value)

    def test_rejects_angle_negative_180(self) -> None:
        """Wall segment should reject -180 degree angle."""
        with pytest.raises(ValueError) as exc_info:
            WallSegment(length=120.0, height=96.0, angle=-180)
        assert "Angle must be between -135 and 135 degrees" in str(exc_info.value)

    def test_wall_segment_is_mutable(self) -> None:
        """Wall segment should be mutable (not frozen)."""
        segment = WallSegment(length=120.0, height=96.0)
        segment.length = 100.0
        assert segment.length == 100.0

    def test_optional_name_can_be_set(self) -> None:
        """Wall segment name can be set to any string."""
        segment = WallSegment(length=120.0, height=96.0, name="kitchen_wall_1")
        assert segment.name == "kitchen_wall_1"

    def test_typical_room_wall(self) -> None:
        """Test typical room wall segment values."""
        # 10 foot wall, 8 foot ceiling, 90 degree turn, 12 inch depth
        segment = WallSegment(
            length=120.0,  # 10 feet in inches
            height=96.0,   # 8 feet in inches
            angle=90,      # right turn
            name="east_wall",
            depth=12.0,
        )
        assert segment.length == 120.0
        assert segment.height == 96.0
        assert segment.angle == 90
        assert segment.name == "east_wall"
        assert segment.depth == 12.0


class TestRoom:
    """Tests for Room aggregate."""

    # --- Creation and Validation Tests ---

    def test_valid_room_single_wall(self) -> None:
        """Room with a single wall should be created successfully."""
        wall = WallSegment(length=120.0, height=96.0, angle=0)
        room = Room(name="hallway", walls=[wall])
        assert room.name == "hallway"
        assert len(room.walls) == 1
        assert room.is_closed is False
        assert room.closure_tolerance == 0.1

    def test_valid_room_multiple_walls(self) -> None:
        """Room with multiple walls should be created successfully."""
        walls = [
            WallSegment(length=120.0, height=96.0, angle=0),
            WallSegment(length=80.0, height=96.0, angle=90),
            WallSegment(length=120.0, height=96.0, angle=90),
        ]
        room = Room(name="kitchen", walls=walls)
        assert room.name == "kitchen"
        assert len(room.walls) == 3

    def test_room_rejects_empty_walls(self) -> None:
        """Room should reject empty wall list."""
        with pytest.raises(ValueError) as exc_info:
            Room(name="empty", walls=[])
        assert "Room must have at least one wall" in str(exc_info.value)

    def test_room_rejects_first_wall_with_nonzero_angle(self) -> None:
        """Room should reject first wall with non-zero angle."""
        wall = WallSegment(length=120.0, height=96.0, angle=90)
        with pytest.raises(ValueError) as exc_info:
            Room(name="invalid", walls=[wall])
        assert "First wall must have angle=0" in str(exc_info.value)

    def test_room_custom_closure_tolerance(self) -> None:
        """Room should accept custom closure tolerance."""
        wall = WallSegment(length=120.0, height=96.0, angle=0)
        room = Room(name="test", walls=[wall], closure_tolerance=0.5)
        assert room.closure_tolerance == 0.5

    # --- total_length Property Tests ---

    def test_total_length_single_wall(self) -> None:
        """Total length should equal single wall length."""
        wall = WallSegment(length=120.0, height=96.0, angle=0)
        room = Room(name="test", walls=[wall])
        assert room.total_length == 120.0

    def test_total_length_multiple_walls(self) -> None:
        """Total length should sum all wall lengths."""
        walls = [
            WallSegment(length=120.0, height=96.0, angle=0),
            WallSegment(length=80.0, height=96.0, angle=90),
            WallSegment(length=100.0, height=96.0, angle=90),
        ]
        room = Room(name="test", walls=walls)
        assert room.total_length == 300.0

    # --- get_wall_positions Tests ---

    def test_wall_positions_single_wall_along_x(self) -> None:
        """Single wall should start at origin and end along positive X."""
        wall = WallSegment(length=100.0, height=96.0, angle=0)
        room = Room(name="test", walls=[wall])
        positions = room.get_wall_positions()

        assert len(positions) == 1
        pos = positions[0]
        assert pos.wall_index == 0
        assert pos.start.x == pytest.approx(0.0)
        assert pos.start.y == pytest.approx(0.0)
        assert pos.end.x == pytest.approx(100.0)
        assert pos.end.y == pytest.approx(0.0)
        assert pos.direction == pytest.approx(0.0)

    def test_wall_positions_l_shape_turn_right(self) -> None:
        """L-shape with right turn should go along X then negative Y."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=50.0, height=96.0, angle=90),  # Turn right
        ]
        room = Room(name="test", walls=walls)
        positions = room.get_wall_positions()

        assert len(positions) == 2

        # First wall: origin to (100, 0)
        assert positions[0].start.x == pytest.approx(0.0)
        assert positions[0].start.y == pytest.approx(0.0)
        assert positions[0].end.x == pytest.approx(100.0)
        assert positions[0].end.y == pytest.approx(0.0)
        assert positions[0].direction == pytest.approx(0.0)

        # Second wall: (100, 0) to (100, -50) - turning right goes in negative Y
        assert positions[1].start.x == pytest.approx(100.0)
        assert positions[1].start.y == pytest.approx(0.0)
        assert positions[1].end.x == pytest.approx(100.0)
        assert positions[1].end.y == pytest.approx(-50.0)
        assert positions[1].direction == pytest.approx(270.0)

    def test_wall_positions_l_shape_turn_left(self) -> None:
        """L-shape with left turn should go along X then positive Y."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=50.0, height=96.0, angle=-90),  # Turn left
        ]
        room = Room(name="test", walls=walls)
        positions = room.get_wall_positions()

        assert len(positions) == 2

        # First wall: origin to (100, 0)
        assert positions[0].start.x == pytest.approx(0.0)
        assert positions[0].start.y == pytest.approx(0.0)
        assert positions[0].end.x == pytest.approx(100.0)
        assert positions[0].end.y == pytest.approx(0.0)

        # Second wall: (100, 0) to (100, 50) - turning left goes in positive Y
        assert positions[1].start.x == pytest.approx(100.0)
        assert positions[1].start.y == pytest.approx(0.0)
        assert positions[1].end.x == pytest.approx(100.0)
        assert positions[1].end.y == pytest.approx(50.0)
        assert positions[1].direction == pytest.approx(90.0)

    def test_wall_positions_rectangular_room(self) -> None:
        """Rectangular room with 4 walls should form a closed rectangle."""
        # Create a 100x60 rectangle (clockwise: right turns)
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),   # East
            WallSegment(length=60.0, height=96.0, angle=90),   # South
            WallSegment(length=100.0, height=96.0, angle=90),  # West
            WallSegment(length=60.0, height=96.0, angle=90),   # North
        ]
        room = Room(name="rectangle", walls=walls, is_closed=True)
        positions = room.get_wall_positions()

        assert len(positions) == 4

        # Wall 0: (0,0) -> (100,0), direction 0
        assert positions[0].end.x == pytest.approx(100.0)
        assert positions[0].end.y == pytest.approx(0.0)

        # Wall 1: (100,0) -> (100,-60), direction 270
        assert positions[1].end.x == pytest.approx(100.0)
        assert positions[1].end.y == pytest.approx(-60.0)

        # Wall 2: (100,-60) -> (0,-60), direction 180
        assert positions[2].end.x == pytest.approx(0.0)
        assert positions[2].end.y == pytest.approx(-60.0)

        # Wall 3: (0,-60) -> (0,0), direction 90
        assert positions[3].end.x == pytest.approx(0.0)
        assert positions[3].end.y == pytest.approx(0.0)

    def test_wall_positions_straight_continuation(self) -> None:
        """Walls with angle=0 should continue in same direction."""
        walls = [
            WallSegment(length=50.0, height=96.0, angle=0),
            WallSegment(length=50.0, height=96.0, angle=0),  # Continue straight
        ]
        room = Room(name="test", walls=walls)
        positions = room.get_wall_positions()

        assert positions[1].start.x == pytest.approx(50.0)
        assert positions[1].end.x == pytest.approx(100.0)
        assert positions[1].end.y == pytest.approx(0.0)
        assert positions[1].direction == pytest.approx(0.0)

    # --- bounding_box Property Tests ---

    def test_bounding_box_single_wall(self) -> None:
        """Bounding box of single wall along X axis."""
        wall = WallSegment(length=100.0, height=96.0, angle=0)
        room = Room(name="test", walls=[wall])
        width, depth = room.bounding_box
        assert width == pytest.approx(100.0)
        assert depth == pytest.approx(0.0)

    def test_bounding_box_l_shape(self) -> None:
        """Bounding box of L-shaped room."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=50.0, height=96.0, angle=90),  # Turn right
        ]
        room = Room(name="test", walls=walls)
        width, depth = room.bounding_box
        assert width == pytest.approx(100.0)
        assert depth == pytest.approx(50.0)  # Depth in Y direction

    def test_bounding_box_rectangular_room(self) -> None:
        """Bounding box of rectangular room."""
        walls = [
            WallSegment(length=120.0, height=96.0, angle=0),
            WallSegment(length=80.0, height=96.0, angle=90),
            WallSegment(length=120.0, height=96.0, angle=90),
            WallSegment(length=80.0, height=96.0, angle=90),
        ]
        room = Room(name="test", walls=walls, is_closed=True)
        width, depth = room.bounding_box
        assert width == pytest.approx(120.0)
        assert depth == pytest.approx(80.0)

    def test_bounding_box_u_shape(self) -> None:
        """Bounding box of U-shaped room."""
        # U-shape: right, right, straight, left, left
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),   # East
            WallSegment(length=60.0, height=96.0, angle=90),   # South
            WallSegment(length=50.0, height=96.0, angle=90),   # West
            WallSegment(length=60.0, height=96.0, angle=-90),  # South again
            WallSegment(length=50.0, height=96.0, angle=-90),  # East
        ]
        room = Room(name="test", walls=walls)
        width, depth = room.bounding_box
        # Total width should be 100 (first wall)
        # Total depth should be 120 (two 60-unit walls going down)
        assert width == pytest.approx(100.0)
        assert depth == pytest.approx(120.0)

    # --- validate_geometry Tests ---

    def test_validate_geometry_valid_l_shape(self) -> None:
        """Valid L-shape should have no geometry errors."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=50.0, height=96.0, angle=90),
        ]
        room = Room(name="test", walls=walls)
        errors = room.validate_geometry()
        assert len(errors) == 0

    def test_validate_geometry_closed_rectangle(self) -> None:
        """Properly closed rectangle should have no closure error."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=60.0, height=96.0, angle=90),
            WallSegment(length=100.0, height=96.0, angle=90),
            WallSegment(length=60.0, height=96.0, angle=90),
        ]
        room = Room(name="test", walls=walls, is_closed=True)
        errors = room.validate_geometry()
        assert len(errors) == 0

    def test_validate_geometry_closure_gap_error(self) -> None:
        """Room marked as closed but with gap should report closure error."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=60.0, height=96.0, angle=90),
            WallSegment(length=100.0, height=96.0, angle=90),
            WallSegment(length=50.0, height=96.0, angle=90),  # 10 inches short
        ]
        room = Room(name="test", walls=walls, is_closed=True)
        errors = room.validate_geometry()

        assert len(errors) == 1
        assert errors[0].error_type == "closure"
        assert "closure gap" in errors[0].message.lower()

    def test_validate_geometry_closure_within_tolerance(self) -> None:
        """Small closure gap within tolerance should not report error."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=60.0, height=96.0, angle=90),
            WallSegment(length=100.0, height=96.0, angle=90),
            WallSegment(length=59.95, height=96.0, angle=90),  # 0.05 short
        ]
        room = Room(name="test", walls=walls, is_closed=True, closure_tolerance=0.1)
        errors = room.validate_geometry()
        assert len(errors) == 0

    def test_validate_geometry_self_intersection(self) -> None:
        """Room with self-intersecting walls should report intersection error."""
        # Create a shape where wall 3 crosses wall 0:
        # Wall 0: (0,0) -> (100,0) horizontal
        # Wall 1: (100,0) -> (100,100) vertical up
        # Wall 2: (100,100) -> (50,100) horizontal left
        # Wall 3: (50,100) -> (50,-50) vertical down - crosses wall 0 at (50,0)
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),    # Wall 0: East
            WallSegment(length=100.0, height=96.0, angle=-90),  # Wall 1: North
            WallSegment(length=50.0, height=96.0, angle=-90),   # Wall 2: West
            WallSegment(length=150.0, height=96.0, angle=-90),  # Wall 3: South (crosses wall 0)
        ]
        room = Room(name="test", walls=walls)
        errors = room.validate_geometry()

        # Should detect intersection between walls 0 and 3
        intersection_errors = [e for e in errors if e.error_type == "intersection"]
        assert len(intersection_errors) >= 1
        assert (0, 3) in [e.wall_indices for e in intersection_errors]

    def test_validate_geometry_non_closed_no_closure_check(self) -> None:
        """Non-closed room should not check for closure gap."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=60.0, height=96.0, angle=90),
        ]
        room = Room(name="test", walls=walls, is_closed=False)
        errors = room.validate_geometry()

        closure_errors = [e for e in errors if e.error_type == "closure"]
        assert len(closure_errors) == 0

    def test_validate_geometry_adjacent_walls_not_intersection(self) -> None:
        """Adjacent walls sharing endpoint should not be flagged as intersecting."""
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0),
            WallSegment(length=50.0, height=96.0, angle=90),
            WallSegment(length=100.0, height=96.0, angle=90),
        ]
        room = Room(name="test", walls=walls)
        errors = room.validate_geometry()

        intersection_errors = [e for e in errors if e.error_type == "intersection"]
        assert len(intersection_errors) == 0

    # --- Real-world Scenario Tests ---

    def test_typical_kitchen_room(self) -> None:
        """Test a typical kitchen room configuration."""
        # 10x12 foot kitchen (120x144 inches)
        walls = [
            WallSegment(length=144.0, height=96.0, angle=0, name="south"),
            WallSegment(length=120.0, height=96.0, angle=90, name="west"),
            WallSegment(length=144.0, height=96.0, angle=90, name="north"),
            WallSegment(length=120.0, height=96.0, angle=90, name="east"),
        ]
        room = Room(name="kitchen", walls=walls, is_closed=True)

        assert room.total_length == 528.0  # Perimeter
        width, depth = room.bounding_box
        assert width == pytest.approx(144.0)
        assert depth == pytest.approx(120.0)
        assert len(room.validate_geometry()) == 0

    def test_closet_alcove_room(self) -> None:
        """Test an L-shaped alcove/closet configuration."""
        # Alcove that is 36 inches wide, 24 inches deep
        walls = [
            WallSegment(length=36.0, height=96.0, angle=0, name="back"),
            WallSegment(length=24.0, height=96.0, angle=90, name="left_side"),
        ]
        room = Room(name="closet_alcove", walls=walls, is_closed=False)

        assert room.total_length == 60.0
        width, depth = room.bounding_box
        assert width == pytest.approx(36.0)
        assert depth == pytest.approx(24.0)
        assert len(room.validate_geometry()) == 0


class TestSectionSectionType:
    """Tests for Section section_type field (FRD-04)."""

    def test_section_type_defaults_to_open(self) -> None:
        """Section should default section_type to OPEN."""
        section = Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(x=0, y=0),
        )
        assert section.section_type == SectionType.OPEN

    def test_section_type_open(self) -> None:
        """Section should accept OPEN section type."""
        section = Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(x=0, y=0),
            section_type=SectionType.OPEN,
        )
        assert section.section_type == SectionType.OPEN

    def test_section_type_doored(self) -> None:
        """Section should accept DOORED section type."""
        section = Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(x=0, y=0),
            section_type=SectionType.DOORED,
        )
        assert section.section_type == SectionType.DOORED

    def test_section_type_drawers(self) -> None:
        """Section should accept DRAWERS section type."""
        section = Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(x=0, y=0),
            section_type=SectionType.DRAWERS,
        )
        assert section.section_type == SectionType.DRAWERS

    def test_section_type_cubby(self) -> None:
        """Section should accept CUBBY section type."""
        section = Section(
            width=12.0,
            height=12.0,
            depth=12.0,
            position=Position(x=0, y=0),
            section_type=SectionType.CUBBY,
        )
        assert section.section_type == SectionType.CUBBY

    def test_section_type_is_mutable(self) -> None:
        """Section section_type should be mutable (Section is not frozen)."""
        section = Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(x=0, y=0),
            section_type=SectionType.OPEN,
        )
        section.section_type = SectionType.DOORED
        assert section.section_type == SectionType.DOORED


class TestCabinetDefaultShelfCount:
    """Tests for Cabinet default_shelf_count field (FRD-04)."""

    def test_default_shelf_count_defaults_to_zero(self) -> None:
        """Cabinet default_shelf_count should default to 0."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )
        assert cabinet.default_shelf_count == 0

    def test_default_shelf_count_with_valid_value(self) -> None:
        """Cabinet should accept valid default_shelf_count."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            default_shelf_count=3,
        )
        assert cabinet.default_shelf_count == 3

    def test_default_shelf_count_zero_valid(self) -> None:
        """Cabinet should accept default_shelf_count of 0."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            default_shelf_count=0,
        )
        assert cabinet.default_shelf_count == 0

    def test_default_shelf_count_high_value(self) -> None:
        """Cabinet should accept high default_shelf_count values."""
        cabinet = Cabinet(
            width=48.0,
            height=120.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            default_shelf_count=20,
        )
        assert cabinet.default_shelf_count == 20

    def test_default_shelf_count_negative_raises_error(self) -> None:
        """Cabinet should reject negative default_shelf_count."""
        with pytest.raises(ValueError, match="default_shelf_count cannot be negative"):
            Cabinet(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialSpec.standard_3_4(),
                default_shelf_count=-1,
            )

    def test_default_shelf_count_with_sections(self) -> None:
        """Cabinet with sections should maintain default_shelf_count."""
        section = Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(x=0, y=0),
        )
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            sections=[section],
            default_shelf_count=5,
        )
        assert cabinet.default_shelf_count == 5
        assert len(cabinet.sections) == 1

    def test_default_shelf_count_with_back_material(self) -> None:
        """Cabinet should work with both default_shelf_count and back_material."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
            default_shelf_count=4,
        )
        assert cabinet.default_shelf_count == 4
        assert cabinet.back_material is not None
        assert cabinet.back_material.thickness == 0.5


class TestSectionTypeEnum:
    """Tests for SectionType enum values (FRD-04)."""

    def test_section_type_values(self) -> None:
        """SectionType should have all expected values."""
        assert SectionType.OPEN.value == "open"
        assert SectionType.DOORED.value == "doored"
        assert SectionType.DRAWERS.value == "drawers"
        assert SectionType.CUBBY.value == "cubby"

    def test_section_type_count(self) -> None:
        """SectionType should have exactly 4 values."""
        assert len(SectionType) == 4

    def test_section_type_from_value(self) -> None:
        """SectionType should be creatable from string values."""
        assert SectionType("open") == SectionType.OPEN
        assert SectionType("doored") == SectionType.DOORED
        assert SectionType("drawers") == SectionType.DRAWERS
        assert SectionType("cubby") == SectionType.CUBBY


class TestPanelCutMetadataField:
    """Tests for Panel cut_metadata field (FRD-11)."""

    def test_panel_default_no_cut_metadata(self) -> None:
        """Panel should default cut_metadata to None."""
        from cabinets.domain.entities import Panel
        from cabinets.domain.value_objects import PanelType

        panel = Panel(
            panel_type=PanelType.SHELF,
            width=24.0,
            height=12.0,
            material=MaterialSpec.standard_3_4(),
        )
        assert panel.cut_metadata is None

    def test_panel_with_cut_metadata(self) -> None:
        """Panel should accept cut_metadata dict."""
        from cabinets.domain.entities import Panel
        from cabinets.domain.value_objects import PanelType

        metadata = {
            "angle_cuts": [{"edge": "left", "angle": 45.0}],
            "taper": {"start_height": 96.0, "end_height": 72.0},
        }
        panel = Panel(
            panel_type=PanelType.LEFT_SIDE,
            width=12.0,
            height=84.0,
            material=MaterialSpec.standard_3_4(),
            cut_metadata=metadata,
        )
        assert panel.cut_metadata == metadata
        assert panel.cut_metadata["taper"]["start_height"] == 96.0

    def test_panel_to_cut_piece_passes_metadata(self) -> None:
        """Panel.to_cut_piece() should pass cut_metadata to CutPiece."""
        from cabinets.domain.entities import Panel
        from cabinets.domain.value_objects import PanelType

        metadata = {"notches": [{"x_offset": 12.0, "width": 24.0, "depth": 6.0}]}
        panel = Panel(
            panel_type=PanelType.TOP,
            width=48.0,
            height=12.0,
            material=MaterialSpec.standard_3_4(),
            cut_metadata=metadata,
        )
        cut_piece = panel.to_cut_piece()
        assert cut_piece.cut_metadata == metadata

    def test_panel_to_cut_piece_none_metadata(self) -> None:
        """Panel.to_cut_piece() should pass None when no cut_metadata."""
        from cabinets.domain.entities import Panel
        from cabinets.domain.value_objects import PanelType

        panel = Panel(
            panel_type=PanelType.SHELF,
            width=24.0,
            height=12.0,
            material=MaterialSpec.standard_3_4(),
        )
        cut_piece = panel.to_cut_piece()
        assert cut_piece.cut_metadata is None

    def test_panel_cut_metadata_with_quantity(self) -> None:
        """Panel.to_cut_piece() should preserve metadata with quantity."""
        from cabinets.domain.entities import Panel
        from cabinets.domain.value_objects import PanelType

        metadata = {"angle_cuts": [{"edge": "top", "angle": 30.0, "bevel": True}]}
        panel = Panel(
            panel_type=PanelType.DIVIDER,
            width=12.0,
            height=82.5,
            material=MaterialSpec.standard_3_4(),
            cut_metadata=metadata,
        )
        cut_piece = panel.to_cut_piece(quantity=3)
        assert cut_piece.quantity == 3
        assert cut_piece.cut_metadata == metadata
