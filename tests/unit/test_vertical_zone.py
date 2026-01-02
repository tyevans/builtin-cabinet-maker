"""Unit tests for FRD-22 vertical zone data model."""

import pytest

from cabinets.domain.value_objects import (
    CountertopEdgeType,
    GapPurpose,
    ZoneMounting,
    ZonePreset,
    ZoneType,
)
from cabinets.domain.vertical_zone import (
    HUTCH_PRESET,
    KITCHEN_PRESET,
    MUDROOM_PRESET,
    VANITY_PRESET,
    VerticalZone,
    VerticalZoneStack,
    get_preset,
)


class TestZoneEnums:
    """Tests for FRD-22 zone-related enums."""

    def test_zone_type_values(self) -> None:
        """Test ZoneType enum has all expected values."""
        assert ZoneType.BASE.value == "base"
        assert ZoneType.UPPER.value == "upper"
        assert ZoneType.GAP.value == "gap"
        assert ZoneType.BENCH.value == "bench"
        assert ZoneType.OPEN.value == "open"

    def test_zone_mounting_values(self) -> None:
        """Test ZoneMounting enum has all expected values."""
        assert ZoneMounting.FLOOR.value == "floor"
        assert ZoneMounting.WALL.value == "wall"
        assert ZoneMounting.SUSPENDED.value == "suspended"
        assert ZoneMounting.ON_BASE.value == "on_base"

    def test_gap_purpose_values(self) -> None:
        """Test GapPurpose enum has all expected values."""
        assert GapPurpose.BACKSPLASH.value == "backsplash"
        assert GapPurpose.MIRROR.value == "mirror"
        assert GapPurpose.HOOKS.value == "hooks"
        assert GapPurpose.WORKSPACE.value == "workspace"
        assert GapPurpose.DISPLAY.value == "display"

    def test_zone_preset_values(self) -> None:
        """Test ZonePreset enum has all expected values."""
        assert ZonePreset.KITCHEN.value == "kitchen"
        assert ZonePreset.MUDROOM.value == "mudroom"
        assert ZonePreset.VANITY.value == "vanity"
        assert ZonePreset.HUTCH.value == "hutch"
        assert ZonePreset.CUSTOM.value == "custom"

    def test_countertop_edge_type_values(self) -> None:
        """Test CountertopEdgeType enum has all expected values."""
        assert CountertopEdgeType.SQUARE.value == "square"
        assert CountertopEdgeType.EASED.value == "eased"
        assert CountertopEdgeType.BULLNOSE.value == "bullnose"
        assert CountertopEdgeType.BEVELED.value == "beveled"
        assert CountertopEdgeType.WATERFALL.value == "waterfall"


