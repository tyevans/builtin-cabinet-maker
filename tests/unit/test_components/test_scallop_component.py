"""Tests for ScallopService and ScallopComponent implementation.

Tests for scallop pattern calculations, ScallopComponent validation, generation,
and hardware methods following the Component protocol for FRD-12 decorative
elements (FR-02 Scalloped Edges).
"""

from __future__ import annotations

import math

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    ScallopComponent,
    ScallopConfig,
    ScallopCutMetadata,
    ScallopService,
    ValidationResult,
    component_registry,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


# =============================================================================
# Registry Restoration Fixture
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def ensure_scallop_component_registered() -> None:
    """Ensure ScallopComponent is registered in the registry.

    This fixture directly registers the ScallopComponent if the registry
    was cleared by other tests, without reloading modules (which would
    cause isinstance failures across other tests).
    """
    if "decorative.scallop" not in component_registry.list():
        # Directly register ScallopComponent without module reload
        # This avoids class identity issues with isinstance checks
        component_registry._components["decorative.scallop"] = ScallopComponent


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def scallop_service() -> ScallopService:
    """Create a ScallopService instance for testing."""
    return ScallopService()


@pytest.fixture
def scallop_component() -> ScallopComponent:
    """Create a ScallopComponent instance for testing."""
    return ScallopComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 48" wide x 36" high section.
    """
    return ComponentContext(
        width=48.0,
        height=36.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=36.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def narrow_context() -> ComponentContext:
    """Create a narrow ComponentContext for testing.

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


# =============================================================================
# ScallopConfig Tests
# =============================================================================


class TestScallopConfig:
    """Tests for ScallopConfig dataclass."""

    def test_scallop_config_with_auto_count(self) -> None:
        """Test creating ScallopConfig with auto count."""
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        assert config.depth == 1.5
        assert config.width == 4.0
        assert config.count == "auto"

    def test_scallop_config_with_explicit_count(self) -> None:
        """Test creating ScallopConfig with explicit count."""
        config = ScallopConfig(depth=1.5, width=6.0, count=8)
        assert config.count == 8

    def test_scallop_config_rejects_zero_depth(self) -> None:
        """Test that zero depth is rejected in __post_init__."""
        with pytest.raises(ValueError, match="depth must be positive"):
            ScallopConfig(depth=0, width=4.0, count="auto")

    def test_scallop_config_rejects_negative_depth(self) -> None:
        """Test that negative depth is rejected in __post_init__."""
        with pytest.raises(ValueError, match="depth must be positive"):
            ScallopConfig(depth=-1.5, width=4.0, count="auto")

    def test_scallop_config_rejects_zero_width(self) -> None:
        """Test that zero width is rejected in __post_init__."""
        with pytest.raises(ValueError, match="width must be positive"):
            ScallopConfig(depth=1.5, width=0, count="auto")

    def test_scallop_config_rejects_negative_width(self) -> None:
        """Test that negative width is rejected in __post_init__."""
        with pytest.raises(ValueError, match="width must be positive"):
            ScallopConfig(depth=1.5, width=-4.0, count="auto")

    def test_scallop_config_rejects_zero_count(self) -> None:
        """Test that zero count is rejected in __post_init__."""
        with pytest.raises(ValueError, match="count must be at least 1"):
            ScallopConfig(depth=1.5, width=4.0, count=0)

    def test_scallop_config_rejects_negative_count(self) -> None:
        """Test that negative count is rejected in __post_init__."""
        with pytest.raises(ValueError, match="count must be at least 1"):
            ScallopConfig(depth=1.5, width=4.0, count=-1)


# =============================================================================
# ScallopConfig Calculate Count Tests
# =============================================================================


