"""STL format exporter for cabinet layouts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from cabinets.infrastructure.exporters.base import ExporterRegistry
from cabinets.infrastructure.stl_exporter import StlExporter as StlExporterImpl
from cabinets.infrastructure.stl_exporter import StlMeshBuilder

if TYPE_CHECKING:
    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput


@ExporterRegistry.register("stl")
class StlLayoutExporter:
    """Exports cabinet layouts to STL format for 3D visualization.

    Wraps the existing StlExporter implementation to conform to the
    Exporter protocol. Supports both single cabinet (LayoutOutput) and
    room layout (RoomLayoutOutput) exports.

    Attributes:
        format_name: "stl"
        file_extension: "stl"
    """

    format_name: ClassVar[str] = "stl"
    file_extension: ClassVar[str] = "stl"

    def __init__(
        self,
        mesh_builder: StlMeshBuilder | None = None,
        door_ajar_angle: float = 45.0,
    ) -> None:
        """Initialize the STL exporter.

        Args:
            mesh_builder: Optional mesh builder for dependency injection.
            door_ajar_angle: Angle in degrees to open doors (default 45).
        """
        self._exporter = StlExporterImpl(mesh_builder=mesh_builder)
        self._door_ajar_angle = door_ajar_angle

    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export layout output to an STL file.

        Automatically detects whether the output is a single cabinet
        (LayoutOutput) or a room layout (RoomLayoutOutput) and uses
        the appropriate export method.

        Args:
            output: The layout output to export.
            path: Path where the STL file will be saved.
        """
        # Import here to avoid circular imports at module level
        from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput

        if isinstance(output, RoomLayoutOutput):
            self._exporter.export_room_layout(
                output,
                filepath=path,
                door_ajar_angle=self._door_ajar_angle,
            )
        elif isinstance(output, LayoutOutput):
            self._exporter.export_to_file(
                output.cabinet,
                filepath=path,
                door_ajar_angle=self._door_ajar_angle,
            )
        else:
            raise TypeError(
                f"Expected LayoutOutput or RoomLayoutOutput, got {type(output).__name__}"
            )

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """STL format does not support string export.

        STL files are binary format and cannot be meaningfully
        represented as strings.

        Raises:
            NotImplementedError: Always raises this exception.
        """
        raise NotImplementedError(
            "STL format is binary and does not support string export. "
            "Use export() to write to a file instead."
        )

    def format_for_console(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """STL format does not support console output.

        STL is a binary 3D format not suitable for terminal display.

        Raises:
            NotImplementedError: Always raises this exception.
        """
        raise NotImplementedError(
            "STL format is binary and does not support console output. "
            "Use export() to write to a file instead."
        )


# Re-export the underlying implementation classes for backwards compatibility
__all__ = ["StlLayoutExporter", "StlExporterImpl", "StlMeshBuilder"]
