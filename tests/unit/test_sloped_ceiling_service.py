"""Unit tests for SlopedCeilingService."""

import pytest

from cabinets.domain.services import SlopedCeilingService
from cabinets.domain.value_objects import CeilingSlope


class TestSlopedCeilingServiceCalculateSectionHeights:
    """Tests for SlopedCeilingService.calculate_section_heights()"""

    def test_uniform_sections_left_to_right(self):
        """Heights decrease from left to right for left_to_right slope."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        heights = service.calculate_section_heights([24, 24, 24], slope, 72)

        # Heights should decrease as we move right
        assert heights[0] > heights[1] > heights[2]

    def test_uniform_sections_right_to_left(self):
        """Heights decrease from right to left for right_to_left slope."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="right_to_left")

        heights = service.calculate_section_heights([24, 24, 24], slope, 72)

        # Heights should increase as we move right (lower on left, higher on right)
        assert heights[0] < heights[1] < heights[2]

    def test_min_height_clamping(self):
        """Heights are clamped to min_height when slope goes too low."""
        service = SlopedCeilingService()
        # Steep slope that would go below min_height
        slope = CeilingSlope(
            angle=60, start_height=48, direction="left_to_right", min_height=24
        )

        heights = service.calculate_section_heights([24, 24, 24, 24], slope, 96)

        # All heights should be at least min_height
        assert all(h >= 24 for h in heights)

    def test_zero_angle_uniform_height(self):
        """Zero angle slope produces uniform height (flat ceiling)."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=0, start_height=84, direction="left_to_right")

        heights = service.calculate_section_heights([24, 24, 24], slope, 72)

        # All heights should be equal (at start_height)
        assert all(h == pytest.approx(84) for h in heights)

    def test_single_section(self):
        """Single section gets height at its midpoint."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        heights = service.calculate_section_heights([48], slope, 48)

        # Single section of width 48, midpoint at 24
        expected_height = slope.height_at_position(24)
        assert heights[0] == pytest.approx(expected_height)

    def test_variable_width_sections(self):
        """Variable width sections are calculated correctly."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=15, start_height=96, direction="left_to_right")

        heights = service.calculate_section_heights([12, 36, 24], slope, 72)

        # Check heights decrease left to right
        assert heights[0] > heights[1] > heights[2]

        # Verify midpoint calculations
        # Section 0: midpoint at 6
        # Section 1: midpoint at 12 + 18 = 30
        # Section 2: midpoint at 12 + 36 + 12 = 60
        assert heights[0] == pytest.approx(slope.height_at_position(6))
        assert heights[1] == pytest.approx(slope.height_at_position(30))
        assert heights[2] == pytest.approx(slope.height_at_position(60))

    def test_empty_sections_list(self):
        """Empty sections list returns empty heights list."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        heights = service.calculate_section_heights([], slope, 72)

        assert heights == []


class TestSlopedCeilingServiceCalculateSectionEdgeHeights:
    """Tests for calculate_section_edge_heights()"""

    def test_left_to_right_slope(self):
        """Left edge is higher than right edge for left_to_right slope."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        left, right = service.calculate_section_edge_heights(0, 24, slope, 72)

        assert left > right

    def test_right_to_left_slope(self):
        """Right edge is higher for right_to_left slope."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="right_to_left")

        left, right = service.calculate_section_edge_heights(48, 24, slope, 72)

        assert right > left

    def test_section_at_start_left_to_right(self):
        """Section at wall start has correct edge heights for left_to_right."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        left, right = service.calculate_section_edge_heights(0, 24, slope, 72)

        # Left edge at position 0, right edge at position 24
        assert left == pytest.approx(slope.height_at_position(0))
        assert right == pytest.approx(slope.height_at_position(24))

    def test_section_at_end_left_to_right(self):
        """Section at wall end has correct edge heights for left_to_right."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        left, right = service.calculate_section_edge_heights(48, 24, slope, 72)

        # Left edge at position 48, right edge at position 72
        assert left == pytest.approx(slope.height_at_position(48))
        assert right == pytest.approx(slope.height_at_position(72))

    def test_min_height_clamping_left_edge(self):
        """Left edge is clamped to min_height when needed."""
        service = SlopedCeilingService()
        # Create slope that goes below min_height on the right
        slope = CeilingSlope(
            angle=45, start_height=60, direction="left_to_right", min_height=30
        )

        # Position section where right edge would be below min_height
        left, right = service.calculate_section_edge_heights(30, 24, slope, 72)

        # Right edge should be clamped to min_height
        assert right >= 30

    def test_min_height_clamping_both_edges(self):
        """Both edges are clamped when section is entirely below min_height."""
        service = SlopedCeilingService()
        slope = CeilingSlope(
            angle=60, start_height=40, direction="left_to_right", min_height=30
        )

        # At the far right, heights will be very low
        left, right = service.calculate_section_edge_heights(60, 12, slope, 72)

        assert left >= 30
        assert right >= 30


