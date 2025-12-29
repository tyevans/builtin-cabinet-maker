"""Tests for MoldingZoneService and molding zone components.

Tests for MoldingZoneService, CrownMoldingComponent, ToeKickComponent,
and LightRailComponent following the Component protocol for FRD-12
decorative elements Phase 7.
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    BaseZone,
    ComponentContext,
    CrownMoldingComponent,
    CrownMoldingZone,
    GenerationResult,
    HardwareItem,
    LightRailComponent,
    LightRailZone,
    MoldingZoneService,
    ToeKickComponent,
    ValidationResult,
    component_registry,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def molding_zone_service() -> MoldingZoneService:
    """Create a MoldingZoneService instance for testing."""
    return MoldingZoneService()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 48" wide x 84" high section
    at position (0, 0) within a 48x84x12 cabinet.
    """
    return ComponentContext(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def wall_cabinet_context() -> ComponentContext:
    """Create a wall cabinet context for light rail testing.

    Returns a context representing a 36" wide x 30" high wall cabinet.
    """
    return ComponentContext(
        width=36.0,
        height=30.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=36.0,
        cabinet_height=30.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def crown_molding_component() -> CrownMoldingComponent:
    """Create a CrownMoldingComponent instance for testing."""
    return CrownMoldingComponent()


@pytest.fixture
def toe_kick_component() -> ToeKickComponent:
    """Create a ToeKickComponent instance for testing."""
    return ToeKickComponent()


@pytest.fixture
def light_rail_component() -> LightRailComponent:
    """Create a LightRailComponent instance for testing."""
    return LightRailComponent()


# =============================================================================
# MoldingZoneService Tests
# =============================================================================


class TestMoldingZoneServiceCrownAdjustments:
    """Tests for MoldingZoneService.calculate_crown_adjustments()."""

    def test_calculate_crown_adjustments_returns_dict(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test that calculate_crown_adjustments returns a dict."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)

        result = molding_zone_service.calculate_crown_adjustments(config, 48.0, 12.0)

        assert isinstance(result, dict)

    def test_calculate_crown_adjustments_top_panel_reduction(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test top_panel_depth_reduction equals setback."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)

        result = molding_zone_service.calculate_crown_adjustments(config, 48.0, 12.0)

        assert result["top_panel_depth_reduction"] == pytest.approx(1.0)

    def test_calculate_crown_adjustments_nailer_width(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test nailer_width equals cabinet_width."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)

        result = molding_zone_service.calculate_crown_adjustments(config, 48.0, 12.0)

        assert result["nailer_width"] == pytest.approx(48.0)

    def test_calculate_crown_adjustments_nailer_depth(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test nailer_depth equals cabinet_depth."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)

        result = molding_zone_service.calculate_crown_adjustments(config, 48.0, 12.0)

        assert result["nailer_depth"] == pytest.approx(12.0)

    def test_calculate_crown_adjustments_zone_height(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test zone_height equals config height."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)

        result = molding_zone_service.calculate_crown_adjustments(config, 48.0, 12.0)

        assert result["zone_height"] == pytest.approx(4.0)


class TestMoldingZoneServiceGenerateCrownNailer:
    """Tests for MoldingZoneService.generate_crown_nailer()."""

    def test_generate_crown_nailer_returns_panel(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test that generate_crown_nailer returns a Panel."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_crown_nailer(
            config, 48.0, 84.0, 12.0, material, position
        )

        assert result is not None
        assert result.panel_type == PanelType.NAILER

    def test_generate_crown_nailer_dimensions(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test nailer panel dimensions."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_crown_nailer(
            config, 48.0, 84.0, 12.0, material, position
        )

        assert result.width == pytest.approx(48.0)
        assert result.height == pytest.approx(2.5)

    def test_generate_crown_nailer_position_at_top(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test nailer is positioned at top of cabinet."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_crown_nailer(
            config, 48.0, 84.0, 12.0, material, position
        )

        # Position y should be cabinet_height - nailer_width
        expected_y = 84.0 - 2.5
        assert result.position.y == pytest.approx(expected_y)

    def test_generate_crown_nailer_metadata(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test nailer metadata contains zone information."""
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_crown_nailer(
            config, 48.0, 84.0, 12.0, material, position
        )

        assert result.metadata["zone_type"] == "crown_molding"
        assert result.metadata["zone_height"] == 4.0
        assert result.metadata["setback"] == 1.0
        assert result.metadata["location"] == "top_back"


class TestMoldingZoneServiceToeKickAdjustments:
    """Tests for MoldingZoneService.calculate_toe_kick_adjustments()."""

    def test_toe_kick_adjustments_returns_values(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test toe kick adjustments for toe_kick type."""
        config = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")

        result = molding_zone_service.calculate_toe_kick_adjustments(config)

        assert result["bottom_panel_raise"] == 4.0
        assert result["side_panel_reduction"] == 4.0
        assert result["toe_kick_height"] == 4.0
        assert result["toe_kick_setback"] == 3.0

    def test_base_molding_adjustments_returns_zeros(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test adjustments are zero for base_molding type."""
        config = BaseZone(height=4.0, setback=3.0, zone_type="base_molding")

        result = molding_zone_service.calculate_toe_kick_adjustments(config)

        assert result["bottom_panel_raise"] == 0
        assert result["side_panel_reduction"] == 0
        assert result["toe_kick_height"] == 0
        assert result["toe_kick_setback"] == 0


class TestMoldingZoneServiceGenerateToeKick:
    """Tests for MoldingZoneService.generate_toe_kick_panel()."""

    def test_generate_toe_kick_panel_returns_panel(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test that generate_toe_kick_panel returns a Panel for toe_kick type."""
        config = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_toe_kick_panel(
            config, 48.0, material, position
        )

        assert result is not None
        assert result.panel_type == PanelType.TOE_KICK

    def test_generate_toe_kick_panel_dimensions(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test toe kick panel dimensions."""
        config = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_toe_kick_panel(
            config, 48.0, material, position
        )

        assert result.width == pytest.approx(48.0)
        assert result.height == pytest.approx(4.0)

    def test_generate_toe_kick_panel_metadata(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test toe kick panel metadata."""
        config = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_toe_kick_panel(
            config, 48.0, material, position
        )

        assert result.metadata["zone_type"] == "toe_kick"
        assert result.metadata["setback"] == 3.0
        assert result.metadata["location"] == "bottom_front_recessed"

    def test_generate_toe_kick_returns_none_for_base_molding(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test that generate_toe_kick_panel returns None for base_molding type."""
        config = BaseZone(height=4.0, setback=3.0, zone_type="base_molding")
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_toe_kick_panel(
            config, 48.0, material, position
        )

        assert result is None


class TestMoldingZoneServiceGenerateLightRail:
    """Tests for MoldingZoneService.generate_light_rail_strip()."""

    def test_generate_light_rail_strip_returns_panel(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test that generate_light_rail_strip returns a Panel when generate_strip=True."""
        config = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_light_rail_strip(
            config, 36.0, material, position
        )

        assert result is not None
        assert result.panel_type == PanelType.LIGHT_RAIL

    def test_generate_light_rail_strip_dimensions(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test light rail strip dimensions."""
        config = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_light_rail_strip(
            config, 36.0, material, position
        )

        assert result.width == pytest.approx(36.0)
        assert result.height == pytest.approx(1.5)

    def test_generate_light_rail_strip_metadata(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test light rail strip metadata."""
        config = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_light_rail_strip(
            config, 36.0, material, position
        )

        assert result.metadata["zone_type"] == "light_rail"
        assert result.metadata["setback"] == 0.25
        assert result.metadata["location"] == "bottom_front"

    def test_generate_light_rail_returns_none_when_generate_strip_false(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test that generate_light_rail_strip returns None when generate_strip=False."""
        config = LightRailZone(height=1.5, setback=0.25, generate_strip=False)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_light_rail_strip(
            config, 36.0, material, position
        )

        assert result is None


class TestMoldingZoneServiceValidation:
    """Tests for MoldingZoneService.validate_zones()."""

    def test_validate_zones_no_zones(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test validation passes with no zones."""
        errors, warnings = molding_zone_service.validate_zones(
            crown=None,
            base=None,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_zones_crown_setback_exceeds_depth(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test error when crown setback exceeds cabinet depth."""
        crown = CrownMoldingZone(height=4.0, setback=15.0, nailer_width=2.5)

        errors, warnings = molding_zone_service.validate_zones(
            crown=crown,
            base=None,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("exceeds cabinet depth" in e for e in errors)

    def test_validate_zones_crown_height_warning(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test warning when crown height exceeds 20% of cabinet height."""
        # 84" cabinet, 20% = 16.8", so 18" should trigger warning
        crown = CrownMoldingZone(height=18.0, setback=1.0, nailer_width=2.5)

        errors, warnings = molding_zone_service.validate_zones(
            crown=crown,
            base=None,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("more than 20%" in w for w in warnings)

    def test_validate_zones_toe_kick_height_warning(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test warning when toe kick height is less than 3\"."""
        base = BaseZone(height=2.5, setback=3.0, zone_type="toe_kick")

        errors, warnings = molding_zone_service.validate_zones(
            crown=None,
            base=base,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("less than" in w and "3\"" in w for w in warnings)

    def test_validate_zones_toe_kick_setback_warning(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test warning when toe kick setback is less than 2\"."""
        base = BaseZone(height=3.5, setback=1.5, zone_type="toe_kick")

        errors, warnings = molding_zone_service.validate_zones(
            crown=None,
            base=base,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("less than" in w and "2\"" in w for w in warnings)

    def test_validate_zones_light_rail_height_warning(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test warning when light rail height exceeds 3\"."""
        light_rail = LightRailZone(height=4.0, setback=0.25, generate_strip=True)

        errors, warnings = molding_zone_service.validate_zones(
            crown=None,
            base=None,
            light_rail=light_rail,
            cabinet_height=30.0,
            cabinet_depth=12.0,
        )

        assert any("may be too tall" in w for w in warnings)

    def test_validate_zones_total_height_warning(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test warning when total zone height exceeds 30% of cabinet height."""
        # 84" cabinet, 30% = 25.2"
        crown = CrownMoldingZone(height=15.0, setback=1.0, nailer_width=2.5)
        base = BaseZone(height=12.0, setback=3.0, zone_type="toe_kick")

        errors, warnings = molding_zone_service.validate_zones(
            crown=crown,
            base=base,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("more than 30%" in w for w in warnings)

    def test_validate_zones_total_height_exceeds_cabinet(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test error when total zone height exceeds cabinet height."""
        crown = CrownMoldingZone(height=50.0, setback=1.0, nailer_width=2.5)
        base = BaseZone(height=40.0, setback=3.0, zone_type="toe_kick")

        errors, warnings = molding_zone_service.validate_zones(
            crown=crown,
            base=base,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("exceeds cabinet" in e for e in errors)


class TestMoldingZoneServiceGenerateAllPanels:
    """Tests for MoldingZoneService.generate_all_zone_panels()."""

    def test_generate_all_zone_panels_empty(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test empty list when no zones configured."""
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_all_zone_panels(
            crown=None,
            base=None,
            light_rail=None,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
            material=material,
            position=position,
        )

        assert len(result) == 0

    def test_generate_all_zone_panels_crown_only(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test generating only crown nailer."""
        crown = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_all_zone_panels(
            crown=crown,
            base=None,
            light_rail=None,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
            material=material,
            position=position,
        )

        assert len(result) == 1
        assert result[0].panel_type == PanelType.NAILER

    def test_generate_all_zone_panels_toe_kick_only(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test generating only toe kick panel."""
        base = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_all_zone_panels(
            crown=None,
            base=base,
            light_rail=None,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
            material=material,
            position=position,
        )

        assert len(result) == 1
        assert result[0].panel_type == PanelType.TOE_KICK

    def test_generate_all_zone_panels_light_rail_only(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test generating only light rail strip."""
        light_rail = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_all_zone_panels(
            crown=None,
            base=None,
            light_rail=light_rail,
            cabinet_width=36.0,
            cabinet_height=30.0,
            cabinet_depth=12.0,
            material=material,
            position=position,
        )

        assert len(result) == 1
        assert result[0].panel_type == PanelType.LIGHT_RAIL

    def test_generate_all_zone_panels_all_zones(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test generating all zone panels."""
        crown = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        base = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        light_rail = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        result = molding_zone_service.generate_all_zone_panels(
            crown=crown,
            base=base,
            light_rail=light_rail,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
            material=material,
            position=position,
        )

        assert len(result) == 3
        panel_types = [p.panel_type for p in result]
        assert PanelType.NAILER in panel_types
        assert PanelType.TOE_KICK in panel_types
        assert PanelType.LIGHT_RAIL in panel_types


class TestMoldingZoneServiceDimensionAdjustments:
    """Tests for MoldingZoneService.get_dimension_adjustments()."""

    def test_get_dimension_adjustments_no_zones(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test default adjustments with no zones."""
        result = molding_zone_service.get_dimension_adjustments(
            crown=None,
            base=None,
            cabinet_depth=12.0,
        )

        assert result["top_panel_depth_reduction"] == 0.0
        assert result["bottom_panel_raise"] == 0.0
        assert result["side_panel_bottom_raise"] == 0.0

    def test_get_dimension_adjustments_crown_only(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test adjustments with crown zone only."""
        crown = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)

        result = molding_zone_service.get_dimension_adjustments(
            crown=crown,
            base=None,
            cabinet_depth=12.0,
        )

        assert result["top_panel_depth_reduction"] == 1.0
        assert result["bottom_panel_raise"] == 0.0
        assert result["side_panel_bottom_raise"] == 0.0

    def test_get_dimension_adjustments_toe_kick_only(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test adjustments with toe kick zone only."""
        base = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")

        result = molding_zone_service.get_dimension_adjustments(
            crown=None,
            base=base,
            cabinet_depth=12.0,
        )

        assert result["top_panel_depth_reduction"] == 0.0
        assert result["bottom_panel_raise"] == 4.0
        assert result["side_panel_bottom_raise"] == 4.0

    def test_get_dimension_adjustments_both_zones(
        self, molding_zone_service: MoldingZoneService
    ) -> None:
        """Test adjustments with both crown and toe kick zones."""
        crown = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        base = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")

        result = molding_zone_service.get_dimension_adjustments(
            crown=crown,
            base=base,
            cabinet_depth=12.0,
        )

        assert result["top_panel_depth_reduction"] == 1.0
        assert result["bottom_panel_raise"] == 4.0
        assert result["side_panel_bottom_raise"] == 4.0


# =============================================================================
# CrownMoldingComponent Registration Tests
# =============================================================================


class TestCrownMoldingComponentRegistration:
    """Tests for CrownMoldingComponent registration in the registry."""

    def test_crown_molding_is_registered(self) -> None:
        """Test that decorative.crown_molding is registered."""
        assert "decorative.crown_molding" in component_registry.list()

    def test_get_returns_crown_molding_component_class(self) -> None:
        """Test that registry.get returns CrownMoldingComponent."""
        component_class = component_registry.get("decorative.crown_molding")
        assert component_class is CrownMoldingComponent

    def test_can_instantiate_from_registry(self) -> None:
        """Test that component can be instantiated from registry."""
        component_class = component_registry.get("decorative.crown_molding")
        component = component_class()
        assert isinstance(component, CrownMoldingComponent)


# =============================================================================
# CrownMoldingComponent Validation Tests
# =============================================================================


class TestCrownMoldingValidation:
    """Tests for CrownMoldingComponent.validate()."""

    def test_validate_returns_ok_for_empty_config(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation passes for empty config."""
        config: dict = {}

        result = crown_molding_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_ok_for_valid_config(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation passes for valid crown molding config."""
        config = {"crown_molding": {"height": 4.0, "setback": 1.0, "nailer_width": 2.5}}

        result = crown_molding_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_invalid_setback(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation fails for setback exceeding depth."""
        config = {"crown_molding": {"height": 4.0, "setback": 15.0, "nailer_width": 2.5}}

        result = crown_molding_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("exceeds" in e for e in result.errors)


# =============================================================================
# CrownMoldingComponent Generation Tests
# =============================================================================


class TestCrownMoldingGeneration:
    """Tests for CrownMoldingComponent.generate()."""

    def test_generate_produces_one_panel(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate produces exactly 1 nailer panel."""
        config = {"crown_molding": {"height": 4.0, "setback": 1.0, "nailer_width": 2.5}}

        result = crown_molding_component.generate(config, standard_context)

        assert len(result.panels) == 1

    def test_generate_produces_nailer_panel(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate produces a NAILER panel."""
        config = {"crown_molding": {"height": 4.0, "setback": 1.0, "nailer_width": 2.5}}

        result = crown_molding_component.generate(config, standard_context)

        assert result.panels[0].panel_type == PanelType.NAILER

    def test_generate_includes_adjustments_in_metadata(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes adjustments."""
        config = {"crown_molding": {"height": 4.0, "setback": 1.0, "nailer_width": 2.5}}

        result = crown_molding_component.generate(config, standard_context)

        assert "adjustments" in result.metadata
        assert result.metadata["adjustments"]["top_panel_depth_reduction"] == 1.0


# =============================================================================
# CrownMoldingComponent Hardware Tests
# =============================================================================


class TestCrownMoldingHardware:
    """Tests for CrownMoldingComponent.hardware()."""

    def test_hardware_returns_empty_list(
        self, crown_molding_component: CrownMoldingComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns an empty list."""
        config = {"crown_molding": {"height": 4.0}}

        hardware = crown_molding_component.hardware(config, standard_context)

        assert len(hardware) == 0


# =============================================================================
# ToeKickComponent Registration Tests
# =============================================================================


class TestToeKickComponentRegistration:
    """Tests for ToeKickComponent registration in the registry."""

    def test_toe_kick_is_registered(self) -> None:
        """Test that decorative.toe_kick is registered."""
        assert "decorative.toe_kick" in component_registry.list()

    def test_get_returns_toe_kick_component_class(self) -> None:
        """Test that registry.get returns ToeKickComponent."""
        component_class = component_registry.get("decorative.toe_kick")
        assert component_class is ToeKickComponent


# =============================================================================
# ToeKickComponent Validation Tests
# =============================================================================


class TestToeKickValidation:
    """Tests for ToeKickComponent.validate()."""

    def test_validate_returns_ok_for_empty_config(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation passes for empty config."""
        config: dict = {}

        result = toe_kick_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_ok_for_valid_config(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation passes for valid toe kick config."""
        config = {"toe_kick": {"height": 3.5, "setback": 3.0}}

        result = toe_kick_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_warning_for_short_height(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test warning for toe kick height < 3\"."""
        config = {"toe_kick": {"height": 2.5, "setback": 3.0}}

        result = toe_kick_component.validate(config, standard_context)

        assert result.is_valid
        assert any("less than" in w for w in result.warnings)

    def test_validate_returns_warning_for_short_setback(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test warning for toe kick setback < 2\"."""
        config = {"toe_kick": {"height": 3.5, "setback": 1.5}}

        result = toe_kick_component.validate(config, standard_context)

        assert result.is_valid
        assert any("less than" in w for w in result.warnings)


# =============================================================================
# ToeKickComponent Generation Tests
# =============================================================================


class TestToeKickGeneration:
    """Tests for ToeKickComponent.generate()."""

    def test_generate_produces_one_panel(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate produces exactly 1 toe kick panel."""
        config = {"toe_kick": {"height": 3.5, "setback": 3.0}}

        result = toe_kick_component.generate(config, standard_context)

        assert len(result.panels) == 1

    def test_generate_produces_toe_kick_panel(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate produces a TOE_KICK panel."""
        config = {"toe_kick": {"height": 3.5, "setback": 3.0}}

        result = toe_kick_component.generate(config, standard_context)

        assert result.panels[0].panel_type == PanelType.TOE_KICK

    def test_generate_includes_adjustments_in_metadata(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes adjustments."""
        config = {"toe_kick": {"height": 3.5, "setback": 3.0}}

        result = toe_kick_component.generate(config, standard_context)

        assert "adjustments" in result.metadata
        assert result.metadata["adjustments"]["bottom_panel_raise"] == 3.5


# =============================================================================
# ToeKickComponent Hardware Tests
# =============================================================================


class TestToeKickHardware:
    """Tests for ToeKickComponent.hardware()."""

    def test_hardware_returns_empty_list(
        self, toe_kick_component: ToeKickComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns an empty list."""
        config = {"toe_kick": {"height": 3.5}}

        hardware = toe_kick_component.hardware(config, standard_context)

        assert len(hardware) == 0


# =============================================================================
# LightRailComponent Registration Tests
# =============================================================================


class TestLightRailComponentRegistration:
    """Tests for LightRailComponent registration in the registry."""

    def test_light_rail_is_registered(self) -> None:
        """Test that decorative.light_rail is registered."""
        assert "decorative.light_rail" in component_registry.list()

    def test_get_returns_light_rail_component_class(self) -> None:
        """Test that registry.get returns LightRailComponent."""
        component_class = component_registry.get("decorative.light_rail")
        assert component_class is LightRailComponent


# =============================================================================
# LightRailComponent Validation Tests
# =============================================================================


class TestLightRailValidation:
    """Tests for LightRailComponent.validate()."""

    def test_validate_returns_ok_for_empty_config(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test validation passes for empty config."""
        config: dict = {}

        result = light_rail_component.validate(config, wall_cabinet_context)

        assert result.is_valid

    def test_validate_returns_ok_for_valid_config(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test validation passes for valid light rail config."""
        config = {"light_rail": {"height": 1.5, "setback": 0.25, "generate_strip": True}}

        result = light_rail_component.validate(config, wall_cabinet_context)

        assert result.is_valid

    def test_validate_returns_warning_for_tall_height(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test warning for light rail height > 3\"."""
        config = {"light_rail": {"height": 4.0, "setback": 0.25, "generate_strip": True}}

        result = light_rail_component.validate(config, wall_cabinet_context)

        assert result.is_valid
        assert any("too tall" in w for w in result.warnings)


# =============================================================================
# LightRailComponent Generation Tests
# =============================================================================


class TestLightRailGeneration:
    """Tests for LightRailComponent.generate()."""

    def test_generate_produces_one_panel_when_strip_true(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test that generate produces exactly 1 panel when generate_strip=True."""
        config = {"light_rail": {"height": 1.5, "setback": 0.25, "generate_strip": True}}

        result = light_rail_component.generate(config, wall_cabinet_context)

        assert len(result.panels) == 1

    def test_generate_produces_no_panel_when_strip_false(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test that generate produces 0 panels when generate_strip=False."""
        config = {"light_rail": {"height": 1.5, "setback": 0.25, "generate_strip": False}}

        result = light_rail_component.generate(config, wall_cabinet_context)

        assert len(result.panels) == 0

    def test_generate_produces_light_rail_panel(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test that generate produces a LIGHT_RAIL panel."""
        config = {"light_rail": {"height": 1.5, "setback": 0.25, "generate_strip": True}}

        result = light_rail_component.generate(config, wall_cabinet_context)

        assert result.panels[0].panel_type == PanelType.LIGHT_RAIL


# =============================================================================
# LightRailComponent Hardware Tests
# =============================================================================


class TestLightRailHardware:
    """Tests for LightRailComponent.hardware()."""

    def test_hardware_returns_empty_list(
        self, light_rail_component: LightRailComponent, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test that hardware returns an empty list."""
        config = {"light_rail": {"height": 1.5}}

        hardware = light_rail_component.hardware(config, wall_cabinet_context)

        assert len(hardware) == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestMoldingZoneIntegration:
    """Integration tests for molding zone components."""

    def test_crown_molding_full_workflow(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for crown molding component."""
        component_class = component_registry.get("decorative.crown_molding")
        component = component_class()

        config = {
            "crown_molding": {
                "height": 4.0,
                "setback": 1.0,
                "nailer_width": 2.5,
            }
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1
        assert generation.panels[0].panel_type == PanelType.NAILER
        assert generation.panels[0].metadata["zone_type"] == "crown_molding"

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_toe_kick_full_workflow(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for toe kick component."""
        component_class = component_registry.get("decorative.toe_kick")
        component = component_class()

        config = {
            "toe_kick": {
                "height": 4.0,
                "setback": 3.0,
            }
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1
        assert generation.panels[0].panel_type == PanelType.TOE_KICK
        assert generation.panels[0].metadata["zone_type"] == "toe_kick"

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_light_rail_full_workflow(
        self, wall_cabinet_context: ComponentContext
    ) -> None:
        """Test complete workflow for light rail component."""
        component_class = component_registry.get("decorative.light_rail")
        component = component_class()

        config = {
            "light_rail": {
                "height": 1.5,
                "setback": 0.25,
                "generate_strip": True,
            }
        }

        # Validate
        validation = component.validate(config, wall_cabinet_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, wall_cabinet_context)
        assert len(generation.panels) == 1
        assert generation.panels[0].panel_type == PanelType.LIGHT_RAIL
        assert generation.panels[0].metadata["zone_type"] == "light_rail"

        # Hardware
        hardware = component.hardware(config, wall_cabinet_context)
        assert len(hardware) == 0


# =============================================================================
# Task Spec Success Criteria Tests
# =============================================================================


class TestTaskSpecSuccessCriteria:
    """Tests matching the success criteria from the task specification."""

    def test_crown_nailer_generated(self) -> None:
        """Success Criteria 1: Crown Nailer Generated."""
        service = MoldingZoneService()
        config = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        nailer = service.generate_crown_nailer(
            config, 48.0, 84.0, 12.0, material, position
        )

        assert nailer.panel_type == PanelType.NAILER
        assert nailer.metadata["zone_type"] == "crown_molding"

    def test_toe_kick_panel_generated(self) -> None:
        """Success Criteria 2: Toe Kick Panel Generated."""
        service = MoldingZoneService()
        config = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        panel = service.generate_toe_kick_panel(config, 48.0, material, position)

        assert panel.panel_type == PanelType.TOE_KICK

    def test_light_rail_strip_generated(self) -> None:
        """Success Criteria 3: Light Rail Strip Generated."""
        service = MoldingZoneService()
        config = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        material = MaterialSpec.standard_3_4()
        position = Position(0, 0)

        panel = service.generate_light_rail_strip(config, 48.0, material, position)

        assert panel.panel_type == PanelType.LIGHT_RAIL

    def test_dimension_adjustments_calculated(self) -> None:
        """Success Criteria 4: Dimension Adjustments Calculated."""
        service = MoldingZoneService()
        crown = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        base = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")

        adjustments = service.get_dimension_adjustments(crown, base, 12.0)

        assert adjustments["top_panel_depth_reduction"] == crown.setback
        assert adjustments["bottom_panel_raise"] == base.height

    def test_validation_zone_height_exceeds_cabinet(self) -> None:
        """Success Criteria 5: Zone height exceeding cabinet fails."""
        service = MoldingZoneService()
        crown = CrownMoldingZone(height=50.0, setback=1.0, nailer_width=2.5)
        base = BaseZone(height=40.0, setback=3.0, zone_type="toe_kick")

        errors, warnings = service.validate_zones(
            crown=crown,
            base=base,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert len(errors) > 0

    def test_validation_toe_kick_short_warning(self) -> None:
        """Success Criteria 5: Toe kick < 3\" generates warning (FR-06)."""
        service = MoldingZoneService()
        base = BaseZone(height=2.5, setback=3.0, zone_type="toe_kick")

        errors, warnings = service.validate_zones(
            crown=None,
            base=base,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert any("less than" in w and "3\"" in w for w in warnings)

    def test_validation_crown_setback_exceeds_depth(self) -> None:
        """Success Criteria 5: Crown setback > depth fails."""
        service = MoldingZoneService()
        crown = CrownMoldingZone(height=4.0, setback=15.0, nailer_width=2.5)

        errors, warnings = service.validate_zones(
            crown=crown,
            base=None,
            light_rail=None,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert len(errors) > 0
        assert any("exceeds" in e for e in errors)


# =============================================================================
# Manual Verification Test (from task spec)
# =============================================================================


class TestManualVerification:
    """Manual verification test from task specification."""

    def test_task_spec_example(self) -> None:
        """Test the example from the task specification."""
        service = MoldingZoneService()
        material = MaterialSpec(thickness=0.75)
        position = Position(0, 0)

        # Test crown molding zone
        crown = CrownMoldingZone(height=4.0, setback=1.0, nailer_width=2.5)
        nailer = service.generate_crown_nailer(crown, 48, 84, 12, material, position)
        assert nailer.panel_type.value == "nailer"
        assert nailer.width == pytest.approx(48.0)
        assert nailer.height == pytest.approx(2.5)

        # Test toe kick zone
        base = BaseZone(height=4.0, setback=3.0, zone_type="toe_kick")
        toe_kick = service.generate_toe_kick_panel(base, 48, material, position)
        assert toe_kick.panel_type.value == "toe_kick"
        assert toe_kick.width == pytest.approx(48.0)
        assert toe_kick.height == pytest.approx(4.0)

        # Test light rail zone
        light_rail = LightRailZone(height=1.5, setback=0.25, generate_strip=True)
        rail = service.generate_light_rail_strip(light_rail, 48, material, position)
        assert rail.panel_type.value == "light_rail"
        assert rail.width == pytest.approx(48.0)
        assert rail.height == pytest.approx(1.5)

        # Test validation
        errors, warnings = service.validate_zones(crown, base, light_rail, 84, 12)
        assert len(errors) == 0  # No errors for valid config

        # Test dimension adjustments
        adjustments = service.get_dimension_adjustments(crown, base, 12.0)
        assert adjustments["top_panel_depth_reduction"] == pytest.approx(1.0)
        assert adjustments["bottom_panel_raise"] == pytest.approx(4.0)

        # Test all panels together
        panels = service.generate_all_zone_panels(
            crown, base, light_rail, 48, 84, 12, material, position
        )
        assert len(panels) == 3

        # Verify panel types
        panel_types = [p.panel_type.value for p in panels]
        assert "nailer" in panel_types
        assert "toe_kick" in panel_types
        assert "light_rail" in panel_types
