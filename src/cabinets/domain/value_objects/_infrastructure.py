"""Infrastructure integration value objects (FRD-15)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ._core_geometry import Point2D
from ._panels import PanelType


class LightingType(str, Enum):
    """Types of cabinet lighting fixtures.

    Defines the different lighting options that can be integrated
    into cabinet infrastructure.

    Attributes:
        LED_STRIP: Linear LED strip lighting, typically for under-cabinet use.
        PUCK_LIGHT: Circular puck-style lights for focused illumination.
        ACCENT: Accent lighting for display or decorative purposes.
    """

    LED_STRIP = "led_strip"
    PUCK_LIGHT = "puck_light"
    ACCENT = "accent"


class LightingLocation(str, Enum):
    """Locations for cabinet lighting installation.

    Specifies where lighting can be mounted relative to the cabinet.

    Attributes:
        UNDER_CABINET: Mounted underneath the cabinet bottom panel.
        IN_CABINET: Mounted inside the cabinet for interior illumination.
        ABOVE_CABINET: Mounted above the cabinet for uplighting.
    """

    UNDER_CABINET = "under_cabinet"
    IN_CABINET = "in_cabinet"
    ABOVE_CABINET = "above_cabinet"


class OutletType(str, Enum):
    """Types of electrical outlets for cabinet integration.

    Defines the different outlet configurations that may require
    cutouts in cabinet panels.

    Attributes:
        SINGLE: Single electrical outlet.
        DOUBLE: Double (duplex) electrical outlet.
        GFI: Ground fault interrupter outlet (required near water sources).
    """

    SINGLE = "single"
    DOUBLE = "double"
    GFI = "gfi"


class GrommetSize(float, Enum):
    """Standard grommet sizes for cable management.

    Defines the standard diameters for cable pass-through grommets
    in inches.

    Attributes:
        SMALL: 2.0 inch diameter, for single cables.
        MEDIUM: 2.5 inch diameter, for multiple cables.
        LARGE: 3.0 inch diameter, for cable bundles.
    """

    SMALL = 2.0
    MEDIUM = 2.5
    LARGE = 3.0


class CutoutShape(str, Enum):
    """Shape of panel cutouts.

    Defines the geometric shape of cutouts in cabinet panels.

    Attributes:
        RECTANGULAR: Rectangular cutout (outlets, vents).
        CIRCULAR: Circular cutout (grommets, wire holes).
    """

    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"


class VentilationPattern(str, Enum):
    """Patterns for ventilation cutouts.

    Defines the different patterns that can be used for
    ventilation panels or cutouts.

    Attributes:
        GRID: Grid pattern of holes for maximum airflow.
        SLOT: Horizontal or vertical slots for directed airflow.
        CIRCULAR: Array of circular holes for aesthetic ventilation.
    """

    GRID = "grid"
    SLOT = "slot"
    CIRCULAR = "circular"


@dataclass(frozen=True)
class PanelCutout:
    """Specification for a cutout in a cabinet panel.

    Represents a hole or opening cut into a panel for infrastructure
    integration such as electrical outlets, cable grommets, wire routing
    holes, or ventilation.

    Attributes:
        cutout_type: Type of cutout (e.g., "outlet", "grommet", "wire_hole", "vent").
        panel: The panel type where this cutout is located.
        position: 2D position of the cutout center on the panel.
        width: Width of the cutout in inches (for rectangular cutouts).
        height: Height of the cutout in inches (for rectangular cutouts).
        shape: Shape of the cutout (rectangular or circular).
        notes: Optional notes or instructions for the cutout.
        diameter: Diameter in inches for circular cutouts (optional).
    """

    cutout_type: str
    panel: PanelType
    position: Point2D
    width: float
    height: float
    shape: CutoutShape = CutoutShape.RECTANGULAR
    notes: str = ""
    diameter: float | None = None

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Cutout width must be positive")
        if self.height <= 0:
            raise ValueError("Cutout height must be positive")
        if self.shape == CutoutShape.CIRCULAR and self.diameter is None:
            raise ValueError("Diameter is required for circular cutouts")
        if self.diameter is not None and self.diameter <= 0:
            raise ValueError("Diameter must be positive")

    @property
    def area(self) -> float:
        """Calculate the area of the cutout in square inches."""
        if self.shape == CutoutShape.CIRCULAR and self.diameter is not None:
            import math

            return math.pi * (self.diameter / 2) ** 2
        return self.width * self.height
