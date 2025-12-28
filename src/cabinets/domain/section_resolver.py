"""Section width resolution for cabinet layouts.

This module provides functionality to resolve section widths when a mix of
fixed-width and "fill" sections are specified. It handles the calculation
of available interior space and distributes remaining width among fill sections.
"""

from dataclasses import dataclass
from typing import Literal


class SectionWidthError(Exception):
    """Raised when section widths cannot be resolved due to invalid specifications."""

    pass


@dataclass(frozen=True)
class SectionSpec:
    """Specification for a single cabinet section.

    Attributes:
        width: Either a fixed width in inches, or "fill" to auto-calculate.
               When "fill" is used, the section will receive an equal share
               of the remaining available width after fixed widths are accounted for.
        shelves: Number of shelves in this section (0 or more).
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
    """

    width: float | Literal["fill"]
    shelves: int = 0
    wall: str | int | None = None
    height_mode: Literal["full", "lower", "upper", "auto"] | None = None

    def __post_init__(self) -> None:
        """Validate section spec values."""
        if isinstance(self.width, (int, float)) and self.width <= 0:
            raise ValueError("Section width must be positive when specified as a number")
        if self.shelves < 0:
            raise ValueError("Number of shelves cannot be negative")

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
            f"Fixed section widths ({fixed_width_sum:.2f}\") exceed available "
            f"interior width ({available_width:.2f}\"). Reduce fixed widths or "
            f"increase cabinet width."
        )

    # Calculate width for fill sections
    remaining_width = available_width - fixed_width_sum

    if fill_count > 0:
        fill_section_width = remaining_width / fill_count

        if fill_section_width <= 0:
            raise SectionWidthError(
                f"Fill sections would have zero or negative width. "
                f"Remaining width ({remaining_width:.2f}\") with {fill_count} fill sections."
            )
    else:
        # No fill sections - validate that fixed widths exactly match
        # Allow small tolerance for floating point comparison
        if abs(fixed_width_sum - available_width) > 0.001:
            raise SectionWidthError(
                f"Fixed section widths ({fixed_width_sum:.2f}\") do not match "
                f"available interior width ({available_width:.2f}\"). "
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

    if errors:
        return errors

    # Try to resolve widths to validate the overall configuration
    try:
        resolve_section_widths(specs, total_width, material_thickness)
    except SectionWidthError as e:
        errors.append(str(e))

    return errors
