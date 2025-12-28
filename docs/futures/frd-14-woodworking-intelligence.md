# FRD-14: Woodworking Intelligence

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** Medium
**Depends On:** `CutPiece`, `MaterialSpec`, `PanelType` from `src/cabinets/domain/value_objects.py`

---

## Problem Statement

Cabinet generation currently produces geometrically correct designs but lacks professional woodworking knowledge:
- No joinery specifications (dado depth, rabbet dimensions)
- No span warnings for shelves that will sag under load
- No grain direction guidance for strength and aesthetics
- No weight capacity estimates for shelves
- No hardware quantity calculations

Users must manually determine joinery, validate spans, and calculate fastener counts.

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Auto-select appropriate joinery | Correct joint type for each connection |
| Warn on unsafe shelf spans | 100% detection of over-span conditions |
| Provide grain recommendations | Included in cut list output |
| Estimate weight capacity | Per-shelf advisory output |
| Calculate hardware quantities | Complete fastener list per project |

---

## Scope

### In Scope
- Joinery type selection and dimensioning
- Shelf span validation with material-specific limits
- Grain direction recommendations
- Weight capacity estimation (advisory)
- Hardware/fastener quantity aggregation
- Integration with existing validation system as warnings

### Out of Scope
- Structural engineering calculations
- Load-bearing certifications
- Custom joint design
- Hardware purchasing integration
- CNC joinery toolpaths

---

## Functional Requirements

### FR-01: Joinery Specifications

- **FR-01.1**: Support joint types: `dado`, `rabbet`, `pocket_screw`, `dowel`, `biscuit`
- **FR-01.2**: Auto-select joint by connection type:
  - Shelf-to-side panel: `dado`
  - Back panel-to-case: `rabbet`
  - Divider-to-top/bottom: `dado`
  - Face frame joints: `pocket_screw` or `dowel`
- **FR-01.3**: Calculate dado depth = 1/3 material thickness (e.g., 0.25" for 3/4")
- **FR-01.4**: Calculate rabbet width = material thickness, depth = 1/2 thickness
- **FR-01.5**: Specify dowel positions (centered, 2" from edges, 6" spacing)
- **FR-01.6**: Specify pocket hole positions (4" from edges, 8" spacing)
- **FR-01.7**: Include joinery dimensions in cut list output

### FR-02: Span Warnings

- **FR-02.1**: Define max unsupported spans by material:
  - 3/4" plywood: 36"
  - 3/4" MDF: 24"
  - 3/4" particle board: 24"
  - 1" solid wood: 42"
- **FR-02.2**: Check all horizontal panels (shelves, top, bottom) against limits
- **FR-02.3**: Generate warning when span exceeds safe limit
- **FR-02.4**: Suggest mitigation: "Add center support or divider"
- **FR-02.5**: Allow user override with acknowledgment flag

### FR-03: Grain Direction

- **FR-03.1**: Recommend grain parallel to longest dimension
- **FR-03.2**: Plywood: face grain along length for pieces > 12" long
- **FR-03.3**: Solid wood: grain must be parallel to length
- **FR-03.4**: Add `grain_direction` field to cut list output
- **FR-03.5**: Note when grain affects visual appearance vs structural

### FR-04: Weight Capacity Estimates

- **FR-04.1**: Calculate estimated capacity based on:
  - Material type and thickness
  - Unsupported span length
  - Support type (dado vs surface-mounted)
- **FR-04.2**: Use simplified deflection formula (advisory only)
- **FR-04.3**: Output format: "Estimated capacity: ~50 lbs distributed"
- **FR-04.4**: Include disclaimer: "Advisory only - not engineered"
- **FR-04.5**: Reduce estimate for point loads vs distributed

### FR-05: Hardware Quantity Calculation

- **FR-05.1**: Calculate screw quantities by type:
  - Case screws: #8 x 1-1/4" (for 3/4" material)
  - Pocket screws: #8 x 1-1/4" coarse (plywood) or fine (hardwood)
  - Back panel screws: #6 x 5/8"
- **FR-05.2**: Calculate dowel quantities: 5/16" x 1-1/2"
- **FR-05.3**: Calculate biscuit quantities: #10 or #20
- **FR-05.4**: Include hardware for components:
  - Hinge screws per door
  - Drawer slide screws per drawer
- **FR-05.5**: Aggregate totals across all cabinet components
- **FR-05.6**: Add 10% overage recommendation

---

## Data Models

### Joinery Types

