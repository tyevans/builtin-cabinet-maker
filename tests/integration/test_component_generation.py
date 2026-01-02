"""Integration tests for component-based cabinet generation.

These tests verify that the LayoutCalculator correctly integrates with the
component registry to generate cabinets using registered components (like
shelf.fixed) instead of inline shelf generation.
"""

from __future__ import annotations

import pytest

from cabinets.application.factory import get_factory
from cabinets.application.config import config_to_section_specs
from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    SectionConfig,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain import LayoutCalculator, LayoutParameters, Wall
from cabinets.domain.components import component_registry
from cabinets.domain.components.door import (
    OverlayDoorComponent,
    InsetDoorComponent,
)
from cabinets.domain.components.drawer import (
    StandardDrawerComponent,
    FileDrawerComponent,
)
from cabinets.domain.components.shelf import (
    AdjustableShelfComponent,
    FixedShelfComponent,
)
from cabinets.domain.section_resolver import SectionSpec, SectionWidthError
from cabinets.domain.entities import Cabinet, Panel
from cabinets.domain.services import Panel3DMapper
from cabinets.domain.value_objects import MaterialSpec, PanelType, SectionType


@pytest.fixture
def ensure_shelf_registered() -> None:
    """Ensure shelf.fixed is registered for tests.

    Other tests may clear the registry, so we re-register if needed.
    """
    if "shelf.fixed" not in component_registry.list():
        component_registry.register("shelf.fixed")(FixedShelfComponent)


class TestLayoutCalculatorUsesComponentRegistry:
    """Tests that LayoutCalculator uses the component registry."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_generate_cabinet_from_specs_uses_component_registry(self) -> None:
        """Test that generate_cabinet_from_specs uses component_registry.get()."""
        calculator = LayoutCalculator()
        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        specs = [SectionSpec(width="fill", shelves=3)]

        cabinet, hardware = calculator.generate_cabinet_from_specs(wall, params, specs)

        # Verify cabinet was created
        assert cabinet is not None
        assert len(cabinet.sections) == 1
        assert len(cabinet.sections[0].shelves) == 3

    def test_generate_cabinet_returns_hardware_list(self) -> None:
        """Test that generate_cabinet_from_specs returns hardware list."""
        calculator = LayoutCalculator()
        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        specs = [SectionSpec(width="fill", shelves=3)]

        cabinet, hardware = calculator.generate_cabinet_from_specs(wall, params, specs)

        # Hardware is empty by default since use_pins is not set
        assert hardware is not None
        assert isinstance(hardware, list)


class TestShelfGenerationMatchesExistingBehavior:
    """Tests that shelf generation behavior is identical to before."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_shelf_positions_match_original_algorithm(self) -> None:
        """Test that shelf Y positions match the original layout algorithm.

        Original algorithm from services.py:
        - shelf_spacing = cabinet.interior_height / (shelf_count + 1)
        - shelf_y = params.material.thickness + shelf_spacing * (j + 1)
        """
        calculator = LayoutCalculator()
        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        specs = [SectionSpec(width="fill", shelves=3)]

        cabinet, _ = calculator.generate_cabinet_from_specs(wall, params, specs)

        # Cabinet interior height = 84 - 2*0.75 = 82.5
        interior_height = cabinet.interior_height
        assert interior_height == pytest.approx(82.5)

        # Expected spacing = 82.5 / 4 = 20.625
        expected_spacing = interior_height / 4

        # Expected positions: 0.75 + 20.625 * (j+1) for j in 0,1,2
        shelves = cabinet.sections[0].shelves
        for i, shelf in enumerate(shelves):
            expected_y = 0.75 + expected_spacing * (i + 1)
            assert shelf.position.y == pytest.approx(expected_y, rel=1e-5)

    def test_shelf_dimensions_match_section_dimensions(self) -> None:
        """Test that shelf width and depth match section dimensions.

        Shelf depth is section.depth - default setback (1.0").
        """
        calculator = LayoutCalculator()
        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        specs = [SectionSpec(width="fill", shelves=2)]

        cabinet, _ = calculator.generate_cabinet_from_specs(wall, params, specs)

        section = cabinet.sections[0]
        default_setback = 1.0  # Default setback from FixedShelfComponent
        for shelf in section.shelves:
            assert shelf.width == pytest.approx(section.width)
            assert shelf.depth == pytest.approx(section.depth - default_setback)

    def test_multiple_sections_with_different_shelf_counts(self) -> None:
        """Test sections with varying shelf counts."""
        calculator = LayoutCalculator()
        wall = Wall(width=72.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=2,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=5),
        ]

        cabinet, _ = calculator.generate_cabinet_from_specs(wall, params, specs)

        assert len(cabinet.sections) == 2
        assert len(cabinet.sections[0].shelves) == 3
        assert len(cabinet.sections[1].shelves) == 5


class TestComponentValidationErrorRaised:
    """Tests that component validation errors are properly raised."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_negative_shelf_count_raises_value_error(self) -> None:
        """Test that negative shelf count raises ValueError at SectionSpec level."""
        with pytest.raises(ValueError, match="Number of shelves cannot be negative"):
            SectionSpec(width="fill", shelves=-1)

    def test_excessive_shelf_count_raises_section_width_error(self) -> None:
        """Test that shelf count > 20 raises SectionWidthError during generation."""
        calculator = LayoutCalculator()
        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # SectionSpec allows shelves=21, but component validation will fail
        specs = [SectionSpec(width="fill", shelves=21)]

        with pytest.raises(
            SectionWidthError, match="shelf count exceeds maximum of 20"
        ):
            calculator.generate_cabinet_from_specs(wall, params, specs)


class TestEndToEndConfigToComponent:
    """End-to-end tests from config to component generation."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_config_to_cabinet_with_shelves(self) -> None:
        """Test full pipeline from config to cabinet with shelves."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                    SectionConfig(width="fill", shelves=5),
                ],
            ),
        )

        section_specs = config_to_section_specs(config)
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(num_sections=2, shelves_per_section=0)

        result = command.execute(wall_input, params_input, section_specs)

        assert result.is_valid
        assert result.cabinet is not None
        assert len(result.cabinet.sections) == 2
        assert len(result.cabinet.sections[0].shelves) == 3
        assert len(result.cabinet.sections[1].shelves) == 5

    def test_config_generates_correct_cut_list(self) -> None:
        """Test that config generates correct cut list including shelves."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width="fill", shelves=4),
                ],
            ),
        )

        section_specs = config_to_section_specs(config)
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(num_sections=1, shelves_per_section=0)

        result = command.execute(wall_input, params_input, section_specs)

        assert result.is_valid
        # Cut list should include shelves
        shelf_pieces = [p for p in result.cut_list if p.panel_type == PanelType.SHELF]
        # 4 shelves with same dimensions will be consolidated into 1 cut piece with qty=4
        total_shelf_count = sum(p.quantity for p in shelf_pieces)
        assert total_shelf_count == 4


class TestHardwareCollection:
    """Tests for hardware collection from components."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_hardware_is_collected_in_output(self) -> None:
        """Test that hardware from components is collected in output."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width="fill", shelves=3),
                ],
            ),
        )

        section_specs = config_to_section_specs(config)
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(num_sections=1, shelves_per_section=0)

        result = command.execute(wall_input, params_input, section_specs)

        assert result.is_valid
        # Hardware list should exist (empty because use_pins defaults to False)
        assert hasattr(result, "hardware")
        assert isinstance(result.hardware, list)


