# FRD-02: Room & Wall Geometry Model

**Created:** 2025-12-27
**Status:** Codebase Aligned and Ready for Task Breakdown
**Priority:** Foundation
**Depends On:** FRD-01 (Configuration Schema)
**Refinement Date:** 2025-12-27

---

## Problem Statement

Built-in cabinets rarely span a single flat wall. Real installations involve corners (L-shape, U-shape), angled walls, and multi-wall runs. The current `Wall` entity is a simple dimension container that cannot model these spatial relationships. A geometry-aware room model is needed to:

- Calculate cabinet layouts across connected wall segments
- Handle 90-degree inside corners where cabinets wrap
- Validate that wall configurations form valid geometry
- Position cabinet sections correctly in 3D space

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| Model connected walls | `WallSegment` entities connect via angles; geometry computes automatically |
| Support L/U shapes | 90-degree inside corners render correctly with proper cabinet wrapping |
| Validate geometry | Invalid configurations (overlapping walls, impossible angles) rejected |
| Integrate with Cabinet | Cabinets can span multiple wall segments with correct 3D positioning |
| JSON configuration | Room geometry expressible in FRD-01 config schema |

---

## Scope

### In Scope
- `WallSegment` entity: length, height, angle from previous wall
- `Room` aggregate: ordered collection of wall segments
- Coordinate system with first wall at origin
- 90-degree inside corner support (angle = 90 or -90)
- Open rooms (sequence) and closed rooms (polygon)
- Wall connection validation
- Multi-wall layout calculation service
- Cabinet-to-wall-segment assignment

