"""Bin packing data models and algorithms for sheet material optimization.

This module provides data structures for representing sheet layouts,
piece placements, and packing results for the guillotine bin packing
algorithm.

All dataclasses are frozen (immutable) to ensure thread safety and
hashability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Sequence

from cabinets.domain.value_objects import CutPiece, GrainDirection, MaterialSpec

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SheetConfig:
    """Configuration for sheet material dimensions.

    Standard sheet sizes:
    - 4'x8' (48"x96") - most common plywood
    - 5'x5' (60"x60") - Baltic birch

    Attributes:
        width: Sheet width in inches (default 48.0 for 4' sheets).
        height: Sheet height in inches (default 96.0 for 8' sheets).
        edge_allowance: Unusable material at sheet edges in inches.
    """

    width: float = 48.0
    height: float = 96.0
    edge_allowance: float = 0.5

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Sheet width must be positive")
        if self.height <= 0:
            raise ValueError("Sheet height must be positive")
        if self.edge_allowance < 0:
            raise ValueError("Edge allowance must be non-negative")

    @property
    def usable_width(self) -> float:
        """Width available for piece placement after edge allowance."""
        return self.width - (2 * self.edge_allowance)

    @property
    def usable_height(self) -> float:
        """Height available for piece placement after edge allowance."""
        return self.height - (2 * self.edge_allowance)

    @property
    def usable_area(self) -> float:
        """Total usable area in square inches."""
        return self.usable_width * self.usable_height


@dataclass(frozen=True)
class BinPackingConfig:
    """Configuration for bin packing optimization.

    Attributes:
        enabled: Whether bin packing optimization is enabled.
        sheet_size: Sheet dimensions configuration.
        kerf: Saw blade kerf width in inches (default 1/8").
        min_offcut_size: Minimum dimension for tracking offcuts in inches.
        allow_panel_splitting: Whether to split oversized panels.
        splittable_types: Panel types that can be split (as string values).
        split_overlap: Overlap at panel joints in inches.
    """

    enabled: bool = True
    sheet_size: SheetConfig = field(default_factory=SheetConfig)
    kerf: float = 0.125
    min_offcut_size: float = 6.0
    allow_panel_splitting: bool = True
    splittable_types: tuple[str, ...] = ("back",)
    split_overlap: float = 1.0

    def __post_init__(self) -> None:
        if not 0 <= self.kerf <= 0.5:
            raise ValueError("Kerf must be between 0 and 0.5 inches")
        if self.min_offcut_size < 0:
            raise ValueError("Minimum offcut size must be non-negative")
        if self.split_overlap < 0:
            raise ValueError("Split overlap must be non-negative")


@dataclass(frozen=True)
class PlacedPiece:
    """A cut piece placed at a specific position on a sheet.

    Coordinates are relative to the usable area origin (after edge allowance).

    Attributes:
        piece: The original cut piece being placed.
        x: Horizontal position from left edge of usable area in inches.
        y: Vertical position from bottom edge of usable area in inches.
        rotated: True if piece is rotated 90 degrees from original orientation.
    """

    piece: CutPiece
    x: float
    y: float
    rotated: bool = False

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("Position coordinates must be non-negative")

    @property
    def placed_width(self) -> float:
        """Width of piece as placed (accounts for rotation)."""
        return self.piece.height if self.rotated else self.piece.width

    @property
    def placed_height(self) -> float:
        """Height of piece as placed (accounts for rotation)."""
        return self.piece.width if self.rotated else self.piece.height

    @property
    def right_edge(self) -> float:
        """X coordinate of piece right edge."""
        return self.x + self.placed_width

    @property
    def top_edge(self) -> float:
        """Y coordinate of piece top edge."""
        return self.y + self.placed_height


@dataclass(frozen=True)
class SheetLayout:
    """Layout of pieces on a single sheet.

    Attributes:
        sheet_index: Zero-based index of this sheet in the packing result.
        sheet_config: Configuration of the sheet dimensions.
        placements: Tuple of placed pieces on this sheet.
        material: Material specification for this sheet.
    """

    sheet_index: int
    sheet_config: SheetConfig
    placements: tuple[PlacedPiece, ...]
    material: MaterialSpec

    def __post_init__(self) -> None:
        if self.sheet_index < 0:
            raise ValueError("Sheet index must be non-negative")

    @property
    def used_area(self) -> float:
        """Total area used by placed pieces in square inches."""
        return sum(p.placed_width * p.placed_height for p in self.placements)

    @property
    def waste_percentage(self) -> float:
        """Percentage of usable area that is waste."""
        usable = self.sheet_config.usable_area
        if usable == 0:
            return 0.0
        return (1 - self.used_area / usable) * 100

    @property
    def piece_count(self) -> int:
        """Number of pieces placed on this sheet."""
        return len(self.placements)


@dataclass(frozen=True)
class Offcut:
    """A reusable leftover piece from sheet cutting.

    Offcuts are rectangular pieces that remain after all required
    pieces are cut and are large enough to potentially reuse.

    Attributes:
        width: Offcut width in inches.
        height: Offcut height in inches.
        material: Material specification of the offcut.
        sheet_index: Index of the sheet this offcut came from.
    """

    width: float
    height: float
    material: MaterialSpec
    sheet_index: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Offcut dimensions must be positive")
        if self.sheet_index < 0:
            raise ValueError("Sheet index must be non-negative")

    @property
    def area(self) -> float:
        """Area of the offcut in square inches."""
        return self.width * self.height


@dataclass(frozen=True)
class PackingResult:
    """Complete result of bin packing optimization.

    Attributes:
        layouts: Tuple of sheet layouts with placed pieces.
        offcuts: Tuple of reusable offcuts identified.
        total_waste_percentage: Overall waste across all sheets.
        sheets_by_material: Count of sheets needed per material.
    """

    layouts: tuple[SheetLayout, ...]
    offcuts: tuple[Offcut, ...]
    total_waste_percentage: float
    sheets_by_material: dict[MaterialSpec, int]

    def __post_init__(self) -> None:
        if self.total_waste_percentage < 0 or self.total_waste_percentage > 100:
            raise ValueError("Waste percentage must be between 0 and 100")

    @property
    def total_sheets(self) -> int:
        """Total number of sheets across all materials."""
        return sum(self.sheets_by_material.values())

    @property
    def total_pieces_placed(self) -> int:
        """Total number of pieces placed across all sheets."""
        return sum(layout.piece_count for layout in self.layouts)


@dataclass
class _Shelf:
    """Internal shelf representation for packing algorithm.

    Represents a horizontal band on a sheet where pieces are placed
    left-to-right. Each shelf's height is set by the first piece placed on it.

    Attributes:
        y: Bottom Y position of shelf (relative to usable area).
        height: Height of shelf (set by first piece placed).
        remaining_width: Width remaining for more pieces.
        pieces: List of pieces placed on this shelf.
    """

    y: float
    height: float
    remaining_width: float
    pieces: list[PlacedPiece] = field(default_factory=list)


@dataclass
class _SheetState:
    """Internal state for a sheet during packing.

    Tracks shelves and available space for placing more pieces.

    Attributes:
        index: Sheet index (0-based).
        shelves: List of shelves on this sheet.
        current_y: Y position for next new shelf.
        sheet_config: Sheet configuration.
    """

    index: int
    shelves: list[_Shelf]
    current_y: float
    sheet_config: SheetConfig

    @property
    def available_height(self) -> float:
        """Remaining height for new shelves."""
        return self.sheet_config.usable_height - self.current_y


class GuillotineBinPacker:
    """Bin packing with guillotine cut constraint using shelf algorithm.

    The shelf algorithm creates horizontal bands (shelves) across the sheet.
    Each shelf's height is determined by the first piece placed on it.
    Pieces are placed left-to-right within each shelf.

    This produces guillotine-compatible layouts where all cuts go edge-to-edge,
    suitable for panel saws and table saws.

    Attributes:
        config: Bin packing configuration (kerf, sheet size, etc.)
    """

    def __init__(self, config: BinPackingConfig) -> None:
        """Initialize the packer with configuration.

        Args:
            config: Bin packing configuration specifying sheet size,
                kerf width, and minimum offcut size.
        """
        self.config = config

    def pack(
        self,
        pieces: Sequence[CutPiece],
        material: MaterialSpec,
    ) -> PackingResult:
        """Pack pieces onto sheets, minimizing waste.

        Uses first-fit decreasing heuristic: pieces are sorted by area
        (largest first) and placed on sheets using a shelf algorithm.
        Tries ALL existing sheets before creating new ones for better fill.

        Args:
            pieces: Cut pieces to pack (may have quantity > 1).
            material: Material specification for all pieces.

        Returns:
            PackingResult with layouts, offcuts, and waste percentage.

        Raises:
            ValueError: If any piece is too large to fit on a sheet.
        """
        if not pieces:
            return PackingResult(
                layouts=(),
                offcuts=(),
                total_waste_percentage=0.0,
                sheets_by_material={},
            )

        # Expand quantities, split oversized pieces, and sort by area (largest first)
        expanded = self._expand_pieces(pieces)
        split_pieces = self._split_oversized_pieces(expanded)
        sorted_pieces = self._sort_by_area(split_pieces)

        logger.debug("Packing %d pieces onto sheets", len(split_pieces))

        # Track all sheets with their state
        sheets: list[_SheetState] = []
        kerf = self.config.kerf

        for piece in sorted_pieces:
            placed = False
            best_placement: tuple[_SheetState, _Shelf, bool, float] | None = None

            # Find best placement across all sheets (minimize height waste)
            for sheet in sheets:
                # Check existing shelves - prefer shelves where piece fits with
                # minimal height waste
                for shelf in sheet.shelves:
                    fits, rotated = self._piece_fits_on_shelf(piece, shelf, kerf)
                    if fits:
                        piece_height = piece.width if rotated else piece.height
                        piece_width = piece.height if rotated else piece.width
                        height_waste = shelf.height - piece_height
                        # Only reject if BOTH: high height waste AND shelf has lots of room
                        # This prevents small pieces from using tall shelves when better
                        # options exist, but allows filling remaining horizontal space
                        waste_ratio = height_waste / shelf.height if shelf.height > 0 else 0
                        width_usage = 1 - (shelf.remaining_width / self.config.sheet_size.usable_width)
                        # Accept if: reasonable height waste OR shelf is already well-used
                        if waste_ratio < 0.7 or width_usage > 0.3:
                            if best_placement is None or height_waste < best_placement[3]:
                                best_placement = (sheet, shelf, rotated, height_waste)
                                if height_waste == 0:
                                    break  # Perfect fit, stop searching

            # Use best existing shelf if found with acceptable waste
            if best_placement is not None:
                sheet, shelf, rotated, _ = best_placement
                self._place_on_shelf(piece, shelf, kerf, rotated)
                placed = True

            if not placed:
                # Try creating a new shelf on sheets with available height
                for sheet in sorted(
                    sheets, key=lambda s: s.available_height, reverse=True
                ):
                    fits, rotated = self._piece_fits_new_shelf(
                        piece, sheet.available_height, self.config.sheet_size.usable_width
                    )
                    if fits:
                        piece_height = piece.width if rotated else piece.height
                        new_shelf = _Shelf(
                            y=sheet.current_y,
                            height=piece_height,
                            remaining_width=self.config.sheet_size.usable_width,
                        )
                        self._place_on_shelf(piece, new_shelf, kerf, rotated)
                        sheet.shelves.append(new_shelf)
                        sheet.current_y += piece_height + kerf
                        placed = True
                        break

            if not placed:
                # Need a new sheet
                fits, rotated = self._piece_fits_new_shelf(
                    piece,
                    self.config.sheet_size.usable_height,
                    self.config.sheet_size.usable_width,
                )
                if not fits:
                    raise ValueError(
                        f"Piece '{piece.label}' ({piece.width}x{piece.height}) "
                        f"exceeds sheet usable area "
                        f"({self.config.sheet_size.usable_width}x"
                        f"{self.config.sheet_size.usable_height})"
                    )

                piece_height = piece.width if rotated else piece.height
                new_shelf = _Shelf(
                    y=0.0,
                    height=piece_height,
                    remaining_width=self.config.sheet_size.usable_width,
                )
                self._place_on_shelf(piece, new_shelf, kerf, rotated)

                new_sheet = _SheetState(
                    index=len(sheets),
                    shelves=[new_shelf],
                    current_y=piece_height + kerf,
                    sheet_config=self.config.sheet_size,
                )
                sheets.append(new_sheet)

        # Convert sheet states to layouts
        layouts: list[SheetLayout] = []
        for sheet in sheets:
            all_placements: list[PlacedPiece] = []
            for shelf in sheet.shelves:
                all_placements.extend(shelf.pieces)

            layout = SheetLayout(
                sheet_index=sheet.index,
                sheet_config=sheet.sheet_config,
                placements=tuple(all_placements),
                material=material,
            )
            layouts.append(layout)

            logger.debug(
                "Sheet %d: %d pieces, %.1f%% waste",
                sheet.index,
                len(all_placements),
                layout.waste_percentage,
            )

        # Calculate results
        offcuts = self._extract_offcuts(layouts)
        total_waste = self._calculate_total_waste(layouts)

        return PackingResult(
            layouts=tuple(layouts),
            offcuts=tuple(offcuts),
            total_waste_percentage=total_waste,
            sheets_by_material={material: len(layouts)},
        )

    def _expand_pieces(self, pieces: Sequence[CutPiece]) -> list[CutPiece]:
        """Expand pieces with quantity > 1 into individual pieces.

        Each piece with quantity N becomes N separate pieces with quantity 1.
        This allows individual placement of each physical piece.

        Args:
            pieces: Sequence of cut pieces, possibly with quantity > 1.

        Returns:
            List of individual cut pieces, each with quantity 1.
        """
        expanded: list[CutPiece] = []
        for piece in pieces:
            for i in range(piece.quantity):
                # Create individual piece with quantity 1
                # Append index to label if quantity > 1
                label = piece.label if piece.quantity == 1 else f"{piece.label} #{i + 1}"
                individual = CutPiece(
                    width=piece.width,
                    height=piece.height,
                    quantity=1,
                    label=label,
                    panel_type=piece.panel_type,
                    material=piece.material,
                    cut_metadata=piece.cut_metadata,
                )
                expanded.append(individual)
        return expanded

    def _sort_by_area(self, pieces: list[CutPiece]) -> list[CutPiece]:
        """Sort pieces by area (largest first) for first-fit decreasing.

        Secondary sort by height (tallest first) to improve shelf utilization.

        Args:
            pieces: List of cut pieces to sort.

        Returns:
            New list sorted by area descending, then by max dimension descending.
        """
        return sorted(
            pieces,
            key=lambda p: (p.width * p.height, max(p.width, p.height)),
            reverse=True,
        )

    def _is_splittable(self, piece: CutPiece) -> bool:
        """Check if a piece's panel type allows splitting.

        Args:
            piece: The cut piece to check.

        Returns:
            True if the piece can be split when oversized.
        """
        if not self.config.allow_panel_splitting:
            return False
        return piece.panel_type.value in self.config.splittable_types

    def _piece_needs_splitting(self, piece: CutPiece) -> bool:
        """Check if a piece is too large for the sheet and needs splitting.

        Args:
            piece: The cut piece to check.

        Returns:
            True if the piece exceeds sheet usable dimensions.
        """
        usable_w = self.config.sheet_size.usable_width
        usable_h = self.config.sheet_size.usable_height

        # Check both orientations (with and without rotation)
        fits_normal = piece.width <= usable_w and piece.height <= usable_h
        fits_rotated = piece.height <= usable_w and piece.width <= usable_h

        return not (fits_normal or fits_rotated)

    def _split_oversized_piece(self, piece: CutPiece) -> list[CutPiece]:
        """Split an oversized piece into multiple smaller pieces.

        Splits along the dimension that exceeds the sheet size, accounting
        for kerf and overlap at joints.

        Args:
            piece: The oversized cut piece to split.

        Returns:
            List of smaller pieces that fit on the sheet.
        """
        usable_w = self.config.sheet_size.usable_width
        usable_h = self.config.sheet_size.usable_height
        kerf = self.config.kerf
        overlap = self.config.split_overlap

        # Determine which dimension(s) need splitting
        width_exceeds = piece.width > usable_w and piece.height > usable_h
        # If both dimensions exceed, we need to handle that case
        if width_exceeds:
            # Both dimensions exceed - this is complex, split width first
            logger.warning(
                "Piece '%s' exceeds both sheet dimensions, splitting width first",
                piece.label,
            )

        # Determine primary split direction
        # Prefer splitting the dimension that exceeds the sheet
        if piece.width > usable_w:
            split_width = True
            split_dim = piece.width
            max_dim = usable_w
        elif piece.height > usable_h:
            split_width = False
            split_dim = piece.height
            max_dim = usable_h
        else:
            # Neither dimension exceeds - shouldn't happen if called correctly
            return [piece]

        # Calculate number of splits needed
        # Each piece after the first needs kerf + overlap added
        # Effective max per piece = max_dim - overlap (except first piece)
        effective_max = max_dim - overlap
        if effective_max <= 0:
            # Overlap too large for sheet - fall back to max dim
            effective_max = max_dim
            overlap = 0

        # Number of pieces needed
        # First piece is max_dim, subsequent pieces cover (split_dim - max_dim)
        remaining = split_dim - max_dim
        num_splits = 1
        while remaining > 0:
            num_splits += 1
            remaining -= (effective_max - kerf)

        # Calculate piece sizes with overlap
        # Each piece overlaps with the next by 'overlap' amount
        piece_sizes: list[float] = []
        total_coverage = 0.0

        for i in range(num_splits):
            if i == 0:
                # First piece: up to max_dim
                size = min(max_dim, split_dim - total_coverage)
            else:
                # Subsequent pieces: need to cover remaining with overlap
                remaining_to_cover = split_dim - total_coverage + overlap
                size = min(max_dim, remaining_to_cover)

            piece_sizes.append(size)
            # Each piece covers size - overlap (except last which covers size)
            if i < num_splits - 1:
                total_coverage += size - overlap
            else:
                total_coverage += size

        # Create split pieces
        split_pieces: list[CutPiece] = []
        for i, size in enumerate(piece_sizes):
            # Create label indicating split
            if num_splits == 1:
                label = piece.label
            else:
                label = f"{piece.label} ({i + 1} of {num_splits})"

            # Create new piece with split dimension
            if split_width:
                new_piece = CutPiece(
                    width=size,
                    height=piece.height,
                    quantity=1,
                    label=label,
                    panel_type=piece.panel_type,
                    material=piece.material,
                    cut_metadata=piece.cut_metadata,
                )
            else:
                new_piece = CutPiece(
                    width=piece.width,
                    height=size,
                    quantity=1,
                    label=label,
                    panel_type=piece.panel_type,
                    material=piece.material,
                    cut_metadata=piece.cut_metadata,
                )

            # Check if this piece still needs splitting in the other dimension
            if self._piece_needs_splitting(new_piece) and self._is_splittable(new_piece):
                # Recursively split
                split_pieces.extend(self._split_oversized_piece(new_piece))
            else:
                split_pieces.append(new_piece)

        logger.info(
            "Split '%s' (%sx%s) into %d pieces",
            piece.label,
            piece.width,
            piece.height,
            len(split_pieces),
        )

        return split_pieces

    def _split_oversized_pieces(self, pieces: list[CutPiece]) -> list[CutPiece]:
        """Process all pieces, splitting any that are oversized and splittable.

        Args:
            pieces: List of cut pieces to process.

        Returns:
            New list with oversized splittable pieces replaced by splits.
        """
        result: list[CutPiece] = []

        for piece in pieces:
            if self._piece_needs_splitting(piece):
                if self._is_splittable(piece):
                    result.extend(self._split_oversized_piece(piece))
                else:
                    # Not splittable, pass through (will fail during packing)
                    result.append(piece)
            else:
                result.append(piece)

        return result

    def _get_grain_direction(self, piece: CutPiece) -> GrainDirection:
        """Extract grain direction from piece cut_metadata.

        Args:
            piece: The cut piece to check.

        Returns:
            GrainDirection enum value, defaulting to NONE.
        """
        if piece.cut_metadata is None:
            return GrainDirection.NONE

        grain_str = piece.cut_metadata.get("grain_direction", "none")
        try:
            return GrainDirection(grain_str)
        except ValueError:
            # Invalid grain value, treat as no constraint
            logger.debug(
                "Invalid grain direction '%s' for piece '%s', treating as NONE",
                grain_str,
                piece.label,
            )
            return GrainDirection.NONE

    def _can_rotate(self, piece: CutPiece) -> bool:
        """Check if piece can be rotated based on grain constraints.

        A piece can rotate if:
        - It has no grain constraint (GrainDirection.NONE)
        - It's square (rotation doesn't change orientation)

        Args:
            piece: The cut piece to check.

        Returns:
            True if the piece can be rotated, False otherwise.
        """
        grain = self._get_grain_direction(piece)

        # No grain constraint - can rotate freely
        if grain == GrainDirection.NONE:
            return True

        # Square pieces can "rotate" but it doesn't change anything
        if piece.width == piece.height:
            return True

        # Grain-constrained non-square pieces cannot rotate
        logger.debug(
            "Piece '%s' cannot rotate due to grain constraint: %s",
            piece.label,
            grain.value,
        )
        return False

    def _check_grain_valid(self, piece: CutPiece, rotated: bool) -> bool:
        """Check if a piece placement satisfies grain constraints.

        Sheet grain runs vertically (parallel to height, the 96" dimension).
        - LENGTH grain: piece length (longest dimension) should align with sheet grain
        - WIDTH grain: piece width (shortest dimension) should align with sheet grain

        When placing a piece:
        - Without rotation: piece height aligns with sheet height (grain)
        - With rotation: piece width aligns with sheet height (grain)

        Args:
            piece: The cut piece to check.
            rotated: Whether the piece would be rotated 90 degrees.

        Returns:
            True if placement satisfies grain constraints.
        """
        grain = self._get_grain_direction(piece)

        if grain == GrainDirection.NONE:
            return True

        # Determine which dimension aligns with sheet grain (vertical)
        # Without rotation: piece height aligns with sheet height (grain)
        # With rotation: piece width aligns with sheet height (grain)

        if grain == GrainDirection.LENGTH:
            # Length (longest dimension) must align with grain
            longest = max(piece.width, piece.height)
            if not rotated:
                # Height aligns with grain
                return piece.height == longest
            else:
                # Width aligns with grain
                return piece.width == longest

        elif grain == GrainDirection.WIDTH:
            # Width (shortest dimension) must align with grain
            shortest = min(piece.width, piece.height)
            if not rotated:
                # Height aligns with grain
                return piece.height == shortest
            else:
                # Width aligns with grain
                return piece.width == shortest

        return True

    def _pack_single_sheet(
        self,
        pieces: list[CutPiece],
        sheet_config: SheetConfig,
    ) -> tuple[list[PlacedPiece], list[CutPiece]]:
        """Pack as many pieces as possible onto a single sheet.

        Uses shelf algorithm: pieces are placed on horizontal shelves,
        left to right. New shelves are created below existing ones.
        Rotation is attempted when pieces don't fit in original orientation.

        Args:
            pieces: List of cut pieces to place (sorted by area descending).
            sheet_config: Configuration of the sheet dimensions.

        Returns:
            Tuple of (placed pieces, remaining pieces that didn't fit).
        """
        usable_width = sheet_config.usable_width
        usable_height = sheet_config.usable_height
        kerf = self.config.kerf

        shelves: list[_Shelf] = []
        placed: list[PlacedPiece] = []
        remaining: list[CutPiece] = []
        current_y = 0.0  # Bottom of available space for new shelves

        for piece in pieces:
            placement = None

            # Try to fit on existing shelf (with rotation check)
            for shelf in shelves:
                fits, rotated = self._piece_fits_on_shelf(piece, shelf, kerf)
                if fits:
                    placement = self._place_on_shelf(piece, shelf, kerf, rotated)
                    placed.append(placement)
                    break

            if placement is None:
                # Try to create new shelf (with rotation check)
                available_height = usable_height - current_y
                fits, rotated = self._piece_fits_new_shelf(
                    piece, available_height, usable_width
                )

                if fits:
                    # Determine shelf height based on piece orientation
                    piece_height = piece.width if rotated else piece.height

                    # Create new shelf
                    shelf = _Shelf(
                        y=current_y,
                        height=piece_height,
                        remaining_width=usable_width,
                    )
                    shelves.append(shelf)

                    placement = self._place_on_shelf(piece, shelf, kerf, rotated)
                    placed.append(placement)

                    # Move Y position down for next potential shelf
                    current_y += piece_height + kerf

            if placement is None:
                # Piece doesn't fit on this sheet
                remaining.append(piece)

        return placed, remaining

    def _piece_fits_on_shelf(
        self,
        piece: CutPiece,
        shelf: _Shelf,
        kerf: float,
    ) -> tuple[bool, bool]:
        """Check if piece fits on existing shelf, considering rotation.

        Args:
            piece: The cut piece to place.
            shelf: The shelf to check.
            kerf: Saw kerf width.

        Returns:
            Tuple of (fits, rotated):
            - fits: True if piece fits in some orientation
            - rotated: True if piece must be rotated to fit
        """
        # Try original orientation first
        width_needed = piece.width + (kerf if shelf.pieces else 0)
        original_fits = (
            piece.height <= shelf.height
            and width_needed <= shelf.remaining_width
            and self._check_grain_valid(piece, rotated=False)
        )

        if original_fits:
            return (True, False)

        # Try rotated orientation if allowed
        if self._can_rotate(piece):
            rotated_width_needed = piece.height + (kerf if shelf.pieces else 0)
            rotated_fits = (
                piece.width <= shelf.height  # Rotated: width becomes height
                and rotated_width_needed <= shelf.remaining_width
                and self._check_grain_valid(piece, rotated=True)
            )

            if rotated_fits:
                logger.debug(
                    "Piece '%s' fits on shelf when rotated",
                    piece.label,
                )
                return (True, True)

        return (False, False)

    def _piece_fits_new_shelf(
        self,
        piece: CutPiece,
        available_height: float,
        usable_width: float,
    ) -> tuple[bool, bool]:
        """Check if piece can start a new shelf, considering rotation.

        Args:
            piece: The cut piece to place.
            available_height: Remaining height on sheet for new shelves.
            usable_width: Usable width of the sheet.

        Returns:
            Tuple of (fits, rotated):
            - fits: True if piece fits in some orientation
            - rotated: True if piece must be rotated to fit
        """
        # Try original orientation first
        original_fits = (
            piece.height <= available_height
            and piece.width <= usable_width
            and self._check_grain_valid(piece, rotated=False)
        )

        if original_fits:
            return (True, False)

        # Try rotated orientation if allowed
        if self._can_rotate(piece):
            rotated_fits = (
                piece.width <= available_height  # Rotated: width becomes height
                and piece.height <= usable_width  # Rotated: height becomes width
                and self._check_grain_valid(piece, rotated=True)
            )

            if rotated_fits:
                logger.debug(
                    "Piece '%s' fits on new shelf when rotated",
                    piece.label,
                )
                return (True, True)

        return (False, False)

    def _place_on_shelf(
        self,
        piece: CutPiece,
        shelf: _Shelf,
        kerf: float,
        rotated: bool = False,
    ) -> PlacedPiece:
        """Place a piece on a shelf and update shelf state.

        Args:
            piece: The cut piece to place.
            shelf: The shelf to place the piece on.
            kerf: Saw blade kerf width.
            rotated: Whether the piece is rotated 90 degrees.

        Returns:
            The placed piece with position information.
        """
        # Calculate X position (accounting for kerf after previous pieces)
        if shelf.pieces:
            last_piece = shelf.pieces[-1]
            x = last_piece.right_edge + kerf
        else:
            x = 0.0

        placement = PlacedPiece(
            piece=piece,
            x=x,
            y=shelf.y,
            rotated=rotated,
        )

        # Update shelf state (use placed dimensions which account for rotation)
        shelf.pieces.append(placement)
        placed_width = placement.placed_width
        width_used = placed_width + (kerf if len(shelf.pieces) > 1 else 0)
        shelf.remaining_width -= width_used

        if rotated:
            logger.debug(
                "Piece '%s' placed rotated at (%s, %s), "
                "placed dimensions: %sx%s (original: %sx%s)",
                piece.label,
                x,
                shelf.y,
                placement.placed_width,
                placement.placed_height,
                piece.width,
                piece.height,
            )

        return placement

    def _extract_offcuts(
        self,
        layouts: list[SheetLayout],
    ) -> list[Offcut]:
        """Identify reusable offcuts from sheet layouts.

        Offcuts are rectangular areas that remain after all pieces are cut.
        Only offcuts larger than min_offcut_size are tracked.

        Args:
            layouts: List of sheet layouts with placed pieces.

        Returns:
            List of identified offcuts meeting minimum size requirements.
        """
        offcuts: list[Offcut] = []
        min_size = self.config.min_offcut_size

        for layout in layouts:
            sheet = layout.sheet_config

            if not layout.placements:
                continue

            # Find rightmost piece to calculate horizontal waste
            max_x = max(p.right_edge for p in layout.placements)
            horizontal_waste_width = sheet.usable_width - max_x

            # Find topmost piece to calculate vertical waste
            max_y = max(p.top_edge for p in layout.placements)

            # Right-side strip offcut (horizontal waste)
            if horizontal_waste_width >= min_size and max_y >= min_size:
                offcuts.append(
                    Offcut(
                        width=horizontal_waste_width,
                        height=max_y,
                        material=layout.material,
                        sheet_index=layout.sheet_index,
                    )
                )

            # Bottom strip offcut (vertical waste below last shelf)
            vertical_waste_height = sheet.usable_height - max_y
            if vertical_waste_height >= min_size and sheet.usable_width >= min_size:
                offcuts.append(
                    Offcut(
                        width=sheet.usable_width,
                        height=vertical_waste_height,
                        material=layout.material,
                        sheet_index=layout.sheet_index,
                    )
                )

        return offcuts

    def _calculate_total_waste(
        self,
        layouts: list[SheetLayout],
    ) -> float:
        """Calculate total waste percentage across all sheets.

        Args:
            layouts: List of sheet layouts with placed pieces.

        Returns:
            Waste percentage (0-100) across all sheets.
        """
        if not layouts:
            return 0.0

        total_usable = sum(layout.sheet_config.usable_area for layout in layouts)
        total_used = sum(layout.used_area for layout in layouts)

        if total_usable == 0:
            return 0.0

        return (1 - total_used / total_usable) * 100


class BinPackingService:
    """Coordinates bin packing optimization across material groups.

    Cabinet projects typically use multiple materials (e.g., 3/4" plywood
    for panels, 1/2" plywood for backs). This service groups pieces by
    material and runs separate optimization for each group, then combines
    the results.

    Each material group can have its own sheet configuration via
    material overrides, allowing different sheet sizes for different materials.

    Attributes:
        config: Bin packing configuration.
        packer: GuillotineBinPacker instance for actual packing.
    """

    def __init__(self, config: BinPackingConfig) -> None:
        """Initialize service with configuration.

        Args:
            config: Bin packing configuration with sheet sizes and options.
        """
        self.config = config
        self.packer = GuillotineBinPacker(config)

    def optimize_cut_list(
        self,
        pieces: Sequence[CutPiece],
    ) -> PackingResult:
        """Optimize cut list, grouping by material.

        Groups pieces by MaterialSpec, runs bin packing for each group,
        and combines results into a single PackingResult.

        Args:
            pieces: All cut pieces from cabinet generation.

        Returns:
            PackingResult with layouts organized by material.

        Raises:
            ValueError: If any piece is too large for its sheet.
        """
        if not self.config.enabled:
            # Return empty result if bin packing is disabled
            return PackingResult(
                layouts=(),
                offcuts=(),
                total_waste_percentage=0.0,
                sheets_by_material={},
            )

        if not pieces:
            return PackingResult(
                layouts=(),
                offcuts=(),
                total_waste_percentage=0.0,
                sheets_by_material={},
            )

        # Group pieces by material
        groups = self._group_by_material(pieces)

        logger.info(
            "Optimizing %d pieces across %d material groups",
            len(pieces),
            len(groups),
        )

        # Pack each material group
        all_layouts: list[SheetLayout] = []
        all_offcuts: list[Offcut] = []
        sheets_by_material: dict[MaterialSpec, int] = {}

        for material, group_pieces in groups.items():
            # Pack this material group
            result = self.packer.pack(group_pieces, material)

            logger.debug(
                "Material %.3f\" %s: %d pieces -> %d sheets",
                material.thickness,
                material.material_type.value,
                len(group_pieces),
                len(result.layouts),
            )

            # Accumulate results
            all_layouts.extend(result.layouts)
            all_offcuts.extend(result.offcuts)
            sheets_by_material[material] = len(result.layouts)

        # Calculate combined statistics
        total_waste = self._calculate_combined_waste(all_layouts)

        return PackingResult(
            layouts=tuple(all_layouts),
            offcuts=tuple(all_offcuts),
            total_waste_percentage=total_waste,
            sheets_by_material=sheets_by_material,
        )

    def _group_by_material(
        self,
        pieces: Sequence[CutPiece],
    ) -> dict[MaterialSpec, list[CutPiece]]:
        """Group pieces by their MaterialSpec.

        MaterialSpec is frozen/hashable, so it can be used as a dict key.
        Pieces with the same material type and thickness are grouped together.

        Args:
            pieces: Cut pieces to group.

        Returns:
            Dictionary mapping MaterialSpec to list of pieces.
        """
        groups: dict[MaterialSpec, list[CutPiece]] = {}

        for piece in pieces:
            material = piece.material
            if material not in groups:
                groups[material] = []
            groups[material].append(piece)

        return groups

    def _calculate_combined_waste(
        self,
        layouts: list[SheetLayout],
    ) -> float:
        """Calculate overall waste percentage across all layouts.

        Waste is calculated as: (total usable area - total used area) / total usable area

        Args:
            layouts: All sheet layouts from all material groups.

        Returns:
            Combined waste percentage (0-100).
        """
        if not layouts:
            return 0.0

        total_usable = sum(
            layout.sheet_config.usable_area
            for layout in layouts
        )
        total_used = sum(layout.used_area for layout in layouts)

        if total_usable == 0:
            return 0.0

        return (1 - total_used / total_usable) * 100
