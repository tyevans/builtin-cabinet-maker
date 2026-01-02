"""Output formatters and exporters for cabinet layouts."""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Any

from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput
from cabinets.domain import Cabinet, CutPiece, MaterialEstimate, MaterialSpec
from cabinets.domain.entities import Room

if TYPE_CHECKING:
    from cabinets.domain.services.safety import (
        SafetyAssessment,
        SafetyCheckResult,
    )
    from cabinets.domain.services.woodworking import HardwareList


class CutListFormatter:
    """Formats cut lists for display.

    Supports optional decorative metadata display in a Notes column.
    When any piece has decorative metadata (arch, scallop, edge profile,
    joinery, or zone), the formatter uses an extended format with Notes.
    """

    def __init__(self, include_decorative: bool = True) -> None:
        """Initialize formatter.

        Args:
            include_decorative: Whether to include decorative notes column.
        """
        self._include_decorative = include_decorative

    def format(self, cut_list: list[CutPiece]) -> str:
        """Format cut list as a table.

        If decorative metadata is present on any piece, includes a Notes
        column with decorative specifications.
        """
        if not cut_list:
            return "No pieces in cut list."

        # Check if any pieces have decorative metadata
        has_decorative = self._include_decorative and any(
            self._get_decorative_notes(piece) for piece in cut_list
        )

        if has_decorative:
            return self._format_with_notes(cut_list)
        else:
            return self._format_simple(cut_list)

    def _format_simple(self, cut_list: list[CutPiece]) -> str:
        """Format cut list without notes column."""
        lines = [
            "CUT LIST",
            "=" * 70,
            f"{'Piece':<20} {'Width':<10} {'Height':<10} {'Qty':<6} {'Area (sq in)'}",
            "-" * 70,
        ]

        total_area = 0.0
        for piece in cut_list:
            lines.append(
                f"{piece.label:<20} {piece.width:<10.3f} {piece.height:<10.3f} "
                f"{piece.quantity:<6} {piece.area:.1f}"
            )
            total_area += piece.area

        lines.append("-" * 70)
        lines.append(f"{'TOTAL':<20} {'':<10} {'':<10} {'':<6} {total_area:.1f}")
        lines.append(f"{'':>50} ({total_area / 144:.2f} sq ft)")

        return "\n".join(lines)

    def _format_with_notes(self, cut_list: list[CutPiece]) -> str:
        """Format cut list with decorative notes column."""
        lines = [
            "CUT LIST",
            "=" * 100,
            f"{'Piece':<20} {'Width':<8} {'Height':<8} {'Qty':<4} {'Area':<10} {'Notes'}",
            "-" * 100,
        ]

        total_area = 0.0
        for piece in cut_list:
            notes = self._get_decorative_notes(piece)
            lines.append(
                f"{piece.label:<20} {piece.width:<8.3f} {piece.height:<8.3f} "
                f"{piece.quantity:<4} {piece.area:<10.1f} {notes}"
            )
            total_area += piece.area

        lines.append("-" * 100)
        lines.append(f"{'TOTAL':<20} {'':<8} {'':<8} {'':<4} {total_area:<10.1f}")
        lines.append(f"{'':>50} ({total_area / 144:.2f} sq ft)")

        return "\n".join(lines)

    def _get_decorative_notes(self, piece: CutPiece) -> str:
        """Extract decorative notes from piece metadata.

        Args:
            piece: Cut piece with potential decorative metadata.

        Returns:
            Formatted notes string, or empty string if no metadata.
        """
        if not piece.cut_metadata:
            return ""

        notes_parts: list[str] = []

        # Grain direction
        if "grain_direction" in piece.cut_metadata:
            grain = piece.cut_metadata.get("grain_direction", "none")
            if grain != "none":
                notes_parts.append(f"Grain: {grain}")

        # Arch metadata
        if "arch_type" in piece.cut_metadata:
            arch_type = piece.cut_metadata.get("arch_type", "")
            radius = piece.cut_metadata.get("radius", 0)
            spring_height = piece.cut_metadata.get("spring_height", 0)
            notes_parts.append(
                f'Arch: {arch_type}, R={radius:.1f}", spring={spring_height:.1f}"'
            )

        # Scallop metadata
        if "scallop_depth" in piece.cut_metadata:
            count = piece.cut_metadata.get("scallop_count", 0)
            width = piece.cut_metadata.get("scallop_width", 0)
            depth = piece.cut_metadata.get("scallop_depth", 0)
            notes_parts.append(f'Scallop: {count}x {width:.2f}" x {depth:.2f}"')

        # Edge profile metadata
        if "edge_profile" in piece.cut_metadata:
            profile = piece.cut_metadata["edge_profile"]
            profile_type = profile.get("profile_type", "")
            size = profile.get("size", 0)
            edges = profile.get("edges", [])
            edges_str = ", ".join(edges) if edges else "auto"
            notes_parts.append(f'Profile: {profile_type} {size:.2f}" ({edges_str})')

        # Joinery notes
        if "joinery_type" in piece.cut_metadata:
            joinery = piece.cut_metadata.get("joinery_type", "")
            notes_parts.append(f"Joinery: {joinery}")

        # Zone type
        if "zone_type" in piece.cut_metadata:
            zone = piece.cut_metadata.get("zone_type", "")
            notes_parts.append(f"Zone: {zone}")

        # Cutouts (infrastructure integration)
        if "cutouts" in piece.cut_metadata:
            cutouts = piece.cut_metadata.get("cutouts", [])
            for cutout in cutouts:
                cutout_type = cutout.get("type", "cutout")
                shape = cutout.get("shape", "")
                x = cutout.get("x", 0)
                y = cutout.get("y", 0)

                # Format display name (capitalize first letter)
                display_name = cutout_type.replace("_", " ").title()

                if shape == "circular":
                    diameter = cutout.get("diameter", 0)
                    notes_parts.append(f'{display_name}: {x}", {y}" - {diameter}" dia')
                elif shape == "rectangular":
                    width = cutout.get("width", 0)
                    height = cutout.get("height", 0)
                    # Check for pattern (e.g., ventilation grids)
                    pattern = cutout.get("pattern")
                    if pattern:
                        notes_parts.append(
                            f'{display_name} ({pattern}): {x}", {y}" - {width}" x {height}"'
                        )
                    else:
                        notes_parts.append(
                            f'{display_name}: {x}", {y}" - {width}" x {height}"'
                        )

        return "; ".join(notes_parts)


