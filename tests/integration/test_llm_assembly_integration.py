"""Integration tests for LLM-based assembly instruction generation.

These tests verify end-to-end workflows for the LLM assembly feature,
including CLI integration, exporter integration, and config parsing.

All tests use mocked HTTP or force fallback to avoid requiring Ollama.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from cabinets.application.config.schemas import CabinetConfiguration
from cabinets.application.dtos import LayoutOutput
from cabinets.domain.entities import Cabinet, Section
from cabinets.domain.services import MaterialEstimate
from cabinets.domain.value_objects import (
    CutPiece,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from cabinets.infrastructure.exporters import ExportManager, ExporterRegistry
from cabinets.infrastructure.llm import (
    AssemblyInstructions,
    AssemblyStep,
    LLMAssemblyGenerator,
    OllamaHealthCheck,
    SafetyWarning,
    ToolRecommendation,
    WarningSeverity,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_material() -> MaterialSpec:
    """Create a sample material specification."""
    return MaterialSpec(material_type=MaterialType.PLYWOOD, thickness=0.75)


@pytest.fixture
def sample_cabinet(sample_material: MaterialSpec) -> Cabinet:
    """Create a sample cabinet for testing."""
    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=sample_material,
        sections=[
            Section(
                width=24.0,
                height=84.0,
                depth=12.0,
                position=Position(x=0.0, y=0.0),
                shelves=[],
            ),
            Section(
                width=24.0,
                height=84.0,
                depth=12.0,
                position=Position(x=24.0, y=0.0),
                shelves=[],
            ),
        ],
    )


@pytest.fixture
def sample_cut_list(sample_material: MaterialSpec) -> list[CutPiece]:
    """Create sample cut list for testing."""
    return [
        CutPiece(
            label="Left Side",
            width=11.25,
            height=84.0,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.LEFT_SIDE,
        ),
        CutPiece(
            label="Right Side",
            width=11.25,
            height=84.0,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.RIGHT_SIDE,
        ),
        CutPiece(
            label="Top",
            width=46.5,
            height=11.25,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.TOP,
        ),
        CutPiece(
            label="Bottom",
            width=46.5,
            height=11.25,
            quantity=1,
            material=sample_material,
            panel_type=PanelType.BOTTOM,
        ),
    ]


@pytest.fixture
def sample_material_estimate() -> MaterialEstimate:
    """Create sample material estimate."""
    return MaterialEstimate(
        total_area_sqin=3000.0,
        total_area_sqft=21.0,
        sheet_count_4x8=1,
        sheet_count_5x5=1,
        waste_percentage=0.15,
    )


@pytest.fixture
def sample_output(
    sample_cabinet: Cabinet,
    sample_cut_list: list[CutPiece],
    sample_material: MaterialSpec,
    sample_material_estimate: MaterialEstimate,
) -> LayoutOutput:
    """Create sample LayoutOutput for testing."""
    return LayoutOutput(
        cabinet=sample_cabinet,
        cut_list=sample_cut_list,
        hardware=[],
        material_estimates={sample_material: sample_material_estimate},
        total_estimate=sample_material_estimate,
    )


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test configs."""
    return tmp_path


@pytest.fixture
def basic_config_json(temp_config_dir: Path) -> Path:
    """Create a basic config JSON file."""
    config = {
        "schema_version": "1.9",
        "cabinet": {
            "width": 48.0,
            "height": 84.0,
            "depth": 12.0,
        },
    }
    config_path = temp_config_dir / "cabinet.json"
    config_path.write_text(json.dumps(config))
    return config_path


@pytest.fixture
def llm_config_json(temp_config_dir: Path) -> Path:
    """Create a config JSON with LLM assembly enabled."""
    config = {
        "schema_version": "1.9",
        "cabinet": {
            "width": 48.0,
            "height": 84.0,
            "depth": 12.0,
        },
        "output": {
            "format": "all",
            "assembly": {
                "use_llm": True,
                "skill_level": "beginner",
                "llm_model": "llama3.2",
                "timeout_seconds": 45,
            },
        },
    }
    config_path = temp_config_dir / "llm_cabinet.json"
    config_path.write_text(json.dumps(config))
    return config_path


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Integration tests for CLI LLM flags."""

    def test_help_shows_llm_options(self) -> None:
        """CLI help includes LLM-related options."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["generate", "--help"])

        assert result.exit_code == 0
        assert "--llm-instructions" in result.stdout
        assert "--skill-level" in result.stdout
        assert "--llm-model" in result.stdout

    def test_invalid_skill_level_rejected(self, basic_config_json: Path) -> None:
        """Invalid skill level produces error."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(basic_config_json),
                "--skill-level",
                "novice",
            ],
        )
        assert result.exit_code != 0
        # Typer CLI result can be in result.stdout or result.output
        output = (result.stdout or result.output or "").lower()
        assert "invalid" in output or "novice" in output or result.exit_code == 1

    def test_valid_skill_levels_accepted(self, basic_config_json: Path) -> None:
        """Valid skill levels are accepted (may fallback due to no Ollama)."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        for level in ["beginner", "intermediate", "expert"]:
            result = runner.invoke(
                app,
                [
                    "generate",
                    "--config",
                    str(basic_config_json),
                    "--skill-level",
                    level,
                ],
            )
            # Should not reject due to skill level (may have other errors, but not skill level)
            assert "invalid skill level" not in result.stdout.lower()

    def test_llm_instructions_flag_without_ollama(
        self, basic_config_json: Path
    ) -> None:
        """CLI handles missing Ollama gracefully."""
        from typer.testing import CliRunner
        from cabinets.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "generate",
                "--config",
                str(basic_config_json),
                "--llm-instructions",
            ],
        )
        # Should complete (possibly with fallback message)
        # Check it doesn't crash with unhandled exception
        assert (
            "Traceback (most recent call last)" not in result.stdout
            or result.exit_code == 0
        )


