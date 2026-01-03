"""Keyboard tray component (FRD-18)."""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import MaterialSpec, PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .constants import MIN_KNEE_CLEARANCE_HEIGHT


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
                f'Keyboard tray reduces knee clearance to {effective_knee_height:.1f}" '
                f'(minimum {self.MIN_EFFECTIVE_KNEE_HEIGHT}")'
            )

        # Check tray width
        if tray_width > context.width:
            errors.append(
                f'Keyboard tray width {tray_width}" exceeds desk width {context.width}"'
            )

        # Validate depth range
        if tray_depth < 8:
            warnings.append(f'Keyboard tray depth {tray_depth}" may be too shallow')
        elif tray_depth > 14:
            warnings.append(f'Keyboard tray depth {tray_depth}" unusually deep')

        # Validate slide length
        if slide_length not in self.VALID_SLIDE_LENGTHS:
            errors.append(
                f'Invalid slide_length {slide_length}". '
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
                name=f'Keyboard Slide {slide_length}"',
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