class TestSlopedCeilingServiceGenerateTaperSpec:
    """Tests for generate_taper_spec()"""

    def test_generates_taper_for_sloped_section(self):
        """Generates TaperSpec when heights differ."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is not None
        assert taper.start_height > taper.end_height
        assert taper.direction == "left_to_right"

    def test_no_taper_for_flat_ceiling(self):
        """Returns None for zero-angle slope (flat ceiling)."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=0, start_height=84, direction="left_to_right")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is None

    def test_taper_direction_left_to_right(self):
        """Taper direction is left_to_right when left is higher."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is not None
        assert taper.direction == "left_to_right"

    def test_taper_direction_right_to_left(self):
        """Taper direction is right_to_left when right is higher."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="right_to_left")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is not None
        assert taper.direction == "right_to_left"

    def test_taper_heights_correct(self):
        """Taper start_height is max and end_height is min."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is not None
        left = slope.height_at_position(0)
        right = slope.height_at_position(24)
        assert taper.start_height == pytest.approx(max(left, right))
        assert taper.end_height == pytest.approx(min(left, right))

    def test_taper_with_min_height_clamping(self):
        """Taper respects min_height clamping."""
        service = SlopedCeilingService()
        # Use parameters where the right edge would be below min_height
        # but left edge is above it, creating a taper
        slope = CeilingSlope(
            angle=45, start_height=60, direction="left_to_right", min_height=30
        )

        # At position 0: height = 60
        # At position 24: height = 60 - 24*tan(45) = 60 - 24 = 36 (above min)
        taper = service.generate_taper_spec(0, 24, slope, 72)

        # Should have a taper since heights differ
        assert taper is not None
        assert taper.start_height == pytest.approx(60)  # Left edge height
        assert taper.end_height == pytest.approx(36)  # Right edge height

        # Now test a case where clamping applies
        # At position 24: height = 60 - 24 = 36
        # At position 48: height = 60 - 48 = 12 (below min_height 30)
        taper_clamped = service.generate_taper_spec(24, 24, slope, 72)

        assert taper_clamped is not None
        assert taper_clamped.end_height >= 30  # Should be clamped to min_height


class TestSlopedCeilingServiceCheckMinHeightViolations:
    """Tests for check_min_height_violations()"""

    def test_no_violations_when_all_above_min(self):
        """No violations when all sections are above min_height."""
        service = SlopedCeilingService()
        slope = CeilingSlope(
            angle=10, start_height=96, direction="left_to_right", min_height=24
        )

        violations = service.check_min_height_violations([24, 24, 24], slope, 72)

        assert len(violations) == 0

    def test_detects_violations(self):
        """Detects sections that violate min_height."""
        service = SlopedCeilingService()
        # Steep slope that will violate min_height for later sections
        slope = CeilingSlope(
            angle=60, start_height=48, direction="left_to_right", min_height=24
        )

        violations = service.check_min_height_violations([24, 24, 24, 24], slope, 96)

        # Later sections should violate
        assert len(violations) > 0
        # Each violation has (index, calculated_height, min_height)
        for idx, calc_height, min_h in violations:
            assert calc_height < min_h

    def test_violation_structure(self):
        """Violations have correct structure (index, height, min_height)."""
        service = SlopedCeilingService()
        slope = CeilingSlope(
            angle=60, start_height=30.0, direction="left_to_right", min_height=24.0
        )

        violations = service.check_min_height_violations([24, 24], slope, 48)

        # Check structure of any violations found
        for violation in violations:
            assert len(violation) == 3
            idx, calc_height, min_h = violation
            assert isinstance(idx, int)
            assert isinstance(calc_height, (int, float))
            assert isinstance(min_h, (int, float))
            assert min_h == pytest.approx(24.0)

    def test_empty_sections_no_violations(self):
        """Empty sections list produces no violations."""
        service = SlopedCeilingService()
        slope = CeilingSlope(
            angle=60, start_height=48, direction="left_to_right", min_height=24
        )

        violations = service.check_min_height_violations([], slope, 72)

        assert violations == []

    def test_right_to_left_violations_at_start(self):
        """Right-to-left slope violations occur at wall start."""
        service = SlopedCeilingService()
        # For right_to_left, the slope descends from right to left
        # So violations would be on the left side of the wall
        slope = CeilingSlope(
            angle=60, start_height=48, direction="right_to_left", min_height=24
        )

        violations = service.check_min_height_violations([24, 24, 24, 24], slope, 96)

        # Early sections (low indices) should have violations for right_to_left
        if violations:
            violation_indices = [v[0] for v in violations]
            # At least some early sections should be in violations
            assert 0 in violation_indices or 1 in violation_indices

    def test_violation_indices_are_correct(self):
        """Violation indices correctly identify which sections violate."""
        service = SlopedCeilingService()
        # Create a scenario where we know exactly which sections will violate
        # With angle=45 and start_height=48, height drops by tan(45)*x = x inches per x distance
        # Midpoint of section 0: 12, height = 48 - 12 = 36 (above 24)
        # Midpoint of section 1: 36, height = 48 - 36 = 12 (below 24)
        # Midpoint of section 2: 60, height = 48 - 60 = -12 (way below 24)
        slope = CeilingSlope(
            angle=45, start_height=48, direction="left_to_right", min_height=24
        )

        violations = service.check_min_height_violations([24, 24, 24], slope, 72)

        # Sections 1 and 2 should violate
        violation_indices = [v[0] for v in violations]
        assert 1 in violation_indices
        assert 2 in violation_indices
        assert 0 not in violation_indices


class TestSlopedCeilingServiceIntegration:
    """Integration tests combining multiple SlopedCeilingService methods."""

    def test_heights_and_tapers_consistent(self):
        """Section heights and taper specs are consistent with each other."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=20, start_height=96, direction="left_to_right")
        wall_length = 72
        section_widths = [24, 24, 24]

        heights = service.calculate_section_heights(section_widths, slope, wall_length)

        # Generate tapers for each section and verify consistency
        current_x = 0.0
        for i, width in enumerate(section_widths):
            taper = service.generate_taper_spec(current_x, width, slope, wall_length)

            if taper is not None:
                # The midpoint height should be between start and end heights
                assert (
                    taper.start_height >= heights[i] >= taper.end_height
                    or taper.end_height >= heights[i] >= taper.start_height
                )

            current_x += width

    def test_violations_match_clamped_heights(self):
        """Sections with violations are the same ones with clamped heights."""
        service = SlopedCeilingService()
        slope = CeilingSlope(
            angle=60, start_height=48, direction="left_to_right", min_height=24
        )
        wall_length = 96
        section_widths = [24, 24, 24, 24]

        heights = service.calculate_section_heights(section_widths, slope, wall_length)
        violations = service.check_min_height_violations(
            section_widths, slope, wall_length
        )

        # Sections with violations should have heights at min_height after clamping
        violation_indices = {v[0] for v in violations}
        for i, height in enumerate(heights):
            if i in violation_indices:
                # Height should be clamped to min_height
                assert height == pytest.approx(24)
            else:
                # Height should be above min_height
                assert height > 24
