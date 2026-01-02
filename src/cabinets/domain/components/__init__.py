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

from .context import ComponentContext as ComponentContext
from .corner import (
    BlindCornerComponent as BlindCornerComponent,
    CornerFootprint as CornerFootprint,
    DiagonalCornerComponent as DiagonalCornerComponent,
    LazySusanCornerComponent as LazySusanCornerComponent,
    calculate_blind_corner_footprint as calculate_blind_corner_footprint,
    calculate_diagonal_footprint as calculate_diagonal_footprint,
    calculate_lazy_susan_footprint as calculate_lazy_susan_footprint,
)
from .decorative import (
    ROUTER_BIT_RECOMMENDATIONS as ROUTER_BIT_RECOMMENDATIONS,
    ArchComponent as ArchComponent,
    ArchConfig as ArchConfig,
    ArchCutMetadata as ArchCutMetadata,
    ArchService as ArchService,
    ArchType as ArchType,
    BaseZone as BaseZone,
    CrownMoldingComponent as CrownMoldingComponent,
    CrownMoldingZone as CrownMoldingZone,
    EdgeProfileComponent as EdgeProfileComponent,
    EdgeProfileConfig as EdgeProfileConfig,
    EdgeProfileMetadata as EdgeProfileMetadata,
    EdgeProfileType as EdgeProfileType,
    FaceFrameComponent as FaceFrameComponent,
    FaceFrameConfig as FaceFrameConfig,
    JoineryType as JoineryType,
    LightRailComponent as LightRailComponent,
    LightRailZone as LightRailZone,
    MoldingZoneService as MoldingZoneService,
    ScallopComponent as ScallopComponent,
    ScallopConfig as ScallopConfig,
    ScallopCutMetadata as ScallopCutMetadata,
    ScallopService as ScallopService,
    ToeKickComponent as ToeKickComponent,
    apply_edge_profile_metadata as apply_edge_profile_metadata,
    detect_visible_edges as detect_visible_edges,
    validate_edge_profile as validate_edge_profile,
)
from .desk import (
    ADA_KNEE_CLEARANCE_WIDTH as ADA_KNEE_CLEARANCE_WIDTH,
    GROMMET_SIZES as GROMMET_SIZES,
    L_SHAPED_CORNER_POST_WIDTH as L_SHAPED_CORNER_POST_WIDTH,
    L_SHAPED_MIN_SURFACE_WIDTH as L_SHAPED_MIN_SURFACE_WIDTH,
    L_SHAPED_WARNING_THRESHOLD as L_SHAPED_WARNING_THRESHOLD,
    MIN_KNEE_CLEARANCE_DEPTH as MIN_KNEE_CLEARANCE_DEPTH,
    MIN_KNEE_CLEARANCE_HEIGHT as MIN_KNEE_CLEARANCE_HEIGHT,
    MIN_KNEE_CLEARANCE_WIDTH as MIN_KNEE_CLEARANCE_WIDTH,
    SITTING_DESK_HEIGHT_DEFAULT as SITTING_DESK_HEIGHT_DEFAULT,
    SITTING_DESK_HEIGHT_MAX as SITTING_DESK_HEIGHT_MAX,
    SITTING_DESK_HEIGHT_MIN as SITTING_DESK_HEIGHT_MIN,
    STANDING_DESK_HEIGHT_DEFAULT as STANDING_DESK_HEIGHT_DEFAULT,
    STANDING_DESK_HEIGHT_MAX as STANDING_DESK_HEIGHT_MAX,
    STANDING_DESK_HEIGHT_MIN as STANDING_DESK_HEIGHT_MIN,
    CornerConnectionType as CornerConnectionType,
    DeskHutchComponent as DeskHutchComponent,
    DeskPedestalComponent as DeskPedestalComponent,
    DeskSurfaceComponent as DeskSurfaceComponent,
    GrommetSpec as DeskGrommetSpec,
    KeyboardTrayComponent as KeyboardTrayComponent,
    LShapedDeskComponent as LShapedDeskComponent,
    LShapedDeskConfiguration as LShapedDeskConfiguration,
    MonitorShelfComponent as MonitorShelfComponent,
)
from .infrastructure import (
    CableChannelSpec as CableChannelSpec,
    CableManagementComponent as CableManagementComponent,
    ElectricalComponent as ElectricalComponent,
    GrommetSpec as GrommetSpec,
    LightingComponent as LightingComponent,
    LightingSpec as LightingSpec,
    OutletSpec as OutletSpec,
    VentilationComponent as VentilationComponent,
    VentilationSpec as VentilationSpec,
    WireRouteSpec as WireRouteSpec,
)
from .countertop import (
    DEFAULT_THICKNESS as COUNTERTOP_DEFAULT_THICKNESS,
    MAX_SUPPORTED_OVERHANG as MAX_SUPPORTED_OVERHANG,
    MAX_THICKNESS as COUNTERTOP_MAX_THICKNESS,
    MAX_UNSUPPORTED_OVERHANG as MAX_UNSUPPORTED_OVERHANG,
    MIN_BRACKET_DEPTH as MIN_BRACKET_DEPTH,
    MIN_BRACKET_WIDTH as MIN_BRACKET_WIDTH,
    MIN_THICKNESS as COUNTERTOP_MIN_THICKNESS,
    SUPPORT_BRACKET_SPACING as SUPPORT_BRACKET_SPACING,
    CountertopSurfaceComponent as CountertopSurfaceComponent,
    OverhangSpec as OverhangSpec,
)
from .media import (
    EQUIPMENT_PRESETS as EQUIPMENT_PRESETS,
    HEAT_GENERATING_EQUIPMENT as HEAT_GENERATING_EQUIPMENT,
    HEAT_SOURCE_CLEARANCE as HEAT_SOURCE_CLEARANCE,
    MIN_EQUIPMENT_DEPTH as MIN_EQUIPMENT_DEPTH,
    MIN_VERTICAL_CLEARANCE as MIN_VERTICAL_CLEARANCE,
    RECOMMENDED_EQUIPMENT_DEPTH as RECOMMENDED_EQUIPMENT_DEPTH,
    EquipmentShelfComponent as EquipmentShelfComponent,
    EquipmentSpec as EquipmentSpec,
    SoundbarShelfComponent as SoundbarShelfComponent,
    SpeakerAlcoveComponent as SpeakerAlcoveComponent,
    VentilatedSectionComponent as VentilatedSectionComponent,
    VentilationSpec as MediaVentilationSpec,
)
from .protocol import Component as Component
from .window_seat import (
    ACCESS_DRAWERS as ACCESS_DRAWERS,
    ACCESS_FRONT_DOORS as ACCESS_FRONT_DOORS,
    ACCESS_HINGED_TOP as ACCESS_HINGED_TOP,
    DEFAULT_SEAT_DEPTH as DEFAULT_SEAT_DEPTH,
    DEFAULT_SEAT_HEIGHT as DEFAULT_SEAT_HEIGHT,
    MAX_SEAT_HEIGHT as MAX_SEAT_HEIGHT,
    MIN_SEAT_DEPTH as MIN_SEAT_DEPTH,
    MIN_SEAT_HEIGHT as MIN_SEAT_HEIGHT,
    MIN_SEAT_WIDTH as MIN_SEAT_WIDTH,
    SEAT_THICKNESS as SEAT_THICKNESS,
    VALID_ACCESS_TYPES as VALID_ACCESS_TYPES,
    MullionFillerComponent as MullionFillerComponent,
    WindowSeatStorageComponent as WindowSeatStorageComponent,
)
from .registry import (
    ComponentRegistry as ComponentRegistry,
    component_registry as component_registry,
)
from .results import (
    GenerationResult as GenerationResult,
    HardwareItem as HardwareItem,
    ValidationResult as ValidationResult,
)

