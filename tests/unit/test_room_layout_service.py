"""Unit tests for RoomLayoutService.

These tests verify:
- Section assignment to walls
- 3D transform computation for sections
- Fit validation for sections on walls
"""

import math

import pytest

from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.section_resolver import SectionSpec
from cabinets.domain.services import RoomLayoutService
from cabinets.domain.value_objects import (
    FitError,
    SectionTransform,
    WallSectionAssignment,
)


@pytest.fixture
def room_layout_service() -> RoomLayoutService:
    """Create a RoomLayoutService instance for testing."""
    return RoomLayoutService()


@pytest.fixture
def simple_room() -> Room:
    """Create a simple single-wall room for testing."""
    wall = WallSegment(length=120.0, height=96.0, angle=0, name="main_wall")
    return Room(name="test_room", walls=[wall])


@pytest.fixture
def l_shaped_room() -> Room:
    """Create an L-shaped room with two walls."""
    walls = [
        WallSegment(length=120.0, height=96.0, angle=0, name="south"),
        WallSegment(length=80.0, height=96.0, angle=90, name="west"),
    ]
    return Room(name="l_room", walls=walls)


@pytest.fixture
def rectangular_room() -> Room:
    """Create a rectangular room with four walls."""
    walls = [
        WallSegment(length=144.0, height=96.0, angle=0, name="south"),
        WallSegment(length=120.0, height=96.0, angle=90, name="west"),
        WallSegment(length=144.0, height=96.0, angle=90, name="north"),
        WallSegment(length=120.0, height=96.0, angle=90, name="east"),
    ]
    return Room(name="kitchen", walls=walls, is_closed=True)


