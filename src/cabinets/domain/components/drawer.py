"""Drawer component implementation for FRD-08.

Phase 1: Core Drawer Infrastructure
Phase 2: Standard Drawer Component

This module provides the foundational data structures for drawer components:
- Slide clearances for different mounting types
- Valid slide lengths for standard hardware
- DrawerBoxSpec for drawer box dimensions
- SlideMountSpec for slide mounting specifications
- Helper for automatic slide length selection
- StandardDrawerComponent for generating drawer panels and hardware
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..entities import Panel
from ..value_objects import MaterialSpec, PanelType, Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult

# Clearance per side required for different slide mounting types (inches)
# Side mount requires the most clearance (1/2" per side)
# Undermount requires minimal clearance (3/16" per side)
# Center mount requires no side clearance
SLIDE_CLEARANCES: dict[str, float] = {
    "side_mount": 0.5,
    "undermount": 0.1875,
    "center_mount": 0.0,
}

# Valid slide lengths in inches (industry standard increments)
VALID_SLIDE_LENGTHS: list[int] = [12, 14, 16, 18, 20, 22, 24]


@dataclass(frozen=True)
class DrawerBoxSpec:
    """Specification for drawer box dimensions.

    Represents the physical dimensions and material thicknesses for a
    drawer box, including the visible drawer front. All measurements
    are in inches.

    The drawer box consists of:
    - Two sides (left and right)
    - Front and back pieces
    - Bottom panel (typically 1/4" plywood or MDF)
    - Visible drawer front (attached to the box front)

    The dado_depth specifies how deep the bottom panel sits in the
    dado cut on the sides, front, and back pieces.

    Attributes:
        box_width: Interior width of the drawer box (inches).
        box_height: Height of the drawer box sides (inches).
        box_depth: Front-to-back depth of the drawer box (inches).
        front_width: Width of the visible drawer front (inches).
        front_height: Height of the visible drawer front (inches).
        bottom_thickness: Thickness of the bottom panel (inches).
            Default: 0.25" (1/4").
        side_thickness: Thickness of the side, front, and back pieces (inches).
            Default: 0.5" (1/2").
        dado_depth: Depth of the dado for the bottom panel (inches).
            Default: 0.25" (1/4").
    """

    box_width: float
    box_height: float
    box_depth: float
    front_width: float
    front_height: float
    bottom_thickness: float = 0.25
    side_thickness: float = 0.5
    dado_depth: float = 0.25


@dataclass(frozen=True)
class SlideMountSpec:
    """Specification for drawer slide mounting.

    Represents the mounting information for a single drawer slide,
    including its position on the cabinet side panel and the locations
    of mounting holes.

    Drawer slides are mounted in pairs (left and right), so a complete
    drawer installation will have two SlideMountSpec instances.

    Attributes:
        panel_id: Identifier for the cabinet panel receiving the slide.
            Typically "left_side" or "right_side".
        slide_type: Type of slide mounting.
            One of: "side_mount", "undermount", "center_mount".
        position_y: Vertical position from section bottom to slide
            centerline (inches).
        slide_length: Length of the drawer slide (inches).
            Must be one of VALID_SLIDE_LENGTHS.
        mounting_holes: Tuple of X positions (from front of cabinet)
            where mounting holes/screws should be placed (inches).
    """

    panel_id: str
    slide_type: str
    position_y: float
    slide_length: int
    mounting_holes: tuple[float, ...]


def _auto_select_slide_length(depth: float) -> int:
    """Select appropriate slide length based on cabinet depth.

    Chooses the largest slide that will fit within the cabinet depth
    while maintaining a 2" clearance at the back. This ensures the
    slide doesn't extend past the cabinet back when fully extended.

    Selection table:
        | Cabinet Depth | Selected Length |
        |---------------|-----------------|
        | < 14"         | 12"             |
        | 14-16"        | 14"             |
        | 16-18"        | 16"             |
        | 18-20"        | 18"             |
        | 20-22"        | 20"             |
        | 22-24"        | 22"             |
        | >= 24"        | 24"             |

    Args:
        depth: Cabinet depth in inches.

    Returns:
        The selected slide length in inches, guaranteed to be one of
        the values in VALID_SLIDE_LENGTHS.
    """
    for length in VALID_SLIDE_LENGTHS:
        if depth < length + 2:
            return length
    return 24


class _DrawerBase:
    """Base class for drawer components with shared validation and generation logic.

    Provides common validation rules and generation logic for all drawer types.
    Subclasses can override or extend this behavior as needed.

    Validation rules:
        - V-01: slide_length > section_depth - 1" -> ERROR
        - V-02: front_height < 3" -> ERROR
        - V-03: front_height > section_height -> ERROR
        - V-04: box_width <= 0 -> ERROR

    Box dimension formulas:
        - box_width = section_width - (2 * side_clearance)
        - box_height = front_height - 0.125" (reveal) - 0.5" (slide clearance)
        - box_depth = slide_length - 1" (rear clearance)
        - Bottom: 1/4" plywood inset into 1/4" dado
        - Sides: 1/2" plywood
    """

    MIN_FRONT_HEIGHT = 3.0

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate drawer configuration.

        Checks that:
        - Slide type is valid (side_mount, undermount, center_mount)
        - Slide length is valid (12, 14, 16, 18, 20, 22, 24 inches)
        - V-01: Slide length does not exceed section depth minus 1" rear clearance
        - V-02: Front height is at least 3" minimum
        - V-03: Front height does not exceed section height
        - V-04: Calculated box width is positive (section not too narrow)
        - V-05: Total drawer height (count * front_height) fits in section

        Args:
            config: Drawer configuration dictionary with optional keys:
                - count: Number of stacked drawers (default: 1)
                - front_height: Height of drawer front. If not specified,
                  auto-calculates to fill section: section_height / count
                - slide_type: Type of slide mounting (default: "side_mount")
                - slide_length: Slide length or "auto" (default: "auto")

            context: Component context with section dimensions and material.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        count = config.get("count", 1)
        # Auto-calculate front_height to fill section if not specified
        front_height = config.get("front_height")
        if front_height is None:
            front_height = context.height / count
        slide_type = config.get("slide_type", "side_mount")
        slide_length_raw = config.get("slide_length", "auto")

        # Resolve auto slide length to a concrete int
        slide_length: int = (
            _auto_select_slide_length(context.depth)
            if slide_length_raw == "auto"
            else int(slide_length_raw)
            if isinstance(slide_length_raw, str)
            else slide_length_raw
        )

        # Validate slide_type
        if slide_type not in SLIDE_CLEARANCES:
            valid_types = list(SLIDE_CLEARANCES.keys())
            errors.append(
                f"Invalid slide_type '{slide_type}'. Must be one of: {valid_types}"
            )

        # Validate slide_length
        if slide_length not in VALID_SLIDE_LENGTHS:
            errors.append(
                f"Invalid slide_length {slide_length}. "
                f"Must be one of: {VALID_SLIDE_LENGTHS}"
            )

        # V-01: Check slide length vs depth
        if slide_length > context.depth - 1:
            errors.append(
                f'Slide length ({slide_length}") exceeds section depth '
                f'({context.depth}") minus 1" rear clearance'
            )

        # V-02: Check minimum front height
        if front_height < self.MIN_FRONT_HEIGHT:
            errors.append(
                f'Front height ({front_height}") below minimum '
                f'({self.MIN_FRONT_HEIGHT}")'
            )

        # V-03: Check front height vs section height
        if front_height > context.height:
            errors.append(
                f'Front height ({front_height}") exceeds section height '
                f'({context.height}")'
            )

        # V-05: Check total drawer height fits in section
        total_height = count * front_height
        if total_height > context.height:
            errors.append(
                f'Total drawer height ({count} x {front_height}" = {total_height}") '
                f'exceeds section height ({context.height}")'
            )

        # V-04: Check box width is positive
        if slide_type in SLIDE_CLEARANCES:
            clearance = SLIDE_CLEARANCES[slide_type]
            box_width = context.width - (2 * clearance)
            if box_width <= 0:
                errors.append(
                    f'Section too narrow ({context.width}") for {slide_type} '
                    f'slides (need >{2 * clearance}")'
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate drawer panels and hardware.

        Creates all drawer box panels including:
        - Drawer front (decorative front panel)
        - Drawer box front (structural, behind decorative front)
        - Left and right drawer sides
        - Drawer bottom (1/4" panel inset in dado)

        Also generates hardware requirements:
        - Drawer slides (quantity based on slide type)
        - Mounting screws
        - Handle/pull
        - Edge banding for drawer front

        Args:
            config: Drawer configuration dictionary with optional keys:
                - count: Number of stacked drawers (default: 1)
                - front_height: Height of drawer front. If not specified,
                  auto-calculates to fill section: section_height / count
                - slide_type: Type of slide mounting (default: "side_mount")
                - slide_length: Slide length or "auto" (default: "auto")
                - soft_close: Whether slides have soft-close (default: True)
                - front_style: Front style "overlay" or "inset" (default: "overlay")

            context: Component context with section dimensions, material, and position.

        Returns:
            GenerationResult containing drawer panels, hardware requirements,
            and metadata with drawer specifications.
        """
        # Parse config
        count = config.get("count", 1)
        # Auto-calculate front_height to fill section if not specified
        front_height = config.get("front_height")
        if front_height is None:
            front_height = context.height / count
        slide_type = config.get("slide_type", "side_mount")
        slide_length_raw = config.get("slide_length", "auto")
        soft_close = config.get("soft_close", True)
        front_style = config.get("front_style", "overlay")

        # Resolve auto slide length to a concrete int
        slide_length: int = (
            _auto_select_slide_length(context.depth)
            if slide_length_raw == "auto"
            else int(slide_length_raw)
            if isinstance(slide_length_raw, str)
            else slide_length_raw
        )

        # Calculate box dimensions
        side_clearance = SLIDE_CLEARANCES[slide_type]
        box_width = context.width - (2 * side_clearance)
        box_height = front_height - 0.125 - 0.5  # reveal + slide clearance
        box_depth = slide_length - 1  # rear clearance

        drawer_spec = DrawerBoxSpec(
            box_width=box_width,
            box_height=box_height,
            box_depth=box_depth,
            front_width=context.width,  # overlay covers full section width
            front_height=front_height,
        )

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Pre-calculate box front width and bottom dimensions
        box_front_width = drawer_spec.box_width - (2 * drawer_spec.side_thickness)
        bottom_width = (
            drawer_spec.box_width
            - (2 * drawer_spec.side_thickness)
            + (2 * drawer_spec.dado_depth)
        )
        bottom_depth = (
            drawer_spec.box_depth - drawer_spec.side_thickness + drawer_spec.dado_depth
        )

        # Generate panels for each drawer in the stack
        for drawer_index in range(count):
            # Calculate vertical position for this drawer
            # Each drawer is stacked above the previous one
            position_y = context.position.y + (drawer_index * front_height)

            # Common metadata for all panels in this drawer
            drawer_metadata = {
                "drawer_index": drawer_index,
                "drawer_count": count,
            }

            # Create drawer front panel (decorative front)
            panels.append(
                Panel(
                    panel_type=PanelType.DRAWER_FRONT,
                    width=drawer_spec.front_width,
                    height=drawer_spec.front_height,
                    material=context.material,
                    position=Position(x=context.position.x, y=position_y),
                    metadata=drawer_metadata.copy(),
                )
            )

            # Create drawer box front (behind the decorative front)
            panels.append(
                Panel(
                    panel_type=PanelType.DRAWER_BOX_FRONT,
                    width=box_front_width,
                    height=drawer_spec.box_height,
                    material=MaterialSpec(
                        thickness=drawer_spec.side_thickness,
                        material_type=context.material.material_type,
                    ),
                    position=Position(
                        x=context.position.x
                        + side_clearance
                        + drawer_spec.side_thickness,
                        y=position_y + 0.625,  # above reveal + slide clearance
                    ),
                    metadata=drawer_metadata.copy(),
                )
            )

            # Create left drawer side
            panels.append(
                Panel(
                    panel_type=PanelType.DRAWER_SIDE,
                    width=drawer_spec.box_depth,
                    height=drawer_spec.box_height,
                    material=MaterialSpec(
                        thickness=drawer_spec.side_thickness,
                        material_type=context.material.material_type,
                    ),
                    position=Position(
                        x=context.position.x + side_clearance,
                        y=position_y + 0.625,
                    ),
                    metadata=drawer_metadata.copy(),
                )
            )

            # Create right drawer side
            panels.append(
                Panel(
                    panel_type=PanelType.DRAWER_SIDE,
                    width=drawer_spec.box_depth,
                    height=drawer_spec.box_height,
                    material=MaterialSpec(
                        thickness=drawer_spec.side_thickness,
                        material_type=context.material.material_type,
                    ),
                    position=Position(
                        x=context.position.x
                        + side_clearance
                        + drawer_spec.box_width
                        - drawer_spec.side_thickness,
                        y=position_y + 0.625,
                    ),
                    metadata=drawer_metadata.copy(),
                )
            )

            # Create drawer bottom
            panels.append(
                Panel(
                    panel_type=PanelType.DRAWER_BOTTOM,
                    width=bottom_width,
                    height=bottom_depth,  # depth becomes height in 2D panel representation
                    material=MaterialSpec(
                        thickness=drawer_spec.bottom_thickness,
                        material_type=context.material.material_type,
                    ),
                    position=Position(
                        x=context.position.x
                        + side_clearance
                        + drawer_spec.side_thickness
                        - drawer_spec.dado_depth,
                        y=position_y + 0.625 + drawer_spec.dado_depth,
                    ),
                    metadata=drawer_metadata.copy(),
                )
            )

        # Add structural top panel above the drawer stack to close off the top drawer
        # Uses HORIZONTAL_DIVIDER (not SHELF) so it doesn't create a cubby above
        # Uses standard 1" front setback
        # Skip if the cabinet handles row-level dividers (multi-row layouts)
        if not context.skip_top_divider:
            top_panel_setback = 1.0
            top_panel_y = context.position.y + (count * front_height)
            panels.append(
                Panel(
                    panel_type=PanelType.HORIZONTAL_DIVIDER,
                    width=context.width,
                    height=context.depth
                    - top_panel_setback,  # depth becomes height in 2D
                    material=context.material,
                    position=Position(
                        x=context.position.x,
                        y=top_panel_y,
                    ),
                )
            )

        # Hardware - Drawer slides (multiply by count for multiple drawers)
        slide_qty = (1 if slide_type == "center_mount" else 2) * count
        screw_qty = 4 * slide_qty

        slide_desc = (
            f'{"Soft-Close " if soft_close else ""}Drawer Slide ({slide_length}")'
        )
        hardware.append(
            HardwareItem(
                name=slide_desc,
                quantity=slide_qty,
                sku=f"SLIDE-{slide_type.upper()}-{slide_length}",
                notes=f"{slide_type.replace('_', ' ')} mount",
            )
        )

        # Mounting screws
        hardware.append(
            HardwareItem(
                name='Mounting Screw #8x5/8"',
                quantity=screw_qty,
                sku="SCREW-8-5/8-PAN",
                notes="For slide mounting",
            )
        )

        # Handle/Pull (one per drawer)
        hardware.append(
            HardwareItem(
                name="Handle/Pull",
                quantity=count,
                sku="HANDLE-DRAWER",
                notes='Centered, 1.5" from top',
            )
        )

        # Edge banding for drawer fronts (all drawers)
        edge_banding_per_drawer = 2 * (
            drawer_spec.front_width + drawer_spec.front_height
        )
        total_edge_banding = edge_banding_per_drawer * count
        hardware.append(
            HardwareItem(
                name="Edge Banding",
                quantity=1,
                sku="EDGE-BAND-3/4",
                notes=f"{total_edge_banding:.2f} linear inches ({count} drawer fronts)",
            )
        )

        metadata = {
            "drawer_count": count,
            "drawer_spec": drawer_spec,
            "slide_type": slide_type,
            "slide_length": slide_length,
            "soft_close": soft_close,
            "front_style": front_style,
        }

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for the drawer.

        This method provides a separate interface for getting just the hardware
        requirements without full panel generation.

        Args:
            config: Drawer configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for drawer hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("drawer.standard")
