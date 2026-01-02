"""Tests for ComponentRegistry and component registration."""

from __future__ import annotations

from typing import Any

import pytest

from cabinets.domain.components import (
    ComponentContext,
    ComponentRegistry,
    GenerationResult,
    HardwareItem,
    ValidationResult,
    component_registry,
)
from cabinets.domain.value_objects import MaterialSpec, Position


class TestComponentRegistrySingleton:
    """Tests for ComponentRegistry singleton behavior."""

    def test_registry_is_singleton(self) -> None:
        """Test that ComponentRegistry returns the same instance."""
        registry1 = ComponentRegistry()
        registry2 = ComponentRegistry()

        assert registry1 is registry2

    def test_module_level_registry_is_same_instance(self) -> None:
        """Test that component_registry is the same as ComponentRegistry()."""
        registry = ComponentRegistry()

        assert component_registry is registry


class TestComponentRegistration:
    """Tests for component registration via decorator."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> None:
        """Clear the registry before each test."""
        component_registry.clear()

    def test_register_component_with_decorator(self) -> None:
        """Test registering a component using the decorator."""

        @component_registry.register("shelf.fixed")
        class FixedShelf:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        assert "shelf.fixed" in component_registry.list()

    def test_register_component_with_three_part_id(self) -> None:
        """Test registering a component with category.type.variant format."""

        @component_registry.register("door.cabinet.inset")
        class InsetDoor:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        assert "door.cabinet.inset" in component_registry.list()

    def test_decorator_returns_original_class(self) -> None:
        """Test that the decorator returns the class unchanged."""

        @component_registry.register("divider.vertical")
        class VerticalDivider:
            custom_attribute = "test"

            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        assert VerticalDivider.custom_attribute == "test"

    def test_duplicate_registration_raises_value_error(self) -> None:
        """Test that registering the same ID twice raises ValueError."""

        @component_registry.register("shelf.adjustable")
        class AdjustableShelf:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        with pytest.raises(
            ValueError, match="Component 'shelf.adjustable' already registered"
        ):

            @component_registry.register("shelf.adjustable")
            class AnotherAdjustableShelf:
                def validate(
                    self, config: dict[str, Any], context: ComponentContext
                ) -> ValidationResult:
                    return ValidationResult.ok()

                def generate(
                    self, config: dict[str, Any], context: ComponentContext
                ) -> GenerationResult:
                    return GenerationResult()

                def hardware(
                    self, config: dict[str, Any], context: ComponentContext
                ) -> list[HardwareItem]:
                    return []


class TestComponentIdValidation:
    """Tests for component ID format validation."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> None:
        """Clear the registry before each test."""
        component_registry.clear()

    def test_invalid_id_single_part_raises_value_error(self) -> None:
        """Test that a single-part ID raises ValueError."""
        with pytest.raises(
            ValueError, match="must be 'category.type' or 'category.type.variant'"
        ):

            @component_registry.register("shelf")
            class InvalidShelf:
                pass

    def test_invalid_id_four_parts_raises_value_error(self) -> None:
        """Test that a four-part ID raises ValueError."""
        with pytest.raises(
            ValueError, match="must be 'category.type' or 'category.type.variant'"
        ):

            @component_registry.register("shelf.fixed.standard.v2")
            class InvalidShelf:
                pass

    def test_invalid_id_empty_raises_value_error(self) -> None:
        """Test that an empty ID raises ValueError."""
        with pytest.raises(
            ValueError, match="must be 'category.type' or 'category.type.variant'"
        ):

            @component_registry.register("")
            class InvalidShelf:
                pass

    def test_valid_two_part_id_passes_validation(self) -> None:
        """Test that a two-part ID is valid."""

        @component_registry.register("drawer.standard")
        class StandardDrawer:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        assert "drawer.standard" in component_registry.list()

    def test_valid_three_part_id_passes_validation(self) -> None:
        """Test that a three-part ID is valid."""

        @component_registry.register("hinge.european.soft_close")
        class SoftCloseHinge:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        assert "hinge.european.soft_close" in component_registry.list()


