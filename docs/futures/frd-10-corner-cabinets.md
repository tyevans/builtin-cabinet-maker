# FRD-10: Corner Cabinet Solutions

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** Medium
**Depends On:** FRD-02 (Room & Wall Geometry), FRD-05 (Component Registry), FRD-07 (Door Component)

---

## Problem Statement

90-degree inside corners where two wall runs meet create dead space that standard rectangular cabinets cannot access. Users need specialized corner cabinet types that:

- Maximize usable storage in corner locations
- Integrate with adjacent standard sections on both walls
- Calculate correct footprints to prevent collisions with adjacent sections
- Generate non-rectangular panels (45-degree cuts, L-shapes)

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Three corner types registered | `corner.lazy_susan`, `corner.blind`, `corner.diagonal` |
| Correct footprint calculation | Adjacent sections start after corner footprint on each wall |
| Hardware integration | Lazy susan hardware, bi-fold hinges in hardware list |
| Panel generation | Non-rectangular panels with correct geometry |
| Wall integration | Corner occupies space on both wall segments |

---

## Scope

### In Scope
- `corner.lazy_susan` - rotating tray corner cabinet
- `corner.blind` - dead corner with accessible pull-out section
- `corner.diagonal` - 45-degree angled front face
- Corner footprint calculations for both wall segments
- Non-rectangular panel generation (45-degree cuts, L-shapes)
- Lazy susan hardware (pole, trays, bearings)
- Bi-fold door hinge hardware

