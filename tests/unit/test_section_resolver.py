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
