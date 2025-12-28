# FRD-04: Variable Section Widths & Types

**Created:** 2025-12-27
**Status:** Codebase Aligned and Ready for Task Breakdown
**Priority:** High
**Depends On:** FRD-01 (Configuration Schema)
**Refinement Date:** 2025-12-27

**Note:** FRD-02 and FRD-03 dependencies are NOT blocking. Core width/fill functionality is already implemented. FRD-03 (obstacle avoidance) is downstream - fill calculation happens before obstacle adjustments.

---

## Problem Statement

Current `Section` entity has a fixed `width` attribute. Real built-in cabinets need:
- Flexible width specification: explicit values or "fill" for automatic sizing
- Different section types (open shelving, doored, drawers, cubbies)
- Per-section configuration overrides (shelf count, depth)
- Proper divider generation between sections with material thickness accounting

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| Flexible width specification | Sections accept explicit width OR "fill" keyword |
| Multiple fill sections | N fill sections divide remaining space equally |
| Section type system | Enum-based types with type-specific behavior hooks |
| Section-level overrides | Each section can override shelf count and depth |
| Proper divider handling | Single shared divider between adjacent sections |
| Validation | Explicit widths cannot exceed available space |

---

## Scope

### In Scope
- Width specification: explicit float OR `"fill"` literal
- Section type enum: `open`, `doored`, `drawers`, `cubby`
- Min/max width constraints per section
- Vertical divider generation between sections
- Section-level shelf count and depth overrides
- Width calculation service for fill sections
- Validation of total widths vs. available space

### Out of Scope
- Type-specific internals (door panels, drawer boxes, cubby dividers) - future FRDs
- Adjustable shelf hole patterns
- Face frame generation
- Hardware specifications

---

## Functional Requirements

### FR-01: Section Width Specification

- **FR-01.1**: Section width SHALL accept `float` (explicit inches) OR `"fill"` literal
- **FR-01.2**: Explicit width SHALL be positive and > 0
- **FR-01.3**: `"fill"` sections SHALL auto-calculate width from remaining space
- **FR-01.4**: Default width SHALL be `"fill"` if not specified
- **FR-01.5**: At least one section MUST have explicit width OR available space must be defined

### FR-02: Fill Width Calculation

- **FR-02.1**: Available space = wall segment width - (outer panel thicknesses)
- **FR-02.2**: Remaining space = available space - sum(explicit widths) - sum(divider thicknesses)
- **FR-02.3**: Each fill section width = remaining space / count(fill sections)
- **FR-02.4**: Fill calculation SHALL occur after obstacle avoidance adjustments
- **FR-02.5**: If remaining space <= 0, validation SHALL fail with clear error

### FR-03: Section Types

- **FR-03.1**: `SectionType` enum SHALL include: `open`, `doored`, `drawers`, `cubby`
- **FR-03.2**: Default type SHALL be `open`
- **FR-03.3**: Type SHALL be stored on section but NOT affect generation in this FRD
- **FR-03.4**: Type-specific generation deferred to future FRDs (05-08)

### FR-04: Section Constraints

