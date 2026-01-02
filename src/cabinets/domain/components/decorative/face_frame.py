"""Face frame component for cabinet fronts.

This module provides FaceFrameComponent for generating stile/rail face frames.
"""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import MaterialSpec, PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .configs import FaceFrameConfig
from .enums import JoineryType


@component_registry.register("decorative.face_frame")
class FaceFrameComponent:
    """Face frame component for cabinet fronts.

    Generates stile (vertical) and rail (horizontal) members that form
    a frame around the cabinet opening. Face frames are used with
    traditional cabinet construction to provide a finished appearance
    and mounting surface for doors and hinges.

    Configuration:
        stile_width: Width of vertical stiles in inches (default: 1.5).
        rail_width: Width of horizontal rails in inches (default: 1.5).
        joinery: Joint type - pocket_screw, mortise_tenon, or dowel.
        material_thickness: Thickness of frame material (default: 0.75).

    Generated Pieces:
        - Left stile (full cabinet height)
        - Right stile (full cabinet height)
        - Top rail (width between stiles)
        - Bottom rail (width between stiles)

    Hardware:
        - Pocket screws (8 for pocket_screw joinery)
        - Dowel pins (8 for dowel joinery)
        - None for mortise_tenon (integral wood joint)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate face frame configuration.

        Checks:
        - stile_width is positive and not too large (FR-03.5)
        - rail_width is positive
        - Cabinet width can accommodate stiles with minimum opening
        - Cabinet height can accommodate rails with minimum opening

        Args:
            config: Face frame configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Get raw config values for validation before parsing
        face_frame_config = config.get("face_frame", {})
        stile_width = face_frame_config.get("stile_width", 1.5)
        rail_width = face_frame_config.get("rail_width", 1.5)

        # FR-03.5: Validate stile width
        if stile_width <= 0:
            errors.append("stile_width must be positive")
        elif stile_width > context.width / 4:
            errors.append(
                f'stile_width {stile_width}" too large for '
                f'{context.width}" cabinet width'
            )

        # Validate rail width
        if rail_width <= 0:
            errors.append("rail_width must be positive")
        elif rail_width > context.height / 4:
            errors.append(
                f'rail_width {rail_width}" too large for '
                f'{context.height}" cabinet height'
            )

        # Check for minimum opening (only if dimensions are valid)
        if not errors:
            opening_width = context.width - (2 * stile_width)
            opening_height = context.height - (2 * rail_width)

            if opening_width < 6.0:
                errors.append(
                    f'Opening width {opening_width:.1f}" is less than 6" minimum'
                )
            if opening_height < 6.0:
                errors.append(
                    f'Opening height {opening_height:.1f}" is less than 6" minimum'
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> FaceFrameConfig:
        """Parse configuration dictionary into FaceFrameConfig.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            FaceFrameConfig with parsed values or defaults.
        """
        face_frame_config = config.get("face_frame", {})

        # Map joinery string to enum
        joinery_str = face_frame_config.get("joinery", "pocket_screw")
        joinery = JoineryType(joinery_str)

        return FaceFrameConfig(
            stile_width=face_frame_config.get("stile_width", 1.5),
            rail_width=face_frame_config.get("rail_width", 1.5),
            joinery=joinery,
            material_thickness=face_frame_config.get("material_thickness", 0.75),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate face frame panels.

        Creates Panel entities for:
        - Left stile (full height)
        - Right stile (full height)
        - Top rail (between stiles)
        - Bottom rail (between stiles)

        Args:
            config: Face frame configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with panels, hardware, and metadata.
        """
        frame_config = self._parse_config(config)
        panels: list[Panel] = []

        # Material for face frame pieces
        material = MaterialSpec(
            thickness=frame_config.material_thickness,
        )

        # Calculate dimensions
        rail_length = context.width - (2 * frame_config.stile_width)

        # Left stile (full height)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_STILE,
                width=frame_config.stile_width,
                height=context.height,
                material=material,
                position=Position(context.position.x, context.position.y),
                metadata={
                    "location": "left",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Right stile (full height)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_STILE,
                width=frame_config.stile_width,
                height=context.height,
                material=material,
                position=Position(
                    context.position.x + context.width - frame_config.stile_width,
                    context.position.y,
                ),
                metadata={
                    "location": "right",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Top rail (between stiles)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_RAIL,
                width=rail_length,
                height=frame_config.rail_width,
                material=material,
                position=Position(
                    context.position.x + frame_config.stile_width,
                    context.position.y + context.height - frame_config.rail_width,
                ),
                metadata={
                    "location": "top",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Bottom rail (between stiles)
        panels.append(
            Panel(
                panel_type=PanelType.FACE_FRAME_RAIL,
                width=rail_length,
                height=frame_config.rail_width,
                material=material,
                position=Position(
                    context.position.x + frame_config.stile_width,
                    context.position.y,
                ),
                metadata={
                    "location": "bottom",
                    "joinery_type": frame_config.joinery.value,
                },
            )
        )

        # Get hardware
        hardware = self.hardware(config, context)

        # Metadata includes opening dimensions for door component coordination
        metadata = {
            "opening_width": frame_config.opening_width(context.width),
            "opening_height": frame_config.opening_height(context.height),
            "stile_width": frame_config.stile_width,
            "rail_width": frame_config.rail_width,
            "joinery_type": frame_config.joinery.value,
        }

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for face frame.

        Hardware depends on joinery type:
        - pocket_screw: 8 pocket screws (2 per corner)
        - dowel: 8 dowel pins (2 per corner)
        - mortise_tenon: None (integral wood joint)

        Args:
            config: Face frame configuration.
            context: Component context.

        Returns:
            List of HardwareItem objects.
        """
        frame_config = self._parse_config(config)
        items: list[HardwareItem] = []

        if frame_config.joinery == JoineryType.POCKET_SCREW:
            items.append(
                HardwareItem(
                    name='Pocket Screw 1-1/4"',
                    quantity=8,
                    sku="KJ-PS-125",
                    notes="2 screws per corner, 4 corners",
                )
            )
        elif frame_config.joinery == JoineryType.DOWEL:
            items.append(
                HardwareItem(
                    name='Dowel Pin 3/8" x 2"',
                    quantity=8,
                    sku="DP-375-2",
                    notes="2 dowels per corner, 4 corners",
                )
            )
        # mortise_tenon needs no hardware

        return items
