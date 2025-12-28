"""Unit tests for obstacle definition and avoidance.

These tests verify:
- ObstacleType enum values
- Clearance creation and validation
- SectionBounds creation, validation, and properties
- ObstacleZone properties and overlap detection
- Obstacle entity creation, validation, and zone calculation
- CollisionResult and ValidRegion value objects
- DEFAULT_CLEARANCES constant
"""

import pytest

from cabinets.domain.entities import Obstacle
from cabinets.domain.value_objects import (
    Clearance,
    CollisionResult,
    DEFAULT_CLEARANCES,
    ObstacleType,
    ObstacleZone,
    SectionBounds,
    ValidRegion,
)


class TestObstacleType:
    """Tests for ObstacleType enum."""

    def test_obstacle_type_values(self) -> None:
        """ObstacleType should have all expected values."""
        assert ObstacleType.WINDOW.value == "window"
        assert ObstacleType.DOOR.value == "door"
        assert ObstacleType.OUTLET.value == "outlet"
        assert ObstacleType.SWITCH.value == "switch"
        assert ObstacleType.VENT.value == "vent"
        assert ObstacleType.SKYLIGHT.value == "skylight"
        assert ObstacleType.CUSTOM.value == "custom"

    def test_obstacle_type_count(self) -> None:
        """ObstacleType should have exactly 7 values."""
        assert len(ObstacleType) == 7


class TestClearance:
    """Tests for Clearance value object."""

    def test_default_clearance(self) -> None:
        """Default clearance should be zero on all sides."""
        clearance = Clearance()
        assert clearance.top == 0.0
        assert clearance.bottom == 0.0
        assert clearance.left == 0.0
        assert clearance.right == 0.0

    def test_custom_clearance(self) -> None:
        """Clearance should accept custom values."""
        clearance = Clearance(top=2.0, bottom=1.0, left=3.0, right=4.0)
        assert clearance.top == 2.0
        assert clearance.bottom == 1.0
        assert clearance.left == 3.0
        assert clearance.right == 4.0

    def test_clearance_is_frozen(self) -> None:
        """Clearance should be immutable."""
        clearance = Clearance(top=2.0)
        with pytest.raises(AttributeError):
            clearance.top = 5.0  # type: ignore

    def test_clearance_rejects_negative_top(self) -> None:
        """Clearance should reject negative top value."""
        with pytest.raises(ValueError) as exc_info:
            Clearance(top=-1.0)
        assert "non-negative" in str(exc_info.value)

    def test_clearance_rejects_negative_bottom(self) -> None:
        """Clearance should reject negative bottom value."""
        with pytest.raises(ValueError) as exc_info:
            Clearance(bottom=-1.0)
        assert "non-negative" in str(exc_info.value)

    def test_clearance_rejects_negative_left(self) -> None:
        """Clearance should reject negative left value."""
        with pytest.raises(ValueError) as exc_info:
            Clearance(left=-1.0)
        assert "non-negative" in str(exc_info.value)

    def test_clearance_rejects_negative_right(self) -> None:
        """Clearance should reject negative right value."""
        with pytest.raises(ValueError) as exc_info:
            Clearance(right=-1.0)
        assert "non-negative" in str(exc_info.value)

    def test_clearance_allows_zero(self) -> None:
        """Clearance should allow zero values."""
        clearance = Clearance(top=0.0, bottom=0.0, left=0.0, right=0.0)
        assert clearance.top == 0.0


