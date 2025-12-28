"""Templates commands for listing and initializing cabinet templates.

This module provides the `templates` command group with subcommands for
listing available templates and initializing new configuration files from
templates.
"""

from pathlib import Path
from typing import Annotated

import typer

from cabinets.application.templates import TemplateManager, TemplateNotFoundError

# Create a Typer app for the templates subcommand group
templates_app = typer.Typer(
    name="templates",
    help="Manage cabinet configuration templates.",
)


@templates_app.command(name="list")
def list_templates() -> None:
    """List all available cabinet templates.

    Displays the name and description of each bundled template.

    Example:
        cabinets templates list
    """
    manager = TemplateManager()
    templates = manager.list_templates()

    typer.echo("Available templates:")
    typer.echo()

    # Calculate max name width for alignment
    max_name_width = max(len(name) for name, _ in templates) if templates else 0

    for name, description in templates:
        typer.echo(f"  {name:<{max_name_width}}  - {description}")

    typer.echo()
    typer.echo("Use 'cabinets templates init <name>' to create a configuration file from a template.")


@templates_app.command(name="init")
def init_template(
    name: Annotated[
        str,
        typer.Argument(help="Name of the template to initialize"),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path (default: <name>.json)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing file"),
    ] = False,
) -> None:
    """Initialize a new configuration file from a template.

    Creates a new JSON configuration file based on the specified template.
    By default, the file is created in the current directory with the
    template name (e.g., 'bookcase.json').

    Examples:
        cabinets templates init bookcase
        cabinets templates init simple-shelf --output my-shelf.json
        cabinets templates init bookcase --force
    """
    manager = TemplateManager()

    # Determine output path
    if output is None:
        output = Path(f"{name}.json")

    # Check if template exists
    if not manager.template_exists(name):
        available = ", ".join(n for n, _ in manager.list_templates())
        typer.echo(f"Error: Template not found: {name}", err=True)
        typer.echo(f"Available templates: {available}", err=True)
        raise typer.Exit(code=1)

    # Check if output file already exists
    if output.exists() and not force:
        typer.echo(f"Error: File already exists: {output}", err=True)
        typer.echo("Use --force to overwrite.", err=True)
        raise typer.Exit(code=1)

    # Initialize the template
    try:
        manager.init_template(name, output)
        typer.echo(f"Created: {output}")
    except TemplateNotFoundError:
        typer.echo(f"Error: Template not found: {name}", err=True)
        raise typer.Exit(code=1)
    except OSError as e:
        typer.echo(f"Error: Could not write file: {e}", err=True)
        raise typer.Exit(code=1)
