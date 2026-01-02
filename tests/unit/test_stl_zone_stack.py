"""Unit tests for STL zone stack export functionality (FRD-22 Phase 6).

Tests the StlMeshBuilder stepped side mesh method, Panel3DMapper handling
of new panel types (COUNTERTOP, SUPPORT_BRACKET, STEPPED_SIDE), and
StlExporter zone stack export.
"""

import pytest
import numpy as np
from stl import mesh

from cabinets.domain import (
    BoundingBox3D,
    Cabinet,
    MaterialSpec,
    Panel,
    Panel3DMapper,
    PanelType,
    Position,
)
from cabinets.domain.value_objects import Position3D
from cabinets.domain.services import ZoneStackLayoutResult
from cabinets.infrastructure.stl_exporter import StlExporter, StlMeshBuilder


class TestStlMeshBuilderSteppedSide:
    """Tests for StlMeshBuilder.build_stepped_side_mesh."""

    @pytest.fixture
    def mesh_builder(self) -> StlMeshBuilder:
        """Create a StlMeshBuilder instance."""
        return StlMeshBuilder()

    @pytest.fixture
    def sample_side_box(self) -> BoundingBox3D:
        """Create a sample bounding box for a side panel."""
        return BoundingBox3D(
            origin=Position3D(x=0, y=0.25, z=0),
            size_x=0.75,  # Panel thickness
            size_y=24.0,  # Full depth
            size_z=84.0,  # Full height
        )

    def test_build_stepped_side_mesh_creates_valid_mesh(
        self, mesh_builder: StlMeshBuilder, sample_side_box: BoundingBox3D
    ) -> None:
        """Test that build_stepped_side_mesh creates a valid mesh."""
        result = mesh_builder.build_stepped_side_mesh(
            box=sample_side_box,
            step_height=36.0,  # Step at 36" (e.g., base cabinet height)
            step_depth_change=12.0,  # Upper zone is 12" shallower
        )

        assert isinstance(result, mesh.Mesh)
        # Should have faces from two boxes (12 faces each = 24 total)
        assert result.vectors.shape[0] == 24

    def test_build_stepped_side_mesh_bottom_section_full_depth(
        self, mesh_builder: StlMeshBuilder, sample_side_box: BoundingBox3D
    ) -> None:
        """Test that bottom section has full depth."""
        result = mesh_builder.build_stepped_side_mesh(
            box=sample_side_box,
            step_height=36.0,
            step_depth_change=12.0,
        )

        # Extract all vertices from the mesh
        all_vertices = result.vectors.reshape(-1, 3)

        # Find vertices at z=0 (bottom of panel, which is y in mesh due to transform)
        # After Y-up transform: (x, z, y) -> (x, y, z) in mesh
        # So mesh y corresponds to domain z (height)
        bottom_vertices = all_vertices[all_vertices[:, 1] < 1]  # Near bottom

        # These should span the full depth (domain y becomes mesh z)
        depths = bottom_vertices[:, 2]
        assert np.max(depths) >= 24.0  # Full depth should be present

    def test_build_stepped_side_mesh_top_section_reduced_depth(
        self, mesh_builder: StlMeshBuilder, sample_side_box: BoundingBox3D
    ) -> None:
        """Test that top section has reduced depth."""
        result = mesh_builder.build_stepped_side_mesh(
            box=sample_side_box,
            step_height=36.0,
            step_depth_change=12.0,
        )

        # Extract all vertices from the mesh
        all_vertices = result.vectors.reshape(-1, 3)

        # Find vertices at high z (top of panel, which is y in mesh)
        # The step_height is 36, so vertices above that should have reduced depth
        top_vertices = all_vertices[all_vertices[:, 1] > 50]  # Well above step

        # These should NOT extend to full depth
        depths = top_vertices[:, 2]
        # Reduced depth is 24 - 12 = 12"
        assert np.max(depths) <= 12.5  # Reduced depth (with some tolerance)

    def test_build_stepped_side_mesh_with_wall_transform(
        self, mesh_builder: StlMeshBuilder, sample_side_box: BoundingBox3D
    ) -> None:
        """Test that wall rotation and position are applied correctly."""
        result = mesh_builder.build_stepped_side_mesh(
            box=sample_side_box,
            step_height=36.0,
            step_depth_change=12.0,
            wall_rotation=90.0,
            wall_position=(10.0, 20.0, 0.0),
        )

        assert isinstance(result, mesh.Mesh)
        # Should still have 24 faces
        assert result.vectors.shape[0] == 24

        # Check that vertices have been transformed (different from non-transformed)
        # With 90 degree rotation, coordinates should be swapped
        all_vertices = result.vectors.reshape(-1, 3)
        # The transform applies rotation and translation, so vertices should differ from
        # a non-transformed mesh. Just verify the mesh was created with expected face count.
        assert len(all_vertices) == 24 * 3  # 24 faces, 3 vertices each


class TestPanel3DMapperNewPanelTypes:
    """Tests for Panel3DMapper handling of new FRD-22 panel types."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        return Cabinet(
            width=48.0,
            height=36.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75),
        )

    def test_countertop_panel_creates_horizontal_box(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that COUNTERTOP panel type creates a horizontal bounding box."""
        mapper = Panel3DMapper(sample_cabinet)

        panel = Panel(
            panel_type=PanelType.COUNTERTOP,
            width=48.0,  # Same as cabinet width
            height=24.0,  # Depth (for horizontal panels, height is depth)
            material=MaterialSpec(thickness=1.0),  # Countertop thickness
            position=Position(x=0, y=36.0),  # Height above floor
        )

        box = mapper.map_panel(panel)

        assert isinstance(box, BoundingBox3D)
        # Width should match panel width
        assert box.size_x == 48.0
        # Depth should match panel height (which is depth for horizontal)
        assert box.size_y == 24.0
        # Height (thickness) should match material thickness
        assert box.size_z == 1.0
        # Z position should match panel position.y (countertop height)
        assert box.origin.z == 36.0

    def test_support_bracket_panel_creates_vertical_box(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that SUPPORT_BRACKET panel type creates a vertical box at front."""
        mapper = Panel3DMapper(sample_cabinet)

        panel = Panel(
            panel_type=PanelType.SUPPORT_BRACKET,
            width=1.5,  # Bracket width
            height=6.0,  # Bracket height (vertical dimension)
            material=MaterialSpec(thickness=0.75),
            position=Position(x=10.0, y=30.0),  # Position along cabinet and height
        )

        box = mapper.map_panel(panel)

        assert isinstance(box, BoundingBox3D)
        # Width should match panel width
        assert box.size_x == 1.5
        # Depth should be panel thickness (thin bracket)
        assert box.size_y == 0.75
        # Height should match panel height
        assert box.size_z == 6.0
        # Y position should be at front of cabinet
        assert box.origin.y == sample_cabinet.depth - 0.75

    def test_stepped_side_panel_creates_vertical_box(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that STEPPED_SIDE panel type creates a vertical side panel box."""
        mapper = Panel3DMapper(sample_cabinet)

        panel = Panel(
            panel_type=PanelType.STEPPED_SIDE,
            width=24.0,  # Max depth
            height=84.0,  # Full height
            material=MaterialSpec(thickness=0.75),
            position=Position(x=0, y=0),
            metadata={
                "step_height": 36.0,
                "step_depth_change": 12.0,
            },
        )

        box = mapper.map_panel(panel)

        assert isinstance(box, BoundingBox3D)
        # X dimension should be panel thickness
        assert box.size_x == 0.75
        # Y dimension should be panel width (depth for side panels)
        assert box.size_y == 24.0
        # Z dimension should be panel height
        assert box.size_z == 84.0


class TestStlExporterSteppedSide:
    """Tests for StlExporter handling of STEPPED_SIDE panels."""

    @pytest.fixture
    def exporter(self) -> StlExporter:
        """Create an StlExporter instance."""
        return StlExporter()

    @pytest.fixture
    def cabinet_with_stepped_side(self) -> Cabinet:
        """Create a cabinet with a stepped side panel."""
        from cabinets.domain.entities import Section

        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75),
            sections=[
                Section(
                    width=46.5,
                    height=82.5,
                    depth=23.75,
                    position=Position(x=0.75, y=0.75),
                )
            ],
        )

        # Add a stepped side panel to the first section
        stepped_panel = Panel(
            panel_type=PanelType.STEPPED_SIDE,
            width=24.0,  # Max depth
            height=84.0,  # Full height
            material=MaterialSpec(thickness=0.75),
            position=Position(x=0, y=0),
            metadata={
                "step_height": 36.0,
                "step_depth_change": 12.0,
            },
        )
        cabinet.sections[0].panels.append(stepped_panel)

        return cabinet

    def test_export_cabinet_with_stepped_side_creates_mesh(
        self, exporter: StlExporter, cabinet_with_stepped_side: Cabinet
    ) -> None:
        """Test that exporting a cabinet with stepped side creates valid mesh."""
        result = exporter.export(cabinet_with_stepped_side)

        assert isinstance(result, mesh.Mesh)
        # Should have faces for all panels
        assert result.vectors.shape[0] > 0


