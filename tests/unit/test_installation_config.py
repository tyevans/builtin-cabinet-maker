"""Unit tests for FRD-17 installation support configuration.

These tests verify:
- Domain value objects (WallType, MountingSystem, LoadCategory, MountingPoint)
- Configuration schema models (InstallationConfigSchema, CleatConfigSchema)
- Config adapter function (config_to_installation)
- Validation rules (mounting system + wall type compatibility)
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from cabinets.application.config import config_to_installation
from cabinets.application.config.schemas import (
    CabinetConfig,
    CabinetConfiguration,
    CleatConfigSchema,
    InstallationConfigSchema,
    LoadCategoryConfig,
    MountingSystemConfig,
    WallTypeConfig,
)
from cabinets.domain.value_objects import (
    LoadCategory,
    MountingPoint,
    MountingSystem,
    WallType,
)


class TestWallTypeEnum:
    """Tests for WallType domain enum."""

    def test_all_values_exist(self) -> None:
        """WallType should have all expected values."""
        assert WallType.DRYWALL.value == "drywall"
        assert WallType.PLASTER.value == "plaster"
        assert WallType.CONCRETE.value == "concrete"
        assert WallType.CMU.value == "cmu"
        assert WallType.BRICK.value == "brick"

    def test_enum_count(self) -> None:
        """WallType should have exactly 5 values."""
        assert len(WallType) == 5

    def test_string_enum_behavior(self) -> None:
        """WallType should behave as a string enum."""
        # String enums are equal to their string values
        assert WallType.DRYWALL == "drywall"
        # The .value attribute returns the string value
        assert WallType.DRYWALL.value == "drywall"


class TestMountingSystemEnum:
    """Tests for MountingSystem domain enum."""

    def test_all_values_exist(self) -> None:
        """MountingSystem should have all expected values."""
        assert MountingSystem.DIRECT_TO_STUD.value == "direct_to_stud"
        assert MountingSystem.FRENCH_CLEAT.value == "french_cleat"
        assert MountingSystem.HANGING_RAIL.value == "hanging_rail"
        assert MountingSystem.TOGGLE_BOLT.value == "toggle_bolt"

    def test_enum_count(self) -> None:
        """MountingSystem should have exactly 4 values."""
        assert len(MountingSystem) == 4

    def test_string_enum_behavior(self) -> None:
        """MountingSystem should behave as a string enum."""
        # String enums are equal to their string values
        assert MountingSystem.FRENCH_CLEAT == "french_cleat"
        # The .value attribute returns the string value
        assert MountingSystem.FRENCH_CLEAT.value == "french_cleat"


class TestLoadCategoryEnum:
    """Tests for LoadCategory domain enum."""

    def test_all_values_exist(self) -> None:
        """LoadCategory should have all expected values."""
        assert LoadCategory.LIGHT.value == "light"
        assert LoadCategory.MEDIUM.value == "medium"
        assert LoadCategory.HEAVY.value == "heavy"

    def test_enum_count(self) -> None:
        """LoadCategory should have exactly 3 values."""
        assert len(LoadCategory) == 3

    def test_string_enum_behavior(self) -> None:
        """LoadCategory should behave as a string enum."""
        # String enums are equal to their string values
        assert LoadCategory.HEAVY == "heavy"
        # The .value attribute returns the string value
        assert LoadCategory.HEAVY.value == "heavy"


class TestMountingPoint:
    """Tests for MountingPoint frozen dataclass."""

    def test_valid_mounting_point(self) -> None:
        """MountingPoint should accept valid parameters."""
        point = MountingPoint(
            x_position=16.0,
            y_position=80.0,
            hits_stud=True,
            fastener_type="screw",
            fastener_spec='#10 x 3" cabinet screw',
        )
        assert point.x_position == 16.0
        assert point.y_position == 80.0
        assert point.hits_stud is True
        assert point.fastener_type == "screw"
        assert point.fastener_spec == '#10 x 3" cabinet screw'

    def test_zero_positions_valid(self) -> None:
        """MountingPoint should accept zero positions."""
        point = MountingPoint(
            x_position=0.0,
            y_position=0.0,
            hits_stud=False,
            fastener_type="toggle_bolt",
            fastener_spec='1/4" toggle bolt',
        )
        assert point.x_position == 0.0
        assert point.y_position == 0.0

    def test_negative_x_position_rejected(self) -> None:
        """MountingPoint should reject negative x_position."""
        with pytest.raises(ValueError) as exc_info:
            MountingPoint(
                x_position=-1.0,
                y_position=80.0,
                hits_stud=True,
                fastener_type="screw",
                fastener_spec='#10 x 3" screw',
            )
        assert "x_position must be non-negative" in str(exc_info.value)

    def test_negative_y_position_rejected(self) -> None:
        """MountingPoint should reject negative y_position."""
        with pytest.raises(ValueError) as exc_info:
            MountingPoint(
                x_position=16.0,
                y_position=-1.0,
                hits_stud=True,
                fastener_type="screw",
                fastener_spec='#10 x 3" screw',
            )
        assert "y_position must be non-negative" in str(exc_info.value)

    def test_empty_fastener_type_rejected(self) -> None:
        """MountingPoint should reject empty fastener_type."""
        with pytest.raises(ValueError) as exc_info:
            MountingPoint(
                x_position=16.0,
                y_position=80.0,
                hits_stud=True,
                fastener_type="",
                fastener_spec='#10 x 3" screw',
            )
        assert "fastener_type must not be empty" in str(exc_info.value)

    def test_empty_fastener_spec_rejected(self) -> None:
        """MountingPoint should reject empty fastener_spec."""
        with pytest.raises(ValueError) as exc_info:
            MountingPoint(
                x_position=16.0,
                y_position=80.0,
                hits_stud=True,
                fastener_type="screw",
                fastener_spec="",
            )
        assert "fastener_spec must not be empty" in str(exc_info.value)

    def test_frozen_dataclass(self) -> None:
        """MountingPoint should be immutable."""
        point = MountingPoint(
            x_position=16.0,
            y_position=80.0,
            hits_stud=True,
            fastener_type="screw",
            fastener_spec='#10 x 3" screw',
        )
        with pytest.raises(AttributeError):
            point.x_position = 32.0  # type: ignore


class TestCleatConfigSchema:
    """Tests for CleatConfigSchema Pydantic model."""

    def test_defaults(self) -> None:
        """CleatConfigSchema should have expected defaults."""
        config = CleatConfigSchema()
        assert config.position_from_top == 4.0
        assert config.width_percentage == 90.0
        assert config.bevel_angle == 45.0

    def test_valid_position_from_top_range(self) -> None:
        """position_from_top should accept values in 2.0-12.0 range."""
        # Minimum valid
        config = CleatConfigSchema(position_from_top=2.0)
        assert config.position_from_top == 2.0

        # Maximum valid
        config = CleatConfigSchema(position_from_top=12.0)
        assert config.position_from_top == 12.0

        # Mid-range
        config = CleatConfigSchema(position_from_top=6.5)
        assert config.position_from_top == 6.5

    def test_position_from_top_below_minimum_rejected(self) -> None:
        """position_from_top below 2.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(position_from_top=1.5)
        assert "greater than or equal to 2" in str(exc_info.value)

    def test_position_from_top_above_maximum_rejected(self) -> None:
        """position_from_top above 12.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(position_from_top=12.5)
        assert "less than or equal to 12" in str(exc_info.value)

    def test_valid_width_percentage_range(self) -> None:
        """width_percentage should accept values in 75.0-100.0 range."""
        # Minimum valid
        config = CleatConfigSchema(width_percentage=75.0)
        assert config.width_percentage == 75.0

        # Maximum valid
        config = CleatConfigSchema(width_percentage=100.0)
        assert config.width_percentage == 100.0

    def test_width_percentage_below_minimum_rejected(self) -> None:
        """width_percentage below 75.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(width_percentage=70.0)
        assert "greater than or equal to 75" in str(exc_info.value)

    def test_width_percentage_above_maximum_rejected(self) -> None:
        """width_percentage above 100.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(width_percentage=105.0)
        assert "less than or equal to 100" in str(exc_info.value)

    def test_valid_bevel_angle_range(self) -> None:
        """bevel_angle should accept values in 30.0-45.0 range."""
        # Minimum valid
        config = CleatConfigSchema(bevel_angle=30.0)
        assert config.bevel_angle == 30.0

        # Maximum valid
        config = CleatConfigSchema(bevel_angle=45.0)
        assert config.bevel_angle == 45.0

    def test_bevel_angle_below_minimum_rejected(self) -> None:
        """bevel_angle below 30.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(bevel_angle=25.0)
        assert "greater than or equal to 30" in str(exc_info.value)

    def test_bevel_angle_above_maximum_rejected(self) -> None:
        """bevel_angle above 45.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(bevel_angle=50.0)
        assert "less than or equal to 45" in str(exc_info.value)

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            CleatConfigSchema(position_from_top=4.0, unknown_field=True)  # type: ignore
        assert "unknown_field" in str(exc_info.value)


class TestInstallationConfigSchema:
    """Tests for InstallationConfigSchema Pydantic model."""

    def test_defaults(self) -> None:
        """InstallationConfigSchema should have expected defaults."""
        config = InstallationConfigSchema()
        assert config.wall_type == WallTypeConfig.DRYWALL
        assert config.wall_thickness == 0.5
        assert config.stud_spacing == 16.0
        assert config.stud_offset == 0.0
        assert config.mounting_system == MountingSystemConfig.DIRECT_TO_STUD
        assert config.expected_load == LoadCategoryConfig.MEDIUM
        assert config.cleat is None
        assert config.generate_instructions is True

    def test_all_wall_types_accepted(self) -> None:
        """All WallTypeConfig values should be accepted."""
        for wall_type in WallTypeConfig:
            # Skip toggle_bolt validation issue for masonry walls
            if wall_type in {
                WallTypeConfig.CONCRETE,
                WallTypeConfig.CMU,
                WallTypeConfig.BRICK,
            }:
                config = InstallationConfigSchema(
                    wall_type=wall_type,
                    mounting_system=MountingSystemConfig.DIRECT_TO_STUD,
                )
            else:
                config = InstallationConfigSchema(wall_type=wall_type)
            assert config.wall_type == wall_type

    def test_all_mounting_systems_accepted(self) -> None:
        """All MountingSystemConfig values should be accepted on drywall."""
        for mounting_system in MountingSystemConfig:
            config = InstallationConfigSchema(mounting_system=mounting_system)
            assert config.mounting_system == mounting_system

    def test_all_load_categories_accepted(self) -> None:
        """All LoadCategoryConfig values should be accepted."""
        for load_category in LoadCategoryConfig:
            config = InstallationConfigSchema(expected_load=load_category)
            assert config.expected_load == load_category

    def test_valid_wall_thickness_range(self) -> None:
        """wall_thickness should accept values in 0.25-2.0 range."""
        config = InstallationConfigSchema(wall_thickness=0.25)
        assert config.wall_thickness == 0.25

        config = InstallationConfigSchema(wall_thickness=2.0)
        assert config.wall_thickness == 2.0

    def test_wall_thickness_below_minimum_rejected(self) -> None:
        """wall_thickness below 0.25 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(wall_thickness=0.2)
        assert "greater than or equal to 0.25" in str(exc_info.value)

    def test_wall_thickness_above_maximum_rejected(self) -> None:
        """wall_thickness above 2.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(wall_thickness=2.5)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_valid_stud_spacing_range(self) -> None:
        """stud_spacing should accept values in 12.0-32.0 range."""
        # Standard 16" spacing
        config = InstallationConfigSchema(stud_spacing=16.0)
        assert config.stud_spacing == 16.0

        # Standard 24" spacing
        config = InstallationConfigSchema(stud_spacing=24.0)
        assert config.stud_spacing == 24.0

    def test_stud_spacing_below_minimum_rejected(self) -> None:
        """stud_spacing below 12.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(stud_spacing=10.0)
        assert "greater than or equal to 12" in str(exc_info.value)

    def test_stud_spacing_above_maximum_rejected(self) -> None:
        """stud_spacing above 32.0 should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(stud_spacing=36.0)
        assert "less than or equal to 32" in str(exc_info.value)

    def test_valid_stud_offset(self) -> None:
        """stud_offset should accept non-negative values."""
        config = InstallationConfigSchema(stud_offset=0.0)
        assert config.stud_offset == 0.0

        config = InstallationConfigSchema(stud_offset=8.0)
        assert config.stud_offset == 8.0

    def test_negative_stud_offset_rejected(self) -> None:
        """Negative stud_offset should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(stud_offset=-1.0)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_cleat_config_optional(self) -> None:
        """cleat should be optional and default to None."""
        config = InstallationConfigSchema()
        assert config.cleat is None

    def test_cleat_config_accepted(self) -> None:
        """cleat configuration should be accepted when provided."""
        cleat = CleatConfigSchema(
            position_from_top=5.0,
            width_percentage=85.0,
            bevel_angle=40.0,
        )
        config = InstallationConfigSchema(cleat=cleat)
        assert config.cleat is not None
        assert config.cleat.position_from_top == 5.0
        assert config.cleat.width_percentage == 85.0
        assert config.cleat.bevel_angle == 40.0

    def test_rejects_unknown_fields(self) -> None:
        """Unknown fields should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(unknown_field="value")  # type: ignore
        assert "unknown_field" in str(exc_info.value)


class TestMountingSystemWallTypeValidation:
    """Tests for mounting system + wall type compatibility validation."""

    def test_toggle_bolt_on_concrete_rejected(self) -> None:
        """Toggle bolt on concrete wall should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(
                wall_type=WallTypeConfig.CONCRETE,
                mounting_system=MountingSystemConfig.TOGGLE_BOLT,
            )
        assert "toggle bolt" in str(exc_info.value).lower()
        assert "concrete" in str(exc_info.value).lower()

    def test_toggle_bolt_on_cmu_rejected(self) -> None:
        """Toggle bolt on CMU wall should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(
                wall_type=WallTypeConfig.CMU,
                mounting_system=MountingSystemConfig.TOGGLE_BOLT,
            )
        assert "toggle bolt" in str(exc_info.value).lower()
        assert "cmu" in str(exc_info.value).lower()

    def test_toggle_bolt_on_brick_rejected(self) -> None:
        """Toggle bolt on brick wall should be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            InstallationConfigSchema(
                wall_type=WallTypeConfig.BRICK,
                mounting_system=MountingSystemConfig.TOGGLE_BOLT,
            )
        assert "toggle bolt" in str(exc_info.value).lower()
        assert "brick" in str(exc_info.value).lower()

    def test_toggle_bolt_on_drywall_accepted(self) -> None:
        """Toggle bolt on drywall should be accepted."""
        config = InstallationConfigSchema(
            wall_type=WallTypeConfig.DRYWALL,
            mounting_system=MountingSystemConfig.TOGGLE_BOLT,
        )
        assert config.mounting_system == MountingSystemConfig.TOGGLE_BOLT

    def test_toggle_bolt_on_plaster_accepted(self) -> None:
        """Toggle bolt on plaster should be accepted."""
        config = InstallationConfigSchema(
            wall_type=WallTypeConfig.PLASTER,
            mounting_system=MountingSystemConfig.TOGGLE_BOLT,
        )
        assert config.mounting_system == MountingSystemConfig.TOGGLE_BOLT

    def test_direct_to_stud_on_all_wall_types_accepted(self) -> None:
        """Direct to stud mounting should work on all wall types."""
        for wall_type in WallTypeConfig:
            config = InstallationConfigSchema(
                wall_type=wall_type,
                mounting_system=MountingSystemConfig.DIRECT_TO_STUD,
            )
            assert config.mounting_system == MountingSystemConfig.DIRECT_TO_STUD

    def test_french_cleat_on_all_wall_types_accepted(self) -> None:
        """French cleat mounting should work on all wall types."""
        for wall_type in WallTypeConfig:
            config = InstallationConfigSchema(
                wall_type=wall_type,
                mounting_system=MountingSystemConfig.FRENCH_CLEAT,
            )
            assert config.mounting_system == MountingSystemConfig.FRENCH_CLEAT


