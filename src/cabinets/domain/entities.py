"""Domain entities for cabinet construction."""

import math
from dataclasses import dataclass, field
from typing import Any

from .value_objects import (
    Clearance,
    CutPiece,
    Dimensions,
    GeometryError,
    MaterialSpec,
    ObstacleType,
    ObstacleZone,
    PanelType,
    Point2D,
    Position,
    SectionType,
    WallPosition,
)


@dataclass
class Panel:
    """A single panel in the cabinet (side, top, bottom, shelf, etc.).

    Attributes:
        panel_type: The type/role of this panel in the cabinet.
        width: Width of the panel in inches.
        height: Height of the panel in inches.
        material: Material specification for this panel.
        position: Position within the cabinet coordinate system.
        metadata: Optional additional data about the panel (e.g., angle cuts,
            machining specs). Common keys include:
            - "is_angled": bool - Panel requires angle cuts
            - "angle": int/float - Angle of cuts in degrees
            - "shelf_index": int - Index of shelf for ordering
            - "shelf_shape": str - Shape descriptor for special shelves
        cut_metadata: Optional structured cut metadata for non-rectangular panels.
            Contains angle cuts, tapers, and notches for advanced cutting.
    """

    panel_type: PanelType
    width: float
    height: float
    material: MaterialSpec
    position: Position = field(default_factory=lambda: Position(0, 0))
    metadata: dict[str, Any] = field(default_factory=dict)
    cut_metadata: dict[str, Any] | None = None

    def to_cut_piece(self, quantity: int = 1) -> CutPiece:
        """Convert panel to a cut piece for the cut list."""
        return CutPiece(
            width=self.width,
            height=self.height,
            quantity=quantity,
            label=self.panel_type.value.replace("_", " ").title(),
            panel_type=self.panel_type,
            material=self.material,
            cut_metadata=self.cut_metadata,
        )


@dataclass
class Shelf:
    """A horizontal shelf within a section."""

    width: float
    depth: float
    material: MaterialSpec
    position: Position

    def to_panel(self) -> Panel:
        """Convert shelf to a panel for cut list generation."""
        return Panel(
            panel_type=PanelType.SHELF,
            width=self.width,
            height=self.depth,
            material=self.material,
            position=self.position,
        )


@dataclass
class Section:
    """A vertical section within a cabinet, containing shelves and other panels.

    Attributes:
        width: Width of the section in inches.
        height: Height of the section in inches.
        depth: Depth of the section in inches.
        position: Position of the section within the cabinet.
        shelves: List of shelves within this section.
        panels: List of additional panels (doors, drawer fronts, etc.).
        section_type: Type of section (open, doored, drawers, cubby).
                      Defaults to OPEN for backward compatibility.
    """

    width: float
    height: float
    depth: float
    position: Position
    shelves: list[Shelf] = field(default_factory=list)
    panels: list[Panel] = field(default_factory=list)
    section_type: SectionType = SectionType.OPEN

    def add_shelf(self, shelf: Shelf) -> None:
        """Add a shelf to this section."""
        self.shelves.append(shelf)

    def add_panel(self, panel: Panel) -> None:
        """Add a panel (door, drawer front, etc.) to this section."""
        self.panels.append(panel)


