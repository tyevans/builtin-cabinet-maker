# FRD-03: Obstacle Definition & Avoidance

**Created:** 2025-12-27
**Status:** Implemented
**Priority:** High
**Depends On:** FRD-01 (Configuration Schema), FRD-02 (Room & Wall Geometry)
**Refinement Date:** 2025-12-27
**Implementation Date:** 2025-12-27

---

## Problem Statement

Real walls have windows, doors, outlets, switches, and vents. Cabinet sections must avoid these obstacles and their required clearances. The system needs to:

- Define obstacles on specific wall segments
- Calculate clearance zones per obstacle type
- Detect collisions between cabinet geometry and obstacle zones
- Automatically resize/split sections to fit around obstacles
- Support partial-height cabinets (e.g., below windows)

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| Model wall obstacles | All standard obstacle types definable with position and dimensions |
| Type-specific clearances | Each obstacle type has configurable default clearance |
| Collision detection | Service accurately detects cabinet/obstacle overlap |
| Auto-layout around obstacles | Sections resize or split to avoid obstacle zones |
| Partial-height support | Can generate upper/lower cabinet sections around windows |
| Validation warnings | Warn when obstacles block entire usable area |

---

## Scope

### In Scope
- `Obstacle` entity with types: window, door, outlet, switch, vent, skylight, custom
- Position: `wall_index`, `horizontal_offset`, `bottom` (from floor), `width`, `height`
- Clearance zones per type (defaults configurable)
- `ObstacleCollisionService` for overlap detection
- Section layout algorithm: resize/split around obstacles
- Upper/lower section generation for windows
- Validation service for blocked areas

### Out of Scope
- 3D obstacle visualization
- Automatic obstacle detection from images
- Obstacle-specific panel cutouts (e.g., outlet box notches)
- HVAC/plumbing routing
- Structural member detection

---

## Domain Model

### Obstacle Types

| Type | Description | Default Clearance |
|------|-------------|-------------------|
| `window` | Standard window | 2" all sides |
| `door` | Door frame/opening | 2" sides, 0" top/bottom |
| `outlet` | Electrical outlet | 0" (code: must remain accessible) |
| `switch` | Light switch | 0" (code: must remain accessible) |
| `vent` | HVAC vent/register | 4" all sides |
| `skylight` | Ceiling skylight | 2" all sides |
| `custom` | User-defined | 0" (user specifies) |

### Clearance Behavior

- **Outlets/Switches**: Cabinet cannot cover; must leave full access
- **Windows**: Clearance allows sill space; cabinet can go below (lower section)
- **Doors**: Cabinet stops at door frame; no overlap allowed
- **Vents**: Clearance ensures airflow; larger buffer required

---

## Functional Requirements

### FR-01: Obstacle Entity

- **FR-01.1**: Obstacle SHALL have: `type` (enum), `wall_index` (int), `horizontal_offset` (float), `bottom` (float), `width` (float), `height` (float)
- **FR-01.2**: `horizontal_offset` is distance from wall segment start (inches)
- **FR-01.3**: `bottom` is distance from floor (inches)
- **FR-01.4**: All dimensions SHALL be positive
- **FR-01.5**: Obstacle SHALL have optional `clearance_override` (per-side clearances)
- **FR-01.6**: Obstacle SHALL compute its bounding box including clearances

### FR-02: Clearance Configuration

- **FR-02.1**: Each obstacle type SHALL have default clearances (top, bottom, left, right)
- **FR-02.2**: Defaults SHALL be configurable in root config under `obstacle_defaults`
- **FR-02.3**: Individual obstacles MAY override defaults via `clearance_override`
- **FR-02.4**: Clearance of 0 means cabinet edge can touch obstacle edge

### FR-03: Collision Detection Service

- **FR-03.1**: `ObstacleCollisionService.check_collision(section_bounds, obstacle_zone)` SHALL return bool
- **FR-03.2**: Service SHALL support batch checking: multiple sections against multiple obstacles
- **FR-03.3**: Collision means ANY overlap between section geometry and obstacle+clearance zone
- **FR-03.4**: Service SHALL return collision details: which section, which obstacle, overlap area

### FR-04: Section Layout Around Obstacles

