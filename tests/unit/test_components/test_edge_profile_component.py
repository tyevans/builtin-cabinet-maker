"""Tests for EdgeProfileComponent implementation.

Tests for EdgeProfileComponent validation, generation, and hardware methods
following the Component protocol for FRD-12 decorative elements.
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    EdgeProfileComponent,
    EdgeProfileConfig,
    EdgeProfileMetadata,
    EdgeProfileType,
    GenerationResult,
    HardwareItem,
    ROUTER_BIT_RECOMMENDATIONS,
    ValidationResult,
    apply_edge_profile_metadata,
    component_registry,
    detect_visible_edges,
    validate_edge_profile,
)
from cabinets.domain.entities import Panel
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def edge_profile_component() -> EdgeProfileComponent:
    """Create an EdgeProfileComponent instance for testing."""
    return EdgeProfileComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 24" wide x 36" high section
    at position (0, 0) with 3/4" material.
    """
    return ComponentContext(
        width=24.0,
        height=36.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def thin_material_context() -> ComponentContext:
    """Create a ComponentContext with thin material for edge case testing.

    Returns a context with 1/2" material.
    """
    return ComponentContext(
        width=24.0,
        height=36.0,
        depth=12.0,
        material=MaterialSpec(thickness=0.5),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def sample_shelf_panel() -> Panel:
    """Create a sample shelf panel for metadata application testing."""
    return Panel(
        panel_type=PanelType.SHELF,
        width=24.0,
        height=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
    )


# =============================================================================
# Router Bit Recommendations Tests
# =============================================================================


class TestRouterBitRecommendations:
    """Tests for ROUTER_BIT_RECOMMENDATIONS constant."""

    def test_all_profile_types_have_recommendations(self) -> None:
        """Test that all EdgeProfileType values have router bit recommendations."""
        for profile_type in EdgeProfileType:
            assert profile_type in ROUTER_BIT_RECOMMENDATIONS

    def test_chamfer_recommendation(self) -> None:
        """Test chamfer router bit recommendation."""
        assert "45-degree" in ROUTER_BIT_RECOMMENDATIONS[EdgeProfileType.CHAMFER]

    def test_roundover_recommendation(self) -> None:
        """Test roundover router bit recommendation."""
        assert "Roundover" in ROUTER_BIT_RECOMMENDATIONS[EdgeProfileType.ROUNDOVER]

    def test_ogee_recommendation(self) -> None:
        """Test ogee router bit recommendation."""
        assert "Ogee" in ROUTER_BIT_RECOMMENDATIONS[EdgeProfileType.OGEE]

    def test_bevel_recommendation(self) -> None:
        """Test bevel router bit recommendation."""
        assert "Bevel" in ROUTER_BIT_RECOMMENDATIONS[EdgeProfileType.BEVEL]

    def test_cove_recommendation(self) -> None:
        """Test cove router bit recommendation."""
        assert "Cove" in ROUTER_BIT_RECOMMENDATIONS[EdgeProfileType.COVE]

    def test_roman_ogee_recommendation(self) -> None:
        """Test Roman ogee router bit recommendation."""
        assert "Roman ogee" in ROUTER_BIT_RECOMMENDATIONS[EdgeProfileType.ROMAN_OGEE]


# =============================================================================
# validate_edge_profile() Function Tests
# =============================================================================


class TestValidateEdgeProfile:
    """Tests for validate_edge_profile() function."""

    def test_valid_profile_no_errors_or_warnings(self) -> None:
        """Test that valid profile size returns no errors or warnings."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
        )

        errors, warnings = validate_edge_profile(config, material_thickness=0.75)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_profile_size_exceeding_half_thickness_generates_warning(self) -> None:
        """Test that profile size > half thickness generates warning."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.5,
        )

        errors, warnings = validate_edge_profile(config, material_thickness=0.75)

        assert len(errors) == 0
        assert len(warnings) == 1
        assert "exceeds half material thickness" in warnings[0]
        assert "0.375" in warnings[0]  # Half of 0.75

    def test_profile_size_exceeding_material_thickness_generates_error(self) -> None:
        """Test that profile size > material thickness generates error."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=1.0,
        )

        errors, warnings = validate_edge_profile(config, material_thickness=0.75)

        assert len(errors) == 1
        assert "exceeds material thickness" in errors[0]
        # Also generates warning since it's also > half thickness
        assert len(warnings) == 1

    def test_profile_size_exactly_at_half_thickness_no_warning(self) -> None:
        """Test that profile size exactly at half thickness has no warning."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.375,  # Exactly half of 0.75
        )

        errors, warnings = validate_edge_profile(config, material_thickness=0.75)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_profile_size_exactly_at_material_thickness_generates_warning(self) -> None:
        """Test that profile size exactly at material thickness generates warning but no error."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.75,
        )

        errors, warnings = validate_edge_profile(config, material_thickness=0.75)

        assert len(errors) == 0  # Not exceeding, so no error
        assert len(warnings) == 1  # But exceeds half, so warning


# =============================================================================
# detect_visible_edges() Function Tests
# =============================================================================


class TestDetectVisibleEdges:
    """Tests for detect_visible_edges() function."""

    def test_shelf_front_edge_always_visible(self) -> None:
        """Test that shelf panels always have front edge visible."""
        edges = detect_visible_edges(PanelType.SHELF)

        assert "front" in edges

    def test_shelf_left_edge_visible_when_at_left_cabinet_edge(self) -> None:
        """Test that shelf left edge is visible when at left cabinet edge."""
        edges = detect_visible_edges(PanelType.SHELF, is_left_edge=True)

        assert "front" in edges
        assert "left" in edges

    def test_shelf_right_edge_visible_when_at_right_cabinet_edge(self) -> None:
        """Test that shelf right edge is visible when at right cabinet edge."""
        edges = detect_visible_edges(PanelType.SHELF, is_right_edge=True)

        assert "front" in edges
        assert "right" in edges

    def test_shelf_both_edges_visible_when_at_both_cabinet_edges(self) -> None:
        """Test that shelf has left and right edges visible when at both edges."""
        edges = detect_visible_edges(PanelType.SHELF, is_left_edge=True, is_right_edge=True)

        assert "front" in edges
        assert "left" in edges
        assert "right" in edges

    def test_face_frame_stile_all_edges_visible(self) -> None:
        """Test that face frame stile has all edges visible."""
        edges = detect_visible_edges(PanelType.FACE_FRAME_STILE)

        assert "top" in edges
        assert "bottom" in edges
        assert "left" in edges
        assert "right" in edges

    def test_face_frame_rail_all_edges_visible(self) -> None:
        """Test that face frame rail has all edges visible."""
        edges = detect_visible_edges(PanelType.FACE_FRAME_RAIL)

        assert "top" in edges
        assert "bottom" in edges
        assert "left" in edges
        assert "right" in edges

    def test_valance_front_and_bottom_visible(self) -> None:
        """Test that valance has front and bottom edges visible."""
        edges = detect_visible_edges(PanelType.VALANCE)

        assert "front" in edges
        assert "bottom" in edges

    def test_default_panel_only_front_visible(self) -> None:
        """Test that default panel types have only front edge visible."""
        edges = detect_visible_edges(PanelType.TOP)

        assert edges == ["front"]


# =============================================================================
# apply_edge_profile_metadata() Function Tests
# =============================================================================


class TestApplyEdgeProfileMetadata:
    """Tests for apply_edge_profile_metadata() function."""

    def test_applies_metadata_to_panel(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that edge profile metadata is applied to panel."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        assert "edge_profile" in profiled_panel.metadata

    def test_preserves_panel_dimensions(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that panel dimensions are preserved."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        assert profiled_panel.width == sample_shelf_panel.width
        assert profiled_panel.height == sample_shelf_panel.height
        assert profiled_panel.panel_type == sample_shelf_panel.panel_type

    def test_metadata_contains_profile_type(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that metadata contains profile type."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.CHAMFER,
            size=0.25,
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        assert profiled_panel.metadata["edge_profile"]["profile_type"] == "chamfer"

    def test_metadata_contains_size(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that metadata contains profile size."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.375,
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        assert profiled_panel.metadata["edge_profile"]["size"] == 0.375

    def test_metadata_contains_edges(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that metadata contains edges list."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges=("top", "bottom"),
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        assert profiled_panel.metadata["edge_profile"]["edges"] == ["top", "bottom"]

    def test_metadata_contains_router_bit(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that metadata contains router bit recommendation."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.OGEE,
            size=0.25,
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        assert profiled_panel.metadata["edge_profile"]["router_bit"] == "Ogee bit"

    def test_auto_edges_uses_visible_edges(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that 'auto' edges uses detected visible edges."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges="auto",
        )

        profiled_panel = apply_edge_profile_metadata(sample_shelf_panel, config)

        # Shelf panel defaults to front edge
        assert "front" in profiled_panel.metadata["edge_profile"]["edges"]

    def test_explicit_visible_edges_override(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that explicit visible_edges parameter overrides auto detection."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges="auto",
        )

        profiled_panel = apply_edge_profile_metadata(
            sample_shelf_panel,
            config,
            visible_edges=["left", "right"],
        )

        assert profiled_panel.metadata["edge_profile"]["edges"] == ["left", "right"]

    def test_preserves_existing_metadata(
        self, sample_shelf_panel: Panel
    ) -> None:
        """Test that existing panel metadata is preserved."""
        # Create panel with existing metadata
        panel_with_metadata = Panel(
            panel_type=PanelType.SHELF,
            width=24.0,
            height=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            metadata={"existing_key": "existing_value"},
        )
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
        )

        profiled_panel = apply_edge_profile_metadata(panel_with_metadata, config)

        assert profiled_panel.metadata["existing_key"] == "existing_value"
        assert "edge_profile" in profiled_panel.metadata


# =============================================================================
# Registration Tests
# =============================================================================


class TestEdgeProfileComponentRegistration:
    """Tests for EdgeProfileComponent registration in the registry."""

    def test_edge_profile_is_registered(self) -> None:
        """Test that decorative.edge_profile is registered in the component registry."""
        assert "decorative.edge_profile" in component_registry.list()

    def test_get_returns_edge_profile_component_class(self) -> None:
        """Test that registry.get returns EdgeProfileComponent."""
        component_class = component_registry.get("decorative.edge_profile")
        assert component_class is EdgeProfileComponent

    def test_can_instantiate_from_registry(self) -> None:
        """Test that component can be instantiated from registry."""
        component_class = component_registry.get("decorative.edge_profile")
        component = component_class()
        assert isinstance(component, EdgeProfileComponent)


# =============================================================================
# Validation Tests
# =============================================================================


class TestEdgeProfileComponentValidation:
    """Tests for EdgeProfileComponent.validate()."""

    def test_validate_returns_ok_for_empty_config(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok when edge_profile config is empty."""
        config: dict = {}

        result = edge_profile_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_returns_ok_for_valid_config(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid config."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_warning_for_large_profile(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns warning for profile > half material thickness."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.5,  # > 0.375 (half of 0.75)
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert result.is_valid  # Still valid, just warning
        assert len(result.warnings) == 1
        assert "exceeds half material thickness" in result.warnings[0]

    def test_validate_returns_error_for_profile_exceeding_material(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns error for profile > material thickness."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 1.0,  # > 0.75 material thickness
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert not result.is_valid
        assert len(result.errors) == 1
        assert "exceeds material thickness" in result.errors[0]

    def test_validate_with_thin_material(
        self, edge_profile_component: EdgeProfileComponent, thin_material_context: ComponentContext
    ) -> None:
        """Test validation with thin material."""
        # With 0.5" material, half is 0.25"
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.3,  # > 0.25 (half of 0.5)
            }
        }

        result = edge_profile_component.validate(config, thin_material_context)

        assert result.is_valid
        assert len(result.warnings) == 1

    def test_validate_with_explicit_edges_list(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with explicit edges list."""
        config = {
            "edge_profile": {
                "profile_type": "chamfer",
                "size": 0.25,
                "edges": ["top", "bottom"],
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_with_auto_edges(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with 'auto' edges."""
        config = {
            "edge_profile": {
                "profile_type": "ogee",
                "size": 0.25,
                "edges": "auto",
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_with_invalid_profile_type(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test validation with invalid profile type."""
        config = {
            "edge_profile": {
                "profile_type": "invalid_profile",
                "size": 0.25,
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert not result.is_valid

    def test_validate_returns_validation_result_type(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ValidationResult type."""
        config: dict = {}

        result = edge_profile_component.validate(config, standard_context)

        assert isinstance(result, ValidationResult)

    def test_validate_all_profile_types(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that all profile types validate successfully."""
        for profile_type in EdgeProfileType:
            config = {
                "edge_profile": {
                    "profile_type": profile_type.value,
                    "size": 0.25,
                }
            }

            result = edge_profile_component.validate(config, standard_context)

            assert result.is_valid, f"Profile type {profile_type.value} failed validation"


# =============================================================================
# Generation Tests
# =============================================================================


class TestEdgeProfileComponentGeneration:
    """Tests for EdgeProfileComponent.generate()."""

    def test_generate_returns_empty_result_for_no_config(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns empty result when no edge_profile config."""
        config: dict = {}

        result = edge_profile_component.generate(config, standard_context)

        assert len(result.panels) == 0
        assert len(result.hardware) == 0

    def test_generate_returns_no_panels(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate does not produce any panels."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
            }
        }

        result = edge_profile_component.generate(config, standard_context)

        assert len(result.panels) == 0

    def test_generate_returns_metadata_with_config(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns metadata with edge_profile_config."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
            }
        }

        result = edge_profile_component.generate(config, standard_context)

        assert "edge_profile_config" in result.metadata
        assert result.metadata["edge_profile_config"]["profile_type"] == "roundover"
        assert result.metadata["edge_profile_config"]["size"] == 0.25

    def test_generate_returns_note_in_metadata(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns explanatory note in metadata."""
        config = {
            "edge_profile": {
                "profile_type": "chamfer",
                "size": 0.125,
            }
        }

        result = edge_profile_component.generate(config, standard_context)

        assert "note" in result.metadata
        assert "parent component" in result.metadata["note"]

    def test_generate_returns_generation_result_type(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns GenerationResult type."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
            }
        }

        result = edge_profile_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)


# =============================================================================
# Hardware Tests
# =============================================================================


class TestEdgeProfileComponentHardware:
    """Tests for EdgeProfileComponent.hardware()."""

    def test_hardware_returns_empty_list(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns empty list."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
            }
        }

        hardware = edge_profile_component.hardware(config, standard_context)

        assert hardware == []

    def test_hardware_returns_list_type(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware returns list type."""
        config: dict = {}

        hardware = edge_profile_component.hardware(config, standard_context)

        assert isinstance(hardware, list)


# =============================================================================
# EdgeProfileConfig Tests
# =============================================================================


class TestEdgeProfileConfig:
    """Tests for EdgeProfileConfig dataclass."""

    def test_valid_config_creation(self) -> None:
        """Test creating a valid EdgeProfileConfig."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
        )

        assert config.profile_type == EdgeProfileType.ROUNDOVER
        assert config.size == 0.25
        assert config.edges == "auto"

    def test_explicit_edges_tuple(self) -> None:
        """Test creating config with explicit edges tuple."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.CHAMFER,
            size=0.125,
            edges=("top", "left"),
        )

        assert config.edges == ("top", "left")

    def test_get_edges_returns_visible_edges_for_auto(self) -> None:
        """Test that get_edges returns visible_edges when edges='auto'."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges="auto",
        )

        result = config.get_edges(["front", "left"])

        assert result == ["front", "left"]

    def test_get_edges_returns_explicit_edges(self) -> None:
        """Test that get_edges returns explicit edges."""
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges=("top", "bottom"),
        )

        result = config.get_edges(["front", "left"])

        assert result == ["top", "bottom"]

    def test_invalid_size_raises_error(self) -> None:
        """Test that invalid size raises ValueError."""
        with pytest.raises(ValueError, match="size must be positive"):
            EdgeProfileConfig(
                profile_type=EdgeProfileType.ROUNDOVER,
                size=0,
            )

    def test_invalid_edge_name_raises_error(self) -> None:
        """Test that invalid edge name raises ValueError."""
        with pytest.raises(ValueError, match="invalid edge"):
            EdgeProfileConfig(
                profile_type=EdgeProfileType.ROUNDOVER,
                size=0.25,
                edges=("front", "invalid_edge"),
            )


# =============================================================================
# EdgeProfileMetadata Tests
# =============================================================================


class TestEdgeProfileMetadata:
    """Tests for EdgeProfileMetadata dataclass."""

    def test_valid_metadata_creation(self) -> None:
        """Test creating a valid EdgeProfileMetadata."""
        metadata = EdgeProfileMetadata(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges=("front",),
        )

        assert metadata.profile_type == EdgeProfileType.ROUNDOVER
        assert metadata.size == 0.25
        assert metadata.edges == ("front",)
        assert metadata.router_bit is None

    def test_metadata_with_router_bit(self) -> None:
        """Test creating metadata with router bit."""
        metadata = EdgeProfileMetadata(
            profile_type=EdgeProfileType.OGEE,
            size=0.375,
            edges=("top", "bottom"),
            router_bit="Ogee bit",
        )

        assert metadata.router_bit == "Ogee bit"


# =============================================================================
# Integration Tests
# =============================================================================


class TestEdgeProfileComponentIntegration:
    """Integration tests for EdgeProfileComponent."""

    def test_full_workflow(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        component_class = component_registry.get("decorative.edge_profile")
        component = component_class()

        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
                "edges": "auto",
            }
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 0  # Edge profiles don't generate panels

        # Verify metadata
        assert "edge_profile_config" in generation.metadata

        # Hardware (edge profiles = no hardware)
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_apply_profile_to_shelf_panel(self) -> None:
        """Test applying edge profile to a shelf panel."""
        panel = Panel(
            panel_type=PanelType.SHELF,
            width=24.0,
            height=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
        )

        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges="auto",
        )

        profiled_panel = apply_edge_profile_metadata(panel, config)

        assert "edge_profile" in profiled_panel.metadata
        assert profiled_panel.metadata["edge_profile"]["profile_type"] == "roundover"
        assert profiled_panel.metadata["edge_profile"]["size"] == 0.25
        assert "front" in profiled_panel.metadata["edge_profile"]["edges"]

    def test_validation_warning_detection(
        self, edge_profile_component: EdgeProfileComponent, standard_context: ComponentContext
    ) -> None:
        """Test that warnings are properly detected for large profiles."""
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.5,  # > 0.375 (half of 0.75)
            }
        }

        result = edge_profile_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.warnings) == 1
        assert "May weaken edge" in result.warnings[0]


# =============================================================================
# Manual Verification Test (from task spec)
# =============================================================================


class TestEdgeProfileManualVerification:
    """Manual verification test from task specification."""

    def test_task_spec_validation_example(self) -> None:
        """Test the validation example from the task specification."""
        errors, warnings = validate_edge_profile(
            EdgeProfileConfig(profile_type=EdgeProfileType.ROUNDOVER, size=0.5),
            material_thickness=0.75,
        )

        assert len(warnings) > 0  # 0.5 > 0.375 (half thickness)

    def test_task_spec_visible_edge_detection_example(self) -> None:
        """Test the visible edge detection example from the task specification."""
        edges = detect_visible_edges(PanelType.SHELF)

        assert "front" in edges

    def test_task_spec_metadata_application_example(self) -> None:
        """Test the metadata application example from the task specification."""
        panel = Panel(
            panel_type=PanelType.SHELF,
            width=24.0,
            height=0.75,
            material=MaterialSpec(thickness=0.75),
            position=Position(0, 0),
        )
        config = EdgeProfileConfig(
            profile_type=EdgeProfileType.ROUNDOVER,
            size=0.25,
            edges="auto",
        )

        profiled_panel = apply_edge_profile_metadata(panel, config)

        assert "edge_profile" in profiled_panel.metadata
        assert profiled_panel.metadata["edge_profile"]["profile_type"] == "roundover"

    def test_component_registered(self) -> None:
        """Test that decorative.edge_profile is in registry."""
        assert "decorative.edge_profile" in component_registry.list()

    def test_all_router_bit_recommendations_present(self) -> None:
        """Test that all profile types have router bit recommendations."""
        for profile_type in EdgeProfileType:
            assert profile_type in ROUTER_BIT_RECOMMENDATIONS