# =============================================================================
# Config Parsing Tests
# =============================================================================


class TestConfigParsing:
    """Integration tests for config file parsing with LLM options."""

    def test_parse_config_with_llm_assembly(self, llm_config_json: Path) -> None:
        """Config with LLM assembly options parses correctly."""
        config_text = llm_config_json.read_text()
        config = CabinetConfiguration.model_validate_json(config_text)

        assert config.schema_version == "1.9"
        assert config.output is not None
        assert config.output.assembly is not None
        assert config.output.assembly.use_llm is True
        assert config.output.assembly.skill_level == "beginner"
        assert config.output.assembly.llm_model == "llama3.2"
        assert config.output.assembly.timeout_seconds == 45

    def test_parse_config_without_assembly(self, basic_config_json: Path) -> None:
        """Config without assembly section uses defaults."""
        config_text = basic_config_json.read_text()
        config = CabinetConfiguration.model_validate_json(config_text)

        # Default assembly config should be available via output
        if config.output and config.output.assembly:
            assert config.output.assembly.use_llm is False
            assert config.output.assembly.skill_level == "intermediate"

    def test_backward_compatible_config_1_8(self, temp_config_dir: Path) -> None:
        """Old config format (1.8) still works."""
        config = {
            "schema_version": "1.8",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config_path = temp_config_dir / "old_config.json"
        config_path.write_text(json.dumps(config))

        parsed = CabinetConfiguration.model_validate_json(config_path.read_text())
        assert parsed.schema_version == "1.8"


# =============================================================================
# Exporter Integration Tests
# =============================================================================


class TestExporterIntegration:
    """Integration tests for LLM assembly exporter."""

    def test_llm_assembly_format_registered(self) -> None:
        """'llm-assembly' format is available in registry."""
        formats = ExporterRegistry.available_formats()
        assert "llm-assembly" in formats

    def test_get_llm_assembly_exporter(self) -> None:
        """Can retrieve LLM assembly exporter from registry."""
        exporter_class = ExporterRegistry.get("llm-assembly")
        assert exporter_class.format_name == "llm-assembly"
        assert exporter_class.file_extension == "md"

    def test_create_exporter_with_config(self) -> None:
        """Can create exporter with custom configuration."""
        from cabinets.infrastructure.exporters import LLMAssemblyExporter

        exporter = LLMAssemblyExporter(
            skill_level="beginner",
            timeout=60.0,
            model="mistral:7b",
        )
        assert exporter.generator.skill_level == "beginner"
        assert exporter.generator.timeout == 60.0
        assert exporter.generator.model == "mistral:7b"

    def test_export_string_returns_markdown(self, sample_output: LayoutOutput) -> None:
        """export_string returns valid markdown content."""
        from cabinets.infrastructure.exporters import LLMAssemblyExporter

        # Force fallback for reliable testing
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        content = exporter.export_string(sample_output)

        assert isinstance(content, str)
        assert len(content) > 0
        # Should have markdown structure (from fallback)
        assert "##" in content  # Has headings

    def test_export_to_file(self, sample_output: LayoutOutput, tmp_path: Path) -> None:
        """export writes content to file."""
        from cabinets.infrastructure.exporters import LLMAssemblyExporter

        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        output_path = tmp_path / "assembly.md"

        exporter.export(sample_output, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert len(content) > 0


# =============================================================================
# ExportManager Integration Tests
# =============================================================================


class TestExportManagerIntegration:
    """Integration tests for ExportManager with llm-assembly format."""

    def test_export_llm_assembly_format(
        self, sample_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """ExportManager can export to llm-assembly format."""
        manager = ExportManager(output_dir=tmp_path)

        results = manager.export_all(
            formats=["llm-assembly"],
            output=sample_output,
            project_name="test-cabinet",
        )

        assert "llm-assembly" in results
        assert results["llm-assembly"].exists()
        assert results["llm-assembly"].suffix == ".md"

    def test_export_multiple_formats_including_llm(
        self, sample_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """ExportManager exports llm-assembly alongside other formats."""
        manager = ExportManager(output_dir=tmp_path)

        results = manager.export_all(
            formats=["json", "llm-assembly"],
            output=sample_output,
            project_name="test-cabinet",
        )

        assert "json" in results
        assert "llm-assembly" in results
        assert results["json"].exists()
        assert results["llm-assembly"].exists()


# =============================================================================
# Fallback Behavior Tests
# =============================================================================


class TestFallbackBehavior:
    """Integration tests for fallback behavior."""

    def test_fallback_produces_valid_markdown(
        self, sample_output: LayoutOutput
    ) -> None:
        """Fallback produces structurally valid markdown."""
        generator = LLMAssemblyGenerator(ollama_url="http://localhost:99999")
        content = generator.generate_sync(sample_output)

        # Check for expected sections
        assert "## Assembly Steps" in content or "## Materials" in content
        # Should indicate fallback
        assert "template fallback" in content

    def test_fallback_indicator_is_html_comment(
        self, sample_output: LayoutOutput
    ) -> None:
        """Fallback indicator is non-visible HTML comment."""
        generator = LLMAssemblyGenerator(ollama_url="http://localhost:99999")
        content = generator.generate_sync(sample_output)

        # HTML comment at start
        assert content.startswith("<!--")
        # Comment closed within first few lines
        lines = content.split("\n")
        comment_closed = any("-->" in line for line in lines[:5])
        assert comment_closed


# =============================================================================
# Full Pipeline Tests (Mocked)
# =============================================================================


class TestFullPipelineMocked:
    """End-to-end pipeline tests with mocked LLM."""

    @pytest.mark.asyncio
    async def test_generate_with_mocked_llm(self, sample_output: LayoutOutput) -> None:
        """Full generation pipeline with mocked LLM response."""
        # Create mock LLM response
        mock_instructions = AssemblyInstructions(
            title="Test Cabinet Assembly",
            skill_level="intermediate",
            cabinet_summary="48x84x12 plywood cabinet",
            estimated_time="3-4 hours",
            safety_warnings=[
                SafetyWarning(
                    severity=WarningSeverity.WARNING,
                    message="Wear safety glasses",
                    context="All operations",
                    mitigation="Keep glasses on",
                ),
            ],
            tools_needed=[
                ToolRecommendation(
                    tool="Table saw",
                    purpose="Panel cutting",
                    required=True,
                ),
            ],
            materials_checklist=["Left Side (1x)", "Right Side (1x)"],
            steps=[
                AssemblyStep(
                    step_number=1,
                    phase="Preparation",
                    title="Prepare Panels",
                    description="Lay out panels...",
                    pieces_involved=["Left Side", "Right Side"],
                ),
            ],
            finishing_notes="Apply finish as desired.",
        )

        generator = LLMAssemblyGenerator()

        # Mock the health check and agent
        with (
            patch.object(
                generator.health_check, "is_available", new_callable=AsyncMock
            ) as mock_available,
            patch.object(
                generator.health_check, "has_model", new_callable=AsyncMock
            ) as mock_has_model,
            patch(
                "cabinets.infrastructure.llm.generator.run_assembly_agent",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_available.return_value = True
            mock_has_model.return_value = True
            mock_agent.return_value = mock_instructions

            result = await generator.generate(sample_output)

        # Verify output contains expected content
        assert "Test Cabinet Assembly" in result
        assert "Wear safety glasses" in result
        assert "Table saw" in result
        assert "Prepare Panels" in result

    def test_pipeline_handles_partial_llm_response(
        self, sample_output: LayoutOutput
    ) -> None:
        """Pipeline handles LLM response with minimal content."""
        # Minimal valid response
        mock_instructions = AssemblyInstructions(
            title="Minimal",
            skill_level="expert",
            cabinet_summary="Cabinet",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Done.",
        )

        generator = LLMAssemblyGenerator()

        with (
            patch.object(
                generator.health_check, "is_available", new_callable=AsyncMock
            ) as mock_available,
            patch.object(
                generator.health_check, "has_model", new_callable=AsyncMock
            ) as mock_has_model,
            patch(
                "cabinets.infrastructure.llm.generator.run_assembly_agent",
                new_callable=AsyncMock,
            ) as mock_agent,
        ):
            mock_available.return_value = True
            mock_has_model.return_value = True
            mock_agent.return_value = mock_instructions

            result = asyncio.run(generator.generate(sample_output))

        # Should still produce valid markdown
        assert "Minimal" in result
        assert "## Finishing" in result


# =============================================================================
# Health Check Integration Tests
# =============================================================================


class TestOllamaHealthCheckIntegration:
    """Integration tests for OllamaHealthCheck."""

    def test_unavailable_server_returns_false(self) -> None:
        """Test that unavailable server returns False quickly."""
        health = OllamaHealthCheck(
            base_url="http://127.0.0.1:59999",  # Port unlikely to be in use
            timeout=2.0,  # Short timeout
        )
        is_available = asyncio.run(health.is_available())
        assert is_available is False
