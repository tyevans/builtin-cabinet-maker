"""Unit tests for FRD-23 Bay Window Alcove value objects.

These tests verify:
- BayType and FillerTreatment enum values
- ApexPoint creation, validation, and distance_to calculation
- CeilingFacet creation, validation, and slope_angle calculation
- RadialCeilingGeometry creation, validation, and height_at_point calculation
- PanelType extensions for bay alcove panels
"""

from math import atan2, degrees, sqrt

import pytest

from cabinets.domain.value_objects import (
    ApexPoint,
    BayType,
    CeilingFacet,
    FillerTreatment,
    PanelType,
    Point2D,
    RadialCeilingGeometry,
)


class TestBayType:
    """Tests for BayType enum."""

    def test_three_wall_value(self) -> None:
        """BayType.THREE_WALL should have correct string value."""
        assert BayType.THREE_WALL.value == "three_wall"

    def test_five_wall_value(self) -> None:
        """BayType.FIVE_WALL should have correct string value."""
        assert BayType.FIVE_WALL.value == "five_wall"

    def test_box_bay_value(self) -> None:
        """BayType.BOX_BAY should have correct string value."""
        assert BayType.BOX_BAY.value == "box_bay"

    def test_bow_value(self) -> None:
        """BayType.BOW should have correct string value."""
        assert BayType.BOW.value == "bow"

    def test_custom_value(self) -> None:
        """BayType.CUSTOM should have correct string value."""
        assert BayType.CUSTOM.value == "custom"

    def test_is_string_enum(self) -> None:
        """BayType should be a string enum for JSON serialization."""
        assert isinstance(BayType.THREE_WALL, str)
        assert BayType.THREE_WALL == "three_wall"


class TestFillerTreatment:
    """Tests for FillerTreatment enum."""

    def test_panel_value(self) -> None:
        """FillerTreatment.PANEL should have correct string value."""
        assert FillerTreatment.PANEL.value == "panel"

    def test_trim_value(self) -> None:
        """FillerTreatment.TRIM should have correct string value."""
        assert FillerTreatment.TRIM.value == "trim"

    def test_none_value(self) -> None:
        """FillerTreatment.NONE should have correct string value."""
        assert FillerTreatment.NONE.value == "none"

    def test_is_string_enum(self) -> None:
        """FillerTreatment should be a string enum for JSON serialization."""
        assert isinstance(FillerTreatment.PANEL, str)
        assert FillerTreatment.PANEL == "panel"


class TestPanelTypeBayAlcoveExtensions:
    """Tests for PanelType bay alcove extensions."""

    def test_seat_surface_value(self) -> None:
        """PanelType.SEAT_SURFACE should have correct string value."""
        assert PanelType.SEAT_SURFACE.value == "seat_surface"

    def test_mullion_filler_value(self) -> None:
        """PanelType.MULLION_FILLER should have correct string value."""
        assert PanelType.MULLION_FILLER.value == "mullion_filler"

    def test_apex_infill_value(self) -> None:
        """PanelType.APEX_INFILL should have correct string value."""
        assert PanelType.APEX_INFILL.value == "apex_infill"


class TestApexPoint:
    """Tests for ApexPoint value object."""

    def test_valid_creation(self) -> None:
        """ApexPoint should be created with valid values."""
        apex = ApexPoint(x=24.0, y=36.0, z=108.0)
        assert apex.x == 24.0
        assert apex.y == 36.0
        assert apex.z == 108.0

    def test_valid_creation_with_origin(self) -> None:
        """ApexPoint should accept x=0, y=0."""
        apex = ApexPoint(x=0.0, y=0.0, z=96.0)
        assert apex.x == 0.0
        assert apex.y == 0.0
        assert apex.z == 96.0

    def test_valid_creation_with_negative_xy(self) -> None:
        """ApexPoint should accept negative x and y coordinates."""
        apex = ApexPoint(x=-12.0, y=-6.0, z=120.0)
        assert apex.x == -12.0
        assert apex.y == -6.0

    def test_rejects_zero_height(self) -> None:
        """ApexPoint should reject zero z height."""
        with pytest.raises(ValueError) as exc_info:
            ApexPoint(x=24.0, y=36.0, z=0.0)
        assert "Apex height must be positive" in str(exc_info.value)

    def test_rejects_negative_height(self) -> None:
        """ApexPoint should reject negative z height."""
        with pytest.raises(ValueError) as exc_info:
            ApexPoint(x=24.0, y=36.0, z=-10.0)
        assert "Apex height must be positive" in str(exc_info.value)

    def test_distance_to_same_point(self) -> None:
        """Distance to same horizontal point should be 0."""
        apex = ApexPoint(x=24.0, y=36.0, z=108.0)
        assert apex.distance_to(24.0, 36.0) == pytest.approx(0.0)

    def test_distance_to_horizontal_offset(self) -> None:
        """Distance to horizontally offset point."""
        apex = ApexPoint(x=0.0, y=0.0, z=108.0)
        # Distance to (3, 4) should be 5 (3-4-5 triangle)
        assert apex.distance_to(3.0, 4.0) == pytest.approx(5.0)

    def test_distance_to_negative_coords(self) -> None:
        """Distance calculation should work with negative coordinates."""
        apex = ApexPoint(x=0.0, y=0.0, z=108.0)
        # Distance to (-3, -4) should also be 5
        assert apex.distance_to(-3.0, -4.0) == pytest.approx(5.0)

    def test_distance_to_arbitrary(self) -> None:
        """Distance to arbitrary point."""
        apex = ApexPoint(x=10.0, y=20.0, z=108.0)
        # Distance from (10, 20) to (22, 25)
        expected = sqrt((22 - 10) ** 2 + (25 - 20) ** 2)
        assert apex.distance_to(22.0, 25.0) == pytest.approx(expected)

    def test_is_frozen(self) -> None:
        """ApexPoint should be immutable."""
        apex = ApexPoint(x=24.0, y=36.0, z=108.0)
        with pytest.raises(AttributeError):
            apex.z = 120.0  # type: ignore


