"""Tests for corner cabinet footprint calculations."""

from __future__ import annotations

import math

import pytest

from cabinets.domain.components import (
    CornerFootprint,
    calculate_blind_corner_footprint,
    calculate_diagonal_footprint,
    calculate_lazy_susan_footprint,
)
from cabinets.domain.components.corner import (
    CornerFootprint as CornerFootprintDirect,
    calculate_blind_corner_footprint as calc_blind_direct,
    calculate_diagonal_footprint as calc_diagonal_direct,
    calculate_lazy_susan_footprint as calc_lazy_susan_direct,
)


class TestCornerFootprintDataclass:
    """Tests for the CornerFootprint dataclass."""

    def test_create_symmetric_footprint(self) -> None:
        """Test creating a symmetric corner footprint."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=24.0)

        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 24.0

    def test_create_asymmetric_footprint(self) -> None:
        """Test creating an asymmetric corner footprint."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=36.0)

        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 36.0

    def test_footprint_is_frozen(self) -> None:
        """Test that CornerFootprint is immutable."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=24.0)

        with pytest.raises(AttributeError):
            footprint.left_wall = 30.0  # type: ignore

    def test_footprint_equality(self) -> None:
        """Test that two footprints with same values are equal."""
        fp1 = CornerFootprint(left_wall=24.0, right_wall=36.0)
        fp2 = CornerFootprint(left_wall=24.0, right_wall=36.0)

        assert fp1 == fp2

    def test_footprint_inequality(self) -> None:
        """Test that footprints with different values are not equal."""
        fp1 = CornerFootprint(left_wall=24.0, right_wall=36.0)
        fp2 = CornerFootprint(left_wall=24.0, right_wall=30.0)

        assert fp1 != fp2

    def test_footprint_hashable(self) -> None:
        """Test that CornerFootprint can be used in sets and as dict keys."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=24.0)

        # Should be able to add to set
        footprint_set = {footprint}
        assert footprint in footprint_set

        # Should be able to use as dict key
        footprint_dict = {footprint: "test"}
        assert footprint_dict[footprint] == "test"

    def test_left_wall_must_be_positive(self) -> None:
        """Test that left_wall must be positive."""
        with pytest.raises(ValueError, match="left_wall must be positive"):
            CornerFootprint(left_wall=0.0, right_wall=24.0)

        with pytest.raises(ValueError, match="left_wall must be positive"):
            CornerFootprint(left_wall=-5.0, right_wall=24.0)

    def test_right_wall_must_be_positive(self) -> None:
        """Test that right_wall must be positive."""
        with pytest.raises(ValueError, match="right_wall must be positive"):
            CornerFootprint(left_wall=24.0, right_wall=0.0)

        with pytest.raises(ValueError, match="right_wall must be positive"):
            CornerFootprint(left_wall=24.0, right_wall=-5.0)

    def test_total_footprint_property(self) -> None:
        """Test total_footprint property calculation."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=36.0)

        assert footprint.total_footprint == 60.0

    def test_is_symmetric_true_for_equal_walls(self) -> None:
        """Test is_symmetric returns True for equal wall values."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=24.0)

        assert footprint.is_symmetric is True

    def test_is_symmetric_false_for_unequal_walls(self) -> None:
        """Test is_symmetric returns False for unequal wall values."""
        footprint = CornerFootprint(left_wall=24.0, right_wall=36.0)

        assert footprint.is_symmetric is False

    def test_is_symmetric_handles_floating_point(self) -> None:
        """Test is_symmetric handles floating point comparison correctly."""
        # Values that are very close but not exactly equal
        footprint = CornerFootprint(left_wall=24.0, right_wall=24.0 + 1e-12)

        assert footprint.is_symmetric is True


class TestCalculateLazySusanFootprint:
    """Tests for calculate_lazy_susan_footprint function."""

    def test_basic_lazy_susan_footprint(self) -> None:
        """Test basic lazy susan footprint calculation."""
        footprint = calculate_lazy_susan_footprint(depth=24.0)

        # Default door_clearance is 2.0
        assert footprint.left_wall == 26.0
        assert footprint.right_wall == 26.0

    def test_lazy_susan_with_custom_clearance(self) -> None:
        """Test lazy susan with custom door clearance."""
        footprint = calculate_lazy_susan_footprint(depth=24.0, door_clearance=3.0)

        assert footprint.left_wall == 27.0
        assert footprint.right_wall == 27.0

    def test_lazy_susan_with_zero_clearance(self) -> None:
        """Test lazy susan with zero door clearance."""
        footprint = calculate_lazy_susan_footprint(depth=24.0, door_clearance=0.0)

        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 24.0

    def test_lazy_susan_is_always_symmetric(self) -> None:
        """Test that lazy susan footprint is always symmetric."""
        footprint = calculate_lazy_susan_footprint(depth=24.0)

        assert footprint.is_symmetric is True

    def test_lazy_susan_standard_base_cabinet(self) -> None:
        """Test lazy susan for standard 24\" base cabinet."""
        footprint = calculate_lazy_susan_footprint(depth=24.0, door_clearance=2.0)

        assert footprint.total_footprint == 52.0  # 26 + 26

    def test_lazy_susan_standard_wall_cabinet(self) -> None:
        """Test lazy susan for standard 12\" wall cabinet."""
        footprint = calculate_lazy_susan_footprint(depth=12.0, door_clearance=2.0)

        assert footprint.left_wall == 14.0
        assert footprint.right_wall == 14.0

    def test_lazy_susan_depth_must_be_positive(self) -> None:
        """Test that depth must be positive."""
        with pytest.raises(ValueError, match="depth must be positive"):
            calculate_lazy_susan_footprint(depth=0.0)

        with pytest.raises(ValueError, match="depth must be positive"):
            calculate_lazy_susan_footprint(depth=-10.0)

    def test_lazy_susan_clearance_must_be_non_negative(self) -> None:
        """Test that door_clearance must be non-negative."""
        with pytest.raises(ValueError, match="door_clearance must be non-negative"):
            calculate_lazy_susan_footprint(depth=24.0, door_clearance=-1.0)


