"""Installation service facade.

This module provides the InstallationService facade that maintains
backward compatibility with the original monolithic installation module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...components.results import HardwareItem
from ...value_objects import (
    CutPiece,
    LoadCategory,
    MaterialType,
)
from .cleat_service import CleatService
from .config import InstallationConfig
from .instruction_generator import InstructionGenerator
from .models import (
    InstallationPlan,
    StudHitAnalysis,
    WeightEstimate,
)
from .mounting_service import MountingService
from .stud_analyzer import StudAnalyzer
from .weight_estimator import WeightEstimator

if TYPE_CHECKING:
    from ...entities import Cabinet


class InstallationService:
    """Service for generating cabinet installation specifications.

    Provides methods for analyzing wall stud alignment, estimating
    cabinet weight, generating mounting hardware lists, and creating
    complete installation plans.

    The service follows woodworking best practices and building codes
    for secure cabinet installation.

    This is a facade that delegates to specialized services:
    - StudAnalyzer: Stud hit analysis
    - WeightEstimator: Cabinet weight estimation
    - MountingService: Hardware generation
    - CleatService: French cleat specifications
    - InstructionGenerator: Markdown instruction generation

    Example:
        >>> from cabinets.domain.services.installation import (
        ...     InstallationService,
        ...     InstallationConfig,
        ... )
        >>> config = InstallationConfig(
        ...     wall_type=WallType.DRYWALL,
        ...     mounting_system=MountingSystem.FRENCH_CLEAT,
        ... )
        >>> service = InstallationService(config)
        >>> plan = service.generate_plan(cabinet, left_edge_position=12.0)
    """

    # Material densities in lbs per square foot per inch of thickness
    # Used for estimating cabinet weight based on panel dimensions
    # Exposed for backward compatibility
    MATERIAL_DENSITIES: dict[MaterialType, float] = WeightEstimator.MATERIAL_DENSITIES

    # Load ratings per linear foot based on load category
    # Exposed for backward compatibility
    LOAD_RATINGS: dict[LoadCategory, float] = MountingService.LOAD_RATINGS

    # Safety factor for mounting calculations (4:1 ratio)
    # Exposed for backward compatibility
    SAFETY_FACTOR: float = MountingService.SAFETY_FACTOR

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the installation service.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config
        self._stud_analyzer = StudAnalyzer(config)
        self._weight_estimator = WeightEstimator(config)
        self._mounting_service = MountingService(config)
        self._cleat_service = CleatService(config)
        self._instruction_generator = InstructionGenerator(config)

    def generate_plan(
        self, cabinet: "Cabinet", left_edge_position: float = 0.0
    ) -> InstallationPlan:
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
        # Calculate stud analysis first as it's used by hardware generation
        stud_analysis = self.calculate_stud_hits(cabinet, left_edge_position)
        weight_estimate = self.estimate_weight(cabinet)
        hardware = self.generate_hardware(cabinet, stud_analysis)
        cleats = self.generate_cleats(cabinet)

        # Collect warnings from various analyses
        warnings: list[str] = []
        if stud_analysis.recommendation:
            warnings.append(stud_analysis.recommendation)
        if weight_estimate.capacity_warning:
            warnings.append(weight_estimate.capacity_warning)

        # Create plan without instructions first (to pass to generate_instructions)
        partial_plan = InstallationPlan(
            mounting_hardware=tuple(hardware),
            cleat_cut_pieces=tuple(cleats),
            stud_analysis=stud_analysis,
            weight_estimate=weight_estimate,
            instructions="",  # Placeholder
            warnings=tuple(warnings),
        )

        # Generate instructions with access to the full plan
        instructions = self.generate_instructions(cabinet, partial_plan)

        # Return final plan with complete instructions
        return InstallationPlan(
            mounting_hardware=tuple(hardware),
            cleat_cut_pieces=tuple(cleats),
            stud_analysis=stud_analysis,
            weight_estimate=weight_estimate,
            instructions=instructions,
            warnings=tuple(warnings),
        )

    def calculate_stud_hits(
        self, cabinet: "Cabinet", left_edge: float
    ) -> StudHitAnalysis:
        """Analyze which mounting points align with wall studs.

        Determines potential mounting point positions across the cabinet
        width and checks which ones align with wall studs based on the
        configured stud spacing and offset.

        Args:
            cabinet: Cabinet to analyze.
            left_edge: Position of cabinet left edge from wall start.

        Returns:
            StudHitAnalysis with stud alignment information.
        """
        return self._stud_analyzer.calculate_stud_hits(cabinet, left_edge)

    def estimate_weight(self, cabinet: "Cabinet") -> WeightEstimate:
        """Estimate cabinet weight and expected load.

        Calculates the estimated weight of the empty cabinet based on
        panel dimensions and material density, then adds expected load
        based on the configured load category.

        Args:
            cabinet: Cabinet to estimate weight for.

        Returns:
            WeightEstimate with weight and load information.
        """
        return self._weight_estimator.estimate_weight(cabinet)

    def generate_cleats(self, cabinet: "Cabinet") -> list[CutPiece]:
        """Generate French cleat cut pieces.

        Creates cut piece specifications for both the wall-mounted
        and cabinet-mounted cleats if the mounting system is set
        to French cleat.

        Args:
            cabinet: Cabinet to generate cleats for.

        Returns:
            List of CutPiece specifications for cleats.
            Empty list if not using French cleat system.
        """
        return self._cleat_service.generate_cleats(cabinet)

    def generate_hardware(
        self, cabinet: "Cabinet", stud_analysis: StudHitAnalysis
    ) -> list[HardwareItem]:
        """Generate mounting hardware list.

        Creates a list of hardware items needed for installation
        based on the mounting system, wall type, and stud alignment.

        Args:
            cabinet: Cabinet to generate hardware for.
            stud_analysis: Stud alignment analysis results.

        Returns:
            List of HardwareItem specifications for mounting.
        """
        return self._mounting_service.generate_hardware(cabinet, stud_analysis)

    def generate_instructions(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> str:
        """Generate installation instructions in markdown.

        Creates step-by-step installation instructions appropriate
        for the configured mounting system and wall type.

        Args:
            cabinet: Cabinet being installed.
            plan: Installation plan (may be None during plan generation).

        Returns:
            Installation instructions as markdown formatted string.
        """
        return self._instruction_generator.generate_instructions(cabinet, plan)
