"""Unit tests for FRD-21 Safety and Compliance features.

This module provides comprehensive tests for:
- Safety enums (Task 01)
- SafetyConfig validation (Task 02)
- SafetyCheckResult dataclass
- WeightCapacityEstimate dataclass (Task 03)
- SafetyAssessment aggregate
- Material compliance checking
- Seismic requirements checking
- SafetyLabel dataclass
- SafetyService methods

Note: Individual safety check methods (anti-tip, accessibility, clearance)
have dedicated test files for detailed coverage.
"""

from __future__ import annotations

import pytest

from cabinets.domain.entities import Cabinet, Section, Shelf
from cabinets.domain.services.safety import (
    ANTI_TIP_HEIGHT_THRESHOLD,
    ADA_MIN_ACCESSIBLE_PERCENTAGE,
    ADA_MIN_REACH,
    ADA_MAX_REACH_UNOBSTRUCTED,
    HEAT_SOURCE_VERTICAL_CLEARANCE,
    HIGH_SEISMIC_ZONES,
    KCMA_SHELF_LOAD_PSF,
    NEC_PANEL_FRONT_CLEARANCE,
    NEC_PANEL_WIDTH_CLEARANCE,
    AccessibilityReport,
    SafetyAssessment,
    SafetyCheckResult,
    SafetyConfig,
    SafetyLabel,
    SafetyService,
    WeightCapacityEstimate,
)
from cabinets.domain.value_objects import (
    ADAStandard,
    MaterialCertification,
    MaterialSpec,
    ObstacleType,
    Position,
    SafetyCategory,
    SafetyCheckStatus,
    SeismicZone,
    VOCCategory,
)


# ==============================================================================
# Enum Tests (Task 01)
# ==============================================================================


class TestSafetyEnums:
    """Test safety-related enums."""

    def test_safety_check_status_values(self) -> None:
        """Test SafetyCheckStatus enum values."""
        assert SafetyCheckStatus.PASS.value == "pass"
        assert SafetyCheckStatus.WARNING.value == "warning"
        assert SafetyCheckStatus.ERROR.value == "error"
        assert SafetyCheckStatus.NOT_APPLICABLE.value == "not_applicable"

    def test_safety_category_values(self) -> None:
        """Test SafetyCategory enum values."""
        assert SafetyCategory.STRUCTURAL.value == "structural"
        assert SafetyCategory.STABILITY.value == "stability"
        assert SafetyCategory.ACCESSIBILITY.value == "accessibility"
        assert SafetyCategory.CLEARANCE.value == "clearance"
        assert SafetyCategory.MATERIAL.value == "material"
        assert SafetyCategory.CHILD_SAFETY.value == "child_safety"
        assert SafetyCategory.SEISMIC.value == "seismic"

    def test_seismic_zone_values(self) -> None:
        """Test SeismicZone enum values."""
        assert SeismicZone.A.value == "A"
        assert SeismicZone.B.value == "B"
        assert SeismicZone.C.value == "C"
        assert SeismicZone.D.value == "D"
        assert SeismicZone.E.value == "E"
        assert SeismicZone.F.value == "F"

    def test_material_certification_values(self) -> None:
        """Test MaterialCertification enum values."""
        assert MaterialCertification.CARB_PHASE2.value == "carb_phase2"
        assert MaterialCertification.NAF.value == "naf"
        assert MaterialCertification.ULEF.value == "ulef"
        assert MaterialCertification.NONE.value == "none"
        assert MaterialCertification.UNKNOWN.value == "unknown"

    def test_voc_category_values(self) -> None:
        """Test VOCCategory enum values per SCAQMD Rule 1113."""
        assert VOCCategory.SUPER_COMPLIANT.value == "super_compliant"
        assert VOCCategory.COMPLIANT.value == "compliant"
        assert VOCCategory.STANDARD.value == "standard"
        assert VOCCategory.UNKNOWN.value == "unknown"

    def test_ada_standard_values(self) -> None:
        """Test ADAStandard enum values."""
        assert ADAStandard.ADA_2010.value == "ADA_2010"

    def test_extended_obstacle_type(self) -> None:
        """Test extended ObstacleType enum includes safety types."""
        assert ObstacleType.ELECTRICAL_PANEL.value == "electrical_panel"
        assert ObstacleType.COOKTOP.value == "cooktop"
        assert ObstacleType.HEAT_SOURCE.value == "heat_source"
        assert ObstacleType.CLOSET_LIGHT.value == "closet_light"


# ==============================================================================
# SafetyConfig Tests (Task 02)
# ==============================================================================


