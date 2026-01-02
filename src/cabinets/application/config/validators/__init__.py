"""Validators subpackage - modular validators for cabinet configurations.

This package provides focused validator classes following the Single Responsibility
Principle, organized by validation domain:
- WoodworkingValidator: Material thickness, span limits, aspect ratios
- ObstacleValidator: Obstacle bounds, wall blocking detection
- InfrastructureValidator: Cutouts, grommets, ventilation, outlets
- SectionDimensionValidator: Section depth and width validation

The ValidatorRegistry provides a central registry for all validators and
coordinates running them against a configuration.
"""

from .base import ValidationError, ValidationResult, ValidationWarning
from .helpers import (
    cutouts_overlap,
    estimate_fill_section_width,
    get_cutout_info,
    get_panel_dimensions,
    get_section_count,
    wall_completely_blocked,
    wall_mostly_blocked,
)
from .infrastructure import InfrastructureValidator
from .obstacle import ObstacleValidator
from .registry import ValidatorRegistry
from .section import SectionDimensionValidator
from .woodworking import WoodworkingValidator

__all__ = [
    # Base classes
    "ValidationError",
    "ValidationWarning",
    "ValidationResult",
    # Registry
    "ValidatorRegistry",
    # Validators
    "WoodworkingValidator",
    "ObstacleValidator",
    "InfrastructureValidator",
    "SectionDimensionValidator",
    # Helpers
    "cutouts_overlap",
    "estimate_fill_section_width",
    "get_cutout_info",
    "get_panel_dimensions",
    "get_section_count",
    "wall_completely_blocked",
    "wall_mostly_blocked",
]
