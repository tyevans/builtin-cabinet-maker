"""Application commands (use cases) for cabinet generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain import (
    CutListGenerator,
    LayoutCalculator,
    LayoutParameters,
    MaterialEstimator,
    SectionSpec,
    SectionWidthError,
    Wall,
    validate_section_specs,
)
from cabinets.domain.section_resolver import RowSpec, SectionSpec, validate_row_specs
from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.services import RoomLayoutService
from cabinets.domain.value_objects import FitError, GeometryError, SectionTransform

from .dtos import LayoutOutput, LayoutParametersInput, RoomLayoutOutput, WallInput

if TYPE_CHECKING:
    from cabinets.domain.services.installation import InstallationConfig


class GenerateLayoutCommand:
    """Command to generate a complete cabinet layout.

    Supports both single-wall cabinet layouts and multi-wall room layouts.
    For room layouts, use execute_room_layout() method.
    """

    def __init__(
        self,
        layout_calculator: LayoutCalculator | None = None,
        cut_list_generator: CutListGenerator | None = None,
        material_estimator: MaterialEstimator | None = None,
        room_layout_service: RoomLayoutService | None = None,
    ) -> None:
        self.layout_calculator = layout_calculator or LayoutCalculator()
        self.cut_list_generator = cut_list_generator or CutListGenerator()
        self.material_estimator = material_estimator or MaterialEstimator()
        self.room_layout_service = room_layout_service or RoomLayoutService()

    def execute(
        self,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
        section_specs: list[SectionSpec] | None = None,
        row_specs: list[RowSpec] | None = None,
        zone_configs: dict[str, dict | None] | None = None,
        installation_config: "InstallationConfig | None" = None,
        left_edge_position: float = 0.0,
    ) -> LayoutOutput:
        """Execute the layout generation command.

        Args:
            wall_input: Wall dimensions for the cabinet.
            params_input: Layout parameters (sections, shelves, materials).
            section_specs: Optional list of section specifications. If provided,
                uses the new specs-based generation with per-section widths and
                shelf counts. If None, uses the legacy uniform sections approach.
            row_specs: Optional list of row specifications for multi-row cabinets.
                When provided, creates vertically stacked rows of sections.
                Cannot be used together with section_specs.
            zone_configs: Optional dict with zone configurations for decorative elements:
                - base_zone: Toe kick zone config
                - crown_molding: Crown molding zone config
                - light_rail: Light rail zone config
            installation_config: Optional installation configuration for mounting hardware,
                French cleat generation, and installation instructions.
            left_edge_position: Position of cabinet left edge from wall start (for stud
                alignment analysis). Default 0.0 inches.

        Returns:
            LayoutOutput with the generated cabinet, cut list, and material estimates.
        """
        # Validate inputs
        errors = wall_input.validate() + params_input.validate()

        # Validate that only one of section_specs or row_specs is provided
        if section_specs is not None and row_specs is not None:
            errors.append(
                "Cannot specify both section_specs and row_specs. "
                "Use section_specs for single-row layout or row_specs for multi-row layout."
            )

        # Validate section specs if provided
        if section_specs is not None:
            spec_errors = validate_section_specs(
                section_specs,
                wall_input.width,
                params_input.material_thickness,
            )
            errors.extend(spec_errors)

        # Validate row specs if provided
        if row_specs is not None:
            row_errors = validate_row_specs(
                row_specs,
                wall_input.height,
                params_input.material_thickness,
            )
            errors.extend(row_errors)

        if errors:
            # Return empty output with errors
            return LayoutOutput(
                cabinet=None,  # type: ignore
                cut_list=[],
                material_estimates={},
                total_estimate=None,  # type: ignore
                errors=errors,
            )

        # Create domain objects
        wall = Wall(
            width=wall_input.width,
            height=wall_input.height,
            depth=wall_input.depth,
        )
        layout_params = LayoutParameters(
            num_sections=params_input.num_sections,
            shelves_per_section=params_input.shelves_per_section,
            material=params_input.to_material_spec(),
            back_material=params_input.to_back_material_spec(),
        )

        # Generate layout based on what was provided
        hardware: list = []
        try:
            if row_specs is not None:
                # Multi-row layout
                cabinet, hardware = self.layout_calculator.generate_cabinet_from_row_specs(
                    wall, layout_params, row_specs, zone_configs=zone_configs
                )
            elif section_specs is not None:
                # Single-row layout with explicit section specs
                cabinet, hardware = self.layout_calculator.generate_cabinet_from_specs(
                    wall, layout_params, section_specs, zone_configs=zone_configs
                )
            else:
                # Legacy uniform sections approach
                cabinet = self.layout_calculator.generate_cabinet(wall, layout_params)
        except SectionWidthError as e:
            return LayoutOutput(
                cabinet=None,  # type: ignore
                cut_list=[],
                material_estimates={},
                total_estimate=None,  # type: ignore
                errors=[str(e)],
            )

        # Generate cut list
        cut_list = self.cut_list_generator.generate(cabinet)

        # Installation support
        installation_hardware = None
        installation_instructions = None
        installation_warnings = None
        stud_analysis = None

        if installation_config:
            from cabinets.domain.services.installation import InstallationService

            installation_service = InstallationService(installation_config)
            installation_plan = installation_service.generate_plan(
                cabinet, left_edge_position=left_edge_position
            )

            # Add cleat cut pieces to main cut list
            cut_list = list(cut_list) + list(installation_plan.cleat_cut_pieces)

            installation_hardware = list(installation_plan.mounting_hardware)
            installation_instructions = installation_plan.instructions
            installation_warnings = list(installation_plan.warnings)
            stud_analysis = {
                "cabinet_left_edge": installation_plan.stud_analysis.cabinet_left_edge,
                "cabinet_width": installation_plan.stud_analysis.cabinet_width,
                "stud_positions": list(installation_plan.stud_analysis.stud_positions),
                "non_stud_positions": list(installation_plan.stud_analysis.non_stud_positions),
                "stud_hit_count": installation_plan.stud_analysis.stud_hit_count,
                "recommendation": installation_plan.stud_analysis.recommendation,
            }

        cut_list = self.cut_list_generator.sort_by_size(cut_list)

        # Estimate materials
        material_estimates = self.material_estimator.estimate(cut_list)
        total_estimate = self.material_estimator.estimate_total(cut_list)

        return LayoutOutput(
            cabinet=cabinet,
            cut_list=cut_list,
            material_estimates=material_estimates,
            total_estimate=total_estimate,
            hardware=hardware,
            installation_hardware=installation_hardware,
            installation_instructions=installation_instructions,
            installation_warnings=installation_warnings,
            stud_analysis=stud_analysis,
        )

    def execute_room_layout(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        params_input: LayoutParametersInput,
    ) -> RoomLayoutOutput:
        """Execute room layout generation for multi-wall cabinets.

        Generates cabinet layouts for each wall section in a room, computing
        3D transforms for proper positioning and combining all cut lists
        and material estimates.

        Args:
            room: Room entity with wall segment definitions.
            section_specs: List of section specifications with wall assignments.
            params_input: Layout parameters (material specs).

        Returns:
            RoomLayoutOutput with cabinets, transforms, cut lists, and estimates.
        """
        errors: list[str] = []

        # Validate parameters input
        param_errors = params_input.validate()
        errors.extend(param_errors)

        if errors:
            return self._create_error_room_output(room, errors)

        # Validate fit - check that sections fit on their assigned walls
        fit_errors = self.room_layout_service.validate_fit(room, section_specs)
        if fit_errors:
            for fit_error in fit_errors:
                errors.append(fit_error.message)
            return self._create_error_room_output(room, errors)

        # Validate room geometry - check for self-intersection, closure gaps
        geometry_errors = room.validate_geometry()
        if geometry_errors:
            for geom_error in geometry_errors:
                errors.append(geom_error.message)
            return self._create_error_room_output(room, errors)

        # Assign sections to walls
        try:
            assignments = self.room_layout_service.assign_sections_to_walls(
                room, section_specs
            )
        except ValueError as e:
            return self._create_error_room_output(room, [str(e)])

        # Compute section transforms
        transforms = self.room_layout_service.compute_section_transforms(
            room, assignments, section_specs
        )

        # Generate a cabinet for each wall section
        cabinets: list = []
        all_cut_pieces: list = []

        layout_params = LayoutParameters(
            num_sections=1,  # Each wall section is its own cabinet
            shelves_per_section=params_input.shelves_per_section,
            material=params_input.to_material_spec(),
            back_material=params_input.to_back_material_spec(),
        )

        # Group section specs by wall index for width resolution
        for assignment in assignments:
            section_spec = section_specs[assignment.section_index]
            wall_segment = room.walls[assignment.wall_index]

            # Create a Wall object for this section
            # Width is determined by the section spec
            section_width = self._resolve_section_width(
                section_spec, wall_segment, section_specs, room
            )

            wall = Wall(
                width=section_width,
                height=wall_segment.height,
                depth=wall_segment.depth,
            )

            # Create section-specific layout params
            section_params = LayoutParameters(
                num_sections=1,
                shelves_per_section=section_spec.shelves,
                material=params_input.to_material_spec(),
                back_material=params_input.to_back_material_spec(),
            )

            # Generate cabinet for this section using section specs for component support
            try:
                # Create a single-section spec list for this cabinet
                # Use "fill" width since this is a single-section cabinet that should fill the space
                # Preserve row_specs if the section has nested rows for vertical stacking
                single_section_spec = [SectionSpec(
                    width="fill",
                    shelves=section_spec.shelves,
                    section_type=section_spec.section_type,
                    component_config=section_spec.component_config,
                    row_specs=section_spec.row_specs,  # Preserve nested rows
                )]
                cabinet, _hardware = self.layout_calculator.generate_cabinet_from_specs(
                    wall, section_params, single_section_spec
                )
                cabinets.append(cabinet)

                # Generate cut list for this cabinet
                cut_list = self.cut_list_generator.generate(cabinet)
                all_cut_pieces.extend(cut_list)
            except SectionWidthError as e:
                return self._create_error_room_output(room, [str(e)])

        # Sort combined cut list by size
        all_cut_pieces = self.cut_list_generator.sort_by_size(all_cut_pieces)

        # Estimate materials for all cut pieces combined
        material_estimates = self.material_estimator.estimate(all_cut_pieces)
        total_estimate = self.material_estimator.estimate_total(all_cut_pieces)

        return RoomLayoutOutput(
            room=room,
            cabinets=cabinets,
            transforms=transforms,
            cut_list=all_cut_pieces,
            material_estimates=material_estimates,
            total_estimate=total_estimate,
        )

    def _create_error_room_output(
        self, room: Room, errors: list[str]
    ) -> RoomLayoutOutput:
        """Create an error RoomLayoutOutput with no cabinets."""
        return RoomLayoutOutput(
            room=room,
            cabinets=[],
            transforms=[],
            cut_list=[],
            material_estimates={},
            total_estimate=None,  # type: ignore
            errors=errors,
        )

    def _resolve_section_width(
        self,
        section_spec: SectionSpec,
        wall_segment: WallSegment,
        all_specs: list[SectionSpec],
        room: Room,
    ) -> float:
        """Resolve the width for a section spec on a given wall.

        For fixed widths, returns the width directly.
        For fill widths, calculates based on remaining space on the wall.

        Args:
            section_spec: The section specification to resolve.
            wall_segment: The wall segment this section is on.
            all_specs: All section specifications (for calculating fill widths).
            room: The room containing the walls.

        Returns:
            The resolved section width in inches.
        """
        if not section_spec.is_fill:
            return section_spec.fixed_width or 0.0

        # Find all sections on the same wall
        wall_index = self._get_wall_index_for_spec(section_spec, room)
        sections_on_wall = [
            s for s in all_specs
            if self._get_wall_index_for_spec(s, room) == wall_index
        ]

        # Calculate fixed widths and fill count
        fixed_widths = sum(
            s.fixed_width or 0.0 for s in sections_on_wall if not s.is_fill
        )
        fill_count = sum(1 for s in sections_on_wall if s.is_fill)

        # Calculate fill width
        remaining = wall_segment.length - fixed_widths
        return remaining / fill_count if fill_count > 0 else 0.0

    def _get_wall_index_for_spec(self, spec: SectionSpec, room: Room) -> int:
        """Get the wall index for a section spec.

        Args:
            spec: The section specification.
            room: The room containing the walls.

        Returns:
            The wall index (0-based).
        """
        if spec.wall is None:
            return 0

        if isinstance(spec.wall, int):
            return spec.wall

        # Look up by name
        for i, wall in enumerate(room.walls):
            if wall.name == spec.wall:
                return i

        return 0  # Default to first wall if not found
