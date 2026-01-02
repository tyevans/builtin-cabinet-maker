"""Domain services for cabinet layout and calculations.

This package provides all domain services for cabinet generation.
Import from subpackages for specialized functionality:
- .installation: Installation support (mounting, cleats, hardware)
- .safety: Safety compliance analysis (FRD-21)
- .woodworking: Woodworking intelligence (joinery, spans, hardware)
- .entertainment_center: Entertainment center layout (FRD-19)
- .bay_alcove_service: Bay alcove layout (FRD-23)
"""

# Core layout services
from .cut_list import CutListGenerator
from .layout_calculator import LayoutCalculator, LayoutParameters
from .material_estimator import MaterialEstimate, MaterialEstimator
from .panel_mapper import Panel3DMapper, RoomPanel3DMapper

# Obstacle handling
from .obstacle import (
    ObstacleAwareLayoutService,
    ObstacleCollisionService,
)

# Geometry services (FRD-11)
from .geometry import (
    OutsideCornerService,
    SkylightVoidService,
    SlopedCeilingService,
)

# Room layout
from .room_layout import RoomLayoutService

# Zone layout (FRD-22)
from .zone_layout import ZoneLayoutService, ZoneStackLayoutResult

# Radial ceiling and panel geometry (FRD-23)
from .radial_ceiling_service import RadialCeilingService, WallSegmentGeometry
from .panel_geometry_service import (
    PanelAngleSpec,
    PanelGeometryService,
    PanelTaperSpec,
)

# Panel generation
from .panel_generation import PanelGenerationService

__all__ = [
    # Core layout
    "CutListGenerator",
    "LayoutCalculator",
    "LayoutParameters",
    "MaterialEstimate",
    "MaterialEstimator",
    "Panel3DMapper",
    "RoomPanel3DMapper",
    # Room layout
    "RoomLayoutService",
    # Obstacle handling
    "ObstacleAwareLayoutService",
    "ObstacleCollisionService",
    # Geometry (FRD-11)
    "OutsideCornerService",
    "SkylightVoidService",
    "SlopedCeilingService",
    # Zone layout (FRD-22)
    "ZoneLayoutService",
    "ZoneStackLayoutResult",
    # Radial/panel geometry (FRD-23)
    "PanelAngleSpec",
    "PanelGeometryService",
    "PanelTaperSpec",
    "RadialCeilingService",
    "WallSegmentGeometry",
    # Panel generation
    "PanelGenerationService",
]
