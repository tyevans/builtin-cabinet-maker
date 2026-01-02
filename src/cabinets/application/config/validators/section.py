"""Section dimension validation for cabinet configurations.

This module provides validation for section dimensions including
width and depth constraints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ValidationResult

if TYPE_CHECKING:
    from cabinets.application.config.schemas import CabinetConfiguration


class SectionDimensionValidator:
    """Validator for section dimension constraints.

    Validates section dimensions against:
    - Total fixed section width doesn't exceed cabinet interior width
    - Section depth overrides don't exceed cabinet depth
    - Multi-row section depth validation
    """

    @property
    def name(self) -> str:
        """Return the validator name."""
        return "section_dimension"

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        """Validate section dimensions against cabinet constraints.

        Args:
            config: A validated CabinetConfiguration instance

        Returns:
            ValidationResult containing any errors found
        """
        result = ValidationResult()

        # Validate total fixed section width doesn't exceed cabinet width
        self._validate_section_widths(config, result)

        # Validate section depths
        self._validate_section_depths(config, result)

        # Validate multi-row section depths
        self._validate_row_section_depths(config, result)

        return result

    def _validate_section_widths(
        self, config: CabinetConfiguration, result: ValidationResult
    ) -> None:
        """Validate that total fixed section width fits in cabinet."""
        total_fixed_width = 0.0
        for section in config.cabinet.sections:
            if isinstance(section.width, (int, float)):
                total_fixed_width += section.width

        material_thickness = config.cabinet.material.thickness
        num_dividers = (
            len(config.cabinet.sections) - 1 if config.cabinet.sections else 0
        )
        available_width = (
            config.cabinet.width
            - (material_thickness * 2)
            - (material_thickness * num_dividers)
        )

        if total_fixed_width > available_width:
            result.add_error(
                path="cabinet.sections",
                message=(
                    f'Total fixed section width ({total_fixed_width:.1f}") exceeds '
                    f'available cabinet interior width ({available_width:.1f}")'
                ),
                value=total_fixed_width,
            )

    def _validate_section_depths(
        self, config: CabinetConfiguration, result: ValidationResult
    ) -> None:
        """Validate that section depths don't exceed cabinet depth (FR-06.3)."""
        cabinet_depth = config.cabinet.depth
        for i, section in enumerate(config.cabinet.sections):
            if section.depth is not None and section.depth > cabinet_depth:
                result.add_error(
                    path=f"cabinet.sections[{i}].depth",
                    message=(
                        f'Section depth ({section.depth}") exceeds '
                        f'cabinet depth ({cabinet_depth}")'
                    ),
                    value=section.depth,
                )

    def _validate_row_section_depths(
        self, config: CabinetConfiguration, result: ValidationResult
    ) -> None:
        """Validate section depths in multi-row layouts."""
        if not config.cabinet.rows:
            return

        cabinet_depth = config.cabinet.depth
        for row_idx, row in enumerate(config.cabinet.rows):
            for section_idx, section in enumerate(row.sections):
                if section.depth is not None and section.depth > cabinet_depth:
                    result.add_error(
                        path=f"cabinet.rows[{row_idx}].sections[{section_idx}].depth",
                        message=(
                            f'Section depth ({section.depth}") exceeds '
                            f'cabinet depth ({cabinet_depth}")'
                        ),
                        value=section.depth,
                    )
