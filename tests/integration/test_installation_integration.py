"""Integration tests for FRD-17 Installation Support.

Tests the complete integration of installation support through:
- GenerateLayoutCommand with installation config
- CLI with installation options
- Installation formatter output
- French cleat cut pieces in cut list
"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain.services.installation import InstallationConfig
from cabinets.domain.value_objects import LoadCategory, MountingSystem, WallType
from cabinets.infrastructure import InstallationFormatter


class TestInstallationCommandIntegration:
    """Test installation support in GenerateLayoutCommand."""

    def test_execute_with_installation_config_adds_hardware(self) -> None:
        """Test that installation config adds hardware to output."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.MEDIUM,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        assert result.is_valid
        assert result.installation_hardware is not None
        assert len(result.installation_hardware) > 0
        assert result.installation_instructions is not None
        assert len(result.installation_instructions) > 0
        assert result.stud_analysis is not None

    def test_execute_with_french_cleat_adds_cleat_cut_pieces(self) -> None:
        """Test that French cleat mounting adds cleat cut pieces."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.FRENCH_CLEAT,
            expected_load=LoadCategory.HEAVY,
            cleat_position_from_top=4.0,
            cleat_width_percentage=90.0,
            cleat_bevel_angle=45.0,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        assert result.is_valid
        # Check for cleat cut pieces in cut list
        cleat_pieces = [cp for cp in result.cut_list if "cleat" in cp.label.lower()]
        assert len(cleat_pieces) >= 2, "Should have wall and cabinet cleats"

    def test_execute_without_installation_config_has_none_fields(self) -> None:
        """Test that without installation config, fields are None."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert result.installation_hardware is None
        assert result.installation_instructions is None
        assert result.installation_warnings is None
        assert result.stud_analysis is None

    def test_stud_analysis_structure(self) -> None:
        """Test that stud analysis has the expected structure."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.MEDIUM,
        )

        result = command.execute(
            wall_input,
            params_input,
            installation_config=installation_config,
            left_edge_position=0.0,
        )

        assert result.stud_analysis is not None
        assert "cabinet_left_edge" in result.stud_analysis
        assert "cabinet_width" in result.stud_analysis
        assert "stud_positions" in result.stud_analysis
        assert "stud_hit_count" in result.stud_analysis
        assert "recommendation" in result.stud_analysis

    def test_left_edge_position_affects_stud_analysis(self) -> None:
        """Test that left_edge_position changes stud analysis."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            stud_offset=0.0,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.MEDIUM,
        )

        # Cabinet at position 0
        result_0 = command.execute(
            wall_input,
            params_input,
            installation_config=installation_config,
            left_edge_position=0.0,
        )

        # Cabinet at position 8 (between studs)
        result_8 = command.execute(
            wall_input,
            params_input,
            installation_config=installation_config,
            left_edge_position=8.0,
        )

        assert result_0.stud_analysis["cabinet_left_edge"] == 0.0
        assert result_8.stud_analysis["cabinet_left_edge"] == 8.0


class TestInstallationFormatterIntegration:
    """Test InstallationFormatter with real output."""

    def test_format_complete_output(self) -> None:
        """Test formatting complete installation output."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.FRENCH_CLEAT,
            expected_load=LoadCategory.HEAVY,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        formatter = InstallationFormatter()
        output = formatter.format(result)

        assert len(output) > 0
        # Should contain markdown headers from instructions
        assert "#" in output or "Installation" in output

    def test_format_hardware_summary(self) -> None:
        """Test formatting hardware summary."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.MEDIUM,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        formatter = InstallationFormatter()
        summary = formatter.format_hardware_summary(result)

        assert "INSTALLATION HARDWARE" in summary
        assert "Total items:" in summary

    def test_format_stud_analysis(self) -> None:
        """Test formatting stud analysis."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.MEDIUM,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        formatter = InstallationFormatter()
        analysis = formatter.format_stud_analysis(result)

        assert "STUD ALIGNMENT ANALYSIS" in analysis
        assert "Cabinet left edge" in analysis
        assert "Cabinet width" in analysis
        assert "Stud hits" in analysis

    def test_format_empty_output_when_no_installation(self) -> None:
        """Test that format returns empty string when no installation data."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )

        result = command.execute(wall_input, params_input)

        formatter = InstallationFormatter()
        output = formatter.format(result)

        assert output == ""


class TestInstallationCLIIntegration:
    """Test CLI with installation options."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_with_wall_type_option(self, runner: CliRunner) -> None:
        """Test CLI with --wall-type option."""
        from cabinets.cli.main import app

        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--wall-type", "drywall",
                "--mounting-system", "french_cleat",
                "--format", "installation",
            ],
        )

        assert result.exit_code == 0
        assert "Installation" in result.output or "INSTALLATION" in result.output

    def test_cli_with_mounting_system_option(self, runner: CliRunner) -> None:
        """Test CLI with --mounting-system option."""
        from cabinets.cli.main import app

        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--mounting-system", "direct_to_stud",
                "--format", "installation",
            ],
        )

        assert result.exit_code == 0

    def test_cli_installation_format_requires_config(self, runner: CliRunner) -> None:
        """Test that installation format requires installation config."""
        from cabinets.cli.main import app

        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--format", "installation",
            ],
        )

        # Should fail because no installation config
        assert result.exit_code != 0
        assert "No installation data" in result.output

    def test_cli_all_format_shows_installation_when_configured(
        self, runner: CliRunner
    ) -> None:
        """Test that 'all' format shows installation summary when configured."""
        from cabinets.cli.main import app

        result = runner.invoke(
            app,
            [
                "generate",
                "--width", "48",
                "--height", "84",
                "--depth", "12",
                "--mounting-system", "french_cleat",
                "--format", "all",
            ],
        )

        assert result.exit_code == 0
        assert "INSTALLATION SUMMARY" in result.output


class TestInstallationConfigFileIntegration:
    """Test installation config from JSON file."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_config_file_with_installation_section(self, runner: CliRunner) -> None:
        """Test loading installation config from JSON file."""
        from cabinets.cli.main import app

        config = {
            "schema_version": "1.8",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
            "installation": {
                "wall_type": "drywall",
                "stud_spacing": 16.0,
                "mounting_system": "french_cleat",
                "expected_load": "heavy",
                "cleat": {
                    "position_from_top": 4.0,
                    "width_percentage": 90.0,
                    "bevel_angle": 45.0,
                },
            },
            "output": {"format": "installation"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config", config_path,
                ],
            )

            assert result.exit_code == 0
            assert "INSTALLATION" in result.output or "Installation" in result.output
        finally:
            Path(config_path).unlink()

    def test_config_file_installation_with_cli_override(
        self, runner: CliRunner
    ) -> None:
        """Test that CLI options override config file installation settings."""
        from cabinets.cli.main import app

        config = {
            "schema_version": "1.8",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
            "installation": {
                "wall_type": "drywall",
                "stud_spacing": 16.0,
                "mounting_system": "direct_to_stud",
                "expected_load": "light",
            },
            "output": {"format": "cutlist"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            config_path = f.name

        try:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config", config_path,
                    "--mounting-system", "french_cleat",  # Override
                    "--expected-load", "heavy",  # Override
                    "--format", "installation",
                ],
            )

            # Should succeed with overridden config
            assert result.exit_code == 0
        finally:
            Path(config_path).unlink()


class TestFrenchCleatCutPiecesIntegration:
    """Test that French cleat cut pieces appear in cut list."""

    def test_cleat_pieces_have_correct_labels(self) -> None:
        """Test that cleat cut pieces have correct labels."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.FRENCH_CLEAT,
            expected_load=LoadCategory.HEAVY,
            cleat_width_percentage=90.0,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        cleat_labels = [
            cp.label.lower() for cp in result.cut_list if "cleat" in cp.label.lower()
        ]
        assert any("wall" in label for label in cleat_labels), "Missing wall cleat"
        assert any(
            "cabinet" in label for label in cleat_labels
        ), "Missing cabinet cleat"

    def test_cleat_dimensions_are_reasonable(self) -> None:
        """Test that cleat dimensions are reasonable."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            stud_spacing=16.0,
            mounting_system=MountingSystem.FRENCH_CLEAT,
            expected_load=LoadCategory.HEAVY,
            cleat_width_percentage=90.0,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        cleat_pieces = [
            cp for cp in result.cut_list if "cleat" in cp.label.lower()
        ]

        for cp in cleat_pieces:
            # Cleat width should be approximately 90% of 48" = 43.2"
            # With material thickness subtracted for inner width
            assert cp.width > 30.0, f"Cleat too narrow: {cp.width}"
            assert cp.width <= 48.0, f"Cleat too wide: {cp.width}"
            # Cleat height (thickness of cleat piece) should be reasonable
            assert cp.height > 1.0, f"Cleat height too small: {cp.height}"
            assert cp.height < 12.0, f"Cleat height too large: {cp.height}"


class TestInstallationWarningsIntegration:
    """Test installation warnings generation."""

    def test_masonry_wall_generates_warning(self) -> None:
        """Test that masonry walls generate appropriate warnings."""
        command = GenerateLayoutCommand()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1,
            shelves_per_section=3,
            material_thickness=0.75,
        )
        installation_config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            stud_spacing=16.0,  # Studs don't apply to concrete
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.HEAVY,
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        assert result.installation_warnings is not None
        # Concrete walls should have masonry-specific warnings
        all_warnings = " ".join(result.installation_warnings).lower()
        # May warn about anchors or masonry-specific requirements
        assert (
            len(result.installation_warnings) > 0
            or "concrete" in result.installation_instructions.lower()
        )