class TestScallopConfigCalculateCount:
    """Tests for ScallopConfig.calculate_count()."""

    def test_calculate_count_auto_exact_fit(self) -> None:
        """Test calculate_count with auto count where scallops fit exactly."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        # 48 / 6 = 8 scallops
        assert config.calculate_count(48.0) == 8

    def test_calculate_count_auto_rounded_down(self) -> None:
        """Test calculate_count with auto count rounded down."""
        config = ScallopConfig(depth=1.5, width=5.0, count="auto")
        # 48 / 5 = 9.6 -> 9 scallops
        assert config.calculate_count(48.0) == 9

    def test_calculate_count_auto_36_inch_piece(self) -> None:
        """Test calculate_count for 36\" piece with 4\" scallops."""
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        # 36 / 4 = 9 scallops
        assert config.calculate_count(36.0) == 9

    def test_calculate_count_auto_24_inch_piece(self) -> None:
        """Test calculate_count for 24\" piece with 4\" scallops."""
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        # 24 / 4 = 6 scallops
        assert config.calculate_count(24.0) == 6

    def test_calculate_count_explicit_ignores_width(self) -> None:
        """Test calculate_count with explicit count ignores piece width."""
        config = ScallopConfig(depth=1.5, width=4.0, count=12)
        assert config.calculate_count(48.0) == 12
        assert config.calculate_count(24.0) == 12

    def test_calculate_count_auto_minimum_one(self) -> None:
        """Test calculate_count with auto returns at least 1."""
        config = ScallopConfig(depth=1.5, width=100.0, count="auto")
        # 48 / 100 = 0.48 -> max(1, 0) = 1
        assert config.calculate_count(48.0) == 1


# =============================================================================
# ScallopConfig Calculate Actual Width Tests
# =============================================================================


class TestScallopConfigCalculateActualWidth:
    """Tests for ScallopConfig.calculate_actual_width()."""

    def test_calculate_actual_width_exact_fit(self) -> None:
        """Test actual width when scallops fit exactly."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        # 48 / 8 = 6.0
        assert config.calculate_actual_width(48.0) == pytest.approx(6.0)

    def test_calculate_actual_width_adjusted(self) -> None:
        """Test actual width is adjusted for symmetric pattern."""
        config = ScallopConfig(depth=1.5, width=5.0, count="auto")
        # 9 scallops for 48" -> 48 / 9 = 5.333...
        assert config.calculate_actual_width(48.0) == pytest.approx(48.0 / 9)

    def test_calculate_actual_width_from_task_spec(self) -> None:
        """Test cases from task specification table."""
        # 48" with 6" scallops -> 8 scallops at 6.0" each
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        assert config.calculate_actual_width(48.0) == pytest.approx(6.0)

        # 48" with 5" scallops -> 9 scallops at 5.33" each
        config = ScallopConfig(depth=1.5, width=5.0, count="auto")
        assert config.calculate_actual_width(48.0) == pytest.approx(48.0 / 9)

        # 36" with 4" scallops -> 9 scallops at 4.0" each
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        assert config.calculate_actual_width(36.0) == pytest.approx(4.0)


# =============================================================================
# ScallopService Pattern Calculation Tests
# =============================================================================


class TestScallopServiceCalculatePattern:
    """Tests for ScallopService.calculate_pattern()."""

    def test_calculate_pattern_returns_metadata(
        self, scallop_service: ScallopService
    ) -> None:
        """Test calculate_pattern returns ScallopCutMetadata."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = scallop_service.calculate_pattern(config, 48.0)
        assert isinstance(pattern, ScallopCutMetadata)

    def test_calculate_pattern_scallop_depth(
        self, scallop_service: ScallopService
    ) -> None:
        """Test pattern includes correct scallop depth."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = scallop_service.calculate_pattern(config, 48.0)
        assert pattern.scallop_depth == pytest.approx(1.5)

    def test_calculate_pattern_scallop_width(
        self, scallop_service: ScallopService
    ) -> None:
        """Test pattern includes calculated scallop width."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = scallop_service.calculate_pattern(config, 48.0)
        assert pattern.scallop_width == pytest.approx(6.0)

    def test_calculate_pattern_scallop_count(
        self, scallop_service: ScallopService
    ) -> None:
        """Test pattern includes correct scallop count."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = scallop_service.calculate_pattern(config, 48.0)
        assert pattern.scallop_count == 8

    def test_calculate_pattern_template_required(
        self, scallop_service: ScallopService
    ) -> None:
        """Test pattern indicates template is required."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = scallop_service.calculate_pattern(config, 48.0)
        assert pattern.template_required is True


