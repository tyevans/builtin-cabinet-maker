"""Arch service and component for arched cabinet openings.

This module provides:
- ArchService for arch geometry calculations
- ArchComponent for generating arch header panels
"""

from __future__ import annotations

import math
from typing import Any

from ...entities import Panel
from ...value_objects import PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .configs import ArchConfig
from .enums import ArchType
from .metadata import ArchCutMetadata


class ArchService:
    """Service for arch geometry calculations.

    Provides methods for calculating arch dimensions, curves,
    and related geometry for arched cabinet openings.

    Supports three arch types:
    - FULL_ROUND (semicircle): radius = width/2
    - SEGMENTAL (partial arc): radius > width/2, shallower curve
    - ELLIPTICAL: semi-major axis a = width/2, semi-minor axis b = radius
    """

    def calculate_header_height(
        self,
        config: ArchConfig,
        opening_width: float,
    ) -> float:
        """Calculate the height of the arch header panel.

        The header height is the rectangular stock height needed
        to cut the arch shape from.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.

        Returns:
            Height of header panel in inches.
        """
        radius = config.calculate_radius(opening_width)

        if config.arch_type == ArchType.FULL_ROUND:
            # Full semicircle: height = radius + spring height
            return radius + config.spring_height

        elif config.arch_type == ArchType.SEGMENTAL:
            # Segmental: calculate arc rise
            half_width = opening_width / 2
            if radius < half_width:
                # Invalid: radius too small
                return config.spring_height
            arc_rise = radius - math.sqrt(radius**2 - half_width**2)
            return arc_rise + config.spring_height

        elif config.arch_type == ArchType.ELLIPTICAL:
            # Elliptical: radius is the semi-minor axis (height)
            return radius + config.spring_height

        return config.spring_height

    def calculate_arc_rise(
        self,
        config: ArchConfig,
        opening_width: float,
    ) -> float:
        """Calculate the rise of the arch curve only (without spring height).

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.

        Returns:
            Arc rise in inches (0 for flat, max for semicircle).
        """
        radius = config.calculate_radius(opening_width)
        half_width = opening_width / 2

        if config.arch_type == ArchType.FULL_ROUND:
            return radius  # Semicircle rise = radius

        elif config.arch_type == ArchType.SEGMENTAL:
            if radius < half_width:
                return 0.0  # Invalid configuration
            return radius - math.sqrt(radius**2 - half_width**2)

        elif config.arch_type == ArchType.ELLIPTICAL:
            return radius  # Semi-minor axis is the rise

        return 0.0

    def calculate_upright_extension(
        self,
        config: ArchConfig,
        opening_width: float,
        upright_position: float,
    ) -> float:
        """Calculate how much an upright extends into the arch area.

        Used to determine the height of side panels that meet the arch.
        For a point at distance x from center, calculates the y-value
        (height above spring line) at that position.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.
            upright_position: Distance from arch center to upright in inches.
                             Use 0 for center, positive for right, negative for left.

        Returns:
            Height extension above spring line in inches (includes spring_height).
        """
        radius = config.calculate_radius(opening_width)
        half_width = opening_width / 2

        # If upright is outside the arch, return spring height only
        if abs(upright_position) >= half_width:
            return config.spring_height

        if config.arch_type == ArchType.FULL_ROUND:
            # Semicircle: y = sqrt(r^2 - x^2)
            y = math.sqrt(radius**2 - upright_position**2)
            return y + config.spring_height

        elif config.arch_type == ArchType.SEGMENTAL:
            if radius < half_width:
                return config.spring_height
            # Segmental arc with center below opening
            # Arc is part of a circle with larger radius
            # y = sqrt(r^2 - x^2) - (r - arc_rise)
            arc_rise = radius - math.sqrt(radius**2 - half_width**2)
            y = math.sqrt(radius**2 - upright_position**2) - (radius - arc_rise)
            return max(0.0, y) + config.spring_height

        elif config.arch_type == ArchType.ELLIPTICAL:
            # Ellipse: y = b * sqrt(1 - (x/a)^2)
            a = half_width  # Semi-major axis (horizontal)
            b = radius  # Semi-minor axis (vertical, height)
            y = b * math.sqrt(1 - (upright_position / a) ** 2)
            return y + config.spring_height

        return config.spring_height

    def generate_curve_points(
        self,
        config: ArchConfig,
        opening_width: float,
        num_points: int = 21,
    ) -> list[tuple[float, float]]:
        """Generate points along the arch curve for templates.

        Points are relative to the arch center at the spring line.
        The x-coordinates range from -opening_width/2 to +opening_width/2.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.
            num_points: Number of points to generate (odd for center point).

        Returns:
            List of (x, y) tuples from left to right.
        """
        half_width = opening_width / 2
        points: list[tuple[float, float]] = []

        for i in range(num_points):
            x = -half_width + (opening_width * i / (num_points - 1))
            y = self.calculate_upright_extension(config, opening_width, x)
            points.append((x, y))

        return points

    def create_cut_metadata(
        self,
        config: ArchConfig,
        opening_width: float,
    ) -> ArchCutMetadata:
        """Create cut metadata for arch header.

        Args:
            config: Arch configuration.
            opening_width: Width of the opening in inches.

        Returns:
            ArchCutMetadata for cut list output.
        """
        return ArchCutMetadata(
            arch_type=config.arch_type,
            radius=config.calculate_radius(opening_width),
            spring_height=config.spring_height,
            opening_width=opening_width,
        )


@component_registry.register("decorative.arch")
class ArchComponent:
    """Arch top component for arched cabinet openings.

    Generates an arched header panel with curve metadata for cutting.
    The arch fits between vertical dividers within a section.

    Configuration:
        arch_type: Type of arch (full_round, segmental, elliptical).
        radius: Radius in inches, or "auto" for semicircle.
        spring_height: Height where arch curve begins (default: 0).

    Generated Pieces:
        - Arch header panel (rectangular stock with curve metadata)

    Notes:
        - STL output shows rectangular bounding box
        - Cut list includes curve specifications for cutting
        - Side panels should reference arch metadata for height
    """

    def __init__(self) -> None:
        """Initialize ArchComponent with its service."""
        self._arch_service = ArchService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate arch configuration.

        Checks:
        - FR-01.1: Required arch configuration fields
        - FR-01.2: Radius valid for arch type and opening width
        - FR-01.6: Arch fits within section width

        Args:
            config: Arch configuration from component_config.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        arch_config = config.get("arch_top", {})
        if not arch_config:
            return ValidationResult.ok()

        # Parse config
        try:
            parsed = self._parse_config(config)
        except (ValueError, KeyError) as e:
            return ValidationResult.fail([f"Invalid arch config: {e}"])

        opening_width = context.width

        # Validate radius is positive if numeric
        if isinstance(parsed.radius, (int, float)) and parsed.radius <= 0:
            errors.append("Arch radius must be positive")
            return ValidationResult(tuple(errors), tuple(warnings))

        # FR-01.2: Validate radius for arch type
        if parsed.arch_type == ArchType.FULL_ROUND:
            # For full_round with explicit radius, radius must equal width/2
            if parsed.radius != "auto":
                expected_radius = opening_width / 2
                if parsed.radius > expected_radius:
                    errors.append(
                        f'Full round arch radius {parsed.radius}" exceeds half opening '
                        f"width ({expected_radius}\"). Use 'auto' or a smaller radius."
                    )

        elif parsed.arch_type == ArchType.SEGMENTAL:
            radius = parsed.calculate_radius(opening_width)
            min_radius = opening_width / 2
            if radius < min_radius:
                errors.append(
                    f'Segmental arch radius {radius}" must be >= half opening '
                    f'width ({min_radius}")'
                )

        # Check header height doesn't exceed section height
        header_height = self._arch_service.calculate_header_height(
            parsed, opening_width
        )
        if header_height > context.height:
            errors.append(
                f'Arch header height {header_height:.1f}" exceeds section '
                f'height {context.height}"'
            )

        # Warning for very tall arches
        elif header_height > context.height * 0.5:
            warnings.append(
                f"Arch header uses {header_height / context.height * 100:.0f}% "
                "of section height"
            )

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> ArchConfig:
        """Parse configuration dictionary into ArchConfig.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            ArchConfig with parsed values.

        Raises:
            ValueError: If configuration values are invalid.
        """
        arch_config = config.get("arch_top", {})

        arch_type_str = arch_config.get("arch_type", "full_round")
        arch_type = ArchType(arch_type_str)

        radius = arch_config.get("radius", "auto")
        spring_height = float(arch_config.get("spring_height", 0.0))

        return ArchConfig(
            arch_type=arch_type,
            radius=radius,
            spring_height=spring_height,
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate arch header panel.

        Creates a rectangular panel representing the stock needed
        to cut the arch shape. Curve metadata is included for cutting.

        Args:
            config: Arch configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with arch header panel and metadata.
        """
        parsed = self._parse_config(config)
        opening_width = context.width

        # Calculate dimensions
        header_height = self._arch_service.calculate_header_height(
            parsed, opening_width
        )
        arc_rise = self._arch_service.calculate_arc_rise(parsed, opening_width)

        # Create cut metadata
        cut_metadata = self._arch_service.create_cut_metadata(parsed, opening_width)

        # Generate curve points for template
        curve_points = self._arch_service.generate_curve_points(parsed, opening_width)

        # Arch header panel (rectangular stock)
        panel = Panel(
            panel_type=PanelType.ARCH_HEADER,
            width=opening_width,
            height=header_height,
            material=context.material,
            position=Position(
                context.position.x,
                context.position.y + context.height - header_height,
            ),
            metadata={
                "arch_type": cut_metadata.arch_type.value,
                "radius": cut_metadata.radius,
                "spring_height": cut_metadata.spring_height,
                "opening_width": cut_metadata.opening_width,
                "arc_rise": arc_rise,
                "curve_points": curve_points,
            },
        )

        # Calculate upright extension at typical edge position (0.75" from edge)
        upright_extension_at_edge = self._arch_service.calculate_upright_extension(
            parsed, opening_width, opening_width / 2 - 0.75
        )

        return GenerationResult(
            panels=(panel,),
            hardware=tuple(),
            metadata={
                "arch_config": {
                    "arch_type": parsed.arch_type.value,
                    "radius": cut_metadata.radius,
                    "spring_height": parsed.spring_height,
                    "opening_width": opening_width,
                    "header_height": header_height,
                    "arc_rise": arc_rise,
                },
                "upright_extension_at_edge": upright_extension_at_edge,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Arch components require no hardware.

        Arches are cut shapes, not hardware installations.

        Args:
            config: Arch configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []
