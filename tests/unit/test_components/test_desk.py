"""Unit tests for desk components (FRD-18).

This module contains comprehensive tests for all desk-related components:
- DeskSurfaceComponent (desk.surface)
- DeskPedestalComponent (desk.pedestal)
- KeyboardTrayComponent (desk.keyboard_tray) - also in test_keyboard_tray_component.py
- MonitorShelfComponent (desk.monitor_shelf)
- DeskHutchComponent (desk.hutch)
- LShapedDeskComponent (desk.l_shaped)

Also tests desk-related value objects:
- DeskType, EdgeTreatment, PedestalType enums
- DeskDimensions dataclass
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    HardwareItem,
    component_registry,
)
from cabinets.domain.components.desk import (
    SITTING_DESK_HEIGHT_DEFAULT,
    SITTING_DESK_HEIGHT_MAX,
    SITTING_DESK_HEIGHT_MIN,
    STANDING_DESK_HEIGHT_DEFAULT,
    STANDING_DESK_HEIGHT_MAX,
    STANDING_DESK_HEIGHT_MIN,
    CornerConnectionType,
    DeskHutchComponent,
    DeskPedestalComponent,
    DeskSurfaceComponent,
    GrommetSpec,
    KeyboardTrayComponent,
    LShapedDeskComponent,
    LShapedDeskConfiguration,
    MonitorShelfComponent,
)
from cabinets.domain.value_objects import (
    DeskDimensions,
    DeskType,
    EdgeTreatment,
    MaterialSpec,
    PanelType,
    PedestalType,
    Position,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def standard_context() -> ComponentContext:
    """Standard desk context: 48" wide, 84" tall section, 24" depth."""
    return ComponentContext(
        width=48.0,
        height=84.0,
        depth=24.0,
        position=Position(0, 0),
        material=MaterialSpec.standard_3_4(),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


@pytest.fixture
def narrow_context() -> ComponentContext:
    """Narrow context for testing width constraints."""
    return ComponentContext(
        width=24.0,
        height=84.0,
        depth=18.0,
        position=Position(0, 0),
        material=MaterialSpec.standard_3_4(),
        section_index=0,
        cabinet_width=24.0,
        cabinet_height=84.0,
        cabinet_depth=18.0,
    )


@pytest.fixture
def wide_context() -> ComponentContext:
    """Wide context for L-shaped desk testing."""
    return ComponentContext(
        width=96.0,
        height=84.0,
        depth=24.0,
        position=Position(0, 0),
        material=MaterialSpec.standard_3_4(),
        section_index=0,
        cabinet_width=96.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


# =============================================================================
# DeskSurfaceComponent Tests
# =============================================================================


class TestDeskSurfaceRegistration:
    """Test desk.surface component registration."""

    def test_component_registered(self):
        """desk.surface is registered in component registry."""
        component_cls = component_registry.get("desk.surface")
        assert component_cls is DeskSurfaceComponent

    def test_component_in_registry_list(self):
        """desk.surface appears in registry list."""
        assert "desk.surface" in component_registry.list()

    def test_component_instantiation(self):
        """DeskSurfaceComponent can be instantiated."""
        component = DeskSurfaceComponent()
        assert component is not None


class TestDeskSurfaceValidation:
    """Test desk.surface validate() method."""

    def test_valid_sitting_height(self, standard_context):
        """Valid sitting desk height passes validation."""
        component = DeskSurfaceComponent()
        config = {"desk_height": 30.0, "depth": 24.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_valid_standing_height(self, standard_context):
        """Valid standing desk height passes validation."""
        component = DeskSurfaceComponent()
        config = {"desk_height": 42.0, "depth": 24.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_height_too_low(self, standard_context):
        """Desk height below 26" produces error."""
        component = DeskSurfaceComponent()
        config = {"desk_height": 24.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "26" in result.errors[0] or "outside" in result.errors[0].lower()

    def test_height_too_high(self, standard_context):
        """Desk height above 50" produces error."""
        component = DeskSurfaceComponent()
        config = {"desk_height": 52.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "50" in result.errors[0] or "outside" in result.errors[0].lower()

    def test_height_between_ranges_warning(self, standard_context):
        """Height between sitting and standing ranges produces warning."""
        component = DeskSurfaceComponent()
        config = {"desk_height": 35.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("between" in w.lower() for w in result.warnings)

    def test_depth_too_shallow(self, standard_context):
        """Desk depth below 18" produces error."""
        component = DeskSurfaceComponent()
        config = {"depth": 16.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "shallow" in result.errors[0].lower()

    def test_depth_too_deep(self, standard_context):
        """Desk depth above 36" produces error."""
        component = DeskSurfaceComponent()
        config = {"depth": 40.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "exceeds" in result.errors[0].lower() or "36" in result.errors[0]

    def test_non_standard_depth_warning(self, standard_context):
        """Non-standard depth produces warning."""
        component = DeskSurfaceComponent()
        config = {"depth": 26.0}  # Not in STANDARD_DEPTHS
        result = component.validate(config, standard_context)
        assert any("non-standard" in w.lower() for w in result.warnings)

    def test_thin_desktop_warning(self, standard_context):
        """Desktop thickness of 3/4" produces warning."""
        component = DeskSurfaceComponent()
        config = {"thickness": 0.75}
        result = component.validate(config, standard_context)
        assert any("flex" in w.lower() for w in result.warnings)

    def test_thickness_too_thin_error(self, standard_context):
        """Desktop thickness below 3/4" produces error."""
        component = DeskSurfaceComponent()
        config = {"thickness": 0.5}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "0.75" in result.errors[0]

    def test_invalid_edge_treatment(self, standard_context):
        """Invalid edge treatment produces error."""
        component = DeskSurfaceComponent()
        config = {"edge_treatment": "invalid"}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "edge" in result.errors[0].lower()

    def test_valid_edge_treatments(self, standard_context):
        """All valid edge treatments pass validation."""
        component = DeskSurfaceComponent()
        for edge in component.VALID_EDGE_TREATMENTS:
            config = {"edge_treatment": edge}
            result = component.validate(config, standard_context)
            assert len(result.errors) == 0, f"Failed for edge treatment: {edge}"

    def test_oversized_grommet_error(self, standard_context):
        """Grommet diameter > 3.5" produces error."""
        component = DeskSurfaceComponent()
        config = {"grommets": [{"x_position": 24, "y_position": 20, "diameter": 5.0}]}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "grommet" in result.errors[0].lower()

    def test_standard_grommet_sizes_valid(self, standard_context):
        """Standard grommet sizes pass validation."""
        component = DeskSurfaceComponent()
        for diameter in [2.0, 2.5, 3.0]:
            config = {
                "grommets": [{"x_position": 24, "y_position": 20, "diameter": diameter}]
            }
            result = component.validate(config, standard_context)
            assert len(result.errors) == 0, f"Failed for grommet diameter: {diameter}"

    def test_default_config_passes(self, standard_context):
        """Default configuration passes validation."""
        component = DeskSurfaceComponent()
        result = component.validate({}, standard_context)
        assert len(result.errors) == 0


class TestDeskSurfaceGeneration:
    """Test desk.surface generate() method."""

    def test_generates_desktop_panel(self, standard_context):
        """Generate creates DESKTOP panel."""
        component = DeskSurfaceComponent()
        config = {"desk_height": 30.0, "depth": 24.0}
        result = component.generate(config, standard_context)
        desktop_panels = [p for p in result.panels if p.panel_type == PanelType.DESKTOP]
        assert len(desktop_panels) == 1
        assert desktop_panels[0].width == 48.0

    def test_desktop_depth_dimension(self, standard_context):
        """Desktop panel height equals configured depth."""
        component = DeskSurfaceComponent()
        config = {"depth": 24.0}
        result = component.generate(config, standard_context)
        desktop = [p for p in result.panels if p.panel_type == PanelType.DESKTOP][0]
        assert desktop.height == 24.0  # depth becomes height in 2D

    def test_waterfall_edge_panel(self, standard_context):
        """Waterfall edge treatment creates additional panel."""
        component = DeskSurfaceComponent()
        config = {"edge_treatment": "waterfall", "desk_height": 30.0}
        result = component.generate(config, standard_context)
        waterfall_panels = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ]
        assert len(waterfall_panels) == 1

    def test_waterfall_edge_height(self, standard_context):
        """Waterfall edge has correct height (desk height - 4")."""
        component = DeskSurfaceComponent()
        config = {"edge_treatment": "waterfall", "desk_height": 30.0}
        result = component.generate(config, standard_context)
        waterfall = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ][0]
        assert waterfall.height == 26.0  # 30 - 4

    def test_no_waterfall_for_square_edge(self, standard_context):
        """Square edge treatment does not create waterfall panel."""
        component = DeskSurfaceComponent()
        config = {"edge_treatment": "square"}
        result = component.generate(config, standard_context)
        waterfall_panels = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ]
        assert len(waterfall_panels) == 0

    def test_grommet_cutout_in_metadata(self, standard_context):
        """Grommets appear as cutouts in metadata."""
        component = DeskSurfaceComponent()
        config = {"grommets": [{"x_position": 24, "y_position": 20, "diameter": 2.5}]}
        result = component.generate(config, standard_context)
        assert "cutouts" in result.metadata
        assert len(result.metadata["cutouts"]) == 1

    def test_grommet_hardware(self, standard_context):
        """Grommets appear in hardware list."""
        component = DeskSurfaceComponent()
        config = {"grommets": [{"x_position": 24, "y_position": 20, "diameter": 2.5}]}
        result = component.generate(config, standard_context)
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 1

    def test_multiple_grommets(self, standard_context):
        """Multiple grommets create multiple cutouts and hardware."""
        component = DeskSurfaceComponent()
        config = {
            "grommets": [
                {"x_position": 12, "y_position": 20, "diameter": 2.5},
                {"x_position": 36, "y_position": 20, "diameter": 2.5},
            ]
        }
        result = component.generate(config, standard_context)
        assert len(result.metadata["cutouts"]) == 2
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 2

    def test_edge_banding_hardware(self, standard_context):
        """Edge banding appears in hardware list."""
        component = DeskSurfaceComponent()
        config = {}
        result = component.generate(config, standard_context)
        edge_banding = [h for h in result.hardware if "Edge Banding" in h.name]
        assert len(edge_banding) == 1

    def test_floating_mount_hardware(self, standard_context):
        """Floating mount includes wall cleats."""
        component = DeskSurfaceComponent()
        config = {"mounting": "floating"}
        result = component.generate(config, standard_context)
        cleats = [h for h in result.hardware if "Cleat" in h.name]
        assert len(cleats) == 1
        lag_screws = [h for h in result.hardware if "Lag Screw" in h.name]
        assert len(lag_screws) == 1

    def test_wide_desk_extra_cleat(self, wide_context):
        """Wide floating desk (>48") gets extra cleat."""
        component = DeskSurfaceComponent()
        config = {"mounting": "floating"}
        result = component.generate(config, wide_context)
        cleats = [h for h in result.hardware if "Cleat" in h.name][0]
        assert cleats.quantity == 3

    def test_pedestal_mount_no_cleats(self, standard_context):
        """Pedestal mount does not include wall cleats."""
        component = DeskSurfaceComponent()
        config = {"mounting": "pedestal"}
        result = component.generate(config, standard_context)
        cleats = [h for h in result.hardware if "Cleat" in h.name]
        assert len(cleats) == 0

    def test_exposed_edges_increase_banding(self, standard_context):
        """Exposed left/right edges increase edge banding length."""
        component = DeskSurfaceComponent()
        config_basic = {"depth": 24.0}
        config_exposed = {"depth": 24.0, "exposed_left": True, "exposed_right": True}

        result_basic = component.generate(config_basic, standard_context)
        result_exposed = component.generate(config_exposed, standard_context)

        banding_basic = [h for h in result_basic.hardware if "Edge Banding" in h.name][
            0
        ]
        banding_exposed = [
            h for h in result_exposed.hardware if "Edge Banding" in h.name
        ][0]

        # Exposed should have more linear inches noted
        assert "48.0" in banding_basic.notes  # Just front edge
        # With exposed sides: 48 + 24 + 24 = 96
        assert "96.0" in banding_exposed.notes

    def test_desktop_panel_metadata(self, standard_context):
        """Desktop panel has correct metadata."""
        component = DeskSurfaceComponent()
        config = {"edge_treatment": "bullnose"}
        result = component.generate(config, standard_context)
        desktop = [p for p in result.panels if p.panel_type == PanelType.DESKTOP][0]
        assert desktop.metadata["component"] == "desk.surface"
        assert desktop.metadata["edge_treatment"] == "bullnose"
        assert desktop.metadata["is_desktop"] is True

    def test_returns_generation_result(self, standard_context):
        """Generate returns GenerationResult instance."""
        component = DeskSurfaceComponent()
        result = component.generate({}, standard_context)
        assert isinstance(result, GenerationResult)


class TestDeskSurfaceHardware:
    """Test desk.surface hardware() method."""

    def test_hardware_method_returns_list(self, standard_context):
        """hardware() method returns a list of HardwareItem."""
        component = DeskSurfaceComponent()
        result = component.hardware({}, standard_context)
        assert isinstance(result, list)
        assert all(isinstance(h, HardwareItem) for h in result)

    def test_hardware_matches_generate(self, standard_context):
        """hardware() returns same items as generate().hardware."""
        component = DeskSurfaceComponent()
        config = {"grommets": [{"x_position": 24, "y_position": 20, "diameter": 2.5}]}

        gen_result = component.generate(config, standard_context)
        hw_result = component.hardware(config, standard_context)

        assert len(hw_result) == len(gen_result.hardware)


# =============================================================================
# DeskPedestalComponent Tests
# =============================================================================


class TestDeskPedestalRegistration:
    """Test desk.pedestal component registration."""

    def test_component_registered(self):
        """desk.pedestal is registered in component registry."""
        component_cls = component_registry.get("desk.pedestal")
        assert component_cls is DeskPedestalComponent

    def test_component_in_registry_list(self):
        """desk.pedestal appears in registry list."""
        assert "desk.pedestal" in component_registry.list()

    def test_component_instantiation(self):
        """DeskPedestalComponent can be instantiated."""
        component = DeskPedestalComponent()
        assert component is not None


class TestDeskPedestalValidation:
    """Test desk.pedestal validate() method."""

    def test_valid_storage_pedestal(self, standard_context):
        """Valid storage pedestal passes validation."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "storage", "width": 18.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_valid_file_pedestal(self, standard_context):
        """Valid file pedestal passes validation."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "width": 18.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_valid_open_pedestal(self, standard_context):
        """Valid open pedestal passes validation."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "open", "width": 15.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_invalid_pedestal_type(self, standard_context):
        """Invalid pedestal type produces error."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "invalid"}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "invalid" in result.errors[0].lower()

    def test_narrow_pedestal_warning(self, standard_context):
        """Narrow pedestal produces warning."""
        component = DeskPedestalComponent()
        config = {"width": 11.0}
        result = component.validate(config, standard_context)
        assert any("limit" in w.lower() for w in result.warnings)

    def test_non_standard_width_warning(self, standard_context):
        """Non-standard width produces warning."""
        component = DeskPedestalComponent()
        config = {"width": 16.0}  # Not in STANDARD_WIDTHS
        result = component.validate(config, standard_context)
        assert any("non-standard" in w.lower() for w in result.warnings)

    def test_file_pedestal_minimum_width(self, standard_context):
        """File pedestal requires minimum 15" width."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "width": 14.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "15" in result.errors[0]

    def test_file_pedestal_at_minimum_width(self, standard_context):
        """File pedestal at minimum 15" width passes."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "width": 15.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_default_config_passes(self, standard_context):
        """Default configuration passes validation."""
        component = DeskPedestalComponent()
        result = component.validate({}, standard_context)
        assert len(result.errors) == 0


class TestDeskPedestalGeneration:
    """Test desk.pedestal generate() method."""

    def test_generates_side_panels(self, standard_context):
        """Generate creates LEFT_SIDE and RIGHT_SIDE panels."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "storage", "width": 18.0}
        result = component.generate(config, standard_context)
        sides = [
            p
            for p in result.panels
            if p.panel_type in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE)
        ]
        assert len(sides) == 2

    def test_generates_bottom_panel(self, standard_context):
        """Generate creates BOTTOM panel."""
        component = DeskPedestalComponent()
        config = {}
        result = component.generate(config, standard_context)
        bottoms = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottoms) == 1

    def test_generates_back_panel(self, standard_context):
        """Generate creates BACK panel."""
        component = DeskPedestalComponent()
        config = {}
        result = component.generate(config, standard_context)
        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(backs) == 1

    def test_wire_chase_panel(self, standard_context):
        """Wire chase panel generated when enabled."""
        component = DeskPedestalComponent()
        config = {"wire_chase": True}
        result = component.generate(config, standard_context)
        chases = [p for p in result.panels if p.panel_type == PanelType.WIRE_CHASE]
        assert len(chases) == 1

    def test_no_wire_chase_when_disabled(self, standard_context):
        """No wire chase panel when disabled."""
        component = DeskPedestalComponent()
        config = {"wire_chase": False}
        result = component.generate(config, standard_context)
        chases = [p for p in result.panels if p.panel_type == PanelType.WIRE_CHASE]
        assert len(chases) == 0

    def test_file_pedestal_hardware(self, standard_context):
        """File pedestal includes file frame hardware."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "width": 18.0}
        result = component.generate(config, standard_context)
        file_frames = [h for h in result.hardware if "File Frame" in h.name]
        assert len(file_frames) == 1

    def test_file_pedestal_slide_count(self, standard_context):
        """File pedestal has 4 drawer slides (2 drawers x 2)."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "width": 18.0}
        result = component.generate(config, standard_context)
        slides = [h for h in result.hardware if "Slide" in h.name]
        assert len(slides) == 1
        assert slides[0].quantity == 4

    def test_storage_pedestal_drawer_count(self, standard_context):
        """Storage pedestal slide count matches drawer count."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "storage", "drawer_count": 4}
        result = component.generate(config, standard_context)
        slides = [h for h in result.hardware if "Slide" in h.name]
        assert slides[0].quantity == 8  # 4 drawers * 2 slides

    def test_storage_pedestal_default_drawers(self, standard_context):
        """Storage pedestal defaults to 3 drawers."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "storage"}
        result = component.generate(config, standard_context)
        slides = [h for h in result.hardware if "Slide" in h.name]
        assert slides[0].quantity == 6  # 3 drawers * 2 slides

    def test_open_pedestal_shelf_pins(self, standard_context):
        """Open pedestal includes shelf pins, no slides."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "open", "shelf_count": 3}
        result = component.generate(config, standard_context)
        pins = [h for h in result.hardware if "Shelf Pin" in h.name]
        assert len(pins) == 1
        assert pins[0].quantity == 12  # 3 shelves * 4 pins
        slides = [h for h in result.hardware if "Slide" in h.name]
        assert len(slides) == 0

    def test_open_pedestal_default_shelves(self, standard_context):
        """Open pedestal defaults to 2 shelves."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "open"}
        result = component.generate(config, standard_context)
        pins = [h for h in result.hardware if "Shelf Pin" in h.name]
        assert pins[0].quantity == 8  # 2 shelves * 4 pins

    def test_pedestal_height_calculation(self, standard_context):
        """Pedestal height is desktop_height - desktop_thickness."""
        component = DeskPedestalComponent()
        config = {"desktop_height": 30.0, "desktop_thickness": 1.0}
        result = component.generate(config, standard_context)
        # Side panel height should be 29"
        side = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE][0]
        assert side.height == 29.0

    def test_pedestal_metadata(self, standard_context):
        """Pedestal metadata includes type and dimensions."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "wire_chase": True}
        result = component.generate(config, standard_context)
        assert result.metadata["pedestal_type"] == "file"
        assert result.metadata["wire_chase"] is True

    def test_file_type_letter(self, standard_context):
        """Letter file type in hardware SKU."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "file_type": "letter", "width": 18.0}
        result = component.generate(config, standard_context)
        file_frame = [h for h in result.hardware if "File Frame" in h.name][0]
        assert "LETTER" in file_frame.sku

    def test_file_type_legal(self, standard_context):
        """Legal file type in hardware SKU."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "file_type": "legal", "width": 18.0}
        result = component.generate(config, standard_context)
        file_frame = [h for h in result.hardware if "File Frame" in h.name][0]
        assert "LEGAL" in file_frame.sku


class TestDeskPedestalHardware:
    """Test desk.pedestal hardware() method."""

    def test_hardware_method_returns_list(self, standard_context):
        """hardware() method returns a list."""
        component = DeskPedestalComponent()
        result = component.hardware({}, standard_context)
        assert isinstance(result, list)
        assert all(isinstance(h, HardwareItem) for h in result)

    def test_hardware_matches_generate(self, standard_context):
        """hardware() returns same items as generate().hardware."""
        component = DeskPedestalComponent()
        config = {"pedestal_type": "file", "width": 18.0}

        gen_result = component.generate(config, standard_context)
        hw_result = component.hardware(config, standard_context)

        assert len(hw_result) == len(gen_result.hardware)


# =============================================================================
# MonitorShelfComponent Tests
# =============================================================================


class TestMonitorShelfRegistration:
    """Test desk.monitor_shelf component registration."""

    def test_component_registered(self):
        """desk.monitor_shelf is registered in component registry."""
        component_cls = component_registry.get("desk.monitor_shelf")
        assert component_cls is MonitorShelfComponent

    def test_component_in_registry_list(self):
        """desk.monitor_shelf appears in registry list."""
        assert "desk.monitor_shelf" in component_registry.list()

    def test_component_instantiation(self):
        """MonitorShelfComponent can be instantiated."""
        component = MonitorShelfComponent()
        assert component is not None


class TestMonitorShelfValidation:
    """Test desk.monitor_shelf validate() method."""

    def test_valid_standard_height(self, standard_context):
        """Standard height (6") passes validation."""
        component = MonitorShelfComponent()
        config = {"height": 6.0, "width": 24.0, "depth": 10.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_all_standard_heights(self, standard_context):
        """All standard heights pass validation."""
        component = MonitorShelfComponent()
        for height in component.STANDARD_HEIGHTS:
            config = {"height": height}
            result = component.validate(config, standard_context)
            assert len(result.errors) == 0, f"Failed for height: {height}"
            assert len(result.warnings) == 0, f"Warning for height: {height}"

    def test_non_standard_height_warning(self, standard_context):
        """Non-standard height produces warning."""
        component = MonitorShelfComponent()
        config = {"height": 5.0}  # Not in STANDARD_HEIGHTS
        result = component.validate(config, standard_context)
        assert any("non-standard" in w.lower() for w in result.warnings)

    def test_width_exceeds_desk_width(self, narrow_context):
        """Shelf width exceeding desk width produces error."""
        component = MonitorShelfComponent()
        config = {"width": 30.0}  # > 24" desk width
        result = component.validate(config, narrow_context)
        assert len(result.errors) == 1
        assert "exceeds" in result.errors[0].lower()

    def test_width_equals_desk_width(self, standard_context):
        """Shelf width equal to desk width passes."""
        component = MonitorShelfComponent()
        config = {"width": 48.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_depth_too_shallow(self, standard_context):
        """Shelf depth below 6" produces error."""
        component = MonitorShelfComponent()
        config = {"depth": 5.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "shallow" in result.errors[0].lower()

    def test_depth_unusually_deep_warning(self, standard_context):
        """Shelf depth above 14" produces warning."""
        component = MonitorShelfComponent()
        config = {"depth": 15.0}
        result = component.validate(config, standard_context)
        assert any("unusually deep" in w.lower() for w in result.warnings)

    def test_height_too_short(self, standard_context):
        """Shelf height below 2" produces error."""
        component = MonitorShelfComponent()
        config = {"height": 1.5}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "too short" in result.errors[0].lower()

    def test_height_unusually_tall_warning(self, standard_context):
        """Shelf height above 12" produces warning."""
        component = MonitorShelfComponent()
        config = {"height": 14.0}
        result = component.validate(config, standard_context)
        assert any("unusually tall" in w.lower() for w in result.warnings)

    def test_default_config_passes(self, standard_context):
        """Default configuration passes validation."""
        component = MonitorShelfComponent()
        result = component.validate({}, standard_context)
        assert len(result.errors) == 0


class TestMonitorShelfGeneration:
    """Test desk.monitor_shelf generate() method."""

    def test_generates_shelf_panel(self, standard_context):
        """Generate creates SHELF panel."""
        component = MonitorShelfComponent()
        config = {}
        result = component.generate(config, standard_context)
        shelves = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelves) == 1

    def test_generates_side_supports(self, standard_context):
        """Generate creates LEFT_SIDE and RIGHT_SIDE panels."""
        component = MonitorShelfComponent()
        config = {}
        result = component.generate(config, standard_context)
        sides = [
            p
            for p in result.panels
            if p.panel_type in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE)
        ]
        assert len(sides) == 2

    def test_generates_back_panel(self, standard_context):
        """Generate creates BACK panel."""
        component = MonitorShelfComponent()
        config = {}
        result = component.generate(config, standard_context)
        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(backs) == 1

    def test_cable_pass_through_back(self, standard_context):
        """Cable pass-through creates shorter back panel."""
        component = MonitorShelfComponent()
        config = {"cable_pass": True, "height": 6.0}
        result = component.generate(config, standard_context)
        back = [p for p in result.panels if p.panel_type == PanelType.BACK][0]
        # Back should be 6 - 2 = 4" (2" cable gap)
        assert back.height == 4.0

    def test_no_cable_pass_full_back(self, standard_context):
        """No cable pass-through creates full height back panel."""
        component = MonitorShelfComponent()
        config = {"cable_pass": False, "height": 6.0}
        result = component.generate(config, standard_context)
        back = [p for p in result.panels if p.panel_type == PanelType.BACK][0]
        assert back.height == 6.0

    def test_cable_pass_metadata(self, standard_context):
        """Cable pass info in back panel metadata."""
        component = MonitorShelfComponent()
        config = {"cable_pass": True}
        result = component.generate(config, standard_context)
        back = [p for p in result.panels if p.panel_type == PanelType.BACK][0]
        assert back.metadata.get("cable_pass") is True

    def test_arm_mount_hardware(self, standard_context):
        """Monitor arm mount includes hardware."""
        component = MonitorShelfComponent()
        config = {"arm_mount": True}
        result = component.generate(config, standard_context)
        arm_mount = [h for h in result.hardware if "Monitor Arm" in h.name]
        assert len(arm_mount) >= 1
        plate = [h for h in result.hardware if "Reinforcement Plate" in h.name]
        assert len(plate) == 1

    def test_no_arm_mount_by_default(self, standard_context):
        """No arm mount hardware by default."""
        component = MonitorShelfComponent()
        config = {"arm_mount": False}
        result = component.generate(config, standard_context)
        arm_mount = [h for h in result.hardware if "Monitor Arm" in h.name]
        assert len(arm_mount) == 0

    def test_assembly_hardware(self, standard_context):
        """Assembly hardware included."""
        component = MonitorShelfComponent()
        result = component.generate({}, standard_context)
        screws = [h for h in result.hardware if "Screw" in h.name]
        assert len(screws) == 1

    def test_shelf_dimensions(self, standard_context):
        """Shelf panel has correct dimensions."""
        component = MonitorShelfComponent()
        config = {"width": 24.0, "depth": 10.0}
        result = component.generate(config, standard_context)
        shelf = [p for p in result.panels if p.panel_type == PanelType.SHELF][0]
        assert shelf.width == 24.0
        assert shelf.height == 10.0  # depth becomes height in 2D

    def test_side_support_dimensions(self, standard_context):
        """Side support panels have correct dimensions."""
        component = MonitorShelfComponent()
        config = {"height": 6.0, "depth": 10.0}
        result = component.generate(config, standard_context)
        side = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE][0]
        assert side.width == 10.0  # depth
        assert side.height == 6.0  # riser height

    def test_result_metadata(self, standard_context):
        """Result metadata includes configuration."""
        component = MonitorShelfComponent()
        config = {"cable_pass": True, "arm_mount": True, "height": 8.0}
        result = component.generate(config, standard_context)
        assert result.metadata["cable_pass"] is True
        assert result.metadata["arm_mount"] is True
        assert result.metadata["riser_height"] == 8.0


class TestMonitorShelfHardware:
    """Test desk.monitor_shelf hardware() method."""

    def test_hardware_method_returns_list(self, standard_context):
        """hardware() method returns a list."""
        component = MonitorShelfComponent()
        result = component.hardware({}, standard_context)
        assert isinstance(result, list)

    def test_hardware_matches_generate(self, standard_context):
        """hardware() returns same items as generate().hardware."""
        component = MonitorShelfComponent()
        config = {"arm_mount": True}

        gen_result = component.generate(config, standard_context)
        hw_result = component.hardware(config, standard_context)

        assert len(hw_result) == len(gen_result.hardware)


# =============================================================================
# DeskHutchComponent Tests
# =============================================================================


class TestDeskHutchRegistration:
    """Test desk.hutch component registration."""

    def test_component_registered(self):
        """desk.hutch is registered in component registry."""
        component_cls = component_registry.get("desk.hutch")
        assert component_cls is DeskHutchComponent

    def test_component_in_registry_list(self):
        """desk.hutch appears in registry list."""
        assert "desk.hutch" in component_registry.list()

    def test_component_instantiation(self):
        """DeskHutchComponent can be instantiated."""
        component = DeskHutchComponent()
        assert component is not None


class TestDeskHutchValidation:
    """Test desk.hutch validate() method."""

    def test_valid_config(self, standard_context):
        """Valid hutch configuration passes validation."""
        component = DeskHutchComponent()
        config = {"head_clearance": 15.0, "depth": 12.0, "height": 24.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 0

    def test_head_clearance_warning(self, standard_context):
        """Head clearance below 15" produces warning."""
        component = DeskHutchComponent()
        config = {"head_clearance": 12.0}
        result = component.validate(config, standard_context)
        assert any(
            "head clearance" in w.lower() or "obstruct" in w.lower()
            for w in result.warnings
        )

    def test_depth_too_shallow(self, standard_context):
        """Hutch depth below 6" produces error."""
        component = DeskHutchComponent()
        config = {"depth": 5.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "6" in result.errors[0]

    def test_deep_hutch_warning(self, standard_context):
        """Deep hutch (>16") produces warning."""
        component = DeskHutchComponent()
        config = {"depth": 18.0}
        result = component.validate(config, standard_context)
        assert any(
            "interfere" in w.lower() or "monitor" in w.lower() for w in result.warnings
        )

    def test_height_too_short(self, standard_context):
        """Hutch height below 12" produces error."""
        component = DeskHutchComponent()
        config = {"height": 10.0}
        result = component.validate(config, standard_context)
        assert len(result.errors) == 1
        assert "too short" in result.errors[0].lower()

    def test_height_unusually_tall_warning(self, standard_context):
        """Hutch height above 48" produces warning."""
        component = DeskHutchComponent()
        config = {"height": 50.0}
        result = component.validate(config, standard_context)
        assert any("unusually tall" in w.lower() for w in result.warnings)

    def test_default_config_passes(self, standard_context):
        """Default configuration passes validation."""
        component = DeskHutchComponent()
        result = component.validate({}, standard_context)
        assert len(result.errors) == 0


class TestDeskHutchGeneration:
    """Test desk.hutch generate() method."""

    def test_generates_side_panels(self, standard_context):
        """Generate creates LEFT_SIDE and RIGHT_SIDE panels."""
        component = DeskHutchComponent()
        config = {}
        result = component.generate(config, standard_context)
        sides = [
            p
            for p in result.panels
            if p.panel_type in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE)
        ]
        assert len(sides) == 2

    def test_generates_top_panel(self, standard_context):
        """Generate creates TOP panel."""
        component = DeskHutchComponent()
        config = {}
        result = component.generate(config, standard_context)
        tops = [p for p in result.panels if p.panel_type == PanelType.TOP]
        assert len(tops) == 1

    def test_generates_bottom_panel(self, standard_context):
        """Generate creates BOTTOM panel."""
        component = DeskHutchComponent()
        config = {}
        result = component.generate(config, standard_context)
        bottoms = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottoms) == 1

    def test_generates_back_panel(self, standard_context):
        """Generate creates BACK panel."""
        component = DeskHutchComponent()
        config = {}
        result = component.generate(config, standard_context)
        backs = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(backs) == 1

    def test_generates_shelves(self, standard_context):
        """Generate creates SHELF panels."""
        component = DeskHutchComponent()
        config = {"shelf_count": 2}
        result = component.generate(config, standard_context)
        shelves = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelves) == 2

    def test_no_shelves_when_zero(self, standard_context):
        """No shelf panels when shelf_count is 0."""
        component = DeskHutchComponent()
        config = {"shelf_count": 0}
        result = component.generate(config, standard_context)
        shelves = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelves) == 0

    def test_shelf_pins_hardware(self, standard_context):
        """Shelf pins included for adjustable shelves."""
        component = DeskHutchComponent()
        config = {"shelf_count": 2}
        result = component.generate(config, standard_context)
        pins = [h for h in result.hardware if "Shelf Pin" in h.name]
        assert len(pins) == 1
        assert pins[0].quantity == 8  # 2 shelves * 4 pins

    def test_task_light_zone_hardware(self, standard_context):
        """Task light zone includes LED hardware."""
        component = DeskHutchComponent()
        config = {"task_light_zone": True}
        result = component.generate(config, standard_context)
        led_channel = [
            h for h in result.hardware if "LED" in h.name and "Channel" in h.name
        ]
        assert len(led_channel) == 1
        power_supply = [h for h in result.hardware if "Power Supply" in h.name]
        assert len(power_supply) == 1

    def test_no_task_light_hardware(self, standard_context):
        """No LED hardware when task_light_zone disabled."""
        component = DeskHutchComponent()
        config = {"task_light_zone": False}
        result = component.generate(config, standard_context)
        led = [h for h in result.hardware if "LED" in h.name]
        assert len(led) == 0

    def test_door_hardware(self, standard_context):
        """Door hardware included when doors enabled."""
        component = DeskHutchComponent()
        config = {"doors": True}
        result = component.generate(config, standard_context)
        hinges = [h for h in result.hardware if "Hinge" in h.name]
        assert len(hinges) == 1
        assert hinges[0].quantity == 4  # 2 doors * 2 hinges
        handles = [h for h in result.hardware if "Handle" in h.name]
        assert len(handles) == 1
        assert handles[0].quantity == 2

    def test_no_door_hardware_by_default(self, standard_context):
        """No door hardware when doors disabled."""
        component = DeskHutchComponent()
        config = {"doors": False}
        result = component.generate(config, standard_context)
        hinges = [h for h in result.hardware if "Hinge" in h.name]
        assert len(hinges) == 0

    def test_assembly_hardware(self, standard_context):
        """Assembly cam locks included."""
        component = DeskHutchComponent()
        result = component.generate({}, standard_context)
        cam_locks = [h for h in result.hardware if "Cam Lock" in h.name]
        assert len(cam_locks) == 1

    def test_task_light_zone_metadata(self, standard_context):
        """Task light zone in bottom panel metadata."""
        component = DeskHutchComponent()
        config = {"task_light_zone": True}
        result = component.generate(config, standard_context)
        bottom = [p for p in result.panels if p.panel_type == PanelType.BOTTOM][0]
        assert bottom.metadata.get("task_light_zone") is True

    def test_result_metadata(self, standard_context):
        """Result metadata includes configuration."""
        component = DeskHutchComponent()
        config = {"shelf_count": 2, "doors": True, "task_light_zone": True}
        result = component.generate(config, standard_context)
        assert result.metadata["shelf_count"] == 2
        assert result.metadata["has_doors"] is True
        assert result.metadata["task_light_zone"] is True


class TestDeskHutchHardware:
    """Test desk.hutch hardware() method."""

    def test_hardware_method_returns_list(self, standard_context):
        """hardware() method returns a list."""
        component = DeskHutchComponent()
        result = component.hardware({}, standard_context)
        assert isinstance(result, list)

    def test_hardware_matches_generate(self, standard_context):
        """hardware() returns same items as generate().hardware."""
        component = DeskHutchComponent()
        config = {"doors": True, "shelf_count": 2}

        gen_result = component.generate(config, standard_context)
        hw_result = component.hardware(config, standard_context)

        assert len(hw_result) == len(gen_result.hardware)


# =============================================================================
# LShapedDeskComponent Tests
# =============================================================================


class TestLShapedDeskRegistration:
    """Test desk.l_shaped component registration."""

    def test_component_registered(self):
        """desk.l_shaped is registered in component registry."""
        component_cls = component_registry.get("desk.l_shaped")
        assert component_cls is LShapedDeskComponent

    def test_component_in_registry_list(self):
        """desk.l_shaped appears in registry list."""
        assert "desk.l_shaped" in component_registry.list()

    def test_component_instantiation(self):
        """LShapedDeskComponent can be instantiated."""
        component = LShapedDeskComponent()
        assert component is not None


class TestLShapedDeskValidation:
    """Test desk.l_shaped validate() method."""

    def test_valid_butt_corner(self, wide_context):
        """Valid butt corner configuration passes validation."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "corner_connection_type": "butt",
        }
        result = component.validate(config, wide_context)
        assert len(result.errors) == 0

    def test_valid_diagonal_corner(self, wide_context):
        """Valid diagonal corner configuration passes validation."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "corner_connection_type": "diagonal",
            "corner_post": True,
        }
        result = component.validate(config, wide_context)
        assert len(result.errors) == 0

    def test_invalid_corner_type(self, wide_context):
        """Invalid corner type produces error."""
        component = LShapedDeskComponent()
        config = {"corner_connection_type": "invalid"}
        result = component.validate(config, wide_context)
        assert len(result.errors) == 1
        assert (
            "corner" in result.errors[0].lower() or "butt" in result.errors[0].lower()
        )

    def test_narrow_main_surface_warning(self, standard_context):
        """Narrow main surface produces warning."""
        component = LShapedDeskComponent()
        config = {"main_surface_width": 30.0}  # Below 36" minimum
        result = component.validate(config, standard_context)
        assert any(
            "narrow" in w.lower() or "main surface" in w.lower()
            for w in result.warnings
        )

    def test_narrow_return_surface_warning(self, standard_context):
        """Narrow return surface produces warning."""
        component = LShapedDeskComponent()
        config = {"return_surface_width": 30.0}  # Below 36" minimum
        result = component.validate(config, standard_context)
        assert any(
            "narrow" in w.lower() or "return surface" in w.lower()
            for w in result.warnings
        )

    def test_shallow_main_depth_error(self, standard_context):
        """Shallow main depth produces error."""
        component = LShapedDeskComponent()
        config = {"main_surface_depth": 16.0}  # Below 18" minimum
        result = component.validate(config, standard_context)
        assert any("18" in err or "shallow" in err.lower() for err in result.errors)

    def test_shallow_return_depth_error(self, standard_context):
        """Shallow return depth produces error."""
        component = LShapedDeskComponent()
        config = {"return_surface_depth": 16.0}  # Below 18" minimum
        result = component.validate(config, standard_context)
        assert any("18" in err or "shallow" in err.lower() for err in result.errors)

    def test_desk_height_too_low(self, standard_context):
        """Desk height below 26" produces error."""
        component = LShapedDeskComponent()
        config = {"desk_height": 24.0}
        result = component.validate(config, standard_context)
        assert any("26" in err or "outside" in err.lower() for err in result.errors)

    def test_desk_height_too_high(self, standard_context):
        """Desk height above 50" produces error."""
        component = LShapedDeskComponent()
        config = {"desk_height": 52.0}
        result = component.validate(config, standard_context)
        assert any("50" in err or "outside" in err.lower() for err in result.errors)

    def test_desk_height_between_ranges_warning(self, standard_context):
        """Height between sitting and standing ranges produces warning."""
        component = LShapedDeskComponent()
        config = {"desk_height": 35.0}
        result = component.validate(config, standard_context)
        assert any("between" in w.lower() for w in result.warnings)

    def test_large_desk_without_corner_post_warning(self, wide_context):
        """Large L-shaped desk without corner post produces warning."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 72.0,
            "return_surface_width": 60.0,
            "corner_post": False,
        }
        result = component.validate(config, wide_context)
        assert any(
            "corner" in w.lower() and "support" in w.lower() for w in result.warnings
        )

    def test_diagonal_without_corner_post_warning(self, standard_context):
        """Diagonal corner without corner post produces warning."""
        component = LShapedDeskComponent()
        config = {
            "corner_connection_type": "diagonal",
            "corner_post": False,
        }
        result = component.validate(config, standard_context)
        assert any(
            "diagonal" in w.lower() or "corner" in w.lower() for w in result.warnings
        )

    def test_default_config_passes(self, standard_context):
        """Default configuration passes validation."""
        component = LShapedDeskComponent()
        result = component.validate({}, standard_context)
        assert len(result.errors) == 0


class TestLShapedDeskGeneration:
    """Test desk.l_shaped generate() method."""

    def test_generates_desktop_panels(self, wide_context):
        """Generate creates multiple DESKTOP panels (main + return)."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
        }
        result = component.generate(config, wide_context)
        desktops = [p for p in result.panels if p.panel_type == PanelType.DESKTOP]
        assert len(desktops) == 2

    def test_main_surface_tagged(self, wide_context):
        """Main surface panels have correct metadata tag."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
        }
        result = component.generate(config, wide_context)
        main_panels = [
            p for p in result.panels if p.metadata.get("l_shaped_surface") == "main"
        ]
        assert len(main_panels) >= 1

    def test_return_surface_tagged(self, wide_context):
        """Return surface panels have correct metadata tag."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
        }
        result = component.generate(config, wide_context)
        return_panels = [
            p for p in result.panels if p.metadata.get("l_shaped_surface") == "return"
        ]
        assert len(return_panels) >= 1

    def test_corner_post_generated(self, wide_context):
        """Corner support post generated when enabled."""
        component = LShapedDeskComponent()
        config = {
            "corner_post": True,
        }
        result = component.generate(config, wide_context)
        posts = [p for p in result.panels if p.metadata.get("is_corner_post") is True]
        assert len(posts) == 1

    def test_diagonal_generates_diagonal_face(self, wide_context):
        """Diagonal corner generates DIAGONAL_FACE panel."""
        component = LShapedDeskComponent()
        config = {
            "corner_connection_type": "diagonal",
        }
        result = component.generate(config, wide_context)
        diagonals = [
            p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE
        ]
        assert len(diagonals) == 1

    def test_butt_no_diagonal_face(self, wide_context):
        """Butt corner does not generate DIAGONAL_FACE panel."""
        component = LShapedDeskComponent()
        config = {
            "corner_connection_type": "butt",
        }
        result = component.generate(config, wide_context)
        diagonals = [
            p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE
        ]
        assert len(diagonals) == 0

    def test_butt_corner_brackets(self, wide_context):
        """Butt corner includes corner bracket hardware."""
        component = LShapedDeskComponent()
        config = {
            "corner_connection_type": "butt",
        }
        result = component.generate(config, wide_context)
        brackets = [h for h in result.hardware if "Corner Bracket" in h.name]
        assert len(brackets) == 1

    def test_diagonal_miter_bolts(self, wide_context):
        """Diagonal corner includes miter bolt hardware."""
        component = LShapedDeskComponent()
        config = {
            "corner_connection_type": "diagonal",
        }
        result = component.generate(config, wide_context)
        miter_bolts = [h for h in result.hardware if "Miter Bolt" in h.name]
        assert len(miter_bolts) == 1

    def test_corner_post_brackets(self, wide_context):
        """Corner post includes bracket hardware."""
        component = LShapedDeskComponent()
        config = {
            "corner_post": True,
        }
        result = component.generate(config, wide_context)
        post_brackets = [h for h in result.hardware if "Post Bracket" in h.name]
        assert len(post_brackets) == 1

    def test_cable_routing_grommet(self, wide_context):
        """Corner cable routing grommet included."""
        component = LShapedDeskComponent()
        result = component.generate({}, wide_context)
        grommets = [h for h in result.hardware if "Grommet" in h.name and "2" in h.name]
        assert len(grommets) == 1

    def test_main_left_pedestal_generated(self, wide_context):
        """Main left pedestal generates panels when configured."""
        component = LShapedDeskComponent()
        config = {
            "main_left_pedestal": {"pedestal_type": "storage", "width": 18.0},
        }
        result = component.generate(config, wide_context)
        pedestal_panels = [
            p
            for p in result.panels
            if p.metadata.get("l_shaped_pedestal") == "main_left"
        ]
        assert len(pedestal_panels) >= 3  # At least sides, bottom, back

    def test_return_right_pedestal_generated(self, wide_context):
        """Return right pedestal generates panels when configured."""
        component = LShapedDeskComponent()
        config = {
            "return_right_pedestal": {"pedestal_type": "file", "width": 18.0},
        }
        result = component.generate(config, wide_context)
        pedestal_panels = [
            p
            for p in result.panels
            if p.metadata.get("l_shaped_pedestal") == "return_right"
        ]
        assert len(pedestal_panels) >= 3

    def test_result_metadata(self, wide_context):
        """Result metadata includes L-shaped configuration."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "corner_connection_type": "diagonal",
        }
        result = component.generate(config, wide_context)
        assert result.metadata["desk_type"] == "l_shaped"
        assert result.metadata["corner_type"] == "diagonal"
        assert result.metadata["main_surface_width"] == 48.0
        assert result.metadata["return_surface_width"] == 36.0


class TestLShapedDeskHardware:
    """Test desk.l_shaped hardware() method."""

    def test_hardware_method_returns_list(self, wide_context):
        """hardware() method returns a list."""
        component = LShapedDeskComponent()
        result = component.hardware({}, wide_context)
        assert isinstance(result, list)

    def test_hardware_matches_generate(self, wide_context):
        """hardware() returns same items as generate().hardware."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
        }

        gen_result = component.generate(config, wide_context)
        hw_result = component.hardware(config, wide_context)

        assert len(hw_result) == len(gen_result.hardware)


