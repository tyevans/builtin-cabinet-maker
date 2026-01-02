"""Unit tests for anti-tip identification per ASTM F2057-23.

Tests the SafetyService anti-tip functionality including:
- check_anti_tip_requirement() method
- get_anti_tip_hardware() helper
- _check_stability() helper
- Wall-mounted exemption detection
- Child safety mode integration
"""

from cabinets.domain.entities import Cabinet
from cabinets.domain.services.safety import (
    ANTI_TIP_HEIGHT_THRESHOLD,
    SafetyCategory,
    SafetyCheckStatus,
    SafetyConfig,
    SafetyService,
)
from cabinets.domain.value_objects import MaterialSpec


def make_cabinet(
    width: float = 36.0,
    height: float = 60.0,
    depth: float = 12.0,
) -> Cabinet:
    """Create a test cabinet with specified dimensions."""
    return Cabinet(
        width=width,
        height=height,
        depth=depth,
        material=MaterialSpec.standard_3_4(),
    )


class TestAntiTipThreshold:
    """Tests for the 27-inch anti-tip height threshold."""

    def test_threshold_constant_is_27_inches(self) -> None:
        """ASTM F2057-23 threshold is 27 inches."""
        assert ANTI_TIP_HEIGHT_THRESHOLD == 27.0

    def test_cabinet_below_threshold_no_anti_tip_required(self) -> None:
        """24-inch cabinet does not require anti-tip."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=24.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert "not required" in result.message.lower()
        assert result.details["anti_tip_required"] is False

    def test_cabinet_at_threshold_requires_anti_tip(self) -> None:
        """Exactly 27-inch cabinet requires anti-tip per ASTM F2057-23.

        Per ASTM F2057-23, units >= 27" tall require anti-tip restraint.
        Exactly 27" is at the threshold and should require anti-tip.
        """
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=27.0)

        result = service.check_anti_tip_requirement(cabinet)

        # At exactly the threshold (27"), cabinet requires anti-tip
        # because the check is `height < threshold` for pass
        assert result.status == SafetyCheckStatus.WARNING
        assert result.details["anti_tip_required"] is True

    def test_cabinet_above_threshold_requires_anti_tip(self) -> None:
        """28-inch cabinet requires anti-tip restraint."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=28.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.WARNING
        assert "required" in result.message.lower()
        assert result.details["anti_tip_required"] is True


class TestAntiTipRequirementResults:
    """Tests for anti-tip check result content."""

    def test_tall_cabinet_returns_warning_status(self) -> None:
        """60-inch tall cabinet returns WARNING status."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.WARNING

    def test_result_includes_correct_category(self) -> None:
        """Result category is STABILITY."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert result.category == SafetyCategory.STABILITY

    def test_result_includes_astm_standard_reference(self) -> None:
        """Result references ASTM F2057-23 standard."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert "ASTM F2057-23" in result.standard_reference

    def test_result_includes_warning_text(self) -> None:
        """Result includes required warning text per ASTM F2057-23."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(cabinet)

        # Check for key warning text components
        assert result.remediation is not None
        assert (
            "anchored to the wall" in result.remediation.lower()
            or "wall" in result.remediation.lower()
        )

    def test_result_includes_height_in_message(self) -> None:
        """Result message includes cabinet height."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert "60.0" in result.message

    def test_result_includes_threshold_in_message(self) -> None:
        """Result message includes threshold height."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert "27" in result.message

    def test_result_details_include_height_to_depth_ratio(self) -> None:
        """Result details include calculated height-to-depth ratio."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0, depth=12.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert "height_to_depth_ratio" in result.details
        assert result.details["height_to_depth_ratio"] == 5.0

    def test_result_details_include_risk_level(self) -> None:
        """Result details include risk level based on ratio."""
        config = SafetyConfig()
        service = SafetyService(config)

        # High risk: ratio > 4
        cabinet_high_risk = make_cabinet(height=60.0, depth=10.0)  # ratio = 6.0
        result_high = service.check_anti_tip_requirement(cabinet_high_risk)
        assert result_high.details["risk_level"] == "high"

        # Moderate risk: ratio <= 4
        cabinet_mod_risk = make_cabinet(height=60.0, depth=20.0)  # ratio = 3.0
        result_mod = service.check_anti_tip_requirement(cabinet_mod_risk)
        assert result_mod.details["risk_level"] == "moderate"


class TestShortCabinetPassing:
    """Tests for cabinets that pass anti-tip check."""

    def test_short_cabinet_passes(self) -> None:
        """24-inch cabinet passes anti-tip check."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=24.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert "not required" in result.message.lower()

    def test_short_cabinet_details_show_not_required(self) -> None:
        """Short cabinet details show anti_tip_required=False."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=24.0)

        result = service.check_anti_tip_requirement(cabinet)

        assert result.details["anti_tip_required"] is False
        assert result.details["height"] == 24.0


class TestWallMountedExemption:
    """Tests for wall-mounted cabinet exemption."""

    def test_wall_mounted_cabinet_exempt(self) -> None:
        """Wall-mounted 60-inch cabinet does not require anti-tip."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        # Simulate wall-mounted by adding wall_index attribute
        cabinet.wall_index = 0  # type: ignore[attr-defined]

        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert "wall-mounted" in result.message.lower()
        assert result.details["is_wall_mounted"] is True

    def test_builtin_cabinet_exempt(self) -> None:
        """Built-in 60-inch cabinet does not require anti-tip."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        # Simulate built-in by adding is_builtin attribute
        cabinet.is_builtin = True  # type: ignore[attr-defined]

        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert result.details["is_wall_mounted"] is True

    def test_freestanding_cabinet_not_exempt(self) -> None:
        """Freestanding 60-inch cabinet requires anti-tip."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        # No wall_index or is_builtin attribute - freestanding
        result = service.check_anti_tip_requirement(cabinet)

        assert result.status == SafetyCheckStatus.WARNING
        assert result.details["is_wall_mounted"] is False


