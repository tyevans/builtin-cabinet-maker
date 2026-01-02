"""Unit tests for corner cabinet room integration.

These tests verify:
- Detection of corner sections from specs
- Finding corners between walls in a room
- Corner footprint calculation
- Corner section assignment to wall junctions
- Space reservation on both walls for corner cabinets
- Regular section offset adjustment around corner reservations
"""

import pytest

from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.section_resolver import SectionSpec
from cabinets.domain.services import RoomLayoutService
from cabinets.domain.value_objects import (
    CornerSectionAssignment,
    CornerType,
    WallSpaceReservation,
)


@pytest.fixture
def room_layout_service() -> RoomLayoutService:
    """Create a RoomLayoutService instance for testing."""
    return RoomLayoutService()


@pytest.fixture
def l_shaped_room() -> Room:
    """Create an L-shaped room with a right turn corner.

    Wall 0: 120" long, runs along +X axis from origin
    Wall 1: 80" long, turns right 90 degrees (runs along -Y axis)

    The corner is at the junction of walls 0 and 1.
    """
    walls = [
        WallSegment(length=120.0, height=96.0, angle=0, name="south", depth=24.0),
        WallSegment(length=80.0, height=96.0, angle=90, name="west", depth=24.0),
    ]
    return Room(name="l_room", walls=walls)


@pytest.fixture
def u_shaped_room() -> Room:
    """Create a U-shaped room with two corners (right turns).

    Wall 0: 120" long, runs along +X axis
    Wall 1: 60" long, turns right 90 degrees
    Wall 2: 120" long, turns right 90 degrees

    Corners are at junctions of (0,1) and (1,2).
    """
    walls = [
        WallSegment(length=120.0, height=96.0, angle=0, name="south", depth=24.0),
        WallSegment(length=60.0, height=96.0, angle=90, name="west", depth=24.0),
        WallSegment(length=120.0, height=96.0, angle=90, name="north", depth=24.0),
    ]
    return Room(name="u_room", walls=walls)


@pytest.fixture
def l_shaped_room_left_turn() -> Room:
    """Create an L-shaped room with a left turn corner.

    Wall 0: 120" long, runs along +X axis
    Wall 1: 80" long, turns left 90 degrees (runs along +Y axis)

    The corner is at the junction of walls 0 and 1.
    """
    walls = [
        WallSegment(length=120.0, height=96.0, angle=0, name="south", depth=24.0),
        WallSegment(length=80.0, height=96.0, angle=-90, name="east", depth=24.0),
    ]
    return Room(name="l_room_left", walls=walls)


