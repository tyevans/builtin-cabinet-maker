# FRD-12: Decorative Elements

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** Medium
**Depends On:** FRD-05 (Component Registry)

---

## Problem Statement

Current cabinet generation produces purely functional rectangular pieces. Real built-in cabinets feature decorative elements that transform utilitarian boxes into finished furniture: arched openings, scalloped valances, face frames, edge profiles, and molding zones. Without these, generated designs appear unfinished and lack the visual appeal of traditional cabinetry.

---

## Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Support arch top openings | 3 arch types generatable (full, segmental, elliptical) |
| Enable scalloped edge patterns | Auto-fit and explicit count modes work correctly |
| Face frame generation | Pocket screw, mortise-tenon, dowel joinery supported |
| Edge profile metadata | 6 profile types assignable to any visible edge |
| Molding zones defined | Crown, base, light rail zones affect panel dimensions |
| Cut list accuracy | All decorative specs appear in cut list metadata |

---

## Scope

### In Scope
- Arch tops: full round, segmental, elliptical
- Scalloped edges on valances, shelf fronts, aprons
- Face frames with stile/rail sizing and joinery types
- Edge profiles: chamfer, roundover, ogee, bevel, cove, roman ogee
- Crown molding nailer strips and setback
- Base molding / toe kick zone
- Light rail zone for under-cabinet lighting
- Decorative metadata in cut list output

### Out of Scope
- Actual molding profile generation (just zones/nailers)
- Carved or routed decorative panels
- Applied decorative overlays
- Curved/serpentine cabinet fronts
- Corbels and brackets

---

## Functional Requirements

### FR-01: Arch Tops

- **FR-01.1**: `arch_top` config SHALL specify: `type`, `radius` (or "auto"), `spring_height`
- **FR-01.2**: Arch types: `full_round` (semicircle), `segmental` (partial arc), `elliptical`
- **FR-01.3**: `radius: "auto"` SHALL calculate semicircle from opening width
- **FR-01.4**: Generator SHALL produce arched header piece with curve metadata
- **FR-01.5**: Side uprights SHALL be extended to meet arch at spring line
- **FR-01.6**: Arch SHALL fit between vertical dividers within a section

### FR-02: Scalloped Edges

- **FR-02.1**: `scallop` config SHALL specify: `depth`, `width`, `count` (or "auto")
- **FR-02.2**: `count: "auto"` SHALL fit whole scallops evenly across piece width
- **FR-02.3**: Applicable pieces: valances, shelf fronts, bottom aprons
- **FR-02.4**: Scallop pattern SHALL be symmetric about centerline
- **FR-02.5**: Cut list SHALL include scallop template dimensions

### FR-03: Face Frames

- **FR-03.1**: `face_frame` config SHALL specify: `stile_width`, `rail_width`, `joinery`
- **FR-03.2**: Joinery types: `pocket_screw`, `mortise_tenon`, `dowel`
- **FR-03.3**: Frame opening dimensions SHALL be calculated as frame outer minus 2x stile/rail
- **FR-03.4**: Door/drawer sizing SHALL reference frame opening (inset into frame)
- **FR-03.5**: Stiles: full cabinet height; Rails: span between stiles
- **FR-03.6**: Face frame pieces SHALL be in cut list with joinery notes

### FR-04: Edge Profiles

- **FR-04.1**: `edge_profile` config SHALL specify: `type`, `size`, `edges` (or "auto")
- **FR-04.2**: Profile types: `chamfer`, `roundover`, `ogee`, `bevel`, `cove`, `roman_ogee`
- **FR-04.3**: `edges: "auto"` SHALL apply to all front-facing visible edges
- **FR-04.4**: Explicit edge selection: `["top", "bottom", "left", "right"]`
- **FR-04.5**: Profile size/radius SHALL be validated against material thickness
- **FR-04.6**: Cut list SHALL include profile type and size per piece

### FR-05: Crown Molding Zone

- **FR-05.1**: `crown_molding` config SHALL specify: `height`, `setback`, `nailer_width`
- **FR-05.2**: Cabinet top SHALL be set back by `setback` distance
- **FR-05.3**: Nailer strip panel SHALL be generated at top back
- **FR-05.4**: Top panel depth reduced by setback amount
- **FR-05.5**: Zone height for user reference (actual molding not generated)

