"""Unit tests for section width resolution algorithm.

This module tests the SectionSpec dataclass and resolve_section_widths function
from the domain layer. It covers various scenarios including:
- All "fill" sections (equal distribution)
- Mix of fixed and "fill" sections
- Single fixed section
- Error cases (fixed widths exceed total, invalid inputs)
"""

import pytest

from cabinets.domain.section_resolver import (
    SectionSpec,
    SectionWidthError,
    resolve_section_widths,
    validate_section_specs,
)
from cabinets.domain.value_objects import SectionType


class TestSectionSpec:
    """Tests for the SectionSpec dataclass."""

    def test_create_fill_section(self) -> None:
        """Test creating a section with fill width."""
        spec = SectionSpec(width="fill", shelves=3)
        assert spec.width == "fill"
        assert spec.shelves == 3
        assert spec.is_fill is True
        assert spec.fixed_width is None

    def test_create_fixed_width_section(self) -> None:
        """Test creating a section with fixed width."""
        spec = SectionSpec(width=24.0, shelves=5)
        assert spec.width == 24.0
        assert spec.shelves == 5
        assert spec.is_fill is False
        assert spec.fixed_width == 24.0

    def test_create_section_default_shelves(self) -> None:
        """Test that default shelf count is 0."""
        spec = SectionSpec(width="fill")
        assert spec.shelves == 0

    def test_create_section_with_integer_width(self) -> None:
        """Test creating a section with integer width (should work)."""
        spec = SectionSpec(width=24, shelves=3)
        assert spec.fixed_width == 24.0
        assert spec.is_fill is False

    def test_negative_width_raises_error(self) -> None:
        """Test that negative width raises ValueError."""
        with pytest.raises(ValueError, match="width must be positive"):
            SectionSpec(width=-10.0, shelves=3)

    def test_zero_width_raises_error(self) -> None:
        """Test that zero width raises ValueError."""
        with pytest.raises(ValueError, match="width must be positive"):
            SectionSpec(width=0, shelves=3)

    def test_negative_shelves_raises_error(self) -> None:
        """Test that negative shelves raises ValueError."""
        with pytest.raises(ValueError, match="shelves cannot be negative"):
            SectionSpec(width="fill", shelves=-1)

    def test_section_is_immutable(self) -> None:
        """Test that SectionSpec is frozen (immutable)."""
        spec = SectionSpec(width=24.0, shelves=3)
        with pytest.raises(AttributeError):
            spec.width = 30.0  # type: ignore


class TestResolveSectionWidthsAllFill:
    """Tests for resolve_section_widths with all fill sections."""

    def test_single_fill_section(self) -> None:
        """Test single fill section takes all available width."""
        specs = [SectionSpec(width="fill", shelves=3)]
        # 48" total - 2*0.75" walls = 46.5" available
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert len(widths) == 1
        assert widths[0] == pytest.approx(46.5, rel=1e-6)

    def test_two_fill_sections_equal_distribution(self) -> None:
        """Test two fill sections split available width equally."""
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75"
        # Each section: 45.75 / 2 = 22.875"
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert len(widths) == 2
        assert widths[0] == pytest.approx(22.875, rel=1e-6)
        assert widths[1] == pytest.approx(22.875, rel=1e-6)

    def test_three_fill_sections_equal_distribution(self) -> None:
        """Test three fill sections split available width equally."""
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width="fill", shelves=4),
            SectionSpec(width="fill", shelves=5),
        ]
        # 72" - 2*0.75" walls - 2*0.75" dividers = 69"
        # Each section: 69 / 3 = 23"
        widths = resolve_section_widths(specs, total_width=72.0, material_thickness=0.75)
        assert len(widths) == 3
        assert widths[0] == pytest.approx(23.0, rel=1e-6)
        assert widths[1] == pytest.approx(23.0, rel=1e-6)
        assert widths[2] == pytest.approx(23.0, rel=1e-6)


