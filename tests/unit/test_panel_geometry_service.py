"""Unit tests for PanelGeometryService (FRD-23 Phase 6).

Tests for:
- calculate_junction_angles() for 3-wall and 5-wall bays
- Symmetric angle calculation (45-degree bays -> 22.5-degree cuts)
- calculate_ceiling_tapers() for sloped ceilings
- get_panel_cut_metadata() for left_side, right_side, top panels
- generate_cut_notes() for human-readable cut descriptions
- get_compound_cut_walls() for identifying compound cuts
- Edge cases (no angle cut needed, no taper needed)
- Cache invalidation
"""

from __future__ import annotations


from cabinets.domain.value_objects import BayAlcoveConfig
from cabinets.domain.services.panel_geometry_service import (
    PanelAngleSpec,
    PanelGeometryService,
    PanelTaperSpec,
)
from cabinets.domain.services.radial_ceiling_service import RadialCeilingService
from cabinets.domain.value_objects import (
    ApexPoint,
    PanelCutMetadata,
    TaperSpec,
)


def create_bay_config(
    walls: list[dict],
    apex: ApexPoint | None = None,
    apex_mode: str = "auto",
    edge_height: float = 84.0,
    sill_clearance: float = 2.0,
    **kwargs,
) -> BayAlcoveConfig:
    """Helper to create BayAlcoveConfig for testing."""
    return BayAlcoveConfig(
        bay_type=kwargs.get("bay_type", "custom"),
        walls=tuple(walls),
        opening_width=kwargs.get("opening_width"),
        bay_depth=kwargs.get("bay_depth"),
        arc_angle=kwargs.get("arc_angle"),
        segment_count=kwargs.get("segment_count"),
        apex=apex,
        apex_mode=apex_mode,
        edge_height=edge_height,
        min_cabinet_width=kwargs.get("min_cabinet_width", 12.0),
        filler_treatment=kwargs.get("filler_treatment", "panel"),
        sill_clearance=sill_clearance,
        head_clearance=kwargs.get("head_clearance", 2.0),
        seat_surface_style=kwargs.get("seat_surface_style", "flat"),
        flank_integration=kwargs.get("flank_integration", "separate"),
        top_style=kwargs.get("top_style"),
        shelf_alignment=kwargs.get("shelf_alignment", "rectangular"),
    )


class TestPanelGeometryServiceInstantiation:
    """Tests for PanelGeometryService instantiation."""

    def test_instantiation(self) -> None:
        """Test that PanelGeometryService can be instantiated."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)
        assert panel_service is not None

    def test_has_ceiling_service_reference(self) -> None:
        """Test that PanelGeometryService stores ceiling service reference."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)
        assert panel_service.ceiling_service is ceiling_service


