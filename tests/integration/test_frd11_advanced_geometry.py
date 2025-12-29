"""Integration tests for FRD-11: Advanced Room Geometry.

This module contains comprehensive integration tests for the FRD-11 features:
- Extended wall angles (-135 to 135 degrees)
- Sloped ceiling support
- Skylight void handling
- Outside corner treatments

These tests verify the complete integration between configuration parsing,
domain value objects, and the new geometry services.
"""

import pytest

from cabinets.application.config import (
    CabinetConfiguration,
    config_to_ceiling_slope,
    config_to_outside_corner,
    config_to_skylights,
)
from cabinets.domain.entities import Room, WallSegment
from cabinets.domain.services import (
    OutsideCornerService,
    SkylightVoidService,
    SlopedCeilingService,
)
from cabinets.domain.value_objects import (
    CeilingSlope,
    MaterialSpec,
    OutsideCornerConfig,
    PanelType,
    Skylight,
)


class TestExtendedWallAngles:
    """Integration tests for extended wall angle support."""

    def test_45_degree_wall_segment_valid(self):
        """WallSegment accepts 45-degree angles."""
        segment = WallSegment(length=48, height=84, angle=45)
        assert segment.angle == 45

    def test_negative_45_degree_wall_segment_valid(self):
        """WallSegment accepts -45-degree angles."""
        segment = WallSegment(length=48, height=84, angle=-45)
        assert segment.angle == -45

    def test_135_degree_wall_segment_valid(self):
        """WallSegment accepts 135-degree angles (outside corner)."""
        segment = WallSegment(length=48, height=84, angle=135)
        assert segment.angle == 135

    def test_negative_135_degree_wall_segment_valid(self):
        """WallSegment accepts -135-degree angles (outside corner)."""
        segment = WallSegment(length=48, height=84, angle=-135)
        assert segment.angle == -135

    def test_angle_out_of_range_raises(self):
        """WallSegment rejects angles outside -135 to 135 range."""
        with pytest.raises(ValueError, match="Angle must be between -135 and 135"):
            WallSegment(length=48, height=84, angle=140)

        with pytest.raises(ValueError, match="Angle must be between -135 and 135"):
            WallSegment(length=48, height=84, angle=-140)

    def test_room_with_angled_walls(self):
        """Room can be created with non-90-degree walls."""
        # A room with a 45-degree angled section
        walls = [
            WallSegment(length=48, height=84, angle=0),
            WallSegment(length=36, height=84, angle=45),
            WallSegment(length=48, height=84, angle=0),
            WallSegment(length=36, height=84, angle=45),
        ]
        room = Room(name="angled_room", walls=walls)
        assert len(room.walls) == 4
        assert room.walls[1].angle == 45
        assert room.walls[3].angle == 45

    def test_room_with_outside_corner_walls(self):
        """Room can be created with outside corner angles (>90 degrees)."""
        walls = [
            WallSegment(length=48, height=84, angle=0),
            WallSegment(length=36, height=84, angle=120),  # Outside corner
            WallSegment(length=48, height=84, angle=0),
        ]
        room = Room(name="outside_corner_room", walls=walls)
        assert len(room.walls) == 3
        assert room.walls[1].angle == 120