class LayoutDiagramFormatter:
    """Formats ASCII diagrams of cabinet layouts."""

    def format(self, cabinet: Cabinet, width: int = 60, height: int = 20) -> str:
        """Generate an ASCII diagram of the cabinet."""
        if cabinet is None:
            return "No cabinet to display."

        lines = [
            "CABINET LAYOUT DIAGRAM",
            "=" * width,
            "",
        ]

        # Create grid
        grid = [[" " for _ in range(width)] for _ in range(height)]

        # Draw outer box
        self._draw_box(grid, 0, 0, width - 1, height - 1)

        # Draw sections and shelves
        num_sections = len(cabinet.sections)
        if num_sections > 0:
            section_display_width = (width - 4) // num_sections

            for i, section in enumerate(cabinet.sections):
                section_x = 2 + i * section_display_width

                # Draw section divider (except for last section)
                if i < num_sections - 1:
                    divider_x = section_x + section_display_width
                    for y in range(1, height - 1):
                        if divider_x < width - 1:
                            grid[y][divider_x] = "|"

                # Draw shelves in this section
                num_shelves = len(section.shelves)
                if num_shelves > 0:
                    shelf_spacing = (height - 4) // (num_shelves + 1)
                    for j in range(num_shelves):
                        shelf_y = height - 2 - shelf_spacing * (j + 1)
                        if 1 < shelf_y < height - 1:
                            for x in range(
                                section_x, section_x + section_display_width - 1
                            ):
                                if x < width - 1:
                                    grid[shelf_y][x] = "-"

        # Convert grid to string
        for row in grid:
            lines.append("".join(row))

        # Add dimensions
        lines.append("")
        lines.append(
            f'Dimensions: {cabinet.width}" W x {cabinet.height}" H x {cabinet.depth}" D'
        )
        lines.append(f"Sections: {len(cabinet.sections)}")
        total_shelves = sum(len(s.shelves) for s in cabinet.sections)
        lines.append(f"Total shelves: {total_shelves}")

        return "\n".join(lines)

    def _draw_box(
        self, grid: list[list[str]], x1: int, y1: int, x2: int, y2: int
    ) -> None:
        """Draw a box on the grid."""
        # Corners
        grid[y1][x1] = "+"
        grid[y1][x2] = "+"
        grid[y2][x1] = "+"
        grid[y2][x2] = "+"

        # Horizontal lines
        for x in range(x1 + 1, x2):
            grid[y1][x] = "-"
            grid[y2][x] = "-"

        # Vertical lines
        for y in range(y1 + 1, y2):
            grid[y][x1] = "|"
            grid[y][x2] = "|"


class MaterialReportFormatter:
    """Formats material estimate reports."""

    def format(
        self,
        estimates: dict[MaterialSpec, MaterialEstimate],
        total: MaterialEstimate,
    ) -> str:
        """Format material estimates as a report."""
        lines = [
            "MATERIAL ESTIMATE",
            "=" * 60,
            "",
        ]

        for material, estimate in estimates.items():
            lines.append(
                f'{material.material_type.value.title()} ({material.thickness}" thick)'
            )
            lines.append(f"  Area needed: {estimate.total_area_sqft:.2f} sq ft")
            lines.append(
                f"  4x8 sheets:  {estimate.sheet_count_4x8} (with {estimate.waste_percentage:.0%} waste)"
            )
            lines.append("")

        lines.append("-" * 60)
        lines.append("TOTAL (all materials)")
        lines.append(f"  Area: {total.total_area_sqft:.2f} sq ft")
        lines.append(f"  4x8 sheets: {total.sheet_count_4x8}")
        lines.append(f"  (Includes {total.waste_percentage:.0%} waste factor)")

        return "\n".join(lines)


