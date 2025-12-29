"""Tests for FixedShelfComponent, DadoSpec, and PinHolePattern."""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    HardwareItem,
    ValidationResult,
    component_registry,
)
from cabinets.domain.components.shelf import (
    DadoSpec,
    FixedShelfComponent,
    MM_TO_INCH,
    PinHolePattern,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def shelf_component() -> FixedShelfComponent:
    """Create a FixedShelfComponent instance for testing."""
    return FixedShelfComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 24" wide section with 72" height
    (interior height) at position (0.75, 0.75) within a 48x84x12 cabinet.
    """
    return ComponentContext(
        width=24.0,
        height=72.0,
        depth=11.5,  # Interior depth (12 - 0.5 back panel)
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


class TestShelfComponentRegistration:
    """Tests for shelf.fixed component registration."""

    @pytest.fixture(autouse=True)
    def ensure_shelf_registered(self) -> None:
        """Ensure shelf.fixed is registered for each test.

        Other tests may clear the registry, so we re-register if needed.
        """
        if "shelf.fixed" not in component_registry.list():
            # Re-register by calling the decorator manually
            component_registry.register("shelf.fixed")(FixedShelfComponent)

    def test_component_is_registered_as_shelf_fixed(self) -> None:
        """Test that shelf.fixed is registered in the component registry."""
        assert "shelf.fixed" in component_registry.list()

    def test_get_returns_fixed_shelf_component_class(self) -> None:
        """Test that registry.get returns FixedShelfComponent."""
        component_class = component_registry.get("shelf.fixed")
        assert component_class is FixedShelfComponent


class TestShelfComponentValidation:
    """Tests for FixedShelfComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid shelf count."""
        config = {"count": 3}

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_zero_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for zero shelf count."""
        config = {"count": 0}

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_missing_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok when count is missing (defaults to 0)."""
        config: dict = {}

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_error_for_negative_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for negative shelf count."""
        config = {"count": -1}

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "shelf count must be non-negative integer" in result.errors

    def test_validate_returns_error_for_count_exceeding_maximum(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for count > 20."""
        config = {"count": 21}

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "shelf count exceeds maximum of 20" in result.errors

    def test_validate_accepts_count_of_20(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate accepts count of exactly 20."""
        config = {"count": 20}

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_non_integer_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for non-integer count."""
        config = {"count": 3.5}

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "shelf count must be non-negative integer" in result.errors

    def test_validate_returns_warning_for_wide_shelf_with_thin_material(
        self, shelf_component: FixedShelfComponent
    ) -> None:
        """Test that validate warns when width > 36 with 3/4 material."""
        wide_context = ComponentContext(
            width=40.0,  # Exceeds 36" recommendation
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),  # 0.75" material
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 3}

        result = shelf_component.validate(config, wide_context)

        assert result.is_valid  # Warnings don't fail validation
        assert len(result.warnings) == 1
        assert "exceeds recommended 36\"" in result.warnings[0]
        assert "consider center support" in result.warnings[0]

    def test_validate_no_warning_for_narrow_shelf(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate has no warning for width <= 36."""
        config = {"count": 3}

        result = shelf_component.validate(config, standard_context)

        assert len(result.warnings) == 0

    def test_validate_no_warning_for_wide_shelf_with_thick_material(
        self, shelf_component: FixedShelfComponent
    ) -> None:
        """Test that validate has no warning for width > 36 with material > 0.75."""
        wide_context = ComponentContext(
            width=40.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec(thickness=1.0, material_type="plywood"),  # 1" material
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 3}

        result = shelf_component.validate(config, wide_context)

        assert len(result.warnings) == 0


class TestShelfComponentGeneration:
    """Tests for FixedShelfComponent.generate()."""

    def test_generate_returns_empty_for_zero_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns empty result for count=0."""
        config = {"count": 0}

        result = shelf_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_generate_returns_empty_for_missing_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns empty result for missing count."""
        config: dict = {}

        result = shelf_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_generate_creates_correct_number_of_panels(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates the correct number of shelf panels."""
        config = {"count": 3}

        result = shelf_component.generate(config, standard_context)

        assert len(result.panels) == 3

    def test_generate_creates_panels_of_correct_type(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panels are of type SHELF."""
        config = {"count": 2}

        result = shelf_component.generate(config, standard_context)

        for panel in result.panels:
            assert panel.panel_type == PanelType.SHELF

    def test_generate_panels_have_correct_dimensions(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panels have correct width and height (depth).

        Note: Shelf depth is context.depth - default setback (1.0").
        """
        config = {"count": 2}

        result = shelf_component.generate(config, standard_context)

        default_setback = 1.0
        expected_depth = standard_context.depth - default_setback  # 11.5 - 1.0 = 10.5

        for panel in result.panels:
            assert panel.width == standard_context.width  # 24.0
            assert panel.height == expected_depth  # 10.5 (depth becomes height in panel)

    def test_generate_panels_have_correct_material(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panels have the context material."""
        config = {"count": 2}

        result = shelf_component.generate(config, standard_context)

        for panel in result.panels:
            assert panel.material == standard_context.material

    def test_generate_calculates_correct_shelf_positions_evenly_spaced(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelves are evenly spaced within the section.

        For a 72" height section with 3 shelves:
        spacing = 72 / (3 + 1) = 18"
        Shelf 1: y = 0.75 + 18 = 18.75"
        Shelf 2: y = 0.75 + 36 = 36.75"
        Shelf 3: y = 0.75 + 54 = 54.75"

        Note: x-position is at section start (setback only affects depth, not width).
        """
        config = {"count": 3}

        result = shelf_component.generate(config, standard_context)

        expected_spacing = 72.0 / 4  # 18.0
        expected_y_positions = [
            0.75 + expected_spacing * (i + 1) for i in range(3)
        ]
        # Shelf x is at section start - setback is for front edge (depth), not left edge
        expected_x = standard_context.position.x

        for i, panel in enumerate(result.panels):
            assert panel.position.y == pytest.approx(expected_y_positions[i])
            assert panel.position.x == pytest.approx(expected_x)  # At section left edge

    def test_generate_single_shelf_centered(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that a single shelf is centered in the section."""
        config = {"count": 1}

        result = shelf_component.generate(config, standard_context)

        # For 1 shelf: spacing = 72 / 2 = 36, y = 0.75 + 36 = 36.75
        assert len(result.panels) == 1
        assert result.panels[0].position.y == pytest.approx(0.75 + 36.0)

    def test_generate_many_shelves_correct_spacing(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that many shelves (10) are correctly spaced."""
        config = {"count": 10}

        result = shelf_component.generate(config, standard_context)

        assert len(result.panels) == 10
        expected_spacing = 72.0 / 11  # ~6.545"

        for i, panel in enumerate(result.panels):
            expected_y = 0.75 + expected_spacing * (i + 1)
            assert panel.position.y == pytest.approx(expected_y)

    def test_generate_returns_generation_result_type(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"count": 2}

        result = shelf_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)


class TestShelfComponentHardware:
    """Tests for FixedShelfComponent.hardware()."""

    def test_hardware_returns_edge_banding_by_default(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns edge banding when edge_band_front is True (default)."""
        config = {"count": 3}

        result = shelf_component.hardware(config, standard_context)

        assert len(result) == 1
        assert result[0].name == "Edge Banding"
        assert "72.0 linear inches" in result[0].notes  # 24.0 width * 3 shelves

    def test_hardware_returns_empty_when_edge_banding_disabled(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list when edge_band_front is False."""
        config = {"count": 3, "edge_band_front": False}

        result = shelf_component.hardware(config, standard_context)

        assert result == []

    def test_hardware_returns_pins_when_use_pins_true(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns shelf pins when use_pins is True."""
        config = {"count": 3, "use_pins": True}

        result = shelf_component.hardware(config, standard_context)

        # Should have both edge banding and shelf pins
        assert len(result) == 2
        pin_item = next(item for item in result if item.name == "Shelf Pin")
        assert isinstance(pin_item, HardwareItem)
        assert pin_item.name == "Shelf Pin"

    def test_hardware_returns_correct_pin_quantity(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns 4 pins per shelf."""
        config = {"count": 5, "use_pins": True, "edge_band_front": False}

        result = shelf_component.hardware(config, standard_context)

        assert result[0].name == "Shelf Pin"
        assert result[0].quantity == 20  # 5 shelves * 4 pins

    def test_hardware_returns_correct_sku_and_notes(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware has correct SKU and notes."""
        config = {"count": 2, "use_pins": True, "edge_band_front": False}

        result = shelf_component.hardware(config, standard_context)

        assert result[0].name == "Shelf Pin"
        assert result[0].sku == "SP-5MM"
        assert result[0].notes == "5mm brass shelf pins"

    def test_hardware_returns_empty_for_zero_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list when count is 0."""
        config = {"count": 0, "use_pins": True}

        result = shelf_component.hardware(config, standard_context)

        assert result == []

    def test_hardware_returns_empty_for_zero_count_with_pins_enabled(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list when no shelves even with pins enabled."""
        config = {"count": 0, "use_pins": True}

        result = shelf_component.hardware(config, standard_context)

        assert result == []


class TestShelfComponentIntegration:
    """Integration tests for FixedShelfComponent with the registry."""

    @pytest.fixture(autouse=True)
    def ensure_shelf_registered(self) -> None:
        """Ensure shelf.fixed is registered for integration tests.

        Other tests may clear the registry, so we re-register if needed.
        """
        if "shelf.fixed" not in component_registry.list():
            component_registry.register("shelf.fixed")(FixedShelfComponent)

    def test_full_workflow_validate_generate_hardware(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        # Get component from registry
        component_class = component_registry.get("shelf.fixed")
        component = component_class()

        config = {"count": 4, "use_pins": True}

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 4

        # Hardware - should have edge banding and shelf pins
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 2
        edge_banding = next(h for h in hardware if h.name == "Edge Banding")
        shelf_pins = next(h for h in hardware if h.name == "Shelf Pin")
        assert edge_banding is not None
        assert shelf_pins.quantity == 16  # 4 * 4 pins

    def test_component_matches_existing_layout_calculator_behavior(
        self, shelf_component: FixedShelfComponent
    ) -> None:
        """Test that shelf positions match the existing LayoutCalculator behavior.

        The existing behavior from services.py:170-181:
        - shelf_spacing = cabinet.interior_height / (spec.shelves + 1)
        - shelf_y = params.material.thickness + shelf_spacing * (j + 1)

        For a cabinet with interior_height=82.5 (84 - 2*0.75), 3 shelves:
        - spacing = 82.5 / 4 = 20.625
        - positions: 0.75 + 20.625 = 21.375, 0.75 + 41.25 = 42.0, 0.75 + 61.875 = 62.625
        """
        # Create a context matching the layout calculator behavior
        context = ComponentContext(
            width=23.25,  # section_width
            height=82.5,  # interior_height
            depth=11.5,  # interior_depth
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),  # current_x, material.thickness
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 3}

        result = shelf_component.generate(config, context)

        # Expected spacing: 82.5 / 4 = 20.625
        expected_positions = [
            0.75 + 20.625,   # 21.375
            0.75 + 41.25,    # 42.0
            0.75 + 61.875,   # 62.625
        ]

        assert len(result.panels) == 3
        for i, panel in enumerate(result.panels):
            assert panel.position.y == pytest.approx(expected_positions[i], rel=1e-5)


class TestMMToInchConstant:
    """Tests for MM_TO_INCH conversion constant."""

    def test_mm_to_inch_value(self) -> None:
        """Test that MM_TO_INCH is the correct conversion factor."""
        assert MM_TO_INCH == pytest.approx(0.03937008)

    def test_mm_to_inch_conversion_accuracy(self) -> None:
        """Test that conversion gives expected values for known measurements."""
        # 25.4mm = 1 inch
        assert 25.4 * MM_TO_INCH == pytest.approx(1.0, rel=1e-5)

    def test_32mm_conversion(self) -> None:
        """Test that 32mm converts to approximately 1.26 inches."""
        assert 32.0 * MM_TO_INCH == pytest.approx(1.26, abs=0.01)

    def test_5mm_conversion(self) -> None:
        """Test that 5mm converts to approximately 0.197 inches."""
        assert 5.0 * MM_TO_INCH == pytest.approx(0.197, abs=0.001)

    def test_37mm_conversion(self) -> None:
        """Test that 37mm (standard inset) converts to approximately 1.46 inches."""
        assert 37.0 * MM_TO_INCH == pytest.approx(1.46, abs=0.01)


class TestDadoSpec:
    """Tests for DadoSpec value object."""

    def test_dado_spec_creation(self) -> None:
        """Test that DadoSpec can be created with all fields."""
        dado = DadoSpec(
            panel_id="left_side",
            position=12.0,
            width=0.75,
            depth=0.25,
            length=11.0,
        )

        assert dado.panel_id == "left_side"
        assert dado.position == 12.0
        assert dado.width == 0.75
        assert dado.depth == 0.25
        assert dado.length == 11.0

    def test_dado_spec_is_frozen(self) -> None:
        """Test that DadoSpec is immutable (frozen)."""
        dado = DadoSpec("left_side", 12.0, 0.75, 0.25, 11.0)

        with pytest.raises(AttributeError):
            dado.position = 15.0  # type: ignore

    def test_dado_spec_equality(self) -> None:
        """Test that two DadoSpecs with same values are equal."""
        dado1 = DadoSpec("left_side", 12.0, 0.75, 0.25, 11.0)
        dado2 = DadoSpec("left_side", 12.0, 0.75, 0.25, 11.0)

        assert dado1 == dado2

    def test_dado_spec_inequality(self) -> None:
        """Test that DadoSpecs with different values are not equal."""
        dado1 = DadoSpec("left_side", 12.0, 0.75, 0.25, 11.0)
        dado2 = DadoSpec("right_side", 12.0, 0.75, 0.25, 11.0)

        assert dado1 != dado2

    def test_dado_spec_right_side_panel(self) -> None:
        """Test creating DadoSpec for right side panel."""
        dado = DadoSpec(
            panel_id="right_side",
            position=24.0,
            width=0.75,
            depth=0.25,
            length=11.5,
        )

        assert dado.panel_id == "right_side"
        assert dado.position == 24.0

    def test_dado_spec_typical_dimensions(self) -> None:
        """Test DadoSpec with typical 3/4 material dimensions.

        For 3/4" material:
        - width = 0.75 (material thickness)
        - depth = 0.25 (thickness / 3)
        """
        thickness = 0.75
        dado = DadoSpec(
            panel_id="left_side",
            position=18.0,
            width=thickness,
            depth=thickness / 3,  # 0.25
            length=11.5,
        )

        assert dado.width == 0.75
        assert dado.depth == pytest.approx(0.25)

    def test_dado_spec_hashable(self) -> None:
        """Test that DadoSpec can be used in sets and as dict keys."""
        dado = DadoSpec("left_side", 12.0, 0.75, 0.25, 11.0)

        # Should be able to add to set
        dado_set = {dado}
        assert dado in dado_set

        # Should be able to use as dict key
        dado_dict = {dado: "test"}
        assert dado_dict[dado] == "test"


class TestPinHolePattern:
    """Tests for PinHolePattern value object."""

    def test_pin_hole_pattern_creation_with_defaults(self) -> None:
        """Test PinHolePattern creation with default spacing and hole diameter."""
        pattern = PinHolePattern(
            panel_id="left_side",
            front_inset=1.46,
            back_inset=1.46,
            start_height=2.0,
            end_height=80.0,
        )

        assert pattern.panel_id == "left_side"
        assert pattern.front_inset == 1.46
        assert pattern.back_inset == 1.46
        assert pattern.start_height == 2.0
        assert pattern.end_height == 80.0
        # Check defaults
        assert pattern.spacing == pytest.approx(32.0 * MM_TO_INCH, rel=1e-5)
        assert pattern.hole_diameter == pytest.approx(5.0 * MM_TO_INCH, rel=1e-5)

    def test_pin_hole_pattern_default_spacing_value(self) -> None:
        """Test that default spacing is approximately 1.26 inches (32mm)."""
        pattern = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)

        assert pattern.spacing == pytest.approx(1.26, abs=0.01)

    def test_pin_hole_pattern_default_hole_diameter_value(self) -> None:
        """Test that default hole diameter is approximately 0.197 inches (5mm)."""
        pattern = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)

        assert pattern.hole_diameter == pytest.approx(0.197, abs=0.001)

    def test_pin_hole_pattern_custom_spacing(self) -> None:
        """Test PinHolePattern with custom spacing."""
        pattern = PinHolePattern(
            panel_id="left_side",
            front_inset=1.46,
            back_inset=1.46,
            start_height=2.0,
            end_height=80.0,
            spacing=1.5,  # Custom spacing
        )

        assert pattern.spacing == 1.5

    def test_pin_hole_pattern_custom_hole_diameter(self) -> None:
        """Test PinHolePattern with custom hole diameter."""
        pattern = PinHolePattern(
            panel_id="left_side",
            front_inset=1.46,
            back_inset=1.46,
            start_height=2.0,
            end_height=80.0,
            hole_diameter=0.25,  # 1/4" holes
        )

        assert pattern.hole_diameter == 0.25

    def test_pin_hole_pattern_is_frozen(self) -> None:
        """Test that PinHolePattern is immutable (frozen)."""
        pattern = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)

        with pytest.raises(AttributeError):
            pattern.start_height = 5.0  # type: ignore

    def test_pin_hole_pattern_equality(self) -> None:
        """Test that two PinHolePatterns with same values are equal."""
        pattern1 = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)
        pattern2 = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)

        assert pattern1 == pattern2

    def test_pin_hole_pattern_inequality(self) -> None:
        """Test that PinHolePatterns with different values are not equal."""
        pattern1 = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)
        pattern2 = PinHolePattern("left_side", 1.46, 1.46, 2.0, 70.0)

        assert pattern1 != pattern2

    def test_pin_hole_pattern_right_side_panel(self) -> None:
        """Test creating PinHolePattern for right side panel."""
        pattern = PinHolePattern(
            panel_id="right_side",
            front_inset=1.46,
            back_inset=1.46,
            start_height=3.0,
            end_height=75.0,
        )

        assert pattern.panel_id == "right_side"

    def test_pin_hole_pattern_asymmetric_insets(self) -> None:
        """Test PinHolePattern with different front and back insets."""
        pattern = PinHolePattern(
            panel_id="left_side",
            front_inset=2.0,
            back_inset=1.0,
            start_height=2.0,
            end_height=80.0,
        )

        assert pattern.front_inset == 2.0
        assert pattern.back_inset == 1.0

    def test_pin_hole_pattern_hashable(self) -> None:
        """Test that PinHolePattern can be used in sets and as dict keys."""
        pattern = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)

        # Should be able to add to set
        pattern_set = {pattern}
        assert pattern in pattern_set

        # Should be able to use as dict key
        pattern_dict = {pattern: "test"}
        assert pattern_dict[pattern] == "test"

    def test_pin_hole_pattern_hole_count_calculation(self) -> None:
        """Test that hole count can be calculated from pattern.

        For a pattern from height 2" to 80" with 32mm (~1.26") spacing:
        - Range = 80 - 2 = 78"
        - Number of holes = floor(78 / 1.26) + 1 = 62 + 1 = 63 holes
        """
        pattern = PinHolePattern("left_side", 1.46, 1.46, 2.0, 80.0)

        height_range = pattern.end_height - pattern.start_height
        hole_count = int(height_range / pattern.spacing) + 1

        # Approximately 62-63 holes depending on exact spacing
        assert 60 <= hole_count <= 65


class TestPositionsBasedConfiguration:
    """Tests for positions-based shelf configuration."""

    def test_validate_explicit_positions_within_bounds(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that explicit positions within bounds pass validation."""
        config = {"positions": [12.0, 36.0, 60.0]}

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_explicit_positions_outside_bounds_fails(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that positions outside section height fail validation."""
        config = {"positions": [12.0, 80.0]}  # 80 > 72 (section height)

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "position 80.0\" outside section height" in result.errors[0]

    def test_validate_negative_position_fails(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that negative positions fail validation."""
        config = {"positions": [-5.0, 36.0]}

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "position -5.0\" outside section height" in result.errors[0]

    def test_validate_minimum_spacing_between_shelves(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelves less than 2\" apart fail validation."""
        config = {"positions": [12.0, 13.0, 36.0]}  # 12 and 13 are only 1" apart

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "less than 2\" apart" in result.errors[0]

    def test_validate_exactly_2_inch_spacing_passes(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelves exactly 2\" apart pass validation."""
        config = {"positions": [12.0, 14.0, 36.0]}  # 12 and 14 are exactly 2" apart

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid

    def test_generate_creates_shelves_at_explicit_positions(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelves are created at explicitly specified positions."""
        config = {"positions": [12.0, 36.0, 60.0]}

        result = shelf_component.generate(config, standard_context)

        assert len(result.panels) == 3
        expected_y = [0.75 + 12.0, 0.75 + 36.0, 0.75 + 60.0]
        for i, panel in enumerate(result.panels):
            assert panel.position.y == pytest.approx(expected_y[i])


class TestSetbackConfiguration:
    """Tests for setback configuration.

    Setback is the front edge inset from section front (depth direction),
    not a left edge offset. It only affects shelf depth, not x position.
    """

    def test_default_setback_affects_depth_not_x(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that default setback of 1.0 inch affects depth, not x position."""
        config = {"count": 1}

        result = shelf_component.generate(config, standard_context)

        # x-position should be at section start (setback doesn't affect x)
        assert result.panels[0].position.x == pytest.approx(standard_context.position.x)
        # depth should be reduced by default setback of 1.0
        expected_depth = standard_context.depth - 1.0  # 11.5 - 1.0 = 10.5
        assert result.panels[0].height == pytest.approx(expected_depth)

    def test_custom_setback_affects_depth_not_x(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that custom setback affects depth, not x position."""
        config = {"count": 1, "setback": 2.0}

        result = shelf_component.generate(config, standard_context)

        # x-position should be at section start (setback doesn't affect x)
        assert result.panels[0].position.x == pytest.approx(standard_context.position.x)
        # depth should be reduced by custom setback
        expected_depth = standard_context.depth - 2.0  # 11.5 - 2.0 = 9.5
        assert result.panels[0].height == pytest.approx(expected_depth)

    def test_zero_setback_places_shelf_at_section_front(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that zero setback places shelf at section front."""
        config = {"count": 1, "setback": 0.0}

        result = shelf_component.generate(config, standard_context)

        assert result.panels[0].position.x == pytest.approx(standard_context.position.x)

    def test_setback_reduces_shelf_depth(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that setback reduces shelf depth appropriately."""
        config = {"count": 1, "setback": 2.0}

        result = shelf_component.generate(config, standard_context)

        expected_depth = standard_context.depth - 2.0  # 11.5 - 2.0 = 9.5
        assert result.panels[0].height == pytest.approx(expected_depth)


class TestDepthOverride:
    """Tests for depth override configuration."""

    def test_explicit_depth_overrides_calculated_depth(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that explicit depth overrides calculated depth."""
        config = {"count": 1, "depth": 8.0}

        result = shelf_component.generate(config, standard_context)

        assert result.panels[0].height == pytest.approx(8.0)

    def test_validate_depth_exceeding_available_fails(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that depth exceeding available depth fails validation."""
        # Available depth = 11.5 - 1.0 (default setback) = 10.5
        config = {"count": 1, "depth": 12.0}

        result = shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "exceeds available" in result.errors[0]

    def test_validate_depth_within_available_passes(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that depth within available depth passes validation."""
        config = {"count": 1, "depth": 8.0}

        result = shelf_component.validate(config, standard_context)

        assert result.is_valid


class TestDadoSpecGeneration:
    """Tests for DadoSpec generation in generate() method."""

    def test_generate_creates_dado_specs_in_metadata(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates dado_specs in metadata."""
        config = {"count": 2}

        result = shelf_component.generate(config, standard_context)

        assert "dado_specs" in result.metadata
        assert len(result.metadata["dado_specs"]) == 4  # 2 shelves * 2 sides

    def test_generate_creates_left_and_right_dado_specs(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado specs are created for both left and right side panels."""
        config = {"count": 1}

        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        assert len(dado_specs) == 2
        panel_ids = {spec.panel_id for spec in dado_specs}
        assert panel_ids == {"left_side", "right_side"}

    def test_dado_spec_has_correct_position(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado spec position matches shelf position within section."""
        config = {"positions": [24.0]}

        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        for spec in dado_specs:
            assert spec.position == 24.0

    def test_dado_spec_has_correct_width(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado width equals material thickness."""
        config = {"count": 1}

        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        for spec in dado_specs:
            assert spec.width == standard_context.material.thickness  # 0.75

    def test_dado_spec_has_correct_depth(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado depth equals thickness / 3."""
        config = {"count": 1}

        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        expected_depth = standard_context.material.thickness / 3  # 0.25
        for spec in dado_specs:
            assert spec.depth == pytest.approx(expected_depth)

    def test_dado_spec_length_matches_shelf_depth(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado length matches the shelf depth (not section depth)."""
        config = {"count": 1, "depth": 9.0}

        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        for spec in dado_specs:
            assert spec.length == 9.0

    def test_dado_spec_length_uses_calculated_depth(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado length uses calculated depth when no override."""
        config = {"count": 1}  # No depth override

        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        expected_depth = standard_context.depth - 1.0  # 11.5 - 1.0 setback = 10.5
        for spec in dado_specs:
            assert spec.length == pytest.approx(expected_depth)


class TestEdgeBandingGeneration:
    """Tests for edge banding generation."""

    def test_generate_includes_edge_banding_hardware(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes edge banding in hardware."""
        config = {"count": 3}

        result = shelf_component.generate(config, standard_context)

        assert len(result.hardware) == 1
        assert result.hardware[0].name == "Edge Banding"

    def test_generate_edge_banding_calculation(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that edge banding linear inches calculation is correct."""
        config = {"count": 3}

        result = shelf_component.generate(config, standard_context)

        # 24.0 width * 3 shelves = 72.0 linear inches
        assert "72.0 linear inches" in result.hardware[0].notes

    def test_generate_no_edge_banding_when_disabled(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that edge banding is excluded when edge_band_front is False."""
        config = {"count": 3, "edge_band_front": False}

        result = shelf_component.generate(config, standard_context)

        assert len(result.hardware) == 0


class TestBackwardCompatibility:
    """Tests to verify backward compatibility with existing configurations."""

    def test_count_based_config_still_works(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that count-based configuration continues to work."""
        config = {"count": 3}

        validation = shelf_component.validate(config, standard_context)
        generation = shelf_component.generate(config, standard_context)

        assert validation.is_valid
        assert len(generation.panels) == 3

    def test_use_pins_config_still_works(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that use_pins configuration continues to work."""
        config = {"count": 3, "use_pins": True}

        hardware = shelf_component.hardware(config, standard_context)

        pin_items = [h for h in hardware if h.name == "Shelf Pin"]
        assert len(pin_items) == 1
        assert pin_items[0].quantity == 12  # 3 * 4 pins

    def test_empty_config_returns_empty_result(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that empty config returns empty generation result."""
        config: dict = {}

        result = shelf_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_wide_span_warning_still_generated(
        self, shelf_component: FixedShelfComponent
    ) -> None:
        """Test that wide span warning is still generated for >36\" spans."""
        wide_context = ComponentContext(
            width=40.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 3}

        result = shelf_component.validate(config, wide_context)

        assert len(result.warnings) == 1
        assert "exceeds recommended 36\"" in result.warnings[0]


# =============================================================================
# AdjustableShelfComponent Tests
# =============================================================================

from cabinets.domain.components.shelf import AdjustableShelfComponent


@pytest.fixture
def adjustable_shelf_component() -> AdjustableShelfComponent:
    """Create an AdjustableShelfComponent instance for testing."""
    return AdjustableShelfComponent()


class TestAdjustableShelfComponentRegistration:
    """Tests for shelf.adjustable component registration."""

    @pytest.fixture(autouse=True)
    def ensure_adjustable_shelf_registered(self) -> None:
        """Ensure shelf.adjustable is registered for each test."""
        if "shelf.adjustable" not in component_registry.list():
            component_registry.register("shelf.adjustable")(AdjustableShelfComponent)

    def test_component_is_registered_as_shelf_adjustable(self) -> None:
        """Test that shelf.adjustable is registered in the component registry."""
        assert "shelf.adjustable" in component_registry.list()

    def test_get_returns_adjustable_shelf_component_class(self) -> None:
        """Test that registry.get returns AdjustableShelfComponent."""
        component_class = component_registry.get("shelf.adjustable")
        assert component_class is AdjustableShelfComponent


class TestAdjustableShelfComponentValidation:
    """Tests for AdjustableShelfComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid shelf count."""
        config = {"count": 3}

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_zero_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for zero shelf count."""
        config = {"count": 0}

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_valid_positions(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid explicit positions."""
        config = {"positions": [12.0, 36.0, 60.0]}

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_warns_for_position_outside_pin_range(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate warns when shelf position is outside pin hole range."""
        # Default pin range: 2.0" to (72.0 - 2.0) = 70.0"
        config = {"positions": [1.0]}  # Below pin_start_height of 2.0"

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid  # Warnings don't fail validation
        assert len(result.warnings) == 1
        assert "outside pin hole range" in result.warnings[0]

    def test_validate_warns_for_position_above_pin_end(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate warns when shelf position is above pin end height."""
        # Default pin range: 2.0" to (72.0 - 2.0) = 70.0"
        config = {"positions": [71.0]}  # Above pin end of 70.0"

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 1
        assert "outside pin hole range" in result.warnings[0]

    def test_validate_error_for_depth_exceeding_available(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate errors when depth exceeds available depth."""
        # Available depth = 11.5 - 1.0 (default setback) = 10.5
        config = {"count": 1, "depth": 12.0}

        result = adjustable_shelf_component.validate(config, standard_context)

        assert not result.is_valid
        assert "exceeds available" in result.errors[0]

    def test_validate_warns_for_wide_shelf_with_thin_material(
        self, adjustable_shelf_component: AdjustableShelfComponent
    ) -> None:
        """Test that validate warns when width > 36\" with 3/4\" material."""
        wide_context = ComponentContext(
            width=40.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 3}

        result = adjustable_shelf_component.validate(config, wide_context)

        assert result.is_valid
        assert len(result.warnings) == 1
        assert "exceeds recommended 36\"" in result.warnings[0]

    def test_validate_custom_pin_start_height(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate respects custom pin_start_height."""
        config = {"positions": [4.0], "pin_start_height": 5.0}

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 1
        assert "outside pin hole range" in result.warnings[0]

    def test_validate_custom_pin_end_offset(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate respects custom pin_end_offset."""
        config = {"positions": [66.0], "pin_end_offset": 10.0}  # pin_end = 72 - 10 = 62

        result = adjustable_shelf_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 1
        assert "outside pin hole range" in result.warnings[0]


class TestAdjustableShelfComponentGeneration:
    """Tests for AdjustableShelfComponent.generate()."""

    def test_generate_returns_empty_for_zero_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns empty result for count=0."""
        config = {"count": 0}

        result = adjustable_shelf_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_generate_returns_empty_for_missing_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns empty result for missing count."""
        config: dict = {}

        result = adjustable_shelf_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_generate_creates_correct_number_of_panels(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates the correct number of shelf panels."""
        config = {"count": 3}

        result = adjustable_shelf_component.generate(config, standard_context)

        assert len(result.panels) == 3

    def test_generate_creates_panels_at_correct_positions(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelves are evenly spaced within the section.

        Setback is for front edge (depth direction), not left edge.
        Shelf x position is at section start.
        """
        config = {"count": 3}

        result = adjustable_shelf_component.generate(config, standard_context)

        expected_spacing = 72.0 / 4  # 18.0
        expected_y_positions = [0.75 + expected_spacing * (i + 1) for i in range(3)]
        # Shelf x is at section start - setback is for front edge (depth), not left edge
        expected_x = standard_context.position.x

        for i, panel in enumerate(result.panels):
            assert panel.position.y == pytest.approx(expected_y_positions[i])
            assert panel.position.x == pytest.approx(expected_x)

    def test_generate_creates_panels_with_correct_dimensions(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panels have correct dimensions."""
        config = {"count": 2}

        result = adjustable_shelf_component.generate(config, standard_context)

        default_setback = 1.0
        expected_depth = standard_context.depth - default_setback

        for panel in result.panels:
            assert panel.width == standard_context.width
            assert panel.height == expected_depth

    def test_generate_creates_pin_hole_patterns_in_metadata(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates pin_hole_patterns in metadata."""
        config = {"count": 2}

        result = adjustable_shelf_component.generate(config, standard_context)

        assert "pin_hole_patterns" in result.metadata
        patterns = result.metadata["pin_hole_patterns"]
        assert len(patterns) == 2  # Left and right side

    def test_generate_pin_patterns_have_correct_panel_ids(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that pin patterns are for left and right side panels."""
        config = {"count": 1}

        result = adjustable_shelf_component.generate(config, standard_context)

        patterns = result.metadata["pin_hole_patterns"]
        panel_ids = {p.panel_id for p in patterns}
        assert panel_ids == {"left_side", "right_side"}

    def test_generate_pin_patterns_have_correct_heights(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that pin patterns have correct start and end heights."""
        config = {"count": 1}

        result = adjustable_shelf_component.generate(config, standard_context)

        for pattern in result.metadata["pin_hole_patterns"]:
            assert pattern.start_height == 2.0  # DEFAULT_PIN_START
            assert pattern.end_height == 70.0  # 72.0 - DEFAULT_PIN_END (2.0)

    def test_generate_pin_patterns_with_custom_heights(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that custom pin heights are respected."""
        config = {"count": 1, "pin_start_height": 3.0, "pin_end_offset": 4.0}

        result = adjustable_shelf_component.generate(config, standard_context)

        for pattern in result.metadata["pin_hole_patterns"]:
            assert pattern.start_height == 3.0
            assert pattern.end_height == 68.0  # 72.0 - 4.0

    def test_generate_includes_shelf_pins_hardware(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes shelf pins in hardware."""
        config = {"count": 3}

        result = adjustable_shelf_component.generate(config, standard_context)

        pin_items = [h for h in result.hardware if h.name == "Shelf Pin"]
        assert len(pin_items) == 1
        assert pin_items[0].quantity == 12  # 3 shelves * 4 pins
        assert pin_items[0].sku == "SP-5MM-BRASS"

    def test_generate_includes_edge_banding_by_default(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes edge banding by default."""
        config = {"count": 3}

        result = adjustable_shelf_component.generate(config, standard_context)

        edge_items = [h for h in result.hardware if h.name == "Edge Banding"]
        assert len(edge_items) == 1
        assert "72.0 linear inches" in edge_items[0].notes

    def test_generate_excludes_edge_banding_when_disabled(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that edge banding is excluded when edge_band_front is False."""
        config = {"count": 3, "edge_band_front": False}

        result = adjustable_shelf_component.generate(config, standard_context)

        edge_items = [h for h in result.hardware if h.name == "Edge Banding"]
        assert len(edge_items) == 0

    def test_generate_returns_generation_result_type(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"count": 2}

        result = adjustable_shelf_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)

    def test_generate_with_explicit_positions(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates shelves at explicit positions."""
        config = {"positions": [10.0, 40.0, 65.0]}

        result = adjustable_shelf_component.generate(config, standard_context)

        assert len(result.panels) == 3
        expected_y = [0.75 + 10.0, 0.75 + 40.0, 0.75 + 65.0]
        for i, panel in enumerate(result.panels):
            assert panel.position.y == pytest.approx(expected_y[i])


class TestAdjustableShelfComponentHardware:
    """Tests for AdjustableShelfComponent.hardware()."""

    def test_hardware_returns_shelf_pins(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns shelf pins."""
        config = {"count": 3}

        result = adjustable_shelf_component.hardware(config, standard_context)

        pin_items = [h for h in result if h.name == "Shelf Pin"]
        assert len(pin_items) == 1
        assert pin_items[0].quantity == 12  # 3 * 4 pins

    def test_hardware_returns_correct_pin_details(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns correct pin SKU and notes."""
        config = {"count": 2}

        result = adjustable_shelf_component.hardware(config, standard_context)

        pin_item = next(h for h in result if h.name == "Shelf Pin")
        assert pin_item.sku == "SP-5MM-BRASS"
        assert pin_item.notes == "5mm brass shelf pins"

    def test_hardware_returns_edge_banding_by_default(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns edge banding by default."""
        config = {"count": 3}

        result = adjustable_shelf_component.hardware(config, standard_context)

        edge_items = [h for h in result if h.name == "Edge Banding"]
        assert len(edge_items) == 1
        assert "72.0 linear inches" in edge_items[0].notes

    def test_hardware_excludes_edge_banding_when_disabled(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware excludes edge banding when edge_band_front is False."""
        config = {"count": 3, "edge_band_front": False}

        result = adjustable_shelf_component.hardware(config, standard_context)

        edge_items = [h for h in result if h.name == "Edge Banding"]
        assert len(edge_items) == 0

    def test_hardware_returns_empty_for_zero_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list for zero count."""
        config = {"count": 0}

        result = adjustable_shelf_component.hardware(config, standard_context)

        assert result == []

    def test_hardware_returns_empty_for_missing_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list for missing count."""
        config: dict = {}

        result = adjustable_shelf_component.hardware(config, standard_context)

        assert result == []

    def test_hardware_with_explicit_positions(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware works with explicit positions."""
        config = {"positions": [10.0, 40.0]}

        result = adjustable_shelf_component.hardware(config, standard_context)

        pin_items = [h for h in result if h.name == "Shelf Pin"]
        assert pin_items[0].quantity == 8  # 2 * 4 pins


class TestAdjustableShelfComponentIntegration:
    """Integration tests for AdjustableShelfComponent."""

    @pytest.fixture(autouse=True)
    def ensure_adjustable_shelf_registered(self) -> None:
        """Ensure shelf.adjustable is registered for integration tests."""
        if "shelf.adjustable" not in component_registry.list():
            component_registry.register("shelf.adjustable")(AdjustableShelfComponent)

    def test_full_workflow_validate_generate_hardware(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        component_class = component_registry.get("shelf.adjustable")
        component = component_class()

        config = {"count": 4}

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 4
        assert "pin_hole_patterns" in generation.metadata

        # Hardware
        hardware = component.hardware(config, standard_context)
        pin_items = [h for h in hardware if h.name == "Shelf Pin"]
        edge_items = [h for h in hardware if h.name == "Edge Banding"]
        assert pin_items[0].quantity == 16  # 4 * 4 pins
        assert len(edge_items) == 1

    def test_adjustable_and_fixed_shelf_coexist_in_registry(self) -> None:
        """Test that both shelf.fixed and shelf.adjustable are in registry."""
        # Ensure both are registered
        if "shelf.fixed" not in component_registry.list():
            component_registry.register("shelf.fixed")(FixedShelfComponent)
        if "shelf.adjustable" not in component_registry.list():
            component_registry.register("shelf.adjustable")(AdjustableShelfComponent)

        registered = component_registry.list()
        assert "shelf.fixed" in registered
        assert "shelf.adjustable" in registered

    def test_adjustable_pins_vs_fixed_pins(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that adjustable always uses pins, fixed only with use_pins=True."""
        adjustable = AdjustableShelfComponent()
        fixed = FixedShelfComponent()
        config = {"count": 3}

        # Adjustable always has shelf pins
        adj_hardware = adjustable.hardware(config, standard_context)
        adj_pins = [h for h in adj_hardware if h.name == "Shelf Pin"]
        assert len(adj_pins) == 1

        # Fixed has no pins by default
        fix_hardware = fixed.hardware(config, standard_context)
        fix_pins = [h for h in fix_hardware if h.name == "Shelf Pin"]
        assert len(fix_pins) == 0

        # Fixed with use_pins=True has pins
        fix_hardware_pins = fixed.hardware({**config, "use_pins": True}, standard_context)
        fix_pins_enabled = [h for h in fix_hardware_pins if h.name == "Shelf Pin"]
        assert len(fix_pins_enabled) == 1


# =============================================================================
# Edge Case Tests for Both Shelf Components
# =============================================================================


class TestShelfComponentEdgeCases:
    """Edge case tests for FixedShelfComponent."""

    def test_single_shelf_at_boundary_positions(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test single shelf at exact boundary positions."""
        # Position at very top of section
        config = {"positions": [71.0]}  # Just under section height of 72
        result = shelf_component.validate(config, standard_context)
        assert result.is_valid

    def test_shelves_at_exactly_2_inch_spacing(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test shelves at exactly minimum 2 inch spacing."""
        config = {"positions": [10.0, 12.0, 14.0]}  # Exactly 2" apart
        result = shelf_component.validate(config, standard_context)
        assert result.is_valid

    def test_shelves_just_under_2_inch_spacing(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test shelves just under minimum 2 inch spacing fails."""
        config = {"positions": [10.0, 11.9]}  # 1.9" apart
        result = shelf_component.validate(config, standard_context)
        assert not result.is_valid
        assert "less than 2\" apart" in result.errors[0]

    def test_maximum_shelf_count_20(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test maximum shelf count of 20 is accepted."""
        config = {"count": 20}
        result = shelf_component.validate(config, standard_context)
        assert result.is_valid

        gen_result = shelf_component.generate(config, standard_context)
        assert len(gen_result.panels) == 20

    def test_setback_equals_section_depth(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test setback equal to section depth results in zero-depth shelf."""
        config = {"count": 1, "setback": 11.5}  # Equal to context.depth
        result = shelf_component.validate(config, standard_context)
        # This should pass validation but result in zero-depth shelf
        assert result.is_valid  # No error for zero depth currently

        gen_result = shelf_component.generate(config, standard_context)
        assert gen_result.panels[0].height == pytest.approx(0.0)

    def test_shelf_at_position_zero(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test shelf at position 0 (bottom of section)."""
        config = {"positions": [0.0]}
        result = shelf_component.validate(config, standard_context)
        assert result.is_valid

    def test_shelf_at_exact_section_height(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test shelf at exact section height (edge case)."""
        config = {"positions": [72.0]}  # Equal to section height
        result = shelf_component.validate(config, standard_context)
        # Position exactly at height is allowed
        assert result.is_valid

    def test_many_shelves_in_small_section(
        self, shelf_component: FixedShelfComponent
    ) -> None:
        """Test many shelves in small section triggers spacing issues."""
        small_context = ComponentContext(
            width=24.0,
            height=20.0,  # Small height
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=24.0,
            cabinet_depth=12.0,
        )
        # 10 shelves in 20" height: 20/11 = 1.8" spacing (less than 2")
        config = {"count": 10}
        gen_result = shelf_component.generate(config, small_context)
        # Component generates them even if spacing is tight
        assert len(gen_result.panels) == 10

    def test_float_shelf_count_rejected(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that float values for count are rejected."""
        config = {"count": 2.5}
        result = shelf_component.validate(config, standard_context)
        assert not result.is_valid

    def test_string_shelf_count_rejected(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that string values for count are rejected."""
        config = {"count": "three"}
        result = shelf_component.validate(config, standard_context)
        assert not result.is_valid

    def test_very_wide_shelf_with_thick_material_no_warning(
        self, shelf_component: FixedShelfComponent
    ) -> None:
        """Test very wide shelf with thick material doesn't warn."""
        context = ComponentContext(
            width=60.0,  # Very wide
            height=72.0,
            depth=11.5,
            material=MaterialSpec(thickness=1.0, material_type="plywood"),  # Thick
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 3}
        result = shelf_component.validate(config, context)
        assert len(result.warnings) == 0


class TestAdjustableShelfComponentEdgeCases:
    """Edge case tests for AdjustableShelfComponent."""

    def test_position_exactly_at_pin_start(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test position exactly at pin start height."""
        config = {"positions": [2.0]}  # Exactly at DEFAULT_PIN_START
        result = adjustable_shelf_component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_position_exactly_at_pin_end(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test position exactly at pin end height."""
        # pin_end = 72.0 - 2.0 = 70.0
        config = {"positions": [70.0]}
        result = adjustable_shelf_component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_position_just_below_pin_start(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test position just below pin start height warns."""
        config = {"positions": [1.99]}  # Just below DEFAULT_PIN_START of 2.0
        result = adjustable_shelf_component.validate(config, standard_context)
        assert result.is_valid  # Warning only
        assert len(result.warnings) == 1

    def test_position_just_above_pin_end(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test position just above pin end height warns."""
        config = {"positions": [70.01]}  # Just above pin_end of 70.0
        result = adjustable_shelf_component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.warnings) == 1

    def test_custom_pin_range_narrow_section(
        self, adjustable_shelf_component: AdjustableShelfComponent
    ) -> None:
        """Test custom pin range in narrow section."""
        context = ComponentContext(
            width=24.0,
            height=24.0,  # Short section
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=30.0,
            cabinet_depth=12.0,
        )
        # With 24" height and 2" default offsets, pin_end = 22"
        config = {"positions": [12.0]}  # Middle
        result = adjustable_shelf_component.validate(config, context)
        assert result.is_valid

    def test_pin_patterns_have_32mm_system_defaults(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that pin patterns use 32mm system defaults."""
        config = {"count": 1}
        result = adjustable_shelf_component.generate(config, standard_context)

        pattern = result.metadata["pin_hole_patterns"][0]
        # 37mm insets
        assert pattern.front_inset == pytest.approx(37.0 * MM_TO_INCH)
        assert pattern.back_inset == pytest.approx(37.0 * MM_TO_INCH)
        # 32mm spacing
        assert pattern.spacing == pytest.approx(32.0 * MM_TO_INCH)
        # 5mm holes
        assert pattern.hole_diameter == pytest.approx(5.0 * MM_TO_INCH)

    def test_empty_positions_list(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test empty positions list returns empty result."""
        config = {"positions": []}
        result = adjustable_shelf_component.generate(config, standard_context)
        assert len(result.panels) == 0

    def test_single_position_hardware_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test single position has correct hardware count."""
        config = {"positions": [36.0]}
        result = adjustable_shelf_component.generate(config, standard_context)

        pin_items = [h for h in result.hardware if h.name == "Shelf Pin"]
        assert pin_items[0].quantity == 4  # 1 shelf * 4 pins

    def test_many_positions_hardware_count(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test many positions have correct hardware count."""
        config = {"positions": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]}  # 6 shelves
        result = adjustable_shelf_component.generate(config, standard_context)

        pin_items = [h for h in result.hardware if h.name == "Shelf Pin"]
        assert pin_items[0].quantity == 24  # 6 shelves * 4 pins

    def test_both_edge_banding_and_pins_returned(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test both edge banding and pins are in hardware."""
        config = {"count": 3}
        result = adjustable_shelf_component.hardware(config, standard_context)

        hardware_names = {h.name for h in result}
        assert hardware_names == {"Shelf Pin", "Edge Banding"}


class TestParseShelfConfigEdgeCases:
    """Edge case tests for _parse_shelf_config helper function."""

    def test_positions_override_count(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that positions take precedence over count."""
        config = {"count": 5, "positions": [10.0, 50.0]}  # Both provided
        result = shelf_component.generate(config, standard_context)
        # Positions should win: 2 shelves instead of 5
        assert len(result.panels) == 2

    def test_negative_count_generates_empty(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that negative count (after passing validation) generates empty."""
        # Directly call generate with invalid count (bypassing validation)
        config = {"count": -5}
        result = shelf_component.generate(config, standard_context)
        # Should return empty due to count <= 0 check in _parse_shelf_config
        assert len(result.panels) == 0

    def test_setback_zero_full_depth_shelf(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test zero setback creates full-depth shelf."""
        config = {"count": 1, "setback": 0}
        result = shelf_component.generate(config, standard_context)
        # Shelf depth should equal context depth
        assert result.panels[0].height == pytest.approx(standard_context.depth)

    def test_depth_override_used_for_dado_length(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that depth override is used for dado length."""
        config = {"count": 1, "depth": 8.0}
        result = shelf_component.generate(config, standard_context)

        dado_specs = result.metadata["dado_specs"]
        for spec in dado_specs:
            assert spec.length == 8.0


class TestMetadataFieldEdgeCases:
    """Edge case tests for metadata field handling."""

    def test_fixed_shelf_metadata_contains_only_dado_specs(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that fixed shelf metadata only contains dado_specs."""
        config = {"count": 2}
        result = shelf_component.generate(config, standard_context)

        assert set(result.metadata.keys()) == {"dado_specs"}

    def test_adjustable_shelf_metadata_contains_only_pin_patterns(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that adjustable shelf metadata only contains pin_hole_patterns."""
        config = {"count": 2}
        result = adjustable_shelf_component.generate(config, standard_context)

        assert set(result.metadata.keys()) == {"pin_hole_patterns"}

    def test_empty_result_has_empty_metadata(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that empty generation result has empty metadata."""
        config = {"count": 0}
        result = shelf_component.generate(config, standard_context)

        # Default GenerationResult has empty metadata dict
        assert result.metadata == {}

    def test_dado_specs_are_dado_spec_instances(
        self, shelf_component: FixedShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that dado_specs contains DadoSpec instances."""
        config = {"count": 1}
        result = shelf_component.generate(config, standard_context)

        for spec in result.metadata["dado_specs"]:
            assert isinstance(spec, DadoSpec)

    def test_pin_patterns_are_pin_hole_pattern_instances(
        self, adjustable_shelf_component: AdjustableShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that pin_hole_patterns contains PinHolePattern instances."""
        config = {"count": 1}
        result = adjustable_shelf_component.generate(config, standard_context)

        for pattern in result.metadata["pin_hole_patterns"]:
            assert isinstance(pattern, PinHolePattern)
