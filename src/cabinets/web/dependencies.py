"""FastAPI dependency injection for cabinet services."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.factory import ServiceFactory, get_factory
from cabinets.application.templates.manager import TemplateManager


@lru_cache(maxsize=1)
def get_service_factory() -> ServiceFactory:
    """Get cached ServiceFactory instance."""
    return get_factory()


def get_generate_command(
    factory: Annotated[ServiceFactory, Depends(get_service_factory)],
) -> GenerateLayoutCommand:
    """Dependency for GenerateLayoutCommand."""
    return factory.create_generate_command()


def get_template_manager() -> TemplateManager:
    """Dependency for TemplateManager."""
    return TemplateManager()


# Type aliases for cleaner endpoint signatures
ServiceFactoryDep = Annotated[ServiceFactory, Depends(get_service_factory)]
GenerateCommandDep = Annotated[GenerateLayoutCommand, Depends(get_generate_command)]
TemplateManagerDep = Annotated[TemplateManager, Depends(get_template_manager)]
