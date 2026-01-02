"""Validator protocol for cabinet configuration validation.

This module defines the protocol that all validators must implement,
enabling consistent validation across different validation domains.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cabinets.application.config.schemas import CabinetConfiguration
    from cabinets.application.config.validators.base import ValidationResult


@runtime_checkable
class Validator(Protocol):
    """Protocol for cabinet configuration validators.

    Validators check specific aspects of a CabinetConfiguration and return
    a ValidationResult containing any errors or warnings found.

    Attributes:
        name: Unique identifier for the validator (e.g., "woodworking", "obstacle").

    Example:
        class MyValidator:
            @property
            def name(self) -> str:
                return "my_validator"

            def validate(self, config: CabinetConfiguration) -> ValidationResult:
                result = ValidationResult()
                # Check something...
                if problem_found:
                    result.add_error("path.to.field", "Description of problem")
                return result
    """

    @property
    def name(self) -> str:
        """Return the unique name/identifier for this validator."""
        ...

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        """Validate the given configuration.

        Args:
            config: A CabinetConfiguration instance to validate.

        Returns:
            ValidationResult containing any errors or warnings found.
        """
        ...