# =============================================================================
# Value Object Tests - DeskType, EdgeTreatment, PedestalType, DeskDimensions
# =============================================================================


class TestDeskTypeEnum:
    """Test DeskType enum."""

    def test_single_value(self):
        """DeskType.SINGLE has correct value."""
        assert DeskType.SINGLE.value == "single"

    def test_l_shaped_value(self):
        """DeskType.L_SHAPED has correct value."""
        assert DeskType.L_SHAPED.value == "l_shaped"

    def test_corner_value(self):
        """DeskType.CORNER has correct value."""
        assert DeskType.CORNER.value == "corner"

    def test_standing_value(self):
        """DeskType.STANDING has correct value."""
        assert DeskType.STANDING.value == "standing"

    def test_all_values_unique(self):
        """All DeskType values are unique."""
        values = [e.value for e in DeskType]
        assert len(values) == len(set(values))

    def test_is_string_enum(self):
        """DeskType members are string compatible."""
        assert isinstance(DeskType.SINGLE, str)
        assert DeskType.SINGLE == "single"


class TestEdgeTreatmentEnum:
    """Test EdgeTreatment enum."""

    def test_square_value(self):
        """EdgeTreatment.SQUARE has correct value."""
        assert EdgeTreatment.SQUARE.value == "square"

    def test_bullnose_value(self):
        """EdgeTreatment.BULLNOSE has correct value."""
        assert EdgeTreatment.BULLNOSE.value == "bullnose"

    def test_waterfall_value(self):
        """EdgeTreatment.WATERFALL has correct value."""
        assert EdgeTreatment.WATERFALL.value == "waterfall"

    def test_eased_value(self):
        """EdgeTreatment.EASED has correct value."""
        assert EdgeTreatment.EASED.value == "eased"

    def test_all_values_unique(self):
        """All EdgeTreatment values are unique."""
        values = [e.value for e in EdgeTreatment]
        assert len(values) == len(set(values))

    def test_is_string_enum(self):
        """EdgeTreatment members are string compatible."""
        assert isinstance(EdgeTreatment.SQUARE, str)
        assert EdgeTreatment.SQUARE == "square"


