"""Decorative element components and configurations.

This package provides components for cabinet decorative elements including:
- Face frames with stile/rail construction
- Arch tops for arched openings
- Scalloped edges for valances and aprons
- Edge profiles for visible edges
- Molding zones (crown, base, light rail)

All public symbols are re-exported here for backwards compatibility.
"""

from __future__ import annotations

# Enums
from .enums import ArchType, EdgeProfileType, JoineryType

# Configuration dataclasses
from .configs import (
    ArchConfig,
    BaseZone,
    CrownMoldingZone,
    EdgeProfileConfig,
    FaceFrameConfig,
    LightRailZone,
    ScallopConfig,
)

# Cut metadata dataclasses
from .metadata import (
    ROUTER_BIT_RECOMMENDATIONS,
    ArchCutMetadata,
    EdgeProfileMetadata,
    ScallopCutMetadata,
)

# Edge profile helpers
from .edge_profile import (
    EdgeProfileComponent,
    apply_edge_profile_metadata,
    detect_visible_edges,
    validate_edge_profile,
)

# Arch service and component
from .arch import ArchComponent, ArchService

# Scallop service and component
from .scallop import ScallopComponent, ScallopService

# Face frame component
from .face_frame import FaceFrameComponent

# Molding zone service and components
from .molding_zones import (
    CrownMoldingComponent,
    LightRailComponent,
    MoldingZoneService,
    ToeKickComponent,
)

__all__ = [
    # Enums
    "ArchType",
    "EdgeProfileType",
    "JoineryType",
    # Configuration dataclasses
    "ArchConfig",
    "BaseZone",
    "CrownMoldingZone",
    "EdgeProfileConfig",
    "FaceFrameConfig",
    "LightRailZone",
    "ScallopConfig",
    # Cut metadata
    "ArchCutMetadata",
    "EdgeProfileMetadata",
    "ROUTER_BIT_RECOMMENDATIONS",
    "ScallopCutMetadata",
    # Edge profile helpers
    "apply_edge_profile_metadata",
    "detect_visible_edges",
    "validate_edge_profile",
    # Services
    "ArchService",
    "MoldingZoneService",
    "ScallopService",
    # Components
    "ArchComponent",
    "CrownMoldingComponent",
    "EdgeProfileComponent",
    "FaceFrameComponent",
    "LightRailComponent",
    "ScallopComponent",
    "ToeKickComponent",
]
