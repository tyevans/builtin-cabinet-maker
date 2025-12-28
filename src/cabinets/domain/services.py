"""Domain services for cabinet layout and calculations."""

from dataclasses import dataclass
import math

from .entities import Cabinet, Obstacle, Panel, Room, Section, Shelf, Wall, WallSegment
from .section_resolver import SectionSpec, resolve_section_widths
from .value_objects import (
    BoundingBox3D,
    Clearance,
    CollisionResult,
    CutPiece,
    DEFAULT_CLEARANCES,
    FitError,
    LayoutResult,
    LayoutWarning,
    MaterialSpec,
    ObstacleType,
    ObstacleZone,
    PanelType,
    PlacedSection,
    Position,
    Position3D,
    SectionBounds,
    SectionTransform,
    SkippedArea,
    ValidRegion,
    WallSectionAssignment,
)


@dataclass
class LayoutParameters:
    """Parameters for generating a cabinet layout."""

    num_sections: int = 1
    shelves_per_section: int = 3
    material: MaterialSpec = None  # type: ignore
    back_material: MaterialSpec = None  # type: ignore

    def __post_init__(self) -> None:
        if self.material is None:
            self.material = MaterialSpec.standard_3_4()
        if self.back_material is None:
            self.back_material = MaterialSpec.standard_1_2()
        if self.num_sections < 1:
            raise ValueError("Must have at least 1 section")
        if self.shelves_per_section < 0:
            raise ValueError("Cannot have negative shelves")


class LayoutCalculator:
    """Calculates cabinet layout from wall dimensions and parameters."""

    def generate_cabinet(self, wall: Wall, params: LayoutParameters) -> Cabinet:
        """Generate a complete cabinet layout with equal-width sections.

        This is the original method that creates equal-width sections with
        uniform shelf counts. For more control over section widths and per-section
        shelf counts, use generate_cabinet_from_specs().

        Args:
            wall: Wall dimensions constraining the cabinet.
            params: Layout parameters including section count and shelves per section.

        Returns:
            A Cabinet entity with the generated layout.
        """
        cabinet = Cabinet(
            width=wall.width,
            height=wall.height,
            depth=wall.depth,
            material=params.material,
            back_material=params.back_material,
        )

        # Calculate section dimensions
        total_dividers = params.num_sections - 1
        divider_width = params.material.thickness * total_dividers
        available_width = cabinet.interior_width - divider_width
        section_width = available_width / params.num_sections

        # Create sections with shelves
        current_x = params.material.thickness  # Start after left side panel
        for i in range(params.num_sections):
            section = Section(
                width=section_width,
                height=cabinet.interior_height,
                depth=cabinet.interior_depth,
                position=Position(current_x, params.material.thickness),
            )

            # Add evenly spaced shelves
            if params.shelves_per_section > 0:
                shelf_spacing = cabinet.interior_height / (
                    params.shelves_per_section + 1
                )
                for j in range(params.shelves_per_section):
                    shelf_y = params.material.thickness + shelf_spacing * (j + 1)
                    shelf = Shelf(
                        width=section_width,
                        depth=cabinet.interior_depth,
                        material=params.material,
                        position=Position(current_x, shelf_y),
                    )
                    section.add_shelf(shelf)

            cabinet.sections.append(section)
            current_x += section_width + params.material.thickness

        return cabinet

    def generate_cabinet_from_specs(
        self,
        wall: Wall,
        params: LayoutParameters,
        section_specs: list[SectionSpec],
    ) -> Cabinet:
        """Generate a cabinet layout with specified section widths and shelf counts.

        This method provides more control over cabinet layout by allowing:
        - Fixed or "fill" widths for each section
        - Different shelf counts per section

        The section_specs list defines each section's width and shelf count.
        Widths can be fixed numbers or "fill" to auto-calculate remaining space.

        Args:
            wall: Wall dimensions constraining the cabinet.
            params: Layout parameters (material specs are used from here).
            section_specs: List of section specifications with widths and shelf counts.

        Returns:
            A Cabinet entity with the generated layout.

        Example:
            >>> specs = [
            ...     SectionSpec(width=24.0, shelves=3),
            ...     SectionSpec(width="fill", shelves=5),
            ... ]
            >>> cabinet = calculator.generate_cabinet_from_specs(wall, params, specs)
        """
        cabinet = Cabinet(
            width=wall.width,
            height=wall.height,
            depth=wall.depth,
            material=params.material,
            back_material=params.back_material,
        )

        # Resolve section widths using the section resolver
        resolved_widths = resolve_section_widths(
            specs=section_specs,
            total_width=wall.width,
            material_thickness=params.material.thickness,
        )

        # Create sections with their specified widths and shelf counts
        current_x = params.material.thickness  # Start after left side panel

        for i, (spec, section_width) in enumerate(zip(section_specs, resolved_widths)):
            section = Section(
                width=section_width,
                height=cabinet.interior_height,
                depth=cabinet.interior_depth,
                position=Position(current_x, params.material.thickness),
            )

            # Add evenly spaced shelves based on this section's specification
            if spec.shelves > 0:
                shelf_spacing = cabinet.interior_height / (spec.shelves + 1)
                for j in range(spec.shelves):
                    shelf_y = params.material.thickness + shelf_spacing * (j + 1)
                    shelf = Shelf(
                        width=section_width,
                        depth=cabinet.interior_depth,
                        material=params.material,
                        position=Position(current_x, shelf_y),
                    )
                    section.add_shelf(shelf)

            cabinet.sections.append(section)
            current_x += section_width + params.material.thickness

        return cabinet