class TestAntiTipHardware:
    """Tests for anti-tip hardware recommendations."""

    def test_short_cabinet_no_hardware(self) -> None:
        """24-inch cabinet gets no anti-tip hardware."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=24.0)

        hardware = service.get_anti_tip_hardware(cabinet)

        assert hardware == []

    def test_tall_cabinet_gets_hardware(self) -> None:
        """60-inch cabinet gets anti-tip hardware list."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        hardware = service.get_anti_tip_hardware(cabinet)

        assert len(hardware) > 0

    def test_hardware_includes_strap_kit(self) -> None:
        """Hardware list includes anti-tip strap kit."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        hardware = service.get_anti_tip_hardware(cabinet)

        assert any("strap" in h.lower() for h in hardware)
        assert any("qty: 1" in h.lower() for h in hardware)

    def test_hardware_includes_mounting_position(self) -> None:
        """Hardware list includes mounting position guidance."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        hardware = service.get_anti_tip_hardware(cabinet)

        assert any("4 inches from top" in h.lower() for h in hardware)

    def test_very_tall_cabinet_extra_hardware(self) -> None:
        """84-inch cabinet gets additional hardware recommendations."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=84.0)

        hardware = service.get_anti_tip_hardware(cabinet)

        # Should have L-bracket recommendation for units >= 72"
        assert any("l-bracket" in h.lower() for h in hardware)

    def test_wall_mounted_no_hardware(self) -> None:
        """Wall-mounted cabinet gets no anti-tip hardware."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)
        cabinet.wall_index = 0  # type: ignore[attr-defined]

        hardware = service.get_anti_tip_hardware(cabinet)

        assert hardware == []


