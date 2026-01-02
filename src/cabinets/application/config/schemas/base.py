"""Base enums and shared models for cabinet configuration schemas.

This module contains all enums and basic shared models that are used across
multiple schema modules. It serves as the foundation for the schema hierarchy.

Note: Many enums are imported directly from the domain layer (value_objects.py)
and aliased here for backward compatibility. This consolidation (TD-07) eliminates
duplicate enum definitions while maintaining the same public API.
"""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

# Import domain enums directly - these now use (str, Enum) for JSON compatibility
from cabinets.domain.value_objects import (
    CountertopEdgeType,
    DeskType,
    EdgeTreatment,
    EquipmentType,
    GapPurpose,
    LightingLocation,
    LightingType,
    LoadCategory,
    MaterialType,
    MountingSystem,
    ObstacleType,
    OutletType,
    PedestalType,
    SectionType,
    SoundbarType,
    SpeakerType,
    VentilationPattern,
    WallType,
    ZoneMounting,
    ZonePreset,
    ZoneType,
)

# Supported schema versions for configuration files
# Version 1.0: Initial schema with basic cabinet configuration
# Version 1.1: Added room geometry, obstacles, and inside corner support (FRD-10)
# Version 1.2: Added sloped ceilings, skylights, and outside corners (FRD-11)
# Version 1.3: Added decorative elements (FRD-12)
# Version 1.4: Added bin packing configuration (FRD-13)
# Version 1.5: Added woodworking intelligence (FRD-14)
# Version 1.6: Added infrastructure integration (FRD-15)
# Version 1.7: Added per-format output configuration (FRD-16)
# Version 1.8: Added installation support (FRD-17)
# Version 1.9: Added LLM-based assembly instructions (FRD-20)
# Version 1.10: Added safety compliance configuration (FRD-21)
# Version 1.11: Added countertops and vertical zones (FRD-22)
SUPPORTED_VERSIONS: frozenset[str] = frozenset(
    {
        "1.0",
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "1.6",
        "1.7",
        "1.8",
        "1.9",
        "1.10",
        "1.11",
    }
)

# =============================================================================
# Backward Compatibility Aliases (TD-07)
# =============================================================================
# These aliases maintain backward compatibility for code that imports
# XxxConfig enums from this module. The underlying implementation now uses
# the domain enums directly, eliminating duplication.

ObstacleTypeConfig = ObstacleType
SectionTypeConfig = SectionType
WallTypeConfig = WallType
MountingSystemConfig = MountingSystem
LoadCategoryConfig = LoadCategory
LightingTypeConfig = LightingType
LightingLocationConfig = LightingLocation
OutletTypeConfig = OutletType
VentilationPatternConfig = VentilationPattern
ZoneTypeConfig = ZoneType
ZoneMountingConfig = ZoneMounting
GapPurposeConfig = GapPurpose
ZonePresetConfig = ZonePreset
CountertopEdgeConfig = CountertopEdgeType
DeskTypeConfig = DeskType
EdgeTreatmentConfig = EdgeTreatment
PedestalTypeConfig = PedestalType
EquipmentTypeConfig = EquipmentType
SoundbarTypeConfig = SoundbarType
SpeakerTypeConfig = SpeakerType


class HeightMode(str, Enum):
    """Height mode for cabinet sections.

    Determines how a section uses the available wall height:
    - FULL: Section spans the full wall height
    - LOWER: Section is placed below obstacles (e.g., under a window)
    - UPPER: Section is placed above obstacles (e.g., above a door)
    - AUTO: System automatically determines the best height mode
    """

    FULL = "full"
    LOWER = "lower"
    UPPER = "upper"
    AUTO = "auto"


# SectionTypeConfig is now an alias for domain SectionType (see above)


