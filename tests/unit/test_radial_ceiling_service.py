"""Unit tests for RadialCeilingService (FRD-23 Phase 3).

Tests for:
- compute_wall_positions() for 3-wall and 5-wall bays
- compute_apex_point() with auto and explicit apex
- compute_ceiling_facets()
- build_radial_ceiling_geometry()
- get_ceiling_height_at() at various points
- get_cabinet_height_for_wall() with and without windows
- Symmetric angle calculation
- Cache invalidation
"""

from __future__ import annotations


import pytest

from cabinets.domain.value_objects import BayAlcoveConfig
from cabinets.domain.services.radial_ceiling_service import (
    RadialCeilingService,
    WallSegmentGeometry,
)
from cabinets.domain.value_objects import (
    ApexPoint,
    CeilingFacet,
    Point2D,
    RadialCeilingGeometry,
)


def create_bay_config(
    walls: list[dict],
    apex: ApexPoint | None = None,
    apex_mode: str = "auto",
    edge_height: float = 84.0,
    sill_clearance: float = 2.0,
    **kwargs,
) -> BayAlcoveConfig:
    """Helper to create BayAlcoveConfig for testing."""
    return BayAlcoveConfig(
        bay_type=kwargs.get("bay_type", "custom"),
        walls=tuple(walls),
        opening_width=kwargs.get("opening_width"),
        bay_depth=kwargs.get("bay_depth"),
        arc_angle=kwargs.get("arc_angle"),
        segment_count=kwargs.get("segment_count"),
        apex=apex,
        apex_mode=apex_mode,
        edge_height=edge_height,
        min_cabinet_width=kwargs.get("min_cabinet_width", 12.0),
        filler_treatment=kwargs.get("filler_treatment", "panel"),
        sill_clearance=sill_clearance,
        head_clearance=kwargs.get("head_clearance", 2.0),
        seat_surface_style=kwargs.get("seat_surface_style", "flat"),
        flank_integration=kwargs.get("flank_integration", "separate"),
        top_style=kwargs.get("top_style"),
        shelf_alignment=kwargs.get("shelf_alignment", "rectangular"),
    )


class TestRadialCeilingServiceInstantiation:
    """Tests for RadialCeilingService instantiation."""

    def test_instantiation(self) -> None:
        """Test that RadialCeilingService can be instantiated."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)
        assert service is not None

    def test_has_compute_wall_positions_method(self) -> None:
        """Test that RadialCeilingService has compute_wall_positions method."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)
        assert hasattr(service, "compute_wall_positions")
        assert callable(service.compute_wall_positions)


