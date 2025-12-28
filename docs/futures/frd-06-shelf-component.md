# FRD-06: Enhanced Shelf Component

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** High (First Component Registry implementation)
**Depends On:** FRD-05 (Component Registry Architecture)

---

## Problem Statement

The current shelf implementation in `LayoutCalculator` is limited to evenly-spaced, full-depth shelves. Users need:
- Fixed shelves with dado joinery for structural rigidity
- Adjustable shelves with 32mm system pin holes
- Custom positioning (explicit heights or evenly distributed)
- Setback control for decorative/functional purposes
- Depth overrides for shallower items

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Two shelf types registered | `shelf.fixed` and `shelf.adjustable` in registry |
| Flexible positioning | Explicit heights OR count-based distribution |
| Hardware tracking | 4 pins per adjustable shelf in hardware list |
| Edge treatment flagging | Front edges marked for banding |
| Dado specifications | Fixed shelves output dado cut positions |

---

## Scope

### In Scope
- `shelf.fixed` component with dado joint specifications
- `shelf.adjustable` component with 32mm pin hole patterns
- Position configuration (explicit heights or count-based)
- Setback and depth override support
- Edge banding quantity tracking
- Shelf pin hardware output

### Out of Scope
- Actual 32mm hole drilling geometry (CAM concern)
- Edge banding material selection
- Mid-span support brackets
- Pull-out shelf hardware

---

## Functional Requirements

### FR-01: Shelf Configuration