class TestVerticalZone:
    """Tests for VerticalZone dataclass."""

    def test_create_base_zone(self) -> None:
        """Test creating a basic base zone."""
        zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        assert zone.zone_type == ZoneType.BASE
        assert zone.height == 34.5
        assert zone.depth == 24.0
        assert zone.mounting == ZoneMounting.FLOOR
        assert zone.sections == ()
        assert zone.gap_purpose is None
        assert zone.mounting_height is None

    def test_create_gap_zone(self) -> None:
        """Test creating a gap zone with zero depth."""
        zone = VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
            gap_purpose=GapPurpose.BACKSPLASH,
        )
        assert zone.zone_type == ZoneType.GAP
        assert zone.depth == 0.0
        assert zone.gap_purpose == GapPurpose.BACKSPLASH

    def test_create_upper_zone_with_mounting_height(self) -> None:
        """Test creating an upper zone with mounting height."""
        zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
            mounting_height=54.0,
        )
        assert zone.mounting_height == 54.0

    def test_create_zone_with_sections(self) -> None:
        """Test creating a zone with section configurations."""
        sections = ({"width": 24.0, "shelves": 3}, {"width": "fill", "shelves": 5})
        zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
            sections=sections,
        )
        assert zone.sections == sections
        assert len(zone.sections) == 2

    def test_zone_is_frozen(self) -> None:
        """Test that VerticalZone is immutable."""
        zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        with pytest.raises(AttributeError):
            zone.height = 36.0  # type: ignore[misc]

    def test_invalid_height_zero(self) -> None:
        """Test that zero height raises ValueError."""
        with pytest.raises(ValueError, match="Zone height must be positive"):
            VerticalZone(
                zone_type=ZoneType.BASE,
                height=0.0,
                depth=24.0,
                mounting=ZoneMounting.FLOOR,
            )

    def test_invalid_height_negative(self) -> None:
        """Test that negative height raises ValueError."""
        with pytest.raises(ValueError, match="Zone height must be positive"):
            VerticalZone(
                zone_type=ZoneType.BASE,
                height=-10.0,
                depth=24.0,
                mounting=ZoneMounting.FLOOR,
            )

    def test_invalid_depth_negative(self) -> None:
        """Test that negative depth raises ValueError."""
        with pytest.raises(ValueError, match="Zone depth cannot be negative"):
            VerticalZone(
                zone_type=ZoneType.BASE,
                height=34.5,
                depth=-1.0,
                mounting=ZoneMounting.FLOOR,
            )

    def test_non_gap_zone_requires_positive_depth(self) -> None:
        """Test that non-gap zones require positive depth."""
        with pytest.raises(
            ValueError, match="Zone depth must be positive for non-gap zones"
        ):
            VerticalZone(
                zone_type=ZoneType.BASE,
                height=34.5,
                depth=0.0,
                mounting=ZoneMounting.FLOOR,
            )

    def test_gap_zone_allows_zero_depth(self) -> None:
        """Test that gap zones can have zero depth."""
        zone = VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
        )
        assert zone.depth == 0.0


