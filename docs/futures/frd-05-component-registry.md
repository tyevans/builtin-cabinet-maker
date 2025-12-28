# FRD-05: Component Registry Architecture

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** High (Foundation for all component types)
**Depends On:** FRD-01 (Configuration Schema), FRD-04 (Variable Sections)

---

## Problem Statement

The current codebase generates shelves directly in `LayoutCalculator.generate_cabinet()`. Adding new component types (doors, drawers, cubbies) would require modifying this core class, violating Open/Closed Principle. A plugin-style component system is needed where:

- New components can be added without modifying existing code
- Components self-register via decorators
- Generation logic is encapsulated per component type
- Hardware requirements are tracked per component

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| Extensible architecture | New component added with single file, zero changes to existing code |
| Type-safe contracts | `Component` protocol enforced via static typing |
| Clear component IDs | `category.type.variant` naming convention followed |
| Hardware tracking | Each component reports its hardware requirements |
| Validation separation | Component validates its own config before generation |

---

## Scope

### In Scope
- `Component` protocol definition
- `ComponentRegistry` singleton with decorator-based registration
- `ComponentContext` dataclass for generation context
- `GenerationResult` and `ValidationResult` value objects
- `HardwareItem` value object for hardware tracking
- Base shelf component implementation as reference

### Out of Scope
- Actual door/drawer/cubby implementations (future FRDs)
- Hardware inventory management
- Component dependency resolution
- Visual component editor

---

## Functional Requirements

### FR-01: Component Protocol

- **FR-01.1**: `Component` SHALL be a `typing.Protocol` with three methods
- **FR-01.2**: `validate(config, context) -> ValidationResult` SHALL validate component config
- **FR-01.3**: `generate(config, context) -> GenerationResult` SHALL produce panels and pieces
- **FR-01.4**: `hardware(config, context) -> list[HardwareItem]` SHALL return hardware list
- **FR-01.5**: All methods SHALL be stateless (no instance state between calls)

### FR-02: Component Registry

- **FR-02.1**: Registry SHALL be a singleton accessible via `component_registry`
- **FR-02.2**: `@component_registry.register("id")` decorator SHALL register components
- **FR-02.3**: `registry.get("id")` SHALL return component or raise `KeyError`
- **FR-02.4**: `registry.list()` SHALL return all registered component IDs
- **FR-02.5**: Duplicate registration SHALL raise `ValueError`

### FR-03: Component ID Convention

- **FR-03.1**: IDs SHALL follow `category.type.variant` pattern
- **FR-03.2**: Category: `shelf`, `door`, `drawer`, `cubby`, `divider`
- **FR-03.3**: Type examples: `fixed`, `adjustable`, `hinged`, `sliding`
- **FR-03.4**: Variant examples: `overlay`, `inset`, `standard`
- **FR-03.5**: Minimal IDs allowed: `category.type` (e.g., `shelf.fixed`)

### FR-04: ComponentContext

- **FR-04.1**: Context SHALL include section dimensions (`width`, `height`, `depth`)
- **FR-04.2**: Context SHALL include material specifications
- **FR-04.3**: Context SHALL include adjacent component references (left, right, above, below)
- **FR-04.4**: Context SHALL include section position within cabinet

### FR-05: GenerationResult

- **FR-05.1**: Result SHALL contain `list[Panel]` for structural panels
- **FR-05.2**: Result SHALL contain `list[CutPiece]` for non-panel pieces
- **FR-05.3**: Result SHALL contain `list[HardwareItem]` for required hardware
- **FR-05.4**: Result SHALL be immutable (frozen dataclass)

### FR-06: ValidationResult

- **FR-06.1**: Result SHALL contain `is_valid: bool`
- **FR-06.2**: Result SHALL contain `errors: list[str]` for blocking issues
- **FR-06.3**: Result SHALL contain `warnings: list[str]` for advisories
- **FR-06.4**: Empty errors list implies `is_valid = True`

---

## Data Models

### Component Protocol