class TestSafetyConfig:
    """Test SafetyConfig domain object."""

    def test_default_values(self) -> None:
        """Test SafetyConfig default values."""
        config = SafetyConfig()
        assert config.safety_factor == 4.0
        assert config.accessibility_enabled is False
        assert config.accessibility_standard == ADAStandard.ADA_2010
        assert config.child_safe_mode is False
        assert config.seismic_zone is None
        assert config.deflection_limit_ratio == 200
        assert config.check_clearances is True
        assert config.generate_labels is True
        assert config.material_certification == MaterialCertification.UNKNOWN
        assert config.finish_voc_category == VOCCategory.UNKNOWN

    def test_custom_values(self) -> None:
        """Test SafetyConfig with custom values."""
        config = SafetyConfig(
            safety_factor=3.0,
            accessibility_enabled=True,
            seismic_zone=SeismicZone.D,
            child_safe_mode=True,
            deflection_limit_ratio=240,
            check_clearances=False,
            material_certification=MaterialCertification.CARB_PHASE2,
            finish_voc_category=VOCCategory.SUPER_COMPLIANT,
        )
        assert config.safety_factor == 3.0
        assert config.accessibility_enabled is True
        assert config.seismic_zone == SeismicZone.D
        assert config.child_safe_mode is True
        assert config.deflection_limit_ratio == 240
        assert config.check_clearances is False
        assert config.material_certification == MaterialCertification.CARB_PHASE2
        assert config.finish_voc_category == VOCCategory.SUPER_COMPLIANT

    def test_invalid_safety_factor_too_low(self) -> None:
        """Test safety factor below minimum raises error."""
        with pytest.raises(ValueError, match="safety_factor"):
            SafetyConfig(safety_factor=1.0)

    def test_invalid_safety_factor_too_high(self) -> None:
        """Test safety factor above maximum raises error."""
        with pytest.raises(ValueError, match="safety_factor"):
            SafetyConfig(safety_factor=7.0)

    def test_safety_factor_boundary_minimum(self) -> None:
        """Test safety factor at minimum boundary (2.0) is valid."""
        config = SafetyConfig(safety_factor=2.0)
        assert config.safety_factor == 2.0

    def test_safety_factor_boundary_maximum(self) -> None:
        """Test safety factor at maximum boundary (6.0) is valid."""
        config = SafetyConfig(safety_factor=6.0)
        assert config.safety_factor == 6.0

    def test_invalid_deflection_ratio(self) -> None:
        """Test invalid deflection ratio raises error."""
        with pytest.raises(ValueError, match="deflection"):
            SafetyConfig(deflection_limit_ratio=150)

    def test_valid_deflection_ratios(self) -> None:
        """Test valid deflection ratios are accepted."""
        for ratio in [200, 240, 360]:
            config = SafetyConfig(deflection_limit_ratio=ratio)
            assert config.deflection_limit_ratio == ratio

    def test_requires_seismic_hardware_none_zone(self) -> None:
        """Test no seismic zone returns False for requires_seismic_hardware."""
        config = SafetyConfig(seismic_zone=None)
        assert config.requires_seismic_hardware is False

    def test_requires_seismic_hardware_low_zones(self) -> None:
        """Test low seismic zones (A, B, C) don't require hardware."""
        for zone in [SeismicZone.A, SeismicZone.B, SeismicZone.C]:
            config = SafetyConfig(seismic_zone=zone)
            assert config.requires_seismic_hardware is False

    def test_requires_seismic_hardware_high_zones(self) -> None:
        """Test high seismic zones (D, E, F) require hardware."""
        for zone in [SeismicZone.D, SeismicZone.E, SeismicZone.F]:
            config = SafetyConfig(seismic_zone=zone)
            assert config.requires_seismic_hardware is True

    def test_high_seismic_zones_constant(self) -> None:
        """Test HIGH_SEISMIC_ZONES contains D, E, F."""
        assert "D" in HIGH_SEISMIC_ZONES
        assert "E" in HIGH_SEISMIC_ZONES
        assert "F" in HIGH_SEISMIC_ZONES
        assert "A" not in HIGH_SEISMIC_ZONES


# ==============================================================================
# SafetyCheckResult Tests
# ==============================================================================


class TestSafetyCheckResult:
    """Test SafetyCheckResult dataclass."""

    def test_create_valid_result(self) -> None:
        """Test creating a valid check result."""
        result = SafetyCheckResult(
            check_id="test_check",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.PASS,
            message="Test passed",
        )
        assert result.check_id == "test_check"
        assert result.category == SafetyCategory.STRUCTURAL
        assert result.status == SafetyCheckStatus.PASS
        assert result.message == "Test passed"

    def test_result_with_optional_fields(self) -> None:
        """Test result with all optional fields."""
        result = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.WARNING,
            message="Test warning",
            remediation="Fix this issue",
            standard_reference="ASTM F2057-23",
            details={"key": "value"},
        )
        assert result.remediation == "Fix this issue"
        assert result.standard_reference == "ASTM F2057-23"
        assert result.details == {"key": "value"}

    def test_is_pass_property(self) -> None:
        """Test is_pass property."""
        result_pass = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.PASS,
            message="Passed",
        )
        result_warning = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.WARNING,
            message="Warning",
        )
        assert result_pass.is_pass is True
        assert result_warning.is_pass is False

    def test_is_warning_property(self) -> None:
        """Test is_warning property."""
        result_warning = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.WARNING,
            message="Warning",
        )
        assert result_warning.is_warning is True

    def test_is_error_property(self) -> None:
        """Test is_error property."""
        result_error = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.ERROR,
            message="Error",
        )
        assert result_error.is_error is True

    def test_formatted_message_pass(self) -> None:
        """Test formatted message includes [PASS] prefix."""
        result = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.PASS,
            message="Test passed",
        )
        assert result.formatted_message == "[PASS] Test passed"

    def test_formatted_message_warning(self) -> None:
        """Test formatted message includes [WARN] prefix."""
        result = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.WARNING,
            message="Test warning",
        )
        assert result.formatted_message == "[WARN] Test warning"

    def test_formatted_message_error(self) -> None:
        """Test formatted message includes [FAIL] prefix."""
        result = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.ERROR,
            message="Test error",
        )
        assert result.formatted_message == "[FAIL] Test error"

    def test_formatted_message_not_applicable(self) -> None:
        """Test formatted message includes [N/A] prefix."""
        result = SafetyCheckResult(
            check_id="test",
            category=SafetyCategory.STRUCTURAL,
            status=SafetyCheckStatus.NOT_APPLICABLE,
            message="Not applicable",
        )
        assert result.formatted_message == "[N/A] Not applicable"

    def test_empty_check_id_raises(self) -> None:
        """Test empty check_id raises error."""
        with pytest.raises(ValueError, match="check_id"):
            SafetyCheckResult(
                check_id="",
                category=SafetyCategory.STRUCTURAL,
                status=SafetyCheckStatus.PASS,
                message="Test",
            )

    def test_empty_message_raises(self) -> None:
        """Test empty message raises error."""
        with pytest.raises(ValueError, match="message"):
            SafetyCheckResult(
                check_id="test",
                category=SafetyCategory.STRUCTURAL,
                status=SafetyCheckStatus.PASS,
                message="",
            )


