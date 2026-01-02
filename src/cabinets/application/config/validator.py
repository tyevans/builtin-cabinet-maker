"""Validation facade for cabinet configurations.

This module provides the main validation entry point and backwards-compatible
exports. The actual validation logic is implemented in the validators subpackage.
"""

from cabinets.application.config.schemas import CabinetConfiguration

# Re-export validation structures for backwards compatibility
from .validators.base import ValidationError, ValidationResult, ValidationWarning

# Re-export constants for backwards compatibility
from .validators.infrastructure import (
    MIN_CUTOUT_EDGE_DISTANCE,
    STANDARD_GROMMET_SIZES,
)
from .validators.infrastructure import (
    check_infrastructure_advisories,
)
from .validators.obstacle import check_obstacle_advisories
from .validators.registry import ValidatorRegistry
from .validators.woodworking import (
    MAX_ASPECT_RATIO,
    MIN_RECOMMENDED_THICKNESS,
    check_woodworking_advisories,
)

# Re-export helper functions with legacy names for backwards compatibility
from .validators.helpers import (
    cutouts_overlap as _cutouts_overlap,
    get_panel_dimensions as _get_panel_dimensions,
    get_section_count as _get_section_count,
    get_cutout_info as _get_cutout_info,
    estimate_fill_section_width as _estimate_fill_section_width,
    wall_completely_blocked as _wall_completely_blocked,
    wall_mostly_blocked as _wall_mostly_blocked,
)

# Import validators for registration
from .validators.infrastructure import InfrastructureValidator
from .validators.obstacle import ObstacleValidator
from .validators.section import SectionDimensionValidator
from .validators.woodworking import WoodworkingValidator


def _ensure_validators_registered() -> None:
    """Ensure all validators are registered with the registry."""
    if not ValidatorRegistry.is_registered("woodworking"):
        ValidatorRegistry.register(WoodworkingValidator())
    if not ValidatorRegistry.is_registered("obstacle"):
        ValidatorRegistry.register(ObstacleValidator())
    if not ValidatorRegistry.is_registered("infrastructure"):
        ValidatorRegistry.register(InfrastructureValidator())
    if not ValidatorRegistry.is_registered("section_dimension"):
        ValidatorRegistry.register(SectionDimensionValidator())


# Register validators on module import
_ensure_validators_registered()


def validate_config(config: CabinetConfiguration) -> ValidationResult:
    """Perform full validation of a cabinet configuration.

    This function performs both structural validation (which should already
    be handled by Pydantic) and advisory checks for woodworking best practices,
    obstacle validation, and infrastructure validation.

    Args:
        config: A CabinetConfiguration instance (already validated by Pydantic)

    Returns:
        ValidationResult containing any errors or warnings
    """
    # Ensure validators are registered
    _ensure_validators_registered()

    # Use the registry to run all validators
    return ValidatorRegistry.validate_all(config)


__all__ = [
    # Main validation function
    "validate_config",
    # Validation structures
    "ValidationError",
    "ValidationWarning",
    "ValidationResult",
    # Registry
    "ValidatorRegistry",
    # Legacy functions for backwards compatibility
    "check_woodworking_advisories",
    "check_obstacle_advisories",
    "check_infrastructure_advisories",
    # Constants
    "MIN_RECOMMENDED_THICKNESS",
    "MAX_ASPECT_RATIO",
    "STANDARD_GROMMET_SIZES",
    "MIN_CUTOUT_EDGE_DISTANCE",
    # Legacy helper functions (underscore-prefixed)
    "_cutouts_overlap",
    "_get_panel_dimensions",
    "_get_section_count",
    "_get_cutout_info",
    "_estimate_fill_section_width",
    "_wall_completely_blocked",
    "_wall_mostly_blocked",
]