class TestSlopedCeilingIntegration:
    """Integration tests for sloped ceiling features."""

    def test_config_to_domain_conversion(self):
        """Configuration converts to domain CeilingSlope."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
                "room": {
                    "name": "attic",
                    "walls": [{"length": 48, "height": 84}],
                    "ceiling": {
                        "slope": {
                            "angle": 30,
                            "start_height": 96,
                            "direction": "left_to_right",
                            "min_height": 24,
                        }
                    },
                },
            }
        )

        slope = config_to_ceiling_slope(config)

        assert slope is not None
        assert slope.angle == 30
        assert slope.start_height == 96
        assert slope.direction == "left_to_right"
        assert slope.min_height == 24

    def test_config_without_slope_returns_none(self):
        """Configuration without ceiling slope returns None."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
            }
        )

        slope = config_to_ceiling_slope(config)
        assert slope is None

    def test_section_heights_under_slope(self):
        """Sections under sloped ceiling have varying heights."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        heights = service.calculate_section_heights([24, 24, 24], slope, 72)

        # Heights should decrease left to right
        assert heights[0] > heights[1] > heights[2]
        # All heights should be less than or equal to start height
        assert all(h <= 96 for h in heights)

    def test_section_heights_right_to_left(self):
        """Sections under right-to-left slope have increasing heights."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="right_to_left")

        heights = service.calculate_section_heights([24, 24, 24], slope, 72)

        # Heights should increase left to right (slope goes right to left)
        assert heights[0] < heights[1] < heights[2]

    def test_taper_spec_generation(self):
        """Taper specs are generated for sections under slope."""
        service = SlopedCeilingService()
        slope = CeilingSlope(angle=30, start_height=96, direction="left_to_right")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is not None
        assert taper.start_height > taper.end_height
        assert taper.direction == "left_to_right"

    def test_taper_spec_not_generated_for_flat(self):
        """No taper spec when section has uniform height."""
        service = SlopedCeilingService()
        # Very small angle results in negligible height difference
        slope = CeilingSlope(angle=0, start_height=96, direction="left_to_right")

        taper = service.generate_taper_spec(0, 24, slope, 72)

        assert taper is None

    def test_min_height_violations(self):
        """Min height violations are detected for short sections."""
        service = SlopedCeilingService()
        # Steep slope with high min_height requirement
        slope = CeilingSlope(
            angle=45, start_height=60, direction="left_to_right", min_height=40
        )

        violations = service.check_min_height_violations([30, 30, 30], slope, 90)

        # Later sections should violate min height
        assert len(violations) > 0
        # Violations contain (section_index, calculated_height, min_height)
        for idx, calc_height, min_height in violations:
            assert calc_height < min_height


class TestSkylightIntegration:
    """Integration tests for skylight void features."""

    def test_config_to_domain_conversion(self):
        """Configuration converts to domain Skylight list."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 72, "height": 84, "depth": 12},
                "room": {
                    "name": "skylight_room",
                    "walls": [{"length": 72, "height": 84}],
                    "ceiling": {
                        "skylights": [
                            {
                                "x_position": 36,
                                "width": 24,
                                "projection_depth": 8,
                                "projection_angle": 90,
                            }
                        ]
                    },
                },
            }
        )

        skylights = config_to_skylights(config)

        assert len(skylights) == 1
        assert skylights[0].x_position == 36
        assert skylights[0].width == 24
        assert skylights[0].projection_depth == 8
        assert skylights[0].projection_angle == 90

    def test_multiple_skylights_conversion(self):
        """Multiple skylights in config are all converted."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 120, "height": 84, "depth": 12},
                "room": {
                    "name": "multi_skylight_room",
                    "walls": [{"length": 120, "height": 84}],
                    "ceiling": {
                        "skylights": [
                            {"x_position": 30, "width": 20, "projection_depth": 6},
                            {"x_position": 80, "width": 20, "projection_depth": 6},
                        ]
                    },
                },
            }
        )

        skylights = config_to_skylights(config)

        assert len(skylights) == 2
        assert skylights[0].x_position == 30
        assert skylights[1].x_position == 80

    def test_config_without_skylights_returns_empty(self):
        """Configuration without skylights returns empty list."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 72, "height": 84, "depth": 12},
            }
        )

        skylights = config_to_skylights(config)
        assert skylights == []

    def test_notch_generation_for_skylight(self):
        """Notches are generated for sections under skylights."""
        service = SkylightVoidService()
        skylight = Skylight(x_position=30, width=20, projection_depth=8)

        notch = service.calculate_void_intersection(skylight, 24, 48, 12)

        assert notch is not None
        assert notch.edge == "top"
        assert notch.depth == 8
        assert notch.width > 0

    def test_no_notch_for_non_intersecting_skylight(self):
        """No notch generated when skylight doesn't intersect section."""
        service = SkylightVoidService()
        # Skylight at x=100, section at x=0-48
        skylight = Skylight(x_position=100, width=20, projection_depth=8)

        notch = service.calculate_void_intersection(skylight, 0, 48, 12)

        assert notch is None

    def test_multiple_notches_for_section(self):
        """Multiple skylights can create multiple notches for a section."""
        service = SkylightVoidService()
        skylights = [
            Skylight(x_position=10, width=10, projection_depth=6),
            Skylight(x_position=30, width=10, projection_depth=6),
        ]

        notches = service.calculate_all_intersections(skylights, 0, 48, 12)

        assert len(notches) == 2

    def test_skylight_void_exceeds_section(self):
        """Warning when skylight void exceeds section width."""
        service = SkylightVoidService()
        # Small section completely covered by large skylight
        skylight = Skylight(x_position=0, width=100, projection_depth=8)

        exceeds = service.check_void_exceeds_section(skylight, 20, 10, 12)

        assert exceeds is True

    def test_sections_with_voids_mapping(self):
        """Map section indices to their required notches."""
        service = SkylightVoidService()
        skylights = [Skylight(x_position=36, width=24, projection_depth=8)]
        # Three sections: 0-24, 24-48, 48-72
        section_specs = [(0, 24), (24, 24), (48, 24)]

        void_map = service.get_sections_with_voids(skylights, section_specs, 12)

        # Skylight at 36-60 should intersect section 1 (24-48) and section 2 (48-72)
        assert 1 in void_map
        assert 2 in void_map
        assert 0 not in void_map