### FR-06: Base Molding / Toe Kick Zone

- **FR-06.1**: `base_zone` config SHALL specify: `height`, `setback`, `type`
- **FR-06.2**: Types: `toe_kick` (recessed), `base_molding` (flush with molding zone)
- **FR-06.3**: Toe kick: bottom panel raised, recessed front panel generated
- **FR-06.4**: Base molding: zone reserved, no structural changes
- **FR-06.5**: Toe kick depth typically 3-4 inches, height 3-4 inches

### FR-07: Light Rail Zone

- **FR-07.1**: `light_rail` config SHALL specify: `height`, `setback`
- **FR-07.2**: Zone at bottom of wall cabinets for lighting strip
- **FR-07.3**: Light rail strip piece generated if `generate_strip: true`
- **FR-07.4**: Zone dimensions for user reference

### FR-08: Component Registration

- **FR-08.1**: Decorative components SHALL register via `@component_registry.register()`
- **FR-08.2**: Component IDs: `decorative.arch`, `decorative.scallop`, `decorative.face_frame`, etc.
- **FR-08.3**: Components SHALL implement standard `Component` protocol

---

## Data Models

### Arch Configuration

```python
# src/cabinets/domain/components/decorative.py

from dataclasses import dataclass
from typing import Literal
from enum import Enum

class ArchType(str, Enum):
    FULL_ROUND = "full_round"
    SEGMENTAL = "segmental"
    ELLIPTICAL = "elliptical"

@dataclass(frozen=True)
class ArchConfig:
    """Configuration for arched opening."""

    arch_type: ArchType
    radius: float | Literal["auto"]
    spring_height: float = 0.0  # Height where arch begins

    def calculate_radius(self, opening_width: float) -> float:
        """Calculate actual radius from opening width."""
        if self.radius == "auto":
            return opening_width / 2  # Semicircle
        return self.radius
```

### Scallop Configuration

```python
@dataclass(frozen=True)
class ScallopConfig:
    """Configuration for scalloped edge pattern."""

    depth: float  # Scallop depth in inches
    width: float  # Single scallop width
    count: int | Literal["auto"]  # Number of scallops or auto-fit

    def calculate_count(self, piece_width: float) -> int:
        """Calculate scallop count for piece width."""
        if self.count == "auto":
            return max(1, int(piece_width / self.width))
        return self.count

    def calculate_actual_width(self, piece_width: float) -> float:
        """Calculate adjusted scallop width for even spacing."""
        count = self.calculate_count(piece_width)
        return piece_width / count
```

### Face Frame Configuration

```python
class JoineryType(str, Enum):
    POCKET_SCREW = "pocket_screw"
    MORTISE_TENON = "mortise_tenon"
    DOWEL = "dowel"

@dataclass(frozen=True)
class FaceFrameConfig:
    """Configuration for face frame construction."""

    stile_width: float = 1.5  # Vertical members
    rail_width: float = 1.5   # Horizontal members
    joinery: JoineryType = JoineryType.POCKET_SCREW
    material_thickness: float = 0.75

    def opening_width(self, frame_width: float) -> float:
        """Calculate opening width inside frame."""
        return frame_width - (2 * self.stile_width)

    def opening_height(self, frame_height: float) -> float:
        """Calculate opening height inside frame."""
        return frame_height - (2 * self.rail_width)
```

### Edge Profile Configuration

```python
class EdgeProfileType(str, Enum):
    CHAMFER = "chamfer"
    ROUNDOVER = "roundover"
    OGEE = "ogee"
    BEVEL = "bevel"
    COVE = "cove"
    ROMAN_OGEE = "roman_ogee"

@dataclass(frozen=True)
class EdgeProfileConfig:
    """Configuration for edge routing profile."""

    profile_type: EdgeProfileType
    size: float  # Radius or dimension in inches
    edges: tuple[str, ...] | Literal["auto"] = "auto"

    def get_edges(self, visible_edges: list[str]) -> list[str]:
        """Return edges to profile."""
        if self.edges == "auto":
            return visible_edges
        return list(self.edges)
```

### Molding Zone Configurations

