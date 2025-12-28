"""Data Transfer Objects for the application layer."""

from dataclasses import dataclass, field

from cabinets.domain import (
    Cabinet,
    CutPiece,
    MaterialEstimate,
    MaterialSpec,
    MaterialType,
)
from cabinets.domain.entities import Room
from cabinets.domain.value_objects import SectionTransform


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
    back_thickness: float = 0.5

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
class LayoutOutput:
    """Output DTO containing the generated layout results."""

    cabinet: Cabinet
    cut_list: list[CutPiece]
    material_estimates: dict[MaterialSpec, MaterialEstimate]
    total_estimate: MaterialEstimate
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the layout was generated successfully."""
        return len(self.errors) == 0


@dataclass
class RoomLayoutOutput:
    """Output DTO from room layout generation.

    Contains the complete room layout with cabinets positioned on multiple walls,
    their 3D transforms for rendering, and combined material estimates.

    Attributes:
        room: The Room entity with wall segment definitions.
        cabinets: List of Cabinet entities, one per wall section.
        transforms: List of SectionTransform objects for 3D positioning.
        cut_list: Combined cut list from all cabinets.
        material_estimates: Material estimates grouped by material type.
        total_estimate: Total material estimate across all cabinets.
        errors: List of error messages if generation failed.
    """

    room: Room
    cabinets: list[Cabinet]
    transforms: list[SectionTransform]
    cut_list: list[CutPiece]
    material_estimates: dict[MaterialSpec, MaterialEstimate]
    total_estimate: MaterialEstimate
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the room layout was generated successfully."""
        return len(self.errors) == 0
