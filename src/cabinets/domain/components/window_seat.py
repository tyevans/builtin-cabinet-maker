"""Window seat storage component for bay window alcoves (FRD-23).

This module provides window seat components for bay window alcove built-ins,
including:
- WindowSeatStorageComponent: Storage cabinet topped with a seat surface
- MullionFillerComponent: Filler panel for narrow mullion zones

Window seats are designed for placement below windows in bay alcoves and
support multiple access types for the storage compartment.
"""

from __future__ import annotations

from typing import Any

from ..entities import Panel
from ..value_objects import MaterialSpec, PanelType, Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult

# Standard window seat dimensions (inches)
MIN_SEAT_HEIGHT = 14.0
MAX_SEAT_HEIGHT = 22.0
DEFAULT_SEAT_HEIGHT = 18.0
DEFAULT_SEAT_DEPTH = 16.0
SEAT_THICKNESS = 0.75

# Minimum dimensions for practical window seat
MIN_SEAT_WIDTH = 12.0
MIN_SEAT_DEPTH = 12.0

# Access type constants
ACCESS_HINGED_TOP = "hinged_top"
ACCESS_FRONT_DOORS = "front_doors"
ACCESS_DRAWERS = "drawers"
VALID_ACCESS_TYPES = (ACCESS_HINGED_TOP, ACCESS_FRONT_DOORS, ACCESS_DRAWERS)

# Edge treatment options
VALID_EDGE_TREATMENTS = ("square", "bullnose", "eased")

# Mullion filler constants
MAX_MULLION_WIDTH = 12.0
MIN_MULLION_WIDTH = 1.0


