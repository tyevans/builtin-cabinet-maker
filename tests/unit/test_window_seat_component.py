"""Tests for WindowSeatStorageComponent and MullionFillerComponent (FRD-23).

This module tests the window seat storage component and mullion filler
component for bay window alcove built-ins.
"""

import importlib

import pytest

from cabinets.domain.components import (
    ACCESS_DRAWERS,
    ACCESS_FRONT_DOORS,
    ACCESS_HINGED_TOP,
    DEFAULT_SEAT_HEIGHT,
    MAX_SEAT_HEIGHT,
    MIN_SEAT_DEPTH,
    MIN_SEAT_HEIGHT,
    MIN_SEAT_WIDTH,
    SEAT_THICKNESS,
    VALID_ACCESS_TYPES,
    MullionFillerComponent,
    WindowSeatStorageComponent,
    component_registry,
)
from cabinets.domain.components.context import ComponentContext
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture(autouse=True)
def ensure_components_registered() -> None:
    """Ensure window seat components are registered before each test.

    The registry tests clear the registry, which removes all registered
    components. This fixture re-imports the window_seat module to
    re-register the components if they have been cleared.
    """
    if "windowseat.storage" not in component_registry.list():
        import cabinets.domain.components.window_seat

        importlib.reload(cabinets.domain.components.window_seat)


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Standard 3/4" plywood material."""
    return MaterialSpec.standard_3_4()


@pytest.fixture
def standard_context(standard_material: MaterialSpec) -> ComponentContext:
    """Standard component context for window seat testing."""
    return ComponentContext(
        width=36.0,
        height=84.0,
        depth=18.0,
        material=standard_material,
        position=Position(0, 0),
        section_index=0,
        cabinet_width=36.0,
        cabinet_height=84.0,
        cabinet_depth=18.0,
    )


@pytest.fixture
def narrow_context(standard_material: MaterialSpec) -> ComponentContext:
    """Narrow context for mullion filler testing."""
    return ComponentContext(
        width=6.0,
        height=84.0,
        depth=18.0,
        material=standard_material,
        position=Position(0, 0),
        section_index=0,
        cabinet_width=6.0,
        cabinet_height=84.0,
        cabinet_depth=18.0,
    )


class TestWindowSeatStorageComponentRegistration:
    """Tests for component registry registration."""

    def test_component_registered(self):
        """WindowSeatStorageComponent should be registered in component registry."""
        component_cls = component_registry.get("windowseat.storage")
        # Use name comparison since module reloads create new class objects
        assert component_cls.__name__ == WindowSeatStorageComponent.__name__
        assert "windowseat.storage" in component_registry.list()

    def test_mullion_filler_registered(self):
        """MullionFillerComponent should be registered in component registry."""
        component_cls = component_registry.get("filler.mullion")
        # Use name comparison since module reloads create new class objects
        assert component_cls.__name__ == MullionFillerComponent.__name__
        assert "filler.mullion" in component_registry.list()


