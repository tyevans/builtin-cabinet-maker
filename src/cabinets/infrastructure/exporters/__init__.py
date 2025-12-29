"""Exporter framework for cabinet layout outputs.

This package provides a unified exporter framework with:
- Exporter Protocol: Defines the interface for all exporters
- ExporterRegistry: Central registry for format discovery
- ExportManager: Coordinates multi-format export operations

Registered exporters:
- assembly: Markdown assembly instructions with build order and joinery details
- bom: Bill of Materials with sheet goods, hardware, and edge banding
- dxf: DXF format for 2D CNC machining and manufacturing
- json: Enhanced JSON with normalized config, 3D positions, joinery, and BOM
- stl: STL format for 3D visualization/printing
- svg: SVG cut diagrams showing piece placements on sheets

Usage:
    from cabinets.infrastructure.exporters import (
        AssemblyInstructionGenerator,
        BillOfMaterials,
        BomGenerator,
        DxfExporter,
        EnhancedJsonExporter,
        ExportManager,
        ExporterRegistry,
        StlLayoutExporter,
        SvgExporter,
    )

    # List available formats
    formats = ExporterRegistry.available_formats()

    # Get a specific exporter
    assembly_exporter_cls = ExporterRegistry.get("assembly")
    assembly_exporter = assembly_exporter_cls()

    bom_exporter_cls = ExporterRegistry.get("bom")
    bom_exporter = bom_exporter_cls(output_format="csv", include_costs=True)

    dxf_exporter_cls = ExporterRegistry.get("dxf")
    dxf_exporter = dxf_exporter_cls(mode="combined", units="mm")

    json_exporter_cls = ExporterRegistry.get("json")
    json_exporter = json_exporter_cls(include_3d_positions=True, include_joinery=True)

    stl_exporter_cls = ExporterRegistry.get("stl")
    stl_exporter = stl_exporter_cls()

    svg_exporter_cls = ExporterRegistry.get("svg")
    svg_exporter = svg_exporter_cls()  # Requires --optimize for bin packing

    # Export to multiple formats
    manager = ExportManager(output_dir=Path("./output"))
    results = manager.export_all(["assembly", "bom", "dxf", "json", "stl", "svg"], layout_output, project_name="my_cabinet")
"""

from cabinets.infrastructure.exporters.base import (
    Exporter,
    ExporterRegistry,
    ExportManager,
)

# Import exporters to trigger registration
from cabinets.infrastructure.exporters.assembly import AssemblyInstructionGenerator
from cabinets.infrastructure.exporters.bom import (
    BillOfMaterials,
    BomGenerator,
    EdgeBandingItem,
    HardwareBomItem,
    SheetGoodItem,
)
from cabinets.infrastructure.exporters.dxf import DxfExporter
from cabinets.infrastructure.exporters.enhanced_json import EnhancedJsonExporter
from cabinets.infrastructure.exporters.stl import StlLayoutExporter
from cabinets.infrastructure.exporters.svg import SvgExporter

# Re-export the underlying STL implementation for backwards compatibility
from cabinets.infrastructure.stl_exporter import StlExporter, StlMeshBuilder

# Re-export formatters for backwards compatibility
# (these were previously in exporters.py, now in formatters.py)
from cabinets.infrastructure.formatters import (
    CutListFormatter,
    HardwareReportFormatter,
    JsonExporter,
    LayoutDiagramFormatter,
    MaterialReportFormatter,
    RoomLayoutDiagramFormatter,
)

__all__ = [
    # Framework
    "Exporter",
    "ExporterRegistry",
    "ExportManager",
    # Registered exporters
    "AssemblyInstructionGenerator",
    "BillOfMaterials",
    "BomGenerator",
    "DxfExporter",
    "EdgeBandingItem",
    "EnhancedJsonExporter",
    "HardwareBomItem",
    "SheetGoodItem",
    "StlLayoutExporter",
    "SvgExporter",
    # Legacy compatibility - STL
    "StlExporter",
    "StlMeshBuilder",
    # Legacy compatibility - Formatters
    "CutListFormatter",
    "HardwareReportFormatter",
    "JsonExporter",
    "LayoutDiagramFormatter",
    "MaterialReportFormatter",
    "RoomLayoutDiagramFormatter",
]
