"""Integration tests for woodworking intelligence module.

These tests verify end-to-end workflows for woodworking intelligence features:
- Full cabinet generation with joinery specifications
- Span warnings integration with validation pipeline
- Cut list with grain direction annotations
- Hardware list aggregation across sections
- CLI with woodworking format output
- Configuration file with woodworking section (schema version 1.5)
"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cabinets.application.factory import get_factory
from cabinets.application.config import (
    config_to_woodworking,
    load_config,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain.entities import Cabinet, Section, Shelf
from cabinets.domain.services.woodworking import (
    WoodworkingConfig,
    WoodworkingIntelligence,
)
from cabinets.domain.value_objects import (
    GrainDirection,
    JointType,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from cabinets.infrastructure.exporters import (
    CutListFormatter,
    HardwareReportFormatter,
    JsonExporter,
)
from cabinets.cli.main import app


runner = CliRunner()


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================


class TestWoodworkingEndToEnd:
    """End-to-end tests for woodworking intelligence workflow."""

    def test_full_cabinet_with_joinery_specs(self):
        """Test full cabinet generation produces joinery specs."""
        # Create cabinet via command
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        assert output.is_valid
        assert output.cabinet is not None

        # Get woodworking specs
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(output.cabinet)

        # Should have joinery for all connections
        assert len(joinery) > 0

        # Check joinery types are appropriate
        joint_types = {j.joint.joint_type for j in joinery}
        assert JointType.DADO in joint_types  # For shelves
        assert JointType.RABBET in joint_types  # For back panel

    def test_full_cabinet_with_span_warnings(self):
        """Test cabinet with over-span shelf generates warnings."""
        # Create wide cabinet that exceeds safe span
        wall_input = WallInput(width=42.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,  # Single section = wide unsupported shelf span
            shelves_per_section=3,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        assert output.is_valid
        assert output.cabinet is not None

        # Get span warnings
        intel = WoodworkingIntelligence()
        warnings = intel.check_spans(output.cabinet)

        # 42" - 2*0.75" sides = 40.5" interior width > 36" limit for 3/4" plywood
        assert len(warnings) >= 1
        for warning in warnings:
            assert warning.span > warning.max_span
            assert warning.material.thickness == 0.75

    def test_full_cabinet_with_hardware_list(self):
        """Test cabinet generation produces complete hardware list."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=4,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        assert output.is_valid

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(output.cabinet)

        # Should have case screws and back panel screws
        assert hardware.total_count > 0

        # Verify both screw types present
        screw_names = [i.name for i in hardware.items]
        assert any("1-1/4" in name for name in screw_names)  # Case screws
        assert any("5/8" in name for name in screw_names)  # Back panel screws

    def test_full_cabinet_with_capacity_estimates(self):
        """Test cabinet generation produces capacity estimates."""
        wall_input = WallInput(width=36.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=4,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        assert output.is_valid

        intel = WoodworkingIntelligence()
        capacities = intel.get_shelf_capacities(output.cabinet)

        # Should have capacity for each shelf
        assert len(capacities) == 4
        for cap in capacities:
            assert cap.capacity_lbs > 0
            assert "Advisory" in cap.disclaimer


# =============================================================================
# Cut List Integration Tests
# =============================================================================


class TestCutListIntegration:
    """Tests for cut list with grain direction integration."""

    def test_cut_list_with_grain_directions(self):
        """Test cut list includes grain direction in output."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        assert output.is_valid

        # Annotate cut list with grain directions
        intel = WoodworkingIntelligence()
        annotated = intel.annotate_cut_list(output.cut_list)

        # Check grain direction is in metadata
        pieces_with_grain = [
            p
            for p in annotated
            if p.cut_metadata and "grain_direction" in p.cut_metadata
        ]
        assert len(pieces_with_grain) > 0

    def test_cut_list_formatter_shows_grain(self):
        """Test CutListFormatter displays grain direction."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=2,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        annotated = intel.annotate_cut_list(output.cut_list)

        formatter = CutListFormatter()
        formatted = formatter.format(annotated)

        # Should show grain direction in notes
        assert "Grain:" in formatted or "grain" in formatted.lower()

    def test_json_exporter_includes_grain(self):
        """Test JsonExporter includes grain direction in output."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=2,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        annotated = intel.annotate_cut_list(output.cut_list)

        # Create a new output with annotated cut list
        from cabinets.application.dtos import LayoutOutput

        output_with_grain = LayoutOutput(
            cabinet=output.cabinet,
            cut_list=annotated,
            material_estimates=output.material_estimates,
            total_estimate=output.total_estimate,
            hardware=output.hardware,
            errors=output.errors,
        )

        exporter = JsonExporter()
        json_output = exporter.export(output_with_grain)
        data = json.loads(json_output)

        # Check for grain direction in cut list
        pieces_with_decorative = [
            p for p in data["cut_list"] if "decorative_metadata" in p
        ]
        assert len(pieces_with_decorative) > 0


# =============================================================================
# Hardware Report Integration Tests
# =============================================================================


class TestHardwareReportIntegration:
    """Tests for hardware report formatting integration."""

    def test_hardware_report_formatting(self):
        """Test hardware report is properly formatted."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(output.cabinet)

        formatter = HardwareReportFormatter()
        report = formatter.format(hardware, show_overage=True)

        # Check report structure
        assert "HARDWARE LIST" in report
        assert "screw" in report.lower()
        assert "TOTAL" in report

    def test_hardware_shopping_list_format(self):
        """Test hardware shopping list format."""
        wall_input = WallInput(width=36.0, height=72.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=2,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(output.cabinet)

        formatter = HardwareReportFormatter()
        shopping = formatter.format_shopping_list(hardware)

        assert "Shopping List" in shopping
        assert "[ ]" in shopping  # Checkbox format


# =============================================================================
# Configuration Integration Tests
# =============================================================================


class TestConfigurationIntegration:
    """Tests for configuration file integration."""

    def test_load_config_with_woodworking_section(self):
        """Test loading config with woodworking section."""
        config_content = {
            "schema_version": "1.5",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [{"width": "fill", "shelves": 4}],
            },
            "woodworking": {
                "joinery": {
                    "default_shelf_joint": "dado",
                    "dado_depth_ratio": 0.333,
                },
                "hardware": {"add_overage": True, "overage_percent": 10},
                "warnings_enabled": True,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_content, f)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)

            assert config.woodworking is not None
            assert config.woodworking.warnings_enabled is True
            assert config.woodworking.joinery.dado_depth_ratio == pytest.approx(0.333)
            assert config.woodworking.hardware.overage_percent == 10

        finally:
            config_path.unlink()

    def test_config_to_woodworking_adapter(self):
        """Test config adapter converts to domain objects."""
        config_content = {
            "schema_version": "1.5",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [],
            },
            "woodworking": {"joinery": {"dado_depth_ratio": 0.4, "dowel_spacing": 5.0}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_content, f)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)
            woodworking_config = config_to_woodworking(config)

            assert woodworking_config is not None
            assert woodworking_config.dado_depth_ratio == pytest.approx(0.4)
            assert woodworking_config.dowel_spacing == 5.0

        finally:
            config_path.unlink()

    def test_config_without_woodworking_uses_defaults(self):
        """Test config without woodworking section uses defaults."""
        config_content = {
            "schema_version": "1.0",
            "cabinet": {"width": 48.0, "height": 84.0, "depth": 12.0},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_content, f)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_config(config_path)
            woodworking_config = config_to_woodworking(config)

            # Should return None (no woodworking config)
            assert woodworking_config is None

            # Service should use defaults
            intel = WoodworkingIntelligence()
            assert intel.config.dado_depth_ratio == pytest.approx(1 / 3)

        finally:
            config_path.unlink()


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Tests for CLI with woodworking format."""

    def test_cli_woodworking_format_basic(self):
        """Test CLI with --format woodworking option."""
        result = runner.invoke(
            app,
            [
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--format",
                "woodworking",
            ],
        )

        assert result.exit_code == 0
        output = result.stdout

        # Should contain woodworking sections
        assert "WOODWORKING" in output or "JOINERY" in output
        assert "HARDWARE" in output or "screw" in output.lower()

    def test_cli_woodworking_with_config_file(self):
        """Test CLI with config file containing woodworking."""
        config_content = {
            "schema_version": "1.5",
            "cabinet": {
                "width": 36.0,
                "height": 72.0,
                "depth": 12.0,
                "sections": [{"width": "fill", "shelves": 3}],
            },
            "woodworking": {"warnings_enabled": True},
            "output": {"format": "woodworking"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_content, f)
            f.flush()
            config_path = f.name

        try:
            result = runner.invoke(
                app,
                ["generate", "--config", config_path],
            )

            assert result.exit_code == 0
            # Woodworking output should be included

        finally:
            Path(config_path).unlink()

    def test_cli_validate_with_span_warnings(self):
        """Test validate command shows span warnings."""
        config_content = {
            "schema_version": "1.5",
            "cabinet": {
                "width": 42.0,  # Over span for single section
                "height": 84.0,
                "depth": 12.0,
                "sections": [{"width": "fill", "shelves": 4}],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_content, f)
            f.flush()
            config_path = f.name

        try:
            result = runner.invoke(
                app,
                ["validate", config_path],
            )

            # Should complete (exit code 0 or 2 for warnings)
            assert result.exit_code in (0, 2)

            # If there are warnings, they should mention span
            if result.exit_code == 2:
                assert "span" in result.stdout.lower()

        finally:
            Path(config_path).unlink()


# =============================================================================
# Multi-Section Integration Tests
# =============================================================================


class TestMultiSectionIntegration:
    """Tests for cabinets with multiple sections."""

    def test_hardware_aggregation_across_sections(self):
        """Test hardware is aggregated across multiple sections."""
        wall_input = WallInput(width=72.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=4,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        assert output.is_valid

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(output.cabinet)

        # Multiple sections should mean more hardware
        # (More dividers, more shelf connections)
        assert hardware.total_count > 50  # Reasonable minimum for 3-section cabinet

    def test_joinery_includes_divider_connections(self):
        """Test joinery includes divider-to-top/bottom connections."""
        wall_input = WallInput(width=72.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=2,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(output.cabinet)

        # Should have divider connections
        divider_connections = [j for j in joinery if j.to_panel == PanelType.DIVIDER]
        assert len(divider_connections) > 0

    def test_span_warnings_per_section(self):
        """Test span warnings are generated per section."""
        # Create cabinet with one narrow and one wide section
        cabinet = Cabinet(
            width=72.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )

        # Narrow section (safe) - 30" width is under 36" limit
        section1 = Section(
            width=30.0, height=82.5, depth=11.25, position=Position(0.75, 0.75)
        )
        shelf1 = Shelf(
            width=30.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20),
        )
        section1.add_shelf(shelf1)
        cabinet.sections.append(section1)

        # Wide section (over span) - 40" width exceeds 36" limit
        section2 = Section(
            width=40.0, height=82.5, depth=11.25, position=Position(31.5, 0.75)
        )
        shelf2 = Shelf(
            width=40.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(31.5, 20),
        )
        section2.add_shelf(shelf2)
        cabinet.sections.append(section2)

        intel = WoodworkingIntelligence()
        warnings = intel.check_spans(cabinet)

        # check_spans also checks top/bottom panels, so we get:
        # - Section 2 Shelf 1 (40" > 36")
        # - Top Panel (max section width 40" > 36")
        # - Bottom Panel (max section width 40" > 36")
        assert len(warnings) >= 1

        # Verify shelf warning is present for section 2
        shelf_warnings = [w for w in warnings if "Section 2" in w.panel_label]
        assert len(shelf_warnings) == 1
        assert shelf_warnings[0].span == 40.0
        assert shelf_warnings[0].max_span == 36.0

        # Verify no warning for section 1 shelf (30" < 36")
        section1_warnings = [w for w in warnings if "Section 1" in w.panel_label]
        assert len(section1_warnings) == 0


# =============================================================================
# Material Variation Tests
# =============================================================================


class TestMaterialVariationIntegration:
    """Tests for different material types."""

    def test_mdf_cabinet_with_stricter_limits(self):
        """Test MDF cabinet has stricter span limits."""
        mdf_material = MaterialSpec(thickness=0.75, material_type=MaterialType.MDF)

        cabinet = Cabinet(
            width=30.0,  # Would be safe for plywood, over for MDF
            height=84.0,
            depth=12.0,
            material=mdf_material,
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=28.5, height=82.5, depth=11.25, position=Position(0.75, 0.75)
        )
        shelf = Shelf(
            width=28.5, depth=11.25, material=mdf_material, position=Position(0.75, 20)
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        intel = WoodworkingIntelligence()
        warnings = intel.check_spans(cabinet)

        # 28.5" exceeds 24" MDF limit
        assert len(warnings) >= 1
        assert warnings[0].max_span == 24.0

    def test_solid_wood_cabinet_capacity(self):
        """Test solid wood cabinet has higher capacity."""
        intel = WoodworkingIntelligence()

        cap_plywood = intel.estimate_capacity(
            thickness=0.75,
            depth=12.0,
            span=24.0,
            material_type=MaterialType.PLYWOOD,
        )
        cap_solid = intel.estimate_capacity(
            thickness=1.0,
            depth=12.0,
            span=24.0,
            material_type=MaterialType.SOLID_WOOD,
        )

        # Solid wood should have higher capacity (thicker + higher modulus)
        assert cap_solid.capacity_lbs > cap_plywood.capacity_lbs


# =============================================================================
# Joinery Specification Tests
# =============================================================================


class TestJoinerySpecificationIntegration:
    """Tests for detailed joinery specifications."""

    def test_dado_depth_calculation(self):
        """Test dado depth is calculated correctly from material thickness."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(output.cabinet)

        # Find a dado joint (shelf-to-side)
        dado_joints = [j for j in joinery if j.joint.joint_type == JointType.DADO]
        assert len(dado_joints) > 0

        # Dado depth should be 1/3 of material thickness (0.75 * 0.333 = 0.25)
        for joint in dado_joints:
            assert joint.joint.depth is not None
            assert joint.joint.depth == pytest.approx(0.25, rel=0.01)

    def test_rabbet_dimensions_for_back_panel(self):
        """Test rabbet dimensions are calculated for back panel."""
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=2,
            material_thickness=0.75,
            back_thickness=0.25,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(output.cabinet)

        # Find rabbet joints (back panel connections)
        rabbet_joints = [j for j in joinery if j.joint.joint_type == JointType.RABBET]
        assert len(rabbet_joints) > 0

        # Rabbet width should equal back panel thickness
        for joint in rabbet_joints:
            assert joint.joint.width is not None
            assert joint.joint.width == pytest.approx(0.25, rel=0.01)


