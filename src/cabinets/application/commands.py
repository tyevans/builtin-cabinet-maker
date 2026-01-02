"""Application commands (use cases) for cabinet generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.domain import (
    LayoutParameters,
    SectionWidthError,
    Wall,
)
from cabinets.domain.section_resolver import RowSpec, SectionSpec
from cabinets.domain.entities import Room

from .dtos import (
    LayoutOutput,
    LayoutParametersInput,
    RoomLayoutOutput,
    WallInput,
)
from .strategies import LayoutStrategyFactory

if TYPE_CHECKING:
    from cabinets.contracts.factory import InstallationServiceFactory
    from cabinets.contracts.protocols import (
        CutListGeneratorProtocol,
        InputValidatorProtocol,
        InstallationPlannerProtocol,
        LayoutCalculatorProtocol,
        MaterialEstimatorProtocol,
        OutputAssemblerProtocol,
        RoomLayoutOrchestratorProtocol,
        RoomLayoutServiceProtocol,
    )
    from cabinets.domain.services.installation import InstallationConfig


class GenerateLayoutCommand:
    """Command to generate a complete cabinet layout.

    This command orchestrates layout generation by delegating to focused services:
    - InputValidatorService: Validates wall inputs, layout parameters, and specs
    - OutputAssemblerService: Assembles LayoutOutput and RoomLayoutOutput DTOs
    - InstallationPlannerService: Coordinates installation planning
    - RoomLayoutOrchestratorService: Orchestrates multi-wall room layouts

    Supports both single-wall cabinet layouts and multi-wall room layouts.
    For room layouts, use execute_room_layout() method.

    Use ServiceFactory.create_generate_command() for default instances with
    all dependencies properly wired.
    """

    def __init__(
        self,
        layout_calculator: "LayoutCalculatorProtocol",
        cut_list_generator: "CutListGeneratorProtocol",
        material_estimator: "MaterialEstimatorProtocol",
        room_layout_service: "RoomLayoutServiceProtocol",
        input_validator: "InputValidatorProtocol | None" = None,
        output_assembler: "OutputAssemblerProtocol | None" = None,
        installation_planner: "InstallationPlannerProtocol | None" = None,
        room_orchestrator: "RoomLayoutOrchestratorProtocol | None" = None,
        # Legacy parameter for backward compatibility
        installation_service_factory: "InstallationServiceFactory | None" = None,
    ) -> None:
        """Initialize command with required dependencies.

        Args:
            layout_calculator: Service for generating cabinet layouts.
            cut_list_generator: Service for generating cut lists from cabinets.
            material_estimator: Service for estimating material requirements.
            room_layout_service: Service for multi-wall room layouts.
            input_validator: Service for validating inputs. If not provided,
                creates a default InputValidatorService.
            output_assembler: Service for assembling output DTOs. If not provided,
                creates a default OutputAssemblerService.
            installation_planner: Optional service for installation planning.
                Required when using installation_config in execute().
            room_orchestrator: Optional service for room layout orchestration.
                If provided, execute_room_layout() delegates to it.
            installation_service_factory: DEPRECATED. Use installation_planner instead.
                For backward compatibility, if this is provided and installation_planner
                is not, an InstallationPlannerService will be created using this factory.
        """
        from cabinets.application.services import (
            InputValidatorService,
            InstallationPlannerService,
            OutputAssemblerService,
        )

        self._layout_calculator = layout_calculator
        self._cut_list_generator = cut_list_generator
        self._material_estimator = material_estimator
        self._room_layout_service = room_layout_service

        # Use provided services or create defaults
        self._input_validator = input_validator or InputValidatorService()
        self._output_assembler = output_assembler or OutputAssemblerService()

        # Handle installation planner - prefer new parameter, fall back to legacy factory
        # Explicitly type as Optional since it can be None
        self._installation_planner: "InstallationPlannerProtocol | None"
        if installation_planner is not None:
            self._installation_planner = installation_planner
        elif installation_service_factory is not None:
            # Legacy compatibility: create planner from factory
            self._installation_planner = InstallationPlannerService(
                installation_service_factory
            )
        else:
            self._installation_planner = None

        self._room_orchestrator = room_orchestrator

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
        # Validate inputs using the validator service
        errors = self._input_validator.validate_wall_input(wall_input)
        errors.extend(self._input_validator.validate_params_input(params_input))
        errors.extend(
            self._input_validator.validate_specs(
                section_specs=section_specs,
                row_specs=row_specs,
                wall_width=wall_input.width,
                wall_height=wall_input.height,
                material_thickness=params_input.material_thickness,
            )
        )

        if errors:
            return self._output_assembler.create_error_output(errors)

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

        # Generate layout using the appropriate strategy
        try:
            strategy_factory = LayoutStrategyFactory(self._layout_calculator)
            strategy = strategy_factory.create_strategy(
                section_specs=section_specs,
                row_specs=row_specs,
            )
            cabinet, hardware = strategy.execute(
                wall=wall,
                layout_params=layout_params,
                zone_configs=zone_configs,
            )
        except SectionWidthError as e:
            return self._output_assembler.create_error_output([str(e)])

        # Generate cut list
        cut_list = self._cut_list_generator.generate(cabinet)

        # Installation planning (requires installation_planner to be configured)
        installation_result = None
        if installation_config is not None:
            if self._installation_planner is None:
                return self._output_assembler.create_error_output(
                    [
                        "installation_config provided but no installation_planner configured"
                    ]
                )
            installation_result = self._installation_planner.plan_installation(
                cabinet=cabinet,
                cut_list=cut_list,
                installation_config=installation_config,
                left_edge_position=left_edge_position,
            )
            cut_list = installation_result.augmented_cut_list

        # Sort cut list
        cut_list = self._cut_list_generator.sort_by_size(cut_list)

        # Assemble and return output
        return self._output_assembler.assemble_layout_output(
            cabinet=cabinet,
            cut_list=cut_list,
            hardware=hardware,
            material_estimator=self._material_estimator,
            installation_result=installation_result,
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
        # Delegate to room orchestrator if available
        if self._room_orchestrator is not None:
            return self._room_orchestrator.orchestrate(
                room=room,
                section_specs=section_specs,
                params_input=params_input,
            )

        # Fallback: inline implementation for backward compatibility
        # This preserves existing behavior when orchestrator is not provided
        return self._execute_room_layout_inline(room, section_specs, params_input)

    def _execute_room_layout_inline(
        self,
        room: Room,
        section_specs: list[SectionSpec],
        params_input: LayoutParametersInput,
    ) -> RoomLayoutOutput:
        """Inline room layout implementation for backward compatibility.

        This method contains the original execute_room_layout logic for
        cases where RoomLayoutOrchestratorService is not provided.
        """

        errors: list[str] = []

        # Validate parameters input
        param_errors = params_input.validate()
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

        # Generate a cabinet for each wall section
        cabinets: list = []
        all_cut_pieces: list = []

        for assignment in assignments:
            section_spec = section_specs[assignment.section_index]
            wall_segment = room.walls[assignment.wall_index]

            # Resolve section width
            section_width = self._resolve_section_width(
                section_spec, wall_segment, section_specs, room
            )

            wall = Wall(
                width=section_width,
                height=wall_segment.height,
                depth=wall_segment.depth,
            )

            section_params = LayoutParameters(
                num_sections=1,
                shelves_per_section=section_spec.shelves,
                material=params_input.to_material_spec(),
                back_material=params_input.to_back_material_spec(),
            )

            try:
                single_section_spec = [
                    SectionSpec(
                        width="fill",
                        shelves=section_spec.shelves,
                        section_type=section_spec.section_type,
                        component_config=section_spec.component_config,
                        row_specs=section_spec.row_specs,
                    )
                ]
                cabinet, _hardware = (
                    self._layout_calculator.generate_cabinet_from_specs(
                        wall, section_params, single_section_spec
                    )
                )
                cabinets.append(cabinet)
                cut_list = self._cut_list_generator.generate(cabinet)
                all_cut_pieces.extend(cut_list)
            except SectionWidthError as e:
                return self._output_assembler.create_error_room_output(room, [str(e)])

        all_cut_pieces = self._cut_list_generator.sort_by_size(all_cut_pieces)

        return self._output_assembler.assemble_room_layout_output(
            room=room,
            cabinets=cabinets,
            transforms=transforms,
            cut_list=all_cut_pieces,
            material_estimator=self._material_estimator,
        )

    def _resolve_section_width(
        self,
        section_spec: SectionSpec,
        wall_segment,
        all_specs: list[SectionSpec],
        room: Room,
    ) -> float:
        """Resolve the width for a section spec on a given wall.

        For fixed widths, returns the width directly.
        For fill widths, calculates based on remaining space on the wall.
        """
        if not section_spec.is_fill:
            return section_spec.fixed_width or 0.0

        wall_index = self._get_wall_index_for_spec(section_spec, room)
        sections_on_wall = [
            s for s in all_specs if self._get_wall_index_for_spec(s, room) == wall_index
        ]

        fixed_widths = sum(
            s.fixed_width or 0.0 for s in sections_on_wall if not s.is_fill
        )
        fill_count = sum(1 for s in sections_on_wall if s.is_fill)

        remaining = wall_segment.length - fixed_widths
        return remaining / fill_count if fill_count > 0 else 0.0

    def _get_wall_index_for_spec(self, spec: SectionSpec, room: Room) -> int:
        """Get the wall index for a section spec."""
        if spec.wall is None:
            return 0
        if isinstance(spec.wall, int):
            return spec.wall
        for i, wall in enumerate(room.walls):
            if wall.name == spec.wall:
                return i
        return 0
