"""Woodworking constants for span limits, material properties, and hardware.

This module provides:
- Maximum unsupported shelf spans by material type and thickness
- Material modulus of elasticity values
- Safety factors and deflection limits
- Hardware specifications and spacing constants
"""

from __future__ import annotations

from cabinets.domain.value_objects import MaterialType


# Maximum unsupported shelf spans by material type and thickness
# Key: (MaterialType, thickness_in_inches)
# Value: maximum span in inches
SPAN_LIMITS: dict[tuple[MaterialType, float], float] = {
    (MaterialType.PLYWOOD, 0.75): 36.0,
    (MaterialType.MDF, 0.75): 24.0,
    (MaterialType.PARTICLE_BOARD, 0.75): 24.0,
    (MaterialType.SOLID_WOOD, 1.0): 42.0,
    # Additional common thicknesses
    (MaterialType.PLYWOOD, 0.5): 24.0,
    (MaterialType.PLYWOOD, 1.0): 42.0,
    (MaterialType.MDF, 0.5): 18.0,
    (MaterialType.SOLID_WOOD, 0.75): 36.0,
}


# Approximate modulus of elasticity (E) in PSI for weight capacity calculations
# These are conservative values for cabinet-grade materials
MATERIAL_MODULUS: dict[MaterialType, float] = {
    MaterialType.PLYWOOD: 1_200_000,  # Baltic birch typical
    MaterialType.MDF: 400_000,  # MDF typical
    MaterialType.PARTICLE_BOARD: 300_000,  # Particle board typical
    MaterialType.SOLID_WOOD: 1_400_000,  # Hardwood average
}

# Safety factor for capacity calculations (conservative)
# A factor of 4.0 means we divide max theoretical load by 4 for safe load rating
SAFETY_FACTOR: float = 4.0

# Maximum deflection ratio (span / max_deflection)
MAX_DEFLECTION_RATIO: float = 300  # L/300 is typical for shelving


# --- Hardware Constants (FR-05) ---

# Standard screw specifications
CASE_SCREW_SPEC = '#8 x 1-1/4" wood screw'
CASE_SCREW_SPACING = 8.0  # inches between screws

BACK_PANEL_SCREW_SPEC = '#6 x 5/8" pan head screw'
BACK_PANEL_SCREW_SPACING = 6.0  # inches between screws

POCKET_SCREW_SPEC = '#8 x 1-1/4" pocket screw'
POCKET_SCREW_COARSE_NOTE = "coarse thread for plywood"
POCKET_SCREW_FINE_NOTE = "fine thread for hardwood"

DOWEL_SPEC = '5/16" x 1-1/2" fluted dowel'

BISCUIT_SPEC_10 = "#10 biscuit"
BISCUIT_SPEC_20 = "#20 biscuit"


def get_max_span(material_type: MaterialType, thickness: float) -> float:
    """Get maximum span for a material, with fallback interpolation.

    Args:
        material_type: Type of material.
        thickness: Material thickness in inches.

    Returns:
        Maximum recommended span in inches.
    """
    # Exact match
    key = (material_type, thickness)
    if key in SPAN_LIMITS:
        return SPAN_LIMITS[key]

    # Find closest thickness for this material
    matching_entries = [
        (t, span) for (mt, t), span in SPAN_LIMITS.items() if mt == material_type
    ]
    if not matching_entries:
        # Default conservative value
        return 24.0

    # Find closest thickness
    closest = min(matching_entries, key=lambda x: abs(x[0] - thickness))
    return closest[1]
