"""Installation data models.

This module provides data models for cabinet installation specifications:
- CleatSpec: French cleat specification
- StudHitAnalysis: Stud alignment analysis
- WeightEstimate: Cabinet weight estimation
- InstallationPlan: Complete installation specification
"""

from __future__ import annotations

from dataclasses import dataclass

from ...components.results import HardwareItem
from ...value_objects import CutPiece


@dataclass(frozen=True)
class CleatSpec:
    """French cleat specification.

    Defines the dimensions and characteristics of a single cleat piece,
    either the wall-mounted cleat or the cabinet-mounted cleat.

    French cleats are beveled strips that interlock to support heavy loads.
    The wall cleat is mounted with the bevel facing up and out, while the
    cabinet cleat has the bevel facing down and in.

    Attributes:
        width: Width of the cleat in inches.
        height: Height of the cleat in inches (before bevel cut).
        thickness: Thickness of the cleat material in inches.
        bevel_angle: Angle of the bevel cut in degrees.
        is_wall_cleat: True if this is the wall-mounted cleat, False for cabinet cleat.
    """

    width: float
    height: float  # Before bevel cut
    thickness: float
    bevel_angle: float  # degrees
    is_wall_cleat: bool  # True = wall, False = cabinet

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Cleat width must be positive")
        if self.height <= 0:
            raise ValueError("Cleat height must be positive")
        if self.thickness <= 0:
            raise ValueError("Cleat thickness must be positive")
        if not 0 < self.bevel_angle < 90:
            raise ValueError("Bevel angle must be between 0 and 90 degrees")

    @property
    def label(self) -> str:
        """Generate a label for the cleat piece."""
        cleat_type = "Wall Cleat" if self.is_wall_cleat else "Cabinet Cleat"
        return f"French {cleat_type}"


@dataclass(frozen=True)
class StudHitAnalysis:
    """Analysis of mounting point alignment with wall studs.

    Analyzes how well a cabinet's mounting points align with the
    wall stud pattern, which is critical for secure installation.

    Attributes:
        cabinet_left_edge: Position of cabinet left edge from wall start in inches.
        cabinet_width: Width of the cabinet in inches.
        stud_positions: Tuple of positions that align with wall studs.
        non_stud_positions: Tuple of positions that miss wall studs.
        stud_hit_count: Number of mounting points that hit studs.
        recommendation: Optional recommendation for improving stud alignment.
    """

    cabinet_left_edge: float
    cabinet_width: float
    stud_positions: tuple[float, ...]  # Positions that hit studs
    non_stud_positions: tuple[float, ...]  # Positions that miss studs
    stud_hit_count: int
    recommendation: str | None = None

    def __post_init__(self) -> None:
        if self.cabinet_width <= 0:
            raise ValueError("Cabinet width must be positive")
        if self.stud_hit_count < 0:
            raise ValueError("Stud hit count must be non-negative")
        if self.stud_hit_count > len(self.stud_positions):
            raise ValueError("Stud hit count cannot exceed number of stud positions")

    @property
    def total_mounting_points(self) -> int:
        """Total number of analyzed mounting points."""
        return len(self.stud_positions) + len(self.non_stud_positions)

    @property
    def hit_percentage(self) -> float:
        """Percentage of mounting points that hit studs."""
        total = self.total_mounting_points
        if total == 0:
            return 0.0
        return (self.stud_hit_count / total) * 100


@dataclass(frozen=True)
class WeightEstimate:
    """Estimated cabinet weight and load.

    Advisory estimate of cabinet weight when empty and when loaded
    to expected capacity. Includes a disclaimer that this is for
    planning purposes only.

    Attributes:
        empty_weight_lbs: Estimated weight of empty cabinet in pounds.
        expected_load_per_foot: Expected load per linear foot based on load category.
        total_estimated_load_lbs: Total estimated load (cabinet + contents) in pounds.
        capacity_warning: Optional warning if load exceeds recommended limits.
        disclaimer: Legal disclaimer about advisory nature of estimates.
    """

    empty_weight_lbs: float
    expected_load_per_foot: float
    total_estimated_load_lbs: float
    capacity_warning: str | None = None
    disclaimer: str = (
        "Weight estimates are advisory only. Actual capacity depends on "
        "wall construction and installation quality."
    )

    def __post_init__(self) -> None:
        if self.empty_weight_lbs < 0:
            raise ValueError("Empty weight must be non-negative")
        if self.expected_load_per_foot < 0:
            raise ValueError("Expected load per foot must be non-negative")
        if self.total_estimated_load_lbs < 0:
            raise ValueError("Total estimated load must be non-negative")

    @property
    def formatted_summary(self) -> str:
        """Generate a formatted weight summary."""
        summary = (
            f"Empty weight: ~{self.empty_weight_lbs:.1f} lbs\n"
            f"Expected load: ~{self.expected_load_per_foot:.1f} lbs/ft\n"
            f"Total estimated: ~{self.total_estimated_load_lbs:.1f} lbs"
        )
        if self.capacity_warning:
            summary += f"\nWARNING: {self.capacity_warning}"
        return summary


@dataclass(frozen=True)
class InstallationPlan:
    """Complete installation specification.

    Contains all information needed to install a cabinet, including
    hardware requirements, cleat specifications (if using French cleats),
    stud alignment analysis, weight estimates, and step-by-step instructions.

    Attributes:
        mounting_hardware: Tuple of hardware items needed for installation.
        cleat_cut_pieces: Tuple of cut pieces for cleats (empty if not using cleats).
        stud_analysis: Analysis of mounting point alignment with wall studs.
        weight_estimate: Estimated weight and load capacity.
        instructions: Installation instructions in markdown format.
        warnings: Tuple of warning messages about the installation.
    """

    mounting_hardware: tuple[HardwareItem, ...]
    cleat_cut_pieces: tuple[CutPiece, ...]
    stud_analysis: StudHitAnalysis
    weight_estimate: WeightEstimate
    instructions: str  # Markdown
    warnings: tuple[str, ...]

    @property
    def has_warnings(self) -> bool:
        """Check if installation plan has any warnings."""
        return len(self.warnings) > 0

    @property
    def uses_cleats(self) -> bool:
        """Check if installation uses French cleats."""
        return len(self.cleat_cut_pieces) > 0

    @property
    def hardware_count(self) -> int:
        """Total count of all hardware items."""
        return sum(item.quantity for item in self.mounting_hardware)
