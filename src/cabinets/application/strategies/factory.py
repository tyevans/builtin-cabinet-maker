"""Factory for creating layout strategies.

The LayoutStrategyFactory encapsulates the strategy selection logic,
keeping the if/elif chain in one place and allowing the command layer
to remain open for extension without modification (OCP).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .row_spec import RowSpecLayoutStrategy
from .section_spec import SectionSpecLayoutStrategy
from .uniform import UniformLayoutStrategy

if TYPE_CHECKING:
    from cabinets.contracts.strategies import LayoutStrategy
    from cabinets.domain.section_resolver import RowSpec, SectionSpec

# Type alias for the calculator - we need the concrete type since strategies
# use methods not on the protocol (generate_cabinet_from_specs, etc.)
# Using Any at runtime avoids circular import issues
from typing import Any

LayoutCalculatorType = Any  # Actually LayoutCalculator at runtime


class LayoutStrategyFactory:
    """Factory for creating layout strategy instances.

    This factory determines which layout strategy to use based on the
    provided specifications (section_specs, row_specs, or neither).

    The factory centralizes the strategy selection logic, which was
    previously an OCP violation in GenerateLayoutCommand. By moving
    this logic here, we can add new strategies without modifying the
    command layer.

    Example:
        ```python
        factory = LayoutStrategyFactory(layout_calculator)
        strategy = factory.create_strategy(section_specs=my_specs)
        cabinet, hardware = strategy.execute(wall, params)
        ```
    """

    def __init__(self, layout_calculator: LayoutCalculatorType) -> None:
        """Initialize with a layout calculator.

        Args:
            layout_calculator: Service for generating cabinet layouts.
                All strategy instances will use this calculator.
        """
        self._layout_calculator = layout_calculator

    def create_strategy(
        self,
        section_specs: list["SectionSpec"] | None = None,
        row_specs: list["RowSpec"] | None = None,
    ) -> "LayoutStrategy":
        """Create the appropriate layout strategy based on specifications.

        Strategy selection logic:
        1. If both section_specs and row_specs are provided, raise ValueError
        2. If row_specs is provided, use RowSpecLayoutStrategy
        3. If section_specs is provided, use SectionSpecLayoutStrategy
        4. Otherwise, use UniformLayoutStrategy

        Args:
            section_specs: Optional list of section specifications.
            row_specs: Optional list of row specifications.

        Returns:
            A LayoutStrategy instance appropriate for the given specifications.

        Raises:
            ValueError: If both section_specs and row_specs are provided.
        """
        if section_specs is not None and row_specs is not None:
            raise ValueError(
                "Cannot specify both section_specs and row_specs. "
                "Use section_specs for single-row layout or row_specs for multi-row layout."
            )

        if row_specs is not None:
            return RowSpecLayoutStrategy(
                layout_calculator=self._layout_calculator,
                row_specs=row_specs,
            )

        if section_specs is not None:
            return SectionSpecLayoutStrategy(
                layout_calculator=self._layout_calculator,
                section_specs=section_specs,
            )

        return UniformLayoutStrategy(
            layout_calculator=self._layout_calculator,
        )


__all__ = [
    "LayoutStrategyFactory",
]