class TestResolveSectionWidthsMixed:
    """Tests for resolve_section_widths with mixed fixed and fill sections."""

    def test_one_fixed_one_fill(self) -> None:
        """Test one fixed section and one fill section."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]
        # 72" - 2*0.75" walls - 1*0.75" divider = 69.75"
        # Fixed: 24"
        # Fill: 69.75 - 24 = 45.75"
        widths = resolve_section_widths(specs, total_width=72.0, material_thickness=0.75)
        assert len(widths) == 2
        assert widths[0] == pytest.approx(24.0, rel=1e-6)
        assert widths[1] == pytest.approx(45.75, rel=1e-6)

    def test_one_fixed_two_fill(self) -> None:
        """Test one fixed section and two fill sections."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
            SectionSpec(width="fill", shelves=5),
        ]
        # 72" - 2*0.75" walls - 2*0.75" dividers = 69"
        # Fixed: 24"
        # Remaining: 69 - 24 = 45"
        # Each fill: 45 / 2 = 22.5"
        widths = resolve_section_widths(specs, total_width=72.0, material_thickness=0.75)
        assert len(widths) == 3
        assert widths[0] == pytest.approx(24.0, rel=1e-6)
        assert widths[1] == pytest.approx(22.5, rel=1e-6)
        assert widths[2] == pytest.approx(22.5, rel=1e-6)

    def test_two_fixed_one_fill(self) -> None:
        """Test two fixed sections and one fill section."""
        specs = [
            SectionSpec(width=20.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
            SectionSpec(width=20.0, shelves=5),
        ]
        # 72" - 2*0.75" walls - 2*0.75" dividers = 69"
        # Fixed: 20 + 20 = 40"
        # Fill: 69 - 40 = 29"
        widths = resolve_section_widths(specs, total_width=72.0, material_thickness=0.75)
        assert len(widths) == 3
        assert widths[0] == pytest.approx(20.0, rel=1e-6)
        assert widths[1] == pytest.approx(29.0, rel=1e-6)
        assert widths[2] == pytest.approx(20.0, rel=1e-6)


class TestResolveSectionWidthsAllFixed:
    """Tests for resolve_section_widths with all fixed sections."""

    def test_single_fixed_section_exact_fit(self) -> None:
        """Test single fixed section that exactly fits available width."""
        specs = [SectionSpec(width=46.5, shelves=3)]
        # 48" - 2*0.75" = 46.5" available, matches fixed width
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert len(widths) == 1
        assert widths[0] == pytest.approx(46.5, rel=1e-6)

    def test_two_fixed_sections_exact_fit(self) -> None:
        """Test two fixed sections that exactly fit available width."""
        specs = [
            SectionSpec(width=22.875, shelves=3),
            SectionSpec(width=22.875, shelves=4),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75"
        # 22.875 + 22.875 = 45.75" matches
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert len(widths) == 2
        assert widths[0] == pytest.approx(22.875, rel=1e-6)
        assert widths[1] == pytest.approx(22.875, rel=1e-6)


class TestResolveSectionWidthsErrors:
    """Tests for error conditions in resolve_section_widths."""

    def test_empty_specs_raises_error(self) -> None:
        """Test that empty specs list raises error."""
        with pytest.raises(SectionWidthError, match="At least one section"):
            resolve_section_widths([], total_width=48.0, material_thickness=0.75)

    def test_fixed_widths_exceed_available_raises_error(self) -> None:
        """Test that fixed widths exceeding available space raises error."""
        specs = [
            SectionSpec(width=30.0, shelves=3),
            SectionSpec(width=30.0, shelves=4),
        ]
        # 48" - 2*0.75" - 0.75" = 45.75" available
        # 30 + 30 = 60" > 45.75"
        with pytest.raises(SectionWidthError, match="exceed available"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)

    def test_fixed_widths_dont_match_available_raises_error(self) -> None:
        """Test that fixed widths not matching available raises error."""
        specs = [
            SectionSpec(width=20.0, shelves=3),
            SectionSpec(width=20.0, shelves=4),
        ]
        # 48" - 2*0.75" - 0.75" = 45.75" available
        # 20 + 20 = 40" != 45.75"
        with pytest.raises(SectionWidthError, match="do not match"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)

    def test_zero_total_width_raises_error(self) -> None:
        """Test that zero total width raises error."""
        specs = [SectionSpec(width="fill", shelves=3)]
        with pytest.raises(SectionWidthError, match="Total width must be positive"):
            resolve_section_widths(specs, total_width=0, material_thickness=0.75)

    def test_negative_total_width_raises_error(self) -> None:
        """Test that negative total width raises error."""
        specs = [SectionSpec(width="fill", shelves=3)]
        with pytest.raises(SectionWidthError, match="Total width must be positive"):
            resolve_section_widths(specs, total_width=-10.0, material_thickness=0.75)

    def test_zero_material_thickness_raises_error(self) -> None:
        """Test that zero material thickness raises error."""
        specs = [SectionSpec(width="fill", shelves=3)]
        with pytest.raises(SectionWidthError, match="Material thickness must be positive"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0)

    def test_no_interior_space_raises_error(self) -> None:
        """Test that no interior space (thickness too big) raises error."""
        specs = [SectionSpec(width="fill", shelves=3)]
        # 10" total with 5" material thickness = 10 - 2*5 = 0" or negative
        with pytest.raises(SectionWidthError, match="No interior space"):
            resolve_section_widths(specs, total_width=10.0, material_thickness=5.0)

    def test_fill_sections_zero_width_raises_error(self) -> None:
        """Test that fill sections with zero remaining width raises error."""
        specs = [
            SectionSpec(width=45.75, shelves=3),  # Takes all available
            SectionSpec(width="fill", shelves=4),  # Would have 0 width
        ]
        # 48" - 2*0.75" - 0.75" = 45.75" available
        # Fixed takes all, fill would have 0
        with pytest.raises(SectionWidthError, match="zero or negative width"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)


class TestValidateSectionSpecs:
    """Tests for the validate_section_specs function."""

    def test_valid_specs_return_empty_list(self) -> None:
        """Test that valid specs return no errors."""
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]
        errors = validate_section_specs(specs, total_width=72.0, material_thickness=0.75)
        assert errors == []

    def test_empty_specs_return_error(self) -> None:
        """Test that empty specs list returns error."""
        errors = validate_section_specs([], total_width=48.0, material_thickness=0.75)
        assert len(errors) == 1
        assert "At least one section" in errors[0]

    def test_invalid_total_width_returns_error(self) -> None:
        """Test that invalid total width returns error."""
        specs = [SectionSpec(width="fill", shelves=3)]
        errors = validate_section_specs(specs, total_width=0, material_thickness=0.75)
        assert len(errors) >= 1
        assert any("Total width" in e for e in errors)

    def test_exceeding_widths_returns_error(self) -> None:
        """Test that exceeding fixed widths returns error."""
        specs = [
            SectionSpec(width=50.0, shelves=3),
            SectionSpec(width=50.0, shelves=4),
        ]
        errors = validate_section_specs(specs, total_width=72.0, material_thickness=0.75)
        assert len(errors) >= 1
        assert any("exceed" in e.lower() for e in errors)


class TestResolveSectionWidthsEdgeCases:
    """Tests for edge cases in resolve_section_widths."""

    def test_large_number_of_fill_sections(self) -> None:
        """Test resolving many fill sections."""
        specs = [SectionSpec(width="fill", shelves=i) for i in range(10)]
        # 120" - 2*0.75" - 9*0.75" = 120 - 8.25 = 111.75"
        # Each: 111.75 / 10 = 11.175"
        widths = resolve_section_widths(specs, total_width=120.0, material_thickness=0.75)
        assert len(widths) == 10
        for width in widths:
            assert width == pytest.approx(11.175, rel=1e-6)

    def test_very_thin_material(self) -> None:
        """Test with very thin material thickness."""
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width="fill", shelves=4),
        ]
        # 48" - 2*0.25" - 1*0.25" = 48 - 0.75 = 47.25"
        # Each: 47.25 / 2 = 23.625"
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.25)
        assert widths[0] == pytest.approx(23.625, rel=1e-6)
        assert widths[1] == pytest.approx(23.625, rel=1e-6)

    def test_very_thick_material(self) -> None:
        """Test with very thick material."""
        specs = [SectionSpec(width="fill", shelves=3)]
        # 48" - 2*2" = 44" available
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=2.0)
        assert widths[0] == pytest.approx(44.0, rel=1e-6)

    def test_fill_first_fixed_last(self) -> None:
        """Test fill section followed by fixed section."""
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width=24.0, shelves=4),
        ]
        # 72" - 2*0.75" - 1*0.75" = 69.75"
        # Fill: 69.75 - 24 = 45.75"
        widths = resolve_section_widths(specs, total_width=72.0, material_thickness=0.75)
        assert widths[0] == pytest.approx(45.75, rel=1e-6)
        assert widths[1] == pytest.approx(24.0, rel=1e-6)

    def test_mixed_fill_fixed_fill(self) -> None:
        """Test fill-fixed-fill pattern."""
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width=20.0, shelves=4),
            SectionSpec(width="fill", shelves=5),
        ]
        # 72" - 2*0.75" - 2*0.75" = 69"
        # Fixed: 20"
        # Remaining: 49"
        # Each fill: 49 / 2 = 24.5"
        widths = resolve_section_widths(specs, total_width=72.0, material_thickness=0.75)
        assert widths[0] == pytest.approx(24.5, rel=1e-6)
        assert widths[1] == pytest.approx(20.0, rel=1e-6)
        assert widths[2] == pytest.approx(24.5, rel=1e-6)

    def test_floating_point_precision(self) -> None:
        """Test that floating point precision is handled correctly."""
        specs = [
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width="fill", shelves=3),
            SectionSpec(width="fill", shelves=3),
        ]
        # 100" - 2*0.75" - 2*0.75" = 97"
        # Each: 97 / 3 = 32.333...
        widths = resolve_section_widths(specs, total_width=100.0, material_thickness=0.75)
        total_resolved = sum(widths)
        # Should approximately equal available width
        assert total_resolved == pytest.approx(97.0, rel=1e-6)