class TestConfigToInstallation:
    """Tests for config_to_installation adapter function."""

    def _create_minimal_cabinet_config(
        self, installation: InstallationConfigSchema | None = None
    ) -> CabinetConfiguration:
        """Create a minimal valid CabinetConfiguration for testing."""
        return CabinetConfiguration(
            schema_version="1.8",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            installation=installation,
        )

    def test_returns_none_when_no_installation_config(self) -> None:
        """config_to_installation should return None when no installation config."""
        config = self._create_minimal_cabinet_config(installation=None)
        result = config_to_installation(config)
        assert result is None

    def test_returns_dict_when_installation_config_present(self) -> None:
        """config_to_installation should return dict when installation config present."""
        installation = InstallationConfigSchema()
        config = self._create_minimal_cabinet_config(installation=installation)
        result = config_to_installation(config)
        assert result is not None
        assert isinstance(result, dict)

    def test_maps_wall_type_correctly(self) -> None:
        """config_to_installation should map wall_type to domain enum."""
        for config_type, domain_type in [
            (WallTypeConfig.DRYWALL, WallType.DRYWALL),
            (WallTypeConfig.PLASTER, WallType.PLASTER),
            (WallTypeConfig.CONCRETE, WallType.CONCRETE),
            (WallTypeConfig.CMU, WallType.CMU),
            (WallTypeConfig.BRICK, WallType.BRICK),
        ]:
            # Use direct_to_stud to avoid toggle_bolt validation issues
            installation = InstallationConfigSchema(
                wall_type=config_type,
                mounting_system=MountingSystemConfig.DIRECT_TO_STUD,
            )
            config = self._create_minimal_cabinet_config(installation=installation)
            result = config_to_installation(config)
            assert result is not None
            assert result["wall_type"] == domain_type

    def test_maps_mounting_system_correctly(self) -> None:
        """config_to_installation should map mounting_system to domain enum."""
        for config_type, domain_type in [
            (MountingSystemConfig.DIRECT_TO_STUD, MountingSystem.DIRECT_TO_STUD),
            (MountingSystemConfig.FRENCH_CLEAT, MountingSystem.FRENCH_CLEAT),
            (MountingSystemConfig.HANGING_RAIL, MountingSystem.HANGING_RAIL),
            (MountingSystemConfig.TOGGLE_BOLT, MountingSystem.TOGGLE_BOLT),
        ]:
            installation = InstallationConfigSchema(mounting_system=config_type)
            config = self._create_minimal_cabinet_config(installation=installation)
            result = config_to_installation(config)
            assert result is not None
            assert result["mounting_system"] == domain_type

    def test_maps_load_category_correctly(self) -> None:
        """config_to_installation should map expected_load to domain enum."""
        for config_type, domain_type in [
            (LoadCategoryConfig.LIGHT, LoadCategory.LIGHT),
            (LoadCategoryConfig.MEDIUM, LoadCategory.MEDIUM),
            (LoadCategoryConfig.HEAVY, LoadCategory.HEAVY),
        ]:
            installation = InstallationConfigSchema(expected_load=config_type)
            config = self._create_minimal_cabinet_config(installation=installation)
            result = config_to_installation(config)
            assert result is not None
            assert result["expected_load"] == domain_type

    def test_includes_all_scalar_fields(self) -> None:
        """config_to_installation should include all scalar configuration fields."""
        installation = InstallationConfigSchema(
            wall_thickness=0.625,
            stud_spacing=24.0,
            stud_offset=4.0,
            generate_instructions=False,
        )
        config = self._create_minimal_cabinet_config(installation=installation)
        result = config_to_installation(config)
        assert result is not None
        assert result["wall_thickness"] == 0.625
        assert result["stud_spacing"] == 24.0
        assert result["stud_offset"] == 4.0
        assert result["generate_instructions"] is False

    def test_cleat_is_none_when_not_provided(self) -> None:
        """config_to_installation should set cleat to None when not provided."""
        installation = InstallationConfigSchema()
        config = self._create_minimal_cabinet_config(installation=installation)
        result = config_to_installation(config)
        assert result is not None
        assert result["cleat"] is None

    def test_includes_cleat_configuration(self) -> None:
        """config_to_installation should include cleat configuration when provided."""
        cleat = CleatConfigSchema(
            position_from_top=5.0,
            width_percentage=85.0,
            bevel_angle=40.0,
        )
        installation = InstallationConfigSchema(cleat=cleat)
        config = self._create_minimal_cabinet_config(installation=installation)
        result = config_to_installation(config)
        assert result is not None
        assert result["cleat"] is not None
        assert result["cleat"]["position_from_top"] == 5.0
        assert result["cleat"]["width_percentage"] == 85.0
        assert result["cleat"]["bevel_angle"] == 40.0


class TestSchemaVersionSupport:
    """Tests for schema version 1.8 support."""

    def test_version_1_8_supported(self) -> None:
        """Schema version 1.8 should be supported."""
        config = CabinetConfiguration(
            schema_version="1.8",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        assert config.schema_version == "1.8"

    def test_installation_field_accepted(self) -> None:
        """CabinetConfiguration should accept installation field."""
        installation = InstallationConfigSchema()
        config = CabinetConfiguration(
            schema_version="1.8",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            installation=installation,
        )
        assert config.installation is not None
        assert config.installation.wall_type == WallTypeConfig.DRYWALL
