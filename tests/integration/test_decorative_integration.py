"""Integration tests for decorative elements (FRD-12).

These tests verify that decorative configuration parsing, component generation,
and cut list formatting work together correctly through the full pipeline.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from cabinets.application.config.schema import (
    ArchTopConfigSchema,
    BaseZoneConfigSchema,
    CabinetConfig,
    CabinetConfiguration,
    CrownMoldingConfigSchema,
    EdgeProfileConfigSchema,
    FaceFrameConfigSchema,
    LightRailConfigSchema,
    ScallopConfigSchema,
    SectionConfig,
)
from cabinets.domain.entities import Cabinet
from cabinets.domain.services import MaterialEstimate
from cabinets.domain.value_objects import CutPiece, MaterialSpec, PanelType
from cabinets.infrastructure.exporters import CutListFormatter, JsonExporter


# =============================================================================
# Configuration Parsing Tests
# =============================================================================


class TestDecorativeConfigParsing:
    """Tests for parsing decorative configuration from JSON."""

    def test_parse_face_frame_config(self) -> None:
        """Parse cabinet config with face frame."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {
                    "stile_width": 1.5,
                    "rail_width": 2.0,
                    "joinery": "mortise_tenon"
                }
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.face_frame is not None
        assert config.cabinet.face_frame.stile_width == 1.5
        assert config.cabinet.face_frame.rail_width == 2.0
        assert config.cabinet.face_frame.joinery.value == "mortise_tenon"

    def test_parse_crown_molding_config(self) -> None:
        """Parse cabinet config with crown molding zone."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "crown_molding": {
                    "height": 4.0,
                    "setback": 1.0,
                    "nailer_width": 2.5
                }
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.crown_molding is not None
        assert config.cabinet.crown_molding.height == 4.0
        assert config.cabinet.crown_molding.setback == 1.0
        assert config.cabinet.crown_molding.nailer_width == 2.5

    def test_parse_base_zone_config(self) -> None:
        """Parse cabinet config with toe kick zone."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "base_zone": {
                    "zone_type": "toe_kick",
                    "height": 4.0,
                    "setback": 3.0
                }
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.base_zone is not None
        assert config.cabinet.base_zone.zone_type == "toe_kick"
        assert config.cabinet.base_zone.height == 4.0
        assert config.cabinet.base_zone.setback == 3.0

    def test_parse_light_rail_config(self) -> None:
        """Parse cabinet config with light rail zone."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 36.0,
                "height": 30.0,
                "depth": 12.0,
                "light_rail": {
                    "height": 1.5,
                    "setback": 0.25,
                    "generate_strip": true
                }
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.light_rail is not None
        assert config.cabinet.light_rail.height == 1.5
        assert config.cabinet.light_rail.setback == 0.25
        assert config.cabinet.light_rail.generate_strip is True

    def test_parse_arch_top_section(self) -> None:
        """Parse section config with arch top."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {
                        "width": 24.0,
                        "arch_top": {
                            "arch_type": "segmental",
                            "radius": 18.0,
                            "spring_height": 6.0
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert len(config.cabinet.sections) == 1
        assert config.cabinet.sections[0].arch_top is not None
        assert config.cabinet.sections[0].arch_top.arch_type.value == "segmental"
        assert config.cabinet.sections[0].arch_top.radius == 18.0
        assert config.cabinet.sections[0].arch_top.spring_height == 6.0

    def test_parse_arch_top_auto_radius(self) -> None:
        """Parse section config with arch top using auto radius."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {
                        "width": 24.0,
                        "arch_top": {
                            "arch_type": "full_round",
                            "radius": "auto"
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.sections[0].arch_top is not None
        assert config.cabinet.sections[0].arch_top.radius == "auto"

    def test_parse_edge_profile_section(self) -> None:
        """Parse section config with edge profile."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {
                        "width": 48.0,
                        "shelves": 4,
                        "edge_profile": {
                            "profile_type": "roundover",
                            "size": 0.25,
                            "edges": ["front"]
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.sections[0].edge_profile is not None
        assert config.cabinet.sections[0].edge_profile.profile_type.value == "roundover"
        assert config.cabinet.sections[0].edge_profile.size == 0.25
        assert config.cabinet.sections[0].edge_profile.edges == ["front"]

    def test_parse_scallop_section(self) -> None:
        """Parse section config with scallop pattern."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {
                        "width": 48.0,
                        "scallop": {
                            "depth": 1.5,
                            "width": 6.0,
                            "count": 8
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.sections[0].scallop is not None
        assert config.cabinet.sections[0].scallop.depth == 1.5
        assert config.cabinet.sections[0].scallop.width == 6.0
        assert config.cabinet.sections[0].scallop.count == 8

    def test_parse_full_decorative_config(self) -> None:
        """Parse cabinet with all decorative elements."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {
                    "stile_width": 1.5,
                    "rail_width": 2.0,
                    "joinery": "pocket_screw"
                },
                "crown_molding": {
                    "height": 4.0,
                    "setback": 1.0
                },
                "base_zone": {
                    "zone_type": "toe_kick",
                    "height": 4.0,
                    "setback": 3.0
                },
                "sections": [
                    {
                        "width": 24.0,
                        "arch_top": {
                            "arch_type": "full_round",
                            "radius": "auto"
                        }
                    },
                    {
                        "width": "fill",
                        "shelves": 5,
                        "edge_profile": {
                            "profile_type": "ogee",
                            "size": 0.375
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        # Verify all decorative elements parsed
        assert config.cabinet.face_frame is not None
        assert config.cabinet.crown_molding is not None
        assert config.cabinet.base_zone is not None
        assert config.cabinet.sections[0].arch_top is not None
        assert config.cabinet.sections[1].edge_profile is not None


# =============================================================================
# Cut List Integration Tests
# =============================================================================


class TestCutListWithDecorativeMetadata:
    """Tests for cut list output with decorative metadata."""

    def test_cut_list_shows_notes_column_when_decorative_present(self) -> None:
        """Cut list includes Notes column when decorative pieces present."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=1.5,
                height=84.0,
                quantity=2,
                label="Face Frame Stile",
                panel_type=PanelType.FACE_FRAME_STILE,
                material=material,
                cut_metadata={"joinery_type": "pocket_screw"},
            ),
            CutPiece(
                width=24.0,
                height=0.75,
                quantity=1,
                label="Top Panel",
                panel_type=PanelType.TOP,
                material=material,
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        # Should have Notes column (wider format)
        assert "Notes" in output
        assert "Joinery: pocket_screw" in output

    def test_cut_list_formats_arch_metadata(self) -> None:
        """Cut list formats arch metadata correctly."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=24.0,
                height=12.0,
                quantity=1,
                label="Arch Header",
                panel_type=PanelType.ARCH_HEADER,
                material=material,
                cut_metadata={
                    "arch_type": "full_round",
                    "radius": 12.0,
                    "spring_height": 6.0,
                },
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        assert "Arch: full_round" in output
        assert "R=12.0" in output
        assert "spring=6.0" in output

    def test_cut_list_formats_scallop_metadata(self) -> None:
        """Cut list formats scallop template information."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=48.0,
                height=3.0,
                quantity=1,
                label="Valance",
                panel_type=PanelType.VALANCE,
                material=material,
                cut_metadata={
                    "scallop_depth": 1.5,
                    "scallop_width": 6.0,
                    "scallop_count": 8,
                },
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        assert "Scallop:" in output
        assert "8x" in output
        assert "6.00" in output
        assert "1.50" in output

    def test_cut_list_formats_edge_profile_metadata(self) -> None:
        """Cut list formats edge profile information."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=24.0,
                height=12.0,
                quantity=4,
                label="Shelf",
                panel_type=PanelType.SHELF,
                material=material,
                cut_metadata={
                    "edge_profile": {
                        "profile_type": "roundover",
                        "size": 0.25,
                        "edges": ["front"],
                    },
                },
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        assert "Profile: roundover" in output
        assert "0.25" in output
        assert "front" in output


# =============================================================================
# JSON Export Integration Tests
# =============================================================================


class TestJsonExportWithDecorativeMetadata:
    """Tests for JSON export with decorative metadata."""

    @pytest.fixture
    def simple_cabinet(self) -> Cabinet:
        """Create a simple cabinet for testing."""
        return Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )

    def test_json_export_includes_arch_metadata(self, simple_cabinet: Cabinet) -> None:
        """JSON export includes arch metadata in decorative_metadata object."""
        from cabinets.application.dtos import LayoutOutput

        material = MaterialSpec(thickness=0.75)
        cut_list = [
            CutPiece(
                width=24.0,
                height=12.0,
                quantity=1,
                label="Arch Header",
                panel_type=PanelType.ARCH_HEADER,
                material=material,
                cut_metadata={
                    "arch_type": "full_round",
                    "radius": 12.0,
                    "spring_height": 0.0,
                },
            ),
        ]

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=cut_list,
            material_estimates={},
            total_estimate=MaterialEstimate(
                total_area_sqin=288.0,
                total_area_sqft=2.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
        )

        exporter = JsonExporter()
        json_str = exporter.export(output)
        data = json.loads(json_str)

        # Check decorative metadata in cut list
        arch_piece = data["cut_list"][0]
        assert "decorative_metadata" in arch_piece
        assert "arch" in arch_piece["decorative_metadata"]
        assert arch_piece["decorative_metadata"]["arch"]["type"] == "full_round"
        assert arch_piece["decorative_metadata"]["arch"]["radius"] == 12.0

    def test_json_export_includes_multiple_decorative_types(
        self, simple_cabinet: Cabinet
    ) -> None:
        """JSON export handles multiple decorative metadata types."""
        from cabinets.application.dtos import LayoutOutput

        material = MaterialSpec(thickness=0.75)
        cut_list = [
            CutPiece(
                width=24.0,
                height=12.0,
                quantity=1,
                label="Arch Header",
                panel_type=PanelType.ARCH_HEADER,
                material=material,
                cut_metadata={
                    "arch_type": "segmental",
                    "radius": 18.0,
                    "spring_height": 4.0,
                },
            ),
            CutPiece(
                width=1.5,
                height=84.0,
                quantity=2,
                label="Stile",
                panel_type=PanelType.FACE_FRAME_STILE,
                material=material,
                cut_metadata={"joinery_type": "mortise_tenon"},
            ),
            CutPiece(
                width=48.0,
                height=4.0,
                quantity=1,
                label="Toe Kick",
                panel_type=PanelType.TOE_KICK,
                material=material,
                cut_metadata={"zone_type": "toe_kick", "setback": 3.5},
            ),
        ]

        output = LayoutOutput(
            cabinet=simple_cabinet,
            cut_list=cut_list,
            material_estimates={},
            total_estimate=MaterialEstimate(
                total_area_sqin=500.0,
                total_area_sqft=3.47,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
        )

        exporter = JsonExporter()
        json_str = exporter.export(output)
        data = json.loads(json_str)

        # Verify all pieces have correct decorative metadata
        assert len(data["cut_list"]) == 3

        arch_piece = data["cut_list"][0]
        assert "arch" in arch_piece["decorative_metadata"]

        stile_piece = data["cut_list"][1]
        assert "joinery" in stile_piece["decorative_metadata"]
        assert stile_piece["decorative_metadata"]["joinery"]["type"] == "mortise_tenon"

        toe_kick_piece = data["cut_list"][2]
        assert "zone" in toe_kick_piece["decorative_metadata"]
        assert toe_kick_piece["decorative_metadata"]["zone"]["type"] == "toe_kick"


# =============================================================================
# Schema Version Tests
# =============================================================================


class TestSchemaVersionCompatibility:
    """Tests for schema version handling with decorative elements."""

    def test_v13_supports_decorative(self) -> None:
        """Schema version 1.3 supports all decorative fields."""
        config = CabinetConfiguration(
            schema_version="1.3",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                face_frame=FaceFrameConfigSchema(stile_width=1.5),
                crown_molding=CrownMoldingConfigSchema(height=4.0),
                base_zone=BaseZoneConfigSchema(height=4.0),
            ),
        )
        assert config.schema_version == "1.3"
        assert config.cabinet.face_frame is not None
        assert config.cabinet.crown_molding is not None
        assert config.cabinet.base_zone is not None

    def test_v10_without_decorative_still_works(self) -> None:
        """Schema version 1.0 configs without decorative elements still parse."""
        config_json = """
        {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{"width": 48.0, "shelves": 3}]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.cabinet.face_frame is None
        assert config.cabinet.crown_molding is None
        assert config.cabinet.base_zone is None
        assert config.cabinet.light_rail is None

    def test_v11_backward_compatible(self) -> None:
        """Schema version 1.1 configs are backward compatible."""
        config_json = """
        {
            "schema_version": "1.1",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.schema_version == "1.1"

    def test_v12_backward_compatible(self) -> None:
        """Schema version 1.2 configs are backward compatible."""
        config_json = """
        {
            "schema_version": "1.2",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.schema_version == "1.2"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestDecorativeErrorHandling:
    """Tests for error handling with decorative elements."""

    def test_invalid_joinery_type_raises(self) -> None:
        """Invalid joinery type raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {
                    "joinery": "invalid_type"
                }
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_invalid_arch_type_raises(self) -> None:
        """Invalid arch type raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{
                    "width": 24.0,
                    "arch_top": {"arch_type": "gothic"}
                }]
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_invalid_edge_profile_type_raises(self) -> None:
        """Invalid edge profile type raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{
                    "width": 24.0,
                    "edge_profile": {"profile_type": "invalid", "size": 0.25}
                }]
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_negative_stile_width_raises(self) -> None:
        """Negative stile width raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {"stile_width": -1.0}
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_negative_arch_radius_raises(self) -> None:
        """Negative arch radius raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{
                    "width": 24.0,
                    "arch_top": {"arch_type": "segmental", "radius": -5.0}
                }]
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_zero_edge_profile_size_raises(self) -> None:
        """Zero edge profile size raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{
                    "width": 24.0,
                    "edge_profile": {"profile_type": "roundover", "size": 0}
                }]
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_negative_scallop_depth_raises(self) -> None:
        """Negative scallop depth raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{
                    "width": 48.0,
                    "scallop": {"depth": -1.0, "width": 6.0}
                }]
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_invalid_base_zone_type_raises(self) -> None:
        """Invalid base zone type raises validation error."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "base_zone": {"zone_type": "invalid"}
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)


# =============================================================================
# Face Frame Door Sizing Workflow Tests
# =============================================================================


class TestFaceFrameDoorSizingWorkflow:
    """Tests for face frame affecting door sizing workflow."""

    def test_face_frame_config_provides_opening_dimensions(self) -> None:
        """Face frame configuration provides opening dimensions for doors."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {
                    "stile_width": 1.5,
                    "rail_width": 2.0,
                    "joinery": "pocket_screw"
                },
                "sections": [
                    {"width": 48.0, "section_type": "doored"}
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        # Calculate expected opening dimensions
        stile_width = config.cabinet.face_frame.stile_width  # type: ignore
        rail_width = config.cabinet.face_frame.rail_width  # type: ignore

        # Opening width = cabinet width - (2 * stile width)
        expected_opening_width = 48.0 - (2 * stile_width)  # 48 - 3 = 45
        # Opening height = cabinet height - (2 * rail width)
        expected_opening_height = 84.0 - (2 * rail_width)  # 84 - 4 = 80

        assert expected_opening_width == pytest.approx(45.0)
        assert expected_opening_height == pytest.approx(80.0)

    def test_face_frame_with_multiple_sections(self) -> None:
        """Face frame config with multiple sections parses correctly."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {
                    "stile_width": 1.5,
                    "rail_width": 2.0
                },
                "sections": [
                    {"width": 24.0, "section_type": "doored"},
                    {"width": 24.0, "section_type": "drawers"},
                    {"width": "fill", "section_type": "open", "shelves": 3}
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        assert config.cabinet.face_frame is not None
        assert len(config.cabinet.sections) == 3


# =============================================================================
# Combined Decorative Features Tests
# =============================================================================


class TestCombinedDecorativeFeatures:
    """Tests for cabinets with multiple decorative features enabled."""

    def test_cabinet_with_all_decorative_features_parses(self) -> None:
        """Cabinet with all decorative features parses correctly."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 72.0,
                "height": 84.0,
                "depth": 12.0,
                "face_frame": {
                    "stile_width": 1.5,
                    "rail_width": 2.0,
                    "joinery": "pocket_screw",
                    "material_thickness": 0.75
                },
                "crown_molding": {
                    "height": 4.0,
                    "setback": 1.0,
                    "nailer_width": 2.0
                },
                "base_zone": {
                    "zone_type": "toe_kick",
                    "height": 4.0,
                    "setback": 3.0
                },
                "sections": [
                    {
                        "width": 24.0,
                        "arch_top": {
                            "arch_type": "full_round",
                            "radius": "auto"
                        }
                    },
                    {
                        "width": 24.0,
                        "shelves": 3,
                        "edge_profile": {
                            "profile_type": "roundover",
                            "size": 0.25,
                            "edges": ["front"]
                        }
                    },
                    {
                        "width": "fill",
                        "shelves": 5,
                        "scallop": {
                            "depth": 1.0,
                            "width": 4.0,
                            "count": "auto"
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        # Verify cabinet-level decorative elements
        assert config.cabinet.face_frame is not None
        assert config.cabinet.crown_molding is not None
        assert config.cabinet.base_zone is not None

        # Verify section-level decorative elements
        assert len(config.cabinet.sections) == 3
        assert config.cabinet.sections[0].arch_top is not None
        assert config.cabinet.sections[1].edge_profile is not None
        assert config.cabinet.sections[2].scallop is not None

    def test_section_with_arch_and_edge_profile(self) -> None:
        """Section can have both arch top and edge profile."""
        config_json = """
        {
            "schema_version": "1.3",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {
                        "width": 24.0,
                        "arch_top": {
                            "arch_type": "elliptical",
                            "radius": 8.0
                        },
                        "edge_profile": {
                            "profile_type": "ogee",
                            "size": 0.375
                        }
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        section = config.cabinet.sections[0]
        assert section.arch_top is not None
        assert section.arch_top.arch_type.value == "elliptical"
        assert section.edge_profile is not None
        assert section.edge_profile.profile_type.value == "ogee"


# =============================================================================
# Output Format Integration Tests
# =============================================================================


class TestOutputFormatIntegration:
    """Tests for output format integration with decorative metadata."""

    def test_cut_list_formatter_handles_mixed_pieces(self) -> None:
        """Cut list formatter handles mix of decorated and plain pieces."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            # Plain piece
            CutPiece(
                width=48.0,
                height=0.75,
                quantity=1,
                label="Top Panel",
                panel_type=PanelType.TOP,
                material=material,
            ),
            # Arch piece
            CutPiece(
                width=24.0,
                height=12.0,
                quantity=1,
                label="Arch Header",
                panel_type=PanelType.ARCH_HEADER,
                material=material,
                cut_metadata={
                    "arch_type": "segmental",
                    "radius": 18.0,
                    "spring_height": 4.0,
                },
            ),
            # Edge profile piece
            CutPiece(
                width=24.0,
                height=12.0,
                quantity=4,
                label="Shelf",
                panel_type=PanelType.SHELF,
                material=material,
                cut_metadata={
                    "edge_profile": {
                        "profile_type": "chamfer",
                        "size": 0.125,
                        "edges": ["front", "left", "right"],
                    },
                },
            ),
            # Joinery piece
            CutPiece(
                width=1.5,
                height=84.0,
                quantity=2,
                label="Stile",
                panel_type=PanelType.FACE_FRAME_STILE,
                material=material,
                cut_metadata={"joinery_type": "dowel"},
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        # All pieces should be present
        assert "Top Panel" in output
        assert "Arch Header" in output
        assert "Shelf" in output
        assert "Stile" in output

        # Notes column should be present
        assert "Notes" in output

        # Decorative metadata should be formatted
        assert "Arch:" in output
        assert "Profile:" in output
        assert "Joinery:" in output