@dataclass
class Cabinet:
    """A complete cabinet with panels and sections.

    Attributes:
        width: Overall cabinet width in inches.
        height: Overall cabinet height in inches.
        depth: Overall cabinet depth in inches.
        material: Material specification for main panels.
        back_material: Material specification for back panel (defaults to 1/4" plywood).
        sections: List of sections within the cabinet.
        default_shelf_count: Default number of shelves for sections that don't specify.
                             When a section spec has shelves=0 and this is > 0, this value
                             is used instead. Defaults to 0 (no default shelves).
        row_heights: List of resolved row heights for multi-row cabinets.
                     Empty list means single-row cabinet (legacy behavior).
                     When populated, horizontal dividers are generated between rows.
        base_zone: Base/toe kick zone configuration (optional).
                   Dict with keys: height (float), setback (float), zone_type (str).
        crown_molding: Crown molding zone configuration (optional).
                       Dict with keys: height (float), setback (float), nailer_width (float).
        light_rail: Light rail zone configuration (optional).
                    Dict with keys: height (float), setback (float).
    """

    width: float
    height: float
    depth: float
    material: MaterialSpec
    back_material: MaterialSpec | None = None
    sections: list[Section] = field(default_factory=list)
    default_shelf_count: int = 0
    row_heights: list[float] = field(default_factory=list)
    base_zone: dict[str, Any] | None = None
    crown_molding: dict[str, Any] | None = None
    light_rail: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.back_material is None:
            self.back_material = MaterialSpec.standard_1_4()
        if self.default_shelf_count < 0:
            raise ValueError("default_shelf_count cannot be negative")

    @property
    def interior_width(self) -> float:
        """Width available inside the cabinet (minus side panels)."""
        return self.width - (2 * self.material.thickness)

    @property
    def interior_height(self) -> float:
        """Height available inside the cabinet (minus top and bottom)."""
        return self.height - (2 * self.material.thickness)

    @property
    def interior_depth(self) -> float:
        """Depth available inside (minus back panel)."""
        assert self.back_material is not None
        return self.depth - self.back_material.thickness

    def get_all_panels(self) -> list[Panel]:
        """Get all panels that make up this cabinet."""
        panels: list[Panel] = []

        # Top panel - spans full width, depth is interior depth
        panels.append(
            Panel(
                panel_type=PanelType.TOP,
                width=self.width,
                height=self.interior_depth,
                material=self.material,
                position=Position(0, self.height - self.material.thickness),
            )
        )

        # Bottom panel - shortened if there's a toe kick zone
        # With a toe kick, the bottom stops at the setback, leaving room for the toe kick panel
        bottom_depth = self.interior_depth
        if self.base_zone and self.base_zone.get("zone_type") == "toe_kick":
            toe_kick_setback = self.base_zone.get("setback", 3.0)
            bottom_depth = self.interior_depth - toe_kick_setback
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=self.width,
                height=bottom_depth,
                material=self.material,
                position=Position(0, 0),
            )
        )

        # Left side panel - full height, interior depth
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=self.interior_depth,
                height=self.interior_height,
                material=self.material,
                position=Position(0, self.material.thickness),
            )
        )

        # Right side panel - same as left
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=self.interior_depth,
                height=self.interior_height,
                material=self.material,
                position=Position(
                    self.width - self.material.thickness, self.material.thickness
                ),
            )
        )

        # Back panel - full width and height, thinner material
        assert self.back_material is not None
        panels.append(
            Panel(
                panel_type=PanelType.BACK,
                width=self.width,
                height=self.height,
                material=self.back_material,
                position=Position(0, 0),
            )
        )

        # Vertical dividers between sections (within each row)
        # For multi-row cabinets, dividers only span the row height, not full cabinet
        for i in range(len(self.sections) - 1):
            section = self.sections[i]
            next_section = self.sections[i + 1]
            # Only add divider if adjacent sections are in the same row
            # (they would have the same y position)
            if abs(section.position.y - next_section.position.y) < 0.001:
                panels.append(
                    Panel(
                        panel_type=PanelType.DIVIDER,
                        width=self.interior_depth,
                        height=section.height,  # Use section height, not interior_height
                        material=self.material,
                        position=Position(
                            section.position.x + section.width, section.position.y
                        ),
                    )
                )

        # Horizontal dividers between rows (for multi-row cabinets)
        if self.row_heights:
            current_y = self.material.thickness  # Start at top of bottom panel
            for i, row_height in enumerate(self.row_heights[:-1]):  # Skip last row
                current_y += row_height  # Move to top of current row
                panels.append(
                    Panel(
                        panel_type=PanelType.HORIZONTAL_DIVIDER,
                        width=self.interior_width,
                        height=self.interior_depth,
                        material=self.material,
                        position=Position(self.material.thickness, current_y),
                    )
                )
                current_y += self.material.thickness  # Account for divider thickness

        # Shelves from all sections
        for section in self.sections:
            for shelf in section.shelves:
                panels.append(shelf.to_panel())

        # Additional panels from sections (doors, drawer fronts, etc.)
        for section in self.sections:
            for panel in section.panels:
                panels.append(panel)

        # Zone panels (toe kick, crown nailer, light rail)
        panels.extend(self._get_zone_panels())

        return panels

    def _get_zone_panels(self) -> list[Panel]:
        """Generate panels for decorative zones (toe kick, crown, light rail)."""
        zone_panels: list[Panel] = []

        # Toe kick panel - recessed panel at bottom front
        if self.base_zone and self.base_zone.get("zone_type") == "toe_kick":
            toe_kick_height = self.base_zone.get("height", 3.5)
            toe_kick_setback = self.base_zone.get("setback", 3.0)
            # Toe kick is positioned at the front, recessed by setback
            zone_panels.append(
                Panel(
                    panel_type=PanelType.TOE_KICK,
                    width=self.width,
                    height=toe_kick_height,
                    material=self.material,
                    position=Position(0, 0),
                    metadata={
                        "zone_type": "toe_kick",
                        "setback": toe_kick_setback,
                        "location": "bottom_front_recessed",
                    },
                )
            )

        # Crown molding nailer - strip at top back for mounting crown molding
        if self.crown_molding:
            crown_height = self.crown_molding.get("height", 3.0)
            nailer_width = self.crown_molding.get("nailer_width", 2.0)
            zone_panels.append(
                Panel(
                    panel_type=PanelType.NAILER,
                    width=self.width,
                    height=nailer_width,  # Nailer depth
                    material=self.material,
                    position=Position(0, self.height - nailer_width),
                    metadata={
                        "zone_type": "crown_molding",
                        "zone_height": crown_height,
                        "setback": self.crown_molding.get("setback", 0.75),
                        "location": "top_back",
                    },
                )
            )

        # Light rail strip - at bottom front for concealing under-cabinet lights
        if self.light_rail:
            rail_height = self.light_rail.get("height", 1.5)
            zone_panels.append(
                Panel(
                    panel_type=PanelType.LIGHT_RAIL,
                    width=self.width,
                    height=rail_height,
                    material=self.material,
                    position=Position(0, 0),
                    metadata={
                        "zone_type": "light_rail",
                        "setback": self.light_rail.get("setback", 0.25),
                        "location": "bottom_front",
                    },
                )
            )

        return zone_panels

    def get_cut_list(self) -> list[CutPiece]:
        """Generate a consolidated cut list for this cabinet."""
        panels = self.get_all_panels()

        # Group identical panels together
        piece_key_to_panels: dict[tuple, list[Panel]] = {}
        for panel in panels:
            key = (
                panel.panel_type,
                round(panel.width, 3),
                round(panel.height, 3),
                panel.material.thickness,
                panel.material.material_type,
            )
            if key not in piece_key_to_panels:
                piece_key_to_panels[key] = []
            piece_key_to_panels[key].append(panel)

        # Convert to cut pieces with quantities
        cut_pieces: list[CutPiece] = []
        for panels_group in piece_key_to_panels.values():
            first_panel = panels_group[0]
            cut_pieces.append(first_panel.to_cut_piece(quantity=len(panels_group)))

        return cut_pieces


