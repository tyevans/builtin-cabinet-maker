"""Cut diagram rendering for bin packing visualization.

This module provides SVG and ASCII rendering of sheet layouts showing piece
placements, dimensions, rotation indicators, and waste areas.
"""

from __future__ import annotations

from cabinets.domain.value_objects import PanelType
from cabinets.infrastructure.bin_packing import (
    PackingResult,
    PlacedPiece,
    SheetConfig,
    SheetLayout,
)

# Color mapping for panel types (FR-04.2)
PANEL_TYPE_COLORS: dict[PanelType, str] = {
    PanelType.SHELF: "#87CEEB",  # Sky blue
    PanelType.LEFT_SIDE: "#90EE90",  # Light green
    PanelType.RIGHT_SIDE: "#90EE90",  # Light green
    PanelType.TOP: "#DDA0DD",  # Plum
    PanelType.BOTTOM: "#DDA0DD",  # Plum
    PanelType.BACK: "#D3D3D3",  # Light gray
    PanelType.DIVIDER: "#F0E68C",  # Khaki
    PanelType.DOOR: "#FFB6C1",  # Light pink
    PanelType.DRAWER_FRONT: "#FFA07A",  # Light salmon
    PanelType.HORIZONTAL_DIVIDER: "#F0E68C",  # Khaki (same as divider)
    PanelType.DRAWER_SIDE: "#FFD700",  # Gold
    PanelType.DRAWER_BOX_FRONT: "#FFA07A",  # Light salmon (same as drawer front)
    PanelType.DRAWER_BOTTOM: "#DEB887",  # Burlywood
    PanelType.DIAGONAL_FACE: "#E6E6FA",  # Lavender
    PanelType.FILLER: "#F5F5DC",  # Beige
    # Decorative panels (FRD-12)
    PanelType.ARCH_HEADER: "#DDA0DD",  # Plum
    PanelType.FACE_FRAME_RAIL: "#BC8F8F",  # Rosy brown
    PanelType.FACE_FRAME_STILE: "#BC8F8F",  # Rosy brown
    PanelType.LIGHT_RAIL: "#E0E0E0",  # Very light gray
    PanelType.NAILER: "#A9A9A9",  # Dark gray
    PanelType.TOE_KICK: "#8B4513",  # Saddle brown
    PanelType.VALANCE: "#D8BFD8",  # Thistle
}


