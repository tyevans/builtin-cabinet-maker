"""Unit tests for InfrastructureValidator."""

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
    OutletConfigSchema,
    OutletTypeConfig,
    PositionConfigSchema,
    SectionConfig,
    VentilationConfigSchema,
    VentilationPatternConfig,
)
from cabinets.domain.value_objects import MaterialType
from cabinets.application.config.validators.infrastructure import (
    InfrastructureValidator,
    check_infrastructure_advisories,
)


@pytest.fixture
def validator() -> InfrastructureValidator:
    """Create an InfrastructureValidator instance."""
    return InfrastructureValidator()


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
                SectionConfig(width="fill", shelves=5),
            ],
        ),
    )


class TestInfrastructureValidatorName:
    """Tests for validator name property."""

    def test_name_is_infrastructure(self, validator: InfrastructureValidator) -> None:
        """Validator name should be 'infrastructure'."""
        assert validator.name == "infrastructure"


class TestNoInfrastructure:
    """Tests for configurations without infrastructure."""

    def test_no_errors_without_infrastructure(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No errors when there is no infrastructure config."""
        result = validator.validate(basic_config)

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestGrommetValidation:
    """Tests for grommet validation (V-05)."""

    def test_valid_grommet_sizes(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No error for valid grommet sizes (2, 2.5, 3)."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.0,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(x=24.0, y=36.0),
                ),
                GrommetConfigSchema(
                    size=3.0,
                    panel="back",
                    position=PositionConfigSchema(x=36.0, y=36.0),
                ),
            ],
        )

        result = validator.validate(basic_config)

        size_errors = [e for e in result.errors if "grommet size" in e.message.lower()]
        assert len(size_errors) == 0

    def test_error_for_invalid_grommet_size(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error for invalid grommet size."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=1.5,  # Invalid size
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
        )

        result = validator.validate(basic_config)

        size_errors = [e for e in result.errors if "grommet size" in e.message.lower()]
        assert len(size_errors) >= 1
        assert size_errors[0].value == 1.5


class TestSectionIndexValidation:
    """Tests for section index validation (V-06)."""

    def test_error_for_invalid_outlet_section_index(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error for outlet referencing invalid section."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.SINGLE,
                    section_index=10,  # Only 2 sections (0, 1)
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
        )

        result = validator.validate(basic_config)

        section_errors = [
            e for e in result.errors if "section index" in e.message.lower()
        ]
        assert len(section_errors) >= 1
        assert section_errors[0].value == 10

    def test_error_for_invalid_lighting_section_index(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error for lighting referencing invalid section."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            lighting=[
                LightingConfigSchema(
                    type=LightingTypeConfig.LED_STRIP,
                    location=LightingLocationConfig.UNDER_CABINET,
                    section_indices=[0, 5, 10],  # 5 and 10 are invalid
                    length=24.0,
                ),
            ],
        )

        result = validator.validate(basic_config)

        section_errors = [
            e for e in result.errors if "section index" in e.message.lower()
        ]
        assert len(section_errors) >= 2  # One for 5 and one for 10

    def test_error_for_invalid_grommet_section_index(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error for grommet referencing invalid section."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                    section_index=5,  # Invalid
                ),
            ],
        )

        result = validator.validate(basic_config)

        section_errors = [
            e for e in result.errors if "section index" in e.message.lower()
        ]
        assert len(section_errors) >= 1


class TestCutoutBoundsValidation:
    """Tests for cutout bounds validation (V-01)."""

    def test_error_for_cutout_exceeding_panel_width(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error when cutout exceeds panel width."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.DOUBLE,
                    section_index=0,
                    panel="back",
                    position=PositionConfigSchema(x=46.0, y=36.0),  # Too close to edge
                ),
            ],
        )

        result = validator.validate(basic_config)

        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message.lower()
        ]
        assert len(bounds_errors) >= 1

    def test_error_for_cutout_exceeding_panel_height(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error when cutout exceeds panel height."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.SINGLE,
                    section_index=0,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=82.0),  # Too close to top
                ),
            ],
        )

        result = validator.validate(basic_config)

        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message.lower()
        ]
        assert len(bounds_errors) >= 1

    def test_error_for_negative_position(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error when cutout has negative position."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(x=-1.0, y=36.0),  # Negative x
                ),
            ],
        )

        result = validator.validate(basic_config)

        negative_errors = [
            e for e in result.errors if "negative position" in e.message.lower()
        ]
        assert len(negative_errors) >= 1


class TestEdgeDistanceValidation:
    """Tests for cutout edge distance validation (V-02)."""

    def test_error_for_cutout_too_close_to_left_edge(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error when cutout is too close to left edge."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.0,
                    panel="back",
                    position=PositionConfigSchema(x=0.5, y=36.0),  # < 1" from edge
                ),
            ],
        )

        result = validator.validate(basic_config)

        edge_errors = [
            e for e in result.errors if "too close to edge" in e.message.lower()
        ]
        assert len(edge_errors) >= 1

    def test_error_for_cutout_too_close_to_bottom_edge(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error when cutout is too close to bottom edge."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.0,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=0.5),  # < 1" from edge
                ),
            ],
        )

        result = validator.validate(basic_config)

        edge_errors = [
            e for e in result.errors if "too close to edge" in e.message.lower()
        ]
        assert len(edge_errors) >= 1


class TestCutoutOverlapValidation:
    """Tests for cutout overlap detection (V-03)."""

    def test_error_for_overlapping_cutouts(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Error when cutouts overlap."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(
                        x=13.0, y=36.5
                    ),  # Overlaps with first
                ),
            ],
        )

        result = validator.validate(basic_config)

        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) >= 1

    def test_no_error_for_non_overlapping_cutouts(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No error when cutouts don't overlap."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.0,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
                GrommetConfigSchema(
                    size=2.0,
                    panel="back",
                    position=PositionConfigSchema(x=24.0, y=36.0),  # Far apart
                ),
            ],
        )

        result = validator.validate(basic_config)

        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) == 0

    def test_no_overlap_check_across_panels(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No overlap error for cutouts on different panels."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
                GrommetConfigSchema(
                    size=2.5,
                    panel="bottom",
                    position=PositionConfigSchema(
                        x=12.0, y=6.0
                    ),  # Same x but different panel
                ),
            ],
        )

        result = validator.validate(basic_config)

        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) == 0


class TestOutletAccessibilityValidation:
    """Tests for outlet accessibility validation (V-04)."""

    def test_warning_for_outlet_behind_shelves(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Warning when outlet is behind a section with shelves."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.SINGLE,
                    section_index=0,  # Section 0 has 3 shelves
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
        )

        result = validator.validate(basic_config)

        accessibility_warnings = [
            w for w in result.warnings if "fixed shelf" in w.message.lower()
        ]
        assert len(accessibility_warnings) >= 1


class TestVentilationAdequacyValidation:
    """Tests for ventilation adequacy validation (V-07)."""

    def test_warning_for_outlets_without_ventilation(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Warning when outlets exist but no ventilation."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.SINGLE,
                    section_index=0,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
            # No ventilation
        )

        result = validator.validate(basic_config)

        vent_warnings = [
            w for w in result.warnings if "ventilation" in w.message.lower()
        ]
        assert len(vent_warnings) >= 1

    def test_no_warning_with_ventilation(
        self, validator: InfrastructureValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No ventilation warning when ventilation is configured."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            outlets=[
                OutletConfigSchema(
                    type=OutletTypeConfig.SINGLE,
                    section_index=0,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
            ventilation=[
                VentilationConfigSchema(
                    pattern=VentilationPatternConfig.GRID,
                    panel="back",
                    position=PositionConfigSchema(x=24.0, y=6.0),
                    width=4.0,
                    height=4.0,
                ),
            ],
        )

        result = validator.validate(basic_config)

        vent_warnings = [
            w
            for w in result.warnings
            if "ventilation" in w.message.lower() and "may need" in w.message.lower()
        ]
        assert len(vent_warnings) == 0


class TestLegacyFunction:
    """Tests for backwards-compatible check_infrastructure_advisories function."""

    def test_legacy_function_returns_list(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """Legacy function returns list of errors and warnings."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=2.5,
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
        )

        result = check_infrastructure_advisories(basic_config)

        assert isinstance(result, list)

    def test_legacy_function_includes_errors(
        self, basic_config: CabinetConfiguration
    ) -> None:
        """Legacy function includes errors for invalid config."""
        basic_config.infrastructure = InfrastructureConfigSchema(
            grommets=[
                GrommetConfigSchema(
                    size=1.5,  # Invalid size
                    panel="back",
                    position=PositionConfigSchema(x=12.0, y=36.0),
                ),
            ],
        )

        result = check_infrastructure_advisories(basic_config)

        from cabinets.application.config.validators.base import ValidationError

        errors = [r for r in result if isinstance(r, ValidationError)]
        assert len(errors) >= 1