class TestSectionSpecSectionType:
    """Tests for SectionSpec section_type field (FRD-04)."""

    def test_section_type_defaults_to_open(self) -> None:
        """SectionSpec should default section_type to OPEN."""
        spec = SectionSpec(width="fill", shelves=3)
        assert spec.section_type == SectionType.OPEN

    def test_section_type_open(self) -> None:
        """SectionSpec should accept OPEN section type."""
        spec = SectionSpec(width=24.0, shelves=3, section_type=SectionType.OPEN)
        assert spec.section_type == SectionType.OPEN

    def test_section_type_doored(self) -> None:
        """SectionSpec should accept DOORED section type."""
        spec = SectionSpec(width=24.0, shelves=3, section_type=SectionType.DOORED)
        assert spec.section_type == SectionType.DOORED

    def test_section_type_drawers(self) -> None:
        """SectionSpec should accept DRAWERS section type."""
        spec = SectionSpec(width=24.0, shelves=0, section_type=SectionType.DRAWERS)
        assert spec.section_type == SectionType.DRAWERS

    def test_section_type_cubby(self) -> None:
        """SectionSpec should accept CUBBY section type."""
        spec = SectionSpec(width=12.0, shelves=0, section_type=SectionType.CUBBY)
        assert spec.section_type == SectionType.CUBBY

    def test_section_type_with_fill_width(self) -> None:
        """SectionSpec section_type should work with fill width."""
        spec = SectionSpec(width="fill", shelves=4, section_type=SectionType.DOORED)
        assert spec.width == "fill"
        assert spec.section_type == SectionType.DOORED

    def test_multiple_specs_with_different_types(self) -> None:
        """Multiple SectionSpecs can have different section types."""
        specs = [
            SectionSpec(width=24.0, shelves=3, section_type=SectionType.OPEN),
            SectionSpec(width=24.0, shelves=0, section_type=SectionType.DRAWERS),
            SectionSpec(width="fill", shelves=2, section_type=SectionType.DOORED),
        ]
        assert specs[0].section_type == SectionType.OPEN
        assert specs[1].section_type == SectionType.DRAWERS
        assert specs[2].section_type == SectionType.DOORED


