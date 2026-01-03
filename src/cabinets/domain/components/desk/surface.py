"""Desktop surface component (FRD-18)."""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import (
    CutoutShape,
    GrommetSize,
    MaterialSpec,
    PanelCutout,
    PanelType,
    Point2D,
    Position,
)
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .constants import (
    GROMMET_SIZES,
    SITTING_DESK_HEIGHT_DEFAULT,
    SITTING_DESK_HEIGHT_MAX,
    SITTING_DESK_HEIGHT_MIN,
    STANDING_DESK_HEIGHT_MIN,
)


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
            errors.append(f'Desk height {height}" outside standard range (26-50")')
        elif height < SITTING_DESK_HEIGHT_MIN or (
            height > SITTING_DESK_HEIGHT_MAX and height < STANDING_DESK_HEIGHT_MIN
        ):
            warnings.append(
                f'Desk height {height}" between sitting and standing ranges'
            )

        # Depth validation
        if depth < 18:
            errors.append(f'Desk depth {depth}" too shallow for workspace')
        elif depth > 36:
            errors.append(f'Desk depth {depth}" exceeds maximum (36")')
        elif depth not in self.STANDARD_DEPTHS:
            warnings.append(f'Desk depth {depth}" is non-standard')

        # Thickness validation
        if thickness < 0.75:
            errors.append('Desktop thickness must be at least 0.75"')
        elif thickness < 1.0:
            warnings.append('3/4" desktop may flex under heavy loads')

        # Grommet validation
        grommets = config.get("grommets", [])
        for i, grommet in enumerate(grommets):
            diameter = grommet.get("diameter", GrommetSize.MEDIUM.value)
            if diameter not in GROMMET_SIZES and diameter > 3.5:
                errors.append(f'Grommet {i + 1} diameter {diameter}" not standard')

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
                    notes=f'Cable grommet {diameter}" diameter',
                )
            )

            hardware.append(
                HardwareItem(
                    name=f'Cable Grommet {diameter}"',
                    quantity=1,
                    sku=f"GROMMET-{diameter:.0f}",
                    notes=f'Desk cable grommet, {diameter}" diameter',
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
                    name='Lag Screw 3/8" x 4"',
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
