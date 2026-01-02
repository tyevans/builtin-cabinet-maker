"""Unit tests for BayAlcoveLayoutService (FRD-23 Phase 5).

Tests cover:
- classify_wall_zones() for various configurations
- Filler zone detection (narrow walls)
- Under-window zone detection
- Full-height zone detection
- get_cabinet_zones() and get_filler_zones()
- get_component_config() for different zone types
- generate_layout_summary()
- Integration with RadialCeilingService
"""

from __future__ import annotations

import pytest

from cabinets.domain.value_objects import BayAlcoveConfig
from cabinets.domain.services.bay_alcove_service import (
    BayAlcoveLayoutService,
    WallZone,
    ZoneType,
)
from cabinets.domain.value_objects import ApexPoint


# --- Fixtures for BayAlcoveConfig ---


@pytest.fixture
def three_wall_bay_config() -> BayAlcoveConfig:
    """Standard 3-wall bay with center window and two side cabinets."""
    return BayAlcoveConfig(
        bay_type="three_wall",
        walls=(
            {"length": 24.0, "angle": None, "name": "left_wall"},
            {
                "length": 36.0,
                "angle": None,
                "name": "center_wall",
                "window": {
                    "sill_height": 18.0,
                    "head_height": 72.0,
                    "width": 32.0,
                    "projection_depth": 0.0,
                },
            },
            {"length": 24.0, "angle": None, "name": "right_wall"},
        ),
        opening_width=72.0,
        bay_depth=24.0,
        arc_angle=None,
        segment_count=None,
        apex=None,
        apex_mode="auto",
        edge_height=84.0,
        min_cabinet_width=12.0,
        filler_treatment="panel",
        sill_clearance=1.0,
        head_clearance=2.0,
        seat_surface_style="flush",
        flank_integration="match",
        top_style=None,
        shelf_alignment="independent",
    )


@pytest.fixture
def five_wall_bay_config() -> BayAlcoveConfig:
    """5-wall bay with windows on 3 walls and narrow mullion walls."""
    return BayAlcoveConfig(
        bay_type="five_wall",
        walls=(
            {"length": 18.0, "angle": None, "name": "wall_0"},
            {
                "length": 8.0,
                "angle": None,
                "name": "mullion_1",
            },  # Too narrow for cabinet
            {
                "length": 24.0,
                "angle": None,
                "name": "wall_2",
                "window": {
                    "sill_height": 20.0,
                    "head_height": 72.0,
                    "width": 20.0,
                    "projection_depth": 0.0,
                },
            },
            {
                "length": 8.0,
                "angle": None,
                "name": "mullion_3",
            },  # Too narrow for cabinet
            {"length": 18.0, "angle": None, "name": "wall_4"},
        ),
        opening_width=60.0,
        bay_depth=20.0,
        arc_angle=None,
        segment_count=None,
        apex=None,
        apex_mode="auto",
        edge_height=84.0,
        min_cabinet_width=12.0,
        filler_treatment="trim",
        sill_clearance=1.5,
        head_clearance=2.0,
        seat_surface_style="flush",
        flank_integration="match",
        top_style=None,
        shelf_alignment="independent",
    )


@pytest.fixture
def all_windows_bay_config() -> BayAlcoveConfig:
    """3-wall bay with windows on all walls."""
    return BayAlcoveConfig(
        bay_type="three_wall",
        walls=(
            {
                "length": 24.0,
                "angle": None,
                "name": "left_wall",
                "window": {
                    "sill_height": 16.0,
                    "head_height": 72.0,
                    "width": 20.0,
                    "projection_depth": 0.0,
                },
            },
            {
                "length": 36.0,
                "angle": None,
                "name": "center_wall",
                "window": {
                    "sill_height": 18.0,
                    "head_height": 72.0,
                    "width": 32.0,
                    "projection_depth": 0.0,
                },
            },
            {
                "length": 24.0,
                "angle": None,
                "name": "right_wall",
                "window": {
                    "sill_height": 16.0,
                    "head_height": 72.0,
                    "width": 20.0,
                    "projection_depth": 0.0,
                },
            },
        ),
        opening_width=72.0,
        bay_depth=24.0,
        arc_angle=None,
        segment_count=None,
        apex=None,
        apex_mode="auto",
        edge_height=84.0,
        min_cabinet_width=12.0,
        filler_treatment="panel",
        sill_clearance=1.0,
        head_clearance=2.0,
        seat_surface_style="flush",
        flank_integration="match",
        top_style=None,
        shelf_alignment="independent",
    )


