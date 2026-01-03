"""Desk pedestal component (FRD-18)."""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import MaterialSpec, PanelType, Position
from ..context import ComponentContext
from ..drawer import _auto_select_slide_length
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .constants import SITTING_DESK_HEIGHT_DEFAULT


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
            warnings.append(f'Pedestal width {width}" may limit drawer options')
        elif width not in self.STANDARD_WIDTHS:
            warnings.append(f'Pedestal width {width}" is non-standard')

        # File pedestal needs minimum width for file folders
        if pedestal_type == "file" and width < 15:
            errors.append('File pedestal requires minimum 15" width for file folders')

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
                position=Position(context.position.x + context.material.thickness, 0),
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
            hardware.extend(
                [
                    HardwareItem(
                        name='Drawer Slide 18"',
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
                ]
            )
        elif pedestal_type == "storage":
            drawer_count = config.get("drawer_count", 3)
            slide_length = _auto_select_slide_length(depth)
            hardware.extend(
                [
                    HardwareItem(
                        name=f'Drawer Slide {slide_length}"',
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
                ]
            )
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
