"""Zone stack generation functions for cabinet CLI.

This module contains functions for generating and outputting
zone stack configurations (kitchen, mudroom, vanity, hutch).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from cabinets.application.config.schemas import CabinetConfiguration
    from cabinets.domain import Cabinet
    from cabinets.domain.services.zone_layout import ZoneStackLayoutResult

from cabinets.application.config import config_to_zone_layout
from cabinets.application.factory import get_factory
from cabinets.domain.value_objects import MaterialSpec

__all__ = [
    "generate_zone_stack",
    "handle_zone_stack_multi_format_export",
    "output_zone_stack_cutlist",
    "output_zone_stack_materials",
    "output_zone_stack_diagram",
    "output_zone_stack_json",
    "output_zone_stack_stl",
    "output_zone_stack_all",
    "build_zone_stack_json",
    "export_cabinet_stl",
]


def generate_zone_stack(
    config: "CabinetConfiguration",
    output_format: str,
    output_file: Path | None,
    output_dir: Path | None,
    output_formats: str | None,
    project_name: str,
) -> None:
    """Generate layout for a zone stack configuration.

    Args:
        config: Full configuration schema with zone_stack.
        output_format: Single output format (cutlist, materials, diagram, etc.).
        output_file: Optional output file path (for STL).
        output_dir: Optional output directory (for multi-format).
        output_formats: Comma-separated list of formats or "all".
        project_name: Project name for file naming.
    """
    # Convert config to zone layout config
    zone_stack_schema = config.cabinet.zone_stack
    if zone_stack_schema is None:
        typer.echo("Error: No zone_stack configuration found", err=True)
        raise typer.Exit(code=1)

    # Get material from cabinet config
    material = None
    if config.cabinet.material:
        material = MaterialSpec(
            thickness=config.cabinet.material.thickness,
            material_type=config.cabinet.material.type,
        )

    zone_layout_config = config_to_zone_layout(
        zone_stack_schema=zone_stack_schema,
        cabinet_width=config.cabinet.width,
        material=material,
    )

    # Generate zone stack
    factory = get_factory()
    service = factory.get_zone_layout_service()
    result = service.generate(zone_layout_config)

    # Handle errors
    if result.has_errors:
        typer.echo("Zone stack generation errors:", err=True)
        for error in result.errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(code=1)

    # Show warnings
    if result.warnings:
        typer.echo("Zone stack warnings:")
        for warning in result.warnings:
            typer.echo(f"  - {warning}")
        typer.echo()

    # Collect cabinets for processing
    cabinets: list[tuple[str, "Cabinet"]] = []
    if result.base_cabinet:
        cabinets.append(("BASE ZONE", result.base_cabinet))
    if result.upper_cabinet:
        cabinets.append(("UPPER ZONE", result.upper_cabinet))

    # Handle multi-format export if --output-formats is specified
    if output_formats is not None:
        handle_zone_stack_multi_format_export(
            result,
            cabinets,
            config,
            output_formats,
            output_dir,
            project_name,
        )
        return

    # Handle single format output
    if output_format == "cutlist":
        output_zone_stack_cutlist(result, cabinets)
    elif output_format == "materials":
        output_zone_stack_materials(result, cabinets)
    elif output_format == "diagram":
        output_zone_stack_diagram(result)
    elif output_format == "json":
        output_zone_stack_json(result, config)
    elif output_format == "stl":
        output_zone_stack_stl(result, config, output_file)
    else:  # "all" or default
        output_zone_stack_all(result, cabinets, config)


def handle_zone_stack_multi_format_export(
    result: "ZoneStackLayoutResult",
    cabinets: list[tuple[str, "Cabinet"]],
    config: "CabinetConfiguration",
    output_formats_str: str,
    output_dir: Path | None,
    project_name: str,
) -> None:
    """Handle multi-format export for zone stacks.

    Args:
        result: Zone stack layout result.
        cabinets: List of (zone_name, cabinet) tuples.
        config: Original configuration.
        output_formats_str: Comma-separated format list or "all".
        output_dir: Output directory for exported files.
        project_name: Project name for file naming.
    """
    # Parse formats
    if output_formats_str.lower() == "all":
        formats = ["json", "stl"]  # Available formats for zone stacks
    else:
        formats = [f.strip().lower() for f in output_formats_str.split(",")]

    # Validate formats - zone stacks support a subset of formats
    supported_formats = {"json", "stl"}
    invalid = [f for f in formats if f not in supported_formats]
    if invalid:
        typer.echo(
            f"Warning: Zone stacks don't support formats: {', '.join(invalid)}",
            err=True,
        )
        typer.echo(
            f"Supported zone stack formats: {', '.join(sorted(supported_formats))}",
            err=True,
        )
        formats = [f for f in formats if f in supported_formats]

    if not formats:
        typer.echo("No valid formats to export for zone stack.", err=True)
        raise typer.Exit(code=1)

    # Set up output directory
    out_dir = output_dir or Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    exported_files: dict[str, Path] = {}

    for fmt in formats:
        if fmt == "json":
            # Export zone stack JSON
            output = build_zone_stack_json(result, config)
            json_path = out_dir / f"{project_name}_zone_stack.json"
            json_path.write_text(json.dumps(output, indent=2))
            exported_files["JSON"] = json_path

        elif fmt == "stl":
            # Export STL files for each cabinet
            if result.base_cabinet:
                base_path = out_dir / f"{project_name}_base.stl"
                export_cabinet_stl(result.base_cabinet, base_path)
                exported_files["STL (base)"] = base_path

            if result.upper_cabinet:
                upper_path = out_dir / f"{project_name}_upper.stl"
                export_cabinet_stl(result.upper_cabinet, upper_path)
                exported_files["STL (upper)"] = upper_path

    typer.echo("\nExported files:")
    for fmt_name, path in exported_files.items():
        typer.echo(f"  {fmt_name}: {path}")


def export_cabinet_stl(cabinet: "Cabinet", output_path: Path) -> None:
    """Export a single cabinet to STL.

    Args:
        cabinet: Cabinet to export.
        output_path: Path for STL file.
    """
    factory = get_factory()
    exporter = factory.get_stl_exporter()
    exporter.export_to_file(cabinet, output_path)


def output_zone_stack_cutlist(
    result: "ZoneStackLayoutResult",
    cabinets: list[tuple[str, "Cabinet"]],
) -> None:
    """Output zone-aware cut list.

    Args:
        result: Zone stack layout result.
        cabinets: List of (zone_name, cabinet) tuples.
    """
    typer.echo()
    typer.echo("=" * 60)
    typer.echo("ZONE STACK CUT LIST")
    typer.echo("=" * 60)

    factory = get_factory()

    # Output each cabinet zone
    for zone_name, cabinet in cabinets:
        typer.echo()
        typer.echo(f'{zone_name} ({cabinet.height}" height, {cabinet.depth}" depth)')
        typer.echo("-" * 40)

        # Generate cut list directly from cabinet
        cut_generator = factory.get_cut_list_generator()
        cut_list = cut_generator.generate(cabinet)

        # Format output
        formatter = factory.get_cut_list_formatter()
        output = formatter.format(cut_list)
        typer.echo(output)

    # Output countertop if present
    if result.countertop_panels:
        typer.echo()
        typer.echo("COUNTERTOP")
        typer.echo("-" * 40)
        for panel in result.countertop_panels:
            metadata = panel.metadata or {}
            edge = metadata.get("edge_treatment", "square")
            label = metadata.get("label", panel.panel_type.value)
            typer.echo(
                f"  {label}: "
                f'{panel.width:.2f}" x {panel.height:.2f}" x {panel.material.thickness:.2f}"  '
                f"Edge: {edge}"
            )
            overhangs = []
            for key in ["front_overhang", "left_overhang", "right_overhang"]:
                val = metadata.get(key, 0)
                if val and val > 0:
                    overhangs.append(f'{key.replace("_overhang", "")}: {val}"')
            if overhangs:
                typer.echo(f"      Overhang: {', '.join(overhangs)}")

    # Output gap zones
    if result.gap_zones:
        typer.echo()
        typer.echo("GAP ZONES (no cabinet panels)")
        typer.echo("-" * 40)
        for gap in result.gap_zones:
            typer.echo(
                f'  {gap.purpose.value.upper()}: {gap.width:.1f}" x {gap.height:.1f}" '
                f'(at {gap.bottom_height:.1f}" from floor)'
            )

    # Output hardware
    if result.hardware:
        typer.echo()
        typer.echo("HARDWARE")
        typer.echo("-" * 40)
        for item in result.hardware:
            typer.echo(f"  {item.name}: {item.quantity} qty")
            if item.notes:
                typer.echo(f"      {item.notes}")


def output_zone_stack_materials(
    result: "ZoneStackLayoutResult",
    cabinets: list[tuple[str, "Cabinet"]],
) -> None:
    """Output zone-aware material report.

    Args:
        result: Zone stack layout result.
        cabinets: List of (zone_name, cabinet) tuples.
    """
    factory = get_factory()

    typer.echo()
    typer.echo("=" * 60)
    typer.echo("ZONE STACK MATERIAL ESTIMATE")
    typer.echo("=" * 60)

    total_sqft = 0.0

    for zone_name, cabinet in cabinets:
        # Generate cut list from cabinet
        cut_generator = factory.get_cut_list_generator()
        cut_list = cut_generator.generate(cabinet)

        estimator = factory.get_material_estimator()
        estimate = estimator.estimate_total(cut_list)

        typer.echo()
        typer.echo(f"{zone_name}")
        typer.echo("-" * 40)
        # Format estimate directly
        typer.echo(f"  Area needed: {estimate.total_area_sqft:.2f} sq ft")
        typer.echo(
            f"  4x8 sheets:  {estimate.sheet_count_4x8} (with {estimate.waste_percentage:.0%} waste)"
        )

        total_sqft += estimate.total_area_sqft

    # Add countertop material
    if result.countertop_panels:
        typer.echo()
        typer.echo("COUNTERTOP")
        typer.echo("-" * 40)
        for panel in result.countertop_panels:
            sqft = (panel.width * panel.height) / 144
            label = (
                panel.metadata.get("label", "Countertop")
                if panel.metadata
                else "Countertop"
            )
            typer.echo(f"  {label}: {sqft:.2f} sq ft")
            total_sqft += sqft

    typer.echo()
    typer.echo(f"TOTAL MATERIAL: {total_sqft:.2f} sq ft")


def output_zone_stack_diagram(result: "ZoneStackLayoutResult") -> None:
    """Output zone-aware ASCII diagram.

    Args:
        result: Zone stack layout result.
    """
    typer.echo()
    typer.echo("=" * 60)
    typer.echo("ZONE STACK DIAGRAM")
    typer.echo("=" * 60)

    # Simple ASCII representation
    max_width = 60

    # Draw from top to bottom
    typer.echo("+" + "-" * (max_width - 2) + "+")

    if result.upper_cabinet:
        height_lines = max(3, int(result.upper_cabinet.height / 10))
        for i in range(height_lines):
            if i == height_lines // 2:
                label = f'UPPER ZONE ({result.upper_cabinet.height}")'
                padding = (max_width - 4 - len(label)) // 2
                typer.echo(
                    f"| {' ' * padding}{label}{' ' * (max_width - 4 - padding - len(label))} |"
                )
            else:
                typer.echo("|" + " " * (max_width - 2) + "|")
        typer.echo("+" + "-" * (max_width - 2) + "+")

    for gap in reversed(list(result.gap_zones)):
        label = f'{gap.purpose.value.upper()} ZONE ({gap.height}")'
        padding = (max_width - 4 - len(label)) // 2
        typer.echo(
            f"| {' ' * padding}{label}{' ' * (max_width - 4 - padding - len(label))} |"
        )
        typer.echo("+" + "-" * (max_width - 2) + "+")

    if result.countertop_panels:
        typer.echo("|" + "=" * (max_width - 2) + "|  <- COUNTERTOP")
        typer.echo("+" + "-" * (max_width - 2) + "+")

    if result.base_cabinet:
        height_lines = max(4, int(result.base_cabinet.height / 10))
        for i in range(height_lines):
            if i == height_lines // 2:
                label = f'BASE ZONE ({result.base_cabinet.height}")'
                padding = (max_width - 4 - len(label)) // 2
                typer.echo(
                    f"| {' ' * padding}{label}{' ' * (max_width - 4 - padding - len(label))} |"
                )
            else:
                typer.echo("|" + " " * (max_width - 2) + "|")
        typer.echo("+" + "-" * (max_width - 2) + "+")

    typer.echo("     FLOOR")


def build_zone_stack_json(
    result: "ZoneStackLayoutResult",
    config: "CabinetConfiguration",
) -> dict:
    """Build JSON output dict for zone stack.

    Args:
        result: Zone stack layout result.
        config: Original configuration.

    Returns:
        Dictionary ready for JSON serialization.
    """
    output: dict = {
        "zone_stack": {
            "preset": config.cabinet.zone_stack.preset.value
            if config.cabinet.zone_stack
            else "custom",
            "base_cabinet": None,
            "upper_cabinet": None,
            "countertop": None,
            "gap_zones": [],
            "hardware": [],
        }
    }

    if result.base_cabinet:
        output["zone_stack"]["base_cabinet"] = {
            "width": result.base_cabinet.width,
            "height": result.base_cabinet.height,
            "depth": result.base_cabinet.depth,
        }

    if result.upper_cabinet:
        output["zone_stack"]["upper_cabinet"] = {
            "width": result.upper_cabinet.width,
            "height": result.upper_cabinet.height,
            "depth": result.upper_cabinet.depth,
        }

    if result.countertop_panels:
        panel = result.countertop_panels[0]
        metadata = panel.metadata or {}
        output["zone_stack"]["countertop"] = {
            "width": panel.width,
            "depth": panel.height,
            "thickness": panel.material.thickness,
            "edge_treatment": metadata.get("edge_treatment", "square"),
        }

    for gap in result.gap_zones:
        output["zone_stack"]["gap_zones"].append(
            {
                "purpose": gap.purpose.value,
                "width": gap.width,
                "height": gap.height,
                "bottom_height": gap.bottom_height,
            }
        )

    for item in result.hardware:
        output["zone_stack"]["hardware"].append(
            {
                "name": item.name,
                "quantity": item.quantity,
                "notes": item.notes,
            }
        )

    return output


def output_zone_stack_json(
    result: "ZoneStackLayoutResult",
    config: "CabinetConfiguration",
) -> None:
    """Output zone stack as JSON.

    Args:
        result: Zone stack layout result.
        config: Original configuration.
    """
    output = build_zone_stack_json(result, config)

    typer.echo()
    typer.echo("ZONE STACK JSON")
    typer.echo("=" * 60)
    typer.echo(json.dumps(output, indent=2))


def output_zone_stack_stl(
    result: "ZoneStackLayoutResult",
    config: "CabinetConfiguration",
    output_path: Path | None = None,
) -> None:
    """Output zone stack as STL file(s).

    For zone stacks, we generate separate STL files for base and upper cabinets.

    Args:
        result: Zone stack layout result.
        config: Original configuration.
        output_path: Optional output path for STL file.
    """
    if output_path:
        base_path = str(output_path).rsplit(".", 1)[0]
    else:
        base_path = "zone_stack"

    factory = get_factory()
    exporter = factory.get_stl_exporter()

    if result.base_cabinet:
        base_stl_path = Path(f"{base_path}_base.stl")
        exporter.export_to_file(result.base_cabinet, base_stl_path)
        typer.echo(f"Base zone STL saved to: {base_stl_path}")

    if result.upper_cabinet:
        upper_stl_path = Path(f"{base_path}_upper.stl")
        exporter.export_to_file(result.upper_cabinet, upper_stl_path)
        typer.echo(f"Upper zone STL saved to: {upper_stl_path}")

    if not result.base_cabinet and not result.upper_cabinet:
        typer.echo("No cabinets to export to STL", err=True)
        raise typer.Exit(code=1)


def output_zone_stack_all(
    result: "ZoneStackLayoutResult",
    cabinets: list[tuple[str, "Cabinet"]],
    config: "CabinetConfiguration",
) -> None:
    """Output all zone stack information.

    Args:
        result: Zone stack layout result.
        cabinets: List of (zone_name, cabinet) tuples.
        config: Original configuration.
    """
    typer.echo()
    typer.echo("=" * 60)
    typer.echo("ZONE STACK LAYOUT")
    typer.echo("=" * 60)

    # Summary
    preset_name = (
        config.cabinet.zone_stack.preset.value
        if config.cabinet.zone_stack
        else "custom"
    )
    typer.echo(f"Preset: {preset_name}")
    if result.base_cabinet:
        typer.echo(
            f'Base zone: {result.base_cabinet.width}"W x {result.base_cabinet.height}"H x {result.base_cabinet.depth}"D'
        )
    if result.upper_cabinet:
        typer.echo(
            f'Upper zone: {result.upper_cabinet.width}"W x {result.upper_cabinet.height}"H x {result.upper_cabinet.depth}"D'
        )
    if result.countertop_panels:
        typer.echo(
            f'Countertop: {result.countertop_panels[0].width}"W x {result.countertop_panels[0].height}"D'
        )
    if result.gap_zones:
        for gap in result.gap_zones:
            typer.echo(f'Gap zone ({gap.purpose.value}): {gap.height}"H')

    # Diagram
    output_zone_stack_diagram(result)

    # Cut list
    output_zone_stack_cutlist(result, cabinets)

    # Materials
    output_zone_stack_materials(result, cabinets)
