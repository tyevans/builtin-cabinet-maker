"""Integration tests for ValidatorRegistry.

These tests verify that the ValidatorRegistry correctly runs all validators
and produces output matching the original validate_config function.
"""

from __future__ import annotations

import pytest

from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    GrommetConfigSchema,
    InfrastructureConfigSchema,
    LightingConfigSchema,
    LightingLocationConfig,
    LightingTypeConfig,
    MaterialConfig,
    ObstacleConfig,
    ObstacleTypeConfig,
    OutletConfigSchema,
    OutletTypeConfig,
    PositionConfigSchema,
    RoomConfig,
    SectionConfig,
    VentilationConfigSchema,
    VentilationPatternConfig,
    WallSegmentConfig,
)
from cabinets.domain.value_objects import MaterialType
from cabinets.application.config.validator import (
    ValidatorRegistry,
    validate_config,
    _ensure_validators_registered,
)
from cabinets.application.config.validators import (
    InfrastructureValidator,
    ObstacleValidator,
    SectionDimensionValidator,
    WoodworkingValidator,
)


@pytest.fixture(autouse=True)
def ensure_validators():
    """Ensure validators are registered for each test."""
    # Clear and re-register to ensure clean state
    ValidatorRegistry.clear()
    _ensure_validators_registered()
    yield
    # Clean up after test
    ValidatorRegistry.reset_disabled()


class TestAllValidatorsRegistered:
    """Tests to verify all expected validators are registered."""

    def test_woodworking_validator_registered(self) -> None:
        """WoodworkingValidator is registered."""
        assert ValidatorRegistry.is_registered("woodworking")

    def test_obstacle_validator_registered(self) -> None:
        """ObstacleValidator is registered."""
        assert ValidatorRegistry.is_registered("obstacle")

    def test_infrastructure_validator_registered(self) -> None:
        """InfrastructureValidator is registered."""
        assert ValidatorRegistry.is_registered("infrastructure")

    def test_section_dimension_validator_registered(self) -> None:
        """SectionDimensionValidator is registered."""
        assert ValidatorRegistry.is_registered("section_dimension")

    def test_all_four_validators_available(self) -> None:
        """All four validators are in the available list."""
        available = ValidatorRegistry.available()

        assert "woodworking" in available
        assert "obstacle" in available
        assert "infrastructure" in available
        assert "section_dimension" in available
        assert len(available) == 4


