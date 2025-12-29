"""Domain services for cabinet layout and calculations.

This package provides all domain services for cabinet generation, including:
- Layout calculation and panel generation
- Room-aware layout with obstacle handling
- Woodworking intelligence (joinery, span limits, hardware)
- Installation support (mounting, cleats, hardware)
"""

# Re-export everything from legacy services module
from ._legacy import (
    CutListGenerator,
    LayoutCalculator,
    LayoutParameters,
    MaterialEstimate,
    MaterialEstimator,
    ObstacleAwareLayoutService,
    ObstacleCollisionService,
    OutsideCornerService,
    Panel3DMapper,
    RoomLayoutService,
    RoomPanel3DMapper,
    SkylightVoidService,
    SlopedCeilingService,
)

# Export installation support module (FRD-17)
from .installation import (
    CleatSpec,
    InstallationConfig,
    InstallationPlan,
    InstallationService,
    StudHitAnalysis,
    WeightEstimate,
)

# Export woodworking intelligence module
from .woodworking import (
    MATERIAL_MODULUS,
    MAX_DEFLECTION_RATIO,
    SAFETY_FACTOR,
    SPAN_LIMITS,
    ConnectionJoinery,
    HardwareList,
    JointSpec,
    SpanWarning,
    WeightCapacity,
    WoodworkingConfig,
    WoodworkingIntelligence,
    get_max_span,
)

# Export entertainment center layout service (FRD-19)
from .entertainment_center import (
    CableChasePosition,
    EntertainmentCenterLayoutService,
    TVIntegration,
    TVZone,
)

__all__ = [
    # Layout and generation
    "LayoutParameters",
    "LayoutCalculator",
    "CutListGenerator",
    "MaterialEstimate",
    "MaterialEstimator",
    "Panel3DMapper",
    # Room-aware layout
    "RoomLayoutService",
    "RoomPanel3DMapper",
    # Obstacle handling
    "ObstacleCollisionService",
    "ObstacleAwareLayoutService",
    # FRD-11 Advanced geometry
    "SlopedCeilingService",
    "SkylightVoidService",
    "OutsideCornerService",
    # Woodworking intelligence (FRD-14)
    "ConnectionJoinery",
    "HardwareList",
    "JointSpec",
    "MATERIAL_MODULUS",
    "MAX_DEFLECTION_RATIO",
    "SAFETY_FACTOR",
    "SPAN_LIMITS",
    "SpanWarning",
    "WeightCapacity",
    "WoodworkingConfig",
    "WoodworkingIntelligence",
    "get_max_span",
    # Installation support (FRD-17)
    "CleatSpec",
    "InstallationConfig",
    "InstallationPlan",
    "InstallationService",
    "StudHitAnalysis",
    "WeightEstimate",
    # Entertainment center layout (FRD-19)
    "CableChasePosition",
    "EntertainmentCenterLayoutService",
    "TVIntegration",
    "TVZone",
]