```python
@dataclass(frozen=True)
class CrownMoldingZone:
    """Crown molding zone at cabinet top."""

    height: float = 3.0       # Zone height for molding
    setback: float = 0.75     # Top panel setback
    nailer_width: float = 2.0  # Nailer strip width

@dataclass(frozen=True)
class BaseZone:
    """Base molding or toe kick zone."""

    height: float = 3.5
    setback: float = 3.0  # Toe kick depth
    zone_type: Literal["toe_kick", "base_molding"] = "toe_kick"

@dataclass(frozen=True)
class LightRailZone:
    """Light rail zone under wall cabinets."""

    height: float = 1.5
    setback: float = 0.25
    generate_strip: bool = True
```

### Cut List Metadata Extensions

```python
@dataclass(frozen=True)
class ArchCutMetadata:
    """Cut metadata for arched pieces."""

    arch_type: ArchType
    radius: float
    spring_height: float
    opening_width: float

@dataclass(frozen=True)
class ScallopCutMetadata:
    """Cut metadata for scalloped pieces."""

    scallop_depth: float
    scallop_width: float
    scallop_count: int
    template_required: bool = True

@dataclass(frozen=True)
class EdgeProfileMetadata:
    """Cut metadata for edge profiling."""

    profile_type: EdgeProfileType
    size: float
    edges: tuple[str, ...]
    router_bit: str | None = None  # Suggested bit

@dataclass(frozen=True)
class DecorativeCutPiece:
    """Extended cut piece with decorative metadata."""

    base_piece: CutPiece
    arch: ArchCutMetadata | None = None
    scallop: ScallopCutMetadata | None = None
    edge_profile: EdgeProfileMetadata | None = None
    joinery_notes: str | None = None
```

---

## Configuration Schema Extensions

### Arch Top

```json
{
  "section": {
    "arch_top": {
      "type": "segmental",
      "radius": 12,
      "spring_height": 6
    }
  }
}
```

### Scalloped Edge

```json
{
  "valance": {
    "scallop": {
      "depth": 1.5,
      "width": 4,
      "count": "auto"
    }
  }
}
```

### Face Frame

```json
{
  "cabinet": {
    "face_frame": {
      "stile_width": 1.5,
      "rail_width": 2.0,
      "joinery": "mortise_tenon"
    }
  }
}
```

### Edge Profiles

```json
{
  "shelves": {
    "edge_profile": {
      "type": "roundover",
      "size": 0.25,
      "edges": ["front"]
    }
  }
}
```

### Molding Zones

```json
{
  "cabinet": {
    "crown_molding": {
      "height": 4,
      "setback": 1.0,
      "nailer_width": 2.5
    },
    "base_zone": {
      "type": "toe_kick",
      "height": 4,
      "setback": 3
    }
  }
}
```

---

## Technical Approach

### Arch Generation Service

```python
# src/cabinets/domain/services/arch_service.py

import math
from ..value_objects import Position
from ..entities import Panel

class ArchService:
    """Generates arched header pieces and modified uprights."""

    def generate_arch_header(
        self,
        config: ArchConfig,
        opening_width: float,
        material: MaterialSpec,
    ) -> tuple[Panel, ArchCutMetadata]:
        """Generate arched header panel with curve metadata."""
        radius = config.calculate_radius(opening_width)

        # Header height = radius + spring height
        header_height = radius + config.spring_height

        metadata = ArchCutMetadata(
            arch_type=config.arch_type,
            radius=radius,
            spring_height=config.spring_height,
            opening_width=opening_width,
        )

        # Panel dimensions for rectangular stock
        panel = Panel(
            panel_type=PanelType.ARCH_HEADER,
            width=opening_width,
            height=header_height,
            material=material,
        )

        return panel, metadata

    def calculate_upright_extension(
        self,
        config: ArchConfig,
        opening_width: float,
        upright_position: float,  # Distance from arch center
    ) -> float:
        """Calculate how much upright extends into arch area."""
        radius = config.calculate_radius(opening_width)

        if config.arch_type == ArchType.FULL_ROUND:
            # Semicircle: y = sqrt(r^2 - x^2)
            if abs(upright_position) >= radius:
                return 0
            return math.sqrt(radius**2 - upright_position**2)

        # Segmental and elliptical calculations...
        return config.spring_height
```

