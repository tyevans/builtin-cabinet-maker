"""Joint selection strategy pattern implementation.

This module implements the Strategy pattern for joint selection,
fixing the Open-Closed Principle violation in the original
_select_joint() method that used if-elif chains.

The Strategy pattern allows adding new joint selection strategies
without modifying existing code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cabinets.domain.value_objects import JointType, PanelType

from .config import WoodworkingConfig
from .models import JointSpec


class JointSelector(ABC):
    """Abstract base class for joint selection strategies.

    Each concrete implementation handles joint selection for a specific
    panel type (the 'to_panel' in a connection).
    """

    @abstractmethod
    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select appropriate joint type for a panel connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            Appropriate JointType for the connection.
        """
        ...


class ShelfJointSelector(JointSelector):
    """Joint selector for shelf panels.

    Shelves typically use dado joints into side panels for strong,
    self-aligning connections that support vertical loads.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for shelf-to-panel connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            Default shelf joint type from config (typically DADO).
        """
        return config.default_shelf_joint


class BackPanelJointSelector(JointSelector):
    """Joint selector for back panels.

    Back panels typically use rabbet joints into the case sides,
    top, and bottom for a flush fit that adds rigidity.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for back panel connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            Default back joint type from config (typically RABBET).
        """
        return config.default_back_joint


class DividerJointSelector(JointSelector):
    """Joint selector for vertical divider panels.

    Dividers use dado joints into top and bottom panels,
    similar to how side panels join.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for divider connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            DADO joint type.
        """
        return JointType.DADO


class HorizontalDividerJointSelector(JointSelector):
    """Joint selector for horizontal divider panels.

    Horizontal dividers use dado joints similar to shelves.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for horizontal divider connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            DADO joint type.
        """
        return JointType.DADO


class TopPanelJointSelector(JointSelector):
    """Joint selector for top panels.

    Top panels use dado joints into side panels.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for top panel connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            DADO joint type.
        """
        return JointType.DADO


class BottomPanelJointSelector(JointSelector):
    """Joint selector for bottom panels.

    Bottom panels use dado joints into side panels.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for bottom panel connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            DADO joint type.
        """
        return JointType.DADO


class FaceFrameJointSelector(JointSelector):
    """Joint selector for face frame components.

    Face frame rails and stiles typically use pocket screw joints
    for strong, hidden connections.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select joint for face frame connection.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            POCKET_SCREW joint type.
        """
        return JointType.POCKET_SCREW


class DefaultJointSelector(JointSelector):
    """Fallback joint selector for unrecognized panel types.

    Uses simple butt joints with mechanical fasteners when no
    specific joinery strategy is defined.
    """

    def select(self, from_panel: PanelType, config: WoodworkingConfig) -> JointType:
        """Select default butt joint.

        Args:
            from_panel: Panel type that receives the joint.
            config: Woodworking configuration with defaults.

        Returns:
            BUTT joint type.
        """
        return JointType.BUTT


# Registry of joint selectors by panel type (to_panel)
# This replaces the if-elif chain and follows Open-Closed Principle
JOINT_SELECTORS: dict[PanelType, JointSelector] = {
    PanelType.SHELF: ShelfJointSelector(),
    PanelType.BACK: BackPanelJointSelector(),
    PanelType.DIVIDER: DividerJointSelector(),
    PanelType.HORIZONTAL_DIVIDER: HorizontalDividerJointSelector(),
    PanelType.TOP: TopPanelJointSelector(),
    PanelType.BOTTOM: BottomPanelJointSelector(),
    PanelType.FACE_FRAME_RAIL: FaceFrameJointSelector(),
    PanelType.FACE_FRAME_STILE: FaceFrameJointSelector(),
}

# Default selector for panel types not in the registry
_DEFAULT_SELECTOR = DefaultJointSelector()


def select_joint(
    from_panel: PanelType,
    to_panel: PanelType,
    config: WoodworkingConfig,
) -> JointType:
    """Select appropriate joint type for a panel connection.

    Uses the Strategy pattern to select the optimal joint type
    based on the panel types being connected.

    Args:
        from_panel: Panel type that receives the joint (e.g., side panel with dado).
        to_panel: Panel type that fits into the joint (e.g., shelf).
        config: Woodworking configuration with defaults.

    Returns:
        Appropriate JointType for the connection.
    """
    selector = JOINT_SELECTORS.get(to_panel, _DEFAULT_SELECTOR)
    return selector.select(from_panel, config)


class JointSpecCalculator:
    """Calculator for joint specifications based on material dimensions.

    Provides methods to calculate dado, rabbet, and fastener-based
    joint specifications with proper dimensions and positions.
    """

    def __init__(self, config: WoodworkingConfig) -> None:
        """Initialize the joint spec calculator.

        Args:
            config: Woodworking configuration.
        """
        self.config = config

    def calculate_dado_spec(self, thickness: float) -> JointSpec:
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

    def calculate_rabbet_spec(
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

    def calculate_fastener_positions(
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

    def get_pocket_screw_spec(self, length: float) -> JointSpec:
        """Generate pocket screw joint specification for a given length.

        Calculates pocket hole positions based on configured edge offset
        and spacing parameters.

        Args:
            length: Length of the joint in inches.

        Returns:
            JointSpec with pocket screw positions.
        """
        positions = self.calculate_fastener_positions(
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
        positions = self.calculate_fastener_positions(
            length=length,
            edge_offset=self.config.dowel_edge_offset,
            spacing=self.config.dowel_spacing,
        )
        return JointSpec.dowel(
            positions=positions,
            spacing=self.config.dowel_spacing,
        )