```python
# src/cabinets/domain/components/protocol.py

from typing import Protocol, Any
from ..value_objects import MaterialSpec, Position
from ..entities import Panel
from .results import GenerationResult, ValidationResult, HardwareItem

class ComponentContext:
    """Context provided to components during generation."""
    width: float
    height: float
    depth: float
    material: MaterialSpec
    position: Position
    section_index: int
    adjacent_left: str | None   # Component ID or None
    adjacent_right: str | None
    adjacent_above: str | None
    adjacent_below: str | None

class Component(Protocol):
    """Protocol for cabinet components."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        """Validate component configuration."""
        ...

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        """Generate panels, pieces, and hardware."""
        ...

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        """Return hardware requirements."""
        ...
```

### Result Value Objects

```python
# src/cabinets/domain/components/results.py

from dataclasses import dataclass, field
from ..entities import Panel
from ..value_objects import CutPiece

@dataclass(frozen=True)
class HardwareItem:
    """Hardware required by a component."""
    name: str
    quantity: int
    sku: str | None = None
    notes: str | None = None

@dataclass(frozen=True)
class ValidationResult:
    """Result of component validation."""
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @classmethod
    def ok(cls, warnings: list[str] | None = None) -> "ValidationResult":
        return cls(warnings=tuple(warnings or []))

    @classmethod
    def fail(cls, errors: list[str], warnings: list[str] | None = None) -> "ValidationResult":
        return cls(errors=tuple(errors), warnings=tuple(warnings or []))

@dataclass(frozen=True)
class GenerationResult:
    """Result of component generation."""
    panels: tuple[Panel, ...] = field(default_factory=tuple)
    cut_pieces: tuple[CutPiece, ...] = field(default_factory=tuple)
    hardware: tuple[HardwareItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_panels(cls, panels: list[Panel]) -> "GenerationResult":
        return cls(panels=tuple(panels))
```

### ComponentContext

```python
# src/cabinets/domain/components/context.py

from dataclasses import dataclass
from ..value_objects import MaterialSpec, Position

@dataclass(frozen=True)
class ComponentContext:
    """Immutable context for component generation."""
    width: float
    height: float
    depth: float
    material: MaterialSpec
    position: Position
    section_index: int
    cabinet_width: float
    cabinet_height: float
    cabinet_depth: float
    adjacent_left: str | None = None
    adjacent_right: str | None = None
    adjacent_above: str | None = None
    adjacent_below: str | None = None
```

### Component Registry

```python
# src/cabinets/domain/components/registry.py

from typing import TypeVar, Callable
from .protocol import Component

C = TypeVar("C", bound=Component)

class ComponentRegistry:
    """Singleton registry for component types."""

    _instance: "ComponentRegistry | None" = None
    _components: dict[str, type[Component]]

    def __new__(cls) -> "ComponentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components = {}
        return cls._instance

    def register(self, component_id: str) -> Callable[[type[C]], type[C]]:
        """Decorator to register a component class."""
        def decorator(cls: type[C]) -> type[C]:
            if component_id in self._components:
                raise ValueError(f"Component '{component_id}' already registered")
            self._validate_id(component_id)
            self._components[component_id] = cls
            return cls
        return decorator

    def get(self, component_id: str) -> type[Component]:
        """Get a component class by ID."""
        if component_id not in self._components:
            raise KeyError(f"Unknown component: {component_id}")
        return self._components[component_id]

    def list(self) -> list[str]:
        """List all registered component IDs."""
        return sorted(self._components.keys())

    def _validate_id(self, component_id: str) -> None:
        """Validate component ID format."""
        parts = component_id.split(".")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(
                f"Invalid component ID '{component_id}': "
                "must be 'category.type' or 'category.type.variant'"
            )

# Singleton instance
component_registry = ComponentRegistry()
```

---

## Reference Implementation: Fixed Shelf

```python
# src/cabinets/domain/components/shelf.py

from typing import Any
from ..entities import Panel
from ..value_objects import PanelType
from .protocol import Component
from .context import ComponentContext
from .results import GenerationResult, ValidationResult, HardwareItem
from .registry import component_registry

@component_registry.register("shelf.fixed")
class FixedShelfComponent:
    """Fixed shelf component - non-adjustable shelves."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors = []
        warnings = []

        count = config.get("count", 0)
        if not isinstance(count, int) or count < 0:
            errors.append("shelf count must be non-negative integer")
        if count > 20:
            errors.append("shelf count exceeds maximum of 20")

        # Advisory for wide shelves
        if context.width > 36 and context.material.thickness <= 0.75:
            warnings.append(
                f"Shelf span {context.width:.1f}\" exceeds recommended 36\" "
                "for 3/4\" material - consider center support"
            )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        count = config.get("count", 0)
        if count == 0:
            return GenerationResult()

        panels = []
        spacing = context.height / (count + 1)

        for i in range(count):
            shelf_y = context.position.y + spacing * (i + 1)
            panels.append(Panel(
                panel_type=PanelType.SHELF,
                width=context.width,
                height=context.depth,
                material=context.material,
                position=Position(context.position.x, shelf_y),
            ))

        return GenerationResult.from_panels(panels)

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        # Fixed shelves - no hardware needed (dado joints or shelf pins)
        count = config.get("count", 0)
        if count == 0:
            return []

        # Optional: shelf pins if adjustable-style mounting
        use_pins = config.get("use_pins", False)
        if use_pins:
            return [HardwareItem(
                name="Shelf Pin",
                quantity=count * 4,  # 4 pins per shelf
                sku="SP-5MM",
                notes="5mm brass shelf pins"
            )]
        return []
```

---

## File Structure

```
src/cabinets/domain/components/
    __init__.py           # Exports: component_registry, Component, ComponentContext, etc.
    protocol.py           # Component protocol definition
    context.py            # ComponentContext dataclass
    results.py            # ValidationResult, GenerationResult, HardwareItem
    registry.py           # ComponentRegistry singleton
    shelf.py              # shelf.fixed, shelf.adjustable implementations
```

### Package Init

```python
# src/cabinets/domain/components/__init__.py

from .protocol import Component
from .context import ComponentContext
from .results import GenerationResult, ValidationResult, HardwareItem
from .registry import component_registry, ComponentRegistry

# Import components to trigger registration
from . import shelf

__all__ = [
    "Component",
    "ComponentContext",
    "GenerationResult",
    "ValidationResult",
    "HardwareItem",
    "component_registry",
    "ComponentRegistry",
]
```

---

## SOLID Principles Alignment

| Principle | How This FRD Enables It |
|-----------|------------------------|
| **Single Responsibility** | Each component handles one type only |
| **Open/Closed** | Add components without modifying registry or services |
| **Liskov Substitution** | All components satisfy same `Component` protocol |
| **Interface Segregation** | `Component` protocol is minimal (3 methods) |
| **Dependency Inversion** | Services depend on `Component` protocol, not implementations |

---

## Integration with Section Generation

```python
# Updated flow in services.py

class SectionBuilder:
    def build_sections(self, configs: list[SectionConfig], ...) -> tuple[list[Section], list[Panel]]:
        for i, config in enumerate(configs):
            # Get component for section type
            component_id = self._resolve_component_id(config.section_type)
            component_class = component_registry.get(component_id)
            component = component_class()

            # Build context
            context = ComponentContext(
                width=resolved_width,
                height=cabinet_height,
                depth=section_depth,
                material=material,
                position=Position(current_x, material.thickness),
                section_index=i,
                cabinet_width=cabinet_width,
                cabinet_height=cabinet_height,
                cabinet_depth=cabinet_depth,
            )

            # Validate
            validation = component.validate(config.to_dict(), context)
            if not validation.is_valid:
                raise ValidationError(validation.errors)

            # Generate
            result = component.generate(config.to_dict(), context)
            panels.extend(result.panels)
            hardware.extend(result.hardware)

    def _resolve_component_id(self, section_type: SectionType) -> str:
        """Map section type to default component ID."""
        mapping = {
            SectionType.OPEN: "shelf.fixed",
            SectionType.DOORED: "door.hinged.overlay",
            SectionType.DRAWERS: "drawer.standard",
            SectionType.CUBBY: "cubby.open",
        }
        return mapping.get(section_type, "shelf.fixed")
```

---

## Validation Rules

| Rule | Check | Error Message |
|------|-------|---------------|
| V-01 | Component ID format | "Invalid component ID: must be 'category.type' or 'category.type.variant'" |
| V-02 | Duplicate registration | "Component 'X' already registered" |
| V-03 | Unknown component | "Unknown component: X" |
| V-04 | Config validation | Delegated to component's `validate()` method |

---

## Testing Strategy

### Unit Tests

| Test Case | Expected |
|-----------|----------|
| Register component via decorator | Component retrievable by ID |
| Duplicate registration | Raises `ValueError` |
| Invalid ID format | Raises `ValueError` |
| Get unknown component | Raises `KeyError` |
| List components | Returns sorted list of IDs |
| FixedShelf validates count | Errors on negative, > 20 |
| FixedShelf generates panels | Correct positions and sizes |
| FixedShelf hardware with pins | Returns 4 pins per shelf |
| ValidationResult.ok() | `is_valid = True` |
| ValidationResult.fail() | `is_valid = False` |

### Integration Tests

- Section with `shelf.fixed` generates correct panels
- Unknown component ID fails gracefully
- Hardware aggregated across all sections
- Validation errors collected before generation

---

## Implementation Phases

### Phase 1: Core Infrastructure (Est. 1 day)
- [ ] Create `src/cabinets/domain/components/` package
- [ ] Implement `ComponentContext` dataclass
- [ ] Implement `ValidationResult`, `GenerationResult`, `HardwareItem`
- [ ] Implement `ComponentRegistry` singleton

### Phase 2: Protocol & Registration (Est. 1 day)
- [ ] Define `Component` protocol
- [ ] Implement `@register` decorator
- [ ] Add ID validation logic
- [ ] Unit tests for registry

### Phase 3: Reference Component (Est. 1 day)
- [ ] Implement `shelf.fixed` component
- [ ] Implement `shelf.adjustable` component (optional)
- [ ] Unit tests for shelf generation

### Phase 4: Integration (Est. 1 day)
- [ ] Update `SectionBuilder` to use component registry
- [ ] Integrate hardware tracking
- [ ] End-to-end tests

---

## Dependencies & Risks

### Dependencies
- FRD-01: Config schema defines component config structures
- FRD-04: `SectionType` enum maps to component IDs
- Existing `Panel`, `CutPiece`, `MaterialSpec` value objects

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Protocol not enforced at runtime | Medium | Use runtime checks in registry |
| Component config schema drift | Medium | Config validation in each component |
| Circular imports | Low | Careful package organization |

---

## Open Questions

1. **Component versioning**: Should components have version numbers?
   - Proposed: No, component ID implies version; breaking changes = new ID

2. **Component discovery**: Auto-discover via entry points or explicit import?
   - Proposed: Explicit import in `__init__.py` for simplicity

3. **Hardware aggregation**: Where to aggregate hardware across sections?
   - Proposed: `Cabinet.get_hardware_list()` method calling all components

---

## Future Component IDs

Reserved component IDs for future FRDs:

| ID | Description | FRD |
|----|-------------|-----|
| `shelf.fixed` | Non-adjustable shelves | This FRD |
| `shelf.adjustable` | Shelves with pin holes | FRD-06 |
| `door.hinged.overlay` | Overlay hinged door | FRD-07 |
| `door.hinged.inset` | Inset hinged door | FRD-07 |
| `door.sliding` | Sliding/bypass door | FRD-07 |
| `drawer.standard` | Standard drawer box | FRD-08 |
| `drawer.file` | File drawer (deeper) | FRD-08 |
| `cubby.open` | Open cubby/bin | FRD-09 |
| `divider.vertical` | Cubby vertical divider | FRD-09 |
| `divider.horizontal` | Cubby horizontal divider | FRD-09 |

---

*FRD-05 ready for implementation: 2025-12-27*
