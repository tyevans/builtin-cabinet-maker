"""Safety service facade that orchestrates all safety sub-services.

This module provides the main SafetyService class that maintains
backward compatibility while delegating to specialized sub-services.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .accessibility_service import AccessibilityService
from .clearance_service import ClearanceService
from .config import SafetyConfig
from .constants import ANTI_TIP_HEIGHT_THRESHOLD, CHILD_ENTRAPMENT_VOLUME_THRESHOLD
from .material_compliance import MaterialComplianceService
from .models import (
    AccessibilityReport,
    SafetyAssessment,
    SafetyCheckResult,
    SafetyLabel,
    WeightCapacityEstimate,
)
from .reporting_service import ReportingService
from .seismic_service import SeismicService
from .stability_service import StabilityService
from .structural_safety import StructuralSafetyService

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet, Obstacle, Panel


class SafetyService:
    """Service for analyzing cabinet safety and compliance.

    Provides comprehensive safety analysis including structural safety,
    stability (anti-tip), accessibility, building code clearances,
    material safety, and seismic requirements.

    All safety guidance is advisory only and includes appropriate
    disclaimers. This service does not provide engineering certification.

    This is a facade that orchestrates specialized sub-services for
    each safety domain while maintaining the original API.

    Example:
        config = SafetyConfig(accessibility_enabled=True, safety_factor=4.0)
        service = SafetyService(config)
        assessment = service.analyze(cabinet, obstacles)

        if assessment.has_errors:
            for error in assessment.get_errors():
                print(error.formatted_message)
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize SafetyService with configuration.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

        # Initialize sub-services
        self._structural = StructuralSafetyService(config)
        self._stability = StabilityService(config)
        self._accessibility = AccessibilityService(config)
        self._clearance = ClearanceService(config)
        self._material = MaterialComplianceService(config)
        self._seismic = SeismicService(config)
        self._reporting = ReportingService(config)

    def analyze(
        self,
        cabinet: "Cabinet",
        obstacles: list["Obstacle"] | None = None,
    ) -> SafetyAssessment:
        """Perform complete safety analysis on a cabinet configuration.

        Runs all enabled safety checks and aggregates results into
        a comprehensive SafetyAssessment.

        Args:
            cabinet: Cabinet configuration to analyze.
            obstacles: Optional list of obstacles for clearance checking.

        Returns:
            Complete SafetyAssessment with all check results.
        """
        all_results: list[SafetyCheckResult] = []

        # 1. Structural safety checks (weight capacity, span limits)
        structural_results = self._structural.check_structural_safety(cabinet)
        all_results.extend(structural_results)

        # 2. Stability checks (anti-tip requirements)
        stability_results = self._stability.check_stability(cabinet)
        all_results.extend(stability_results)

        # 3. Accessibility checks (ADA compliance)
        accessibility_results = self._accessibility.check_accessibility(cabinet)
        all_results.extend(accessibility_results)

        # 4. Clearance checks (building codes)
        if obstacles is not None:
            clearance_results = self._clearance.check_clearances(cabinet, obstacles)
            all_results.extend(clearance_results)

        # 5. Material compliance
        material_result = self._material.check_material_compliance()
        all_results.append(material_result)

        # 6. Seismic requirements
        seismic_result = self._seismic.check_seismic_requirements()
        all_results.append(seismic_result)

        # Gather weight capacities
        weight_capacities = self._structural.get_shelf_capacities(cabinet)

        # Gather accessibility report
        accessibility_report: AccessibilityReport | None = None
        if self.config.accessibility_enabled:
            accessibility_report = self._accessibility.analyze_accessibility(cabinet)

        # Determine anti-tip requirement
        anti_tip_result = self._stability.check_anti_tip_requirement(cabinet)
        anti_tip_required = anti_tip_result.details.get("anti_tip_required", False)

        # Gather seismic hardware recommendations
        seismic_hardware = self._seismic.get_seismic_hardware()

        # Generate child safety notes if enabled
        child_safety_notes: list[str] = []
        if self.config.child_safe_mode:
            child_safety_notes = self._generate_child_safety_notes(cabinet)

        # Generate material notes
        material_notes = self._material.generate_material_notes()

        # Create assessment (labels will be generated if config.generate_labels is True)
        assessment = SafetyAssessment(
            check_results=all_results,
            weight_capacities=weight_capacities,
            accessibility_report=accessibility_report,
            safety_labels=[],  # Populated below if enabled
            anti_tip_required=anti_tip_required,
            seismic_hardware=seismic_hardware,
            child_safety_notes=child_safety_notes,
            material_notes=material_notes,
        )

        # Generate safety labels if enabled
        if self.config.generate_labels:
            assessment.safety_labels.extend(
                self._reporting.generate_safety_labels(assessment)
            )

        return assessment

    # =========================================================================
    # Delegated methods for backward compatibility
    # =========================================================================

    def calculate_weight_capacity(
        self, panel: "Panel"
    ) -> WeightCapacityEstimate | None:
        """Calculate weight capacity for a shelf panel.

        Delegates to StructuralSafetyService.

        Args:
            panel: Panel to calculate capacity for.

        Returns:
            WeightCapacityEstimate or None if panel is not a shelf.
        """
        return self._structural.calculate_weight_capacity(panel)

    def get_shelf_capacities(self, cabinet: "Cabinet") -> list[WeightCapacityEstimate]:
        """Get weight capacity estimates for all shelves in a cabinet.

        Delegates to StructuralSafetyService.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of WeightCapacityEstimate for all shelf panels.
        """
        return self._structural.get_shelf_capacities(cabinet)

    def check_anti_tip_requirement(self, cabinet: "Cabinet") -> SafetyCheckResult:
        """Check if cabinet requires anti-tip restraint.

        Delegates to StabilityService.

        Args:
            cabinet: Cabinet to check.

        Returns:
            SafetyCheckResult indicating anti-tip requirement status.
        """
        return self._stability.check_anti_tip_requirement(cabinet)

    def get_anti_tip_hardware(self, cabinet: "Cabinet") -> list[str]:
        """Get recommended anti-tip hardware for a cabinet.

        Delegates to StabilityService.

        Args:
            cabinet: Cabinet requiring anti-tip protection.

        Returns:
            List of hardware recommendations.
        """
        return self._stability.get_anti_tip_hardware(cabinet)

    def analyze_accessibility(self, cabinet: "Cabinet") -> AccessibilityReport:
        """Analyze ADA accessibility compliance.

        Delegates to AccessibilityService.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            AccessibilityReport with compliance details.
        """
        return self._accessibility.analyze_accessibility(cabinet)

    def check_clearances(
        self,
        cabinet: "Cabinet",
        obstacles: list["Obstacle"],
    ) -> list[SafetyCheckResult]:
        """Check clearances from electrical panels, heat sources, egress.

        Delegates to ClearanceService.

        Args:
            cabinet: Cabinet configuration.
            obstacles: List of obstacles to check clearances against.

        Returns:
            List of SafetyCheckResult for each clearance check.
        """
        return self._clearance.check_clearances(cabinet, obstacles)

    def check_material_compliance(self) -> SafetyCheckResult:
        """Check material certification compliance.

        Delegates to MaterialComplianceService.

        Returns:
            SafetyCheckResult for material compliance.
        """
        return self._material.check_material_compliance()

    def check_seismic_requirements(self) -> SafetyCheckResult:
        """Check seismic zone requirements.

        Delegates to SeismicService.

        Returns:
            SafetyCheckResult for seismic requirements.
        """
        return self._seismic.check_seismic_requirements()

    def get_seismic_hardware(self) -> list[str]:
        """Get list of recommended seismic hardware.

        Delegates to SeismicService.

        Returns:
            List of hardware recommendations for seismic zones.
        """
        return self._seismic.get_seismic_hardware()

    def generate_safety_labels(
        self,
        assessment: SafetyAssessment,
    ) -> list[SafetyLabel]:
        """Generate safety label content based on assessment.

        Delegates to ReportingService.

        Args:
            assessment: Completed SafetyAssessment.

        Returns:
            List of SafetyLabel objects.
        """
        return self._reporting.generate_safety_labels(assessment)

    def generate_safety_report(self, assessment: SafetyAssessment) -> str:
        """Generate a comprehensive safety report in markdown format.

        Delegates to ReportingService.

        Args:
            assessment: Completed SafetyAssessment.

        Returns:
            Markdown-formatted safety report string.
        """
        return self._reporting.generate_safety_report(assessment)

    def get_anti_tip_hardware_from_assessment(
        self,
        assessment: SafetyAssessment,
    ) -> list[str]:
        """Get anti-tip hardware recommendations from assessment context.

        Delegates to ReportingService.

        Args:
            assessment: SafetyAssessment containing anti-tip data.

        Returns:
            List of hardware recommendations.
        """
        return self._reporting.get_anti_tip_hardware_from_assessment(assessment)

    # =========================================================================
    # Private helper methods kept in facade for child safety
    # =========================================================================

    def _generate_child_safety_notes(self, cabinet: "Cabinet") -> list[str]:
        """Generate child safety recommendations.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of child safety recommendation strings.
        """
        notes: list[str] = []

        # Check for entrapment risk (enclosed spaces > 1.5 cu ft)
        for section in cabinet.sections:
            section_volume = (
                section.width
                * cabinet.depth
                * (section.height if hasattr(section, "height") else cabinet.height)
            )
            if section_volume >= CHILD_ENTRAPMENT_VOLUME_THRESHOLD:
                notes.append(
                    "CHILD SAFETY: Enclosed storage spaces may pose entrapment risk. "
                    "Consider ventilation holes or self-closing hinges."
                )
                break

        # Anti-tip warning for child safety
        if cabinet.height >= ANTI_TIP_HEIGHT_THRESHOLD:
            notes.append(
                "CHILD SAFETY: Furniture tip-over is a leading cause of child injury. "
                "Anchor all tall furniture to the wall."
            )

        # Drawer safety
        if any(hasattr(s, "drawers") and s.drawers for s in cabinet.sections):
            notes.append(
                "CHILD SAFETY: Install drawer stops or soft-close mechanisms "
                "to prevent finger pinching."
            )

        # Sharp edges
        notes.append(
            "CHILD SAFETY: Consider edge protectors on sharp corners "
            "in areas accessible to children."
        )

        return notes

    # =========================================================================
    # Private methods delegated to sub-services (kept for internal use)
    # =========================================================================

    def _check_structural_safety(self, cabinet: "Cabinet") -> list[SafetyCheckResult]:
        """Perform structural safety checks. Delegates to StructuralSafetyService."""
        return self._structural.check_structural_safety(cabinet)

    def _is_wall_mounted(self, cabinet: "Cabinet") -> bool:
        """Check if cabinet is wall-mounted. Delegates to StabilityService."""
        return self._stability.is_wall_mounted(cabinet)

    def _check_stability(self, cabinet: "Cabinet") -> list[SafetyCheckResult]:
        """Perform stability checks. Delegates to StabilityService."""
        return self._stability.check_stability(cabinet)

    def _check_accessibility(self, cabinet: "Cabinet") -> list[SafetyCheckResult]:
        """Perform accessibility checks. Delegates to AccessibilityService."""
        return self._accessibility.check_accessibility(cabinet)

    def _generate_material_notes(self) -> list[str]:
        """Generate material notes. Delegates to MaterialComplianceService."""
        return self._material.generate_material_notes()

    # =========================================================================
    # Accessibility helper methods delegated for backward compatibility
    # =========================================================================

    def _get_cabinet_floor_offset(self, cabinet: "Cabinet") -> float:
        """Get cabinet floor offset. Delegates to AccessibilityService."""
        return self._accessibility._get_cabinet_floor_offset(cabinet)

    def _calculate_shelf_height(
        self,
        cabinet: "Cabinet",
        section: object,
        shelf: object,
        shelf_idx: int,
        floor_offset: float,
    ) -> float:
        """Calculate shelf height from floor. Delegates to AccessibilityService."""
        return self._accessibility._calculate_shelf_height(
            cabinet, section, shelf, shelf_idx, floor_offset
        )

    def _get_shelf_storage_height(
        self,
        cabinet: "Cabinet",
        section: object,
        shelf_idx: int,
    ) -> float:
        """Get usable storage height above a shelf. Delegates to AccessibilityService."""
        return self._accessibility._get_shelf_storage_height(
            cabinet, section, shelf_idx
        )


__all__ = ["SafetyService"]
