"""Unit tests for bay alcove configuration schema (FRD-23 Phase 2).

These tests verify the Pydantic validation for bay window alcove configuration
models including BayWindowConfig, BayWallSegmentConfig, ApexPointConfig,
BayAlcoveConfigSchema, and the RoomConfig bay_alcove integration.
"""

import pytest
from pydantic import ValidationError

from cabinets.application.config.schemas import (
    ApexPointConfig,
    BayAlcoveConfigSchema,
    BayWallSegmentConfig,
    BayWindowConfig,
    RoomConfig,
    WallSegmentConfig,
)
from cabinets.application.config import (
    BayAlcoveConfig,
    config_to_bay_alcove,
)
from cabinets.application.config.schemas import CabinetConfiguration, CabinetConfig


class TestBayWindowConfig:
    """Tests for BayWindowConfig validation."""

    def test_valid_bay_window_config(self):
        """Test valid bay window configuration."""
        config = BayWindowConfig(
            sill_height=30.0,
            head_height=72.0,
            width=36.0,
            projection_depth=2.0,
        )
        assert config.sill_height == 30.0
        assert config.head_height == 72.0
        assert config.width == 36.0
        assert config.projection_depth == 2.0

    def test_bay_window_full_width(self):
        """Test bay window with 'full' width."""
        config = BayWindowConfig(
            sill_height=30.0,
            head_height=72.0,
            width="full",
        )
        assert config.width == "full"

    def test_bay_window_default_values(self):
        """Test bay window default values."""
        config = BayWindowConfig(
            sill_height=30.0,
            head_height=72.0,
        )
        assert config.width == "full"
        assert config.projection_depth == 0.0

    def test_bay_window_invalid_head_height_below_sill(self):
        """Test that head_height must be greater than sill_height."""
        with pytest.raises(ValidationError) as exc_info:
            BayWindowConfig(
                sill_height=72.0,
                head_height=30.0,  # Less than sill_height
            )
        assert "head_height must be greater than sill_height" in str(exc_info.value)

    def test_bay_window_invalid_head_height_equal_sill(self):
        """Test that head_height cannot equal sill_height."""
        with pytest.raises(ValidationError) as exc_info:
            BayWindowConfig(
                sill_height=50.0,
                head_height=50.0,  # Equal to sill_height
            )
        assert "head_height must be greater than sill_height" in str(exc_info.value)

    def test_bay_window_invalid_negative_sill_height(self):
        """Test that sill_height must be non-negative."""
        with pytest.raises(ValidationError):
            BayWindowConfig(
                sill_height=-5.0,
                head_height=72.0,
            )

    def test_bay_window_invalid_zero_head_height(self):
        """Test that head_height must be positive."""
        with pytest.raises(ValidationError):
            BayWindowConfig(
                sill_height=0.0,
                head_height=0.0,
            )

    def test_bay_window_invalid_negative_projection(self):
        """Test that projection_depth must be non-negative."""
        with pytest.raises(ValidationError):
            BayWindowConfig(
                sill_height=30.0,
                head_height=72.0,
                projection_depth=-1.0,
            )

    def test_bay_window_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            BayWindowConfig(
                sill_height=30.0,
                head_height=72.0,
                extra_field="not allowed",
            )


