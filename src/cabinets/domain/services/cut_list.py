"""Cut list generation service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .panel_generation import PanelGenerationService

if TYPE_CHECKING:
    from ..entities import Cabinet
    from ..value_objects import CutPiece

__all__ = ["CutListGenerator"]


class CutListGenerator:
    """Generates optimized cut lists from cabinets."""

    def __init__(self) -> None:
        """Initialize the cut list generator."""
        self._panel_service = PanelGenerationService()

    def generate(self, cabinet: Cabinet) -> list[CutPiece]:
        """Generate a cut list for the given cabinet.

        Uses the PanelGenerationService to get all panels and then
        generates a consolidated cut list with quantities.

        Args:
            cabinet: The cabinet to generate a cut list for.

        Returns:
            List of CutPiece objects with consolidated quantities.
        """
        return self._panel_service.get_cut_list(cabinet)

    def sort_by_size(self, cut_list: list[CutPiece]) -> list[CutPiece]:
        """Sort cut list by area (largest first) for efficient cutting."""
        return sorted(cut_list, key=lambda p: p.area, reverse=True)
