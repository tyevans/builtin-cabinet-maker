"""Molding zone service and components.

This module provides:
- MoldingZoneService for zone calculations and panel generation
- CrownMoldingComponent for crown molding zones
- ToeKickComponent for toe kick zones
- LightRailComponent for light rail zones
"""

from __future__ import annotations

from typing import Any

from ...entities import Panel
from ...value_objects import MaterialSpec, PanelType, Position
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .configs import BaseZone, CrownMoldingZone, LightRailZone


class MoldingZoneService:
    """Service for molding zone calculations and panel generation.

    Handles crown molding, base/toe kick, and light rail zones.
    Generates nailer strips and calculates dimension adjustments.

    This service provides the core logic for molding zone operations,
    while the individual component classes (CrownMoldingComponent,
    ToeKickComponent, LightRailComponent) wrap this service to implement
    the Component protocol.
    """

    def calculate_crown_adjustments(
        self,
        config: CrownMoldingZone,
        cabinet_width: float,
        cabinet_depth: float,
    ) -> dict[str, float]:
        """Calculate dimension adjustments for crown molding zone.

        Args:
            config: Crown molding zone configuration.
            cabinet_width: Cabinet width in inches.
            cabinet_depth: Cabinet depth in inches.

        Returns:
            Dict with adjustment values:
            - top_panel_depth_reduction: Amount to reduce top panel depth
            - nailer_depth: Depth of nailer strip
            - nailer_width: Width of nailer strip (full cabinet width)
        """
        return {
            "top_panel_depth_reduction": config.setback,
            "nailer_depth": cabinet_depth,  # Full depth for support
            "nailer_width": cabinet_width,
            "zone_height": config.height,
        }

    def generate_crown_nailer(
        self,
        config: CrownMoldingZone,
        cabinet_width: float,
        cabinet_height: float,
        cabinet_depth: float,
        material: MaterialSpec,
        position: Position,
    ) -> Panel:
        """Generate crown molding nailer strip.

        The nailer strip is positioned at the top back of the cabinet,
        providing a mounting surface for crown molding.

        Args:
            config: Crown molding zone configuration.
            cabinet_width: Cabinet width in inches.
            cabinet_height: Cabinet height in inches.
            cabinet_depth: Cabinet depth in inches.
            material: Material for nailer.
            position: Cabinet position.

        Returns:
            Nailer panel.
        """
        return Panel(
            panel_type=PanelType.NAILER,
            width=cabinet_width,
            height=config.nailer_width,  # Note: nailer is horizontal, "height" is depth
            material=material,
            position=Position(
                position.x,
                position.y + cabinet_height - config.nailer_width,
            ),
            metadata={
                "zone_type": "crown_molding",
                "zone_height": config.height,
                "setback": config.setback,
                "location": "top_back",
            },
        )

    def calculate_toe_kick_adjustments(
        self,
        config: BaseZone,
    ) -> dict[str, float]:
        """Calculate dimension adjustments for toe kick zone.

        Args:
            config: Base zone configuration.

        Returns:
            Dict with adjustment values:
            - bottom_panel_raise: Amount to raise bottom panel
            - side_panel_reduction: Amount to shorten side panels
            - toe_kick_height: Height of toe kick
            - toe_kick_setback: Depth of toe kick recess
        """
        if config.zone_type != "toe_kick":
            return {
                "bottom_panel_raise": 0,
                "side_panel_reduction": 0,
                "toe_kick_height": 0,
                "toe_kick_setback": 0,
            }

        return {
            "bottom_panel_raise": config.height,
            "side_panel_reduction": config.height,
            "toe_kick_height": config.height,
            "toe_kick_setback": config.setback,
        }

    def generate_toe_kick_panel(
        self,
        config: BaseZone,
        cabinet_width: float,
        material: MaterialSpec,
        position: Position,
    ) -> Panel | None:
        """Generate toe kick front panel.

        The toe kick panel is recessed from the cabinet front,
        creating the toe space under the cabinet.

        Args:
            config: Base zone configuration.
            cabinet_width: Cabinet width in inches.
            material: Material for panel.
            position: Cabinet position.

        Returns:
            Toe kick panel, or None if not toe_kick type.
        """
        if config.zone_type != "toe_kick":
            return None

        return Panel(
            panel_type=PanelType.TOE_KICK,
            width=cabinet_width,
            height=config.height,
            material=material,
            position=Position(position.x, position.y),
            metadata={
                "zone_type": "toe_kick",
                "setback": config.setback,
                "location": "bottom_front_recessed",
            },
        )

    def generate_light_rail_strip(
        self,
        config: LightRailZone,
        cabinet_width: float,
        material: MaterialSpec,
        position: Position,
    ) -> Panel | None:
        """Generate light rail strip.

        The light rail strip is positioned at the bottom front
        of wall cabinets to conceal under-cabinet lighting.

        Args:
            config: Light rail zone configuration.
            cabinet_width: Cabinet width in inches.
            material: Material for strip.
            position: Cabinet position.

        Returns:
            Light rail panel, or None if generate_strip is False.
        """
        if not config.generate_strip:
            return None

        return Panel(
            panel_type=PanelType.LIGHT_RAIL,
            width=cabinet_width,
            height=config.height,
            material=material,
            position=Position(position.x, position.y),
            metadata={
                "zone_type": "light_rail",
                "setback": config.setback,
                "location": "bottom_front",
            },
        )

    def validate_zones(
        self,
        crown: CrownMoldingZone | None,
        base: BaseZone | None,
        light_rail: LightRailZone | None,
        cabinet_height: float,
        cabinet_depth: float,
    ) -> tuple[list[str], list[str]]:
        """Validate molding zone configurations.

        Checks that zones don't exceed cabinet dimensions and
        don't conflict with each other.

        Args:
            crown: Crown molding zone config (or None).
            base: Base zone config (or None).
            light_rail: Light rail zone config (or None).
            cabinet_height: Cabinet height in inches.
            cabinet_depth: Cabinet depth in inches.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        total_zone_height = 0.0

        # Validate crown zone
        if crown:
            total_zone_height += crown.height
            if crown.setback >= cabinet_depth:
                errors.append(
                    f'Crown setback {crown.setback}" exceeds cabinet depth '
                    f'{cabinet_depth}"'
                )
            if crown.height > cabinet_height * 0.2:
                warnings.append(
                    f'Crown zone height {crown.height}" is more than 20% '
                    "of cabinet height"
                )

        # Validate base zone
        if base:
            total_zone_height += base.height
            if base.zone_type == "toe_kick":
                if base.height < 3.0:
                    warnings.append(
                        f'Toe kick height {base.height}" is less than '
                        'recommended 3" minimum (FR-06)'
                    )
                if base.setback < 2.0:
                    warnings.append(
                        f'Toe kick setback {base.setback}" is less than '
                        'recommended 2" minimum'
                    )

        # Validate light rail zone
        if light_rail:
            if light_rail.height > 3.0:
                warnings.append(
                    f'Light rail height {light_rail.height}" may be too tall'
                )

        # Check total zone height
        if total_zone_height > cabinet_height * 0.3:
            warnings.append(
                f'Total zone height {total_zone_height}" is more than 30% '
                "of cabinet height"
            )

        if total_zone_height >= cabinet_height:
            errors.append(
                f'Total zone height {total_zone_height}" exceeds cabinet '
                f'height {cabinet_height}"'
            )

        return errors, warnings

    def generate_all_zone_panels(
        self,
        crown: CrownMoldingZone | None,
        base: BaseZone | None,
        light_rail: LightRailZone | None,
        cabinet_width: float,
        cabinet_height: float,
        cabinet_depth: float,
        material: MaterialSpec,
        position: Position,
    ) -> list[Panel]:
        """Generate all panels for configured molding zones.

        Args:
            crown: Crown molding zone config (or None).
            base: Base zone config (or None).
            light_rail: Light rail zone config (or None).
            cabinet_width: Cabinet width in inches.
            cabinet_height: Cabinet height in inches.
            cabinet_depth: Cabinet depth in inches.
            material: Material for panels.
            position: Cabinet position.

        Returns:
            List of zone panels (nailer, toe kick, light rail).
        """
        panels: list[Panel] = []

        if crown:
            panels.append(
                self.generate_crown_nailer(
                    crown,
                    cabinet_width,
                    cabinet_height,
                    cabinet_depth,
                    material,
                    position,
                )
            )

        if base and base.zone_type == "toe_kick":
            toe_kick = self.generate_toe_kick_panel(
                base, cabinet_width, material, position
            )
            if toe_kick:
                panels.append(toe_kick)

        if light_rail:
            rail = self.generate_light_rail_strip(
                light_rail, cabinet_width, material, position
            )
            if rail:
                panels.append(rail)

        return panels

    def get_dimension_adjustments(
        self,
        crown: CrownMoldingZone | None,
        base: BaseZone | None,
        cabinet_depth: float,
    ) -> dict[str, float]:
        """Get all dimension adjustments for zone configurations.

        Combines adjustments from all zones into a single dict.

        Args:
            crown: Crown molding zone config (or None).
            base: Base zone config (or None).
            cabinet_depth: Cabinet depth in inches.

        Returns:
            Dict with all adjustment values.
        """
        adjustments = {
            "top_panel_depth_reduction": 0.0,
            "bottom_panel_raise": 0.0,
            "side_panel_bottom_raise": 0.0,
        }

        if crown:
            adjustments["top_panel_depth_reduction"] = crown.setback

        if base and base.zone_type == "toe_kick":
            adjustments["bottom_panel_raise"] = base.height
            adjustments["side_panel_bottom_raise"] = base.height

        return adjustments


@component_registry.register("decorative.crown_molding")
class CrownMoldingComponent:
    """Crown molding zone component.

    Generates a nailer strip at the top back of the cabinet to provide
    a mounting surface for crown molding. The top panel depth is reduced
    by the configured setback to allow the molding to sit flush.

    Configuration:
        height: Zone height for molding in inches (default: 3.0).
        setback: Top panel setback distance in inches (default: 0.75).
        nailer_width: Width of nailer strip in inches (default: 2.0).

    Generated Pieces:
        - Nailer strip panel (PanelType.NAILER) at top back of cabinet

    Hardware:
        None - nailer strips are structural, attached with standard joinery.

    Note:
        The actual crown molding profile is not generated - only the
        zone and nailer strip. Crown molding is typically purchased
        as linear molding and cut to fit.
    """

    def __init__(self) -> None:
        """Initialize CrownMoldingComponent with its service."""
        self._service = MoldingZoneService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate crown molding zone configuration.

        Checks:
        - height > 0
        - setback > 0
        - setback < cabinet depth
        - height doesn't exceed 20% of cabinet height (warning)

        Args:
            config: Crown molding configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        crown_config = config.get("crown_molding", {})
        if not crown_config:
            return ValidationResult.ok()

        # Parse and validate
        try:
            parsed = self._parse_config(config)
        except ValueError as e:
            return ValidationResult.fail([str(e)])

        # Validate using service
        zone_errors, zone_warnings = self._service.validate_zones(
            crown=parsed,
            base=None,
            light_rail=None,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )

        errors.extend(zone_errors)
        warnings.extend(zone_warnings)

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> CrownMoldingZone:
        """Parse configuration dictionary into CrownMoldingZone.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            CrownMoldingZone with parsed values or defaults.
        """
        crown_config = config.get("crown_molding", {})

        return CrownMoldingZone(
            height=crown_config.get("height", 3.0),
            setback=crown_config.get("setback", 0.75),
            nailer_width=crown_config.get("nailer_width", 2.0),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate crown molding nailer panel.

        Creates a nailer strip panel at the top back of the cabinet.

        Args:
            config: Crown molding configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with nailer panel and metadata.
        """
        parsed = self._parse_config(config)

        nailer = self._service.generate_crown_nailer(
            config=parsed,
            cabinet_width=context.cabinet_width,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
            material=context.material,
            position=context.position,
        )

        adjustments = self._service.calculate_crown_adjustments(
            config=parsed,
            cabinet_width=context.cabinet_width,
            cabinet_depth=context.cabinet_depth,
        )

        return GenerationResult(
            panels=(nailer,),
            hardware=tuple(),
            metadata={
                "crown_zone": {
                    "height": parsed.height,
                    "setback": parsed.setback,
                    "nailer_width": parsed.nailer_width,
                },
                "adjustments": adjustments,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Crown molding zones require no hardware.

        Nailer strips are attached with standard cabinet joinery.

        Args:
            config: Crown molding configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


@component_registry.register("decorative.toe_kick")
class ToeKickComponent:
    """Toe kick zone component.

    Generates a recessed front panel at the bottom of the cabinet to
    create toe space. The bottom panel is raised by the toe kick height
    and side panels are shortened accordingly.

    Configuration:
        height: Toe kick height in inches (default: 3.5).
        setback: Toe kick recess depth in inches (default: 3.0).

    Generated Pieces:
        - Toe kick panel (PanelType.TOE_KICK) at bottom front of cabinet

    Hardware:
        None - toe kick panels are structural, attached with standard joinery.

    Note:
        The toe kick panel is recessed from the front face of the cabinet
        by the setback distance, creating space for the user's toes when
        standing close to the cabinet.
    """

    def __init__(self) -> None:
        """Initialize ToeKickComponent with its service."""
        self._service = MoldingZoneService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate toe kick zone configuration.

        Checks:
        - height > 0
        - setback >= 0
        - height < 3.0 generates warning (FR-06 recommends >= 3")
        - setback < 2.0 generates warning (recommended >= 2")

        Args:
            config: Toe kick configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        toe_kick_config = config.get("toe_kick", {})
        if not toe_kick_config:
            return ValidationResult.ok()

        # Parse and validate
        try:
            parsed = self._parse_config(config)
        except ValueError as e:
            return ValidationResult.fail([str(e)])

        # Validate using service
        zone_errors, zone_warnings = self._service.validate_zones(
            crown=None,
            base=parsed,
            light_rail=None,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )

        errors.extend(zone_errors)
        warnings.extend(zone_warnings)

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> BaseZone:
        """Parse configuration dictionary into BaseZone for toe kick.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            BaseZone with zone_type="toe_kick".
        """
        toe_kick_config = config.get("toe_kick", {})

        return BaseZone(
            height=toe_kick_config.get("height", 3.5),
            setback=toe_kick_config.get("setback", 3.0),
            zone_type="toe_kick",
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate toe kick panel.

        Creates a recessed panel at the bottom front of the cabinet.

        Args:
            config: Toe kick configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with toe kick panel and metadata.
        """
        parsed = self._parse_config(config)

        panel = self._service.generate_toe_kick_panel(
            config=parsed,
            cabinet_width=context.cabinet_width,
            material=context.material,
            position=context.position,
        )

        adjustments = self._service.calculate_toe_kick_adjustments(config=parsed)

        panels = (panel,) if panel else tuple()

        return GenerationResult(
            panels=panels,
            hardware=tuple(),
            metadata={
                "toe_kick_zone": {
                    "height": parsed.height,
                    "setback": parsed.setback,
                },
                "adjustments": adjustments,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Toe kick zones require no hardware.

        Toe kick panels are attached with standard cabinet joinery.

        Args:
            config: Toe kick configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []


@component_registry.register("decorative.light_rail")
class LightRailComponent:
    """Light rail zone component.

    Generates a light rail strip at the bottom front of wall cabinets
    to conceal under-cabinet lighting. Only generates the strip panel
    if generate_strip is True.

    Configuration:
        height: Light rail strip height in inches (default: 1.5).
        setback: Light rail setback in inches (default: 0.25).
        generate_strip: Whether to generate strip piece (default: True).

    Generated Pieces:
        - Light rail strip (PanelType.LIGHT_RAIL) at bottom front of cabinet
          (only if generate_strip=True)

    Hardware:
        None - light rail strips are attached with standard methods.

    Note:
        Light rail strips are typically used on wall cabinets to conceal
        under-cabinet lighting fixtures. The zone reserves space for the
        lighting, and the optional strip provides a finished appearance.
    """

    def __init__(self) -> None:
        """Initialize LightRailComponent with its service."""
        self._service = MoldingZoneService()

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate light rail zone configuration.

        Checks:
        - height > 0
        - setback >= 0
        - height > 3.0 generates warning (may be too tall)

        Args:
            config: Light rail configuration from section config.
            context: Component context with cabinet dimensions.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        light_rail_config = config.get("light_rail", {})
        if not light_rail_config:
            return ValidationResult.ok()

        # Parse and validate
        try:
            parsed = self._parse_config(config)
        except ValueError as e:
            return ValidationResult.fail([str(e)])

        # Validate using service
        zone_errors, zone_warnings = self._service.validate_zones(
            crown=None,
            base=None,
            light_rail=parsed,
            cabinet_height=context.cabinet_height,
            cabinet_depth=context.cabinet_depth,
        )

        errors.extend(zone_errors)
        warnings.extend(zone_warnings)

        return ValidationResult(tuple(errors), tuple(warnings))

    def _parse_config(self, config: dict[str, Any]) -> LightRailZone:
        """Parse configuration dictionary into LightRailZone.

        Args:
            config: Configuration dictionary from component_config.

        Returns:
            LightRailZone with parsed values or defaults.
        """
        light_rail_config = config.get("light_rail", {})

        return LightRailZone(
            height=light_rail_config.get("height", 1.5),
            setback=light_rail_config.get("setback", 0.25),
            generate_strip=light_rail_config.get("generate_strip", True),
        )

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate light rail strip panel.

        Creates a strip panel at the bottom front of the cabinet
        if generate_strip is True.

        Args:
            config: Light rail configuration.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult with light rail panel and metadata.
        """
        parsed = self._parse_config(config)

        panel = self._service.generate_light_rail_strip(
            config=parsed,
            cabinet_width=context.cabinet_width,
            material=context.material,
            position=context.position,
        )

        panels = (panel,) if panel else tuple()

        return GenerationResult(
            panels=panels,
            hardware=tuple(),
            metadata={
                "light_rail_zone": {
                    "height": parsed.height,
                    "setback": parsed.setback,
                    "generate_strip": parsed.generate_strip,
                },
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Light rail zones require no hardware.

        Light rail strips are attached with standard methods.

        Args:
            config: Light rail configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []
