# FRD-09: Cubby & Grid Layouts

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** Medium
**Depends On:** FRD-05 (Component Registry Architecture)

---

## Problem Statement

Users need grid-based storage subdivisions (cubbies) for organizing books, bins, and small items. Current implementation lacks:
- Uniform grids with equal-sized compartments
- Variable grids with custom row heights and column widths
- Proper divider intersection joinery
- Edge-sharing logic to avoid double-thickness walls

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Two cubby types registered | `cubby.uniform` and `cubby.variable` in registry |
| Correct divider counts | rows-1 horizontal, (columns-1)*rows vertical |
| Intersection joinery | Half-lap notch positions calculated |
| Size validation | Minimum 6"x6" interior enforced |
| No double-thickness | Shared edges between adjacent cubbies |

---

## Scope

### In Scope
- `cubby.uniform` component (equal-sized grid)
- `cubby.variable` component (custom row/column dimensions)
- Horizontal and vertical divider generation
- Half-lap notch calculations for intersections
- Minimum cubby size validation

### Out of Scope
- Dado joinery for outer frame attachment
- Removable divider hardware
- Angled or diagonal dividers
- Cubby doors or drawer fronts

---

## Functional Requirements

### FR-01: Uniform Cubby Component (`cubby.uniform`)

- **FR-01.1**: SHALL register as `cubby.uniform` via `@component_registry.register`
- **FR-01.2**: SHALL accept `rows: int` and `columns: int` configuration
- **FR-01.3**: SHALL calculate equal cubby sizes:
  - cubby_width = (section_width - (columns-1) * divider_thickness) / columns
  - cubby_height = (section_height - (rows-1) * divider_thickness) / rows
- **FR-01.4**: SHALL use section material thickness as default divider thickness
- **FR-01.5**: SHALL support `divider_thickness: float` override

### FR-02: Variable Cubby Component (`cubby.variable`)

- **FR-02.1**: SHALL register as `cubby.variable` via `@component_registry.register`
- **FR-02.2**: SHALL accept `row_heights: list[float]` (inches)
- **FR-02.3**: SHALL accept `column_widths: list[float]` (inches)
- **FR-02.4**: SHALL validate total dimensions fit within section
- **FR-02.5**: SHALL support mixed uniform/variable (one array, one count)

### FR-03: Divider Generation

- **FR-03.1**: Horizontal dividers SHALL span full section width
- **FR-03.2**: Vertical dividers SHALL fit between horizontal dividers (not full height)
- **FR-03.3**: Horizontal divider count = rows - 1
- **FR-03.4**: Vertical divider count = (columns - 1) * rows
- **FR-03.5**: Each divider SHALL be a `CutPiece` with label indicating position

### FR-04: Intersection Joinery

- **FR-04.1**: SHALL support `joinery: "half_lap" | "dado"` configuration
- **FR-04.2**: Half-lap notch depth = divider_thickness / 2
- **FR-04.3**: Half-lap notch width = divider_thickness
- **FR-04.4**: Horizontal dividers: notches on top edge at vertical positions
- **FR-04.5**: Vertical dividers: notches on bottom edge at horizontal positions
- **FR-04.6**: Notch positions SHALL be included in cut piece metadata

### FR-05: Validation

- **FR-05.1**: Minimum cubby interior size = 6" x 6"
- **FR-05.2**: Total row heights + dividers SHALL equal section height (variable)
- **FR-05.3**: Total column widths + dividers SHALL equal section width (variable)
- **FR-05.4**: rows >= 1, columns >= 1
- **FR-05.5**: rows <= 10, columns <= 10 (practical limit)

---

## Data Models

### CubbyConfig

```python
@dataclass(frozen=True)
class CubbyConfig:
    """Configuration for cubby grid."""
    rows: int = 2
    columns: int = 2
    row_heights: tuple[float, ...] | None = None    # For variable
    column_widths: tuple[float, ...] | None = None  # For variable
    divider_thickness: float | None = None          # Default: material thickness
    joinery: str = "half_lap"                       # "half_lap" | "dado"
```

### NotchSpec

```python
@dataclass(frozen=True)
class NotchSpec:
    """Half-lap notch specification for divider intersection."""
    position: float      # Distance from left/bottom edge
    width: float         # Notch width (= divider thickness)
    depth: float         # Notch depth (= divider thickness / 2)
    edge: str            # "top" | "bottom" | "left" | "right"
```

### DividerPiece

