"""Decorative element components and configurations.

This module provides components for cabinet decorative elements including:
- Face frames with stile/rail construction
- Arch tops for arched openings
- Scalloped edges for valances and aprons
- Edge profiles for visible edges
- Molding zones (crown, base, light rail)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


# --- Enums ---


class ArchType(str, Enum):
    """Types of arched openings.

    Defines the curve geometry for arched cabinet openings.

    Attributes:
        FULL_ROUND: Semicircular arch (180 degrees).
        SEGMENTAL: Partial arc, less than semicircle.
        ELLIPTICAL: Elliptical curve, wider than tall.
    """

    FULL_ROUND = "full_round"
    SEGMENTAL = "segmental"
    ELLIPTICAL = "elliptical"


class JoineryType(str, Enum):
    """Types of joinery for face frame construction.

    Defines how stiles and rails are joined together.

    Attributes:
        POCKET_SCREW: Angled screws through pocket holes.
        MORTISE_TENON: Traditional mortise and tenon joint.
        DOWEL: Dowel pin joints.
    """

    POCKET_SCREW = "pocket_screw"
    MORTISE_TENON = "mortise_tenon"
    DOWEL = "dowel"


class EdgeProfileType(str, Enum):
    """Types of edge profiles for visible panel edges.

    Defines router bit profiles applied to exposed edges.

    Attributes:
        CHAMFER: 45-degree flat cut on edge corner.
        ROUNDOVER: Rounded edge with specified radius.
        OGEE: S-curve decorative profile.
        BEVEL: Angled flat cut (similar to chamfer but full edge).
        COVE: Concave curved cut.
        ROMAN_OGEE: Classic decorative S-curve with fillet.
    """

    CHAMFER = "chamfer"
    ROUNDOVER = "roundover"
    OGEE = "ogee"
    BEVEL = "bevel"
    COVE = "cove"
    ROMAN_OGEE = "roman_ogee"


# --- Config Dataclasses ---


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


# --- Cut Metadata Dataclasses ---


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


# --- Router Bit Recommendations ---

ROUTER_BIT_RECOMMENDATIONS: dict[EdgeProfileType, str] = {
    EdgeProfileType.CHAMFER: "45-degree chamfer bit",
    EdgeProfileType.ROUNDOVER: "Roundover bit (size = radius)",
    EdgeProfileType.OGEE: "Ogee bit",
    EdgeProfileType.BEVEL: "Bevel bit",
    EdgeProfileType.COVE: "Cove bit (size = radius)",
    EdgeProfileType.ROMAN_OGEE: "Roman ogee bit",
}


# --- Edge Profile Helper Functions ---

import math
from typing import Any

from ..entities import Panel
from ..value_objects import MaterialSpec, PanelType, Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult


# --- Arch Service ---


class ArchService:
    """Service for arch geometry calculations.

    Provides methods for calculating arch dimensions, curves,
    and related geometry for arched cabinet openings.

    Supports three arch types:
    - FULL_ROUND (semicircle): radius = width/2
    - SEGMENTAL (partial arc): radius > width/2, shallower curve
    - ELLIPTICAL: semi-major axis a = width/2, semi-minor axis b = radius
    """

    def calculate_header_height(
        self,
        config: ArchConfig,
        opening_width: float,
    ) -> float:
        """Calculate the height of the arch header panel.

        The header height is the rectangular stock height needed
        to cut the arch shape from.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.

        Returns:
            Height of header panel in inches.
        """
        radius = config.calculate_radius(opening_width)

        if config.arch_type == ArchType.FULL_ROUND:
            # Full semicircle: height = radius + spring height
            return radius + config.spring_height

        elif config.arch_type == ArchType.SEGMENTAL:
            # Segmental: calculate arc rise
            half_width = opening_width / 2
            if radius < half_width:
                # Invalid: radius too small
                return config.spring_height
            arc_rise = radius - math.sqrt(radius**2 - half_width**2)
            return arc_rise + config.spring_height

        elif config.arch_type == ArchType.ELLIPTICAL:
            # Elliptical: radius is the semi-minor axis (height)
            return radius + config.spring_height

        return config.spring_height

    def calculate_arc_rise(
        self,
        config: ArchConfig,
        opening_width: float,
    ) -> float:
        """Calculate the rise of the arch curve only (without spring height).

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.

        Returns:
            Arc rise in inches (0 for flat, max for semicircle).
        """
        radius = config.calculate_radius(opening_width)
        half_width = opening_width / 2

        if config.arch_type == ArchType.FULL_ROUND:
            return radius  # Semicircle rise = radius

        elif config.arch_type == ArchType.SEGMENTAL:
            if radius < half_width:
                return 0.0  # Invalid configuration
            return radius - math.sqrt(radius**2 - half_width**2)

        elif config.arch_type == ArchType.ELLIPTICAL:
            return radius  # Semi-minor axis is the rise

        return 0.0

    def calculate_upright_extension(
        self,
        config: ArchConfig,
        opening_width: float,
        upright_position: float,
    ) -> float:
        """Calculate how much an upright extends into the arch area.

        Used to determine the height of side panels that meet the arch.
        For a point at distance x from center, calculates the y-value
        (height above spring line) at that position.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.
            upright_position: Distance from arch center to upright in inches.
                             Use 0 for center, positive for right, negative for left.

        Returns:
            Height extension above spring line in inches (includes spring_height).
        """
        radius = config.calculate_radius(opening_width)
        half_width = opening_width / 2

        # If upright is outside the arch, return spring height only
        if abs(upright_position) >= half_width:
            return config.spring_height

        if config.arch_type == ArchType.FULL_ROUND:
            # Semicircle: y = sqrt(r^2 - x^2)
            y = math.sqrt(radius**2 - upright_position**2)
            return y + config.spring_height

        elif config.arch_type == ArchType.SEGMENTAL:
            if radius < half_width:
                return config.spring_height
            # Segmental arc with center below opening
            # Arc is part of a circle with larger radius
            # y = sqrt(r^2 - x^2) - (r - arc_rise)
            arc_rise = radius - math.sqrt(radius**2 - half_width**2)
            y = math.sqrt(radius**2 - upright_position**2) - (radius - arc_rise)
            return max(0.0, y) + config.spring_height

        elif config.arch_type == ArchType.ELLIPTICAL:
            # Ellipse: y = b * sqrt(1 - (x/a)^2)
            a = half_width  # Semi-major axis (horizontal)
            b = radius  # Semi-minor axis (vertical, height)
            y = b * math.sqrt(1 - (upright_position / a) ** 2)
            return y + config.spring_height

        return config.spring_height

    def generate_curve_points(
        self,
        config: ArchConfig,
        opening_width: float,
        num_points: int = 21,
    ) -> list[tuple[float, float]]:
        """Generate points along the arch curve for templates.

        Points are relative to the arch center at the spring line.
        The x-coordinates range from -opening_width/2 to +opening_width/2.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.
            num_points: Number of points to generate (odd for center point).

        Returns:
            List of (x, y) tuples from left to right.
        """
        half_width = opening_width / 2
        points: list[tuple[float, float]] = []

        for i in range(num_points):
            x = -half_width + (opening_width * i / (num_points - 1))
            y = self.calculate_upright_extension(config, opening_width, x)
            points.append((x, y))

        return points

    def create_cut_metadata(
        self,
        config: ArchConfig,
        opening_width: float,
    ) -> ArchCutMetadata:
        """Create cut metadata for arch header.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.

        Returns:
            ArchCutMetadata for cut list output.
        """
        return ArchCutMetadata(
            arch_type=config.arch_type,
            radius=config.calculate_radius(opening_width),
            spring_height=config.spring_height,
            opening_width=opening_width,
        )


# --- Scallop Service ---


class ScallopService:
    """Service for scallop pattern calculations.

    Provides methods for calculating scallop patterns, generating
    template specifications, and ensuring symmetric layouts.
    """

    def calculate_pattern(
        self,
        config: ScallopConfig,
        piece_width: float,
    ) -> ScallopCutMetadata:
        """Calculate scallop pattern for a piece.

        Determines the number of scallops and adjusted width for
        symmetric pattern on the given piece width.

        Args:
            config: Scallop configuration.
            piece_width: Width of the piece to scallop in inches.

        Returns:
            ScallopCutMetadata with pattern specifications.
        """
        count = config.calculate_count(piece_width)
        actual_width = config.calculate_actual_width(piece_width)

        return ScallopCutMetadata(
            scallop_depth=config.depth,
            scallop_width=actual_width,
            scallop_count=count,
            template_required=True,
        )

    def generate_template_info(
        self,
        metadata: ScallopCutMetadata,
    ) -> str:
        """Generate template description for cut list.

        Creates a human-readable description of the scallop template
        needed to cut the pattern.

        Args:
            metadata: Scallop cut metadata.

        Returns:
            Template description string.
        """
        return (
            f"Scallop template: {metadata.scallop_count} scallops, "
            f'{metadata.scallop_width:.2f}" wide x '
            f'{metadata.scallop_depth:.2f}" deep each'
        )

    def calculate_scallop_centers(
        self,
        metadata: ScallopCutMetadata,
        piece_width: float,
    ) -> list[float]:
        """Calculate X positions of scallop centers.

        Centers are evenly distributed across piece width,
        ensuring symmetric pattern.

        Args:
            metadata: Scallop cut metadata.
            piece_width: Width of the piece in inches.

        Returns:
            List of X positions from left edge.
        """
        centers: list[float] = []
        half_width = metadata.scallop_width / 2

        for i in range(metadata.scallop_count):
            center = half_width + (i * metadata.scallop_width)
            centers.append(center)

        return centers

    def generate_scallop_points(
        self,
        metadata: ScallopCutMetadata,
        num_points_per_scallop: int = 11,
    ) -> list[tuple[float, float]]:
        """Generate curve points for scallop template creation.

        Creates points along the scallop pattern curve for template
        generation or CNC cutting. Each scallop is approximated by
        a semicircle.

        Args:
            metadata: Scallop cut metadata.
            num_points_per_scallop: Number of points per scallop curve.

        Returns:
            List of (x, y) tuples for the complete scallop pattern,
            where y=0 is the top edge and y=depth is the bottom of scallops.
        """
        points: list[tuple[float, float]] = []

        for i in range(metadata.scallop_count):
            center_x = (
                metadata.scallop_width / 2 + i * metadata.scallop_width
            )
            radius = metadata.scallop_width / 2

            # Generate points for this scallop (semicircle going down)
            for j in range(num_points_per_scallop):
                # Angle from 0 to pi (left to right along semicircle)
                angle = math.pi * j / (num_points_per_scallop - 1)

                # x position along the semicircle
                x = center_x - radius * math.cos(angle)

                # y position: 0 at top edge, depth at bottom of scallop
                # Use min of scallop_depth and the semicircle's y
                y_normalized = math.sin(angle)  # 0 at edges, 1 at center
                y = y_normalized * metadata.scallop_depth

                # Skip duplicate points at scallop boundaries
                if i > 0 and j == 0:
                    continue

                points.append((x, y))

        return points

    def validate_pattern(
        self,
        config: ScallopConfig,
        piece_width: float,
        piece_height: float,
    ) -> tuple[list[str], list[str]]:
        """Validate scallop pattern against piece dimensions.

        Checks that scallop depth doesn't exceed piece height and
        that at least one scallop fits.

        Args:
            config: Scallop configuration.
            piece_width: Width of the piece in inches.
            piece_height: Height of the piece in inches.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check depth doesn't exceed height
        if config.depth >= piece_height:
            errors.append(
                f"Scallop depth {config.depth}\" exceeds piece height "
                f"{piece_height}\""
            )
        elif config.depth > piece_height * 0.5:
            warnings.append(
                f"Scallop depth {config.depth}\" is more than half the "
                f"piece height ({piece_height}\")"
            )

        # Check at least one scallop fits
        count = config.calculate_count(piece_width)
        if count < 1:
            errors.append(
                f"Scallop width {config.width}\" is too large for piece "
                f"width {piece_width}\""
            )

        # Check for reasonable scallop count
        if count > 20:
            warnings.append(
                f"Pattern has {count} scallops. Consider wider scallops "
                "for cleaner appearance."
            )

        # Warn about aspect ratio
        actual_width = piece_width / max(count, 1)
        aspect_ratio = actual_width / config.depth
        if aspect_ratio < 1.5:
            warnings.append(
                f"Scallop aspect ratio {aspect_ratio:.1f} is narrow. "
                "Consider reducing depth."
            )
        elif aspect_ratio > 4:
            warnings.append(
                f"Scallop aspect ratio {aspect_ratio:.1f} is wide. "
                "Consider increasing depth for visibility."
            )

        return errors, warnings


