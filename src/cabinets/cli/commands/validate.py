"""Validate command for checking configuration files.

This module provides the `validate` command that checks a JSON configuration
file for errors and warnings, including woodworking advisories.
"""

from pathlib import Path
from typing import Annotated

import typer

from cabinets.application.config import (
    ConfigError,
    ValidationResult,
    load_config,
    validate_config,
)

# Create a sub-app for the validate command
# This will be added to the main app
validate_app = typer.Typer()


@validate_app.command(name="validate")
def validate(
    config_file: Annotated[
        Path,
        typer.Argument(help="Path to the JSON configuration file to validate"),
    ],
) -> None:
    """Validate a cabinet configuration file.

    Checks the configuration file for:
    - JSON syntax errors
    - Schema validation errors (missing required fields, invalid types, etc.)
    - Woodworking advisories (shelf span, material thickness, stability)

    Exit codes:
        0 - Configuration is valid with no warnings
        1 - Configuration has errors (cannot be used)
        2 - Configuration is valid but has warnings

    Example:
        cabinets validate my-cabinet.json
    """
    typer.echo(f"Validating {config_file}...")
    typer.echo()

    # Try to load and validate the configuration
    try:
        config = load_config(config_file)
    except ConfigError as e:
        # Display errors from loading phase
        _display_load_error(e)
        raise typer.Exit(code=1)

    # Run full validation including woodworking advisories
    result = validate_config(config)

    # Display results
    _display_validation_result(result)

    # Exit with appropriate code
    raise typer.Exit(code=result.exit_code)


def _display_load_error(error: ConfigError) -> None:
    """Display a configuration loading error.

    Args:
        error: The ConfigError to display
    """
    if error.error_type == "file_not_found":
        typer.echo("Errors:", err=True)
        typer.echo(f"  File not found: {error.path}", err=True)
    elif error.error_type == "json_parse":
        typer.echo("Errors:", err=True)
        typer.echo("  Invalid JSON syntax", err=True)
        for detail in error.details:
            line = detail.get("line", "?")
            column = detail.get("column", "?")
            message = detail.get("message", "Unknown error")
            typer.echo(f"    Line {line}, Column {column}: {message}", err=True)
    elif error.error_type == "validation":
        typer.echo("Errors:", err=True)
        for detail in error.details:
            path = detail.get("path", "unknown")
            message = detail.get("message", "Unknown error")
            value = detail.get("value")
            if value is not None:
                typer.echo(f"  {path}: {message}", err=True)
                typer.echo(f"    Value: {value!r}", err=True)
            else:
                typer.echo(f"  {path}: {message}", err=True)
    else:
        typer.echo("Errors:", err=True)
        typer.echo(f"  {error.message}", err=True)

    typer.echo()
    typer.echo("Validation failed.", err=True)


def _display_validation_result(result: ValidationResult) -> None:
    """Display validation results including errors and warnings.

    Args:
        result: The ValidationResult to display
    """
    # Display errors
    if result.errors:
        typer.echo("Errors:", err=True)
        for error in result.errors:
            typer.echo(f"  {error.path}: {error.message}", err=True)
            if error.value is not None:
                typer.echo(f"    Value: {error.value!r}", err=True)
        typer.echo()

    # Display warnings
    if result.warnings:
        typer.echo("Warnings:")
        for warning in result.warnings:
            typer.echo(f"  {warning.path}: {warning.message}")
            if warning.suggestion:
                typer.echo(f"    Suggestion: {warning.suggestion}")
        typer.echo()

    # Display summary
    if result.errors:
        error_count = len(result.errors)
        warning_count = len(result.warnings)
        typer.echo(
            f"Validation failed: {error_count} error(s), {warning_count} warning(s)",
            err=True,
        )
    elif result.warnings:
        warning_count = len(result.warnings)
        typer.echo(f"Validation passed with {warning_count} warning(s)")
    else:
        typer.echo("Validation passed. Configuration is valid.")


# Standalone command function for direct registration
def validate_command(
    config_file: Annotated[
        Path,
        typer.Argument(help="Path to the JSON configuration file to validate"),
    ],
) -> None:
    """Validate a cabinet configuration file.

    Checks the configuration file for:
    - JSON syntax errors
    - Schema validation errors (missing required fields, invalid types, etc.)
    - Woodworking advisories (shelf span, material thickness, stability)

    Exit codes:
        0 - Configuration is valid with no warnings
        1 - Configuration has errors (cannot be used)
        2 - Configuration is valid but has warnings

    Example:
        cabinets validate my-cabinet.json
    """
    validate(config_file)
