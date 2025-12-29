"""Woodworking intelligence domain services and data models.

This module provides:
- Data models for woodworking intelligence features
- Joint specifications for panel connections
- Span limits for material safety
- Weight capacity estimations
- Hardware aggregation
- WoodworkingIntelligence service for joinery analysis
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..components.results import HardwareItem
from ..value_objects import (
    CutPiece,
    GrainDirection,
    JointType,
    MaterialSpec,
    MaterialType,
    PanelType,
)

if TYPE_CHECKING:
    from ..entities import Cabinet, Section, Shelf


# Maximum unsupported shelf spans by material type and thickness
# Key: (MaterialType, thickness_in_inches)
# Value: maximum span in inches
SPAN_LIMITS: dict[tuple[MaterialType, float], float] = {
    (MaterialType.PLYWOOD, 0.75): 36.0,
    (MaterialType.MDF, 0.75): 24.0,
    (MaterialType.PARTICLE_BOARD, 0.75): 24.0,
    (MaterialType.SOLID_WOOD, 1.0): 42.0,
    # Additional common thicknesses
    (MaterialType.PLYWOOD, 0.5): 24.0,
    (MaterialType.PLYWOOD, 1.0): 42.0,
    (MaterialType.MDF, 0.5): 18.0,
    (MaterialType.SOLID_WOOD, 0.75): 36.0,
}


# Approximate modulus of elasticity (E) in PSI for weight capacity calculations
# These are conservative values for cabinet-grade materials
MATERIAL_MODULUS: dict[MaterialType, float] = {
    MaterialType.PLYWOOD: 1_200_000,  # Baltic birch typical
    MaterialType.MDF: 400_000,  # MDF typical
    MaterialType.PARTICLE_BOARD: 300_000,  # Particle board typical
    MaterialType.SOLID_WOOD: 1_400_000,  # Hardwood average
}

# Safety factor for capacity calculations (conservative)
SAFETY_FACTOR: float = 0.5

# Maximum deflection ratio (span / max_deflection)
MAX_DEFLECTION_RATIO: float = 300  # L/300 is typical for shelving


# --- Hardware Constants (FR-05) ---

# Standard screw specifications
CASE_SCREW_SPEC = '#8 x 1-1/4" wood screw'
CASE_SCREW_SPACING = 8.0  # inches between screws

BACK_PANEL_SCREW_SPEC = '#6 x 5/8" pan head screw'
BACK_PANEL_SCREW_SPACING = 6.0  # inches between screws

POCKET_SCREW_SPEC = '#8 x 1-1/4" pocket screw'
POCKET_SCREW_COARSE_NOTE = "coarse thread for plywood"
POCKET_SCREW_FINE_NOTE = "fine thread for hardwood"

DOWEL_SPEC = '5/16" x 1-1/2" fluted dowel'

BISCUIT_SPEC_10 = "#10 biscuit"
BISCUIT_SPEC_20 = "#20 biscuit"


def get_max_span(material_type: MaterialType, thickness: float) -> float:
    """Get maximum span for a material, with fallback interpolation.

    Args:
        material_type: Type of material.
        thickness: Material thickness in inches.

    Returns:
        Maximum recommended span in inches.
    """
    # Exact match
    key = (material_type, thickness)
    if key in SPAN_LIMITS:
        return SPAN_LIMITS[key]

    # Find closest thickness for this material
    matching_entries = [
        (t, span) for (mt, t), span in SPAN_LIMITS.items() if mt == material_type
    ]
    if not matching_entries:
        # Default conservative value
        return 24.0

    # Find closest thickness
    closest = min(matching_entries, key=lambda x: abs(x[0] - thickness))
    return closest[1]


@dataclass(frozen=True)
class JointSpec:
    """Specification for a woodworking joint.

    Contains all dimensional and positional information needed to
    create the joint during cabinet construction.

    Attributes:
        joint_type: Type of joint (dado, rabbet, pocket_screw, etc.).
        depth: Joint depth in inches (for dado/rabbet). None for fastener joints.
        width: Joint width in inches (for rabbet). None for other joints.
        positions: Fastener positions along the joint in inches from one end.
            Used for dowel, pocket screw, and biscuit joints.
        spacing: Nominal spacing between fasteners in inches.
    """

    joint_type: JointType
    depth: float | None = None
    width: float | None = None
    positions: tuple[float, ...] = field(default_factory=tuple)
    spacing: float | None = None

    def __post_init__(self) -> None:
        if self.depth is not None and self.depth <= 0:
            raise ValueError("Joint depth must be positive")
        if self.width is not None and self.width <= 0:
            raise ValueError("Joint width must be positive")
        if self.spacing is not None and self.spacing <= 0:
            raise ValueError("Joint spacing must be positive")
        for pos in self.positions:
            if pos < 0:
                raise ValueError("Position values must be non-negative")

    @classmethod
    def dado(cls, depth: float) -> JointSpec:
        """Create a dado joint specification.

        Args:
            depth: Dado depth in inches (typically 1/3 of material thickness).

        Returns:
            JointSpec for a dado joint.
        """
        return cls(joint_type=JointType.DADO, depth=depth)

    @classmethod
    def rabbet(cls, width: float, depth: float) -> JointSpec:
        """Create a rabbet joint specification.

        Args:
            width: Rabbet width in inches (typically material thickness).
            depth: Rabbet depth in inches (typically 1/2 material thickness).

        Returns:
            JointSpec for a rabbet joint.
        """
        return cls(joint_type=JointType.RABBET, width=width, depth=depth)

    @classmethod
    def pocket_screw(cls, positions: tuple[float, ...], spacing: float) -> JointSpec:
        """Create a pocket screw joint specification.

        Args:
            positions: Screw hole positions from joint start in inches.
            spacing: Nominal spacing between holes in inches.

        Returns:
            JointSpec for pocket screw joinery.
        """
        return cls(
            joint_type=JointType.POCKET_SCREW, positions=positions, spacing=spacing
        )

    @classmethod
    def dowel(cls, positions: tuple[float, ...], spacing: float) -> JointSpec:
        """Create a dowel joint specification.

        Args:
            positions: Dowel positions from joint start in inches.
            spacing: Nominal spacing between dowels in inches.

        Returns:
            JointSpec for dowel joinery.
        """
        return cls(joint_type=JointType.DOWEL, positions=positions, spacing=spacing)

    @classmethod
    def biscuit(cls, positions: tuple[float, ...], spacing: float) -> JointSpec:
        """Create a biscuit joint specification.

        Args:
            positions: Biscuit positions from joint start in inches.
            spacing: Nominal spacing between biscuits in inches.

        Returns:
            JointSpec for biscuit joinery.
        """
        return cls(joint_type=JointType.BISCUIT, positions=positions, spacing=spacing)

    @classmethod
    def butt(cls) -> JointSpec:
        """Create a simple butt joint specification.

        Returns:
            JointSpec for a butt joint (mechanical fasteners only).
        """
        return cls(joint_type=JointType.BUTT)


@dataclass(frozen=True)
class ConnectionJoinery:
    """Joinery specification for a panel-to-panel connection.

    Describes how two panels are joined together, including the joint
    type and its specifications.

    Attributes:
        from_panel: Panel type that receives the joint (e.g., side panel with dado).
        to_panel: Panel type that fits into the joint (e.g., shelf).
        joint: Complete joint specification with dimensions and positions.
        location_description: Human-readable description of joint location.
    """

    from_panel: PanelType
    to_panel: PanelType
    joint: JointSpec
    location_description: str = ""

    def __post_init__(self) -> None:
        if self.from_panel == self.to_panel:
            raise ValueError("from_panel and to_panel must be different")


@dataclass(frozen=True)
class SpanWarning:
    """Warning for shelf span exceeding safe limits.

    Generated when a horizontal panel's unsupported span exceeds
    the recommended maximum for its material type and thickness.

    Attributes:
        panel_label: Identifier for the panel (e.g., "Shelf 1", "Top Panel").
        span: Actual unsupported span in inches.
        max_span: Maximum recommended span for this material in inches.
        material: Material specification of the panel.
        suggestion: Recommended mitigation action.
        severity: Warning severity level ("warning" or "critical").
    """

    panel_label: str
    span: float
    max_span: float
    material: MaterialSpec
    suggestion: str = "Add center support or divider"
    severity: str = "warning"

    def __post_init__(self) -> None:
        if self.span <= 0:
            raise ValueError("Span must be positive")
        if self.max_span <= 0:
            raise ValueError("Max span must be positive")
        if self.severity not in ("warning", "critical"):
            raise ValueError("Severity must be 'warning' or 'critical'")

    @property
    def excess_percentage(self) -> float:
        """How much the span exceeds the limit as a percentage."""
        return ((self.span - self.max_span) / self.max_span) * 100

    @property
    def formatted_message(self) -> str:
        """Human-readable warning message."""
        return (
            f"{self.panel_label}: {self.span:.1f}\" span exceeds "
            f"{self.max_span:.1f}\" maximum for "
            f"{self.material.material_type.value} at {self.material.thickness}\" thick"
        )


@dataclass(frozen=True)
class WeightCapacity:
    """Estimated weight capacity for a horizontal panel.

    Advisory estimate based on simplified beam deflection calculations.
    Always includes a disclaimer that this is not an engineered calculation.

    Attributes:
        panel_label: Identifier for the panel.
        capacity_lbs: Estimated capacity in pounds.
        load_type: Type of load ("distributed" or "point").
        span: Unsupported span length in inches.
        material: Material specification of the panel.
        disclaimer: Legal disclaimer about advisory nature.
    """

    panel_label: str
    capacity_lbs: float
    load_type: str
    span: float
    material: MaterialSpec
    disclaimer: str = "Advisory only - not engineered"

    def __post_init__(self) -> None:
        if self.capacity_lbs < 0:
            raise ValueError("Capacity must be non-negative")
        if self.load_type not in ("distributed", "point"):
            raise ValueError("Load type must be 'distributed' or 'point'")
        if self.span <= 0:
            raise ValueError("Span must be positive")

    @property
    def formatted_message(self) -> str:
        """Human-readable capacity statement."""
        return (
            f"{self.panel_label}: ~{self.capacity_lbs:.0f} lbs {self.load_type} "
            f"({self.disclaimer})"
        )


@dataclass(frozen=True)
class HardwareList:
    """Aggregated hardware requirements for a cabinet.

    Contains all hardware items needed with quantities, and provides
    methods for adding overage and aggregating across components.

    Attributes:
        items: Tuple of hardware items with quantities.
    """

    items: tuple[HardwareItem, ...]

    def with_overage(self, percent: float = 10.0) -> HardwareList:
        """Create a new HardwareList with overage added to quantities.

        Args:
            percent: Overage percentage to add (default 10%).

        Returns:
            New HardwareList with increased quantities.
        """
        if percent < 0:
            raise ValueError("Overage percent must be non-negative")

        multiplier = 1 + (percent / 100)
        new_items = tuple(
            HardwareItem(
                name=item.name,
                quantity=math.ceil(item.quantity * multiplier),
                sku=item.sku,
                notes=item.notes,
            )
            for item in self.items
        )
        return HardwareList(items=new_items)

    @classmethod
    def aggregate(cls, *hardware_lists: HardwareList) -> HardwareList:
        """Combine multiple HardwareLists, summing quantities by name.

        Args:
            hardware_lists: Variable number of HardwareList instances.

        Returns:
            New HardwareList with aggregated quantities.
        """
        # Aggregate by item name
        totals: dict[str, dict] = {}
        for hw_list in hardware_lists:
            for item in hw_list.items:
                if item.name in totals:
                    totals[item.name]["quantity"] += item.quantity
                else:
                    totals[item.name] = {
                        "quantity": item.quantity,
                        "sku": item.sku,
                        "notes": item.notes,
                    }

        new_items = tuple(
            HardwareItem(
                name=name,
                quantity=data["quantity"],
                sku=data["sku"],
                notes=data["notes"],
            )
            for name, data in sorted(totals.items())
        )
        return cls(items=new_items)

    @property
    def total_count(self) -> int:
        """Total count of all hardware items."""
        return sum(item.quantity for item in self.items)

    @property
    def by_category(self) -> dict[str, list[HardwareItem]]:
        """Group hardware items by category (inferred from name)."""
        categories: dict[str, list[HardwareItem]] = {}
        for item in self.items:
            # Infer category from item name
            if "screw" in item.name.lower():
                cat = "screws"
            elif "dowel" in item.name.lower():
                cat = "dowels"
            elif "biscuit" in item.name.lower():
                cat = "biscuits"
            elif "hinge" in item.name.lower():
                cat = "hinges"
            elif "slide" in item.name.lower():
                cat = "slides"
            else:
                cat = "other"

            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        return categories

    @classmethod
    def empty(cls) -> HardwareList:
        """Create an empty HardwareList."""
        return cls(items=())


@dataclass(frozen=True)
class WoodworkingConfig:
    """Configuration for woodworking intelligence service.

    Allows customization of default joint types and dimension ratios
    for joinery calculations.

    Attributes:
        default_shelf_joint: Default joint type for shelf-to-side connections.
        default_back_joint: Default joint type for back panel-to-case connections.
        dado_depth_ratio: Ratio of material thickness for dado depth (default 1/3).
        rabbet_depth_ratio: Ratio of case material thickness for rabbet depth (default 1/2).
        dowel_edge_offset: Distance from panel edges for first/last dowels in inches.
        dowel_spacing: Spacing between dowels in inches.
        pocket_hole_edge_offset: Distance from panel edges for first/last pocket holes.
        pocket_hole_spacing: Spacing between pocket holes in inches.
    """

    default_shelf_joint: JointType = JointType.DADO
    default_back_joint: JointType = JointType.RABBET
    dado_depth_ratio: float = 1 / 3  # Standard: 1/3 of thickness
    rabbet_depth_ratio: float = 0.5  # Standard: 1/2 of case thickness
    dowel_edge_offset: float = 2.0  # 2" from edges (FR-01.5)
    dowel_spacing: float = 6.0  # 6" spacing (FR-01.5)
    pocket_hole_edge_offset: float = 4.0  # 4" from edges (FR-01.6)
    pocket_hole_spacing: float = 8.0  # 8" spacing (FR-01.6)

    def __post_init__(self) -> None:
        if self.dado_depth_ratio <= 0 or self.dado_depth_ratio > 1:
            raise ValueError("dado_depth_ratio must be between 0 and 1")
        if self.rabbet_depth_ratio <= 0 or self.rabbet_depth_ratio > 1:
            raise ValueError("rabbet_depth_ratio must be between 0 and 1")
        if self.dowel_edge_offset <= 0:
            raise ValueError("dowel_edge_offset must be positive")
        if self.dowel_spacing <= 0:
            raise ValueError("dowel_spacing must be positive")
        if self.pocket_hole_edge_offset <= 0:
            raise ValueError("pocket_hole_edge_offset must be positive")
        if self.pocket_hole_spacing <= 0:
            raise ValueError("pocket_hole_spacing must be positive")


class WoodworkingIntelligence:
    """Professional woodworking knowledge service.

    Provides joinery specifications for cabinet construction based on
    woodworking best practices. Analyzes cabinet structure and returns
    appropriate joint types and specifications for each panel connection.

    Joint Selection Rules:
        - Shelf-to-side panel: DADO joint
        - Back panel-to-case: RABBET joint
        - Divider-to-top/bottom: DADO joint
        - Top/bottom-to-sides: DADO joint
        - Face frame joints: POCKET_SCREW or DOWEL
        - Default fallback: BUTT joint

    Dimension Calculations:
        - Dado depth = material thickness * dado_depth_ratio (default 1/3)
        - Rabbet width = back material thickness
        - Rabbet depth = case material thickness * rabbet_depth_ratio (default 1/2)
        - Dowel positions: 2" from edges, 6" spacing
        - Pocket hole positions: 4" from edges, 8" spacing

    Example:
        >>> from cabinets.domain.services.woodworking import WoodworkingIntelligence
        >>> intel = WoodworkingIntelligence()
        >>> joinery = intel.get_joinery(cabinet)
        >>> for joint in joinery:
        ...     print(f"{joint.from_panel.value} -> {joint.to_panel.value}: {joint.joint.joint_type.value}")
    """

    def __init__(self, config: WoodworkingConfig | None = None) -> None:
        """Initialize the woodworking intelligence service.

        Args:
            config: Optional configuration overrides. Uses defaults if not provided.
        """
        self.config = config or WoodworkingConfig()

    def get_joinery(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Determine joinery for all panel connections in a cabinet.

        Analyzes the cabinet structure and returns joinery specifications
        for each panel-to-panel connection based on panel types and
        woodworking best practices.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of ConnectionJoinery objects describing each joint.
        """
        connections: list[ConnectionJoinery] = []

        # Generate joinery for each connection type
        connections.extend(self._shelf_to_side_joinery(cabinet))
        connections.extend(self._back_panel_joinery(cabinet))
        connections.extend(self._divider_joinery(cabinet))
        connections.extend(self._top_bottom_joinery(cabinet))

        return connections

    def _select_joint(
        self, from_panel: PanelType, to_panel: PanelType
    ) -> JointType:
        """Select appropriate joint type for a panel connection.

        Uses woodworking best practices to select the optimal joint type
        based on the panel types being connected.

        Args:
            from_panel: Panel type that receives the joint (e.g., side panel with dado).
            to_panel: Panel type that fits into the joint (e.g., shelf).

        Returns:
            Appropriate JointType for the connection.
        """
        # Shelf-to-side: DADO
        if to_panel == PanelType.SHELF:
            return self.config.default_shelf_joint

        # Back panel: RABBET
        if to_panel == PanelType.BACK:
            return self.config.default_back_joint

        # Divider-to-top/bottom: DADO
        if to_panel == PanelType.DIVIDER:
            return JointType.DADO

        # Horizontal divider: DADO
        if to_panel == PanelType.HORIZONTAL_DIVIDER:
            return JointType.DADO

        # Top/bottom-to-sides: DADO
        if to_panel in (PanelType.TOP, PanelType.BOTTOM):
            return JointType.DADO

        # Face frame: POCKET_SCREW
        if to_panel in (PanelType.FACE_FRAME_RAIL, PanelType.FACE_FRAME_STILE):
            return JointType.POCKET_SCREW

        # Default fallback
        return JointType.BUTT

    def _calculate_dado_spec(self, thickness: float) -> JointSpec:
        """Calculate dado joint specification.

        Dado depth is calculated as a fraction of material thickness
        (default 1/3), which is standard woodworking practice.

        Args:
            thickness: Material thickness in inches.

        Returns:
            JointSpec for a dado joint with calculated depth.
        """
        depth = thickness * self.config.dado_depth_ratio
        return JointSpec.dado(depth=depth)

    def _calculate_rabbet_spec(
        self, back_thickness: float, case_thickness: float
    ) -> JointSpec:
        """Calculate rabbet joint specification.

        Rabbet width equals the back panel thickness (so the back sits flush).
        Rabbet depth is a fraction of the case material thickness.

        Args:
            back_thickness: Back panel material thickness in inches.
            case_thickness: Case material thickness in inches.

        Returns:
            JointSpec for a rabbet joint with calculated dimensions.
        """
        width = back_thickness
        depth = case_thickness * self.config.rabbet_depth_ratio
        return JointSpec.rabbet(width=width, depth=depth)

    def _calculate_fastener_positions(
        self, length: float, edge_offset: float, spacing: float
    ) -> tuple[float, ...]:
        """Calculate fastener positions along a joint.

        Positions fasteners starting at edge_offset from each end,
        with remaining fasteners spaced evenly at approximately
        the given spacing.

        Args:
            length: Total length of the joint in inches.
            edge_offset: Distance from each end for first/last fastener.
            spacing: Nominal spacing between fasteners.

        Returns:
            Tuple of positions from the start of the joint.
        """
        if length <= 2 * edge_offset:
            # Joint too short for normal layout, use center only
            return (length / 2,)

        # Start and end positions
        start_pos = edge_offset
        end_pos = length - edge_offset
        available_length = end_pos - start_pos

        if available_length <= 0:
            return (length / 2,)

        # Calculate number of interior positions needed
        num_interior = max(0, int(available_length / spacing))

        if num_interior == 0:
            # Only room for start and end positions
            return (start_pos, end_pos)

        # Distribute interior fasteners evenly
        actual_spacing = available_length / (num_interior + 1)
        positions = [start_pos]
        for i in range(num_interior):
            positions.append(start_pos + actual_spacing * (i + 1))
        positions.append(end_pos)

        return tuple(positions)

    def _shelf_to_side_joinery(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Generate joinery for shelf-to-side panel connections.

        Shelves typically use dado joints into side panels for strong,
        self-aligning connections that support vertical loads.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of ConnectionJoinery for shelf connections.
        """
        connections: list[ConnectionJoinery] = []
        dado_spec = self._calculate_dado_spec(cabinet.material.thickness)

        for section in cabinet.sections:
            for shelf in section.shelves:
                # Left side connection
                connections.append(
                    ConnectionJoinery(
                        from_panel=PanelType.LEFT_SIDE,
                        to_panel=PanelType.SHELF,
                        joint=dado_spec,
                        location_description=f"Shelf at {shelf.position.y:.1f}\" height",
                    )
                )

                # Right side connection (or divider if not last section)
                connections.append(
                    ConnectionJoinery(
                        from_panel=PanelType.RIGHT_SIDE,
                        to_panel=PanelType.SHELF,
                        joint=dado_spec,
                        location_description=f"Shelf at {shelf.position.y:.1f}\" height",
                    )
                )

        return connections

    def _back_panel_joinery(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Generate joinery for back panel-to-case connections.

        Back panels typically use rabbet joints into the case sides,
        top, and bottom for a flush fit that adds rigidity.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of ConnectionJoinery for back panel connections.
        """
        connections: list[ConnectionJoinery] = []

        # Calculate rabbet dimensions
        assert cabinet.back_material is not None
        rabbet_spec = self._calculate_rabbet_spec(
            back_thickness=cabinet.back_material.thickness,
            case_thickness=cabinet.material.thickness,
        )

        # Rabbet into all four case edges
        case_panels = [
            (PanelType.LEFT_SIDE, "Left side"),
            (PanelType.RIGHT_SIDE, "Right side"),
            (PanelType.TOP, "Top"),
            (PanelType.BOTTOM, "Bottom"),
        ]

        for panel_type, description in case_panels:
            connections.append(
                ConnectionJoinery(
                    from_panel=panel_type,
                    to_panel=PanelType.BACK,
                    joint=rabbet_spec,
                    location_description=f"Back panel rabbet in {description}",
                )
            )

        return connections

    def _divider_joinery(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Generate joinery for vertical divider connections.

        Dividers use dado joints into top and bottom panels,
        similar to how side panels join.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of ConnectionJoinery for divider connections.
        """
        connections: list[ConnectionJoinery] = []

        # Check if cabinet has dividers (more than 1 section)
        num_sections = len(cabinet.sections)
        if num_sections <= 1:
            return connections

        dado_spec = self._calculate_dado_spec(cabinet.material.thickness)

        # Each divider between sections
        for i in range(num_sections - 1):
            connections.append(
                ConnectionJoinery(
                    from_panel=PanelType.TOP,
                    to_panel=PanelType.DIVIDER,
                    joint=dado_spec,
                    location_description=f"Divider {i + 1} to top panel",
                )
            )
            connections.append(
                ConnectionJoinery(
                    from_panel=PanelType.BOTTOM,
                    to_panel=PanelType.DIVIDER,
                    joint=dado_spec,
                    location_description=f"Divider {i + 1} to bottom panel",
                )
            )

        return connections

    def _top_bottom_joinery(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Generate joinery for top/bottom to side panel connections.

        Top and bottom panels typically use dado joints into side panels,
        capturing the sides for a strong case structure.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of ConnectionJoinery for top/bottom connections.
        """
        connections: list[ConnectionJoinery] = []
        dado_spec = self._calculate_dado_spec(cabinet.material.thickness)

        # Top to sides
        connections.append(
            ConnectionJoinery(
                from_panel=PanelType.LEFT_SIDE,
                to_panel=PanelType.TOP,
                joint=dado_spec,
                location_description="Top panel dado in left side",
            )
        )
        connections.append(
            ConnectionJoinery(
                from_panel=PanelType.RIGHT_SIDE,
                to_panel=PanelType.TOP,
                joint=dado_spec,
                location_description="Top panel dado in right side",
            )
        )

        # Bottom to sides
        connections.append(
            ConnectionJoinery(
                from_panel=PanelType.LEFT_SIDE,
                to_panel=PanelType.BOTTOM,
                joint=dado_spec,
                location_description="Bottom panel dado in left side",
            )
        )
        connections.append(
            ConnectionJoinery(
                from_panel=PanelType.RIGHT_SIDE,
                to_panel=PanelType.BOTTOM,
                joint=dado_spec,
                location_description="Bottom panel dado in right side",
            )
        )

        return connections

    def get_pocket_screw_spec(self, length: float) -> JointSpec:
        """Generate pocket screw joint specification for a given length.

        Calculates pocket hole positions based on configured edge offset
        and spacing parameters.

        Args:
            length: Length of the joint in inches.

        Returns:
            JointSpec with pocket screw positions.
        """
        positions = self._calculate_fastener_positions(
            length=length,
            edge_offset=self.config.pocket_hole_edge_offset,
            spacing=self.config.pocket_hole_spacing,
        )
        return JointSpec.pocket_screw(
            positions=positions,
            spacing=self.config.pocket_hole_spacing,
        )

    def get_dowel_spec(self, length: float) -> JointSpec:
        """Generate dowel joint specification for a given length.

        Calculates dowel positions based on configured edge offset
        and spacing parameters.

        Args:
            length: Length of the joint in inches.

        Returns:
            JointSpec with dowel positions.
        """
        positions = self._calculate_fastener_positions(
            length=length,
            edge_offset=self.config.dowel_edge_offset,
            spacing=self.config.dowel_spacing,
        )
        return JointSpec.dowel(
            positions=positions,
            spacing=self.config.dowel_spacing,
        )

    def check_spans(self, cabinet: Cabinet) -> list[SpanWarning]:
        """Check all horizontal panels for span violations.

        Analyzes shelves, top, and bottom panels against material-specific
        span limits. Returns warnings for any panels that exceed safe limits.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of SpanWarning objects for panels exceeding limits.
        """
        warnings: list[SpanWarning] = []

        # Check each section's shelves
        for section_idx, section in enumerate(cabinet.sections):
            for shelf_idx, shelf in enumerate(section.shelves):
                span = self._calculate_shelf_span(shelf, section)
                max_span = get_max_span(
                    shelf.material.material_type, shelf.material.thickness
                )

                if span > max_span:
                    severity = "critical" if span > max_span * 1.5 else "warning"
                    warnings.append(
                        SpanWarning(
                            panel_label=f"Section {section_idx + 1} Shelf {shelf_idx + 1}",
                            span=span,
                            max_span=max_span,
                            material=shelf.material,
                            suggestion=self._get_span_suggestion(span, max_span),
                            severity=severity,
                        )
                    )

        # Check top panel span
        top_span = self._calculate_case_span(cabinet, PanelType.TOP)
        if top_span > 0:
            max_span = get_max_span(
                cabinet.material.material_type, cabinet.material.thickness
            )
            if top_span > max_span:
                warnings.append(
                    SpanWarning(
                        panel_label="Top Panel",
                        span=top_span,
                        max_span=max_span,
                        material=cabinet.material,
                        suggestion=self._get_span_suggestion(top_span, max_span),
                        severity="warning",
                    )
                )

        # Check bottom panel span
        bottom_span = self._calculate_case_span(cabinet, PanelType.BOTTOM)
        if bottom_span > 0:
            max_span = get_max_span(
                cabinet.material.material_type, cabinet.material.thickness
            )
            if bottom_span > max_span:
                warnings.append(
                    SpanWarning(
                        panel_label="Bottom Panel",
                        span=bottom_span,
                        max_span=max_span,
                        material=cabinet.material,
                        suggestion=self._get_span_suggestion(bottom_span, max_span),
                        severity="warning",
                    )
                )

        return warnings

    def _calculate_shelf_span(self, shelf: "Shelf", section: "Section") -> float:
        """Calculate unsupported span for a shelf.

        The unsupported span is the width of the section that the shelf
        spans, not accounting for any intermediate supports.

        Args:
            shelf: The shelf to analyze.
            section: The section containing the shelf.

        Returns:
            Unsupported span in inches.
        """
        # Basic calculation: section width is the unsupported span
        # In a more complex implementation, this could account for
        # intermediate dividers or supports
        return section.width

    def _calculate_case_span(self, cabinet: Cabinet, panel_type: PanelType) -> float:
        """Calculate unsupported span for top/bottom case panels.

        For cabinets with multiple sections, the span between dividers
        may be less than the full cabinet width. This method calculates
        the maximum unsupported span.

        Args:
            cabinet: The cabinet to analyze.
            panel_type: Either TOP or BOTTOM panel type.

        Returns:
            Maximum unsupported span in inches.
        """
        if not cabinet.sections:
            return cabinet.interior_width

        # Find the widest section (maximum span between supports)
        max_section_width = max(section.width for section in cabinet.sections)
        return max_section_width

    def _get_span_suggestion(self, span: float, max_span: float) -> str:
        """Generate suggestion text based on span excess.

        Args:
            span: Actual span in inches.
            max_span: Maximum recommended span in inches.

        Returns:
            Suggestion text for mitigation.
        """
        excess_percent = ((span - max_span) / max_span) * 100

        if excess_percent > 50:
            return (
                "Add center support or divider. Consider thicker material "
                "(1\" or greater) for this span."
            )
        elif excess_percent > 25:
            return "Add center support or divider to reduce span."
        else:
            return (
                "Consider adding center support, using thicker material, "
                "or reducing load expectations."
            )

    # --- Grain Direction Methods (FR-03) ---

    def get_grain_directions(
        self,
        cut_list: list[CutPiece],
    ) -> dict[str, GrainDirection]:
        """Recommend grain direction for each cut piece.

        Determines optimal grain direction based on:
        - Piece dimensions (grain parallel to longest dimension)
        - Material type (solid wood requires grain along length)
        - Panel type (visible panels prioritize aesthetics)

        For panels with grain_direction already in cut_metadata, that value
        is used instead of calculating a recommendation.

        Args:
            cut_list: List of cut pieces to analyze.

        Returns:
            Dict mapping piece labels to recommended GrainDirection.
        """
        recommendations: dict[str, GrainDirection] = {}

        for piece in cut_list:
            # Check if grain direction already specified in metadata
            existing = self._get_existing_grain(piece)
            if existing is not None:
                recommendations[piece.label] = existing
                continue

            # Recommend based on piece characteristics
            recommendations[piece.label] = self._recommend_grain(piece)

        return recommendations

    def _get_existing_grain(self, piece: CutPiece) -> GrainDirection | None:
        """Get existing grain direction from piece metadata.

        Args:
            piece: Cut piece to check.

        Returns:
            GrainDirection if specified in metadata, None otherwise.
        """
        if not piece.cut_metadata:
            return None

        grain_str = piece.cut_metadata.get("grain_direction")
        if grain_str is None:
            return None

        try:
            return GrainDirection(grain_str)
        except ValueError:
            return None

    def _recommend_grain(self, piece: CutPiece) -> GrainDirection:
        """Calculate recommended grain direction for a piece.

        Rules applied in order:
        1. For MDF/particle board: no visible grain (NONE)
        2. For solid wood: grain must be parallel to longest dimension
        3. For plywood face panels: grain along length for aesthetics
        4. For pieces > 12" in longest dimension: grain along longest dimension
        5. Otherwise: no constraint (piece can rotate freely)

        Args:
            piece: Cut piece to analyze.

        Returns:
            Recommended GrainDirection.
        """
        # MDF and particle board have no visible grain
        if piece.material.material_type in (
            MaterialType.MDF,
            MaterialType.PARTICLE_BOARD,
        ):
            return GrainDirection.NONE

        # Solid wood always needs grain parallel to length for strength
        if piece.material.material_type == MaterialType.SOLID_WOOD:
            return self._grain_for_longest_dimension(piece)

        # Visible face panels should have grain along length for aesthetics
        if self._is_visible_panel(piece):
            # For plywood, face grain should be along length
            if piece.material.material_type == MaterialType.PLYWOOD:
                return self._grain_for_longest_dimension(piece)

        # For pieces > 12" in longest dimension, recommend grain along length
        max_dimension = max(piece.width, piece.height)
        if max_dimension > 12.0:
            return self._grain_for_longest_dimension(piece)

        # For small pieces, no grain constraint
        return GrainDirection.NONE

    def _grain_for_longest_dimension(self, piece: CutPiece) -> GrainDirection:
        """Determine grain direction for longest dimension.

        Args:
            piece: Cut piece to analyze.

        Returns:
            LENGTH if width >= height, WIDTH otherwise.
        """
        if piece.width >= piece.height:
            return GrainDirection.LENGTH
        else:
            return GrainDirection.WIDTH

    def _is_visible_panel(self, piece: CutPiece) -> bool:
        """Determine if a panel is visible and aesthetically important.

        Visible panels include:
        - Side panels (when not against wall)
        - Door panels
        - Drawer fronts
        - Face frame components
        - Shelves (front edge visible)

        Non-visible panels include:
        - Back panels
        - Drawer sides and bottoms
        - Internal dividers

        Args:
            piece: Cut piece to check.

        Returns:
            True if panel visibility matters for grain.
        """
        visible_types = {
            PanelType.LEFT_SIDE,
            PanelType.RIGHT_SIDE,
            PanelType.TOP,
            PanelType.BOTTOM,
            PanelType.DOOR,
            PanelType.DRAWER_FRONT,
            PanelType.SHELF,
            PanelType.FACE_FRAME_RAIL,
            PanelType.FACE_FRAME_STILE,
            PanelType.VALANCE,
            PanelType.ARCH_HEADER,
            PanelType.LIGHT_RAIL,
        }
        return piece.panel_type in visible_types

    def annotate_cut_list(
        self,
        cut_list: list[CutPiece],
    ) -> list[CutPiece]:
        """Create new cut list with grain directions in metadata.

        Creates copies of cut pieces with grain_direction added to
        their cut_metadata. Pieces that already have grain_direction
        specified are not modified.

        Args:
            cut_list: Original cut list.

        Returns:
            New cut list with grain directions in metadata.
        """
        directions = self.get_grain_directions(cut_list)
        annotated = []

        for piece in cut_list:
            grain = directions.get(piece.label, GrainDirection.NONE)

            # Skip if already has grain direction
            if piece.cut_metadata and "grain_direction" in piece.cut_metadata:
                annotated.append(piece)
                continue

            # Create new metadata with grain direction
            new_metadata = dict(piece.cut_metadata) if piece.cut_metadata else {}
            new_metadata["grain_direction"] = grain.value

            # Create new piece with updated metadata
            new_piece = CutPiece(
                width=piece.width,
                height=piece.height,
                quantity=piece.quantity,
                label=piece.label,
                panel_type=piece.panel_type,
                material=piece.material,
                cut_metadata=new_metadata,
            )
            annotated.append(new_piece)

        return annotated

    # --- Weight Capacity Methods (FR-04) ---

    def estimate_capacity(
        self,
        thickness: float,
        depth: float,
        span: float,
        material_type: MaterialType,
        load_type: str = "distributed",
        panel_label: str = "Shelf",
    ) -> WeightCapacity:
        """Estimate weight capacity for a horizontal panel.

        Uses simplified beam deflection formula to estimate the load capacity
        of a shelf or horizontal panel. This is an advisory estimate only and
        should not be used for structural engineering purposes.

        The formula used is based on the deflection limit approach:
        For distributed load: P = (384 * E * I * delta_max) / (5 * L^4)
        Where delta_max = L / 300 (standard deflection limit)

        Args:
            thickness: Panel thickness in inches.
            depth: Panel depth (front-to-back) in inches.
            span: Unsupported span in inches.
            material_type: Type of material.
            load_type: "distributed" or "point" load type.
            panel_label: Label for the panel in output.

        Returns:
            WeightCapacity with estimated capacity and disclaimer.
        """
        base_capacity = self._calculate_base_capacity(
            thickness=thickness,
            depth=depth,
            span=span,
            material_type=material_type,
        )

        # Reduce capacity for point loads (more concentrated stress)
        if load_type == "point":
            base_capacity *= 0.5  # 50% reduction for point loads

        # Apply safety factor
        final_capacity = base_capacity * SAFETY_FACTOR

        # Round to nearest 5 lbs for readability
        final_capacity = round(final_capacity / 5) * 5

        # Minimum capacity of 5 lbs
        final_capacity = max(5.0, final_capacity)

        return WeightCapacity(
            panel_label=panel_label,
            capacity_lbs=final_capacity,
            load_type=load_type,
            span=span,
            material=MaterialSpec(thickness=thickness, material_type=material_type),
            disclaimer="Advisory only - not engineered",
        )

    def _calculate_base_capacity(
        self,
        thickness: float,
        depth: float,
        span: float,
        material_type: MaterialType,
    ) -> float:
        """Calculate base load capacity using beam deflection formula.

        Uses the formula for maximum load based on deflection limit:
        For a uniformly distributed load on a simply supported beam:
        w = (384 * E * I * delta) / (5 * L^4)

        Where:
        - E = modulus of elasticity (psi)
        - I = moment of inertia = (b * h^3) / 12
        - delta = maximum deflection = L / 300
        - L = span length
        - w = load per unit length
        - Total load P = w * L

        Args:
            thickness: Panel thickness in inches.
            depth: Panel depth (front-to-back) in inches.
            span: Unsupported span in inches.
            material_type: Type of material.

        Returns:
            Base capacity in pounds (before safety factor).
        """
        if span <= 0:
            return 0.0

        # Get modulus of elasticity
        E = MATERIAL_MODULUS.get(material_type, 1_000_000)

        # Moment of inertia for rectangular section
        # I = (b * h^3) / 12, where b = depth, h = thickness
        I = (depth * (thickness**3)) / 12

        # Maximum allowable deflection (L/300 standard)
        delta_max = span / MAX_DEFLECTION_RATIO

        # Convert span to same units (already in inches)
        L = span

        # Calculate maximum distributed load (lbs/inch)
        # w = (384 * E * I * delta) / (5 * L^4)
        w = (384 * E * I * delta_max) / (5 * (L**4))

        # Total capacity is w * L (load per inch * span)
        total_load = w * L

        return total_load

    def get_shelf_capacities(
        self,
        cabinet: "Cabinet",
    ) -> list[WeightCapacity]:
        """Get weight capacity estimates for all shelves in a cabinet.

        Calculates capacity for each shelf based on its material,
        thickness, depth, and span.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of WeightCapacity objects, one per shelf.
        """
        capacities: list[WeightCapacity] = []

        for section_idx, section in enumerate(cabinet.sections):
            for shelf_idx, shelf in enumerate(section.shelves):
                # Calculate span (section width is unsupported span)
                span = section.width

                capacity = self.estimate_capacity(
                    thickness=shelf.material.thickness,
                    depth=shelf.depth,
                    span=span,
                    material_type=shelf.material.material_type,
                    load_type="distributed",
                    panel_label=f"Section {section_idx + 1} Shelf {shelf_idx + 1}",
                )
                capacities.append(capacity)

        return capacities

    def format_capacity_report(
        self,
        capacities: list[WeightCapacity],
    ) -> str:
        """Format weight capacity estimates as a report.

        Args:
            capacities: List of WeightCapacity objects.

        Returns:
            Formatted report string.
        """
        lines = [
            "WEIGHT CAPACITY ESTIMATES",
            "=" * 60,
            "",
            "DISCLAIMER: These are advisory estimates only.",
            "Do not use for structural engineering or load-bearing applications.",
            "",
            "-" * 60,
        ]

        for cap in capacities:
            lines.append(
                f"{cap.panel_label}: ~{cap.capacity_lbs:.0f} lbs ({cap.load_type})"
            )
            lines.append(
                f"  Material: {cap.material.material_type.value} at {cap.material.thickness}\""
            )
            lines.append(f"  Span: {cap.span:.1f}\"")
            lines.append("")

        lines.append("-" * 60)
        lines.append("Note: Capacities assume evenly distributed loads.")
        lines.append("Point loads reduce capacity by approximately 50%.")

        return "\n".join(lines)

    # --- Hardware Calculation Methods (FR-05) ---

    def calculate_hardware(
        self,
        cabinet: "Cabinet",
        include_overage: bool = True,
        overage_percent: float = 10.0,
    ) -> HardwareList:
        """Calculate all hardware needed for cabinet construction.

        Aggregates fastener requirements for case assembly, back panel
        attachment, and joinery-specific hardware. Optionally adds
        overage for waste and mistakes.

        Args:
            cabinet: Cabinet to analyze.
            include_overage: Whether to add overage percentage.
            overage_percent: Percentage of overage to add (default 10%).

        Returns:
            HardwareList with all hardware items and quantities.
        """
        items: list[HardwareItem] = []

        # Case assembly screws
        items.extend(self._case_screws(cabinet))

        # Back panel attachment
        items.extend(self._back_panel_screws(cabinet))

        # Joinery-specific fasteners
        joinery = self.get_joinery(cabinet)
        items.extend(self._joinery_fasteners(cabinet, joinery))

        # Shelf-related fasteners (placeholder for future component integration)
        items.extend(self._shelf_fasteners(cabinet))

        # Aggregate all items by name
        hardware_list = HardwareList(items=tuple(items))
        aggregated = HardwareList.aggregate(hardware_list)

        if include_overage:
            aggregated = aggregated.with_overage(overage_percent)

        return aggregated

    def _case_screws(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Calculate screws for case assembly.

        Screws are used to attach top and bottom panels to side panels,
        and to attach dividers. Uses standard spacing of 8" between screws.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of HardwareItem for case screws.
        """
        items: list[HardwareItem] = []

        # Calculate perimeter of case (where sides meet top/bottom)
        # Top and bottom each connect to both sides
        cabinet_depth = cabinet.depth

        # Screws for top-to-sides (2 sides x screws along depth)
        top_screws_per_side = max(2, int(cabinet_depth / CASE_SCREW_SPACING) + 1)
        top_screws = top_screws_per_side * 2  # Both sides

        # Screws for bottom-to-sides (same as top)
        bottom_screws = top_screws_per_side * 2

        # Screws for dividers (each divider connects to top and bottom)
        num_dividers = max(0, len(cabinet.sections) - 1)
        divider_screws = 0
        if num_dividers > 0:
            screws_per_divider_edge = max(
                2, int(cabinet_depth / CASE_SCREW_SPACING) + 1
            )
            divider_screws = num_dividers * screws_per_divider_edge * 2  # Top and bottom

        total_case_screws = top_screws + bottom_screws + divider_screws

        if total_case_screws > 0:
            items.append(
                HardwareItem(
                    name=CASE_SCREW_SPEC,
                    quantity=total_case_screws,
                    sku=None,
                    notes="Case assembly",
                )
            )

        return items

    def _back_panel_screws(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Calculate screws for back panel attachment.

        Back panel is attached around the perimeter with standard spacing
        of 6" between screws.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of HardwareItem for back panel screws.
        """
        items: list[HardwareItem] = []

        # Calculate perimeter of back panel
        width = cabinet.width
        height = cabinet.height

        # Screws along top and bottom edges
        horizontal_screws = max(2, int(width / BACK_PANEL_SCREW_SPACING) + 1) * 2

        # Screws along left and right edges (excluding corners already counted)
        vertical_screws = max(0, int(height / BACK_PANEL_SCREW_SPACING) - 1) * 2

        # Add screws along dividers if any
        num_dividers = max(0, len(cabinet.sections) - 1)
        divider_screws = 0
        if num_dividers > 0:
            screws_per_divider = max(2, int(height / BACK_PANEL_SCREW_SPACING))
            divider_screws = num_dividers * screws_per_divider

        total_back_screws = horizontal_screws + vertical_screws + divider_screws

        if total_back_screws > 0:
            items.append(
                HardwareItem(
                    name=BACK_PANEL_SCREW_SPEC,
                    quantity=total_back_screws,
                    sku=None,
                    notes="Back panel attachment",
                )
            )

        return items

    def _joinery_fasteners(
        self,
        cabinet: "Cabinet",
        joinery: list[ConnectionJoinery],
    ) -> list[HardwareItem]:
        """Calculate fasteners for joinery connections.

        Different joint types require different fasteners:
        - Pocket screw: Pocket screws
        - Dowel: Dowel pins
        - Biscuit: Biscuits
        - Dado/Rabbet: No additional fasteners (glued joints)

        Args:
            cabinet: Cabinet to analyze.
            joinery: List of ConnectionJoinery from get_joinery().

        Returns:
            List of HardwareItem for joinery-specific fasteners.
        """
        items: list[HardwareItem] = []

        # Count fasteners by type
        pocket_screw_count = 0
        dowel_count = 0
        biscuit_count = 0

        for connection in joinery:
            joint = connection.joint

            if joint.joint_type == JointType.POCKET_SCREW:
                # Count based on positions
                pocket_screw_count += len(joint.positions)

            elif joint.joint_type == JointType.DOWEL:
                # Count based on positions
                dowel_count += len(joint.positions)

            elif joint.joint_type == JointType.BISCUIT:
                # Count based on positions
                biscuit_count += len(joint.positions)

            # Dado and rabbet joints don't need additional fasteners

        # Add pocket screws if any
        if pocket_screw_count > 0:
            # Determine thread type based on material
            is_hardwood = cabinet.material.material_type == MaterialType.SOLID_WOOD
            notes = POCKET_SCREW_FINE_NOTE if is_hardwood else POCKET_SCREW_COARSE_NOTE

            items.append(
                HardwareItem(
                    name=POCKET_SCREW_SPEC,
                    quantity=pocket_screw_count,
                    sku=None,
                    notes=notes,
                )
            )

        # Add dowels if any
        if dowel_count > 0:
            items.append(
                HardwareItem(
                    name=DOWEL_SPEC,
                    quantity=dowel_count,
                    sku=None,
                    notes="Joinery alignment",
                )
            )

        # Add biscuits if any
        if biscuit_count > 0:
            # Use #20 for panels, #10 for narrow pieces
            items.append(
                HardwareItem(
                    name=BISCUIT_SPEC_20,
                    quantity=biscuit_count,
                    sku=None,
                    notes="Panel joinery",
                )
            )

        return items

    def _shelf_fasteners(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Calculate hardware for shelf support.

        For adjustable shelves, this includes shelf pins.
        For fixed shelves with dado joints, no additional hardware is needed.

        Note: This is called separately from calculate_hardware() since
        shelf components already generate their own hardware via the
        component registry pattern.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of HardwareItem for shelf support.
        """
        # Currently, shelf components generate their own hardware
        # This method is a placeholder for future centralization
        return []
