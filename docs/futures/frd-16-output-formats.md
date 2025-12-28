# FRD-16: Advanced Output Formats

**Created:** 2025-12-27
**Status:** Ready for Implementation
**Priority:** High
**Depends On:** FRD-13 (Bin Packing), existing exporters in `src/cabinets/infrastructure/`

---

## Problem Statement

Current output limited to STL, basic JSON, and text cut lists. Users need:
- DXF files for CNC routing
- Assembly instructions for build sequencing
- Complete JSON for external tool integration
- Visual SVG cut diagrams from bin packing
- Consolidated bill of materials (BOM)

---

## Goals & Success Criteria

| Goal | Success Criteria |
|------|------------------|
| DXF export | Valid 2D DXF with layers, opens in CAD software |
| Assembly instructions | Logical build order with joinery references |
| Enhanced JSON | All config, dimensions, pieces, warnings in output |
| SVG diagrams | One SVG per sheet with labeled pieces |
| BOM generation | Complete material/hardware quantities |

---

## Scope

**In Scope:** DXF exporter, assembly sequence generator, enhanced JSON, SVG cut diagrams, BOM aggregator, CLI `--output-formats` flag, JSON config `output.formats: [...]`

**Out of Scope:** G-code generation, interactive editors, PDF output, vendor-specific CAM formats

---

## Functional Requirements

### FR-01: DXF Export

- **FR-01.1**: Generate 2D DXF (R2010 format) using `ezdxf` library
- **FR-01.2**: Scale: 1 DXF unit = 1 inch
- **FR-01.3**: Output modes: `per_panel` or `combined`
- **FR-01.4**: Required layers: `OUTLINE`, `DADOS`, `HOLES`, `LABELS`
- **FR-01.5**: Dado positions calculated from shelf/divider placement
- **FR-01.6**: Configurable hole pattern (32mm system support)

### FR-02: Assembly Sequence

- **FR-02.1**: Generate step-by-step build instructions (markdown)
- **FR-02.2**: Build order: carcase -> back -> dividers -> shelves -> doors
- **FR-02.3**: Each step references pieces by cut list label
- **FR-02.4**: Joinery methods: `dado`, `rabbet`, `butt`, `biscuit`, `pocket_hole`
- **FR-02.5**: Include fastener/glue notes per step

### FR-03: Enhanced JSON Output

- **FR-03.1**: Include normalized configuration (all defaults resolved)
- **FR-03.2**: Include all calculated dimensions per piece
- **FR-03.3**: Include 3D positions for each panel
- **FR-03.4**: Include joinery specifications and validation warnings
- **FR-03.5**: Schema version field for compatibility

```json
{
  "schema_version": "1.0",
  "config": {},
  "cabinet": { "dimensions": {}, "sections": [] },
  "pieces": [{ "id": "", "dimensions": {}, "position_3d": {}, "joinery": [] }],
  "cut_list": [],
  "bom": {},
  "warnings": []
}
```

### FR-04: SVG Cut Diagrams

- **FR-04.1**: One SVG per sheet from bin packing result
- **FR-04.2**: Pieces as colored rectangles (by type: shelf=blue, side=green)
- **FR-04.3**: Labels with piece name and dimensions
- **FR-04.4**: Legend, waste areas in gray, sheet number header
- **FR-04.5**: Configurable: `show_dimensions`, `show_labels`, `show_grain`

### FR-05: Bill of Materials (BOM)

- **FR-05.1**: Sheet goods: material, thickness, sheet size, quantity, sq ft
- **FR-05.2**: Hardware: fasteners, shelf pins, hinges, slides with quantities
- **FR-05.3**: Edge banding: linear feet per material/color
- **FR-05.4**: Optional `unit_cost` fields for cost estimation
- **FR-05.5**: Output formats: `text`, `csv`, `json`

### FR-06: CLI Integration

- **FR-06.1**: `--output-formats stl,dxf,json,bom,svg,assembly`
- **FR-06.2**: `--output-formats all` enables all formats
- **FR-06.3**: `--output-dir <path>` for output directory
- **FR-06.4**: File naming: `{project_name}_{format}.{ext}`
- **FR-06.5**: JSON config:
```yaml
output:
  formats: ["stl", "dxf", "json", "bom"]
  output_dir: "./output"
  dxf: { mode: "per_panel" }
  svg: { scale: 10, show_dimensions: true }
  bom: { format: "csv" }
```

---

## Data Models

### Exporter Protocol

```python
# src/cabinets/infrastructure/exporters/base.py
class Exporter(Protocol):
    format_name: str
    file_extension: str
    def export(self, output: LayoutOutput, path: Path) -> None: ...
    def export_string(self, output: LayoutOutput) -> str: ...
```

### DXF Models

```python
@dataclass(frozen=True)
class DxfPanelData:
    label: str
    width: float
    height: float
    outline: list[tuple[float, float]]
    dados: list[DadoLine]
    holes: list[HoleSpec]

@dataclass(frozen=True)
class DadoLine:
    start: tuple[float, float]
    end: tuple[float, float]
    depth: float
    width: float

@dataclass(frozen=True)
class HoleSpec:
    center: tuple[float, float]
    diameter: float
    purpose: str  # "shelf_pin", "mounting", "wire"
```

### Assembly Models