### Out of Scope
- Non-90-degree corners
- Outside corners (cabinets don't wrap outside corners)
- Corner appliance garages
- Motorized lazy susan mechanisms

---

## Functional Requirements

### FR-01: Corner Component IDs

- **FR-01.1**: `corner.lazy_susan` SHALL register via `@component_registry.register`
- **FR-01.2**: `corner.blind` SHALL register via `@component_registry.register`
- **FR-01.3**: `corner.diagonal` SHALL register via `@component_registry.register`
- **FR-01.4**: All corner components SHALL implement the `Component` protocol

### FR-02: Corner Geometry

- **FR-02.1**: Corner cabinets SHALL occupy space on BOTH wall segments
- **FR-02.2**: `left_footprint` = space consumed on left wall (inches)
- **FR-02.3**: `right_footprint` = space consumed on right wall (inches)
- **FR-02.4**: Adjacent sections on left wall SHALL start after `left_footprint`
- **FR-02.5**: Adjacent sections on right wall SHALL start after `right_footprint`
- **FR-02.6**: Total corner depth SHALL be configurable (default: cabinet depth)

### FR-03: Lazy Susan Configuration

- **FR-03.1**: `tray_diameter` SHALL be explicit or auto-calculated: `(depth * 2) - 4`
- **FR-03.2**: `tray_count` SHALL specify number of rotating shelves (default: 2)
- **FR-03.3**: `door_style` SHALL be "single" or "bifold" (default: "bifold")
- **FR-03.4**: `door_clearance` SHALL ensure door clears tray rotation (min: 2")
- **FR-03.5**: Lazy susan footprint: equal on both walls = `depth + door_clearance`

### FR-04: Blind Corner Configuration

- **FR-04.1**: `blind_side` SHALL be "left" or "right" (which side is dead)
- **FR-04.2**: `accessible_width` SHALL specify usable pull-out width
- **FR-04.3**: `pull_out` (boolean) SHALL enable/disable pull-out hardware
- **FR-04.4**: `filler_width` SHALL specify filler panel on blind side (default: 3")
- **FR-04.5**: Blind footprint: blind side = `depth`, accessible side = `accessible_width + filler_width`

### FR-05: Diagonal Configuration

- **FR-05.1**: `face_width` SHALL specify diagonal panel width (front face)
- **FR-05.2**: `face_width` default: `depth * sqrt(2)` (45-45-90 triangle)
- **FR-05.3**: Side panels SHALL have 45-degree angle cuts
- **FR-05.4**: `shelf_shape` SHALL be "triangular" or "squared" (default: "squared")
- **FR-05.5**: Diagonal footprint: equal on both walls = `depth`

### FR-06: Panel Generation

- **FR-06.1**: Lazy susan SHALL generate: 2 side panels, top, bottom, back (L-shape or 2 panels)
- **FR-06.2**: Blind SHALL generate: 2 side panels, top, bottom, back, filler panel
- **FR-06.3**: Diagonal SHALL generate: 2 angled side panels, diagonal face, top, bottom, back
- **FR-06.4**: Angled panels SHALL include cut angle metadata (45 degrees)
- **FR-06.5**: L-shaped back panels SHALL be flagged as non-rectangular

### FR-07: Hardware Requirements

- **FR-07.1**: Lazy susan hardware: center pole, trays (qty = tray_count), bearings (qty = tray_count)
- **FR-07.2**: Bi-fold hinges: 2 per door leaf (4 total for bi-fold pair)
- **FR-07.3**: Blind pull-out (if enabled): slides, pull-out tray
- **FR-07.4**: All hardware SHALL be returned in `GenerationResult.hardware`

### FR-08: Validation

- **FR-08.1**: `tray_diameter` SHALL NOT exceed available interior space
- **FR-08.2**: `accessible_width` SHALL be >= 12" for blind corners
- **FR-08.3**: `face_width` SHALL be >= 18" for diagonal corners
- **FR-08.4**: Corner depth SHALL match adjacent section depths
- **FR-08.5**: Corner cabinet height SHALL match adjacent cabinet heights

---

## Data Models

### CornerConfig Base

```python
# src/cabinets/domain/components/corner.py

from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class CornerFootprint:
    """Space consumed by corner on each wall segment."""
    left_wall: float   # Inches consumed on left wall
    right_wall: float  # Inches consumed on right wall
```

### LazySusanConfig

```python
@dataclass(frozen=True)
class LazySusanConfig:
    """Configuration for lazy susan corner cabinet."""
    tray_diameter: float | None = None  # Auto-calculate if None
    tray_count: int = 2
    door_style: Literal["single", "bifold"] = "bifold"
    door_clearance: float = 2.0  # Inches
```

### BlindCornerConfig

```python
@dataclass(frozen=True)
class BlindCornerConfig:
    """Configuration for blind corner cabinet."""
    blind_side: Literal["left", "right"] = "left"
    accessible_width: float = 24.0  # Inches
    pull_out: bool = True
    filler_width: float = 3.0  # Inches
```

### DiagonalCornerConfig

```python
@dataclass(frozen=True)
class DiagonalCornerConfig:
    """Configuration for diagonal corner cabinet."""
    face_width: float | None = None  # Auto-calculate if None
    shelf_shape: Literal["triangular", "squared"] = "squared"
    shelf_count: int = 2
```

### AngledPanel Extension

```python
@dataclass(frozen=True)
class AngledCutSpec:
    """Specification for angled panel cuts."""
    edge: Literal["left", "right", "top", "bottom"]
    angle: float  # Degrees from perpendicular (0 = square cut)

@dataclass(frozen=True)
class PanelGeometry:
    """Extended panel geometry for non-rectangular panels."""
    shape: Literal["rectangular", "triangular", "l_shaped"]
    angled_cuts: tuple[AngledCutSpec, ...] = ()
```

---

## Technical Approach

### File: `src/cabinets/domain/components/corner.py`

```python
from typing import Any
from math import sqrt
from ..entities import Panel
from ..value_objects import PanelType, Position, MaterialSpec
from .context import ComponentContext
from .results import GenerationResult, ValidationResult, HardwareItem
from .registry import component_registry

def _calculate_footprint_lazy_susan(depth: float, door_clearance: float) -> tuple[float, float]:
    """Equal footprint on both walls."""
    footprint = depth + door_clearance
    return footprint, footprint

def _calculate_footprint_blind(
    depth: float,
    accessible_width: float,
    filler_width: float,
    blind_side: str,
) -> tuple[float, float]:
    """Asymmetric footprint based on blind side."""
    accessible_footprint = accessible_width + filler_width
    if blind_side == "left":
        return depth, accessible_footprint  # Left is dead, right is accessible
    return accessible_footprint, depth  # Right is dead, left is accessible

def _calculate_footprint_diagonal(depth: float) -> tuple[float, float]:
    """Equal footprint on both walls."""
    return depth, depth


@component_registry.register("corner.lazy_susan")
class LazySusanCornerComponent:
    """Lazy susan corner cabinet with rotating trays."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []

        tray_diameter = config.get("tray_diameter")
        tray_count = config.get("tray_count", 2)

        # Auto-calculate diameter if not specified
        if tray_diameter is None:
            tray_diameter = (context.depth * 2) - 4

        # Validate tray fits
        max_diameter = (context.depth * 2) - 2  # Leave 1" clearance per side
        if tray_diameter > max_diameter:
            errors.append(f"Tray diameter {tray_diameter:.1f}\" exceeds max {max_diameter:.1f}\"")

        if tray_count < 1 or tray_count > 5:
            errors.append("Tray count must be between 1 and 5")

        if tray_diameter < 16:
            warnings.append("Small tray diameter may limit usability")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        tray_count = config.get("tray_count", 2)
        door_style = config.get("door_style", "bifold")
        door_clearance = config.get("door_clearance", 2.0)

        tray_diameter = config.get("tray_diameter") or (context.depth * 2) - 4

        panels = self._generate_panels(context, door_clearance)
        hardware = self._generate_hardware(tray_count, tray_diameter, door_style)

        return GenerationResult(panels=tuple(panels), hardware=tuple(hardware))

    def _generate_panels(self, context: ComponentContext, door_clearance: float) -> list[Panel]:
        # Simplified: generates standard cabinet box for corner
        # Real implementation would generate L-shaped back
        return [
            Panel(PanelType.LEFT_SIDE, context.depth, context.height, context.material),
            Panel(PanelType.RIGHT_SIDE, context.depth, context.height, context.material),
            Panel(PanelType.TOP, context.depth + door_clearance, context.depth, context.material),
            Panel(PanelType.BOTTOM, context.depth + door_clearance, context.depth, context.material),
        ]

    def _generate_hardware(
        self, tray_count: int, tray_diameter: float, door_style: str
    ) -> list[HardwareItem]:
        items = [
            HardwareItem("Lazy Susan Center Pole", 1, "LS-POLE-36", f"36\" pole"),
            HardwareItem("Lazy Susan Tray", tray_count, "LS-TRAY-28", f"{tray_diameter:.0f}\" diameter"),
            HardwareItem("Lazy Susan Bearing", tray_count, "LS-BEARING", "Ball bearing swivel"),
        ]

        if door_style == "bifold":
            items.append(HardwareItem("Bi-fold Hinge", 4, "BIFOLD-HINGE", "2 per door leaf"))

        return items

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        tray_count = config.get("tray_count", 2)
        door_style = config.get("door_style", "bifold")
        tray_diameter = config.get("tray_diameter") or (context.depth * 2) - 4
        return self._generate_hardware(tray_count, tray_diameter, door_style)


@component_registry.register("corner.blind")
class BlindCornerComponent:
    """Blind corner cabinet with dead space and accessible section."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []

        accessible_width = config.get("accessible_width", 24.0)
        blind_side = config.get("blind_side", "left")

        if accessible_width < 12:
            errors.append("Accessible width must be at least 12 inches")

        if blind_side not in ("left", "right"):
            errors.append("blind_side must be 'left' or 'right'")

        if accessible_width > 36:
            warnings.append("Wide accessible section may reduce pull-out effectiveness")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        accessible_width = config.get("accessible_width", 24.0)
        filler_width = config.get("filler_width", 3.0)
        pull_out = config.get("pull_out", True)

        panels = self._generate_panels(context, accessible_width, filler_width)
        hardware = self._generate_hardware(pull_out, context.height)

        return GenerationResult(panels=tuple(panels), hardware=tuple(hardware))

    def _generate_panels(
        self, context: ComponentContext, accessible_width: float, filler_width: float
    ) -> list[Panel]:
        return [
            Panel(PanelType.LEFT_SIDE, context.depth, context.height, context.material),
            Panel(PanelType.RIGHT_SIDE, context.depth, context.height, context.material),
            Panel(PanelType.TOP, accessible_width + filler_width, context.depth, context.material),
            Panel(PanelType.BOTTOM, accessible_width + filler_width, context.depth, context.material),
            Panel(PanelType.DIVIDER, filler_width, context.height, context.material),  # Filler
        ]

    def _generate_hardware(self, pull_out: bool, height: float) -> list[HardwareItem]:
        items = []
        if pull_out:
            items.extend([
                HardwareItem("Blind Corner Pull-out Slides", 1, "BC-SLIDE-22", "22\" full extension"),
                HardwareItem("Blind Corner Pull-out Tray", 1, "BC-TRAY", "Wire basket tray"),
            ])
        return items

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        pull_out = config.get("pull_out", True)
        return self._generate_hardware(pull_out, context.height)


@component_registry.register("corner.diagonal")
class DiagonalCornerComponent:
    """Diagonal corner cabinet with 45-degree angled front face."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []

        face_width = config.get("face_width")
        if face_width is None:
            face_width = context.depth * sqrt(2)

        if face_width < 18:
            errors.append("Face width must be at least 18 inches")

        shelf_count = config.get("shelf_count", 2)
        if shelf_count < 0 or shelf_count > 6:
            errors.append("Shelf count must be between 0 and 6")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        face_width = config.get("face_width") or context.depth * sqrt(2)
        shelf_count = config.get("shelf_count", 2)
        shelf_shape = config.get("shelf_shape", "squared")

        panels = self._generate_panels(context, face_width, shelf_count, shelf_shape)
        hardware = self._generate_hardware(shelf_count)

        return GenerationResult(panels=tuple(panels), hardware=tuple(hardware))

    def _generate_panels(
        self,
        context: ComponentContext,
        face_width: float,
        shelf_count: int,
        shelf_shape: str,
    ) -> list[Panel]:
        panels = [
            # Angled side panels (45-degree cuts)
            Panel(PanelType.LEFT_SIDE, context.depth, context.height, context.material),
            Panel(PanelType.RIGHT_SIDE, context.depth, context.height, context.material),
            # Diagonal face panel
            Panel(PanelType.DIVIDER, face_width, context.height, context.material),
            Panel(PanelType.TOP, context.depth, context.depth, context.material),
            Panel(PanelType.BOTTOM, context.depth, context.depth, context.material),
        ]

        # Add shelves
        for _ in range(shelf_count):
            if shelf_shape == "triangular":
                # Triangular shelf: depth x depth (roughly)
                panels.append(Panel(PanelType.SHELF, context.depth, context.depth, context.material))
            else:
                # Squared shelf: clips back corners
                panels.append(Panel(PanelType.SHELF, context.depth * 0.8, context.depth * 0.8, context.material))

        return panels

    def _generate_hardware(self, shelf_count: int) -> list[HardwareItem]:
        items = []
        if shelf_count > 0:
            items.append(HardwareItem("Shelf Pin", shelf_count * 4, "SP-5MM", "5mm brass pins"))
        return items

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        shelf_count = config.get("shelf_count", 2)
        return self._generate_hardware(shelf_count)
```

---

## Configuration Examples

### Lazy Susan Corner

```yaml
room:
  walls:
    - { length: 96, height: 84, name: "left" }
    - { length: 72, height: 84, angle: 90, name: "right" }

cabinet:
  sections:
    - wall: "left"
      component: corner.lazy_susan
      config:
        tray_count: 3
        door_style: bifold
        door_clearance: 2.5
    - wall: "left"
      width: 24
      shelves: 4
```

### Blind Corner

```yaml
cabinet:
  sections:
    - component: corner.blind
      config:
        blind_side: left
        accessible_width: 24
        pull_out: true
        filler_width: 3
```

### Diagonal Corner

```yaml
cabinet:
  sections:
    - component: corner.diagonal
      config:
        face_width: 24
        shelf_shape: squared
        shelf_count: 3
```

---

## Footprint Calculation Reference

| Type | Left Footprint | Right Footprint | Notes |
|------|----------------|-----------------|-------|
| Lazy Susan | depth + clearance | depth + clearance | Symmetric |
| Blind (left dead) | depth | accessible + filler | Asymmetric |
| Blind (right dead) | accessible + filler | depth | Asymmetric |
| Diagonal | depth | depth | Symmetric |

---

## Validation Rules

| Rule | Check | Error/Warning |
|------|-------|---------------|
| V-01 | tray_diameter <= max | ERROR: "Tray diameter exceeds max" |
| V-02 | tray_count 1-5 | ERROR: "Tray count must be between 1 and 5" |
| V-03 | accessible_width >= 12 | ERROR: "Accessible width must be at least 12 inches" |
| V-04 | blind_side valid | ERROR: "blind_side must be 'left' or 'right'" |
| V-05 | face_width >= 18 | ERROR: "Face width must be at least 18 inches" |
| V-06 | shelf_count 0-6 | ERROR: "Shelf count must be between 0 and 6" |
| V-07 | small tray | WARNING: "Small tray diameter may limit usability" |
| V-08 | wide accessible | WARNING: "Wide accessible section may reduce pull-out effectiveness" |

---

## PanelType Extensions

Add to `value_objects.py`:

```python
class PanelType(Enum):
    # ... existing ...
    DIAGONAL_FACE = "diagonal_face"
    FILLER = "filler"
```

---

## Testing Strategy

### Unit Tests

| Test | Assertion |
|------|-----------|
| `corner.lazy_susan` registers | Registry lookup succeeds |
| `corner.blind` registers | Registry lookup succeeds |
| `corner.diagonal` registers | Registry lookup succeeds |
| Lazy susan footprint | Both walls = depth + clearance |
| Blind footprint (left dead) | Left = depth, Right = accessible + filler |
| Diagonal footprint | Both walls = depth |
| Tray diameter auto-calc | (depth * 2) - 4 |
| Face width auto-calc | depth * sqrt(2) |
| Hardware: lazy susan | Pole, trays, bearings, bi-fold hinges |
| Hardware: blind pull-out | Slides, tray |
| Validation: large tray | Error returned |
| Validation: small accessible | Error returned |

### Integration Tests

- Corner cabinet integrated with room geometry
- Adjacent sections positioned after corner footprint
- Hardware aggregated across all corner types

---

## Implementation Phases

### Phase 1: Core Infrastructure (Est. 0.5 day)
- [ ] Add `PanelType.DIAGONAL_FACE`, `PanelType.FILLER`
- [ ] Create `corner.py` module
- [ ] Implement `CornerFootprint` dataclass
- [ ] Implement footprint calculation functions

### Phase 2: Lazy Susan Component (Est. 1 day)
- [ ] Implement `LazySusanCornerComponent`
- [ ] Tray diameter calculation
- [ ] Panel generation
- [ ] Hardware list (pole, trays, bearings, bi-fold hinges)

### Phase 3: Blind Corner Component (Est. 0.5 day)
- [ ] Implement `BlindCornerComponent`
- [ ] Asymmetric footprint calculation
- [ ] Pull-out hardware option

### Phase 4: Diagonal Corner Component (Est. 0.5 day)
- [ ] Implement `DiagonalCornerComponent`
- [ ] Face width calculation
- [ ] Triangular vs squared shelf shapes

### Phase 5: Room Integration (Est. 1 day)
- [ ] Update `RoomLayoutService` to handle corner footprints
- [ ] Position adjacent sections correctly
- [ ] Integration tests

---

## Dependencies & Risks

### Dependencies
- FRD-02: Room geometry for corner detection and wall segment assignment
- FRD-05: `Component` protocol, `ComponentContext`, `GenerationResult`, `HardwareItem`
- FRD-07: Door component for bi-fold door integration

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Non-rectangular panel complexity | High | Start with simplified rectangular approximations |
| Footprint calculation errors | High | Extensive unit tests with known configurations |
| Lazy susan hardware variations | Medium | Use generic hardware IDs, notes for specifics |

---

## Open Questions

1. **L-shaped back panels**: Generate as single L-shaped panel or two rectangular panels?
   - Proposed: Two rectangular panels (simpler cut list)

2. **Door integration**: Should corner components generate their own doors or delegate to FRD-07?
   - Proposed: Include door hardware in corner component; delegate panel generation to door component

3. **Shelf pin hole patterns**: Should diagonal shelves have shelf pin support?
   - Proposed: Yes, use standard pin pattern on accessible edges

---

*FRD-10 ready for implementation: 2025-12-27*