class TestBayWallSegmentConfig:
    """Tests for BayWallSegmentConfig validation."""

    def test_valid_wall_segment_minimal(self):
        """Test minimal valid wall segment configuration."""
        config = BayWallSegmentConfig(length=24.0)
        assert config.length == 24.0
        assert config.angle is None
        assert config.window is None
        assert config.name is None
        assert config.zone_type == "auto"
        assert config.shelf_alignment is None
        assert config.top_style is None

    def test_valid_wall_segment_full(self):
        """Test fully specified wall segment configuration."""
        window = BayWindowConfig(sill_height=30.0, head_height=72.0)
        config = BayWallSegmentConfig(
            length=48.0,
            angle=45.0,
            window=window,
            name="center_wall",
            zone_type="cabinet",
            shelf_alignment="rectangular",
            top_style="flat",
        )
        assert config.length == 48.0
        assert config.angle == 45.0
        assert config.window is not None
        assert config.name == "center_wall"
        assert config.zone_type == "cabinet"
        assert config.shelf_alignment == "rectangular"
        assert config.top_style == "flat"

    def test_wall_segment_invalid_zero_length(self):
        """Test that length must be positive."""
        with pytest.raises(ValidationError):
            BayWallSegmentConfig(length=0.0)

    def test_wall_segment_invalid_negative_length(self):
        """Test that length must be positive."""
        with pytest.raises(ValidationError):
            BayWallSegmentConfig(length=-10.0)

    def test_wall_segment_valid_angle_range(self):
        """Test valid angle values at boundaries."""
        # Test minimum angle
        config_min = BayWallSegmentConfig(length=24.0, angle=-180.0)
        assert config_min.angle == -180.0

        # Test maximum angle
        config_max = BayWallSegmentConfig(length=24.0, angle=180.0)
        assert config_max.angle == 180.0

    def test_wall_segment_invalid_angle_out_of_range(self):
        """Test that angle must be within -180 to 180."""
        with pytest.raises(ValidationError):
            BayWallSegmentConfig(length=24.0, angle=181.0)

        with pytest.raises(ValidationError):
            BayWallSegmentConfig(length=24.0, angle=-181.0)

    def test_wall_segment_zone_types(self):
        """Test valid zone type values."""
        for zone_type in ["cabinet", "filler", "auto"]:
            config = BayWallSegmentConfig(length=24.0, zone_type=zone_type)
            assert config.zone_type == zone_type

    def test_wall_segment_invalid_zone_type(self):
        """Test that invalid zone type is rejected."""
        with pytest.raises(ValidationError):
            BayWallSegmentConfig(length=24.0, zone_type="invalid")

    def test_wall_segment_shelf_alignment_options(self):
        """Test valid shelf alignment values."""
        for alignment in ["rectangular", "wall_parallel", None]:
            config = BayWallSegmentConfig(length=24.0, shelf_alignment=alignment)
            assert config.shelf_alignment == alignment

    def test_wall_segment_top_style_options(self):
        """Test valid top style values."""
        for style in ["flat", "ceiling_follow", "angled", None]:
            config = BayWallSegmentConfig(length=24.0, top_style=style)
            assert config.top_style == style


class TestApexPointConfig:
    """Tests for ApexPointConfig validation."""

    def test_valid_apex_point_at_center(self):
        """Test valid apex point at center."""
        config = ApexPointConfig(x=0.0, y=0.0, z=96.0)
        assert config.x == 0.0
        assert config.y == 0.0
        assert config.z == 96.0

    def test_valid_apex_point_offset(self):
        """Test valid apex point with offset."""
        config = ApexPointConfig(x=12.0, y=-6.0, z=108.0)
        assert config.x == 12.0
        assert config.y == -6.0
        assert config.z == 108.0

    def test_apex_point_default_xy(self):
        """Test default x and y values."""
        config = ApexPointConfig(z=96.0)
        assert config.x == 0.0
        assert config.y == 0.0

    def test_apex_point_invalid_zero_z(self):
        """Test that z must be positive."""
        with pytest.raises(ValidationError):
            ApexPointConfig(z=0.0)

    def test_apex_point_invalid_negative_z(self):
        """Test that z must be positive."""
        with pytest.raises(ValidationError):
            ApexPointConfig(z=-10.0)


