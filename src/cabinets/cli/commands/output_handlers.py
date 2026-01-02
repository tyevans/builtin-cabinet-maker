"""Output format handling functions for cabinet CLI.

This module contains functions that handle exporting cabinet layouts
to various output formats including JSON, SVG, DXF, STL, BOM, and Assembly.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from cabinets.application.commands import LayoutOutput, RoomLayoutOutput

from cabinets.infrastructure.exporters import ExporterRegistry, ExportManager

__all__ = [
    "handle_multi_format_export",
]


def handle_multi_format_export(
    output_formats_str: str,
    output_dir: Path | None,
    project_name: str,
    result: "LayoutOutput | RoomLayoutOutput",
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

    # Check if safety-labels is requested but no safety assessment
    safety_assessment = getattr(result, "safety_assessment", None)
    if "safety-labels" in formats and safety_assessment is None:
        typer.echo(
            "Warning: Safety labels export requires safety checking enabled. "
            "Skipping safety-labels.",
            err=True,
        )
        formats = [f for f in formats if f != "safety-labels"]

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
