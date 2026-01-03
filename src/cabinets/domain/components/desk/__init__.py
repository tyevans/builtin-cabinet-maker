"""Desk components for built-in desk generation (FRD-18).

This module provides desk surface components including:
- Desktop panel generation with configurable dimensions
- Grommet cutouts for cable management
- Waterfall edge treatment support
- Edge banding calculation
- Floating desk mounting hardware
- L-shaped desk configuration for corner desks

The desk components are designed to integrate with the cabinet system
and follow the same component protocol patterns.
"""

from __future__ import annotations

# Configuration and constants
from .config import CornerConnectionType, GrommetSpec, LShapedDeskConfiguration
from .constants import (
    ADA_KNEE_CLEARANCE_WIDTH,
    GROMMET_SIZES,
    L_SHAPED_CORNER_POST_WIDTH,
    L_SHAPED_MIN_SURFACE_WIDTH,
    L_SHAPED_WARNING_THRESHOLD,
    MIN_KNEE_CLEARANCE_DEPTH,
    MIN_KNEE_CLEARANCE_HEIGHT,
    MIN_KNEE_CLEARANCE_WIDTH,
    SITTING_DESK_HEIGHT_DEFAULT,
    SITTING_DESK_HEIGHT_MAX,
    SITTING_DESK_HEIGHT_MIN,
    STANDING_DESK_HEIGHT_DEFAULT,
    STANDING_DESK_HEIGHT_MAX,
    STANDING_DESK_HEIGHT_MIN,
)

# Component classes - importing these triggers component registration
from .hutch import DeskHutchComponent
from .keyboard_tray import KeyboardTrayComponent
from .l_shaped import LShapedDeskComponent
from .monitor_shelf import MonitorShelfComponent
from .pedestal import DeskPedestalComponent
from .surface import DeskSurfaceComponent

__all__ = [
    # Constants
    "SITTING_DESK_HEIGHT_MIN",
    "SITTING_DESK_HEIGHT_MAX",
    "SITTING_DESK_HEIGHT_DEFAULT",
    "STANDING_DESK_HEIGHT_MIN",
    "STANDING_DESK_HEIGHT_MAX",
    "STANDING_DESK_HEIGHT_DEFAULT",
    "MIN_KNEE_CLEARANCE_WIDTH",
    "MIN_KNEE_CLEARANCE_HEIGHT",
    "MIN_KNEE_CLEARANCE_DEPTH",
    "ADA_KNEE_CLEARANCE_WIDTH",
    "GROMMET_SIZES",
    "L_SHAPED_CORNER_POST_WIDTH",
    "L_SHAPED_MIN_SURFACE_WIDTH",
    "L_SHAPED_WARNING_THRESHOLD",
    # Configuration
    "CornerConnectionType",
    "GrommetSpec",
    "LShapedDeskConfiguration",
    # Components
    "DeskSurfaceComponent",
    "DeskPedestalComponent",
    "KeyboardTrayComponent",
    "MonitorShelfComponent",
    "DeskHutchComponent",
    "LShapedDeskComponent",
]