class TestBayAlcoveConfigSchema:
    """Tests for BayAlcoveConfigSchema validation."""

    def _create_minimal_walls(self, count: int = 3) -> list[BayWallSegmentConfig]:
        """Helper to create minimal wall configurations."""
        return [BayWallSegmentConfig(length=24.0) for _ in range(count)]

    def test_valid_minimal_config(self):
        """Test minimal valid bay alcove configuration."""
        config = BayAlcoveConfigSchema(walls=self._create_minimal_walls(3))
        assert config.bay_type == "custom"
        assert len(config.walls) == 3
        assert config.apex == "auto"
        assert config.edge_height == 84.0

    def test_valid_three_wall_bay(self):
        """Test valid three-wall bay configuration."""
        walls = [
            BayWallSegmentConfig(length=24.0, angle=45.0),
            BayWallSegmentConfig(length=48.0, angle=0.0),
            BayWallSegmentConfig(length=24.0, angle=-45.0),
        ]
        config = BayAlcoveConfigSchema(
            bay_type="three_wall",
            walls=walls,
            opening_width=96.0,
            bay_depth=24.0,
        )
        assert config.bay_type == "three_wall"
        assert config.opening_width == 96.0
        assert config.bay_depth == 24.0

    def test_valid_five_wall_bay(self):
        """Test valid five-wall bay configuration."""
        walls = self._create_minimal_walls(5)
        config = BayAlcoveConfigSchema(
            bay_type="five_wall",
            walls=walls,
        )
        assert config.bay_type == "five_wall"
        assert len(config.walls) == 5

    def test_valid_bow_bay(self):
        """Test valid bow bay configuration with required arc settings."""
        walls = self._create_minimal_walls(5)
        config = BayAlcoveConfigSchema(
            bay_type="bow",
            walls=walls,
            arc_angle=120.0,
            segment_count=5,
        )
        assert config.bay_type == "bow"
        assert config.arc_angle == 120.0
        assert config.segment_count == 5

    def test_bow_bay_missing_arc_angle(self):
        """Test that bow bay requires arc_angle."""
        walls = self._create_minimal_walls(5)
        with pytest.raises(ValidationError) as exc_info:
            BayAlcoveConfigSchema(
                bay_type="bow",
                walls=walls,
                segment_count=5,
            )
        assert "arc_angle required for bow bay_type" in str(exc_info.value)

    def test_bow_bay_missing_segment_count(self):
        """Test that bow bay requires segment_count."""
        walls = self._create_minimal_walls(5)
        with pytest.raises(ValidationError) as exc_info:
            BayAlcoveConfigSchema(
                bay_type="bow",
                walls=walls,
                arc_angle=120.0,
            )
        assert "segment_count required for bow bay_type" in str(exc_info.value)

    def test_non_bow_bay_without_arc_settings(self):
        """Test that non-bow bays don't require arc settings."""
        walls = self._create_minimal_walls(3)
        # Should not raise
        config = BayAlcoveConfigSchema(
            bay_type="three_wall",
            walls=walls,
        )
        assert config.arc_angle is None
        assert config.segment_count is None

    def test_valid_explicit_apex(self):
        """Test valid explicit apex configuration."""
        apex = ApexPointConfig(x=0.0, y=0.0, z=108.0)
        config = BayAlcoveConfigSchema(
            walls=self._create_minimal_walls(3),
            apex=apex,
        )
        assert config.apex == apex
        assert config.apex.z == 108.0

    def test_apex_auto(self):
        """Test apex set to 'auto'."""
        config = BayAlcoveConfigSchema(
            walls=self._create_minimal_walls(3),
            apex="auto",
        )
        assert config.apex == "auto"

    def test_apex_none(self):
        """Test apex set to None (flat ceiling)."""
        config = BayAlcoveConfigSchema(
            walls=self._create_minimal_walls(3),
            apex=None,
        )
        assert config.apex is None

    def test_min_walls_constraint(self):
        """Test that at least 3 walls are required."""
        walls = self._create_minimal_walls(2)
        with pytest.raises(ValidationError):
            BayAlcoveConfigSchema(walls=walls)

    def test_max_walls_constraint(self):
        """Test that at most 12 walls are allowed."""
        walls = self._create_minimal_walls(13)
        with pytest.raises(ValidationError):
            BayAlcoveConfigSchema(walls=walls)

    def test_walls_at_boundaries(self):
        """Test walls count at minimum and maximum."""
        # Minimum
        config_min = BayAlcoveConfigSchema(walls=self._create_minimal_walls(3))
        assert len(config_min.walls) == 3

        # Maximum
        config_max = BayAlcoveConfigSchema(walls=self._create_minimal_walls(12))
        assert len(config_max.walls) == 12

    def test_min_cabinet_width_range(self):
        """Test min_cabinet_width constraints."""
        walls = self._create_minimal_walls(3)

        # Valid range
        config = BayAlcoveConfigSchema(walls=walls, min_cabinet_width=6.0)
        assert config.min_cabinet_width == 6.0

        # Minimum boundary
        config_min = BayAlcoveConfigSchema(walls=walls, min_cabinet_width=3.0)
        assert config_min.min_cabinet_width == 3.0

        # Maximum boundary
        config_max = BayAlcoveConfigSchema(walls=walls, min_cabinet_width=24.0)
        assert config_max.min_cabinet_width == 24.0

    def test_min_cabinet_width_out_of_range(self):
        """Test min_cabinet_width validation failure."""
        walls = self._create_minimal_walls(3)

        with pytest.raises(ValidationError):
            BayAlcoveConfigSchema(walls=walls, min_cabinet_width=2.0)

        with pytest.raises(ValidationError):
            BayAlcoveConfigSchema(walls=walls, min_cabinet_width=25.0)

    def test_filler_treatment_options(self):
        """Test valid filler treatment values."""
        walls = self._create_minimal_walls(3)
        for treatment in ["panel", "trim", "none"]:
            config = BayAlcoveConfigSchema(walls=walls, filler_treatment=treatment)
            assert config.filler_treatment == treatment

    def test_seat_surface_style_options(self):
        """Test valid seat surface style values."""
        walls = self._create_minimal_walls(3)
        for style in ["continuous", "per_section", "bridged"]:
            config = BayAlcoveConfigSchema(walls=walls, seat_surface_style=style)
            assert config.seat_surface_style == style

    def test_flank_integration_options(self):
        """Test valid flank integration values."""
        walls = self._create_minimal_walls(3)
        for integration in ["separate", "shared_panel", "butted"]:
            config = BayAlcoveConfigSchema(walls=walls, flank_integration=integration)
            assert config.flank_integration == integration

    def test_shelf_alignment_options(self):
        """Test valid shelf alignment values."""
        walls = self._create_minimal_walls(3)
        for alignment in ["rectangular", "wall_parallel", "mixed"]:
            config = BayAlcoveConfigSchema(walls=walls, shelf_alignment=alignment)
            assert config.shelf_alignment == alignment

    def test_arc_angle_range(self):
        """Test arc_angle validation range."""
        walls = self._create_minimal_walls(5)

        # Valid at boundaries for bow type
        config_min = BayAlcoveConfigSchema(
            bay_type="bow", walls=walls, arc_angle=30.0, segment_count=5
        )
        assert config_min.arc_angle == 30.0

        config_max = BayAlcoveConfigSchema(
            bay_type="bow", walls=walls, arc_angle=180.0, segment_count=5
        )
        assert config_max.arc_angle == 180.0

    def test_segment_count_range(self):
        """Test segment_count validation range."""
        walls = self._create_minimal_walls(5)

        # Valid at boundaries
        config_min = BayAlcoveConfigSchema(
            bay_type="bow", walls=walls, arc_angle=90.0, segment_count=3
        )
        assert config_min.segment_count == 3

        config_max = BayAlcoveConfigSchema(
            bay_type="bow", walls=walls, arc_angle=90.0, segment_count=12
        )
        assert config_max.segment_count == 12

    def test_default_values(self):
        """Test all default values are set correctly."""
        walls = self._create_minimal_walls(3)
        config = BayAlcoveConfigSchema(walls=walls)

        assert config.bay_type == "custom"
        assert config.opening_width is None
        assert config.bay_depth is None
        assert config.arc_angle is None
        assert config.segment_count is None
        assert config.apex == "auto"
        assert config.edge_height == 84.0
        assert config.min_cabinet_width == 6.0
        assert config.filler_treatment == "panel"
        assert config.sill_clearance == 1.0
        assert config.head_clearance == 2.0
        assert config.seat_surface_style == "per_section"
        assert config.flank_integration == "separate"
        assert config.top_style is None
        assert config.shelf_alignment == "rectangular"