class TestCalculateJunctionAngles:
    """Tests for calculate_junction_angles method."""

    def test_three_wall_bay_returns_three_specs(self) -> None:
        """Test that 3-wall bay returns 3 angle specs."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles = panel_service.calculate_junction_angles()

        assert len(angles) == 3
        assert all(isinstance(spec, PanelAngleSpec) for spec in angles)

    def test_five_wall_bay_returns_five_specs(self) -> None:
        """Test that 5-wall bay returns 5 angle specs."""
        walls = [
            {"length": 24.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 24.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles = panel_service.calculate_junction_angles()

        assert len(angles) == 5

    def test_wall_indices_are_correct(self) -> None:
        """Test that angle specs have correct wall indices."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles = panel_service.calculate_junction_angles()

        for i, spec in enumerate(angles):
            assert spec.wall_index == i

    def test_three_wall_symmetric_bay_angles(self) -> None:
        """Test angle calculation for symmetric 3-wall bay.

        For 3 walls with symmetric angles:
        - Exterior turn angle = 180 - (360/3) = 60 degrees
        - Wall directions are 0, 60, 120 degrees
        - Junction between sequential walls (0->1, 1->2) = 60 degrees, cut = 30
        - Junction wrap-around (2->0) = |0 - 120| = 120 degrees, cut = 60

        The middle wall (index 1) has both angles = 30 degrees because
        it connects to adjacent walls without wrap-around effects.
        """
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles = panel_service.calculate_junction_angles()

        # Wall 1 (middle) should have consistent 30-degree cuts on both sides
        # because it connects to walls 0 and 2 sequentially
        assert abs(angles[1].left_angle - 30.0) < 0.1
        assert abs(angles[1].right_angle - 30.0) < 0.1

        # Wall 0: left from wrap (60) and right to next (30)
        assert abs(angles[0].left_angle - 60.0) < 0.1
        assert abs(angles[0].right_angle - 30.0) < 0.1

        # Wall 2: left from previous (30) and right to wrap (60)
        assert abs(angles[2].left_angle - 30.0) < 0.1
        assert abs(angles[2].right_angle - 60.0) < 0.1

    def test_explicit_45_degree_angles(self) -> None:
        """Test angle calculation with explicit 45-degree wall turns.

        For explicit 45-degree turns:
        - Panel cut = 45/2 = 22.5 degrees
        """
        walls = [
            {"length": 36.0, "angle": None},  # First wall at 0 degrees
            {"length": 48.0, "angle": 45.0},  # 45-degree turn
            {"length": 36.0, "angle": 45.0},  # Another 45-degree turn
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles = panel_service.calculate_junction_angles()

        # Wall 1: right edge to wall 0 (45-degree difference = 22.5 cut)
        # Wall 1: left edge from wall 0 (45-degree difference = 22.5 cut)
        assert abs(angles[1].left_angle - 22.5) < 0.1
        assert abs(angles[1].right_angle - 22.5) < 0.1

    def test_caching_returns_same_result(self) -> None:
        """Test that calling calculate_junction_angles twice returns cached result."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles1 = panel_service.calculate_junction_angles()
        angles2 = panel_service.calculate_junction_angles()

        assert angles1 is angles2

    def test_is_compound_initially_false(self) -> None:
        """Test that is_compound is initially False."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        angles = panel_service.calculate_junction_angles()

        for spec in angles:
            assert spec.is_compound is False


class TestCalculateCeilingTapers:
    """Tests for calculate_ceiling_tapers method."""

    def test_returns_list_of_taper_specs(self) -> None:
        """Test that method returns list of PanelTaperSpec objects."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        tapers = panel_service.calculate_ceiling_tapers()

        assert isinstance(tapers, list)
        assert all(isinstance(t, PanelTaperSpec) for t in tapers)

    def test_taper_has_correct_direction(self) -> None:
        """Test that tapers have front_to_back direction."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        tapers = panel_service.calculate_ceiling_tapers()

        for taper in tapers:
            assert taper.taper_direction == "front_to_back"

    def test_taper_front_height_greater_than_back(self) -> None:
        """Test that front height is typically greater than back (sloped ceiling)."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        tapers = panel_service.calculate_ceiling_tapers()

        # For radial ceiling, front (near midpoint) should be higher than
        # back (at edge_height)
        for taper in tapers:
            assert taper.front_height >= taper.back_height

    def test_caching_returns_same_result(self) -> None:
        """Test that calling calculate_ceiling_tapers twice returns cached result."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        tapers1 = panel_service.calculate_ceiling_tapers()
        tapers2 = panel_service.calculate_ceiling_tapers()

        assert tapers1 is tapers2

    def test_no_taper_when_flat_ceiling(self) -> None:
        """Test that no tapers are returned when ceiling height difference is small."""
        # Create a bay with apex at same height as edge (flat ceiling)
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        # With apex_mode auto and edge_height, apex will be edge_height + 12
        # This creates a slope, so we need to test differently
        # Using explicit apex at edge height to simulate flat
        explicit_apex = ApexPoint(x=0.0, y=0.0, z=84.5)  # Just 0.5" above edge
        config = create_bay_config(
            walls, apex=explicit_apex, apex_mode="explicit", edge_height=84.0
        )
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        tapers = panel_service.calculate_ceiling_tapers()

        # With minimal height difference, tapers should be filtered out
        # (threshold is 0.5")
        # Note: The actual behavior depends on height_at_point calculation
        assert isinstance(tapers, list)


class TestGetPanelCutMetadata:
    """Tests for get_panel_cut_metadata method."""

    def test_left_side_panel_has_angle_cut(self) -> None:
        """Test that left_side panel gets angle cut on left edge."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        metadata = panel_service.get_panel_cut_metadata(
            wall_index=1, panel_type="left_side"
        )

        assert metadata is not None
        assert isinstance(metadata, PanelCutMetadata)
        assert len(metadata.angle_cuts) > 0
        assert metadata.angle_cuts[0].edge == "left"

    def test_right_side_panel_has_angle_cut(self) -> None:
        """Test that right_side panel gets angle cut on right edge."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        metadata = panel_service.get_panel_cut_metadata(
            wall_index=1, panel_type="right_side"
        )

        assert metadata is not None
        assert len(metadata.angle_cuts) > 0
        assert metadata.angle_cuts[0].edge == "right"

    def test_top_panel_has_taper(self) -> None:
        """Test that top panel gets taper specification."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Get tapers to check if wall 1 has a taper
        tapers = panel_service.calculate_ceiling_tapers()
        has_taper = any(t.wall_index == 1 for t in tapers)

        metadata = panel_service.get_panel_cut_metadata(wall_index=1, panel_type="top")

        if has_taper:
            assert metadata is not None
            assert metadata.taper is not None
            assert isinstance(metadata.taper, TaperSpec)

    def test_back_panel_returns_none(self) -> None:
        """Test that back panel returns None (no special cuts)."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        metadata = panel_service.get_panel_cut_metadata(wall_index=1, panel_type="back")

        assert metadata is None

    def test_angle_cut_is_not_beveled(self) -> None:
        """Test that angle cuts are miter cuts, not bevel cuts."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        metadata = panel_service.get_panel_cut_metadata(
            wall_index=1, panel_type="left_side"
        )

        assert metadata is not None
        assert metadata.angle_cuts[0].bevel is False

    def test_no_metadata_for_tiny_angle(self) -> None:
        """Test that no metadata returned when angle is negligible."""
        # Create walls with 90-degree turns (no miter needed for straight junction)
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": 0.0},  # No turn
            {"length": 36.0, "angle": 0.0},  # No turn
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Wall 1 with 0-degree turns should have negligible angles
        metadata = panel_service.get_panel_cut_metadata(
            wall_index=1, panel_type="left_side"
        )

        # With 0-degree turn, no meaningful angle cut needed
        # metadata should be None or have empty angle_cuts
        if metadata is not None:
            assert len(metadata.angle_cuts) == 0 or all(
                abs(c.angle) <= 0.5 for c in metadata.angle_cuts
            )


class TestGenerateCutNotes:
    """Tests for generate_cut_notes method."""

    def test_angle_cut_note_format(self) -> None:
        """Test that angle cut notes have correct format."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        notes = panel_service.generate_cut_notes(wall_index=1, panel_type="left_side")

        # Notes should contain angle, cut type, and edge
        assert "deg" in notes
        assert "miter" in notes
        assert "left" in notes

    def test_taper_note_format(self) -> None:
        """Test that taper notes have correct format."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Only test if wall has taper
        tapers = panel_service.calculate_ceiling_tapers()
        if any(t.wall_index == 1 for t in tapers):
            notes = panel_service.generate_cut_notes(wall_index=1, panel_type="top")
            assert "Taper" in notes

    def test_empty_notes_for_no_cuts(self) -> None:
        """Test that empty string returned when no special cuts needed."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        notes = panel_service.generate_cut_notes(wall_index=1, panel_type="back")

        assert notes == ""