class TestCalculateBlindCornerFootprint:
    """Tests for calculate_blind_corner_footprint function."""

    def test_basic_blind_corner_left(self) -> None:
        """Test basic blind corner with blind side on left."""
        footprint = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=36.0,
            filler_width=3.0,
            blind_side="left",
        )

        assert footprint.left_wall == 24.0  # Blind side = depth
        assert footprint.right_wall == 39.0  # Accessible = width + filler

    def test_basic_blind_corner_right(self) -> None:
        """Test basic blind corner with blind side on right."""
        footprint = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=36.0,
            filler_width=3.0,
            blind_side="right",
        )

        assert footprint.left_wall == 39.0  # Accessible = width + filler
        assert footprint.right_wall == 24.0  # Blind side = depth

    def test_blind_corner_default_filler(self) -> None:
        """Test blind corner with default 3\" filler."""
        footprint = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=30.0,
        )

        # Default is blind_side="left"
        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 33.0  # 30 + 3 default filler

    def test_blind_corner_zero_filler(self) -> None:
        """Test blind corner with zero filler width."""
        footprint = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=36.0,
            filler_width=0.0,
            blind_side="left",
        )

        assert footprint.right_wall == 36.0  # No filler added

    def test_blind_corner_is_asymmetric(self) -> None:
        """Test that blind corner footprint is asymmetric."""
        footprint = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=36.0,
        )

        assert footprint.is_symmetric is False

    def test_blind_corner_total_footprint(self) -> None:
        """Test total footprint calculation for blind corner."""
        footprint = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=36.0,
            filler_width=3.0,
        )

        assert footprint.total_footprint == 63.0  # 24 + 39

    def test_blind_corner_depth_must_be_positive(self) -> None:
        """Test that depth must be positive."""
        with pytest.raises(ValueError, match="depth must be positive"):
            calculate_blind_corner_footprint(
                depth=0.0,
                accessible_width=36.0,
            )

        with pytest.raises(ValueError, match="depth must be positive"):
            calculate_blind_corner_footprint(
                depth=-10.0,
                accessible_width=36.0,
            )

    def test_blind_corner_accessible_width_must_be_positive(self) -> None:
        """Test that accessible_width must be positive."""
        with pytest.raises(ValueError, match="accessible_width must be positive"):
            calculate_blind_corner_footprint(
                depth=24.0,
                accessible_width=0.0,
            )

        with pytest.raises(ValueError, match="accessible_width must be positive"):
            calculate_blind_corner_footprint(
                depth=24.0,
                accessible_width=-10.0,
            )

    def test_blind_corner_filler_must_be_non_negative(self) -> None:
        """Test that filler_width must be non-negative."""
        with pytest.raises(ValueError, match="filler_width must be non-negative"):
            calculate_blind_corner_footprint(
                depth=24.0,
                accessible_width=36.0,
                filler_width=-1.0,
            )

    def test_blind_corner_invalid_blind_side(self) -> None:
        """Test that blind_side must be 'left' or 'right'."""
        with pytest.raises(ValueError, match="blind_side must be 'left' or 'right'"):
            calculate_blind_corner_footprint(
                depth=24.0,
                accessible_width=36.0,
                blind_side="center",
            )

        with pytest.raises(ValueError, match="blind_side must be 'left' or 'right'"):
            calculate_blind_corner_footprint(
                depth=24.0,
                accessible_width=36.0,
                blind_side="",
            )

    def test_blind_corner_wall_cabinet_dimensions(self) -> None:
        """Test blind corner for wall cabinet (12\" depth)."""
        footprint = calculate_blind_corner_footprint(
            depth=12.0,
            accessible_width=24.0,
            filler_width=3.0,
            blind_side="left",
        )

        assert footprint.left_wall == 12.0
        assert footprint.right_wall == 27.0


class TestCalculateDiagonalFootprint:
    """Tests for calculate_diagonal_footprint function."""

    def test_basic_diagonal_footprint(self) -> None:
        """Test basic diagonal footprint calculation."""
        footprint = calculate_diagonal_footprint(depth=24.0)

        # Each wall equals the depth for a 45-degree diagonal
        assert footprint.left_wall == 24.0
        assert footprint.right_wall == 24.0

    def test_diagonal_is_always_symmetric(self) -> None:
        """Test that diagonal footprint is always symmetric."""
        footprint = calculate_diagonal_footprint(depth=24.0)

        assert footprint.is_symmetric is True

    def test_diagonal_total_footprint(self) -> None:
        """Test total footprint for diagonal cabinet."""
        footprint = calculate_diagonal_footprint(depth=24.0)

        assert footprint.total_footprint == 48.0  # 24 + 24

    def test_diagonal_wall_cabinet(self) -> None:
        """Test diagonal for wall cabinet (12\" depth)."""
        footprint = calculate_diagonal_footprint(depth=12.0)

        assert footprint.left_wall == 12.0
        assert footprint.right_wall == 12.0

    def test_diagonal_depth_must_be_positive(self) -> None:
        """Test that depth must be positive."""
        with pytest.raises(ValueError, match="depth must be positive"):
            calculate_diagonal_footprint(depth=0.0)

        with pytest.raises(ValueError, match="depth must be positive"):
            calculate_diagonal_footprint(depth=-10.0)

    def test_diagonal_various_depths(self) -> None:
        """Test diagonal footprint with various depths."""
        depths = [12.0, 18.0, 24.0, 30.0]

        for depth in depths:
            footprint = calculate_diagonal_footprint(depth=depth)
            assert footprint.left_wall == depth
            assert footprint.right_wall == depth

    def test_diagonal_face_width_calculation(self) -> None:
        """Test the relationship between depth and diagonal face width.

        The diagonal face width = depth * sqrt(2).
        This test documents the expected geometric relationship.
        """
        depth = 24.0
        footprint = calculate_diagonal_footprint(depth=depth)

        # The diagonal face would be depth * sqrt(2)
        expected_diagonal_face = depth * math.sqrt(2)
        assert expected_diagonal_face == pytest.approx(33.94, abs=0.01)

        # But the wall footprints equal the depth
        assert footprint.left_wall == depth
        assert footprint.right_wall == depth


class TestCornerFootprintComparisons:
    """Tests comparing different corner cabinet types."""

    def test_lazy_susan_vs_diagonal_same_depth(self) -> None:
        """Compare lazy susan and diagonal footprints for same depth."""
        lazy_susan = calculate_lazy_susan_footprint(depth=24.0, door_clearance=0.0)
        diagonal = calculate_diagonal_footprint(depth=24.0)

        # With no door clearance, they should be identical
        assert lazy_susan.left_wall == diagonal.left_wall
        assert lazy_susan.right_wall == diagonal.right_wall

    def test_lazy_susan_larger_than_diagonal_with_clearance(self) -> None:
        """Test that lazy susan with clearance is larger than diagonal."""
        lazy_susan = calculate_lazy_susan_footprint(depth=24.0, door_clearance=2.0)
        diagonal = calculate_diagonal_footprint(depth=24.0)

        assert lazy_susan.total_footprint > diagonal.total_footprint

    def test_blind_corner_asymmetric_vs_symmetric(self) -> None:
        """Test that blind corner is asymmetric while others are symmetric."""
        lazy_susan = calculate_lazy_susan_footprint(depth=24.0)
        diagonal = calculate_diagonal_footprint(depth=24.0)
        blind = calculate_blind_corner_footprint(depth=24.0, accessible_width=36.0)

        assert lazy_susan.is_symmetric is True
        assert diagonal.is_symmetric is True
        assert blind.is_symmetric is False

    def test_blind_corner_has_largest_footprint(self) -> None:
        """Test that blind corner typically has the largest total footprint."""
        lazy_susan = calculate_lazy_susan_footprint(depth=24.0, door_clearance=2.0)
        diagonal = calculate_diagonal_footprint(depth=24.0)
        blind = calculate_blind_corner_footprint(
            depth=24.0,
            accessible_width=36.0,
            filler_width=3.0,
        )

        assert blind.total_footprint > lazy_susan.total_footprint
        assert blind.total_footprint > diagonal.total_footprint


