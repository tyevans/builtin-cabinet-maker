"""DXF format exporter for cabinet layouts.

Generates 2D DXF files (R2010 format) for CNC machining and manufacturing.
Supports per-panel and combined output modes, with 32mm system shelf pin holes.
"""

from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

import ezdxf

from cabinets.domain.value_objects import CutPiece, JointType, PanelType
from cabinets.infrastructure.exporters.base import ExporterRegistry

if TYPE_CHECKING:
    from ezdxf.document import Drawing
    from ezdxf.layouts import Modelspace

    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput


logger = logging.getLogger(__name__)


# Layer configuration for DXF output
LAYERS = {
    "OUTLINE": {"color": 7, "linetype": "CONTINUOUS"},  # White - panel outlines
    "DADOS": {"color": 1, "linetype": "DASHED"},  # Red - dado cuts
    "HOLES": {"color": 3, "linetype": "CONTINUOUS"},  # Green - shelf pin holes
    "LABELS": {"color": 5, "linetype": "CONTINUOUS"},  # Blue - text labels
}

# 32mm system constants (in inches for internal use)
MM_TO_INCH = 1 / 25.4
SHELF_PIN_HOLE_DIAMETER_MM = 5.0  # Standard 5mm shelf pin holes
SHELF_PIN_SPACING_MM = 32.0  # 32mm system spacing
SHELF_PIN_EDGE_OFFSET_MM = 37.0  # Standard distance from panel edge to first hole


@ExporterRegistry.register("dxf")
class DxfExporter:
    """Exports cabinet layouts to DXF format for CNC machining.

    Generates 2D panel drawings with outlines, dado positions, shelf pin holes,
    and labels. Supports both per-panel and combined output modes.

    Attributes:
        format_name: "dxf"
        file_extension: "dxf"
    """

    format_name: ClassVar[str] = "dxf"
    file_extension: ClassVar[str] = "dxf"

    def __init__(
        self,
        mode: str = "combined",
        units: str = "inches",
        hole_pattern: str = "32mm",
        hole_diameter: float | None = None,
        panel_spacing: float = 2.0,
        panels_per_row: int = 4,
    ) -> None:
        """Initialize the DXF exporter.

        Args:
            mode: Output mode - "combined" for all panels in one file,
                  "per_panel" for separate files per panel.
            units: Output units - "inches" or "mm".
            hole_pattern: Shelf pin hole pattern - "32mm" or "none".
            hole_diameter: Custom hole diameter in output units. If None,
                          uses 5mm (standard for 32mm system).
            panel_spacing: Space between panels in combined mode (in output units).
            panels_per_row: Number of panels per row in combined mode.
        """
        if mode not in ("combined", "per_panel"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'combined' or 'per_panel'")
        if units not in ("inches", "mm"):
            raise ValueError(f"Invalid units: {units}. Must be 'inches' or 'mm'")
        if hole_pattern not in ("32mm", "none"):
            raise ValueError(
                f"Invalid hole_pattern: {hole_pattern}. Must be '32mm' or 'none'"
            )

        self.mode = mode
        self.units = units
        self.scale = 25.4 if units == "mm" else 1.0
        self.hole_pattern = hole_pattern

        # Convert hole diameter to output units
        if hole_diameter is not None:
            self.hole_diameter = hole_diameter
        else:
            # Default 5mm holes converted to output units
            self.hole_diameter = SHELF_PIN_HOLE_DIAMETER_MM * MM_TO_INCH * self.scale

        self.panel_spacing = panel_spacing
        self.panels_per_row = panels_per_row

        # 32mm system constants in output units
        self._hole_spacing = SHELF_PIN_SPACING_MM * MM_TO_INCH * self.scale
        self._edge_offset = SHELF_PIN_EDGE_OFFSET_MM * MM_TO_INCH * self.scale

    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export layout output to DXF file(s).

        In combined mode, creates a single DXF file with all panels arranged
        in a grid layout. In per-panel mode, creates separate files for each
        unique panel, named {path_stem}_{panel_label}.dxf.

        Args:
            output: The layout output to export.
            path: Path where the DXF file(s) will be saved.
        """
        # Import here to avoid circular imports at module level
        from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput

        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
        elif isinstance(output, LayoutOutput):
            cut_list = output.cut_list
        else:
            raise TypeError(
                f"Expected LayoutOutput or RoomLayoutOutput, got {type(output).__name__}"
            )

        if not cut_list:
            logger.warning("No cut pieces to export")
            return

        if self.mode == "combined":
            self._export_combined(cut_list, path)
        else:
            self._export_per_panel(cut_list, path)

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Export layout output as DXF string.

        Note: DXF string export is provided for convenience but is not
        the typical use case. DXF files are usually written directly to disk.

        Args:
            output: The layout output to export.

        Returns:
            DXF file content as a string.
        """
        # Import here to avoid circular imports at module level
        from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput

        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
        elif isinstance(output, LayoutOutput):
            cut_list = output.cut_list
        else:
            raise TypeError(
                f"Expected LayoutOutput or RoomLayoutOutput, got {type(output).__name__}"
            )

        if not cut_list:
            return ""

        doc = self._create_document()
        msp = doc.modelspace()
        self._draw_all_panels(msp, cut_list)

        # Write to string buffer
        stream = StringIO()
        doc.write(stream)
        return stream.getvalue()

    def format_for_console(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """DXF format does not support console output.

        DXF is a CAD format not suitable for terminal display.

        Raises:
            NotImplementedError: Always raises this exception.
        """
        raise NotImplementedError(
            "DXF format is not suitable for console display. "
            "Use export() to write to a file instead."
        )

    def _create_document(self) -> Drawing:
        """Create a new DXF document with layers configured.

        Returns:
            Configured DXF document.
        """
        doc = ezdxf.new("R2010")
        self._setup_layers(doc)
        return doc

    def _setup_layers(self, doc: Drawing) -> None:
        """Create DXF layers with appropriate colors and linetypes.

        Args:
            doc: DXF document to add layers to.
        """
        for name, props in LAYERS.items():
            layer = doc.layers.add(name, color=cast(int, props["color"]))
            # Note: DASHED linetype needs to be loaded from standard linetypes
            if props["linetype"] == "DASHED":
                # Load standard linetypes if not already present
                if "DASHED" not in doc.linetypes:
                    doc.linetypes.add(
                        "DASHED",
                        pattern=[0.5, 0.25, -0.25],
                        description="Dashed line",
                    )
                layer.dxf.linetype = "DASHED"

    def _export_combined(self, cut_list: list[CutPiece], path: Path) -> None:
        """Export all panels to a single combined DXF file.

        Arranges panels in a grid layout with spacing between them.

        Args:
            cut_list: List of cut pieces to export.
            path: Output file path.
        """
        doc = self._create_document()
        msp = doc.modelspace()
        self._draw_all_panels(msp, cut_list)
        doc.saveas(path)
        logger.info(f"Exported combined DXF to {path}")

    def _export_per_panel(self, cut_list: list[CutPiece], path: Path) -> None:
        """Export each unique panel to a separate DXF file.

        Creates files named {path_stem}_{panel_label}.dxf for each unique panel.

        Args:
            cut_list: List of cut pieces to export.
            path: Base output path (will be modified to include panel label).
        """
        path_stem = path.stem
        path_parent = path.parent

        for piece in cut_list:
            doc = self._create_document()
            msp = doc.modelspace()

            # Draw single panel at origin
            self._draw_panel(msp, piece, 0.0, 0.0)

            # Create panel-specific filename
            # Sanitize label for filename
            safe_label = piece.label.replace(" ", "_").replace("/", "-")
            panel_path = path_parent / f"{path_stem}_{safe_label}.dxf"
            doc.saveas(panel_path)
            logger.info(f"Exported panel DXF to {panel_path}")

    def _draw_all_panels(self, msp: Modelspace, cut_list: list[CutPiece]) -> None:
        """Draw all panels in a grid layout.

        Arranges panels left-to-right, top-to-bottom with configured spacing.
        Uses a two-pass approach to prevent overlapping panels.

        Args:
            msp: DXF modelspace to draw in.
            cut_list: List of cut pieces to draw.
        """
        # First pass: expand cut list and calculate row assignments
        expanded_panels: list[
            tuple[CutPiece, float, float]
        ] = []  # (piece, width, height)
        for piece in cut_list:
            width = piece.width * self.scale
            height = piece.height * self.scale
            for _ in range(piece.quantity):
                expanded_panels.append((piece, width, height))

        # Calculate row heights
        rows: list[list[tuple[CutPiece, float, float]]] = []
        current_row: list[tuple[CutPiece, float, float]] = []

        for panel in expanded_panels:
            if len(current_row) >= self.panels_per_row:
                rows.append(current_row)
                current_row = []
            current_row.append(panel)

        if current_row:
            rows.append(current_row)

        # Second pass: draw panels with correct Y offsets
        # Use current_y as the TOP of each row, panels extend downward
        current_y = 0.0

        for row in rows:
            # Find the maximum height in this row
            row_height = max(panel[2] for panel in row)

            # Calculate the bottom of this row (panels will be drawn from bottom up)
            row_bottom = current_y - row_height

            # Draw all panels in this row at the same baseline (row_bottom)
            current_x = 0.0
            for piece, width, height in row:
                self._draw_panel(msp, piece, current_x, row_bottom)
                current_x += width + self.panel_spacing

            # Next row's top is below this row's bottom
            current_y = row_bottom - self.panel_spacing

    def _draw_panel(
        self, msp: Modelspace, piece: CutPiece, offset_x: float, offset_y: float
    ) -> None:
        """Draw a single panel with outline, dados, holes, and label.

        Args:
            msp: DXF modelspace to draw in.
            piece: Cut piece to draw.
            offset_x: X offset for panel position.
            offset_y: Y offset for panel position.
        """
        width = piece.width * self.scale
        height = piece.height * self.scale

        # Draw panel components
        self._draw_outline(msp, offset_x, offset_y, width, height)
        self._draw_dados(msp, piece, offset_x, offset_y, width, height)
        self._draw_holes(msp, piece, offset_x, offset_y, width, height)
        self._draw_label(msp, piece, offset_x, offset_y, width, height)

    def _draw_outline(
        self, msp: Modelspace, x: float, y: float, width: float, height: float
    ) -> None:
        """Draw panel outline as closed polyline.

        Args:
            msp: DXF modelspace to draw in.
            x: X position of bottom-left corner.
            y: Y position of bottom-left corner.
            width: Panel width.
            height: Panel height.
        """
        points = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
            (x, y),  # Close the polyline
        ]
        msp.add_lwpolyline(points, dxfattribs={"layer": "OUTLINE"})

    def _draw_dados(
        self,
        msp: Modelspace,
        piece: CutPiece,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw dado cuts from joinery data in piece metadata.

        Dados are grooves cut into panels to receive shelves or dividers.
        The position and dimensions are extracted from the cut_metadata.

        Args:
            msp: DXF modelspace to draw in.
            piece: Cut piece with potential dado metadata.
            x: X position of panel bottom-left corner.
            y: Y position of panel bottom-left corner.
            width: Panel width in output units.
            height: Panel height in output units.
        """
        if not piece.cut_metadata:
            return

        # Check for joinery data in metadata
        joinery = piece.cut_metadata.get("joinery", [])
        if not joinery:
            return

        for joint in joinery:
            joint_type = joint.get("type")
            if joint_type != JointType.DADO.value and joint_type != "dado":
                continue

            # Get dado position and dimensions
            position = joint.get("position", 0.0) * self.scale
            dado_width = joint.get("width", 0.75) * self.scale
            orientation = joint.get("orientation", "horizontal")

            if orientation == "horizontal":
                # Horizontal dado (for shelves in side panels)
                # Draw as two lines representing the dado groove
                y_pos = y + position
                msp.add_line(
                    (x, y_pos),
                    (x + width, y_pos),
                    dxfattribs={"layer": "DADOS"},
                )
                msp.add_line(
                    (x, y_pos + dado_width),
                    (x + width, y_pos + dado_width),
                    dxfattribs={"layer": "DADOS"},
                )
            else:
                # Vertical dado (for dividers in top/bottom panels)
                x_pos = x + position
                msp.add_line(
                    (x_pos, y),
                    (x_pos, y + height),
                    dxfattribs={"layer": "DADOS"},
                )
                msp.add_line(
                    (x_pos + dado_width, y),
                    (x_pos + dado_width, y + height),
                    dxfattribs={"layer": "DADOS"},
                )

    def _draw_holes(
        self,
        msp: Modelspace,
        piece: CutPiece,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw shelf pin holes using 32mm system.

        Only draws holes for side panels (left_side, right_side) and dividers.
        Holes are placed along the inside edge at 32mm intervals.

        Args:
            msp: DXF modelspace to draw in.
            piece: Cut piece to draw holes for.
            x: X position of panel bottom-left corner.
            y: Y position of panel bottom-left corner.
            width: Panel width in output units.
            height: Panel height in output units.
        """
        if self.hole_pattern == "none":
            return

        # Only draw holes for side panels and dividers
        hole_panel_types = {
            PanelType.LEFT_SIDE,
            PanelType.RIGHT_SIDE,
            PanelType.DIVIDER,
        }

        if piece.panel_type not in hole_panel_types:
            return

        # Calculate hole positions using 32mm system
        # Holes are placed at a fixed distance from the front and back edges
        # and spaced every 32mm vertically

        # Edge offsets (distance from front/back edge to hole line)
        front_edge_offset = self._edge_offset
        back_edge_offset = width - self._edge_offset

        # Vertical range for holes
        # Start 37mm from bottom and top edges
        start_y = y + self._edge_offset
        end_y = y + height - self._edge_offset

        # Generate hole positions along vertical lines
        current_y = start_y
        while current_y <= end_y:
            # Front line of holes
            self._draw_hole(msp, x + front_edge_offset, current_y)
            # Back line of holes
            self._draw_hole(msp, x + back_edge_offset, current_y)

            current_y += self._hole_spacing

    def _draw_hole(self, msp: Modelspace, cx: float, cy: float) -> None:
        """Draw a single shelf pin hole as a circle.

        Args:
            msp: DXF modelspace to draw in.
            cx: X center of hole.
            cy: Y center of hole.
        """
        radius = self.hole_diameter / 2
        msp.add_circle((cx, cy), radius, dxfattribs={"layer": "HOLES"})

    def _draw_label(
        self,
        msp: Modelspace,
        piece: CutPiece,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Draw piece label with dimensions centered in panel.

        The label includes the piece label and dimensions in the format:
        "Label\nW x H"

        Args:
            msp: DXF modelspace to draw in.
            piece: Cut piece to label.
            x: X position of panel bottom-left corner.
            y: Y position of panel bottom-left corner.
            width: Panel width in output units.
            height: Panel height in output units.
        """
        # Calculate center position
        center_x = x + width / 2
        center_y = y + height / 2

        # Format dimension text
        if self.units == "mm":
            dim_text = (
                f"{piece.width * self.scale:.1f} x {piece.height * self.scale:.1f} mm"
            )
        else:
            dim_text = f'{piece.width:.3f}" x {piece.height:.3f}"'

        label_text = f"{piece.label}\n{dim_text}"

        # Calculate text height based on panel size
        # Use 5% of the smaller dimension, with min/max limits
        min_text_height = 0.15 * self.scale  # 0.15" or ~4mm minimum
        max_text_height = 1.0 * self.scale  # 1" or 25mm maximum
        text_height = max(
            min_text_height, min(max_text_height, min(width, height) * 0.08)
        )

        # Add multiline text centered in panel
        msp.add_mtext(
            label_text,
            dxfattribs={
                "layer": "LABELS",
                "char_height": text_height,
                "insert": (center_x, center_y),
                "attachment_point": 5,  # MIDDLE_CENTER
            },
        )


# Export for backwards compatibility
__all__ = ["DxfExporter", "LAYERS"]
