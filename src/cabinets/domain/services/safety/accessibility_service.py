"""ADA accessibility compliance analysis service.

This module provides ADA accessibility validation including
reach range checking and accessible storage percentage calculation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cabinets.domain.value_objects import SafetyCategory, SafetyCheckStatus

from .config import SafetyConfig
from .constants import (
    ADA_MAX_OBSTRUCTION_DEPTH,
    ADA_MAX_REACH_OBSTRUCTED,
    ADA_MAX_REACH_UNOBSTRUCTED,
    ADA_MIN_ACCESSIBLE_PERCENTAGE,
    ADA_MIN_REACH,
)
from .models import AccessibilityReport, SafetyCheckResult

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet


class AccessibilityService:
    """Service for ADA accessibility analysis.

    Provides reach range validation and accessible storage
    percentage calculations for cabinet configurations.

    Example:
        config = SafetyConfig(accessibility_enabled=True)
        service = AccessibilityService(config)
        report = service.analyze_accessibility(cabinet)
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize AccessibilityService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def analyze_accessibility(self, cabinet: "Cabinet") -> AccessibilityReport:
        """Analyze ADA accessibility compliance.

        Validates reach ranges and calculates accessible storage
        percentage against ADA requirements. Checks that at least
        50% of storage is within accessible reach range.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            AccessibilityReport with compliance details.
        """
        if not self.config.accessibility_enabled:
            # Return minimal report when disabled
            return AccessibilityReport(
                total_storage_volume=0.0,
                accessible_storage_volume=0.0,
                accessible_percentage=0.0,
                is_compliant=True,  # Not applicable when disabled
                non_compliant_areas=(),
                reach_violations=(),
                hardware_notes=(),
                standard=self.config.accessibility_standard,
            )

        # Calculate total and accessible storage volumes
        total_volume = 0.0
        accessible_volume = 0.0
        non_compliant_areas: list[str] = []
        reach_violations: list[str] = []

        # Get floor offset if cabinet is wall-mounted
        floor_offset = self._get_cabinet_floor_offset(cabinet)

        for section_idx, section in enumerate(cabinet.sections):
            for shelf_idx, shelf in enumerate(section.shelves):
                # Calculate shelf position from floor
                shelf_height_from_floor = self._calculate_shelf_height(
                    cabinet, section, shelf, shelf_idx, floor_offset
                )

                # Calculate storage volume for this shelf area
                shelf_width = section.width - (2 * cabinet.material.thickness)
                shelf_depth = cabinet.depth - cabinet.material.thickness
                # Assume shelf height is distance to next shelf or top
                shelf_storage_height = self._get_shelf_storage_height(
                    cabinet, section, shelf_idx
                )

                shelf_volume = shelf_width * shelf_depth * shelf_storage_height
                total_volume += shelf_volume

                # Check if shelf is within accessible reach range
                is_accessible, violation = self._check_shelf_accessibility(
                    shelf_height_from_floor,
                    shelf_storage_height,
                    cabinet.depth,
                    section_idx,
                    shelf_idx,
                )

                if is_accessible:
                    accessible_volume += shelf_volume
                else:
                    non_compliant_areas.append(
                        f"Section {section_idx}, Shelf {shelf_idx}: "
                        f'height {shelf_height_from_floor:.1f}" from floor'
                    )
                    if violation:
                        reach_violations.append(violation)

        # Calculate accessible percentage
        accessible_percentage = (
            (accessible_volume / total_volume * 100) if total_volume > 0 else 0.0
        )

        is_compliant = accessible_percentage >= ADA_MIN_ACCESSIBLE_PERCENTAGE

        # Generate hardware notes
        hardware_notes = self._generate_accessibility_hardware_notes()

        return AccessibilityReport(
            total_storage_volume=round(total_volume, 2),
            accessible_storage_volume=round(accessible_volume, 2),
            accessible_percentage=round(accessible_percentage, 1),
            is_compliant=is_compliant,
            non_compliant_areas=tuple(non_compliant_areas),
            reach_violations=tuple(reach_violations),
            hardware_notes=tuple(hardware_notes),
            standard=self.config.accessibility_standard,
        )

    def _get_cabinet_floor_offset(self, cabinet: "Cabinet") -> float:
        """Get the distance from floor to cabinet bottom.

        Args:
            cabinet: Cabinet to check.

        Returns:
            Height in inches from floor to cabinet bottom.
        """
        # Check for wall-mounted cabinet with height offset
        if hasattr(cabinet, "floor_offset") and cabinet.floor_offset is not None:
            return cabinet.floor_offset

        # Check for toe kick
        if hasattr(cabinet, "toe_kick_height") and cabinet.toe_kick_height:
            return cabinet.toe_kick_height

        # Default: cabinet sits on floor
        return 0.0

    def _calculate_shelf_height(
        self,
        cabinet: "Cabinet",
        section: Any,
        shelf: Any,
        shelf_idx: int,
        floor_offset: float,
    ) -> float:
        """Calculate shelf height from floor.

        Args:
            cabinet: Parent cabinet.
            section: Section containing the shelf.
            shelf: Shelf object.
            shelf_idx: Index of shelf in section.
            floor_offset: Height of cabinet bottom from floor.

        Returns:
            Height of shelf surface from floor in inches.
        """
        # If shelf has explicit height property
        if hasattr(shelf, "height_from_bottom"):
            return floor_offset + shelf.height_from_bottom

        # Calculate based on equal spacing
        section_height = (
            section.height if hasattr(section, "height") else cabinet.height
        )
        num_shelves = len(section.shelves)

        if num_shelves == 0:
            return floor_offset

        # Account for top/bottom panels
        usable_height = section_height - (2 * cabinet.material.thickness)
        shelf_spacing = usable_height / (num_shelves + 1)

        return (
            floor_offset
            + cabinet.material.thickness
            + (shelf_spacing * (shelf_idx + 1))
        )

    def _get_shelf_storage_height(
        self,
        cabinet: "Cabinet",
        section: Any,
        shelf_idx: int,
    ) -> float:
        """Get usable storage height above a shelf.

        Args:
            cabinet: Parent cabinet.
            section: Section containing the shelf.
            shelf_idx: Index of shelf in section.

        Returns:
            Usable storage height in inches.
        """
        section_height = (
            section.height if hasattr(section, "height") else cabinet.height
        )
        num_shelves = len(section.shelves)

        if num_shelves == 0:
            return section_height - (2 * cabinet.material.thickness)

        usable_height = section_height - (2 * cabinet.material.thickness)
        return usable_height / (num_shelves + 1)

    def _check_shelf_accessibility(
        self,
        shelf_height: float,
        storage_height: float,
        cabinet_depth: float,
        section_idx: int,
        shelf_idx: int,
    ) -> tuple[bool, str | None]:
        """Check if a shelf is within ADA accessible reach range.

        Args:
            shelf_height: Height of shelf from floor.
            storage_height: Usable height above shelf.
            cabinet_depth: Depth of cabinet (affects obstructed reach).
            section_idx: Section index for error messages.
            shelf_idx: Shelf index for error messages.

        Returns:
            Tuple of (is_accessible, violation_message).
        """
        # Determine if reach is obstructed (over countertop scenario)
        is_obstructed = cabinet_depth > ADA_MAX_OBSTRUCTION_DEPTH

        if is_obstructed:
            max_reach = ADA_MAX_REACH_OBSTRUCTED
            reach_type = "obstructed"
        else:
            max_reach = ADA_MAX_REACH_UNOBSTRUCTED
            reach_type = "unobstructed"

        # Check if shelf surface is within reach range
        shelf_too_high = shelf_height > max_reach
        shelf_too_low = shelf_height < ADA_MIN_REACH

        if shelf_too_high:
            return False, (
                f"Section {section_idx}, Shelf {shelf_idx}: "
                f'Shelf at {shelf_height:.1f}" exceeds {max_reach}" '
                f"{reach_type} reach maximum"
            )

        if shelf_too_low:
            return False, (
                f"Section {section_idx}, Shelf {shelf_idx}: "
                f'Shelf at {shelf_height:.1f}" below {ADA_MIN_REACH}" '
                f"minimum reach height"
            )

        return True, None

    def _generate_accessibility_hardware_notes(self) -> list[str]:
        """Generate hardware recommendations for accessibility.

        Returns:
            List of hardware recommendation strings.
        """
        notes: list[str] = []

        notes.append(
            "ADA: Select hardware operable without tight grasping, pinching, "
            "or wrist twisting"
        )
        notes.append("Recommended: Lever-style handles, D-pulls, or loop handles")
        notes.append(
            "Avoid: Small knobs, recessed pulls, or touch latches that require "
            "precise finger control"
        )
        notes.append("Door/drawer operation should require no more than 5 lbf of force")

        return notes

    def check_accessibility(self, cabinet: "Cabinet") -> list[SafetyCheckResult]:
        """Perform accessibility checks.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of SafetyCheckResult for accessibility checks.
        """
        results: list[SafetyCheckResult] = []

        if not self.config.accessibility_enabled:
            results.append(
                SafetyCheckResult(
                    check_id="accessibility_analysis",
                    category=SafetyCategory.ACCESSIBILITY,
                    status=SafetyCheckStatus.NOT_APPLICABLE,
                    message="Accessibility checking not enabled",
                )
            )
            return results

        report = self.analyze_accessibility(cabinet)

        # Overall compliance check
        if report.is_compliant:
            results.append(
                SafetyCheckResult(
                    check_id="accessibility_compliance",
                    category=SafetyCategory.ACCESSIBILITY,
                    status=SafetyCheckStatus.PASS,
                    message=(
                        f"Accessibility compliant: {report.accessible_percentage:.1f}% "
                        f"of storage within reach range (requires 50%)"
                    ),
                    standard_reference="2010 ADA Standards",
                    details={
                        "accessible_percentage": report.accessible_percentage,
                        "total_volume": report.total_storage_volume,
                        "accessible_volume": report.accessible_storage_volume,
                    },
                )
            )
        else:
            results.append(
                SafetyCheckResult(
                    check_id="accessibility_compliance",
                    category=SafetyCategory.ACCESSIBILITY,
                    status=SafetyCheckStatus.ERROR,
                    message=(
                        f"Accessibility non-compliant: {report.accessible_percentage:.1f}% "
                        f"of storage within reach range (requires 50% minimum)"
                    ),
                    remediation=(
                        "Lower cabinet mounting height or reduce shelf heights "
                        'to bring more storage within 15-48" reach range'
                    ),
                    standard_reference="2010 ADA Standards",
                    details={
                        "accessible_percentage": report.accessible_percentage,
                        "required_percentage": ADA_MIN_ACCESSIBLE_PERCENTAGE,
                        "total_volume": report.total_storage_volume,
                        "accessible_volume": report.accessible_storage_volume,
                    },
                )
            )

        # Individual reach violations
        for violation in report.reach_violations:
            results.append(
                SafetyCheckResult(
                    check_id="accessibility_reach_violation",
                    category=SafetyCategory.ACCESSIBILITY,
                    status=SafetyCheckStatus.WARNING,
                    message=violation,
                    remediation="Adjust shelf height or cabinet position",
                    standard_reference="2010 ADA Standards 308.2",
                )
            )

        return results


__all__ = ["AccessibilityService"]
