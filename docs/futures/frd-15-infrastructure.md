# FRD-15: Infrastructure Integration

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** Medium
**Depends On:** FRD-03 (Obstacle Avoidance), FRD-05 (Component Registry)

---

## Problem Statement

Built-in cabinets often need to accommodate electrical, lighting, and cable management infrastructure. Currently, the system cannot:

- Define locations for LED strip channels or puck lights
- Place electrical outlet cutouts in panels
- Add cable management grommets and channels
- Route wiring paths through cabinet structures
- Track infrastructure hardware in cut lists

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| Lighting integration | LED strips, puck lights, accent positions configurable per section |
| Electrical support | Standard US outlet box cutouts with required clearances |
| Cable management | Grommet holes, cable channels, access panels defined |
| Wire routing | Path indication through cabinet for wiring |
| Cut list integration | Panel cutouts, grommets, channels in output |

---

## Scope

### In Scope

- `LightingConfig`: LED strips, puck lights, accent lighting positions
- `OutletConfig`: Single, double, GFI outlet box placements
- `CableManagementConfig`: Grommets, channels, access panels
- Wire routing path specifications
- Panel cutout generation for all infrastructure types
- Hardware list additions (grommets, wire channels)
- Ventilation hole specifications for electronics

### Out of Scope

- Actual electrical wiring specifications (code compliance)
- Smart home / automation integration
- Power supply placement for LED systems
- Conduit material specifications
- Low-voltage vs line-voltage distinction

---

## Functional Requirements

### FR-01: Lighting Configuration

- **FR-01.1**: SHALL support `led_strip` type with location: `under_cabinet`, `in_cabinet`, `above_cabinet`
- **FR-01.2**: SHALL support `puck_light` type with diameter (standard: 2.5", 3")
- **FR-01.3**: SHALL support `accent` type for decorative positioning
- **FR-01.4**: Each light SHALL specify `section_indices` for placement
- **FR-01.5**: LED strips SHALL include channel dimensions (width: 0.5", depth: 0.25" default)
- **FR-01.6**: Puck lights SHALL generate circular cutout specifications
- **FR-01.7**: SHALL specify wire routing path from light to cabinet exit point

### FR-02: Electrical Outlet Configuration

- **FR-02.1**: SHALL support outlet types: `single`, `double`, `gfi`
- **FR-02.2**: Standard US box dimensions:
  - Single: 2" W x 3.75" H
  - Double: 4" W x 3.75" H
  - GFI: 2.75" W x 4.5" H
- **FR-02.3**: SHALL specify `panel` for cutout: `back`, `left_side`, `right_side`
- **FR-02.4**: SHALL specify `position` as `{x, y}` relative to panel origin
- **FR-02.5**: Cutouts SHALL maintain 0.125" clearance around box
- **FR-02.6**: SHALL indicate conduit entry direction: `top`, `bottom`, `left`, `right`

### FR-03: Cable Management