class ArchTypeConfig(str, Enum):
    """Arch type for configuration.

    Defines the curve geometry for arched cabinet openings.

    Attributes:
        FULL_ROUND: Semicircular arch where radius equals half the opening width.
        SEGMENTAL: Partial arc with specified radius larger than half width.
        ELLIPTICAL: Elliptical curve for a softer arch profile.
    """

    FULL_ROUND = "full_round"
    SEGMENTAL = "segmental"
    ELLIPTICAL = "elliptical"


class JoineryTypeConfig(str, Enum):
    """Joinery type for configuration.

    Defines how cabinet components are joined together.

    Attributes:
        DADO: Groove cut into one panel to receive another.
        RABBET: L-shaped cut along panel edge for back panel fit.
        POCKET_SCREW: Pocket hole joinery with angled screws.
        MORTISE_TENON: Traditional mortise and tenon joints.
        DOWEL: Dowel pin joinery for alignment and strength.
        BISCUIT: Football-shaped spline for panel alignment.
        BUTT: Simple butt joint with mechanical fasteners.
    """

    DADO = "dado"
    RABBET = "rabbet"
    POCKET_SCREW = "pocket_screw"
    MORTISE_TENON = "mortise_tenon"
    DOWEL = "dowel"
    BISCUIT = "biscuit"
    BUTT = "butt"


class EdgeProfileTypeConfig(str, Enum):
    """Edge profile type for configuration.

    Defines router bit profiles for visible edges.

    Attributes:
        CHAMFER: Angled flat cut at 45 degrees.
        ROUNDOVER: Rounded edge profile.
        OGEE: S-curve decorative profile.
        BEVEL: Angled cut at specified angle.
        COVE: Concave curved profile.
        ROMAN_OGEE: Complex S-curve with fillet.
    """

    CHAMFER = "chamfer"
    ROUNDOVER = "roundover"
    OGEE = "ogee"
    BEVEL = "bevel"
    COVE = "cove"
    ROMAN_OGEE = "roman_ogee"


# =============================================================================
# Infrastructure Integration Enums (FRD-15)
# =============================================================================
# LightingTypeConfig, LightingLocationConfig, OutletTypeConfig, and
# VentilationPatternConfig are now aliases for domain enums (see above)


class CableManagementTypeConfig(str, Enum):
    """Cable management type for routing cables through cabinets.

    Defines the method used to manage cables within cabinet structures.

    Attributes:
        GROMMET: Round cable pass-through grommet.
        CHANNEL: Linear cable routing channel.
    """

    GROMMET = "grommet"
    CHANNEL = "channel"


# VentilationPatternConfig is now an alias for domain VentilationPattern (see above)


class ConduitDirectionConfig(str, Enum):
    """Direction for electrical conduit routing.

    Defines the direction in which conduit exits from an electrical box.

    Attributes:
        TOP: Conduit exits from the top of the box.
        BOTTOM: Conduit exits from the bottom of the box.
        LEFT: Conduit exits from the left side of the box.
        RIGHT: Conduit exits from the right side of the box.
    """

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


# =============================================================================
# Installation Support Enums (FRD-17)
# =============================================================================
# WallTypeConfig, MountingSystemConfig, and LoadCategoryConfig are now
# aliases for domain enums (see above)


# =============================================================================
# Zone Stack Configuration Enums (FRD-22)
# =============================================================================
# ZoneTypeConfig, ZoneMountingConfig, GapPurposeConfig, ZonePresetConfig,
# and CountertopEdgeConfig are now aliases for domain enums (see above)


# =============================================================================
# Built-in Desk Enums (FRD-18)
# =============================================================================
# DeskTypeConfig, EdgeTreatmentConfig, and PedestalTypeConfig are now
# aliases for domain enums (see above)


class DeskMountingConfig(str, Enum):
    """Desktop mounting method.

    Defines how the desktop is supported.

    Attributes:
        PEDESTAL: Supported by desk pedestals.
        FLOATING: Wall-mounted with cleats.
        LEGS: Supported by desk legs.
    """

    PEDESTAL = "pedestal"
    FLOATING = "floating"
    LEGS = "legs"


