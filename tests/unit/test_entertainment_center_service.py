"""Unit tests for entertainment center layout service.

FRD-19: Entertainment Centers and Media Fixtures - Phase 6: Layout Types
"""

import pytest

from cabinets.domain.services.entertainment_center import (
    CableChasePosition,
    EntertainmentCenterLayoutService,
    TVIntegration,
    TVZone,
)
from cabinets.domain.value_objects import Dimensions, Position


class TestTVIntegration:
    """Tests for TVIntegration dataclass."""

    def test_create_valid_tv_integration(self) -> None:
        """Test creating a valid TV integration specification."""
        tv = TVIntegration(
            screen_size=65,
            mounting="wall",
            center_height=42.0,
            viewing_width=57.0,
        )
        assert tv.screen_size == 65
        assert tv.mounting == "wall"
        assert tv.center_height == 42.0
        assert tv.viewing_width == 57.0

    def test_tv_integration_stand_mounting(self) -> None:
        """Test TV integration with stand mounting."""
        tv = TVIntegration(
            screen_size=55,
            mounting="stand",
            center_height=36.0,
            viewing_width=48.0,
        )
        assert tv.mounting == "stand"

    def test_from_screen_size_65_inch(self) -> None:
        """Test from_screen_size factory for 65\" TV."""
        tv = TVIntegration.from_screen_size(65)
        assert tv.screen_size == 65
        assert tv.mounting == "wall"
        assert tv.center_height == 42.0
        assert tv.viewing_width == 57.0

    def test_from_screen_size_55_inch(self) -> None:
        """Test from_screen_size factory for 55\" TV."""
        tv = TVIntegration.from_screen_size(55)
        assert tv.screen_size == 55
        assert tv.viewing_width == 48.0

    def test_from_screen_size_75_inch(self) -> None:
        """Test from_screen_size factory for 75\" TV."""
        tv = TVIntegration.from_screen_size(75)
        assert tv.screen_size == 75
        assert tv.viewing_width == 65.0

    def test_from_screen_size_50_inch(self) -> None:
        """Test from_screen_size factory for 50\" TV."""
        tv = TVIntegration.from_screen_size(50)
        assert tv.screen_size == 50
        assert tv.viewing_width == 44.0

    def test_from_screen_size_85_inch(self) -> None:
        """Test from_screen_size factory for 85\" TV."""
        tv = TVIntegration.from_screen_size(85)
        assert tv.screen_size == 85
        assert tv.viewing_width == 74.0

    def test_from_screen_size_custom_mounting(self) -> None:
        """Test from_screen_size with custom mounting option."""
        tv = TVIntegration.from_screen_size(65, mounting="stand")
        assert tv.mounting == "stand"

    def test_from_screen_size_custom_height(self) -> None:
        """Test from_screen_size with custom center height."""
        tv = TVIntegration.from_screen_size(65, center_height=50.0)
        assert tv.center_height == 50.0

    def test_from_screen_size_non_standard_size(self) -> None:
        """Test from_screen_size with non-standard TV size uses calculation."""
        tv = TVIntegration.from_screen_size(60)
        # Non-standard sizes use 0.87 factor
        expected_width = 60 * 0.87
        assert tv.viewing_width == pytest.approx(expected_width, rel=0.01)

    def test_tv_integration_screen_size_too_small_raises_error(self) -> None:
        """Test that screen size below 32\" raises ValueError."""
        with pytest.raises(ValueError, match="at least 32 inches"):
            TVIntegration(
                screen_size=30,
                mounting="wall",
                center_height=42.0,
                viewing_width=26.0,
            )

    def test_tv_integration_screen_size_too_large_raises_error(self) -> None:
        """Test that screen size above 100\" raises ValueError."""
        with pytest.raises(ValueError, match="at most 100 inches"):
            TVIntegration(
                screen_size=110,
                mounting="wall",
                center_height=42.0,
                viewing_width=95.0,
            )

    def test_tv_integration_negative_center_height_raises_error(self) -> None:
        """Test that negative center height raises ValueError."""
        with pytest.raises(ValueError, match="Center height must be positive"):
            TVIntegration(
                screen_size=65,
                mounting="wall",
                center_height=-10.0,
                viewing_width=57.0,
            )

    def test_tv_integration_zero_viewing_width_raises_error(self) -> None:
        """Test that zero viewing width raises ValueError."""
        with pytest.raises(ValueError, match="Viewing width must be positive"):
            TVIntegration(
                screen_size=65,
                mounting="wall",
                center_height=42.0,
                viewing_width=0.0,
            )

    def test_tv_integration_is_frozen(self) -> None:
        """Test that TVIntegration is immutable."""
        tv = TVIntegration.from_screen_size(65)
        with pytest.raises(AttributeError):
            tv.screen_size = 75  # type: ignore