### Face Frame Component

```python
@component_registry.register("decorative.face_frame")
class FaceFrameComponent:
    """Generates face frame pieces for cabinet front."""

    def validate(
        self,
        config: dict[str, Any],
        context: ComponentContext
    ) -> ValidationResult:
        errors = []

        frame_config = FaceFrameConfig(**config.get("face_frame", {}))

        if frame_config.stile_width <= 0:
            errors.append("stile_width must be positive")
        if frame_config.rail_width <= 0:
            errors.append("rail_width must be positive")
        if frame_config.stile_width > context.width / 4:
            errors.append("stile_width too large for cabinet width")

        return ValidationResult(errors=tuple(errors))

    def generate(
        self,
        config: dict[str, Any],
        context: ComponentContext
    ) -> GenerationResult:
        frame_config = FaceFrameConfig(**config.get("face_frame", {}))

        pieces = []

        # Left stile (full height)
        pieces.append(CutPiece(
            width=frame_config.stile_width,
            height=context.height,
            quantity=1,
            label="Face Frame Left Stile",
            panel_type=PanelType.FACE_FRAME,
            material=MaterialSpec(frame_config.material_thickness),
        ))

        # Right stile
        pieces.append(CutPiece(
            width=frame_config.stile_width,
            height=context.height,
            quantity=1,
            label="Face Frame Right Stile",
            panel_type=PanelType.FACE_FRAME,
            material=MaterialSpec(frame_config.material_thickness),
        ))

        # Top rail (between stiles)
        rail_length = context.width - (2 * frame_config.stile_width)
        pieces.append(CutPiece(
            width=rail_length,
            height=frame_config.rail_width,
            quantity=1,
            label="Face Frame Top Rail",
            panel_type=PanelType.FACE_FRAME,
            material=MaterialSpec(frame_config.material_thickness),
        ))

        # Bottom rail
        pieces.append(CutPiece(
            width=rail_length,
            height=frame_config.rail_width,
            quantity=1,
            label="Face Frame Bottom Rail",
            panel_type=PanelType.FACE_FRAME,
            material=MaterialSpec(frame_config.material_thickness),
        ))

        return GenerationResult(cut_pieces=tuple(pieces))

    def hardware(
        self,
        config: dict[str, Any],
        context: ComponentContext
    ) -> list[HardwareItem]:
        frame_config = FaceFrameConfig(**config.get("face_frame", {}))

        if frame_config.joinery == JoineryType.POCKET_SCREW:
            return [HardwareItem(
                name="Pocket Screw 1-1/4\"",
                quantity=8,  # 2 per corner
                sku="KJ-PS-125",
            )]
        elif frame_config.joinery == JoineryType.DOWEL:
            return [HardwareItem(
                name="Dowel Pin 3/8\" x 2\"",
                quantity=8,
                sku="DP-375-2",
            )]
        return []  # Mortise-tenon needs no hardware
```

### Scallop Pattern Service

```python
class ScallopService:
    """Generates scallop pattern specifications."""

    def calculate_pattern(
        self,
        config: ScallopConfig,
        piece_width: float,
    ) -> ScallopCutMetadata:
        """Calculate scallop pattern for piece."""
        count = config.calculate_count(piece_width)
        actual_width = config.calculate_actual_width(piece_width)

        return ScallopCutMetadata(
            scallop_depth=config.depth,
            scallop_width=actual_width,
            scallop_count=count,
            template_required=True,
        )

    def generate_template_info(
        self,
        metadata: ScallopCutMetadata,
    ) -> str:
        """Generate template description for cut list."""
        return (
            f"Scallop template: {metadata.scallop_count} scallops, "
            f"{metadata.scallop_width:.2f}\" wide x "
            f"{metadata.scallop_depth:.2f}\" deep each"
        )
```

---

## File Structure

```
src/cabinets/domain/components/
    decorative.py          # Decorative components and configs

src/cabinets/domain/services/
    arch_service.py        # Arch generation logic
    scallop_service.py     # Scallop pattern calculations
    molding_zone_service.py # Zone dimension adjustments
```

---

## Validation Rules

