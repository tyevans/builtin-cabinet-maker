"""Monitor shelf component (FRD-18)."""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import MaterialSpec, PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult


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
                f'Monitor shelf height {riser_height}" is non-standard '
                f"(standard: {self.STANDARD_HEIGHTS})"
            )

        # Width validation
        if riser_width > context.width:
            errors.append(
                f'Monitor shelf width {riser_width}" exceeds desk width {context.width}"'
            )

        # Depth validation
        if riser_depth < 6:
            errors.append(f'Monitor shelf depth {riser_depth}" too shallow')
        elif riser_depth > 14:
            warnings.append(f'Monitor shelf depth {riser_depth}" unusually deep')

        # Height range check
        if riser_height < 2:
            errors.append(f'Monitor shelf height {riser_height}" too short')
        elif riser_height > 12:
            warnings.append(f'Monitor shelf height {riser_height}" unusually tall')

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
                    notes='6" x 6" steel plate for arm mounting point',
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
