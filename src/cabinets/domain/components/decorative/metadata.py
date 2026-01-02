"""Cut metadata dataclasses for decorative components.

This module provides metadata objects used in cut lists:
- ArchCutMetadata for arched pieces
- ScallopCutMetadata for scalloped pieces
- EdgeProfileMetadata for edge profiling

Also includes router bit recommendations for edge profiles.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import ArchType, EdgeProfileType


@dataclass(frozen=True)
class ArchCutMetadata:
    """Cut metadata for arched pieces.

    Extended information for cut list output about arch geometry.

    Attributes:
        arch_type: Type of arch curve.
        radius: Actual radius of the arch in inches.
        spring_height: Height where arch begins in inches.
        opening_width: Width of the arch opening in inches.
    """

    arch_type: ArchType
    radius: float
    spring_height: float
    opening_width: float


@dataclass(frozen=True)
class ScallopCutMetadata:
    """Cut metadata for scalloped pieces.

    Extended information for cut list output about scallop pattern.

    Attributes:
        scallop_depth: Depth of each scallop in inches.
        scallop_width: Actual width of each scallop in inches.
        scallop_count: Number of scallops.
        template_required: Whether a cutting template is needed.
    """

    scallop_depth: float
    scallop_width: float
    scallop_count: int
    template_required: bool = True


@dataclass(frozen=True)
class EdgeProfileMetadata:
    """Cut metadata for edge profiling.

    Extended information for cut list output about edge profiles.

    Attributes:
        profile_type: Type of edge profile.
        size: Profile size/radius in inches.
        edges: Edges to apply the profile to.
        router_bit: Optional suggested router bit description.
    """

    profile_type: EdgeProfileType
    size: float
    edges: tuple[str, ...]
    router_bit: str | None = None


# Router bit recommendations for each edge profile type
ROUTER_BIT_RECOMMENDATIONS: dict[EdgeProfileType, str] = {
    EdgeProfileType.CHAMFER: "45-degree chamfer bit",
    EdgeProfileType.ROUNDOVER: "Roundover bit (size = radius)",
    EdgeProfileType.OGEE: "Ogee bit",
    EdgeProfileType.BEVEL: "Bevel bit",
    EdgeProfileType.COVE: "Cove bit (size = radius)",
    EdgeProfileType.ROMAN_OGEE: "Roman ogee bit",
}
