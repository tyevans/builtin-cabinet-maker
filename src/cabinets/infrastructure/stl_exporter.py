"""STL export functionality using numpy-stl."""

import hashlib
import math
import random
from pathlib import Path

import numpy as np
from stl import mesh

from cabinets.application.dtos import RoomLayoutOutput
from cabinets.domain import BoundingBox3D, Cabinet, Panel, Panel3DMapper, PanelType
from cabinets.domain.services import RoomPanel3DMapper


def _random_ajar_angle(box: BoundingBox3D, min_angle: float = 30.0, max_angle: float = 60.0) -> float:
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
        """
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
        for i in range(n_verts):
            v1 = front_vertices[i]
            v2 = front_vertices[(i + 1) % n_verts]
            front_triangles.append((fan_center, v1, v2))

        # Create fan triangles for back face (reverse winding)
        back_fan_center = (x0 + width / 2, y0 + depth, z0 + height)
        back_triangles = []
        for i in range(n_verts):
            v1 = back_vertices[i]
            v2 = back_vertices[(i + 1) % n_verts]
            back_triangles.append((back_fan_center, v2, v1))  # Reversed winding

        # Create edge faces connecting front and back
        edge_triangles = []
        for i in range(n_verts):
            # Front edge vertices
            f1 = front_vertices[i]
            f2 = front_vertices[(i + 1) % n_verts]
            # Back edge vertices
            b1 = back_vertices[i]
            b2 = back_vertices[(i + 1) % n_verts]
            # Two triangles per edge segment (quad split into triangles)
            edge_triangles.append((f1, b1, f2))
            edge_triangles.append((f2, b1, b2))

        # Combine all triangles
        all_triangles = front_triangles + back_triangles + edge_triangles

        # Apply wall rotation and translation
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        def transform_vertex(v: tuple[float, float, float]) -> tuple[float, float, float]:
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
        for i in range(n_verts):
            v1 = front_vertices[i]
            v2 = front_vertices[(i + 1) % n_verts]
            front_triangles.append((fan_center, v1, v2))

        # Back face fan triangles (reverse winding)
        for i in range(n_verts):
            v1 = back_vertices[i]
            v2 = back_vertices[(i + 1) % n_verts]
            back_triangles.append((back_fan_center, v2, v1))

        # Edge faces connecting front and back
        for i in range(n_verts):
            f1 = front_vertices[i]
            f2 = front_vertices[(i + 1) % n_verts]
            b1 = back_vertices[i]
            b2 = back_vertices[(i + 1) % n_verts]
            edge_triangles.append((f1, b1, f2))
            edge_triangles.append((f2, b1, b2))

        # Combine all triangles
        all_triangles = front_triangles + back_triangles + edge_triangles

        # Apply wall rotation and translation
        wall_angle_rad = math.radians(wall_rotation)
        cos_w = math.cos(wall_angle_rad)
        sin_w = math.sin(wall_angle_rad)
        tx, ty, tz = wall_position

        def transform_vertex(v: tuple[float, float, float]) -> tuple[float, float, float]:
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

    def export(
        self, cabinet: Cabinet, door_ajar_angle: float = 45.0
    ) -> mesh.Mesh:
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
                        self.mesh_builder.build_scalloped_panel_mesh(box, scallop_points)
                    )
                else:
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