class TestSectionSpecDepth:
    """Tests for SectionSpec depth field (FRD-04)."""

    def test_depth_defaults_to_none(self) -> None:
        """SectionSpec depth should default to None."""
        spec = SectionSpec(width="fill", shelves=3)
        assert spec.depth is None

    def test_depth_with_valid_value(self) -> None:
        """SectionSpec should accept valid positive depth."""
        spec = SectionSpec(width=24.0, shelves=3, depth=10.0)
        assert spec.depth == 10.0

    def test_depth_with_integer_value(self) -> None:
        """SectionSpec should accept integer depth value."""
        spec = SectionSpec(width=24.0, shelves=3, depth=12)
        assert spec.depth == 12

    def test_depth_with_small_value(self) -> None:
        """SectionSpec should accept small positive depth."""
        spec = SectionSpec(width=24.0, shelves=3, depth=4.0)
        assert spec.depth == 4.0

    def test_depth_with_large_value(self) -> None:
        """SectionSpec should accept large depth for deep cabinets."""
        spec = SectionSpec(width=24.0, shelves=3, depth=24.0)
        assert spec.depth == 24.0

    def test_zero_depth_raises_error(self) -> None:
        """SectionSpec should reject zero depth."""
        with pytest.raises(ValueError, match="depth must be positive"):
            SectionSpec(width=24.0, shelves=3, depth=0)

    def test_negative_depth_raises_error(self) -> None:
        """SectionSpec should reject negative depth."""
        with pytest.raises(ValueError, match="depth must be positive"):
            SectionSpec(width=24.0, shelves=3, depth=-5.0)

    def test_depth_with_fill_width(self) -> None:
        """SectionSpec depth override should work with fill width."""
        spec = SectionSpec(width="fill", shelves=4, depth=8.0)
        assert spec.width == "fill"
        assert spec.depth == 8.0

    def test_depth_with_section_type(self) -> None:
        """SectionSpec depth should work with section_type."""
        spec = SectionSpec(
            width=24.0, shelves=3, depth=10.0, section_type=SectionType.DOORED
        )
        assert spec.depth == 10.0
        assert spec.section_type == SectionType.DOORED


