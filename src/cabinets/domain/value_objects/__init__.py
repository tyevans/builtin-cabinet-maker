"""Value objects for the cabinet domain.

This module provides immutable data types used throughout the cabinet
system. All classes are re-exported from sub-modules for convenience.
"""

from __future__ import annotations

# Core geometry and materials
from ._core_geometry import (
    CutPiece,
    Dimensions,
    MaterialSpec,
    MaterialType,
    MountingPoint,
    Point2D,
    Position,
    Position3D,
)

# Panel types and cutting specifications
from ._panels import (
    AngleCut,
    GrainDirection,
    JointType,
    NotchSpec,
    PanelCutMetadata,
    PanelType,
    SectionType,
    TaperSpec,
)

# 3D geometry and visualization
from ._3d_geometry import (
    BoundingBox3D,
    CeilingSlope,
    OutsideCornerConfig,
    Skylight,
)

# Safety compliance (FRD-21)
from ._safety import (
    ADAStandard,
    MaterialCertification,
    SafetyCategory,
    SafetyCheckStatus,
    SeismicZone,
    VOCCategory,
)

# Obstacle detection and avoidance
from ._obstacles import (
    Clearance,
    CollisionResult,
    DEFAULT_CLEARANCES,
    ObstacleType,
    ObstacleZone,
    SectionBounds,
)

# Layout and spatial arrangement
from ._layout import (
    FitError,
    GeometryError,
    LayoutResult,
    LayoutWarning,
    PlacedSection,
    SectionTransform,
    SkippedArea,
    ValidRegion,
    WallPosition,
    WallSectionAssignment,
)

# Corner cabinet handling
from ._corners import (
    CornerSectionAssignment,
    CornerType,
    WallSpaceReservation,
)

# Installation support (FRD-17)
from ._installation import (
    LoadCategory,
    MountingSystem,
    WallType,
)

# Infrastructure integration (FRD-15)
from ._infrastructure import (
    CutoutShape,
    GrommetSize,
    LightingLocation,
    LightingType,
    OutletType,
    PanelCutout,
    VentilationPattern,
)

# Desk configurations (FRD-18)
from ._desks import (
    DeskDimensions,
    DeskType,
    EdgeTreatment,
    PedestalType,
)

# Countertops and vertical zones (FRD-22)
from ._zones import (
    CountertopEdgeType,
    GapPurpose,
    ZoneMounting,
    ZonePreset,
    ZoneType,
)

# Entertainment center (FRD-19)
from ._entertainment import (
    EquipmentType,
    SoundbarType,
    SpeakerType,
)

# Bay window alcove (FRD-23)
from ._bays import (
    ApexPoint,
    BayAlcoveConfig,
    BayType,
    CeilingFacet,
    FillerTreatment,
    RadialCeilingGeometry,
)

__all__ = [
    # Core geometry
    "MaterialType",
    "Dimensions",
    "Position",
    "MaterialSpec",
    "CutPiece",
    "Position3D",
    "Point2D",
    "MountingPoint",
    # Panels
    "PanelType",
    "SectionType",
    "GrainDirection",
    "JointType",
    "AngleCut",
    "TaperSpec",
    "NotchSpec",
    "PanelCutMetadata",
    # 3D geometry
    "BoundingBox3D",
    "CeilingSlope",
    "Skylight",
    "OutsideCornerConfig",
    # Safety
    "SafetyCheckStatus",
    "SafetyCategory",
    "SeismicZone",
    "MaterialCertification",
    "VOCCategory",
    "ADAStandard",
    # Obstacles
    "ObstacleType",
    "Clearance",
    "SectionBounds",
    "ObstacleZone",
    "CollisionResult",
    "DEFAULT_CLEARANCES",
    # Layout
    "WallPosition",
    "GeometryError",
    "SectionTransform",
    "WallSectionAssignment",
    "FitError",
    "ValidRegion",
    "PlacedSection",
    "LayoutWarning",
    "SkippedArea",
    "LayoutResult",
    # Corners
    "CornerType",
    "CornerSectionAssignment",
    "WallSpaceReservation",
    # Installation
    "WallType",
    "MountingSystem",
    "LoadCategory",
    # Infrastructure
    "LightingType",
    "LightingLocation",
    "OutletType",
    "GrommetSize",
    "CutoutShape",
    "VentilationPattern",
    "PanelCutout",
    # Desks
    "DeskType",
    "EdgeTreatment",
    "PedestalType",
    "DeskDimensions",
    # Zones
    "ZoneType",
    "ZoneMounting",
    "GapPurpose",
    "ZonePreset",
    "CountertopEdgeType",
    # Entertainment
    "EquipmentType",
    "SoundbarType",
    "SpeakerType",
    # Bays
    "BayType",
    "FillerTreatment",
    "ApexPoint",
    "CeilingFacet",
    "RadialCeilingGeometry",
    "BayAlcoveConfig",
]