# ==============================================================================
# WeightCapacityEstimate Tests (Task 03)
# ==============================================================================


class TestWeightCapacityEstimate:
    """Test WeightCapacityEstimate dataclass."""

    def test_create_valid_estimate(self) -> None:
        """Test creating a valid weight capacity estimate."""
        estimate = WeightCapacityEstimate(
            panel_id="shelf_0",
            safe_load_lbs=45.0,
            max_deflection_inches=0.18,
            deflection_at_rated_load=0.045,
            safety_factor=4.0,
            material="plywood",
            span_inches=36.0,
        )
        assert estimate.panel_id == "shelf_0"
        assert estimate.safe_load_lbs == 45.0
        assert estimate.max_deflection_inches == 0.18
        assert estimate.deflection_at_rated_load == 0.045
        assert estimate.safety_factor == 4.0
        assert estimate.material == "plywood"
        assert estimate.span_inches == 36.0
        assert "Estimate only" in estimate.disclaimer

    def test_negative_load_raises(self) -> None:
        """Test negative load raises error."""
        with pytest.raises(ValueError):
            WeightCapacityEstimate(
                panel_id="shelf_0",
                safe_load_lbs=-10.0,
                max_deflection_inches=0.18,
                deflection_at_rated_load=0.045,
                safety_factor=4.0,
                material="plywood",
                span_inches=36.0,
            )

    def test_zero_load_valid(self) -> None:
        """Test zero load is valid."""
        estimate = WeightCapacityEstimate(
            panel_id="shelf_0",
            safe_load_lbs=0.0,
            max_deflection_inches=0.18,
            deflection_at_rated_load=0.0,
            safety_factor=4.0,
            material="plywood",
            span_inches=36.0,
        )
        assert estimate.safe_load_lbs == 0.0

    def test_invalid_max_deflection_raises(self) -> None:
        """Test non-positive max_deflection raises error."""
        with pytest.raises(ValueError):
            WeightCapacityEstimate(
                panel_id="shelf_0",
                safe_load_lbs=45.0,
                max_deflection_inches=0.0,
                deflection_at_rated_load=0.045,
                safety_factor=4.0,
                material="plywood",
                span_inches=36.0,
            )

    def test_invalid_safety_factor_raises(self) -> None:
        """Test non-positive safety_factor raises error."""
        with pytest.raises(ValueError):
            WeightCapacityEstimate(
                panel_id="shelf_0",
                safe_load_lbs=45.0,
                max_deflection_inches=0.18,
                deflection_at_rated_load=0.045,
                safety_factor=0.0,
                material="plywood",
                span_inches=36.0,
            )

    def test_invalid_span_raises(self) -> None:
        """Test non-positive span raises error."""
        with pytest.raises(ValueError):
            WeightCapacityEstimate(
                panel_id="shelf_0",
                safe_load_lbs=45.0,
                max_deflection_inches=0.18,
                deflection_at_rated_load=0.045,
                safety_factor=4.0,
                material="plywood",
                span_inches=0.0,
            )

    def test_meets_kcma_standard_true(self) -> None:
        """Test meets_kcma_standard property for adequate capacity."""
        estimate = WeightCapacityEstimate(
            panel_id="shelf_0",
            safe_load_lbs=45.0,  # > KCMA_SHELF_LOAD_PSF (15)
            max_deflection_inches=0.18,
            deflection_at_rated_load=0.045,
            safety_factor=4.0,
            material="plywood",
            span_inches=36.0,
        )
        assert estimate.meets_kcma_standard is True

    def test_meets_kcma_standard_false(self) -> None:
        """Test meets_kcma_standard property for inadequate capacity."""
        estimate = WeightCapacityEstimate(
            panel_id="shelf_0",
            safe_load_lbs=10.0,  # < KCMA_SHELF_LOAD_PSF (15)
            max_deflection_inches=0.18,
            deflection_at_rated_load=0.045,
            safety_factor=4.0,
            material="plywood",
            span_inches=36.0,
        )
        assert estimate.meets_kcma_standard is False

    def test_formatted_message(self) -> None:
        """Test formatted message property."""
        estimate = WeightCapacityEstimate(
            panel_id="shelf_0",
            safe_load_lbs=45.0,
            max_deflection_inches=0.18,
            deflection_at_rated_load=0.045,
            safety_factor=4.0,
            material="plywood",
            span_inches=36.0,
        )
        message = estimate.formatted_message
        assert "shelf_0" in message
        assert "45 lbs" in message
        assert "plywood" in message
        assert "36.0" in message
        assert "4.0:1 safety factor" in message


