"""Countertop surface component for FRD-22 Countertops and Vertical Zones.

This component generates countertop panels with configurable overhang,
edge treatments, and support brackets for large overhangs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..entities import Panel
from ..value_objects import (
    CountertopEdgeType,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult


# Standard countertop dimensions (inches)
MIN_THICKNESS = 0.5
MAX_THICKNESS = 2.0
DEFAULT_THICKNESS = 1.0
MAX_UNSUPPORTED_OVERHANG = 12.0
MAX_SUPPORTED_OVERHANG = 24.0
SUPPORT_BRACKET_SPACING = 24.0
MIN_BRACKET_WIDTH = 12.0
MIN_BRACKET_DEPTH = 8.0


@dataclass(frozen=True)
class OverhangSpec:
    """Specification for countertop overhang.

    Attributes:
        front: Front overhang in inches (typically 1" for standard countertops).
        left: Left side overhang in inches (0 if against wall).
        right: Right side overhang in inches (0 if against wall).
        back: Back overhang in inches (typically 0, abuts wall).
    """

    front: float = 1.0
    left: float = 0.0
    right: float = 0.0
    back: float = 0.0


@component_registry.register("countertop.surface")
class CountertopSurfaceComponent:
    """Countertop surface spanning cabinet base zones.

    This component generates:
    - Main countertop panel with specified thickness and overhangs
    - Optional waterfall edge panel (vertical panel at front)
    - Support brackets for large overhangs (>12")
    - Edge banding specifications for visible edges

    Configuration:
        thickness: float - Countertop thickness (default: 1.0")
        front_overhang: float - Front overhang in inches (default: 1.0")
        left_overhang: float - Left side overhang (default: 0.0")
        right_overhang: float - Right side overhang (default: 0.0")
        back_overhang: float - Back overhang (default: 0.0")
        edge_treatment: str - Edge type: "square", "eased", "bullnose",
                             "beveled", "waterfall" (default: "square")
        support_brackets: bool - Force support brackets (default: False)
        waterfall_height: float - Height for waterfall edge (default: 34.5")
        bracket_size: tuple[float, float] - Bracket dimensions (default: (12, 8))
        material: dict - Material specification override
        intermediate_support: bool - Has center support for long spans
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate countertop configuration.

        Checks:
        - Thickness within allowed range (0.5" - 2.0")
        - Overhang within safe limits (max 24" with support)
        - Support brackets required for overhangs > 12"
        - Waterfall edge requires front overhang
        - Long spans may need center support

        Args:
            config: Countertop configuration dictionary with optional keys:
                - thickness: Countertop thickness (default: 1.0")
                - front_overhang: Front overhang (default: 1.0")
                - left_overhang: Left side overhang (default: 0.0")
                - right_overhang: Right side overhang (default: 0.0")
                - edge_treatment: Edge type (default: "square")
                - support_brackets: Force support brackets (default: False)
                - intermediate_support: Has center support (default: False)

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        thickness = config.get("thickness", DEFAULT_THICKNESS)
        front_overhang = config.get("front_overhang", 1.0)
        edge_treatment = config.get("edge_treatment", "square")

        # Thickness validation
        if thickness < MIN_THICKNESS:
            errors.append(
                f'Countertop thickness {thickness}" too thin for structural integrity '
                f'(minimum: {MIN_THICKNESS}")'
            )
        if thickness > MAX_THICKNESS:
            errors.append(
                f'Countertop thickness {thickness}" exceeds maximum ({MAX_THICKNESS}")'
            )

        # Overhang validation
        if front_overhang > MAX_SUPPORTED_OVERHANG:
            errors.append(
                f'Front overhang {front_overhang}" exceeds safe span '
                f'(maximum: {MAX_SUPPORTED_OVERHANG}")'
            )
        elif front_overhang > MAX_UNSUPPORTED_OVERHANG:
            if not config.get("support_brackets", False):
                warnings.append(
                    f'Front overhang {front_overhang}" requires support brackets. '
                    'Add "support_brackets": true to configuration.'
                )

        # Left/right overhang validation
        left_overhang = config.get("left_overhang", 0.0)
        right_overhang = config.get("right_overhang", 0.0)
        if left_overhang > 6.0:
            warnings.append(
                f'Left overhang {left_overhang}" is large. Consider support if exposed.'
            )
        if right_overhang > 6.0:
            warnings.append(
                f'Right overhang {right_overhang}" is large. Consider support if exposed.'
            )

        # Edge treatment validation
        valid_treatments = [e.value for e in CountertopEdgeType]
        if edge_treatment not in valid_treatments:
            errors.append(
                f"Invalid edge treatment '{edge_treatment}'. "
                f"Valid options: {valid_treatments}"
            )
        if edge_treatment == "waterfall" and front_overhang < 1.0:
            errors.append('Waterfall edge requires front overhang >= 1"')

        # Span validation
        span = context.width
        if span > 96 and not config.get("intermediate_support", False):
            warnings.append(
                f'Countertop span {span}" may sag without center support. '
                "Consider adding intermediate support."
            )

        return ValidationResult(
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate countertop panels and hardware.

        Creates:
        - Main countertop panel (PanelType.COUNTERTOP)
        - Waterfall edge panel if edge_treatment is "waterfall"
        - Support brackets for large overhangs (>12")
        - Edge banding specifications for visible edges

        Args:
            config: Countertop configuration dictionary with optional keys:
                - thickness: Countertop thickness (default: 1.0")
                - front_overhang: Front overhang (default: 1.0")
                - left_overhang: Left side overhang (default: 0.0")
                - right_overhang: Right side overhang (default: 0.0")
                - back_overhang: Back overhang (default: 0.0")
                - edge_treatment: Edge type (default: "square")
                - support_brackets: Force support brackets (default: False)
                - waterfall_height: Waterfall edge height (default: 34.5")
                - bracket_size: Bracket dimensions (default: (12, 8))
                - material: Material specification override

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing countertop panels, hardware requirements,
            and metadata with edge treatment and dimension information.
        """
        thickness = config.get("thickness", DEFAULT_THICKNESS)
        front_overhang = config.get("front_overhang", 1.0)
        left_overhang = config.get("left_overhang", 0.0)
        right_overhang = config.get("right_overhang", 0.0)
        back_overhang = config.get("back_overhang", 0.0)
        edge_treatment = config.get("edge_treatment", "square")

        # Total countertop dimensions
        total_width = context.width + left_overhang + right_overhang
        total_depth = context.depth + front_overhang + back_overhang

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Material - use config override or context default
        material_config = config.get("material", {})
        if material_config:
            material_type_str = material_config.get("type", "plywood")
            try:
                material_type = MaterialType(material_type_str)
            except ValueError:
                material_type = MaterialType.PLYWOOD
            material = MaterialSpec(
                thickness=thickness,
                material_type=material_type,
            )
        else:
            material = MaterialSpec(thickness=thickness)

        # Main countertop panel
        # The panel position represents where it logically sits in the cabinet.
        # Overhang adjustments are stored in metadata for actual positioning.
        # Position cannot be negative, so we use max(0, adjusted_value).
        adjusted_x = max(0.0, context.position.x - left_overhang)
        adjusted_y = max(0.0, context.position.y - back_overhang)

        countertop_panel = Panel(
            panel_type=PanelType.COUNTERTOP,
            width=total_width,
            height=total_depth,  # Depth becomes height in 2D representation
            material=material,
            position=Position(x=adjusted_x, y=adjusted_y),
            metadata={
                "component": "countertop.surface",
                "edge_treatment": edge_treatment,
                "is_countertop": True,
                "front_overhang": front_overhang,
                "left_overhang": left_overhang,
                "right_overhang": right_overhang,
                "back_overhang": back_overhang,
                "zone": "base",
                "label": "Countertop",
                # Store the logical offset for downstream processing
                "position_offset_x": -left_overhang,
                "position_offset_y": -back_overhang,
            },
        )
        panels.append(countertop_panel)

        # Waterfall edge (vertical panel at front)
        if edge_treatment == "waterfall":
            waterfall_height = config.get("waterfall_height", 34.5)  # Full base height
            waterfall_x = max(0.0, context.position.x - left_overhang)
            waterfall_panel = Panel(
                panel_type=PanelType.WATERFALL_EDGE,
                width=total_width,
                height=waterfall_height,
                material=material,
                position=Position(x=waterfall_x, y=0),  # Starts at floor level
                metadata={
                    "component": "countertop.surface",
                    "is_waterfall_edge": True,
                    "parent_panel": "countertop",
                    "label": "Waterfall Edge",
                    "position_offset_x": -left_overhang,
                },
            )
            panels.append(waterfall_panel)

        # Support brackets for large overhangs
        if front_overhang > MAX_UNSUPPORTED_OVERHANG or config.get(
            "support_brackets", False
        ):
            bracket_count = self._calculate_bracket_count(total_width)
            bracket_size = config.get(
                "bracket_size", (MIN_BRACKET_WIDTH, MIN_BRACKET_DEPTH)
            )

            hardware.append(
                HardwareItem(
                    name=f'Countertop Support Bracket {bracket_size[0]}"x{bracket_size[1]}"',
                    quantity=bracket_count,
                    sku="CTOP-BRACKET-12X8",
                    notes=f'Support brackets for {front_overhang}" overhang, '
                    f'spaced {SUPPORT_BRACKET_SPACING}" apart',
                )
            )
            hardware.append(
                HardwareItem(
                    name='Bracket Mounting Screw #10 x 1-1/2"',
                    quantity=bracket_count * 4,
                    sku="SCREW-10-1.5",
                    notes="Bracket mounting hardware (4 per bracket)",
                )
            )

        # Edge banding calculation
        edge_banding_hardware = self._calculate_edge_banding(
            total_width=total_width,
            total_depth=total_depth,
            front_overhang=front_overhang,
            left_overhang=left_overhang,
            right_overhang=right_overhang,
            edge_treatment=edge_treatment,
        )
        if edge_banding_hardware:
            hardware.append(edge_banding_hardware)

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "edge_treatment": edge_treatment,
                "total_width": total_width,
                "total_depth": total_depth,
                "thickness": thickness,
                "overhangs": {
                    "front": front_overhang,
                    "left": left_overhang,
                    "right": right_overhang,
                    "back": back_overhang,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware items for countertop installation.

        Hardware varies based on configuration:
        - Support brackets for large overhangs (>12")
        - Bracket mounting screws
        - Edge banding (if applicable)

        Args:
            config: Countertop configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for countertop hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)

    def _calculate_bracket_count(self, width: float) -> int:
        """Calculate number of support brackets needed.

        Brackets are placed at each end plus every SUPPORT_BRACKET_SPACING inches.
        Minimum of 2 brackets.

        Args:
            width: Total countertop width in inches.

        Returns:
            Number of support brackets required.
        """
        return max(2, int(width / SUPPORT_BRACKET_SPACING) + 1)

    def _calculate_edge_banding(
        self,
        total_width: float,
        total_depth: float,
        front_overhang: float,
        left_overhang: float,
        right_overhang: float,
        edge_treatment: str,
    ) -> HardwareItem | None:
        """Calculate edge banding requirements for visible edges.

        Waterfall edges don't need edge banding (the waterfall panel is the edge).

        Args:
            total_width: Total countertop width including overhangs.
            total_depth: Total countertop depth including overhangs.
            front_overhang: Front overhang in inches.
            left_overhang: Left overhang in inches.
            right_overhang: Right overhang in inches.
            edge_treatment: Edge treatment type.

        Returns:
            HardwareItem for edge banding, or None if not needed.
        """
        if edge_treatment == "waterfall":
            return None

        visible_edges: list[str] = []
        edge_banding_length = 0.0

        if front_overhang > 0:
            visible_edges.append("front")
            edge_banding_length += total_width
        if left_overhang > 0:
            visible_edges.append("left")
            edge_banding_length += total_depth
        if right_overhang > 0:
            visible_edges.append("right")
            edge_banding_length += total_depth

        if edge_banding_length > 0:
            return HardwareItem(
                name=f"Edge Banding ({edge_treatment})",
                quantity=1,
                sku=f"EDGE-{edge_treatment.upper()}",
                notes=f"{edge_banding_length:.1f} linear inches for "
                f"{', '.join(visible_edges)} edges",
            )

        return None
