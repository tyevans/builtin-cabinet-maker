"""Result types for component validation and generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..entities import Panel
from ..value_objects import CutPiece


@dataclass(frozen=True)
class HardwareItem:
    """Hardware required by a component.

    Represents a piece of hardware (screws, hinges, brackets, etc.) that
    is needed for a component. Includes quantity and optional SKU for
    ordering purposes.

    Attributes:
        name: Human-readable name of the hardware item.
        quantity: Number of items required.
        sku: Optional manufacturer or vendor SKU.
        notes: Optional notes about installation or usage.
    """

    name: str
    quantity: int
    sku: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Result of component validation.

    Contains any errors or warnings found during validation. A component
    is considered valid if there are no errors, even if there are warnings.

    Attributes:
        errors: Tuple of error messages (validation failures).
        warnings: Tuple of warning messages (non-fatal issues).
    """

    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors).

        Returns:
            True if there are no errors, False otherwise.
        """
        return len(self.errors) == 0

    @classmethod
    def ok(cls, warnings: list[str] | None = None) -> ValidationResult:
        """Create a successful validation result.

        Args:
            warnings: Optional list of warning messages.

        Returns:
            A ValidationResult with no errors and the provided warnings.
        """
        return cls(warnings=tuple(warnings or []))

    @classmethod
    def fail(
        cls, errors: list[str], warnings: list[str] | None = None
    ) -> ValidationResult:
        """Create a failed validation result.

        Args:
            errors: List of error messages.
            warnings: Optional list of warning messages.

        Returns:
            A ValidationResult with the provided errors and warnings.
        """
        return cls(errors=tuple(errors), warnings=tuple(warnings or []))


@dataclass(frozen=True)
class GenerationResult:
    """Result of component generation.

    Contains all the outputs of generating a component: panels for 3D
    visualization, cut pieces for the cut list, and hardware items.

    The metadata field allows components to include additional structured
    data that may be consumed by downstream processors (e.g., machining
    specifications, drilling patterns).

    Attributes:
        panels: Tuple of Panel objects for the component.
        cut_pieces: Tuple of CutPiece objects for the cut list.
        hardware: Tuple of HardwareItem objects required.
        metadata: Additional structured data from component generation.
            Common keys include:
            - "dado_specs": list[DadoSpec] for fixed shelf dado joints
            - "pin_hole_patterns": list[PinHolePattern] for adjustable shelf drilling
    """

    panels: tuple[Panel, ...] = field(default_factory=tuple)
    cut_pieces: tuple[CutPiece, ...] = field(default_factory=tuple)
    hardware: tuple[HardwareItem, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_panels(cls, panels: list[Panel]) -> GenerationResult:
        """Create a GenerationResult from a list of panels.

        This is a convenience factory for components that only produce
        panels without explicit cut pieces or hardware.

        Args:
            panels: List of Panel objects.

        Returns:
            A GenerationResult containing the provided panels.
        """
        return cls(panels=tuple(panels))