```python
# src/cabinets/domain/services/woodworking.py

class JointType(str, Enum):
    DADO = "dado"
    RABBET = "rabbet"
    POCKET_SCREW = "pocket_screw"
    DOWEL = "dowel"
    BISCUIT = "biscuit"
    BUTT = "butt"

@dataclass(frozen=True)
class JointSpec:
    """Specification for a joint."""
    joint_type: JointType
    depth: float | None = None      # For dado/rabbet
    width: float | None = None      # For rabbet
    positions: tuple[float, ...] = ()  # For dowel/pocket/biscuit
    spacing: float | None = None    # Between fasteners

@dataclass(frozen=True)
class ConnectionJoinery:
    """Joinery for a panel-to-panel connection."""
    from_panel: PanelType
    to_panel: PanelType
    joint: JointSpec
```

### Span Warning

```python
@dataclass(frozen=True)
class SpanWarning:
    """Warning for shelf span exceeding safe limits."""
    panel_label: str
    span: float
    max_span: float
    material: MaterialSpec
    suggestion: str = "Add center support or divider"

@dataclass(frozen=True)
class SpanLimits:
    """Maximum spans by material type."""
    limits: dict[tuple[MaterialType, float], float] = field(default_factory=lambda: {
        (MaterialType.PLYWOOD, 0.75): 36.0,
        (MaterialType.MDF, 0.75): 24.0,
        (MaterialType.PARTICLE_BOARD, 0.75): 24.0,
        (MaterialType.SOLID_WOOD, 1.0): 42.0,
    })
```

### Weight Capacity

```python
@dataclass(frozen=True)
class WeightCapacity:
    """Estimated weight capacity for a shelf."""
    panel_label: str
    capacity_lbs: float
    load_type: str  # "distributed" or "point"
    disclaimer: str = "Advisory only - not engineered"
```

### Hardware List

```python
@dataclass(frozen=True)
class HardwareItem:
    """A type of hardware needed."""
    name: str           # "#8 x 1-1/4 wood screw"
    quantity: int
    category: str       # "screws", "dowels", "biscuits"

@dataclass(frozen=True)
class HardwareList:
    """Complete hardware requirements."""
    items: tuple[HardwareItem, ...]

    def with_overage(self, percent: float = 0.10) -> "HardwareList":
        """Add overage percentage to quantities."""
        ...
```

---

## Configuration Schema

```yaml
woodworking:
  joinery:
    default_shelf_joint: dado
    default_back_joint: rabbet
    dado_depth_ratio: 0.333      # 1/3 of thickness
    rabbet_depth_ratio: 0.5

  span_limits:
    plywood_3_4: 36
    mdf_3_4: 24
    particle_board_3_4: 24
    solid_wood_1: 42

  hardware:
    add_overage: true
    overage_percent: 10

  warnings:
    enabled: true
    span_check: true
    require_acknowledgment: false
```

---

## Technical Approach

### Service Implementation

```python
# src/cabinets/domain/services/woodworking.py

class WoodworkingIntelligence:
    """Professional woodworking knowledge service."""

    def __init__(self, config: WoodworkingConfig | None = None):
        self.config = config or WoodworkingConfig()

    def get_joinery(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Determine joinery for all panel connections."""
        connections = []
        for panel in cabinet.get_all_panels():
            joint = self._select_joint(panel, cabinet)
            connections.append(joint)
        return connections

    def check_spans(self, cabinet: Cabinet) -> list[SpanWarning]:
        """Check all horizontal panels for span violations."""
        warnings = []
        for panel in cabinet.get_all_panels():
            if panel.panel_type in (PanelType.SHELF, PanelType.TOP, PanelType.BOTTOM):
                span = self._calculate_span(panel, cabinet)
                max_span = self._get_max_span(panel.material)
                if span > max_span:
                    warnings.append(SpanWarning(
                        panel_label=panel.panel_type.value,
                        span=span,
                        max_span=max_span,
                        material=panel.material,
                    ))
        return warnings

    def get_grain_directions(self, cut_list: list[CutPiece]) -> dict[str, str]:
        """Recommend grain direction for each cut piece."""
        return {
            piece.label: "length" if piece.width >= piece.height else "width"
            for piece in cut_list
        }

    def estimate_capacity(self, panel: Panel, span: float) -> WeightCapacity:
        """Estimate weight capacity for a horizontal panel."""
        # Simplified beam deflection approximation
        # capacity ~ (E * I) / (span^3) * safety_factor
        base_capacity = self._calculate_base_capacity(
            panel.material,
            panel.width,  # depth of shelf
            span
        )
        return WeightCapacity(
            panel_label=panel.panel_type.value,
            capacity_lbs=round(base_capacity, 0),
            load_type="distributed",
        )

    def calculate_hardware(self, cabinet: Cabinet) -> HardwareList:
        """Calculate all hardware needed for cabinet."""
        items = []
        items.extend(self._case_screws(cabinet))
        items.extend(self._back_panel_screws(cabinet))
        items.extend(self._joinery_fasteners(cabinet))
        return HardwareList(items=tuple(items))
```

