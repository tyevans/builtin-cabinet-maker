# FRD-07: Door Component

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** High
**Depends On:** FRD-05 (Component Registry Architecture)

---

## Problem Statement

Cabinet sections need closeable fronts. The current system has no door support. Users need:
- Hinged doors in overlay, inset, and partial overlay styles
- Single and double door configurations
- European hinge boring specifications for CNC/drilling
- Hardware requirements for hinges and handles

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Three door styles registered | `door.hinged.overlay`, `door.hinged.inset`, `door.hinged.partial` |
| Configurable count | Single (1) or double (2) doors per section |
| Hinge calculation | Correct count based on door height |
| Hardware output | European hinges + handle placeholders in hardware list |
| Cut list integration | Door panels with edge treatment on all 4 sides |

---

## Scope

### In Scope
- `door.hinged.overlay` - full overlay doors
- `door.hinged.inset` - inset doors within face frame
- `door.hinged.partial` - partial overlay doors
- Single and double door configurations
- European 35mm hinge cup boring specifications
- Hinge count calculation by door height
- Handle/knob position placeholder

### Out of Scope
- Sliding/bypass doors (future FRD)
- Glass panel doors
- Face frame construction
- Soft-close damper mechanisms (noted as option only)
- Actual handle selection/procurement

---

## Functional Requirements

### FR-01: Door Styles

- **FR-01.1**: `door.hinged.overlay` SHALL cover cabinet face frame completely
- **FR-01.2**: `door.hinged.inset` SHALL sit inside face frame opening
- **FR-01.3**: `door.hinged.partial` SHALL overlap face frame partially
- **FR-01.4**: All styles SHALL register via `@component_registry.register`

### FR-02: Door Configuration