- **FR-04.1**: Layout service SHALL automatically adjust section widths to avoid obstacles
- **FR-04.2**: Sections MAY be split into multiple narrower sections around obstacles
- **FR-04.3**: Sections MAY be shortened in height to fit below/above obstacles
- **FR-04.4**: Layout SHALL prefer: (1) resize existing section, (2) split section, (3) skip area
- **FR-04.5**: Minimum section width SHALL be configurable (default: 6")

### FR-05: Partial-Height Sections

- **FR-05.1**: For windows, system SHALL support "lower" sections (floor to window bottom - clearance)
- **FR-05.2**: For windows, system SHALL support "upper" sections (window top + clearance to ceiling)
- **FR-05.3**: Section config MAY specify `height_mode`: `full`, `lower`, `upper`, `auto`
- **FR-05.4**: `auto` mode: system determines best fit around obstacles

### FR-06: Validation & Warnings

- **FR-06.1**: Validator SHALL warn when obstacle blocks >80% of wall segment usable width
- **FR-06.2**: Validator SHALL error when obstacle completely blocks wall segment
- **FR-06.3**: Validator SHALL warn when resulting section width < minimum
- **FR-06.4**: Warnings SHALL include suggestions (e.g., "Consider upper/lower sections")

---

## Data Models

### Obstacle Entity

```python
# src/cabinets/domain/entities.py

class ObstacleType(Enum):
    WINDOW = "window"
    DOOR = "door"
    OUTLET = "outlet"
    SWITCH = "switch"
    VENT = "vent"
    SKYLIGHT = "skylight"
    CUSTOM = "custom"

@dataclass(frozen=True)
class Clearance:
    """Clearance distances around an obstacle."""
    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0

@dataclass
class Obstacle:
    """An obstacle on a wall that cabinets must avoid."""

    obstacle_type: ObstacleType
    wall_index: int
    horizontal_offset: float  # From wall segment start
    bottom: float             # From floor
    width: float
    height: float
    clearance_override: Clearance | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Obstacle dimensions must be positive")
        if self.horizontal_offset < 0 or self.bottom < 0:
            raise ValueError("Obstacle position must be non-negative")

    def get_clearance(self, defaults: dict[ObstacleType, Clearance]) -> Clearance:
        """Get effective clearance (override or default)."""
        if self.clearance_override:
            return self.clearance_override
        return defaults.get(self.obstacle_type, Clearance())

    def get_zone_bounds(self, clearance: Clearance) -> ObstacleZone:
        """Get obstacle bounds including clearance."""
        return ObstacleZone(
            left=self.horizontal_offset - clearance.left,
            right=self.horizontal_offset + self.width + clearance.right,
            bottom=self.bottom - clearance.bottom,
            top=self.bottom + self.height + clearance.top,
            obstacle=self
        )
```

### Supporting Value Objects

```python
# src/cabinets/domain/value_objects.py

@dataclass(frozen=True)
class ObstacleZone:
    """Bounding box of obstacle including clearances."""
    left: float
    right: float
    bottom: float
    top: float
    obstacle: "Obstacle"

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    def overlaps(self, other: "SectionBounds") -> bool:
        """Check if this zone overlaps with a section."""
        return not (
            self.right <= other.left or
            self.left >= other.right or
            self.top <= other.bottom or
            self.bottom >= other.top
        )

@dataclass(frozen=True)
class SectionBounds:
    """2D bounds of a cabinet section on a wall."""
    left: float    # Horizontal offset from wall start
    right: float
    bottom: float  # From floor
    top: float
```

---

## Configuration Schema Extension (v1.2)

### Obstacle Configuration

```json
{
  "schema_version": "1.2",
  "obstacle_defaults": {
    "window": {"top": 2, "bottom": 2, "left": 2, "right": 2},
    "outlet": {"top": 0, "bottom": 0, "left": 0, "right": 0},
    "vent": {"top": 4, "bottom": 4, "left": 4, "right": 4}
  },
  "room": {
    "name": "living-room",
    "walls": [
      {"length": 120, "height": 96}
    ],
    "obstacles": [
      {
        "type": "window",
        "wall": 0,
        "horizontal_offset": 36,
        "bottom": 36,
        "width": 48,
        "height": 48
      },
      {
        "type": "outlet",
        "wall": 0,
        "horizontal_offset": 12,
        "bottom": 12,
        "width": 3,
        "height": 5
      }
    ]
  },
  "cabinet": {
    "depth": 12,
    "sections": [
      {"width": "fill", "height_mode": "auto", "shelves": 4}
    ]
  }
}
```

### Field Definitions

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `obstacle_defaults` | object | No | Built-in | Keyed by obstacle type |
| `obstacle_defaults.{type}` | Clearance | No | Type default | top/bottom/left/right floats |
| `room.obstacles` | array | No | `[]` | List of obstacles |
| `room.obstacles[].type` | enum | Yes | - | window, door, outlet, switch, vent, skylight, custom |
| `room.obstacles[].wall` | int\|string | Yes | - | Wall index or name |
| `room.obstacles[].horizontal_offset` | float | Yes | - | >= 0 |
| `room.obstacles[].bottom` | float | Yes | - | >= 0 |
| `room.obstacles[].width` | float | Yes | - | > 0 |
| `room.obstacles[].height` | float | Yes | - | > 0 |
| `room.obstacles[].clearance` | Clearance | No | Type default | Override clearances |
| `cabinet.sections[].height_mode` | enum | No | `full` | full, lower, upper, auto |

---

## Services

### ObstacleCollisionService

```python
# src/cabinets/domain/services.py

class ObstacleCollisionService:
    """Detects collisions between cabinet sections and obstacles."""

    def __init__(self, default_clearances: dict[ObstacleType, Clearance]):
        self.default_clearances = default_clearances

    def get_obstacle_zones(
        self,
        obstacles: list[Obstacle],
        wall_index: int
    ) -> list[ObstacleZone]:
        """Get all obstacle zones for a specific wall."""
        return [
            obs.get_zone_bounds(obs.get_clearance(self.default_clearances))
            for obs in obstacles
            if obs.wall_index == wall_index
        ]

    def check_collision(
        self,
        section: SectionBounds,
        zones: list[ObstacleZone]
    ) -> list[CollisionResult]:
        """Check if section collides with any obstacle zones."""
        return [
            CollisionResult(zone=z, overlap=self._calc_overlap(section, z))
            for z in zones
            if z.overlaps(section)
        ]

    def find_valid_regions(
        self,
        wall_length: float,
        wall_height: float,
        zones: list[ObstacleZone]
    ) -> list[ValidRegion]:
        """Find regions on wall where sections can be placed."""
        ...

@dataclass
class CollisionResult:
    zone: ObstacleZone
    overlap: float  # Square inches of overlap

@dataclass
class ValidRegion:
    left: float
    right: float
    bottom: float
    top: float
    region_type: str  # "full", "lower", "upper", "gap"
```

### ObstacleAwareLayoutService

```python
class ObstacleAwareLayoutService:
    """Lays out cabinet sections while avoiding obstacles."""

    def __init__(
        self,
        collision_service: ObstacleCollisionService,
        min_section_width: float = 6.0
    ):
        self.collision_service = collision_service
        self.min_section_width = min_section_width

    def layout_sections(
        self,
        wall: WallSegment,
        obstacles: list[Obstacle],
        requested_sections: list[SectionConfig]
    ) -> LayoutResult:
        """
        Layout sections on wall, avoiding obstacles.
        Returns adjusted sections with positions.
        """
        ...

    def split_section_around_obstacle(
        self,
        section: SectionConfig,
        zone: ObstacleZone
    ) -> list[SectionConfig]:
        """Split a section into parts that avoid an obstacle."""
        ...

@dataclass
class LayoutResult:
    sections: list[PlacedSection]
    warnings: list[LayoutWarning]
    skipped_areas: list[SkippedArea]

@dataclass
class PlacedSection:
    config: SectionConfig
    bounds: SectionBounds
    height_mode: str  # "full", "lower", "upper"

@dataclass
class LayoutWarning:
    message: str
    suggestion: str | None
```

---

## Layout Algorithm

### Section Placement Logic

1. Get all obstacle zones for target wall
2. Find valid regions (gaps between obstacles)
3. For each requested section:
   - If `height_mode=auto`: find best fit (full > lower > upper)
   - If section fits in valid region: place it
   - If section overlaps obstacle:
     - Try resize to fit adjacent gap
     - Try split around obstacle
     - If neither works and section < min_width: skip with warning
4. Return placed sections with warnings

### Partial-Height Logic

```
Wall with window:
+------------------------------------------+
|                                          |  <- Upper region
|    +------------------------+            |     (window top + clearance to ceiling)
|    |       WINDOW           |            |
|    +------------------------+            |
|                                          |  <- Lower region
|                                          |     (floor to window bottom - clearance)
+------------------------------------------+

If height_mode=auto and obstacle is window:
  - Check if lower region height >= min_section_height
  - Check if upper region height >= min_section_height
  - Place sections in viable regions
```

---

## Validation Rules

| Rule | Check | Message |
|------|-------|---------|
| V-01 | Obstacle within wall bounds | "Obstacle '{name}' extends beyond wall {wall_index}" |
| V-02 | Wall reference valid | "Obstacle references unknown wall: {wall}" |
| V-03 | Clearance non-negative | "Clearance values must be non-negative" |
| V-04 | Usable area exists | "Wall {wall_index} entirely blocked by obstacles" |
| V-05 | Section fits somewhere | "Section {n} cannot fit: all regions blocked" |
| V-06 | Width above minimum | "Warning: Section {n} reduced to {w}\" (below recommended {min}\")" |

---

## Testing Strategy

### Unit Tests

| Test Case | Input | Expected |
|-----------|-------|----------|
| No obstacles | Empty obstacle list | Full wall available |
| Single window | 48" window centered | Left gap, right gap, lower region |
| Multiple obstacles | Window + outlet | Correct zone calculations |
| Collision detected | Section overlaps window | CollisionResult returned |
| No collision | Section in gap | Empty collision list |
| Section split | Wide section + centered obstacle | Two narrower sections |
| Lower section | Window, height_mode=lower | Section below window |
| Blocked wall | Door spanning full width | Validation error |

### Integration Tests

- Config with obstacles generates correct cabinet layout
- STL output shows sections avoiding obstacle regions
- Partial-height sections have correct dimensions
- Warnings surface in CLI output

---

## Implementation Phases

### Phase 1: Core Model (Est. 2 days)
- [ ] Add `ObstacleType` enum and `Clearance` value object
- [ ] Implement `Obstacle` entity with zone calculation
- [ ] Add `ObstacleZone` and `SectionBounds` value objects
- [ ] Default clearance configuration

### Phase 2: Collision Service (Est. 2 days)
- [ ] Implement `ObstacleCollisionService`
- [ ] Zone overlap detection
- [ ] Valid region finder
- [ ] Batch collision checking

### Phase 3: Layout Integration (Est. 3 days)
- [ ] Implement `ObstacleAwareLayoutService`
- [ ] Section splitting logic
- [ ] Partial-height section support
- [ ] Integration with existing layout service

### Phase 4: Config & Validation (Est. 2 days)
- [ ] Extend config schema to v1.2
- [ ] Obstacle validation rules
- [ ] Warning generation
- [ ] CLI output formatting

---

## Dependencies & Risks

### Dependencies
- FRD-01: Configuration schema for obstacle definitions
- FRD-02: Wall geometry for obstacle placement context
- Existing `Section` entity for layout integration

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex edge cases | Medium | Thorough test coverage; start with simple cases |
| Layout algorithm performance | Low | Optimize only if >100 obstacles (unlikely) |
| User confusion on clearances | Medium | Clear defaults; good documentation |
| Code compliance (outlets) | High | Research NEC codes; conservative defaults |

---

## Open Questions

1. **Code compliance**: What are actual NEC requirements for outlet accessibility?
   - Research needed; current assumption is outlet must be fully exposed

2. **Corner obstacles**: How to handle obstacles near wall corners?
   - Proposed: Obstacle belongs to one wall only; corner logic in FRD-02

3. **Floating cabinets**: Support wall-mounted upper cabinets (not floor-to-ceiling)?
   - Proposed: Yes via `height_mode=upper` with explicit height

---

## Appendix: Example Configurations

### Wall with Window (Lower Cabinets)

```json
{
  "schema_version": "1.2",
  "room": {
    "name": "window-wall",
    "walls": [{"length": 120, "height": 96}],
    "obstacles": [
      {
        "type": "window",
        "wall": 0,
        "horizontal_offset": 36,
        "bottom": 36,
        "width": 48,
        "height": 48
      }
    ]
  },
  "cabinet": {
    "depth": 12,
    "sections": [
      {"width": 36, "shelves": 4},
      {"width": 48, "height_mode": "lower", "shelves": 2},
      {"width": 36, "shelves": 4}
    ]
  }
}
```

### Wall with Multiple Obstacles

```json
{
  "schema_version": "1.2",
  "room": {
    "name": "busy-wall",
    "walls": [{"length": 144, "height": 96}],
    "obstacles": [
      {"type": "door", "wall": 0, "horizontal_offset": 0, "bottom": 0, "width": 36, "height": 84},
      {"type": "outlet", "wall": 0, "horizontal_offset": 48, "bottom": 12, "width": 3, "height": 5},
      {"type": "outlet", "wall": 0, "horizontal_offset": 108, "bottom": 12, "width": 3, "height": 5},
      {"type": "vent", "wall": 0, "horizontal_offset": 60, "bottom": 0, "width": 12, "height": 4}
    ]
  },
  "cabinet": {
    "depth": 12,
    "sections": [
      {"width": "fill", "wall": 0, "shelves": 4}
    ]
  }
}
```

### Custom Clearance Override

```json
{
  "schema_version": "1.2",
  "obstacle_defaults": {
    "window": {"top": 3, "bottom": 3, "left": 3, "right": 3}
  },
  "room": {
    "walls": [{"length": 96, "height": 96}],
    "obstacles": [
      {
        "type": "window",
        "wall": 0,
        "horizontal_offset": 24,
        "bottom": 30,
        "width": 48,
        "height": 36,
        "clearance": {"top": 1, "bottom": 6, "left": 2, "right": 2}
      }
    ]
  }
}
```

---

## Implementation Analysis: Codebase Alignment

This section documents the codebase analysis performed to align the FRD with existing infrastructure and identify implementation pathways.

### Implementation Analysis: Domain Layer (Backend Support)

#### Current State

**Relevant Files:**
- `src/cabinets/domain/entities.py` - Contains `Wall`, `Cabinet`, `Section`, `Shelf`, `Panel` entities
- `src/cabinets/domain/value_objects.py` - Contains `Position`, `Position3D`, `Dimensions`, `BoundingBox3D`, `MaterialSpec`, `CutPiece`
- `src/cabinets/domain/services.py` - Contains `LayoutCalculator`, `Panel3DMapper`, `CutListGenerator`, `MaterialEstimator`
- `src/cabinets/domain/section_resolver.py` - Contains `SectionSpec`, `resolve_section_widths()`

**Existing Patterns:**

1. **Wall Entity** (entities.py:213-228): Simple frozen dataclass with `width`, `height`, `depth`. No concept of wall index or obstacles.

2. **Position/Position3D**: 2D `Position(x, y)` for cabinet-internal coordinates; `Position3D(x, y, z)` for 3D space. Both enforce non-negative values.

3. **BoundingBox3D**: Used for STL mesh generation with `get_vertices()` and `get_triangles()`. This is 3D-specific and not suitable for 2D obstacle collision detection.

4. **Section Entity** (entities.py:56-69): Has `width`, `height`, `depth`, `position`, and `shelves`. No `height_mode` concept.

5. **SectionSpec** (section_resolver.py:19-50): Supports `width: float | Literal["fill"]` and `shelves: int`. No `height_mode` or `wall` field.

6. **LayoutCalculator** (services.py:38-171): Generates cabinets from `Wall` + `LayoutParameters`. Assumes full-height sections with no obstacle awareness.

#### Needed Work

- [ ] Add `ObstacleType` enum to `value_objects.py` - Complexity: Low
- [ ] Add `Clearance` frozen dataclass to `value_objects.py` - Complexity: Low
- [ ] Add `SectionBounds` value object (2D bounding box for sections) - Complexity: Low
- [ ] Add `ObstacleZone` value object (2D bounding box with obstacle reference) - Complexity: Low
- [ ] Add `Obstacle` entity to `entities.py` with zone calculation - Complexity: Medium
- [ ] Add `CollisionResult`, `ValidRegion`, `PlacedSection`, `LayoutResult` value objects - Complexity: Low
- [ ] Extend `SectionSpec` with optional `height_mode` field - Complexity: Low
- [ ] Create `ObstacleCollisionService` in `services.py` - Complexity: Medium
- [ ] Create `ObstacleAwareLayoutService` in `services.py` - Complexity: High

**Dependencies:** FRD-02's `WallSegment` must exist for `wall_index` reference

#### Recommended Approach

Add new value objects (`ObstacleType`, `Clearance`, `SectionBounds`, `ObstacleZone`) to `value_objects.py`. These are distinct from existing types which serve different purposes:
- `Position`/`Position3D`: Cabinet-internal positioning (non-negative)
- `SectionBounds`/`ObstacleZone`: Wall surface collision detection (can have negative values for clearance overflow)
- `BoundingBox3D`: 3D mesh generation

Create `Obstacle` entity in `entities.py` with zone calculation method. The entity follows existing patterns (dataclass with `__post_init__` validation).

`ObstacleCollisionService` and `ObstacleAwareLayoutService` follow the existing service pattern in `services.py`, taking dependencies via constructor injection.

---

### Implementation Analysis: Application Layer

#### Current State

**Relevant Files:**
- `src/cabinets/application/config/schema.py` - Pydantic v2 schema with `CabinetConfiguration` root model
- `src/cabinets/application/config/adapter.py` - Converts config to DTOs and `SectionSpec`
- `src/cabinets/application/config/validator.py` - Validation structures and woodworking advisories
- `src/cabinets/application/config/loader.py` - JSON loading with error handling

**Existing Patterns:**

1. **Schema versioning**: Uses pattern `r"^\d+\.\d+$"` with major version 1 validation. v1.2 is supported by pattern.

2. **Strict validation**: All Pydantic models use `extra="forbid"` to reject unknown fields.

3. **SectionConfig** (schema.py:31-51): Has `width: float | Literal["fill"]` and `shelves: int`. No `height_mode` field.

4. **ValidationResult** (validator.py:51-111): Collects errors and warnings with path-based messages.

5. **check_woodworking_advisories()** (validator.py:120-208): Pattern for advisory validation checks.

6. **Config adapter** (adapter.py): Clean conversion layer with `config_to_dtos()` and `config_to_section_specs()`.

#### Needed Work

- [ ] Add `ObstacleTypeConfig` enum to schema (matches domain `ObstacleType`) - Complexity: Low
- [ ] Add `ClearanceConfig` Pydantic model - Complexity: Low
- [ ] Add `ObstacleConfig` Pydantic model - Complexity: Low
- [ ] Add `ObstacleDefaultsConfig` model for clearance defaults - Complexity: Low
- [ ] Add optional `obstacle_defaults` field to `CabinetConfiguration` - Complexity: Low
- [ ] Add optional `obstacles` array to `RoomConfig` (from FRD-02) - Complexity: Low
- [ ] Add optional `height_mode` field to `SectionConfig` - Complexity: Low
- [ ] Add `config_to_obstacles()` adapter function - Complexity: Low
- [ ] Add `config_to_clearance_defaults()` adapter function - Complexity: Low
- [ ] Add obstacle validation rules (V-01 through V-06) to `validator.py` - Complexity: Medium
- [ ] Extend `validate_config()` to include obstacle validation - Complexity: Low

**Dependencies:** FRD-02's `RoomConfig` must exist for `obstacles` array placement

#### Recommended Approach

Extend existing schema incrementally:
1. Add obstacle-related Pydantic models to `schema.py`
2. Make `obstacle_defaults` optional at root level
3. Add `obstacles` array to `RoomConfig` (FRD-02 provides the base)
4. Add `height_mode` to `SectionConfig` with enum validation
5. Add adapter functions following `config_to_section_specs()` pattern
6. Add validation following `check_woodworking_advisories()` pattern

Schema v1.0 and v1.1 configs remain 100% compatible (no obstacles field = empty list).

---

### Implementation Analysis: Infrastructure Layer

#### Current State

**Relevant Files:**
- `src/cabinets/infrastructure/stl_exporter.py` - `StlMeshBuilder`, `StlExporter`
- `src/cabinets/infrastructure/exporters.py` - `CutListFormatter`, `LayoutDiagramFormatter`, `MaterialReportFormatter`, `JsonExporter`

**Existing Patterns:**

1. **StlExporter** (stl_exporter.py): Uses `Panel3DMapper` to get boxes, builds combined mesh at origin. Obstacle avoidance happens upstream in layout service.

2. **LayoutDiagramFormatter** (exporters.py:41-123): ASCII art for single cabinet layout. Could be extended to show obstacle zones.

3. **JsonExporter** (exporters.py:155-189): Exports cabinet, cut list, and material estimate.

#### Needed Work

- [ ] (Optional) Extend `LayoutDiagramFormatter` to show obstacle zones on wall - Complexity: Medium
- [ ] (Optional) Extend `JsonExporter` to include obstacle data in output - Complexity: Low
- [ ] No changes needed for `StlExporter` - obstacles affect layout, not mesh generation

**Dependencies:** Layout service produces placed sections; infrastructure just renders them

#### Recommended Approach

Infrastructure changes are optional enhancements. The core obstacle avoidance functionality is in the domain layer (services). Infrastructure receives already-placed sections and renders them as before.

Future enhancement: Add ASCII visualization of obstacle zones in `LayoutDiagramFormatter` to help users understand layout decisions.

---

### Implementation Analysis: FRD-02 Dependencies

#### Critical Dependencies (Must Complete First)

FRD-03 cannot be implemented until FRD-02 provides:

1. **WallSegment Entity**: Provides `wall_index` for obstacle placement reference
2. **Room Aggregate**: Container for obstacles array
3. **RoomConfig Schema**: Base model that FRD-03 extends with `obstacles` field
4. **RoomLayoutService**: Foundation that `ObstacleAwareLayoutService` builds upon

#### FRD-02 Current State

Based on the refinement tracking document:
- Status: "Codebase Aligned and Ready for Task Breakdown"
- Implementation not yet started
- Estimated 10-11 days effort

#### Integration Strategy

| FRD-02 Phase | FRD-03 Can Start |
|--------------|------------------|
| Phase 1: Core Geometry (WallSegment, Room) | FRD-03 Phase 1 can start after |
| Phase 2: Layout Service (RoomLayoutService) | FRD-03 Phase 2-3 can start after |
| Phase 3: Schema and Config | FRD-03 Phase 4 can start after |
| Phase 4: Testing | Can run in parallel |

#### Recommended Sequencing

1. Wait for FRD-02 Phase 1-2 completion (WallSegment, Room, RoomLayoutService)
2. Start FRD-03 Phase 1 (Core Model) when FRD-02 Phase 2 is complete
3. FRD-03 Phase 3 (Layout Integration) wraps/extends FRD-02's RoomLayoutService
4. FRD-03 Phase 4 (Config) extends FRD-02's schema v1.1 to v1.2

---

### Implementation Analysis: Testing Infrastructure

#### Current State

**Relevant Files:**
- `tests/unit/test_config_schema.py` - Comprehensive schema tests
- `tests/fixtures/configs/` - JSON fixture files (6 files)
- `tests/integration/test_validate_command.py` - CLI integration tests

**Existing Patterns:**

1. Uses pytest with class-based test organization
2. Pydantic validation tested via direct model instantiation
3. Fixture configs stored as JSON files in `tests/fixtures/configs/`
4. `FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "configs"`
5. `ValidationResult` tested for error/warning handling

#### Needed Work

- [ ] Add `tests/unit/test_obstacle_entity.py` - Complexity: Medium
  - Test `Obstacle` creation and validation
  - Test zone calculation with clearances
  - Test clearance override behavior
- [ ] Add `tests/unit/test_obstacle_collision_service.py` - Complexity: Medium
  - Test zone overlap detection
  - Test valid region finding
  - Test batch collision checking
- [ ] Add `tests/unit/test_obstacle_aware_layout_service.py` - Complexity: Medium-High
  - Test section splitting
  - Test partial-height section generation
  - Test layout preference order (resize > split > skip)
- [ ] Add obstacle config fixtures to `tests/fixtures/configs/` - Complexity: Low
  - `valid_with_obstacles.json`
  - `obstacles_block_wall.json`
  - `custom_clearances.json`
- [ ] Add `tests/integration/test_obstacle_generation.py` - Complexity: Medium
  - End-to-end obstacle config loading and layout generation
  - Verify sections avoid obstacles correctly

**Dependencies:** All implementation must be complete for integration tests

---

### Lateral Moves Identified

#### 1. SectionSpec Height Mode Extension
**Description:** Extend `SectionSpec` dataclass with optional `height_mode: Literal["full", "lower", "upper", "auto"] | None` field.
**Rationale:** Required for partial-height sections around windows.
**Impact:** Additive change, existing code unaffected (defaults to `None` = full height).
**Status:** Ready to implement.

#### 2. 2D Bounding Box Types (Separate from 3D)
**Description:** Create `SectionBounds` and `ObstacleZone` as new value objects distinct from `BoundingBox3D`.
**Rationale:** Different semantic purpose (wall surface collision vs 3D mesh). Different constraints (can have negative values for clearance overflow).
**Impact:** New types, no modification to existing code.
**Status:** Ready to implement.

#### 3. ObstacleAwareLayoutService as Wrapper
**Description:** Create `ObstacleAwareLayoutService` that wraps `RoomLayoutService` rather than modifying it.
**Rationale:** Clean separation of concerns. Testable in isolation. Non-destructive to FRD-02 work.
**Approach:**
  - Takes `RoomLayoutService` via constructor injection
  - Intercepts section layout requests
  - Applies obstacle zone filtering
  - Delegates actual layout to wrapped service
**Status:** Pending FRD-02 implementation.

#### 4. Validation Extension Pattern
**Description:** Add `check_obstacle_advisories()` following the `check_woodworking_advisories()` pattern.
**Rationale:** Consistent validation approach, reuses existing structures.
**Status:** Ready to implement after schema changes.

---

### Revised Complexity Assessment

| Component | Complexity | Effort | Risk | Notes |
|-----------|------------|--------|------|-------|
| ObstacleType, Clearance VOs | Low | 0.5 day | Low | Simple types |
| SectionBounds, ObstacleZone VOs | Low | 0.5 day | Low | 2D rectangles with overlap |
| Obstacle entity with zone calc | Medium | 0.5 day | Low | Dataclass with methods |
| CollisionResult, ValidRegion, etc | Low | 0.25 day | Low | Simple containers |
| SectionSpec height_mode field | Low | 0.25 day | Low | Add field to existing |
| ObstacleCollisionService | Medium | 1.5 days | Medium | Zone overlap, region finding |
| ObstacleAwareLayoutService | High | 2.5 days | Medium-High | Section splitting, partial-height |
| Config schema v1.2 extensions | Low | 0.5 day | Low | Pydantic models |
| Config adapters (obstacles) | Low | 0.5 day | Low | Conversion functions |
| Obstacle validation rules | Medium | 1 day | Low | V-01 through V-06 |
| Unit tests | Medium | 1.5 days | Low | Entity, collision, layout |
| Integration tests | Medium | 1 day | Low | End-to-end |
| **Total** | | **10-11 days** | | After FRD-02 |

---

### Implementation Pathway Summary

**Phase 1: Foundation (2 days)** - Can start when FRD-02 Phase 1 is near completion
1. Add value objects: `ObstacleType`, `Clearance`, `SectionBounds`, `ObstacleZone`
2. Add result types: `CollisionResult`, `ValidRegion`
3. Add `Obstacle` entity with zone calculation
4. Add `height_mode` to `SectionSpec`
5. Add unit tests for entities and value objects

**Phase 2: Collision Service (2 days)** - Requires FRD-02 WallSegment
1. Implement `ObstacleCollisionService`
2. Zone overlap detection (`overlaps()` method)
3. Valid region finder for wall
4. Batch collision checking
5. Add unit tests for collision service

**Phase 3: Layout Integration (3 days)** - Requires FRD-02 RoomLayoutService
1. Add result types: `PlacedSection`, `LayoutResult`, `LayoutWarning`, `SkippedArea`
2. Implement `ObstacleAwareLayoutService` wrapping RoomLayoutService
3. Section splitting logic
4. Partial-height section support (lower/upper/auto)
5. Integration with existing LayoutCalculator for cabinet generation
6. Add unit tests for layout service

**Phase 4: Config and Validation (2 days)** - Requires FRD-02 RoomConfig
1. Add Pydantic models: `ObstacleConfig`, `ClearanceConfig`, `ObstacleDefaultsConfig`
2. Add `height_mode` to `SectionConfig`
3. Add `obstacle_defaults` to `CabinetConfiguration`
4. Add `obstacles` to `RoomConfig`
5. Add adapter functions
6. Add validation rules (V-01 through V-06)
7. Add config tests

**Phase 5: Integration and Polish (2 days)**
1. Integration tests for obstacle configs
2. Update fixture configs with obstacle examples
3. (Optional) Extend LayoutDiagramFormatter for obstacle visualization
4. Documentation examples

---

### Codebase Alignment Verification

- [x] FRD entities follow existing domain patterns (dataclasses with `__post_init__` validation)
- [x] FRD value objects follow frozen dataclass pattern with property methods
- [x] FRD services follow existing service patterns (constructor injection, clear method signatures)
- [x] FRD schema extension aligns with existing Pydantic v2 patterns
- [x] FRD validation follows existing `ValidationResult` and advisory patterns
- [x] FRD testing strategy aligns with existing pytest patterns and fixtures
- [x] Backward compatibility path verified (no obstacles = empty list, existing flow unchanged)
- [x] All lateral moves identified and documented
- [x] No destructive changes to existing functionality required
- [x] FRD-02 dependencies clearly identified and sequencing documented