class CutDiagramRenderer:
    """Renders cut diagrams in SVG format.

    Generates visual representations of sheet layouts showing
    piece placements, dimensions, and waste areas.

    Attributes:
        scale: Pixels per inch for SVG rendering (default 10).
        piece_fill: Default fill color for placed pieces.
        piece_stroke: Stroke color for piece outlines.
        waste_fill: Fill color for waste areas.
        text_color: Color for labels and dimensions.
        show_dimensions: Whether to show piece dimensions in labels.
        show_labels: Whether to show piece labels.
        show_grain: Whether to show grain direction indicators.
        use_panel_colors: Whether to color pieces by panel type.
    """

    def __init__(
        self,
        scale: float = 10.0,
        piece_fill: str = "#ADD8E6",  # Light blue
        piece_stroke: str = "#000000",  # Black
        waste_fill: str = "#D3D3D3",  # Light gray
        text_color: str = "#000000",  # Black
        show_dimensions: bool = True,
        show_labels: bool = True,
        show_grain: bool = False,
        use_panel_colors: bool = True,
    ) -> None:
        """Initialize renderer with styling options.

        Args:
            scale: Pixels per inch for SVG rendering (default 10.0).
            piece_fill: Default fill color for placed pieces (default light blue).
            piece_stroke: Stroke color for piece outlines (default black).
            waste_fill: Fill color for waste areas (default light gray).
            text_color: Color for labels and dimensions (default black).
            show_dimensions: Whether to show piece dimensions (default True).
            show_labels: Whether to show piece labels (default True).
            show_grain: Whether to show grain direction arrows (default False).
            use_panel_colors: Whether to color pieces by panel type (default True).
        """
        self.scale = scale
        self.piece_fill = piece_fill
        self.piece_stroke = piece_stroke
        self.waste_fill = waste_fill
        self.text_color = text_color
        self.show_dimensions = show_dimensions
        self.show_labels = show_labels
        self.show_grain = show_grain
        self.use_panel_colors = use_panel_colors

    def render_svg(self, layout: SheetLayout, total_sheets: int = 1) -> str:
        """Generate SVG cut diagram for a single sheet.

        Args:
            layout: Sheet layout with placed pieces.
            total_sheets: Total number of sheets (for header display).

        Returns:
            SVG string representation of the layout.
        """
        sheet = layout.sheet_config
        header_height = 30  # Pixels for header text

        # Collect panel types used in this layout for legend
        panel_types_used: set[PanelType] = set()
        if self.use_panel_colors:
            for placement in layout.placements:
                panel_types_used.add(placement.piece.panel_type)

        # Calculate legend height
        legend_height = self._calculate_legend_height(panel_types_used)

        # Calculate SVG dimensions
        svg_width = sheet.width * self.scale
        svg_height = sheet.height * self.scale + header_height + legend_height

        # Start SVG document
        parts: list[str] = [
            f'<svg width="{svg_width}" height="{svg_height}" '
            f'xmlns="http://www.w3.org/2000/svg">',
            "",
            "  <!-- Background -->",
            f'  <rect x="0" y="0" width="{svg_width}" height="{svg_height}" '
            f'fill="white"/>',
            "",
        ]

        # Add header
        parts.append(
            self._render_header(layout, total_sheets, svg_width, header_height)
        )

        # Add sheet outline (offset by header)
        parts.append("  <!-- Sheet outline -->")
        parts.append(
            f'  <rect x="0" y="{header_height}" '
            f'width="{svg_width}" height="{sheet.height * self.scale}" '
            f'fill="#f5deb3" stroke="{self.piece_stroke}" stroke-width="2"/>'
        )

        # Add edge allowance indicator (dashed rectangle)
        if sheet.edge_allowance > 0:
            ea = sheet.edge_allowance * self.scale
            usable_w = sheet.usable_width * self.scale
            usable_h = sheet.usable_height * self.scale
            parts.append("  <!-- Usable area (inside edge allowance) -->")
            parts.append(
                f'  <rect x="{ea}" y="{header_height + ea}" '
                f'width="{usable_w}" height="{usable_h}" '
                f'fill="none" stroke="#999999" stroke-dasharray="5,5"/>'
            )

        # Add waste areas (before pieces so pieces render on top)
        parts.append("")
        parts.append("  <!-- Waste areas -->")
        waste_svg = self._render_waste_areas(layout, header_height)
        if waste_svg:
            parts.append(waste_svg)

        # Add placed pieces
        parts.append("")
        parts.append("  <!-- Placed pieces -->")
        for placement in layout.placements:
            parts.append(self._render_piece(placement, sheet, header_height))

        # Add legend if panel colors are used
        if self.use_panel_colors and panel_types_used:
            legend_y = header_height + sheet.height * self.scale
            parts.append("")
            parts.append("  <!-- Legend -->")
            parts.append(self._render_legend(panel_types_used, svg_width, legend_y))

        # Close SVG
        parts.append("")
        parts.append("</svg>")

        return "\n".join(parts)

    def render_all_svg(self, result: PackingResult) -> list[str]:
        """Generate SVG cut diagrams for all sheets.

        Args:
            result: Complete packing result.

        Returns:
            List of SVG strings, one per sheet.
        """
        total_sheets = len(result.layouts)
        return [self.render_svg(layout, total_sheets) for layout in result.layouts]

    def _render_header(
        self,
        layout: SheetLayout,
        total_sheets: int,
        svg_width: float,
        header_height: float,
    ) -> str:
        """Render sheet header with material and waste info.

        Args:
            layout: Sheet layout.
            total_sheets: Total number of sheets.
            svg_width: SVG width in pixels.
            header_height: Header height in pixels.

        Returns:
            SVG elements for header.
        """
        material = layout.material
        material_desc = f'{material.thickness}" {material.material_type.value}'
        waste = layout.waste_percentage

        header_text = (
            f"Sheet {layout.sheet_index + 1} of {total_sheets} - "
            f"{material_desc} - {waste:.1f}% waste"
        )

        return (
            f"  <!-- Header -->\n"
            f'  <rect x="0" y="0" width="{svg_width}" height="{header_height}" '
            f'fill="#E0E0E0"/>\n'
            f'  <text x="10" y="{header_height - 8}" '
            f'font-family="Arial, sans-serif" font-size="14" '
            f'fill="{self.text_color}">{header_text}</text>'
        )

    def _render_piece(
        self,
        placement: PlacedPiece,
        sheet: SheetConfig,
        header_height: float,
    ) -> str:
        """Render a single placed piece as SVG rect and text.

        Args:
            placement: The placed piece.
            sheet: Sheet configuration.
            header_height: Header height offset.

        Returns:
            SVG elements for the piece.
        """
        # Calculate position (account for edge allowance and header)
        x = (sheet.edge_allowance + placement.x) * self.scale
        y = header_height + (sheet.edge_allowance + placement.y) * self.scale
        w = placement.placed_width * self.scale
        h = placement.placed_height * self.scale

        piece = placement.piece
        label = piece.label

        # Determine fill color based on panel type if use_panel_colors is True
        if self.use_panel_colors:
            fill_color = PANEL_TYPE_COLORS.get(piece.panel_type, self.piece_fill)
        else:
            fill_color = self.piece_fill

        # Build dimensions string
        dims = f'{piece.width:.1f}" x {piece.height:.1f}"'
        if placement.rotated:
            dims += " (R)"  # Rotation indicator

        # Center text in piece
        text_x = x + w / 2
        text_y = y + h / 2

        # Adjust font size based on piece dimensions
        font_size = min(12, min(w, h) / 6)
        if font_size < 6:
            # Too small for text, just show piece without labels
            svg_parts = [
                f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                f'fill="{fill_color}" stroke="{self.piece_stroke}"/>'
            ]
            # Add grain indicator even for small pieces if enabled
            if self.show_grain:
                grain_svg = self._render_grain_indicator(
                    placement, x, y, w, h, font_size
                )
                if grain_svg:
                    svg_parts.append(grain_svg)
            return "\n".join(svg_parts)

        # Build the piece SVG group
        svg_parts = [
            "  <g>",
            f'    <rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill_color}" stroke="{self.piece_stroke}"/>',
        ]

        # Add label if show_labels is True
        if self.show_labels:
            svg_parts.append(
                f'    <text x="{text_x}" y="{text_y - font_size / 2}" '
                f'text-anchor="middle" font-family="Arial, sans-serif" '
                f'font-size="{font_size}" fill="{self.text_color}">{label}</text>'
            )

        # Add dimensions if show_dimensions is True
        if self.show_dimensions:
            # Adjust vertical position if label is hidden
            dims_y = text_y + font_size / 2 + 2 if self.show_labels else text_y
            svg_parts.append(
                f'    <text x="{text_x}" y="{dims_y}" '
                f'text-anchor="middle" font-family="Arial, sans-serif" '
                f'font-size="{font_size * 0.8}" fill="{self.text_color}">{dims}</text>'
            )

        # Add grain direction indicator if show_grain is True
        if self.show_grain:
            grain_svg = self._render_grain_indicator(placement, x, y, w, h, font_size)
            if grain_svg:
                svg_parts.append(grain_svg)

        svg_parts.append("  </g>")
        return "\n".join(svg_parts)

    def _render_grain_indicator(
        self,
        placement: PlacedPiece,
        x: float,
        y: float,
        w: float,
        h: float,
        font_size: float,
    ) -> str | None:
        """Render grain direction arrow on a piece.

        Args:
            placement: The placed piece with metadata.
            x: X position of piece in pixels.
            y: Y position of piece in pixels.
            w: Width of piece in pixels.
            h: Height of piece in pixels.
            font_size: Font size for text (used to scale arrow).

        Returns:
            SVG elements for grain arrow, or None if no grain direction.
        """
        piece = placement.piece
        grain_direction = None

        # Get grain direction from cut_metadata if available
        if piece.cut_metadata:
            grain_direction = piece.cut_metadata.get("grain_direction")

        if not grain_direction:
            return None

        # Calculate arrow position (bottom-right corner of piece)
        arrow_margin = max(5, font_size)
        arrow_length = min(20, min(w, h) / 4)

        # Position arrow in lower-right area
        arrow_x = x + w - arrow_margin - arrow_length
        arrow_y = y + h - arrow_margin

        # Determine arrow direction based on grain_direction value
        # and whether piece is rotated
        if grain_direction == "length":
            # Grain runs along the original length (longest dimension)
            # Arrow horizontal by default, but vertical if rotated
            if placement.rotated:
                # Vertical arrow (pointing down)
                return self._render_arrow(
                    arrow_x + arrow_length / 2,
                    arrow_y - arrow_length,
                    arrow_x + arrow_length / 2,
                    arrow_y,
                )
            else:
                # Horizontal arrow (pointing right)
                return self._render_arrow(
                    arrow_x,
                    arrow_y - arrow_length / 2,
                    arrow_x + arrow_length,
                    arrow_y - arrow_length / 2,
                )
        elif grain_direction == "width":
            # Grain runs along the original width (shortest dimension)
            if placement.rotated:
                # Horizontal arrow
                return self._render_arrow(
                    arrow_x,
                    arrow_y - arrow_length / 2,
                    arrow_x + arrow_length,
                    arrow_y - arrow_length / 2,
                )
            else:
                # Vertical arrow
                return self._render_arrow(
                    arrow_x + arrow_length / 2,
                    arrow_y - arrow_length,
                    arrow_x + arrow_length / 2,
                    arrow_y,
                )
        # "none" or unrecognized - no indicator
        return None

    def _render_arrow(self, x1: float, y1: float, x2: float, y2: float) -> str:
        """Render an arrow from (x1, y1) to (x2, y2).

        Args:
            x1: Start X coordinate.
            y1: Start Y coordinate.
            x2: End X coordinate (arrow head).
            y2: End Y coordinate (arrow head).

        Returns:
            SVG elements for the arrow.
        """
        # Arrow line
        svg = f'    <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        svg += f'stroke="{self.text_color}" stroke-width="1.5"/>\n'

        # Calculate arrow head points
        import math

        angle = math.atan2(y2 - y1, x2 - x1)
        head_length = 6
        head_angle = math.pi / 6  # 30 degrees

        # Left side of arrow head
        lx = x2 - head_length * math.cos(angle - head_angle)
        ly = y2 - head_length * math.sin(angle - head_angle)

        # Right side of arrow head
        rx = x2 - head_length * math.cos(angle + head_angle)
        ry = y2 - head_length * math.sin(angle + head_angle)

        # Arrow head as polygon
        svg += f'    <polygon points="{x2},{y2} {lx},{ly} {rx},{ry}" '
        svg += f'fill="{self.text_color}"/>'

        return svg

    def _calculate_legend_height(self, panel_types: set[PanelType]) -> float:
        """Calculate the height needed for the legend.

        Args:
            panel_types: Set of panel types used in the diagram.

        Returns:
            Height in pixels needed for the legend, or 0 if no legend.
        """
        if not panel_types or not self.use_panel_colors:
            return 0.0

        # Calculate rows needed (3 columns of items per row)
        items_per_row = 3
        num_items = len(panel_types)
        num_rows = (num_items + items_per_row - 1) // items_per_row

        # Height: title (20px) + padding (10px) + rows (25px each) + bottom padding (10px)
        return 20 + 10 + (num_rows * 25) + 10

    def _render_legend(
        self,
        panel_types: set[PanelType],
        svg_width: float,
        y_offset: float,
    ) -> str:
        """Render legend showing panel type colors.

        Args:
            panel_types: Set of panel types used in the diagram.
            svg_width: Width of the SVG in pixels.
            y_offset: Y position to start the legend.

        Returns:
            SVG elements for the legend.
        """
        if not panel_types:
            return ""

        parts: list[str] = []

        # Legend background
        legend_height = self._calculate_legend_height(panel_types)
        parts.append(
            f'  <rect x="0" y="{y_offset}" width="{svg_width}" '
            f'height="{legend_height}" fill="#F5F5F5" stroke="#CCCCCC"/>'
        )

        # Legend title
        parts.append(
            f'  <text x="10" y="{y_offset + 18}" '
            f'font-family="Arial, sans-serif" font-size="12" font-weight="bold" '
            f'fill="{self.text_color}">Panel Types:</text>'
        )

        # Sort panel types for consistent ordering
        sorted_types = sorted(panel_types, key=lambda pt: pt.value)

        # Layout items in columns (3 columns)
        items_per_row = 3
        column_width = svg_width / items_per_row
        swatch_size = 15
        start_y = y_offset + 35  # After title

        for idx, panel_type in enumerate(sorted_types):
            row = idx // items_per_row
            col = idx % items_per_row

            x = col * column_width + 15
            y = start_y + row * 25

            color = PANEL_TYPE_COLORS.get(panel_type, self.piece_fill)

            # Color swatch
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{swatch_size}" height="{swatch_size}" '
                f'fill="{color}" stroke="{self.piece_stroke}"/>'
            )

            # Label - format panel type name nicely
            label = panel_type.value.replace("_", " ").title()
            parts.append(
                f'  <text x="{x + swatch_size + 5}" y="{y + swatch_size - 3}" '
                f'font-family="Arial, sans-serif" font-size="10" '
                f'fill="{self.text_color}">{label}</text>'
            )

        return "\n".join(parts)

    def _render_waste_areas(self, layout: SheetLayout, header_height: float) -> str:
        """Render waste areas as gray rectangles.

        Calculates approximate waste regions based on piece placements.
        Shows vertical waste strip (below all pieces) and horizontal gaps.

        Args:
            layout: Sheet layout.
            header_height: Header height offset.

        Returns:
            SVG elements for waste areas.
        """
        if not layout.placements:
            return ""

        sheet = layout.sheet_config
        ea = sheet.edge_allowance

        parts: list[str] = []

        # Find the maximum Y extent of all pieces
        max_y = max(p.y + p.placed_height for p in layout.placements)

        # Vertical waste strip below all pieces
        waste_height = sheet.usable_height - max_y
        if waste_height > 1:  # Only show if meaningful
            x = ea * self.scale
            y = header_height + (ea + max_y) * self.scale
            w = sheet.usable_width * self.scale
            h = waste_height * self.scale
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                f'fill="{self.waste_fill}" stroke="none"/>'
            )

        # Horizontal waste strip to the right (simplified - rightmost edge)
        max_x = max(p.x + p.placed_width for p in layout.placements)
        waste_width = sheet.usable_width - max_x
        if waste_width > 1:  # Only show if meaningful
            x = (ea + max_x) * self.scale
            y = header_height + ea * self.scale
            w = waste_width * self.scale
            h = max_y * self.scale
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                f'fill="{self.waste_fill}" stroke="none"/>'
            )

        return "\n".join(parts)

    def render_combined_svg(self, result: PackingResult) -> str:
        """Generate single SVG with all sheets stacked vertically.

        Args:
            result: Complete packing result.

        Returns:
            Combined SVG string with all sheets.
        """
        if not result.layouts:
            return (
                '<svg width="100" height="50" xmlns="http://www.w3.org/2000/svg">'
                '<text x="10" y="30">No sheets to display</text></svg>'
            )

        # Calculate combined dimensions
        header_height = 30
        sheet_spacing = 20
        first_sheet = result.layouts[0].sheet_config

        svg_width = first_sheet.width * self.scale
        svg_height = sum(
            layout.sheet_config.height * self.scale + header_height + sheet_spacing
            for layout in result.layouts
        )

        parts: list[str] = [
            f'<svg width="{svg_width}" height="{svg_height}" '
            f'xmlns="http://www.w3.org/2000/svg">',
            f'  <rect x="0" y="0" width="{svg_width}" height="{svg_height}" '
            f'fill="white"/>',
        ]

        y_offset = 0.0
        total_sheets = len(result.layouts)

        for layout in result.layouts:
            # Render this sheet's content in a translated group
            parts.append(f'  <g transform="translate(0, {y_offset})">')
            parts.append(f"    <!-- Sheet {layout.sheet_index + 1} -->")

            # Get the individual sheet SVG and extract the content
            # (between the opening and closing svg tags)
            sheet_svg = self.render_svg(layout, total_sheets)
            # Extract content between <svg...> and </svg>
            start_idx = sheet_svg.find(">") + 1
            end_idx = sheet_svg.rfind("</svg>")
            inner_content = sheet_svg[start_idx:end_idx]

            # Indent and add the inner content
            for line in inner_content.strip().split("\n"):
                if line.strip():
                    parts.append(f"  {line}")

            parts.append("  </g>")

            y_offset += (
                layout.sheet_config.height * self.scale + header_height + sheet_spacing
            )

        parts.append("</svg>")
        return "\n".join(parts)

    def render_ascii(
        self,
        layout: SheetLayout,
        width: int = 80,
        total_sheets: int = 1,
    ) -> str:
        """Generate ASCII cut diagram for a single sheet.

        Creates a text-based representation of the sheet layout suitable
        for terminal display. Uses box-drawing characters for piece outlines.

        Args:
            layout: Sheet layout with placed pieces.
            width: Terminal width in characters (default 80).
            total_sheets: Total number of sheets (for header display).

        Returns:
            ASCII string representation of the layout.
        """
        sheet = layout.sheet_config
        material = layout.material
        material_desc = f'{material.thickness}" {material.material_type.value}'

        # Calculate scale: characters per inch
        # Reserve 2 chars for borders
        usable_width = width - 2
        scale_x = usable_width / sheet.width

        # Calculate height in lines (proportional to width)
        aspect_ratio = sheet.height / sheet.width
        grid_height = int(
            usable_width * aspect_ratio * 0.5
        )  # 0.5 for char aspect ratio
        grid_height = max(grid_height, 10)  # Minimum height

        scale_y = grid_height / sheet.height

        # Create grid
        grid = [[" " for _ in range(usable_width)] for _ in range(grid_height)]

        # Draw pieces onto grid
        for placement in layout.placements:
            self._draw_piece_ascii(grid, placement, sheet, scale_x, scale_y)

        # Build output
        lines: list[str] = []

        # Header
        header = (
            f"Sheet {layout.sheet_index + 1} of {total_sheets} - "
            f"{material_desc} - {layout.waste_percentage:.1f}% waste"
        )
        lines.append(header)

        # Top border
        lines.append("+" + "-" * usable_width + "+")

        # Grid content
        for row in grid:
            lines.append("|" + "".join(row) + "|")

        # Bottom border
        lines.append("+" + "-" * usable_width + "+")

        return "\n".join(lines)

    def _draw_piece_ascii(
        self,
        grid: list[list[str]],
        placement: PlacedPiece,
        sheet: SheetConfig,
        scale_x: float,
        scale_y: float,
    ) -> None:
        """Draw a single piece onto the ASCII grid.

        Args:
            grid: 2D character grid.
            placement: The placed piece.
            sheet: Sheet configuration.
            scale_x: Characters per inch (horizontal).
            scale_y: Characters per inch (vertical).
        """
        # Calculate grid coordinates
        ea = sheet.edge_allowance
        x1 = int((ea + placement.x) * scale_x)
        y1 = int((ea + placement.y) * scale_y)
        x2 = int((ea + placement.x + placement.placed_width) * scale_x)
        y2 = int((ea + placement.y + placement.placed_height) * scale_y)

        # Clamp to grid bounds
        grid_height = len(grid)
        grid_width = len(grid[0]) if grid else 0
        x1 = max(0, min(x1, grid_width - 1))
        x2 = max(0, min(x2, grid_width - 1))
        y1 = max(0, min(y1, grid_height - 1))
        y2 = max(0, min(y2, grid_height - 1))

        # Draw box outline
        for x in range(x1, x2 + 1):
            if y1 < grid_height:
                grid[y1][x] = "-"
            if y2 < grid_height:
                grid[y2][x] = "-"

        for y in range(y1, y2 + 1):
            if x1 < grid_width:
                grid[y][x1] = "|"
            if x2 < grid_width:
                grid[y][x2] = "|"

        # Draw corners
        if y1 < grid_height and x1 < grid_width:
            grid[y1][x1] = "+"
        if y1 < grid_height and x2 < grid_width:
            grid[y1][x2] = "+"
        if y2 < grid_height and x1 < grid_width:
            grid[y2][x1] = "+"
        if y2 < grid_height and x2 < grid_width:
            grid[y2][x2] = "+"

        # Add label inside piece (if space permits)
        piece = placement.piece
        label_row = y1 + 1
        dims_row = y1 + 2

        if label_row < y2 and label_row < grid_height:
            label = piece.label[: x2 - x1 - 2]  # Truncate to fit
            if len(label) > 0 and x1 + 1 + len(label) <= x2:
                for i, char in enumerate(label):
                    if x1 + 1 + i < x2:
                        grid[label_row][x1 + 1 + i] = char

        if dims_row < y2 and dims_row < grid_height:
            dims = f"{piece.width:.0f}x{piece.height:.0f}"
            if placement.rotated:
                dims += "R"
            dims = dims[: x2 - x1 - 2]  # Truncate to fit
            if len(dims) > 0 and x1 + 1 + len(dims) <= x2:
                for i, char in enumerate(dims):
                    if x1 + 1 + i < x2:
                        grid[dims_row][x1 + 1 + i] = char

    def render_all_ascii(
        self,
        result: PackingResult,
        width: int = 80,
    ) -> str:
        """Generate ASCII cut diagrams for all sheets.

        Args:
            result: Complete packing result.
            width: Terminal width in characters.

        Returns:
            Combined ASCII string with all sheets.
        """
        if not result.layouts:
            return "No sheets to display."

        total_sheets = len(result.layouts)
        parts: list[str] = []

        for layout in result.layouts:
            parts.append(self.render_ascii(layout, width, total_sheets))
            parts.append("")  # Blank line between sheets

        # Add summary
        parts.append("=" * width)
        parts.append(
            f"SUMMARY: {total_sheets} sheet{'s' if total_sheets != 1 else ''}, "
            f"{result.total_waste_percentage:.1f}% total waste"
        )

        for material, count in result.sheets_by_material.items():
            material_desc = f'{material.thickness}" {material.material_type.value}'
            parts.append(f"  {material_desc}: {count} sheet{'s' if count != 1 else ''}")

        return "\n".join(parts)

    def render_waste_summary(self, result: PackingResult) -> str:
        """Generate text summary of waste and sheet usage.

        Args:
            result: Complete packing result.

        Returns:
            Formatted summary string.
        """
        lines: list[str] = [
            "CUT OPTIMIZATION SUMMARY",
            "=" * 40,
            f"Total Sheets: {result.total_sheets}",
            f"Total Waste: {result.total_waste_percentage:.1f}%",
            "",
            "Sheets by Material:",
        ]

        for material, count in result.sheets_by_material.items():
            material_desc = f'{material.thickness}" {material.material_type.value}'
            lines.append(f"  {material_desc}: {count} sheet{'s' if count != 1 else ''}")

        lines.append("")
        lines.append("Per-Sheet Details:")

        for layout in result.layouts:
            material_desc = (
                f'{layout.material.thickness}" {layout.material.material_type.value}'
            )
            lines.append(
                f"  Sheet {layout.sheet_index + 1}: "
                f"{layout.piece_count} piece{'s' if layout.piece_count != 1 else ''}, "
                f"{layout.waste_percentage:.1f}% waste ({material_desc})"
            )

        if result.offcuts:
            lines.append("")
            lines.append(f"Reusable Offcuts: {len(result.offcuts)}")
            for offcut in result.offcuts:
                lines.append(
                    f'  {offcut.width:.1f}" x {offcut.height:.1f}" '
                    f'({offcut.material.thickness}" {offcut.material.material_type.value})'
                )

        return "\n".join(lines)