class JsonExporter:
    """Exports layout data as JSON.

    Includes decorative metadata for pieces when present, providing
    detailed specifications for arch, scallop, edge profile, joinery,
    and molding zone configurations.
    """

    def export(self, output: LayoutOutput) -> str:
        """Export layout output as JSON string."""
        if not output.is_valid:
            return json.dumps({"errors": output.errors}, indent=2)

        data = {
            "cabinet": {
                "width": output.cabinet.width,
                "height": output.cabinet.height,
                "depth": output.cabinet.depth,
                "material_thickness": output.cabinet.material.thickness,
                "sections": len(output.cabinet.sections),
                "total_shelves": sum(len(s.shelves) for s in output.cabinet.sections),
            },
            "cut_list": [self._format_cut_piece(p) for p in output.cut_list],
            "material_estimate": {
                "total_area_sqft": output.total_estimate.total_area_sqft,
                "sheet_count_4x8": output.total_estimate.sheet_count_4x8,
                "waste_percentage": output.total_estimate.waste_percentage,
            },
        }
        return json.dumps(data, indent=2)

    def _format_cut_piece(self, piece: CutPiece) -> dict[str, Any]:
        """Format a single cut piece for JSON output.

        Args:
            piece: Cut piece to format.

        Returns:
            Dictionary with piece data and optional decorative metadata.
        """
        result: dict[str, Any] = {
            "label": piece.label,
            "width": piece.width,
            "height": piece.height,
            "quantity": piece.quantity,
            "panel_type": piece.panel_type.value,
            "material_thickness": piece.material.thickness,
        }

        # Include decorative metadata if present
        if piece.cut_metadata:
            decorative: dict[str, Any] = {}

            # Grain direction
            if "grain_direction" in piece.cut_metadata:
                grain = piece.cut_metadata.get("grain_direction")
                if grain and grain != "none":
                    decorative["grain_direction"] = grain

            # Arch metadata
            if "arch_type" in piece.cut_metadata:
                decorative["arch"] = {
                    "type": piece.cut_metadata.get("arch_type"),
                    "radius": piece.cut_metadata.get("radius"),
                    "spring_height": piece.cut_metadata.get("spring_height"),
                }

            # Scallop metadata
            if "scallop_depth" in piece.cut_metadata:
                decorative["scallop"] = {
                    "depth": piece.cut_metadata.get("scallop_depth"),
                    "width": piece.cut_metadata.get("scallop_width"),
                    "count": piece.cut_metadata.get("scallop_count"),
                    "template_info": piece.cut_metadata.get("template_info"),
                }

            # Edge profile metadata
            if "edge_profile" in piece.cut_metadata:
                decorative["edge_profile"] = piece.cut_metadata["edge_profile"]

            # Joinery metadata
            if "joinery_type" in piece.cut_metadata:
                decorative["joinery"] = {
                    "type": piece.cut_metadata.get("joinery_type"),
                }

            # Zone metadata
            if "zone_type" in piece.cut_metadata:
                decorative["zone"] = {
                    "type": piece.cut_metadata.get("zone_type"),
                    "setback": piece.cut_metadata.get("setback"),
                }

            if decorative:
                result["decorative_metadata"] = decorative

            # Cutouts (infrastructure integration) - added to result directly, not decorative
            if "cutouts" in piece.cut_metadata:
                cutouts_raw = piece.cut_metadata.get("cutouts", [])
                formatted_cutouts: list[dict[str, Any]] = []

                for cutout in cutouts_raw:
                    cutout_type = cutout.get("type", "cutout")
                    shape = cutout.get("shape", "")
                    x = cutout.get("x", 0)
                    y = cutout.get("y", 0)

                    formatted_cutout: dict[str, Any] = {
                        "type": cutout_type,
                        "position": {"x": x, "y": y},
                        "shape": shape,
                    }

                    if shape == "circular":
                        formatted_cutout["diameter"] = cutout.get("diameter", 0)
                    elif shape == "rectangular":
                        formatted_cutout["dimensions"] = {
                            "width": cutout.get("width", 0),
                            "height": cutout.get("height", 0),
                        }
                        # Include pattern if present (e.g., for vents)
                        pattern = cutout.get("pattern")
                        if pattern:
                            formatted_cutout["pattern"] = pattern

                    formatted_cutouts.append(formatted_cutout)

                if formatted_cutouts:
                    result["cutouts"] = formatted_cutouts

        return result


