"""Base exporter framework with Protocol, Registry, and Manager."""

from __future__ import annotations

import logging
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput


logger = logging.getLogger(__name__)


@runtime_checkable
class Exporter(Protocol):
    """Protocol for all exporters.

    Exporters convert LayoutOutput or RoomLayoutOutput to a specific format.
    Each exporter must define its format name and file extension, and implement
    at least the export method.

    Attributes:
        format_name: Human-readable name for the export format (e.g., "stl", "json").
        file_extension: File extension without leading dot (e.g., "stl", "json").
    """

    format_name: ClassVar[str]
    file_extension: ClassVar[str]

    @abstractmethod
    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export layout output to a file.

        Args:
            output: The layout output to export.
            path: Path where the file will be saved.
        """
        ...

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Export layout output as a string.

        This method is optional. Not all formats support string export
        (e.g., binary formats like STL).

        Args:
            output: The layout output to export.

        Returns:
            String representation of the exported data.

        Raises:
            NotImplementedError: If the format does not support string export.
        """
        raise NotImplementedError(
            f"Format '{self.format_name}' does not support string export"
        )


class ExporterRegistry:
    """Registry for exporter classes.

    Provides a central registry for all available exporters. Exporters
    register themselves using the @ExporterRegistry.register decorator.

    Example:
        @ExporterRegistry.register("json")
        class JsonLayoutExporter:
            format_name = "json"
            file_extension = "json"
            ...
    """

    _exporters: ClassVar[dict[str, type[Exporter]]] = {}

    @classmethod
    def register(cls, format_name: str) -> type:
        """Decorator to register an exporter class.

        Args:
            format_name: The format name to register (e.g., "stl", "json").

        Returns:
            Decorator function that registers the class.

        Example:
            @ExporterRegistry.register("stl")
            class StlLayoutExporter:
                ...
        """

        def decorator(exporter_class: type[Exporter]) -> type[Exporter]:
            if format_name in cls._exporters:
                logger.warning(
                    f"Overwriting existing exporter for format '{format_name}'"
                )
            cls._exporters[format_name] = exporter_class
            logger.debug(f"Registered exporter '{format_name}': {exporter_class.__name__}")
            return exporter_class

        return decorator

    @classmethod
    def get(cls, format_name: str) -> type[Exporter]:
        """Get an exporter class by format name.

        Args:
            format_name: The format name to look up.

        Returns:
            The exporter class for the specified format.

        Raises:
            KeyError: If no exporter is registered for the format.
        """
        if format_name not in cls._exporters:
            available = ", ".join(sorted(cls._exporters.keys()))
            raise KeyError(
                f"No exporter registered for format '{format_name}'. "
                f"Available formats: {available or 'none'}"
            )
        return cls._exporters[format_name]

    @classmethod
    def available_formats(cls) -> list[str]:
        """Get list of all registered format names.

        Returns:
            Sorted list of available format names.
        """
        return sorted(cls._exporters.keys())

    @classmethod
    def is_registered(cls, format_name: str) -> bool:
        """Check if a format is registered.

        Args:
            format_name: The format name to check.

        Returns:
            True if the format is registered, False otherwise.
        """
        return format_name in cls._exporters

    @classmethod
    def clear(cls) -> None:
        """Clear all registered exporters.

        This is primarily useful for testing.
        """
        cls._exporters.clear()


class ExportManager:
    """Manages export operations to multiple formats.

    Coordinates exporting layout output to one or more formats,
    handling file naming and directory management.

    Attributes:
        output_dir: Directory where exported files will be saved.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize the export manager.

        Args:
            output_dir: Directory where exported files will be saved.
                        Will be created if it doesn't exist.
        """
        self.output_dir = Path(output_dir)

    def export_all(
        self,
        formats: list[str],
        output: LayoutOutput | RoomLayoutOutput,
        project_name: str = "cabinet",
    ) -> dict[str, Path]:
        """Export layout output to multiple formats.

        Args:
            formats: List of format names to export (e.g., ["stl", "json"]).
            output: The layout output to export.
            project_name: Base name for output files (default "cabinet").

        Returns:
            Dictionary mapping format names to output file paths.

        Raises:
            KeyError: If any format is not registered.
            OSError: If file operations fail.
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        results: dict[str, Path] = {}

        for format_name in formats:
            exporter_class = ExporterRegistry.get(format_name)
            exporter = exporter_class()

            # Generate filename: {project_name}_{format}.{ext}
            filename = f"{project_name}_{format_name}.{exporter.file_extension}"
            filepath = self.output_dir / filename

            logger.info(f"Exporting to {format_name}: {filepath}")
            exporter.export(output, filepath)
            results[format_name] = filepath

        return results

    def export_single(
        self,
        format_name: str,
        output: LayoutOutput | RoomLayoutOutput,
        project_name: str = "cabinet",
    ) -> Path:
        """Export layout output to a single format.

        Convenience method for exporting to just one format.

        Args:
            format_name: Format name to export (e.g., "stl").
            output: The layout output to export.
            project_name: Base name for output file (default "cabinet").

        Returns:
            Path to the exported file.

        Raises:
            KeyError: If the format is not registered.
            OSError: If file operations fail.
        """
        results = self.export_all([format_name], output, project_name)
        return results[format_name]
