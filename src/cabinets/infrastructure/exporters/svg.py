"""SVG exporter for cut diagrams.

This module provides an SVG exporter that wraps CutDiagramRenderer
to generate cut layout diagrams as SVG files. It requires bin packing
results to be available in the layout output.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from cabinets.infrastructure.cut_diagram_renderer import CutDiagramRenderer
from cabinets.infrastructure.exporters.base import ExporterRegistry

if TYPE_CHECKING:
    from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput


@ExporterRegistry.register("svg")
class SvgExporter:
    """SVG exporter for cut layout diagrams.

    Generates SVG visualizations of sheet layouts showing piece
    placements, dimensions, rotation indicators, and waste areas.

    Requires bin packing results to be available in the layout output.
    Use the --optimize flag or configure bin_packing in the config file.

    Attributes:
        format_name: Identifier for this export format.
        file_extension: File extension for SVG files.
    """

    format_name: ClassVar[str] = "svg"
    file_extension: ClassVar[str] = "svg"

    def __init__(
        self,
        scale: float = 10.0,
        show_dimensions: bool = True,
        show_labels: bool = True,
        show_grain: bool = False,
        use_panel_colors: bool = True,
    ) -> None:
        """Initialize the SVG exporter.

        Args:
            scale: Pixels per inch for SVG rendering (default 10.0).
            show_dimensions: Whether to show piece dimensions (default True).
            show_labels: Whether to show piece labels (default True).
            show_grain: Whether to show grain direction arrows (default False).
            use_panel_colors: Whether to color pieces by panel type (default True).
        """
        self.renderer = CutDiagramRenderer(
            scale=scale,
            show_dimensions=show_dimensions,
            show_labels=show_labels,
            show_grain=show_grain,
            use_panel_colors=use_panel_colors,
        )

    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export SVG cut diagrams to file.

        Generates a combined SVG containing all sheets stacked vertically.

        Args:
            output: The layout output containing packing results.
            path: Path where the SVG file will be saved.

        Raises:
            ValueError: If bin packing results are not available.
        """
        packing_result = getattr(output, "packing_result", None)
        if packing_result is None:
            raise ValueError(
                "SVG export requires bin packing results. "
                "Use --optimize flag or configure bin_packing in the config file."
            )

        svg_content = self.renderer.render_combined_svg(packing_result)
        path.write_text(svg_content)

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Export SVG as string.

        Args:
            output: The layout output containing packing results.

        Returns:
            SVG content as a string.

        Raises:
            ValueError: If bin packing results are not available.
        """
        packing_result = getattr(output, "packing_result", None)
        if packing_result is None:
            raise ValueError(
                "SVG export requires bin packing results. "
                "Use --optimize flag or configure bin_packing in the config file."
            )

        return self.renderer.render_combined_svg(packing_result)

    def export_individual_sheets(
        self, output: LayoutOutput | RoomLayoutOutput, base_path: Path
    ) -> list[Path]:
        """Export individual SVG files for each sheet.

        Creates separate SVG files for each sheet, named with a numeric suffix.

        Args:
            output: The layout output containing packing results.
            base_path: Base path for output files. Files will be named
                      {stem}_1.svg, {stem}_2.svg, etc.

        Returns:
            List of paths to the created files.

        Raises:
            ValueError: If bin packing results are not available.
        """
        packing_result = getattr(output, "packing_result", None)
        if packing_result is None:
            raise ValueError(
                "SVG export requires bin packing results. "
                "Use --optimize flag or configure bin_packing in the config file."
            )

        svgs = self.renderer.render_all_svg(packing_result)
        created_files: list[Path] = []

        for i, svg_content in enumerate(svgs, start=1):
            if len(svgs) == 1:
                file_path = base_path
            else:
                stem = base_path.stem
                suffix = base_path.suffix or ".svg"
                file_path = base_path.parent / f"{stem}_{i}{suffix}"

            file_path.write_text(svg_content)
            created_files.append(file_path)

        return created_files
