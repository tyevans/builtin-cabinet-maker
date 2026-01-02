"""Safety and compliance configuration schemas.

This module contains safety configuration models including SafetyConfigSchema
and AccessibilityConfigSchema for FRD-21.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AccessibilityConfigSchema(BaseModel):
    """ADA accessibility configuration.

    Enables ADA compliance checking for cabinet designs, validating
    reach ranges and accessible storage percentage requirements.

    Attributes:
        enabled: Enable ADA accessibility checking.
        standard: Which ADA standard to use for validation.
        min_accessible_percentage: Minimum percentage of accessible storage.

    Example:
        ```yaml
        safety:
          accessibility:
            enabled: true
            standard: ADA_2010
            min_accessible_percentage: 50.0
        ```
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    standard: Literal["ADA_2010", "ANSI_A117.1"] = "ADA_2010"
    min_accessible_percentage: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Minimum percentage of storage that must be accessible",
    )


class SafetyConfigSchema(BaseModel):
    """Safety and compliance configuration.

    Configures safety analysis features including structural safety,
    accessibility, child safety, seismic requirements, and building
    code clearance checking.

    Attributes:
        safety_factor: Safety factor for capacity calculations (2.0-6.0).
        deflection_limit: Maximum shelf deflection ratio (L/200, L/240, L/360).
        accessibility: ADA accessibility configuration.
        child_safe_mode: Enable child safety recommendations.
        seismic_zone: IBC seismic design category (A-F).
        check_clearances: Enable building code clearance checking.
        material_certification: Material formaldehyde certification level.
        finish_voc_category: Finish VOC content category.
        generate_labels: Generate safety label content.
        generate_safety_report: Generate detailed safety report.

    Example:
        ```yaml
        safety:
          safety_factor: 4.0
          deflection_limit: L/200
          accessibility:
            enabled: true
          child_safe_mode: true
          seismic_zone: D
          check_clearances: true
          material_certification: carb_phase2
          generate_labels: true
        ```
    """

    model_config = ConfigDict(extra="forbid")

    # Structural safety
    safety_factor: float = Field(
        default=4.0,
        ge=2.0,
        le=6.0,
        description="Safety factor for capacity calculations (2.0-6.0)",
    )
    deflection_limit: Literal["L/200", "L/240", "L/360"] = Field(
        default="L/200",
        description="Maximum allowable shelf deflection ratio",
    )

    # Accessibility
    accessibility: AccessibilityConfigSchema | None = None

    # Child safety
    child_safe_mode: bool = Field(
        default=False,
        description="Enable child safety recommendations (soft-close, locks)",
    )

    # Seismic
    seismic_zone: Literal["A", "B", "C", "D", "E", "F"] | None = Field(
        default=None,
        description="IBC seismic design category (zones D/E/F require enhanced anchoring)",
    )

    # Building code clearances
    check_clearances: bool = Field(
        default=True,
        description="Enable building code clearance checking",
    )

    # Material safety
    material_certification: Literal["carb_phase2", "naf", "ulef", "none", "unknown"] = (
        Field(
            default="unknown",
            description="Material formaldehyde certification level",
        )
    )
    finish_voc_category: Literal[
        "super_compliant", "compliant", "standard", "unknown"
    ] = Field(
        default="unknown",
        description="Finish VOC content category",
    )

    # Output
    generate_labels: bool = Field(
        default=True,
        description="Generate safety label content",
    )
    generate_safety_report: bool = Field(
        default=True,
        description="Generate detailed safety report",
    )