class TestSectionBounds:
    """Tests for SectionBounds value object."""

    def test_valid_section_bounds(self) -> None:
        """Valid section bounds should be created successfully."""
        bounds = SectionBounds(left=10.0, right=50.0, bottom=0.0, top=80.0)
        assert bounds.left == 10.0
        assert bounds.right == 50.0
        assert bounds.bottom == 0.0
        assert bounds.top == 80.0

    def test_section_bounds_width_property(self) -> None:
        """SectionBounds width should be right - left."""
        bounds = SectionBounds(left=10.0, right=50.0, bottom=0.0, top=80.0)
        assert bounds.width == 40.0

    def test_section_bounds_height_property(self) -> None:
        """SectionBounds height should be top - bottom."""
        bounds = SectionBounds(left=10.0, right=50.0, bottom=0.0, top=80.0)
        assert bounds.height == 80.0

    def test_section_bounds_is_frozen(self) -> None:
        """SectionBounds should be immutable."""
        bounds = SectionBounds(left=10.0, right=50.0, bottom=0.0, top=80.0)
        with pytest.raises(AttributeError):
            bounds.left = 0.0  # type: ignore

    def test_section_bounds_rejects_right_less_than_left(self) -> None:
        """SectionBounds should reject right <= left."""
        with pytest.raises(ValueError) as exc_info:
            SectionBounds(left=50.0, right=10.0, bottom=0.0, top=80.0)
        assert "right must be greater than left" in str(exc_info.value)

    def test_section_bounds_rejects_right_equal_left(self) -> None:
        """SectionBounds should reject right == left."""
        with pytest.raises(ValueError) as exc_info:
            SectionBounds(left=10.0, right=10.0, bottom=0.0, top=80.0)
        assert "right must be greater than left" in str(exc_info.value)

    def test_section_bounds_rejects_top_less_than_bottom(self) -> None:
        """SectionBounds should reject top <= bottom."""
        with pytest.raises(ValueError) as exc_info:
            SectionBounds(left=10.0, right=50.0, bottom=80.0, top=0.0)
        assert "top must be greater than bottom" in str(exc_info.value)

    def test_section_bounds_rejects_top_equal_bottom(self) -> None:
        """SectionBounds should reject top == bottom."""
        with pytest.raises(ValueError) as exc_info:
            SectionBounds(left=10.0, right=50.0, bottom=40.0, top=40.0)
        assert "top must be greater than bottom" in str(exc_info.value)


class TestObstacle:
    """Tests for Obstacle entity."""

    def test_valid_obstacle_minimal(self) -> None:
        """Valid obstacle with required fields only."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        assert obstacle.obstacle_type == ObstacleType.WINDOW
        assert obstacle.wall_index == 0
        assert obstacle.horizontal_offset == 24.0
        assert obstacle.bottom == 36.0
        assert obstacle.width == 48.0
        assert obstacle.height == 36.0
        assert obstacle.clearance_override is None
        assert obstacle.name is None

    def test_valid_obstacle_full(self) -> None:
        """Valid obstacle with all fields specified."""
        custom_clearance = Clearance(top=3.0, bottom=3.0, left=3.0, right=3.0)
        obstacle = Obstacle(
            obstacle_type=ObstacleType.DOOR,
            wall_index=1,
            horizontal_offset=0.0,
            bottom=0.0,
            width=36.0,
            height=80.0,
            clearance_override=custom_clearance,
            name="entry_door",
        )
        assert obstacle.obstacle_type == ObstacleType.DOOR
        assert obstacle.wall_index == 1
        assert obstacle.clearance_override == custom_clearance
        assert obstacle.name == "entry_door"

    def test_obstacle_top_property(self) -> None:
        """Obstacle top should be bottom + height."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        assert obstacle.top == 72.0

    def test_obstacle_right_property(self) -> None:
        """Obstacle right should be horizontal_offset + width."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        assert obstacle.right == 72.0

    def test_obstacle_rejects_zero_width(self) -> None:
        """Obstacle should reject zero width."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=0,
                height=36.0,
            )
        assert "dimensions must be positive" in str(exc_info.value)

    def test_obstacle_rejects_negative_width(self) -> None:
        """Obstacle should reject negative width."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=-10.0,
                height=36.0,
            )
        assert "dimensions must be positive" in str(exc_info.value)

    def test_obstacle_rejects_zero_height(self) -> None:
        """Obstacle should reject zero height."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=0,
            )
        assert "dimensions must be positive" in str(exc_info.value)

    def test_obstacle_rejects_negative_height(self) -> None:
        """Obstacle should reject negative height."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=-5.0,
            )
        assert "dimensions must be positive" in str(exc_info.value)

    def test_obstacle_rejects_negative_horizontal_offset(self) -> None:
        """Obstacle should reject negative horizontal_offset."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=-5.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            )
        assert "position must be non-negative" in str(exc_info.value)

    def test_obstacle_rejects_negative_bottom(self) -> None:
        """Obstacle should reject negative bottom."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=24.0,
                bottom=-5.0,
                width=48.0,
                height=36.0,
            )
        assert "position must be non-negative" in str(exc_info.value)

    def test_obstacle_rejects_negative_wall_index(self) -> None:
        """Obstacle should reject negative wall_index."""
        with pytest.raises(ValueError) as exc_info:
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=-1,
                horizontal_offset=24.0,
                bottom=36.0,
                width=48.0,
                height=36.0,
            )
        assert "Wall index must be non-negative" in str(exc_info.value)

    def test_obstacle_allows_zero_offset_and_bottom(self) -> None:
        """Obstacle should allow zero offset and bottom (corner placement)."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.DOOR,
            wall_index=0,
            horizontal_offset=0.0,
            bottom=0.0,
            width=36.0,
            height=80.0,
        )
        assert obstacle.horizontal_offset == 0.0
        assert obstacle.bottom == 0.0


class TestObstacleGetClearance:
    """Tests for Obstacle.get_clearance method."""

    def test_get_clearance_with_override(self) -> None:
        """get_clearance should return override when specified."""
        custom_clearance = Clearance(top=5.0, bottom=5.0, left=5.0, right=5.0)
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
            clearance_override=custom_clearance,
        )
        result = obstacle.get_clearance(DEFAULT_CLEARANCES)
        assert result == custom_clearance

    def test_get_clearance_with_default(self) -> None:
        """get_clearance should return default when no override."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        result = obstacle.get_clearance(DEFAULT_CLEARANCES)
        assert result == DEFAULT_CLEARANCES[ObstacleType.WINDOW]

    def test_get_clearance_unknown_type_returns_zero(self) -> None:
        """get_clearance should return zero clearance for unknown type with empty defaults."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.CUSTOM,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        result = obstacle.get_clearance({})
        assert result == Clearance()


class TestObstacleGetZoneBounds:
    """Tests for Obstacle.get_zone_bounds method."""

    def test_get_zone_bounds_no_clearance(self) -> None:
        """get_zone_bounds with zero clearance should match obstacle bounds."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.OUTLET,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=4.0,
            height=4.0,
        )
        zone = obstacle.get_zone_bounds(Clearance())
        assert zone.left == 24.0
        assert zone.right == 28.0
        assert zone.bottom == 36.0
        assert zone.top == 40.0
        assert zone.obstacle is obstacle

    def test_get_zone_bounds_with_clearance(self) -> None:
        """get_zone_bounds should expand by clearance amounts."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        clearance = Clearance(top=2.0, bottom=2.0, left=2.0, right=2.0)
        zone = obstacle.get_zone_bounds(clearance)
        assert zone.left == 22.0  # 24 - 2
        assert zone.right == 74.0  # 24 + 48 + 2
        assert zone.bottom == 34.0  # 36 - 2
        assert zone.top == 74.0  # 36 + 36 + 2

    def test_get_zone_bounds_asymmetric_clearance(self) -> None:
        """get_zone_bounds should handle asymmetric clearance."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.DOOR,
            wall_index=0,
            horizontal_offset=0.0,
            bottom=0.0,
            width=36.0,
            height=80.0,
        )
        clearance = Clearance(top=0.0, bottom=0.0, left=2.0, right=2.0)
        zone = obstacle.get_zone_bounds(clearance)
        assert zone.left == -2.0  # 0 - 2 (can be negative)
        assert zone.right == 38.0  # 36 + 2
        assert zone.bottom == 0.0
        assert zone.top == 80.0


class TestObstacleZone:
    """Tests for ObstacleZone value object."""

    def _create_zone(
        self,
        left: float = 20.0,
        right: float = 70.0,
        bottom: float = 34.0,
        top: float = 74.0,
    ) -> ObstacleZone:
        """Helper to create an ObstacleZone with a dummy obstacle."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=22.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        return ObstacleZone(
            left=left, right=right, bottom=bottom, top=top, obstacle=obstacle
        )

    def test_zone_width_property(self) -> None:
        """ObstacleZone width should be right - left."""
        zone = self._create_zone(left=20.0, right=70.0)
        assert zone.width == 50.0

    def test_zone_height_property(self) -> None:
        """ObstacleZone height should be top - bottom."""
        zone = self._create_zone(bottom=34.0, top=74.0)
        assert zone.height == 40.0

    def test_zone_overlaps_fully_inside(self) -> None:
        """Overlaps should return True when section is inside zone."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=30.0, right=60.0, bottom=40.0, top=60.0)
        assert zone.overlaps(section) is True

    def test_zone_overlaps_fully_contains(self) -> None:
        """Overlaps should return True when section contains zone."""
        zone = self._create_zone(left=30.0, right=60.0, bottom=40.0, top=60.0)
        section = SectionBounds(left=20.0, right=70.0, bottom=34.0, top=74.0)
        assert zone.overlaps(section) is True

    def test_zone_overlaps_partial_right(self) -> None:
        """Overlaps should return True when section overlaps from right."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=60.0, right=100.0, bottom=40.0, top=60.0)
        assert zone.overlaps(section) is True

    def test_zone_overlaps_partial_left(self) -> None:
        """Overlaps should return True when section overlaps from left."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=0.0, right=30.0, bottom=40.0, top=60.0)
        assert zone.overlaps(section) is True

    def test_zone_overlaps_partial_top(self) -> None:
        """Overlaps should return True when section overlaps from top."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=30.0, right=60.0, bottom=60.0, top=90.0)
        assert zone.overlaps(section) is True

    def test_zone_overlaps_partial_bottom(self) -> None:
        """Overlaps should return True when section overlaps from bottom."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=30.0, right=60.0, bottom=0.0, top=50.0)
        assert zone.overlaps(section) is True

    def test_zone_no_overlap_left(self) -> None:
        """Overlaps should return False when section is entirely to the left."""
        zone = self._create_zone(left=50.0, right=100.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=0.0, right=50.0, bottom=34.0, top=74.0)
        assert zone.overlaps(section) is False

    def test_zone_no_overlap_right(self) -> None:
        """Overlaps should return False when section is entirely to the right."""
        zone = self._create_zone(left=0.0, right=50.0, bottom=34.0, top=74.0)
        section = SectionBounds(left=50.0, right=100.0, bottom=34.0, top=74.0)
        assert zone.overlaps(section) is False

    def test_zone_no_overlap_above(self) -> None:
        """Overlaps should return False when section is entirely above."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=0.0, top=40.0)
        section = SectionBounds(left=20.0, right=70.0, bottom=40.0, top=80.0)
        assert zone.overlaps(section) is False

    def test_zone_no_overlap_below(self) -> None:
        """Overlaps should return False when section is entirely below."""
        zone = self._create_zone(left=20.0, right=70.0, bottom=40.0, top=80.0)
        section = SectionBounds(left=20.0, right=70.0, bottom=0.0, top=40.0)
        assert zone.overlaps(section) is False

    def test_zone_no_overlap_corner(self) -> None:
        """Overlaps should return False when section touches corner only."""
        zone = self._create_zone(left=50.0, right=100.0, bottom=50.0, top=100.0)
        section = SectionBounds(left=0.0, right=50.0, bottom=0.0, top=50.0)
        assert zone.overlaps(section) is False


