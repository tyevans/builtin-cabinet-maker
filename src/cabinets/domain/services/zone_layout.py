"""Zone layout service for FRD-22 Countertops and Vertical Zones.

This service orchestrates the generation of vertical zone configurations,
producing multiple cabinets, countertops, and gap zone metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..entities import Cabinet, Panel, Section, Shelf
from ..value_objects import (
    GapPurpose,
    MaterialSpec,
    PanelType,
    Position,
    ZoneMounting,
    ZoneType,
)
from ..vertical_zone import (
    VerticalZone,
    VerticalZoneStack,
    get_preset,
)
from ..components.context import ComponentContext
from ..components.countertop import CountertopSurfaceComponent
from ..components.results import HardwareItem


@dataclass(frozen=True)
class GapZoneMetadata:
    """Metadata for a gap zone (no panels generated).

    Attributes:
        purpose: Purpose of the gap (backsplash, mirror, hooks, etc.)
        width: Width of the gap zone in inches
        height: Height of the gap zone in inches
        bottom_height: Height from floor to bottom of gap
        notes: Additional notes about the gap zone
    """

    purpose: GapPurpose
    width: float
    height: float
    bottom_height: float
    notes: str = ""


@dataclass
class ZoneStackLayoutResult:
    """Result of zone stack layout generation.

    Contains all generated cabinets, panels, and metadata for
    a complete vertical zone configuration.
    """

    base_cabinet: Cabinet | None = None
    upper_cabinet: Cabinet | None = None
    countertop_panels: tuple[Panel, ...] = field(default_factory=tuple)
    gap_zones: tuple[GapZoneMetadata, ...] = field(default_factory=tuple)
    hardware: tuple[HardwareItem, ...] = field(default_factory=tuple)
    full_height_side_panels: tuple[Panel, ...] = field(default_factory=tuple)
    wall_nailer_panels: tuple[Panel, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def all_panels(self) -> tuple[Panel, ...]:
        """Get all generated panels across all zones."""
        panels: list[Panel] = []
        panels.extend(self.countertop_panels)
        panels.extend(self.full_height_side_panels)
        panels.extend(self.wall_nailer_panels)
        return tuple(panels)

    @property
    def has_errors(self) -> bool:
        """Check if the result has any errors."""
        return len(self.errors) > 0


@dataclass
class CountertopConfig:
    """Configuration for countertop generation.

    Attributes:
        thickness: Countertop thickness in inches (default: 1.0)
        front_overhang: Front overhang in inches (default: 1.0)
        left_overhang: Left side overhang in inches (default: 0.0)
        right_overhang: Right side overhang in inches (default: 0.0)
        back_overhang: Back overhang in inches (default: 0.0)
        edge_treatment: Edge treatment type (default: "square")
        support_brackets: Whether to include support brackets (default: False)
        material: Optional material override
    """

    thickness: float = 1.0
    front_overhang: float = 1.0
    left_overhang: float = 0.0
    right_overhang: float = 0.0
    back_overhang: float = 0.0
    edge_treatment: str = "square"
    support_brackets: bool = False
    material: dict[str, Any] | None = None


@dataclass
class ZoneLayoutConfig:
    """Configuration for zone layout generation.

    Attributes:
        preset: Zone preset name (kitchen, mudroom, vanity, hutch, custom)
        width: Total width of the zone stack in inches
        custom_zones: Custom zone definitions (required if preset=custom)
        countertop: Countertop configuration (None to skip countertop)
        full_height_sides: Whether side panels span all zones
        upper_cabinet_height: Height of upper zone (for presets)
        material: Default material for cabinets
    """

    preset: str = "custom"
    width: float = 48.0
    custom_zones: list[dict[str, Any]] | None = None
    countertop: CountertopConfig | None = None
    full_height_sides: bool = False
    upper_cabinet_height: float = 30.0
    material: MaterialSpec | None = None


class ZoneLayoutService:
    """Service for generating vertical zone stack layouts.

    This service coordinates the generation of:
    - Base cabinet (floor-mounted zones)
    - Upper cabinet (wall-mounted zones)
    - Countertop surface
    - Gap zones (backsplash, mirror, etc.)
    - Full-height side panels (stepped for depth changes)
    - Wall nailers for upper cabinet mounting
    """

    def __init__(self) -> None:
        self._countertop_component = CountertopSurfaceComponent()

    def generate(self, config: ZoneLayoutConfig) -> ZoneStackLayoutResult:
        """Generate a complete zone stack layout.

        Args:
            config: Zone layout configuration

        Returns:
            ZoneStackLayoutResult containing all generated elements
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Get zone stack from preset or custom config
        try:
            zone_stack = self._resolve_zone_stack(config)
        except ValueError as e:
            return ZoneStackLayoutResult(errors=(str(e),))

        # Validate zone stack
        validation_errors, validation_warnings = self._validate_zone_stack(
            zone_stack, config
        )
        errors.extend(validation_errors)
        warnings.extend(validation_warnings)

        if errors:
            return ZoneStackLayoutResult(
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

        # Generate base cabinet (floor-mounted zones)
        base_cabinet = self._generate_base_cabinet(zone_stack, config)

        # Generate upper cabinet (wall-mounted zones)
        upper_cabinet = self._generate_upper_cabinet(zone_stack, config)

        # Generate countertop
        countertop_panels: tuple[Panel, ...] = ()
        countertop_hardware: list[HardwareItem] = []
        if config.countertop is not None and base_cabinet is not None:
            countertop_result = self._generate_countertop(
                zone_stack, config, base_cabinet
            )
            countertop_panels = countertop_result.get("panels", ())
            countertop_hardware = list(countertop_result.get("hardware", ()))
            warnings.extend(countertop_result.get("warnings", []))

        # Generate gap zone metadata
        gap_zones = self._generate_gap_zones(zone_stack)

        # Generate wall nailers for upper cabinet
        wall_nailer_panels: tuple[Panel, ...] = ()
        nailer_hardware: list[HardwareItem] = []
        if upper_cabinet is not None:
            nailer_result = self._generate_wall_nailer(zone_stack, config)
            wall_nailer_panels = nailer_result.get("panels", ())
            nailer_hardware = list(nailer_result.get("hardware", ()))

        # Generate full-height side panels if requested
        full_height_side_panels: tuple[Panel, ...] = ()
        if config.full_height_sides or zone_stack.full_height_sides:
            full_height_side_panels = self._generate_full_height_sides(
                zone_stack, config
            )

        # Combine all hardware
        all_hardware = tuple(countertop_hardware + nailer_hardware)

        return ZoneStackLayoutResult(
            base_cabinet=base_cabinet,
            upper_cabinet=upper_cabinet,
            countertop_panels=countertop_panels,
            gap_zones=gap_zones,
            hardware=all_hardware,
            full_height_side_panels=full_height_side_panels,
            wall_nailer_panels=wall_nailer_panels,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _resolve_zone_stack(self, config: ZoneLayoutConfig) -> VerticalZoneStack:
        """Resolve zone stack from preset or custom configuration."""
        if config.preset.lower() == "custom":
            if not config.custom_zones:
                raise ValueError(
                    "Custom zone configuration requires 'custom_zones' list"
                )
            return self._build_custom_zone_stack(config)
        else:
            return get_preset(config.preset, width=config.width)

    def _build_custom_zone_stack(self, config: ZoneLayoutConfig) -> VerticalZoneStack:
        """Build a zone stack from custom zone definitions."""
        zones: list[VerticalZone] = []

        for zone_def in config.custom_zones or []:
            zone_type = ZoneType(zone_def.get("zone_type", "base"))
            mounting = ZoneMounting(zone_def.get("mounting", "floor"))
            gap_purpose = None
            if zone_def.get("gap_purpose"):
                gap_purpose = GapPurpose(zone_def["gap_purpose"])

            zone = VerticalZone(
                zone_type=zone_type,
                height=zone_def.get("height", 30.0),
                depth=zone_def.get("depth", 0.0 if zone_type == ZoneType.GAP else 24.0),
                mounting=mounting,
                sections=tuple(zone_def.get("sections", [])),
                gap_purpose=gap_purpose,
                mounting_height=zone_def.get("mounting_height"),
            )
            zones.append(zone)

        return VerticalZoneStack(
            zones=tuple(zones),
            total_width=config.width,
            full_height_sides=config.full_height_sides,
        )

    def _validate_zone_stack(
        self, zone_stack: VerticalZoneStack, config: ZoneLayoutConfig
    ) -> tuple[list[str], list[str]]:
        """Validate the zone stack configuration."""
        errors: list[str] = []
        warnings: list[str] = []

        # Check total height
        total_height = zone_stack.total_height
        if config.countertop:
            total_height += config.countertop.thickness

        # Typical max wall height
        if total_height > 120:  # 10 feet
            warnings.append(
                f'Zone stack total height ({total_height:.1f}") is very tall. '
                "Verify this fits your space."
            )

        # Check for floor-mounted zones
        floor_zones = [z for z in zone_stack.zones if z.mounting == ZoneMounting.FLOOR]
        if not floor_zones:
            errors.append("Zone stack must have at least one floor-mounted zone")

        # Check bench height if present
        for zone in zone_stack.zones:
            if zone.zone_type == ZoneType.BENCH:
                if zone.height < 16 or zone.height > 22:
                    warnings.append(
                        f'Bench height {zone.height}" is outside comfortable '
                        f'sitting range (16-22")'
                    )

        # Check backsplash height if present
        for zone in zone_stack.zones:
            if zone.gap_purpose == GapPurpose.BACKSPLASH:
                if zone.height < 15:
                    warnings.append(
                        f'Backsplash zone height {zone.height}" may be too short '
                        'for outlets (standard: 18")'
                    )

        # Check upper zone depth vs base zone depth
        base_zones = zone_stack.base_zones
        upper_zones = zone_stack.upper_zones
        if base_zones and upper_zones:
            base_depth = max(z.depth for z in base_zones)
            for upper in upper_zones:
                if upper.depth > base_depth:
                    warnings.append(
                        f'Upper zone depth ({upper.depth}") exceeds base depth '
                        f'({base_depth}"), creating overhang'
                    )

        return errors, warnings

    def _generate_base_cabinet(
        self, zone_stack: VerticalZoneStack, config: ZoneLayoutConfig
    ) -> Cabinet | None:
        """Generate cabinet for floor-mounted zones."""
        floor_zones = [z for z in zone_stack.zones if z.mounting == ZoneMounting.FLOOR]

        if not floor_zones:
            return None

        # Use the first floor zone for dimensions
        # (typically there's only one base zone)
        primary_zone = floor_zones[0]

        # Build sections from zone definitions
        sections = self._build_sections_from_zone(
            primary_zone, config, zone_stack.total_width
        )

        material = config.material or MaterialSpec(thickness=0.75)

        return Cabinet(
            width=zone_stack.total_width,
            height=primary_zone.height,
            depth=primary_zone.depth,
            material=material,
            sections=sections,
        )

    def _generate_upper_cabinet(
        self, zone_stack: VerticalZoneStack, config: ZoneLayoutConfig
    ) -> Cabinet | None:
        """Generate cabinet for wall-mounted zones."""
        wall_zones = [
            z
            for z in zone_stack.zones
            if z.mounting == ZoneMounting.WALL and z.zone_type != ZoneType.GAP
        ]

        if not wall_zones:
            return None

        # Use the first wall zone for dimensions
        primary_zone = wall_zones[0]

        # Build sections from zone definitions
        sections = self._build_sections_from_zone(
            primary_zone, config, zone_stack.total_width
        )

        material = config.material or MaterialSpec(thickness=0.75)

        return Cabinet(
            width=zone_stack.total_width,
            height=primary_zone.height,
            depth=primary_zone.depth,
            material=material,
            sections=sections,
        )

    def _build_sections_from_zone(
        self, zone: VerticalZone, config: ZoneLayoutConfig, cabinet_width: float
    ) -> list[Section]:
        """Build cabinet sections from zone definition."""
        sections: list[Section] = []
        material = config.material or MaterialSpec(thickness=0.75)

        if zone.sections:
            # Calculate section widths from zone section definitions
            section_defs = list(zone.sections)
            num_sections = len(section_defs)

            # Calculate interior width (cabinet width minus side panels)
            interior_width = cabinet_width - (2 * material.thickness)

            # Calculate divider space
            num_dividers = max(0, num_sections - 1)
            divider_space = num_dividers * material.thickness
            available_width = interior_width - divider_space

            # Calculate fixed and fill widths
            fixed_width_total = 0.0
            fill_count = 0
            for section_def in section_defs:
                width_val = section_def.get("width", "fill")
                if width_val == "fill":
                    fill_count += 1
                else:
                    fixed_width_total += float(width_val)

            # Calculate fill section width
            remaining_width = available_width - fixed_width_total
            fill_width = remaining_width / fill_count if fill_count > 0 else 0

            # Build sections with resolved widths
            current_x = material.thickness
            for section_def in section_defs:
                width_val = section_def.get("width", "fill")
                if width_val == "fill":
                    section_width = fill_width
                else:
                    section_width = float(width_val)

                shelves_list: list[Shelf] = []
                shelf_count = section_def.get("shelves", 0)

                # Calculate interior height for shelves
                section_interior_height = zone.height - (2 * material.thickness)
                section_interior_depth = zone.depth - 0.25  # Back panel

                if shelf_count > 0:
                    # Evenly space shelves
                    shelf_spacing = section_interior_height / (shelf_count + 1)
                    for i in range(shelf_count):
                        shelf_y = material.thickness + shelf_spacing * (i + 1)
                        shelves_list.append(
                            Shelf(
                                width=section_width,
                                depth=section_interior_depth,
                                material=material,
                                position=Position(x=current_x, y=shelf_y),
                            )
                        )

                section = Section(
                    width=section_width,
                    height=zone.height - (2 * material.thickness),
                    depth=section_interior_depth,
                    position=Position(x=current_x, y=material.thickness),
                    shelves=shelves_list,
                )
                sections.append(section)

                current_x += section_width + material.thickness
        else:
            # Default: single open section using full interior width
            interior_width = cabinet_width - (2 * material.thickness)
            section_interior_height = zone.height - (2 * material.thickness)
            section_interior_depth = zone.depth - 0.25  # Back panel

            # Create 3 default shelves
            shelves_list = []
            shelf_spacing = section_interior_height / 4
            for i in range(3):
                shelf_y = material.thickness + shelf_spacing * (i + 1)
                shelves_list.append(
                    Shelf(
                        width=interior_width,
                        depth=section_interior_depth,
                        material=material,
                        position=Position(x=material.thickness, y=shelf_y),
                    )
                )

            sections.append(
                Section(
                    width=interior_width,
                    height=section_interior_height,
                    depth=section_interior_depth,
                    position=Position(x=material.thickness, y=material.thickness),
                    shelves=shelves_list,
                )
            )

        return sections

    def _generate_countertop(
        self,
        zone_stack: VerticalZoneStack,
        config: ZoneLayoutConfig,
        base_cabinet: Cabinet,
    ) -> dict[str, Any]:
        """Generate countertop using the CountertopSurfaceComponent."""
        ct_config = config.countertop
        if ct_config is None:
            return {"panels": (), "hardware": (), "warnings": []}

        # Find base zone height for countertop position
        base_height = base_cabinet.height
        material = config.material or MaterialSpec(thickness=0.75)

        # Create component context
        context = ComponentContext(
            width=zone_stack.total_width,
            height=ct_config.thickness,
            depth=base_cabinet.depth,
            material=material,
            position=Position(x=0, y=base_height),
            section_index=0,
            cabinet_width=zone_stack.total_width,
            cabinet_height=base_height + ct_config.thickness,
            cabinet_depth=base_cabinet.depth,
        )

        # Build component config
        component_config: dict[str, Any] = {
            "thickness": ct_config.thickness,
            "front_overhang": ct_config.front_overhang,
            "left_overhang": ct_config.left_overhang,
            "right_overhang": ct_config.right_overhang,
            "back_overhang": ct_config.back_overhang,
            "edge_treatment": ct_config.edge_treatment,
            "support_brackets": ct_config.support_brackets,
        }
        if ct_config.material:
            component_config["material"] = ct_config.material

        # Validate
        validation = self._countertop_component.validate(component_config, context)
        warnings = list(validation.warnings)

        # Generate
        result = self._countertop_component.generate(component_config, context)

        return {
            "panels": result.panels,
            "hardware": result.hardware,
            "warnings": warnings,
        }

    def _generate_gap_zones(
        self, zone_stack: VerticalZoneStack
    ) -> tuple[GapZoneMetadata, ...]:
        """Generate metadata for gap zones."""
        gap_zones: list[GapZoneMetadata] = []

        current_height = 0.0
        for zone in zone_stack.zones:
            if zone.zone_type == ZoneType.GAP and zone.gap_purpose:
                gap_zones.append(
                    GapZoneMetadata(
                        purpose=zone.gap_purpose,
                        width=zone_stack.total_width,
                        height=zone.height,
                        bottom_height=current_height,
                        notes=f"{zone.gap_purpose.value.title()} zone - no cabinet panels",
                    )
                )
            current_height += zone.height

        return tuple(gap_zones)

    def _generate_wall_nailer(
        self, zone_stack: VerticalZoneStack, config: ZoneLayoutConfig
    ) -> dict[str, Any]:
        """Generate wall nailer for upper cabinet mounting."""
        wall_zones = zone_stack.upper_zones
        if not wall_zones:
            return {"panels": (), "hardware": ()}

        primary_zone = wall_zones[0]
        material = config.material or MaterialSpec(thickness=0.75)

        # Standard nailer dimensions
        nailer_height = 3.0  # 3" tall

        # Position nailer at top of upper cabinet back
        mounting_height = primary_zone.mounting_height or 54.0
        nailer_y = mounting_height + primary_zone.height - nailer_height

        nailer_panel = Panel(
            panel_type=PanelType.NAILER,
            width=zone_stack.total_width - 1.5,  # Inside side panels
            height=nailer_height,
            material=material,
            position=Position(x=0.75, y=nailer_y),
            metadata={
                "component": "zone.layout",
                "zone": "upper",
                "purpose": "wall_mounting",
                "label": "Wall Nailer",
            },
        )

        # Wall mounting hardware
        # Assume studs every 16", need at least 2 screws
        stud_count = max(2, int(zone_stack.total_width / 16) + 1)
        hardware = [
            HardwareItem(
                name='Wall Mounting Screw #10 x 3"',
                quantity=stud_count * 2,  # 2 screws per stud
                sku="SCREW-10-3",
                notes='For mounting nailer to wall studs (every 16")',
            ),
        ]

        return {
            "panels": (nailer_panel,),
            "hardware": tuple(hardware),
        }

    def _generate_full_height_sides(
        self, zone_stack: VerticalZoneStack, config: ZoneLayoutConfig
    ) -> tuple[Panel, ...]:
        """Generate full-height side panels that span all zones.

        If zones have different depths, generates stepped side panels.
        """
        panels: list[Panel] = []
        material = config.material or MaterialSpec(thickness=0.75)

        # Calculate total height including countertop
        total_height = zone_stack.total_height
        if config.countertop:
            total_height += config.countertop.thickness

        # Find max depth across all non-gap zones
        non_gap_zones = [z for z in zone_stack.zones if z.zone_type != ZoneType.GAP]
        if not non_gap_zones:
            return ()

        max_depth = max(z.depth for z in non_gap_zones)

        # Check if we need stepped panels (different depths)
        depths = set(z.depth for z in non_gap_zones)
        is_stepped = len(depths) > 1

        if is_stepped:
            panel_type = PanelType.STEPPED_SIDE
            label = "Stepped Side Panel"
        else:
            panel_type = PanelType.LEFT_SIDE
            label = "Full Height Side Panel"

        # Left side panel
        left_panel = Panel(
            panel_type=panel_type,
            width=max_depth,
            height=total_height,
            material=material,
            position=Position(x=0, y=0),
            metadata={
                "component": "zone.layout",
                "is_full_height": True,
                "is_stepped": is_stepped,
                "side": "left",
                "label": f"Left {label}",
            },
        )
        panels.append(left_panel)

        # Right side panel
        right_panel = Panel(
            panel_type=panel_type if is_stepped else PanelType.RIGHT_SIDE,
            width=max_depth,
            height=total_height,
            material=material,
            position=Position(x=zone_stack.total_width - material.thickness, y=0),
            metadata={
                "component": "zone.layout",
                "is_full_height": True,
                "is_stepped": is_stepped,
                "side": "right",
                "label": f"Right {label}",
            },
        )
        panels.append(right_panel)

        return tuple(panels)
