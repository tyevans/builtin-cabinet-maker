"""Countertop and vertical zone value objects (FRD-22)."""

from __future__ import annotations

from enum import Enum


class ZoneType(str, Enum):
    """Types of vertical zones in cabinet configurations.

    Defines the different types of vertical zones that can be stacked
    to create multi-zone cabinet configurations like kitchen base/upper
    or mudroom bench/open shelving.

    Attributes:
        BASE: Floor-standing base cabinet zone.
        UPPER: Wall-mounted upper cabinet zone.
        GAP: Empty gap zone (for backsplash, mirror, hooks, etc.).
        BENCH: Bench/seat zone, typically lower height.
        OPEN: Open shelving zone without doors.
    """

    BASE = "base"
    UPPER = "upper"
    GAP = "gap"
    BENCH = "bench"
    OPEN = "open"


class ZoneMounting(str, Enum):
    """Mounting methods for cabinet zones.

    Defines how a zone is attached/supported in the overall configuration.

    Attributes:
        FLOOR: Zone rests on the floor (base cabinets, benches).
        WALL: Zone is mounted to the wall (upper cabinets).
        SUSPENDED: Zone is suspended from ceiling or structure.
        ON_BASE: Zone rests on top of a base zone (hutch uppers).
    """

    FLOOR = "floor"
    WALL = "wall"
    SUSPENDED = "suspended"
    ON_BASE = "on_base"


class GapPurpose(str, Enum):
    """Purpose designation for gap zones.

    Defines the intended use of a gap zone, which affects
    recommendations for wall treatment and accessories.

    Attributes:
        BACKSPLASH: Kitchen backsplash area (typically tile/stone).
        MIRROR: Bathroom mirror area.
        HOOKS: Coat hooks or hanging storage area.
        WORKSPACE: Workspace area between base and upper cabinets.
        DISPLAY: Display or decorative area.
    """

    BACKSPLASH = "backsplash"
    MIRROR = "mirror"
    HOOKS = "hooks"
    WORKSPACE = "workspace"
    DISPLAY = "display"


class ZonePreset(str, Enum):
    """Preset vertical zone configurations.

    Provides standard zone stack configurations for common use cases.
    Each preset defines a complete vertical arrangement of zones.

    Attributes:
        KITCHEN: Standard kitchen with base, countertop, backsplash, and uppers.
        MUDROOM: Mudroom with bench, hooks area, and open upper storage.
        VANITY: Bathroom vanity with base, counter, mirror area, and small uppers.
        HUTCH: Desk hutch with base desk, workspace gap, and upper storage.
        CUSTOM: User-defined custom zone configuration.
    """

    KITCHEN = "kitchen"
    MUDROOM = "mudroom"
    VANITY = "vanity"
    HUTCH = "hutch"
    CUSTOM = "custom"


class CountertopEdgeType(str, Enum):
    """Edge treatment types for countertops.

    Defines the different edge finishing options for countertop surfaces.
    Affects both aesthetics and cut list generation.

    Attributes:
        SQUARE: Standard square edge (most common, easiest to fabricate).
        EASED: Slightly rounded/softened edge (removes sharp corner).
        BULLNOSE: Fully rounded edge profile.
        BEVELED: Angled edge cut (typically 45 degrees).
        WATERFALL: Edge continues down as vertical panel.
    """

    SQUARE = "square"
    EASED = "eased"
    BULLNOSE = "bullnose"
    BEVELED = "beveled"
    WATERFALL = "waterfall"
