"""Unit tests for SafetyLabelExporter (FRD-21 Task 10)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


from cabinets.domain.services.safety import SafetyLabel
from cabinets.infrastructure.exporters import ExporterRegistry
from cabinets.infrastructure.exporters.safety_labels import (
    LabelStyle,
    SafetyLabelExporter,
)


class TestSafetyLabelExporterRegistration:
    """Tests for exporter registration."""

    def test_exporter_is_registered(self) -> None:
        """SafetyLabelExporter is registered in ExporterRegistry."""
        assert ExporterRegistry.is_registered("safety-labels")

    def test_exporter_can_be_retrieved(self) -> None:
        """SafetyLabelExporter can be retrieved from registry."""
        exporter_class = ExporterRegistry.get("safety-labels")
        assert exporter_class is SafetyLabelExporter

    def test_available_formats_includes_safety_labels(self) -> None:
        """Available formats includes safety-labels."""
        formats = ExporterRegistry.available_formats()
        assert "safety-labels" in formats

    def test_format_name_attribute(self) -> None:
        """format_name is 'safety-labels'."""
        assert SafetyLabelExporter.format_name == "safety-labels"

    def test_file_extension_attribute(self) -> None:
        """file_extension is 'svg'."""
        assert SafetyLabelExporter.file_extension == "svg"


class TestSafetyLabelExporterInit:
    """Tests for exporter initialization."""

    def test_default_initialization(self) -> None:
        """Default initialization creates exporter with default style."""
        exporter = SafetyLabelExporter()
        assert exporter.style is not None
        assert exporter.style.background_color == "#ffffff"
        assert exporter.style.warning_color == "#ffcc00"

    def test_custom_style_initialization(self) -> None:
        """Custom style is applied during initialization."""
        custom_style = LabelStyle(
            warning_color="#ff6600",
            title_font_size=20.0,
        )
        exporter = SafetyLabelExporter(style=custom_style)
        assert exporter.style.warning_color == "#ff6600"
        assert exporter.style.title_font_size == 20.0


class TestLabelStyle:
    """Tests for LabelStyle dataclass."""

    def test_default_values(self) -> None:
        """LabelStyle has correct default values."""
        style = LabelStyle()
        assert style.background_color == "#ffffff"
        assert style.border_color == "#000000"
        assert style.border_width == 2.0
        assert style.warning_color == "#ffcc00"
        assert style.error_color == "#ff0000"
        assert style.text_color == "#000000"
        assert style.title_font_size == 18.0
        assert style.body_font_size == 12.0
        assert style.font_family == "Arial, Helvetica, sans-serif"

    def test_custom_values(self) -> None:
        """LabelStyle accepts custom values."""
        style = LabelStyle(
            background_color="#f0f0f0",
            warning_color="#ff9900",
            title_font_size=24.0,
        )
        assert style.background_color == "#f0f0f0"
        assert style.warning_color == "#ff9900"
        assert style.title_font_size == 24.0


class TestExportSingleLabel:
    """Tests for exporting single labels."""

    def test_export_anti_tip_label(self) -> None:
        """Export anti_tip label to SVG."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TIP-OVER HAZARD",
            body_text="Must be anchored to wall.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert svg.startswith("<svg")
        assert "TIP-OVER" in svg
        assert "WARNING" in svg

    def test_export_weight_capacity_label(self) -> None:
        """Export weight_capacity label to SVG."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="weight_capacity",
            title="MAXIMUM LOAD",
            body_text="Do not exceed 45 lbs per shelf.",
            warning_icon=True,
            dimensions=(4.0, 2.0),
        )
        svg = exporter.export_label(label)
        assert svg.startswith("<svg")
        assert "MAXIMUM LOAD" in svg
        assert "45 lbs" in svg

    def test_export_installation_label(self) -> None:
        """Export installation label to SVG."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="installation",
            title="INSTALLATION SAFETY",
            body_text="- Secure to wall studs\n- Follow all mounting instructions",
            warning_icon=False,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert svg.startswith("<svg")
        assert "INSTALLATION SAFETY" in svg
        assert "Secure to wall" in svg

    def test_export_material_label(self) -> None:
        """Export material label to SVG."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="material",
            title="MATERIAL INFORMATION",
            body_text="CARB Phase 2 compliant materials used.",
            warning_icon=False,
            dimensions=(4.0, 2.0),
        )
        svg = exporter.export_label(label)
        assert svg.startswith("<svg")
        assert "MATERIAL INFORMATION" in svg
        assert "CARB" in svg


class TestLabelDimensions:
    """Tests for label dimensions."""

    def test_label_dimensions_4x3_at_96_dpi(self) -> None:
        """4x3 inch label at 96 DPI = 384x288 pixels."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TEST",
            body_text="Test body.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        # Float values are output (384.0, 288.0)
        assert 'width="384' in svg
        assert 'height="288' in svg

    def test_label_dimensions_4x2_at_96_dpi(self) -> None:
        """4x2 inch label at 96 DPI = 384x192 pixels."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="weight_capacity",
            title="TEST",
            body_text="Test body.",
            dimensions=(4.0, 2.0),
        )
        svg = exporter.export_label(label)
        # Float values are output (384.0, 192.0)
        assert 'width="384' in svg
        assert 'height="192' in svg

    def test_label_dimensions_2x4_at_96_dpi(self) -> None:
        """2x4 inch label at 96 DPI = 192x384 pixels."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="installation",
            title="TEST",
            body_text="Test body.",
            dimensions=(2.0, 4.0),
        )
        svg = exporter.export_label(label)
        # Float values are output (192.0, 384.0)
        assert 'width="192' in svg
        assert 'height="384' in svg