# =============================================================================
# Entertainment Center Enums (FRD-19)
# =============================================================================
# EquipmentTypeConfig, SoundbarTypeConfig, and SpeakerTypeConfig are now
# aliases for domain enums (see above)


class MediaVentilationTypeConfig(str, Enum):
    """Ventilation type for media sections.

    Defines the ventilation approach for thermal management in
    enclosed media cabinet sections.

    Attributes:
        PASSIVE_REAR: Ventilation slots in rear panel.
        PASSIVE_BOTTOM: Ventilation slots in bottom panel.
        PASSIVE_SLOTS: Side ventilation slots.
        ACTIVE_FAN: Active cooling with fan mount.
        NONE: No ventilation (for non-heat-generating equipment).
    """

    PASSIVE_REAR = "passive_rear"
    PASSIVE_BOTTOM = "passive_bottom"
    PASSIVE_SLOTS = "passive_slots"
    ACTIVE_FAN = "active_fan"
    NONE = "none"


# SoundbarTypeConfig and SpeakerTypeConfig are now aliases for domain enums (see above)


class GrommetPositionConfig(str, Enum):
    """Grommet position for cable management.

    Defines where cable grommets are placed on equipment shelves.

    Attributes:
        CENTER_REAR: Centered at rear of shelf.
        LEFT_REAR: Left side at rear of shelf.
        RIGHT_REAR: Right side at rear of shelf.
        NONE: No grommet.
    """

    CENTER_REAR = "center_rear"
    LEFT_REAR = "left_rear"
    RIGHT_REAR = "right_rear"
    NONE = "none"


class EntertainmentLayoutTypeConfig(str, Enum):
    """Entertainment center layout type.

    Defines the overall layout configuration for entertainment centers.

    Attributes:
        CONSOLE: Low console under wall-mounted TV.
        WALL_UNIT: Full wall unit surrounding TV.
        FLOATING: Wall-mounted floating shelves.
        TOWER: Vertical tower units flanking TV.
    """

    CONSOLE = "console"
    WALL_UNIT = "wall_unit"
    FLOATING = "floating"
    TOWER = "tower"


class TVMountingConfig(str, Enum):
    """TV mounting type.

    Defines how the TV is mounted relative to the entertainment center.

    Attributes:
        WALL: TV is wall-mounted above/within the unit.
        STAND: TV sits on a stand on top of a cabinet section.
    """

    WALL = "wall"
    STAND = "stand"


# =============================================================================
# Bin Packing Enums (FRD-13)
# =============================================================================


class SplittablePanelType(str, Enum):
    """Panel types that can be split when oversized.

    These panel types are typically hidden or can have seams without
    affecting appearance or function.
    """

    BACK = "back"


# =============================================================================
# Shared Base Models
# =============================================================================


class ClearanceConfig(BaseModel):
    """Clearance distances around an obstacle.

    Specifies the minimum space that must be kept clear around an obstacle
    in each direction. All values are in inches and must be non-negative.

    Attributes:
        top: Clearance above the obstacle (default 0.0)
        bottom: Clearance below the obstacle (default 0.0)
        left: Clearance to the left of the obstacle (default 0.0)
        right: Clearance to the right of the obstacle (default 0.0)
    """

    model_config = ConfigDict(extra="forbid")

    top: float = Field(default=0.0, ge=0)
    bottom: float = Field(default=0.0, ge=0)
    left: float = Field(default=0.0, ge=0)
    right: float = Field(default=0.0, ge=0)


class MaterialConfig(BaseModel):
    """Material configuration for cabinet components.

    Attributes:
        type: The type of material (plywood, mdf, particle_board, solid_wood)
        thickness: Material thickness in inches (0.25 to 2.0)
    """

    model_config = ConfigDict(extra="forbid")

    type: MaterialType = MaterialType.PLYWOOD
    thickness: float = Field(default=0.75, ge=0.25, le=2.0)
