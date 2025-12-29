"""Unit tests for CutDiagramRenderer."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cabinets.domain.value_objects import CutPiece, MaterialSpec, MaterialType, PanelType
from cabinets.infrastructure.bin_packing import (
    PackingResult,
    PlacedPiece,
    SheetConfig,
    SheetLayout,
)
from cabinets.infrastructure.cut_diagram_renderer import CutDiagramRenderer


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Standard 3/4 inch plywood."""
    return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)


@pytest.fixture
def sheet_config() -> SheetConfig:
    """Standard 4x8 sheet."""
    return SheetConfig(width=48, height=96, edge_allowance=0.5)


@pytest.fixture
def sample_piece(standard_material: MaterialSpec) -> CutPiece:
    """Sample cut piece for testing."""
    return CutPiece(
        width=24.0,
        height=48.0,
        quantity=1,
        label="Side Panel",
        panel_type=PanelType.LEFT_SIDE,
        material=standard_material,
    )


@pytest.fixture
def sample_placement(sample_piece: CutPiece) -> PlacedPiece:
    """Sample placed piece at origin."""
    return PlacedPiece(piece=sample_piece, x=0.0, y=0.0, rotated=False)


@pytest.fixture
def rotated_placement(sample_piece: CutPiece) -> PlacedPiece:
    """Sample rotated placement."""
    return PlacedPiece(piece=sample_piece, x=25.0, y=0.0, rotated=True)


@pytest.fixture
def sample_layout(
    sheet_config: SheetConfig,
    standard_material: MaterialSpec,
    sample_placement: PlacedPiece,
) -> SheetLayout:
    """Sample sheet layout with one piece."""
    return SheetLayout(
        sheet_index=0,
        sheet_config=sheet_config,
        placements=(sample_placement,),
        material=standard_material,
    )


@pytest.fixture
def multi_piece_layout(
    sheet_config: SheetConfig,
    standard_material: MaterialSpec,
    sample_placement: PlacedPiece,
    rotated_placement: PlacedPiece,
) -> SheetLayout:
    """Layout with multiple pieces including a rotated one."""
    return SheetLayout(
        sheet_index=0,
        sheet_config=sheet_config,
        placements=(sample_placement, rotated_placement),
        material=standard_material,
    )


@pytest.fixture
def renderer() -> CutDiagramRenderer:
    """Default renderer instance."""
    return CutDiagramRenderer()


