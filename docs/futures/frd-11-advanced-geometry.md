# FRD-11: Advanced Room Geometry

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** Medium
**Depends On:** FRD-02 (Room & Wall Geometry)

---

## Problem Statement

FRD-02 constrains wall angles to exactly 90 degrees. Real rooms have:

- Non-perpendicular walls (bay windows, angled alcoves, 45-degree corners)
- Outside corners where walls turn outward (convex geometry)
- Sloped ceilings (attic spaces, cathedral ceilings, under-stair areas)
- Skylights that project into cabinet space

These require specialized panel cuts and height calculations that FRD-02 cannot model.

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Support 45-135 degree wall angles | `wall.angle` accepts expanded range |
| Handle outside (convex) corners | Three treatment options configurable |
| Calculate sloped ceiling heights | Per-section height computed from slope |
| Model skylight voids | Top panel notching generated |
| Generate angled panel cuts | Cut metadata includes angle specifications |

---

## Scope

### In Scope
- Wall angles from 45 to 135 degrees
- Outside corner handling (angled face, butted filler, wrap-around)
- Ceiling slope definition and per-section height calculation
- Skylight void projection and top panel notching
- Angled cut specifications on panels (side panels, top panels)
- Minimum usable height warnings

### Out of Scope
- Curves or arcs (walls, ceilings)
- Multiple ceiling slopes per room
- Dormer window geometry
- Complex skylight shapes (only rectangular projections)

---

## Functional Requirements

### FR-01: Non-90-Degree Wall Angles

- **FR-01.1**: `wall.angle` SHALL accept values from -135 to 135 degrees
- **FR-01.2**: Angles SHALL remain relative to previous wall direction
- **FR-01.3**: Side panels at angled junctions SHALL include cut angle metadata
- **FR-01.4**: Filler panels SHALL be generated for angles where sections cannot meet flush

### FR-02: Outside Corners (Convex)

- **FR-02.1**: Outside corners occur when absolute angle > 90 degrees
- **FR-02.2**: `outside_corner_treatment` SHALL specify handling:
  - `angled_face`: 45-degree angled panel bridges the corner
  - `butted_filler`: Filler panel closes gap, sections butt to filler
  - `wrap_around`: Continuous shelving wraps the corner (open shelving only)
- **FR-02.3**: Outside corners SHALL NOT create dead space (unlike inside corners)
- **FR-02.4**: Default treatment SHALL be `angled_face`

### FR-03: Sloped Ceilings

