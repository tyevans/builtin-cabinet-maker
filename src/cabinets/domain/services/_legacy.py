"""Domain services for cabinet layout and calculations."""

from dataclasses import dataclass
import math

__all__ = [
    # Layout and generation
    "LayoutParameters",
    "LayoutCalculator",
    "CutListGenerator",
    "MaterialEstimate",
    "MaterialEstimator",
    "Panel3DMapper",
    # Room-aware layout
    "RoomLayoutService",
    "RoomPanel3DMapper",
    # Obstacle handling
    "ObstacleCollisionService",
    "ObstacleAwareLayoutService",
    # FRD-11 Advanced geometry
    "SlopedCeilingService",
    "SkylightVoidService",
    "OutsideCornerService",
]

from ..components import ComponentContext, component_registry
from ..components.corner import (
    CornerFootprint,
    calculate_blind_corner_footprint,
    calculate_diagonal_footprint,
    calculate_lazy_susan_footprint,
)
from ..components.results import HardwareItem
from ..entities import Cabinet, Obstacle, Panel, Room, Section, Shelf, Wall, WallSegment
from ..section_resolver import (
    RowSpec,
    SectionRowSpec,
    SectionSpec,
    SectionWidthError,
    resolve_row_heights,
    resolve_section_row_heights,
    resolve_section_widths,
)
from ..value_objects import (
    AngleCut,
    BoundingBox3D,
    CeilingSlope,
    Clearance,
    CollisionResult,
    CornerSectionAssignment,
    CornerType,
    CutPiece,
    DEFAULT_CLEARANCES,
    FitError,
    LayoutResult,
    LayoutWarning,
    MaterialSpec,
    NotchSpec,
    ObstacleType,
    ObstacleZone,
    OutsideCornerConfig,
    PanelType,
    PlacedSection,
    Position,
    Position3D,
    SectionBounds,
    SectionTransform,
    SectionType,
    SkippedArea,
    Skylight,
    TaperSpec,
    ValidRegion,
    WallSectionAssignment,
    WallSpaceReservation,
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
            self.back_material = MaterialSpec.standard_1_4()
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
        default_shelf_count: int = 0,
        zone_configs: dict[str, dict | None] | None = None,
    ) -> tuple[Cabinet, list[HardwareItem]]:
        """Generate a cabinet layout with specified section widths and shelf counts.

        This method provides more control over cabinet layout by allowing:
        - Fixed or "fill" widths for each section
        - Different shelf counts per section
        - Per-section depth overrides
        - Default shelf count for sections that don't specify
        - Zone configurations for toe kick, crown molding, and light rail

        The section_specs list defines each section's width and shelf count.
        Widths can be fixed numbers or "fill" to auto-calculate remaining space.

        Components are looked up from the component registry based on section type.
        Currently, all section types map to "shelf.fixed" until additional
        components (doors, drawers, cubbies) are implemented.

        Args:
            wall: Wall dimensions constraining the cabinet.
            params: Layout parameters (material specs are used from here).
            section_specs: List of section specifications with widths and shelf counts.
            default_shelf_count: Default number of shelves for sections with shelves=0.
                                 Only used when spec.shelves is 0 and this is > 0.
            zone_configs: Optional dict with zone configurations:
                          - base_zone: Toe kick zone config
                          - crown_molding: Crown molding zone config
                          - light_rail: Light rail zone config

        Returns:
            A tuple of (Cabinet, list[HardwareItem]) containing the cabinet entity
            with the generated layout and a list of all hardware items needed.

        Raises:
            ValueError: If a section's depth override exceeds the cabinet depth.
            SectionWidthError: If component validation fails.

        Example:
            >>> specs = [
            ...     SectionSpec(width=24.0, shelves=3),
            ...     SectionSpec(width="fill", shelves=5),
            ... ]
            >>> cabinet, hardware = calculator.generate_cabinet_from_specs(wall, params, specs)
        """
        zones = zone_configs or {}
        cabinet = Cabinet(
            width=wall.width,
            height=wall.height,
            depth=wall.depth,
            material=params.material,
            back_material=params.back_material,
            default_shelf_count=default_shelf_count,
            base_zone=zones.get("base_zone"),
            crown_molding=zones.get("crown_molding"),
            light_rail=zones.get("light_rail"),
        )

        # Collect hardware from all components
        all_hardware: list[HardwareItem] = []

        # Resolve section widths using the section resolver
        resolved_widths = resolve_section_widths(
            specs=section_specs,
            total_width=wall.width,
            material_thickness=params.material.thickness,
        )

        # Create sections with their specified widths and shelf counts
        current_x = params.material.thickness  # Start after left side panel

        for i, (spec, section_width) in enumerate(zip(section_specs, resolved_widths)):
            # Determine section depth: use spec.depth if set, otherwise use cabinet interior depth
            if spec.depth is not None:
                # Validate that section depth doesn't exceed cabinet depth
                if spec.depth > wall.depth:
                    raise ValueError(
                        f"Section {i} depth ({spec.depth}\") exceeds cabinet depth ({wall.depth}\")"
                    )
                # Use the minimum of spec depth and cabinet interior depth
                section_depth = min(spec.depth, cabinet.interior_depth)
            else:
                section_depth = cabinet.interior_depth

            # Handle sections with nested rows (vertical stacking)
            if spec.has_rows:
                section, hardware = self._generate_section_with_rows(
                    spec=spec,
                    section_width=section_width,
                    section_height=cabinet.interior_height,
                    section_depth=section_depth,
                    x_offset=current_x,
                    y_offset=params.material.thickness,
                    params=params,
                    section_index=i,
                    default_shelf_count=default_shelf_count,
                )
                cabinet.sections.append(section)
                all_hardware.extend(hardware)
                current_x += section_width + params.material.thickness
                continue

            # Determine shelf count: use spec.shelves if > 0, otherwise use default_shelf_count
            shelf_count = spec.shelves if spec.shelves > 0 else default_shelf_count

            section = Section(
                width=section_width,
                height=cabinet.interior_height,
                depth=section_depth,
                position=Position(current_x, params.material.thickness),
                section_type=spec.section_type,
            )

            # Build component context (shared for all component calls)
            context = ComponentContext(
                width=section_width,
                height=cabinet.interior_height,
                depth=section_depth,
                material=params.material,
                position=Position(current_x, params.material.thickness),
                section_index=i,
                cabinet_width=cabinet.width,
                cabinet_height=cabinet.height,
                cabinet_depth=cabinet.depth,
            )

            # Generate primary component based on section type or explicit override
            primary_component_id = spec.component_config.get(
                "component", self._resolve_component_id(spec.section_type)
            )

            if shelf_count > 0 or primary_component_id.startswith("door.") or primary_component_id.startswith("drawer."):
                component_class = component_registry.get(primary_component_id)
                component = component_class()

                # Build component config by merging spec.component_config with defaults
                # For shelf components, pass shelf_count as "count"
                # For drawer/door components, use their own config
                if primary_component_id.startswith("shelf."):
                    component_config = {"count": shelf_count, **spec.component_config}
                else:
                    component_config = dict(spec.component_config)

                # Validate
                validation = component.validate(component_config, context)
                if not validation.is_valid:
                    raise SectionWidthError(", ".join(validation.errors))

                # Generate
                result = component.generate(component_config, context)

                # Add panels to section based on type
                for panel in result.panels:
                    if panel.panel_type == PanelType.SHELF:
                        # Convert SHELF panels back to Shelf entities
                        shelf = Shelf(
                            width=panel.width,
                            depth=panel.height,  # Panel height is shelf depth
                            material=panel.material,
                            position=panel.position,
                        )
                        section.add_shelf(shelf)
                    else:
                        # Add non-shelf panels (doors, drawer fronts, etc.) directly
                        section.add_panel(panel)

                # Collect hardware from component
                all_hardware.extend(result.hardware)

            # For doored sections, also generate shelves behind the doors
            if (
                spec.section_type == SectionType.DOORED
                and shelf_count > 0
                and primary_component_id.startswith("door.")
            ):
                shelf_component = component_registry.get("shelf.fixed")()
                shelf_config = {"count": shelf_count}
                shelf_result = shelf_component.generate(shelf_config, context)

                for panel in shelf_result.panels:
                    shelf = Shelf(
                        width=panel.width,
                        depth=panel.height,
                        material=panel.material,
                        position=panel.position,
                    )
                    section.add_shelf(shelf)

                all_hardware.extend(shelf_result.hardware)

            cabinet.sections.append(section)
            current_x += section_width + params.material.thickness

        return cabinet, all_hardware

    def generate_cabinet_from_row_specs(
        self,
        wall: Wall,
        params: LayoutParameters,
        row_specs: list[RowSpec],
        default_shelf_count: int = 0,
        zone_configs: dict[str, dict | None] | None = None,
    ) -> tuple[Cabinet, list[HardwareItem]]:
        """Generate a cabinet layout with vertically stacked rows.

        This method supports multi-row cabinets where each row has its own
        height and contains horizontally arranged sections. Rows are stacked
        from bottom to top.

        Each row's height can be fixed or "fill" to auto-calculate remaining space.
        Within each row, sections are laid out horizontally with their own
        width specifications (fixed or "fill").

        Horizontal dividers are generated between rows.

        Args:
            wall: Wall dimensions constraining the cabinet.
            params: Layout parameters (material specs are used from here).
            row_specs: List of row specifications with heights and section specs.
            default_shelf_count: Default number of shelves for sections with shelves=0.
            zone_configs: Optional dict with zone configurations:
                          - base_zone: Toe kick zone config
                          - crown_molding: Crown molding zone config
                          - light_rail: Light rail zone config

        Returns:
            A tuple of (Cabinet, list[HardwareItem]) containing the cabinet entity
            with the generated layout and a list of all hardware items needed.

        Raises:
            ValueError: If a section's depth override exceeds the cabinet depth.
            SectionWidthError: If component validation fails.
            RowHeightError: If row heights cannot be resolved.

        Example:
            >>> row_specs = [
            ...     RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
            ...     RowSpec(height="fill", section_specs=(SectionSpec(width="fill", shelves=4),)),
            ... ]
            >>> cabinet, hardware = calculator.generate_cabinet_from_row_specs(wall, params, row_specs)
        """
        # Resolve row heights
        resolved_heights = resolve_row_heights(
            row_specs=row_specs,
            total_height=wall.height,
            material_thickness=params.material.thickness,
        )

        zones = zone_configs or {}
        cabinet = Cabinet(
            width=wall.width,
            height=wall.height,
            depth=wall.depth,
            material=params.material,
            back_material=params.back_material,
            default_shelf_count=default_shelf_count,
            row_heights=resolved_heights,  # Store for horizontal divider generation
            base_zone=zones.get("base_zone"),
            crown_molding=zones.get("crown_molding"),
            light_rail=zones.get("light_rail"),
        )

        # Collect hardware from all components
        all_hardware: list[HardwareItem] = []

        # Process each row from bottom to top
        current_y = params.material.thickness  # Start at top of bottom panel

        for row_idx, (row_spec, row_height) in enumerate(zip(row_specs, resolved_heights)):
            # Resolve section widths for this row
            resolved_widths = resolve_section_widths(
                specs=list(row_spec.section_specs),
                total_width=wall.width,
                material_thickness=params.material.thickness,
            )

            # Create sections within this row
            current_x = params.material.thickness  # Start after left side panel

            for i, (spec, section_width) in enumerate(
                zip(row_spec.section_specs, resolved_widths)
            ):
                # Determine section depth
                if spec.depth is not None:
                    if spec.depth > wall.depth:
                        raise ValueError(
                            f"Row {row_idx} Section {i} depth ({spec.depth}\") "
                            f"exceeds cabinet depth ({wall.depth}\")"
                        )
                    section_depth = min(spec.depth, cabinet.interior_depth)
                else:
                    section_depth = cabinet.interior_depth

                # Determine shelf count
                shelf_count = spec.shelves if spec.shelves > 0 else default_shelf_count

                section = Section(
                    width=section_width,
                    height=row_height,  # Use row height, not cabinet interior height
                    depth=section_depth,
                    position=Position(current_x, current_y),
                    section_type=spec.section_type,
                )

                # Build component context
                context = ComponentContext(
                    width=section_width,
                    height=row_height,
                    depth=section_depth,
                    material=params.material,
                    position=Position(current_x, current_y),
                    section_index=i,
                    cabinet_width=cabinet.width,
                    cabinet_height=cabinet.height,
                    cabinet_depth=cabinet.depth,
                )

                # Generate primary component based on section type
                primary_component_id = spec.component_config.get(
                    "component", self._resolve_component_id(spec.section_type)
                )

                if (
                    shelf_count > 0
                    or primary_component_id.startswith("door.")
                    or primary_component_id.startswith("drawer.")
                    or primary_component_id.startswith("cubby.")
                ):
                    component_class = component_registry.get(primary_component_id)
                    component = component_class()

                    # For shelf components, pass shelf_count as "count"
                    # For drawer/door/cubby components, use their own config
                    if primary_component_id.startswith("shelf."):
                        component_config = {"count": shelf_count, **spec.component_config}
                    else:
                        component_config = dict(spec.component_config)

                    validation = component.validate(component_config, context)
                    if not validation.is_valid:
                        raise SectionWidthError(", ".join(validation.errors))

                    result = component.generate(component_config, context)

                    for panel in result.panels:
                        if panel.panel_type == PanelType.SHELF:
                            shelf = Shelf(
                                width=panel.width,
                                depth=panel.height,
                                material=panel.material,
                                position=panel.position,
                            )
                            section.add_shelf(shelf)
                        else:
                            section.add_panel(panel)

                    all_hardware.extend(result.hardware)

                # For doored sections, also generate shelves behind the doors
                if (
                    spec.section_type == SectionType.DOORED
                    and shelf_count > 0
                    and primary_component_id.startswith("door.")
                ):
                    shelf_component = component_registry.get("shelf.fixed")()
                    shelf_config = {"count": shelf_count}
                    shelf_result = shelf_component.generate(shelf_config, context)

                    for panel in shelf_result.panels:
                        shelf = Shelf(
                            width=panel.width,
                            depth=panel.height,
                            material=panel.material,
                            position=panel.position,
                        )
                        section.add_shelf(shelf)

                    all_hardware.extend(shelf_result.hardware)

                cabinet.sections.append(section)
                current_x += section_width + params.material.thickness

            # Move to next row (add row height + horizontal divider thickness)
            current_y += row_height + params.material.thickness

        return cabinet, all_hardware

    def _generate_section_with_rows(
        self,
        spec: SectionSpec,
        section_width: float,
        section_height: float,
        section_depth: float,
        x_offset: float,
        y_offset: float,
        params: LayoutParameters,
        section_index: int,
        default_shelf_count: int,
    ) -> tuple[Section, list[HardwareItem]]:
        """Generate a section with vertically stacked rows.

        This method handles sections that have nested rows for vertical stacking
        (e.g., drawers on bottom, shelves on top).

        Args:
            spec: The section specification with row_specs.
            section_width: Resolved width of this section.
            section_height: Interior height available for this section.
            section_depth: Depth of this section.
            x_offset: X position of this section.
            y_offset: Y position (bottom) of this section.
            params: Layout parameters (material specs).
            section_index: Index of this section in the cabinet.
            default_shelf_count: Default shelves for rows with shelves=0.

        Returns:
            A tuple of (Section, list[HardwareItem]) containing the section entity
            and all hardware items needed.
        """
        assert spec.row_specs is not None, "Section must have row_specs"

        # Create the container section
        section = Section(
            width=section_width,
            height=section_height,
            depth=section_depth,
            position=Position(x_offset, y_offset),
            section_type=SectionType.OPEN,  # Container is open; rows define their types
        )

        all_hardware: list[HardwareItem] = []

        # Resolve row heights within this section
        resolved_heights = resolve_section_row_heights(
            row_specs=list(spec.row_specs),
            section_height=section_height,
            material_thickness=params.material.thickness,
        )

        # Generate components for each row
        current_y = y_offset  # Start at section bottom

        for row_idx, (row_spec, row_height) in enumerate(
            zip(spec.row_specs, resolved_heights)
        ):
            # Determine shelf count for this row
            shelf_count = (
                row_spec.shelves if row_spec.shelves > 0 else default_shelf_count
            )

            # Build component context for this row
            context = ComponentContext(
                width=section_width,
                height=row_height,
                depth=section_depth,
                material=params.material,
                position=Position(x_offset, current_y),
                section_index=section_index,
                cabinet_width=section_width,  # Within section context
                cabinet_height=section_height,
                cabinet_depth=section_depth,
            )

            # Generate primary component based on row's section type
            primary_component_id = row_spec.component_config.get(
                "component", self._resolve_component_id(row_spec.section_type)
            )

            if (
                shelf_count > 0
                or primary_component_id.startswith("door.")
                or primary_component_id.startswith("drawer.")
                or primary_component_id.startswith("cubby.")
            ):
                component_class = component_registry.get(primary_component_id)
                component = component_class()

                # Build component config
                if primary_component_id.startswith("shelf."):
                    component_config = {"count": shelf_count, **row_spec.component_config}
                else:
                    component_config = dict(row_spec.component_config)

                # Validate
                validation = component.validate(component_config, context)
                if not validation.is_valid:
                    raise SectionWidthError(", ".join(validation.errors))

                # Generate
                result = component.generate(component_config, context)

                # Add panels to section
                for panel in result.panels:
                    if panel.panel_type == PanelType.SHELF:
                        shelf = Shelf(
                            width=panel.width,
                            depth=panel.height,  # Panel height is shelf depth
                            material=panel.material,
                            position=panel.position,
                        )
                        section.add_shelf(shelf)
                    else:
                        section.add_panel(panel)

                all_hardware.extend(result.hardware)

            # For doored rows, also generate shelves behind the doors
            if (
                row_spec.section_type == SectionType.DOORED
                and shelf_count > 0
                and primary_component_id.startswith("door.")
            ):
                shelf_component = component_registry.get("shelf.fixed")()
                shelf_config = {"count": shelf_count}
                shelf_result = shelf_component.generate(shelf_config, context)

                for panel in shelf_result.panels:
                    shelf = Shelf(
                        width=panel.width,
                        depth=panel.height,
                        material=panel.material,
                        position=panel.position,
                    )
                    section.add_shelf(shelf)

                all_hardware.extend(shelf_result.hardware)

            # Add horizontal divider between rows (except for last row)
            if row_idx < len(spec.row_specs) - 1:
                divider = Panel(
                    width=section_width,
                    height=section_depth,  # Panel height = section depth
                    material=params.material,
                    position=Position(x_offset, current_y + row_height),
                    panel_type=PanelType.HORIZONTAL_DIVIDER,
                )
                section.add_panel(divider)

            # Move to next row (add row height + horizontal divider thickness)
            current_y += row_height + params.material.thickness

        return section, all_hardware

    def _resolve_component_id(self, section_type: SectionType) -> str:
        """Map section type to default component ID.

        Currently, all section types map to "shelf.fixed" until additional
        components (doors, drawers, cubbies) are implemented.

        Args:
            section_type: The type of cabinet section.

        Returns:
            The component ID to use for generating this section's contents.
        """
        mapping = {
            SectionType.OPEN: "shelf.fixed",
            SectionType.DOORED: "door.hinged.overlay",
            SectionType.DRAWERS: "drawer.standard",
            SectionType.CUBBY: "cubby.uniform",
        }
        return mapping.get(section_type, "shelf.fixed")


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
                # Using a reference box thickness of 0.5" for standard drawer sides
                box_side_thickness = 0.5
                box_front_y = self.cabinet.depth - self.material_thickness - box_side_thickness
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
                # panel.height is the nailer depth (how far it extends from back)
                return BoundingBox3D(
                    origin=Position3D(
                        x=0,
                        y=self.back_thickness,  # Just in front of back panel
                        z=self.cabinet.height - thickness,  # At top of cabinet
                    ),
                    size_x=panel.width,
                    size_y=panel.height,  # Nailer depth
                    size_z=thickness,
                )

            case PanelType.LIGHT_RAIL:
                # Vertical strip at bottom front for light concealment
                setback = panel.metadata.get("setback", 0.25) if panel.metadata else 0.25
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

            # --- Desk panels (FRD-18) ---

            case PanelType.DESKTOP:
                # Horizontal panel at desk height
                desk_height = panel.metadata.get("desk_height", 30.0) if panel.metadata else 30.0
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
                chase_depth = thickness  # Use panel thickness (typically 0.25")
                return BoundingBox3D(
                    origin=Position3D(
                        x=panel.position.x,
                        y=self.cabinet.depth - chase_depth,  # At rear of cabinet
                        z=panel.position.y,  # Vertical position (bottom of chase)
                    ),
                    size_x=panel.width,  # Chase width (typically 3-4")
                    size_y=chase_depth,  # Thin panel representation
                    size_z=panel.height,  # Full section/cabinet height
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
        panels = self.cabinet.get_all_panels()
        return [self.map_panel(panel) for panel in panels]

    def map_all_panels_with_types(self) -> list[tuple[BoundingBox3D, Panel]]:
        """Convert all cabinet panels to 3D bounding boxes with panel info.

        Returns a list of tuples containing the bounding box and the original
        panel. This allows consumers to check panel types (e.g., for rendering
        doors differently than other panels).

        Returns:
            List of (BoundingBox3D, Panel) tuples for all cabinet panels.
        """
        panels = self.cabinet.get_all_panels()
        return [(self.map_panel(panel), panel) for panel in panels]


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

        # Build wall name to index mapping for width resolution
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Pre-compute section widths per wall for fill sections
        wall_section_widths = self._compute_section_widths_per_wall(
            room, section_specs, wall_name_to_index
        )

        # First pass: compute raw positions (may be negative)
        raw_positions: list[tuple[float, float, float, float]] = []  # (x, y, z, rotation)

        for assignment in assignments:
            wall_pos = wall_positions[assignment.wall_index]

            # Calculate position along the wall
            direction_rad = math.radians(wall_pos.direction)

            # Calculate X, Y position based on wall start and offset along wall
            x = wall_pos.start.x + assignment.offset_along_wall * math.cos(direction_rad)
            y = wall_pos.start.y + assignment.offset_along_wall * math.sin(direction_rad)

            # Z position starts at floor level
            z = 0.0

            # Rotation is based on wall direction
            # Wall direction is the angle the wall runs along.
            # Cabinet back is at y=0, front at y=depth (facing +Y originally).
            # To face "into the room" (perpendicular to wall, toward interior),
            # we negate the direction so the cabinet rotates the opposite way.
            rotation_z = (-wall_pos.direction) % 360

            raw_positions.append((x, y, z, rotation_z))

        # Second pass: create transforms, mirroring negative coordinates to positive
        # This keeps the origin at (0,0) and flips negative positions to positive space
        transforms: list[SectionTransform] = []
        for assignment, (x, y, z, rotation_z) in zip(assignments, raw_positions):
            # Mirror negative coordinates to positive (abs value)
            final_x = abs(x)
            final_y = abs(y)
            position = Position3D(x=final_x, y=final_y, z=z)

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

    def detect_corner_sections(
        self,
        section_specs: list[SectionSpec],
    ) -> list[tuple[int, str]]:
        """Detect which sections are corner components.

        A section is a corner component if its component_config contains a
        'component' key that starts with 'corner.' (e.g., 'corner.lazy_susan',
        'corner.diagonal', 'corner.blind').

        Args:
            section_specs: List of section specifications.

        Returns:
            List of tuples (section_index, corner_component_id) for each
            corner section detected.
        """
        corners: list[tuple[int, str]] = []
        for idx, spec in enumerate(section_specs):
            component_id = spec.component_config.get("component", "")
            if isinstance(component_id, str) and component_id.startswith("corner."):
                corners.append((idx, component_id))
        return corners

    def find_wall_corners(
        self,
        room: Room,
    ) -> list[tuple[int, int, int]]:
        """Find corners between adjacent walls.

        A corner exists when one wall's angle is 90 (right turn) or -90 (left turn).
        The corner is at the junction between that wall and the previous wall.

        For a right turn (angle=90), when facing the corner:
        - Left wall is the wall before the turn (current wall index - 1)
        - Right wall is the wall at the turn (current wall index)

        For a left turn (angle=-90), the orientation is reversed.

        Args:
            room: The room containing wall segments.

        Returns:
            List of tuples (left_wall_index, right_wall_index, angle) for each
            corner detected. The angle is 90 or -90 indicating turn direction.
        """
        corners: list[tuple[int, int, int]] = []

        for i, wall in enumerate(room.walls):
            if wall.angle in (90, -90):
                # Wall with angle != 0 creates a corner with the previous wall
                # For wall[i] with angle 90 or -90, the corner is between
                # wall[i-1] (ends at corner) and wall[i] (starts at corner)
                left_wall_idx = (i - 1) % len(room.walls)
                right_wall_idx = i
                corners.append((left_wall_idx, right_wall_idx, int(wall.angle)))

        return corners

    def calculate_corner_footprint(
        self,
        component_id: str,
        component_config: dict,
        depth: float,
    ) -> CornerFootprint:
        """Calculate the footprint for a corner component.

        Uses the appropriate footprint calculation function based on the
        corner type extracted from the component_id.

        Args:
            component_id: The component ID (e.g., 'corner.lazy_susan').
            component_config: The component configuration dictionary.
            depth: The cabinet depth in inches.

        Returns:
            CornerFootprint with left and right wall consumption.

        Raises:
            ValueError: If the corner type is unknown.
        """
        if component_id == "corner.lazy_susan":
            door_clearance = component_config.get("door_clearance", 2.0)
            return calculate_lazy_susan_footprint(depth, door_clearance)

        elif component_id == "corner.diagonal":
            return calculate_diagonal_footprint(depth)

        elif component_id == "corner.blind":
            accessible_width = component_config.get("accessible_width", 24.0)
            filler_width = component_config.get("filler_width", 3.0)
            blind_side = component_config.get("blind_side", "left")
            return calculate_blind_corner_footprint(
                depth, accessible_width, filler_width, blind_side
            )

        else:
            raise ValueError(f"Unknown corner component type: {component_id}")

    def get_corner_type(self, component_id: str) -> CornerType:
        """Map component ID to CornerType enum.

        Args:
            component_id: The component ID (e.g., 'corner.lazy_susan').

        Returns:
            The corresponding CornerType enum value.

        Raises:
            ValueError: If the corner type is unknown.
        """
        mapping = {
            "corner.lazy_susan": CornerType.LAZY_SUSAN,
            "corner.diagonal": CornerType.DIAGONAL,
            "corner.blind": CornerType.BLIND,
        }
        if component_id not in mapping:
            raise ValueError(f"Unknown corner component type: {component_id}")
        return mapping[component_id]

    def assign_corner_sections(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        default_depth: float = 24.0,
    ) -> tuple[list[CornerSectionAssignment], list[WallSpaceReservation]]:
        """Assign corner sections to wall junctions and calculate reservations.

        This method:
        1. Detects which sections are corner components
        2. Finds corners between walls in the room
        3. Matches corner sections to wall corners based on the 'wall' attribute
        4. Calculates footprints and creates space reservations

        For corner placement, the section's 'wall' attribute indicates which wall
        junction to use. If a section specifies wall N, and wall N has a corner
        (angle 90 or -90), the corner cabinet is placed at that junction.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications.
            default_depth: Default cabinet depth if not specified.

        Returns:
            A tuple of:
            - List of CornerSectionAssignment for corner sections
            - List of WallSpaceReservation for space consumed on each wall
        """
        corner_sections = self.detect_corner_sections(section_specs)
        if not corner_sections:
            return [], []

        wall_corners = self.find_wall_corners(room)
        if not wall_corners:
            return [], []

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        assignments: list[CornerSectionAssignment] = []
        reservations: list[WallSpaceReservation] = []

        for section_idx, component_id in corner_sections:
            spec = section_specs[section_idx]

            # Resolve which wall the section is assigned to
            try:
                wall_idx = self._resolve_wall_index(
                    spec.wall, len(room.walls), wall_name_to_index
                )
            except ValueError:
                continue

            # Find if this wall has a corner (is the right wall of a corner)
            corner_info = None
            for left_wall, right_wall, angle in wall_corners:
                if right_wall == wall_idx:
                    corner_info = (left_wall, right_wall, angle)
                    break

            if corner_info is None:
                # No corner at this wall junction, skip
                continue

            left_wall_idx, right_wall_idx, angle = corner_info

            # Get depth from spec or default
            depth = spec.depth if spec.depth is not None else default_depth

            # Calculate footprint
            footprint = self.calculate_corner_footprint(
                component_id, spec.component_config, depth
            )

            # Determine left/right wall footprint based on angle
            # For angle 90 (right turn), the standard orientation applies
            # For angle -90 (left turn), swap left and right
            if angle == 90:
                left_fp = footprint.left_wall
                right_fp = footprint.right_wall
            else:  # angle == -90
                left_fp = footprint.right_wall
                right_fp = footprint.left_wall

            # Get wall lengths for offset calculation
            left_wall_length = room.walls[left_wall_idx].length
            right_wall_length = room.walls[right_wall_idx].length

            # Corner is at the END of left wall and START of right wall
            left_wall_offset = left_wall_length - left_fp
            right_wall_offset = 0.0

            # Create assignment
            assignment = CornerSectionAssignment(
                section_index=section_idx,
                left_wall_index=left_wall_idx,
                right_wall_index=right_wall_idx,
                left_wall_footprint=left_fp,
                right_wall_footprint=right_fp,
                corner_type=self.get_corner_type(component_id),
                at_wall_end=True,
                left_wall_offset=left_wall_offset,
                right_wall_offset=right_wall_offset,
            )
            assignments.append(assignment)

            # Create reservations for both walls
            # Left wall: reserved space at the end
            reservations.append(
                WallSpaceReservation(
                    wall_index=left_wall_idx,
                    start_offset=left_wall_offset,
                    end_offset=left_wall_length,
                    reserved_by_section=section_idx,
                    is_corner_start=False,
                    is_corner_end=True,
                )
            )

            # Right wall: reserved space at the start
            reservations.append(
                WallSpaceReservation(
                    wall_index=right_wall_idx,
                    start_offset=0.0,
                    end_offset=right_fp,
                    reserved_by_section=section_idx,
                    is_corner_start=True,
                    is_corner_end=False,
                )
            )

        return assignments, reservations

    def assign_sections_to_walls_with_corners(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        default_depth: float = 24.0,
    ) -> tuple[
        list[WallSectionAssignment],
        list[CornerSectionAssignment],
        list[WallSpaceReservation],
    ]:
        """Assign sections to walls, handling corner cabinets specially.

        This method extends assign_sections_to_walls to handle corner cabinets
        that span two walls. Corner sections are assigned first, reserving space
        on both walls they occupy. Regular sections are then assigned to the
        remaining available space.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications.
            default_depth: Default cabinet depth for corner calculations.

        Returns:
            A tuple of:
            - List of WallSectionAssignment for regular sections
            - List of CornerSectionAssignment for corner sections
            - List of WallSpaceReservation for corner-reserved space
        """
        if not section_specs:
            return [], [], []

        # First, handle corner sections
        corner_assignments, reservations = self.assign_corner_sections(
            room, section_specs, default_depth
        )

        # Build a set of section indices that are corners
        corner_section_indices = {ca.section_index for ca in corner_assignments}

        # Build wall name to index mapping
        wall_name_to_index: dict[str, int] = {}
        for i, wall in enumerate(room.walls):
            if wall.name is not None:
                wall_name_to_index[wall.name] = i

        # Build reservation lookup: wall_index -> list of reservations
        wall_reservations: dict[int, list[WallSpaceReservation]] = {}
        for res in reservations:
            if res.wall_index not in wall_reservations:
                wall_reservations[res.wall_index] = []
            wall_reservations[res.wall_index].append(res)

        # Group non-corner sections by wall index
        wall_sections: dict[int, list[tuple[int, SectionSpec]]] = {}
        for section_idx, spec in enumerate(section_specs):
            if section_idx in corner_section_indices:
                continue  # Skip corner sections

            wall_idx = self._resolve_wall_index(
                spec.wall, len(room.walls), wall_name_to_index
            )
            if wall_idx not in wall_sections:
                wall_sections[wall_idx] = []
            wall_sections[wall_idx].append((section_idx, spec))

        # Calculate available space per wall after corner reservations
        def get_available_start(wall_idx: int) -> float:
            """Get the starting offset after any corner-start reservations."""
            if wall_idx not in wall_reservations:
                return 0.0
            for res in wall_reservations[wall_idx]:
                if res.is_corner_start:
                    return res.end_offset
            return 0.0

        def get_available_end(wall_idx: int) -> float:
            """Get the ending offset before any corner-end reservations."""
            wall_length = room.walls[wall_idx].length
            if wall_idx not in wall_reservations:
                return wall_length
            for res in wall_reservations[wall_idx]:
                if res.is_corner_end:
                    return res.start_offset
            return wall_length

        # Create assignments with sequential offsets per wall, respecting reservations
        assignments: list[WallSectionAssignment] = []

        for wall_idx, sections in wall_sections.items():
            available_start = get_available_start(wall_idx)
            available_end = get_available_end(wall_idx)
            available_length = available_end - available_start

            current_offset = available_start

            for section_idx, spec in sections:
                # For fixed width sections, use the width directly
                # For fill sections, calculate based on available space
                if spec.is_fill:
                    fixed_widths = sum(
                        s.fixed_width or 0.0
                        for _, s in sections
                        if not s.is_fill
                    )
                    fill_count = sum(1 for _, s in sections if s.is_fill)
                    remaining = available_length - fixed_widths
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

        return assignments, corner_assignments, reservations

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


@dataclass
class SlopedCeilingService:
    """Calculates section heights and generates tapered panels for sloped ceilings.

    This service handles the geometry calculations needed for cabinets installed
    under sloped ceilings, such as in attic spaces or vaulted ceiling areas.
    It determines the appropriate height for each cabinet section based on its
    position along the slope and generates taper specifications for top panels.
    """

    def calculate_section_heights(
        self,
        section_widths: list[float],
        slope: CeilingSlope,
        wall_length: float,
    ) -> list[float]:
        """Calculate height for each section based on position along slope.

        Uses the midpoint of each section to determine its height along the
        slope. This provides a representative height for the section while
        avoiding edge cases at section boundaries.

        Args:
            section_widths: Width of each section in inches.
            slope: CeilingSlope definition specifying angle, start height, and direction.
            wall_length: Total wall length in inches.

        Returns:
            List of calculated heights for each section in inches.
        """
        heights = []
        current_position = 0.0

        for width in section_widths:
            # Use section midpoint for height calculation
            midpoint = current_position + width / 2

            # Calculate position based on direction
            if slope.direction == "right_to_left":
                position = wall_length - midpoint
            else:
                position = midpoint

            height = slope.height_at_position(position)

            # Clamp to minimum height
            if height < slope.min_height:
                height = slope.min_height

            heights.append(height)
            current_position += width

        return heights

    def calculate_section_edge_heights(
        self,
        section_x: float,
        section_width: float,
        slope: CeilingSlope,
        wall_length: float,
    ) -> tuple[float, float]:
        """Calculate left and right edge heights for a section.

        Determines the ceiling height at both edges of a section, which is
        needed to generate taper specifications for the top panel.

        Args:
            section_x: X position of section left edge in inches.
            section_width: Width of section in inches.
            slope: CeilingSlope definition.
            wall_length: Total wall length in inches.

        Returns:
            Tuple of (left_height, right_height) in inches.
        """
        left_x = section_x
        right_x = section_x + section_width

        if slope.direction == "right_to_left":
            left_pos = wall_length - left_x
            right_pos = wall_length - right_x
        else:
            left_pos = left_x
            right_pos = right_x

        left_height = max(slope.height_at_position(left_pos), slope.min_height)
        right_height = max(slope.height_at_position(right_pos), slope.min_height)

        return (left_height, right_height)

    def generate_taper_spec(
        self,
        section_x: float,
        section_width: float,
        slope: CeilingSlope,
        wall_length: float,
    ) -> TaperSpec | None:
        """Generate TaperSpec for a section under a sloped ceiling.

        Calculates whether a section requires a tapered top panel and, if so,
        generates the specification for that taper including start/end heights
        and direction.

        Args:
            section_x: X position of section left edge in inches.
            section_width: Width of section in inches.
            slope: CeilingSlope definition.
            wall_length: Total wall length in inches.

        Returns:
            TaperSpec if the section has non-uniform height (taper needed),
            None if the section has uniform height (no taper needed).
        """
        left_height, right_height = self.calculate_section_edge_heights(
            section_x, section_width, slope, wall_length
        )

        # No taper needed if heights are equal (within tolerance)
        if abs(left_height - right_height) < 0.001:
            return None

        # Determine taper direction based on which end is higher
        if left_height > right_height:
            direction = "left_to_right"
        else:
            direction = "right_to_left"

        return TaperSpec(
            start_height=max(left_height, right_height),
            end_height=min(left_height, right_height),
            direction=direction,
        )

    def check_min_height_violations(
        self,
        section_widths: list[float],
        slope: CeilingSlope,
        wall_length: float,
    ) -> list[tuple[int, float, float]]:
        """Check for sections that violate minimum height.

        Identifies any sections where the calculated height at the midpoint
        falls below the slope's minimum height threshold. This helps detect
        sections that would be too short to be usable.

        Args:
            section_widths: Width of each section in inches.
            slope: CeilingSlope definition.
            wall_length: Total wall length in inches.

        Returns:
            List of (section_index, calculated_height, min_height) tuples
            for each section that violates the minimum height requirement.
            Empty list if no violations are detected.
        """
        violations = []
        current_position = 0.0

        for i, width in enumerate(section_widths):
            midpoint = current_position + width / 2

            if slope.direction == "right_to_left":
                position = wall_length - midpoint
            else:
                position = midpoint

            height = slope.height_at_position(position)

            if height < slope.min_height:
                violations.append((i, height, slope.min_height))

            current_position += width

        return violations


@dataclass
class SkylightVoidService:
    """Calculates skylight void intersections with cabinet sections."""

    def calculate_void_intersection(
        self,
        skylight: Skylight,
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> NotchSpec | None:
        """Calculate notch needed for skylight void, if any.

        Args:
            skylight: Skylight definition
            section_x: X position of section left edge
            section_width: Width of section
            cabinet_depth: Depth of cabinet (for void projection calculation)

        Returns:
            NotchSpec if skylight intersects section, None otherwise
        """
        void_x, void_width = skylight.void_at_depth(cabinet_depth)
        void_end = void_x + void_width
        section_end = section_x + section_width

        # Check for intersection
        if void_end <= section_x or void_x >= section_end:
            return None  # No intersection

        # Calculate notch dimensions relative to section
        notch_x = max(0.0, void_x - section_x)
        notch_end = min(section_width, void_end - section_x)
        notch_width = notch_end - notch_x

        return NotchSpec(
            x_offset=notch_x,
            width=notch_width,
            depth=skylight.projection_depth,
            edge="top",
        )

    def calculate_all_intersections(
        self,
        skylights: list[Skylight],
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> list[NotchSpec]:
        """Calculate all notches needed for multiple skylights.

        Args:
            skylights: List of skylight definitions
            section_x: X position of section left edge
            section_width: Width of section
            cabinet_depth: Depth of cabinet

        Returns:
            List of NotchSpecs for all intersecting skylights
        """
        notches = []
        for skylight in skylights:
            notch = self.calculate_void_intersection(
                skylight, section_x, section_width, cabinet_depth
            )
            if notch is not None:
                notches.append(notch)
        return notches

    def get_sections_with_voids(
        self,
        skylights: list[Skylight],
        section_specs: list[tuple[float, float]],  # List of (x_position, width)
        cabinet_depth: float,
    ) -> dict[int, list[NotchSpec]]:
        """Map section indices to their required notches.

        Args:
            skylights: List of skylight definitions
            section_specs: List of (x_position, width) tuples for each section
            cabinet_depth: Depth of cabinet

        Returns:
            Dict mapping section index to list of NotchSpecs
        """
        result = {}
        for i, (section_x, section_width) in enumerate(section_specs):
            notches = self.calculate_all_intersections(
                skylights, section_x, section_width, cabinet_depth
            )
            if notches:
                result[i] = notches
        return result

    def check_void_exceeds_section(
        self,
        skylight: Skylight,
        section_x: float,
        section_width: float,
        cabinet_depth: float,
    ) -> bool:
        """Check if skylight void exceeds section width (warning condition).

        Returns True if the void width at cabinet depth exceeds section width.
        """
        void_x, void_width = skylight.void_at_depth(cabinet_depth)
        void_end = void_x + void_width
        section_end = section_x + section_width

        # Check if void completely contains section
        if void_x <= section_x and void_end >= section_end:
            return True
        return False


@dataclass
class OutsideCornerService:
    """Generates panels for outside (convex) corner treatments."""

    def is_outside_corner(self, wall_angle: float) -> bool:
        """Determine if an angle represents an outside corner.

        Outside corners occur when the absolute angle is greater than 90 degrees.

        Args:
            wall_angle: The wall junction angle in degrees.

        Returns:
            True if the angle represents an outside corner, False otherwise.
        """
        return abs(wall_angle) > 90

    def calculate_angled_face_panel(
        self,
        corner_config: OutsideCornerConfig,
        height: float,
        depth: float,
        material: MaterialSpec,
    ) -> Panel:
        """Generate an angled face panel for outside corner treatment.

        The angled face panel bridges the corner at the specified face_angle.

        Args:
            corner_config: Outside corner configuration with face_angle.
            height: Height of the panel in inches.
            depth: Depth of the cabinet in inches.
            material: Material specification for the panel.

        Returns:
            A Panel with DIAGONAL_FACE type and angle cut metadata.
        """
        from math import radians, tan

        # Calculate panel width based on depth and face angle
        # Width of angled panel is based on the gap created by the corner
        # For a 45-degree face, width = depth * 2 * tan(face_angle/2)
        panel_width = 2 * depth * tan(radians(corner_config.face_angle / 2))

        # Create cut metadata for the angled edges
        cut_metadata = {
            "angle_cuts": [
                {"edge": "left", "angle": corner_config.face_angle, "bevel": True},
                {"edge": "right", "angle": corner_config.face_angle, "bevel": True},
            ],
            "corner_treatment": "angled_face",
        }

        return Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=panel_width,
            height=height,
            material=material,
            cut_metadata=cut_metadata,
        )

    def calculate_filler_panel(
        self,
        corner_config: OutsideCornerConfig,
        height: float,
        material: MaterialSpec,
    ) -> Panel:
        """Generate a filler panel for butted_filler corner treatment.

        The filler panel is a simple rectangular panel with the specified width.

        Args:
            corner_config: Outside corner configuration with filler_width.
            height: Height of the panel in inches.
            material: Material specification for the panel.

        Returns:
            A Panel with FILLER type and butted_filler metadata.
        """
        cut_metadata = {
            "corner_treatment": "butted_filler",
        }

        return Panel(
            panel_type=PanelType.FILLER,
            width=corner_config.filler_width,
            height=height,
            material=material,
            cut_metadata=cut_metadata,
        )

    def generate_corner_panels(
        self,
        corner_config: OutsideCornerConfig,
        height: float,
        depth: float,
        material: MaterialSpec,
    ) -> list[Panel]:
        """Generate all panels needed for the specified corner treatment.

        Args:
            corner_config: Outside corner configuration.
            height: Cabinet height at the corner.
            depth: Cabinet depth.
            material: Material specification for panels.

        Returns:
            List of panels for the corner treatment.
        """
        if corner_config.treatment == "angled_face":
            return [self.calculate_angled_face_panel(corner_config, height, depth, material)]
        elif corner_config.treatment == "butted_filler":
            return [self.calculate_filler_panel(corner_config, height, material)]
        elif corner_config.treatment == "wrap_around":
            # Defer wrap_around to future implementation
            # For now, fall back to angled_face
            return [self.calculate_angled_face_panel(corner_config, height, depth, material)]
        else:
            return []

    def calculate_side_panel_angle_cut(
        self,
        wall_angle: float,
        side: str,  # "left" or "right"
    ) -> AngleCut | None:
        """Calculate angle cut for side panel at non-90-degree wall junction.

        Args:
            wall_angle: The angle of the wall junction.
            side: Which side of the junction ("left" or "right").

        Returns:
            AngleCut specification if needed, None for 90-degree junctions.
        """
        # Standard 90-degree junction needs no special cut
        if wall_angle in (90, -90, 0):
            return None

        # Calculate the cut angle (half the deviation from 90 degrees)
        deviation = abs(90 - abs(wall_angle))
        cut_angle = deviation / 2

        # Determine edge based on side
        edge = "right" if side == "right" else "left"

        return AngleCut(
            edge=edge,
            angle=cut_angle,
            bevel=True,
        )