class TestAssignSectionsToWalls:
    """Tests for assign_sections_to_walls method."""

    def test_empty_section_specs(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Empty section specs should return empty assignments."""
        assignments = room_layout_service.assign_sections_to_walls(
            simple_room, []
        )
        assert assignments == []

    def test_single_section_default_wall(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Single section with no wall specified should go to wall 0."""
        specs = [SectionSpec(width=24.0, shelves=3)]
        assignments = room_layout_service.assign_sections_to_walls(
            simple_room, specs
        )

        assert len(assignments) == 1
        assert assignments[0].section_index == 0
        assert assignments[0].wall_index == 0
        assert assignments[0].offset_along_wall == 0.0

    def test_multiple_sections_sequential_placement(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Multiple sections should be placed sequentially on the wall."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width=36.0, shelves=4),
            SectionSpec(width=24.0, shelves=2),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            simple_room, specs
        )

        assert len(assignments) == 3
        assert assignments[0].offset_along_wall == 0.0
        assert assignments[1].offset_along_wall == pytest.approx(24.0)
        assert assignments[2].offset_along_wall == pytest.approx(60.0)

    def test_section_assigned_by_wall_index(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Section should be assigned to specified wall index."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=1),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            l_shaped_room, specs
        )

        assert len(assignments) == 1
        assert assignments[0].wall_index == 1
        assert assignments[0].offset_along_wall == 0.0

    def test_section_assigned_by_wall_name(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Section should be assigned to wall by name."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall="west"),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            l_shaped_room, specs
        )

        assert len(assignments) == 1
        assert assignments[0].wall_index == 1

    def test_sections_on_multiple_walls(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Sections on different walls should be tracked separately."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=0),
            SectionSpec(width=36.0, shelves=4, wall=1),
            SectionSpec(width=24.0, shelves=2, wall=0),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            l_shaped_room, specs
        )

        # Section 0 on wall 0 at offset 0
        assert assignments[0].section_index == 0
        assert assignments[0].wall_index == 0
        assert assignments[0].offset_along_wall == 0.0

        # Section 1 on wall 1 at offset 0
        assert assignments[1].section_index == 1
        assert assignments[1].wall_index == 1
        assert assignments[1].offset_along_wall == 0.0

        # Section 2 on wall 0 at offset 24
        assert assignments[2].section_index == 2
        assert assignments[2].wall_index == 0
        assert assignments[2].offset_along_wall == pytest.approx(24.0)

    def test_fill_section_width_calculation(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Fill section should calculate width based on remaining space."""
        # Wall is 120 inches, fixed section is 24 inches
        # Fill section should be 96 inches (120 - 24)
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            simple_room, specs
        )

        assert len(assignments) == 2
        assert assignments[0].offset_along_wall == 0.0
        assert assignments[1].offset_along_wall == pytest.approx(24.0)

    def test_multiple_fill_sections(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Multiple fill sections should split remaining space equally."""
        # Wall is 120 inches, fixed section is 24 inches
        # Two fill sections should each be 48 inches ((120 - 24) / 2)
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width=24.0, shelves=4),
            SectionSpec(width="fill", shelves=2),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            simple_room, specs
        )

        assert len(assignments) == 3
        # First fill section at offset 0
        assert assignments[0].offset_along_wall == 0.0
        # Fixed section at offset 48
        assert assignments[1].offset_along_wall == pytest.approx(48.0)
        # Second fill section at offset 72
        assert assignments[2].offset_along_wall == pytest.approx(72.0)

    def test_assignments_sorted_by_section_index(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Assignments should be returned sorted by section index."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=1),
            SectionSpec(width=36.0, shelves=4, wall=0),
            SectionSpec(width=24.0, shelves=2, wall=1),
        ]
        assignments = room_layout_service.assign_sections_to_walls(
            l_shaped_room, specs
        )

        assert [a.section_index for a in assignments] == [0, 1, 2]

    def test_invalid_wall_index_raises_error(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Invalid wall index should raise ValueError."""
        specs = [SectionSpec(width=24.0, shelves=3, wall=5)]

        with pytest.raises(ValueError) as exc_info:
            room_layout_service.assign_sections_to_walls(simple_room, specs)
        assert "out of range" in str(exc_info.value)

    def test_invalid_wall_name_raises_error(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Invalid wall name should raise ValueError."""
        specs = [SectionSpec(width=24.0, shelves=3, wall="nonexistent")]

        with pytest.raises(ValueError) as exc_info:
            room_layout_service.assign_sections_to_walls(simple_room, specs)
        assert "not found" in str(exc_info.value)


class TestComputeSectionTransforms:
    """Tests for compute_section_transforms method."""

    def test_empty_assignments(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Empty assignments should return empty transforms."""
        transforms = room_layout_service.compute_section_transforms(
            simple_room, [], []
        )
        assert transforms == []

    def test_single_section_on_first_wall(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Single section on first wall should have correct transform."""
        specs = [SectionSpec(width=24.0, shelves=3)]
        assignments = [
            WallSectionAssignment(section_index=0, wall_index=0, offset_along_wall=0.0)
        ]

        transforms = room_layout_service.compute_section_transforms(
            simple_room, assignments, specs
        )

        assert len(transforms) == 1
        assert transforms[0].section_index == 0
        assert transforms[0].wall_index == 0
        # First wall runs along X axis (direction=0), so position starts at origin
        assert transforms[0].position.x == pytest.approx(0.0)
        # Y is offset by depth perpendicular to wall direction
        assert transforms[0].position.z == pytest.approx(0.0)
        assert transforms[0].rotation_z == pytest.approx(0.0)

    def test_section_with_offset(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Section with offset should have position moved along wall."""
        specs = [SectionSpec(width=24.0, shelves=3)]
        assignments = [
            WallSectionAssignment(section_index=0, wall_index=0, offset_along_wall=50.0)
        ]

        transforms = room_layout_service.compute_section_transforms(
            simple_room, assignments, specs
        )

        assert len(transforms) == 1
        # Position should be offset 50 units along the wall (X direction for first wall)
        assert transforms[0].position.x == pytest.approx(50.0)

    def test_section_on_perpendicular_wall(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Section on perpendicular wall should have 270 degree rotation."""
        specs = [SectionSpec(width=24.0, shelves=3, wall=1)]
        assignments = [
            WallSectionAssignment(section_index=0, wall_index=1, offset_along_wall=0.0)
        ]

        transforms = room_layout_service.compute_section_transforms(
            l_shaped_room, assignments, specs
        )

        assert len(transforms) == 1
        assert transforms[0].wall_index == 1
        # Second wall has direction 270 (turned right 90 degrees)
        assert transforms[0].rotation_z == pytest.approx(270.0)

    def test_multiple_sections_transforms(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Multiple sections should have correct transforms."""
        specs = [
            SectionSpec(width=24.0, shelves=3, wall=0),
            SectionSpec(width=36.0, shelves=4, wall=1),
        ]
        assignments = [
            WallSectionAssignment(section_index=0, wall_index=0, offset_along_wall=0.0),
            WallSectionAssignment(section_index=1, wall_index=1, offset_along_wall=0.0),
        ]

        transforms = room_layout_service.compute_section_transforms(
            l_shaped_room, assignments, specs
        )

        assert len(transforms) == 2
        assert transforms[0].section_index == 0
        assert transforms[0].rotation_z == pytest.approx(0.0)
        assert transforms[1].section_index == 1
        assert transforms[1].rotation_z == pytest.approx(270.0)


class TestValidateFit:
    """Tests for validate_fit method."""

    def test_empty_section_specs(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Empty section specs should return no errors."""
        errors = room_layout_service.validate_fit(simple_room, [])
        assert errors == []

    def test_sections_fit_on_wall(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Sections that fit on wall should have no errors."""
        # Wall is 120 inches, total sections = 80 inches
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width=36.0, shelves=4),
            SectionSpec(width=20.0, shelves=2),
        ]
        errors = room_layout_service.validate_fit(simple_room, specs)
        assert errors == []

    def test_sections_exactly_fit_wall(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Sections that exactly fill wall should have no errors."""
        # Wall is 120 inches
        specs = [
            SectionSpec(width=60.0, shelves=3),
            SectionSpec(width=60.0, shelves=4),
        ]
        errors = room_layout_service.validate_fit(simple_room, specs)
        assert errors == []

    def test_fill_section_valid(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Fill section with valid remaining space should have no errors."""
        # Wall is 120 inches, fixed = 80, fill gets 40
        specs = [
            SectionSpec(width=40.0, shelves=3),
            SectionSpec(width=40.0, shelves=4),
            SectionSpec(width="fill", shelves=2),
        ]
        errors = room_layout_service.validate_fit(simple_room, specs)
        assert errors == []

    def test_fixed_widths_exceed_wall_length(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Fixed widths exceeding wall length should report error."""
        # Wall is 120 inches, total fixed = 150 inches
        specs = [
            SectionSpec(width=60.0, shelves=3),
            SectionSpec(width=50.0, shelves=4),
            SectionSpec(width=40.0, shelves=2),
        ]
        errors = room_layout_service.validate_fit(simple_room, specs)

        assert len(errors) == 1
        assert errors[0].error_type == "exceeds_length"
        assert errors[0].wall_index == 0
        assert "150.00" in errors[0].message
        assert "120.00" in errors[0].message

    def test_invalid_wall_index_reference(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Invalid wall index should report error."""
        specs = [SectionSpec(width=24.0, shelves=3, wall=5)]
        errors = room_layout_service.validate_fit(simple_room, specs)

        assert len(errors) == 1
        assert errors[0].error_type == "invalid_wall_reference"
        assert errors[0].wall_index is None
        assert "out of range" in errors[0].message

    def test_invalid_wall_name_reference(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Invalid wall name should report error."""
        specs = [SectionSpec(width=24.0, shelves=3, wall="nonexistent")]
        errors = room_layout_service.validate_fit(simple_room, specs)

        assert len(errors) == 1
        assert errors[0].error_type == "invalid_wall_reference"
        assert errors[0].wall_index is None
        assert "not found" in errors[0].message

    def test_negative_wall_index(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Negative wall index should report error."""
        specs = [SectionSpec(width=24.0, shelves=3, wall=-1)]
        errors = room_layout_service.validate_fit(simple_room, specs)

        assert len(errors) == 1
        assert errors[0].error_type == "invalid_wall_reference"

    def test_fill_section_no_remaining_space(
        self, room_layout_service: RoomLayoutService, simple_room: Room
    ) -> None:
        """Fill section with no remaining space should report error."""
        # Wall is 120 inches, fixed = 120, fill gets 0
        specs = [
            SectionSpec(width=120.0, shelves=3),
            SectionSpec(width="fill", shelves=2),
        ]
        errors = room_layout_service.validate_fit(simple_room, specs)

        assert len(errors) == 1
        assert errors[0].error_type == "exceeds_length"
        assert "zero or negative" in errors[0].message.lower()

    def test_multiple_walls_with_errors(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Errors on multiple walls should all be reported."""
        # Wall 0 is 120 inches, wall 1 is 80 inches
        specs = [
            SectionSpec(width=150.0, shelves=3, wall=0),  # Exceeds wall 0
            SectionSpec(width=100.0, shelves=4, wall=1),  # Exceeds wall 1
        ]
        errors = room_layout_service.validate_fit(l_shaped_room, specs)

        assert len(errors) == 2
        wall_indices = {e.wall_index for e in errors}
        assert wall_indices == {0, 1}

    def test_mixed_valid_and_invalid_walls(
        self, room_layout_service: RoomLayoutService, l_shaped_room: Room
    ) -> None:
        """Valid sections on one wall and invalid on another."""
        # Wall 0 is 120 inches, wall 1 is 80 inches
        specs = [
            SectionSpec(width=60.0, shelves=3, wall=0),   # Valid on wall 0
            SectionSpec(width=100.0, shelves=4, wall=1),  # Exceeds wall 1
        ]
        errors = room_layout_service.validate_fit(l_shaped_room, specs)

        assert len(errors) == 1
        assert errors[0].wall_index == 1
        assert errors[0].error_type == "exceeds_length"

    def test_sections_across_all_walls(
        self, room_layout_service: RoomLayoutService, rectangular_room: Room
    ) -> None:
        """Sections on all walls of rectangular room."""
        specs = [
            SectionSpec(width=48.0, shelves=3, wall="south"),
            SectionSpec(width=40.0, shelves=4, wall="west"),
            SectionSpec(width=48.0, shelves=3, wall="north"),
            SectionSpec(width=40.0, shelves=4, wall="east"),
        ]
        errors = room_layout_service.validate_fit(rectangular_room, specs)
        assert errors == []


class TestResolveWallIndex:
    """Tests for _resolve_wall_index private method."""

    def test_none_returns_zero(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """None wall reference should return 0."""
        result = room_layout_service._resolve_wall_index(None, 3, {})
        assert result == 0

    def test_valid_index(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Valid wall index should be returned as-is."""
        result = room_layout_service._resolve_wall_index(2, 3, {})
        assert result == 2

    def test_index_out_of_range(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Index out of range should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            room_layout_service._resolve_wall_index(5, 3, {})
        assert "out of range" in str(exc_info.value)

    def test_negative_index(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Negative index should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            room_layout_service._resolve_wall_index(-1, 3, {})
        assert "out of range" in str(exc_info.value)

    def test_valid_name(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Valid wall name should return corresponding index."""
        name_map = {"north": 0, "south": 1, "east": 2}
        result = room_layout_service._resolve_wall_index("south", 3, name_map)
        assert result == 1

    def test_invalid_name(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Invalid wall name should raise ValueError."""
        name_map = {"north": 0, "south": 1}
        with pytest.raises(ValueError) as exc_info:
            room_layout_service._resolve_wall_index("west", 3, name_map)
        assert "not found" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_kitchen_cabinet_layout(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Test a realistic kitchen cabinet layout scenario."""
        # 12x10 foot kitchen
        walls = [
            WallSegment(length=144.0, height=96.0, angle=0, name="south"),
            WallSegment(length=120.0, height=96.0, angle=90, name="west"),
        ]
        room = Room(name="kitchen", walls=walls)

        # Cabinet sections: base cabinets on south wall
        specs = [
            SectionSpec(width=24.0, shelves=2, wall="south"),  # Base cabinet 1
            SectionSpec(width=36.0, shelves=3, wall="south"),  # Base cabinet 2
            SectionSpec(width="fill", shelves=2, wall="south"),  # Fill remaining
            SectionSpec(width=30.0, shelves=2, wall="west"),   # West wall cabinet
        ]

        # Validate fit
        errors = room_layout_service.validate_fit(room, specs)
        assert errors == []

        # Assign sections
        assignments = room_layout_service.assign_sections_to_walls(room, specs)
        assert len(assignments) == 4

        # Compute transforms
        transforms = room_layout_service.compute_section_transforms(
            room, assignments, specs
        )
        assert len(transforms) == 4

        # Verify south wall cabinets
        south_transforms = [t for t in transforms if t.wall_index == 0]
        assert len(south_transforms) == 3
        assert all(t.rotation_z == pytest.approx(0.0) for t in south_transforms)

        # Verify west wall cabinet
        west_transforms = [t for t in transforms if t.wall_index == 1]
        assert len(west_transforms) == 1
        assert west_transforms[0].rotation_z == pytest.approx(270.0)

    def test_closet_built_in(
        self, room_layout_service: RoomLayoutService
    ) -> None:
        """Test a closet built-in cabinet scenario."""
        # Simple 6 foot closet alcove
        walls = [WallSegment(length=72.0, height=96.0, angle=0, name="back")]
        room = Room(name="closet", walls=[walls[0]])

        # Three equal sections filling the closet
        specs = [
            SectionSpec(width="fill", shelves=5),
            SectionSpec(width="fill", shelves=5),
            SectionSpec(width="fill", shelves=5),
        ]

        errors = room_layout_service.validate_fit(room, specs)
        assert errors == []

        assignments = room_layout_service.assign_sections_to_walls(room, specs)
        assert len(assignments) == 3

        # Each section should be 24 inches (72 / 3)
        # Offsets should be 0, 24, 48
        assert assignments[0].offset_along_wall == pytest.approx(0.0)
        assert assignments[1].offset_along_wall == pytest.approx(24.0)
        assert assignments[2].offset_along_wall == pytest.approx(48.0)
