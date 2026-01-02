"""Span checking service for shelf and panel spans.

This module provides SpanChecker service for validating
horizontal panel spans against material-specific limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.value_objects import PanelType

from .constants import get_max_span
from .models import SpanWarning

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet, Section, Shelf


class SpanChecker:
    """Service for checking horizontal panel spans.

    Analyzes shelves, top, and bottom panels against material-specific
    span limits. Returns warnings for any panels that exceed safe limits.
    """

    def check_spans(self, cabinet: "Cabinet") -> list[SpanWarning]:
        """Check all horizontal panels for span violations.

        Analyzes shelves, top, and bottom panels against material-specific
        span limits. Returns warnings for any panels that exceed safe limits.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of SpanWarning objects for panels exceeding limits.
        """
        warnings: list[SpanWarning] = []

        # Check each section's shelves
        for section_idx, section in enumerate(cabinet.sections):
            for shelf_idx, shelf in enumerate(section.shelves):
                span = self._calculate_shelf_span(shelf, section)
                max_span = get_max_span(
                    shelf.material.material_type, shelf.material.thickness
                )

                if span > max_span:
                    severity = "critical" if span > max_span * 1.5 else "warning"
                    warnings.append(
                        SpanWarning(
                            panel_label=f"Section {section_idx + 1} Shelf {shelf_idx + 1}",
                            span=span,
                            max_span=max_span,
                            material=shelf.material,
                            suggestion=self._get_span_suggestion(span, max_span),
                            severity=severity,
                        )
                    )

        # Check top panel span
        top_span = self._calculate_case_span(cabinet, PanelType.TOP)
        if top_span > 0:
            max_span = get_max_span(
                cabinet.material.material_type, cabinet.material.thickness
            )
            if top_span > max_span:
                warnings.append(
                    SpanWarning(
                        panel_label="Top Panel",
                        span=top_span,
                        max_span=max_span,
                        material=cabinet.material,
                        suggestion=self._get_span_suggestion(top_span, max_span),
                        severity="warning",
                    )
                )

        # Check bottom panel span
        bottom_span = self._calculate_case_span(cabinet, PanelType.BOTTOM)
        if bottom_span > 0:
            max_span = get_max_span(
                cabinet.material.material_type, cabinet.material.thickness
            )
            if bottom_span > max_span:
                warnings.append(
                    SpanWarning(
                        panel_label="Bottom Panel",
                        span=bottom_span,
                        max_span=max_span,
                        material=cabinet.material,
                        suggestion=self._get_span_suggestion(bottom_span, max_span),
                        severity="warning",
                    )
                )

        return warnings

    def _calculate_shelf_span(self, shelf: "Shelf", section: "Section") -> float:
        """Calculate unsupported span for a shelf.

        The unsupported span is the width of the section that the shelf
        spans, not accounting for any intermediate supports.

        Args:
            shelf: The shelf to analyze.
            section: The section containing the shelf.

        Returns:
            Unsupported span in inches.
        """
        # Basic calculation: section width is the unsupported span
        # In a more complex implementation, this could account for
        # intermediate dividers or supports
        return section.width

    def _calculate_case_span(self, cabinet: "Cabinet", panel_type: PanelType) -> float:
        """Calculate unsupported span for top/bottom case panels.

        For cabinets with multiple sections, the span between dividers
        may be less than the full cabinet width. This method calculates
        the maximum unsupported span.

        Args:
            cabinet: The cabinet to analyze.
            panel_type: Either TOP or BOTTOM panel type.

        Returns:
            Maximum unsupported span in inches.
        """
        if not cabinet.sections:
            return cabinet.interior_width

        # Find the widest section (maximum span between supports)
        max_section_width = max(section.width for section in cabinet.sections)
        return max_section_width

    def _get_span_suggestion(self, span: float, max_span: float) -> str:
        """Generate suggestion text based on span excess.

        Args:
            span: Actual span in inches.
            max_span: Maximum recommended span in inches.

        Returns:
            Suggestion text for mitigation.
        """
        excess_percent = ((span - max_span) / max_span) * 100

        if excess_percent > 50:
            return (
                "Add center support or divider. Consider thicker material "
                '(1" or greater) for this span.'
            )
        elif excess_percent > 25:
            return "Add center support or divider to reduce span."
        else:
            return (
                "Consider adding center support, using thicker material, "
                "or reducing load expectations."
            )