class TestModuleExports:
    """Tests for module exports and imports."""

    def test_corner_footprint_exported_from_components(self) -> None:
        """Test that CornerFootprint is exported from components package."""
        from cabinets.domain.components import CornerFootprint as CF

        footprint = CF(left_wall=24.0, right_wall=24.0)
        assert footprint.is_symmetric is True

    def test_lazy_susan_function_exported_from_components(self) -> None:
        """Test that calculate_lazy_susan_footprint is exported."""
        from cabinets.domain.components import calculate_lazy_susan_footprint as calc

        footprint = calc(depth=24.0)
        assert footprint.left_wall == 26.0

    def test_blind_corner_function_exported_from_components(self) -> None:
        """Test that calculate_blind_corner_footprint is exported."""
        from cabinets.domain.components import calculate_blind_corner_footprint as calc

        footprint = calc(depth=24.0, accessible_width=36.0)
        assert footprint.left_wall == 24.0

    def test_diagonal_function_exported_from_components(self) -> None:
        """Test that calculate_diagonal_footprint is exported."""
        from cabinets.domain.components import calculate_diagonal_footprint as calc

        footprint = calc(depth=24.0)
        assert footprint.left_wall == 24.0

    def test_direct_import_from_corner_module(self) -> None:
        """Test direct import from corner module works."""
        # These are imported at the top of the file
        footprint = CornerFootprintDirect(left_wall=12.0, right_wall=12.0)
        assert footprint.total_footprint == 24.0

        lazy = calc_lazy_susan_direct(depth=12.0)
        assert lazy.is_symmetric is True

        blind = calc_blind_direct(depth=12.0, accessible_width=24.0)
        assert blind.is_symmetric is False

        diag = calc_diagonal_direct(depth=12.0)
        assert diag.left_wall == 12.0


class TestEdgeCases:
    """Edge case tests for corner cabinet calculations."""

    def test_very_small_depth(self) -> None:
        """Test with very small depth values."""
        footprint = calculate_diagonal_footprint(depth=0.001)
        assert footprint.left_wall == pytest.approx(0.001)
        assert footprint.right_wall == pytest.approx(0.001)

    def test_very_large_depth(self) -> None:
        """Test with very large depth values."""
        footprint = calculate_diagonal_footprint(depth=10000.0)
        assert footprint.left_wall == 10000.0
        assert footprint.right_wall == 10000.0

    def test_floating_point_precision(self) -> None:
        """Test that floating point calculations maintain precision."""
        footprint = calculate_lazy_susan_footprint(depth=23.999, door_clearance=2.001)
        assert footprint.left_wall == pytest.approx(26.0, abs=0.001)

    def test_blind_corner_minimum_practical_dimensions(self) -> None:
        """Test blind corner with minimum practical dimensions."""
        footprint = calculate_blind_corner_footprint(
            depth=12.0,  # Minimum practical depth
            accessible_width=12.0,  # Minimum practical width
            filler_width=1.5,  # Minimum practical filler
        )
        assert footprint.total_footprint == 25.5  # 12 + 13.5

    def test_blind_corner_maximum_practical_dimensions(self) -> None:
        """Test blind corner with maximum practical dimensions."""
        footprint = calculate_blind_corner_footprint(
            depth=36.0,  # Large depth
            accessible_width=48.0,  # Large width
            filler_width=6.0,  # Large filler
        )
        assert footprint.total_footprint == 90.0  # 36 + 54


class TestPanelTypeEnumValues:
    """Tests for new PanelType enum values added for corner cabinets."""

    def test_diagonal_face_panel_type_exists(self) -> None:
        """Test that DIAGONAL_FACE panel type exists."""
        from cabinets.domain.value_objects import PanelType

        assert hasattr(PanelType, "DIAGONAL_FACE")
        assert PanelType.DIAGONAL_FACE.value == "diagonal_face"

    def test_filler_panel_type_exists(self) -> None:
        """Test that FILLER panel type exists."""
        from cabinets.domain.value_objects import PanelType

        assert hasattr(PanelType, "FILLER")
        assert PanelType.FILLER.value == "filler"

    def test_panel_type_enum_includes_all_original_values(self) -> None:
        """Test that all original PanelType values still exist."""
        from cabinets.domain.value_objects import PanelType

        original_types = [
            "TOP",
            "BOTTOM",
            "LEFT_SIDE",
            "RIGHT_SIDE",
            "BACK",
            "SHELF",
            "DIVIDER",
            "DOOR",
            "DRAWER_FRONT",
            "DRAWER_SIDE",
            "DRAWER_BOX_FRONT",
            "DRAWER_BOTTOM",
        ]

        for type_name in original_types:
            assert hasattr(PanelType, type_name), f"Missing PanelType.{type_name}"

    def test_panel_type_new_values_are_distinct(self) -> None:
        """Test that new PanelType values are distinct from existing ones."""
        from cabinets.domain.value_objects import PanelType

        values = [pt.value for pt in PanelType]
        assert len(values) == len(set(values)), "Duplicate PanelType values found"


# =============================================================================
# Phase 2: LazySusanCornerComponent Tests
# =============================================================================

