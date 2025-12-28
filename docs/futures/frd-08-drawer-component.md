# FRD-08: Drawer Component

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Depends On:** FRD-05 (Component Registry)

---

## Functional Requirements

### FR-01: Component Registration

- `drawer.standard` - basic drawer box with front
- `drawer.file` - deeper drawer for hanging files (letter: 10.5" min, legal: 12" min)

### FR-02: Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `front_height` | float | required | Drawer front panel height (min 3") |
| `slide_type` | enum | `side_mount` | `side_mount`, `undermount`, `center_mount` |
| `slide_length` | int/str | `auto` | 12, 14, 16, 18, 20, 22, 24 inches or `auto` |
| `soft_close` | bool | `true` | Soft-close slides |
| `front_style` | enum | `overlay` | `overlay` or `inset` |
| `file_type` | str | `letter` | `letter` or `legal` (file drawer only) |

### FR-03: Slide Clearances

| Slide Type | Per-Side Clearance | Total Width Reduction |
|------------|-------------------|----------------------|
| `side_mount` | 0.5" | 1.0" |
| `undermount` | 0.1875" (3/16") | 0.375" |
| `center_mount` | 0" | 0" |

### FR-04: Box Dimension Formulas

- `box_width` = section_width - (2 * side_clearance)
- `box_height` = front_height - 0.125" (reveal) - 0.5" (slide clearance)
- `box_depth` = slide_length - 1" (rear clearance)
- Bottom: 1/4" plywood inset into 1/4" dado
- Sides: 1/2" plywood

### FR-05: Auto Slide Length Selection

| Cabinet Depth | Selected Length |
|--------------|-----------------|
| < 14" | 12" |
| 14-16" | 14" |
| 16-18" | 16" |
| 18-20" | 18" |
| 20-22" | 20" |
| 22-24" | 22" |
| >= 24" | 24" |

### FR-06: Hardware Output

