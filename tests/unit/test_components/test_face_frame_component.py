"""Tests for FaceFrameComponent implementation.

Tests for FaceFrameComponent validation, generation, and hardware methods
following the Component protocol for FRD-12 decorative elements.
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    FaceFrameComponent,
    FaceFrameConfig,
    GenerationResult,
    HardwareItem,
    JoineryType,
    ValidationResult,
    component_registry,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def face_frame_component() -> FaceFrameComponent:
    """Create a FaceFrameComponent instance for testing."""
    return FaceFrameComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 48" wide x 84" high section
    at position (0, 0) within a 48x84x12 cabinet.
    """
    return ComponentContext(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def small_context() -> ComponentContext:
    """Create a small ComponentContext for edge case testing.

    Returns a context representing a 12" wide x 12" high section.
    """
    return ComponentContext(
        width=12.0,
        height=12.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=12.0,
        cabinet_height=12.0,
        cabinet_depth=12.0,
    )


# =============================================================================
# Registration Tests
# =============================================================================


class TestFaceFrameComponentRegistration:
    """Tests for FaceFrameComponent registration in the registry."""

    def test_face_frame_is_registered(self) -> None:
        """Test that decorative.face_frame is registered in the component registry."""
        assert "decorative.face_frame" in component_registry.list()

    def test_get_returns_face_frame_component_class(self) -> None:
        """Test that registry.get returns FaceFrameComponent."""
        component_class = component_registry.get("decorative.face_frame")
        assert component_class is FaceFrameComponent

    def test_can_instantiate_from_registry(self) -> None:
        """Test that component can be instantiated from registry."""
        component_class = component_registry.get("decorative.face_frame")
        component = component_class()
        assert isinstance(component, FaceFrameComponent)


# =============================================================================
# Validation Tests
# =============================================================================


class TestFaceFrameValidation:
    """Tests for FaceFrameComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns ok for valid config with defaults."""
        config: dict = {"face_frame": {}}

        result = face_frame_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_custom_stile_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns ok for custom stile width."""
        config = {"face_frame": {"stile_width": 2.0}}

        result = face_frame_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_ok_for_custom_rail_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns ok for custom rail width."""
        config = {"face_frame": {"rail_width": 2.5}}

        result = face_frame_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_error_for_negative_stile_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns error for negative stile width."""
        config = {"face_frame": {"stile_width": -1.0}}

        result = face_frame_component.validate(config, standard_context)

        assert not result.is_valid
        assert "stile_width must be positive" in result.errors

    def test_validate_returns_error_for_zero_stile_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns error for zero stile width."""
        config = {"face_frame": {"stile_width": 0}}

        result = face_frame_component.validate(config, standard_context)

        assert not result.is_valid
        assert "stile_width must be positive" in result.errors

    def test_validate_returns_error_for_negative_rail_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns error for negative rail width."""
        config = {"face_frame": {"rail_width": -1.0}}

        result = face_frame_component.validate(config, standard_context)

        assert not result.is_valid
        assert "rail_width must be positive" in result.errors

    def test_validate_returns_error_for_zero_rail_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns error for zero rail width."""
        config = {"face_frame": {"rail_width": 0}}

        result = face_frame_component.validate(config, standard_context)

        assert not result.is_valid
        assert "rail_width must be positive" in result.errors

    def test_validate_returns_error_for_stile_width_too_large(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns error for stile_width > cabinet_width/4."""
        # 48" cabinet width, max stile = 12"
        config = {"face_frame": {"stile_width": 13.0}}

        result = face_frame_component.validate(config, standard_context)

        assert not result.is_valid
        assert "too large for" in result.errors[0]
        assert "48.0" in result.errors[0]

    def test_validate_returns_error_for_rail_width_too_large(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns error for rail_width > cabinet_height/4."""
        # 84" cabinet height, max rail = 21"
        config = {"face_frame": {"rail_width": 22.0}}

        result = face_frame_component.validate(config, standard_context)

        assert not result.is_valid
        assert "too large for" in result.errors[0]
        assert "84.0" in result.errors[0]

    def test_validate_returns_error_for_opening_width_below_minimum(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test that validate returns error for opening width < 6\"."""
        # Use a 16" wide cabinet with 3" stiles (max = 4") = 10" opening
        # But 3" stiles would leave only 10" opening, so we need wider context
        # 14" width with 3" stiles = 8" opening (still above 6")
        # Use 12" width with 3" stiles = 6" opening (exactly at minimum)
        # But 12"/4 = 3" so stile_width 3" is at the limit
        # Let's use 10" width with 2.5" stiles (2.5 <= 2.5 limit) = 5" opening
        context = ComponentContext(
            width=10.0,
            height=24.0,  # Larger height to avoid height errors
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=10.0,
            cabinet_height=24.0,
            cabinet_depth=12.0,
        )
        # stile_width 2.5" is at the limit (10/4 = 2.5), opening = 10 - 5 = 5" (below 6")
        config = {"face_frame": {"stile_width": 2.5, "rail_width": 1.5}}

        result = face_frame_component.validate(config, context)

        assert not result.is_valid
        assert any(
            "Opening width" in e and 'less than 6" minimum' in e for e in result.errors
        )

    def test_validate_returns_error_for_opening_height_below_minimum(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test that validate returns error for opening height < 6\"."""
        # Use 24" wide cabinet (for width headroom) with 10" height
        # 10"/4 = 2.5" max rail, so use 2.5" rails for 5" opening (below 6")
        context = ComponentContext(
            width=24.0,  # Larger width to avoid width errors
            height=10.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=24.0,
            cabinet_height=10.0,
            cabinet_depth=12.0,
        )
        # rail_width 2.5" is at the limit (10/4 = 2.5), opening = 10 - 5 = 5" (below 6")
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.5}}

        result = face_frame_component.validate(config, context)

        assert not result.is_valid
        assert any(
            "Opening height" in e and 'less than 6" minimum' in e for e in result.errors
        )

    def test_validate_accepts_stile_at_max_quarter_width(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate accepts stile_width exactly at cabinet_width/4."""
        # 48" cabinet width, max stile = 12"
        config = {"face_frame": {"stile_width": 12.0}}

        result = face_frame_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_accepts_rail_at_max_quarter_height(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate accepts rail_width exactly at cabinet_height/4."""
        # 84" cabinet height, max rail = 21"
        config = {"face_frame": {"rail_width": 21.0}}

        result = face_frame_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_returns_validation_result_type(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that validate returns ValidationResult type."""
        config: dict = {}

        result = face_frame_component.validate(config, standard_context)

        assert isinstance(result, ValidationResult)


# =============================================================================
# Generation Tests
# =============================================================================


class TestFaceFrameGeneration:
    """Tests for FaceFrameComponent.generate()."""

    def test_generate_produces_four_panels(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that generate produces exactly 4 panels."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        assert len(result.panels) == 4

    def test_generate_produces_two_stiles(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that generate produces 2 stile panels."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        stiles = [
            p for p in result.panels if p.panel_type == PanelType.FACE_FRAME_STILE
        ]
        assert len(stiles) == 2

    def test_generate_produces_two_rails(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that generate produces 2 rail panels."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        rails = [p for p in result.panels if p.panel_type == PanelType.FACE_FRAME_RAIL]
        assert len(rails) == 2

    def test_generate_stile_dimensions(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that stiles have correct dimensions (full height)."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        stiles = [
            p for p in result.panels if p.panel_type == PanelType.FACE_FRAME_STILE
        ]
        for stile in stiles:
            assert stile.width == pytest.approx(1.5)
            assert stile.height == pytest.approx(84.0)  # Full height

    def test_generate_rail_dimensions(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that rails have correct dimensions (between stiles)."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        # Rail width = cabinet_width - (2 * stile_width) = 48 - 3 = 45
        expected_rail_width = 48.0 - (2 * 1.5)

        rails = [p for p in result.panels if p.panel_type == PanelType.FACE_FRAME_RAIL]
        for rail in rails:
            assert rail.width == pytest.approx(expected_rail_width)
            assert rail.height == pytest.approx(2.0)

    def test_generate_left_stile_position(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test left stile position is at context origin."""
        config = {"face_frame": {"stile_width": 1.5}}

        result = face_frame_component.generate(config, standard_context)

        left_stile = next(
            p
            for p in result.panels
            if p.panel_type == PanelType.FACE_FRAME_STILE
            and p.metadata.get("location") == "left"
        )
        assert left_stile.position.x == pytest.approx(0.0)
        assert left_stile.position.y == pytest.approx(0.0)

    def test_generate_right_stile_position(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test right stile position is at context.width - stile_width."""
        config = {"face_frame": {"stile_width": 1.5}}

        result = face_frame_component.generate(config, standard_context)

        right_stile = next(
            p
            for p in result.panels
            if p.panel_type == PanelType.FACE_FRAME_STILE
            and p.metadata.get("location") == "right"
        )
        assert right_stile.position.x == pytest.approx(48.0 - 1.5)
        assert right_stile.position.y == pytest.approx(0.0)

    def test_generate_top_rail_position(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test top rail position is at context.height - rail_width."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        top_rail = next(
            p
            for p in result.panels
            if p.panel_type == PanelType.FACE_FRAME_RAIL
            and p.metadata.get("location") == "top"
        )
        assert top_rail.position.x == pytest.approx(1.5)  # After left stile
        assert top_rail.position.y == pytest.approx(84.0 - 2.0)

    def test_generate_bottom_rail_position(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test bottom rail position is at context origin.y."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        bottom_rail = next(
            p
            for p in result.panels
            if p.panel_type == PanelType.FACE_FRAME_RAIL
            and p.metadata.get("location") == "bottom"
        )
        assert bottom_rail.position.x == pytest.approx(1.5)  # After left stile
        assert bottom_rail.position.y == pytest.approx(0.0)

    def test_generate_panel_material_thickness(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that panels use configured material thickness."""
        config = {"face_frame": {"material_thickness": 0.625}}

        result = face_frame_component.generate(config, standard_context)

        for panel in result.panels:
            assert panel.material.thickness == pytest.approx(0.625)

    def test_generate_panel_joinery_metadata(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that panels include joinery_type in metadata."""
        config = {"face_frame": {"joinery": "mortise_tenon"}}

        result = face_frame_component.generate(config, standard_context)

        for panel in result.panels:
            assert panel.metadata.get("joinery_type") == "mortise_tenon"

    def test_generate_returns_generation_result(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config: dict = {}

        result = face_frame_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)

    def test_generate_metadata_includes_opening_dimensions(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that metadata includes opening_width and opening_height."""
        config = {"face_frame": {"stile_width": 1.5, "rail_width": 2.0}}

        result = face_frame_component.generate(config, standard_context)

        assert "opening_width" in result.metadata
        assert "opening_height" in result.metadata
        # opening_width = 48 - (2 * 1.5) = 45
        assert result.metadata["opening_width"] == pytest.approx(45.0)
        # opening_height = 84 - (2 * 2.0) = 80
        assert result.metadata["opening_height"] == pytest.approx(80.0)

    def test_generate_metadata_includes_frame_dimensions(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that metadata includes stile_width and rail_width."""
        config = {"face_frame": {"stile_width": 2.0, "rail_width": 2.5}}

        result = face_frame_component.generate(config, standard_context)

        assert result.metadata["stile_width"] == pytest.approx(2.0)
        assert result.metadata["rail_width"] == pytest.approx(2.5)

    def test_generate_metadata_includes_joinery_type(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that metadata includes joinery_type."""
        config = {"face_frame": {"joinery": "dowel"}}

        result = face_frame_component.generate(config, standard_context)

        assert result.metadata["joinery_type"] == "dowel"

    def test_generate_with_offset_position(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test that panel positions respect context position offset."""
        context = ComponentContext(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(10.0, 5.0),  # Offset from origin
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"face_frame": {"stile_width": 1.5}}

        result = face_frame_component.generate(config, context)

        left_stile = next(
            p
            for p in result.panels
            if p.panel_type == PanelType.FACE_FRAME_STILE
            and p.metadata.get("location") == "left"
        )
        assert left_stile.position.x == pytest.approx(10.0)
        assert left_stile.position.y == pytest.approx(5.0)


# =============================================================================
# Hardware Tests
# =============================================================================


class TestFaceFrameHardware:
    """Tests for FaceFrameComponent.hardware()."""

    def test_hardware_pocket_screw_returns_8_screws(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that pocket_screw joinery returns 8 screws."""
        config = {"face_frame": {"joinery": "pocket_screw"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert len(hardware) == 1
        assert hardware[0].quantity == 8
        assert "Pocket Screw" in hardware[0].name

    def test_hardware_pocket_screw_sku(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that pocket_screw hardware has correct SKU."""
        config = {"face_frame": {"joinery": "pocket_screw"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert hardware[0].sku == "KJ-PS-125"

    def test_hardware_pocket_screw_notes(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that pocket_screw hardware has descriptive notes."""
        config = {"face_frame": {"joinery": "pocket_screw"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert "2 screws per corner" in hardware[0].notes
        assert "4 corners" in hardware[0].notes

    def test_hardware_dowel_returns_8_dowels(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that dowel joinery returns 8 dowel pins."""
        config = {"face_frame": {"joinery": "dowel"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert len(hardware) == 1
        assert hardware[0].quantity == 8
        assert "Dowel Pin" in hardware[0].name

    def test_hardware_dowel_sku(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that dowel hardware has correct SKU."""
        config = {"face_frame": {"joinery": "dowel"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert hardware[0].sku == "DP-375-2"

    def test_hardware_dowel_notes(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that dowel hardware has descriptive notes."""
        config = {"face_frame": {"joinery": "dowel"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert "2 dowels per corner" in hardware[0].notes
        assert "4 corners" in hardware[0].notes

    def test_hardware_mortise_tenon_returns_no_hardware(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that mortise_tenon joinery returns empty hardware list."""
        config = {"face_frame": {"joinery": "mortise_tenon"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert len(hardware) == 0

    def test_hardware_default_joinery_is_pocket_screw(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that default joinery (pocket_screw) is used when not specified."""
        config: dict = {}

        hardware = face_frame_component.hardware(config, standard_context)

        assert len(hardware) == 1
        assert "Pocket Screw" in hardware[0].name

    def test_hardware_returns_list_of_hardware_items(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that hardware returns list of HardwareItem objects."""
        config = {"face_frame": {"joinery": "pocket_screw"}}

        hardware = face_frame_component.hardware(config, standard_context)

        assert isinstance(hardware, list)
        for item in hardware:
            assert isinstance(item, HardwareItem)

    def test_hardware_included_in_generate_result(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that generate() includes hardware in the result."""
        config = {"face_frame": {"joinery": "dowel"}}

        result = face_frame_component.generate(config, standard_context)

        assert len(result.hardware) == 1
        assert result.hardware[0].quantity == 8


# =============================================================================
# Config Parsing Tests
# =============================================================================


class TestFaceFrameConfigParsing:
    """Tests for FaceFrameComponent._parse_config()."""

    def test_parse_config_defaults(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test that default values are applied when config is empty."""
        config: dict = {}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.stile_width == 1.5
        assert frame_config.rail_width == 1.5
        assert frame_config.joinery == JoineryType.POCKET_SCREW
        assert frame_config.material_thickness == 0.75

    def test_parse_config_custom_stile_width(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test custom stile_width is parsed correctly."""
        config = {"face_frame": {"stile_width": 2.0}}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.stile_width == 2.0

    def test_parse_config_custom_rail_width(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test custom rail_width is parsed correctly."""
        config = {"face_frame": {"rail_width": 2.5}}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.rail_width == 2.5

    def test_parse_config_pocket_screw_joinery(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test pocket_screw joinery is parsed correctly."""
        config = {"face_frame": {"joinery": "pocket_screw"}}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.joinery == JoineryType.POCKET_SCREW

    def test_parse_config_mortise_tenon_joinery(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test mortise_tenon joinery is parsed correctly."""
        config = {"face_frame": {"joinery": "mortise_tenon"}}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.joinery == JoineryType.MORTISE_TENON

    def test_parse_config_dowel_joinery(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test dowel joinery is parsed correctly."""
        config = {"face_frame": {"joinery": "dowel"}}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.joinery == JoineryType.DOWEL

    def test_parse_config_custom_material_thickness(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test custom material_thickness is parsed correctly."""
        config = {"face_frame": {"material_thickness": 0.625}}

        frame_config = face_frame_component._parse_config(config)

        assert frame_config.material_thickness == 0.625

    def test_parse_config_returns_face_frame_config(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test that _parse_config returns FaceFrameConfig instance."""
        config: dict = {}

        frame_config = face_frame_component._parse_config(config)

        assert isinstance(frame_config, FaceFrameConfig)


# =============================================================================
# Integration Tests
# =============================================================================


class TestFaceFrameComponentIntegration:
    """Integration tests for FaceFrameComponent with the registry."""

    def test_full_workflow(self, standard_context: ComponentContext) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        component_class = component_registry.get("decorative.face_frame")
        component = component_class()

        config = {
            "face_frame": {
                "stile_width": 1.5,
                "rail_width": 2.0,
                "joinery": "mortise_tenon",
            }
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 4

        # Verify panel types
        stiles = [
            p for p in generation.panels if p.panel_type == PanelType.FACE_FRAME_STILE
        ]
        rails = [
            p for p in generation.panels if p.panel_type == PanelType.FACE_FRAME_RAIL
        ]
        assert len(stiles) == 2
        assert len(rails) == 2

        # Verify metadata
        assert "opening_width" in generation.metadata
        assert "opening_height" in generation.metadata

        # Hardware (mortise_tenon = no hardware)
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 0

    def test_workflow_with_pocket_screws(
        self, standard_context: ComponentContext
    ) -> None:
        """Test workflow with pocket screw joinery."""
        component = FaceFrameComponent()

        config = {"face_frame": {"joinery": "pocket_screw"}}

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 4
        assert len(generation.hardware) == 1
        assert generation.hardware[0].quantity == 8

    def test_workflow_with_dowels(self, standard_context: ComponentContext) -> None:
        """Test workflow with dowel joinery."""
        component = FaceFrameComponent()

        config = {"face_frame": {"joinery": "dowel"}}

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.hardware) == 1
        assert "Dowel" in generation.hardware[0].name


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestFaceFrameEdgeCases:
    """Edge case tests for FaceFrameComponent."""

    def test_minimum_valid_opening(
        self, face_frame_component: FaceFrameComponent
    ) -> None:
        """Test face frame with minimum valid 6\" opening."""
        # 12" cabinet with 3" stiles = 6" opening (exactly minimum)
        context = ComponentContext(
            width=12.0,
            height=12.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=12.0,
            cabinet_height=12.0,
            cabinet_depth=12.0,
        )
        # stile_width 3" -> opening = 12 - 6 = 6" (exactly minimum)
        # rail_width 3" -> opening = 12 - 6 = 6" (exactly minimum)
        config = {"face_frame": {"stile_width": 3.0, "rail_width": 3.0}}

        validation = face_frame_component.validate(config, context)

        assert validation.is_valid

    def test_various_joinery_types_in_metadata(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that all joinery types are correctly recorded in panel metadata."""
        for joinery in ["pocket_screw", "mortise_tenon", "dowel"]:
            config = {"face_frame": {"joinery": joinery}}

            result = face_frame_component.generate(config, standard_context)

            for panel in result.panels:
                assert panel.metadata.get("joinery_type") == joinery

    def test_panel_locations_in_metadata(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that all panels have correct location in metadata."""
        config: dict = {}

        result = face_frame_component.generate(config, standard_context)

        locations = [p.metadata.get("location") for p in result.panels]
        assert "left" in locations
        assert "right" in locations
        assert "top" in locations
        assert "bottom" in locations

    def test_empty_face_frame_config_uses_defaults(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that empty face_frame config uses all defaults."""
        config = {"face_frame": {}}

        result = face_frame_component.generate(config, standard_context)

        # Default stile_width = 1.5, so opening_width = 48 - 3 = 45
        assert result.metadata["opening_width"] == pytest.approx(45.0)
        # Default rail_width = 1.5, so opening_height = 84 - 3 = 81
        assert result.metadata["opening_height"] == pytest.approx(81.0)

    def test_no_face_frame_key_uses_defaults(
        self,
        face_frame_component: FaceFrameComponent,
        standard_context: ComponentContext,
    ) -> None:
        """Test that missing face_frame key uses all defaults."""
        config: dict = {}  # No face_frame key at all

        result = face_frame_component.generate(config, standard_context)

        assert result.metadata["stile_width"] == pytest.approx(1.5)
        assert result.metadata["rail_width"] == pytest.approx(1.5)
        assert result.metadata["joinery_type"] == "pocket_screw"


# =============================================================================
# Manual Verification Test (from task spec)
# =============================================================================


class TestFaceFrameManualVerification:
    """Manual verification test from task specification."""

    def test_task_spec_example(self) -> None:
        """Test the example from the task specification."""
        # Create context
        context = ComponentContext(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        # Create and test component
        component = FaceFrameComponent()

        # Validate
        config = {
            "face_frame": {
                "stile_width": 1.5,
                "rail_width": 2.0,
                "joinery": "mortise_tenon",
            }
        }
        result = component.validate(config, context)
        assert result.is_valid
        assert len(result.errors) == 0

        # Generate
        gen_result = component.generate(config, context)
        assert len(gen_result.panels) == 4

        # Check panel types and dimensions
        stiles = [
            p for p in gen_result.panels if p.panel_type == PanelType.FACE_FRAME_STILE
        ]
        rails = [
            p for p in gen_result.panels if p.panel_type == PanelType.FACE_FRAME_RAIL
        ]

        assert len(stiles) == 2
        assert len(rails) == 2

        for stile in stiles:
            assert stile.width == pytest.approx(1.5)
            assert stile.height == pytest.approx(84.0)

        for rail in rails:
            assert rail.width == pytest.approx(45.0)  # 48 - 2 * 1.5
            assert rail.height == pytest.approx(2.0)

        # Hardware (mortise_tenon = 0)
        assert len(gen_result.hardware) == 0

        # Opening dimensions
        assert gen_result.metadata["opening_width"] == pytest.approx(45.0)  # 48 - 3
        assert gen_result.metadata["opening_height"] == pytest.approx(80.0)  # 84 - 4