# ==============================================================================
# SafetyAssessment Tests
# ==============================================================================


class TestSafetyAssessment:
    """Test SafetyAssessment aggregate."""

    def test_empty_assessment(self) -> None:
        """Test creating an empty assessment."""
        assessment = SafetyAssessment(
            check_results=[],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )
        assert assessment.warnings_count == 0
        assert assessment.errors_count == 0
        assert assessment.has_warnings is False
        assert assessment.has_errors is False
        assert assessment.is_safe is True

    def test_assessment_counts(self) -> None:
        """Test assessment counts warnings and errors."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test1",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.WARNING,
                    message="Warning 1",
                ),
                SafetyCheckResult(
                    check_id="test2",
                    category=SafetyCategory.STABILITY,
                    status=SafetyCheckStatus.WARNING,
                    message="Warning 2",
                ),
                SafetyCheckResult(
                    check_id="test3",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.ERROR,
                    message="Error 1",
                ),
                SafetyCheckResult(
                    check_id="test4",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Pass 1",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        assert assessment.warnings_count == 2
        assert assessment.errors_count == 1
        assert assessment.has_warnings is True
        assert assessment.has_errors is True
        assert assessment.is_safe is False

    def test_is_safe_with_warnings_only(self) -> None:
        """Test is_safe is True when only warnings (no errors)."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test",
                    category=SafetyCategory.MATERIAL,
                    status=SafetyCheckStatus.WARNING,
                    message="Material warning",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        assert assessment.has_warnings is True
        assert assessment.has_errors is False
        assert assessment.is_safe is True

    def test_summary_passed(self) -> None:
        """Test summary for passed assessment."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Passed",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        assert "PASSED: All safety checks passed" in assessment.summary

    def test_summary_passed_with_warnings(self) -> None:
        """Test summary for passed assessment with warnings."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test",
                    category=SafetyCategory.MATERIAL,
                    status=SafetyCheckStatus.WARNING,
                    message="Warning",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        assert "PASSED with 1 warning(s)" in assessment.summary

    def test_summary_failed(self) -> None:
        """Test summary for failed assessment."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="test",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.ERROR,
                    message="Error",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        assert "FAILED: 1 error(s)" in assessment.summary

    def test_get_results_by_category(self) -> None:
        """Test filtering results by category."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="structural_1",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Structural pass",
                ),
                SafetyCheckResult(
                    check_id="structural_2",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.WARNING,
                    message="Structural warning",
                ),
                SafetyCheckResult(
                    check_id="stability",
                    category=SafetyCategory.STABILITY,
                    status=SafetyCheckStatus.WARNING,
                    message="Stability warning",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        structural = assessment.get_results_by_category(SafetyCategory.STRUCTURAL)
        assert len(structural) == 2

        stability = assessment.get_results_by_category(SafetyCategory.STABILITY)
        assert len(stability) == 1

        clearance = assessment.get_results_by_category(SafetyCategory.CLEARANCE)
        assert len(clearance) == 0

    def test_get_errors(self) -> None:
        """Test get_errors method."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="pass",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Pass",
                ),
                SafetyCheckResult(
                    check_id="error1",
                    category=SafetyCategory.CLEARANCE,
                    status=SafetyCheckStatus.ERROR,
                    message="Error 1",
                ),
                SafetyCheckResult(
                    check_id="error2",
                    category=SafetyCategory.ACCESSIBILITY,
                    status=SafetyCheckStatus.ERROR,
                    message="Error 2",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        errors = assessment.get_errors()
        assert len(errors) == 2
        assert all(e.status == SafetyCheckStatus.ERROR for e in errors)

    def test_get_warnings(self) -> None:
        """Test get_warnings method."""
        assessment = SafetyAssessment(
            check_results=[
                SafetyCheckResult(
                    check_id="pass",
                    category=SafetyCategory.STRUCTURAL,
                    status=SafetyCheckStatus.PASS,
                    message="Pass",
                ),
                SafetyCheckResult(
                    check_id="warning",
                    category=SafetyCategory.MATERIAL,
                    status=SafetyCheckStatus.WARNING,
                    message="Warning",
                ),
            ],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        warnings = assessment.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].check_id == "warning"


# ==============================================================================
# SafetyLabel Tests
# ==============================================================================


class TestSafetyLabel:
    """Test SafetyLabel dataclass."""

    def test_valid_label(self) -> None:
        """Test creating valid label."""
        label = SafetyLabel(
            label_type="weight_capacity",
            title="Test Title",
            body_text="Test body",
            dimensions=(4.0, 3.0),
        )
        assert label.label_type == "weight_capacity"
        assert label.title == "Test Title"
        assert label.body_text == "Test body"
        assert label.warning_icon is False
        assert label.dimensions == (4.0, 3.0)

    def test_label_with_warning_icon(self) -> None:
        """Test label with warning icon."""
        label = SafetyLabel(
            label_type="anti_tip",
            title="Warning",
            body_text="Danger",
            warning_icon=True,
        )
        assert label.warning_icon is True

    def test_valid_label_types(self) -> None:
        """Test all valid label types are accepted."""
        valid_types = ["weight_capacity", "anti_tip", "installation", "material"]
        for label_type in valid_types:
            label = SafetyLabel(
                label_type=label_type,
                title="Test",
                body_text="Test",
            )
            assert label.label_type == label_type

    def test_invalid_label_type_raises(self) -> None:
        """Test invalid label type raises error."""
        with pytest.raises(ValueError, match="label_type"):
            SafetyLabel(
                label_type="invalid_type",
                title="Test",
                body_text="Test",
            )

    def test_empty_title_raises(self) -> None:
        """Test empty title raises error."""
        with pytest.raises(ValueError, match="title"):
            SafetyLabel(
                label_type="weight_capacity",
                title="",
                body_text="Test",
            )

    def test_empty_body_raises(self) -> None:
        """Test empty body_text raises error."""
        with pytest.raises(ValueError, match="body_text"):
            SafetyLabel(
                label_type="weight_capacity",
                title="Test",
                body_text="",
            )

    def test_invalid_dimensions_raises(self) -> None:
        """Test invalid dimensions raises error."""
        with pytest.raises(ValueError, match="dimensions"):
            SafetyLabel(
                label_type="weight_capacity",
                title="Test",
                body_text="Test",
                dimensions=(0, 3.0),
            )
        with pytest.raises(ValueError, match="dimensions"):
            SafetyLabel(
                label_type="weight_capacity",
                title="Test",
                body_text="Test",
                dimensions=(4.0, -1.0),
            )

    def test_width_inches_property(self) -> None:
        """Test width_inches property."""
        label = SafetyLabel(
            label_type="weight_capacity",
            title="Test",
            body_text="Test",
            dimensions=(5.0, 3.0),
        )
        assert label.width_inches == 5.0

    def test_height_inches_property(self) -> None:
        """Test height_inches property."""
        label = SafetyLabel(
            label_type="weight_capacity",
            title="Test",
            body_text="Test",
            dimensions=(5.0, 3.0),
        )
        assert label.height_inches == 3.0

    def test_default_dimensions(self) -> None:
        """Test default dimensions are 4x3 inches."""
        label = SafetyLabel(
            label_type="weight_capacity",
            title="Test",
            body_text="Test",
        )
        assert label.dimensions == (4.0, 3.0)


# ==============================================================================
# AccessibilityReport Tests
# ==============================================================================


class TestAccessibilityReport:
    """Test AccessibilityReport dataclass."""

    def test_create_valid_report(self) -> None:
        """Test creating a valid accessibility report."""
        report = AccessibilityReport(
            total_storage_volume=1000.0,
            accessible_storage_volume=600.0,
            accessible_percentage=60.0,
            is_compliant=True,
            non_compliant_areas=(),
            reach_violations=(),
            hardware_notes=(),
        )
        assert report.total_storage_volume == 1000.0
        assert report.accessible_storage_volume == 600.0
        assert report.accessible_percentage == 60.0
        assert report.is_compliant is True
        assert report.standard == ADAStandard.ADA_2010  # default

    def test_formatted_summary_compliant(self) -> None:
        """Test formatted summary for compliant report."""
        report = AccessibilityReport(
            total_storage_volume=1000.0,
            accessible_storage_volume=600.0,
            accessible_percentage=60.0,
            is_compliant=True,
            non_compliant_areas=(),
            reach_violations=(),
            hardware_notes=(),
        )
        assert "COMPLIANT" in report.formatted_summary
        assert "60.0%" in report.formatted_summary

    def test_formatted_summary_non_compliant(self) -> None:
        """Test formatted summary for non-compliant report."""
        report = AccessibilityReport(
            total_storage_volume=1000.0,
            accessible_storage_volume=400.0,
            accessible_percentage=40.0,
            is_compliant=False,
            non_compliant_areas=("Area 1",),
            reach_violations=("Violation 1",),
            hardware_notes=(),
        )
        assert "NON-COMPLIANT" in report.formatted_summary
        assert "40.0%" in report.formatted_summary

    def test_negative_volume_raises(self) -> None:
        """Test negative total_storage_volume raises error."""
        with pytest.raises(ValueError, match="non-negative"):
            AccessibilityReport(
                total_storage_volume=-100.0,
                accessible_storage_volume=0.0,
                accessible_percentage=0.0,
                is_compliant=True,
                non_compliant_areas=(),
                reach_violations=(),
                hardware_notes=(),
            )

    def test_negative_accessible_volume_raises(self) -> None:
        """Test negative accessible_storage_volume raises error."""
        with pytest.raises(ValueError, match="non-negative"):
            AccessibilityReport(
                total_storage_volume=100.0,
                accessible_storage_volume=-10.0,
                accessible_percentage=0.0,
                is_compliant=True,
                non_compliant_areas=(),
                reach_violations=(),
                hardware_notes=(),
            )

    def test_percentage_above_100_raises(self) -> None:
        """Test percentage > 100 raises error."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            AccessibilityReport(
                total_storage_volume=100.0,
                accessible_storage_volume=100.0,
                accessible_percentage=150.0,
                is_compliant=True,
                non_compliant_areas=(),
                reach_violations=(),
                hardware_notes=(),
            )

    def test_percentage_below_zero_raises(self) -> None:
        """Test percentage < 0 raises error."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            AccessibilityReport(
                total_storage_volume=100.0,
                accessible_storage_volume=0.0,
                accessible_percentage=-10.0,
                is_compliant=False,
                non_compliant_areas=(),
                reach_violations=(),
                hardware_notes=(),
            )


# ==============================================================================
# Material Compliance Tests
# ==============================================================================


class TestMaterialCompliance:
    """Test material certification compliance checking."""

    def test_unknown_certification_warning(self) -> None:
        """Test unknown certification produces warning."""
        service = SafetyService(
            SafetyConfig(material_certification=MaterialCertification.UNKNOWN)
        )
        result = service.check_material_compliance()

        assert result.status == SafetyCheckStatus.WARNING
        assert result.category == SafetyCategory.MATERIAL
        assert "not specified" in result.message.lower()
        assert result.remediation is not None
        assert "CARB Phase 2" in result.remediation

    def test_none_certification_error(self) -> None:
        """Test NONE certification produces error."""
        service = SafetyService(
            SafetyConfig(material_certification=MaterialCertification.NONE)
        )
        result = service.check_material_compliance()

        assert result.status == SafetyCheckStatus.ERROR
        assert "non-compliant" in result.message.lower()
        assert result.remediation is not None

    def test_carb_phase2_pass(self) -> None:
        """Test CARB Phase 2 certification passes."""
        service = SafetyService(
            SafetyConfig(material_certification=MaterialCertification.CARB_PHASE2)
        )
        result = service.check_material_compliance()

        assert result.status == SafetyCheckStatus.PASS
        assert "CARB Phase 2" in result.message
        assert "CARB ATCM 93120" in result.standard_reference

    def test_naf_certification_pass(self) -> None:
        """Test NAF (No Added Formaldehyde) certification passes."""
        service = SafetyService(
            SafetyConfig(material_certification=MaterialCertification.NAF)
        )
        result = service.check_material_compliance()

        assert result.status == SafetyCheckStatus.PASS
        assert "No Added Formaldehyde" in result.message or "NAF" in result.message

    def test_ulef_certification_pass(self) -> None:
        """Test ULEF (Ultra-Low Emitting Formaldehyde) certification passes."""
        service = SafetyService(
            SafetyConfig(material_certification=MaterialCertification.ULEF)
        )
        result = service.check_material_compliance()

        assert result.status == SafetyCheckStatus.PASS
        assert "ULEF" in result.message or "Ultra-Low" in result.message


# ==============================================================================
# Seismic Requirements Tests
# ==============================================================================


class TestSeismicRequirements:
    """Test seismic zone requirement checking."""

    def test_no_zone_not_applicable(self) -> None:
        """Test no seismic zone returns NOT_APPLICABLE."""
        service = SafetyService(SafetyConfig(seismic_zone=None))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.NOT_APPLICABLE
        assert result.category == SafetyCategory.SEISMIC
        assert "not specified" in result.message.lower()

    def test_zone_a_passes(self) -> None:
        """Test seismic zone A passes without special requirements."""
        service = SafetyService(SafetyConfig(seismic_zone=SeismicZone.A))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.PASS
        assert "Zone A" in result.message
        assert "Standard anchoring" in result.message

    def test_zone_b_passes(self) -> None:
        """Test seismic zone B passes without special requirements."""
        service = SafetyService(SafetyConfig(seismic_zone=SeismicZone.B))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.PASS

    def test_zone_c_passes(self) -> None:
        """Test seismic zone C passes without special requirements."""
        service = SafetyService(SafetyConfig(seismic_zone=SeismicZone.C))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.PASS

    def test_zone_d_requires_hardware(self) -> None:
        """Test seismic zone D generates warning and requires hardware."""
        service = SafetyService(SafetyConfig(seismic_zone=SeismicZone.D))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.WARNING
        assert "Zone D" in result.message
        assert "enhanced" in result.message.lower()
        assert result.remediation is not None
        assert "seismic-rated" in result.remediation.lower()

    def test_zone_e_requires_hardware(self) -> None:
        """Test seismic zone E generates warning and requires hardware."""
        service = SafetyService(SafetyConfig(seismic_zone=SeismicZone.E))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.WARNING
        assert "Zone E" in result.message

    def test_zone_f_requires_hardware(self) -> None:
        """Test seismic zone F generates warning and requires hardware."""
        service = SafetyService(SafetyConfig(seismic_zone=SeismicZone.F))
        result = service.check_seismic_requirements()

        assert result.status == SafetyCheckStatus.WARNING
        assert "Zone F" in result.message

    def test_seismic_hardware_list_empty_for_low_zones(self) -> None:
        """Test seismic hardware list is empty for zones A-C."""
        for zone in [SeismicZone.A, SeismicZone.B, SeismicZone.C]:
            service = SafetyService(SafetyConfig(seismic_zone=zone))
            hardware = service.get_seismic_hardware()
            assert hardware == []

    def test_seismic_hardware_list_populated_for_high_zones(self) -> None:
        """Test seismic hardware list has items for zones D-F."""
        for zone in [SeismicZone.D, SeismicZone.E, SeismicZone.F]:
            service = SafetyService(SafetyConfig(seismic_zone=zone))
            hardware = service.get_seismic_hardware()
            assert len(hardware) > 0
            assert any("seismic" in h.lower() for h in hardware)


# ==============================================================================
# Safety Constants Tests
# ==============================================================================


class TestSafetyConstants:
    """Test safety-related constants."""

    def test_anti_tip_height_threshold(self) -> None:
        """Test anti-tip threshold is 27 inches per ASTM F2057-23."""
        assert ANTI_TIP_HEIGHT_THRESHOLD == 27.0

    def test_ada_min_reach(self) -> None:
        """Test ADA minimum reach is 15 inches."""
        assert ADA_MIN_REACH == 15.0

    def test_ada_max_reach_unobstructed(self) -> None:
        """Test ADA maximum unobstructed reach is 48 inches."""
        assert ADA_MAX_REACH_UNOBSTRUCTED == 48.0

    def test_ada_min_accessible_percentage(self) -> None:
        """Test ADA minimum accessible storage is 50%."""
        assert ADA_MIN_ACCESSIBLE_PERCENTAGE == 50.0

    def test_nec_panel_clearances(self) -> None:
        """Test NEC 110.26 electrical panel clearances."""
        assert NEC_PANEL_FRONT_CLEARANCE == 36.0
        assert NEC_PANEL_WIDTH_CLEARANCE == 30.0

    def test_heat_source_vertical_clearance(self) -> None:
        """Test heat source vertical clearance is 30 inches."""
        assert HEAT_SOURCE_VERTICAL_CLEARANCE == 30.0

    def test_kcma_shelf_load(self) -> None:
        """Test KCMA standard shelf load is 15 lbs/sq ft."""
        assert KCMA_SHELF_LOAD_PSF == 15.0


# ==============================================================================
# SafetyService Weight Capacity Tests (Task 03)
# ==============================================================================


class TestSafetyServiceWeightCapacity:
    """Test SafetyService weight capacity methods."""

    def make_cabinet_with_shelves(
        self,
        width: float = 48.0,
        height: float = 84.0,
        depth: float = 12.0,
        num_shelves: int = 3,
    ) -> Cabinet:
        """Create a cabinet with shelves for testing."""
        material = MaterialSpec.standard_3_4()
        cabinet = Cabinet(
            width=width,
            height=height,
            depth=depth,
            material=material,
        )

        # Create section with shelves
        section = Section(
            width=width - (2 * material.thickness),
            height=height,
            depth=depth,
            position=Position(material.thickness, 0),
        )

        shelf_width = section.width - (2 * material.thickness)
        shelf_depth = depth - material.thickness

        for _ in range(num_shelves):
            section.add_shelf(
                Shelf(
                    width=shelf_width,
                    depth=shelf_depth,
                    material=material,
                    position=Position(0, 0),
                )
            )

        cabinet.sections.append(section)
        return cabinet

    def test_get_shelf_capacities_returns_list(self) -> None:
        """Test get_shelf_capacities returns capacity list."""
        service = SafetyService(SafetyConfig(safety_factor=4.0))
        cabinet = self.make_cabinet_with_shelves(num_shelves=3)

        capacities = service.get_shelf_capacities(cabinet)

        assert isinstance(capacities, list)
        assert len(capacities) == 3

    def test_get_shelf_capacities_uses_safety_factor(self) -> None:
        """Test capacity calculations use configured safety factor."""
        cabinet = self.make_cabinet_with_shelves(num_shelves=1)

        service_4x = SafetyService(SafetyConfig(safety_factor=4.0))
        service_2x = SafetyService(SafetyConfig(safety_factor=2.0))

        capacities_4x = service_4x.get_shelf_capacities(cabinet)
        capacities_2x = service_2x.get_shelf_capacities(cabinet)

        # 2x safety factor should allow ~2x the load of 4x safety factor
        # (not exact due to rounding)
        assert capacities_2x[0].safe_load_lbs > capacities_4x[0].safe_load_lbs

    def test_get_shelf_capacities_includes_material_info(self) -> None:
        """Test capacity estimates include material information."""
        service = SafetyService(SafetyConfig(safety_factor=4.0))
        cabinet = self.make_cabinet_with_shelves(num_shelves=1)

        capacities = service.get_shelf_capacities(cabinet)

        assert capacities[0].material == "plywood"
        assert capacities[0].safety_factor == 4.0

    def test_get_shelf_capacities_empty_cabinet(self) -> None:
        """Test get_shelf_capacities with no shelves returns empty list."""
        service = SafetyService(SafetyConfig(safety_factor=4.0))
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )

        capacities = service.get_shelf_capacities(cabinet)

        assert capacities == []


# ==============================================================================
# SafetyService Structural Checks Tests
# ==============================================================================


class TestSafetyServiceStructuralChecks:
    """Test SafetyService structural check methods."""

    def make_cabinet_with_shelves(
        self,
        width: float = 48.0,
        height: float = 84.0,
        depth: float = 12.0,
        num_shelves: int = 3,
    ) -> Cabinet:
        """Create a cabinet with shelves for testing."""
        material = MaterialSpec.standard_3_4()
        cabinet = Cabinet(
            width=width,
            height=height,
            depth=depth,
            material=material,
        )

        section = Section(
            width=width - (2 * material.thickness),
            height=height,
            depth=depth,
            position=Position(material.thickness, 0),
        )

        shelf_width = section.width - (2 * material.thickness)
        shelf_depth = depth - material.thickness

        for _ in range(num_shelves):
            section.add_shelf(
                Shelf(
                    width=shelf_width,
                    depth=shelf_depth,
                    material=material,
                    position=Position(0, 0),
                )
            )

        cabinet.sections.append(section)
        return cabinet

    def test_check_structural_safety_no_shelves(self) -> None:
        """Test structural check with no shelves returns NOT_APPLICABLE."""
        service = SafetyService(SafetyConfig())
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )

        results = service._check_structural_safety(cabinet)

        assert len(results) == 1
        assert results[0].status == SafetyCheckStatus.NOT_APPLICABLE
        assert "No shelves" in results[0].message

    def test_check_structural_safety_with_shelves(self) -> None:
        """Test structural check with shelves returns capacity results."""
        service = SafetyService(SafetyConfig())
        cabinet = self.make_cabinet_with_shelves(num_shelves=2)

        results = service._check_structural_safety(cabinet)

        # Should have results for shelf capacities
        capacity_results = [r for r in results if "weight_capacity" in r.check_id]
        assert len(capacity_results) == 2

    def test_check_structural_safety_categories(self) -> None:
        """Test structural check results have STRUCTURAL category."""
        service = SafetyService(SafetyConfig())
        cabinet = self.make_cabinet_with_shelves(num_shelves=1)

        results = service._check_structural_safety(cabinet)

        for result in results:
            assert result.category == SafetyCategory.STRUCTURAL


# ==============================================================================
# SafetyService Label Generation Tests
# ==============================================================================


class TestSafetyServiceLabelGeneration:
    """Test SafetyService safety label generation."""

    def test_generate_labels_weight_capacity(self) -> None:
        """Test label generation includes weight capacity label."""
        service = SafetyService(SafetyConfig())
        assessment = SafetyAssessment(
            check_results=[],
            weight_capacities=[
                WeightCapacityEstimate(
                    panel_id="shelf_0",
                    safe_load_lbs=45.0,
                    max_deflection_inches=0.18,
                    deflection_at_rated_load=0.045,
                    safety_factor=4.0,
                    material="plywood",
                    span_inches=36.0,
                ),
            ],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        labels = service.generate_safety_labels(assessment)

        weight_labels = [
            label for label in labels if label.label_type == "weight_capacity"
        ]
        assert len(weight_labels) == 1
        assert "45 lbs" in weight_labels[0].body_text
        assert weight_labels[0].warning_icon is True

    def test_generate_labels_anti_tip(self) -> None:
        """Test label generation includes anti-tip label when required."""
        service = SafetyService(SafetyConfig())
        assessment = SafetyAssessment(
            check_results=[],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=True,
            seismic_hardware=[],
        )

        labels = service.generate_safety_labels(assessment)

        anti_tip_labels = [label for label in labels if label.label_type == "anti_tip"]
        assert len(anti_tip_labels) == 1
        assert "TIP-OVER HAZARD" in anti_tip_labels[0].title
        assert anti_tip_labels[0].warning_icon is True

    def test_generate_labels_always_includes_installation(self) -> None:
        """Test label generation always includes installation label."""
        service = SafetyService(SafetyConfig())
        assessment = SafetyAssessment(
            check_results=[],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        labels = service.generate_safety_labels(assessment)

        installation_labels = [
            label for label in labels if label.label_type == "installation"
        ]
        assert len(installation_labels) == 1
        assert "INSTALLATION SAFETY" in installation_labels[0].title

    def test_generate_labels_no_anti_tip_when_not_required(self) -> None:
        """Test no anti-tip label when not required."""
        service = SafetyService(SafetyConfig())
        assessment = SafetyAssessment(
            check_results=[],
            weight_capacities=[],
            accessibility_report=None,
            safety_labels=[],
            anti_tip_required=False,
            seismic_hardware=[],
        )

        labels = service.generate_safety_labels(assessment)

        anti_tip_labels = [label for label in labels if label.label_type == "anti_tip"]
        assert len(anti_tip_labels) == 0
