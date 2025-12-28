"""Cabinet templates and preset configurations.

This package provides bundled template configurations for common cabinet types
and a TemplateManager class for accessing them.
"""

from cabinets.application.templates.manager import (
    TemplateManager,
    TemplateNotFoundError,
    TEMPLATE_METADATA,
)

__all__ = [
    "TemplateManager",
    "TemplateNotFoundError",
    "TEMPLATE_METADATA",
]
