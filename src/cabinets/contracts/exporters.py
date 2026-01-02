"""Exporter protocols for file output generation.

This module defines protocol classes for exporters that convert layout
output to various file formats (STL, JSON, etc.). These protocols extend
the existing Exporter protocol pattern from infrastructure/exporters/base.py.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput
    from cabinets.domain.entities import Cabinet


@runtime_checkable
class ExporterProtocol(Protocol):
    """Base protocol for all exporters.

    Exporters convert LayoutOutput or RoomLayoutOutput to a specific format.
    Each exporter must define its format name and file extension, and implement
    at least the export method.

    This protocol mirrors the Exporter protocol in infrastructure/exporters/base.py
    and serves as the contract for dependency injection.

    Attributes:
        format_name: Human-readable name for the export format (e.g., "stl", "json").
        file_extension: File extension without leading dot (e.g., "stl", "json").

    Example:
        ```python
        class StlExporter:
            format_name: ClassVar[str] = "stl"
            file_extension: ClassVar[str] = "stl"

            def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
                # Implementation
                ...
        ```
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


class StlExporterProtocol(Protocol):
    """Protocol for STL file export.

    Implementations export cabinet layouts to STL (stereolithography) format
    for 3D visualization or printing.

    Example:
        ```python
        class StlExporter:
            def export(self, cabinet: Cabinet, door_ajar_angle: float = 45.0) -> Any:
                # Generate 3D mesh
                ...

            def export_to_file(self, cabinet: Cabinet, filepath: Path, door_ajar_angle: float = 45.0) -> None:
                # Generate 3D mesh and write to STL file
                ...
        ```
    """

    def export(self, cabinet: "Cabinet", door_ajar_angle: float = 45.0) -> "Any":
        """Export a cabinet to an STL mesh object.

        Args:
            cabinet: The cabinet to export.
            door_ajar_angle: Angle in degrees to open doors.

        Returns:
            A mesh object representing the entire cabinet.
        """
        ...

    def export_to_file(
        self,
        cabinet: "Cabinet",
        filepath: "Path | str",
        door_ajar_angle: float = 45.0,
    ) -> None:
        """Export a cabinet to an STL file.

        Args:
            cabinet: The cabinet to export.
            filepath: Path where the STL file will be saved.
            door_ajar_angle: Angle in degrees to open doors.
        """
        ...


class JsonExporterProtocol(Protocol):
    """Protocol for JSON export.

    Implementations export cabinet layouts to JSON format for
    data exchange, storage, or further processing.

    Example:
        ```python
        class JsonExporter:
            def export(self, output: LayoutOutput) -> str:
                # Serialize to JSON string
                ...
        ```
    """

    def export(self, output: "LayoutOutput") -> str:
        """Export layout output as a JSON string.

        Args:
            output: The layout output to export.

        Returns:
            JSON string representation of the layout.
        """
        ...


__all__ = [
    "ExporterProtocol",
    "JsonExporterProtocol",
    "StlExporterProtocol",
]
