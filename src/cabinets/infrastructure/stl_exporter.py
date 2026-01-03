"""STL export functionality using numpy-stl."""

import hashlib
import math
import random
from pathlib import Path

import numpy as np
from stl import mesh

from cabinets.contracts.dtos import RoomLayoutOutput
from cabinets.domain import BoundingBox3D, Cabinet, Panel, Panel3DMapper, PanelType
from cabinets.domain.services import RoomPanel3DMapper, ZoneStackLayoutResult
from cabinets.domain.value_objects import Position3D


def _random_ajar_angle(
    box: BoundingBox3D, min_angle: float = 30.0, max_angle: float = 60.0
) -> float:
    """Generate a deterministic 'random' ajar angle based on door position.

    Uses the door's position as a seed so the same door always gets the same
    angle, making output reproducible while varying angles between doors.

    Args:
        box: The door's bounding box (position used as seed).
        min_angle: Minimum angle in degrees.
        max_angle: Maximum angle in degrees.

    Returns:
        A 'random' angle between min_angle and max_angle.
    """
    # Create a seed from the door's position
    seed_str = f"{box.origin.x:.2f},{box.origin.y:.2f},{box.origin.z:.2f}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.uniform(min_angle, max_angle)


class StlMeshBuilder:
    """Builds STL meshes from 3D bounding boxes.

    Single Responsibility: Handles low-level mesh creation from geometry primitives.

    Coordinate System Transformation:
    The domain uses Z-up coordinates (X=width, Y=depth, Z=height), which is
    common in engineering/CAD. However, many STL viewers use Y-up coordinates.
    This builder transforms coordinates to Y-up for better viewer compatibility:
    - x' = x (width unchanged)
    - y' = z (domain height becomes viewer vertical)
    - z' = y (domain depth becomes viewer depth)
    """

    def build_box_mesh(self, box: BoundingBox3D) -> mesh.Mesh:
        """Create an STL mesh for a single bounding box.

        Transforms from Z-up (domain) to Y-up (STL viewer) coordinates.

        Args:
            box: The 3D bounding box to convert to a mesh.

        Returns:
            A numpy-stl Mesh object representing the box.
        """
        # Get vertices in domain coordinates (Z-up)
        domain_vertices = box.get_vertices()

        # Transform to Y-up: (x, y, z) -> (x, z, y)
        # This makes height (Z) become the vertical axis (Y) in viewers
        vertices = np.array([(x, z, y) for x, y, z in domain_vertices])
        triangles = box.get_triangles()

        # Create mesh with 12 triangles (2 per face, 6 faces)
        box_mesh = mesh.Mesh(np.zeros(12, dtype=mesh.Mesh.dtype))

        for i, (v0, v1, v2) in enumerate(triangles):
            box_mesh.vectors[i] = [vertices[v0], vertices[v1], vertices[v2]]

        return box_mesh

    def build_box_mesh_with_transform(
        self,
        box: BoundingBox3D,
        wall_rotation: float = 0.0,
        wall_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> mesh.Mesh:
        """Create an STL mesh for a bounding box with wall transform applied.

        Args:
            box: The 3D bounding box in local coordinates.
            wall_rotation: Rotation around Z axis in degrees.
            wall_position: Translation (x, y, z) after rotation.

        Returns:
            A numpy-stl Mesh object representing the transformed box.
        """
        # Get vertices in local coordinates
        x0 = box.origin.x
        y0 = box.origin.y
        z0 = box.origin.z
        vertices_local = [
            (x0, y0, z0),
            (x0 + box.size_x, y0, z0),
            (x0 + box.size_x, y0 + box.size_y, z0),
            (x0, y0 + box.size_y, z0),
            (x0, y0, z0 + box.size_z),
            (x0 + box.size_x, y0, z0 + box.size_z),
            (x0 + box.size_x, y0 + box.size_y, z0 + box.size_z),
            (x0, y0 + box.size_y, z0 + box.size_z),
        ]

        # Apply wall rotation and translation
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        room_vertices = []
        for vx, vy, vz in vertices_local:
            rx = vx * cos_w - vy * sin_w
            ry = vx * sin_w + vy * cos_w
            room_vertices.append((rx + tx, ry + ty, vz + tz))

        # Transform to Y-up: (x, y, z) -> (x, z, y)
        vertices = np.array([(x, z, y) for x, y, z in room_vertices])

        triangles = box.get_triangles()
        box_mesh = mesh.Mesh(np.zeros(12, dtype=mesh.Mesh.dtype))
        for i, (v0, v1, v2) in enumerate(triangles):
            box_mesh.vectors[i] = [vertices[v0], vertices[v1], vertices[v2]]

        return box_mesh

    def build_ajar_door_mesh(
        self,
        box: BoundingBox3D,
        ajar_angle: float = 45.0,
        hinge_side: str = "left",
        wall_rotation: float = 0.0,
        wall_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> mesh.Mesh:
        """Create an STL mesh for a door panel rotated to appear ajar.

        The door is rotated around its hinge edge (left or right) by the
        specified angle. This makes doors visually distinguishable from
        solid panels in the STL output.

        Args:
            box: The 3D bounding box representing the closed door position.
            ajar_angle: Rotation angle in degrees (default 15°).
            hinge_side: Which edge has the hinge - "left" or "right".

        Returns:
            A numpy-stl Mesh object representing the ajar door.

        Raises:
            ValueError: If hinge_side is not "left" or "right".
        """
        # Validate hinge_side
        if hinge_side not in ("left", "right"):
            raise ValueError(
                f"hinge_side must be 'left' or 'right', got '{hinge_side}'"
            )

        # Get base vertices in domain coordinates (Z-up)
        # Door box: origin is at bottom-left-front of door
        x0, y0, z0 = box.origin.x, box.origin.y, box.origin.z
        width = box.size_x
        depth = box.size_y  # Door thickness
        height = box.size_z

        # Convert angle to radians (positive to open outward/forward)
        # For right-hinged doors, negate the angle so both doors swing forward
        angle_rad = math.radians(ajar_angle)
        if hinge_side == "right":
            angle_rad = -angle_rad
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Generate 8 vertices of the door
        # We rotate around the Z axis at the hinge edge
        if hinge_side == "left":
            # Hinge is on left edge (x = x0), rotate around that axis
            # Points at x0 stay fixed, points at x0+width swing outward
            hinge_x = x0
            vertices = []
            for dx, dy, dz in [
                (0, 0, 0),
                (width, 0, 0),
                (width, depth, 0),
                (0, depth, 0),
                (0, 0, height),
                (width, 0, height),
                (width, depth, height),
                (0, depth, height),
            ]:
                # Rotate (dx, dy) around origin (the hinge at x=0, y=y0)
                # Then translate by (x0, y0, z0)
                if dx == 0:
                    # Hinge edge - no rotation
                    vx = x0
                    vy = y0 + dy
                else:
                    # Free edge - rotate around hinge
                    # Rotation in XY plane around the hinge point
                    rx = dx * cos_a - dy * sin_a
                    ry = dx * sin_a + dy * cos_a
                    vx = x0 + rx
                    vy = y0 + ry
                vz = z0 + dz
                vertices.append((vx, vy, vz))
        else:
            # Hinge is on right edge (x = x0 + width), rotate around that axis
            hinge_x = x0 + width
            vertices = []
            for dx, dy, dz in [
                (0, 0, 0),
                (width, 0, 0),
                (width, depth, 0),
                (0, depth, 0),
                (0, 0, height),
                (width, 0, height),
                (width, depth, height),
                (0, depth, height),
            ]:
                if dx == width:
                    # Hinge edge - no rotation
                    vx = x0 + width
                    vy = y0 + dy
                else:
                    # Free edge - rotate around hinge (which is at dx=width)
                    # Distance from hinge: -(width - dx) = dx - width
                    dist_from_hinge = dx - width
                    rx = dist_from_hinge * cos_a - dy * sin_a
                    ry = dist_from_hinge * sin_a + dy * cos_a
                    vx = hinge_x + rx
                    vy = y0 + ry
                vz = z0 + dz
                vertices.append((vx, vy, vz))

        # Apply wall rotation and translation to get room coordinates
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        room_vertices = []
        for vx, vy, vz in vertices:
            # Rotate around Z axis
            rx = vx * cos_w - vy * sin_w
            ry = vx * sin_w + vy * cos_w
            # Translate
            room_vertices.append((rx + tx, ry + ty, vz + tz))

        # Transform to Y-up: (x, y, z) -> (x, z, y)
        transformed_vertices = np.array([(x, z, y) for x, y, z in room_vertices])

        # Same triangle indices as axis-aligned box
        triangles = box.get_triangles()

        # Create mesh with 12 triangles
        door_mesh = mesh.Mesh(np.zeros(12, dtype=mesh.Mesh.dtype))
        for i, (v0, v1, v2) in enumerate(triangles):
            door_mesh.vectors[i] = [
                transformed_vertices[v0],
                transformed_vertices[v1],
                transformed_vertices[v2],
            ]

        return door_mesh

    def build_pulled_out_drawer_mesh(
        self,
        box: BoundingBox3D,
        drawer_index: int,
        drawer_count: int,
        base_pull_out: float = 2.0,
        max_pull_out: float = 8.0,
        wall_rotation: float = 0.0,
        wall_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> mesh.Mesh:
        """Create an STL mesh for a drawer panel pulled out from the cabinet.

        Drawers are rendered pulled out by ascending amounts from top to bottom
        (bottom drawer most pulled out). A small random variation is added based
        on the drawer's position hash to make adjacent horizontal drawers appear
        slightly different.

        Args:
            box: The 3D bounding box representing the closed drawer position.
            drawer_index: Index of this drawer in the stack (0 = bottom).
            drawer_count: Total number of drawers in the stack.
            base_pull_out: Minimum pull-out distance in inches (default 2").
            max_pull_out: Maximum pull-out distance in inches (default 8").

        Returns:
            A numpy-stl Mesh object representing the pulled-out drawer.
        """
        # Calculate the base pull-out for this drawer based on position in stack
        # drawer_index 0 = bottom (most pulled out), drawer_count-1 = top (least)
        # Invert the index so bottom drawer has highest value
        inverted_index = drawer_count - 1 - drawer_index

        # Scale between base_pull_out and max_pull_out based on position
        if drawer_count > 1:
            position_factor = inverted_index / (drawer_count - 1)
        else:
            position_factor = 0.5  # Single drawer gets middle pull-out

        pull_out_range = max_pull_out - base_pull_out
        base_amount = base_pull_out + (position_factor * pull_out_range)

        # Add small pseudo-random variation based on drawer_index
        # This creates slight variation between drawers without affecting
        # the cohesion of parts within the same drawer
        hash_bytes = hashlib.md5(str(drawer_index).encode()).digest()
        random_factor = int.from_bytes(hash_bytes[:4], "little") / (2**32)
        # Random variation of +/- 0.5 inch (smaller to keep drawers cohesive)
        random_offset = (random_factor - 0.5) * 1.0

        pull_out_amount = base_amount + random_offset

        # Get base vertices in domain coordinates (Z-up)
        # Apply pull-out by translating in the +Y direction (forward/out from cabinet)
        # Y=0 is at back (wall), Y increases toward front, so +Y pulls drawer out
        x0 = box.origin.x
        y0 = box.origin.y + pull_out_amount  # Pull forward (positive Y)
        z0 = box.origin.z
        width = box.size_x
        depth = box.size_y
        height = box.size_z

        # Generate 8 vertices of the translated box
        vertices = [
            (x0, y0, z0),
            (x0 + width, y0, z0),
            (x0 + width, y0 + depth, z0),
            (x0, y0 + depth, z0),
            (x0, y0, z0 + height),
            (x0 + width, y0, z0 + height),
            (x0 + width, y0 + depth, z0 + height),
            (x0, y0 + depth, z0 + height),
        ]

        # Apply wall rotation and translation to get room coordinates
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        room_vertices = []
        for vx, vy, vz in vertices:
            # Rotate around Z axis
            rx = vx * cos_w - vy * sin_w
            ry = vx * sin_w + vy * cos_w
            # Translate
            room_vertices.append((rx + tx, ry + ty, vz + tz))

        # Transform to Y-up: (x, y, z) -> (x, z, y)
        transformed_vertices = np.array([(x, z, y) for x, y, z in room_vertices])

        # Same triangle indices as axis-aligned box
        triangles = box.get_triangles()

        # Create mesh with 12 triangles
        drawer_mesh = mesh.Mesh(np.zeros(12, dtype=mesh.Mesh.dtype))
        for i, (v0, v1, v2) in enumerate(triangles):
            drawer_mesh.vectors[i] = [
                transformed_vertices[v0],
                transformed_vertices[v1],
                transformed_vertices[v2],
            ]

        return drawer_mesh

    def build_arch_header_mesh(
        self,
        box: BoundingBox3D,
        curve_points: list[tuple[float, float]],
        wall_rotation: float = 0.0,
        wall_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> mesh.Mesh:
        """Create an STL mesh for an arch header panel with curved bottom edge.

        The arch header is a rectangular panel with an arched cutout at the
        bottom. The curve_points define the shape of the arch opening.

        Args:
            box: The 3D bounding box representing the rectangular stock.
            curve_points: List of (x, y) tuples defining the arch curve.
                         x is relative to arch center (-width/2 to +width/2),
                         y is the height at that point (0 = spring line).
            wall_rotation: Rotation around Z axis in degrees.
            wall_position: Translation (x, y, z) after rotation.

        Returns:
            A numpy-stl Mesh object representing the arch header with curve.
        """
        if not curve_points or len(curve_points) < 2:
            # Fall back to box mesh if no curve data
            return self.build_box_mesh_with_transform(box, wall_rotation, wall_position)

        # Box dimensions in domain coordinates (Z-up)
        x0 = box.origin.x
        y0 = box.origin.y  # Front face Y position
        z0 = box.origin.z  # Bottom of panel (where arch starts)
        width = box.size_x
        depth = box.size_y  # Material thickness
        height = box.size_z  # Panel height (arch stock height)

        # The curve_points are relative to arch center at spring line
        # x ranges from -width/2 to +width/2
        # y is the height above spring line (which is at z0 in world coords)
        # The arch OPENING is below the curve, so material is ABOVE the curve

        # Transform curve points to absolute coordinates
        # The panel's left edge is at x0, center is at x0 + width/2
        center_x = x0 + width / 2

        # Build front face vertices (at y0)
        # Order: top-left, top-right, then arch curve points right-to-left
        front_vertices = []

        # Top edge corners
        front_vertices.append((x0, y0, z0 + height))  # Top-left
        front_vertices.append((x0 + width, y0, z0 + height))  # Top-right

        # Arch curve points (reversed to go right-to-left for proper winding)
        for cx, cy in reversed(curve_points):
            px = center_x + cx  # Convert relative x to absolute
            pz = z0 + cy  # Convert relative y to absolute z (height)
            front_vertices.append((px, y0, pz))

        # Build back face vertices (at y0 + depth) - same shape
        back_vertices = [(vx, y0 + depth, vz) for vx, vy, vz in front_vertices]

        # Triangulate the front face using fan from top-center
        # Fan center point
        fan_center = (x0 + width / 2, y0, z0 + height)

        front_triangles = []
        n_verts = len(front_vertices)

        # Create fan triangles for front face
        # Winding is reversed (v2, v1) because Y/Z swap in transform inverts handedness
        for i in range(n_verts):
            v1 = front_vertices[i]
            v2 = front_vertices[(i + 1) % n_verts]
            front_triangles.append((fan_center, v2, v1))

        # Create fan triangles for back face
        # After Y/Z swap, this needs (v1, v2) order for outward normals
        back_fan_center = (x0 + width / 2, y0 + depth, z0 + height)
        back_triangles = []
        for i in range(n_verts):
            v1 = back_vertices[i]
            v2 = back_vertices[(i + 1) % n_verts]
            back_triangles.append((back_fan_center, v1, v2))

        # Create edge faces connecting front and back
        # Winding reversed for Y/Z swap transform
        edge_triangles = []
        for i in range(n_verts):
            # Front edge vertices
            f1 = front_vertices[i]
            f2 = front_vertices[(i + 1) % n_verts]
            # Back edge vertices
            b1 = back_vertices[i]
            b2 = back_vertices[(i + 1) % n_verts]
            # Two triangles per edge segment (quad split into triangles)
            edge_triangles.append((f1, f2, b1))
            edge_triangles.append((f2, b2, b1))

        # Combine all triangles
        all_triangles = front_triangles + back_triangles + edge_triangles

        # Apply wall rotation and translation
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        def transform_vertex(
            v: tuple[float, float, float],
        ) -> tuple[float, float, float]:
            vx, vy, vz = v
            # Rotate around Z axis
            rx = vx * cos_w - vy * sin_w
            ry = vx * sin_w + vy * cos_w
            # Translate and transform to Y-up: (x, y, z) -> (x, z, y)
            return (rx + tx, vz + tz, ry + ty)

        # Create mesh
        arch_mesh = mesh.Mesh(np.zeros(len(all_triangles), dtype=mesh.Mesh.dtype))
        for i, (v0, v1, v2) in enumerate(all_triangles):
            arch_mesh.vectors[i] = [
                transform_vertex(v0),
                transform_vertex(v1),
                transform_vertex(v2),
            ]

        return arch_mesh

    def build_scalloped_panel_mesh(
        self,
        box: BoundingBox3D,
        scallop_points: list[tuple[float, float]],
        wall_rotation: float = 0.0,
        wall_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> mesh.Mesh:
        """Create an STL mesh for a panel with scalloped bottom edge.

        The scalloped panel (typically a valance) has a wavy bottom edge
        defined by the scallop_points.

        Args:
            box: The 3D bounding box representing the rectangular stock.
            scallop_points: List of (x, y) tuples defining the scallop pattern.
                           x is the horizontal position (0 to width),
                           y is the depth of cut (0 = top edge, positive = down).
            wall_rotation: Rotation around Z axis in degrees.
            wall_position: Translation (x, y, z) after rotation.

        Returns:
            A numpy-stl Mesh object representing the scalloped panel.
        """
        if not scallop_points or len(scallop_points) < 2:
            # Fall back to box mesh if no scallop data
            return self.build_box_mesh_with_transform(box, wall_rotation, wall_position)

        # Box dimensions in domain coordinates (Z-up)
        x0 = box.origin.x
        y0 = box.origin.y  # Front face Y position
        z0 = box.origin.z  # Bottom of panel
        width = box.size_x
        depth = box.size_y  # Material thickness
        height = box.size_z  # Panel height

        # The scallop_points define the bottom edge pattern
        # x is position along width (0 to total_width)
        # y is cut depth (0 = top edge of scallop pattern, positive = bottom)
        # The scallops cut INTO the panel from the bottom

        # Build front face vertices (at y0)
        # Order: top-left, top-right, then scallop curve left-to-right at bottom
        front_vertices = []

        # Top edge corners
        front_vertices.append((x0, y0, z0 + height))  # Top-left
        front_vertices.append((x0 + width, y0, z0 + height))  # Top-right

        # Right edge down to scallop start
        # The scallops are at the bottom, so we go from top-right down
        # First scallop point x=0 is at left edge

        # Scallop points in reverse order (right to left) for proper winding
        # Each point (sx, sy) where sx is x-position, sy is depth of cut
        for sx, sy in reversed(scallop_points):
            px = x0 + sx  # Absolute x position
            # sy is depth of cut from top of scallop zone
            # The panel bottom is at z0, scallop cuts up from there
            pz = z0 + (height - sy)  # Higher sy = deeper cut = lower z
            front_vertices.append((px, y0, pz))

        # Build back face vertices (at y0 + depth) - same shape
        back_vertices = [(vx, y0 + depth, vz) for vx, vy, vz in front_vertices]

        # Triangulate faces using fan from top-center
        fan_center = (x0 + width / 2, y0, z0 + height)
        back_fan_center = (x0 + width / 2, y0 + depth, z0 + height)

        front_triangles = []
        back_triangles = []
        edge_triangles = []

        n_verts = len(front_vertices)

        # Front face fan triangles
        # Winding is reversed (v2, v1) because Y/Z swap in transform inverts handedness
        for i in range(n_verts):
            v1 = front_vertices[i]
            v2 = front_vertices[(i + 1) % n_verts]
            front_triangles.append((fan_center, v2, v1))

        # Back face fan triangles
        # After Y/Z swap, this needs (v1, v2) order for outward normals
        for i in range(n_verts):
            v1 = back_vertices[i]
            v2 = back_vertices[(i + 1) % n_verts]
            back_triangles.append((back_fan_center, v1, v2))

        # Edge faces connecting front and back
        # Winding reversed for Y/Z swap transform
        for i in range(n_verts):
            f1 = front_vertices[i]
            f2 = front_vertices[(i + 1) % n_verts]
            b1 = back_vertices[i]
            b2 = back_vertices[(i + 1) % n_verts]
            edge_triangles.append((f1, f2, b1))
            edge_triangles.append((f2, b2, b1))

        # Combine all triangles
        all_triangles = front_triangles + back_triangles + edge_triangles

        # Apply wall rotation and translation
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        def transform_vertex(
            v: tuple[float, float, float],
        ) -> tuple[float, float, float]:
            vx, vy, vz = v
            rx = vx * cos_w - vy * sin_w
            ry = vx * sin_w + vy * cos_w
            return (rx + tx, vz + tz, ry + ty)

        # Create mesh
        scallop_mesh = mesh.Mesh(np.zeros(len(all_triangles), dtype=mesh.Mesh.dtype))
        for i, (v0, v1, v2) in enumerate(all_triangles):
            scallop_mesh.vectors[i] = [
                transform_vertex(v0),
                transform_vertex(v1),
                transform_vertex(v2),
            ]

        return scallop_mesh

    def build_stepped_side_mesh(
        self,
        box: BoundingBox3D,
        step_height: float,
        step_depth_change: float,
        wall_rotation: float = 0.0,
        wall_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> mesh.Mesh:
        """Create mesh for side panel that steps inward at a height transition.

        Creates an L-shaped panel by combining two rectangular boxes:
        - Bottom box: full depth, from floor to step_height
        - Top box: reduced depth, from step_height to full height

        Used when base zone is deeper than upper zone (e.g., base 24", upper 12").
        Panel is full depth below step_height, reduced depth above.

        The stepped panel has an L-shape when viewed from the side:

            +-----+      <- top (reduced depth)
            |     |
            |     +----+ <- step_height (full depth starts here)
            |          |
            |          |
            +----------+ <- bottom (full depth)

        Args:
            box: Bounding box for the full panel (max dimensions).
                 size_x = thickness, size_y = full depth, size_z = full height
            step_height: Height from bottom where the step occurs.
            step_depth_change: How much the depth reduces at the step (positive value).
            wall_rotation: Rotation around Z axis in degrees.
            wall_position: Translation (x, y, z) after rotation.

        Returns:
            mesh.Mesh with L-shaped geometry (combined from two boxes).

        Raises:
            ValueError: If step_height is not positive or exceeds box height.
            ValueError: If step_depth_change exceeds box depth.
        """
        from cabinets.domain import BoundingBox3D, Position3D

        # Validate step parameters
        if step_height <= 0:
            raise ValueError(f"step_height must be positive, got {step_height}")
        if step_height >= box.size_z:
            raise ValueError(
                f"step_height ({step_height}) must be less than box height ({box.size_z})"
            )
        if step_depth_change > box.size_y:
            raise ValueError(
                f"step_depth_change ({step_depth_change}) cannot exceed "
                f"box depth ({box.size_y})"
            )

        # Create bottom box (full depth, from floor to step_height)
        bottom_box = BoundingBox3D(
            origin=Position3D(
                x=box.origin.x,
                y=box.origin.y,
                z=box.origin.z,
            ),
            size_x=box.size_x,  # Panel thickness
            size_y=box.size_y,  # Full depth
            size_z=step_height,  # From floor to step
        )

        # Create top box (reduced depth, from step_height to full height)
        reduced_depth = box.size_y - step_depth_change
        top_box = BoundingBox3D(
            origin=Position3D(
                x=box.origin.x,
                y=box.origin.y,  # Same front position
                z=box.origin.z + step_height,  # Start at step height
            ),
            size_x=box.size_x,  # Same panel thickness
            size_y=reduced_depth,  # Reduced depth
            size_z=box.size_z - step_height,  # Remaining height
        )

        # Build meshes for both boxes with transform applied
        bottom_mesh = self.build_box_mesh_with_transform(
            bottom_box, wall_rotation, wall_position
        )
        top_mesh = self.build_box_mesh_with_transform(
            top_box, wall_rotation, wall_position
        )

        # Combine meshes
        return self.combine_meshes([bottom_mesh, top_mesh])

    def combine_meshes(self, meshes: list[mesh.Mesh]) -> mesh.Mesh:
        """Combine multiple meshes into a single mesh.

        Args:
            meshes: List of meshes to combine.

        Returns:
            A single combined mesh containing all faces.
        """
        if not meshes:
            return mesh.Mesh(np.zeros(0, dtype=mesh.Mesh.dtype))

        total_faces = sum(m.vectors.shape[0] for m in meshes)
        combined = mesh.Mesh(np.zeros(total_faces, dtype=mesh.Mesh.dtype))

        offset = 0
        for m in meshes:
            num_faces = m.vectors.shape[0]
            combined.vectors[offset : offset + num_faces] = m.vectors
            offset += num_faces

        return combined


class StlExporter:
    """Exports cabinet layouts to STL format.

    Single Responsibility: Orchestrates the conversion of Cabinet domain objects
    to STL files using the Panel3DMapper and StlMeshBuilder.

    Dependency Inversion: Depends on domain abstractions (Cabinet, BoundingBox3D),
    not on numpy-stl implementation details exposed to the domain.
    """

    def __init__(self, mesh_builder: StlMeshBuilder | None = None) -> None:
        """Initialize the exporter.

        Args:
            mesh_builder: Optional mesh builder instance for dependency injection.
        """
        self.mesh_builder = mesh_builder or StlMeshBuilder()

    def export(self, cabinet: Cabinet, door_ajar_angle: float = 45.0) -> mesh.Mesh:
        """Export a cabinet to an STL mesh object.

        Doors are rendered slightly ajar (open) to make them visually
        distinguishable from solid panels. Decorative elements (arches,
        scallops) are rendered with actual curved geometry.

        Args:
            cabinet: The cabinet to export.
            door_ajar_angle: Angle in degrees to open doors (default 15°).

        Returns:
            A numpy-stl Mesh object representing the entire cabinet.
        """
        mapper = Panel3DMapper(cabinet)
        panels_with_boxes = mapper.map_all_panels_with_types()

        # Define drawer panel types that should be rendered pulled out
        drawer_panel_types = {
            PanelType.DRAWER_FRONT,
            PanelType.DRAWER_SIDE,
            PanelType.DRAWER_BOX_FRONT,
            PanelType.DRAWER_BOTTOM,
        }

        meshes = []
        for box, panel in panels_with_boxes:
            if panel.panel_type == PanelType.DOOR:
                # Render doors ajar so they're visually distinguishable
                # Use random angle (30-60°) so stacked doors don't align perfectly
                hinge_side = panel.metadata.get("hinge_side", "left")
                ajar_angle = _random_ajar_angle(box)
                meshes.append(
                    self.mesh_builder.build_ajar_door_mesh(
                        box, ajar_angle=ajar_angle, hinge_side=hinge_side
                    )
                )
            elif panel.panel_type in drawer_panel_types:
                # Render drawer panels pulled out, with bottom drawers
                # pulled out more than top drawers
                drawer_index = panel.metadata.get("drawer_index", 0)
                drawer_count = panel.metadata.get("drawer_count", 1)
                meshes.append(
                    self.mesh_builder.build_pulled_out_drawer_mesh(
                        box,
                        drawer_index=drawer_index,
                        drawer_count=drawer_count,
                    )
                )
            elif panel.panel_type == PanelType.ARCH_HEADER:
                # Render arch header with actual curved geometry
                curve_points = panel.metadata.get("curve_points")
                if curve_points:
                    meshes.append(
                        self.mesh_builder.build_arch_header_mesh(box, curve_points)
                    )
                else:
                    meshes.append(self.mesh_builder.build_box_mesh(box))
            elif panel.panel_type == PanelType.VALANCE:
                # Render scalloped valance with actual scallop geometry
                scallop_points = panel.metadata.get("scallop_points")
                if scallop_points:
                    meshes.append(
                        self.mesh_builder.build_scalloped_panel_mesh(
                            box, scallop_points
                        )
                    )
                else:
                    meshes.append(self.mesh_builder.build_box_mesh(box))
            elif panel.panel_type == PanelType.STEPPED_SIDE:
                # Render stepped side panel with L-shaped geometry
                step_height = panel.metadata.get("step_height", box.size_z / 2)
                step_depth_change = panel.metadata.get("step_depth_change", 0.0)
                if step_depth_change > 0:
                    meshes.append(
                        self.mesh_builder.build_stepped_side_mesh(
                            box,
                            step_height=step_height,
                            step_depth_change=step_depth_change,
                        )
                    )
                else:
                    # No depth change, render as regular box
                    meshes.append(self.mesh_builder.build_box_mesh(box))
            else:
                meshes.append(self.mesh_builder.build_box_mesh(box))

        return self.mesh_builder.combine_meshes(meshes)

    def export_to_file(
        self,
        cabinet: Cabinet,
        filepath: Path | str,
        door_ajar_angle: float = 45.0,
    ) -> None:
        """Export a cabinet to an STL file.

        Args:
            cabinet: The cabinet to export.
            filepath: Path where the STL file will be saved.
            door_ajar_angle: Angle in degrees to open doors (default 15°).
        """
        combined_mesh = self.export(cabinet, door_ajar_angle=door_ajar_angle)
        combined_mesh.save(str(filepath))

    def export_room_layout(
        self,
        room_output: RoomLayoutOutput,
        filepath: Path | str,
        door_ajar_angle: float = 45.0,
    ) -> None:
        """Export a room layout with multiple cabinets to an STL file.

        Uses RoomPanel3DMapper to transform each cabinet's panels into room
        coordinates, then combines all meshes into a single STL file.

        Args:
            room_output: The room layout output containing cabinets and transforms.
            filepath: Path where the STL file will be saved.
            door_ajar_angle: Angle in degrees to open doors (default 45).
        """
        room_mesh = self.export_room(room_output, door_ajar_angle=door_ajar_angle)
        room_mesh.save(str(filepath))

    def export_room(
        self,
        room_output: RoomLayoutOutput,
        door_ajar_angle: float = 45.0,
    ) -> mesh.Mesh:
        """Export a room layout to an STL mesh object.

        Uses RoomPanel3DMapper to transform each cabinet's panels into room
        coordinates, applying the proper rotation and translation for each
        cabinet's position along the walls. Decorative elements (arches,
        scallops) are rendered with actual curved geometry.

        Args:
            room_output: The room layout output containing cabinets and transforms.
            door_ajar_angle: Angle in degrees to open doors (default 45).

        Returns:
            A numpy-stl Mesh object representing the entire room layout.
        """
        if not room_output.cabinets:
            return mesh.Mesh(np.zeros(0, dtype=mesh.Mesh.dtype))

        # Use RoomPanel3DMapper to get boxes in LOCAL coordinates with transforms
        room_mapper = RoomPanel3DMapper()
        panels_with_boxes = room_mapper.map_cabinets_to_boxes_with_panels(
            room_output.cabinets, room_output.transforms
        )

        # Define drawer panel types that should be rendered pulled out
        drawer_panel_types = {
            PanelType.DRAWER_FRONT,
            PanelType.DRAWER_SIDE,
            PanelType.DRAWER_BOX_FRONT,
            PanelType.DRAWER_BOTTOM,
        }

        # Build meshes for each panel, applying transforms after ajar/pull-out effects
        meshes = []
        for box, panel, transform in panels_with_boxes:
            # Extract transform info for mesh builders
            wall_rotation = transform.rotation_z
            wall_position = (
                transform.position.x,
                transform.position.y,
                transform.position.z,
            )

            if panel.panel_type == PanelType.DOOR:
                # Render doors ajar, then transform to room coordinates
                # Use random angle (30-60°) so stacked doors don't align perfectly
                hinge_side = panel.metadata.get("hinge_side", "left")
                ajar_angle = _random_ajar_angle(box)
                meshes.append(
                    self.mesh_builder.build_ajar_door_mesh(
                        box,
                        ajar_angle=ajar_angle,
                        hinge_side=hinge_side,
                        wall_rotation=wall_rotation,
                        wall_position=wall_position,
                    )
                )
            elif panel.panel_type in drawer_panel_types:
                # Render drawer pulled out, then transform to room coordinates
                drawer_index = panel.metadata.get("drawer_index", 0)
                drawer_count = panel.metadata.get("drawer_count", 1)
                meshes.append(
                    self.mesh_builder.build_pulled_out_drawer_mesh(
                        box,
                        drawer_index=drawer_index,
                        drawer_count=drawer_count,
                        wall_rotation=wall_rotation,
                        wall_position=wall_position,
                    )
                )
            elif panel.panel_type == PanelType.ARCH_HEADER:
                # Render arch header with actual curved geometry
                curve_points = panel.metadata.get("curve_points")
                if curve_points:
                    meshes.append(
                        self.mesh_builder.build_arch_header_mesh(
                            box,
                            curve_points,
                            wall_rotation=wall_rotation,
                            wall_position=wall_position,
                        )
                    )
                else:
                    meshes.append(
                        self.mesh_builder.build_box_mesh_with_transform(
                            box,
                            wall_rotation=wall_rotation,
                            wall_position=wall_position,
                        )
                    )
            elif panel.panel_type == PanelType.VALANCE:
                # Render scalloped valance with actual scallop geometry
                scallop_points = panel.metadata.get("scallop_points")
                if scallop_points:
                    meshes.append(
                        self.mesh_builder.build_scalloped_panel_mesh(
                            box,
                            scallop_points,
                            wall_rotation=wall_rotation,
                            wall_position=wall_position,
                        )
                    )
                else:
                    meshes.append(
                        self.mesh_builder.build_box_mesh_with_transform(
                            box,
                            wall_rotation=wall_rotation,
                            wall_position=wall_position,
                        )
                    )
            elif panel.panel_type == PanelType.STEPPED_SIDE:
                # Render stepped side panel with L-shaped geometry
                step_height = panel.metadata.get("step_height", box.size_z / 2)
                step_depth_change = panel.metadata.get("step_depth_change", 0.0)
                if step_depth_change > 0:
                    meshes.append(
                        self.mesh_builder.build_stepped_side_mesh(
                            box,
                            step_height=step_height,
                            step_depth_change=step_depth_change,
                            wall_rotation=wall_rotation,
                            wall_position=wall_position,
                        )
                    )
                else:
                    # No depth change, render as regular box
                    meshes.append(
                        self.mesh_builder.build_box_mesh_with_transform(
                            box,
                            wall_rotation=wall_rotation,
                            wall_position=wall_position,
                        )
                    )
            else:
                # Regular panel - just apply transform
                meshes.append(
                    self.mesh_builder.build_box_mesh_with_transform(
                        box,
                        wall_rotation=wall_rotation,
                        wall_position=wall_position,
                    )
                )

        return self.mesh_builder.combine_meshes(meshes)

    def export_zone_stack(
        self,
        result: ZoneStackLayoutResult,
        output_path: Path | str,
        door_ajar_angle: float = 45.0,
    ) -> None:
        """Export a complete zone stack to an STL file.

        Positions all zones correctly:
        - Base cabinet at floor level
        - Countertop panels on top of base cabinet
        - Upper cabinet at mounting height

        Args:
            result: Zone stack layout result from ZoneLayoutService.
            output_path: Path where the STL file will be saved.
            door_ajar_angle: Angle in degrees to open doors (default 45).
        """
        zone_mesh = self.export_zone_stack_mesh(result, door_ajar_angle)
        zone_mesh.save(str(output_path))

    def export_zone_stack_mesh(
        self,
        result: ZoneStackLayoutResult,
        door_ajar_angle: float = 45.0,
    ) -> mesh.Mesh:
        """Export a zone stack to an STL mesh object.

        Positions all zones correctly:
        - Base cabinet at floor level
        - Countertop panels on top of base cabinet
        - Upper cabinet at mounting height

        Args:
            result: Zone stack layout result from ZoneLayoutService.
            door_ajar_angle: Angle in degrees to open doors (default 45).

        Returns:
            A numpy-stl Mesh object representing the entire zone stack.
        """
        meshes: list[mesh.Mesh] = []

        # Determine cabinet depth and back thickness from base cabinet
        cabinet_depth = 24.0  # Default
        back_thickness = 0.25  # Default
        if result.base_cabinet:
            cabinet_depth = result.base_cabinet.depth
            if result.base_cabinet.back_material:
                back_thickness = result.base_cabinet.back_material.thickness

        # Export base cabinet at floor level
        if result.base_cabinet:
            base_mesh = self.export(result.base_cabinet, door_ajar_angle)
            meshes.append(base_mesh)

        # Export countertop panels
        if result.countertop_panels:
            countertop_meshes = self._export_panels_as_meshes(
                list(result.countertop_panels),
                cabinet_depth=cabinet_depth,
                back_thickness=back_thickness,
            )
            meshes.extend(countertop_meshes)

        # Export upper cabinet at mounting height
        if result.upper_cabinet:
            # Calculate mounting height from gap zones or base cabinet
            mounting_height = self._calculate_mounting_height(result)
            upper_mesh = self._export_cabinet_with_offset(
                result.upper_cabinet,
                z_offset=mounting_height,
                door_ajar_angle=door_ajar_angle,
            )
            meshes.append(upper_mesh)

        # Export full-height side panels
        if result.full_height_side_panels:
            side_meshes = self._export_panels_as_meshes(
                list(result.full_height_side_panels),
                cabinet_depth=cabinet_depth,
                back_thickness=back_thickness,
            )
            meshes.extend(side_meshes)

        # Export wall nailer panels
        if result.wall_nailer_panels:
            nailer_meshes = self._export_panels_as_meshes(
                list(result.wall_nailer_panels),
                cabinet_depth=cabinet_depth,
                back_thickness=back_thickness,
            )
            meshes.extend(nailer_meshes)

        # Combine all meshes
        if meshes:
            return self.mesh_builder.combine_meshes(meshes)
        else:
            return mesh.Mesh(np.zeros(0, dtype=mesh.Mesh.dtype))

    def _export_panels_as_meshes(
        self,
        panels: list[Panel],
        cabinet_depth: float = 24.0,
        back_thickness: float = 0.25,
    ) -> list[mesh.Mesh]:
        """Export a list of panels to meshes.

        Args:
            panels: List of panels to export.
            cabinet_depth: Cabinet depth for positioning calculations.
            back_thickness: Back panel thickness for Y positioning (default 0.25").

        Returns:
            List of mesh objects for the panels.
        """
        meshes: list[mesh.Mesh] = []

        for panel in panels:
            thickness = panel.material.thickness

            # Determine the bounding box based on panel type
            if panel.panel_type == PanelType.COUNTERTOP:
                # Horizontal countertop panel
                box = BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=back_thickness,
                        z=panel.position.y,  # position.y is the height
                    ),
                    size_x=panel.width,
                    size_y=panel.height,  # panel.height is depth for horizontal
                    size_z=thickness,
                )
            elif panel.panel_type in (
                PanelType.LEFT_SIDE,
                PanelType.RIGHT_SIDE,
                PanelType.STEPPED_SIDE,
            ):
                # Vertical side panel
                box = BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=panel.width,  # panel.width is depth for vertical
                    size_z=panel.height,
                )
                # Handle stepped side panels
                if panel.panel_type == PanelType.STEPPED_SIDE:
                    step_height = panel.metadata.get("step_height", box.size_z / 2)
                    step_depth_change = panel.metadata.get("step_depth_change", 0.0)
                    if step_depth_change > 0:
                        stepped_mesh = self.mesh_builder.build_stepped_side_mesh(
                            box,
                            step_height=step_height,
                            step_depth_change=step_depth_change,
                        )
                        meshes.append(stepped_mesh)
                        continue
            elif panel.panel_type == PanelType.NAILER:
                # Horizontal nailer panel
                box = BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,  # nailer depth
                    size_z=thickness,
                )
            elif panel.panel_type == PanelType.SUPPORT_BRACKET:
                # Support bracket for countertop
                box = BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=cabinet_depth - thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )
            else:
                # Default: horizontal panel
                box = BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,
                    size_z=thickness,
                )

            meshes.append(self.mesh_builder.build_box_mesh(box))

        return meshes

    def _calculate_mounting_height(self, result: ZoneStackLayoutResult) -> float:
        """Calculate the mounting height for the upper cabinet.

        The mounting height is determined by:
        1. Gap zones (if present): Use the highest gap zone's top edge
        2. Base cabinet + countertop (if gap zones absent): Use base height + countertop
        3. Default: 54" (standard upper cabinet mounting height)

        Args:
            result: Zone stack layout result containing cabinets and gap zones.

        Returns:
            Height in inches from floor where upper cabinet should be mounted.
        """
        # Method 1: Calculate from gap zones
        if result.gap_zones:
            # Find the gap zone that precedes the upper cabinet
            # This is typically the highest gap zone (backsplash, mirror, etc.)
            max_gap_top = 0.0
            for gap in result.gap_zones:
                gap_top = gap.bottom_height + gap.height
                if gap_top > max_gap_top:
                    max_gap_top = gap_top
            if max_gap_top > 0:
                return max_gap_top

        # Method 2: Calculate from base cabinet and countertop
        if result.base_cabinet:
            base_height = result.base_cabinet.height
            # Add countertop thickness if present
            countertop_thickness = 0.0
            if result.countertop_panels:
                # Get thickness from first countertop panel
                countertop_thickness = result.countertop_panels[0].material.thickness
            # Add a standard backsplash gap (18") if no gap zones specified
            # This represents a typical kitchen configuration
            return base_height + countertop_thickness + 18.0

        # Method 3: Default fallback
        return 54.0  # Standard upper cabinet mounting height

    def _export_cabinet_with_offset(
        self,
        cabinet: Cabinet,
        z_offset: float,
        door_ajar_angle: float = 45.0,
    ) -> mesh.Mesh:
        """Export a cabinet with a vertical offset.

        Args:
            cabinet: The cabinet to export.
            z_offset: Vertical offset in inches (height from floor).
            door_ajar_angle: Angle in degrees to open doors.

        Returns:
            A numpy-stl Mesh object representing the offset cabinet.
        """
        # Export the cabinet normally
        cabinet_mesh = self.export(cabinet, door_ajar_angle)

        # Apply the z offset (domain height) to all vertices.
        #
        # Coordinate transform from domain to mesh (for Y-up STL viewers):
        #   Domain: (x, y, z) = (width, depth, height)  [Z-up]
        #   Mesh:   (x, y, z) = (width, height, depth)  [Y-up]
        #
        # The transform is: domain (x, y, z) -> mesh (x, z, y)
        # So domain z (height) becomes mesh y (index [1]).
        #
        # Adding z_offset to mesh y raises the cabinet vertically.
        for i in range(len(cabinet_mesh.vectors)):
            for j in range(3):
                cabinet_mesh.vectors[i][j][1] += z_offset

        return cabinet_mesh