- **FR-02.1**: `count` SHALL accept 1 (single) or 2 (double/pair)
- **FR-02.2**: `hinge_side` SHALL accept "left" or "right" for single doors
- **FR-02.3**: Double doors SHALL default to left-right pair opening
- **FR-02.4**: `reveal` SHALL set gap around door (default: 0.125" / 1/8")
- **FR-02.5**: `overlay` SHALL set overlap amount for overlay styles (default: 0.5")

### FR-03: Door Sizing

- **FR-03.1**: Overlay door width = section_width + (2 * overlay) - reveal
- **FR-03.2**: Overlay door height = section_height + (2 * overlay) - reveal
- **FR-03.3**: Inset door width = opening_width - (2 * reveal)
- **FR-03.4**: Inset door height = opening_height - (2 * reveal)
- **FR-03.5**: Double doors SHALL split width evenly minus center gap

### FR-04: Hinge Specifications

- **FR-04.1**: Hinge count based on door height:
  - < 40": 2 hinges
  - 40-60": 3 hinges
  - > 60": 4 hinges
- **FR-04.2**: European hinge cup: 35mm diameter, 12mm depth
- **FR-04.3**: Cup center: 22.5mm from door edge (standard)
- **FR-04.4**: Top/bottom hinge: 3" from door edge
- **FR-04.5**: Middle hinges: evenly distributed between top/bottom
- **FR-04.6**: Side panel SHALL include hinge plate drilling positions

### FR-05: Hardware Output

- **FR-05.1**: European hinges (with soft_close option flag)
- **FR-05.2**: Handle/knob position: centered horizontally, 3" from top (upper) or bottom (lower)
- **FR-05.3**: Handle placeholder in hardware list (qty = door count)

### FR-06: Edge Treatment

- **FR-06.1**: All 4 edges of door panel SHALL be flagged for edge banding
- **FR-06.2**: Edge banding perimeter = 2*(width + height) per door

### FR-07: Validation

- **FR-07.1**: Door count must be 1 or 2
- **FR-07.2**: Section height > 6" minimum
- **FR-07.3**: Section width > 6" minimum for single, > 12" for double
- **FR-07.4**: Reveal must be positive and < 0.5"
- **FR-07.5**: Door height > 60" SHALL trigger warning (weight concern)

---

## Data Models

### DoorConfig

```python
@dataclass(frozen=True)
class DoorConfig:
    """Configuration for door component."""
    count: int = 1                    # 1 = single, 2 = double
    hinge_side: str = "left"          # "left" or "right" (single door)
    reveal: float = 0.125             # Gap around door (inches)
    overlay: float = 0.5              # Overlay amount (overlay styles)
    soft_close: bool = True           # Soft-close hinges
    handle_position: str = "upper"    # "upper" or "lower"
```

### HingeSpec

```python
@dataclass(frozen=True)
class HingeSpec:
    """European hinge boring specification."""
    door_id: str              # Which door (e.g., "left_door", "right_door")
    side: str                 # "left" or "right" edge of door
    positions: tuple[float, ...]  # Y positions from door bottom (inches)
    cup_diameter: float = 35.0 * MM_TO_INCH  # ~1.378"
    cup_depth: float = 12.0 * MM_TO_INCH     # ~0.472"
    cup_inset: float = 22.5 * MM_TO_INCH     # ~0.886" from edge to center
```

### HingePlateSpec

```python
@dataclass(frozen=True)
class HingePlateSpec:
    """Hinge mounting plate specification for side panel."""
    panel_id: str             # "left_side" or "right_side"
    positions: tuple[float, ...]  # Y positions matching door hinges
    plate_width: float = 0.5  # Mounting plate width
    plate_height: float = 2.0 # Mounting plate height
```

---

## Technical Approach

### File: `src/cabinets/domain/components/door.py`

```python
from typing import Any
from dataclasses import dataclass
from ..entities import Panel
from ..value_objects import PanelType, Position, MaterialSpec
from .context import ComponentContext
from .results import GenerationResult, ValidationResult, HardwareItem
from .registry import component_registry

MM_TO_INCH = 0.03937008

@dataclass(frozen=True)
class HingeSpec:
    door_id: str
    side: str
    positions: tuple[float, ...]
    cup_diameter: float = 35.0 * MM_TO_INCH
    cup_depth: float = 12.0 * MM_TO_INCH
    cup_inset: float = 22.5 * MM_TO_INCH

def _calculate_hinge_count(door_height: float) -> int:
    """Determine hinge count based on door height."""
    if door_height < 40:
        return 2
    elif door_height <= 60:
        return 3
    else:
        return 4

def _calculate_hinge_positions(door_height: float) -> tuple[float, ...]:
    """Calculate hinge Y positions from door bottom."""
    count = _calculate_hinge_count(door_height)
    top_offset = 3.0    # 3" from top
    bottom_offset = 3.0 # 3" from bottom

    positions = [bottom_offset, door_height - top_offset]

    if count >= 3:
        middle = door_height / 2
        positions.insert(1, middle)

    if count == 4:
        # Add quarter points
        quarter = (door_height - top_offset - bottom_offset) / 3
        positions = [
            bottom_offset,
            bottom_offset + quarter,
            bottom_offset + 2 * quarter,
            door_height - top_offset,
        ]

    return tuple(sorted(positions))

class _HingedDoorBase:
    """Base class for hinged door components."""

    STYLE: str = ""  # Override in subclass

    def _parse_config(self, config: dict[str, Any]) -> tuple[int, str, float, float, bool]:
        """Parse door config. Returns (count, hinge_side, reveal, overlay, soft_close)."""
        return (
            config.get("count", 1),
            config.get("hinge_side", "left"),
            config.get("reveal", 0.125),
            config.get("overlay", 0.5),
            config.get("soft_close", True),
        )

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,
        count: int,
    ) -> tuple[float, float]:
        """Calculate single door dimensions. Override per style."""
        raise NotImplementedError

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []
        count, hinge_side, reveal, overlay, _ = self._parse_config(config)

        # Validate count
        if count not in (1, 2):
            errors.append("Door count must be 1 or 2")

        # Validate hinge_side
        if count == 1 and hinge_side not in ("left", "right"):
            errors.append("hinge_side must be 'left' or 'right'")

        # Validate reveal
        if reveal <= 0 or reveal >= 0.5:
            errors.append("Reveal must be between 0 and 0.5 inches")

        # Validate minimum dimensions
        if context.height < 6:
            errors.append("Section height must be at least 6 inches")
        if context.width < 6:
            errors.append("Section width must be at least 6 inches")
        if count == 2 and context.width < 12:
            errors.append("Double doors require section width >= 12 inches")

        # Warning for tall doors
        door_width, door_height = self._calculate_door_size(context, reveal, overlay, count)
        if door_height > 60:
            warnings.append(f"Door height {door_height:.1f}\" exceeds 60\" - consider weight")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        count, hinge_side, reveal, overlay, soft_close = self._parse_config(config)
        door_width, door_height = self._calculate_door_size(context, reveal, overlay, count)

        # Use door material if specified, else section material
        door_material = config.get("material") or context.material
        if isinstance(door_material, dict):
            door_material = MaterialSpec(
                thickness=door_material.get("thickness", 0.75),
            )

        panels = []
        hinge_specs = []
        hinge_positions = _calculate_hinge_positions(door_height)

        if count == 1:
            # Single door
            panels.append(Panel(
                panel_type=PanelType.DOOR,
                width=door_width,
                height=door_height,
                material=door_material,
                position=Position(context.position.x, context.position.y),
            ))
            hinge_specs.append(HingeSpec(
                door_id="door",
                side=hinge_side,
                positions=hinge_positions,
            ))
        else:
            # Double doors - split width with center gap
            center_gap = reveal
            single_width = (door_width - center_gap) / 2

            # Left door
            panels.append(Panel(
                panel_type=PanelType.DOOR,
                width=single_width,
                height=door_height,
                material=door_material,
                position=Position(context.position.x, context.position.y),
            ))
            hinge_specs.append(HingeSpec(
                door_id="left_door",
                side="left",
                positions=hinge_positions,
            ))

            # Right door
            panels.append(Panel(
                panel_type=PanelType.DOOR,
                width=single_width,
                height=door_height,
                material=door_material,
                position=Position(
                    context.position.x + single_width + center_gap,
                    context.position.y,
                ),
            ))
            hinge_specs.append(HingeSpec(
                door_id="right_door",
                side="right",
                positions=hinge_positions,
            ))

        # Hardware
        hinge_count = _calculate_hinge_count(door_height) * count
        hinge_type = "Soft-Close European Hinge" if soft_close else "European Hinge"

        hardware = [
            HardwareItem(
                name=hinge_type,
                quantity=hinge_count,
                sku="EURO-35MM-SC" if soft_close else "EURO-35MM",
                notes=f"35mm cup, {count} door(s)",
            ),
            HardwareItem(
                name="Handle/Knob",
                quantity=count,
                notes="Position placeholder - select handle separately",
            ),
        ]

        # Edge banding for all 4 edges
        perimeter = 2 * (door_width + door_height) * count
        hardware.append(HardwareItem(
            name="Edge Banding",
            quantity=1,
            notes=f"{perimeter:.1f} linear inches (all edges)",
        ))

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
        )

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        count, _, reveal, overlay, soft_close = self._parse_config(config)
        door_width, door_height = self._calculate_door_size(context, reveal, overlay, count)

        hinge_count = _calculate_hinge_count(door_height) * count
        hinge_type = "Soft-Close European Hinge" if soft_close else "European Hinge"

        items = [
            HardwareItem(
                name=hinge_type,
                quantity=hinge_count,
                sku="EURO-35MM-SC" if soft_close else "EURO-35MM",
                notes=f"35mm cup, {count} door(s)",
            ),
            HardwareItem(
                name="Handle/Knob",
                quantity=count,
                notes="Position placeholder",
            ),
        ]

        perimeter = 2 * (door_width + door_height) * count
        items.append(HardwareItem(
            name="Edge Banding",
            quantity=1,
            notes=f"{perimeter:.1f} linear inches",
        ))

        return items


@component_registry.register("door.hinged.overlay")
class OverlayDoorComponent(_HingedDoorBase):
    """Full overlay hinged door - covers cabinet face."""

    STYLE = "overlay"

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,
        count: int,
    ) -> tuple[float, float]:
        # Full overlay: door overlaps cabinet sides by 'overlay' amount
        door_height = context.height + (2 * overlay) - reveal

        if count == 1:
            door_width = context.width + (2 * overlay) - reveal
        else:
            # Double doors share the overlay
            door_width = context.width + (2 * overlay) - reveal

        return door_width, door_height


@component_registry.register("door.hinged.inset")
class InsetDoorComponent(_HingedDoorBase):
    """Inset hinged door - sits inside face frame opening."""

    STYLE = "inset"

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,  # Not used for inset
        count: int,
    ) -> tuple[float, float]:
        # Inset: door sits inside opening with reveal gap
        door_height = context.height - (2 * reveal)
        door_width = context.width - (2 * reveal)
        return door_width, door_height


@component_registry.register("door.hinged.partial")
class PartialOverlayDoorComponent(_HingedDoorBase):
    """Partial overlay hinged door - reveals some face frame."""

    STYLE = "partial"

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,
        count: int,
    ) -> tuple[float, float]:
        # Partial overlay: half the overlay of full overlay
        partial_overlay = overlay / 2
        door_height = context.height + (2 * partial_overlay) - reveal
        door_width = context.width + (2 * partial_overlay) - reveal
        return door_width, door_height
```

---

## Configuration Examples

### Single Overlay Door (Left Hinge)

```yaml
sections:
  - type: doored
    component: door.hinged.overlay
    config:
      count: 1
      hinge_side: left
      reveal: 0.125
      overlay: 0.5
      soft_close: true
```

### Double Inset Doors

```yaml
sections:
  - type: doored
    component: door.hinged.inset
    config:
      count: 2
      reveal: 0.0625  # 1/16" gap
```

---

## Hardware Output Example

```
Component: door.hinged.overlay
Section: 24" wide x 30" high

Door Dimensions: 24.875" x 30.875" (single)
Hinge Count: 2 (door < 40")

Hardware List:
  - Soft-Close European Hinge (EURO-35MM-SC): 2 qty
  - Handle/Knob: 1 qty
  - Edge Banding: 111.5 linear inches
```

---

## Hinge Boring Specification

```
Door: 30" height, left hinge

Hinge Cup Positions:
  - Hinge 1: Y=3.0" from bottom, X=0.886" from left edge
  - Hinge 2: Y=27.0" from bottom, X=0.886" from left edge

Cup Specs:
  - Diameter: 35mm (1.378")
  - Depth: 12mm (0.472")

Side Panel Plate Positions:
  - Corresponding Y positions on left_side panel
```

---

## PanelType Extension

Add to `value_objects.py`:

```python
class PanelType(Enum):
    # ... existing ...
    DOOR = "door"
```

---

## Validation Rules

| Rule | Check | Error/Warning |
|------|-------|---------------|
| V-01 | count in (1, 2) | ERROR: "Door count must be 1 or 2" |
| V-02 | hinge_side valid | ERROR: "hinge_side must be 'left' or 'right'" |
| V-03 | reveal in range | ERROR: "Reveal must be between 0 and 0.5 inches" |
| V-04 | min height | ERROR: "Section height must be at least 6 inches" |
| V-05 | min width | ERROR: "Section width must be at least 6/12 inches" |
| V-06 | tall door | WARNING: "Door height exceeds 60\" - consider weight" |

---

## Testing Strategy

### Unit Tests

| Test | Assertion |
|------|-----------|
| `door.hinged.overlay` registers | Registry lookup succeeds |
| `door.hinged.inset` registers | Registry lookup succeeds |
| `door.hinged.partial` registers | Registry lookup succeeds |
| Overlay sizing | door_width = section + 2*overlay - reveal |
| Inset sizing | door_width = section - 2*reveal |
| Single door panel | 1 Panel with correct dimensions |
| Double door panels | 2 Panels with split width |
| Hinge count < 40" | 2 hinges |
| Hinge count 40-60" | 3 hinges |
| Hinge count > 60" | 4 hinges |
| Hinge positions | 3" from top/bottom, evenly distributed |
| Hardware list | Includes hinges, handle, edge banding |
| Validation: invalid count | Error returned |
| Validation: tall door | Warning returned |

### Integration Tests

- Section with `door.hinged.overlay` generates correct panel + hardware
- Double doors produce 2 panels with matching hinge specs
- Hardware aggregation includes all door hinges across sections

---

## Implementation Phases

### Phase 1: Core Door Components (Est. 0.5 day)
- [ ] Add `PanelType.DOOR` to value_objects.py
- [ ] Implement `HingeSpec` dataclass
- [ ] Implement `_HingedDoorBase` with shared logic
- [ ] Implement `OverlayDoorComponent`

### Phase 2: Additional Styles (Est. 0.5 day)
- [ ] Implement `InsetDoorComponent`
- [ ] Implement `PartialOverlayDoorComponent`
- [ ] Add door material override support

### Phase 3: Hardware & Validation (Est. 0.5 day)
- [ ] Implement hinge count calculation
- [ ] Implement hinge position calculation
- [ ] Add all validation rules
- [ ] Edge banding calculation

### Phase 4: Testing (Est. 0.5 day)
- [ ] Unit tests for all three components
- [ ] Integration tests with registry
- [ ] Hardware output verification

---

## Dependencies & Risks

### Dependencies
- FRD-05: `Component` protocol, `ComponentContext`, `GenerationResult`, `HardwareItem`
- Existing: `Panel`, `Position`, `MaterialSpec`
- New: `PanelType.DOOR` enum value

### Risks

| Risk | Mitigation |
|------|------------|
| Hinge boring specs not consumed | Document as metadata; implement in cut list export |
| Material override complexity | Support dict config with MaterialSpec fallback |
| Face frame assumptions | Document that dimensions assume standard face frame or frameless |

---

## Open Questions

1. **Face frame dimensions**: Should we assume standard 1.5" face frame or frameless?
   - Proposed: Frameless (overlay relative to cabinet sides), face frame support in future FRD

2. **Hinge plate drilling output**: How to output side panel drilling specs?
   - Proposed: Include in panel metadata, consume during cut list generation

3. **Handle positioning**: Should handle position be configurable X/Y?
   - Proposed: Defer detailed handle config; current implementation uses standard positions

---

*FRD-07 ready for implementation: 2025-12-27*