# =============================================================================
# ScallopService Template Info Tests
# =============================================================================


class TestScallopServiceTemplateInfo:
    """Tests for ScallopService.generate_template_info()."""

    def test_generate_template_info_format(
        self, scallop_service: ScallopService
    ) -> None:
        """Test template info string format."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        info = scallop_service.generate_template_info(metadata)
        assert "Scallop template" in info

    def test_generate_template_info_contains_count(
        self, scallop_service: ScallopService
    ) -> None:
        """Test template info contains scallop count."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        info = scallop_service.generate_template_info(metadata)
        assert "8 scallops" in info

    def test_generate_template_info_contains_width(
        self, scallop_service: ScallopService
    ) -> None:
        """Test template info contains scallop width."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        info = scallop_service.generate_template_info(metadata)
        assert '6.00"' in info

    def test_generate_template_info_contains_depth(
        self, scallop_service: ScallopService
    ) -> None:
        """Test template info contains scallop depth."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        info = scallop_service.generate_template_info(metadata)
        assert '1.50"' in info


# =============================================================================
# ScallopService Scallop Centers Tests
# =============================================================================


class TestScallopServiceCalculateCenters:
    """Tests for ScallopService.calculate_scallop_centers()."""

    def test_calculate_centers_count(
        self, scallop_service: ScallopService
    ) -> None:
        """Test correct number of centers are returned."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        centers = scallop_service.calculate_scallop_centers(metadata, 48.0)
        assert len(centers) == 8

    def test_calculate_centers_first_position(
        self, scallop_service: ScallopService
    ) -> None:
        """Test first center is at half scallop width."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        centers = scallop_service.calculate_scallop_centers(metadata, 48.0)
        assert centers[0] == pytest.approx(3.0)  # 6.0 / 2

    def test_calculate_centers_last_position(
        self, scallop_service: ScallopService
    ) -> None:
        """Test last center is at piece_width - half scallop width."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        centers = scallop_service.calculate_scallop_centers(metadata, 48.0)
        assert centers[-1] == pytest.approx(45.0)  # 48 - 3

    def test_calculate_centers_evenly_distributed(
        self, scallop_service: ScallopService
    ) -> None:
        """Test centers are evenly distributed."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        centers = scallop_service.calculate_scallop_centers(metadata, 48.0)

        # Check spacing between consecutive centers
        for i in range(1, len(centers)):
            spacing = centers[i] - centers[i - 1]
            assert spacing == pytest.approx(6.0)

    def test_calculate_centers_symmetry(
        self, scallop_service: ScallopService
    ) -> None:
        """Test centers are symmetric about piece center (FR-02.4)."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=8,
            template_required=True,
        )
        piece_width = 48.0
        centers = scallop_service.calculate_scallop_centers(metadata, piece_width)

        # Check symmetry: center[i] and center[n-1-i] should be equidistant from center
        n = len(centers)
        for i in range(n // 2):
            dist_left = piece_width / 2 - centers[i]
            dist_right = centers[n - 1 - i] - piece_width / 2
            assert dist_left == pytest.approx(dist_right)


# =============================================================================
# ScallopService Generate Scallop Points Tests
# =============================================================================


class TestScallopServiceGeneratePoints:
    """Tests for ScallopService.generate_scallop_points()."""

    def test_generate_points_returns_list(
        self, scallop_service: ScallopService
    ) -> None:
        """Test generate_scallop_points returns a list of tuples."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=2,
            template_required=True,
        )
        points = scallop_service.generate_scallop_points(metadata)
        assert isinstance(points, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in points)

    def test_generate_points_start_at_origin(
        self, scallop_service: ScallopService
    ) -> None:
        """Test first point starts at x=0, y=0."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=2,
            template_required=True,
        )
        points = scallop_service.generate_scallop_points(metadata)
        assert points[0][0] == pytest.approx(0.0)
        assert points[0][1] == pytest.approx(0.0)

    def test_generate_points_end_at_piece_width(
        self, scallop_service: ScallopService
    ) -> None:
        """Test last point ends at x=piece_width (scallop_width * count)."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=2,
            template_required=True,
        )
        points = scallop_service.generate_scallop_points(metadata)
        # 2 scallops * 6" = 12" total
        assert points[-1][0] == pytest.approx(12.0)
        assert points[-1][1] == pytest.approx(0.0)

    def test_generate_points_max_depth_at_center(
        self, scallop_service: ScallopService
    ) -> None:
        """Test scallop reaches max depth at center."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=1,
            template_required=True,
        )
        points = scallop_service.generate_scallop_points(metadata, num_points_per_scallop=11)

        # Find the center point (should be at index 5 for 11 points)
        center_point = points[5]
        assert center_point[0] == pytest.approx(3.0)  # Center of 6" scallop
        assert center_point[1] == pytest.approx(1.5)  # Max depth

    def test_generate_points_y_never_exceeds_depth(
        self, scallop_service: ScallopService
    ) -> None:
        """Test y values never exceed scallop depth."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=3,
            template_required=True,
        )
        points = scallop_service.generate_scallop_points(metadata)
        for x, y in points:
            assert y <= metadata.scallop_depth + 1e-10


