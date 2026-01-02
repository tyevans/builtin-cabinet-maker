"""Base module for layout strategies.

Re-exports the LayoutStrategy protocol and provides common type aliases
for strategy implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Re-export the protocol for convenience
from cabinets.contracts.strategies import LayoutStrategy

if TYPE_CHECKING:
    from cabinets.domain.components.results import HardwareItem
    from cabinets.domain.entities import Cabinet

# Type alias for strategy return type
LayoutResult = tuple["Cabinet", list["HardwareItem"]]

__all__ = [
    "LayoutResult",
    "LayoutStrategy",
]
