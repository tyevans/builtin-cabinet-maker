"""Service protocols for dependency injection.

This module defines protocol classes that establish contracts between layers.
Infrastructure implementations depend on these protocols, enabling loose coupling
and testability through dependency injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet, Room, Wall, WallSegment
    from cabinets.domain.section_resolver import RowSpec, SectionSpec
    from cabinets.domain.services.installation.config import InstallationConfig
    from cabinets.domain.services.installation.models import InstallationPlan
    from cabinets.domain.services.layout_calculator import LayoutParameters
    from cabinets.domain.services.material_estimator import MaterialEstimate
    from cabinets.domain.value_objects import CutPiece, MaterialSpec, SectionTransform
    from cabinets.application.dtos import (
        LayoutOutput,
        LayoutParametersInput,
        RoomLayoutOutput,
        WallInput,
    )


class LayoutCalculatorProtocol(Protocol):
    """Protocol for cabinet layout calculation.

    Implementations generate cabinet layouts from wall dimensions and
    layout parameters. This is the core service for cabinet generation.

    Example:
        ```python
        class LayoutCalculator:
            def generate_cabinet(
                self, wall: Wall, params: LayoutParameters, section_specs: list | None = None
            ) -> Cabinet:
                # Implementation
                ...
        ```
    """

    def generate_cabinet(
        self,
        wall: Wall,
        params: LayoutParameters,
        section_specs: list | None = None,
    ) -> Cabinet:
        """Generate a complete cabinet layout.

        Args:
            wall: Wall dimensions constraining the cabinet.
            params: Layout parameters including section count and shelves per section.
            section_specs: Optional list of section specifications for custom layouts.

        Returns:
            A Cabinet entity with the generated layout.
        """
        ...

    def generate_cabinet_from_specs(
        self,
        wall: Wall,
        params: LayoutParameters,
        section_specs: "list[SectionSpec]",
        default_shelf_count: int = 0,
        zone_configs: "dict[str, dict | None] | None" = None,
    ) -> "tuple[Cabinet, list]":
        """Generate a cabinet layout with specified section widths and shelf counts.

        Args:
            wall: Wall dimensions constraining the cabinet.
            params: Layout parameters (material specs are used from here).
            section_specs: List of section specifications with widths and shelf counts.
            default_shelf_count: Default number of shelves for sections with shelves=0.
            zone_configs: Optional dict with zone configurations.

        Returns:
            A tuple of (Cabinet, list[HardwareItem]).
        """
        ...


class CutListGeneratorProtocol(Protocol):
    """Protocol for cut list generation.

    Implementations generate a list of cut pieces from a cabinet entity,
    consolidating pieces with matching dimensions and materials.

    Example:
        ```python
        class CutListGenerator:
            def generate(self, cabinet: Cabinet) -> list[CutPiece]:
                # Implementation
                ...
        ```
    """

    def generate(self, cabinet: Cabinet) -> list[CutPiece]:
        """Generate a cut list for the given cabinet.

        Args:
            cabinet: The cabinet to generate a cut list for.

        Returns:
            List of CutPiece objects with consolidated quantities.
        """
        ...

    def sort_by_size(self, cut_list: list[CutPiece]) -> list[CutPiece]:
        """Sort cut list by area (largest first) for efficient cutting.

        Args:
            cut_list: List of cut pieces to sort.

        Returns:
            Sorted list of CutPiece objects.
        """
        ...


class MaterialEstimatorProtocol(Protocol):
    """Protocol for material estimation.

    Implementations estimate material requirements from a cut list,
    grouping by material type and calculating sheet counts.

    Example:
        ```python
        class MaterialEstimator:
            def estimate(
                self, cut_list: list[CutPiece]
            ) -> dict[MaterialSpec, MaterialEstimate]:
                # Implementation
                ...
        ```
    """

    def estimate(
        self, cut_list: list[CutPiece]
    ) -> dict[MaterialSpec, MaterialEstimate]:
        """Estimate materials needed for a cut list, grouped by material type.

        Args:
            cut_list: List of cut pieces to estimate materials for.

        Returns:
            Dictionary mapping MaterialSpec to MaterialEstimate.
        """
        ...

    def estimate_total(self, cut_list: list[CutPiece]) -> MaterialEstimate:
        """Estimate total materials needed (all types combined).

        Args:
            cut_list: List of cut pieces to estimate materials for.

        Returns:
            MaterialEstimate for the total.
        """
        ...


class RoomLayoutServiceProtocol(Protocol):
    """Protocol for room layout generation.

    Implementations handle multi-wall room layouts, assigning cabinet
    sections to walls and computing 3D transforms for STL generation.

    Example:
        ```python
        class RoomLayoutService:
            def generate_room_layout(
                self, room: Room, params: LayoutParameters
            ) -> Room:
                # Implementation
                ...
        ```
    """

    def generate_room_layout(self, room: Room, params: LayoutParameters) -> Room:
        """Generate a complete room layout with cabinets on multiple walls.

        Args:
            room: The room containing wall segments.
            params: Layout parameters for cabinet generation.

        Returns:
            The Room entity with cabinets positioned on walls.
        """
        ...

    def validate_fit(
        self,
        room: Room,
        section_specs: "list[SectionSpec]",
    ) -> list:
        """Check that sections fit on their assigned walls.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications to validate.

        Returns:
            List of FitError objects describing any issues found.
        """
        ...

    def assign_sections_to_walls(
        self,
        room: Room,
        section_specs: "list[SectionSpec]",
    ) -> list:
        """Assign cabinet sections to wall segments.

        Args:
            room: The room containing wall segments.
            section_specs: List of section specifications to assign.

        Returns:
            List of WallSectionAssignment objects with computed positions.
        """
        ...

    def compute_section_transforms(
        self,
        room: Room,
        assignments: list,
        section_specs: "list[SectionSpec]",
    ) -> list:
        """Compute 3D position and rotation for each section.

        Args:
            room: The room containing wall segments.
            assignments: Wall assignments for each section.
            section_specs: Original section specifications (for width calculation).

        Returns:
            List of SectionTransform objects with 3D positions and rotations.
        """
        ...


@runtime_checkable
class InstallationServiceProtocol(Protocol):
    """Protocol for cabinet installation planning.

    Implementations generate installation plans including mounting hardware,
    French cleat specifications, stud alignment analysis, weight estimates,
    and step-by-step installation instructions.

    This protocol enables dependency injection for the InstallationService,
    allowing unit tests to mock installation behavior without depending on
    the concrete implementation.

    Example:
        ```python
        class InstallationService:
            def generate_plan(
                self, cabinet: Cabinet, left_edge_position: float = 0.0
            ) -> InstallationPlan:
                # Implementation
                ...
        ```
    """

    def generate_plan(
        self, cabinet: "Cabinet", left_edge_position: float = 0.0
    ) -> "InstallationPlan":
        """Generate complete installation plan for a cabinet.

        Creates a comprehensive installation plan including hardware
        requirements, mounting specifications, and step-by-step
        instructions.

        Args:
            cabinet: Cabinet to generate installation plan for.
            left_edge_position: Position of cabinet left edge from wall start.

        Returns:
            Complete InstallationPlan with all installation details.
        """
        ...


@runtime_checkable
class InputValidatorProtocol(Protocol):
    """Protocol for validating layout generation inputs.

    Centralizes validation logic for wall inputs, layout parameters,
    and section/row specifications. Enables consistent error reporting
    and easier testing of validation rules.
    """

    def validate_wall_input(self, wall_input: "WallInput") -> list[str]:
        """Validate wall dimensions input.

        Args:
            wall_input: Wall dimensions to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        ...

    def validate_params_input(self, params_input: "LayoutParametersInput") -> list[str]:
        """Validate layout parameters input.

        Args:
            params_input: Layout parameters to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        ...

    def validate_specs(
        self,
        section_specs: "list[SectionSpec] | None",
        row_specs: "list[RowSpec] | None",
        wall_width: float,
        wall_height: float,
        material_thickness: float,
    ) -> list[str]:
        """Validate section and row specifications.

        Checks mutual exclusivity (can't use both section_specs and row_specs),
        and validates that specs fit within wall dimensions.

        Args:
            section_specs: Optional section specifications.
            row_specs: Optional row specifications for multi-row layouts.
            wall_width: Wall width for fit validation.
            wall_height: Wall height for fit validation.
            material_thickness: Material thickness for validation.

        Returns:
            List of validation error messages (empty if valid).
        """
        ...


@runtime_checkable
class InstallationPlannerProtocol(Protocol):
    """Protocol for coordinating installation planning.

    Encapsulates the orchestration of installation plan generation,
    including service instantiation, plan generation, and result
    transformation. Requires an InstallationServiceFactory - no
    fallback instantiation for better testability.
    """

    def plan_installation(
        self,
        cabinet: "Cabinet",
        cut_list: "list[CutPiece]",
        installation_config: "InstallationConfig",
        left_edge_position: float = 0.0,
    ) -> "InstallationPlanResult":
        """Generate installation plan and augment cut list.

        Args:
            cabinet: Cabinet to generate installation plan for.
            cut_list: Existing cut list to augment with cleat pieces.
            installation_config: Configuration for installation planning.
            left_edge_position: Position of cabinet left edge from wall start.

        Returns:
            InstallationPlanResult with augmented cut list and plan details.
        """
        ...


@runtime_checkable
class OutputAssemblerProtocol(Protocol):
    """Protocol for assembling layout output DTOs.

    Centralizes output assembly logic, separating DTO construction
    from business logic in the command layer.
    """

    def assemble_layout_output(
        self,
        cabinet: "Cabinet",
        cut_list: "list[CutPiece]",
        hardware: list,
        material_estimator: "MaterialEstimatorProtocol",
        installation_result: "InstallationPlanResult | None" = None,
    ) -> "LayoutOutput":
        """Assemble complete LayoutOutput from components.

        Args:
            cabinet: Generated cabinet entity.
            cut_list: Sorted cut list (may include installation pieces).
            hardware: List of hardware items from woodworking.
            material_estimator: Estimator for material calculations.
            installation_result: Optional installation plan result.

        Returns:
            Complete LayoutOutput DTO.
        """
        ...

    def assemble_room_layout_output(
        self,
        room: "Room",
        cabinets: "list[Cabinet]",
        transforms: "list[SectionTransform]",
        cut_list: "list[CutPiece]",
        material_estimator: "MaterialEstimatorProtocol",
    ) -> "RoomLayoutOutput":
        """Assemble RoomLayoutOutput from components.

        Args:
            room: Room entity with wall definitions.
            cabinets: List of generated cabinets.
            transforms: 3D transforms for each cabinet.
            cut_list: Combined sorted cut list.
            material_estimator: Estimator for material calculations.

        Returns:
            Complete RoomLayoutOutput DTO.
        """
        ...

    def create_error_output(self, errors: list[str]) -> "LayoutOutput":
        """Create an error LayoutOutput with no cabinet.

        Args:
            errors: List of error messages.

        Returns:
            LayoutOutput with errors and empty cabinet.
        """
        ...

    def create_error_room_output(
        self, room: "Room", errors: list[str]
    ) -> "RoomLayoutOutput":
        """Create an error RoomLayoutOutput with no cabinets.

        Args:
            room: Room entity (preserved in output).
            errors: List of error messages.

        Returns:
            RoomLayoutOutput with errors and empty cabinets.
        """
        ...


@runtime_checkable
class SectionWidthResolverProtocol(Protocol):
    """Protocol for resolving section widths in room context.

    Handles "fill" width calculation for sections that should expand
    to fill remaining wall space, accounting for other sections on
    the same wall.
    """

    def resolve_width(
        self,
        section_spec: "SectionSpec",
        wall_segment: "WallSegment",
        all_specs: "list[SectionSpec]",
        room: "Room",
    ) -> float:
        """Resolve the width for a section spec on a given wall.

        For fixed widths, returns the width directly.
        For fill widths, calculates based on remaining space on the wall.

        Args:
            section_spec: Section specification to resolve.
            wall_segment: Wall segment this section is on.
            all_specs: All section specifications (for fill calculation).
            room: Room containing the walls.

        Returns:
            Resolved section width in inches.
        """
        ...

    def get_wall_index(self, spec: "SectionSpec", room: "Room") -> int:
        """Get the wall index for a section spec.

        Args:
            spec: Section specification.
            room: Room containing the walls.

        Returns:
            Wall index (0-based).
        """
        ...


@runtime_checkable
class RoomLayoutOrchestratorProtocol(Protocol):
    """Protocol for orchestrating multi-wall room layouts.

    Coordinates validation, section assignment, cabinet generation,
    and output assembly for room layouts with multiple wall segments.
    """

    def orchestrate(
        self,
        room: "Room",
        section_specs: "list[SectionSpec]",
        params_input: "LayoutParametersInput",
    ) -> "RoomLayoutOutput":
        """Orchestrate complete room layout generation.

        Args:
            room: Room entity with wall segment definitions.
            section_specs: Section specifications with wall assignments.
            params_input: Layout parameters (material specs).

        Returns:
            RoomLayoutOutput with cabinets, transforms, and estimates.
        """
        ...


# Forward reference for InstallationPlanResult (defined in application layer)
class InstallationPlanResult(Protocol):
    """Result from installation planning.

    Contains augmented cut list, hardware, instructions, warnings,
    and stud analysis data.
    """

    augmented_cut_list: "list[CutPiece]"
    hardware: list
    instructions: str | None
    warnings: list[str]
    stud_analysis: dict | None


__all__ = [
    "CutListGeneratorProtocol",
    "InputValidatorProtocol",
    "InstallationPlannerProtocol",
    "InstallationPlanResult",
    "InstallationServiceProtocol",
    "LayoutCalculatorProtocol",
    "MaterialEstimatorProtocol",
    "OutputAssemblerProtocol",
    "RoomLayoutOrchestratorProtocol",
    "RoomLayoutServiceProtocol",
    "SectionWidthResolverProtocol",
]