class TestComponentRetrieval:
    """Tests for retrieving registered components."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> None:
        """Clear the registry before each test."""
        component_registry.clear()

    def test_get_returns_registered_component(self) -> None:
        """Test that get() returns the registered component class."""

        @component_registry.register("panel.back")
        class BackPanel:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        retrieved = component_registry.get("panel.back")

        assert retrieved is BackPanel

    def test_get_unknown_id_raises_key_error(self) -> None:
        """Test that get() with unknown ID raises KeyError."""
        with pytest.raises(KeyError, match="Unknown component: nonexistent.component"):
            component_registry.get("nonexistent.component")

    def test_get_returns_instantiable_class(self) -> None:
        """Test that the retrieved class can be instantiated."""

        @component_registry.register("shelf.glass")
        class GlassShelf:
            def __init__(self) -> None:
                self.name = "Glass Shelf"

            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        shelf_class = component_registry.get("shelf.glass")
        instance = shelf_class()

        assert instance.name == "Glass Shelf"


class TestComponentList:
    """Tests for listing registered components."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> None:
        """Clear the registry before each test."""
        component_registry.clear()

    def test_list_returns_empty_list_when_no_components(self) -> None:
        """Test that list() returns empty list when registry is empty."""
        result = component_registry.list()

        assert result == []

    def test_list_returns_all_registered_ids(self) -> None:
        """Test that list() returns all registered component IDs."""

        @component_registry.register("shelf.fixed")
        class FixedShelf:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        @component_registry.register("drawer.standard")
        class StandardDrawer:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        result = component_registry.list()

        assert "shelf.fixed" in result
        assert "drawer.standard" in result
        assert len(result) == 2

    def test_list_returns_sorted_ids(self) -> None:
        """Test that list() returns IDs in sorted order."""

        @component_registry.register("zebra.stripe")
        class ZebraStripe:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        @component_registry.register("alpha.first")
        class AlphaFirst:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        @component_registry.register("middle.component")
        class MiddleComponent:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        result = component_registry.list()

        assert result == ["alpha.first", "middle.component", "zebra.stripe"]


class TestRegistryClear:
    """Tests for clearing the registry."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> None:
        """Clear the registry before each test."""
        component_registry.clear()

    def test_clear_removes_all_components(self) -> None:
        """Test that clear() removes all registered components."""

        @component_registry.register("shelf.fixed")
        class FixedShelf:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        @component_registry.register("drawer.standard")
        class StandardDrawer:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return []

        assert len(component_registry.list()) == 2

        component_registry.clear()

        assert component_registry.list() == []

    def test_clear_allows_re_registration(self) -> None:
        """Test that clear() allows the same ID to be registered again."""

        @component_registry.register("shelf.fixed")
        class FixedShelf1:
            pass

        component_registry.clear()

        # Should not raise ValueError
        @component_registry.register("shelf.fixed")
        class FixedShelf2:
            pass

        assert "shelf.fixed" in component_registry.list()


class TestComponentProtocolIntegration:
    """Tests for component protocol integration with registry."""

    @pytest.fixture(autouse=True)
    def clear_registry(self) -> None:
        """Clear the registry before each test."""
        component_registry.clear()

    def test_registered_component_satisfies_protocol(self) -> None:
        """Test that a registered component can be used as Component protocol."""

        @component_registry.register("shelf.test")
        class TestShelf:
            def validate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> ValidationResult:
                if config.get("width", 0) < 6:
                    return ValidationResult.fail(["Width must be at least 6 inches"])
                return ValidationResult.ok()

            def generate(
                self, config: dict[str, Any], context: ComponentContext
            ) -> GenerationResult:
                return GenerationResult()

            def hardware(
                self, config: dict[str, Any], context: ComponentContext
            ) -> list[HardwareItem]:
                return [HardwareItem(name="Shelf Pin", quantity=4)]

        shelf_class = component_registry.get("shelf.test")
        shelf = shelf_class()

        # Create a test context
        context = ComponentContext(
            width=24.0,
            height=0.75,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        # Test validate
        result = shelf.validate({"width": 24}, context)
        assert result.is_valid

        invalid_result = shelf.validate({"width": 4}, context)
        assert not invalid_result.is_valid
        assert "Width must be at least 6 inches" in invalid_result.errors

        # Test generate
        gen_result = shelf.generate({}, context)
        assert isinstance(gen_result, GenerationResult)

        # Test hardware
        hardware = shelf.hardware({}, context)
        assert len(hardware) == 1
        assert hardware[0].name == "Shelf Pin"
        assert hardware[0].quantity == 4
