"""Configuration dataclasses for decorative components.

This module provides configuration objects for:
- Arch openings
- Scallop patterns
- Face frames
- Edge profiles
- Molding zones (crown, base, light rail)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .enums import ArchType, EdgeProfileType, JoineryType


@dataclass(frozen=True)
class ArchConfig:
    """Configuration for arched opening.

    Defines the geometry of an arched opening within a cabinet section.
    The arch is defined by its type, radius, and spring height.

    Attributes:
        arch_type: Type of arch curve (full_round, segmental, elliptical).
        radius: Radius in inches, or "auto" to calculate from opening width.
        spring_height: Height from section bottom where arch curve begins (inches).
    """

    arch_type: ArchType
    radius: float | Literal["auto"]
    spring_height: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.radius, (int, float)) and self.radius <= 0:
            raise ValueError("radius must be positive")
        if self.spring_height < 0:
            raise ValueError("spring_height must be non-negative")

    def calculate_radius(self, opening_width: float) -> float:
        """Calculate actual radius from opening width.

        For auto radius, calculates a semicircle radius (width / 2).

        Args:
            opening_width: Width of the opening in inches.

        Returns:
            Calculated radius in inches.
        """
        if self.radius == "auto":
            return opening_width / 2
        return self.radius


@dataclass(frozen=True)
class ScallopConfig:
    """Configuration for scalloped edge pattern.

    Defines a repeating scallop pattern for decorative edges on
    valances, shelf fronts, or aprons.

    Attributes:
        depth: Depth of each scallop in inches.
        width: Nominal width of each scallop in inches.
        count: Number of scallops, or "auto" to fit evenly.
    """

    depth: float
    width: float
    count: int | Literal["auto"]

    def __post_init__(self) -> None:
        if self.depth <= 0:
            raise ValueError("depth must be positive")
        if self.width <= 0:
            raise ValueError("width must be positive")
        if isinstance(self.count, int) and self.count < 1:
            raise ValueError("count must be at least 1")

    def calculate_count(self, piece_width: float) -> int:
        """Calculate scallop count for piece width.

        Args:
            piece_width: Total width of the piece in inches.

        Returns:
            Number of scallops that fit evenly.
        """
        if self.count == "auto":
            return max(1, int(piece_width / self.width))
        return self.count

    def calculate_actual_width(self, piece_width: float) -> float:
        """Calculate adjusted scallop width for even spacing.

        Args:
            piece_width: Total width of the piece in inches.

        Returns:
            Adjusted width per scallop for symmetric pattern.
        """
        count = self.calculate_count(piece_width)
        return piece_width / count


@dataclass(frozen=True)
class FaceFrameConfig:
    """Configuration for face frame construction.

    Face frames consist of vertical stiles and horizontal rails
    joined at corners using the specified joinery type.

    Attributes:
        stile_width: Width of vertical stiles in inches.
        rail_width: Width of horizontal rails in inches.
        joinery: Type of joint used at stile/rail connections.
        material_thickness: Thickness of face frame material in inches.
    """

    stile_width: float = 1.5
    rail_width: float = 1.5
    joinery: JoineryType = JoineryType.POCKET_SCREW
    material_thickness: float = 0.75

    def __post_init__(self) -> None:
        if self.stile_width <= 0:
            raise ValueError("stile_width must be positive")
        if self.rail_width <= 0:
            raise ValueError("rail_width must be positive")
        if self.material_thickness <= 0:
            raise ValueError("material_thickness must be positive")

    def opening_width(self, frame_width: float) -> float:
        """Calculate opening width inside frame.

        Args:
            frame_width: Total frame width in inches.

        Returns:
            Opening width between stiles in inches.
        """
        return frame_width - (2 * self.stile_width)

    def opening_height(self, frame_height: float) -> float:
        """Calculate opening height inside frame.

        Args:
            frame_height: Total frame height in inches.

        Returns:
            Opening height between rails in inches.
        """
        return frame_height - (2 * self.rail_width)


@dataclass(frozen=True)
class EdgeProfileConfig:
    """Configuration for edge routing profile.

    Defines the router profile applied to visible panel edges.

    Attributes:
        profile_type: Type of edge profile (chamfer, roundover, etc.).
        size: Profile size/radius in inches.
        edges: Specific edges to profile, or "auto" for all visible edges.
    """

    profile_type: EdgeProfileType
    size: float
    edges: tuple[str, ...] | Literal["auto"] = "auto"

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("size must be positive")
        if isinstance(self.edges, tuple):
            valid_edges = {"top", "bottom", "left", "right"}
            for edge in self.edges:
                if edge not in valid_edges:
                    raise ValueError(
                        f"invalid edge: {edge}. Must be one of {valid_edges}"
                    )

    def get_edges(self, visible_edges: list[str]) -> list[str]:
        """Return edges to profile.

        Args:
            visible_edges: List of edges that are visible/exposed.

        Returns:
            List of edges to apply the profile to.
        """
        if self.edges == "auto":
            return visible_edges
        return list(self.edges)


@dataclass(frozen=True)
class CrownMoldingZone:
    """Crown molding zone at cabinet top.

    Defines the zone reserved for crown molding installation,
    including setback for top panel and nailer strip generation.

    Attributes:
        height: Zone height for molding in inches.
        setback: Top panel setback distance in inches.
        nailer_width: Width of nailer strip in inches.
    """

    height: float = 3.0
    setback: float = 0.75
    nailer_width: float = 2.0

    def __post_init__(self) -> None:
        if self.height <= 0:
            raise ValueError("height must be positive")
        if self.setback <= 0:
            raise ValueError("setback must be positive")
        if self.nailer_width <= 0:
            raise ValueError("nailer_width must be positive")


@dataclass(frozen=True)
class BaseZone:
    """Base molding or toe kick zone.

    Defines the zone at cabinet bottom for toe kick or base molding.

    Attributes:
        height: Zone height in inches.
        setback: Toe kick depth/recess in inches.
        zone_type: Type of base treatment (toe_kick or base_molding).
    """

    height: float = 3.5
    setback: float = 3.0
    zone_type: Literal["toe_kick", "base_molding"] = "toe_kick"

    def __post_init__(self) -> None:
        if self.height <= 0:
            raise ValueError("height must be positive")
        if self.setback < 0:
            raise ValueError("setback must be non-negative")


@dataclass(frozen=True)
class LightRailZone:
    """Light rail zone under wall cabinets.

    Defines the zone for under-cabinet lighting installation.

    Attributes:
        height: Zone height in inches.
        setback: Light rail setback in inches.
        generate_strip: Whether to generate a light rail strip piece.
    """

    height: float = 1.5
    setback: float = 0.25
    generate_strip: bool = True

    def __post_init__(self) -> None:
        if self.height <= 0:
            raise ValueError("height must be positive")
        if self.setback < 0:
            raise ValueError("setback must be non-negative")
