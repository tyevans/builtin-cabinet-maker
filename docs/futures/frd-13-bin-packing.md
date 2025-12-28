# FRD-13: Bin Packing & Cut Optimization

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** High
**Depends On:** Existing `CutPiece` from `src/cabinets/domain/value_objects.py`

---

## Problem Statement

Cabinet projects generate many cut pieces that must be extracted from standard sheet goods. Without optimization, pieces are cut sequentially, leading to:
- 25-40% material waste (industry average without optimization)
- Suboptimal sheet utilization
- Increased material costs
- Manual layout planning required

Bin packing algorithms can reduce waste to 10-15% while respecting real-world constraints like saw kerf, grain direction, and guillotine cutting patterns.

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Reduce material waste | 15%+ improvement vs. naive layout |
| Support guillotine cuts | All layouts cuttable with panel saw |
| Handle grain constraints | Grain-sensitive pieces orient correctly |
| Multi-material support | Separate optimization per material group |
| Generate visual output | SVG or ASCII cut diagrams per sheet |

---

## Scope

### In Scope
- Guillotine-compatible bin packing algorithm
- First-fit decreasing heuristic (sort by area)
- Standard sheet sizes (4'x8', 5'x5', custom)
- Configurable kerf allowance
- Edge allowance (unusable material at edges)
- Grain direction constraints
- Multi-material grouping
- Visual cut diagrams (SVG/ASCII)
- Waste percentage reporting
- Offcut inventory tracking

### Out of Scope
- Non-guillotine (free-form) cutting patterns
- CNC toolpath generation
- Cost optimization (price-per-sheet)
- Nested irregular shapes
- Real-time interactive layout editing

---

## Functional Requirements

### FR-01: Bin Packing Algorithm

- **FR-01.1**: Implement guillotine cutting algorithm (all cuts go edge-to-edge)
- **FR-01.2**: Use first-fit decreasing heuristic (sort pieces by area, largest first)
- **FR-01.3**: Support `rectpack` library integration OR custom implementation
- **FR-01.4**: Allow piece rotation (90 degrees) unless grain-constrained
- **FR-01.5**: Minimize number of sheets used as primary objective

### FR-02: Sheet Configuration

