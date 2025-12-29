"""Tests for KeyboardTrayComponent (desk.keyboard_tray)."""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    HardwareItem,
    ValidationResult,
    component_registry,
)
from cabinets.domain.components.desk import (
    MIN_KNEE_CLEARANCE_HEIGHT,
    KeyboardTrayComponent,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def keyboard_tray_component() -> KeyboardTrayComponent:
    """Create a KeyboardTrayComponent instance for testing."""
    return KeyboardTrayComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 48" wide desk section with adequate
    dimensions for keyboard tray testing. The height of 30" provides adequate
    knee clearance when combined with desk height configuration.
    """
    return ComponentContext(
        width=48.0,
        height=30.0,  # Standard desk height
        depth=24.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0.0, 0.0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=30.0,
        cabinet_depth=24.0,
    )


@pytest.fixture
def adequate_knee_clearance_config() -> dict:
    """Return config with adequate knee clearance for default tray settings.

    Default knee_clearance_height of 24" with MIN_CLEARANCE of 2" and
    TRAY_THICKNESS of 0.75" gives effective of 21.25" which is below 22".
    This fixture provides enough clearance (25") to pass validation.
    """
    return {"knee_clearance_height": 25.0}


class TestKeyboardTrayComponentRegistration:
    """Tests for desk.keyboard_tray component registration."""

    def test_component_is_registered_as_desk_keyboard_tray(self) -> None:
        """Test that desk.keyboard_tray is registered in the component registry."""
        assert "desk.keyboard_tray" in component_registry.list()

    def test_get_returns_keyboard_tray_component_class(self) -> None:
        """Test that registry.get returns KeyboardTrayComponent."""
        component_class = component_registry.get("desk.keyboard_tray")
        assert component_class is KeyboardTrayComponent


class TestKeyboardTrayComponentConstants:
    """Tests for KeyboardTrayComponent class constants."""

    def test_standard_width(self) -> None:
        """Test that STANDARD_WIDTH is 20.0 inches."""
        assert KeyboardTrayComponent.STANDARD_WIDTH == 20.0

    def test_standard_depth(self) -> None:
        """Test that STANDARD_DEPTH is 10.0 inches."""
        assert KeyboardTrayComponent.STANDARD_DEPTH == 10.0

    def test_min_clearance(self) -> None:
        """Test that MIN_CLEARANCE is 2.0 inches."""
        assert KeyboardTrayComponent.MIN_CLEARANCE == 2.0

    def test_tray_thickness(self) -> None:
        """Test that TRAY_THICKNESS is 0.75 inches (3/4")."""
        assert KeyboardTrayComponent.TRAY_THICKNESS == 0.75

    def test_min_effective_knee_height(self) -> None:
        """Test that MIN_EFFECTIVE_KNEE_HEIGHT is 22.0 inches."""
        assert KeyboardTrayComponent.MIN_EFFECTIVE_KNEE_HEIGHT == 22.0

    def test_enclosure_height(self) -> None:
        """Test that ENCLOSURE_HEIGHT is 3.0 inches."""
        assert KeyboardTrayComponent.ENCLOSURE_HEIGHT == 3.0

    def test_valid_slide_lengths(self) -> None:
        """Test that VALID_SLIDE_LENGTHS contains expected values."""
        expected = (10, 12, 14, 16, 18, 20)
        assert KeyboardTrayComponent.VALID_SLIDE_LENGTHS == expected


class TestKeyboardTrayComponentValidation:
    """Tests for KeyboardTrayComponent.validate()."""

    def test_validate_returns_ok_for_valid_default_config(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for config with adequate knee clearance.

        Default knee_clearance_height of 24" gives effective of 21.25" which is
        below the 22" minimum, so we need to provide adequate clearance.
        """
        config = {"knee_clearance_height": 25.0}  # Gives effective of 22.25"

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_valid_custom_config(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid custom configuration."""
        config = {
            "width": 22.0,
            "depth": 12.0,
            "slide_length": 14,
            "knee_clearance_height": 26.0,
        }

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_errors_when_knee_clearance_below_minimum(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate errors when effective knee clearance < 22"."""
        # With knee_height=24, tray_clearance=2, tray_thickness=0.75
        # effective = 24 - 2 - 0.75 = 21.25" (below 22")
        config = {
            "knee_clearance_height": 24.0,
            "tray_clearance": 2.0,
        }

        result = keyboard_tray_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("knee clearance" in err and "21.2" in err for err in result.errors)

    def test_validate_passes_when_knee_clearance_at_minimum(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate passes when effective knee clearance exactly 22"."""
        # effective = 24.75 - 2.0 - 0.75 = 22.0"
        config = {
            "knee_clearance_height": 24.75,
            "tray_clearance": 2.0,
        }

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_errors_when_tray_width_exceeds_desk_width(
        self, keyboard_tray_component: KeyboardTrayComponent
    ) -> None:
        """Test that validate errors when tray_width > desk width."""
        narrow_context = ComponentContext(
            width=18.0,  # Narrow desk
            height=30.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.0, 0.0),
            section_index=0,
            cabinet_width=18.0,
            cabinet_height=30.0,
            cabinet_depth=24.0,
        )
        config = {"width": 20.0}  # Default 20" exceeds 18" desk width

        result = keyboard_tray_component.validate(config, narrow_context)

        assert not result.is_valid
        assert any("exceeds desk width" in err for err in result.errors)

    def test_validate_warns_on_shallow_depth(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate warns when depth < 8 inches."""
        config = {"depth": 7.0, "knee_clearance_height": 25.0}

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid  # Warning, not error
        assert len(result.warnings) > 0
        assert any("too shallow" in warn for warn in result.warnings)

    def test_validate_warns_on_deep_tray(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate warns when depth > 14 inches."""
        config = {"depth": 15.0, "knee_clearance_height": 25.0}

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid  # Warning, not error
        assert len(result.warnings) > 0
        assert any("unusually deep" in warn for warn in result.warnings)

    def test_validate_no_warning_for_standard_depth_range(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate has no warnings for depth in 8-14 inch range."""
        for depth in [8.0, 10.0, 12.0, 14.0]:
            config = {"depth": depth, "knee_clearance_height": 25.0}

            result = keyboard_tray_component.validate(config, standard_context)

            assert result.is_valid
            assert len(result.warnings) == 0, f"Unexpected warning for depth {depth}"

    def test_validate_errors_on_invalid_slide_length(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate errors for invalid slide_length."""
        config = {"slide_length": 22}  # Not in valid list

        result = keyboard_tray_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("Invalid slide_length" in err for err in result.errors)

    def test_validate_accepts_all_valid_slide_lengths(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate accepts all valid slide lengths."""
        for slide_length in KeyboardTrayComponent.VALID_SLIDE_LENGTHS:
            config = {"slide_length": slide_length, "knee_clearance_height": 25.0}

            result = keyboard_tray_component.validate(config, standard_context)

            assert result.is_valid, f"Failed for slide_length: {slide_length}"

    def test_validate_multiple_errors(
        self, keyboard_tray_component: KeyboardTrayComponent
    ) -> None:
        """Test that multiple validation errors are all reported."""
        narrow_context = ComponentContext(
            width=15.0,
            height=30.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.0, 0.0),
            section_index=0,
            cabinet_width=15.0,
            cabinet_height=30.0,
            cabinet_depth=24.0,
        )
        config = {
            "width": 20.0,  # Exceeds 15" width
            "knee_clearance_height": 24.0,  # Insufficient clearance
            "slide_length": 25,  # Invalid slide length
        }

        result = keyboard_tray_component.validate(config, narrow_context)

        assert not result.is_valid
        assert len(result.errors) >= 3


class TestKeyboardTrayComponentGeneration:
    """Tests for KeyboardTrayComponent.generate()."""

    def test_generate_returns_generation_result(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)

    def test_generate_creates_keyboard_tray_panel(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates a KEYBOARD_TRAY panel."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        tray_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_TRAY]
        assert len(tray_panels) == 1

    def test_generate_tray_dimensions_default(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray panel has default dimensions (20" x 10")."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        tray_panel = next(p for p in result.panels if p.panel_type == PanelType.KEYBOARD_TRAY)
        assert tray_panel.width == KeyboardTrayComponent.STANDARD_WIDTH  # 20"
        assert tray_panel.height == KeyboardTrayComponent.STANDARD_DEPTH  # 10"

    def test_generate_tray_dimensions_custom(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray panel has custom dimensions when specified."""
        config = {"width": 24.0, "depth": 12.0}

        result = keyboard_tray_component.generate(config, standard_context)

        tray_panel = next(p for p in result.panels if p.panel_type == PanelType.KEYBOARD_TRAY)
        assert tray_panel.width == 24.0
        assert tray_panel.height == 12.0

    def test_generate_tray_material_is_3_4_inch(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray panel uses 3/4 inch material."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        tray_panel = next(p for p in result.panels if p.panel_type == PanelType.KEYBOARD_TRAY)
        assert tray_panel.material.thickness == 0.75

    def test_generate_tray_metadata(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that tray panel has correct metadata."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        tray_panel = next(p for p in result.panels if p.panel_type == PanelType.KEYBOARD_TRAY)
        assert tray_panel.metadata["component"] == "desk.keyboard_tray"
        assert tray_panel.metadata["is_keyboard_tray"] is True

    def test_generate_no_enclosure_panels_by_default(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that no enclosure panels are created by default."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        enclosure_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_ENCLOSURE]
        assert len(enclosure_panels) == 0
        assert len(result.panels) == 1  # Only tray panel

    def test_generate_enclosure_panels_when_enclosed(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosure panels are created when enclosed=True."""
        config = {"enclosed": True}

        result = keyboard_tray_component.generate(config, standard_context)

        enclosure_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_ENCLOSURE]
        assert len(enclosure_panels) == 2  # Left and right
        assert len(result.panels) == 3  # Tray + 2 enclosure

    def test_generate_enclosure_panel_dimensions(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosure panels have correct dimensions."""
        config = {"enclosed": True, "depth": 10.0}

        result = keyboard_tray_component.generate(config, standard_context)

        enclosure_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_ENCLOSURE]
        for panel in enclosure_panels:
            assert panel.width == 10.0  # Runs front to back (depth)
            assert panel.height == KeyboardTrayComponent.ENCLOSURE_HEIGHT  # 3"

    def test_generate_enclosure_material_is_1_2_inch(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosure panels use 1/2 inch material."""
        config = {"enclosed": True}

        result = keyboard_tray_component.generate(config, standard_context)

        enclosure_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_ENCLOSURE]
        for panel in enclosure_panels:
            assert panel.material.thickness == 0.5

    def test_generate_enclosure_metadata(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosure panels have correct metadata."""
        config = {"enclosed": True}

        result = keyboard_tray_component.generate(config, standard_context)

        enclosure_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_ENCLOSURE]
        sides = set()
        for panel in enclosure_panels:
            assert panel.metadata["component"] == "desk.keyboard_tray"
            assert panel.metadata["is_enclosure"] is True
            sides.add(panel.metadata["side"])
        assert sides == {"left", "right"}

    def test_generate_metadata_includes_enclosed_and_slide_length(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that result metadata includes enclosed and slide_length."""
        config = {"enclosed": True, "slide_length": 16}

        result = keyboard_tray_component.generate(config, standard_context)

        assert result.metadata["enclosed"] is True
        assert result.metadata["slide_length"] == 16


class TestKeyboardTrayComponentHardware:
    """Tests for KeyboardTrayComponent hardware generation."""

    def test_generate_includes_hardware(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes hardware items."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        assert len(result.hardware) > 0

    def test_generate_includes_keyboard_slide(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes keyboard slide."""
        config = {"slide_length": 14}

        result = keyboard_tray_component.generate(config, standard_context)

        slide_items = [h for h in result.hardware if "Keyboard Slide" in h.name]
        assert len(slide_items) == 1
        assert slide_items[0].quantity == 1
        assert '14"' in slide_items[0].name
        assert slide_items[0].sku == "KB-SLIDE-14"
        assert "pair" in slide_items[0].notes.lower()

    def test_generate_slide_length_in_hardware_name(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that slide length is reflected in hardware name."""
        for slide_length in [10, 14, 18]:
            config = {"slide_length": slide_length}

            result = keyboard_tray_component.generate(config, standard_context)

            slide_item = next(h for h in result.hardware if "Keyboard Slide" in h.name)
            assert f'{slide_length}"' in slide_item.name
            assert slide_item.sku == f"KB-SLIDE-{slide_length}"

    def test_generate_includes_mounting_screws(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes mounting screws."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        screw_items = [h for h in result.hardware if "Screw" in h.name]
        assert len(screw_items) == 1
        assert screw_items[0].quantity == 8
        assert screw_items[0].sku == "SCREW-6-1/2-PAN"

    def test_generate_no_wrist_rest_by_default(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that no wrist rest is included by default."""
        config = {}

        result = keyboard_tray_component.generate(config, standard_context)

        wrist_rest_items = [h for h in result.hardware if "Wrist Rest" in h.name]
        assert len(wrist_rest_items) == 0

    def test_generate_includes_wrist_rest_when_enabled(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that wrist rest is included when wrist_rest=True."""
        config = {"wrist_rest": True}

        result = keyboard_tray_component.generate(config, standard_context)

        wrist_rest_items = [h for h in result.hardware if "Wrist Rest" in h.name]
        assert len(wrist_rest_items) == 1
        assert wrist_rest_items[0].quantity == 1
        assert wrist_rest_items[0].sku == "WRIST-REST-20"

    def test_hardware_method_returns_list(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() method returns a list."""
        config = {}

        result = keyboard_tray_component.hardware(config, standard_context)

        assert isinstance(result, list)
        assert all(isinstance(item, HardwareItem) for item in result)

    def test_hardware_method_matches_generate_hardware(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns same items as generate().hardware."""
        config = {"wrist_rest": True}

        generate_result = keyboard_tray_component.generate(config, standard_context)
        hardware_result = keyboard_tray_component.hardware(config, standard_context)

        assert len(hardware_result) == len(generate_result.hardware)

    def test_hardware_count_without_wrist_rest(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test hardware count without wrist rest (slide + screws = 2 items)."""
        config = {"wrist_rest": False}

        result = keyboard_tray_component.hardware(config, standard_context)

        assert len(result) == 2

    def test_hardware_count_with_wrist_rest(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test hardware count with wrist rest (slide + screws + wrist rest = 3 items)."""
        config = {"wrist_rest": True}

        result = keyboard_tray_component.hardware(config, standard_context)

        assert len(result) == 3


class TestKeyboardTrayComponentIntegration:
    """Integration tests for KeyboardTrayComponent."""

    def test_full_workflow_validate_generate_hardware(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        # Get component from registry
        component_class = component_registry.get("desk.keyboard_tray")
        component = component_class()

        config = {
            "width": 22.0,
            "depth": 11.0,
            "slide_length": 14,
            "enclosed": True,
            "wrist_rest": True,
            "knee_clearance_height": 25.0,  # Adequate knee clearance
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 3  # Tray + 2 enclosure
        assert generation.metadata["enclosed"] is True

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 3  # Slide + screws + wrist rest

    def test_keyboard_tray_with_different_slide_lengths(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test keyboard tray with all valid slide lengths."""
        for slide_length in KeyboardTrayComponent.VALID_SLIDE_LENGTHS:
            config = {"slide_length": slide_length, "knee_clearance_height": 25.0}

            validation = keyboard_tray_component.validate(config, standard_context)
            assert validation.is_valid, f"Failed validation for slide_length: {slide_length}"

            generation = keyboard_tray_component.generate(config, standard_context)
            assert generation.metadata["slide_length"] == slide_length


class TestKeyboardTrayComponentEdgeCases:
    """Edge case tests for KeyboardTrayComponent."""

    def test_minimum_depth_boundary(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test keyboard tray at minimum depth boundary (8")."""
        config = {"depth": 8.0, "knee_clearance_height": 25.0}

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 0

    def test_maximum_depth_boundary(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test keyboard tray at maximum depth boundary (14")."""
        config = {"depth": 14.0, "knee_clearance_height": 25.0}

        result = keyboard_tray_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 0

    def test_tray_width_exactly_matches_desk_width(
        self, keyboard_tray_component: KeyboardTrayComponent
    ) -> None:
        """Test that tray width can equal desk width."""
        context = ComponentContext(
            width=20.0,
            height=30.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.0, 0.0),
            section_index=0,
            cabinet_width=20.0,
            cabinet_height=30.0,
            cabinet_depth=24.0,
        )
        config = {"width": 20.0, "knee_clearance_height": 25.0}

        result = keyboard_tray_component.validate(config, context)

        assert result.is_valid

    def test_effective_knee_clearance_calculation(
        self, keyboard_tray_component: KeyboardTrayComponent, standard_context: ComponentContext
    ) -> None:
        """Test effective knee clearance calculation with various inputs."""
        # effective = knee_height - tray_clearance - tray_thickness (0.75)
        test_cases = [
            # (knee_height, tray_clearance, expected_effective, should_pass)
            (26.0, 2.0, 23.25, True),  # 26 - 2 - 0.75 = 23.25 > 22
            (25.0, 2.0, 22.25, True),  # 25 - 2 - 0.75 = 22.25 > 22
            (24.75, 2.0, 22.0, True),  # 24.75 - 2 - 0.75 = 22.0 = 22
            (24.5, 2.0, 21.75, False),  # 24.5 - 2 - 0.75 = 21.75 < 22
            (24.0, 2.0, 21.25, False),  # 24 - 2 - 0.75 = 21.25 < 22
        ]

        for knee_height, tray_clearance, expected, should_pass in test_cases:
            config = {
                "knee_clearance_height": knee_height,
                "tray_clearance": tray_clearance,
            }

            result = keyboard_tray_component.validate(config, standard_context)

            assert result.is_valid == should_pass, (
                f"Failed for knee={knee_height}, clearance={tray_clearance}, "
                f"expected effective={expected}, should_pass={should_pass}"
            )

    def test_enclosure_position_offset(
        self, keyboard_tray_component: KeyboardTrayComponent
    ) -> None:
        """Test that right enclosure panel is offset by tray width."""
        context = ComponentContext(
            width=48.0,
            height=30.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(5.0, 10.0),  # Non-zero position
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=30.0,
            cabinet_depth=24.0,
        )
        config = {"enclosed": True, "width": 20.0}

        result = keyboard_tray_component.generate(config, context)

        enclosure_panels = [p for p in result.panels if p.panel_type == PanelType.KEYBOARD_ENCLOSURE]
        right_panel = next(p for p in enclosure_panels if p.metadata["side"] == "right")

        # Right panel should be offset by tray width from context position
        assert right_panel.position.x == context.position.x + 20.0