### Out of Scope
- Arbitrary angles (non-90-degree corners) - future enhancement
- Outside corners (cabinets don't wrap outside corners)
- Doors/windows as wall features - separate FRD
- 3D room visualization
- Import from CAD formats

---

## Domain Model

### Coordinate System

```
Y (depth into wall)
^
|
|    Wall continues at angle
|    from endpoint
|
+---------> X (along wall)

- First wall starts at origin (0, 0), runs along positive X
- Angle 0 = continues straight (same direction)
- Angle 90 = turns right (inside corner, Y becomes new X direction)
- Angle -90 = turns left (inside corner)
- Z axis is vertical (height)
```

### Wall Segment Relationships

```
        Wall 2 (angle=90 from Wall 1)
           |
           |
           v
Wall 1 ----+
(starts at origin)

L-Shape: [Wall1, Wall2] where Wall2.angle = 90
U-Shape: [Wall1, Wall2, Wall3] where Wall2.angle = 90, Wall3.angle = 90
```

---

## Functional Requirements

### FR-01: WallSegment Entity

- **FR-01.1**: WallSegment SHALL have: `length` (float, inches), `height` (float, inches), `angle` (float, degrees)
- **FR-01.2**: `length` and `height` SHALL be positive values
- **FR-01.3**: `angle` SHALL be relative to previous wall's direction (0 = straight, 90 = right turn, -90 = left turn)
- **FR-01.4**: First wall in a room SHALL have `angle = 0` (establishes baseline direction)
- **FR-01.5**: WallSegment SHALL compute its start and end points given a starting position and direction

### FR-02: Room Aggregate

- **FR-02.1**: Room SHALL contain an ordered list of 1+ WallSegment entities
- **FR-02.2**: Room SHALL have a `name` identifier (string)
- **FR-02.3**: Room SHALL have `is_closed` property (boolean) - whether walls form a closed polygon
- **FR-02.4**: Room SHALL compute global coordinates for each wall segment's start/end points
- **FR-02.5**: Room SHALL expose total linear wall length (sum of all segments)
- **FR-02.6**: Room SHALL expose bounding box dimensions

### FR-03: Geometry Validation

- **FR-03.1**: Adjacent walls SHALL connect (end of wall N = start of wall N+1)
- **FR-03.2**: Closed rooms SHALL have final wall end within tolerance of first wall start (configurable, default 0.1")
- **FR-03.3**: Walls SHALL NOT self-intersect (crossing paths invalid)
- **FR-03.4**: Validation errors SHALL identify specific wall segments involved
- **FR-03.5**: For v1, angles SHALL be constrained to {-90, 0, 90} degrees

### FR-04: Cabinet Integration

- **FR-04.1**: Cabinet sections SHALL be assignable to specific wall segments
- **FR-04.2**: A cabinet section's width SHALL NOT exceed its assigned wall segment's length
- **FR-04.3**: Cabinet spanning multiple walls SHALL have sections for each wall segment
- **FR-04.4**: Corner sections SHALL be flagged for special panel generation (future)
- **FR-04.5**: Layout service SHALL compute 3D position/rotation for each section based on wall geometry

### FR-05: Configuration Schema Extension

- **FR-05.1**: Config schema v1.1 SHALL add optional `room` object at root level
- **FR-05.2**: Room config SHALL support inline wall definitions or reference to separate room file
- **FR-05.3**: Section assignment SHALL use `wall_index` (0-based) or `wall_name` reference
- **FR-05.4**: Schema SHALL validate wall references exist

---

## Data Models

### WallSegment Entity

```python
# src/cabinets/domain/entities.py

@dataclass
class WallSegment:
    """A wall segment in a room, with position relative to previous wall."""

    length: float          # Length along the wall (inches)
    height: float          # Wall height (inches)
    angle: float = 0.0     # Angle from previous wall direction (degrees)
    name: str | None = None  # Optional identifier
    depth: float = 12.0    # Available depth for cabinets (inches)

    def __post_init__(self) -> None:
        if self.length <= 0 or self.height <= 0:
            raise ValueError("Wall dimensions must be positive")
        if self.angle not in (-90, 0, 90):
            raise ValueError("Angle must be -90, 0, or 90 degrees")
```

### Room Aggregate

```python
@dataclass
class Room:
    """A room defined by connected wall segments."""

    name: str
    walls: list[WallSegment]
    is_closed: bool = False
    closure_tolerance: float = 0.1  # inches

    def __post_init__(self) -> None:
        if not self.walls:
            raise ValueError("Room must have at least one wall")
        if self.walls[0].angle != 0:
            raise ValueError("First wall must have angle=0")

    def get_wall_positions(self) -> list[WallPosition]:
        """Calculate global coordinates for each wall."""
        ...

    def validate_geometry(self) -> list[GeometryError]:
        """Check for geometry errors."""
        ...

    @property
    def total_length(self) -> float:
        """Sum of all wall segment lengths."""
        return sum(w.length for w in self.walls)

    @property
    def bounding_box(self) -> tuple[float, float]:
        """(width, depth) bounding box of room footprint."""
        ...
```

### Supporting Value Objects

```python
# src/cabinets/domain/value_objects.py

@dataclass(frozen=True)
class Point2D:
    """2D point in room coordinate space."""
    x: float
    y: float

@dataclass(frozen=True)
class WallPosition:
    """Computed position and orientation of a wall segment."""
    wall_index: int
    start: Point2D
    end: Point2D
    direction: float  # Angle in degrees from positive X axis

@dataclass(frozen=True)
class GeometryError:
    """Geometry validation error."""
    wall_indices: tuple[int, ...]
    message: str
    error_type: str  # "intersection", "closure", "invalid_angle"
```

---

## Configuration Schema Extension (v1.1)

### Room Configuration

```json
{
  "schema_version": "1.1",
  "room": {
    "name": "living-room-corner",
    "walls": [
      {"length": 96, "height": 96, "name": "main"},
      {"length": 48, "height": 96, "angle": 90, "name": "return"}
    ],
    "is_closed": false
  },
  "cabinet": {
    "depth": 12,
    "material": {"type": "plywood", "thickness": 0.75},
    "sections": [
      {"width": 48, "wall": "main", "shelves": 4},
      {"width": 48, "wall": "main", "shelves": 4},
      {"width": 48, "wall": "return", "shelves": 4}
    ]
  }
}
```

### Field Definitions

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `room.name` | string | Yes | - | Non-empty |
| `room.walls` | array | Yes | - | 1+ items |
| `room.walls[].length` | float | Yes | - | > 0 |
| `room.walls[].height` | float | Yes | - | > 0 |
| `room.walls[].angle` | float | No | 0 | -90, 0, or 90 |
| `room.walls[].name` | string | No | - | Unique within room |
| `room.walls[].depth` | float | No | 12.0 | > 0 |
| `room.is_closed` | bool | No | false | - |
| `cabinet.sections[].wall` | string\|int | No | 0 | Wall name or index |

---

## Layout Calculation Service

### RoomLayoutService

```python
# src/cabinets/domain/services.py

class RoomLayoutService:
    """Calculates cabinet positions within room geometry."""

    def assign_sections_to_walls(
        self,
        room: Room,
        sections: list[SectionConfig]
    ) -> list[WallSectionAssignment]:
        """
        Assign cabinet sections to wall segments.
        Returns assignments with computed positions.
        Raises if sections don't fit on assigned walls.
        """
        ...

    def compute_section_transforms(
        self,
        room: Room,
        assignments: list[WallSectionAssignment]
    ) -> list[SectionTransform]:
        """
        Compute 3D position and rotation for each section.
        Used for STL generation with correct spatial layout.
        """
        ...

    def validate_fit(
        self,
        room: Room,
        sections: list[SectionConfig]
    ) -> list[FitError]:
        """Check that sections fit on their assigned walls."""
        ...
```

### Transform Computation

```python
@dataclass(frozen=True)
class SectionTransform:
    """3D transform for positioning a cabinet section."""
    section_index: int
    wall_index: int
    position: Position3D      # Origin point in room coordinates
    rotation_z: float         # Rotation around Z axis (degrees)

@dataclass
class WallSectionAssignment:
    """Assignment of a section to a wall segment."""
    section_index: int
    wall_index: int
    offset_along_wall: float  # Distance from wall start
```

---

## Validation Rules

### Geometry Validation

| Rule | Check | Error Message |
|------|-------|---------------|
| G-01 | First wall angle = 0 | "First wall must have angle=0" |
| G-02 | Angle in {-90, 0, 90} | "Wall {n}: angle must be -90, 0, or 90" |
| G-03 | No self-intersection | "Walls {n} and {m} intersect" |
| G-04 | Closed room closes | "Room does not close: gap of {x} inches" |
| G-05 | Positive dimensions | "Wall {n}: length must be positive" |

### Fit Validation

| Rule | Check | Error Message |
|------|-------|---------------|
| F-01 | Section fits on wall | "Section {n} width {w} exceeds wall {m} length {l}" |
| F-02 | Wall reference valid | "Section {n} references unknown wall '{name}'" |
| F-03 | No overlap on wall | "Sections {n} and {m} overlap on wall {w}" |

---

## Migration Path

### Refactoring Existing `Wall` Entity

Current `Wall` becomes `WallConstraints` for backward compatibility:

```python
# Deprecate but keep for compatibility
@dataclass(frozen=True)
class WallConstraints:
    """Simple wall dimensions (deprecated, use WallSegment)."""
    width: float
    height: float
    depth: float
```

Single-wall configurations continue to work:
- If no `room` in config, create implicit single-wall room
- `cabinet.width/height/depth` maps to single WallSegment

---

## Testing Strategy

### Unit Tests

| Test Case | Input | Expected |
|-----------|-------|----------|
| Single wall room | 1 wall, angle=0 | Valid room |
| L-shape room | 2 walls, second angle=90 | Valid, correct positions |
| U-shape room | 3 walls, angles 90, 90 | Valid, correct positions |
| Invalid first angle | First wall angle=90 | Validation error |
| Self-intersection | Walls that cross | Validation error |
| Section fits | Width < wall length | Valid assignment |
| Section too wide | Width > wall length | Fit error |

### Integration Tests

- Load room config from JSON, generate cabinet with correct geometry
- Multi-wall cabinet produces valid STL with correct transforms
- L-shape corner generates properly positioned sections

---

## Implementation Phases

### Phase 1: Core Geometry (Est. 3 days)
- [ ] Add `Point2D` value object
- [ ] Implement `WallSegment` entity
- [ ] Implement `Room` aggregate with position calculation
- [ ] Basic geometry validation (angles, dimensions)

### Phase 2: Layout Service (Est. 2 days)
- [ ] Implement `RoomLayoutService`
- [ ] Section-to-wall assignment
- [ ] 3D transform computation
- [ ] Fit validation

### Phase 3: Integration (Est. 2 days)
- [ ] Extend config schema to v1.1 with room support
- [ ] Update cabinet generation to use room geometry
- [ ] Backward compatibility for single-wall configs

### Phase 4: Testing & Polish (Est. 2 days)
- [ ] Unit tests for geometry calculations
- [ ] Integration tests for multi-wall cabinets
- [ ] Documentation and examples

---

## Dependencies & Risks

### Dependencies
- FRD-01 config schema (must be implemented first)
- Existing `Cabinet` entity (extend, don't break)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Geometry math errors | High | Extensive unit tests with known coordinates |
| Corner panel complexity | Medium | Defer corner-specific panels to future FRD |
| Performance with many walls | Low | Unlikely to have >20 walls; optimize if needed |

---

## Open Questions

1. **Corner panel handling**: Should corner sections have special panel generation (mitered edges, filler pieces)?
   - Proposed: Flag corners but defer special handling to FRD-03

2. **Partial wall coverage**: Can sections leave gaps on a wall (not fill entire length)?
   - Proposed: Yes, allow gaps. Sections specify width, not "fill wall"

3. **Multi-floor/multi-room**: Support multiple rooms in one config?
   - Proposed: No for v1. One room per config file.

---

## Appendix: Example Configurations

### Single Wall (Backward Compatible)

```json
{
  "schema_version": "1.0",
  "cabinet": {
    "width": 96,
    "height": 84,
    "depth": 12,
    "sections": [{"shelves": 4}]
  }
}
```

### L-Shape Corner

```json
{
  "schema_version": "1.1",
  "room": {
    "name": "corner-unit",
    "walls": [
      {"length": 72, "height": 84, "name": "left"},
      {"length": 48, "height": 84, "angle": 90, "name": "right"}
    ]
  },
  "cabinet": {
    "depth": 12,
    "sections": [
      {"width": 36, "wall": "left", "shelves": 4},
      {"width": 36, "wall": "left", "shelves": 4},
      {"width": 48, "wall": "right", "shelves": 4}
    ]
  }
}
```

### U-Shape Built-In

```json
{
  "schema_version": "1.1",
  "room": {
    "name": "alcove",
    "walls": [
      {"length": 36, "height": 96, "name": "left"},
      {"length": 72, "height": 96, "angle": 90, "name": "back"},
      {"length": 36, "height": 96, "angle": 90, "name": "right"}
    ]
  },
  "cabinet": {
    "depth": 14,
    "sections": [
      {"width": 36, "wall": "left", "shelves": 5},
      {"width": 72, "wall": "back", "shelves": 5},
      {"width": 36, "wall": "right", "shelves": 5}
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
1. **Wall Entity** (entities.py:213-227): Frozen dataclass with `width`, `height`, `depth`. Used by `LayoutCalculator.generate_cabinet()`.
2. **Position/Position3D**: 2D `Position(x, y)` for cabinet-internal coordinates; `Position3D(x, y, z)` for 3D space.
3. **BoundingBox3D**: Used for STL mesh generation with `get_vertices()` and `get_triangles()` methods.
4. **Panel3DMapper** (services.py:252-359): Maps 2D panels to 3D bounding boxes at origin with no rotation support.
5. **LayoutCalculator**: Generates cabinets from Wall + LayoutParameters. Has `generate_cabinet_from_specs()` for per-section control.
6. **SectionSpec**: Already supports `width: float | Literal["fill"]` and `shelves: int` - extendable for wall assignment.

#### Needed Work

- [ ] Add `Point2D` value object (room coordinate space) - Complexity: Low
- [ ] Add `WallPosition` value object (computed wall position/orientation) - Complexity: Low
- [ ] Add `GeometryError` value object (validation error details) - Complexity: Low
- [ ] Add `WallSegment` entity with `length`, `height`, `angle`, `name`, `depth` - Complexity: Low
- [ ] Add `Room` aggregate with `walls`, `name`, `is_closed`, position calculation - Complexity: Medium
- [ ] Add geometry validation (`validate_geometry()`) with intersection detection - Complexity: Medium-High
- [ ] Create type alias `WallConstraints = Wall` for backward compatibility - Complexity: Low
- [ ] Extend `SectionSpec` with optional `wall` field (str | int) - Complexity: Low

**Dependencies:** None - domain layer is foundation

#### Recommended Approach

Add new value objects (`Point2D`, `WallPosition`, `GeometryError`) to `value_objects.py`. Add `WallSegment` entity and `Room` aggregate to `entities.py`. Keep existing `Wall` entity and add `WallConstraints` alias. This preserves all existing behavior while enabling new functionality.

For `Point2D` vs existing `Position`: Use both - `Position` is for cabinet-internal coordinates (always non-negative), `Point2D` is for room coordinates (can be negative in some geometries). Different semantic meanings justify separate types.

---

### Implementation Analysis: Application Layer

#### Current State

**Relevant Files:**
- `src/cabinets/application/config/schema.py` - Pydantic v2 schema with `CabinetConfiguration` root model
- `src/cabinets/application/config/adapter.py` - Converts config to DTOs and `SectionSpec`
- `src/cabinets/application/config/loader.py` - Loads and validates JSON config files
- `src/cabinets/application/config/validator.py` - Woodworking advisory checks
- `src/cabinets/application/dtos.py` - `WallInput`, `LayoutParametersInput`, `LayoutOutput`
- `src/cabinets/application/commands.py` - `GenerateLayoutCommand` orchestration

**Existing Patterns:**
1. **Schema versioning**: Uses pattern `r"^\d+\.\d+$"` with major version 1 validation. v1.1 is already supported by pattern.
2. **Strict validation**: All Pydantic models use `extra="forbid"` to reject unknown fields.
3. **SectionConfig**: Already has `width: float | Literal["fill"]` and `shelves: int`.
4. **Config adapter**: Clean separation between schema models and domain objects.
5. **Validation result**: Uses `ValidationResult` with errors and warnings for advisory checks.

#### Needed Work

- [ ] Add `WallSegmentConfig` Pydantic model - Complexity: Low
- [ ] Add `RoomConfig` Pydantic model - Complexity: Low
- [ ] Add optional `room: RoomConfig | None` to `CabinetConfiguration` - Complexity: Low
- [ ] Add optional `wall: str | int` field to `SectionConfig` - Complexity: Low
- [ ] Add `config_to_room()` adapter function - Complexity: Low
- [ ] Extend `config_to_section_specs()` to include wall assignment - Complexity: Low
- [ ] Add `RoomInput` DTO (optional) - Complexity: Low
- [ ] Extend `GenerateLayoutCommand` to handle room geometry - Complexity: Medium
- [ ] Add room geometry validation to `validator.py` - Complexity: Medium

**Dependencies:** Domain layer entities must exist first

#### Recommended Approach

Extend existing schema incrementally:
1. Add `WallSegmentConfig` and `RoomConfig` to `schema.py`
2. Make `room` optional at root level - absence means single-wall mode
3. Extend `SectionConfig` with optional `wall` field
4. Add adapter functions for room conversion
5. Modify `GenerateLayoutCommand` to detect room config and route appropriately

Schema v1.0 configs remain 100% compatible (no `room` field = implicit single wall).

---

### Implementation Analysis: Infrastructure Layer

#### Current State

**Relevant Files:**
- `src/cabinets/infrastructure/stl_exporter.py` - `StlMeshBuilder`, `StlExporter`
- `src/cabinets/infrastructure/exporters.py` - `CutListFormatter`, `LayoutDiagramFormatter`, `MaterialReportFormatter`, `JsonExporter`

**Existing Patterns:**
1. **StlMeshBuilder**: Creates STL meshes from `BoundingBox3D`, combines multiple meshes.
2. **StlExporter**: Uses `Panel3DMapper` to get boxes, builds combined mesh at origin.
3. **LayoutDiagramFormatter**: ASCII art for single cabinet layout.

#### Needed Work

- [ ] Create `RoomPanel3DMapper` service - Complexity: Medium
  - Wraps `Panel3DMapper` for individual cabinets
  - Applies `SectionTransform` to translate/rotate bounding boxes
  - Returns combined list of transformed boxes
- [ ] Extend `StlMeshBuilder` with transform support (optional) - Complexity: Medium
- [ ] Update `LayoutDiagramFormatter` for multi-wall view (optional, can defer) - Complexity: Medium
- [ ] Extend `JsonExporter` to include room geometry in output - Complexity: Low

**Dependencies:** Domain layer `Room`, `SectionTransform` must exist

#### Recommended Approach

Create new `RoomPanel3DMapper` class that:
1. Takes `Room` and list of `(Cabinet, SectionTransform)` tuples
2. For each cabinet, uses existing `Panel3DMapper` to get boxes at origin
3. Applies rotation (around Z) and translation to each box based on transform
4. Returns combined list of `BoundingBox3D` objects

This preserves existing `Panel3DMapper` unchanged while adding multi-wall capability.

**Transform Math:**
```python
# For each bounding box from Panel3DMapper:
# 1. Rotate around Z axis by transform.rotation_z degrees
# 2. Translate by transform.position (x, y, z)
```

---

### Implementation Analysis: Domain Services

#### Current State

**Relevant File:** `src/cabinets/domain/services.py`

**Existing Services:**
- `LayoutCalculator`: Generates single cabinet from wall dimensions
- `Panel3DMapper`: Maps panels to 3D boxes (single cabinet at origin)
- `CutListGenerator`: Generates cut list from cabinet
- `MaterialEstimator`: Estimates material needs from cut list

#### Needed Work

- [ ] Add `RoomLayoutService` class - Complexity: Medium
  - `assign_sections_to_walls()`: Distribute sections across walls
  - `compute_section_transforms()`: Calculate 3D position/rotation per section
  - `validate_fit()`: Check sections fit on their assigned walls
- [ ] Add `SectionTransform` value object to `value_objects.py` - Complexity: Low
- [ ] Add `WallSectionAssignment` value object - Complexity: Low
- [ ] Add `FitError` value object for fit validation errors - Complexity: Low

**Dependencies:** `Room`, `WallSegment`, `WallPosition` must exist

#### Recommended Approach

Create `RoomLayoutService` as a new service class that:
1. Uses `Room.get_wall_positions()` to get wall coordinates
2. Groups sections by their `wall` assignment
3. For each wall, uses existing `LayoutCalculator` to generate cabinet section
4. Computes `SectionTransform` based on wall position and direction

This keeps existing `LayoutCalculator` unchanged and layers room awareness on top.

---

### Implementation Analysis: CLI Layer

#### Current State

**Relevant File:** `src/cabinets/cli/main.py`

**Existing Patterns:**
- Uses Typer with `--config` option for JSON files
- Merges CLI overrides with config file values
- Calls `GenerateLayoutCommand` for generation
- Outputs to various formats (STL, JSON, cutlist, diagram, materials)

#### Needed Work

- [ ] No CLI changes required for basic room support - Complexity: None
  - Config loading already handles any valid JSON
  - Room geometry flows through existing command infrastructure
- [ ] (Optional) Add `--room-file` option for separate room definition - Complexity: Low
- [ ] (Optional) Add room-specific output options - Complexity: Low

**Dependencies:** Application layer command must handle room configs

#### Recommended Approach

No immediate CLI changes needed. The existing `--config` path handles room configs transparently once the application layer supports them. Future enhancements can add room-specific CLI options.

---

### Implementation Analysis: Testing Infrastructure

#### Current State

**Relevant Files:**
- `tests/unit/test_config_schema.py` - Comprehensive schema tests
- `tests/fixtures/configs/` - JSON fixture files
- `tests/integration/test_validate_command.py` - CLI integration tests

**Existing Patterns:**
- Unit tests use pytest with direct model instantiation
- Fixture configs stored as JSON files in `tests/fixtures/configs/`
- Integration tests exercise CLI commands

#### Needed Work

- [ ] Add `tests/unit/test_room_geometry.py` - Complexity: Medium
  - Test `WallSegment` creation and validation
  - Test `Room` position calculation (L-shape, U-shape)
  - Test geometry validation (intersection detection)
- [ ] Add `tests/unit/test_room_layout_service.py` - Complexity: Medium
  - Test section-to-wall assignment
  - Test transform computation
  - Test fit validation
- [ ] Add room config fixtures to `tests/fixtures/configs/` - Complexity: Low
- [ ] Add `tests/integration/test_room_generation.py` - Complexity: Medium
  - Test end-to-end room config loading and generation
  - Test STL output with correct transforms
- [ ] Add backward compatibility tests for v1.0 configs - Complexity: Low

**Dependencies:** All implementation must be complete for integration tests

---

### Lateral Moves Identified

#### 1. Wall to WallConstraints Alias
**Description:** Add `WallConstraints = Wall` type alias for semantic clarity and future deprecation path.
**Rationale:** Allows gradual migration without breaking existing code.
**Impact:** Additive only, no risk.
**Status:** Ready to implement.

#### 2. Point2D vs Position Coexistence
**Description:** Keep both `Position` (cabinet-internal, non-negative) and `Point2D` (room coordinates, any value).
**Rationale:** Different semantic contexts justify separate types despite similar structure.
**Impact:** Minor complexity increase, clearer code.
**Status:** Approved approach.

#### 3. RoomPanel3DMapper Wrapper Pattern
**Description:** Create new `RoomPanel3DMapper` that wraps `Panel3DMapper` rather than modifying it.
**Rationale:** Preserves existing single-wall behavior unchanged, clean separation.
**Impact:** More code but safer, more maintainable.
**Status:** Recommended approach.

---

### Revised Complexity Assessment

| Component | Complexity | Effort | Notes |
|-----------|------------|--------|-------|
| Value Objects (Point2D, WallPosition, GeometryError, SectionTransform, WallSectionAssignment, FitError) | Low | 1 day | Straightforward frozen dataclasses |
| WallSegment entity | Low | 0.5 day | Simple dataclass with validation |
| Room aggregate with position calculation | Medium | 1.5 days | Geometry math for L/U shapes |
| Geometry validation (intersection detection) | Medium-High | 1 day | Line segment intersection algorithm |
| Config schema v1.1 (WallSegmentConfig, RoomConfig, section wall field) | Low | 0.5 day | Pydantic models |
| Config adapter extensions | Low | 0.5 day | Conversion functions |
| RoomLayoutService | Medium | 1.5 days | Section assignment and transform computation |
| RoomPanel3DMapper | Medium | 1 day | Transform application |
| GenerateLayoutCommand extension | Medium | 0.5 day | Room detection and routing |
| Unit tests | Medium | 1.5 days | Geometry, layout, config tests |
| Integration tests | Medium | 1 day | End-to-end, backward compatibility |
| **Total** | | **10-11 days** | |

---

### Implementation Pathway Summary

**Phase 1: Foundation (3 days)**
1. Add value objects: `Point2D`, `WallPosition`, `GeometryError`
2. Add `WallSegment` entity with validation
3. Add `Room` aggregate with position calculation
4. Add basic geometry validation (angles, dimensions)
5. Add unit tests for geometry

**Phase 2: Layout Service (2 days)**
1. Add `SectionTransform`, `WallSectionAssignment`, `FitError` value objects
2. Implement `RoomLayoutService` with section assignment
3. Implement transform computation
4. Implement fit validation
5. Add unit tests for layout service

**Phase 3: Schema and Config (1.5 days)**
1. Add `WallSegmentConfig`, `RoomConfig` to schema
2. Add `wall` field to `SectionConfig`
3. Add `room` field to `CabinetConfiguration`
4. Add adapter functions
5. Add config tests

**Phase 4: Infrastructure (1.5 days)**
1. Implement `RoomPanel3DMapper`
2. Extend `GenerateLayoutCommand` for room handling
3. Ensure backward compatibility for v1.0 configs

**Phase 5: Integration and Polish (2 days)**
1. Integration tests for room configs
2. Backward compatibility tests
3. Update/add fixture configs
4. Documentation examples

---

### Codebase Alignment Verification

- [x] FRD entities map to existing domain patterns (dataclasses, frozen value objects)
- [x] FRD schema extension aligns with existing Pydantic v2 patterns
- [x] FRD services align with existing service patterns (LayoutCalculator, Panel3DMapper)
- [x] FRD testing strategy aligns with existing pytest patterns
- [x] Backward compatibility path verified (v1.0 configs work unchanged)
- [x] All lateral moves identified and documented
- [x] No destructive changes to existing functionality required
