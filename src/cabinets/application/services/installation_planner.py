"""Installation planner service for layout generation.

Coordinates installation planning, including service instantiation,
plan generation, and result transformation. Requires an
InstallationServiceFactory - no fallback instantiation for better
testability and explicit dependency management.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cabinets.contracts.factory import InstallationServiceFactory
    from cabinets.domain.entities import Cabinet
    from cabinets.domain.services.installation.config import InstallationConfig
    from cabinets.domain.value_objects import CutPiece


@dataclass
class InstallationPlanResult:
    """Result from installation planning.

    Contains augmented cut list, hardware, instructions, warnings,
    and stud analysis data from installation plan generation.

    Attributes:
        augmented_cut_list: Original cut list plus cleat cut pieces.
        hardware: List of mounting hardware items.
        instructions: Installation instructions in markdown format.
        warnings: List of installation-related warnings.
        stud_analysis: Stud alignment analysis as a dictionary.
    """

    augmented_cut_list: "list[CutPiece]"
    hardware: list
    instructions: str | None
    warnings: list[str]
    stud_analysis: dict[str, Any] | None


class InstallationPlannerService:
    """Service for coordinating installation planning.

    Encapsulates the orchestration of installation plan generation,
    including service instantiation via factory, plan generation,
    and result transformation.

    This service requires an InstallationServiceFactory in the
    constructor - there is no fallback to direct instantiation.
    This enforces proper dependency injection for testability.
    """

    def __init__(
        self, installation_service_factory: "InstallationServiceFactory"
    ) -> None:
        """Initialize with required installation service factory.

        Args:
            installation_service_factory: Factory for creating installation
                services. Cannot be None - explicit DI is required.
        """
        self._factory = installation_service_factory

    def plan_installation(
        self,
        cabinet: "Cabinet",
        cut_list: "list[CutPiece]",
        installation_config: "InstallationConfig",
        left_edge_position: float = 0.0,
    ) -> InstallationPlanResult:
        """Generate installation plan and augment cut list.

        Creates an installation service using the factory, generates
        the installation plan, and returns a structured result.

        Args:
            cabinet: Cabinet to generate installation plan for.
            cut_list: Existing cut list to augment with cleat pieces.
            installation_config: Configuration for installation planning.
            left_edge_position: Position of cabinet left edge from wall start.

        Returns:
            InstallationPlanResult with augmented cut list and plan details.
        """
        # Create installation service via factory
        installation_service = self._factory.create_installation_service(
            installation_config
        )

        # Generate plan
        plan = installation_service.generate_plan(
            cabinet, left_edge_position=left_edge_position
        )

        # Augment cut list with cleat pieces
        augmented_cut_list = list(cut_list) + list(plan.cleat_cut_pieces)

        # Build stud analysis dict
        stud_analysis = {
            "cabinet_left_edge": plan.stud_analysis.cabinet_left_edge,
            "cabinet_width": plan.stud_analysis.cabinet_width,
            "stud_positions": list(plan.stud_analysis.stud_positions),
            "non_stud_positions": list(plan.stud_analysis.non_stud_positions),
            "stud_hit_count": plan.stud_analysis.stud_hit_count,
            "recommendation": plan.stud_analysis.recommendation,
        }

        return InstallationPlanResult(
            augmented_cut_list=augmented_cut_list,
            hardware=list(plan.mounting_hardware),
            instructions=plan.instructions,
            warnings=list(plan.warnings),
            stud_analysis=stud_analysis,
        )