class StandardDrawerComponent(_DrawerBase):
    """Standard drawer component - basic drawer box with front.

    Generates one or more stacked standard drawers with:
    - Decorative overlay front panel
    - 1/2" plywood box sides, front, and back
    - 1/4" plywood bottom in 1/4" dado
    - Drawer slides (side mount, undermount, or center mount)
    - Handle/pull and edge banding

    Configuration options:
        count: Number of stacked drawers (default: 1)
        front_height: Height of each drawer front in inches (min: 3.0).
                      If not specified, auto-calculates to fill section height.
        slide_type: Type of slide mounting - "side_mount", "undermount",
                    or "center_mount" (default: "side_mount")
        slide_length: Slide length in inches or "auto" (default: "auto")
        soft_close: Whether to use soft-close slides (default: True)
        front_style: Front style - "overlay" or "inset" (default: "overlay")

    Example:
        config = {
            "count": 4,
            "front_height": 8.0,
            "slide_type": "side_mount",
            "slide_length": "auto",
            "soft_close": True,
        }
        result = component.generate(config, context)
    """

    pass


@component_registry.register("drawer.file")
class FileDrawerComponent(_DrawerBase):
    """File drawer component - deeper drawer for hanging files.

    File drawers are designed to accommodate hanging file folders and require
    greater interior height than standard drawers. They support both letter
    and legal size files.

    Minimum interior heights:
        - Letter files: 10.5" minimum box height
        - Legal files: 12.0" minimum box height

    Configuration options:
        file_type: Type of files - "letter" or "legal" (default: "letter")
        front_height: Height of drawer front in inches (must provide sufficient box height)
        slide_type: Type of slide mounting - "side_mount", "undermount",
                    or "center_mount" (default: "side_mount")
        slide_length: Slide length in inches or "auto" (default: "auto")
        soft_close: Whether to use soft-close slides (default: True)
        front_style: Front style - "overlay" or "inset" (default: "overlay")

    Note: Center mount slides are not recommended for file drawers due to
    the weight when loaded with files.

    Validation rules:
        - V-05: file drawer height < 10.5"/12" -> ERROR (insufficient for file type)
        - V-06: center_mount + file drawer -> WARNING (heavy when loaded)

    Example:
        config = {
            "file_type": "legal",
            "front_height": 14.0,
            "slide_type": "undermount",
            "soft_close": True,
        }
        result = component.generate(config, context)
    """

    MIN_FILE_HEIGHT: dict[str, float] = {"letter": 10.5, "legal": 12.0}

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate file drawer configuration.

        In addition to base drawer validation, checks:
        - V-05: Box height meets minimum for file type (letter: 10.5", legal: 12.0")
        - V-06: Warns if center_mount slides are used (not recommended for heavy file drawers)

        Args:
            config: File drawer configuration dictionary with optional keys:
                - file_type: Type of files - "letter" or "legal" (default: "letter")
                - front_height: Height of drawer front (default: 6.0")
                - slide_type: Type of slide mounting (default: "side_mount")
                - slide_length: Slide length or "auto" (default: "auto")

            context: Component context with section dimensions and material.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        result = super().validate(config, context)
        errors = list(result.errors)
        warnings = list(result.warnings)

        file_type = config.get("file_type", "letter")
        slide_type = config.get("slide_type", "side_mount")
        front_height = config.get("front_height", 6.0)

        # Calculate actual box height
        box_height = front_height - 0.125 - 0.5  # reveal + slide clearance

        # Validate file_type
        if file_type not in self.MIN_FILE_HEIGHT:
            errors.append(
                f"Invalid file_type '{file_type}'. Must be 'letter' or 'legal'"
            )
        else:
            # V-05: Check minimum height for file type
            min_height = self.MIN_FILE_HEIGHT[file_type]
            if box_height < min_height:
                errors.append(
                    f'File drawer box height ({box_height:.2f}") is below minimum '
                    f'for {file_type} files ({min_height}")'
                )

        # V-06: Warn about center mount with file drawers
        if slide_type == "center_mount":
            warnings.append(
                "center_mount slides not recommended for file drawers "
                "(heavy when loaded)"
            )

        return ValidationResult(tuple(errors), tuple(warnings))
