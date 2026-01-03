"""Pydantic response schemas for the REST API."""

from typing import Any

from pydantic import BaseModel, Field


class CutPieceSchema(BaseModel):
    """Cut piece in the cut list."""

    label: str = Field(..., description="Piece label/name")
    width: float = Field(..., description="Width in inches")
    height: float = Field(..., description="Height in inches")
    thickness: float = Field(..., description="Thickness in inches")
    material_type: str = Field(..., description="Material type")
    quantity: int = Field(default=1, description="Number of pieces")
    notes: str | None = Field(default=None, description="Additional notes")


class MaterialEstimateSchema(BaseModel):
    """Material estimate for a material type."""

    sheet_count: float = Field(..., description="Estimated sheet count needed")
    total_area_sqft: float = Field(..., description="Total area in square feet")
    waste_percentage: float = Field(..., description="Waste percentage applied")


class CabinetSummarySchema(BaseModel):
    """Summary of generated cabinet."""

    width: float = Field(..., description="Cabinet width in inches")
    height: float = Field(..., description="Cabinet height in inches")
    depth: float = Field(..., description="Cabinet depth in inches")
    num_sections: int = Field(..., description="Number of sections")
    total_shelves: int = Field(..., description="Total number of shelves")


class LayoutOutputSchema(BaseModel):
    """Response for layout generation."""

    is_valid: bool = Field(..., description="Whether generation was successful")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    cabinet: CabinetSummarySchema | None = Field(
        default=None, description="Cabinet summary"
    )
    cut_list: list[CutPieceSchema] = Field(
        default_factory=list, description="List of cut pieces"
    )
    material_estimates: dict[str, MaterialEstimateSchema] = Field(
        default_factory=dict, description="Material estimates by material key"
    )
    total_estimate: MaterialEstimateSchema | None = Field(
        default=None, description="Total material estimate"
    )


class ValidationResultSchema(BaseModel):
    """Response for configuration validation."""

    is_valid: bool = Field(..., description="Whether configuration is valid")
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="Validation errors"
    )
    warnings: list[dict[str, Any]] = Field(
        default_factory=list, description="Validation warnings"
    )


class TemplateListItemSchema(BaseModel):
    """Single template in the list."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")


class TemplateListSchema(BaseModel):
    """Response for template listing."""

    templates: list[TemplateListItemSchema] = Field(
        ..., description="Available templates"
    )


class TemplateContentSchema(BaseModel):
    """Response for template content."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    content: dict[str, Any] = Field(..., description="Template configuration content")


class ExportFormatsSchema(BaseModel):
    """Response for available export formats."""

    formats: list[str] = Field(..., description="Available format names")


class WallSummarySchema(BaseModel):
    """Summary of a wall segment in a room layout."""

    name: str | None = Field(default=None, description="Wall name")
    length: float = Field(..., description="Wall length in inches")
    height: float = Field(..., description="Wall height in inches")
    depth: float = Field(..., description="Cabinet depth in inches")
    angle: float = Field(default=0.0, description="Wall angle in degrees")


class RoomLayoutOutputSchema(BaseModel):
    """Response for room layout generation."""

    is_valid: bool = Field(..., description="Whether generation was successful")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    room_name: str | None = Field(default=None, description="Room name")
    walls: list[WallSummarySchema] = Field(
        default_factory=list, description="Wall summaries"
    )
    cabinets: list[CabinetSummarySchema] = Field(
        default_factory=list, description="Cabinet summaries for each section"
    )
    cut_list: list[CutPieceSchema] = Field(
        default_factory=list, description="Combined cut list"
    )
    material_estimates: dict[str, MaterialEstimateSchema] = Field(
        default_factory=dict, description="Material estimates by material key"
    )
    total_estimate: MaterialEstimateSchema | None = Field(
        default=None, description="Total material estimate"
    )


class ErrorResponseSchema(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type identifier")
    details: list[dict[str, Any]] | dict[str, Any] | None = Field(
        default=None, description="Additional error details"
    )
