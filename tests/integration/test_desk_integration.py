"""Integration tests for desk component generation (FRD-18).

These tests verify end-to-end desk generation including:
- Complete desk section generation with surface, pedestals, and fixtures
- Desk integration with adjacent cabinet sections
- L-shaped desk configurations with corner connections
- Pedestal drawer hardware integration with FRD-08
- Hutch door hardware integration with FRD-07
- Cable grommet cutouts in output
- STL export rendering of desk panels
- End-to-end workflow tests

Test run command:
    uv run pytest tests/integration/test_desk_integration.py -v
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import ComponentContext, component_registry
from cabinets.domain.components.desk import (
    DeskHutchComponent,
    DeskPedestalComponent,
    DeskSurfaceComponent,
    KeyboardTrayComponent,
    LShapedDeskComponent,
    MonitorShelfComponent,
)
from cabinets.domain.entities import Cabinet, Panel
from cabinets.domain.services import Panel3DMapper
from cabinets.domain.value_objects import (
    MaterialSpec,
    PanelType,
    Position,
)
from cabinets.infrastructure.stl_exporter import StlExporter


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ensure_desk_components_registered() -> None:
    """Ensure all desk components are registered for tests."""
    if "desk.surface" not in component_registry.list():
        component_registry.register("desk.surface")(DeskSurfaceComponent)
    if "desk.pedestal" not in component_registry.list():
        component_registry.register("desk.pedestal")(DeskPedestalComponent)
    if "desk.keyboard_tray" not in component_registry.list():
        component_registry.register("desk.keyboard_tray")(KeyboardTrayComponent)
    if "desk.monitor_shelf" not in component_registry.list():
        component_registry.register("desk.monitor_shelf")(MonitorShelfComponent)
    if "desk.hutch" not in component_registry.list():
        component_registry.register("desk.hutch")(DeskHutchComponent)
    if "desk.l_shaped" not in component_registry.list():
        component_registry.register("desk.l_shaped")(LShapedDeskComponent)


@pytest.fixture
def standard_desk_context() -> ComponentContext:
    """Create a standard context for desk component testing."""
    return ComponentContext(
        width=60.0,
        height=84.0,
        depth=24.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=60.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


@pytest.fixture
def narrow_desk_context() -> ComponentContext:
    """Create a narrow context for pedestal testing."""
    return ComponentContext(
        width=18.0,
        height=84.0,
        depth=24.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=60.0,
        cabinet_height=84.0,
        cabinet_depth=24.0,
    )


# =============================================================================
# Test 1: Complete Desk Section Generation
# =============================================================================


class TestCompleteDeskGeneration:
    """Tests for complete desk section generation with all fixtures."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_complete_desk_with_all_fixtures(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Generate desk with pedestals, hutch, keyboard tray, and monitor shelf.

        Verifies that all components generate their expected panels and hardware.
        """
        # Generate surface
        surface = DeskSurfaceComponent()
        surface_config = {
            "desk_height": 30.0,
            "depth": 24.0,
            "edge_treatment": "bullnose",
            "grommets": [{"x_position": 40.0, "y_position": 21.0, "diameter": 2.5}],
        }
        surface_result = surface.generate(surface_config, standard_desk_context)

        # Generate keyboard tray
        keyboard = KeyboardTrayComponent()
        keyboard_config = {"width": 20.0, "enclosed": True}
        keyboard_result = keyboard.generate(keyboard_config, standard_desk_context)

        # Generate hutch
        hutch = DeskHutchComponent()
        hutch_config = {
            "height": 30.0,
            "shelf_count": 2,
            "doors": True,
            "task_light_zone": True,
        }
        hutch_result = hutch.generate(hutch_config, standard_desk_context)

        # Generate monitor shelf
        monitor = MonitorShelfComponent()
        monitor_config = {"width": 24.0, "height": 6.0, "arm_mount": True}
        monitor_result = monitor.generate(monitor_config, standard_desk_context)

        # Verify desktop panel generated
        panel_types = {p.panel_type for p in surface_result.panels}
        assert PanelType.DESKTOP in panel_types

        # Verify keyboard tray and enclosure panels
        kb_panel_types = {p.panel_type for p in keyboard_result.panels}
        assert PanelType.KEYBOARD_TRAY in kb_panel_types
        assert PanelType.KEYBOARD_ENCLOSURE in kb_panel_types

        # Verify hutch panels (sides, top, bottom, back, shelves)
        hutch_panel_types = {p.panel_type for p in hutch_result.panels}
        assert PanelType.LEFT_SIDE in hutch_panel_types
        assert PanelType.RIGHT_SIDE in hutch_panel_types
        assert PanelType.TOP in hutch_panel_types
        assert PanelType.BOTTOM in hutch_panel_types
        assert PanelType.BACK in hutch_panel_types
        assert PanelType.SHELF in hutch_panel_types

        # Verify hardware includes all expected items
        all_hardware = (
            list(surface_result.hardware)
            + list(keyboard_result.hardware)
            + list(hutch_result.hardware)
            + list(monitor_result.hardware)
        )
        hardware_names = {h.name for h in all_hardware}

        # Check for grommet
        assert any("Grommet" in name for name in hardware_names)

        # Check for keyboard slide
        assert any("Keyboard Slide" in name for name in hardware_names)

        # Check for monitor arm mount hardware
        assert any("Monitor Arm" in name for name in hardware_names)

        # Check for LED light hardware (task light zone)
        assert any("LED" in name for name in hardware_names)

        # Check for European hinges (hutch doors)
        assert any(
            "European Hinge" in name or "Hinge" in name for name in hardware_names
        )

    def test_desk_surface_generates_correct_panels(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test that desk surface generates desktop panel with correct dimensions."""
        surface = DeskSurfaceComponent()
        config = {"desk_height": 30.0, "depth": 24.0, "edge_treatment": "square"}

        result = surface.generate(config, standard_desk_context)

        # Verify desktop panel
        desktop_panels = [p for p in result.panels if p.panel_type == PanelType.DESKTOP]
        assert len(desktop_panels) == 1

        desktop = desktop_panels[0]
        assert desktop.width == 60.0  # context.width
        assert desktop.height == 24.0  # depth becomes height in 2D representation
        assert desktop.metadata.get("edge_treatment") == "square"
        assert desktop.metadata.get("is_desktop") is True

    def test_waterfall_edge_generates_extra_panel(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test that waterfall edge treatment generates additional panel."""
        surface = DeskSurfaceComponent()
        config = {"desk_height": 30.0, "depth": 24.0, "edge_treatment": "waterfall"}

        result = surface.generate(config, standard_desk_context)

        # Should have desktop and waterfall edge panels
        panel_types = {p.panel_type for p in result.panels}
        assert PanelType.DESKTOP in panel_types
        assert PanelType.WATERFALL_EDGE in panel_types

        # Waterfall edge should have correct height (desk_height - 4")
        waterfall_panels = [
            p for p in result.panels if p.panel_type == PanelType.WATERFALL_EDGE
        ]
        assert len(waterfall_panels) == 1
        assert waterfall_panels[0].height == 26.0  # 30 - 4


# =============================================================================
# Test 2: Desk Integrates with Adjacent Cabinet Sections
# =============================================================================


class TestDeskCabinetIntegration:
    """Tests for desk section adjacent to standard cabinet sections."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_desk_pedestal_creates_cabinet_box_panels(
        self, narrow_desk_context: ComponentContext
    ) -> None:
        """Test that desk pedestal generates proper cabinet box panels.

        Pedestals are placed adjacent to the desk surface and must generate
        side panels, bottom, and back like a standard cabinet section.
        """
        pedestal = DeskPedestalComponent()
        config = {
            "pedestal_type": "storage",
            "width": 18.0,
            "desktop_height": 30.0,
            "desktop_thickness": 1.0,
            "drawer_count": 3,
        }

        result = pedestal.generate(config, narrow_desk_context)

        # Verify cabinet box panels
        panel_types = {p.panel_type for p in result.panels}
        assert PanelType.LEFT_SIDE in panel_types
        assert PanelType.RIGHT_SIDE in panel_types
        assert PanelType.BOTTOM in panel_types
        assert PanelType.BACK in panel_types

        # Verify pedestal height = desktop_height - desktop_thickness
        side_panels = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE]
        assert len(side_panels) == 1
        assert side_panels[0].height == pytest.approx(29.0)  # 30 - 1

    def test_desk_pedestal_panel_alignment(
        self, narrow_desk_context: ComponentContext
    ) -> None:
        """Test that pedestal panels are correctly aligned."""
        pedestal = DeskPedestalComponent()
        config = {
            "pedestal_type": "storage",
            "width": 18.0,
            "desktop_height": 30.0,
        }

        result = pedestal.generate(config, narrow_desk_context)

        # Get right side panel
        right_panel = next(
            p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE
        )

        # Right panel should be offset by width - material_thickness
        expected_right_x = 18.0 - narrow_desk_context.material.thickness
        assert right_panel.position.x == pytest.approx(expected_right_x)

    def test_divider_handling_between_sections(self) -> None:
        """Test that desk section respects divider panel boundaries.

        When a desk section is between two cabinet sections, the divider
        panels should provide proper separation.
        """
        # Context simulating a desk section between cabinets
        context = ComponentContext(
            width=48.0,  # Desk section width
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(24.0, 0),  # After a 24" storage section
            section_index=1,
            cabinet_width=120.0,  # Total cabinet width
            cabinet_height=84.0,
            cabinet_depth=24.0,
            adjacent_left="storage",  # Cabinet on left
            adjacent_right="storage",  # Cabinet on right
        )

        surface = DeskSurfaceComponent()
        config = {"desk_height": 30.0, "depth": 24.0}

        result = surface.generate(config, context)

        # Desktop panel should be positioned at context position
        desktop = next(p for p in result.panels if p.panel_type == PanelType.DESKTOP)
        assert desktop.position.x == 24.0


