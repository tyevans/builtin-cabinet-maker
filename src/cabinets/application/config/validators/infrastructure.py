"""Infrastructure validation for cabinet configurations.

This module provides validation for infrastructure elements including
cutouts, grommets, ventilation, and electrical outlets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ValidationError, ValidationResult, ValidationWarning
from .helpers import (
    cutouts_overlap,
    get_cutout_info,
    get_panel_dimensions,
    get_section_count,
)

if TYPE_CHECKING:
    from cabinets.application.config.schemas import (
        CabinetConfiguration,
        InfrastructureConfigSchema,
    )

# Standard grommet sizes in inches
STANDARD_GROMMET_SIZES: frozenset[float] = frozenset({2.0, 2.5, 3.0})

# Minimum edge distance for cutouts in inches
MIN_CUTOUT_EDGE_DISTANCE: float = 1.0


class InfrastructureValidator:
    """Validator for infrastructure configuration.

    Validates infrastructure elements against the following rules:
    - V-01: Cutout within panel bounds
    - V-02: Cutout edge distance (min 1")
    - V-03: Cutout overlap detection
    - V-04: Outlet accessibility (behind fixed shelf warning)
    - V-05: Grommet size validation (standard sizes: 2, 2.5, or 3)
    - V-06: Section index validation
    - V-07: Ventilation adequacy warning
    """

    @property
    def name(self) -> str:
        """Return the validator name."""
        return "infrastructure"

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        """Check infrastructure configuration for potential issues.

        Args:
            config: A validated CabinetConfiguration instance

        Returns:
            ValidationResult containing any errors or warnings
        """
        result = ValidationResult()

        if not config.infrastructure:
            return result

        infra = config.infrastructure
        section_count = get_section_count(config)

        # Collect all cutouts for overlap detection, organized by panel
        panel_cutouts: dict[
            str, list[tuple[str, tuple[float, float], tuple[float, float]]]
        ] = {}

        # Validate lighting section indices
        self._validate_lighting(infra, section_count, result)

        # Process outlets
        self._validate_outlets(config, infra, section_count, panel_cutouts, result)

        # Process grommets
        self._validate_grommets(config, infra, section_count, panel_cutouts, result)

        # Process ventilation areas
        self._validate_ventilation(config, infra, panel_cutouts, result)

        # V-03: Cutout overlap detection
        self._check_cutout_overlaps(panel_cutouts, result)

        # V-07: Ventilation adequacy warning
        self._check_ventilation_adequacy(infra, result)

        return result

    def _validate_lighting(
        self,
        infra: "InfrastructureConfigSchema",
        section_count: int,
        result: ValidationResult,
    ) -> None:
        """Validate lighting section indices."""
        for i, lighting in enumerate(infra.lighting):
            path = f"infrastructure.lighting[{i}]"
            for section_idx in lighting.section_indices:
                if section_idx >= section_count:
                    result.add_error(
                        path=f"{path}.section_indices",
                        message=f"Section index {section_idx} out of range (cabinet has {section_count} sections)",
                        value=section_idx,
                    )

    def _validate_outlets(
        self,
        config: "CabinetConfiguration",
        infra: "InfrastructureConfigSchema",
        section_count: int,
        panel_cutouts: dict[
            str, list[tuple[str, tuple[float, float], tuple[float, float]]]
        ],
        result: ValidationResult,
    ) -> None:
        """Validate outlet configurations."""
        for i, outlet in enumerate(infra.outlets):
            path = f"infrastructure.outlets[{i}]"

            # V-06: Section index validation
            if outlet.section_index >= section_count:
                result.add_error(
                    path=f"{path}.section_index",
                    message=f"Section index {outlet.section_index} out of range (cabinet has {section_count} sections)",
                    value=outlet.section_index,
                )

            # Get panel dimensions and cutout info
            panel_dims = get_panel_dimensions(config, outlet.panel)
            cutout_path, cutout_pos, cutout_dims, panel = get_cutout_info(
                outlet, "outlet", i
            )

            # V-01: Cutout within panel bounds
            self._check_cutout_bounds(path, cutout_pos, cutout_dims, panel_dims, result)

            # V-02: Cutout edge distance
            self._check_edge_distance(path, cutout_pos, cutout_dims, panel_dims, result)

            # V-04: Outlet accessibility - check if outlet is behind a shelf position
            if outlet.panel == "back" and config.cabinet.sections:
                if outlet.section_index < len(config.cabinet.sections):
                    section = config.cabinet.sections[outlet.section_index]
                    if section.shelves > 0:
                        result.add_warning(
                            path=path,
                            message=f"Outlet behind fixed shelf at section {outlet.section_index}",
                            suggestion="Consider adjusting shelf positions or outlet location for accessibility",
                        )

            # Collect for overlap detection
            if panel not in panel_cutouts:
                panel_cutouts[panel] = []
            panel_cutouts[panel].append((cutout_path, cutout_pos, cutout_dims))

    def _validate_grommets(
        self,
        config: "CabinetConfiguration",
        infra: "InfrastructureConfigSchema",
        section_count: int,
        panel_cutouts: dict[
            str, list[tuple[str, tuple[float, float], tuple[float, float]]]
        ],
        result: ValidationResult,
    ) -> None:
        """Validate grommet configurations."""
        for i, grommet in enumerate(infra.grommets):
            path = f"infrastructure.grommets[{i}]"

            # V-05: Grommet size validation
            if grommet.size not in STANDARD_GROMMET_SIZES:
                result.add_error(
                    path=f"{path}.size",
                    message=f"Invalid grommet size: {grommet.size} (use 2, 2.5, or 3)",
                    value=grommet.size,
                )

            # V-06: Section index validation (if specified)
            if (
                grommet.section_index is not None
                and grommet.section_index >= section_count
            ):
                result.add_error(
                    path=f"{path}.section_index",
                    message=f"Section index {grommet.section_index} out of range (cabinet has {section_count} sections)",
                    value=grommet.section_index,
                )

            # Get panel dimensions and cutout info
            panel_dims = get_panel_dimensions(config, grommet.panel)
            cutout_path, cutout_pos, cutout_dims, panel = get_cutout_info(
                grommet, "grommet", i
            )

            # V-01: Cutout within panel bounds
            self._check_cutout_bounds(path, cutout_pos, cutout_dims, panel_dims, result)

            # V-02: Cutout edge distance
            self._check_edge_distance(path, cutout_pos, cutout_dims, panel_dims, result)

            # Collect for overlap detection
            if panel not in panel_cutouts:
                panel_cutouts[panel] = []
            panel_cutouts[panel].append((cutout_path, cutout_pos, cutout_dims))

    def _validate_ventilation(
        self,
        config: "CabinetConfiguration",
        infra: "InfrastructureConfigSchema",
        panel_cutouts: dict[
            str, list[tuple[str, tuple[float, float], tuple[float, float]]]
        ],
        result: ValidationResult,
    ) -> None:
        """Validate ventilation configurations."""
        for i, vent in enumerate(infra.ventilation):
            path = f"infrastructure.ventilation[{i}]"

            # Get panel dimensions and cutout info
            panel_dims = get_panel_dimensions(config, vent.panel)
            cutout_path, cutout_pos, cutout_dims, panel = get_cutout_info(
                vent, "ventilation", i
            )

            # V-01: Cutout within panel bounds
            self._check_cutout_bounds(path, cutout_pos, cutout_dims, panel_dims, result)

            # V-02: Cutout edge distance
            self._check_edge_distance(path, cutout_pos, cutout_dims, panel_dims, result)

            # Collect for overlap detection
            if panel not in panel_cutouts:
                panel_cutouts[panel] = []
            panel_cutouts[panel].append((cutout_path, cutout_pos, cutout_dims))

    def _check_cutout_bounds(
        self,
        path: str,
        cutout_pos: tuple[float, float],
        cutout_dims: tuple[float, float],
        panel_dims: tuple[float, float],
        result: ValidationResult,
    ) -> None:
        """Check if cutout is within panel bounds."""
        if cutout_pos[0] + cutout_dims[0] > panel_dims[0]:
            result.add_error(
                path=path,
                message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel width: {panel_dims[0]})",
            )
        if cutout_pos[1] + cutout_dims[1] > panel_dims[1]:
            result.add_error(
                path=path,
                message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) exceeds panel dimensions (panel height: {panel_dims[1]})",
            )
        if cutout_pos[0] < 0 or cutout_pos[1] < 0:
            result.add_error(
                path=path,
                message=f"Cutout at ({cutout_pos[0]}, {cutout_pos[1]}) has negative position",
            )

    def _check_edge_distance(
        self,
        path: str,
        cutout_pos: tuple[float, float],
        cutout_dims: tuple[float, float],
        panel_dims: tuple[float, float],
        result: ValidationResult,
    ) -> None:
        """Check if cutout maintains minimum edge distance."""
        if cutout_pos[0] < MIN_CUTOUT_EDGE_DISTANCE:
            result.add_error(
                path=path,
                message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
            )
        if cutout_pos[1] < MIN_CUTOUT_EDGE_DISTANCE:
            result.add_error(
                path=path,
                message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
            )
        if panel_dims[0] - (cutout_pos[0] + cutout_dims[0]) < MIN_CUTOUT_EDGE_DISTANCE:
            result.add_error(
                path=path,
                message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
            )
        if panel_dims[1] - (cutout_pos[1] + cutout_dims[1]) < MIN_CUTOUT_EDGE_DISTANCE:
            result.add_error(
                path=path,
                message=f'Cutout too close to edge (min {MIN_CUTOUT_EDGE_DISTANCE}")',
            )

    def _check_cutout_overlaps(
        self,
        panel_cutouts: dict[
            str, list[tuple[str, tuple[float, float], tuple[float, float]]]
        ],
        result: ValidationResult,
    ) -> None:
        """Check for cutout overlaps on each panel."""
        for panel, cutouts in panel_cutouts.items():
            for i, (path1, pos1, dims1) in enumerate(cutouts):
                for j, (path2, pos2, dims2) in enumerate(cutouts[i + 1 :], start=i + 1):
                    if cutouts_overlap(pos1, dims1, pos2, dims2):
                        result.add_error(
                            path=path1,
                            message=f"Cutouts overlap at ({pos1[0]}, {pos1[1]})",
                        )

    def _check_ventilation_adequacy(
        self, infra: "InfrastructureConfigSchema", result: ValidationResult
    ) -> None:
        """Check if electronics enclosure has adequate ventilation."""
        has_ventilation = len(infra.ventilation) > 0
        has_outlets = len(infra.outlets) > 0

        # If we have outlets but no ventilation, suggest ventilation for electronics
        if has_outlets and not has_ventilation:
            result.add_warning(
                path="infrastructure",
                message="Electronics enclosure may need additional ventilation",
                suggestion="Consider adding ventilation cutouts for heat dissipation",
            )


# Legacy function for backwards compatibility
def check_infrastructure_advisories(
    config: CabinetConfiguration,
) -> list[ValidationError | ValidationWarning]:
    """Check infrastructure configuration for potential issues.

    This function is maintained for backwards compatibility.
    New code should use InfrastructureValidator directly.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of validation errors and warnings for infrastructure-related issues
    """
    validator = InfrastructureValidator()
    result = validator.validate(config)

    # Convert ValidationResult to list for legacy compatibility
    results: list[ValidationError | ValidationWarning] = []
    results.extend(result.errors)
    results.extend(result.warnings)
    return results