class TestRoomConfigWithBayAlcove:
    """Tests for RoomConfig integration with bay_alcove."""

    def _create_room_walls(self) -> list[WallSegmentConfig]:
        """Helper to create room walls."""
        return [
            WallSegmentConfig(length=120.0, height=96.0, angle=0.0),
            WallSegmentConfig(length=96.0, height=96.0, angle=90.0),
        ]

    def _create_bay_walls(self) -> list[BayWallSegmentConfig]:
        """Helper to create bay walls."""
        return [
            BayWallSegmentConfig(length=24.0, angle=45.0),
            BayWallSegmentConfig(length=48.0, angle=0.0),
            BayWallSegmentConfig(length=24.0, angle=-45.0),
        ]

    def test_room_without_bay_alcove(self):
        """Test room configuration without bay alcove."""
        config = RoomConfig(
            name="living_room",
            walls=self._create_room_walls(),
        )
        assert config.bay_alcove is None

    def test_room_with_bay_alcove(self):
        """Test room configuration with bay alcove."""
        bay_config = BayAlcoveConfigSchema(
            bay_type="three_wall",
            walls=self._create_bay_walls(),
        )
        config = RoomConfig(
            name="living_room",
            walls=self._create_room_walls(),
            bay_alcove=bay_config,
        )
        assert config.bay_alcove is not None
        assert config.bay_alcove.bay_type == "three_wall"
        assert len(config.bay_alcove.walls) == 3

    def test_room_with_bay_alcove_and_other_features(self):
        """Test room with bay alcove alongside other features."""
        bay_config = BayAlcoveConfigSchema(walls=self._create_bay_walls())
        config = RoomConfig(
            name="living_room",
            walls=self._create_room_walls(),
            is_closed=True,
            bay_alcove=bay_config,
        )
        assert config.bay_alcove is not None
        assert config.is_closed is True


