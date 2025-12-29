"""Protocol definition for cabinet components."""

from __future__ import annotations

from typing import Any, Protocol

from .context import ComponentContext
from .results import GenerationResult, HardwareItem, ValidationResult


class Component(Protocol):
    """Protocol for cabinet components.

    This protocol defines the interface that all component implementations
    must satisfy. Components are responsible for validating their configuration,
    generating panels and cut pieces, and specifying required hardware.

    Components are registered with the ComponentRegistry using a component ID
    that follows the format 'category.type' or 'category.type.variant'.

    Example:
        @component_registry.register("shelf.fixed")
        class FixedShelf:
            def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
                # Validate shelf configuration
                ...

            def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
                # Generate shelf panels and cut pieces
                ...

            def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
                # Return shelf pins or brackets
                ...
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate component configuration.

        Checks that the provided configuration is valid for this component type,
        given the context in which it will be generated. Should check for:
        - Required configuration keys
        - Valid value ranges
        - Compatibility with context dimensions
        - Any other component-specific constraints

        Args:
            config: Component configuration dictionary.
            context: Context providing dimensions and adjacency information.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        ...

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate panels, pieces, and hardware for this component.

        Creates all the physical outputs for the component: Panel objects
        for 3D visualization, CutPiece objects for the cut list, and
        HardwareItem objects for required hardware.

        Should only be called after validate() returns a successful result.

        Args:
            config: Component configuration dictionary.
            context: Context providing dimensions and adjacency information.

        Returns:
            GenerationResult containing panels, cut pieces, and hardware.
        """
        ...

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for this component.

        Lists all hardware items (screws, hinges, brackets, shelf pins, etc.)
        required for this component. This is separate from generate() to
        allow hardware bills of material to be generated without full
        component generation.

        Args:
            config: Component configuration dictionary.
            context: Context providing dimensions and adjacency information.

        Returns:
            List of HardwareItem objects required by this component.
        """
        ...