# =============================================================================
# ScallopService Validate Pattern Tests
# =============================================================================


class TestScallopServiceValidatePattern:
    """Tests for ScallopService.validate_pattern()."""

    def test_validate_pattern_valid_config(
        self, scallop_service: ScallopService
    ) -> None:
        """Test validation passes for valid configuration."""
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        errors, warnings = scallop_service.validate_pattern(config, 48.0, 4.0)
        assert len(errors) == 0

    def test_validate_pattern_depth_exceeds_height(
        self, scallop_service: ScallopService
    ) -> None:
        """Test error when scallop depth >= piece height."""
        config = ScallopConfig(depth=5.0, width=6.0, count="auto")
        errors, warnings = scallop_service.validate_pattern(config, 48.0, 4.0)
        assert len(errors) > 0
        assert any("exceeds piece height" in e for e in errors)

    def test_validate_pattern_depth_more_than_half_height_warning(
        self, scallop_service: ScallopService
    ) -> None:
        """Test warning when scallop depth > 50% of piece height."""
        config = ScallopConfig(depth=2.5, width=6.0, count="auto")
        errors, warnings = scallop_service.validate_pattern(config, 48.0, 4.0)
        assert len(errors) == 0
        assert len(warnings) > 0
        assert any("more than half" in w for w in warnings)

    def test_validate_pattern_too_many_scallops_warning(
        self, scallop_service: ScallopService
    ) -> None:
        """Test warning when > 20 scallops."""
        config = ScallopConfig(depth=1.5, width=2.0, count="auto")
        # 48 / 2 = 24 scallops
        errors, warnings = scallop_service.validate_pattern(config, 48.0, 4.0)
        assert any("24 scallops" in w for w in warnings)

    def test_validate_pattern_narrow_aspect_ratio_warning(
        self, scallop_service: ScallopService
    ) -> None:
        """Test warning for narrow aspect ratio (< 1.5)."""
        config = ScallopConfig(depth=4.0, width=5.0, count="auto")
        # 9 scallops at 5.33" width, depth 4" -> ratio ~1.33
        errors, warnings = scallop_service.validate_pattern(config, 48.0, 10.0)
        assert any("narrow" in w.lower() for w in warnings)

    def test_validate_pattern_wide_aspect_ratio_warning(
        self, scallop_service: ScallopService
    ) -> None:
        """Test warning for wide aspect ratio (> 4)."""
        config = ScallopConfig(depth=1.0, width=6.0, count="auto")
        # 8 scallops at 6" width, depth 1" -> ratio 6
        errors, warnings = scallop_service.validate_pattern(config, 48.0, 4.0)
        assert any("wide" in w.lower() for w in warnings)


# =============================================================================
# ScallopComponent Registration Tests
# =============================================================================


