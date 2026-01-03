"""Core geometry and material value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._panels import PanelType  # noqa: F401 - needed for runtime type resolution


class MaterialType(str, Enum):
    """Types of materials used in cabinet construction."""

    PLYWOOD = "plywood"
    MDF = "mdf"
    PARTICLE_BOARD = "particle_board"
    SOLID_WOOD = "solid_wood"


@dataclass(frozen=True)
class Dimensions:
    """Immutable dimensions in inches."""

    width: float
    height: float
    depth: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.depth <= 0:
            raise ValueError("All dimensions must be positive")

    @property
    def area(self) -> float:
        """Calculate surface area (width x height) in square inches."""
        return self.width * self.height

    @property
    def volume(self) -> float:
        """Calculate volume in cubic inches."""
        return self.width * self.height * self.depth


@dataclass(frozen=True)
class Position:
    """Position within the cabinet, from bottom-left corner."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("Position coordinates must be non-negative")


@dataclass(frozen=True)
class MaterialSpec:
    """Material specification for cabinet construction."""

    thickness: float
    material_type: MaterialType = MaterialType.PLYWOOD

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError("Material thickness must be positive")

    @classmethod
    def standard_3_4(cls) -> "MaterialSpec":
        """Standard 3/4 inch plywood."""
        return cls(thickness=0.75, material_type=MaterialType.PLYWOOD)

    @classmethod
    def standard_1_2(cls) -> "MaterialSpec":
        """Standard 1/2 inch plywood."""
        return cls(thickness=0.5, material_type=MaterialType.PLYWOOD)

    @classmethod
    def standard_1_4(cls) -> "MaterialSpec":
        """Standard 1/4 inch plywood (typically used for cabinet backs)."""
        return cls(thickness=0.25, material_type=MaterialType.PLYWOOD)


@dataclass(frozen=True)
class CutPiece:
    """A piece to be cut from sheet material."""

    width: float
    height: float
    quantity: int
    label: str
    panel_type: PanelType
    material: MaterialSpec
    cut_metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Cut piece dimensions must be positive")
        if self.quantity < 1:
            raise ValueError("Quantity must be at least 1")

    @property
    def area(self) -> float:
        """Total area for all pieces of this type in square inches."""
        return self.width * self.height * self.quantity


@dataclass(frozen=True)
class Point2D:
    """2D point in room coordinate space.

    Unlike Position (which is for cabinet-internal coordinates and must be
    non-negative), Point2D represents points in a room coordinate system
    where negative values are valid.
    """

    x: float
    y: float


@dataclass(frozen=True)
class Position3D:
    """3D position in space (origin at front-bottom-left of cabinet)."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0 or self.z < 0:
            raise ValueError("Position coordinates must be non-negative")


@dataclass(frozen=True)
class MountingPoint:
    """A single mounting point on the cabinet.

    Represents a specific location where the cabinet will be
    fastened to the wall, including stud alignment information
    and fastener specifications.

    Attributes:
        x_position: Distance from cabinet left edge in inches.
        y_position: Distance from cabinet bottom in inches.
        hits_stud: True if this mounting point aligns with a wall stud.
        fastener_type: Type of fastener (e.g., screw, lag_bolt, toggle_bolt, tapcon).
        fastener_spec: Specific fastener specification (e.g., "#10 x 3\" cabinet screw").
    """

    x_position: float
    y_position: float
    hits_stud: bool
    fastener_type: str
    fastener_spec: str

    def __post_init__(self) -> None:
        if self.x_position < 0:
            raise ValueError("x_position must be non-negative")
        if self.y_position < 0:
            raise ValueError("y_position must be non-negative")
        if not self.fastener_type:
            raise ValueError("fastener_type must not be empty")
        if not self.fastener_spec:
            raise ValueError("fastener_spec must not be empty")
