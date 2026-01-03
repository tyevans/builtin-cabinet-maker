"""Entertainment center value objects (FRD-19)."""

from __future__ import annotations

from enum import Enum


class EquipmentType(str, Enum):
    """Types of media equipment with standard dimensions.

    Defines the common media equipment types that can be accommodated
    in entertainment center sections. Each type has default dimensions
    and heat generation characteristics.

    Attributes:
        RECEIVER: A/V receiver (17.5"W x 7"H x 18"D, generates heat).
        CONSOLE_HORIZONTAL: Gaming console in horizontal position (generates heat).
        CONSOLE_VERTICAL: Gaming console in vertical position (generates heat).
        STREAMING: Small streaming device (Apple TV, Roku, etc.).
        CABLE_BOX: Cable or satellite box (generates heat).
        BLU_RAY: Blu-ray or DVD player.
        TURNTABLE: Record turntable.
        CUSTOM: User-specified custom equipment dimensions.
    """

    RECEIVER = "receiver"
    CONSOLE_HORIZONTAL = "console_horizontal"
    CONSOLE_VERTICAL = "console_vertical"
    STREAMING = "streaming"
    CABLE_BOX = "cable_box"
    BLU_RAY = "blu_ray"
    TURNTABLE = "turntable"
    CUSTOM = "custom"


class SoundbarType(str, Enum):
    """Soundbar size categories.

    Defines the standard soundbar sizes for entertainment center
    integration. Soundbars require open shelves (not enclosed)
    for proper sound projection.

    Attributes:
        COMPACT: Small soundbar, approximately 24" width.
        STANDARD: Medium soundbar, approximately 36" width.
        PREMIUM: Large soundbar, 48"+ width.
        CUSTOM: User-specified custom soundbar dimensions.
    """

    COMPACT = "compact"
    STANDARD = "standard"
    PREMIUM = "premium"
    CUSTOM = "custom"


class SpeakerType(str, Enum):
    """Types of speakers for built-in alcoves.

    Defines the common speaker types that can be accommodated
    in entertainment center alcoves. Each type has different
    dimensional and acoustic requirements.

    Attributes:
        CENTER_CHANNEL: Horizontal center channel speaker (ear level placement).
        BOOKSHELF: Standard bookshelf speaker (vertical orientation).
        SUBWOOFER: Subwoofer with port clearance requirements.
    """

    CENTER_CHANNEL = "center_channel"
    BOOKSHELF = "bookshelf"
    SUBWOOFER = "subwoofer"
