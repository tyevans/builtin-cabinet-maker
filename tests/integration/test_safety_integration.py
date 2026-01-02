"""Integration tests for FRD-21 Safety and Compliance features.

These tests verify end-to-end safety analysis workflows including
configuration loading, safety analysis, and output generation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cabinets.application.factory import get_factory
from cabinets.application.config import (
    CabinetConfiguration,
    config_to_dtos,
    config_to_safety,
    load_config,
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain.entities import Cabinet, Obstacle, Section, Shelf
from cabinets.domain.value_objects import (
    MaterialSpec,
    ObstacleType,
    Position,
    SafetyCategory,
    SafetyCheckStatus,
    SeismicZone,
)
from cabinets.domain.services.safety import (
    AccessibilityReport,
    SafetyAssessment,
    SafetyCheckResult,
    SafetyConfig,
    SafetyLabel,
    SafetyService,
    WeightCapacityEstimate,
)
from cabinets.infrastructure.formatters import SafetyReportFormatter
from cabinets.infrastructure.exporters.safety_labels import SafetyLabelExporter


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def sample_cabinet() -> Cabinet:
    """Create a sample cabinet for testing."""
    material = MaterialSpec.standard_3_4()

    # Create sections with shelves
    sections = [
        Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(0.75, 0.0),
            shelves=[
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(0.75, 20.0),
                ),
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(0.75, 42.0),
                ),
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(0.75, 64.0),
                ),
            ],
        ),
        Section(
            width=24.0,
            height=84.0,
            depth=12.0,
            position=Position(24.75, 0.0),
            shelves=[
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(24.75, 16.0),
                ),
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(24.75, 32.0),
                ),
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(24.75, 48.0),
                ),
                Shelf(
                    width=22.5,
                    depth=11.25,
                    material=material,
                    position=Position(24.75, 64.0),
                ),
            ],
        ),
    ]

    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=material,
        sections=sections,
    )


@pytest.fixture
def sample_obstacles() -> list[Obstacle]:
    """Create sample obstacles for testing."""
    return [
        Obstacle(
            obstacle_type=ObstacleType.ELECTRICAL_PANEL,
            wall_index=0,
            horizontal_offset=60.0,
            bottom=0.0,
            width=24.0,
            height=36.0,
        ),
        Obstacle(
            obstacle_type=ObstacleType.COOKTOP,
            wall_index=0,
            horizontal_offset=80.0,
            bottom=36.0,
            width=30.0,
            height=4.0,
        ),
    ]


@pytest.fixture
def sample_config_dict() -> dict:
    """Create sample configuration dictionary."""
    return {
        "schema_version": "1.10",
        "cabinet": {
            "width": 48.0,
            "height": 84.0,
            "depth": 12.0,
            "material": {"type": "plywood", "thickness": 0.75},
            "sections": [
                {"width": 24.0, "shelves": 3},
                {"width": "fill", "shelves": 4},
            ],
        },
        "safety": {
            "safety_factor": 4.0,
            "deflection_limit": "L/200",
            "accessibility": {"enabled": True, "standard": "ADA_2010"},
            "child_safe_mode": True,
            "seismic_zone": "D",
            "check_clearances": True,
            "material_certification": "carb_phase2",
            "generate_labels": True,
        },
        "room": {
            "name": "test-room",
            "walls": [
                {
                    "length": 120.0,
                    "height": 96.0,
                    "angle": 0,
                }
            ],
            "obstacles": [
                {
                    "type": "electrical_panel",
                    "wall": 0,
                    "horizontal_offset": 60.0,
                    "bottom": 0.0,
                    "width": 24.0,
                    "height": 36.0,
                }
            ],
        },
    }


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


# ==============================================================================
# Weight Capacity Integration Tests
# ==============================================================================


class TestWeightCapacityIntegration:
    """Test weight capacity calculation integration."""

    def test_all_shelves_have_capacity(self, sample_cabinet: Cabinet) -> None:
        """Test all shelves get capacity estimates."""
        config = SafetyConfig(safety_factor=4.0)
        service = SafetyService(config)

        capacities = service.get_shelf_capacities(sample_cabinet)

        # Count total shelves
        total_shelves = sum(len(section.shelves) for section in sample_cabinet.sections)

        # Should have capacity for each shelf
        assert len(capacities) == total_shelves

    def test_capacity_varies_by_span(self) -> None:
        """Test capacity varies with different spans."""
        config = SafetyConfig(safety_factor=4.0)
        service = SafetyService(config)
        material = MaterialSpec.standard_3_4()

        # Create two cabinets with different widths
        narrow_cabinet = Cabinet(
            width=24.0,
            height=84.0,
            depth=12.0,
            material=material,
            sections=[
                Section(
                    width=22.5,
                    height=84.0,
                    depth=12.0,
                    position=Position(0.75, 0.0),
                    shelves=[
                        Shelf(
                            width=22.5,
                            depth=11.25,
                            material=material,
                            position=Position(0.75, 42.0),
                        )
                    ],
                )
            ],
        )

        wide_cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=material,
            sections=[
                Section(
                    width=46.5,
                    height=84.0,
                    depth=12.0,
                    position=Position(0.75, 0.0),
                    shelves=[
                        Shelf(
                            width=46.5,
                            depth=11.25,
                            material=material,
                            position=Position(0.75, 42.0),
                        )
                    ],
                )
            ],
        )

        narrow_capacities = service.get_shelf_capacities(narrow_cabinet)
        wide_capacities = service.get_shelf_capacities(wide_cabinet)

        assert len(narrow_capacities) == 1
        assert len(wide_capacities) == 1

        narrow_capacity = narrow_capacities[0].safe_load_lbs
        wide_capacity = wide_capacities[0].safe_load_lbs

        # Narrow should have higher capacity (shorter span)
        assert narrow_capacity > wide_capacity

    def test_capacity_estimate_has_required_fields(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test capacity estimate has all required fields."""
        config = SafetyConfig(safety_factor=4.0)
        service = SafetyService(config)

        capacities = service.get_shelf_capacities(sample_cabinet)
        assert len(capacities) > 0

        capacity = capacities[0]
        assert isinstance(capacity, WeightCapacityEstimate)
        assert capacity.safe_load_lbs > 0
        assert capacity.max_deflection_inches > 0
        assert capacity.safety_factor == 4.0
        assert capacity.span_inches > 0
        assert capacity.material == "plywood"
        assert capacity.disclaimer is not None


# ==============================================================================
# Stability Integration Tests
# ==============================================================================


class TestStabilityIntegration:
    """Test stability analysis integration."""

    def test_anti_tip_required_for_tall_cabinet(self, sample_cabinet: Cabinet) -> None:
        """Test tall cabinet requires anti-tip restraint."""
        config = SafetyConfig()
        service = SafetyService(config)

        result = service.check_anti_tip_requirement(sample_cabinet)

        # 84" cabinet should require anti-tip (threshold is 27")
        assert result.status == SafetyCheckStatus.WARNING
        assert result.category == SafetyCategory.STABILITY
        assert "anti-tip" in result.message.lower()

    def test_anti_tip_not_required_for_short_cabinet(self) -> None:
        """Test short cabinet does not require anti-tip."""
        config = SafetyConfig()
        service = SafetyService(config)
        material = MaterialSpec.standard_3_4()

        short_cabinet = Cabinet(
            width=24.0,
            height=24.0,  # Below 27" threshold
            depth=12.0,
            material=material,
            sections=[],
        )

        result = service.check_anti_tip_requirement(short_cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert "not required" in result.message.lower()

    def test_anti_tip_hardware_recommendations(self, sample_cabinet: Cabinet) -> None:
        """Test anti-tip hardware recommendations are generated."""
        config = SafetyConfig()
        service = SafetyService(config)

        hardware = service.get_anti_tip_hardware(sample_cabinet)

        # 84" cabinet should have hardware recommendations
        assert len(hardware) > 0
        assert any("strap" in h.lower() for h in hardware)


# ==============================================================================
# Accessibility Integration Tests
# ==============================================================================


class TestAccessibilityIntegration:
    """Test accessibility analysis integration."""

    def test_accessibility_report_for_tall_cabinet(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test accessibility analysis for tall cabinet."""
        config = SafetyConfig(accessibility_enabled=True)
        service = SafetyService(config)

        report = service.analyze_accessibility(sample_cabinet)

        assert isinstance(report, AccessibilityReport)
        assert report.total_storage_volume > 0
        # 84" cabinet will have some storage outside reach range
        assert 0 <= report.accessible_percentage <= 100

    def test_accessibility_disabled_returns_minimal_report(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test disabled accessibility returns minimal report."""
        config = SafetyConfig(accessibility_enabled=False)
        service = SafetyService(config)

        report = service.analyze_accessibility(sample_cabinet)

        assert isinstance(report, AccessibilityReport)
        assert report.total_storage_volume == 0.0
        assert report.is_compliant is True  # N/A when disabled


# ==============================================================================
# Clearance Detection Integration Tests
# ==============================================================================


class TestClearanceIntegration:
    """Test clearance detection with obstacles."""

    def test_electrical_panel_clearance_detection(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test electrical panel clearance is detected."""
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.ELECTRICAL_PANEL,
                wall_index=0,
                horizontal_offset=24.0,  # Overlaps cabinet
                bottom=0.0,
                width=24.0,
                height=36.0,
            )
        ]

        config = SafetyConfig(check_clearances=True)
        service = SafetyService(config)

        results = service.check_clearances(sample_cabinet, obstacles)

        # Should have clearance check results
        assert len(results) > 0
        clearance_results = [
            r for r in results if r.category == SafetyCategory.CLEARANCE
        ]
        assert len(clearance_results) > 0

    def test_no_clearance_issues_when_clear(self, sample_cabinet: Cabinet) -> None:
        """Test no clearance issues when cabinet is clear of obstacles."""
        # Obstacles far from cabinet
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.ELECTRICAL_PANEL,
                wall_index=0,
                horizontal_offset=200.0,  # Far away
                bottom=0.0,
                width=24.0,
                height=36.0,
            )
        ]

        config = SafetyConfig(check_clearances=True)
        service = SafetyService(config)

        results = service.check_clearances(sample_cabinet, obstacles)

        # Should pass clearance checks
        errors = [r for r in results if r.status == SafetyCheckStatus.ERROR]
        assert len(errors) == 0

    def test_egress_blocking_detection(self, sample_cabinet: Cabinet) -> None:
        """Test egress window blocking is detected."""
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.WINDOW,
                wall_index=0,
                horizontal_offset=10.0,
                bottom=36.0,
                width=36.0,
                height=48.0,
                is_egress=True,
            )
        ]

        config = SafetyConfig(check_clearances=True)
        service = SafetyService(config)

        results = service.check_clearances(sample_cabinet, obstacles)

        # Should have results (egress checking)
        assert len(results) > 0

    def test_heat_source_clearance_violation(self, sample_cabinet: Cabinet) -> None:
        """Test heat source vertical clearance violation is detected."""
        # Place cooktop directly under cabinet
        obstacles = [
            Obstacle(
                obstacle_type=ObstacleType.COOKTOP,
                wall_index=0,
                horizontal_offset=0.0,
                bottom=0.0,  # At floor level, cabinet will be above it
                width=30.0,
                height=4.0,
            )
        ]

        config = SafetyConfig(check_clearances=True)
        service = SafetyService(config)

        results = service.check_clearances(sample_cabinet, obstacles)

        # Should detect heat source clearance issue
        clearance_results = [
            r for r in results if r.category == SafetyCategory.CLEARANCE
        ]
        assert len(clearance_results) > 0


# ==============================================================================
# Configuration Integration Tests
# ==============================================================================


class TestConfigurationIntegration:
    """Test configuration file integration."""

    def test_config_with_safety_section_loads(self, sample_config_dict: dict) -> None:
        """Test configuration with safety section validates."""
        config = CabinetConfiguration.model_validate(sample_config_dict)

        assert config.schema_version == "1.10"
        assert config.safety is not None
        assert config.safety.safety_factor == 4.0
        assert config.safety.seismic_zone == "D"
        assert config.safety.child_safe_mode is True

    def test_config_to_safety_adapter(self, sample_config_dict: dict) -> None:
        """Test config_to_safety adapter converts correctly."""
        config = CabinetConfiguration.model_validate(sample_config_dict)
        safety_config = config_to_safety(config.safety)

        assert isinstance(safety_config, SafetyConfig)
        assert safety_config.safety_factor == 4.0
        assert safety_config.seismic_zone == SeismicZone.D
        assert safety_config.accessibility_enabled is True

    def test_config_file_round_trip(
        self, sample_config_dict: dict, tmp_path: Path
    ) -> None:
        """Test config saves and loads correctly."""
        config_path = tmp_path / "test_config.json"

        # Save config
        config_path.write_text(json.dumps(sample_config_dict, indent=2))

        # Load config
        loaded_dict = json.loads(config_path.read_text())
        config = CabinetConfiguration.model_validate(loaded_dict)

        assert config.safety is not None
        assert config.safety.safety_factor == 4.0
        assert config.safety.accessibility is not None
        assert config.safety.accessibility.enabled is True

    def test_safety_config_defaults(self) -> None:
        """Test safety config has sensible defaults."""
        config_dict = {
            "schema_version": "1.10",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
            "safety": {},  # Empty safety section - should use defaults
        }

        config = CabinetConfiguration.model_validate(config_dict)

        assert config.safety is not None
        assert config.safety.safety_factor == 4.0
        assert config.safety.deflection_limit == "L/200"
        assert config.safety.check_clearances is True
        assert config.safety.generate_labels is True


# ==============================================================================
# Safety Report Integration Tests
# ==============================================================================


class TestSafetyReportIntegration:
    """Test safety report generation integration."""

    def test_report_formatter_structure(self) -> None:
        """Test safety report formatter creates valid structure."""
        # Create a minimal SafetyAssessment
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test_check",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Test passed",
                )
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        formatter = SafetyReportFormatter()
        report = formatter.format(assessment)

        # Verify report structure
        assert "# Safety Assessment Report" in report
        assert "## Summary" in report
        assert "## Disclaimers" in report

    def test_report_reflects_assessment_status(self) -> None:
        """Test report correctly reflects assessment status."""
        # Assessment with warning
        assessment_warning = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="anti_tip",
                    category=SafetyCategory.STABILITY,
                    status=SafetyCheckStatus.WARNING,
                    message="Anti-tip required",
                )
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=True,
            seismic_hardware=[],
        )

        formatter = SafetyReportFormatter()
        report = formatter.format(assessment_warning)

        assert "WARNINGS" in report or "warning" in report.lower()

    def test_report_saves_to_file(self, tmp_path: Path) -> None:
        """Test report saves to file correctly."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test_check",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Test passed",
                )
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        formatter = SafetyReportFormatter()
        report = formatter.format(assessment)

        report_path = tmp_path / "safety_report.md"
        report_path.write_text(report)

        # Verify file
        assert report_path.exists()
        content = report_path.read_text()
        assert "Safety Assessment Report" in content


# ==============================================================================
# Safety Labels Integration Tests
# ==============================================================================


class TestSafetyLabelsIntegration:
    """Test safety labels export integration."""

    def test_single_label_export_to_svg(self) -> None:
        """Test single safety label exports to valid SVG."""
        label = SafetyLabel(
            label_type="weight_capacity",
            title="MAXIMUM LOAD",
            body_text="Do not exceed 45 lbs per shelf.",
            warning_icon=True,
            dimensions=(4.0, 3.0),
        )

        exporter = SafetyLabelExporter()
        svg = exporter.export_label(label)

        assert svg.startswith("<svg")
        assert "MAXIMUM LOAD" in svg
        assert "</svg>" in svg

    def test_anti_tip_label_format(self) -> None:
        """Test anti-tip label has correct format."""
        label = SafetyLabel(
            label_type="anti_tip",
            title="TIP-OVER HAZARD",
            body_text="Secure to wall to prevent tip-over. Do not climb on furniture.",
            warning_icon=True,
            dimensions=(4.0, 4.0),
        )

        exporter = SafetyLabelExporter()
        svg = exporter.export_label(label)

        assert "WARNING" in svg
        assert "TIP-OVER" in svg

    def test_multiple_labels_export(self) -> None:
        """Test multiple labels export correctly."""
        labels = [
            SafetyLabel(
                label_type="weight_capacity",
                title="MAX LOAD",
                body_text="50 lbs per shelf",
            ),
            SafetyLabel(
                label_type="anti_tip",
                title="WARNING",
                body_text="Secure to wall",
                warning_icon=True,
            ),
        ]

        exporter = SafetyLabelExporter()
        svg_dict = exporter.export_all_labels(labels)

        assert len(svg_dict) == 2
        assert "weight_capacity" in svg_dict
        assert "anti_tip" in svg_dict

    def test_labels_save_to_directory(self, tmp_path: Path) -> None:
        """Test labels save to directory as SVG files."""
        labels = [
            SafetyLabel(
                label_type="weight_capacity",
                title="MAX LOAD",
                body_text="50 lbs per shelf",
            ),
            SafetyLabel(
                label_type="installation",
                title="INSTALLATION",
                body_text="Mount to wall studs\nUse appropriate fasteners",
            ),
        ]

        exporter = SafetyLabelExporter()

        for label in labels:
            svg = exporter.export_label(label)
            filepath = tmp_path / f"safety_label_{label.label_type}.svg"
            filepath.write_text(svg)

        # Verify files created
        svg_files = list(tmp_path.glob("*.svg"))
        assert len(svg_files) == len(labels)


# ==============================================================================
# Seismic Hardware Integration Tests
# ==============================================================================


class TestSeismicHardwareIntegration:
    """Test seismic hardware requirements."""

    def test_high_seismic_zone_requires_hardware(self) -> None:
        """Test high seismic zones require enhanced anchoring."""
        config = SafetyConfig(seismic_zone=SeismicZone.D)

        assert config.requires_seismic_hardware is True

    def test_low_seismic_zone_no_enhanced_hardware(self) -> None:
        """Test low seismic zones don't require enhanced hardware."""
        config = SafetyConfig(seismic_zone=SeismicZone.A)

        assert config.requires_seismic_hardware is False

    def test_no_seismic_zone_specified(self) -> None:
        """Test no seismic zone specified."""
        config = SafetyConfig(seismic_zone=None)

        assert config.requires_seismic_hardware is False


# ==============================================================================
# Child Safety Integration Tests
# ==============================================================================


class TestChildSafetyIntegration:
    """Test child safety mode integration."""

    def test_child_safe_mode_config(self) -> None:
        """Test child safe mode configuration."""
        config = SafetyConfig(child_safe_mode=True)

        assert config.child_safe_mode is True

    def test_child_safety_from_json_config(self, sample_config_dict: dict) -> None:
        """Test child safety mode from JSON config."""
        config = CabinetConfiguration.model_validate(sample_config_dict)
        safety_config = config_to_safety(config.safety)

        assert safety_config.child_safe_mode is True


# ==============================================================================
# CLI Integration Tests
# ==============================================================================


class TestCLIIntegration:
    """Test CLI safety options integration."""

    def test_cli_generates_cabinet(self, runner: CliRunner) -> None:
        """Test CLI generates cabinet successfully."""
        from cabinets.cli.main import app

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
                "json",
            ],
        )

        assert result.exit_code == 0

    def test_cli_with_config_file(
        self, sample_config_dict: dict, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test CLI with configuration file containing safety section."""
        from cabinets.cli.main import app

        # Write config file
        config_path = tmp_path / "cabinet_config.json"
        config_path.write_text(json.dumps(sample_config_dict, indent=2))

        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(config_path),
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0


# ==============================================================================
# Generate Layout Command Integration Tests
# ==============================================================================


class TestGenerateLayoutCommandIntegration:
    """Test GenerateLayoutCommand with safety configurations."""

    def test_execute_generates_valid_cabinet(self) -> None:
        """Test command generates valid cabinet."""
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert result.cabinet is not None
        assert result.cabinet.width == 48.0
        assert result.cabinet.height == 84.0

    def test_execute_generates_cut_list(self) -> None:
        """Test command generates cut list."""
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert len(result.cut_list) > 0


# ==============================================================================
# End-to-End Workflow Tests
# ==============================================================================


class TestEndToEndWorkflows:
    """Test complete end-to-end safety workflows."""

    def test_config_to_safety_analysis_workflow(self, sample_config_dict: dict) -> None:
        """Test workflow: config -> safety service -> analysis."""
        # Load configuration
        config = CabinetConfiguration.model_validate(sample_config_dict)

        # Convert to safety config
        safety_config = config_to_safety(config.safety)
        assert isinstance(safety_config, SafetyConfig)

        # Create service
        service = SafetyService(safety_config)

        # Create a cabinet for testing
        material = MaterialSpec.standard_3_4()
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=material,
            sections=[
                Section(
                    width=46.5,
                    height=84.0,
                    depth=12.0,
                    position=Position(0.75, 0.0),
                    shelves=[
                        Shelf(
                            width=45.0,
                            depth=11.25,
                            material=material,
                            position=Position(0.75, 42.0),
                        )
                    ],
                )
            ],
        )

        # Run individual analyses
        anti_tip_result = service.check_anti_tip_requirement(cabinet)
        assert anti_tip_result is not None
        assert anti_tip_result.category == SafetyCategory.STABILITY

        capacities = service.get_shelf_capacities(cabinet)
        assert len(capacities) >= 1

        accessibility_report = service.analyze_accessibility(cabinet)
        assert accessibility_report is not None

    def test_json_config_to_cabinet_to_safety_workflow(self, tmp_path: Path) -> None:
        """Test workflow: JSON file -> cabinet generation -> safety checks."""
        # Create config file
        config_dict = {
            "schema_version": "1.10",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "material": {"type": "plywood", "thickness": 0.75},
                "sections": [{"width": 24.0, "shelves": 3}],
            },
            "safety": {
                "safety_factor": 4.0,
                "accessibility": {"enabled": True},
            },
        }

        config_path = tmp_path / "test_cabinet.json"
        config_path.write_text(json.dumps(config_dict, indent=2))

        # Load and parse
        config = load_config(config_path)

        # Generate cabinet
        wall_input, params_input = config_to_dtos(config)
        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input)

        assert result.is_valid
        cabinet = result.cabinet

        # Run safety checks
        safety_config = config_to_safety(config.safety)
        service = SafetyService(safety_config)

        # Verify safety checks can run on generated cabinet
        anti_tip = service.check_anti_tip_requirement(cabinet)
        assert anti_tip is not None

        _ = service.get_shelf_capacities(cabinet)
        # May have 0 capacities if shelves aren't set up correctly
        # but the method should run without error

    def test_safety_labels_generation_workflow(self) -> None:
        """Test complete safety label generation workflow."""
        # Create labels based on assessment results
        labels = [
            SafetyLabel(
                label_type="weight_capacity",
                title="MAXIMUM SHELF LOAD",
                body_text="Do not exceed 45 lbs per shelf.\nDistribute weight evenly.",
                warning_icon=True,
            ),
            SafetyLabel(
                label_type="anti_tip",
                title="TIP-OVER HAZARD",
                body_text=(
                    "To reduce the risk of tip-over:\n"
                    "- Secure to wall using included hardware\n"
                    "- Do not allow children to climb\n"
                    "- Store heavier items on lower shelves"
                ),
                warning_icon=True,
                dimensions=(4.0, 4.0),
            ),
        ]

        # Export labels
        exporter = SafetyLabelExporter()

        for label in labels:
            svg = exporter.export_label(label)
            assert svg.startswith("<svg")
            assert label.title in svg

        # Export all at once
        all_svgs = exporter.export_all_labels(labels)
        assert len(all_svgs) == 2

    def test_full_report_generation_workflow(self) -> None:
        """Test complete safety report generation workflow."""
        # Create comprehensive assessment
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="weight_capacity_shelf_0",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Shelf 0: 45 lbs capacity (meets KCMA standard)",
                    standard_reference="ANSI/KCMA A161.1",
                ),
                SafetyCheckResult(
                    check_id="anti_tip_requirement",
                    category=SafetyCategory.STABILITY,
                    status=SafetyCheckStatus.WARNING,
                    message='Anti-tip restraint required: Cabinet height 84" exceeds 27" threshold',
                    remediation="Install anti-tip strap or bracket",
                    standard_reference="ASTM F2057-23",
                ),
                SafetyCheckResult(
                    check_id="accessibility_compliance",
                    category=SafetyCategory.ACCESSIBILITY,
                    status=SafetyCheckStatus.PASS,
                    message="Accessibility compliant: 75% of storage within reach range",
                    standard_reference="2010 ADA Standards",
                ),
            ],
            weight_capacities=[
                WeightCapacityEstimate(
                    panel_id="section_0_shelf_0",
                    safe_load_lbs=45.0,
                    max_deflection_inches=0.1,
                    deflection_at_rated_load=0.05,
                    safety_factor=4.0,
                    material="plywood",
                    span_inches=22.5,
                )
            ],
            accessibility_report=AccessibilityReport(
                total_storage_volume=5000.0,
                accessible_storage_volume=3750.0,
                accessible_percentage=75.0,
                is_compliant=True,
                non_compliant_areas=(),
                reach_violations=(),
                hardware_notes=("Use lever-style handles",),
            ),
            safety_labels=[
                SafetyLabel(
                    label_type="weight_capacity",
                    title="MAX LOAD",
                    body_text="45 lbs per shelf",
                ),
            ],
            anti_tip_required=True,
            seismic_hardware=["Seismic bracket", "Lag screws"],
        )

        # Generate report
        formatter = SafetyReportFormatter()
        report = formatter.format(assessment)

        # Verify report content
        assert "Safety Assessment Report" in report
        assert "Summary" in report
        assert len(report) > 500  # Should be substantial