class TestComputeWallPositions:
    """Tests for compute_wall_positions method."""

    def test_three_wall_bay_positions(self) -> None:
        """Test wall positions for a 3-wall bay."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        assert len(segments) == 3
        assert all(isinstance(seg, WallSegmentGeometry) for seg in segments)

    def test_first_wall_starts_at_origin(self) -> None:
        """Test that first wall starts at origin."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        assert segments[0].start_point.x == 0.0
        assert segments[0].start_point.y == 0.0

    def test_walls_connect_correctly(self) -> None:
        """Test that each wall starts where the previous one ends."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        for i in range(1, len(segments)):
            prev_end = segments[i - 1].end_point
            curr_start = segments[i].start_point
            assert abs(prev_end.x - curr_start.x) < 1e-10
            assert abs(prev_end.y - curr_start.y) < 1e-10

    def test_wall_length_preserved(self) -> None:
        """Test that wall lengths are preserved."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        for i, seg in enumerate(segments):
            assert seg.length == walls[i]["length"]

    def test_five_wall_bay_positions(self) -> None:
        """Test wall positions for a 5-wall bay."""
        walls = [
            {"length": 24.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 24.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        assert len(segments) == 5
        # Verify all walls connect properly
        for i in range(1, len(segments)):
            prev_end = segments[i - 1].end_point
            curr_start = segments[i].start_point
            assert abs(prev_end.x - curr_start.x) < 1e-10
            assert abs(prev_end.y - curr_start.y) < 1e-10

    def test_symmetric_angle_calculation_three_wall(self) -> None:
        """Test symmetric angle calculation for 3-wall bay."""
        # For 3 walls: exterior turn angle = 180 - (360/3) = 60 degrees
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        # First wall at angle 0
        assert segments[0].angle == 0.0
        # Second wall at angle 60 (0 + 60)
        assert abs(segments[1].angle - 60.0) < 1e-10
        # Third wall at angle 120 (60 + 60)
        assert abs(segments[2].angle - 120.0) < 1e-10

    def test_symmetric_angle_calculation_five_wall(self) -> None:
        """Test symmetric angle calculation for 5-wall bay."""
        # For 5 walls: exterior turn angle = 180 - (360/5) = 108 degrees
        walls = [
            {"length": 24.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 24.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        expected_turn = 180.0 - (360.0 / 5.0)  # 108 degrees
        assert segments[0].angle == 0.0
        assert abs(segments[1].angle - expected_turn) < 1e-10
        assert abs(segments[2].angle - 2 * expected_turn) < 1e-10

    def test_explicit_angles_override_symmetric(self) -> None:
        """Test that explicit angles override symmetric calculation."""
        walls = [
            {"length": 36.0, "angle": None},  # First wall at 0 degrees
            {"length": 48.0, "angle": 45.0},  # Explicit 45 degree turn
            {"length": 36.0, "angle": 45.0},  # Explicit 45 degree turn
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        assert segments[0].angle == 0.0
        assert segments[1].angle == 45.0
        assert segments[2].angle == 90.0

    def test_midpoint_calculation(self) -> None:
        """Test that midpoints are calculated correctly."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()

        for seg in segments:
            expected_mid_x = (seg.start_point.x + seg.end_point.x) / 2
            expected_mid_y = (seg.start_point.y + seg.end_point.y) / 2
            assert abs(seg.midpoint.x - expected_mid_x) < 1e-10
            assert abs(seg.midpoint.y - expected_mid_y) < 1e-10

    def test_caching_returns_same_result(self) -> None:
        """Test that calling compute_wall_positions multiple times returns cached result."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        segments1 = service.compute_wall_positions()
        segments2 = service.compute_wall_positions()

        assert segments1 is segments2


class TestComputeApexPoint:
    """Tests for compute_apex_point method."""

    def test_auto_apex_calculation(self) -> None:
        """Test automatic apex calculation from wall midpoints."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, apex_mode="auto", edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()

        assert isinstance(apex, ApexPoint)
        # Apex z should be edge_height + 12
        assert apex.z == 96.0

    def test_auto_apex_center_calculation(self) -> None:
        """Test that auto apex is centered on wall midpoints."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, apex_mode="auto", edge_height=84.0)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()
        apex = service.compute_apex_point()

        # Calculate expected center
        xs = [s.midpoint.x for s in segments]
        ys = [s.midpoint.y for s in segments]
        expected_x = sum(xs) / len(xs)
        expected_y = sum(ys) / len(ys)

        assert abs(apex.x - expected_x) < 1e-10
        assert abs(apex.y - expected_y) < 1e-10

    def test_explicit_apex(self) -> None:
        """Test using explicit apex point from configuration."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        explicit_apex = ApexPoint(x=10.0, y=20.0, z=96.0)
        config = create_bay_config(
            walls, apex=explicit_apex, apex_mode="explicit", edge_height=84.0
        )
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()

        assert apex.x == 10.0
        assert apex.y == 20.0
        assert apex.z == 96.0

    def test_none_apex_uses_auto(self) -> None:
        """Test that None apex uses auto calculation."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, apex=None, apex_mode="auto", edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()

        # Should compute auto apex
        assert isinstance(apex, ApexPoint)
        assert apex.z == 96.0  # edge_height + 12


class TestComputeCeilingFacets:
    """Tests for compute_ceiling_facets method."""

    def test_facet_count_matches_wall_count(self) -> None:
        """Test that number of facets equals number of walls."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        facets = service.compute_ceiling_facets(apex)

        assert len(facets) == 3

    def test_five_wall_facet_count(self) -> None:
        """Test facet count for 5-wall bay."""
        walls = [
            {"length": 24.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 24.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        facets = service.compute_ceiling_facets(apex)

        assert len(facets) == 5

    def test_facets_are_ceiling_facet_instances(self) -> None:
        """Test that all facets are CeilingFacet instances."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        facets = service.compute_ceiling_facets(apex)

        assert all(isinstance(f, CeilingFacet) for f in facets)

    def test_facets_have_correct_wall_indices(self) -> None:
        """Test that facets have correct wall indices."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        facets = service.compute_ceiling_facets(apex)

        for i, facet in enumerate(facets):
            assert facet.wall_index == i

    def test_facets_share_apex(self) -> None:
        """Test that all facets share the same apex point."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        facets = service.compute_ceiling_facets(apex)

        for facet in facets:
            assert facet.apex == apex

    def test_facets_have_correct_edge_height(self) -> None:
        """Test that facets have correct edge height."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        facets = service.compute_ceiling_facets(apex)

        for facet in facets:
            assert facet.edge_height == 84.0


class TestBuildRadialCeilingGeometry:
    """Tests for build_radial_ceiling_geometry method."""

    def test_returns_radial_ceiling_geometry(self) -> None:
        """Test that method returns RadialCeilingGeometry."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        geometry = service.build_radial_ceiling_geometry()

        assert isinstance(geometry, RadialCeilingGeometry)

    def test_geometry_has_apex(self) -> None:
        """Test that geometry has apex point."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        geometry = service.build_radial_ceiling_geometry()

        assert isinstance(geometry.apex, ApexPoint)

    def test_geometry_has_facets(self) -> None:
        """Test that geometry has facets."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        geometry = service.build_radial_ceiling_geometry()

        assert len(geometry.facets) == 3

    def test_geometry_has_correct_edge_height(self) -> None:
        """Test that geometry has correct edge height."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        geometry = service.build_radial_ceiling_geometry()

        assert geometry.edge_height == 84.0

    def test_caching_returns_same_geometry(self) -> None:
        """Test that calling build twice returns cached geometry."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        geometry1 = service.build_radial_ceiling_geometry()
        geometry2 = service.build_radial_ceiling_geometry()

        assert geometry1 is geometry2


class TestGetCeilingHeightAt:
    """Tests for get_ceiling_height_at method."""

    def test_height_at_apex_is_apex_height(self) -> None:
        """Test that height at apex position is approximately apex height."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()
        height = service.get_ceiling_height_at(apex.x, apex.y)

        # Height at apex should be apex height
        assert height is not None
        assert abs(height - apex.z) < 1e-10

    def test_height_at_wall_midpoint(self) -> None:
        """Test height at wall midpoint is between edge and apex."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        segments = service.compute_wall_positions()
        apex = service.compute_apex_point()

        # Get height at first wall's midpoint
        midpoint = segments[0].midpoint
        height = service.get_ceiling_height_at(midpoint.x, midpoint.y)

        assert height is not None
        # Height should be between edge_height and apex.z
        assert height >= 84.0
        assert height <= apex.z

    def test_height_interpolation(self) -> None:
        """Test that height interpolates linearly from edge to apex."""
        # Use a simple right triangle bay for predictable geometry
        walls = [
            {"length": 36.0, "angle": None},  # Wall at 0 degrees
            {"length": 36.0, "angle": 90.0},  # Wall at 90 degrees
            {"length": 36.0, "angle": 90.0},  # Wall at 180 degrees
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        apex = service.compute_apex_point()

        # Height at different distances from apex should follow linear interpolation
        height_at_apex = service.get_ceiling_height_at(apex.x, apex.y)
        assert height_at_apex is not None


class TestGetCabinetHeightForWall:
    """Tests for get_cabinet_height_for_wall method."""

    def test_wall_without_window_uses_ceiling_height(self) -> None:
        """Test that wall without window uses ceiling height."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        service = RadialCeilingService(config)

        height = service.get_cabinet_height_for_wall(0)

        # Height should be the ceiling height at wall midpoint
        segments = service.compute_wall_positions()
        midpoint = segments[0].midpoint
        ceiling_height = service.get_ceiling_height_at(midpoint.x, midpoint.y)
        assert height == ceiling_height

    def test_wall_with_window_uses_sill_height_minus_clearance(self) -> None:
        """Test that wall with window uses sill height minus clearance."""
        walls = [
            {"length": 36.0, "angle": None},
            {
                "length": 48.0,
                "angle": None,
                "window": {"sill_height": 36.0, "head_height": 72.0},
            },
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0, sill_clearance=2.0)
        service = RadialCeilingService(config)

        height = service.get_cabinet_height_for_wall(1)

        # Height should be sill_height - sill_clearance
        assert height == 34.0  # 36.0 - 2.0

    def test_invalid_wall_index_raises_error(self) -> None:
        """Test that invalid wall index raises ValueError."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        with pytest.raises(ValueError, match="Invalid wall index"):
            service.get_cabinet_height_for_wall(5)

    def test_negative_wall_index_raises_error(self) -> None:
        """Test that negative wall index raises ValueError."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        with pytest.raises(ValueError, match="Invalid wall index"):
            service.get_cabinet_height_for_wall(-1)

    def test_cabinet_height_with_different_sill_clearance(self) -> None:
        """Test cabinet height with different sill clearance values."""
        walls = [
            {"length": 36.0, "angle": None},
            {
                "length": 48.0,
                "angle": None,
                "window": {"sill_height": 36.0, "head_height": 72.0},
            },
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0, sill_clearance=4.0)
        service = RadialCeilingService(config)

        height = service.get_cabinet_height_for_wall(1)

        # Height should be sill_height - sill_clearance
        assert height == 32.0  # 36.0 - 4.0


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_cache_clears_wall_segments(self) -> None:
        """Test that invalidate_cache clears wall segment cache."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        # Build the cache
        service.compute_wall_positions()
        assert service._wall_segments is not None

        # Invalidate
        service.invalidate_cache()
        assert service._wall_segments is None

    def test_invalidate_cache_clears_radial_ceiling(self) -> None:
        """Test that invalidate_cache clears radial ceiling cache."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        service = RadialCeilingService(config)

        # Build the cache
        service.build_radial_ceiling_geometry()
        assert service._radial_ceiling is not None

        # Invalidate
        service.invalidate_cache()
        assert service._radial_ceiling is None


class TestWallSegmentGeometryDataclass:
    """Tests for WallSegmentGeometry dataclass."""

    def test_dataclass_fields(self) -> None:
        """Test that WallSegmentGeometry has expected fields."""
        segment = WallSegmentGeometry(
            index=0,
            start_point=Point2D(0.0, 0.0),
            end_point=Point2D(36.0, 0.0),
            length=36.0,
            angle=0.0,
            midpoint=Point2D(18.0, 0.0),
        )

        assert segment.index == 0
        assert segment.start_point.x == 0.0
        assert segment.start_point.y == 0.0
        assert segment.end_point.x == 36.0
        assert segment.end_point.y == 0.0
        assert segment.length == 36.0
        assert segment.angle == 0.0
        assert segment.midpoint.x == 18.0
        assert segment.midpoint.y == 0.0


class TestImportFromServicesPackage:
    """Tests for importing from services package."""

    def test_import_radial_ceiling_service(self) -> None:
        """Test that RadialCeilingService can be imported from services package."""
        from cabinets.domain.services import RadialCeilingService as RCS

        assert RCS is not None

    def test_import_wall_segment_geometry(self) -> None:
        """Test that WallSegmentGeometry can be imported from services package."""
        from cabinets.domain.services import WallSegmentGeometry as WSG

        assert WSG is not None
