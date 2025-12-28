"""CLI command implementations for the cabinets application.

This package contains subcommands for the cabinets CLI, including:
- validate: Validate a configuration file
- templates: Manage cabinet configuration templates
"""

from cabinets.cli.commands.validate import validate_command
from cabinets.cli.commands.templates import templates_app

__all__ = ["validate_command", "templates_app"]
