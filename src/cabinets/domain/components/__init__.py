"""Component registry architecture for cabinet components.

This package provides the infrastructure for registering and generating
cabinet components (shelves, dividers, doors, drawers, etc.) in a
pluggable, extensible way.

Phase 1: Core Infrastructure
- ComponentContext: Immutable context for component generation
- ValidationResult: Result of component validation
- GenerationResult: Result of component generation
- HardwareItem: Hardware required by a component

Phase 2: Protocol & Registration
- Component: Protocol defining the component interface
- ComponentRegistry: Singleton registry for component types
- component_registry: The singleton registry instance

Corner Cabinet Support:
- CornerFootprint: Space consumed by corner cabinet on each wall
- calculate_lazy_susan_footprint: Footprint for rotating shelf corner cabinets
- calculate_blind_corner_footprint: Footprint for blind corner cabinets
- calculate_diagonal_footprint: Footprint for diagonal face corner cabinets

Infrastructure Integration (FRD-15):
- LightingComponent: LED strips and puck lights
- ElectricalComponent: Outlet cutouts
- CableManagementComponent: Cable grommets
- VentilationComponent: Ventilation patterns
"""

from .context import ComponentContext
from .corner import (
    BlindCornerComponent,
    CornerFootprint,
    DiagonalCornerComponent,
    LazySusanCornerComponent,
    calculate_blind_corner_footprint,
    calculate_diagonal_footprint,
    calculate_lazy_susan_footprint,
)
from .decorative import (
    ROUTER_BIT_RECOMMENDATIONS,
    ArchComponent,
    ArchConfig,
    ArchCutMetadata,
    ArchService,
    ArchType,
    BaseZone,
    CrownMoldingComponent,
    CrownMoldingZone,
    EdgeProfileComponent,
    EdgeProfileConfig,
    EdgeProfileMetadata,
    EdgeProfileType,
    FaceFrameComponent,
    FaceFrameConfig,
    JoineryType,
    LightRailComponent,
    LightRailZone,
    MoldingZoneService,
    ScallopComponent,
    ScallopConfig,
    ScallopCutMetadata,
    ScallopService,
    ToeKickComponent,
    apply_edge_profile_metadata,
    detect_visible_edges,
    validate_edge_profile,
)
from .desk import (
    ADA_KNEE_CLEARANCE_WIDTH,
    GROMMET_SIZES,
    L_SHAPED_CORNER_POST_WIDTH,
    L_SHAPED_MIN_SURFACE_WIDTH,
    L_SHAPED_WARNING_THRESHOLD,
    MIN_KNEE_CLEARANCE_DEPTH,
    MIN_KNEE_CLEARANCE_HEIGHT,
    MIN_KNEE_CLEARANCE_WIDTH,
    SITTING_DESK_HEIGHT_DEFAULT,
    SITTING_DESK_HEIGHT_MAX,
    SITTING_DESK_HEIGHT_MIN,
    STANDING_DESK_HEIGHT_DEFAULT,
    STANDING_DESK_HEIGHT_MAX,
    STANDING_DESK_HEIGHT_MIN,
    CornerConnectionType,
    DeskHutchComponent,
    DeskPedestalComponent,
    DeskSurfaceComponent,
    GrommetSpec as DeskGrommetSpec,
    KeyboardTrayComponent,
    LShapedDeskComponent,
    LShapedDeskConfiguration,
    MonitorShelfComponent,
)
from .infrastructure import (
    CableChannelSpec,
    CableManagementComponent,
    ElectricalComponent,
    GrommetSpec,
    LightingComponent,
    LightingSpec,
    OutletSpec,
    VentilationComponent,
    VentilationSpec,
    WireRouteSpec,
)
from .media import (
    EQUIPMENT_PRESETS,
    HEAT_GENERATING_EQUIPMENT,
    HEAT_SOURCE_CLEARANCE,
    MIN_EQUIPMENT_DEPTH,
    MIN_VERTICAL_CLEARANCE,
    RECOMMENDED_EQUIPMENT_DEPTH,
    EquipmentShelfComponent,
    EquipmentSpec,
    SoundbarShelfComponent,
    SpeakerAlcoveComponent,
    VentilatedSectionComponent,
    VentilationSpec as MediaVentilationSpec,
)
from .protocol import Component
from .registry import ComponentRegistry, component_registry
from .results import GenerationResult, HardwareItem, ValidationResult

