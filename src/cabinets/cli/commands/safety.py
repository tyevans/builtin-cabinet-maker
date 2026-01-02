"""Safety-related functions for cabinet CLI.

This module contains functions for building safety configurations
and displaying/exporting safety assessment results.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from cabinets.domain.services.installation import InstallationConfig
    from cabinets.domain.services.safety import SafetyAssessment, SafetyConfig

__all__ = [
    "build_installation_config",
    "build_installation_config_from_cli",
    "build_safety_config",
    "display_safety_summary",
    "export_safety_labels",
]


def build_installation_config(config_dict: dict) -> "InstallationConfig":
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


def build_installation_config_from_cli(
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
        kwargs["expected_load"] = load_map.get(
            expected_load.lower(), LoadCategory.MEDIUM
        )

    return InstallationConfig(**kwargs)  # type: ignore[arg-type]


def build_safety_config(
    safety_factor: float,
    accessibility: bool,
    child_safe: bool,
    seismic_zone: str | None,
    material_cert: str,
    no_clearance_check: bool,
) -> "SafetyConfig":
    """Build SafetyConfig from CLI options.

    Args:
        safety_factor: Safety factor for calculations (2.0-6.0).
        accessibility: Enable ADA checking.
        child_safe: Enable child safety mode.
        seismic_zone: IBC seismic zone letter (A-F).
        material_cert: Material certification string.
        no_clearance_check: Disable clearance checking.

    Returns:
        SafetyConfig domain object.
    """
    from cabinets.domain.services.safety import SafetyConfig
    from cabinets.domain.value_objects import (
        ADAStandard,
        MaterialCertification,
        SeismicZone,
        VOCCategory,
    )

    # Parse seismic zone
    seismic = None
    if seismic_zone:
        seismic_zone_upper = seismic_zone.upper()
        if seismic_zone_upper in ("A", "B", "C", "D", "E", "F"):
            seismic = SeismicZone(seismic_zone_upper)
        else:
            typer.echo(
                f"Warning: Invalid seismic zone '{seismic_zone}'. "
                f"Valid values: A, B, C, D, E, F",
                err=True,
            )

    # Parse material certification
    cert_map = {
        "carb_phase2": MaterialCertification.CARB_PHASE2,
        "naf": MaterialCertification.NAF,
        "ulef": MaterialCertification.ULEF,
        "none": MaterialCertification.NONE,
        "unknown": MaterialCertification.UNKNOWN,
    }
    cert = cert_map.get(material_cert.lower(), MaterialCertification.UNKNOWN)

    return SafetyConfig(
        accessibility_enabled=accessibility,
        accessibility_standard=ADAStandard.ADA_2010,
        child_safe_mode=child_safe,
        seismic_zone=seismic,
        safety_factor=safety_factor,
        deflection_limit_ratio=200,  # L/200 default
        check_clearances=not no_clearance_check,
        generate_labels=True,
        material_certification=cert,
        finish_voc_category=VOCCategory.UNKNOWN,
    )


def display_safety_summary(assessment: "SafetyAssessment") -> None:
    """Display safety assessment summary to console.

    Args:
        assessment: Completed safety assessment.
    """
    from cabinets.domain.value_objects import SafetyCategory

    typer.echo()
    typer.echo("=" * 60)
    typer.echo("SAFETY ASSESSMENT")
    typer.echo("=" * 60)
    typer.echo()

    # Summary
    if assessment.has_errors:
        summary_prefix = "[FAIL]"
    elif assessment.has_warnings:
        summary_prefix = "[WARN]"
    else:
        summary_prefix = "[PASS]"

    typer.echo(f"{summary_prefix} {assessment.summary}")
    typer.echo()

    # Results by category
    categories = [
        (SafetyCategory.STRUCTURAL, "Structural Safety"),
        (SafetyCategory.STABILITY, "Stability"),
        (SafetyCategory.ACCESSIBILITY, "Accessibility"),
        (SafetyCategory.CLEARANCE, "Clearances"),
        (SafetyCategory.MATERIAL, "Material Safety"),
        (SafetyCategory.SEISMIC, "Seismic"),
        (SafetyCategory.CHILD_SAFETY, "Child Safety"),
    ]

    for category, title in categories:
        results = assessment.get_results_by_category(category)
        if results:
            typer.echo(f"{title}:")
            for result in results:
                typer.echo(f"  {result.formatted_message}")
                if result.remediation:
                    typer.echo(f"    Suggestion: {result.remediation}")
            typer.echo()

    # Weight capacities
    if assessment.weight_capacities:
        typer.echo("Weight Capacities:")
        for capacity in assessment.weight_capacities:
            typer.echo(f"  {capacity.formatted_message}")
        typer.echo()

    # Anti-tip warning
    if assessment.anti_tip_required:
        typer.echo("Anti-Tip Required: Install anti-tip restraint hardware")
        typer.echo()

    # Seismic hardware
    if assessment.seismic_hardware:
        typer.echo("Seismic Hardware Required:")
        for hw in assessment.seismic_hardware:
            typer.echo(f"  - {hw}")
        typer.echo()

    # Disclaimer
    typer.echo(
        "Note: Safety estimates are advisory only. "
        "Consult professionals for critical installations."
    )


def export_safety_labels(
    assessment: "SafetyAssessment",
    output_dir: Path | None,
) -> None:
    """Export safety labels to SVG files.

    Args:
        assessment: Completed safety assessment.
        output_dir: Output directory for label files.
    """
    if not assessment.safety_labels:
        typer.echo("No safety labels to export")
        return

    # Note: SafetyLabelExporter will be implemented in Task 10
    # For now, export basic text files with label content
    output_path = output_dir or Path(".")
    output_path.mkdir(parents=True, exist_ok=True)

    for label in assessment.safety_labels:
        filename = f"safety_label_{label.label_type}.txt"
        filepath = output_path / filename
        content = f"{label.title}\n{'=' * len(label.title)}\n\n{label.body_text}"
        filepath.write_text(content)
        typer.echo(f"Exported: {filepath}")
