"""Common Pydantic schemas shared across requests and responses."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class MaterialTypeEnum(str, Enum):
    """Material type options."""

    PLYWOOD = "plywood"
    MDF = "mdf"
    PARTICLE_BOARD = "particle_board"
    SOLID_WOOD = "solid_wood"


class SectionTypeEnum(str, Enum):
    """Section type options."""

    OPEN = "open"
    DOORED = "doored"
    DRAWERS = "drawers"
    CUBBY = "cubby"


class DimensionsSchema(BaseModel):
    """Wall/cabinet dimensions in inches."""

    width: float = Field(..., gt=0, le=240, description="Width in inches")
    height: float = Field(..., gt=0, le=120, description="Height in inches")
    depth: float = Field(..., gt=0, le=36, description="Depth in inches")


class MaterialSchema(BaseModel):
    """Material specification."""

    type: MaterialTypeEnum = Field(
        default=MaterialTypeEnum.PLYWOOD, description="Material type"
    )
    thickness: float = Field(
        default=0.75, ge=0.25, le=2.0, description="Thickness in inches"
    )


class SectionSpecSchema(BaseModel):
    """Section specification - mirrors domain SectionSpec."""

    width: float | Literal["fill"] = Field(
        default="fill", description="Width in inches or 'fill' to auto-calculate"
    )
    shelves: int = Field(default=0, ge=0, le=20, description="Number of shelves")
    section_type: SectionTypeEnum = Field(
        default=SectionTypeEnum.OPEN, description="Section type"
    )
    min_width: float = Field(default=6.0, gt=0, description="Minimum width in inches")
    max_width: float | None = Field(
        default=None, gt=0, description="Maximum width in inches"
    )
    component_config: dict[str, Any] = Field(
        default_factory=dict, description="Additional component configuration"
    )