__all__ = [
    # Decorative configs and enums (FRD-12)
    "ArchComponent",
    "ArchConfig",
    "ArchCutMetadata",
    "ArchService",
    "ArchType",
    "BaseZone",
    "CrownMoldingComponent",
    "CrownMoldingZone",
    "EdgeProfileComponent",
    "EdgeProfileConfig",
    "EdgeProfileMetadata",
    "EdgeProfileType",
    "FaceFrameComponent",
    "FaceFrameConfig",
    "JoineryType",
    "LightRailComponent",
    "LightRailZone",
    "MoldingZoneService",
    "ROUTER_BIT_RECOMMENDATIONS",
    "ScallopComponent",
    "ScallopConfig",
    "ScallopCutMetadata",
    "ScallopService",
    "ToeKickComponent",
    "apply_edge_profile_metadata",
    "detect_visible_edges",
    "validate_edge_profile",
    # Desk components (FRD-18)
    "ADA_KNEE_CLEARANCE_WIDTH",
    "CornerConnectionType",
    "DeskGrommetSpec",
    "DeskHutchComponent",
    "DeskPedestalComponent",
    "DeskSurfaceComponent",
    "GROMMET_SIZES",
    "KeyboardTrayComponent",
    "L_SHAPED_CORNER_POST_WIDTH",
    "L_SHAPED_MIN_SURFACE_WIDTH",
    "L_SHAPED_WARNING_THRESHOLD",
    "LShapedDeskComponent",
    "LShapedDeskConfiguration",
    "MIN_KNEE_CLEARANCE_DEPTH",
    "MIN_KNEE_CLEARANCE_HEIGHT",
    "MIN_KNEE_CLEARANCE_WIDTH",
    "MonitorShelfComponent",
    "SITTING_DESK_HEIGHT_DEFAULT",
    "SITTING_DESK_HEIGHT_MAX",
    "SITTING_DESK_HEIGHT_MIN",
    "STANDING_DESK_HEIGHT_DEFAULT",
    "STANDING_DESK_HEIGHT_MAX",
    "STANDING_DESK_HEIGHT_MIN",
    # Infrastructure integration (FRD-15)
    "CableChannelSpec",
    "CableManagementComponent",
    "ElectricalComponent",
    "GrommetSpec",
    "LightingComponent",
    "LightingSpec",
    "OutletSpec",
    "VentilationComponent",
    "VentilationSpec",
    "WireRouteSpec",
    # Media components (FRD-19)
    "EQUIPMENT_PRESETS",
    "EquipmentShelfComponent",
    "EquipmentSpec",
    "HEAT_GENERATING_EQUIPMENT",
    "HEAT_SOURCE_CLEARANCE",
    "MIN_EQUIPMENT_DEPTH",
    "MIN_VERTICAL_CLEARANCE",
    "MediaVentilationSpec",
    "RECOMMENDED_EQUIPMENT_DEPTH",
    "SoundbarShelfComponent",
    "SpeakerAlcoveComponent",
    "VentilatedSectionComponent",
    # Core component infrastructure
    "BlindCornerComponent",
    "Component",
    "ComponentContext",
    "ComponentRegistry",
    "CornerFootprint",
    "DiagonalCornerComponent",
    "GenerationResult",
    "HardwareItem",
    "LazySusanCornerComponent",
    "ValidationResult",
    "calculate_blind_corner_footprint",
    "calculate_diagonal_footprint",
    "calculate_lazy_susan_footprint",
    "component_registry",
]

# Import components to trigger registration
# Note: corner module is imported above to get CornerFootprint and LazySusanCornerComponent
# Note: infrastructure module is imported above for spec classes and components
# Note: media module is imported above for equipment specs and components
from . import corner, cubby, decorative, desk, door, drawer, infrastructure, media, shelf
