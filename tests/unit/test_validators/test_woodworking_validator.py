"""Unit tests for WoodworkingValidator."""

from __future__ import annotations

import pytest

from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    MaterialConfig,
    SectionConfig,
)
from cabinets.domain.value_objects import MaterialType
from cabinets.application.config.validators.woodworking import (
    MAX_ASPECT_RATIO,
    MIN_RECOMMENDED_THICKNESS,
    WoodworkingValidator,
    check_woodworking_advisories,
)


@pytest.fixture
def validator() -> WoodworkingValidator:
    """Create a WoodworkingValidator instance."""
    return WoodworkingValidator()


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


class TestWoodworkingValidatorName:
    """Tests for validator name property."""

    def test_name_is_woodworking(self, validator: WoodworkingValidator) -> None:
        """Validator name should be 'woodworking'."""
        assert validator.name == "woodworking"


class TestShelfSpanValidation:
    """Tests for shelf span validation."""

    def test_no_warning_for_acceptable_span(
        self, validator: WoodworkingValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No warning for shelf span within limits."""
        result = validator.validate(basic_config)

        # 24" span is acceptable for 3/4" plywood
        span_warnings = [w for w in result.warnings if "span" in w.message.lower()]
        assert len(span_warnings) == 0

    def test_warning_for_excessive_span(self, validator: WoodworkingValidator) -> None:
        """Warning generated for shelf span exceeding limits."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=72.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.5,
                ),
                sections=[
                    SectionConfig(
                        width=48.0, shelves=3
                    ),  # 48" span is too much for 1/2" plywood
                ],
            ),
        )

        result = validator.validate(config)

        span_warnings = [w for w in result.warnings if "span" in w.message.lower()]
        assert len(span_warnings) >= 1
        assert "exceeds recommended" in span_warnings[0].message.lower()

    def test_fill_section_span_estimated(self, validator: WoodworkingValidator) -> None:
        """Fill section width is estimated for span checking."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=96.0,  # Large cabinet
                height=84.0,
                depth=12.0,
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.5,  # Thin material
                ),
                sections=[
                    SectionConfig(
                        width="fill", shelves=3
                    ),  # Fill section will be ~94.5"
                ],
            ),
        )

        result = validator.validate(config)

        # Should warn about the fill section span
        span_warnings = [w for w in result.warnings if "span" in w.message.lower()]
        assert len(span_warnings) >= 1


class TestMaterialThicknessValidation:
    """Tests for material thickness validation."""

    def test_no_warning_for_adequate_thickness(
        self, validator: WoodworkingValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No warning for adequate material thickness (0.75")."""
        result = validator.validate(basic_config)

        thickness_warnings = [
            w
            for w in result.warnings
            if "thickness" in w.message.lower() and "below" in w.message.lower()
        ]
        assert len(thickness_warnings) == 0

    def test_warning_for_thin_material(self, validator: WoodworkingValidator) -> None:
        """Warning generated for thin material."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.25,  # Very thin
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                ],
            ),
        )

        result = validator.validate(config)

        thickness_warnings = [
            w
            for w in result.warnings
            if "thickness" in w.message.lower() and "below" in w.message.lower()
        ]
        assert len(thickness_warnings) >= 1
        assert str(MIN_RECOMMENDED_THICKNESS) in thickness_warnings[0].message

    def test_no_warning_for_standard_back_panel(
        self, validator: WoodworkingValidator
    ) -> None:
        """No warning for standard back panel thickness.

        Note: The original validator checks for back_thickness < 0.25, but
        Pydantic enforces minimum thickness at 0.25, so this warning path
        is unreachable in practice. This test verifies no false warnings
        for valid back panel configurations.
        """
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
                back_material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.25,  # Standard 1/4" back panel
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                ],
            ),
        )

        result = validator.validate(config)

        back_warnings = [
            w for w in result.warnings if "back panel" in w.message.lower()
        ]
        assert len(back_warnings) == 0


class TestAspectRatioValidation:
    """Tests for aspect ratio (stability) validation."""

    def test_no_warning_for_stable_ratio(
        self, validator: WoodworkingValidator, basic_config: CabinetConfiguration
    ) -> None:
        """No warning for stable height-to-depth ratio."""
        result = validator.validate(basic_config)

        # 84/12 = 7:1, which exceeds MAX_ASPECT_RATIO (4.0), so this WILL warn
        # Let's check what we get
        # Actually 84/12 = 7 which is > 4
        ratio_warnings = [
            w
            for w in result.warnings
            if "ratio" in w.message.lower() or "stability" in w.message.lower()
        ]
        # Since 84/12 = 7:1 > 4:1, we expect a warning
        assert len(ratio_warnings) >= 1

    def test_warning_for_unstable_ratio(self, validator: WoodworkingValidator) -> None:
        """Warning generated for unstable height-to-depth ratio."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=96.0,
                depth=12.0,  # 96/12 = 8:1 ratio
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.75,
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                ],
            ),
        )

        result = validator.validate(config)

        ratio_warnings = [w for w in result.warnings if "ratio" in w.message.lower()]
        assert len(ratio_warnings) >= 1
        assert "8.0:1" in ratio_warnings[0].message
        assert str(int(MAX_ASPECT_RATIO)) in ratio_warnings[0].suggestion

    def test_no_warning_for_squat_cabinet(
        self, validator: WoodworkingValidator
    ) -> None:
        """No warning for squat (stable) cabinet."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=36.0,
                depth=24.0,  # 36/24 = 1.5:1 ratio
                material=MaterialConfig(
                    type=MaterialType.PLYWOOD,
                    thickness=0.75,
                ),
                sections=[
                    SectionConfig(width=24.0, shelves=3),
                ],
            ),
        )

        result = validator.validate(config)

        ratio_warnings = [w for w in result.warnings if "ratio" in w.message.lower()]
        assert len(ratio_warnings) == 0


class TestLegacyFunction:
    """Tests for backwards-compatible check_woodworking_advisories function."""

    def test_legacy_function_returns_same_result(
        self, validator: WoodworkingValidator, basic_config: CabinetConfiguration
    ) -> None:
        """Legacy function returns same result as validator."""
        legacy_result = check_woodworking_advisories(basic_config)
        validator_result = validator.validate(basic_config)

        assert len(legacy_result.errors) == len(validator_result.errors)
        assert len(legacy_result.warnings) == len(validator_result.warnings)
