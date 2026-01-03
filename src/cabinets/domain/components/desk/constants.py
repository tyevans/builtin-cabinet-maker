"""Ergonomic constants for desk components (FRD-18)."""

from __future__ import annotations

from ...value_objects import GrommetSize

# --- Ergonomic Constants ---

SITTING_DESK_HEIGHT_MIN = 28.0
SITTING_DESK_HEIGHT_MAX = 32.0
SITTING_DESK_HEIGHT_DEFAULT = 30.0
STANDING_DESK_HEIGHT_MIN = 38.0
STANDING_DESK_HEIGHT_MAX = 48.0
STANDING_DESK_HEIGHT_DEFAULT = 42.0
MIN_KNEE_CLEARANCE_WIDTH = 24.0
MIN_KNEE_CLEARANCE_HEIGHT = 24.0
MIN_KNEE_CLEARANCE_DEPTH = 15.0
ADA_KNEE_CLEARANCE_WIDTH = 30.0

# Standard grommet sizes (reuse GrommetSize enum values)
GROMMET_SIZES = [
    GrommetSize.SMALL.value,
    GrommetSize.MEDIUM.value,
    GrommetSize.LARGE.value,
]

# L-shaped desk constants
L_SHAPED_CORNER_POST_WIDTH = 3.0  # 3" square corner support post
L_SHAPED_MIN_SURFACE_WIDTH = 36.0  # Minimum surface width for practical use
L_SHAPED_WARNING_THRESHOLD = 60.0  # Warn if > 60" without corner support
