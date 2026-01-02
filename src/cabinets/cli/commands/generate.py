"""Generate command for cabinet CLI.

This module contains the main generate command that orchestrates
cabinet layout generation from wall dimensions or configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from cabinets.application import (
    LayoutParametersInput,
    WallInput,
)
from cabinets.application.config import (
    ConfigError,
    config_to_all_section_specs,
    config_to_bin_packing,
    config_to_dtos,
    config_to_installation,
    config_to_obstacles,
    config_to_room,
    config_to_row_specs,
    config_to_safety,
    config_to_section_specs,
    config_to_woodworking,
    config_to_zone_configs,
    has_row_specs,
    has_section_specs,
    load_config,
    merge_config_with_cli,
)
from cabinets.application.factory import get_factory
from cabinets.domain import Cabinet
from cabinets.infrastructure import (
    BinPackingConfig,
    BinPackingService,
    CutDiagramRenderer,
)
from cabinets.infrastructure.llm import check_ollama_sync

from cabinets.infrastructure.exporters import ExporterRegistry

from .output_handlers import handle_multi_format_export
from .safety import (
    build_installation_config,
    build_installation_config_from_cli,
    build_safety_config,
    display_safety_summary,
    export_safety_labels,
)
from .zone_stack import generate_zone_stack

__all__ = ["generate"]


def generate(
    config_file: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to JSON configuration file"),
    ] = None,
    width: Annotated[
        float | None,
        typer.Option("--width", "-w", help="Wall width in inches"),
    ] = None,
    height: Annotated[
        float | None,
        typer.Option("--height", "-h", help="Wall height in inches"),
    ] = None,
    depth: Annotated[
        float | None,
        typer.Option("--depth", "-d", help="Cabinet depth in inches"),
    ] = None,
    sections: Annotated[
        int | None,
        typer.Option("--sections", "-s", help="Number of vertical sections"),
    ] = None,
    shelves: Annotated[
        int | None,
        typer.Option("--shelves", help="Shelves per section"),
    ] = None,
    thickness: Annotated[
        float | None,
        typer.Option("--thickness", "-t", help="Material thickness in inches"),
    ] = None,
    output_format: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help="Output format: all, cutlist, diagram, materials, json, stl, cutlayout, woodworking, installation, llm-assembly, safety, safety_labels",
        ),
    ] = None,
    optimize: Annotated[
        bool,
        typer.Option(
            "--optimize", help="Enable bin packing optimization for cut layout"
        ),
    ] = False,
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Output file path (required for stl format)"
        ),
    ] = None,
    output_formats: Annotated[
        str | None,
        typer.Option(
            "--output-formats",
            help="Comma-separated export formats: stl,dxf,json,bom,svg,assembly (or 'all')",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            help="Output directory for multi-format export",
        ),
    ] = None,
    project_name: Annotated[
        str,
        typer.Option(
            "--project-name",
            help="Project name for output file naming",
        ),
    ] = "cabinet",
    # Installation options (FRD-17)
    wall_type: Annotated[
        str | None,
        typer.Option(
            "--wall-type",
            help="Wall type: drywall, plaster, concrete, cmu, brick",
        ),
    ] = None,
    stud_spacing: Annotated[
        float | None,
        typer.Option(
            "--stud-spacing",
            help="Stud spacing in inches (default: 16)",
        ),
    ] = None,
    mounting_system: Annotated[
        str | None,
        typer.Option(
            "--mounting-system",
            help="Mounting system: direct_to_stud, french_cleat, hanging_rail, toggle_bolt",
        ),
    ] = None,
    expected_load: Annotated[
        str | None,
        typer.Option(
            "--expected-load",
            help="Expected load category: light, medium, heavy",
        ),
    ] = None,
    # LLM Assembly Options (FRD-20)
    llm_instructions: Annotated[
        bool,
        typer.Option(
            "--llm-instructions/--no-llm-instructions",
            help="Use LLM for enhanced assembly instructions. "
            "Requires Ollama (ollama.com) with a model installed. "
            "Falls back to template-based instructions if unavailable.",
        ),
    ] = False,
    skill_level: Annotated[
        str,
        typer.Option(
            "--skill-level",
            help="Skill level for LLM assembly instructions. "
            "Choices: beginner (detailed), intermediate (balanced), expert (concise).",
        ),
    ] = "intermediate",
    llm_model: Annotated[
        str,
        typer.Option(
            "--llm-model",
            help="Ollama model name for LLM generation. Default: llama3.2",
        ),
    ] = "llama3.2",
    ollama_url: Annotated[
        str,
        typer.Option(
            "--ollama-url",
            help="Ollama server URL. Default: http://localhost:11434",
        ),
    ] = "http://localhost:11434",
    llm_timeout: Annotated[
        int,
        typer.Option(
            "--llm-timeout",
            help="LLM generation timeout in seconds. Default: 30",
        ),
    ] = 30,
    # Safety Options (FRD-21)
    safety_factor: Annotated[
        float,
        typer.Option(
            "--safety-factor",
            help="Safety factor for capacity calculations (2.0-6.0)",
            min=2.0,
            max=6.0,
        ),
    ] = 4.0,
    accessibility: Annotated[
        bool,
        typer.Option(
            "--accessibility/--no-accessibility",
            help="Enable ADA accessibility checking",
        ),
    ] = False,
    child_safe: Annotated[
        bool,
        typer.Option(
            "--child-safe/--no-child-safe",
            help="Enable child safety mode (soft-close, locks, tip-over warnings)",
        ),
    ] = False,
    seismic_zone: Annotated[
        str | None,
        typer.Option(
            "--seismic-zone",
            help="IBC seismic design category (A, B, C, D, E, F)",
        ),
    ] = None,
    material_cert: Annotated[
        str,
        typer.Option(
            "--material-cert",
            help="Material certification (carb_phase2, naf, ulef, none, unknown)",
        ),
    ] = "unknown",
    no_clearance_check: Annotated[
        bool,
        typer.Option(
            "--no-clearance-check",
            help="Disable building code clearance checking",
        ),
    ] = False,
) -> None:
    """Generate a cabinet layout from wall dimensions.

    Supports both single cabinet generation and vertical zone stacks
    (kitchen, mudroom, vanity, hutch configurations).

    You can provide dimensions via CLI options or via a JSON configuration file.
    When using --config, CLI options override config file values.

    Zone Stack Configurations:
        For zone stack configurations (kitchen base+upper, mudroom bench+storage,
        etc.), use a JSON config file with the zone_stack field under cabinet:

        {
            "schema_version": "1.11",
            "cabinet": {
                "width": 72,
                "height": 84,
                "depth": 24,
                "zone_stack": {
                    "preset": "kitchen",
                    "countertop": { "thickness": 1.5, "edge_treatment": "eased" }
                }
            }
        }

        Available presets: kitchen, mudroom, vanity, hutch, custom

    LLM Assembly Instructions:
        Use --llm-instructions to enable AI-enhanced assembly instructions.
        This feature requires Ollama to be installed and running locally.
        Install Ollama from: https://ollama.com
        Then run: ollama pull llama3.2

    Safety Options:
        --safety-factor FLOAT    Safety factor for capacity (default: 4.0)
        --accessibility          Enable ADA reach range checking
        --child-safe             Enable child safety mode
        --seismic-zone ZONE      IBC seismic category (A-F)
        --material-cert CERT     Material certification level
        --no-clearance-check     Disable building code clearances

    Safety Output:
        --format safety          Include safety analysis report
        --format safety_labels   Generate printable safety labels

    Examples:
        cabinets generate --width 48 --height 84 --depth 12
        cabinets generate --config my-cabinet.json
        cabinets generate --config my-cabinet.json --width 60
        cabinets generate --config my-cabinet.json --output-formats stl,json --output-dir ./output
        cabinets generate --config my-cabinet.json --output-formats all --output-dir ./output --optimize
        cabinets generate --config my-cabinet.json --llm-instructions
        cabinets generate --config my-cabinet.json --llm-instructions --skill-level beginner
        cabinets generate --config my-cabinet.json --llm-instructions --llm-model mistral:7b
        cabinets generate --config my-cabinet.json --accessibility --child-safe --format safety
        cabinets generate --config my-cabinet.json --seismic-zone D --format safety
        cabinets generate --config kitchen-zone.json --format cutlist
    """
    # Validate skill_level option
    valid_skill_levels = {"beginner", "intermediate", "expert"}
    if skill_level not in valid_skill_levels:
        typer.echo(
            f"Error: Invalid skill level '{skill_level}'. "
            f"Choose from: {', '.join(sorted(valid_skill_levels))}",
            err=True,
        )
        raise typer.Exit(code=1)

    # Determine input source and create DTOs
    section_specs = None  # Will be set if config has section specifications
    row_specs = None  # Will be set if config has row specifications
    bin_packing_config: BinPackingConfig | None = (
        None  # Will be set if bin packing is configured
    )
    config = None  # Will be set if config file is loaded

    if config_file is not None:
        # Load configuration from file
        try:
            config = load_config(config_file)
        except ConfigError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)

        # Merge with CLI overrides
        config = merge_config_with_cli(
            config,
            width=width,
            height=height,
            depth=depth,
            material_thickness=thickness,
            output_format=output_format,
            stl_file=output_file,
        )

        # Convert to DTOs
        wall_input, params_input = config_to_dtos(config)

        # Check if config has row or section specifications
        # Only use specs if CLI doesn't override sections/shelves
        if sections is None and shelves is None:
            if has_row_specs(config):
                # Multi-row layout - use row specs
                row_specs = config_to_row_specs(config)
            elif has_section_specs(config):
                # Single-row with explicit sections
                section_specs = config_to_section_specs(config)
        else:
            # Override sections/shelves if provided via CLI
            if sections is not None:
                params_input.num_sections = sections
            if shelves is not None:
                params_input.shelves_per_section = shelves

        # Use format from config if not overridden
        if output_format is None:
            output_format = config.output.format
        # Use stl_file from config if not overridden
        if output_file is None and config.output.stl_file:
            output_file = Path(config.output.stl_file)

        # Extract bin packing config from configuration file
        if config.bin_packing is not None:
            bin_packing_config = config_to_bin_packing(config.bin_packing)
    else:
        # CLI-only mode: require width, height, depth
        if width is None or height is None or depth is None:
            typer.echo(
                "Error: --width, --height, and --depth are required when --config is not provided",
                err=True,
            )
            raise typer.Exit(code=1)

        wall_input = WallInput(width=width, height=height, depth=depth)
        params_input = LayoutParametersInput(
            num_sections=sections if sections is not None else 1,
            shelves_per_section=shelves if shelves is not None else 3,
            material_thickness=thickness if thickness is not None else 0.75,
        )

    # Enable bin packing via --optimize flag if not already configured
    if optimize and bin_packing_config is None:
        bin_packing_config = BinPackingConfig(enabled=True)
    # If --optimize is used but config has bin_packing disabled, override it
    elif optimize and bin_packing_config is not None and not bin_packing_config.enabled:
        # Create new config with enabled=True but preserve other settings
        bin_packing_config = BinPackingConfig(
            enabled=True,
            sheet_size=bin_packing_config.sheet_size,
            kerf=bin_packing_config.kerf,
            min_offcut_size=bin_packing_config.min_offcut_size,
        )

    # Set default output format if not specified
    if output_format is None:
        output_format = "all"

    # Build installation config from CLI options and/or config file
    installation_config = None
    if config_file is not None and config is not None:
        # Start with config file installation settings
        installation_dict = config_to_installation(config)
        if installation_dict is not None:
            installation_config = build_installation_config(installation_dict)

    # Override with CLI options if provided
    if wall_type or stud_spacing or mounting_system or expected_load:
        installation_config = build_installation_config_from_cli(
            wall_type=wall_type,
            stud_spacing=stud_spacing,
            mounting_system=mounting_system,
            expected_load=expected_load,
            base_config=installation_config,
        )

    # Build safety config from CLI options and/or config file (FRD-21)
    safety_config = None
    has_safety_cli_options = (
        safety_factor != 4.0
        or accessibility
        or child_safe
        or seismic_zone is not None
        or material_cert != "unknown"
        or no_clearance_check
    )

    if config_file is not None and config is not None and config.safety is not None:
        # Start with config file safety settings
        safety_config = config_to_safety(config.safety)
        # CLI overrides if explicitly set
        if has_safety_cli_options:
            from cabinets.domain.services.safety import SafetyConfig
            from cabinets.domain.value_objects import (
                MaterialCertification,
                SeismicZone,
            )

            # Merge CLI overrides with config file base
            new_kwargs = {
                "accessibility_enabled": safety_config.accessibility_enabled
                or accessibility,
                "accessibility_standard": safety_config.accessibility_standard,
                "child_safe_mode": safety_config.child_safe_mode or child_safe,
                "seismic_zone": safety_config.seismic_zone,
                "safety_factor": safety_factor
                if safety_factor != 4.0
                else safety_config.safety_factor,
                "deflection_limit_ratio": safety_config.deflection_limit_ratio,
                "check_clearances": not no_clearance_check
                if no_clearance_check
                else safety_config.check_clearances,
                "generate_labels": safety_config.generate_labels,
                "material_certification": safety_config.material_certification,
                "finish_voc_category": safety_config.finish_voc_category,
            }
            # Handle seismic zone CLI override
            if seismic_zone is not None:
                seismic_zone_upper = seismic_zone.upper()
                if seismic_zone_upper in ("A", "B", "C", "D", "E", "F"):
                    new_kwargs["seismic_zone"] = SeismicZone(seismic_zone_upper)
            # Handle material cert CLI override
            if material_cert != "unknown":
                cert_map = {
                    "carb_phase2": MaterialCertification.CARB_PHASE2,
                    "naf": MaterialCertification.NAF,
                    "ulef": MaterialCertification.ULEF,
                    "none": MaterialCertification.NONE,
                    "unknown": MaterialCertification.UNKNOWN,
                }
                new_kwargs["material_certification"] = cert_map.get(
                    material_cert.lower(), MaterialCertification.UNKNOWN
                )
            safety_config = SafetyConfig(**new_kwargs)  # type: ignore[arg-type]
    elif has_safety_cli_options or output_format in ("safety", "safety_labels"):
        # Build from CLI options only
        safety_config = build_safety_config(
            safety_factor=safety_factor,
            accessibility=accessibility,
            child_safe=child_safe,
            seismic_zone=seismic_zone,
            material_cert=material_cert,
            no_clearance_check=no_clearance_check,
        )

    # Execute command (with optional section/row specs from config)
    factory = get_factory()
    command = factory.create_generate_command()

    # Extract zone configs (toe kick, crown molding, light rail) from config
    zone_configs = None
    if config_file is not None and config is not None:
        zone_configs = config_to_zone_configs(config)

    # Check for zone stack configuration (FRD-22)
    if config is not None and config.cabinet and config.cabinet.zone_stack:
        # Zone stack mode - use ZoneLayoutService
        generate_zone_stack(
            config,
            output_format or "all",
            output_file,
            output_dir,
            output_formats,
            project_name,
        )
        return

    # Check if config has room geometry - use room layout if present
    room = None
    room_section_specs = None
    if config_file is not None and config is not None and config.room is not None:
        room = config_to_room(config)
        # For room layouts, extract all sections (from rows or flat sections)
        room_section_specs = config_to_all_section_specs(config)

    if room is not None:
        # Room layout mode - generate cabinets for each wall section
        _handle_room_layout(
            command=command,
            room=room,
            room_section_specs=room_section_specs or [],
            params_input=params_input,
            output_format=output_format,
            output_file=output_file,
            output_formats=output_formats,
            output_dir=output_dir,
            project_name=project_name,
            bin_packing_config=bin_packing_config,
            optimize=optimize,
            factory=factory,
        )
    else:
        # Single-wall cabinet mode (original behavior)
        _handle_single_cabinet(
            command=command,
            wall_input=wall_input,
            params_input=params_input,
            section_specs=section_specs,
            row_specs=row_specs,
            zone_configs=zone_configs,
            installation_config=installation_config,
            safety_config=safety_config,
            output_format=output_format,
            output_file=output_file,
            output_formats=output_formats,
            output_dir=output_dir,
            project_name=project_name,
            bin_packing_config=bin_packing_config,
            optimize=optimize,
            config_file=config_file,
            config=config,
            factory=factory,
            llm_instructions=llm_instructions,
            skill_level=skill_level,
            llm_model=llm_model,
            ollama_url=ollama_url,
            llm_timeout=llm_timeout,
            safety_factor=safety_factor,
            accessibility=accessibility,
            child_safe=child_safe,
            seismic_zone=seismic_zone,
            material_cert=material_cert,
            no_clearance_check=no_clearance_check,
        )


def _handle_room_layout(
    command,
    room,
    room_section_specs: list,
    params_input,
    output_format: str,
    output_file: Path | None,
    output_formats: str | None,
    output_dir: Path | None,
    project_name: str,
    bin_packing_config: BinPackingConfig | None,
    optimize: bool,
    factory,
) -> None:
    """Handle room layout generation mode.

    Args:
        command: The generate command.
        room: Room configuration.
        room_section_specs: Section specifications for the room.
        params_input: Layout parameters.
        output_format: Single output format.
        output_file: Optional output file path.
        output_formats: Comma-separated formats for multi-export.
        output_dir: Output directory for multi-format export.
        project_name: Project name for file naming.
        bin_packing_config: Bin packing configuration.
        optimize: Whether optimization is enabled.
        factory: Factory for creating services.
    """
    result = command.execute_room_layout(room, room_section_specs, params_input)

    # Handle errors
    if not result.is_valid:
        typer.echo("Errors:", err=True)
        for error in result.errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1)

    # Run bin packing optimization if enabled and we have cut pieces
    packing_result = None
    if bin_packing_config and bin_packing_config.enabled and result.cut_list:
        bin_packing_service = BinPackingService(bin_packing_config)
        try:
            packing_result = bin_packing_service.optimize_cut_list(result.cut_list)
            # Store in result for exporters
            result.packing_result = packing_result
        except ValueError as e:
            typer.echo(f"Warning: Bin packing failed: {e}", err=True)
            # Continue without bin packing result

    # Handle multi-format export if --output-formats is specified
    if output_formats is not None:
        handle_multi_format_export(
            output_formats,
            output_dir,
            project_name,
            result,
            optimize_enabled=optimize,
        )
        return  # Exit after multi-format export

    # Format and display output for room layout
    if output_format == "cutlayout":
        if packing_result is None:
            typer.echo(
                "Error: No bin packing result available. Use --optimize or configure bin_packing in config.",
                err=True,
            )
            raise typer.Exit(code=1)
        renderer = CutDiagramRenderer()
        if output_file is not None:
            # Save SVG files
            svgs = renderer.render_all_svg(packing_result)
            for i, svg in enumerate(svgs):
                if len(svgs) == 1:
                    svg_path = output_file
                else:
                    # Multiple sheets: sheet_1.svg, sheet_2.svg, etc.
                    stem = output_file.stem
                    suffix = output_file.suffix or ".svg"
                    svg_path = output_file.parent / f"{stem}_{i + 1}{suffix}"
                svg_path.write_text(svg)
                typer.echo(f"SVG exported to: {svg_path}")
        else:
            # Display ASCII in terminal
            typer.echo(renderer.render_all_ascii(packing_result))
        # Always show waste summary
        typer.echo()
        typer.echo(renderer.render_waste_summary(packing_result))
    elif output_format == "stl":
        if output_file is None:
            output_file = Path("cabinet.stl")
        exporter = factory.get_stl_exporter()
        if result.cabinets:
            # Export full room layout with all cabinets positioned
            exporter.export_room_layout(result, output_file)
            typer.echo(f"STL exported to: {output_file}")
            typer.echo(
                f"  {len(result.cabinets)} sections across {len(room.walls)} walls"
            )
        else:
            typer.echo("No cabinets generated for room layout", err=True)
            raise typer.Exit(code=1)
    elif output_format == "json":
        # Use ExporterRegistry for JSON console output (supports RoomLayoutOutput)
        exporter_class = ExporterRegistry.get("json")
        exporter = exporter_class()
        typer.echo(exporter.format_for_console(result))
    elif output_format == "cutlist":
        formatter = factory.get_cut_list_formatter()
        typer.echo(formatter.format(result.cut_list))
    elif output_format == "diagram":
        # For room layout diagram, group cabinets by wall
        formatter = factory.get_layout_diagram_formatter()
        # Group cabinets by wall index
        cabinets_by_wall: dict[int, list[Cabinet]] = {}
        for i, cabinet in enumerate(result.cabinets):
            wall_idx = (
                result.transforms[i].wall_index if i < len(result.transforms) else 0
            )
            if wall_idx not in cabinets_by_wall:
                cabinets_by_wall[wall_idx] = []
            cabinets_by_wall[wall_idx].append(cabinet)
        # Display grouped by wall
        for wall_idx in sorted(cabinets_by_wall.keys()):
            wall_name = (
                room.walls[wall_idx].name
                if wall_idx < len(room.walls) and room.walls[wall_idx].name
                else f"Wall {wall_idx + 1}"
            )
            typer.echo(
                f"--- {wall_name} ({len(cabinets_by_wall[wall_idx])} sections) ---"
            )
            for cabinet in cabinets_by_wall[wall_idx]:
                typer.echo(formatter.format(cabinet))
            typer.echo()
    elif output_format == "materials":
        formatter = factory.get_material_report_formatter()
        typer.echo(formatter.format(result.material_estimates, result.total_estimate))
    else:  # "all"
        # Show all outputs for room layout
        diagram_formatter = factory.get_layout_diagram_formatter()
        typer.echo(f"Room: {room.name}")
        typer.echo(f"Walls: {len(room.walls)}, Sections: {len(result.cabinets)}")
        typer.echo()
        # Group cabinets by wall index
        wall_cabinets: dict[int, list[Cabinet]] = {}
        for i, cabinet in enumerate(result.cabinets):
            wall_idx = (
                result.transforms[i].wall_index if i < len(result.transforms) else 0
            )
            if wall_idx not in wall_cabinets:
                wall_cabinets[wall_idx] = []
            wall_cabinets[wall_idx].append(cabinet)
        # Display grouped by wall
        for wall_idx in sorted(wall_cabinets.keys()):
            wall_name = (
                room.walls[wall_idx].name
                if wall_idx < len(room.walls) and room.walls[wall_idx].name
                else f"Wall {wall_idx + 1}"
            )
            typer.echo(f"--- {wall_name} ({len(wall_cabinets[wall_idx])} sections) ---")
            for cabinet in wall_cabinets[wall_idx]:
                typer.echo(diagram_formatter.format(cabinet))
            typer.echo()

        cutlist_formatter = factory.get_cut_list_formatter()
        typer.echo(cutlist_formatter.format(result.cut_list))
        typer.echo()

        material_formatter = factory.get_material_report_formatter()
        typer.echo(
            material_formatter.format(result.material_estimates, result.total_estimate)
        )

        # Add bin packing summary if available
        if packing_result is not None:
            typer.echo()
            renderer = CutDiagramRenderer()
            typer.echo(renderer.render_waste_summary(packing_result))
            typer.echo()
            typer.echo("Use --format cutlayout for detailed cut diagrams")


def _handle_single_cabinet(
    command,
    wall_input,
    params_input,
    section_specs,
    row_specs,
    zone_configs,
    installation_config,
    safety_config,
    output_format: str,
    output_file: Path | None,
    output_formats: str | None,
    output_dir: Path | None,
    project_name: str,
    bin_packing_config: BinPackingConfig | None,
    optimize: bool,
    config_file: Path | None,
    config,
    factory,
    llm_instructions: bool,
    skill_level: str,
    llm_model: str,
    ollama_url: str,
    llm_timeout: int,
    safety_factor: float,
    accessibility: bool,
    child_safe: bool,
    seismic_zone: str | None,
    material_cert: str,
    no_clearance_check: bool,
) -> None:
    """Handle single cabinet generation mode.

    Args:
        command: The generate command.
        wall_input: Wall dimensions input.
        params_input: Layout parameters.
        section_specs: Section specifications.
        row_specs: Row specifications for multi-row layouts.
        zone_configs: Zone configurations (toe kick, crown, etc.).
        installation_config: Installation configuration.
        safety_config: Safety configuration.
        output_format: Single output format.
        output_file: Optional output file path.
        output_formats: Comma-separated formats for multi-export.
        output_dir: Output directory for multi-format export.
        project_name: Project name for file naming.
        bin_packing_config: Bin packing configuration.
        optimize: Whether optimization is enabled.
        config_file: Path to config file if used.
        config: Loaded configuration.
        factory: Factory for creating services.
        llm_instructions: Whether to use LLM for assembly.
        skill_level: Skill level for instructions.
        llm_model: Ollama model name.
        ollama_url: Ollama server URL.
        llm_timeout: LLM timeout in seconds.
        safety_factor: Safety factor for calculations.
        accessibility: Enable ADA checking.
        child_safe: Enable child safety mode.
        seismic_zone: IBC seismic zone.
        material_cert: Material certification.
        no_clearance_check: Disable clearance checking.
    """
    result = command.execute(
        wall_input,
        params_input,
        section_specs=section_specs,
        row_specs=row_specs,
        zone_configs=zone_configs,
        installation_config=installation_config,
    )

    # Handle errors
    if not result.is_valid:
        typer.echo("Errors:", err=True)
        for error in result.errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1)

    # Run bin packing optimization if enabled and we have cut pieces
    packing_result = None
    if bin_packing_config and bin_packing_config.enabled and result.cut_list:
        bin_packing_service = BinPackingService(bin_packing_config)
        try:
            packing_result = bin_packing_service.optimize_cut_list(result.cut_list)
            # Store in result for potential JSON export
            result.packing_result = packing_result
        except ValueError as e:
            typer.echo(f"Warning: Bin packing failed: {e}", err=True)
            # Continue without bin packing result

    # Handle multi-format export if --output-formats is specified
    if output_formats is not None:
        handle_multi_format_export(
            output_formats,
            output_dir,
            project_name,
            result,
            optimize_enabled=optimize,
        )
        return  # Exit after multi-format export

    # Format and display output
    if output_format == "cutlayout":
        if packing_result is None:
            typer.echo(
                "Error: No bin packing result available. Use --optimize or configure bin_packing in config.",
                err=True,
            )
            raise typer.Exit(code=1)
        renderer = CutDiagramRenderer()
        if output_file is not None:
            # Save SVG files
            svgs = renderer.render_all_svg(packing_result)
            for i, svg in enumerate(svgs):
                if len(svgs) == 1:
                    svg_path = output_file
                else:
                    # Multiple sheets: sheet_1.svg, sheet_2.svg, etc.
                    stem = output_file.stem
                    suffix = output_file.suffix or ".svg"
                    svg_path = output_file.parent / f"{stem}_{i + 1}{suffix}"
                svg_path.write_text(svg)
                typer.echo(f"SVG exported to: {svg_path}")
        else:
            # Display ASCII in terminal
            typer.echo(renderer.render_all_ascii(packing_result))
        # Always show waste summary
        typer.echo()
        typer.echo(renderer.render_waste_summary(packing_result))
    elif output_format == "stl":
        if output_file is None:
            output_file = Path("cabinet.stl")
        exporter = factory.get_stl_exporter()
        exporter.export_to_file(result.cabinet, output_file)
        typer.echo(f"STL exported to: {output_file}")
    elif output_format == "json":
        # Use ExporterRegistry for JSON console output
        exporter_class = ExporterRegistry.get("json")
        exporter = exporter_class()
        typer.echo(exporter.format_for_console(result))
    elif output_format == "cutlist":
        formatter = factory.get_cut_list_formatter()
        typer.echo(formatter.format(result.cut_list))
    elif output_format == "diagram":
        formatter = factory.get_layout_diagram_formatter()
        typer.echo(formatter.format(result.cabinet))
    elif output_format == "materials":
        formatter = factory.get_material_report_formatter()
        typer.echo(formatter.format(result.material_estimates, result.total_estimate))
    elif output_format == "woodworking":
        _handle_woodworking_output(result, config_file, config, factory)
    elif output_format == "installation":
        _handle_installation_output(result, factory)
    elif output_format == "llm-assembly" or (
        output_format == "assembly" and llm_instructions
    ):
        _handle_llm_assembly_output(
            result,
            config,
            factory,
            llm_instructions,
            skill_level,
            llm_model,
            ollama_url,
            llm_timeout,
        )
    elif output_format == "safety":
        _handle_safety_output(
            result,
            safety_config,
            config_file,
            config,
            safety_factor,
            accessibility,
            child_safe,
            seismic_zone,
            material_cert,
            no_clearance_check,
        )
    elif output_format == "safety_labels":
        _handle_safety_labels_output(
            result,
            safety_config,
            config_file,
            config,
            output_dir,
            safety_factor,
            accessibility,
            child_safe,
            seismic_zone,
            material_cert,
            no_clearance_check,
        )
    else:  # "all"
        _handle_all_output(result, factory, packing_result, safety_config)


def _handle_woodworking_output(result, config_file, config, factory) -> None:
    """Handle woodworking format output."""
    from cabinets.domain.services.woodworking import WoodworkingIntelligence

    # Get woodworking config if available
    woodworking_config = None
    if config_file is not None and config is not None:
        woodworking_config = config_to_woodworking(config)

    intel = WoodworkingIntelligence(config=woodworking_config)

    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("WOODWORKING SPECIFICATIONS")
    typer.echo("=" * 60)
    typer.echo("")

    # Joinery specifications
    joinery = intel.get_joinery(result.cabinet)
    typer.echo("JOINERY:")
    for j in joinery[:10]:  # Show first 10
        joint_desc = (
            f"{j.from_panel.value} -> {j.to_panel.value}: {j.joint.joint_type.value}"
        )
        if j.joint.depth:
            joint_desc += f' (depth: {j.joint.depth:.3f}")'
        if j.joint.width:
            joint_desc += f' (width: {j.joint.width:.3f}")'
        typer.echo(f"  {joint_desc}")
    if len(joinery) > 10:
        typer.echo(f"  ... and {len(joinery) - 10} more connections")
    typer.echo("")

    # Span warnings
    warnings = intel.check_spans(result.cabinet)
    if warnings:
        typer.echo("SPAN WARNINGS:")
        for w in warnings:
            typer.echo(f"  {w.formatted_message}")
            typer.echo(f"    Suggestion: {w.suggestion}")
        typer.echo("")
    else:
        typer.echo("SPAN CHECK: All spans within limits")
        typer.echo("")

    # Weight capacity estimates
    capacities = intel.get_shelf_capacities(result.cabinet)
    if capacities:
        typer.echo("WEIGHT CAPACITY ESTIMATES:")
        typer.echo("  (Advisory only - not engineered)")
        for cap in capacities:
            typer.echo(
                f"  {cap.panel_label}: ~{cap.capacity_lbs:.0f} lbs ({cap.load_type})"
            )
        typer.echo("")

    # Hardware list
    hardware = intel.calculate_hardware(result.cabinet)
    hw_formatter = factory.get_hardware_report_formatter()
    typer.echo(hw_formatter.format(hardware, show_overage=True))


def _handle_installation_output(result, factory) -> None:
    """Handle installation format output."""
    if not result.installation_instructions:
        typer.echo("Error: No installation data available.", err=True)
        typer.echo(
            "Use --wall-type, --mounting-system, etc. or add 'installation' section to config.",
            err=True,
        )
        raise typer.Exit(code=1)

    installation_formatter = factory.get_installation_formatter()
    typer.echo(installation_formatter.format(result))
    typer.echo()
    typer.echo(installation_formatter.format_hardware_summary(result))
    typer.echo()
    typer.echo(installation_formatter.format_stud_analysis(result))


def _handle_llm_assembly_output(
    result,
    config,
    factory,
    llm_instructions: bool,
    skill_level: str,
    llm_model: str,
    ollama_url: str,
    llm_timeout: int,
) -> None:
    """Handle LLM-enhanced assembly instructions output."""
    # Determine effective settings from CLI and config
    assembly_config = (
        config.output.assembly
        if config and config.output and config.output.assembly
        else None
    )

    # CLI overrides config
    effective_model = (
        llm_model
        if llm_model != "llama3.2"
        else (assembly_config.llm_model if assembly_config else "llama3.2")
    )
    effective_skill = (
        skill_level
        if skill_level != "intermediate"
        else (assembly_config.skill_level if assembly_config else "intermediate")
    )
    effective_url = (
        ollama_url
        if ollama_url != "http://localhost:11434"
        else (
            assembly_config.ollama_url if assembly_config else "http://localhost:11434"
        )
    )
    effective_timeout = (
        llm_timeout
        if llm_timeout != 30
        else (assembly_config.timeout_seconds if assembly_config else 30)
    )
    effective_troubleshooting = (
        assembly_config.include_troubleshooting if assembly_config else True
    )
    effective_time_estimates = (
        assembly_config.include_time_estimates if assembly_config else True
    )

    typer.echo("Generating LLM-enhanced assembly instructions...")

    # Check Ollama availability
    available, message = check_ollama_sync(
        base_url=effective_url,
        model_name=effective_model,
    )

    if available:
        typer.echo(f"  Model: {effective_model}")
        typer.echo(f"  Skill level: {effective_skill}")

        from cabinets.infrastructure.llm import LLMAssemblyGenerator

        generator = LLMAssemblyGenerator(
            ollama_url=effective_url,
            model=effective_model,
            timeout=float(effective_timeout),
            skill_level=effective_skill,  # type: ignore[arg-type]
            include_troubleshooting=effective_troubleshooting,
            include_time_estimates=effective_time_estimates,
        )

        try:
            content = generator.generate_sync(result)
            typer.echo()
            typer.echo(content)
        except Exception as e:
            typer.echo(f"Warning: LLM generation failed: {e}", err=True)
            typer.echo("Falling back to template-based instructions.")
            fallback = factory.get_assembly_instruction_generator()
            content = fallback.export_string(result)
            typer.echo()
            typer.echo(content)
    else:
        typer.echo(f"Note: {message}")
        typer.echo("Using template-based assembly instructions.")
        fallback = factory.get_assembly_instruction_generator()
        content = fallback.export_string(result)
        typer.echo()
        typer.echo(content)


def _handle_safety_output(
    result,
    safety_config,
    config_file,
    config,
    safety_factor: float,
    accessibility: bool,
    child_safe: bool,
    seismic_zone: str | None,
    material_cert: str,
    no_clearance_check: bool,
) -> None:
    """Handle safety format output."""
    if safety_config is None:
        # Create default safety config
        safety_config = build_safety_config(
            safety_factor=safety_factor,
            accessibility=accessibility,
            child_safe=child_safe,
            seismic_zone=seismic_zone,
            material_cert=material_cert,
            no_clearance_check=no_clearance_check,
        )
    from cabinets.domain.services.safety import SafetyService

    safety_service = SafetyService(safety_config)

    # Get obstacles from config if available
    obstacles = []
    if config_file is not None and config is not None:
        obstacles = config_to_obstacles(config)

    # Perform safety analysis
    try:
        safety_assessment = safety_service.analyze(result.cabinet, obstacles)
        display_safety_summary(safety_assessment)
    except NotImplementedError:
        # SafetyService.analyze() is not yet fully implemented
        typer.echo("=" * 60)
        typer.echo("SAFETY ASSESSMENT")
        typer.echo("=" * 60)
        typer.echo()

        # Display what we can from available safety checks
        typer.echo("Anti-Tip Analysis:")
        anti_tip_result = safety_service.check_anti_tip_requirement(result.cabinet)
        typer.echo(f"  {anti_tip_result.formatted_message}")
        if anti_tip_result.remediation:
            typer.echo(f"    Suggestion: {anti_tip_result.remediation}")
        typer.echo()

        typer.echo("Weight Capacities:")
        capacities = safety_service.get_shelf_capacities(result.cabinet)
        for cap in capacities:
            typer.echo(f"  {cap.formatted_message}")
        typer.echo()

        typer.echo("Material Compliance:")
        material_result = safety_service.check_material_compliance()
        typer.echo(f"  {material_result.formatted_message}")
        typer.echo()

        typer.echo("Seismic Requirements:")
        seismic_result = safety_service.check_seismic_requirements()
        typer.echo(f"  {seismic_result.formatted_message}")
        typer.echo()

        typer.echo(
            "Note: Safety estimates are advisory only. "
            "Consult professionals for critical installations."
        )


def _handle_safety_labels_output(
    result,
    safety_config,
    config_file,
    config,
    output_dir,
    safety_factor: float,
    accessibility: bool,
    child_safe: bool,
    seismic_zone: str | None,
    material_cert: str,
    no_clearance_check: bool,
) -> None:
    """Handle safety labels format output."""
    if safety_config is None:
        safety_config = build_safety_config(
            safety_factor=safety_factor,
            accessibility=accessibility,
            child_safe=child_safe,
            seismic_zone=seismic_zone,
            material_cert=material_cert,
            no_clearance_check=no_clearance_check,
        )
    from cabinets.domain.services.safety import SafetyService, SafetyAssessment

    safety_service = SafetyService(safety_config)

    # Get obstacles from config if available
    obstacles = []
    if config_file is not None and config is not None:
        obstacles = config_to_obstacles(config)

    # Try to perform full analysis, fall back to partial
    try:
        safety_assessment = safety_service.analyze(result.cabinet, obstacles)
    except NotImplementedError:
        # Create a partial assessment with what we can compute
        anti_tip_result = safety_service.check_anti_tip_requirement(result.cabinet)
        capacities = safety_service.get_shelf_capacities(result.cabinet)
        labels = safety_service.generate_safety_labels(
            SafetyAssessment(
                check_results=[anti_tip_result],
                weight_capacities=capacities,
                accessibility_report=None,
                safety_labels=[],
                anti_tip_required=anti_tip_result.details.get(
                    "anti_tip_required", False
                ),
                seismic_hardware=safety_service.get_seismic_hardware(),
            )
        )
        safety_assessment = SafetyAssessment(
            check_results=[anti_tip_result],
            weight_capacities=capacities,
            accessibility_report=None,
            safety_labels=labels,
            anti_tip_required=anti_tip_result.details.get("anti_tip_required", False),
            seismic_hardware=safety_service.get_seismic_hardware(),
        )

    export_safety_labels(safety_assessment, output_dir)


def _handle_all_output(result, factory, packing_result, safety_config) -> None:
    """Handle 'all' format output - show all outputs."""
    diagram_formatter = factory.get_layout_diagram_formatter()
    typer.echo(diagram_formatter.format(result.cabinet))
    typer.echo()

    cutlist_formatter = factory.get_cut_list_formatter()
    typer.echo(cutlist_formatter.format(result.cut_list))
    typer.echo()

    material_formatter = factory.get_material_report_formatter()
    typer.echo(
        material_formatter.format(result.material_estimates, result.total_estimate)
    )

    # Add bin packing summary if available
    if packing_result is not None:
        typer.echo()
        renderer = CutDiagramRenderer()
        typer.echo(renderer.render_waste_summary(packing_result))
        typer.echo()
        typer.echo("Use --format cutlayout for detailed cut diagrams")

    # Add installation summary if available
    if result.installation_instructions:
        typer.echo()
        typer.echo("=" * 60)
        typer.echo("INSTALLATION SUMMARY")
        typer.echo("=" * 60)
        installation_formatter = factory.get_installation_formatter()
        typer.echo(installation_formatter.format_hardware_summary(result))
        typer.echo()
        typer.echo(installation_formatter.format_stud_analysis(result))
        typer.echo()
        typer.echo("Use --format installation for full instructions")

    # Add safety summary if safety config is present (FRD-21)
    if safety_config is not None:
        from cabinets.domain.services.safety import SafetyService

        safety_service = SafetyService(safety_config)

        typer.echo()
        typer.echo("=" * 60)
        typer.echo("SAFETY SUMMARY")
        typer.echo("=" * 60)

        # Display key safety checks
        anti_tip_result = safety_service.check_anti_tip_requirement(result.cabinet)
        typer.echo(f"Stability: {anti_tip_result.formatted_message}")

        material_result = safety_service.check_material_compliance()
        typer.echo(f"Material: {material_result.formatted_message}")

        if safety_config.seismic_zone:
            seismic_result = safety_service.check_seismic_requirements()
            typer.echo(f"Seismic: {seismic_result.formatted_message}")

        typer.echo()
        typer.echo("Use --format safety for full safety analysis")
