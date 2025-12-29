"""Assembly instruction generator for cabinet layouts.

Generates step-by-step markdown build instructions with proper build order,
joinery methods, and fastener/glue notes per step.

Build Order (FR-02.2):
1. carcase (side panels, top, bottom)
2. back panel
3. dividers
4. fixed shelves
5. adjustable shelves (preparation only)
6. doors
7. drawers
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from cabinets.domain.value_objects import CutPiece, JointType, PanelType
from cabinets.infrastructure.exporters.base import ExporterRegistry

if TYPE_CHECKING:
    from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput
    from cabinets.domain.services.woodworking import ConnectionJoinery


logger = logging.getLogger(__name__)


# Build phases in assembly order (FR-02.2)
BUILD_PHASES: list[tuple[str, str, list[PanelType]]] = [
    (
        "carcase_prep",
        "Prepare Case Panels",
        [PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE],
    ),
    (
        "horizontal",
        "Attach Horizontal Panels",
        [PanelType.TOP, PanelType.BOTTOM],
    ),
    ("dividers", "Install Dividers", [PanelType.DIVIDER, PanelType.HORIZONTAL_DIVIDER]),
    ("back", "Attach Back Panel", [PanelType.BACK]),
    ("fixed_shelves", "Install Fixed Shelves", [PanelType.SHELF]),
    ("adjustable_shelves", "Prepare Adjustable Shelves", []),
    ("doors", "Mount Doors", [PanelType.DOOR]),
    (
        "drawers",
        "Install Drawers",
        [
            PanelType.DRAWER_FRONT,
            PanelType.DRAWER_SIDE,
            PanelType.DRAWER_BOX_FRONT,
            PanelType.DRAWER_BOTTOM,
        ],
    ),
]


# Joinery instructions by type (FR-02.4)
JOINERY_INSTRUCTIONS: dict[str, str] = {
    "dado": "Cut dado groove {depth:.3f}\" deep x {width:.3f}\" wide at {position}",
    "rabbet": "Cut rabbet {depth:.3f}\" deep x {width:.3f}\" wide along edge",
    "butt": "Apply glue and use pocket screws or dowels for alignment",
    "biscuit": "Cut biscuit slots at marked positions and insert #20 biscuits",
    "pocket_hole": "Drill pocket holes at {spacing:.1f}\" spacing and secure with 1-1/4\" pocket screws",
    "pocket_screw": "Drill pocket holes at {spacing:.1f}\" spacing and secure with 1-1/4\" pocket screws",
    "dowel": "Drill dowel holes at {spacing:.1f}\" spacing and insert 5/16\" x 1-1/2\" fluted dowels",
}


# Fastener and glue notes per phase
PHASE_NOTES: dict[str, dict[str, str]] = {
    "carcase_prep": {
        "glue": "Do not apply glue during preparation - dry fit first",
        "fasteners": "No fasteners needed for preparation",
        "tips": "Mark 'inside' face of each panel before cutting joinery",
    },
    "horizontal": {
        "glue": "Apply thin, even coat of wood glue to all mating surfaces",
        "fasteners": "Use #8 x 1-1/4\" wood screws, pre-drill to prevent splitting",
        "tips": "Check for square using diagonal measurements",
        "clamp_time": "Clamp for minimum 30 minutes before proceeding",
    },
    "dividers": {
        "glue": "Apply glue to dado grooves before inserting dividers",
        "fasteners": "Optional: add pocket screws from underside for extra strength",
        "tips": "Ensure dividers are perfectly plumb using a level",
    },
    "back": {
        "glue": "Apply light bead of glue in rabbet before attaching back",
        "fasteners": "Use #6 x 5/8\" pan head screws at 6\" intervals around perimeter",
        "tips": "Back panel squares up the entire cabinet - measure diagonals",
    },
    "fixed_shelves": {
        "glue": "Apply glue to dado grooves for permanent shelf installation",
        "fasteners": "No additional fasteners needed for dado-mounted shelves",
        "tips": "Insert shelves before back panel for easier alignment",
    },
    "adjustable_shelves": {
        "glue": "No glue - shelves must remain removable",
        "fasteners": "Install 4 shelf pins per shelf (5mm shelf pins)",
        "tips": "Drill shelf pin holes using 32mm system for consistent spacing",
    },
    "doors": {
        "glue": "No glue required for door installation",
        "fasteners": "Use European cup hinges (35mm) - 2 per door under 40\", 3 for taller",
        "tips": "Install hinges on doors before mounting to cabinet",
    },
    "drawers": {
        "glue": "Apply glue to drawer box joints during assembly",
        "fasteners": "Use #6 x 1\" screws to attach drawer front to drawer box",
        "tips": "Install drawer slides before attaching drawer front for proper alignment",
    },
}


# Standard tools needed for cabinet assembly
TOOLS_LIST: list[str] = [
    "Table saw or track saw (for panel cutting)",
    "Router with dado and rabbet bits",
    "Pocket hole jig (e.g., Kreg) with appropriate bit",
    "Drill with countersink bit",
    "Square (combination square and framing square)",
    "Measuring tape and marking pencil",
    "Clamps (4+ bar clamps, 24-48\" recommended)",
    "Rubber mallet",
    "Level (24\" or longer)",
    "Safety glasses and hearing protection",
]


@ExporterRegistry.register("assembly")
class AssemblyInstructionGenerator:
    """Generates step-by-step assembly instructions in markdown format.

    This exporter creates detailed build instructions including:
    - Materials verification checklist
    - Tools needed list
    - Step-by-step assembly instructions following proper build order
    - Joinery method details per step
    - Fastener and glue recommendations

    Attributes:
        format_name: "assembly"
        file_extension: "md"
    """

    format_name: ClassVar[str] = "assembly"
    file_extension: ClassVar[str] = "md"

    def __init__(
        self,
        include_timestamps: bool = True,
        include_warnings: bool = True,
    ) -> None:
        """Initialize the assembly instruction generator.

        Args:
            include_timestamps: Whether to include generation timestamp in header.
            include_warnings: Whether to include safety warnings section.
        """
        self.include_timestamps = include_timestamps
        self.include_warnings = include_warnings

    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export assembly instructions to markdown file.

        Args:
            output: The layout output to generate instructions for.
            path: Path where the markdown file will be saved.
        """
        content = self.export_string(output)
        path.write_text(content)
        logger.info(f"Exported assembly instructions to {path}")

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Generate markdown assembly instructions.

        Args:
            output: The layout output to generate instructions for.

        Returns:
            Complete markdown-formatted assembly instructions.
        """
        # Import here to avoid circular imports at module level
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        lines: list[str] = []
        lines.extend(self._header(output))
        lines.extend(self._materials_checklist(output))
        lines.extend(self._tools_needed())

        if self.include_warnings:
            lines.extend(self._safety_warnings())

        lines.extend(self._generate_steps(output))
        lines.extend(self._finishing_notes())

        return "\n".join(lines)

    def _header(self, output: LayoutOutput | RoomLayoutOutput) -> list[str]:
        """Generate document header.

        Args:
            output: Layout output for dimension information.

        Returns:
            List of header lines.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        lines: list[str] = []

        # Determine cabinet dimensions
        if isinstance(output, RoomLayoutOutput):
            if output.cabinets:
                cabinet = output.cabinets[0]
                title = f'Assembly Instructions: {cabinet.width:.0f}"W x {cabinet.height:.0f}"H Room Cabinet System'
            else:
                title = "Assembly Instructions: Room Cabinet System"
        elif isinstance(output, LayoutOutput):
            cabinet = output.cabinet
            title = f'Assembly Instructions: {cabinet.width:.0f}"W x {cabinet.height:.0f}"H x {cabinet.depth:.0f}"D Cabinet'
        else:
            title = "Assembly Instructions"

        lines.append(f"# {title}")
        lines.append("")

        if self.include_timestamps:
            lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
            lines.append("")

        return lines

    def _materials_checklist(self, output: LayoutOutput | RoomLayoutOutput) -> list[str]:
        """Generate materials verification checklist.

        Args:
            output: Layout output for cut list and hardware information.

        Returns:
            List of checklist lines.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        lines: list[str] = []
        lines.append("## Materials Checklist")
        lines.append("")
        lines.append("Verify all materials are ready before beginning assembly:")
        lines.append("")

        # Cut pieces checklist
        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
            hardware = []  # RoomLayoutOutput doesn't have hardware directly
        elif isinstance(output, LayoutOutput):
            cut_list = output.cut_list
            hardware = output.hardware
        else:
            cut_list = []
            hardware = []

        lines.append("### Cut Pieces")
        lines.append("")
        if cut_list:
            for piece in cut_list:
                lines.append(
                    f"- [ ] {piece.label} ({piece.quantity}x): "
                    f'{piece.width:.3f}" x {piece.height:.3f}" '
                    f"({piece.material.material_type.value})"
                )
        else:
            lines.append("- [ ] All cut pieces verified against cut list")
        lines.append("")

        # Hardware checklist
        lines.append("### Hardware")
        lines.append("")
        if hardware:
            for item in hardware:
                note = f" - {item.notes}" if item.notes else ""
                lines.append(f"- [ ] {item.name} (qty: {item.quantity}){note}")
        else:
            lines.append("- [ ] Wood screws (assorted sizes)")
            lines.append("- [ ] Pocket hole screws (1-1/4\")")
            lines.append("- [ ] Shelf pins (5mm)")
            lines.append("- [ ] Back panel screws (#6 x 5/8\")")
        lines.append("")

        # Consumables
        lines.append("### Consumables")
        lines.append("")
        lines.append("- [ ] Wood glue (PVA or aliphatic resin)")
        lines.append("- [ ] Clean rags for glue cleanup")
        lines.append("- [ ] Sandpaper (120, 180, 220 grit)")
        lines.append("")

        return lines

    def _tools_needed(self) -> list[str]:
        """Generate tools needed section.

        Returns:
            List of tool requirement lines.
        """
        lines: list[str] = []
        lines.append("## Tools Needed")
        lines.append("")

        for tool in TOOLS_LIST:
            lines.append(f"- {tool}")
        lines.append("")

        return lines

    def _safety_warnings(self) -> list[str]:
        """Generate safety warnings section.

        Returns:
            List of safety warning lines.
        """
        lines: list[str] = []
        lines.append("## Safety Warnings")
        lines.append("")
        lines.append("> **Important:** Always wear appropriate safety equipment:")
        lines.append("> - Safety glasses when using power tools or drilling")
        lines.append("> - Hearing protection when using power tools")
        lines.append("> - Dust mask when sanding or routing")
        lines.append("> - Work gloves when handling large panels")
        lines.append("")

        return lines

    def _generate_steps(self, output: LayoutOutput | RoomLayoutOutput) -> list[str]:
        """Generate step-by-step assembly instructions.

        Args:
            output: Layout output for cut list and joinery information.

        Returns:
            List of instruction step lines.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        lines: list[str] = []
        lines.append("## Assembly Steps")
        lines.append("")

        # Get cut list
        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
            cabinet = output.cabinets[0] if output.cabinets else None
        elif isinstance(output, LayoutOutput):
            cut_list = output.cut_list
            cabinet = output.cabinet
        else:
            cut_list = []
            cabinet = None

        # Group pieces by build phase
        pieces_by_phase = self._group_pieces_by_phase(cut_list)

        # Get joinery information if available
        joinery_list: list[ConnectionJoinery] = []
        if cabinet:
            try:
                from cabinets.domain.services.woodworking import WoodworkingIntelligence

                intel = WoodworkingIntelligence()
                joinery_list = intel.get_joinery(cabinet)
            except Exception as e:
                logger.debug(f"Could not get joinery information: {e}")

        step_number = 1

        for phase_id, phase_name, phase_panel_types in BUILD_PHASES:
            phase_pieces = pieces_by_phase.get(phase_id, [])

            # Skip phases with no pieces (except adjustable_shelves which is always included)
            if not phase_pieces and phase_id != "adjustable_shelves":
                continue

            lines.append(f"### Step {step_number}: {phase_name}")
            lines.append("")

            # List pieces for this phase
            if phase_pieces:
                lines.append("**Pieces:**")
                for piece in phase_pieces:
                    lines.append(f"- {piece.label} ({piece.quantity}x)")
                lines.append("")

            # Add joinery instructions for this phase
            phase_joinery = self._get_joinery_for_phase(joinery_list, phase_panel_types)
            if phase_joinery:
                lines.append("**Joinery:**")
                for joint in phase_joinery:
                    instruction = self._format_joinery_step(joint)
                    if instruction:
                        lines.append(f"- {instruction}")
                lines.append("")

            # Add phase-specific instructions
            lines.extend(self._get_phase_instructions(phase_id, phase_pieces))

            # Add notes (FR-02.5)
            phase_notes = PHASE_NOTES.get(phase_id, {})
            if phase_notes:
                lines.append("**Notes:**")
                if "glue" in phase_notes:
                    lines.append(f"- *Glue:* {phase_notes['glue']}")
                if "fasteners" in phase_notes:
                    lines.append(f"- *Fasteners:* {phase_notes['fasteners']}")
                if "tips" in phase_notes:
                    lines.append(f"- *Tips:* {phase_notes['tips']}")
                if "clamp_time" in phase_notes:
                    lines.append(f"- *Clamping:* {phase_notes['clamp_time']}")
                lines.append("")

            lines.append("---")
            lines.append("")
            step_number += 1

        return lines

    def _group_pieces_by_phase(
        self, cut_list: list[CutPiece]
    ) -> dict[str, list[CutPiece]]:
        """Group cut pieces by their build phase.

        Args:
            cut_list: List of cut pieces from the layout output.

        Returns:
            Dictionary mapping phase IDs to lists of cut pieces.
        """
        # Create mapping of panel type to phase
        panel_to_phase: dict[PanelType, str] = {}
        for phase_id, _phase_name, panel_types in BUILD_PHASES:
            for panel_type in panel_types:
                panel_to_phase[panel_type] = phase_id

        # Group pieces
        groups: dict[str, list[CutPiece]] = {}
        for piece in cut_list:
            phase_id = panel_to_phase.get(piece.panel_type, "other")
            if phase_id not in groups:
                groups[phase_id] = []
            groups[phase_id].append(piece)

        return groups

    def _get_joinery_for_phase(
        self,
        joinery_list: list[ConnectionJoinery],
        panel_types: list[PanelType],
    ) -> list[ConnectionJoinery]:
        """Get joinery connections relevant to a build phase.

        Args:
            joinery_list: Full list of joinery connections.
            panel_types: Panel types included in this phase.

        Returns:
            Filtered list of joinery connections for this phase.
        """
        if not joinery_list or not panel_types:
            return []

        return [
            joint
            for joint in joinery_list
            if joint.to_panel in panel_types or joint.from_panel in panel_types
        ]

    def _format_joinery_step(self, joinery: ConnectionJoinery) -> str:
        """Format a joinery connection as an instruction.

        Args:
            joinery: ConnectionJoinery object describing the joint.

        Returns:
            Human-readable instruction string.
        """
        joint = joinery.joint
        joint_type = joint.joint_type.value

        # Get instruction template
        template = JOINERY_INSTRUCTIONS.get(joint_type, "")
        if not template:
            return f"{joint_type.replace('_', ' ').title()} joint: {joinery.location_description}"

        # Format with available values
        format_values = {
            "depth": joint.depth or 0.25,
            "width": joint.width or 0.75,
            "position": joinery.location_description or "as marked",
            "spacing": joint.spacing or 8.0,
        }

        try:
            instruction = template.format(**format_values)
        except KeyError:
            instruction = f"{joint_type.replace('_', ' ').title()} joint"

        # Add from/to panel context
        from_panel = joinery.from_panel.value.replace("_", " ").title()
        to_panel = joinery.to_panel.value.replace("_", " ").title()

        return f"{from_panel} to {to_panel}: {instruction}"

    def _get_phase_instructions(
        self, phase_id: str, pieces: list[CutPiece]
    ) -> list[str]:
        """Get detailed instructions for a specific phase.

        Args:
            phase_id: Identifier of the build phase.
            pieces: Cut pieces involved in this phase.

        Returns:
            List of instruction lines.
        """
        lines: list[str] = []

        if phase_id == "carcase_prep":
            lines.append("**Instructions:**")
            lines.append("1. Lay out side panels with inside faces up")
            lines.append("2. Mark dado positions for top, bottom, and fixed shelf locations")
            lines.append("3. Cut all dados using router with straight bit or table saw with dado blade")
            lines.append("4. Test fit top and bottom panels in dados - should be snug but not forced")
            lines.append("")

        elif phase_id == "horizontal":
            lines.append("**Instructions:**")
            lines.append("1. Apply glue to all dado grooves in side panels")
            lines.append("2. Insert bottom panel into dados in both side panels")
            lines.append("3. Insert top panel into dados in both side panels")
            lines.append("4. Square the assembly using clamps and diagonal measurements")
            lines.append("5. Pre-drill and drive screws through sides into top and bottom")
            lines.append("")

        elif phase_id == "dividers":
            if pieces:
                lines.append("**Instructions:**")
                lines.append("1. Apply glue to vertical dado grooves in top and bottom panels")
                lines.append("2. Slide dividers into place from the front")
                lines.append("3. Ensure dividers are plumb using a level")
                lines.append("4. Wipe away excess glue with damp rag")
                lines.append("")

        elif phase_id == "back":
            lines.append("**Instructions:**")
            lines.append("1. Verify cabinet is square by measuring diagonals")
            lines.append("2. Apply thin bead of glue in rabbet around perimeter")
            lines.append("3. Position back panel in rabbet")
            lines.append("4. Drive screws around perimeter at 6\" intervals")
            lines.append("5. Add screws along dividers if present")
            lines.append("")

        elif phase_id == "fixed_shelves":
            if pieces:
                lines.append("**Instructions:**")
                lines.append("1. Apply glue to shelf dados in side panels")
                lines.append("2. Slide shelves into position from front")
                lines.append("3. Verify shelves are level")
                lines.append("4. Wipe away excess glue")
                lines.append("")

        elif phase_id == "adjustable_shelves":
            lines.append("**Instructions:**")
            lines.append("1. Mark shelf pin hole locations using 32mm system template")
            lines.append("2. Drill shelf pin holes using 5mm bit with depth stop")
            lines.append("3. Vacuum out holes to remove debris")
            lines.append("4. Insert shelf pins at desired heights")
            lines.append("5. Place adjustable shelves on pins")
            lines.append("")

        elif phase_id == "doors":
            if pieces:
                lines.append("**Instructions:**")
                lines.append("1. Mark hinge cup locations on doors (typically 3\" from top and bottom)")
                lines.append("2. Drill 35mm hinge cup holes using Forstner bit")
                lines.append("3. Install hinge cups in doors")
                lines.append("4. Mark mounting plate positions on cabinet sides")
                lines.append("5. Install mounting plates")
                lines.append("6. Attach doors and adjust for proper alignment")
                lines.append("")

        elif phase_id == "drawers":
            if pieces:
                lines.append("**Instructions:**")
                lines.append("1. Assemble drawer boxes with glue and fasteners")
                lines.append("2. Install drawer slides on cabinet (follow manufacturer spacing)")
                lines.append("3. Attach slide members to drawer boxes")
                lines.append("4. Insert drawers and test operation")
                lines.append("5. Attach drawer fronts with proper reveals")
                lines.append("")

        return lines

    def _finishing_notes(self) -> list[str]:
        """Generate finishing notes section.

        Returns:
            List of finishing notes lines.
        """
        lines: list[str] = []
        lines.append("## Finishing")
        lines.append("")
        lines.append("After assembly is complete:")
        lines.append("")
        lines.append("1. **Inspect all joints** - Check for gaps, squeeze-out, or loose fits")
        lines.append("2. **Sand all surfaces** - Progress through 120, 180, 220 grit")
        lines.append("3. **Fill any holes** - Use wood filler matching final finish")
        lines.append("4. **Remove dust** - Vacuum and wipe with tack cloth")
        lines.append("5. **Apply finish** - Follow manufacturer instructions for chosen finish")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Assembly instructions generated by Cabinet Layout Generator*")
        lines.append("")

        return lines


# Export for backwards compatibility
__all__ = [
    "AssemblyInstructionGenerator",
    "BUILD_PHASES",
    "JOINERY_INSTRUCTIONS",
    "PHASE_NOTES",
]