- Drawer slides: 2 per drawer (1 for center_mount)
- Mounting screws: 4 per slide (#8 x 5/8" pan head)
- Handle/pull: 1 per drawer (position: centered, 1.5" from top)
- Edge banding: perimeter of drawer front

### FR-07: Validation Rules

| Rule | Condition | Result |
|------|-----------|--------|
| V-01 | slide_length > section_depth - 1" | ERROR |
| V-02 | front_height < 3" | ERROR |
| V-03 | front_height > section_height | ERROR |
| V-04 | box_width <= 0 | ERROR |
| V-05 | file drawer height < 10.5"/12" | ERROR |
| V-06 | center_mount + file drawer | WARNING |

---

## Data Models

```python
# src/cabinets/domain/components/drawer.py

SLIDE_CLEARANCES = {"side_mount": 0.5, "undermount": 0.1875, "center_mount": 0.0}
VALID_SLIDE_LENGTHS = [12, 14, 16, 18, 20, 22, 24]

@dataclass(frozen=True)
class DrawerBoxSpec:
    box_width: float
    box_height: float
    box_depth: float
    front_width: float
    front_height: float
    bottom_thickness: float = 0.25
    side_thickness: float = 0.5
    dado_depth: float = 0.25

@dataclass(frozen=True)
class SlideMountSpec:
    panel_id: str           # "left_side" or "right_side"
    slide_type: str
    position_y: float       # From section bottom
    slide_length: int
    mounting_holes: tuple[float, ...]  # X positions from front
```

---

## Implementation

```python
def _auto_select_slide_length(depth: float) -> int:
    for length in VALID_SLIDE_LENGTHS:
        if depth < length + 2:
            return length
    return 24

class _DrawerBase:
    MIN_FRONT_HEIGHT = 3.0

    def validate(self, config: dict, context: ComponentContext) -> ValidationResult:
        errors = []
        front_height = config.get("front_height", 6.0)
        slide_type = config.get("slide_type", "side_mount")
        slide_length = config.get("slide_length", "auto")
        if slide_length == "auto":
            slide_length = _auto_select_slide_length(context.depth)

        if slide_type not in SLIDE_CLEARANCES:
            errors.append(f"Invalid slide_type '{slide_type}'")
        if slide_length not in VALID_SLIDE_LENGTHS:
            errors.append(f"Invalid slide_length {slide_length}")
        if slide_length > context.depth - 1:
            errors.append("Slide length exceeds section depth")
        if front_height < self.MIN_FRONT_HEIGHT:
            errors.append(f"Front height below {self.MIN_FRONT_HEIGHT}\"")
        if context.width - (2 * SLIDE_CLEARANCES.get(slide_type, 0.5)) <= 0:
            errors.append("Section too narrow for slides")

        return ValidationResult(tuple(errors), ())

    def generate(self, config: dict, context: ComponentContext) -> GenerationResult:
        # Parse config, calculate box dimensions, generate panels + hardware
        ...

@component_registry.register("drawer.standard")
class StandardDrawerComponent(_DrawerBase):
    pass

@component_registry.register("drawer.file")
class FileDrawerComponent(_DrawerBase):
    MIN_FILE_HEIGHT = {"letter": 10.5, "legal": 12.0}

    def validate(self, config: dict, context: ComponentContext) -> ValidationResult:
        result = super().validate(config, context)
        errors = list(result.errors)
        # Check file drawer interior height meets minimum
        file_type = config.get("file_type", "letter")
        min_height = self.MIN_FILE_HEIGHT[file_type]
        # ... validate box_height >= min_height
        return ValidationResult(tuple(errors), result.warnings)
```

---

## PanelType Extension

```python
class PanelType(Enum):
    # existing...
    DRAWER_FRONT = "drawer_front"
    DRAWER_SIDE = "drawer_side"
    DRAWER_BOX_FRONT = "drawer_box_front"
    DRAWER_BOTTOM = "drawer_bottom"
```

---

## Configuration Examples

```yaml
# Standard drawer
sections:
  - component: drawer.standard
    config:
      front_height: 6.0
      slide_type: side_mount
      slide_length: auto
      soft_close: true

# File drawer (legal)
sections:
  - component: drawer.file
    config:
      front_height: 14.0
      slide_type: undermount
      slide_length: 22
      file_type: legal
```

---

## Hardware Output Example

```
drawer.standard | 18"W x 24"D section | front_height: 6"

Box: 17"W x 5.375"H x 21"D (22" slides)

Hardware:
  - Soft-Close Drawer Slide (22"): 2 qty
  - Mounting Screw #8x5/8": 8 qty
  - Handle/Pull: 1 qty
  - Edge Banding: 48.75 linear in
```

---

## Testing Strategy

| Test | Expected |
|------|----------|
| `drawer.standard` registers | Registry lookup succeeds |
| `drawer.file` registers | Registry lookup succeeds |
| Auto slide: 14" depth | Returns 12" |
| Side-mount clearance | box_width = section - 1" |
| Undermount clearance | box_width = section - 0.375" |
| Hardware: side_mount | 2 slides, 8 screws |
| Hardware: center_mount | 1 slide, 4 screws |
| Slide too long | Validation error |
| File drawer too shallow | Validation error |

---

## Implementation Phases

1. **Core** (0.5 day): Add PanelTypes, implement `_DrawerBase`, `StandardDrawerComponent`
2. **File Drawer** (0.5 day): `FileDrawerComponent`, height validation
3. **Hardware** (0.5 day): Slide specs, mounting holes, edge banding
4. **Testing** (0.5 day): Unit + integration tests

---

## Dependencies

- FRD-05: Component protocol, ComponentContext, GenerationResult, HardwareItem
- Existing: Panel, Position, MaterialSpec
- New: PanelType.DRAWER_* enum values

---

## Open Questions

1. **Drawer stacks**: Handle multiple drawers per section?
   - Proposed: Single drawer per component; section builder handles stacking

2. **Box material**: Allow override from default 1/2" plywood?
   - Proposed: Add config option in future iteration

---

*FRD-08 ready for implementation: 2025-12-27*