class TestOutsideCornerIntegration:
    """Integration tests for outside corner handling."""

    def test_config_to_domain_conversion(self):
        """Configuration converts to domain OutsideCornerConfig."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
                "room": {
                    "name": "corner_room",
                    "walls": [
                        {"length": 48, "height": 84, "angle": 0},
                        {"length": 36, "height": 84, "angle": 120},
                    ],
                    "outside_corner": {
                        "treatment": "angled_face",
                        "face_angle": 45,
                    },
                },
            }
        )

        corner = config_to_outside_corner(config)

        assert corner is not None
        assert corner.treatment == "angled_face"
        assert corner.face_angle == 45

    def test_butted_filler_config_conversion(self):
        """Butted filler corner configuration is converted correctly."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
                "room": {
                    "name": "filler_room",
                    "walls": [{"length": 48, "height": 84}],
                    "outside_corner": {
                        "treatment": "butted_filler",
                        "filler_width": 4.5,
                    },
                },
            }
        )

        corner = config_to_outside_corner(config)

        assert corner is not None
        assert corner.treatment == "butted_filler"
        assert corner.filler_width == 4.5

    def test_config_without_outside_corner_returns_none(self):
        """Configuration without outside corner returns None."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
            }
        )

        corner = config_to_outside_corner(config)
        assert corner is None

    def test_angled_face_panel_generation(self):
        """Angled face panels are generated for outside corners."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="angled_face", face_angle=45)
        material = MaterialSpec(thickness=0.75)

        panels = service.generate_corner_panels(config, 84, 12, material)

        assert len(panels) == 1
        assert panels[0].panel_type == PanelType.DIAGONAL_FACE
        assert panels[0].height == 84
        assert panels[0].cut_metadata is not None
        assert "angle_cuts" in panels[0].cut_metadata

    def test_filler_panel_generation(self):
        """Filler panels are generated for butted_filler treatment."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="butted_filler", filler_width=4)
        material = MaterialSpec(thickness=0.75)

        panels = service.generate_corner_panels(config, 84, 12, material)

        assert len(panels) == 1
        assert panels[0].panel_type == PanelType.FILLER
        assert panels[0].width == 4
        assert panels[0].height == 84

    def test_is_outside_corner_detection(self):
        """Service correctly identifies outside corners by angle."""
        service = OutsideCornerService()

        # Standard 90-degree inside corner
        assert service.is_outside_corner(90) is False
        assert service.is_outside_corner(-90) is False

        # Outside corners (angle > 90)
        assert service.is_outside_corner(120) is True
        assert service.is_outside_corner(-120) is True
        assert service.is_outside_corner(135) is True

    def test_side_panel_angle_cut_generation(self):
        """Side panel angle cuts are generated for non-90-degree junctions."""
        service = OutsideCornerService()

        # Standard 90-degree junction needs no cut
        cut = service.calculate_side_panel_angle_cut(90, "right")
        assert cut is None

        # 120-degree junction needs angle cut
        cut = service.calculate_side_panel_angle_cut(120, "right")
        assert cut is not None
        assert cut.edge == "right"
        assert cut.bevel is True


class TestCombinedAdvancedGeometry:
    """Integration tests combining multiple FRD-11 features."""

    def test_full_config_with_all_features(self):
        """Complete configuration with slope, skylights, and outside corner."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 72, "height": 84, "depth": 12},
                "room": {
                    "name": "full_feature_room",
                    "walls": [
                        {"length": 72, "height": 84, "angle": 0},
                        {"length": 48, "height": 84, "angle": 120},
                    ],
                    "ceiling": {
                        "slope": {
                            "angle": 20,
                            "start_height": 96,
                            "direction": "left_to_right",
                        },
                        "skylights": [
                            {"x_position": 36, "width": 24, "projection_depth": 8}
                        ],
                    },
                    "outside_corner": {
                        "treatment": "angled_face",
                    },
                },
            }
        )

        slope = config_to_ceiling_slope(config)
        skylights = config_to_skylights(config)
        corner = config_to_outside_corner(config)

        assert slope is not None
        assert slope.angle == 20
        assert len(skylights) == 1
        assert corner is not None
        assert corner.treatment == "angled_face"

    def test_section_with_slope_and_skylight(self):
        """Section affected by both slope and skylight."""
        slope_service = SlopedCeilingService()
        skylight_service = SkylightVoidService()

        slope = CeilingSlope(angle=20, start_height=96, direction="left_to_right")
        skylight = Skylight(x_position=12, width=24, projection_depth=8)

        # Get height at section midpoint
        heights = slope_service.calculate_section_heights([24], slope, 72)

        # Get notch for skylight
        notch = skylight_service.calculate_void_intersection(skylight, 0, 24, 12)

        assert len(heights) == 1
        assert heights[0] < 96  # Height reduced by slope
        assert notch is not None  # Skylight intersects section
        assert notch.edge == "top"

    def test_schema_version_1_2_supported(self):
        """Schema version 1.2 is accepted for FRD-11 features."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.2",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
            }
        )

        assert config.schema_version == "1.2"

    def test_schema_version_1_1_supported(self):
        """Schema version 1.1 is still supported."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.1",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
            }
        )

        assert config.schema_version == "1.1"

    def test_schema_version_1_0_supported(self):
        """Schema version 1.0 is still supported."""
        config = CabinetConfiguration.model_validate(
            {
                "schema_version": "1.0",
                "cabinet": {"width": 48, "height": 84, "depth": 12},
            }
        )

        assert config.schema_version == "1.0"


