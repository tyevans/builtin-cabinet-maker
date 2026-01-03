"""3D geometry and visualization value objects."""

from __future__ import annotations

from dataclasses import dataclass
from math import radians, tan
from typing import Literal

from ._core_geometry import Position3D


@dataclass(frozen=True)
class BoundingBox3D:
    """Axis-aligned 3D bounding box representing a panel in space."""

    origin: Position3D
    size_x: float  # Width (left to right)
    size_y: float  # Depth (front to back)
    size_z: float  # Height (bottom to top)

    def __post_init__(self) -> None:
        if self.size_x <= 0 or self.size_y <= 0 or self.size_z <= 0:
            raise ValueError("Bounding box dimensions must be positive")

    def get_vertices(self) -> list[tuple[float, float, float]]:
        """Return 8 corner vertices of the box."""
        x0, y0, z0 = self.origin.x, self.origin.y, self.origin.z
        x1, y1, z1 = x0 + self.size_x, y0 + self.size_y, z0 + self.size_z
        return [
            (x0, y0, z0),  # 0: front-bottom-left
            (x1, y0, z0),  # 1: front-bottom-right
            (x1, y1, z0),  # 2: back-bottom-right
            (x0, y1, z0),  # 3: back-bottom-left
            (x0, y0, z1),  # 4: front-top-left
            (x1, y0, z1),  # 5: front-top-right
            (x1, y1, z1),  # 6: back-top-right
            (x0, y1, z1),  # 7: back-top-left
        ]

    def get_triangles(self) -> list[tuple[int, int, int]]:
        """Return 12 triangles (as vertex indices) forming the 6 box faces.

        Winding order is clockwise when viewed from outside in domain Z-up coords.
        This becomes counter-clockwise (correct outward normals) after the Y/Z swap
        transform applied in STL export: (x, y, z) -> (x, z, y).
        """
        return [
            # Bottom face (z=min) -> becomes front face after Y/Z swap
            (0, 1, 2),
            (0, 2, 3),
            # Top face (z=max) -> becomes back face after Y/Z swap
            (4, 6, 5),
            (4, 7, 6),
            # Front face (y=min) -> becomes bottom face after Y/Z swap
            (0, 5, 1),
            (0, 4, 5),
            # Back face (y=max) -> becomes top face after Y/Z swap
            (2, 7, 3),
            (2, 6, 7),
            # Left face (x=min)
            (0, 7, 4),
            (0, 3, 7),
            # Right face (x=max)
            (1, 6, 2),
            (1, 5, 6),
        ]


@dataclass(frozen=True)
class CeilingSlope:
    """Ceiling slope definition.

    Represents a sloped ceiling that affects cabinet height along a wall.
    Used for attic spaces, vaulted ceilings, or other non-flat ceiling conditions.

    Attributes:
        angle: Degrees from horizontal (0-60). Higher values mean steeper slopes.
        start_height: Height at slope start in inches.
        direction: Direction of slope - which way the ceiling descends.
        min_height: Minimum usable height in inches (default 24.0).
    """

    angle: float
    start_height: float
    direction: Literal["left_to_right", "right_to_left", "front_to_back"]
    min_height: float = 24.0

    def __post_init__(self) -> None:
        if not 0 <= self.angle <= 60:
            raise ValueError("Slope angle must be between 0 and 60 degrees")
        if self.start_height <= 0:
            raise ValueError("Start height must be positive")
        if self.min_height < 0:
            raise ValueError("Minimum height cannot be negative")

    def height_at_position(self, position: float) -> float:
        """Calculate ceiling height at given position along slope.

        Args:
            position: Distance along the slope direction in inches.

        Returns:
            Ceiling height at that position in inches.
        """
        return self.start_height - (position * tan(radians(self.angle)))


@dataclass(frozen=True)
class Skylight:
    """Skylight definition with projection into cabinet space.

    Represents a skylight that may project down into the cabinet area,
    creating a void that panels must avoid.

    Attributes:
        x_position: Position along wall in inches (from left edge).
        width: Skylight width in inches.
        projection_depth: How far the skylight projects down in inches.
        projection_angle: Angle from ceiling in degrees (90 = vertical projection).
    """

    x_position: float
    width: float
    projection_depth: float
    projection_angle: float = 90.0

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Skylight width must be positive")
        if self.projection_depth <= 0:
            raise ValueError("Projection depth must be positive")
        if not 0 < self.projection_angle <= 180:
            raise ValueError("Projection angle must be between 0 and 180 degrees")

    def void_at_depth(self, cabinet_depth: float) -> tuple[float, float]:
        """Calculate void dimensions at cabinet top level.

        For angled projections, the void expands as it projects down.
        This method calculates the void dimensions at the cabinet's depth.

        Args:
            cabinet_depth: Depth of the cabinet in inches.

        Returns:
            Tuple of (void_start_x, void_width) at cabinet depth.
        """
        if self.projection_angle == 90:
            return (self.x_position, self.width)
        # Angled projection expands the void
        expansion = cabinet_depth * tan(radians(90 - self.projection_angle))
        return (self.x_position - expansion / 2, self.width + expansion)


@dataclass(frozen=True)
class OutsideCornerConfig:
    """Configuration for outside (convex) corner treatment.

    Outside corners occur when cabinet runs wrap around a projecting wall
    or column. This configuration specifies how to handle the corner transition.

    Attributes:
        treatment: Type of corner treatment to apply.
            - "angled_face": 45-degree angled face panel
            - "butted_filler": Filler strip between perpendicular runs
            - "wrap_around": Continuous face around corner
        filler_width: Width of filler strip for butted_filler treatment (inches).
        face_angle: Angle of face panel for angled_face treatment (degrees).
    """

    treatment: Literal["angled_face", "butted_filler", "wrap_around"] = "angled_face"
    filler_width: float = 3.0
    face_angle: float = 45.0

    def __post_init__(self) -> None:
        if self.filler_width <= 0:
            raise ValueError("Filler width must be positive")
        if not 0 < self.face_angle < 90:
            raise ValueError("Face angle must be between 0 and 90 degrees")
