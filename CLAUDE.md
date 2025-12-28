# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI tool for generating built-in cabinet and shelf layouts from wall dimensions. It produces cut lists, material estimates, ASCII diagrams, and STL files for 3D visualization/printing.

## Commands

```bash
# Install dependencies
uv sync

# Run CLI
uv run cabinets generate --width 48 --height 84 --depth 12
uv run cabinets generate --config cabinet.json
uv run cabinets validate cabinet.json
uv run cabinets templates list

# Run tests
uv run pytest                           # all tests
uv run pytest tests/unit/               # unit tests only
uv run pytest tests/integration/        # integration tests only
uv run pytest tests/unit/test_entities.py -k "test_wall"  # specific test pattern
```

## Architecture

The project follows Clean Architecture with distinct layers:

### Domain Layer (`src/cabinets/domain/`)
- **entities.py**: Core domain objects - `Cabinet`, `Section`, `Shelf`, `Panel`, `Wall`, `Room`, `WallSegment`
- **value_objects.py**: Immutable value types - `Dimensions`, `Position`, `MaterialSpec`, `CutPiece`, `PanelType`
- **services.py**: Domain services - `LayoutCalculator`, `CutListGenerator`, `MaterialEstimator`, `Panel3DMapper`
- **section_resolver.py**: Resolves "fill" widths for variable-width sections

### Application Layer (`src/cabinets/application/`)
- **commands.py**: Use cases - `GenerateLayoutCommand` orchestrates layout generation
- **dtos.py**: Data transfer objects for CLI/API boundaries
- **config/**: JSON configuration schema, loading, validation, and merging with CLI overrides

### Infrastructure Layer (`src/cabinets/infrastructure/`)
- **exporters.py**: Output formatters - `CutListFormatter`, `LayoutDiagramFormatter`, `MaterialReportFormatter`, `JsonExporter`
- **stl_exporter.py**: 3D mesh generation using numpy-stl

### CLI Layer (`src/cabinets/cli/`)
- **main.py**: Typer CLI with commands: `generate`, `cutlist`, `materials`, `diagram`, `validate`
- **commands/**: Subcommands for validation and template management

## Key Design Patterns

- Cabinet dimensions use inches as the standard unit
- Sections can have fixed widths or `"fill"` to auto-calculate remaining space
- Material thickness defaults: 3/4" for panels, 1/2" for back panel
- The `Panel3DMapper` converts 2D panel representations to 3D bounding boxes for STL export
- Configuration files use Pydantic v2 schemas with version validation (schema_version: "1.0")

## Configuration File Structure

```json
{
  "schema_version": "1.0",
  "cabinet": {
    "width": 48.0,
    "height": 84.0,
    "depth": 12.0,
    "material": {"type": "plywood", "thickness": 0.75},
    "sections": [
      {"width": 24.0, "shelves": 3},
      {"width": "fill", "shelves": 5}
    ]
  },
  "output": {"format": "all"}
}
```
