"""Layout calculator service for cabinet generation.

This module provides the core layout calculation functionality for generating
cabinet layouts from wall dimensions and parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..components import ComponentContext, component_registry
from ..components.results import HardwareItem
from ..entities import Cabinet, Panel, Section, Shelf
from ..section_resolver import (
    RowSpec,
    SectionSpec,
    SectionWidthError,
    resolve_row_heights,
    resolve_section_row_heights,
    resolve_section_widths,
)
from ..value_objects import (
    MaterialSpec,
    PanelType,
    Position,
    SectionType,
)

if TYPE_CHECKING:
    from ..entities import Wall

__all__ = [
    "LayoutParameters",
    "LayoutCalculator",
]


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
                          - face_frame: Face frame config

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
            face_frame=zones.get("face_frame"),
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
                        f'Section {i} depth ({spec.depth}") exceeds cabinet depth ({wall.depth}")'
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

            if (
                shelf_count > 0
                or primary_component_id.startswith("door.")
                or primary_component_id.startswith("drawer.")
            ):
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
                          - face_frame: Face frame config

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
        zones = zone_configs or {}

        # Extract base zone (toe kick) height if present
        base_zone = zones.get("base_zone")
        base_zone_height = 0.0
        if base_zone and base_zone.get("zone_type") == "toe_kick":
            base_zone_height = base_zone.get("height", 0.0)

        # Resolve row heights, accounting for toe kick
        resolved_heights = resolve_row_heights(
            row_specs=row_specs,
            total_height=wall.height,
            material_thickness=params.material.thickness,
            base_zone_height=base_zone_height,
        )

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
            face_frame=zones.get("face_frame"),
        )

        # Collect hardware from all components
        all_hardware: list[HardwareItem] = []

        # Process each row from bottom to top
        # Start above toe kick (if present) and bottom panel
        current_y = base_zone_height + params.material.thickness

        for row_idx, (row_spec, row_height) in enumerate(
            zip(row_specs, resolved_heights)
        ):
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
                            f'Row {row_idx} Section {i} depth ({spec.depth}") '
                            f'exceeds cabinet depth ({wall.depth}")'
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
                # For rows with horizontal dividers above them (all but the last row),
                # set skip_top_divider=True so components don't generate their own
                is_not_last_row = row_idx < len(row_specs) - 1
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
                    skip_top_divider=is_not_last_row,
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
                        component_config = {
                            "count": shelf_count,
                            **spec.component_config,
                        }
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
            # For rows with horizontal dividers above them (all but the last row),
            # set skip_top_divider=True so components don't generate their own
            is_not_last_row = row_idx < len(spec.row_specs) - 1
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
                skip_top_divider=is_not_last_row,
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
                    component_config = {
                        "count": shelf_count,
                        **row_spec.component_config,
                    }
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
