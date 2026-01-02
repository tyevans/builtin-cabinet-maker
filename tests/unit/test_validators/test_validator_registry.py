"""Unit tests for ValidatorRegistry."""

from __future__ import annotations

import pytest

from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    MaterialConfig,
    SectionConfig,
)
from cabinets.domain.value_objects import MaterialType
from cabinets.application.config.validators.base import ValidationResult
from cabinets.application.config.validators.registry import ValidatorRegistry


class MockValidator:
    """Mock validator for testing."""

    def __init__(self, name: str, add_error: bool = False, add_warning: bool = False):
        self._name = name
        self._add_error = add_error
        self._add_warning = add_warning

    @property
    def name(self) -> str:
        return self._name

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        result = ValidationResult()
        if self._add_error:
            result.add_error(f"test.{self._name}", f"Error from {self._name}")
        if self._add_warning:
            result.add_warning(f"test.{self._name}", f"Warning from {self._name}")
        return result


class RaisingValidator:
    """Validator that raises an exception."""

    @property
    def name(self) -> str:
        return "raising"

    def validate(self, config: CabinetConfiguration) -> ValidationResult:
        raise ValueError("Test exception")


@pytest.fixture
def basic_config() -> CabinetConfiguration:
    """Create a basic cabinet configuration for testing."""
    return CabinetConfiguration(
        schema_version="1.6",
        cabinet=CabinetConfig(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialConfig(
                type=MaterialType.PLYWOOD,
                thickness=0.75,
            ),
            sections=[
                SectionConfig(width=24.0, shelves=3),
            ],
        ),
    )


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean registry before and after each test."""
    ValidatorRegistry.clear()
    yield
    ValidatorRegistry.clear()


class TestValidatorRegistration:
    """Tests for validator registration."""

    def test_register_validator(self) -> None:
        """Register a validator successfully."""
        validator = MockValidator("test_validator")
        ValidatorRegistry.register(validator)

        assert ValidatorRegistry.is_registered("test_validator")

    def test_get_registered_validator(self) -> None:
        """Get a registered validator."""
        validator = MockValidator("test_validator")
        ValidatorRegistry.register(validator)

        retrieved = ValidatorRegistry.get("test_validator")

        assert retrieved is validator

    def test_get_unregistered_raises_keyerror(self) -> None:
        """Getting unregistered validator raises KeyError."""
        with pytest.raises(KeyError) as exc_info:
            ValidatorRegistry.get("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_available_returns_sorted_names(self) -> None:
        """Available returns sorted list of validator names."""
        ValidatorRegistry.register(MockValidator("zebra"))
        ValidatorRegistry.register(MockValidator("alpha"))
        ValidatorRegistry.register(MockValidator("beta"))

        available = ValidatorRegistry.available()

        assert available == ["alpha", "beta", "zebra"]

    def test_is_registered_true(self) -> None:
        """is_registered returns True for registered validator."""
        ValidatorRegistry.register(MockValidator("test"))

        assert ValidatorRegistry.is_registered("test") is True

    def test_is_registered_false(self) -> None:
        """is_registered returns False for unregistered validator."""
        assert ValidatorRegistry.is_registered("nonexistent") is False


class TestValidatorEnableDisable:
    """Tests for enabling/disabling validators."""

    def test_enable_validator(self) -> None:
        """Enable a disabled validator."""
        validator = MockValidator("test")
        ValidatorRegistry.register(validator)
        ValidatorRegistry.disable("test")

        ValidatorRegistry.enable("test")

        assert ValidatorRegistry.is_enabled("test") is True

    def test_disable_validator(self) -> None:
        """Disable a validator."""
        validator = MockValidator("test")
        ValidatorRegistry.register(validator)

        ValidatorRegistry.disable("test")

        assert ValidatorRegistry.is_enabled("test") is False

    def test_enable_unregistered_raises_keyerror(self) -> None:
        """Enabling unregistered validator raises KeyError."""
        with pytest.raises(KeyError):
            ValidatorRegistry.enable("nonexistent")

    def test_disable_unregistered_raises_keyerror(self) -> None:
        """Disabling unregistered validator raises KeyError."""
        with pytest.raises(KeyError):
            ValidatorRegistry.disable("nonexistent")

    def test_is_enabled_default(self) -> None:
        """Validators are enabled by default."""
        ValidatorRegistry.register(MockValidator("test"))

        assert ValidatorRegistry.is_enabled("test") is True

    def test_reset_disabled(self) -> None:
        """reset_disabled re-enables all validators."""
        ValidatorRegistry.register(MockValidator("a"))
        ValidatorRegistry.register(MockValidator("b"))
        ValidatorRegistry.disable("a")
        ValidatorRegistry.disable("b")

        ValidatorRegistry.reset_disabled()

        assert ValidatorRegistry.is_enabled("a") is True
        assert ValidatorRegistry.is_enabled("b") is True


class TestValidateAll:
    """Tests for validate_all functionality."""

    def test_validate_all_runs_all_validators(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_all runs all registered validators."""
        ValidatorRegistry.register(MockValidator("a", add_error=True))
        ValidatorRegistry.register(MockValidator("b", add_error=True))

        result = ValidatorRegistry.validate_all(basic_config)

        assert len(result.errors) == 2
        error_messages = [e.message for e in result.errors]
        assert "Error from a" in error_messages
        assert "Error from b" in error_messages

    def test_validate_all_skips_disabled(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_all skips disabled validators."""
        ValidatorRegistry.register(MockValidator("enabled", add_error=True))
        ValidatorRegistry.register(MockValidator("disabled", add_error=True))
        ValidatorRegistry.disable("disabled")

        result = ValidatorRegistry.validate_all(basic_config)

        assert len(result.errors) == 1
        assert result.errors[0].message == "Error from enabled"

    def test_validate_all_merges_warnings(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_all merges warnings from all validators."""
        ValidatorRegistry.register(MockValidator("a", add_warning=True))
        ValidatorRegistry.register(MockValidator("b", add_warning=True))

        result = ValidatorRegistry.validate_all(basic_config)

        assert len(result.warnings) == 2

    def test_validate_all_catches_exceptions(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_all catches and records validator exceptions."""
        ValidatorRegistry.register(RaisingValidator())

        result = ValidatorRegistry.validate_all(basic_config)

        # Should have an error from the caught exception
        assert len(result.errors) == 1
        assert "raising" in result.errors[0].message.lower()
        assert "failed" in result.errors[0].message.lower()

    def test_validate_all_empty_registry(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_all returns empty result for empty registry."""
        result = ValidatorRegistry.validate_all(basic_config)

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestValidateSingle:
    """Tests for validate_single functionality."""

    def test_validate_single_runs_one_validator(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_single runs only specified validator."""
        ValidatorRegistry.register(MockValidator("a", add_error=True))
        ValidatorRegistry.register(MockValidator("b", add_error=True))

        result = ValidatorRegistry.validate_single("a", basic_config)

        assert len(result.errors) == 1
        assert result.errors[0].message == "Error from a"

    def test_validate_single_unregistered_raises(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """validate_single raises KeyError for unregistered validator."""
        with pytest.raises(KeyError):
            ValidatorRegistry.validate_single("nonexistent", basic_config)


class TestClear:
    """Tests for clear functionality."""

    def test_clear_removes_validators(self) -> None:
        """clear removes all registered validators."""
        ValidatorRegistry.register(MockValidator("a"))
        ValidatorRegistry.register(MockValidator("b"))

        ValidatorRegistry.clear()

        assert ValidatorRegistry.available() == []

    def test_clear_resets_disabled(self) -> None:
        """clear also resets disabled state."""
        ValidatorRegistry.register(MockValidator("a"))
        ValidatorRegistry.disable("a")

        ValidatorRegistry.clear()
        ValidatorRegistry.register(MockValidator("a"))

        assert ValidatorRegistry.is_enabled("a") is True
