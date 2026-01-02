"""Installation instruction generation service.

This module provides the InstructionGenerator class for generating
step-by-step installation instructions in markdown format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...value_objects import (
    LoadCategory,
    MountingSystem,
    WallType,
)
from .config import InstallationConfig
from .models import InstallationPlan

if TYPE_CHECKING:
    from ...entities import Cabinet


class InstructionGenerator:
    """Service for generating installation instructions in markdown format.

    Creates step-by-step installation instructions appropriate
    for the configured mounting system and wall type.
    """

    # Load ratings per linear foot based on load category
    LOAD_RATINGS: dict[LoadCategory, float] = {
        LoadCategory.LIGHT: 15.0,
        LoadCategory.MEDIUM: 30.0,
        LoadCategory.HEAVY: 50.0,
    }

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the instruction generator.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config

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
        lines.append(f'- **Width:** {cabinet.width:.1f}"')
        lines.append(f'- **Height:** {cabinet.height:.1f}"')
        lines.append(f'- **Depth:** {cabinet.depth:.1f}"')
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
        tools.append('- Level (48" minimum recommended)')
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
                tools.append('- 3/16" carbide masonry drill bit')
            else:
                tools.append('- 5/32" carbide masonry drill bit')

        # Pilot drill bit based on screw size
        if self.config.wall_type in (WallType.DRYWALL, WallType.PLASTER):
            if self.config.mounting_system == MountingSystem.DIRECT_TO_STUD:
                tools.append('- 1/8" pilot drill bit')
            elif self.config.mounting_system == MountingSystem.TOGGLE_BOLT:
                if self.config.expected_load == LoadCategory.HEAVY:
                    tools.append('- 3/8" drill bit (for toggle bolts)')
                else:
                    tools.append('- 1/4" drill bit (for toggle bolts)')
            elif self.config.mounting_system == MountingSystem.FRENCH_CLEAT:
                tools.append('- 3/16" pilot drill bit (for lag bolts)')
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
            f'{stud_spacing:.0f}" on center.'
        )
        steps.append("")

        steps.append("### Step 2: Mark Cabinet Position")
        steps.append("")
        steps.append(
            "Draw a level horizontal line at the desired mounting height. This line "
            'indicates the bottom edge of the cabinet. Use a 48" level or longer '
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
            f'height minus {cleat_position:.0f}" (cleat position from cabinet top). '
            f"Draw a level line at this height. Secure the wall cleat with the "
            f"bevel facing up and outward. Drive lag bolts through the cleat into "
            f"each wall stud."
        )
        steps.append("")

        steps.append("### Step 3: Install Cabinet Cleat")
        steps.append("")
        steps.append(
            f"Attach the cabinet cleat to the inside back of the cabinet, "
            f'{cleat_position:.0f}" down from the top. The bevel should face '
            f'down and inward. Secure with wood screws spaced 6" apart.'
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
            'be positioned about 1/4" from the bolt tip.'
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
            'If adjustment is needed, drill new holes at least 2" from any '
            "existing holes."
        )
        steps.append("")

        return steps

    def _generate_safety_notes(self, plan: InstallationPlan | None) -> list[str]:
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