@pytest.fixture
def no_windows_bay_config() -> BayAlcoveConfig:
    """3-wall bay with no windows (all full-height cabinets)."""
    return BayAlcoveConfig(
        bay_type="box_bay",
        walls=(
            {"length": 24.0, "angle": 90.0, "name": "left_wall"},
            {"length": 36.0, "angle": 90.0, "name": "center_wall"},
            {"length": 24.0, "angle": 90.0, "name": "right_wall"},
        ),
        opening_width=72.0,
        bay_depth=24.0,
        arc_angle=None,
        segment_count=None,
        apex=None,
        apex_mode="auto",
        edge_height=84.0,
        min_cabinet_width=12.0,
        filler_treatment="none",
        sill_clearance=1.0,
        head_clearance=2.0,
        seat_surface_style="flush",
        flank_integration="match",
        top_style=None,
        shelf_alignment="independent",
    )


@pytest.fixture
def explicit_apex_bay_config() -> BayAlcoveConfig:
    """Bay with explicit apex point specification."""
    apex = ApexPoint(x=36.0, y=12.0, z=96.0)
    return BayAlcoveConfig(
        bay_type="three_wall",
        walls=(
            {"length": 24.0, "angle": None, "name": "left_wall"},
            {"length": 36.0, "angle": None, "name": "center_wall"},
            {"length": 24.0, "angle": None, "name": "right_wall"},
        ),
        opening_width=72.0,
        bay_depth=24.0,
        arc_angle=None,
        segment_count=None,
        apex=apex,
        apex_mode="explicit",
        edge_height=84.0,
        min_cabinet_width=12.0,
        filler_treatment="panel",
        sill_clearance=1.0,
        head_clearance=2.0,
        seat_surface_style="flush",
        flank_integration="match",
        top_style=None,
        shelf_alignment="independent",
    )


@pytest.fixture
def all_narrow_walls_config() -> BayAlcoveConfig:
    """Bay with all walls too narrow for cabinets."""
    return BayAlcoveConfig(
        bay_type="bow",
        walls=(
            {"length": 8.0, "angle": None, "name": "segment_0"},
            {"length": 8.0, "angle": None, "name": "segment_1"},
            {"length": 8.0, "angle": None, "name": "segment_2"},
            {"length": 8.0, "angle": None, "name": "segment_3"},
            {"length": 8.0, "angle": None, "name": "segment_4"},
        ),
        opening_width=40.0,
        bay_depth=12.0,
        arc_angle=120.0,
        segment_count=5,
        apex=None,
        apex_mode="auto",
        edge_height=84.0,
        min_cabinet_width=12.0,
        filler_treatment="panel",
        sill_clearance=1.0,
        head_clearance=2.0,
        seat_surface_style="flush",
        flank_integration="match",
        top_style=None,
        shelf_alignment="independent",
    )


# --- Tests for ZoneType Enum ---


class TestZoneType:
    """Tests for ZoneType enumeration."""

    def test_zone_type_values(self) -> None:
        """Zone types should have expected string values."""
        assert ZoneType.UNDER_WINDOW.value == "under_window"
        assert ZoneType.FULL_HEIGHT.value == "full_height"
        assert ZoneType.ABOVE_WINDOW.value == "above_window"
        assert ZoneType.FILLER.value == "filler"

    def test_zone_type_is_string_enum(self) -> None:
        """ZoneType should be a string enum for serialization."""
        assert isinstance(ZoneType.UNDER_WINDOW, str)
        assert ZoneType.UNDER_WINDOW == "under_window"


# --- Tests for WallZone Dataclass ---