class TestCeilingFacet:
    """Tests for CeilingFacet value object."""

    @pytest.fixture
    def apex(self) -> ApexPoint:
        """Create a standard apex point for tests."""
        return ApexPoint(x=0.0, y=0.0, z=120.0)

    @pytest.fixture
    def simple_facet(self, apex: ApexPoint) -> CeilingFacet:
        """Create a simple facet for tests."""
        return CeilingFacet(
            wall_index=0,
            edge_start=Point2D(x=-24.0, y=36.0),
            edge_end=Point2D(x=24.0, y=36.0),
            edge_height=96.0,
            apex=apex,
        )

    def test_valid_creation(self, apex: ApexPoint) -> None:
        """CeilingFacet should be created with valid values."""
        facet = CeilingFacet(
            wall_index=0,
            edge_start=Point2D(x=-24.0, y=36.0),
            edge_end=Point2D(x=24.0, y=36.0),
            edge_height=96.0,
            apex=apex,
        )
        assert facet.wall_index == 0
        assert facet.edge_height == 96.0
        assert facet.apex == apex

    def test_rejects_negative_wall_index(self, apex: ApexPoint) -> None:
        """CeilingFacet should reject negative wall index."""
        with pytest.raises(ValueError) as exc_info:
            CeilingFacet(
                wall_index=-1,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            )
        assert "Wall index must be non-negative" in str(exc_info.value)

    def test_rejects_zero_edge_height(self, apex: ApexPoint) -> None:
        """CeilingFacet should reject zero edge height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=0.0,
                apex=apex,
            )
        assert "Edge height must be positive" in str(exc_info.value)

    def test_rejects_negative_edge_height(self, apex: ApexPoint) -> None:
        """CeilingFacet should reject negative edge height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=-10.0,
                apex=apex,
            )
        assert "Edge height must be positive" in str(exc_info.value)

    def test_rejects_edge_height_at_apex(self, apex: ApexPoint) -> None:
        """CeilingFacet should reject edge height equal to apex height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=120.0,  # Same as apex z
                apex=apex,
            )
        assert "Edge height must be less than apex height" in str(exc_info.value)

    def test_rejects_edge_height_above_apex(self, apex: ApexPoint) -> None:
        """CeilingFacet should reject edge height above apex height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=130.0,  # Above apex z
                apex=apex,
            )
        assert "Edge height must be less than apex height" in str(exc_info.value)

    def test_slope_angle_calculation(self, simple_facet: CeilingFacet) -> None:
        """Slope angle should be calculated correctly."""
        # Edge center is at (0, 36), apex is at (0, 0, 120)
        # Horizontal distance = 36, vertical rise = 120 - 96 = 24
        expected_angle = degrees(atan2(24.0, 36.0))
        assert simple_facet.slope_angle == pytest.approx(expected_angle)

    def test_slope_angle_steep(self) -> None:
        """Slope angle for steep facet."""
        apex = ApexPoint(x=0.0, y=0.0, z=120.0)
        facet = CeilingFacet(
            wall_index=0,
            edge_start=Point2D(x=-6.0, y=6.0),
            edge_end=Point2D(x=6.0, y=6.0),
            edge_height=60.0,
            apex=apex,
        )
        # Edge center is at (0, 6), apex is at (0, 0, 120)
        # Horizontal distance = 6, vertical rise = 120 - 60 = 60
        expected_angle = degrees(atan2(60.0, 6.0))
        assert facet.slope_angle == pytest.approx(expected_angle)

    def test_slope_angle_vertical(self) -> None:
        """Slope angle should be 90 when apex directly above edge."""
        apex = ApexPoint(x=0.0, y=0.0, z=120.0)
        facet = CeilingFacet(
            wall_index=0,
            edge_start=Point2D(x=-12.0, y=0.0),
            edge_end=Point2D(x=12.0, y=0.0),
            edge_height=96.0,
            apex=apex,
        )
        # Edge center is at (0, 0), directly below apex
        assert facet.slope_angle == pytest.approx(90.0)

    def test_height_at_apex(self, apex: ApexPoint) -> None:
        """Height at apex location should be apex height."""
        facet = CeilingFacet(
            wall_index=0,
            edge_start=Point2D(x=-24.0, y=36.0),
            edge_end=Point2D(x=24.0, y=36.0),
            edge_height=96.0,
            apex=apex,
        )
        # At apex location (0, 0), height should be apex z
        assert facet.height_at_point(0.0, 0.0) == pytest.approx(120.0)

    def test_height_at_edge_center(self, simple_facet: CeilingFacet) -> None:
        """Height at edge center should be edge height."""
        # Edge center is at (0, 36)
        assert simple_facet.height_at_point(0.0, 36.0) == pytest.approx(96.0)

    def test_height_at_midpoint(self, simple_facet: CeilingFacet) -> None:
        """Height at midpoint should be interpolated."""
        # Midpoint between apex (0, 0) and edge center (0, 36) is (0, 18)
        # Height should be (120 + 96) / 2 = 108
        assert simple_facet.height_at_point(0.0, 18.0) == pytest.approx(108.0)

    def test_height_beyond_edge(self, simple_facet: CeilingFacet) -> None:
        """Height beyond edge should clamp to edge height."""
        # Point at (0, 72) is beyond edge center (0, 36)
        # t = 72/36 = 2, but clamped to 1
        assert simple_facet.height_at_point(0.0, 72.0) == pytest.approx(96.0)

    def test_is_frozen(self, simple_facet: CeilingFacet) -> None:
        """CeilingFacet should be immutable."""
        with pytest.raises(AttributeError):
            simple_facet.edge_height = 100.0  # type: ignore