@component_registry.register("windowseat.storage")
class WindowSeatStorageComponent:
    """Window seat storage component for bay window alcoves.

    Generates a storage cabinet topped with a seat surface, designed
    for placement below windows in bay alcoves. Supports multiple
    access types: hinged top (traditional window seat), front doors,
    or drawers.

    Configuration options:
        seat_height: Total height including seat surface (14-22 inches)
        seat_depth: Depth of the seat surface (default: context.depth)
        access_type: "hinged_top", "front_doors", or "drawers"
        edge_treatment: "square", "bullnose", or "eased"
        cushion_recess: Depth to recess for cushion accommodation
        cushion_thickness: Expected cushion thickness for ergonomic warnings

    Panel Generation:
        - Seat surface panel (horizontal top)
        - Left and right side panels
        - Bottom panel
        - Back panel (1/4" material)
        - Access-specific panels (doors or drawer fronts)

    Hardware Generation:
        - Hinged top: Piano hinge + soft-close lid stays
        - Front doors: European hinges (2 per door)
        - Drawers: Full extension drawer slides
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate window seat configuration.

        Checks:
        - Seat height within valid range (14-22")
        - Warning for heights above comfortable range
        - Access type is valid
        - Cushion thickness is reasonable
        - Context dimensions are sufficient

        Args:
            config: Window seat configuration dictionary with optional keys:
                - seat_height: Height of seat surface (default: 18")
                - access_type: Access type (default: "hinged_top")
                - cushion_thickness: Expected cushion thickness (default: 0)

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        seat_height = config.get("seat_height", DEFAULT_SEAT_HEIGHT)
        access_type = config.get("access_type", ACCESS_HINGED_TOP)
        cushion_thickness = config.get("cushion_thickness", 0)

        # Validate seat height
        if seat_height < MIN_SEAT_HEIGHT:
            errors.append(
                f'Seat height {seat_height}" below minimum {MIN_SEAT_HEIGHT}"'
            )
        if seat_height > MAX_SEAT_HEIGHT:
            warnings.append(
                f'Seat height {seat_height}" above comfortable range '
                f'(max {MAX_SEAT_HEIGHT}")'
            )

        # Validate access type
        if access_type not in VALID_ACCESS_TYPES:
            errors.append(
                f"Invalid access type '{access_type}'. "
                f"Must be one of: {', '.join(VALID_ACCESS_TYPES)}"
            )

        # Validate cushion thickness
        if cushion_thickness > 6:
            warnings.append(
                f'Cushion thickness {cushion_thickness}" may make seat '
                "uncomfortably high"
            )
        if cushion_thickness < 0:
            errors.append("Cushion thickness cannot be negative")

        # Validate edge treatment if specified
        edge_treatment = config.get("edge_treatment", "eased")
        if edge_treatment not in VALID_EDGE_TREATMENTS:
            errors.append(
                f"Invalid edge treatment '{edge_treatment}'. "
                f"Must be one of: {', '.join(VALID_EDGE_TREATMENTS)}"
            )

        # Validate context dimensions
        if context.width < MIN_SEAT_WIDTH:
            errors.append(
                f'Width {context.width}" too narrow for window seat '
                f'(min {MIN_SEAT_WIDTH}")'
            )
        if context.depth < MIN_SEAT_DEPTH:
            errors.append(
                f'Depth {context.depth}" too shallow for window seat '
                f'(min {MIN_SEAT_DEPTH}")'
            )

        # Validate cushion recess
        cushion_recess = config.get("cushion_recess", 0)
        if cushion_recess < 0:
            errors.append("Cushion recess cannot be negative")
        if cushion_recess > 2:
            warnings.append(
                f'Cushion recess {cushion_recess}" is deep; ensure structural '
                "integrity of seat surface"
            )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate window seat panels and hardware.

        Creates:
        - Seat surface panel (PanelType.SEAT_SURFACE)
        - Left and right side panels
        - Bottom panel
        - Back panel (1/4" material)
        - Access-specific panels and hardware

        Args:
            config: Window seat configuration dictionary with optional keys:
                - seat_height: Height of seat surface (default: 18")
                - seat_depth: Depth of seat (default: context.depth)
                - access_type: Access type (default: "hinged_top")
                - edge_treatment: Edge type (default: "eased")
                - cushion_recess: Recess depth for cushion (default: 0)

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing window seat panels, hardware
            requirements, and metadata with access type and dimensions.
        """
        seat_height = config.get("seat_height", DEFAULT_SEAT_HEIGHT)
        seat_depth = config.get("seat_depth", context.depth)
        access_type = config.get("access_type", ACCESS_HINGED_TOP)
        edge_treatment = config.get("edge_treatment", "eased")
        cushion_recess = config.get("cushion_recess", 0)

        panels: list[Panel] = []
        hardware: list[HardwareItem] = []

        # Box height is total height minus seat surface thickness
        box_height = seat_height - SEAT_THICKNESS

        # Calculate interior width (accounting for side panels)
        interior_width = context.width - (2 * context.material.thickness)

        # Seat surface panel (horizontal top)
        seat_surface = Panel(
            panel_type=PanelType.SEAT_SURFACE,
            width=context.width,
            height=seat_depth,  # For horizontal panels, "height" is depth
            material=context.material,
            position=Position(0, seat_height - SEAT_THICKNESS),
            metadata={
                "component": "windowseat.storage",
                "is_seat_surface": True,
                "edge_treatment": edge_treatment,
                "cushion_recess": cushion_recess,
                "orientation": "horizontal",
            },
        )
        panels.append(seat_surface)

        # Left side panel
        panels.append(
            Panel(
                panel_type=PanelType.LEFT_SIDE,
                width=seat_depth,
                height=box_height,
                material=context.material,
                position=Position(0, 0),
                metadata={"component": "windowseat.storage"},
            )
        )

        # Right side panel
        panels.append(
            Panel(
                panel_type=PanelType.RIGHT_SIDE,
                width=seat_depth,
                height=box_height,
                material=context.material,
                position=Position(context.width - context.material.thickness, 0),
                metadata={"component": "windowseat.storage"},
            )
        )

        # Bottom panel
        panels.append(
            Panel(
                panel_type=PanelType.BOTTOM,
                width=interior_width,
                height=seat_depth,
                material=context.material,
                position=Position(context.material.thickness, 0),
                metadata={"component": "windowseat.storage"},
            )
        )

        # Back panel (typically 1/4" material)
        back_material = MaterialSpec.standard_1_4()
        panels.append(
            Panel(
                panel_type=PanelType.BACK,
                width=context.width,
                height=seat_height,
                material=back_material,
                position=Position(0, 0),
                metadata={"component": "windowseat.storage"},
            )
        )

        # Generate access-specific panels and hardware
        if access_type == ACCESS_HINGED_TOP:
            hardware.extend(self._generate_hinged_top_hardware(context.width))
        elif access_type == ACCESS_FRONT_DOORS:
            door_panels, door_hardware = self._generate_front_doors(
                interior_width, box_height, context.material
            )
            panels.extend(door_panels)
            hardware.extend(door_hardware)
        elif access_type == ACCESS_DRAWERS:
            drawer_panels, drawer_hardware = self._generate_drawers(
                interior_width, box_height, seat_depth, context.material
            )
            panels.extend(drawer_panels)
            hardware.extend(drawer_hardware)

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={
                "access_type": access_type,
                "seat_height": seat_height,
                "seat_depth": seat_depth,
                "edge_treatment": edge_treatment,
                "cushion_recess": cushion_recess,
                "box_height": box_height,
                "interior_width": interior_width,
            },
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for window seat.

        Window seat hardware varies by access type:
        - Hinged top: Piano hinge + soft-close lid stays
        - Front doors: European hinges (2 per door)
        - Drawers: Full extension drawer slides

        Args:
            config: Window seat configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            List of HardwareItem objects for window seat hardware.
        """
        result = self.generate(config, context)
        return list(result.hardware)

    def _generate_hinged_top_hardware(self, width: float) -> list[HardwareItem]:
        """Generate hardware for hinged top access.

        Hinged top access requires:
        - Piano hinge along the back edge for smooth operation
        - Soft-close lid stays for safety and convenience

        Args:
            width: Width of the window seat in inches.

        Returns:
            List of HardwareItem objects for hinged top hardware.
        """
        return [
            HardwareItem(
                name="Piano Hinge",
                quantity=1,
                sku="PIANO-36",
                notes=f'{width:.0f}" length for hinged seat lid',
            ),
            HardwareItem(
                name="Soft-Close Lid Stay",
                quantity=2,
                sku="LID-STAY-SC",
                notes="One per side for balanced support and safety",
            ),
        ]

    def _generate_front_doors(
        self, interior_width: float, box_height: float, material: MaterialSpec
    ) -> tuple[list[Panel], list[HardwareItem]]:
        """Generate panels and hardware for front door access.

        Front door access divides the front into one or more doors
        based on the interior width. Each door gets 2 European hinges.

        Args:
            interior_width: Interior width of the cabinet box in inches.
            box_height: Height of the cabinet box in inches.
            material: Material specification for door panels.

        Returns:
            Tuple of (list of door panels, list of hardware items).
        """
        # Determine number of doors based on width
        # Doors wider than 24" are unwieldy, so we add more doors
        door_count = max(1, int(interior_width / 24))
        door_width = interior_width / door_count

        panels = []
        for i in range(door_count):
            panels.append(
                Panel(
                    panel_type=PanelType.DOOR,
                    width=door_width,
                    height=box_height,
                    material=material,
                    position=Position(material.thickness + i * door_width, 0),
                    metadata={
                        "component": "windowseat.storage",
                        "door_index": i,
                        "door_count": door_count,
                    },
                )
            )

        hardware = [
            HardwareItem(
                name="European Hinge 110-degree",
                quantity=door_count * 2,
                sku="EURO-HINGE-110",
                notes=f"2 hinges per door, {door_count} door(s)",
            ),
        ]

        return panels, hardware

    def _generate_drawers(
        self,
        interior_width: float,
        box_height: float,
        depth: float,
        material: MaterialSpec,
    ) -> tuple[list[Panel], list[HardwareItem]]:
        """Generate panels and hardware for drawer access.

        Drawer access creates a single large drawer for the window seat
        storage compartment.

        Args:
            interior_width: Interior width of the cabinet box in inches.
            box_height: Height of the cabinet box in inches.
            depth: Depth of the window seat in inches.
            material: Material specification for drawer front.

        Returns:
            Tuple of (list of drawer front panels, list of hardware items).
        """
        # Single drawer for window seat storage
        drawer_height = box_height - 1.0  # Allow clearance

        panels = [
            Panel(
                panel_type=PanelType.DRAWER_FRONT,
                width=interior_width,
                height=drawer_height,
                material=material,
                position=Position(material.thickness, 0),
                metadata={"component": "windowseat.storage", "drawer_index": 0},
            ),
        ]

        # Determine slide length (typically depth - 2 inches for clearance)
        slide_length = int(depth - 2)
        # Standard slide lengths
        standard_lengths = [12, 14, 16, 18, 20, 22, 24]
        # Find the nearest standard slide length
        slide_length = min(standard_lengths, key=lambda x: abs(x - slide_length))

        hardware = [
            HardwareItem(
                name="Full Extension Drawer Slides",
                quantity=1,  # 1 pair
                sku=f"SLIDE-FE-{slide_length}",
                notes=f'{slide_length}" slides for window seat drawer',
            ),
        ]

        return panels, hardware


@component_registry.register("filler.mullion")
class MullionFillerComponent:
    """Filler panel component for narrow mullion zones.

    Used when a bay wall segment is below the minimum cabinet width
    threshold. Generates a decorative filler panel that matches
    the adjacent cabinet face.

    Configuration options:
        style: Filler panel style - "flat", "beveled", or "routed"

    Panel Generation:
        - Single mullion filler panel (PanelType.MULLION_FILLER)

    Hardware Generation:
        - None (filler panels are typically glued or nailed)
    """

    VALID_STYLES = ("flat", "beveled", "routed")

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate filler configuration.

        Checks:
        - Width is appropriate for a mullion filler
        - Width is not too narrow to be practical
        - Style is valid

        Args:
            config: Filler configuration dictionary with optional keys:
                - style: Panel style (default: "flat")

            context: Component context with section dimensions.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check width is appropriate for mullion filler
        if context.width > MAX_MULLION_WIDTH:
            warnings.append(
                f'Width {context.width}" is wide for a mullion filler '
                f'(typically < {MAX_MULLION_WIDTH}")'
            )
        if context.width < MIN_MULLION_WIDTH:
            errors.append(
                f'Width {context.width}" too narrow for filler panel '
                f'(min {MIN_MULLION_WIDTH}")'
            )

        # Validate style if specified
        style = config.get("style", "flat")
        if style not in self.VALID_STYLES:
            errors.append(
                f"Invalid filler style '{style}'. "
                f"Must be one of: {', '.join(self.VALID_STYLES)}"
            )

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate mullion filler panel.

        Creates a single filler panel sized to fill the narrow zone
        between bay wall segments.

        Args:
            config: Filler configuration dictionary with optional keys:
                - style: Panel style (default: "flat")

            context: Component context with section dimensions and position.

        Returns:
            GenerationResult containing the filler panel and metadata.
        """
        filler_style = config.get("style", "flat")

        panel = Panel(
            panel_type=PanelType.MULLION_FILLER,
            width=context.width,
            height=context.height,
            material=context.material,
            position=Position(0, 0),
            metadata={
                "component": "filler.mullion",
                "style": filler_style,
            },
        )

        return GenerationResult(
            panels=(panel,),
            hardware=(),
            metadata={"style": filler_style},
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Filler panels require no hardware.

        Mullion filler panels are typically attached using wood glue
        and/or finish nails, which are not tracked as discrete hardware.

        Args:
            config: Filler configuration dictionary.
            context: Component context with section dimensions.

        Returns:
            Empty list (no hardware required).
        """
        return []
