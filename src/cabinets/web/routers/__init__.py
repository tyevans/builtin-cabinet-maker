"""API routers for the REST API."""

from cabinets.web.routers.export import router as export_router
from cabinets.web.routers.generate import router as generate_router
from cabinets.web.routers.templates import router as templates_router
from cabinets.web.routers.validate import router as validate_router

__all__ = [
    "export_router",
    "generate_router",
    "templates_router",
    "validate_router",
]
