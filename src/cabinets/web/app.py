"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cabinets.web.exceptions import register_exception_handlers
from cabinets.web.routers import (
    export_router,
    generate_router,
    templates_router,
    validate_router,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Cabinet Generator API",
        description="REST API for generating built-in cabinet and shelf layouts",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware for browser access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(generate_router, prefix="/api/v1")
    app.include_router(validate_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


# Application instance for ASGI servers (uvicorn)
app = create_app()
