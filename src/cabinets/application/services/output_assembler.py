"""Output assembler service for layout generation.

Centralizes DTO assembly logic extracted from GenerateLayoutCommand,
separating data transformation from business logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cabinets.contracts.dtos import (
    CoreLayoutOutput,
    InstallationOutput,
    LayoutOutput,
    RoomLayoutOutput,
    WoodworkingOutput,
)

if TYPE_CHECKING:
    from cabinets.contracts.protocols import (
        InstallationPlanResult,
        MaterialEstimatorProtocol,
    )
    from cabinets.domain.entities import Cabinet, Room
    from cabinets.domain.value_objects import CutPiece, SectionTransform


class OutputAssemblerService:
    """Service for assembling layout output DTOs.

    Centralizes output assembly logic that was previously inline in
    GenerateLayoutCommand methods. This enables:
    - Consistent output structure across different entry points
    - Easier unit testing of output assembly
    - Clear separation of DTO construction from business logic
    """

    def assemble_layout_output(
        self,
        cabinet: "Cabinet",
        cut_list: "list[CutPiece]",
        hardware: list,
        material_estimator: "MaterialEstimatorProtocol",
        installation_result: "InstallationPlanResult | None" = None,
    ) -> LayoutOutput:
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
        # Estimate materials
        material_estimates = material_estimator.estimate(cut_list)
        total_estimate = material_estimator.estimate_total(cut_list)

        # Build core output
        core = CoreLayoutOutput(
            cabinet=cabinet,
            cut_list=cut_list,
            material_estimates=material_estimates,
            total_estimate=total_estimate,
        )

        # Woodworking output (always present, may have empty hardware list)
        woodworking = WoodworkingOutput(hardware=hardware)

        # Installation output (only present if planning was done)
        installation = None
        if installation_result is not None:
            installation = InstallationOutput(
                hardware=installation_result.hardware,
                instructions=installation_result.instructions,
                warnings=installation_result.warnings,
                stud_analysis=installation_result.stud_analysis,
            )

        return LayoutOutput(
            core=core,
            woodworking=woodworking,
            installation=installation,
        )

    def assemble_room_layout_output(
        self,
        room: "Room",
        cabinets: "list[Cabinet]",
        transforms: "list[SectionTransform]",
        cut_list: "list[CutPiece]",
        material_estimator: "MaterialEstimatorProtocol",
    ) -> RoomLayoutOutput:
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
        material_estimates = material_estimator.estimate(cut_list)
        total_estimate = material_estimator.estimate_total(cut_list)

        return RoomLayoutOutput(
            room=room,
            cabinets=cabinets,
            transforms=transforms,
            cut_list=cut_list,
            material_estimates=material_estimates,
            total_estimate=total_estimate,
        )

    def create_error_output(self, errors: list[str]) -> LayoutOutput:
        """Create an error LayoutOutput with no cabinet.

        Args:
            errors: List of error messages.

        Returns:
            LayoutOutput with errors and empty/null fields.
        """
        return LayoutOutput(
            core=CoreLayoutOutput(
                cabinet=None,  # type: ignore
                cut_list=[],
                material_estimates={},
                total_estimate=None,  # type: ignore
                errors=errors,
            ),
        )

    def create_error_room_output(
        self, room: "Room", errors: list[str]
    ) -> RoomLayoutOutput:
        """Create an error RoomLayoutOutput with no cabinets.

        Args:
            room: Room entity (preserved in output).
            errors: List of error messages.

        Returns:
            RoomLayoutOutput with errors and empty cabinets.
        """
        return RoomLayoutOutput(
            room=room,
            cabinets=[],
            transforms=[],
            cut_list=[],
            material_estimates={},
            total_estimate=None,  # type: ignore
            errors=errors,
        )
