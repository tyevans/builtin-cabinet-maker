"""Input validation service for layout generation.

Centralizes validation logic extracted from GenerateLayoutCommand,
providing consistent error reporting and easier testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain import validate_section_specs
from cabinets.domain.section_resolver import validate_row_specs

if TYPE_CHECKING:
    from cabinets.domain.section_resolver import RowSpec, SectionSpec
    from cabinets.application.dtos import LayoutParametersInput, WallInput


class InputValidatorService:
    """Service for validating layout generation inputs.

    Centralizes validation logic that was previously inline in
    GenerateLayoutCommand.execute(). This enables:
    - Consistent validation across different entry points
    - Easier unit testing of validation rules
    - Clear separation of validation from orchestration
    """

    def validate_wall_input(self, wall_input: "WallInput") -> list[str]:
        """Validate wall dimensions input.

        Delegates to WallInput.validate() for dimension validation.

        Args:
            wall_input: Wall dimensions to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        return wall_input.validate()

    def validate_params_input(self, params_input: "LayoutParametersInput") -> list[str]:
        """Validate layout parameters input.

        Delegates to LayoutParametersInput.validate() for parameter validation.

        Args:
            params_input: Layout parameters to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        return params_input.validate()

    def validate_specs(
        self,
        section_specs: "list[SectionSpec] | None",
        row_specs: "list[RowSpec] | None",
        wall_width: float,
        wall_height: float,
        material_thickness: float,
    ) -> list[str]:
        """Validate section and row specifications.

        Checks:
        1. Mutual exclusivity (can't use both section_specs and row_specs)
        2. Section specs fit within wall width
        3. Row specs fit within wall height

        Args:
            section_specs: Optional section specifications.
            row_specs: Optional row specifications for multi-row layouts.
            wall_width: Wall width for fit validation.
            wall_height: Wall height for fit validation.
            material_thickness: Material thickness for validation.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        # Check mutual exclusivity
        if section_specs is not None and row_specs is not None:
            errors.append(
                "Cannot specify both section_specs and row_specs. "
                "Use section_specs for single-row layout or row_specs for multi-row layout."
            )
            return errors  # Early return - can't validate further

        # Validate section specs if provided
        if section_specs is not None:
            spec_errors = validate_section_specs(
                section_specs,
                wall_width,
                material_thickness,
            )
            errors.extend(spec_errors)

        # Validate row specs if provided
        if row_specs is not None:
            row_errors = validate_row_specs(
                row_specs,
                wall_height,
                material_thickness,
            )
            errors.extend(row_errors)

        return errors

    def validate_all(
        self,
        wall_input: "WallInput",
        params_input: "LayoutParametersInput",
        section_specs: "list[SectionSpec] | None" = None,
        row_specs: "list[RowSpec] | None" = None,
    ) -> list[str]:
        """Validate all inputs for layout generation.

        Convenience method that combines all validation steps.

        Args:
            wall_input: Wall dimensions to validate.
            params_input: Layout parameters to validate.
            section_specs: Optional section specifications.
            row_specs: Optional row specifications.

        Returns:
            List of all validation error messages (empty if all valid).
        """
        errors: list[str] = []
        errors.extend(self.validate_wall_input(wall_input))
        errors.extend(self.validate_params_input(params_input))
        errors.extend(
            self.validate_specs(
                section_specs=section_specs,
                row_specs=row_specs,
                wall_width=wall_input.width,
                wall_height=wall_input.height,
                material_thickness=params_input.material_thickness,
            )
        )
        return errors