class TestRadialCeilingGeometry:
    """Tests for RadialCeilingGeometry value object."""

    @pytest.fixture
    def apex(self) -> ApexPoint:
        """Create a standard apex point for tests."""
        return ApexPoint(x=0.0, y=0.0, z=120.0)

    @pytest.fixture
    def three_facets(self, apex: ApexPoint) -> tuple[CeilingFacet, ...]:
        """Create three facets for a basic bay window ceiling."""
        return (
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-36.0, y=24.0),
                edge_end=Point2D(x=-24.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=1,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=2,
                edge_start=Point2D(x=24.0, y=36.0),
                edge_end=Point2D(x=36.0, y=24.0),
                edge_height=96.0,
                apex=apex,
            ),
        )

    def test_valid_creation(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """RadialCeilingGeometry should be created with valid values."""
        geometry = RadialCeilingGeometry(
            apex=apex,
            facets=three_facets,
            edge_height=96.0,
        )
        assert geometry.apex == apex
        assert len(geometry.facets) == 3
        assert geometry.edge_height == 96.0

    def test_rejects_zero_edge_height(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """RadialCeilingGeometry should reject zero edge height."""
        with pytest.raises(ValueError) as exc_info:
            RadialCeilingGeometry(
                apex=apex,
                facets=three_facets,
                edge_height=0.0,
            )
        assert "Edge height must be positive" in str(exc_info.value)

    def test_rejects_negative_edge_height(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """RadialCeilingGeometry should reject negative edge height."""
        with pytest.raises(ValueError) as exc_info:
            RadialCeilingGeometry(
                apex=apex,
                facets=three_facets,
                edge_height=-10.0,
            )
        assert "Edge height must be positive" in str(exc_info.value)

    def test_rejects_less_than_three_facets(self, apex: ApexPoint) -> None:
        """RadialCeilingGeometry requires at least 3 facets."""
        two_facets = (
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=0.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=1,
                edge_start=Point2D(x=0.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            ),
        )
        with pytest.raises(ValueError) as exc_info:
            RadialCeilingGeometry(
                apex=apex,
                facets=two_facets,
                edge_height=96.0,
            )
        assert "Radial ceiling requires at least 3 facets" in str(exc_info.value)

    def test_rejects_mismatched_apex(self, apex: ApexPoint) -> None:
        """RadialCeilingGeometry should reject facets with different apex."""
        other_apex = ApexPoint(x=10.0, y=10.0, z=130.0)
        facets = (
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-36.0, y=24.0),
                edge_end=Point2D(x=-24.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=1,
                edge_start=Point2D(x=-24.0, y=36.0),
                edge_end=Point2D(x=24.0, y=36.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=2,
                edge_start=Point2D(x=24.0, y=36.0),
                edge_end=Point2D(x=36.0, y=24.0),
                edge_height=96.0,
                apex=other_apex,  # Different apex
            ),
        )
        with pytest.raises(ValueError) as exc_info:
            RadialCeilingGeometry(
                apex=apex,
                facets=facets,
                edge_height=96.0,
            )
        assert "All facets must share the same apex point" in str(exc_info.value)

    def test_height_at_apex_location(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """Height at apex location should be apex height."""
        geometry = RadialCeilingGeometry(
            apex=apex,
            facets=three_facets,
            edge_height=96.0,
        )
        height = geometry.height_at_point(0.0, 0.0)
        assert height is not None
        assert height == pytest.approx(120.0)

    def test_height_at_center_facet(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """Height at center facet edge should be edge height."""
        geometry = RadialCeilingGeometry(
            apex=apex,
            facets=three_facets,
            edge_height=96.0,
        )
        # Center facet edge center is at (0, 36)
        height = geometry.height_at_point(0.0, 36.0)
        assert height is not None
        assert height == pytest.approx(96.0)

    def test_average_slope_angle(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """Average slope angle should be computed correctly."""
        geometry = RadialCeilingGeometry(
            apex=apex,
            facets=three_facets,
            edge_height=96.0,
        )
        avg_angle = geometry.average_slope_angle
        # Should be average of the three facet angles
        expected = sum(f.slope_angle for f in three_facets) / 3
        assert avg_angle == pytest.approx(expected)

    def test_is_frozen(
        self, apex: ApexPoint, three_facets: tuple[CeilingFacet, ...]
    ) -> None:
        """RadialCeilingGeometry should be immutable."""
        geometry = RadialCeilingGeometry(
            apex=apex,
            facets=three_facets,
            edge_height=96.0,
        )
        with pytest.raises(AttributeError):
            geometry.edge_height = 100.0  # type: ignore


class TestCeilingFacetEdgeCases:
    """Edge case tests for ceiling geometry calculations."""

    def test_facet_with_coincident_edge_points(self) -> None:
        """Facet with coincident edge points (degenerate case)."""
        apex = ApexPoint(x=0.0, y=0.0, z=120.0)
        facet = CeilingFacet(
            wall_index=0,
            edge_start=Point2D(x=24.0, y=36.0),
            edge_end=Point2D(x=24.0, y=36.0),  # Same as start
            edge_height=96.0,
            apex=apex,
        )
        # Should still compute valid slope angle
        angle = facet.slope_angle
        assert 0 <= angle <= 90

    def test_geometry_with_symmetric_facets(self) -> None:
        """Symmetric facets should produce consistent heights."""
        apex = ApexPoint(x=0.0, y=0.0, z=120.0)
        # Create symmetric 4-facet arrangement
        facets = (
            CeilingFacet(
                wall_index=0,
                edge_start=Point2D(x=-24.0, y=0.0),
                edge_end=Point2D(x=0.0, y=-24.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=1,
                edge_start=Point2D(x=0.0, y=-24.0),
                edge_end=Point2D(x=24.0, y=0.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=2,
                edge_start=Point2D(x=24.0, y=0.0),
                edge_end=Point2D(x=0.0, y=24.0),
                edge_height=96.0,
                apex=apex,
            ),
            CeilingFacet(
                wall_index=3,
                edge_start=Point2D(x=0.0, y=24.0),
                edge_end=Point2D(x=-24.0, y=0.0),
                edge_height=96.0,
                apex=apex,
            ),
        )
        geometry = RadialCeilingGeometry(
            apex=apex,
            facets=facets,
            edge_height=96.0,
        )

        # Heights at symmetric points should be equal
        h1 = geometry.height_at_point(12.0, 0.0)
        h2 = geometry.height_at_point(-12.0, 0.0)
        h3 = geometry.height_at_point(0.0, 12.0)
        h4 = geometry.height_at_point(0.0, -12.0)

        assert h1 is not None
        assert h2 is not None
        assert h3 is not None
        assert h4 is not None
        # All should be approximately equal due to symmetry
        assert h1 == pytest.approx(h2, rel=0.01)
        assert h1 == pytest.approx(h3, rel=0.01)
        assert h1 == pytest.approx(h4, rel=0.01)