- **FR-01.1**: Shelves SHALL accept `positions: list[float]` for explicit height placement (inches from section bottom)
- **FR-01.2**: Shelves SHALL accept `count: int` for evenly-distributed placement
- **FR-01.3**: If both provided, `positions` SHALL take precedence
- **FR-01.4**: `setback: float` SHALL control front edge inset (default: 1.0")
- **FR-01.5**: `depth: float | None` SHALL allow shallower-than-section shelves

### FR-02: Fixed Shelf Component (`shelf.fixed`)

- **FR-02.1**: SHALL register as `shelf.fixed` via `@component_registry.register`
- **FR-02.2**: SHALL output dado joint specifications:
  - Dado depth = material_thickness / 3
  - Dado width = material_thickness
  - Dado positions on left/right side panels
- **FR-02.3**: SHALL include dado positions in `cut_pieces` output
- **FR-02.4**: SHALL NOT output shelf pin hardware

### FR-03: Adjustable Shelf Component (`shelf.adjustable`)

- **FR-03.1**: SHALL register as `shelf.adjustable` via `@component_registry.register`
- **FR-03.2**: SHALL output pin hole specifications:
  - 32mm vertical spacing between holes
  - 37mm inset from front/back edges
  - Start/end heights configurable (default: 2" from top/bottom)
- **FR-03.3**: SHALL output 4 shelf pins per shelf in hardware list
- **FR-03.4**: Pin hole patterns SHALL be included in side panel cut specifications

### FR-04: Edge Treatment

- **FR-04.1**: Front edge of each shelf SHALL be flagged for edge banding
- **FR-04.2**: Hardware list SHALL include edge banding linear inches

### FR-05: Validation

- **FR-05.1**: Shelf positions SHALL be within section height bounds
- **FR-05.2**: Shelf depth SHALL NOT exceed section depth minus setback
- **FR-05.3**: Adjacent shelves SHALL have minimum 2" spacing
- **FR-05.4**: Wide shelves (>36") SHALL trigger warning for 3/4" material

---

## Data Models

### ShelfConfig

```python
@dataclass(frozen=True)
class ShelfConfig:
    """Configuration for shelf placement."""
    positions: tuple[float, ...] | None = None  # Explicit heights
    count: int | None = None                     # Or evenly distributed
    setback: float = 1.0                         # Front inset (inches)
    depth: float | None = None                   # Override section depth
    edge_band_front: bool = True                 # Apply edge banding
```

### DadoSpec (Fixed Shelves)

```python
@dataclass(frozen=True)
class DadoSpec:
    """Dado joint specification for fixed shelves."""
    panel_id: str           # Which panel (e.g., "left_side", "right_side")
    position: float         # Distance from panel bottom (inches)
    width: float            # Dado width (= shelf material thickness)
    depth: float            # Dado depth (= thickness / 3)
    length: float           # Dado length (= shelf depth)
```

### PinHolePattern (Adjustable Shelves)

```python
@dataclass(frozen=True)
class PinHolePattern:
    """32mm system pin hole pattern specification."""
    panel_id: str           # Which panel
    front_inset: float      # Distance from front edge (default 37mm)
    back_inset: float       # Distance from back edge (default 37mm)
    start_height: float     # First hole height from bottom
    end_height: float       # Last hole height from bottom
    spacing: float = 32.0   # Hole spacing in mm (32mm system)
    hole_diameter: float = 5.0  # 5mm holes
```

---

## Technical Approach

### File: `src/cabinets/domain/components/shelf.py`

```python
from typing import Any
from dataclasses import dataclass
from ..entities import Panel
from ..value_objects import PanelType, Position
from .protocol import Component
from .context import ComponentContext
from .results import GenerationResult, ValidationResult, HardwareItem
from .registry import component_registry

MM_TO_INCH = 0.03937008

@dataclass(frozen=True)
class DadoSpec:
    panel_id: str
    position: float
    width: float
    depth: float
    length: float

@dataclass(frozen=True)
class PinHolePattern:
    panel_id: str
    front_inset: float
    back_inset: float
    start_height: float
    end_height: float
    spacing: float = 32.0 * MM_TO_INCH  # ~1.26"
    hole_diameter: float = 5.0 * MM_TO_INCH  # ~0.197"

def _parse_shelf_config(config: dict[str, Any], context: ComponentContext) -> tuple[list[float], float, float]:
    """Parse shelf config, return (positions, setback, depth)."""
    setback = config.get("setback", 1.0)
    depth = config.get("depth") or (context.depth - setback)

    if positions := config.get("positions"):
        return list(positions), setback, depth

    count = config.get("count", 0)
    if count <= 0:
        return [], setback, depth

    spacing = context.height / (count + 1)
    return [spacing * (i + 1) for i in range(count)], setback, depth


@component_registry.register("shelf.fixed")
class FixedShelfComponent:
    """Fixed shelf with dado joinery."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []
        positions, setback, depth = _parse_shelf_config(config, context)

        for i, pos in enumerate(positions):
            if pos < 0 or pos > context.height:
                errors.append(f"Shelf {i+1} position {pos}\" outside section height")

        for i in range(len(positions) - 1):
            if positions[i+1] - positions[i] < 2.0:
                errors.append(f"Shelves {i+1} and {i+2} less than 2\" apart")

        if depth > context.depth - setback:
            errors.append(f"Shelf depth {depth}\" exceeds available {context.depth - setback}\"")

        if context.width > 36 and context.material.thickness <= 0.75:
            warnings.append(f"Span {context.width:.1f}\" may sag - consider support")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        positions, setback, depth = _parse_shelf_config(config, context)
        if not positions:
            return GenerationResult()

        panels = []
        dado_specs = []
        thickness = context.material.thickness
        dado_depth = thickness / 3

        for pos in positions:
            panels.append(Panel(
                panel_type=PanelType.SHELF,
                width=context.width,
                height=depth,
                material=context.material,
                position=Position(context.position.x + setback, context.position.y + pos),
            ))

            # Dado on left side panel
            dado_specs.append(DadoSpec(
                panel_id="left_side",
                position=pos,
                width=thickness,
                depth=dado_depth,
                length=depth,
            ))
            # Dado on right side panel
            dado_specs.append(DadoSpec(
                panel_id="right_side",
                position=pos,
                width=thickness,
                depth=dado_depth,
                length=depth,
            ))

        edge_banding_inches = context.width * len(positions)
        hardware = [
            HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{edge_banding_inches:.1f} linear inches for shelf fronts",
            )
        ] if config.get("edge_band_front", True) else []

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            # Note: dado_specs stored as metadata - implementation detail
        )

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        positions, _, _ = _parse_shelf_config(config, context)
        if not positions or not config.get("edge_band_front", True):
            return []
        return [HardwareItem(
            name="Edge Banding",
            quantity=1,
            notes=f"{context.width * len(positions):.1f} linear inches",
        )]


@component_registry.register("shelf.adjustable")
class AdjustableShelfComponent:
    """Adjustable shelf with 32mm system pin holes."""

    DEFAULT_PIN_START = 2.0   # inches from bottom
    DEFAULT_PIN_END = 2.0     # inches from top
    FRONT_INSET = 37.0 * MM_TO_INCH  # ~1.46"
    BACK_INSET = 37.0 * MM_TO_INCH

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []
        positions, setback, depth = _parse_shelf_config(config, context)

        pin_start = config.get("pin_start_height", self.DEFAULT_PIN_START)
        pin_end = context.height - config.get("pin_end_offset", self.DEFAULT_PIN_END)

        for i, pos in enumerate(positions):
            if pos < pin_start or pos > pin_end:
                warnings.append(f"Shelf {i+1} at {pos}\" outside pin hole range")

        if depth > context.depth - setback:
            errors.append(f"Shelf depth {depth}\" exceeds available {context.depth - setback}\"")

        if context.width > 36 and context.material.thickness <= 0.75:
            warnings.append(f"Span {context.width:.1f}\" may sag - consider support")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        positions, setback, depth = _parse_shelf_config(config, context)
        if not positions:
            return GenerationResult()

        panels = []
        for pos in positions:
            panels.append(Panel(
                panel_type=PanelType.SHELF,
                width=context.width,
                height=depth,
                material=context.material,
                position=Position(context.position.x + setback, context.position.y + pos),
            ))

        # Pin hole pattern specs
        pin_start = config.get("pin_start_height", self.DEFAULT_PIN_START)
        pin_end = context.height - config.get("pin_end_offset", self.DEFAULT_PIN_END)

        pin_patterns = [
            PinHolePattern("left_side", self.FRONT_INSET, self.BACK_INSET, pin_start, pin_end),
            PinHolePattern("right_side", self.FRONT_INSET, self.BACK_INSET, pin_start, pin_end),
        ]

        # Hardware
        shelf_count = len(positions)
        hardware = [
            HardwareItem(
                name="Shelf Pin",
                quantity=shelf_count * 4,
                sku="SP-5MM-BRASS",
                notes="5mm brass shelf pins",
            ),
        ]

        if config.get("edge_band_front", True):
            hardware.append(HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{context.width * shelf_count:.1f} linear inches",
            ))

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
        )

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        positions, _, _ = _parse_shelf_config(config, context)
        if not positions:
            return []

        shelf_count = len(positions)
        items = [
            HardwareItem(
                name="Shelf Pin",
                quantity=shelf_count * 4,
                sku="SP-5MM-BRASS",
                notes="5mm brass shelf pins",
            ),
        ]

        if config.get("edge_band_front", True):
            items.append(HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{context.width * shelf_count:.1f} linear inches",
            ))

        return items
```

---

## Configuration Examples

### Fixed Shelves with Explicit Positions

```yaml
sections:
  - type: open
    component: shelf.fixed
    config:
      positions: [8.0, 16.0, 24.0]  # 3 shelves at specific heights
      setback: 1.0
      edge_band_front: true
```

### Adjustable Shelves with Count

```yaml
sections:
  - type: open
    component: shelf.adjustable
    config:
      count: 4                # 4 evenly-distributed shelves
      setback: 0.5
      depth: 10.0             # Shallower than section
      pin_start_height: 3.0   # Pin holes start 3" up
      pin_end_offset: 3.0     # Pin holes end 3" from top
```

---

## Hardware Output Examples

### Adjustable Shelf Hardware

```
Component: shelf.adjustable
Config: { count: 3, width: 24" }

Hardware List:
  - Shelf Pin (SP-5MM-BRASS): 12 qty
  - Edge Banding: 72.0 linear inches
```

### Fixed Shelf Dado Specs

```
Component: shelf.fixed
Config: { positions: [12.0, 24.0], thickness: 0.75" }

Dado Specifications:
  - Left Side Panel:
    - Position: 12.0", Width: 0.75", Depth: 0.25", Length: 22.5"
    - Position: 24.0", Width: 0.75", Depth: 0.25", Length: 22.5"
  - Right Side Panel:
    - (mirror of left)
```

---

## Validation Rules

| Rule | Check | Error/Warning |
|------|-------|---------------|
| V-01 | Position in bounds | ERROR: "position X outside section height" |
| V-02 | Minimum spacing | ERROR: "Shelves X and Y less than 2\" apart" |
| V-03 | Depth valid | ERROR: "depth exceeds available" |
| V-04 | Span warning | WARNING: "Span may sag - consider support" |
| V-05 | Pin range | WARNING: "outside pin hole range" |

---

## Testing Strategy

### Unit Tests

| Test | Assertion |
|------|-----------|
| `shelf.fixed` registers | `component_registry.get("shelf.fixed")` succeeds |
| `shelf.adjustable` registers | `component_registry.get("shelf.adjustable")` succeeds |
| Explicit positions | 3 positions -> 3 Panel objects at correct heights |
| Count-based distribution | count=4 -> 4 evenly spaced shelves |
| Setback applied | Shelf position.x offset by setback |
| Depth override | Custom depth reflected in panel.height |
| Fixed shelf dados | 2 DadoSpec per shelf (left + right) |
| Adjustable shelf pins | 4 pins per shelf in hardware |
| Edge banding tracked | Linear inches calculated correctly |
| Validation: out of bounds | Position > height -> error |
| Validation: too close | 1" spacing -> error |
| Validation: span warning | 40" wide, 0.75" thick -> warning |

### Integration Tests

- Section with `shelf.fixed` generates correct panels + dados
- Section with `shelf.adjustable` generates correct panels + hardware
- Hardware list aggregates across multiple sections
- Edge banding totals across all shelves

---

## Implementation Phases

### Phase 1: Core Shelf Components (Est. 0.5 day)
- [ ] Implement `ShelfConfig`, `DadoSpec`, `PinHolePattern` dataclasses
- [ ] Implement `_parse_shelf_config` helper
- [ ] Implement `FixedShelfComponent` with dado output
- [ ] Implement `AdjustableShelfComponent` with pin hole output

### Phase 2: Hardware & Edge Treatment (Est. 0.5 day)
- [ ] Add edge banding to hardware lists
- [ ] Add shelf pin counting logic
- [ ] Implement `hardware()` methods

### Phase 3: Validation & Testing (Est. 0.5 day)
- [ ] Implement all validation rules
- [ ] Unit tests for both components
- [ ] Integration tests with component registry

---

## Dependencies & Risks

### Dependencies
- FRD-05: `Component` protocol, `ComponentContext`, `GenerationResult`, `HardwareItem`
- Existing: `Panel`, `PanelType.SHELF`, `Position`, `MaterialSpec`

### Risks

| Risk | Mitigation |
|------|------------|
| Dado specs not consumed downstream | Document as metadata; implement consumer in cut list phase |
| Pin hole pattern imperial/metric confusion | Use constants with clear naming (`MM_TO_INCH`) |
| Edge banding aggregation complexity | Simple linear inch sum; material type TBD |

---

## Open Questions

1. **Dado spec output format**: Should `DadoSpec` be in `GenerationResult.cut_pieces` or separate metadata?
   - Proposed: Separate `dado_specs` attribute on result (extend `GenerationResult`)

2. **Pin hole pattern output**: Where should drilling specs live?
   - Proposed: Metadata on side panel cut pieces, or separate drilling plan output

3. **Edge banding material types**: Track different banding types (PVC, veneer)?
   - Proposed: Defer to future FRD; current implementation tracks linear inches only

---

*FRD-06 ready for implementation: 2025-12-27*