class RoomLayoutDiagramFormatter:
    """Formats ASCII diagrams of room layouts with multiple wall segments.

    Renders L-shaped and multi-wall room layouts as ASCII diagrams,
    showing cabinet sections positioned along each wall with proper
    angles between walls.
    """

    def __init__(self, chars_per_inch: float = 0.5, min_wall_chars: int = 10) -> None:
        """Initialize the formatter.

        Args:
            chars_per_inch: Scale factor for converting inches to ASCII characters.
            min_wall_chars: Minimum character width for wall representation.
        """
        self.chars_per_inch = chars_per_inch
        self.min_wall_chars = min_wall_chars

    def format(self, room_output: RoomLayoutOutput, cabinet_height: int = 5) -> str:
        """Generate an ASCII diagram of the room layout.

        Args:
            room_output: The room layout output containing room and cabinets.
            cabinet_height: Height in ASCII rows for cabinet rendering.

        Returns:
            ASCII string representation of the room layout.
        """
        if not room_output.is_valid:
            return f"Invalid room layout: {', '.join(room_output.errors)}"

        room = room_output.room
        cabinets = room_output.cabinets
        wall_positions = room.get_wall_positions()

        lines = [
            "ROOM LAYOUT DIAGRAM",
            "=" * 60,
            f"Room: {room.name}",
            "",
        ]

        # Determine the layout type based on wall angles
        is_l_shaped = len(wall_positions) == 2 and len(room.walls) == 2
        if is_l_shaped and room.walls[1].angle in (90, -90):
            # Render L-shaped layout
            lines.extend(self._render_l_shaped(room, cabinets, cabinet_height))
        else:
            # Render each wall separately for other layouts
            lines.extend(self._render_sequential_walls(room, cabinets, cabinet_height))

        # Add summary
        lines.append("")
        lines.append("-" * 60)
        lines.append(f"Total walls: {len(room.walls)}")
        lines.append(f"Total cabinets: {len(cabinets)}")
        total_shelves = sum(
            sum(len(s.shelves) for s in cab.sections) for cab in cabinets
        )
        lines.append(f"Total shelves: {total_shelves}")

        return "\n".join(lines)

    def _render_l_shaped(
        self,
        room: Room,
        cabinets: list[Cabinet],
        cabinet_height: int,
    ) -> list[str]:
        """Render an L-shaped room layout.

        For 90-degree corners, renders the first wall horizontally
        and the second wall vertically connected at the corner.

        Args:
            room: The Room entity.
            cabinets: List of cabinets, one per wall.
            cabinet_height: Height in ASCII rows for cabinet rendering.

        Returns:
            List of ASCII lines representing the L-shaped layout.
        """
        lines: list[str] = []
        wall1 = room.walls[0]
        wall2 = room.walls[1]

        # Calculate character widths for each wall
        wall1_chars = max(self.min_wall_chars, int(wall1.length * self.chars_per_inch))
        wall2_chars = max(self.min_wall_chars, int(wall2.length * self.chars_per_inch))

        # Determine if it's a right turn (90) or left turn (-90)
        is_right_turn = wall2.angle == 90

        # Render Wall 1 (horizontal)
        lines.append(f'Wall 1 ({wall1.length}")')

        # Get cabinet for wall 1 (if exists)
        cab1 = cabinets[0] if len(cabinets) > 0 else None
        wall1_box = self._render_cabinet_box(cab1, wall1_chars, cabinet_height)
        lines.extend(wall1_box)

        # Render corner connector and Wall 2
        # The indentation depends on corner direction
        if is_right_turn:
            # Right turn: Wall 2 goes down-right
            indent = " " * (wall1_chars - 1)
            lines.append(f"{indent}|")
            lines.append(f'{indent}| Wall 2 ({wall2.length}")')

            # Get cabinet for wall 2 (if exists)
            cab2 = cabinets[1] if len(cabinets) > 1 else None
            wall2_box = self._render_cabinet_box(cab2, wall2_chars, cabinet_height)
            for line in wall2_box:
                lines.append(f"{indent}{line}")
        else:
            # Left turn: Wall 2 goes down-left
            lines.append("|")
            lines.append(f'| Wall 2 ({wall2.length}")')

            cab2 = cabinets[1] if len(cabinets) > 1 else None
            wall2_box = self._render_cabinet_box(cab2, wall2_chars, cabinet_height)
            lines.extend(wall2_box)

        return lines

    def _render_sequential_walls(
        self,
        room: Room,
        cabinets: list[Cabinet],
        cabinet_height: int,
    ) -> list[str]:
        """Render walls sequentially for non-L-shaped layouts.

        Each wall is rendered as a separate section with its cabinet.

        Args:
            room: The Room entity.
            cabinets: List of cabinets, one per wall.
            cabinet_height: Height in ASCII rows for cabinet rendering.

        Returns:
            List of ASCII lines representing the walls sequentially.
        """
        lines: list[str] = []

        for i, wall in enumerate(room.walls):
            if i > 0:
                lines.append("")
                # Show angle if not continuing straight
                if wall.angle != 0:
                    angle_desc = "right" if wall.angle > 0 else "left"
                    lines.append(f"  ({abs(wall.angle)} degree {angle_desc} turn)")
                lines.append("")

            wall_chars = max(
                self.min_wall_chars, int(wall.length * self.chars_per_inch)
            )

            # Wall header
            wall_name = wall.name or f"Wall {i + 1}"
            lines.append(f'{wall_name} ({wall.length}")')

            # Get cabinet for this wall (if exists)
            cabinet = cabinets[i] if i < len(cabinets) else None
            wall_box = self._render_cabinet_box(cabinet, wall_chars, cabinet_height)
            lines.extend(wall_box)

        return lines

    def _render_cabinet_box(
        self, cabinet: Cabinet | None, width: int, height: int
    ) -> list[str]:
        """Render a single cabinet as an ASCII box with sections.

        Args:
            cabinet: The cabinet to render, or None for empty wall.
            width: Width in characters.
            height: Height in characters.

        Returns:
            List of ASCII lines representing the cabinet.
        """
        lines: list[str] = []

        if cabinet is None:
            # Empty wall - just show outline
            lines.append("+" + "-" * (width - 2) + "+")
            for _ in range(height - 2):
                lines.append("|" + " " * (width - 2) + "|")
            lines.append("+" + "-" * (width - 2) + "+")
            return lines

        num_sections = len(cabinet.sections)
        if num_sections == 0:
            num_sections = 1

        # Calculate section widths proportionally
        section_chars = self._calculate_section_widths(cabinet, width - 2)

        # Top border
        top_line = "+"
        for sec_width in section_chars:
            top_line += "-" * sec_width + "+"
        # Ensure we don't exceed width
        if len(top_line) > width:
            top_line = top_line[: width - 1] + "+"
        lines.append(top_line)

        # Section labels row
        label_line = "|"
        for i, sec_width in enumerate(section_chars):
            if i < len(cabinet.sections):
                section = cabinet.sections[i]
                shelf_count = len(section.shelves)
                label = f"S{i + 1}({shelf_count})"
            else:
                label = f"S{i + 1}"
            # Center the label in the section width
            label = label[:sec_width]  # Truncate if too long
            padding = sec_width - len(label)
            left_pad = padding // 2
            right_pad = padding - left_pad
            label_line += " " * left_pad + label + " " * right_pad + "|"
        if len(label_line) > width:
            label_line = label_line[: width - 1] + "|"
        lines.append(label_line)

        # Divider row
        div_line = "|"
        for sec_width in section_chars:
            div_line += "-" * sec_width + "|"
        if len(div_line) > width:
            div_line = div_line[: width - 1] + "|"
        lines.append(div_line)

        # Content rows
        for _ in range(height - 4):
            content_line = "|"
            for sec_width in section_chars:
                content_line += " " * sec_width + "|"
            if len(content_line) > width:
                content_line = content_line[: width - 1] + "|"
            lines.append(content_line)

        # Bottom border
        bottom_line = "+"
        for sec_width in section_chars:
            bottom_line += "-" * sec_width + "+"
        if len(bottom_line) > width:
            bottom_line = bottom_line[: width - 1] + "+"
        lines.append(bottom_line)

        return lines

    def _calculate_section_widths(
        self, cabinet: Cabinet, available_chars: int
    ) -> list[int]:
        """Calculate proportional character widths for cabinet sections.

        Args:
            cabinet: The cabinet with sections to measure.
            available_chars: Total available characters (excluding borders).

        Returns:
            List of character widths for each section.
        """
        num_sections = len(cabinet.sections)
        if num_sections == 0:
            return [available_chars]

        # Account for dividers between sections
        divider_chars = num_sections - 1
        content_chars = available_chars - divider_chars

        if content_chars < num_sections:
            # Not enough space, give each section 1 char minimum
            return [1] * num_sections

        # Calculate proportional widths based on actual section widths
        total_width = sum(s.width for s in cabinet.sections)
        if total_width == 0:
            # Equal widths if no section widths defined
            base_width = content_chars // num_sections
            widths = [base_width] * num_sections
            # Distribute remainder
            remainder = content_chars - (base_width * num_sections)
            for i in range(remainder):
                widths[i] += 1
            return widths

        # Proportional widths
        widths = []
        remaining_chars = content_chars
        for i, section in enumerate(cabinet.sections):
            if i == num_sections - 1:
                # Last section gets remaining space
                widths.append(max(1, remaining_chars))
            else:
                proportion = section.width / total_width
                chars = max(1, int(content_chars * proportion))
                widths.append(chars)
                remaining_chars -= chars

        return widths


