"""WoodworkingIntelligence facade service.

This module provides the WoodworkingIntelligence class as a facade
that coordinates all woodworking intelligence services while
maintaining the original public API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.value_objects import CutPiece, GrainDirection, JointType, PanelType

from .capacity_calculator import CapacityCalculator
from .config import WoodworkingConfig
from .grain_advisor import GrainAdvisor
from .hardware_calculator import HardwareCalculator
from .joint_selection import JointSpecCalculator, select_joint
from .models import ConnectionJoinery, HardwareList, SpanWarning, WeightCapacity
from .span_checker import SpanChecker

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet


class WoodworkingIntelligence:
    """Professional woodworking knowledge service.

    Provides joinery specifications for cabinet construction based on
    woodworking best practices. Analyzes cabinet structure and returns
    appropriate joint types and specifications for each panel connection.

    This class serves as a facade that coordinates multiple specialized
    services while maintaining a unified public API.

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

        # Initialize sub-services
        self._joint_spec_calculator = JointSpecCalculator(self.config)
        self._span_checker = SpanChecker()
        self._capacity_calculator = CapacityCalculator()
        self._hardware_calculator = HardwareCalculator()
        self._grain_advisor = GrainAdvisor()

    # --- Joinery Methods ---

    def get_joinery(self, cabinet: "Cabinet") -> list[ConnectionJoinery]:
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

    def _select_joint(self, from_panel: PanelType, to_panel: PanelType) -> "JointType":
        """Select appropriate joint type for a panel connection.

        Uses the Strategy pattern via select_joint() function.

        Args:
            from_panel: Panel type that receives the joint.
            to_panel: Panel type that fits into the joint.

        Returns:
            Appropriate JointType for the connection.
        """
        return select_joint(from_panel, to_panel, self.config)

    def _shelf_to_side_joinery(self, cabinet: "Cabinet") -> list[ConnectionJoinery]:
        """Generate joinery for shelf-to-side panel connections."""
        connections: list[ConnectionJoinery] = []
        dado_spec = self._joint_spec_calculator.calculate_dado_spec(
            cabinet.material.thickness
        )

        for section in cabinet.sections:
            for shelf in section.shelves:
                # Left side connection
                connections.append(
                    ConnectionJoinery(
                        from_panel=PanelType.LEFT_SIDE,
                        to_panel=PanelType.SHELF,
                        joint=dado_spec,
                        location_description=f'Shelf at {shelf.position.y:.1f}" height',
                    )
                )

                # Right side connection (or divider if not last section)
                connections.append(
                    ConnectionJoinery(
                        from_panel=PanelType.RIGHT_SIDE,
                        to_panel=PanelType.SHELF,
                        joint=dado_spec,
                        location_description=f'Shelf at {shelf.position.y:.1f}" height',
                    )
                )

        return connections

    def _back_panel_joinery(self, cabinet: "Cabinet") -> list[ConnectionJoinery]:
        """Generate joinery for back panel-to-case connections."""
        connections: list[ConnectionJoinery] = []

        # Calculate rabbet dimensions
        assert cabinet.back_material is not None
        rabbet_spec = self._joint_spec_calculator.calculate_rabbet_spec(
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

    def _divider_joinery(self, cabinet: "Cabinet") -> list[ConnectionJoinery]:
        """Generate joinery for vertical divider connections."""
        connections: list[ConnectionJoinery] = []

        # Check if cabinet has dividers (more than 1 section)
        num_sections = len(cabinet.sections)
        if num_sections <= 1:
            return connections

        dado_spec = self._joint_spec_calculator.calculate_dado_spec(
            cabinet.material.thickness
        )

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

    def _top_bottom_joinery(self, cabinet: "Cabinet") -> list[ConnectionJoinery]:
        """Generate joinery for top/bottom to side panel connections."""
        connections: list[ConnectionJoinery] = []
        dado_spec = self._joint_spec_calculator.calculate_dado_spec(
            cabinet.material.thickness
        )

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

    # --- Fastener Spec Methods (delegated to JointSpecCalculator) ---

    def get_pocket_screw_spec(self, length: float):
        """Generate pocket screw joint specification for a given length.

        Args:
            length: Length of the joint in inches.

        Returns:
            JointSpec with pocket screw positions.
        """
        return self._joint_spec_calculator.get_pocket_screw_spec(length)

    def get_dowel_spec(self, length: float):
        """Generate dowel joint specification for a given length.

        Args:
            length: Length of the joint in inches.

        Returns:
            JointSpec with dowel positions.
        """
        return self._joint_spec_calculator.get_dowel_spec(length)

    # --- Span Checking Methods (delegated to SpanChecker) ---

    def check_spans(self, cabinet: "Cabinet") -> list[SpanWarning]:
        """Check all horizontal panels for span violations.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of SpanWarning objects for panels exceeding limits.
        """
        return self._span_checker.check_spans(cabinet)

    # --- Capacity Methods (delegated to CapacityCalculator) ---

    def estimate_capacity(
        self,
        thickness: float,
        depth: float,
        span: float,
        material_type,
        load_type: str = "distributed",
        panel_label: str = "Shelf",
    ) -> WeightCapacity:
        """Estimate weight capacity for a horizontal panel.

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
        return self._capacity_calculator.estimate_capacity(
            thickness=thickness,
            depth=depth,
            span=span,
            material_type=material_type,
            load_type=load_type,
            panel_label=panel_label,
        )

    def get_shelf_capacities(self, cabinet: "Cabinet") -> list[WeightCapacity]:
        """Get weight capacity estimates for all shelves in a cabinet.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of WeightCapacity objects, one per shelf.
        """
        return self._capacity_calculator.get_shelf_capacities(cabinet)

    def format_capacity_report(self, capacities: list[WeightCapacity]) -> str:
        """Format weight capacity estimates as a report.

        Args:
            capacities: List of WeightCapacity objects.

        Returns:
            Formatted report string.
        """
        return self._capacity_calculator.format_capacity_report(capacities)

    # --- Grain Direction Methods (delegated to GrainAdvisor) ---

    def get_grain_directions(
        self,
        cut_list: list[CutPiece],
    ) -> dict[str, GrainDirection]:
        """Recommend grain direction for each cut piece.

        Args:
            cut_list: List of cut pieces to analyze.

        Returns:
            Dict mapping piece labels to recommended GrainDirection.
        """
        return self._grain_advisor.get_grain_directions(cut_list)

    def annotate_cut_list(
        self,
        cut_list: list[CutPiece],
    ) -> list[CutPiece]:
        """Create new cut list with grain directions in metadata.

        Args:
            cut_list: Original cut list.

        Returns:
            New cut list with grain directions in metadata.
        """
        return self._grain_advisor.annotate_cut_list(cut_list)

    # --- Hardware Methods (delegated to HardwareCalculator) ---

    def calculate_hardware(
        self,
        cabinet: "Cabinet",
        include_overage: bool = True,
        overage_percent: float = 10.0,
    ) -> HardwareList:
        """Calculate all hardware needed for cabinet construction.

        Args:
            cabinet: Cabinet to analyze.
            include_overage: Whether to add overage percentage.
            overage_percent: Percentage of overage to add (default 10%).

        Returns:
            HardwareList with all hardware items and quantities.
        """
        joinery = self.get_joinery(cabinet)
        return self._hardware_calculator.calculate_hardware(
            cabinet=cabinet,
            joinery=joinery,
            include_overage=include_overage,
            overage_percent=overage_percent,
        )

    # --- Legacy private methods for backward compatibility ---

    def _calculate_dado_spec(self, thickness: float):
        """Calculate dado joint specification (legacy method)."""
        return self._joint_spec_calculator.calculate_dado_spec(thickness)

    def _calculate_rabbet_spec(self, back_thickness: float, case_thickness: float):
        """Calculate rabbet joint specification (legacy method)."""
        return self._joint_spec_calculator.calculate_rabbet_spec(
            back_thickness, case_thickness
        )

    def _calculate_fastener_positions(
        self, length: float, edge_offset: float, spacing: float
    ) -> tuple[float, ...]:
        """Calculate fastener positions (legacy method)."""
        return self._joint_spec_calculator.calculate_fastener_positions(
            length, edge_offset, spacing
        )

    # --- Grain Advisor private method proxies (for test compatibility) ---

    def _is_visible_panel(self, piece: CutPiece) -> bool:
        """Check if panel is visible (delegated to GrainAdvisor)."""
        return self._grain_advisor._is_visible_panel(piece)

    def _grain_for_longest_dimension(self, piece: CutPiece) -> GrainDirection:
        """Get grain direction for longest dimension (delegated to GrainAdvisor)."""
        return self._grain_advisor._grain_for_longest_dimension(piece)

    def _get_existing_grain(self, piece: CutPiece) -> GrainDirection | None:
        """Get existing grain from metadata (delegated to GrainAdvisor)."""
        return self._grain_advisor._get_existing_grain(piece)

    # --- Capacity Calculator private method proxies (for test compatibility) ---

    def _calculate_base_capacity(
        self,
        thickness: float,
        depth: float,
        span: float,
        material_type,
    ) -> float:
        """Calculate base capacity (delegated to CapacityCalculator)."""
        return self._capacity_calculator._calculate_base_capacity(
            thickness, depth, span, material_type
        )

    # --- Hardware Calculator private method proxies (for test compatibility) ---

    def _case_screws(self, cabinet: "Cabinet") -> list:
        """Calculate case screws (delegated to HardwareCalculator)."""
        return self._hardware_calculator._case_screws(cabinet)

    def _back_panel_screws(self, cabinet: "Cabinet") -> list:
        """Calculate back panel screws (delegated to HardwareCalculator)."""
        return self._hardware_calculator._back_panel_screws(cabinet)

    def _joinery_fasteners(self, cabinet: "Cabinet", joinery: list) -> list:
        """Calculate joinery fasteners (delegated to HardwareCalculator)."""
        return self._hardware_calculator._joinery_fasteners(cabinet, joinery)

    def _shelf_fasteners(self, cabinet: "Cabinet") -> list:
        """Calculate shelf fasteners (delegated to HardwareCalculator)."""
        return self._hardware_calculator._shelf_fasteners(cabinet)
