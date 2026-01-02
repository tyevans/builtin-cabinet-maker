"""Safety constants and disclaimers for cabinet compliance analysis.

This module contains all threshold values, clearance requirements,
and legal disclaimers used throughout the safety analysis system.
"""

from __future__ import annotations

# ==============================================================================
# Anti-Tip Constants
# ==============================================================================

# Anti-tip threshold (ASTM F2057-23 references 27" for clothing storage units)
ANTI_TIP_HEIGHT_THRESHOLD: float = 27.0


# ==============================================================================
# ADA Accessibility Constants
# ==============================================================================

# ADA reach ranges (inches) - 2010 ADA Standards
ADA_MIN_REACH: float = 15.0
ADA_MAX_REACH_UNOBSTRUCTED: float = 48.0
ADA_MAX_REACH_OBSTRUCTED: float = 44.0
ADA_MAX_OBSTRUCTION_DEPTH: float = 24.0
ADA_MIN_ACCESSIBLE_PERCENTAGE: float = 50.0

# ADA knee clearance (inches)
ADA_KNEE_CLEARANCE_HEIGHT: float = 27.0
ADA_KNEE_CLEARANCE_WIDTH: float = 30.0
ADA_KNEE_CLEARANCE_DEPTH: float = 19.0


# ==============================================================================
# Building Code Clearances
# ==============================================================================

# NEC electrical panel clearances (inches) - NEC Article 110.26
NEC_PANEL_FRONT_CLEARANCE: float = 36.0
NEC_PANEL_WIDTH_CLEARANCE: float = 30.0
NEC_PANEL_HEIGHT_CLEARANCE: float = 78.0

# Heat source clearances (inches)
HEAT_SOURCE_VERTICAL_CLEARANCE: float = 30.0
HEAT_SOURCE_HORIZONTAL_CLEARANCE: float = 15.0

# Egress clearance warning zone (inches)
EGRESS_ADJACENT_WARNING: float = 18.0

# Closet lighting clearances (NEC 410.16)
CLOSET_LIGHT_INCANDESCENT_CLEARANCE: float = 12.0
CLOSET_LIGHT_RECESSED_CLEARANCE: float = 6.0
CLOSET_LIGHT_CFL_CLEARANCE: float = 6.0


# ==============================================================================
# Structural Safety Constants
# ==============================================================================

# KCMA standard shelf load (lbs per square foot)
KCMA_SHELF_LOAD_PSF: float = 15.0


# ==============================================================================
# Child Safety Constants
# ==============================================================================

# Child entrapment volume threshold (1.5 cubic feet in cubic inches)
CHILD_ENTRAPMENT_VOLUME_THRESHOLD: float = 2592.0


# ==============================================================================
# Seismic Constants
# ==============================================================================

# Seismic zones requiring enhanced anchoring
HIGH_SEISMIC_ZONES: frozenset[str] = frozenset({"D", "E", "F"})


# ==============================================================================
# Safety Disclaimers
# ==============================================================================

WEIGHT_CAPACITY_DISCLAIMER: str = (
    "Estimate only. Actual capacity depends on material quality, "
    "installation, and loading distribution."
)

SAFETY_GENERAL_DISCLAIMER: str = (
    "Safety estimates are advisory only and do not constitute professional "
    "structural engineering. For critical installations, consult a licensed "
    "contractor or structural engineer."
)

ADA_DISCLAIMER: str = (
    "Accessibility analysis is based on general ADA guidelines. Specific "
    "requirements may vary by jurisdiction and building type."
)

MATERIAL_DISCLAIMER: str = (
    "Material certifications cannot be verified by this software. "
    "Always obtain documentation from material suppliers."
)


__all__ = [
    # Anti-tip
    "ANTI_TIP_HEIGHT_THRESHOLD",
    # ADA
    "ADA_MIN_REACH",
    "ADA_MAX_REACH_UNOBSTRUCTED",
    "ADA_MAX_REACH_OBSTRUCTED",
    "ADA_MAX_OBSTRUCTION_DEPTH",
    "ADA_MIN_ACCESSIBLE_PERCENTAGE",
    "ADA_KNEE_CLEARANCE_HEIGHT",
    "ADA_KNEE_CLEARANCE_WIDTH",
    "ADA_KNEE_CLEARANCE_DEPTH",
    # Building codes
    "NEC_PANEL_FRONT_CLEARANCE",
    "NEC_PANEL_WIDTH_CLEARANCE",
    "NEC_PANEL_HEIGHT_CLEARANCE",
    "HEAT_SOURCE_VERTICAL_CLEARANCE",
    "HEAT_SOURCE_HORIZONTAL_CLEARANCE",
    "EGRESS_ADJACENT_WARNING",
    "CLOSET_LIGHT_INCANDESCENT_CLEARANCE",
    "CLOSET_LIGHT_RECESSED_CLEARANCE",
    "CLOSET_LIGHT_CFL_CLEARANCE",
    # Structural
    "KCMA_SHELF_LOAD_PSF",
    # Child safety
    "CHILD_ENTRAPMENT_VOLUME_THRESHOLD",
    # Seismic
    "HIGH_SEISMIC_ZONES",
    # Disclaimers
    "WEIGHT_CAPACITY_DISCLAIMER",
    "SAFETY_GENERAL_DISCLAIMER",
    "ADA_DISCLAIMER",
    "MATERIAL_DISCLAIMER",
]
