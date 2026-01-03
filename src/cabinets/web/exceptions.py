"""Custom exceptions and error handlers for the REST API."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cabinets.application.templates.manager import TemplateNotFoundError
from cabinets.domain.section_resolver import SectionWidthError


class CabinetGenerationError(Exception):
    """Raised when cabinet generation fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Generation failed: {errors}")


class ExportError(Exception):
    """Raised when export operation fails."""

    def __init__(self, message: str, format_name: str) -> None:
        self.message = message
        self.format_name = format_name
        super().__init__(message)


class UnsupportedFormatError(Exception):
    """Raised when requested export format is not supported."""

    def __init__(self, format_name: str, available: list[str]) -> None:
        self.format_name = format_name
        self.available = available
        super().__init__(
            f"Unsupported format: {format_name}. Available: {', '.join(available)}"
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with the FastAPI app."""

    @app.exception_handler(SectionWidthError)
    async def section_width_error_handler(
        request: Request, exc: SectionWidthError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": str(exc),
                "error_type": "section_width",
                "details": None,
            },
        )

    @app.exception_handler(CabinetGenerationError)
    async def generation_error_handler(
        request: Request, exc: CabinetGenerationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Cabinet generation failed",
                "error_type": "generation",
                "details": [{"message": e} for e in exc.errors],
            },
        )

    @app.exception_handler(ExportError)
    async def export_error_handler(request: Request, exc: ExportError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.message,
                "error_type": "export",
                "details": [{"format": exc.format_name}],
            },
        )

    @app.exception_handler(TemplateNotFoundError)
    async def template_not_found_handler(
        request: Request, exc: TemplateNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"Template not found: {exc.name}",
                "error_type": "not_found",
                "details": None,
            },
        )

    @app.exception_handler(UnsupportedFormatError)
    async def unsupported_format_handler(
        request: Request, exc: UnsupportedFormatError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": str(exc),
                "error_type": "unsupported_format",
                "details": {"format": exc.format_name, "available": exc.available},
            },
        )