class HardwareReportFormatter:
    """Formats hardware lists for display.

    Provides formatted output of hardware requirements, grouped by
    category with totals and optional overage information.
    """

    def format(
        self,
        hardware_list: "HardwareList",
        title: str = "HARDWARE LIST",
        show_overage: bool = False,
        overage_percent: float = 10.0,
    ) -> str:
        """Format hardware list as a readable report.

        Args:
            hardware_list: HardwareList to format.
            title: Report title.
            show_overage: Whether to show overage column.
            overage_percent: Overage percentage for display.

        Returns:
            Formatted report string.
        """
        lines = [
            title,
            "=" * 60,
            "",
        ]

        if not hardware_list.items:
            lines.append("No hardware required.")
            return "\n".join(lines)

        # Group by category
        categories = hardware_list.by_category

        # Format header
        if show_overage:
            lines.append(
                f"{'Item':<35} {'Qty':>6} {'w/' + str(int(overage_percent)) + '%':>8}"
            )
        else:
            lines.append(f"{'Item':<35} {'Qty':>8}")
        lines.append("-" * 60)

        # Format each category
        for category, items in sorted(categories.items()):
            lines.append(f"\n{category.upper()}")
            for item in items:
                if show_overage:
                    overage_qty = math.ceil(item.quantity * (1 + overage_percent / 100))
                    lines.append(
                        f"  {item.name:<33} {item.quantity:>6} {overage_qty:>8}"
                    )
                else:
                    lines.append(f"  {item.name:<33} {item.quantity:>8}")

                if item.notes:
                    lines.append(f"    ({item.notes})")

        # Total
        lines.append("")
        lines.append("-" * 60)
        total = hardware_list.total_count
        if show_overage:
            total_with_overage = sum(
                math.ceil(item.quantity * (1 + overage_percent / 100))
                for item in hardware_list.items
            )
            lines.append(f"{'TOTAL':<35} {total:>6} {total_with_overage:>8}")
        else:
            lines.append(f"{'TOTAL':<35} {total:>8}")

        return "\n".join(lines)

    def format_shopping_list(
        self,
        hardware_list: "HardwareList",
    ) -> str:
        """Format hardware as a simple shopping list.

        Args:
            hardware_list: HardwareList to format.

        Returns:
            Simple list format for shopping.
        """
        lines = ["Shopping List:", ""]

        for item in sorted(hardware_list.items, key=lambda x: x.name):
            lines.append(f"[ ] {item.quantity}x {item.name}")
            if item.sku:
                lines.append(f"    SKU: {item.sku}")

        return "\n".join(lines)


