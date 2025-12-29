"""Tests for the exporter framework (base.py)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import ClassVar

import pytest

from cabinets.infrastructure.exporters import (
    Exporter,
    ExporterRegistry,
    ExportManager,
    StlLayoutExporter,
)


class TestExporterRegistry:
    """Tests for ExporterRegistry."""

    def setup_method(self) -> None:
        """Store original exporters before each test."""
        self._original_exporters = ExporterRegistry._exporters.copy()

    def teardown_method(self) -> None:
        """Restore original exporters after each test."""
        ExporterRegistry._exporters = self._original_exporters

    def test_stl_exporter_is_registered(self) -> None:
        """StlLayoutExporter should be registered as 'stl'."""
        assert ExporterRegistry.is_registered("stl")
        assert ExporterRegistry.get("stl") is StlLayoutExporter

    def test_available_formats_includes_stl(self) -> None:
        """available_formats() should include 'stl'."""
        formats = ExporterRegistry.available_formats()
        assert "stl" in formats

    def test_get_unknown_format_raises_key_error(self) -> None:
        """get() should raise KeyError for unknown formats."""
        with pytest.raises(KeyError) as exc_info:
            ExporterRegistry.get("unknown_format")
        assert "No exporter registered for format 'unknown_format'" in str(
            exc_info.value
        )

    def test_register_new_exporter(self) -> None:
        """register() should add a new exporter to the registry."""

        @ExporterRegistry.register("test_format")
        class TestExporter:
            format_name: ClassVar[str] = "test_format"
            file_extension: ClassVar[str] = "test"

            def export(self, output, path: Path) -> None:
                pass

        assert ExporterRegistry.is_registered("test_format")
        assert ExporterRegistry.get("test_format") is TestExporter
        assert "test_format" in ExporterRegistry.available_formats()

    def test_is_registered_returns_false_for_unknown(self) -> None:
        """is_registered() should return False for unknown formats."""
        assert not ExporterRegistry.is_registered("nonexistent_format")

    def test_clear_removes_all_exporters(self) -> None:
        """clear() should remove all registered exporters."""
        # Register a test exporter
        @ExporterRegistry.register("temp_test")
        class TempExporter:
            format_name: ClassVar[str] = "temp_test"
            file_extension: ClassVar[str] = "tmp"

            def export(self, output, path: Path) -> None:
                pass

        assert ExporterRegistry.is_registered("temp_test")

        ExporterRegistry.clear()
        assert ExporterRegistry.available_formats() == []


class TestStlLayoutExporter:
    """Tests for StlLayoutExporter."""

    def test_format_name(self) -> None:
        """StlLayoutExporter should have format_name 'stl'."""
        assert StlLayoutExporter.format_name == "stl"

    def test_file_extension(self) -> None:
        """StlLayoutExporter should have file_extension 'stl'."""
        assert StlLayoutExporter.file_extension == "stl"

    def test_export_string_raises_not_implemented(self) -> None:
        """export_string() should raise NotImplementedError for binary format."""
        exporter = StlLayoutExporter()
        with pytest.raises(NotImplementedError) as exc_info:
            exporter.export_string(None)  # type: ignore
        assert "binary" in str(exc_info.value).lower()


class TestExportManager:
    """Tests for ExportManager."""

    def test_init_creates_instance_with_output_dir(self) -> None:
        """ExportManager should store the output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExportManager(Path(tmpdir))
            assert manager.output_dir == Path(tmpdir)

    def test_export_all_unknown_format_raises_key_error(self) -> None:
        """export_all() should raise KeyError for unknown formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ExportManager(Path(tmpdir))
            with pytest.raises(KeyError):
                manager.export_all(["unknown_format"], None, "test")  # type: ignore


class TestExporterProtocol:
    """Tests for the Exporter protocol."""

    def test_stl_exporter_implements_protocol(self) -> None:
        """StlLayoutExporter should implement the Exporter protocol."""
        exporter = StlLayoutExporter()
        # Protocol check via isinstance with runtime_checkable
        assert isinstance(exporter, Exporter)

    def test_stl_exporter_has_required_attributes(self) -> None:
        """StlLayoutExporter should have all required protocol attributes."""
        # Check class attributes exist
        assert hasattr(StlLayoutExporter, "format_name")
        assert hasattr(StlLayoutExporter, "file_extension")

        # Check instance has export method
        exporter = StlLayoutExporter()
        assert hasattr(exporter, "export")
        assert callable(exporter.export)

    def test_stl_exporter_has_optional_export_string(self) -> None:
        """StlLayoutExporter should have export_string method (optional in protocol)."""
        exporter = StlLayoutExporter()
        assert hasattr(exporter, "export_string")
        assert callable(exporter.export_string)