class TestWindowSeatStorageValidation:
    """Tests for WindowSeatStorageComponent validation."""

    def test_valid_default_config(self, standard_context: ComponentContext):
        """Default configuration should be valid."""
        component = WindowSeatStorageComponent()
        result = component.validate({}, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_seat_height_too_low(self, standard_context: ComponentContext):
        """Seat height below minimum should produce error."""
        component = WindowSeatStorageComponent()
        config = {"seat_height": MIN_SEAT_HEIGHT - 1}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("below minimum" in e for e in result.errors)

    def test_seat_height_above_comfortable_range(
        self, standard_context: ComponentContext
    ):
        """Seat height above comfortable range should produce warning."""
        component = WindowSeatStorageComponent()
        config = {"seat_height": MAX_SEAT_HEIGHT + 1}
        result = component.validate(config, standard_context)
        assert result.is_valid  # Still valid, just a warning
        assert any("above comfortable range" in w for w in result.warnings)

    def test_invalid_access_type(self, standard_context: ComponentContext):
        """Invalid access type should produce error."""
        component = WindowSeatStorageComponent()
        config = {"access_type": "invalid_type"}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("Invalid access type" in e for e in result.errors)

    def test_valid_access_types(self, standard_context: ComponentContext):
        """All valid access types should pass validation."""
        component = WindowSeatStorageComponent()
        for access_type in VALID_ACCESS_TYPES:
            config = {"access_type": access_type}
            result = component.validate(config, standard_context)
            assert result.is_valid, f"Access type '{access_type}' should be valid"

    def test_excessive_cushion_thickness_warning(
        self, standard_context: ComponentContext
    ):
        """Excessive cushion thickness should produce warning."""
        component = WindowSeatStorageComponent()
        config = {"cushion_thickness": 8}
        result = component.validate(config, standard_context)
        assert result.is_valid  # Still valid, just a warning
        assert any("uncomfortably high" in w for w in result.warnings)

    def test_negative_cushion_thickness(self, standard_context: ComponentContext):
        """Negative cushion thickness should produce error."""
        component = WindowSeatStorageComponent()
        config = {"cushion_thickness": -1}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("cannot be negative" in e for e in result.errors)

    def test_width_too_narrow(self, standard_material: MaterialSpec):
        """Width below minimum should produce error."""
        context = ComponentContext(
            width=MIN_SEAT_WIDTH - 1,
            height=84.0,
            depth=18.0,
            material=standard_material,
            position=Position(0, 0),
            section_index=0,
            cabinet_width=11.0,
            cabinet_height=84.0,
            cabinet_depth=18.0,
        )
        component = WindowSeatStorageComponent()
        result = component.validate({}, context)
        assert not result.is_valid
        assert any("too narrow" in e for e in result.errors)

    def test_depth_too_shallow(self, standard_material: MaterialSpec):
        """Depth below minimum should produce error."""
        context = ComponentContext(
            width=36.0,
            height=84.0,
            depth=MIN_SEAT_DEPTH - 1,
            material=standard_material,
            position=Position(0, 0),
            section_index=0,
            cabinet_width=36.0,
            cabinet_height=84.0,
            cabinet_depth=11.0,
        )
        component = WindowSeatStorageComponent()
        result = component.validate({}, context)
        assert not result.is_valid
        assert any("too shallow" in e for e in result.errors)

    def test_invalid_edge_treatment(self, standard_context: ComponentContext):
        """Invalid edge treatment should produce error."""
        component = WindowSeatStorageComponent()
        config = {"edge_treatment": "invalid_edge"}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("Invalid edge treatment" in e for e in result.errors)

    def test_deep_cushion_recess_warning(self, standard_context: ComponentContext):
        """Deep cushion recess should produce warning."""
        component = WindowSeatStorageComponent()
        config = {"cushion_recess": 3}
        result = component.validate(config, standard_context)
        assert result.is_valid
        assert any("structural integrity" in w for w in result.warnings)


class TestWindowSeatStorageGeneration:
    """Tests for WindowSeatStorageComponent panel and hardware generation."""

    def test_generates_seat_surface(self, standard_context: ComponentContext):
        """Should generate a seat surface panel."""
        component = WindowSeatStorageComponent()
        result = component.generate({}, standard_context)
        seat_panels = [
            p for p in result.panels if p.panel_type == PanelType.SEAT_SURFACE
        ]
        assert len(seat_panels) == 1
        assert seat_panels[0].metadata["is_seat_surface"] is True

    def test_generates_side_panels(self, standard_context: ComponentContext):
        """Should generate left and right side panels."""
        component = WindowSeatStorageComponent()
        result = component.generate({}, standard_context)
        left_sides = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE]
        right_sides = [p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE]
        assert len(left_sides) == 1
        assert len(right_sides) == 1

    def test_generates_bottom_panel(self, standard_context: ComponentContext):
        """Should generate a bottom panel."""
        component = WindowSeatStorageComponent()
        result = component.generate({}, standard_context)
        bottom_panels = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottom_panels) == 1

    def test_generates_back_panel(self, standard_context: ComponentContext):
        """Should generate a back panel with 1/4 inch material."""
        component = WindowSeatStorageComponent()
        result = component.generate({}, standard_context)
        back_panels = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(back_panels) == 1
        assert back_panels[0].material.thickness == 0.25

    def test_seat_surface_dimensions(self, standard_context: ComponentContext):
        """Seat surface should match context width and depth."""
        component = WindowSeatStorageComponent()
        result = component.generate({}, standard_context)
        seat_panels = [
            p for p in result.panels if p.panel_type == PanelType.SEAT_SURFACE
        ]
        assert seat_panels[0].width == standard_context.width
        assert (
            seat_panels[0].height == standard_context.depth
        )  # height is depth for horizontal

    def test_box_height_calculation(self, standard_context: ComponentContext):
        """Side panel height should be seat height minus seat thickness."""
        component = WindowSeatStorageComponent()
        config = {"seat_height": 18.0}
        result = component.generate(config, standard_context)
        left_side = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE][0]
        expected_box_height = 18.0 - SEAT_THICKNESS
        assert left_side.height == expected_box_height

    def test_metadata_includes_access_type(self, standard_context: ComponentContext):
        """Result metadata should include access type."""
        component = WindowSeatStorageComponent()
        result = component.generate({}, standard_context)
        assert result.metadata["access_type"] == ACCESS_HINGED_TOP

    def test_metadata_includes_dimensions(self, standard_context: ComponentContext):
        """Result metadata should include seat dimensions."""
        component = WindowSeatStorageComponent()
        config = {"seat_height": 20.0}
        result = component.generate(config, standard_context)
        assert result.metadata["seat_height"] == 20.0
        assert result.metadata["seat_depth"] == standard_context.depth


class TestWindowSeatHingedTopHardware:
    """Tests for hinged top access type hardware."""

    def test_generates_piano_hinge(self, standard_context: ComponentContext):
        """Hinged top should include piano hinge."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_HINGED_TOP}
        result = component.generate(config, standard_context)
        piano_hinges = [h for h in result.hardware if "Piano Hinge" in h.name]
        assert len(piano_hinges) == 1
        assert piano_hinges[0].quantity == 1

    def test_generates_lid_stays(self, standard_context: ComponentContext):
        """Hinged top should include soft-close lid stays."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_HINGED_TOP}
        result = component.generate(config, standard_context)
        lid_stays = [h for h in result.hardware if "Lid Stay" in h.name]
        assert len(lid_stays) == 1
        assert lid_stays[0].quantity == 2  # One per side


class TestWindowSeatFrontDoorsHardware:
    """Tests for front doors access type panels and hardware."""

    def test_generates_door_panels(self, standard_context: ComponentContext):
        """Front doors should generate door panels."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_FRONT_DOORS}
        result = component.generate(config, standard_context)
        door_panels = [p for p in result.panels if p.panel_type == PanelType.DOOR]
        assert len(door_panels) >= 1

    def test_door_count_based_on_width(self, standard_material: MaterialSpec):
        """Number of doors should be based on width (max 24 inches per door)."""
        # Wide seat should have multiple doors
        wide_context = ComponentContext(
            width=72.0,
            height=84.0,
            depth=18.0,
            material=standard_material,
            position=Position(0, 0),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=84.0,
            cabinet_depth=18.0,
        )
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_FRONT_DOORS}
        result = component.generate(config, wide_context)
        door_panels = [p for p in result.panels if p.panel_type == PanelType.DOOR]
        # Interior width is 72 - 2*0.75 = 70.5, should have 3 doors (70.5/24 = 2.9)
        assert len(door_panels) >= 2

    def test_generates_european_hinges(self, standard_context: ComponentContext):
        """Front doors should include European hinges."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_FRONT_DOORS}
        result = component.generate(config, standard_context)
        hinges = [h for h in result.hardware if "European Hinge" in h.name]
        assert len(hinges) == 1
        # 2 hinges per door
        door_panels = [p for p in result.panels if p.panel_type == PanelType.DOOR]
        assert hinges[0].quantity == len(door_panels) * 2


class TestWindowSeatDrawersHardware:
    """Tests for drawer access type panels and hardware."""

    def test_generates_drawer_front(self, standard_context: ComponentContext):
        """Drawer access should generate drawer front panel."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_DRAWERS}
        result = component.generate(config, standard_context)
        drawer_fronts = [
            p for p in result.panels if p.panel_type == PanelType.DRAWER_FRONT
        ]
        assert len(drawer_fronts) == 1

    def test_generates_drawer_slides(self, standard_context: ComponentContext):
        """Drawer access should include drawer slides."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_DRAWERS}
        result = component.generate(config, standard_context)
        slides = [h for h in result.hardware if "Drawer Slides" in h.name]
        assert len(slides) == 1
        assert slides[0].quantity == 1  # 1 pair

    def test_drawer_slide_length_based_on_depth(
        self, standard_context: ComponentContext
    ):
        """Drawer slide length should be appropriate for depth."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_DRAWERS}
        result = component.generate(config, standard_context)
        slides = [h for h in result.hardware if "Drawer Slides" in h.name]
        # Standard context depth is 18, slide should be around 16
        assert "16" in slides[0].sku or "14" in slides[0].sku


class TestWindowSeatHardwareMethod:
    """Tests for the hardware() method."""

    def test_hardware_method_returns_list(self, standard_context: ComponentContext):
        """hardware() method should return a list."""
        component = WindowSeatStorageComponent()
        hardware = component.hardware({}, standard_context)
        assert isinstance(hardware, list)

    def test_hardware_method_matches_generate(self, standard_context: ComponentContext):
        """hardware() method should match hardware from generate()."""
        component = WindowSeatStorageComponent()
        config = {"access_type": ACCESS_FRONT_DOORS}
        hardware = component.hardware(config, standard_context)
        result = component.generate(config, standard_context)
        assert len(hardware) == len(result.hardware)


class TestMullionFillerValidation:
    """Tests for MullionFillerComponent validation."""

    def test_valid_narrow_width(self, narrow_context: ComponentContext):
        """Narrow width should be valid for mullion filler."""
        component = MullionFillerComponent()
        result = component.validate({}, narrow_context)
        assert result.is_valid

    def test_wide_width_warning(self, standard_context: ComponentContext):
        """Wide width should produce warning."""
        component = MullionFillerComponent()
        result = component.validate({}, standard_context)
        # 36 inches is too wide for a mullion filler
        assert any("wide for a mullion filler" in w for w in result.warnings)

    def test_too_narrow_width_error(self, standard_material: MaterialSpec):
        """Width below minimum should produce error."""
        context = ComponentContext(
            width=0.5,  # Too narrow
            height=84.0,
            depth=18.0,
            material=standard_material,
            position=Position(0, 0),
            section_index=0,
            cabinet_width=0.5,
            cabinet_height=84.0,
            cabinet_depth=18.0,
        )
        component = MullionFillerComponent()
        result = component.validate({}, context)
        assert not result.is_valid
        assert any("too narrow" in e for e in result.errors)

    def test_invalid_style_error(self, narrow_context: ComponentContext):
        """Invalid style should produce error."""
        component = MullionFillerComponent()
        config = {"style": "invalid_style"}
        result = component.validate(config, narrow_context)
        assert not result.is_valid
        assert any("Invalid filler style" in e for e in result.errors)

    def test_valid_styles(self, narrow_context: ComponentContext):
        """All valid styles should pass validation."""
        component = MullionFillerComponent()
        for style in MullionFillerComponent.VALID_STYLES:
            config = {"style": style}
            result = component.validate(config, narrow_context)
            assert result.is_valid, f"Style '{style}' should be valid"


class TestMullionFillerGeneration:
    """Tests for MullionFillerComponent panel generation."""

    def test_generates_mullion_filler_panel(self, narrow_context: ComponentContext):
        """Should generate a mullion filler panel."""
        component = MullionFillerComponent()
        result = component.generate({}, narrow_context)
        assert len(result.panels) == 1
        assert result.panels[0].panel_type == PanelType.MULLION_FILLER

    def test_panel_dimensions_match_context(self, narrow_context: ComponentContext):
        """Filler panel should match context dimensions."""
        component = MullionFillerComponent()
        result = component.generate({}, narrow_context)
        panel = result.panels[0]
        assert panel.width == narrow_context.width
        assert panel.height == narrow_context.height

    def test_metadata_includes_style(self, narrow_context: ComponentContext):
        """Panel metadata should include style."""
        component = MullionFillerComponent()
        config = {"style": "beveled"}
        result = component.generate(config, narrow_context)
        assert result.panels[0].metadata["style"] == "beveled"
        assert result.metadata["style"] == "beveled"

    def test_no_hardware_generated(self, narrow_context: ComponentContext):
        """Filler panels should not require hardware."""
        component = MullionFillerComponent()
        result = component.generate({}, narrow_context)
        assert len(result.hardware) == 0


class TestMullionFillerHardwareMethod:
    """Tests for MullionFillerComponent hardware() method."""

    def test_hardware_returns_empty_list(self, narrow_context: ComponentContext):
        """hardware() should return empty list."""
        component = MullionFillerComponent()
        hardware = component.hardware({}, narrow_context)
        assert hardware == []


class TestConstants:
    """Tests for module constants."""

    def test_seat_height_range(self):
        """Seat height range should be reasonable."""
        assert MIN_SEAT_HEIGHT < DEFAULT_SEAT_HEIGHT < MAX_SEAT_HEIGHT

    def test_default_seat_height_is_comfortable(self):
        """Default seat height should be comfortable (around 18 inches)."""
        assert 16 <= DEFAULT_SEAT_HEIGHT <= 20

    def test_seat_thickness_is_standard(self):
        """Seat thickness should be standard 3/4 inch."""
        assert SEAT_THICKNESS == 0.75

    def test_access_types_tuple(self):
        """Access types should be a tuple of strings."""
        assert isinstance(VALID_ACCESS_TYPES, tuple)
        assert all(isinstance(t, str) for t in VALID_ACCESS_TYPES)

    def test_all_access_type_constants_in_valid_types(self):
        """All access type constants should be in VALID_ACCESS_TYPES."""
        assert ACCESS_HINGED_TOP in VALID_ACCESS_TYPES
        assert ACCESS_FRONT_DOORS in VALID_ACCESS_TYPES
        assert ACCESS_DRAWERS in VALID_ACCESS_TYPES