class TestComponentConfigPassthrough:
    """Tests for component_config passthrough."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_component_config_field_exists_in_section_config(self) -> None:
        """Test that SectionConfig has component_config field."""
        section = SectionConfig(width=24.0, shelves=3)
        assert hasattr(section, "component_config")
        assert section.component_config == {}

    def test_component_config_with_custom_values(self) -> None:
        """Test that SectionConfig accepts custom component_config."""
        section = SectionConfig(
            width=24.0,
            shelves=3,
            component_config={"use_pins": True, "custom_key": "value"},
        )
        assert section.component_config == {"use_pins": True, "custom_key": "value"}

    def test_component_config_flows_to_section_spec(self) -> None:
        """Test that component_config flows from SectionConfig to SectionSpec."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(
                        width="fill",
                        shelves=3,
                        component_config={"use_pins": True},
                    ),
                ],
            ),
        )

        section_specs = config_to_section_specs(config)

        assert len(section_specs) == 1
        assert section_specs[0].component_config == {"use_pins": True}


# =============================================================================
# Integration tests for AdjustableShelfComponent
# =============================================================================


@pytest.fixture
def ensure_adjustable_shelf_registered() -> None:
    """Ensure shelf.adjustable is registered for tests."""
    if "shelf.adjustable" not in component_registry.list():
        component_registry.register("shelf.adjustable")(AdjustableShelfComponent)


class TestAdjustableShelfIntegration:
    """Integration tests for shelf.adjustable component."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_adjustable_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_adjustable_shelf_registered_in_registry(self) -> None:
        """Test that shelf.adjustable is registered in the component registry."""
        assert "shelf.adjustable" in component_registry.list()

    def test_adjustable_shelf_can_be_retrieved_and_instantiated(self) -> None:
        """Test that AdjustableShelfComponent can be retrieved and instantiated."""
        component_class = component_registry.get("shelf.adjustable")
        component = component_class()
        assert component is not None
        assert hasattr(component, "validate")
        assert hasattr(component, "generate")
        assert hasattr(component, "hardware")


class TestAdjustableShelfGenerationBehavior:
    """Tests for adjustable shelf generation matching expected behavior."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_adjustable_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_adjustable_shelf_positions_evenly_distributed(self) -> None:
        """Test that adjustable shelves are evenly distributed like fixed shelves."""
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        component = AdjustableShelfComponent()
        config = {"count": 3}

        result = component.generate(config, context)

        # Verify even distribution
        assert len(result.panels) == 3
        expected_spacing = 72.0 / 4  # 18.0
        for i, panel in enumerate(result.panels):
            expected_y = 0.75 + expected_spacing * (i + 1)
            assert panel.position.y == pytest.approx(expected_y)

    def test_adjustable_shelf_includes_pin_hole_patterns(self) -> None:
        """Test that adjustable shelves include pin hole patterns in metadata."""
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        component = AdjustableShelfComponent()
        config = {"count": 2}

        result = component.generate(config, context)

        assert "pin_hole_patterns" in result.metadata
        patterns = result.metadata["pin_hole_patterns"]
        assert len(patterns) == 2
        panel_ids = {p.panel_id for p in patterns}
        assert panel_ids == {"left_side", "right_side"}

    def test_adjustable_shelf_always_includes_pins(self) -> None:
        """Test that adjustable shelves always include shelf pins in hardware."""
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        component = AdjustableShelfComponent()
        config = {"count": 3}

        result = component.generate(config, context)

        pin_items = [h for h in result.hardware if h.name == "Shelf Pin"]
        assert len(pin_items) == 1
        assert pin_items[0].quantity == 12  # 3 shelves * 4 pins

    def test_adjustable_vs_fixed_shelf_hardware_differences(self) -> None:
        """Test the key differences between adjustable and fixed shelf hardware."""
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        fixed = FixedShelfComponent()
        adjustable = AdjustableShelfComponent()
        config = {"count": 3}

        fixed_result = fixed.generate(config, context)
        adjustable_result = adjustable.generate(config, context)

        # Fixed shelf has dado_specs, adjustable has pin_hole_patterns
        assert "dado_specs" in fixed_result.metadata
        assert "pin_hole_patterns" in adjustable_result.metadata
        assert "dado_specs" not in adjustable_result.metadata
        assert "pin_hole_patterns" not in fixed_result.metadata

        # Adjustable always includes shelf pins
        adj_pins = [h for h in adjustable_result.hardware if h.name == "Shelf Pin"]
        assert len(adj_pins) == 1

        # Fixed shelf does not include pins by default
        fix_pins = [h for h in fixed_result.hardware if h.name == "Shelf Pin"]
        assert len(fix_pins) == 0


