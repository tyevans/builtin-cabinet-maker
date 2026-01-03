"""Desk hutch component (FRD-18)."""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import MaterialSpec, PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult


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
                f'Hutch head clearance {head_clearance}" may obstruct user '
                f'(minimum recommended: {self.MIN_HEAD_CLEARANCE}")'
            )

        # Depth validation
        if hutch_depth < self.MIN_DEPTH:
            errors.append(f'Hutch depth must be at least {self.MIN_DEPTH}"')
        elif hutch_depth > self.MAX_DEPTH:
            warnings.append(
                f'Deep hutch ({hutch_depth}") may interfere with monitor placement'
            )

        # Height validation
        if hutch_height < self.MIN_HEIGHT:
            errors.append(f'Hutch height {hutch_height}" too short')
        elif hutch_height > self.MAX_HEIGHT:
            warnings.append(f'Hutch height {hutch_height}" unusually tall')

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
