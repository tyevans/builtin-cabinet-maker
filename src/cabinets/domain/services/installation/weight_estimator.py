"""Cabinet weight estimation service.

This module provides the WeightEstimator class for calculating
estimated cabinet weight and load capacity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...value_objects import (
    LoadCategory,
    MaterialType,
    MountingSystem,
)
from ..panel_generation import PanelGenerationService
from .config import InstallationConfig
from .models import WeightEstimate

if TYPE_CHECKING:
    from ...entities import Cabinet


class WeightEstimator:
    """Service for estimating cabinet weight and load capacity.

    Calculates the estimated weight of the empty cabinet based on
    panel dimensions and material density, then adds expected load
    based on the configured load category.
    """

    # Material densities in lbs per square foot per inch of thickness
    # Used for estimating cabinet weight based on panel dimensions
    MATERIAL_DENSITIES: dict[MaterialType, float] = {
        MaterialType.PLYWOOD: 3.0,
        MaterialType.MDF: 4.0,
        MaterialType.PARTICLE_BOARD: 3.5,
        MaterialType.SOLID_WOOD: 3.5,
    }

    # Load ratings per linear foot based on load category
    LOAD_RATINGS: dict[LoadCategory, float] = {
        LoadCategory.LIGHT: 15.0,
        LoadCategory.MEDIUM: 30.0,
        LoadCategory.HEAVY: 50.0,
    }

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the weight estimator.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config

    def estimate_weight(self, cabinet: "Cabinet") -> WeightEstimate:
        """Estimate cabinet weight and expected load.

        Calculates the estimated weight of the empty cabinet based on
        panel dimensions and material density, then adds expected load
        based on the configured load category.

        Args:
            cabinet: Cabinet to estimate weight for.

        Returns:
            WeightEstimate with weight and load information.
        """
        # Calculate empty weight from panel areas
        # Weight = area (sq ft) * thickness (inches) * density (lbs/sqft/inch)
        panel_service = PanelGenerationService()
        panels = panel_service.get_all_panels(cabinet)
        empty_weight_lbs = 0.0

        for panel in panels:
            # Convert dimensions from inches to feet for area calculation
            area_sqin = panel.width * panel.height
            area_sqft = area_sqin / 144.0  # 144 sq inches per sq foot

            # Get material density (lbs per sqft per inch of thickness)
            density = self.MATERIAL_DENSITIES.get(
                panel.material.material_type,
                3.0,  # Default to plywood density
            )

            # Weight = area * thickness * density
            panel_weight = area_sqft * panel.material.thickness * density
            empty_weight_lbs += panel_weight

        # Calculate expected load based on cabinet width and load category
        cabinet_width_ft = cabinet.width / 12.0
        load_per_foot = self.LOAD_RATINGS[self.config.expected_load]
        expected_load = cabinet_width_ft * load_per_foot

        # Total estimated load
        total_estimated_load_lbs = empty_weight_lbs + expected_load

        # Generate capacity warning if load is heavy
        capacity_warning: str | None = None

        # Safe mounting capacity thresholds (approximate)
        # Direct to stud: ~150 lbs per stud with proper screws
        # Toggle bolts: ~50-75 lbs per toggle
        # French cleat: depends on stud mounting
        if self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
            # Toggle bolts have lower capacity
            safe_threshold = 100.0  # Conservative threshold for toggle bolts
            if total_estimated_load_lbs > safe_threshold:
                capacity_warning = (
                    f"Total estimated load ({total_estimated_load_lbs:.0f} lbs) may exceed "
                    "safe capacity for toggle bolt mounting. Consider using French cleat "
                    "with stud mounting or direct-to-stud installation."
                )
        elif self.config.expected_load == LoadCategory.HEAVY:
            safe_threshold = 200.0  # Threshold for heavy loads
            if total_estimated_load_lbs > safe_threshold:
                capacity_warning = (
                    f"Heavy load configuration ({total_estimated_load_lbs:.0f} lbs estimated). "
                    "Ensure mounting into at least 2 studs with appropriate lag bolts "
                    "or use a French cleat system for secure installation."
                )

        return WeightEstimate(
            empty_weight_lbs=round(empty_weight_lbs, 1),
            expected_load_per_foot=load_per_foot,
            total_estimated_load_lbs=round(total_estimated_load_lbs, 1),
            capacity_warning=capacity_warning,
        )
