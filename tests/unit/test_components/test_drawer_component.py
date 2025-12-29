"""Tests for StandardDrawerComponent, _DrawerBase, and related types."""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    HardwareItem,
    ValidationResult,
    component_registry,
)
from cabinets.domain.components.drawer import (
    SLIDE_CLEARANCES,
    VALID_SLIDE_LENGTHS,
    DrawerBoxSpec,
    FileDrawerComponent,
    SlideMountSpec,
    StandardDrawerComponent,
    _auto_select_slide_length,
)
from cabinets.domain.value_objects import MaterialSpec, PanelType, Position


@pytest.fixture
def drawer_component() -> StandardDrawerComponent:
    """Create a StandardDrawerComponent instance for testing."""
    return StandardDrawerComponent()


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing.

    Returns a context representing a 24" wide section with 72" height
    at position (0.75, 0.75) within a 48x84x18 cabinet.
    The depth of 17.5" allows for 16" slides with 1" rear clearance.
    """
    return ComponentContext(
        width=24.0,
        height=72.0,
        depth=17.5,  # Interior depth (18 - 0.5 back panel), allows 16" slides
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=18.0,
    )


class TestDrawerComponentRegistration:
    """Tests for drawer.standard component registration."""

    @pytest.fixture(autouse=True)
    def ensure_drawer_registered(self) -> None:
        """Ensure drawer.standard is registered for each test."""
        if "drawer.standard" not in component_registry.list():
            component_registry.register("drawer.standard")(StandardDrawerComponent)

    def test_component_is_registered_as_drawer_standard(self) -> None:
        """Test that drawer.standard is registered in the component registry."""
        assert "drawer.standard" in component_registry.list()

    def test_get_returns_standard_drawer_component_class(self) -> None:
        """Test that registry.get returns StandardDrawerComponent."""
        component_class = component_registry.get("drawer.standard")
        assert component_class is StandardDrawerComponent


class TestDrawerComponentValidation:
    """Tests for StandardDrawerComponent.validate()."""

    def test_validate_returns_ok_for_valid_config(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid drawer config."""
        config = {"front_height": 6.0, "slide_type": "side_mount"}

        result = drawer_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_default_config(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for empty config (uses defaults)."""
        config: dict = {}

        result = drawer_component.validate(config, standard_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_v01_slide_length_exceeds_depth_fails(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test V-01: slide_length > section_depth - 1" fails validation."""
        # Create shallow context where 12" slide won't fit (need 13" depth minimum)
        shallow_context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=10.0,  # Too shallow for 12" slides (need 13")
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"slide_length": 12}

        result = drawer_component.validate(config, shallow_context)

        assert not result.is_valid
        assert any("exceeds section depth" in err for err in result.errors)

    def test_validate_v02_front_height_below_minimum_fails(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test V-02: front_height < 3" fails validation."""
        config = {"front_height": 2.5}

        result = drawer_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("below minimum" in err for err in result.errors)

    def test_validate_v03_front_height_exceeds_section_height_fails(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test V-03: front_height > section_height fails validation."""
        config = {"front_height": 80.0}  # Exceeds 72" section height

        result = drawer_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("exceeds section height" in err for err in result.errors)

    def test_validate_v04_section_too_narrow_for_slides_fails(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test V-04: box_width <= 0 fails validation."""
        # Create very narrow context where side mount slides don't fit
        narrow_context = ComponentContext(
            width=0.5,  # Too narrow for 0.5" clearance on each side
            height=72.0,
            depth=18.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=20.0,
        )
        config = {"slide_type": "side_mount"}

        result = drawer_component.validate(config, narrow_context)

        assert not result.is_valid
        assert any("too narrow" in err for err in result.errors)

    def test_validate_invalid_slide_type_fails(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that invalid slide_type fails validation."""
        config = {"slide_type": "invalid_type"}

        result = drawer_component.validate(config, standard_context)

        assert not result.is_valid
        assert any("Invalid slide_type" in err for err in result.errors)

    def test_validate_invalid_slide_length_fails(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test that invalid slide_length fails validation."""
        # Create deep enough context for 30" slides if they existed
        deep_context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=35.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=40.0,
        )
        config = {"slide_length": 30}  # Not a valid length

        result = drawer_component.validate(config, deep_context)

        assert not result.is_valid
        assert any("Invalid slide_length" in err for err in result.errors)

    def test_validate_front_height_exactly_minimum_passes(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that front_height exactly at minimum (3") passes validation."""
        config = {"front_height": 3.0}

        result = drawer_component.validate(config, standard_context)

        assert result.is_valid

    def test_validate_all_slide_types(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that all valid slide types pass validation."""
        for slide_type in SLIDE_CLEARANCES.keys():
            config = {"slide_type": slide_type}

            result = drawer_component.validate(config, standard_context)

            assert result.is_valid, f"Failed for slide_type: {slide_type}"

    def test_validate_all_slide_lengths(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test that all valid slide lengths pass validation when depth allows."""
        # Create deep enough context for all slide lengths
        deep_context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=30.0,  # Deep enough for 24" slides + 1" clearance
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=35.0,
        )

        for slide_length in VALID_SLIDE_LENGTHS:
            config = {"slide_length": slide_length}

            result = drawer_component.validate(config, deep_context)

            assert result.is_valid, f"Failed for slide_length: {slide_length}"


class TestDrawerComponentGeneration:
    """Tests for StandardDrawerComponent.generate()."""

    def test_generate_returns_generation_result(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        assert isinstance(result, GenerationResult)

    def test_generate_creates_six_panels(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates 6 panels (front, box front, 2 sides, bottom, top panel)."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        # 5 drawer panels + 1 top panel (horizontal divider)
        assert len(result.panels) == 6

    def test_generate_creates_drawer_front_panel(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates a DRAWER_FRONT panel."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        front_panels = [p for p in result.panels if p.panel_type == PanelType.DRAWER_FRONT]
        assert len(front_panels) == 1

    def test_generate_drawer_front_dimensions(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that drawer front has correct dimensions."""
        config = {"front_height": 8.0}

        result = drawer_component.generate(config, standard_context)

        front_panel = next(p for p in result.panels if p.panel_type == PanelType.DRAWER_FRONT)
        assert front_panel.width == standard_context.width  # 24.0
        assert front_panel.height == 8.0

    def test_generate_creates_drawer_box_front_panel(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates a DRAWER_BOX_FRONT panel."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        box_front_panels = [p for p in result.panels if p.panel_type == PanelType.DRAWER_BOX_FRONT]
        assert len(box_front_panels) == 1

    def test_generate_creates_two_drawer_side_panels(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates 2 DRAWER_SIDE panels (left and right)."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        side_panels = [p for p in result.panels if p.panel_type == PanelType.DRAWER_SIDE]
        assert len(side_panels) == 2

    def test_generate_creates_drawer_bottom_panel(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates a DRAWER_BOTTOM panel."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        bottom_panels = [p for p in result.panels if p.panel_type == PanelType.DRAWER_BOTTOM]
        assert len(bottom_panels) == 1

    def test_generate_box_height_calculation(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that box height is front_height - 0.125" - 0.5"."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        expected_box_height = 6.0 - 0.125 - 0.5  # 5.375
        side_panel = next(p for p in result.panels if p.panel_type == PanelType.DRAWER_SIDE)
        assert side_panel.height == pytest.approx(expected_box_height)

    def test_generate_box_width_calculation_side_mount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test box width for side mount slides (0.5" clearance per side)."""
        config = {"front_height": 6.0, "slide_type": "side_mount"}

        result = drawer_component.generate(config, standard_context)

        # box_width = section_width - (2 * 0.5) = 24.0 - 1.0 = 23.0
        expected_box_width = 23.0
        # Check via metadata
        assert result.metadata["drawer_spec"].box_width == pytest.approx(expected_box_width)

    def test_generate_box_width_calculation_undermount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test box width for undermount slides (0.1875" clearance per side)."""
        config = {"front_height": 6.0, "slide_type": "undermount"}

        result = drawer_component.generate(config, standard_context)

        # box_width = section_width - (2 * 0.1875) = 24.0 - 0.375 = 23.625
        expected_box_width = 24.0 - (2 * SLIDE_CLEARANCES["undermount"])
        assert result.metadata["drawer_spec"].box_width == pytest.approx(expected_box_width)

    def test_generate_box_width_calculation_center_mount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test box width for center mount slides (0" clearance per side)."""
        config = {"front_height": 6.0, "slide_type": "center_mount"}

        result = drawer_component.generate(config, standard_context)

        # box_width = section_width - 0 = 24.0
        expected_box_width = 24.0
        assert result.metadata["drawer_spec"].box_width == pytest.approx(expected_box_width)

    def test_generate_box_depth_calculation(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test that box depth is slide_length - 1" rear clearance."""
        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=20.0,  # Deep enough for 18" slides
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=22.0,
        )
        config = {"front_height": 6.0, "slide_length": 18}

        result = drawer_component.generate(config, context)

        expected_box_depth = 18 - 1  # 17"
        assert result.metadata["drawer_spec"].box_depth == pytest.approx(expected_box_depth)

    def test_generate_auto_slide_length_selection(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that auto slide length is correctly selected."""
        config = {"front_height": 6.0, "slide_length": "auto"}

        result = drawer_component.generate(config, standard_context)

        # For 17.5" depth, auto should select 16" slides
        # (largest that fits with 2" clearance)
        expected_slide_length = _auto_select_slide_length(standard_context.depth)
        assert result.metadata["slide_length"] == expected_slide_length

    def test_generate_drawer_front_position(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that drawer front is positioned at context position."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        front_panel = next(p for p in result.panels if p.panel_type == PanelType.DRAWER_FRONT)
        assert front_panel.position.x == pytest.approx(standard_context.position.x)
        assert front_panel.position.y == pytest.approx(standard_context.position.y)

    def test_generate_metadata_includes_drawer_spec(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes drawer_spec."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        assert "drawer_spec" in result.metadata
        assert isinstance(result.metadata["drawer_spec"], DrawerBoxSpec)

    def test_generate_metadata_includes_slide_info(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes slide information."""
        config = {"front_height": 6.0, "slide_type": "undermount", "soft_close": False}

        result = drawer_component.generate(config, standard_context)

        assert result.metadata["slide_type"] == "undermount"
        assert result.metadata["soft_close"] is False

    def test_generate_with_custom_front_style(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that custom front style is captured in metadata."""
        config = {"front_height": 6.0, "front_style": "inset"}

        result = drawer_component.generate(config, standard_context)

        assert result.metadata["front_style"] == "inset"


class TestDrawerComponentHardware:
    """Tests for StandardDrawerComponent.hardware() and generated hardware."""

    def test_generate_includes_hardware(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes hardware items."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        assert len(result.hardware) > 0

    def test_generate_includes_drawer_slides(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes drawer slides."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        slide_items = [h for h in result.hardware if "Slide" in h.name]
        assert len(slide_items) == 1

    def test_generate_slide_quantity_side_mount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side mount slides require quantity 2."""
        config = {"front_height": 6.0, "slide_type": "side_mount"}

        result = drawer_component.generate(config, standard_context)

        slide_item = next(h for h in result.hardware if "Slide" in h.name)
        assert slide_item.quantity == 2

    def test_generate_slide_quantity_center_mount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that center mount slides require quantity 1."""
        config = {"front_height": 6.0, "slide_type": "center_mount"}

        result = drawer_component.generate(config, standard_context)

        slide_item = next(h for h in result.hardware if "Slide" in h.name)
        assert slide_item.quantity == 1

    def test_generate_soft_close_in_slide_name(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that soft close is reflected in slide name."""
        config = {"front_height": 6.0, "soft_close": True}

        result = drawer_component.generate(config, standard_context)

        slide_item = next(h for h in result.hardware if "Slide" in h.name)
        assert "Soft-Close" in slide_item.name

    def test_generate_non_soft_close_slide_name(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that non-soft close slides don't have Soft-Close in name."""
        config = {"front_height": 6.0, "soft_close": False}

        result = drawer_component.generate(config, standard_context)

        slide_item = next(h for h in result.hardware if "Slide" in h.name)
        assert "Soft-Close" not in slide_item.name

    def test_generate_includes_mounting_screws(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes mounting screws."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        screw_items = [h for h in result.hardware if "Screw" in h.name]
        assert len(screw_items) == 1

    def test_generate_screw_quantity_side_mount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side mount needs 8 screws (4 per slide * 2 slides)."""
        config = {"front_height": 6.0, "slide_type": "side_mount"}

        result = drawer_component.generate(config, standard_context)

        screw_item = next(h for h in result.hardware if "Screw" in h.name)
        assert screw_item.quantity == 8

    def test_generate_screw_quantity_center_mount(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that center mount needs 4 screws (4 per slide * 1 slide)."""
        config = {"front_height": 6.0, "slide_type": "center_mount"}

        result = drawer_component.generate(config, standard_context)

        screw_item = next(h for h in result.hardware if "Screw" in h.name)
        assert screw_item.quantity == 4

    def test_generate_includes_handle(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes handle/pull."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        handle_items = [h for h in result.hardware if "Handle" in h.name or "Pull" in h.name]
        assert len(handle_items) == 1
        assert handle_items[0].quantity == 1

    def test_generate_includes_edge_banding(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes edge banding."""
        config = {"front_height": 6.0}

        result = drawer_component.generate(config, standard_context)

        edge_items = [h for h in result.hardware if "Edge" in h.name]
        assert len(edge_items) == 1

    def test_generate_edge_banding_calculation(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that edge banding linear inches is calculated correctly."""
        config = {"front_height": 8.0}

        result = drawer_component.generate(config, standard_context)

        edge_item = next(h for h in result.hardware if "Edge" in h.name)
        # Perimeter = 2 * (width + height) = 2 * (24.0 + 8.0) = 64.0
        expected = 2 * (24.0 + 8.0)
        assert f"{expected:.2f}" in edge_item.notes

    def test_hardware_method_returns_list(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() method returns a list."""
        config = {"front_height": 6.0}

        result = drawer_component.hardware(config, standard_context)

        assert isinstance(result, list)
        assert all(isinstance(item, HardwareItem) for item in result)

    def test_hardware_method_matches_generate_hardware(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns same items as generate().hardware."""
        config = {"front_height": 6.0}

        generate_result = drawer_component.generate(config, standard_context)
        hardware_result = drawer_component.hardware(config, standard_context)

        assert len(hardware_result) == len(generate_result.hardware)


class TestAutoSlideLength:
    """Tests for _auto_select_slide_length helper function."""

    def test_auto_select_12_for_shallow_cabinet(self) -> None:
        """Test that 12" slides are selected for shallow cabinets."""
        assert _auto_select_slide_length(12.0) == 12

    def test_auto_select_14_for_medium_cabinet(self) -> None:
        """Test that 14" slides are selected for 14-16" depth."""
        assert _auto_select_slide_length(15.0) == 14

    def test_auto_select_16_for_medium_deep_cabinet(self) -> None:
        """Test that 16" slides are selected for 16-18" depth."""
        assert _auto_select_slide_length(17.0) == 16

    def test_auto_select_18_for_deep_cabinet(self) -> None:
        """Test that 18" slides are selected for 18-20" depth."""
        assert _auto_select_slide_length(19.0) == 18

    def test_auto_select_20_for_deeper_cabinet(self) -> None:
        """Test that 20" slides are selected for 20-22" depth."""
        assert _auto_select_slide_length(21.0) == 20

    def test_auto_select_22_for_very_deep_cabinet(self) -> None:
        """Test that 22" slides are selected for 22-24" depth."""
        assert _auto_select_slide_length(23.0) == 22

    def test_auto_select_24_for_extra_deep_cabinet(self) -> None:
        """Test that 24" slides are selected for >= 26" depth."""
        assert _auto_select_slide_length(30.0) == 24

    def test_auto_select_boundary_at_14(self) -> None:
        """Test boundary: 14" depth should get 14" slides.

        Logic: depth < length + 2 means 14 < 12 + 2 is False (14 is not < 14),
        so we check next length. 14 < 14 + 2 is True, so we return 14.
        """
        assert _auto_select_slide_length(14.0) == 14

    def test_auto_select_boundary_at_26(self) -> None:
        """Test boundary: 26" depth should get 24" slides."""
        assert _auto_select_slide_length(26.0) == 24


class TestSlideConstants:
    """Tests for slide clearance and length constants."""

    def test_slide_clearances_contains_side_mount(self) -> None:
        """Test that SLIDE_CLEARANCES contains side_mount."""
        assert "side_mount" in SLIDE_CLEARANCES
        assert SLIDE_CLEARANCES["side_mount"] == 0.5

    def test_slide_clearances_contains_undermount(self) -> None:
        """Test that SLIDE_CLEARANCES contains undermount."""
        assert "undermount" in SLIDE_CLEARANCES
        assert SLIDE_CLEARANCES["undermount"] == 0.1875

    def test_slide_clearances_contains_center_mount(self) -> None:
        """Test that SLIDE_CLEARANCES contains center_mount."""
        assert "center_mount" in SLIDE_CLEARANCES
        assert SLIDE_CLEARANCES["center_mount"] == 0.0

    def test_valid_slide_lengths_values(self) -> None:
        """Test that VALID_SLIDE_LENGTHS contains expected values."""
        expected = [12, 14, 16, 18, 20, 22, 24]
        assert VALID_SLIDE_LENGTHS == expected


class TestDrawerBoxSpec:
    """Tests for DrawerBoxSpec dataclass."""

    def test_drawer_box_spec_creation(self) -> None:
        """Test that DrawerBoxSpec can be created with required fields."""
        spec = DrawerBoxSpec(
            box_width=22.0,
            box_height=5.5,
            box_depth=16.0,
            front_width=24.0,
            front_height=6.0,
        )

        assert spec.box_width == 22.0
        assert spec.box_height == 5.5
        assert spec.box_depth == 16.0
        assert spec.front_width == 24.0
        assert spec.front_height == 6.0

    def test_drawer_box_spec_default_thicknesses(self) -> None:
        """Test that DrawerBoxSpec has correct default thicknesses."""
        spec = DrawerBoxSpec(
            box_width=22.0,
            box_height=5.5,
            box_depth=16.0,
            front_width=24.0,
            front_height=6.0,
        )

        assert spec.bottom_thickness == 0.25  # 1/4"
        assert spec.side_thickness == 0.5  # 1/2"
        assert spec.dado_depth == 0.25  # 1/4"

    def test_drawer_box_spec_custom_thicknesses(self) -> None:
        """Test that DrawerBoxSpec accepts custom thicknesses."""
        spec = DrawerBoxSpec(
            box_width=22.0,
            box_height=5.5,
            box_depth=16.0,
            front_width=24.0,
            front_height=6.0,
            bottom_thickness=0.5,
            side_thickness=0.75,
            dado_depth=0.375,
        )

        assert spec.bottom_thickness == 0.5
        assert spec.side_thickness == 0.75
        assert spec.dado_depth == 0.375

    def test_drawer_box_spec_is_frozen(self) -> None:
        """Test that DrawerBoxSpec is immutable (frozen)."""
        spec = DrawerBoxSpec(
            box_width=22.0,
            box_height=5.5,
            box_depth=16.0,
            front_width=24.0,
            front_height=6.0,
        )

        with pytest.raises(AttributeError):
            spec.box_width = 20.0  # type: ignore

    def test_drawer_box_spec_equality(self) -> None:
        """Test that two DrawerBoxSpecs with same values are equal."""
        spec1 = DrawerBoxSpec(22.0, 5.5, 16.0, 24.0, 6.0)
        spec2 = DrawerBoxSpec(22.0, 5.5, 16.0, 24.0, 6.0)

        assert spec1 == spec2


class TestSlideMountSpec:
    """Tests for SlideMountSpec dataclass."""

    def test_slide_mount_spec_creation(self) -> None:
        """Test that SlideMountSpec can be created with all fields."""
        spec = SlideMountSpec(
            panel_id="left_side",
            slide_type="side_mount",
            position_y=3.0,
            slide_length=18,
            mounting_holes=(2.0, 8.0, 14.0),
        )

        assert spec.panel_id == "left_side"
        assert spec.slide_type == "side_mount"
        assert spec.position_y == 3.0
        assert spec.slide_length == 18
        assert spec.mounting_holes == (2.0, 8.0, 14.0)

    def test_slide_mount_spec_is_frozen(self) -> None:
        """Test that SlideMountSpec is immutable (frozen)."""
        spec = SlideMountSpec(
            panel_id="left_side",
            slide_type="side_mount",
            position_y=3.0,
            slide_length=18,
            mounting_holes=(2.0, 8.0, 14.0),
        )

        with pytest.raises(AttributeError):
            spec.position_y = 5.0  # type: ignore


class TestDrawerComponentIntegration:
    """Integration tests for StandardDrawerComponent."""

    @pytest.fixture(autouse=True)
    def ensure_drawer_registered(self) -> None:
        """Ensure drawer.standard is registered for integration tests."""
        if "drawer.standard" not in component_registry.list():
            component_registry.register("drawer.standard")(StandardDrawerComponent)

    def test_full_workflow_validate_generate_hardware(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        # Get component from registry
        component_class = component_registry.get("drawer.standard")
        component = component_class()

        config = {
            "front_height": 8.0,
            "slide_type": "undermount",
            "soft_close": True,
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        # 5 drawer panels + 1 top panel (horizontal divider)
        assert len(generation.panels) == 6
        assert "drawer_spec" in generation.metadata

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 4  # slides, screws, handle, edge banding

    def test_drawer_with_different_contexts(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test drawer generation with different context dimensions.

        Depths must accommodate auto-selected slides with 1" rear clearance:
        - 21" depth -> 20" slides (20 + 1 = 21, fits)
        - 19" depth -> 18" slides (18 + 1 = 19, fits)
        - 17" depth -> 16" slides (16 + 1 = 17, fits)
        """
        contexts = [
            # Standard cabinet (21" depth for 20" slides)
            ComponentContext(
                width=24.0, height=72.0, depth=21.0,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 0.75),
                section_index=0,
                cabinet_width=48.0, cabinet_height=84.0, cabinet_depth=24.0,
            ),
            # Wide cabinet (19" depth for 18" slides)
            ComponentContext(
                width=36.0, height=36.0, depth=19.0,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 0.75),
                section_index=0,
                cabinet_width=72.0, cabinet_height=42.0, cabinet_depth=22.0,
            ),
            # Narrow cabinet (17" depth for 16" slides)
            ComponentContext(
                width=12.0, height=30.0, depth=17.0,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 0.75),
                section_index=0,
                cabinet_width=24.0, cabinet_height=36.0, cabinet_depth=20.0,
            ),
        ]

        config = {"front_height": 6.0}

        for ctx in contexts:
            validation = drawer_component.validate(config, ctx)
            assert validation.is_valid, f"Failed for context: {ctx}"

            generation = drawer_component.generate(config, ctx)
            # 5 drawer panels + 1 top panel (horizontal divider)
            assert len(generation.panels) == 6


class TestDrawerComponentEdgeCases:
    """Edge case tests for StandardDrawerComponent."""

    def test_minimum_front_height(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test drawer with minimum front height (3")."""
        config = {"front_height": 3.0}

        result = drawer_component.validate(config, standard_context)
        assert result.is_valid

        generation = drawer_component.generate(config, standard_context)
        # 5 drawer panels + 1 top panel (horizontal divider)
        assert len(generation.panels) == 6

    def test_large_front_height(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test drawer with large front height."""
        config = {"front_height": 60.0}  # Within 72" section height

        result = drawer_component.validate(config, standard_context)
        assert result.is_valid

        generation = drawer_component.generate(config, standard_context)
        front_panel = next(p for p in generation.panels if p.panel_type == PanelType.DRAWER_FRONT)
        assert front_panel.height == 60.0

    def test_all_slide_types_generate_correctly(
        self, drawer_component: StandardDrawerComponent, standard_context: ComponentContext
    ) -> None:
        """Test that all slide types generate correct box widths."""
        for slide_type, clearance in SLIDE_CLEARANCES.items():
            config = {"front_height": 6.0, "slide_type": slide_type}

            generation = drawer_component.generate(config, standard_context)

            expected_box_width = standard_context.width - (2 * clearance)
            assert generation.metadata["drawer_spec"].box_width == pytest.approx(expected_box_width)

    def test_deepest_slide_length(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test drawer with deepest slide length (24")."""
        deep_context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=30.0,  # Deep enough for 24" slides
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=35.0,
        )
        config = {"front_height": 6.0, "slide_length": 24}

        result = drawer_component.validate(config, deep_context)
        assert result.is_valid

        generation = drawer_component.generate(config, deep_context)
        assert generation.metadata["slide_length"] == 24
        assert generation.metadata["drawer_spec"].box_depth == 23  # 24 - 1

    def test_shallowest_slide_length(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test drawer with shallowest slide length (12")."""
        context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=15.0,  # Minimum for 12" slides
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=18.0,
        )
        config = {"front_height": 6.0, "slide_length": 12}

        result = drawer_component.validate(config, context)
        assert result.is_valid

        generation = drawer_component.generate(config, context)
        assert generation.metadata["slide_length"] == 12
        assert generation.metadata["drawer_spec"].box_depth == 11  # 12 - 1

    def test_multiple_validation_errors(
        self, drawer_component: StandardDrawerComponent
    ) -> None:
        """Test that multiple validation errors are all reported."""
        # Create context with many issues
        narrow_shallow_context = ComponentContext(
            width=0.5,  # Too narrow
            height=10.0,  # Too short for 12" front
            depth=5.0,  # Too shallow for any slides
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {
            "front_height": 12.0,  # Exceeds section height
            "slide_type": "side_mount",
            "slide_length": 12,  # Won't fit in 5" depth
        }

        result = drawer_component.validate(config, narrow_shallow_context)

        assert not result.is_valid
        # Should have multiple errors
        assert len(result.errors) >= 3


# =============================================================================
# FileDrawerComponent Tests
# =============================================================================


@pytest.fixture
def file_drawer_component() -> FileDrawerComponent:
    """Create a FileDrawerComponent instance for testing."""
    return FileDrawerComponent()


@pytest.fixture
def deep_context() -> ComponentContext:
    """Create a deep ComponentContext suitable for file drawers.

    Returns a context with sufficient height for file drawers and
    depth for standard slides.

    Note: depth of 21" allows for 20" auto-selected slides (20 + 1" rear clearance).
    """
    return ComponentContext(
        width=24.0,
        height=72.0,
        depth=21.0,  # Deep enough for 20" slides (20 + 1" = 21)
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


class TestFileDrawerComponentRegistration:
    """Tests for drawer.file component registration."""

    @pytest.fixture(autouse=True)
    def ensure_file_drawer_registered(self) -> None:
        """Ensure drawer.file is registered for each test."""
        if "drawer.file" not in component_registry.list():
            component_registry.register("drawer.file")(FileDrawerComponent)

    def test_component_is_registered_as_drawer_file(self) -> None:
        """Test that drawer.file is registered in the component registry."""
        assert "drawer.file" in component_registry.list()

    def test_get_returns_file_drawer_component_class(self) -> None:
        """Test that registry.get returns FileDrawerComponent."""
        component_class = component_registry.get("drawer.file")
        assert component_class is FileDrawerComponent


class TestFileDrawerComponentValidation:
    """Tests for FileDrawerComponent.validate()."""

    def test_validate_returns_ok_for_valid_letter_file_drawer(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid letter file drawer config."""
        # Letter files need 10.5" box height
        # box_height = front_height - 0.125 - 0.5 = front_height - 0.625
        # For 10.5" box height, need front_height >= 11.125"
        config = {"file_type": "letter", "front_height": 12.0}

        result = file_drawer_component.validate(config, deep_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_returns_ok_for_valid_legal_file_drawer(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid legal file drawer config."""
        # Legal files need 12.0" box height
        # For 12.0" box height, need front_height >= 12.625"
        config = {"file_type": "legal", "front_height": 14.0}

        result = file_drawer_component.validate(config, deep_context)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_v05_letter_file_height_below_minimum_fails(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test V-05: letter file drawer with box_height < 10.5" fails validation."""
        # box_height = 8.0 - 0.625 = 7.375", below 10.5" minimum
        config = {"file_type": "letter", "front_height": 8.0}

        result = file_drawer_component.validate(config, deep_context)

        assert not result.is_valid
        assert any("below minimum" in err and "letter" in err for err in result.errors)

    def test_validate_v05_legal_file_height_below_minimum_fails(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test V-05: legal file drawer with box_height < 12.0" fails validation."""
        # box_height = 10.0 - 0.625 = 9.375", below 12.0" minimum
        config = {"file_type": "legal", "front_height": 10.0}

        result = file_drawer_component.validate(config, deep_context)

        assert not result.is_valid
        assert any("below minimum" in err and "legal" in err for err in result.errors)

    def test_validate_invalid_file_type_fails(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that invalid file_type fails validation."""
        config = {"file_type": "tabloid", "front_height": 14.0}

        result = file_drawer_component.validate(config, deep_context)

        assert not result.is_valid
        assert any("Invalid file_type" in err for err in result.errors)

    def test_validate_v06_center_mount_generates_warning(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test V-06: center_mount + file drawer generates warning."""
        config = {
            "file_type": "letter",
            "front_height": 12.0,
            "slide_type": "center_mount",
        }

        result = file_drawer_component.validate(config, deep_context)

        # Should have warning about center mount
        assert len(result.warnings) > 0
        assert any("center_mount" in warn and "not recommended" in warn for warn in result.warnings)

    def test_validate_side_mount_no_warning(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that side_mount file drawer does not generate warning."""
        config = {
            "file_type": "letter",
            "front_height": 12.0,
            "slide_type": "side_mount",
        }

        result = file_drawer_component.validate(config, deep_context)

        # Should have no warnings
        assert len(result.warnings) == 0

    def test_validate_undermount_no_warning(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that undermount file drawer does not generate warning."""
        config = {
            "file_type": "legal",
            "front_height": 14.0,
            "slide_type": "undermount",
        }

        result = file_drawer_component.validate(config, deep_context)

        # Should have no warnings
        assert len(result.warnings) == 0

    def test_validate_letter_file_minimum_boundary(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test letter file drawer exactly at minimum height boundary.

        box_height = front_height - 0.625
        For box_height = 10.5, front_height = 11.125
        """
        config = {"file_type": "letter", "front_height": 11.125}

        result = file_drawer_component.validate(config, deep_context)

        assert result.is_valid

    def test_validate_legal_file_minimum_boundary(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test legal file drawer exactly at minimum height boundary.

        box_height = front_height - 0.625
        For box_height = 12.0, front_height = 12.625
        """
        config = {"file_type": "legal", "front_height": 12.625}

        result = file_drawer_component.validate(config, deep_context)

        assert result.is_valid

    def test_validate_default_file_type_is_letter(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that default file_type is 'letter' when not specified."""
        # Valid for letter (10.5" min), but too short for legal (12.0" min)
        # box_height = 11.125 - 0.625 = 10.5"
        config = {"front_height": 11.125}

        result = file_drawer_component.validate(config, deep_context)

        # Should pass with default letter type
        assert result.is_valid

    def test_validate_inherits_base_drawer_validation(
        self, file_drawer_component: FileDrawerComponent
    ) -> None:
        """Test that file drawer inherits base drawer validation rules."""
        # Create context too shallow for slides (V-01)
        shallow_context = ComponentContext(
            width=24.0,
            height=72.0,
            depth=10.0,  # Too shallow for 12" slides
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )
        config = {"file_type": "letter", "front_height": 12.0, "slide_length": 12}

        result = file_drawer_component.validate(config, shallow_context)

        assert not result.is_valid
        # Should have error about slide length from base class
        assert any("exceeds section depth" in err for err in result.errors)


class TestFileDrawerComponentGeneration:
    """Tests for FileDrawerComponent.generate()."""

    def test_generate_returns_generation_result(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"file_type": "letter", "front_height": 12.0}

        result = file_drawer_component.generate(config, deep_context)

        assert isinstance(result, GenerationResult)

    def test_generate_creates_six_panels(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that generate creates 6 panels (front, box front, 2 sides, bottom, top panel)."""
        config = {"file_type": "legal", "front_height": 14.0}

        result = file_drawer_component.generate(config, deep_context)

        # 5 drawer panels + 1 top panel (horizontal divider)
        assert len(result.panels) == 6

    def test_generate_creates_drawer_front_with_correct_height(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that generate creates drawer front with specified height."""
        config = {"file_type": "letter", "front_height": 12.0}

        result = file_drawer_component.generate(config, deep_context)

        front_panel = next(p for p in result.panels if p.panel_type == PanelType.DRAWER_FRONT)
        assert front_panel.height == 12.0

    def test_generate_box_height_sufficient_for_files(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that generated box height meets file requirements."""
        config = {"file_type": "letter", "front_height": 12.0}

        result = file_drawer_component.generate(config, deep_context)

        # box_height = 12.0 - 0.125 - 0.5 = 11.375"
        expected_box_height = 12.0 - 0.125 - 0.5
        side_panel = next(p for p in result.panels if p.panel_type == PanelType.DRAWER_SIDE)
        assert side_panel.height == pytest.approx(expected_box_height)
        # Verify it meets letter file requirement
        assert side_panel.height >= FileDrawerComponent.MIN_FILE_HEIGHT["letter"]

    def test_generate_includes_hardware(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that generate includes hardware items."""
        config = {"file_type": "letter", "front_height": 12.0}

        result = file_drawer_component.generate(config, deep_context)

        assert len(result.hardware) > 0

    def test_generate_metadata_includes_slide_info(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test that metadata includes drawer specification."""
        config = {"file_type": "legal", "front_height": 14.0, "slide_type": "undermount"}

        result = file_drawer_component.generate(config, deep_context)

        assert "drawer_spec" in result.metadata
        assert result.metadata["slide_type"] == "undermount"


class TestFileDrawerComponentIntegration:
    """Integration tests for FileDrawerComponent."""

    @pytest.fixture(autouse=True)
    def ensure_file_drawer_registered(self) -> None:
        """Ensure drawer.file is registered for integration tests."""
        if "drawer.file" not in component_registry.list():
            component_registry.register("drawer.file")(FileDrawerComponent)

    def test_full_workflow_validate_generate_hardware(
        self, deep_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        # Get component from registry
        component_class = component_registry.get("drawer.file")
        component = component_class()

        config = {
            "file_type": "legal",
            "front_height": 14.0,
            "slide_type": "undermount",
            "soft_close": True,
        }

        # Validate
        validation = component.validate(config, deep_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, deep_context)
        # 5 drawer panels + 1 top panel (horizontal divider)
        assert len(generation.panels) == 6
        assert "drawer_spec" in generation.metadata

        # Hardware
        hardware = component.hardware(config, deep_context)
        assert len(hardware) == 4  # slides, screws, handle, edge banding

    def test_file_drawer_with_different_file_types(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test file drawer with both letter and legal file types."""
        file_types = [
            ("letter", 12.0),  # front_height gives 11.375" box (> 10.5")
            ("legal", 14.0),   # front_height gives 13.375" box (> 12.0")
        ]

        for file_type, front_height in file_types:
            config = {"file_type": file_type, "front_height": front_height}

            validation = file_drawer_component.validate(config, deep_context)
            assert validation.is_valid, f"Failed validation for file_type: {file_type}"

            generation = file_drawer_component.generate(config, deep_context)
            # 5 drawer panels + 1 top panel (horizontal divider)
            assert len(generation.panels) == 6, f"Wrong panel count for file_type: {file_type}"


class TestFileDrawerComponentEdgeCases:
    """Edge case tests for FileDrawerComponent."""

    def test_file_drawer_with_center_mount_and_insufficient_height(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test file drawer with both center mount warning and height error."""
        # This config should have both a warning (center mount) and error (height)
        config = {
            "file_type": "letter",
            "front_height": 8.0,  # Too short: box = 7.375" < 10.5"
            "slide_type": "center_mount",
        }

        result = file_drawer_component.validate(config, deep_context)

        # Should have error about height
        assert not result.is_valid
        assert any("below minimum" in err for err in result.errors)
        # Should also have warning about center mount
        assert len(result.warnings) > 0
        assert any("center_mount" in warn for warn in result.warnings)

    def test_file_drawer_min_height_constants(
        self, file_drawer_component: FileDrawerComponent
    ) -> None:
        """Test that MIN_FILE_HEIGHT constants are correctly defined."""
        assert file_drawer_component.MIN_FILE_HEIGHT["letter"] == 10.5
        assert file_drawer_component.MIN_FILE_HEIGHT["legal"] == 12.0

    def test_file_drawer_just_below_letter_minimum(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test letter file drawer just below minimum height fails."""
        # box_height = 11.124 - 0.625 = 10.499" < 10.5"
        config = {"file_type": "letter", "front_height": 11.124}

        result = file_drawer_component.validate(config, deep_context)

        assert not result.is_valid
        assert any("below minimum" in err for err in result.errors)

    def test_file_drawer_just_below_legal_minimum(
        self, file_drawer_component: FileDrawerComponent, deep_context: ComponentContext
    ) -> None:
        """Test legal file drawer just below minimum height fails."""
        # box_height = 12.624 - 0.625 = 11.999" < 12.0"
        config = {"file_type": "legal", "front_height": 12.624}

        result = file_drawer_component.validate(config, deep_context)

        assert not result.is_valid
        assert any("below minimum" in err for err in result.errors)