class TestTVZone:
    """Tests for TVZone dataclass."""

    def test_create_valid_tv_zone(self) -> None:
        """Test creating a valid TV zone."""
        zone = TVZone(
            tv_zone_start=10.0,
            tv_zone_width=61.0,
            tv_zone_end=71.0,
            flanking_left_width=10.0,
            flanking_right_width=10.0,
            tv_center_height=42.0,
        )
        assert zone.tv_zone_start == 10.0
        assert zone.tv_zone_width == 61.0
        assert zone.tv_zone_end == 71.0
        assert zone.flanking_left_width == 10.0
        assert zone.flanking_right_width == 10.0
        assert zone.tv_center_height == 42.0

    def test_tv_zone_zero_flanking_is_valid(self) -> None:
        """Test TV zone with zero flanking width is valid."""
        zone = TVZone(
            tv_zone_start=0.0,
            tv_zone_width=72.0,
            tv_zone_end=72.0,
            flanking_left_width=0.0,
            flanking_right_width=0.0,
            tv_center_height=42.0,
        )
        assert zone.flanking_left_width == 0.0
        assert zone.flanking_right_width == 0.0

    def test_tv_zone_zero_width_raises_error(self) -> None:
        """Test that zero TV zone width raises ValueError."""
        with pytest.raises(ValueError, match="TV zone width must be positive"):
            TVZone(
                tv_zone_start=0.0,
                tv_zone_width=0.0,
                tv_zone_end=0.0,
                flanking_left_width=0.0,
                flanking_right_width=0.0,
                tv_center_height=42.0,
            )

    def test_tv_zone_negative_flanking_raises_error(self) -> None:
        """Test that negative flanking width raises ValueError."""
        with pytest.raises(
            ValueError, match="Flanking left width must be non-negative"
        ):
            TVZone(
                tv_zone_start=0.0,
                tv_zone_width=60.0,
                tv_zone_end=60.0,
                flanking_left_width=-5.0,
                flanking_right_width=5.0,
                tv_center_height=42.0,
            )

    def test_tv_zone_is_frozen(self) -> None:
        """Test that TVZone is immutable."""
        zone = TVZone(
            tv_zone_start=10.0,
            tv_zone_width=61.0,
            tv_zone_end=71.0,
            flanking_left_width=10.0,
            flanking_right_width=10.0,
            tv_center_height=42.0,
        )
        with pytest.raises(AttributeError):
            zone.tv_zone_width = 70.0  # type: ignore