@dataclass(frozen=True)
class Wall:
    """Wall dimensions that constrain the cabinet."""

    width: float
    height: float
    depth: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.depth <= 0:
            raise ValueError("Wall dimensions must be positive")

    def to_dimensions(self) -> Dimensions:
        """Convert to Dimensions value object."""
        return Dimensions(width=self.width, height=self.height, depth=self.depth)


# Type alias for backward compatibility
WallConstraints = Wall


@dataclass
class WallSegment:
    """A wall segment in a room, with position relative to previous wall.

    Wall segments are used to define room geometry by connecting walls
    at specified angles. Each segment defines a wall's length, height,
    and the angle it makes from the previous wall's direction.

    Attributes:
        length: Length along the wall in inches.
        height: Wall height in inches.
        angle: Angle from previous wall direction in degrees.
               Must be -90 (left turn), 0 (straight), or 90 (right turn).
        name: Optional identifier for the wall segment.
        depth: Available depth for cabinets in inches.
    """

    length: float
    height: float
    angle: float = 0.0
    name: str | None = None
    depth: float = 12.0

    def __post_init__(self) -> None:
        """Validate wall segment dimensions and angle."""
        if self.length <= 0 or self.height <= 0:
            raise ValueError("Wall dimensions must be positive")
        if self.depth <= 0:
            raise ValueError("Depth must be positive")
        if not -135 <= self.angle <= 135:
            raise ValueError("Angle must be between -135 and 135 degrees")


