"""Material estimation service."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..value_objects import CutPiece, MaterialSpec

__all__ = ["MaterialEstimate", "MaterialEstimator"]


@dataclass
class MaterialEstimate:
    """Estimate of materials needed for a project."""

    total_area_sqin: float
    total_area_sqft: float
    sheet_count_4x8: int
    sheet_count_5x5: int
    waste_percentage: float

    @property
    def description(self) -> str:
        """Human-readable description of material needs."""
        return (
            f"{self.total_area_sqft:.1f} sq ft total "
            f"({self.sheet_count_4x8} sheets of 4x8, "
            f"assuming {self.waste_percentage:.0%} waste)"
        )


class MaterialEstimator:
    """Estimates material requirements for cabinet construction."""

    SHEET_4X8_SQIN = 48 * 96  # 4608 sq in
    SHEET_5X5_SQIN = 60 * 60  # 3600 sq in

    def __init__(self, waste_factor: float = 0.15) -> None:
        """Initialize with waste factor (default 15%)."""
        self.waste_factor = waste_factor

    def estimate(
        self, cut_list: list[CutPiece]
    ) -> dict[MaterialSpec, MaterialEstimate]:
        """Estimate materials needed for a cut list, grouped by material type."""
        # Group pieces by material
        material_areas: dict[MaterialSpec, float] = {}
        for piece in cut_list:
            if piece.material not in material_areas:
                material_areas[piece.material] = 0
            material_areas[piece.material] += piece.area

        # Calculate estimates per material
        estimates: dict[MaterialSpec, MaterialEstimate] = {}
        for material, total_area in material_areas.items():
            area_with_waste = total_area * (1 + self.waste_factor)
            estimates[material] = MaterialEstimate(
                total_area_sqin=total_area,
                total_area_sqft=total_area / 144,
                sheet_count_4x8=math.ceil(area_with_waste / self.SHEET_4X8_SQIN),
                sheet_count_5x5=math.ceil(area_with_waste / self.SHEET_5X5_SQIN),
                waste_percentage=self.waste_factor,
            )

        return estimates

    def estimate_total(self, cut_list: list[CutPiece]) -> MaterialEstimate:
        """Estimate total materials needed (all types combined)."""
        total_area = sum(piece.area for piece in cut_list)
        area_with_waste = total_area * (1 + self.waste_factor)
        return MaterialEstimate(
            total_area_sqin=total_area,
            total_area_sqft=total_area / 144,
            sheet_count_4x8=math.ceil(area_with_waste / self.SHEET_4X8_SQIN),
            sheet_count_5x5=math.ceil(area_with_waste / self.SHEET_5X5_SQIN),
            waste_percentage=self.waste_factor,
        )
