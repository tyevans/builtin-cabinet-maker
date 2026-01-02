"""Unit tests for countertop surface component (FRD-22).

Tests for:
- CountertopSurfaceComponent (countertop.surface)
- Component registration verification
- Validation of thickness, overhangs, and edge treatments
- Generation of countertop panels, waterfall edges, and hardware
"""

import importlib

import pytest

from cabinets.domain.components import (
    ComponentContext,
    component_registry,
)
from cabinets.domain.components.countertop import (
    DEFAULT_THICKNESS,
    MAX_SUPPORTED_OVERHANG,
    MAX_THICKNESS,
    MAX_UNSUPPORTED_OVERHANG,
    MIN_BRACKET_DEPTH,
    MIN_BRACKET_WIDTH,
    MIN_THICKNESS,
    SUPPORT_BRACKET_SPACING,
    CountertopSurfaceComponent,
    OverhangSpec,
)
from cabinets.domain.value_objects import (
    CountertopEdgeType,
    MaterialSpec,
    PanelType,
    Position,
)


@pytest.fixture(autouse=True)
def ensure_components_registered() -> None:
    """Ensure countertop component is registered before each test.

    The registry tests clear the registry, which removes all registered
    components. This fixture re-imports the countertop module to
    re-register the component if it has been cleared.
    """
    if "countertop.surface" not in component_registry.list():
        import cabinets.domain.components.countertop

        importlib.reload(cabinets.domain.components.countertop)


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard component context for testing."""
    return ComponentContext(
        width=48.0,
        height=34.5,
        depth=24.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 34.5),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


@pytest.fixture
def wide_context() -> ComponentContext:
    """Create a wide (>96") component context for span testing."""
    return ComponentContext(
        width=120.0,
        height=34.5,
        depth=24.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 34.5),
        section_index=0,
        cabinet_width=120.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


# --- OverhangSpec Tests ---


class TestOverhangSpec:
    """Tests for OverhangSpec dataclass."""

    def test_default_values(self) -> None:
        """Test default overhang values."""
        spec = OverhangSpec()
        assert spec.front == 1.0
        assert spec.left == 0.0
        assert spec.right == 0.0
        assert spec.back == 0.0

    def test_custom_values(self) -> None:
        """Test custom overhang values."""
        spec = OverhangSpec(front=2.0, left=1.0, right=1.0, back=0.5)
        assert spec.front == 2.0
        assert spec.left == 1.0
        assert spec.right == 1.0
        assert spec.back == 0.5

    def test_immutable(self) -> None:
        """Test that OverhangSpec is immutable (frozen)."""
        spec = OverhangSpec()
        with pytest.raises(AttributeError):
            spec.front = 5.0  # type: ignore[misc]


# --- Component Registration Tests ---


class TestCountertopRegistration:
    """Tests for countertop component registration."""

    def test_component_is_registered(self) -> None:
        """Test that countertop.surface is registered in the registry."""
        components = component_registry.list()
        assert "countertop.surface" in components

    def test_component_class_retrieval(self) -> None:
        """Test retrieving the component class from registry."""
        component_cls = component_registry.get("countertop.surface")
        assert component_cls is not None
        assert component_cls.__name__ == "CountertopSurfaceComponent"

    def test_component_has_required_methods(self) -> None:
        """Test that the component has all required protocol methods."""
        component = CountertopSurfaceComponent()
        assert hasattr(component, "validate")
        assert hasattr(component, "generate")
        assert hasattr(component, "hardware")
        assert callable(component.validate)
        assert callable(component.generate)
        assert callable(component.hardware)


# --- Validation Tests ---


class TestCountertopValidation:
    """Tests for CountertopSurfaceComponent.validate() method."""

    def test_valid_configuration(self, standard_context: ComponentContext) -> None:
        """Test that a valid configuration passes validation."""
        component = CountertopSurfaceComponent()
        config = {
            "thickness": 1.0,
            "front_overhang": 1.0,
            "edge_treatment": "square",
        }

        result = component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_thickness_too_thin_error(self, standard_context: ComponentContext) -> None:
        """Test that thickness below minimum produces error."""
        component = CountertopSurfaceComponent()
        config = {
            "thickness": 0.25,  # Below MIN_THICKNESS (0.5")
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "too thin" in result.errors[0].lower()
        assert str(MIN_THICKNESS) in result.errors[0]

    def test_thickness_too_thick_error(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that thickness above maximum produces error."""
        component = CountertopSurfaceComponent()
        config = {
            "thickness": 3.0,  # Above MAX_THICKNESS (2.0")
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "exceeds maximum" in result.errors[0].lower()
        assert str(MAX_THICKNESS) in result.errors[0]

    def test_large_overhang_without_brackets_warning(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that overhang >12" without brackets produces warning."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,  # Above MAX_UNSUPPORTED_OVERHANG (12")
            "support_brackets": False,
        }

        result = component.validate(config, standard_context)
        assert result.is_valid  # Still valid, just a warning
        assert len(result.warnings) == 1
        assert "requires support brackets" in result.warnings[0].lower()

    def test_large_overhang_with_brackets_no_warning(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that overhang >12" with brackets does not produce warning."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,  # Above MAX_UNSUPPORTED_OVERHANG (12")
            "support_brackets": True,
        }

        result = component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_excessive_overhang_error(self, standard_context: ComponentContext) -> None:
        """Test that overhang >24" produces error."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 30.0,  # Above MAX_SUPPORTED_OVERHANG (24")
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "exceeds safe span" in result.errors[0].lower()
        assert str(MAX_SUPPORTED_OVERHANG) in result.errors[0]

    def test_invalid_edge_treatment_error(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that invalid edge treatment produces error."""
        component = CountertopSurfaceComponent()
        config = {
            "edge_treatment": "curved",  # Invalid value
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "invalid edge treatment" in result.errors[0].lower()
        assert "curved" in result.errors[0].lower()

    def test_all_valid_edge_treatments(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that all valid edge treatments pass validation."""
        component = CountertopSurfaceComponent()

        for edge_type in CountertopEdgeType:
            config = {
                "edge_treatment": edge_type.value,
                "front_overhang": 1.0,  # Required for waterfall
            }
            result = component.validate(config, standard_context)
            assert result.is_valid, (
                f"Edge treatment '{edge_type.value}' should be valid"
            )

    def test_waterfall_without_front_overhang_error(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that waterfall edge without front overhang produces error."""
        component = CountertopSurfaceComponent()
        config = {
            "edge_treatment": "waterfall",
            "front_overhang": 0.5,  # Less than required 1.0"
        }

        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "waterfall" in result.errors[0].lower()
        assert "front overhang" in result.errors[0].lower()

    def test_long_span_without_support_warning(
        self, wide_context: ComponentContext
    ) -> None:
        """Test that long span (>96") without support produces warning."""
        component = CountertopSurfaceComponent()
        config = {
            "intermediate_support": False,
        }

        result = component.validate(config, wide_context)
        assert result.is_valid  # Still valid, just a warning
        assert len(result.warnings) == 1
        assert "may sag" in result.warnings[0].lower()

    def test_long_span_with_support_no_warning(
        self, wide_context: ComponentContext
    ) -> None:
        """Test that long span (>96") with support does not produce warning."""
        component = CountertopSurfaceComponent()
        config = {
            "intermediate_support": True,
        }

        result = component.validate(config, wide_context)
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_large_left_overhang_warning(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that large left overhang produces warning."""
        component = CountertopSurfaceComponent()
        config = {
            "left_overhang": 8.0,  # Above 6.0" threshold
        }

        result = component.validate(config, standard_context)
        assert result.is_valid
        assert any("left overhang" in w.lower() for w in result.warnings)

    def test_large_right_overhang_warning(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that large right overhang produces warning."""
        component = CountertopSurfaceComponent()
        config = {
            "right_overhang": 8.0,  # Above 6.0" threshold
        }

        result = component.validate(config, standard_context)
        assert result.is_valid
        assert any("right overhang" in w.lower() for w in result.warnings)


# --- Generation Tests ---


class TestCountertopGeneration:
    """Tests for CountertopSurfaceComponent.generate() method."""

    def test_basic_countertop_panel_generation(
        self, standard_context: ComponentContext
    ) -> None:
        """Test basic countertop panel generation."""
        component = CountertopSurfaceComponent()
        config = {}  # Use all defaults

        result = component.generate(config, standard_context)

        assert len(result.panels) == 1
        panel = result.panels[0]
        assert panel.panel_type == PanelType.COUNTERTOP
        assert panel.metadata["component"] == "countertop.surface"
        assert panel.metadata["is_countertop"] is True

    def test_panel_dimensions_with_overhangs(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that panel dimensions include overhangs."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 2.0,
            "left_overhang": 1.0,
            "right_overhang": 1.0,
            "back_overhang": 0.5,
        }

        result = component.generate(config, standard_context)

        panel = result.panels[0]
        # Width should include left and right overhangs
        expected_width = standard_context.width + 1.0 + 1.0  # 48 + 2 = 50
        assert panel.width == expected_width

        # Height (depth in 2D) should include front and back overhangs
        expected_depth = standard_context.depth + 2.0 + 0.5  # 24 + 2.5 = 26.5
        assert panel.height == expected_depth

    def test_panel_position_offset_stored_in_metadata(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that position offsets for overhangs are stored in metadata."""
        component = CountertopSurfaceComponent()
        config = {
            "left_overhang": 3.0,
            "back_overhang": 1.0,
        }

        result = component.generate(config, standard_context)

        panel = result.panels[0]
        # Position coordinates are clamped to non-negative
        # Offsets are stored in metadata for downstream processing
        assert panel.position.x >= 0
        assert panel.position.y >= 0
        assert panel.metadata["position_offset_x"] == -3.0
        assert panel.metadata["position_offset_y"] == -1.0

    def test_waterfall_edge_generates_two_panels(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that waterfall edge treatment generates two panels."""
        component = CountertopSurfaceComponent()
        config = {
            "edge_treatment": "waterfall",
            "front_overhang": 1.5,
        }

        result = component.generate(config, standard_context)

        assert len(result.panels) == 2
        panel_types = [p.panel_type for p in result.panels]
        assert PanelType.COUNTERTOP in panel_types
        assert PanelType.WATERFALL_EDGE in panel_types

        # Check waterfall panel metadata
        waterfall_panel = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ][0]
        assert waterfall_panel.metadata["is_waterfall_edge"] is True
        assert waterfall_panel.metadata["parent_panel"] == "countertop"

    def test_waterfall_edge_height(self, standard_context: ComponentContext) -> None:
        """Test that waterfall edge uses configured height."""
        component = CountertopSurfaceComponent()
        config = {
            "edge_treatment": "waterfall",
            "front_overhang": 1.5,
            "waterfall_height": 30.0,
        }

        result = component.generate(config, standard_context)

        waterfall_panel = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ][0]
        assert waterfall_panel.height == 30.0

    def test_waterfall_edge_default_height(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that waterfall edge uses default height (34.5)."""
        component = CountertopSurfaceComponent()
        config = {
            "edge_treatment": "waterfall",
            "front_overhang": 1.5,
        }

        result = component.generate(config, standard_context)

        waterfall_panel = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ][0]
        assert waterfall_panel.height == 34.5

    def test_support_brackets_generated_for_large_overhang(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that support brackets are generated for overhangs >12"."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,  # Above MAX_UNSUPPORTED_OVERHANG
            "support_brackets": True,
        }

        result = component.generate(config, standard_context)

        hardware_names = [h.name for h in result.hardware]
        assert any("Support Bracket" in name for name in hardware_names)
        assert any("Mounting Screw" in name for name in hardware_names)

    def test_support_brackets_count(self, standard_context: ComponentContext) -> None:
        """Test support bracket count calculation."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,
            "support_brackets": True,
        }

        result = component.generate(config, standard_context)

        bracket_hardware = [h for h in result.hardware if "Support Bracket" in h.name][
            0
        ]
        # Width is 48", spacing is 24", so should have 3 brackets (48/24 + 1)
        assert bracket_hardware.quantity == 3

    def test_support_brackets_minimum_two(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that minimum of 2 support brackets are generated."""
        # Create a narrow context
        narrow_context = ComponentContext(
            width=18.0,  # Less than SUPPORT_BRACKET_SPACING
            height=34.5,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 34.5),
            section_index=0,
            cabinet_width=18.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,
            "support_brackets": True,
        }

        result = component.generate(config, narrow_context)

        bracket_hardware = [h for h in result.hardware if "Support Bracket" in h.name][
            0
        ]
        assert bracket_hardware.quantity >= 2

    def test_edge_banding_calculated_correctly(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that edge banding is calculated for visible edges."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 1.0,  # Front edge visible
            "left_overhang": 0.5,  # Left edge visible
            "right_overhang": 0.0,  # Right edge not visible
            "edge_treatment": "square",
        }

        result = component.generate(config, standard_context)

        edge_banding = [h for h in result.hardware if "Edge Banding" in h.name]
        assert len(edge_banding) == 1

        # Check that notes include front and left edges
        notes = edge_banding[0].notes
        assert "front" in notes.lower()
        assert "left" in notes.lower()

    def test_no_edge_banding_for_waterfall(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that no edge banding is generated for waterfall edge."""
        component = CountertopSurfaceComponent()
        config = {
            "edge_treatment": "waterfall",
            "front_overhang": 1.5,
        }

        result = component.generate(config, standard_context)

        edge_banding = [h for h in result.hardware if "Edge Banding" in h.name]
        assert len(edge_banding) == 0

    def test_metadata_includes_all_dimensions(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes all dimension information."""
        component = CountertopSurfaceComponent()
        # Use small overhangs that won't produce edge banding warnings
        config = {
            "thickness": 1.5,
            "front_overhang": 1.0,  # No extra edge banding warnings
            "left_overhang": 0.0,
            "right_overhang": 0.0,
            "back_overhang": 0.0,
            "edge_treatment": "bullnose",
        }

        result = component.generate(config, standard_context)

        assert result.metadata["edge_treatment"] == "bullnose"
        assert result.metadata["thickness"] == 1.5
        assert result.metadata["total_width"] == 48.0  # 48 + 0 + 0
        assert result.metadata["total_depth"] == 25.0  # 24 + 1 + 0
        assert result.metadata["overhangs"]["front"] == 1.0
        assert result.metadata["overhangs"]["left"] == 0.0
        assert result.metadata["overhangs"]["right"] == 0.0
        assert result.metadata["overhangs"]["back"] == 0.0

    def test_custom_material_specification(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that custom material specification is applied."""
        component = CountertopSurfaceComponent()
        config = {
            "thickness": 1.25,
            # Use a valid MaterialType enum value
            "material": {"type": "mdf"},
        }

        result = component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.material.thickness == 1.25
        assert panel.material.material_type.value == "mdf"

    def test_panel_metadata_includes_overhangs(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that panel metadata includes overhang values."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 2.0,
            "left_overhang": 0.0,  # Use 0 to avoid position issues
        }

        result = component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.metadata["front_overhang"] == 2.0
        assert panel.metadata["left_overhang"] == 0.0
        assert panel.metadata["zone"] == "base"


# --- Hardware Method Tests ---


class TestCountertopHardware:
    """Tests for CountertopSurfaceComponent.hardware() method."""

    def test_hardware_returns_same_as_generate(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns same items as generate()."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,
            "support_brackets": True,
        }

        hardware = component.hardware(config, standard_context)
        result = component.generate(config, standard_context)

        assert len(hardware) == len(result.hardware)
        for i, item in enumerate(hardware):
            assert item.name == result.hardware[i].name
            assert item.quantity == result.hardware[i].quantity

    def test_hardware_includes_all_items(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes brackets, screws, and edge banding."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,
            "left_overhang": 0.0,  # Use 0 to avoid position issues
            "support_brackets": True,
            "edge_treatment": "square",
        }

        hardware = component.hardware(config, standard_context)

        names = [h.name for h in hardware]
        assert any("Support Bracket" in name for name in names)
        assert any("Screw" in name for name in names)
        assert any("Edge Banding" in name for name in names)


# --- Constants Tests ---


class TestCountertopConstants:
    """Tests for countertop module constants."""

    def test_thickness_constants(self) -> None:
        """Test thickness constant values."""
        assert MIN_THICKNESS == 0.5
        assert MAX_THICKNESS == 2.0
        assert DEFAULT_THICKNESS == 1.0

    def test_overhang_constants(self) -> None:
        """Test overhang constant values."""
        assert MAX_UNSUPPORTED_OVERHANG == 12.0
        assert MAX_SUPPORTED_OVERHANG == 24.0

    def test_bracket_constants(self) -> None:
        """Test bracket constant values."""
        assert SUPPORT_BRACKET_SPACING == 24.0
        assert MIN_BRACKET_WIDTH == 12.0
        assert MIN_BRACKET_DEPTH == 8.0

    def test_module_exports_constants(self) -> None:
        """Test that constants are exported from module."""
        from cabinets.domain.components.countertop import (
            DEFAULT_THICKNESS,
        )

        # Just verify they are importable
        assert DEFAULT_THICKNESS is not None


# --- Edge Cases ---


class TestCountertopEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_overhang_all_sides(self, standard_context: ComponentContext) -> None:
        """Test countertop with no overhangs."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 0.0,
            "left_overhang": 0.0,
            "right_overhang": 0.0,
            "back_overhang": 0.0,
        }

        result = component.generate(config, standard_context)

        panel = result.panels[0]
        assert panel.width == standard_context.width
        assert panel.height == standard_context.depth

        # No edge banding since no visible edges
        edge_banding = [h for h in result.hardware if "Edge Banding" in h.name]
        assert len(edge_banding) == 0

    def test_minimum_valid_thickness(self, standard_context: ComponentContext) -> None:
        """Test countertop at minimum valid thickness."""
        component = CountertopSurfaceComponent()
        config = {
            "thickness": MIN_THICKNESS,  # 0.5"
        }

        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_maximum_valid_thickness(self, standard_context: ComponentContext) -> None:
        """Test countertop at maximum valid thickness."""
        component = CountertopSurfaceComponent()
        config = {
            "thickness": MAX_THICKNESS,  # 2.0"
        }

        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_maximum_supported_overhang(
        self, standard_context: ComponentContext
    ) -> None:
        """Test countertop at maximum supported overhang."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": MAX_SUPPORTED_OVERHANG,  # 24"
            "support_brackets": True,
        }

        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_defaults_used_when_config_empty(
        self, standard_context: ComponentContext
    ) -> None:
        """Test that defaults are applied when config is empty."""
        component = CountertopSurfaceComponent()
        config = {}

        result = component.generate(config, standard_context)

        # Check defaults are applied
        assert result.metadata["thickness"] == DEFAULT_THICKNESS
        assert result.metadata["edge_treatment"] == "square"
        assert result.metadata["overhangs"]["front"] == 1.0
        assert result.metadata["overhangs"]["left"] == 0.0
        assert result.metadata["overhangs"]["right"] == 0.0
        assert result.metadata["overhangs"]["back"] == 0.0

    def test_bracket_size_customization(
        self, standard_context: ComponentContext
    ) -> None:
        """Test custom bracket size in hardware."""
        component = CountertopSurfaceComponent()
        config = {
            "front_overhang": 15.0,
            "support_brackets": True,
            "bracket_size": (15, 10),  # Use integers for cleaner formatting
        }

        result = component.generate(config, standard_context)

        bracket_hardware = [h for h in result.hardware if "Support Bracket" in h.name][
            0
        ]
        # Check that the bracket name includes the size info
        assert "15" in bracket_hardware.name
        assert "10" in bracket_hardware.name