@dataclass
class Room:
    """A room defined by connected wall segments.

    The Room aggregate manages the geometry of a room by connecting wall
    segments at specified angles. The first wall starts at origin (0, 0)
    and runs along the positive X axis. Subsequent walls connect at the
    end of the previous wall, with direction changes based on their angle.

    Attributes:
        name: Identifier for the room.
        walls: List of wall segments that define the room boundary.
        is_closed: Whether the room forms a closed polygon.
        closure_tolerance: Maximum gap allowed for room closure in inches.
    """

    name: str
    walls: list[WallSegment]
    is_closed: bool = False
    closure_tolerance: float = 0.1  # inches

    def __post_init__(self) -> None:
        """Validate room configuration."""
        if not self.walls:
            raise ValueError("Room must have at least one wall")
        if self.walls[0].angle != 0:
            raise ValueError("First wall must have angle=0")

    def get_wall_positions(self) -> list[WallPosition]:
        """Calculate global coordinates for each wall.

        First wall starts at origin (0, 0), runs along positive X.
        Subsequent walls start where previous wall ended,
        direction changes based on the wall's angle.

        The angle convention:
        - angle 0 = continue same direction
        - angle 90 = turn right (clockwise when viewed from above)
        - angle -90 = turn left (counter-clockwise)

        Returns:
            List of WallPosition objects with computed start/end coordinates.
        """
        positions: list[WallPosition] = []

        # Start at origin, facing along positive X axis (direction = 0 degrees)
        current_x = 0.0
        current_y = 0.0
        current_direction = 0.0  # degrees from positive X axis

        for i, wall in enumerate(self.walls):
            # Apply the wall's angle to change direction
            # Positive angle (90) = turn right = subtract from direction
            # Negative angle (-90) = turn left = add to direction (subtract negative)
            current_direction = (current_direction - wall.angle) % 360

            # Calculate end point using trigonometry
            # Convert direction to radians for math functions
            direction_rad = math.radians(current_direction)
            end_x = current_x + wall.length * math.cos(direction_rad)
            end_y = current_y + wall.length * math.sin(direction_rad)

            positions.append(
                WallPosition(
                    wall_index=i,
                    start=Point2D(x=current_x, y=current_y),
                    end=Point2D(x=end_x, y=end_y),
                    direction=current_direction,
                )
            )

            # Move to the end point for the next wall
            current_x = end_x
            current_y = end_y

        return positions

    def validate_geometry(self) -> list[GeometryError]:
        """Check for geometry errors (self-intersection, closure gaps).

        Validates the room geometry for:
        1. Self-intersection: Wall segments that cross each other
        2. Closure gap: If is_closed=True, checks if end point is near start point

        Returns:
            List of GeometryError objects describing any issues found.
        """
        errors: list[GeometryError] = []
        positions = self.get_wall_positions()

        # Check for self-intersection
        for i, pos_i in enumerate(positions):
            for j, pos_j in enumerate(positions):
                # Only check pairs where j > i + 1 to avoid adjacent walls
                # and avoid checking the same pair twice
                if j <= i + 1:
                    continue
                # Also skip if first and last wall when checking closed room
                # (they should meet, not intersect)
                if i == 0 and j == len(positions) - 1 and self.is_closed:
                    continue

                if self._segments_intersect(pos_i, pos_j):
                    errors.append(
                        GeometryError(
                            wall_indices=(i, j),
                            message=f"Wall {i} intersects with wall {j}",
                            error_type="intersection",
                        )
                    )

        # Check closure gap if room should be closed
        if self.is_closed and positions:
            start_point = positions[0].start
            end_point = positions[-1].end
            gap = math.sqrt(
                (end_point.x - start_point.x) ** 2
                + (end_point.y - start_point.y) ** 2
            )
            if gap > self.closure_tolerance:
                errors.append(
                    GeometryError(
                        wall_indices=(0, len(positions) - 1),
                        message=f"Room closure gap of {gap:.3f} inches exceeds tolerance of {self.closure_tolerance} inches",
                        error_type="closure",
                    )
                )

        return errors

    def _segments_intersect(self, pos_a: WallPosition, pos_b: WallPosition) -> bool:
        """Check if two wall segments intersect.

        Uses the cross product method to detect line segment intersection.
        Two segments intersect if and only if each segment straddles the line
        containing the other segment.

        Args:
            pos_a: First wall position.
            pos_b: Second wall position.

        Returns:
            True if the segments intersect (excluding endpoints).
        """
        # Extract coordinates
        ax1, ay1 = pos_a.start.x, pos_a.start.y
        ax2, ay2 = pos_a.end.x, pos_a.end.y
        bx1, by1 = pos_b.start.x, pos_b.start.y
        bx2, by2 = pos_b.end.x, pos_b.end.y

        # Calculate cross products to determine if points are on opposite sides
        def cross(ox: float, oy: float, ax: float, ay: float, bx: float, by: float) -> float:
            """Cross product of vectors (o->a) and (o->b)."""
            return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)

        # Check if segment b straddles the line containing segment a
        d1 = cross(ax1, ay1, ax2, ay2, bx1, by1)
        d2 = cross(ax1, ay1, ax2, ay2, bx2, by2)

        # Check if segment a straddles the line containing segment b
        d3 = cross(bx1, by1, bx2, by2, ax1, ay1)
        d4 = cross(bx1, by1, bx2, by2, ax2, ay2)

        # Segments intersect if each straddles the other's line
        # Use strict inequality to exclude endpoint touches
        if d1 * d2 < 0 and d3 * d4 < 0:
            return True

        return False

    @property
    def total_length(self) -> float:
        """Sum of all wall segment lengths.

        Returns:
            Total perimeter length in inches.
        """
        return sum(w.length for w in self.walls)

    @property
    def bounding_box(self) -> tuple[float, float]:
        """Calculate the bounding box of the room footprint.

        Returns:
            Tuple of (width, depth) representing the bounding box dimensions.
        """
        positions = self.get_wall_positions()

        if not positions:
            return (0.0, 0.0)

        # Collect all x and y coordinates from wall positions
        x_coords: list[float] = []
        y_coords: list[float] = []

        for pos in positions:
            x_coords.extend([pos.start.x, pos.end.x])
            y_coords.extend([pos.start.y, pos.end.y])

        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)

        width = max_x - min_x
        depth = max_y - min_y

        return (width, depth)


