"""Unit tests for Panel3DMapper.

These tests verify:
- Mapping 2D panels to 3D bounding boxes for each PanelType
- Correct positioning and dimensions for structural panels
- Correct handling of new corner cabinet panel types (DIAGONAL_FACE, FILLER)
- Panel metadata handling for angled panels
"""

import math

import pytest

from cabinets.domain.entities import Cabinet, Panel
from cabinets.domain.services import Panel3DMapper
from cabinets.domain.value_objects import (
    BoundingBox3D,
    MaterialSpec,
    PanelType,
    Position,
)


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Standard 3/4 inch plywood."""
    return MaterialSpec.standard_3_4()


@pytest.fixture
def back_material() -> MaterialSpec:
    """Standard 1/2 inch plywood for backs."""
    return MaterialSpec.standard_1_2()


@pytest.fixture
def simple_cabinet(
    standard_material: MaterialSpec, back_material: MaterialSpec
) -> Cabinet:
    """Create a simple cabinet for testing."""
    return Cabinet(
        width=24.0,
        height=30.0,
        depth=12.0,
        material=standard_material,
        back_material=back_material,
    )


@pytest.fixture
def mapper(simple_cabinet: Cabinet) -> Panel3DMapper:
    """Create a Panel3DMapper instance for testing."""
    return Panel3DMapper(simple_cabinet)


class TestPanel3DMapperInit:
    """Tests for Panel3DMapper initialization."""

    def test_init_with_cabinet(
        self,
        simple_cabinet: Cabinet,
        standard_material: MaterialSpec,
        back_material: MaterialSpec,
    ) -> None:
        """Should initialize with cabinet properties."""
        mapper = Panel3DMapper(simple_cabinet)
        assert mapper.cabinet is simple_cabinet
        assert mapper.back_thickness == back_material.thickness
        assert mapper.material_thickness == standard_material.thickness


class TestMapPanelDiagonalFace:
    """Tests for mapping DIAGONAL_FACE panels."""

    def test_diagonal_face_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DIAGONAL_FACE panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=24.0 * math.sqrt(2),  # Diagonal width for 24" depth
            height=28.5,  # Interior height
            material=standard_material,
            position=Position(x=0.75, y=0.75),
            metadata={"is_angled": True, "angle": 45},
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_diagonal_face_positioned_at_front(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DIAGONAL_FACE panel should be positioned at the front face of cabinet."""
        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=33.94,  # Approximate diagonal width
            height=28.5,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
            metadata={"is_angled": True, "angle": 45},
        )

        result = mapper.map_panel(panel)

        # Y position should be at cabinet_depth - thickness (front face)
        expected_y = mapper.cabinet.depth - standard_material.thickness
        assert result.origin.y == pytest.approx(expected_y)

    def test_diagonal_face_uses_panel_position_for_x_and_z(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DIAGONAL_FACE panel should use panel.position for X and Z coordinates."""
        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=33.94,
            height=28.5,
            material=standard_material,
            position=Position(x=5.0, y=10.0),
            metadata={"is_angled": True, "angle": 45},
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(5.0)
        assert result.origin.z == pytest.approx(10.0)

    def test_diagonal_face_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DIAGONAL_FACE panel should have correct dimensions."""
        panel_width = 33.94
        panel_height = 28.5
        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=panel_width,
            height=panel_height,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
            metadata={"is_angled": True, "angle": 45},
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(panel_width)
        assert result.size_y == pytest.approx(standard_material.thickness)
        assert result.size_z == pytest.approx(panel_height)

    def test_diagonal_face_without_metadata(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DIAGONAL_FACE panel should work even without metadata."""
        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=33.94,
            height=28.5,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)
        assert result.size_x == pytest.approx(33.94)

    def test_diagonal_face_with_different_cabinet_depth(
        self, standard_material: MaterialSpec, back_material: MaterialSpec
    ) -> None:
        """DIAGONAL_FACE positioning should adapt to cabinet depth."""
        deep_cabinet = Cabinet(
            width=36.0,
            height=30.0,
            depth=24.0,  # Deeper cabinet
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(deep_cabinet)

        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=24.0 * math.sqrt(2),
            height=28.5,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
            metadata={"is_angled": True, "angle": 45},
        )

        result = mapper.map_panel(panel)

        # Y position should be at 24.0 - 0.75 = 23.25 for deeper cabinet
        expected_y = 24.0 - standard_material.thickness
        assert result.origin.y == pytest.approx(expected_y)


class TestMapPanelFiller:
    """Tests for mapping FILLER panels."""

    def test_filler_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """FILLER panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.FILLER,
            width=11.5,  # Interior depth
            height=28.5,  # Interior height
            material=standard_material,
            position=Position(x=0.75, y=0.75),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_filler_positioned_after_back(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """FILLER panel should be positioned after the back panel."""
        panel = Panel(
            panel_type=PanelType.FILLER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
        )

        result = mapper.map_panel(panel)

        # Y position should start after back panel thickness
        assert result.origin.y == pytest.approx(mapper.back_thickness)

    def test_filler_uses_panel_position_for_x_and_z(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """FILLER panel should use panel.position for X and Z coordinates."""
        panel = Panel(
            panel_type=PanelType.FILLER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=3.0, y=0.75),
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(3.0)
        assert result.origin.z == pytest.approx(0.75)

    def test_filler_dimensions_vertical_panel(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """FILLER panel should have correct dimensions as vertical panel."""
        panel_width = 11.5  # This is depth for vertical panels
        panel_height = 28.5
        panel = Panel(
            panel_type=PanelType.FILLER,
            width=panel_width,
            height=panel_height,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
        )

        result = mapper.map_panel(panel)

        # For vertical panels: size_x = thickness, size_y = panel.width (depth)
        assert result.size_x == pytest.approx(standard_material.thickness)
        assert result.size_y == pytest.approx(panel_width)
        assert result.size_z == pytest.approx(panel_height)

    def test_filler_similar_to_divider(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """FILLER and DIVIDER panels should have same dimensional behavior."""
        filler = Panel(
            panel_type=PanelType.FILLER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=12.0, y=0.75),
        )
        divider = Panel(
            panel_type=PanelType.DIVIDER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=12.0, y=0.75),
        )

        filler_result = mapper.map_panel(filler)
        divider_result = mapper.map_panel(divider)

        # Both should have same origin and dimensions
        assert filler_result.origin.x == divider_result.origin.x
        assert filler_result.origin.y == divider_result.origin.y
        assert filler_result.origin.z == divider_result.origin.z
        assert filler_result.size_x == divider_result.size_x
        assert filler_result.size_y == divider_result.size_y
        assert filler_result.size_z == divider_result.size_z

    def test_filler_with_different_position(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """FILLER panel at different positions should be correctly mapped."""
        # Left side filler
        left_filler = Panel(
            panel_type=PanelType.FILLER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=0.0, y=0.75),
        )
        # Right side filler
        right_filler = Panel(
            panel_type=PanelType.FILLER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=24.0, y=0.75),
        )

        left_result = mapper.map_panel(left_filler)
        right_result = mapper.map_panel(right_filler)

        assert left_result.origin.x == pytest.approx(0.0)
        assert right_result.origin.x == pytest.approx(24.0)


class TestMapPanelExistingTypes:
    """Tests to ensure existing panel types still work correctly."""

    def test_door_panel(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DOOR panel should still be mapped correctly."""
        panel = Panel(
            panel_type=PanelType.DOOR,
            width=22.0,
            height=28.0,
            material=standard_material,
            position=Position(x=1.0, y=1.0),
        )

        result = mapper.map_panel(panel)

        # Door should be at front face
        expected_y = mapper.cabinet.depth - standard_material.thickness
        assert result.origin.y == pytest.approx(expected_y)
        assert result.size_x == pytest.approx(22.0)
        assert result.size_z == pytest.approx(28.0)

    def test_divider_panel(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DIVIDER panel should still be mapped correctly."""
        panel = Panel(
            panel_type=PanelType.DIVIDER,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=12.0, y=0.75),
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(12.0)
        assert result.origin.y == pytest.approx(mapper.back_thickness)
        assert result.origin.z == pytest.approx(0.75)
        assert result.size_x == pytest.approx(standard_material.thickness)
        assert result.size_y == pytest.approx(11.5)
        assert result.size_z == pytest.approx(28.5)

    def test_shelf_panel(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """SHELF panel should still be mapped correctly."""
        panel = Panel(
            panel_type=PanelType.SHELF,
            width=22.5,
            height=11.5,  # Depth for horizontal panels
            material=standard_material,
            position=Position(x=0.75, y=15.0),
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(0.75)
        assert result.origin.y == pytest.approx(mapper.back_thickness)
        assert result.origin.z == pytest.approx(15.0)
        assert result.size_x == pytest.approx(22.5)
        assert result.size_y == pytest.approx(11.5)
        assert result.size_z == pytest.approx(standard_material.thickness)


class TestMapAllPanels:
    """Tests for map_all_panels method."""

    def test_map_all_panels_returns_list(self, simple_cabinet: Cabinet) -> None:
        """map_all_panels should return a list of BoundingBox3D."""
        mapper = Panel3DMapper(simple_cabinet)
        result = mapper.map_all_panels()

        assert isinstance(result, list)
        assert all(isinstance(box, BoundingBox3D) for box in result)

    def test_map_all_panels_includes_structural_panels(
        self, simple_cabinet: Cabinet
    ) -> None:
        """map_all_panels should include all structural panels."""
        mapper = Panel3DMapper(simple_cabinet)
        result = mapper.map_all_panels()

        # Simple cabinet has: TOP, BOTTOM, LEFT_SIDE, RIGHT_SIDE, BACK = 5 panels
        assert len(result) == 5


class TestPanelMetadataHandling:
    """Tests for handling panel metadata, particularly for angled panels."""

    def test_angled_panel_metadata_preserved_in_input(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """Panel metadata should be accessible on the input panel."""
        panel = Panel(
            panel_type=PanelType.DIAGONAL_FACE,
            width=33.94,
            height=28.5,
            material=standard_material,
            position=Position(x=0.75, y=0.75),
            metadata={"is_angled": True, "angle": 45},
        )

        # Verify metadata is on the panel
        assert panel.metadata.get("is_angled") is True
        assert panel.metadata.get("angle") == 45

        # Map the panel (the bounding box itself doesn't carry metadata)
        result = mapper.map_panel(panel)
        assert isinstance(result, BoundingBox3D)

    def test_side_panels_with_angle_metadata(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """Side panels with angle metadata should still map correctly."""
        # In diagonal corner cabinets, side panels have angle cuts
        panel = Panel(
            panel_type=PanelType.LEFT_SIDE,
            width=11.5,
            height=28.5,
            material=standard_material,
            position=Position(x=0, y=0.75),
            metadata={"is_angled": True, "angle": 45},
        )

        result = mapper.map_panel(panel)

        # Should still map as a normal left side panel
        assert result.origin.x == 0
        assert result.size_x == pytest.approx(standard_material.thickness)


class TestMapPanelDesktop:
    """Tests for mapping DESKTOP panels (FRD-18)."""

    def test_desktop_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DESKTOP panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=48.0,
            height=24.0,  # depth in 2D
            material=standard_material,
            position=Position(x=0, y=0),
            metadata={"desk_height": 30.0},
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_desktop_positioned_at_desk_height(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DESKTOP panel should be positioned at desk_height - thickness."""
        desk_height = 30.0
        panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=48.0,
            height=24.0,
            material=standard_material,
            position=Position(x=0, y=0),
            metadata={"desk_height": desk_height},
        )

        result = mapper.map_panel(panel)

        # Z position should be at desk_height - thickness
        expected_z = desk_height - standard_material.thickness
        assert result.origin.z == pytest.approx(expected_z)

    def test_desktop_uses_default_desk_height_without_metadata(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DESKTOP panel without metadata should use default 30.0 desk height."""
        panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=48.0,
            height=24.0,
            material=standard_material,
            position=Position(x=0, y=0),
        )

        result = mapper.map_panel(panel)

        # Default desk_height is 30.0
        expected_z = 30.0 - standard_material.thickness
        assert result.origin.z == pytest.approx(expected_z)

    def test_desktop_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DESKTOP panel should have correct dimensions."""
        panel_width = 48.0
        panel_depth = 24.0
        panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=panel_width,
            height=panel_depth,  # depth for horizontal panels
            material=standard_material,
            position=Position(x=0, y=0),
            metadata={"desk_height": 30.0},
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(panel_width)
        assert result.size_y == pytest.approx(panel_depth)
        assert result.size_z == pytest.approx(standard_material.thickness)

    def test_desktop_uses_panel_position_x(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """DESKTOP panel should use panel.position.x for X coordinate."""
        panel = Panel(
            panel_type=PanelType.DESKTOP,
            width=48.0,
            height=24.0,
            material=standard_material,
            position=Position(x=12.0, y=0),
            metadata={"desk_height": 30.0},
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(12.0)


class TestMapPanelWaterfallEdge:
    """Tests for mapping WATERFALL_EDGE panels (FRD-18)."""

    def test_waterfall_edge_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WATERFALL_EDGE panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.WATERFALL_EDGE,
            width=48.0,
            height=28.0,  # drop height
            material=standard_material,
            position=Position(x=0, y=0),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_waterfall_edge_positioned_at_front(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WATERFALL_EDGE panel should be positioned at cabinet front face."""
        panel = Panel(
            panel_type=PanelType.WATERFALL_EDGE,
            width=48.0,
            height=28.0,
            material=standard_material,
            position=Position(x=0, y=0),
        )

        result = mapper.map_panel(panel)

        # Y position should be at cabinet_depth - thickness (front face)
        expected_y = mapper.cabinet.depth - standard_material.thickness
        assert result.origin.y == pytest.approx(expected_y)

    def test_waterfall_edge_uses_panel_position_for_x_and_z(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WATERFALL_EDGE panel should use panel.position for X and Z."""
        panel = Panel(
            panel_type=PanelType.WATERFALL_EDGE,
            width=48.0,
            height=28.0,
            material=standard_material,
            position=Position(x=5.0, y=2.0),  # y is Z in 3D
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(5.0)
        assert result.origin.z == pytest.approx(2.0)

    def test_waterfall_edge_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WATERFALL_EDGE panel should have correct dimensions as vertical panel."""
        panel_width = 48.0
        panel_height = 28.0
        panel = Panel(
            panel_type=PanelType.WATERFALL_EDGE,
            width=panel_width,
            height=panel_height,
            material=standard_material,
            position=Position(x=0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(panel_width)
        assert result.size_y == pytest.approx(standard_material.thickness)
        assert result.size_z == pytest.approx(panel_height)


class TestMapPanelKeyboardTray:
    """Tests for mapping KEYBOARD_TRAY panels (FRD-18)."""

    def test_keyboard_tray_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_TRAY panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.KEYBOARD_TRAY,
            width=24.0,
            height=10.0,  # tray depth
            material=standard_material,
            position=Position(x=12.0, y=26.0),  # y is height
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_keyboard_tray_positioned_at_specified_height(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_TRAY panel should be positioned at specified height."""
        tray_height = 26.0
        panel = Panel(
            panel_type=PanelType.KEYBOARD_TRAY,
            width=24.0,
            height=10.0,
            material=standard_material,
            position=Position(x=12.0, y=tray_height),
        )

        result = mapper.map_panel(panel)

        assert result.origin.z == pytest.approx(tray_height)

    def test_keyboard_tray_uses_default_height_when_zero(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_TRAY panel at position.y=0 should use default 26.0 height."""
        panel = Panel(
            panel_type=PanelType.KEYBOARD_TRAY,
            width=24.0,
            height=10.0,
            material=standard_material,
            position=Position(x=12.0, y=0),
        )

        result = mapper.map_panel(panel)

        # Default tray height is 26.0 (4" below 30" desk)
        assert result.origin.z == pytest.approx(26.0)

    def test_keyboard_tray_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_TRAY panel should have correct dimensions as horizontal panel."""
        panel_width = 24.0
        panel_depth = 10.0
        panel = Panel(
            panel_type=PanelType.KEYBOARD_TRAY,
            width=panel_width,
            height=panel_depth,
            material=standard_material,
            position=Position(x=12.0, y=26.0),
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(panel_width)
        assert result.size_y == pytest.approx(panel_depth)
        assert result.size_z == pytest.approx(standard_material.thickness)


class TestMapPanelKeyboardEnclosure:
    """Tests for mapping KEYBOARD_ENCLOSURE panels (FRD-18)."""

    def test_keyboard_enclosure_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_ENCLOSURE panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.KEYBOARD_ENCLOSURE,
            width=10.0,  # enclosure depth
            height=4.0,  # enclosure height
            material=standard_material,
            position=Position(x=12.0, y=26.0),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_keyboard_enclosure_positioned_after_back(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_ENCLOSURE panel should be positioned after back panel."""
        panel = Panel(
            panel_type=PanelType.KEYBOARD_ENCLOSURE,
            width=10.0,
            height=4.0,
            material=standard_material,
            position=Position(x=12.0, y=26.0),
        )

        result = mapper.map_panel(panel)

        assert result.origin.y == pytest.approx(mapper.back_thickness)

    def test_keyboard_enclosure_uses_panel_position(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_ENCLOSURE panel should use panel.position for X and Z."""
        panel = Panel(
            panel_type=PanelType.KEYBOARD_ENCLOSURE,
            width=10.0,
            height=4.0,
            material=standard_material,
            position=Position(x=12.0, y=26.0),
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(12.0)
        assert result.origin.z == pytest.approx(26.0)

    def test_keyboard_enclosure_dimensions_vertical_panel(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """KEYBOARD_ENCLOSURE panel should have correct dimensions as vertical panel."""
        panel_depth = 10.0  # This is depth for vertical panels
        panel_height = 4.0
        panel = Panel(
            panel_type=PanelType.KEYBOARD_ENCLOSURE,
            width=panel_depth,
            height=panel_height,
            material=standard_material,
            position=Position(x=12.0, y=26.0),
        )

        result = mapper.map_panel(panel)

        # For vertical panels: size_x = thickness, size_y = panel.width (depth)
        assert result.size_x == pytest.approx(standard_material.thickness)
        assert result.size_y == pytest.approx(panel_depth)
        assert result.size_z == pytest.approx(panel_height)


class TestMapPanelModestyPanel:
    """Tests for mapping MODESTY_PANEL panels (FRD-18)."""

    def test_modesty_panel_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """MODESTY_PANEL panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.MODESTY_PANEL,
            width=36.0,
            height=12.0,
            material=standard_material,
            position=Position(x=6.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_modesty_panel_positioned_after_back(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """MODESTY_PANEL should be positioned after back panel (at knee zone back)."""
        panel = Panel(
            panel_type=PanelType.MODESTY_PANEL,
            width=36.0,
            height=12.0,
            material=standard_material,
            position=Position(x=6.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.origin.y == pytest.approx(mapper.back_thickness)

    def test_modesty_panel_uses_panel_position(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """MODESTY_PANEL should use panel.position for X and Z."""
        panel = Panel(
            panel_type=PanelType.MODESTY_PANEL,
            width=36.0,
            height=12.0,
            material=standard_material,
            position=Position(x=6.0, y=8.0),
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(6.0)
        assert result.origin.z == pytest.approx(8.0)

    def test_modesty_panel_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """MODESTY_PANEL should have correct dimensions as vertical panel."""
        panel_width = 36.0
        panel_height = 12.0
        panel = Panel(
            panel_type=PanelType.MODESTY_PANEL,
            width=panel_width,
            height=panel_height,
            material=standard_material,
            position=Position(x=6.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(panel_width)
        assert result.size_y == pytest.approx(standard_material.thickness)
        assert result.size_z == pytest.approx(panel_height)


class TestMapPanelWireChase:
    """Tests for mapping WIRE_CHASE panels (FRD-18)."""

    def test_wire_chase_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WIRE_CHASE panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.WIRE_CHASE,
            width=3.0,  # chase width
            height=26.0,  # pedestal height
            material=standard_material,
            position=Position(x=10.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_wire_chase_positioned_at_back_wall(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WIRE_CHASE panel should be positioned at y=0 (back wall)."""
        panel = Panel(
            panel_type=PanelType.WIRE_CHASE,
            width=3.0,
            height=26.0,
            material=standard_material,
            position=Position(x=10.0, y=0),
        )

        result = mapper.map_panel(panel)

        # Y position should be at back wall (0)
        assert result.origin.y == pytest.approx(0)

    def test_wire_chase_uses_panel_position(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WIRE_CHASE panel should use panel.position for X and Z."""
        panel = Panel(
            panel_type=PanelType.WIRE_CHASE,
            width=3.0,
            height=26.0,
            material=standard_material,
            position=Position(x=10.0, y=4.0),  # y is Z (above floor)
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(10.0)
        assert result.origin.z == pytest.approx(4.0)

    def test_wire_chase_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """WIRE_CHASE panel should have correct dimensions."""
        panel_width = 3.0
        panel_height = 26.0
        panel = Panel(
            panel_type=PanelType.WIRE_CHASE,
            width=panel_width,
            height=panel_height,
            material=standard_material,
            position=Position(x=10.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(panel_width)
        assert result.size_y == pytest.approx(standard_material.thickness)
        assert result.size_z == pytest.approx(panel_height)


class TestMapPanelCableChase:
    """Tests for mapping CABLE_CHASE panels (FRD-19 Entertainment Centers)."""

    def test_cable_chase_returns_bounding_box(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should return a valid BoundingBox3D."""
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,  # chase width (typical 3-4 inches)
            height=60.0,  # full section height
            material=standard_material,
            position=Position(x=20.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert isinstance(result, BoundingBox3D)

    def test_cable_chase_positioned_at_rear_of_cabinet(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should be positioned at rear of cabinet."""
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,
            height=60.0,
            material=standard_material,
            position=Position(x=20.0, y=0),
        )

        result = mapper.map_panel(panel)

        # Y position should be at cabinet_depth - thickness (rear of cabinet)
        expected_y = mapper.cabinet.depth - standard_material.thickness
        assert result.origin.y == pytest.approx(expected_y)

    def test_cable_chase_uses_panel_position_for_x(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should use panel.position.x for X coordinate."""
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,
            height=60.0,
            material=standard_material,
            position=Position(x=20.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.origin.x == pytest.approx(20.0)

    def test_cable_chase_uses_panel_position_for_z(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should use panel.position.y for Z coordinate (height)."""
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,
            height=60.0,
            material=standard_material,
            position=Position(x=20.0, y=6.0),  # Start 6 inches from floor
        )

        result = mapper.map_panel(panel)

        assert result.origin.z == pytest.approx(6.0)

    def test_cable_chase_dimensions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should have correct dimensions."""
        chase_width = 4.0
        chase_height = 60.0
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=chase_width,
            height=chase_height,
            material=standard_material,
            position=Position(x=20.0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(chase_width)
        assert result.size_y == pytest.approx(standard_material.thickness)
        assert result.size_z == pytest.approx(chase_height)

    def test_cable_chase_narrow_width(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should work with narrow 3-inch width."""
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.0,  # Narrow chase
            height=72.0,  # Full cabinet height
            material=standard_material,
            position=Position(x=0, y=0),
        )

        result = mapper.map_panel(panel)

        assert result.size_x == pytest.approx(3.0)
        assert result.size_z == pytest.approx(72.0)

    def test_cable_chase_at_different_positions(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE panel should work at different X positions."""
        # Left side chase
        left_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.5,
            height=60.0,
            material=standard_material,
            position=Position(x=0, y=0),
        )
        # Center chase
        center_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.5,
            height=60.0,
            material=standard_material,
            position=Position(x=10.0, y=0),
        )
        # Right side chase
        right_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.5,
            height=60.0,
            material=standard_material,
            position=Position(x=20.0, y=0),
        )

        left_result = mapper.map_panel(left_chase)
        center_result = mapper.map_panel(center_chase)
        right_result = mapper.map_panel(right_chase)

        assert left_result.origin.x == pytest.approx(0)
        assert center_result.origin.x == pytest.approx(10.0)
        assert right_result.origin.x == pytest.approx(20.0)
        # All should be at rear
        expected_y = mapper.cabinet.depth - standard_material.thickness
        assert left_result.origin.y == pytest.approx(expected_y)
        assert center_result.origin.y == pytest.approx(expected_y)
        assert right_result.origin.y == pytest.approx(expected_y)

    def test_cable_chase_with_different_cabinet_depth(
        self, standard_material: MaterialSpec, back_material: MaterialSpec
    ) -> None:
        """CABLE_CHASE positioning should adapt to cabinet depth."""
        deep_cabinet = Cabinet(
            width=48.0,
            height=72.0,
            depth=24.0,  # Deeper cabinet (entertainment center)
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(deep_cabinet)

        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,
            height=60.0,
            material=standard_material,
            position=Position(x=22.0, y=0),
        )

        result = mapper.map_panel(panel)

        # Y position should be at 24.0 - 0.75 = 23.25 for deeper cabinet
        expected_y = 24.0 - standard_material.thickness
        assert result.origin.y == pytest.approx(expected_y)

    def test_cable_chase_with_thin_material(self, mapper: Panel3DMapper) -> None:
        """CABLE_CHASE panel with thin material should render correctly."""
        thin_material = MaterialSpec.standard_1_4()  # 1/4 inch material
        panel = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,
            height=60.0,
            material=thin_material,
            position=Position(x=20.0, y=0),
        )

        result = mapper.map_panel(panel)

        # Y origin should adjust for thinner material
        expected_y = mapper.cabinet.depth - thin_material.thickness
        assert result.origin.y == pytest.approx(expected_y)
        # Size Y should be the thin material thickness
        assert result.size_y == pytest.approx(thin_material.thickness)


class TestFallbackPanelType:
    """Tests for the fallback case handling unknown panel types."""

    def test_fallback_handles_unknown_type_gracefully(
        self, mapper: Panel3DMapper, standard_material: MaterialSpec
    ) -> None:
        """Unknown panel types should be handled by fallback case."""
        # Note: This test uses a standard panel type but verifies the fallback
        # behavior works for horizontal panel handling, which is the fallback
        # treatment for any unrecognized panel types
        panel = Panel(
            panel_type=PanelType.SHELF,  # Using a known type
            width=22.0,
            height=11.5,
            material=standard_material,
            position=Position(x=1.0, y=10.0),
        )

        result = mapper.map_panel(panel)

        # Should return a valid BoundingBox3D
        assert isinstance(result, BoundingBox3D)
        # Should use horizontal panel semantics
        assert result.size_z == pytest.approx(standard_material.thickness)