# =============================================================================
# Grain Direction Tests
# =============================================================================


class TestGrainDirectionIntegration:
    """Tests for grain direction recommendations."""

    def test_grain_direction_for_visible_panels(self):
        """Test visible panels get appropriate grain direction."""
        wall_input = WallInput(width=36.0, height=72.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=2,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        intel = WoodworkingIntelligence()
        directions = intel.get_grain_directions(output.cut_list)

        # All visible panels should have grain direction
        for label, grain in directions.items():
            # Side panels, top, bottom should have grain recommendations
            if any(x in label.lower() for x in ["side", "top", "bottom", "shelf"]):
                assert grain in (GrainDirection.LENGTH, GrainDirection.WIDTH)

    def test_mdf_panels_have_no_grain(self):
        """Test MDF panels have NONE grain direction."""
        intel = WoodworkingIntelligence()

        # Create a mock MDF cut piece
        from cabinets.domain.value_objects import CutPiece

        mdf_piece = CutPiece(
            width=24.0,
            height=12.0,
            quantity=1,
            label="MDF Shelf",
            panel_type=PanelType.SHELF,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.MDF),
        )

        directions = intel.get_grain_directions([mdf_piece])

        assert directions["MDF Shelf"] == GrainDirection.NONE


# =============================================================================
# Custom Configuration Tests
# =============================================================================