# Explicit __all__ for re-exports including aliases
__all__ = [
    # Context and results
    "ComponentContext",
    "GenerationResult",
    "HardwareItem",
    "ValidationResult",
    # Registry
    "ComponentRegistry",
    "component_registry",
    # Protocol
    "Component",
    # Corner components
    "BlindCornerComponent",
    "CornerFootprint",
    "DiagonalCornerComponent",
    "LazySusanCornerComponent",
    "calculate_blind_corner_footprint",
    "calculate_diagonal_footprint",
    "calculate_lazy_susan_footprint",
    # Decorative components
    "ROUTER_BIT_RECOMMENDATIONS",
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
    "ScallopComponent",
    "ScallopConfig",
    "ScallopCutMetadata",
    "ScallopService",
    "ToeKickComponent",
    "apply_edge_profile_metadata",
    "detect_visible_edges",
    "validate_edge_profile",
    # Desk components and constants
    "ADA_KNEE_CLEARANCE_WIDTH",
    "GROMMET_SIZES",
    "L_SHAPED_CORNER_POST_WIDTH",
    "L_SHAPED_MIN_SURFACE_WIDTH",
    "L_SHAPED_WARNING_THRESHOLD",
    "MIN_KNEE_CLEARANCE_DEPTH",
    "MIN_KNEE_CLEARANCE_HEIGHT",
    "MIN_KNEE_CLEARANCE_WIDTH",
    "SITTING_DESK_HEIGHT_DEFAULT",
    "SITTING_DESK_HEIGHT_MAX",
    "SITTING_DESK_HEIGHT_MIN",
    "STANDING_DESK_HEIGHT_DEFAULT",
    "STANDING_DESK_HEIGHT_MAX",
    "STANDING_DESK_HEIGHT_MIN",
    "CornerConnectionType",
    "DeskHutchComponent",
    "DeskPedestalComponent",
    "DeskSurfaceComponent",
    "DeskGrommetSpec",  # Alias for desk.GrommetSpec
    "KeyboardTrayComponent",
    "LShapedDeskComponent",
    "LShapedDeskConfiguration",
    "MonitorShelfComponent",
    # Infrastructure components
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
    # Countertop components and constants
    "COUNTERTOP_DEFAULT_THICKNESS",  # Alias
    "COUNTERTOP_MAX_THICKNESS",  # Alias
    "COUNTERTOP_MIN_THICKNESS",  # Alias
    "MAX_SUPPORTED_OVERHANG",
    "MAX_UNSUPPORTED_OVERHANG",
    "MIN_BRACKET_DEPTH",
    "MIN_BRACKET_WIDTH",
    "SUPPORT_BRACKET_SPACING",
    "CountertopSurfaceComponent",
    "OverhangSpec",
    # Media components and constants
    "EQUIPMENT_PRESETS",
    "HEAT_GENERATING_EQUIPMENT",
    "HEAT_SOURCE_CLEARANCE",
    "MIN_EQUIPMENT_DEPTH",
    "MIN_VERTICAL_CLEARANCE",
    "RECOMMENDED_EQUIPMENT_DEPTH",
    "EquipmentShelfComponent",
    "EquipmentSpec",
    "SoundbarShelfComponent",
    "SpeakerAlcoveComponent",
    "VentilatedSectionComponent",
    "MediaVentilationSpec",  # Alias for media.VentilationSpec
    # Window seat components and constants
    "ACCESS_DRAWERS",
    "ACCESS_FRONT_DOORS",
    "ACCESS_HINGED_TOP",
    "DEFAULT_SEAT_DEPTH",
    "DEFAULT_SEAT_HEIGHT",
    "MAX_SEAT_HEIGHT",
    "MIN_SEAT_DEPTH",
    "MIN_SEAT_HEIGHT",
    "MIN_SEAT_WIDTH",
    "SEAT_THICKNESS",
    "VALID_ACCESS_TYPES",
    "MullionFillerComponent",
    "WindowSeatStorageComponent",
    # Functions
    "register_all_components",
    "ensure_components_registered",
    "get_registry",
]

# Component registration tracking
_components_registered = False


def register_all_components() -> None:
    """Explicitly register all built-in components.

    This function imports all component modules, which triggers their
    @component_registry decorator registration. Call this once at
    application startup.

    Note: Some modules (corner, infrastructure, media, decorative, desk,
    countertop, window_seat) are also imported above for their exported
    classes and constants. Re-importing them here is safe and ensures
    registration happens.
    """
    from . import (  # noqa: F401
        corner,
        countertop,
        cubby,
        decorative,
        desk,
        door,
        drawer,
        infrastructure,
        media,
        shelf,
        window_seat,
    )
    # Modules self-register via decorators when imported


def ensure_components_registered() -> None:
    """Ensure components are registered (idempotent).

    Safe to call multiple times - registration only happens once.
    """
    global _components_registered
    if not _components_registered:
        register_all_components()
        _components_registered = True


def get_registry() -> "ComponentRegistry":
    """Get the component registry, ensuring defaults are registered.

    Returns:
        The singleton ComponentRegistry instance with all built-in
        components registered.
    """
    ensure_components_registered()
    return ComponentRegistry()


# Maintain backward compatibility - auto-register on import
register_all_components()
_components_registered = True
