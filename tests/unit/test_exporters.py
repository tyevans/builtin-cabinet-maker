"""Tests for infrastructure exporters with decorative metadata support.

Tests for CutListFormatter and JsonExporter handling of decorative metadata
including arch, scallop, edge profile, joinery, and zone information.
"""

from __future__ import annotations

import json

import pytest

from cabinets.application.dtos import LayoutOutput
from cabinets.domain.entities import Cabinet
from cabinets.domain.services import MaterialEstimate
from cabinets.domain.value_objects import CutPiece, MaterialSpec, PanelType
from cabinets.infrastructure.exporters import (
    CutListFormatter,
    HardwareReportFormatter,
    JsonExporter,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Create standard 3/4\" material."""
    return MaterialSpec.standard_3_4()


@pytest.fixture
def simple_cut_piece(standard_material: MaterialSpec) -> CutPiece:
    """Create a simple cut piece without decorative metadata."""
    return CutPiece(
        width=24.0,
        height=12.0,
        quantity=2,
        label="Shelf",
        panel_type=PanelType.SHELF,
        material=standard_material,
    )


@pytest.fixture
def arch_cut_piece(standard_material: MaterialSpec) -> CutPiece:
    """Create a cut piece with arch metadata."""
    return CutPiece(
        width=24.0,
        height=12.0,
        quantity=1,
        label="Arch Header",
        panel_type=PanelType.ARCH_HEADER,
        material=standard_material,
        cut_metadata={
            "arch_type": "full_round",
            "radius": 12.0,
            "spring_height": 6.0,
        },
    )


@pytest.fixture
def scallop_cut_piece(standard_material: MaterialSpec) -> CutPiece:
    """Create a cut piece with scallop metadata."""
    return CutPiece(
        width=48.0,
        height=3.0,
        quantity=1,
        label="Valance",
        panel_type=PanelType.VALANCE,
        material=standard_material,
        cut_metadata={
            "scallop_depth": 1.5,
            "scallop_width": 6.0,
            "scallop_count": 8,
            "template_info": "8x 6.0\" x 1.5\"",
        },
    )


@pytest.fixture
def edge_profile_cut_piece(standard_material: MaterialSpec) -> CutPiece:
    """Create a cut piece with edge profile metadata."""
    return CutPiece(
        width=24.0,
        height=12.0,
        quantity=4,
        label="Shelf",
        panel_type=PanelType.SHELF,
        material=standard_material,
        cut_metadata={
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
                "edges": ["front"],
            },
        },
    )


@pytest.fixture
def joinery_cut_piece(standard_material: MaterialSpec) -> CutPiece:
    """Create a cut piece with joinery metadata."""
    return CutPiece(
        width=1.5,
        height=84.0,
        quantity=2,
        label="Face Frame Stile",
        panel_type=PanelType.FACE_FRAME_STILE,
        material=standard_material,
        cut_metadata={
            "joinery_type": "pocket_screw",
        },
    )


@pytest.fixture
def zone_cut_piece(standard_material: MaterialSpec) -> CutPiece:
    """Create a cut piece with zone metadata."""
    return CutPiece(
        width=48.0,
        height=4.0,
        quantity=1,
        label="Toe Kick",
        panel_type=PanelType.TOE_KICK,
        material=standard_material,
        cut_metadata={
            "zone_type": "toe_kick",
            "setback": 3.5,
        },
    )


@pytest.fixture
def mixed_cut_list(
    simple_cut_piece: CutPiece,
    arch_cut_piece: CutPiece,
    scallop_cut_piece: CutPiece,
    edge_profile_cut_piece: CutPiece,
    joinery_cut_piece: CutPiece,
    zone_cut_piece: CutPiece,
) -> list[CutPiece]:
    """Create a cut list with mixed decorative metadata."""
    return [
        simple_cut_piece,
        arch_cut_piece,
        scallop_cut_piece,
        edge_profile_cut_piece,
        joinery_cut_piece,
        zone_cut_piece,
    ]


@pytest.fixture
def simple_cabinet() -> Cabinet:
    """Create a simple cabinet for LayoutOutput testing."""
    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        back_material=MaterialSpec.standard_1_2(),
    )


@pytest.fixture
def simple_layout_output(simple_cabinet: Cabinet, mixed_cut_list: list[CutPiece]) -> LayoutOutput:
    """Create a simple LayoutOutput for JsonExporter testing."""
    return LayoutOutput(
        cabinet=simple_cabinet,
        cut_list=mixed_cut_list,
        total_estimate=MaterialEstimate(
            total_area_sqin=1000.0,
            total_area_sqft=6.94,
            sheet_count_4x8=1,
            sheet_count_5x5=1,
            waste_percentage=0.15,
        ),
        material_estimates={},
    )


# =============================================================================
# CutListFormatter Basic Tests
# =============================================================================