class TestVerticalZoneStack:
    """Tests for VerticalZoneStack dataclass."""

    def test_create_simple_stack(self) -> None:
        """Test creating a simple zone stack."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        stack = VerticalZoneStack(
            zones=(base_zone,),
            total_width=48.0,
        )
        assert len(stack.zones) == 1
        assert stack.total_width == 48.0
        assert stack.full_height_sides is False

    def test_create_multi_zone_stack(self) -> None:
        """Test creating a multi-zone stack."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        gap_zone = VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
            gap_purpose=GapPurpose.BACKSPLASH,
        )
        upper_zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
        )
        stack = VerticalZoneStack(
            zones=(base_zone, gap_zone, upper_zone),
            total_width=48.0,
        )
        assert len(stack.zones) == 3

    def test_stack_total_height(self) -> None:
        """Test total_height property calculates correctly."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        gap_zone = VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
        )
        upper_zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
        )
        stack = VerticalZoneStack(
            zones=(base_zone, gap_zone, upper_zone),
            total_width=48.0,
        )
        assert stack.total_height == 82.5  # 34.5 + 18.0 + 30.0

    def test_stack_base_zones(self) -> None:
        """Test base_zones property filters correctly."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        bench_zone = VerticalZone(
            zone_type=ZoneType.BENCH,
            height=18.0,
            depth=16.0,
            mounting=ZoneMounting.FLOOR,
        )
        upper_zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
        )
        stack = VerticalZoneStack(
            zones=(base_zone, bench_zone, upper_zone),
            total_width=48.0,
        )
        base_zones = stack.base_zones
        assert len(base_zones) == 2
        assert base_zone in base_zones
        assert bench_zone in base_zones

    def test_stack_upper_zones(self) -> None:
        """Test upper_zones property filters correctly."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        upper_zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
        )
        stack = VerticalZoneStack(
            zones=(base_zone, upper_zone),
            total_width=48.0,
        )
        upper_zones = stack.upper_zones
        assert len(upper_zones) == 1
        assert upper_zone in upper_zones

    def test_stack_gap_zones(self) -> None:
        """Test gap_zones property filters correctly."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        gap_zone = VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
            gap_purpose=GapPurpose.BACKSPLASH,
        )
        upper_zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
        )
        stack = VerticalZoneStack(
            zones=(base_zone, gap_zone, upper_zone),
            total_width=48.0,
        )
        gap_zones = stack.gap_zones
        assert len(gap_zones) == 1
        assert gap_zone in gap_zones

    def test_zone_bottom_height(self) -> None:
        """Test zone_bottom_height calculates correctly."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        gap_zone = VerticalZone(
            zone_type=ZoneType.GAP,
            height=18.0,
            depth=0.0,
            mounting=ZoneMounting.WALL,
        )
        upper_zone = VerticalZone(
            zone_type=ZoneType.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMounting.WALL,
        )
        stack = VerticalZoneStack(
            zones=(base_zone, gap_zone, upper_zone),
            total_width=48.0,
        )
        assert stack.zone_bottom_height(0) == 0.0
        assert stack.zone_bottom_height(1) == 34.5
        assert stack.zone_bottom_height(2) == 52.5  # 34.5 + 18.0

    def test_zone_bottom_height_index_error(self) -> None:
        """Test zone_bottom_height raises IndexError for invalid index."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        stack = VerticalZoneStack(
            zones=(base_zone,),
            total_width=48.0,
        )
        with pytest.raises(IndexError, match="Zone index 1 out of range"):
            stack.zone_bottom_height(1)
        with pytest.raises(IndexError, match="Zone index -1 out of range"):
            stack.zone_bottom_height(-1)

    def test_stack_full_height_sides(self) -> None:
        """Test creating a stack with full height sides."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        stack = VerticalZoneStack(
            zones=(base_zone,),
            total_width=48.0,
            full_height_sides=True,
        )
        assert stack.full_height_sides is True

    def test_stack_is_frozen(self) -> None:
        """Test that VerticalZoneStack is immutable."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        stack = VerticalZoneStack(
            zones=(base_zone,),
            total_width=48.0,
        )
        with pytest.raises(AttributeError):
            stack.total_width = 60.0  # type: ignore[misc]

    def test_empty_zones_raises_error(self) -> None:
        """Test that empty zones tuple raises ValueError."""
        with pytest.raises(ValueError, match="Zone stack must have at least one zone"):
            VerticalZoneStack(
                zones=(),
                total_width=48.0,
            )

    def test_invalid_width_zero(self) -> None:
        """Test that zero width raises ValueError."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        with pytest.raises(ValueError, match="Total width must be positive"):
            VerticalZoneStack(
                zones=(base_zone,),
                total_width=0.0,
            )

    def test_invalid_width_negative(self) -> None:
        """Test that negative width raises ValueError."""
        base_zone = VerticalZone(
            zone_type=ZoneType.BASE,
            height=34.5,
            depth=24.0,
            mounting=ZoneMounting.FLOOR,
        )
        with pytest.raises(ValueError, match="Total width must be positive"):
            VerticalZoneStack(
                zones=(base_zone,),
                total_width=-10.0,
            )


class TestZonePresets:
    """Tests for zone preset configurations."""

    def test_kitchen_preset_structure(self) -> None:
        """Test KITCHEN_PRESET has correct structure."""
        assert len(KITCHEN_PRESET.zones) == 3
        assert KITCHEN_PRESET.total_width == 48.0

        # Base zone
        base = KITCHEN_PRESET.zones[0]
        assert base.zone_type == ZoneType.BASE
        assert base.height == 34.5
        assert base.depth == 24.0
        assert base.mounting == ZoneMounting.FLOOR

        # Gap zone
        gap = KITCHEN_PRESET.zones[1]
        assert gap.zone_type == ZoneType.GAP
        assert gap.height == 18.0
        assert gap.depth == 0.0
        assert gap.gap_purpose == GapPurpose.BACKSPLASH

        # Upper zone
        upper = KITCHEN_PRESET.zones[2]
        assert upper.zone_type == ZoneType.UPPER
        assert upper.height == 30.0
        assert upper.depth == 12.0
        assert upper.mounting_height == 54.0

    def test_mudroom_preset_structure(self) -> None:
        """Test MUDROOM_PRESET has correct structure."""
        assert len(MUDROOM_PRESET.zones) == 3
        assert MUDROOM_PRESET.total_width == 48.0
        assert MUDROOM_PRESET.full_height_sides is True

        # Bench zone
        bench = MUDROOM_PRESET.zones[0]
        assert bench.zone_type == ZoneType.BENCH
        assert bench.height == 18.0
        assert bench.depth == 16.0

        # Gap zone
        gap = MUDROOM_PRESET.zones[1]
        assert gap.zone_type == ZoneType.GAP
        assert gap.gap_purpose == GapPurpose.HOOKS

        # Open zone
        open_zone = MUDROOM_PRESET.zones[2]
        assert open_zone.zone_type == ZoneType.OPEN

    def test_vanity_preset_structure(self) -> None:
        """Test VANITY_PRESET has correct structure."""
        assert len(VANITY_PRESET.zones) == 3
        assert VANITY_PRESET.total_width == 36.0

        # Base zone
        base = VANITY_PRESET.zones[0]
        assert base.zone_type == ZoneType.BASE
        assert base.height == 34.0
        assert base.depth == 21.0

        # Gap zone
        gap = VANITY_PRESET.zones[1]
        assert gap.gap_purpose == GapPurpose.MIRROR

    def test_hutch_preset_structure(self) -> None:
        """Test HUTCH_PRESET has correct structure."""
        assert len(HUTCH_PRESET.zones) == 3
        assert HUTCH_PRESET.total_width == 48.0

        # Base zone
        base = HUTCH_PRESET.zones[0]
        assert base.zone_type == ZoneType.BASE
        assert base.height == 30.0
        assert base.depth == 24.0

        # Gap zone
        gap = HUTCH_PRESET.zones[1]
        assert gap.mounting == ZoneMounting.ON_BASE
        assert gap.gap_purpose == GapPurpose.WORKSPACE

        # Upper zone
        upper = HUTCH_PRESET.zones[2]
        assert upper.mounting == ZoneMounting.ON_BASE


class TestGetPreset:
    """Tests for get_preset function."""

    def test_get_kitchen_preset(self) -> None:
        """Test getting kitchen preset by name."""
        preset = get_preset("kitchen")
        assert preset is KITCHEN_PRESET

    def test_get_mudroom_preset(self) -> None:
        """Test getting mudroom preset by name."""
        preset = get_preset("mudroom")
        assert preset is MUDROOM_PRESET

    def test_get_vanity_preset(self) -> None:
        """Test getting vanity preset by name."""
        preset = get_preset("vanity")
        assert preset is VANITY_PRESET

    def test_get_hutch_preset(self) -> None:
        """Test getting hutch preset by name."""
        preset = get_preset("hutch")
        assert preset is HUTCH_PRESET

    def test_get_preset_case_insensitive(self) -> None:
        """Test that preset name is case insensitive."""
        assert get_preset("Kitchen") is KITCHEN_PRESET
        assert get_preset("KITCHEN") is KITCHEN_PRESET
        assert get_preset("KiTcHeN") is KITCHEN_PRESET

    def test_get_preset_with_custom_width(self) -> None:
        """Test getting preset with custom width creates new stack."""
        preset = get_preset("kitchen", width=60.0)
        assert preset is not KITCHEN_PRESET
        assert preset.total_width == 60.0
        assert preset.zones == KITCHEN_PRESET.zones

    def test_get_preset_with_same_width_returns_original(self) -> None:
        """Test getting preset with same width returns original."""
        preset = get_preset("kitchen", width=48.0)
        assert preset is KITCHEN_PRESET

    def test_get_preset_invalid_name(self) -> None:
        """Test getting invalid preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset: invalid"):
            get_preset("invalid")

    def test_get_preset_invalid_name_shows_valid_presets(self) -> None:
        """Test error message includes valid preset names."""
        with pytest.raises(ValueError) as exc_info:
            get_preset("bathroom")
        error_msg = str(exc_info.value)
        assert "kitchen" in error_msg
        assert "mudroom" in error_msg
        assert "vanity" in error_msg
        assert "hutch" in error_msg
