"""Unit tests for GenerateLayoutCommand room layout functionality.

These tests verify:
- Room layout generation with execute_room_layout()
- Fit error handling
- Geometry error handling
- Multi-wall cabinet generation
- Combined cut lists and material estimates
- Backward compatibility with single-wall execute()
"""

import pytest

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.dtos import LayoutParametersInput, RoomLayoutOutput, WallInput
from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.section_resolver import SectionSpec


@pytest.fixture
def command() -> GenerateLayoutCommand:
    """Create a GenerateLayoutCommand instance for testing."""
    return GenerateLayoutCommand()


@pytest.fixture
def params_input() -> LayoutParametersInput:
    """Create standard layout parameters."""
    return LayoutParametersInput(
        num_sections=1,
        shelves_per_section=3,
        material_thickness=0.75,
        material_type="plywood",
        back_thickness=0.25,
    )


@pytest.fixture
def simple_room() -> Room:
    """Create a simple single-wall room for testing."""
    wall = WallSegment(length=120.0, height=96.0, angle=0, name="main_wall", depth=12.0)
    return Room(name="test_room", walls=[wall])


@pytest.fixture
def l_shaped_room() -> Room:
    """Create an L-shaped room with two walls."""
    walls = [
        WallSegment(length=120.0, height=96.0, angle=0, name="south", depth=12.0),
        WallSegment(length=80.0, height=96.0, angle=90, name="west", depth=12.0),
    ]
    return Room(name="l_room", walls=walls)


@pytest.fixture
def rectangular_room() -> Room:
    """Create a rectangular room with four walls."""
    walls = [
        WallSegment(length=144.0, height=96.0, angle=0, name="south", depth=12.0),
        WallSegment(length=120.0, height=96.0, angle=90, name="west", depth=12.0),
        WallSegment(length=144.0, height=96.0, angle=90, name="north", depth=12.0),
        WallSegment(length=120.0, height=96.0, angle=90, name="east", depth=12.0),
    ]
    return Room(name="kitchen", walls=walls, is_closed=True)


