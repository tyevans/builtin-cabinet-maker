"""Component registry for managing cabinet component types."""

from __future__ import annotations

from typing import Callable, TypeVar

from .protocol import Component

C = TypeVar("C", bound=Component)


class ComponentRegistry:
    """Singleton registry for component types.

    The ComponentRegistry is the central registry for all component types
    in the system. It provides a decorator-based registration mechanism
    and lookup by component ID.

    Component IDs must follow the format 'category.type' or 'category.type.variant':
    - 'shelf.fixed' - A fixed shelf component
    - 'shelf.adjustable' - An adjustable shelf component
    - 'door.cabinet.inset' - An inset cabinet door variant

    Example:
        @component_registry.register("shelf.fixed")
        class FixedShelf:
            def validate(self, config, context):
                ...

            def generate(self, config, context):
                ...

            def hardware(self, config, context):
                ...

        # Later, retrieve the component class
        shelf_cls = component_registry.get("shelf.fixed")
        shelf = shelf_cls()
    """

    _instance: ComponentRegistry | None = None
    _components: dict[str, type[Component]]

    def __new__(cls) -> ComponentRegistry:
        """Create or return the singleton instance.

        Returns:
            The singleton ComponentRegistry instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components = {}
        return cls._instance

    def register(self, component_id: str) -> Callable[[type[C]], type[C]]:
        """Decorator to register a component class.

        Registers a component class with the given component ID. The ID must
        be unique and follow the format 'category.type' or 'category.type.variant'.

        Args:
            component_id: Unique identifier for the component type.

        Returns:
            A decorator function that registers the class and returns it unchanged.

        Raises:
            ValueError: If component_id is already registered or has invalid format.

        Example:
            @component_registry.register("drawer.standard")
            class StandardDrawer:
                ...
        """

        def decorator(cls: type[C]) -> type[C]:
            if component_id in self._components:
                raise ValueError(f"Component '{component_id}' already registered")
            self._validate_id(component_id)
            self._components[component_id] = cls
            return cls

        return decorator

    def get(self, component_id: str) -> type[Component]:
        """Get a component class by ID.

        Retrieves the component class registered under the given ID.

        Args:
            component_id: The component identifier to look up.

        Returns:
            The component class registered under the given ID.

        Raises:
            KeyError: If no component is registered with the given ID.
        """
        if component_id not in self._components:
            raise KeyError(f"Unknown component: {component_id}")
        return self._components[component_id]

    def list(self) -> list[str]:
        """List all registered component IDs.

        Returns:
            A sorted list of all registered component IDs.
        """
        return sorted(self._components.keys())

    def _validate_id(self, component_id: str) -> None:
        """Validate component ID format.

        Component IDs must be in the format 'category.type' or
        'category.type.variant'. This means they must have 2 or 3
        dot-separated parts.

        Args:
            component_id: The component ID to validate.

        Raises:
            ValueError: If the ID format is invalid.
        """
        parts = component_id.split(".")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"Invalid component ID '{component_id}': "
                "must be 'category.type' or 'category.type.variant'"
            )

    def clear(self) -> None:
        """Clear all registered components.

        This method is intended for testing only. It removes all registered
        components from the registry, allowing tests to start with a clean
        state.

        Warning:
            Do not use in production code. This will break any code that
            depends on registered components.
        """
        self._components = {}


# Singleton instance for convenient access
component_registry = ComponentRegistry()
