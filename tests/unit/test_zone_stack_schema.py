"""Unit tests for FRD-22 Zone Stack configuration schemas.

Tests cover:
- CountertopOverhangSchema defaults and validation
- CountertopConfigSchema defaults and validation
- VerticalZoneConfigSchema validation
- ZoneStackConfigSchema preset validation
- ZoneStackConfigSchema custom zones validation
- config_to_zone_layout adapter function
- Full config file parsing with zone_stack
"""

import pytest
from pydantic import ValidationError

from cabinets.application.config import (
    CountertopConfigSchema,
    CountertopEdgeConfig,
    CountertopOverhangSchema,
    GapPurposeConfig,
    MaterialConfig,
    VerticalZoneConfigSchema,
    ZoneMountingConfig,
    ZonePresetConfig,
    ZoneStackConfigSchema,
    ZoneTypeConfig,
    config_to_zone_layout,
    load_config_from_dict,
)
from cabinets.domain.value_objects import MaterialSpec


class TestCountertopOverhangSchema:
    """Tests for CountertopOverhangSchema."""

    def test_defaults(self) -> None:
        """Test that default values are correct."""
        schema = CountertopOverhangSchema()
        assert schema.front == 1.0
        assert schema.left == 0.0
        assert schema.right == 0.0
        assert schema.back == 0.0

    def test_custom_values(self) -> None:
        """Test that custom overhang values are accepted."""
        schema = CountertopOverhangSchema(
            front=2.0,
            left=1.0,
            right=1.0,
            back=0.5,
        )
        assert schema.front == 2.0
        assert schema.left == 1.0
        assert schema.right == 1.0
        assert schema.back == 0.5

    def test_front_overhang_limits(self) -> None:
        """Test front overhang validation limits."""
        # Maximum 24 inches
        schema = CountertopOverhangSchema(front=24.0)
        assert schema.front == 24.0

        # Over limit
        with pytest.raises(ValidationError) as exc_info:
            CountertopOverhangSchema(front=25.0)
        assert "less than or equal to 24" in str(exc_info.value)

    def test_side_overhang_limits(self) -> None:
        """Test left/right overhang validation limits."""
        # Maximum 6 inches
        schema = CountertopOverhangSchema(left=6.0, right=6.0)
        assert schema.left == 6.0
        assert schema.right == 6.0

        # Over limit
        with pytest.raises(ValidationError) as exc_info:
            CountertopOverhangSchema(left=7.0)
        assert "less than or equal to 6" in str(exc_info.value)

    def test_back_overhang_limits(self) -> None:
        """Test back overhang validation limits."""
        # Maximum 2 inches
        schema = CountertopOverhangSchema(back=2.0)
        assert schema.back == 2.0

        # Over limit
        with pytest.raises(ValidationError) as exc_info:
            CountertopOverhangSchema(back=3.0)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_negative_overhang_rejected(self) -> None:
        """Test that negative overhang values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CountertopOverhangSchema(front=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestCountertopConfigSchema:
    """Tests for CountertopConfigSchema."""

    def test_defaults(self) -> None:
        """Test that default values are correct."""
        schema = CountertopConfigSchema()
        assert schema.thickness == 1.0
        assert schema.edge_treatment == CountertopEdgeConfig.SQUARE
        assert schema.support_brackets is False
        assert schema.material is None
        assert schema.overhang.front == 1.0

    def test_thickness_limits(self) -> None:
        """Test thickness validation limits."""
        # Minimum 0.5 inches
        schema = CountertopConfigSchema(thickness=0.5)
        assert schema.thickness == 0.5

        # Maximum 2.0 inches
        schema = CountertopConfigSchema(thickness=2.0)
        assert schema.thickness == 2.0

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            CountertopConfigSchema(thickness=0.4)
        assert "greater than or equal to 0.5" in str(exc_info.value)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            CountertopConfigSchema(thickness=2.5)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_edge_treatments(self) -> None:
        """Test all edge treatment options."""
        for edge in CountertopEdgeConfig:
            schema = CountertopConfigSchema(edge_treatment=edge)
            assert schema.edge_treatment == edge

    def test_custom_material(self) -> None:
        """Test custom material override."""
        material = MaterialConfig(type="plywood", thickness=1.5)
        schema = CountertopConfigSchema(material=material)
        assert schema.material is not None
        assert schema.material.thickness == 1.5

    def test_support_brackets(self) -> None:
        """Test support brackets option."""
        schema = CountertopConfigSchema(support_brackets=True)
        assert schema.support_brackets is True


class TestVerticalZoneConfigSchema:
    """Tests for VerticalZoneConfigSchema."""

    def test_base_zone(self) -> None:
        """Test base cabinet zone configuration."""
        schema = VerticalZoneConfigSchema(
            zone_type=ZoneTypeConfig.BASE,
            height=36.0,
            depth=24.0,
            mounting=ZoneMountingConfig.FLOOR,
        )
        assert schema.zone_type == ZoneTypeConfig.BASE
        assert schema.height == 36.0
        assert schema.depth == 24.0
        assert schema.mounting == ZoneMountingConfig.FLOOR

    def test_upper_zone(self) -> None:
        """Test upper cabinet zone configuration."""
        schema = VerticalZoneConfigSchema(
            zone_type=ZoneTypeConfig.UPPER,
            height=30.0,
            depth=12.0,
            mounting=ZoneMountingConfig.WALL,
            mounting_height=54.0,
        )
        assert schema.zone_type == ZoneTypeConfig.UPPER
        assert schema.mounting == ZoneMountingConfig.WALL
        assert schema.mounting_height == 54.0

    def test_gap_zone(self) -> None:
        """Test gap zone configuration."""
        schema = VerticalZoneConfigSchema(
            zone_type=ZoneTypeConfig.GAP,
            height=18.0,
            depth=0.0,
            gap_purpose=GapPurposeConfig.BACKSPLASH,
        )
        assert schema.zone_type == ZoneTypeConfig.GAP
        assert schema.depth == 0.0
        assert schema.gap_purpose == GapPurposeConfig.BACKSPLASH

    def test_height_must_be_positive(self) -> None:
        """Test that height must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.BASE,
                height=0,
                depth=24.0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_depth_can_be_zero(self) -> None:
        """Test that depth can be zero (for gap zones)."""
        schema = VerticalZoneConfigSchema(
            zone_type=ZoneTypeConfig.GAP,
            height=18.0,
            depth=0.0,
        )
        assert schema.depth == 0.0

    def test_depth_cannot_be_negative(self) -> None:
        """Test that depth cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.BASE,
                height=36.0,
                depth=-1.0,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_all_zone_types(self) -> None:
        """Test all zone type options."""
        for zone_type in ZoneTypeConfig:
            schema = VerticalZoneConfigSchema(
                zone_type=zone_type,
                height=24.0,
                depth=12.0,
            )
            assert schema.zone_type == zone_type

    def test_all_mounting_types(self) -> None:
        """Test all mounting type options."""
        for mounting in ZoneMountingConfig:
            schema = VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.UPPER,
                height=24.0,
                depth=12.0,
                mounting=mounting,
            )
            assert schema.mounting == mounting

    def test_all_gap_purposes(self) -> None:
        """Test all gap purpose options."""
        for purpose in GapPurposeConfig:
            schema = VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.GAP,
                height=18.0,
                depth=0.0,
                gap_purpose=purpose,
            )
            assert schema.gap_purpose == purpose


class TestZoneStackConfigSchema:
    """Tests for ZoneStackConfigSchema."""

    def test_preset_defaults(self) -> None:
        """Test that preset defaults to custom."""
        # Non-custom preset doesn't require zones
        schema = ZoneStackConfigSchema(preset=ZonePresetConfig.KITCHEN)
        assert schema.preset == ZonePresetConfig.KITCHEN
        assert schema.zones == []

    def test_custom_preset_requires_zones(self) -> None:
        """Test that custom preset requires zones list."""
        with pytest.raises(ValidationError) as exc_info:
            ZoneStackConfigSchema(preset=ZonePresetConfig.CUSTOM)
        assert "Custom zone preset requires 'zones' list" in str(exc_info.value)

    def test_custom_preset_with_zones(self) -> None:
        """Test custom preset with zones defined."""
        zones = [
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.BASE,
                height=36.0,
                depth=24.0,
            ),
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.GAP,
                height=18.0,
                depth=0.0,
                gap_purpose=GapPurposeConfig.BACKSPLASH,
            ),
        ]
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.CUSTOM,
            zones=zones,
        )
        assert schema.preset == ZonePresetConfig.CUSTOM
        assert len(schema.zones) == 2

    def test_all_presets(self) -> None:
        """Test all preset options."""
        for preset in ZonePresetConfig:
            if preset == ZonePresetConfig.CUSTOM:
                # Custom requires zones
                zones = [
                    VerticalZoneConfigSchema(
                        zone_type=ZoneTypeConfig.BASE,
                        height=36.0,
                        depth=24.0,
                    )
                ]
                schema = ZoneStackConfigSchema(preset=preset, zones=zones)
            else:
                schema = ZoneStackConfigSchema(preset=preset)
            assert schema.preset == preset

    def test_countertop_config(self) -> None:
        """Test countertop configuration in zone stack."""
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.KITCHEN,
            countertop=CountertopConfigSchema(
                thickness=1.5,
                edge_treatment=CountertopEdgeConfig.BULLNOSE,
            ),
        )
        assert schema.countertop is not None
        assert schema.countertop.thickness == 1.5
        assert schema.countertop.edge_treatment == CountertopEdgeConfig.BULLNOSE

    def test_full_height_sides(self) -> None:
        """Test full height sides option."""
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.KITCHEN,
            full_height_sides=True,
        )
        assert schema.full_height_sides is True

    def test_upper_cabinet_height_limits(self) -> None:
        """Test upper cabinet height validation limits."""
        # Minimum 12 inches
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.KITCHEN,
            upper_cabinet_height=12.0,
        )
        assert schema.upper_cabinet_height == 12.0

        # Maximum 48 inches
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.KITCHEN,
            upper_cabinet_height=48.0,
        )
        assert schema.upper_cabinet_height == 48.0

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ZoneStackConfigSchema(
                preset=ZonePresetConfig.KITCHEN,
                upper_cabinet_height=10.0,
            )
        assert "greater than or equal to 12" in str(exc_info.value)


class TestConfigToZoneLayout:
    """Tests for config_to_zone_layout adapter function."""

    def test_basic_preset(self) -> None:
        """Test conversion of preset configuration."""
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.KITCHEN,
            upper_cabinet_height=30.0,
        )
        result = config_to_zone_layout(schema, cabinet_width=48.0)

        assert result.preset == "kitchen"
        assert result.width == 48.0
        assert result.upper_cabinet_height == 30.0

    def test_custom_zones(self) -> None:
        """Test conversion of custom zone configuration."""
        zones = [
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.BASE,
                height=36.0,
                depth=24.0,
                mounting=ZoneMountingConfig.FLOOR,
            ),
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.GAP,
                height=18.0,
                depth=0.0,
                gap_purpose=GapPurposeConfig.BACKSPLASH,
            ),
            VerticalZoneConfigSchema(
                zone_type=ZoneTypeConfig.UPPER,
                height=30.0,
                depth=12.0,
                mounting=ZoneMountingConfig.WALL,
                mounting_height=54.0,
            ),
        ]
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.CUSTOM,
            zones=zones,
        )
        result = config_to_zone_layout(schema, cabinet_width=60.0)

        assert result.preset == "custom"
        assert result.width == 60.0
        assert result.custom_zones is not None
        assert len(result.custom_zones) == 3

        # Check first zone
        base_zone = result.custom_zones[0]
        assert base_zone["zone_type"] == "base"
        assert base_zone["height"] == 36.0
        assert base_zone["depth"] == 24.0
        assert base_zone["mounting"] == "floor"

        # Check gap zone with purpose
        gap_zone = result.custom_zones[1]
        assert gap_zone["zone_type"] == "gap"
        assert gap_zone["gap_purpose"] == "backsplash"

        # Check upper zone with mounting height
        upper_zone = result.custom_zones[2]
        assert upper_zone["zone_type"] == "upper"
        assert upper_zone["mounting_height"] == 54.0

    def test_countertop_conversion(self) -> None:
        """Test countertop configuration conversion."""
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.KITCHEN,
            countertop=CountertopConfigSchema(
                thickness=1.5,
                overhang=CountertopOverhangSchema(
                    front=2.0,
                    left=1.0,
                    right=1.0,
                    back=0.5,
                ),
                edge_treatment=CountertopEdgeConfig.BULLNOSE,
                support_brackets=True,
            ),
        )
        result = config_to_zone_layout(schema, cabinet_width=48.0)

        assert result.countertop is not None
        assert result.countertop.thickness == 1.5
        assert result.countertop.front_overhang == 2.0
        assert result.countertop.left_overhang == 1.0
        assert result.countertop.right_overhang == 1.0
        assert result.countertop.back_overhang == 0.5
        assert result.countertop.edge_treatment == "bullnose"
        assert result.countertop.support_brackets is True

    def test_with_material(self) -> None:
        """Test conversion with material parameter."""
        schema = ZoneStackConfigSchema(preset=ZonePresetConfig.VANITY)
        material = MaterialSpec(thickness=0.75)
        result = config_to_zone_layout(schema, cabinet_width=36.0, material=material)

        assert result.material is not None
        assert result.material.thickness == 0.75

    def test_full_height_sides(self) -> None:
        """Test full height sides conversion."""
        schema = ZoneStackConfigSchema(
            preset=ZonePresetConfig.HUTCH,
            full_height_sides=True,
        )
        result = config_to_zone_layout(schema, cabinet_width=48.0)

        assert result.full_height_sides is True


class TestFullConfigParsing:
    """Tests for full config file parsing with zone_stack."""

    def test_config_with_zone_stack(self) -> None:
        """Test loading a full config with zone_stack."""
        config_dict = {
            "schema_version": "1.11",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 24.0,
                "zone_stack": {
                    "preset": "kitchen",
                    "countertop": {
                        "thickness": 1.0,
                        "overhang": {"front": 1.5},
                        "edge_treatment": "eased",
                    },
                    "full_height_sides": True,
                },
            },
        }
        config = load_config_from_dict(config_dict)

        assert config.cabinet.zone_stack is not None
        assert config.cabinet.zone_stack.preset == ZonePresetConfig.KITCHEN
        assert config.cabinet.zone_stack.countertop is not None
        assert config.cabinet.zone_stack.countertop.thickness == 1.0
        assert config.cabinet.zone_stack.countertop.overhang.front == 1.5
        assert config.cabinet.zone_stack.full_height_sides is True

    def test_config_with_custom_zones(self) -> None:
        """Test loading config with custom zone stack."""
        config_dict = {
            "schema_version": "1.11",
            "cabinet": {
                "width": 60.0,
                "height": 96.0,
                "depth": 24.0,
                "zone_stack": {
                    "preset": "custom",
                    "zones": [
                        {
                            "zone_type": "base",
                            "height": 36.0,
                            "depth": 24.0,
                            "mounting": "floor",
                        },
                        {
                            "zone_type": "gap",
                            "height": 18.0,
                            "depth": 0.0,
                            "gap_purpose": "backsplash",
                        },
                        {
                            "zone_type": "upper",
                            "height": 30.0,
                            "depth": 12.0,
                            "mounting": "wall",
                            "mounting_height": 54.0,
                        },
                    ],
                },
            },
        }
        config = load_config_from_dict(config_dict)

        assert config.cabinet.zone_stack is not None
        assert config.cabinet.zone_stack.preset == ZonePresetConfig.CUSTOM
        assert len(config.cabinet.zone_stack.zones) == 3

    def test_config_without_zone_stack(self) -> None:
        """Test that zone_stack is optional."""
        config_dict = {
            "schema_version": "1.11",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
            },
        }
        config = load_config_from_dict(config_dict)

        assert config.cabinet.zone_stack is None

    def test_config_integration_with_adapter(self) -> None:
        """Test full config loading and adapter conversion."""
        config_dict = {
            "schema_version": "1.11",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 24.0,
                "zone_stack": {
                    "preset": "mudroom",
                    "upper_cabinet_height": 36.0,
                },
            },
        }
        config = load_config_from_dict(config_dict)

        assert config.cabinet.zone_stack is not None
        zone_config = config_to_zone_layout(
            config.cabinet.zone_stack,
            config.cabinet.width,
        )

        assert zone_config.preset == "mudroom"
        assert zone_config.width == 48.0
        assert zone_config.upper_cabinet_height == 36.0
