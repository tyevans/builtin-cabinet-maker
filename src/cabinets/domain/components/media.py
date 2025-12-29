"""Media and entertainment center component implementations for FRD-19.

Phase 1: Foundation - Core Media Infrastructure

This module provides media/entertainment center components for cabinet sections:
- Equipment dimension presets for common A/V devices
- Ventilation specifications for heat-generating equipment
- Equipment shelf with grommet cutouts
- Ventilated section for enclosed equipment
- Soundbar shelf with acoustic considerations
- Speaker alcove for built-in speaker placement

All components follow the Component protocol and register with the component_registry.

Media equipment typically requires:
- Greater depth than standard cabinets (16-20" vs 12")
- Proper ventilation for heat-generating devices
- Cable management via grommets and cable chases
- Acoustic considerations for audio equipment

Equipment Types and Heat Generation:
- Receivers, gaming consoles, and cable boxes generate significant heat
- Heat-generating equipment needs 8"+ vertical clearance
- Non-heat-generating equipment needs only 2" clearance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ..entities import Panel
from ..value_objects import (
    CutoutShape,
    EquipmentType,
    MaterialSpec,
    PanelCutout,
    PanelType,
    Point2D,
    Position,
    SoundbarType,
    SpeakerType,
)
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult


# =============================================================================
# Equipment Dimension Presets
# =============================================================================

# Equipment dimension presets: (width, height, depth) in inches
# These are standard dimensions for common media equipment
EQUIPMENT_PRESETS: dict[str, tuple[float, float, float]] = {
    "receiver": (17.5, 7.0, 18.0),
    "console_horizontal": (16.0, 4.0, 12.0),
    "console_vertical": (8.0, 12.0, 8.0),
    "streaming": (6.0, 2.0, 4.0),
    "cable_box": (12.0, 3.0, 10.0),
    "blu_ray": (14.0, 3.0, 10.0),
    "turntable": (18.0, 6.0, 14.0),
}

# Equipment types that generate heat and require additional ventilation
HEAT_GENERATING_EQUIPMENT: set[str] = {
    "receiver",
    "console_horizontal",
    "console_vertical",
    "cable_box",
}

# =============================================================================
# Clearance Constants
# =============================================================================

# Minimum equipment shelf depth (below this is an error)
MIN_EQUIPMENT_DEPTH: float = 12.0

# Recommended equipment shelf depth (below this is a warning)
RECOMMENDED_EQUIPMENT_DEPTH: float = 16.0

# Minimum vertical clearance above non-heat equipment
MIN_VERTICAL_CLEARANCE: float = 2.0

# Minimum vertical clearance above heat-generating equipment
HEAT_SOURCE_CLEARANCE: float = 8.0


# =============================================================================
# Specification Dataclasses
# =============================================================================


@dataclass(frozen=True)
class VentilationSpec:
    """Specification for ventilation in media sections.

    Represents the configuration for thermal management in enclosed
    media equipment compartments.

    Attributes:
        ventilation_type: Type of ventilation system.
            - "passive_rear": Back panel with vent cutouts (most common).
            - "passive_bottom": Bottom gaps for convection airflow.
            - "passive_slots": Slotted door panels for airflow.
            - "active_fan": Fan mounting cutout for active cooling.
            - "none": No ventilation (not recommended for heat sources).
        vent_pattern: Pattern of ventilation holes for passive_rear.
            One of: "grid", "slot", "mesh".
        open_area_percent: Percentage of panel area that is open (default 30%).
        fan_size_mm: Fan size in millimeters for active_fan type (80 or 120).
    """

    ventilation_type: Literal[
        "passive_rear", "passive_bottom", "passive_slots", "active_fan", "none"
    ]
    vent_pattern: Literal["grid", "slot", "mesh"] = "grid"
    open_area_percent: float = 30.0
    fan_size_mm: int | None = None

    def __post_init__(self) -> None:
        if self.open_area_percent < 0 or self.open_area_percent > 100:
            raise ValueError("open_area_percent must be between 0 and 100")
        if self.fan_size_mm is not None and self.fan_size_mm not in (80, 120):
            raise ValueError("fan_size_mm must be 80 or 120")


@dataclass(frozen=True)
class EquipmentSpec:
    """Specification for a piece of media equipment.

    Represents the dimensions and thermal properties of a media device
    for use in equipment shelf calculations.

    Attributes:
        equipment_type: Type identifier for the equipment.
        width: Equipment width in inches.
        height: Equipment height in inches.
        depth: Equipment depth in inches.
        generates_heat: True if the equipment generates significant heat.
        required_clearance: Minimum vertical clearance above equipment in inches.
    """

    equipment_type: str
    width: float
    height: float
    depth: float
    generates_heat: bool
    required_clearance: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.depth <= 0:
            raise ValueError("Equipment dimensions must be positive")
        if self.required_clearance < 0:
            raise ValueError("Required clearance cannot be negative")


# =============================================================================
# Helper Functions
# =============================================================================


def _get_equipment_spec(
    equipment_type: str, custom_dims: dict[str, Any] | None = None
) -> EquipmentSpec:
    """Get equipment specification from preset or custom dimensions.

    Retrieves standard equipment dimensions from presets or creates
    a custom specification from provided dimensions.

    Args:
        equipment_type: Type of equipment (must match EQUIPMENT_PRESETS key
            or be "custom").
        custom_dims: Optional dictionary with custom dimensions:
            - width: Equipment width in inches
            - height: Equipment height in inches
            - depth: Equipment depth in inches
            - generates_heat: Whether equipment generates heat (default False)
            - clearance: Required vertical clearance (default MIN_VERTICAL_CLEARANCE)

    Returns:
        EquipmentSpec with the equipment's dimensional and thermal properties.
    """
    if equipment_type == "custom" and custom_dims:
        return EquipmentSpec(
            equipment_type="custom",
            width=custom_dims.get("width", 17.0),
            height=custom_dims.get("height", 6.0),
            depth=custom_dims.get("depth", 14.0),
            generates_heat=custom_dims.get("generates_heat", False),
            required_clearance=custom_dims.get("clearance", MIN_VERTICAL_CLEARANCE),
        )

    if equipment_type in EQUIPMENT_PRESETS:
        w, h, d = EQUIPMENT_PRESETS[equipment_type]
        generates_heat = equipment_type in HEAT_GENERATING_EQUIPMENT
        clearance = HEAT_SOURCE_CLEARANCE if generates_heat else MIN_VERTICAL_CLEARANCE
        return EquipmentSpec(
            equipment_type=equipment_type,
            width=w,
            height=h,
            depth=d,
            generates_heat=generates_heat,
            required_clearance=clearance,
        )

    # Default fallback for unknown equipment types
    return EquipmentSpec(
        equipment_type="unknown",
        width=17.0,
        height=6.0,
        depth=14.0,
        generates_heat=False,
        required_clearance=MIN_VERTICAL_CLEARANCE,
    )


# =============================================================================
# Media Components
# =============================================================================


@component_registry.register("media.equipment_shelf")
class EquipmentShelfComponent:
    """Equipment shelf with proper depth and grommet cutout.

    Generates shelves for media equipment with appropriate depth,
    cable management grommets, and heat source considerations.

    Configuration options:
        equipment_type: Type of equipment (default: "receiver")
            One of: receiver, console_horizontal, console_vertical,
            streaming, cable_box, blu_ray, turntable, custom
        custom_dimensions: Dict with width, height, depth for custom equipment
        depth: Override shelf depth (default: auto-calculated from equipment)
        vertical_clearance: Override vertical space above equipment
        grommet_position: Position for cable grommet
            One of: "center_rear", "left_rear", "right_rear"
        grommet_diameter: Diameter of cable grommet in inches (default: 2.5)

    Example:
        config = {
            "equipment_type": "receiver",
            "grommet_position": "center_rear",
            "grommet_diameter": 2.5,
        }
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate equipment shelf configuration.

        Checks that:
        - Shelf depth is sufficient for equipment (minimum 12", warning at 16")
        - Vertical clearance is adequate for heat-generating equipment
        - Equipment width fits within section width

        Args:
            config: Equipment shelf configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        equipment_type = config.get("equipment_type", "receiver")
        equipment = _get_equipment_spec(equipment_type, config.get("custom_dimensions"))

        shelf_depth = config.get("depth", context.depth)
        vertical_clearance = config.get(
            "vertical_clearance", equipment.required_clearance + equipment.height
        )

        # Depth validation
        if shelf_depth < MIN_EQUIPMENT_DEPTH:
            errors.append(f"Shelf depth {shelf_depth}\" too shallow for equipment")
        elif shelf_depth < RECOMMENDED_EQUIPMENT_DEPTH:
            warnings.append(
                f"Shelf depth {shelf_depth}\" may be tight for A/V receivers"
            )

        # Clearance validation for heat sources
        if equipment.generates_heat:
            effective_clearance = vertical_clearance - equipment.height
            if effective_clearance < HEAT_SOURCE_CLEARANCE:
                warnings.append(
                    f"{equipment_type} generates heat; {effective_clearance:.1f}\" clearance "
                    f"may be insufficient (recommend {HEAT_SOURCE_CLEARANCE}\"+)"
                )

        # Width validation
        if equipment.width > context.width:
            errors.append(
                f"Equipment width {equipment.width}\" exceeds section width {context.width}\""
            )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate equipment shelf panels and hardware.

        Creates shelf panel with equipment-specific metadata and
        cable management grommet cutout.

        Args:
            config: Equipment shelf configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            GenerationResult with shelf panel, grommet cutout, and hardware.
        """
        equipment_type = config.get("equipment_type", "receiver")
        equipment = _get_equipment_spec(equipment_type, config.get("custom_dimensions"))

        depth = config.get("depth", max(context.depth, equipment.depth + 4))
        grommet_position = config.get("grommet_position", "center_rear")
        grommet_diameter = config.get("grommet_diameter", 2.5)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []
        cutouts: list[PanelCutout] = []

        # Equipment shelf panel - uses standard SHELF type with metadata
        shelf_panel = Panel(
            panel_type=PanelType.SHELF,
            width=context.width,
            height=depth,
            material=context.material,
            position=context.position,
            metadata={
                "component": "media.equipment_shelf",
                "equipment_type": equipment_type,
                "is_equipment_shelf": True,
                "generates_heat": equipment.generates_heat,
            },
        )
        panels.append(shelf_panel)

        # Calculate grommet position
        if grommet_position == "center_rear":
            grommet_x = context.width / 2
            grommet_y = depth - 2  # 2" from back edge
        elif grommet_position == "left_rear":
            grommet_x = context.width * 0.25
            grommet_y = depth - 2
        elif grommet_position == "right_rear":
            grommet_x = context.width * 0.75
            grommet_y = depth - 2
        else:
            grommet_x = context.width / 2
            grommet_y = depth - 2

        # Create grommet cutout
        cutouts.append(
            PanelCutout(
                cutout_type="cable_grommet",
                panel=PanelType.SHELF,
                position=Point2D(x=grommet_x, y=grommet_y),
                width=grommet_diameter,
                height=grommet_diameter,
                shape=CutoutShape.CIRCULAR,
                diameter=grommet_diameter,
                notes=f"Cable grommet for {equipment_type}",
            )
        )

        # Grommet hardware
        hardware.append(
            HardwareItem(
                name=f'Cable Grommet {grommet_diameter}"',
                quantity=1,
                sku=f"GROMMET-{grommet_diameter:.0f}",
                notes="Equipment shelf cable grommet",
            )
        )

        # Cable tie mounts for cable management
        hardware.append(
            HardwareItem(
                name="Cable Tie Mount",
                quantity=4,
                sku="CABLE-TIE-MOUNT",
                notes="Adhesive cable tie mounting points",
            )
        )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "cutouts": cutouts,
                "equipment_type": equipment_type,
                "generates_heat": equipment.generates_heat,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for equipment shelf.

        Args:
            config: Equipment shelf configuration dictionary.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for grommets and cable management.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("media.ventilated_section")
class VentilatedSectionComponent:
    """Section with thermal management for enclosed equipment.

    Generates back panel with ventilation cutouts or fan mounting
    for proper thermal management of enclosed media equipment.

    Configuration options:
        ventilation_type: Type of ventilation system (default: "passive_rear")
            One of: passive_rear, passive_bottom, passive_slots, active_fan, none
        vent_pattern: Pattern for passive ventilation (default: "grid")
            One of: grid, slot, mesh
        fan_size_mm: Fan size for active ventilation (default: 120)
            One of: 80, 120
        has_equipment: Whether section contains equipment (default: True)
        enclosed: Whether section is enclosed with doors (default: True)

    Example:
        config = {
            "ventilation_type": "passive_rear",
            "vent_pattern": "grid",
            "has_equipment": True,
            "enclosed": True,
        }
    """

    VENT_PATTERNS = ("grid", "slot", "mesh")
    FAN_SIZES = (80, 120)  # mm

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate ventilated section configuration.

        Checks that:
        - Enclosed equipment compartments have ventilation
        - Fan sizes are standard (80mm or 120mm)

        Args:
            config: Ventilated section configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        vent_type = config.get("ventilation_type", "passive_rear")
        has_equipment = config.get("has_equipment", True)
        is_enclosed = config.get("enclosed", True)

        # Enclosed equipment must have ventilation
        if has_equipment and is_enclosed and vent_type == "none":
            errors.append("Enclosed equipment compartments require ventilation")

        # Validate fan size for active ventilation
        if vent_type == "active_fan":
            fan_size = config.get("fan_size_mm", 120)
            if fan_size not in self.FAN_SIZES:
                warnings.append(
                    f"Non-standard fan size {fan_size}mm; use 80mm or 120mm"
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate ventilated section panels and hardware.

        Creates back panel with ventilation pattern or fan cutout,
        along with appropriate hardware (grilles, fans).

        Args:
            config: Ventilated section configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            GenerationResult with ventilated back panel and hardware.
        """
        vent_type = config.get("ventilation_type", "passive_rear")
        vent_pattern = config.get("vent_pattern", "grid")
        fan_size = config.get("fan_size_mm", 120)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []
        cutouts: list[PanelCutout] = []

        # Back panel with ventilation (if passive_rear)
        if vent_type == "passive_rear":
            back_panel = Panel(
                panel_type=PanelType.BACK,
                width=context.width,
                height=context.height,
                material=MaterialSpec.standard_1_4(),
                position=context.position,
                metadata={
                    "component": "media.ventilated_section",
                    "ventilation_type": vent_type,
                    "vent_pattern": vent_pattern,
                    "requires_vent_cutout": True,
                },
            )
            panels.append(back_panel)

            hardware.append(
                HardwareItem(
                    name="Ventilation Grille",
                    quantity=1,
                    sku="VENT-GRILLE-RECT",
                    notes=f"Back panel ventilation grille, {vent_pattern} pattern",
                )
            )

        # Fan cutout (if active_fan)
        if vent_type == "active_fan":
            fan_size_in = fan_size / 25.4  # mm to inches

            cutouts.append(
                PanelCutout(
                    cutout_type="cooling_fan",
                    panel=PanelType.BACK,
                    position=Point2D(x=context.width / 2, y=context.height / 2),
                    width=fan_size_in,
                    height=fan_size_in,
                    shape=CutoutShape.CIRCULAR,
                    diameter=fan_size_in,
                    notes=f"{fan_size}mm cooling fan mount",
                )
            )

            hardware.extend(
                [
                    HardwareItem(
                        name=f"Cooling Fan {fan_size}mm",
                        quantity=1,
                        sku=f"FAN-{fan_size}MM-QUIET",
                        notes="Low-noise DC cooling fan",
                    ),
                    HardwareItem(
                        name="Fan Power Adapter",
                        quantity=1,
                        sku="FAN-PWR-USB",
                        notes="USB power adapter for cooling fan",
                    ),
                ]
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "ventilation_type": vent_type,
                "vent_pattern": vent_pattern,
                "cutouts": cutouts,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for ventilated section.

        Args:
            config: Ventilated section configuration dictionary.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for ventilation hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("media.soundbar_shelf")
class SoundbarShelfComponent:
    """Open shelf for soundbar with acoustic considerations.

    Generates shelf for soundbar placement with proper clearances
    and open back for sound projection.

    Configuration options:
        soundbar_type: Size category (default: "standard")
            One of: compact (24"), standard (36"), premium (48"+), custom
        soundbar_width: Custom width for custom type (default: 36.0)
        soundbar_height: Custom height for custom type (default: 3.0)
        soundbar_depth: Custom depth for custom type (default: 4.0)
        dolby_atmos: Whether soundbar has Atmos upfiring drivers (default: False)
        side_clearance: Clearance from side walls (default: 12.0)
        ceiling_clearance: Clearance above soundbar (default: 36.0)
        enclosed: Whether soundbar is enclosed (must be False)
        below_equipment: Whether soundbar is below equipment (generates warning)
        include_mount: Include soundbar mounting bracket (default: False)

    Example:
        config = {
            "soundbar_type": "standard",
            "dolby_atmos": True,
            "side_clearance": 12.0,
        }
    """

    SOUNDBAR_PRESETS: dict[str, tuple[float, float, float]] = {
        "compact": (24.0, 3.0, 3.0),
        "standard": (36.0, 3.0, 4.0),
        "premium": (48.0, 4.0, 5.0),
    }

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate soundbar shelf configuration.

        Checks that:
        - Soundbar is not enclosed (critical for sound quality)
        - Side clearance is adequate for sound projection
        - Atmos soundbars have ceiling clearance for height effects
        - Soundbar is not below equipment that blocks sound

        Args:
            config: Soundbar shelf configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        enclosed = config.get("enclosed", False)
        has_atmos = config.get("dolby_atmos", False)
        side_clearance = config.get("side_clearance", 12.0)
        ceiling_clearance = config.get("ceiling_clearance", 36.0)

        # Critical: soundbars must not be enclosed
        if enclosed:
            errors.append("Soundbars must not be enclosed - sound will be muffled")

        # Side clearance validation
        if side_clearance < 6:
            warnings.append(
                f"Side clearance {side_clearance}\" may affect sound projection"
            )
        elif side_clearance < 12:
            warnings.append("Consider 12\"+ side clearance for optimal sound")

        # Atmos ceiling clearance
        if has_atmos and ceiling_clearance < 24:
            warnings.append(
                f"Ceiling clearance {ceiling_clearance}\" may affect Atmos height effects; "
                "recommend 24\"+"
            )

        # Check if soundbar is below equipment (bad for sound)
        if config.get("below_equipment", False):
            warnings.append(
                "Soundbar below equipment may have blocked sound projection"
            )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate soundbar shelf panels and hardware.

        Creates open shelf for soundbar placement (no back panel
        for proper sound projection).

        Args:
            config: Soundbar shelf configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            GenerationResult with soundbar shelf panel and optional mount.
        """
        soundbar_type = config.get("soundbar_type", "standard")

        if soundbar_type in self.SOUNDBAR_PRESETS:
            sb_width, sb_height, sb_depth = self.SOUNDBAR_PRESETS[soundbar_type]
        else:
            sb_width = config.get("soundbar_width", 36.0)
            sb_height = config.get("soundbar_height", 3.0)
            sb_depth = config.get("soundbar_depth", 4.0)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Soundbar shelf - open, no back panel
        shelf_panel = Panel(
            panel_type=PanelType.SHELF,
            width=context.width,
            height=sb_depth + 2,  # +2" for placement tolerance
            material=context.material,
            position=context.position,
            metadata={
                "component": "media.soundbar_shelf",
                "soundbar_type": soundbar_type,
                "is_soundbar_shelf": True,
                "open_back": True,  # Critical for sound
            },
        )
        panels.append(shelf_panel)

        # Soundbar mount hardware (optional)
        if config.get("include_mount", False):
            hardware.append(
                HardwareItem(
                    name="Soundbar Wall Mount Bracket",
                    quantity=1,
                    sku="SOUNDBAR-MOUNT-UNIV",
                    notes="Universal soundbar mounting bracket",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "soundbar_type": soundbar_type,
                "soundbar_dimensions": (sb_width, sb_height, sb_depth),
                "open_back": True,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for soundbar shelf.

        Args:
            config: Soundbar shelf configuration dictionary.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for soundbar mounting.
        """
        result = self.generate(config, context)
        return list(result.hardware)


@component_registry.register("media.speaker_alcove")
class SpeakerAlcoveComponent:
    """Alcove for speakers with acoustic considerations.

    Generates alcove panels for built-in speaker placement with
    proper clearances and open back for acoustic performance.

    Configuration options:
        speaker_type: Type of speaker (default: "center_channel")
            One of: center_channel, bookshelf, subwoofer
        speaker_width: Custom width (only for custom dimensions)
        speaker_height: Custom height (only for custom dimensions)
        speaker_depth: Custom depth (only for custom dimensions)
        alcove_height_from_floor: Height for center channel placement (default: 36.0)
        port_clearance: Clearance for subwoofer port (default: 4.0)
        include_dampening: Include acoustic foam recommendation (default: True)

    Example:
        config = {
            "speaker_type": "center_channel",
            "alcove_height_from_floor": 36.0,
            "include_dampening": True,
        }
    """

    SPEAKER_PRESETS: dict[str, tuple[float, float, float]] = {
        "center_channel": (24.0, 8.0, 12.0),
        "bookshelf": (8.0, 12.0, 10.0),
        "subwoofer": (15.0, 15.0, 18.0),
    }

    MIN_SUBWOOFER_PORT_CLEARANCE: float = 4.0

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate speaker alcove configuration.

        Checks that:
        - Center channel is at appropriate ear level (36-42" from floor)
        - Subwoofer has adequate port clearance

        Args:
            config: Speaker alcove configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        speaker_type = config.get("speaker_type", "center_channel")
        alcove_height = config.get("alcove_height_from_floor", 36.0)

        # Center channel ear level validation
        if speaker_type == "center_channel" and alcove_height < 30:
            warnings.append(
                f"Center channel at {alcove_height}\" may be below ear level; "
                "recommend 36-42\" for seated viewing"
            )

        # Subwoofer port clearance validation
        if speaker_type == "subwoofer":
            port_clearance = config.get("port_clearance", 4.0)
            if port_clearance < self.MIN_SUBWOOFER_PORT_CLEARANCE:
                errors.append(
                    f"Subwoofer port clearance {port_clearance}\" insufficient; "
                    f"minimum {self.MIN_SUBWOOFER_PORT_CLEARANCE}\" required"
                )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate speaker alcove panels and hardware.

        Creates alcove panels (sides and bottom, no back for acoustics)
        with optional acoustic dampening material.

        Args:
            config: Speaker alcove configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            GenerationResult with alcove panels and acoustic hardware.
        """
        speaker_type = config.get("speaker_type", "center_channel")

        if speaker_type in self.SPEAKER_PRESETS:
            sp_width, sp_height, sp_depth = self.SPEAKER_PRESETS[speaker_type]
        else:
            sp_width = config.get("speaker_width", 12.0)
            sp_height = config.get("speaker_height", 10.0)
            sp_depth = config.get("speaker_depth", 10.0)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Side panels for alcove
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=sp_depth + 2,
                height=sp_height + 2,
                material=context.material,
                position=context.position,
                metadata={
                    "component": "media.speaker_alcove",
                    "speaker_type": speaker_type,
                },
            )
        )
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=sp_depth + 2,
                height=sp_height + 2,
                material=context.material,
                position=Position(context.position.x + sp_width + 2, context.position.y),
                metadata={
                    "component": "media.speaker_alcove",
                    "speaker_type": speaker_type,
                },
            )
        )

        # Bottom panel (no back panel for acoustic reasons)
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=sp_width + 2,
                height=sp_depth + 2,
                material=context.material,
                position=context.position,
                metadata={
                    "component": "media.speaker_alcove",
                    "speaker_type": speaker_type,
                    "open_back": True,  # Acoustic requirement
                },
            )
        )

        # Acoustic dampening material recommendation
        if config.get("include_dampening", True):
            hardware.append(
                HardwareItem(
                    name="Acoustic Dampening Foam",
                    quantity=1,
                    sku="ACOUSTIC-FOAM-SHEET",
                    notes=f"For {speaker_type} alcove interior",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "speaker_type": speaker_type,
                "speaker_dimensions": (sp_width, sp_height, sp_depth),
                "open_back": True,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for speaker alcove.

        Args:
            config: Speaker alcove configuration dictionary.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for acoustic materials.
        """
        result = self.generate(config, context)
        return list(result.hardware)
