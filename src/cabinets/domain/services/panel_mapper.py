"""Panel 3D mapping services for cabinet layout.

This module provides services for mapping 2D panel representations to 3D
bounding boxes, supporting both single cabinet and multi-cabinet room scenarios.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..value_objects import BoundingBox3D, PanelType, Position3D, SectionTransform
from .panel_generation import PanelGenerationService

if TYPE_CHECKING:
    from ..entities import Cabinet, Panel

__all__ = [
    "Panel3DMapper",
    "RoomPanel3DMapper",
]


class Panel3DMapper:
    """Maps 2D panel representations to 3D bounding boxes.

    Coordinate system:
    - Origin: Front-bottom-left corner of cabinet
    - X: Width (left to right)
    - Y: Depth (front to back)
    - Z: Height (bottom to top)
    """

    def __init__(self, cabinet: Cabinet) -> None:
        self.cabinet = cabinet
        # back_material is set to a default in Cabinet.__post_init__ if None
        assert cabinet.back_material is not None
        self.back_thickness = cabinet.back_material.thickness
        self.material_thickness = cabinet.material.thickness
        # Extract toe kick height if present
        self.base_zone_height = 0.0
        if cabinet.base_zone and cabinet.base_zone.get("zone_type") == "toe_kick":
            self.base_zone_height = cabinet.base_zone.get("height", 0.0)

    def map_panel(self, panel: Panel) -> BoundingBox3D:
        """Convert a 2D panel to a 3D bounding box."""
        thickness = panel.material.thickness

        match panel.panel_type:
            case PanelType.TOP:
                # Horizontal panel at top of cabinet
                return BoundingBox3D(
                    origin=Position3D(
                        x=0,
                        y=self.back_thickness,
                        z=self.cabinet.height - thickness,
                    ),
                    size_x=self.cabinet.width,
                    size_y=panel.height,  # panel.height is depth for horizontal panels
                    size_z=thickness,
                )

            case PanelType.BOTTOM:
                # Horizontal panel at bottom of cabinet (raised by toe kick if present)
                return BoundingBox3D(
                    origin=Position3D(
                        x=0, y=self.back_thickness, z=self.base_zone_height
                    ),
                    size_x=self.cabinet.width,
                    size_y=panel.height,
                    size_z=thickness,
                )

            case PanelType.LEFT_SIDE:
                # Vertical panel on left side
                return BoundingBox3D(
                    origin=Position3D(
                        x=0,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=panel.width,  # panel.width is depth for vertical panels
                    size_z=panel.height,
                )

            case PanelType.RIGHT_SIDE:
                # Vertical panel on right side
                return BoundingBox3D(
                    origin=Position3D(
                        x=self.cabinet.width - thickness,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=panel.width,
                    size_z=panel.height,
                )

            case PanelType.BACK:
                # Back panel at y=0 (against the wall)
                return BoundingBox3D(
                    origin=Position3D(x=0, y=0, z=0),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.SHELF:
                # Horizontal shelf within a section
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,  # panel.height is depth for shelves
                    size_z=thickness,
                )

            case PanelType.DIVIDER:
                # Vertical divider between sections
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=panel.width,  # panel.width is depth for dividers
                    size_z=panel.height,
                )

            case PanelType.HORIZONTAL_DIVIDER:
                # Horizontal divider between rows (like a shelf spanning full width)
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,  # panel.height is depth for horizontal dividers
                    size_z=thickness,
                )

            case PanelType.DOOR:
                # Vertical panel at front face of cabinet
                # y = cabinet_depth - thickness places door at the front
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.DRAWER_FRONT:
                # Decorative front panel of the drawer (visible, at front face)
                # y = cabinet_depth - thickness places drawer front at the front
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.DRAWER_SIDE:
                # Left or right side panel of the drawer box
                # panel.width is the depth of the drawer box (box_depth)
                # panel.height is the height of the drawer box side
                # Sides extend backward from the box front
                box_depth = panel.width
                # Box front is flush behind decorative front
                box_front_y = self.cabinet.depth - self.material_thickness - thickness
                # Side starts at back edge and extends to box front
                side_start_y = box_front_y - box_depth + thickness
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=side_start_y,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=box_depth,  # panel.width is depth for drawer sides
                    size_z=panel.height,
                )

            case PanelType.DRAWER_BOX_FRONT:
                # Front panel of the drawer box (behind the decorative drawer front)
                # Flush against the back of the decorative front panel
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - self.material_thickness - thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.DRAWER_BOTTOM:
                # Horizontal bottom panel of the drawer box
                # panel.height is the depth (bottom_depth) for horizontal panels
                bottom_depth = panel.height
                # Align with drawer sides - box front is flush behind decorative front
                # Use drawer_side_thickness from metadata if available, otherwise default
                # to standard 0.5" drawer side thickness
                box_side_thickness = (
                    panel.metadata.get("drawer_side_thickness", 0.5)
                    if panel.metadata
                    else 0.5
                )
                box_front_y = (
                    self.cabinet.depth - self.material_thickness - box_side_thickness
                )
                bottom_start_y = box_front_y - bottom_depth + box_side_thickness
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=bottom_start_y,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=bottom_depth,
                    size_z=thickness,
                )

            case PanelType.DIAGONAL_FACE:
                # Angled front panel for diagonal corner cabinets
                # Uses rectangular approximation for STL generation
                # The actual panel sits at a 45-degree angle, but we approximate
                # with a rectangular bounding box positioned at the front face
                # Note: panel.metadata may contain is_angled: true and angle: 45
                # for downstream processing that can handle angled geometry
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.FILLER:
                # Vertical filler panel at the side of a cabinet
                # Used in blind corner cabinets to fill gaps
                # Similar to DIVIDER - a vertical panel
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=panel.width,  # panel.width is depth for vertical panels
                    size_z=panel.height,
                )

            case PanelType.TOE_KICK:
                # Recessed panel at bottom front of cabinet
                # The setback value from metadata positions it behind the cabinet front
                setback = panel.metadata.get("setback", 3.0) if panel.metadata else 3.0
                return BoundingBox3D(
                    origin=Position3D(
                        x=0,
                        y=self.cabinet.depth - setback,  # Recessed from front
                        z=0,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.NAILER:
                # Horizontal nailer strip at top back for crown molding mounting
                # Sits on top of the cabinet top panel, at the back
                # panel.height is the nailer depth (how far it extends from back)
                return BoundingBox3D(
                    origin=Position3D(
                        x=0,
                        y=self.back_thickness,  # Just in front of back panel
                        z=self.cabinet.height,  # On top of cabinet (above top panel)
                    ),
                    size_x=panel.width,
                    size_y=panel.height,  # Nailer depth
                    size_z=thickness,
                )

            case PanelType.LIGHT_RAIL:
                # Vertical strip at bottom front for light concealment
                setback = (
                    panel.metadata.get("setback", 0.25) if panel.metadata else 0.25
                )
                return BoundingBox3D(
                    origin=Position3D(
                        x=0,
                        y=self.cabinet.depth - thickness - setback,  # At front face
                        z=0,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.FACE_FRAME_STILE:
                # Vertical stile at cabinet front (left or right)
                # Face frame attaches to front of cabinet, extending outward
                # panel.width is the stile width, panel.height is the cabinet height
                # Position.x indicates left (0) or right (cabinet.width - stile_width)
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth,  # Flush with front, extends outward
                        z=panel.position.y,  # Typically 0 (starts at bottom)
                    ),
                    size_x=panel.width,  # Stile width
                    size_y=thickness,  # Stile depth (material thickness)
                    size_z=panel.height,  # Full cabinet height
                )

            case PanelType.FACE_FRAME_RAIL:
                # Horizontal rail at cabinet front (top or bottom)
                # Face frame attaches to front of cabinet, extending outward
                # panel.width is the rail length, panel.height is the rail width
                # Position.x is the x offset (stile_width), Position.y is z position
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,  # Offset by stile width
                        y=self.cabinet.depth,  # Flush with front, extends outward
                        z=panel.position.y,  # 0 for bottom, cabinet.height - rail_width for top
                    ),
                    size_x=panel.width,  # Rail length (between stiles)
                    size_y=thickness,  # Rail depth (material thickness)
                    size_z=panel.height,  # Rail width (height dimension)
                )

            # --- Desk panels (FRD-18) ---

            case PanelType.DESKTOP:
                # Horizontal panel at desk height
                desk_height = (
                    panel.metadata.get("desk_height", 30.0) if panel.metadata else 30.0
                )
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=desk_height - thickness,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,
                    size_z=thickness,
                )

            case PanelType.WATERFALL_EDGE:
                # Vertical panel at front edge of desktop
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.KEYBOARD_TRAY:
                # Horizontal panel below desktop for keyboard
                tray_z = panel.position.y if panel.position.y > 0 else 26.0
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=tray_z,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,
                    size_z=thickness,
                )

            case PanelType.KEYBOARD_ENCLOSURE:
                # Vertical side rails for keyboard tray enclosure
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,
                    size_y=panel.width,
                    size_z=panel.height,
                )

            case PanelType.MODESTY_PANEL:
                # Vertical panel at back of knee clearance zone
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.WIRE_CHASE:
                # Vertical channel panel for cable routing
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=0,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=thickness,
                    size_z=panel.height,
                )

            case PanelType.CABLE_CHASE:
                # Vertical cable routing channel (FRD-19 Entertainment Centers)
                # A tall, narrow vertical panel at the rear of the cabinet
                # Used for routing cables from floor to equipment shelves
                # Typical dimensions: 3-4" wide, full height, thin (1/4") depth representation
                # Position at rear (y=0 is against wall, y=cabinet.depth is front)
                chase_depth = thickness  # Use panel thickness (typically 0.25")
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,  # At rear, just in front of back panel
                        z=panel.position.y,  # Vertical position (bottom of chase)
                    ),
                    size_x=panel.width,  # Chase width (typically 3-4")
                    size_y=chase_depth,  # Thin panel representation
                    size_z=panel.height,  # Full section/cabinet height
                )

            # --- Countertop and Zone panels (FRD-22) ---

            case PanelType.COUNTERTOP:
                # Horizontal countertop panel sitting on top of base cabinet
                # panel.width = countertop width (may include overhangs)
                # panel.height = countertop depth (for horizontal panels, height is depth)
                # position.y = height above floor where countertop sits
                countertop_height = panel.position.y
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,  # Start behind back panel
                        z=countertop_height,  # Height of countertop
                    ),
                    size_x=panel.width,  # Countertop width
                    size_y=panel.height,  # Countertop depth
                    size_z=thickness,  # Countertop thickness
                )

            case PanelType.SUPPORT_BRACKET:
                # Support bracket for countertop overhang
                # Typically L-shaped but approximated as a rectangular box
                # panel.width = bracket width (typically 1-2")
                # panel.height = bracket height (vertical dimension)
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - thickness,  # At front of cabinet
                        z=panel.position.y,  # Vertical position
                    ),
                    size_x=panel.width,  # Bracket width
                    size_y=thickness,  # Bracket depth (thin)
                    size_z=panel.height,  # Bracket height
                )

            case PanelType.STEPPED_SIDE:
                # Full-height side panel that steps inward at a height transition
                # Used when base zone is deeper than upper zone
                # The actual stepping is handled by the STL mesh builder
                # panel.width = maximum depth (at base)
                # panel.height = full height
                # Metadata may contain step_height and step_depth_change
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=thickness,  # Panel thickness
                    size_y=panel.width,  # panel.width is depth for side panels
                    size_z=panel.height,  # Full height
                )

            case _:
                # Fallback for any unhandled panel types - treat as horizontal panel
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.back_thickness,
                        z=panel.position.y,
                    ),
                    size_x=panel.width,
                    size_y=panel.height,
                    size_z=thickness,
                )

    def map_all_panels(self) -> list[BoundingBox3D]:
        """Convert all cabinet panels to 3D bounding boxes."""
        panel_service = PanelGenerationService()
        panels = panel_service.get_all_panels(self.cabinet)
        return [self.map_panel(panel) for panel in panels]

    def map_all_panels_with_types(self) -> list[tuple[BoundingBox3D, Panel]]:
        """Convert all cabinet panels to 3D bounding boxes with panel info.

        Returns a list of tuples containing the bounding box and the original
        panel. This allows consumers to check panel types (e.g., for rendering
        doors differently than other panels).

        Returns:
            List of (BoundingBox3D, Panel) tuples for all cabinet panels.
        """
        panel_service = PanelGenerationService()
        panels = panel_service.get_all_panels(self.cabinet)
        return [(self.map_panel(panel), panel) for panel in panels]


class RoomPanel3DMapper:
    """Maps panels from multiple cabinets to 3D bounding boxes with room transforms.

    Wraps the existing Panel3DMapper to handle multi-wall room scenarios.
    Each cabinet section is first mapped to 3D boxes at origin, then
    transformed (rotated and translated) based on its SectionTransform.
    """

    def __init__(self, panel_mapper: Panel3DMapper | None = None) -> None:
        """Initialize with optional existing Panel3DMapper.

        Args:
            panel_mapper: Optional Panel3DMapper instance to use.
                         If None, a new one will be created for each cabinet.
        """
        self._panel_mapper = panel_mapper

    def map_cabinets_to_boxes(
        self,
        cabinets: list[Cabinet],
        transforms: list[SectionTransform],
    ) -> list[BoundingBox3D]:
        """Map multiple cabinets to transformed 3D bounding boxes.

        Each cabinet is first mapped to bounding boxes at origin using
        Panel3DMapper, then each box is transformed according to the
        corresponding SectionTransform.

        Args:
            cabinets: List of cabinet sections (one per wall assignment)
            transforms: Corresponding transforms for each cabinet

        Returns:
            Combined list of BoundingBox3D with room transforms applied

        Raises:
            ValueError: If cabinets and transforms have different lengths
        """
        if len(cabinets) != len(transforms):
            raise ValueError(
                f"Number of cabinets ({len(cabinets)}) must match "
                f"number of transforms ({len(transforms)})"
            )

        all_boxes: list[BoundingBox3D] = []

        for cabinet, transform in zip(cabinets, transforms):
            # Use provided mapper or create one for this cabinet
            if self._panel_mapper is not None:
                # If a mapper was provided, use it (assumes same cabinet)
                mapper = self._panel_mapper
            else:
                mapper = Panel3DMapper(cabinet)

            # Get all panels mapped to boxes at origin
            origin_boxes = mapper.map_all_panels()

            # Apply transform to each box
            for box in origin_boxes:
                transformed_box = self._apply_transform(box, transform)
                all_boxes.append(transformed_box)

        return all_boxes

    def map_cabinets_to_boxes_with_panels(
        self,
        cabinets: list[Cabinet],
        transforms: list[SectionTransform],
    ) -> list[tuple[BoundingBox3D, Panel, SectionTransform]]:
        """Map multiple cabinets to 3D bounding boxes with panel info and transforms.

        Unlike map_cabinets_to_boxes, this returns the ORIGINAL (untransformed)
        bounding boxes along with their transforms. This allows the STL exporter
        to apply ajar/pull-out effects in local coordinates before transforming.

        Args:
            cabinets: List of cabinet sections (one per wall assignment)
            transforms: Corresponding transforms for each cabinet

        Returns:
            List of (BoundingBox3D, Panel, SectionTransform) tuples.
            The box is in LOCAL coordinates (not yet transformed).
            The transform should be applied after any ajar/pull-out effects.
        """
        if len(cabinets) != len(transforms):
            raise ValueError(
                f"Number of cabinets ({len(cabinets)}) must match "
                f"number of transforms ({len(transforms)})"
            )

        results: list[tuple[BoundingBox3D, Panel, SectionTransform]] = []

        for cabinet, transform in zip(cabinets, transforms):
            # Create mapper for this cabinet
            mapper = Panel3DMapper(cabinet)

            # Get panels with boxes at origin (local coordinates)
            panels_with_boxes = mapper.map_all_panels_with_types()

            # Return original boxes with their transform (NOT pre-transformed)
            for box, panel in panels_with_boxes:
                results.append((box, panel, transform))

        return results

    def _apply_transform(
        self,
        box: BoundingBox3D,
        transform: SectionTransform,
    ) -> BoundingBox3D:
        """Apply a SectionTransform to a bounding box.

        The transform is applied in two steps:
        1. Rotate the box around Z axis by transform.rotation_z degrees
        2. Translate by transform.position

        For rotation around Z axis:
        - x' = x * cos(angle) - y * sin(angle)
        - y' = x * sin(angle) + y * cos(angle)
        - z' = z (unchanged)

        After rotating all 8 corners, we compute a new axis-aligned bounding
        box from the transformed corners.

        Args:
            box: The bounding box to transform
            transform: The transform to apply (rotation + translation)

        Returns:
            New BoundingBox3D with transform applied
        """
        # Get all 8 vertices of the box
        vertices = box.get_vertices()

        # Convert rotation to radians
        angle_rad = math.radians(transform.rotation_z)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)

        # Transform each vertex: rotate then translate
        transformed_vertices: list[tuple[float, float, float]] = []
        for x, y, z in vertices:
            # Rotate around Z axis
            x_rot = x * cos_angle - y * sin_angle
            y_rot = x * sin_angle + y * cos_angle
            z_rot = z  # Z unchanged for rotation around Z axis

            # Translate by transform position
            x_final = x_rot + transform.position.x
            y_final = y_rot + transform.position.y
            z_final = z_rot + transform.position.z

            transformed_vertices.append((x_final, y_final, z_final))

        # Compute new axis-aligned bounding box from transformed vertices
        x_coords = [v[0] for v in transformed_vertices]
        y_coords = [v[1] for v in transformed_vertices]
        z_coords = [v[2] for v in transformed_vertices]

        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)
        min_z = min(z_coords)
        max_z = max(z_coords)

        # Handle floating-point precision issues: clamp near-zero values to zero
        # This prevents very small negative numbers from causing Position3D validation errors
        epsilon = 1e-10
        if abs(min_x) < epsilon:
            min_x = 0.0
        if abs(min_y) < epsilon:
            min_y = 0.0
        if abs(min_z) < epsilon:
            min_z = 0.0
        if abs(max_x) < epsilon:
            max_x = 0.0
        if abs(max_y) < epsilon:
            max_y = 0.0
        if abs(max_z) < epsilon:
            max_z = 0.0

        # Position3D requires non-negative coordinates. In room coordinate space,
        # rotations can produce negative values. We need to shift the entire AABB
        # to positive space while preserving its size.
        shift_x = -min_x if min_x < 0 else 0.0
        shift_y = -min_y if min_y < 0 else 0.0
        shift_z = -min_z if min_z < 0 else 0.0

        # Apply shift to make all coordinates non-negative
        min_x += shift_x
        max_x += shift_x
        min_y += shift_y
        max_y += shift_y
        min_z += shift_z
        max_z += shift_z

        # Create new bounding box with transformed origin and dimensions
        return BoundingBox3D(
            origin=Position3D(x=min_x, y=min_y, z=min_z),
            size_x=max_x - min_x,
            size_y=max_y - min_y,
            size_z=max_z - min_z,
        )
