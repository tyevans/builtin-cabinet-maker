"""Infrastructure layer - external concerns and formatters."""

from .bin_packing import (
    BinPackingConfig,
    BinPackingService,
    GuillotineBinPacker,
    Offcut,
    PackingResult,
    PlacedPiece,
    SheetConfig,
    SheetLayout,
)
from .cut_diagram_renderer import CutDiagramRenderer

# Formatters (renamed from exporters.py to avoid conflict with exporters/ package)
from .formatters import (
    CutListFormatter,
    HardwareReportFormatter,
    InstallationFormatter,
    JsonExporter,
    LayoutDiagramFormatter,
    MaterialReportFormatter,
    RoomLayoutDiagramFormatter,
)

# STL exporter (keeping legacy import path for backwards compatibility)
from .stl_exporter import StlExporter, StlMeshBuilder

# New exporter framework from exporters/ package
from .exporters import (
    Exporter,
    ExporterRegistry,
    ExportManager,
    StlLayoutExporter,
)

__all__ = [
    # Bin packing
    "BinPackingConfig",
    "BinPackingService",
    "GuillotineBinPacker",
    "Offcut",
    "PackingResult",
    "PlacedPiece",
    "SheetConfig",
    "SheetLayout",
    # Cut diagram rendering
    "CutDiagramRenderer",
    # Legacy formatters
    "CutListFormatter",
    "HardwareReportFormatter",
    "InstallationFormatter",
    "JsonExporter",
    "LayoutDiagramFormatter",
    "MaterialReportFormatter",
    "RoomLayoutDiagramFormatter",
    # STL exporter (legacy)
    "StlExporter",
    "StlMeshBuilder",
    # New exporter framework
    "Exporter",
    "ExporterRegistry",
    "ExportManager",
    "StlLayoutExporter",
]