class TestWallZone:
    """Tests for WallZone dataclass."""

    def test_wall_zone_creation(self) -> None:
        """WallZone should be created with all required fields."""
        zone = WallZone(
            wall_index=0,
            zone_type=ZoneType.UNDER_WINDOW,
            height=17.0,
            width=24.0,
            depth=16.0,
            angle=45.0,
            window_sill=18.0,
            window_head=72.0,
            use_window_seat=True,
            filler_treatment="panel",
        )

        assert zone.wall_index == 0
        assert zone.zone_type == ZoneType.UNDER_WINDOW
        assert zone.height == 17.0
        assert zone.width == 24.0
        assert zone.depth == 16.0
        assert zone.angle == 45.0
        assert zone.window_sill == 18.0
        assert zone.window_head == 72.0
        assert zone.use_window_seat is True
        assert zone.filler_treatment == "panel"

    def test_wall_zone_no_window(self) -> None:
        """WallZone can have None for window fields."""
        zone = WallZone(
            wall_index=1,
            zone_type=ZoneType.FULL_HEIGHT,
            height=84.0,
            width=36.0,
            depth=24.0,
            angle=90.0,
            window_sill=None,
            window_head=None,
            use_window_seat=False,
            filler_treatment="none",
        )

        assert zone.window_sill is None
        assert zone.window_head is None
        assert zone.use_window_seat is False


# --- Tests for BayAlcoveLayoutService ---


