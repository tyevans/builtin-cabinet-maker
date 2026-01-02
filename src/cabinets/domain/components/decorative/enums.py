"""Enums for decorative element components.

This module defines enumeration types used for decorative cabinet features:
- Arch types for curved openings
- Joinery types for face frame construction
- Edge profile types for router profiles
"""

from __future__ import annotations

from enum import Enum


class ArchType(str, Enum):
    """Types of arched openings.

    Defines the curve geometry for arched cabinet openings.

    Attributes:
        FULL_ROUND: Semicircular arch (180 degrees).
        SEGMENTAL: Partial arc, less than semicircle.
        ELLIPTICAL: Elliptical curve, wider than tall.
    """

    FULL_ROUND = "full_round"
    SEGMENTAL = "segmental"
    ELLIPTICAL = "elliptical"


class JoineryType(str, Enum):
    """Types of joinery for face frame construction.

    Defines how stiles and rails are joined together.

    Attributes:
        POCKET_SCREW: Angled screws through pocket holes.
        MORTISE_TENON: Traditional mortise and tenon joint.
        DOWEL: Dowel pin joints.
    """

    POCKET_SCREW = "pocket_screw"
    MORTISE_TENON = "mortise_tenon"
    DOWEL = "dowel"


class EdgeProfileType(str, Enum):
    """Types of edge profiles for visible panel edges.

    Defines router bit profiles applied to exposed edges.

    Attributes:
        CHAMFER: 45-degree flat cut on edge corner.
        ROUNDOVER: Rounded edge with specified radius.
        OGEE: S-curve decorative profile.
        BEVEL: Angled flat cut (similar to chamfer but full edge).
        COVE: Concave curved cut.
        ROMAN_OGEE: Classic decorative S-curve with fillet.
    """

    CHAMFER = "chamfer"
    ROUNDOVER = "roundover"
    OGEE = "ogee"
    BEVEL = "bevel"
    COVE = "cove"
    ROMAN_OGEE = "roman_ogee"
