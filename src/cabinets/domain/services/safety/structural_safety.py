"""Structural safety analysis service.

This module provides weight capacity calculations and structural
safety checks for cabinet configurations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.value_objects import (
    PanelType,
    SafetyCategory,
    SafetyCheckStatus,
)
from cabinets.domain.services.woodworking import (
    MATERIAL_MODULUS,
    get_max_span,
)

from .config import SafetyConfig
from .constants import KCMA_SHELF_LOAD_PSF, WEIGHT_CAPACITY_DISCLAIMER
from .models import SafetyCheckResult, WeightCapacityEstimate

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet, Panel


class StructuralSafetyService:
    """Service for structural safety analysis.

    Provides weight capacity calculations and span limit checking
    for cabinet shelves and panels.

    Example:
        config = SafetyConfig(safety_factor=4.0)
        service = StructuralSafetyService(config)
        capacities = service.get_shelf_capacities(cabinet)
    """

    def __init__(self, config: SafetyConfig) -> None:
        """Initialize StructuralSafetyService.

        Args:
            config: Safety analysis configuration.
        """
        self.config = config

    def calculate_weight_capacity(
        self, panel: "Panel"
    ) -> WeightCapacityEstimate | None:
        """Calculate weight capacity for a shelf panel.

        Uses beam deflection formula to estimate safe load capacity
        with the configured safety factor. Delegates core calculation
        to WoodworkingIntelligence.

        Args:
            panel: Panel to calculate capacity for.

        Returns:
            WeightCapacityEstimate or None if panel is not a shelf.
        """
        # Only calculate for shelf-type panels
        if panel.panel_type != PanelType.SHELF:
            return None

        # Get material modulus
        material_type = panel.material.material_type
        E = MATERIAL_MODULUS.get(material_type, 1_200_000)  # Default to plywood

        # Calculate moment of inertia for rectangular cross-section
        # I = (b * h^3) / 12 where b = depth, h = thickness
        # Note: panel.height is depth in our model for shelves
        b = panel.height  # depth (front to back)
        h = panel.material.thickness
        moment_of_inertia = (b * h**3) / 12

        span = panel.width  # unsupported span

        # Maximum allowable deflection based on configured ratio
        # L/200, L/240, or L/360
        max_deflection = span / self.config.deflection_limit_ratio

        # Solve for load from deflection formula:
        # delta = (5 * W * L^4) / (384 * E * I)
        # W = (delta * 384 * E * I) / (5 * L^4)
        if span > 0:
            max_load = (max_deflection * 384 * E * moment_of_inertia) / (5 * span**4)
        else:
            max_load = 0

        # Apply safety factor
        safe_load = max_load / self.config.safety_factor

        # Calculate deflection at rated load
        if E * moment_of_inertia > 0 and span > 0:
            deflection_at_load = (5 * safe_load * span**4) / (
                384 * E * moment_of_inertia
            )
        else:
            deflection_at_load = 0

        # Create panel identifier
        panel_id = (
            f"shelf_{panel.position.y:.0f}"
            if hasattr(panel, "position") and panel.position
            else "shelf"
        )

        return WeightCapacityEstimate(
            panel_id=panel_id,
            safe_load_lbs=round(safe_load, 1),
            max_deflection_inches=round(max_deflection, 3),
            deflection_at_rated_load=round(deflection_at_load, 4),
            safety_factor=self.config.safety_factor,
            material=material_type.value,
            span_inches=span,
            disclaimer=WEIGHT_CAPACITY_DISCLAIMER,
        )

    def get_shelf_capacities(self, cabinet: "Cabinet") -> list[WeightCapacityEstimate]:
        """Get weight capacity estimates for all shelves in a cabinet.

        Iterates through all sections and shelves, calculating weight
        capacity for each horizontal surface.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of WeightCapacityEstimate for all shelf panels.
        """
        capacities: list[WeightCapacityEstimate] = []

        for section_idx, section in enumerate(cabinet.sections):
            for shelf_idx, shelf in enumerate(section.shelves):
                # Create a unique panel identifier
                panel_id = f"section_{section_idx}_shelf_{shelf_idx}"

                # Get material from shelf
                material = shelf.material

                # Calculate capacity using shelf dimensions
                # Span is the section width minus side panel thickness on each side
                span = section.width - (2 * cabinet.material.thickness)
                depth = shelf.depth

                if span <= 0 or depth <= 0:
                    continue

                # Get material modulus
                E = MATERIAL_MODULUS.get(material.material_type, 1_200_000)
                h = material.thickness
                moment_of_inertia = (depth * h**3) / 12

                max_deflection = span / self.config.deflection_limit_ratio

                if span > 0:
                    max_load = (max_deflection * 384 * E * moment_of_inertia) / (
                        5 * span**4
                    )
                else:
                    max_load = 0

                safe_load = max_load / self.config.safety_factor

                if E * moment_of_inertia > 0 and span > 0:
                    deflection_at_load = (5 * safe_load * span**4) / (
                        384 * E * moment_of_inertia
                    )
                else:
                    deflection_at_load = 0

                capacities.append(
                    WeightCapacityEstimate(
                        panel_id=panel_id,
                        safe_load_lbs=round(safe_load, 1),
                        max_deflection_inches=round(max_deflection, 3),
                        deflection_at_rated_load=round(deflection_at_load, 4),
                        safety_factor=self.config.safety_factor,
                        material=material.material_type.value,
                        span_inches=span,
                        disclaimer=WEIGHT_CAPACITY_DISCLAIMER,
                    )
                )

        return capacities

    def check_structural_safety(
        self,
        cabinet: "Cabinet",
    ) -> list[SafetyCheckResult]:
        """Perform structural safety checks including weight capacity.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of SafetyCheckResult for structural checks.
        """
        results: list[SafetyCheckResult] = []
        capacities = self.get_shelf_capacities(cabinet)

        if not capacities:
            results.append(
                SafetyCheckResult(
                    check_id="weight_capacity_analysis",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.NOT_APPLICABLE,
                    message="No shelves found for weight capacity analysis",
                )
            )
            return results

        # Check each shelf against KCMA standard
        for capacity in capacities:
            # Calculate shelf area for KCMA comparison
            # KCMA requires 15 lbs/sq ft
            # Estimate depth from span (typical shelf is 12" deep)
            # Use a conservative estimate of 12" depth
            estimated_depth = 12.0
            shelf_area_sqft = (capacity.span_inches * estimated_depth) / 144.0

            kcma_required = shelf_area_sqft * KCMA_SHELF_LOAD_PSF

            if capacity.safe_load_lbs >= kcma_required:
                results.append(
                    SafetyCheckResult(
                        check_id=f"weight_capacity_{capacity.panel_id}",
                        category=SafetyCategory.STRUCTURAL,
                        status=SafetyCheckStatus.PASS,
                        message=(
                            f"{capacity.panel_id}: {capacity.safe_load_lbs:.0f} lbs capacity "
                            f"(meets KCMA standard)"
                        ),
                        standard_reference="ANSI/KCMA A161.1",
                        details={
                            "safe_load_lbs": capacity.safe_load_lbs,
                            "span_inches": capacity.span_inches,
                            "material": capacity.material,
                            "safety_factor": capacity.safety_factor,
                        },
                    )
                )
            else:
                results.append(
                    SafetyCheckResult(
                        check_id=f"weight_capacity_{capacity.panel_id}",
                        category=SafetyCategory.STRUCTURAL,
                        status=SafetyCheckStatus.WARNING,
                        message=(
                            f"{capacity.panel_id}: {capacity.safe_load_lbs:.0f} lbs capacity "
                            f"(below KCMA {KCMA_SHELF_LOAD_PSF} lbs/sq ft standard)"
                        ),
                        remediation=(
                            "Consider thicker material, shorter span, or add center support"
                        ),
                        standard_reference="ANSI/KCMA A161.1",
                        details={
                            "safe_load_lbs": capacity.safe_load_lbs,
                            "kcma_required": kcma_required,
                            "span_inches": capacity.span_inches,
                            "material": capacity.material,
                        },
                    )
                )

        # Check for span warnings
        for section_idx, section in enumerate(cabinet.sections):
            span = section.width - (2 * cabinet.material.thickness)
            max_span = get_max_span(
                cabinet.material.material_type, cabinet.material.thickness
            )

            if span > max_span:
                results.append(
                    SafetyCheckResult(
                        check_id=f"span_warning_section_{section_idx}",
                        category=SafetyCategory.STRUCTURAL,
                        status=SafetyCheckStatus.WARNING,
                        message=(
                            f"Section {section_idx}: "
                            f'{span:.1f}" span exceeds {max_span:.1f}" recommended maximum '
                            f"for {cabinet.material.material_type.value}"
                        ),
                        remediation="Add center divider or use thicker/stronger material",
                        details={
                            "actual_span": span,
                            "max_span": max_span,
                            "excess_percent": ((span - max_span) / max_span) * 100,
                        },
                    )
                )
            elif span > max_span * 0.9:  # Within 10% of limit
                results.append(
                    SafetyCheckResult(
                        check_id=f"span_warning_section_{section_idx}",
                        category=SafetyCategory.STRUCTURAL,
                        status=SafetyCheckStatus.PASS,
                        message=(
                            f"Section {section_idx}: "
                            f'{span:.1f}" span approaches {max_span:.1f}" limit'
                        ),
                        details={
                            "actual_span": span,
                            "max_span": max_span,
                            "margin_percent": ((max_span - span) / max_span) * 100,
                        },
                    )
                )

        return results


__all__ = ["StructuralSafetyService"]
