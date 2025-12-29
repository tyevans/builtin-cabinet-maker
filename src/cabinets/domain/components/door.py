"""Hinged door component implementations.

This module provides door components for cabinet sections, including:
- Full overlay doors (door.hinged.overlay)
- Inset doors (door.hinged.inset)
- Partial overlay doors (door.hinged.partial)

All door components support single and double door configurations,
European 35mm hinge boring specifications, and automatic hinge count
calculation based on door height.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..entities import Panel
from ..value_objects import MaterialSpec, PanelType, Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult

# Conversion constant for European hardware (more precise than 0.03937008)
MM_TO_INCH = 0.0393700787  # 1mm = 0.0393700787 inches


@dataclass(frozen=True)
class HingeSpec:
    """European hinge boring specification.

    Represents the hinge cup boring requirements for a door panel.
    European hinges use a 35mm cup that is bored into the back of the door.

    Attributes:
        door_id: Identifier for the door (e.g., "door", "left_door", "right_door").
        side: Which edge of the door the hinges are on ("left" or "right").
        positions: Tuple of Y positions from door bottom for each hinge (inches).
        cup_diameter: Diameter of the hinge cup boring (default: 35mm = ~1.378").
        cup_depth: Depth of the hinge cup boring (default: 12mm = ~0.472").
        cup_inset: Distance from door edge to cup center (default: 22.5mm = ~0.886").
    """

    door_id: str
    side: str  # "left" or "right"
    positions: tuple[float, ...]
    cup_diameter: float = 35.0 * MM_TO_INCH  # ~1.378"
    cup_depth: float = 12.0 * MM_TO_INCH  # ~0.472"
    cup_inset: float = 22.5 * MM_TO_INCH  # ~0.886" from edge to center


@dataclass(frozen=True)
class HingePlateSpec:
    """Hinge mounting plate specification for cabinet side panel.

    Represents where to drill/mount hinge plates on the cabinet side panel.
    The plate positions correspond to the hinge positions on the door.

    Attributes:
        panel_id: Which side panel ("left_side" or "right_side").
        positions: Tuple of Y positions from panel bottom for each plate (inches).
        plate_inset: Distance from panel front edge to plate center (default: 0.5").
        plate_width: Width of the mounting plate (default: 0.5").
        plate_height: Height of the mounting plate (default: 2.0").
    """

    panel_id: str  # "left_side" or "right_side"
    positions: tuple[float, ...]
    plate_inset: float = 0.5  # Distance from front edge
    plate_width: float = 0.5
    plate_height: float = 2.0


@dataclass(frozen=True)
class HandlePositionSpec:
    """Handle/knob mounting position specification.

    Represents the drilling position for handle or knob mounting on a door.
    Position is relative to the door panel origin (bottom-left corner).

    Attributes:
        door_id: Identifier for the door (e.g., "door", "left_door", "right_door").
        x: Horizontal position from left edge of door (inches).
        y: Vertical position from bottom of door (inches).
        position_type: "upper" (near top) or "lower" (near bottom).
    """

    door_id: str
    x: float  # From left edge of door
    y: float  # From bottom of door
    position_type: str  # "upper" or "lower"


def _calculate_hinge_count(door_height: float) -> int:
    """Determine hinge count based on door height.

    Standard hinge count guidelines:
    - Doors under 40": 2 hinges
    - Doors 40-60": 3 hinges
    - Doors over 60": 4 hinges

    Args:
        door_height: Height of the door in inches.

    Returns:
        Number of hinges required (2, 3, or 4).
    """
    if door_height < 40:
        return 2
    elif door_height <= 60:
        return 3
    else:
        return 4


def _calculate_hinge_positions(door_height: float) -> tuple[float, ...]:
    """Calculate hinge Y positions from door bottom.

    Top and bottom hinges are positioned 3" from the door edges.
    Middle hinges (when present) are evenly distributed between them.

    Args:
        door_height: Height of the door in inches.

    Returns:
        Tuple of Y positions from door bottom for each hinge.
    """
    count = _calculate_hinge_count(door_height)
    top_offset = 3.0  # 3" from top
    bottom_offset = 3.0  # 3" from bottom

    if count == 2:
        positions = [bottom_offset, door_height - top_offset]
    elif count == 3:
        middle = door_height / 2
        positions = [bottom_offset, middle, door_height - top_offset]
    else:  # count == 4
        # Evenly distribute between top and bottom hinges
        usable_height = door_height - top_offset - bottom_offset
        quarter = usable_height / 3
        positions = [
            bottom_offset,
            bottom_offset + quarter,
            bottom_offset + 2 * quarter,
            door_height - top_offset,
        ]

    return tuple(sorted(positions))


class _HingedDoorBase:
    """Base class for hinged door components.

    Provides shared logic for all hinged door styles including:
    - Configuration parsing
    - Validation (FR-07 rules)
    - Panel and hinge spec generation
    - Hardware list generation

    Subclasses must implement _calculate_door_size() to define
    their specific sizing logic.
    """

    STYLE: str = ""  # Override in subclass

    def _parse_config(
        self, config: dict[str, Any]
    ) -> tuple[int, str, float, float, bool, str]:
        """Parse door configuration.

        Args:
            config: Component configuration dictionary.

        Returns:
            Tuple of (count, hinge_side, reveal, overlay, soft_close, handle_position).
        """
        return (
            config.get("count", 1),
            config.get("hinge_side", "left"),
            config.get("reveal", 0.125),
            config.get("overlay", 0.5),
            config.get("soft_close", True),
            config.get("handle_position", "upper"),
        )

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,
        count: int,
    ) -> tuple[float, float]:
        """Calculate single door dimensions.

        Must be overridden by subclasses to implement style-specific sizing.

        Args:
            context: Component context with section dimensions.
            reveal: Gap around door in inches.
            overlay: Overlay amount in inches (for overlay styles).
            count: Number of doors (1 or 2).

        Returns:
            Tuple of (door_width, door_height) in inches.

        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate door configuration.

        Implements FR-07 validation rules:
        - FR-07.1: Door count must be 1 or 2
        - FR-07.2: Section height > 6" minimum
        - FR-07.3: Section width > 6" for single, > 12" for double
        - FR-07.4: Reveal must be positive and < 0.5"
        - FR-07.5: Door height > 60" triggers weight warning

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []
        count, hinge_side, reveal, overlay, _, _ = self._parse_config(config)

        # FR-07.1: Validate count
        if count not in (1, 2):
            errors.append("Door count must be 1 or 2")

        # Validate hinge_side for single doors
        if count == 1 and hinge_side not in ("left", "right"):
            errors.append("hinge_side must be 'left' or 'right'")

        # FR-07.4: Validate reveal
        if reveal <= 0 or reveal >= 0.5:
            errors.append("Reveal must be between 0 and 0.5 inches")

        # FR-07.2: Validate minimum section height
        if context.height < 6:
            errors.append("Section height must be at least 6 inches")

        # FR-07.3: Validate minimum section width
        if context.width < 6:
            errors.append("Section width must be at least 6 inches")
        if count == 2 and context.width < 12:
            errors.append("Double doors require section width >= 12 inches")

        # FR-07.5: Warning for tall doors (weight concern)
        # Only calculate if basic validation passed
        if not errors:
            _, door_height = self._calculate_door_size(context, reveal, overlay, count)
            if door_height > 60:
                warnings.append(
                    f"Door height {door_height:.1f}\" exceeds 60\" - consider weight"
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate door panels with hinge and handle specifications.

        Creates Panel entities for single or double doors with:
        - Correct dimensions based on door style
        - PanelType.DOOR panel type
        - HingeSpec metadata for door hinge boring
        - HingePlateSpec metadata for side panel drilling
        - HandlePositionSpec metadata for handle mounting

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing door panels, hardware, and drilling specs.
        """
        count, hinge_side, reveal, overlay, soft_close, handle_position = (
            self._parse_config(config)
        )
        door_width, door_height = self._calculate_door_size(
            context, reveal, overlay, count
        )

        # Use door material if specified, else section material
        door_material = config.get("material") or context.material
        if isinstance(door_material, dict):
            door_material = MaterialSpec(
                thickness=door_material.get("thickness", 0.75),
            )

        panels: list[Panel] = []
        hinge_specs: list[HingeSpec] = []
        hinge_plate_specs: list[HingePlateSpec] = []
        handle_specs: list[HandlePositionSpec] = []
        hinge_positions = _calculate_hinge_positions(door_height)

        # Calculate handle Y position based on handle_position setting
        # FR-05.2: centered horizontally, 3" from top (upper) or bottom (lower)
        handle_offset = 3.0

        if count == 1:
            # Single door
            panels.append(
                Panel(
                    panel_type=PanelType.DOOR,
                    width=door_width,
                    height=door_height,
                    material=door_material,
                    position=Position(context.position.x, context.position.y),
                    metadata={"hinge_side": hinge_side},
                )
            )
            hinge_specs.append(
                HingeSpec(
                    door_id="door",
                    side=hinge_side,
                    positions=hinge_positions,
                )
            )
            # Hinge plate on the corresponding side panel
            hinge_plate_specs.append(
                HingePlateSpec(
                    panel_id=f"{hinge_side}_side",
                    positions=hinge_positions,
                )
            )
            # Handle position - centered horizontally, offset from top/bottom
            handle_x = door_width / 2
            handle_y = (
                door_height - handle_offset
                if handle_position == "upper"
                else handle_offset
            )
            handle_specs.append(
                HandlePositionSpec(
                    door_id="door",
                    x=handle_x,
                    y=handle_y,
                    position_type=handle_position,
                )
            )
        else:
            # Double doors - split width with center gap
            center_gap = reveal
            single_width = (door_width - center_gap) / 2

            # Left door (hinges on left side)
            panels.append(
                Panel(
                    panel_type=PanelType.DOOR,
                    width=single_width,
                    height=door_height,
                    material=door_material,
                    position=Position(context.position.x, context.position.y),
                    metadata={"hinge_side": "left"},
                )
            )
            hinge_specs.append(
                HingeSpec(
                    door_id="left_door",
                    side="left",
                    positions=hinge_positions,
                )
            )
            hinge_plate_specs.append(
                HingePlateSpec(
                    panel_id="left_side",
                    positions=hinge_positions,
                )
            )
            # Left door handle - near the right edge (opposite hinge side)
            handle_specs.append(
                HandlePositionSpec(
                    door_id="left_door",
                    x=single_width - handle_offset,  # Near right edge
                    y=(
                        door_height - handle_offset
                        if handle_position == "upper"
                        else handle_offset
                    ),
                    position_type=handle_position,
                )
            )

            # Right door (hinges on right side)
            panels.append(
                Panel(
                    panel_type=PanelType.DOOR,
                    width=single_width,
                    height=door_height,
                    material=door_material,
                    position=Position(
                        context.position.x + single_width + center_gap,
                        context.position.y,
                    ),
                    metadata={"hinge_side": "right"},
                )
            )
            hinge_specs.append(
                HingeSpec(
                    door_id="right_door",
                    side="right",
                    positions=hinge_positions,
                )
            )
            hinge_plate_specs.append(
                HingePlateSpec(
                    panel_id="right_side",
                    positions=hinge_positions,
                )
            )
            # Right door handle - near the left edge (opposite hinge side)
            handle_specs.append(
                HandlePositionSpec(
                    door_id="right_door",
                    x=handle_offset,  # Near left edge
                    y=(
                        door_height - handle_offset
                        if handle_position == "upper"
                        else handle_offset
                    ),
                    position_type=handle_position,
                )
            )

        # Build hardware list
        hinge_count = _calculate_hinge_count(door_height) * count
        hinge_type = "Soft-Close European Hinge" if soft_close else "European Hinge"

        hardware: list[HardwareItem] = [
            HardwareItem(
                name=hinge_type,
                quantity=hinge_count,
                sku="EURO-35MM-SC" if soft_close else "EURO-35MM",
                notes=f"35mm cup, {count} door(s)",
            ),
            HardwareItem(
                name="Handle/Knob",
                quantity=count,
                notes=f"Position: {handle_position}, 3\" from edge",
            ),
        ]

        # FR-06: Edge banding for all 4 edges
        perimeter = 2 * (door_width + door_height) * count
        hardware.append(
            HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{perimeter:.1f} linear inches (all edges)",
            )
        )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "hinge_specs": hinge_specs,
                "hinge_plate_specs": hinge_plate_specs,
                "handle_specs": handle_specs,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for door component.

        Calculates hardware needs including:
        - European hinges (soft-close or standard)
        - Handle/knob placeholder
        - Edge banding for all 4 edges

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for doors.
        """
        count, _, reveal, overlay, soft_close, handle_position = self._parse_config(
            config
        )
        door_width, door_height = self._calculate_door_size(
            context, reveal, overlay, count
        )

        hinge_count = _calculate_hinge_count(door_height) * count
        hinge_type = "Soft-Close European Hinge" if soft_close else "European Hinge"

        items: list[HardwareItem] = [
            HardwareItem(
                name=hinge_type,
                quantity=hinge_count,
                sku="EURO-35MM-SC" if soft_close else "EURO-35MM",
                notes=f"35mm cup, {count} door(s)",
            ),
            HardwareItem(
                name="Handle/Knob",
                quantity=count,
                notes=f"Position: {handle_position}, 3\" from edge",
            ),
        ]

        # Edge banding perimeter
        perimeter = 2 * (door_width + door_height) * count
        items.append(
            HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{perimeter:.1f} linear inches",
            )
        )

        return items


@component_registry.register("door.hinged.overlay")
class OverlayDoorComponent(_HingedDoorBase):
    """Full overlay hinged door component.

    Full overlay doors cover the cabinet face completely, overlapping
    the cabinet sides by the overlay amount. This is the most common
    door style for frameless (European-style) cabinets.

    Configuration:
        count: Number of doors (1 = single, 2 = double pair).
        hinge_side: "left" or "right" for single doors.
        reveal: Gap around door edges (default: 0.125" / 1/8").
        overlay: Overlap amount on each side (default: 0.5").
        soft_close: Use soft-close hinges (default: True).

    Sizing Formula:
        door_width = section_width + (2 * overlay) - reveal
        door_height = section_height + (2 * overlay) - reveal
    """

    STYLE = "overlay"

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,
        count: int,
    ) -> tuple[float, float]:
        """Calculate full overlay door dimensions.

        Full overlay doors extend beyond the section opening by the
        overlay amount on each side, minus the reveal gap.

        Args:
            context: Component context with section dimensions.
            reveal: Gap around door in inches.
            overlay: Overlay amount in inches.
            count: Number of doors (1 or 2).

        Returns:
            Tuple of (door_width, door_height) in inches.
        """
        door_height = context.height + (2 * overlay) - reveal
        door_width = context.width + (2 * overlay) - reveal
        return door_width, door_height


@component_registry.register("door.hinged.inset")
class InsetDoorComponent(_HingedDoorBase):
    """Inset hinged door component.

    Inset doors sit inside the face frame opening with a reveal gap
    around all edges. This style is common for traditional and
    Shaker-style cabinets with face frames.

    Configuration:
        count: Number of doors (1 = single, 2 = double pair).
        hinge_side: "left" or "right" for single doors.
        reveal: Gap around door edges (default: 0.125" / 1/8").
        overlay: Not used for inset doors (ignored).
        soft_close: Use soft-close hinges (default: True).

    Sizing Formula:
        door_width = opening_width - (2 * reveal)
        door_height = opening_height - (2 * reveal)
    """

    STYLE = "inset"

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,  # Not used for inset
        count: int,
    ) -> tuple[float, float]:
        """Calculate inset door dimensions.

        Inset doors fit within the opening with reveal gaps on all sides.
        The overlay parameter is ignored for inset doors.

        Args:
            context: Component context with section dimensions.
            reveal: Gap around door in inches.
            overlay: Ignored for inset doors.
            count: Number of doors (1 or 2).

        Returns:
            Tuple of (door_width, door_height) in inches.
        """
        door_height = context.height - (2 * reveal)
        door_width = context.width - (2 * reveal)
        return door_width, door_height


@component_registry.register("door.hinged.partial")
class PartialOverlayDoorComponent(_HingedDoorBase):
    """Partial overlay hinged door component.

    Partial overlay doors overlap the face frame by half the overlay
    amount, revealing some of the face frame. This style is common
    for transitional and traditional cabinets.

    Configuration:
        count: Number of doors (1 = single, 2 = double pair).
        hinge_side: "left" or "right" for single doors.
        reveal: Gap around door edges (default: 0.125" / 1/8").
        overlay: Base overlay amount (halved for partial overlay).
        soft_close: Use soft-close hinges (default: True).

    Sizing Formula:
        partial_overlay = overlay / 2
        door_width = section_width + (2 * partial_overlay) - reveal
        door_height = section_height + (2 * partial_overlay) - reveal
    """

    STYLE = "partial"

    def _calculate_door_size(
        self,
        context: ComponentContext,
        reveal: float,
        overlay: float,
        count: int,
    ) -> tuple[float, float]:
        """Calculate partial overlay door dimensions.

        Partial overlay uses half the overlay amount compared to
        full overlay, revealing more of the face frame.

        Args:
            context: Component context with section dimensions.
            reveal: Gap around door in inches.
            overlay: Base overlay amount (will be halved).
            count: Number of doors (1 or 2).

        Returns:
            Tuple of (door_width, door_height) in inches.
        """
        partial_overlay = overlay / 2
        door_height = context.height + (2 * partial_overlay) - reveal
        door_width = context.width + (2 * partial_overlay) - reveal
        return door_width, door_height
