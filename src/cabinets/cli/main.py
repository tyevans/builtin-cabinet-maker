"""Typer CLI for cabinet generation."""

from pathlib import Path
from typing import Annotated

import typer

from cabinets.application import (
    GenerateLayoutCommand,
    LayoutParametersInput,
    WallInput,
)
from cabinets.application.config import (
    ConfigError,
    config_to_dtos,
    config_to_section_specs,
    has_section_specs,
    load_config,
    merge_config_with_cli,
)
from cabinets.infrastructure import (
    CutListFormatter,
    JsonExporter,
    LayoutDiagramFormatter,
    MaterialReportFormatter,
    StlExporter,
)
from cabinets.cli.commands import validate_command, templates_app

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
        typer.Option("--format", "-f", help="Output format: all, cutlist, diagram, materials, json, stl"),
    ] = None,
    output_file: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (required for stl format)"),
    ] = None,
) -> None:
    """Generate a cabinet layout from wall dimensions.

    You can provide dimensions via CLI options or via a JSON configuration file.
    When using --config, CLI options override config file values.

    Examples:
        cabinets generate --width 48 --height 84 --depth 12
        cabinets generate --config my-cabinet.json
        cabinets generate --config my-cabinet.json --width 60
    """
    # Determine input source and create DTOs
    section_specs = None  # Will be set if config has section specifications

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

        # Check if config has section specifications
        # Only use section specs if CLI doesn't override sections/shelves
        if has_section_specs(config) and sections is None and shelves is None:
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

    # Set default output format if not specified
    if output_format is None:
        output_format = "all"

    # Execute command (with optional section specs from config)
    command = GenerateLayoutCommand()
    result = command.execute(wall_input, params_input, section_specs=section_specs)

    # Handle errors
    if not result.is_valid:
        typer.echo("Errors:", err=True)
        for error in result.errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1)

    # Format and display output
    if output_format == "stl":
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
