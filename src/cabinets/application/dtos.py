"""Data Transfer Objects for the application layer.

This module provides DTOs for the application layer, including input DTOs
for validation and output DTOs for layout results.

Note: LayoutOutput, RoomLayoutOutput, and related output DTOs are now
defined in cabinets.contracts.dtos and re-exported here for backward
compatibility. New code should import from cabinets.contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cabinets.domain import (
    MaterialSpec,
    MaterialType,
)

# Re-export output DTOs from contracts for backward compatibility
from cabinets.contracts.dtos import (
    CoreLayoutOutput,
    InstallationOutput,
    LayoutOutput,
    PackingOutput,
    RoomLayoutOutput,
    WoodworkingOutput,
)

if TYPE_CHECKING:
    pass


@dataclass
class WallInput:
    """Input DTO for wall dimensions."""

    width: float
    height: float
    depth: float

    def validate(self) -> list[str]:
        """Validate input and return list of error messages."""
        errors: list[str] = []
        if self.width <= 0:
            errors.append("Width must be positive")
        if self.height <= 0:
            errors.append("Height must be positive")
        if self.depth <= 0:
            errors.append("Depth must be positive")
        if self.width > 240:  # 20 feet
            errors.append("Width exceeds maximum (240 inches)")
        if self.height > 120:  # 10 feet
            errors.append("Height exceeds maximum (120 inches)")
        if self.depth > 36:  # 3 feet
            errors.append("Depth exceeds maximum (36 inches)")
        return errors


@dataclass
class LayoutParametersInput:
    """Input DTO for layout parameters."""

    num_sections: int = 1
    shelves_per_section: int = 3
    material_thickness: float = 0.75
    material_type: str = "plywood"
    back_thickness: float = 0.25

    def validate(self) -> list[str]:
        """Validate input and return list of error messages."""
        errors: list[str] = []
        if self.num_sections < 1:
            errors.append("Must have at least 1 section")
        if self.num_sections > 10:
            errors.append("Maximum 10 sections supported")
        if self.shelves_per_section < 0:
            errors.append("Shelves per section cannot be negative")
        if self.shelves_per_section > 20:
            errors.append("Maximum 20 shelves per section")
        if self.material_thickness <= 0:
            errors.append("Material thickness must be positive")
        if self.back_thickness <= 0:
            errors.append("Back thickness must be positive")
        valid_materials = [m.value for m in MaterialType]
        if self.material_type not in valid_materials:
            errors.append(f"Material type must be one of: {', '.join(valid_materials)}")
        return errors

    def to_material_spec(self) -> MaterialSpec:
        """Convert to MaterialSpec value object."""
        return MaterialSpec(
            thickness=self.material_thickness,
            material_type=MaterialType(self.material_type),
        )

    def to_back_material_spec(self) -> MaterialSpec:
        """Convert back material to MaterialSpec value object."""
        return MaterialSpec(
            thickness=self.back_thickness,
            material_type=MaterialType(self.material_type),
        )


@dataclass
class SafetyOutput:
    """Safety analysis output data.

    Data transfer object for safety assessment results, suitable
    for serialization and CLI output.

    Attributes:
        weight_capacities: List of weight capacity dictionaries.
        anti_tip_required: Whether anti-tip restraint is required.
        anti_tip_hardware: Recommended anti-tip hardware (if required).
        accessibility_report: Accessibility report dictionary (if enabled).
        clearance_violations: List of clearance violation messages.
        material_compliance: Material certification status message.
        seismic_requirements: List of seismic requirements (if applicable).
        safety_labels: List of safety label dictionaries.
        safety_report_markdown: Full safety report in markdown format.
        warnings: List of warning messages.
        errors: List of error messages.
    """

    weight_capacities: list[dict[str, Any]]
    anti_tip_required: bool
    anti_tip_hardware: list[str] | None
    accessibility_report: dict[str, Any] | None
    clearance_violations: list[str]
    material_compliance: str
    seismic_requirements: list[str] | None
    safety_labels: list[dict[str, str]]
    safety_report_markdown: str
    warnings: list[str]
    errors: list[str]


__all__ = [
    # Input DTOs
    "LayoutParametersInput",
    "WallInput",
    # Output DTOs (re-exported from contracts)
    "CoreLayoutOutput",
    "InstallationOutput",
    "LayoutOutput",
    "PackingOutput",
    "RoomLayoutOutput",
    "WoodworkingOutput",
    # Safety output
    "SafetyOutput",
]
