"""Unit tests for RoomPanel3DMapper.

These tests verify:
- Mapping multiple cabinets to transformed 3D bounding boxes
- Applying rotation and translation transforms correctly
- Handling edge cases like empty inputs and mismatched lengths
"""

import math

import pytest

from cabinets.domain.entities import Cabinet
from cabinets.domain.services import Panel3DMapper, RoomPanel3DMapper
from cabinets.domain.value_objects import (
    BoundingBox3D,
    MaterialSpec,
    Position3D,
    SectionTransform,
)


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Standard 3/4 inch plywood."""
    return MaterialSpec.standard_3_4()


@pytest.fixture
def back_material() -> MaterialSpec:
    """Standard 1/2 inch plywood for backs."""
    return MaterialSpec.standard_1_2()


@pytest.fixture
def simple_cabinet(standard_material: MaterialSpec, back_material: MaterialSpec) -> Cabinet:
    """Create a simple cabinet for testing."""
    return Cabinet(
        width=24.0,
        height=30.0,
        depth=12.0,
        material=standard_material,
        back_material=back_material,
    )


@pytest.fixture
def room_mapper() -> RoomPanel3DMapper:
    """Create a RoomPanel3DMapper instance for testing."""
    return RoomPanel3DMapper()


class TestRoomPanel3DMapperInit:
    """Tests for RoomPanel3DMapper initialization."""

    def test_init_without_panel_mapper(self) -> None:
        """Should initialize without a panel mapper."""
        mapper = RoomPanel3DMapper()
        assert mapper._panel_mapper is None

    def test_init_with_panel_mapper(self, simple_cabinet: Cabinet) -> None:
        """Should initialize with provided panel mapper."""
        panel_mapper = Panel3DMapper(simple_cabinet)
        mapper = RoomPanel3DMapper(panel_mapper=panel_mapper)
        assert mapper._panel_mapper is panel_mapper


class TestMapCabinetsToBoxes:
    """Tests for map_cabinets_to_boxes method."""

    def test_empty_inputs(self, room_mapper: RoomPanel3DMapper) -> None:
        """Empty cabinets and transforms should return empty list."""
        result = room_mapper.map_cabinets_to_boxes([], [])
        assert result == []

    def test_mismatched_lengths_raises_error(
        self, room_mapper: RoomPanel3DMapper, simple_cabinet: Cabinet
    ) -> None:
        """Mismatched cabinets and transforms lengths should raise ValueError."""
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=0.0, y=0.0, z=0.0),
            rotation_z=0.0,
        )

        with pytest.raises(ValueError) as exc_info:
            room_mapper.map_cabinets_to_boxes([simple_cabinet], [transform, transform])
        assert "must match" in str(exc_info.value)

    def test_single_cabinet_no_transform(
        self, room_mapper: RoomPanel3DMapper, simple_cabinet: Cabinet
    ) -> None:
        """Single cabinet with identity transform should return untransformed boxes."""
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=0.0, y=0.0, z=0.0),
            rotation_z=0.0,
        )

        result = room_mapper.map_cabinets_to_boxes([simple_cabinet], [transform])

        # Should have panels: top, bottom, left, right, back
        # (no sections/shelves in simple cabinet)
        assert len(result) == 5

        # All boxes should still be at origin area (no rotation, no translation)
        for box in result:
            assert box.origin.x >= 0
            assert box.origin.y >= 0
            assert box.origin.z >= 0

    def test_single_cabinet_with_translation(
        self, room_mapper: RoomPanel3DMapper, simple_cabinet: Cabinet
    ) -> None:
        """Single cabinet with translation should offset all boxes."""
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=50.0, y=30.0, z=0.0),
            rotation_z=0.0,
        )

        result = room_mapper.map_cabinets_to_boxes([simple_cabinet], [transform])

        # All boxes should be translated
        for box in result:
            # With no rotation, minimum x should be at least 50
            assert box.origin.x >= 50.0
            # With no rotation, minimum y should be at least 30
            assert box.origin.y >= 30.0

    def test_single_cabinet_with_90_degree_rotation(
        self, room_mapper: RoomPanel3DMapper, simple_cabinet: Cabinet
    ) -> None:
        """Single cabinet with 90 degree rotation should rotate all boxes.

        Note: When rotating from origin, negative coordinates are clamped to 0.
        To properly test rotation, we translate first to ensure all results
        are in positive coordinate space.
        """
        # Use a translation that ensures all rotated coordinates stay positive
        # Cabinet is 24x12 (width x depth), so we need at least 24 units of Y offset
        # to keep all coordinates positive after 90 degree rotation
        identity_transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=30.0, y=30.0, z=0.0),
            rotation_z=0.0,
        )
        unrotated_boxes = room_mapper.map_cabinets_to_boxes(
            [simple_cabinet], [identity_transform]
        )

        # Now rotate 90 degrees with same translation offset
        rotate_transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=30.0, y=30.0, z=0.0),
            rotation_z=90.0,
        )
        rotated_boxes = room_mapper.map_cabinets_to_boxes(
            [simple_cabinet], [rotate_transform]
        )

        # Should have same number of boxes
        assert len(rotated_boxes) == len(unrotated_boxes)

        # After 90 degree rotation, X and Y dimensions swap
        # (within tolerance for floating point)
        for unrotated, rotated in zip(unrotated_boxes, rotated_boxes):
            # Z dimension should be unchanged
            assert rotated.size_z == pytest.approx(unrotated.size_z, rel=1e-9)
            # X and Y dimensions should be swapped (approximately)
            assert rotated.size_x == pytest.approx(unrotated.size_y, rel=1e-9)
            assert rotated.size_y == pytest.approx(unrotated.size_x, rel=1e-9)

    def test_multiple_cabinets_with_different_transforms(
        self,
        room_mapper: RoomPanel3DMapper,
        standard_material: MaterialSpec,
        back_material: MaterialSpec,
    ) -> None:
        """Multiple cabinets with different transforms should all be transformed."""
        cabinet1 = Cabinet(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=standard_material,
            back_material=back_material,
        )
        cabinet2 = Cabinet(
            width=36.0,
            height=30.0,
            depth=12.0,
            material=standard_material,
            back_material=back_material,
        )

        transforms = [
            SectionTransform(
                section_index=0,
                wall_index=0,
                position=Position3D(x=0.0, y=0.0, z=0.0),
                rotation_z=0.0,
            ),
            SectionTransform(
                section_index=1,
                wall_index=0,
                position=Position3D(x=50.0, y=0.0, z=0.0),
                rotation_z=0.0,
            ),
        ]

        result = room_mapper.map_cabinets_to_boxes([cabinet1, cabinet2], transforms)

        # 5 panels per cabinet = 10 total boxes
        assert len(result) == 10

    def test_270_degree_rotation_equivalent_to_minus_90(
        self, room_mapper: RoomPanel3DMapper, simple_cabinet: Cabinet
    ) -> None:
        """270 degree rotation should produce same result as -90 degrees.

        Use sufficient translation to keep all coordinates positive.
        """
        # Use enough translation to keep all coordinates positive after rotation
        transform_270 = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=50.0, y=50.0, z=0.0),
            rotation_z=270.0,
        )
        transform_neg90 = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=50.0, y=50.0, z=0.0),
            rotation_z=-90.0,
        )

        result_270 = room_mapper.map_cabinets_to_boxes([simple_cabinet], [transform_270])
        result_neg90 = room_mapper.map_cabinets_to_boxes([simple_cabinet], [transform_neg90])

        assert len(result_270) == len(result_neg90)
        for box_270, box_neg90 in zip(result_270, result_neg90):
            assert box_270.origin.x == pytest.approx(box_neg90.origin.x, abs=1e-9)
            assert box_270.origin.y == pytest.approx(box_neg90.origin.y, abs=1e-9)
            assert box_270.origin.z == pytest.approx(box_neg90.origin.z, abs=1e-9)
            assert box_270.size_x == pytest.approx(box_neg90.size_x, abs=1e-9)
            assert box_270.size_y == pytest.approx(box_neg90.size_y, abs=1e-9)
            assert box_270.size_z == pytest.approx(box_neg90.size_z, abs=1e-9)


class TestApplyTransform:
    """Tests for _apply_transform private method."""

    def test_identity_transform(self, room_mapper: RoomPanel3DMapper) -> None:
        """Identity transform should not change the box."""
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=0.0, y=0.0, z=0.0),
            rotation_z=0.0,
        )

        result = room_mapper._apply_transform(box, transform)

        assert result.origin.x == pytest.approx(0.0)
        assert result.origin.y == pytest.approx(0.0)
        assert result.origin.z == pytest.approx(0.0)
        assert result.size_x == pytest.approx(10.0)
        assert result.size_y == pytest.approx(5.0)
        assert result.size_z == pytest.approx(3.0)

    def test_translation_only(self, room_mapper: RoomPanel3DMapper) -> None:
        """Translation should offset the box origin."""
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=20.0, y=15.0, z=5.0),
            rotation_z=0.0,
        )

        result = room_mapper._apply_transform(box, transform)

        assert result.origin.x == pytest.approx(20.0)
        assert result.origin.y == pytest.approx(15.0)
        assert result.origin.z == pytest.approx(5.0)
        # Dimensions should not change
        assert result.size_x == pytest.approx(10.0)
        assert result.size_y == pytest.approx(5.0)
        assert result.size_z == pytest.approx(3.0)

    def test_90_degree_rotation(self, room_mapper: RoomPanel3DMapper) -> None:
        """90 degree rotation should swap X and Y dimensions.

        Use translation to keep coordinates positive.
        """
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        # Translate enough to keep all coordinates positive after rotation
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=15.0, y=15.0, z=0.0),
            rotation_z=90.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # After 90 degree rotation, dimensions swap
        assert result.size_x == pytest.approx(5.0)
        assert result.size_y == pytest.approx(10.0)
        assert result.size_z == pytest.approx(3.0)

    def test_180_degree_rotation(self, room_mapper: RoomPanel3DMapper) -> None:
        """180 degree rotation should keep dimensions but change origin.

        Use translation to keep coordinates positive.
        """
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        # Translate enough to keep all coordinates positive after 180 rotation
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=15.0, y=10.0, z=0.0),
            rotation_z=180.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # Dimensions should be preserved
        assert result.size_x == pytest.approx(10.0)
        assert result.size_y == pytest.approx(5.0)
        assert result.size_z == pytest.approx(3.0)

    def test_45_degree_rotation(self, room_mapper: RoomPanel3DMapper) -> None:
        """45 degree rotation should create larger bounding box.

        Use translation to keep coordinates positive.
        """
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=10.0,
            size_z=3.0,
        )
        # Translate enough to keep all coordinates positive after 45 degree rotation
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=20.0, y=20.0, z=0.0),
            rotation_z=45.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # For a square rotated 45 degrees, the bounding box diagonal becomes the side
        # Expected size: 10 * sqrt(2) = 14.14...
        expected_size = 10.0 * math.sqrt(2)
        assert result.size_x == pytest.approx(expected_size, rel=1e-9)
        assert result.size_y == pytest.approx(expected_size, rel=1e-9)
        assert result.size_z == pytest.approx(3.0)

    def test_rotation_with_offset_origin(self, room_mapper: RoomPanel3DMapper) -> None:
        """Rotation with non-zero origin should rotate around world origin.

        Note: Negative coordinates are clamped to 0, so we translate to keep
        coordinates positive.
        """
        box = BoundingBox3D(
            origin=Position3D(x=10.0, y=0.0, z=0.0),
            size_x=5.0,
            size_y=5.0,
            size_z=3.0,
        )
        # Translate to keep all coordinates positive after rotation
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=10.0, y=0.0, z=0.0),
            rotation_z=90.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # After 90 degree rotation around world origin:
        # Original corners at z=0: (10,0), (15,0), (15,5), (10,5)
        # After rotation: (0,10), (0,15), (-5,15), (-5,10)
        # After translation (+10, 0): (10,10), (10,15), (5,15), (5,10)
        # Min/max: x=[5,10], y=[10,15]
        assert result.origin.x == pytest.approx(5.0, abs=1e-9)
        assert result.origin.y == pytest.approx(10.0, abs=1e-9)

    def test_combined_rotation_and_translation(
        self, room_mapper: RoomPanel3DMapper
    ) -> None:
        """Combined rotation and translation should apply rotation first."""
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=100.0, y=50.0, z=10.0),
            rotation_z=90.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # After 90 degree rotation, dimensions swap
        assert result.size_x == pytest.approx(5.0)
        assert result.size_y == pytest.approx(10.0)
        # Translation is applied after rotation
        assert result.origin.x >= 95.0  # 100 - 5 (new x dimension)
        assert result.origin.y >= 50.0  # Translation applied

    def test_z_position_preserved(self, room_mapper: RoomPanel3DMapper) -> None:
        """Z position should be preserved through rotation.

        Use translation to keep coordinates positive.
        """
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=5.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        # Translate enough in X/Y to keep coordinates positive after rotation
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=15.0, y=15.0, z=10.0),
            rotation_z=90.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # Z should be original (5) + translation (10) = 15
        assert result.origin.z == pytest.approx(15.0)
        # Z dimension unchanged
        assert result.size_z == pytest.approx(3.0)


class TestCoordinateClamping:
    """Tests for coordinate clamping behavior.

    The RoomPanel3DMapper clamps negative coordinates to 0 because
    Position3D requires non-negative values. This is necessary when
    rotations produce negative coordinates (e.g., rotating around origin).
    """

    def test_negative_coordinates_clamped_to_zero(
        self, room_mapper: RoomPanel3DMapper
    ) -> None:
        """Negative coordinates from rotation should be clamped to 0."""
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=5.0,
            size_z=3.0,
        )
        # Rotate 90 degrees without translation - this will produce negative Y
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=0.0, y=0.0, z=0.0),
            rotation_z=90.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # Origin should be clamped to 0 (negative values become 0)
        assert result.origin.x >= 0.0
        assert result.origin.y >= 0.0
        assert result.origin.z >= 0.0

    def test_floating_point_near_zero_clamped(
        self, room_mapper: RoomPanel3DMapper
    ) -> None:
        """Very small negative values from floating point should be clamped."""
        box = BoundingBox3D(
            origin=Position3D(x=0.0, y=0.0, z=0.0),
            size_x=10.0,
            size_y=10.0,
            size_z=3.0,
        )
        # 360 degree rotation should return to origin, but floating point
        # may produce very small negative numbers like -1e-15
        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=0.0, y=0.0, z=0.0),
            rotation_z=360.0,
        )

        result = room_mapper._apply_transform(box, transform)

        # Should be clamped to exactly 0, not a tiny negative
        assert result.origin.x == pytest.approx(0.0, abs=1e-9)
        assert result.origin.y == pytest.approx(0.0, abs=1e-9)
        assert result.origin.z == pytest.approx(0.0, abs=1e-9)


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_l_shaped_room_cabinets(
        self,
        room_mapper: RoomPanel3DMapper,
        standard_material: MaterialSpec,
        back_material: MaterialSpec,
    ) -> None:
        """Test cabinets on two perpendicular walls.

        Uses realistic positions that would come from RoomLayoutService,
        ensuring all coordinates remain positive.
        """
        # Cabinet on first wall (along X axis)
        cabinet1 = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=standard_material,
            back_material=back_material,
        )
        # Cabinet on second wall (perpendicular, 270 degrees)
        cabinet2 = Cabinet(
            width=36.0,
            height=30.0,
            depth=12.0,
            material=standard_material,
            back_material=back_material,
        )

        # Use positions that keep all coordinates positive
        # The second cabinet is positioned after the first wall ends
        transforms = [
            SectionTransform(
                section_index=0,
                wall_index=0,
                position=Position3D(x=0.0, y=12.0, z=0.0),  # Offset for depth
                rotation_z=0.0,
            ),
            SectionTransform(
                section_index=1,
                wall_index=1,
                position=Position3D(x=48.0, y=50.0, z=0.0),  # Positioned to stay positive
                rotation_z=270.0,
            ),
        ]

        result = room_mapper.map_cabinets_to_boxes([cabinet1, cabinet2], transforms)

        # 5 panels each = 10 total
        assert len(result) == 10

        # All boxes should have valid coordinates
        for box in result:
            assert box.origin.x >= 0
            assert box.origin.y >= 0
            assert box.origin.z >= 0

    def test_cabinet_with_sections_and_shelves(
        self,
        room_mapper: RoomPanel3DMapper,
        standard_material: MaterialSpec,
        back_material: MaterialSpec,
    ) -> None:
        """Test that cabinets with sections and shelves are properly transformed."""
        from cabinets.domain.entities import Section, Shelf
        from cabinets.domain.value_objects import Position

        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=standard_material,
            back_material=back_material,
        )

        # Add a section with shelves
        section = Section(
            width=46.5,  # Interior width
            height=28.5,  # Interior height
            depth=11.5,  # Interior depth
            position=Position(0.75, 0.75),  # After material thickness
        )
        shelf = Shelf(
            width=46.5,
            depth=11.5,
            material=standard_material,
            position=Position(0.75, 15.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=10.0, y=5.0, z=0.0),
            rotation_z=0.0,
        )

        result = room_mapper.map_cabinets_to_boxes([cabinet], [transform])

        # 5 structural panels + 1 shelf = 6 boxes
        assert len(result) == 6

        # All should be translated
        for box in result:
            assert box.origin.x >= 10.0
            assert box.origin.y >= 5.0

    def test_full_360_degree_rotation_returns_to_original(
        self, room_mapper: RoomPanel3DMapper, simple_cabinet: Cabinet
    ) -> None:
        """360 degree rotation should return to original positions.

        Use translation to keep coordinates positive and comparable.
        """
        # Use a translation that keeps all coordinates positive
        identity_transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=50.0, y=50.0, z=0.0),
            rotation_z=0.0,
        )
        full_rotation_transform = SectionTransform(
            section_index=0,
            wall_index=0,
            position=Position3D(x=50.0, y=50.0, z=0.0),
            rotation_z=360.0,
        )

        original = room_mapper.map_cabinets_to_boxes([simple_cabinet], [identity_transform])
        rotated = room_mapper.map_cabinets_to_boxes([simple_cabinet], [full_rotation_transform])

        assert len(original) == len(rotated)
        for orig, rot in zip(original, rotated):
            assert orig.origin.x == pytest.approx(rot.origin.x, abs=1e-9)
            assert orig.origin.y == pytest.approx(rot.origin.y, abs=1e-9)
            assert orig.origin.z == pytest.approx(rot.origin.z, abs=1e-9)
            assert orig.size_x == pytest.approx(rot.size_x, abs=1e-9)
            assert orig.size_y == pytest.approx(rot.size_y, abs=1e-9)
            assert orig.size_z == pytest.approx(rot.size_z, abs=1e-9)