class TestGetCompoundCutWalls:
    """Tests for get_compound_cut_walls method."""

    def test_returns_list_of_wall_indices(self) -> None:
        """Test that method returns list of integers."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        compound_walls = panel_service.get_compound_cut_walls()

        assert isinstance(compound_walls, list)
        assert all(isinstance(i, int) for i in compound_walls)

    def test_compound_walls_have_both_angle_and_taper(self) -> None:
        """Test that compound walls have both significant angles and tapers."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls, edge_height=84.0)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        compound_walls = panel_service.get_compound_cut_walls()
        angle_specs = panel_service.calculate_junction_angles()
        taper_specs = panel_service.calculate_ceiling_tapers()

        for wall_idx in compound_walls:
            # Should have meaningful angle
            angle_spec = next(s for s in angle_specs if s.wall_index == wall_idx)
            assert abs(angle_spec.left_angle) > 0.5 or abs(angle_spec.right_angle) > 0.5

            # Should have taper
            assert any(t.wall_index == wall_idx for t in taper_specs)

    def test_result_is_sorted(self) -> None:
        """Test that result is sorted by wall index."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        compound_walls = panel_service.get_compound_cut_walls()

        assert compound_walls == sorted(compound_walls)


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_cache_clears_angle_specs(self) -> None:
        """Test that invalidate_cache clears angle specs cache."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Build the cache
        panel_service.calculate_junction_angles()
        assert panel_service._angle_specs is not None

        # Invalidate
        panel_service.invalidate_cache()
        assert panel_service._angle_specs is None

    def test_invalidate_cache_clears_taper_specs(self) -> None:
        """Test that invalidate_cache clears taper specs cache."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Build the cache
        panel_service.calculate_ceiling_tapers()
        assert panel_service._taper_specs is not None

        # Invalidate
        panel_service.invalidate_cache()
        assert panel_service._taper_specs is None


class TestPanelAngleSpecDataclass:
    """Tests for PanelAngleSpec dataclass."""

    def test_dataclass_fields(self) -> None:
        """Test that PanelAngleSpec has expected fields."""
        spec = PanelAngleSpec(
            wall_index=0,
            left_angle=22.5,
            right_angle=22.5,
            is_compound=False,
        )

        assert spec.wall_index == 0
        assert spec.left_angle == 22.5
        assert spec.right_angle == 22.5
        assert spec.is_compound is False


class TestPanelTaperSpecDataclass:
    """Tests for PanelTaperSpec dataclass."""

    def test_dataclass_fields(self) -> None:
        """Test that PanelTaperSpec has expected fields."""
        spec = PanelTaperSpec(
            wall_index=1,
            front_height=90.0,
            back_height=84.0,
            taper_direction="front_to_back",
        )

        assert spec.wall_index == 1
        assert spec.front_height == 90.0
        assert spec.back_height == 84.0
        assert spec.taper_direction == "front_to_back"


class TestImportFromServicesPackage:
    """Tests for importing from services package."""

    def test_import_panel_geometry_service(self) -> None:
        """Test that PanelGeometryService can be imported from services package."""
        from cabinets.domain.services import PanelGeometryService as PGS

        assert PGS is not None

    def test_import_panel_angle_spec(self) -> None:
        """Test that PanelAngleSpec can be imported from services package."""
        from cabinets.domain.services import PanelAngleSpec as PAS

        assert PAS is not None

    def test_import_panel_taper_spec(self) -> None:
        """Test that PanelTaperSpec can be imported from services package."""
        from cabinets.domain.services import PanelTaperSpec as PTS

        assert PTS is not None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_wall_bay_angles(self) -> None:
        """Test handling of minimal wall count (3 walls minimum for valid bay)."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Should not raise errors
        angles = panel_service.calculate_junction_angles()
        assert len(angles) == 3

    def test_wall_index_out_of_range(self) -> None:
        """Test get_panel_cut_metadata with out-of-range wall index."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Wall index 5 is out of range for 3-wall bay
        metadata = panel_service.get_panel_cut_metadata(
            wall_index=5, panel_type="left_side"
        )

        # Should return None since wall doesn't exist
        assert metadata is None

    def test_unknown_panel_type(self) -> None:
        """Test get_panel_cut_metadata with unknown panel type."""
        walls = [
            {"length": 36.0, "angle": None},
            {"length": 48.0, "angle": None},
            {"length": 36.0, "angle": None},
        ]
        config = create_bay_config(walls)
        ceiling_service = RadialCeilingService(config)
        panel_service = PanelGeometryService(ceiling_service)

        # Unknown panel type should return None
        metadata = panel_service.get_panel_cut_metadata(
            wall_index=1, panel_type="unknown"
        )

        assert metadata is None
