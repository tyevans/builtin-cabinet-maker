"""Validator registry for managing cabinet configuration validators.

This module provides a central registry for all available validators,
similar to the ExporterRegistry pattern used in infrastructure/exporters/base.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from .base import ValidationResult

if TYPE_CHECKING:
    from cabinets.application.config.schemas import CabinetConfiguration
    from cabinets.contracts.validators import Validator

logger = logging.getLogger(__name__)


class ValidatorRegistry:
    """Registry for validator classes.

    Provides a central registry for all available validators. Validators
    can be registered, enabled/disabled, and run against configurations.

    The registry supports:
    - Registering validator instances
    - Enabling/disabling specific validators
    - Running all enabled validators
    - Clearing for testing purposes

    Example:
        # Register a validator
        ValidatorRegistry.register(WoodworkingValidator())

        # Run all validators
        result = ValidatorRegistry.validate_all(config)

        # Disable a validator
        ValidatorRegistry.disable("woodworking")
    """

    _validators: ClassVar[dict[str, "Validator"]] = {}
    _disabled: ClassVar[set[str]] = set()

    @classmethod
    def register(cls, validator: "Validator") -> None:
        """Register a validator instance.

        Args:
            validator: The validator instance to register.

        Note:
            If a validator with the same name is already registered,
            it will be overwritten with a warning logged.
        """
        name = validator.name
        if name in cls._validators:
            logger.warning(f"Overwriting existing validator '{name}'")
        cls._validators[name] = validator
        logger.debug(f"Registered validator '{name}': {type(validator).__name__}")

    @classmethod
    def get(cls, name: str) -> "Validator":
        """Get a validator by name.

        Args:
            name: The validator name to look up.

        Returns:
            The validator instance.

        Raises:
            KeyError: If no validator is registered with that name.
        """
        if name not in cls._validators:
            available = ", ".join(sorted(cls._validators.keys()))
            raise KeyError(
                f"No validator registered with name '{name}'. "
                f"Available validators: {available or 'none'}"
            )
        return cls._validators[name]

    @classmethod
    def available(cls) -> list[str]:
        """Get list of all registered validator names.

        Returns:
            Sorted list of registered validator names.
        """
        return sorted(cls._validators.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a validator is registered.

        Args:
            name: The validator name to check.

        Returns:
            True if registered, False otherwise.
        """
        return name in cls._validators

    @classmethod
    def enable(cls, name: str) -> None:
        """Enable a validator by name.

        Args:
            name: The validator name to enable.

        Raises:
            KeyError: If no validator is registered with that name.
        """
        if name not in cls._validators:
            raise KeyError(f"No validator registered with name '{name}'")
        cls._disabled.discard(name)
        logger.debug(f"Enabled validator '{name}'")

    @classmethod
    def disable(cls, name: str) -> None:
        """Disable a validator by name.

        Disabled validators will be skipped during validate_all().

        Args:
            name: The validator name to disable.

        Raises:
            KeyError: If no validator is registered with that name.
        """
        if name not in cls._validators:
            raise KeyError(f"No validator registered with name '{name}'")
        cls._disabled.add(name)
        logger.debug(f"Disabled validator '{name}'")

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """Check if a validator is enabled.

        Args:
            name: The validator name to check.

        Returns:
            True if the validator is registered and enabled, False otherwise.
        """
        return name in cls._validators and name not in cls._disabled

    @classmethod
    def validate_all(cls, config: "CabinetConfiguration") -> ValidationResult:
        """Run all enabled validators against a configuration.

        Args:
            config: The cabinet configuration to validate.

        Returns:
            ValidationResult containing merged errors and warnings from all validators.
        """
        result = ValidationResult()

        for name in sorted(cls._validators.keys()):
            if name in cls._disabled:
                logger.debug(f"Skipping disabled validator '{name}'")
                continue

            validator = cls._validators[name]
            logger.debug(f"Running validator '{name}'")
            try:
                validator_result = validator.validate(config)
                result.merge(validator_result)
            except Exception as e:
                logger.error(f"Validator '{name}' raised an exception: {e}")
                result.add_error(
                    path="validation",
                    message=f"Validator '{name}' failed: {str(e)}",
                )

        return result

    @classmethod
    def validate_single(
        cls, name: str, config: "CabinetConfiguration"
    ) -> ValidationResult:
        """Run a single validator against a configuration.

        Args:
            name: The validator name to run.
            config: The cabinet configuration to validate.

        Returns:
            ValidationResult from the specified validator.

        Raises:
            KeyError: If no validator is registered with that name.
        """
        validator = cls.get(name)
        return validator.validate(config)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered validators and disabled states.

        This is primarily useful for testing.
        """
        cls._validators.clear()
        cls._disabled.clear()

    @classmethod
    def reset_disabled(cls) -> None:
        """Reset all validators to enabled state.

        This is useful for testing or when you want to re-enable all validators.
        """
        cls._disabled.clear()
