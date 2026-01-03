"""Pydantic request schemas for the REST API."""

from typing import Any

from pydantic import BaseModel, Field

from cabinets.web.schemas.common import (
    DimensionsSchema,
    MaterialSchema,
    SectionSpecSchema,
)


class GenerateRequest(BaseModel):
    """Request for generating a cabinet layout."""

    dimensions: DimensionsSchema = Field(..., description="Cabinet dimensions")
    num_sections: int = Field(default=1, ge=1, le=10, description="Number of sections")
    shelves_per_section: int = Field(
        default=3, ge=0, le=20, description="Shelves per section"
    )
    material: MaterialSchema = Field(
        default_factory=MaterialSchema, description="Main panel material"
    )
    back_thickness: float = Field(
        default=0.25, ge=0.125, le=1.0, description="Back panel thickness in inches"
    )
    section_specs: list[SectionSpecSchema] | None = Field(
        default=None, description="Optional detailed section specifications"
    )


class GenerateFromConfigRequest(BaseModel):
    """Request for generating a cabinet from a full configuration."""

    config: dict[str, Any] = Field(..., description="Full cabinet configuration JSON")


class ConfigValidateRequest(BaseModel):
    """Request for validating a configuration."""

    config: dict[str, Any] = Field(..., description="Cabinet configuration JSON")


class ExportRequest(BaseModel):
    """Request for exporting layout to specific format."""

    dimensions: DimensionsSchema = Field(..., description="Cabinet dimensions")
    num_sections: int = Field(default=1, ge=1, le=10, description="Number of sections")
    shelves_per_section: int = Field(
        default=3, ge=0, le=20, description="Shelves per section"
    )
    material: MaterialSchema = Field(
        default_factory=MaterialSchema, description="Main panel material"
    )
    back_thickness: float = Field(
        default=0.25, ge=0.125, le=1.0, description="Back panel thickness in inches"
    )