class InstallationFormatter:
    """Formats installation instructions and hardware for output.

    Provides formatted output of installation information including
    step-by-step instructions, mounting hardware, stud analysis,
    and any warnings or recommendations.
    """

    def format(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Format complete installation output.

        Args:
            output: LayoutOutput or RoomLayoutOutput containing installation data.

        Returns:
            Formatted installation output as a string.
            Returns empty string if no installation instructions are present.
        """
        if not output.installation_instructions:
            return ""

        lines: list[str] = []

        # Installation instructions (already markdown)
        lines.append(output.installation_instructions)

        # Warnings section if any
        if output.installation_warnings:
            lines.append("\n## Warnings\n")
            for warning in output.installation_warnings:
                lines.append(f"- {warning}")

        # Stud analysis summary
        if output.stud_analysis:
            lines.append("\n## Stud Analysis Summary\n")
            lines.append(
                f'Cabinet position: {output.stud_analysis["cabinet_left_edge"]}" from wall start'
            )
            lines.append(f'Cabinet width: {output.stud_analysis["cabinet_width"]}"')
            lines.append(f"Studs hit: {output.stud_analysis['stud_hit_count']}")
            if output.stud_analysis.get("stud_positions"):
                positions = ", ".join(
                    f'{p}"' for p in output.stud_analysis["stud_positions"]
                )
                lines.append(f"Stud positions within cabinet: {positions}")
            if output.stud_analysis.get("recommendation"):
                lines.append(
                    f"\nRecommendation: {output.stud_analysis['recommendation']}"
                )

        return "\n".join(lines)

    def format_hardware_summary(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Format a summary of installation hardware.

        Args:
            output: LayoutOutput or RoomLayoutOutput containing installation data.

        Returns:
            Formatted hardware summary as a string.
        """
        if not output.installation_hardware:
            return "No installation hardware required."

        lines: list[str] = [
            "INSTALLATION HARDWARE",
            "=" * 50,
            "",
        ]

        for item in output.installation_hardware:
            qty_str = f"{item.quantity}x" if item.quantity > 1 else "1x"
            lines.append(f"  {qty_str} {item.name}")
            if item.notes:
                lines.append(f"      {item.notes}")

        total_count = sum(item.quantity for item in output.installation_hardware)
        lines.append("")
        lines.append("-" * 50)
        lines.append(f"Total items: {total_count}")

        return "\n".join(lines)

    def format_stud_analysis(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Format stud alignment analysis.

        Args:
            output: LayoutOutput or RoomLayoutOutput containing stud analysis.

        Returns:
            Formatted stud analysis as a string.
        """
        if not output.stud_analysis:
            return "No stud analysis available."

        analysis = output.stud_analysis
        lines: list[str] = [
            "STUD ALIGNMENT ANALYSIS",
            "=" * 50,
            "",
            f'Cabinet left edge: {analysis["cabinet_left_edge"]}" from wall start',
            f'Cabinet width: {analysis["cabinet_width"]}"',
            "",
        ]

        stud_count = analysis["stud_hit_count"]
        if stud_count == 0:
            lines.append("Stud hits: NONE - Consider repositioning cabinet")
        elif stud_count == 1:
            lines.append("Stud hits: 1 - Additional anchoring recommended")
        else:
            lines.append(f"Stud hits: {stud_count} - Good mounting positions available")

        if analysis.get("stud_positions"):
            lines.append("")
            lines.append("Stud positions within cabinet span:")
            for pos in analysis["stud_positions"]:
                relative_pos = pos - analysis["cabinet_left_edge"]
                lines.append(
                    f'  - {pos}" from wall start ({relative_pos:.1f}" from cabinet left)'
                )

        if analysis.get("non_stud_positions"):
            lines.append("")
            lines.append("Mounting points that miss studs:")
            for pos in analysis["non_stud_positions"]:
                relative_pos = pos - analysis["cabinet_left_edge"]
                lines.append(
                    f'  - {pos}" from wall start ({relative_pos:.1f}" from cabinet left)'
                )

        if analysis.get("recommendation"):
            lines.append("")
            lines.append("-" * 50)
            lines.append(f"RECOMMENDATION: {analysis['recommendation']}")

        return "\n".join(lines)


class SafetyReportFormatter:
    """Formatter for generating safety report in markdown format.

    Generates a comprehensive safety report from a SafetyAssessment,
    including all check results, weight capacities, accessibility
    analysis, and recommendations.

    Example:
        ```python
        formatter = SafetyReportFormatter()
        assessment = safety_service.analyze(cabinet, obstacles)
        report = formatter.format(assessment)
        print(report)
        ```
    """

    def __init__(self) -> None:
        """Initialize the SafetyReportFormatter."""
        # Import here to avoid circular imports at module level
        from cabinets.domain.value_objects import SafetyCheckStatus

        self._status_icons = {
            SafetyCheckStatus.PASS: "[PASS]",
            SafetyCheckStatus.WARNING: "[WARN]",
            SafetyCheckStatus.ERROR: "[FAIL]",
            SafetyCheckStatus.NOT_APPLICABLE: "[N/A]",
        }

    def format(self, assessment: "SafetyAssessment") -> str:
        """Generate markdown safety report from assessment.

        Args:
            assessment: Completed SafetyAssessment.

        Returns:
            Markdown-formatted safety report string.
        """
        from cabinets.domain.value_objects import SafetyCategory

        sections: list[str] = []

        # Header
        sections.append(self._format_header(assessment))

        # Summary
        sections.append(self._format_summary(assessment))

        # Weight Capacity
        if assessment.weight_capacities:
            sections.append(self._format_weight_capacity(assessment))

        # Stability
        stability_results = assessment.get_results_by_category(SafetyCategory.STABILITY)
        if stability_results:
            sections.append(self._format_stability(assessment, stability_results))

        # Accessibility
        if (
            assessment.accessibility_report
            and assessment.accessibility_report.total_storage_volume > 0
        ):
            sections.append(self._format_accessibility(assessment))

        # Clearances
        clearance_results = assessment.get_results_by_category(SafetyCategory.CLEARANCE)
        if clearance_results:
            sections.append(self._format_clearances(clearance_results))

        # Material Safety
        material_results = assessment.get_results_by_category(SafetyCategory.MATERIAL)
        if material_results:
            sections.append(self._format_material_safety(material_results))

        # Seismic
        seismic_results = assessment.get_results_by_category(SafetyCategory.SEISMIC)
        if seismic_results or assessment.seismic_hardware:
            sections.append(self._format_seismic(assessment, seismic_results))

        # Child Safety
        child_results = assessment.get_results_by_category(SafetyCategory.CHILD_SAFETY)
        if child_results or assessment.child_safety_notes:
            sections.append(self._format_child_safety(assessment, child_results))

        # Safety Labels (if present)
        if assessment.safety_labels:
            sections.append(self._format_safety_labels(assessment))

        # Disclaimers
        sections.append(self._format_disclaimers())

        return "\n\n".join(sections)

    def _format_header(self, assessment: "SafetyAssessment") -> str:
        """Format report header.

        Args:
            assessment: The safety assessment.

        Returns:
            Markdown header string.
        """
        return "# Safety Assessment Report\n\nGenerated by Cabinet Layout Generator"

    def _format_summary(self, assessment: "SafetyAssessment") -> str:
        """Format summary section.

        Args:
            assessment: The safety assessment.

        Returns:
            Markdown summary section.
        """
        lines: list[str] = ["## Summary"]

        # Status badge
        if assessment.has_errors:
            status = "**FAILED** - Safety issues require attention"
        elif assessment.has_warnings:
            status = "**PASSED with WARNINGS** - Review recommended"
        else:
            status = "**PASSED** - All safety checks passed"

        lines.append(f"\nStatus: {status}")
        lines.append(f"\n- Errors: {assessment.errors_count}")
        lines.append(f"- Warnings: {assessment.warnings_count}")

        if assessment.anti_tip_required:
            lines.append("\n**Anti-tip restraint is required for this cabinet.**")

        return "\n".join(lines)

    def _format_weight_capacity(self, assessment: "SafetyAssessment") -> str:
        """Format weight capacity section.

        Args:
            assessment: The safety assessment.

        Returns:
            Markdown weight capacity section with table.
        """
        from cabinets.domain.value_objects import SafetyCategory

        lines: list[str] = ["## Weight Capacity"]

        lines.append("\n| Shelf | Capacity | Material | Span | Safety Factor |")
        lines.append("|-------|----------|----------|------|---------------|")

        for cap in assessment.weight_capacities:
            lines.append(
                f"| {cap.panel_id} | {cap.safe_load_lbs:.0f} lbs | "
                f'{cap.material} | {cap.span_inches:.1f}" | {cap.safety_factor:.0f}:1 |'
            )

        # Structural check results
        structural_results = assessment.get_results_by_category(
            SafetyCategory.STRUCTURAL
        )
        if structural_results:
            lines.append("\n### Structural Analysis")
            for result in structural_results:
                lines.append(f"\n{self._status_icons[result.status]} {result.message}")
                if result.remediation:
                    lines.append(f"  - *Suggestion: {result.remediation}*")
                if result.standard_reference:
                    lines.append(f"  - Standard: {result.standard_reference}")

        return "\n".join(lines)

    def _format_stability(
        self,
        assessment: "SafetyAssessment",
        results: list["SafetyCheckResult"],
    ) -> str:
        """Format stability section.

        Args:
            assessment: The safety assessment.
            results: Stability check results.

        Returns:
            Markdown stability section.
        """
        lines: list[str] = ["## Stability"]

        for result in results:
            lines.append(f"\n{self._status_icons[result.status]} {result.message}")
            if result.remediation:
                lines.append(f"  - *Suggestion: {result.remediation}*")
            if result.standard_reference:
                lines.append(f"  - Standard: {result.standard_reference}")

        if assessment.anti_tip_required:
            lines.append("\n### Anti-Tip Hardware Required")
            lines.append(
                "\n**WARNING:** To reduce the risk of tip-over, this furniture"
            )
            lines.append("must be anchored to the wall. See installation instructions.")

        return "\n".join(lines)

    def _format_accessibility(self, assessment: "SafetyAssessment") -> str:
        """Format accessibility section.

        Args:
            assessment: The safety assessment.

        Returns:
            Markdown accessibility section.
        """
        report = assessment.accessibility_report
        if not report:
            return ""

        lines: list[str] = ["## Accessibility (ADA)"]

        status = "COMPLIANT" if report.is_compliant else "NON-COMPLIANT"
        lines.append(f"\nStatus: **{status}**")
        lines.append(f"\n- Accessible Storage: {report.accessible_percentage:.1f}%")
        lines.append("- Required Minimum: 50%")
        lines.append(f"- Standard: {report.standard.value}")

        if report.reach_violations:
            lines.append("\n### Reach Range Violations")
            for violation in report.reach_violations:
                lines.append(f"- {violation}")

        if report.non_compliant_areas:
            lines.append("\n### Non-Compliant Areas")
            for area in report.non_compliant_areas:
                lines.append(f"- {area}")

        if report.hardware_notes:
            lines.append("\n### Hardware Recommendations")
            for note in report.hardware_notes:
                lines.append(f"- {note}")

        return "\n".join(lines)

    def _format_clearances(self, results: list["SafetyCheckResult"]) -> str:
        """Format clearances section.

        Args:
            results: Clearance check results.

        Returns:
            Markdown clearances section.
        """
        lines: list[str] = ["## Building Code Clearances"]

        for result in results:
            lines.append(f"\n{self._status_icons[result.status]} {result.message}")
            if result.remediation:
                lines.append(f"  - *Suggestion: {result.remediation}*")
            if result.standard_reference:
                lines.append(f"  - Standard: {result.standard_reference}")

        return "\n".join(lines)

    def _format_material_safety(self, results: list["SafetyCheckResult"]) -> str:
        """Format material safety section.

        Args:
            results: Material safety check results.

        Returns:
            Markdown material safety section.
        """
        lines: list[str] = ["## Material Safety"]

        for result in results:
            lines.append(f"\n{self._status_icons[result.status]} {result.message}")
            if result.remediation:
                lines.append(f"  - *Suggestion: {result.remediation}*")
            if result.standard_reference:
                lines.append(f"  - Standard: {result.standard_reference}")

        return "\n".join(lines)

    def _format_seismic(
        self,
        assessment: "SafetyAssessment",
        results: list["SafetyCheckResult"],
    ) -> str:
        """Format seismic section.

        Args:
            assessment: The safety assessment.
            results: Seismic check results.

        Returns:
            Markdown seismic section.
        """
        lines: list[str] = ["## Seismic Requirements"]

        for result in results:
            lines.append(f"\n{self._status_icons[result.status]} {result.message}")
            if result.remediation:
                lines.append(f"  - *Suggestion: {result.remediation}*")
            if result.standard_reference:
                lines.append(f"  - Standard: {result.standard_reference}")

        if assessment.seismic_hardware:
            lines.append("\n### Required Hardware")
            for hw in assessment.seismic_hardware:
                lines.append(f"- {hw}")

        return "\n".join(lines)

    def _format_child_safety(
        self,
        assessment: "SafetyAssessment",
        results: list["SafetyCheckResult"],
    ) -> str:
        """Format child safety section.

        Args:
            assessment: The safety assessment.
            results: Child safety check results.

        Returns:
            Markdown child safety section.
        """
        lines: list[str] = ["## Child Safety"]

        for result in results:
            lines.append(f"\n{self._status_icons[result.status]} {result.message}")
            if result.remediation:
                lines.append(f"  - *Suggestion: {result.remediation}*")

        if assessment.child_safety_notes:
            lines.append("\n### Recommendations")
            for note in assessment.child_safety_notes:
                lines.append(f"- {note}")

        return "\n".join(lines)

    def _format_safety_labels(self, assessment: "SafetyAssessment") -> str:
        """Format safety labels section.

        Args:
            assessment: The safety assessment.

        Returns:
            Markdown safety labels section.
        """
        lines: list[str] = ["## Safety Labels"]
        lines.append(
            "\nThe following safety labels should be attached to this cabinet:"
        )

        for label in assessment.safety_labels:
            lines.append(f"\n### {label.title}")
            lines.append(f"- Type: {label.label_type}")
            lines.append(f'- Size: {label.width_inches}" x {label.height_inches}"')
            if label.warning_icon:
                lines.append("- Includes warning icon")
            # Show first line of body text as preview
            preview = label.body_text.split("\n")[0]
            if len(preview) > 60:
                preview = preview[:60] + "..."
            lines.append(f'- Content: "{preview}"')

        return "\n".join(lines)

    def _format_disclaimers(self) -> str:
        """Format disclaimers section.

        Returns:
            Markdown disclaimers section.
        """
        from cabinets.domain.services.safety import (
            ADA_DISCLAIMER,
            MATERIAL_DISCLAIMER,
            SAFETY_GENERAL_DISCLAIMER,
        )

        lines: list[str] = ["## Disclaimers"]

        lines.append(f"\n**General:** {SAFETY_GENERAL_DISCLAIMER}")
        lines.append(f"\n**Accessibility:** {ADA_DISCLAIMER}")
        lines.append(f"\n**Materials:** {MATERIAL_DISCLAIMER}")

        return "\n".join(lines)
