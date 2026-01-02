"""Building code clearance analysis service.

This module provides clearance checking for electrical panels,
heat sources, egress paths, and closet lighting fixtures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.value_objects import (
    ObstacleType,
    SafetyCategory,
    SafetyCheckStatus,
)

from .config import SafetyConfig
from .constants import (
    CLOSET_LIGHT_CFL_CLEARANCE,
    CLOSET_LIGHT_INCANDESCENT_CLEARANCE,
    CLOSET_LIGHT_RECESSED_CLEARANCE,
    EGRESS_ADJACENT_WARNING,
    HEAT_SOURCE_HORIZONTAL_CLEARANCE,
    HEAT_SOURCE_VERTICAL_CLEARANCE,
    NEC_PANEL_FRONT_CLEARANCE,
    NEC_PANEL_HEIGHT_CLEARANCE,
    NEC_PANEL_WIDTH_CLEARANCE,
)
from .models import SafetyCheckResult

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet, Obstacle


class ClearanceService:
    """Service for building code clearance analysis.

    Provides clearance checking against electrical panels, heat sources,
    egress paths, and closet lighting fixtures.

    Example:
        config = SafetyConfig(check_clearances=True)
        service = ClearanceService(config)
        results = service.check_clearances(cabinet, obstacles)
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize ClearanceService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def check_clearances(
        self,
        cabinet: "Cabinet",
        obstacles: list["Obstacle"],
    ) -> list[SafetyCheckResult]:
        """Check clearances from electrical panels, heat sources, egress.

        Validates cabinet positioning against building code clearance
        requirements for various obstacle types.

        Args:
            cabinet: Cabinet configuration.
            obstacles: List of obstacles to check clearances against.

        Returns:
            List of SafetyCheckResult for each clearance check.
        """
        if not self.config.check_clearances:
            return [
                SafetyCheckResult(
                    check_id="clearance_checking",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.NOT_APPLICABLE,
                    message="Clearance checking disabled",
                )
            ]

        if not obstacles:
            return [
                SafetyCheckResult(
                    check_id="clearance_checking",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.PASS,
                    message="No obstacles specified for clearance checking",
                )
            ]

        results: list[SafetyCheckResult] = []

        # Get cabinet bounds (assume cabinet positioned at origin for simplicity)
        cabinet_bounds = self._get_cabinet_bounds(cabinet)

        for obstacle in obstacles:
            obstacle_results = self._check_obstacle_clearance(
                cabinet, cabinet_bounds, obstacle
            )
            results.extend(obstacle_results)

        # Add summary if no violations found
        if not any(r.status == SafetyCheckStatus.ERROR for r in results):
            if not any(r.status == SafetyCheckStatus.WARNING for r in results):
                results.append(
                    SafetyCheckResult(
                        check_id="clearance_summary",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.PASS,
                        message="All clearance requirements met",
                    )
                )

        return results

    def _get_cabinet_bounds(self, cabinet: "Cabinet") -> dict[str, float]:
        """Get cabinet bounding box coordinates.

        Args:
            cabinet: Cabinet to get bounds for.

        Returns:
            Dictionary with left, right, bottom, top coordinates.
        """
        # Get cabinet position if available, otherwise assume origin
        x_offset = 0.0
        y_offset = 0.0  # height from floor

        if hasattr(cabinet, "position") and cabinet.position:
            x_offset = cabinet.position.x if hasattr(cabinet.position, "x") else 0.0
            y_offset = cabinet.position.y if hasattr(cabinet.position, "y") else 0.0

        return {
            "left": x_offset,
            "right": x_offset + cabinet.width,
            "bottom": y_offset,
            "top": y_offset + cabinet.height,
            "front": 0.0,
            "back": cabinet.depth,
        }

    def _check_obstacle_clearance(
        self,
        cabinet: "Cabinet",
        cabinet_bounds: dict[str, float],
        obstacle: "Obstacle",
    ) -> list[SafetyCheckResult]:
        """Check clearance from a specific obstacle.

        Args:
            cabinet: Cabinet configuration.
            cabinet_bounds: Cabinet bounding box.
            obstacle: Obstacle to check.

        Returns:
            List of SafetyCheckResult for this obstacle.
        """
        # Route to specific checker based on obstacle type
        if obstacle.obstacle_type == ObstacleType.ELECTRICAL_PANEL:
            return self._check_electrical_panel_clearance(cabinet_bounds, obstacle)
        elif obstacle.obstacle_type in (ObstacleType.COOKTOP, ObstacleType.HEAT_SOURCE):
            return self._check_heat_source_clearance(cabinet_bounds, obstacle)
        elif obstacle.obstacle_type == ObstacleType.CLOSET_LIGHT:
            return self._check_closet_light_clearance(cabinet_bounds, obstacle)
        elif obstacle.obstacle_type in (ObstacleType.WINDOW, ObstacleType.DOOR):
            if obstacle.is_egress:
                return self._check_egress_clearance(cabinet_bounds, obstacle)
            else:
                return []  # Non-egress windows/doors handled by normal obstacle avoidance
        else:
            return []  # Other obstacle types don't have special clearance requirements

    def _check_electrical_panel_clearance(
        self,
        cabinet_bounds: dict[str, float],
        obstacle: "Obstacle",
    ) -> list[SafetyCheckResult]:
        """Check NEC electrical panel clearance requirements.

        NEC Article 110.26 requires:
        - 36" clear working space in front of panel
        - 30" minimum width
        - 78" minimum height clearance

        Args:
            cabinet_bounds: Cabinet bounding box.
            obstacle: Electrical panel obstacle.

        Returns:
            List of SafetyCheckResult.
        """
        results: list[SafetyCheckResult] = []

        panel_left = obstacle.horizontal_offset
        panel_right = obstacle.horizontal_offset + obstacle.width
        panel_bottom = obstacle.bottom
        panel_top = obstacle.bottom + obstacle.height

        # Check horizontal overlap (cabinet blocks panel access)
        # The 30" width clearance zone is centered on the panel
        panel_center = (panel_left + panel_right) / 2
        clearance_left = panel_center - NEC_PANEL_WIDTH_CLEARANCE / 2
        clearance_right = panel_center + NEC_PANEL_WIDTH_CLEARANCE / 2

        horizontal_overlap = (
            cabinet_bounds["right"] > clearance_left
            and cabinet_bounds["left"] < clearance_right
        )

        # Check if cabinet is in front of panel (within 36" frontal clearance)
        # This is a 2D approximation - assumes cabinet is against same wall
        if horizontal_overlap:
            results.append(
                SafetyCheckResult(
                    check_id="electrical_panel_clearance",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.ERROR,
                    message=(
                        "Building Code Violation: Cabinet encroaches on "
                        "electrical panel clearance zone"
                    ),
                    remediation=(
                        f'Maintain minimum {NEC_PANEL_WIDTH_CLEARANCE}" clear width '
                        f'and {NEC_PANEL_FRONT_CLEARANCE}" clear depth in front of '
                        "electrical panel per NEC Article 110.26"
                    ),
                    standard_reference="NEC Article 110.26",
                    details={
                        "panel_position": {
                            "left": panel_left,
                            "right": panel_right,
                            "bottom": panel_bottom,
                            "top": panel_top,
                        },
                        "required_clearance": {
                            "front": NEC_PANEL_FRONT_CLEARANCE,
                            "width": NEC_PANEL_WIDTH_CLEARANCE,
                            "height": NEC_PANEL_HEIGHT_CLEARANCE,
                        },
                    },
                )
            )
        else:
            results.append(
                SafetyCheckResult(
                    check_id="electrical_panel_clearance",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.PASS,
                    message="Electrical panel clearance requirements met",
                    standard_reference="NEC Article 110.26",
                )
            )

        return results

    def _check_heat_source_clearance(
        self,
        cabinet_bounds: dict[str, float],
        obstacle: "Obstacle",
    ) -> list[SafetyCheckResult]:
        """Check heat source clearance requirements.

        Typical requirements:
        - 30" vertical clearance above cooktops
        - 15" horizontal clearance from heat sources

        Args:
            cabinet_bounds: Cabinet bounding box.
            obstacle: Heat source obstacle (cooktop or heat_source).

        Returns:
            List of SafetyCheckResult.
        """
        results: list[SafetyCheckResult] = []

        heat_left = obstacle.horizontal_offset
        heat_right = obstacle.horizontal_offset + obstacle.width
        heat_top = obstacle.bottom + obstacle.height

        # Check if cabinet is above heat source
        horizontal_overlap = (
            cabinet_bounds["right"] > heat_left and cabinet_bounds["left"] < heat_right
        )

        if horizontal_overlap:
            # Check vertical clearance
            vertical_gap = cabinet_bounds["bottom"] - heat_top

            if vertical_gap < HEAT_SOURCE_VERTICAL_CLEARANCE:
                results.append(
                    SafetyCheckResult(
                        check_id="heat_source_vertical_clearance",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.ERROR,
                        message=(
                            f'Fire Safety Violation: Cabinet at {vertical_gap:.1f}" '
                            f'above heat source (requires {HEAT_SOURCE_VERTICAL_CLEARANCE}" minimum)'
                        ),
                        remediation=(
                            f'Maintain minimum {HEAT_SOURCE_VERTICAL_CLEARANCE}" '
                            "vertical clearance above cooking surface"
                        ),
                        standard_reference="IRC Section R307.2",
                        details={
                            "actual_clearance": vertical_gap,
                            "required_clearance": HEAT_SOURCE_VERTICAL_CLEARANCE,
                        },
                    )
                )
            else:
                results.append(
                    SafetyCheckResult(
                        check_id="heat_source_vertical_clearance",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.PASS,
                        message=(
                            f'Heat source vertical clearance OK: {vertical_gap:.1f}" '
                            f'(requires {HEAT_SOURCE_VERTICAL_CLEARANCE}")'
                        ),
                        standard_reference="IRC Section R307.2",
                    )
                )
        else:
            # Check horizontal clearance for adjacent cabinets
            # Cabinet is to the left of heat source
            if cabinet_bounds["right"] <= heat_left:
                left_gap = heat_left - cabinet_bounds["right"]
                if left_gap < HEAT_SOURCE_HORIZONTAL_CLEARANCE:
                    results.append(
                        SafetyCheckResult(
                            check_id="heat_source_horizontal_clearance",
                            category=SafetyCategory.CLEARANCE,
                            status=SafetyCheckStatus.WARNING,
                            message=(
                                f'Fire Safety: Cabinet within {left_gap:.1f}" '
                                "of heat source"
                            ),
                            remediation=(
                                f'Consider maintaining {HEAT_SOURCE_HORIZONTAL_CLEARANCE}" '
                                "horizontal clearance from heat sources"
                            ),
                            details={
                                "actual_clearance": left_gap,
                                "recommended_clearance": HEAT_SOURCE_HORIZONTAL_CLEARANCE,
                            },
                        )
                    )
            # Cabinet is to the right of heat source
            elif cabinet_bounds["left"] >= heat_right:
                right_gap = cabinet_bounds["left"] - heat_right
                if right_gap < HEAT_SOURCE_HORIZONTAL_CLEARANCE:
                    results.append(
                        SafetyCheckResult(
                            check_id="heat_source_horizontal_clearance",
                            category=SafetyCategory.CLEARANCE,
                            status=SafetyCheckStatus.WARNING,
                            message=(
                                f'Fire Safety: Cabinet within {right_gap:.1f}" '
                                "of heat source"
                            ),
                            remediation=(
                                f'Consider maintaining {HEAT_SOURCE_HORIZONTAL_CLEARANCE}" '
                                "horizontal clearance from heat sources"
                            ),
                            details={
                                "actual_clearance": right_gap,
                                "recommended_clearance": HEAT_SOURCE_HORIZONTAL_CLEARANCE,
                            },
                        )
                    )

        return results

    def _check_egress_clearance(
        self,
        cabinet_bounds: dict[str, float],
        obstacle: "Obstacle",
    ) -> list[SafetyCheckResult]:
        """Check emergency egress clearance requirements.

        Egress windows and doors must not be blocked by cabinets.

        Args:
            cabinet_bounds: Cabinet bounding box.
            obstacle: Egress window or door obstacle.

        Returns:
            List of SafetyCheckResult.
        """
        results: list[SafetyCheckResult] = []

        egress_left = obstacle.horizontal_offset
        egress_right = obstacle.horizontal_offset + obstacle.width
        egress_bottom = obstacle.bottom
        egress_top = obstacle.bottom + obstacle.height

        # Check for direct blocking
        horizontal_overlap = (
            cabinet_bounds["right"] > egress_left
            and cabinet_bounds["left"] < egress_right
        )
        vertical_overlap = (
            cabinet_bounds["top"] > egress_bottom
            and cabinet_bounds["bottom"] < egress_top
        )

        if horizontal_overlap and vertical_overlap:
            results.append(
                SafetyCheckResult(
                    check_id="egress_clearance",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.ERROR,
                    message=(
                        f"Egress Violation: Cabinet blocks emergency egress "
                        f"{obstacle.obstacle_type.value}"
                    ),
                    remediation=(
                        "Do not obstruct emergency egress paths. "
                        "Relocate cabinet to maintain clear access to egress opening."
                    ),
                    standard_reference="IFC Section 1031 / IRC R310",
                    details={
                        "egress_type": obstacle.obstacle_type.value,
                        "egress_position": {
                            "left": egress_left,
                            "right": egress_right,
                            "bottom": egress_bottom,
                            "top": egress_top,
                        },
                    },
                )
            )
        else:
            # Check if cabinet is adjacent (within warning distance)
            # Calculate distances to egress
            if cabinet_bounds["right"] <= egress_left:
                horizontal_distance = egress_left - cabinet_bounds["right"]
            elif cabinet_bounds["left"] >= egress_right:
                horizontal_distance = cabinet_bounds["left"] - egress_right
            else:
                horizontal_distance = 0  # Overlap

            adjacent = (
                horizontal_distance < EGRESS_ADJACENT_WARNING and vertical_overlap
            )

            if adjacent:
                results.append(
                    SafetyCheckResult(
                        check_id="egress_adjacent_warning",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.WARNING,
                        message=(
                            f'Cabinet within {EGRESS_ADJACENT_WARNING}" of egress '
                            f"{obstacle.obstacle_type.value}"
                        ),
                        remediation=(
                            "Verify cabinet does not impede emergency egress access"
                        ),
                        standard_reference="IFC Section 1031",
                    )
                )
            else:
                results.append(
                    SafetyCheckResult(
                        check_id="egress_clearance",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.PASS,
                        message="Egress clearance requirements met",
                        standard_reference="IFC Section 1031",
                    )
                )

        return results

    def _check_closet_light_clearance(
        self,
        cabinet_bounds: dict[str, float],
        obstacle: "Obstacle",
    ) -> list[SafetyCheckResult]:
        """Check closet lighting fixture clearance requirements.

        NEC 410.16 requires clearances from storage:
        - 12" for incandescent/surface fixtures
        - 6" for recessed fixtures
        - 6" for CFL/LED fixtures

        Args:
            cabinet_bounds: Cabinet bounding box.
            obstacle: Closet light fixture obstacle.

        Returns:
            List of SafetyCheckResult.
        """
        results: list[SafetyCheckResult] = []

        light_left = obstacle.horizontal_offset
        light_right = obstacle.horizontal_offset + obstacle.width
        light_bottom = obstacle.bottom

        # Determine fixture type and required clearance
        # Default to most conservative (incandescent) clearance
        required_clearance = CLOSET_LIGHT_INCANDESCENT_CLEARANCE

        # Check if fixture info in obstacle name or use default
        fixture_type = "incandescent/surface"
        if obstacle.name:
            name_lower = obstacle.name.lower()
            if "recessed" in name_lower:
                required_clearance = CLOSET_LIGHT_RECESSED_CLEARANCE
                fixture_type = "recessed"
            elif "led" in name_lower or "cfl" in name_lower:
                required_clearance = CLOSET_LIGHT_CFL_CLEARANCE
                fixture_type = "LED/CFL"

        # Check if cabinet top is within clearance zone below fixture
        # Expand horizontal check zone by 6" on each side
        horizontal_overlap = (
            cabinet_bounds["right"] > light_left - 6
            and cabinet_bounds["left"] < light_right + 6
        )

        if horizontal_overlap:
            vertical_gap = light_bottom - cabinet_bounds["top"]

            if vertical_gap < required_clearance:
                results.append(
                    SafetyCheckResult(
                        check_id="closet_light_clearance",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.ERROR,
                        message=(
                            f'NEC Violation: Storage within {vertical_gap:.1f}" of '
                            f'{fixture_type} closet light (requires {required_clearance}")'
                        ),
                        remediation=(
                            f'Maintain minimum {required_clearance}" clearance '
                            f"between storage and {fixture_type} lighting fixtures "
                            "per NEC 410.16"
                        ),
                        standard_reference="NEC 410.16",
                        details={
                            "fixture_type": fixture_type,
                            "actual_clearance": vertical_gap,
                            "required_clearance": required_clearance,
                        },
                    )
                )
            else:
                results.append(
                    SafetyCheckResult(
                        check_id="closet_light_clearance",
                        category=SafetyCategory.CLEARANCE,
                        status=SafetyCheckStatus.PASS,
                        message=(
                            f'Closet light clearance OK: {vertical_gap:.1f}" '
                            f'(requires {required_clearance}")'
                        ),
                        standard_reference="NEC 410.16",
                    )
                )

        return results


__all__ = ["ClearanceService"]