class TestPedestalTypeEnum:
    """Test PedestalType enum."""

    def test_file_value(self):
        """PedestalType.FILE has correct value."""
        assert PedestalType.FILE.value == "file"

    def test_storage_value(self):
        """PedestalType.STORAGE has correct value."""
        assert PedestalType.STORAGE.value == "storage"

    def test_open_value(self):
        """PedestalType.OPEN has correct value."""
        assert PedestalType.OPEN.value == "open"

    def test_all_values_unique(self):
        """All PedestalType values are unique."""
        values = [e.value for e in PedestalType]
        assert len(values) == len(set(values))

    def test_is_string_enum(self):
        """PedestalType members are string compatible."""
        assert isinstance(PedestalType.FILE, str)
        assert PedestalType.FILE == "file"


class TestDeskDimensionsDataclass:
    """Test DeskDimensions dataclass."""

    def test_default_values(self):
        """DeskDimensions has correct default values."""
        dims = DeskDimensions()
        assert dims.standard_desk_height == 29.5
        assert dims.standing_desk_min_height == 38.0
        assert dims.standing_desk_max_height == 48.0
        assert dims.min_knee_clearance_height == 24.0
        assert dims.min_knee_clearance_width == 20.0
        assert dims.min_knee_clearance_depth == 15.0
        assert dims.keyboard_tray_height == 3.0
        assert dims.keyboard_tray_depth == 10.0

    def test_custom_values(self):
        """DeskDimensions accepts custom values."""
        dims = DeskDimensions(
            standard_desk_height=30.0,
            standing_desk_min_height=40.0,
            standing_desk_max_height=50.0,
        )
        assert dims.standard_desk_height == 30.0
        assert dims.standing_desk_min_height == 40.0
        assert dims.standing_desk_max_height == 50.0

    def test_invalid_standard_height_raises(self):
        """Non-positive standard desk height raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(standard_desk_height=0)

    def test_invalid_standing_min_height_raises(self):
        """Non-positive standing desk min height raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(standing_desk_min_height=0)

    def test_standing_max_less_than_min_raises(self):
        """Standing desk max < min raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(standing_desk_min_height=40.0, standing_desk_max_height=35.0)

    def test_invalid_knee_clearance_height_raises(self):
        """Non-positive knee clearance height raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(min_knee_clearance_height=0)

    def test_invalid_knee_clearance_width_raises(self):
        """Non-positive knee clearance width raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(min_knee_clearance_width=0)

    def test_invalid_knee_clearance_depth_raises(self):
        """Non-positive knee clearance depth raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(min_knee_clearance_depth=0)

    def test_invalid_keyboard_tray_height_raises(self):
        """Non-positive keyboard tray height raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(keyboard_tray_height=0)

    def test_invalid_keyboard_tray_depth_raises(self):
        """Non-positive keyboard tray depth raises error."""
        with pytest.raises(ValueError):
            DeskDimensions(keyboard_tray_depth=0)

    def test_frozen(self):
        """DeskDimensions is immutable (frozen)."""
        dims = DeskDimensions()
        with pytest.raises(AttributeError):
            dims.standard_desk_height = 32.0  # type: ignore


# =============================================================================
# Desk-Specific Value Object Tests (GrommetSpec, LShapedDeskConfiguration)
# =============================================================================


class TestGrommetSpec:
    """Test GrommetSpec dataclass."""

    def test_valid_grommet(self):
        """Valid GrommetSpec creation."""
        spec = GrommetSpec(x_position=24.0, y_position=20.0, diameter=2.5)
        assert spec.x_position == 24.0
        assert spec.y_position == 20.0
        assert spec.diameter == 2.5

    def test_negative_x_position_raises(self):
        """Negative x_position raises error."""
        with pytest.raises(ValueError):
            GrommetSpec(x_position=-5.0, y_position=20.0, diameter=2.5)

    def test_negative_y_position_raises(self):
        """Negative y_position raises error."""
        with pytest.raises(ValueError):
            GrommetSpec(x_position=24.0, y_position=-5.0, diameter=2.5)

    def test_zero_diameter_raises(self):
        """Zero diameter raises error."""
        with pytest.raises(ValueError):
            GrommetSpec(x_position=24.0, y_position=20.0, diameter=0)

    def test_negative_diameter_raises(self):
        """Negative diameter raises error."""
        with pytest.raises(ValueError):
            GrommetSpec(x_position=24.0, y_position=20.0, diameter=-1.0)

    def test_frozen(self):
        """GrommetSpec is immutable (frozen)."""
        spec = GrommetSpec(x_position=24.0, y_position=20.0, diameter=2.5)
        with pytest.raises(AttributeError):
            spec.diameter = 3.0  # type: ignore


class TestLShapedDeskConfiguration:
    """Test LShapedDeskConfiguration dataclass."""

    def test_valid_configuration(self):
        """Valid LShapedDeskConfiguration creation."""
        config = LShapedDeskConfiguration(
            main_surface_width=48.0,
            return_surface_width=36.0,
        )
        assert config.main_surface_width == 48.0
        assert config.return_surface_width == 36.0
        assert config.main_surface_depth == 24.0  # default
        assert config.return_surface_depth == 24.0  # default
        assert config.desk_height == 30.0  # default
        assert config.corner_type == "butt"  # default
        assert config.corner_post is True  # default

    def test_custom_configuration(self):
        """Custom LShapedDeskConfiguration values."""
        config = LShapedDeskConfiguration(
            main_surface_width=60.0,
            return_surface_width=48.0,
            main_surface_depth=30.0,
            return_surface_depth=24.0,
            desk_height=42.0,
            corner_type="diagonal",
            corner_post=False,
        )
        assert config.main_surface_width == 60.0
        assert config.return_surface_width == 48.0
        assert config.main_surface_depth == 30.0
        assert config.return_surface_depth == 24.0
        assert config.desk_height == 42.0
        assert config.corner_type == "diagonal"
        assert config.corner_post is False

    def test_zero_main_width_raises(self):
        """Zero main_surface_width raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(main_surface_width=0, return_surface_width=36.0)

    def test_negative_main_width_raises(self):
        """Negative main_surface_width raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(main_surface_width=-10, return_surface_width=36.0)

    def test_zero_return_width_raises(self):
        """Zero return_surface_width raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(main_surface_width=48.0, return_surface_width=0)

    def test_zero_main_depth_raises(self):
        """Zero main_surface_depth raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(
                main_surface_width=48.0,
                return_surface_width=36.0,
                main_surface_depth=0,
            )

    def test_zero_return_depth_raises(self):
        """Zero return_surface_depth raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(
                main_surface_width=48.0,
                return_surface_width=36.0,
                return_surface_depth=0,
            )

    def test_zero_desk_height_raises(self):
        """Zero desk_height raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(
                main_surface_width=48.0,
                return_surface_width=36.0,
                desk_height=0,
            )

    def test_invalid_corner_type_raises(self):
        """Invalid corner_type raises error."""
        with pytest.raises(ValueError):
            LShapedDeskConfiguration(
                main_surface_width=48.0,
                return_surface_width=36.0,
                corner_type="invalid",  # type: ignore
            )

    def test_pedestal_config(self):
        """Pedestal configuration stored correctly."""
        config = LShapedDeskConfiguration(
            main_surface_width=48.0,
            return_surface_width=36.0,
            main_left_pedestal={"pedestal_type": "file", "width": 18.0},
            return_right_pedestal={"pedestal_type": "storage", "width": 15.0},
        )
        assert config.main_left_pedestal == {"pedestal_type": "file", "width": 18.0}
        assert config.return_right_pedestal == {
            "pedestal_type": "storage",
            "width": 15.0,
        }

    def test_frozen(self):
        """LShapedDeskConfiguration is immutable (frozen)."""
        config = LShapedDeskConfiguration(
            main_surface_width=48.0,
            return_surface_width=36.0,
        )
        with pytest.raises(AttributeError):
            config.main_surface_width = 60.0  # type: ignore


class TestCornerConnectionTypeEnum:
    """Test CornerConnectionType enum."""

    def test_butt_value(self):
        """CornerConnectionType.BUTT has correct value."""
        assert CornerConnectionType.BUTT.value == "butt"

    def test_diagonal_value(self):
        """CornerConnectionType.DIAGONAL has correct value."""
        assert CornerConnectionType.DIAGONAL.value == "diagonal"

    def test_is_string_enum(self):
        """CornerConnectionType members are string compatible."""
        assert isinstance(CornerConnectionType.BUTT, str)
        assert CornerConnectionType.BUTT == "butt"


# =============================================================================
# Desk Component Constants Tests
# =============================================================================


class TestDeskComponentConstants:
    """Test desk component module constants."""

    def test_sitting_height_range(self):
        """Sitting desk height constants are valid."""
        assert SITTING_DESK_HEIGHT_MIN == 28.0
        assert SITTING_DESK_HEIGHT_MAX == 32.0
        assert SITTING_DESK_HEIGHT_DEFAULT == 30.0
        assert (
            SITTING_DESK_HEIGHT_MIN
            < SITTING_DESK_HEIGHT_DEFAULT
            < SITTING_DESK_HEIGHT_MAX
        )

    def test_standing_height_range(self):
        """Standing desk height constants are valid."""
        assert STANDING_DESK_HEIGHT_MIN == 38.0
        assert STANDING_DESK_HEIGHT_MAX == 48.0
        assert STANDING_DESK_HEIGHT_DEFAULT == 42.0
        assert (
            STANDING_DESK_HEIGHT_MIN
            < STANDING_DESK_HEIGHT_DEFAULT
            < STANDING_DESK_HEIGHT_MAX
        )

    def test_sitting_standing_gap(self):
        """Gap between sitting and standing ranges."""
        assert STANDING_DESK_HEIGHT_MIN > SITTING_DESK_HEIGHT_MAX


# =============================================================================
# Integration Tests
# =============================================================================


class TestDeskComponentIntegration:
    """Integration tests for desk components working together."""

    def test_full_desk_workflow(self, standard_context):
        """Test complete desk setup: surface + pedestal + keyboard tray."""
        surface = DeskSurfaceComponent()
        pedestal = DeskPedestalComponent()
        keyboard = KeyboardTrayComponent()

        surface_config = {"desk_height": 30.0, "depth": 24.0}
        pedestal_config = {"pedestal_type": "file", "width": 18.0}
        keyboard_config = {"knee_clearance_height": 25.0}

        # Validate all components
        assert surface.validate(surface_config, standard_context).is_valid
        assert pedestal.validate(pedestal_config, standard_context).is_valid
        assert keyboard.validate(keyboard_config, standard_context).is_valid

        # Generate all components
        surface_result = surface.generate(surface_config, standard_context)
        pedestal_result = pedestal.generate(pedestal_config, standard_context)
        keyboard_result = keyboard.generate(keyboard_config, standard_context)

        # All should produce panels and hardware
        assert len(surface_result.panels) >= 1
        assert len(pedestal_result.panels) >= 3
        assert len(keyboard_result.panels) >= 1

        assert len(surface_result.hardware) >= 1
        assert len(pedestal_result.hardware) >= 1
        assert len(keyboard_result.hardware) >= 1

    def test_desk_with_hutch_workflow(self, standard_context):
        """Test desk with hutch above."""
        surface = DeskSurfaceComponent()
        hutch = DeskHutchComponent()

        surface_config = {"desk_height": 30.0}
        hutch_config = {"head_clearance": 15.0, "height": 24.0, "shelf_count": 2}

        assert surface.validate(surface_config, standard_context).is_valid
        assert hutch.validate(hutch_config, standard_context).is_valid

        surface_result = surface.generate(surface_config, standard_context)
        hutch_result = hutch.generate(hutch_config, standard_context)

        assert len(surface_result.panels) >= 1
        assert len(hutch_result.panels) >= 5  # sides, top, bottom, back + shelves

    def test_l_shaped_desk_with_pedestals(self, wide_context):
        """Test L-shaped desk with both end pedestals."""
        component = LShapedDeskComponent()
        config = {
            "main_surface_width": 60.0,
            "return_surface_width": 48.0,
            "corner_connection_type": "butt",
            "main_left_pedestal": {"pedestal_type": "file", "width": 18.0},
            "return_right_pedestal": {"pedestal_type": "storage", "width": 15.0},
        }

        result = component.validate(config, wide_context)
        assert len(result.errors) == 0

        gen_result = component.generate(config, wide_context)

        # Should have surfaces and pedestals
        desktops = [p for p in gen_result.panels if p.panel_type == PanelType.DESKTOP]
        assert len(desktops) == 2

        main_pedestal = [
            p
            for p in gen_result.panels
            if p.metadata.get("l_shaped_pedestal") == "main_left"
        ]
        return_pedestal = [
            p
            for p in gen_result.panels
            if p.metadata.get("l_shaped_pedestal") == "return_right"
        ]
        assert len(main_pedestal) >= 3
        assert len(return_pedestal) >= 3
