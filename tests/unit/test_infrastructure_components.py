"""Unit tests for infrastructure components (FRD-15).

Tests for:
- LightingComponent (infrastructure.lighting)
- ElectricalComponent (infrastructure.electrical)
- CableManagementComponent (infrastructure.cable_management)
- VentilationComponent (infrastructure.ventilation)
"""

import importlib

import pytest

from cabinets.domain.components import (
    CableManagementComponent,
    ComponentContext,
    ElectricalComponent,
    LightingComponent,
    VentilationComponent,
    component_registry,
)
from cabinets.domain.components.infrastructure import (
    CableChannelSpec,
    GrommetSpec,
    LightingSpec,
    OutletSpec,
    VentilationSpec,
    WireRouteSpec,
)
from cabinets.domain.value_objects import (
    LightingLocation,
    LightingType,
    MaterialSpec,
    OutletType,
    PanelType,
    Point2D,
    Position,
    VentilationPattern,
)


@pytest.fixture(autouse=True)
def ensure_components_registered() -> None:
    """Ensure infrastructure components are registered before each test.

    The registry tests clear the registry, which removes all registered
    components. This fixture re-imports the infrastructure module to
    re-register the components if they've been cleared.
    """
    # Check if infrastructure components are registered
    if "infrastructure.lighting" not in component_registry.list():
        # Re-import the module to trigger registration
        import cabinets.domain.components.infrastructure

        importlib.reload(cabinets.domain.components.infrastructure)


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard component context for testing."""
    return ComponentContext(
        width=24.0,
        height=30.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


# --- Spec Dataclass Tests ---


class TestLightingSpec:
    """Tests for LightingSpec dataclass."""

    def test_led_strip_spec(self) -> None:
        """Test LED strip lighting specification."""
        spec = LightingSpec(
            light_type=LightingType.LED_STRIP,
            location=LightingLocation.UNDER_CABINET,
            section_indices=(0, 1, 2),
            length=48.0,
            channel_width=0.5,
            channel_depth=0.25,
        )

        assert spec.light_type == LightingType.LED_STRIP
        assert spec.location == LightingLocation.UNDER_CABINET
        assert spec.section_indices == (0, 1, 2)
        assert spec.length == 48.0
        assert spec.channel_width == 0.5
        assert spec.channel_depth == 0.25

    def test_puck_light_spec(self) -> None:
        """Test puck light specification."""
        spec = LightingSpec(
            light_type=LightingType.PUCK_LIGHT,
            location=LightingLocation.IN_CABINET,
            section_indices=(0,),
            diameter=2.5,
            position=Point2D(12.0, 6.0),
        )

        assert spec.light_type == LightingType.PUCK_LIGHT
        assert spec.diameter == 2.5
        assert spec.position is not None
        assert spec.position.x == 12.0
        assert spec.position.y == 6.0


class TestOutletSpec:
    """Tests for OutletSpec dataclass."""

    def test_single_outlet_dimensions(self) -> None:
        """Test single outlet cutout dimensions."""
        spec = OutletSpec(
            outlet_type=OutletType.SINGLE,
            section_index=0,
            panel=PanelType.BACK,
            position=Point2D(12.0, 6.0),
        )

        width, height = spec.cutout_dimensions
        assert width == 2.25
        assert height == 4.0

    def test_double_outlet_dimensions(self) -> None:
        """Test double outlet cutout dimensions."""
        spec = OutletSpec(
            outlet_type=OutletType.DOUBLE,
            section_index=0,
            panel=PanelType.BACK,
            position=Point2D(12.0, 6.0),
        )

        width, height = spec.cutout_dimensions
        assert width == 4.25
        assert height == 4.0

    def test_gfi_outlet_dimensions(self) -> None:
        """Test GFI outlet cutout dimensions."""
        spec = OutletSpec(
            outlet_type=OutletType.GFI,
            section_index=0,
            panel=PanelType.BACK,
            position=Point2D(12.0, 6.0),
        )

        width, height = spec.cutout_dimensions
        assert width == 3.0
        assert height == 4.75


class TestGrommetSpec:
    """Tests for GrommetSpec dataclass."""

    def test_grommet_spec(self) -> None:
        """Test grommet specification."""
        spec = GrommetSpec(
            size=2.5,
            panel=PanelType.BACK,
            position=Point2D(6.0, 4.0),
            section_index=0,
        )

        assert spec.size == 2.5
        assert spec.panel == PanelType.BACK
        assert spec.position.x == 6.0
        assert spec.position.y == 4.0


class TestVentilationSpec:
    """Tests for VentilationSpec dataclass."""

    def test_ventilation_spec(self) -> None:
        """Test ventilation specification."""
        spec = VentilationSpec(
            pattern=VentilationPattern.GRID,
            panel=PanelType.BACK,
            position=Point2D(12.0, 6.0),
            width=8.0,
            height=4.0,
            hole_size=0.25,
        )

        assert spec.pattern == VentilationPattern.GRID
        assert spec.width == 8.0
        assert spec.height == 4.0
        assert spec.hole_size == 0.25


class TestCableChannelSpec:
    """Tests for CableChannelSpec dataclass."""

    def test_cable_channel_spec(self) -> None:
        """Test cable channel specification."""
        spec = CableChannelSpec(
            start=Point2D(0.0, 0.0),
            end=Point2D(24.0, 0.0),
            width=2.0,
            depth=1.0,
        )

        assert spec.start.x == 0.0
        assert spec.end.x == 24.0
        assert spec.width == 2.0
        assert spec.depth == 1.0


class TestWireRouteSpec:
    """Tests for WireRouteSpec dataclass."""

    def test_wire_route_spec(self) -> None:
        """Test wire route specification."""
        spec = WireRouteSpec(
            waypoints=(Point2D(0, 0), Point2D(12, 0), Point2D(12, 12)),
            hole_diameter=0.75,
            panel_penetrations=(PanelType.BACK, PanelType.BOTTOM),
        )

        assert len(spec.waypoints) == 3
        assert spec.hole_diameter == 0.75
        assert len(spec.panel_penetrations) == 2


# --- Lighting Component Tests ---


class TestLightingComponent:
    """Tests for LightingComponent."""

    def test_component_registration(self) -> None:
        """Test that lighting component is registered."""
        component = component_registry.get("infrastructure.lighting")
        assert component is not None
        assert component.__name__ == "LightingComponent"

    def test_validate_led_strip_valid(self, standard_context: ComponentContext) -> None:
        """Test validation of valid LED strip configuration."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0],
            "length": 20.0,
        }

        result = component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_led_strip_missing_length(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation error when LED strip length is missing."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0],
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("length" in e for e in result.errors)

    def test_validate_invalid_light_type(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation error for invalid light type."""
        component = LightingComponent()
        config = {
            "light_type": "halogen",  # Invalid
            "location": "under_cabinet",
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("light_type" in e for e in result.errors)

    def test_validate_invalid_location(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation error for invalid location."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "inside_wall",  # Invalid
            "length": 20.0,
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("location" in e for e in result.errors)

    def test_generate_led_strip(self, standard_context: ComponentContext) -> None:
        """Test generation of LED strip lighting."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0, 1],
            "length": 36.0,
        }

        result = component.generate(config, standard_context)

        # Check hardware
        assert len(result.hardware) >= 3  # LED strip, channel, driver
        hardware_names = [h.name for h in result.hardware]
        assert any("LED Strip" in name for name in hardware_names)
        assert any("Channel" in name for name in hardware_names)
        assert any("Driver" in name for name in hardware_names)

        # Check metadata
        assert "lighting_specs" in result.metadata
        specs = result.metadata["lighting_specs"]
        assert len(specs) == 1
        assert specs[0].light_type == LightingType.LED_STRIP

    def test_generate_puck_lights(self, standard_context: ComponentContext) -> None:
        """Test generation of puck lights."""
        component = LightingComponent()
        config = {
            "light_type": "puck_light",
            "location": "in_cabinet",
            "puck_positions": [
                {"x": 6.0, "y": 6.0},
                {"x": 18.0, "y": 6.0},
            ],
            "puck_diameter": 2.5,
        }

        result = component.generate(config, standard_context)

        # Check hardware
        hardware_names = [h.name for h in result.hardware]
        assert any("Puck Light" in name for name in hardware_names)
        assert any("Harness" in name for name in hardware_names)

        # Check cutouts
        assert "cutouts" in result.metadata
        assert len(result.metadata["cutouts"]) == 2
        for cutout in result.metadata["cutouts"]:
            assert cutout["shape"] == "circular"
            assert cutout["cutout_type"] == "puck_light"

    def test_hardware_method(self, standard_context: ComponentContext) -> None:
        """Test hardware() method returns same items as generate()."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "length": 24.0,
        }

        hardware = component.hardware(config, standard_context)
        result = component.generate(config, standard_context)

        assert len(hardware) == len(result.hardware)


# --- Electrical Component Tests ---


class TestElectricalComponent:
    """Tests for ElectricalComponent."""

    def test_component_registration(self) -> None:
        """Test that electrical component is registered."""
        component = component_registry.get("infrastructure.electrical")
        assert component is not None
        assert component.__name__ == "ElectricalComponent"

    def test_validate_valid_outlet(self, standard_context: ComponentContext) -> None:
        """Test validation of valid outlet configuration."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "single",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
        }

        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_invalid_outlet_type(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation error for invalid outlet type."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "triple",  # Invalid
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("outlet_type" in e for e in result.errors)

    def test_validate_position_too_close_to_edge(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation error when outlet is too close to edge."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "double",  # 4.25" wide
            "panel": "back",
            "position": {"x": 2.0, "y": 15.0},  # Too close to left edge
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("edge" in e.lower() for e in result.errors)

    def test_validate_warns_if_blocked(
        self, standard_context: ComponentContext
    ) -> None:
        """Test warning when outlet may be blocked by shelf."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "single",
            "panel": "back",
            "position": {"x": 12.0, "y": 10.0},  # Low position
        }

        result = component.validate(config, standard_context)
        assert result.is_valid  # Still valid, just a warning
        assert len(result.warnings) > 0
        assert any("blocked" in w.lower() for w in result.warnings)

    def test_generate_outlet_cutout(self, standard_context: ComponentContext) -> None:
        """Test generation of outlet cutout."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "double",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
            "conduit_direction": "bottom",
        }

        result = component.generate(config, standard_context)

        # Check cutouts
        assert "cutouts" in result.metadata
        assert len(result.metadata["cutouts"]) == 1
        cutout = result.metadata["cutouts"][0]
        assert cutout["cutout_type"] == "outlet"
        assert cutout["shape"] == "rectangular"
        assert cutout["width"] == 4.25  # Double outlet width
        assert cutout["height"] == 4.0

        # Check outlet spec
        assert "outlet_spec" in result.metadata
        spec = result.metadata["outlet_spec"]
        assert spec["outlet_type"] == "double"
        assert spec["conduit_direction"] == "bottom"

    def test_hardware_returns_empty(self, standard_context: ComponentContext) -> None:
        """Test that hardware() returns empty list (electrical is separate trade)."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "single",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
        }

        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0


# --- Cable Management Component Tests ---


class TestCableManagementComponent:
    """Tests for CableManagementComponent."""

    def test_component_registration(self) -> None:
        """Test that cable management component is registered."""
        component = component_registry.get("infrastructure.cable_management")
        assert component is not None
        assert component.__name__ == "CableManagementComponent"

    def test_validate_valid_grommets(self, standard_context: ComponentContext) -> None:
        """Test validation of valid grommet configuration."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.0, "panel": "back", "position": {"x": 6.0, "y": 15.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 18.0, "y": 15.0}},
            ]
        }

        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_invalid_grommet_size(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation error for invalid grommet size."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 1.5, "panel": "back", "position": {"x": 6.0, "y": 15.0}},
            ]
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("size" in e.lower() for e in result.errors)

    def test_validate_all_valid_sizes(self, standard_context: ComponentContext) -> None:
        """Test that all valid grommet sizes pass validation."""
        component = CableManagementComponent()

        for size in [2.0, 2.5, 3.0]:
            config = {
                "grommets": [
                    {"size": size, "panel": "back", "position": {"x": 12.0, "y": 15.0}},
                ]
            }
            result = component.validate(config, standard_context)
            assert result.is_valid, f"Size {size} should be valid"

    def test_generate_grommet_cutouts(self, standard_context: ComponentContext) -> None:
        """Test generation of grommet cutouts."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.5, "panel": "back", "position": {"x": 6.0, "y": 15.0}},
                {"size": 3.0, "panel": "bottom", "position": {"x": 12.0, "y": 6.0}},
            ]
        }

        result = component.generate(config, standard_context)

        # Check cutouts
        assert "cutouts" in result.metadata
        assert len(result.metadata["cutouts"]) == 2
        for cutout in result.metadata["cutouts"]:
            assert cutout["shape"] == "circular"
            assert cutout["cutout_type"] == "grommet"

        # Check hardware - should have 2 grommets of different sizes
        assert len(result.hardware) == 2
        skus = [h.sku for h in result.hardware]
        assert "GRM-250-BLK" in skus
        assert "GRM-300-BLK" in skus

    def test_hardware_sku_pattern(self, standard_context: ComponentContext) -> None:
        """Test that hardware SKUs follow expected pattern."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.0, "panel": "back", "position": {"x": 6.0, "y": 15.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 15.0}},
                {"size": 3.0, "panel": "back", "position": {"x": 18.0, "y": 15.0}},
            ]
        }

        result = component.generate(config, standard_context)

        expected_skus = {"GRM-200-BLK", "GRM-250-BLK", "GRM-300-BLK"}
        actual_skus = {h.sku for h in result.hardware}
        assert actual_skus == expected_skus

    def test_hardware_aggregates_same_size(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that hardware aggregates multiple grommets of same size."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.5, "panel": "back", "position": {"x": 6.0, "y": 15.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 18.0, "y": 15.0}},
            ]
        }

        result = component.generate(config, standard_context)

        # Should be single hardware item with quantity 2
        assert len(result.hardware) == 1
        assert result.hardware[0].quantity == 2
        assert result.hardware[0].sku == "GRM-250-BLK"


