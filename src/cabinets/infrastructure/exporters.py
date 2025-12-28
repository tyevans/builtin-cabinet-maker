"""Output formatters and exporters for cabinet layouts."""

import json
from dataclasses import asdict
from typing import Any

from cabinets.application import LayoutOutput
from cabinets.domain import Cabinet, CutPiece, MaterialEstimate, MaterialSpec


class CutListFormatter:
    """Formats cut lists for display."""

    def format(self, cut_list: list[CutPiece]) -> str:
        """Format cut list as a table."""
        if not cut_list:
            return "No pieces in cut list."

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

        # Calculate scale
        scale_x = (width - 4) / cabinet.width
        scale_y = (height - 2) / cabinet.height

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
                            for x in range(section_x, section_x + section_display_width - 1):
                                if x < width - 1:
                                    grid[shelf_y][x] = "-"

        # Convert grid to string
        for row in grid:
            lines.append("".join(row))

        # Add dimensions
        lines.append("")
        lines.append(f"Dimensions: {cabinet.width}\" W x {cabinet.height}\" H x {cabinet.depth}\" D")
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
            lines.append(f"{material.material_type.value.title()} ({material.thickness}\" thick)")
            lines.append(f"  Area needed: {estimate.total_area_sqft:.2f} sq ft")
            lines.append(f"  4x8 sheets:  {estimate.sheet_count_4x8} (with {estimate.waste_percentage:.0%} waste)")
            lines.append("")

        lines.append("-" * 60)
        lines.append("TOTAL (all materials)")
        lines.append(f"  Area: {total.total_area_sqft:.2f} sq ft")
        lines.append(f"  4x8 sheets: {total.sheet_count_4x8}")
        lines.append(f"  (Includes {total.waste_percentage:.0%} waste factor)")

        return "\n".join(lines)


class JsonExporter:
    """Exports layout data as JSON."""

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
            "cut_list": [
                {
                    "label": p.label,
                    "width": p.width,
                    "height": p.height,
                    "quantity": p.quantity,
                    "panel_type": p.panel_type.value,
                    "material_thickness": p.material.thickness,
                }
                for p in output.cut_list
            ],
            "material_estimate": {
                "total_area_sqft": output.total_estimate.total_area_sqft,
                "sheet_count_4x8": output.total_estimate.sheet_count_4x8,
                "waste_percentage": output.total_estimate.waste_percentage,
            },
        }
        return json.dumps(data, indent=2)
