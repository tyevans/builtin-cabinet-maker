"""Cabinet generation endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from cabinets.application.config import (
    config_to_all_section_specs,
    config_to_dtos,
    config_to_room,
    config_to_section_specs,
    config_to_zone_configs,
    load_config_from_dict,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.web.dependencies import GenerateCommandDep
from cabinets.web.exceptions import CabinetGenerationError
from cabinets.web.schemas.requests import GenerateFromConfigRequest, GenerateRequest
from cabinets.web.schemas.responses import (
    CabinetSummarySchema,
    CutPieceSchema,
    LayoutOutputSchema,
    MaterialEstimateSchema,
    RoomLayoutOutputSchema,
    WallSummarySchema,
)

router = APIRouter(prefix="/generate", tags=["generate"])


def _layout_output_to_schema(output: Any) -> LayoutOutputSchema:
    """Convert LayoutOutput to response schema."""
    # Build cabinet summary
    cabinet_summary = None
    if output.cabinet:
        total_shelves = sum(len(section.shelves) for section in output.cabinet.sections)
        cabinet_summary = CabinetSummarySchema(
            width=output.cabinet.width,
            height=output.cabinet.height,
            depth=output.cabinet.depth,
            num_sections=len(output.cabinet.sections),
            total_shelves=total_shelves,
        )

    # Build cut list
    cut_list = [
        CutPieceSchema(
            label=piece.label,
            width=piece.width,
            height=piece.height,
            thickness=piece.material.thickness,
            material_type=piece.material.material_type.value,
            quantity=piece.quantity,
            notes=None,
        )
        for piece in output.cut_list
    ]

    # Build material estimates
    material_estimates = {}
    for spec, estimate in output.material_estimates.items():
        key = f"{spec.material_type.value}_{spec.thickness}"
        material_estimates[key] = MaterialEstimateSchema(
            sheet_count=float(estimate.sheet_count_4x8),
            total_area_sqft=estimate.total_area_sqft,
            waste_percentage=estimate.waste_percentage,
        )

    # Build total estimate
    total_estimate = None
    if output.total_estimate:
        total_estimate = MaterialEstimateSchema(
            sheet_count=float(output.total_estimate.sheet_count_4x8),
            total_area_sqft=output.total_estimate.total_area_sqft,
            waste_percentage=output.total_estimate.waste_percentage,
        )

    return LayoutOutputSchema(
        is_valid=output.is_valid,
        errors=output.errors,
        cabinet=cabinet_summary,
        cut_list=cut_list,
        material_estimates=material_estimates,
        total_estimate=total_estimate,
    )


def _room_layout_output_to_schema(output: Any) -> RoomLayoutOutputSchema:
    """Convert RoomLayoutOutput to response schema."""
    # Build wall summaries
    walls = [
        WallSummarySchema(
            name=wall.name,
            length=wall.length,
            height=wall.height,
            depth=wall.depth,
            angle=wall.angle,
        )
        for wall in output.room.walls
    ]

    # Build cabinet summaries
    cabinets = []
    for cabinet in output.cabinets:
        total_shelves = sum(len(section.shelves) for section in cabinet.sections)
        cabinets.append(
            CabinetSummarySchema(
                width=cabinet.width,
                height=cabinet.height,
                depth=cabinet.depth,
                num_sections=len(cabinet.sections),
                total_shelves=total_shelves,
            )
        )

    # Build cut list
    cut_list = [
        CutPieceSchema(
            label=piece.label,
            width=piece.width,
            height=piece.height,
            thickness=piece.material.thickness,
            material_type=piece.material.material_type.value,
            quantity=piece.quantity,
            notes=None,
        )
        for piece in output.cut_list
    ]

    # Build material estimates
    material_estimates = {}
    for spec, estimate in output.material_estimates.items():
        key = f"{spec.material_type.value}_{spec.thickness}"
        material_estimates[key] = MaterialEstimateSchema(
            sheet_count=float(estimate.sheet_count_4x8),
            total_area_sqft=estimate.total_area_sqft,
            waste_percentage=estimate.waste_percentage,
        )

    # Build total estimate
    total_estimate = None
    if output.total_estimate:
        total_estimate = MaterialEstimateSchema(
            sheet_count=float(output.total_estimate.sheet_count_4x8),
            total_area_sqft=output.total_estimate.total_area_sqft,
            waste_percentage=output.total_estimate.waste_percentage,
        )

    return RoomLayoutOutputSchema(
        is_valid=output.is_valid,
        errors=output.errors,
        room_name=output.room.name,
        walls=walls,
        cabinets=cabinets,
        cut_list=cut_list,
        material_estimates=material_estimates,
        total_estimate=total_estimate,
    )


@router.post("", response_model=LayoutOutputSchema)
async def generate_layout(
    request: GenerateRequest,
    command: GenerateCommandDep,
) -> LayoutOutputSchema:
    """Generate a cabinet layout from dimensions.

    Args:
        request: Generation request with dimensions and parameters.
        command: Injected GenerateLayoutCommand.

    Returns:
        Generated layout output with cabinet, cut list, and estimates.

    Raises:
        HTTPException: If validation fails or generation errors occur.
    """
    # Convert request to application DTOs
    wall_input = WallInput(
        width=request.dimensions.width,
        height=request.dimensions.height,
        depth=request.dimensions.depth,
    )

    params_input = LayoutParametersInput(
        num_sections=request.num_sections,
        shelves_per_section=request.shelves_per_section,
        material_thickness=request.material.thickness,
        material_type=request.material.type.value,
        back_thickness=request.back_thickness,
    )

    # Validate inputs
    wall_errors = wall_input.validate()
    params_errors = params_input.validate()
    if wall_errors or params_errors:
        raise HTTPException(
            status_code=422,
            detail={"errors": wall_errors + params_errors},
        )

    # Generate layout
    output = command.execute(wall_input, params_input)

    if not output.is_valid:
        raise CabinetGenerationError(output.errors)

    return _layout_output_to_schema(output)


@router.post("/from-config", response_model=LayoutOutputSchema | RoomLayoutOutputSchema)
async def generate_from_config(
    request: GenerateFromConfigRequest,
    command: GenerateCommandDep,
) -> LayoutOutputSchema | RoomLayoutOutputSchema:
    """Generate a cabinet layout from a full configuration.

    Supports both single-cabinet configurations and room layouts with
    multiple walls. Room layouts are detected by the presence of a
    'room' section in the configuration with wall definitions.

    Args:
        request: Request containing full cabinet configuration.
        command: Injected GenerateLayoutCommand.

    Returns:
        Generated layout output with cabinet(s), cut list, and estimates.
        Returns RoomLayoutOutputSchema for room configurations,
        LayoutOutputSchema for single-cabinet configurations.

    Raises:
        HTTPException: If configuration is invalid or generation fails.
    """
    try:
        # Load config from dict
        config = load_config_from_dict(request.config)

        # Check for room configuration
        if config.room is not None:
            # Room layout mode - generate cabinets for each wall section
            room = config_to_room(config)
            if room is None:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Invalid room configuration",
                        "error_type": "config_error",
                    },
                )
            room_section_specs = config_to_all_section_specs(config)
            _, params_input = config_to_dtos(config)

            # Execute room layout generation
            room_output = command.execute_room_layout(
                room, room_section_specs, params_input
            )

            if not room_output.is_valid:
                raise CabinetGenerationError(room_output.errors)

            return _room_layout_output_to_schema(room_output)

        # Single-cabinet mode (original behavior)
        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)
        zone_configs = config_to_zone_configs(config)

        # Generate layout with section specs for proper widths
        cabinet_output = command.execute(
            wall_input,
            params_input,
            section_specs=section_specs,
            zone_configs=zone_configs,
        )

        if not cabinet_output.is_valid:
            raise CabinetGenerationError(cabinet_output.errors)

        return _layout_output_to_schema(cabinet_output)

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": str(e), "error_type": "config_error"},
        ) from e