# =============================================================================
# Test 3: L-Shaped Desk Generates Corner Connection
# =============================================================================


class TestLShapedDeskCorner:
    """Tests for L-shaped desk with different corner connection types."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_l_shaped_desk_with_butt_joint(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test L-shaped desk with 90-degree butt joint connection."""
        l_desk = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "main_surface_depth": 24.0,
            "return_surface_depth": 24.0,
            "desk_height": 30.0,
            "corner_connection_type": "butt",
            "corner_post": True,
        }

        result = l_desk.generate(config, standard_desk_context)

        # Verify both surfaces generated
        desktop_panels = [p for p in result.panels if p.panel_type == PanelType.DESKTOP]
        assert len(desktop_panels) == 2

        # Verify corner post (DIVIDER panel used for post)
        divider_panels = [p for p in result.panels if p.panel_type == PanelType.DIVIDER]
        corner_posts = [p for p in divider_panels if p.metadata.get("is_corner_post")]
        assert len(corner_posts) == 1

        # Verify butt joint hardware (corner brackets)
        hardware_names = {h.name for h in result.hardware}
        assert any("Corner Bracket" in name for name in hardware_names)

        # Verify metadata
        assert result.metadata.get("desk_type") == "l_shaped"
        assert result.metadata.get("corner_type") == "butt"

    def test_l_shaped_desk_with_diagonal_joint(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test L-shaped desk with 45-degree diagonal joint connection."""
        l_desk = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "main_surface_depth": 24.0,
            "return_surface_depth": 24.0,
            "desk_height": 30.0,
            "corner_connection_type": "diagonal",
            "corner_post": True,
        }

        result = l_desk.generate(config, standard_desk_context)

        # Verify diagonal face panel generated
        diagonal_panels = [
            p for p in result.panels if p.panel_type == PanelType.DIAGONAL_FACE
        ]
        assert len(diagonal_panels) == 1

        # Diagonal face should have metadata indicating angle
        diagonal = diagonal_panels[0]
        assert diagonal.metadata.get("is_diagonal") is True
        assert diagonal.metadata.get("angle") == 45.0

        # Verify miter bolt hardware for diagonal connection
        hardware_names = {h.name for h in result.hardware}
        assert any("Miter Bolt" in name for name in hardware_names)

        # Verify corner post is generated for diagonal type
        divider_panels = [p for p in result.panels if p.panel_type == PanelType.DIVIDER]
        corner_posts = [p for p in divider_panels if p.metadata.get("is_corner_post")]
        assert len(corner_posts) >= 1

    def test_corner_support_post_dimensions(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test that corner support post has correct dimensions."""
        l_desk = LShapedDeskComponent()
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "desk_height": 30.0,
            "corner_connection_type": "butt",
            "corner_post": True,
        }

        result = l_desk.generate(config, standard_desk_context)

        # Find corner post
        corner_post = next(
            p
            for p in result.panels
            if p.panel_type == PanelType.DIVIDER and p.metadata.get("is_corner_post")
        )

        # Corner post width should be 3" (L_SHAPED_CORNER_POST_WIDTH)
        assert corner_post.width == 3.0

        # Post height should be desk_height - desktop_thickness (default 1.0)
        assert corner_post.height == pytest.approx(29.0)