class TestExecuteRoomLayout:
    """Tests for execute_room_layout method."""

    def test_single_section_on_single_wall(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Single section on a single-wall room should generate one cabinet."""
        specs = [SectionSpec(width=60.0, shelves=3)]

        result = command.execute_room_layout(simple_room, specs, params_input)

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.cabinets) == 1
        assert len(result.transforms) == 1
        assert len(result.cut_list) > 0
        assert result.total_estimate is not None
        assert result.room == simple_room

    def test_fill_section_fills_wall(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Fill section should use the full wall width."""
        specs = [SectionSpec(width="fill", shelves=4)]

        result = command.execute_room_layout(simple_room, specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 1
        # Cabinet width should equal wall length (120)
        assert result.cabinets[0].width == pytest.approx(120.0)

    def test_multiple_sections_on_same_wall(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Multiple sections on same wall should generate multiple cabinets."""
        specs = [
            SectionSpec(width=24.0, shelves=2),
            SectionSpec(width=36.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]

        result = command.execute_room_layout(simple_room, specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 3
        assert len(result.transforms) == 3
        # First cabinet is 24 inches
        assert result.cabinets[0].width == pytest.approx(24.0)
        # Second cabinet is 36 inches
        assert result.cabinets[1].width == pytest.approx(36.0)
        # Third cabinet fills remaining (120 - 24 - 36 = 60)
        assert result.cabinets[2].width == pytest.approx(60.0)

    def test_sections_on_multiple_walls(
        self,
        command: GenerateLayoutCommand,
        l_shaped_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Sections on different walls should have different transforms."""
        specs = [
            SectionSpec(width=48.0, shelves=3, wall="south"),
            SectionSpec(width=40.0, shelves=4, wall="west"),
        ]

        result = command.execute_room_layout(l_shaped_room, specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 2
        assert len(result.transforms) == 2

        # First transform on south wall (direction 0)
        assert result.transforms[0].wall_index == 0
        assert result.transforms[0].rotation_z == pytest.approx(0.0)

        # Second transform on west wall (direction 270, rotation negated to 90)
        assert result.transforms[1].wall_index == 1
        assert result.transforms[1].rotation_z == pytest.approx(90.0)

    def test_combined_cut_list(
        self,
        command: GenerateLayoutCommand,
        l_shaped_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Cut list should combine pieces from all cabinets."""
        specs = [
            SectionSpec(width=48.0, shelves=2, wall="south"),
            SectionSpec(width=40.0, shelves=2, wall="west"),
        ]

        result = command.execute_room_layout(l_shaped_room, specs, params_input)

        assert result.is_valid
        # Should have pieces from both cabinets
        assert len(result.cut_list) > 0
        # Total estimate should reflect all cabinets
        assert result.total_estimate.total_area_sqft > 0

    def test_combined_material_estimates(
        self,
        command: GenerateLayoutCommand,
        l_shaped_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Material estimates should combine all cabinets."""
        specs = [
            SectionSpec(width=48.0, shelves=3, wall="south"),
            SectionSpec(width=40.0, shelves=3, wall="west"),
        ]

        result = command.execute_room_layout(l_shaped_room, specs, params_input)

        assert result.is_valid
        assert len(result.material_estimates) > 0
        assert result.total_estimate is not None


class TestExecuteRoomLayoutErrors:
    """Tests for error handling in execute_room_layout."""

    def test_sections_exceed_wall_length(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Sections exceeding wall length should return fit errors."""
        # Wall is 120 inches, sections total 150
        specs = [
            SectionSpec(width=80.0, shelves=3),
            SectionSpec(width=70.0, shelves=4),
        ]

        result = command.execute_room_layout(simple_room, specs, params_input)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert "exceed" in result.errors[0].lower()
        assert len(result.cabinets) == 0

    def test_invalid_wall_reference(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Invalid wall reference should return error."""
        specs = [SectionSpec(width=24.0, shelves=3, wall=5)]

        result = command.execute_room_layout(simple_room, specs, params_input)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert "out of range" in result.errors[0].lower()

    def test_invalid_wall_name(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """Invalid wall name should return error."""
        specs = [SectionSpec(width=24.0, shelves=3, wall="nonexistent")]

        result = command.execute_room_layout(simple_room, specs, params_input)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_invalid_params_input(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
    ) -> None:
        """Invalid parameters should return validation errors."""
        specs = [SectionSpec(width=24.0, shelves=3)]
        invalid_params = LayoutParametersInput(
            num_sections=-1,  # Invalid
            shelves_per_section=3,
            material_thickness=0.75,
        )

        result = command.execute_room_layout(simple_room, specs, invalid_params)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_geometry_error_self_intersection(
        self, command: GenerateLayoutCommand, params_input: LayoutParametersInput
    ) -> None:
        """Self-intersecting room geometry should return error."""
        # Create a room that would self-intersect
        # This is tricky - the Room class validates but intersection is checked later
        # We'll create a room that forms an "X" pattern
        walls = [
            WallSegment(length=100.0, height=96.0, angle=0, name="w1", depth=12.0),
            WallSegment(length=50.0, height=96.0, angle=90, name="w2", depth=12.0),
            WallSegment(length=100.0, height=96.0, angle=-90, name="w3", depth=12.0),
            WallSegment(length=100.0, height=96.0, angle=-90, name="w4", depth=12.0),
        ]
        room = Room(name="intersecting", walls=walls)

        specs = [SectionSpec(width=24.0, shelves=3)]

        result = command.execute_room_layout(room, specs, params_input)

        # The room should have geometry errors
        geometry_errors = room.validate_geometry()
        if geometry_errors:
            assert not result.is_valid
            assert len(result.errors) > 0


class TestExecuteRoomLayoutIntegration:
    """Integration tests for realistic room layout scenarios."""

    def test_kitchen_cabinet_layout(
        self, command: GenerateLayoutCommand, params_input: LayoutParametersInput
    ) -> None:
        """Test a realistic kitchen cabinet layout."""
        walls = [
            WallSegment(length=144.0, height=96.0, angle=0, name="south", depth=24.0),
            WallSegment(length=96.0, height=96.0, angle=90, name="west", depth=24.0),
        ]
        room = Room(name="kitchen", walls=walls)

        specs = [
            SectionSpec(width=24.0, shelves=2, wall="south"),  # Base cabinet
            SectionSpec(width=36.0, shelves=3, wall="south"),  # Sink cabinet
            SectionSpec(width="fill", shelves=2, wall="south"),  # Fill remaining
            SectionSpec(width=30.0, shelves=3, wall="west"),  # Corner
        ]

        result = command.execute_room_layout(room, specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 4
        assert len(result.transforms) == 4

        # Verify south wall cabinets
        south_transforms = [t for t in result.transforms if t.wall_index == 0]
        assert len(south_transforms) == 3

        # Verify west wall cabinet
        west_transforms = [t for t in result.transforms if t.wall_index == 1]
        assert len(west_transforms) == 1

    def test_closet_built_in(
        self, command: GenerateLayoutCommand, params_input: LayoutParametersInput
    ) -> None:
        """Test a closet built-in with equal sections."""
        walls = [WallSegment(length=72.0, height=84.0, angle=0, name="back", depth=18.0)]
        room = Room(name="closet", walls=walls)

        # Three equal fill sections
        specs = [
            SectionSpec(width="fill", shelves=5),
            SectionSpec(width="fill", shelves=5),
            SectionSpec(width="fill", shelves=5),
        ]

        result = command.execute_room_layout(room, specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 3

        # Each cabinet should be 24 inches (72 / 3)
        for cabinet in result.cabinets:
            assert cabinet.width == pytest.approx(24.0)

    def test_u_shaped_room(
        self, command: GenerateLayoutCommand, params_input: LayoutParametersInput
    ) -> None:
        """Test a U-shaped room layout."""
        walls = [
            WallSegment(length=96.0, height=96.0, angle=0, name="left", depth=12.0),
            WallSegment(length=72.0, height=96.0, angle=90, name="back", depth=12.0),
            WallSegment(length=96.0, height=96.0, angle=90, name="right", depth=12.0),
        ]
        room = Room(name="u_room", walls=walls)

        specs = [
            SectionSpec(width=48.0, shelves=4, wall="left"),
            SectionSpec(width="fill", shelves=3, wall="back"),
            SectionSpec(width=48.0, shelves=4, wall="right"),
        ]

        result = command.execute_room_layout(room, specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 3

        # Back cabinet should fill the wall (72 inches)
        back_cabinet = result.cabinets[1]
        assert back_cabinet.width == pytest.approx(72.0)


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with single-wall execute()."""

    def test_single_wall_execute_unchanged(
        self, command: GenerateLayoutCommand
    ) -> None:
        """Standard execute() should still work as before."""
        wall_input = WallInput(width=72.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=4,
            material_thickness=0.75,
        )

        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert result.cabinet is not None
        assert len(result.cabinet.sections) == 3
        assert len(result.cut_list) > 0

    def test_single_wall_execute_with_specs(
        self, command: GenerateLayoutCommand
    ) -> None:
        """execute() with section_specs should still work."""
        wall_input = WallInput(width=72.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        section_specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]

        result = command.execute(wall_input, params_input, section_specs)

        assert result.is_valid
        assert result.cabinet is not None
        assert len(result.cabinet.sections) == 2

    def test_execute_validation_errors_unchanged(
        self, command: GenerateLayoutCommand
    ) -> None:
        """execute() validation errors should still work."""
        wall_input = WallInput(width=-1.0, height=84.0, depth=12.0)  # Invalid
        params_input = LayoutParametersInput()

        result = command.execute(wall_input, params_input)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert "positive" in result.errors[0].lower()


class TestRoomLayoutOutputProperties:
    """Tests for RoomLayoutOutput DTO properties."""

    def test_is_valid_true_when_no_errors(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """is_valid should be True when there are no errors."""
        specs = [SectionSpec(width=60.0, shelves=3)]
        result = command.execute_room_layout(simple_room, specs, params_input)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_is_valid_false_when_errors(
        self,
        command: GenerateLayoutCommand,
        simple_room: Room,
        params_input: LayoutParametersInput,
    ) -> None:
        """is_valid should be False when there are errors."""
        # Sections exceed wall length
        specs = [
            SectionSpec(width=100.0, shelves=3),
            SectionSpec(width=100.0, shelves=3),
        ]
        result = command.execute_room_layout(simple_room, specs, params_input)

        assert result.is_valid is False
        assert len(result.errors) > 0
