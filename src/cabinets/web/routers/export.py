"""Export format endpoints."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.infrastructure import BinPackingConfig, BinPackingService
from cabinets.infrastructure.cut_diagram_renderer import CutDiagramRenderer
from cabinets.infrastructure.exporters import ExporterRegistry
from cabinets.infrastructure.exporters.bom import BomGenerator
from cabinets.web.dependencies import GenerateCommandDep
from cabinets.web.exceptions import CabinetGenerationError, UnsupportedFormatError
from cabinets.web.schemas.requests import ExportRequest, GenerateFromConfigRequest
from cabinets.web.schemas.responses import ExportFormatsSchema

router = APIRouter(prefix="/export", tags=["export"])


def _generate_layout(command: GenerateCommandDep, request: ExportRequest):
    """Helper to generate layout from export request."""
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

    return output


@router.get("/formats", response_model=ExportFormatsSchema)
async def list_export_formats() -> ExportFormatsSchema:
    """List all available export formats.

    Returns:
        List of available format names.
    """
    # Ensure exporters are loaded
    from cabinets.infrastructure import exporters as _  # noqa: F401

    return ExportFormatsSchema(formats=ExporterRegistry.available_formats())


@router.post("/stl")
async def export_stl(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> FileResponse:
    """Export cabinet as STL file (binary 3D model).

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        STL file as binary download.
    """
    output = _generate_layout(command, request)

    # Export to temporary file
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    exporter_class = ExporterRegistry.get("stl")
    exporter = exporter_class()
    exporter.export(output, tmp_path)

    return FileResponse(
        path=tmp_path,
        media_type="application/octet-stream",
        filename="cabinet.stl",
        headers={"Content-Disposition": "attachment; filename=cabinet.stl"},
    )


@router.post("/stl-from-config")
async def export_stl_from_config(
    request: GenerateFromConfigRequest,
    command: GenerateCommandDep,
) -> Response:
    """Export cabinet as STL from full configuration.

    This endpoint accepts the full cabinet configuration (same format as
    /generate/from-config) and returns STL binary data. This ensures the
    3D model matches exactly what the backend generates, including proper
    section widths.

    Supports both single-cabinet configurations and room layouts with
    multiple walls.

    Args:
        request: Request containing full cabinet configuration.
        command: Injected GenerateLayoutCommand.

    Returns:
        STL binary data.
    """
    from cabinets.application.config import (
        config_to_all_section_specs,
        config_to_dtos,
        config_to_room,
        config_to_section_specs,
        config_to_zone_configs,
        load_config_from_dict,
    )

    try:
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
            output = command.execute_room_layout(room, room_section_specs, params_input)

            if not output.is_valid:
                raise CabinetGenerationError(output.errors)

            # Export room layout to temporary file
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            exporter_class = ExporterRegistry.get("stl")
            exporter = exporter_class()
            exporter.export(output, tmp_path)

            # Read the file and return as response
            stl_data = tmp_path.read_bytes()
            tmp_path.unlink()  # Clean up temp file

            return Response(
                content=stl_data,
                media_type="application/octet-stream",
                headers={"Content-Disposition": "attachment; filename=cabinet.stl"},
            )

        # Single-cabinet mode (original behavior)
        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)
        zone_configs = config_to_zone_configs(config)

        cabinet_output = command.execute(
            wall_input,
            params_input,
            section_specs=section_specs,
            zone_configs=zone_configs,
        )

        if not cabinet_output.is_valid:
            raise CabinetGenerationError(cabinet_output.errors)

        # Export to temporary file
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        exporter_class = ExporterRegistry.get("stl")
        exporter = exporter_class()
        exporter.export(cabinet_output, tmp_path)

        # Read the file and return as response
        stl_data = tmp_path.read_bytes()
        tmp_path.unlink()  # Clean up temp file

        return Response(
            content=stl_data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=cabinet.stl"},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": str(e), "error_type": "config_error"},
        ) from e


@router.post("/dxf")
async def export_dxf(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> FileResponse:
    """Export cabinet as DXF file (2D CAD format).

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        DXF file as download.
    """
    output = _generate_layout(command, request)

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    exporter_class = ExporterRegistry.get("dxf")
    exporter = exporter_class()
    exporter.export(output, tmp_path)

    return FileResponse(
        path=tmp_path,
        media_type="application/dxf",
        filename="cabinet.dxf",
    )


@router.post("/svg")
async def export_svg(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> Response:
    """Export cabinet as SVG file (vector graphics).

    Note: Full SVG cut diagrams require bin packing. This endpoint
    returns a basic SVG representation.

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        SVG content as text response.
    """
    output = _generate_layout(command, request)

    try:
        exporter_class = ExporterRegistry.get("svg")
        exporter = exporter_class()
        svg_content = exporter.export_string(output)

        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={"Content-Disposition": "attachment; filename=cabinet.svg"},
        )
    except NotImplementedError:
        # SVG may require bin packing
        raise HTTPException(
            status_code=400,
            detail={
                "error": "SVG export requires bin packing optimization",
                "error_type": "missing_requirement",
            },
        )


@router.post("/json")
async def export_json(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> Response:
    """Export cabinet as enhanced JSON.

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        JSON content as response.
    """
    output = _generate_layout(command, request)

    exporter_class = ExporterRegistry.get("json")
    exporter = exporter_class()
    json_content = exporter.export_string(output)

    return Response(
        content=json_content,
        media_type="application/json",
    )


@router.post("/assembly")
async def export_assembly(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> Response:
    """Export assembly instructions as Markdown.

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        Markdown content as text response.
    """
    output = _generate_layout(command, request)

    exporter_class = ExporterRegistry.get("assembly")
    exporter = exporter_class()
    markdown_content = exporter.export_string(output)

    return Response(
        content=markdown_content,
        media_type="text/markdown",
    )


@router.post("/bom")
async def export_bom(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> Response:
    """Export bill of materials as Markdown.

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        BOM content as markdown response.
    """
    output = _generate_layout(command, request)

    exporter = BomGenerator(output_format="markdown")
    bom_content = exporter.export_string(output)

    return Response(
        content=bom_content,
        media_type="text/markdown",
    )


class SheetLayoutSchema(BaseModel):
    """Schema for a single sheet layout."""

    sheet_index: int = Field(..., description="Index of the sheet (0-based)")
    piece_count: int = Field(..., description="Number of pieces on this sheet")
    waste_percentage: float = Field(..., description="Waste percentage for this sheet")
    svg: str = Field(..., description="SVG content for this sheet layout")


class CutLayoutsResponseSchema(BaseModel):
    """Response schema for cut layout SVGs."""

    total_sheets: int = Field(..., description="Total number of sheets")
    total_waste_percentage: float = Field(..., description="Overall waste percentage")
    sheets: list[SheetLayoutSchema] = Field(..., description="Sheet layouts with SVGs")
    combined_svg: str = Field(..., description="All sheets in a single stacked SVG")


@router.post("/cut-layouts", response_model=CutLayoutsResponseSchema)
async def export_cut_layouts(
    request: ExportRequest,
    command: GenerateCommandDep,
) -> CutLayoutsResponseSchema:
    """Export cut layout SVGs showing bin-packed pieces on 4x8 sheets.

    Performs bin packing optimization on the cut list and returns SVG
    visualizations showing how pieces should be arranged on sheets.

    Args:
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        Cut layout response with individual sheet SVGs and combined view.
    """
    output = _generate_layout(command, request)

    # Run bin packing optimization
    bin_packing_config = BinPackingConfig(enabled=True)
    bin_packing_service = BinPackingService(bin_packing_config)

    try:
        packing_result = bin_packing_service.optimize_cut_list(output.cut_list)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Bin packing failed: {e}",
                "error_type": "bin_packing_error",
            },
        )

    # Render SVGs
    renderer = CutDiagramRenderer(
        scale=8.0,  # Slightly smaller scale for web display
        show_dimensions=True,
        show_labels=True,
        show_grain=False,
        use_panel_colors=True,
    )

    # Generate individual sheet SVGs
    individual_svgs = renderer.render_all_svg(packing_result)

    # Generate combined stacked SVG
    combined_svg = renderer.render_combined_svg(packing_result)

    # Build response
    sheets = []
    for i, layout in enumerate(packing_result.layouts):
        sheets.append(
            SheetLayoutSchema(
                sheet_index=i,
                piece_count=layout.piece_count,
                waste_percentage=layout.waste_percentage,
                svg=individual_svgs[i],
            )
        )

    return CutLayoutsResponseSchema(
        total_sheets=packing_result.total_sheets,
        total_waste_percentage=packing_result.total_waste_percentage,
        sheets=sheets,
        combined_svg=combined_svg,
    )


@router.post("/{format_name}")
async def export_generic(
    format_name: str,
    request: ExportRequest,
    command: GenerateCommandDep,
) -> Response:
    """Export cabinet to any registered format.

    This is a catch-all endpoint for formats not explicitly defined above.

    Args:
        format_name: Export format name.
        request: Export request with cabinet dimensions.
        command: Injected GenerateLayoutCommand.

    Returns:
        Exported content as appropriate response type.

    Raises:
        UnsupportedFormatError: If format is not registered.
    """
    # Ensure exporters are loaded
    from cabinets.infrastructure import exporters as _  # noqa: F401

    available = ExporterRegistry.available_formats()
    if not ExporterRegistry.is_registered(format_name):
        raise UnsupportedFormatError(format_name, available)

    output = _generate_layout(command, request)

    exporter_class = ExporterRegistry.get(format_name)
    exporter = exporter_class()

    try:
        content = exporter.export_string(output)
        return Response(
            content=content,
            media_type="text/plain",
        )
    except NotImplementedError:
        # Binary format - export to temp file
        with tempfile.NamedTemporaryFile(
            suffix=f".{exporter.file_extension}", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)

        exporter.export(output, tmp_path)

        return FileResponse(
            path=tmp_path,
            media_type="application/octet-stream",
            filename=f"cabinet.{exporter.file_extension}",
        )