class TestDomainValueObjects:
    """Tests for FRD-11 domain value objects."""

    def test_ceiling_slope_height_calculation(self):
        """CeilingSlope calculates height at position correctly."""
        slope = CeilingSlope(angle=30, start_height=100, direction="left_to_right")

        height_at_0 = slope.height_at_position(0)
        height_at_50 = slope.height_at_position(50)

        assert height_at_0 == 100
        assert height_at_50 < 100

    def test_ceiling_slope_validation(self):
        """CeilingSlope validates angle and height constraints."""
        # Valid slope
        slope = CeilingSlope(angle=30, start_height=100, direction="left_to_right")
        assert slope.angle == 30

        # Invalid angle (too steep)
        with pytest.raises(ValueError, match="Slope angle must be between"):
            CeilingSlope(angle=70, start_height=100, direction="left_to_right")

        # Invalid start height
        with pytest.raises(ValueError, match="Start height must be positive"):
            CeilingSlope(angle=30, start_height=-10, direction="left_to_right")

    def test_skylight_void_calculation(self):
        """Skylight calculates void dimensions at cabinet depth."""
        # Vertical projection (90 degrees)
        skylight = Skylight(
            x_position=20, width=24, projection_depth=8, projection_angle=90
        )
        void_x, void_width = skylight.void_at_depth(12)

        assert void_x == 20
        assert void_width == 24

        # Angled projection should expand void
        skylight_angled = Skylight(
            x_position=20, width=24, projection_depth=8, projection_angle=75
        )
        void_x_angled, void_width_angled = skylight_angled.void_at_depth(12)

        assert void_width_angled > 24  # Void expands with angle

    def test_skylight_validation(self):
        """Skylight validates dimension constraints."""
        # Valid skylight
        skylight = Skylight(x_position=20, width=24, projection_depth=8)
        assert skylight.width == 24

        # Invalid width
        with pytest.raises(ValueError, match="Skylight width must be positive"):
            Skylight(x_position=20, width=-1, projection_depth=8)

        # Invalid projection depth
        with pytest.raises(ValueError, match="Projection depth must be positive"):
            Skylight(x_position=20, width=24, projection_depth=0)

    def test_outside_corner_config_validation(self):
        """OutsideCornerConfig validates angle and width constraints."""
        # Valid config
        config = OutsideCornerConfig(treatment="angled_face", face_angle=45)
        assert config.face_angle == 45

        # Invalid face angle
        with pytest.raises(ValueError, match="Face angle must be between"):
            OutsideCornerConfig(treatment="angled_face", face_angle=90)

        # Invalid filler width
        with pytest.raises(ValueError, match="Filler width must be positive"):
            OutsideCornerConfig(treatment="butted_filler", filler_width=-1)
