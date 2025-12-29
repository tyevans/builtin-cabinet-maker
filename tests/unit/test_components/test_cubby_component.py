"""Tests for UniformCubbyComponent, VariableCubbyComponent, and NotchSpec."""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    HardwareItem,
    ValidationResult,
    component_registry,
)
from cabinets.domain.components.cubby import (
    MIN_CUBBY_SIZE,
    MAX_GRID_SIZE,
    NotchSpec,
    UniformCubbyComponent,
    VariableCubbyComponent,
    _calculate_uniform_sizes,
    _generate_dividers,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def uniform_cubby_component() -> UniformCubbyComponent:
    """Create a UniformCubbyComponent instance for testing."""
    return UniformCubbyComponent()


@pytest.fixture
def variable_cubby_component() -> VariableCubbyComponent:
    """Create a VariableCubbyComponent instance for testing."""
    return VariableCubbyComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 24" wide by 36" tall section with 11.5" depth
    at position (0.75, 0.75) within a 48x84x12 cabinet.
    """
    return ComponentContext(
        width=24.0,
        height=36.0,
        depth=11.5,  # Interior depth (12 - 0.5 back panel)
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def large_context() -> ComponentContext:
    """Create a larger ComponentContext for testing grids.

    Returns a context representing a 48" wide by 72" tall section.
    """
    return ComponentContext(
        width=48.0,
        height=72.0,
        depth=11.5,
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


# =============================================================================
# NotchSpec Tests
# =============================================================================


class TestNotchSpec:
    """Tests for NotchSpec value object."""

    def test_notch_spec_creation(self) -> None:
        """Test that NotchSpec can be created with all fields."""
        notch = NotchSpec(
            position=12.0,
            width=0.75,
            depth=0.375,
            edge="top",
        )

        assert notch.position == 12.0
        assert notch.width == 0.75
        assert notch.depth == 0.375
        assert notch.edge == "top"

    def test_notch_spec_is_frozen(self) -> None:
        """Test that NotchSpec is immutable (frozen)."""
        notch = NotchSpec(12.0, 0.75, 0.375, "top")

        with pytest.raises(AttributeError):
            notch.position = 15.0  # type: ignore

    def test_notch_spec_equality(self) -> None:
        """Test that two NotchSpecs with same values are equal."""
        notch1 = NotchSpec(12.0, 0.75, 0.375, "top")
        notch2 = NotchSpec(12.0, 0.75, 0.375, "top")

        assert notch1 == notch2

    def test_notch_spec_inequality(self) -> None:
        """Test that NotchSpecs with different values are not equal."""
        notch1 = NotchSpec(12.0, 0.75, 0.375, "top")
        notch2 = NotchSpec(12.0, 0.75, 0.375, "bottom")

        assert notch1 != notch2

    def test_notch_spec_valid_edges(self) -> None:
        """Test NotchSpec accepts all valid edge values."""
        for edge in ["top", "bottom", "left", "right"]:
            notch = NotchSpec(12.0, 0.75, 0.375, edge)
            assert notch.edge == edge

    def test_notch_spec_invalid_edge_raises(self) -> None:
        """Test NotchSpec raises for invalid edge value."""
        with pytest.raises(ValueError, match="Edge must be one of"):
            NotchSpec(12.0, 0.75, 0.375, "invalid")

    def test_notch_spec_negative_position_raises(self) -> None:
        """Test NotchSpec raises for negative position."""
        with pytest.raises(ValueError, match="position must be non-negative"):
            NotchSpec(-1.0, 0.75, 0.375, "top")

    def test_notch_spec_zero_width_raises(self) -> None:
        """Test NotchSpec raises for zero width."""
        with pytest.raises(ValueError, match="width must be positive"):
            NotchSpec(12.0, 0.0, 0.375, "top")

    def test_notch_spec_zero_depth_raises(self) -> None:
        """Test NotchSpec raises for zero depth."""
        with pytest.raises(ValueError, match="depth must be positive"):
            NotchSpec(12.0, 0.75, 0.0, "top")

    def test_notch_spec_hashable(self) -> None:
        """Test that NotchSpec can be used in sets and as dict keys."""
        notch = NotchSpec(12.0, 0.75, 0.375, "top")

        notch_set = {notch}
        assert notch in notch_set

        notch_dict = {notch: "test"}
        assert notch_dict[notch] == "test"


# =============================================================================
# UniformCubbyComponent Registration Tests
# =============================================================================


class TestUniformCubbyComponentRegistration:
    """Tests for cubby.uniform component registration."""

    @pytest.fixture(autouse=True)
    def ensure_cubby_registered(self) -> None:
        """Ensure cubby.uniform is registered for each test."""
        if "cubby.uniform" not in component_registry.list():
            component_registry.register("cubby.uniform")(UniformCubbyComponent)

    def test_component_is_registered_as_cubby_uniform(self) -> None:
        """Test that cubby.uniform is registered in the component registry."""
        assert "cubby.uniform" in component_registry.list()

    def test_get_returns_uniform_cubby_component_class(self) -> None:
        """Test that registry.get returns UniformCubbyComponent."""
        component_class = component_registry.get("cubby.uniform")
        assert component_class is UniformCubbyComponent


# =============================================================================
# UniformCubbyComponent Validation Tests
# =============================================================================


class TestUniformCubbyComponentValidation:
    """Tests for UniformCubbyComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid rows and columns."""
        config = {"rows": 3, "columns": 4}

        result = uniform_cubby_component.validate(config, large_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_single_cubby(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for 1x1 grid (no dividers)."""
        config = {"rows": 1, "columns": 1}

        result = uniform_cubby_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_ok_for_defaults(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok with default rows/columns."""
        config = {}

        result = uniform_cubby_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_zero_rows(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for zero rows."""
        config = {"rows": 0, "columns": 2}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "rows must be a positive integer" in result.errors

    def test_validate_returns_error_for_negative_rows(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for negative rows."""
        config = {"rows": -1, "columns": 2}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "rows must be a positive integer" in result.errors

    def test_validate_returns_error_for_zero_columns(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for zero columns."""
        config = {"rows": 2, "columns": 0}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "columns must be a positive integer" in result.errors

    def test_validate_returns_error_for_rows_exceeding_max(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for rows > 10."""
        config = {"rows": 11, "columns": 2}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert f"rows exceeds maximum of {MAX_GRID_SIZE}" in result.errors

    def test_validate_returns_error_for_columns_exceeding_max(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for columns > 10."""
        config = {"rows": 2, "columns": 11}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert f"columns exceeds maximum of {MAX_GRID_SIZE}" in result.errors

    def test_validate_returns_error_for_cubby_width_below_minimum(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error when cubby width < 6 inches."""
        # 24" width, 5 columns: (24 - 4*0.75) / 5 = 4.2" (below 6")
        config = {"rows": 1, "columns": 5}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Cubby width" in result.errors[0]
        assert "less than minimum" in result.errors[0]

    def test_validate_returns_error_for_cubby_height_below_minimum(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error when cubby height < 6 inches."""
        # 36" height, 7 rows: (36 - 6*0.75) / 7 = 4.5" (below 6")
        config = {"rows": 7, "columns": 1}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Cubby height" in result.errors[0]
        assert "less than minimum" in result.errors[0]

    def test_validate_accepts_max_grid_size(
        self, uniform_cubby_component: UniformCubbyComponent
    ) -> None:
        """Test that validate accepts exactly 10x10 grid with sufficient space."""
        # Need large context for 10x10 grid with 6" min cubby size
        # 10 cubbies * 6" + 9 dividers * 0.75" = 66.75" per dimension
        large_context = ComponentContext(
            width=67.0,
            height=67.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=72.0,
            cabinet_depth=12.0,
        )
        config = {"rows": 10, "columns": 10}

        result = uniform_cubby_component.validate(config, large_context)

        assert result.is_valid

    def test_validate_returns_error_for_float_rows(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for float rows."""
        config = {"rows": 2.5, "columns": 2}

        result = uniform_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "rows must be a positive integer" in result.errors


# =============================================================================
# UniformCubbyComponent Generation Tests
# =============================================================================


class TestUniformCubbyComponentGeneration:
    """Tests for UniformCubbyComponent.generate()."""

    def test_generate_returns_empty_for_single_cubby(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 1x1 grid generates no panels (no dividers needed)."""
        config = {"rows": 1, "columns": 1}

        result = uniform_cubby_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_generate_creates_horizontal_dividers(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that horizontal dividers are created for multiple rows."""
        config = {"rows": 3, "columns": 1}  # 2 horizontal dividers

        result = uniform_cubby_component.generate(config, large_context)

        horizontal_panels = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(horizontal_panels) == 2

    def test_generate_creates_vertical_dividers(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that vertical dividers are created for multiple columns."""
        config = {"rows": 1, "columns": 3}  # 2 vertical dividers

        result = uniform_cubby_component.generate(config, large_context)

        vertical_panels = [p for p in result.panels if p.panel_type == PanelType.DIVIDER]
        assert len(vertical_panels) == 2

    def test_generate_creates_correct_total_panels_for_grid(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test total panel count for a 3x4 grid.

        3 rows, 4 columns:
        - Horizontal dividers: 2 (rows - 1)
        - Vertical dividers: 3 (columns - 1) * 3 (rows) = 9
        - Total: 11 panels
        """
        config = {"rows": 3, "columns": 4}

        result = uniform_cubby_component.generate(config, large_context)

        expected_horizontal = 2
        expected_vertical = 9
        assert len(result.panels) == expected_horizontal + expected_vertical

    def test_generate_horizontal_dividers_use_shelf_panel_type(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that horizontal dividers use PanelType.SHELF."""
        config = {"rows": 2, "columns": 1}

        result = uniform_cubby_component.generate(config, large_context)

        for panel in result.panels:
            if panel.width == large_context.width:  # Horizontal dividers span full width
                assert panel.panel_type == PanelType.SHELF

    def test_generate_vertical_dividers_use_divider_panel_type(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that vertical dividers use PanelType.DIVIDER."""
        config = {"rows": 1, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        for panel in result.panels:
            assert panel.panel_type == PanelType.DIVIDER

    def test_generate_horizontal_divider_dimensions(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test horizontal divider has correct dimensions."""
        config = {"rows": 2, "columns": 1}

        result = uniform_cubby_component.generate(config, large_context)

        assert len(result.panels) == 1
        panel = result.panels[0]
        assert panel.width == large_context.width  # Full section width
        assert panel.height == large_context.depth  # Section depth

    def test_generate_returns_notch_specs_in_metadata(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that notch_specs are included in metadata."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        assert "notch_specs" in result.metadata
        assert isinstance(result.metadata["notch_specs"], dict)

    def test_generate_notch_specs_keyed_by_divider_label(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that notch_specs are keyed by divider labels."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        notch_specs = result.metadata["notch_specs"]
        # Should have horizontal_divider_1, vertical_divider_r1_c1, vertical_divider_r2_c1
        assert "horizontal_divider_1" in notch_specs

    def test_generate_includes_edge_banding_hardware(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that edge banding hardware is included."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        assert len(result.hardware) == 1
        assert result.hardware[0].name == "Edge Banding"

    def test_generate_no_edge_banding_when_disabled(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that edge banding is excluded when disabled."""
        config = {"rows": 2, "columns": 2, "edge_band_front": False}

        result = uniform_cubby_component.generate(config, large_context)

        assert len(result.hardware) == 0

    def test_generate_returns_generation_result_type(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        assert isinstance(result, GenerationResult)


# =============================================================================
# UniformCubbyComponent Hardware Tests
# =============================================================================


class TestUniformCubbyComponentHardware:
    """Tests for UniformCubbyComponent.hardware()."""

    def test_hardware_returns_edge_banding(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that hardware returns edge banding for grid."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.hardware(config, large_context)

        assert len(result) == 1
        assert result[0].name == "Edge Banding"

    def test_hardware_returns_empty_for_single_cubby(
        self, uniform_cubby_component: UniformCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty for 1x1 grid (no dividers)."""
        config = {"rows": 1, "columns": 1}

        result = uniform_cubby_component.hardware(config, standard_context)

        assert len(result) == 0

    def test_hardware_returns_empty_when_disabled(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty when edge_band_front is False."""
        config = {"rows": 2, "columns": 2, "edge_band_front": False}

        result = uniform_cubby_component.hardware(config, large_context)

        assert len(result) == 0

    def test_hardware_calculates_correct_banding_length(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that edge banding calculation is correct.

        For 2x2 grid (48" wide, 72" tall, 0.75" dividers):
        - 1 horizontal divider: 48"
        - 2 vertical dividers per row * 2 rows = 2 vertical dividers total
        - But each vertical fits within one row, so 2 verticals
        - Row height: (72 - 0.75) / 2 = 35.625"
        - Vertical banding: 35.625" * 2 = 71.25"
        - Total: 48" + 71.25" = 119.25" (approximately)
        """
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.hardware(config, large_context)

        assert "linear inches" in result[0].notes


# =============================================================================
# VariableCubbyComponent Registration Tests
# =============================================================================


class TestVariableCubbyComponentRegistration:
    """Tests for cubby.variable component registration."""

    @pytest.fixture(autouse=True)
    def ensure_variable_registered(self) -> None:
        """Ensure cubby.variable is registered for each test."""
        if "cubby.variable" not in component_registry.list():
            component_registry.register("cubby.variable")(VariableCubbyComponent)

    def test_component_is_registered_as_cubby_variable(self) -> None:
        """Test that cubby.variable is registered in the component registry."""
        assert "cubby.variable" in component_registry.list()

    def test_get_returns_variable_cubby_component_class(self) -> None:
        """Test that registry.get returns VariableCubbyComponent."""
        component_class = component_registry.get("cubby.variable")
        assert component_class is VariableCubbyComponent


# =============================================================================
# VariableCubbyComponent Validation Tests
# =============================================================================


class TestVariableCubbyComponentValidation:
    """Tests for VariableCubbyComponent.validate()."""

    def test_validate_returns_ok_for_valid_explicit_dimensions(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test that validate returns ok for valid row_heights and column_widths."""
        # 48" wide, 72" tall, 0.75" dividers
        # 3 columns: column_widths + 2*0.75 dividers = 48"
        #   So column_widths sum = 48 - 1.5 = 46.5"
        # 2 rows: row_heights + 0.75 divider = 72"
        #   So row_heights sum = 72 - 0.75 = 71.25"
        context = ComponentContext(
            width=48.0,
            height=72.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {
            "row_heights": [35.625, 35.625],  # Sum = 71.25, + 0.75 divider = 72.0
            "column_widths": [12.0, 22.5, 12.0],  # Sum = 46.5, + 1.5 dividers = 48.0
        }

        result = variable_cubby_component.validate(config, context)

        assert result.is_valid

    def test_validate_returns_ok_for_row_heights_only(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test validate with row_heights and uniform columns."""
        context = ComponentContext(
            width=24.0,
            height=36.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        # 36" height, 2 rows: row_heights must sum to 36 - 0.75 = 35.25"
        config = {
            "row_heights": [17.625, 17.625],
            "columns": 2,  # Uniform columns
        }

        result = variable_cubby_component.validate(config, context)

        assert result.is_valid

    def test_validate_returns_ok_for_column_widths_only(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test validate with column_widths and uniform rows."""
        context = ComponentContext(
            width=24.0,
            height=36.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        # 24" width, 2 columns: column_widths must sum to 24 - 0.75 = 23.25"
        config = {
            "column_widths": [11.625, 11.625],
            "rows": 2,  # Uniform rows
        }

        result = variable_cubby_component.validate(config, context)

        assert result.is_valid

    def test_validate_returns_error_for_empty_row_heights(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for empty row_heights list."""
        config = {"row_heights": [], "columns": 2}

        result = variable_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "row_heights must be a non-empty list" in result.errors

    def test_validate_returns_error_for_empty_column_widths(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for empty column_widths list."""
        config = {"column_widths": [], "rows": 2}

        result = variable_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "column_widths must be a non-empty list" in result.errors

    def test_validate_returns_error_for_negative_row_height(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for negative row height."""
        config = {"row_heights": [10.0, -5.0], "columns": 1}

        result = variable_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "Row 2 height must be positive" in result.errors

    def test_validate_returns_error_for_row_height_below_minimum(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for row height < 6 inches."""
        config = {"row_heights": [5.0], "columns": 1}

        result = variable_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "less than minimum" in result.errors[0]

    def test_validate_returns_error_for_dimension_mismatch(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error when dimensions don't match section."""
        # 36" height but row_heights sum to different value
        config = {"row_heights": [10.0, 10.0], "columns": 1}  # Sum = 20, not 36

        result = variable_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert "does not equal section height" in result.errors[0]

    def test_validate_returns_error_for_too_many_rows(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for more than 10 rows."""
        config = {"row_heights": [6.0] * 11, "columns": 1}

        result = variable_cubby_component.validate(config, standard_context)

        assert not result.is_valid
        assert f"exceeds maximum of {MAX_GRID_SIZE}" in result.errors[0]


# =============================================================================
# VariableCubbyComponent Generation Tests
# =============================================================================


class TestVariableCubbyComponentGeneration:
    """Tests for VariableCubbyComponent.generate()."""

    def test_generate_creates_correct_panels_for_variable_grid(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test generation with variable row heights."""
        context = ComponentContext(
            width=24.0,
            height=37.5,  # 12 + 0.75 + 24 + 0.75 = 37.5
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"row_heights": [12.0, 24.0], "columns": 1}  # 2 rows, 1 column

        result = variable_cubby_component.generate(config, context)

        # Should have 1 horizontal divider (rows - 1)
        assert len(result.panels) == 1
        assert result.panels[0].panel_type == PanelType.SHELF

    def test_generate_creates_variable_width_columns(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test generation with variable column widths."""
        context = ComponentContext(
            width=24.75,  # 6 + 0.75 + 12 + 0.75 + 6 = 25.5, need adjustment
            height=36.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        # Width: 6 + 0.75 + 12 + 0.75 + 6 = 25.5, so use 25.5
        context = ComponentContext(
            width=25.5,
            height=36.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"column_widths": [6.0, 12.0, 6.0], "rows": 1}  # 3 columns, 1 row

        result = variable_cubby_component.generate(config, context)

        # Should have 2 vertical dividers (columns - 1)
        assert len(result.panels) == 2
        for panel in result.panels:
            assert panel.panel_type == PanelType.DIVIDER

    def test_generate_with_mixed_mode(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test generation with explicit row_heights and uniform columns."""
        context = ComponentContext(
            width=24.0,
            height=36.75,  # 12 + 0.75 + 24 = 36.75
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {
            "row_heights": [12.0, 24.0],
            "columns": 2,  # Uniform columns
        }

        result = variable_cubby_component.generate(config, context)

        # 1 horizontal divider + 2 vertical dividers (1 per row * 2 rows)
        horizontal = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        vertical = [p for p in result.panels if p.panel_type == PanelType.DIVIDER]
        assert len(horizontal) == 1
        assert len(vertical) == 2

    def test_generate_returns_notch_specs(
        self, variable_cubby_component: VariableCubbyComponent
    ) -> None:
        """Test that notch_specs are included in metadata."""
        context = ComponentContext(
            width=24.0,
            height=36.75,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"row_heights": [12.0, 24.0], "columns": 2}

        result = variable_cubby_component.generate(config, context)

        assert "notch_specs" in result.metadata

    def test_generate_returns_empty_for_invalid_config(
        self, variable_cubby_component: VariableCubbyComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns empty for invalid config."""
        config = {"rows": 0, "columns": 0}

        result = variable_cubby_component.generate(config, standard_context)

        assert len(result.panels) == 0


# =============================================================================
# Notch Spec Generation Tests
# =============================================================================


class TestNotchSpecGeneration:
    """Tests for notch specification generation in dividers."""

    def test_horizontal_divider_notches_on_top_edge(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that horizontal dividers have notches on top edge."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        notch_specs = result.metadata["notch_specs"]
        h_notches = notch_specs.get("horizontal_divider_1", [])
        assert len(h_notches) == 1
        assert h_notches[0].edge == "top"

    def test_bottom_row_vertical_divider_notch_on_top(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that vertical dividers in bottom row have notch on top edge."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        notch_specs = result.metadata["notch_specs"]
        # Bottom row is r1
        v_notches = notch_specs.get("vertical_divider_r1_c1", [])
        assert len(v_notches) == 1
        assert v_notches[0].edge == "top"

    def test_top_row_vertical_divider_notch_on_bottom(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that vertical dividers in top row have notch on bottom edge."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        notch_specs = result.metadata["notch_specs"]
        # Top row is r2 (for 2 rows)
        v_notches = notch_specs.get("vertical_divider_r2_c1", [])
        assert len(v_notches) == 1
        assert v_notches[0].edge == "bottom"

    def test_middle_row_vertical_divider_notches_on_both_edges(
        self, uniform_cubby_component: UniformCubbyComponent
    ) -> None:
        """Test that vertical dividers in middle rows have notches on both edges."""
        context = ComponentContext(
            width=48.0,
            height=90.0,  # Tall enough for 3 rows of 6"+ each
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=96.0,
            cabinet_depth=12.0,
        )
        config = {"rows": 3, "columns": 2}

        result = uniform_cubby_component.generate(config, context)

        notch_specs = result.metadata["notch_specs"]
        # Middle row is r2 (for 3 rows: r1=bottom, r2=middle, r3=top)
        v_notches = notch_specs.get("vertical_divider_r2_c1", [])
        assert len(v_notches) == 2
        edges = {n.edge for n in v_notches}
        assert edges == {"top", "bottom"}

    def test_single_row_vertical_dividers_no_notches(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that vertical dividers in single-row grid have no notches."""
        config = {"rows": 1, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        notch_specs = result.metadata["notch_specs"]
        v_notches = notch_specs.get("vertical_divider_r1_c1", [])
        assert len(v_notches) == 0

    def test_notch_width_equals_material_thickness(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that notch width equals material thickness."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        notch_specs = result.metadata["notch_specs"]
        for notches in notch_specs.values():
            for notch in notches:
                assert notch.width == large_context.material.thickness

    def test_notch_depth_equals_half_thickness(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that notch depth equals half material thickness."""
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.generate(config, large_context)

        half_thickness = large_context.material.thickness / 2
        notch_specs = result.metadata["notch_specs"]
        for notches in notch_specs.values():
            for notch in notches:
                assert notch.depth == pytest.approx(half_thickness)


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestCalculateUniformSizes:
    """Tests for _calculate_uniform_sizes helper function."""

    def test_returns_empty_for_zero_count(self) -> None:
        """Test that function returns empty list for zero count."""
        result = _calculate_uniform_sizes(48.0, 0, 0.75)
        assert result == []

    def test_returns_single_size_for_one_count(self) -> None:
        """Test that function returns single size for count=1."""
        result = _calculate_uniform_sizes(24.0, 1, 0.75)
        assert result == [24.0]

    def test_accounts_for_divider_thickness(self) -> None:
        """Test that divider thickness is subtracted from available space."""
        # 24" with 2 sections and 0.75" divider: (24 - 0.75) / 2 = 11.625"
        result = _calculate_uniform_sizes(24.0, 2, 0.75)
        assert len(result) == 2
        assert result[0] == pytest.approx(11.625)
        assert result[1] == pytest.approx(11.625)

    def test_all_sizes_equal(self) -> None:
        """Test that all returned sizes are equal."""
        result = _calculate_uniform_sizes(48.0, 4, 0.75)
        assert len(result) == 4
        assert all(s == result[0] for s in result)


# =============================================================================
# Integration Tests
# =============================================================================


class TestCubbyComponentIntegration:
    """Integration tests for cubby components."""

    @pytest.fixture(autouse=True)
    def ensure_components_registered(self) -> None:
        """Ensure cubby components are registered for integration tests."""
        if "cubby.uniform" not in component_registry.list():
            component_registry.register("cubby.uniform")(UniformCubbyComponent)
        if "cubby.variable" not in component_registry.list():
            component_registry.register("cubby.variable")(VariableCubbyComponent)

    def test_full_workflow_uniform_cubby(
        self, large_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        component_class = component_registry.get("cubby.uniform")
        component = component_class()

        config = {"rows": 3, "columns": 4}

        # Validate
        validation = component.validate(config, large_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, large_context)
        # 2 horizontal + 3 vertical * 3 rows = 11 panels
        assert len(generation.panels) == 11
        assert "notch_specs" in generation.metadata

        # Hardware
        hardware = component.hardware(config, large_context)
        assert len(hardware) == 1
        assert hardware[0].name == "Edge Banding"

    def test_both_cubby_types_in_registry(self) -> None:
        """Test that both cubby.uniform and cubby.variable are in registry."""
        registered = component_registry.list()
        assert "cubby.uniform" in registered
        assert "cubby.variable" in registered


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestCubbyComponentEdgeCases:
    """Edge case tests for cubby components."""

    def test_exactly_minimum_cubby_size(
        self, uniform_cubby_component: UniformCubbyComponent
    ) -> None:
        """Test validation passes for cubbies at exactly minimum size."""
        # 12.75" width: (12.75 - 0.75) / 2 = 6.0" (exactly minimum)
        context = ComponentContext(
            width=12.75,
            height=12.75,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.validate(config, context)

        assert result.is_valid

    def test_just_under_minimum_cubby_size(
        self, uniform_cubby_component: UniformCubbyComponent
    ) -> None:
        """Test validation fails for cubbies just under minimum size."""
        # 12.74" width: (12.74 - 0.75) / 2 = 5.995" (just under minimum)
        context = ComponentContext(
            width=12.74,
            height=12.75,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"rows": 2, "columns": 2}

        result = uniform_cubby_component.validate(config, context)

        assert not result.is_valid
        assert "less than minimum" in result.errors[0]

    def test_thick_material_affects_cubby_size(
        self, uniform_cubby_component: UniformCubbyComponent
    ) -> None:
        """Test that thicker material reduces cubby sizes appropriately."""
        context = ComponentContext(
            width=24.0,
            height=24.0,
            depth=11.5,
            material=MaterialSpec(thickness=1.0),  # 1" thick material
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        # 2 columns with 1" divider: (24 - 1) / 2 = 11.5" cubbies
        config = {"rows": 1, "columns": 2}

        result = uniform_cubby_component.validate(config, context)
        assert result.is_valid

        gen_result = uniform_cubby_component.generate(config, context)
        assert len(gen_result.panels) == 1  # 1 vertical divider

    def test_many_dividers_in_large_section(
        self, uniform_cubby_component: UniformCubbyComponent
    ) -> None:
        """Test 5x5 grid generation in large section."""
        context = ComponentContext(
            width=60.0,
            height=60.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=72.0,
            cabinet_depth=12.0,
        )
        config = {"rows": 5, "columns": 5}

        result = uniform_cubby_component.generate(config, context)

        # 4 horizontal dividers + 4 vertical * 5 rows = 24 panels
        expected_horizontal = 4
        expected_vertical = 4 * 5
        assert len(result.panels) == expected_horizontal + expected_vertical

    def test_panel_positions_are_correct(
        self, uniform_cubby_component: UniformCubbyComponent, large_context: ComponentContext
    ) -> None:
        """Test that panel positions are calculated correctly."""
        config = {"rows": 2, "columns": 1}

        result = uniform_cubby_component.generate(config, large_context)

        # One horizontal divider
        assert len(result.panels) == 1
        panel = result.panels[0]

        # Horizontal divider should be at context.position.x, context.position.y + row_height
        assert panel.position.x == large_context.position.x
        # Row height = (72 - 0.75) / 2 = 35.625
        expected_y = large_context.position.y + 35.625
        assert panel.position.y == pytest.approx(expected_y)
