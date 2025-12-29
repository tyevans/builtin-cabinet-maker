"""Corner cabinet footprint calculations and components.

This module provides data structures and calculations for corner cabinet
footprints. Corner cabinets are specialized units designed to fit in the
corner where two walls meet, maximizing storage in otherwise difficult
to access spaces.

Three main corner cabinet types are supported:

1. **Lazy Susan**: A rotating shelf system that provides full access to
   the corner space. The cabinet is square with equal footprint on both
   walls.

2. **Blind Corner**: A standard cabinet that extends into the corner with
   one accessible side and one "blind" side. Requires a filler panel for
   proper door clearance.

3. **Diagonal**: A cabinet with a diagonal face across the corner,
   creating an angled front that provides easier access than blind corners.

Components:
- LazySusanCornerComponent: Component for generating lazy susan corner cabinets
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..entities import Panel
from ..value_objects import MaterialSpec, PanelType, Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult


@dataclass(frozen=True)
class CornerFootprint:
    """Space consumed by corner cabinet on each wall segment.

    Represents the linear distance along each wall that a corner cabinet
    occupies. These measurements are taken from the interior corner point
    where the two walls meet.

    Attributes:
        left_wall: Inches consumed on the left wall (when facing the corner).
        right_wall: Inches consumed on the right wall (when facing the corner).

    Example:
        A lazy susan with 24" depth would have equal footprints:
        >>> footprint = CornerFootprint(left_wall=24.0, right_wall=24.0)

        A blind corner might have asymmetric footprints:
        >>> footprint = CornerFootprint(left_wall=36.0, right_wall=18.0)
    """

    left_wall: float
    right_wall: float

    def __post_init__(self) -> None:
        """Validate that footprint values are positive."""
        if self.left_wall <= 0:
            raise ValueError("left_wall must be positive")
        if self.right_wall <= 0:
            raise ValueError("right_wall must be positive")

    @property
    def total_footprint(self) -> float:
        """Calculate total linear footage consumed by the corner cabinet."""
        return self.left_wall + self.right_wall

    @property
    def is_symmetric(self) -> bool:
        """Check if the footprint is equal on both walls."""
        return math.isclose(self.left_wall, self.right_wall, rel_tol=1e-9)


def calculate_lazy_susan_footprint(
    depth: float,
    door_clearance: float = 2.0,
) -> CornerFootprint:
    """Calculate footprint for a lazy susan corner cabinet.

    A lazy susan cabinet is square, with equal space consumed on both walls.
    The footprint equals the cabinet depth plus any door clearance needed.

    The rotating shelves inside require a square cabinet body to function
    properly, making this the most space-efficient corner solution in terms
    of access-to-footprint ratio.

    Args:
        depth: Cabinet depth in inches. Standard depths are 24" for base
            cabinets and 12" for wall cabinets.
        door_clearance: Additional space needed for door swing, in inches.
            Default is 2.0" which accommodates standard hinges.

    Returns:
        CornerFootprint with equal left and right wall consumption.

    Raises:
        ValueError: If depth or door_clearance is not positive.

    Example:
        >>> footprint = calculate_lazy_susan_footprint(depth=24.0)
        >>> footprint.left_wall
        26.0
        >>> footprint.right_wall
        26.0
        >>> footprint.is_symmetric
        True
    """
    if depth <= 0:
        raise ValueError("depth must be positive")
    if door_clearance < 0:
        raise ValueError("door_clearance must be non-negative")

    total = depth + door_clearance
    return CornerFootprint(left_wall=total, right_wall=total)


def calculate_blind_corner_footprint(
    depth: float,
    accessible_width: float,
    filler_width: float = 3.0,
    blind_side: str = "left",
) -> CornerFootprint:
    """Calculate footprint for a blind corner cabinet.

    A blind corner cabinet extends into the corner with one side accessible
    and the other side "blind" (not directly accessible from the front).
    A filler panel is typically required on the accessible side to allow
    proper door swing clearance.

    The blind side extends the full depth into the corner, while the
    accessible side includes the cabinet opening plus the filler.

    Args:
        depth: Cabinet depth in inches. Standard depths are 24" for base
            cabinets and 12" for wall cabinets.
        accessible_width: Width of the accessible cabinet opening in inches.
            This is the usable cabinet face width.
        filler_width: Width of the filler panel in inches. Default is 3.0"
            which is standard for most installations. Fillers ensure adjacent
            doors and drawers can open without hitting the wall.
        blind_side: Which wall the blind (inaccessible) side faces.
            Must be "left" or "right". Default is "left".

    Returns:
        CornerFootprint with asymmetric wall consumption based on the
        blind side configuration.

    Raises:
        ValueError: If depth, accessible_width, or filler_width is invalid,
            or if blind_side is not "left" or "right".

    Example:
        >>> footprint = calculate_blind_corner_footprint(
        ...     depth=24.0,
        ...     accessible_width=36.0,
        ...     filler_width=3.0,
        ...     blind_side="left"
        ... )
        >>> footprint.left_wall  # Blind side: full depth
        24.0
        >>> footprint.right_wall  # Accessible side: width + filler
        39.0
    """
    if depth <= 0:
        raise ValueError("depth must be positive")
    if accessible_width <= 0:
        raise ValueError("accessible_width must be positive")
    if filler_width < 0:
        raise ValueError("filler_width must be non-negative")
    if blind_side not in ("left", "right"):
        raise ValueError("blind_side must be 'left' or 'right'")

    # The blind side takes up the full depth against the wall
    blind_footprint = depth

    # The accessible side includes the cabinet width plus filler
    accessible_footprint = accessible_width + filler_width

    if blind_side == "left":
        return CornerFootprint(
            left_wall=blind_footprint,
            right_wall=accessible_footprint,
        )
    else:
        return CornerFootprint(
            left_wall=accessible_footprint,
            right_wall=blind_footprint,
        )


def calculate_diagonal_footprint(depth: float) -> CornerFootprint:
    """Calculate footprint for a diagonal corner cabinet.

    A diagonal corner cabinet has an angled face that cuts across the corner
    at 45 degrees. This design provides better access than a blind corner
    while using less total wall space than a lazy susan.

    The footprint on each wall is calculated using the Pythagorean theorem:
    for a cabinet with depth D positioned at 45 degrees, each wall segment
    equals D * sqrt(2) / 2, which simplifies to D / sqrt(2).

    However, for practical cabinet construction, the diagonal face creates
    a cabinet where each wall segment equals the depth (the diagonal face
    width is depth * sqrt(2)).

    Args:
        depth: Cabinet depth in inches, measured perpendicular to the
            diagonal face. Standard depths are 24" for base cabinets
            and 12" for wall cabinets.

    Returns:
        CornerFootprint with equal wall consumption on both sides.
        Each wall segment equals the cabinet depth.

    Raises:
        ValueError: If depth is not positive.

    Example:
        >>> footprint = calculate_diagonal_footprint(depth=24.0)
        >>> footprint.left_wall
        24.0
        >>> footprint.right_wall
        24.0
        >>> footprint.is_symmetric
        True

    Note:
        The diagonal face width (the visible front) would be:
        diagonal_face_width = depth * sqrt(2) = depth * 1.414...

        For a 24" depth cabinet:
        diagonal_face_width = 24 * 1.414 = 33.94"
    """
    if depth <= 0:
        raise ValueError("depth must be positive")

    # For a 45-degree diagonal cabinet, each wall segment equals the depth
    # The cabinet forms an isoceles right triangle with the corner
    return CornerFootprint(left_wall=depth, right_wall=depth)


@component_registry.register("corner.lazy_susan")
class LazySusanCornerComponent:
    """Lazy Susan corner cabinet component.

    A rotating shelf system that provides full access to corner cabinet space.
    The cabinet is square with equal footprint on both walls, and contains
    rotating trays mounted on a central pole.

    Configuration:
        tray_diameter: float | None - Diameter of rotating trays in inches.
            If None, auto-calculated as (depth * 2) - 4.
        tray_count: int - Number of rotating trays (default: 2, range: 1-5).
        door_style: "single" | "bifold" - Door configuration (default: "bifold").
        door_clearance: float - Space for door swing in inches (default: 2.0).

    Panel Generation:
        - LEFT_SIDE: Left wall panel
        - RIGHT_SIDE: Right wall panel
        - TOP: Top panel
        - BOTTOM: Bottom panel
        - BACK: Back panel(s) - L-shaped or two rectangular panels

    Hardware Generation:
        - Lazy Susan Center Pole (1)
        - Lazy Susan Trays (qty = tray_count)
        - Lazy Susan Bearings (qty = tray_count)
        - Bi-fold hinges (4 total) if door_style is "bifold"
        - Standard hinges if door_style is "single"

    Example:
        config = {
            "tray_diameter": 20.0,
            "tray_count": 3,
            "door_style": "bifold",
            "door_clearance": 2.0,
        }
        result = component.generate(config, context)
    """

    # Minimum practical tray diameter for usability
    MIN_PRACTICAL_TRAY_DIAMETER = 16.0

    def _parse_config(
        self, config: dict[str, Any], context: ComponentContext
    ) -> tuple[float, int, str, float]:
        """Parse lazy susan configuration.

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            Tuple of (tray_diameter, tray_count, door_style, door_clearance).
        """
        door_clearance = config.get("door_clearance", 2.0)
        tray_count = config.get("tray_count", 2)
        door_style = config.get("door_style", "bifold")

        # Auto-calculate tray diameter if not provided
        tray_diameter = config.get("tray_diameter")
        if tray_diameter is None:
            # Default formula: (depth * 2) - 4 inches for clearance
            tray_diameter = (context.depth * 2) - 4.0

        return tray_diameter, tray_count, door_style, door_clearance

    def _calculate_max_tray_diameter(self, depth: float) -> float:
        """Calculate maximum allowable tray diameter.

        The tray must fit within the cabinet with 2" total clearance
        (1" on each side for rotation).

        Args:
            depth: Cabinet depth in inches.

        Returns:
            Maximum tray diameter in inches.
        """
        return (depth * 2) - 2.0

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate lazy susan configuration.

        Validation Rules:
        - Tray diameter must not exceed (depth * 2) - 2
        - Tray count must be between 1 and 5 (inclusive)
        - Door style must be "single" or "bifold"
        - Warning if tray diameter < 16" (may be too small for practical use)

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        tray_diameter, tray_count, door_style, door_clearance = self._parse_config(
            config, context
        )

        # Validate tray count (1-5)
        if not isinstance(tray_count, int) or tray_count < 1 or tray_count > 5:
            errors.append("Tray count must be between 1 and 5")

        # Validate door style
        if door_style not in ("single", "bifold"):
            errors.append("Door style must be 'single' or 'bifold'")

        # Validate door clearance
        if door_clearance < 0:
            errors.append("Door clearance must be non-negative")

        # Validate tray diameter against maximum
        max_diameter = self._calculate_max_tray_diameter(context.depth)
        if tray_diameter > max_diameter:
            errors.append(
                f"Tray diameter {tray_diameter:.1f}\" exceeds maximum "
                f"{max_diameter:.1f}\" for {context.depth:.1f}\" depth"
            )

        # Warning for small tray diameter
        if tray_diameter < self.MIN_PRACTICAL_TRAY_DIAMETER:
            warnings.append(
                f"Tray diameter {tray_diameter:.1f}\" is less than recommended "
                f"minimum of {self.MIN_PRACTICAL_TRAY_DIAMETER:.1f}\" - "
                "may be impractical for storage"
            )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate lazy susan corner cabinet panels.

        Creates panel entities for the cabinet structure including:
        - Left and right side panels
        - Top and bottom panels
        - Back panels (two rectangular panels forming an L-shape)

        The lazy susan trays themselves are hardware items, not panels.

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing cabinet panels and hardware.
        """
        tray_diameter, tray_count, door_style, door_clearance = self._parse_config(
            config, context
        )

        panels: list[Panel] = []
        material = context.material

        # Calculate interior dimensions
        thickness = material.thickness
        interior_height = context.height - (2 * thickness)
        interior_depth = context.depth - thickness  # Account for back panel

        # LEFT_SIDE panel - full height, depth of section
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=interior_depth,
                height=interior_height,
                material=material,
                position=Position(context.position.x, context.position.y + thickness),
            )
        )

        # RIGHT_SIDE panel - full height, depth of section
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=interior_depth,
                height=interior_height,
                material=material,
                position=Position(
                    context.position.x + context.width - thickness,
                    context.position.y + thickness,
                ),
            )
        )

        # TOP panel - full width, interior depth
        panels.append(
            Panel(
                panel_type=PanelType.TOP,
                width=context.width,
                height=interior_depth,
                material=material,
                position=Position(
                    context.position.x, context.position.y + context.height - thickness
                ),
            )
        )

        # BOTTOM panel - full width, interior depth
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=context.width,
                height=interior_depth,
                material=material,
                position=Position(context.position.x, context.position.y),
            )
        )

        # BACK panels - two rectangular panels forming L-shape
        # Back panel material (typically thinner)
        back_material = MaterialSpec.standard_1_4()

        # First back panel - runs along left wall (full height, left section width)
        # This covers from the back-left corner to the cabinet depth
        back_width_left = context.depth
        panels.append(
            Panel(
                panel_type=PanelType.BACK,
                width=back_width_left,
                height=context.height,
                material=back_material,
                position=Position(context.position.x, context.position.y),
            )
        )

        # Second back panel - runs along right wall
        # This covers from where the first panel ends to the front
        back_width_right = context.width - context.depth
        if back_width_right > 0:
            panels.append(
                Panel(
                    panel_type=PanelType.BACK,
                    width=back_width_right,
                    height=context.height,
                    material=back_material,
                    position=Position(
                        context.position.x + context.depth, context.position.y
                    ),
                )
            )

        # Generate hardware
        hardware = self.hardware(config, context)

        # Calculate footprint for metadata
        footprint = calculate_lazy_susan_footprint(context.depth, door_clearance)

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "tray_diameter": tray_diameter,
                "tray_count": tray_count,
                "door_style": door_style,
                "footprint": {
                    "left_wall": footprint.left_wall,
                    "right_wall": footprint.right_wall,
                    "total": footprint.total_footprint,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for lazy susan corner cabinet.

        Hardware includes:
        - Lazy Susan Center Pole (1) - vertical mounting pole
        - Lazy Susan Trays (qty = tray_count) - rotating shelf trays
        - Lazy Susan Bearings (qty = tray_count) - rotation bearings
        - Door hinges based on door_style:
          - "bifold": 4 bi-fold hinges (2 pairs)
          - "single": 2-3 standard European hinges

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for the lazy susan cabinet.
        """
        tray_diameter, tray_count, door_style, _ = self._parse_config(config, context)

        items: list[HardwareItem] = []

        # Lazy Susan Center Pole
        items.append(
            HardwareItem(
                name="Lazy Susan Center Pole",
                quantity=1,
                sku="LS-POLE-ADJ",
                notes=f"Adjustable pole for {context.height:.1f}\" cabinet height",
            )
        )

        # Lazy Susan Trays
        items.append(
            HardwareItem(
                name="Lazy Susan Tray",
                quantity=tray_count,
                sku=f"LS-TRAY-{int(tray_diameter)}",
                notes=f"{tray_diameter:.1f}\" diameter rotating tray",
            )
        )

        # Lazy Susan Bearings
        items.append(
            HardwareItem(
                name="Lazy Susan Bearing",
                quantity=tray_count,
                sku="LS-BEARING",
                notes="Heavy-duty ball bearing for smooth rotation",
            )
        )

        # Door hardware based on style
        if door_style == "bifold":
            # Bi-fold doors require 4 hinges (2 pairs for the folding mechanism)
            items.append(
                HardwareItem(
                    name="Bi-Fold Hinge",
                    quantity=4,
                    sku="BIFOLD-HINGE-35MM",
                    notes="35mm cup bi-fold hinge for corner cabinet doors",
                )
            )
            items.append(
                HardwareItem(
                    name="Bi-Fold Door Catch",
                    quantity=1,
                    sku="BIFOLD-CATCH",
                    notes="Magnetic catch for bi-fold door alignment",
                )
            )
        else:
            # Single door - calculate hinge count based on height
            if context.height < 40:
                hinge_count = 2
            elif context.height <= 60:
                hinge_count = 3
            else:
                hinge_count = 4

            items.append(
                HardwareItem(
                    name="European Hinge",
                    quantity=hinge_count,
                    sku="EURO-35MM-SC",
                    notes="35mm soft-close hinge for corner cabinet door",
                )
            )

        # Door handle/knob
        items.append(
            HardwareItem(
                name="Handle/Knob",
                quantity=1 if door_style == "single" else 2,
                notes="Position placeholder - select handle separately",
            )
        )

        return items


@component_registry.register("corner.diagonal")
class DiagonalCornerComponent:
    """Diagonal corner cabinet component.

    A corner cabinet with a diagonal face that cuts across the corner at 45 degrees.
    This design provides better access than a blind corner while maintaining a
    clean, angled front. The side panels require 45-degree angle cuts.

    Configuration:
        face_width: float | None - Width of diagonal face in inches.
            If None, auto-calculated as depth * sqrt(2).
        shelf_shape: "triangular" | "squared" - Shape of interior shelves (default: "squared").
        shelf_count: int - Number of shelves (default: 2, range: 0-6).

    Panel Generation:
        - LEFT_SIDE: Left wall panel (with 45-degree angle cut)
        - RIGHT_SIDE: Right wall panel (with 45-degree angle cut)
        - DIAGONAL_FACE: Angled front panel
        - TOP: Top panel
        - BOTTOM: Bottom panel
        - SHELF: Shelf panels (qty = shelf_count)

    Hardware Generation:
        - Shelf Pins (shelf_count * 4) if shelf_count > 0

    Footprint (symmetric):
        - Both walls = depth

    Example:
        config = {
            "face_width": 24.0,
            "shelf_shape": "squared",
            "shelf_count": 3,
        }
        result = component.generate(config, context)
    """

    # Minimum face width for practical usability
    MIN_FACE_WIDTH = 18.0
    # Maximum shelf count
    MAX_SHELF_COUNT = 6

    def _parse_config(
        self, config: dict[str, Any], context: ComponentContext
    ) -> tuple[float, str, int]:
        """Parse diagonal corner configuration.

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            Tuple of (face_width, shelf_shape, shelf_count).
        """
        shelf_shape = config.get("shelf_shape", "squared")
        shelf_count = config.get("shelf_count", 2)

        # Auto-calculate face width if not provided: depth * sqrt(2)
        face_width = config.get("face_width")
        if face_width is None:
            face_width = context.depth * math.sqrt(2)

        return face_width, shelf_shape, shelf_count

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate diagonal corner configuration.

        Validation Rules:
        - face_width must be >= 18"
        - shelf_count must be between 0 and 6 (inclusive)
        - shelf_shape must be "triangular" or "squared"

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        face_width, shelf_shape, shelf_count = self._parse_config(config, context)

        # Validate face_width
        if face_width < self.MIN_FACE_WIDTH:
            errors.append(
                f"face_width must be at least {self.MIN_FACE_WIDTH:.0f}\" "
                f"(got {face_width:.1f}\")"
            )

        # Validate shelf_count (0-6)
        if not isinstance(shelf_count, int) or shelf_count < 0 or shelf_count > self.MAX_SHELF_COUNT:
            errors.append(f"shelf_count must be between 0 and {self.MAX_SHELF_COUNT}")

        # Validate shelf_shape
        if shelf_shape not in ("triangular", "squared"):
            errors.append("shelf_shape must be 'triangular' or 'squared'")

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate diagonal corner cabinet panels.

        Creates panel entities for the cabinet structure including:
        - Left and right side panels (with 45-degree angle cuts)
        - Diagonal face panel
        - Top and bottom panels
        - Shelf panels based on shelf_shape and shelf_count

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing cabinet panels and hardware.
        """
        face_width, shelf_shape, shelf_count = self._parse_config(config, context)

        panels: list[Panel] = []
        material = context.material

        # Calculate dimensions
        thickness = material.thickness
        interior_height = context.height - (2 * thickness)
        interior_depth = context.depth - thickness  # Account for back

        # LEFT_SIDE panel - with 45-degree angle cut
        # The side panel is the full depth, but will be cut at an angle
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=interior_depth,
                height=interior_height,
                material=material,
                position=Position(context.position.x, context.position.y + thickness),
                metadata={"is_angled": True, "angle": 45},
            )
        )

        # RIGHT_SIDE panel - with 45-degree angle cut
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=interior_depth,
                height=interior_height,
                material=material,
                position=Position(
                    context.position.x + context.width - thickness,
                    context.position.y + thickness,
                ),
                metadata={"is_angled": True, "angle": 45},
            )
        )

        # DIAGONAL_FACE panel - the angled front face
        panels.append(
            Panel(
                panel_type=PanelType.DIAGONAL_FACE,
                width=face_width,
                height=interior_height,
                material=material,
                position=Position(context.position.x, context.position.y + thickness),
                metadata={"is_angled": True, "angle": 45},
            )
        )

        # TOP panel
        panels.append(
            Panel(
                panel_type=PanelType.TOP,
                width=context.depth,
                height=context.depth,
                material=material,
                position=Position(
                    context.position.x, context.position.y + context.height - thickness
                ),
            )
        )

        # BOTTOM panel
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=context.depth,
                height=context.depth,
                material=material,
                position=Position(context.position.x, context.position.y),
            )
        )

        # SHELF panels - dimensions depend on shelf_shape
        if shelf_count > 0:
            if shelf_shape == "triangular":
                shelf_width = context.depth
                shelf_depth = context.depth
            else:  # squared
                shelf_width = context.depth * 0.8
                shelf_depth = context.depth * 0.8

            for i in range(shelf_count):
                panels.append(
                    Panel(
                        panel_type=PanelType.SHELF,
                        width=shelf_width,
                        height=shelf_depth,
                        material=material,
                        position=Position(
                            context.position.x + thickness,
                            context.position.y + thickness,
                        ),
                        metadata={"shelf_index": i, "shelf_shape": shelf_shape},
                    )
                )

        # Generate hardware
        hardware = self.hardware(config, context)

        # Calculate footprint for metadata
        footprint = calculate_diagonal_footprint(context.depth)

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "face_width": face_width,
                "shelf_shape": shelf_shape,
                "shelf_count": shelf_count,
                "footprint": {
                    "left_wall": footprint.left_wall,
                    "right_wall": footprint.right_wall,
                    "total": footprint.total_footprint,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for diagonal corner cabinet.

        Hardware includes:
        - Shelf Pins (shelf_count * 4) if shelf_count > 0

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for the diagonal corner cabinet.
        """
        _, _, shelf_count = self._parse_config(config, context)

        items: list[HardwareItem] = []

        if shelf_count > 0:
            # Shelf Pins - 4 per shelf
            items.append(
                HardwareItem(
                    name="Shelf Pin",
                    quantity=shelf_count * 4,
                    sku="SP-5MM",
                    notes="5mm shelf pins for adjustable shelves",
                )
            )

        return items


@component_registry.register("corner.blind")
class BlindCornerComponent:
    """Blind corner cabinet component.

    A standard cabinet that extends into the corner with one accessible side
    and one "blind" (inaccessible) side. The blind side requires pull-out
    hardware for access, and a filler panel is typically installed for proper
    door/drawer clearance on adjacent cabinets.

    Configuration:
        blind_side: "left" | "right" - Which side is dead/inaccessible (default: "left").
        accessible_width: float - Usable pull-out width in inches (default: 24.0).
        pull_out: bool - Enable/disable pull-out hardware (default: True).
        filler_width: float - Filler panel width on blind side in inches (default: 3.0).

    Panel Generation:
        - LEFT_SIDE: Left wall panel
        - RIGHT_SIDE: Right wall panel
        - TOP: Top panel (accessible_width + filler_width for width)
        - BOTTOM: Bottom panel (accessible_width + filler_width for width)
        - BACK: Back panel
        - FILLER: Filler panel on the blind side

    Hardware Generation (when pull_out is True):
        - Blind Corner Pull-out Slides (1 set)
        - Blind Corner Pull-out Tray (1)

    Footprint (asymmetric):
        - If blind_side == "left": left_wall = depth, right_wall = accessible_width + filler_width
        - If blind_side == "right": left_wall = accessible_width + filler_width, right_wall = depth

    Example:
        config = {
            "blind_side": "left",
            "accessible_width": 24.0,
            "pull_out": True,
            "filler_width": 3.0,
        }
        result = component.generate(config, context)
    """

    # Minimum practical accessible width for usability
    MIN_ACCESSIBLE_WIDTH = 12.0
    # Maximum recommended accessible width for pull-out effectiveness
    MAX_RECOMMENDED_WIDTH = 36.0

    def _parse_config(
        self, config: dict[str, Any], context: ComponentContext
    ) -> tuple[str, float, bool, float]:
        """Parse blind corner configuration.

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            Tuple of (blind_side, accessible_width, pull_out, filler_width).
        """
        blind_side = config.get("blind_side", "left")
        accessible_width = config.get("accessible_width", 24.0)
        pull_out = config.get("pull_out", True)
        filler_width = config.get("filler_width", 3.0)

        return blind_side, accessible_width, pull_out, filler_width

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate blind corner configuration.

        Validation Rules:
        - blind_side must be "left" or "right"
        - accessible_width must be >= 12"
        - Warning if accessible_width > 36" (reduces pull-out effectiveness)
        - filler_width must be non-negative

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        blind_side, accessible_width, pull_out, filler_width = self._parse_config(
            config, context
        )

        # Validate blind_side
        if blind_side not in ("left", "right"):
            errors.append("blind_side must be 'left' or 'right'")

        # Validate accessible_width
        if accessible_width < self.MIN_ACCESSIBLE_WIDTH:
            errors.append(
                f"accessible_width must be at least {self.MIN_ACCESSIBLE_WIDTH:.0f}\" "
                f"(got {accessible_width:.1f}\")"
            )

        # Warning for wide accessible width
        if accessible_width > self.MAX_RECOMMENDED_WIDTH:
            warnings.append(
                f"accessible_width {accessible_width:.1f}\" exceeds recommended maximum "
                f"of {self.MAX_RECOMMENDED_WIDTH:.0f}\" - may reduce pull-out effectiveness"
            )

        # Validate filler_width
        if filler_width < 0:
            errors.append("filler_width must be non-negative")

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate blind corner cabinet panels.

        Creates panel entities for the cabinet structure including:
        - Left and right side panels
        - Top and bottom panels
        - Back panel
        - Filler panel on the blind side

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing cabinet panels and hardware.
        """
        blind_side, accessible_width, pull_out, filler_width = self._parse_config(
            config, context
        )

        panels: list[Panel] = []
        material = context.material

        # Calculate dimensions
        thickness = material.thickness
        interior_height = context.height - (2 * thickness)
        interior_depth = context.depth - thickness  # Account for back panel
        cabinet_width = accessible_width + filler_width

        # LEFT_SIDE panel - full height, depth of section
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=interior_depth,
                height=interior_height,
                material=material,
                position=Position(context.position.x, context.position.y + thickness),
            )
        )

        # RIGHT_SIDE panel - full height, depth of section
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=interior_depth,
                height=interior_height,
                material=material,
                position=Position(
                    context.position.x + cabinet_width - thickness,
                    context.position.y + thickness,
                ),
            )
        )

        # TOP panel - full cabinet width, interior depth
        panels.append(
            Panel(
                panel_type=PanelType.TOP,
                width=cabinet_width,
                height=interior_depth,
                material=material,
                position=Position(
                    context.position.x, context.position.y + context.height - thickness
                ),
            )
        )

        # BOTTOM panel - full cabinet width, interior depth
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=cabinet_width,
                height=interior_depth,
                material=material,
                position=Position(context.position.x, context.position.y),
            )
        )

        # BACK panel - uses standard 1/4" back material
        back_material = MaterialSpec.standard_1_4()
        panels.append(
            Panel(
                panel_type=PanelType.BACK,
                width=cabinet_width,
                height=context.height,
                material=back_material,
                position=Position(context.position.x, context.position.y),
            )
        )

        # FILLER panel - on the blind side
        # Filler height is the full cabinet height
        if filler_width > 0:
            if blind_side == "left":
                filler_x = context.position.x
            else:
                filler_x = context.position.x + cabinet_width - filler_width
            panels.append(
                Panel(
                    panel_type=PanelType.FILLER,
                    width=filler_width,
                    height=context.height,
                    material=material,
                    position=Position(filler_x, context.position.y),
                )
            )

        # Generate hardware
        hardware = self.hardware(config, context)

        # Calculate footprint for metadata
        footprint = calculate_blind_corner_footprint(
            depth=context.depth,
            accessible_width=accessible_width,
            filler_width=filler_width,
            blind_side=blind_side,
        )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "blind_side": blind_side,
                "accessible_width": accessible_width,
                "pull_out": pull_out,
                "filler_width": filler_width,
                "cabinet_width": cabinet_width,
                "footprint": {
                    "left_wall": footprint.left_wall,
                    "right_wall": footprint.right_wall,
                    "total": footprint.total_footprint,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for blind corner cabinet.

        Hardware includes (when pull_out is True):
        - Blind Corner Pull-out Slides (1 set) - heavy-duty slides for pull-out
        - Blind Corner Pull-out Tray (1) - the accessible storage tray

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for the blind corner cabinet.
        """
        blind_side, accessible_width, pull_out, filler_width = self._parse_config(
            config, context
        )

        items: list[HardwareItem] = []

        if pull_out:
            # Blind Corner Pull-out Slides
            items.append(
                HardwareItem(
                    name="Blind Corner Pull-out Slides",
                    quantity=1,
                    sku="BC-PULLOUT-SLIDE",
                    notes=f"Heavy-duty slides for {accessible_width:.0f}\" pull-out",
                )
            )

            # Blind Corner Pull-out Tray
            items.append(
                HardwareItem(
                    name="Blind Corner Pull-out Tray",
                    quantity=1,
                    sku=f"BC-TRAY-{int(accessible_width)}",
                    notes=f"{accessible_width:.1f}\" wide pull-out tray for {blind_side} blind corner",
                )
            )

        return items
