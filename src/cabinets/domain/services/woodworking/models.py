"""Woodworking data models.

This module provides dataclasses for:
- JointSpec: Specification for a woodworking joint
- ConnectionJoinery: Joinery specification for panel-to-panel connections
- SpanWarning: Warning for shelf span exceeding safe limits
- WeightCapacity: Estimated weight capacity for horizontal panels
- HardwareList: Aggregated hardware requirements
- GrainAnnotation: Grain direction annotation for cut pieces
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cabinets.domain.components.results import HardwareItem
from cabinets.domain.value_objects import (
    JointType,
    MaterialSpec,
    PanelType,
)


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
            f'{self.panel_label}: {self.span:.1f}" span exceeds '
            f'{self.max_span:.1f}" maximum for '
            f'{self.material.material_type.value} at {self.material.thickness}" thick'
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
class GrainAnnotation:
    """Grain direction annotation for a cut piece.

    Associates a cut piece label with its recommended grain direction
    and the reasoning behind the recommendation.

    Attributes:
        label: Cut piece label (e.g., "Left Side Panel").
        grain_direction: Recommended grain direction value.
        reason: Brief explanation for the recommendation.
    """

    label: str
    grain_direction: str
    reason: str = ""
