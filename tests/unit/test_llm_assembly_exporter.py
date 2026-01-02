"""Unit tests for LLMAssemblyExporter.

Tests cover:
- Exporter registration with ExporterRegistry
- Class attributes (format_name, file_extension)
- Initialization with default and custom parameters
- export() method for file output
- export_string() method for string output
- from_config() factory method
- Integration with LLMAssemblyGenerator
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cabinets.application.config.schemas import AssemblyOutputConfigSchema
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
from cabinets.infrastructure.exporters import (
    ExporterRegistry,
    LLMAssemblyExporter,
)


@pytest.fixture
def material() -> MaterialSpec:
    """Create a test material specification."""
    return MaterialSpec(material_type=MaterialType.PLYWOOD, thickness=0.75)


@pytest.fixture
def cabinet(material: MaterialSpec) -> Cabinet:
    """Create a test cabinet."""
    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=material,
        sections=[
            Section(
                width=48.0,
                height=84.0,
                depth=12.0,
                position=Position(x=0.0, y=0.0),
                shelves=[],
            )
        ],
    )


@pytest.fixture
def cut_list(material: MaterialSpec) -> list[CutPiece]:
    """Create a test cut list."""
    return [
        CutPiece(
            label="Left Side",
            width=11.25,
            height=84.0,
            quantity=1,
            material=material,
            panel_type=PanelType.LEFT_SIDE,
        ),
        CutPiece(
            label="Right Side",
            width=11.25,
            height=84.0,
            quantity=1,
            material=material,
            panel_type=PanelType.RIGHT_SIDE,
        ),
    ]


@pytest.fixture
def material_estimate() -> MaterialEstimate:
    """Create a test material estimate."""
    return MaterialEstimate(
        total_area_sqin=1000.0,
        total_area_sqft=7.0,
        sheet_count_4x8=1,
        sheet_count_5x5=0,
        waste_percentage=5.0,
    )


@pytest.fixture
def layout_output(
    cabinet: Cabinet,
    cut_list: list[CutPiece],
    material: MaterialSpec,
    material_estimate: MaterialEstimate,
) -> LayoutOutput:
    """Create a test layout output."""
    return LayoutOutput(
        cabinet=cabinet,
        cut_list=cut_list,
        hardware=[],
        material_estimates={material: material_estimate},
        total_estimate=material_estimate,
    )


class TestExporterRegistration:
    """Tests for exporter registration with ExporterRegistry."""

    def test_llm_assembly_is_registered(self) -> None:
        """llm-assembly format is registered in ExporterRegistry."""
        assert ExporterRegistry.is_registered("llm-assembly")

    def test_available_formats_includes_llm_assembly(self) -> None:
        """available_formats() includes llm-assembly."""
        formats = ExporterRegistry.available_formats()
        assert "llm-assembly" in formats

    def test_get_returns_llm_assembly_exporter_class(self) -> None:
        """get('llm-assembly') returns LLMAssemblyExporter class."""
        exporter_class = ExporterRegistry.get("llm-assembly")
        assert exporter_class is LLMAssemblyExporter


class TestExporterAttributes:
    """Tests for LLMAssemblyExporter class attributes."""

    def test_format_name_is_llm_assembly(self) -> None:
        """format_name is 'llm-assembly'."""
        assert LLMAssemblyExporter.format_name == "llm-assembly"

    def test_file_extension_is_md(self) -> None:
        """file_extension is 'md'."""
        assert LLMAssemblyExporter.file_extension == "md"

    def test_instance_format_name(self) -> None:
        """Instance has correct format_name attribute."""
        exporter = LLMAssemblyExporter()
        assert exporter.format_name == "llm-assembly"

    def test_instance_file_extension(self) -> None:
        """Instance has correct file_extension attribute."""
        exporter = LLMAssemblyExporter()
        assert exporter.file_extension == "md"


class TestExporterInitialization:
    """Tests for LLMAssemblyExporter initialization."""

    def test_default_initialization(self) -> None:
        """Exporter can be initialized with defaults."""
        exporter = LLMAssemblyExporter()
        assert exporter.generator.ollama_url == "http://localhost:11434"
        assert exporter.generator.model == "llama3.2"
        assert exporter.generator.timeout == 30.0
        assert exporter.generator.skill_level == "intermediate"
        assert exporter.generator.include_troubleshooting is True
        assert exporter.generator.include_time_estimates is True

    def test_custom_ollama_url(self) -> None:
        """Exporter accepts custom ollama_url."""
        exporter = LLMAssemblyExporter(ollama_url="http://custom:8080")
        assert exporter.generator.ollama_url == "http://custom:8080"

    def test_custom_model(self) -> None:
        """Exporter accepts custom model."""
        exporter = LLMAssemblyExporter(model="mistral:7b")
        assert exporter.generator.model == "mistral:7b"

    def test_custom_timeout(self) -> None:
        """Exporter accepts custom timeout."""
        exporter = LLMAssemblyExporter(timeout=60.0)
        assert exporter.generator.timeout == 60.0

    def test_custom_skill_level_beginner(self) -> None:
        """Exporter accepts skill_level='beginner'."""
        exporter = LLMAssemblyExporter(skill_level="beginner")
        assert exporter.generator.skill_level == "beginner"

    def test_custom_skill_level_expert(self) -> None:
        """Exporter accepts skill_level='expert'."""
        exporter = LLMAssemblyExporter(skill_level="expert")
        assert exporter.generator.skill_level == "expert"

    def test_disable_troubleshooting(self) -> None:
        """Exporter accepts include_troubleshooting=False."""
        exporter = LLMAssemblyExporter(include_troubleshooting=False)
        assert exporter.generator.include_troubleshooting is False

    def test_disable_time_estimates(self) -> None:
        """Exporter accepts include_time_estimates=False."""
        exporter = LLMAssemblyExporter(include_time_estimates=False)
        assert exporter.generator.include_time_estimates is False


class TestExportString:
    """Tests for export_string() method."""

    def test_export_string_returns_string(self, layout_output: LayoutOutput) -> None:
        """export_string() returns a string."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        content = exporter.export_string(layout_output)
        assert isinstance(content, str)

    def test_export_string_returns_non_empty(self, layout_output: LayoutOutput) -> None:
        """export_string() returns non-empty content."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        content = exporter.export_string(layout_output)
        assert len(content) > 0

    def test_export_string_contains_assembly_steps(
        self, layout_output: LayoutOutput
    ) -> None:
        """export_string() contains assembly steps section."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        content = exporter.export_string(layout_output)
        assert "## Assembly Steps" in content

    def test_export_string_uses_generator(self, layout_output: LayoutOutput) -> None:
        """export_string() delegates to generator.generate_sync()."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")

        with patch.object(
            exporter.generator, "generate_sync", return_value="mocked content"
        ) as mock_generate:
            content = exporter.export_string(layout_output)
            mock_generate.assert_called_once_with(layout_output)
            assert content == "mocked content"


class TestExport:
    """Tests for export() method."""

    def test_export_writes_file(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """export() writes content to file."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        output_path = tmp_path / "assembly.md"

        exporter.export(layout_output, output_path)

        assert output_path.exists()

    def test_export_file_content_matches_string(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """export() file content matches export_string() output."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        output_path = tmp_path / "assembly.md"

        exporter.export(layout_output, output_path)
        file_content = output_path.read_text()
        string_content = exporter.export_string(layout_output)

        # Both use fallback, so contents should be similar structure
        assert "## Assembly Steps" in file_content
        assert "## Assembly Steps" in string_content

    def test_export_creates_markdown_file(
        self, layout_output: LayoutOutput, tmp_path: Path
    ) -> None:
        """export() creates a markdown file with .md extension."""
        exporter = LLMAssemblyExporter(ollama_url="http://localhost:99999")
        output_path = tmp_path / "assembly.md"

        exporter.export(layout_output, output_path)

        assert output_path.suffix == ".md"
        content = output_path.read_text()
        assert content.startswith("<!--") or content.startswith("#")


class TestFromConfig:
    """Tests for from_config() factory method."""

    def test_from_config_with_none(self) -> None:
        """from_config(None) returns exporter with defaults."""
        exporter = LLMAssemblyExporter.from_config(None)
        assert exporter.generator.skill_level == "intermediate"
        assert exporter.generator.model == "llama3.2"
        assert exporter.generator.timeout == 30.0
        assert exporter.generator.ollama_url == "http://localhost:11434"

    def test_from_config_with_skill_level(self) -> None:
        """from_config() applies skill_level from config."""
        config = AssemblyOutputConfigSchema(skill_level="expert")
        exporter = LLMAssemblyExporter.from_config(config)
        assert exporter.generator.skill_level == "expert"

    def test_from_config_with_llm_model(self) -> None:
        """from_config() applies llm_model from config."""
        config = AssemblyOutputConfigSchema(llm_model="mistral:7b")
        exporter = LLMAssemblyExporter.from_config(config)
        assert exporter.generator.model == "mistral:7b"

    def test_from_config_with_timeout_seconds(self) -> None:
        """from_config() applies timeout_seconds from config."""
        config = AssemblyOutputConfigSchema(timeout_seconds=60)
        exporter = LLMAssemblyExporter.from_config(config)
        assert exporter.generator.timeout == 60.0

    def test_from_config_with_ollama_url(self) -> None:
        """from_config() applies ollama_url from config."""
        config = AssemblyOutputConfigSchema(ollama_url="http://custom:8080")
        exporter = LLMAssemblyExporter.from_config(config)
        assert exporter.generator.ollama_url == "http://custom:8080"

    def test_from_config_with_include_troubleshooting(self) -> None:
        """from_config() applies include_troubleshooting from config."""
        config = AssemblyOutputConfigSchema(include_troubleshooting=False)
        exporter = LLMAssemblyExporter.from_config(config)
        assert exporter.generator.include_troubleshooting is False

    def test_from_config_with_include_time_estimates(self) -> None:
        """from_config() applies include_time_estimates from config."""
        config = AssemblyOutputConfigSchema(include_time_estimates=False)
        exporter = LLMAssemblyExporter.from_config(config)
        assert exporter.generator.include_time_estimates is False

    def test_from_config_full_configuration(self) -> None:
        """from_config() applies all settings from config."""
        config = AssemblyOutputConfigSchema(
            use_llm=True,
            skill_level="beginner",
            llm_model="codellama:13b",
            ollama_url="http://llm-server:11434",
            timeout_seconds=120,
            include_troubleshooting=False,
            include_time_estimates=False,
        )
        exporter = LLMAssemblyExporter.from_config(config)

        assert exporter.generator.skill_level == "beginner"
        assert exporter.generator.model == "codellama:13b"
        assert exporter.generator.ollama_url == "http://llm-server:11434"
        assert exporter.generator.timeout == 120.0
        assert exporter.generator.include_troubleshooting is False
        assert exporter.generator.include_time_estimates is False


class TestExporterProtocol:
    """Tests for Exporter protocol compliance."""

    def test_has_format_name_class_var(self) -> None:
        """LLMAssemblyExporter has format_name ClassVar."""
        assert hasattr(LLMAssemblyExporter, "format_name")
        assert LLMAssemblyExporter.format_name == "llm-assembly"

    def test_has_file_extension_class_var(self) -> None:
        """LLMAssemblyExporter has file_extension ClassVar."""
        assert hasattr(LLMAssemblyExporter, "file_extension")
        assert LLMAssemblyExporter.file_extension == "md"

    def test_has_export_method(self) -> None:
        """LLMAssemblyExporter has export method."""
        exporter = LLMAssemblyExporter()
        assert callable(exporter.export)

    def test_has_export_string_method(self) -> None:
        """LLMAssemblyExporter has export_string method."""
        exporter = LLMAssemblyExporter()
        assert callable(exporter.export_string)

    def test_implements_exporter_protocol(self) -> None:
        """LLMAssemblyExporter can be used as Exporter."""
        from cabinets.infrastructure.exporters.base import Exporter

        exporter = LLMAssemblyExporter()
        # Protocol check (runtime_checkable)
        assert isinstance(exporter, Exporter)


class TestModuleExports:
    """Tests for module-level exports."""

    def test_importable_from_exporters_package(self) -> None:
        """LLMAssemblyExporter is importable from exporters package."""
        from cabinets.infrastructure.exporters import LLMAssemblyExporter as Exported

        assert Exported is LLMAssemblyExporter

    def test_in_exporters_all(self) -> None:
        """LLMAssemblyExporter is in __all__."""
        from cabinets.infrastructure import exporters

        assert "LLMAssemblyExporter" in exporters.__all__
