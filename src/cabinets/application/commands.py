"""Application commands (use cases) for cabinet generation."""

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
from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.services import RoomLayoutService
from cabinets.domain.value_objects import FitError, GeometryError, SectionTransform

from .dtos import LayoutOutput, LayoutParametersInput, RoomLayoutOutput, WallInput


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
    ) -> LayoutOutput:
        """Execute the layout generation command.

        Args:
            wall_input: Wall dimensions for the cabinet.
            params_input: Layout parameters (sections, shelves, materials).
            section_specs: Optional list of section specifications. If provided,
                uses the new specs-based generation with per-section widths and
                shelf counts. If None, uses the legacy uniform sections approach.

        Returns:
            LayoutOutput with the generated cabinet, cut list, and material estimates.
        """
        # Validate inputs
        errors = wall_input.validate() + params_input.validate()

        # Validate section specs if provided
        if section_specs is not None:
            spec_errors = validate_section_specs(
                section_specs,
                wall_input.width,
                params_input.material_thickness,
            )
            errors.extend(spec_errors)

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

        # Generate layout - use specs-based method if section_specs provided
        try:
            if section_specs is not None:
                cabinet = self.layout_calculator.generate_cabinet_from_specs(
                    wall, layout_params, section_specs
                )
            else:
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
        cut_list = self.cut_list_generator.sort_by_size(cut_list)

        # Estimate materials
        material_estimates = self.material_estimator.estimate(cut_list)
        total_estimate = self.material_estimator.estimate_total(cut_list)

        return LayoutOutput(
            cabinet=cabinet,
            cut_list=cut_list,
            material_estimates=material_estimates,
            total_estimate=total_estimate,
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

            # Generate cabinet for this section
            try:
                cabinet = self.layout_calculator.generate_cabinet(wall, section_params)
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