```python
@dataclass(frozen=True)
class DividerPiece:
    """Divider cut piece with notch specifications."""
    width: float
    height: float
    label: str                          # e.g., "H-DIV-1", "V-DIV-2-3"
    orientation: str                    # "horizontal" | "vertical"
    notches: tuple[NotchSpec, ...]      # Notch positions for joinery
    row_index: int | None = None        # For vertical dividers
    column_index: int | None = None     # For horizontal dividers
```

---

## Technical Approach

### File: `src/cabinets/domain/components/cubby.py`

```python
from typing import Any
from dataclasses import dataclass
from ..entities import Panel
from ..value_objects import PanelType, CutPiece, MaterialSpec
from .protocol import Component
from .context import ComponentContext
from .results import GenerationResult, ValidationResult, HardwareItem
from .registry import component_registry

MIN_CUBBY_SIZE = 6.0  # inches

@dataclass(frozen=True)
class NotchSpec:
    position: float
    width: float
    depth: float
    edge: str

@dataclass(frozen=True)
class DividerPiece:
    width: float
    height: float
    label: str
    orientation: str
    notches: tuple[NotchSpec, ...]
    row_index: int | None = None
    column_index: int | None = None


def _calculate_uniform_sizes(
    total: float, count: int, divider_thickness: float
) -> list[float]:
    """Calculate uniform cubby sizes."""
    usable = total - (count - 1) * divider_thickness
    size = usable / count
    return [size] * count


def _validate_cubby_sizes(
    widths: list[float], heights: list[float]
) -> list[str]:
    """Validate minimum cubby sizes."""
    errors = []
    for i, w in enumerate(widths):
        if w < MIN_CUBBY_SIZE:
            errors.append(f"Column {i+1} width {w:.1f}\" below minimum {MIN_CUBBY_SIZE}\"")
    for i, h in enumerate(heights):
        if h < MIN_CUBBY_SIZE:
            errors.append(f"Row {i+1} height {h:.1f}\" below minimum {MIN_CUBBY_SIZE}\"")
    return errors


@component_registry.register("cubby.uniform")
class UniformCubbyComponent:
    """Uniform grid of equal-sized cubbies."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []

        rows = config.get("rows", 2)
        columns = config.get("columns", 2)

        if rows < 1 or columns < 1:
            errors.append("rows and columns must be >= 1")
        if rows > 10 or columns > 10:
            errors.append("rows and columns must be <= 10")

        divider_thickness = config.get("divider_thickness", context.material.thickness)
        widths = _calculate_uniform_sizes(context.width, columns, divider_thickness)
        heights = _calculate_uniform_sizes(context.height, rows, divider_thickness)

        errors.extend(_validate_cubby_sizes(widths, heights))

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        rows = config.get("rows", 2)
        columns = config.get("columns", 2)
        divider_thickness = config.get("divider_thickness", context.material.thickness)
        joinery = config.get("joinery", "half_lap")

        widths = _calculate_uniform_sizes(context.width, columns, divider_thickness)
        heights = _calculate_uniform_sizes(context.height, rows, divider_thickness)

        cut_pieces = _generate_dividers(
            context, widths, heights, divider_thickness, joinery
        )

        return GenerationResult(cut_pieces=tuple(cut_pieces))

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        return []  # Structural - no hardware


@component_registry.register("cubby.variable")
class VariableCubbyComponent:
    """Grid with variable row heights and/or column widths."""

    def validate(self, config: dict[str, Any], context: ComponentContext) -> ValidationResult:
        errors, warnings = [], []
        divider_thickness = config.get("divider_thickness", context.material.thickness)

        # Get row heights
        row_heights = config.get("row_heights")
        rows = config.get("rows", 2)
        if row_heights:
            heights = list(row_heights)
            total_h = sum(heights) + (len(heights) - 1) * divider_thickness
            if abs(total_h - context.height) > 0.01:
                errors.append(
                    f"Row heights + dividers = {total_h:.2f}\", "
                    f"section height = {context.height:.2f}\""
                )
        else:
            heights = _calculate_uniform_sizes(context.height, rows, divider_thickness)

        # Get column widths
        column_widths = config.get("column_widths")
        columns = config.get("columns", 2)
        if column_widths:
            widths = list(column_widths)
            total_w = sum(widths) + (len(widths) - 1) * divider_thickness
            if abs(total_w - context.width) > 0.01:
                errors.append(
                    f"Column widths + dividers = {total_w:.2f}\", "
                    f"section width = {context.width:.2f}\""
                )
        else:
            widths = _calculate_uniform_sizes(context.width, columns, divider_thickness)

        if len(heights) < 1 or len(widths) < 1:
            errors.append("Must have at least 1 row and 1 column")
        if len(heights) > 10 or len(widths) > 10:
            errors.append("Maximum 10 rows and 10 columns")

        errors.extend(_validate_cubby_sizes(widths, heights))

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(self, config: dict[str, Any], context: ComponentContext) -> GenerationResult:
        divider_thickness = config.get("divider_thickness", context.material.thickness)
        joinery = config.get("joinery", "half_lap")

        row_heights = config.get("row_heights")
        rows = config.get("rows", 2)
        heights = list(row_heights) if row_heights else _calculate_uniform_sizes(
            context.height, rows, divider_thickness
        )

        column_widths = config.get("column_widths")
        columns = config.get("columns", 2)
        widths = list(column_widths) if column_widths else _calculate_uniform_sizes(
            context.width, columns, divider_thickness
        )

        cut_pieces = _generate_dividers(
            context, widths, heights, divider_thickness, joinery
        )

        return GenerationResult(cut_pieces=tuple(cut_pieces))

    def hardware(self, config: dict[str, Any], context: ComponentContext) -> list[HardwareItem]:
        return []  # Structural - no hardware


def _generate_dividers(
    context: ComponentContext,
    widths: list[float],
    heights: list[float],
    divider_thickness: float,
    joinery: str,
) -> list[CutPiece]:
    """Generate horizontal and vertical dividers with notch specs."""
    pieces = []
    num_rows = len(heights)
    num_cols = len(widths)
    notch_depth = divider_thickness / 2 if joinery == "half_lap" else divider_thickness

    # Calculate vertical divider X positions (for notch placement on horizontals)
    v_positions = []
    x = 0.0
    for i in range(num_cols - 1):
        x += widths[i]
        v_positions.append(x)
        x += divider_thickness

    # Calculate horizontal divider Y positions
    h_positions = []
    y = 0.0
    for i in range(num_rows - 1):
        y += heights[i]
        h_positions.append(y)
        y += divider_thickness

    # Generate horizontal dividers (full width, rows-1 count)
    for i, h_pos in enumerate(h_positions):
        notches = tuple(
            NotchSpec(
                position=vp,
                width=divider_thickness,
                depth=notch_depth,
                edge="top"
            )
            for vp in v_positions
        )
        pieces.append(CutPiece(
            width=context.width,
            height=context.depth,
            quantity=1,
            label=f"H-DIV-{i+1}",
            panel_type=PanelType.DIVIDER,
            material=context.material,
            # Note: notches stored as metadata in implementation
        ))

    # Generate vertical dividers (fit between horizontals)
    for row_idx in range(num_rows):
        row_height = heights[row_idx]
        for col_idx in range(num_cols - 1):
            # Notch at bottom if not bottom row
            notches = []
            if row_idx > 0:
                notches.append(NotchSpec(
                    position=0,
                    width=divider_thickness,
                    depth=notch_depth,
                    edge="bottom"
                ))
            # Notch at top if not top row
            if row_idx < num_rows - 1:
                notches.append(NotchSpec(
                    position=row_height - notch_depth,
                    width=divider_thickness,
                    depth=notch_depth,
                    edge="top"
                ))

            pieces.append(CutPiece(
                width=row_height,  # Vertical piece "width" is row height
                height=context.depth,
                quantity=1,
                label=f"V-DIV-{row_idx+1}-{col_idx+1}",
                panel_type=PanelType.DIVIDER,
                material=context.material,
            ))

    return pieces
```

