"""Mounting hardware generation service.

This module provides the MountingService class for generating
mounting hardware lists based on mounting system type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...components.results import HardwareItem
from ...value_objects import (
    LoadCategory,
    MountingSystem,
    WallType,
)
from .config import InstallationConfig
from .models import StudHitAnalysis

if TYPE_CHECKING:
    from ...entities import Cabinet


class MountingService:
    """Service for generating mounting hardware specifications.

    Creates hardware lists based on mounting system type (direct-to-stud,
    French cleat, toggle bolt, hanging rail) and wall type.
    """

    # Load ratings per linear foot based on load category
    LOAD_RATINGS: dict[LoadCategory, float] = {
        LoadCategory.LIGHT: 15.0,
        LoadCategory.MEDIUM: 30.0,
        LoadCategory.HEAVY: 50.0,
    }

    # Safety factor for mounting calculations (4:1 ratio)
    SAFETY_FACTOR: float = 4.0

    # Standard screw lengths available (inches)
    STANDARD_SCREW_LENGTHS: tuple[float, ...] = (
        1.5,
        1.75,
        2.0,
        2.25,
        2.5,
        2.75,
        3.0,
        3.5,
        4.0,
    )

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the mounting service.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config

    def generate_hardware(
        self, cabinet: "Cabinet", stud_analysis: StudHitAnalysis
    ) -> list[HardwareItem]:
        """Generate mounting hardware list.

        Creates a list of hardware items needed for installation
        based on the mounting system, wall type, and stud alignment.

        Args:
            cabinet: Cabinet to generate hardware for.
            stud_analysis: Stud alignment analysis results.

        Returns:
            List of HardwareItem specifications for mounting.
        """
        hardware: list[HardwareItem] = []
        back_thickness = (
            cabinet.back_material.thickness if cabinet.back_material else 0.25
        )

        # Handle masonry walls (concrete, CMU, brick)
        if self.config.wall_type in (WallType.CONCRETE, WallType.CMU, WallType.BRICK):
            hardware.extend(self._generate_masonry_hardware(cabinet))
            return hardware

        # Handle drywall/plaster walls based on mounting system
        if self.config.mounting_system == MountingSystem.DIRECT_TO_STUD:
            hardware.extend(
                self._generate_direct_to_stud_hardware(
                    cabinet, stud_analysis, back_thickness
                )
            )

        elif self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
            hardware.extend(self._generate_toggle_bolt_hardware(cabinet))

        elif self.config.mounting_system == MountingSystem.FRENCH_CLEAT:
            hardware.extend(
                self._generate_french_cleat_hardware(cabinet, stud_analysis)
            )

        elif self.config.mounting_system == MountingSystem.HANGING_RAIL:
            hardware.extend(
                self._generate_hanging_rail_hardware(cabinet, stud_analysis)
            )

        return hardware

    def _calculate_screw_length(self, back_thickness: float) -> float:
        """Calculate required screw length and round up to standard size.

        Args:
            back_thickness: Cabinet back panel thickness in inches.

        Returns:
            Standard screw length in inches.
        """
        # Minimum penetration into stud/wall
        min_penetration = 1.5
        # Required length = back + wall + penetration
        required_length = back_thickness + self.config.wall_thickness + min_penetration

        # Round up to next standard length
        for std_length in self.STANDARD_SCREW_LENGTHS:
            if std_length >= required_length:
                return std_length

        # If exceeds all standard lengths, return the maximum
        return self.STANDARD_SCREW_LENGTHS[-1]

    def _generate_direct_to_stud_hardware(
        self,
        cabinet: "Cabinet",
        stud_analysis: StudHitAnalysis,
        back_thickness: float,
    ) -> list[HardwareItem]:
        """Generate hardware for direct-to-stud mounting."""
        hardware: list[HardwareItem] = []

        screw_length = self._calculate_screw_length(back_thickness)
        stud_hit_count = max(stud_analysis.stud_hit_count, 2)  # Minimum 2 locations
        screws_per_stud = 2  # 2 screws per stud location (top and bottom)

        hardware.append(
            HardwareItem(
                name=f'#10 x {screw_length}" cabinet screw',
                quantity=stud_hit_count * screws_per_stud,
                sku=None,
                notes="Direct mounting into wall studs",
            )
        )

        return hardware

    def _generate_toggle_bolt_hardware(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Generate hardware for toggle bolt mounting."""
        hardware: list[HardwareItem] = []

        # Determine toggle bolt size based on load category
        if self.config.expected_load == LoadCategory.HEAVY:
            toggle_size = '3/8"'
            capacity_per_toggle = 75.0  # lbs
        else:
            toggle_size = '1/4"'
            capacity_per_toggle = 50.0  # lbs

        # Calculate quantity based on load with safety factor
        cabinet_width_ft = cabinet.width / 12.0
        expected_load = cabinet_width_ft * self.LOAD_RATINGS[self.config.expected_load]
        required_capacity = expected_load * self.SAFETY_FACTOR
        qty = max(4, int(required_capacity / capacity_per_toggle) + 1)

        hardware.append(
            HardwareItem(
                name=f"{toggle_size} toggle bolt",
                quantity=qty,
                sku=None,
                notes=f"For non-stud mounting, {capacity_per_toggle:.0f} lb capacity each",
            )
        )

        return hardware

    def _generate_french_cleat_hardware(
        self, cabinet: "Cabinet", stud_analysis: StudHitAnalysis
    ) -> list[HardwareItem]:
        """Generate hardware for French cleat mounting."""
        hardware: list[HardwareItem] = []

        stud_hit_count = max(stud_analysis.stud_hit_count, 2)

        # Lag bolts for wall cleat mounting into studs
        hardware.append(
            HardwareItem(
                name='1/4" x 3" lag bolt',
                quantity=stud_hit_count,
                sku=None,
                notes="For mounting wall cleat into studs",
            )
        )

        # Washers for lag bolts
        hardware.append(
            HardwareItem(
                name='1/4" flat washer',
                quantity=stud_hit_count,
                sku=None,
                notes="Use with lag bolts",
            )
        )

        # Cabinet screws for attaching cabinet cleat to cabinet back
        # Calculate based on cleat width
        cleat_width = cabinet.width * (self.config.cleat_width_percentage / 100.0)
        screw_spacing = 6.0  # inches
        cabinet_cleat_screws = max(4, int(cleat_width / screw_spacing) + 1)

        hardware.append(
            HardwareItem(
                name='#8 x 1-1/4" wood screw',
                quantity=cabinet_cleat_screws,
                sku=None,
                notes="For attaching cleat to cabinet back",
            )
        )

        return hardware

    def _generate_hanging_rail_hardware(
        self, cabinet: "Cabinet", stud_analysis: StudHitAnalysis
    ) -> list[HardwareItem]:
        """Generate hardware for hanging rail mounting."""
        hardware: list[HardwareItem] = []

        # Hanging rail
        hardware.append(
            HardwareItem(
                name=f'{cabinet.width:.0f}" hanging rail',
                quantity=1,
                sku=None,
                notes="Standard cabinet hanging rail system",
            )
        )

        # Rail mounting screws (based on stud hits)
        stud_hit_count = max(stud_analysis.stud_hit_count, 2)
        hardware.append(
            HardwareItem(
                name='#10 x 3" cabinet screw',
                quantity=stud_hit_count * 2,
                sku=None,
                notes="For mounting rail into studs",
            )
        )

        # Cabinet mounting brackets (typically 2 per cabinet)
        hardware.append(
            HardwareItem(
                name="Hanging rail bracket",
                quantity=2,
                sku=None,
                notes="Mount inside cabinet, hooks onto rail",
            )
        )

        return hardware

    def _generate_masonry_hardware(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Generate hardware for masonry wall mounting."""
        hardware: list[HardwareItem] = []

        # Determine Tapcon size based on load
        if self.config.expected_load == LoadCategory.HEAVY:
            tapcon_size = '1/4" x 2-3/4"'
            drill_bit = '3/16"'
        else:
            tapcon_size = '3/16" x 2-3/4"'
            drill_bit = '5/32"'

        # Calculate quantity based on load with safety factor
        cabinet_width_ft = cabinet.width / 12.0
        expected_load = cabinet_width_ft * self.LOAD_RATINGS[self.config.expected_load]

        # Tapcons: ~100 lbs capacity each in concrete
        capacity_per_tapcon = 100.0
        required_capacity = expected_load * self.SAFETY_FACTOR
        qty = max(4, int(required_capacity / capacity_per_tapcon) + 1)

        hardware.append(
            HardwareItem(
                name=f"{tapcon_size} Tapcon screw",
                quantity=qty,
                sku=None,
                notes=f"For {self.config.wall_type.value} wall mounting",
            )
        )

        hardware.append(
            HardwareItem(
                name=f"{drill_bit} carbide masonry drill bit",
                quantity=1,
                sku=None,
                notes="Required for pre-drilling Tapcon holes",
            )
        )

        return hardware
