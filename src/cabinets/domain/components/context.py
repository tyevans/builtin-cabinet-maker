"""Component context for component generation."""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects import MaterialSpec, Position


@dataclass(frozen=True)
class ComponentContext:
    """Immutable context for component generation.

    Provides all the information a component needs to generate its panels,
    cut pieces, and hardware. The context includes both the component's own
    dimensions and position, as well as information about the cabinet it
    belongs to and adjacent components.

    Attributes:
        width: Width of the component in inches.
        height: Height of the component in inches.
        depth: Depth of the component in inches.
        material: Material specification for the component.
        position: Position of the component within the cabinet.
        section_index: Index of the section this component belongs to.
        cabinet_width: Overall cabinet width in inches.
        cabinet_height: Overall cabinet height in inches.
        cabinet_depth: Overall cabinet depth in inches.
        adjacent_left: Type identifier of component to the left, if any.
        adjacent_right: Type identifier of component to the right, if any.
        adjacent_above: Type identifier of component above, if any.
        adjacent_below: Type identifier of component below, if any.
        skip_top_divider: When True, the cabinet handles row-level horizontal
            dividers, so components (like drawers) should not generate their
            own top dividers. Used in row-based layouts.
    """

    width: float
    height: float
    depth: float
    material: MaterialSpec
    position: Position
    section_index: int
    cabinet_width: float
    cabinet_height: float
    cabinet_depth: float
    adjacent_left: str | None = None
    adjacent_right: str | None = None
    adjacent_above: str | None = None
    adjacent_below: str | None = None
    # When True, the cabinet handles row-level horizontal dividers,
    # so components should not generate their own top dividers
    skip_top_divider: bool = False