class TestScallopComponentRegistration:
    """Tests for ScallopComponent registration in the registry."""

    def test_scallop_is_registered(self) -> None:
        """Test that decorative.scallop is registered in the component registry."""
        assert "decorative.scallop" in component_registry.list()

    def test_get_returns_scallop_component_class(self) -> None:
        """Test that registry.get returns ScallopComponent."""
        component_class = component_registry.get("decorative.scallop")
        assert component_class is ScallopComponent

    def test_can_instantiate_from_registry(self) -> None:
        """Test that component can be instantiated from registry."""
        component_class = component_registry.get("decorative.scallop")
        component = component_class()
        assert isinstance(component, ScallopComponent)


# =============================================================================
# ScallopComponent Validation Tests
# =============================================================================


class TestScallopComponentValidation:
    """Tests for ScallopComponent.validate()."""

    def test_validate_returns_ok_for_empty_config(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok when no scallop config present."""
        config: dict = {}
        result = scallop_component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_valid_config(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid configuration."""
        config = {
            "scallop": {"depth": 0.5, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }
        result = scallop_component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_returns_error_for_depth_exceeds_material_thickness(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test error when depth >= material thickness."""
        config = {
            "scallop": {"depth": 1.0, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }
        # Material thickness is 0.75"
        result = scallop_component.validate(config, standard_context)
        assert not result.is_valid
        assert any("material thickness" in e for e in result.errors)

    def test_validate_returns_error_for_depth_exceeds_valance_height(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test error when depth >= valance height."""
        config = {
            "scallop": {"depth": 0.5, "width": 6.0, "count": "auto"},
            "valance_height": 0.4,
        }
        result = scallop_component.validate(config, standard_context)
        assert not result.is_valid
        assert any("exceeds piece height" in e for e in result.errors)

    def test_validate_returns_validation_result_type(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ValidationResult type."""
        config: dict = {}
        result = scallop_component.validate(config, standard_context)
        assert isinstance(result, ValidationResult)


# =============================================================================
# ScallopComponent Generation Tests
# =============================================================================


class TestScallopComponentGeneration:
    """Tests for ScallopComponent.generate()."""

    def test_generate_produces_one_panel(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate produces exactly 1 panel."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        assert len(result.panels) == 1

    def test_generate_panel_type_is_valance(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panel has VALANCE type."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        assert result.panels[0].panel_type == PanelType.VALANCE

    def test_generate_panel_dimensions(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel dimensions match context width and valance height."""
        config = {
            "scallop": {"depth": 1.5, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert panel.width == pytest.approx(48.0)
        assert panel.height == pytest.approx(4.0)

    def test_generate_panel_position(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel position is at top of section."""
        config = {
            "scallop": {"depth": 1.5, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        # y = section_height - valance_height = 36 - 4 = 32
        assert panel.position.x == pytest.approx(0.0)
        assert panel.position.y == pytest.approx(32.0)

    def test_generate_panel_position_with_offset(
        self, scallop_component: ScallopComponent
    ) -> None:
        """Test panel position respects context position offset."""
        context = ComponentContext(
            width=48.0,
            height=36.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(10.0, 5.0),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {
            "scallop": {"depth": 1.5, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }
        result = scallop_component.generate(config, context)
        panel = result.panels[0]
        # x = 10, y = 5 + 36 - 4 = 37
        assert panel.position.x == pytest.approx(10.0)
        assert panel.position.y == pytest.approx(37.0)

    def test_generate_panel_material(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel uses context material."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert panel.material.thickness == pytest.approx(0.75)

    def test_generate_panel_metadata_contains_scallop_depth(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains scallop_depth."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert panel.metadata["scallop_depth"] == pytest.approx(1.5)

    def test_generate_panel_metadata_contains_scallop_width(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains scallop_width."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert panel.metadata["scallop_width"] == pytest.approx(6.0)

    def test_generate_panel_metadata_contains_scallop_count(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains scallop_count."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert panel.metadata["scallop_count"] == 8

    def test_generate_panel_metadata_contains_scallop_centers(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains scallop_centers list."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert "scallop_centers" in panel.metadata
        assert len(panel.metadata["scallop_centers"]) == 8

    def test_generate_panel_metadata_contains_scallop_points(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains scallop_points list."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert "scallop_points" in panel.metadata
        assert len(panel.metadata["scallop_points"]) > 0

    def test_generate_panel_metadata_contains_template_info(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains template_info string."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert "template_info" in panel.metadata
        assert "Scallop template" in panel.metadata["template_info"]

    def test_generate_panel_metadata_contains_template_required(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test panel metadata contains template_required flag."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        panel = result.panels[0]
        assert panel.metadata["template_required"] is True

    def test_generate_result_metadata_contains_scallop_pattern(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test result metadata contains scallop_pattern dictionary."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        assert "scallop_pattern" in result.metadata
        pattern = result.metadata["scallop_pattern"]
        assert pattern["depth"] == pytest.approx(1.5)
        assert pattern["width"] == pytest.approx(6.0)
        assert pattern["count"] == 8

    def test_generate_returns_generation_result(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        assert isinstance(result, GenerationResult)

    def test_generate_returns_no_hardware(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns no hardware."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        result = scallop_component.generate(config, standard_context)
        assert len(result.hardware) == 0


# =============================================================================
# ScallopComponent Hardware Tests
# =============================================================================


class TestScallopComponentHardware:
    """Tests for ScallopComponent.hardware()."""

    def test_hardware_returns_empty_list(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list (scallops have no hardware)."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        hardware = scallop_component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_hardware_returns_list_type(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns a list."""
        config = {"scallop": {"depth": 1.5, "width": 6.0, "count": "auto"}}
        hardware = scallop_component.hardware(config, standard_context)
        assert isinstance(hardware, list)


# =============================================================================
# Integration Tests
# =============================================================================


class TestScallopComponentIntegration:
    """Integration tests for ScallopComponent with the registry."""

    def test_full_workflow_auto_count(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow with auto count."""
        component_class = component_registry.get("decorative.scallop")
        component = component_class()

        config = {
            "scallop": {"depth": 0.5, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1

        # Verify panel
        panel = generation.panels[0]
        assert panel.panel_type == PanelType.VALANCE
        assert panel.width == pytest.approx(48.0)
        assert panel.height == pytest.approx(4.0)
        assert panel.metadata["scallop_count"] == 8

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_full_workflow_explicit_count(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow with explicit count."""
        component = ScallopComponent()

        config = {
            "scallop": {"depth": 0.5, "width": 4.0, "count": 12},
            "valance_height": 4.0,
        }

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        panel = generation.panels[0]

        # With explicit count of 12, actual width = 48 / 12 = 4.0
        assert panel.metadata["scallop_count"] == 12
        assert panel.metadata["scallop_width"] == pytest.approx(4.0)

    def test_full_workflow_narrow_piece(
        self, narrow_context: ComponentContext
    ) -> None:
        """Test complete workflow with narrow 24\" piece."""
        component = ScallopComponent()

        config = {
            "scallop": {"depth": 0.5, "width": 4.0, "count": "auto"},
            "valance_height": 4.0,
        }

        validation = component.validate(config, narrow_context)
        assert validation.is_valid

        generation = component.generate(config, narrow_context)
        panel = generation.panels[0]

        # 24 / 4 = 6 scallops
        assert panel.width == pytest.approx(24.0)
        assert panel.metadata["scallop_count"] == 6


# =============================================================================
# Task Specification Verification Tests
# =============================================================================


class TestScallopTaskSpecVerification:
    """Verification tests from task specification."""

    def test_auto_count_48_6_returns_12(self) -> None:
        """Verify: 48\" piece with 4\" scallops -> 12 scallops (FR-02.2)."""
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        assert config.calculate_count(48.0) == 12

    def test_symmetric_pattern_centers(self) -> None:
        """Verify: centers are evenly distributed (FR-02.4)."""
        service = ScallopService()
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = service.calculate_pattern(config, 48.0)
        centers = service.calculate_scallop_centers(pattern, 48.0)

        assert len(centers) == pattern.scallop_count

        # Verify even spacing
        for i in range(1, len(centers)):
            assert centers[i] - centers[i - 1] == pytest.approx(6.0)

    def test_template_info_generated(self) -> None:
        """Verify: template info is generated (FR-02.5)."""
        service = ScallopService()
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        pattern = service.calculate_pattern(config, 48.0)
        template = service.generate_template_info(pattern)

        assert "Scallop template" in template
        assert str(pattern.scallop_count) in template

    def test_task_spec_table_cases(self) -> None:
        """Verify test cases from task specification table."""
        # 48" with 6" scallops -> 8 scallops at 6.0"
        config = ScallopConfig(depth=1.5, width=6.0, count="auto")
        assert config.calculate_count(48.0) == 8
        assert config.calculate_actual_width(48.0) == pytest.approx(6.0)

        # 48" with 5" scallops -> 9 scallops at 5.33"
        config = ScallopConfig(depth=1.5, width=5.0, count="auto")
        assert config.calculate_count(48.0) == 9
        assert config.calculate_actual_width(48.0) == pytest.approx(48.0 / 9)

        # 36" with 4" scallops -> 9 scallops at 4.0"
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        assert config.calculate_count(36.0) == 9
        assert config.calculate_actual_width(36.0) == pytest.approx(4.0)

        # 24" with 4" scallops -> 6 scallops at 4.0"
        config = ScallopConfig(depth=1.5, width=4.0, count="auto")
        assert config.calculate_count(24.0) == 6
        assert config.calculate_actual_width(24.0) == pytest.approx(4.0)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestScallopEdgeCases:
    """Edge case tests for ScallopComponent and ScallopService."""

    def test_single_scallop(
        self, scallop_component: ScallopComponent
    ) -> None:
        """Test scallop pattern with single scallop."""
        context = ComponentContext(
            width=6.0,
            height=12.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=6.0,
            cabinet_height=12.0,
            cabinet_depth=12.0,
        )
        config = {
            "scallop": {"depth": 0.5, "width": 6.0, "count": "auto"},
            "valance_height": 4.0,
        }

        validation = scallop_component.validate(config, context)
        assert validation.is_valid

        generation = scallop_component.generate(config, context)
        panel = generation.panels[0]
        assert panel.metadata["scallop_count"] == 1

    def test_wide_scallops_forced_to_one(self) -> None:
        """Test very wide scallops forced to count of 1."""
        config = ScallopConfig(depth=1.5, width=100.0, count="auto")
        assert config.calculate_count(48.0) == 1

    def test_default_valance_height_used(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test default valance height of 4.0 is used."""
        config = {"scallop": {"depth": 0.5, "width": 6.0, "count": "auto"}}
        # No valance_height specified

        generation = scallop_component.generate(config, standard_context)
        panel = generation.panels[0]
        assert panel.height == pytest.approx(4.0)

    def test_custom_valance_height(
        self, scallop_component: ScallopComponent, standard_context: ComponentContext
    ) -> None:
        """Test custom valance height is used."""
        config = {
            "scallop": {"depth": 0.5, "width": 6.0, "count": "auto"},
            "valance_height": 6.0,
        }

        generation = scallop_component.generate(config, standard_context)
        panel = generation.panels[0]
        assert panel.height == pytest.approx(6.0)

    def test_scallop_points_for_multiple_scallops(
        self, scallop_service: ScallopService
    ) -> None:
        """Test scallop points cover all scallops without gaps."""
        metadata = ScallopCutMetadata(
            scallop_depth=1.5,
            scallop_width=6.0,
            scallop_count=3,
            template_required=True,
        )
        points = scallop_service.generate_scallop_points(metadata, num_points_per_scallop=5)

        # Should have points from x=0 to x=18 (3 scallops * 6")
        x_values = [p[0] for p in points]
        assert min(x_values) == pytest.approx(0.0)
        assert max(x_values) == pytest.approx(18.0)
