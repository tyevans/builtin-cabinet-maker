"""Material compliance and certification service.

This module provides material certification validation and
VOC compliance checking for cabinet materials.
"""

from __future__ import annotations

from cabinets.domain.value_objects import (
    MaterialCertification,
    SafetyCategory,
    SafetyCheckStatus,
    VOCCategory,
)

from .config import SafetyConfig
from .models import SafetyCheckResult


class MaterialComplianceService:
    """Service for material compliance analysis.

    Provides material certification and VOC compliance checking
    for cabinet configurations.

    Example:
        config = SafetyConfig(material_certification=MaterialCertification.CARB_PHASE2)
        service = MaterialComplianceService(config)
        result = service.check_material_compliance()
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize MaterialComplianceService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def check_material_compliance(self) -> SafetyCheckResult:
        """Check material certification compliance.

        Validates material certification configuration and generates
        appropriate warnings for unspecified certifications.

        Returns:
            SafetyCheckResult for material compliance.
        """
        if self.config.material_certification == MaterialCertification.UNKNOWN:
            return SafetyCheckResult(
                check_id="material_certification",
                category=SafetyCategory.MATERIAL,
                status=SafetyCheckStatus.WARNING,
                message="Material certification not specified",
                remediation=(
                    "Verify CARB Phase 2 compliance for US sales. "
                    "Request documentation from material supplier."
                ),
                standard_reference="CARB ATCM 93120 / EPA TSCA Title VI",
            )
        elif self.config.material_certification == MaterialCertification.NONE:
            return SafetyCheckResult(
                check_id="material_certification",
                category=SafetyCategory.MATERIAL,
                status=SafetyCheckStatus.ERROR,
                message="Materials marked as non-compliant with formaldehyde standards",
                remediation=(
                    "Use CARB Phase 2 compliant, NAF, or ULEF certified materials "
                    "for composite wood products."
                ),
                standard_reference="CARB ATCM 93120 / EPA TSCA Title VI",
            )
        else:
            cert_name = {
                MaterialCertification.CARB_PHASE2: "CARB Phase 2",
                MaterialCertification.NAF: "No Added Formaldehyde (NAF)",
                MaterialCertification.ULEF: "Ultra-Low Emitting Formaldehyde (ULEF)",
            }.get(self.config.material_certification, "Unknown")

            return SafetyCheckResult(
                check_id="material_certification",
                category=SafetyCategory.MATERIAL,
                status=SafetyCheckStatus.PASS,
                message=f"Material certification: {cert_name}",
                standard_reference="CARB ATCM 93120 / EPA TSCA Title VI",
            )

    def generate_material_notes(self) -> list[str]:
        """Generate material safety notes based on configuration.

        Returns:
            List of material safety note strings.
        """
        notes: list[str] = []

        # Certification note
        if self.config.material_certification == MaterialCertification.UNKNOWN:
            notes.append(
                "Material certification not specified. Verify CARB Phase 2 or "
                "equivalent compliance before use."
            )
        elif self.config.material_certification == MaterialCertification.NAF:
            notes.append(
                "No Added Formaldehyde (NAF) certified materials specified. "
                "Suitable for sensitive environments."
            )
        elif self.config.material_certification == MaterialCertification.ULEF:
            notes.append(
                "Ultra-Low Emitting Formaldehyde (ULEF) materials specified. "
                "Exceeds standard emission requirements."
            )

        # VOC note
        if self.config.finish_voc_category == VOCCategory.UNKNOWN:
            notes.append(
                "Finish VOC category not specified. Use low-VOC finishes "
                "in occupied spaces."
            )
        elif self.config.finish_voc_category == VOCCategory.COMPLIANT:
            notes.append(
                "Low-VOC (compliant) finish specified. Allow adequate ventilation during curing."
            )
        elif self.config.finish_voc_category == VOCCategory.SUPER_COMPLIANT:
            notes.append(
                "Super-compliant (near-zero VOC) finish specified. Minimal off-gassing expected."
            )

        return notes


__all__ = ["MaterialComplianceService"]