from cabinets.domain.components import (
    ComponentContext,
    LazySusanCornerComponent,
    component_registry,
)
from cabinets.domain.components.corner import LazySusanCornerComponent as LazySusanDirect
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard component context for testing."""
    return ComponentContext(
        width=24.0,
        height=34.5,  # Standard base cabinet height
        depth=24.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=24.0,
        cabinet_height=34.5,
        cabinet_depth=24.0,
    )


@pytest.fixture
def lazy_susan_component() -> LazySusanCornerComponent:
    """Create a LazySusanCornerComponent instance."""
    return LazySusanCornerComponent()


class TestLazySusanComponentRegistration:
    """Tests for LazySusanCornerComponent registration."""

    def test_component_registered_with_correct_id(self) -> None:
        """Test that component is registered under 'corner.lazy_susan'."""
        component_cls = component_registry.get("corner.lazy_susan")
        assert component_cls is LazySusanCornerComponent

    def test_component_in_registry_list(self) -> None:
        """Test that component ID appears in registry list."""
        registered = component_registry.list()
        assert "corner.lazy_susan" in registered

    def test_component_can_be_imported_from_package(self) -> None:
        """Test that component can be imported from components package."""
        from cabinets.domain.components import LazySusanCornerComponent as LS

        assert LS is LazySusanCornerComponent

    def test_direct_import_from_corner_module(self) -> None:
        """Test that component can be imported directly from corner module."""
        assert LazySusanDirect is LazySusanCornerComponent


class TestLazySusanValidation:
    """Tests for LazySusanCornerComponent validation."""

    def test_validate_default_config(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with default configuration."""
        config: dict = {}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_explicit_tray_diameter(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with explicit tray diameter."""
        config = {"tray_diameter": 20.0}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_tray_count_minimum(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with minimum tray count (1)."""
        config = {"tray_count": 1}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_tray_count_maximum(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with maximum tray count (5)."""
        config = {"tray_count": 5}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_tray_count_zero_fails(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray count of 0 fails validation."""
        config = {"tray_count": 0}
        result = lazy_susan_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("Tray count must be between 1 and 5" in e for e in result.errors)

    def test_validate_tray_count_exceeds_maximum_fails(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray count > 5 fails validation."""
        config = {"tray_count": 6}
        result = lazy_susan_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("Tray count must be between 1 and 5" in e for e in result.errors)

    def test_validate_tray_diameter_exceeds_maximum_fails(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray diameter exceeding max fails validation."""
        # Max for 24" depth = (24 * 2) - 2 = 46"
        config = {"tray_diameter": 47.0}
        result = lazy_susan_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("exceeds maximum" in e for e in result.errors)

    def test_validate_tray_diameter_at_maximum_passes(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray diameter at max passes validation."""
        # Max for 24" depth = (24 * 2) - 2 = 46"
        config = {"tray_diameter": 46.0}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_small_tray_diameter_warning(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test that small tray diameter generates warning."""
        # Create a context with small depth that results in < 16" tray
        context = ComponentContext(
            width=12.0,
            height=34.5,
            depth=9.0,  # (9 * 2) - 4 = 14" auto-calc diameter
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=12.0,
            cabinet_height=34.5,
            cabinet_depth=9.0,
        )
        config: dict = {}  # Will auto-calculate to 14"
        result = lazy_susan_component.validate(config, context)

        assert result.is_valid  # Warnings don't fail validation
        assert len(result.warnings) > 0
        assert any("less than recommended minimum" in w for w in result.warnings)

    def test_validate_door_style_single(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with single door style."""
        config = {"door_style": "single"}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_door_style_bifold(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with bifold door style."""
        config = {"door_style": "bifold"}
        result = lazy_susan_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_invalid_door_style_fails(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that invalid door style fails validation."""
        config = {"door_style": "sliding"}
        result = lazy_susan_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("Door style must be" in e for e in result.errors)

    def test_validate_negative_door_clearance_fails(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that negative door clearance fails validation."""
        config = {"door_clearance": -1.0}
        result = lazy_susan_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("non-negative" in e for e in result.errors)


class TestLazySusanPanelGeneration:
    """Tests for LazySusanCornerComponent panel generation."""

    def test_generate_creates_panels(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates panel entities."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        assert len(result.panels) > 0

    def test_generate_creates_left_side_panel(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that LEFT_SIDE panel is generated."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        left_sides = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE]
        assert len(left_sides) == 1

    def test_generate_creates_right_side_panel(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that RIGHT_SIDE panel is generated."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        right_sides = [p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE]
        assert len(right_sides) == 1

    def test_generate_creates_top_panel(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that TOP panel is generated."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        tops = [p for p in result.panels if p.panel_type == PanelType.TOP]
        assert len(tops) == 1

    def test_generate_creates_bottom_panel(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that BOTTOM panel is generated."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        bottoms = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottoms) == 1

    def test_generate_creates_back_panels(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that BACK panels are generated (L-shaped = 2 panels)."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        # Should have 2 back panels forming L-shape (or 1 if width == depth)
        assert len(backs) >= 1

    def test_generate_panel_count(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test total panel count for square cabinet (width == depth)."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        # When width == depth: LEFT_SIDE + RIGHT_SIDE + TOP + BOTTOM + 1 BACK = 5 panels
        # (Second back panel has width = 0 when width == depth, so not generated)
        assert len(result.panels) == 5

    def test_generate_side_panel_dimensions(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test side panel dimensions are correct."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        left_side = next(p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE)
        thickness = standard_context.material.thickness
        expected_depth = standard_context.depth - thickness  # Interior depth
        expected_height = standard_context.height - (2 * thickness)  # Interior height

        assert left_side.width == pytest.approx(expected_depth)
        assert left_side.height == pytest.approx(expected_height)

    def test_generate_includes_metadata(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes tray and footprint info."""
        config = {"tray_count": 3}
        result = lazy_susan_component.generate(config, standard_context)

        assert "tray_diameter" in result.metadata
        assert "tray_count" in result.metadata
        assert result.metadata["tray_count"] == 3
        assert "door_style" in result.metadata
        assert "footprint" in result.metadata

    def test_generate_footprint_metadata(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test footprint metadata values."""
        config = {"door_clearance": 2.0}
        result = lazy_susan_component.generate(config, standard_context)

        footprint = result.metadata["footprint"]
        # For 24" depth with 2" clearance: 26" on each wall
        assert footprint["left_wall"] == 26.0
        assert footprint["right_wall"] == 26.0
        assert footprint["total"] == 52.0


class TestLazySusanHardwareGeneration:
    """Tests for LazySusanCornerComponent hardware generation."""

    def test_hardware_includes_center_pole(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes center pole."""
        config: dict = {}
        hardware = lazy_susan_component.hardware(config, standard_context)

        poles = [h for h in hardware if "Center Pole" in h.name]
        assert len(poles) == 1
        assert poles[0].quantity == 1

    def test_hardware_includes_trays(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes correct number of trays."""
        config = {"tray_count": 3}
        hardware = lazy_susan_component.hardware(config, standard_context)

        trays = [h for h in hardware if "Tray" in h.name]
        assert len(trays) == 1
        assert trays[0].quantity == 3

    def test_hardware_includes_bearings(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes bearings matching tray count."""
        config = {"tray_count": 4}
        hardware = lazy_susan_component.hardware(config, standard_context)

        bearings = [h for h in hardware if "Bearing" in h.name]
        assert len(bearings) == 1
        assert bearings[0].quantity == 4

    def test_hardware_bifold_hinges(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that bifold door style includes 4 hinges."""
        config = {"door_style": "bifold"}
        hardware = lazy_susan_component.hardware(config, standard_context)

        hinges = [h for h in hardware if "Bi-Fold Hinge" in h.name]
        assert len(hinges) == 1
        assert hinges[0].quantity == 4

    def test_hardware_bifold_includes_catch(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that bifold door style includes door catch."""
        config = {"door_style": "bifold"}
        hardware = lazy_susan_component.hardware(config, standard_context)

        catches = [h for h in hardware if "Catch" in h.name]
        assert len(catches) == 1

    def test_hardware_single_door_hinges_short_cabinet(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test single door hinge count for short cabinet (< 40\")."""
        context = ComponentContext(
            width=24.0,
            height=30.0,  # Short cabinet
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=30.0,
            cabinet_depth=24.0,
        )
        config = {"door_style": "single"}
        hardware = lazy_susan_component.hardware(config, context)

        hinges = [h for h in hardware if "European Hinge" in h.name]
        assert len(hinges) == 1
        assert hinges[0].quantity == 2

    def test_hardware_single_door_hinges_medium_cabinet(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test single door hinge count for medium cabinet (40-60\")."""
        context = ComponentContext(
            width=24.0,
            height=50.0,  # Medium cabinet
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=50.0,
            cabinet_depth=24.0,
        )
        config = {"door_style": "single"}
        hardware = lazy_susan_component.hardware(config, context)

        hinges = [h for h in hardware if "European Hinge" in h.name]
        assert len(hinges) == 1
        assert hinges[0].quantity == 3

    def test_hardware_single_door_hinges_tall_cabinet(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test single door hinge count for tall cabinet (> 60\")."""
        context = ComponentContext(
            width=24.0,
            height=84.0,  # Tall cabinet
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )
        config = {"door_style": "single"}
        hardware = lazy_susan_component.hardware(config, context)

        hinges = [h for h in hardware if "European Hinge" in h.name]
        assert len(hinges) == 1
        assert hinges[0].quantity == 4

    def test_hardware_handle_count_single(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test handle count for single door."""
        config = {"door_style": "single"}
        hardware = lazy_susan_component.hardware(config, standard_context)

        handles = [h for h in hardware if "Handle" in h.name]
        assert len(handles) == 1
        assert handles[0].quantity == 1

    def test_hardware_handle_count_bifold(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test handle count for bifold doors."""
        config = {"door_style": "bifold"}
        hardware = lazy_susan_component.hardware(config, standard_context)

        handles = [h for h in hardware if "Handle" in h.name]
        assert len(handles) == 1
        assert handles[0].quantity == 2

    def test_hardware_tray_sku_includes_diameter(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray SKU includes diameter."""
        config = {"tray_diameter": 18.0}
        hardware = lazy_susan_component.hardware(config, standard_context)

        trays = [h for h in hardware if "Tray" in h.name]
        assert trays[0].sku == "LS-TRAY-18"


class TestLazySusanAutoCalculations:
    """Tests for LazySusanCornerComponent auto-calculations."""

    def test_auto_calculate_tray_diameter(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test auto-calculation of tray diameter when not specified."""
        config: dict = {}
        result = lazy_susan_component.generate(config, standard_context)

        # For 24" depth: (24 * 2) - 4 = 44"
        assert result.metadata["tray_diameter"] == 44.0

    def test_auto_calculate_tray_diameter_small_depth(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test auto-calculation for small depth cabinet."""
        context = ComponentContext(
            width=12.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=12.0,
            cabinet_height=30.0,
            cabinet_depth=12.0,
        )
        config: dict = {}
        result = lazy_susan_component.generate(config, context)

        # For 12" depth: (12 * 2) - 4 = 20"
        assert result.metadata["tray_diameter"] == 20.0

    def test_explicit_diameter_overrides_auto(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that explicit tray_diameter overrides auto-calculation."""
        config = {"tray_diameter": 30.0}
        result = lazy_susan_component.generate(config, standard_context)

        assert result.metadata["tray_diameter"] == 30.0


class TestLazySusanEdgeCases:
    """Edge case tests for LazySusanCornerComponent."""

    def test_square_cabinet_single_back_panel(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test that when width equals depth, back panels still work correctly."""
        context = ComponentContext(
            width=24.0,
            height=34.5,
            depth=24.0,  # Same as width
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=34.5,
            cabinet_depth=24.0,
        )
        config: dict = {}
        result = lazy_susan_component.generate(config, context)

        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        # With width == depth, second back panel width = width - depth = 0
        # So we should have only 1 back panel
        assert len(backs) == 1

    def test_wide_cabinet_two_back_panels(
        self, lazy_susan_component: LazySusanCornerComponent
    ) -> None:
        """Test that when width > depth, we get two back panels."""
        context = ComponentContext(
            width=36.0,  # Wider than depth
            height=34.5,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=36.0,
            cabinet_height=34.5,
            cabinet_depth=24.0,
        )
        config: dict = {}
        result = lazy_susan_component.generate(config, context)

        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(backs) == 2

    def test_minimum_tray_count(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test with minimum tray count."""
        config = {"tray_count": 1}
        result = lazy_susan_component.generate(config, standard_context)

        trays = [h for h in result.hardware if "Tray" in h.name]
        bearings = [h for h in result.hardware if "Bearing" in h.name]
        assert trays[0].quantity == 1
        assert bearings[0].quantity == 1

    def test_maximum_tray_count(
        self, lazy_susan_component: LazySusanCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test with maximum tray count."""
        config = {"tray_count": 5}
        result = lazy_susan_component.generate(config, standard_context)

        trays = [h for h in result.hardware if "Tray" in h.name]
        bearings = [h for h in result.hardware if "Bearing" in h.name]
        assert trays[0].quantity == 5
        assert bearings[0].quantity == 5


# =============================================================================
# Phase 3: BlindCornerComponent Tests
# =============================================================================

from cabinets.domain.components import BlindCornerComponent
from cabinets.domain.components.corner import BlindCornerComponent as BlindCornerDirect


@pytest.fixture
def blind_corner_component() -> BlindCornerComponent:
    """Create a BlindCornerComponent instance."""
    return BlindCornerComponent()


class TestBlindCornerComponentRegistration:
    """Tests for BlindCornerComponent registration."""

    def test_component_registered_with_correct_id(self) -> None:
        """Test that component is registered under 'corner.blind'."""
        component_cls = component_registry.get("corner.blind")
        assert component_cls is BlindCornerComponent

    def test_component_in_registry_list(self) -> None:
        """Test that component ID appears in registry list."""
        registered = component_registry.list()
        assert "corner.blind" in registered

    def test_component_can_be_imported_from_package(self) -> None:
        """Test that component can be imported from components package."""
        from cabinets.domain.components import BlindCornerComponent as BC

        assert BC is BlindCornerComponent

    def test_direct_import_from_corner_module(self) -> None:
        """Test that component can be imported directly from corner module."""
        assert BlindCornerDirect is BlindCornerComponent


class TestBlindCornerValidation:
    """Tests for BlindCornerComponent validation."""

    def test_validate_default_config(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with default configuration."""
        config: dict = {}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_blind_side_left(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with blind_side='left'."""
        config = {"blind_side": "left"}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_blind_side_right(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with blind_side='right'."""
        config = {"blind_side": "right"}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_invalid_blind_side_fails(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that invalid blind_side fails validation."""
        config = {"blind_side": "center"}
        result = blind_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("blind_side must be 'left' or 'right'" in e for e in result.errors)

    def test_validate_accessible_width_minimum(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with minimum accessible_width (12\")."""
        config = {"accessible_width": 12.0}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_accessible_width_below_minimum_fails(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that accessible_width below 12\" fails validation."""
        config = {"accessible_width": 10.0}
        result = blind_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("accessible_width must be at least 12" in e for e in result.errors)

    def test_validate_accessible_width_above_maximum_warning(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that accessible_width above 36\" generates warning."""
        config = {"accessible_width": 40.0}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid  # Warnings don't fail validation
        assert len(result.warnings) > 0
        assert any("exceeds recommended maximum" in w for w in result.warnings)

    def test_validate_accessible_width_at_maximum_no_warning(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that accessible_width at 36\" does not generate warning."""
        config = {"accessible_width": 36.0}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 0

    def test_validate_filler_width_zero(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with zero filler_width."""
        config = {"filler_width": 0.0}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_negative_filler_width_fails(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that negative filler_width fails validation."""
        config = {"filler_width": -1.0}
        result = blind_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("filler_width must be non-negative" in e for e in result.errors)

    def test_validate_pull_out_true(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with pull_out=True."""
        config = {"pull_out": True}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_pull_out_false(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with pull_out=False."""
        config = {"pull_out": False}
        result = blind_corner_component.validate(config, standard_context)

        assert result.is_valid


class TestBlindCornerPanelGeneration:
    """Tests for BlindCornerComponent panel generation."""

    def test_generate_creates_panels(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates panel entities."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        assert len(result.panels) > 0

    def test_generate_creates_left_side_panel(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that LEFT_SIDE panel is generated."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        left_sides = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE]
        assert len(left_sides) == 1

    def test_generate_creates_right_side_panel(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that RIGHT_SIDE panel is generated."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        right_sides = [p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE]
        assert len(right_sides) == 1

    def test_generate_creates_top_panel(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that TOP panel is generated."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        tops = [p for p in result.panels if p.panel_type == PanelType.TOP]
        assert len(tops) == 1

    def test_generate_creates_bottom_panel(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that BOTTOM panel is generated."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        bottoms = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottoms) == 1

    def test_generate_creates_back_panel(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that BACK panel is generated."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(backs) == 1

    def test_generate_creates_filler_panel(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that FILLER panel is generated."""
        config = {"filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        fillers = [p for p in result.panels if p.panel_type == PanelType.FILLER]
        assert len(fillers) == 1
        assert fillers[0].width == 3.0

    def test_generate_no_filler_when_zero_width(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that no FILLER panel is generated when filler_width is 0."""
        config = {"filler_width": 0.0}
        result = blind_corner_component.generate(config, standard_context)

        fillers = [p for p in result.panels if p.panel_type == PanelType.FILLER]
        assert len(fillers) == 0

    def test_generate_panel_count_with_filler(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test total panel count with filler."""
        config = {"filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        # LEFT_SIDE + RIGHT_SIDE + TOP + BOTTOM + BACK + FILLER = 6 panels
        assert len(result.panels) == 6

    def test_generate_panel_count_without_filler(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test total panel count without filler."""
        config = {"filler_width": 0.0}
        result = blind_corner_component.generate(config, standard_context)

        # LEFT_SIDE + RIGHT_SIDE + TOP + BOTTOM + BACK = 5 panels
        assert len(result.panels) == 5

    def test_generate_top_bottom_width_includes_filler(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that TOP and BOTTOM panels have correct width (accessible + filler)."""
        config = {"accessible_width": 24.0, "filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        top = next(p for p in result.panels if p.panel_type == PanelType.TOP)
        bottom = next(p for p in result.panels if p.panel_type == PanelType.BOTTOM)

        expected_width = 24.0 + 3.0  # accessible_width + filler_width
        assert top.width == expected_width
        assert bottom.width == expected_width

    def test_generate_side_panel_dimensions(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test side panel dimensions are correct."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        left_side = next(p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE)
        thickness = standard_context.material.thickness
        expected_depth = standard_context.depth - thickness  # Interior depth
        expected_height = standard_context.height - (2 * thickness)  # Interior height

        assert left_side.width == pytest.approx(expected_depth)
        assert left_side.height == pytest.approx(expected_height)

    def test_generate_back_panel_uses_quarter_inch_material(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that back panel uses 1/4\" material."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        back = next(p for p in result.panels if p.panel_type == PanelType.BACK)
        assert back.material.thickness == 0.25

    def test_generate_includes_metadata(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes configuration info."""
        config = {"blind_side": "right", "accessible_width": 30.0}
        result = blind_corner_component.generate(config, standard_context)

        assert "blind_side" in result.metadata
        assert result.metadata["blind_side"] == "right"
        assert "accessible_width" in result.metadata
        assert result.metadata["accessible_width"] == 30.0
        assert "pull_out" in result.metadata
        assert "filler_width" in result.metadata
        assert "cabinet_width" in result.metadata
        assert "footprint" in result.metadata

    def test_generate_footprint_metadata_left(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test footprint metadata values for blind_side='left'."""
        config = {"blind_side": "left", "accessible_width": 24.0, "filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        footprint = result.metadata["footprint"]
        # For blind_side="left": left_wall = depth, right_wall = accessible + filler
        assert footprint["left_wall"] == standard_context.depth
        assert footprint["right_wall"] == 27.0  # 24 + 3
        assert footprint["total"] == standard_context.depth + 27.0

    def test_generate_footprint_metadata_right(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test footprint metadata values for blind_side='right'."""
        config = {"blind_side": "right", "accessible_width": 24.0, "filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        footprint = result.metadata["footprint"]
        # For blind_side="right": left_wall = accessible + filler, right_wall = depth
        assert footprint["left_wall"] == 27.0  # 24 + 3
        assert footprint["right_wall"] == standard_context.depth
        assert footprint["total"] == 27.0 + standard_context.depth

    def test_generate_filler_position_left_side(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test filler panel position when blind_side='left'."""
        config = {"blind_side": "left", "filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        filler = next(p for p in result.panels if p.panel_type == PanelType.FILLER)
        # Filler should be at the left side (x = position.x)
        assert filler.position.x == standard_context.position.x

    def test_generate_filler_position_right_side(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test filler panel position when blind_side='right'."""
        config = {"blind_side": "right", "accessible_width": 24.0, "filler_width": 3.0}
        result = blind_corner_component.generate(config, standard_context)

        filler = next(p for p in result.panels if p.panel_type == PanelType.FILLER)
        cabinet_width = 24.0 + 3.0
        expected_x = standard_context.position.x + cabinet_width - 3.0
        assert filler.position.x == expected_x


class TestBlindCornerHardwareGeneration:
    """Tests for BlindCornerComponent hardware generation."""

    def test_hardware_includes_pullout_slides_when_enabled(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes pull-out slides when pull_out=True."""
        config = {"pull_out": True}
        hardware = blind_corner_component.hardware(config, standard_context)

        slides = [h for h in hardware if "Pull-out Slides" in h.name]
        assert len(slides) == 1
        assert slides[0].quantity == 1

    def test_hardware_includes_pullout_tray_when_enabled(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes pull-out tray when pull_out=True."""
        config = {"pull_out": True}
        hardware = blind_corner_component.hardware(config, standard_context)

        trays = [h for h in hardware if "Pull-out Tray" in h.name]
        assert len(trays) == 1
        assert trays[0].quantity == 1

    def test_hardware_empty_when_pullout_disabled(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that no hardware is returned when pull_out=False."""
        config = {"pull_out": False}
        hardware = blind_corner_component.hardware(config, standard_context)

        assert len(hardware) == 0

    def test_hardware_tray_sku_includes_width(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray SKU includes accessible width."""
        config = {"pull_out": True, "accessible_width": 30.0}
        hardware = blind_corner_component.hardware(config, standard_context)

        trays = [h for h in hardware if "Pull-out Tray" in h.name]
        assert trays[0].sku == "BC-TRAY-30"

    def test_hardware_tray_notes_include_blind_side(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray notes include blind side."""
        config = {"pull_out": True, "blind_side": "right"}
        hardware = blind_corner_component.hardware(config, standard_context)

        trays = [h for h in hardware if "Pull-out Tray" in h.name]
        assert "right" in trays[0].notes

    def test_hardware_slides_notes_include_width(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that slides notes include accessible width."""
        config = {"pull_out": True, "accessible_width": 24.0}
        hardware = blind_corner_component.hardware(config, standard_context)

        slides = [h for h in hardware if "Pull-out Slides" in h.name]
        assert "24" in slides[0].notes


class TestBlindCornerEdgeCases:
    """Edge case tests for BlindCornerComponent."""

    def test_minimum_accessible_width(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test with minimum accessible width (12\")."""
        config = {"accessible_width": 12.0}
        result = blind_corner_component.generate(config, standard_context)

        assert result.metadata["accessible_width"] == 12.0
        assert result.metadata["cabinet_width"] == 15.0  # 12 + 3 default filler

    def test_maximum_practical_accessible_width(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test with maximum practical accessible width (36\")."""
        config = {"accessible_width": 36.0}
        result = blind_corner_component.generate(config, standard_context)

        assert result.metadata["accessible_width"] == 36.0
        assert result.metadata["cabinet_width"] == 39.0  # 36 + 3 default filler

    def test_large_filler_width(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test with large filler width."""
        config = {"accessible_width": 24.0, "filler_width": 6.0}
        result = blind_corner_component.generate(config, standard_context)

        filler = next(p for p in result.panels if p.panel_type == PanelType.FILLER)
        assert filler.width == 6.0
        assert result.metadata["cabinet_width"] == 30.0

    def test_both_blind_sides_produce_correct_footprints(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that left and right blind sides produce mirror footprints."""
        config_left = {"blind_side": "left", "accessible_width": 24.0, "filler_width": 3.0}
        config_right = {"blind_side": "right", "accessible_width": 24.0, "filler_width": 3.0}

        result_left = blind_corner_component.generate(config_left, standard_context)
        result_right = blind_corner_component.generate(config_right, standard_context)

        fp_left = result_left.metadata["footprint"]
        fp_right = result_right.metadata["footprint"]

        # They should be mirrors of each other
        assert fp_left["left_wall"] == fp_right["right_wall"]
        assert fp_left["right_wall"] == fp_right["left_wall"]
        assert fp_left["total"] == fp_right["total"]

    def test_hardware_in_generate_result(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes hardware in result."""
        config = {"pull_out": True}
        result = blind_corner_component.generate(config, standard_context)

        assert len(result.hardware) == 2  # Slides + Tray

    def test_no_hardware_in_generate_when_disabled(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate has no hardware when pull_out=False."""
        config = {"pull_out": False}
        result = blind_corner_component.generate(config, standard_context)

        assert len(result.hardware) == 0

    def test_defaults_are_applied(
        self, blind_corner_component: BlindCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that all defaults are correctly applied."""
        config: dict = {}
        result = blind_corner_component.generate(config, standard_context)

        assert result.metadata["blind_side"] == "left"
        assert result.metadata["accessible_width"] == 24.0
        assert result.metadata["pull_out"] is True
        assert result.metadata["filler_width"] == 3.0
        assert result.metadata["cabinet_width"] == 27.0  # 24 + 3


# =============================================================================
# Phase 4: DiagonalCornerComponent Tests
# =============================================================================

from cabinets.domain.components import DiagonalCornerComponent
from cabinets.domain.components.corner import DiagonalCornerComponent as DiagonalCornerDirect


@pytest.fixture
def diagonal_corner_component() -> DiagonalCornerComponent:
    """Create a DiagonalCornerComponent instance."""
    return DiagonalCornerComponent()


class TestDiagonalCornerComponentRegistration:
    """Tests for DiagonalCornerComponent registration."""

    def test_component_registered_with_correct_id(self) -> None:
        """Test that component is registered under 'corner.diagonal'."""
        component_cls = component_registry.get("corner.diagonal")
        assert component_cls is DiagonalCornerComponent

    def test_component_in_registry_list(self) -> None:
        """Test that component ID appears in registry list."""
        registered = component_registry.list()
        assert "corner.diagonal" in registered

    def test_component_can_be_imported_from_package(self) -> None:
        """Test that component can be imported from components package."""
        from cabinets.domain.components import DiagonalCornerComponent as DC

        assert DC is DiagonalCornerComponent

    def test_direct_import_from_corner_module(self) -> None:
        """Test that component can be imported directly from corner module."""
        assert DiagonalCornerDirect is DiagonalCornerComponent


class TestDiagonalCornerValidation:
    """Tests for DiagonalCornerComponent validation."""

    def test_validate_default_config(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with default configuration."""
        config: dict = {}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_explicit_face_width(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with explicit face_width."""
        config = {"face_width": 24.0}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_face_width_minimum(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with minimum face_width (18\")."""
        config = {"face_width": 18.0}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_face_width_below_minimum_fails(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that face_width below 18\" fails validation."""
        config = {"face_width": 16.0}
        result = diagonal_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("face_width must be at least 18" in e for e in result.errors)

    def test_validate_shelf_count_zero(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with shelf_count=0."""
        config = {"shelf_count": 0}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_shelf_count_maximum(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with maximum shelf_count (6)."""
        config = {"shelf_count": 6}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_shelf_count_exceeds_maximum_fails(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf_count > 6 fails validation."""
        config = {"shelf_count": 7}
        result = diagonal_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("shelf_count must be between 0 and 6" in e for e in result.errors)

    def test_validate_shelf_count_negative_fails(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf_count < 0 fails validation."""
        config = {"shelf_count": -1}
        result = diagonal_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("shelf_count must be between 0 and 6" in e for e in result.errors)

    def test_validate_shelf_shape_triangular(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with shelf_shape='triangular'."""
        config = {"shelf_shape": "triangular"}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_shelf_shape_squared(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with shelf_shape='squared'."""
        config = {"shelf_shape": "squared"}
        result = diagonal_corner_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_invalid_shelf_shape_fails(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that invalid shelf_shape fails validation."""
        config = {"shelf_shape": "circular"}
        result = diagonal_corner_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("shelf_shape must be 'triangular' or 'squared'" in e for e in result.errors)

    def test_validate_auto_calculated_face_width_below_minimum(
        self, diagonal_corner_component: DiagonalCornerComponent
    ) -> None:
        """Test that auto-calculated face_width below 18\" fails validation."""
        # Create a context with small depth that results in < 18" face width
        # depth * sqrt(2) < 18 when depth < 18/sqrt(2) = 12.73
        context = ComponentContext(
            width=12.0,
            height=34.5,
            depth=10.0,  # 10 * sqrt(2) = 14.14" < 18"
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=12.0,
            cabinet_height=34.5,
            cabinet_depth=10.0,
        )
        config: dict = {}
        result = diagonal_corner_component.validate(config, context)

        assert not result.is_valid
        assert any("face_width must be at least 18" in e for e in result.errors)


class TestDiagonalCornerPanelGeneration:
    """Tests for DiagonalCornerComponent panel generation."""

    def test_generate_creates_panels(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates panel entities."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        assert len(result.panels) > 0

    def test_generate_creates_left_side_panel(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that LEFT_SIDE panel is generated."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        left_sides = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE]
        assert len(left_sides) == 1

    def test_generate_creates_right_side_panel(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that RIGHT_SIDE panel is generated."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        right_sides = [p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE]
        assert len(right_sides) == 1

    def test_generate_creates_diagonal_face_panel(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that DIAGONAL_FACE panel is generated."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        diagonal_faces = [p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE]
        assert len(diagonal_faces) == 1

    def test_generate_creates_top_panel(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that TOP panel is generated."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        tops = [p for p in result.panels if p.panel_type == PanelType.TOP]
        assert len(tops) == 1

    def test_generate_creates_bottom_panel(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that BOTTOM panel is generated."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        bottoms = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottoms) == 1

    def test_generate_panel_count_with_default_shelves(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test total panel count with default shelf_count (2)."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        # LEFT_SIDE + RIGHT_SIDE + DIAGONAL_FACE + TOP + BOTTOM + 2 SHELF = 7 panels
        assert len(result.panels) == 7

    def test_generate_panel_count_no_shelves(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test total panel count with shelf_count=0."""
        config = {"shelf_count": 0}
        result = diagonal_corner_component.generate(config, standard_context)

        # LEFT_SIDE + RIGHT_SIDE + DIAGONAL_FACE + TOP + BOTTOM = 5 panels
        assert len(result.panels) == 5

    def test_generate_panel_count_with_many_shelves(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test total panel count with shelf_count=5."""
        config = {"shelf_count": 5}
        result = diagonal_corner_component.generate(config, standard_context)

        # LEFT_SIDE + RIGHT_SIDE + DIAGONAL_FACE + TOP + BOTTOM + 5 SHELF = 10 panels
        assert len(result.panels) == 10

    def test_generate_side_panels_have_angle_metadata(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side panels have angled cut metadata."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        left_side = next(p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE)
        right_side = next(p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE)

        assert left_side.metadata.get("is_angled") is True
        assert left_side.metadata.get("angle") == 45
        assert right_side.metadata.get("is_angled") is True
        assert right_side.metadata.get("angle") == 45

    def test_generate_diagonal_face_has_angle_metadata(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that diagonal face panel has angled metadata."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        diagonal_face = next(p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE)

        assert diagonal_face.metadata.get("is_angled") is True
        assert diagonal_face.metadata.get("angle") == 45

    def test_generate_diagonal_face_width_auto_calculated(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that diagonal face width is auto-calculated as depth * sqrt(2)."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        diagonal_face = next(p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE)

        # For 24" depth: 24 * sqrt(2) = 33.94"
        expected_width = standard_context.depth * math.sqrt(2)
        assert diagonal_face.width == pytest.approx(expected_width)

    def test_generate_diagonal_face_width_explicit(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that explicit face_width is used."""
        config = {"face_width": 30.0}
        result = diagonal_corner_component.generate(config, standard_context)

        diagonal_face = next(p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE)

        assert diagonal_face.width == 30.0

    def test_generate_triangular_shelf_dimensions(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test triangular shelf dimensions (depth x depth)."""
        config = {"shelf_shape": "triangular", "shelf_count": 1}
        result = diagonal_corner_component.generate(config, standard_context)

        shelves = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelves) == 1
        assert shelves[0].width == standard_context.depth
        assert shelves[0].height == standard_context.depth
        assert shelves[0].metadata.get("shelf_shape") == "triangular"

    def test_generate_squared_shelf_dimensions(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test squared shelf dimensions (depth * 0.8 x depth * 0.8)."""
        config = {"shelf_shape": "squared", "shelf_count": 1}
        result = diagonal_corner_component.generate(config, standard_context)

        shelves = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelves) == 1
        expected_dimension = standard_context.depth * 0.8
        assert shelves[0].width == pytest.approx(expected_dimension)
        assert shelves[0].height == pytest.approx(expected_dimension)
        assert shelves[0].metadata.get("shelf_shape") == "squared"

    def test_generate_shelves_have_index_metadata(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelves have shelf_index in metadata."""
        config = {"shelf_count": 3}
        result = diagonal_corner_component.generate(config, standard_context)

        shelves = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        indices = [s.metadata.get("shelf_index") for s in shelves]

        assert sorted(indices) == [0, 1, 2]

    def test_generate_includes_metadata(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes configuration info."""
        config = {"shelf_shape": "triangular", "shelf_count": 3}
        result = diagonal_corner_component.generate(config, standard_context)

        assert "face_width" in result.metadata
        assert "shelf_shape" in result.metadata
        assert result.metadata["shelf_shape"] == "triangular"
        assert "shelf_count" in result.metadata
        assert result.metadata["shelf_count"] == 3
        assert "footprint" in result.metadata

    def test_generate_footprint_metadata(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test footprint metadata values (symmetric, both = depth)."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        footprint = result.metadata["footprint"]
        # For diagonal: both walls equal depth
        assert footprint["left_wall"] == standard_context.depth
        assert footprint["right_wall"] == standard_context.depth
        assert footprint["total"] == standard_context.depth * 2


class TestDiagonalCornerHardwareGeneration:
    """Tests for DiagonalCornerComponent hardware generation."""

    def test_hardware_includes_shelf_pins_with_shelves(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes shelf pins when shelf_count > 0."""
        config = {"shelf_count": 2}
        hardware = diagonal_corner_component.hardware(config, standard_context)

        pins = [h for h in hardware if "Shelf Pin" in h.name]
        assert len(pins) == 1
        assert pins[0].quantity == 8  # 2 shelves * 4 pins

    def test_hardware_shelf_pin_count_scales_with_shelves(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf pin count is shelf_count * 4."""
        config = {"shelf_count": 5}
        hardware = diagonal_corner_component.hardware(config, standard_context)

        pins = [h for h in hardware if "Shelf Pin" in h.name]
        assert len(pins) == 1
        assert pins[0].quantity == 20  # 5 shelves * 4 pins

    def test_hardware_no_pins_when_no_shelves(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that no shelf pins are returned when shelf_count=0."""
        config = {"shelf_count": 0}
        hardware = diagonal_corner_component.hardware(config, standard_context)

        assert len(hardware) == 0

    def test_hardware_shelf_pin_sku(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf pins have correct SKU."""
        config = {"shelf_count": 1}
        hardware = diagonal_corner_component.hardware(config, standard_context)

        pins = [h for h in hardware if "Shelf Pin" in h.name]
        assert pins[0].sku == "SP-5MM"

    def test_hardware_in_generate_result(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes hardware in result."""
        config = {"shelf_count": 3}
        result = diagonal_corner_component.generate(config, standard_context)

        assert len(result.hardware) == 1
        assert result.hardware[0].quantity == 12  # 3 * 4


class TestDiagonalCornerAutoCalculations:
    """Tests for DiagonalCornerComponent auto-calculations."""

    def test_auto_calculate_face_width(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test auto-calculation of face_width when not specified."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        # For 24" depth: 24 * sqrt(2) = 33.94"
        expected = standard_context.depth * math.sqrt(2)
        assert result.metadata["face_width"] == pytest.approx(expected)

    def test_auto_calculate_face_width_different_depth(
        self, diagonal_corner_component: DiagonalCornerComponent
    ) -> None:
        """Test auto-calculation for different depth cabinet."""
        context = ComponentContext(
            width=18.0,
            height=30.0,
            depth=18.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=18.0,
            cabinet_height=30.0,
            cabinet_depth=18.0,
        )
        config: dict = {}
        result = diagonal_corner_component.generate(config, context)

        # For 18" depth: 18 * sqrt(2) = 25.46"
        expected = 18.0 * math.sqrt(2)
        assert result.metadata["face_width"] == pytest.approx(expected)

    def test_explicit_face_width_overrides_auto(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that explicit face_width overrides auto-calculation."""
        config = {"face_width": 28.0}
        result = diagonal_corner_component.generate(config, standard_context)

        assert result.metadata["face_width"] == 28.0


class TestDiagonalCornerEdgeCases:
    """Edge case tests for DiagonalCornerComponent."""

    def test_defaults_are_applied(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that all defaults are correctly applied."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        assert result.metadata["shelf_shape"] == "squared"
        assert result.metadata["shelf_count"] == 2
        # Face width should be auto-calculated
        assert result.metadata["face_width"] == pytest.approx(
            standard_context.depth * math.sqrt(2)
        )

    def test_minimum_face_width_at_boundary(
        self, diagonal_corner_component: DiagonalCornerComponent
    ) -> None:
        """Test with face_width exactly at minimum (18\")."""
        context = ComponentContext(
            width=18.0,
            height=30.0,
            depth=18.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=18.0,
            cabinet_height=30.0,
            cabinet_depth=18.0,
        )
        config = {"face_width": 18.0}
        result = diagonal_corner_component.validate(config, context)

        assert result.is_valid

    def test_all_shelf_counts_in_range(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that all shelf counts 0-6 are valid."""
        for count in range(7):
            config = {"shelf_count": count}
            result = diagonal_corner_component.validate(config, standard_context)
            assert result.is_valid, f"shelf_count={count} should be valid"

    def test_footprint_is_symmetric(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that diagonal corner footprint is always symmetric."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        footprint = result.metadata["footprint"]
        assert footprint["left_wall"] == footprint["right_wall"]

    def test_side_panel_dimensions(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test side panel dimensions are correct."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        left_side = next(p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE)
        thickness = standard_context.material.thickness
        expected_depth = standard_context.depth - thickness  # Interior depth
        expected_height = standard_context.height - (2 * thickness)  # Interior height

        assert left_side.width == pytest.approx(expected_depth)
        assert left_side.height == pytest.approx(expected_height)

    def test_top_bottom_panels_are_square(
        self, diagonal_corner_component: DiagonalCornerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that top and bottom panels are square (depth x depth)."""
        config: dict = {}
        result = diagonal_corner_component.generate(config, standard_context)

        top = next(p for p in result.panels if p.panel_type == PanelType.TOP)
        bottom = next(p for p in result.panels if p.panel_type == PanelType.BOTTOM)

        assert top.width == standard_context.depth
        assert top.height == standard_context.depth
        assert bottom.width == standard_context.depth
        assert bottom.height == standard_context.depth