class TestConfigToBayAlcove:
    """Tests for config_to_bay_alcove adapter function."""

    def _create_cabinet_config(self) -> CabinetConfig:
        """Helper to create cabinet config."""
        return CabinetConfig(width=48.0, height=84.0, depth=12.0)

    def _create_room_walls(self) -> list[WallSegmentConfig]:
        """Helper to create room walls."""
        return [WallSegmentConfig(length=120.0, height=96.0, angle=0.0)]

    def _create_bay_walls(self) -> list[BayWallSegmentConfig]:
        """Helper to create bay walls."""
        return [
            BayWallSegmentConfig(length=24.0, angle=45.0, name="left"),
            BayWallSegmentConfig(length=48.0, angle=0.0, name="center"),
            BayWallSegmentConfig(length=24.0, angle=-45.0, name="right"),
        ]

    def test_config_without_room_returns_none(self):
        """Test that config without room returns None."""
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
        )
        result = config_to_bay_alcove(config)
        assert result is None

    def test_config_without_bay_alcove_returns_none(self):
        """Test that config with room but no bay_alcove returns None."""
        room = RoomConfig(name="room", walls=self._create_room_walls())
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
            room=room,
        )
        result = config_to_bay_alcove(config)
        assert result is None

    def test_config_with_bay_alcove_converts(self):
        """Test that config with bay_alcove converts properly."""
        bay_config = BayAlcoveConfigSchema(
            bay_type="three_wall",
            walls=self._create_bay_walls(),
            edge_height=90.0,
            min_cabinet_width=8.0,
        )
        room = RoomConfig(
            name="room",
            walls=self._create_room_walls(),
            bay_alcove=bay_config,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
            room=room,
        )
        result = config_to_bay_alcove(config)

        assert result is not None
        assert isinstance(result, BayAlcoveConfig)
        assert result.bay_type == "three_wall"
        assert result.wall_count == 3
        assert result.edge_height == 90.0
        assert result.min_cabinet_width == 8.0

    def test_config_with_explicit_apex_converts(self):
        """Test that explicit apex configuration converts properly."""
        apex = ApexPointConfig(x=0.0, y=0.0, z=108.0)
        bay_config = BayAlcoveConfigSchema(
            walls=self._create_bay_walls(),
            apex=apex,
        )
        room = RoomConfig(
            name="room",
            walls=self._create_room_walls(),
            bay_alcove=bay_config,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
            room=room,
        )
        result = config_to_bay_alcove(config)

        assert result is not None
        assert result.apex is not None
        assert result.apex.z == 108.0
        assert result.apex_mode == "explicit"

    def test_config_with_auto_apex_converts(self):
        """Test that auto apex configuration converts properly."""
        bay_config = BayAlcoveConfigSchema(
            walls=self._create_bay_walls(),
            apex="auto",
        )
        room = RoomConfig(
            name="room",
            walls=self._create_room_walls(),
            bay_alcove=bay_config,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
            room=room,
        )
        result = config_to_bay_alcove(config)

        assert result is not None
        assert result.apex is None
        assert result.apex_mode == "auto"

    def test_config_with_window_converts(self):
        """Test that wall with window converts properly."""
        window = BayWindowConfig(sill_height=30.0, head_height=72.0, width=36.0)
        walls = [
            BayWallSegmentConfig(length=24.0, angle=45.0),
            BayWallSegmentConfig(length=48.0, angle=0.0, window=window),
            BayWallSegmentConfig(length=24.0, angle=-45.0),
        ]
        bay_config = BayAlcoveConfigSchema(walls=walls)
        room = RoomConfig(
            name="room",
            walls=self._create_room_walls(),
            bay_alcove=bay_config,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
            room=room,
        )
        result = config_to_bay_alcove(config)

        assert result is not None
        center_wall = result.get_wall(1)
        assert center_wall["window"] is not None
        assert center_wall["window"]["sill_height"] == 30.0
        assert center_wall["window"]["head_height"] == 72.0

    def test_bay_alcove_config_properties(self):
        """Test BayAlcoveConfig helper properties."""
        bay_config = BayAlcoveConfigSchema(
            bay_type="bow",
            walls=self._create_bay_walls(),
            arc_angle=120.0,
            segment_count=5,
        )
        room = RoomConfig(
            name="room",
            walls=self._create_room_walls(),
            bay_alcove=bay_config,
        )
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=self._create_cabinet_config(),
            room=room,
        )
        result = config_to_bay_alcove(config)

        assert result is not None
        assert result.is_bow is True
        assert result.wall_count == 3

        # Test get_wall method
        first_wall = result.get_wall(0)
        assert first_wall["length"] == 24.0
        assert first_wall["name"] == "left"
