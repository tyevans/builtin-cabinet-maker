# Built-in Cabinets and Shelves

A Python CLI tool and web interface for generating built-in cabinet and shelf layouts from wall dimensions. Produces cut lists, material estimates, ASCII diagrams, STL files for 3D visualization, DXF files for CNC, and assembly instructions.

## Features

- **Web Interface**: Interactive cabinet designer with real-time 3D preview
- **Layout Generation**: Generate cabinet layouts from wall dimensions or JSON configuration files
- **Multiple Output Formats**: Cut lists, material estimates, ASCII diagrams, STL, DXF, SVG, JSON, BOM
- **Multi-Section Cabinets**: Define sections with fixed widths or auto-calculated "fill" widths
- **Multi-Row Layouts**: Create complex cabinets with multiple vertical rows
- **Room Layouts**: Generate cabinets across multiple walls in a room
- **Zone Stacks**: Kitchen, mudroom, vanity, and hutch presets with countertops
- **Bin Packing Optimization**: Optimize sheet material usage with cut diagrams
- **Woodworking Intelligence**: Joinery recommendations, span warnings, hardware lists
- **Installation Planning**: Mounting points, stud analysis, hardware specifications
- **Safety Analysis**: ADA compliance, seismic requirements, material certifications
- **LLM Assembly Instructions**: AI-enhanced assembly guides via Ollama integration

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/builtin-cabinets-and-shelves.git
cd builtin-cabinets-and-shelves

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

## Quick Start

```bash
# Generate a simple cabinet from CLI options
uv run cabinets generate --width 48 --height 84 --depth 12

# Generate from a configuration file
uv run cabinets generate --config cabinet.json

# Generate with specific output format
uv run cabinets generate --width 48 --height 84 --depth 12 --format cutlist

# Export to multiple formats
uv run cabinets generate --config cabinet.json --output-formats stl,dxf,json --output-dir ./output

# Validate a configuration file
uv run cabinets validate cabinet.json

# List available templates
uv run cabinets templates list
```

## Web Interface (Frontend)

The project includes an interactive web-based cabinet designer built with modern web technologies.

### Frontend Tech Stack