class CutListGenerator:
    """Generates optimized cut lists from cabinets."""

    def generate(self, cabinet: Cabinet) -> list[CutPiece]:
        """Generate a cut list for the given cabinet."""
        return cabinet.get_cut_list()

    def sort_by_size(self, cut_list: list[CutPiece]) -> list[CutPiece]:
        """Sort cut list by area (largest first) for efficient cutting."""
        return sorted(cut_list, key=lambda p: p.area, reverse=True)


@dataclass
class MaterialEstimate:
    """Estimate of materials needed for a project."""

    total_area_sqin: float
    total_area_sqft: float
    sheet_count_4x8: int
    sheet_count_5x5: int
    waste_percentage: float

    @property
    def description(self) -> str:
        """Human-readable description of material needs."""
        return (
            f"{self.total_area_sqft:.1f} sq ft total "
            f"({self.sheet_count_4x8} sheets of 4x8, "
            f"assuming {self.waste_percentage:.0%} waste)"
        )


class MaterialEstimator:
    """Estimates material requirements for cabinet construction."""

    SHEET_4X8_SQIN = 48 * 96  # 4608 sq in
    SHEET_5X5_SQIN = 60 * 60  # 3600 sq in

    def __init__(self, waste_factor: float = 0.15) -> None:
        """Initialize with waste factor (default 15%)."""
        self.waste_factor = waste_factor

    def estimate(self, cut_list: list[CutPiece]) -> dict[MaterialSpec, MaterialEstimate]:
        """Estimate materials needed for a cut list, grouped by material type."""
        # Group pieces by material
        material_areas: dict[MaterialSpec, float] = {}
        for piece in cut_list:
            if piece.material not in material_areas:
                material_areas[piece.material] = 0
            material_areas[piece.material] += piece.area

        # Calculate estimates per material
        estimates: dict[MaterialSpec, MaterialEstimate] = {}
        for material, total_area in material_areas.items():
            area_with_waste = total_area * (1 + self.waste_factor)
            estimates[material] = MaterialEstimate(
                total_area_sqin=total_area,
                total_area_sqft=total_area / 144,
                sheet_count_4x8=math.ceil(area_with_waste / self.SHEET_4X8_SQIN),
                sheet_count_5x5=math.ceil(area_with_waste / self.SHEET_5X5_SQIN),
                waste_percentage=self.waste_factor,
            )

        return estimates

    def estimate_total(self, cut_list: list[CutPiece]) -> MaterialEstimate:
        """Estimate total materials needed (all types combined)."""
        total_area = sum(piece.area for piece in cut_list)
        area_with_waste = total_area * (1 + self.waste_factor)
        return MaterialEstimate(
            total_area_sqin=total_area,
            total_area_sqft=total_area / 144,
            sheet_count_4x8=math.ceil(area_with_waste / self.SHEET_4X8_SQIN),
            sheet_count_5x5=math.ceil(area_with_waste / self.SHEET_5X5_SQIN),
            waste_percentage=self.waste_factor,
        )


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
        self.back_thickness = cabinet.back_material.thickness
        self.material_thickness = cabinet.material.thickness

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
                # Horizontal panel at bottom of cabinet
                return BoundingBox3D(
                    origin=Position3D(x=0, y=self.back_thickness, z=0),
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

    def map_all_panels(self) -> list[BoundingBox3D]:
        """Convert all cabinet panels to 3D bounding boxes."""
        panels = self.cabinet.get_all_panels()
        return [self.map_panel(panel) for panel in panels]


class RoomLayoutService:
    """Calculates cabinet positions within room geometry.

    This service handles the assignment of cabinet sections to walls
    within a room and computes the 3D transforms needed for STL generation.
    """

    def assign_sections_to_walls(
        self,
        room: Room,
        section_specs: list[SectionSpec],
    ) -> list[WallSectionAssignment]:
        """Assign cabinet sections to wall segments.

        Each SectionSpec may have an optional 'wall' attribute:
        - If wall is None or not specified, assign to wall index 0
        - If wall is an int, it's the wall index (0-based)
        - If wall is a str, find the wall by name

        For each wall, sections are placed sequentially from the wall's start.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications to assign.

        Returns:
            List of WallSectionAssignment objects with computed positions.

        Raises:
            ValueError: If a wall reference is invalid.
        """
        if not section_specs:
            return []

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Group sections by wall index
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec in enumerate(section_specs):
            wall_idx = self._resolve_wall_index(
                spec.wall, len(room.walls), wall_name_to_index
            )
            if wall_idx not in wall_sections:
                wall_sections[wall_idx] = []
            wall_sections[wall_idx].append((section_idx, spec))

        # Create assignments with sequential offsets per wall
        assignments: list[WallSectionAssignment] = []

        for wall_idx, sections in wall_sections.items():
            current_offset = 0.0

            for section_idx, spec in sections:
                # For fixed width sections, use the width directly
                # For fill sections, we need to resolve the width
                if spec.is_fill:
                    # Calculate fill width based on remaining space on this wall
                    wall_length = room.walls[wall_idx].length
                    fixed_widths = sum(
                        s.fixed_width or 0.0
                        for _, s in sections
                        if not s.is_fill
                    )
                    fill_count = sum(1 for _, s in sections if s.is_fill)
                    remaining = wall_length - fixed_widths
                    section_width = remaining / fill_count if fill_count > 0 else 0.0
                else:
                    section_width = spec.fixed_width or 0.0

                assignments.append(
                    WallSectionAssignment(
                        section_index=section_idx,
                        wall_index=wall_idx,
                        offset_along_wall=current_offset,
                    )
                )
                current_offset += section_width

        # Sort by section index to maintain original order
        assignments.sort(key=lambda a: a.section_index)
        return assignments

    def compute_section_transforms(
        self,
        room: Room,
        assignments: list[WallSectionAssignment],
        section_specs: list[SectionSpec],
    ) -> list[SectionTransform]:
        """Compute 3D position and rotation for each section.

        Used for STL generation with correct spatial layout.

        Args:
            room: The room containing wall segments.
            assignments: Wall assignments for each section.
            section_specs: Original section specifications (for width calculation).

        Returns:
            List of SectionTransform objects with 3D positions and rotations.
        """
        if not assignments:
            return []

        wall_positions = room.get_wall_positions()
        transforms: list[SectionTransform] = []

        # Build wall name to index mapping for width resolution
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Pre-compute section widths per wall for fill sections
        wall_section_widths = self._compute_section_widths_per_wall(
            room, section_specs, wall_name_to_index
        )

        for assignment in assignments:
            wall_pos = wall_positions[assignment.wall_index]
            wall_segment = room.walls[assignment.wall_index]

            # Calculate position along the wall
            direction_rad = math.radians(wall_pos.direction)

            # Calculate X, Y position based on wall start and offset
            x = wall_pos.start.x + assignment.offset_along_wall * math.cos(direction_rad)
            y = wall_pos.start.y + assignment.offset_along_wall * math.sin(direction_rad)

            # Calculate the perpendicular offset for depth
            # The cabinet sits against the wall, so we offset perpendicular
            # to the wall direction by the wall depth
            # Perpendicular direction is wall_direction - 90 degrees (to the right)
            perp_direction_rad = math.radians(wall_pos.direction - 90)
            depth_offset_x = wall_segment.depth * math.cos(perp_direction_rad)
            depth_offset_y = wall_segment.depth * math.sin(perp_direction_rad)

            # Z position starts at floor level
            z = 0.0

            # Handle potential negative coordinates by ensuring non-negative
            # The Position3D requires non-negative values, so we may need to
            # adjust the coordinate system. For now, use absolute values if needed.
            final_x = x + depth_offset_x
            final_y = y + depth_offset_y

            # Position3D requires non-negative coordinates. In room coordinates,
            # we may have negative values. We handle this by offsetting to ensure
            # all values are non-negative when needed.
            # For simplicity, we create the transform with the raw values,
            # but Position3D will validate them.
            try:
                position = Position3D(x=max(0.0, final_x), y=max(0.0, final_y), z=z)
            except ValueError:
                # If coordinates are negative, clamp to zero
                position = Position3D(x=0.0, y=0.0, z=0.0)

            # Rotation is based on wall direction
            # Wall direction is angle from positive X axis
            rotation_z = wall_pos.direction

            transforms.append(
                SectionTransform(
                    section_index=assignment.section_index,
                    wall_index=assignment.wall_index,
                    position=position,
                    rotation_z=rotation_z,
                )
            )

        return transforms

    def validate_fit(
        self,
        room: Room,
        section_specs: list[SectionSpec],
    ) -> list[FitError]:
        """Check that sections fit on their assigned walls.

        Validates:
        - invalid_wall_reference: Wall name/index doesn't exist
        - exceeds_length: Total section widths on a wall exceed wall length
        - overlap: Sections overlap on the same wall

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications to validate.

        Returns:
            List of FitError objects describing any issues found.
        """
        errors: list[FitError] = []

        if not section_specs:
            return errors

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # First pass: check for invalid wall references
        valid_sections: list[tuple[int, SectionSpec, int]] = []
        for section_idx, spec in enumerate(section_specs):
            try:
                wall_idx = self._resolve_wall_index(
                    spec.wall, len(room.walls), wall_name_to_index
                )
                valid_sections.append((section_idx, spec, wall_idx))
            except ValueError as e:
                errors.append(
                    FitError(
                        section_index=section_idx,
                        wall_index=None,
                        message=str(e),
                        error_type="invalid_wall_reference",
                    )
                )

        # Group valid sections by wall
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec, wall_idx in valid_sections:
            if wall_idx not in wall_sections:
                wall_sections[wall_idx] = []
            wall_sections[wall_idx].append((section_idx, spec))

        # Check each wall for length and overlap issues
        for wall_idx, sections in wall_sections.items():
            wall_length = room.walls[wall_idx].length

            # Calculate widths for this wall's sections
            fixed_widths = sum(
                s.fixed_width or 0.0 for _, s in sections if not s.is_fill
            )
            fill_count = sum(1 for _, s in sections if s.is_fill)

            # Calculate remaining space for fill sections
            remaining_for_fills = wall_length - fixed_widths

            if remaining_for_fills < 0:
                # Fixed widths alone exceed wall length
                errors.append(
                    FitError(
                        section_index=sections[0][0],  # First section on this wall
                        wall_index=wall_idx,
                        message=(
                            f"Fixed section widths ({fixed_widths:.2f}\") exceed "
                            f"wall length ({wall_length:.2f}\") on wall {wall_idx}"
                        ),
                        error_type="exceeds_length",
                    )
                )
                continue

            # If there are fill sections, check if they would have valid width
            if fill_count > 0:
                fill_width = remaining_for_fills / fill_count
                if fill_width <= 0:
                    errors.append(
                        FitError(
                            section_index=sections[0][0],
                            wall_index=wall_idx,
                            message=(
                                f"Fill sections would have zero or negative width on wall {wall_idx}"
                            ),
                            error_type="exceeds_length",
                        )
                    )
                    continue

            # Calculate total width (all sections)
            total_width = fixed_widths
            if fill_count > 0:
                total_width += fill_count * (remaining_for_fills / fill_count)

            # Check if total exceeds wall length (with tolerance)
            if total_width > wall_length + 0.001:
                errors.append(
                    FitError(
                        section_index=sections[0][0],
                        wall_index=wall_idx,
                        message=(
                            f"Total section width ({total_width:.2f}\") exceeds "
                            f"wall length ({wall_length:.2f}\") on wall {wall_idx}"
                        ),
                        error_type="exceeds_length",
                    )
                )

        return errors

    def _resolve_wall_index(
        self,
        wall_ref: str | int | None,
        num_walls: int,
        wall_name_to_index: dict[str, int],
    ) -> int:
        """Resolve a wall reference to a wall index.

        Args:
            wall_ref: Wall reference (None, int index, or string name).
            num_walls: Total number of walls in the room.
            wall_name_to_index: Mapping from wall names to indices.

        Returns:
            Wall index (0-based).

        Raises:
            ValueError: If the wall reference is invalid.
        """
        if wall_ref is None:
            return 0

        if isinstance(wall_ref, int):
            if wall_ref < 0 or wall_ref >= num_walls:
                raise ValueError(
                    f"Wall index {wall_ref} is out of range (0-{num_walls - 1})"
                )
            return wall_ref

        if isinstance(wall_ref, str):
            if wall_ref not in wall_name_to_index:
                raise ValueError(f"Wall name '{wall_ref}' not found")
            return wall_name_to_index[wall_ref]

        raise ValueError(f"Invalid wall reference type: {type(wall_ref)}")

    def _compute_section_widths_per_wall(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        wall_name_to_index: dict[str, int],
    ) -> dict[int, list[float]]:
        """Compute resolved section widths grouped by wall.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications.
            wall_name_to_index: Mapping from wall names to indices.

        Returns:
            Dictionary mapping wall index to list of section widths.
        """
        # Group sections by wall
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec in enumerate(section_specs):
            try:
                wall_idx = self._resolve_wall_index(
                    spec.wall, len(room.walls), wall_name_to_index
                )
                if wall_idx not in wall_sections:
                    wall_sections[wall_idx] = []
                wall_sections[wall_idx].append((section_idx, spec))
            except ValueError:
                continue

        # Compute widths per wall
        result: dict[int, list[float]] = {}
        for wall_idx, sections in wall_sections.items():
            wall_length = room.walls[wall_idx].length
            fixed_widths = sum(
                s.fixed_width or 0.0 for _, s in sections if not s.is_fill
            )
            fill_count = sum(1 for _, s in sections if s.is_fill)
            remaining = wall_length - fixed_widths
            fill_width = remaining / fill_count if fill_count > 0 else 0.0

            widths: list[float] = []
            for _, spec in sections:
                if spec.is_fill:
                    widths.append(fill_width)
                else:
                    widths.append(spec.fixed_width or 0.0)

            result[wall_idx] = widths

        return result


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

        # Position3D requires non-negative coordinates. In room coordinate space,
        # rotations can produce negative values. We clamp to zero with a warning
        # that the caller should ensure transforms produce valid room positions.
        if min_x < 0:
            min_x = 0.0
        if min_y < 0:
            min_y = 0.0
        if min_z < 0:
            min_z = 0.0

        # Create new bounding box with transformed origin and dimensions
        return BoundingBox3D(
            origin=Position3D(x=min_x, y=min_y, z=min_z),
            size_x=max_x - min_x,
            size_y=max_y - min_y,
            size_z=max_z - min_z,
        )


class ObstacleCollisionService:
    """Detects collisions between cabinet sections and obstacles.

    This service provides collision detection capabilities for cabinet layout,
    including:
    - Getting obstacle zones for specific walls
    - Checking individual sections against obstacle zones
    - Batch collision checking for multiple sections
    - Finding valid regions on walls where sections can be placed

    Attributes:
        default_clearances: Mapping of obstacle types to their default clearances.
    """

    def __init__(
        self, default_clearances: dict[ObstacleType, Clearance] | None = None
    ) -> None:
        """Initialize the collision service.

        Args:
            default_clearances: Optional custom clearance mapping. If not provided,
                               uses DEFAULT_CLEARANCES from value_objects.
        """
        self.default_clearances = default_clearances or DEFAULT_CLEARANCES

    def get_obstacle_zones(
        self,
        obstacles: list[Obstacle],
        wall_index: int,
    ) -> list[ObstacleZone]:
        """Get all obstacle zones for a specific wall.

        Filters obstacles to those on the specified wall and computes their
        exclusion zones including clearances.

        Args:
            obstacles: List of all obstacles in the room.
            wall_index: Index of the wall to get zones for.

        Returns:
            List of ObstacleZone objects for obstacles on the specified wall.
        """
        return [
            obs.get_zone_bounds(obs.get_clearance(self.default_clearances))
            for obs in obstacles
            if obs.wall_index == wall_index
        ]

    def check_collision(
        self,
        section: SectionBounds,
        zones: list[ObstacleZone],
    ) -> list[CollisionResult]:
        """Check if section collides with any obstacle zones.

        Args:
            section: The cabinet section bounds to check.
            zones: List of obstacle zones to check against.

        Returns:
            List of CollisionResult objects for each collision detected.
            Empty list if no collisions.
        """
        results = []
        for zone in zones:
            if zone.overlaps(section):
                overlap = self._calculate_overlap_area(section, zone)
                results.append(CollisionResult(zone=zone, overlap_area=overlap))
        return results

    def check_collisions_batch(
        self,
        sections: list[SectionBounds],
        zones: list[ObstacleZone],
    ) -> dict[int, list[CollisionResult]]:
        """Check multiple sections against multiple zones.

        Performs collision detection for each section and returns results
        keyed by section index.

        Args:
            sections: List of cabinet section bounds to check.
            zones: List of obstacle zones to check against.

        Returns:
            Dictionary mapping section index to list of CollisionResult objects.
            Sections with no collisions will have empty lists.
        """
        return {
            i: self.check_collision(section, zones)
            for i, section in enumerate(sections)
        }

    def find_valid_regions(
        self,
        wall_length: float,
        wall_height: float,
        zones: list[ObstacleZone],
        min_width: float = 6.0,
        min_height: float = 12.0,
    ) -> list[ValidRegion]:
        """Find regions on wall where sections can be placed.

        Analyzes the wall space considering obstacle zones and finds all
        regions where cabinet sections can be placed.

        Returns regions categorized as:
        - "full": Full height available (no vertical obstruction)
        - "lower": Below obstacles (e.g., under windows)
        - "upper": Above obstacles (e.g., over doors)
        - "gap": Horizontal gap between obstacles

        Args:
            wall_length: Total length of the wall in inches.
            wall_height: Total height of the wall in inches.
            zones: List of obstacle zones on the wall.
            min_width: Minimum region width to include (default 6 inches).
            min_height: Minimum region height to include (default 12 inches).

        Returns:
            List of ValidRegion objects representing available placement areas.
        """
        if not zones:
            return [
                ValidRegion(
                    left=0,
                    right=wall_length,
                    bottom=0,
                    top=wall_height,
                    region_type="full",
                )
            ]

        regions: list[ValidRegion] = []

        # Sort zones by horizontal position
        sorted_zones = sorted(zones, key=lambda z: z.left)

        # Find horizontal regions (gaps between zones and regions above/below zones)
        current_x = 0.0
        for zone in sorted_zones:
            # Gap before this zone (analyze vertical region)
            if zone.left > current_x:
                gap_region = self._analyze_vertical_region(
                    left=current_x,
                    right=zone.left,
                    wall_height=wall_height,
                    zones=zones,
                    min_width=min_width,
                    min_height=min_height,
                )
                regions.extend(gap_region)

            # Region below zone
            if zone.bottom > 0:
                lower = ValidRegion(
                    left=max(0, zone.left),
                    right=min(wall_length, zone.right),
                    bottom=0,
                    top=zone.bottom,
                    region_type="lower",
                )
                if lower.width >= min_width and lower.height >= min_height:
                    regions.append(lower)

            # Region above zone
            if zone.top < wall_height:
                upper = ValidRegion(
                    left=max(0, zone.left),
                    right=min(wall_length, zone.right),
                    bottom=zone.top,
                    top=wall_height,
                    region_type="upper",
                )
                if upper.width >= min_width and upper.height >= min_height:
                    regions.append(upper)

            current_x = max(current_x, zone.right)

        # Gap after last zone
        if current_x < wall_length:
            gap_region = self._analyze_vertical_region(
                left=current_x,
                right=wall_length,
                wall_height=wall_height,
                zones=zones,
                min_width=min_width,
                min_height=min_height,
            )
            regions.extend(gap_region)

        return regions

    def _calculate_overlap_area(
        self,
        section: SectionBounds,
        zone: ObstacleZone,
    ) -> float:
        """Calculate the overlapping area between section and zone.

        Args:
            section: The cabinet section bounds.
            zone: The obstacle zone.

        Returns:
            Overlap area in square inches. Returns 0 if no overlap.
        """
        x_overlap = max(
            0, min(section.right, zone.right) - max(section.left, zone.left)
        )
        y_overlap = max(
            0, min(section.top, zone.top) - max(section.bottom, zone.bottom)
        )
        return x_overlap * y_overlap

    def _analyze_vertical_region(
        self,
        left: float,
        right: float,
        wall_height: float,
        zones: list[ObstacleZone],
        min_width: float,
        min_height: float,
    ) -> list[ValidRegion]:
        """Analyze a vertical slice of wall for valid regions.

        Examines a horizontal range of the wall and determines what vertical
        regions are available, considering any obstacles that block portions
        of that horizontal range.

        Args:
            left: Left edge of the horizontal range.
            right: Right edge of the horizontal range.
            wall_height: Total height of the wall.
            zones: All obstacle zones on the wall.
            min_width: Minimum region width to include.
            min_height: Minimum region height to include.

        Returns:
            List of ValidRegion objects for the analyzed slice.
        """
        if right - left < min_width:
            return []

        # Check if any zones block this horizontal region
        blocking_zones = [
            z for z in zones if not (z.right <= left or z.left >= right)
        ]

        if not blocking_zones:
            return [
                ValidRegion(
                    left=left,
                    right=right,
                    bottom=0,
                    top=wall_height,
                    region_type="full",
                )
            ]

        # Find unblocked vertical regions
        regions: list[ValidRegion] = []

        # Sort blockers by bottom edge
        sorted_blockers = sorted(blocking_zones, key=lambda z: z.bottom)

        current_y = 0.0
        for blocker in sorted_blockers:
            if blocker.bottom > current_y:
                region = ValidRegion(
                    left=left,
                    right=right,
                    bottom=current_y,
                    top=blocker.bottom,
                    region_type="gap" if current_y > 0 else "lower",
                )
                if region.height >= min_height:
                    regions.append(region)
            current_y = max(current_y, blocker.top)

        # Region above all blockers
        if current_y < wall_height:
            region = ValidRegion(
                left=left,
                right=right,
                bottom=current_y,
                top=wall_height,
                region_type="upper",
            )
            if region.height >= min_height:
                regions.append(region)

        return regions


class ObstacleAwareLayoutService:
    """Lays out cabinet sections while avoiding obstacles.

    This service calculates the placement of cabinet sections on a wall,
    automatically avoiding obstacles and finding the best available regions.
    It supports automatic height mode selection (full, lower, upper) and
    can split sections around obstacles when necessary.

    Attributes:
        collision_service: Service for obstacle collision detection.
        min_section_width: Minimum width for a section in inches (default 6.0).
        min_section_height: Minimum height for a section in inches (default 12.0).
    """

    def __init__(
        self,
        collision_service: ObstacleCollisionService,
        min_section_width: float = 6.0,
        min_section_height: float = 12.0,
    ) -> None:
        """Initialize the layout service.

        Args:
            collision_service: Service for obstacle collision detection.
            min_section_width: Minimum width for a section in inches.
            min_section_height: Minimum height for a section in inches.
        """
        self.collision_service = collision_service
        self.min_section_width = min_section_width
        self.min_section_height = min_section_height

    def layout_sections(
        self,
        wall_length: float,
        wall_height: float,
        wall_index: int,
        obstacles: list[Obstacle],
        requested_sections: list[SectionSpec],
    ) -> LayoutResult:
        """Layout sections on wall, avoiding obstacles.

        Algorithm:
        1. Get obstacle zones for this wall
        2. Find valid regions
        3. For each requested section:
           - If height_mode specified, use that
           - If "auto" or None, try full height first, then lower, then upper
           - Try to fit in available regions
           - If doesn't fit, try splitting
           - If still doesn't fit, add to skipped with warning
        4. Return placed sections, warnings, and skipped areas

        Args:
            wall_length: Total length of the wall in inches.
            wall_height: Total height of the wall in inches.
            wall_index: Index of the wall (0-based).
            obstacles: List of all obstacles in the room.
            requested_sections: List of section specifications to place.

        Returns:
            LayoutResult containing placed sections, warnings, and skipped areas.
        """
        zones = self.collision_service.get_obstacle_zones(obstacles, wall_index)
        valid_regions = self.collision_service.find_valid_regions(
            wall_length,
            wall_height,
            zones,
            min_width=self.min_section_width,
            min_height=self.min_section_height,
        )

        placed_sections: list[PlacedSection] = []
        warnings: list[LayoutWarning] = []
        skipped_areas: list[SkippedArea] = []

        # Track remaining space in each region
        remaining_regions = list(valid_regions)
        current_x = 0.0

        for i, spec in enumerate(requested_sections):
            section_width = self._resolve_width(
                spec, wall_length, current_x, remaining_regions
            )
            height_mode = spec.height_mode or "full"

            if height_mode == "auto":
                # Try full height first, then lower, then upper
                placement = self._try_place_section(
                    i,
                    section_width,
                    spec.shelves,
                    remaining_regions,
                    zones,
                    wall_height,
                    current_x,
                    preferred_modes=["full", "lower", "upper"],
                )
            else:
                placement = self._try_place_section(
                    i,
                    section_width,
                    spec.shelves,
                    remaining_regions,
                    zones,
                    wall_height,
                    current_x,
                    preferred_modes=[height_mode],
                )

            if placement:
                placed_sections.append(placement)
                current_x = placement.bounds.right
                # Update remaining regions
                remaining_regions = self._consume_region(
                    remaining_regions, placement.bounds
                )
            else:
                # Try splitting around obstacles
                split_placements = self._try_split_section(
                    i,
                    section_width,
                    spec.shelves,
                    remaining_regions,
                    zones,
                    wall_height,
                    current_x,
                )
                if split_placements:
                    placed_sections.extend(split_placements)
                    for p in split_placements:
                        current_x = max(current_x, p.bounds.right)
                        remaining_regions = self._consume_region(
                            remaining_regions, p.bounds
                        )
                    warnings.append(
                        LayoutWarning(
                            message=f"Section {i} was split into {len(split_placements)} parts to avoid obstacles",
                            suggestion=None,
                        )
                    )
                else:
                    # Skip this section
                    skipped_areas.append(
                        SkippedArea(
                            bounds=SectionBounds(
                                left=current_x,
                                right=current_x + section_width,
                                bottom=0,
                                top=wall_height,
                            ),
                            reason=f"Section {i} cannot fit: blocked by obstacles",
                        )
                    )
                    warnings.append(
                        LayoutWarning(
                            message=f"Section {i} skipped: cannot fit around obstacles",
                            suggestion="Consider using height_mode='lower' or 'upper' for partial-height sections",
                        )
                    )

        return LayoutResult(
            placed_sections=placed_sections,
            warnings=warnings,
            skipped_areas=skipped_areas,
        )

    def _resolve_width(
        self,
        spec: SectionSpec,
        wall_length: float,
        current_x: float,
        remaining_regions: list[ValidRegion],
    ) -> float:
        """Resolve 'fill' width to actual width.

        Args:
            spec: The section specification.
            wall_length: Total wall length.
            current_x: Current x position along the wall.
            remaining_regions: List of available regions.

        Returns:
            The resolved width for the section.
        """
        if spec.width == "fill":
            # Fill remaining space in current full-height regions
            available = wall_length - current_x
            for region in remaining_regions:
                if (
                    region.region_type == "full"
                    and region.left <= current_x < region.right
                ):
                    available = region.right - current_x
                    break
            return max(available, self.min_section_width)
        return float(spec.width)

    def _try_place_section(
        self,
        section_index: int,
        width: float,
        shelves: int,
        regions: list[ValidRegion],
        zones: list[ObstacleZone],
        wall_height: float,
        current_x: float,
        preferred_modes: list[str],
    ) -> PlacedSection | None:
        """Try to place a section in available regions.

        Args:
            section_index: Index of the section being placed.
            width: Requested width of the section.
            shelves: Number of shelves for the section.
            regions: Available regions for placement.
            zones: Obstacle zones to avoid.
            wall_height: Total wall height.
            current_x: Current x position along the wall.
            preferred_modes: List of height modes to try, in order of preference.

        Returns:
            PlacedSection if placement succeeded, None otherwise.
        """
        for mode in preferred_modes:
            # Sort regions to prefer those starting at or after current_x
            sorted_regions = sorted(
                regions, key=lambda r: (0 if r.left >= current_x else 1, r.left)
            )

            for region in sorted_regions:
                if not self._mode_matches_region(mode, region):
                    continue

                if region.width >= width:
                    # Determine the left position for this placement
                    left = max(region.left, current_x) if region.left < current_x else region.left

                    # Check if there's enough width from this starting position
                    available_width = region.right - left
                    if available_width < width:
                        continue

                    # Check if this placement would collide
                    bounds = SectionBounds(
                        left=left,
                        right=left + width,
                        bottom=region.bottom,
                        top=region.top,
                    )

                    collisions = self.collision_service.check_collision(bounds, zones)
                    if not collisions:
                        return PlacedSection(
                            section_index=section_index,
                            bounds=bounds,
                            height_mode=mode if mode != "auto" else region.region_type,
                            shelves=shelves,
                        )
        return None

    def _mode_matches_region(self, mode: str, region: ValidRegion) -> bool:
        """Check if height mode matches region type.

        Args:
            mode: The requested height mode.
            region: The region to check.

        Returns:
            True if the mode matches the region type.
        """
        if mode == "full":
            return region.region_type == "full"
        if mode == "lower":
            return region.region_type in ("lower", "gap")
        if mode == "upper":
            return region.region_type in ("upper", "gap")
        return True  # auto matches any

    def _try_split_section(
        self,
        section_index: int,
        original_width: float,
        shelves: int,
        regions: list[ValidRegion],
        zones: list[ObstacleZone],
        wall_height: float,
        current_x: float,
    ) -> list[PlacedSection]:
        """Try to split a section around obstacles.

        Args:
            section_index: Index of the section being split.
            original_width: Original requested width of the section.
            shelves: Number of shelves for the section.
            regions: Available regions for placement.
            zones: Obstacle zones to avoid.
            wall_height: Total wall height.
            current_x: Current x position along the wall.

        Returns:
            List of PlacedSection objects representing the split parts,
            or empty list if splitting is not possible.
        """
        placements: list[PlacedSection] = []
        remaining_width = original_width

        # Sort regions by left position, preferring those at or after current_x
        sorted_regions = sorted(
            [r for r in regions if r.left >= current_x or r.right > current_x],
            key=lambda r: r.left,
        )

        for region in sorted_regions:
            if remaining_width < self.min_section_width:
                break

            # Determine starting position in this region
            start_x = max(region.left, current_x)
            available_in_region = region.right - start_x

            if available_in_region >= self.min_section_width:
                # Take as much as we can from this region
                take_width = min(remaining_width, available_in_region)
                if take_width >= self.min_section_width:
                    bounds = SectionBounds(
                        left=start_x,
                        right=start_x + take_width,
                        bottom=region.bottom,
                        top=region.top,
                    )

                    collisions = self.collision_service.check_collision(bounds, zones)
                    if not collisions:
                        # Distribute shelves proportionally
                        proportion = take_width / original_width
                        section_shelves = max(1, int(shelves * proportion))

                        placements.append(
                            PlacedSection(
                                section_index=section_index,
                                bounds=bounds,
                                height_mode=region.region_type,
                                shelves=section_shelves,
                            )
                        )
                        remaining_width -= take_width

        return placements if placements else []

    def _consume_region(
        self,
        regions: list[ValidRegion],
        consumed: SectionBounds,
    ) -> list[ValidRegion]:
        """Update regions after placing a section.

        Args:
            regions: Current list of available regions.
            consumed: The bounds of the placed section.

        Returns:
            Updated list of regions with the consumed area removed.
        """
        new_regions: list[ValidRegion] = []
        for region in regions:
            # If this region doesn't overlap with consumed, keep it
            if consumed.right <= region.left or consumed.left >= region.right:
                new_regions.append(region)
            elif consumed.bottom >= region.top or consumed.top <= region.bottom:
                # No vertical overlap
                new_regions.append(region)
            else:
                # Split the region if there's remaining space
                if consumed.left > region.left:
                    # Left portion remains
                    left_width = consumed.left - region.left
                    if left_width >= self.min_section_width:
                        new_regions.append(
                            ValidRegion(
                                left=region.left,
                                right=consumed.left,
                                bottom=region.bottom,
                                top=region.top,
                                region_type=region.region_type,
                            )
                        )
                if consumed.right < region.right:
                    # Right portion remains
                    right_width = region.right - consumed.right
                    if right_width >= self.min_section_width:
                        new_regions.append(
                            ValidRegion(
                                left=consumed.right,
                                right=region.right,
                                bottom=region.bottom,
                                top=region.top,
                                region_type=region.region_type,
                            )
                        )
        return new_regions