---

## Configuration Examples

### Uniform 3x3 Grid

```yaml
sections:
  - type: cubby
    component: cubby.uniform
    config:
      rows: 3
      columns: 3
      joinery: half_lap
```

### Variable Grid (Taller Bottom Row)

```yaml
sections:
  - type: cubby
    component: cubby.variable
    config:
      row_heights: [12.0, 12.0, 18.0, 12.0]  # 4 rows, bottom taller
      column_widths: [16.0, 24.0, 16.0]       # 3 columns, center wider
      divider_thickness: 0.75
      joinery: half_lap
```

### Mixed Uniform/Variable

```yaml
sections:
  - type: cubby
    component: cubby.variable
    config:
      rows: 4                               # Uniform row heights
      column_widths: [10.0, 20.0, 10.0]     # Variable column widths
```

---

## Dimension Calculation Examples

### Example: 36" x 48" Section, 3x3 Uniform, 0.75" Dividers

```
Dividers needed:
  - Horizontal: 3-1 = 2 dividers
  - Vertical: (3-1) * 3 = 6 dividers

Cubby width calculation:
  usable_width = 36 - (3-1) * 0.75 = 36 - 1.5 = 34.5"
  cubby_width = 34.5 / 3 = 11.5"

Cubby height calculation:
  usable_height = 48 - (3-1) * 0.75 = 48 - 1.5 = 46.5"
  cubby_height = 46.5 / 3 = 15.5"

Cut list:
  - H-DIV-1: 36" x depth, notches at 12.25" and 24.5"
  - H-DIV-2: 36" x depth, notches at 12.25" and 24.5"
  - V-DIV-1-1: 15.5" x depth (row 1, col 1)
  - V-DIV-1-2: 15.5" x depth (row 1, col 2)
  - V-DIV-2-1: 15.5" x depth (row 2, col 1)
  - V-DIV-2-2: 15.5" x depth (row 2, col 2)
  - V-DIV-3-1: 15.5" x depth (row 3, col 1)
  - V-DIV-3-2: 15.5" x depth (row 3, col 2)
```