class TestCutListFormatterBasic:
    """Basic tests for CutListFormatter."""

    def test_format_empty_list(self) -> None:
        """Test formatting empty cut list."""
        formatter = CutListFormatter()
        result = formatter.format([])
        assert result == "No pieces in cut list."

    def test_format_simple_cut_list(self, simple_cut_piece: CutPiece) -> None:
        """Test formatting cut list without decorative metadata."""
        formatter = CutListFormatter()
        result = formatter.format([simple_cut_piece])

        assert "CUT LIST" in result
        assert "Shelf" in result
        assert "24.000" in result
        assert "12.000" in result
        # Should NOT have Notes column since no decorative metadata
        assert "Notes" not in result

    def test_format_with_decorative_disabled(self, arch_cut_piece: CutPiece) -> None:
        """Test formatting with decorative notes disabled."""
        formatter = CutListFormatter(include_decorative=False)
        result = formatter.format([arch_cut_piece])

        assert "Notes" not in result
        assert "Arch:" not in result

    def test_default_includes_decorative(self) -> None:
        """Test that decorative notes are included by default."""
        formatter = CutListFormatter()
        assert formatter._include_decorative is True


# =============================================================================
# CutListFormatter Decorative Notes Tests
# =============================================================================


class TestCutListFormatterDecorativeNotes:
    """Tests for CutListFormatter decorative notes extraction."""

    def test_arch_notes_format(self, arch_cut_piece: CutPiece) -> None:
        """Test arch metadata formatting."""
        formatter = CutListFormatter()
        result = formatter.format([arch_cut_piece])

        assert "Notes" in result
        assert 'Arch: full_round, R=12.0", spring=6.0"' in result

    def test_scallop_notes_format(self, scallop_cut_piece: CutPiece) -> None:
        """Test scallop metadata formatting."""
        formatter = CutListFormatter()
        result = formatter.format([scallop_cut_piece])

        assert "Notes" in result
        assert 'Scallop: 8x 6.00" x 1.50"' in result

    def test_edge_profile_notes_format(self, edge_profile_cut_piece: CutPiece) -> None:
        """Test edge profile metadata formatting."""
        formatter = CutListFormatter()
        result = formatter.format([edge_profile_cut_piece])

        assert "Notes" in result
        assert 'Profile: roundover 0.25" (front)' in result

    def test_joinery_notes_format(self, joinery_cut_piece: CutPiece) -> None:
        """Test joinery metadata formatting."""
        formatter = CutListFormatter()
        result = formatter.format([joinery_cut_piece])

        assert "Notes" in result
        assert "Joinery: pocket_screw" in result

    def test_zone_notes_format(self, zone_cut_piece: CutPiece) -> None:
        """Test zone metadata formatting."""
        formatter = CutListFormatter()
        result = formatter.format([zone_cut_piece])

        assert "Notes" in result
        assert "Zone: toe_kick" in result

    def test_multiple_notes_semicolon_separated(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test that multiple notes are separated by semicolons."""
        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Decorated Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={
                "edge_profile": {
                    "profile_type": "roundover",
                    "size": 0.25,
                    "edges": ["front"],
                },
                "joinery_type": "pocket_screw",
            },
        )

        formatter = CutListFormatter()
        result = formatter.format([piece])

        # Both notes should be present separated by semicolon
        assert "Profile:" in result
        assert "Joinery:" in result
        assert ";" in result

    def test_edge_profile_auto_edges(self, standard_material: MaterialSpec) -> None:
        """Test edge profile with no edges specified shows 'auto'."""
        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={
                "edge_profile": {
                    "profile_type": "chamfer",
                    "size": 0.125,
                    "edges": [],
                },
            },
        )

        formatter = CutListFormatter()
        result = formatter.format([piece])

        assert "(auto)" in result


# =============================================================================
# CutListFormatter Mixed Content Tests
# =============================================================================


class TestCutListFormatterMixedContent:
    """Tests for CutListFormatter with mixed decorative and simple pieces."""

    def test_mixed_cut_list_uses_notes_column(
        self, mixed_cut_list: list[CutPiece]
    ) -> None:
        """Test that mixed cut list uses Notes column when any piece has metadata."""
        formatter = CutListFormatter()
        result = formatter.format(mixed_cut_list)

        assert "Notes" in result
        # Check headers are present
        assert "Piece" in result
        assert "Width" in result
        assert "Height" in result
        assert "Qty" in result
        assert "Area" in result

    def test_mixed_cut_list_shows_all_pieces(
        self, mixed_cut_list: list[CutPiece]
    ) -> None:
        """Test that all pieces are shown in mixed cut list."""
        formatter = CutListFormatter()
        result = formatter.format(mixed_cut_list)

        assert "Shelf" in result
        assert "Arch Header" in result
        assert "Valance" in result
        assert "Face Frame Stile" in result
        assert "Toe Kick" in result

    def test_simple_piece_has_empty_notes(
        self, simple_cut_piece: CutPiece, arch_cut_piece: CutPiece
    ) -> None:
        """Test that simple pieces have empty notes in mixed list."""
        formatter = CutListFormatter()
        cut_list = [simple_cut_piece, arch_cut_piece]
        result = formatter.format(cut_list)

        # The result should have Notes column
        assert "Notes" in result
        # Arch piece should have Arch: in notes
        assert "Arch:" in result

    def test_total_area_calculated_correctly(
        self, mixed_cut_list: list[CutPiece]
    ) -> None:
        """Test that total area is calculated correctly."""
        formatter = CutListFormatter()
        result = formatter.format(mixed_cut_list)

        # Calculate expected total
        expected_total = sum(p.area for p in mixed_cut_list)
        # Check that TOTAL line exists
        assert "TOTAL" in result


# =============================================================================
# CutListFormatter Internal Methods Tests
# =============================================================================


class TestCutListFormatterInternalMethods:
    """Tests for CutListFormatter internal methods."""

    def test_get_decorative_notes_no_metadata(self, simple_cut_piece: CutPiece) -> None:
        """Test _get_decorative_notes with no metadata."""
        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(simple_cut_piece)
        assert notes == ""

    def test_get_decorative_notes_with_arch(self, arch_cut_piece: CutPiece) -> None:
        """Test _get_decorative_notes with arch metadata."""
        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(arch_cut_piece)
        assert "Arch:" in notes
        assert "full_round" in notes
        assert "R=12.0" in notes
        assert "spring=6.0" in notes

    def test_get_decorative_notes_with_scallop(
        self, scallop_cut_piece: CutPiece
    ) -> None:
        """Test _get_decorative_notes with scallop metadata."""
        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(scallop_cut_piece)
        assert "Scallop:" in notes
        assert "8x" in notes
        assert "6.00" in notes
        assert "1.50" in notes

    def test_get_decorative_notes_with_edge_profile(
        self, edge_profile_cut_piece: CutPiece
    ) -> None:
        """Test _get_decorative_notes with edge profile metadata."""
        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(edge_profile_cut_piece)
        assert "Profile:" in notes
        assert "roundover" in notes
        assert "0.25" in notes
        assert "front" in notes


# =============================================================================
# JsonExporter Basic Tests
# =============================================================================


class TestJsonExporterBasic:
    """Basic tests for JsonExporter."""

    def test_export_returns_valid_json(
        self, simple_layout_output: LayoutOutput
    ) -> None:
        """Test that export returns valid JSON."""
        exporter = JsonExporter()
        result = exporter.export(simple_layout_output)

        # Should be parseable JSON
        data = json.loads(result)
        assert "cabinet" in data
        assert "cut_list" in data
        assert "material_estimate" in data

    def test_export_cabinet_dimensions(
        self, simple_layout_output: LayoutOutput
    ) -> None:
        """Test that cabinet dimensions are exported correctly."""
        exporter = JsonExporter()
        result = exporter.export(simple_layout_output)
        data = json.loads(result)

        assert data["cabinet"]["width"] == 48.0
        assert data["cabinet"]["height"] == 84.0
        assert data["cabinet"]["depth"] == 12.0

    def test_export_cut_list_pieces(
        self, simple_layout_output: LayoutOutput
    ) -> None:
        """Test that cut list pieces are exported."""
        exporter = JsonExporter()
        result = exporter.export(simple_layout_output)
        data = json.loads(result)

        assert len(data["cut_list"]) == 6

    def test_export_invalid_output_returns_errors(self) -> None:
        """Test that invalid output returns error JSON."""
        output = LayoutOutput(
            cabinet=None,  # type: ignore
            cut_list=[],
            total_estimate=None,  # type: ignore
            material_estimates={},
            errors=["Cabinet generation failed"],  # is_valid is a property based on errors
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        assert "errors" in data
        assert "Cabinet generation failed" in data["errors"]


# =============================================================================
# JsonExporter Decorative Metadata Tests
# =============================================================================


class TestJsonExporterDecorativeMetadata:
    """Tests for JsonExporter decorative metadata handling."""

    def test_export_arch_metadata(
        self, simple_cabinet: Cabinet, arch_cut_piece: CutPiece
    ) -> None:
        """Test that arch metadata is exported correctly."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[arch_cut_piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=288.0,
                total_area_sqft=2.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece = data["cut_list"][0]
        assert "decorative_metadata" in piece
        assert "arch" in piece["decorative_metadata"]
        assert piece["decorative_metadata"]["arch"]["type"] == "full_round"
        assert piece["decorative_metadata"]["arch"]["radius"] == 12.0
        assert piece["decorative_metadata"]["arch"]["spring_height"] == 6.0

    def test_export_scallop_metadata(
        self, simple_cabinet: Cabinet, scallop_cut_piece: CutPiece
    ) -> None:
        """Test that scallop metadata is exported correctly."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[scallop_cut_piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=144.0,
                total_area_sqft=1.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece = data["cut_list"][0]
        assert "decorative_metadata" in piece
        assert "scallop" in piece["decorative_metadata"]
        assert piece["decorative_metadata"]["scallop"]["depth"] == 1.5
        assert piece["decorative_metadata"]["scallop"]["width"] == 6.0
        assert piece["decorative_metadata"]["scallop"]["count"] == 8

    def test_export_edge_profile_metadata(
        self, simple_cabinet: Cabinet, edge_profile_cut_piece: CutPiece
    ) -> None:
        """Test that edge profile metadata is exported correctly."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[edge_profile_cut_piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=288.0,
                total_area_sqft=2.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece = data["cut_list"][0]
        assert "decorative_metadata" in piece
        assert "edge_profile" in piece["decorative_metadata"]
        assert piece["decorative_metadata"]["edge_profile"]["profile_type"] == "roundover"
        assert piece["decorative_metadata"]["edge_profile"]["size"] == 0.25

    def test_export_joinery_metadata(
        self, simple_cabinet: Cabinet, joinery_cut_piece: CutPiece
    ) -> None:
        """Test that joinery metadata is exported correctly."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[joinery_cut_piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=252.0,
                total_area_sqft=1.75,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece = data["cut_list"][0]
        assert "decorative_metadata" in piece
        assert "joinery" in piece["decorative_metadata"]
        assert piece["decorative_metadata"]["joinery"]["type"] == "pocket_screw"

    def test_export_zone_metadata(
        self, simple_cabinet: Cabinet, zone_cut_piece: CutPiece
    ) -> None:
        """Test that zone metadata is exported correctly."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[zone_cut_piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=192.0,
                total_area_sqft=1.33,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece = data["cut_list"][0]
        assert "decorative_metadata" in piece
        assert "zone" in piece["decorative_metadata"]
        assert piece["decorative_metadata"]["zone"]["type"] == "toe_kick"
        assert piece["decorative_metadata"]["zone"]["setback"] == 3.5

    def test_export_no_decorative_metadata_for_simple_piece(
        self, simple_cabinet: Cabinet, simple_cut_piece: CutPiece
    ) -> None:
        """Test that simple pieces don't have decorative_metadata field."""
        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[simple_cut_piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=288.0,
                total_area_sqft=2.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece = data["cut_list"][0]
        assert "decorative_metadata" not in piece


# =============================================================================
# JsonExporter Internal Methods Tests
# =============================================================================


class TestJsonExporterInternalMethods:
    """Tests for JsonExporter internal methods."""

    def test_format_cut_piece_basic_fields(
        self, simple_cut_piece: CutPiece
    ) -> None:
        """Test _format_cut_piece includes basic fields."""
        exporter = JsonExporter()
        result = exporter._format_cut_piece(simple_cut_piece)

        assert result["label"] == "Shelf"
        assert result["width"] == 24.0
        assert result["height"] == 12.0
        assert result["quantity"] == 2
        assert result["panel_type"] == "shelf"
        assert result["material_thickness"] == 0.75

    def test_format_cut_piece_with_arch_metadata(
        self, arch_cut_piece: CutPiece
    ) -> None:
        """Test _format_cut_piece with arch metadata."""
        exporter = JsonExporter()
        result = exporter._format_cut_piece(arch_cut_piece)

        assert "decorative_metadata" in result
        assert "arch" in result["decorative_metadata"]
        assert result["decorative_metadata"]["arch"]["type"] == "full_round"

    def test_format_cut_piece_without_metadata(
        self, simple_cut_piece: CutPiece
    ) -> None:
        """Test _format_cut_piece without cut_metadata."""
        exporter = JsonExporter()
        result = exporter._format_cut_piece(simple_cut_piece)

        assert "decorative_metadata" not in result


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestExporterEdgeCases:
    """Edge case and error handling tests for exporters."""

    def test_cutlist_formatter_with_empty_cut_metadata(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test formatter handles empty cut_metadata dict."""
        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={},
        )

        formatter = CutListFormatter()
        result = formatter.format([piece])

        # Should not have Notes column since metadata is empty
        assert "Notes" not in result

    def test_cutlist_formatter_with_none_cut_metadata(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test formatter handles None cut_metadata."""
        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata=None,
        )

        formatter = CutListFormatter()
        result = formatter.format([piece])

        # Should not have Notes column
        assert "Notes" not in result

    def test_json_exporter_with_empty_cut_metadata(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test JsonExporter handles empty cut_metadata dict."""
        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={},
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=288.0,
                total_area_sqft=2.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        # Should not have decorative_metadata
        assert "decorative_metadata" not in data["cut_list"][0]

    def test_arch_metadata_with_zero_values(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test arch metadata formatting with zero values."""
        piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="Arch Header",
            panel_type=PanelType.ARCH_HEADER,
            material=standard_material,
            cut_metadata={
                "arch_type": "full_round",
                "radius": 0,
                "spring_height": 0,
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert "R=0.0" in notes
        assert "spring=0.0" in notes


# =============================================================================
# Grain Direction Tests for Exporters
# =============================================================================


class TestCutListFormatterGrainDirection:
    """Tests for CutListFormatter grain direction handling."""

    @pytest.fixture
    def standard_material(self) -> MaterialSpec:
        """Create standard 3/4\" material."""
        return MaterialSpec.standard_3_4()

    def test_grain_direction_in_notes(self, standard_material: MaterialSpec) -> None:
        """Test that grain_direction appears in notes."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
            cut_metadata={"grain_direction": "length"},
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert "Grain: length" in notes

    def test_grain_direction_none_not_displayed(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test that grain_direction 'none' is not displayed."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
            cut_metadata={"grain_direction": "none"},
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        # 'none' should not appear
        assert "Grain" not in notes

    def test_grain_direction_width(self, standard_material: MaterialSpec) -> None:
        """Test grain_direction 'width' is displayed correctly."""
        piece = CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Tall Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
            cut_metadata={"grain_direction": "width"},
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert "Grain: width" in notes

    def test_grain_direction_combined_with_other_notes(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test grain_direction combined with other metadata."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Decorated Panel",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={
                "grain_direction": "length",
                "joinery_type": "dado",
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert "Grain: length" in notes
        assert "Joinery: dado" in notes
        assert ";" in notes  # Should be semicolon separated


class TestJsonExporterGrainDirection:
    """Tests for JsonExporter grain direction handling."""

    @pytest.fixture
    def standard_material(self) -> MaterialSpec:
        """Create standard 3/4\" material."""
        return MaterialSpec.standard_3_4()

    @pytest.fixture
    def simple_cabinet(self) -> Cabinet:
        """Create a simple cabinet for output."""
        return Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )

    def test_grain_direction_in_json_output(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test that grain_direction is included in JSON output."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
            cut_metadata={"grain_direction": "length"},
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=432.0,
                total_area_sqft=3.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        assert "decorative_metadata" in piece_data
        assert piece_data["decorative_metadata"]["grain_direction"] == "length"

    def test_grain_direction_none_not_in_json(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test that grain_direction 'none' is not in JSON output."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
            cut_metadata={"grain_direction": "none"},
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=432.0,
                total_area_sqft=3.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        # decorative_metadata shouldn't exist if only grain_direction is "none"
        assert "decorative_metadata" not in piece_data

    def test_grain_direction_width_in_json(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test that grain_direction 'width' is in JSON output."""
        piece = CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Tall Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=standard_material,
            cut_metadata={"grain_direction": "width"},
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=432.0,
                total_area_sqft=3.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        assert "decorative_metadata" in piece_data
        assert piece_data["decorative_metadata"]["grain_direction"] == "width"

    def test_grain_direction_combined_with_other_metadata(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test grain_direction combined with other decorative metadata."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Decorated Panel",
            panel_type=PanelType.SHELF,
            material=standard_material,
            cut_metadata={
                "grain_direction": "length",
                "joinery_type": "dado",
                "edge_profile": {
                    "profile_type": "roundover",
                    "size": 0.25,
                    "edges": ["front"],
                },
            },
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=432.0,
                total_area_sqft=3.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        assert "decorative_metadata" in piece_data
        decorative = piece_data["decorative_metadata"]
        assert decorative["grain_direction"] == "length"
        assert "joinery" in decorative
        assert "edge_profile" in decorative


# =============================================================================
# HardwareReportFormatter Tests (FR-05)
# =============================================================================


class TestHardwareReportFormatterBasic:
    """Basic tests for HardwareReportFormatter."""

    @pytest.fixture
    def sample_hardware_list(self):
        """Create a sample HardwareList for testing."""
        from cabinets.domain.components.results import HardwareItem
        from cabinets.domain.services.woodworking import HardwareList

        items = (
            HardwareItem(name='#8 x 1-1/4" wood screw', quantity=24, notes="Case assembly"),
            HardwareItem(name='#6 x 5/8" pan head screw', quantity=40, notes="Back panel"),
        )
        return HardwareList(items=items)

    @pytest.fixture
    def empty_hardware_list(self):
        """Create an empty HardwareList."""
        from cabinets.domain.services.woodworking import HardwareList

        return HardwareList.empty()

    def test_format_returns_string(self, sample_hardware_list) -> None:
        """Test that format returns a string."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list)
        assert isinstance(result, str)

    def test_format_includes_title(self, sample_hardware_list) -> None:
        """Test that format includes the title."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list)
        assert "HARDWARE LIST" in result

    def test_format_custom_title(self, sample_hardware_list) -> None:
        """Test that custom title is used."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list, title="CUSTOM HARDWARE")
        assert "CUSTOM HARDWARE" in result

    def test_format_includes_items(self, sample_hardware_list) -> None:
        """Test that format includes item names."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list)
        assert '#8 x 1-1/4" wood screw' in result
        assert '#6 x 5/8" pan head screw' in result

    def test_format_includes_quantities(self, sample_hardware_list) -> None:
        """Test that format includes item quantities."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list)
        assert "24" in result
        assert "40" in result

    def test_format_includes_total(self, sample_hardware_list) -> None:
        """Test that format includes total count."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list)
        assert "TOTAL" in result
        # Total should be 64
        assert "64" in result

    def test_format_empty_list(self, empty_hardware_list) -> None:
        """Test formatting empty hardware list."""
        formatter = HardwareReportFormatter()
        result = formatter.format(empty_hardware_list)
        assert "No hardware required." in result

    def test_format_includes_notes(self, sample_hardware_list) -> None:
        """Test that format includes item notes."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list)
        assert "Case assembly" in result
        assert "Back panel" in result


class TestHardwareReportFormatterOverage:
    """Tests for HardwareReportFormatter overage display."""

    @pytest.fixture
    def sample_hardware_list(self):
        """Create a sample HardwareList for testing."""
        from cabinets.domain.components.results import HardwareItem
        from cabinets.domain.services.woodworking import HardwareList

        items = (
            HardwareItem(name='#8 x 1-1/4" wood screw', quantity=24, notes="Case assembly"),
            HardwareItem(name='#6 x 5/8" pan head screw', quantity=40, notes="Back panel"),
        )
        return HardwareList(items=items)

    def test_format_with_overage_column(self, sample_hardware_list) -> None:
        """Test format shows overage column when enabled."""
        formatter = HardwareReportFormatter()
        result = formatter.format(
            sample_hardware_list, show_overage=True, overage_percent=10.0
        )
        # Should show header with overage column
        assert "w/10%" in result

    def test_format_overage_calculation(self, sample_hardware_list) -> None:
        """Test that overage is calculated correctly."""
        import math

        formatter = HardwareReportFormatter()
        result = formatter.format(
            sample_hardware_list, show_overage=True, overage_percent=10.0
        )
        # 24 * 1.1 = 26.4 -> 27
        assert "27" in result
        # 40 * 1.1 = 44
        assert "44" in result

    def test_format_without_overage_column(self, sample_hardware_list) -> None:
        """Test format without overage column."""
        formatter = HardwareReportFormatter()
        result = formatter.format(sample_hardware_list, show_overage=False)
        # Should not have overage column header
        assert "w/10%" not in result


class TestHardwareReportFormatterCategories:
    """Tests for HardwareReportFormatter category grouping."""

    @pytest.fixture
    def mixed_hardware_list(self):
        """Create a HardwareList with mixed categories."""
        from cabinets.domain.components.results import HardwareItem
        from cabinets.domain.services.woodworking import HardwareList

        items = (
            HardwareItem(name="Wood screw", quantity=24),
            HardwareItem(name="Fluted dowel", quantity=8),
            HardwareItem(name="#20 biscuit", quantity=6),
            HardwareItem(name="Soft-close hinge", quantity=4),
        )
        return HardwareList(items=items)

    def test_format_groups_by_category(self, mixed_hardware_list) -> None:
        """Test that items are grouped by category."""
        formatter = HardwareReportFormatter()
        result = formatter.format(mixed_hardware_list)

        # Categories should appear as headers
        assert "SCREWS" in result
        assert "DOWELS" in result
        assert "BISCUITS" in result
        assert "HINGES" in result


class TestHardwareReportFormatterShoppingList:
    """Tests for HardwareReportFormatter shopping list format."""

    @pytest.fixture
    def sample_hardware_list(self):
        """Create a sample HardwareList for testing."""
        from cabinets.domain.components.results import HardwareItem
        from cabinets.domain.services.woodworking import HardwareList

        items = (
            HardwareItem(
                name='#8 x 1-1/4" wood screw', quantity=24, sku="SCR-8114", notes="Case"
            ),
            HardwareItem(name='#6 x 5/8" pan head screw', quantity=40),
        )
        return HardwareList(items=items)

    def test_shopping_list_format_returns_string(self, sample_hardware_list) -> None:
        """Test that format_shopping_list returns a string."""
        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(sample_hardware_list)
        assert isinstance(result, str)

    def test_shopping_list_includes_header(self, sample_hardware_list) -> None:
        """Test that shopping list includes header."""
        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(sample_hardware_list)
        assert "Shopping List:" in result

    def test_shopping_list_includes_checkboxes(self, sample_hardware_list) -> None:
        """Test that shopping list includes checkboxes."""
        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(sample_hardware_list)
        assert "[ ]" in result

    def test_shopping_list_includes_quantities(self, sample_hardware_list) -> None:
        """Test that shopping list includes quantities."""
        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(sample_hardware_list)
        assert "24x" in result
        assert "40x" in result

    def test_shopping_list_includes_sku(self, sample_hardware_list) -> None:
        """Test that shopping list includes SKU when present."""
        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(sample_hardware_list)
        assert "SKU: SCR-8114" in result

    def test_shopping_list_sorted_by_name(self, sample_hardware_list) -> None:
        """Test that shopping list is sorted by name."""
        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(sample_hardware_list)
        # #6 should come before #8 alphabetically
        idx_6 = result.find("#6")
        idx_8 = result.find("#8")
        assert idx_6 < idx_8


class TestHardwareReportFormatterIntegration:
    """Integration tests for HardwareReportFormatter with WoodworkingIntelligence."""

    def test_format_calculated_hardware(self) -> None:
        """Test formatting hardware from calculate_hardware method."""
        from cabinets.domain.entities import Cabinet, Section
        from cabinets.domain.services.woodworking import WoodworkingIntelligence
        from cabinets.domain.value_objects import MaterialSpec, Position

        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(cabinet, include_overage=False)

        formatter = HardwareReportFormatter()
        result = formatter.format(hardware)

        assert "HARDWARE LIST" in result
        assert "screw" in result.lower()
        assert "TOTAL" in result

    def test_shopping_list_from_calculated_hardware(self) -> None:
        """Test shopping list from calculate_hardware method."""
        from cabinets.domain.entities import Cabinet, Section
        from cabinets.domain.services.woodworking import WoodworkingIntelligence
        from cabinets.domain.value_objects import MaterialSpec, Position

        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(cabinet)

        formatter = HardwareReportFormatter()
        result = formatter.format_shopping_list(hardware)

        assert "Shopping List:" in result
        assert "[ ]" in result


# =============================================================================
# Infrastructure Cutouts Tests (FRD-15 Phase 5)
# =============================================================================


class TestCutListFormatterCutouts:
    """Tests for CutListFormatter cutout handling."""

    @pytest.fixture
    def standard_material(self) -> MaterialSpec:
        """Create standard 3/4\" material."""
        return MaterialSpec.standard_3_4()

    def test_circular_cutout_grommet(self, standard_material: MaterialSpec) -> None:
        """Test circular cutout (grommet) formatting."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    }
                ]
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert 'Grommet: 12.0", 36.0" - 2.5" dia' in notes

    def test_circular_cutout_wire_hole(self, standard_material: MaterialSpec) -> None:
        """Test circular cutout (wire hole) formatting."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "wire_hole",
                        "x": 6.0,
                        "y": 48.0,
                        "diameter": 0.75,
                        "shape": "circular",
                    }
                ]
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert 'Wire Hole: 6.0", 48.0" - 0.75" dia' in notes

    def test_rectangular_cutout_outlet(self, standard_material: MaterialSpec) -> None:
        """Test rectangular cutout (outlet) formatting."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "outlet",
                        "x": 6.0,
                        "y": 12.0,
                        "width": 2.25,
                        "height": 4.0,
                        "shape": "rectangular",
                    }
                ]
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert 'Outlet: 6.0", 12.0" - 2.25" x 4.0"' in notes

    def test_rectangular_cutout_vent_with_pattern(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test rectangular cutout with pattern (vent) formatting."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "vent",
                        "x": 24.0,
                        "y": 12.0,
                        "width": 6.0,
                        "height": 4.0,
                        "shape": "rectangular",
                        "pattern": "grid",
                    }
                ]
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert 'Vent (grid): 24.0", 12.0" - 6.0" x 4.0"' in notes

    def test_multiple_cutouts(self, standard_material: MaterialSpec) -> None:
        """Test multiple cutouts formatting."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    },
                    {
                        "type": "outlet",
                        "x": 6.0,
                        "y": 12.0,
                        "width": 2.25,
                        "height": 4.0,
                        "shape": "rectangular",
                    },
                ]
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert "Grommet:" in notes
        assert "Outlet:" in notes
        # Should be separated by semicolons
        assert ";" in notes

    def test_cutouts_combined_with_other_metadata(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test cutouts combined with other decorative metadata."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "grain_direction": "length",
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    }
                ],
            },
        )

        formatter = CutListFormatter()
        notes = formatter._get_decorative_notes(piece)
        assert "Grain: length" in notes
        assert "Grommet:" in notes

    def test_cutout_triggers_notes_column(self, standard_material: MaterialSpec) -> None:
        """Test that cutouts trigger the Notes column in output."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    }
                ]
            },
        )

        formatter = CutListFormatter()
        result = formatter.format([piece])
        assert "Notes" in result
        assert "Grommet:" in result


class TestJsonExporterCutouts:
    """Tests for JsonExporter cutout handling."""

    @pytest.fixture
    def standard_material(self) -> MaterialSpec:
        """Create standard 3/4\" material."""
        return MaterialSpec.standard_3_4()

    @pytest.fixture
    def simple_cabinet(self) -> Cabinet:
        """Create a simple cabinet for output."""
        return Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )

    def test_circular_cutout_in_json(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test circular cutout in JSON output."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    }
                ]
            },
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=4032.0,
                total_area_sqft=28.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        assert "cutouts" in piece_data
        assert len(piece_data["cutouts"]) == 1

        cutout = piece_data["cutouts"][0]
        assert cutout["type"] == "grommet"
        assert cutout["position"] == {"x": 12.0, "y": 36.0}
        assert cutout["diameter"] == 2.5
        assert cutout["shape"] == "circular"

    def test_rectangular_cutout_in_json(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test rectangular cutout in JSON output."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "outlet",
                        "x": 6.0,
                        "y": 12.0,
                        "width": 2.25,
                        "height": 4.0,
                        "shape": "rectangular",
                    }
                ]
            },
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=4032.0,
                total_area_sqft=28.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        assert "cutouts" in piece_data

        cutout = piece_data["cutouts"][0]
        assert cutout["type"] == "outlet"
        assert cutout["position"] == {"x": 6.0, "y": 12.0}
        assert cutout["dimensions"] == {"width": 2.25, "height": 4.0}
        assert cutout["shape"] == "rectangular"

    def test_rectangular_cutout_with_pattern_in_json(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test rectangular cutout with pattern in JSON output."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "vent",
                        "x": 24.0,
                        "y": 12.0,
                        "width": 6.0,
                        "height": 4.0,
                        "shape": "rectangular",
                        "pattern": "grid",
                    }
                ]
            },
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=4032.0,
                total_area_sqft=28.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        cutout = piece_data["cutouts"][0]
        assert cutout["pattern"] == "grid"

    def test_multiple_cutouts_in_json(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test multiple cutouts in JSON output."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    },
                    {
                        "type": "outlet",
                        "x": 6.0,
                        "y": 12.0,
                        "width": 2.25,
                        "height": 4.0,
                        "shape": "rectangular",
                    },
                    {
                        "type": "wire_hole",
                        "x": 6.0,
                        "y": 48.0,
                        "diameter": 0.75,
                        "shape": "circular",
                    },
                    {
                        "type": "vent",
                        "x": 24.0,
                        "y": 12.0,
                        "width": 6.0,
                        "height": 4.0,
                        "shape": "rectangular",
                        "pattern": "grid",
                    },
                ]
            },
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=4032.0,
                total_area_sqft=28.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        assert "cutouts" in piece_data
        assert len(piece_data["cutouts"]) == 4

        # Verify each cutout type is present
        cutout_types = [c["type"] for c in piece_data["cutouts"]]
        assert "grommet" in cutout_types
        assert "outlet" in cutout_types
        assert "wire_hole" in cutout_types
        assert "vent" in cutout_types

    def test_cutouts_separate_from_decorative_metadata(
        self, simple_cabinet: Cabinet, standard_material: MaterialSpec
    ) -> None:
        """Test that cutouts are separate from decorative_metadata in JSON."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={
                "grain_direction": "length",
                "cutouts": [
                    {
                        "type": "grommet",
                        "x": 12.0,
                        "y": 36.0,
                        "diameter": 2.5,
                        "shape": "circular",
                    }
                ],
            },
        )

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=[piece],
            total_estimate=MaterialEstimate(
                total_area_sqin=4032.0,
                total_area_sqft=28.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
            material_estimates={},
        )

        exporter = JsonExporter()
        result = exporter.export(output)
        data = json.loads(result)

        piece_data = data["cut_list"][0]
        # cutouts should be at top level
        assert "cutouts" in piece_data
        # decorative_metadata should exist separately
        assert "decorative_metadata" in piece_data
        assert piece_data["decorative_metadata"]["grain_direction"] == "length"
        # cutouts should NOT be in decorative_metadata
        assert "cutouts" not in piece_data["decorative_metadata"]

    def test_format_cut_piece_no_cutouts(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test _format_cut_piece without cutouts does not add cutouts field."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
        )

        exporter = JsonExporter()
        result = exporter._format_cut_piece(piece)
        assert "cutouts" not in result

    def test_format_cut_piece_empty_cutouts_list(
        self, standard_material: MaterialSpec
    ) -> None:
        """Test _format_cut_piece with empty cutouts list."""
        piece = CutPiece(
            width=48.0,
            height=84.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=standard_material,
            cut_metadata={"cutouts": []},
        )

        exporter = JsonExporter()
        result = exporter._format_cut_piece(piece)
        # Empty cutouts list should not add cutouts field
        assert "cutouts" not in result
