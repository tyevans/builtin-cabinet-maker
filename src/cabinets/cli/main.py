"""Typer CLI for cabinet generation.

This module provides the main CLI entry point for the cabinets application.
The complex generate command logic has been extracted to cli/commands/ for
better maintainability following Single Responsibility Principle.
"""

from __future__ import annotations

from typing import Annotated

import typer

from cabinets.application import (
    LayoutParametersInput,
    WallInput,
)
from cabinets.application.factory import get_factory
from cabinets.cli.commands import validate_command, templates_app
from cabinets.cli.commands.generate import generate

__all__ = ["app", "generate", "cutlist", "materials", "diagram"]

app = typer.Typer(
    name="cabinets",
    help="Generate built-in cabinets and shelves from wall dimensions.",
)

# Register validate command
app.command(name="validate")(validate_command)

# Register templates subcommand group
app.add_typer(templates_app, name="templates")

# Register generate command from extracted module
app.command()(generate)


@app.command()
def cutlist(
    width: Annotated[float, typer.Option("--width", "-w", help="Wall width in inches")],
    height: Annotated[
        float, typer.Option("--height", "-h", help="Wall height in inches")
    ],
    depth: Annotated[
        float, typer.Option("--depth", "-d", help="Cabinet depth in inches")
    ],
    sections: Annotated[
        int, typer.Option("--sections", "-s", help="Number of vertical sections")
    ] = 1,
    shelves: Annotated[int, typer.Option("--shelves", help="Shelves per section")] = 3,
    thickness: Annotated[
        float, typer.Option("--thickness", "-t", help="Material thickness in inches")
    ] = 0.75,
) -> None:
    """Display cut list for a cabinet."""
    wall_input = WallInput(width=width, height=height, depth=depth)
    params_input = LayoutParametersInput(
        num_sections=sections,
        shelves_per_section=shelves,
        material_thickness=thickness,
    )

    factory = get_factory()
    command = factory.create_generate_command()
    result = command.execute(wall_input, params_input)

    if not result.is_valid:
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)

    formatter = factory.get_cut_list_formatter()
    typer.echo(formatter.format(result.cut_list))


@app.command()
def materials(
    width: Annotated[float, typer.Option("--width", "-w", help="Wall width in inches")],
    height: Annotated[
        float, typer.Option("--height", "-h", help="Wall height in inches")
    ],
    depth: Annotated[
        float, typer.Option("--depth", "-d", help="Cabinet depth in inches")
    ],
    sections: Annotated[
        int, typer.Option("--sections", "-s", help="Number of vertical sections")
    ] = 1,
    shelves: Annotated[int, typer.Option("--shelves", help="Shelves per section")] = 3,
    thickness: Annotated[
        float, typer.Option("--thickness", "-t", help="Material thickness in inches")
    ] = 0.75,
) -> None:
    """Show material estimate for a cabinet."""
    wall_input = WallInput(width=width, height=height, depth=depth)
    params_input = LayoutParametersInput(
        num_sections=sections,
        shelves_per_section=shelves,
        material_thickness=thickness,
    )

    factory = get_factory()
    command = factory.create_generate_command()
    result = command.execute(wall_input, params_input)

    if not result.is_valid:
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)

    formatter = factory.get_material_report_formatter()
    typer.echo(formatter.format(result.material_estimates, result.total_estimate))


@app.command()
def diagram(
    width: Annotated[float, typer.Option("--width", "-w", help="Wall width in inches")],
    height: Annotated[
        float, typer.Option("--height", "-h", help="Wall height in inches")
    ],
    depth: Annotated[
        float, typer.Option("--depth", "-d", help="Cabinet depth in inches")
    ],
    sections: Annotated[
        int, typer.Option("--sections", "-s", help="Number of vertical sections")
    ] = 1,
    shelves: Annotated[int, typer.Option("--shelves", help="Shelves per section")] = 3,
    thickness: Annotated[
        float, typer.Option("--thickness", "-t", help="Material thickness in inches")
    ] = 0.75,
) -> None:
    """Show ASCII diagram of a cabinet layout."""
    wall_input = WallInput(width=width, height=height, depth=depth)
    params_input = LayoutParametersInput(
        num_sections=sections,
        shelves_per_section=shelves,
        material_thickness=thickness,
    )

    factory = get_factory()
    command = factory.create_generate_command()
    result = command.execute(wall_input, params_input)

    if not result.is_valid:
        for error in result.errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)

    formatter = factory.get_layout_diagram_formatter()
    typer.echo(formatter.format(result.cabinet))


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", help="Host to bind to")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind to")] = 8000,
    reload: Annotated[
        bool, typer.Option("--reload", help="Enable auto-reload for development")
    ] = False,
) -> None:
    """Start the REST API server.

    Requires the 'web' optional dependencies:
        uv pip install -e ".[web]"
    """
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "Error: FastAPI/uvicorn not installed. "
            "Install with: uv pip install -e '.[web]'",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Starting Cabinet API server at http://{host}:{port}")
    typer.echo("API docs available at http://{host}:{port}/docs")
    uvicorn.run(
        "cabinets.web:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
