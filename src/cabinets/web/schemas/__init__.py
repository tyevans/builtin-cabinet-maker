"""Pydantic schemas for the REST API."""

from cabinets.web.schemas.common import (
    DimensionsSchema,
    MaterialSchema,
    MaterialTypeEnum,
    SectionSpecSchema,
    SectionTypeEnum,
)
from cabinets.web.schemas.requests import (
    ConfigValidateRequest,
    ExportRequest,
    GenerateFromConfigRequest,
    GenerateRequest,
)
from cabinets.web.schemas.responses import (
    CabinetSummarySchema,
    CutPieceSchema,
    ErrorResponseSchema,
    ExportFormatsSchema,
    LayoutOutputSchema,
    MaterialEstimateSchema,
    TemplateContentSchema,
    TemplateListSchema,
    ValidationResultSchema,
)

__all__ = [
    # Common
    "DimensionsSchema",
    "MaterialSchema",
    "MaterialTypeEnum",
    "SectionSpecSchema",
    "SectionTypeEnum",
    # Requests
    "ConfigValidateRequest",
    "ExportRequest",
    "GenerateFromConfigRequest",
    "GenerateRequest",
    # Responses
    "CabinetSummarySchema",
    "CutPieceSchema",
    "ErrorResponseSchema",
    "ExportFormatsSchema",
    "LayoutOutputSchema",
    "MaterialEstimateSchema",
    "TemplateContentSchema",
    "TemplateListSchema",
    "ValidationResultSchema",
]
