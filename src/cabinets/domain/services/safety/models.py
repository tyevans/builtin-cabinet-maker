"""Safety data models and result types.

This module contains all dataclasses used for safety analysis results,
including check results, capacity estimates, accessibility reports,
safety labels, and the overall safety assessment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cabinets.domain.value_objects import (
    ADAStandard,
    SafetyCategory,
    SafetyCheckStatus,
)

from .constants import WEIGHT_CAPACITY_DISCLAIMER, KCMA_SHELF_LOAD_PSF


@dataclass(frozen=True)
class SafetyCheckResult:
    """Result of a single safety check.

    Represents the outcome of evaluating one safety criterion against
    the cabinet configuration. Includes status, message, and remediation
    guidance when applicable.

    Attributes:
        check_id: Unique identifier for this check type (e.g., "anti_tip_required").
        category: Safety category this check belongs to.
        status: Outcome status (pass, warning, error, not_applicable).
        message: Human-readable description of the check result.
        remediation: Suggested action to address warnings/errors (optional).
        standard_reference: Citation to relevant standard (e.g., "NEC 110.26").
        details: Additional structured data about the check (optional).
    """

    check_id: str
    category: SafetyCategory
    status: SafetyCheckStatus
    message: str
    remediation: str | None = None
    standard_reference: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("check_id must not be empty")
        if not self.message:
            raise ValueError("message must not be empty")

    @property
    def is_pass(self) -> bool:
        """Check if this result indicates a passing status."""
        return self.status == SafetyCheckStatus.PASS

    @property
    def is_warning(self) -> bool:
        """Check if this result indicates a warning."""
        return self.status == SafetyCheckStatus.WARNING

    @property
    def is_error(self) -> bool:
        """Check if this result indicates an error."""
        return self.status == SafetyCheckStatus.ERROR

    @property
    def formatted_message(self) -> str:
        """Human-readable formatted message with status prefix."""
        prefix = {
            SafetyCheckStatus.PASS: "[PASS]",
            SafetyCheckStatus.WARNING: "[WARN]",
            SafetyCheckStatus.ERROR: "[FAIL]",
            SafetyCheckStatus.NOT_APPLICABLE: "[N/A]",
        }
        return f"{prefix[self.status]} {self.message}"


@dataclass(frozen=True)
class WeightCapacityEstimate:
    """Calculated weight capacity for a shelf or horizontal surface.

    Advisory estimate based on beam deflection calculations. Always
    includes a disclaimer that this is not an engineered calculation.

    Attributes:
        panel_id: Identifier for the panel (e.g., "shelf_1", "section_0_shelf_2").
        safe_load_lbs: Estimated safe load capacity in pounds.
        max_deflection_inches: Maximum allowable deflection (L/200, L/240, etc.).
        deflection_at_rated_load: Expected deflection at safe_load_lbs.
        safety_factor: Safety factor applied (typically 4.0).
        material: Material type description.
        span_inches: Unsupported span of the shelf in inches.
        disclaimer: Legal disclaimer about advisory nature.
    """

    panel_id: str
    safe_load_lbs: float
    max_deflection_inches: float
    deflection_at_rated_load: float
    safety_factor: float
    material: str
    span_inches: float
    disclaimer: str = WEIGHT_CAPACITY_DISCLAIMER

    def __post_init__(self) -> None:
        if self.safe_load_lbs < 0:
            raise ValueError("safe_load_lbs must be non-negative")
        if self.max_deflection_inches <= 0:
            raise ValueError("max_deflection_inches must be positive")
        if self.safety_factor <= 0:
            raise ValueError("safety_factor must be positive")
        if self.span_inches <= 0:
            raise ValueError("span_inches must be positive")

    @property
    def meets_kcma_standard(self) -> bool:
        """Check if capacity meets KCMA 15 lbs/sq ft standard.

        Assumes panel_id contains information about shelf dimensions,
        but this property provides a basic threshold check.
        """
        # KCMA requires 15 lbs/sq ft - this is a simplified check
        return self.safe_load_lbs >= KCMA_SHELF_LOAD_PSF

    @property
    def formatted_message(self) -> str:
        """Human-readable capacity statement."""
        return (
            f"{self.panel_id}: {self.safe_load_lbs:.0f} lbs capacity "
            f'({self.material}, {self.span_inches:.1f}" span, '
            f"{self.safety_factor}:1 safety factor)"
        )


@dataclass(frozen=True)
class AccessibilityReport:
    """ADA accessibility compliance report.

    Summarizes accessibility analysis for a cabinet configuration,
    including reach range validation and accessible storage percentage.

    Attributes:
        total_storage_volume: Total storage volume in cubic inches.
        accessible_storage_volume: Volume within ADA reach range.
        accessible_percentage: Percentage of storage that is accessible.
        is_compliant: True if accessible_percentage >= 50%.
        non_compliant_areas: Descriptions of areas outside reach range.
        reach_violations: Specific reach range violations.
        hardware_notes: Recommendations for accessible hardware.
        standard: ADA standard version used for analysis.
    """

    total_storage_volume: float
    accessible_storage_volume: float
    accessible_percentage: float
    is_compliant: bool
    non_compliant_areas: tuple[str, ...]
    reach_violations: tuple[str, ...]
    hardware_notes: tuple[str, ...]
    standard: ADAStandard = ADAStandard.ADA_2010

    def __post_init__(self) -> None:
        if self.total_storage_volume < 0:
            raise ValueError("total_storage_volume must be non-negative")
        if self.accessible_storage_volume < 0:
            raise ValueError("accessible_storage_volume must be non-negative")
        if not 0 <= self.accessible_percentage <= 100:
            raise ValueError("accessible_percentage must be between 0 and 100")

    @property
    def formatted_summary(self) -> str:
        """Human-readable accessibility summary."""
        status = "COMPLIANT" if self.is_compliant else "NON-COMPLIANT"
        return (
            f"Accessibility: {self.accessible_percentage:.1f}% accessible "
            f"({status}, requires 50% minimum)"
        )


@dataclass(frozen=True)
class SafetyLabel:
    """Generated safety label content.

    Represents the text and formatting for a safety label that can
    be exported to SVG/PDF for printing and attachment to cabinets.

    Attributes:
        label_type: Type of label (weight_capacity, anti_tip, installation, material).
        title: Label title/header text.
        body_text: Main label content.
        warning_icon: Whether to include a warning icon.
        dimensions: Label size in inches (width, height).
    """

    label_type: str
    title: str
    body_text: str
    warning_icon: bool = False
    dimensions: tuple[float, float] = (4.0, 3.0)  # Default 4"x3"

    def __post_init__(self) -> None:
        valid_types = {"weight_capacity", "anti_tip", "installation", "material"}
        if self.label_type not in valid_types:
            raise ValueError(f"label_type must be one of {valid_types}")
        if not self.title:
            raise ValueError("title must not be empty")
        if not self.body_text:
            raise ValueError("body_text must not be empty")
        if self.dimensions[0] <= 0 or self.dimensions[1] <= 0:
            raise ValueError("dimensions must be positive")

    @property
    def width_inches(self) -> float:
        """Label width in inches."""
        return self.dimensions[0]

    @property
    def height_inches(self) -> float:
        """Label height in inches."""
        return self.dimensions[1]


@dataclass
class SafetyAssessment:
    """Complete safety assessment for a cabinet configuration.

    Aggregates all safety check results, capacity estimates, accessibility
    analysis, and generated labels into a comprehensive assessment.

    Attributes:
        check_results: All individual safety check results.
        weight_capacities: Weight capacity estimates for all shelves.
        accessibility_report: ADA accessibility report (if enabled).
        safety_labels: Generated safety labels.
        anti_tip_required: Whether anti-tip restraint is required.
        seismic_hardware: List of seismic hardware recommendations.
        child_safety_notes: Child safety recommendations (if enabled).
        material_notes: Material safety notes.
        warnings_count: Total number of warning-level results.
        errors_count: Total number of error-level results.
    """

    check_results: list[SafetyCheckResult]
    weight_capacities: list[WeightCapacityEstimate]
    accessibility_report: AccessibilityReport | None
    safety_labels: list[SafetyLabel]
    anti_tip_required: bool
    seismic_hardware: list[str]
    child_safety_notes: list[str] = field(default_factory=list)
    material_notes: list[str] = field(default_factory=list)
    warnings_count: int = 0
    errors_count: int = 0

    def __post_init__(self) -> None:
        # Calculate counts from check_results if not provided
        if self.warnings_count == 0 and self.errors_count == 0:
            self.warnings_count = sum(
                1 for r in self.check_results if r.status == SafetyCheckStatus.WARNING
            )
            self.errors_count = sum(
                1 for r in self.check_results if r.status == SafetyCheckStatus.ERROR
            )

    @property
    def has_errors(self) -> bool:
        """Check if assessment contains any error-level results."""
        return self.errors_count > 0

    @property
    def has_warnings(self) -> bool:
        """Check if assessment contains any warning-level results."""
        return self.warnings_count > 0

    @property
    def is_safe(self) -> bool:
        """Check if assessment passed with no errors (warnings allowed)."""
        return not self.has_errors

    @property
    def summary(self) -> str:
        """Human-readable summary of assessment."""
        if self.has_errors:
            return f"FAILED: {self.errors_count} error(s), {self.warnings_count} warning(s)"
        elif self.has_warnings:
            return f"PASSED with {self.warnings_count} warning(s)"
        else:
            return "PASSED: All safety checks passed"

    def get_results_by_category(
        self, category: SafetyCategory
    ) -> list[SafetyCheckResult]:
        """Get all check results for a specific category."""
        return [r for r in self.check_results if r.category == category]

    def get_errors(self) -> list[SafetyCheckResult]:
        """Get all error-level check results."""
        return [r for r in self.check_results if r.status == SafetyCheckStatus.ERROR]

    def get_warnings(self) -> list[SafetyCheckResult]:
        """Get all warning-level check results."""
        return [r for r in self.check_results if r.status == SafetyCheckStatus.WARNING]


__all__ = [
    "SafetyCheckResult",
    "WeightCapacityEstimate",
    "AccessibilityReport",
    "SafetyLabel",
    "SafetyAssessment",
]
