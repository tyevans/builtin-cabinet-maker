"""Safety reporting and label generation service.

This module provides safety label generation and comprehensive
safety report formatting for cabinet configurations.
"""

from __future__ import annotations

from .config import SafetyConfig
from .constants import (
    ADA_DISCLAIMER,
    MATERIAL_DISCLAIMER,
    SAFETY_GENERAL_DISCLAIMER,
    WEIGHT_CAPACITY_DISCLAIMER,
)
from .models import SafetyAssessment, SafetyLabel


class ReportingService:
    """Service for safety reporting and label generation.

    Provides safety label content generation and comprehensive
    markdown report formatting for safety assessments.

    Example:
        config = SafetyConfig(generate_labels=True)
        service = ReportingService(config)
        labels = service.generate_safety_labels(assessment)
        report = service.generate_safety_report(assessment)
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize ReportingService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def generate_safety_labels(
        self,
        assessment: SafetyAssessment,
    ) -> list[SafetyLabel]:
        """Generate safety label content based on assessment.

        Creates appropriate safety labels for the cabinet including
        weight capacity, anti-tip warnings, and installation guidance.

        Args:
            assessment: Completed SafetyAssessment.

        Returns:
            List of SafetyLabel objects.
        """
        labels: list[SafetyLabel] = []

        # Weight capacity label
        if assessment.weight_capacities:
            avg_capacity = sum(
                wc.safe_load_lbs for wc in assessment.weight_capacities
            ) / len(assessment.weight_capacities)
            labels.append(
                SafetyLabel(
                    label_type="weight_capacity",
                    title="MAXIMUM LOAD",
                    body_text=(
                        f"Do not exceed {avg_capacity:.0f} lbs per shelf.\n"
                        f"{WEIGHT_CAPACITY_DISCLAIMER}"
                    ),
                    warning_icon=True,
                    dimensions=(4.0, 2.0),
                )
            )

        # Anti-tip label
        if assessment.anti_tip_required:
            labels.append(
                SafetyLabel(
                    label_type="anti_tip",
                    title="WARNING: TIP-OVER HAZARD",
                    body_text=(
                        "To reduce the risk of tip-over, this furniture "
                        "must be anchored to the wall.\n\n"
                        "Serious or fatal crushing injuries can occur from "
                        "furniture tip-over. See installation instructions."
                    ),
                    warning_icon=True,
                    dimensions=(4.0, 3.0),
                )
            )

        # Installation label
        labels.append(
            SafetyLabel(
                label_type="installation",
                title="INSTALLATION SAFETY",
                body_text=(
                    "- Secure to wall studs or use appropriate anchors\n"
                    "- Follow all mounting instructions\n"
                    "- Do not exceed rated load capacity\n"
                    "- Inspect mounting periodically"
                ),
                warning_icon=False,
                dimensions=(4.0, 3.0),
            )
        )

        return labels

    def generate_safety_report(self, assessment: SafetyAssessment) -> str:
        """Generate a comprehensive safety report in markdown format.

        Args:
            assessment: Completed SafetyAssessment.

        Returns:
            Markdown-formatted safety report string.
        """
        lines: list[str] = []

        # Header
        lines.append("# Cabinet Safety Assessment Report")
        lines.append("")
        lines.append(f"**Overall Status:** {assessment.summary}")
        lines.append("")

        # Disclaimer
        lines.append("---")
        lines.append("")
        lines.append(f"*{SAFETY_GENERAL_DISCLAIMER}*")
        lines.append("")

        # Summary statistics
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total checks performed: {len(assessment.check_results)}")
        lines.append(
            f"- Passed: {sum(1 for r in assessment.check_results if r.is_pass)}"
        )
        lines.append(f"- Warnings: {assessment.warnings_count}")
        lines.append(f"- Errors: {assessment.errors_count}")
        lines.append("")

        # Errors section (if any)
        errors = assessment.get_errors()
        if errors:
            lines.append("## Errors (Action Required)")
            lines.append("")
            for error in errors:
                lines.append(f"### {error.check_id}")
                lines.append("- **Status:** FAIL")
                lines.append(f"- **Category:** {error.category.value}")
                lines.append(f"- **Message:** {error.message}")
                if error.remediation:
                    lines.append(f"- **Remediation:** {error.remediation}")
                if error.standard_reference:
                    lines.append(f"- **Reference:** {error.standard_reference}")
                lines.append("")

        # Warnings section (if any)
        warnings = assessment.get_warnings()
        if warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in warnings:
                lines.append(f"### {warning.check_id}")
                lines.append("- **Status:** WARNING")
                lines.append(f"- **Category:** {warning.category.value}")
                lines.append(f"- **Message:** {warning.message}")
                if warning.remediation:
                    lines.append(f"- **Remediation:** {warning.remediation}")
                if warning.standard_reference:
                    lines.append(f"- **Reference:** {warning.standard_reference}")
                lines.append("")

        # Weight capacity section
        if assessment.weight_capacities:
            lines.append("## Weight Capacity Estimates")
            lines.append("")
            lines.append(f"*{WEIGHT_CAPACITY_DISCLAIMER}*")
            lines.append("")
            lines.append(
                "| Shelf | Capacity (lbs) | Span (in) | Material | Safety Factor |"
            )
            lines.append(
                "|-------|----------------|-----------|----------|---------------|"
            )
            for wc in assessment.weight_capacities:
                lines.append(
                    f"| {wc.panel_id} | {wc.safe_load_lbs:.0f} | "
                    f"{wc.span_inches:.1f} | {wc.material} | {wc.safety_factor}:1 |"
                )
            lines.append("")

        # Accessibility section
        if assessment.accessibility_report and self.config.accessibility_enabled:
            report = assessment.accessibility_report
            lines.append("## Accessibility Analysis")
            lines.append("")
            lines.append(f"*{ADA_DISCLAIMER}*")
            lines.append("")
            lines.append(f"- **Standard:** {report.standard.value}")
            lines.append(
                f"- **Compliance:** {'COMPLIANT' if report.is_compliant else 'NON-COMPLIANT'}"
            )
            lines.append(
                f"- **Accessible Storage:** {report.accessible_percentage:.1f}%"
            )
            lines.append(f"  - Total Volume: {report.total_storage_volume:.0f} cu in")
            lines.append(
                f"  - Accessible Volume: {report.accessible_storage_volume:.0f} cu in"
            )
            lines.append("")

            if report.reach_violations:
                lines.append("### Reach Violations")
                for violation in report.reach_violations:
                    lines.append(f"- {violation}")
                lines.append("")

            if report.hardware_notes:
                lines.append("### Hardware Recommendations")
                for note in report.hardware_notes:
                    lines.append(f"- {note}")
                lines.append("")

        # Anti-tip section
        if assessment.anti_tip_required:
            lines.append("## Anti-Tip Requirements")
            lines.append("")
            lines.append("**WARNING:** This cabinet requires anti-tip restraint.")
            lines.append("")
            anti_tip_hardware = self.get_anti_tip_hardware_from_assessment(assessment)
            if anti_tip_hardware:
                lines.append("### Recommended Hardware")
                for hw in anti_tip_hardware:
                    lines.append(f"- {hw}")
                lines.append("")

        # Seismic section
        if assessment.seismic_hardware:
            lines.append("## Seismic Requirements")
            lines.append("")
            lines.append("Enhanced anchoring required for seismic zone.")
            lines.append("")
            lines.append("### Recommended Hardware")
            for hw in assessment.seismic_hardware:
                lines.append(f"- {hw}")
            lines.append("")

        # Child safety section
        if assessment.child_safety_notes:
            lines.append("## Child Safety Notes")
            lines.append("")
            for note in assessment.child_safety_notes:
                lines.append(f"- {note}")
            lines.append("")

        # Material notes section
        if assessment.material_notes:
            lines.append("## Material Safety Notes")
            lines.append("")
            lines.append(f"*{MATERIAL_DISCLAIMER}*")
            lines.append("")
            for note in assessment.material_notes:
                lines.append(f"- {note}")
            lines.append("")

        # All passing checks (collapsed)
        passing = [r for r in assessment.check_results if r.is_pass]
        if passing:
            lines.append("## Passing Checks")
            lines.append("")
            for result in passing:
                lines.append(f"- [PASS] {result.message}")
            lines.append("")

        return "\n".join(lines)

    def get_anti_tip_hardware_from_assessment(
        self,
        assessment: SafetyAssessment,
    ) -> list[str]:
        """Get anti-tip hardware recommendations from assessment context.

        This is a helper for report generation that doesn't require
        the cabinet object.

        Args:
            assessment: SafetyAssessment containing anti-tip data.

        Returns:
            List of hardware recommendations.
        """
        if not assessment.anti_tip_required:
            return []

        # Extract height from check results if available
        height = 84.0  # Default assumption for tall cabinet
        for result in assessment.check_results:
            if result.check_id == "anti_tip_requirement" and "height" in result.details:
                height = result.details["height"]
                break

        hardware: list[str] = []
        hardware.append("Anti-tip furniture strap kit (qty: 1)")
        hardware.append("Mounting position: 4 inches from top")

        if height >= 48:
            hardware.append(
                "Anti-tip bracket with lag screw (qty: 2) - for added security"
            )

        if height >= 72:
            hardware.append(
                "Consider L-bracket wall attachment at top corners (qty: 2)"
            )

        hardware.append(
            '#10 x 3" wood screw for stud mounting (qty: 2) - OR - '
            '1/4" toggle bolt for drywall (qty: 2)'
        )

        return hardware


__all__ = ["ReportingService"]