def validate_edge_profile(
    config: EdgeProfileConfig,
    material_thickness: float,
) -> tuple[list[str], list[str]]:
    """Validate edge profile configuration against material.

    Checks:
    - Profile size is positive
    - Profile size doesn't exceed half the material thickness (structural)
    - Profile size doesn't exceed material thickness (impossible)

    Args:
        config: Edge profile configuration.
        material_thickness: Material thickness in inches.

    Returns:
        Tuple of (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Validate size is positive
    if config.size <= 0:
        errors.append("Profile size must be positive")
        return errors, warnings

    # FR-04.5: Profile size validation
    max_safe_size = material_thickness / 2
    if config.size > max_safe_size:
        warnings.append(
            f"Profile size {config.size}\" exceeds half material thickness "
            f"({max_safe_size:.3f}\"). May weaken edge."
        )

    if config.size > material_thickness:
        errors.append(
            f"Profile size {config.size}\" exceeds material thickness "
            f"({material_thickness}\"). Cannot apply profile."
        )

    return errors, warnings


def detect_visible_edges(
    panel_type: PanelType,
    is_left_edge: bool = False,
    is_right_edge: bool = False,
) -> list[str]:
    """Detect which edges of a panel are visible/exposed.

    Determines front-facing visible edges based on panel type and position.

    Args:
        panel_type: Type of panel.
        is_left_edge: Whether panel is at left edge of cabinet.
        is_right_edge: Whether panel is at right edge of cabinet.

    Returns:
        List of visible edge names ("top", "bottom", "left", "right", "front").
    """
    visible: list[str] = []

    # Shelf panels: front edge is always visible
    if panel_type == PanelType.SHELF:
        visible.append("front")  # Note: front = bottom edge for shelf
        # Left/right edges visible if at cabinet edge
        if is_left_edge:
            visible.append("left")
        if is_right_edge:
            visible.append("right")

    # Face frame pieces: all exposed edges
    elif panel_type in (PanelType.FACE_FRAME_STILE, PanelType.FACE_FRAME_RAIL):
        visible.extend(["top", "bottom", "left", "right"])

    # Valance: front and bottom typically visible
    elif panel_type == PanelType.VALANCE:
        visible.extend(["front", "bottom"])

    # Default: just front edge
    else:
        visible.append("front")

    return visible


def apply_edge_profile_metadata(
    panel: Panel,
    config: EdgeProfileConfig,
    visible_edges: list[str] | None = None,
) -> Panel:
    """Apply edge profile metadata to a panel.

    Creates a new Panel with edge profile metadata added.

    Args:
        panel: Original panel.
        config: Edge profile configuration.
        visible_edges: Override for visible edges (uses auto-detect if None).

    Returns:
        New Panel with edge_profile metadata.
    """
    # Determine edges to profile
    if visible_edges is None:
        visible_edges = detect_visible_edges(panel.panel_type)

    edges = config.get_edges(visible_edges)

    # Get router bit recommendation
    router_bit = ROUTER_BIT_RECOMMENDATIONS.get(config.profile_type)

    # Create metadata
    profile_metadata = EdgeProfileMetadata(
        profile_type=config.profile_type,
        size=config.size,
        edges=tuple(edges),
        router_bit=router_bit,
    )

    # Merge with existing metadata
    new_metadata = dict(panel.metadata)
    new_metadata["edge_profile"] = {
        "profile_type": profile_metadata.profile_type.value,
        "size": profile_metadata.size,
        "edges": list(profile_metadata.edges),
        "router_bit": profile_metadata.router_bit,
    }

    # Create new panel with updated metadata
    return Panel(
        panel_type=panel.panel_type,
        width=panel.width,
        height=panel.height,
        material=panel.material,
        position=panel.position,
        metadata=new_metadata,
        cut_metadata=panel.cut_metadata,
    )


# --- Face Frame Component ---


@component_registry.register("decorative.face_frame")
class FaceFrameComponent:
    """Face frame component for cabinet fronts.

    Generates stile (vertical) and rail (horizontal) members that form
    a frame around the cabinet opening. Face frames are used with
    traditional cabinet construction to provide a finished appearance
    and mounting surface for doors and hinges.

    Configuration:
        stile_width: Width of vertical stiles in inches (default: 1.5).
        rail_width: Width of horizontal rails in inches (default: 1.5).
        joinery: Joint type - pocket_screw, mortise_tenon, or dowel.
        material_thickness: Thickness of frame material (default: 0.75).

    Generated Pieces:
        - Left stile (full cabinet height)
        - Right stile (full cabinet height)
        - Top rail (width between stiles)
        - Bottom rail (width between stiles)

    Hardware:
        - Pocket screws (8 for pocket_screw joinery)
        - Dowel pins (8 for dowel joinery)
        - None for mortise_tenon (integral wood joint)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate face frame configuration.

        Checks:
        - stile_width is positive and not too large (FR-03.5)
        - rail_width is positive
        - Cabinet width can accommodate stiles with minimum opening
        - Cabinet height can accommodate rails with minimum opening

        Args:
            config: Face frame configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Get raw config values for validation before parsing
        face_frame_config = config.get("face_frame", {})
        stile_width = face_frame_config.get("stile_width", 1.5)
        rail_width = face_frame_config.get("rail_width", 1.5)

        # FR-03.5: Validate stile width
        if stile_width <= 0:
            errors.append("stile_width must be positive")
        elif stile_width > context.width / 4:
            errors.append(
                f"stile_width {stile_width}\" too large for "
                f"{context.width}\" cabinet width"
            )

        # Validate rail width
        if rail_width <= 0:
            errors.append("rail_width must be positive")
        elif rail_width > context.height / 4:
            errors.append(
                f"rail_width {rail_width}\" too large for "
                f"{context.height}\" cabinet height"
            )

        # Check for minimum opening (only if dimensions are valid)
        if not errors:
            opening_width = context.width - (2 * stile_width)
            opening_height = context.height - (2 * rail_width)

            if opening_width < 6.0:
                errors.append(
                    f"Opening width {opening_width:.1f}\" is less than 6\" minimum"
                )
            if opening_height < 6.0:
                errors.append(
                    f"Opening height {opening_height:.1f}\" is less than 6\" minimum"
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> FaceFrameConfig:
        """Parse configuration dictionary into FaceFrameConfig.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            FaceFrameConfig with parsed values or defaults.
        """
        face_frame_config = config.get("face_frame", {})

        # Map joinery string to enum
        joinery_str = face_frame_config.get("joinery", "pocket_screw")
        joinery = JoineryType(joinery_str)

        return FaceFrameConfig(
            stile_width=face_frame_config.get("stile_width", 1.5),
            rail_width=face_frame_config.get("rail_width", 1.5),
            joinery=joinery,
            material_thickness=face_frame_config.get("material_thickness", 0.75),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate face frame panels.

        Creates Panel entities for:
        - Left stile (full height)
        - Right stile (full height)
        - Top rail (between stiles)
        - Bottom rail (between stiles)

        Args:
            config: Face frame configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with panels, hardware, and metadata.
        """
        frame_config = self._parse_config(config)
        panels: list[Panel] = []

        # Material for face frame pieces
        material = MaterialSpec(
            thickness=frame_config.material_thickness,
        )

        # Calculate dimensions
        rail_length = context.width - (2 * frame_config.stile_width)

        # Left stile (full height)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_STILE,
                width=frame_config.stile_width,
                height=context.height,
                material=material,
                position=Position(context.position.x, context.position.y),
                metadata={
                    "location": "left",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Right stile (full height)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_STILE,
                width=frame_config.stile_width,
                height=context.height,
                material=material,
                position=Position(
                    context.position.x + context.width - frame_config.stile_width,
                    context.position.y,
                ),
                metadata={
                    "location": "right",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Top rail (between stiles)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_RAIL,
                width=rail_length,
                height=frame_config.rail_width,
                material=material,
                position=Position(
                    context.position.x + frame_config.stile_width,
                    context.position.y + context.height - frame_config.rail_width,
                ),
                metadata={
                    "location": "top",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Bottom rail (between stiles)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_RAIL,
                width=rail_length,
                height=frame_config.rail_width,
                material=material,
                position=Position(
                    context.position.x + frame_config.stile_width,
                    context.position.y,
                ),
                metadata={
                    "location": "bottom",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Get hardware
        hardware = self.hardware(config, context)

        # Metadata includes opening dimensions for door component coordination
        metadata = {
            "opening_width": frame_config.opening_width(context.width),
            "opening_height": frame_config.opening_height(context.height),
            "stile_width": frame_config.stile_width,
            "rail_width": frame_config.rail_width,
            "joinery_type": frame_config.joinery.value,
        }

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for face frame.

        Hardware depends on joinery type:
        - pocket_screw: 8 pocket screws (2 per corner)
        - dowel: 8 dowel pins (2 per corner)
        - mortise_tenon: None (integral wood joint)

        Args:
            config: Face frame configuration.
            context: Component context.

        Returns:
            List of HardwareItem objects.
        """
        frame_config = self._parse_config(config)
        items: list[HardwareItem] = []

        if frame_config.joinery == JoineryType.POCKET_SCREW:
            items.append(
                HardwareItem(
                    name='Pocket Screw 1-1/4"',
                    quantity=8,
                    sku="KJ-PS-125",
                    notes="2 screws per corner, 4 corners",
                )
            )
        elif frame_config.joinery == JoineryType.DOWEL:
            items.append(
                HardwareItem(
                    name='Dowel Pin 3/8" x 2"',
                    quantity=8,
                    sku="DP-375-2",
                    notes="2 dowels per corner, 4 corners",
                )
            )
        # mortise_tenon needs no hardware

        return items


# --- Edge Profile Component ---


@component_registry.register("decorative.edge_profile")
class EdgeProfileComponent:
    """Edge profile metadata component.

    This component does not generate physical panels - it applies
    edge profile metadata to existing panels. It's typically used
    in combination with shelf or other components.

    Configuration:
        profile_type: Type of edge profile (chamfer, roundover, etc.).
        size: Profile size/radius in inches.
        edges: Specific edges to profile, or "auto" for visible edges.

    Usage:
        Edge profiles are typically specified at the section level and
        applied to panels generated by other components (e.g., shelves).
        This component validates the configuration but generation is
        handled by the layout calculator or parent component.

    Example:
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
                "edges": "auto"
            }
        }
        result = component.validate(config, context)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate edge profile configuration.

        Checks:
        - Profile size is positive
        - Profile size doesn't exceed material thickness (error)
        - Profile size exceeds half material thickness (warning)

        Args:
            config: Edge profile configuration.
            context: Component context with material information.

        Returns:
            ValidationResult with any errors or warnings.
        """
        edge_config = config.get("edge_profile", {})

        if not edge_config:
            return ValidationResult.ok()

        try:
            # Parse edges - can be "auto" string or list of edge names
            edges_value = edge_config.get("edges", "auto")
            if isinstance(edges_value, list):
                edges: tuple[str, ...] | Literal["auto"] = tuple(edges_value)
            else:
                edges = edges_value

            profile_config = EdgeProfileConfig(
                profile_type=EdgeProfileType(
                    edge_config.get("profile_type", "roundover")
                ),
                size=edge_config.get("size", 0.25),
                edges=edges,
            )
        except (ValueError, KeyError) as e:
            return ValidationResult.fail([str(e)])

        # Get material thickness
        material_thickness = context.material.thickness

        # Validate against material
        errors, warnings = validate_edge_profile(profile_config, material_thickness)

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Edge profile does not generate panels directly.

        Edge profile metadata is applied to panels from other components.
        This method returns an empty result with profile config in metadata.

        Args:
            config: Edge profile configuration.
            context: Component context.

        Returns:
            Empty GenerationResult with profile config in metadata.
        """
        edge_config = config.get("edge_profile", {})

        if not edge_config:
            return GenerationResult()

        return GenerationResult(
            metadata={
                "edge_profile_config": edge_config,
                "note": "Edge profile applied to panels by parent component",
            }
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Edge profiles require no hardware.

        Edge profiles are router cuts, not hardware installations.

        Args:
            config: Edge profile configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


# --- Arch Component ---


@component_registry.register("decorative.arch")
class ArchComponent:
    """Arch top component for arched cabinet openings.

    Generates an arched header panel with curve metadata for cutting.
    The arch fits between vertical dividers within a section.

    Configuration:
        arch_type: Type of arch (full_round, segmental, elliptical).
        radius: Radius in inches, or "auto" for semicircle.
        spring_height: Height where arch curve begins (default: 0).

    Generated Pieces:
        - Arch header panel (rectangular stock with curve metadata)

    Notes:
        - STL output shows rectangular bounding box
        - Cut list includes curve specifications for cutting
        - Side panels should reference arch metadata for height
    """

    def __init__(self) -> None:
        """Initialize ArchComponent with its service."""
        self._arch_service = ArchService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate arch configuration.

        Checks:
        - FR-01.1: Required arch configuration fields
        - FR-01.2: Radius valid for arch type and opening width
        - FR-01.6: Arch fits within section width

        Args:
            config: Arch configuration from component_config.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        arch_config = config.get("arch_top", {})
        if not arch_config:
            return ValidationResult.ok()

        # Parse config
        try:
            parsed = self._parse_config(config)
        except (ValueError, KeyError) as e:
            return ValidationResult.fail([f"Invalid arch config: {e}"])

        opening_width = context.width

        # Validate radius is positive if numeric
        if isinstance(parsed.radius, (int, float)) and parsed.radius <= 0:
            errors.append("Arch radius must be positive")
            return ValidationResult(tuple(errors), tuple(warnings))

        # FR-01.2: Validate radius for arch type
        if parsed.arch_type == ArchType.FULL_ROUND:
            # For full_round with explicit radius, radius must equal width/2
            if parsed.radius != "auto":
                expected_radius = opening_width / 2
                if parsed.radius > expected_radius:
                    errors.append(
                        f"Full round arch radius {parsed.radius}\" exceeds half opening "
                        f"width ({expected_radius}\"). Use 'auto' or a smaller radius."
                    )

        elif parsed.arch_type == ArchType.SEGMENTAL:
            radius = parsed.calculate_radius(opening_width)
            min_radius = opening_width / 2
            if radius < min_radius:
                errors.append(
                    f"Segmental arch radius {radius}\" must be >= half opening "
                    f"width ({min_radius}\")"
                )

        # Check header height doesn't exceed section height
        header_height = self._arch_service.calculate_header_height(
            parsed, opening_width
        )
        if header_height > context.height:
            errors.append(
                f"Arch header height {header_height:.1f}\" exceeds section "
                f"height {context.height}\""
            )

        # Warning for very tall arches
        elif header_height > context.height * 0.5:
            warnings.append(
                f"Arch header uses {header_height / context.height * 100:.0f}% "
                "of section height"
            )

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> ArchConfig:
        """Parse configuration dictionary into ArchConfig.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            ArchConfig with parsed values.

        Raises:
            ValueError: If configuration values are invalid.
        """
        arch_config = config.get("arch_top", {})

        arch_type_str = arch_config.get("arch_type", "full_round")
        arch_type = ArchType(arch_type_str)

        radius = arch_config.get("radius", "auto")
        spring_height = float(arch_config.get("spring_height", 0.0))

        return ArchConfig(
            arch_type=arch_type,
            radius=radius,
            spring_height=spring_height,
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate arch header panel.

        Creates a rectangular panel representing the stock needed
        to cut the arch shape. Curve metadata is included for cutting.

        Args:
            config: Arch configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with arch header panel and metadata.
        """
        parsed = self._parse_config(config)
        opening_width = context.width

        # Calculate dimensions
        header_height = self._arch_service.calculate_header_height(
            parsed, opening_width
        )
        arc_rise = self._arch_service.calculate_arc_rise(parsed, opening_width)

        # Create cut metadata
        cut_metadata = self._arch_service.create_cut_metadata(parsed, opening_width)

        # Generate curve points for template
        curve_points = self._arch_service.generate_curve_points(parsed, opening_width)

        # Arch header panel (rectangular stock)
        panel = Panel(
            panel_type=PanelType.ARCH_HEADER,
            width=opening_width,
            height=header_height,
            material=context.material,
            position=Position(
                context.position.x,
                context.position.y + context.height - header_height,
            ),
            metadata={
                "arch_type": cut_metadata.arch_type.value,
                "radius": cut_metadata.radius,
                "spring_height": cut_metadata.spring_height,
                "opening_width": cut_metadata.opening_width,
                "arc_rise": arc_rise,
                "curve_points": curve_points,
            },
        )

        # Calculate upright extension at typical edge position (0.75" from edge)
        upright_extension_at_edge = self._arch_service.calculate_upright_extension(
            parsed, opening_width, opening_width / 2 - 0.75
        )

        return GenerationResult(
            panels=(panel,),
            hardware=tuple(),
            metadata={
                "arch_config": {
                    "arch_type": parsed.arch_type.value,
                    "radius": cut_metadata.radius,
                    "spring_height": parsed.spring_height,
                    "opening_width": opening_width,
                    "header_height": header_height,
                    "arc_rise": arc_rise,
                },
                "upright_extension_at_edge": upright_extension_at_edge,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Arch components require no hardware.

        Arches are cut shapes, not hardware installations.

        Args:
            config: Arch configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


# --- Scallop Component ---


@component_registry.register("decorative.scallop")
class ScallopComponent:
    """Scallop pattern component for decorative edges.

    Generates a panel (typically valance) with scallop pattern metadata.
    Applicable to valances, shelf fronts, and bottom aprons.

    Configuration:
        scallop.depth: Depth of each scallop in inches.
        scallop.width: Nominal width of each scallop in inches.
        scallop.count: Number of scallops, or "auto" to fit evenly.
        valance_height: Height of the valance panel in inches (default: 4.0).

    Generated Pieces:
        - Valance panel with scallop metadata

    Notes:
        - STL output shows rectangular panel
        - Cut list includes template specifications
        - Pattern is always symmetric about centerline (FR-02.4)
    """

    def __init__(self) -> None:
        """Initialize ScallopComponent with its service."""
        self._scallop_service = ScallopService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate scallop configuration.

        Checks:
        - FR-02.1: Required scallop configuration fields
        - FR-02.3: Applicable piece type
        - Depth vs piece height

        Args:
            config: Scallop configuration from component_config.
            context: Component context with dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        scallop_config = config.get("scallop", {})
        if not scallop_config:
            return ValidationResult.ok()

        # Parse config
        try:
            parsed = self._parse_config(config)
        except (ValueError, KeyError) as e:
            return ValidationResult.fail([f"Invalid scallop config: {e}"])

        # Validate depth is positive
        if parsed.depth <= 0:
            return ValidationResult.fail(["Scallop depth must be positive"])

        # Validate width is positive
        if parsed.width <= 0:
            return ValidationResult.fail(["Scallop width must be positive"])

        # Get valance height from config or use default
        valance_height = config.get("valance_height", 4.0)

        # Validate depth is less than material thickness
        if parsed.depth >= context.material.thickness:
            return ValidationResult.fail(
                [
                    f"Scallop depth {parsed.depth}\" must be less than "
                    f"material thickness {context.material.thickness}\""
                ]
            )

        # Validate pattern
        errors, warnings = self._scallop_service.validate_pattern(
            parsed, context.width, valance_height
        )

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> ScallopConfig:
        """Parse configuration dictionary into ScallopConfig.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            ScallopConfig with parsed values.
        """
        scallop_config = config.get("scallop", {})

        return ScallopConfig(
            depth=scallop_config.get("depth", 1.5),
            width=scallop_config.get("width", 4.0),
            count=scallop_config.get("count", "auto"),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate valance panel with scallop pattern.

        Creates a valance panel with scallop metadata for cutting.

        Args:
            config: Scallop configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with valance panel and metadata.
        """
        parsed = self._parse_config(config)
        valance_height = config.get("valance_height", 4.0)

        # Calculate pattern
        pattern = self._scallop_service.calculate_pattern(parsed, context.width)

        # Calculate scallop centers for template
        centers = self._scallop_service.calculate_scallop_centers(
            pattern, context.width
        )

        # Generate template info
        template_info = self._scallop_service.generate_template_info(pattern)

        # Generate scallop curve points
        scallop_points = self._scallop_service.generate_scallop_points(pattern)

        # Valance panel
        panel = Panel(
            panel_type=PanelType.VALANCE,
            width=context.width,
            height=valance_height,
            material=context.material,
            position=Position(
                context.position.x,
                context.position.y + context.height - valance_height,
            ),
            metadata={
                "scallop_depth": pattern.scallop_depth,
                "scallop_width": pattern.scallop_width,
                "scallop_count": pattern.scallop_count,
                "scallop_centers": centers,
                "scallop_points": scallop_points,
                "template_info": template_info,
                "template_required": pattern.template_required,
            },
        )

        return GenerationResult(
            panels=(panel,),
            hardware=tuple(),
            metadata={
                "scallop_pattern": {
                    "depth": pattern.scallop_depth,
                    "width": pattern.scallop_width,
                    "count": pattern.scallop_count,
                    "centers": centers,
                    "template_info": template_info,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Scallop patterns require no hardware.

        Args:
            config: Scallop configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


# --- Molding Zone Service ---


class MoldingZoneService:
    """Service for molding zone calculations and panel generation.

    Handles crown molding, base/toe kick, and light rail zones.
    Generates nailer strips and calculates dimension adjustments.

    This service provides the core logic for molding zone operations,
    while the individual component classes (CrownMoldingComponent,
    ToeKickComponent, LightRailComponent) wrap this service to implement
    the Component protocol.
    """

    def calculate_crown_adjustments(
        self,
        config: CrownMoldingZone,
        cabinet_width: float,
        cabinet_depth: float,
    ) -> dict[str, float]:
        """Calculate dimension adjustments for crown molding zone.

        Args:
            config: Crown molding zone configuration.
            cabinet_width: Cabinet width in inches.
            cabinet_depth: Cabinet depth in inches.

        Returns:
            Dict with adjustment values:
            - top_panel_depth_reduction: Amount to reduce top panel depth
            - nailer_depth: Depth of nailer strip
            - nailer_width: Width of nailer strip (full cabinet width)
        """
        return {
            "top_panel_depth_reduction": config.setback,
            "nailer_depth": cabinet_depth,  # Full depth for support
            "nailer_width": cabinet_width,
            "zone_height": config.height,
        }

    def generate_crown_nailer(
        self,
        config: CrownMoldingZone,
        cabinet_width: float,
        cabinet_height: float,
        cabinet_depth: float,
        material: MaterialSpec,
        position: Position,
    ) -> Panel:
        """Generate crown molding nailer strip.

        The nailer strip is positioned at the top back of the cabinet,
        providing a mounting surface for crown molding.

        Args:
            config: Crown molding zone configuration.
            cabinet_width: Cabinet width in inches.
            cabinet_height: Cabinet height in inches.
            cabinet_depth: Cabinet depth in inches.
            material: Material for nailer.
            position: Cabinet position.

        Returns:
            Nailer panel.
        """
        return Panel(
            panel_type=PanelType.NAILER,
            width=cabinet_width,
            height=config.nailer_width,  # Note: nailer is horizontal, "height" is depth
            material=material,
            position=Position(
                position.x,
                position.y + cabinet_height - config.nailer_width,
            ),
            metadata={
                "zone_type": "crown_molding",
                "zone_height": config.height,
                "setback": config.setback,
                "location": "top_back",
            },
        )

    def calculate_toe_kick_adjustments(
        self,
        config: BaseZone,
    ) -> dict[str, float]:
        """Calculate dimension adjustments for toe kick zone.

        Args:
            config: Base zone configuration.

        Returns:
            Dict with adjustment values:
            - bottom_panel_raise: Amount to raise bottom panel
            - side_panel_reduction: Amount to shorten side panels
            - toe_kick_height: Height of toe kick
            - toe_kick_setback: Depth of toe kick recess
        """
        if config.zone_type != "toe_kick":
            return {
                "bottom_panel_raise": 0,
                "side_panel_reduction": 0,
                "toe_kick_height": 0,
                "toe_kick_setback": 0,
            }

        return {
            "bottom_panel_raise": config.height,
            "side_panel_reduction": config.height,
            "toe_kick_height": config.height,
            "toe_kick_setback": config.setback,
        }

    def generate_toe_kick_panel(
        self,
        config: BaseZone,
        cabinet_width: float,
        material: MaterialSpec,
        position: Position,
    ) -> Panel | None:
        """Generate toe kick front panel.

        The toe kick panel is recessed from the cabinet front,
        creating the toe space under the cabinet.

        Args:
            config: Base zone configuration.
            cabinet_width: Cabinet width in inches.
            material: Material for panel.
            position: Cabinet position.

        Returns:
            Toe kick panel, or None if not toe_kick type.
        """
        if config.zone_type != "toe_kick":
            return None

        return Panel(
            panel_type=PanelType.TOE_KICK,
            width=cabinet_width,
            height=config.height,
            material=material,
            position=Position(position.x, position.y),
            metadata={
                "zone_type": "toe_kick",
                "setback": config.setback,
                "location": "bottom_front_recessed",
            },
        )

    def generate_light_rail_strip(
        self,
        config: LightRailZone,
        cabinet_width: float,
        material: MaterialSpec,
        position: Position,
    ) -> Panel | None:
        """Generate light rail strip.

        The light rail strip is positioned at the bottom front
        of wall cabinets to conceal under-cabinet lighting.

        Args:
            config: Light rail zone configuration.
            cabinet_width: Cabinet width in inches.
            material: Material for strip.
            position: Cabinet position.

        Returns:
            Light rail panel, or None if generate_strip is False.
        """
        if not config.generate_strip:
            return None

        return Panel(
            panel_type=PanelType.LIGHT_RAIL,
            width=cabinet_width,
            height=config.height,
            material=material,
            position=Position(position.x, position.y),
            metadata={
                "zone_type": "light_rail",
                "setback": config.setback,
                "location": "bottom_front",
            },
        )

    def validate_zones(
        self,
        crown: CrownMoldingZone | None,
        base: BaseZone | None,
        light_rail: LightRailZone | None,
        cabinet_height: float,
        cabinet_depth: float,
    ) -> tuple[list[str], list[str]]:
        """Validate molding zone configurations.

        Checks that zones don't exceed cabinet dimensions and
        don't conflict with each other.

        Args:
            crown: Crown molding zone config (or None).
            base: Base zone config (or None).
            light_rail: Light rail zone config (or None).
            cabinet_height: Cabinet height in inches.
            cabinet_depth: Cabinet depth in inches.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        total_zone_height = 0

        # Validate crown zone
        if crown:
            total_zone_height += crown.height
            if crown.setback >= cabinet_depth:
                errors.append(
                    f"Crown setback {crown.setback}\" exceeds cabinet depth "
                    f"{cabinet_depth}\""
                )
            if crown.height > cabinet_height * 0.2:
                warnings.append(
                    f"Crown zone height {crown.height}\" is more than 20% "
                    "of cabinet height"
                )

        # Validate base zone
        if base:
            total_zone_height += base.height
            if base.zone_type == "toe_kick":
                if base.height < 3.0:
                    warnings.append(
                        f"Toe kick height {base.height}\" is less than "
                        "recommended 3\" minimum (FR-06)"
                    )
                if base.setback < 2.0:
                    warnings.append(
                        f"Toe kick setback {base.setback}\" is less than "
                        "recommended 2\" minimum"
                    )

        # Validate light rail zone
        if light_rail:
            if light_rail.height > 3.0:
                warnings.append(
                    f"Light rail height {light_rail.height}\" may be too tall"
                )

        # Check total zone height
        if total_zone_height > cabinet_height * 0.3:
            warnings.append(
                f"Total zone height {total_zone_height}\" is more than 30% "
                "of cabinet height"
            )

        if total_zone_height >= cabinet_height:
            errors.append(
                f"Total zone height {total_zone_height}\" exceeds cabinet "
                f"height {cabinet_height}\""
            )

        return errors, warnings

    def generate_all_zone_panels(
        self,
        crown: CrownMoldingZone | None,
        base: BaseZone | None,
        light_rail: LightRailZone | None,
        cabinet_width: float,
        cabinet_height: float,
        cabinet_depth: float,
        material: MaterialSpec,
        position: Position,
    ) -> list[Panel]:
        """Generate all panels for configured molding zones.

        Args:
            crown: Crown molding zone config (or None).
            base: Base zone config (or None).
            light_rail: Light rail zone config (or None).
            cabinet_width: Cabinet width in inches.
            cabinet_height: Cabinet height in inches.
            cabinet_depth: Cabinet depth in inches.
            material: Material for panels.
            position: Cabinet position.

        Returns:
            List of zone panels (nailer, toe kick, light rail).
        """
        panels: list[Panel] = []

        if crown:
            panels.append(
                self.generate_crown_nailer(
                    crown, cabinet_width, cabinet_height, cabinet_depth, material, position
                )
            )

        if base and base.zone_type == "toe_kick":
            toe_kick = self.generate_toe_kick_panel(base, cabinet_width, material, position)
            if toe_kick:
                panels.append(toe_kick)

        if light_rail:
            rail = self.generate_light_rail_strip(
                light_rail, cabinet_width, material, position
            )
            if rail:
                panels.append(rail)

        return panels

    def get_dimension_adjustments(
        self,
        crown: CrownMoldingZone | None,
        base: BaseZone | None,
        cabinet_depth: float,
    ) -> dict[str, float]:
        """Get all dimension adjustments for zone configurations.

        Combines adjustments from all zones into a single dict.

        Args:
            crown: Crown molding zone config (or None).
            base: Base zone config (or None).
            cabinet_depth: Cabinet depth in inches.

        Returns:
            Dict with all adjustment values.
        """
        adjustments = {
            "top_panel_depth_reduction": 0.0,
            "bottom_panel_raise": 0.0,
            "side_panel_bottom_raise": 0.0,
        }

        if crown:
            adjustments["top_panel_depth_reduction"] = crown.setback

        if base and base.zone_type == "toe_kick":
            adjustments["bottom_panel_raise"] = base.height
            adjustments["side_panel_bottom_raise"] = base.height

        return adjustments


# --- Crown Molding Component ---


@component_registry.register("decorative.crown_molding")
class CrownMoldingComponent:
    """Crown molding zone component.

    Generates a nailer strip at the top back of the cabinet to provide
    a mounting surface for crown molding. The top panel depth is reduced
    by the configured setback to allow the molding to sit flush.

    Configuration:
        height: Zone height for molding in inches (default: 3.0).
        setback: Top panel setback distance in inches (default: 0.75).
        nailer_width: Width of nailer strip in inches (default: 2.0).

    Generated Pieces:
        - Nailer strip panel (PanelType.NAILER) at top back of cabinet

    Hardware:
        None - nailer strips are structural, attached with standard joinery.

    Note:
        The actual crown molding profile is not generated - only the
        zone and nailer strip. Crown molding is typically purchased
        as linear molding and cut to fit.
    """

    def __init__(self) -> None:
        """Initialize CrownMoldingComponent with its service."""
        self._service = MoldingZoneService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate crown molding zone configuration.

        Checks:
        - height > 0
        - setback > 0
        - setback < cabinet depth
        - height doesn't exceed 20% of cabinet height (warning)

        Args:
            config: Crown molding configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        crown_config = config.get("crown_molding", {})
        if not crown_config:
            return ValidationResult.ok()

        # Parse and validate
        try:
            parsed = self._parse_config(config)
        except ValueError as e:
            return ValidationResult.fail([str(e)])

        # Validate using service
        zone_errors, zone_warnings = self._service.validate_zones(
            crown=parsed,
            base=None,
            light_rail=None,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )

        errors.extend(zone_errors)
        warnings.extend(zone_warnings)

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> CrownMoldingZone:
        """Parse configuration dictionary into CrownMoldingZone.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            CrownMoldingZone with parsed values or defaults.
        """
        crown_config = config.get("crown_molding", {})

        return CrownMoldingZone(
            height=crown_config.get("height", 3.0),
            setback=crown_config.get("setback", 0.75),
            nailer_width=crown_config.get("nailer_width", 2.0),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate crown molding nailer panel.

        Creates a nailer strip panel at the top back of the cabinet.

        Args:
            config: Crown molding configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with nailer panel and metadata.
        """
        parsed = self._parse_config(config)

        nailer = self._service.generate_crown_nailer(
            config=parsed,
            cabinet_width=context.cabinet_width,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
            material=context.material,
            position=context.position,
        )

        adjustments = self._service.calculate_crown_adjustments(
            config=parsed,
            cabinet_width=context.cabinet_width,
            cabinet_depth=context.cabinet_depth,
        )

        return GenerationResult(
            panels=(nailer,),
            hardware=tuple(),
            metadata={
                "crown_zone": {
                    "height": parsed.height,
                    "setback": parsed.setback,
                    "nailer_width": parsed.nailer_width,
                },
                "adjustments": adjustments,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Crown molding zones require no hardware.

        Nailer strips are attached with standard cabinet joinery.

        Args:
            config: Crown molding configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


# --- Toe Kick Component ---


@component_registry.register("decorative.toe_kick")
class ToeKickComponent:
    """Toe kick zone component.

    Generates a recessed front panel at the bottom of the cabinet to
    create toe space. The bottom panel is raised by the toe kick height
    and side panels are shortened accordingly.

    Configuration:
        height: Toe kick height in inches (default: 3.5).
        setback: Toe kick recess depth in inches (default: 3.0).

    Generated Pieces:
        - Toe kick panel (PanelType.TOE_KICK) at bottom front of cabinet

    Hardware:
        None - toe kick panels are structural, attached with standard joinery.

    Note:
        The toe kick panel is recessed from the front face of the cabinet
        by the setback distance, creating space for the user's toes when
        standing close to the cabinet.
    """

    def __init__(self) -> None:
        """Initialize ToeKickComponent with its service."""
        self._service = MoldingZoneService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate toe kick zone configuration.

        Checks:
        - height > 0
        - setback >= 0
        - height < 3.0 generates warning (FR-06 recommends >= 3")
        - setback < 2.0 generates warning (recommended >= 2")

        Args:
            config: Toe kick configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        toe_kick_config = config.get("toe_kick", {})
        if not toe_kick_config:
            return ValidationResult.ok()

        # Parse and validate
        try:
            parsed = self._parse_config(config)
        except ValueError as e:
            return ValidationResult.fail([str(e)])

        # Validate using service
        zone_errors, zone_warnings = self._service.validate_zones(
            crown=None,
            base=parsed,
            light_rail=None,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )

        errors.extend(zone_errors)
        warnings.extend(zone_warnings)

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> BaseZone:
        """Parse configuration dictionary into BaseZone for toe kick.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            BaseZone with zone_type="toe_kick".
        """
        toe_kick_config = config.get("toe_kick", {})

        return BaseZone(
            height=toe_kick_config.get("height", 3.5),
            setback=toe_kick_config.get("setback", 3.0),
            zone_type="toe_kick",
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate toe kick panel.

        Creates a recessed panel at the bottom front of the cabinet.

        Args:
            config: Toe kick configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with toe kick panel and metadata.
        """
        parsed = self._parse_config(config)

        panel = self._service.generate_toe_kick_panel(
            config=parsed,
            cabinet_width=context.cabinet_width,
            material=context.material,
            position=context.position,
        )

        adjustments = self._service.calculate_toe_kick_adjustments(config=parsed)

        panels = (panel,) if panel else tuple()

        return GenerationResult(
            panels=panels,
            hardware=tuple(),
            metadata={
                "toe_kick_zone": {
                    "height": parsed.height,
                    "setback": parsed.setback,
                },
                "adjustments": adjustments,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Toe kick zones require no hardware.

        Toe kick panels are attached with standard cabinet joinery.

        Args:
            config: Toe kick configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


# --- Light Rail Component ---


@component_registry.register("decorative.light_rail")
class LightRailComponent:
    """Light rail zone component.

    Generates a light rail strip at the bottom front of wall cabinets
    to conceal under-cabinet lighting. Only generates the strip panel
    if generate_strip is True.

    Configuration:
        height: Light rail strip height in inches (default: 1.5).
        setback: Light rail setback in inches (default: 0.25).
        generate_strip: Whether to generate strip piece (default: True).

    Generated Pieces:
        - Light rail strip (PanelType.LIGHT_RAIL) at bottom front of cabinet
          (only if generate_strip=True)

    Hardware:
        None - light rail strips are attached with standard methods.

    Note:
        Light rail strips are typically used on wall cabinets to conceal
        under-cabinet lighting fixtures. The zone reserves space for the
        lighting, and the optional strip provides a finished appearance.
    """

    def __init__(self) -> None:
        """Initialize LightRailComponent with its service."""
        self._service = MoldingZoneService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate light rail zone configuration.

        Checks:
        - height > 0
        - setback >= 0
        - height > 3.0 generates warning (may be too tall)

        Args:
            config: Light rail configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        light_rail_config = config.get("light_rail", {})
        if not light_rail_config:
            return ValidationResult.ok()

        # Parse and validate
        try:
            parsed = self._parse_config(config)
        except ValueError as e:
            return ValidationResult.fail([str(e)])

        # Validate using service
        zone_errors, zone_warnings = self._service.validate_zones(
            crown=None,
            base=None,
            light_rail=parsed,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )

        errors.extend(zone_errors)
        warnings.extend(zone_warnings)

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> LightRailZone:
        """Parse configuration dictionary into LightRailZone.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            LightRailZone with parsed values or defaults.
        """
        light_rail_config = config.get("light_rail", {})

        return LightRailZone(
            height=light_rail_config.get("height", 1.5),
            setback=light_rail_config.get("setback", 0.25),
            generate_strip=light_rail_config.get("generate_strip", True),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate light rail strip panel.

        Creates a strip panel at the bottom front of the cabinet
        if generate_strip is True.

        Args:
            config: Light rail configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with light rail panel and metadata.
        """
        parsed = self._parse_config(config)

        panel = self._service.generate_light_rail_strip(
            config=parsed,
            cabinet_width=context.cabinet_width,
            material=context.material,
            position=context.position,
        )

        panels = (panel,) if panel else tuple()

        return GenerationResult(
            panels=panels,
            hardware=tuple(),
            metadata={
                "light_rail_zone": {
                    "height": parsed.height,
                    "setback": parsed.setback,
                    "generate_strip": parsed.generate_strip,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Light rail zones require no hardware.

        Light rail strips are attached with standard methods.

        Args:
            config: Light rail configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []
