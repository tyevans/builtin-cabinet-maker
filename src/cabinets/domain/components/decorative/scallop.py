"""Scallop service and component for decorative edges.

This module provides:
- ScallopService for scallop pattern calculations
- ScallopComponent for generating scalloped panels (valances)
"""

from __future__ import annotations

import math
from typing import Any

from ...entities import Panel
from ...value_objects import PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .configs import ScallopConfig
from .metadata import ScallopCutMetadata


class ScallopService:
    """Service for scallop pattern calculations.

    Provides methods for calculating scallop patterns, generating
    template specifications, and ensuring symmetric layouts.
    """

    def calculate_pattern(
        self,
        config: ScallopConfig,
        piece_width: float,
    ) -> ScallopCutMetadata:
        """Calculate scallop pattern for a piece.

        Determines the number of scallops and adjusted width for
        symmetric pattern on the given piece width.

        Args:
            config: Scallop configuration.
            piece_width: Width of the piece to scallop in inches.

        Returns:
            ScallopCutMetadata with pattern specifications.
        """
        count = config.calculate_count(piece_width)
        actual_width = config.calculate_actual_width(piece_width)

        return ScallopCutMetadata(
            scallop_depth=config.depth,
            scallop_width=actual_width,
            scallop_count=count,
            template_required=True,
        )

    def generate_template_info(
        self,
        metadata: ScallopCutMetadata,
    ) -> str:
        """Generate template description for cut list.

        Creates a human-readable description of the scallop template
        needed to cut the pattern.

        Args:
            metadata: Scallop cut metadata.

        Returns:
            Template description string.
        """
        return (
            f"Scallop template: {metadata.scallop_count} scallops, "
            f'{metadata.scallop_width:.2f}" wide x '
            f'{metadata.scallop_depth:.2f}" deep each'
        )

    def calculate_scallop_centers(
        self,
        metadata: ScallopCutMetadata,
        piece_width: float,
    ) -> list[float]:
        """Calculate X positions of scallop centers.

        Centers are evenly distributed across piece width,
        ensuring symmetric pattern.

        Args:
            metadata: Scallop cut metadata.
            piece_width: Width of the piece in inches.

        Returns:
            List of X positions from left edge.
        """
        centers: list[float] = []
        half_width = metadata.scallop_width / 2

        for i in range(metadata.scallop_count):
            center = half_width + (i * metadata.scallop_width)
            centers.append(center)

        return centers

    def generate_scallop_points(
        self,
        metadata: ScallopCutMetadata,
        num_points_per_scallop: int = 11,
    ) -> list[tuple[float, float]]:
        """Generate curve points for scallop template creation.

        Creates points along the scallop pattern curve for template
        generation or CNC cutting. Each scallop is approximated by
        a semicircle.

        Args:
            metadata: Scallop cut metadata.
            num_points_per_scallop: Number of points per scallop curve.

        Returns:
            List of (x, y) tuples for the complete scallop pattern,
            where y=0 is the top edge and y=depth is the bottom of scallops.
        """
        points: list[tuple[float, float]] = []

        for i in range(metadata.scallop_count):
            center_x = metadata.scallop_width / 2 + i * metadata.scallop_width
            radius = metadata.scallop_width / 2

            # Generate points for this scallop (semicircle going down)
            for j in range(num_points_per_scallop):
                # Angle from 0 to pi (left to right along semicircle)
                angle = math.pi * j / (num_points_per_scallop - 1)

                # x position along the semicircle
                x = center_x - radius * math.cos(angle)

                # y position: 0 at top edge, depth at bottom of scallop
                # Use min of scallop_depth and the semicircle's y
                y_normalized = math.sin(angle)  # 0 at edges, 1 at center
                y = y_normalized * metadata.scallop_depth

                # Skip duplicate points at scallop boundaries
                if i > 0 and j == 0:
                    continue

                points.append((x, y))

        return points

    def validate_pattern(
        self,
        config: ScallopConfig,
        piece_width: float,
        piece_height: float,
    ) -> tuple[list[str], list[str]]:
        """Validate scallop pattern against piece dimensions.

        Checks that scallop depth doesn't exceed piece height and
        that at least one scallop fits.

        Args:
            config: Scallop configuration.
            piece_width: Width of the piece in inches.
            piece_height: Height of the piece in inches.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check depth doesn't exceed height
        if config.depth >= piece_height:
            errors.append(
                f'Scallop depth {config.depth}" exceeds piece height {piece_height}"'
            )
        elif config.depth > piece_height * 0.5:
            warnings.append(
                f'Scallop depth {config.depth}" is more than half the '
                f'piece height ({piece_height}")'
            )

        # Check at least one scallop fits
        count = config.calculate_count(piece_width)
        if count < 1:
            errors.append(
                f'Scallop width {config.width}" is too large for piece '
                f'width {piece_width}"'
            )

        # Check for reasonable scallop count
        if count > 20:
            warnings.append(
                f"Pattern has {count} scallops. Consider wider scallops "
                "for cleaner appearance."
            )

        # Warn about aspect ratio
        actual_width = piece_width / max(count, 1)
        aspect_ratio = actual_width / config.depth
        if aspect_ratio < 1.5:
            warnings.append(
                f"Scallop aspect ratio {aspect_ratio:.1f} is narrow. "
                "Consider reducing depth."
            )
        elif aspect_ratio > 4:
            warnings.append(
                f"Scallop aspect ratio {aspect_ratio:.1f} is wide. "
                "Consider increasing depth for visibility."
            )

        return errors, warnings


@component_registry.register("decorative.scallop")
class ScallopComponent:
    """Scallop pattern component for decorative edges.

    Generates a panel (typically valance) with scallop pattern metadata.
    Applicable to valances, shelf fronts, and bottom aprons.

    Configuration:
        scallop.depth: Depth of each scallop in inches.
        scallop.width: Nominal width of each scallop in inches.
        scallop.count: Number of scallops, or "auto" to fit evenly.
        valance_height: Height of the valance panel in inches (default: 4.0).

    Generated Pieces:
        - Valance panel with scallop metadata

    Notes:
        - STL output shows rectangular panel
        - Cut list includes template specifications
        - Pattern is always symmetric about centerline (FR-02.4)
    """

    def __init__(self) -> None:
        """Initialize ScallopComponent with its service."""
        self._scallop_service = ScallopService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate scallop configuration.

        Checks:
        - FR-02.1: Required scallop configuration fields
        - FR-02.3: Applicable piece type
        - Depth vs piece height

        Args:
            config: Scallop configuration from component_config.
            context: Component context with dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        scallop_config = config.get("scallop", {})
        if not scallop_config:
            return ValidationResult.ok()

        # Parse config
        try:
            parsed = self._parse_config(config)
        except (ValueError, KeyError) as e:
            return ValidationResult.fail([f"Invalid scallop config: {e}"])

        # Validate depth is positive
        if parsed.depth <= 0:
            return ValidationResult.fail(["Scallop depth must be positive"])

        # Validate width is positive
        if parsed.width <= 0:
            return ValidationResult.fail(["Scallop width must be positive"])

        # Get valance height from config or use default
        valance_height = config.get("valance_height", 4.0)

        # Validate depth is less than material thickness
        if parsed.depth >= context.material.thickness:
            return ValidationResult.fail(
                [
                    f'Scallop depth {parsed.depth}" must be less than '
                    f'material thickness {context.material.thickness}"'
                ]
            )

        # Validate pattern
        errors, warnings = self._scallop_service.validate_pattern(
            parsed, context.width, valance_height
        )

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> ScallopConfig:
        """Parse configuration dictionary into ScallopConfig.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            ScallopConfig with parsed values.
        """
        scallop_config = config.get("scallop", {})

        return ScallopConfig(
            depth=scallop_config.get("depth", 1.5),
            width=scallop_config.get("width", 4.0),
            count=scallop_config.get("count", "auto"),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate valance panel with scallop pattern.

        Creates a valance panel with scallop metadata for cutting.

        Args:
            config: Scallop configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with valance panel and metadata.
        """
        parsed = self._parse_config(config)
        valance_height = config.get("valance_height", 4.0)

        # Calculate pattern
        pattern = self._scallop_service.calculate_pattern(parsed, context.width)

        # Calculate scallop centers for template
        centers = self._scallop_service.calculate_scallop_centers(
            pattern, context.width
        )

        # Generate template info
        template_info = self._scallop_service.generate_template_info(pattern)

        # Generate scallop curve points
        scallop_points = self._scallop_service.generate_scallop_points(pattern)

        # Valance panel
        panel = Panel(
            panel_type=PanelType.VALANCE,
            width=context.width,
            height=valance_height,
            material=context.material,
            position=Position(
                context.position.x,
                context.position.y + context.height - valance_height,
            ),
            metadata={
                "scallop_depth": pattern.scallop_depth,
                "scallop_width": pattern.scallop_width,
                "scallop_count": pattern.scallop_count,
                "scallop_centers": centers,
                "scallop_points": scallop_points,
                "template_info": template_info,
                "template_required": pattern.template_required,
            },
        )

        return GenerationResult(
            panels=(panel,),
            hardware=tuple(),
            metadata={
                "scallop_pattern": {
                    "depth": pattern.scallop_depth,
                    "width": pattern.scallop_width,
                    "count": pattern.scallop_count,
                    "centers": centers,
                    "template_info": template_info,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Scallop patterns require no hardware.

        Args:
            config: Scallop configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []
