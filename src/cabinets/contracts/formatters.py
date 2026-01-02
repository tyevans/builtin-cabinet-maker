"""Formatter protocols for output generation.

This module defines protocol classes for formatters that convert domain
objects into human-readable output formats (text, tables, diagrams).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from cabinets.domain.entities import Cabinet
    from cabinets.domain.services.material_estimator import MaterialEstimate
    from cabinets.domain.value_objects import CutPiece, MaterialSpec


class FormatterProtocol(Protocol):
    """Base protocol for all formatters.

    Formatters convert data into string representations for display.
    All formatter implementations should follow this basic interface.
    """

    def format(self, data: Any) -> str:
        """Format data as a string.

        Args:
            data: The data to format.

        Returns:
            Formatted string representation.
        """
        ...


class CutListFormatterProtocol(Protocol):
    """Protocol for cut list formatting.

    Implementations format cut lists as human-readable tables,
    optionally including decorative metadata and notes.

    Example:
        ```python
        class CutListFormatter:
            def format(self, cut_list: list[CutPiece]) -> str:
                # Implementation
                ...
        ```
    """

    def format(self, cut_list: list[CutPiece]) -> str:
        """Format a cut list as a table.

        Args:
            cut_list: List of cut pieces to format.

        Returns:
            Formatted cut list table as a string.
        """
        ...


class LayoutDiagramFormatterProtocol(Protocol):
    """Protocol for layout diagram formatting.

    Implementations generate ASCII diagrams of cabinet layouts,
    showing sections, shelves, and dimensions.

    Example:
        ```python
        class LayoutDiagramFormatter:
            def format(self, cabinet: Cabinet, width: int = 60, height: int = 20) -> str:
                # Implementation
                ...
        ```
    """

    def format(self, cabinet: Cabinet, width: int = 60, height: int = 20) -> str:
        """Generate an ASCII diagram of the cabinet.

        Args:
            cabinet: The cabinet to diagram.
            width: Width of the diagram in characters.
            height: Height of the diagram in characters.

        Returns:
            ASCII diagram as a string.
        """
        ...


class MaterialReportFormatterProtocol(Protocol):
    """Protocol for material report formatting.

    Implementations format material estimates as human-readable reports,
    showing area needs, sheet counts, and waste factors.

    Example:
        ```python
        class MaterialReportFormatter:
            def format(
                self,
                estimates: dict[MaterialSpec, MaterialEstimate],
                total: MaterialEstimate,
            ) -> str:
                # Implementation
                ...
        ```
    """

    def format(
        self,
        estimates: dict[MaterialSpec, MaterialEstimate],
        total: MaterialEstimate,
    ) -> str:
        """Format material estimates as a report.

        Args:
            estimates: Material estimates grouped by material type.
            total: Total material estimate across all types.

        Returns:
            Formatted material report as a string.
        """
        ...


__all__ = [
    "CutListFormatterProtocol",
    "FormatterProtocol",
    "LayoutDiagramFormatterProtocol",
    "MaterialReportFormatterProtocol",
]