class TestCollisionResult:
    """Tests for CollisionResult value object."""

    def test_valid_collision_result(self) -> None:
        """Valid collision result should be created successfully."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        zone = ObstacleZone(left=22.0, right=74.0, bottom=34.0, top=74.0, obstacle=obstacle)
        result = CollisionResult(zone=zone, overlap_area=100.0)
        assert result.zone == zone
        assert result.overlap_area == 100.0

    def test_collision_result_is_frozen(self) -> None:
        """CollisionResult should be immutable."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        zone = ObstacleZone(left=22.0, right=74.0, bottom=34.0, top=74.0, obstacle=obstacle)
        result = CollisionResult(zone=zone, overlap_area=100.0)
        with pytest.raises(AttributeError):
            result.overlap_area = 200.0  # type: ignore

    def test_collision_result_rejects_negative_overlap(self) -> None:
        """CollisionResult should reject negative overlap_area."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        zone = ObstacleZone(left=22.0, right=74.0, bottom=34.0, top=74.0, obstacle=obstacle)
        with pytest.raises(ValueError) as exc_info:
            CollisionResult(zone=zone, overlap_area=-10.0)
        assert "non-negative" in str(exc_info.value)

    def test_collision_result_allows_zero_overlap(self) -> None:
        """CollisionResult should allow zero overlap_area."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        zone = ObstacleZone(left=22.0, right=74.0, bottom=34.0, top=74.0, obstacle=obstacle)
        result = CollisionResult(zone=zone, overlap_area=0.0)
        assert result.overlap_area == 0.0