class TestBayAlcoveLayoutServiceInit:
    """Tests for BayAlcoveLayoutService initialization."""

    def test_service_initialization(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Service should initialize with bay config."""
        service = BayAlcoveLayoutService(three_wall_bay_config)

        assert service.bay_config is three_wall_bay_config
        assert service.ceiling_service is not None
        assert service._zones is None

    def test_ceiling_service_created(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Service should create a RadialCeilingService."""
        service = BayAlcoveLayoutService(three_wall_bay_config)

        # Verify ceiling service works
        apex = service.ceiling_service.compute_apex_point()
        assert apex.z > 0


class TestClassifyWallZones:
    """Tests for classify_wall_zones method."""

    def test_three_wall_bay_classification(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """3-wall bay should have correct zone types."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        zones = service.classify_wall_zones()

        assert len(zones) == 3

        # Left wall: full height (no window, wide enough)
        assert zones[0].zone_type == ZoneType.FULL_HEIGHT
        assert zones[0].wall_index == 0

        # Center wall: under window
        assert zones[1].zone_type == ZoneType.UNDER_WINDOW
        assert zones[1].wall_index == 1
        assert zones[1].use_window_seat is True

        # Right wall: full height (no window, wide enough)
        assert zones[2].zone_type == ZoneType.FULL_HEIGHT
        assert zones[2].wall_index == 2

    def test_filler_zone_detection(self, five_wall_bay_config: BayAlcoveConfig) -> None:
        """Narrow walls should be classified as filler zones."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        zones = service.classify_wall_zones()

        assert len(zones) == 5

        # Walls 1 and 3 are mullions (8" < 12" min_cabinet_width)
        assert zones[1].zone_type == ZoneType.FILLER
        assert zones[3].zone_type == ZoneType.FILLER

        # Other walls should not be fillers
        assert zones[0].zone_type == ZoneType.FULL_HEIGHT
        assert zones[2].zone_type == ZoneType.UNDER_WINDOW
        assert zones[4].zone_type == ZoneType.FULL_HEIGHT

    def test_all_windows_classification(
        self, all_windows_bay_config: BayAlcoveConfig
    ) -> None:
        """Bay with windows on all walls should all be under_window."""
        service = BayAlcoveLayoutService(all_windows_bay_config)
        zones = service.classify_wall_zones()

        assert len(zones) == 3
        for zone in zones:
            assert zone.zone_type == ZoneType.UNDER_WINDOW
            assert zone.use_window_seat is True
            assert zone.window_sill is not None

    def test_no_windows_classification(
        self, no_windows_bay_config: BayAlcoveConfig
    ) -> None:
        """Bay with no windows should all be full_height."""
        service = BayAlcoveLayoutService(no_windows_bay_config)
        zones = service.classify_wall_zones()

        assert len(zones) == 3
        for zone in zones:
            assert zone.zone_type == ZoneType.FULL_HEIGHT
            assert zone.use_window_seat is False
            assert zone.window_sill is None

    def test_zone_heights_under_window(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Under-window zone height should be sill_height - sill_clearance."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        zones = service.classify_wall_zones()

        # Center wall has window with sill at 18", clearance is 1"
        center_zone = zones[1]
        assert center_zone.zone_type == ZoneType.UNDER_WINDOW
        assert center_zone.height == 17.0  # 18 - 1

    def test_zone_widths(self, three_wall_bay_config: BayAlcoveConfig) -> None:
        """Zone widths should match wall lengths."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        zones = service.classify_wall_zones()

        assert zones[0].width == 24.0
        assert zones[1].width == 36.0
        assert zones[2].width == 24.0

    def test_zone_depths(self, three_wall_bay_config: BayAlcoveConfig) -> None:
        """Zone depths should use bay_depth."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        zones = service.classify_wall_zones()

        for zone in zones:
            assert zone.depth == 24.0  # bay_depth from config

    def test_filler_treatment_propagation(
        self, five_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Filler treatment should be propagated to zones."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        zones = service.classify_wall_zones()

        for zone in zones:
            assert zone.filler_treatment == "trim"  # From config

    def test_zones_cached(self, three_wall_bay_config: BayAlcoveConfig) -> None:
        """Zones should be cached after first classification."""
        service = BayAlcoveLayoutService(three_wall_bay_config)

        zones1 = service.classify_wall_zones()
        zones2 = service.classify_wall_zones()

        assert zones1 is zones2  # Same object reference


class TestGetCabinetZones:
    """Tests for get_cabinet_zones method."""

    def test_returns_non_filler_zones(
        self, five_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Should return only zones that get cabinets."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        cabinet_zones = service.get_cabinet_zones()

        # 5 walls, 2 are fillers -> 3 cabinet zones
        assert len(cabinet_zones) == 3

        for zone in cabinet_zones:
            assert zone.zone_type != ZoneType.FILLER

    def test_all_cabinets_when_no_fillers(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Should return all zones when none are fillers."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        cabinet_zones = service.get_cabinet_zones()

        assert len(cabinet_zones) == 3

    def test_no_cabinets_when_all_narrow(
        self, all_narrow_walls_config: BayAlcoveConfig
    ) -> None:
        """Should return empty list when all walls are too narrow."""
        service = BayAlcoveLayoutService(all_narrow_walls_config)
        cabinet_zones = service.get_cabinet_zones()

        assert len(cabinet_zones) == 0


class TestGetFillerZones:
    """Tests for get_filler_zones method."""

    def test_returns_only_filler_zones(
        self, five_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Should return only filler zones."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        filler_zones = service.get_filler_zones()

        # 2 mullion walls are fillers
        assert len(filler_zones) == 2

        for zone in filler_zones:
            assert zone.zone_type == ZoneType.FILLER

    def test_no_fillers_when_all_wide(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Should return empty list when no walls are fillers."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        filler_zones = service.get_filler_zones()

        assert len(filler_zones) == 0

    def test_all_fillers_when_all_narrow(
        self, all_narrow_walls_config: BayAlcoveConfig
    ) -> None:
        """Should return all zones when all are fillers."""
        service = BayAlcoveLayoutService(all_narrow_walls_config)
        filler_zones = service.get_filler_zones()

        assert len(filler_zones) == 5


class TestGetComponentConfig:
    """Tests for get_component_config method."""

    def test_filler_zone_config(self, five_wall_bay_config: BayAlcoveConfig) -> None:
        """Filler zones should get filler.mullion component config."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        filler_zones = service.get_filler_zones()

        config = service.get_component_config(filler_zones[0])

        assert config["component_type"] == "filler.mullion"
        assert config["style"] == "flat"

    def test_under_window_zone_config(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Under-window zones should get windowseat.storage config."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        zones = service.classify_wall_zones()
        under_window_zone = zones[1]  # Center wall

        config = service.get_component_config(under_window_zone)

        assert config["component_type"] == "windowseat.storage"
        assert config["seat_height"] == under_window_zone.height
        assert config["access_type"] == "hinged_top"
        assert config["edge_treatment"] == "eased"

    def test_full_height_zone_config(
        self, no_windows_bay_config: BayAlcoveConfig
    ) -> None:
        """Full-height zones should get cabinet.basic config."""
        service = BayAlcoveLayoutService(no_windows_bay_config)
        zones = service.classify_wall_zones()

        config = service.get_component_config(zones[0])

        assert config["component_type"] == "cabinet.basic"
        assert config["height"] == zones[0].height


class TestFillerHeightCalculation:
    """Tests for filler height calculation."""

    def test_filler_matches_adjacent_window_seat(
        self, five_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Filler height should match adjacent window seat height."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        zones = service.classify_wall_zones()

        # Filler at index 1 is between full-height and under-window
        filler_zone = zones[1]
        adjacent_cabinet = zones[0]  # Full height

        # Filler should match the adjacent full-height cabinet
        assert filler_zone.height == adjacent_cabinet.height

    def test_filler_matches_adjacent_full_height(
        self, five_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Filler adjacent to full-height should match that height."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        zones = service.classify_wall_zones()

        # Filler at index 3 is between under-window and full-height
        filler_zone = zones[3]
        adjacent_cabinet = zones[2]  # Under window: 20 - 1.5 = 18.5

        # Should match the adjacent under-window height
        assert filler_zone.height == adjacent_cabinet.height

    def test_filler_uses_edge_height_when_isolated(
        self, all_narrow_walls_config: BayAlcoveConfig
    ) -> None:
        """Isolated fillers should use edge_height."""
        service = BayAlcoveLayoutService(all_narrow_walls_config)
        zones = service.classify_wall_zones()

        # All walls are fillers, so they should use edge_height
        for zone in zones:
            assert zone.height == 84.0  # edge_height from config


class TestGenerateLayoutSummary:
    """Tests for generate_layout_summary method."""

    def test_summary_structure(self, three_wall_bay_config: BayAlcoveConfig) -> None:
        """Summary should have expected structure."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        summary = service.generate_layout_summary()

        assert "wall_count" in summary
        assert "bay_type" in summary
        assert "cabinet_zones" in summary
        assert "filler_zones" in summary
        assert "zones" in summary
        assert "apex" in summary
        assert "edge_height" in summary
        assert "min_cabinet_width" in summary

    def test_summary_counts(self, five_wall_bay_config: BayAlcoveConfig) -> None:
        """Summary should have correct zone counts."""
        service = BayAlcoveLayoutService(five_wall_bay_config)
        summary = service.generate_layout_summary()

        assert summary["wall_count"] == 5
        assert summary["cabinet_zones"] == 3
        assert summary["filler_zones"] == 2

    def test_summary_zones_detail(self, three_wall_bay_config: BayAlcoveConfig) -> None:
        """Summary zones should have expected detail."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        summary = service.generate_layout_summary()

        zones = summary["zones"]
        assert len(zones) == 3

        for zone_dict in zones:
            assert "wall_index" in zone_dict
            assert "zone_type" in zone_dict
            assert "height" in zone_dict
            assert "width" in zone_dict
            assert "depth" in zone_dict
            assert "angle" in zone_dict
            assert "has_window" in zone_dict
            assert "use_window_seat" in zone_dict
            assert "filler_treatment" in zone_dict

    def test_summary_apex_coordinates(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Summary should include apex coordinates."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        summary = service.generate_layout_summary()

        apex = summary["apex"]
        assert "x" in apex
        assert "y" in apex
        assert "z" in apex
        assert apex["z"] > 0  # Apex should be above floor

    def test_summary_explicit_apex(
        self, explicit_apex_bay_config: BayAlcoveConfig
    ) -> None:
        """Summary with explicit apex should use those coordinates."""
        service = BayAlcoveLayoutService(explicit_apex_bay_config)
        summary = service.generate_layout_summary()

        apex = summary["apex"]
        assert apex["x"] == 36.0
        assert apex["y"] == 12.0
        assert apex["z"] == 96.0

    def test_summary_bay_type(self, no_windows_bay_config: BayAlcoveConfig) -> None:
        """Summary should include bay type."""
        service = BayAlcoveLayoutService(no_windows_bay_config)
        summary = service.generate_layout_summary()

        assert summary["bay_type"] == "box_bay"


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_cache_clears_zones(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """invalidate_cache should clear cached zones."""
        service = BayAlcoveLayoutService(three_wall_bay_config)

        # Populate cache
        zones1 = service.classify_wall_zones()
        assert service._zones is not None

        # Invalidate
        service.invalidate_cache()
        assert service._zones is None

        # Re-classify creates new objects
        zones2 = service.classify_wall_zones()
        assert zones1 is not zones2


class TestRadialCeilingIntegration:
    """Tests for integration with RadialCeilingService."""

    def test_uses_ceiling_service_for_full_height(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Full-height zones should use ceiling service for height."""
        service = BayAlcoveLayoutService(three_wall_bay_config)
        zones = service.classify_wall_zones()

        # Full height zones (0 and 2) should use ceiling service height
        left_zone = zones[0]
        right_zone = zones[2]

        # Heights should be calculated from ceiling geometry
        # With auto apex, these should be close to or at edge_height
        assert left_zone.height > 0
        assert right_zone.height > 0

    def test_ceiling_service_wall_positions(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Wall positions should be computed by ceiling service."""
        service = BayAlcoveLayoutService(three_wall_bay_config)

        # Access ceiling service to verify it computed wall positions
        segments = service.ceiling_service.compute_wall_positions()
        assert len(segments) == 3

        # Each segment should have computed geometry
        for seg in segments:
            assert seg.length > 0
            assert seg.start_point is not None
            assert seg.end_point is not None

    def test_apex_computed_for_zones(
        self, three_wall_bay_config: BayAlcoveConfig
    ) -> None:
        """Apex should be computed and available through ceiling service."""
        service = BayAlcoveLayoutService(three_wall_bay_config)

        # Trigger zone classification (which uses ceiling service)
        service.classify_wall_zones()

        # Apex should be computed
        apex = service.ceiling_service.compute_apex_point()
        assert apex is not None
        assert apex.z > service.bay_config.edge_height


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_wall_bay_raises_error(self) -> None:
        """Single wall bay should raise error (radial ceiling requires 3+ walls)."""
        # Note: RadialCeilingGeometry requires at least 3 facets
        config = BayAlcoveConfig(
            bay_type="custom",
            walls=({"length": 36.0, "angle": None, "name": "single_wall"},),
            opening_width=36.0,
            bay_depth=16.0,
            arc_angle=None,
            segment_count=None,
            apex=None,
            apex_mode="auto",
            edge_height=84.0,
            min_cabinet_width=12.0,
            filler_treatment="none",
            sill_clearance=1.0,
            head_clearance=2.0,
            seat_surface_style="flush",
            flank_integration="match",
            top_style=None,
            shelf_alignment="independent",
        )

        service = BayAlcoveLayoutService(config)
        # Should raise ValueError because RadialCeilingGeometry requires 3+ facets
        with pytest.raises(
            ValueError, match="Radial ceiling requires at least 3 facets"
        ):
            service.classify_wall_zones()

    def test_exact_min_width_wall(self) -> None:
        """Wall exactly at min_cabinet_width should be cabinet, not filler."""
        config = BayAlcoveConfig(
            bay_type="three_wall",
            walls=(
                {"length": 12.0, "angle": None, "name": "exact_min"},  # Exactly 12"
                {"length": 36.0, "angle": None, "name": "center"},
                {"length": 12.0, "angle": None, "name": "exact_min_2"},
            ),
            opening_width=60.0,
            bay_depth=16.0,
            arc_angle=None,
            segment_count=None,
            apex=None,
            apex_mode="auto",
            edge_height=84.0,
            min_cabinet_width=12.0,  # Same as wall width
            filler_treatment="panel",
            sill_clearance=1.0,
            head_clearance=2.0,
            seat_surface_style="flush",
            flank_integration="match",
            top_style=None,
            shelf_alignment="independent",
        )

        service = BayAlcoveLayoutService(config)
        zones = service.classify_wall_zones()

        # All walls are >= min_cabinet_width, so no fillers
        assert all(z.zone_type != ZoneType.FILLER for z in zones)

    def test_default_depth_when_none(self) -> None:
        """Should use default depth (16.0) when bay_depth is None."""
        config = BayAlcoveConfig(
            bay_type="three_wall",
            walls=(
                {"length": 24.0, "angle": None, "name": "wall"},
                {"length": 36.0, "angle": None, "name": "wall"},
                {"length": 24.0, "angle": None, "name": "wall"},
            ),
            opening_width=72.0,
            bay_depth=None,  # Not specified
            arc_angle=None,
            segment_count=None,
            apex=None,
            apex_mode="auto",
            edge_height=84.0,
            min_cabinet_width=12.0,
            filler_treatment="panel",
            sill_clearance=1.0,
            head_clearance=2.0,
            seat_surface_style="flush",
            flank_integration="match",
            top_style=None,
            shelf_alignment="independent",
        )

        service = BayAlcoveLayoutService(config)
        zones = service.classify_wall_zones()

        for zone in zones:
            assert zone.depth == 16.0  # Default depth
