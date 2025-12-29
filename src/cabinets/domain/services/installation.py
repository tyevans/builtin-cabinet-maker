"""Installation support domain services and data models.

This module provides:
- Data models for cabinet installation specifications
- French cleat specifications
- Stud alignment analysis
- Weight estimation
- Installation planning service
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..components.results import HardwareItem
from ..value_objects import (
    CutPiece,
    LoadCategory,
    MaterialType,
    MountingSystem,
    PanelType,
    WallType,
)

if TYPE_CHECKING:
    from ..entities import Cabinet


@dataclass(frozen=True)
class InstallationConfig:
    """Configuration for cabinet installation.

    Contains all parameters needed to plan cabinet installation,
    including wall construction details, mounting method, and
    expected load category.

    Attributes:
        wall_type: Type of wall construction (drywall, plaster, concrete, etc.).
        wall_thickness: Thickness of wall covering in inches (default 0.5 for drywall).
        stud_spacing: Distance between wall studs in inches (default 16.0 OC).
        stud_offset: Distance from wall start to first stud in inches.
        mounting_system: Method used to mount cabinet to wall.
        expected_load: Expected load category for capacity planning.
        cleat_position_from_top: Distance from cabinet top to cleat center in inches.
        cleat_width_percentage: Cleat width as percentage of cabinet width (0-100).
        cleat_bevel_angle: Bevel angle for French cleat in degrees.
    """

    wall_type: WallType = WallType.DRYWALL
    wall_thickness: float = 0.5  # inches (1/2" drywall standard)
    stud_spacing: float = 16.0  # inches on center
    stud_offset: float = 0.0  # first stud from wall start
    mounting_system: MountingSystem = MountingSystem.DIRECT_TO_STUD
    expected_load: LoadCategory = LoadCategory.MEDIUM
    cleat_position_from_top: float = 4.0  # inches
    cleat_width_percentage: float = 90.0  # percent of cabinet width
    cleat_bevel_angle: float = 45.0  # degrees

    def __post_init__(self) -> None:
        if self.wall_thickness <= 0:
            raise ValueError("Wall thickness must be positive")
        if self.stud_spacing <= 0:
            raise ValueError("Stud spacing must be positive")
        if self.stud_offset < 0:
            raise ValueError("Stud offset must be non-negative")
        if self.cleat_position_from_top < 0:
            raise ValueError("Cleat position from top must be non-negative")
        if not 0 < self.cleat_width_percentage <= 100:
            raise ValueError("Cleat width percentage must be between 0 and 100")
        if not 0 < self.cleat_bevel_angle < 90:
            raise ValueError("Cleat bevel angle must be between 0 and 90 degrees")


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


class InstallationService:
    """Service for generating cabinet installation specifications.

    Provides methods for analyzing wall stud alignment, estimating
    cabinet weight, generating mounting hardware lists, and creating
    complete installation plans.

    The service follows woodworking best practices and building codes
    for secure cabinet installation.

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
    MATERIAL_DENSITIES: dict[MaterialType, float] = {
        MaterialType.PLYWOOD: 3.0,
        MaterialType.MDF: 4.0,
        MaterialType.PARTICLE_BOARD: 3.5,
        MaterialType.SOLID_WOOD: 3.5,
    }

    # Load ratings per linear foot based on load category
    LOAD_RATINGS: dict[LoadCategory, float] = {
        LoadCategory.LIGHT: 15.0,
        LoadCategory.MEDIUM: 30.0,
        LoadCategory.HEAVY: 50.0,
    }

    # Safety factor for mounting calculations (4:1 ratio)
    SAFETY_FACTOR: float = 4.0

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the installation service.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config

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
        cabinet_right_edge = left_edge + cabinet.width
        stud_positions: list[float] = []
        non_stud_positions: list[float] = []

        # Calculate all stud positions that fall within the cabinet span
        # First stud is at stud_offset from wall start
        current_stud = self.config.stud_offset
        while current_stud <= cabinet_right_edge:
            if current_stud >= left_edge:
                # This stud is within cabinet span
                # Record the position relative to the wall (absolute position)
                stud_positions.append(current_stud)
            current_stud += self.config.stud_spacing

        # Calculate potential mounting points that miss studs
        # Mounting points are typically at the cabinet edges and at regular intervals
        # Standard mounting points: near left edge, near right edge, and any in between
        mounting_interval = 16.0  # Standard mounting point spacing
        edge_offset = 3.0  # Offset from cabinet edge for mounting points

        # Collect all potential mounting point positions
        potential_points: list[float] = []
        potential_points.append(left_edge + edge_offset)  # Near left edge
        potential_points.append(cabinet_right_edge - edge_offset)  # Near right edge

        # Add intermediate points if cabinet is wide enough
        current_point = left_edge + edge_offset + mounting_interval
        while current_point < cabinet_right_edge - edge_offset:
            potential_points.append(current_point)
            current_point += mounting_interval

        # Determine which points hit studs (within 0.5" tolerance)
        stud_tolerance = 0.5
        for point in potential_points:
            hits_stud = False
            for stud_pos in stud_positions:
                if abs(point - stud_pos) <= stud_tolerance:
                    hits_stud = True
                    break
            if not hits_stud:
                non_stud_positions.append(point)

        stud_hit_count = len(stud_positions)
        recommendation: str | None = None

        if stud_hit_count < 2:
            if stud_hit_count == 0:
                recommendation = (
                    "No stud hits detected within cabinet span. "
                    "Consider using toggle bolts, wall anchors, or repositioning "
                    "the cabinet for better stud alignment."
                )
            else:
                recommendation = (
                    "Only 1 stud hit detected. For secure mounting, consider "
                    "using toggle bolts for non-stud locations or repositioning "
                    "cabinet to align with at least 2 studs."
                )

        return StudHitAnalysis(
            cabinet_left_edge=left_edge,
            cabinet_width=cabinet.width,
            stud_positions=tuple(stud_positions),
            non_stud_positions=tuple(non_stud_positions),
            stud_hit_count=stud_hit_count,
            recommendation=recommendation,
        )

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
        # Calculate empty weight from panel areas
        # Weight = area (sq ft) * thickness (inches) * density (lbs/sqft/inch)
        panels = cabinet.get_all_panels()
        empty_weight_lbs = 0.0

        for panel in panels:
            # Convert dimensions from inches to feet for area calculation
            area_sqin = panel.width * panel.height
            area_sqft = area_sqin / 144.0  # 144 sq inches per sq foot

            # Get material density (lbs per sqft per inch of thickness)
            density = self.MATERIAL_DENSITIES.get(
                panel.material.material_type, 3.0  # Default to plywood density
            )

            # Weight = area * thickness * density
            panel_weight = area_sqft * panel.material.thickness * density
            empty_weight_lbs += panel_weight

        # Calculate expected load based on cabinet width and load category
        cabinet_width_ft = cabinet.width / 12.0
        load_per_foot = self.LOAD_RATINGS[self.config.expected_load]
        expected_load = cabinet_width_ft * load_per_foot

        # Total estimated load
        total_estimated_load_lbs = empty_weight_lbs + expected_load

        # Generate capacity warning if load is heavy
        capacity_warning: str | None = None

        # Safe mounting capacity thresholds (approximate)
        # Direct to stud: ~150 lbs per stud with proper screws
        # Toggle bolts: ~50-75 lbs per toggle
        # French cleat: depends on stud mounting
        if self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
            # Toggle bolts have lower capacity
            safe_threshold = 100.0  # Conservative threshold for toggle bolts
            if total_estimated_load_lbs > safe_threshold:
                capacity_warning = (
                    f"Total estimated load ({total_estimated_load_lbs:.0f} lbs) may exceed "
                    "safe capacity for toggle bolt mounting. Consider using French cleat "
                    "with stud mounting or direct-to-stud installation."
                )
        elif self.config.expected_load == LoadCategory.HEAVY:
            safe_threshold = 200.0  # Threshold for heavy loads
            if total_estimated_load_lbs > safe_threshold:
                capacity_warning = (
                    f"Heavy load configuration ({total_estimated_load_lbs:.0f} lbs estimated). "
                    "Ensure mounting into at least 2 studs with appropriate lag bolts "
                    "or use a French cleat system for secure installation."
                )

        return WeightEstimate(
            empty_weight_lbs=round(empty_weight_lbs, 1),
            expected_load_per_foot=load_per_foot,
            total_estimated_load_lbs=round(total_estimated_load_lbs, 1),
            capacity_warning=capacity_warning,
        )

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
        # Return empty list if not using French cleat system
        if self.config.mounting_system != MountingSystem.FRENCH_CLEAT:
            return []

        cleats: list[CutPiece] = []

        # Calculate cleat dimensions
        cleat_width = cabinet.width * (self.config.cleat_width_percentage / 100.0)
        cleat_height = 3.0  # Standard cleat height (before bevel)
        cleat_thickness = cabinet.material.thickness

        # Wall cleat - mounted to wall with bevel facing up and out
        wall_cleat = CutPiece(
            width=cleat_width,
            height=cleat_height,
            quantity=1,
            label="French Cleat (Wall)",
            panel_type=PanelType.NAILER,
            material=cabinet.material,
            cut_metadata={
                "bevel_angle": self.config.cleat_bevel_angle,
                "bevel_edge": "top",
                "grain_direction": "length",
                "installation_note": (
                    "Mount to wall with bevel facing up and outward. "
                    "Secure into wall studs with lag bolts."
                ),
            },
        )
        cleats.append(wall_cleat)

        # Cabinet cleat - attached to cabinet back with bevel facing down and in
        cabinet_cleat = CutPiece(
            width=cleat_width,
            height=cleat_height,
            quantity=1,
            label="French Cleat (Cabinet)",
            panel_type=PanelType.NAILER,
            material=cabinet.material,
            cut_metadata={
                "bevel_angle": self.config.cleat_bevel_angle,
                "bevel_edge": "bottom",
                "grain_direction": "length",
                "installation_note": (
                    "Attach to cabinet back with bevel facing down and inward. "
                    f"Position {self.config.cleat_position_from_top}\" from cabinet top."
                ),
            },
        )
        cleats.append(cabinet_cleat)

        return cleats

    # Standard screw lengths available (inches)
    STANDARD_SCREW_LENGTHS: tuple[float, ...] = (
        1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0
    )

    def _calculate_screw_length(self, back_thickness: float) -> float:
        """Calculate required screw length and round up to standard size.

        Args:
            back_thickness: Cabinet back panel thickness in inches.

        Returns:
            Standard screw length in inches.
        """
        # Minimum penetration into stud/wall
        min_penetration = 1.5
        # Required length = back + wall + penetration
        required_length = (
            back_thickness + self.config.wall_thickness + min_penetration
        )

        # Round up to next standard length
        for std_length in self.STANDARD_SCREW_LENGTHS:
            if std_length >= required_length:
                return std_length

        # If exceeds all standard lengths, return the maximum
        return self.STANDARD_SCREW_LENGTHS[-1]

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
        hardware: list[HardwareItem] = []
        back_thickness = cabinet.back_material.thickness if cabinet.back_material else 0.25

        # Handle masonry walls (concrete, CMU, brick)
        if self.config.wall_type in (WallType.CONCRETE, WallType.CMU, WallType.BRICK):
            hardware.extend(self._generate_masonry_hardware(cabinet))
            return hardware

        # Handle drywall/plaster walls based on mounting system
        if self.config.mounting_system == MountingSystem.DIRECT_TO_STUD:
            hardware.extend(
                self._generate_direct_to_stud_hardware(cabinet, stud_analysis, back_thickness)
            )

        elif self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
            hardware.extend(
                self._generate_toggle_bolt_hardware(cabinet)
            )

        elif self.config.mounting_system == MountingSystem.FRENCH_CLEAT:
            hardware.extend(
                self._generate_french_cleat_hardware(cabinet, stud_analysis)
            )

        elif self.config.mounting_system == MountingSystem.HANGING_RAIL:
            hardware.extend(
                self._generate_hanging_rail_hardware(cabinet, stud_analysis)
            )

        return hardware

    def _generate_direct_to_stud_hardware(
        self,
        cabinet: "Cabinet",
        stud_analysis: StudHitAnalysis,
        back_thickness: float,
    ) -> list[HardwareItem]:
        """Generate hardware for direct-to-stud mounting."""
        hardware: list[HardwareItem] = []

        screw_length = self._calculate_screw_length(back_thickness)
        stud_hit_count = max(stud_analysis.stud_hit_count, 2)  # Minimum 2 locations
        screws_per_stud = 2  # 2 screws per stud location (top and bottom)

        hardware.append(
            HardwareItem(
                name=f'#10 x {screw_length}" cabinet screw',
                quantity=stud_hit_count * screws_per_stud,
                sku=None,
                notes="Direct mounting into wall studs",
            )
        )

        return hardware

    def _generate_toggle_bolt_hardware(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Generate hardware for toggle bolt mounting."""
        hardware: list[HardwareItem] = []

        # Determine toggle bolt size based on load category
        if self.config.expected_load == LoadCategory.HEAVY:
            toggle_size = '3/8"'
            capacity_per_toggle = 75.0  # lbs
        else:
            toggle_size = '1/4"'
            capacity_per_toggle = 50.0  # lbs

        # Calculate quantity based on load with safety factor
        cabinet_width_ft = cabinet.width / 12.0
        expected_load = cabinet_width_ft * self.LOAD_RATINGS[self.config.expected_load]
        required_capacity = expected_load * self.SAFETY_FACTOR
        qty = max(4, int(required_capacity / capacity_per_toggle) + 1)

        hardware.append(
            HardwareItem(
                name=f'{toggle_size} toggle bolt',
                quantity=qty,
                sku=None,
                notes=f"For non-stud mounting, {capacity_per_toggle:.0f} lb capacity each",
            )
        )

        return hardware

    def _generate_french_cleat_hardware(
        self, cabinet: "Cabinet", stud_analysis: StudHitAnalysis
    ) -> list[HardwareItem]:
        """Generate hardware for French cleat mounting."""
        hardware: list[HardwareItem] = []

        stud_hit_count = max(stud_analysis.stud_hit_count, 2)

        # Lag bolts for wall cleat mounting into studs
        hardware.append(
            HardwareItem(
                name='1/4" x 3" lag bolt',
                quantity=stud_hit_count,
                sku=None,
                notes="For mounting wall cleat into studs",
            )
        )

        # Washers for lag bolts
        hardware.append(
            HardwareItem(
                name='1/4" flat washer',
                quantity=stud_hit_count,
                sku=None,
                notes="Use with lag bolts",
            )
        )

        # Cabinet screws for attaching cabinet cleat to cabinet back
        # Calculate based on cleat width
        cleat_width = cabinet.width * (self.config.cleat_width_percentage / 100.0)
        screw_spacing = 6.0  # inches
        cabinet_cleat_screws = max(4, int(cleat_width / screw_spacing) + 1)

        hardware.append(
            HardwareItem(
                name='#8 x 1-1/4" wood screw',
                quantity=cabinet_cleat_screws,
                sku=None,
                notes="For attaching cleat to cabinet back",
            )
        )

        return hardware

    def _generate_hanging_rail_hardware(
        self, cabinet: "Cabinet", stud_analysis: StudHitAnalysis
    ) -> list[HardwareItem]:
        """Generate hardware for hanging rail mounting."""
        hardware: list[HardwareItem] = []

        # Hanging rail
        hardware.append(
            HardwareItem(
                name=f'{cabinet.width:.0f}" hanging rail',
                quantity=1,
                sku=None,
                notes="Standard cabinet hanging rail system",
            )
        )

        # Rail mounting screws (based on stud hits)
        stud_hit_count = max(stud_analysis.stud_hit_count, 2)
        hardware.append(
            HardwareItem(
                name='#10 x 3" cabinet screw',
                quantity=stud_hit_count * 2,
                sku=None,
                notes="For mounting rail into studs",
            )
        )

        # Cabinet mounting brackets (typically 2 per cabinet)
        hardware.append(
            HardwareItem(
                name="Hanging rail bracket",
                quantity=2,
                sku=None,
                notes="Mount inside cabinet, hooks onto rail",
            )
        )

        return hardware

    def _generate_masonry_hardware(self, cabinet: "Cabinet") -> list[HardwareItem]:
        """Generate hardware for masonry wall mounting."""
        hardware: list[HardwareItem] = []

        # Determine Tapcon size based on load
        if self.config.expected_load == LoadCategory.HEAVY:
            tapcon_size = '1/4" x 2-3/4"'
            drill_bit = '3/16"'
        else:
            tapcon_size = '3/16" x 2-3/4"'
            drill_bit = '5/32"'

        # Calculate quantity based on load with safety factor
        cabinet_width_ft = cabinet.width / 12.0
        expected_load = cabinet_width_ft * self.LOAD_RATINGS[self.config.expected_load]

        # Tapcons: ~100 lbs capacity each in concrete
        capacity_per_tapcon = 100.0
        required_capacity = expected_load * self.SAFETY_FACTOR
        qty = max(4, int(required_capacity / capacity_per_tapcon) + 1)

        hardware.append(
            HardwareItem(
                name=f'{tapcon_size} Tapcon screw',
                quantity=qty,
                sku=None,
                notes=f"For {self.config.wall_type.value} wall mounting",
            )
        )

        hardware.append(
            HardwareItem(
                name=f'{drill_bit} carbide masonry drill bit',
                quantity=1,
                sku=None,
                notes=f"Required for pre-drilling Tapcon holes",
            )
        )

        return hardware

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
        lines: list[str] = []

        # Header with cabinet dimensions
        lines.append("# Cabinet Installation Instructions")
        lines.append("")
        lines.append("## Cabinet Specifications")
        lines.append("")
        lines.append(f"- **Width:** {cabinet.width:.1f}\"")
        lines.append(f"- **Height:** {cabinet.height:.1f}\"")
        lines.append(f"- **Depth:** {cabinet.depth:.1f}\"")
        lines.append(f"- **Wall Type:** {self.config.wall_type.value.title()}")
        lines.append(f"- **Mounting System:** {self._format_mounting_system()}")
        lines.append("")

        # Tools Required section
        lines.append("## Tools Required")
        lines.append("")
        lines.extend(self._generate_tools_list())
        lines.append("")

        # Hardware list if plan is available
        if plan and plan.mounting_hardware:
            lines.append("## Hardware Required")
            lines.append("")
            for hw in plan.mounting_hardware:
                qty_str = f"{hw.quantity}x" if hw.quantity > 1 else "1x"
                lines.append(f"- {qty_str} {hw.name}")
                if hw.notes:
                    lines.append(f"  - {hw.notes}")
            lines.append("")

        # Step-by-step procedure
        lines.append("## Installation Procedure")
        lines.append("")
        lines.extend(self._generate_procedure_steps(cabinet, plan))
        lines.append("")

        # Safety Notes section
        lines.append("## Safety Notes")
        lines.append("")
        lines.extend(self._generate_safety_notes(plan))
        lines.append("")

        # Disclaimer (required)
        lines.append("## Disclaimer")
        lines.append("")
        lines.append(
            "For reference only. Consult local codes and a professional "
            "installer for critical installations."
        )
        lines.append("")

        return "\n".join(lines)

    def _format_mounting_system(self) -> str:
        """Format mounting system name for display."""
        system_names = {
            MountingSystem.DIRECT_TO_STUD: "Direct to Stud",
            MountingSystem.FRENCH_CLEAT: "French Cleat",
            MountingSystem.TOGGLE_BOLT: "Toggle Bolt",
            MountingSystem.HANGING_RAIL: "Hanging Rail",
        }
        return system_names.get(self.config.mounting_system, "Direct to Stud")

    def _generate_tools_list(self) -> list[str]:
        """Generate list of required tools based on configuration."""
        tools: list[str] = []

        # Common tools for all installations
        tools.append("- Level (48\" minimum recommended)")
        tools.append("- Tape measure")
        tools.append("- Pencil")
        tools.append("- Drill/driver")

        # Stud finder for stud-based mounting
        if self.config.wall_type in (WallType.DRYWALL, WallType.PLASTER):
            if self.config.mounting_system in (
                MountingSystem.DIRECT_TO_STUD,
                MountingSystem.FRENCH_CLEAT,
                MountingSystem.HANGING_RAIL,
            ):
                tools.append("- Stud finder")

        # Masonry tools
        if self.config.wall_type in (WallType.CONCRETE, WallType.CMU, WallType.BRICK):
            tools.append("- Hammer drill")
            if self.config.expected_load == LoadCategory.HEAVY:
                tools.append("- 3/16\" carbide masonry drill bit")
            else:
                tools.append("- 5/32\" carbide masonry drill bit")

        # Pilot drill bit based on screw size
        if self.config.wall_type in (WallType.DRYWALL, WallType.PLASTER):
            if self.config.mounting_system == MountingSystem.DIRECT_TO_STUD:
                tools.append("- 1/8\" pilot drill bit")
            elif self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
                if self.config.expected_load == LoadCategory.HEAVY:
                    tools.append("- 3/8\" drill bit (for toggle bolts)")
                else:
                    tools.append("- 1/4\" drill bit (for toggle bolts)")
            elif self.config.mounting_system == MountingSystem.FRENCH_CLEAT:
                tools.append("- 3/16\" pilot drill bit (for lag bolts)")
                tools.append("- Socket wrench or impact driver")

        # Drive bit
        tools.append("- #2 Phillips or square drive bit")

        return tools

    def _generate_procedure_steps(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> list[str]:
        """Generate step-by-step procedure based on mounting system."""
        # Handle masonry walls
        if self.config.wall_type in (WallType.CONCRETE, WallType.CMU, WallType.BRICK):
            return self._generate_masonry_steps(cabinet, plan)

        # Handle drywall/plaster by mounting system
        if self.config.mounting_system == MountingSystem.DIRECT_TO_STUD:
            return self._generate_direct_to_stud_steps(cabinet, plan)
        elif self.config.mounting_system == MountingSystem.FRENCH_CLEAT:
            return self._generate_french_cleat_steps(cabinet, plan)
        elif self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
            return self._generate_toggle_bolt_steps(cabinet, plan)
        elif self.config.mounting_system == MountingSystem.HANGING_RAIL:
            return self._generate_hanging_rail_steps(cabinet, plan)

        # Fallback
        return self._generate_direct_to_stud_steps(cabinet, plan)

    def _generate_direct_to_stud_steps(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> list[str]:
        """Generate steps for direct-to-stud mounting."""
        steps: list[str] = []
        stud_spacing = self.config.stud_spacing

        steps.append("### Step 1: Locate Wall Studs")
        steps.append("")
        steps.append(
            f"Use a stud finder to locate wall studs. Mark the center of each stud "
            f"within the cabinet mounting area. Studs are typically spaced "
            f"{stud_spacing:.0f}\" on center."
        )
        steps.append("")

        steps.append("### Step 2: Mark Cabinet Position")
        steps.append("")
        steps.append(
            "Draw a level horizontal line at the desired mounting height. This line "
            "indicates the bottom edge of the cabinet. Use a 48\" level or longer "
            "to ensure accuracy."
        )
        steps.append("")

        steps.append("### Step 3: Pre-drill Mounting Holes")
        steps.append("")
        steps.append(
            "Pre-drill pilot holes through the cabinet back panel at each stud "
            "location. Drill holes near the top and bottom of the cabinet back "
            "for secure mounting."
        )
        steps.append("")

        steps.append("### Step 4: Mount Cabinet")
        steps.append("")
        steps.append(
            "With a helper, lift the cabinet into position and align with your "
            "level line. Drive screws through the pre-drilled holes into the wall "
            "studs. Start with one screw, check level, then drive remaining screws."
        )
        steps.append("")

        steps.append("### Step 5: Verify and Adjust")
        steps.append("")
        steps.append(
            "Check the cabinet with a level in both directions. If needed, loosen "
            "screws slightly and insert shims behind the cabinet to achieve level. "
            "Retighten screws and verify level again."
        )
        steps.append("")

        return steps

    def _generate_french_cleat_steps(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> list[str]:
        """Generate steps for French cleat mounting."""
        steps: list[str] = []
        cleat_position = self.config.cleat_position_from_top

        steps.append("### Step 1: Locate Wall Studs")
        steps.append("")
        steps.append(
            "Use a stud finder to locate and mark wall studs within the cabinet "
            "mounting area. French cleat systems require secure attachment to "
            "wall studs for maximum strength."
        )
        steps.append("")

        steps.append("### Step 2: Install Wall Cleat")
        steps.append("")
        steps.append(
            f"Calculate the wall cleat height: cabinet bottom height plus cabinet "
            f"height minus {cleat_position:.0f}\" (cleat position from cabinet top). "
            f"Draw a level line at this height. Secure the wall cleat with the "
            f"bevel facing up and outward. Drive lag bolts through the cleat into "
            f"each wall stud."
        )
        steps.append("")

        steps.append("### Step 3: Install Cabinet Cleat")
        steps.append("")
        steps.append(
            f"Attach the cabinet cleat to the inside back of the cabinet, "
            f"{cleat_position:.0f}\" down from the top. The bevel should face "
            f"down and inward. Secure with wood screws spaced 6\" apart."
        )
        steps.append("")

        steps.append("### Step 4: Mount Cabinet")
        steps.append("")
        steps.append(
            "With a helper, lift the cabinet and hook the cabinet cleat over the "
            "wall cleat. The beveled edges should interlock, with the cabinet "
            "cleat resting on the wall cleat."
        )
        steps.append("")

        steps.append("### Step 5: Secure and Verify")
        steps.append("")
        steps.append(
            "Check the cabinet with a level. For additional security, you may "
            "drive screws through the bottom of the cabinet back into wall studs. "
            "This prevents the cabinet from being lifted off the cleat."
        )
        steps.append("")

        return steps

    def _generate_toggle_bolt_steps(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> list[str]:
        """Generate steps for toggle bolt mounting."""
        steps: list[str] = []

        if self.config.expected_load == LoadCategory.HEAVY:
            drill_size = '3/8"'
        else:
            drill_size = '1/4"'

        steps.append("### Step 1: Mark Mounting Positions")
        steps.append("")
        steps.append(
            "Hold the cabinet against the wall or use a template to mark the "
            "mounting hole positions. Space toggle bolts evenly across the width "
            "of the cabinet, with holes near all four corners and additional "
            "holes in the center if the cabinet is wide."
        )
        steps.append("")

        steps.append("### Step 2: Pre-drill Holes")
        steps.append("")
        steps.append(
            f"Drill {drill_size} holes through the drywall at each marked position. "
            f"The holes must be large enough for the folded toggle wings to pass "
            f"through. Also drill matching holes through the cabinet back panel."
        )
        steps.append("")

        steps.append("### Step 3: Insert Toggle Bolts")
        steps.append("")
        steps.append(
            "Thread the toggle bolt through the cabinet back from the inside. "
            "Then attach the toggle wings to the bolt threads. The wings should "
            "be positioned about 1/4\" from the bolt tip."
        )
        steps.append("")

        steps.append("### Step 4: Mount Cabinet")
        steps.append("")
        steps.append(
            "With a helper, hold the cabinet in position. Push each toggle bolt "
            "through the wall until the wings spring open on the other side. "
            "You will hear or feel a click when the wings deploy."
        )
        steps.append("")

        steps.append("### Step 5: Tighten and Verify")
        steps.append("")
        steps.append(
            "Pull back on each toggle bolt to seat the wings against the back of "
            "the drywall, then tighten the bolts. Check level and adjust as needed "
            "before fully tightening all bolts."
        )
        steps.append("")

        return steps

    def _generate_hanging_rail_steps(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> list[str]:
        """Generate steps for hanging rail mounting."""
        steps: list[str] = []

        steps.append("### Step 1: Locate Wall Studs")
        steps.append("")
        steps.append(
            "Use a stud finder to locate wall studs within the cabinet mounting "
            "area. The hanging rail must be secured into at least two wall studs "
            "for safe installation."
        )
        steps.append("")

        steps.append("### Step 2: Install Hanging Rail")
        steps.append("")
        steps.append(
            "Mark a level line at the mounting height for the rail. The rail "
            "typically mounts at the top of the cabinet location. Secure the "
            "rail to wall studs using cabinet screws. Verify the rail is level "
            "before fully tightening all screws."
        )
        steps.append("")

        steps.append("### Step 3: Attach Cabinet Brackets")
        steps.append("")
        steps.append(
            "Install the hanging brackets inside the cabinet near the top. "
            "These brackets hook over the wall rail. Position brackets according "
            "to the rail manufacturer's specifications."
        )
        steps.append("")

        steps.append("### Step 4: Hang Cabinet")
        steps.append("")
        steps.append(
            "With a helper, lift the cabinet and hook the brackets over the "
            "hanging rail. The cabinet should slide down and lock into position "
            "on the rail."
        )
        steps.append("")

        steps.append("### Step 5: Adjust and Secure")
        steps.append("")
        steps.append(
            "Most hanging rail systems allow for minor height and depth "
            "adjustments via the bracket mechanisms. Adjust until the cabinet "
            "is level and properly aligned. If required, drive additional screws "
            "through the cabinet back into studs for extra security."
        )
        steps.append("")

        return steps

    def _generate_masonry_steps(
        self, cabinet: "Cabinet", plan: InstallationPlan | None
    ) -> list[str]:
        """Generate steps for masonry wall mounting."""
        steps: list[str] = []
        wall_type = self.config.wall_type.value

        if self.config.expected_load == LoadCategory.HEAVY:
            drill_size = '3/16"'
            embedment = '2-1/4"'
        else:
            drill_size = '5/32"'
            embedment = '2"'

        steps.append("### Step 1: Mark Mounting Positions")
        steps.append("")
        steps.append(
            f"Hold the cabinet against the {wall_type} wall or use a template "
            f"to mark the mounting hole positions. For {wall_type}, space fasteners "
            f"evenly across the cabinet width. Avoid mortar joints in brick or CMU "
            f"walls; drill into the solid masonry units."
        )
        steps.append("")

        steps.append("### Step 2: Pre-drill Pilot Holes")
        steps.append("")
        steps.append(
            f"Using a hammer drill with a {drill_size} carbide masonry bit, drill "
            f"pilot holes at each marked position. Drill to a depth of at least "
            f"{embedment} (the Tapcon embedment depth). Clear dust from holes "
            f"using compressed air or a vacuum."
        )
        steps.append("")

        steps.append("### Step 3: Prepare Cabinet Back")
        steps.append("")
        steps.append(
            "Pre-drill clearance holes through the cabinet back panel at each "
            "mounting position. The holes should be slightly larger than the "
            "Tapcon screw diameter to allow for alignment."
        )
        steps.append("")

        steps.append("### Step 4: Mount Cabinet")
        steps.append("")
        steps.append(
            "With a helper, hold the cabinet in position against the wall. "
            "Drive Tapcon screws through the cabinet back into the pre-drilled "
            "holes. Start with opposite corner screws, check level, then "
            "drive remaining screws."
        )
        steps.append("")

        steps.append("### Step 5: Verify Installation")
        steps.append("")
        steps.append(
            "Check the cabinet with a level in both directions. Tapcon screws "
            "cannot be easily adjusted once set, so verify alignment is correct. "
            "If adjustment is needed, drill new holes at least 2\" from any "
            "existing holes."
        )
        steps.append("")

        return steps

    def _generate_safety_notes(
        self, plan: InstallationPlan | None
    ) -> list[str]:
        """Generate safety notes based on installation configuration."""
        notes: list[str] = []

        # Load capacity note
        if plan and plan.weight_estimate:
            total_load = plan.weight_estimate.total_estimated_load_lbs
            notes.append(
                f"- **Maximum Load Capacity:** This installation is designed for an "
                f"estimated maximum load of approximately {total_load:.0f} lbs. "
                f"Do not exceed this capacity."
            )
        else:
            load_per_foot = self.LOAD_RATINGS[self.config.expected_load]
            notes.append(
                f"- **Expected Load:** This installation is designed for a "
                f"{self.config.expected_load.value} load category "
                f"({load_per_foot:.0f} lbs per linear foot)."
            )

        # Always use a helper
        notes.append(
            "- **Always Use a Helper:** Cabinet mounting requires at least two "
            "people. Never attempt to lift and mount a cabinet alone."
        )

        # Eye protection for masonry
        if self.config.wall_type in (WallType.CONCRETE, WallType.CMU, WallType.BRICK):
            notes.append(
                "- **Eye and Ear Protection:** Wear safety glasses and hearing "
                "protection when drilling into masonry."
            )

        # Professional consultation
        notes.append(
            "- **Professional Consultation:** For critical installations or if "
            "uncertain about wall construction, consult a professional installer "
            "or structural engineer."
        )

        return notes