class TestValidRegion:
    """Tests for ValidRegion value object."""

    def test_valid_region_full(self) -> None:
        """Valid region with 'full' type should be created successfully."""
        region = ValidRegion(left=0.0, right=120.0, bottom=0.0, top=96.0, region_type="full")
        assert region.left == 0.0
        assert region.right == 120.0
        assert region.bottom == 0.0
        assert region.top == 96.0
        assert region.region_type == "full"

    def test_valid_region_lower(self) -> None:
        """Valid region with 'lower' type should be created successfully."""
        region = ValidRegion(left=0.0, right=120.0, bottom=0.0, top=36.0, region_type="lower")
        assert region.region_type == "lower"

    def test_valid_region_upper(self) -> None:
        """Valid region with 'upper' type should be created successfully."""
        region = ValidRegion(left=0.0, right=120.0, bottom=72.0, top=96.0, region_type="upper")
        assert region.region_type == "upper"

    def test_valid_region_gap(self) -> None:
        """Valid region with 'gap' type should be created successfully."""
        region = ValidRegion(left=70.0, right=100.0, bottom=0.0, top=96.0, region_type="gap")
        assert region.region_type == "gap"

    def test_valid_region_width_property(self) -> None:
        """ValidRegion width should be right - left."""
        region = ValidRegion(left=10.0, right=50.0, bottom=0.0, top=96.0, region_type="full")
        assert region.width == 40.0

    def test_valid_region_height_property(self) -> None:
        """ValidRegion height should be top - bottom."""
        region = ValidRegion(left=0.0, right=120.0, bottom=10.0, top=80.0, region_type="full")
        assert region.height == 70.0

    def test_valid_region_is_frozen(self) -> None:
        """ValidRegion should be immutable."""
        region = ValidRegion(left=0.0, right=120.0, bottom=0.0, top=96.0, region_type="full")
        with pytest.raises(AttributeError):
            region.left = 10.0  # type: ignore

    def test_valid_region_rejects_invalid_type(self) -> None:
        """ValidRegion should reject invalid region_type."""
        with pytest.raises(ValueError) as exc_info:
            ValidRegion(left=0.0, right=120.0, bottom=0.0, top=96.0, region_type="invalid")
        assert "region_type must be one of" in str(exc_info.value)

    def test_valid_region_rejects_right_less_than_left(self) -> None:
        """ValidRegion should reject right <= left."""
        with pytest.raises(ValueError) as exc_info:
            ValidRegion(left=50.0, right=10.0, bottom=0.0, top=96.0, region_type="full")
        assert "right must be greater than left" in str(exc_info.value)

    def test_valid_region_rejects_top_less_than_bottom(self) -> None:
        """ValidRegion should reject top <= bottom."""
        with pytest.raises(ValueError) as exc_info:
            ValidRegion(left=0.0, right=120.0, bottom=96.0, top=0.0, region_type="full")
        assert "top must be greater than bottom" in str(exc_info.value)