class TestDetectCornerSections:
    """Tests for detect_corner_sections method."""

    def test_no_corner_sections(self, room_layout_service: RoomLayoutService) -> None:
        """Specs without corner components should return empty list."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width=36.0, shelves=4),
        ]
        result = room_layout_service.detect_corner_sections(specs)
        assert result == []

    def test_detect_lazy_susan_corner(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Should detect lazy susan corner component."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(
                width=26.0,
                shelves=0,
                component_config={"component": "corner.lazy_susan"},
            ),
        ]
        result = room_layout_service.detect_corner_sections(specs)
        assert len(result) == 1
        assert result[0] == (1, "corner.lazy_susan")

    def test_detect_diagonal_corner(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Should detect diagonal corner component."""
        specs = [
            SectionSpec(
                width=24.0,
                shelves=0,
                component_config={"component": "corner.diagonal"},
            ),
        ]
        result = room_layout_service.detect_corner_sections(specs)
        assert len(result) == 1
        assert result[0] == (0, "corner.diagonal")

    def test_detect_blind_corner(self, room_layout_service: RoomLayoutService) -> None:
        """Should detect blind corner component."""
        specs = [
            SectionSpec(
                width=30.0,
                shelves=0,
                component_config={
                    "component": "corner.blind",
                    "blind_side": "left",
                    "accessible_width": 24.0,
                },
            ),
        ]
        result = room_layout_service.detect_corner_sections(specs)
        assert len(result) == 1
        assert result[0] == (0, "corner.blind")

    def test_detect_multiple_corners(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Should detect multiple corner components."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(
                width=26.0,
                shelves=0,
                component_config={"component": "corner.lazy_susan"},
            ),
            SectionSpec(width=36.0, shelves=4),
            SectionSpec(
                width=24.0,
                shelves=0,
                component_config={"component": "corner.diagonal"},
            ),
        ]
        result = room_layout_service.detect_corner_sections(specs)
        assert len(result) == 2
        assert result[0] == (1, "corner.lazy_susan")
        assert result[1] == (3, "corner.diagonal")

    def test_ignore_non_corner_components(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Should not detect non-corner components."""
        specs = [
            SectionSpec(
                width=24.0,
                shelves=3,
                component_config={"component": "shelf.fixed"},
            ),
            SectionSpec(
                width=24.0,
                shelves=0,
                component_config={"component": "door.hinged"},
            ),
        ]
        result = room_layout_service.detect_corner_sections(specs)
        assert result == []


class TestFindWallCorners:
    """Tests for find_wall_corners method."""

    def test_single_wall_no_corners(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Single wall room has no corners."""
        room = Room(
            name="single",
            walls=[WallSegment(length=120.0, height=96.0, angle=0)],
        )
        result = room_layout_service.find_wall_corners(room)
        assert result == []

    def test_l_shaped_room_one_corner(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """L-shaped room should have one corner."""
        result = room_layout_service.find_wall_corners(l_shaped_room)
        assert len(result) == 1
        left_wall, right_wall, angle = result[0]
        assert left_wall == 0
        assert right_wall == 1
        assert angle == 90

    def test_u_shaped_room_two_corners(
        self, room_layout_service: RoomLayoutService, u_shaped_room: Room
    ) -> None:
        """U-shaped room should have two corners."""
        result = room_layout_service.find_wall_corners(u_shaped_room)
        assert len(result) == 2

        # First corner: wall 0 -> wall 1
        assert result[0] == (0, 1, 90)
        # Second corner: wall 1 -> wall 2
        assert result[1] == (1, 2, 90)

    def test_left_turn_corner(
        self, room_layout_service: RoomLayoutService, l_shaped_room_left_turn: Room
    ) -> None:
        """Left turn should be detected with angle -90."""
        result = room_layout_service.find_wall_corners(l_shaped_room_left_turn)
        assert len(result) == 1
        left_wall, right_wall, angle = result[0]
        assert left_wall == 0
        assert right_wall == 1
        assert angle == -90


class TestCalculateCornerFootprint:
    """Tests for calculate_corner_footprint method."""

    def test_lazy_susan_default_clearance(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Lazy susan with default door clearance."""
        footprint = room_layout_service.calculate_corner_footprint(
            "corner.lazy_susan", {}, 24.0
        )
        # Default clearance is 2.0, so each wall = 24 + 2 = 26
        assert footprint.left_wall == 26.0
        assert footprint.right_wall == 26.0

    def test_lazy_susan_custom_clearance(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Lazy susan with custom door clearance."""
        footprint = room_layout_service.calculate_corner_footprint(
            "corner.lazy_susan", {"door_clearance": 3.0}, 24.0
        )
        assert footprint.left_wall == 27.0
        assert footprint.right_wall == 27.0

    def test_diagonal_footprint(self, room_layout_service: RoomLayoutService) -> None:
        """Diagonal corner footprint equals depth on each wall."""
        footprint = room_layout_service.calculate_corner_footprint(
            "corner.diagonal", {}, 24.0
        )
        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 24.0

    def test_blind_corner_left_side(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Blind corner with left blind side."""
        footprint = room_layout_service.calculate_corner_footprint(
            "corner.blind",
            {"blind_side": "left", "accessible_width": 36.0, "filler_width": 3.0},
            24.0,
        )
        # Left wall (blind side) = depth = 24
        # Right wall (accessible) = width + filler = 36 + 3 = 39
        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 39.0

    def test_blind_corner_right_side(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Blind corner with right blind side."""
        footprint = room_layout_service.calculate_corner_footprint(
            "corner.blind",
            {"blind_side": "right", "accessible_width": 30.0, "filler_width": 3.0},
            24.0,
        )
        # Left wall (accessible) = width + filler = 30 + 3 = 33
        # Right wall (blind side) = depth = 24
        assert footprint.left_wall == 33.0
        assert footprint.right_wall == 24.0

    def test_unknown_corner_type_raises(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Unknown corner type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown corner component type"):
            room_layout_service.calculate_corner_footprint("corner.unknown", {}, 24.0)


class TestGetCornerType:
    """Tests for get_corner_type method."""

    def test_lazy_susan_type(self, room_layout_service: RoomLayoutService) -> None:
        """Should return LAZY_SUSAN type."""
        assert (
            room_layout_service.get_corner_type("corner.lazy_susan")
            == CornerType.LAZY_SUSAN
        )

    def test_diagonal_type(self, room_layout_service: RoomLayoutService) -> None:
        """Should return DIAGONAL type."""
        assert (
            room_layout_service.get_corner_type("corner.diagonal")
            == CornerType.DIAGONAL
        )

    def test_blind_type(self, room_layout_service: RoomLayoutService) -> None:
        """Should return BLIND type."""
        assert room_layout_service.get_corner_type("corner.blind") == CornerType.BLIND

    def test_unknown_type_raises(self, room_layout_service: RoomLayoutService) -> None:
        """Should raise ValueError for unknown type."""
        with pytest.raises(ValueError, match="Unknown corner component type"):
            room_layout_service.get_corner_type("corner.unknown")


class TestAssignCornerSections:
    """Tests for assign_corner_sections method."""

    def test_no_corner_sections(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """No corner sections should return empty results."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=0),
            SectionSpec(width=36.0, shelves=4, wall=1),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room, specs
        )
        assert assignments == []
        assert reservations == []

    def test_single_lazy_susan_at_corner(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Lazy susan at L-shaped corner should create proper assignment."""
        specs = [
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=1,  # Wall 1 has the corner with wall 0
                component_config={"component": "corner.lazy_susan"},
            ),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room, specs
        )

        assert len(assignments) == 1
        assignment = assignments[0]

        assert assignment.section_index == 0
        assert assignment.left_wall_index == 0  # South wall
        assert assignment.right_wall_index == 1  # West wall
        assert assignment.corner_type == CornerType.LAZY_SUSAN
        assert assignment.left_wall_footprint == 26.0
        assert assignment.right_wall_footprint == 26.0
        # Corner at end of wall 0 (length 120), footprint 26
        assert assignment.left_wall_offset == pytest.approx(120.0 - 26.0)
        assert assignment.right_wall_offset == 0.0

    def test_corner_creates_two_reservations(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Corner section should create reservations on both walls."""
        specs = [
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={"component": "corner.lazy_susan"},
            ),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room, specs
        )

        assert len(reservations) == 2

        # Left wall reservation (at end of wall 0)
        left_res = [r for r in reservations if r.wall_index == 0][0]
        assert left_res.start_offset == pytest.approx(94.0)  # 120 - 26
        assert left_res.end_offset == 120.0
        assert left_res.is_corner_end is True
        assert left_res.is_corner_start is False

        # Right wall reservation (at start of wall 1)
        right_res = [r for r in reservations if r.wall_index == 1][0]
        assert right_res.start_offset == 0.0
        assert right_res.end_offset == 26.0
        assert right_res.is_corner_start is True
        assert right_res.is_corner_end is False

    def test_diagonal_corner_footprint(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Diagonal corner should have depth-based footprint."""
        specs = [
            SectionSpec(
                width=24.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={"component": "corner.diagonal"},
            ),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room, specs
        )

        assert len(assignments) == 1
        assert assignments[0].left_wall_footprint == 24.0
        assert assignments[0].right_wall_footprint == 24.0

    def test_blind_corner_asymmetric_footprint(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Blind corner should have asymmetric footprint."""
        specs = [
            SectionSpec(
                width=30.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={
                    "component": "corner.blind",
                    "blind_side": "left",
                    "accessible_width": 30.0,
                    "filler_width": 3.0,
                },
            ),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room, specs
        )

        assert len(assignments) == 1
        # Left wall (blind side) = depth = 24
        assert assignments[0].left_wall_footprint == 24.0
        # Right wall (accessible) = width + filler = 30 + 3 = 33
        assert assignments[0].right_wall_footprint == 33.0

    def test_left_turn_corner_swaps_footprint(
        self, room_layout_service: RoomLayoutService, l_shaped_room_left_turn: Room
    ) -> None:
        """Left turn corner should swap left/right footprint for asymmetric cabinets."""
        specs = [
            SectionSpec(
                width=30.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={
                    "component": "corner.blind",
                    "blind_side": "left",
                    "accessible_width": 30.0,
                    "filler_width": 3.0,
                },
            ),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room_left_turn, specs
        )

        assert len(assignments) == 1
        # For left turn, footprints are swapped
        # Original: left=24, right=33
        # After swap: left=33, right=24
        assert assignments[0].left_wall_footprint == 33.0
        assert assignments[0].right_wall_footprint == 24.0

    def test_no_corner_at_wall_skips_section(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Corner section on wall without corner should be skipped."""
        specs = [
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=0,  # Wall 0 is the left wall, not a corner wall
                component_config={"component": "corner.lazy_susan"},
            ),
        ]
        assignments, reservations = room_layout_service.assign_corner_sections(
            l_shaped_room, specs
        )

        # Wall 0 doesn't have a corner (it's the first wall), so this should be skipped
        assert len(assignments) == 0
        assert len(reservations) == 0


class TestAssignSectionsToWallsWithCorners:
    """Tests for assign_sections_to_walls_with_corners method."""

    def test_no_corner_sections_same_as_regular(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Without corners, should behave like regular assignment."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=0),
            SectionSpec(width=36.0, shelves=4, wall=0),
        ]
        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(
                l_shaped_room, specs
            )
        )

        assert len(regular) == 2
        assert len(corners) == 0
        assert len(reservations) == 0

        assert regular[0].section_index == 0
        assert regular[0].offset_along_wall == 0.0
        assert regular[1].section_index == 1
        assert regular[1].offset_along_wall == pytest.approx(24.0)

    def test_corner_reserves_space_for_regular_sections(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Corner should reserve space, regular sections offset after."""
        specs = [
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={"component": "corner.lazy_susan"},
            ),
            SectionSpec(width=24.0, shelves=3, wall=1),
        ]
        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(
                l_shaped_room, specs
            )
        )

        assert len(corners) == 1
        assert len(regular) == 1

        # Regular section on wall 1 should start after corner reservation
        # Corner reserves 26" at start of wall 1
        assert regular[0].section_index == 1
        assert regular[0].wall_index == 1
        assert regular[0].offset_along_wall == pytest.approx(26.0)

    def test_sections_on_left_wall_end_before_corner(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Sections on left wall should not overlap corner reservation."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=0),  # Regular on wall 0
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={"component": "corner.lazy_susan"},
            ),
        ]
        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(
                l_shaped_room, specs
            )
        )

        assert len(corners) == 1
        assert len(regular) == 1

        # Regular section on wall 0 starts at 0
        # Wall 0 is 120", corner reserves 26" at end (94-120)
        # Section at offset 0 with width 24 fits in 0-24
        assert regular[0].section_index == 0
        assert regular[0].wall_index == 0
        assert regular[0].offset_along_wall == 0.0

    def test_fill_sections_account_for_corner_reservation(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Fill sections should calculate width based on available space after corners."""
        specs = [
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={"component": "corner.lazy_susan"},
            ),
            SectionSpec(width="fill", shelves=3, wall=1),  # Fill remaining on wall 1
        ]
        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(
                l_shaped_room, specs
            )
        )

        assert len(corners) == 1
        assert len(regular) == 1

        # Wall 1 is 80", corner reserves 26" at start
        # Fill section should start at 26" and get width 80 - 26 = 54"
        assert regular[0].offset_along_wall == pytest.approx(26.0)

    def test_multiple_sections_with_corner(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Multiple sections around a corner should be positioned correctly."""
        specs = [
            SectionSpec(width=30.0, shelves=2, wall=0),  # Section 0 on wall 0
            SectionSpec(width=30.0, shelves=2, wall=0),  # Section 1 on wall 0
            SectionSpec(
                width=26.0,
                shelves=0,
                wall=1,
                depth=24.0,
                component_config={"component": "corner.lazy_susan"},
            ),  # Section 2: corner
            SectionSpec(width=24.0, shelves=3, wall=1),  # Section 3 on wall 1
            SectionSpec(width=24.0, shelves=3, wall=1),  # Section 4 on wall 1
        ]
        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(
                l_shaped_room, specs
            )
        )

        assert len(corners) == 1
        assert len(regular) == 4

        # Sort by section index for easier assertions
        regular_by_idx = {a.section_index: a for a in regular}

        # Wall 0 sections start at 0, not affected by corner end
        assert regular_by_idx[0].offset_along_wall == 0.0
        assert regular_by_idx[1].offset_along_wall == pytest.approx(30.0)

        # Wall 1 sections start after corner reservation (26")
        assert regular_by_idx[3].offset_along_wall == pytest.approx(26.0)
        assert regular_by_idx[4].offset_along_wall == pytest.approx(50.0)  # 26 + 24

    def test_empty_specs_returns_empty(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Empty specs should return empty results."""
        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(l_shaped_room, [])
        )
        assert regular == []
        assert corners == []
        assert reservations == []


class TestCornerSectionAssignmentDataclass:
    """Tests for CornerSectionAssignment dataclass validation."""

    def test_valid_assignment(self) -> None:
        """Valid assignment should be created successfully."""
        assignment = CornerSectionAssignment(
            section_index=0,
            left_wall_index=0,
            right_wall_index=1,
            left_wall_footprint=26.0,
            right_wall_footprint=26.0,
            corner_type=CornerType.LAZY_SUSAN,
        )
        assert assignment.section_index == 0
        assert assignment.total_footprint == 52.0

    def test_negative_section_index_raises(self) -> None:
        """Negative section index should raise ValueError."""
        with pytest.raises(ValueError, match="Section index must be non-negative"):
            CornerSectionAssignment(
                section_index=-1,
                left_wall_index=0,
                right_wall_index=1,
                left_wall_footprint=26.0,
                right_wall_footprint=26.0,
                corner_type=CornerType.LAZY_SUSAN,
            )

    def test_negative_wall_index_raises(self) -> None:
        """Negative wall index should raise ValueError."""
        with pytest.raises(ValueError, match="wall index must be non-negative"):
            CornerSectionAssignment(
                section_index=0,
                left_wall_index=-1,
                right_wall_index=1,
                left_wall_footprint=26.0,
                right_wall_footprint=26.0,
                corner_type=CornerType.LAZY_SUSAN,
            )

    def test_zero_footprint_raises(self) -> None:
        """Zero or negative footprint should raise ValueError."""
        with pytest.raises(ValueError, match="footprint must be positive"):
            CornerSectionAssignment(
                section_index=0,
                left_wall_index=0,
                right_wall_index=1,
                left_wall_footprint=0.0,
                right_wall_footprint=26.0,
                corner_type=CornerType.LAZY_SUSAN,
            )


class TestWallSpaceReservationDataclass:
    """Tests for WallSpaceReservation dataclass validation."""

    def test_valid_reservation(self) -> None:
        """Valid reservation should be created successfully."""
        reservation = WallSpaceReservation(
            wall_index=0,
            start_offset=94.0,
            end_offset=120.0,
            reserved_by_section=0,
            is_corner_end=True,
        )
        assert reservation.length == 26.0

    def test_negative_wall_index_raises(self) -> None:
        """Negative wall index should raise ValueError."""
        with pytest.raises(ValueError, match="Wall index must be non-negative"):
            WallSpaceReservation(
                wall_index=-1,
                start_offset=0.0,
                end_offset=26.0,
                reserved_by_section=0,
            )

    def test_negative_offset_raises(self) -> None:
        """Negative start offset should raise ValueError."""
        with pytest.raises(ValueError, match="Start offset must be non-negative"):
            WallSpaceReservation(
                wall_index=0,
                start_offset=-5.0,
                end_offset=26.0,
                reserved_by_section=0,
            )

    def test_end_before_start_raises(self) -> None:
        """End offset before start should raise ValueError."""
        with pytest.raises(ValueError, match="End offset must be >= start offset"):
            WallSpaceReservation(
                wall_index=0,
                start_offset=30.0,
                end_offset=20.0,
                reserved_by_section=0,
            )


class TestIntegrationScenarios:
    """Integration tests for realistic corner cabinet scenarios."""

    def test_kitchen_l_layout_with_corner(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Test a realistic L-shaped kitchen with corner cabinet."""
        # 10' x 8' L-shaped kitchen
        room = Room(
            name="kitchen",
            walls=[
                WallSegment(
                    length=120.0, height=96.0, angle=0, name="south", depth=24.0
                ),
                WallSegment(
                    length=96.0, height=96.0, angle=90, name="west", depth=24.0
                ),
            ],
        )

        specs = [
            # South wall cabinets
            SectionSpec(width=24.0, shelves=0, wall="south"),  # Base 1
            SectionSpec(width=36.0, shelves=0, wall="south"),  # Base 2 (sink)
            # Corner cabinet
            SectionSpec(
                width=26.0,
                shelves=0,
                wall="west",
                depth=24.0,
                component_config={"component": "corner.lazy_susan"},
            ),
            # West wall cabinets
            SectionSpec(width=24.0, shelves=0, wall="west"),  # Base 3
            SectionSpec(width=24.0, shelves=0, wall="west"),  # Base 4
        ]

        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(room, specs)
        )

        # Should have 1 corner and 4 regular sections
        assert len(corners) == 1
        assert len(regular) == 4

        # Corner should be section 2
        assert corners[0].section_index == 2
        assert corners[0].corner_type == CornerType.LAZY_SUSAN

        # South wall sections: 0, 1 at offsets 0, 24
        south_sections = [a for a in regular if a.wall_index == 0]
        assert len(south_sections) == 2
        south_by_idx = {a.section_index: a for a in south_sections}
        assert south_by_idx[0].offset_along_wall == 0.0
        assert south_by_idx[1].offset_along_wall == pytest.approx(24.0)

        # West wall sections: 3, 4 after corner (26")
        west_sections = [a for a in regular if a.wall_index == 1]
        assert len(west_sections) == 2
        west_by_idx = {a.section_index: a for a in west_sections}
        assert west_by_idx[3].offset_along_wall == pytest.approx(26.0)
        assert west_by_idx[4].offset_along_wall == pytest.approx(50.0)

    def test_u_shaped_kitchen_with_two_corners(
        self, room_layout_service: RoomLayoutService, u_shaped_room: Room
    ) -> None:
        """Test U-shaped layout with corner cabinets at both corners."""
        specs = [
            # South wall cabinets
            SectionSpec(width=24.0, shelves=0, wall="south"),
            # First corner (south->west)
            SectionSpec(
                width=24.0,
                shelves=0,
                wall="west",
                depth=24.0,
                component_config={"component": "corner.diagonal"},
            ),
            # West wall cabinet
            SectionSpec(width="fill", shelves=0, wall="west"),
            # Second corner (west->north)
            SectionSpec(
                width=24.0,
                shelves=0,
                wall="north",
                depth=24.0,
                component_config={"component": "corner.diagonal"},
            ),
            # North wall cabinets
            SectionSpec(width=24.0, shelves=0, wall="north"),
        ]

        regular, corners, reservations = (
            room_layout_service.assign_sections_to_walls_with_corners(
                u_shaped_room, specs
            )
        )

        # Should have 2 corners
        assert len(corners) == 2
        assert corners[0].section_index == 1
        assert corners[1].section_index == 3

        # Should have 3 regular sections
        assert len(regular) == 3

        # Reservations should cover both corners on 3 walls
        # Wall 0: end reservation for corner 1
        # Wall 1: start reservation for corner 1, end reservation for corner 2
        # Wall 2: start reservation for corner 2
        assert len(reservations) == 4
