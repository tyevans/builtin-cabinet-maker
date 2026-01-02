"""Tests for ArchService and ArchComponent implementation.

Tests for arch geometry calculations, ArchComponent validation, generation,
and hardware methods following the Component protocol for FRD-12 decorative
elements (FR-01 Arch Tops).
"""

from __future__ import annotations

import math

import pytest

from cabinets.domain.components import (
    ArchComponent,
    ArchConfig,
    ArchCutMetadata,
    ArchService,
    ArchType,
    ComponentContext,
    GenerationResult,
    ValidationResult,
    component_registry,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def arch_service() -> ArchService:
    """Create an ArchService instance for testing."""
    return ArchService()


@pytest.fixture
def arch_component() -> ArchComponent:
    """Create an ArchComponent instance for testing."""
    return ArchComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 24" wide x 36" high section.
    """
    return ComponentContext(
        width=24.0,
        height=36.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=24.0,
        cabinet_height=36.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def wide_context() -> ComponentContext:
    """Create a wide ComponentContext for testing.

    Returns a context representing a 36" wide x 84" high section.
    """
    return ComponentContext(
        width=36.0,
        height=84.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=36.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


# =============================================================================
# ArchConfig Tests
# =============================================================================


class TestArchConfig:
    """Tests for ArchConfig dataclass."""

    def test_arch_config_with_auto_radius(self) -> None:
        """Test creating ArchConfig with auto radius."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")
        assert config.arch_type == ArchType.FULL_ROUND
        assert config.radius == "auto"
        assert config.spring_height == 0.0

    def test_arch_config_with_explicit_radius(self) -> None:
        """Test creating ArchConfig with explicit radius."""
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)
        assert config.arch_type == ArchType.SEGMENTAL
        assert config.radius == 18.0

    def test_arch_config_with_spring_height(self) -> None:
        """Test creating ArchConfig with spring height."""
        config = ArchConfig(
            arch_type=ArchType.FULL_ROUND, radius="auto", spring_height=4.0
        )
        assert config.spring_height == 4.0

    def test_arch_config_calculate_radius_auto(self) -> None:
        """Test calculate_radius with auto returns opening_width / 2."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")
        assert config.calculate_radius(24.0) == pytest.approx(12.0)
        assert config.calculate_radius(36.0) == pytest.approx(18.0)

    def test_arch_config_calculate_radius_explicit(self) -> None:
        """Test calculate_radius with explicit value returns that value."""
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)
        assert config.calculate_radius(24.0) == pytest.approx(18.0)

    def test_arch_config_rejects_zero_radius(self) -> None:
        """Test that zero radius is rejected in __post_init__."""
        with pytest.raises(ValueError, match="radius must be positive"):
            ArchConfig(arch_type=ArchType.FULL_ROUND, radius=0)

    def test_arch_config_rejects_negative_radius(self) -> None:
        """Test that negative radius is rejected in __post_init__."""
        with pytest.raises(ValueError, match="radius must be positive"):
            ArchConfig(arch_type=ArchType.FULL_ROUND, radius=-5.0)

    def test_arch_config_rejects_negative_spring_height(self) -> None:
        """Test that negative spring height is rejected in __post_init__."""
        with pytest.raises(ValueError, match="spring_height must be non-negative"):
            ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto", spring_height=-1.0)


# =============================================================================
# ArchService Math Tests - Full Round
# =============================================================================


class TestArchServiceFullRound:
    """Tests for ArchService with full_round (semicircle) arches."""

    def test_header_height_full_round_auto_radius(
        self, arch_service: ArchService
    ) -> None:
        """Test header height for full round with auto radius."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        # 24" opening -> 12" radius -> 12" header
        height = arch_service.calculate_header_height(config, 24.0)
        assert height == pytest.approx(12.0)

        # 36" opening -> 18" radius -> 18" header
        height = arch_service.calculate_header_height(config, 36.0)
        assert height == pytest.approx(18.0)

    def test_header_height_full_round_with_spring_height(
        self, arch_service: ArchService
    ) -> None:
        """Test header height includes spring height."""
        config = ArchConfig(
            arch_type=ArchType.FULL_ROUND, radius="auto", spring_height=4.0
        )

        # 24" opening -> 12" radius + 4" spring = 16" header
        height = arch_service.calculate_header_height(config, 24.0)
        assert height == pytest.approx(16.0)

    def test_arc_rise_full_round(self, arch_service: ArchService) -> None:
        """Test arc rise for full round equals radius."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        # Arc rise (without spring height) should equal radius
        arc_rise = arch_service.calculate_arc_rise(config, 24.0)
        assert arc_rise == pytest.approx(12.0)

    def test_upright_extension_at_center_full_round(
        self, arch_service: ArchService
    ) -> None:
        """Test upright extension at center (x=0) equals radius."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        # At center, y = sqrt(r^2 - 0^2) = r
        extension = arch_service.calculate_upright_extension(config, 24.0, 0)
        assert extension == pytest.approx(12.0)

    def test_upright_extension_at_edge_full_round(
        self, arch_service: ArchService
    ) -> None:
        """Test upright extension at edge (x=r) equals 0 plus spring."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        # At edge (x = +/-12), should return spring_height (0)
        extension = arch_service.calculate_upright_extension(config, 24.0, 12.0)
        assert extension == pytest.approx(0.0)

        extension = arch_service.calculate_upright_extension(config, 24.0, -12.0)
        assert extension == pytest.approx(0.0)

    def test_upright_extension_outside_arch_full_round(
        self, arch_service: ArchService
    ) -> None:
        """Test upright extension outside arch returns spring height."""
        config = ArchConfig(
            arch_type=ArchType.FULL_ROUND, radius="auto", spring_height=2.0
        )

        # Outside the arch (x > r)
        extension = arch_service.calculate_upright_extension(config, 24.0, 15.0)
        assert extension == pytest.approx(2.0)

    def test_upright_extension_at_midpoint_full_round(
        self, arch_service: ArchService
    ) -> None:
        """Test upright extension at midpoint (x=r/sqrt(2))."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        # For semicircle with r=12, at x = r/sqrt(2) = 8.485...
        # y = sqrt(144 - 72) = sqrt(72) = 8.485...
        r = 12.0
        x = r / math.sqrt(2)
        expected_y = math.sqrt(r**2 - x**2)

        extension = arch_service.calculate_upright_extension(config, 24.0, x)
        assert extension == pytest.approx(expected_y)

    def test_curve_points_full_round_symmetry(self, arch_service: ArchService) -> None:
        """Test that curve points are symmetric for full round."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        points = arch_service.generate_curve_points(config, 24.0, num_points=5)

        assert len(points) == 5

        # First and last should be at edges with y=0
        assert points[0][0] == pytest.approx(-12.0)
        assert points[0][1] == pytest.approx(0.0)
        assert points[4][0] == pytest.approx(12.0)
        assert points[4][1] == pytest.approx(0.0)

        # Center should be at x=0, y=12
        assert points[2][0] == pytest.approx(0.0)
        assert points[2][1] == pytest.approx(12.0)

        # Points 1 and 3 should be symmetric
        assert points[1][1] == pytest.approx(points[3][1])
        assert points[1][0] == pytest.approx(-points[3][0])


# =============================================================================
# ArchService Math Tests - Segmental
# =============================================================================


class TestArchServiceSegmental:
    """Tests for ArchService with segmental arches."""

    def test_header_height_segmental_18_radius_24_opening(
        self, arch_service: ArchService
    ) -> None:
        """Test segmental arch with 18" radius, 24" opening.

        From task spec: segmental 24" opening, 18" radius -> ~2.68" header
        Arc rise = r - sqrt(r^2 - (w/2)^2) = 18 - sqrt(324 - 144) = 18 - sqrt(180)
                 = 18 - 13.416... = ~4.58" (different from spec?)

        Let me verify: r = 18, w/2 = 12
        arc_rise = 18 - sqrt(18^2 - 12^2) = 18 - sqrt(324 - 144) = 18 - sqrt(180)
                 = 18 - 13.4164... = 4.5836... (not 2.68)

        Actually for segmental with r=18, w=24:
        arc_rise = r - sqrt(r^2 - (w/2)^2) = 18 - sqrt(324 - 144) = 18 - 13.416 = 4.584
        """
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)

        height = arch_service.calculate_header_height(config, 24.0)
        expected = 18.0 - math.sqrt(18.0**2 - 12.0**2)  # ~4.584
        assert height == pytest.approx(expected, rel=1e-3)

    def test_header_height_segmental_24_radius_24_opening(
        self, arch_service: ArchService
    ) -> None:
        """Test segmental arch with 24" radius, 24" opening.

        From task spec: segmental 24" opening, 24" radius -> ~1.07" header
        Arc rise = r - sqrt(r^2 - (w/2)^2) = 24 - sqrt(576 - 144) = 24 - sqrt(432)
                 = 24 - 20.78... = ~3.22" (different from spec?)

        Let me verify: actually 24 - sqrt(24^2 - 12^2) = 24 - sqrt(576-144) = 24 - 20.78 = 3.22

        The spec table might be using different formulas. Let me just test the math.
        """
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=24.0)

        height = arch_service.calculate_header_height(config, 24.0)
        expected = 24.0 - math.sqrt(24.0**2 - 12.0**2)  # ~3.215
        assert height == pytest.approx(expected, rel=1e-3)

    def test_arc_rise_segmental(self, arch_service: ArchService) -> None:
        """Test arc rise calculation for segmental arch."""
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)

        arc_rise = arch_service.calculate_arc_rise(config, 24.0)
        expected = 18.0 - math.sqrt(18.0**2 - 12.0**2)
        assert arc_rise == pytest.approx(expected, rel=1e-3)

    def test_segmental_invalid_radius_too_small(
        self, arch_service: ArchService
    ) -> None:
        """Test segmental with radius < opening/2 returns spring height only."""
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=10.0)

        # 10" radius for 24" opening is invalid (need at least 12")
        height = arch_service.calculate_header_height(config, 24.0)
        assert height == pytest.approx(0.0)  # Just spring height

        arc_rise = arch_service.calculate_arc_rise(config, 24.0)
        assert arc_rise == pytest.approx(0.0)

    def test_upright_extension_segmental_at_center(
        self, arch_service: ArchService
    ) -> None:
        """Test upright extension at center for segmental arch."""
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)

        # At center (x=0), the extension should be the arc rise
        extension = arch_service.calculate_upright_extension(config, 24.0, 0)
        arc_rise = arch_service.calculate_arc_rise(config, 24.0)
        assert extension == pytest.approx(arc_rise)

    def test_upright_extension_segmental_at_edge(
        self, arch_service: ArchService
    ) -> None:
        """Test upright extension at edge for segmental arch."""
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)

        # At edge (x = opening/2), should be at spring line
        extension = arch_service.calculate_upright_extension(config, 24.0, 12.0)
        assert extension == pytest.approx(0.0)


# =============================================================================
# ArchService Math Tests - Elliptical
# =============================================================================


class TestArchServiceElliptical:
    """Tests for ArchService with elliptical arches."""

    def test_header_height_elliptical(self, arch_service: ArchService) -> None:
        """Test header height for elliptical arch.

        From task spec: elliptical 24" opening, 8" radius -> 8.0" header
        """
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        height = arch_service.calculate_header_height(config, 24.0)
        assert height == pytest.approx(8.0)

    def test_header_height_elliptical_with_spring(
        self, arch_service: ArchService
    ) -> None:
        """Test elliptical header height includes spring height."""
        config = ArchConfig(
            arch_type=ArchType.ELLIPTICAL, radius=8.0, spring_height=2.0
        )

        height = arch_service.calculate_header_height(config, 24.0)
        assert height == pytest.approx(10.0)

    def test_arc_rise_elliptical(self, arch_service: ArchService) -> None:
        """Test arc rise for elliptical equals radius (semi-minor axis)."""
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        arc_rise = arch_service.calculate_arc_rise(config, 24.0)
        assert arc_rise == pytest.approx(8.0)

    def test_upright_extension_elliptical_at_center(
        self, arch_service: ArchService
    ) -> None:
        """Test elliptical upright extension at center.

        At x=0: y = b * sqrt(1 - 0) = b = radius
        """
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        extension = arch_service.calculate_upright_extension(config, 24.0, 0)
        assert extension == pytest.approx(8.0)

    def test_upright_extension_elliptical_at_edge(
        self, arch_service: ArchService
    ) -> None:
        """Test elliptical upright extension at edge.

        At x = a (semi-major axis): y = b * sqrt(1 - 1) = 0
        """
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        # At edge, x = 12 (opening/2 = semi-major axis)
        extension = arch_service.calculate_upright_extension(config, 24.0, 12.0)
        assert extension == pytest.approx(0.0)

    def test_upright_extension_elliptical_at_midpoint(
        self, arch_service: ArchService
    ) -> None:
        """Test elliptical upright extension at midpoint.

        At x = a/2: y = b * sqrt(1 - 0.25) = b * sqrt(0.75)
        """
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        # x = 6 (half of semi-major axis = 12)
        extension = arch_service.calculate_upright_extension(config, 24.0, 6.0)
        expected = 8.0 * math.sqrt(1 - (6.0 / 12.0) ** 2)  # 8 * sqrt(0.75)
        assert extension == pytest.approx(expected)

    def test_curve_points_elliptical(self, arch_service: ArchService) -> None:
        """Test curve points for elliptical arch."""
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        points = arch_service.generate_curve_points(config, 24.0, num_points=5)

        # At edges y should be 0
        assert points[0][1] == pytest.approx(0.0)
        assert points[4][1] == pytest.approx(0.0)

        # At center y should be b (8")
        assert points[2][1] == pytest.approx(8.0)


# =============================================================================
# ArchService Cut Metadata Tests
# =============================================================================


class TestArchServiceCutMetadata:
    """Tests for ArchService.create_cut_metadata()."""

    def test_create_cut_metadata_full_round(self, arch_service: ArchService) -> None:
        """Test cut metadata creation for full round arch."""
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        metadata = arch_service.create_cut_metadata(config, 24.0)

        assert isinstance(metadata, ArchCutMetadata)
        assert metadata.arch_type == ArchType.FULL_ROUND
        assert metadata.radius == pytest.approx(12.0)
        assert metadata.spring_height == pytest.approx(0.0)
        assert metadata.opening_width == pytest.approx(24.0)

    def test_create_cut_metadata_segmental(self, arch_service: ArchService) -> None:
        """Test cut metadata creation for segmental arch."""
        config = ArchConfig(
            arch_type=ArchType.SEGMENTAL, radius=18.0, spring_height=2.0
        )

        metadata = arch_service.create_cut_metadata(config, 24.0)

        assert metadata.arch_type == ArchType.SEGMENTAL
        assert metadata.radius == pytest.approx(18.0)
        assert metadata.spring_height == pytest.approx(2.0)
        assert metadata.opening_width == pytest.approx(24.0)


# =============================================================================
# ArchComponent Registration Tests
# =============================================================================


class TestArchComponentRegistration:
    """Tests for ArchComponent registration in the registry."""

    def test_arch_is_registered(self) -> None:
        """Test that decorative.arch is registered in the component registry."""
        assert "decorative.arch" in component_registry.list()

    def test_get_returns_arch_component_class(self) -> None:
        """Test that registry.get returns ArchComponent."""
        component_class = component_registry.get("decorative.arch")
        assert component_class is ArchComponent

    def test_can_instantiate_from_registry(self) -> None:
        """Test that component can be instantiated from registry."""
        component_class = component_registry.get("decorative.arch")
        component = component_class()
        assert isinstance(component, ArchComponent)


# =============================================================================
# ArchComponent Validation Tests
# =============================================================================


class TestArchComponentValidation:
    """Tests for ArchComponent.validate()."""

    def test_validate_returns_ok_for_empty_config(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok when no arch_top config present."""
        config: dict = {}

        result = arch_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_valid_full_round_auto(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid full_round with auto radius."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_ok_for_valid_segmental(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid segmental arch."""
        config = {"arch_top": {"arch_type": "segmental", "radius": 18.0}}

        result = arch_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_ok_for_valid_elliptical(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid elliptical arch."""
        config = {"arch_top": {"arch_type": "elliptical", "radius": 8.0}}

        result = arch_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_segmental_radius_too_small(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test FR-01.2: Segmental radius < opening/2 is rejected."""
        # Opening is 24", so radius must be >= 12"
        config = {"arch_top": {"arch_type": "segmental", "radius": 10.0}}

        result = arch_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("must be >= half opening" in e for e in result.errors)

    def test_validate_returns_error_for_full_round_radius_too_large(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that full_round with radius > opening/2 is rejected."""
        # Opening is 24", so radius should not exceed 12"
        config = {"arch_top": {"arch_type": "full_round", "radius": 15.0}}

        result = arch_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("exceeds half opening" in e for e in result.errors)

    def test_validate_returns_error_for_header_exceeds_section_height(
        self, arch_component: ArchComponent
    ) -> None:
        """Test that arch header taller than section is rejected."""
        # Create a short context where arch would be too tall
        short_context = ComponentContext(
            width=24.0,
            height=10.0,  # Too short for 12" arch
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=10.0,
            cabinet_depth=12.0,
        )
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.validate(config, short_context)

        assert not result.is_valid
        assert any("exceeds section height" in e for e in result.errors)

    def test_validate_returns_warning_for_tall_arch(
        self, arch_component: ArchComponent
    ) -> None:
        """Test warning for arch using > 50% of section height."""
        # Create context where arch uses > 50% height
        # 24" opening, full_round = 12" header. Need height < 24" for > 50%
        context = ComponentContext(
            width=24.0,
            height=20.0,  # 12/20 = 60% > 50%
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=20.0,
            cabinet_depth=12.0,
        )
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.validate(config, context)

        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("of section height" in w for w in result.warnings)

    def test_validate_returns_error_for_invalid_arch_type(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that invalid arch_type is rejected."""
        config = {"arch_top": {"arch_type": "gothic"}}  # Invalid type

        result = arch_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("Invalid arch config" in e for e in result.errors)

    def test_validate_returns_validation_result_type(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ValidationResult type."""
        config: dict = {}

        result = arch_component.validate(config, standard_context)

        assert isinstance(result, ValidationResult)


# =============================================================================
# ArchComponent Generation Tests
# =============================================================================


class TestArchComponentGeneration:
    """Tests for ArchComponent.generate()."""

    def test_generate_produces_one_panel(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate produces exactly 1 panel."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        assert len(result.panels) == 1

    def test_generate_panel_type_is_arch_header(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panel has ARCH_HEADER type."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        assert result.panels[0].panel_type == PanelType.ARCH_HEADER

    def test_generate_panel_dimensions_full_round(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel dimensions for full round arch."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        # Width should match opening width
        assert panel.width == pytest.approx(24.0)
        # Height should be radius (12" for 24" opening)
        assert panel.height == pytest.approx(12.0)

    def test_generate_panel_dimensions_elliptical(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel dimensions for elliptical arch."""
        config = {"arch_top": {"arch_type": "elliptical", "radius": 8.0}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.width == pytest.approx(24.0)
        assert panel.height == pytest.approx(8.0)

    def test_generate_panel_position(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel position is at top of section."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        # Panel should be at top of section: y = section_height - header_height
        # = 36 - 12 = 24
        assert panel.position.x == pytest.approx(0.0)
        assert panel.position.y == pytest.approx(24.0)

    def test_generate_panel_position_with_offset(
        self, arch_component: ArchComponent
    ) -> None:
        """Test panel position respects context position offset."""
        context = ComponentContext(
            width=24.0,
            height=36.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(10.0, 5.0),  # Offset from origin
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, context)

        panel = result.panels[0]
        # x = context.position.x = 10
        # y = context.position.y + context.height - header_height = 5 + 36 - 12 = 29
        assert panel.position.x == pytest.approx(10.0)
        assert panel.position.y == pytest.approx(29.0)

    def test_generate_panel_material(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel uses context material."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.material.thickness == pytest.approx(0.75)

    def test_generate_panel_metadata_contains_arch_type(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains arch_type."""
        config = {"arch_top": {"arch_type": "segmental", "radius": 18.0}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["arch_type"] == "segmental"

    def test_generate_panel_metadata_contains_radius(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains radius."""
        config = {"arch_top": {"arch_type": "segmental", "radius": 18.0}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["radius"] == pytest.approx(18.0)

    def test_generate_panel_metadata_contains_auto_radius(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains calculated radius for auto."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["radius"] == pytest.approx(12.0)

    def test_generate_panel_metadata_contains_spring_height(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains spring_height."""
        config = {
            "arch_top": {
                "arch_type": "full_round",
                "radius": "auto",
                "spring_height": 4.0,
            }
        }

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["spring_height"] == pytest.approx(4.0)

    def test_generate_panel_metadata_contains_opening_width(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains opening_width."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["opening_width"] == pytest.approx(24.0)

    def test_generate_panel_metadata_contains_arc_rise(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains arc_rise."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["arc_rise"] == pytest.approx(12.0)

    def test_generate_panel_metadata_contains_curve_points(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains curve_points."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        panel = result.panels[0]
        assert "curve_points" in panel.metadata
        assert len(panel.metadata["curve_points"]) == 21  # Default num_points

    def test_generate_result_metadata_contains_arch_config(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test result metadata contains arch_config dictionary."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        assert "arch_config" in result.metadata
        arch_config = result.metadata["arch_config"]
        assert arch_config["arch_type"] == "full_round"
        assert arch_config["radius"] == pytest.approx(12.0)
        assert arch_config["header_height"] == pytest.approx(12.0)
        assert arch_config["arc_rise"] == pytest.approx(12.0)

    def test_generate_result_metadata_contains_upright_extension(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test result metadata contains upright_extension_at_edge."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        assert "upright_extension_at_edge" in result.metadata

    def test_generate_returns_generation_result(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)

    def test_generate_returns_no_hardware(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns no hardware."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        result = arch_component.generate(config, standard_context)

        assert len(result.hardware) == 0


# =============================================================================
# ArchComponent Hardware Tests
# =============================================================================


class TestArchComponentHardware:
    """Tests for ArchComponent.hardware()."""

    def test_hardware_returns_empty_list(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list (arches have no hardware)."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        hardware = arch_component.hardware(config, standard_context)

        assert len(hardware) == 0

    def test_hardware_returns_list_type(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns a list."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        hardware = arch_component.hardware(config, standard_context)

        assert isinstance(hardware, list)


# =============================================================================
# Integration Tests
# =============================================================================


class TestArchComponentIntegration:
    """Integration tests for ArchComponent with the registry."""

    def test_full_workflow_full_round(self, standard_context: ComponentContext) -> None:
        """Test complete workflow for full_round arch."""
        component_class = component_registry.get("decorative.arch")
        component = component_class()

        config = {
            "arch_top": {
                "arch_type": "full_round",
                "radius": "auto",
                "spring_height": 0.0,
            }
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1

        # Verify panel
        panel = generation.panels[0]
        assert panel.panel_type == PanelType.ARCH_HEADER
        assert panel.width == pytest.approx(24.0)
        assert panel.height == pytest.approx(12.0)

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_full_workflow_segmental(self, standard_context: ComponentContext) -> None:
        """Test complete workflow for segmental arch."""
        component = ArchComponent()

        config = {"arch_top": {"arch_type": "segmental", "radius": 18.0}}

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1

        panel = generation.panels[0]
        assert panel.metadata["arch_type"] == "segmental"
        assert panel.metadata["radius"] == pytest.approx(18.0)

    def test_full_workflow_elliptical(self, standard_context: ComponentContext) -> None:
        """Test complete workflow for elliptical arch."""
        component = ArchComponent()

        config = {"arch_top": {"arch_type": "elliptical", "radius": 8.0}}

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1

        panel = generation.panels[0]
        assert panel.metadata["arch_type"] == "elliptical"
        assert panel.height == pytest.approx(8.0)

    def test_full_workflow_with_spring_height(
        self, standard_context: ComponentContext
    ) -> None:
        """Test workflow with non-zero spring height."""
        component = ArchComponent()

        config = {
            "arch_top": {
                "arch_type": "full_round",
                "radius": "auto",
                "spring_height": 4.0,
            }
        }

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        panel = generation.panels[0]

        # Header height = radius + spring = 12 + 4 = 16
        assert panel.height == pytest.approx(16.0)
        assert panel.metadata["spring_height"] == pytest.approx(4.0)


# =============================================================================
# Mathematical Verification Tests (from task spec)
# =============================================================================


class TestArchMathVerification:
    """Mathematical verification tests from task specification."""

    def test_full_round_24_opening(self) -> None:
        """Verify: 24\" opening, full_round, auto radius -> 12\" header."""
        service = ArchService()
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        header_height = service.calculate_header_height(config, 24.0)

        assert header_height == pytest.approx(12.0)

    def test_full_round_36_opening(self) -> None:
        """Verify: 36\" opening, full_round, auto radius -> 18\" header."""
        service = ArchService()
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        header_height = service.calculate_header_height(config, 36.0)

        assert header_height == pytest.approx(18.0)

    def test_elliptical_24_opening_8_radius(self) -> None:
        """Verify: 24\" opening, elliptical, 8\" radius -> 8\" header."""
        service = ArchService()
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        header_height = service.calculate_header_height(config, 24.0)

        assert header_height == pytest.approx(8.0)

    def test_segmental_math_formula(self) -> None:
        """Verify segmental arc rise formula: r - sqrt(r^2 - (w/2)^2)."""
        service = ArchService()

        # Test with r=18, w=24
        config = ArchConfig(arch_type=ArchType.SEGMENTAL, radius=18.0)
        arc_rise = service.calculate_arc_rise(config, 24.0)

        # Manual calculation
        r = 18.0
        w = 24.0
        expected = r - math.sqrt(r**2 - (w / 2) ** 2)

        assert arc_rise == pytest.approx(expected)

    def test_full_round_upright_extension_formula(self) -> None:
        """Verify semicircle formula: y = sqrt(r^2 - x^2)."""
        service = ArchService()
        config = ArchConfig(arch_type=ArchType.FULL_ROUND, radius="auto")

        # Test at various x positions
        r = 12.0  # For 24" opening
        for x in [0, 3, 6, 9, 11]:
            extension = service.calculate_upright_extension(config, 24.0, x)
            expected = math.sqrt(r**2 - x**2)
            assert extension == pytest.approx(expected, abs=1e-6)

    def test_elliptical_upright_extension_formula(self) -> None:
        """Verify ellipse formula: y = b * sqrt(1 - (x/a)^2)."""
        service = ArchService()
        config = ArchConfig(arch_type=ArchType.ELLIPTICAL, radius=8.0)

        # Test at various x positions
        a = 12.0  # Semi-major (24/2)
        b = 8.0  # Semi-minor (radius)
        for x in [0, 3, 6, 9, 11]:
            extension = service.calculate_upright_extension(config, 24.0, x)
            expected = b * math.sqrt(1 - (x / a) ** 2)
            assert extension == pytest.approx(expected, abs=1e-6)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestArchEdgeCases:
    """Edge case tests for ArchComponent and ArchService."""

    def test_very_small_opening(self, arch_component: ArchComponent) -> None:
        """Test arch with very small opening."""
        context = ComponentContext(
            width=6.0,  # Small opening
            height=12.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=6.0,
            cabinet_height=12.0,
            cabinet_depth=12.0,
        )
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        validation = arch_component.validate(config, context)
        assert validation.is_valid

        generation = arch_component.generate(config, context)
        panel = generation.panels[0]
        assert panel.width == pytest.approx(6.0)
        assert panel.height == pytest.approx(3.0)  # r = 3

    def test_large_spring_height(self, arch_component: ArchComponent) -> None:
        """Test arch with large spring height."""
        context = ComponentContext(
            width=24.0,
            height=48.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=48.0,
            cabinet_depth=12.0,
        )
        config = {
            "arch_top": {
                "arch_type": "full_round",
                "radius": "auto",
                "spring_height": 12.0,
            }
        }

        validation = arch_component.validate(config, context)
        assert validation.is_valid

        generation = arch_component.generate(config, context)
        panel = generation.panels[0]
        # Header = radius (12) + spring (12) = 24
        assert panel.height == pytest.approx(24.0)

    def test_segmental_radius_exactly_at_minimum(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test segmental with radius exactly at minimum (opening/2)."""
        # This is essentially a full_round at the limit
        config = {
            "arch_top": {
                "arch_type": "segmental",
                "radius": 12.0,  # Exactly opening/2
            }
        }

        validation = arch_component.validate(config, standard_context)
        assert validation.is_valid

    def test_default_spring_height_is_zero(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that default spring height is 0."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        generation = arch_component.generate(config, standard_context)
        panel = generation.panels[0]

        assert panel.metadata["spring_height"] == pytest.approx(0.0)

    def test_curve_points_count(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test that curve points defaults to 21 points."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        generation = arch_component.generate(config, standard_context)
        panel = generation.panels[0]

        assert len(panel.metadata["curve_points"]) == 21

    def test_curve_points_start_and_end_at_edges(
        self, arch_component: ArchComponent, standard_context: ComponentContext
    ) -> None:
        """Test curve points start and end at arch edges."""
        config = {"arch_top": {"arch_type": "full_round", "radius": "auto"}}

        generation = arch_component.generate(config, standard_context)
        panel = generation.panels[0]
        points = panel.metadata["curve_points"]

        # First point at left edge
        assert points[0][0] == pytest.approx(-12.0)
        # Last point at right edge
        assert points[-1][0] == pytest.approx(12.0)