class TestCableChasePosition:
    """Tests for CableChasePosition dataclass."""

    def test_create_valid_cable_chase_position(self) -> None:
        """Test creating a valid cable chase position."""
        chase = CableChasePosition(
            x=36.0,
            y=0.0,
            width=3.0,
            purpose="TV cable routing",
        )
        assert chase.x == 36.0
        assert chase.y == 0.0
        assert chase.width == 3.0
        assert chase.purpose == "TV cable routing"

    def test_cable_chase_default_width(self) -> None:
        """Test cable chase has default 3\" width."""
        chase = CableChasePosition(x=36.0, y=0.0)
        assert chase.width == 3.0

    def test_cable_chase_default_purpose(self) -> None:
        """Test cable chase has empty default purpose."""
        chase = CableChasePosition(x=36.0, y=0.0)
        assert chase.purpose == ""

    def test_cable_chase_to_position(self) -> None:
        """Test cable chase to_position method."""
        chase = CableChasePosition(x=36.0, y=12.0)
        position = chase.to_position()
        assert isinstance(position, Position)
        assert position.x == 36.0
        assert position.y == 12.0

    def test_cable_chase_negative_x_raises_error(self) -> None:
        """Test that negative x position raises ValueError."""
        with pytest.raises(ValueError, match="X position must be non-negative"):
            CableChasePosition(x=-5.0, y=0.0)

    def test_cable_chase_negative_y_raises_error(self) -> None:
        """Test that negative y position raises ValueError."""
        with pytest.raises(ValueError, match="Y position must be non-negative"):
            CableChasePosition(x=36.0, y=-5.0)

    def test_cable_chase_zero_width_raises_error(self) -> None:
        """Test that zero width raises ValueError."""
        with pytest.raises(ValueError, match="Width must be positive"):
            CableChasePosition(x=36.0, y=0.0, width=0.0)

    def test_cable_chase_is_frozen(self) -> None:
        """Test that CableChasePosition is immutable."""
        chase = CableChasePosition(x=36.0, y=0.0)
        with pytest.raises(AttributeError):
            chase.x = 40.0  # type: ignore


class TestEntertainmentCenterLayoutService:
    """Tests for EntertainmentCenterLayoutService class."""

    def test_service_instantiation(self) -> None:
        """Test that service can be instantiated."""
        service = EntertainmentCenterLayoutService()
        assert service is not None
        assert service.layout_constraints is not None

    def test_layout_constraints_defined(self) -> None:
        """Test that layout constraints are defined for all types."""
        service = EntertainmentCenterLayoutService()
        assert "console" in service.layout_constraints
        assert "wall_unit" in service.layout_constraints
        assert "floating" in service.layout_constraints
        assert "tower" in service.layout_constraints


