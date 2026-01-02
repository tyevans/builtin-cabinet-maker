"""Grain direction advisory service.

This module provides GrainAdvisor for recommending optimal grain
direction for cut pieces based on material type, panel type, and dimensions.
"""

from __future__ import annotations

from cabinets.domain.value_objects import (
    CutPiece,
    GrainDirection,
    MaterialType,
    PanelType,
)


class GrainAdvisor:
    """Service for recommending grain direction for cut pieces.

    Determines optimal grain direction based on:
    - Piece dimensions (grain parallel to longest dimension)
    - Material type (solid wood requires grain along length)
    - Panel type (visible panels prioritize aesthetics)
    """

    # Panel types that are visible and aesthetically important
    VISIBLE_PANEL_TYPES: frozenset[PanelType] = frozenset(
        {
            PanelType.LEFT_SIDE,
            PanelType.RIGHT_SIDE,
            PanelType.TOP,
            PanelType.BOTTOM,
            PanelType.DOOR,
            PanelType.DRAWER_FRONT,
            PanelType.SHELF,
            PanelType.FACE_FRAME_RAIL,
            PanelType.FACE_FRAME_STILE,
            PanelType.VALANCE,
            PanelType.ARCH_HEADER,
            PanelType.LIGHT_RAIL,
        }
    )

    def get_grain_directions(
        self,
        cut_list: list[CutPiece],
    ) -> dict[str, GrainDirection]:
        """Recommend grain direction for each cut piece.

        Determines optimal grain direction based on:
        - Piece dimensions (grain parallel to longest dimension)
        - Material type (solid wood requires grain along length)
        - Panel type (visible panels prioritize aesthetics)

        For panels with grain_direction already in cut_metadata, that value
        is used instead of calculating a recommendation.

        Args:
            cut_list: List of cut pieces to analyze.

        Returns:
            Dict mapping piece labels to recommended GrainDirection.
        """
        recommendations: dict[str, GrainDirection] = {}

        for piece in cut_list:
            # Check if grain direction already specified in metadata
            existing = self._get_existing_grain(piece)
            if existing is not None:
                recommendations[piece.label] = existing
                continue

            # Recommend based on piece characteristics
            recommendations[piece.label] = self._recommend_grain(piece)

        return recommendations

    def _get_existing_grain(self, piece: CutPiece) -> GrainDirection | None:
        """Get existing grain direction from piece metadata.

        Args:
            piece: Cut piece to check.

        Returns:
            GrainDirection if specified in metadata, None otherwise.
        """
        if not piece.cut_metadata:
            return None

        grain_str = piece.cut_metadata.get("grain_direction")
        if grain_str is None:
            return None

        try:
            return GrainDirection(grain_str)
        except ValueError:
            return None

    def _recommend_grain(self, piece: CutPiece) -> GrainDirection:
        """Calculate recommended grain direction for a piece.

        Rules applied in order:
        1. For MDF/particle board: no visible grain (NONE)
        2. For solid wood: grain must be parallel to longest dimension
        3. For plywood face panels: grain along length for aesthetics
        4. For pieces > 12" in longest dimension: grain along longest dimension
        5. Otherwise: no constraint (piece can rotate freely)

        Args:
            piece: Cut piece to analyze.

        Returns:
            Recommended GrainDirection.
        """
        # MDF and particle board have no visible grain
        if piece.material.material_type in (
            MaterialType.MDF,
            MaterialType.PARTICLE_BOARD,
        ):
            return GrainDirection.NONE

        # Solid wood always needs grain parallel to length for strength
        if piece.material.material_type == MaterialType.SOLID_WOOD:
            return self._grain_for_longest_dimension(piece)

        # Visible face panels should have grain along length for aesthetics
        if self._is_visible_panel(piece):
            # For plywood, face grain should be along length
            if piece.material.material_type == MaterialType.PLYWOOD:
                return self._grain_for_longest_dimension(piece)

        # For pieces > 12" in longest dimension, recommend grain along length
        max_dimension = max(piece.width, piece.height)
        if max_dimension > 12.0:
            return self._grain_for_longest_dimension(piece)

        # For small pieces, no grain constraint
        return GrainDirection.NONE

    def _grain_for_longest_dimension(self, piece: CutPiece) -> GrainDirection:
        """Determine grain direction for longest dimension.

        Args:
            piece: Cut piece to analyze.

        Returns:
            LENGTH if width >= height, WIDTH otherwise.
        """
        if piece.width >= piece.height:
            return GrainDirection.LENGTH
        else:
            return GrainDirection.WIDTH

    def _is_visible_panel(self, piece: CutPiece) -> bool:
        """Determine if a panel is visible and aesthetically important.

        Visible panels include:
        - Side panels (when not against wall)
        - Door panels
        - Drawer fronts
        - Face frame components
        - Shelves (front edge visible)

        Non-visible panels include:
        - Back panels
        - Drawer sides and bottoms
        - Internal dividers

        Args:
            piece: Cut piece to check.

        Returns:
            True if panel visibility matters for grain.
        """
        return piece.panel_type in self.VISIBLE_PANEL_TYPES

    def annotate_cut_list(
        self,
        cut_list: list[CutPiece],
    ) -> list[CutPiece]:
        """Create new cut list with grain directions in metadata.

        Creates copies of cut pieces with grain_direction added to
        their cut_metadata. Pieces that already have grain_direction
        specified are not modified.

        Args:
            cut_list: Original cut list.

        Returns:
            New cut list with grain directions in metadata.
        """
        directions = self.get_grain_directions(cut_list)
        annotated = []

        for piece in cut_list:
            grain = directions.get(piece.label, GrainDirection.NONE)

            # Skip if already has grain direction
            if piece.cut_metadata and "grain_direction" in piece.cut_metadata:
                annotated.append(piece)
                continue

            # Create new metadata with grain direction
            new_metadata = dict(piece.cut_metadata) if piece.cut_metadata else {}
            new_metadata["grain_direction"] = grain.value

            # Create new piece with updated metadata
            new_piece = CutPiece(
                width=piece.width,
                height=piece.height,
                quantity=piece.quantity,
                label=piece.label,
                panel_type=piece.panel_type,
                material=piece.material,
                cut_metadata=new_metadata,
            )
            annotated.append(new_piece)

        return annotated
