"""Room layout orchestrator service.

Coordinates validation, section assignment, cabinet generation,
and output assembly for room layouts with multiple wall segments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain import (
    LayoutParameters,
    SectionSpec,
    SectionWidthError,
    Wall,
)

if TYPE_CHECKING:
    from cabinets.contracts.protocols import (
        CutListGeneratorProtocol,
        InputValidatorProtocol,
        LayoutCalculatorProtocol,
        MaterialEstimatorProtocol,
        OutputAssemblerProtocol,
        RoomLayoutServiceProtocol,
        SectionWidthResolverProtocol,
    )
    from cabinets.domain.entities import Cabinet, Room
    from cabinets.domain.value_objects import CutPiece
    from cabinets.application.dtos import LayoutParametersInput, RoomLayoutOutput


class RoomLayoutOrchestratorService:
    """Orchestrates multi-wall room layout generation.

    Coordinates validation, section assignment, cabinet generation,
    and output assembly for room layouts. This service was extracted
    from GenerateLayoutCommand.execute_room_layout() to follow SRP.
    """

    def __init__(
        self,
        input_validator: "InputValidatorProtocol",
        room_layout_service: "RoomLayoutServiceProtocol",
        layout_calculator: "LayoutCalculatorProtocol",
        cut_list_generator: "CutListGeneratorProtocol",
        section_width_resolver: "SectionWidthResolverProtocol",
        output_assembler: "OutputAssemblerProtocol",
        material_estimator: "MaterialEstimatorProtocol",
    ) -> None:
        """Initialize with required dependencies.

        Args:
            input_validator: Service for input validation.
            room_layout_service: Service for room layout operations.
            layout_calculator: Service for cabinet layout generation.
            cut_list_generator: Service for cut list generation.
            section_width_resolver: Service for resolving section widths.
            output_assembler: Service for assembling output DTOs.
            material_estimator: Service for material estimation.
        """
        self._input_validator = input_validator
        self._room_layout_service = room_layout_service
        self._layout_calculator = layout_calculator
        self._cut_list_generator = cut_list_generator
        self._section_width_resolver = section_width_resolver
        self._output_assembler = output_assembler
        self._material_estimator = material_estimator

    def orchestrate(
        self,
        room: "Room",
        section_specs: "list[SectionSpec]",
        params_input: "LayoutParametersInput",
    ) -> "RoomLayoutOutput":
        """Orchestrate complete room layout generation.

        Coordinates:
        1. Parameter validation
        2. Fit validation (sections fit on assigned walls)
        3. Room geometry validation
        4. Section-to-wall assignment
        5. Section transform computation (3D positioning)
        6. Per-wall cabinet generation
        7. Combined cut list and material aggregation
        8. Output assembly

        Args:
            room: Room entity with wall segment definitions.
            section_specs: Section specifications with wall assignments.
            params_input: Layout parameters (material specs).

        Returns:
            RoomLayoutOutput with cabinets, transforms, and estimates.
        """
        errors: list[str] = []

        # Validate parameters input
        param_errors = self._input_validator.validate_params_input(params_input)
        errors.extend(param_errors)

        if errors:
            return self._output_assembler.create_error_room_output(room, errors)

        # Validate fit - check that sections fit on their assigned walls
        fit_errors = self._room_layout_service.validate_fit(room, section_specs)
        if fit_errors:
            for fit_error in fit_errors:
                errors.append(fit_error.message)
            return self._output_assembler.create_error_room_output(room, errors)

        # Validate room geometry - check for self-intersection, closure gaps
        geometry_errors = room.validate_geometry()
        if geometry_errors:
            for geom_error in geometry_errors:
                errors.append(geom_error.message)
            return self._output_assembler.create_error_room_output(room, errors)

        # Assign sections to walls
        try:
            assignments = self._room_layout_service.assign_sections_to_walls(
                room, section_specs
            )
        except ValueError as e:
            return self._output_assembler.create_error_room_output(room, [str(e)])

        # Compute section transforms
        transforms = self._room_layout_service.compute_section_transforms(
            room, assignments, section_specs
        )

        # Generate cabinets
        cabinets, all_cut_pieces = self._generate_cabinets(
            room, section_specs, assignments, params_input
        )

        # Check for cabinet generation errors
        if cabinets is None:
            # Error occurred during generation - all_cut_pieces contains error message
            return self._output_assembler.create_error_room_output(
                room, [str(all_cut_pieces)]
            )

        # Sort combined cut list by size (all_cut_pieces is list[CutPiece] here since cabinets is not None)
        assert isinstance(all_cut_pieces, list)
        all_cut_pieces = self._cut_list_generator.sort_by_size(all_cut_pieces)

        return self._output_assembler.assemble_room_layout_output(
            room=room,
            cabinets=cabinets,
            transforms=transforms,
            cut_list=all_cut_pieces,
            material_estimator=self._material_estimator,
        )

    def _generate_cabinets(
        self,
        room: "Room",
        section_specs: "list[SectionSpec]",
        assignments: list,
        params_input: "LayoutParametersInput",
    ) -> tuple["list[Cabinet] | None", "list[CutPiece] | str"]:
        """Generate cabinets for each wall assignment.

        Args:
            room: Room entity with wall definitions.
            section_specs: Section specifications.
            assignments: Section-to-wall assignments.
            params_input: Layout parameters.

        Returns:
            Tuple of (cabinets, cut_pieces) on success, or (None, error_message)
            on failure.
        """
        cabinets: list = []
        all_cut_pieces: list = []

        for assignment in assignments:
            section_spec = section_specs[assignment.section_index]
            wall_segment = room.walls[assignment.wall_index]

            # Resolve section width (handles "fill" widths)
            section_width = self._section_width_resolver.resolve_width(
                section_spec, wall_segment, section_specs, room
            )

            # Create a Wall object for this section
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
                # Create a single-section spec list for this cabinet
                single_section_spec = [
                    SectionSpec(
                        width="fill",
                        shelves=section_spec.shelves,
                        section_type=section_spec.section_type,
                        component_config=section_spec.component_config,
                        row_specs=section_spec.row_specs,  # Preserve nested rows
                    )
                ]
                cabinet, _hardware = (
                    self._layout_calculator.generate_cabinet_from_specs(
                        wall, section_params, single_section_spec
                    )
                )
                cabinets.append(cabinet)

                # Generate cut list for this cabinet
                cut_list = self._cut_list_generator.generate(cabinet)
                all_cut_pieces.extend(cut_list)
            except SectionWidthError as e:
                return None, str(e)

        return cabinets, all_cut_pieces
