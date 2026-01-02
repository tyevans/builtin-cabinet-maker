"""Infrastructure component implementations for FRD-15.

Phase 3: Infrastructure Components

This module provides infrastructure integration components for cabinet sections:
- LightingComponent: LED strips and puck lights
- ElectricalComponent: Outlet cutouts
- CableManagementComponent: Grommets for cable pass-through
- VentilationComponent: Ventilation patterns for electronics cooling

All components follow the Component protocol and register with the component_registry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..value_objects import (
    CutoutShape,
    LightingLocation,
    LightingType,
    OutletType,
    PanelCutout,
    PanelType,
    Point2D,
    VentilationPattern,
)
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult


# --- Spec Dataclasses ---


@dataclass(frozen=True)
class LightingSpec:
    """Specification for cabinet lighting installation.

    Represents the configuration for a lighting installation within
    a cabinet, supporting both LED strips and puck lights.

    Attributes:
        light_type: Type of lighting (LED strip, puck, accent).
        location: Where the lighting is installed (under, in, above cabinet).
        section_indices: Tuple of section indices where lighting is installed.
        length: Length of LED strip in inches (required for LED strips).
        diameter: Diameter of puck light in inches (default: 2.5").
        channel_width: Width of LED channel in inches (default: 0.5").
        channel_depth: Depth of LED channel in inches (default: 0.25").
        position: Optional 2D position for puck light placement.
    """

    light_type: LightingType
    location: LightingLocation
    section_indices: tuple[int, ...]
    length: float | None = None
    diameter: float = 2.5
    channel_width: float = 0.5
    channel_depth: float = 0.25
    position: Point2D | None = None


@dataclass(frozen=True)
class OutletSpec:
    """Specification for electrical outlet cutout.

    Represents the configuration for an electrical outlet cutout
    in a cabinet panel.

    Attributes:
        outlet_type: Type of outlet (single, double, GFI).
        section_index: Index of the section containing the outlet.
        panel: Panel type where the cutout is located.
        position: 2D position of the cutout center on the panel.
        conduit_direction: Direction for conduit routing (default: "bottom").
    """

    outlet_type: OutletType
    section_index: int
    panel: PanelType
    position: Point2D
    conduit_direction: str = "bottom"

    @property
    def cutout_dimensions(self) -> tuple[float, float]:
        """Return (width, height) with 0.125" clearance.

        Standard outlet box dimensions with clearance for installation:
        - Single: 2.25" x 4.0"
        - Double: 4.25" x 4.0"
        - GFI: 3.0" x 4.75"

        Returns:
            Tuple of (width, height) in inches.
        """
        dims = {
            OutletType.SINGLE: (2.25, 4.0),
            OutletType.DOUBLE: (4.25, 4.0),
            OutletType.GFI: (3.0, 4.75),
        }
        return dims[self.outlet_type]


@dataclass(frozen=True)
class GrommetSpec:
    """Specification for cable management grommet.

    Represents a circular cutout for cable pass-through with
    a rubber grommet insert.

    Attributes:
        size: Diameter of the grommet in inches (2.0, 2.5, or 3.0).
        panel: Panel type where the grommet is installed.
        position: 2D position of the grommet center on the panel.
        section_index: Optional section index for the grommet.
    """

    size: float  # Diameter in inches (2.0, 2.5, or 3.0)
    panel: PanelType
    position: Point2D
    section_index: int | None = None


@dataclass(frozen=True)
class CableChannelSpec:
    """Specification for cable routing channel.

    Represents a channel routed into a panel for organized cable
    routing within the cabinet.

    Attributes:
        start: Starting point of the channel.
        end: Ending point of the channel.
        width: Width of the channel in inches (default: 2.0").
        depth: Depth of the channel in inches (default: 1.0").
    """

    start: Point2D
    end: Point2D
    width: float = 2.0
    depth: float = 1.0


@dataclass(frozen=True)
class VentilationSpec:
    """Specification for ventilation cutout area.

    Represents a ventilation area with a pattern of holes or slots
    for airflow in cabinet panels.

    Attributes:
        pattern: Pattern type (grid, slot, circular).
        panel: Panel type where ventilation is located.
        position: 2D position of the ventilation area center.
        width: Width of the ventilation area in inches.
        height: Height of the ventilation area in inches.
        hole_size: Diameter of individual holes in inches (default: 0.25").
    """

    pattern: VentilationPattern
    panel: PanelType
    position: Point2D
    width: float
    height: float
    hole_size: float = 0.25


@dataclass(frozen=True)
class WireRouteSpec:
    """Specification for wire routing path through cabinet.

    Represents a path for routing wires through multiple panels
    with drilled holes at each penetration point.

    Attributes:
        waypoints: Tuple of 2D points defining the wire route.
        hole_diameter: Diameter of wire holes in inches (default: 0.75").
        panel_penetrations: Tuple of panel types the wire passes through.
    """

    waypoints: tuple[Point2D, ...]
    hole_diameter: float = 0.75
    panel_penetrations: tuple[PanelType, ...] = ()


# --- Base Class with Shared Validation ---


class _InfrastructureBase:
    """Base class for infrastructure components with shared validation.

    Provides common validation methods used across all infrastructure
    components for checking edge distances, section indices, and
    cutout overlaps.
    """

    MIN_EDGE_DISTANCE = 1.0  # Minimum 1" from panel edges

    def _validate_edge_distance(
        self,
        position: Point2D,
        panel_width: float,
        panel_height: float,
        cutout_width: float,
        cutout_height: float,
        min_edge: float = 1.0,
    ) -> list[str]:
        """Check that cutout maintains minimum distance from panel edges.

        Validates that a cutout centered at the given position will not
        be too close to any edge of the panel.

        Args:
            position: Center position of the cutout.
            panel_width: Width of the panel in inches.
            panel_height: Height of the panel in inches.
            cutout_width: Width of the cutout in inches.
            cutout_height: Height of the cutout in inches.
            min_edge: Minimum distance from edge in inches (default: 1.0").

        Returns:
            List of error messages for edge distance violations.
        """
        errors: list[str] = []

        # Calculate cutout bounds
        left = position.x - cutout_width / 2
        right = position.x + cutout_width / 2
        bottom = position.y - cutout_height / 2
        top = position.y + cutout_height / 2

        # Check each edge
        if left < min_edge:
            errors.append(
                f'Cutout left edge ({left:.2f}") too close to panel edge '
                f'(minimum {min_edge}" required)'
            )
        if right > panel_width - min_edge:
            errors.append(
                f'Cutout right edge ({right:.2f}") too close to panel edge '
                f'(maximum {panel_width - min_edge:.2f}" allowed)'
            )
        if bottom < min_edge:
            errors.append(
                f'Cutout bottom edge ({bottom:.2f}") too close to panel edge '
                f'(minimum {min_edge}" required)'
            )
        if top > panel_height - min_edge:
            errors.append(
                f'Cutout top edge ({top:.2f}") too close to panel edge '
                f'(maximum {panel_height - min_edge:.2f}" allowed)'
            )

        return errors

    def _validate_section_index(
        self,
        index: int,
        max_sections: int,
    ) -> list[str]:
        """Check that section index is valid.

        Args:
            index: The section index to validate.
            max_sections: Maximum number of sections (exclusive upper bound).

        Returns:
            List of error messages for invalid indices.
        """
        errors: list[str] = []
        if index < 0:
            errors.append(f"Section index {index} cannot be negative")
        if index >= max_sections:
            errors.append(f"Section index {index} exceeds maximum {max_sections - 1}")
        return errors

    def _check_cutout_overlap(
        self,
        cutouts: list[PanelCutout],
    ) -> list[str]:
        """Check that no cutouts overlap with each other.

        Args:
            cutouts: List of PanelCutout objects to check.

        Returns:
            List of error messages for overlapping cutouts.
        """
        errors: list[str] = []

        for i, cutout_a in enumerate(cutouts):
            for j, cutout_b in enumerate(cutouts[i + 1 :], start=i + 1):
                # Only check cutouts on the same panel
                if cutout_a.panel != cutout_b.panel:
                    continue

                # Calculate bounds for each cutout
                a_left = cutout_a.position.x - cutout_a.width / 2
                a_right = cutout_a.position.x + cutout_a.width / 2
                a_bottom = cutout_a.position.y - cutout_a.height / 2
                a_top = cutout_a.position.y + cutout_a.height / 2

                b_left = cutout_b.position.x - cutout_b.width / 2
                b_right = cutout_b.position.x + cutout_b.width / 2
                b_bottom = cutout_b.position.y - cutout_b.height / 2
                b_top = cutout_b.position.y + cutout_b.height / 2

                # Check for overlap (rectangles overlap if they don't not overlap)
                overlaps = not (
                    a_right <= b_left
                    or b_right <= a_left
                    or a_top <= b_bottom
                    or b_top <= a_bottom
                )

                if overlaps:
                    errors.append(
                        f"Cutout {i} ({cutout_a.cutout_type}) overlaps with "
                        f"cutout {j} ({cutout_b.cutout_type}) on {cutout_a.panel.value}"
                    )

        return errors

    def _cutout_to_dict(self, cutout: PanelCutout) -> dict[str, Any]:
        """Convert a PanelCutout to a serializable dictionary.

        Args:
            cutout: The PanelCutout to convert.

        Returns:
            Dictionary representation of the cutout.
        """
        result: dict[str, Any] = {
            "cutout_type": cutout.cutout_type,
            "panel": cutout.panel.value,
            "position": {"x": cutout.position.x, "y": cutout.position.y},
            "width": cutout.width,
            "height": cutout.height,
            "shape": cutout.shape.value,
        }
        if cutout.notes:
            result["notes"] = cutout.notes
        if cutout.diameter is not None:
            result["diameter"] = cutout.diameter
        return result


# --- Lighting Component ---


@component_registry.register("infrastructure.lighting")
class LightingComponent(_InfrastructureBase):
    """Lighting infrastructure component.

    Generates specifications for cabinet lighting including LED strips
    and puck lights. Supports under-cabinet, in-cabinet, and above-cabinet
    mounting locations.

    Configuration options:
        light_type: Type of lighting - "led_strip", "puck_light", or "accent"
        location: Installation location - "under_cabinet", "in_cabinet", "above_cabinet"
        section_indices: List of section indices where lighting is installed
        length: Length of LED strip in inches (required for led_strip type)
        puck_positions: List of {x, y} positions for puck lights
        puck_diameter: Diameter of puck lights (default: 2.5")

    Example:
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0, 1, 2],
            "length": 48.0,
        }
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate lighting configuration.

        Checks that:
        - light_type is valid
        - location is valid
        - section_indices are valid
        - LED strips have length specified
        - Puck light positions are within bounds

        Args:
            config: Lighting configuration dictionary.
            context: Component context with dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate light_type
        light_type_str = config.get("light_type", "led_strip")
        try:
            light_type = LightingType(light_type_str)
        except ValueError:
            valid_types = [lt.value for lt in LightingType]
            errors.append(
                f"Invalid light_type '{light_type_str}'. Must be one of: {valid_types}"
            )
            light_type = None

        # Validate location
        location_str = config.get("location", "under_cabinet")
        try:
            LightingLocation(location_str)
        except ValueError:
            valid_locations = [loc.value for loc in LightingLocation]
            errors.append(
                f"Invalid location '{location_str}'. Must be one of: {valid_locations}"
            )

        # Validate section indices
        section_indices = config.get("section_indices", [context.section_index])
        for idx in section_indices:
            # Use a reasonable maximum; in real usage this would come from cabinet config
            if idx < 0:
                errors.append(f"Section index {idx} cannot be negative")

        # LED strips require length
        if light_type == LightingType.LED_STRIP:
            length = config.get("length")
            if length is None:
                errors.append("LED strip lighting requires 'length' to be specified")
            elif length <= 0:
                errors.append("LED strip length must be positive")
            elif length > context.width * len(section_indices):
                warnings.append(
                    f'LED strip length ({length}") may exceed available space'
                )

        # Puck lights - validate positions if provided
        if light_type == LightingType.PUCK_LIGHT:
            puck_positions = config.get("puck_positions", [])
            puck_diameter = config.get("puck_diameter", 2.5)

            for i, pos in enumerate(puck_positions):
                if isinstance(pos, dict):
                    x, y = pos.get("x", 0), pos.get("y", 0)
                    position = Point2D(x, y)
                    edge_errors = self._validate_edge_distance(
                        position,
                        context.width,
                        context.depth,  # Puck lights on bottom panel
                        puck_diameter,
                        puck_diameter,
                    )
                    for err in edge_errors:
                        errors.append(f"Puck light {i + 1}: {err}")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate lighting specifications and hardware.

        Creates lighting specs for LED strips or puck lights, including
        cutout specifications for puck light installations.

        Args:
            config: Lighting configuration dictionary.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult containing hardware and lighting specs.
        """
        light_type = LightingType(config.get("light_type", "led_strip"))
        location = LightingLocation(config.get("location", "under_cabinet"))
        section_indices = config.get("section_indices", [context.section_index])

        hardware: list[HardwareItem] = []
        cutouts: list[dict[str, Any]] = []
        lighting_specs: list[LightingSpec] = []

        if light_type == LightingType.LED_STRIP:
            length = config.get("length", context.width)
            channel_width = config.get("channel_width", 0.5)
            channel_depth = config.get("channel_depth", 0.25)

            lighting_specs.append(
                LightingSpec(
                    light_type=light_type,
                    location=location,
                    section_indices=tuple(section_indices),
                    length=length,
                    channel_width=channel_width,
                    channel_depth=channel_depth,
                )
            )

            # Hardware for LED strip installation
            hardware.append(
                HardwareItem(
                    name="LED Strip Light",
                    quantity=1,
                    sku="LED-STRIP-WW",
                    notes=f'{length:.1f}" warm white LED strip',
                )
            )
            hardware.append(
                HardwareItem(
                    name="LED Aluminum Channel",
                    quantity=1,
                    sku="LED-CHANNEL-AL",
                    notes=f'{length:.1f}" aluminum channel with diffuser',
                )
            )
            hardware.append(
                HardwareItem(
                    name="LED Driver/Transformer",
                    quantity=1,
                    sku="LED-DRIVER-12V",
                    notes="12V LED driver",
                )
            )

        elif light_type == LightingType.PUCK_LIGHT:
            puck_positions = config.get("puck_positions", [])
            puck_diameter = config.get("puck_diameter", 2.5)

            # Determine target panel based on location
            target_panel = PanelType.BOTTOM
            if location == LightingLocation.IN_CABINET:
                target_panel = PanelType.TOP
            elif location == LightingLocation.ABOVE_CABINET:
                target_panel = PanelType.TOP

            for i, pos in enumerate(puck_positions):
                if isinstance(pos, dict):
                    position = Point2D(pos.get("x", 0), pos.get("y", 0))
                else:
                    continue

                lighting_specs.append(
                    LightingSpec(
                        light_type=light_type,
                        location=location,
                        section_indices=tuple(section_indices),
                        diameter=puck_diameter,
                        position=position,
                    )
                )

                # Create circular cutout for puck light
                cutout = PanelCutout(
                    cutout_type="puck_light",
                    panel=target_panel,
                    position=position,
                    width=puck_diameter,
                    height=puck_diameter,
                    shape=CutoutShape.CIRCULAR,
                    diameter=puck_diameter,
                    notes=f"Puck light {i + 1} cutout",
                )
                cutouts.append(self._cutout_to_dict(cutout))

            # Hardware for puck lights
            if puck_positions:
                hardware.append(
                    HardwareItem(
                        name=f'Puck Light ({puck_diameter}")',
                        quantity=len(puck_positions),
                        sku=f"PUCK-LED-{puck_diameter:.1f}",
                        notes="LED puck light with mounting ring",
                    )
                )
                hardware.append(
                    HardwareItem(
                        name="Puck Light Wire Harness",
                        quantity=1,
                        sku="PUCK-HARNESS",
                        notes=f"Wire harness for {len(puck_positions)} puck lights",
                    )
                )

        metadata: dict[str, Any] = {
            "lighting_specs": lighting_specs,
        }
        if cutouts:
            metadata["cutouts"] = cutouts

        return GenerationResult(
            hardware=tuple(hardware),
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for lighting component.

        Args:
            config: Lighting configuration dictionary.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for lighting hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


# --- Electrical Component ---


@component_registry.register("infrastructure.electrical")
class ElectricalComponent(_InfrastructureBase):
    """Electrical outlet infrastructure component.

    Generates cutout specifications for electrical outlets in cabinet
    panels. Supports single, double, and GFI outlet types.

    Configuration options:
        outlet_type: Type of outlet - "single", "double", or "gfi"
        panel: Panel where outlet is located (e.g., "back", "left_side")
        position: {x, y} position of outlet center on panel
        conduit_direction: Direction for conduit - "top", "bottom", "left", "right"

    Example:
        config = {
            "outlet_type": "double",
            "panel": "back",
            "position": {"x": 12.0, "y": 6.0},
            "conduit_direction": "bottom",
        }
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate electrical outlet configuration.

        Checks that:
        - outlet_type is valid
        - panel type is valid
        - Position is within panel bounds with edge clearance
        - Warns if outlet may be blocked by fixed shelf

        Args:
            config: Electrical configuration dictionary.
            context: Component context with dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate outlet_type
        outlet_type_str = config.get("outlet_type", "single")
        try:
            outlet_type = OutletType(outlet_type_str)
        except ValueError:
            valid_types = [ot.value for ot in OutletType]
            errors.append(
                f"Invalid outlet_type '{outlet_type_str}'. Must be one of: {valid_types}"
            )
            return ValidationResult(tuple(errors), tuple(warnings))

        # Validate panel
        panel_str = config.get("panel", "back")
        try:
            panel = PanelType(panel_str)
        except ValueError:
            valid_panels = [p.value for p in PanelType]
            errors.append(
                f"Invalid panel '{panel_str}'. Must be one of: {valid_panels}"
            )
            return ValidationResult(tuple(errors), tuple(warnings))

        # Get outlet dimensions
        outlet_spec = OutletSpec(
            outlet_type=outlet_type,
            section_index=context.section_index,
            panel=panel,
            position=Point2D(0, 0),  # Temporary
        )
        cutout_width, cutout_height = outlet_spec.cutout_dimensions

        # Get position and validate
        pos = config.get("position", {})
        if not isinstance(pos, dict):
            errors.append("Position must be a dictionary with 'x' and 'y' keys")
        else:
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            position = Point2D(x, y)

            # Determine panel dimensions based on panel type
            if panel in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE):
                panel_width = context.depth
                panel_height = context.height
            elif panel == PanelType.BACK:
                panel_width = context.width
                panel_height = context.height
            elif panel in (PanelType.TOP, PanelType.BOTTOM):
                panel_width = context.width
                panel_height = context.depth
            else:
                panel_width = context.width
                panel_height = context.height

            # Check edge distances
            edge_errors = self._validate_edge_distance(
                position,
                panel_width,
                panel_height,
                cutout_width,
                cutout_height,
            )
            errors.extend(edge_errors)

            # Warn if outlet might be blocked by fixed shelf
            if panel == PanelType.BACK and y < context.height * 0.5:
                warnings.append(
                    "Outlet position may be blocked if fixed shelves are installed above it"
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate outlet cutout specifications.

        Creates rectangular cutout specifications for electrical outlets.

        Args:
            config: Electrical configuration dictionary.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult containing cutout specifications in metadata.
        """
        outlet_type = OutletType(config.get("outlet_type", "single"))
        panel = PanelType(config.get("panel", "back"))
        pos = config.get("position", {"x": context.width / 2, "y": context.height / 3})
        position = Point2D(pos.get("x", 0), pos.get("y", 0))
        conduit_direction = config.get("conduit_direction", "bottom")

        outlet_spec = OutletSpec(
            outlet_type=outlet_type,
            section_index=context.section_index,
            panel=panel,
            position=position,
            conduit_direction=conduit_direction,
        )

        cutout_width, cutout_height = outlet_spec.cutout_dimensions

        cutout = PanelCutout(
            cutout_type="outlet",
            panel=panel,
            position=position,
            width=cutout_width,
            height=cutout_height,
            shape=CutoutShape.RECTANGULAR,
            notes=f"{outlet_type.value} outlet cutout, conduit {conduit_direction}",
        )

        metadata: dict[str, Any] = {
            "cutouts": [self._cutout_to_dict(cutout)],
            "outlet_spec": {
                "outlet_type": outlet_type.value,
                "section_index": outlet_spec.section_index,
                "panel": panel.value,
                "position": {"x": position.x, "y": position.y},
                "conduit_direction": conduit_direction,
                "cutout_width": cutout_width,
                "cutout_height": cutout_height,
            },
        }

        # No hardware items - electrical work is typically separate trade
        return GenerationResult(
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for electrical component.

        Electrical outlets are typically installed by electricians and
        don't require cabinet hardware, so this returns an empty list.

        Args:
            config: Electrical configuration dictionary.
            context: Component context with dimensions.

        Returns:
            Empty list - electrical hardware is separate trade.
        """
        return []


# --- Cable Management Component ---


@component_registry.register("infrastructure.cable_management")
class CableManagementComponent(_InfrastructureBase):
    """Cable management infrastructure component.

    Generates specifications for cable grommets that allow cables to pass
    through cabinet panels cleanly. Supports standard grommet sizes of
    2.0", 2.5", and 3.0" diameter.

    Configuration options:
        grommets: List of grommet specifications, each with:
            - size: Diameter in inches (2.0, 2.5, or 3.0)
            - panel: Panel where grommet is installed
            - position: {x, y} position on panel

    Example:
        config = {
            "grommets": [
                {"size": 2.5, "panel": "back", "position": {"x": 6.0, "y": 4.0}},
                {"size": 2.0, "panel": "bottom", "position": {"x": 12.0, "y": 6.0}},
            ]
        }
    """

    VALID_GROMMET_SIZES = {2.0, 2.5, 3.0}  # Standard sizes in inches
    GROMMET_SKU_MAP = {
        2.0: "GRM-200-BLK",
        2.5: "GRM-250-BLK",
        3.0: "GRM-300-BLK",
    }

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate cable management configuration.

        Checks that:
        - Grommet sizes are valid (2.0, 2.5, or 3.0 inches)
        - Panel types are valid
        - Positions are within panel bounds with edge clearance

        Args:
            config: Cable management configuration dictionary.
            context: Component context with dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        grommets = config.get("grommets", [])

        for i, grommet in enumerate(grommets):
            if not isinstance(grommet, dict):
                errors.append(f"Grommet {i + 1}: must be a dictionary")
                continue

            # Validate size
            size = grommet.get("size", 2.5)
            if size not in self.VALID_GROMMET_SIZES:
                errors.append(
                    f'Grommet {i + 1}: invalid size {size}". '
                    f"Must be one of: {sorted(self.VALID_GROMMET_SIZES)}"
                )

            # Validate panel
            panel_str = grommet.get("panel", "back")
            try:
                panel = PanelType(panel_str)
            except ValueError:
                valid_panels = [p.value for p in PanelType]
                errors.append(
                    f"Grommet {i + 1}: invalid panel '{panel_str}'. "
                    f"Must be one of: {valid_panels}"
                )
                continue

            # Validate position
            pos = grommet.get("position", {})
            if not isinstance(pos, dict):
                errors.append(f"Grommet {i + 1}: position must be a dictionary")
                continue

            x = pos.get("x", 0)
            y = pos.get("y", 0)
            position = Point2D(x, y)

            # Determine panel dimensions
            if panel in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE):
                panel_width = context.depth
                panel_height = context.height
            elif panel == PanelType.BACK:
                panel_width = context.width
                panel_height = context.height
            elif panel in (PanelType.TOP, PanelType.BOTTOM):
                panel_width = context.width
                panel_height = context.depth
            else:
                panel_width = context.width
                panel_height = context.height

            # Check edge distances (grommet is circular, so width = height = size)
            edge_errors = self._validate_edge_distance(
                position,
                panel_width,
                panel_height,
                size,
                size,
            )
            for err in edge_errors:
                errors.append(f"Grommet {i + 1}: {err}")

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate grommet cutout specifications and hardware.

        Creates circular cutout specifications for cable grommets and
        includes rubber grommet hardware items.

        Args:
            config: Cable management configuration dictionary.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult containing cutouts and hardware.
        """
        grommets = config.get("grommets", [])
        hardware: list[HardwareItem] = []
        cutouts: list[dict[str, Any]] = []
        grommet_specs: list[GrommetSpec] = []

        # Count grommets by size for hardware aggregation
        size_counts: dict[float, int] = {}

        for grommet in grommets:
            if not isinstance(grommet, dict):
                continue

            size = grommet.get("size", 2.5)
            panel = PanelType(grommet.get("panel", "back"))
            pos = grommet.get("position", {"x": 0, "y": 0})
            position = Point2D(pos.get("x", 0), pos.get("y", 0))
            section_index = grommet.get("section_index")

            grommet_specs.append(
                GrommetSpec(
                    size=size,
                    panel=panel,
                    position=position,
                    section_index=section_index,
                )
            )

            # Create circular cutout
            cutout = PanelCutout(
                cutout_type="grommet",
                panel=panel,
                position=position,
                width=size,
                height=size,
                shape=CutoutShape.CIRCULAR,
                diameter=size,
                notes=f'{size}" cable grommet',
            )
            cutouts.append(self._cutout_to_dict(cutout))

            # Count for hardware
            size_counts[size] = size_counts.get(size, 0) + 1

        # Generate hardware items grouped by size
        for size, count in sorted(size_counts.items()):
            sku = self.GROMMET_SKU_MAP.get(size, f"GRM-{int(size * 100)}-BLK")
            hardware.append(
                HardwareItem(
                    name=f'Rubber Grommet {size}"',
                    quantity=count,
                    sku=sku,
                    notes="Cable pass-through",
                )
            )

        metadata: dict[str, Any] = {
            "grommet_specs": grommet_specs,
        }
        if cutouts:
            metadata["cutouts"] = cutouts

        return GenerationResult(
            hardware=tuple(hardware),
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for cable management.

        Args:
            config: Cable management configuration dictionary.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for rubber grommets.
        """
        result = self.generate(config, context)
        return list(result.hardware)


# --- Ventilation Component ---


@component_registry.register("infrastructure.ventilation")
class VentilationComponent(_InfrastructureBase):
    """Ventilation infrastructure component.

    Generates specifications for ventilation areas in cabinet panels.
    Supports grid, slot, and circular hole patterns for airflow.

    Configuration options:
        pattern: Ventilation pattern - "grid", "slot", or "circular"
        panel: Panel where ventilation is located
        position: {x, y} position of ventilation area center
        width: Width of ventilation area in inches
        height: Height of ventilation area in inches
        hole_size: Diameter of individual holes (default: 0.25")
        electronics: Boolean indicating if cabinet contains electronics

    Example:
        config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 12.0, "y": 6.0},
            "width": 8.0,
            "height": 4.0,
            "hole_size": 0.25,
            "electronics": True,
        }
    """

    MIN_VENT_AREA_SQ_IN = 4.0  # Minimum ventilation area

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate ventilation configuration.

        Checks that:
        - Pattern is valid (grid, slot, circular)
        - Panel type is valid
        - Position/size are within panel bounds
        - Warns if electronics mentioned without adequate ventilation

        Args:
            config: Ventilation configuration dictionary.
            context: Component context with dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate pattern
        pattern_str = config.get("pattern", "grid")
        try:
            VentilationPattern(pattern_str)
        except ValueError:
            valid_patterns = [p.value for p in VentilationPattern]
            errors.append(
                f"Invalid pattern '{pattern_str}'. Must be one of: {valid_patterns}"
            )

        # Validate panel
        panel_str = config.get("panel", "back")
        try:
            panel = PanelType(panel_str)
        except ValueError:
            valid_panels = [p.value for p in PanelType]
            errors.append(
                f"Invalid panel '{panel_str}'. Must be one of: {valid_panels}"
            )
            return ValidationResult(tuple(errors), tuple(warnings))

        # Get ventilation area dimensions
        vent_width = config.get("width", 4.0)
        vent_height = config.get("height", 2.0)

        if vent_width <= 0:
            errors.append("Ventilation width must be positive")
        if vent_height <= 0:
            errors.append("Ventilation height must be positive")

        # Get position
        pos = config.get("position", {})
        if not isinstance(pos, dict):
            errors.append("Position must be a dictionary with 'x' and 'y' keys")
        else:
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            position = Point2D(x, y)

            # Determine panel dimensions
            if panel in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE):
                panel_width = context.depth
                panel_height = context.height
            elif panel == PanelType.BACK:
                panel_width = context.width
                panel_height = context.height
            elif panel in (PanelType.TOP, PanelType.BOTTOM):
                panel_width = context.width
                panel_height = context.depth
            else:
                panel_width = context.width
                panel_height = context.height

            # Check edge distances
            edge_errors = self._validate_edge_distance(
                position,
                panel_width,
                panel_height,
                vent_width,
                vent_height,
            )
            errors.extend(edge_errors)

        # Check for electronics advisory
        has_electronics = config.get("electronics", False)
        if has_electronics:
            vent_area = vent_width * vent_height
            if vent_area < self.MIN_VENT_AREA_SQ_IN:
                warnings.append(
                    f"Electronics present but ventilation area ({vent_area:.1f} sq in) "
                    f"is below recommended minimum ({self.MIN_VENT_AREA_SQ_IN} sq in)"
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate ventilation area specifications.

        Creates metadata specifying the ventilation pattern, location,
        and dimensions. The actual hole pattern is specified for
        manufacturing/cut list generation.

        Args:
            config: Ventilation configuration dictionary.
            context: Component context with dimensions and position.

        Returns:
            GenerationResult containing ventilation specifications.
        """
        pattern = VentilationPattern(config.get("pattern", "grid"))
        panel = PanelType(config.get("panel", "back"))
        pos = config.get("position", {"x": context.width / 2, "y": context.height / 4})
        position = Point2D(pos.get("x", 0), pos.get("y", 0))
        vent_width = config.get("width", 4.0)
        vent_height = config.get("height", 2.0)
        hole_size = config.get("hole_size", 0.25)

        # Calculate hole count for different patterns
        hole_count = 0
        if pattern == VentilationPattern.GRID:
            # Grid: holes spaced at 2x hole diameter
            spacing = hole_size * 2
            cols = int(vent_width / spacing)
            rows = int(vent_height / spacing)
            hole_count = cols * rows
        elif pattern == VentilationPattern.SLOT:
            # Slots: horizontal slots across the area
            slot_count = int(vent_height / (hole_size * 3))
            hole_count = slot_count  # Each slot is one cut
        elif pattern == VentilationPattern.CIRCULAR:
            # Circular: concentric rings of holes
            radius = min(vent_width, vent_height) / 2
            rings = int(radius / (hole_size * 3))
            # Approximate hole count per ring
            hole_count = sum(
                int(2 * math.pi * (i + 1) * hole_size * 3 / (hole_size * 2))
                for i in range(rings)
            )

        # Create a rectangular cutout entry for the ventilation area
        # The actual holes are specified in the pattern metadata
        cutout = PanelCutout(
            cutout_type="ventilation",
            panel=panel,
            position=position,
            width=vent_width,
            height=vent_height,
            shape=CutoutShape.RECTANGULAR,
            notes=f"{pattern.value} pattern ventilation, {hole_count} holes",
        )

        metadata: dict[str, Any] = {
            "ventilation_spec": {
                "pattern": pattern.value,
                "panel": panel.value,
                "position": {"x": position.x, "y": position.y},
                "width": vent_width,
                "height": vent_height,
                "hole_size": hole_size,
                "hole_count": hole_count,
            },
            "cutouts": [self._cutout_to_dict(cutout)],
        }

        # No specific hardware for ventilation - it's machined into the panel
        return GenerationResult(
            metadata=metadata,
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for ventilation.

        Ventilation is machined into panels and requires no additional
        hardware items.

        Args:
            config: Ventilation configuration dictionary.
            context: Component context with dimensions.

        Returns:
            Empty list - ventilation is machined, no hardware needed.
        """
        return []
