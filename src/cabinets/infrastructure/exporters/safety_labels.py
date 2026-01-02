"""Safety label SVG exporter for cabinet safety documentation.

This module generates printable SVG safety labels for cabinet
weight capacity, anti-tip warnings, installation guidance,
and material information.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar
from xml.etree import ElementTree as ET

from cabinets.domain.services.safety import SafetyLabel
from cabinets.infrastructure.exporters.base import ExporterRegistry

if TYPE_CHECKING:
    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput


@dataclass
class LabelStyle:
    """Styling configuration for safety labels."""

    background_color: str = "#ffffff"
    border_color: str = "#000000"
    border_width: float = 2.0
    warning_color: str = "#ffcc00"
    error_color: str = "#ff0000"
    text_color: str = "#000000"
    title_font_size: float = 18.0
    body_font_size: float = 12.0
    font_family: str = "Arial, Helvetica, sans-serif"


@ExporterRegistry.register("safety-labels")
class SafetyLabelExporter:
    """Exporter for generating SVG safety labels.

    Creates printable safety labels in SVG format with configurable
    dimensions and styling. Labels are designed for printing at
    standard label sizes.

    Attributes:
        format_name: Identifier for this export format.
        file_extension: File extension for SVG files.

    Example:
        ```python
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="weight_capacity",
            title="MAXIMUM LOAD",
            body_text="Do not exceed 45 lbs per shelf.",
            warning_icon=True,
            dimensions=(4.0, 3.0)
        )
        svg_content = exporter.export_label(label)
        with open("weight_label.svg", "w") as f:
            f.write(svg_content)
        ```
    """

    format_name: ClassVar[str] = "safety-labels"
    file_extension: ClassVar[str] = "svg"

    # DPI for print calculations
    DPI: int = 96  # SVG standard

    def __init__(self, style: LabelStyle | None = None) -> None:
        """Initialize exporter with optional style.

        Args:
            style: Label styling configuration.
        """
        self.style = style or LabelStyle()

    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export safety labels from layout output to file.

        Generates a combined SVG containing all safety labels stacked vertically.

        Args:
            output: The layout output containing safety assessment.
            path: Path where the SVG file will be saved.

        Raises:
            ValueError: If safety assessment is not available.
        """
        safety_assessment = getattr(output, "safety_assessment", None)
        if safety_assessment is None:
            raise ValueError(
                "Safety label export requires safety assessment. "
                "Enable safety checking in the configuration."
            )

        labels = safety_assessment.safety_labels
        if not labels:
            raise ValueError(
                "No safety labels to export. "
                "Ensure generate_labels is enabled in safety configuration."
            )

        svg_content = self._render_combined_labels(labels)
        path.write_text(svg_content)

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Export safety labels as a combined SVG string.

        Args:
            output: The layout output containing safety assessment.

        Returns:
            SVG content as a string.

        Raises:
            ValueError: If safety assessment is not available.
        """
        safety_assessment = getattr(output, "safety_assessment", None)
        if safety_assessment is None:
            raise ValueError(
                "Safety label export requires safety assessment. "
                "Enable safety checking in the configuration."
            )

        labels = safety_assessment.safety_labels
        if not labels:
            raise ValueError(
                "No safety labels to export. "
                "Ensure generate_labels is enabled in safety configuration."
            )

        return self._render_combined_labels(labels)

    def format_for_console(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Safety labels format does not support console output.

        Safety labels are SVG graphics not suitable for terminal display.

        Raises:
            NotImplementedError: Always raises this exception.
        """
        raise NotImplementedError(
            "Safety labels are graphical SVG and do not support console output. "
            "Use export() to write to a file instead."
        )

    def export_label(self, label: SafetyLabel) -> str:
        """Export a single safety label to SVG.

        Args:
            label: SafetyLabel to export.

        Returns:
            SVG content as string.
        """
        width_px = label.width_inches * self.DPI
        height_px = label.height_inches * self.DPI

        # Create SVG root
        svg = ET.Element(
            "svg",
            xmlns="http://www.w3.org/2000/svg",
            width=f"{width_px}",
            height=f"{height_px}",
            viewBox=f"0 0 {width_px} {height_px}",
        )

        # Add defs for reusable elements
        defs = ET.SubElement(svg, "defs")
        self._add_warning_icon_def(defs)

        # Background
        ET.SubElement(
            svg,
            "rect",
            x="0",
            y="0",
            width=f"{width_px}",
            height=f"{height_px}",
            fill=self.style.background_color,
            stroke=self.style.border_color,
        )
        # Set stroke-width separately to avoid Python keyword conflict
        svg[-1].set("stroke-width", str(self.style.border_width))

        # Content based on label type
        if label.label_type == "anti_tip":
            self._render_anti_tip_label(svg, label, width_px, height_px)
        elif label.label_type == "weight_capacity":
            self._render_weight_capacity_label(svg, label, width_px, height_px)
        elif label.label_type == "installation":
            self._render_installation_label(svg, label, width_px, height_px)
        elif label.label_type == "material":
            self._render_material_label(svg, label, width_px, height_px)
        else:
            self._render_generic_label(svg, label, width_px, height_px)

        # Return SVG as string
        return ET.tostring(svg, encoding="unicode")

    def export_all_labels(
        self,
        labels: list[SafetyLabel],
    ) -> dict[str, str]:
        """Export multiple labels to SVG.

        Args:
            labels: List of SafetyLabels to export.

        Returns:
            Dictionary mapping label type to SVG content.
        """
        return {label.label_type: self.export_label(label) for label in labels}

    def _render_combined_labels(self, labels: list[SafetyLabel]) -> str:
        """Render multiple labels as a single combined SVG.

        Labels are stacked vertically with spacing between them.

        Args:
            labels: List of labels to render.

        Returns:
            Combined SVG string.
        """
        if not labels:
            return ""

        spacing = 20  # pixels between labels
        total_width = max(label.width_inches * self.DPI for label in labels)
        total_height = sum(label.height_inches * self.DPI for label in labels)
        total_height += spacing * (len(labels) - 1)

        # Create combined SVG root
        combined_svg = ET.Element(
            "svg",
            xmlns="http://www.w3.org/2000/svg",
            width=f"{total_width}",
            height=f"{total_height}",
            viewBox=f"0 0 {total_width} {total_height}",
        )

        # Add defs for reusable elements
        defs = ET.SubElement(combined_svg, "defs")
        self._add_warning_icon_def(defs)

        # Position each label
        current_y = 0.0
        for label in labels:
            label_width = label.width_inches * self.DPI
            label_height = label.height_inches * self.DPI

            # Create group for this label
            g = ET.SubElement(
                combined_svg,
                "g",
                transform=f"translate(0, {current_y})",
            )

            # Background
            bg = ET.SubElement(
                g,
                "rect",
                x="0",
                y="0",
                width=f"{label_width}",
                height=f"{label_height}",
                fill=self.style.background_color,
                stroke=self.style.border_color,
            )
            bg.set("stroke-width", str(self.style.border_width))

            # Content based on label type
            if label.label_type == "anti_tip":
                self._render_anti_tip_label(g, label, label_width, label_height)
            elif label.label_type == "weight_capacity":
                self._render_weight_capacity_label(g, label, label_width, label_height)
            elif label.label_type == "installation":
                self._render_installation_label(g, label, label_width, label_height)
            elif label.label_type == "material":
                self._render_material_label(g, label, label_width, label_height)
            else:
                self._render_generic_label(g, label, label_width, label_height)

            current_y += label_height + spacing

        return ET.tostring(combined_svg, encoding="unicode")

    def _add_warning_icon_def(self, defs: ET.Element) -> None:
        """Add warning triangle icon definition."""
        symbol = ET.SubElement(
            defs,
            "symbol",
            id="warning-icon",
            viewBox="0 0 24 24",
        )
        # Warning triangle path
        path = ET.SubElement(
            symbol,
            "path",
            d="M12 2L1 21h22L12 2z",
            fill=self.style.warning_color,
            stroke=self.style.border_color,
        )
        path.set("stroke-width", "1")
        # Exclamation mark
        text = ET.SubElement(
            symbol,
            "text",
            x="12",
            y="18",
        )
        text.set("text-anchor", "middle")
        text.set("font-size", "12")
        text.set("font-weight", "bold")
        text.set("fill", self.style.border_color)
        text.text = "!"

    def _render_anti_tip_label(
        self,
        svg: ET.Element,
        label: SafetyLabel,
        width: float,
        height: float,
    ) -> None:
        """Render anti-tip warning label."""
        padding = 10
        current_y = padding + 10

        # Warning band at top
        ET.SubElement(
            svg,
            "rect",
            x="0",
            y="0",
            width=str(width),
            height="40",
            fill=self.style.warning_color,
        )

        # Warning icon
        if label.warning_icon:
            ET.SubElement(
                svg,
                "use",
                href="#warning-icon",
                x=str(padding),
                y="8",
                width="24",
                height="24",
            )

        # WARNING text
        warning_text = ET.SubElement(
            svg,
            "text",
            x=str(width / 2),
            y="28",
        )
        warning_text.set("text-anchor", "middle")
        warning_text.set("font-size", str(self.style.title_font_size + 2))
        warning_text.set("font-weight", "bold")
        warning_text.set("fill", self.style.border_color)
        warning_text.set("font-family", self.style.font_family)
        warning_text.text = "WARNING"

        current_y = 55

        # Title
        title_text = ET.SubElement(
            svg,
            "text",
            x=str(width / 2),
            y=str(current_y),
        )
        title_text.set("text-anchor", "middle")
        title_text.set("font-size", str(self.style.title_font_size))
        title_text.set("font-weight", "bold")
        title_text.set("fill", self.style.border_color)
        title_text.set("font-family", self.style.font_family)
        title_text.text = label.title

        current_y += 25

        # Body text (wrapped)
        self._render_wrapped_text(svg, label.body_text, width, current_y, padding)

    def _render_weight_capacity_label(
        self,
        svg: ET.Element,
        label: SafetyLabel,
        width: float,
        height: float,
    ) -> None:
        """Render weight capacity label."""
        padding = 10
        current_y = padding + 20

        # Warning icon if specified
        if label.warning_icon:
            ET.SubElement(
                svg,
                "use",
                href="#warning-icon",
                x=str(padding),
                y=str(current_y - 15),
                width="24",
                height="24",
            )

        # Title
        title_text = ET.SubElement(
            svg,
            "text",
            x=str(width / 2),
            y=str(current_y),
        )
        title_text.set("text-anchor", "middle")
        title_text.set("font-size", str(self.style.title_font_size))
        title_text.set("font-weight", "bold")
        title_text.set("fill", self.style.border_color)
        title_text.set("font-family", self.style.font_family)
        title_text.text = label.title

        current_y += 25

        # Horizontal line
        line = ET.SubElement(
            svg,
            "line",
            x1=str(padding),
            y1=str(current_y),
            x2=str(width - padding),
            y2=str(current_y),
            stroke=self.style.border_color,
        )
        line.set("stroke-width", "1")

        current_y += 15

        # Body text
        self._render_wrapped_text(svg, label.body_text, width, current_y, padding)

    def _render_installation_label(
        self,
        svg: ET.Element,
        label: SafetyLabel,
        width: float,
        height: float,
    ) -> None:
        """Render installation guidance label."""
        padding = 10
        current_y = padding + 20

        # Title
        title_text = ET.SubElement(
            svg,
            "text",
            x=str(width / 2),
            y=str(current_y),
        )
        title_text.set("text-anchor", "middle")
        title_text.set("font-size", str(self.style.title_font_size))
        title_text.set("font-weight", "bold")
        title_text.set("fill", self.style.border_color)
        title_text.set("font-family", self.style.font_family)
        title_text.text = label.title

        current_y += 20

        # Body text (bullet points)
        for line in label.body_text.split("\n"):
            if line.strip():
                line_text = ET.SubElement(
                    svg,
                    "text",
                    x=str(padding + 5),
                    y=str(current_y),
                )
                line_text.set("font-size", str(self.style.body_font_size))
                line_text.set("fill", self.style.text_color)
                line_text.set("font-family", self.style.font_family)
                line_text.text = line.strip()
                current_y += 18

    def _render_material_label(
        self,
        svg: ET.Element,
        label: SafetyLabel,
        width: float,
        height: float,
    ) -> None:
        """Render material information label."""
        self._render_generic_label(svg, label, width, height)

    def _render_generic_label(
        self,
        svg: ET.Element,
        label: SafetyLabel,
        width: float,
        height: float,
    ) -> None:
        """Render generic label layout."""
        padding = 10
        current_y = padding + 20

        # Warning icon if needed
        icon_offset = 0
        if label.warning_icon:
            ET.SubElement(
                svg,
                "use",
                href="#warning-icon",
                x=str(padding),
                y=str(current_y - 15),
                width="24",
                height="24",
            )
            icon_offset = 30

        # Title
        title_text = ET.SubElement(
            svg,
            "text",
            x=str(padding + icon_offset),
            y=str(current_y),
        )
        title_text.set("font-size", str(self.style.title_font_size))
        title_text.set("font-weight", "bold")
        title_text.set("fill", self.style.border_color)
        title_text.set("font-family", self.style.font_family)
        title_text.text = label.title

        current_y += 25

        # Body text
        self._render_wrapped_text(svg, label.body_text, width, current_y, padding)

    def _render_wrapped_text(
        self,
        svg: ET.Element,
        text: str,
        width: float,
        start_y: float,
        padding: float,
    ) -> None:
        """Render text with line wrapping.

        Args:
            svg: SVG element to add text to.
            text: Text to render.
            width: Available width in pixels.
            start_y: Starting Y position.
            padding: Horizontal padding.
        """
        available_width = width - (2 * padding)
        chars_per_line = int(available_width / (self.style.body_font_size * 0.5))
        current_y = start_y

        for paragraph in text.split("\n"):
            if not paragraph.strip():
                current_y += 10
                continue

            words = paragraph.split()
            lines: list[str] = []
            current_line: list[str] = []

            for word in words:
                test_line = " ".join(current_line + [word])
                if len(test_line) <= chars_per_line:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(" ".join(current_line))

            for line in lines:
                line_text = ET.SubElement(
                    svg,
                    "text",
                    x=str(padding),
                    y=str(current_y),
                )
                line_text.set("font-size", str(self.style.body_font_size))
                line_text.set("fill", self.style.text_color)
                line_text.set("font-family", self.style.font_family)
                line_text.text = line
                current_y += self.style.body_font_size + 4