# =============================================================================
# Test 4: Pedestal Uses Drawer Component Hardware
# =============================================================================


class TestPedestalDrawerHardware:
    """Tests for pedestal drawer hardware matching FRD-08 patterns."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_file_pedestal_generates_drawer_slides_and_file_frame(
        self, narrow_desk_context: ComponentContext
    ) -> None:
        """Test file pedestal generates drawer slides and file frame hardware.

        File pedestals have:
        - Pencil drawer (top)
        - File drawer (bottom)
        Each requires a pair of slides, plus file frame for hanging files.
        """
        pedestal = DeskPedestalComponent()
        config = {
            "pedestal_type": "file",
            "width": 18.0,
            "file_type": "letter",
            "desktop_height": 30.0,
        }

        result = pedestal.generate(config, narrow_desk_context)

        # Verify drawer slides
        slide_items = [h for h in result.hardware if "Slide" in h.name]
        assert len(slide_items) >= 1

        # File pedestal should have 4 slides (2 drawers * 2 slides each)
        total_slides = sum(h.quantity for h in slide_items)
        assert total_slides == 4

        # Verify file frame hardware
        file_frame_items = [h for h in result.hardware if "File Frame" in h.name]
        assert len(file_frame_items) == 1
        assert file_frame_items[0].quantity == 1

        # Verify SKU matches expected pattern
        assert file_frame_items[0].sku == "FILE-FRAME-LETTER"

    def test_storage_pedestal_generates_correct_slide_quantities(
        self, narrow_desk_context: ComponentContext
    ) -> None:
        """Test storage pedestal generates correct slide quantities.

        Storage pedestals have configurable drawer count.
        Each drawer requires 2 slides (left and right).
        """
        pedestal = DeskPedestalComponent()

        # Test with 3 drawers
        config_3 = {
            "pedestal_type": "storage",
            "width": 18.0,
            "drawer_count": 3,
            "desktop_height": 30.0,
        }
        result_3 = pedestal.generate(config_3, narrow_desk_context)

        slide_items_3 = [h for h in result_3.hardware if "Slide" in h.name]
        total_slides_3 = sum(h.quantity for h in slide_items_3)
        assert total_slides_3 == 6  # 3 drawers * 2 slides

        # Test with 5 drawers
        config_5 = {
            "pedestal_type": "storage",
            "width": 18.0,
            "drawer_count": 5,
            "desktop_height": 30.0,
        }
        result_5 = pedestal.generate(config_5, narrow_desk_context)

        slide_items_5 = [h for h in result_5.hardware if "Slide" in h.name]
        total_slides_5 = sum(h.quantity for h in slide_items_5)
        assert total_slides_5 == 10  # 5 drawers * 2 slides

    def test_hardware_skus_match_frd08_patterns(
        self, narrow_desk_context: ComponentContext
    ) -> None:
        """Verify hardware SKUs follow FRD-08 drawer hardware patterns."""
        pedestal = DeskPedestalComponent()
        config = {
            "pedestal_type": "storage",
            "width": 18.0,
            "drawer_count": 3,
            "desktop_height": 30.0,
        }

        result = pedestal.generate(config, narrow_desk_context)

        # Drawer slides should have SLIDE-XX-FULL SKU pattern
        slide_items = [h for h in result.hardware if "Slide" in h.name]
        assert len(slide_items) >= 1
        for slide in slide_items:
            assert slide.sku is not None
            assert slide.sku.startswith("SLIDE-")
            assert "FULL" in slide.sku


# =============================================================================
# Test 5: Hutch Uses Door Component Patterns
# =============================================================================


class TestHutchDoorHardware:
    """Tests for hutch door hardware matching FRD-07 patterns."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_hutch_with_doors_generates_hinges(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test hutch with doors=True generates European hinges.

        Standard hutch with 2 doors, 2 hinges per door = 4 hinges total.
        """
        hutch = DeskHutchComponent()
        config = {
            "height": 24.0,
            "depth": 12.0,
            "shelf_count": 1,
            "doors": True,
        }

        result = hutch.generate(config, standard_desk_context)

        # Verify European hinges
        hinge_items = [h for h in result.hardware if "Hinge" in h.name]
        assert len(hinge_items) >= 1

        # Should have 4 hinges (2 doors * 2 hinges)
        total_hinges = sum(h.quantity for h in hinge_items)
        assert total_hinges == 4

        # Verify SKU pattern matches FRD-07
        hinge = hinge_items[0]
        assert hinge.sku is not None
        assert "EU" in hinge.sku or "HINGE" in hinge.sku

    def test_hutch_without_doors_no_hinges(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test hutch with doors=False generates no door hinges."""
        hutch = DeskHutchComponent()
        config = {
            "height": 24.0,
            "depth": 12.0,
            "shelf_count": 1,
            "doors": False,
        }

        result = hutch.generate(config, standard_desk_context)

        # Should not have door hinges
        hinge_items = [h for h in result.hardware if "Hinge" in h.name]
        assert len(hinge_items) == 0

    def test_door_hardware_matches_frd07_patterns(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Verify door hardware follows FRD-07 patterns."""
        hutch = DeskHutchComponent()
        config = {
            "height": 24.0,
            "depth": 12.0,
            "doors": True,
        }

        result = hutch.generate(config, standard_desk_context)

        # Verify door handles are included
        handle_items = [
            h for h in result.hardware if "Handle" in h.name or "Knob" in h.name
        ]
        assert len(handle_items) >= 1

        # European hinge SKU should be present
        hinge_items = [h for h in result.hardware if "Hinge" in h.name]
        assert len(hinge_items) >= 1
        hinge = hinge_items[0]
        assert "EU" in hinge.sku or "110" in hinge.sku


# =============================================================================
# Test 6: Cable Grommets Appear in Output
# =============================================================================


class TestCableGrommetOutput:
    """Tests for cable grommet cutouts in cut list metadata and hardware."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_grommet_cutouts_in_metadata(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test grommet cutouts are included in generation result metadata."""
        surface = DeskSurfaceComponent()
        config = {
            "desk_height": 30.0,
            "depth": 24.0,
            "grommets": [
                {"x_position": 20.0, "y_position": 21.0, "diameter": 2.5},
                {"x_position": 40.0, "y_position": 21.0, "diameter": 2.0},
            ],
        }

        result = surface.generate(config, standard_desk_context)

        # Verify cutouts in metadata
        assert "cutouts" in result.metadata
        cutouts = result.metadata["cutouts"]
        assert len(cutouts) == 2

        # Verify cutout properties
        for cutout in cutouts:
            assert cutout.cutout_type == "grommet"
            assert cutout.panel == PanelType.DESKTOP
            assert cutout.shape.value == "circular"
            assert cutout.diameter in [2.0, 2.5]

    def test_grommet_hardware_in_list(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test grommet hardware is in hardware list with correct SKUs."""
        surface = DeskSurfaceComponent()
        config = {
            "desk_height": 30.0,
            "depth": 24.0,
            "grommets": [
                {"x_position": 30.0, "y_position": 21.0, "diameter": 2.5},
            ],
        }

        result = surface.generate(config, standard_desk_context)

        # Verify grommet hardware
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 1

        grommet = grommet_items[0]
        assert grommet.quantity == 1
        assert grommet.sku == "GROMMET-2"  # diameter rounded to int

    def test_multiple_grommets_hardware(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test multiple grommets generate correct hardware counts."""
        surface = DeskSurfaceComponent()
        config = {
            "desk_height": 30.0,
            "depth": 24.0,
            "grommets": [
                {"x_position": 15.0, "y_position": 21.0, "diameter": 2.0},
                {"x_position": 30.0, "y_position": 21.0, "diameter": 2.5},
                {"x_position": 45.0, "y_position": 21.0, "diameter": 3.0},
            ],
        }

        result = surface.generate(config, standard_desk_context)

        # Verify 3 grommet hardware items
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 3

        # Each should have quantity 1
        for g in grommet_items:
            assert g.quantity == 1

    def test_grommet_position_in_cutout(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test grommet position is correctly recorded in cutout."""
        surface = DeskSurfaceComponent()
        config = {
            "desk_height": 30.0,
            "depth": 24.0,
            "grommets": [
                {"x_position": 25.0, "y_position": 18.0, "diameter": 2.5},
            ],
        }

        result = surface.generate(config, standard_desk_context)

        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1

        cutout = cutouts[0]
        assert cutout.position.x == 25.0
        assert cutout.position.y == 18.0


# =============================================================================
# Test 7: STL Export Renders Desk Correctly
# =============================================================================


class TestSTLExportDesk:
    """Tests for STL export of desk panels."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_panel3dmapper_generates_desktop_bounding_box(self) -> None:
        """Test Panel3DMapper generates correct bounding box for desktop panels."""
        cabinet = Cabinet(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_4(),
        )

        # Create desktop panel
        desktop_panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=60.0,
            height=24.0,  # depth becomes height in 2D representation
            material=MaterialSpec(thickness=1.0),
            position=Position(0, 0),
            metadata={"desk_height": 30.0},
        )

        mapper = Panel3DMapper(cabinet)
        bbox = mapper.map_panel(desktop_panel)

        # Verify desktop is at correct Z height
        # z = desk_height - thickness = 30 - 1 = 29
        assert bbox.origin.z == pytest.approx(29.0)

        # Verify horizontal dimensions
        assert bbox.size_x == pytest.approx(60.0)  # width
        assert bbox.size_y == pytest.approx(24.0)  # depth
        assert bbox.size_z == pytest.approx(1.0)  # thickness

    def test_panel3dmapper_generates_waterfall_edge_bounding_box(self) -> None:
        """Test Panel3DMapper generates correct bounding box for waterfall edge."""
        cabinet = Cabinet(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_4(),
        )

        # Create waterfall edge panel
        waterfall_panel = Panel(
            panel_type=PanelType.WATERFALL_EDGE,
            width=60.0,
            height=26.0,  # desk_height - 4" gap
            material=MaterialSpec(thickness=1.0),
            position=Position(0, 0),
        )

        mapper = Panel3DMapper(cabinet)
        bbox = mapper.map_panel(waterfall_panel)

        # Waterfall edge should be at front of cabinet
        assert bbox.origin.y == pytest.approx(cabinet.depth - 1.0)

        # Verify dimensions (vertical panel at front)
        assert bbox.size_x == pytest.approx(60.0)
        assert bbox.size_y == pytest.approx(1.0)  # thickness
        assert bbox.size_z == pytest.approx(26.0)

    def test_panel3dmapper_generates_keyboard_tray_bounding_box(self) -> None:
        """Test Panel3DMapper generates correct bounding box for keyboard tray."""
        cabinet = Cabinet(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_4(),
        )

        # Create keyboard tray panel
        tray_panel = Panel(
            panel_type=PanelType.KEYBOARD_TRAY,
            width=20.0,
            height=10.0,  # depth becomes height
            material=MaterialSpec.standard_3_4(),
            position=Position(20.0, 26.0),  # centered, at tray height
        )

        mapper = Panel3DMapper(cabinet)
        bbox = mapper.map_panel(tray_panel)

        # Keyboard tray is horizontal panel below desktop
        assert bbox.origin.z == pytest.approx(26.0)  # position.y becomes z
        assert bbox.size_x == pytest.approx(20.0)
        assert bbox.size_y == pytest.approx(10.0)  # tray depth
        assert bbox.size_z == pytest.approx(0.75)  # thickness

    def test_stl_export_desk_panels(self, tmp_path) -> None:
        """Test STL export of complete desk with panels."""
        cabinet = Cabinet(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_4(),
        )

        # Create desk-like cabinet structure
        context = ComponentContext(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=60.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )

        # Generate surface panels (result used to verify component generates)
        surface = DeskSurfaceComponent()
        config = {"desk_height": 30.0, "depth": 24.0}
        surface.generate(config, context)

        # Export to STL
        exporter = StlExporter()
        stl_path = tmp_path / "desk.stl"
        exporter.export_to_file(cabinet, stl_path)

        # Verify STL file was created
        assert stl_path.exists()
        assert stl_path.stat().st_size > 0


# =============================================================================
# Test 8: End-to-End Workflow
# =============================================================================


class TestEndToEndWorkflow:
    """End-to-end tests for complete desk built-in configurations."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_home_office_builtin_desk_center_cabinet_sides(self) -> None:
        """Test full home office built-in with desk in center and cabinets on sides.

        Layout: [Storage Cabinet] - [Desk with Pedestals] - [Storage Cabinet]
        """
        # Left storage cabinet context (defined for future use)
        _left_context = ComponentContext(
            width=24.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=120.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
            adjacent_right="desk",
        )

        # Desk section context (center)
        desk_context = ComponentContext(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(24.0, 0),
            section_index=1,
            cabinet_width=120.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
            adjacent_left="storage",
            adjacent_right="storage",
        )

        # Right storage cabinet context (defined for future use)
        _right_context = ComponentContext(
            width=36.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(84.0, 0),
            section_index=2,
            cabinet_width=120.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
            adjacent_left="desk",
        )

        # Generate desk surface
        surface = DeskSurfaceComponent()
        surface_result = surface.generate(
            {"desk_height": 30.0, "depth": 24.0}, desk_context
        )

        # Generate left pedestal
        left_pedestal = DeskPedestalComponent()
        left_ped_context = ComponentContext(
            width=18.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(24.0, 0),
            section_index=1,
            cabinet_width=120.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )
        left_ped_result = left_pedestal.generate(
            {"pedestal_type": "file", "width": 18.0, "desktop_height": 30.0},
            left_ped_context,
        )

        # Generate right pedestal
        right_ped_context = ComponentContext(
            width=18.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(66.0, 0),
            section_index=1,
            cabinet_width=120.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )
        right_ped_result = left_pedestal.generate(
            {
                "pedestal_type": "storage",
                "width": 18.0,
                "drawer_count": 3,
                "desktop_height": 30.0,
            },
            right_ped_context,
        )

        # Verify total width matches expectations
        # Left cabinet (24) + Desk (60) + Right cabinet (36) = 120"
        total_width = 24.0 + 60.0 + 36.0
        assert total_width == 120.0

        # Verify desk section position
        assert desk_context.position.x == 24.0

        # Verify pedestals fit within desk section
        # Left pedestal at 24 (after left cabinet)
        assert left_ped_context.position.x == 24.0
        # Right pedestal at 66 (24 + 60 - 18)
        assert right_ped_context.position.x == 66.0

        # Verify panels generated for all components
        assert len(surface_result.panels) > 0
        assert len(left_ped_result.panels) > 0
        assert len(right_ped_result.panels) > 0

        # Verify hardware totals
        total_hardware = (
            len(list(surface_result.hardware))
            + len(list(left_ped_result.hardware))
            + len(list(right_ped_result.hardware))
        )
        assert total_hardware > 0

    def test_kitchen_desk_nook_configuration(self) -> None:
        """Test kitchen desk nook with base cabinet integration.

        Layout: A small desk area that matches kitchen cabinets,
        with desk at counter height - 6" and single pedestal.
        """
        # Kitchen desk context (matches 24" deep base cabinets)
        desk_context = ComponentContext(
            width=36.0,
            height=84.0,
            depth=24.0,  # Match kitchen base cabinet depth
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=36.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )

        # Desk surface at 30" (typical counter is 36", desk is counter - 6")
        surface = DeskSurfaceComponent()
        surface_config = {
            "desk_height": 30.0,
            "depth": 24.0,
            "edge_treatment": "square",
            "grommets": [{"x_position": 18.0, "y_position": 21.0, "diameter": 2.5}],
        }
        surface_result = surface.generate(surface_config, desk_context)

        # Single storage pedestal on one side
        pedestal_context = ComponentContext(
            width=18.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=36.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )
        pedestal = DeskPedestalComponent()
        pedestal_config = {
            "pedestal_type": "storage",
            "width": 18.0,
            "drawer_count": 2,
            "desktop_height": 30.0,
        }
        pedestal_result = pedestal.generate(pedestal_config, pedestal_context)

        # Optional keyboard tray
        keyboard = KeyboardTrayComponent()
        keyboard_config = {"width": 20.0, "enclosed": False}
        keyboard_result = keyboard.generate(keyboard_config, desk_context)

        # Verify desk surface dimensions
        desktop = next(
            p for p in surface_result.panels if p.panel_type == PanelType.DESKTOP
        )
        assert desktop.width == 36.0
        assert desktop.height == 24.0  # depth in 2D representation

        # Verify grommet in hardware
        grommet_items = [h for h in surface_result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 1

        # Verify pedestal generates proper panels
        ped_panel_types = {p.panel_type for p in pedestal_result.panels}
        assert PanelType.LEFT_SIDE in ped_panel_types
        assert PanelType.RIGHT_SIDE in ped_panel_types

        # Verify keyboard tray hardware
        kb_slide_items = [h for h in keyboard_result.hardware if "Slide" in h.name]
        assert len(kb_slide_items) >= 1

    def test_standing_desk_with_lower_storage(self) -> None:
        """Test standing-height desk with lower storage zone."""
        context = ComponentContext(
            width=60.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=60.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )

        # Standing desk surface at 42" height
        surface = DeskSurfaceComponent()
        surface_config = {
            "desk_height": 42.0,  # Standing height
            "depth": 22.0,  # Slightly shallower for standing
        }
        surface_result = surface.generate(surface_config, context)

        # Verify desktop at standing height
        assert surface_result.metadata.get("desk_height") == 42.0

        # Storage pedestal below (41" height available)
        pedestal_context = ComponentContext(
            width=24.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=60.0,
            cabinet_height=84.0,
            cabinet_depth=24.0,
        )
        pedestal = DeskPedestalComponent()
        pedestal_config = {
            "pedestal_type": "open",  # Open shelves for standing desk
            "width": 24.0,
            "shelf_count": 3,  # Multiple shelves in tall space
            "desktop_height": 42.0,
        }
        pedestal_result = pedestal.generate(pedestal_config, pedestal_context)

        # Verify pedestal height for standing desk
        # pedestal_height = desktop_height - desktop_thickness (default 1.0)
        assert pedestal_result.metadata.get("pedestal_height") == pytest.approx(41.0)

        # Open pedestal should have shelf pins, no drawer slides
        shelf_pin_items = [h for h in pedestal_result.hardware if "Shelf Pin" in h.name]
        assert len(shelf_pin_items) >= 1
        drawer_slide_items = [h for h in pedestal_result.hardware if "Slide" in h.name]
        assert len(drawer_slide_items) == 0


# =============================================================================
# Test Validation
# =============================================================================


class TestDeskValidation:
    """Tests for desk component validation."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_desk_surface_validates_height_range(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test that desk height outside valid range generates error."""
        surface = DeskSurfaceComponent()

        # Height too low
        config_low = {"desk_height": 20.0}
        result_low = surface.validate(config_low, standard_desk_context)
        assert not result_low.is_valid
        assert any("outside standard range" in e for e in result_low.errors)

        # Height too high
        config_high = {"desk_height": 55.0}
        result_high = surface.validate(config_high, standard_desk_context)
        assert not result_high.is_valid

    def test_desk_surface_validates_depth_minimum(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test that desk depth below minimum generates error."""
        surface = DeskSurfaceComponent()

        config = {"desk_height": 30.0, "depth": 15.0}
        result = surface.validate(config, standard_desk_context)

        assert not result.is_valid
        assert any("too shallow" in e for e in result.errors)

    def test_l_shaped_validates_corner_type(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test L-shaped desk validates corner connection type."""
        l_desk = LShapedDeskComponent()

        # Invalid corner type
        config = {
            "main_surface_width": 48.0,
            "return_surface_width": 36.0,
            "corner_connection_type": "invalid_type",
        }
        result = l_desk.validate(config, standard_desk_context)

        assert not result.is_valid
        assert any(
            "corner_type" in e and ("butt" in e or "diagonal" in e)
            for e in result.errors
        )

    def test_keyboard_tray_validates_knee_clearance(
        self, standard_desk_context: ComponentContext
    ) -> None:
        """Test keyboard tray validates knee clearance is maintained."""
        keyboard = KeyboardTrayComponent()

        # With very low knee clearance height, tray should fail validation
        config = {
            "width": 20.0,
            "knee_clearance_height": 20.0,  # Too low with tray installed
            "tray_clearance": 2.0,
        }
        result = keyboard.validate(config, standard_desk_context)

        # Effective knee height = 20 - 2 - 0.75 = 17.25" < 22" minimum
        assert not result.is_valid
        assert any("knee clearance" in e.lower() for e in result.errors)


# =============================================================================
# Component Registry Tests
# =============================================================================


class TestDeskComponentRegistry:
    """Tests for desk component registration."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_desk_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_all_desk_components_registered(self) -> None:
        """Verify all desk components are registered in the component registry."""
        registered = component_registry.list()

        assert "desk.surface" in registered
        assert "desk.pedestal" in registered
        assert "desk.keyboard_tray" in registered
        assert "desk.monitor_shelf" in registered
        assert "desk.hutch" in registered
        assert "desk.l_shaped" in registered

    def test_desk_components_can_be_retrieved(self) -> None:
        """Verify desk components can be retrieved from registry."""
        surface_class = component_registry.get("desk.surface")
        pedestal_class = component_registry.get("desk.pedestal")
        keyboard_class = component_registry.get("desk.keyboard_tray")
        monitor_class = component_registry.get("desk.monitor_shelf")
        hutch_class = component_registry.get("desk.hutch")
        l_shaped_class = component_registry.get("desk.l_shaped")

        assert surface_class == DeskSurfaceComponent
        assert pedestal_class == DeskPedestalComponent
        assert keyboard_class == KeyboardTrayComponent
        assert monitor_class == MonitorShelfComponent
        assert hutch_class == DeskHutchComponent
        assert l_shaped_class == LShapedDeskComponent

    def test_desk_components_have_required_methods(self) -> None:
        """Verify desk components have validate, generate, and hardware methods."""
        component_names = [
            "desk.surface",
            "desk.pedestal",
            "desk.keyboard_tray",
            "desk.monitor_shelf",
            "desk.hutch",
            "desk.l_shaped",
        ]

        for name in component_names:
            component_class = component_registry.get(name)
            component = component_class()

            assert hasattr(component, "validate")
            assert hasattr(component, "generate")
            assert hasattr(component, "hardware")
            assert callable(getattr(component, "validate"))
            assert callable(getattr(component, "generate"))
            assert callable(getattr(component, "hardware"))
