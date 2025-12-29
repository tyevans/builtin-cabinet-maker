"""Desk components for built-in desk generation (FRD-18).

This module provides desk surface components including:
- Desktop panel generation with configurable dimensions
- Grommet cutouts for cable management
- Waterfall edge treatment support
- Edge banding calculation
- Floating desk mounting hardware
- L-shaped desk configuration for corner desks

The desk components are designed to integrate with the cabinet system
and follow the same component protocol patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from ..entities import Panel
from ..value_objects import (
    CutoutShape,
    GrommetSize,
    MaterialSpec,
    PanelCutout,
    PanelType,
    Point2D,
    Position,
)
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult


# --- Ergonomic Constants ---

SITTING_DESK_HEIGHT_MIN = 28.0
SITTING_DESK_HEIGHT_MAX = 32.0
SITTING_DESK_HEIGHT_DEFAULT = 30.0
STANDING_DESK_HEIGHT_MIN = 38.0
STANDING_DESK_HEIGHT_MAX = 48.0
STANDING_DESK_HEIGHT_DEFAULT = 42.0
MIN_KNEE_CLEARANCE_WIDTH = 24.0
MIN_KNEE_CLEARANCE_HEIGHT = 24.0
MIN_KNEE_CLEARANCE_DEPTH = 15.0
ADA_KNEE_CLEARANCE_WIDTH = 30.0

# Standard grommet sizes (reuse GrommetSize enum values)
GROMMET_SIZES = [GrommetSize.SMALL.value, GrommetSize.MEDIUM.value, GrommetSize.LARGE.value]


class CornerConnectionType(str, Enum):
    """Types of corner connections for L-shaped desks.

    Defines how two perpendicular desk surfaces connect at the corner.

    Attributes:
        BUTT: 90-degree butt joint connection (surfaces meet at right angle).
        DIAGONAL: 45-degree mitered connection with diagonal face panel.
    """

    BUTT = "butt"
    DIAGONAL = "diagonal"


# L-shaped desk constants
L_SHAPED_CORNER_POST_WIDTH = 3.0  # 3" square corner support post
L_SHAPED_MIN_SURFACE_WIDTH = 36.0  # Minimum surface width for practical use
L_SHAPED_WARNING_THRESHOLD = 60.0  # Warn if > 60" without corner support


@dataclass(frozen=True)
class GrommetSpec:
    """Specification for cable grommet cutout.

    Represents the position and size of a cable grommet cutout
    on a desktop surface.

    Attributes:
        x_position: Distance from left edge of desktop in inches.
        y_position: Distance from front edge of desktop in inches.
        diameter: Grommet diameter in inches.
    """

    x_position: float  # From left edge of desktop
    y_position: float  # From front edge of desktop
    diameter: float    # Grommet diameter in inches

    def __post_init__(self) -> None:
        """Validate grommet specification values."""
        if self.x_position < 0:
            raise ValueError("x_position must be non-negative")
        if self.y_position < 0:
            raise ValueError("y_position must be non-negative")
        if self.diameter <= 0:
            raise ValueError("diameter must be positive")


@dataclass(frozen=True)
class LShapedDeskConfiguration:
    """Configuration for L-shaped desk layout.

    An L-shaped desk consists of two desk surfaces that meet at a corner:
    the main surface (primary work area) and the return surface (secondary
    work area on the perpendicular wall).

    Attributes:
        main_surface_width: Width of main desk surface in inches.
        return_surface_width: Width of return surface in inches.
        main_surface_depth: Depth of main surface (default: 24").
        return_surface_depth: Depth of return surface (can differ from main).
        desk_height: Height of both surfaces in inches (must match).
        corner_type: Connection type - "butt" or "diagonal".
        corner_post: Include vertical support post at corner.
        main_left_pedestal: Pedestal config for main surface left side.
        return_right_pedestal: Pedestal config for return surface right side.
    """

    main_surface_width: float
    return_surface_width: float
    main_surface_depth: float = 24.0
    return_surface_depth: float = 24.0
    desk_height: float = 30.0
    corner_type: Literal["butt", "diagonal"] = "butt"
    corner_post: bool = True
    main_left_pedestal: dict[str, Any] | None = None
    return_right_pedestal: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate L-shaped desk configuration."""
        if self.main_surface_width <= 0:
            raise ValueError("main_surface_width must be positive")
        if self.return_surface_width <= 0:
            raise ValueError("return_surface_width must be positive")
        if self.main_surface_depth <= 0:
            raise ValueError("main_surface_depth must be positive")
        if self.return_surface_depth <= 0:
            raise ValueError("return_surface_depth must be positive")
        if self.desk_height <= 0:
            raise ValueError("desk_height must be positive")
        if self.corner_type not in ("butt", "diagonal"):
            raise ValueError("corner_type must be 'butt' or 'diagonal'")


@component_registry.register("desk.surface")
class DeskSurfaceComponent:
    """Desktop surface panel with optional features.

    Generates horizontal desktop panels with support for:
    - Configurable height (sitting or standing)
    - Multiple depth options (18", 20", 22", 24", 30")
    - Edge treatments (square, bullnose, waterfall, eased)
    - Cable grommet cutouts
    - Floating mount option with wall cleats
    - Edge banding calculation

    Configuration:
        desk_height: float - Height of desk surface (26-50", default: 30")
        depth: float - Desktop depth (default: 24")
        thickness: float - Desktop thickness (default: 1.0")
        edge_treatment: str - Edge type: "square", "bullnose", "waterfall", "eased"
        grommets: list[dict] - Grommet specs with x_position, y_position, diameter
        mounting: str - Mount type: "pedestal", "floating", "legs"
        exposed_left: bool - Edge banding on left edge
        exposed_right: bool - Edge banding on right edge
    """

    VALID_EDGE_TREATMENTS = ("square", "bullnose", "waterfall", "eased")
    STANDARD_DEPTHS = (18.0, 20.0, 22.0, 24.0, 30.0)

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate desk surface configuration.

        Checks:
        - Desk height within valid range (26-50")
        - Warning for heights between sitting and standing ranges
        - Desk depth at least 18"
        - Warning for non-standard depths
        - Desktop thickness at least 0.75"
        - Warning for 3/4" thickness (may flex)
        - Grommet sizes are standard
        - Edge treatment is valid

        Args:
            config: Desk configuration dictionary with optional keys:
                - desk_height: Height of desk surface (default: 30")
                - depth: Desktop depth (default: 24")
                - thickness: Desktop thickness (default: 1.0")
                - grommets: List of grommet specifications
                - edge_treatment: Edge type (default: "square")

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        height = config.get("desk_height", SITTING_DESK_HEIGHT_DEFAULT)
        depth = config.get("depth", 24.0)
        thickness = config.get("thickness", 1.0)

        # Height validation
        if height < 26 or height > 50:
            errors.append(f"Desk height {height}\" outside standard range (26-50\")")
        elif (
            height < SITTING_DESK_HEIGHT_MIN
            or (height > SITTING_DESK_HEIGHT_MAX and height < STANDING_DESK_HEIGHT_MIN)
        ):
            warnings.append(f"Desk height {height}\" between sitting and standing ranges")

        # Depth validation
        if depth < 18:
            errors.append(f"Desk depth {depth}\" too shallow for workspace")
        elif depth > 36:
            errors.append(f"Desk depth {depth}\" exceeds maximum (36\")")
        elif depth not in self.STANDARD_DEPTHS:
            warnings.append(f"Desk depth {depth}\" is non-standard")

        # Thickness validation
        if thickness < 0.75:
            errors.append("Desktop thickness must be at least 0.75\"")
        elif thickness < 1.0:
            warnings.append("3/4\" desktop may flex under heavy loads")

        # Grommet validation
        grommets = config.get("grommets", [])
        for i, grommet in enumerate(grommets):
            diameter = grommet.get("diameter", GrommetSize.MEDIUM.value)
            if diameter not in GROMMET_SIZES and diameter > 3.5:
                errors.append(f"Grommet {i + 1} diameter {diameter}\" not standard")

        # Edge treatment validation
        edge = config.get("edge_treatment", "square")
        if edge not in self.VALID_EDGE_TREATMENTS:
            errors.append(f"Invalid edge treatment '{edge}'")

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate desktop surface panels and hardware.

        Creates:
        - Main desktop panel (PanelType.DESKTOP)
        - Grommet cutouts as PanelCutout in metadata
        - Waterfall edge panel if edge_treatment is "waterfall"
        - Hardware: grommets, edge banding, wall cleats (if floating)

        Args:
            config: Desk configuration dictionary with optional keys:
                - desk_height: Height of desk surface (default: 30")
                - depth: Desktop depth (default: 24")
                - thickness: Desktop thickness (default: 1.0")
                - edge_treatment: Edge type (default: "square")
                - grommets: List of grommet specifications
                - mounting: Mount type (default: "pedestal")
                - exposed_left: Edge banding on left edge
                - exposed_right: Edge banding on right edge

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing desktop panels, hardware requirements,
            and metadata with grommet cutouts and edge treatment.
        """
        width = context.width
        depth = config.get("depth", 24.0)
        thickness = config.get("thickness", 1.0)
        edge_treatment = config.get("edge_treatment", "square")
        grommets = config.get("grommets", [])

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []
        cutouts: list[PanelCutout] = []

        # Main desktop panel
        desktop_panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=width,
            height=depth,  # depth becomes height in 2D panel representation
            material=MaterialSpec(thickness=thickness),
            position=context.position,
            metadata={
                "component": "desk.surface",
                "edge_treatment": edge_treatment,
                "is_desktop": True,
            },
        )
        panels.append(desktop_panel)

        # Grommet cutouts
        for grommet in grommets:
            x_pos = grommet.get("x_position", width / 2)
            y_pos = grommet.get("y_position", depth - 3)  # 3" from back default
            diameter = grommet.get("diameter", GrommetSize.MEDIUM.value)

            cutouts.append(
                PanelCutout(
                    cutout_type="grommet",
                    panel=PanelType.DESKTOP,
                    position=Point2D(x=x_pos, y=y_pos),
                    width=diameter,
                    height=diameter,
                    shape=CutoutShape.CIRCULAR,
                    diameter=diameter,
                    notes=f"Cable grommet {diameter}\" diameter",
                )
            )

            hardware.append(
                HardwareItem(
                    name=f"Cable Grommet {diameter}\"",
                    quantity=1,
                    sku=f"GROMMET-{diameter:.0f}",
                    notes=f"Desk cable grommet, {diameter}\" diameter",
                )
            )

        # Waterfall edge panel
        if edge_treatment == "waterfall":
            desk_height = config.get("desk_height", SITTING_DESK_HEIGHT_DEFAULT)
            waterfall_height = desk_height - 4  # Leave 4" gap at bottom
            panels.append(
                Panel(
                    panel_type=PanelType.WATERFALL_EDGE,
                    width=width,
                    height=waterfall_height,
                    material=MaterialSpec(thickness=thickness),
                    position=Position(context.position.x, 0),
                    metadata={
                        "component": "desk.surface",
                        "is_waterfall_edge": True,
                    },
                )
            )

        # Edge banding calculation
        visible_edges = ["front"]
        if config.get("exposed_left", False):
            visible_edges.append("left")
        if config.get("exposed_right", False):
            visible_edges.append("right")

        edge_banding_length = 0.0
        if "front" in visible_edges:
            edge_banding_length += width
        if "left" in visible_edges:
            edge_banding_length += depth
        if "right" in visible_edges:
            edge_banding_length += depth

        if edge_banding_length > 0:
            hardware.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{edge_banding_length:.1f} linear inches for desktop edges",
                )
            )

        # Wall cleats for floating desk
        if config.get("mounting", "pedestal") == "floating":
            cleat_count = 2 if width <= 48 else 3
            hardware.append(
                HardwareItem(
                    name="French Cleat",
                    quantity=cleat_count,
                    sku="CLEAT-HEAVY",
                    notes="Heavy-duty wall cleat for floating desk",
                )
            )
            hardware.append(
                HardwareItem(
                    name="Lag Screw 3/8\" x 4\"",
                    quantity=cleat_count * 4,
                    notes="For wall cleat mounting into studs",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "cutouts": cutouts,
                "edge_treatment": edge_treatment,
                "desk_height": config.get("desk_height", SITTING_DESK_HEIGHT_DEFAULT),
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for desk surface.

        Desk surfaces require:
        - Cable grommets (1 per cutout)
        - Edge banding (linear footage)
        - Wall cleats if floating mount

        Args:
            config: Desk configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for desk hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


# Import drawer infrastructure for slide length selection
from .drawer import SLIDE_CLEARANCES, VALID_SLIDE_LENGTHS, _auto_select_slide_length


@component_registry.register("desk.pedestal")
class DeskPedestalComponent:
    """Desk pedestal (file drawers, storage drawers, or open shelves).

    Generates the cabinet box structure for desk pedestals with support for:
    - File pedestal: Pencil drawer + file drawer (letter or legal)
    - Storage pedestal: Configurable number of storage drawers
    - Open pedestal: Open shelving without drawers

    Configuration:
        pedestal_type: str - Type: "file", "storage", "open"
        width: float - Pedestal width (12-30", default: 18")
        position: str - "left" or "right" relative to knee clearance
        drawer_count: int - Number of drawers for storage type (default: 3)
        file_type: str - "letter" or "legal" for file pedestal
        desktop_height: float - Height of associated desktop (default: 30")
        desktop_thickness: float - Thickness of desktop (default: 1.0")
        wire_chase: bool - Include wire routing in back panel (default: True)
        shelf_count: int - Number of shelves for open type (default: 2)
    """

    PEDESTAL_TYPES = ("file", "storage", "open")
    STANDARD_WIDTHS = (15.0, 18.0, 21.0, 24.0)

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate pedestal configuration.

        Checks:
        - Pedestal type is valid
        - Width is at least 12" (warning if non-standard)
        - File pedestal requires minimum 15" width
        - Pedestal depth does not exceed available space

        Args:
            config: Pedestal configuration dictionary with optional keys:
                - pedestal_type: Type of pedestal (default: "storage")
                - width: Pedestal width (default: 18.0")

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        pedestal_type = config.get("pedestal_type", "storage")
        width = config.get("width", 18.0)

        # Type validation
        if pedestal_type not in self.PEDESTAL_TYPES:
            errors.append(f"Invalid pedestal type '{pedestal_type}'")

        # Width validation
        if width < 12:
            warnings.append(f"Pedestal width {width}\" may limit drawer options")
        elif width not in self.STANDARD_WIDTHS:
            warnings.append(f"Pedestal width {width}\" is non-standard")

        # File pedestal needs minimum width for file folders
        if pedestal_type == "file" and width < 15:
            errors.append("File pedestal requires minimum 15\" width for file folders")

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate pedestal cabinet box panels and hardware.

        Creates:
        - Left and right side panels
        - Bottom panel
        - Back panel (with optional wire chase cutout)
        - Hardware based on pedestal type

        Does NOT generate drawer panels - that is done by drawer components
        orchestrated at a higher level.

        Args:
            config: Pedestal configuration dictionary with optional keys:
                - pedestal_type: Type of pedestal (default: "storage")
                - width: Pedestal width (default: 18.0")
                - depth: Pedestal depth (default: context.depth)
                - desktop_height: Height of desktop (default: 30.0")
                - desktop_thickness: Desktop thickness (default: 1.0")
                - wire_chase: Include wire routing (default: True)
                - drawer_count: Number of drawers for storage type (default: 3)
                - shelf_count: Number of shelves for open type (default: 2)
                - file_type: "letter" or "legal" for file pedestal (default: "letter")

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing pedestal panels, hardware requirements,
            and metadata with pedestal type and dimensions.
        """
        pedestal_type = config.get("pedestal_type", "storage")
        width = config.get("width", 18.0)
        depth = config.get("depth", context.depth)
        desktop_height = config.get("desktop_height", SITTING_DESK_HEIGHT_DEFAULT)
        desktop_thickness = config.get("desktop_thickness", 1.0)
        wire_chase = config.get("wire_chase", True)

        # Pedestal height is desktop height minus desktop thickness
        pedestal_height = desktop_height - desktop_thickness

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Left side panel
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=depth,
                height=pedestal_height,
                material=context.material,
                position=context.position,
                metadata={"component": "desk.pedestal"},
            )
        )

        # Right side panel
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=depth,
                height=pedestal_height,
                material=context.material,
                position=Position(
                    context.position.x + width - context.material.thickness,
                    context.position.y,
                ),
                metadata={"component": "desk.pedestal"},
            )
        )

        # Bottom panel (inset between sides)
        inner_width = width - 2 * context.material.thickness
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=inner_width,
                height=depth,
                material=context.material,
                position=Position(
                    context.position.x + context.material.thickness, 0
                ),
                metadata={"component": "desk.pedestal"},
            )
        )

        # Back panel (1/4" material)
        back_material = MaterialSpec.standard_1_4()
        back_panel = Panel(
            panel_type=PanelType.BACK,
            width=width,
            height=pedestal_height,
            material=back_material,
            position=context.position,
            metadata={
                "component": "desk.pedestal",
                "wire_chase": wire_chase,
            },
        )
        panels.append(back_panel)

        # Wire chase panel (optional, for cable routing)
        if wire_chase:
            panels.append(
                Panel(
                    panel_type=PanelType.WIRE_CHASE,
                    width=3.0,  # 3" standard wire channel
                    height=pedestal_height,
                    material=back_material,
                    position=Position(
                        context.position.x + width / 2 - 1.5,  # centered
                        context.position.y,
                    ),
                    metadata={
                        "component": "desk.pedestal",
                        "is_wire_chase": True,
                    },
                )
            )

        # Hardware based on pedestal type
        if pedestal_type == "file":
            # File pedestal: pencil drawer (top) + file drawer (bottom)
            file_type = config.get("file_type", "letter")
            hardware.extend([
                HardwareItem(
                    name="Drawer Slide 18\"",
                    quantity=4,  # 2 pair for 2 drawers
                    sku="SLIDE-18-FULL",
                    notes="Full extension slides for file pedestal",
                ),
                HardwareItem(
                    name="Hanging File Frame",
                    quantity=1,
                    sku=f"FILE-FRAME-{file_type.upper()}",
                    notes=f"{file_type.capitalize()}-size hanging file frame",
                ),
                HardwareItem(
                    name="Handle/Pull",
                    quantity=2,
                    sku="HANDLE-DRAWER",
                    notes="Drawer pulls for pencil and file drawers",
                ),
            ])
        elif pedestal_type == "storage":
            drawer_count = config.get("drawer_count", 3)
            slide_length = _auto_select_slide_length(depth)
            hardware.extend([
                HardwareItem(
                    name=f"Drawer Slide {slide_length}\"",
                    quantity=drawer_count * 2,
                    sku=f"SLIDE-{slide_length}-FULL",
                    notes=f"Full extension slides for {drawer_count} drawers",
                ),
                HardwareItem(
                    name="Handle/Pull",
                    quantity=drawer_count,
                    sku="HANDLE-DRAWER",
                    notes=f"Drawer pulls for {drawer_count} drawers",
                ),
            ])
        else:  # pedestal_type == "open"
            shelf_count = config.get("shelf_count", 2)
            hardware.append(
                HardwareItem(
                    name="Shelf Pin",
                    quantity=shelf_count * 4,
                    sku="SP-5MM-BRASS",
                    notes=f"5mm brass shelf pins for {shelf_count} shelves",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "pedestal_type": pedestal_type,
                "pedestal_height": pedestal_height,
                "wire_chase": wire_chase,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for desk pedestal.

        Hardware varies by pedestal type:
        - File: 2 pair drawer slides + file frame + 2 handles
        - Storage: drawer slides + handles (count varies)
        - Open: shelf pins

        Args:
            config: Pedestal configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for pedestal hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("desk.keyboard_tray")
class KeyboardTrayComponent:
    """Pull-out keyboard tray with undermount slides.

    Generates keyboard tray panels with support for:
    - Standard 20" x 10" tray (configurable)
    - Undermount slide hardware
    - Optional enclosure rails for dust protection
    - Optional wrist rest

    Configuration:
        width: float - Tray width (default: 20")
        depth: float - Tray depth (default: 10")
        slide_length: int - Slide length in inches (default: 14")
        enclosed: bool - Add enclosure rails (default: False)
        wrist_rest: bool - Include wrist rest (default: False)
        tray_clearance: float - Space below desktop (default: 2")
        knee_clearance_height: float - Available knee clearance (default: 24")
    """

    STANDARD_WIDTH = 20.0
    STANDARD_DEPTH = 10.0
    MIN_CLEARANCE = 2.0
    TRAY_THICKNESS = 0.75  # 3/4" tray panel
    MIN_EFFECTIVE_KNEE_HEIGHT = 22.0
    ENCLOSURE_HEIGHT = 3.0  # 3" tall enclosure sides
    VALID_SLIDE_LENGTHS = (10, 12, 14, 16, 18, 20)

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate keyboard tray configuration.

        Checks:
        - Tray width does not exceed desk width
        - Knee clearance maintained with tray installed
        - Tray depth is reasonable (8-14")
        - Slide length is valid

        Args:
            config: Keyboard tray configuration dictionary with optional keys:
                - width: Tray width (default: 20")
                - depth: Tray depth (default: 10")
                - knee_clearance_height: Available knee clearance (default: 24")
                - tray_clearance: Space below desktop (default: 2")
                - slide_length: Slide length in inches (default: 14)

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        tray_width = config.get("width", self.STANDARD_WIDTH)
        tray_depth = config.get("depth", self.STANDARD_DEPTH)
        knee_height = config.get("knee_clearance_height", MIN_KNEE_CLEARANCE_HEIGHT)
        tray_clearance = config.get("tray_clearance", self.MIN_CLEARANCE)
        slide_length = config.get("slide_length", 14)

        # Check that tray doesn't compromise knee clearance
        # Tray hangs below desktop: desktop bottom - clearance - tray thickness
        effective_knee_height = knee_height - tray_clearance - self.TRAY_THICKNESS
        if effective_knee_height < self.MIN_EFFECTIVE_KNEE_HEIGHT:
            errors.append(
                f"Keyboard tray reduces knee clearance to {effective_knee_height:.1f}\" "
                f"(minimum {self.MIN_EFFECTIVE_KNEE_HEIGHT}\")"
            )

        # Check tray width
        if tray_width > context.width:
            errors.append(
                f"Keyboard tray width {tray_width}\" exceeds desk width {context.width}\""
            )

        # Validate depth range
        if tray_depth < 8:
            warnings.append(f"Keyboard tray depth {tray_depth}\" may be too shallow")
        elif tray_depth > 14:
            warnings.append(f"Keyboard tray depth {tray_depth}\" unusually deep")

        # Validate slide length
        if slide_length not in self.VALID_SLIDE_LENGTHS:
            errors.append(
                f"Invalid slide_length {slide_length}\". "
                f"Valid lengths: {self.VALID_SLIDE_LENGTHS}"
            )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate keyboard tray panel and hardware.

        Creates:
        - Tray panel (PanelType.KEYBOARD_TRAY)
        - Optional enclosure panels (PanelType.KEYBOARD_ENCLOSURE)
        - Hardware: keyboard slides, optional wrist rest

        Args:
            config: Keyboard tray configuration dictionary with optional keys:
                - width: Tray width (default: 20")
                - depth: Tray depth (default: 10")
                - enclosed: Add enclosure rails (default: False)
                - slide_length: Slide length in inches (default: 14)
                - wrist_rest: Include wrist rest (default: False)

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing keyboard tray panels, hardware requirements,
            and metadata with enclosure and slide information.
        """
        width = config.get("width", self.STANDARD_WIDTH)
        depth = config.get("depth", self.STANDARD_DEPTH)
        enclosed = config.get("enclosed", False)
        slide_length = config.get("slide_length", 14)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Main tray panel
        panels.append(
            Panel(
                panel_type=PanelType.KEYBOARD_TRAY,
                width=width,
                height=depth,  # depth becomes height in 2D panel representation
                material=MaterialSpec.standard_3_4(),
                position=context.position,
                metadata={
                    "component": "desk.keyboard_tray",
                    "is_keyboard_tray": True,
                },
            )
        )

        # Keyboard slide hardware
        hardware.append(
            HardwareItem(
                name=f"Keyboard Slide {slide_length}\"",
                quantity=1,
                sku=f"KB-SLIDE-{slide_length}",
                notes="Undermount keyboard tray slides (pair)",
            )
        )

        # Optional enclosure rails
        if enclosed:
            # Left enclosure rail
            panels.append(
                Panel(
                    panel_type=PanelType.KEYBOARD_ENCLOSURE,
                    width=depth,  # runs front to back
                    height=self.ENCLOSURE_HEIGHT,
                    material=MaterialSpec.standard_1_2(),
                    position=context.position,
                    metadata={
                        "component": "desk.keyboard_tray",
                        "is_enclosure": True,
                        "side": "left",
                    },
                )
            )
            # Right enclosure rail
            panels.append(
                Panel(
                    panel_type=PanelType.KEYBOARD_ENCLOSURE,
                    width=depth,
                    height=self.ENCLOSURE_HEIGHT,
                    material=MaterialSpec.standard_1_2(),
                    position=Position(context.position.x + width, context.position.y),
                    metadata={
                        "component": "desk.keyboard_tray",
                        "is_enclosure": True,
                        "side": "right",
                    },
                )
            )

        # Optional wrist rest
        if config.get("wrist_rest", False):
            hardware.append(
                HardwareItem(
                    name="Keyboard Wrist Rest",
                    quantity=1,
                    sku="WRIST-REST-20",
                    notes="Padded wrist rest for keyboard tray",
                )
            )

        # Mounting screws for slide
        hardware.append(
            HardwareItem(
                name='Mounting Screw #6x1/2"',
                quantity=8,
                sku="SCREW-6-1/2-PAN",
                notes="For keyboard slide mounting",
            )
        )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "enclosed": enclosed,
                "slide_length": slide_length,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for keyboard tray.

        Keyboard trays require:
        - Keyboard slide mechanism (1 pair)
        - Mounting screws
        - Optional wrist rest

        Args:
            config: Keyboard tray configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for keyboard tray hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("desk.monitor_shelf")
class MonitorShelfComponent:
    """Monitor riser shelf above desktop.

    Generates a small shelf unit that sits on or is attached to the desktop
    to raise monitors to a more ergonomic height. Supports:
    - Standard heights: 4", 6", 8" above desktop
    - Cable pass-through in back panel
    - Optional monitor arm mounting point

    Configuration:
        width: float - Shelf width (default: 24")
        height: float - Riser height (default: 6")
        depth: float - Shelf depth (default: 10")
        cable_pass: bool - Include cable pass-through gap (default: True)
        arm_mount: bool - Include monitor arm mounting hardware (default: False)
    """

    STANDARD_HEIGHTS = (4.0, 6.0, 8.0)
    DEFAULT_WIDTH = 24.0
    DEFAULT_DEPTH = 10.0

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate monitor shelf configuration.

        Checks:
        - Riser height is within reasonable range (standard: 4", 6", 8")
        - Shelf width does not exceed desk width
        - Depth is reasonable (6-14")

        Args:
            config: Monitor shelf configuration dictionary with optional keys:
                - height: Riser height (default: 6.0")
                - width: Shelf width (default: 24.0")
                - depth: Shelf depth (default: 10.0")

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        riser_height = config.get("height", 6.0)
        riser_width = config.get("width", self.DEFAULT_WIDTH)
        riser_depth = config.get("depth", self.DEFAULT_DEPTH)

        # Height warning for non-standard
        if riser_height not in self.STANDARD_HEIGHTS:
            warnings.append(
                f"Monitor shelf height {riser_height}\" is non-standard "
                f"(standard: {self.STANDARD_HEIGHTS})"
            )

        # Width validation
        if riser_width > context.width:
            errors.append(
                f"Monitor shelf width {riser_width}\" exceeds desk width {context.width}\""
            )

        # Depth validation
        if riser_depth < 6:
            errors.append(f"Monitor shelf depth {riser_depth}\" too shallow")
        elif riser_depth > 14:
            warnings.append(f"Monitor shelf depth {riser_depth}\" unusually deep")

        # Height range check
        if riser_height < 2:
            errors.append(f"Monitor shelf height {riser_height}\" too short")
        elif riser_height > 12:
            warnings.append(f"Monitor shelf height {riser_height}\" unusually tall")

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate monitor shelf panels and hardware.

        Creates:
        - Top shelf panel (PanelType.SHELF)
        - Left and right side supports (PanelType.LEFT_SIDE, RIGHT_SIDE)
        - Back panel with optional cable pass-through gap (PanelType.BACK)
        - Optional monitor arm mounting hardware

        Args:
            config: Monitor shelf configuration dictionary with optional keys:
                - width: Shelf width (default: 24.0")
                - height: Riser height (default: 6.0")
                - depth: Shelf depth (default: 10.0")
                - cable_pass: Include cable pass-through gap (default: True)
                - arm_mount: Include monitor arm mounting hardware (default: False)

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing monitor shelf panels, hardware requirements,
            and metadata with cable pass-through and arm mount information.
        """
        width = config.get("width", self.DEFAULT_WIDTH)
        height = config.get("height", 6.0)
        depth = config.get("depth", self.DEFAULT_DEPTH)
        has_cable_pass = config.get("cable_pass", True)
        arm_mount = config.get("arm_mount", False)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Top shelf panel
        panels.append(
            Panel(
                panel_type=PanelType.SHELF,
                width=width,
                height=depth,  # depth becomes height in 2D panel representation
                material=context.material,
                position=Position(context.position.x, context.position.y + height),
                metadata={
                    "component": "desk.monitor_shelf",
                    "is_monitor_shelf": True,
                },
            )
        )

        # Left side support
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=depth,
                height=height,
                material=context.material,
                position=context.position,
                metadata={"component": "desk.monitor_shelf"},
            )
        )

        # Right side support
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=depth,
                height=height,
                material=context.material,
                position=Position(
                    context.position.x + width - context.material.thickness,
                    context.position.y,
                ),
                metadata={"component": "desk.monitor_shelf"},
            )
        )

        # Back panel with optional cable pass-through
        if has_cable_pass:
            # Leave 2" gap at bottom for cables
            cable_gap = 2.0
            back_height = height - cable_gap
            back_y_offset = cable_gap
            panels.append(
                Panel(
                    panel_type=PanelType.BACK,
                    width=width,
                    height=back_height,
                    material=MaterialSpec.standard_1_4(),
                    position=Position(
                        context.position.x, context.position.y + back_y_offset
                    ),
                    metadata={
                        "component": "desk.monitor_shelf",
                        "cable_pass": True,
                        "cable_gap": cable_gap,
                    },
                )
            )
        else:
            # Full height back panel
            panels.append(
                Panel(
                    panel_type=PanelType.BACK,
                    width=width,
                    height=height,
                    material=MaterialSpec.standard_1_4(),
                    position=context.position,
                    metadata={"component": "desk.monitor_shelf"},
                )
            )

        # Monitor arm mount hardware
        if arm_mount:
            hardware.append(
                HardwareItem(
                    name="Monitor Arm Through-Desk Mount",
                    quantity=1,
                    sku="MONITOR-ARM-MOUNT",
                    notes="Reinforced through-shelf mount for monitor arm",
                )
            )
            # Reinforcement plate for arm mount
            hardware.append(
                HardwareItem(
                    name="Monitor Arm Reinforcement Plate",
                    quantity=1,
                    sku="ARM-PLATE-6X6",
                    notes="6\" x 6\" steel plate for arm mounting point",
                )
            )

        # Assembly hardware
        hardware.append(
            HardwareItem(
                name='Wood Screw #8x1-1/4"',
                quantity=8,
                sku="SCREW-8-1.25-FH",
                notes="For shelf assembly",
            )
        )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "cable_pass": has_cable_pass,
                "arm_mount": arm_mount,
                "riser_height": height,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for monitor shelf.

        Monitor shelves require:
        - Assembly screws
        - Optional monitor arm mount and reinforcement plate

        Args:
            config: Monitor shelf configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for monitor shelf hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("desk.hutch")
class DeskHutchComponent:
    """Upper storage hutch above desk surface.

    Generates a cabinet unit positioned above the desktop, typically
    mounted to the wall or sitting on the desktop. Supports:
    - Configurable height and depth (shallower than desktop)
    - Adjustable or fixed shelves
    - Optional doors (uses FRD-07 door infrastructure)
    - Task lighting mounting zone at bottom

    Configuration:
        height: float - Hutch height (12-48", default: 24")
        depth: float - Hutch depth (6-16", default: 12")
        head_clearance: float - Space above desktop (default: 15")
        shelf_count: int - Number of interior shelves (default: 1)
        doors: bool - Include doors (default: False)
        task_light_zone: bool - Include task lighting zone (default: True)
    """

    MIN_HEAD_CLEARANCE = 15.0  # inches above desktop
    MIN_DEPTH = 6.0
    MAX_DEPTH = 16.0
    MIN_HEIGHT = 12.0
    MAX_HEIGHT = 48.0
    DEFAULT_HEIGHT = 24.0
    DEFAULT_DEPTH = 12.0

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate hutch configuration.

        Checks:
        - Head clearance is at least 15" (warning if less)
        - Depth is within range (6-16")
        - Deep hutch warning (may interfere with monitor)
        - Height is reasonable (12-48")

        Args:
            config: Hutch configuration dictionary with optional keys:
                - head_clearance: Space above desktop (default: 15")
                - depth: Hutch depth (default: 12")
                - height: Hutch height (default: 24")

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        head_clearance = config.get("head_clearance", self.MIN_HEAD_CLEARANCE)
        hutch_depth = config.get("depth", self.DEFAULT_DEPTH)
        hutch_height = config.get("height", self.DEFAULT_HEIGHT)

        # Head clearance warning
        if head_clearance < self.MIN_HEAD_CLEARANCE:
            warnings.append(
                f"Hutch head clearance {head_clearance}\" may obstruct user "
                f"(minimum recommended: {self.MIN_HEAD_CLEARANCE}\")"
            )

        # Depth validation
        if hutch_depth < self.MIN_DEPTH:
            errors.append(f"Hutch depth must be at least {self.MIN_DEPTH}\"")
        elif hutch_depth > self.MAX_DEPTH:
            warnings.append(
                f"Deep hutch ({hutch_depth}\") may interfere with monitor placement"
            )

        # Height validation
        if hutch_height < self.MIN_HEIGHT:
            errors.append(f"Hutch height {hutch_height}\" too short")
        elif hutch_height > self.MAX_HEIGHT:
            warnings.append(f"Hutch height {hutch_height}\" unusually tall")

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate hutch cabinet box panels and hardware.

        Creates:
        - Side panels (LEFT_SIDE, RIGHT_SIDE)
        - Top panel (TOP)
        - Bottom panel (BOTTOM) with optional task light zone
        - Back panel (BACK)
        - Interior shelves (SHELF)
        - Hardware: shelf pins, hinges (if doors), task light channel

        Args:
            config: Hutch configuration dictionary with optional keys:
                - height: Hutch height (default: 24")
                - depth: Hutch depth (default: 12")
                - shelf_count: Number of interior shelves (default: 1)
                - doors: Include doors (default: False)
                - task_light_zone: Include task lighting zone (default: True)

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing hutch panels, hardware requirements,
            and metadata with shelf count, door status, and task light zone info.
        """
        width = context.width
        height = config.get("height", self.DEFAULT_HEIGHT)
        depth = config.get("depth", self.DEFAULT_DEPTH)
        shelf_count = config.get("shelf_count", 1)
        has_doors = config.get("doors", False)
        has_task_light_zone = config.get("task_light_zone", True)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Left side panel
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=depth,
                height=height,
                material=context.material,
                position=context.position,
                metadata={"component": "desk.hutch"},
            )
        )

        # Right side panel
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=depth,
                height=height,
                material=context.material,
                position=Position(
                    context.position.x + width - context.material.thickness,
                    context.position.y,
                ),
                metadata={"component": "desk.hutch"},
            )
        )

        # Top panel
        panels.append(
            Panel(
                panel_type=PanelType.TOP,
                width=width,
                height=depth,
                material=context.material,
                position=Position(
                    context.position.x,
                    context.position.y + height - context.material.thickness,
                ),
                metadata={"component": "desk.hutch"},
            )
        )

        # Bottom panel (with task light zone metadata)
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=width,
                height=depth,
                material=context.material,
                position=context.position,
                metadata={
                    "component": "desk.hutch",
                    "task_light_zone": has_task_light_zone,
                },
            )
        )

        # Back panel (1/4" material)
        panels.append(
            Panel(
                panel_type=PanelType.BACK,
                width=width,
                height=height,
                material=MaterialSpec.standard_1_4(),
                position=context.position,
                metadata={"component": "desk.hutch"},
            )
        )

        # Interior shelves
        if shelf_count > 0:
            interior_width = width - 2 * context.material.thickness
            shelf_depth = depth - 0.5  # Slight setback from front
            for i in range(shelf_count):
                panels.append(
                    Panel(
                        panel_type=PanelType.SHELF,
                        width=interior_width,
                        height=shelf_depth,
                        material=context.material,
                        position=context.position,
                        metadata={
                            "component": "desk.hutch",
                            "shelf_index": i,
                        },
                    )
                )

            # Shelf pins for adjustable shelves
            hardware.append(
                HardwareItem(
                    name="Shelf Pin",
                    quantity=shelf_count * 4,
                    sku="SP-5MM-BRASS",
                    notes="5mm brass shelf pins for hutch",
                )
            )

        # Task light zone hardware
        if has_task_light_zone:
            hardware.append(
                HardwareItem(
                    name="LED Light Strip Mounting Channel",
                    quantity=1,
                    sku="LED-CHANNEL-48",
                    notes="Aluminum channel for under-hutch LED strip",
                )
            )
            hardware.append(
                HardwareItem(
                    name="LED Light Strip Power Supply",
                    quantity=1,
                    sku="LED-PSU-12V-2A",
                    notes="12V power supply for LED strip",
                )
            )

        # Door hardware (if doors specified)
        if has_doors:
            # Assuming 2 doors for standard hutch
            door_count = 2
            hinges_per_door = 2
            hardware.append(
                HardwareItem(
                    name="European Hinge 110deg",
                    quantity=door_count * hinges_per_door,
                    sku="HINGE-EU-110",
                    notes="Concealed hinges for hutch doors",
                )
            )
            hardware.append(
                HardwareItem(
                    name="Door Handle",
                    quantity=door_count,
                    sku="HANDLE-DOOR",
                    notes="Handles for hutch doors",
                )
            )

        # Assembly hardware
        hardware.append(
            HardwareItem(
                name="Cam Lock",
                quantity=8,
                sku="CAM-LOCK-15MM",
                notes="For hutch assembly",
            )
        )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "shelf_count": shelf_count,
                "has_doors": has_doors,
                "task_light_zone": has_task_light_zone,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for desk hutch.

        Hutch hardware includes:
        - Shelf pins (4 per shelf)
        - Task light channel and power supply (if task light zone)
        - European hinges and handles (if doors)
        - Assembly cam locks

        Args:
            config: Hutch configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for hutch hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("desk.l_shaped")
class LShapedDeskComponent:
    """L-shaped desk configuration with main surface and return surface.

    Generates an L-shaped desk layout consisting of two perpendicular desk
    surfaces that meet at a corner. Supports:
    - Main surface (primary work area)
    - Return surface (secondary work area on perpendicular wall)
    - Corner connection types: butt (90-degree) or diagonal (45-degree)
    - Optional corner support post for stability
    - End pedestals for storage
    - Cable routing accommodation between surfaces

    Configuration:
        main_surface_width: float - Width of main desk surface in inches.
        return_surface_width: float - Width of return surface in inches.
        main_surface_depth: float - Depth of main surface (default: 24").
        return_surface_depth: float - Depth of return surface (default: 24").
        desk_height: float - Height of both surfaces (default: 30").
        corner_connection_type: str - "butt" or "diagonal" (default: "butt").
        corner_post: bool - Include corner support post (default: True).
        main_left_pedestal: dict | None - Pedestal config for main surface left.
        return_right_pedestal: dict | None - Pedestal config for return right.
        edge_treatment: str - Edge type for surfaces (default: "square").

    Panel Generation:
        - Main surface desktop panel (via DeskSurfaceComponent)
        - Return surface desktop panel (via DeskSurfaceComponent)
        - Corner support post (if enabled or diagonal type)
        - Diagonal face panel (if corner_connection_type is "diagonal")
        - Pedestal panels (if pedestals configured)

    Hardware Generation:
        - Corner brackets for butt connection
        - Miter fasteners for diagonal connection
        - Corner post brackets (if corner post enabled)
        - Pedestal hardware (via DeskPedestalComponent)
    """

    VALID_CORNER_TYPES = ("butt", "diagonal")

    def _parse_config(
        self, config: dict[str, Any], context: ComponentContext
    ) -> LShapedDeskConfiguration:
        """Parse L-shaped desk configuration from dict.

        Args:
            config: Component configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            LShapedDeskConfiguration with validated values.
        """
        main_width = config.get("main_surface_width", context.width)
        return_width = config.get("return_surface_width", context.width * 0.75)
        main_depth = config.get("main_surface_depth", 24.0)
        return_depth = config.get("return_surface_depth", 24.0)
        desk_height = config.get("desk_height", SITTING_DESK_HEIGHT_DEFAULT)
        corner_type = config.get("corner_connection_type", "butt")
        corner_post = config.get("corner_post", True)
        main_left_pedestal = config.get("main_left_pedestal")
        return_right_pedestal = config.get("return_right_pedestal")

        return LShapedDeskConfiguration(
            main_surface_width=main_width,
            return_surface_width=return_width,
            main_surface_depth=main_depth,
            return_surface_depth=return_depth,
            desk_height=desk_height,
            corner_type=corner_type,
            corner_post=corner_post,
            main_left_pedestal=main_left_pedestal,
            return_right_pedestal=return_right_pedestal,
        )

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate L-shaped desk configuration.

        Checks:
        - Main surface dimensions are valid
        - Return surface dimensions are valid
        - Corner connection type is valid
        - Desk height is within ergonomic range
        - Warning if large L-shaped desk without corner support

        Args:
            config: L-shaped desk configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Parse configuration
        try:
            l_config = self._parse_config(config, context)
        except ValueError as e:
            errors.append(str(e))
            return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

        # Validate corner connection type
        if l_config.corner_type not in self.VALID_CORNER_TYPES:
            errors.append(
                f"Invalid corner_connection_type '{l_config.corner_type}'. "
                f"Must be one of: {self.VALID_CORNER_TYPES}"
            )

        # Validate main surface dimensions
        if l_config.main_surface_width < L_SHAPED_MIN_SURFACE_WIDTH:
            warnings.append(
                f"Main surface width {l_config.main_surface_width}\" is narrow. "
                f"Minimum recommended: {L_SHAPED_MIN_SURFACE_WIDTH}\""
            )

        if l_config.main_surface_depth < 18:
            errors.append(
                f"Main surface depth {l_config.main_surface_depth}\" too shallow. "
                "Minimum depth: 18\""
            )

        # Validate return surface dimensions
        if l_config.return_surface_width < L_SHAPED_MIN_SURFACE_WIDTH:
            warnings.append(
                f"Return surface width {l_config.return_surface_width}\" is narrow. "
                f"Minimum recommended: {L_SHAPED_MIN_SURFACE_WIDTH}\""
            )

        if l_config.return_surface_depth < 18:
            errors.append(
                f"Return surface depth {l_config.return_surface_depth}\" too shallow. "
                "Minimum depth: 18\""
            )

        # Validate desk height
        if l_config.desk_height < 26 or l_config.desk_height > 50:
            errors.append(
                f"Desk height {l_config.desk_height}\" outside standard range (26-50\")"
            )
        elif (
            l_config.desk_height < SITTING_DESK_HEIGHT_MIN
            or (
                l_config.desk_height > SITTING_DESK_HEIGHT_MAX
                and l_config.desk_height < STANDING_DESK_HEIGHT_MIN
            )
        ):
            warnings.append(
                f"Desk height {l_config.desk_height}\" between sitting and standing ranges"
            )

        # Warning for large L-shaped without corner support
        total_span = l_config.main_surface_width + l_config.return_surface_width
        if total_span > L_SHAPED_WARNING_THRESHOLD * 2 and not l_config.corner_post:
            warnings.append(
                f"Large L-shaped desk (total span {total_span:.0f}\") without corner "
                "support may flex. Consider enabling corner_post."
            )

        # Warning for diagonal without corner post
        if l_config.corner_type == "diagonal" and not l_config.corner_post:
            warnings.append(
                "Diagonal corner connection typically requires corner support post. "
                "Consider enabling corner_post."
            )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate L-shaped desk panels and hardware.

        Creates:
        - Main surface panels (via DeskSurfaceComponent)
        - Return surface panels (via DeskSurfaceComponent)
        - Corner support post panel (if enabled or diagonal type)
        - Diagonal face panel (if corner_connection_type is "diagonal")
        - End pedestal panels (if configured)

        Args:
            config: L-shaped desk configuration dictionary.
            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing all panels, hardware requirements,
            and metadata with L-shaped desk configuration.
        """
        l_config = self._parse_config(config, context)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []
        all_metadata: dict[str, Any] = {
            "desk_type": "l_shaped",
            "corner_type": l_config.corner_type,
            "main_surface_width": l_config.main_surface_width,
            "return_surface_width": l_config.return_surface_width,
        }

        edge_treatment = config.get("edge_treatment", "square")
        thickness = config.get("thickness", 1.0)

        # Generate main surface
        main_surface = DeskSurfaceComponent()
        main_config = {
            "desk_height": l_config.desk_height,
            "depth": l_config.main_surface_depth,
            "edge_treatment": edge_treatment,
            "thickness": thickness,
            "exposed_right": False,  # Corner connection
        }
        main_context = ComponentContext(
            width=l_config.main_surface_width,
            height=context.height,
            depth=l_config.main_surface_depth,
            position=Position(0, 0),
            material=context.material,
            section_index=context.section_index,
            cabinet_width=context.cabinet_width,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )
        main_result = main_surface.generate(main_config, main_context)
        # Tag main surface panels
        for panel in main_result.panels:
            tagged_panel = Panel(
                panel_type=panel.panel_type,
                width=panel.width,
                height=panel.height,
                material=panel.material,
                position=panel.position,
                metadata={
                    **panel.metadata,
                    "l_shaped_surface": "main",
                    "component": "desk.l_shaped",
                },
            )
            panels.append(tagged_panel)
        hardware.extend(main_result.hardware)

        # Calculate return surface position
        # For butt joint: return surface starts at main_width - return_depth
        # For diagonal: return surface position accounts for diagonal face
        if l_config.corner_type == "butt":
            return_x = l_config.main_surface_width - l_config.return_surface_depth
        else:  # diagonal
            # For diagonal, surfaces overlap less at the corner
            # cos(45) = 0.707, so offset is reduced
            return_x = (
                l_config.main_surface_width - l_config.return_surface_depth * 0.707
            )

        # Generate return surface
        return_surface = DeskSurfaceComponent()
        return_config = {
            "desk_height": l_config.desk_height,
            "depth": l_config.return_surface_depth,
            "edge_treatment": edge_treatment,
            "thickness": thickness,
            "exposed_left": False,  # Corner connection
        }
        return_context = ComponentContext(
            width=l_config.return_surface_width,
            height=context.height,
            depth=l_config.return_surface_depth,
            position=Position(return_x, 0),
            material=context.material,
            section_index=context.section_index,
            cabinet_width=context.cabinet_width,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )
        return_result = return_surface.generate(return_config, return_context)
        # Tag return surface panels
        for panel in return_result.panels:
            tagged_panel = Panel(
                panel_type=panel.panel_type,
                width=panel.width,
                height=panel.height,
                material=panel.material,
                position=panel.position,
                metadata={
                    **panel.metadata,
                    "l_shaped_surface": "return",
                    "component": "desk.l_shaped",
                },
            )
            panels.append(tagged_panel)
        hardware.extend(return_result.hardware)

        # Corner support post (if diagonal or explicitly requested)
        if l_config.corner_post or l_config.corner_type == "diagonal":
            post_width = L_SHAPED_CORNER_POST_WIDTH
            post_height = l_config.desk_height - thickness
            panels.append(
                Panel(
                    panel_type=PanelType.DIVIDER,  # Reuse divider for vertical post
                    width=post_width,
                    height=post_height,
                    material=context.material,
                    position=Position(
                        l_config.main_surface_width - post_width / 2, 0
                    ),
                    metadata={
                        "component": "desk.l_shaped",
                        "is_corner_post": True,
                        "corner_type": l_config.corner_type,
                    },
                )
            )
            hardware.append(
                HardwareItem(
                    name="Corner Post Bracket",
                    quantity=2,
                    sku="POST-BRACKET-L",
                    notes="L-brackets for corner support post",
                )
            )
            all_metadata["corner_post_enabled"] = True

        # Diagonal corner face panel (if diagonal type)
        if l_config.corner_type == "diagonal":
            # Create 45-degree diagonal face panel
            # diagonal_width = depth * sqrt(2) for 45-degree angle
            diagonal_width = l_config.main_surface_depth * 1.414
            panels.append(
                Panel(
                    panel_type=PanelType.DIAGONAL_FACE,
                    width=diagonal_width,
                    height=l_config.desk_height - thickness,
                    material=context.material,
                    position=Position(
                        l_config.main_surface_width - l_config.main_surface_depth, 0
                    ),
                    metadata={
                        "component": "desk.l_shaped",
                        "is_diagonal": True,
                        "angle": 45.0,
                    },
                )
            )
            # Miter fasteners for diagonal connection
            hardware.append(
                HardwareItem(
                    name="Miter Bolt",
                    quantity=4,
                    sku="MITER-BOLT-6",
                    notes="6mm miter bolts for diagonal corner connection",
                )
            )
            all_metadata["diagonal_face_width"] = diagonal_width
        else:
            # Butt joint hardware - corner brackets
            hardware.append(
                HardwareItem(
                    name="Corner Bracket",
                    quantity=4,
                    sku="BRACKET-CORNER-90",
                    notes="90-degree corner brackets for butt joint connection",
                )
            )

        # Cable routing accommodation at corner
        hardware.append(
            HardwareItem(
                name="Cable Grommet 2\"",
                quantity=1,
                sku="GROMMET-2",
                notes="Corner cable routing grommet between surfaces",
            )
        )

        # End pedestals
        if l_config.main_left_pedestal:
            pedestal = DeskPedestalComponent()
            ped_config = {
                **l_config.main_left_pedestal,
                "desktop_height": l_config.desk_height,
            }
            ped_width = l_config.main_left_pedestal.get("width", 18.0)
            ped_context = ComponentContext(
                width=ped_width,
                height=context.height,
                depth=l_config.main_surface_depth,
                position=Position(0, 0),
                material=context.material,
                section_index=context.section_index,
                cabinet_width=context.cabinet_width,
                cabinet_height=context.cabinet_height,
                cabinet_depth=context.cabinet_depth,
            )
            ped_result = pedestal.generate(ped_config, ped_context)
            # Tag pedestal panels
            for panel in ped_result.panels:
                tagged_panel = Panel(
                    panel_type=panel.panel_type,
                    width=panel.width,
                    height=panel.height,
                    material=panel.material,
                    position=panel.position,
                    metadata={
                        **panel.metadata,
                        "l_shaped_pedestal": "main_left",
                        "component": "desk.l_shaped",
                    },
                )
                panels.append(tagged_panel)
            hardware.extend(ped_result.hardware)
            all_metadata["main_left_pedestal"] = True

        if l_config.return_right_pedestal:
            pedestal = DeskPedestalComponent()
            ped_config = {
                **l_config.return_right_pedestal,
                "desktop_height": l_config.desk_height,
            }
            ped_width = l_config.return_right_pedestal.get("width", 18.0)
            # Position at right end of return surface
            ped_x = return_x + l_config.return_surface_width - ped_width
            ped_context = ComponentContext(
                width=ped_width,
                height=context.height,
                depth=l_config.return_surface_depth,
                position=Position(ped_x, 0),
                material=context.material,
                section_index=context.section_index,
                cabinet_width=context.cabinet_width,
                cabinet_height=context.cabinet_height,
                cabinet_depth=context.cabinet_depth,
            )
            ped_result = pedestal.generate(ped_config, ped_context)
            # Tag pedestal panels
            for panel in ped_result.panels:
                tagged_panel = Panel(
                    panel_type=panel.panel_type,
                    width=panel.width,
                    height=panel.height,
                    material=panel.material,
                    position=panel.position,
                    metadata={
                        **panel.metadata,
                        "l_shaped_pedestal": "return_right",
                        "component": "desk.l_shaped",
                    },
                )
                panels.append(tagged_panel)
            hardware.extend(ped_result.hardware)
            all_metadata["return_right_pedestal"] = True

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata=all_metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for L-shaped desk.

        Hardware includes:
        - Corner brackets (butt connection) or miter bolts (diagonal)
        - Corner post brackets (if corner post enabled)
        - Cable routing grommet
        - Pedestal hardware (if pedestals configured)

        Args:
            config: L-shaped desk configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for L-shaped desk hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)