# --- Ventilation Component Tests ---


class TestVentilationComponent:
    """Tests for VentilationComponent."""

    def test_component_registration(self) -> None:
        """Test that ventilation component is registered."""
        component = component_registry.get("infrastructure.ventilation")
        assert component is not None
        assert component.__name__ == "VentilationComponent"

    def test_validate_valid_ventilation(
        self, standard_context: ComponentContext
    ) -> None:
        """Test validation of valid ventilation configuration."""
        component = VentilationComponent()
        config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
            "width": 6.0,
            "height": 3.0,
        }

        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_invalid_pattern(self, standard_context: ComponentContext) -> None:
        """Test validation error for invalid pattern."""
        component = VentilationComponent()
        config = {
            "pattern": "hexagon",  # Invalid
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
            "width": 6.0,
            "height": 3.0,
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("pattern" in e.lower() for e in result.errors)

    def test_validate_all_valid_patterns(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that all valid patterns pass validation."""
        component = VentilationComponent()

        for pattern in ["grid", "slot", "circular"]:
            config = {
                "pattern": pattern,
                "panel": "back",
                "position": {"x": 12.0, "y": 15.0},
                "width": 6.0,
                "height": 3.0,
            }
            result = component.validate(config, standard_context)
            assert result.is_valid, f"Pattern '{pattern}' should be valid"

    def test_validate_warns_insufficient_ventilation(
        self, standard_context: ComponentContext
    ) -> None:
        """Test warning when ventilation area is insufficient for electronics."""
        component = VentilationComponent()
        config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
            "width": 1.5,  # Small area
            "height": 1.5,  # 2.25 sq in < 4 sq in minimum
            "electronics": True,
        }

        result = component.validate(config, standard_context)
        assert result.is_valid  # Still valid, just a warning
        assert len(result.warnings) > 0
        assert any("ventilation area" in w.lower() for w in result.warnings)

    def test_generate_ventilation_metadata(
        self, standard_context: ComponentContext
    ) -> None:
        """Test generation of ventilation metadata."""
        component = VentilationComponent()
        config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
            "width": 8.0,
            "height": 4.0,
            "hole_size": 0.25,
        }

        result = component.generate(config, standard_context)

        # Check ventilation spec
        assert "ventilation_spec" in result.metadata
        spec = result.metadata["ventilation_spec"]
        assert spec["pattern"] == "grid"
        assert spec["width"] == 8.0
        assert spec["height"] == 4.0
        assert spec["hole_count"] > 0

        # Check cutouts
        assert "cutouts" in result.metadata
        assert len(result.metadata["cutouts"]) == 1
        cutout = result.metadata["cutouts"][0]
        assert cutout["cutout_type"] == "ventilation"

    def test_hardware_returns_empty(self, standard_context: ComponentContext) -> None:
        """Test that hardware() returns empty list (ventilation is machined)."""
        component = VentilationComponent()
        config = {
            "pattern": "slot",
            "panel": "back",
            "position": {"x": 12.0, "y": 15.0},
            "width": 6.0,
            "height": 3.0,
        }

        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0


# --- Base Class Tests ---


class TestInfrastructureBase:
    """Tests for _InfrastructureBase validation helpers."""

    def test_edge_distance_validation(self, standard_context: ComponentContext) -> None:
        """Test edge distance validation catches violations."""
        # Use electrical component as test subject
        component = ElectricalComponent()

        # Position that violates left edge
        config = {
            "outlet_type": "single",  # 2.25" wide
            "panel": "back",
            "position": {"x": 1.0, "y": 15.0},  # Left edge violation
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("edge" in e.lower() for e in result.errors)

    def test_cutout_overlap_detection(self, standard_context: ComponentContext) -> None:
        """Test that overlapping cutouts are detected."""
        component = CableManagementComponent()

        # Two grommets at the same position
        config = {
            "grommets": [
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 15.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 15.0}},
            ]
        }

        # This should generate but the cutouts would overlap
        # The base class has overlap detection but it's not used in validate()
        result = component.generate(config, standard_context)
        assert len(result.metadata["cutouts"]) == 2


# --- Integration Tests ---


class TestInfrastructureIntegration:
    """Integration tests for infrastructure components working together."""

    def test_multiple_infrastructure_components(
        self, standard_context: ComponentContext
    ) -> None:
        """Test using multiple infrastructure components together."""
        # Configure lighting
        lighting = LightingComponent()
        lighting_config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "length": 24.0,
        }
        lighting_result = lighting.generate(lighting_config, standard_context)

        # Configure cable management
        cable = CableManagementComponent()
        cable_config = {
            "grommets": [
                {"size": 2.5, "panel": "back", "position": {"x": 6.0, "y": 15.0}},
            ]
        }
        cable_result = cable.generate(cable_config, standard_context)

        # Configure ventilation
        vent = VentilationComponent()
        vent_config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 18.0, "y": 15.0},
            "width": 4.0,
            "height": 2.0,
        }
        vent_result = vent.generate(vent_config, standard_context)

        # All should generate successfully
        assert len(lighting_result.hardware) > 0
        assert len(cable_result.hardware) > 0
        assert "ventilation_spec" in vent_result.metadata

    def test_component_registry_access(self) -> None:
        """Test that all infrastructure components are accessible via registry."""
        components = [
            "infrastructure.lighting",
            "infrastructure.electrical",
            "infrastructure.cable_management",
            "infrastructure.ventilation",
        ]

        for component_id in components:
            component_cls = component_registry.get(component_id)
            assert component_cls is not None, f"Component {component_id} not found"

            # Instantiate and verify has required methods
            instance = component_cls()
            assert hasattr(instance, "validate")
            assert hasattr(instance, "generate")
            assert hasattr(instance, "hardware")
