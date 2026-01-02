"""Weight capacity calculation service.

This module provides CapacityCalculator for estimating weight
capacity of horizontal panels using beam deflection formulas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.value_objects import MaterialSpec, MaterialType

from .constants import MATERIAL_MODULUS, MAX_DEFLECTION_RATIO, SAFETY_FACTOR
from .models import WeightCapacity

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet


class CapacityCalculator:
    """Service for calculating weight capacity of horizontal panels.

    Uses simplified beam deflection formula to estimate the load capacity
    of shelves and horizontal panels. This is an advisory estimate only
    and should not be used for structural engineering purposes.
    """

    def estimate_capacity(
        self,
        thickness: float,
        depth: float,
        span: float,
        material_type: MaterialType,
        load_type: str = "distributed",
        panel_label: str = "Shelf",
    ) -> WeightCapacity:
        """Estimate weight capacity for a horizontal panel.

        Uses simplified beam deflection formula to estimate the load capacity
        of a shelf or horizontal panel. This is an advisory estimate only and
        should not be used for structural engineering purposes.

        The formula used is based on the deflection limit approach:
        For distributed load: P = (384 * E * I * delta_max) / (5 * L^4)
        Where delta_max = L / 300 (standard deflection limit)

        Args:
            thickness: Panel thickness in inches.
            depth: Panel depth (front-to-back) in inches.
            span: Unsupported span in inches.
            material_type: Type of material.
            load_type: "distributed" or "point" load type.
            panel_label: Label for the panel in output.

        Returns:
            WeightCapacity with estimated capacity and disclaimer.
        """
        base_capacity = self._calculate_base_capacity(
            thickness=thickness,
            depth=depth,
            span=span,
            material_type=material_type,
        )

        # Reduce capacity for point loads (more concentrated stress)
        if load_type == "point":
            base_capacity *= 0.5  # 50% reduction for point loads

        # Apply safety factor (divide by safety factor for safe load rating)
        final_capacity = base_capacity / SAFETY_FACTOR

        # Round to nearest 5 lbs for readability
        final_capacity = round(final_capacity / 5) * 5

        # Minimum capacity of 5 lbs
        final_capacity = max(5.0, final_capacity)

        return WeightCapacity(
            panel_label=panel_label,
            capacity_lbs=final_capacity,
            load_type=load_type,
            span=span,
            material=MaterialSpec(thickness=thickness, material_type=material_type),
            disclaimer="Advisory only - not engineered",
        )

    def _calculate_base_capacity(
        self,
        thickness: float,
        depth: float,
        span: float,
        material_type: MaterialType,
    ) -> float:
        """Calculate base load capacity using beam deflection formula.

        Uses the formula for maximum load based on deflection limit:
        For a uniformly distributed load on a simply supported beam:
        w = (384 * E * I * delta) / (5 * L^4)

        Where:
        - E = modulus of elasticity (psi)
        - I = moment of inertia = (b * h^3) / 12
        - delta = maximum deflection = L / 300
        - L = span length
        - w = load per unit length
        - Total load P = w * L

        Args:
            thickness: Panel thickness in inches.
            depth: Panel depth (front-to-back) in inches.
            span: Unsupported span in inches.
            material_type: Type of material.

        Returns:
            Base capacity in pounds (before safety factor).
        """
        if span <= 0:
            return 0.0

        # Get modulus of elasticity
        E = MATERIAL_MODULUS.get(material_type, 1_000_000)

        # Moment of inertia for rectangular section
        # I = (b * h^3) / 12, where b = depth, h = thickness
        moment_of_inertia = (depth * (thickness**3)) / 12

        # Maximum allowable deflection (L/300 standard)
        delta_max = span / MAX_DEFLECTION_RATIO

        # Convert span to same units (already in inches)
        L = span

        # Calculate maximum distributed load (lbs/inch)
        # w = (384 * E * I * delta) / (5 * L^4)
        w = (384 * E * moment_of_inertia * delta_max) / (5 * (L**4))

        # Total capacity is w * L (load per inch * span)
        total_load = w * L

        return total_load

    def get_shelf_capacities(self, cabinet: "Cabinet") -> list[WeightCapacity]:
        """Get weight capacity estimates for all shelves in a cabinet.

        Calculates capacity for each shelf based on its material,
        thickness, depth, and span.

        Args:
            cabinet: Cabinet to analyze.

        Returns:
            List of WeightCapacity objects, one per shelf.
        """
        capacities: list[WeightCapacity] = []

        for section_idx, section in enumerate(cabinet.sections):
            for shelf_idx, shelf in enumerate(section.shelves):
                # Calculate span (section width is unsupported span)
                span = section.width

                capacity = self.estimate_capacity(
                    thickness=shelf.material.thickness,
                    depth=shelf.depth,
                    span=span,
                    material_type=shelf.material.material_type,
                    load_type="distributed",
                    panel_label=f"Section {section_idx + 1} Shelf {shelf_idx + 1}",
                )
                capacities.append(capacity)

        return capacities

    def format_capacity_report(self, capacities: list[WeightCapacity]) -> str:
        """Format weight capacity estimates as a report.

        Args:
            capacities: List of WeightCapacity objects.

        Returns:
            Formatted report string.
        """
        lines = [
            "WEIGHT CAPACITY ESTIMATES",
            "=" * 60,
            "",
            "DISCLAIMER: These are advisory estimates only.",
            "Do not use for structural engineering or load-bearing applications.",
            "",
            "-" * 60,
        ]

        for cap in capacities:
            lines.append(
                f"{cap.panel_label}: ~{cap.capacity_lbs:.0f} lbs ({cap.load_type})"
            )
            lines.append(
                f'  Material: {cap.material.material_type.value} at {cap.material.thickness}"'
            )
            lines.append(f'  Span: {cap.span:.1f}"')
            lines.append("")

        lines.append("-" * 60)
        lines.append("Note: Capacities assume evenly distributed loads.")
        lines.append("Point loads reduce capacity by approximately 50%.")

        return "\n".join(lines)