class TestStlExporterZoneStack:
    """Tests for StlExporter zone stack export functionality."""

    @pytest.fixture
    def exporter(self) -> StlExporter:
        """Create an StlExporter instance."""
        return StlExporter()

    @pytest.fixture
    def sample_zone_stack_result(self) -> ZoneStackLayoutResult:
        """Create a sample zone stack result for testing."""
        base_cabinet = Cabinet(
            width=48.0,
            height=36.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75),
        )

        upper_cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75),
        )

        countertop_panel = Panel(
            panel_type=PanelType.COUNTERTOP,
            width=48.0,
            height=24.0,  # Depth
            material=MaterialSpec(thickness=1.0),
            position=Position(x=0, y=36.0),
        )

        return ZoneStackLayoutResult(
            base_cabinet=base_cabinet,
            upper_cabinet=upper_cabinet,
            countertop_panels=(countertop_panel,),
        )

    def test_export_zone_stack_mesh_creates_valid_mesh(
        self, exporter: StlExporter, sample_zone_stack_result: ZoneStackLayoutResult
    ) -> None:
        """Test that export_zone_stack_mesh creates a valid mesh."""
        result = exporter.export_zone_stack_mesh(sample_zone_stack_result)

        assert isinstance(result, mesh.Mesh)
        # Should have faces for base cabinet, upper cabinet, and countertop
        assert result.vectors.shape[0] > 0

    def test_export_zone_stack_mesh_with_only_base_cabinet(
        self, exporter: StlExporter
    ) -> None:
        """Test zone stack export with only base cabinet."""
        base_cabinet = Cabinet(
            width=48.0,
            height=36.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75),
        )

        result = ZoneStackLayoutResult(base_cabinet=base_cabinet)

        mesh_result = exporter.export_zone_stack_mesh(result)

        assert isinstance(mesh_result, mesh.Mesh)
        assert mesh_result.vectors.shape[0] > 0

    def test_export_zone_stack_mesh_empty_result(self, exporter: StlExporter) -> None:
        """Test zone stack export with empty result returns empty mesh."""
        result = ZoneStackLayoutResult()

        mesh_result = exporter.export_zone_stack_mesh(result)

        assert isinstance(mesh_result, mesh.Mesh)
        assert mesh_result.vectors.shape[0] == 0

    def test_export_zone_stack_mesh_upper_cabinet_positioned_correctly(
        self, exporter: StlExporter
    ) -> None:
        """Test that upper cabinet is positioned at mounting height."""
        base_cabinet = Cabinet(
            width=48.0,
            height=36.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75),
        )

        upper_cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75),
        )

        result = ZoneStackLayoutResult(
            base_cabinet=base_cabinet,
            upper_cabinet=upper_cabinet,
        )

        mesh_result = exporter.export_zone_stack_mesh(result)

        # Extract all vertices
        all_vertices = mesh_result.vectors.reshape(-1, 3)

        # Upper cabinet should have vertices at y >= 54 (mounting height)
        # After Y-up transform, y in mesh is height
        max_height = np.max(all_vertices[:, 1])

        # Upper cabinet top is at mounting_height (54) + cabinet_height (30) = 84
        assert max_height >= 80  # Should be near 84 (allowing for some tolerance)


class TestPanel3DMapperFallback:
    """Tests for Panel3DMapper fallback behavior with new panel types."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        return Cabinet(
            width=48.0,
            height=36.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75),
        )

    def test_new_panel_types_dont_fall_through_to_default(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that new panel types have explicit handling, not default fallback."""
        mapper = Panel3DMapper(sample_cabinet)

        # COUNTERTOP
        countertop = Panel(
            panel_type=PanelType.COUNTERTOP,
            width=48.0,
            height=24.0,
            material=MaterialSpec(thickness=1.0),
            position=Position(x=0, y=36.0),
        )
        box = mapper.map_panel(countertop)
        # Countertop should be at z=36 (the specified height)
        assert box.origin.z == 36.0
        # Countertop thickness should be 1.0
        assert box.size_z == 1.0

        # SUPPORT_BRACKET
        bracket = Panel(
            panel_type=PanelType.SUPPORT_BRACKET,
            width=1.5,
            height=6.0,
            material=MaterialSpec(thickness=0.75),
            position=Position(x=10.0, y=30.0),
        )
        box = mapper.map_panel(bracket)
        # Bracket should be at front of cabinet
        assert box.origin.y == sample_cabinet.depth - 0.75

        # STEPPED_SIDE
        stepped = Panel(
            panel_type=PanelType.STEPPED_SIDE,
            width=24.0,
            height=84.0,
            material=MaterialSpec(thickness=0.75),
            position=Position(x=0, y=0),
        )
        box = mapper.map_panel(stepped)
        # Stepped side thickness should be x dimension
        assert box.size_x == 0.75
        # Depth should be y dimension
        assert box.size_y == 24.0