### Integration with Validation

```python
# Integration point in validation pipeline

class WoodworkingValidator:
    """Validates cabinet against woodworking best practices."""

    def validate(self, cabinet: Cabinet) -> list[ValidationWarning]:
        """Run all woodworking checks."""
        intel = WoodworkingIntelligence()
        warnings = []

        # Span checks
        for span_warning in intel.check_spans(cabinet):
            warnings.append(ValidationWarning(
                code="SPAN_EXCEEDED",
                message=f"{span_warning.panel_label}: {span_warning.span}\" exceeds "
                        f"{span_warning.max_span}\" max for {span_warning.material.material_type.value}",
                suggestion=span_warning.suggestion,
                severity="warning",
                acknowledgeable=True,
            ))

        return warnings
```

---

## File Structure

```
src/cabinets/domain/services/
    __init__.py
    woodworking.py      # Core intelligence service
```

---

## Validation Rules

| Rule | Check | Severity |
|------|-------|----------|
| V-01 | Shelf span <= material max | WARNING |
| V-02 | Dado depth <= 1/2 thickness | ERROR |
| V-03 | Rabbet depth > 0 | ERROR |
| V-04 | Dowel spacing >= 4" | WARNING |
| V-05 | Pocket screw material compatible | WARNING |

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| Dado depth calculation | 0.75" material | 0.25" depth |
| Rabbet dimensions | 0.5" back panel | 0.5" width, 0.25" depth |
| Span warning | 40" plywood shelf | Warning generated |
| Span pass | 30" plywood shelf | No warning |
| Grain direction | 36x12" piece | "length" recommended |
| Hardware count | 4 shelves | Correct screw count |

### Integration Tests

- Full cabinet generates complete joinery specs
- Span warnings integrate with validation pipeline
- Hardware list aggregates across multiple cabinets
- Cut list includes grain directions

---

## Implementation Phases

### Phase 1: Joinery Specs (1 day)
- [ ] `JointType` enum and `JointSpec` dataclass
- [ ] Joint selection logic by panel type
- [ ] Dado/rabbet dimension calculations
- [ ] Dowel/pocket hole position calculations

### Phase 2: Span Warnings (0.5 day)
- [ ] `SpanWarning` dataclass
- [ ] Material-specific span limits
- [ ] Span checking logic
- [ ] Integration with validation pipeline

### Phase 3: Grain Direction (0.5 day)
- [ ] Grain recommendation logic
- [ ] Cut list output enhancement
- [ ] Material-specific rules

### Phase 4: Weight Capacity (0.5 day)
- [ ] Deflection approximation formula
- [ ] Capacity output formatting
- [ ] Disclaimer handling

### Phase 5: Hardware Calculation (1 day)
- [ ] Screw type/size logic
- [ ] Quantity calculations per joint type
- [ ] Component hardware (hinges, slides)
- [ ] Aggregation and overage

### Phase 6: Integration (0.5 day)
- [ ] Wire into cabinet generation pipeline
- [ ] Configuration schema support
- [ ] End-to-end testing

---

## Dependencies & Risks

### Dependencies
- `CutPiece` from `src/cabinets/domain/value_objects.py`
- `MaterialSpec`, `MaterialType` for material properties
- `PanelType` for connection type inference
- Existing validation infrastructure

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Weight estimates misused | High | Clear disclaimers, conservative estimates |
| Joinery selection wrong | Medium | Allow user override in config |
| Span limits too conservative | Low | Make configurable per material |
| Hardware counts inaccurate | Low | Add overage buffer, user verification |

---

## Open Questions

1. **Weight capacity formula**: Use simple beam deflection or more complex model?
   - Proposed: Simple approximation with conservative safety factor

2. **Joinery preference override**: Allow user to force specific joint types?
   - Proposed: Yes, via configuration

3. **Hardware brands**: Include specific product recommendations?
   - Proposed: No for v1; generic specifications only

---

*FRD-14 ready for implementation: 2025-12-27*
