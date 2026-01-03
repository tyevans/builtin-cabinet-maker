"""L-shaped desk component (FRD-18)."""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .config import LShapedDeskConfiguration
from .constants import (
    L_SHAPED_CORNER_POST_WIDTH,
    L_SHAPED_MIN_SURFACE_WIDTH,
    L_SHAPED_WARNING_THRESHOLD,
    SITTING_DESK_HEIGHT_DEFAULT,
    SITTING_DESK_HEIGHT_MAX,
    SITTING_DESK_HEIGHT_MIN,
    STANDING_DESK_HEIGHT_MIN,
)
from .pedestal import DeskPedestalComponent
from .surface import DeskSurfaceComponent


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
                f'Main surface width {l_config.main_surface_width}" is narrow. '
                f'Minimum recommended: {L_SHAPED_MIN_SURFACE_WIDTH}"'
            )

        if l_config.main_surface_depth < 18:
            errors.append(
                f'Main surface depth {l_config.main_surface_depth}" too shallow. '
                'Minimum depth: 18"'
            )

        # Validate return surface dimensions
        if l_config.return_surface_width < L_SHAPED_MIN_SURFACE_WIDTH:
            warnings.append(
                f'Return surface width {l_config.return_surface_width}" is narrow. '
                f'Minimum recommended: {L_SHAPED_MIN_SURFACE_WIDTH}"'
            )

        if l_config.return_surface_depth < 18:
            errors.append(
                f'Return surface depth {l_config.return_surface_depth}" too shallow. '
                'Minimum depth: 18"'
            )

        # Validate desk height
        if l_config.desk_height < 26 or l_config.desk_height > 50:
            errors.append(
                f'Desk height {l_config.desk_height}" outside standard range (26-50")'
            )
        elif l_config.desk_height < SITTING_DESK_HEIGHT_MIN or (
            l_config.desk_height > SITTING_DESK_HEIGHT_MAX
            and l_config.desk_height < STANDING_DESK_HEIGHT_MIN
        ):
            warnings.append(
                f'Desk height {l_config.desk_height}" between sitting and standing ranges'
            )

        # Warning for large L-shaped without corner support
        total_span = l_config.main_surface_width + l_config.return_surface_width
        if total_span > L_SHAPED_WARNING_THRESHOLD * 2 and not l_config.corner_post:
            warnings.append(
                f'Large L-shaped desk (total span {total_span:.0f}") without corner '
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
                    position=Position(l_config.main_surface_width - post_width / 2, 0),
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
                name='Cable Grommet 2"',
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
