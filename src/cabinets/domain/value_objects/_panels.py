"""Panel types and cutting specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class PanelType(str, Enum):
    """Types of panels in a cabinet."""

    # Structural panels
    TOP = "top"
    BOTTOM = "bottom"
    LEFT_SIDE = "left_side"
    RIGHT_SIDE = "right_side"
    BACK = "back"
    SHELF = "shelf"
    DIVIDER = "divider"
    HORIZONTAL_DIVIDER = "horizontal_divider"
    DOOR = "door"
    DRAWER_FRONT = "drawer_front"
    DRAWER_SIDE = "drawer_side"
    DRAWER_BOX_FRONT = "drawer_box_front"
    DRAWER_BOTTOM = "drawer_bottom"
    DIAGONAL_FACE = "diagonal_face"
    FILLER = "filler"

    # Decorative panels (FRD-12)
    ARCH_HEADER = "arch_header"
    FACE_FRAME_RAIL = "face_frame_rail"
    FACE_FRAME_STILE = "face_frame_stile"
    LIGHT_RAIL = "light_rail"
    NAILER = "nailer"
    TOE_KICK = "toe_kick"
    VALANCE = "valance"

    # Desk panels (FRD-18)
    DESKTOP = "desktop"
    WATERFALL_EDGE = "waterfall_edge"
    KEYBOARD_TRAY = "keyboard_tray"
    KEYBOARD_ENCLOSURE = "keyboard_enclosure"
    MODESTY_PANEL = "modesty_panel"
    WIRE_CHASE = "wire_chase"

    # Cable routing (shared FRD-18/FRD-19)
    CABLE_CHASE = "cable_chase"

    # Countertop and zone panels (FRD-22)
    COUNTERTOP = "countertop"
    SUPPORT_BRACKET = "support_bracket"
    STEPPED_SIDE = "stepped_side"

    # Bay alcove panels (FRD-23)
    SEAT_SURFACE = "seat_surface"
    MULLION_FILLER = "mullion_filler"
    APEX_INFILL = "apex_infill"


class SectionType(str, Enum):
    """Types of cabinet sections.

    Defines the different types of cabinet sections that can be created,
    each with its own visual and functional characteristics.

    Attributes:
        OPEN: Open shelving without doors or drawers.
        DOORED: Section with cabinet doors.
        DRAWERS: Section containing drawers.
        CUBBY: Small open compartment, typically square.
    """

    OPEN = "open"
    DOORED = "doored"
    DRAWERS = "drawers"
    CUBBY = "cubby"


class GrainDirection(str, Enum):
    """Grain direction constraint for cut pieces.

    Controls whether a piece can be rotated during bin packing optimization.

    Attributes:
        NONE: No grain constraint, piece can rotate freely.
        LENGTH: Grain runs parallel to piece length (longest dimension).
        WIDTH: Grain runs parallel to piece width (shortest dimension).
    """

    NONE = "none"
    LENGTH = "length"
    WIDTH = "width"


class JointType(str, Enum):
    """Types of woodworking joints for panel connections.

    Defines the different joinery methods that can be used to connect
    cabinet panels. Each type has specific dimension calculations and
    hardware requirements.

    Attributes:
        DADO: Groove cut into one panel to receive another (shelf-to-side).
        RABBET: L-shaped cut along panel edge (back panel-to-case).
        POCKET_SCREW: Angled screw holes for face frame assembly.
        DOWEL: Cylindrical pins for alignment and strength.
        BISCUIT: Football-shaped spline for alignment.
        BUTT: Simple butt joint with mechanical fasteners.
    """

    DADO = "dado"
    RABBET = "rabbet"
    POCKET_SCREW = "pocket_screw"
    DOWEL = "dowel"
    BISCUIT = "biscuit"
    BUTT = "butt"


@dataclass(frozen=True)
class AngleCut:
    """Specification for angled cut on panel edge.

    Represents a non-perpendicular cut on one edge of a panel,
    used for corner cabinets or sloped ceiling conditions.

    Attributes:
        edge: Which edge of the panel has the angled cut.
        angle: Degrees from perpendicular (0-90).
        bevel: True for beveled edge (angled through thickness),
               False for straight cut (angled in plane).
    """

    edge: Literal["left", "right", "top", "bottom"]
    angle: float
    bevel: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.angle <= 90:
            raise ValueError("Cut angle must be between 0 and 90 degrees")


@dataclass(frozen=True)
class TaperSpec:
    """Specification for tapered panel (sloped ceiling).

    Represents a panel that tapers from one height to another,
    typically used for side panels under sloped ceilings.

    Attributes:
        start_height: Height at the start of the taper in inches.
        end_height: Height at the end of the taper in inches.
        direction: Direction of the taper along the panel.
    """

    start_height: float
    end_height: float
    direction: Literal["left_to_right", "right_to_left"]

    def __post_init__(self) -> None:
        if self.start_height <= 0 or self.end_height <= 0:
            raise ValueError("Heights must be positive")


@dataclass(frozen=True)
class NotchSpec:
    """Specification for notched panel (skylight void).

    Represents a rectangular notch cut from a panel edge,
    typically used to accommodate skylight projections or other obstructions.

    Attributes:
        x_offset: Distance from left edge of panel to notch start in inches.
        width: Width of the notch in inches.
        depth: Depth of notch from the edge in inches.
        edge: Which edge of the panel the notch is cut from.
    """

    x_offset: float
    width: float
    depth: float
    edge: Literal["top", "bottom", "left", "right"]

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Notch width must be positive")
        if self.depth <= 0:
            raise ValueError("Notch depth must be positive")
        if self.x_offset < 0:
            raise ValueError("Notch x_offset cannot be negative")


@dataclass(frozen=True)
class PanelCutMetadata:
    """Extended cut metadata for non-rectangular panels.

    Aggregates all special cutting instructions for a panel that
    is not a simple rectangle. Used to communicate cutting requirements
    to the cut list and manufacturing systems.

    Attributes:
        angle_cuts: Tuple of angle cuts to apply to panel edges.
        taper: Optional taper specification for tapered panels.
        notches: Tuple of notch specifications for notched panels.
    """

    angle_cuts: tuple[AngleCut, ...] = field(default_factory=tuple)
    taper: TaperSpec | None = None
    notches: tuple[NotchSpec, ...] = field(default_factory=tuple)