class TestCustomWoodworkingConfig:
    """Tests for custom woodworking configuration."""

    def test_custom_dado_depth_ratio(self):
        """Test custom dado depth ratio is applied."""
        config = WoodworkingConfig(dado_depth_ratio=0.5)  # 50% instead of default 33%
        intel = WoodworkingIntelligence(config=config)

        wall_input = WallInput(width=36.0, height=72.0, depth=12.0)
        params = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=2,
            material_thickness=0.75,
        )

        command = get_factory().create_generate_command()
        output = command.execute(wall_input, params)

        joinery = intel.get_joinery(output.cabinet)
        dado_joints = [j for j in joinery if j.joint.joint_type == JointType.DADO]

        # Dado depth should be 50% of material thickness (0.75 * 0.5 = 0.375)
        for joint in dado_joints:
            assert joint.joint.depth == pytest.approx(0.375, rel=0.01)

    def test_custom_dowel_spacing(self):
        """Test custom dowel spacing is applied."""
        config = WoodworkingConfig(dowel_spacing=4.0)  # 4" instead of default 6"
        intel = WoodworkingIntelligence(config=config)

        # Test dowel spec generation
        spec = intel.get_dowel_spec(length=24.0)

        # With 4" spacing on 24" joint, expect more positions than default
        # Edge offset is 2", so positions at 2", 6", 10", 14", 18", 22"
        assert len(spec.positions) >= 4
        assert spec.spacing == 4.0


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestWoodworkingErrorHandling:
    """Tests for error handling in woodworking workflows."""

    def test_empty_cabinet_no_crash(self):
        """Test that empty cabinet doesn't crash woodworking analysis."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )
        # No sections added

        intel = WoodworkingIntelligence()

        # Should not crash
        joinery = intel.get_joinery(cabinet)
        warnings = intel.check_spans(cabinet)
        hardware = intel.calculate_hardware(cabinet)
        capacities = intel.get_shelf_capacities(cabinet)

        # Should return empty or minimal results
        assert isinstance(joinery, list)
        assert isinstance(warnings, list)
        assert isinstance(hardware.items, tuple)
        assert isinstance(capacities, list)

    def test_invalid_config_values_handled(self):
        """Test that invalid config values are rejected properly."""
        with pytest.raises(ValueError):
            WoodworkingConfig(dado_depth_ratio=1.5)  # > 1 is invalid

        with pytest.raises(ValueError):
            WoodworkingConfig(dowel_spacing=-1)  # Negative is invalid
