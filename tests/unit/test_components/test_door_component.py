"""Tests for door component implementations.

Tests for OverlayDoorComponent, InsetDoorComponent, PartialOverlayDoorComponent,
HingeSpec, HingePlateSpec, HandlePositionSpec, and related functions.
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    HardwareItem,
    ValidationResult,
    component_registry,
)
from cabinets.domain.components.door import (
    HandlePositionSpec,
    HingePlateSpec,
    HingeSpec,
    InsetDoorComponent,
    MM_TO_INCH,
    OverlayDoorComponent,
    PartialOverlayDoorComponent,
    _calculate_hinge_count,
    _calculate_hinge_positions,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def overlay_component() -> OverlayDoorComponent:
    """Create an OverlayDoorComponent instance for testing."""
    return OverlayDoorComponent()


@pytest.fixture
def inset_component() -> InsetDoorComponent:
    """Create an InsetDoorComponent instance for testing."""
    return InsetDoorComponent()


@pytest.fixture
def partial_component() -> PartialOverlayDoorComponent:
    """Create a PartialOverlayDoorComponent instance for testing."""
    return PartialOverlayDoorComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 24" wide x 30" high section
    at position (0.75, 0.75) within a 48x84x12 cabinet.
    """
    return ComponentContext(
        width=24.0,
        height=30.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


# =============================================================================
# Registration Tests
# =============================================================================


class TestDoorComponentRegistration:
    """Tests for door component registration in the registry."""

    @pytest.fixture(autouse=True)
    def ensure_doors_registered(self) -> None:
        """Ensure door components are registered for each test."""
        if "door.hinged.overlay" not in component_registry.list():
            component_registry.register("door.hinged.overlay")(OverlayDoorComponent)
        if "door.hinged.inset" not in component_registry.list():
            component_registry.register("door.hinged.inset")(InsetDoorComponent)
        if "door.hinged.partial" not in component_registry.list():
            component_registry.register("door.hinged.partial")(PartialOverlayDoorComponent)

    def test_overlay_door_is_registered(self) -> None:
        """Test that door.hinged.overlay is registered in the component registry."""
        assert "door.hinged.overlay" in component_registry.list()

    def test_inset_door_is_registered(self) -> None:
        """Test that door.hinged.inset is registered in the component registry."""
        assert "door.hinged.inset" in component_registry.list()

    def test_partial_door_is_registered(self) -> None:
        """Test that door.hinged.partial is registered in the component registry."""
        assert "door.hinged.partial" in component_registry.list()

    def test_get_returns_overlay_door_component_class(self) -> None:
        """Test that registry.get returns OverlayDoorComponent."""
        component_class = component_registry.get("door.hinged.overlay")
        assert component_class is OverlayDoorComponent

    def test_get_returns_inset_door_component_class(self) -> None:
        """Test that registry.get returns InsetDoorComponent."""
        component_class = component_registry.get("door.hinged.inset")
        assert component_class is InsetDoorComponent

    def test_get_returns_partial_door_component_class(self) -> None:
        """Test that registry.get returns PartialOverlayDoorComponent."""
        component_class = component_registry.get("door.hinged.partial")
        assert component_class is PartialOverlayDoorComponent


# =============================================================================
# Overlay Door Validation Tests
# =============================================================================


class TestOverlayDoorValidation:
    """Tests for OverlayDoorComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid single door config."""
        config = {"count": 1, "hinge_side": "left"}

        result = overlay_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_double_doors(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid double door config."""
        config = {"count": 2}

        result = overlay_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_error_for_count_zero(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for count of 0."""
        config = {"count": 0}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Door count must be 1 or 2" in result.errors

    def test_validate_returns_error_for_count_three(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for count of 3."""
        config = {"count": 3}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Door count must be 1 or 2" in result.errors

    def test_validate_returns_error_for_invalid_hinge_side_single_door(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for invalid hinge_side on single door."""
        config = {"count": 1, "hinge_side": "top"}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "hinge_side must be 'left' or 'right'" in result.errors

    def test_validate_accepts_left_hinge_side(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate accepts 'left' hinge_side."""
        config = {"count": 1, "hinge_side": "left"}

        result = overlay_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_accepts_right_hinge_side(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate accepts 'right' hinge_side."""
        config = {"count": 1, "hinge_side": "right"}

        result = overlay_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_reveal_zero(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for reveal of 0."""
        config = {"count": 1, "reveal": 0}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Reveal must be between 0 and 0.5 inches" in result.errors

    def test_validate_returns_error_for_reveal_negative(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for negative reveal."""
        config = {"count": 1, "reveal": -0.1}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Reveal must be between 0 and 0.5 inches" in result.errors

    def test_validate_returns_error_for_reveal_at_half_inch(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for reveal of exactly 0.5."""
        config = {"count": 1, "reveal": 0.5}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Reveal must be between 0 and 0.5 inches" in result.errors

    def test_validate_returns_error_for_reveal_above_half_inch(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for reveal > 0.5."""
        config = {"count": 1, "reveal": 0.6}

        result = overlay_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Reveal must be between 0 and 0.5 inches" in result.errors

    def test_validate_accepts_reveal_just_under_half_inch(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate accepts reveal of 0.499."""
        config = {"count": 1, "reveal": 0.499}

        result = overlay_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_section_height_below_6_inches(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that validate returns error for section height < 6\"."""
        short_context = ComponentContext(
            width=24.0,
            height=5.0,  # Too short
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        result = overlay_component.validate(config, short_context)

        assert not result.is_valid
        assert "Section height must be at least 6 inches" in result.errors

    def test_validate_accepts_section_height_exactly_6_inches(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that validate accepts section height of exactly 6\"."""
        context = ComponentContext(
            width=24.0,
            height=6.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        result = overlay_component.validate(config, context)

        assert result.is_valid

    def test_validate_returns_error_for_section_width_below_6_inches(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that validate returns error for section width < 6\"."""
        narrow_context = ComponentContext(
            width=5.0,  # Too narrow
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        result = overlay_component.validate(config, narrow_context)

        assert not result.is_valid
        assert "Section width must be at least 6 inches" in result.errors

    def test_validate_returns_error_for_double_door_width_below_12_inches(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that validate returns error for double doors with width < 12\"."""
        context = ComponentContext(
            width=10.0,  # Wide enough for single, not for double
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 2}

        result = overlay_component.validate(config, context)

        assert not result.is_valid
        assert "Double doors require section width >= 12 inches" in result.errors

    def test_validate_accepts_double_door_width_exactly_12_inches(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that validate accepts double doors with width of exactly 12\"."""
        context = ComponentContext(
            width=12.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 2}

        result = overlay_component.validate(config, context)

        assert result.is_valid

    def test_validate_returns_warning_for_door_height_exceeding_60_inches(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that validate returns warning for door height > 60\"."""
        tall_context = ComponentContext(
            width=24.0,
            height=65.0,  # Tall section
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        result = overlay_component.validate(config, tall_context)

        assert result.is_valid  # Warning only, still valid
        assert len(result.warnings) == 1
        assert "exceeds 60\"" in result.warnings[0]
        assert "consider weight" in result.warnings[0]


# =============================================================================
# Inset Door Validation Tests
# =============================================================================


class TestInsetDoorValidation:
    """Tests for InsetDoorComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, inset_component: InsetDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid inset door config."""
        config = {"count": 1, "hinge_side": "right"}

        result = inset_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_error_for_invalid_count(
        self, inset_component: InsetDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for invalid count."""
        config = {"count": 0}

        result = inset_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Door count must be 1 or 2" in result.errors

    def test_validate_returns_error_for_invalid_reveal(
        self, inset_component: InsetDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for invalid reveal."""
        config = {"count": 1, "reveal": 0.5}

        result = inset_component.validate(config, standard_context)

        assert not result.is_valid


# =============================================================================
# Partial Overlay Door Validation Tests
# =============================================================================


class TestPartialOverlayDoorValidation:
    """Tests for PartialOverlayDoorComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, partial_component: PartialOverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid partial overlay door config."""
        config = {"count": 1, "hinge_side": "left"}

        result = partial_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_error_for_invalid_count(
        self, partial_component: PartialOverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for invalid count."""
        config = {"count": 3}

        result = partial_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Door count must be 1 or 2" in result.errors


# =============================================================================
# Overlay Door Generation Tests
# =============================================================================


class TestOverlayDoorGeneration:
    """Tests for OverlayDoorComponent.generate()."""

    def test_generate_single_door_sizing(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test single overlay door sizing: width = section_width + (2 * overlay) - reveal."""
        config = {"count": 1, "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        # Expected: 24.0 + (2 * 0.5) - 0.125 = 24.875
        expected_width = 24.0 + (2 * 0.5) - 0.125
        assert len(result.panels) == 1
        assert result.panels[0].width == pytest.approx(expected_width)

    def test_generate_single_door_height(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test single overlay door height sizing."""
        config = {"count": 1, "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        # Expected: 30.0 + (2 * 0.5) - 0.125 = 30.875
        expected_height = 30.0 + (2 * 0.5) - 0.125
        assert result.panels[0].height == pytest.approx(expected_height)

    def test_generate_double_door_creates_two_panels(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that double doors create two panels."""
        config = {"count": 2}

        result = overlay_component.generate(config, standard_context)

        assert len(result.panels) == 2

    def test_generate_double_door_sizing(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test double overlay door sizing with center gap."""
        config = {"count": 2, "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        # Total width: 24.0 + (2 * 0.5) - 0.125 = 24.875
        # Center gap: 0.125 (reveal)
        # Single door width: (24.875 - 0.125) / 2 = 12.375
        total_width = 24.0 + (2 * 0.5) - 0.125
        center_gap = 0.125
        expected_single_width = (total_width - center_gap) / 2

        for panel in result.panels:
            assert panel.width == pytest.approx(expected_single_width)

    def test_generate_panel_type_is_door(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated panels are of type DOOR."""
        config = {"count": 1}

        result = overlay_component.generate(config, standard_context)

        assert result.panels[0].panel_type == PanelType.DOOR

    def test_generate_single_door_position(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that single door is positioned at context position."""
        config = {"count": 1}

        result = overlay_component.generate(config, standard_context)

        assert result.panels[0].position.x == standard_context.position.x
        assert result.panels[0].position.y == standard_context.position.y

    def test_generate_double_door_left_position(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that left door is positioned at context position."""
        config = {"count": 2}

        result = overlay_component.generate(config, standard_context)

        assert result.panels[0].position.x == standard_context.position.x
        assert result.panels[0].position.y == standard_context.position.y

    def test_generate_double_door_right_position(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that right door is positioned with offset for left door and gap."""
        config = {"count": 2, "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        left_door_width = result.panels[0].width
        center_gap = 0.125
        expected_right_x = standard_context.position.x + left_door_width + center_gap

        assert result.panels[1].position.x == pytest.approx(expected_right_x)

    def test_generate_returns_generation_result(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"count": 1}

        result = overlay_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)


# =============================================================================
# Inset Door Generation Tests
# =============================================================================


class TestInsetDoorGeneration:
    """Tests for InsetDoorComponent.generate()."""

    def test_generate_inset_door_width(
        self, inset_component: InsetDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test inset door sizing: width = section_width - (2 * reveal)."""
        config = {"count": 1, "reveal": 0.125}

        result = inset_component.generate(config, standard_context)

        # Expected: 24.0 - (2 * 0.125) = 23.75
        expected_width = 24.0 - (2 * 0.125)
        assert result.panels[0].width == pytest.approx(expected_width)

    def test_generate_inset_door_height(
        self, inset_component: InsetDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test inset door height sizing."""
        config = {"count": 1, "reveal": 0.125}

        result = inset_component.generate(config, standard_context)

        # Expected: 30.0 - (2 * 0.125) = 29.75
        expected_height = 30.0 - (2 * 0.125)
        assert result.panels[0].height == pytest.approx(expected_height)

    def test_generate_inset_ignores_overlay(
        self, inset_component: InsetDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that inset door ignores overlay parameter."""
        config_with_overlay = {"count": 1, "reveal": 0.125, "overlay": 1.0}
        config_without_overlay = {"count": 1, "reveal": 0.125}

        result_with = inset_component.generate(config_with_overlay, standard_context)
        result_without = inset_component.generate(config_without_overlay, standard_context)

        assert result_with.panels[0].width == result_without.panels[0].width
        assert result_with.panels[0].height == result_without.panels[0].height


# =============================================================================
# Partial Overlay Door Generation Tests
# =============================================================================


class TestPartialOverlayDoorGeneration:
    """Tests for PartialOverlayDoorComponent.generate()."""

    def test_generate_partial_overlay_door_uses_half_overlay(
        self, partial_component: PartialOverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test partial overlay uses overlay/2 for sizing."""
        config = {"count": 1, "overlay": 0.5, "reveal": 0.125}

        result = partial_component.generate(config, standard_context)

        # Partial overlay = 0.5 / 2 = 0.25
        # Expected width: 24.0 + (2 * 0.25) - 0.125 = 24.375
        expected_width = 24.0 + (2 * 0.25) - 0.125
        assert result.panels[0].width == pytest.approx(expected_width)

    def test_generate_partial_overlay_height(
        self, partial_component: PartialOverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test partial overlay door height sizing."""
        config = {"count": 1, "overlay": 0.5, "reveal": 0.125}

        result = partial_component.generate(config, standard_context)

        # Partial overlay = 0.5 / 2 = 0.25
        # Expected height: 30.0 + (2 * 0.25) - 0.125 = 30.375
        expected_height = 30.0 + (2 * 0.25) - 0.125
        assert result.panels[0].height == pytest.approx(expected_height)


# =============================================================================
# Hinge Calculation Tests
# =============================================================================


class TestHingeCalculations:
    """Tests for hinge count and position calculations."""

    def test_hinge_count_under_40_inches_is_2(self) -> None:
        """Test that doors under 40\" use 2 hinges."""
        assert _calculate_hinge_count(39.9) == 2
        assert _calculate_hinge_count(30.0) == 2
        assert _calculate_hinge_count(10.0) == 2

    def test_hinge_count_at_40_inches_is_3(self) -> None:
        """Test that doors at 40\" use 3 hinges."""
        assert _calculate_hinge_count(40.0) == 3

    def test_hinge_count_between_40_and_60_is_3(self) -> None:
        """Test that doors 40-60\" use 3 hinges."""
        assert _calculate_hinge_count(45.0) == 3
        assert _calculate_hinge_count(50.0) == 3
        assert _calculate_hinge_count(60.0) == 3

    def test_hinge_count_over_60_inches_is_4(self) -> None:
        """Test that doors over 60\" use 4 hinges."""
        assert _calculate_hinge_count(60.1) == 4
        assert _calculate_hinge_count(72.0) == 4
        assert _calculate_hinge_count(84.0) == 4

    def test_hinge_positions_2_hinges(self) -> None:
        """Test hinge positions for 2-hinge configuration."""
        # 30" door: 2 hinges at 3" from bottom and 3" from top
        positions = _calculate_hinge_positions(30.0)

        assert len(positions) == 2
        assert positions[0] == pytest.approx(3.0)  # 3" from bottom
        assert positions[1] == pytest.approx(27.0)  # 3" from top (30 - 3)

    def test_hinge_positions_3_hinges(self) -> None:
        """Test hinge positions for 3-hinge configuration."""
        # 50" door: 3 hinges at 3", 25", and 47"
        positions = _calculate_hinge_positions(50.0)

        assert len(positions) == 3
        assert positions[0] == pytest.approx(3.0)  # 3" from bottom
        assert positions[1] == pytest.approx(25.0)  # Middle
        assert positions[2] == pytest.approx(47.0)  # 3" from top

    def test_hinge_positions_4_hinges(self) -> None:
        """Test hinge positions for 4-hinge configuration."""
        # 72" door: 4 hinges evenly distributed
        positions = _calculate_hinge_positions(72.0)

        assert len(positions) == 4
        assert positions[0] == pytest.approx(3.0)  # 3" from bottom
        # Usable height: 72 - 3 - 3 = 66"
        # Quarter: 66 / 3 = 22"
        assert positions[1] == pytest.approx(3.0 + 22.0)  # 25"
        assert positions[2] == pytest.approx(3.0 + 44.0)  # 47"
        assert positions[3] == pytest.approx(69.0)  # 3" from top

    def test_hinge_positions_are_sorted(self) -> None:
        """Test that hinge positions are returned in sorted order."""
        for height in [30.0, 50.0, 72.0]:
            positions = _calculate_hinge_positions(height)
            assert positions == tuple(sorted(positions))

    def test_hinge_positions_at_boundary_40_inches(self) -> None:
        """Test hinge positions at 40\" boundary."""
        positions = _calculate_hinge_positions(40.0)

        assert len(positions) == 3
        assert positions[0] == pytest.approx(3.0)
        assert positions[1] == pytest.approx(20.0)  # Middle
        assert positions[2] == pytest.approx(37.0)

    def test_hinge_positions_at_boundary_60_inches(self) -> None:
        """Test hinge positions at 60\" boundary."""
        positions = _calculate_hinge_positions(60.0)

        assert len(positions) == 3  # 60" is included in 40-60 range
        assert positions[0] == pytest.approx(3.0)
        assert positions[1] == pytest.approx(30.0)  # Middle
        assert positions[2] == pytest.approx(57.0)


# =============================================================================
# Hardware Tests
# =============================================================================


class TestDoorHardware:
    """Tests for door hardware generation."""

    def test_hardware_includes_correct_hinge_count_single_door(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes correct hinge count for single door."""
        config = {"count": 1}

        hardware = overlay_component.hardware(config, standard_context)

        # 30" section height with overlay gives ~30.875" door -> 2 hinges
        hinge_item = next(h for h in hardware if "Hinge" in h.name)
        assert hinge_item.quantity == 2

    def test_hardware_includes_correct_hinge_count_double_door(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes correct hinge count for double doors."""
        config = {"count": 2}

        hardware = overlay_component.hardware(config, standard_context)

        # Each door gets 2 hinges, total = 4
        hinge_item = next(h for h in hardware if "Hinge" in h.name)
        assert hinge_item.quantity == 4

    def test_hardware_soft_close_hinges_by_default(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that soft-close hinges are used by default."""
        config = {"count": 1}

        hardware = overlay_component.hardware(config, standard_context)

        hinge_item = next(h for h in hardware if "Hinge" in h.name)
        assert "Soft-Close" in hinge_item.name
        assert hinge_item.sku == "EURO-35MM-SC"

    def test_hardware_regular_hinges_when_soft_close_false(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that regular hinges are used when soft_close is False."""
        config = {"count": 1, "soft_close": False}

        hardware = overlay_component.hardware(config, standard_context)

        hinge_item = next(h for h in hardware if "Hinge" in h.name)
        assert "Soft-Close" not in hinge_item.name
        assert hinge_item.sku == "EURO-35MM"

    def test_hardware_includes_handle_knob_placeholder(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes handle/knob placeholder."""
        config = {"count": 1}

        hardware = overlay_component.hardware(config, standard_context)

        handle_item = next(h for h in hardware if h.name == "Handle/Knob")
        assert handle_item.quantity == 1

    def test_hardware_handle_quantity_matches_door_count(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that handle quantity matches door count."""
        config = {"count": 2}

        hardware = overlay_component.hardware(config, standard_context)

        handle_item = next(h for h in hardware if h.name == "Handle/Knob")
        assert handle_item.quantity == 2

    def test_hardware_includes_edge_banding(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes edge banding."""
        config = {"count": 1}

        hardware = overlay_component.hardware(config, standard_context)

        edge_item = next(h for h in hardware if h.name == "Edge Banding")
        assert edge_item is not None

    def test_hardware_edge_banding_correct_linear_inches_single(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test edge banding linear inches for single door."""
        config = {"count": 1, "overlay": 0.5, "reveal": 0.125}

        hardware = overlay_component.hardware(config, standard_context)

        # Door: 24.875 x 30.875
        # Perimeter = 2 * (24.875 + 30.875) = 111.5
        door_width = 24.0 + (2 * 0.5) - 0.125
        door_height = 30.0 + (2 * 0.5) - 0.125
        expected_perimeter = 2 * (door_width + door_height)

        edge_item = next(h for h in hardware if h.name == "Edge Banding")
        assert f"{expected_perimeter:.1f}" in edge_item.notes

    def test_hardware_edge_banding_correct_linear_inches_double(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test edge banding linear inches for double doors."""
        config = {"count": 2, "overlay": 0.5, "reveal": 0.125}

        hardware = overlay_component.hardware(config, standard_context)

        # Total door width: 24.875
        # Height: 30.875
        # Perimeter * 2 doors = 2 * (24.875 + 30.875) * 2 = 223.0
        door_width = 24.0 + (2 * 0.5) - 0.125
        door_height = 30.0 + (2 * 0.5) - 0.125
        expected_perimeter = 2 * (door_width + door_height) * 2

        edge_item = next(h for h in hardware if h.name == "Edge Banding")
        assert f"{expected_perimeter:.1f}" in edge_item.notes


# =============================================================================
# HingeSpec Tests
# =============================================================================


class TestHingeSpec:
    """Tests for HingeSpec value object."""

    def test_hinge_spec_creation(self) -> None:
        """Test that HingeSpec can be created with all fields."""
        spec = HingeSpec(
            door_id="door",
            side="left",
            positions=(3.0, 27.0),
        )

        assert spec.door_id == "door"
        assert spec.side == "left"
        assert spec.positions == (3.0, 27.0)

    def test_hinge_spec_default_cup_diameter(self) -> None:
        """Test that HingeSpec has correct default cup diameter (35mm)."""
        spec = HingeSpec(door_id="door", side="left", positions=(3.0,))

        expected_diameter = 35.0 * MM_TO_INCH
        assert spec.cup_diameter == pytest.approx(expected_diameter)

    def test_hinge_spec_default_cup_depth(self) -> None:
        """Test that HingeSpec has correct default cup depth (12mm)."""
        spec = HingeSpec(door_id="door", side="left", positions=(3.0,))

        expected_depth = 12.0 * MM_TO_INCH
        assert spec.cup_depth == pytest.approx(expected_depth)

    def test_hinge_spec_default_cup_inset(self) -> None:
        """Test that HingeSpec has correct default cup inset (22.5mm)."""
        spec = HingeSpec(door_id="door", side="left", positions=(3.0,))

        expected_inset = 22.5 * MM_TO_INCH
        assert spec.cup_inset == pytest.approx(expected_inset)

    def test_hinge_spec_is_frozen(self) -> None:
        """Test that HingeSpec is immutable (frozen)."""
        spec = HingeSpec(door_id="door", side="left", positions=(3.0, 27.0))

        with pytest.raises(AttributeError):
            spec.side = "right"  # type: ignore

    def test_hinge_spec_equality(self) -> None:
        """Test that two HingeSpecs with same values are equal."""
        spec1 = HingeSpec(door_id="door", side="left", positions=(3.0, 27.0))
        spec2 = HingeSpec(door_id="door", side="left", positions=(3.0, 27.0))

        assert spec1 == spec2

    def test_hinge_spec_inequality(self) -> None:
        """Test that HingeSpecs with different values are not equal."""
        spec1 = HingeSpec(door_id="door", side="left", positions=(3.0, 27.0))
        spec2 = HingeSpec(door_id="door", side="right", positions=(3.0, 27.0))

        assert spec1 != spec2


# =============================================================================
# Integration Tests
# =============================================================================


class TestDoorComponentIntegration:
    """Integration tests for door components with the registry."""

    @pytest.fixture(autouse=True)
    def ensure_doors_registered(self) -> None:
        """Ensure door components are registered for integration tests."""
        if "door.hinged.overlay" not in component_registry.list():
            component_registry.register("door.hinged.overlay")(OverlayDoorComponent)
        if "door.hinged.inset" not in component_registry.list():
            component_registry.register("door.hinged.inset")(InsetDoorComponent)
        if "door.hinged.partial" not in component_registry.list():
            component_registry.register("door.hinged.partial")(PartialOverlayDoorComponent)

    def test_full_workflow_overlay_door(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        component_class = component_registry.get("door.hinged.overlay")
        component = component_class()

        config = {"count": 1, "hinge_side": "left"}

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1
        assert generation.panels[0].panel_type == PanelType.DOOR
        assert "hinge_specs" in generation.metadata

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) >= 3  # Hinges, handle, edge banding

    def test_full_workflow_inset_door(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for inset door."""
        component_class = component_registry.get("door.hinged.inset")
        component = component_class()

        config = {"count": 2}

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 2

    def test_full_workflow_partial_overlay_door(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for partial overlay door."""
        component_class = component_registry.get("door.hinged.partial")
        component = component_class()

        config = {"count": 1}

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 1

    def test_hinge_specs_in_metadata_single_door(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hinge_specs are present in metadata for single door."""
        config = {"count": 1, "hinge_side": "right"}

        result = overlay_component.generate(config, standard_context)

        assert "hinge_specs" in result.metadata
        hinge_specs = result.metadata["hinge_specs"]
        assert len(hinge_specs) == 1
        assert hinge_specs[0].door_id == "door"
        assert hinge_specs[0].side == "right"

    def test_hinge_specs_in_metadata_double_doors(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hinge_specs are present in metadata for double doors."""
        config = {"count": 2}

        result = overlay_component.generate(config, standard_context)

        hinge_specs = result.metadata["hinge_specs"]
        assert len(hinge_specs) == 2
        assert hinge_specs[0].door_id == "left_door"
        assert hinge_specs[0].side == "left"
        assert hinge_specs[1].door_id == "right_door"
        assert hinge_specs[1].side == "right"


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestDoorComponentEdgeCases:
    """Edge case tests for door components."""

    def test_default_config_values(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that default config values are applied correctly."""
        config: dict = {}  # Empty config, use all defaults

        result = overlay_component.validate(config, standard_context)

        # Default count=1 should be valid
        assert result.is_valid

    def test_custom_material_in_config(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that custom material in config is used."""
        config = {
            "count": 1,
            "material": {"thickness": 0.5}
        }

        result = overlay_component.generate(config, standard_context)

        assert result.panels[0].material.thickness == 0.5

    def test_very_tall_door_has_4_hinges(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that very tall doors have 4 hinges."""
        tall_context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        hardware = overlay_component.hardware(config, tall_context)

        hinge_item = next(h for h in hardware if "Hinge" in h.name)
        assert hinge_item.quantity == 4

    def test_minimum_size_door(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test door at minimum section size."""
        min_context = ComponentContext(
            width=6.0,
            height=6.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.0, 0.0),
            section_index=0,
            cabinet_width=12.0,
            cabinet_height=12.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        validation = overlay_component.validate(config, min_context)
        assert validation.is_valid

        generation = overlay_component.generate(config, min_context)
        assert len(generation.panels) == 1

    def test_different_reveal_values(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test various valid reveal values."""
        for reveal in [0.0625, 0.125, 0.25, 0.375]:
            config = {"count": 1, "reveal": reveal}
            result = overlay_component.validate(config, standard_context)
            assert result.is_valid, f"Reveal {reveal} should be valid"

    def test_different_overlay_values(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test various overlay values affect door size correctly."""
        overlays = [0.25, 0.5, 0.75, 1.0]
        reveal = 0.125

        for overlay in overlays:
            config = {"count": 1, "overlay": overlay, "reveal": reveal}
            result = overlay_component.generate(config, standard_context)

            expected_width = 24.0 + (2 * overlay) - reveal
            assert result.panels[0].width == pytest.approx(expected_width)

    def test_mm_to_inch_constant(self) -> None:
        """Test that MM_TO_INCH is the correct conversion factor."""
        assert MM_TO_INCH == pytest.approx(0.0393700787)
        # 25.4mm = 1 inch
        assert 25.4 * MM_TO_INCH == pytest.approx(1.0, rel=1e-5)

    def test_35mm_cup_diameter_in_inches(self) -> None:
        """Test that 35mm cup diameter converts correctly to inches."""
        expected_inches = 35.0 * MM_TO_INCH
        assert expected_inches == pytest.approx(1.378, abs=0.001)


class TestDoorGenerationMetadata:
    """Tests for metadata generation in door components."""

    def test_single_door_hinge_positions_in_spec(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hinge spec contains correct positions."""
        config = {"count": 1}

        result = overlay_component.generate(config, standard_context)

        hinge_spec = result.metadata["hinge_specs"][0]
        # Door height ~30.875, should have 2 hinges
        assert len(hinge_spec.positions) == 2
        assert hinge_spec.positions[0] == pytest.approx(3.0)

    def test_tall_door_hinge_positions_in_spec(
        self, overlay_component: OverlayDoorComponent
    ) -> None:
        """Test that tall door hinge spec contains 4 positions."""
        tall_context = ComponentContext(
            width=24.0,
            height=70.0,  # Will result in door > 60" after overlay
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"count": 1}

        result = overlay_component.generate(config, tall_context)

        hinge_spec = result.metadata["hinge_specs"][0]
        assert len(hinge_spec.positions) == 4

    def test_hardware_returned_in_generate_result(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate() returns hardware in the result."""
        config = {"count": 1}

        result = overlay_component.generate(config, standard_context)

        assert len(result.hardware) >= 3
        hardware_names = [h.name for h in result.hardware]
        assert "Handle/Knob" in hardware_names
        assert "Edge Banding" in hardware_names
        assert any("Hinge" in name for name in hardware_names)


class TestDoorStyleComparison:
    """Tests comparing different door styles."""

    def test_overlay_is_larger_than_inset(
        self,
        overlay_component: OverlayDoorComponent,
        inset_component: InsetDoorComponent,
        standard_context: ComponentContext
    ) -> None:
        """Test that overlay doors are larger than inset doors."""
        config = {"count": 1, "reveal": 0.125, "overlay": 0.5}

        overlay_result = overlay_component.generate(config, standard_context)
        inset_result = inset_component.generate(config, standard_context)

        assert overlay_result.panels[0].width > inset_result.panels[0].width
        assert overlay_result.panels[0].height > inset_result.panels[0].height

    def test_partial_is_between_overlay_and_inset(
        self,
        overlay_component: OverlayDoorComponent,
        inset_component: InsetDoorComponent,
        partial_component: PartialOverlayDoorComponent,
        standard_context: ComponentContext
    ) -> None:
        """Test that partial overlay is between full overlay and inset."""
        config = {"count": 1, "reveal": 0.125, "overlay": 0.5}

        overlay_result = overlay_component.generate(config, standard_context)
        inset_result = inset_component.generate(config, standard_context)
        partial_result = partial_component.generate(config, standard_context)

        # Partial should be smaller than full overlay
        assert partial_result.panels[0].width < overlay_result.panels[0].width

        # Partial should be larger than inset
        assert partial_result.panels[0].width > inset_result.panels[0].width

    def test_all_door_types_produce_same_panel_type(
        self,
        overlay_component: OverlayDoorComponent,
        inset_component: InsetDoorComponent,
        partial_component: PartialOverlayDoorComponent,
        standard_context: ComponentContext
    ) -> None:
        """Test that all door types produce PanelType.DOOR."""
        config = {"count": 1}

        for component in [overlay_component, inset_component, partial_component]:
            result = component.generate(config, standard_context)
            assert result.panels[0].panel_type == PanelType.DOOR


# =============================================================================
# HingePlateSpec Tests
# =============================================================================


class TestHingePlateSpec:
    """Tests for HingePlateSpec value object."""

    def test_hinge_plate_spec_creation(self) -> None:
        """Test that HingePlateSpec can be created with all fields."""
        spec = HingePlateSpec(
            panel_id="left_side",
            positions=(3.0, 27.0),
        )

        assert spec.panel_id == "left_side"
        assert spec.positions == (3.0, 27.0)

    def test_hinge_plate_spec_default_plate_inset(self) -> None:
        """Test that HingePlateSpec has correct default plate inset (0.5\")."""
        spec = HingePlateSpec(panel_id="left_side", positions=(3.0,))

        assert spec.plate_inset == 0.5

    def test_hinge_plate_spec_default_plate_dimensions(self) -> None:
        """Test that HingePlateSpec has correct default plate dimensions."""
        spec = HingePlateSpec(panel_id="left_side", positions=(3.0,))

        assert spec.plate_width == 0.5
        assert spec.plate_height == 2.0

    def test_hinge_plate_spec_is_frozen(self) -> None:
        """Test that HingePlateSpec is immutable (frozen)."""
        spec = HingePlateSpec(panel_id="left_side", positions=(3.0, 27.0))

        with pytest.raises(AttributeError):
            spec.panel_id = "right_side"  # type: ignore

    def test_hinge_plate_spec_equality(self) -> None:
        """Test that two HingePlateSpecs with same values are equal."""
        spec1 = HingePlateSpec(panel_id="left_side", positions=(3.0, 27.0))
        spec2 = HingePlateSpec(panel_id="left_side", positions=(3.0, 27.0))

        assert spec1 == spec2

    def test_hinge_plate_spec_inequality(self) -> None:
        """Test that HingePlateSpecs with different values are not equal."""
        spec1 = HingePlateSpec(panel_id="left_side", positions=(3.0, 27.0))
        spec2 = HingePlateSpec(panel_id="right_side", positions=(3.0, 27.0))

        assert spec1 != spec2


class TestHingePlateSpecInGeneration:
    """Tests for HingePlateSpec generation in door components."""

    def test_single_door_left_hinge_creates_left_side_plate_spec(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that single door with left hinge creates left_side plate spec."""
        config = {"count": 1, "hinge_side": "left"}

        result = overlay_component.generate(config, standard_context)

        assert "hinge_plate_specs" in result.metadata
        plate_specs = result.metadata["hinge_plate_specs"]
        assert len(plate_specs) == 1
        assert plate_specs[0].panel_id == "left_side"

    def test_single_door_right_hinge_creates_right_side_plate_spec(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that single door with right hinge creates right_side plate spec."""
        config = {"count": 1, "hinge_side": "right"}

        result = overlay_component.generate(config, standard_context)

        plate_specs = result.metadata["hinge_plate_specs"]
        assert len(plate_specs) == 1
        assert plate_specs[0].panel_id == "right_side"

    def test_double_doors_create_both_side_plate_specs(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that double doors create plate specs for both side panels."""
        config = {"count": 2}

        result = overlay_component.generate(config, standard_context)

        plate_specs = result.metadata["hinge_plate_specs"]
        assert len(plate_specs) == 2
        panel_ids = {spec.panel_id for spec in plate_specs}
        assert panel_ids == {"left_side", "right_side"}

    def test_hinge_plate_positions_match_hinge_positions(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hinge plate positions match door hinge positions."""
        config = {"count": 1, "hinge_side": "left"}

        result = overlay_component.generate(config, standard_context)

        hinge_specs = result.metadata["hinge_specs"]
        plate_specs = result.metadata["hinge_plate_specs"]

        assert hinge_specs[0].positions == plate_specs[0].positions


# =============================================================================
# HandlePositionSpec Tests
# =============================================================================


class TestHandlePositionSpec:
    """Tests for HandlePositionSpec value object."""

    def test_handle_position_spec_creation(self) -> None:
        """Test that HandlePositionSpec can be created with all fields."""
        spec = HandlePositionSpec(
            door_id="door",
            x=12.0,
            y=27.0,
            position_type="upper",
        )

        assert spec.door_id == "door"
        assert spec.x == 12.0
        assert spec.y == 27.0
        assert spec.position_type == "upper"

    def test_handle_position_spec_is_frozen(self) -> None:
        """Test that HandlePositionSpec is immutable (frozen)."""
        spec = HandlePositionSpec(door_id="door", x=12.0, y=27.0, position_type="upper")

        with pytest.raises(AttributeError):
            spec.x = 15.0  # type: ignore

    def test_handle_position_spec_equality(self) -> None:
        """Test that two HandlePositionSpecs with same values are equal."""
        spec1 = HandlePositionSpec(door_id="door", x=12.0, y=27.0, position_type="upper")
        spec2 = HandlePositionSpec(door_id="door", x=12.0, y=27.0, position_type="upper")

        assert spec1 == spec2


class TestHandlePositionSpecInGeneration:
    """Tests for HandlePositionSpec generation in door components."""

    def test_single_door_handle_spec_in_metadata(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that single door generates handle spec in metadata."""
        config = {"count": 1}

        result = overlay_component.generate(config, standard_context)

        assert "handle_specs" in result.metadata
        handle_specs = result.metadata["handle_specs"]
        assert len(handle_specs) == 1
        assert handle_specs[0].door_id == "door"

    def test_double_doors_handle_specs_in_metadata(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that double doors generate handle specs for both doors."""
        config = {"count": 2}

        result = overlay_component.generate(config, standard_context)

        handle_specs = result.metadata["handle_specs"]
        assert len(handle_specs) == 2
        door_ids = {spec.door_id for spec in handle_specs}
        assert door_ids == {"left_door", "right_door"}

    def test_upper_handle_position_3_inches_from_top(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that upper handle is 3\" from top of door."""
        config = {"count": 1, "handle_position": "upper", "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        # Door height: 30 + 2*0.5 - 0.125 = 30.875
        door_height = 30.0 + (2 * 0.5) - 0.125
        expected_y = door_height - 3.0

        handle_spec = result.metadata["handle_specs"][0]
        assert handle_spec.y == pytest.approx(expected_y)
        assert handle_spec.position_type == "upper"

    def test_lower_handle_position_3_inches_from_bottom(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that lower handle is 3\" from bottom of door."""
        config = {"count": 1, "handle_position": "lower"}

        result = overlay_component.generate(config, standard_context)

        handle_spec = result.metadata["handle_specs"][0]
        assert handle_spec.y == pytest.approx(3.0)
        assert handle_spec.position_type == "lower"

    def test_single_door_handle_centered_horizontally(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that single door handle is centered horizontally."""
        config = {"count": 1, "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        # Door width: 24 + 2*0.5 - 0.125 = 24.875
        door_width = 24.0 + (2 * 0.5) - 0.125
        expected_x = door_width / 2

        handle_spec = result.metadata["handle_specs"][0]
        assert handle_spec.x == pytest.approx(expected_x)

    def test_double_door_handles_opposite_hinge_side(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that double door handles are positioned opposite their hinges."""
        config = {"count": 2, "overlay": 0.5, "reveal": 0.125}

        result = overlay_component.generate(config, standard_context)

        handle_specs = result.metadata["handle_specs"]

        # Find left and right door specs
        left_handle = next(h for h in handle_specs if h.door_id == "left_door")
        right_handle = next(h for h in handle_specs if h.door_id == "right_door")

        # Door width: (24.875 - 0.125) / 2 = 12.375
        door_width = 24.0 + (2 * 0.5) - 0.125
        single_width = (door_width - 0.125) / 2

        # Left door handle should be near right edge (single_width - 3)
        assert left_handle.x == pytest.approx(single_width - 3.0)

        # Right door handle should be near left edge (3")
        assert right_handle.x == pytest.approx(3.0)

    def test_default_handle_position_is_upper(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that default handle position is 'upper'."""
        config = {"count": 1}  # No handle_position specified

        result = overlay_component.generate(config, standard_context)

        handle_spec = result.metadata["handle_specs"][0]
        assert handle_spec.position_type == "upper"

    def test_hardware_notes_include_handle_position(
        self, overlay_component: OverlayDoorComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware notes include handle position info."""
        config = {"count": 1, "handle_position": "lower"}

        result = overlay_component.generate(config, standard_context)

        handle_hardware = next(h for h in result.hardware if h.name == "Handle/Knob")
        assert "lower" in handle_hardware.notes
        assert "3\"" in handle_hardware.notes