- **FR-03.1**: `ceiling.slope` object SHALL define: `angle` (degrees), `start_height` (inches), `direction` ("left_to_right" | "right_to_left" | "front_to_back")
- **FR-03.2**: Section height SHALL be calculated: `start_height - (position_along_slope * tan(angle))`
- **FR-03.3**: Sections SHALL auto-size to fit under slope when `auto_fit: true`
- **FR-03.4**: `ceiling.slope.min_height` SHALL set minimum usable height (default: 24")
- **FR-03.5**: Sections below `min_height` SHALL generate a warning

### FR-04: Skylight Voids

- **FR-04.1**: `ceiling.skylights[]` array SHALL define skylight positions
- **FR-04.2**: Each skylight SHALL specify: `x_position`, `width`, `projection_depth`, `projection_angle`
- **FR-04.3**: Void at cabinet top level SHALL be calculated from projection geometry
- **FR-04.4**: Top panels SHALL be notched or split to avoid skylight voids
- **FR-04.5**: Sections directly under skylights SHALL have reduced height or notched tops

### FR-05: Panel Modifications

- **FR-05.1**: Side panels SHALL include `angle_cut` when adjacent to non-90 walls
- **FR-05.2**: Top panels SHALL include `taper` specification under sloped ceilings
- **FR-05.3**: Top panels SHALL include `notch` specification for skylight voids
- **FR-05.4**: All angle/taper/notch specs SHALL be in cut list metadata

### FR-06: Validation

- **FR-06.1**: Wall angle SHALL be rejected if outside -135 to 135 range
- **FR-06.2**: Ceiling slope angle SHALL be 0-60 degrees
- **FR-06.3**: Skylight void SHALL NOT exceed section width
- **FR-06.4**: Minimum height violations SHALL generate warnings, not errors

---

## Data Models

### Extended WallSegment

```python
# Extend src/cabinets/domain/entities.py

@dataclass
class WallSegment:
    """A wall segment with support for non-90-degree angles."""

    length: float
    height: float
    angle: float = 0.0  # -135 to 135 degrees
    name: str | None = None
    depth: float = 12.0

    def __post_init__(self) -> None:
        if self.length <= 0 or self.height <= 0:
            raise ValueError("Wall dimensions must be positive")
        if not -135 <= self.angle <= 135:
            raise ValueError("Angle must be between -135 and 135 degrees")
```

### CeilingSlope Value Object

```python
# src/cabinets/domain/value_objects.py

@dataclass(frozen=True)
class CeilingSlope:
    """Ceiling slope definition."""

    angle: float  # Degrees from horizontal (0-60)
    start_height: float  # Height at slope start (inches)
    direction: Literal["left_to_right", "right_to_left", "front_to_back"]
    min_height: float = 24.0  # Minimum usable height

    def __post_init__(self) -> None:
        if not 0 <= self.angle <= 60:
            raise ValueError("Slope angle must be 0-60 degrees")
        if self.start_height <= 0:
            raise ValueError("Start height must be positive")

    def height_at_position(self, position: float) -> float:
        """Calculate ceiling height at given position along slope."""
        from math import tan, radians
        return self.start_height - (position * tan(radians(self.angle)))
```

### Skylight Value Object

```python
@dataclass(frozen=True)
class Skylight:
    """Skylight definition with projection into cabinet space."""

    x_position: float  # Position along wall (inches)
    width: float  # Skylight width (inches)
    projection_depth: float  # How far it projects down (inches)
    projection_angle: float = 90.0  # Angle from ceiling (90 = vertical)

    def void_at_depth(self, cabinet_depth: float) -> tuple[float, float]:
        """Calculate void dimensions at cabinet top level.

        Returns: (void_start_x, void_width) at cabinet depth
        """
        from math import tan, radians
        if self.projection_angle == 90:
            return (self.x_position, self.width)
        # Angled projection expands the void
        expansion = cabinet_depth * tan(radians(90 - self.projection_angle))
        return (self.x_position - expansion / 2, self.width + expansion)
```

### Panel Cut Specifications

```python
@dataclass(frozen=True)
class AngleCut:
    """Specification for angled cut on panel edge."""

    edge: Literal["left", "right", "top", "bottom"]
    angle: float  # Degrees from perpendicular
    bevel: bool = False  # True for beveled edge, False for straight cut

@dataclass(frozen=True)
class TaperSpec:
    """Specification for tapered panel (sloped ceiling)."""

    start_height: float
    end_height: float
    direction: Literal["left_to_right", "right_to_left"]

@dataclass(frozen=True)
class NotchSpec:
    """Specification for notched panel (skylight void)."""

    x_offset: float  # From left edge
    width: float
    depth: float  # Notch depth from edge
    edge: Literal["top", "bottom", "left", "right"]

@dataclass(frozen=True)
class PanelCutMetadata:
    """Extended cut metadata for non-rectangular panels."""

    angle_cuts: tuple[AngleCut, ...] = ()
    taper: TaperSpec | None = None
    notches: tuple[NotchSpec, ...] = ()
```

### OutsideCornerConfig

```python
@dataclass(frozen=True)
class OutsideCornerConfig:
    """Configuration for outside (convex) corner treatment."""

    treatment: Literal["angled_face", "butted_filler", "wrap_around"] = "angled_face"
    filler_width: float = 3.0  # For butted_filler treatment
    face_angle: float = 45.0  # For angled_face treatment
```

---

## Configuration Schema Extensions

### Wall Angle (Extended)

```json
{
  "room": {
    "walls": [
      {"length": 72, "height": 84, "angle": 0},
      {"length": 48, "height": 84, "angle": 45}
    ]
  }
}
```

### Ceiling Slope

```json
{
  "room": {
    "ceiling": {
      "slope": {
        "angle": 30,
        "start_height": 96,
        "direction": "left_to_right",
        "min_height": 24
      }
    }
  }
}
```

### Skylights

```json
{
  "room": {
    "ceiling": {
      "skylights": [
        {
          "x_position": 36,
          "width": 24,
          "projection_depth": 8,
          "projection_angle": 75
        }
      ]
    }
  }
}
```

### Outside Corner Treatment

```json
{
  "room": {
    "walls": [
      {"length": 48, "height": 84, "angle": 0},
      {"length": 36, "height": 84, "angle": 120}
    ],
    "outside_corner": {
      "treatment": "angled_face",
      "face_angle": 45
    }
  }
}
```

---

## Technical Approach

### Height Calculation Service

```python
# src/cabinets/domain/services.py

class SlopedCeilingService:
    """Calculates section heights under sloped ceilings."""

    def calculate_section_heights(
        self,
        sections: list[SectionConfig],
        slope: CeilingSlope,
        wall_length: float,
    ) -> list[float]:
        """Calculate height for each section based on position."""
        heights = []
        current_position = 0.0

        for section in sections:
            # Use section midpoint for height calculation
            midpoint = current_position + section.width / 2
            height = slope.height_at_position(midpoint)

            if height < slope.min_height:
                # Will generate warning during validation
                height = slope.min_height

            heights.append(height)
            current_position += section.width

        return heights

    def generate_tapered_top(
        self,
        section_width: float,
        start_height: float,
        end_height: float,
        material: MaterialSpec,
    ) -> Panel:
        """Generate tapered top panel for sloped ceiling."""
        # Panel uses max height, taper spec defines the cut
        ...
```

### Skylight Void Service

```python
class SkylightVoidService:
    """Calculates skylight void intersections with cabinets."""

    def calculate_void_intersection(
        self,
        skylight: Skylight,
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> NotchSpec | None:
        """Calculate notch needed for skylight void, if any."""
        void_x, void_width = skylight.void_at_depth(cabinet_depth)
        void_end = void_x + void_width
        section_end = section_x + section_width

        # Check for intersection
        if void_end <= section_x or void_x >= section_end:
            return None  # No intersection

        # Calculate notch dimensions
        notch_x = max(0, void_x - section_x)
        notch_width = min(void_end, section_end) - max(void_x, section_x)

        return NotchSpec(
            x_offset=notch_x,
            width=notch_width,
            depth=skylight.projection_depth,
            edge="top",
        )
```

### Angle Cut Calculation

```python
def calculate_side_panel_cut(
    wall_angle: float,
    side: Literal["left", "right"],
) -> AngleCut | None:
    """Calculate angle cut for side panel at wall junction."""
    if wall_angle == 90 or wall_angle == -90:
        return None  # Standard 90-degree, no special cut

    # Adjust for which side of the junction
    cut_angle = abs(90 - abs(wall_angle)) / 2

    return AngleCut(
        edge="right" if side == "right" else "left",
        angle=cut_angle,
        bevel=True,
    )
```

---

## Validation Rules

| Rule | Check | Result |
|------|-------|--------|
| V-01 | -135 <= wall.angle <= 135 | ERROR if outside range |
| V-02 | 0 <= ceiling.slope.angle <= 60 | ERROR if outside range |
| V-03 | ceiling.slope.start_height > 0 | ERROR if non-positive |
| V-04 | skylight.width > 0 | ERROR if non-positive |
| V-05 | section_height < min_height | WARNING |
| V-06 | skylight void > section width | WARNING |
| V-07 | outside corner angle > 135 | ERROR |

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| 45-degree wall angle | angle=45 | Valid WallSegment |
| 135-degree wall angle | angle=135 | Valid WallSegment |
| Invalid angle (150) | angle=150 | ValueError |
| Height at slope position | slope=30, pos=24 | Calculated height |
| Skylight void intersection | skylight overlaps section | NotchSpec returned |
| No skylight intersection | skylight outside section | None returned |
| Side panel angle cut | wall_angle=45 | AngleCut with angle=22.5 |
| Min height warning | height < min_height | Warning generated |

### Integration Tests

- Sloped ceiling cabinet generates tapered top panels
- Skylight void produces notched top panels
- Multi-angle room layout calculates all positions correctly
- Outside corner treatments generate correct panels

---

## Implementation Phases

### Phase 1: Extended Angles (Est. 1 day)
- [ ] Extend `WallSegment.angle` validation to -135/135 range
- [ ] Update `Room.validate_geometry()` for new angles
- [ ] Add `AngleCut` specification to panel generation
- [ ] Side panel angle cut calculation

### Phase 2: Outside Corners (Est. 1 day)
- [ ] Add `OutsideCornerConfig` dataclass
- [ ] Implement three treatment options
- [ ] Generate filler/angled panels for outside corners
- [ ] Update layout service for convex geometry

### Phase 3: Sloped Ceilings (Est. 1.5 days)
- [ ] Add `CeilingSlope` value object
- [ ] Implement `SlopedCeilingService`
- [ ] Per-section height calculation
- [ ] `TaperSpec` and tapered panel generation
- [ ] Min height validation and warnings

### Phase 4: Skylight Voids (Est. 1 day)
- [ ] Add `Skylight` value object
- [ ] Implement `SkylightVoidService`
- [ ] Void projection calculation
- [ ] `NotchSpec` and notched panel generation

### Phase 5: Integration (Est. 0.5 day)
- [ ] Update config schema to v1.2
- [ ] Integration tests
- [ ] Documentation

---

## Dependencies & Risks

### Dependencies
- FRD-02: Base room geometry (this extends it)
- `WallSegment`, `Room`, `RoomLayoutService` from FRD-02
- Panel generation pipeline

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Angle math errors | High | Extensive unit tests with known values |
| Complex panel geometry | High | Start with simple cases, add complexity |
| STL generation for angled panels | Medium | May need build-cad-model updates |
| User confusion with angles | Medium | Clear documentation, visual examples |

---

## Open Questions

1. **Tapered panel generation**: Generate as single tapered piece or multiple rectangular pieces?
   - Proposed: Single tapered piece with TaperSpec metadata

2. **Skylight void depth**: Should void depth be automatic based on ceiling thickness?
   - Proposed: Explicit `projection_depth` required

3. **Wrap-around shelving**: How to handle shelf continuity at outside corners?
   - Proposed: Defer detailed implementation; flag for future enhancement

---

*FRD-11 ready for implementation: 2025-12-27*