- **[Lit](https://lit.dev/)** - Web Components library
- **[Shoelace](https://shoelace.style/)** - UI component library
- **[Tailwind CSS](https://tailwindcss.com/)** - Utility-first CSS
- **[Three.js](https://threejs.org/)** - 3D visualization for STL preview
- **[Vite](https://vitejs.dev/)** - Build tool and dev server

### Running the Frontend

```bash
# Install frontend dependencies
cd frontend
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The frontend requires the FastAPI backend server running at `http://localhost:8000`. Configure the API URL via the `VITE_API_URL` environment variable if needed.

### Starting the Backend API

```bash
# Start the FastAPI server
uv run uvicorn cabinets.web.app:app --reload
```

### Frontend Features

- **Real-time 3D Preview**: Interactive STL visualization with orbit controls
- **Cabinet Configuration**: Set dimensions, materials, and section layouts
- **Section Tree Editor**: Visual hierarchy editor for cabinet sections
- **Component Types**: Configure open shelves, doors, drawers, and cubbies
- **Room & Obstacle Editor**: Define room layouts and obstacles (windows, outlets)
- **Infrastructure Editor**: Configure wall types and mounting options
- **Installation Planner**: Mounting points and hardware specifications
- **Export Menu**: Download designs as STL, DXF, JSON, BOM, or assembly instructions
- **Config Import/Export**: Save and load cabinet configurations as JSON

### Frontend Architecture

```
frontend/src/
├── api/                  # API client and types
│   ├── api.ts            # FastAPI client
│   └── types.ts          # TypeScript interfaces
├── components/           # Lit web components
│   ├── app-shell.ts      # Main application shell
│   ├── config-sidebar.ts # Configuration panel
│   ├── preview-panel.ts  # 3D preview container
│   ├── stl-viewer.ts     # Three.js STL renderer
│   ├── section-tree-editor/  # Section hierarchy editor
│   ├── room-editor/      # Room layout editor
│   ├── obstacle-editor/  # Obstacle placement
│   └── ...
├── state/                # Application state management
│   ├── cabinet-state.ts  # Cabinet configuration store
│   └── store.ts          # Generic store utilities
└── main.ts               # Application entry point
```

## CLI Commands

### `cabinets generate`

Generate a cabinet layout from wall dimensions or configuration file.

```bash
# Basic options
--config, -c PATH       Path to JSON configuration file
--width, -w FLOAT       Wall width in inches
--height, -h FLOAT      Wall height in inches
--depth, -d FLOAT       Cabinet depth in inches
--sections, -s INT      Number of vertical sections
--shelves INT           Shelves per section
--thickness, -t FLOAT   Material thickness in inches (default: 0.75)

# Output options
--format, -f FORMAT     Output format (see Output Formats below)
--output, -o PATH       Output file path (required for stl)
--output-formats STR    Comma-separated formats: stl,dxf,json,bom,svg,assembly
--output-dir PATH       Output directory for multi-format export
--project-name STR      Project name for file naming (default: cabinet)
--optimize              Enable bin packing optimization

# Installation options
--wall-type TYPE        Wall type: drywall, plaster, concrete, cmu, brick
--stud-spacing FLOAT    Stud spacing in inches (default: 16)
--mounting-system TYPE  Mounting: direct_to_stud, french_cleat, hanging_rail, toggle_bolt
--expected-load LOAD    Load category: light, medium, heavy

# LLM Assembly options
--llm-instructions      Use LLM for enhanced assembly instructions
--skill-level LEVEL     Skill level: beginner, intermediate, expert
--llm-model MODEL       Ollama model name (default: llama3.2)

# Safety options
--safety-factor FLOAT   Safety factor for capacity (2.0-6.0, default: 4.0)
--accessibility         Enable ADA accessibility checking
--child-safe            Enable child safety mode
--seismic-zone ZONE     IBC seismic category (A-F)
--material-cert CERT    Material certification level
```

### Output Formats

| Format | Description |
|--------|-------------|
| `all` | Display all outputs (default) |
| `cutlist` | Cut list with dimensions and quantities |
| `diagram` | ASCII diagram of cabinet layout |
| `materials` | Material estimate with sheet counts |
| `json` | Full JSON export of cabinet data |
| `stl` | 3D STL file for visualization/printing |
| `cutlayout` | Cut diagram showing piece placement on sheets |
| `woodworking` | Joinery specs, span warnings, hardware |
| `installation` | Mounting instructions and hardware |
| `safety` | Safety analysis report |
| `safety_labels` | Printable safety labels |
| `llm-assembly` | AI-enhanced assembly instructions |

### `cabinets validate`

Validate a JSON configuration file.

```bash
uv run cabinets validate cabinet.json
```

### `cabinets templates`

Manage configuration templates.

```bash
# List available templates
uv run cabinets templates list

# Show template contents
uv run cabinets templates show bookcase
```

## Configuration File

Cabinet configurations use JSON with a versioned schema:

```json
{
  "schema_version": "1.0",
  "cabinet": {
    "width": 72.0,
    "height": 84.0,
    "depth": 12.0,
    "material": {
      "type": "plywood",
      "thickness": 0.75
    },
    "sections": [
      {"width": 24.0, "shelves": 3},
      {"width": 24.0, "shelves": 5},
      {"width": "fill", "shelves": 4}
    ]
  },
  "output": {
    "format": "all"
  }
}
```

### Section Types

Sections can be configured with different types:

```json
{
  "sections": [
    {"width": 24, "shelves": 5, "type": "open"},
    {"width": 18, "shelves": 0, "type": "doored", "doors": 2},
    {"width": 12, "type": "drawers", "drawer_count": 4},
    {"width": "fill", "type": "cubby", "cubby_width": 6, "cubby_height": 6}
  ]
}
```

### Zone Stack Configurations

For kitchen, mudroom, vanity, or hutch configurations:

```json
{
  "schema_version": "1.11",
  "cabinet": {
    "width": 72,
    "height": 84,
    "depth": 24,
    "zone_stack": {
      "preset": "kitchen",
      "countertop": {
        "thickness": 1.5,
        "overhang": 1.0,
        "edge_treatment": "eased"
      }
    }
  }
}
```

### Room Layouts

For multi-wall cabinet runs:

```json
{
  "schema_version": "1.0",
  "room": {
    "name": "Office",
    "walls": [
      {"length": 120, "height": 96, "depth": 12, "angle": 0},
      {"length": 96, "height": 96, "depth": 12, "angle": 90}
    ]
  },
  "cabinet": {
    "sections": [
      {"width": 24, "shelves": 5, "wall_index": 0},
      {"width": 36, "shelves": 3, "wall_index": 1}
    ]
  }
}
```

## Architecture

The project follows Clean Architecture with distinct layers:

```
src/cabinets/
├── domain/           # Core business logic (entities, value objects, services)
├── application/      # Use cases and orchestration
├── infrastructure/   # External adapters (exporters, formatters)
├── cli/              # Command-line interface
├── web/              # FastAPI REST API
└── contracts/        # Protocols and interfaces

frontend/
└── src/              # Lit/TypeScript web application
```

### Domain Layer (`domain/`)

Contains core business logic independent of external concerns.

**Entities** (`entities.py`):
- `Cabinet` - Complete cabinet with sections
- `Section` - Vertical section containing shelves and panels
- `Panel` - Individual panel (side, top, shelf, door, etc.)
- `Shelf` - Horizontal shelf within a section
- `Room` - Room defined by connected wall segments
- `Wall` / `WallSegment` - Wall dimensions and geometry
- `Obstacle` - Obstacles that cabinets must avoid (windows, outlets, etc.)

**Value Objects** (`value_objects.py`):
- `Dimensions`, `Position`, `Position3D` - Spatial measurements
- `MaterialSpec` - Material type and thickness
- `CutPiece` - Piece for cut list with dimensions and quantity
- `PanelType`, `SectionType` - Type enumerations
- Safety-related: `SeismicZone`, `MaterialCertification`, `SafetyCategory`
- Geometry: `CeilingSlope`, `Skylight`, `AngleCut`, `TaperSpec`

**Domain Services** (`services/`):
- `LayoutCalculator` - Calculate cabinet layouts from wall dimensions
- `CutListGenerator` - Generate cut lists from cabinet structure
- `MaterialEstimator` - Estimate sheet material requirements
- `PanelGenerationService` - Generate panels for cabinets
- `WoodworkingIntelligence` - Joinery, spans, hardware calculations
- `SafetyService` - Safety analysis and compliance checking
- `InstallationFacade` - Installation planning and mounting

### Application Layer (`application/`)

Orchestrates domain services and handles configuration.

**Commands** (`commands.py`):
- `GenerateLayoutCommand` - Main use case for layout generation

**Configuration** (`config/`):
- `schemas/` - Pydantic v2 schemas for JSON configuration
- `adapters/` - Convert config schemas to domain objects
- `validators/` - Validation rules for configuration
- `loader.py` - Load and parse configuration files
- `merger.py` - Merge CLI options with file configuration

**Services** (`services/`):
- `InputValidator` - Validate input parameters
- `OutputAssembler` - Assemble final output DTOs
- `SectionWidthResolver` - Resolve "fill" widths

**Strategies** (`strategies/`):
- Layout strategies: `UniformStrategy`, `RowSpecStrategy`, `SectionSpecStrategy`

### Infrastructure Layer (`infrastructure/`)

External adapters for output and persistence.

**Exporters** (`exporters/`):
- `STLExporter` - 3D mesh generation using numpy-stl
- `DXFExporter` - DXF files for CNC/CAD using ezdxf
- `SVGExporter` - SVG cut diagrams
- `JsonExporter` - JSON data export
- `BOMExporter` - Bill of materials
- `AssemblyExporter` - Assembly instructions
- `LLMAssemblyExporter` - AI-enhanced assembly via Ollama

**Formatters** (`formatters.py`):
- `CutListFormatter` - Format cut lists for display
- `LayoutDiagramFormatter` - ASCII cabinet diagrams
- `MaterialReportFormatter` - Material estimates

**Bin Packing** (`bin_packing.py`):
- `BinPackingService` - Optimize piece placement on sheets
- `CutDiagramRenderer` - Render cut diagrams as ASCII/SVG

### CLI Layer (`cli/`)

Command-line interface using Typer.

**Main Commands** (`main.py`):
- `generate` - Generate cabinet layout
- `cutlist` - Display cut list only
- `materials` - Display material estimate
- `diagram` - Display ASCII diagram
- `validate` - Validate configuration file
- `templates` - Template management subcommands

### Web Layer (`web/`)

FastAPI REST API for the frontend application.

**Endpoints**:
- `POST /api/v1/generate/from-config` - Generate layout from full configuration
- `GET /api/v1/export/formats` - List available export formats
- `POST /api/v1/export/{format}` - Export to specified format (stl, dxf, json, bom, svg, assembly)
- `POST /api/v1/export/stl-from-config` - Generate STL from full configuration
- `POST /api/v1/export/cut-layouts` - Get bin-packed cut layout SVGs

### Frontend (`frontend/`)

Lit-based web application with Shoelace UI components.

**Components** (`src/components/`):
- `app-shell` - Main layout with header, sidebar, and preview area
- `config-sidebar` - Cabinet configuration forms
- `section-tree-editor` - Hierarchical section editor
- `stl-viewer` - Three.js-based 3D STL renderer
- `preview-panel` - Tabbed preview (3D, cut list, assembly, BOM)
- `export-menu` - Download exports in various formats

**State Management** (`src/state/`):
- `cabinet-state.ts` - Reactive store for cabinet configuration
- Auto-regeneration on configuration changes with debouncing

## Key Public Interfaces

### Domain Entities

```python
from cabinets.domain import Cabinet, Section, Panel, Shelf, Wall, Room

# Create a wall constraint
wall = Wall(width=48.0, height=84.0, depth=12.0)

# Access cabinet properties
cabinet.width           # Overall width
cabinet.interior_width  # Width minus side panels
cabinet.sections        # List of sections
```

### Application DTOs

```python
from cabinets.application import WallInput, LayoutParametersInput, LayoutOutput

# Input DTOs
wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
params = LayoutParametersInput(
    num_sections=3,
    shelves_per_section=4,
    material_thickness=0.75
)

# Execute generation
from cabinets.application.factory import get_factory
factory = get_factory()
command = factory.create_generate_command()
result = command.execute(wall_input, params)

# Access output
result.cabinet      # Generated Cabinet entity
result.cut_list     # List of CutPiece objects
result.is_valid     # Validation status
result.errors       # List of error messages
```

### Formatters and Exporters

```python
# Get formatters via factory
factory = get_factory()
cut_formatter = factory.get_cut_list_formatter()
diagram_formatter = factory.get_layout_diagram_formatter()
material_formatter = factory.get_material_report_formatter()

# Format output
print(cut_formatter.format(result.cut_list))
print(diagram_formatter.format(result.cabinet))

# Export to file
stl_exporter = factory.get_stl_exporter()
stl_exporter.export_to_file(result.cabinet, Path("cabinet.stl"))
```

### Exporter Registry

```python
from cabinets.infrastructure.exporters import ExporterRegistry

# Get exporter by format
JsonExporter = ExporterRegistry.get("json")
exporter = JsonExporter()

# Export to file
exporter.export_to_file(result, Path("cabinet.json"))

# Or get formatted string
output = exporter.format_for_console(result)
```

## Development

### Backend

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_entities.py

# Run with coverage
uv run pytest --cov=cabinets

# Type checking
uv run mypy src/cabinets

# Start API server for development
uv run uvicorn cabinets.web.app:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Type checking
npm run typecheck

# Build for production
npm run build
```