---

## Validation Rules

| Rule | Check | Error Message |
|------|-------|---------------|
| V-01 | rows >= 1, columns >= 1 | "rows and columns must be >= 1" |
| V-02 | rows <= 10, columns <= 10 | "rows and columns must be <= 10" |
| V-03 | Cubby width >= 6" | "Column X width Y\" below minimum 6\"" |
| V-04 | Cubby height >= 6" | "Row X height Y\" below minimum 6\"" |
| V-05 | Variable heights sum | "Row heights + dividers = X\", section height = Y\"" |
| V-06 | Variable widths sum | "Column widths + dividers = X\", section width = Y\"" |

---

## Testing Strategy

### Unit Tests

| Test | Assertion |
|------|-----------|
| `cubby.uniform` registers | `component_registry.get("cubby.uniform")` succeeds |
| `cubby.variable` registers | `component_registry.get("cubby.variable")` succeeds |
| Uniform 2x2 sizing | 4 equal cubbies calculated correctly |
| Uniform divider count | rows-1 horizontal, (cols-1)*rows vertical |
| Variable heights | Custom heights preserved in output |
| Variable widths | Custom widths preserved in output |
| Notch positions | Half-lap notches at correct intersections |
| Min size validation | 5"x5" cubby triggers error |
| Dimension sum validation | Heights not summing to section height triggers error |
| No hardware | `hardware()` returns empty list |

### Integration Tests

- Section with `cubby.uniform` generates correct divider cut pieces
- Section with `cubby.variable` validates dimension constraints
- Divider labels follow naming convention
- Notch specs attached to cut pieces

---

## Implementation Phases

### Phase 1: Core Components (Est. 0.5 day)
- [ ] Create `src/cabinets/domain/components/cubby.py`
- [ ] Implement `NotchSpec` and `DividerPiece` dataclasses
- [ ] Implement `UniformCubbyComponent`
- [ ] Implement `VariableCubbyComponent`

### Phase 2: Divider Generation (Est. 0.5 day)
- [ ] Implement `_generate_dividers` helper
- [ ] Calculate notch positions for half-lap joinery
- [ ] Generate horizontal dividers with correct notches
- [ ] Generate vertical dividers with correct notches

### Phase 3: Validation & Testing (Est. 0.5 day)
- [ ] Implement all validation rules
- [ ] Unit tests for both components
- [ ] Integration tests with component registry

---

## Dependencies & Risks

### Dependencies
- FRD-05: `Component` protocol, `ComponentContext`, `GenerationResult`
- Existing: `CutPiece`, `PanelType.DIVIDER`, `MaterialSpec`

### Risks

| Risk | Mitigation |
|------|------------|
| Notch specs not in CutPiece | Extend CutPiece or use metadata dict |
| Floating point tolerance | Use 0.01" tolerance for dimension sums |
| Complex variable validation | Clear error messages with calculated vs expected values |

---

## Open Questions

1. **Notch spec storage**: Should `NotchSpec` be stored in `CutPiece` or separate metadata?
   - Proposed: Add optional `metadata: dict` to `CutPiece` value object

2. **Dado joinery option**: Should dado cut to frame panels also be generated?
   - Proposed: Defer to future enhancement; current scope is divider-to-divider only

3. **Edge banding**: Should divider front edges be flagged for banding?
   - Proposed: Add `edge_band_front: bool` config option, default True

---

*FRD-09 ready for implementation: 2025-12-27*