class TestStabilityChecks:
    """Tests for _check_stability() comprehensive checks."""

    def test_stability_includes_anti_tip_check(self) -> None:
        """Stability check includes anti-tip result."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        results = service._check_stability(cabinet)

        anti_tip_results = [r for r in results if r.check_id == "anti_tip_requirement"]
        assert len(anti_tip_results) == 1

    def test_high_ratio_adds_stability_warning(self) -> None:
        """Height-to-depth ratio > 5 adds stability warning."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=72.0, depth=10.0)  # ratio = 7.2

        results = service._check_stability(cabinet)

        ratio_results = [r for r in results if r.check_id == "stability_ratio"]
        assert len(ratio_results) == 1
        assert ratio_results[0].status == SafetyCheckStatus.WARNING
        assert "high tip-over risk" in ratio_results[0].message.lower()

    def test_moderate_ratio_passes(self) -> None:
        """Height-to-depth ratio between 3-5 passes with info."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=48.0, depth=12.0)  # ratio = 4.0

        results = service._check_stability(cabinet)

        ratio_results = [r for r in results if r.check_id == "stability_ratio"]
        assert len(ratio_results) == 1
        assert ratio_results[0].status == SafetyCheckStatus.PASS

    def test_low_ratio_no_extra_check(self) -> None:
        """Height-to-depth ratio <= 3 has no stability_ratio result."""
        config = SafetyConfig()
        service = SafetyService(config)
        cabinet = make_cabinet(height=36.0, depth=12.0)  # ratio = 3.0

        results = service._check_stability(cabinet)

        ratio_results = [r for r in results if r.check_id == "stability_ratio"]
        # Ratio of exactly 3 should not trigger (condition is > 3)
        assert len(ratio_results) == 0


class TestChildSafetyMode:
    """Tests for child safety mode anti-tip integration."""

    def test_child_safe_mode_adds_warning(self) -> None:
        """Child safe mode adds extra tip-over warning."""
        config = SafetyConfig(child_safe_mode=True)
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        results = service._check_stability(cabinet)

        child_results = [
            r for r in results if r.category == SafetyCategory.CHILD_SAFETY
        ]
        assert len(child_results) > 0

    def test_child_safe_mode_warning_content(self) -> None:
        """Child safety warning includes appropriate content."""
        config = SafetyConfig(child_safe_mode=True)
        service = SafetyService(config)
        cabinet = make_cabinet(height=60.0)

        results = service._check_stability(cabinet)

        child_results = [
            r for r in results if r.category == SafetyCategory.CHILD_SAFETY
        ]
        assert len(child_results) == 1

        result = child_results[0]
        assert "child" in result.message.lower()
        assert result.standard_reference == "CPSC Safety Alert"

    def test_child_safe_mode_short_cabinet_no_warning(self) -> None:
        """Child safe mode does not warn for short cabinets."""
        config = SafetyConfig(child_safe_mode=True)
        service = SafetyService(config)
        cabinet = make_cabinet(height=24.0)

        results = service._check_stability(cabinet)

        child_results = [
            r for r in results if r.category == SafetyCategory.CHILD_SAFETY
        ]
        assert len(child_results) == 0


class TestSuccessCriteriaFromTask:
    """Tests matching the success criteria from task-04-anti-tip.md."""

    def test_anti_tip_required_for_tall_freestanding_units(self) -> None:
        """Success Criteria 1: 60" tall cabinet above threshold."""
        config = SafetyConfig()
        service = SafetyService(config)
        # Create a tall cabinet (not wall-mounted)
        tall_cabinet = make_cabinet(height=60.0)

        result = service.check_anti_tip_requirement(tall_cabinet)

        assert result.status == SafetyCheckStatus.WARNING
        assert "required" in result.message.lower()

    def test_anti_tip_not_required_for_short_units(self) -> None:
        """Success Criteria 2: 24" tall cabinet below threshold."""
        config = SafetyConfig()
        service = SafetyService(config)
        short_cabinet = make_cabinet(height=24.0)

        result = service.check_anti_tip_requirement(short_cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert "not required" in result.message.lower()

    def test_wall_mounted_units_exempt_from_anti_tip(self) -> None:
        """Success Criteria 3: 60" tall but wall-mounted."""
        config = SafetyConfig()
        service = SafetyService(config)
        wall_mounted_cabinet = make_cabinet(height=60.0)
        wall_mounted_cabinet.wall_index = 0  # type: ignore[attr-defined]

        result = service.check_anti_tip_requirement(wall_mounted_cabinet)

        assert result.status == SafetyCheckStatus.PASS
        assert "wall-mounted" in result.message.lower()

    def test_anti_tip_hardware_list_generated(self) -> None:
        """Success Criteria 4: Hardware list for tall cabinet."""
        config = SafetyConfig()
        service = SafetyService(config)
        tall_cabinet = make_cabinet(height=60.0)

        hardware = service.get_anti_tip_hardware(tall_cabinet)

        assert len(hardware) > 0
        assert any("strap" in h.lower() for h in hardware)

    def test_child_safety_mode_adds_extra_warnings(self) -> None:
        """Success Criteria 5: Child safety mode adds extra warnings."""
        config = SafetyConfig(child_safe_mode=True)
        service = SafetyService(config)
        tall_cabinet = make_cabinet(height=60.0)

        results = service._check_stability(tall_cabinet)

        child_warnings = [
            r for r in results if r.category == SafetyCategory.CHILD_SAFETY
        ]
        assert len(child_warnings) > 0
