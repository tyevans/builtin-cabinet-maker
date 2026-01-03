"""Installation support value objects (FRD-17)."""

from __future__ import annotations

from enum import Enum


class WallType(str, Enum):
    """Wall construction type for installation planning.

    Defines the different wall types that affect fastener selection
    and mounting hardware recommendations.

    Attributes:
        DRYWALL: Standard drywall/gypsum board over wood studs.
        PLASTER: Traditional plaster over lath construction.
        CONCRETE: Solid poured concrete walls.
        CMU: Concrete masonry unit (cinder block) walls.
        BRICK: Solid or veneer brick walls.
    """

    DRYWALL = "drywall"
    PLASTER = "plaster"
    CONCRETE = "concrete"
    CMU = "cmu"
    BRICK = "brick"


class MountingSystem(str, Enum):
    """Cabinet mounting method.

    Defines the different mounting systems that can be used
    to secure cabinets to walls.

    Attributes:
        DIRECT_TO_STUD: Direct mounting through cabinet back into wall studs.
        FRENCH_CLEAT: 45-degree beveled cleat system for secure mounting.
        HANGING_RAIL: Metal rail system for cabinet suspension and adjustment.
        TOGGLE_BOLT: Heavy-duty toggle bolt anchors for non-stud locations.
    """

    DIRECT_TO_STUD = "direct_to_stud"
    FRENCH_CLEAT = "french_cleat"
    HANGING_RAIL = "hanging_rail"
    TOGGLE_BOLT = "toggle_bolt"


class LoadCategory(str, Enum):
    """Expected load category for capacity calculations.

    Defines the expected load per linear foot for cabinets,
    which affects mounting hardware requirements.

    Attributes:
        LIGHT: Light loads, approximately 15 lbs per linear foot.
        MEDIUM: Medium loads, approximately 30 lbs per linear foot.
        HEAVY: Heavy loads, approximately 50 lbs per linear foot.
    """

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
