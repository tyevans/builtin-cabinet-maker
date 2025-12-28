# Built-in Cabinet and Shelving Generator System

**Date Created:** 2025-12-27
**Last Updated:** 2025-12-27
**Author/Agent:** FRD Builder Agent
**Status:** In Progress - Problem Statement Complete

---

## Table of Contents

1. [Problem Statement](#problem-statement) - COMPLETE
2. [Goals & Success Criteria](#goals--success-criteria) - COMPLETE
3. [Scope & Boundaries](#scope--boundaries) - COMPLETE
4. [User Stories / Use Cases](#user-stories--use-cases) - COMPLETE
5. [Functional Requirements](#functional-requirements) - COMPLETE
6. [Technical Approach](#technical-approach) - COMPLETE
7. [Architecture & Integration Considerations](#architecture--integration-considerations) - COMPLETE
8. [Data Models & Schema Changes](#data-models--schema-changes) - COMPLETE
9. [UI/UX Considerations](#uiux-considerations) - COMPLETE
10. [Security & Privacy Considerations](#security--privacy-considerations) - COMPLETE
11. [Testing Strategy](#testing-strategy) - COMPLETE
12. [Implementation Phases](#implementation-phases) - COMPLETE
13. [Dependencies & Risks](#dependencies--risks) - COMPLETE
14. [Open Questions](#open-questions) - COMPLETE
15. [Status](#status)

---

## Problem Statement

### Current State

The existing codebase provides a foundational cabinet generation system with the following capabilities:

**Existing Architecture (Clean Layered Design):**
- **Domain Layer** (`src/cabinets/domain/`): Core entities (`Cabinet`, `Panel`, `Section`, `Shelf`, `Wall`), value objects (`Dimensions`, `Position`, `MaterialSpec`, `CutPiece`, `BoundingBox3D`), and domain services (`LayoutCalculator`, `CutListGenerator`, `MaterialEstimator`, `Panel3DMapper`)
- **Application Layer** (`src/cabinets/application/`): Commands (`GenerateLayoutCommand`) and DTOs (`WallInput`, `LayoutParametersInput`, `LayoutOutput`)
- **Infrastructure Layer** (`src/cabinets/infrastructure/`): STL export (`StlExporter`, `StlMeshBuilder`) and formatters (`CutListFormatter`, `LayoutDiagramFormatter`, `MaterialReportFormatter`, `JsonExporter`)
- **CLI Layer** (`src/cabinets/cli/`): Typer-based CLI with commands for `generate`, `cutlist`, `materials`, and `diagram`

**Current Capabilities:**
- Generate simple rectangular cabinets with evenly-spaced sections and shelves
- Basic material specification (thickness, type: plywood/MDF/particle board/solid wood)
- Cut list generation with quantity consolidation
- Material estimation with waste factor calculation
- STL mesh export for 3D visualization
- JSON export of layout data
- ASCII diagram output

**Current Limitations:**

1. **Single-Wall, Simple Geometry Only**: The system can only generate cabinets against a single flat wall with rectangular dimensions. Real-world built-ins frequently wrap around corners, accommodate angles, and work within complex room geometries.

2. **No Spatial Awareness**: No ability to define or work around obstacles such as windows, skylights, doors, electrical outlets, or existing fixtures. Built-in furniture must integrate with the room's architectural features.

3. **Uniform Section Distribution**: All sections are evenly sized with identical shelf counts. Real cabinetry requires variable section widths, different storage configurations per section, and mixed-use zones (e.g., cabinet section next to open shelving).

4. **Missing Component Types**: The system generates only basic box construction (panels, shelves, dividers). Professional built-ins require:
   - Doors (hinged, sliding, barn-style)
   - Drawers with proper hardware allowances
   - Specialty cabinets (corner units, lazy susans)
   - Decorative elements (arches, scallops, bevels)
   - Hardware and accessory integration (pegboard, lighting, electrical)

5. **No Material Optimization**: Cut list generation exists but lacks bin packing algorithms to optimize material usage and minimize waste across multiple sheet goods.

6. **CLI Parameter Limitations**: All configuration must be passed as command-line arguments. Complex configurations with dozens of parameters become unwieldy. No JSON configuration file input.

7. **Missing Woodworking Intelligence**: The system treats all panels as simple rectangular sheets without consideration for:
   - Joinery requirements (dado, rabbet, pocket screws, dowels)
   - Grain direction for solid wood and plywood
   - Edge banding requirements
   - Structural reinforcement needs
   - Professional finishing details

8. **No Infrastructure Routing**: Built-in furniture often must accommodate lighting (under-cabinet, in-cabinet, accent), electrical outlets within cabinets, and cable management. The system has no concept of routing or placement for these elements.

### User Pain Points

**Hobbyist Woodworkers and DIYers:**
- Spend hours manually calculating dimensions for built-ins that wrap around room features
- Struggle to optimize sheet good purchases and minimize expensive waste
- Lack confidence that their designs will be structurally sound
- Cannot easily visualize how components fit together before cutting

**Professional Cabinet Makers:**
- Need to rapidly iterate on designs for client approval
- Require production-ready cut lists with proper joinery allowances
- Must accommodate complex room geometries that clients present
- Need material lists for accurate quoting

**Interior Designers and Architects:**
- Want to quickly prototype built-in solutions for clients
- Need accurate 3D models for presentations
- Must ensure designs respect architectural constraints (windows, HVAC, structural elements)

### Business/Technical Drivers

1. **Market Gap**: Existing cabinet design software is either prohibitively expensive (professional CAD), overly simplistic (basic calculators), or focused on manufactured/modular systems rather than custom built-ins.

2. **Configuration-First Architecture**: A JSON-based configuration contract enables:
   - Version-controlled design files
   - Reproducible builds
   - Template libraries and sharing
   - Future GUI development without core logic changes
   - Integration with other tools and pipelines

3. **Voxel/Slot-Based Flexibility**: A flexible spatial system allows modeling arbitrary geometries while maintaining the discrete, manufacturable nature of cabinet components.

### Evidence from Codebase

The existing architecture demonstrates a well-structured foundation:

```python
# Current domain model shows clean separation (src/cabinets/domain/entities.py)
@dataclass
class Cabinet:
    width: float
    height: float
    depth: float
    material: MaterialSpec
    back_material: MaterialSpec | None = None
    sections: list[Section] = field(default_factory=list)
```

```python
# Current CLI shows need for configuration files (src/cabinets/cli/main.py)
# All parameters are CLI options - becomes unwieldy for complex configurations
@app.command()
def generate(
    width: Annotated[float, typer.Option("--width", "-w", ...)],
    height: Annotated[float, typer.Option("--height", "-h", ...)],
    depth: Annotated[float, typer.Option("--depth", "-d", ...)],
    sections: Annotated[int, typer.Option("--sections", "-s", ...)] = 1,
    ...
)
```

The clean domain model with value objects (`MaterialSpec`, `CutPiece`, `BoundingBox3D`) and services (`Panel3DMapper`, `MaterialEstimator`) provides a solid foundation to extend with the required capabilities.

---

## Goals & Success Criteria

### Primary Goals

#### G1: JSON Configuration Contract as Primary Interface
Enable complex cabinet and shelving designs to be fully specified through JSON configuration files, making CLI parameters secondary to file-based configuration.

**Success Criteria:**
- SC-G1.1: Any design achievable through CLI can be expressed in JSON configuration
- SC-G1.2: JSON schema provides validation with clear error messages for invalid configurations
- SC-G1.3: Configuration files can be loaded, validated, and processed in under 2 seconds for typical designs
- SC-G1.4: JSON schema is documented and versioned, with migration support for schema changes
- SC-G1.5: Example configuration templates provided for common use cases (bookshelf, closet organizer, entertainment center, corner cabinet)

#### G2: Complex Room Geometry Support
Support built-in furniture that wraps around corners, accommodates non-rectangular walls, and works within real-world room constraints.

**Success Criteria:**
- SC-G2.1: System can generate cabinets that wrap around 90-degree inside corners (L-shaped configurations)
- SC-G2.2: System can handle outside corners (convex room shapes)
- SC-G2.3: Support for angled walls (non-90-degree corners)
- SC-G2.4: Sloped ceiling accommodation with automatic height adjustment
- SC-G2.5: Generated corner solutions are structurally sound and aesthetically coherent

#### G3: Obstacle and Feature Integration
Allow users to define room features (windows, skylights, doors, outlets) and have the system automatically work around them.

**Success Criteria:**
- SC-G3.1: Window definitions create automatic voids in cabinet design with configurable clearance
- SC-G3.2: Skylight accommodation for angled ceiling installations
- SC-G3.3: Built-in desk integration with proper ergonomic heights and cable management zones
- SC-G3.4: Outlet and switch positions are respected with required clearance zones
- SC-G3.5: Feature avoidance generates clean, usable adjacent cabinet sections

#### G4: Complete Component Library
Provide a comprehensive set of cabinet components that can be mixed and matched to create professional-quality built-ins.

**Success Criteria:**
- SC-G4.1: Door types available: hinged (overlay, inset, partial overlay), sliding, barn door
- SC-G4.2: Drawer generation with proper hardware clearances for standard drawer slides
- SC-G4.3: Corner cabinet solutions: lazy susan, diagonal front, blind corner
- SC-G4.4: Shelf variations: fixed, adjustable (with pin hole placement), glass with wood trim
- SC-G4.5: Cubby/slot system with configurable vertical and horizontal dividers
- SC-G4.6: Specialty sections: pegboard, wine rack, pull-out trays
- SC-G4.7: Each component can be independently styled/swapped without affecting adjacent components

#### G5: Decorative Elements and Finishing
Support professional finishing details and decorative elements that elevate designs from utilitarian to beautiful.

**Success Criteria:**
- SC-G5.1: Arch tops available for cabinet openings with configurable radius
- SC-G5.2: Scallop patterns for shelf edges and valances
- SC-G5.3: Bevel and chamfer options for edges and face frames
- SC-G5.4: Crown molding and base molding integration zones defined
- SC-G5.5: Face frame construction supported with proper proportions
- SC-G5.6: Edge banding requirements automatically calculated for visible edges

#### G6: Infrastructure Integration
Allow built-ins to accommodate modern electrical and lighting requirements.

**Success Criteria:**
- SC-G6.1: Under-cabinet lighting channels can be specified with wire routing paths
- SC-G6.2: In-cabinet lighting placement (LED strips, puck lights) with switch locations
- SC-G6.3: Electrical outlet positions within cabinets with required clearances
- SC-G6.4: Cable management channels for entertainment center applications
- SC-G6.5: Cut list includes holes/notches required for wire routing

#### G7: Production-Ready Output Generation
Generate outputs that can be directly used for material purchasing and construction.

**Success Criteria:**
- SC-G7.1: Cut lists include all necessary details: dimensions, quantity, material, grain direction, edge treatments
- SC-G7.2: Bin packing optimization reduces material waste by at least 15% compared to naive layout
- SC-G7.3: Materials list includes hardware (hinges, slides, screws) with quantities
- SC-G7.4: STL export produces manifold meshes suitable for CNC or 3D printing visualization
- SC-G7.5: Assembly instructions or diagrams generated showing build sequence
- SC-G7.6: Joinery specifications included where applicable (dado depths, rabbet dimensions)

#### G8: Woodworking Quality Standards
Ensure generated plans follow professional woodworking best practices.

**Success Criteria:**
- SC-G8.1: Grain direction recommendations for plywood and solid wood components
- SC-G8.2: Structural span calculations warn when shelves exceed safe unsupported lengths
- SC-G8.3: Joinery type recommendations based on component relationships and loads
- SC-G8.4: Standard reveal and gap tolerances configurable (default to professional standards)
- SC-G8.5: Weight-bearing capacity estimates for shelves based on material and span

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Configuration expressiveness | 100% of supported features configurable via JSON | Feature parity testing |
| Corner wrap generation accuracy | All generated corner joints are structurally valid | Geometric validation tests |
| Obstacle avoidance correctness | Zero overlaps between cabinet geometry and defined obstacles | Collision detection tests |
| Material waste reduction | 15%+ improvement over naive cut list | Bin packing benchmarks |
| Cut list accuracy | All pieces manufacturable as specified | Manual review of sample outputs |
| Generation time | < 5 seconds for complex configurations | Performance benchmarks |
| STL validity | 100% manifold meshes | Mesh validation tools |

### Definition of Done

A feature area is considered complete when:
1. All success criteria for that goal are met
2. Unit tests cover core logic with >80% coverage
3. Integration tests validate end-to-end workflows
4. JSON schema updated if new configuration options added
5. Example configurations demonstrate the feature
6. Generated outputs have been manually verified for correctness

---

## Scope & Boundaries

### In Scope

#### Phase 1: Foundation (MVP)

**JSON Configuration System:**
- JSON schema definition for cabinet configurations
- CLI command to load and validate configuration files
- Schema versioning system
- Basic template library (simple bookshelf, basic cabinet)

**Enhanced Spatial Model:**
- Multi-wall room definition (connected wall segments)
- 90-degree inside corner wrapping
- Variable-width sections within a single cabinet run
- Window and door obstacle definitions with clearance zones

**Extended Component Types:**
- Hinged doors (overlay style)
- Fixed shelves with configurable positions
- Basic drawer boxes (single size)
- Vertical dividers within sections

**Improved Output:**
- Enhanced cut list with edge treatment flags
- Basic bin packing for single sheet size
- Improved STL export with component separation

#### Phase 2: Professional Features

**Advanced Geometry:**
- Outside corners (convex configurations)
- Angled walls (non-90-degree)
- Sloped ceiling accommodation
- Skylight voids

**Complete Component Library:**
- Sliding doors and barn doors
- Inset and partial overlay doors
- Multiple drawer sizes with slide clearances
- Adjustable shelf pin hole placement
- Corner cabinet types (lazy susan, blind corner, diagonal)
- Glass panel shelves with wood trim

**Decorative Elements:**
- Arch tops for openings
- Scalloped edges
- Face frame generation
- Crown and base molding integration zones
- Edge profiles (bevel, chamfer, roundover)

**Infrastructure:**
- Lighting channel definitions
- Electrical routing zones
- Cable management paths

#### Phase 3: Production Optimization

**Advanced Material Optimization:**
- Multi-sheet bin packing with grain direction
- Multiple material type optimization
- Kerf allowance in cut calculations
- Offcut tracking and reuse suggestions

**Woodworking Intelligence:**
- Joinery type selection (dado, rabbet, pocket, dowel)
- Structural span warnings
- Grain direction recommendations
- Weight capacity estimates
- Hardware specification and quantity calculation

**Enhanced Output Formats:**
- DXF export for CNC
- Assembly sequence diagrams
- Step-by-step build instructions
- Bill of materials with pricing estimates

### Out of Scope

The following are explicitly NOT part of this system:

**Live Editing / GUI:**
- No graphical user interface for design manipulation
- No real-time 3D preview during editing
- No drag-and-drop component placement
- Future GUI development is enabled by the JSON contract but not included

**Manufacturing Integration:**
- No direct CNC machine control or G-code generation
- No integration with specific CAM software
- No automated ordering from material suppliers

**Advanced Furniture Types:**
- Freestanding furniture (tables, chairs, beds)
- Furniture with complex mechanical systems (murphy beds, lift mechanisms)
- Upholstered components
- Metal or mixed-material construction (wood only)

**Structural Engineering:**
- No load-bearing wall integration calculations
- No seismic or building code compliance verification
- No professional engineering stamps or certifications
- System provides recommendations, not structural guarantees

**Finish Specifications:**
- No paint/stain color management
- No finish material quantity calculations
- No surface preparation instructions

**Room Scanning / Import:**
- No 3D room scanning integration
- No import from architectural CAD formats (DWG, Revit)
- No photo-based room measurement

**Collaboration Features:**
- No multi-user editing
- No cloud storage or sync
- No version control integration (beyond file-based)
- No commenting or review workflows

### Boundary Conditions

**Maximum Supported Dimensions:**
- Wall length: Up to 40 feet (480 inches) per segment
- Cabinet height: Up to 12 feet (144 inches)
- Cabinet depth: Up to 36 inches
- Number of connected wall segments: Up to 8
- Sections per wall run: Up to 20
- Total components per project: Up to 500

**Supported Materials:**
- Sheet goods: Plywood, MDF, particle board, melamine
- Solid wood: Configurable species with standard thicknesses
- Standard thicknesses: 1/4", 3/8", 1/2", 5/8", 3/4", 1"
- Sheet sizes: 4x8', 5x5', custom sizes

**Hardware Assumptions:**
- Standard 32mm system compatibility
- Common drawer slide sizes (12"-24" in 2" increments)
- Standard European hinge boring
- US standard electrical box sizes

### Related Features (Separate Concerns)

The following features may be valuable but should be separate projects/documents:

- **Template Marketplace**: Sharing and discovering configuration templates
- **Pricing Calculator**: Integration with lumber/hardware pricing APIs
- **AR Visualization**: Viewing generated designs in physical space
- **Collaborative Design Review**: Multi-user feedback on designs
- **Machine Learning Optimization**: AI-assisted design suggestions

---

## User Stories / Use Cases

### User Personas

**DIY Homeowner (Dana)**
- Comfortable with woodworking basics but not a professional
- Has a table saw, miter saw, and basic hand tools
- Wants to build custom built-ins that fit their space perfectly
- Prioritizes clear instructions and accurate cut lists
- Budget-conscious, wants to minimize material waste

**Professional Cabinet Maker (Carlos)**
- Builds custom cabinetry for clients as primary income
- Has a full shop with CNC capability
- Needs rapid design iteration for client approval
- Requires production-ready outputs
- Values accuracy and professional-grade joinery

**Interior Designer (Iris)**
- Designs spaces for clients, doesn't build herself
- Needs to communicate design intent to builders
- Wants professional visualizations for client presentations
- Must ensure designs are buildable within budget

### User Stories

#### Configuration and Setup

**US-001: Load Configuration from File**
> As Dana (DIY), I want to load my cabinet design from a JSON file so that I can save my work and make incremental changes without re-entering all parameters.

Acceptance Criteria:
- CLI accepts `--config` flag with path to JSON file
- Invalid JSON produces clear error messages with line numbers
- Configuration values override CLI defaults
- Partial configurations allowed (missing values use defaults)

**US-002: Validate Configuration Before Generation**
> As Carlos (Professional), I want to validate my configuration file without generating output so that I can quickly check for errors during design iteration.

Acceptance Criteria:
- CLI `validate` command checks configuration without generating
- All validation errors reported (not just first)
- Warnings for suboptimal configurations (e.g., unsupported shelf spans)
- Exit code indicates pass/fail for scripting

**US-003: Use Configuration Templates**
> As Dana (DIY), I want to start from a template configuration so that I don't have to learn all options before creating my first design.

Acceptance Criteria:
- CLI `templates` command lists available templates
- CLI `init --template <name>` creates configuration from template
- Templates include comments explaining each option
- Templates cover common use cases (bookshelf, closet, entertainment center)

#### Room Definition

**US-004: Define Multi-Wall Room Layout**
> As Carlos (Professional), I want to define a room with multiple connected walls so that I can generate built-ins that wrap around corners.

Acceptance Criteria:
- Configuration supports array of wall segments with lengths and angles
- Walls can be connected at inside corners (L-shape, U-shape)
- System validates wall connections are geometrically valid
- Error if walls would create impossible geometry

**US-005: Define Obstacles in Room**
> As Dana (DIY), I want to mark where my windows and doors are so that the cabinet design works around them automatically.

Acceptance Criteria:
- Obstacles defined with position, size, and clearance requirements
- Types: window, door, outlet, switch, vent, custom
- System prevents cabinet components from overlapping obstacles
- Adjacent sections sized appropriately around obstacles

**US-006: Handle Sloped Ceilings**
> As Dana (DIY), I want to specify that my attic room has a sloped ceiling so that the cabinets fit properly under the slope.

Acceptance Criteria:
- Ceiling slope defined as angle and starting height
- Cabinet sections automatically adjust height to fit
- Sections that would be too short are flagged as warnings
- Multiple slope directions supported (dormer situations)

#### Component Design

**US-007: Create Variable-Width Sections**
> As Carlos (Professional), I want to specify exact widths for each section so that I can create designs with purpose-built storage zones.

Acceptance Criteria:
- Each section can have explicit width or use "fill" for remaining space
- Minimum/maximum width constraints supported
- Divider thickness accounted for automatically
- Error if specified widths exceed available space

**US-008: Add Doors to Sections**
> As Iris (Designer), I want to specify which sections have doors and what style so that I can create a cohesive design aesthetic.

Acceptance Criteria:
- Door type per section: none, single, double, sliding
- Door style: overlay, inset, partial overlay
- Hardware specification: hinge type, handle style
- Door reveal configurable (gap around door)

**US-009: Add Drawers to Sections**
> As Carlos (Professional), I want to add drawer stacks to sections with proper hardware clearances so that the drawers will function correctly when built.

Acceptance Criteria:
- Drawers defined by height with automatic quantity calculation
- Drawer slide type affects required clearances
- Drawer box dimensions account for slide mounting
- Front sizing accounts for overlay/inset style

**US-010: Configure Shelf Positions**
> As Dana (DIY), I want to specify exact shelf positions so that I can fit specific items (books, equipment, etc.).

Acceptance Criteria:
- Shelves positioned by distance from bottom or top
- Adjustable shelf option generates pin hole patterns
- Fixed shelf option includes dado joint specifications
- Shelf depth can differ from cabinet depth (setback)

**US-011: Create Cubby Grid Layout**
> As Iris (Designer), I want to divide a section into a grid of cubbies so that I can create visually interesting storage.

Acceptance Criteria:
- Grid defined by rows and columns
- Individual cubby dimensions calculated automatically
- Divider thickness accounted for
- Non-uniform grids supported (different row heights)

**US-012: Design Corner Cabinets**
> As Carlos (Professional), I want to choose from corner cabinet solutions so that corner space is usable and accessible.

Acceptance Criteria:
- Corner types: lazy susan, blind corner, diagonal front
- Lazy susan specifies tray diameter and count
- Blind corner specifies accessible section width
- Generated geometry handles the corner connection

#### Decorative Elements

**US-013: Add Arch Tops to Openings**
> As Iris (Designer), I want to specify arch tops for cabinet openings so that I can add visual interest to the design.

Acceptance Criteria:
- Arch radius configurable per opening
- Arch can be partial (segment) or full semicircle
- Cut list includes arch pieces with proper dimensions
- STL export renders arches correctly

**US-014: Add Scalloped Edges**
> As Iris (Designer), I want to add scalloped valances and shelf edges so that I can create a traditional aesthetic.

Acceptance Criteria:
- Scallop pattern: depth, width, spacing configurable
- Applicable to: valances, shelf fronts, aprons
- Cut list includes profile information
- Pattern scales to fit piece width

**US-015: Specify Edge Treatments**
> As Carlos (Professional), I want to specify edge banding and profiles for each piece so that the cut list includes finishing requirements.

Acceptance Criteria:
- Edge treatment per side: none, banding, profile (chamfer, roundover, ogee)
- Visible vs. hidden edges automatically identified
- Edge banding quantity calculated
- Profile dimensions included in cut list

#### Infrastructure Integration

**US-016: Plan Lighting Placement**
> As Carlos (Professional), I want to specify under-cabinet and in-cabinet lighting so that I can include routing in the design.

Acceptance Criteria:
- Lighting zones defined with type (LED strip, puck, etc.)
- Wire routing paths calculated
- Access holes included in cut list
- Switch locations can be specified

**US-017: Accommodate Electrical Outlets**
> As Dana (DIY), I want to include outlets inside cabinets for charging devices so that I have proper clearance and wire routing.

Acceptance Criteria:
- Outlet box locations defined with standard US sizes
- Required clearances maintained around outlets
- Back panel holes included in cut list
- Conduit paths can be specified

#### Output Generation

**US-018: Generate Optimized Cut List**
> As Dana (DIY), I want a cut list that optimizes material usage so that I don't waste expensive plywood.

Acceptance Criteria:
- Bin packing algorithm arranges cuts on sheet goods
- Grain direction respected for plywood
- Visual diagram shows cut layout per sheet
- Waste percentage reported

**US-019: Generate Hardware List**
> As Carlos (Professional), I want a complete hardware list so that I can quote jobs accurately.

Acceptance Criteria:
- All fasteners quantified (screws, dowels, etc.)
- Hinges counted with specific type
- Drawer slides counted with length
- Shelf pins counted for adjustable shelves

**US-020: Export 3D Model**
> As Iris (Designer), I want to export a 3D model for client visualization so that I can present designs professionally.

Acceptance Criteria:
- STL export produces valid manifold mesh
- Components can be exported separately or combined
- Model scale is accurate (1 unit = 1 inch)
- Export suitable for rendering software import

**US-021: Generate Assembly Instructions**
> As Dana (DIY), I want assembly instructions so that I know the order to build the cabinet.

Acceptance Criteria:
- Step-by-step assembly sequence
- Identifies which pieces connect where
- Specifies joinery for each connection
- Includes diagrams or references to pieces

### Edge Cases and Error Conditions

**EC-001: Section Too Narrow for Door**
- If a section width is less than minimum for specified door type, generate warning and suggest alternatives

**EC-002: Shelf Span Exceeds Safe Limits**
- If shelf width exceeds recommended unsupported span for material, generate warning with support recommendations

**EC-003: Drawer in Corner Section**
- If drawers specified in a corner cabinet section, validate drawer can open without interference

**EC-004: Obstacle Blocks Entire Wall**
- If obstacles prevent any cabinet placement on a wall segment, generate error with clear explanation

**EC-005: Conflicting Specifications**
- If user specifies both explicit section widths and fill sections that cannot be reconciled, generate error explaining the conflict

**EC-006: Material Insufficient**
- If cut list requires more material than practical (e.g., 50 sheets), generate warning suggesting design review

---

## Functional Requirements

Requirements are organized by functional area and prioritized as:
- **Must Have (M)**: Required for MVP, blocks release if missing
- **Should Have (S)**: Important for professional use, target for Phase 2
- **Nice to Have (N)**: Enhances experience, can be deferred

### CLI Interface Requirements

**FR-CLI-001 (M)**: Configuration File Loading
- The CLI SHALL accept a `--config` or `-c` flag specifying a JSON configuration file path
- The CLI SHALL support both absolute and relative paths
- If the file does not exist, the CLI SHALL exit with error code 1 and a descriptive message

**FR-CLI-002 (M)**: Configuration Validation Command
- The CLI SHALL provide a `validate` command that checks configuration without generating output
- Validation SHALL report all errors found, not just the first
- Validation SHALL distinguish between errors (blocking) and warnings (advisory)
- Exit code SHALL be 0 for valid, 1 for errors, 2 for warnings only

**FR-CLI-003 (M)**: Template Management Commands
- The CLI SHALL provide a `templates list` command showing available templates
- The CLI SHALL provide a `templates init <name> [--output <path>]` command to create new config from template
- Templates SHALL be bundled with the package installation

**FR-CLI-004 (M)**: Generation Command Enhancement
- The existing `generate` command SHALL accept `--config` for file-based configuration
- CLI parameters SHALL override config file values when both provided
- The `--output-dir` flag SHALL specify directory for all generated files

**FR-CLI-005 (S)**: Batch Processing
- The CLI SHALL support processing multiple configuration files in one invocation
- Batch mode SHALL continue on error for individual files (unless `--fail-fast` specified)
- Batch mode SHALL produce summary of successes and failures

### Configuration Schema Requirements

**FR-CFG-001 (M)**: Schema Version
- Every configuration file SHALL include a `schema_version` field
- The system SHALL reject configurations with unsupported schema versions
- The system SHALL provide migration guidance for outdated schemas

**FR-CFG-002 (M)**: Room Definition Schema
- Configuration SHALL support a `room` object containing:
  - `walls`: Array of wall segment definitions
  - `obstacles`: Array of obstacle definitions
  - `ceiling`: Ceiling configuration (flat or sloped)

**FR-CFG-003 (M)**: Wall Segment Schema
- Each wall segment SHALL include:
  - `length`: Length in inches (required)
  - `height`: Default height in inches (required)
  - `angle`: Angle relative to previous wall in degrees (default: 0 for continuation, 90 for corner)
  - `depth`: Default cabinet depth for this wall (optional, overrides global)

**FR-CFG-004 (M)**: Obstacle Schema
- Each obstacle SHALL include:
  - `type`: Enum (window, door, outlet, switch, vent, skylight, custom)
  - `wall_index`: Which wall the obstacle is on
  - `position`: Distance from wall start
  - `width`: Obstacle width
  - `height`: Obstacle height
  - `bottom`: Distance from floor to bottom of obstacle
  - `clearance`: Required clearance around obstacle (default by type)

**FR-CFG-005 (M)**: Cabinet Definition Schema
- Configuration SHALL support a `cabinet` object containing:
  - `depth`: Default depth in inches
  - `material`: Material specification
  - `back_material`: Back panel material
  - `sections`: Array of section definitions

**FR-CFG-006 (M)**: Section Definition Schema
- Each section SHALL include:
  - `width`: Explicit width OR "fill" for automatic sizing
  - `type`: Section type (open, doored, drawers, corner, cubby)
  - `shelves`: Array of shelf definitions OR shelf count for even distribution
  - `doors`: Door configuration (if applicable)
  - `drawers`: Drawer configuration (if applicable)

**FR-CFG-007 (S)**: Style System Schema
- Configuration SHALL support a `styles` object for reusable component definitions
- Styles SHALL be referenceable by name from component definitions
- Built-in styles SHALL be provided for common configurations

**FR-CFG-008 (S)**: Decorative Elements Schema
- Configuration SHALL support decorative elements including:
  - `arches`: Arch top configurations
  - `scallops`: Scallop pattern definitions
  - `moldings`: Crown and base molding zones
  - `edge_profiles`: Edge treatment definitions

### Spatial Geometry Requirements

**FR-GEO-001 (M)**: Multi-Wall Layout Generation
- The system SHALL generate cabinet layouts spanning multiple connected walls
- Wall connections SHALL support angles from 45 to 315 degrees
- The system SHALL validate that wall configurations form valid geometry

**FR-GEO-002 (M)**: Inside Corner Handling
- For 90-degree inside corners, the system SHALL generate one of:
  - Butted cabinets (one cabinet ends, other begins at corner)
  - Continuous wrap (cabinet wraps around corner as single unit)
  - Corner unit (specialized corner cabinet at junction)
- Corner handling method SHALL be configurable

**FR-GEO-003 (S)**: Outside Corner Handling
- For convex corners, the system SHALL support:
  - Angled face (45-degree front panel)
  - Butted cabinets with filler
  - Open corner with wrap-around shelving

**FR-GEO-004 (S)**: Sloped Ceiling Accommodation
- The system SHALL calculate maximum cabinet height at each position based on ceiling slope
- Sections SHALL automatically adjust height when ceiling restricts
- The system SHALL warn when sections become too short for practical use (< 12")

**FR-GEO-005 (M)**: Obstacle Avoidance
- The system SHALL NOT generate cabinet components that overlap defined obstacles
- The system SHALL maintain required clearances around obstacles
- Cabinet sections adjacent to obstacles SHALL size appropriately
- The system SHALL report when obstacles prevent reasonable cabinet placement

**FR-GEO-006 (S)**: Skylight Integration
- Skylights SHALL be defined with position, size, and projection angle
- The system SHALL calculate void area at cabinet depth
- Cabinet tops SHALL be notched or shaped to accommodate skylight projection

### Component Generation Requirements

**FR-CMP-001 (M)**: Basic Cabinet Box
- The system SHALL generate standard cabinet boxes with:
  - Top, bottom, left side, right side panels
  - Back panel (configurable material)
  - Proper joinery allowances based on configuration

**FR-CMP-002 (M)**: Fixed Shelves
- Fixed shelves SHALL be positioned at explicit heights or evenly distributed
- Shelf depth SHALL be configurable (default: cabinet depth - 1")
- Shelf edges SHALL be flagged for edge treatment

**FR-CMP-003 (S)**: Adjustable Shelves
- Adjustable shelf configurations SHALL generate:
  - Shelf pieces at specified quantity
  - Pin hole patterns on side panels (32mm system or custom)
  - Shelf pin hardware requirements

**FR-CMP-004 (M)**: Vertical Dividers
- Dividers SHALL be positioned at section boundaries
- Divider dadoes SHALL be calculated for fixed dividers
- Divider depth SHALL match shelf depth configuration

**FR-CMP-005 (S)**: Hinged Doors
- Door configurations SHALL include:
  - Style: overlay, inset, partial overlay
  - Count: single, double (pair)
  - Opening direction: left, right (per door for pairs)
- Door dimensions SHALL account for reveals and overlay amounts
- Hinge boring locations SHALL be calculated (32mm system)

**FR-CMP-006 (S)**: Sliding Doors
- Sliding door configurations SHALL include:
  - Track type: top-mount, bottom-mount, bypass
  - Number of panels
  - Panel overlap amount
- Track hardware requirements SHALL be calculated

**FR-CMP-007 (S)**: Barn Doors
- Barn door configurations SHALL include:
  - Door style (panel pattern)
  - Track length requirement
  - Hardware specification
- Track mounting zone SHALL be identified

**FR-CMP-008 (S)**: Drawer Boxes
- Drawer configurations SHALL include:
  - Height per drawer or count with automatic sizing
  - Slide type and required clearances
  - Front style: overlay, inset
- Drawer box dimensions SHALL calculate from slide clearances
- Bottom panel material SHALL be configurable

**FR-CMP-009 (S)**: Corner Cabinet: Lazy Susan
- Lazy susan configurations SHALL include:
  - Tray diameter (or auto-calculate from cabinet size)
  - Number of trays
  - Door style (single door, bi-fold)
- Door hinge points SHALL account for rotation clearance

**FR-CMP-010 (S)**: Corner Cabinet: Blind Corner
- Blind corner configurations SHALL include:
  - Accessible section width
  - Filler panel width on blind side
- Pull-out hardware requirements SHALL be specified if applicable

**FR-CMP-011 (S)**: Corner Cabinet: Diagonal
- Diagonal front configurations SHALL calculate:
  - Angled face panel dimensions
  - Side panel angles
  - Shelf shapes for diagonal interior

**FR-CMP-012 (S)**: Cubby Grid
- Cubby configurations SHALL include:
  - Rows and columns count OR explicit cell dimensions
  - Whether dimensions are uniform or variable
- All divider pieces SHALL be generated with proper dimensions
- Dadoes for divider intersections SHALL be calculated

**FR-CMP-013 (N)**: Specialty Sections
- The system SHALL support specialty section types:
  - Pegboard back (pegboard dimensions and mounting)
  - Wine rack (X-divider grid calculation)
  - Pull-out tray (tray and slide specifications)

### Decorative Element Requirements

**FR-DEC-001 (S)**: Arch Tops
- Arch configurations SHALL include:
  - Radius (or "auto" for semicircle based on width)
  - Arch type: full round, segmental, elliptical
- Cut list SHALL include arch piece with radius specification
- 3D model SHALL render arch geometry correctly

**FR-DEC-002 (S)**: Scalloped Edges
- Scallop configurations SHALL include:
  - Scallop depth, width, and count (or "auto-fit")
  - Edge selection: top, bottom, front
- Pattern SHALL scale to fit piece width evenly
- Cut list SHALL include scallop profile specification

**FR-DEC-003 (S)**: Edge Profiles
- Edge profile configurations SHALL support:
  - Types: chamfer, roundover, ogee, bevel, square
  - Size/radius for the profile
  - Which edges receive the profile
- System SHALL auto-identify visible edges if not explicit

**FR-DEC-004 (S)**: Face Frames
- Face frame configurations SHALL include:
  - Stile width (vertical members)
  - Rail width (horizontal members)
  - Joinery type (pocket screw, mortise-tenon, dowel)
- Frame pieces SHALL be added to cut list
- Frame offsets SHALL adjust door/drawer sizing

**FR-DEC-005 (N)**: Molding Integration Zones
- Configuration SHALL define molding zones:
  - Crown molding area at top
  - Base molding area at bottom
  - Light rail for under-cabinet lighting
- Zones SHALL affect panel dimensions (nailers, clearances)

### Infrastructure Integration Requirements

**FR-INF-001 (S)**: Lighting Channels
- Lighting configurations SHALL include:
  - Type: LED strip, puck light, rope light
  - Location: under-cabinet, in-cabinet, accent
  - Power source location
- Wire routing paths SHALL be calculated
- Access holes SHALL be added to cut list

**FR-INF-002 (S)**: Electrical Outlets
- Outlet configurations SHALL include:
  - Box type and dimensions (US standard sizes)
  - Location: back panel, side panel, inside cabinet
  - Circuit routing indication
- Required clearances SHALL be maintained
- Panel cutouts SHALL be added to cut list

**FR-INF-003 (N)**: Cable Management
- Cable management configurations SHALL include:
  - Grommet locations and sizes
  - Cable channel paths
  - Access panel locations
- Cut list SHALL include routing holes

### Output Generation Requirements

**FR-OUT-001 (M)**: Enhanced Cut List
- Cut list SHALL include for each piece:
  - Dimensions (width x height)
  - Quantity
  - Material type and thickness
  - Grain direction recommendation
  - Edge treatments (per edge)
  - Joinery requirements (dadoes, rabbets, holes)

**FR-OUT-002 (S)**: Bin Packing Optimization
- System SHALL optimize cut layout across sheet goods
- Optimization SHALL respect:
  - Grain direction constraints
  - Saw kerf allowance (configurable, default 1/8")
  - Edge allowance for panel edges
- System SHALL output:
  - Visual cut diagram per sheet
  - Waste percentage
  - Offcut inventory (reusable pieces)

**FR-OUT-003 (S)**: Hardware List
- System SHALL generate hardware requirements:
  - Screws by type, size, and quantity
  - Hinges by type and count
  - Drawer slides by size and count
  - Shelf pins by count
  - Handles/knobs by count
  - Specialty hardware (lazy susan hardware, etc.)

**FR-OUT-004 (M)**: STL Export Enhancement
- STL export SHALL produce manifold (watertight) meshes
- Export options SHALL include:
  - Combined (all components in one file)
  - Separated (one file per component)
  - Assembly groups (logical groupings)
- Scale SHALL be configurable (default: 1 unit = 1 inch)

**FR-OUT-005 (S)**: JSON Output Enhancement
- JSON output SHALL include:
  - Complete configuration used
  - All calculated dimensions
  - All generated pieces with positions
  - Validation warnings
- JSON SHALL be suitable for import into other tools

**FR-OUT-006 (N)**: Assembly Sequence
- System SHALL generate assembly order recommendations
- Order SHALL account for:
  - Structural dependencies
  - Practical access considerations
  - Joinery sequence requirements

**FR-OUT-007 (N)**: DXF Export
- System SHALL export 2D DXF files for:
  - Individual panels (for CNC cutting)
  - Cut layout diagrams
  - Joinery locations

### Woodworking Quality Requirements

**FR-WW-001 (M)**: Span Validation
- System SHALL warn when shelf span exceeds recommendations:
  - 3/4" plywood: 36" max unsupported
  - 3/4" MDF: 24" max unsupported
  - Recommendations SHALL be configurable
- Warnings SHALL suggest adding support/dividers

**FR-WW-002 (S)**: Grain Direction
- System SHALL recommend grain direction for:
  - Plywood: Face grain direction
  - Solid wood: Grain parallel to length
- Cut list SHALL indicate grain direction per piece
- Bin packing SHALL respect grain constraints

**FR-WW-003 (S)**: Joinery Specifications
- System SHALL calculate joinery dimensions:
  - Dado depth (1/3 to 1/2 material thickness)
  - Rabbet depth and width
  - Pocket hole locations
  - Dowel positions
- Specifications SHALL be included in cut list notes

**FR-WW-004 (S)**: Reveal and Tolerance Standards
- System SHALL apply standard reveals:
  - Door reveal: 1/8" default (configurable)
  - Drawer reveal: 1/8" default (configurable)
  - Inset gap: 1/16" per side default
- Tolerances SHALL be adjustable for different skill levels

**FR-WW-005 (N)**: Weight Capacity Estimation
- System SHALL estimate shelf weight capacity based on:
  - Material type and thickness
  - Span width
  - Support configuration
- Estimates SHALL be advisory (not engineered)

---

## Technical Approach

### High-Level Strategy

The system will be built as a **configuration-driven generator** following these principles:

1. **Configuration as Code**: JSON configurations are the canonical representation of designs, enabling version control, reproducibility, and tooling integration.

2. **Voxel-Inspired Spatial Model**: Room space is modeled as a flexible grid of potential cabinet "slots" that can be filled, merged, or left empty based on obstacles and design intent.

3. **Component Composition**: Complex cabinets are built from simple, well-defined components (panels, shelves, doors) that are combined through a clean composition model.

4. **Domain-Driven Design**: Core logic lives in the domain layer with no dependencies on infrastructure, enabling easy testing and future UI integration.

5. **Progressive Enhancement**: The existing simple cabinet generation continues to work; new features are additive.

### Technology Stack

**Core Language:** Python 3.13+
- Existing codebase foundation
- Strong typing with dataclasses and type hints
- Clean Architecture patterns already established

**CLI Framework:** Typer (existing)
- Already integrated for current CLI
- Rich terminal output support
- Automatic help generation

**3D Geometry:**
- **numpy-stl** (existing): STL mesh generation
- **numpy**: Numerical calculations for geometry
- Consider **cadquery** or **build123d** for complex 3D operations if needed

**Configuration:**
- **Pydantic v2**: JSON schema validation, serialization, settings management
- **JSON Schema**: Export for documentation and external tool integration

**Bin Packing:**
- **rectpack**: 2D bin packing algorithms (pip installable)
- Custom wrapper for grain direction and kerf constraints

**Output Formats:**
- **ezdxf**: DXF file generation for CNC
- **jinja2**: Template-based text output (assembly instructions, reports)

### Core Algorithms

#### Voxel/Slot-Based Spatial Model

The room space is divided into a flexible grid where:

```
Room Definition -> Wall Segments -> Slot Grid -> Component Placement
```

1. **Wall segments** define the linear extents available for cabinets
2. **Obstacles** mark slots as unavailable
3. **Sections** claim contiguous ranges of slots
4. **Components** are generated to fill section volumes

This model allows:
- Easy obstacle avoidance (mark slots as blocked)
- Flexible section sizing (merge adjacent slots)
- Corner handling (slots at wall junctions have special rules)
- Sloped ceiling (slot heights vary along the run)

#### Corner Resolution Algorithm

For inside corners:
```
1. Identify corner junction between wall segments
2. Determine corner handling strategy (butt, wrap, or corner unit)
3. If butted: Generate separate cabinets terminating at corner
4. If wrapped: Calculate continuous panel that spans corner
5. If corner unit: Insert specialized corner cabinet, adjust adjacent sections
```

#### Obstacle Avoidance Algorithm

```
1. Map obstacles to slot ranges on each wall
2. Mark affected slots with obstacle clearance requirements
3. During section generation:
   a. Sections cannot span blocked slots
   b. Section heights adjust at obstacle boundaries
   c. Partial-height sections generated for window undersills
```

#### Bin Packing for Cut Optimization

Using guillotine cutting pattern (required for panel saws):

```
1. Group pieces by material type and thickness
2. Sort pieces by area (largest first) with secondary sort by dimension
3. For each sheet:
   a. Apply first-fit decreasing algorithm
   b. Respect grain direction constraints
   c. Add kerf allowance between pieces
4. Calculate waste percentage and generate cut diagrams
```

### Key Design Patterns

#### Configuration Pipeline

```
JSON File -> Pydantic Model (validation) -> Domain Objects -> Generation -> Output
```

The configuration is transformed through stages:
1. **Load**: Raw JSON to Pydantic configuration model
2. **Validate**: Schema validation, cross-field validation, warnings
3. **Transform**: Configuration to domain entities (Wall, Cabinet, Section)
4. **Generate**: Domain services produce panels, cut lists, 3D geometry
5. **Export**: Results to various output formats

#### Component Registry Pattern

Components (door types, shelf styles, decorative elements) are registered in a component registry:

```python
@component_registry.register("door.hinged.overlay")
class OverlayDoorComponent:
    def validate(self, config: DoorConfig, context: SectionContext) -> list[str]
    def generate(self, config: DoorConfig, context: SectionContext) -> list[Panel]
    def hardware(self, config: DoorConfig, context: SectionContext) -> list[Hardware]
```

Benefits:
- Easy to add new component types
- Consistent interface for all components
- Style swapping is a configuration change

#### Visitor Pattern for Output Generation

Different outputs (cut list, STL, hardware list) are generated by visitors that traverse the component tree:

```python
class CabinetVisitor(Protocol):
    def visit_cabinet(self, cabinet: Cabinet) -> None
    def visit_section(self, section: Section) -> None
    def visit_panel(self, panel: Panel) -> None
    def visit_door(self, door: Door) -> None
```

This allows adding new output formats without modifying component classes.

### Existing Code Integration

The current codebase provides a solid foundation:

**Keep and Extend:**
- `Cabinet`, `Section`, `Panel`, `Shelf` entities - extend with new attributes
- `MaterialSpec`, `CutPiece` value objects - enhance with new fields
- `Panel3DMapper`, `StlExporter` - extend for new geometry types
- `LayoutCalculator` - refactor into strategy pattern for different layout modes
- CLI structure - add new commands alongside existing

**Refactor:**
- `Wall` entity - expand to `WallSegment` with angle/connection support
- `LayoutParameters` - replace with full configuration model
- Command/DTO pattern - expand for new operations

**Add:**
- Room model (walls + obstacles + ceiling)
- Configuration loading and validation layer
- Component registry and component implementations
- Bin packing service
- Hardware calculation service

### Performance Considerations

**Target Performance:**
- Simple configuration (single wall, 5 sections): < 1 second
- Complex configuration (3 walls, 20 sections, obstacles): < 5 seconds
- Bin packing for 50+ pieces: < 10 seconds

**Optimization Strategies:**
- Lazy computation: Only calculate what's needed for requested output
- Caching: Memoize geometric calculations within a generation run
- Efficient data structures: Use numpy arrays for bulk geometry operations

### Error Handling Strategy

**Validation Errors (blocking):**
- Invalid configuration syntax
- Missing required fields
- Impossible geometry (overlapping sections, negative dimensions)
- Constraint violations (sections exceed wall length)

**Warnings (advisory):**
- Suboptimal design (shelf spans, narrow sections)
- Material waste above threshold
- Missing optional fields that affect quality

**Error Reporting:**
- All errors collected before returning (not fail-fast during validation)
- Clear error messages with configuration path (e.g., "sections[2].shelves[0].height")
- Suggestions for resolution where possible

---

## Architecture & Integration Considerations

### System Architecture Overview

The system follows a Clean Architecture pattern with distinct layers:

```
+------------------------------------------------------------------+
|                         CLI Layer                                  |
|  (Typer commands, argument parsing, output formatting)             |
+------------------------------------------------------------------+
                                |
+------------------------------------------------------------------+
|                     Application Layer                              |
|  (Commands, DTOs, Orchestration, Configuration Loading)            |
+------------------------------------------------------------------+
                                |
+------------------------------------------------------------------+
|                       Domain Layer                                 |
|  (Entities, Value Objects, Domain Services, Business Rules)        |
+------------------------------------------------------------------+
                                |
+------------------------------------------------------------------+
|                   Infrastructure Layer                             |
|  (File I/O, STL Export, DXF Export, External Libraries)           |
+------------------------------------------------------------------+
```

### Layer Responsibilities

#### CLI Layer (`src/cabinets/cli/`)

**Current State:**
- `main.py`: Typer app with `generate`, `cutlist`, `materials`, `diagram` commands

**Extended Responsibilities:**
- Parse command-line arguments and flags
- Load configuration files (delegate to Application layer)
- Format output for terminal display
- Handle exit codes and error display
- Progress indication for long operations

**New Commands:**
```
cabinets validate <config>     # Validate configuration
cabinets templates list        # List available templates
cabinets templates init <name> # Create from template
cabinets generate --config <file> [options]  # Generate with config
cabinets batch <config1> <config2> ...       # Batch processing
```

#### Application Layer (`src/cabinets/application/`)

**Current State:**
- `commands.py`: `GenerateLayoutCommand` orchestrating generation
- `dtos.py`: Input/Output DTOs (`WallInput`, `LayoutParametersInput`, `LayoutOutput`)

**Extended Responsibilities:**
- Configuration loading and transformation
- Schema validation orchestration
- Command orchestration for all operations
- DTO definitions for new features

**New Components:**
```python
# commands.py additions
class LoadConfigurationCommand:
    """Load and validate JSON configuration."""

class ValidateConfigurationCommand:
    """Validate without generating."""

class GenerateFromConfigCommand:
    """Generate layout from configuration file."""

class BatchGenerateCommand:
    """Process multiple configurations."""

# configuration.py (new)
class ConfigurationLoader:
    """Load JSON configuration files."""

class ConfigurationValidator:
    """Validate configuration against schema."""

class ConfigurationTransformer:
    """Transform config to domain objects."""
```

#### Domain Layer (`src/cabinets/domain/`)

**Current State:**
- `entities.py`: `Cabinet`, `Section`, `Panel`, `Shelf`, `Wall`
- `value_objects.py`: `Dimensions`, `Position`, `MaterialSpec`, `CutPiece`, `BoundingBox3D`
- `services.py`: `LayoutCalculator`, `CutListGenerator`, `MaterialEstimator`, `Panel3DMapper`

**Extended Responsibilities:**
- Core business logic for all cabinet generation
- Component definitions and generation
- Spatial calculations and geometry
- Woodworking rules and validations

**New Domain Model Components:**
```python
# entities.py additions
class Room:
    """Room containing walls, obstacles, ceiling."""
    walls: list[WallSegment]
    obstacles: list[Obstacle]
    ceiling: Ceiling

class WallSegment:
    """Wall segment with connection info."""
    length: float
    height: float
    angle_from_previous: float

class Obstacle:
    """Obstacle blocking cabinet placement."""
    type: ObstacleType
    bounds: BoundingBox2D
    clearance: Clearance

class Door:
    """Door component for a section."""

class Drawer:
    """Drawer component for a section."""

class CornerUnit:
    """Specialized corner cabinet."""

# services.py additions
class RoomLayoutService:
    """Calculate cabinet layout within room geometry."""

class ObstacleAvoidanceService:
    """Handle obstacle intersection detection."""

class CornerResolutionService:
    """Determine corner handling strategy."""

class ComponentFactory:
    """Create components from configuration."""
```

#### Infrastructure Layer (`src/cabinets/infrastructure/`)

**Current State:**
- `stl_exporter.py`: `StlExporter`, `StlMeshBuilder`
- `exporters.py`: `CutListFormatter`, `LayoutDiagramFormatter`, `MaterialReportFormatter`, `JsonExporter`

**Extended Responsibilities:**
- File system operations
- External library integrations
- Output format generation
- Template file management

**New Infrastructure Components:**
```python
# bin_packing.py (new)
class BinPackingService:
    """Optimize cut list layout on sheet goods."""

class CutDiagramRenderer:
    """Generate visual cut diagrams."""

# dxf_exporter.py (new)
class DxfExporter:
    """Export DXF files for CNC."""

# hardware.py (new)
class HardwareCalculator:
    """Calculate hardware requirements."""

# templates.py (new)
class TemplateManager:
    """Manage configuration templates."""
```

### Component Architecture

#### Component Registry System

A registry pattern enables extensible component types:

```python
# domain/components/registry.py
class ComponentRegistry:
    _components: dict[str, type[Component]] = {}

    @classmethod
    def register(cls, component_id: str):
        def decorator(component_class):
            cls._components[component_id] = component_class
            return component_class
        return decorator

    @classmethod
    def get(cls, component_id: str) -> type[Component]:
        return cls._components[component_id]

# domain/components/base.py
class Component(Protocol):
    def validate(self, config: dict, context: ComponentContext) -> ValidationResult
    def generate(self, config: dict, context: ComponentContext) -> GenerationResult
    def hardware(self, config: dict, context: ComponentContext) -> list[HardwareItem]

# domain/components/doors.py
@ComponentRegistry.register("door.hinged.overlay")
class OverlayHingedDoor(Component):
    ...

@ComponentRegistry.register("door.barn")
class BarnDoor(Component):
    ...
```

#### Configuration Schema Architecture

Using Pydantic for robust validation:

```python
# application/schema/base.py
class BaseConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')

class VersionedConfig(BaseConfig):
    schema_version: str = Field(..., pattern=r'^\d+\.\d+$')

# application/schema/room.py
class WallSegmentConfig(BaseConfig):
    length: float = Field(..., gt=0, le=480)
    height: float = Field(..., gt=0, le=144)
    angle: float = Field(default=0, ge=-180, le=180)

class ObstacleConfig(BaseConfig):
    type: ObstacleType
    wall_index: int = Field(..., ge=0)
    position: float = Field(..., ge=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    bottom: float = Field(default=0, ge=0)
    clearance: float = Field(default=2.0)

# application/schema/cabinet.py
class CabinetConfig(VersionedConfig):
    room: RoomConfig
    cabinet: CabinetDefinitionConfig
    styles: dict[str, StyleConfig] = {}
    output: OutputConfig = OutputConfig()
```

### Data Flow Architecture

```
User Request
     |
     v
+--------------------+
| CLI Command Parser |
+--------------------+
     |
     v
+------------------------+
| Configuration Loader   | <-- JSON File
+------------------------+
     |
     v
+------------------------+
| Schema Validator       | --> Validation Errors/Warnings
| (Pydantic)            |
+------------------------+
     |
     v
+------------------------+
| Config Transformer     |
| (to Domain Objects)    |
+------------------------+
     |
     v
+------------------------+
| Room Layout Service    |
| - Wall processing      |
| - Obstacle mapping     |
| - Slot grid creation   |
+------------------------+
     |
     v
+------------------------+
| Section Generator      |
| - Component factory    |
| - Panel generation     |
| - Hardware calculation |
+------------------------+
     |
     v
+------------------------+
| Output Generators      |
| - Cut List            |
| - STL Export          |
| - Hardware List       |
| - Bin Packing         |
+------------------------+
     |
     v
Output Files / Terminal
```

### API Contracts

#### Configuration File Contract

The JSON configuration file is the primary API:

```json
{
  "schema_version": "1.0",
  "room": {
    "walls": [
      {"length": 120, "height": 96, "angle": 0},
      {"length": 84, "height": 96, "angle": 90}
    ],
    "obstacles": [
      {"type": "window", "wall_index": 0, "position": 30, "width": 36, "height": 48, "bottom": 36}
    ],
    "ceiling": {"type": "flat"}
  },
  "cabinet": {
    "depth": 12,
    "material": {"type": "plywood", "thickness": 0.75},
    "sections": [
      {"width": 24, "type": "open", "shelves": 3},
      {"width": "fill", "type": "doored", "door": {"style": "overlay"}}
    ]
  },
  "output": {
    "formats": ["cutlist", "stl", "hardware"],
    "stl_options": {"combined": true}
  }
}
```

#### CLI Contract

```bash
# Configuration-based generation
cabinets generate --config design.json --output-dir ./output

# Validation only
cabinets validate design.json

# Template operations
cabinets templates list
cabinets templates init bookshelf --output my-bookshelf.json

# Batch processing
cabinets batch project/*.json --output-dir ./builds
```

### Integration Points

#### External Tools Integration

**Future GUI Development:**
- JSON contract enables any GUI to generate configurations
- Real-time validation API could be exposed
- Preview generation through same pipeline

**CNC/CAM Integration:**
- DXF export for direct CNC import
- Cut diagram SVG/PDF for manual reference

**3D Visualization:**
- STL export compatible with any 3D viewer
- Component-separated export for exploded views

#### Extensibility Points

**Adding New Component Types:**
1. Create component class implementing `Component` protocol
2. Register with `ComponentRegistry`
3. Define Pydantic config schema
4. Component automatically available in configurations

**Adding New Output Formats:**
1. Create exporter implementing export interface
2. Register in output format registry
3. Add CLI option for format

**Adding New Validation Rules:**
1. Add validator to appropriate Pydantic model
2. Or add domain service validation rule

---

## Data Models & Schema Changes

### JSON Configuration Schema

The complete JSON schema for cabinet configurations. This serves as the contract between users and the system.

#### Root Schema (v1.0)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Cabinet Configuration",
  "type": "object",
  "required": ["schema_version", "room", "cabinet"],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+$",
      "description": "Schema version (major.minor)"
    },
    "room": { "$ref": "#/definitions/room" },
    "cabinet": { "$ref": "#/definitions/cabinet" },
    "styles": { "$ref": "#/definitions/styles" },
    "output": { "$ref": "#/definitions/output" }
  }
}
```

#### Room Definition

```json
{
  "room": {
    "walls": [
      {
        "length": 120,
        "height": 96,
        "angle": 0,
        "depth_override": null
      },
      {
        "length": 84,
        "height": 96,
        "angle": 90
      }
    ],
    "obstacles": [
      {
        "type": "window",
        "wall_index": 0,
        "position": 30,
        "width": 36,
        "height": 48,
        "bottom": 36,
        "clearance": 2
      }
    ],
    "ceiling": {
      "type": "sloped",
      "slope_angle": 30,
      "slope_start_height": 72,
      "slope_direction": "away_from_wall"
    }
  }
}
```

#### Cabinet Definition

```json
{
  "cabinet": {
    "depth": 12,
    "material": {
      "type": "plywood",
      "thickness": 0.75,
      "species": "birch"
    },
    "back_material": {
      "type": "plywood",
      "thickness": 0.25
    },
    "construction": {
      "joinery": "dado",
      "face_frame": false,
      "edge_banding": "visible_edges"
    },
    "sections": [
      {
        "width": 24,
        "type": "open",
        "shelves": {
          "count": 4,
          "adjustable": true,
          "setback": 1
        }
      },
      {
        "width": "fill",
        "type": "doored",
        "door": {
          "style": "overlay",
          "count": 2,
          "hardware": "european_hinge"
        },
        "shelves": [
          {"position": 24, "from": "bottom"},
          {"position": 48, "from": "bottom"}
        ]
      },
      {
        "width": 18,
        "type": "drawers",
        "drawers": [
          {"height": 6, "slide": "soft_close_full"},
          {"height": 6, "slide": "soft_close_full"},
          {"height": 8, "slide": "soft_close_full"}
        ]
      }
    ],
    "corner_handling": "lazy_susan",
    "decorative": {
      "top_treatment": "crown_molding_zone",
      "base_treatment": "toe_kick"
    }
  }
}
```

#### Styles Definition

```json
{
  "styles": {
    "modern_door": {
      "type": "door",
      "style": "overlay",
      "overlay_amount": 0.5,
      "reveal": 0.125,
      "edge_profile": "square"
    },
    "glass_shelf": {
      "type": "shelf",
      "material": "glass",
      "thickness": 0.25,
      "frame": {
        "material": "solid_wood",
        "width": 1.5
      }
    }
  }
}
```

#### Output Configuration

```json
{
  "output": {
    "formats": ["cutlist", "stl", "hardware", "diagram"],
    "cutlist_options": {
      "include_joinery": true,
      "grain_direction": true,
      "edge_treatments": true
    },
    "stl_options": {
      "mode": "combined",
      "scale": 1.0,
      "include_hardware": false
    },
    "bin_packing": {
      "enabled": true,
      "sheet_size": {"width": 48, "height": 96},
      "kerf": 0.125,
      "edge_allowance": 0.5
    }
  }
}
```

### Domain Model Extensions

#### New Value Objects

```python
@dataclass(frozen=True)
class Angle:
    """Angle in degrees."""
    degrees: float

    def __post_init__(self):
        if not -180 <= self.degrees <= 180:
            raise ValueError("Angle must be between -180 and 180 degrees")

    @property
    def radians(self) -> float:
        return math.radians(self.degrees)

@dataclass(frozen=True)
class Clearance:
    """Clearance requirements around an obstacle."""
    top: float = 0
    bottom: float = 0
    left: float = 0
    right: float = 0

@dataclass(frozen=True)
class EdgeTreatment:
    """Edge treatment specification."""
    type: EdgeType  # none, banding, chamfer, roundover, ogee
    size: float = 0  # profile size if applicable

@dataclass(frozen=True)
class JoinerySpec:
    """Joinery specification for a connection."""
    type: JoineryType  # dado, rabbet, pocket, dowel, biscuit
    depth: float
    width: float | None = None
    positions: list[float] | None = None  # for pocket/dowel
```

#### Extended Entity Attributes

```python
@dataclass
class Panel:
    # Existing
    panel_type: PanelType
    width: float
    height: float
    material: MaterialSpec
    position: Position

    # New
    grain_direction: GrainDirection = GrainDirection.LENGTH
    edges: dict[Edge, EdgeTreatment] = field(default_factory=dict)
    joinery: list[JoinerySpec] = field(default_factory=list)
    label: str = ""
    notes: list[str] = field(default_factory=list)

@dataclass
class Section:
    # Existing
    width: float
    height: float
    depth: float
    position: Position
    shelves: list[Shelf]

    # New
    section_type: SectionType = SectionType.OPEN
    doors: list[Door] = field(default_factory=list)
    drawers: list[Drawer] = field(default_factory=list)
    style_ref: str | None = None
    decorative: DecorativeConfig | None = None
```

### Database/Persistence

The system does not use a database. All data is:
- **Input**: JSON configuration files
- **Output**: Generated files (STL, cut list, etc.)
- **Templates**: Bundled JSON files in package

No migration or schema versioning is needed beyond the configuration schema version.

---

## UI/UX Considerations

### CLI User Experience

Since the primary interface is CLI with JSON configuration, UX focuses on:

#### Command Discovery

```bash
$ cabinets --help

Built-in Cabinet and Shelving Generator

Commands:
  generate   Generate cabinet layout from configuration
  validate   Validate configuration file
  templates  Manage configuration templates
  cutlist    Display cut list only
  materials  Display material estimate only
  diagram    Display ASCII diagram only

Use 'cabinets <command> --help' for more information.
```

#### Error Messages

Errors must be clear, actionable, and include context:

```
$ cabinets validate bad-config.json

Validation Errors:
  - room.walls[1].angle: Value 270 exceeds maximum of 180
  - cabinet.sections[0].width: Cannot be negative (-12)
  - cabinet.sections[2].door.style: Unknown style 'overlayed' (did you mean 'overlay'?)

Validation Warnings:
  - cabinet.sections[1].shelves[0]: Shelf span of 42" exceeds recommended 36" for 3/4" plywood.
    Consider adding a center divider.

Run 'cabinets generate --help' for usage information.
```

#### Progress Indication

For longer operations, provide feedback:

```
$ cabinets generate --config complex-design.json --output-dir ./build

Loading configuration... done
Validating... done (2 warnings)
Generating layout...
  - Processing wall 1/3... done
  - Processing wall 2/3... done
  - Processing wall 3/3... done
  - Resolving corners... done
  - Generating components (47 pieces)... done
Optimizing cut layout... done (12% waste)
Exporting...
  - Cut list... ./build/cutlist.txt
  - STL model... ./build/cabinet.stl
  - Hardware list... ./build/hardware.txt

Generation complete. 2 warnings.
```

#### Output Formatting

**Cut List (Terminal):**
```
CUT LIST - Modern Bookshelf
================================================================================
Piece                 Width      Height     Qty   Material      Grain   Edges
--------------------------------------------------------------------------------
Top Panel             48.000     11.250     1     3/4" Ply      W       F:band
Bottom Panel          48.000     11.250     1     3/4" Ply      W       F:band
Left Side             11.250     72.000     1     3/4" Ply      H       F:band
Right Side            11.250     72.000     1     3/4" Ply      H       F:band
Back Panel            48.000     72.000     1     1/4" Ply      -       none
Shelf                 46.500     10.500     4     3/4" Ply      W       F:band
Divider               10.500     70.500     2     3/4" Ply      H       none
--------------------------------------------------------------------------------
Total: 11 pieces | 31.2 sq ft | Recommended: 2 sheets 4x8 (18% waste)

Notes:
  - Grain: W=width, H=height
  - Edges: F=front, B=back, L=left, R=right
  - All shelves require 1/4" dado, 3/8" deep
```

### JSON Configuration Authoring

#### Templates as Learning Tool

Templates include extensive comments to guide users:

```json
{
  // Configuration schema version - do not modify
  "schema_version": "1.0",

  // Room definition - describe the space for your built-in
  "room": {
    // Walls are listed in order, connected at corners
    // First wall starts at origin, subsequent walls connect at specified angle
    "walls": [
      {
        "length": 96,      // Wall length in inches
        "height": 84,      // Floor to ceiling (or desired cabinet height)
        "angle": 0         // 0 = continues straight, 90 = turns right (inside corner)
      }
    ],

    // Obstacles the cabinet must work around
    "obstacles": [
      // Example: window
      // {
      //   "type": "window",
      //   "wall_index": 0,      // Which wall (0-indexed)
      //   "position": 24,       // Distance from wall start
      //   "width": 36,
      //   "height": 48,
      //   "bottom": 36,         // Height of window sill from floor
      //   "clearance": 2        // Required gap around window
      // }
    ]
  },

  // Cabinet specification
  "cabinet": {
    "depth": 12,           // How deep the cabinet projects from wall

    // Material for main cabinet body
    "material": {
      "type": "plywood",   // plywood, mdf, particle_board, solid_wood
      "thickness": 0.75    // Standard 3/4"
    },

    // Sections from left to right
    "sections": [
      {
        "width": 24,       // Fixed width, or "fill" to use remaining space
        "type": "open",    // open, doored, drawers, cubby
        "shelves": 3       // Number of evenly-spaced shelves
      }
    ]
  }
}
```

#### Schema Documentation

Export JSON Schema for IDE integration:

```bash
$ cabinets schema export > cabinet-schema.json
```

Users can then configure VSCode/other editors for autocomplete and validation.

### Visualization

#### ASCII Diagrams (Terminal)

For quick visual verification without leaving terminal:

```
FRONT VIEW
+--------------------------------------------------+
|                      TOP                          |
+----------+-------------------+-------------------+
|          |                   |    [DRAWER]       |
|   SIDE   |                   +-------------------+
|          |       OPEN        |    [DRAWER]       |
|          |      SECTION      +-------------------+
|          |                   |    [DRAWER]       |
+----------+-------------------+-------------------+
                  96" wide x 84" tall
```

#### STL for 3D Visualization

Users can view STL files in:
- Online viewers (ViewSTL.com, etc.)
- Installed viewers (MeshLab, Windows 3D Viewer)
- CAD software for further manipulation

### Error Prevention

#### Validation Before Generation

Always validate, providing fix suggestions:

```
$ cabinets validate my-design.json

Checking configuration...

Issues found:

ERROR: cabinet.sections total width (128") exceeds wall length (120")
  Suggestion: Reduce section widths or use "fill" for automatic sizing

WARNING: cabinet.sections[1].shelves[0] span is 36" (at limit for 3/4" plywood)
  Suggestion: This will work but may sag under heavy load. Consider adding a center support.

WARNING: room.obstacles[0] (window) leaves only 8" for cabinet section
  Suggestion: Section will be very narrow. Consider adjusting design.

2 errors, 2 warnings
```

#### Reasonable Defaults

When values are omitted, use sensible defaults from woodworking best practices:

- Material thickness: 3/4" plywood
- Back material: 1/4" plywood
- Shelf setback: 1" from front
- Door reveal: 1/8"
- Dado depth: 1/3 material thickness
- Kerf allowance: 1/8"

---

## Security & Privacy Considerations

### Threat Model

As a local CLI tool processing user-provided configuration files, the security surface is minimal but not zero.

#### Input Validation Security

**Threat:** Malicious JSON configuration files
**Mitigation:**
- Strict schema validation using Pydantic
- No code execution from configuration (no eval, no template injection)
- Limit maximum values to prevent resource exhaustion
- Sanitize all strings before use in file paths or outputs

**Implementation:**
```python
# Pydantic handles type coercion safely
# Additional guards for path-related fields
class OutputConfig(BaseModel):
    output_dir: Path

    @field_validator('output_dir')
    def validate_path(cls, v):
        # Prevent path traversal
        resolved = v.resolve()
        if '..' in str(v):
            raise ValueError("Path traversal not allowed")
        return resolved
```

#### File System Security

**Threat:** Unauthorized file access or overwrite
**Mitigation:**
- Only write to explicitly specified output directory
- Never overwrite without user consent (or --force flag)
- Validate output paths don't escape intended directory
- Use safe file handling practices

**Implementation:**
```python
def safe_write(filepath: Path, content: bytes, force: bool = False) -> None:
    if filepath.exists() and not force:
        raise FileExistsError(f"{filepath} exists. Use --force to overwrite.")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(content)
```

#### Resource Exhaustion

**Threat:** Denial of service through extreme configurations
**Mitigation:**
- Maximum limits on all dimensions (wall length, section count, etc.)
- Maximum total piece count (500 pieces)
- Timeout for generation operations (configurable, default 5 minutes)
- Memory limits through reasonable maximum mesh complexity

### Privacy Considerations

**Data Handling:**
- No telemetry or usage tracking
- No network access required for core functionality
- All processing is local
- Configuration files may contain personal information (room dimensions could reveal home layout)

**Recommendations for Users:**
- Keep configuration files in private repositories
- Do not share configurations that reveal sensitive home details
- Consider .gitignore for output files that contain room dimensions

### Dependency Security

**Third-Party Libraries:**
- Use pinned dependency versions in pyproject.toml
- Regular security audits of dependencies (dependabot/renovate)
- Prefer well-maintained, widely-used libraries

**Current Dependencies (security relevant):**
- `pydantic`: Well-maintained, security-conscious design
- `numpy`: Widely used, regularly updated
- `numpy-stl`: Limited functionality, low attack surface
- `typer`: CLI parsing only, minimal attack surface

### Code Security Practices

- No use of `eval()`, `exec()`, or dynamic code execution
- No shell command construction from user input
- Type hints throughout for static analysis
- Input validation at system boundaries

---

## Testing Strategy

### Testing Pyramid

```
                    /\
                   /  \
                  / E2E \        <- Few, high-value end-to-end tests
                 /______\
                /        \
               /Integration\     <- API boundary tests
              /______________\
             /                \
            /    Unit Tests    \  <- Many, fast, isolated tests
           /____________________\
```

### Unit Testing

**Target Coverage:** 80%+ for domain layer, 70%+ overall

**Domain Layer Tests (`tests/unit/domain/`):**
- Value object validation and behavior
- Entity creation and business logic
- Service calculations and algorithms

```python
# Example: test_value_objects.py
def test_dimensions_validates_positive():
    with pytest.raises(ValueError, match="positive"):
        Dimensions(width=-10, height=20, depth=12)

def test_material_spec_standard_3_4():
    spec = MaterialSpec.standard_3_4()
    assert spec.thickness == 0.75
    assert spec.material_type == MaterialType.PLYWOOD

# Example: test_services.py
def test_layout_calculator_sections_fit():
    wall = Wall(width=48, height=84, depth=12)
    params = LayoutParameters(num_sections=3)
    calc = LayoutCalculator()

    cabinet = calc.generate_cabinet(wall, params)

    total_width = sum(s.width for s in cabinet.sections)
    assert total_width <= cabinet.interior_width
```

**Application Layer Tests (`tests/unit/application/`):**
- Command execution logic
- DTO validation
- Configuration transformation

```python
# Example: test_configuration.py
def test_config_loader_valid_json():
    loader = ConfigurationLoader()
    config = loader.load(Path("fixtures/valid-config.json"))
    assert config.schema_version == "1.0"

def test_config_validator_reports_all_errors():
    validator = ConfigurationValidator()
    invalid_config = {...}  # Multiple errors

    result = validator.validate(invalid_config)

    assert len(result.errors) == 3  # All errors found
```

### Integration Testing

**Target:** Test component interactions and external dependencies

**Configuration to Output Tests (`tests/integration/`):**
```python
def test_generate_from_config_produces_valid_stl():
    config_path = Path("fixtures/simple-bookshelf.json")
    output_dir = tmp_path / "output"

    result = GenerateFromConfigCommand().execute(config_path, output_dir)

    stl_path = output_dir / "cabinet.stl"
    assert stl_path.exists()
    mesh = stl.mesh.Mesh.from_file(str(stl_path))
    assert mesh.is_closed()  # Valid manifold

def test_bin_packing_reduces_waste():
    cut_list = [...large cut list...]
    packer = BinPackingService()

    result = packer.pack(cut_list, sheet_size=(48, 96))

    # Verify waste is reasonable
    assert result.waste_percentage < 0.25

    # Verify all pieces placed
    assert len(result.placed_pieces) == len(cut_list)
```

**CLI Tests (`tests/integration/cli/`):**
```python
def test_cli_generate_with_config(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps(VALID_CONFIG))

    result = runner.invoke(app, ["generate", "--config", str(config)])

    assert result.exit_code == 0
    assert "Generation complete" in result.output

def test_cli_validate_reports_errors():
    result = runner.invoke(app, ["validate", "fixtures/invalid-config.json"])

    assert result.exit_code == 1
    assert "Validation Errors" in result.output
```

### End-to-End Testing

**Target:** Critical user journeys work completely

```python
# tests/e2e/test_complete_workflows.py

def test_simple_bookshelf_workflow(tmp_path):
    """Complete workflow: template -> customize -> generate -> verify"""
    # Create from template
    result = runner.invoke(app, [
        "templates", "init", "bookshelf",
        "--output", str(tmp_path / "my-shelf.json")
    ])
    assert result.exit_code == 0

    # Modify configuration
    config = json.loads((tmp_path / "my-shelf.json").read_text())
    config["cabinet"]["sections"][0]["width"] = 36
    (tmp_path / "my-shelf.json").write_text(json.dumps(config))

    # Generate
    result = runner.invoke(app, [
        "generate",
        "--config", str(tmp_path / "my-shelf.json"),
        "--output-dir", str(tmp_path / "output")
    ])
    assert result.exit_code == 0

    # Verify outputs exist and are valid
    assert (tmp_path / "output" / "cutlist.txt").exists()
    assert (tmp_path / "output" / "cabinet.stl").exists()

def test_corner_cabinet_geometry_valid(tmp_path):
    """Corner cabinet generates valid, connected geometry"""
    config = CORNER_CABINET_CONFIG
    # ... setup ...

    result = runner.invoke(app, ["generate", "--config", ...])

    # Load STL and verify corner connection
    mesh = load_stl(tmp_path / "output" / "cabinet.stl")
    # Verify no gaps at corner (custom geometry validation)
    assert verify_corner_connection(mesh)
```

### Property-Based Testing

Use Hypothesis for generative testing of algorithms:

```python
from hypothesis import given, strategies as st

@given(
    width=st.floats(min_value=12, max_value=120),
    height=st.floats(min_value=12, max_value=96),
    num_sections=st.integers(min_value=1, max_value=10)
)
def test_sections_always_fit(width, height, num_sections):
    """Sections should always fit within cabinet width"""
    wall = Wall(width=width, height=height, depth=12)
    params = LayoutParameters(num_sections=num_sections)

    cabinet = LayoutCalculator().generate_cabinet(wall, params)

    total = sum(s.width for s in cabinet.sections)
    assert total <= cabinet.interior_width

@given(pieces=st.lists(st.tuples(
    st.floats(min_value=1, max_value=24),
    st.floats(min_value=1, max_value=24)
), min_size=1, max_size=20))
def test_bin_packing_places_all_pieces(pieces):
    """Bin packing should place all pieces that can physically fit"""
    cut_pieces = [CutPiece(w, h, 1, "test", ...) for w, h in pieces]
    packer = BinPackingService()

    result = packer.pack(cut_pieces, sheet_size=(48, 96))

    # All pieces smaller than sheet should be placed
    for p in cut_pieces:
        if p.width <= 48 and p.height <= 96:
            assert p in result.placed_pieces
```

### Visual/Golden Testing

For geometry and output format validation:

```python
def test_stl_matches_golden(tmp_path):
    """STL output matches known-good reference"""
    generate_cabinet(STANDARD_CONFIG, tmp_path / "test.stl")

    # Compare mesh characteristics
    test_mesh = load_stl(tmp_path / "test.stl")
    golden_mesh = load_stl("fixtures/golden/standard-cabinet.stl")

    assert test_mesh.volume == pytest.approx(golden_mesh.volume, rel=0.001)
    assert test_mesh.bounds == pytest.approx(golden_mesh.bounds, rel=0.001)
```

### Test Organization

```
tests/
  unit/
    domain/
      test_entities.py
      test_value_objects.py
      test_services.py
    application/
      test_commands.py
      test_configuration.py
    infrastructure/
      test_exporters.py
      test_bin_packing.py
  integration/
    test_generation_pipeline.py
    test_cli.py
    test_stl_export.py
  e2e/
    test_complete_workflows.py
  fixtures/
    configs/
      valid-simple.json
      valid-complex.json
      invalid-schema.json
    golden/
      standard-cabinet.stl
  conftest.py
```

### CI/CD Testing

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.13'
    - run: pip install -e .[dev]
    - run: pytest tests/unit -v --cov=cabinets --cov-report=xml
    - run: pytest tests/integration -v
    - run: pytest tests/e2e -v --slow
```

---

## Implementation Phases

### Phase 1: Foundation (MVP)

**Timeline Estimate:** 4-6 weeks
**Goal:** Configuration-driven generation with basic multi-wall support

#### Milestone 1.1: Configuration System (Week 1-2)

**Deliverables:**
- [ ] Pydantic configuration schema (v1.0)
- [ ] JSON schema export for documentation
- [ ] ConfigurationLoader with validation
- [ ] CLI `--config` flag support
- [ ] CLI `validate` command
- [ ] 3 starter templates (bookshelf, cabinet, closet)

**Definition of Done:**
- User can load valid JSON and generate output
- Invalid JSON produces helpful error messages
- Templates can be initialized and customized

#### Milestone 1.2: Enhanced Spatial Model (Week 2-3)

**Deliverables:**
- [ ] WallSegment entity with angle support
- [ ] Room entity aggregating walls
- [ ] Multi-wall layout calculation
- [ ] 90-degree inside corner handling (butt joint style)
- [ ] Obstacle entity and avoidance logic

**Definition of Done:**
- L-shaped cabinet configuration generates correctly
- Windows/doors create appropriate voids
- Cut list reflects all pieces for multi-wall layout

#### Milestone 1.3: Variable Sections (Week 3-4)

**Deliverables:**
- [ ] Section width: explicit or "fill"
- [ ] Section-level shelf configuration
- [ ] Vertical divider generation
- [ ] Enhanced cut list with per-section details

**Definition of Done:**
- Mixed section widths work correctly
- Dividers between sections are properly sized
- Cut list groups pieces logically

#### Milestone 1.4: Phase 1 Polish (Week 4-6)

**Deliverables:**
- [ ] Basic bin packing (single sheet size)
- [ ] Enhanced STL export (verified manifold)
- [ ] Comprehensive validation warnings
- [ ] Documentation and examples
- [ ] 80%+ test coverage

**Definition of Done:**
- End-to-end workflow tested
- All Phase 1 features documented
- No critical bugs

---

### Phase 2: Professional Features

**Timeline Estimate:** 6-8 weeks
**Goal:** Complete component library and decorative elements

#### Milestone 2.1: Doors and Drawers (Week 1-3)

**Deliverables:**
- [ ] Door component (overlay style)
- [ ] Door hardware calculation (hinges)
- [ ] Drawer component with slide clearances
- [ ] Inset door style support
- [ ] Partial overlay support

**Definition of Done:**
- Doors generate with proper dimensions
- Hardware list includes hinges and slides
- Cut list includes door and drawer front pieces

#### Milestone 2.2: Corner Cabinets (Week 3-5)

**Deliverables:**
- [ ] Lazy susan corner cabinet
- [ ] Blind corner cabinet
- [ ] Diagonal front corner cabinet
- [ ] Corner component selection in config

**Definition of Done:**
- Corner cabinets generate valid geometry
- Interior is accessible as designed
- Integrates with adjacent sections

#### Milestone 2.3: Advanced Geometry (Week 4-6)

**Deliverables:**
- [ ] Outside corner handling
- [ ] Angled wall support (non-90-degree)
- [ ] Sloped ceiling accommodation
- [ ] Skylight void calculation

**Definition of Done:**
- Convex room shapes work
- Attic-style sloped ceilings handled
- All geometry produces valid STL

#### Milestone 2.4: Decorative Elements (Week 6-8)

**Deliverables:**
- [ ] Arch top generation
- [ ] Scalloped edge patterns
- [ ] Face frame support
- [ ] Edge profile specification
- [ ] Crown/base molding zones

**Definition of Done:**
- Decorative elements render in STL
- Cut list includes profile specifications
- Configuration is intuitive

---

### Phase 3: Production Optimization

**Timeline Estimate:** 4-6 weeks
**Goal:** Production-ready outputs and woodworking intelligence

#### Milestone 3.1: Advanced Bin Packing (Week 1-2)

**Deliverables:**
- [ ] Multi-sheet optimization
- [ ] Grain direction constraints
- [ ] Kerf allowance in calculations
- [ ] Visual cut diagram output
- [ ] Offcut tracking

**Definition of Done:**
- Waste reduction measurably improved
- Cut diagrams are usable for cutting
- Grain direction respected

#### Milestone 3.2: Woodworking Intelligence (Week 2-4)

**Deliverables:**
- [ ] Joinery specification in cut list
- [ ] Span warnings and recommendations
- [ ] Grain direction recommendations
- [ ] Weight capacity estimates
- [ ] Hardware quantities complete

**Definition of Done:**
- Cut list is production-ready
- Warnings prevent common mistakes
- Hardware list is complete and accurate

#### Milestone 3.3: Enhanced Outputs (Week 4-5)

**Deliverables:**
- [ ] DXF export for CNC
- [ ] Assembly sequence generation
- [ ] Infrastructure routing (lighting, electrical)
- [ ] Comprehensive JSON output

**Definition of Done:**
- DXF imports correctly into CAD software
- Assembly instructions are clear
- All outputs are consistent

#### Milestone 3.4: Phase 3 Polish (Week 5-6)

**Deliverables:**
- [ ] Performance optimization
- [ ] Documentation complete
- [ ] Example gallery
- [ ] User feedback integration

**Definition of Done:**
- Complex configs generate in < 5s
- All features documented
- User-tested and refined

---

### Rollout Strategy

**Alpha Release (After Phase 1):**
- Limited testing with select users
- Gather feedback on configuration UX
- Identify critical missing features

**Beta Release (After Phase 2):**
- Broader testing audience
- Focus on geometry correctness
- Gather professional feedback

**1.0 Release (After Phase 3):**
- Production-ready for general use
- Complete documentation
- Stable configuration schema

---

## Dependencies & Risks

### External Dependencies

#### Python Packages

| Package | Purpose | Version | Risk Level |
|---------|---------|---------|------------|
| pydantic | Configuration validation | ^2.0 | Low - Stable, well-maintained |
| numpy | Numerical calculations | ^2.0 | Low - Extremely stable |
| numpy-stl | STL export | ^3.0 | Low - Simple, stable |
| typer | CLI framework | ^0.12 | Low - Stable, active development |
| rectpack | Bin packing | ^0.2 | Medium - Less active, may need fork |
| ezdxf | DXF export | ^1.0 | Low - Stable, well-documented |
| jinja2 | Template rendering | ^3.0 | Low - Very stable |
| pytest | Testing | ^8.0 | Low - Standard choice |
| hypothesis | Property testing | ^6.0 | Low - Stable |

**Mitigation for Medium-Risk Dependencies:**
- `rectpack`: Evaluate alternatives (py-bin-packing, custom implementation)
- Pin specific versions in pyproject.toml
- Include fallback algorithms if primary fails

#### System Dependencies

- **Python 3.13+**: Required for modern type hints and performance
  - Risk: Users on older Python versions cannot use
  - Mitigation: Clear documentation of requirements

- **No external binaries required**: All functionality in pure Python
  - Benefit: Easy installation via pip

### Technical Risks

#### R1: Corner Geometry Complexity (High Impact, Medium Probability)

**Risk:** Corner cabinet geometry calculations become intractable for complex angles.

**Impact:** Cannot support non-90-degree corners; limits room geometry support.

**Mitigation:**
- Start with 90-degree corners only in MVP
- Research computational geometry libraries (Shapely, PyGEOS)
- Consider constraint-based design approach
- Defer complex angles to Phase 2 with dedicated research

#### R2: Bin Packing Optimization Limits (Medium Impact, Medium Probability)

**Risk:** Bin packing doesn't achieve target waste reduction for complex cut lists.

**Impact:** Material estimates less valuable; user trust reduced.

**Mitigation:**
- Benchmark multiple algorithms (guillotine, shelf, maxrects)
- Allow user-specified sheet sizes
- Provide manual override options
- Set realistic expectations (15% improvement target)

#### R3: STL Mesh Validity (High Impact, Low Probability)

**Risk:** Generated STL meshes have defects (non-manifold, holes, inversions).

**Impact:** Users cannot use outputs for visualization or CNC.

**Mitigation:**
- Use proven mesh generation approach from existing code
- Add mesh validation step before export
- Automated testing with mesh validation tools
- Provide mesh repair guidance if issues occur

#### R4: Configuration Schema Evolution (Medium Impact, High Probability)

**Risk:** Schema changes break existing configuration files.

**Impact:** User frustration; reluctance to update.

**Mitigation:**
- Semantic versioning for schema
- Migration scripts for breaking changes
- Deprecation warnings before removal
- Backwards compatibility where possible

#### R5: Woodworking Accuracy (High Impact, Medium Probability)

**Risk:** Generated dimensions or joinery specs are incorrect for real-world use.

**Impact:** Users build furniture that doesn't fit or isn't structurally sound.

**Mitigation:**
- Consult woodworking references for standards
- Include clear disclaimers about tolerances
- Provide tolerance configuration for different skill levels
- Manual review of key calculations
- User feedback loop for corrections

### Schedule Risks

#### S1: Scope Creep (High Probability)

**Risk:** Feature requests expand scope beyond resources.

**Mitigation:**
- Clear phase boundaries
- "Out of scope" documentation
- Feature request triage process
- Focus on MVP completion first

#### S2: Geometry Algorithm Development (Medium Probability)

**Risk:** Corner handling and obstacle avoidance algorithms take longer than expected.

**Mitigation:**
- Time-boxed research spikes
- Fallback to simpler approaches
- Consider external library integration

### Contingency Plans

**If rectpack insufficient:**
- Implement custom guillotine algorithm
- Integrate alternative library
- Reduce bin packing scope to "good enough"

**If corner geometry too complex:**
- Limit to 90-degree corners for 1.0
- Document as known limitation
- Research computational geometry solutions

**If STL export has issues:**
- Investigate cadquery or build123d as alternatives
- Consider STEP export instead
- Provide mesh repair tool recommendations

---

## Open Questions

*To be completed*

---

## Status

**Current Status:** In Progress
**Last Updated:** 2025-12-27
**Completed Sections:** Problem Statement (1/14)
**Next Section:** Goals & Success Criteria
**Progress:** 7%

### Change Log

| Date | Section | Notes |
|------|---------|-------|
| 2025-12-27 | Problem Statement | Initial creation with full analysis of existing codebase capabilities, limitations, and user pain points |

### Notes for Next Iteration
- Goals should define measurable success criteria for each major feature area
- Consider phased success metrics (MVP vs. full feature set)
- Define what "quality woodworking plans" means in testable terms