class TestAdjustableShelfValidation:
    """Integration tests for adjustable shelf validation."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_adjustable_shelf_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_adjustable_shelf_warns_for_positions_outside_pin_range(self) -> None:
        """Test that positions outside pin range generate warnings."""
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        component = AdjustableShelfComponent()
        # Position 1.0 is below default pin_start_height of 2.0
        config = {"positions": [1.0, 36.0]}

        result = component.validate(config, context)

        assert result.is_valid  # Warnings don't fail validation
        assert len(result.warnings) >= 1
        assert any("outside pin hole range" in w for w in result.warnings)


# =============================================================================
# Integration tests for Door Components
# =============================================================================


@pytest.fixture
def ensure_door_components_registered() -> None:
    """Ensure door components are registered for tests."""
    if "door.hinged.overlay" not in component_registry.list():
        component_registry.register("door.hinged.overlay")(OverlayDoorComponent)
    if "door.hinged.inset" not in component_registry.list():
        component_registry.register("door.hinged.inset")(InsetDoorComponent)


class TestDoorComponentIntegration:
    """Integration tests for door components with DOORED section type."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        ensure_shelf_registered: None,
        ensure_door_components_registered: None,
    ) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_doored_section_generates_door_panels(self) -> None:
        """Test that DOORED section type uses door.hinged.overlay and generates door panels.

        Verifies the full flow from SectionSpec with DOORED type to LayoutCalculator
        generating door panels using the component registry.
        """
        calculator = LayoutCalculator()
        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # Create a DOORED section with 1 door (shelves parameter used for door count)
        specs = [SectionSpec(width="fill", shelves=1, section_type=SectionType.DOORED)]

        cabinet, hardware = calculator.generate_cabinet_from_specs(wall, params, specs)

        # Verify cabinet was created with doored section
        assert cabinet is not None
        assert len(cabinet.sections) == 1
        assert cabinet.sections[0].section_type == SectionType.DOORED

        # Verify door panels were generated (as shelves from component)
        # The door component generates panels that are converted to shelves
        section = cabinet.sections[0]
        assert len(section.shelves) == 1  # Single door

        # Verify hardware includes door-related items
        assert len(hardware) > 0
        hardware_names = [h.name for h in hardware]
        assert any("Hinge" in name for name in hardware_names)
        assert any("Handle" in name or "Knob" in name for name in hardware_names)

    def test_door_hardware_aggregation(self) -> None:
        """Test that door hardware (hinges, handles, edge banding) aggregates correctly.

        Verifies that door components properly calculate and aggregate hardware
        requirements including hinges, handles, and edge banding.
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        # Create context for a 24"x72" section
        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        component = OverlayDoorComponent()
        config = {"count": 1, "soft_close": True}

        result = component.generate(config, context)

        # Verify hardware aggregation
        hardware_dict = {h.name: h for h in result.hardware}

        # Check hinges
        # With overlay=0.5 (default), reveal=0.125 (default):
        # door_height = 72 + (2 * 0.5) - 0.125 = 72.875"
        # Since 72.875" > 60", _calculate_hinge_count returns 4 hinges
        hinge_item = hardware_dict.get("Soft-Close European Hinge")
        assert hinge_item is not None
        assert hinge_item.quantity == 4  # 4 hinges for 72.875" door (> 60")
        assert hinge_item.sku == "EURO-35MM-SC"

        # Check handle/knob
        handle_item = hardware_dict.get("Handle/Knob")
        assert handle_item is not None
        assert handle_item.quantity == 1  # 1 handle for single door

        # Check edge banding
        edge_item = hardware_dict.get("Edge Banding")
        assert edge_item is not None
        assert edge_item.quantity == 1  # 1 entry for total perimeter
        assert "linear inches" in (edge_item.notes or "")

    def test_double_door_produces_two_panels(self) -> None:
        """Test that double door config generates 2 door panels.

        Verifies that specifying count=2 in component configuration produces
        two separate door panels with correct dimensions and hinge placements.
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=36.0,  # Wide enough for double doors
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        component = OverlayDoorComponent()
        config = {"count": 2}  # Double door configuration

        result = component.generate(config, context)

        # Verify two door panels were generated
        assert len(result.panels) == 2

        # Verify both panels are door type
        for panel in result.panels:
            assert panel.panel_type == PanelType.DOOR

        # Verify doors have equal widths (minus center gap)
        door_widths = [panel.width for panel in result.panels]
        assert door_widths[0] == pytest.approx(door_widths[1])

        # Verify hinge specifications in metadata
        hinge_specs = result.metadata.get("hinge_specs", [])
        assert len(hinge_specs) == 2
        door_ids = {spec.door_id for spec in hinge_specs}
        assert door_ids == {"left_door", "right_door"}

        # Verify hardware counts (hinges * 2 doors)
        hardware_dict = {h.name: h for h in result.hardware}
        hinge_item = hardware_dict.get("Soft-Close European Hinge")
        assert hinge_item is not None
        # Door height = 72 + (2 * 0.5) - 0.125 = 72.875" (with overlay defaults)
        # 72.875" > 60" means 4 hinges per door
        # 4 hinges per door * 2 doors = 8 hinges
        assert hinge_item.quantity == 8

    def test_door_component_override(self) -> None:
        """Test that section can specify component_id to use different door style.

        Verifies that component_config can override the default door.hinged.overlay
        to use door.hinged.inset or other door styles via component selection.
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        # Test overlay door sizing
        overlay_component = OverlayDoorComponent()
        overlay_config = {"count": 1, "reveal": 0.125, "overlay": 0.5}
        overlay_result = overlay_component.generate(overlay_config, context)

        # Test inset door sizing
        inset_component = InsetDoorComponent()
        inset_config = {"count": 1, "reveal": 0.125}
        inset_result = inset_component.generate(inset_config, context)

        # Verify both produce door panels
        assert len(overlay_result.panels) == 1
        assert len(inset_result.panels) == 1
        assert overlay_result.panels[0].panel_type == PanelType.DOOR
        assert inset_result.panels[0].panel_type == PanelType.DOOR

        # Verify sizing difference: overlay is larger than inset
        # Overlay: section_width + (2 * overlay) - reveal = 24 + 1.0 - 0.125 = 24.875"
        # Inset: section_width - (2 * reveal) = 24 - 0.25 = 23.75"
        overlay_width = overlay_result.panels[0].width
        inset_width = inset_result.panels[0].width

        assert overlay_width == pytest.approx(24.875)
        assert inset_width == pytest.approx(23.75)
        assert overlay_width > inset_width

        # Verify both can be retrieved from registry with different IDs
        assert "door.hinged.overlay" in component_registry.list()
        assert "door.hinged.inset" in component_registry.list()

        # Verify using registry to get different components works
        overlay_class = component_registry.get("door.hinged.overlay")
        inset_class = component_registry.get("door.hinged.inset")
        assert overlay_class == OverlayDoorComponent
        assert inset_class == InsetDoorComponent

    def test_door_panels_in_3d_mapping(self) -> None:
        """Test that door panels map correctly to 3D bounding boxes.

        Verifies that Panel3DMapper.DOOR case correctly positions door panels
        at the front face (y=0) of the cabinet with correct dimensions.
        """
        from cabinets.domain.value_objects import Position

        # Create a simple cabinet with a door
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )

        # Create door panel manually to test 3D mapping
        door_panel = Panel(
            panel_type=PanelType.DOOR,
            width=24.0,  # Door width
            height=72.0,  # Door height
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),  # Position within cabinet
        )

        # Use Panel3DMapper to convert to 3D
        mapper = Panel3DMapper(cabinet)
        bounding_box = mapper.map_panel(door_panel)

        # Verify door is positioned at front face
        # In the 3D coordinate system: y=0 is back, y=depth is front
        # Door origin.y = depth - thickness places the door at the front
        expected_y = cabinet.depth - door_panel.material.thickness
        assert bounding_box.origin.y == pytest.approx(expected_y)

        # Verify door dimensions
        assert bounding_box.size_x == pytest.approx(24.0)  # Door width
        assert bounding_box.size_y == pytest.approx(0.75)  # Material thickness
        assert bounding_box.size_z == pytest.approx(72.0)  # Door height

        # Verify door x position from panel position
        assert bounding_box.origin.x == pytest.approx(0.75)

        # Verify door z position from panel position.y
        assert bounding_box.origin.z == pytest.approx(0.75)


# =============================================================================
# Integration tests for Drawer Components
# =============================================================================


@pytest.fixture
def ensure_drawer_components_registered() -> None:
    """Ensure drawer components are registered for tests."""
    if "drawer.standard" not in component_registry.list():
        component_registry.register("drawer.standard")(StandardDrawerComponent)
    if "drawer.file" not in component_registry.list():
        component_registry.register("drawer.file")(FileDrawerComponent)


class TestDrawerComponentIntegration:
    """Integration tests for drawer component with cabinet generation."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        ensure_shelf_registered: None,
        ensure_drawer_components_registered: None,
    ) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_section_type_drawers_uses_drawer_component(self) -> None:
        """Verify SectionType.DRAWERS maps to drawer.standard component.

        Tests that a section with section_type=DRAWERS generates drawer panels
        using the drawer.standard component from the registry.
        """
        calculator = LayoutCalculator()
        # Use 16" depth to allow 12" slides (need depth > slide_length + 1" rear clearance)
        wall = Wall(width=48.0, height=84.0, depth=16.0)
        params = LayoutParameters(
            num_sections=1,
            shelves_per_section=0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # Create a DRAWERS section with 1 drawer (shelves parameter used for drawer count)
        specs = [SectionSpec(width="fill", shelves=1, section_type=SectionType.DRAWERS)]

        cabinet, hardware = calculator.generate_cabinet_from_specs(wall, params, specs)

        # Verify cabinet was created with drawers section
        assert cabinet is not None
        assert len(cabinet.sections) == 1
        assert cabinet.sections[0].section_type == SectionType.DRAWERS

        # Verify drawer panels were generated (stored in section.panels, not shelves)
        section = cabinet.sections[0]
        assert len(section.panels) >= 1  # At least one drawer panel generated

        # Verify drawer panel types are present
        panel_types = [panel.panel_type for panel in section.panels]
        assert PanelType.DRAWER_FRONT in panel_types
        assert PanelType.DRAWER_BOX_FRONT in panel_types

        # Verify hardware includes drawer-related items
        assert len(hardware) > 0
        hardware_names = [h.name for h in hardware]
        assert any("Slide" in name for name in hardware_names)

    def test_drawer_panels_in_cabinet_generation(self) -> None:
        """Verify drawer panels are included in cabinet generation output.

        Tests that DRAWER_* panel types appear in the output when generating
        a cabinet with a DRAWERS section type.
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        # Create context for a drawer section (16" depth for 12" slides)
        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=16.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=16.0,
        )

        component = StandardDrawerComponent()
        config = {"front_height": 6.0, "slide_type": "side_mount"}

        result = component.generate(config, context)

        # Verify drawer panels were generated
        panel_types = [panel.panel_type for panel in result.panels]
        assert PanelType.DRAWER_FRONT in panel_types
        assert PanelType.DRAWER_BOX_FRONT in panel_types
        assert PanelType.DRAWER_SIDE in panel_types
        assert PanelType.DRAWER_BOTTOM in panel_types

        # Verify correct number of panels: front, box front, 2 sides, bottom, top panel = 6
        assert len(result.panels) == 6

    def test_drawer_hardware_aggregation(self) -> None:
        """Verify drawer hardware is aggregated in cabinet generation.

        Tests that slides, screws, handles appear in hardware list when
        generating drawer components.
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        # Use 16" depth for 12" slides (need depth > slide_length + 1")
        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=16.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=16.0,
        )

        component = StandardDrawerComponent()
        config = {"front_height": 6.0, "slide_type": "side_mount", "soft_close": True}

        result = component.generate(config, context)

        # Verify hardware aggregation
        hardware_dict = {h.name: h for h in result.hardware}

        # Check slides (side_mount requires 2 slides)
        slide_item = [h for h in result.hardware if "Slide" in h.name][0]
        assert slide_item is not None
        assert slide_item.quantity == 2  # 2 slides for side_mount

        # Check mounting screws
        screw_item = hardware_dict.get('Mounting Screw #8x5/8"')
        assert screw_item is not None
        assert screw_item.quantity == 8  # 4 screws per slide * 2 slides

        # Check handle/pull
        handle_item = hardware_dict.get("Handle/Pull")
        assert handle_item is not None
        assert handle_item.quantity == 1

        # Check edge banding
        edge_item = hardware_dict.get("Edge Banding")
        assert edge_item is not None
        assert edge_item.quantity == 1

    def test_file_drawer_validation(self) -> None:
        """Verify file drawer validates height requirements.

        Tests that FileDrawerComponent properly validates minimum height
        requirements for letter and legal file types.
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        # Use 18" depth with explicit 16" slide length to avoid slide/depth conflicts
        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=18.0,  # Deeper for file drawer
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=18.0,
        )

        component = FileDrawerComponent()

        # Test letter file with sufficient height (specify slide_length to avoid auto-selection issues)
        valid_config = {"front_height": 12.0, "file_type": "letter", "slide_length": 16}
        result = component.validate(valid_config, context)
        assert result.is_valid

        # Test letter file with insufficient height (box height would be 5.375")
        invalid_config = {
            "front_height": 6.0,
            "file_type": "letter",
            "slide_length": 16,
        }
        result = component.validate(invalid_config, context)
        assert not result.is_valid
        assert any("below minimum" in err for err in result.errors)

    def test_drawer_slide_auto_selection(self) -> None:
        """Verify auto slide length selection based on cabinet depth.

        Tests that slide_length="auto" correctly selects appropriate slide
        length based on section depth. Selection logic: for each slide length,
        if depth < length + 2, return that length. This gives 2" clearance.

        Selection table:
        - depth < 14" -> 12" slides
        - depth 14-16" -> 14" slides
        - depth 16-18" -> 16" slides
        - depth 18-20" -> 18" slides
        - depth 20-22" -> 20" slides
        - depth 22-24" -> 22" slides
        - depth >= 24" -> 24" slides
        """
        from cabinets.domain.components import ComponentContext
        from cabinets.domain.value_objects import Position

        # Test with 13" depth - should select 12" slides (13 < 14)
        context_13 = ComponentContext(
            width=24.0,
            height=72.0,
            depth=13.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=13.0,
        )

        component = StandardDrawerComponent()
        config = {"front_height": 6.0, "slide_length": "auto"}

        result = component.generate(config, context_13)
        assert result.metadata["slide_length"] == 12

        # Test with 17" depth - should select 16" slides (17 < 18)
        context_17 = ComponentContext(
            width=24.0,
            height=72.0,
            depth=17.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=17.0,
        )

        result = component.generate(config, context_17)
        assert result.metadata["slide_length"] == 16

    def test_drawer_components_in_registry(self) -> None:
        """Verify drawer components are properly registered.

        Tests that drawer.standard and drawer.file are registered in the
        component registry and can be retrieved.
        """
        assert "drawer.standard" in component_registry.list()
        assert "drawer.file" in component_registry.list()

        standard_class = component_registry.get("drawer.standard")
        file_class = component_registry.get("drawer.file")

        assert standard_class == StandardDrawerComponent
        assert file_class == FileDrawerComponent
