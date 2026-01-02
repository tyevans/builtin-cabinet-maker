"""Section width resolution for cabinet layouts.

This module provides functionality to resolve section widths when a mix of
fixed-width and "fill" sections are specified. It handles the calculation
of available interior space and distributes remaining width among fill sections.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from .value_objects import SectionType


@dataclass(frozen=True)
class SectionRowSpec:
    """Specification for a vertical row within a section.

    This is used when a section needs vertical stacking (rows) rather than
    a single uniform configuration. Each row represents a vertical zone
    within the section's boundaries.

    Attributes:
        height: Fixed height in inches, or "fill" to auto-calculate.
        section_type: Type for this row (open, doored, drawers, cubby).
        shelves: Number of shelves in this row (0 or more).
        component_config: Component-specific configuration dictionary.
        min_height: Minimum allowed height in inches. Defaults to 6.0.
        max_height: Maximum allowed height in inches. None means no limit.
    """

    height: float | Literal["fill"]
    section_type: SectionType = SectionType.OPEN
    shelves: int = 0
    component_config: dict[str, Any] = field(default_factory=dict)
    min_height: float = 6.0
    max_height: float | None = None

    def __post_init__(self) -> None:
        """Validate section row spec values."""
        if isinstance(self.height, (int, float)) and self.height <= 0:
            raise ValueError("Row height must be positive when specified as a number")
        if self.shelves < 0:
            raise ValueError("Number of shelves cannot be negative")
        if self.min_height <= 0:
            raise ValueError("min_height must be greater than 0")
        if self.max_height is not None and self.max_height < self.min_height:
            raise ValueError("max_height must be greater than or equal to min_height")
        if isinstance(self.height, (int, float)):
            if self.height < self.min_height:
                raise ValueError(
                    f'Row height {self.height}" is below min_height {self.min_height}"'
                )
            if self.max_height is not None and self.height > self.max_height:
                raise ValueError(
                    f'Row height {self.height}" exceeds max_height {self.max_height}"'
                )

    @property
    def is_fill(self) -> bool:
        """Check if this row uses fill height."""
        return self.height == "fill"

    @property
    def fixed_height(self) -> float | None:
        """Return the fixed height if specified, None if fill."""
        if isinstance(self.height, (int, float)):
            return float(self.height)
        return None


class SectionWidthError(Exception):
    """Raised when section widths cannot be resolved due to invalid specifications."""

    pass


@dataclass(frozen=True)
class SectionSpec:
    """Specification for a single cabinet section.

    A section can be configured in two ways:
    1. Flat configuration: Use shelves/section_type for uniform section
    2. Row-based configuration: Use row_specs for vertical stacking within the section

    Attributes:
        width: Either a fixed width in inches, or "fill" to auto-calculate.
               When "fill" is used, the section will receive an equal share
               of the remaining available width after fixed widths are accounted for.
        shelves: Number of shelves in this section (0 or more). Ignored if row_specs is set.
        wall: Optional wall assignment. Can be:
              - None: Defaults to wall index 0
              - int: Wall index (0-based)
              - str: Wall name to look up
        height_mode: Optional height mode for obstacle avoidance. Can be:
                     - None: Default behavior (full height)
                     - "full": Full wall height
                     - "lower": Only below obstacles (e.g., under windows)
                     - "upper": Only above obstacles (e.g., above counters)
                     - "auto": Automatically determine based on obstacles
        section_type: Type of cabinet section (open, doored, drawers, cubby).
                      Defaults to OPEN for backward compatibility. Ignored if row_specs is set.
        min_width: Minimum allowed width in inches. Defaults to 6.0.
        max_width: Maximum allowed width in inches. None means no limit.
        depth: Optional per-section depth override in inches. When None, inherits
               from cabinet depth. When specified, must be positive.
        component_config: Component-specific configuration dictionary. Passed
                         directly to the component's validate() and generate()
                         methods. Defaults to empty dict.
        row_specs: Optional tuple of SectionRowSpec for vertical stacking within
                  this section. When set, shelves and section_type are ignored.
    """

    width: float | Literal["fill"]
    shelves: int = 0
    wall: str | int | None = None
    height_mode: Literal["full", "lower", "upper", "auto"] | None = None
    section_type: SectionType = SectionType.OPEN
    min_width: float = 6.0
    max_width: float | None = None
    depth: float | None = None
    component_config: dict[str, Any] = field(default_factory=dict)
    row_specs: tuple[SectionRowSpec, ...] | None = None

    def __post_init__(self) -> None:
        """Validate section spec values."""
        if isinstance(self.width, (int, float)) and self.width <= 0:
            raise ValueError(
                "Section width must be positive when specified as a number"
            )
        if self.shelves < 0:
            raise ValueError("Number of shelves cannot be negative")
        if self.min_width <= 0:
            raise ValueError("min_width must be greater than 0")
        if self.max_width is not None and self.max_width < self.min_width:
            raise ValueError("max_width must be greater than or equal to min_width")
        if isinstance(self.width, (int, float)):
            if self.width < self.min_width:
                raise ValueError(
                    f'Section width {self.width}" is below min_width {self.min_width}"'
                )
            if self.max_width is not None and self.width > self.max_width:
                raise ValueError(
                    f'Section width {self.width}" exceeds max_width {self.max_width}"'
                )
        if self.depth is not None and self.depth <= 0:
            raise ValueError("Section depth must be positive when specified")

    @property
    def is_fill(self) -> bool:
        """Check if this section uses fill width."""
        return self.width == "fill"

    @property
    def fixed_width(self) -> float | None:
        """Return the fixed width if specified, None if fill."""
        if isinstance(self.width, (int, float)):
            return float(self.width)
        return None

    @property
    def has_rows(self) -> bool:
        """Check if this section uses row-based layout."""
        return self.row_specs is not None and len(self.row_specs) > 0


def resolve_section_widths(
    specs: list[SectionSpec],
    total_width: float,
    material_thickness: float,
) -> list[float]:
    """Resolve section widths from specifications.

    This function takes a list of section specifications (which may include
    both fixed widths and "fill" markers) and calculates the actual width
    for each section.

    Algorithm:
    1. Calculate available interior width (total_width - 2 * outer wall thickness)
    2. Subtract divider thickness between sections
    3. Sum all fixed widths
    4. Distribute remaining width equally among "fill" sections
    5. Validate that fixed widths don't exceed available width

    Args:
        specs: List of section specifications with widths and shelf counts.
        total_width: Total cabinet width in inches (outer dimension).
        material_thickness: Thickness of material in inches (used for walls and dividers).

    Returns:
        List of resolved section widths in the same order as the input specs.

    Raises:
        SectionWidthError: If fixed widths exceed available space, or if there
            are no sections specified, or if fill sections would result in
            zero or negative width.

    Example:
        >>> specs = [
        ...     SectionSpec(width=24.0, shelves=3),
        ...     SectionSpec(width="fill", shelves=4),
        ...     SectionSpec(width="fill", shelves=4),
        ... ]
        >>> # Cabinet is 72" wide with 0.75" material
        >>> # Interior = 72 - 2*0.75 = 70.5"
        >>> # After 2 dividers = 70.5 - 2*0.75 = 69"
        >>> # Fixed width = 24"
        >>> # Remaining = 69 - 24 = 45"
        >>> # Each fill = 45 / 2 = 22.5"
        >>> resolve_section_widths(specs, 72.0, 0.75)
        [24.0, 22.5, 22.5]
    """
    if not specs:
        raise SectionWidthError("At least one section specification is required")

    if total_width <= 0:
        raise SectionWidthError("Total width must be positive")

    if material_thickness <= 0:
        raise SectionWidthError("Material thickness must be positive")

    num_sections = len(specs)
    num_dividers = num_sections - 1

    # Calculate available interior width
    # Subtract outer walls (left and right) and dividers between sections
    outer_walls_thickness = 2 * material_thickness
    dividers_thickness = num_dividers * material_thickness
    available_width = total_width - outer_walls_thickness - dividers_thickness

    if available_width <= 0:
        raise SectionWidthError(
            f"No interior space available. Total width ({total_width}) must be greater "
            f"than outer walls ({outer_walls_thickness}) and dividers ({dividers_thickness})"
        )

    # Calculate fixed widths sum and count fill sections
    fixed_width_sum = 0.0
    fill_count = 0

    for spec in specs:
        if spec.is_fill:
            fill_count += 1
        else:
            fixed_width = spec.fixed_width
            assert fixed_width is not None  # Type narrowing
            fixed_width_sum += fixed_width

    # Validate fixed widths don't exceed available space
    if fixed_width_sum > available_width:
        raise SectionWidthError(
            f'Fixed section widths ({fixed_width_sum:.2f}") exceed available '
            f'interior width ({available_width:.2f}"). Reduce fixed widths or '
            f"increase cabinet width."
        )

    # Calculate width for fill sections
    remaining_width = available_width - fixed_width_sum

    if fill_count > 0:
        fill_section_width = remaining_width / fill_count

        if fill_section_width <= 0:
            raise SectionWidthError(
                f"Fill sections would have zero or negative width. "
                f'Remaining width ({remaining_width:.2f}") with {fill_count} fill sections.'
            )

        # Validate fill width against min/max constraints for each fill section
        for i, spec in enumerate(specs):
            if spec.is_fill:
                if fill_section_width < spec.min_width:
                    raise SectionWidthError(
                        f'Section {i}: calculated fill width {fill_section_width:.2f}" '
                        f'is below min_width {spec.min_width}"'
                    )
                if spec.max_width is not None and fill_section_width > spec.max_width:
                    raise SectionWidthError(
                        f'Section {i}: calculated fill width {fill_section_width:.2f}" '
                        f'exceeds max_width {spec.max_width}"'
                    )
    else:
        # No fill sections - validate that fixed widths exactly match
        # Allow small tolerance for floating point comparison
        if abs(fixed_width_sum - available_width) > 0.001:
            raise SectionWidthError(
                f'Fixed section widths ({fixed_width_sum:.2f}") do not match '
                f'available interior width ({available_width:.2f}"). '
                f"Use 'fill' for at least one section to automatically adjust."
            )
        fill_section_width = 0.0  # Not used, but defined for type consistency

    # Build the result list
    resolved_widths: list[float] = []
    for spec in specs:
        if spec.is_fill:
            resolved_widths.append(fill_section_width)
        else:
            fixed_width = spec.fixed_width
            assert fixed_width is not None
            resolved_widths.append(fixed_width)

    return resolved_widths


def validate_section_specs(
    specs: list[SectionSpec],
    total_width: float,
    material_thickness: float,
) -> list[str]:
    """Validate section specifications and return list of errors.

    This is a non-throwing version of the validation that can be used
    for collecting multiple errors before presenting them to the user.

    Args:
        specs: List of section specifications.
        total_width: Total cabinet width in inches.
        material_thickness: Material thickness in inches.

    Returns:
        List of error messages. Empty list if valid.
    """
    errors: list[str] = []

    if not specs:
        errors.append("At least one section specification is required")
        return errors

    if total_width <= 0:
        errors.append("Total width must be positive")

    if material_thickness <= 0:
        errors.append("Material thickness must be positive")

    if errors:
        return errors

    # Validate individual specs
    for i, spec in enumerate(specs):
        if spec.shelves < 0:
            errors.append(f"Section {i + 1}: Number of shelves cannot be negative")
        if not spec.is_fill and spec.fixed_width is not None and spec.fixed_width <= 0:
            errors.append(f"Section {i + 1}: Width must be positive")
        # Validate min_width/max_width constraints
        if spec.min_width <= 0:
            errors.append(f"Section {i + 1}: min_width must be greater than 0")
        if spec.max_width is not None and spec.max_width < spec.min_width:
            errors.append(
                f"Section {i + 1}: max_width must be greater than or equal to min_width"
            )
        if not spec.is_fill and spec.fixed_width is not None:
            if spec.fixed_width < spec.min_width:
                errors.append(
                    f'Section {i + 1}: width {spec.fixed_width}" is below min_width {spec.min_width}"'
                )
            if spec.max_width is not None and spec.fixed_width > spec.max_width:
                errors.append(
                    f'Section {i + 1}: width {spec.fixed_width}" exceeds max_width {spec.max_width}"'
                )

    if errors:
        return errors

    # Try to resolve widths to validate the overall configuration
    try:
        resolve_section_widths(specs, total_width, material_thickness)
    except SectionWidthError as e:
        errors.append(str(e))

    return errors


class RowHeightError(Exception):
    """Raised when row heights cannot be resolved due to invalid specifications."""

    pass


@dataclass(frozen=True)
class RowSpec:
    """Specification for a horizontal row (vertical zone) within a cabinet.

    Rows allow vertically stacking different section layouts. Each row has its
    own height and contains horizontally arranged sections.

    Attributes:
        height: Either a fixed height in inches, or "fill" to auto-calculate.
               When "fill" is used, the row will receive an equal share
               of the remaining available height after fixed heights are accounted for.
        section_specs: Tuple of section specifications within this row.
        min_height: Minimum allowed height in inches. Defaults to 6.0.
        max_height: Maximum allowed height in inches. None means no limit.
    """

    height: float | Literal["fill"]
    section_specs: tuple[SectionSpec, ...]
    min_height: float = 6.0
    max_height: float | None = None

    def __post_init__(self) -> None:
        """Validate row spec values."""
        if isinstance(self.height, (int, float)) and self.height <= 0:
            raise ValueError("Row height must be positive when specified as a number")
        if not self.section_specs:
            raise ValueError("Row must have at least one section specification")
        if self.min_height <= 0:
            raise ValueError("min_height must be greater than 0")
        if self.max_height is not None and self.max_height < self.min_height:
            raise ValueError("max_height must be greater than or equal to min_height")
        if isinstance(self.height, (int, float)):
            if self.height < self.min_height:
                raise ValueError(
                    f'Row height {self.height}" is below min_height {self.min_height}"'
                )
            if self.max_height is not None and self.height > self.max_height:
                raise ValueError(
                    f'Row height {self.height}" exceeds max_height {self.max_height}"'
                )

    @property
    def is_fill(self) -> bool:
        """Check if this row uses fill height."""
        return self.height == "fill"

    @property
    def fixed_height(self) -> float | None:
        """Return the fixed height if specified, None if fill."""
        if isinstance(self.height, (int, float)):
            return float(self.height)
        return None


def resolve_row_heights(
    row_specs: list[RowSpec],
    total_height: float,
    material_thickness: float,
    base_zone_height: float = 0.0,
) -> list[float]:
    """Resolve row heights from specifications.

    This function takes a list of row specifications (which may include
    both fixed heights and "fill" markers) and calculates the actual height
    for each row.

    Algorithm:
    1. Calculate available interior height (total_height - 2 * outer panel thickness - base_zone_height)
    2. Subtract horizontal divider thickness between rows
    3. Sum all fixed heights
    4. Distribute remaining height equally among "fill" rows
    5. Validate that fixed heights don't exceed available height

    Args:
        row_specs: List of row specifications with heights and section specs.
        total_height: Total cabinet height in inches (outer dimension).
        material_thickness: Thickness of material in inches (used for top/bottom
                           panels and horizontal dividers).
        base_zone_height: Height of the base zone (toe kick) in inches. This space
                         is reserved at the bottom and not available for rows.

    Returns:
        List of resolved row heights in the same order as the input specs.

    Raises:
        RowHeightError: If fixed heights exceed available space, or if there
            are no rows specified, or if fill rows would result in
            zero or negative height.

    Example:
        >>> row_specs = [
        ...     RowSpec(height=30.0, section_specs=(...)),
        ...     RowSpec(height="fill", section_specs=(...)),
        ...     RowSpec(height=12.0, section_specs=(...)),
        ... ]
        >>> # Cabinet is 95" tall with 0.75" material, 4" toe kick
        >>> # Interior = 95 - 2*0.75 - 4 = 89.5"
        >>> # After 2 horizontal dividers = 89.5 - 2*0.75 = 88"
        >>> # Fixed heights = 30 + 12 = 42"
        >>> # Remaining = 88 - 42 = 46"
        >>> # Fill row = 46"
        >>> resolve_row_heights(row_specs, 95.0, 0.75, base_zone_height=4.0)
        [30.0, 46.0, 12.0]
    """
    if not row_specs:
        raise RowHeightError("At least one row specification is required")

    if total_height <= 0:
        raise RowHeightError("Total height must be positive")

    if material_thickness <= 0:
        raise RowHeightError("Material thickness must be positive")

    num_rows = len(row_specs)
    num_horizontal_dividers = num_rows - 1

    # Calculate available interior height
    # Subtract top and bottom panels, horizontal dividers between rows, and base zone
    outer_panels_thickness = 2 * material_thickness
    dividers_thickness = num_horizontal_dividers * material_thickness
    available_height = (
        total_height - outer_panels_thickness - dividers_thickness - base_zone_height
    )

    if available_height <= 0:
        base_zone_msg = (
            f", base zone ({base_zone_height})" if base_zone_height > 0 else ""
        )
        raise RowHeightError(
            f"No interior space available. Total height ({total_height}) must be greater "
            f"than outer panels ({outer_panels_thickness}), dividers ({dividers_thickness}){base_zone_msg}"
        )

    # Calculate fixed heights sum and count fill rows
    fixed_height_sum = 0.0
    fill_count = 0

    for spec in row_specs:
        if spec.is_fill:
            fill_count += 1
        else:
            fixed_height = spec.fixed_height
            assert fixed_height is not None  # Type narrowing
            fixed_height_sum += fixed_height

    # Validate fixed heights don't exceed available space
    if fixed_height_sum > available_height:
        raise RowHeightError(
            f'Fixed row heights ({fixed_height_sum:.2f}") exceed available '
            f'interior height ({available_height:.2f}"). Reduce fixed heights or '
            f"increase cabinet height."
        )

    # Calculate height for fill rows
    remaining_height = available_height - fixed_height_sum

    if fill_count > 0:
        fill_row_height = remaining_height / fill_count

        if fill_row_height <= 0:
            raise RowHeightError(
                f"Fill rows would have zero or negative height. "
                f'Remaining height ({remaining_height:.2f}") with {fill_count} fill rows.'
            )

        # Validate fill height against min/max constraints for each fill row
        for i, spec in enumerate(row_specs):
            if spec.is_fill:
                if fill_row_height < spec.min_height:
                    raise RowHeightError(
                        f'Row {i}: calculated fill height {fill_row_height:.2f}" '
                        f'is below min_height {spec.min_height}"'
                    )
                if spec.max_height is not None and fill_row_height > spec.max_height:
                    raise RowHeightError(
                        f'Row {i}: calculated fill height {fill_row_height:.2f}" '
                        f'exceeds max_height {spec.max_height}"'
                    )
    else:
        # No fill rows - validate that fixed heights exactly match
        # Allow small tolerance for floating point comparison
        if abs(fixed_height_sum - available_height) > 0.001:
            raise RowHeightError(
                f'Fixed row heights ({fixed_height_sum:.2f}") do not match '
                f'available interior height ({available_height:.2f}"). '
                f"Use 'fill' for at least one row to automatically adjust."
            )
        fill_row_height = 0.0  # Not used, but defined for type consistency

    # Build the result list
    resolved_heights: list[float] = []
    for spec in row_specs:
        if spec.is_fill:
            resolved_heights.append(fill_row_height)
        else:
            fixed_height = spec.fixed_height
            assert fixed_height is not None
            resolved_heights.append(fixed_height)

    return resolved_heights


def resolve_section_row_heights(
    row_specs: list[SectionRowSpec],
    section_height: float,
    material_thickness: float,
) -> list[float]:
    """Resolve row heights within a section.

    This function is similar to resolve_row_heights but for rows within a section.
    The key difference is that it does NOT subtract top/bottom panels - those are
    part of the cabinet, not the section. It only accounts for horizontal dividers
    between rows within the section.

    Args:
        row_specs: List of SectionRowSpec specifications.
        section_height: Interior height of the section in inches (already excluding
                       cabinet top/bottom panels).
        material_thickness: Thickness of material in inches (for horizontal dividers).

    Returns:
        List of resolved row heights in the same order as the input specs.

    Raises:
        RowHeightError: If fixed heights exceed available space, or if there
            are no rows specified, or if fill rows would result in
            zero or negative height.

    Example:
        >>> row_specs = [
        ...     SectionRowSpec(height=42.0, section_type=SectionType.DRAWERS),
        ...     SectionRowSpec(height="fill", section_type=SectionType.OPEN, shelves=4),
        ... ]
        >>> # Section interior is 82" with 0.75" material
        >>> # After 1 horizontal divider = 82 - 0.75 = 81.25"
        >>> # Fixed heights = 42"
        >>> # Fill row = 81.25 - 42 = 39.25"
        >>> resolve_section_row_heights(row_specs, 82.0, 0.75)
        [42.0, 39.25]
    """
    if not row_specs:
        raise RowHeightError("At least one section row specification is required")

    if section_height <= 0:
        raise RowHeightError("Section height must be positive")

    if material_thickness <= 0:
        raise RowHeightError("Material thickness must be positive")

    num_rows = len(row_specs)
    num_horizontal_dividers = num_rows - 1

    # Calculate available height for rows
    # Only subtract horizontal dividers between rows (no top/bottom panels)
    dividers_thickness = num_horizontal_dividers * material_thickness
    available_height = section_height - dividers_thickness

    if available_height <= 0:
        raise RowHeightError(
            f"No interior space available. Section height ({section_height}) must be "
            f"greater than dividers ({dividers_thickness})"
        )

    # Calculate fixed heights sum and count fill rows
    fixed_height_sum = 0.0
    fill_count = 0

    for spec in row_specs:
        if spec.is_fill:
            fill_count += 1
        else:
            fixed_height = spec.fixed_height
            assert fixed_height is not None  # Type narrowing
            fixed_height_sum += fixed_height

    # Validate fixed heights don't exceed available space
    if fixed_height_sum > available_height:
        raise RowHeightError(
            f'Fixed row heights ({fixed_height_sum:.2f}") exceed available '
            f'height ({available_height:.2f}"). Reduce fixed heights or '
            f"increase section height."
        )

    # Calculate height for fill rows
    remaining_height = available_height - fixed_height_sum

    if fill_count > 0:
        fill_row_height = remaining_height / fill_count

        if fill_row_height <= 0:
            raise RowHeightError(
                f"Fill rows would have zero or negative height. "
                f'Remaining height ({remaining_height:.2f}") with {fill_count} fill rows.'
            )

        # Validate fill height against min/max constraints for each fill row
        for i, spec in enumerate(row_specs):
            if spec.is_fill:
                if fill_row_height < spec.min_height:
                    raise RowHeightError(
                        f'Section row {i}: calculated fill height {fill_row_height:.2f}" '
                        f'is below min_height {spec.min_height}"'
                    )
                if spec.max_height is not None and fill_row_height > spec.max_height:
                    raise RowHeightError(
                        f'Section row {i}: calculated fill height {fill_row_height:.2f}" '
                        f'exceeds max_height {spec.max_height}"'
                    )
    else:
        # No fill rows - validate that fixed heights exactly match
        if abs(fixed_height_sum - available_height) > 0.001:
            raise RowHeightError(
                f'Fixed row heights ({fixed_height_sum:.2f}") do not match '
                f'available height ({available_height:.2f}"). '
                f"Use 'fill' for at least one row to automatically adjust."
            )
        fill_row_height = 0.0  # Not used, but defined for type consistency

    # Build the result list
    resolved_heights: list[float] = []
    for spec in row_specs:
        if spec.is_fill:
            resolved_heights.append(fill_row_height)
        else:
            fixed_height = spec.fixed_height
            assert fixed_height is not None
            resolved_heights.append(fixed_height)

    return resolved_heights


def validate_row_specs(
    row_specs: list[RowSpec],
    total_height: float,
    material_thickness: float,
    base_zone_height: float = 0.0,
) -> list[str]:
    """Validate row specifications and return list of errors.

    This is a non-throwing version of the validation that can be used
    for collecting multiple errors before presenting them to the user.

    Args:
        row_specs: List of row specifications.
        total_height: Total cabinet height in inches.
        material_thickness: Material thickness in inches.
        base_zone_height: Height of the base zone (toe kick) in inches.

    Returns:
        List of error messages. Empty list if valid.
    """
    errors: list[str] = []

    if not row_specs:
        errors.append("At least one row specification is required")
        return errors

    if total_height <= 0:
        errors.append("Total height must be positive")

    if material_thickness <= 0:
        errors.append("Material thickness must be positive")

    if errors:
        return errors

    # Validate individual row specs
    for i, spec in enumerate(row_specs):
        if (
            not spec.is_fill
            and spec.fixed_height is not None
            and spec.fixed_height <= 0
        ):
            errors.append(f"Row {i + 1}: Height must be positive")
        if not spec.section_specs:
            errors.append(f"Row {i + 1}: Must have at least one section")
        # Validate min_height/max_height constraints
        if spec.min_height <= 0:
            errors.append(f"Row {i + 1}: min_height must be greater than 0")
        if spec.max_height is not None and spec.max_height < spec.min_height:
            errors.append(
                f"Row {i + 1}: max_height must be greater than or equal to min_height"
            )
        if not spec.is_fill and spec.fixed_height is not None:
            if spec.fixed_height < spec.min_height:
                errors.append(
                    f'Row {i + 1}: height {spec.fixed_height}" is below min_height {spec.min_height}"'
                )
            if spec.max_height is not None and spec.fixed_height > spec.max_height:
                errors.append(
                    f'Row {i + 1}: height {spec.fixed_height}" exceeds max_height {spec.max_height}"'
                )

    if errors:
        return errors

    # Try to resolve heights to validate the overall configuration
    try:
        resolve_row_heights(
            row_specs, total_height, material_thickness, base_zone_height
        )
    except RowHeightError as e:
        errors.append(str(e))

    return errors