```python
class JoineryMethod(str, Enum):
    DADO = "dado"
    RABBET = "rabbet"
    BUTT = "butt"
    BISCUIT = "biscuit"
    POCKET_HOLE = "pocket_hole"

@dataclass(frozen=True)
class AssemblyStep:
    step_number: int
    description: str
    pieces_involved: tuple[str, ...]
    connections: tuple[AssemblyConnection, ...]
    notes: str = ""
```

### BOM Models

```python
@dataclass(frozen=True)
class BillOfMaterials:
    sheet_goods: tuple[SheetGoodItem, ...]
    hardware: tuple[HardwareItem, ...]
    edge_banding: tuple[EdgeBandingItem, ...]

@dataclass(frozen=True)
class SheetGoodItem:
    material: MaterialSpec
    sheet_size: tuple[float, float]
    quantity: int
    unit_cost: float | None = None

@dataclass(frozen=True)
class HardwareItem:
    name: str
    size: str
    quantity: int
    sku: str = ""
```

---

## Technical Approach

### File Structure

```
src/cabinets/infrastructure/exporters/
    __init__.py
    base.py           # Exporter protocol, registry
    dxf.py            # DXF exporter (ezdxf)
    svg.py            # SVG cut diagram renderer
    assembly.py       # Assembly instruction generator
    enhanced_json.py  # Full JSON exporter
    bom.py            # BOM generator
    manager.py        # Multi-format export coordinator
```

### Exporter Registry

```python
class ExporterRegistry:
    _exporters: dict[str, type[Exporter]] = {}

    @classmethod
    def register(cls, format_name: str):
        def decorator(exporter_cls):
            cls._exporters[format_name] = exporter_cls
            return exporter_cls
        return decorator

    @classmethod
    def export_all(cls, formats: list[str], output: LayoutOutput, output_dir: Path) -> dict[str, Path]:
        ...
```

### DXF Generation

```python
import ezdxf

@ExporterRegistry.register("dxf")
class DxfExporter:
    LAYERS = {
        "OUTLINE": {"color": 7},
        "DADOS": {"color": 1},
        "HOLES": {"color": 3},
        "LABELS": {"color": 5},
    }

    def export(self, output: LayoutOutput, path: Path) -> None:
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        for name, props in self.LAYERS.items():
            doc.layers.add(name, color=props["color"])
        for piece in output.cut_list:
            self._draw_panel(msp, piece)
        doc.saveas(path)
```

### CLI Extension

```python
@app.command()
def generate(
    output_formats: Annotated[str | None, typer.Option("--output-formats")] = None,
    output_dir: Annotated[Path | None, typer.Option("--output-dir")] = None,
) -> None:
    if output_formats:
        formats = [f.strip() for f in output_formats.split(",")]
        manager = ExportManager(output_dir or Path("."))
        files = manager.export_all(formats, result)
        for fmt, path in files.items():
            typer.echo(f"{fmt.upper()} exported to: {path}")
```

---

## Validation Rules

| Rule | Check | Message |
|------|-------|---------|
| V-01 | Output directory writable | "Cannot write to {path}" |
| V-02 | ezdxf available | "DXF export requires ezdxf: pip install ezdxf" |
| V-03 | Format recognized | "Unknown format: {name}" |
| V-04 | SVG requires bin packing | "SVG diagrams require bin packing enabled" |

---

## Testing Strategy

**Unit Tests:**
- DXF layer creation (all 4 layers present)
- DXF panel outline (closed polyline, correct dimensions)
- Assembly step ordering (carcase before shelves)
- BOM sheet count matches bin packing
- Enhanced JSON has all required fields
- SVG piece placement at correct positions

**Integration Tests:**
- Full cabinet exports to all formats without error
- DXF opens in LibreCAD/AutoCAD
- SVG renders in browser
- BOM CSV imports into spreadsheet

---

## Implementation Phases

| Phase | Tasks | Est. |
|-------|-------|------|
| 1. Framework | `base.py` protocol/registry, `manager.py`, migrate `StlExporter` | 0.5d |
| 2. DXF | Add ezdxf, implement exporter with layers, dado/hole generation | 1.5d |
| 3. Assembly | Dependency graph, build order, joinery detection, markdown output | 1d |
| 4. JSON | Extend exporter with full schema, 3D positions, warnings | 0.5d |
| 5. SVG | Cut diagram renderer, colors, labels, legend, bin packing integration | 1d |
| 6. BOM | Sheet goods, hardware, edge banding aggregation, CSV/JSON output | 0.5d |
| 7. CLI | `--output-formats`, `--output-dir`, config schema, e2e tests | 0.5d |

**Total: ~5.5 days**

---

## Dependencies & Risks

### Dependencies

| Dependency | Purpose |
|------------|---------|
| `ezdxf` | DXF generation (`pip install ezdxf`) |
| FRD-13 | Bin packing for SVG layouts |
| FRD-14 | Joinery data for assembly |

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ezdxf compatibility | Medium | Pin version, test with CAD apps |
| Assembly order complexity | Medium | Start with simple carcase-first |
| BOM accuracy | Medium | Validate against manual calculations |

---

## Open Questions

1. **DXF units**: Add `--dxf-units mm` conversion flag?
   - Proposed: Default inches, optional mm flag

2. **Assembly format**: Plain text vs. Markdown?
   - Proposed: Markdown default

3. **BOM vendor formats**: Support lumber yard-specific formats?
   - Proposed: Defer; CSV sufficient for v1

---

*FRD-16 ready for implementation: 2025-12-27*
