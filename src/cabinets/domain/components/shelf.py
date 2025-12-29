"""Fixed shelf component implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..entities import Shelf
from ..value_objects import Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult

# Conversion constant for 32mm system
MM_TO_INCH = 0.03937008  # 1mm = 0.03937008 inches


@dataclass(frozen=True)
class DadoSpec:
    """Dado joint specification for fixed shelves.

    Represents a dado cut on a side panel that receives a shelf end.
    Dadoes provide strong, permanent shelf attachment.

    Attributes:
        panel_id: Identifier for the panel receiving the dado.
            Typically "left_side" or "right_side".
        position: Distance from panel bottom to dado center (inches).
        width: Dado width, equal to shelf material thickness (inches).
        depth: Dado depth, typically thickness / 3 (inches).
        length: Dado length, equal to shelf depth (inches).
    """

    panel_id: str  # "left_side" or "right_side"
    position: float  # Distance from panel bottom (inches)
    width: float  # Dado width (= shelf material thickness)
    depth: float  # Dado depth (= thickness / 3)
    length: float  # Dado length (= shelf depth)


@dataclass(frozen=True)
class PinHolePattern:
    """32mm system pin hole pattern specification.

    Represents a column of pin holes on a side panel for adjustable
    shelf support. The 32mm system is an industry standard where holes
    are spaced 32mm apart vertically.

    Attributes:
        panel_id: Identifier for the panel receiving the holes.
            Typically "left_side" or "right_side".
        front_inset: Distance from panel front edge to front hole column (inches).
            Default: 37mm (~1.46").
        back_inset: Distance from panel back edge to back hole column (inches).
            Default: 37mm (~1.46").
        start_height: Height of first hole from panel bottom (inches).
        end_height: Height of last hole from panel bottom (inches).
        spacing: Vertical distance between holes (inches).
            Default: 32mm (~1.26").
        hole_diameter: Diameter of holes (inches).
            Default: 5mm (~0.197").
    """

    panel_id: str
    front_inset: float
    back_inset: float
    start_height: float
    end_height: float
    spacing: float = 32.0 * MM_TO_INCH  # ~1.26 inches
    hole_diameter: float = 5.0 * MM_TO_INCH  # ~0.197 inches


def _parse_shelf_config(
    config: dict[str, Any],
    context: ComponentContext,
) -> tuple[list[float], float, float]:
    """Parse shelf configuration into positions, setback, and depth.

    Handles both explicit positions and count-based distribution.
    If positions are provided, they take precedence over count.

    Args:
        config: Component configuration dictionary with optional keys:
            - positions: list[float] - Explicit shelf heights from section bottom
            - count: int - Number of evenly-distributed shelves
            - setback: float - Front edge inset (default: 1.0")
            - depth: float - Override section depth

        context: Component context providing section dimensions.

    Returns:
        A tuple of (positions, setback, depth) where:
            - positions: List of shelf heights from section bottom
            - setback: Front edge inset in inches
            - depth: Shelf depth in inches
    """
    # Extract setback with default
    setback = config.get("setback", 1.0)

    # Calculate depth: use override or derive from context
    depth = config.get("depth") or (context.depth - setback)

    # Check for explicit positions first (takes precedence)
    if positions := config.get("positions"):
        return list(positions), setback, depth

    # Fall back to count-based distribution
    count = config.get("count", 0)

    # Handle invalid count values gracefully
    if not isinstance(count, int) or count <= 0:
        return [], setback, depth

    # Calculate evenly-spaced positions
    spacing = context.height / (count + 1)
    calculated_positions = [spacing * (i + 1) for i in range(count)]

    return calculated_positions, setback, depth


@component_registry.register("shelf.fixed")
class FixedShelfComponent:
    """Fixed shelf component - non-adjustable shelves.

    This component generates evenly-spaced fixed shelves within a section.
    The shelves are positioned vertically with equal spacing based on the
    count specified in the configuration.

    Configuration:
        count: Number of shelves to generate (0-20).
        use_pins: If True, include shelf pins in hardware list.

    Example:
        config = {"count": 3, "use_pins": True}
        result = component.generate(config, context)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate shelf configuration.

        Checks that:
        - count is a non-negative integer (when using count-based config)
        - count does not exceed 20 (when using count-based config)
        - Positions are within section height bounds (FR-05.1)
        - Shelf depth does not exceed available depth (FR-05.2)
        - Adjacent shelves have minimum 2" spacing (FR-05.3)
        - Warns if shelf span exceeds 36" for 3/4" material (FR-05.4)

        Args:
            config: Configuration with 'count' or 'positions' key.
            context: Component context with dimensions and material.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate count if using count-based configuration (for backward compatibility)
        if "positions" not in config:
            count = config.get("count", 0)
            if not isinstance(count, int) or count < 0:
                errors.append("shelf count must be non-negative integer")
            if isinstance(count, int) and count > 20:
                errors.append("shelf count exceeds maximum of 20")

        # Parse configuration to get positions, setback, and depth
        positions, setback, depth = _parse_shelf_config(config, context)

        # FR-05.1: Validate positions are within section height bounds
        for i, pos in enumerate(positions):
            if pos < 0 or pos > context.height:
                errors.append(f"Shelf {i + 1} position {pos}\" outside section height")

        # FR-05.3: Validate minimum 2" spacing between adjacent shelves
        sorted_positions = sorted(positions)
        for i in range(len(sorted_positions) - 1):
            if sorted_positions[i + 1] - sorted_positions[i] < 2.0:
                errors.append(f"Shelves {i + 1} and {i + 2} less than 2\" apart")

        # FR-05.2: Validate depth does not exceed available depth
        available_depth = context.depth - setback
        if depth > available_depth:
            errors.append(
                f"Shelf depth {depth}\" exceeds available {available_depth}\""
            )

        # FR-05.4: Advisory for wide shelves that may sag
        if context.width > 36 and context.material.thickness <= 0.75:
            warnings.append(
                f"Shelf span {context.width:.1f}\" exceeds recommended 36\" "
                "for 3/4\" material - consider center support"
            )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate shelf panels with dado specifications.

        Creates shelves at specified positions (or evenly distributed by count).
        Generates dado joint specifications for left and right side panels.
        Tracks edge banding for front edges.

        Args:
            config: Configuration with 'count' or 'positions' key.
            context: Component context with dimensions, material, and position.

        Returns:
            GenerationResult containing shelf panels, hardware (edge banding),
            and metadata with dado specifications.
        """
        positions, setback, depth = _parse_shelf_config(config, context)

        if not positions:
            return GenerationResult()

        shelves: list[Shelf] = []
        dado_specs: list[DadoSpec] = []
        thickness = context.material.thickness
        dado_depth = thickness / 3

        for pos in positions:
            # Create shelf at position - setback affects depth, not x position
            shelf_x = context.position.x
            shelf_y = context.position.y + pos
            shelves.append(
                Shelf(
                    width=context.width,
                    depth=depth,  # Use parsed depth (may be overridden)
                    material=context.material,
                    position=Position(shelf_x, shelf_y),
                )
            )

            # Create dado specs for both side panels
            dado_specs.append(
                DadoSpec(
                    panel_id="left_side",
                    position=pos,
                    width=thickness,
                    depth=dado_depth,
                    length=depth,
                )
            )
            dado_specs.append(
                DadoSpec(
                    panel_id="right_side",
                    position=pos,
                    width=thickness,
                    depth=dado_depth,
                    length=depth,
                )
            )

        # Convert shelves to panels
        panels = [shelf.to_panel() for shelf in shelves]

        # Calculate edge banding requirement
        hardware: list[HardwareItem] = []
        if config.get("edge_band_front", True):
            edge_banding_inches = context.width * len(positions)
            hardware.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{edge_banding_inches:.1f} linear inches for shelf fronts",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={"dado_specs": dado_specs},
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for fixed shelves.

        Fixed shelves require:
        - Edge banding for front edges (if edge_band_front is True, default True)
        - Optional shelf pins if use_pins is True (for semi-fixed installations)

        Note: Fixed shelves with dados typically don't need shelf pins as the
        dado joint provides structural support.

        Args:
            config: Configuration with 'count' or 'positions' key, and optional
                'use_pins' and 'edge_band_front' keys.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for edge banding and optional shelf pins.
        """
        positions, _, _ = _parse_shelf_config(config, context)

        if not positions:
            return []

        hardware: list[HardwareItem] = []

        # Edge banding for shelf fronts (default True)
        if config.get("edge_band_front", True):
            edge_banding_inches = context.width * len(positions)
            hardware.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{edge_banding_inches:.1f} linear inches",
                )
            )

        # Optional shelf pins for semi-fixed installations
        use_pins = config.get("use_pins", False)
        if use_pins:
            hardware.append(
                HardwareItem(
                    name="Shelf Pin",
                    quantity=len(positions) * 4,  # 4 pins per shelf
                    sku="SP-5MM",
                    notes="5mm brass shelf pins",
                )
            )

        return hardware


@component_registry.register("shelf.adjustable")
class AdjustableShelfComponent:
    """Adjustable shelf component with 32mm system pin holes.

    This component generates adjustable shelves that rest on pins in
    a 32mm system hole pattern. The pin holes are drilled in the side
    panels at 32mm intervals, providing multiple shelf position options.

    Unlike fixed shelves which use dado joints for permanent installation,
    adjustable shelves can be repositioned by the user without tools,
    simply by moving the shelf pins to different holes.

    Configuration:
        positions: list[float] - Explicit shelf heights (inches from bottom).
        count: int - Number of evenly-distributed shelves (alternative to positions).
        setback: float - Front edge inset from section front (default: 1.0").
        depth: float - Override shelf depth (default: context.depth - setback).
        edge_band_front: bool - Apply edge banding to front edge (default: True).
        pin_start_height: float - Height of first pin hole from bottom (default: 2.0").
        pin_end_offset: float - Distance from top to last pin hole (default: 2.0").

    Pin Hole System:
        The 32mm system uses standardized spacing between holes (32mm or ~1.26")
        with front and back hole columns inset 37mm (~1.46") from panel edges.
        This allows for compatibility with standard European cabinet hardware.

    Example:
        config = {
            "count": 4,
            "edge_band_front": True,
            "pin_start_height": 3.0,
            "pin_end_offset": 2.0,
        }
        result = component.generate(config, context)
    """

    # Class constants for 32mm system
    DEFAULT_PIN_START = 2.0  # inches from bottom
    DEFAULT_PIN_END = 2.0  # inches from top (offset)
    FRONT_INSET = 37.0 * MM_TO_INCH  # ~1.46 inches
    BACK_INSET = 37.0 * MM_TO_INCH  # ~1.46 inches

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate adjustable shelf configuration.

        Performs validation checks specific to adjustable shelves:
        - Warns if shelf positions are outside the pin hole range
        - Errors if shelf depth exceeds available section depth
        - Warns for wide spans that may cause sagging

        Args:
            config: Configuration dictionary with shelf specifications.
            context: Component context providing section dimensions and material.

        Returns:
            ValidationResult containing any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        positions, setback, depth = _parse_shelf_config(config, context)

        # Calculate pin hole range
        pin_start = config.get("pin_start_height", self.DEFAULT_PIN_START)
        pin_end = context.height - config.get("pin_end_offset", self.DEFAULT_PIN_END)

        # Check shelf positions against pin hole range
        for i, pos in enumerate(positions):
            if pos < pin_start or pos > pin_end:
                warnings.append(
                    f"Shelf {i + 1} at {pos}\" outside pin hole range "
                    f"({pin_start}\" to {pin_end}\")"
                )

        # Validate depth does not exceed available depth
        available_depth = context.depth - setback
        if depth > available_depth:
            errors.append(
                f"Shelf depth {depth}\" exceeds available {available_depth}\""
            )

        # Wide span warning for potential sagging
        if context.width > 36 and context.material.thickness <= 0.75:
            warnings.append(
                f"Shelf span {context.width:.1f}\" exceeds recommended 36\" "
                "for 3/4\" material - consider center support"
            )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate adjustable shelf panels with pin hole patterns.

        Creates shelves at specified positions (or evenly distributed by count).
        Also generates pin hole pattern specifications for left and right side
        panels that define where the 32mm system holes should be drilled.

        The generated result includes:
        - Panel entities for each shelf
        - PinHolePattern specifications in metadata["pin_hole_patterns"]
        - Hardware items for shelf pins (4 per shelf) and optional edge banding

        Args:
            config: Configuration dictionary with shelf specifications.
            context: Component context providing section dimensions, material,
                and position.

        Returns:
            GenerationResult containing shelf panels, hardware requirements,
            and pin hole pattern metadata.
        """
        positions, setback, depth = _parse_shelf_config(config, context)

        if not positions:
            return GenerationResult()

        shelves: list[Shelf] = []
        for pos in positions:
            # Create shelf at position - setback affects depth, not x position
            shelf_x = context.position.x
            shelf_y = context.position.y + pos
            shelves.append(
                Shelf(
                    width=context.width,
                    depth=depth,
                    material=context.material,
                    position=Position(shelf_x, shelf_y),
                )
            )

        # Convert shelves to panels
        panels = [shelf.to_panel() for shelf in shelves]

        # Generate pin hole pattern specs for side panels
        pin_start = config.get("pin_start_height", self.DEFAULT_PIN_START)
        pin_end = context.height - config.get("pin_end_offset", self.DEFAULT_PIN_END)

        pin_patterns = [
            PinHolePattern(
                panel_id="left_side",
                front_inset=self.FRONT_INSET,
                back_inset=self.BACK_INSET,
                start_height=pin_start,
                end_height=pin_end,
            ),
            PinHolePattern(
                panel_id="right_side",
                front_inset=self.FRONT_INSET,
                back_inset=self.BACK_INSET,
                start_height=pin_start,
                end_height=pin_end,
            ),
        ]

        # Build hardware list
        shelf_count = len(positions)
        hardware: list[HardwareItem] = [
            HardwareItem(
                name="Shelf Pin",
                quantity=shelf_count * 4,
                sku="SP-5MM-BRASS",
                notes="5mm brass shelf pins",
            ),
        ]

        if config.get("edge_band_front", True):
            edge_banding_inches = context.width * shelf_count
            hardware.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{edge_banding_inches:.1f} linear inches for shelf fronts",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={"pin_hole_patterns": pin_patterns},
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for adjustable shelves.

        Adjustable shelves require:
        - 4 shelf pins per shelf (5mm brass pins, one at each corner)
        - Edge banding for front edges (if edge_band_front is True)

        The shelf pins are standard 5mm diameter brass pins that insert
        into the 32mm system holes drilled in the side panels.

        Args:
            config: Configuration dictionary with shelf specifications.
            context: Component context providing section dimensions.

        Returns:
            List of HardwareItem objects for shelf pins and optional
            edge banding.
        """
        positions, _, _ = _parse_shelf_config(config, context)

        if not positions:
            return []

        shelf_count = len(positions)
        items: list[HardwareItem] = [
            HardwareItem(
                name="Shelf Pin",
                quantity=shelf_count * 4,
                sku="SP-5MM-BRASS",
                notes="5mm brass shelf pins",
            ),
        ]

        if config.get("edge_band_front", True):
            edge_banding_inches = context.width * shelf_count
            items.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{edge_banding_inches:.1f} linear inches",
                )
            )

        return items
