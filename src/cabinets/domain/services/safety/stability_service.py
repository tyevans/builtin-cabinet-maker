"""Cabinet stability and anti-tip analysis service.

This module provides anti-tip requirement checking and stability
analysis for cabinet configurations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.value_objects import SafetyCategory, SafetyCheckStatus

from .config import SafetyConfig
from .constants import ANTI_TIP_HEIGHT_THRESHOLD
from .models import SafetyCheckResult

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet


class StabilityService:
    """Service for cabinet stability analysis.

    Provides anti-tip requirement checking and stability ratio
    analysis for cabinet configurations.

    Example:
        config = SafetyConfig(child_safe_mode=True)
        service = StabilityService(config)
        result = service.check_anti_tip_requirement(cabinet)
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize StabilityService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def is_wall_mounted(self, cabinet: "Cabinet") -> bool:
        """Check if cabinet is configured for wall mounting.

        A cabinet is considered wall-mounted if it has a mounting system
        configured, is marked as a built-in, or is part of a room layout
        (indicating it's attached to a wall).

        Args:
            cabinet: Cabinet to check.

        Returns:
            True if cabinet has wall mounting configured.
        """
        # Check if cabinet has mounting_system attribute (from installation config)
        if hasattr(cabinet, "mounting_system") and cabinet.mounting_system is not None:
            return True

        # Check if cabinet is marked as built-in
        if hasattr(cabinet, "is_builtin") and cabinet.is_builtin:
            return True

        # Check if cabinet has wall reference (part of room layout)
        if hasattr(cabinet, "wall_index") and cabinet.wall_index is not None:
            return True

        # Default: freestanding cabinet
        return False

    def check_anti_tip_requirement(self, cabinet: "Cabinet") -> SafetyCheckResult:
        """Check if cabinet requires anti-tip restraint.

        Units >= 27" tall that are not wall-mounted require anti-tip
        restraint per ASTM F2057-23 guidance. Note that built-in furniture
        is exempt from mandatory requirements, but guidance is provided
        as a safety best practice.

        Args:
            cabinet: Cabinet to check.

        Returns:
            SafetyCheckResult indicating anti-tip requirement status.
        """
        height = cabinet.height

        # Check if cabinet is wall-mounted (has mounting system configured)
        is_wall_mounted = self.is_wall_mounted(cabinet)

        if is_wall_mounted:
            return SafetyCheckResult(
                check_id="anti_tip_requirement",
                category=SafetyCategory.STABILITY,
                status=SafetyCheckStatus.PASS,
                message=(
                    f'Cabinet height {height:.1f}" - wall-mounted installation '
                    "provides tip-over protection"
                ),
                standard_reference="ASTM F2057-23 (guidance)",
                details={
                    "height": height,
                    "is_wall_mounted": True,
                    "anti_tip_required": False,
                },
            )

        if height < ANTI_TIP_HEIGHT_THRESHOLD:
            return SafetyCheckResult(
                check_id="anti_tip_requirement",
                category=SafetyCategory.STABILITY,
                status=SafetyCheckStatus.PASS,
                message=(
                    f'Cabinet height {height:.1f}" below {ANTI_TIP_HEIGHT_THRESHOLD}" threshold - '
                    "anti-tip restraint not required"
                ),
                standard_reference="ASTM F2057-23 (guidance)",
                details={
                    "height": height,
                    "threshold": ANTI_TIP_HEIGHT_THRESHOLD,
                    "is_wall_mounted": False,
                    "anti_tip_required": False,
                },
            )

        # Calculate tip-over risk factor based on height-to-depth ratio
        depth = cabinet.depth
        height_to_depth_ratio = height / depth if depth > 0 else float("inf")
        risk_level = "high" if height_to_depth_ratio > 4 else "moderate"

        return SafetyCheckResult(
            check_id="anti_tip_requirement",
            category=SafetyCategory.STABILITY,
            status=SafetyCheckStatus.WARNING,
            message=(
                f'Anti-tip restraint required: Cabinet height {height:.1f}" '
                f'exceeds {ANTI_TIP_HEIGHT_THRESHOLD}" threshold'
            ),
            remediation=(
                "WARNING: To reduce the risk of tip-over, furniture must be anchored to the wall. "
                "Install anti-tip strap or bracket to secure cabinet to wall. "
                'Mount 4" from cabinet top into wall stud or use appropriate anchor.'
            ),
            standard_reference="ASTM F2057-23 (guidance)",
            details={
                "height": height,
                "depth": depth,
                "threshold": ANTI_TIP_HEIGHT_THRESHOLD,
                "height_to_depth_ratio": round(height_to_depth_ratio, 2),
                "risk_level": risk_level,
                "is_wall_mounted": False,
                "anti_tip_required": True,
            },
        )

    def get_anti_tip_hardware(self, cabinet: "Cabinet") -> list[str]:
        """Get recommended anti-tip hardware for a cabinet.

        Generates a list of hardware recommendations for cabinets that
        require anti-tip restraint based on height and mounting status.

        Args:
            cabinet: Cabinet requiring anti-tip protection.

        Returns:
            List of hardware recommendations. Empty list if no anti-tip needed.
        """
        height = cabinet.height

        # No hardware needed for short or wall-mounted cabinets
        if height < ANTI_TIP_HEIGHT_THRESHOLD or self.is_wall_mounted(cabinet):
            return []

        hardware: list[str] = []

        # Base anti-tip strap recommendation
        hardware.append("Anti-tip furniture strap kit (qty: 1)")

        # Mounting position guidance
        hardware.append("Mounting position: 4 inches from top")

        # Additional recommendations based on height
        if height >= 48:
            hardware.append(
                "Anti-tip bracket with lag screw (qty: 2) - for added security"
            )

        if height >= 72:
            hardware.append(
                "Consider L-bracket wall attachment at top corners (qty: 2)"
            )

        # Wall fastener recommendations
        hardware.append(
            '#10 x 3" wood screw for stud mounting (qty: 2) - OR - '
            '1/4" toggle bolt for drywall (qty: 2)'
        )

        return hardware

    def check_stability(self, cabinet: "Cabinet") -> list[SafetyCheckResult]:
        """Perform stability checks including anti-tip requirement.

        Comprehensive stability analysis including anti-tip checks,
        height-to-depth ratio warnings, and child safety considerations.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of SafetyCheckResult for stability checks.
        """
        results: list[SafetyCheckResult] = []

        # Anti-tip check
        anti_tip_result = self.check_anti_tip_requirement(cabinet)
        results.append(anti_tip_result)

        # Height-to-depth ratio warning for tall narrow units
        if cabinet.depth > 0:
            ratio = cabinet.height / cabinet.depth

            if ratio > 5:
                results.append(
                    SafetyCheckResult(
                        check_id="stability_ratio",
                        category=SafetyCategory.STABILITY,
                        status=SafetyCheckStatus.WARNING,
                        message=(
                            f"High tip-over risk: Height-to-depth ratio {ratio:.1f}:1 "
                            f"(cabinet is {ratio:.1f}x taller than deep)"
                        ),
                        remediation=(
                            "Ensure secure wall attachment. Consider adding ballast "
                            "to lower sections or widening the base."
                        ),
                        details={
                            "height": cabinet.height,
                            "depth": cabinet.depth,
                            "ratio": round(ratio, 2),
                        },
                    )
                )
            elif ratio > 3:
                results.append(
                    SafetyCheckResult(
                        check_id="stability_ratio",
                        category=SafetyCategory.STABILITY,
                        status=SafetyCheckStatus.PASS,
                        message=(
                            f"Moderate stability: Height-to-depth ratio {ratio:.1f}:1"
                        ),
                        details={
                            "height": cabinet.height,
                            "depth": cabinet.depth,
                            "ratio": round(ratio, 2),
                        },
                    )
                )

        # Child safety mode adds extra warnings
        if self.config.child_safe_mode and cabinet.height >= ANTI_TIP_HEIGHT_THRESHOLD:
            results.append(
                SafetyCheckResult(
                    check_id="child_safety_tip_over",
                    category=SafetyCategory.CHILD_SAFETY,
                    status=SafetyCheckStatus.WARNING,
                    message=(
                        "CHILD SAFETY: Furniture tip-over is a leading cause of "
                        "injury to children. Secure this unit to the wall."
                    ),
                    remediation=(
                        "Install anti-tip restraint before use. "
                        "Do not allow children to climb on furniture. "
                        "Store heavier items on lower shelves."
                    ),
                    standard_reference="CPSC Safety Alert",
                    details={
                        "child_safe_mode": True,
                        "height": cabinet.height,
                    },
                )
            )

        return results


__all__ = ["StabilityService"]
