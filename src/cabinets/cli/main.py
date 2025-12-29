"""Typer CLI for cabinet generation."""

from pathlib import Path
from typing import Annotated

import typer

from cabinets.application import (
    GenerateLayoutCommand,
    LayoutParametersInput,
    WallInput,
)
from cabinets.domain import Cabinet
from cabinets.application.config import (
    ConfigError,
    config_to_all_section_specs,
    config_to_bin_packing,
    config_to_dtos,
    config_to_installation,
    config_to_room,
    config_to_row_specs,
    config_to_section_specs,
    config_to_woodworking,
    config_to_zone_configs,
    has_row_specs,
    has_section_specs,
    load_config,
    merge_config_with_cli,
)
from cabinets.infrastructure import (
    BinPackingConfig,
    BinPackingService,
    CutDiagramRenderer,
    CutListFormatter,
    HardwareReportFormatter,
    InstallationFormatter,
    JsonExporter,
    LayoutDiagramFormatter,
    MaterialReportFormatter,
    StlExporter,
)
from cabinets.infrastructure.exporters import ExporterRegistry, ExportManager
from cabinets.cli.commands import validate_command, templates_app


def _handle_multi_format_export(
    output_formats_str: str,
    output_dir: Path | None,
    project_name: str,
    result,  # LayoutOutput or RoomLayoutOutput
    optimize_enabled: bool,
) -> bool:
    """Handle multi-format export via --output-formats option.

    Args:
        output_formats_str: Comma-separated format list or "all".
        output_dir: Output directory for exported files.
        project_name: Project name for file naming.
        result: The layout output to export.
        optimize_enabled: Whether bin packing optimization was enabled.

    Returns:
        True if multi-format export was handled (caller should exit),
        False if not applicable.
    """
    # Parse formats
    if output_formats_str.lower() == "all":
        formats = ExporterRegistry.available_formats()
    else:
        formats = [f.strip().lower() for f in output_formats_str.split(",")]

    # Validate formats
    available = ExporterRegistry.available_formats()
    invalid = [f for f in formats if f not in available]
    if invalid:
        typer.echo(f"Unknown formats: {', '.join(invalid)}", err=True)
        typer.echo(f"Available formats: {', '.join(available)}", err=True)
        raise typer.Exit(code=1)

    # Check if SVG is requested but no packing result
    packing_result = getattr(result, "packing_result", None)
    if "svg" in formats and packing_result is None:
        if optimize_enabled:
            typer.echo(
                "Warning: SVG export skipped - bin packing failed or no cut pieces.",
                err=True,
            )
            formats = [f for f in formats if f != "svg"]
        else:
            typer.echo(
                "Warning: SVG export requires --optimize flag. Skipping SVG.",
                err=True,
            )
            formats = [f for f in formats if f != "svg"]

    if not formats:
        typer.echo("No valid formats to export.", err=True)
        raise typer.Exit(code=1)

    # Set up output directory
    out_dir = output_dir or Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Export all formats
    manager = ExportManager(out_dir)
    try:
        files = manager.export_all(formats, result, project_name)
    except Exception as e:
        typer.echo(f"Export error: {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo("\nExported files:")
    for fmt, path in files.items():
        typer.echo(f"  {fmt.upper()}: {path}")

    return True


def _build_installation_config(config_dict: dict) -> "InstallationConfig":
    """Build InstallationConfig from config dictionary.

    Args:
        config_dict: Dictionary from config_to_installation().

    Returns:
        InstallationConfig domain object.
    """
    from cabinets.domain.services.installation import InstallationConfig

    kwargs = {
        "wall_type": config_dict["wall_type"],
        "wall_thickness": config_dict.get("wall_thickness", 0.5),
        "stud_spacing": config_dict.get("stud_spacing", 16.0),
        "stud_offset": config_dict.get("stud_offset", 0.0),
        "mounting_system": config_dict["mounting_system"],
        "expected_load": config_dict["expected_load"],
    }

    # Add cleat configuration if present
    if config_dict.get("cleat"):
        cleat = config_dict["cleat"]
        kwargs["cleat_position_from_top"] = cleat.get("position_from_top", 4.0)
        kwargs["cleat_width_percentage"] = cleat.get("width_percentage", 90.0)
        kwargs["cleat_bevel_angle"] = cleat.get("bevel_angle", 45.0)

    return InstallationConfig(**kwargs)


def _build_installation_config_from_cli(
    wall_type: str | None = None,
    stud_spacing: float | None = None,
    mounting_system: str | None = None,
    expected_load: str | None = None,
    base_config: "InstallationConfig | None" = None,
) -> "InstallationConfig":
    """Build InstallationConfig from CLI options.

    Args:
        wall_type: Wall type string from CLI.
        stud_spacing: Stud spacing from CLI.
        mounting_system: Mounting system string from CLI.
        expected_load: Expected load category string from CLI.
        base_config: Optional base config to override.

    Returns:
        InstallationConfig domain object.
    """
    from cabinets.domain.services.installation import InstallationConfig
    from cabinets.domain.value_objects import LoadCategory, MountingSystem, WallType

    # Start with base config values or defaults
    if base_config:
        kwargs = {
            "wall_type": base_config.wall_type,
            "wall_thickness": base_config.wall_thickness,
            "stud_spacing": base_config.stud_spacing,
            "stud_offset": base_config.stud_offset,
            "mounting_system": base_config.mounting_system,
            "expected_load": base_config.expected_load,
            "cleat_position_from_top": base_config.cleat_position_from_top,
            "cleat_width_percentage": base_config.cleat_width_percentage,
            "cleat_bevel_angle": base_config.cleat_bevel_angle,
        }
    else:
        kwargs = {}

    # Override with CLI options
    if wall_type:
        wall_type_map = {
            "drywall": WallType.DRYWALL,
            "plaster": WallType.PLASTER,
            "concrete": WallType.CONCRETE,
            "cmu": WallType.CMU,
            "brick": WallType.BRICK,
        }
        kwargs["wall_type"] = wall_type_map.get(wall_type.lower(), WallType.DRYWALL)

    if stud_spacing:
        kwargs["stud_spacing"] = stud_spacing

    if mounting_system:
        mounting_map = {
            "direct_to_stud": MountingSystem.DIRECT_TO_STUD,
            "french_cleat": MountingSystem.FRENCH_CLEAT,
            "hanging_rail": MountingSystem.HANGING_RAIL,
            "toggle_bolt": MountingSystem.TOGGLE_BOLT,
        }
        kwargs["mounting_system"] = mounting_map.get(
            mounting_system.lower(), MountingSystem.DIRECT_TO_STUD
        )

    if expected_load:
        load_map = {
            "light": LoadCategory.LIGHT,
            "medium": LoadCategory.MEDIUM,
            "heavy": LoadCategory.HEAVY,
        }
        kwargs["expected_load"] = load_map.get(expected_load.lower(), LoadCategory.MEDIUM)

    return InstallationConfig(**kwargs)


# Type hint for forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cabinets.domain.services.installation import InstallationConfig


app = typer.Typer(
    name="cabinets",
    help="Generate built-in cabinets and shelves from wall dimensions.",
)

# Register validate command
app.command(name="validate")(validate_command)

# Register templates subcommand group
app.add_typer(templates_app, name="templates")


@app.command()
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
        typer.Option("--format", "-f", help="Output format: all, cutlist, diagram, materials, json, stl, cutlayout, woodworking, installation"),
    ] = None,
    optimize: Annotated[
        bool,
        typer.Option("--optimize", help="Enable bin packing optimization for cut layout"),
    ] = False,
    output_file: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (required for stl format)"),
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
) -> None:
    """Generate a cabinet layout from wall dimensions.

    You can provide dimensions via CLI options or via a JSON configuration file.
    When using --config, CLI options override config file values.

    Examples:
        cabinets generate --width 48 --height 84 --depth 12
        cabinets generate --config my-cabinet.json
        cabinets generate --config my-cabinet.json --width 60
        cabinets generate --config my-cabinet.json --output-formats stl,json --output-dir ./output
        cabinets generate --config my-cabinet.json --output-formats all --output-dir ./output --optimize
    """
    # Determine input source and create DTOs
    section_specs = None  # Will be set if config has section specifications
    row_specs = None  # Will be set if config has row specifications
    bin_packing_config: BinPackingConfig | None = None  # Will be set if bin packing is configured
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
            installation_config = _build_installation_config(installation_dict)

    # Override with CLI options if provided
    if wall_type or stud_spacing or mounting_system or expected_load:
        installation_config = _build_installation_config_from_cli(
            wall_type=wall_type,
            stud_spacing=stud_spacing,
            mounting_system=mounting_system,
            expected_load=expected_load,
            base_config=installation_config,
        )

    # Execute command (with optional section/row specs from config)
    command = GenerateLayoutCommand()

    # Extract zone configs (toe kick, crown molding, light rail) from config
    zone_configs = None
    if config_file is not None:
        zone_configs = config_to_zone_configs(config)

    # Check if config has room geometry - use room layout if present
    room = None
    room_section_specs = None
    if config_file is not None and config.room is not None:
        room = config_to_room(config)
        # For room layouts, extract all sections (from rows or flat sections)
        room_section_specs = config_to_all_section_specs(config)

    if room is not None:
        # Room layout mode - generate cabinets for each wall section
        result = command.execute_room_layout(room, room_section_specs or [], params_input)

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
            _handle_multi_format_export(
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
                typer.echo("Error: No bin packing result available. Use --optimize or configure bin_packing in config.", err=True)
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
                        svg_path = output_file.parent / f"{stem}_{i+1}{suffix}"
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
            exporter = StlExporter()
            if result.cabinets:
                # Export full room layout with all cabinets positioned
                exporter.export_room_layout(result, output_file)
                typer.echo(f"STL exported to: {output_file}")
                typer.echo(f"  {len(result.cabinets)} sections across {len(room.walls)} walls")
            else:
                typer.echo("No cabinets generated for room layout", err=True)
                raise typer.Exit(code=1)
        elif output_format == "json":
            # JSON export for room layout - output basic info
            import json
            room_data = {
                "room": room.name,
                "cabinets": len(result.cabinets),
                "walls": len(room.walls),
                "cut_list": [
                    {"label": cp.label, "width": cp.width, "height": cp.height, "quantity": cp.quantity}
                    for cp in result.cut_list
                ],
            }
            typer.echo(json.dumps(room_data, indent=2))
        elif output_format == "cutlist":
            formatter = CutListFormatter()
            typer.echo(formatter.format(result.cut_list))
        elif output_format == "diagram":
            # For room layout diagram, group cabinets by wall
            formatter = LayoutDiagramFormatter()
            # Group cabinets by wall index
            cabinets_by_wall: dict[int, list[Cabinet]] = {}
            for i, cabinet in enumerate(result.cabinets):
                wall_idx = result.transforms[i].wall_index if i < len(result.transforms) else 0
                if wall_idx not in cabinets_by_wall:
                    cabinets_by_wall[wall_idx] = []
                cabinets_by_wall[wall_idx].append(cabinet)
            # Display grouped by wall
            for wall_idx in sorted(cabinets_by_wall.keys()):
                wall_name = room.walls[wall_idx].name if wall_idx < len(room.walls) and room.walls[wall_idx].name else f"Wall {wall_idx + 1}"
                typer.echo(f"--- {wall_name} ({len(cabinets_by_wall[wall_idx])} sections) ---")
                for cabinet in cabinets_by_wall[wall_idx]:
                    typer.echo(formatter.format(cabinet))
                typer.echo()
        elif output_format == "materials":
            formatter = MaterialReportFormatter()
            typer.echo(formatter.format(result.material_estimates, result.total_estimate))
        else:  # "all"
            # Show all outputs for room layout
            diagram_formatter = LayoutDiagramFormatter()
            typer.echo(f"Room: {room.name}")
            typer.echo(f"Walls: {len(room.walls)}, Sections: {len(result.cabinets)}")
            typer.echo()
            # Group cabinets by wall index
            cabinets_by_wall: dict[int, list[Cabinet]] = {}
            for i, cabinet in enumerate(result.cabinets):
                wall_idx = result.transforms[i].wall_index if i < len(result.transforms) else 0
                if wall_idx not in cabinets_by_wall:
                    cabinets_by_wall[wall_idx] = []
                cabinets_by_wall[wall_idx].append(cabinet)
            # Display grouped by wall
            for wall_idx in sorted(cabinets_by_wall.keys()):
                wall_name = room.walls[wall_idx].name if wall_idx < len(room.walls) and room.walls[wall_idx].name else f"Wall {wall_idx + 1}"
                typer.echo(f"--- {wall_name} ({len(cabinets_by_wall[wall_idx])} sections) ---")
                for cabinet in cabinets_by_wall[wall_idx]:
                    typer.echo(diagram_formatter.format(cabinet))
                typer.echo()

            cutlist_formatter = CutListFormatter()
            typer.echo(cutlist_formatter.format(result.cut_list))
            typer.echo()

            material_formatter = MaterialReportFormatter()
            typer.echo(material_formatter.format(result.material_estimates, result.total_estimate))

            # Add bin packing summary if available
            if packing_result is not None:
                typer.echo()
                renderer = CutDiagramRenderer()
                typer.echo(renderer.render_waste_summary(packing_result))
                typer.echo()
                typer.echo("Use --format cutlayout for detailed cut diagrams")
    else:
        # Single-wall cabinet mode (original behavior)
        result = command.execute(
            wall_input, params_input, section_specs=section_specs, row_specs=row_specs,
            zone_configs=zone_configs, installation_config=installation_config
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
            _handle_multi_format_export(
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
                typer.echo("Error: No bin packing result available. Use --optimize or configure bin_packing in config.", err=True)
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
                        svg_path = output_file.parent / f"{stem}_{i+1}{suffix}"
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
            exporter = StlExporter()
            exporter.export_to_file(result.cabinet, output_file)
            typer.echo(f"STL exported to: {output_file}")
        elif output_format == "json":
            exporter = JsonExporter()
            typer.echo(exporter.export(result))
        elif output_format == "cutlist":
            formatter = CutListFormatter()
            typer.echo(formatter.format(result.cut_list))
        elif output_format == "diagram":
            formatter = LayoutDiagramFormatter()
            typer.echo(formatter.format(result.cabinet))
        elif output_format == "materials":
            formatter = MaterialReportFormatter()
            typer.echo(formatter.format(result.material_estimates, result.total_estimate))
        elif output_format == "woodworking":
            # Woodworking intelligence output
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
                joint_desc = f"{j.from_panel.value} -> {j.to_panel.value}: {j.joint.joint_type.value}"
                if j.joint.depth:
                    joint_desc += f" (depth: {j.joint.depth:.3f}\")"
                if j.joint.width:
                    joint_desc += f" (width: {j.joint.width:.3f}\")"
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
                    typer.echo(f"  {cap.panel_label}: ~{cap.capacity_lbs:.0f} lbs ({cap.load_type})")
                typer.echo("")

            # Hardware list
            hardware = intel.calculate_hardware(result.cabinet)
            hw_formatter = HardwareReportFormatter()
            typer.echo(hw_formatter.format(hardware, show_overage=True))
        elif output_format == "installation":
            # Installation instructions output (FRD-17)
            if not result.installation_instructions:
                typer.echo("Error: No installation data available.", err=True)
                typer.echo("Use --wall-type, --mounting-system, etc. or add 'installation' section to config.", err=True)
                raise typer.Exit(code=1)

            installation_formatter = InstallationFormatter()
            typer.echo(installation_formatter.format(result))
            typer.echo()
            typer.echo(installation_formatter.format_hardware_summary(result))
            typer.echo()
            typer.echo(installation_formatter.format_stud_analysis(result))
        else:  # "all"
            # Show all outputs
            diagram_formatter = LayoutDiagramFormatter()
            typer.echo(diagram_formatter.format(result.cabinet))
            typer.echo()

            cutlist_formatter = CutListFormatter()
            typer.echo(cutlist_formatter.format(result.cut_list))
            typer.echo()

            material_formatter = MaterialReportFormatter()
            typer.echo(material_formatter.format(result.material_estimates, result.total_estimate))

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
                installation_formatter = InstallationFormatter()
                typer.echo(installation_formatter.format_hardware_summary(result))
                typer.echo()
                typer.echo(installation_formatter.format_stud_analysis(result))
                typer.echo()
                typer.echo("Use --format installation for full instructions")


@app.command()
def cutlist(
    width: Annotated[float, typer.Option("--width", "-w", help="Wall width in inches")],
    height: Annotated[float, typer.Option("--height", "-h", help="Wall height in inches")],
    depth: Annotated[float, typer.Option("--depth", "-d", help="Cabinet depth in inches")],
    sections: Annotated[int, typer.Option("--sections", "-s", help="Number of vertical sections")] = 1,
    shelves: Annotated[int, typer.Option("--shelves", help="Shelves per section")] = 3,
    thickness: Annotated[float, typer.Option("--thickness", "-t", help="Material thickness in inches")] = 0.75,
) -> None:
    """Display cut list for a cabinet."""
    wall_input = WallInput(width=width, height=height, depth=depth)
    params_input = LayoutParametersInput(
        num_sections=sections,
        shelves_per_section=shelves,
        material_thickness=thickness,
    )

    command = GenerateLayoutCommand()
    result = command.execute(wall_input, params_input)

    if not result.is_valid:
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)

    formatter = CutListFormatter()
    typer.echo(formatter.format(result.cut_list))


@app.command()
def materials(
    width: Annotated[float, typer.Option("--width", "-w", help="Wall width in inches")],
    height: Annotated[float, typer.Option("--height", "-h", help="Wall height in inches")],
    depth: Annotated[float, typer.Option("--depth", "-d", help="Cabinet depth in inches")],
    sections: Annotated[int, typer.Option("--sections", "-s", help="Number of vertical sections")] = 1,
    shelves: Annotated[int, typer.Option("--shelves", help="Shelves per section")] = 3,
    thickness: Annotated[float, typer.Option("--thickness", "-t", help="Material thickness in inches")] = 0.75,
) -> None:
    """Show material estimate for a cabinet."""
    wall_input = WallInput(width=width, height=height, depth=depth)
    params_input = LayoutParametersInput(
        num_sections=sections,
        shelves_per_section=shelves,
        material_thickness=thickness,
    )

    command = GenerateLayoutCommand()
    result = command.execute(wall_input, params_input)

    if not result.is_valid:
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)

    formatter = MaterialReportFormatter()
    typer.echo(formatter.format(result.material_estimates, result.total_estimate))


@app.command()
def diagram(
    width: Annotated[float, typer.Option("--width", "-w", help="Wall width in inches")],
    height: Annotated[float, typer.Option("--height", "-h", help="Wall height in inches")],
    depth: Annotated[float, typer.Option("--depth", "-d", help="Cabinet depth in inches")],
    sections: Annotated[int, typer.Option("--sections", "-s", help="Number of vertical sections")] = 1,
    shelves: Annotated[int, typer.Option("--shelves", help="Shelves per section")] = 3,
    thickness: Annotated[float, typer.Option("--thickness", "-t", help="Material thickness in inches")] = 0.75,
) -> None:
    """Show ASCII diagram of a cabinet layout."""
    wall_input = WallInput(width=width, height=height, depth=depth)
    params_input = LayoutParametersInput(
        num_sections=sections,
        shelves_per_section=shelves,
        material_thickness=thickness,
    )

    command = GenerateLayoutCommand()
    result = command.execute(wall_input, params_input)

    if not result.is_valid:
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)

    formatter = LayoutDiagramFormatter()
    typer.echo(formatter.format(result.cabinet))


if __name__ == "__main__":
    app()
