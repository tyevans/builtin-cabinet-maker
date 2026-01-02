"""Unit tests for SkylightVoidService."""

import pytest

from cabinets.domain.services import SkylightVoidService
from cabinets.domain.value_objects import Skylight


class TestSkylightVoidServiceCalculateVoidIntersection:
    """Tests for calculate_void_intersection()"""

    def test_no_intersection_skylight_left_of_section(self):
        """Returns None when skylight is entirely left of section."""
        service = SkylightVoidService()
        skylight = Skylight(x_position=0, width=20, projection_depth=8)

        result = service.calculate_void_intersection(skylight, 24, 24, 12)

        assert result is None

    def test_no_intersection_skylight_right_of_section(self):
        """Returns None when skylight is entirely right of section."""
        service = SkylightVoidService()
        skylight = Skylight(x_position=60, width=20, projection_depth=8)

        result = service.calculate_void_intersection(skylight, 24, 24, 12)

        assert result is None

    def test_full_intersection_skylight_within_section(self):
        """Returns NotchSpec when skylight is entirely within section."""
        service = SkylightVoidService()
        # Skylight from 30-50 within section 24-72
        skylight = Skylight(x_position=30, width=20, projection_depth=8)

        result = service.calculate_void_intersection(skylight, 24, 48, 12)

        assert result is not None
        assert result.x_offset == pytest.approx(6)  # 30 - 24 = 6
        assert result.width == pytest.approx(20)
        assert result.depth == 8
        assert result.edge == "top"

    def test_partial_intersection_left_overlap(self):
        """Returns NotchSpec for partial left overlap."""
        service = SkylightVoidService()
        # Skylight from 20-40, section from 30-60
        skylight = Skylight(x_position=20, width=20, projection_depth=8)

        result = service.calculate_void_intersection(skylight, 30, 30, 12)

        assert result is not None
        assert result.x_offset == pytest.approx(0)  # Starts at section edge
        assert result.width == pytest.approx(10)  # 40 - 30 = 10

    def test_partial_intersection_right_overlap(self):
        """Returns NotchSpec for partial right overlap."""
        service = SkylightVoidService()
        # Skylight from 50-70, section from 24-60
        skylight = Skylight(x_position=50, width=20, projection_depth=8)

        result = service.calculate_void_intersection(skylight, 24, 36, 12)

        assert result is not None
        assert result.x_offset == pytest.approx(26)  # 50 - 24 = 26
        assert result.width == pytest.approx(10)  # 60 - 50 = 10

    def test_angled_projection_expands_void(self):
        """Angled projection expands the void width."""
        service = SkylightVoidService()
        # 75 degree angle will expand void
        skylight = Skylight(
            x_position=36, width=24, projection_depth=8, projection_angle=75
        )

        result = service.calculate_void_intersection(skylight, 24, 48, 12)

        assert result is not None
        # Void is expanded, so width should be > 24
        assert result.width > 24


class TestSkylightVoidServiceCalculateAllIntersections:
    """Tests for calculate_all_intersections()"""

    def test_no_skylights(self):
        """Returns empty list when no skylights."""
        service = SkylightVoidService()

        result = service.calculate_all_intersections([], 24, 24, 12)

        assert result == []

    def test_multiple_skylights_some_intersecting(self):
        """Returns notches only for intersecting skylights."""
        service = SkylightVoidService()
        skylights = [
            Skylight(x_position=0, width=10, projection_depth=8),  # No intersection
            Skylight(x_position=30, width=10, projection_depth=6),  # Intersects
            Skylight(x_position=100, width=10, projection_depth=8),  # No intersection
        ]

        result = service.calculate_all_intersections(skylights, 24, 48, 12)

        assert len(result) == 1
        assert result[0].depth == 6


class TestSkylightVoidServiceGetSectionsWithVoids:
    """Tests for get_sections_with_voids()"""

    def test_maps_sections_to_notches(self):
        """Returns correct mapping of section indices to notches."""
        service = SkylightVoidService()
        # Skylight from 30-44 (narrower to only intersect middle section)
        skylights = [Skylight(x_position=30, width=14, projection_depth=8)]
        sections = [(0, 24), (24, 24), (48, 24)]  # 3 sections, middle one intersects

        result = service.get_sections_with_voids(skylights, sections, 12)

        assert 1 in result  # Second section (24-48) intersects with skylight (30-44)
        assert 0 not in result
        assert 2 not in result

    def test_skylight_spanning_multiple_sections(self):
        """Skylight spanning multiple sections creates notches in each."""
        service = SkylightVoidService()
        # Skylight from 30-50 spans sections 1 and 2
        skylights = [Skylight(x_position=30, width=20, projection_depth=8)]
        sections = [(0, 24), (24, 24), (48, 24)]  # 3 sections

        result = service.get_sections_with_voids(skylights, sections, 12)

        assert 0 not in result  # First section (0-24) doesn't intersect
        assert 1 in result  # Second section (24-48) intersects with skylight (30-50)
        assert 2 in result  # Third section (48-72) intersects with skylight (30-50)
        # Verify the notch dimensions
        assert result[1][0].x_offset == pytest.approx(6)  # 30 - 24 = 6
        assert result[1][0].width == pytest.approx(18)  # 48 - 30 = 18
        assert result[2][0].x_offset == pytest.approx(0)  # Starts at section edge
        assert result[2][0].width == pytest.approx(2)  # 50 - 48 = 2


class TestSkylightVoidServiceCheckVoidExceedsSection:
    """Tests for check_void_exceeds_section()"""

    def test_void_smaller_than_section(self):
        """Returns False when void is smaller than section."""
        service = SkylightVoidService()
        skylight = Skylight(x_position=30, width=12, projection_depth=8)

        result = service.check_void_exceeds_section(skylight, 24, 48, 12)

        assert result is False

    def test_void_larger_than_section(self):
        """Returns True when void completely contains section."""
        service = SkylightVoidService()
        skylight = Skylight(x_position=20, width=60, projection_depth=8)

        result = service.check_void_exceeds_section(skylight, 30, 24, 12)

        assert result is True