class TestDefaultClearances:
    """Tests for DEFAULT_CLEARANCES constant."""

    def test_default_clearances_contains_all_types(self) -> None:
        """DEFAULT_CLEARANCES should have an entry for each ObstacleType."""
        for obstacle_type in ObstacleType:
            assert obstacle_type in DEFAULT_CLEARANCES

    def test_default_clearance_window(self) -> None:
        """Window should have 2-inch clearance on all sides."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.WINDOW]
        assert clearance.top == 2.0
        assert clearance.bottom == 2.0
        assert clearance.left == 2.0
        assert clearance.right == 2.0

    def test_default_clearance_door(self) -> None:
        """Door should have side clearance only."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.DOOR]
        assert clearance.top == 0.0
        assert clearance.bottom == 0.0
        assert clearance.left == 2.0
        assert clearance.right == 2.0

    def test_default_clearance_outlet(self) -> None:
        """Outlet should have no clearance."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.OUTLET]
        assert clearance.top == 0.0
        assert clearance.bottom == 0.0
        assert clearance.left == 0.0
        assert clearance.right == 0.0

    def test_default_clearance_switch(self) -> None:
        """Switch should have no clearance."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.SWITCH]
        assert clearance.top == 0.0
        assert clearance.bottom == 0.0
        assert clearance.left == 0.0
        assert clearance.right == 0.0

    def test_default_clearance_vent(self) -> None:
        """Vent should have 4-inch clearance on all sides."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.VENT]
        assert clearance.top == 4.0
        assert clearance.bottom == 4.0
        assert clearance.left == 4.0
        assert clearance.right == 4.0

    def test_default_clearance_skylight(self) -> None:
        """Skylight should have 2-inch clearance on all sides."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.SKYLIGHT]
        assert clearance.top == 2.0
        assert clearance.bottom == 2.0
        assert clearance.left == 2.0
        assert clearance.right == 2.0

    def test_default_clearance_custom(self) -> None:
        """Custom should have no clearance."""
        clearance = DEFAULT_CLEARANCES[ObstacleType.CUSTOM]
        assert clearance.top == 0.0
        assert clearance.bottom == 0.0
        assert clearance.left == 0.0
        assert clearance.right == 0.0


class TestObstacleIntegration:
    """Integration tests for obstacle and zone calculations."""

    def test_window_with_default_clearance_zone(self) -> None:
        """Window obstacle with default clearance should produce correct zone."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=24.0,
            bottom=36.0,
            width=48.0,
            height=36.0,
        )
        clearance = obstacle.get_clearance(DEFAULT_CLEARANCES)
        zone = obstacle.get_zone_bounds(clearance)

        # Window: 24-72 horizontal, 36-72 vertical
        # With 2" clearance: 22-74 horizontal, 34-74 vertical
        assert zone.left == 22.0
        assert zone.right == 74.0
        assert zone.bottom == 34.0
        assert zone.top == 74.0
        assert zone.width == 52.0
        assert zone.height == 40.0

    def test_door_with_default_clearance_zone(self) -> None:
        """Door obstacle with default clearance should produce correct zone."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.DOOR,
            wall_index=0,
            horizontal_offset=0.0,
            bottom=0.0,
            width=36.0,
            height=80.0,
        )
        clearance = obstacle.get_clearance(DEFAULT_CLEARANCES)
        zone = obstacle.get_zone_bounds(clearance)

        # Door: 0-36 horizontal, 0-80 vertical
        # With 2" side clearance only: -2 to 38 horizontal, 0-80 vertical
        assert zone.left == -2.0
        assert zone.right == 38.0
        assert zone.bottom == 0.0
        assert zone.top == 80.0

    def test_zone_overlap_with_cabinet_section(self) -> None:
        """Test zone overlap detection with realistic cabinet placement."""
        obstacle = Obstacle(
            obstacle_type=ObstacleType.WINDOW,
            wall_index=0,
            horizontal_offset=48.0,
            bottom=36.0,
            width=36.0,
            height=36.0,
            name="kitchen_window",
        )
        clearance = obstacle.get_clearance(DEFAULT_CLEARANCES)
        zone = obstacle.get_zone_bounds(clearance)

        # Zone: 46-86 horizontal, 34-74 vertical

        # Section that overlaps
        overlapping = SectionBounds(left=40.0, right=60.0, bottom=0.0, top=96.0)
        assert zone.overlaps(overlapping) is True

        # Section to the left (no overlap)
        left_section = SectionBounds(left=0.0, right=46.0, bottom=0.0, top=96.0)
        assert zone.overlaps(left_section) is False

        # Section to the right (no overlap)
        right_section = SectionBounds(left=86.0, right=120.0, bottom=0.0, top=96.0)
        assert zone.overlaps(right_section) is False

        # Section below the window (no overlap)
        lower_section = SectionBounds(left=46.0, right=86.0, bottom=0.0, top=34.0)
        assert zone.overlaps(lower_section) is False

        # Section above the window (no overlap)
        upper_section = SectionBounds(left=46.0, right=86.0, bottom=74.0, top=96.0)
        assert zone.overlaps(upper_section) is False