| Rule | Check | Result |
|------|-------|--------|
| V-01 | arch.radius > 0 or "auto" | ERROR if invalid |
| V-02 | arch.radius <= opening_width/2 (for full_round) | ERROR if too large |
| V-03 | scallop.depth < material_thickness | ERROR if too deep |
| V-04 | scallop.width > 0 | ERROR if non-positive |
| V-05 | face_frame.stile_width > 0 | ERROR if non-positive |
| V-06 | face_frame.rail_width > 0 | ERROR if non-positive |
| V-07 | edge_profile.size <= material_thickness/2 | WARNING if too large |
| V-08 | crown_molding.setback > 0 | ERROR if non-positive |
| V-09 | toe_kick.height >= 3" | WARNING if too short |

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| Auto radius calculation | width=24, auto | radius=12 |
| Scallop auto count | width=48, scallop_width=6 | count=8 |
| Face frame opening | frame=48, stile=1.5 | opening=45 |
| Edge profile validation | size=1, thickness=0.75 | Warning |
| Arch upright extension | radius=12, pos=6 | ~10.39" |
| Toe kick panel gen | height=4, setback=3 | Panel generated |

### Integration Tests

- Cabinet with face frame generates all stile/rail pieces
- Arch top section produces arch header in cut list
- Crown zone reduces top panel depth correctly
- Edge profiles appear in cut list metadata
- Scalloped valance includes template info

---

## Implementation Phases

### Phase 1: Data Models (Est. 0.5 day)
- [ ] Add `ArchType`, `JoineryType`, `EdgeProfileType` enums
- [ ] Create config dataclasses
- [ ] Add `PanelType.FACE_FRAME`, `PanelType.ARCH_HEADER` to enum
- [ ] Create cut metadata dataclasses

### Phase 2: Face Frames (Est. 1 day)
- [ ] Implement `FaceFrameConfig` with opening calculations
- [ ] Register `decorative.face_frame` component
- [ ] Generate stile and rail pieces
- [ ] Include joinery hardware

### Phase 3: Edge Profiles (Est. 0.5 day)
- [ ] Implement `EdgeProfileConfig`
- [ ] Add profile metadata to cut pieces
- [ ] Auto-detect visible edges logic
- [ ] Validation for profile size vs thickness

### Phase 4: Arch Tops (Est. 1.5 days)
- [ ] Implement `ArchService` with curve calculations
- [ ] Register `decorative.arch` component
- [ ] Generate arch header panels
- [ ] Calculate upright extensions
- [ ] Arch metadata in cut list

### Phase 5: Scalloped Edges (Est. 1 day)
- [ ] Implement `ScallopService`
- [ ] Auto-fit count calculation
- [ ] Pattern symmetry logic
- [ ] Template info generation

### Phase 6: Molding Zones (Est. 1 day)
- [ ] Implement `CrownMoldingZone` with nailer generation
- [ ] Implement `BaseZone` with toe kick panel
- [ ] Implement `LightRailZone`
- [ ] Update panel dimension calculations

### Phase 7: Integration (Est. 0.5 day)
- [ ] Update config schema
- [ ] Integration tests
- [ ] Cut list output formatting

---

## Dependencies & Risks

### Dependencies
- FRD-05: Component registry for `@component_registry.register()`
- FRD-01: Configuration schema for JSON config format
- Existing `Panel`, `CutPiece`, `MaterialSpec` value objects
- FRD-07 (Doors): Face frame affects door sizing

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Arch curve math complexity | Medium | Use well-tested math formulas |
| Face frame/door coordination | High | Clear opening calculation API |
| Scallop template accuracy | Low | Template info only, user cuts |
| Zone dimension conflicts | Medium | Validate zone heights don't exceed cabinet |

---

## Open Questions

1. **Intermediate rails**: Should face frames support horizontal intermediate rails (between drawers)?
   - Proposed: Yes, add `intermediate_rails: [{position: 24, width: 1.5}]`

2. **Edge profile combinations**: Allow different profiles on different edges of same piece?
   - Proposed: No for v1; single profile per piece

3. **Arch STL generation**: Generate curved geometry or rectangular bounding box?
   - Proposed: Rectangular in STL; arch curve is cut metadata only

---

*FRD-12 ready for implementation: 2025-12-27*