@dataclass
class Obstacle:
    """An obstacle on a wall that cabinets must avoid.

    Obstacles represent features on walls that cabinets cannot overlap with,
    such as windows, doors, outlets, switches, and vents. Each obstacle has
    a type, position, dimensions, and optional clearance requirements.

    Attributes:
        obstacle_type: The type of obstacle (window, door, outlet, etc.).
        wall_index: Index of the wall this obstacle is on (0-based).
        horizontal_offset: Horizontal distance from wall segment start in inches.
        bottom: Vertical distance from floor in inches.
        width: Width of the obstacle in inches.
        height: Height of the obstacle in inches.
        clearance_override: Optional custom clearance (overrides default for type).
        name: Optional identifier for the obstacle.
    """

    obstacle_type: ObstacleType
    wall_index: int
    horizontal_offset: float  # From wall segment start
    bottom: float  # From floor
    width: float
    height: float
    clearance_override: Clearance | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        """Validate obstacle dimensions and position."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Obstacle dimensions must be positive")
        if self.horizontal_offset < 0 or self.bottom < 0:
            raise ValueError("Obstacle position must be non-negative")
        if self.wall_index < 0:
            raise ValueError("Wall index must be non-negative")

    def get_clearance(self, defaults: dict[ObstacleType, Clearance]) -> Clearance:
        """Get effective clearance (override or default).

        Returns the custom clearance if one was specified, otherwise returns
        the default clearance for this obstacle type from the provided defaults.

        Args:
            defaults: Dictionary mapping obstacle types to default clearances.

        Returns:
            The effective clearance for this obstacle.
        """
        if self.clearance_override:
            return self.clearance_override
        return defaults.get(self.obstacle_type, Clearance())

    def get_zone_bounds(self, clearance: Clearance) -> ObstacleZone:
        """Get obstacle bounds including clearance.

        Calculates the total exclusion zone for this obstacle by adding
        the clearance distances to each side of the obstacle.

        Args:
            clearance: The clearance distances to apply.

        Returns:
            An ObstacleZone representing the total exclusion area.
        """
        return ObstacleZone(
            left=self.horizontal_offset - clearance.left,
            right=self.horizontal_offset + self.width + clearance.right,
            bottom=self.bottom - clearance.bottom,
            top=self.bottom + self.height + clearance.top,
            obstacle=self,
        )

    @property
    def top(self) -> float:
        """Top edge of the obstacle (bottom + height)."""
        return self.bottom + self.height

    @property
    def right(self) -> float:
        """Right edge of the obstacle (horizontal_offset + width)."""
        return self.horizontal_offset + self.width
