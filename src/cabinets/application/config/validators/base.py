"""Base validation structures for cabinet configuration validation.

This module provides the core validation result classes used across all
validators in the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationError:
    """Represents a blocking validation error.

    Validation errors indicate configuration issues that must be fixed
    before the cabinet can be generated.

    Attributes:
        path: JSON path to the invalid field (e.g., "cabinet.sections[0].width")
        message: Human-readable description of the error
        value: The invalid value that caused the error
    """

    path: str
    message: str
    value: Any = None


@dataclass
class ValidationWarning:
    """Represents a non-blocking validation warning.

    Validation warnings indicate potential issues or deviations from
    woodworking best practices. The configuration can still be used,
    but the user should be aware of these concerns.

    Attributes:
        path: JSON path to the concerning field
        message: Human-readable description of the concern
        suggestion: Optional suggested remediation
    """

    path: str
    message: str
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Container for validation errors and warnings.

    This class collects all validation issues found during configuration
    validation and provides methods to check the overall validation status.

    Attributes:
        errors: List of blocking validation errors
        warnings: List of non-blocking validation warnings
    """

    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the configuration has no blocking errors."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Check if the configuration has any warnings."""
        return len(self.warnings) > 0

    @property
    def exit_code(self) -> int:
        """Get the CLI exit code based on validation status.

        Returns:
            0 if valid with no warnings
            1 if there are errors
            2 if valid but has warnings
        """
        if self.errors:
            return 1
        if self.warnings:
            return 2
        return 0

    def add_error(
        self, path: str, message: str, value: Any = None
    ) -> "ValidationResult":
        """Add a validation error and return self for chaining."""
        self.errors.append(ValidationError(path=path, message=message, value=value))
        return self

    def add_warning(
        self, path: str, message: str, suggestion: str | None = None
    ) -> "ValidationResult":
        """Add a validation warning and return self for chaining."""
        self.warnings.append(
            ValidationWarning(path=path, message=message, suggestion=suggestion)
        )
        return self

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Merge another ValidationResult into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self