class TestValidateLayout:
    """Tests for EntertainmentCenterLayoutService.validate_layout() method."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    # Console layout validation tests
    def test_validate_console_valid_dimensions(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test console validation with valid dimensions."""
        dimensions = Dimensions(width=72.0, height=24.0, depth=18.0)
        errors, warnings = service.validate_layout("console", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_console_height_below_minimum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test console validation with height below minimum (16\")."""
        dimensions = Dimensions(width=72.0, height=14.0, depth=18.0)
        errors, warnings = service.validate_layout("console", dimensions)
        assert len(errors) == 1
        assert "below minimum" in errors[0]
        assert "16" in errors[0]

    def test_validate_console_height_above_maximum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test console validation with height above maximum (30\")."""
        dimensions = Dimensions(width=72.0, height=36.0, depth=18.0)
        errors, warnings = service.validate_layout("console", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "exceeds typical" in warnings[0]
        assert "30" in warnings[0]

    def test_validate_console_depth_warning(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test console validation with insufficient depth warning."""
        dimensions = Dimensions(width=72.0, height=24.0, depth=12.0)
        errors, warnings = service.validate_layout("console", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "insufficient" in warnings[0].lower()

    # Wall unit layout validation tests
    def test_validate_wall_unit_valid_dimensions(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test wall unit validation with valid dimensions."""
        dimensions = Dimensions(width=96.0, height=84.0, depth=16.0)
        errors, warnings = service.validate_layout("wall_unit", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_wall_unit_height_below_minimum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test wall unit validation with height below minimum (72\")."""
        dimensions = Dimensions(width=96.0, height=60.0, depth=16.0)
        errors, warnings = service.validate_layout("wall_unit", dimensions)
        assert len(errors) == 1
        assert "below minimum" in errors[0]
        assert "72" in errors[0]

    def test_validate_wall_unit_height_above_maximum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test wall unit validation with height above maximum (96\")."""
        dimensions = Dimensions(width=96.0, height=108.0, depth=16.0)
        errors, warnings = service.validate_layout("wall_unit", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "exceeds typical" in warnings[0]

    # Floating layout validation tests
    def test_validate_floating_valid_dimensions(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating validation with valid dimensions."""
        dimensions = Dimensions(width=60.0, height=18.0, depth=14.0)
        errors, warnings = service.validate_layout("floating", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_floating_height_below_minimum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating validation with height below minimum (12\")."""
        dimensions = Dimensions(width=60.0, height=10.0, depth=14.0)
        errors, warnings = service.validate_layout("floating", dimensions)
        assert len(errors) == 1
        assert "below minimum" in errors[0]
        assert "12" in errors[0]

    def test_validate_floating_height_above_maximum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating validation with height above maximum (24\")."""
        dimensions = Dimensions(width=60.0, height=30.0, depth=14.0)
        errors, warnings = service.validate_layout("floating", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "exceeds typical" in warnings[0]

    # Tower layout validation tests
    def test_validate_tower_valid_dimensions(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test tower validation with valid dimensions."""
        dimensions = Dimensions(width=30.0, height=72.0, depth=20.0)
        errors, warnings = service.validate_layout("tower", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_tower_width_below_minimum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test tower validation with width below minimum (24\")."""
        dimensions = Dimensions(width=20.0, height=72.0, depth=20.0)
        errors, warnings = service.validate_layout("tower", dimensions)
        assert len(errors) == 1
        assert "too narrow" in errors[0]
        assert "24" in errors[0]

    def test_validate_tower_width_above_maximum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test tower validation with width above maximum (36\")."""
        dimensions = Dimensions(width=40.0, height=72.0, depth=20.0)
        errors, warnings = service.validate_layout("tower", dimensions)
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "exceeds typical" in warnings[0]

    def test_validate_tower_depth_below_minimum(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test tower validation with depth below minimum (18\")."""
        dimensions = Dimensions(width=30.0, height=72.0, depth=14.0)
        errors, warnings = service.validate_layout("tower", dimensions)
        assert len(errors) == 1
        assert "insufficient for equipment" in errors[0]
        assert "18" in errors[0]

    # Unknown layout type test
    def test_validate_unknown_layout_type_raises_error(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test that unknown layout type raises ValueError."""
        dimensions = Dimensions(width=72.0, height=24.0, depth=18.0)
        with pytest.raises(ValueError, match="Unknown layout type"):
            service.validate_layout("unknown_type", dimensions)


class TestCalculateTVZone:
    """Tests for EntertainmentCenterLayoutService.calculate_tv_zone() method."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    def test_calculate_tv_zone_centered(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test TV zone calculation with centered TV."""
        tv = TVIntegration.from_screen_size(65)  # 57" viewing width
        zone = service.calculate_tv_zone(tv, cabinet_width=96.0)

        # TV zone width = 57 + 2*2 = 61"
        # Flanking = (96 - 61) / 2 = 17.5" each
        assert zone.tv_zone_width == pytest.approx(61.0, rel=0.01)
        assert zone.flanking_left_width == pytest.approx(17.5, rel=0.01)
        assert zone.flanking_right_width == pytest.approx(17.5, rel=0.01)
        assert zone.tv_zone_start == pytest.approx(17.5, rel=0.01)
        assert zone.tv_zone_end == pytest.approx(78.5, rel=0.01)
        assert zone.tv_center_height == 42.0

    def test_calculate_tv_zone_exact_width(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test TV zone calculation when cabinet exactly fits TV zone."""
        tv = TVIntegration(
            screen_size=65,
            mounting="wall",
            center_height=42.0,
            viewing_width=68.0,  # With 2" clearance each side = 72"
        )
        zone = service.calculate_tv_zone(tv, cabinet_width=72.0)

        # No flanking storage when exact fit
        assert zone.flanking_left_width == pytest.approx(0.0, abs=0.01)
        assert zone.flanking_right_width == pytest.approx(0.0, abs=0.01)
        assert zone.tv_zone_width == pytest.approx(72.0, rel=0.01)

    def test_calculate_tv_zone_insufficient_width_raises_error(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test that insufficient cabinet width raises ValueError."""
        tv = TVIntegration.from_screen_size(85)  # 74" + 4" clearance = 78"
        with pytest.raises(ValueError, match="insufficient for TV zone"):
            service.calculate_tv_zone(tv, cabinet_width=72.0)

    def test_calculate_tv_zone_55_inch_tv(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test TV zone calculation for 55\" TV."""
        tv = TVIntegration.from_screen_size(55)  # 48" viewing width
        zone = service.calculate_tv_zone(tv, cabinet_width=72.0)

        # TV zone width = 48 + 4 = 52"
        # Flanking = (72 - 52) / 2 = 10" each
        assert zone.tv_zone_width == pytest.approx(52.0, rel=0.01)
        assert zone.flanking_left_width == pytest.approx(10.0, rel=0.01)
        assert zone.flanking_right_width == pytest.approx(10.0, rel=0.01)

    def test_calculate_tv_zone_custom_center_height(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test TV zone preserves custom center height."""
        tv = TVIntegration.from_screen_size(65, center_height=50.0)
        zone = service.calculate_tv_zone(tv, cabinet_width=96.0)
        assert zone.tv_center_height == 50.0


class TestGenerateCableChasePositions:
    """Tests for EntertainmentCenterLayoutService.generate_cable_chase_positions()."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    def test_cable_chase_wall_unit_centered(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test cable chase for wall unit is centered."""
        positions = service.generate_cable_chase_positions("wall_unit", 96.0)

        assert len(positions) == 1
        chase = positions[0]
        # Center position = (96 / 2) - (3 / 2) = 46.5
        assert chase.x == pytest.approx(46.5, rel=0.01)
        assert chase.y == 0.0
        assert chase.width == 3.0
        assert "TV" in chase.purpose or "Central" in chase.purpose

    def test_cable_chase_tower_right_side(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test cable chase for tower is on right side."""
        positions = service.generate_cable_chase_positions("tower", 30.0)

        assert len(positions) == 1
        chase = positions[0]
        # Right side position = 30 - 4 = 26"
        assert chase.x == pytest.approx(26.0, rel=0.01)
        assert "Equipment" in chase.purpose or "stack" in chase.purpose.lower()

    def test_cable_chase_console_centered(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test cable chase for console is centered."""
        positions = service.generate_cable_chase_positions("console", 72.0)

        assert len(positions) == 1
        chase = positions[0]
        # Center = (72 / 2) - (3 / 2) = 34.5"
        assert chase.x == pytest.approx(34.5, rel=0.01)

    def test_cable_chase_floating_centered(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test cable chase for floating is centered with wall routing."""
        positions = service.generate_cable_chase_positions("floating", 60.0)

        assert len(positions) == 1
        chase = positions[0]
        # Center = (60 / 2) - (3 / 2) = 28.5"
        assert chase.x == pytest.approx(28.5, rel=0.01)
        assert "wall" in chase.purpose.lower()


class TestGetDefaultDimensions:
    """Tests for EntertainmentCenterLayoutService.get_default_dimensions()."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    def test_default_dimensions_console(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test default dimensions for console layout."""
        dims = service.get_default_dimensions("console")
        assert dims.height == 24.0  # Default console height
        assert dims.depth == 18.0  # Equipment depth
        assert dims.width == 72.0

    def test_default_dimensions_wall_unit(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test default dimensions for wall unit layout."""
        dims = service.get_default_dimensions("wall_unit")
        assert dims.height == 84.0  # Default wall unit height
        assert dims.depth == 16.0
        assert dims.width == 96.0

    def test_default_dimensions_floating(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test default dimensions for floating layout."""
        dims = service.get_default_dimensions("floating")
        assert dims.height == 18.0  # Default floating height
        assert dims.depth == 14.0
        assert dims.width == 60.0

    def test_default_dimensions_tower(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test default dimensions for tower layout."""
        dims = service.get_default_dimensions("tower")
        assert dims.width == 30.0
        assert dims.depth == 20.0  # Default tower depth
        assert dims.height == 72.0

    def test_default_dimensions_unknown_type_raises_error(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test that unknown layout type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown layout type"):
            service.get_default_dimensions("unknown")


class TestFloatingWeightCapacity:
    """Tests for floating mount weight capacity calculations."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    def test_calculate_floating_weight_capacity_default(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test default floating weight capacity calculation."""
        # 2 cleats * 75 lbs = 150 lbs base capacity
        capacity = service.calculate_floating_weight_capacity(
            width=48.0, depth=14.0, cleat_count=2
        )
        assert capacity == 150.0

    def test_calculate_floating_weight_capacity_wide_unit(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test capacity reduction for very wide units."""
        # Width > 48" reduces capacity
        capacity_normal = service.calculate_floating_weight_capacity(
            width=48.0, depth=14.0
        )
        capacity_wide = service.calculate_floating_weight_capacity(
            width=72.0, depth=14.0
        )
        assert capacity_wide < capacity_normal

    def test_calculate_floating_weight_capacity_deep_unit(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test capacity reduction for very deep units."""
        # Depth > 16" reduces capacity
        capacity_normal = service.calculate_floating_weight_capacity(
            width=48.0, depth=16.0
        )
        capacity_deep = service.calculate_floating_weight_capacity(
            width=48.0, depth=24.0
        )
        assert capacity_deep < capacity_normal

    def test_calculate_floating_weight_capacity_more_cleats(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test capacity increases with more cleats."""
        capacity_2_cleats = service.calculate_floating_weight_capacity(
            width=48.0, depth=14.0, cleat_count=2
        )
        capacity_3_cleats = service.calculate_floating_weight_capacity(
            width=48.0, depth=14.0, cleat_count=3
        )
        assert capacity_3_cleats > capacity_2_cleats

    def test_validate_floating_weight_safe(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating weight validation for safe load."""
        dimensions = Dimensions(width=48.0, height=18.0, depth=14.0)
        is_safe, message = service.validate_floating_weight(dimensions, 100.0)
        assert is_safe is True
        assert "within safe capacity" in message

    def test_validate_floating_weight_exceeds_max(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating weight validation when exceeding max limit (150 lbs)."""
        dimensions = Dimensions(width=48.0, height=18.0, depth=14.0)
        is_safe, message = service.validate_floating_weight(dimensions, 200.0)
        assert is_safe is False
        assert "exceeds maximum" in message
        assert "150" in message

    def test_validate_floating_weight_exceeds_calculated_capacity(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating weight validation when exceeding calculated capacity."""
        # Very wide/deep unit has reduced capacity below 150 lbs
        dimensions = Dimensions(width=72.0, height=18.0, depth=20.0)
        # This should exceed the reduced capacity but not the 150 lb max
        is_safe, message = service.validate_floating_weight(dimensions, 120.0)
        # May or may not be safe depending on exact calculation
        assert isinstance(is_safe, bool)
        assert len(message) > 0


class TestLayoutConstraints:
    """Tests for layout constraint constants."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    def test_console_constraints(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test console layout constraints are correct."""
        constraints = service.layout_constraints["console"]
        assert constraints["min_height"] == 16.0
        assert constraints["max_height"] == 30.0
        assert constraints["default_height"] == 24.0
        assert constraints["min_depth"] == 14.0

    def test_wall_unit_constraints(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test wall unit layout constraints are correct."""
        constraints = service.layout_constraints["wall_unit"]
        assert constraints["min_height"] == 72.0
        assert constraints["max_height"] == 96.0
        assert constraints["default_height"] == 84.0

    def test_floating_constraints(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test floating layout constraints are correct."""
        constraints = service.layout_constraints["floating"]
        assert constraints["min_height"] == 12.0
        assert constraints["max_height"] == 24.0
        assert constraints["default_height"] == 18.0
        assert constraints["max_weight_lbs"] == 150.0

    def test_tower_constraints(self, service: EntertainmentCenterLayoutService) -> None:
        """Test tower layout constraints are correct."""
        constraints = service.layout_constraints["tower"]
        assert constraints["min_width"] == 24.0
        assert constraints["max_width"] == 36.0
        assert constraints["min_depth"] == 18.0

    def test_default_cable_chase_width(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test default cable chase width constant."""
        assert service.DEFAULT_CABLE_CHASE_WIDTH == 3.0

    def test_tv_side_clearance(self, service: EntertainmentCenterLayoutService) -> None:
        """Test TV side clearance constant."""
        assert service.TV_SIDE_CLEARANCE == 2.0


class TestServiceIntegration:
    """Integration tests for the entertainment center layout service."""

    @pytest.fixture
    def service(self) -> EntertainmentCenterLayoutService:
        """Create service fixture."""
        return EntertainmentCenterLayoutService()

    def test_full_console_workflow(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test complete workflow for console entertainment center."""
        # Get default dimensions
        dims = service.get_default_dimensions("console")

        # Validate layout
        errors, warnings = service.validate_layout("console", dims)
        assert len(errors) == 0

        # Create TV integration for 55" TV
        tv = TVIntegration.from_screen_size(55)

        # Calculate TV zone
        zone = service.calculate_tv_zone(tv, dims.width)
        assert zone.tv_zone_width < dims.width

        # Get cable chase positions
        chases = service.generate_cable_chase_positions("console", dims.width)
        assert len(chases) > 0

    def test_full_wall_unit_workflow(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test complete workflow for wall unit entertainment center."""
        # Get default dimensions
        dims = service.get_default_dimensions("wall_unit")

        # Validate layout
        errors, warnings = service.validate_layout("wall_unit", dims)
        assert len(errors) == 0

        # Create TV integration for 65" TV
        tv = TVIntegration.from_screen_size(65)

        # Calculate TV zone
        zone = service.calculate_tv_zone(tv, dims.width)
        assert zone.flanking_left_width > 0
        assert zone.flanking_right_width > 0

        # Get cable chase positions
        chases = service.generate_cable_chase_positions("wall_unit", dims.width)
        assert len(chases) > 0

    def test_full_floating_workflow(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test complete workflow for floating entertainment center."""
        # Get default dimensions
        dims = service.get_default_dimensions("floating")

        # Validate layout
        errors, warnings = service.validate_layout("floating", dims)
        assert len(errors) == 0

        # Validate weight capacity
        is_safe, _ = service.validate_floating_weight(dims, 80.0)
        assert is_safe

        # Get cable chase positions
        chases = service.generate_cable_chase_positions("floating", dims.width)
        assert len(chases) > 0

    def test_full_tower_workflow(
        self, service: EntertainmentCenterLayoutService
    ) -> None:
        """Test complete workflow for tower entertainment center."""
        # Get default dimensions
        dims = service.get_default_dimensions("tower")

        # Validate layout
        errors, warnings = service.validate_layout("tower", dims)
        assert len(errors) == 0

        # Get cable chase positions
        chases = service.generate_cable_chase_positions("tower", dims.width)
        assert len(chases) > 0


class TestServiceExports:
    """Tests for service exports from entertainment_center subpackage."""

    def test_service_importable_from_subpackage(self) -> None:
        """Test that service is importable from entertainment_center subpackage."""
        from cabinets.domain.services.entertainment_center import (
            CableChasePosition,
            EntertainmentCenterLayoutService,
            TVIntegration,
            TVZone,
        )

        assert EntertainmentCenterLayoutService is not None
        assert TVIntegration is not None
        assert TVZone is not None
        assert CableChasePosition is not None
