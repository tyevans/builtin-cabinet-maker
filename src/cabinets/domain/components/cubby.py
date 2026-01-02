"""Cubby grid component implementation.

Provides components for creating grid-based storage subdivisions (cubbies)
within cabinet sections. Cubbies are formed by intersecting horizontal
and vertical dividers using half-lap notch joints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..entities import Panel
from ..value_objects import PanelType, Position
from .context import ComponentContext
from .registry import component_registry
from .results import GenerationResult, HardwareItem, ValidationResult

# Minimum cubby size in inches
MIN_CUBBY_SIZE = 6.0

# Maximum rows/columns allowed
MAX_GRID_SIZE = 10


@dataclass(frozen=True)
class NotchSpec:
    """Half-lap notch specification for divider intersection.

    Represents a notch cut on a divider panel where it intersects
    with another divider. Half-lap joints allow dividers to interlock
    at their intersections, creating a rigid grid structure.

    Attributes:
        position: Distance from left edge (for top/bottom notches) or
            bottom edge (for left/right notches) to notch center (inches).
        width: Notch width, equal to intersecting divider thickness (inches).
        depth: Notch depth, equal to half the divider thickness (inches).
        edge: Which edge the notch is on - "top", "bottom", "left", or "right".
    """

    position: float  # Distance from left/bottom edge
    width: float  # Notch width (= divider thickness)
    depth: float  # Notch depth (= divider thickness / 2)
    edge: str  # "top" | "bottom" | "left" | "right"

    def __post_init__(self) -> None:
        """Validate notch specification."""
        if self.position < 0:
            raise ValueError("Notch position must be non-negative")
        if self.width <= 0:
            raise ValueError("Notch width must be positive")
        if self.depth <= 0:
            raise ValueError("Notch depth must be positive")
        valid_edges = {"top", "bottom", "left", "right"}
        if self.edge not in valid_edges:
            raise ValueError(f"Edge must be one of {valid_edges}, got '{self.edge}'")


def _calculate_uniform_sizes(
    total_dimension: float,
    count: int,
    divider_thickness: float,
) -> list[float]:
    """Calculate uniform cubby sizes for a dimension.

    Args:
        total_dimension: Total width or height available (inches).
        count: Number of cubbies in this dimension.
        divider_thickness: Thickness of divider material (inches).

    Returns:
        List of cubby sizes (all equal for uniform grid).
    """
    if count <= 0:
        return []

    # Available space minus dividers
    num_dividers = count - 1
    available = total_dimension - (num_dividers * divider_thickness)
    cubby_size = available / count

    return [cubby_size] * count


def _generate_dividers(
    context: ComponentContext,
    rows: int,
    columns: int,
    column_widths: list[float],
    row_heights: list[float],
) -> tuple[list[Panel], dict[str, list[NotchSpec]]]:
    """Generate divider panels with notch specifications.

    Creates horizontal dividers (between rows) and vertical dividers
    (between columns within each row). Calculates half-lap notch
    positions for divider intersections.

    Notch placement rules:
    - Horizontal dividers: notches on TOP edge at vertical divider positions
    - Vertical dividers in bottom row: notches on TOP edge only
    - Vertical dividers in middle rows: notches on BOTH top and bottom
    - Vertical dividers in top row: notches on BOTTOM edge only

    Args:
        context: Component context with dimensions and material.
        rows: Number of rows in the grid.
        columns: Number of columns in the grid.
        column_widths: List of column widths (inches).
        row_heights: List of row heights (inches).

    Returns:
        Tuple of (panels, notch_specs) where notch_specs is a dict
        keyed by divider label containing lists of NotchSpec objects.
    """
    panels: list[Panel] = []
    notch_specs: dict[str, list[NotchSpec]] = {}
    thickness = context.material.thickness
    half_thickness = thickness / 2

    # Calculate vertical divider positions (cumulative column widths)
    vertical_positions: list[float] = []
    cumulative_x = 0.0
    for i, width in enumerate(column_widths[:-1]):  # Skip last column
        cumulative_x += width
        vertical_positions.append(cumulative_x)
        cumulative_x += thickness  # Account for divider

    # Calculate horizontal divider positions (cumulative row heights from bottom)
    horizontal_positions: list[float] = []
    cumulative_y = 0.0
    for i, height in enumerate(row_heights[:-1]):  # Skip last row
        cumulative_y += height
        horizontal_positions.append(cumulative_y)
        cumulative_y += thickness  # Account for divider

    # Generate horizontal dividers (rows - 1 count)
    # Horizontal dividers span full section width
    for h_idx, y_pos in enumerate(horizontal_positions):
        label = f"horizontal_divider_{h_idx + 1}"
        panel = Panel(
            panel_type=PanelType.SHELF,  # Use SHELF for horizontal dividers
            width=context.width,
            height=context.depth,  # Depth becomes panel height for horizontal
            material=context.material,
            position=Position(
                x=context.position.x,
                y=context.position.y + y_pos,
            ),
        )
        panels.append(panel)

        # Calculate notches on TOP edge at vertical divider positions
        notches: list[NotchSpec] = []
        for v_pos in vertical_positions:
            notches.append(
                NotchSpec(
                    position=v_pos + half_thickness,  # Center of notch
                    width=thickness,
                    depth=half_thickness,
                    edge="top",
                )
            )
        notch_specs[label] = notches

    # Generate vertical dividers (columns - 1 per row, for each row)
    # Vertical dividers fit between horizontal dividers
    cumulative_row_y = 0.0
    for row_idx in range(rows):
        row_height = row_heights[row_idx]

        for v_idx, x_pos in enumerate(vertical_positions):
            # Unique label for each vertical divider
            label = f"vertical_divider_r{row_idx + 1}_c{v_idx + 1}"

            panel = Panel(
                panel_type=PanelType.DIVIDER,  # Use DIVIDER for vertical
                width=context.depth,  # Depth becomes panel width for vertical
                height=row_height,  # Height of this row's cubby space
                material=context.material,
                position=Position(
                    x=context.position.x + x_pos,
                    y=context.position.y + cumulative_row_y,
                ),
            )
            panels.append(panel)

            # Calculate notches based on row position
            notches = []

            if rows == 1:
                # Single row: no horizontal dividers, no notches needed
                pass
            elif row_idx == 0:
                # Bottom row: notch on TOP edge only
                notches.append(
                    NotchSpec(
                        position=row_height,  # At top of divider
                        width=thickness,
                        depth=half_thickness,
                        edge="top",
                    )
                )
            elif row_idx == rows - 1:
                # Top row: notch on BOTTOM edge only
                notches.append(
                    NotchSpec(
                        position=0.0,  # At bottom of divider
                        width=thickness,
                        depth=half_thickness,
                        edge="bottom",
                    )
                )
            else:
                # Middle row: notches on BOTH edges
                notches.append(
                    NotchSpec(
                        position=0.0,  # At bottom of divider
                        width=thickness,
                        depth=half_thickness,
                        edge="bottom",
                    )
                )
                notches.append(
                    NotchSpec(
                        position=row_height,  # At top of divider
                        width=thickness,
                        depth=half_thickness,
                        edge="top",
                    )
                )

            notch_specs[label] = notches

        # Move to next row (add row height + divider thickness if not last row)
        cumulative_row_y += row_height
        if row_idx < rows - 1:
            cumulative_row_y += thickness

    return panels, notch_specs


@component_registry.register("cubby.uniform")
class UniformCubbyComponent:
    """Uniform cubby grid component - equal-sized grid subdivisions.

    Creates a grid of equal-sized cubbies within a cabinet section.
    The grid is defined by the number of rows and columns, with each
    cubby having identical dimensions.

    Configuration:
        rows: Number of rows in the grid (1-10).
        columns: Number of columns in the grid (1-10).

    The component generates:
    - Horizontal dividers between rows (using PanelType.SHELF)
    - Vertical dividers between columns within each row (using PanelType.DIVIDER)
    - NotchSpec metadata for half-lap joint locations

    Example:
        config = {"rows": 3, "columns": 4}
        result = component.generate(config, context)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate uniform cubby configuration.

        Checks that:
        - rows is an integer between 1 and 10 (inclusive)
        - columns is an integer between 1 and 10 (inclusive)
        - Resulting cubby width is at least MIN_CUBBY_SIZE (6 inches)
        - Resulting cubby height is at least MIN_CUBBY_SIZE (6 inches)

        Args:
            config: Configuration with 'rows' and 'columns' keys.
            context: Component context with dimensions and material.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        rows = config.get("rows", 1)
        columns = config.get("columns", 1)

        # Validate rows
        if not isinstance(rows, int) or rows < 1:
            errors.append("rows must be a positive integer")
        elif rows > MAX_GRID_SIZE:
            errors.append(f"rows exceeds maximum of {MAX_GRID_SIZE}")

        # Validate columns
        if not isinstance(columns, int) or columns < 1:
            errors.append("columns must be a positive integer")
        elif columns > MAX_GRID_SIZE:
            errors.append(f"columns exceeds maximum of {MAX_GRID_SIZE}")

        # If basic validation passed, check cubby sizes
        if not errors:
            thickness = context.material.thickness

            # Calculate cubby width
            num_vertical_dividers = columns - 1
            available_width = context.width - (num_vertical_dividers * thickness)
            cubby_width = available_width / columns

            if cubby_width < MIN_CUBBY_SIZE:
                errors.append(
                    f'Cubby width {cubby_width:.2f}" is less than '
                    f'minimum {MIN_CUBBY_SIZE}"'
                )

            # Calculate cubby height
            num_horizontal_dividers = rows - 1
            available_height = context.height - (num_horizontal_dividers * thickness)
            cubby_height = available_height / rows

            if cubby_height < MIN_CUBBY_SIZE:
                errors.append(
                    f'Cubby height {cubby_height:.2f}" is less than '
                    f'minimum {MIN_CUBBY_SIZE}"'
                )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate uniform cubby grid panels with notch specifications.

        Creates horizontal and vertical dividers to form a uniform grid.
        Each divider is labeled and includes notch specifications for
        half-lap joints where dividers intersect.

        Args:
            config: Configuration with 'rows' and 'columns' keys.
            context: Component context with dimensions, material, and position.

        Returns:
            GenerationResult containing divider panels, hardware (edge banding),
            and metadata with notch specifications.
        """
        rows = config.get("rows", 1)
        columns = config.get("columns", 1)

        if rows < 1 or columns < 1:
            return GenerationResult()

        thickness = context.material.thickness

        # Calculate uniform sizes
        column_widths = _calculate_uniform_sizes(context.width, columns, thickness)
        row_heights = _calculate_uniform_sizes(context.height, rows, thickness)

        # Generate dividers with notch specs
        panels, notch_specs = _generate_dividers(
            context, rows, columns, column_widths, row_heights
        )

        # Calculate edge banding (front edges of all dividers)
        # Horizontal dividers: context.width each
        # Vertical dividers: row_heights for each column in each row
        num_horizontal = rows - 1

        horizontal_banding = context.width * num_horizontal
        vertical_banding = sum(row_heights) * (columns - 1)
        total_banding = horizontal_banding + vertical_banding

        hardware: list[HardwareItem] = []
        if total_banding > 0 and config.get("edge_band_front", True):
            hardware.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{total_banding:.1f} linear inches for divider fronts",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={"notch_specs": notch_specs},
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for uniform cubby grid.

        Cubby grids require:
        - Edge banding for front edges of all dividers (if enabled)

        Args:
            config: Configuration with 'rows' and 'columns' keys.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for edge banding.
        """
        rows = config.get("rows", 1)
        columns = config.get("columns", 1)

        if rows < 1 or columns < 1:
            return []

        if not config.get("edge_band_front", True):
            return []

        thickness = context.material.thickness

        # Calculate row heights for vertical banding
        row_heights = _calculate_uniform_sizes(context.height, rows, thickness)

        num_horizontal = rows - 1
        horizontal_banding = context.width * num_horizontal
        vertical_banding = sum(row_heights) * (columns - 1)
        total_banding = horizontal_banding + vertical_banding

        if total_banding <= 0:
            return []

        return [
            HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{total_banding:.1f} linear inches for divider fronts",
            )
        ]