class TestSectionSpecMinMaxWidth:
    """Tests for SectionSpec min_width/max_width fields (FRD-04)."""

    def test_min_width_defaults_to_six(self) -> None:
        """SectionSpec min_width should default to 6.0."""
        spec = SectionSpec(width="fill", shelves=3)
        assert spec.min_width == 6.0

    def test_max_width_defaults_to_none(self) -> None:
        """SectionSpec max_width should default to None."""
        spec = SectionSpec(width="fill", shelves=3)
        assert spec.max_width is None

    def test_custom_min_width(self) -> None:
        """SectionSpec should accept custom min_width."""
        spec = SectionSpec(width="fill", shelves=3, min_width=10.0)
        assert spec.min_width == 10.0

    def test_custom_max_width(self) -> None:
        """SectionSpec should accept custom max_width."""
        spec = SectionSpec(width="fill", shelves=3, max_width=36.0)
        assert spec.max_width == 36.0

    def test_min_and_max_width_together(self) -> None:
        """SectionSpec should accept both min_width and max_width."""
        spec = SectionSpec(width="fill", shelves=3, min_width=12.0, max_width=30.0)
        assert spec.min_width == 12.0
        assert spec.max_width == 30.0

    def test_min_width_equals_max_width(self) -> None:
        """SectionSpec should accept min_width equal to max_width."""
        spec = SectionSpec(width="fill", shelves=3, min_width=20.0, max_width=20.0)
        assert spec.min_width == 20.0
        assert spec.max_width == 20.0

    def test_zero_min_width_raises_error(self) -> None:
        """SectionSpec should reject zero min_width."""
        with pytest.raises(ValueError, match="min_width must be greater than 0"):
            SectionSpec(width="fill", shelves=3, min_width=0)

    def test_negative_min_width_raises_error(self) -> None:
        """SectionSpec should reject negative min_width."""
        with pytest.raises(ValueError, match="min_width must be greater than 0"):
            SectionSpec(width="fill", shelves=3, min_width=-5.0)

    def test_max_width_less_than_min_width_raises_error(self) -> None:
        """SectionSpec should reject max_width less than min_width."""
        with pytest.raises(
            ValueError, match="max_width must be greater than or equal to min_width"
        ):
            SectionSpec(width="fill", shelves=3, min_width=20.0, max_width=15.0)

    def test_fixed_width_below_min_width_raises_error(self) -> None:
        """SectionSpec should reject fixed width below min_width."""
        with pytest.raises(ValueError, match="below min_width"):
            SectionSpec(width=10.0, shelves=3, min_width=12.0)

    def test_fixed_width_above_max_width_raises_error(self) -> None:
        """SectionSpec should reject fixed width above max_width."""
        with pytest.raises(ValueError, match="exceeds max_width"):
            SectionSpec(width=30.0, shelves=3, max_width=24.0)

    def test_fixed_width_at_min_width_valid(self) -> None:
        """SectionSpec should accept fixed width equal to min_width."""
        spec = SectionSpec(width=12.0, shelves=3, min_width=12.0)
        assert spec.width == 12.0
        assert spec.min_width == 12.0

    def test_fixed_width_at_max_width_valid(self) -> None:
        """SectionSpec should accept fixed width equal to max_width."""
        spec = SectionSpec(width=24.0, shelves=3, max_width=24.0)
        assert spec.width == 24.0
        assert spec.max_width == 24.0

    def test_fixed_width_within_range_valid(self) -> None:
        """SectionSpec should accept fixed width within min/max range."""
        spec = SectionSpec(width=18.0, shelves=3, min_width=12.0, max_width=24.0)
        assert spec.width == 18.0
        assert spec.min_width == 12.0
        assert spec.max_width == 24.0


class TestResolveSectionWidthsMinWidthConstraint:
    """Tests for resolve_section_widths with min_width constraint violations."""

    def test_fill_width_below_min_width_raises_error(self) -> None:
        """Fill section should raise error when calculated width below min_width."""
        specs = [
            SectionSpec(width=80.0, shelves=3),  # Takes most of the space
            SectionSpec(width="fill", shelves=4, min_width=15.0),  # Needs 15" min
        ]
        # 96" - 2*0.75" walls - 1*0.75" divider = 93.75" available
        # Fixed takes 80", leaving 13.75" for fill
        # 13.75" < 15.0" min_width
        with pytest.raises(SectionWidthError, match="below min_width"):
            resolve_section_widths(specs, total_width=96.0, material_thickness=0.75)

    def test_multiple_fill_sections_below_min_width(self) -> None:
        """Multiple fill sections should raise error when any is below min_width."""
        specs = [
            SectionSpec(width="fill", shelves=3, min_width=20.0),
            SectionSpec(width="fill", shelves=4, min_width=20.0),
            SectionSpec(width="fill", shelves=5, min_width=20.0),
        ]
        # 48" - 2*0.75" walls - 2*0.75" dividers = 45" available
        # Each fill: 45 / 3 = 15" which is < 20" min_width
        with pytest.raises(SectionWidthError, match="below min_width"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)

    def test_fill_width_at_min_width_succeeds(self) -> None:
        """Fill section at exactly min_width should succeed."""
        specs = [
            SectionSpec(width=25.5, shelves=3),
            SectionSpec(width="fill", shelves=4, min_width=20.0),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75" available
        # Fixed takes 25.5", leaving 20.25" for fill
        # 20.25" >= 20.0" min_width, should succeed
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert len(widths) == 2
        assert widths[0] == pytest.approx(25.5, rel=1e-6)
        assert widths[1] == pytest.approx(20.25, rel=1e-6)

    def test_fill_width_above_min_width_succeeds(self) -> None:
        """Fill section above min_width should succeed."""
        specs = [
            SectionSpec(width=20.0, shelves=3),
            SectionSpec(width="fill", shelves=4, min_width=10.0),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75" available
        # Fixed takes 20", leaving 25.75" for fill
        # 25.75" > 10.0" min_width
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert widths[1] == pytest.approx(25.75, rel=1e-6)


class TestResolveSectionWidthsMaxWidthConstraint:
    """Tests for resolve_section_widths with max_width constraint violations."""

    def test_fill_width_above_max_width_raises_error(self) -> None:
        """Fill section should raise error when calculated width above max_width."""
        specs = [
            SectionSpec(width="fill", shelves=3, max_width=20.0),
        ]
        # 48" - 2*0.75" walls = 46.5" available
        # Single fill takes all 46.5", which exceeds 20" max_width
        with pytest.raises(SectionWidthError, match="exceeds max_width"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)

    def test_fill_width_at_max_width_succeeds(self) -> None:
        """Fill section at exactly max_width should succeed."""
        specs = [
            SectionSpec(width=26.5, shelves=3),
            SectionSpec(width="fill", shelves=4, max_width=20.0),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75" available
        # Fixed takes 26.5", leaving 19.25" for fill
        # 19.25" <= 20.0" max_width, should succeed
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert len(widths) == 2
        assert widths[0] == pytest.approx(26.5, rel=1e-6)
        assert widths[1] == pytest.approx(19.25, rel=1e-6)

    def test_fill_width_below_max_width_succeeds(self) -> None:
        """Fill section below max_width should succeed."""
        specs = [
            SectionSpec(width=30.0, shelves=3),
            SectionSpec(width="fill", shelves=4, max_width=20.0),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75" available
        # Fixed takes 30", leaving 15.75" for fill
        # 15.75" < 20.0" max_width
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert widths[1] == pytest.approx(15.75, rel=1e-6)

    def test_multiple_fill_sections_above_max_width(self) -> None:
        """Multiple fill sections should raise error when any exceeds max_width."""
        specs = [
            SectionSpec(width="fill", shelves=3, max_width=15.0),
            SectionSpec(width="fill", shelves=4, max_width=15.0),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75" available
        # Each fill: 45.75 / 2 = 22.875", which exceeds 15" max_width
        with pytest.raises(SectionWidthError, match="exceeds max_width"):
            resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)

    def test_fill_with_both_min_and_max_constraints_succeeds(self) -> None:
        """Fill section within min/max range should succeed."""
        specs = [
            SectionSpec(width=25.0, shelves=3),
            SectionSpec(width="fill", shelves=4, min_width=10.0, max_width=25.0),
        ]
        # 48" - 2*0.75" walls - 1*0.75" divider = 45.75" available
        # Fixed takes 25", leaving 20.75" for fill
        # 10" <= 20.75" <= 25", should succeed
        widths = resolve_section_widths(specs, total_width=48.0, material_thickness=0.75)
        assert widths[1] == pytest.approx(20.75, rel=1e-6)


class TestValidateSectionSpecsMinMaxWidth:
    """Tests for validate_section_specs with min/max width constraints."""

    def test_min_width_violation_returns_error(self) -> None:
        """validate_section_specs should return error for min_width violation."""
        specs = [
            SectionSpec(width=80.0, shelves=3),
            SectionSpec(width="fill", shelves=4, min_width=15.0),
        ]
        errors = validate_section_specs(specs, total_width=96.0, material_thickness=0.75)
        assert len(errors) >= 1
        assert any("min_width" in e.lower() for e in errors)

    def test_max_width_violation_returns_error(self) -> None:
        """validate_section_specs should return error for max_width violation."""
        specs = [
            SectionSpec(width="fill", shelves=3, max_width=20.0),
        ]
        errors = validate_section_specs(specs, total_width=48.0, material_thickness=0.75)
        assert len(errors) >= 1
        assert any("max_width" in e.lower() for e in errors)

    def test_invalid_min_width_in_spec_returns_error(self) -> None:
        """validate_section_specs should catch invalid min_width during validation."""
        # This test checks validation logic for specs that manage to exist
        # In practice, __post_init__ would catch min_width <= 0
        specs = [SectionSpec(width="fill", shelves=3, min_width=8.0)]
        errors = validate_section_specs(specs, total_width=48.0, material_thickness=0.75)
        assert len(errors) == 0  # Valid spec

    def test_valid_specs_with_constraints_returns_empty(self) -> None:
        """validate_section_specs should return empty list for valid specs."""
        specs = [
            SectionSpec(width=20.0, shelves=3),
            SectionSpec(width="fill", shelves=4, min_width=10.0, max_width=30.0),
        ]
        errors = validate_section_specs(specs, total_width=48.0, material_thickness=0.75)
        assert errors == []


# ==============================================================================
# Tests for RowSpec and resolve_row_heights
# ==============================================================================

from cabinets.domain.section_resolver import (
    RowSpec,
    RowHeightError,
    resolve_row_heights,
    validate_row_specs,
)


class TestRowSpec:
    """Tests for the RowSpec dataclass."""

    def test_create_fill_row(self) -> None:
        """Test creating a row with fill height."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        spec = RowSpec(height="fill", section_specs=section_specs)
        assert spec.height == "fill"
        assert spec.is_fill is True
        assert spec.fixed_height is None

    def test_create_fixed_height_row(self) -> None:
        """Test creating a row with fixed height."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        spec = RowSpec(height=30.0, section_specs=section_specs)
        assert spec.height == 30.0
        assert spec.is_fill is False
        assert spec.fixed_height == 30.0

    def test_row_with_multiple_sections(self) -> None:
        """Test creating a row with multiple sections."""
        section_specs = (
            SectionSpec(width=24.0, shelves=2),
            SectionSpec(width="fill", shelves=3),
        )
        spec = RowSpec(height=30.0, section_specs=section_specs)
        assert len(spec.section_specs) == 2

    def test_negative_height_raises_error(self) -> None:
        """Test that negative height raises ValueError."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        with pytest.raises(ValueError, match="height must be positive"):
            RowSpec(height=-10.0, section_specs=section_specs)

    def test_zero_height_raises_error(self) -> None:
        """Test that zero height raises ValueError."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        with pytest.raises(ValueError, match="height must be positive"):
            RowSpec(height=0, section_specs=section_specs)

    def test_empty_section_specs_raises_error(self) -> None:
        """Test that empty section_specs raises ValueError."""
        with pytest.raises(ValueError, match="at least one section"):
            RowSpec(height=30.0, section_specs=())

    def test_row_is_immutable(self) -> None:
        """Test that RowSpec is frozen (immutable)."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        spec = RowSpec(height=30.0, section_specs=section_specs)
        with pytest.raises(AttributeError):
            spec.height = 40.0  # type: ignore


class TestResolveRowHeightsAllFill:
    """Tests for resolve_row_heights with all fill rows."""

    def test_single_fill_row(self) -> None:
        """Test single fill row takes all available height."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [RowSpec(height="fill", section_specs=section_specs)]
        # 95" total - 2*0.75" panels = 93.5" available
        heights = resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)
        assert len(heights) == 1
        assert heights[0] == pytest.approx(93.5, rel=1e-6)

    def test_two_fill_rows_equal_distribution(self) -> None:
        """Test two fill rows split available height equally."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height="fill", section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs),
        ]
        # 95" - 2*0.75" panels - 1*0.75" divider = 92.75"
        # Each row: 92.75 / 2 = 46.375"
        heights = resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)
        assert len(heights) == 2
        assert heights[0] == pytest.approx(46.375, rel=1e-6)
        assert heights[1] == pytest.approx(46.375, rel=1e-6)

    def test_four_fill_rows_equal_distribution(self) -> None:
        """Test four fill rows split available height equally."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height="fill", section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs),
        ]
        # 95" - 2*0.75" panels - 3*0.75" dividers = 91.25"
        # Each row: 91.25 / 4 = 22.8125"
        heights = resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)
        assert len(heights) == 4
        for h in heights:
            assert h == pytest.approx(22.8125, rel=1e-6)


class TestResolveRowHeightsMixed:
    """Tests for resolve_row_heights with mixed fixed and fill rows."""

    def test_one_fixed_one_fill(self) -> None:
        """Test one fixed row and one fill row."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=30.0, section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs),
        ]
        # 95" - 2*0.75" panels - 1*0.75" divider = 92.75"
        # Fixed: 30"
        # Fill: 92.75 - 30 = 62.75"
        heights = resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)
        assert len(heights) == 2
        assert heights[0] == pytest.approx(30.0, rel=1e-6)
        assert heights[1] == pytest.approx(62.75, rel=1e-6)

    def test_three_fixed_one_fill(self) -> None:
        """Test three fixed rows and one fill row (example layout)."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=30.0, section_specs=section_specs),  # Bottom doors
            RowSpec(height=10.0, section_specs=section_specs),  # Drawers
            RowSpec(height="fill", section_specs=section_specs),  # Open shelves
            RowSpec(height=12.0, section_specs=section_specs),  # Top cubbies
        ]
        # 95" - 2*0.75" panels - 3*0.75" dividers = 91.25"
        # Fixed: 30 + 10 + 12 = 52"
        # Fill: 91.25 - 52 = 39.25"
        heights = resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)
        assert len(heights) == 4
        assert heights[0] == pytest.approx(30.0, rel=1e-6)
        assert heights[1] == pytest.approx(10.0, rel=1e-6)
        assert heights[2] == pytest.approx(39.25, rel=1e-6)
        assert heights[3] == pytest.approx(12.0, rel=1e-6)


class TestResolveRowHeightsErrors:
    """Tests for error conditions in resolve_row_heights."""

    def test_empty_row_specs_raises_error(self) -> None:
        """Test that empty row specs list raises error."""
        with pytest.raises(RowHeightError, match="At least one row"):
            resolve_row_heights([], total_height=95.0, material_thickness=0.75)

    def test_fixed_heights_exceed_available_raises_error(self) -> None:
        """Test that fixed heights exceeding available space raises error."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=50.0, section_specs=section_specs),
            RowSpec(height=50.0, section_specs=section_specs),
        ]
        # 95" - 2*0.75" - 0.75" = 92.75" available
        # 50 + 50 = 100" > 92.75"
        with pytest.raises(RowHeightError, match="exceed available"):
            resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)

    def test_zero_total_height_raises_error(self) -> None:
        """Test that zero total height raises error."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [RowSpec(height="fill", section_specs=section_specs)]
        with pytest.raises(RowHeightError, match="Total height must be positive"):
            resolve_row_heights(row_specs, total_height=0, material_thickness=0.75)

    def test_fill_rows_zero_height_raises_error(self) -> None:
        """Test that fill rows with zero remaining height raises error."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=92.75, section_specs=section_specs),  # Takes all available
            RowSpec(height="fill", section_specs=section_specs),  # Would have 0 height
        ]
        # 95" - 2*0.75" panels - 1*0.75" divider = 92.75" available
        # First row takes all, fill would have 0
        with pytest.raises(RowHeightError, match="zero or negative height"):
            resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)


class TestResolveRowHeightsMinMaxConstraints:
    """Tests for resolve_row_heights with min/max height constraints."""

    def test_fill_height_below_min_height_raises_error(self) -> None:
        """Fill row should raise error when calculated height below min_height."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=80.0, section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs, min_height=15.0),
        ]
        # 95" - 2*0.75" - 0.75" = 92.75" available
        # Fixed takes 80", leaving 12.75" for fill
        # 12.75" < 15.0" min_height
        with pytest.raises(RowHeightError, match="below min_height"):
            resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)

    def test_fill_height_above_max_height_raises_error(self) -> None:
        """Fill row should raise error when calculated height above max_height."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height="fill", section_specs=section_specs, max_height=50.0),
        ]
        # 95" - 2*0.75" = 93.5" available
        # Single fill takes all 93.5", which exceeds 50" max_height
        with pytest.raises(RowHeightError, match="exceeds max_height"):
            resolve_row_heights(row_specs, total_height=95.0, material_thickness=0.75)


class TestValidateRowSpecs:
    """Tests for the validate_row_specs function."""

    def test_valid_specs_return_empty_list(self) -> None:
        """Test that valid specs return no errors."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=30.0, section_specs=section_specs),
            RowSpec(height="fill", section_specs=section_specs),
        ]
        errors = validate_row_specs(row_specs, total_height=95.0, material_thickness=0.75)
        assert errors == []

    def test_empty_specs_return_error(self) -> None:
        """Test that empty row specs list returns error."""
        errors = validate_row_specs([], total_height=95.0, material_thickness=0.75)
        assert len(errors) == 1
        assert "At least one row" in errors[0]

    def test_exceeding_heights_returns_error(self) -> None:
        """Test that exceeding fixed heights returns error."""
        section_specs = (SectionSpec(width="fill", shelves=3),)
        row_specs = [
            RowSpec(height=50.0, section_specs=section_specs),
            RowSpec(height=50.0, section_specs=section_specs),
        ]
        errors = validate_row_specs(row_specs, total_height=95.0, material_thickness=0.75)
        assert len(errors) >= 1
        assert any("exceed" in e.lower() for e in errors)