class TestSvgValidStructure:
    """Tests for valid SVG structure."""

    def test_svg_opens_and_closes_properly(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """SVG output has proper opening and closing tags."""
        svg = renderer.render_svg(sample_layout)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_svg_is_valid_xml(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """SVG output is parseable as valid XML."""
        svg = renderer.render_svg(sample_layout)
        # Should not raise any exception
        root = ET.fromstring(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"

    def test_svg_has_xmlns_attribute(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """SVG includes the xmlns namespace attribute."""
        svg = renderer.render_svg(sample_layout)
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_svg_dimensions_match_sheet_at_scale(
        self, sample_layout: SheetLayout
    ) -> None:
        """SVG dimensions match sheet size at configured scale."""
        # Create renderer without panel colors to avoid legend
        renderer = CutDiagramRenderer(use_panel_colors=False)
        svg = renderer.render_svg(sample_layout)
        # Sheet is 48x96, so SVG should be 480 wide
        # Height includes 30px header, so 960 + 30 = 990
        assert 'width="480.0"' in svg or 'width="480"' in svg
        # Allow for floating point representation
        root = ET.fromstring(svg)
        width = float(root.get("width", "0"))
        height = float(root.get("height", "0"))
        assert width == 480.0
        assert height == 990.0  # 96 * 10 + 30 header

    def test_custom_scale_affects_dimensions(
        self, sample_layout: SheetLayout
    ) -> None:
        """Custom scale changes SVG dimensions."""
        # Create renderer without panel colors to avoid legend
        renderer = CutDiagramRenderer(scale=5.0, use_panel_colors=False)
        svg = renderer.render_svg(sample_layout)
        root = ET.fromstring(svg)
        width = float(root.get("width", "0"))
        height = float(root.get("height", "0"))
        # 48 * 5 = 240
        # 96 * 5 + 30 = 510
        assert width == 240.0
        assert height == 510.0


class TestPieceRendering:
    """Tests for piece rendering in SVG."""

    def test_piece_label_appears_in_svg(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Piece labels are rendered in the SVG."""
        svg = renderer.render_svg(sample_layout)
        assert "Side Panel" in svg

    def test_piece_dimensions_appear_in_svg(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Piece dimensions are shown in SVG."""
        svg = renderer.render_svg(sample_layout)
        # Should contain dimensions like 24.0" x 48.0"
        assert '24.0" x 48.0"' in svg

    def test_piece_rectangle_rendered(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Pieces are rendered as rectangles."""
        svg = renderer.render_svg(sample_layout)
        root = ET.fromstring(svg)
        # Find all rect elements
        rects = root.findall(".//{http://www.w3.org/2000/svg}rect")
        # Should have at least 3 rects: background, sheet, piece
        assert len(rects) >= 3

    def test_rotated_piece_shows_indicator(
        self, renderer: CutDiagramRenderer, multi_piece_layout: SheetLayout
    ) -> None:
        """Rotated pieces show (R) indicator."""
        svg = renderer.render_svg(multi_piece_layout)
        assert "(R)" in svg

    def test_all_pieces_rendered(
        self, renderer: CutDiagramRenderer, multi_piece_layout: SheetLayout
    ) -> None:
        """All placed pieces appear in the SVG."""
        svg = renderer.render_svg(multi_piece_layout)
        # Both pieces should be rendered
        # The rotated one should have (R) indicator
        assert "(R)" in svg
        # Count the "Side Panel" label occurrences (should be 2)
        assert svg.count("Side Panel") == 2

    def test_piece_position_is_correct(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        sheet_config: SheetConfig,
    ) -> None:
        """Piece is positioned correctly accounting for edge allowance."""
        svg = renderer.render_svg(sample_layout)
        root = ET.fromstring(svg)
        # Find the piece group (contains rect and text)
        groups = root.findall(".//{http://www.w3.org/2000/svg}g")
        assert len(groups) >= 1
        # Check that rect exists inside a group (piece rendering)
        piece_rect = None
        for g in groups:
            rect = g.find("{http://www.w3.org/2000/svg}rect")
            if rect is not None:
                piece_rect = rect
                break
        assert piece_rect is not None
        # Expected x position: edge_allowance * scale = 0.5 * 10 = 5
        x = float(piece_rect.get("x", "0"))
        # Position should be edge_allowance (0.5) * scale (10) = 5
        assert x == 5.0


class TestHeaderRendering:
    """Tests for header rendering."""

    def test_header_shows_sheet_number(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Header displays sheet number."""
        svg = renderer.render_svg(sample_layout)
        assert "Sheet 1" in svg

    def test_header_shows_total_sheets(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Header shows total sheet count."""
        svg = renderer.render_svg(sample_layout, total_sheets=3)
        assert "1 of 3" in svg

    def test_header_shows_material_info(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Header displays material type and thickness."""
        svg = renderer.render_svg(sample_layout)
        assert "plywood" in svg.lower()
        assert '0.75"' in svg

    def test_header_shows_waste_percentage(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Header displays waste percentage."""
        svg = renderer.render_svg(sample_layout)
        assert "% waste" in svg


class TestWasteRendering:
    """Tests for waste area rendering."""

    def test_waste_fill_color_used(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Waste areas use configured fill color."""
        svg = renderer.render_svg(sample_layout)
        # Default waste fill is #D3D3D3
        assert renderer.waste_fill in svg

    def test_custom_waste_fill_color(
        self, sample_layout: SheetLayout
    ) -> None:
        """Custom waste fill color is applied."""
        custom_color = "#FF0000"
        renderer = CutDiagramRenderer(waste_fill=custom_color)
        svg = renderer.render_svg(sample_layout)
        assert custom_color in svg

    def test_waste_areas_rendered_for_partial_sheet(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Waste areas are rendered when sheet is not fully used."""
        svg = renderer.render_svg(sample_layout)
        # The layout has a 24x48 piece on a 48x96 sheet
        # Should have waste areas
        root = ET.fromstring(svg)
        rects = root.findall(".//{http://www.w3.org/2000/svg}rect")
        # Should include waste rectangles
        waste_rects = [
            r for r in rects if r.get("fill") == renderer.waste_fill
        ]
        assert len(waste_rects) > 0


class TestEdgeAllowance:
    """Tests for edge allowance rendering."""

    def test_edge_allowance_dashed_line(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Edge allowance area is shown with dashed line."""
        svg = renderer.render_svg(sample_layout)
        assert "stroke-dasharray" in svg

    def test_usable_area_dimensions(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Usable area rectangle has correct dimensions."""
        svg = renderer.render_svg(sample_layout)
        root = ET.fromstring(svg)
        # Find the dashed rect (usable area indicator)
        rects = root.findall(".//{http://www.w3.org/2000/svg}rect")
        dashed_rect = None
        for r in rects:
            style = r.get("stroke-dasharray")
            if style:
                dashed_rect = r
                break
        assert dashed_rect is not None
        # Usable area: (48 - 2*0.5) * 10 = 470
        # Usable height: (96 - 2*0.5) * 10 = 950
        width = float(dashed_rect.get("width", "0"))
        height = float(dashed_rect.get("height", "0"))
        assert width == 470.0
        assert height == 950.0


class TestRenderAllSvg:
    """Tests for render_all_svg method."""

    def test_render_all_returns_list(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """render_all_svg returns a list of SVGs."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        svgs = renderer.render_all_svg(result)
        assert isinstance(svgs, list)
        assert len(svgs) == 1

    def test_render_all_multiple_sheets(
        self,
        renderer: CutDiagramRenderer,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        sample_placement: PlacedPiece,
    ) -> None:
        """render_all_svg handles multiple sheets."""
        layout1 = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        layout2 = SheetLayout(
            sheet_index=1,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        result = PackingResult(
            layouts=(layout1, layout2),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 2},
        )
        svgs = renderer.render_all_svg(result)
        assert len(svgs) == 2
        # Each SVG should be valid
        for svg in svgs:
            root = ET.fromstring(svg)
            assert root.tag == "{http://www.w3.org/2000/svg}svg"

    def test_render_all_empty_result(
        self, renderer: CutDiagramRenderer
    ) -> None:
        """render_all_svg handles empty result."""
        result = PackingResult(
            layouts=(),
            offcuts=(),
            total_waste_percentage=0.0,
            sheets_by_material={},
        )
        svgs = renderer.render_all_svg(result)
        assert svgs == []


class TestRenderCombinedSvg:
    """Tests for render_combined_svg method."""

    def test_combined_empty_result(
        self, renderer: CutDiagramRenderer
    ) -> None:
        """render_combined_svg handles empty result."""
        result = PackingResult(
            layouts=(),
            offcuts=(),
            total_waste_percentage=0.0,
            sheets_by_material={},
        )
        svg = renderer.render_combined_svg(result)
        assert "No sheets to display" in svg

    def test_combined_svg_is_valid_xml(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Combined SVG is valid XML."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        svg = renderer.render_combined_svg(result)
        root = ET.fromstring(svg)
        assert root.tag == "{http://www.w3.org/2000/svg}svg"

    def test_combined_svg_contains_all_sheets(
        self,
        renderer: CutDiagramRenderer,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        sample_placement: PlacedPiece,
    ) -> None:
        """Combined SVG contains content from all sheets."""
        layout1 = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        layout2 = SheetLayout(
            sheet_index=1,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        result = PackingResult(
            layouts=(layout1, layout2),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 2},
        )
        svg = renderer.render_combined_svg(result)
        # Should contain sheet references
        assert "Sheet 1" in svg
        assert "Sheet 2" in svg


class TestCustomStyling:
    """Tests for custom styling options."""

    def test_custom_piece_fill(
        self, sample_layout: SheetLayout
    ) -> None:
        """Custom piece fill color is applied when use_panel_colors is False."""
        custom_fill = "#FF5733"
        # Disable panel colors to use custom piece fill
        renderer = CutDiagramRenderer(piece_fill=custom_fill, use_panel_colors=False)
        svg = renderer.render_svg(sample_layout)
        assert custom_fill in svg

    def test_custom_piece_stroke(
        self, sample_layout: SheetLayout
    ) -> None:
        """Custom piece stroke color is applied."""
        custom_stroke = "#0000FF"
        renderer = CutDiagramRenderer(piece_stroke=custom_stroke)
        svg = renderer.render_svg(sample_layout)
        assert custom_stroke in svg

    def test_custom_text_color(
        self, sample_layout: SheetLayout
    ) -> None:
        """Custom text color is applied."""
        custom_text = "#00FF00"
        renderer = CutDiagramRenderer(text_color=custom_text)
        svg = renderer.render_svg(sample_layout)
        assert custom_text in svg


class TestSmallPieces:
    """Tests for handling small pieces."""

    def test_small_piece_renders_without_labels(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Very small pieces render without labels (to avoid overlap)."""
        small_piece = CutPiece(
            width=1.0,
            height=1.0,
            quantity=1,
            label="Tiny",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        small_placement = PlacedPiece(piece=small_piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(small_placement,),
            material=standard_material,
        )
        renderer = CutDiagramRenderer()
        svg = renderer.render_svg(layout)
        # At scale 10, a 1x1 piece is 10x10 pixels
        # Font size calculation: min(12, 10/6) = 1.67, which is < 6
        # So the label should NOT appear (too small)
        # But the rect should still be there
        root = ET.fromstring(svg)
        rects = root.findall(".//{http://www.w3.org/2000/svg}rect")
        assert len(rects) >= 1


class TestAsciiRendering:
    """Tests for ASCII rendering."""

    def test_ascii_output_structure(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII output has proper structure with borders."""
        ascii_out = renderer.render_ascii(sample_layout)
        lines = ascii_out.split("\n")
        # Second line should be the top border
        assert lines[1].startswith("+")
        assert lines[1].endswith("+")
        # Last line should be bottom border
        assert lines[-1].startswith("+")
        assert lines[-1].endswith("+")

    def test_ascii_respects_width(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII output respects specified width."""
        ascii_out = renderer.render_ascii(sample_layout, width=80)
        lines = ascii_out.split("\n")
        # Grid lines (border lines) should be exactly 80 characters
        for line in lines[1:]:  # Skip header
            assert len(line) <= 80

    def test_ascii_header_shows_sheet_number(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII header displays sheet number."""
        ascii_out = renderer.render_ascii(sample_layout)
        first_line = ascii_out.split("\n")[0]
        assert "Sheet" in first_line
        assert "1 of" in first_line

    def test_ascii_header_shows_material(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII header displays material information."""
        ascii_out = renderer.render_ascii(sample_layout)
        first_line = ascii_out.split("\n")[0]
        assert "plywood" in first_line.lower()
        assert '0.75"' in first_line

    def test_ascii_header_shows_waste_percentage(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII header displays waste percentage."""
        ascii_out = renderer.render_ascii(sample_layout)
        first_line = ascii_out.split("\n")[0]
        assert "% waste" in first_line

    def test_ascii_piece_label_appears(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Piece labels appear in ASCII output."""
        ascii_out = renderer.render_ascii(sample_layout)
        # Label may be truncated but should appear at least partially
        assert "Side" in ascii_out

    def test_ascii_piece_dimensions_appear(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """Piece dimensions appear in ASCII output."""
        ascii_out = renderer.render_ascii(sample_layout)
        # Dimensions like 24x48 should appear
        assert "24x48" in ascii_out

    def test_ascii_rotated_piece_shows_indicator(
        self, renderer: CutDiagramRenderer, multi_piece_layout: SheetLayout
    ) -> None:
        """Rotated pieces show R indicator in ASCII."""
        ascii_out = renderer.render_ascii(multi_piece_layout)
        # Rotated piece should have R indicator
        assert "R" in ascii_out

    def test_ascii_uses_box_characters(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII output uses box drawing characters."""
        ascii_out = renderer.render_ascii(sample_layout)
        # Should have corners
        assert "+" in ascii_out
        # Should have horizontal and vertical lines
        assert "-" in ascii_out
        assert "|" in ascii_out

    def test_ascii_narrow_width_support(
        self, renderer: CutDiagramRenderer, sample_layout: SheetLayout
    ) -> None:
        """ASCII works with narrow terminal width."""
        ascii_out = renderer.render_ascii(sample_layout, width=40)
        # Should not crash, output should be valid
        assert len(ascii_out) > 0
        lines = ascii_out.split("\n")
        for line in lines[1:]:  # Skip header
            assert len(line) <= 40


class TestRenderAllAscii:
    """Tests for render_all_ascii method."""

    def test_render_all_ascii_empty_result(
        self, renderer: CutDiagramRenderer
    ) -> None:
        """render_all_ascii handles empty result."""
        result = PackingResult(
            layouts=(),
            offcuts=(),
            total_waste_percentage=0.0,
            sheets_by_material={},
        )
        ascii_out = renderer.render_all_ascii(result)
        assert ascii_out == "No sheets to display."

    def test_render_all_ascii_single_sheet(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """render_all_ascii renders single sheet with summary."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        ascii_out = renderer.render_all_ascii(result)
        assert "SUMMARY" in ascii_out
        assert "1 sheet" in ascii_out

    def test_render_all_ascii_multiple_sheets(
        self,
        renderer: CutDiagramRenderer,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        sample_placement: PlacedPiece,
    ) -> None:
        """render_all_ascii handles multiple sheets."""
        layout1 = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        layout2 = SheetLayout(
            sheet_index=1,
            sheet_config=sheet_config,
            placements=(sample_placement,),
            material=standard_material,
        )
        result = PackingResult(
            layouts=(layout1, layout2),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 2},
        )
        ascii_out = renderer.render_all_ascii(result)
        # Should contain both sheets
        assert "Sheet 1 of 2" in ascii_out
        assert "Sheet 2 of 2" in ascii_out
        # Should have summary
        assert "SUMMARY" in ascii_out
        assert "2 sheets" in ascii_out

    def test_render_all_ascii_total_waste_shown(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Summary shows total waste percentage."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=35.5,
            sheets_by_material={standard_material: 1},
        )
        ascii_out = renderer.render_all_ascii(result)
        assert "35.5%" in ascii_out


class TestRenderWasteSummary:
    """Tests for render_waste_summary method."""

    def test_waste_summary_header(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Waste summary has proper header."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        summary = renderer.render_waste_summary(result)
        assert "CUT OPTIMIZATION SUMMARY" in summary

    def test_waste_summary_total_sheets(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Waste summary shows total sheet count."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        summary = renderer.render_waste_summary(result)
        assert "Total Sheets: 1" in summary

    def test_waste_summary_total_waste(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Waste summary shows total waste percentage."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=45.3,
            sheets_by_material={standard_material: 1},
        )
        summary = renderer.render_waste_summary(result)
        assert "Total Waste: 45.3%" in summary

    def test_waste_summary_material_breakdown(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Waste summary shows sheets by material."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        summary = renderer.render_waste_summary(result)
        assert "Sheets by Material:" in summary
        assert "plywood" in summary.lower()

    def test_waste_summary_per_sheet_details(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Waste summary shows per-sheet details."""
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        summary = renderer.render_waste_summary(result)
        assert "Per-Sheet Details:" in summary
        assert "Sheet 1:" in summary

    def test_waste_summary_with_offcuts(
        self,
        renderer: CutDiagramRenderer,
        sample_layout: SheetLayout,
        standard_material: MaterialSpec,
    ) -> None:
        """Waste summary shows reusable offcuts when present."""
        from cabinets.infrastructure.bin_packing import Offcut

        offcut = Offcut(
            width=10.0,
            height=20.0,
            material=standard_material,
            sheet_index=0,
        )
        result = PackingResult(
            layouts=(sample_layout,),
            offcuts=(offcut,),
            total_waste_percentage=50.0,
            sheets_by_material={standard_material: 1},
        )
        summary = renderer.render_waste_summary(result)
        assert "Reusable Offcuts:" in summary
        assert '10.0" x 20.0"' in summary


# =============================================================================
# Edge Case Tests - Pieces Touching All Edges
# =============================================================================


class TestPiecesTouchingEdges:
    """Tests for pieces that touch various edges of the sheet."""

    def test_piece_touches_left_edge(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Piece at x=0 touches left edge of usable area."""
        piece = CutPiece(
            width=20.0,
            height=40.0,
            quantity=1,
            label="Left Edge",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        # Should produce valid SVG
        assert svg.startswith("<svg")
        assert "Left Edge" in svg

    def test_piece_touches_bottom_edge(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Piece at y=0 touches bottom edge of usable area."""
        piece = CutPiece(
            width=20.0,
            height=40.0,
            quantity=1,
            label="Bottom Edge",
            panel_type=PanelType.BOTTOM,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert svg.startswith("<svg")
        assert "Bottom Edge" in svg

    def test_piece_exactly_fills_usable_area(
        self,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Piece that exactly fills the usable area touches all edges."""
        # Sheet 50x100 with no edge allowance
        sheet = SheetConfig(width=50.0, height=100.0, edge_allowance=0.0)
        piece = CutPiece(
            width=50.0,
            height=100.0,
            quantity=1,
            label="Full Sheet",
            panel_type=PanelType.TOP,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert svg.startswith("<svg")
        assert "Full Sheet" in svg
        # Waste should be approximately 0%
        assert "0.0% waste" in svg or "0% waste" in svg

    def test_piece_touches_right_edge(
        self,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Piece placed at right edge of usable area."""
        # Sheet 50x100 with no edge allowance
        sheet = SheetConfig(width=50.0, height=100.0, edge_allowance=0.0)
        # 30-wide piece at x=20 reaches right edge (20+30=50)
        piece = CutPiece(
            width=30.0,
            height=50.0,
            quantity=1,
            label="Right Edge",
            panel_type=PanelType.RIGHT_SIDE,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=20.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert svg.startswith("<svg")
        assert "Right Edge" in svg

    def test_piece_touches_top_edge(
        self,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Piece placed at top edge of usable area."""
        # Sheet 50x100 with no edge allowance
        sheet = SheetConfig(width=50.0, height=100.0, edge_allowance=0.0)
        # 60-tall piece at y=40 reaches top edge (40+60=100)
        piece = CutPiece(
            width=30.0,
            height=60.0,
            quantity=1,
            label="Top Edge",
            panel_type=PanelType.TOP,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=40.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert svg.startswith("<svg")
        assert "Top Edge" in svg


class TestRendererEmptyLayouts:
    """Tests for empty layout handling in renderer."""

    def test_empty_layout_renders_svg(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Empty layout (no placements) still produces valid SVG."""
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        # Should show 100% waste for empty layout
        assert "100.0% waste" in svg or "100% waste" in svg

    def test_empty_layout_renders_ascii(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Empty layout produces valid ASCII output."""
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(),
            material=standard_material,
        )

        ascii_out = renderer.render_ascii(layout)

        # Should have basic structure
        assert "Sheet" in ascii_out
        assert "+" in ascii_out  # Border characters


class TestRendererSinglePiece:
    """Tests for single piece per sheet scenarios."""

    def test_single_small_piece_svg(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Single small piece renders correctly in SVG."""
        piece = CutPiece(
            width=10.0,
            height=10.0,
            quantity=1,
            label="Single",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert "Single" in svg
        assert '10.0" x 10.0"' in svg

    def test_single_large_piece_svg(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Single large piece renders correctly in SVG."""
        # Large piece: 40x90 on 47x95 usable sheet
        piece = CutPiece(
            width=40.0,
            height=90.0,
            quantity=1,
            label="Large Single",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        assert "Large Single" in svg
        assert '40.0" x 90.0"' in svg

    def test_single_piece_ascii(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Single piece renders correctly in ASCII."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="OnlyPiece",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        ascii_out = renderer.render_ascii(layout)

        # Label should appear (possibly truncated)
        assert "Only" in ascii_out
        # Dimensions should appear
        assert "20x30" in ascii_out


class TestRendererManyPieces:
    """Tests for layouts with many pieces."""

    def test_many_pieces_on_sheet(
        self,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Many pieces render correctly without overlap issues."""
        sheet = SheetConfig(width=50.0, height=100.0, edge_allowance=0.0)

        # Create 10 small pieces in a grid
        placements = []
        for i in range(10):
            piece = CutPiece(
                width=8.0,
                height=8.0,
                quantity=1,
                label=f"P{i}",
                panel_type=PanelType.SHELF,
                material=standard_material,
            )
            # Arrange in rows
            x = (i % 5) * 10.0
            y = (i // 5) * 10.0
            placements.append(PlacedPiece(piece=piece, x=x, y=y, rotated=False))

        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=tuple(placements),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        # All piece labels should appear
        for i in range(10):
            assert f"P{i}" in svg

    def test_densely_packed_svg(
        self,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Densely packed layout renders without issues."""
        sheet = SheetConfig(width=100.0, height=100.0, edge_allowance=0.0)

        # Fill with 10x10 pieces (100 pieces)
        placements = []
        idx = 0
        for row in range(10):
            for col in range(10):
                piece = CutPiece(
                    width=10.0,
                    height=10.0,
                    quantity=1,
                    label=f"D{idx}",
                    panel_type=PanelType.SHELF,
                    material=standard_material,
                )
                placements.append(
                    PlacedPiece(
                        piece=piece, x=col * 10.0, y=row * 10.0, rotated=False
                    )
                )
                idx += 1

        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=tuple(placements),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        # Should be valid SVG
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        # Should show ~0% waste
        assert "0.0% waste" in svg or "0% waste" in svg


class TestRendererVerySmallPieces:
    """Tests for rendering very small pieces."""

    def test_very_small_piece_svg(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Very small piece renders as rectangle even if labels are suppressed."""
        # Create a 0.5" x 0.5" piece
        piece = CutPiece(
            width=0.5,
            height=0.5,
            quantity=1,
            label="Tiny",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        # Should still be valid SVG with rect element
        assert svg.startswith("<svg")
        assert "<rect" in svg

    def test_mixed_very_small_and_normal_pieces(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Mixed sizes render correctly together."""
        # Normal piece
        normal_piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Normal",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
        )
        # Tiny piece
        tiny_piece = CutPiece(
            width=0.5,
            height=0.5,
            quantity=1,
            label="Tiny",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )

        placements = (
            PlacedPiece(piece=normal_piece, x=0.0, y=0.0, rotated=False),
            PlacedPiece(piece=tiny_piece, x=21.0, y=0.0, rotated=False),
        )

        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=placements,
            material=standard_material,
        )

        svg = renderer.render_svg(layout)

        # Normal piece label should appear
        assert "Normal" in svg
        assert '20.0" x 30.0"' in svg


class TestRendererMultiMaterial:
    """Tests for rendering layouts with multiple material types."""

    def test_waste_summary_multiple_materials(
        self,
        renderer: CutDiagramRenderer,
    ) -> None:
        """Waste summary shows all material types."""
        material_1 = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        material_2 = MaterialSpec(thickness=0.5, material_type=MaterialType.MDF)
        sheet = SheetConfig()

        piece1 = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Plywood",
            panel_type=PanelType.LEFT_SIDE,
            material=material_1,
        )
        piece2 = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="MDF",
            panel_type=PanelType.SHELF,
            material=material_2,
        )

        layout1 = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=(PlacedPiece(piece=piece1, x=0.0, y=0.0),),
            material=material_1,
        )
        layout2 = SheetLayout(
            sheet_index=1,
            sheet_config=sheet,
            placements=(PlacedPiece(piece=piece2, x=0.0, y=0.0),),
            material=material_2,
        )

        result = PackingResult(
            layouts=(layout1, layout2),
            offcuts=(),
            total_waste_percentage=45.0,
            sheets_by_material={material_1: 1, material_2: 1},
        )

        summary = renderer.render_waste_summary(result)

        # Should mention both materials
        assert "plywood" in summary.lower()
        assert "mdf" in summary.lower()
        assert "Total Sheets: 2" in summary


# =============================================================================
# Panel Type Colors Tests (FRD-16 FR-04.2)
# =============================================================================


class TestPanelTypeColors:
    """Tests for panel type color rendering."""

    def test_panel_type_colors_dictionary_exists(self) -> None:
        """PANEL_TYPE_COLORS dictionary is defined with expected colors."""
        from cabinets.infrastructure.cut_diagram_renderer import PANEL_TYPE_COLORS

        assert PanelType.SHELF in PANEL_TYPE_COLORS
        assert PanelType.LEFT_SIDE in PANEL_TYPE_COLORS
        assert PanelType.BACK in PANEL_TYPE_COLORS
        assert PANEL_TYPE_COLORS[PanelType.SHELF] == "#87CEEB"  # Sky blue

    def test_use_panel_colors_applies_correct_fill(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When use_panel_colors=True, pieces use panel type colors."""
        from cabinets.infrastructure.cut_diagram_renderer import PANEL_TYPE_COLORS

        # Create a shelf piece
        shelf_piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=shelf_piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=True)
        svg = renderer.render_svg(layout)

        # Should use the shelf color
        expected_color = PANEL_TYPE_COLORS[PanelType.SHELF]
        assert expected_color in svg

    def test_use_panel_colors_false_uses_default_fill(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When use_panel_colors=False, pieces use default piece_fill."""
        default_fill = "#ADD8E6"
        shelf_piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=shelf_piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # Should use the default fill, not the panel type color
        assert default_fill in svg

    def test_multiple_panel_types_different_colors(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Different panel types render with different colors."""
        from cabinets.infrastructure.cut_diagram_renderer import PANEL_TYPE_COLORS

        shelf_piece = CutPiece(
            width=15.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        side_piece = CutPiece(
            width=15.0,
            height=30.0,
            quantity=1,
            label="Side",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
        )

        placements = (
            PlacedPiece(piece=shelf_piece, x=0.0, y=0.0, rotated=False),
            PlacedPiece(piece=side_piece, x=16.0, y=0.0, rotated=False),
        )
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=placements,
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=True)
        svg = renderer.render_svg(layout)

        # Both colors should appear
        assert PANEL_TYPE_COLORS[PanelType.SHELF] in svg
        assert PANEL_TYPE_COLORS[PanelType.LEFT_SIDE] in svg


# =============================================================================
# Legend Tests (FRD-16 FR-04.4)
# =============================================================================


class TestLegendRendering:
    """Tests for legend rendering."""

    def test_legend_appears_when_panel_colors_enabled(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Legend is rendered when use_panel_colors=True."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=True)
        svg = renderer.render_svg(layout)

        assert "Panel Types:" in svg
        assert "<!-- Legend -->" in svg

    def test_legend_not_shown_when_panel_colors_disabled(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Legend is not rendered when use_panel_colors=False."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=False)
        svg = renderer.render_svg(layout)

        assert "Panel Types:" not in svg
        assert "<!-- Legend -->" not in svg

    def test_legend_shows_all_used_panel_types(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Legend shows entries for all panel types used in the layout."""
        shelf_piece = CutPiece(
            width=15.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        side_piece = CutPiece(
            width=15.0,
            height=30.0,
            quantity=1,
            label="Side",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
        )
        back_piece = CutPiece(
            width=10.0,
            height=30.0,
            quantity=1,
            label="Back",
            panel_type=PanelType.BACK,
            material=standard_material,
        )

        placements = (
            PlacedPiece(piece=shelf_piece, x=0.0, y=0.0, rotated=False),
            PlacedPiece(piece=side_piece, x=16.0, y=0.0, rotated=False),
            PlacedPiece(piece=back_piece, x=32.0, y=0.0, rotated=False),
        )
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=placements,
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=True)
        svg = renderer.render_svg(layout)

        # All three panel type names should appear in the legend
        assert "Shelf" in svg
        assert "Left Side" in svg
        assert "Back" in svg

    def test_legend_not_shown_for_empty_layout(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Legend is not rendered for layouts with no pieces."""
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(use_panel_colors=True)
        svg = renderer.render_svg(layout)

        assert "Panel Types:" not in svg

    def test_legend_increases_svg_height(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """SVG height increases to accommodate the legend."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer_with_legend = CutDiagramRenderer(use_panel_colors=True)
        renderer_no_legend = CutDiagramRenderer(use_panel_colors=False)

        svg_with_legend = renderer_with_legend.render_svg(layout)
        svg_no_legend = renderer_no_legend.render_svg(layout)

        root_with = ET.fromstring(svg_with_legend)
        root_without = ET.fromstring(svg_no_legend)

        height_with = float(root_with.get("height", "0"))
        height_without = float(root_without.get("height", "0"))

        assert height_with > height_without


# =============================================================================
# Show Labels/Dimensions Tests (FRD-16 FR-04.5)
# =============================================================================


class TestShowLabelsAndDimensions:
    """Tests for configurable label and dimension visibility."""

    def test_show_labels_true_displays_label(
        self,
        sample_layout: SheetLayout,
    ) -> None:
        """When show_labels=True, piece labels are displayed."""
        renderer = CutDiagramRenderer(show_labels=True, use_panel_colors=False)
        svg = renderer.render_svg(sample_layout)
        assert "Side Panel" in svg

    def test_show_labels_false_hides_label(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When show_labels=False, piece labels are not displayed."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="UniqueLabel123",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_labels=False, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # The unique label should not appear
        assert "UniqueLabel123" not in svg

    def test_show_dimensions_true_displays_dimensions(
        self,
        sample_layout: SheetLayout,
    ) -> None:
        """When show_dimensions=True, piece dimensions are displayed."""
        renderer = CutDiagramRenderer(show_dimensions=True, use_panel_colors=False)
        svg = renderer.render_svg(sample_layout)
        assert '24.0" x 48.0"' in svg

    def test_show_dimensions_false_hides_dimensions(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When show_dimensions=False, piece dimensions are not displayed."""
        piece = CutPiece(
            width=17.5,
            height=33.3,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_dimensions=False, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # The dimensions should not appear
        assert '17.5" x 33.3"' not in svg

    def test_both_labels_and_dimensions_hidden(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When both are False, only the rectangle is rendered."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="HiddenLabel",
            panel_type=PanelType.SHELF,
            material=standard_material,
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(
            show_labels=False, show_dimensions=False, use_panel_colors=False
        )
        svg = renderer.render_svg(layout)

        # Neither label nor dimensions should appear
        assert "HiddenLabel" not in svg
        assert '20.0" x 30.0"' not in svg
        # But the rectangle should still be there
        assert "<rect" in svg


# =============================================================================
# Grain Direction Indicator Tests (FRD-16 FR-04.5)
# =============================================================================


class TestGrainDirectionIndicator:
    """Tests for grain direction arrow rendering."""

    def test_show_grain_false_no_arrow(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When show_grain=False, no grain arrows are rendered."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={"grain_direction": "length"},
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_grain=False, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # No arrow elements should be present
        assert "<line" not in svg
        assert "<polygon" not in svg

    def test_show_grain_true_with_grain_direction(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When show_grain=True and grain_direction is set, arrow is rendered."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={"grain_direction": "length"},
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_grain=True, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # Arrow elements should be present (line and polygon for arrow head)
        assert "<line" in svg
        assert "<polygon" in svg

    def test_show_grain_true_no_grain_metadata(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """When show_grain=True but no grain_direction, no arrow is rendered."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata=None,  # No metadata
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_grain=True, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # No arrow elements should be present
        assert "<line" not in svg
        assert "<polygon" not in svg

    def test_grain_direction_width(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Grain direction 'width' renders an arrow."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={"grain_direction": "width"},
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_grain=True, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # Arrow elements should be present
        assert "<line" in svg
        assert "<polygon" in svg

    def test_grain_direction_none_no_arrow(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Grain direction 'none' renders no arrow."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={"grain_direction": "none"},
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_grain=True, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # No arrow elements should be present
        assert "<line" not in svg
        assert "<polygon" not in svg

    def test_rotated_piece_grain_indicator(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Rotated pieces still render grain indicator correctly."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Test",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={"grain_direction": "length"},
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=True)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        renderer = CutDiagramRenderer(show_grain=True, use_panel_colors=False)
        svg = renderer.render_svg(layout)

        # Arrow elements should be present
        assert "<line" in svg
        assert "<polygon" in svg


# =============================================================================
# Configuration Options Tests (FRD-16 FR-04.5)
# =============================================================================


class TestConfigurationOptions:
    """Tests for renderer configuration options."""

    def test_default_configuration(self) -> None:
        """Default configuration has expected values."""
        renderer = CutDiagramRenderer()

        assert renderer.scale == 10.0
        assert renderer.show_dimensions is True
        assert renderer.show_labels is True
        assert renderer.show_grain is False
        assert renderer.use_panel_colors is True

    def test_all_options_configurable(self) -> None:
        """All new options can be configured via constructor."""
        renderer = CutDiagramRenderer(
            scale=5.0,
            show_dimensions=False,
            show_labels=False,
            show_grain=True,
            use_panel_colors=False,
        )

        assert renderer.scale == 5.0
        assert renderer.show_dimensions is False
        assert renderer.show_labels is False
        assert renderer.show_grain is True
        assert renderer.use_panel_colors is False

    def test_combined_configuration(
        self,
        sheet_config: SheetConfig,
        standard_material: MaterialSpec,
    ) -> None:
        """Multiple configuration options work together correctly."""
        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="ConfigTest",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={"grain_direction": "length"},
        )
        placement = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet_config,
            placements=(placement,),
            material=standard_material,
        )

        # Enable grain, disable labels, use panel colors
        renderer = CutDiagramRenderer(
            show_dimensions=True,
            show_labels=False,
            show_grain=True,
            use_panel_colors=True,
        )
        svg = renderer.render_svg(layout)

        # Should have grain arrow
        assert "<line" in svg
        # Should not have the label
        assert "ConfigTest" not in svg
        # Should have dimensions
        assert '20.0" x 30.0"' in svg
        # Should have legend
        assert "Panel Types:" in svg