@component_registry.register("cubby.variable")
class VariableCubbyComponent:
    """Variable cubby grid component - custom-sized grid subdivisions.

    Creates a grid of cubbies with variable row heights and/or column
    widths. Supports three modes:
    1. Both row_heights and column_widths specified
    2. Only row_heights specified (uniform columns)
    3. Only column_widths specified (uniform rows)

    Configuration:
        row_heights: list[float] - Explicit heights for each row (inches).
        column_widths: list[float] - Explicit widths for each column (inches).
        rows: int - Number of rows (used when row_heights not specified).
        columns: int - Number of columns (used when column_widths not specified).

    The total of row_heights + dividers must equal section height.
    The total of column_widths + dividers must equal section width.

    Example:
        config = {
            "row_heights": [12.0, 8.0, 12.0],  # 3 rows with variable heights
            "column_widths": [6.0, 10.0, 6.0],  # 3 columns with variable widths
        }
        result = component.generate(config, context)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate variable cubby configuration.

        Checks that:
        - row_heights and/or column_widths are provided, or rows/columns counts
        - All heights/widths are positive
        - Individual cubby dimensions are at least MIN_CUBBY_SIZE
        - Total dimensions + dividers equal section dimensions (within tolerance)
        - Grid size does not exceed MAX_GRID_SIZE (10)

        Args:
            config: Configuration with dimension lists or counts.
            context: Component context with dimensions and material.

        Returns:
            ValidationResult with any errors or warnings found.
        """
        errors: list[str] = []
        warnings: list[str] = []

        thickness = context.material.thickness
        tolerance = 0.001  # Floating point tolerance

        # Resolve row configuration
        row_heights = config.get("row_heights")
        rows = config.get("rows", 1)

        if row_heights is not None:
            if not isinstance(row_heights, list) or len(row_heights) == 0:
                errors.append("row_heights must be a non-empty list")
            elif len(row_heights) > MAX_GRID_SIZE:
                errors.append(f"Number of rows exceeds maximum of {MAX_GRID_SIZE}")
            else:
                # Validate individual heights
                for i, h in enumerate(row_heights):
                    if not isinstance(h, (int, float)) or h <= 0:
                        errors.append(f"Row {i + 1} height must be positive")
                    elif h < MIN_CUBBY_SIZE:
                        errors.append(
                            f'Row {i + 1} height {h:.2f}" is less than '
                            f'minimum {MIN_CUBBY_SIZE}"'
                        )

                # Validate total height
                if not any("height must be positive" in e for e in errors):
                    num_dividers = len(row_heights) - 1
                    total = sum(row_heights) + (num_dividers * thickness)
                    if abs(total - context.height) > tolerance:
                        errors.append(
                            f'Row heights ({sum(row_heights):.2f}") + dividers '
                            f'({num_dividers * thickness:.2f}") = {total:.2f}" '
                            f'does not equal section height ({context.height:.2f}")'
                        )
        else:
            # Using rows count
            if not isinstance(rows, int) or rows < 1:
                errors.append("rows must be a positive integer")
            elif rows > MAX_GRID_SIZE:
                errors.append(f"rows exceeds maximum of {MAX_GRID_SIZE}")
            else:
                # Check calculated row height
                num_dividers = rows - 1
                available = context.height - (num_dividers * thickness)
                row_height = available / rows
                if row_height < MIN_CUBBY_SIZE:
                    errors.append(
                        f'Calculated row height {row_height:.2f}" is less than '
                        f'minimum {MIN_CUBBY_SIZE}"'
                    )

        # Resolve column configuration
        column_widths = config.get("column_widths")
        columns = config.get("columns", 1)

        if column_widths is not None:
            if not isinstance(column_widths, list) or len(column_widths) == 0:
                errors.append("column_widths must be a non-empty list")
            elif len(column_widths) > MAX_GRID_SIZE:
                errors.append(f"Number of columns exceeds maximum of {MAX_GRID_SIZE}")
            else:
                # Validate individual widths
                for i, w in enumerate(column_widths):
                    if not isinstance(w, (int, float)) or w <= 0:
                        errors.append(f"Column {i + 1} width must be positive")
                    elif w < MIN_CUBBY_SIZE:
                        errors.append(
                            f'Column {i + 1} width {w:.2f}" is less than '
                            f'minimum {MIN_CUBBY_SIZE}"'
                        )

                # Validate total width
                if not any("width must be positive" in e for e in errors):
                    num_dividers = len(column_widths) - 1
                    total = sum(column_widths) + (num_dividers * thickness)
                    if abs(total - context.width) > tolerance:
                        errors.append(
                            f'Column widths ({sum(column_widths):.2f}") + dividers '
                            f'({num_dividers * thickness:.2f}") = {total:.2f}" '
                            f'does not equal section width ({context.width:.2f}")'
                        )
        else:
            # Using columns count
            if not isinstance(columns, int) or columns < 1:
                errors.append("columns must be a positive integer")
            elif columns > MAX_GRID_SIZE:
                errors.append(f"columns exceeds maximum of {MAX_GRID_SIZE}")
            else:
                # Check calculated column width
                num_dividers = columns - 1
                available = context.width - (num_dividers * thickness)
                col_width = available / columns
                if col_width < MIN_CUBBY_SIZE:
                    errors.append(
                        f'Calculated column width {col_width:.2f}" is less than '
                        f'minimum {MIN_CUBBY_SIZE}"'
                    )

        return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Generate variable cubby grid panels with notch specifications.

        Creates horizontal and vertical dividers based on specified
        row_heights and column_widths (or calculated from rows/columns counts).

        Args:
            config: Configuration with dimension lists or counts.
            context: Component context with dimensions, material, and position.

        Returns:
            GenerationResult containing divider panels, hardware,
            and metadata with notch specifications.
        """
        thickness = context.material.thickness

        # Resolve row heights
        row_heights = config.get("row_heights")
        if row_heights is None:
            rows = config.get("rows", 1)
            if rows < 1:
                return GenerationResult()
            row_heights = _calculate_uniform_sizes(context.height, rows, thickness)
        rows = len(row_heights)

        # Resolve column widths
        column_widths = config.get("column_widths")
        if column_widths is None:
            columns = config.get("columns", 1)
            if columns < 1:
                return GenerationResult()
            column_widths = _calculate_uniform_sizes(context.width, columns, thickness)
        columns = len(column_widths)

        if rows < 1 or columns < 1:
            return GenerationResult()

        # Generate dividers with notch specs
        panels, notch_specs = _generate_dividers(
            context, rows, columns, column_widths, row_heights
        )

        # Calculate edge banding
        num_horizontal = rows - 1
        num_vertical_per_row = columns - 1

        horizontal_banding = context.width * num_horizontal
        vertical_banding = sum(row_heights) * num_vertical_per_row
        total_banding = horizontal_banding + vertical_banding

        hardware: list[HardwareItem] = []
        if total_banding > 0 and config.get("edge_band_front", True):
            hardware.append(
                HardwareItem(
                    name="Edge Banding",
                    quantity=1,
                    notes=f"{total_banding:.1f} linear inches for divider fronts",
                )
            )

        return GenerationResult(
            panels=tuple(panels),
            hardware=tuple(hardware),
            metadata={"notch_specs": notch_specs},
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Return hardware requirements for variable cubby grid.

        Args:
            config: Configuration with dimension lists or counts.
            context: Component context with dimensions.

        Returns:
            List of HardwareItem objects for edge banding.
        """
        thickness = context.material.thickness

        # Resolve row heights
        row_heights = config.get("row_heights")
        if row_heights is None:
            rows = config.get("rows", 1)
            if rows < 1:
                return []
            row_heights = _calculate_uniform_sizes(context.height, rows, thickness)
        rows = len(row_heights)

        # Resolve column widths
        column_widths = config.get("column_widths")
        if column_widths is None:
            columns = config.get("columns", 1)
            if columns < 1:
                return []
            column_widths = _calculate_uniform_sizes(context.width, columns, thickness)
        columns = len(column_widths)

        if rows < 1 or columns < 1:
            return []

        if not config.get("edge_band_front", True):
            return []

        num_horizontal = rows - 1
        num_vertical_per_row = columns - 1

        horizontal_banding = context.width * num_horizontal
        vertical_banding = sum(row_heights) * num_vertical_per_row
        total_banding = horizontal_banding + vertical_banding

        if total_banding <= 0:
            return []

        return [
            HardwareItem(
                name="Edge Banding",
                quantity=1,
                notes=f"{total_banding:.1f} linear inches for divider fronts",
            )
        ]
