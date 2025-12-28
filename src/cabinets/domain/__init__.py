"""Domain layer - core business logic."""

from .entities import Cabinet, Panel, Section, Shelf, Wall
from .section_resolver import (
    SectionSpec,
    SectionWidthError,
    resolve_section_widths,
    validate_section_specs,
)
from .services import (
    CutListGenerator,
    LayoutCalculator,
    LayoutParameters,
    MaterialEstimate,
    MaterialEstimator,
    Panel3DMapper,
)
from .value_objects import (
    BoundingBox3D,
    CutPiece,
    Dimensions,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
    Position3D,
)

__all__ = [
    "BoundingBox3D",
    "Cabinet",
    "CutListGenerator",
    "CutPiece",
    "Dimensions",
    "LayoutCalculator",
    "LayoutParameters",
    "MaterialEstimate",
    "MaterialEstimator",
    "MaterialSpec",
    "MaterialType",
    "Panel",
    "Panel3DMapper",
    "PanelType",
    "Position",
    "Position3D",
    "Section",
    "SectionSpec",
    "SectionWidthError",
    "Shelf",
    "Wall",
    "resolve_section_widths",
    "validate_section_specs",
]
