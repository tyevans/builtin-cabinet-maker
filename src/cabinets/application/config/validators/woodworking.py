"""Woodworking advisory validator for cabinet configurations.

This module provides validation for woodworking best practices including
shelf span limits, material thickness, and cabinet stability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain.services.woodworking import get_max_span

from .base import ValidationResult
from .helpers import estimate_fill_section_width

if TYPE_CHECKING:
    from cabinets.application.config.schemas import CabinetConfiguration

# Woodworking Advisory Constants
MIN_RECOMMENDED_THICKNESS = 0.5  # inches
MAX_ASPECT_RATIO = 4.0  # height:depth ratio for stability


class WoodworkingValidator:
    """Validator for woodworking best practices.

    Checks configuration against common woodworking guidelines:
    - Shelf span exceeds recommended maximum for material thickness
    - Material thickness is very thin (< 0.5")
    - Extreme cabinet aspect ratios (stability concerns)
    - Back panel material thickness

    These are advisory warnings and do not prevent cabinet generation.
    """

    @property
    def name(self) -> str:
        """Return the validator name."""
        return "woodworking"

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        """Check configuration against woodworking best practices.

        Args:
            config: A validated CabinetConfiguration instance

        Returns:
            ValidationResult containing any warnings found
        """
        result = ValidationResult()

        material_thickness = config.cabinet.material.thickness
        material_type = config.cabinet.material.type

        # Check each section for shelf span concerns
        for i, section in enumerate(config.cabinet.sections):
            section_path = f"cabinet.sections[{i}]"

            # Determine effective section width
            section_width: float | None = None
            if isinstance(section.width, (int, float)):
                section_width = float(section.width)
            elif section.width == "fill":
                # For "fill" sections, we need to estimate the width
                # This is approximate - actual calculation happens in domain layer
                section_width = estimate_fill_section_width(config, i)

            # Check shelf span using material-specific limits from SPAN_LIMITS
            if section_width is not None and section.shelves > 0:
                max_span = get_max_span(material_type, material_thickness)
                if section_width > max_span:
                    result.add_warning(
                        path=section_path,
                        message=(
                            f'Shelf span of {section_width:.0f}" exceeds recommended '
                            f'{max_span:.0f}" for {material_type.value} at {material_thickness}" thickness'
                        ),
                        suggestion=(
                            "Consider adding a center support divider or using "
                            'thicker material (1" or greater)'
                        ),
                    )

        # Check for very thin material
        if material_thickness < MIN_RECOMMENDED_THICKNESS:
            result.add_warning(
                path="cabinet.material.thickness",
                message=(
                    f'Material thickness of {material_thickness}" is below '
                    f'recommended minimum of {MIN_RECOMMENDED_THICKNESS}"'
                ),
                suggestion='Consider using at least 1/2" (0.5") material for structural integrity',
            )

        # Check back material thickness if specified
        if config.cabinet.back_material:
            back_thickness = config.cabinet.back_material.thickness
            if back_thickness < 0.25:
                result.add_warning(
                    path="cabinet.back_material.thickness",
                    message=f'Back panel thickness of {back_thickness}" is very thin',
                    suggestion='Consider using at least 1/4" (0.25") material for the back panel',
                )

        # Check aspect ratio for stability
        aspect_ratio = config.cabinet.height / config.cabinet.depth
        if aspect_ratio > MAX_ASPECT_RATIO:
            result.add_warning(
                path="cabinet",
                message=(
                    f"Height-to-depth ratio of {aspect_ratio:.1f}:1 may cause stability issues"
                ),
                suggestion=(
                    f"Consider increasing depth or securing cabinet to wall. "
                    f"Recommended ratio is {MAX_ASPECT_RATIO:.0f}:1 or less"
                ),
            )

        return result


# Legacy function for backwards compatibility
def check_woodworking_advisories(config: CabinetConfiguration) -> ValidationResult:
    """Check configuration against woodworking best practices.

    This function is maintained for backwards compatibility.
    New code should use WoodworkingValidator directly.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        ValidationResult containing any warnings found
    """
    validator = WoodworkingValidator()
    return validator.validate(config)