- **FR-02.1**: Support standard sheet size: 4'x8' (48"x96")
- **FR-02.2**: Support standard sheet size: 5'x5' (60"x60")
- **FR-02.3**: Support custom sheet dimensions via config
- **FR-02.4**: Configurable edge allowance (default: 0.5")
- **FR-02.5**: Support multiple sheet sizes in same project

### FR-03: Kerf Allowance

- **FR-03.1**: Configurable saw blade kerf width (default: 0.125" / 1/8")
- **FR-03.2**: Kerf added between adjacent pieces in layout
- **FR-03.3**: Kerf applied after each guillotine cut
- **FR-03.4**: Validate kerf does not exceed reasonable bounds (0-0.5")

### FR-04: Grain Direction

- **FR-04.1**: `CutPiece` extended with `grain_direction` attribute
- **FR-04.2**: Grain options: `none`, `length_wise`, `width_wise`
- **FR-04.3**: `grain_direction: none` allows free rotation
- **FR-04.4**: `length_wise`/`width_wise` locks orientation relative to sheet grain
- **FR-04.5**: Sheet grain assumed parallel to sheet length (96" dimension)

### FR-05: Multi-Material Optimization

- **FR-05.1**: Group pieces by `MaterialSpec` (type + thickness)
- **FR-05.2**: Run separate bin packing per material group
- **FR-05.3**: Each material group has own sheet configuration
- **FR-05.4**: Output organized by material group

### FR-06: Output Generation

- **FR-06.1**: Generate visual cut diagram per sheet (SVG format)
- **FR-06.2**: ASCII fallback diagram for terminal output
- **FR-06.3**: Report waste percentage per sheet
- **FR-06.4**: Report total waste percentage across all sheets
- **FR-06.5**: Track reusable offcuts (pieces > configurable threshold)
- **FR-06.6**: Report sheet count needed per material

---

## Data Models

### Extended CutPiece

```python
# Extension to src/cabinets/domain/value_objects.py

class GrainDirection(str, Enum):
    """Grain direction constraint for cut pieces."""
    NONE = "none"           # Can rotate freely
    LENGTH_WISE = "length"  # Grain parallel to piece length
    WIDTH_WISE = "width"    # Grain parallel to piece width

@dataclass(frozen=True)
class CutPieceWithGrain(CutPiece):
    """Cut piece with grain direction constraint."""
    grain_direction: GrainDirection = GrainDirection.NONE
```

### Sheet Configuration

```python
# src/cabinets/infrastructure/bin_packing.py

@dataclass(frozen=True)
class SheetConfig:
    """Configuration for sheet material."""
    width: float = 48.0       # inches
    height: float = 96.0      # inches
    edge_allowance: float = 0.5

    @property
    def usable_width(self) -> float:
        return self.width - (2 * self.edge_allowance)

    @property
    def usable_height(self) -> float:
        return self.height - (2 * self.edge_allowance)

@dataclass(frozen=True)
class BinPackingConfig:
    """Configuration for bin packing optimization."""
    enabled: bool = True
    sheet_size: SheetConfig = field(default_factory=SheetConfig)
    kerf: float = 0.125       # 1/8" saw blade
    edge_allowance: float = 0.5
    grain_direction: bool = True
    min_offcut_size: float = 6.0  # Track offcuts larger than this
```

### Placement Result

```python
@dataclass(frozen=True)
class PlacedPiece:
    """A piece placed on a sheet."""
    piece: CutPiece
    x: float              # Position from sheet left edge
    y: float              # Position from sheet bottom edge
    rotated: bool         # True if rotated 90 degrees

@dataclass(frozen=True)
class SheetLayout:
    """Layout of pieces on a single sheet."""
    sheet_index: int
    sheet_config: SheetConfig
    placements: tuple[PlacedPiece, ...]
    material: MaterialSpec

    @property
    def used_area(self) -> float:
        return sum(p.piece.width * p.piece.height for p in self.placements)

    @property
    def waste_percentage(self) -> float:
        total = self.sheet_config.usable_width * self.sheet_config.usable_height
        return (1 - self.used_area / total) * 100

@dataclass(frozen=True)
class Offcut:
    """Reusable leftover piece."""
    width: float
    height: float
    material: MaterialSpec
    sheet_index: int

@dataclass(frozen=True)
class PackingResult:
    """Complete bin packing result."""
    layouts: tuple[SheetLayout, ...]
    offcuts: tuple[Offcut, ...]
    total_waste_percentage: float
    sheets_by_material: dict[MaterialSpec, int]
```

---

## Configuration Schema

```yaml
# In project config
bin_packing:
  enabled: true
  sheet_size:
    width: 48
    height: 96
  kerf: 0.125
  edge_allowance: 0.5
  grain_direction: true
  min_offcut_size: 6.0

  # Optional: per-material overrides
  material_overrides:
    - material_type: plywood
      thickness: 0.25
      sheet_size:
        width: 48
        height: 48
```

---

## Technical Approach

### Algorithm Implementation

```python
# src/cabinets/infrastructure/bin_packing.py

from typing import Sequence
import rectpack  # Optional dependency

class GuillotineBinPacker:
    """Bin packing with guillotine cut constraint."""

    def __init__(self, config: BinPackingConfig):
        self.config = config

    def pack(
        self,
        pieces: Sequence[CutPiece],
        material: MaterialSpec,
    ) -> PackingResult:
        """Pack pieces onto sheets, minimizing waste."""
        # Sort by area (first-fit decreasing)
        sorted_pieces = sorted(
            pieces,
            key=lambda p: p.width * p.height,
            reverse=True
        )

        # Expand quantities into individual pieces
        expanded = []
        for piece in sorted_pieces:
            for _ in range(piece.quantity):
                expanded.append(piece)

        # Pack using guillotine algorithm
        layouts = self._guillotine_pack(expanded, material)

        # Calculate offcuts
        offcuts = self._extract_offcuts(layouts)

        return PackingResult(
            layouts=tuple(layouts),
            offcuts=tuple(offcuts),
            total_waste_percentage=self._calc_total_waste(layouts),
            sheets_by_material={material: len(layouts)},
        )

    def _guillotine_pack(
        self,
        pieces: list[CutPiece],
        material: MaterialSpec,
    ) -> list[SheetLayout]:
        """Guillotine-compatible bin packing."""
        # Implementation uses shelf-based or maxrects with guillotine constraint
        ...

    def _can_rotate(self, piece: CutPiece) -> bool:
        """Check if piece can be rotated based on grain."""
        if not self.config.grain_direction:
            return True
        if hasattr(piece, 'grain_direction'):
            return piece.grain_direction == GrainDirection.NONE
        return True
```

### Multi-Material Coordinator

```python
class BinPackingService:
    """Coordinates bin packing across material groups."""

    def __init__(self, config: BinPackingConfig):
        self.config = config
        self.packer = GuillotineBinPacker(config)

    def optimize_cut_list(
        self,
        pieces: Sequence[CutPiece],
    ) -> PackingResult:
        """Optimize cut list, grouping by material."""
        # Group by material
        groups: dict[MaterialSpec, list[CutPiece]] = {}
        for piece in pieces:
            if piece.material not in groups:
                groups[piece.material] = []
            groups[piece.material].append(piece)

        # Pack each group
        all_layouts = []
        all_offcuts = []
        sheets_by_material = {}

        for material, group_pieces in groups.items():
            result = self.packer.pack(group_pieces, material)
            all_layouts.extend(result.layouts)
            all_offcuts.extend(result.offcuts)
            sheets_by_material[material] = len(result.layouts)

        return PackingResult(
            layouts=tuple(all_layouts),
            offcuts=tuple(all_offcuts),
            total_waste_percentage=self._calc_total_waste(all_layouts),
            sheets_by_material=sheets_by_material,
        )
```

### Output Generation

```python
class CutDiagramRenderer:
    """Renders cut diagrams in various formats."""

    def render_svg(self, layout: SheetLayout) -> str:
        """Generate SVG cut diagram."""
        svg_parts = [
            f'<svg width="{layout.sheet_config.width * 10}" '
            f'height="{layout.sheet_config.height * 10}" '
            f'xmlns="http://www.w3.org/2000/svg">'
        ]

        # Sheet outline
        svg_parts.append(
            f'<rect x="0" y="0" '
            f'width="{layout.sheet_config.width * 10}" '
            f'height="{layout.sheet_config.height * 10}" '
            f'fill="none" stroke="black"/>'
        )

        # Each placed piece
        for placement in layout.placements:
            w = placement.piece.width if not placement.rotated else placement.piece.height
            h = placement.piece.height if not placement.rotated else placement.piece.width
            svg_parts.append(
                f'<rect x="{placement.x * 10}" y="{placement.y * 10}" '
                f'width="{w * 10}" height="{h * 10}" '
                f'fill="lightblue" stroke="black"/>'
                f'<text x="{(placement.x + w/2) * 10}" '
                f'y="{(placement.y + h/2) * 10}" '
                f'text-anchor="middle">{placement.piece.label}</text>'
            )

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def render_ascii(self, layout: SheetLayout, width: int = 80) -> str:
        """Generate ASCII cut diagram for terminal."""
        ...
```

---

## File Structure

```
src/cabinets/infrastructure/
    bin_packing.py          # Core algorithm and service
    cut_diagram_renderer.py # SVG/ASCII output generation
```

---

## Validation Rules

| Rule | Check | Result |
|------|-------|--------|
| V-01 | All pieces fit within sheet bounds | ERROR if oversized |
| V-02 | kerf >= 0 and <= 0.5 | ERROR if out of range |
| V-03 | edge_allowance >= 0 | ERROR if negative |
| V-04 | sheet dimensions > 0 | ERROR if non-positive |
| V-05 | Grain-constrained piece fits in required orientation | WARNING if tight fit |

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| Single piece fits | 24x48 piece, 48x96 sheet | 1 sheet, 50% waste |
| Kerf calculation | Two 24x48 pieces adjacent | Gap = kerf width |
| Grain constraint | Length-wise piece, narrow orientation | Rotation blocked |
| Material grouping | Mixed 3/4" and 1/4" pieces | Separate layouts |
| First-fit decreasing | Random order input | Largest placed first |
| Edge allowance | 48x96 piece, 0.5" allowance | Piece fits 47x95 usable |

### Integration Tests

- Full cabinet cut list optimizes to fewer sheets than naive
- SVG output renders valid, viewable diagram
- Offcut tracking captures pieces > threshold
- Multi-cabinet project groups materials correctly

---

## Implementation Phases

### Phase 1: Core Data Models (0.5 day)
- [ ] Add `GrainDirection` enum to value_objects
- [ ] Create `SheetConfig`, `BinPackingConfig` dataclasses
- [ ] Create `PlacedPiece`, `SheetLayout`, `PackingResult` dataclasses

### Phase 2: Basic Bin Packing (1.5 days)
- [ ] Implement `GuillotineBinPacker` with shelf algorithm
- [ ] First-fit decreasing sort
- [ ] Basic piece placement without rotation
- [ ] Sheet overflow handling (add new sheet)

### Phase 3: Rotation & Grain (1 day)
- [ ] Implement rotation logic
- [ ] Add grain direction constraint checking
- [ ] Extend `CutPiece` with grain attribute

### Phase 4: Multi-Material (0.5 day)
- [ ] Implement `BinPackingService` coordinator
- [ ] Material grouping logic
- [ ] Per-material sheet configuration

### Phase 5: Output Generation (1 day)
- [ ] Implement SVG renderer
- [ ] Implement ASCII fallback renderer
- [ ] Waste percentage calculation
- [ ] Offcut inventory tracking

### Phase 6: Integration (0.5 day)
- [ ] Wire into cabinet generation pipeline
- [ ] Add configuration schema support
- [ ] End-to-end testing

---

## Dependencies & Risks

### Dependencies
- `CutPiece` from `src/cabinets/domain/value_objects.py`
- `MaterialSpec` for material grouping
- Optional: `rectpack` library (pip installable)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| rectpack unavailable | Medium | Implement fallback shelf algorithm |
| Large piece counts slow | Low | Algorithm is O(n log n) sort + O(n) placement |
| Suboptimal layouts | Medium | First-fit decreasing is good heuristic, not optimal |
| Grain adds complexity | Low | Simple rotation lock, well-defined behavior |

---

## Open Questions

1. **rectpack vs custom**: Use rectpack library or implement custom guillotine algorithm?
   - Proposed: Start with rectpack, custom fallback if needed

2. **Offcut storage**: Should offcuts persist across projects for inventory tracking?
   - Proposed: No for v1; output only, no persistence

3. **Sheet cost optimization**: Factor in different sheet prices?
   - Proposed: No for v1; minimize sheet count only

---

*FRD-13 ready for implementation: 2025-12-27*
