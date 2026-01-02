"""Seismic zone compliance service.

This module provides seismic zone requirement checking and
hardware recommendations for cabinet installations.
"""

from __future__ import annotations

from cabinets.domain.value_objects import SafetyCategory, SafetyCheckStatus

from .config import SafetyConfig
from .models import SafetyCheckResult


class SeismicService:
    """Service for seismic compliance analysis.

    Provides seismic zone checking and hardware recommendations
    for cabinet installations in earthquake-prone areas.

    Example:
        config = SafetyConfig(seismic_zone=SeismicZone.D)
        service = SeismicService(config)
        result = service.check_seismic_requirements()
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize SeismicService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def check_seismic_requirements(self) -> SafetyCheckResult:
        """Check seismic zone requirements.

        Identifies if enhanced anchoring is required based on
        seismic zone configuration.

        Returns:
            SafetyCheckResult for seismic requirements.
        """
        if self.config.seismic_zone is None:
            return SafetyCheckResult(
                check_id="seismic_zone",
                category=SafetyCategory.SEISMIC,
                status=SafetyCheckStatus.NOT_APPLICABLE,
                message="Seismic zone not specified",
            )

        if self.config.requires_seismic_hardware:
            return SafetyCheckResult(
                check_id="seismic_zone",
                category=SafetyCategory.SEISMIC,
                status=SafetyCheckStatus.WARNING,
                message=(
                    f"Seismic Zone {self.config.seismic_zone.value}: "
                    "Enhanced anchoring required"
                ),
                remediation=(
                    "Use seismic-rated anchoring hardware. "
                    "Consult structural engineer for installations in "
                    "Seismic Design Category D or higher."
                ),
                standard_reference="CBC Section 1617A / IBC Seismic",
            )
        else:
            return SafetyCheckResult(
                check_id="seismic_zone",
                category=SafetyCategory.SEISMIC,
                status=SafetyCheckStatus.PASS,
                message=(
                    f"Seismic Zone {self.config.seismic_zone.value}: "
                    "Standard anchoring acceptable"
                ),
                standard_reference="IBC Seismic",
            )

    def get_seismic_hardware(self) -> list[str]:
        """Get list of recommended seismic hardware.

        Returns:
            List of hardware recommendations for seismic zones.
        """
        if not self.config.requires_seismic_hardware:
            return []

        return [
            "Seismic-rated wall anchor (qty: per mounting point)",
            'Steel angle bracket with 1/4" lag screws (qty: 2 per cabinet)',
            "Threaded rod tie-down (optional, for tall units)",
        ]


__all__ = ["SeismicService"]