class TestWarningIcon:
    """Tests for warning icon rendering."""

    def test_warning_icon_included_when_specified(self) -> None:
        """Warning icon included when warning_icon=True."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="WARNING",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "warning-icon" in svg
        assert 'href="#warning-icon"' in svg

    def test_warning_icon_definition_present(self) -> None:
        """Warning icon definition is in defs section."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="WARNING",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert '<symbol id="warning-icon"' in svg
        # Check for warning triangle path
        assert "M12 2L1 21h22L12 2z" in svg


class TestCustomStyling:
    """Tests for custom styling."""

    def test_custom_warning_color_applied(self) -> None:
        """Custom warning color is applied to SVG."""
        style = LabelStyle(warning_color="#ff6600")
        exporter = SafetyLabelExporter(style=style)
        label = SafetyLabel(
            label_type="anti_tip",
            title="WARNING",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "#ff6600" in svg

    def test_custom_font_size_applied(self) -> None:
        """Custom title font size is applied."""
        style = LabelStyle(title_font_size=24.0)
        exporter = SafetyLabelExporter(style=style)
        label = SafetyLabel(
            label_type="weight_capacity",
            title="TEST",
            body_text="Test.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert 'font-size="24' in svg

    def test_custom_font_family_applied(self) -> None:
        """Custom font family is applied."""
        style = LabelStyle(font_family="Times New Roman, serif")
        exporter = SafetyLabelExporter(style=style)
        label = SafetyLabel(
            label_type="weight_capacity",
            title="TEST",
            body_text="Test.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "Times New Roman" in svg


class TestExportMultipleLabels:
    """Tests for exporting multiple labels."""

    def test_export_all_labels(self) -> None:
        """export_all_labels returns dict of SVGs."""
        exporter = SafetyLabelExporter()
        labels = [
            SafetyLabel(
                label_type="anti_tip",
                title="TIP-OVER",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
            SafetyLabel(
                label_type="weight_capacity",
                title="WEIGHT",
                body_text="Test.",
                dimensions=(4.0, 2.0),
            ),
            SafetyLabel(
                label_type="installation",
                title="INSTALL",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
        ]
        results = exporter.export_all_labels(labels)
        assert len(results) == 3
        assert all(svg.startswith("<svg") for svg in results.values())

    def test_export_all_labels_keys_match_types(self) -> None:
        """export_all_labels dict keys match label types."""
        exporter = SafetyLabelExporter()
        labels = [
            SafetyLabel(
                label_type="anti_tip",
                title="TEST",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
            SafetyLabel(
                label_type="material",
                title="TEST",
                body_text="Test.",
                dimensions=(4.0, 2.0),
            ),
        ]
        results = exporter.export_all_labels(labels)
        assert "anti_tip" in results
        assert "material" in results


class TestSvgValidity:
    """Tests for SVG XML validity."""

    def test_svg_validates_as_xml(self) -> None:
        """Exported SVG is valid XML."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TEST",
            body_text="Test body text.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        # Parse as XML - will raise if invalid
        root = ET.fromstring(svg)
        # Tag includes namespace
        assert root.tag.endswith("svg")

    def test_svg_has_proper_namespace(self) -> None:
        """SVG has proper xmlns namespace."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="weight_capacity",
            title="TEST",
            body_text="Test.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_svg_has_viewbox(self) -> None:
        """SVG has viewBox attribute."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="installation",
            title="TEST",
            body_text="Test.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "viewBox=" in svg


class TestTextWrapping:
    """Tests for text wrapping functionality."""

    def test_long_text_is_wrapped(self) -> None:
        """Long body text is wrapped into multiple lines."""
        exporter = SafetyLabelExporter()
        long_text = (
            "This is a very long piece of text that should be wrapped "
            "into multiple lines because it exceeds the available width "
            "of the label. The text should break at word boundaries."
        )
        label = SafetyLabel(
            label_type="anti_tip",
            title="TEST",
            body_text=long_text,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        root = ET.fromstring(svg)
        # Multiple text elements should be created for wrapped text
        text_elements = root.findall(".//{http://www.w3.org/2000/svg}text")
        # Should have more than just title
        assert len(text_elements) > 2

    def test_newlines_preserved(self) -> None:
        """Explicit newlines in body text create separate paragraphs."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="installation",
            title="TEST",
            body_text="Line one.\n\nLine two.\n\nLine three.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "Line one" in svg
        assert "Line two" in svg
        assert "Line three" in svg


class TestAntiTipLabelSpecificFeatures:
    """Tests for anti-tip label specific features."""

    def test_anti_tip_has_warning_band(self) -> None:
        """Anti-tip label has yellow warning band at top."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TIP-OVER HAZARD",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        # Check for yellow rectangle at top (warning band)
        assert 'fill="#ffcc00"' in svg

    def test_anti_tip_has_warning_header(self) -> None:
        """Anti-tip label has 'WARNING' header text."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TIP-OVER HAZARD",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert ">WARNING<" in svg


class TestCombinedLabelExport:
    """Tests for combined label rendering."""

    def test_render_combined_labels_returns_single_svg(self) -> None:
        """Rendering combined labels returns a single SVG."""
        exporter = SafetyLabelExporter()
        labels = [
            SafetyLabel(
                label_type="anti_tip",
                title="TEST1",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
            SafetyLabel(
                label_type="weight_capacity",
                title="TEST2",
                body_text="Test.",
                dimensions=(4.0, 2.0),
            ),
        ]
        svg = exporter._render_combined_labels(labels)
        assert svg.startswith("<svg")
        # Should have both labels' content
        assert "TEST1" in svg
        assert "TEST2" in svg

    def test_combined_svg_validates_as_xml(self) -> None:
        """Combined SVG is valid XML."""
        exporter = SafetyLabelExporter()
        labels = [
            SafetyLabel(
                label_type="anti_tip",
                title="TEST1",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
            SafetyLabel(
                label_type="installation",
                title="TEST2",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
        ]
        svg = exporter._render_combined_labels(labels)
        root = ET.fromstring(svg)
        # Tag includes namespace
        assert root.tag.endswith("svg")


class TestFileExport:
    """Tests for file export functionality."""

    def test_export_label_to_file(self) -> None:
        """Label can be exported to file."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TEST",
            body_text="Test.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_label.svg"
            path.write_text(svg)
            assert path.exists()
            content = path.read_text()
            assert content.startswith("<svg")


class TestSuccessCriteriaFromTask:
    """Tests matching success criteria from task specification."""

    def test_export_single_label_to_svg(self) -> None:
        """Export single label to SVG - from task success criteria."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TIP-OVER HAZARD",
            body_text="Must be anchored to wall.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert svg.startswith("<svg")
        assert "TIP-OVER" in svg

    def test_export_multiple_labels(self) -> None:
        """Export multiple labels - from task success criteria."""
        exporter = SafetyLabelExporter()
        labels = [
            SafetyLabel(
                label_type="anti_tip",
                title="HAZARD",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
            SafetyLabel(
                label_type="weight_capacity",
                title="LOAD",
                body_text="Test.",
                dimensions=(4.0, 2.0),
            ),
            SafetyLabel(
                label_type="installation",
                title="INSTALL",
                body_text="Test.",
                dimensions=(4.0, 3.0),
            ),
        ]
        results = exporter.export_all_labels(labels)
        assert len(results) == 3
        assert all(svg.startswith("<svg") for svg in results.values())

    def test_label_dimensions_correct(self) -> None:
        """Label dimensions correct - from task success criteria."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="weight_capacity",
            title="TEST",
            body_text="Test.",
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        # 4" x 3" at 96 DPI = 384 x 288 pixels
        # Note: float values are output as 384.0, 288.0
        assert 'width="384' in svg
        assert 'height="288' in svg

    def test_warning_icon_included_when_specified(self) -> None:
        """Warning icon included when specified - from task success criteria."""
        exporter = SafetyLabelExporter()
        label = SafetyLabel(
            label_type="anti_tip",
            title="TEST",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "warning-icon" in svg

    def test_custom_styling_applied(self) -> None:
        """Custom styling applied - from task success criteria."""
        style = LabelStyle(warning_color="#ff6600", title_font_size=20)
        exporter = SafetyLabelExporter(style=style)
        label = SafetyLabel(
            label_type="anti_tip",
            title="TEST",
            body_text="Test.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )
        svg = exporter.export_label(label)
        assert "#ff6600" in svg