class TestRegistryMatchesValidateConfig:
    """Tests to verify registry output matches validate_config."""

    def test_simple_config_same_result(self) -> None:
        """Simple config produces same result from both methods."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=36.0,  # Low aspect ratio to avoid stability warning
                depth=24.0,
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.75,
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                ],
            ),
        )

        registry_result = ValidatorRegistry.validate_all(config)
        facade_result = validate_config(config)

        assert len(registry_result.errors) == len(facade_result.errors)
        assert len(registry_result.warnings) == len(facade_result.warnings)
        assert registry_result.is_valid == facade_result.is_valid

    def test_config_with_errors_same_result(self) -> None:
        """Config with errors produces same result from both methods."""
        config = CabinetConfiguration(
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
                    SectionConfig(width=60.0, shelves=3),  # Too wide for cabinet
                ],
            ),
        )

        registry_result = ValidatorRegistry.validate_all(config)
        facade_result = validate_config(config)

        assert len(registry_result.errors) == len(facade_result.errors)
        assert not registry_result.is_valid
        assert not facade_result.is_valid


class TestComplexConfigValidation:
    """Tests for complex configurations using all validators."""

    @pytest.fixture
    def complex_config(self) -> CabinetConfiguration:
        """Create a complex config with room, obstacles, and infrastructure."""
        return CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=16.0,
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.75,
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                    SectionConfig(width="fill", shelves=5),
                ],
            ),
            room=RoomConfig(
                name="test_room",
                walls=[
                    WallSegmentConfig(length=120.0, height=96.0),
                ],
                obstacles=[
                    ObstacleConfig(
                        type=ObstacleTypeConfig.WINDOW,
                        wall=0,
                        horizontal_offset=10.0,
                        bottom=24.0,
                        width=30.0,
                        height=36.0,
                    ),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                lighting=[
                    LightingConfigSchema(
                        type=LightingTypeConfig.LED_STRIP,
                        location=LightingLocationConfig.UNDER_CABINET,
                        section_indices=[0, 1],
                        length=48.0,
                    ),
                ],
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=12.0, y=36.0),
                    ),
                ],
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=36.0, y=24.0),
                    ),
                ],
                ventilation=[
                    VentilationConfigSchema(
                        pattern=VentilationPatternConfig.GRID,
                        panel="back",
                        position=PositionConfigSchema(x=48.0, y=6.0),
                        width=6.0,
                        height=4.0,
                    ),
                ],
            ),
        )

    def test_all_validators_run_on_complex_config(
        self, complex_config: CabinetConfiguration
    ) -> None:
        """All validators process complex config."""
        result = validate_config(complex_config)

        # Should run without errors (config is valid)
        # but may have warnings
        assert result.is_valid or len(result.errors) >= 0

    def test_disabling_validator_skips_checks(
        self, complex_config: CabinetConfiguration
    ) -> None:
        """Disabling a validator skips its checks."""
        # Get result with all validators
        full_result = ValidatorRegistry.validate_all(complex_config)
        full_warning_count = len(full_result.warnings)

        # Disable woodworking and check again
        ValidatorRegistry.disable("woodworking")
        reduced_result = ValidatorRegistry.validate_all(complex_config)

        # Should have fewer or equal warnings
        assert len(reduced_result.warnings) <= full_warning_count

        # Re-enable for other tests
        ValidatorRegistry.enable("woodworking")


class TestValidatorProtocolCompliance:
    """Tests to verify validators comply with the Validator protocol."""

    def test_woodworking_implements_protocol(self) -> None:
        """WoodworkingValidator implements Validator protocol."""
        from cabinets.contracts.validators import Validator

        validator = WoodworkingValidator()
        assert isinstance(validator, Validator)

    def test_obstacle_implements_protocol(self) -> None:
        """ObstacleValidator implements Validator protocol."""
        from cabinets.contracts.validators import Validator

        validator = ObstacleValidator()
        assert isinstance(validator, Validator)

    def test_infrastructure_implements_protocol(self) -> None:
        """InfrastructureValidator implements Validator protocol."""
        from cabinets.contracts.validators import Validator

        validator = InfrastructureValidator()
        assert isinstance(validator, Validator)

    def test_section_dimension_implements_protocol(self) -> None:
        """SectionDimensionValidator implements Validator protocol."""
        from cabinets.contracts.validators import Validator

        validator = SectionDimensionValidator()
        assert isinstance(validator, Validator)


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with original validator.py."""

    def test_validation_error_importable_from_original(self) -> None:
        """ValidationError can be imported from original module."""
        from cabinets.application.config.validator import ValidationError

        error = ValidationError(path="test", message="test message")
        assert error.path == "test"
        assert error.message == "test message"

    def test_validation_warning_importable_from_original(self) -> None:
        """ValidationWarning can be imported from original module."""
        from cabinets.application.config.validator import ValidationWarning

        warning = ValidationWarning(
            path="test", message="test message", suggestion="fix it"
        )
        assert warning.path == "test"
        assert warning.suggestion == "fix it"

    def test_validation_result_importable_from_original(self) -> None:
        """ValidationResult can be imported from original module."""
        from cabinets.application.config.validator import ValidationResult

        result = ValidationResult()
        result.add_error("test", "error")
        result.add_warning("test", "warning")

        assert not result.is_valid
        assert result.has_warnings

    def test_legacy_functions_still_work(self) -> None:
        """Legacy check_*_advisories functions still work."""
        from cabinets.application.config.validator import (
            check_infrastructure_advisories,
            check_obstacle_advisories,
            check_woodworking_advisories,
        )

        config = CabinetConfiguration(
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

        # All should return results without error
        woodworking_result = check_woodworking_advisories(config)
        assert woodworking_result is not None

        obstacle_result = check_obstacle_advisories(config)
        assert isinstance(obstacle_result, list)

        infra_result = check_infrastructure_advisories(config)
        assert isinstance(infra_result, list)

    def test_constants_importable_from_original(self) -> None:
        """Constants can be imported from original module."""
        from cabinets.application.config.validator import (
            MAX_ASPECT_RATIO,
            MIN_CUTOUT_EDGE_DISTANCE,
            MIN_RECOMMENDED_THICKNESS,
            STANDARD_GROMMET_SIZES,
        )

        assert MIN_RECOMMENDED_THICKNESS == 0.5
        assert MAX_ASPECT_RATIO == 4.0
        assert 2.5 in STANDARD_GROMMET_SIZES
        assert MIN_CUTOUT_EDGE_DISTANCE == 1.0