- **FR-04.1**: Section MAY specify `min_width` (float, default: 6.0")
- **FR-04.2**: Section MAY specify `max_width` (float, default: none)
- **FR-04.3**: Fill sections SHALL respect min/max constraints during calculation
- **FR-04.4**: If constraints cannot be satisfied, validation SHALL fail
- **FR-04.5**: Explicit widths outside min/max SHALL produce validation error

### FR-05: Vertical Dividers

- **FR-05.1**: Divider SHALL be generated between each pair of adjacent sections
- **FR-05.2**: Divider thickness = cabinet material thickness (shared, not doubled)
- **FR-05.3**: Divider height = interior height (between top and bottom panels)
- **FR-05.4**: Divider depth = interior depth (accounting for back panel)
- **FR-05.5**: Number of dividers = number of sections - 1
- **FR-05.6**: Section interior width = section width (divider is BETWEEN sections, not inside)

### FR-06: Section-Level Overrides

- **FR-06.1**: Section MAY override `shelf_count` (default: inherit from cabinet)
- **FR-06.2**: Section MAY override `depth` (default: inherit from cabinet)
- **FR-06.3**: Depth override SHALL NOT exceed cabinet depth
- **FR-06.4**: Shelf count SHALL be 0-20 inclusive

### FR-07: Validation

- **FR-07.1**: Sum of explicit widths + dividers SHALL NOT exceed available space
- **FR-07.2**: Each fill section calculated width SHALL be >= min_width
- **FR-07.3**: Section references to walls (from FRD-02) SHALL be validated
- **FR-07.4**: Validation errors SHALL include section index and constraint violated

---

## Data Models

### Extended Section Configuration

```python
# src/cabinets/application/config/schema.py

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class SectionType(str, Enum):
    OPEN = "open"
    DOORED = "doored"
    DRAWERS = "drawers"
    CUBBY = "cubby"

class SectionConfig(BaseModel):
    """Configuration for a single cabinet section."""

    width: float | Literal["fill"] = "fill"
    section_type: SectionType = SectionType.OPEN
    shelf_count: int | None = Field(default=None, ge=0, le=20)
    depth: float | None = Field(default=None, gt=0)
    min_width: float = Field(default=6.0, gt=0)
    max_width: float | None = Field(default=None, gt=0)
    wall: int | str = 0  # Wall index or name (from FRD-02)

    @field_validator("width")
    @classmethod
    def validate_width(cls, v):
        if isinstance(v, (int, float)) and v <= 0:
            raise ValueError("width must be positive")
        return v

    @model_validator(mode="after")
    def validate_constraints(self):
        if self.max_width and self.min_width > self.max_width:
            raise ValueError("min_width cannot exceed max_width")
        if isinstance(self.width, (int, float)):
            if self.width < self.min_width:
                raise ValueError(f"width {self.width} below min_width {self.min_width}")
            if self.max_width and self.width > self.max_width:
                raise ValueError(f"width {self.width} exceeds max_width {self.max_width}")
        return self
```

### Extended Section Entity

```python
# src/cabinets/domain/entities.py

from enum import Enum

class SectionType(Enum):
    OPEN = "open"
    DOORED = "doored"
    DRAWERS = "drawers"
    CUBBY = "cubby"

@dataclass
class Section:
    """A vertical section within a cabinet."""

    width: float
    height: float
    depth: float
    position: Position
    section_type: SectionType = SectionType.OPEN
    shelf_count: int = 0
    shelves: list[Shelf] = field(default_factory=list)

    def add_shelf(self, shelf: Shelf) -> None:
        self.shelves.append(shelf)
```

### Width Resolution Value Object

```python
# src/cabinets/domain/value_objects.py

@dataclass(frozen=True)
class ResolvedWidth:
    """Result of width calculation for a section."""
    section_index: int
    requested: float | Literal["fill"]
    resolved: float
    is_fill: bool

@dataclass(frozen=True)
class WidthCalculationResult:
    """Complete result of section width resolution."""
    resolved_widths: list[ResolvedWidth]
    total_width: float
    available_space: float
    divider_count: int
    divider_thickness: float
```

---

## Services

### SectionWidthCalculator

```python
# src/cabinets/domain/services.py

class SectionWidthCalculator:
    """Calculates resolved widths for sections with fill support."""

    def calculate(
        self,
        sections: list[SectionConfig],
        available_space: float,
        material_thickness: float
    ) -> WidthCalculationResult:
        """
        Resolve all section widths.

        Args:
            sections: Section configurations with explicit or fill widths
            available_space: Total interior width (after outer panels)
            material_thickness: Divider thickness

        Returns:
            WidthCalculationResult with all widths resolved

        Raises:
            ValueError: If widths cannot be resolved within constraints
        """
        divider_count = len(sections) - 1
        divider_total = divider_count * material_thickness

        # Sum explicit widths
        explicit_total = sum(
            s.width for s in sections
            if isinstance(s.width, (int, float))
        )

        # Find fill sections
        fill_sections = [
            (i, s) for i, s in enumerate(sections)
            if s.width == "fill"
        ]

        remaining = available_space - explicit_total - divider_total

        if remaining < 0:
            raise ValueError(
                f"Explicit widths ({explicit_total}) + dividers ({divider_total}) "
                f"exceed available space ({available_space})"
            )

        if not fill_sections and remaining > 0.01:  # tolerance
            raise ValueError(
                f"No fill sections but {remaining}\" unallocated"
            )

        # Calculate fill widths
        fill_width = remaining / len(fill_sections) if fill_sections else 0

        # Validate constraints
        for i, section in fill_sections:
            if fill_width < section.min_width:
                raise ValueError(
                    f"Section {i}: calculated fill width {fill_width:.2f}\" "
                    f"below min_width {section.min_width}\""
                )
            if section.max_width and fill_width > section.max_width:
                raise ValueError(
                    f"Section {i}: calculated fill width {fill_width:.2f}\" "
                    f"exceeds max_width {section.max_width}\""
                )

        # Build results
        resolved = []
        for i, section in enumerate(sections):
            is_fill = section.width == "fill"
            resolved.append(ResolvedWidth(
                section_index=i,
                requested=section.width,
                resolved=fill_width if is_fill else section.width,
                is_fill=is_fill
            ))

        return WidthCalculationResult(
            resolved_widths=resolved,
            total_width=sum(r.resolved for r in resolved) + divider_total,
            available_space=available_space,
            divider_count=divider_count,
            divider_thickness=material_thickness
        )
```

### SectionBuilder

```python
class SectionBuilder:
    """Builds Section entities from resolved configurations."""

    def __init__(self, width_calculator: SectionWidthCalculator):
        self.width_calculator = width_calculator

    def build_sections(
        self,
        configs: list[SectionConfig],
        cabinet_height: float,
        cabinet_depth: float,
        available_width: float,
        material: MaterialSpec,
        default_shelf_count: int = 0
    ) -> tuple[list[Section], list[Panel]]:
        """
        Build Section entities and divider panels.

        Returns:
            Tuple of (sections, divider_panels)
        """
        result = self.width_calculator.calculate(
            configs, available_width, material.thickness
        )

        sections = []
        dividers = []
        current_x = material.thickness  # Start after left panel

        for i, resolved in enumerate(result.resolved_widths):
            config = configs[i]

            # Resolve overrides
            depth = config.depth or cabinet_depth
            shelf_count = (
                config.shelf_count
                if config.shelf_count is not None
                else default_shelf_count
            )

            section = Section(
                width=resolved.resolved,
                height=cabinet_height,
                depth=depth,
                position=Position(current_x, material.thickness),
                section_type=SectionType(config.section_type.value),
                shelf_count=shelf_count
            )
            sections.append(section)

            current_x += resolved.resolved

            # Add divider (except after last section)
            if i < len(configs) - 1:
                dividers.append(Panel(
                    panel_type=PanelType.DIVIDER,
                    width=depth - material.thickness,  # Interior depth
                    height=cabinet_height,
                    material=material,
                    position=Position(current_x, material.thickness)
                ))
                current_x += material.thickness

        return sections, dividers
```

---

## Configuration Schema Extension

### Section Configuration (v1.2+)

```json
{
  "schema_version": "1.2",
  "cabinet": {
    "width": 96,
    "height": 84,
    "depth": 12,
    "material": {"type": "plywood", "thickness": 0.75},
    "default_shelves": 4,
    "sections": [
      {
        "width": 24,
        "type": "doored",
        "shelves": 2
      },
      {
        "width": "fill",
        "type": "open",
        "min_width": 12,
        "max_width": 36
      },
      {
        "width": "fill",
        "type": "drawers",
        "depth": 10
      }
    ]
  }
}
```

### Field Definitions

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `sections[].width` | float\|"fill" | No | `"fill"` | > 0 or "fill" |
| `sections[].type` | enum | No | `"open"` | open, doored, drawers, cubby |
| `sections[].shelves` | int | No | inherit | 0-20 |
| `sections[].depth` | float | No | inherit | > 0, <= cabinet depth |
| `sections[].min_width` | float | No | 6.0 | > 0 |
| `sections[].max_width` | float | No | none | > min_width |
| `sections[].wall` | int\|string | No | 0 | Valid wall ref |
| `cabinet.default_shelves` | int | No | 0 | 0-20 |

---

## Width Calculation Examples

### Example 1: Mixed Explicit and Fill

```
Cabinet width: 96"
Material thickness: 0.75"
Sections: [24", "fill", "fill"]

Available space = 96 - (2 * 0.75) = 94.5"
Dividers = 2 * 0.75 = 1.5"
Explicit widths = 24"
Remaining = 94.5 - 24 - 1.5 = 69"
Fill width = 69 / 2 = 34.5" each

Result: [24", 34.5", 34.5"] + 2 dividers
```

### Example 2: All Fill Sections

```
Cabinet width: 72"
Material thickness: 0.75"
Sections: ["fill", "fill", "fill"]

Available space = 72 - 1.5 = 70.5"
Dividers = 2 * 0.75 = 1.5"
Remaining = 70.5 - 1.5 = 69"
Fill width = 69 / 3 = 23" each

Result: [23", 23", 23"] + 2 dividers
```

### Example 3: Validation Failure

```
Cabinet width: 48"
Material thickness: 0.75"
Sections: [24", 24", "fill"]

Available space = 48 - 1.5 = 46.5"
Dividers = 2 * 0.75 = 1.5"
Explicit widths = 48"
Remaining = 46.5 - 48 - 1.5 = -3"

ERROR: Explicit widths exceed available space
```

---

## Validation Rules

| Rule | Check | Error Message |
|------|-------|---------------|
| V-01 | width > 0 (if explicit) | "Section {n}: width must be positive" |
| V-02 | min_width <= max_width | "Section {n}: min_width exceeds max_width" |
| V-03 | explicit width >= min_width | "Section {n}: width below min_width" |
| V-04 | explicit width <= max_width | "Section {n}: width exceeds max_width" |
| V-05 | sum(explicit) + dividers <= available | "Total explicit widths exceed available space" |
| V-06 | fill_width >= min_width | "Section {n}: calculated width {w}\" below min_width" |
| V-07 | fill_width <= max_width | "Section {n}: calculated width {w}\" exceeds max_width" |
| V-08 | depth <= cabinet_depth | "Section {n}: depth exceeds cabinet depth" |
| V-09 | 0 <= shelf_count <= 20 | "Section {n}: shelf count out of range" |

---

## Integration with Existing Code

### Cabinet Entity Updates

```python
# src/cabinets/domain/entities.py

@dataclass
class Cabinet:
    # ... existing fields ...
    default_shelf_count: int = 0

    def get_all_panels(self) -> list[Panel]:
        panels: list[Panel] = []

        # ... existing top/bottom/sides/back code ...

        # Dividers between sections (already implemented)
        for i in range(len(self.sections) - 1):
            section = self.sections[i]
            panels.append(
                Panel(
                    panel_type=PanelType.DIVIDER,
                    width=self.interior_depth,
                    height=self.interior_height,
                    material=self.material,
                    position=Position(
                        section.position.x + section.width,
                        self.material.thickness
                    ),
                )
            )

        # ... existing shelf code ...

        return panels
```

### Command Handler Updates

```python
# src/cabinets/application/commands.py

class GenerateCabinetCommand:
    def execute(self, config: CabinetConfiguration) -> Cabinet:
        calculator = SectionWidthCalculator()
        builder = SectionBuilder(calculator)

        available_width = config.cabinet.width - (2 * config.cabinet.material.thickness)

        sections, dividers = builder.build_sections(
            configs=config.cabinet.sections,
            cabinet_height=config.cabinet.height - (2 * config.cabinet.material.thickness),
            cabinet_depth=config.cabinet.depth,
            available_width=available_width,
            material=config.cabinet.material.to_spec(),
            default_shelf_count=config.cabinet.default_shelves
        )

        cabinet = Cabinet(
            width=config.cabinet.width,
            height=config.cabinet.height,
            depth=config.cabinet.depth,
            material=config.cabinet.material.to_spec(),
            sections=sections,
            default_shelf_count=config.cabinet.default_shelves
        )

        return cabinet
```

---

## Testing Strategy

### Unit Tests

| Test Case | Input | Expected |
|-----------|-------|----------|
| Single fill section | `["fill"]`, 48" available | Width = 48" |
| Two fill sections | `["fill", "fill"]`, 48" | Each = 23.25" (after divider) |
| Mixed widths | `[24, "fill"]`, 48" | [24", 23.25"] |
| All explicit | `[20, 20]`, 48" | [20", 20"], 7.5" unused warning |
| Min width violated | `["fill"]`, 4" available, min=6 | Validation error |
| Max width enforced | `["fill"]`, 48", max=12 | Validation error |
| Explicit exceeds space | `[30, 30]`, 48" | Validation error |
| Depth override | depth=10, cabinet=12 | Section depth = 10" |
| Type assignment | type="doored" | section_type = DOORED |

### Integration Tests

- Config with fill sections generates correct cabinet dimensions
- Multiple fill sections produce equal widths
- Dividers positioned correctly between sections
- Section-level overrides reflected in generated panels
- STL output has correct geometry

---

## Implementation Phases

### Phase 1: Core Width System (Est. 2 days)
- [ ] Add `SectionType` enum to entities
- [ ] Implement `SectionWidthCalculator` service
- [ ] Add `ResolvedWidth` and `WidthCalculationResult` value objects
- [ ] Unit tests for width calculations

### Phase 2: Section Builder (Est. 2 days)
- [ ] Implement `SectionBuilder` service
- [ ] Integrate with `Cabinet.get_all_panels()` for dividers
- [ ] Section-level override handling
- [ ] Position calculations

### Phase 3: Schema & Validation (Est. 1 day)
- [ ] Extend `SectionConfig` Pydantic model
- [ ] Add validation rules and error messages
- [ ] Update config schema documentation

### Phase 4: Integration (Est. 2 days)
- [ ] Update `GenerateCabinetCommand` to use new services
- [ ] Integration with FRD-02 wall geometry
- [ ] Integration with FRD-03 obstacle avoidance
- [ ] End-to-end tests

---

## Dependencies & Risks

### Dependencies
- FRD-01: Configuration schema for section definitions
- FRD-02: Wall segment widths for available space calculation
- FRD-03: Obstacle avoidance modifies available space before fill calculation
- Existing `Section` and `Cabinet` entities (extend, maintain backward compatibility)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Float precision in width calc | Medium | Use tolerance (0.01") in comparisons |
| Complex constraint interactions | Medium | Thorough unit tests; clear error messages |
| Breaking existing configs | High | Default width="fill" maintains behavior |

---

## Open Questions

1. **Rounding strategy**: Round fill widths to 1/16" or keep float precision?
   - Proposed: Keep float; rounding is cut list concern

2. **Unallocated space**: Error or warning when all explicit with leftover space?
   - Proposed: Warning; user may want intentional gaps

3. **Zero-width sections**: Allow width=0 to create divider-only positions?
   - Proposed: No; minimum 6" enforced

---

## Appendix: Example Configurations

### Simple Two-Section Cabinet

```json
{
  "schema_version": "1.2",
  "cabinet": {
    "width": 48,
    "height": 84,
    "depth": 12,
    "sections": [
      {"width": 24, "shelves": 4},
      {"width": "fill", "shelves": 3}
    ]
  }
}
```

### Multi-Type Cabinet

```json
{
  "schema_version": "1.2",
  "cabinet": {
    "width": 96,
    "height": 84,
    "depth": 14,
    "default_shelves": 4,
    "sections": [
      {"width": 24, "type": "doored"},
      {"width": "fill", "type": "open", "min_width": 18},
      {"width": "fill", "type": "open", "min_width": 18},
      {"width": 24, "type": "drawers", "depth": 12}
    ]
  }
}
```

### Constrained Fill Sections

```json
{
  "schema_version": "1.2",
  "cabinet": {
    "width": 72,
    "height": 48,
    "depth": 10,
    "sections": [
      {"width": "fill", "min_width": 12, "max_width": 24, "shelves": 2},
      {"width": "fill", "min_width": 12, "max_width": 24, "shelves": 2},
      {"width": "fill", "min_width": 12, "max_width": 24, "shelves": 2}
    ]
  }
}
```

---

## Implementation Analysis: Codebase Alignment

This section documents the codebase analysis performed to align the FRD with existing infrastructure and identify implementation pathways.

### Critical Discovery: Core Functionality Already Implemented

**The majority of FRD-04 requirements are ALREADY IMPLEMENTED.** The codebase has robust support for variable section widths with fill calculation. Only the section type system and constraint features remain to be implemented.

---

### Implementation Analysis: Domain Layer (Backend Support)

#### Current State

**Relevant Files:**
- `src/cabinets/domain/section_resolver.py` - **232 lines of width resolution logic**
- `src/cabinets/domain/entities.py` - `Section`, `Cabinet` entities
- `src/cabinets/domain/value_objects.py` - `Position`, `MaterialSpec`
- `src/cabinets/domain/services.py` - `LayoutCalculator`, `RoomLayoutService`

**Already Implemented (DONE):**

1. **SectionSpec dataclass** (section_resolver.py:19-55):
   - `width: float | Literal["fill"]` - DONE
   - `shelves: int = 0` - DONE
   - `wall: str | int | None = None` - DONE (from FRD-02)
   - `is_fill` property - DONE
   - `fixed_width` property - DONE
   - `__post_init__` validation - DONE

2. **resolve_section_widths()** (section_resolver.py:57-179):
   - Calculates interior width minus outer panels - DONE
   - Subtracts divider thicknesses - DONE
   - Distributes remaining width equally among fill sections - DONE
   - Comprehensive validation and error handling - DONE

3. **validate_section_specs()** (section_resolver.py:182-231):
   - Non-throwing validation function - DONE
   - Returns list of error messages - DONE

4. **LayoutCalculator.generate_cabinet_from_specs()** (services.py:102-174):
   - Takes `section_specs: list[SectionSpec]` - DONE
   - Calls `resolve_section_widths()` - DONE
   - Creates `Section` entities with correct widths - DONE
   - Generates evenly-spaced shelves per section - DONE

5. **Cabinet.get_all_panels()** (entities.py:106-188):
   - Generates `PanelType.DIVIDER` between sections - DONE
   - Correct positioning at section boundaries - DONE

6. **RoomLayoutService** (services.py:364-744):
   - Section-to-wall assignment - DONE
   - Wall reference resolution (index and name) - DONE
   - Fit validation - DONE

#### Needed Work

- [ ] Add `SectionType` enum to `value_objects.py` or `entities.py` - Complexity: Low
- [ ] Add `section_type: SectionType = SectionType.OPEN` to `SectionSpec` - Complexity: Low
- [ ] Add `depth: float | None = None` to `SectionSpec` for per-section override - Complexity: Low
- [ ] Add `min_width: float = 6.0` to `SectionSpec` - Complexity: Low
- [ ] Add `max_width: float | None = None` to `SectionSpec` - Complexity: Low
- [ ] Extend `resolve_section_widths()` to validate min/max constraints - Complexity: Medium
- [ ] Add `section_type: SectionType` to `Section` entity - Complexity: Low
- [ ] Add `default_shelf_count: int = 0` to `Cabinet` entity - Complexity: Low
- [ ] Update `generate_cabinet_from_specs()` to handle depth override - Complexity: Low

#### Recommended Approach

Extend existing code incrementally:
1. Add `SectionType` enum (4 values: open, doored, drawers, cubby)
2. Add new optional fields to `SectionSpec` - all with defaults for backward compatibility
3. Modify `resolve_section_widths()` to check min/max after fill calculation
4. Add `section_type` to `Section` entity
5. Update `generate_cabinet_from_specs()` for depth override

---

### Implementation Analysis: Application Layer

#### Current State

**Relevant Files:**
- `src/cabinets/application/config/schema.py` - Pydantic v2 schema
- `src/cabinets/application/config/adapter.py` - Config to domain conversion
- `src/cabinets/application/config/validator.py` - Validation structures

**Already Implemented (DONE):**

1. **SectionConfig** (schema.py:90-112):
   - `width: float | Literal["fill"] = "fill"` - DONE
   - `shelves: int` with ge=0, le=20 - DONE
   - `wall: str | int | None` - DONE
   - Validation - DONE

2. **config_to_section_specs()** (adapter.py:112-157):
   - Converts `SectionConfig` to domain `SectionSpec` - DONE
   - Handles width and shelves - DONE

3. **validate_config()** (validator.py:257-298):
   - Validates total fixed widths - DONE
   - Woodworking advisories - DONE

#### Needed Work

- [ ] Add `SectionTypeConfig` enum to schema (matches domain enum) - Complexity: Low
- [ ] Add `section_type: SectionTypeConfig = "open"` to `SectionConfig` - Complexity: Low
- [ ] Add `depth: float | None` to `SectionConfig` - Complexity: Low
- [ ] Add `min_width: float = 6.0` to `SectionConfig` - Complexity: Low
- [ ] Add `max_width: float | None` to `SectionConfig` - Complexity: Low
- [ ] Add `default_shelves: int` to `CabinetConfig` - Complexity: Low
- [ ] Update `config_to_section_specs()` for new fields - Complexity: Low
- [ ] (Optional) Add constraint validation to `validate_config()` - Complexity: Low

---

### Implementation Analysis: Infrastructure Layer

#### Current State

**Relevant Files:**
- `src/cabinets/infrastructure/exporters.py` - Formatters and exporters
- `src/cabinets/infrastructure/stl_exporter.py` - 3D mesh generation

**Analysis:**

1. **LayoutDiagramFormatter** (exporters.py:41-123):
   - Already shows sections and dividers
   - No changes needed for FRD-04 (types don't affect ASCII layout)

2. **JsonExporter** (exporters.py:155-190):
   - Could optionally include section types
   - Not critical for FRD-04 core functionality

3. **StlExporter**:
   - No changes needed - uses Panel3DMapper which handles sections

#### Needed Work

- [ ] (Optional) Extend JsonExporter to include section types - Complexity: Low

---

### Implementation Analysis: Testing

#### Current State

**Relevant Files:**
- `tests/unit/test_section_resolver.py` - **365 lines of comprehensive tests**
- `tests/unit/test_entities.py`
- `tests/unit/test_config_schema.py`

**Already Tested (DONE):**

1. `TestSectionSpec` - creation, validation, properties
2. `TestResolveSectionWidthsAllFill` - single, two, three fill sections
3. `TestResolveSectionWidthsMixed` - fixed + fill combinations
4. `TestResolveSectionWidthsAllFixed` - exact fit scenarios
5. `TestResolveSectionWidthsErrors` - all error conditions
6. `TestResolveSectionWidthsEdgeCases` - edge cases, precision

#### Needed Work

- [ ] Test `SectionType` enum values - Complexity: Low
- [ ] Test `SectionSpec` with new fields (section_type, depth, min/max) - Complexity: Low
- [ ] Test constraint validation in `resolve_section_widths()` - Complexity: Medium
- [ ] Test `Section` entity with section_type - Complexity: Low
- [ ] Test `SectionConfig` schema with new fields - Complexity: Low
- [ ] Test config adapter for new fields - Complexity: Low

---

### Lateral Moves Identified

#### 1. SectionType Enum Location
**Description:** Add `SectionType` enum to `value_objects.py` (consistent with other enums like `MaterialType`, `PanelType`)
**Rationale:** Follows existing pattern for domain enums
**Impact:** New type, no existing code changes
**Status:** Ready to implement

#### 2. Constraint Validation in resolve_section_widths()
**Description:** Add min/max validation AFTER fill width calculation
**Rationale:** Fill widths are calculated, then checked against constraints
**Algorithm:**
```python
# After calculating fill_width:
for i, spec in fill_sections:
    if fill_width < spec.min_width:
        raise SectionWidthError(f"Section {i}: fill width {fill_width:.2f} below min_width {spec.min_width}")
    if spec.max_width and fill_width > spec.max_width:
        raise SectionWidthError(f"Section {i}: fill width {fill_width:.2f} exceeds max_width {spec.max_width}")
```
**Status:** Ready to implement

#### 3. Depth Override in generate_cabinet_from_specs()
**Description:** If section has depth override, use it instead of cabinet depth
**Implementation:** Simple conditional in section creation loop
**Status:** Ready to implement

#### 4. ResolvedWidth Value Object (DEFERRED)
**Description:** The FRD proposes `ResolvedWidth` and `WidthCalculationResult` types
**Assessment:** Current callers only need `list[float]`. Extra metadata not needed.
**Recommendation:** Defer to future if callers need this information
**Status:** Not implementing in this phase

---

### Revised Implementation Phases

Based on codebase analysis, the phases are significantly reduced:

#### Phase 1: Section Type System (Est. 0.5 day)
- [x] Width specification (explicit or fill) - ALREADY DONE
- [x] Fill width calculation - ALREADY DONE
- [ ] Add `SectionType` enum to value_objects.py
- [ ] Add `section_type` field to `SectionSpec`
- [ ] Add `section_type` field to `Section` entity
- [ ] Unit tests for SectionType

#### Phase 2: Constraint System (Est. 0.5 day)
- [ ] Add `min_width`, `max_width` fields to `SectionSpec`
- [ ] Extend `resolve_section_widths()` with constraint validation
- [ ] Unit tests for constraint validation

#### Phase 3: Section Overrides (Est. 0.5 day)
- [ ] Add `depth` field to `SectionSpec`
- [ ] Update `generate_cabinet_from_specs()` for depth override
- [ ] Add `default_shelf_count` to `Cabinet` entity
- [ ] Unit tests for overrides

#### Phase 4: Schema & Config (Est. 0.5 day)
- [ ] Extend `SectionConfig` with new fields
- [ ] Add `default_shelves` to `CabinetConfig`
- [ ] Update `config_to_section_specs()` adapter
- [ ] Config schema tests

#### Phase 5: Integration & Polish (Est. 0.5 day)
- [ ] Integration tests
- [ ] (Optional) JsonExporter enhancement
- [ ] Documentation updates

**Total Revised Estimate: 2.5 days** (down from original 7+ days)

---

### Revised Dependencies

#### Hard Dependencies (ALREADY SATISFIED)
- FRD-01: Configuration schema - DONE (schema.py exists with versioning)
- Existing `Section`, `Cabinet`, `SectionSpec` - DONE

#### Soft Dependencies (NOT BLOCKING)
- FRD-02: Room & Wall Geometry - ALREADY IMPLEMENTED in codebase
- FRD-03: Obstacle Avoidance - NOT needed; fill calculation is upstream

---

### Revised Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Float precision in width calc | Medium | Already handled with tolerance (0.001) | MITIGATED |
| Complex constraint interactions | Medium | Clear validation order (calc then check) | MITIGATED |
| Breaking existing configs | Low | All new fields optional with defaults | MITIGATED |

---

### Codebase Alignment Verification

- [x] Core width specification (explicit/fill) - ALREADY IMPLEMENTED
- [x] Fill width calculation algorithm - ALREADY IMPLEMENTED
- [x] Divider generation - ALREADY IMPLEMENTED
- [x] Wall assignment - ALREADY IMPLEMENTED (via FRD-02)
- [x] Config schema supports sections - ALREADY IMPLEMENTED
- [x] Comprehensive test coverage for width resolution - ALREADY IMPLEMENTED
- [ ] Section type system - TO BE IMPLEMENTED
- [ ] Constraint validation (min/max) - TO BE IMPLEMENTED
- [ ] Depth override - TO BE IMPLEMENTED
- [ ] Default shelf count - TO BE IMPLEMENTED

---

### Summary

**FRD-04 is approximately 70% implemented.** The core variable section width functionality with fill calculation is complete and well-tested. Remaining work focuses on:

1. Adding the `SectionType` enum (placeholder for future FRDs 05-08)
2. Adding min/max width constraints
3. Adding per-section depth override
4. Adding cabinet-level default shelf count

This is a 2.5-day effort, not the 7+ days originally estimated.

The FRD is marked as **"Codebase Aligned and Ready for Task Breakdown"**.