- **FR-03.1**: Grommet types SHALL support standard sizes: 2", 2.5", 3" diameter
- **FR-03.2**: Grommets SHALL specify `panel` and `position` for placement
- **FR-03.3**: Cable channels SHALL define path with `start`, `end`, `width` (default: 2")
- **FR-03.4**: Access panels SHALL specify dimensions and hinge/removable type
- **FR-03.5**: Ventilation holes SHALL specify pattern: `grid`, `slot`, `circular`
- **FR-03.6**: Ventilation SHALL calculate minimum CFM based on enclosure volume

### FR-04: Wire Routing

- **FR-04.1**: Wire routes SHALL be defined as ordered list of waypoints
- **FR-04.2**: Routes SHALL specify panel penetration points (access holes)
- **FR-04.3**: Access hole diameter: 0.75" default for low-voltage, 1" for line-voltage
- **FR-04.4**: Routes SHALL avoid structural elements (dados, dividers)

### FR-05: Cut List Integration

- **FR-05.1**: Panel cutouts SHALL appear in cut piece notes with position/size
- **FR-05.2**: Grommets SHALL appear in hardware list with size and quantity
- **FR-05.3**: Wire channel pieces SHALL appear as separate cut pieces if applicable
- **FR-05.4**: Access hole positions SHALL be noted on relevant panels

### FR-06: Validation

- **FR-06.1**: Cutouts SHALL NOT overlap each other or structural elements
- **FR-06.2**: Cutouts SHALL maintain minimum edge distance (1" from panel edges)
- **FR-06.3**: Outlet positions SHALL be reachable (not behind fixed shelves)
- **FR-06.4**: Ventilation SHALL warn if electronics specified without adequate airflow

---

## Data Models

### InfrastructureConfig

```python
# src/cabinets/domain/components/infrastructure.py

from dataclasses import dataclass
from enum import Enum
from typing import Any

class LightingType(Enum):
    LED_STRIP = "led_strip"
    PUCK_LIGHT = "puck_light"
    ACCENT = "accent"

class LightingLocation(Enum):
    UNDER_CABINET = "under_cabinet"
    IN_CABINET = "in_cabinet"
    ABOVE_CABINET = "above_cabinet"

class OutletType(Enum):
    SINGLE = "single"
    DOUBLE = "double"
    GFI = "gfi"

class GrommetSize(Enum):
    SMALL = 2.0      # 2" diameter
    MEDIUM = 2.5     # 2.5" diameter
    LARGE = 3.0      # 3" diameter

class PanelLocation(Enum):
    BACK = "back"
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"
    TOP = "top"
    BOTTOM = "bottom"

@dataclass(frozen=True)
class Position2D:
    x: float
    y: float

@dataclass(frozen=True)
class LightingSpec:
    light_type: LightingType
    location: LightingLocation
    section_indices: tuple[int, ...]
    length: float | None = None           # For LED strips
    diameter: float = 2.5                  # For puck lights
    channel_width: float = 0.5            # LED channel width
    channel_depth: float = 0.25           # LED channel depth

@dataclass(frozen=True)
class OutletSpec:
    outlet_type: OutletType
    section_index: int
    panel: PanelLocation
    position: Position2D
    conduit_direction: str = "bottom"     # top, bottom, left, right

    @property
    def cutout_dimensions(self) -> tuple[float, float]:
        """Return (width, height) with clearance."""
        dims = {
            OutletType.SINGLE: (2.25, 4.0),
            OutletType.DOUBLE: (4.25, 4.0),
            OutletType.GFI: (3.0, 4.75),
        }
        return dims[self.outlet_type]

@dataclass(frozen=True)
class GrommetSpec:
    size: float                           # Diameter in inches
    panel: PanelLocation
    position: Position2D
    section_index: int | None = None      # None = cabinet-level

@dataclass(frozen=True)
class CableChannelSpec:
    start: Position2D
    end: Position2D
    width: float = 2.0
    depth: float = 1.0

@dataclass(frozen=True)
class VentilationSpec:
    pattern: str                          # "grid", "slot", "circular"
    panel: PanelLocation
    position: Position2D
    width: float
    height: float
    hole_size: float = 0.25              # Individual hole diameter

@dataclass(frozen=True)
class WireRouteSpec:
    waypoints: tuple[Position2D, ...]
    hole_diameter: float = 0.75
    panel_penetrations: tuple[PanelLocation, ...] = ()
```

### Cutout Value Object

```python
@dataclass(frozen=True)
class PanelCutout:
    """Cutout specification for a panel."""
    cutout_type: str                      # "outlet", "grommet", "wire_hole", "vent"
    panel: PanelLocation
    position: Position2D                  # Center point
    width: float
    height: float
    shape: str = "rectangular"            # "rectangular", "circular"
    notes: str = ""
```

---

## Technical Approach

### File Structure

```
src/cabinets/domain/components/
    infrastructure.py      # New: all infrastructure models and component
```

### Component Registration

```python
@component_registry.register("infrastructure.lighting")
class LightingComponent:
    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        ...

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        ...

@component_registry.register("infrastructure.electrical")
class ElectricalComponent:
    ...

@component_registry.register("infrastructure.cable_management")
class CableManagementComponent:
    ...
```

### Integration with Existing Entities

- Extend `Panel.to_cut_piece()` to include cutout notes
- Add `cutouts: list[PanelCutout]` to `Panel` entity
- Hardware items: `HardwareItem(name="Grommet", size="2.5\"", quantity=1)`

---

## Configuration Schema

### YAML Configuration

```yaml
infrastructure:
  lighting:
    - type: led_strip
      location: under_cabinet
      section_indices: [0, 1, 2]
      channel_width: 0.5
      channel_depth: 0.25
    - type: puck_light
      location: in_cabinet
      section_indices: [1]
      diameter: 3.0
      position: { x: 12, y: 6 }

  outlets:
    - type: single
      section_index: 1
      panel: back
      position: { x: 6, y: 12 }
      conduit_direction: bottom
    - type: gfi
      section_index: 0
      panel: left_side
      position: { x: 3, y: 18 }

  cable_management:
    - type: grommet
      size: 2.5
      panel: top
      position: { x: 24, y: 6 }
      section_index: 2
    - type: grommet
      size: 2.0
      panel: back
      position: { x: 12, y: 36 }
    - type: channel
      start: { x: 0, y: 6 }
      end: { x: 48, y: 6 }
      width: 2.0

  ventilation:
    - pattern: grid
      panel: back
      position: { x: 24, y: 12 }
      width: 6
      height: 4
      hole_size: 0.25

  wire_routes:
    - waypoints:
        - { x: 6, y: 48 }
        - { x: 6, y: 12 }
        - { x: 24, y: 12 }
      hole_diameter: 0.75
      panel_penetrations: [back, bottom]
```

### JSON Schema Extension

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `infrastructure.lighting` | array | No | `[]` |
| `infrastructure.lighting[].type` | enum | Yes | - |
| `infrastructure.lighting[].location` | enum | Yes | - |
| `infrastructure.lighting[].section_indices` | array[int] | Yes | - |
| `infrastructure.outlets` | array | No | `[]` |
| `infrastructure.outlets[].type` | enum | Yes | - |
| `infrastructure.outlets[].panel` | enum | Yes | - |
| `infrastructure.outlets[].position` | object | Yes | - |
| `infrastructure.cable_management` | array | No | `[]` |
| `infrastructure.cable_management[].type` | enum | Yes | - |
| `infrastructure.cable_management[].size` | float | For grommet | - |
| `infrastructure.ventilation` | array | No | `[]` |
| `infrastructure.wire_routes` | array | No | `[]` |

---

## Hardware Output

### Grommet Hardware

```
Hardware List:
  - Rubber Grommet 2.5": 2 qty (SKU: GRM-250-BLK)
  - Rubber Grommet 2.0": 1 qty (SKU: GRM-200-BLK)
```

### Cut List Notes

```
Cut Piece: Back Panel (48" x 84")
  Cutouts:
    - Outlet (single): 6", 12" - 2.25" x 4.0"
    - Grommet hole: 12", 36" - 2.0" dia
    - Wire access: 6", 48" - 0.75" dia
    - Ventilation grid: 24", 12" - 6" x 4"
```

---

## Validation Rules

| Rule | Check | Message |
|------|-------|---------|
| V-01 | Cutout within panel bounds | "Cutout at ({x}, {y}) exceeds panel dimensions" |
| V-02 | Cutout edge distance | "Cutout too close to edge (min 1\")" |
| V-03 | No cutout overlap | "Cutouts overlap at ({x}, {y})" |
| V-04 | Outlet accessibility | "Outlet behind fixed shelf at section {n}" |
| V-05 | Grommet size valid | "Invalid grommet size: {size} (use 2, 2.5, or 3)" |
| V-06 | Section index valid | "Section index {n} out of range" |
| V-07 | Ventilation adequacy | "Warning: Electronics may need additional ventilation" |

---

## Testing Strategy

### Unit Tests

| Test | Assertion |
|------|-----------|
| LED strip config | Channel dimensions in output |
| Puck light cutout | Circular cutout at specified position |
| Outlet dimensions | Correct size for single/double/GFI |
| Grommet hardware | Hardware list includes grommet |
| Cutout overlap | Validation error when cutouts overlap |
| Edge distance | Validation error when cutout < 1" from edge |
| Wire route | Waypoints generate access holes |
| Ventilation grid | Correct hole pattern generated |

### Integration Tests

- Full cabinet with lighting generates panel cutouts
- Multiple outlet types in single cabinet
- Cable management across multiple sections
- Cut list includes all infrastructure notes

---

## Implementation Phases

### Phase 1: Core Models (Est. 1 day)

- [ ] Create `infrastructure.py` with all dataclasses
- [ ] Implement `LightingSpec`, `OutletSpec`, `GrommetSpec`
- [ ] Implement `PanelCutout` value object
- [ ] Add cutout support to `Panel` entity

### Phase 2: Components (Est. 1.5 days)

- [ ] Implement `LightingComponent` with LED strip and puck light
- [ ] Implement `ElectricalComponent` with outlet types
- [ ] Implement `CableManagementComponent` with grommets/channels
- [ ] Register all components

### Phase 3: Validation & Output (Est. 1 day)

- [ ] Implement all validation rules
- [ ] Integrate cutouts into cut list output
- [ ] Add hardware items for grommets
- [ ] Wire route access hole generation

### Phase 4: Testing (Est. 0.5 day)

- [ ] Unit tests for all components
- [ ] Integration tests with full cabinet
- [ ] Edge case coverage

---

## Dependencies & Risks

### Dependencies

- FRD-03: Uses `Clearance` concept for outlet clearances
- FRD-05: Component registry for registration
- Existing `Panel`, `CutPiece`, `HardwareItem` entities

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Electrical code variations | Medium | Document as "indicative only, verify with electrician" |
| Complex cutout geometry | Low | Start with rectangular/circular only |
| Wire routing conflicts | Medium | Validate against structural elements |
| Ventilation calculations | Low | Provide warning only, not enforcement |

---

## Open Questions

1. **LED driver placement**: Should we track power supply locations?
   - Proposed: Out of scope for v1; note in documentation

2. **Conduit sizing**: Track conduit diameter for wire bundles?
   - Proposed: Defer; indicate direction only

3. **Low-voltage vs line-voltage**: Different hole sizes?
   - Proposed: Yes, 0.75" vs 1.0" default, configurable

---

## Appendix: Standard Dimensions

### US Electrical Box Sizes

| Type | Width | Height | Depth |
|------|-------|--------|-------|
| Single gang | 2" | 3.75" | 2.5" |
| Double gang | 4" | 3.75" | 2.5" |
| GFI | 2.75" | 4.5" | 2.5" |

### LED Channel Profiles

| Profile | Width | Depth | Use Case |
|---------|-------|-------|----------|
| Slim | 0.4" | 0.2" | Under-cabinet strips |
| Standard | 0.5" | 0.25" | General purpose |
| Deep | 0.75" | 0.5" | High-output strips |

### Grommet Sizes

| Size | Cable Capacity | Typical Use |
|------|----------------|-------------|
| 2" | 3-4 cables | Single device |
| 2.5" | 5-6 cables | Multiple devices |
| 3" | 8+ cables | Entertainment center |

---

*FRD-15 ready for implementation: 2025-12-27*
