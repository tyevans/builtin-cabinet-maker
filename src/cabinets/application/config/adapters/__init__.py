"""Adapter modules for converting configuration to domain objects.

This package provides conversion functions that transform Pydantic-based
configuration models into domain-level objects used by the cabinet
generation system.

All public adapter functions are re-exported here for backward compatibility.
Users should import from this module or from the parent config package.

Example:
    >>> from cabinets.application.config.adapters import config_to_dtos
    >>> # Or equivalently:
    >>> from cabinets.application.config import config_to_dtos
"""

# DTO adapter functions
from cabinets.application.config.adapters.dto_adapter import (
    config_to_dtos,
    config_to_zone_configs,
)

# Section and row adapter functions
from cabinets.application.config.adapters.section_adapter import (
    config_to_all_section_specs,
    config_to_row_specs,
    config_to_section_specs,
    has_row_specs,
    has_section_specs,
)

# Room, geometry, and obstacle adapter functions
from cabinets.application.config.adapters.room_adapter import (
    config_to_ceiling_slope,
    config_to_clearance_defaults,
    config_to_obstacles,
    config_to_outside_corner,
    config_to_room,
    config_to_skylights,
)

# Safety adapter functions
from cabinets.application.config.adapters.safety_adapter import (
    config_to_safety,
)

# Installation adapter functions
from cabinets.application.config.adapters.installation_adapter import (
    config_to_installation,
)

# Woodworking adapter functions
from cabinets.application.config.adapters.woodworking_adapter import (
    config_to_bin_packing,
    config_to_hardware_settings,
    config_to_span_limits,
    config_to_woodworking,
)

# Zone and bay alcove adapter functions
from cabinets.application.config.adapters.zone_adapter import (
    config_to_bay_alcove,
    config_to_zone_layout,
)

# Re-export BayAlcoveConfig from domain for backward compatibility
from cabinets.domain.value_objects import BayAlcoveConfig

__all__ = [
    # Domain classes re-exported for backward compatibility
    "BayAlcoveConfig",
    # DTO functions
    "config_to_dtos",
    "config_to_zone_configs",
    # Section functions
    "config_to_all_section_specs",
    "config_to_row_specs",
    "config_to_section_specs",
    "has_row_specs",
    "has_section_specs",
    # Room functions
    "config_to_ceiling_slope",
    "config_to_clearance_defaults",
    "config_to_obstacles",
    "config_to_outside_corner",
    "config_to_room",
    "config_to_skylights",
    # Safety functions
    "config_to_safety",
    # Installation functions
    "config_to_installation",
    # Woodworking functions
    "config_to_bin_packing",
    "config_to_hardware_settings",
    "config_to_span_limits",
    "config_to_woodworking",
    # Zone functions
    "config_to_bay_alcove",
    "config_to_zone_layout",
]
