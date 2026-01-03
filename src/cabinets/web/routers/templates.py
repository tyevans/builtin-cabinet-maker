"""Template management endpoints."""

import json

from fastapi import APIRouter

from cabinets.application.templates.manager import TEMPLATE_METADATA
from cabinets.web.dependencies import TemplateManagerDep
from cabinets.web.schemas.responses import (
    TemplateContentSchema,
    TemplateListItemSchema,
    TemplateListSchema,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListSchema)
async def list_templates(
    manager: TemplateManagerDep,
) -> TemplateListSchema:
    """List all available templates.

    Args:
        manager: Injected TemplateManager.

    Returns:
        List of available templates with names and descriptions.
    """
    templates = [
        TemplateListItemSchema(name=name, description=desc)
        for name, desc in manager.list_templates()
    ]
    return TemplateListSchema(templates=templates)


@router.get("/{name}", response_model=TemplateContentSchema)
async def get_template(
    name: str,
    manager: TemplateManagerDep,
) -> TemplateContentSchema:
    """Get the content of a specific template.

    Args:
        name: Template name.
        manager: Injected TemplateManager.

    Returns:
        Template content with name, description, and configuration.

    Raises:
        TemplateNotFoundError: If template does not exist (handled by exception handler).
    """
    # Get template content (raises TemplateNotFoundError if not found)
    content_str = manager.get_template(name)
    content = json.loads(content_str)

    # Get description from metadata
    description = TEMPLATE_METADATA.get(name, "")

    return TemplateContentSchema(
        name=name,
        description=description,
        content=content,
    )
