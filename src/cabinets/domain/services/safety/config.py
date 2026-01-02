"""Safety configuration for cabinet compliance analysis.

This module contains the SafetyConfig dataclass that controls
which safety checks are performed and how they are configured.
"""

from __future__ import annotations

from dataclasses import dataclass

from cabinets.domain.value_objects import (
    ADAStandard,
    MaterialCertification,
    SeismicZone,
    VOCCategory,
)

from .constants import HIGH_SEISMIC_ZONES


@dataclass(frozen=True)
class SafetyConfig:
    """Configuration for safety analysis.

    Domain object containing all settings that control which safety
    checks are performed and how they are configured.

    Attributes:
        accessibility_enabled: Enable ADA accessibility checking.
        accessibility_standard: Which ADA standard to use.
        child_safe_mode: Enable child safety recommendations.
        seismic_zone: IBC seismic design category (A-F) or None.
        safety_factor: Safety factor for capacity calculations (default 4.0).
        deflection_limit_ratio: Deflection limit as span ratio (200 for L/200).
        check_clearances: Enable building code clearance checking.
        generate_labels: Generate safety label content.
        material_certification: Material certification level.
        finish_voc_category: Finish VOC category.
    """

    accessibility_enabled: bool = False
    accessibility_standard: ADAStandard = ADAStandard.ADA_2010
    child_safe_mode: bool = False
    seismic_zone: SeismicZone | None = None
    safety_factor: float = 4.0
    deflection_limit_ratio: int = 200  # L/200
    check_clearances: bool = True
    generate_labels: bool = True
    material_certification: MaterialCertification = MaterialCertification.UNKNOWN
    finish_voc_category: VOCCategory = VOCCategory.UNKNOWN

    def __post_init__(self) -> None:
        if self.safety_factor < 2.0 or self.safety_factor > 6.0:
            raise ValueError("safety_factor must be between 2.0 and 6.0")
        if self.deflection_limit_ratio not in {200, 240, 360}:
            raise ValueError("deflection_limit_ratio must be 200, 240, or 360")

    @property
    def requires_seismic_hardware(self) -> bool:
        """Check if seismic zone requires enhanced anchoring."""
        if self.seismic_zone is None:
            return False
        return self.seismic_zone.value in HIGH_SEISMIC_ZONES


__all__ = ["SafetyConfig"]
