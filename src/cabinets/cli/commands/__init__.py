"""CLI command implementations for the cabinets application.

This package contains subcommands and helper modules for the cabinets CLI:

Subcommands:
- validate: Validate a configuration file
- templates: Manage cabinet configuration templates
- generate: Generate cabinet layouts (main command)

Helper Modules:
- output_handlers: Multi-format export handling
- zone_stack: Zone stack generation (kitchen, mudroom, etc.)
- safety: Safety configuration and output
"""

from cabinets.cli.commands.validate import validate_command
from cabinets.cli.commands.templates import templates_app
from cabinets.cli.commands.generate import generate
from cabinets.cli.commands.output_handlers import handle_multi_format_export
from cabinets.cli.commands.zone_stack import (
    generate_zone_stack,
    handle_zone_stack_multi_format_export,
    output_zone_stack_cutlist,
    output_zone_stack_materials,
    output_zone_stack_diagram,
    output_zone_stack_json,
    output_zone_stack_stl,
    output_zone_stack_all,
    build_zone_stack_json,
    export_cabinet_stl,
)
from cabinets.cli.commands.safety import (
    build_installation_config,
    build_installation_config_from_cli,
    build_safety_config,
    display_safety_summary,
    export_safety_labels,
)

__all__ = [
    # Subcommands
    "validate_command",
    "templates_app",
    "generate",
    # Output handlers
    "handle_multi_format_export",
    # Zone stack functions
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
    # Safety functions
    "build_installation_config",
    "build_installation_config_from_cli",
    "build_safety_config",
    "display_safety_summary",
    "export_safety_labels",
]
