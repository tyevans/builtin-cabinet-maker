"""Tests for media/entertainment center components (FRD-19 Phase 1).

Tests verify:
- CABLE_CHASE is in PanelType enum
- All media enums exist with correct values
- Media components register correctly in the registry
- Equipment presets have correct dimensions
- VentilationSpec and EquipmentSpec dataclasses work correctly
- Component validation and generation logic
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import (
    ComponentContext,
    GenerationResult,
    ValidationResult,
    component_registry,
)
from cabinets.domain.components.media import (
    EQUIPMENT_PRESETS,
    HEAT_GENERATING_EQUIPMENT,
    HEAT_SOURCE_CLEARANCE,
    MIN_EQUIPMENT_DEPTH,
    MIN_VERTICAL_CLEARANCE,
    RECOMMENDED_EQUIPMENT_DEPTH,
    EquipmentShelfComponent,
    EquipmentSpec,
    SoundbarShelfComponent,
    SpeakerAlcoveComponent,
    VentilatedSectionComponent,
    VentilationSpec,
    _get_equipment_spec,
)
from cabinets.domain.value_objects import (
    EquipmentType,
    MaterialSpec,
    PanelType,
    Position,
    SoundbarType,
    SpeakerType,
)


# =============================================================================
# Task 01: PanelType CABLE_CHASE Tests
# =============================================================================


class TestCableChaseEnumValue:
    """Tests for CABLE_CHASE in PanelType enum."""

    def test_cable_chase_in_panel_type_enum(self) -> None:
        """Test that CABLE_CHASE is a valid PanelType enum member."""
        assert hasattr(PanelType, "CABLE_CHASE")
        assert PanelType.CABLE_CHASE.value == "cable_chase"

    def test_cable_chase_is_enum_member(self) -> None:
        """Test that CABLE_CHASE is a proper enum member."""
        assert isinstance(PanelType.CABLE_CHASE, PanelType)

    def test_cable_chase_can_be_used_in_comparison(self) -> None:
        """Test that CABLE_CHASE can be compared like other PanelType values."""
        panel_type = PanelType.CABLE_CHASE
        assert panel_type == PanelType.CABLE_CHASE
        assert panel_type != PanelType.SHELF


# =============================================================================
# Task 01: Media Enums Tests
# =============================================================================


class TestEquipmentTypeEnum:
    """Tests for EquipmentType enum."""

    def test_equipment_type_exists(self) -> None:
        """Test that EquipmentType enum exists."""
        assert EquipmentType is not None

    def test_equipment_type_values(self) -> None:
        """Test that all expected equipment types are present."""
        expected_values = {
            "receiver",
            "console_horizontal",
            "console_vertical",
            "streaming",
            "cable_box",
            "blu_ray",
            "turntable",
            "custom",
        }
        actual_values = {member.value for member in EquipmentType}
        assert actual_values == expected_values

    def test_receiver_enum_value(self) -> None:
        """Test RECEIVER enum value."""
        assert EquipmentType.RECEIVER.value == "receiver"

    def test_console_horizontal_enum_value(self) -> None:
        """Test CONSOLE_HORIZONTAL enum value."""
        assert EquipmentType.CONSOLE_HORIZONTAL.value == "console_horizontal"

    def test_console_vertical_enum_value(self) -> None:
        """Test CONSOLE_VERTICAL enum value."""
        assert EquipmentType.CONSOLE_VERTICAL.value == "console_vertical"

    def test_streaming_enum_value(self) -> None:
        """Test STREAMING enum value."""
        assert EquipmentType.STREAMING.value == "streaming"

    def test_cable_box_enum_value(self) -> None:
        """Test CABLE_BOX enum value."""
        assert EquipmentType.CABLE_BOX.value == "cable_box"

    def test_blu_ray_enum_value(self) -> None:
        """Test BLU_RAY enum value."""
        assert EquipmentType.BLU_RAY.value == "blu_ray"

    def test_turntable_enum_value(self) -> None:
        """Test TURNTABLE enum value."""
        assert EquipmentType.TURNTABLE.value == "turntable"

    def test_custom_enum_value(self) -> None:
        """Test CUSTOM enum value."""
        assert EquipmentType.CUSTOM.value == "custom"


class TestSoundbarTypeEnum:
    """Tests for SoundbarType enum."""

    def test_soundbar_type_exists(self) -> None:
        """Test that SoundbarType enum exists."""
        assert SoundbarType is not None

    def test_soundbar_type_values(self) -> None:
        """Test that all expected soundbar types are present."""
        expected_values = {"compact", "standard", "premium", "custom"}
        actual_values = {member.value for member in SoundbarType}
        assert actual_values == expected_values

    def test_compact_enum_value(self) -> None:
        """Test COMPACT enum value (24" width)."""
        assert SoundbarType.COMPACT.value == "compact"

    def test_standard_enum_value(self) -> None:
        """Test STANDARD enum value (36" width)."""
        assert SoundbarType.STANDARD.value == "standard"

    def test_premium_enum_value(self) -> None:
        """Test PREMIUM enum value (48"+ width)."""
        assert SoundbarType.PREMIUM.value == "premium"

    def test_custom_soundbar_enum_value(self) -> None:
        """Test CUSTOM enum value."""
        assert SoundbarType.CUSTOM.value == "custom"


class TestSpeakerTypeEnum:
    """Tests for SpeakerType enum."""

    def test_speaker_type_exists(self) -> None:
        """Test that SpeakerType enum exists."""
        assert SpeakerType is not None

    def test_speaker_type_values(self) -> None:
        """Test that all expected speaker types are present."""
        expected_values = {"center_channel", "bookshelf", "subwoofer"}
        actual_values = {member.value for member in SpeakerType}
        assert actual_values == expected_values

    def test_center_channel_enum_value(self) -> None:
        """Test CENTER_CHANNEL enum value."""
        assert SpeakerType.CENTER_CHANNEL.value == "center_channel"

    def test_bookshelf_enum_value(self) -> None:
        """Test BOOKSHELF enum value."""
        assert SpeakerType.BOOKSHELF.value == "bookshelf"

    def test_subwoofer_enum_value(self) -> None:
        """Test SUBWOOFER enum value."""
        assert SpeakerType.SUBWOOFER.value == "subwoofer"


# =============================================================================
# Task 02: Equipment Presets Tests
# =============================================================================


class TestEquipmentPresets:
    """Tests for EQUIPMENT_PRESETS dictionary."""

    def test_presets_contains_expected_equipment(self) -> None:
        """Test that all expected equipment types have presets."""
        expected_types = {
            "receiver",
            "console_horizontal",
            "console_vertical",
            "streaming",
            "cable_box",
            "blu_ray",
            "turntable",
        }
        assert set(EQUIPMENT_PRESETS.keys()) == expected_types

    def test_receiver_dimensions(self) -> None:
        """Test receiver preset dimensions (17.5" x 7" x 18")."""
        w, h, d = EQUIPMENT_PRESETS["receiver"]
        assert w == 17.5
        assert h == 7.0
        assert d == 18.0

    def test_console_horizontal_dimensions(self) -> None:
        """Test console horizontal preset dimensions."""
        w, h, d = EQUIPMENT_PRESETS["console_horizontal"]
        assert w == 16.0
        assert h == 4.0
        assert d == 12.0

    def test_console_vertical_dimensions(self) -> None:
        """Test console vertical preset dimensions."""
        w, h, d = EQUIPMENT_PRESETS["console_vertical"]
        assert w == 8.0
        assert h == 12.0
        assert d == 8.0

    def test_streaming_dimensions(self) -> None:
        """Test streaming device preset dimensions."""
        w, h, d = EQUIPMENT_PRESETS["streaming"]
        assert w == 6.0
        assert h == 2.0
        assert d == 4.0

    def test_cable_box_dimensions(self) -> None:
        """Test cable box preset dimensions."""
        w, h, d = EQUIPMENT_PRESETS["cable_box"]
        assert w == 12.0
        assert h == 3.0
        assert d == 10.0

    def test_blu_ray_dimensions(self) -> None:
        """Test Blu-ray player preset dimensions."""
        w, h, d = EQUIPMENT_PRESETS["blu_ray"]
        assert w == 14.0
        assert h == 3.0
        assert d == 10.0

    def test_turntable_dimensions(self) -> None:
        """Test turntable preset dimensions."""
        w, h, d = EQUIPMENT_PRESETS["turntable"]
        assert w == 18.0
        assert h == 6.0
        assert d == 14.0


class TestHeatGeneratingEquipment:
    """Tests for HEAT_GENERATING_EQUIPMENT set."""

    def test_heat_generating_equipment_contains_expected_types(self) -> None:
        """Test that heat-generating equipment set contains correct types."""
        expected = {"receiver", "console_horizontal", "console_vertical", "cable_box"}
        assert HEAT_GENERATING_EQUIPMENT == expected

    def test_receiver_generates_heat(self) -> None:
        """Test that receiver is in heat-generating set."""
        assert "receiver" in HEAT_GENERATING_EQUIPMENT

    def test_console_horizontal_generates_heat(self) -> None:
        """Test that horizontal console is in heat-generating set."""
        assert "console_horizontal" in HEAT_GENERATING_EQUIPMENT

    def test_console_vertical_generates_heat(self) -> None:
        """Test that vertical console is in heat-generating set."""
        assert "console_vertical" in HEAT_GENERATING_EQUIPMENT

    def test_cable_box_generates_heat(self) -> None:
        """Test that cable box is in heat-generating set."""
        assert "cable_box" in HEAT_GENERATING_EQUIPMENT

    def test_streaming_does_not_generate_heat(self) -> None:
        """Test that streaming device is NOT in heat-generating set."""
        assert "streaming" not in HEAT_GENERATING_EQUIPMENT

    def test_blu_ray_does_not_generate_heat(self) -> None:
        """Test that Blu-ray player is NOT in heat-generating set."""
        assert "blu_ray" not in HEAT_GENERATING_EQUIPMENT

    def test_turntable_does_not_generate_heat(self) -> None:
        """Test that turntable is NOT in heat-generating set."""
        assert "turntable" not in HEAT_GENERATING_EQUIPMENT


# =============================================================================
# Task 02: Clearance Constants Tests
# =============================================================================


class TestClearanceConstants:
    """Tests for media clearance constants."""

    def test_min_equipment_depth(self) -> None:
        """Test MIN_EQUIPMENT_DEPTH is 12.0 inches."""
        assert MIN_EQUIPMENT_DEPTH == 12.0

    def test_recommended_equipment_depth(self) -> None:
        """Test RECOMMENDED_EQUIPMENT_DEPTH is 16.0 inches."""
        assert RECOMMENDED_EQUIPMENT_DEPTH == 16.0

    def test_min_vertical_clearance(self) -> None:
        """Test MIN_VERTICAL_CLEARANCE is 2.0 inches."""
        assert MIN_VERTICAL_CLEARANCE == 2.0

    def test_heat_source_clearance(self) -> None:
        """Test HEAT_SOURCE_CLEARANCE is 8.0 inches."""
        assert HEAT_SOURCE_CLEARANCE == 8.0


# =============================================================================
# Task 02: VentilationSpec Dataclass Tests
# =============================================================================


class TestVentilationSpec:
    """Tests for VentilationSpec dataclass."""

    def test_create_passive_rear_ventilation(self) -> None:
        """Test creating a passive rear ventilation spec."""
        spec = VentilationSpec(ventilation_type="passive_rear")
        assert spec.ventilation_type == "passive_rear"
        assert spec.vent_pattern == "grid"
        assert spec.open_area_percent == 30.0
        assert spec.fan_size_mm is None

    def test_create_passive_with_custom_pattern(self) -> None:
        """Test creating passive ventilation with custom pattern."""
        spec = VentilationSpec(ventilation_type="passive_rear", vent_pattern="slot")
        assert spec.vent_pattern == "slot"

    def test_create_passive_with_mesh_pattern(self) -> None:
        """Test creating passive ventilation with mesh pattern."""
        spec = VentilationSpec(ventilation_type="passive_rear", vent_pattern="mesh")
        assert spec.vent_pattern == "mesh"

    def test_create_active_fan_ventilation_80mm(self) -> None:
        """Test creating active fan ventilation with 80mm fan."""
        spec = VentilationSpec(ventilation_type="active_fan", fan_size_mm=80)
        assert spec.ventilation_type == "active_fan"
        assert spec.fan_size_mm == 80

    def test_create_active_fan_ventilation_120mm(self) -> None:
        """Test creating active fan ventilation with 120mm fan."""
        spec = VentilationSpec(ventilation_type="active_fan", fan_size_mm=120)
        assert spec.fan_size_mm == 120

    def test_create_no_ventilation(self) -> None:
        """Test creating spec with no ventilation."""
        spec = VentilationSpec(ventilation_type="none")
        assert spec.ventilation_type == "none"

    def test_invalid_open_area_percent_negative(self) -> None:
        """Test that negative open area percent raises ValueError."""
        with pytest.raises(ValueError, match="open_area_percent must be between"):
            VentilationSpec(ventilation_type="passive_rear", open_area_percent=-10)

    def test_invalid_open_area_percent_over_100(self) -> None:
        """Test that open area percent over 100 raises ValueError."""
        with pytest.raises(ValueError, match="open_area_percent must be between"):
            VentilationSpec(ventilation_type="passive_rear", open_area_percent=150)

    def test_invalid_fan_size(self) -> None:
        """Test that non-standard fan size raises ValueError."""
        with pytest.raises(ValueError, match="fan_size_mm must be 80 or 120"):
            VentilationSpec(ventilation_type="active_fan", fan_size_mm=60)

    def test_ventilation_spec_is_frozen(self) -> None:
        """Test that VentilationSpec is immutable."""
        spec = VentilationSpec(ventilation_type="passive_rear")
        with pytest.raises(AttributeError):
            spec.ventilation_type = "none"  # type: ignore


# =============================================================================
# Task 02: EquipmentSpec Dataclass Tests
# =============================================================================


class TestEquipmentSpec:
    """Tests for EquipmentSpec dataclass."""

    def test_create_equipment_spec(self) -> None:
        """Test creating a basic equipment spec."""
        spec = EquipmentSpec(
            equipment_type="receiver",
            width=17.5,
            height=7.0,
            depth=18.0,
            generates_heat=True,
            required_clearance=8.0,
        )
        assert spec.equipment_type == "receiver"
        assert spec.width == 17.5
        assert spec.height == 7.0
        assert spec.depth == 18.0
        assert spec.generates_heat is True
        assert spec.required_clearance == 8.0

    def test_create_non_heat_equipment_spec(self) -> None:
        """Test creating equipment spec that doesn't generate heat."""
        spec = EquipmentSpec(
            equipment_type="turntable",
            width=18.0,
            height=6.0,
            depth=14.0,
            generates_heat=False,
            required_clearance=2.0,
        )
        assert spec.generates_heat is False
        assert spec.required_clearance == 2.0

    def test_invalid_zero_width(self) -> None:
        """Test that zero width raises ValueError."""
        with pytest.raises(ValueError, match="dimensions must be positive"):
            EquipmentSpec(
                equipment_type="test",
                width=0,
                height=5.0,
                depth=5.0,
                generates_heat=False,
                required_clearance=2.0,
            )

    def test_invalid_negative_height(self) -> None:
        """Test that negative height raises ValueError."""
        with pytest.raises(ValueError, match="dimensions must be positive"):
            EquipmentSpec(
                equipment_type="test",
                width=5.0,
                height=-1.0,
                depth=5.0,
                generates_heat=False,
                required_clearance=2.0,
            )

    def test_invalid_negative_clearance(self) -> None:
        """Test that negative clearance raises ValueError."""
        with pytest.raises(ValueError, match="clearance cannot be negative"):
            EquipmentSpec(
                equipment_type="test",
                width=5.0,
                height=5.0,
                depth=5.0,
                generates_heat=False,
                required_clearance=-1.0,
            )

    def test_equipment_spec_is_frozen(self) -> None:
        """Test that EquipmentSpec is immutable."""
        spec = EquipmentSpec(
            equipment_type="receiver",
            width=17.5,
            height=7.0,
            depth=18.0,
            generates_heat=True,
            required_clearance=8.0,
        )
        with pytest.raises(AttributeError):
            spec.width = 20.0  # type: ignore


# =============================================================================
# Task 02: _get_equipment_spec Helper Tests
# =============================================================================


class TestGetEquipmentSpec:
    """Tests for _get_equipment_spec helper function."""

    def test_get_receiver_spec(self) -> None:
        """Test getting receiver spec from presets."""
        spec = _get_equipment_spec("receiver")
        assert spec.equipment_type == "receiver"
        assert spec.width == 17.5
        assert spec.height == 7.0
        assert spec.depth == 18.0
        assert spec.generates_heat is True
        assert spec.required_clearance == HEAT_SOURCE_CLEARANCE

    def test_get_streaming_spec(self) -> None:
        """Test getting streaming device spec (non-heat-generating)."""
        spec = _get_equipment_spec("streaming")
        assert spec.equipment_type == "streaming"
        assert spec.generates_heat is False
        assert spec.required_clearance == MIN_VERTICAL_CLEARANCE

    def test_get_custom_spec(self) -> None:
        """Test getting custom equipment spec."""
        custom_dims = {
            "width": 20.0,
            "height": 8.0,
            "depth": 16.0,
            "generates_heat": True,
            "clearance": 10.0,
        }
        spec = _get_equipment_spec("custom", custom_dims)
        assert spec.equipment_type == "custom"
        assert spec.width == 20.0
        assert spec.height == 8.0
        assert spec.depth == 16.0
        assert spec.generates_heat is True
        assert spec.required_clearance == 10.0

    def test_get_custom_spec_with_defaults(self) -> None:
        """Test getting custom spec with some default values."""
        custom_dims = {"width": 15.0}
        spec = _get_equipment_spec("custom", custom_dims)
        assert spec.width == 15.0
        assert spec.height == 6.0  # default
        assert spec.depth == 14.0  # default
        assert spec.generates_heat is False  # default
        assert spec.required_clearance == MIN_VERTICAL_CLEARANCE  # default

    def test_get_unknown_equipment_fallback(self) -> None:
        """Test that unknown equipment type returns default fallback."""
        spec = _get_equipment_spec("unknown_device")
        assert spec.equipment_type == "unknown"
        assert spec.generates_heat is False


# =============================================================================
# Task 02: Component Registration Tests
# =============================================================================


class TestMediaComponentRegistration:
    """Tests for media component registration in component_registry."""

    def test_equipment_shelf_is_registered(self) -> None:
        """Test that media.equipment_shelf is registered."""
        assert "media.equipment_shelf" in component_registry.list()

    def test_ventilated_section_is_registered(self) -> None:
        """Test that media.ventilated_section is registered."""
        assert "media.ventilated_section" in component_registry.list()

    def test_soundbar_shelf_is_registered(self) -> None:
        """Test that media.soundbar_shelf is registered."""
        assert "media.soundbar_shelf" in component_registry.list()

    def test_speaker_alcove_is_registered(self) -> None:
        """Test that media.speaker_alcove is registered."""
        assert "media.speaker_alcove" in component_registry.list()

    def test_get_equipment_shelf_component(self) -> None:
        """Test that registry returns correct equipment shelf component class."""
        component_class = component_registry.get("media.equipment_shelf")
        assert component_class is EquipmentShelfComponent

    def test_get_ventilated_section_component(self) -> None:
        """Test that registry returns correct ventilated section component class."""
        component_class = component_registry.get("media.ventilated_section")
        assert component_class is VentilatedSectionComponent

    def test_get_soundbar_shelf_component(self) -> None:
        """Test that registry returns correct soundbar shelf component class."""
        component_class = component_registry.get("media.soundbar_shelf")
        assert component_class is SoundbarShelfComponent

    def test_get_speaker_alcove_component(self) -> None:
        """Test that registry returns correct speaker alcove component class."""
        component_class = component_registry.get("media.speaker_alcove")
        assert component_class is SpeakerAlcoveComponent


# =============================================================================
# Component Context Fixture
# =============================================================================


@pytest.fixture
def standard_context() -> ComponentContext:
    """Create a standard ComponentContext for testing media components.

    Returns a context representing a 24" wide section with 36" height
    and 18" depth - suitable for most media equipment.
    """
    return ComponentContext(
        width=24.0,
        height=36.0,
        depth=18.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=72.0,
        cabinet_depth=20.0,
    )


@pytest.fixture
def shallow_context() -> ComponentContext:
    """Create a shallow context for testing depth validation."""
    return ComponentContext(
        width=24.0,
        height=36.0,
        depth=10.0,  # Too shallow for equipment
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=72.0,
        cabinet_depth=12.0,
    )


@pytest.fixture
def narrow_context() -> ComponentContext:
    """Create a narrow context for testing width validation."""
    return ComponentContext(
        width=12.0,  # Narrower than receiver width
        height=36.0,
        depth=18.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0.75, 0.75),
        section_index=0,
        cabinet_width=24.0,
        cabinet_height=72.0,
        cabinet_depth=20.0,
    )


# =============================================================================
# EquipmentShelfComponent Tests
# =============================================================================


class TestEquipmentShelfComponentValidation:
    """Tests for EquipmentShelfComponent.validate()."""

    @pytest.fixture
    def component(self) -> EquipmentShelfComponent:
        """Create an EquipmentShelfComponent instance."""
        return EquipmentShelfComponent()

    def test_validate_returns_ok_for_valid_config(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid equipment shelf config."""
        config = {"equipment_type": "receiver"}
        result = component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_shallow_depth_error(
        self, component: EquipmentShelfComponent, shallow_context: ComponentContext
    ) -> None:
        """Test that shallow depth generates error."""
        config = {"equipment_type": "receiver"}
        result = component.validate(config, shallow_context)
        assert not result.is_valid
        assert any("too shallow" in err for err in result.errors)

    def test_validate_marginal_depth_warning(
        self, component: EquipmentShelfComponent
    ) -> None:
        """Test that marginal depth generates warning."""
        context = ComponentContext(
            width=24.0,
            height=36.0,
            depth=14.0,  # Between MIN and RECOMMENDED
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=72.0,
            cabinet_depth=16.0,
        )
        config = {"equipment_type": "receiver"}
        result = component.validate(config, context)
        assert result.is_valid  # Should still be valid
        assert len(result.warnings) > 0
        assert any("may be tight" in warn for warn in result.warnings)

    def test_validate_equipment_too_wide_error(
        self, component: EquipmentShelfComponent, narrow_context: ComponentContext
    ) -> None:
        """Test that equipment too wide for section generates error."""
        config = {"equipment_type": "receiver"}  # 17.5" wide
        result = component.validate(config, narrow_context)
        assert not result.is_valid
        assert any("exceeds section width" in err for err in result.errors)

    def test_validate_heat_generating_equipment_warning(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that heat-generating equipment with low clearance generates warning."""
        config = {
            "equipment_type": "receiver",
            "vertical_clearance": 10.0,  # 10 - 7 (receiver height) = 3" clearance
        }
        result = component.validate(config, standard_context)
        # Should have warning about heat clearance
        assert len(result.warnings) > 0
        assert any("heat" in warn.lower() for warn in result.warnings)


class TestEquipmentShelfComponentGeneration:
    """Tests for EquipmentShelfComponent.generate()."""

    @pytest.fixture
    def component(self) -> EquipmentShelfComponent:
        """Create an EquipmentShelfComponent instance."""
        return EquipmentShelfComponent()

    def test_generate_returns_generation_result(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate returns a GenerationResult instance."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        assert isinstance(result, GenerationResult)

    def test_generate_creates_shelf_panel(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates a shelf panel."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        assert len(result.panels) >= 1
        shelf_panels = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelf_panels) == 1

    def test_generate_includes_grommet_hardware(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes cable grommet hardware."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) >= 1

    def test_generate_includes_cable_management_hardware(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes cable tie mount hardware."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        cable_items = [h for h in result.hardware if "Cable" in h.name]
        assert len(cable_items) >= 1

    def test_generate_metadata_includes_equipment_type(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes equipment type."""
        config = {"equipment_type": "blu_ray"}
        result = component.generate(config, standard_context)
        assert result.metadata["equipment_type"] == "blu_ray"

    def test_generate_metadata_includes_heat_info(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes heat generation info."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        assert result.metadata["generates_heat"] is True

    # Task 03: Additional tests for specific requirements

    def test_generate_shelf_panel_has_required_metadata_fields(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf panel has all required metadata fields."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        shelf_panel = next(p for p in result.panels if p.panel_type == PanelType.SHELF)
        # Verify all required metadata fields
        assert shelf_panel.metadata["component"] == "media.equipment_shelf"
        assert shelf_panel.metadata["equipment_type"] == "receiver"
        assert shelf_panel.metadata["is_equipment_shelf"] is True
        assert shelf_panel.metadata["generates_heat"] is True

    def test_generate_grommet_cutout_center_rear_position(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test grommet cutout position for center_rear."""
        config = {"equipment_type": "receiver", "grommet_position": "center_rear"}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        # Center should be at width/2
        assert cutout.position.x == standard_context.width / 2

    def test_generate_grommet_cutout_left_rear_position(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test grommet cutout position for left_rear."""
        config = {"equipment_type": "receiver", "grommet_position": "left_rear"}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        # Left rear should be at 25% of width
        assert cutout.position.x == standard_context.width * 0.25

    def test_generate_grommet_cutout_right_rear_position(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test grommet cutout position for right_rear."""
        config = {"equipment_type": "receiver", "grommet_position": "right_rear"}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        # Right rear should be at 75% of width
        assert cutout.position.x == standard_context.width * 0.75

    def test_generate_grommet_cutout_is_circular(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that grommet cutout uses CutoutShape.CIRCULAR."""
        from cabinets.domain.value_objects import CutoutShape

        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        assert cutout.shape == CutoutShape.CIRCULAR
        assert cutout.cutout_type == "cable_grommet"

    def test_generate_grommet_custom_diameter(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that grommet diameter can be customized."""
        config = {"equipment_type": "receiver", "grommet_diameter": 3.0}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        assert cutout.diameter == 3.0
        # Hardware should reflect the diameter
        grommet_item = next(h for h in result.hardware if "Grommet" in h.name)
        assert '3.0"' in grommet_item.name

    def test_generate_cable_tie_mount_hardware_details(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test cable tie mount hardware has correct quantity and SKU."""
        config = {"equipment_type": "receiver"}
        result = component.generate(config, standard_context)
        cable_tie_item = next(h for h in result.hardware if "Cable Tie Mount" in h.name)
        assert cable_tie_item.quantity == 4
        assert cable_tie_item.sku == "CABLE-TIE-MOUNT"

    def test_generate_grommet_hardware_sku_based_on_diameter(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test grommet hardware SKU is based on diameter."""
        config = {"equipment_type": "receiver", "grommet_diameter": 2.5}
        result = component.generate(config, standard_context)
        grommet_item = next(h for h in result.hardware if "Grommet" in h.name)
        assert grommet_item.quantity == 1
        assert grommet_item.sku == "GROMMET-2"  # 2.5 rounds to 2


class TestEquipmentShelfHardwareMethod:
    """Tests for EquipmentShelfComponent.hardware() method."""

    @pytest.fixture
    def component(self) -> EquipmentShelfComponent:
        """Create an EquipmentShelfComponent instance."""
        return EquipmentShelfComponent()

    def test_hardware_returns_list_of_hardware_items(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns a list of HardwareItem objects."""
        from cabinets.domain.components.results import HardwareItem

        config = {"equipment_type": "receiver"}
        hardware = component.hardware(config, standard_context)
        assert isinstance(hardware, list)
        assert len(hardware) >= 2  # At least grommet and cable tie mounts
        for item in hardware:
            assert isinstance(item, HardwareItem)

    def test_hardware_includes_grommet_and_cable_ties(
        self, component: EquipmentShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware includes both grommet and cable tie mounts."""
        config = {"equipment_type": "receiver"}
        hardware = component.hardware(config, standard_context)
        hardware_names = [h.name for h in hardware]
        assert any("Grommet" in name for name in hardware_names)
        assert any("Cable Tie Mount" in name for name in hardware_names)


# =============================================================================
# VentilatedSectionComponent Tests
# =============================================================================


class TestVentilatedSectionComponentValidation:
    """Tests for VentilatedSectionComponent.validate()."""

    @pytest.fixture
    def component(self) -> VentilatedSectionComponent:
        """Create a VentilatedSectionComponent instance."""
        return VentilatedSectionComponent()

    def test_validate_returns_ok_for_valid_config(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid ventilated section config."""
        config = {"ventilation_type": "passive_rear", "has_equipment": True}
        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_enclosed_without_ventilation_error(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosed equipment without ventilation generates error."""
        config = {
            "ventilation_type": "none",
            "has_equipment": True,
            "enclosed": True,
        }
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("require ventilation" in err for err in result.errors)

    def test_validate_non_standard_fan_size_warning(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that non-standard fan size generates warning."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 60}
        result = component.validate(config, standard_context)
        assert len(result.warnings) > 0
        assert any("Non-standard fan size" in warn for warn in result.warnings)


class TestVentilatedSectionComponentValidation80mmFan:
    """Additional validation tests for 80mm fan size."""

    @pytest.fixture
    def component(self) -> VentilatedSectionComponent:
        """Create a VentilatedSectionComponent instance."""
        return VentilatedSectionComponent()

    def test_validate_80mm_fan_is_valid(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 80mm fan size is accepted without warnings."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 80}
        result = component.validate(config, standard_context)
        assert result.is_valid
        # No warnings about fan size
        assert not any("fan size" in warn.lower() for warn in result.warnings)

    def test_validate_120mm_fan_is_valid(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 120mm fan size is accepted without warnings."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.validate(config, standard_context)
        assert result.is_valid
        # No warnings about fan size
        assert not any("fan size" in warn.lower() for warn in result.warnings)


class TestVentilatedSectionComponentGeneration:
    """Tests for VentilatedSectionComponent.generate()."""

    @pytest.fixture
    def component(self) -> VentilatedSectionComponent:
        """Create a VentilatedSectionComponent instance."""
        return VentilatedSectionComponent()

    def test_generate_passive_rear_creates_back_panel(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that passive_rear generates back panel with ventilation."""
        config = {"ventilation_type": "passive_rear"}
        result = component.generate(config, standard_context)
        back_panels = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(back_panels) == 1
        assert back_panels[0].metadata.get("requires_vent_cutout") is True

    def test_generate_active_fan_includes_fan_hardware(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that active_fan generates fan hardware."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.generate(config, standard_context)
        fan_items = [h for h in result.hardware if "Fan" in h.name]
        assert len(fan_items) >= 1

    # Task 04: Additional tests for specific requirements

    def test_generate_passive_rear_back_panel_metadata(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that passive_rear back panel has all required metadata."""
        config = {"ventilation_type": "passive_rear", "vent_pattern": "grid"}
        result = component.generate(config, standard_context)
        back_panel = next(p for p in result.panels if p.panel_type == PanelType.BACK)
        assert back_panel.metadata["component"] == "media.ventilated_section"
        assert back_panel.metadata["ventilation_type"] == "passive_rear"
        assert back_panel.metadata["vent_pattern"] == "grid"
        assert back_panel.metadata["requires_vent_cutout"] is True

    def test_generate_passive_rear_slot_pattern(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that slot pattern is recorded in back panel metadata."""
        config = {"ventilation_type": "passive_rear", "vent_pattern": "slot"}
        result = component.generate(config, standard_context)
        back_panel = next(p for p in result.panels if p.panel_type == PanelType.BACK)
        assert back_panel.metadata["vent_pattern"] == "slot"

    def test_generate_passive_rear_grille_hardware(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that passive_rear includes ventilation grille hardware."""
        config = {"ventilation_type": "passive_rear"}
        result = component.generate(config, standard_context)
        grille_items = [h for h in result.hardware if "Grille" in h.name]
        assert len(grille_items) == 1
        assert grille_items[0].sku == "VENT-GRILLE-RECT"

    def test_generate_active_fan_80mm_cutout_size(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 80mm fan generates correctly sized cutout in inches."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 80}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        # 80mm = ~3.15 inches
        expected_size_inches = 80 / 25.4
        assert abs(cutout.diameter - expected_size_inches) < 0.01

    def test_generate_active_fan_120mm_cutout_size(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 120mm fan generates correctly sized cutout in inches."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        # 120mm = ~4.72 inches
        expected_size_inches = 120 / 25.4
        assert abs(cutout.diameter - expected_size_inches) < 0.01

    def test_generate_active_fan_cutout_is_circular(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that fan cutout uses CutoutShape.CIRCULAR."""
        from cabinets.domain.value_objects import CutoutShape

        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        assert cutout.shape == CutoutShape.CIRCULAR
        assert cutout.cutout_type == "cooling_fan"

    def test_generate_active_fan_cutout_centered(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that fan cutout is centered on the back panel."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.generate(config, standard_context)
        cutouts = result.metadata.get("cutouts", [])
        assert len(cutouts) == 1
        cutout = cutouts[0]
        # Should be centered
        assert cutout.position.x == standard_context.width / 2
        assert cutout.position.y == standard_context.height / 2

    def test_generate_active_fan_hardware_sku_80mm(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 80mm fan has correct SKU."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 80}
        result = component.generate(config, standard_context)
        fan_item = next(h for h in result.hardware if "Cooling Fan" in h.name)
        assert fan_item.sku == "FAN-80MM-QUIET"
        assert fan_item.quantity == 1

    def test_generate_active_fan_hardware_sku_120mm(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that 120mm fan has correct SKU."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.generate(config, standard_context)
        fan_item = next(h for h in result.hardware if "Cooling Fan" in h.name)
        assert fan_item.sku == "FAN-120MM-QUIET"
        assert fan_item.quantity == 1

    def test_generate_active_fan_power_adapter_hardware(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that active_fan includes power adapter hardware."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        result = component.generate(config, standard_context)
        adapter_items = [h for h in result.hardware if "Power Adapter" in h.name]
        assert len(adapter_items) == 1
        assert adapter_items[0].sku == "FAN-PWR-USB"
        assert adapter_items[0].quantity == 1

    def test_generate_metadata_includes_ventilation_type(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes ventilation type."""
        config = {"ventilation_type": "passive_rear"}
        result = component.generate(config, standard_context)
        assert result.metadata["ventilation_type"] == "passive_rear"

    def test_generate_metadata_includes_vent_pattern(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that metadata includes vent pattern."""
        config = {"ventilation_type": "passive_rear", "vent_pattern": "mesh"}
        result = component.generate(config, standard_context)
        assert result.metadata["vent_pattern"] == "mesh"


class TestVentilatedSectionHardwareMethod:
    """Tests for VentilatedSectionComponent.hardware() method."""

    @pytest.fixture
    def component(self) -> VentilatedSectionComponent:
        """Create a VentilatedSectionComponent instance."""
        return VentilatedSectionComponent()

    def test_hardware_returns_list_of_hardware_items(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns a list of HardwareItem objects."""
        from cabinets.domain.components.results import HardwareItem

        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        hardware = component.hardware(config, standard_context)
        assert isinstance(hardware, list)
        for item in hardware:
            assert isinstance(item, HardwareItem)

    def test_hardware_passive_rear_returns_grille(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware for passive_rear includes grille."""
        config = {"ventilation_type": "passive_rear"}
        hardware = component.hardware(config, standard_context)
        hardware_names = [h.name for h in hardware]
        assert any("Grille" in name for name in hardware_names)

    def test_hardware_active_fan_returns_fan_and_adapter(
        self, component: VentilatedSectionComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware for active_fan includes fan and adapter."""
        config = {"ventilation_type": "active_fan", "fan_size_mm": 120}
        hardware = component.hardware(config, standard_context)
        hardware_names = [h.name for h in hardware]
        assert any("Cooling Fan" in name for name in hardware_names)
        assert any("Power Adapter" in name for name in hardware_names)


# =============================================================================
# SoundbarShelfComponent Tests
# =============================================================================


class TestSoundbarShelfComponentValidation:
    """Tests for SoundbarShelfComponent.validate()."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_validate_returns_ok_for_open_shelf(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for open soundbar shelf."""
        config = {"soundbar_type": "standard", "enclosed": False}
        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_enclosed_soundbar_error(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosed soundbar generates error."""
        config = {"soundbar_type": "standard", "enclosed": True}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("muffled" in err for err in result.errors)

    def test_validate_low_side_clearance_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that low side clearance generates warning."""
        config = {"soundbar_type": "standard", "side_clearance": 4.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) > 0
        assert any("clearance" in warn for warn in result.warnings)

    def test_validate_atmos_low_ceiling_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that Atmos soundbar with low ceiling generates warning."""
        config = {
            "soundbar_type": "premium",
            "dolby_atmos": True,
            "ceiling_clearance": 18.0,
        }
        result = component.validate(config, standard_context)
        assert len(result.warnings) > 0
        assert any("Atmos" in warn for warn in result.warnings)


class TestSoundbarShelfComponentGeneration:
    """Tests for SoundbarShelfComponent.generate()."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_generate_creates_shelf_panel(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates a shelf panel."""
        config = {"soundbar_type": "standard"}
        result = component.generate(config, standard_context)
        shelf_panels = [p for p in result.panels if p.panel_type == PanelType.SHELF]
        assert len(shelf_panels) == 1

    def test_generate_marks_shelf_as_open_back(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generated shelf has open_back metadata."""
        config = {"soundbar_type": "standard"}
        result = component.generate(config, standard_context)
        shelf_panel = next(p for p in result.panels if p.panel_type == PanelType.SHELF)
        assert shelf_panel.metadata.get("open_back") is True

    def test_generate_with_mount_includes_hardware(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate with mount includes mounting hardware."""
        config = {"soundbar_type": "standard", "include_mount": True}
        result = component.generate(config, standard_context)
        mount_items = [h for h in result.hardware if "Mount" in h.name]
        assert len(mount_items) >= 1


# =============================================================================
# SpeakerAlcoveComponent Tests
# =============================================================================


class TestSpeakerAlcoveComponentValidation:
    """Tests for SpeakerAlcoveComponent.validate()."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_validate_returns_ok_for_valid_config(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that validate returns ok for valid speaker alcove config."""
        config = {"speaker_type": "center_channel", "alcove_height_from_floor": 36.0}
        result = component.validate(config, standard_context)
        assert result.is_valid

    def test_validate_center_channel_low_placement_warning(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that low center channel placement generates warning."""
        config = {"speaker_type": "center_channel", "alcove_height_from_floor": 24.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) > 0
        assert any("ear level" in warn for warn in result.warnings)

    def test_validate_subwoofer_port_clearance_error(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that subwoofer with insufficient port clearance generates error."""
        config = {"speaker_type": "subwoofer", "port_clearance": 2.0}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert any("port clearance" in err for err in result.errors)


class TestSpeakerAlcoveComponentGeneration:
    """Tests for SpeakerAlcoveComponent.generate()."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_generate_creates_alcove_panels(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate creates side and bottom panels for alcove."""
        config = {"speaker_type": "center_channel"}
        result = component.generate(config, standard_context)
        # Should have 2 side panels + 1 bottom panel
        assert len(result.panels) == 3

    def test_generate_includes_dampening_hardware(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate includes acoustic dampening hardware."""
        config = {"speaker_type": "center_channel", "include_dampening": True}
        result = component.generate(config, standard_context)
        foam_items = [h for h in result.hardware if "Foam" in h.name]
        assert len(foam_items) >= 1

    def test_generate_without_dampening_no_foam(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that generate without dampening excludes foam hardware."""
        config = {"speaker_type": "bookshelf", "include_dampening": False}
        result = component.generate(config, standard_context)
        foam_items = [h for h in result.hardware if "Foam" in h.name]
        assert len(foam_items) == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestMediaComponentIntegration:
    """Integration tests for media components."""

    def test_full_workflow_equipment_shelf(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow: get component, validate, generate, hardware."""
        # Get component from registry
        component_class = component_registry.get("media.equipment_shelf")
        component = component_class()

        config = {
            "equipment_type": "receiver",
            "grommet_position": "center_rear",
        }

        # Validate
        validation = component.validate(config, standard_context)
        assert validation.is_valid

        # Generate
        generation = component.generate(config, standard_context)
        assert len(generation.panels) >= 1

        # Hardware
        hardware = component.hardware(config, standard_context)
        assert len(hardware) >= 1

    def test_full_workflow_ventilated_section(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for ventilated section."""
        component_class = component_registry.get("media.ventilated_section")
        component = component_class()

        config = {
            "ventilation_type": "passive_rear",
            "vent_pattern": "grid",
            "has_equipment": True,
        }

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) >= 1

    def test_full_workflow_soundbar_shelf(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for soundbar shelf."""
        component_class = component_registry.get("media.soundbar_shelf")
        component = component_class()

        config = {
            "soundbar_type": "premium",
            "dolby_atmos": False,
            "include_mount": True,
        }

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) >= 1
        assert len(generation.hardware) >= 1

    def test_full_workflow_speaker_alcove(
        self, standard_context: ComponentContext
    ) -> None:
        """Test complete workflow for speaker alcove."""
        component_class = component_registry.get("media.speaker_alcove")
        component = component_class()

        config = {
            "speaker_type": "center_channel",
            "alcove_height_from_floor": 40.0,
            "include_dampening": True,
        }

        validation = component.validate(config, standard_context)
        assert validation.is_valid

        generation = component.generate(config, standard_context)
        assert len(generation.panels) == 3  # 2 sides + bottom
        assert len(generation.hardware) >= 1  # acoustic foam


# =============================================================================
# Task 05: Soundbar Shelf Component - Comprehensive Tests (FRD-19 Phase 3)
# =============================================================================


class TestSoundbarPresetDimensions:
    """Tests for SOUNDBAR_PRESETS dictionary values."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_soundbar_presets_compact_dimensions(
        self, component: SoundbarShelfComponent
    ) -> None:
        """Test compact soundbar preset dimensions (24.0, 3.0, 3.0)."""
        assert "compact" in component.SOUNDBAR_PRESETS
        w, h, d = component.SOUNDBAR_PRESETS["compact"]
        assert w == 24.0
        assert h == 3.0
        assert d == 3.0

    def test_soundbar_presets_standard_dimensions(
        self, component: SoundbarShelfComponent
    ) -> None:
        """Test standard soundbar preset dimensions (36.0, 3.0, 4.0)."""
        assert "standard" in component.SOUNDBAR_PRESETS
        w, h, d = component.SOUNDBAR_PRESETS["standard"]
        assert w == 36.0
        assert h == 3.0
        assert d == 4.0

    def test_soundbar_presets_premium_dimensions(
        self, component: SoundbarShelfComponent
    ) -> None:
        """Test premium soundbar preset dimensions (48.0, 4.0, 5.0)."""
        assert "premium" in component.SOUNDBAR_PRESETS
        w, h, d = component.SOUNDBAR_PRESETS["premium"]
        assert w == 48.0
        assert h == 4.0
        assert d == 5.0


class TestSoundbarEnclosureValidation:
    """Tests for soundbar enclosure validation - must not be enclosed."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_enclosed_soundbar_generates_error(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosed=True generates specific ERROR message."""
        config = {"soundbar_type": "standard", "enclosed": True}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "Soundbars must not be enclosed" in result.errors[0]
        assert "sound will be muffled" in result.errors[0]

    def test_non_enclosed_soundbar_no_error(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that enclosed=False (default) does not generate error."""
        config = {"soundbar_type": "standard"}
        result = component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0


class TestSoundbarSideClearanceWarnings:
    """Tests for soundbar side clearance warning thresholds."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_side_clearance_below_6_inches_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side_clearance < 6 generates warning about sound projection."""
        config = {"soundbar_type": "standard", "side_clearance": 5.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("sound projection" in warn for warn in result.warnings)

    def test_side_clearance_exactly_6_inches_recommendation_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side_clearance >= 6 but < 12 generates optimal sound warning."""
        config = {"soundbar_type": "standard", "side_clearance": 6.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("12" in warn and "optimal" in warn for warn in result.warnings)

    def test_side_clearance_10_inches_recommendation_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side_clearance = 10 (between 6 and 12) recommends 12+."""
        config = {"soundbar_type": "standard", "side_clearance": 10.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("12" in warn for warn in result.warnings)

    def test_side_clearance_12_inches_no_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that side_clearance >= 12 generates no clearance warning."""
        config = {"soundbar_type": "standard", "side_clearance": 12.0}
        result = component.validate(config, standard_context)
        # No warnings about clearance
        assert not any("clearance" in warn for warn in result.warnings)


class TestSoundbarDolbyAtmosCeilingClearance:
    """Tests for Dolby Atmos ceiling clearance validation."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_dolby_atmos_ceiling_clearance_below_24_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test dolby_atmos=True with ceiling_clearance < 24 generates warning."""
        config = {
            "soundbar_type": "premium",
            "dolby_atmos": True,
            "ceiling_clearance": 20.0,
        }
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("Atmos height effects" in warn for warn in result.warnings)
        assert any("24" in warn for warn in result.warnings)

    def test_dolby_atmos_ceiling_clearance_exactly_24_no_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test dolby_atmos=True with ceiling_clearance = 24 generates no warning."""
        config = {
            "soundbar_type": "premium",
            "dolby_atmos": True,
            "ceiling_clearance": 24.0,
        }
        result = component.validate(config, standard_context)
        # No Atmos-related warnings
        assert not any("Atmos" in warn for warn in result.warnings)

    def test_non_atmos_soundbar_low_ceiling_no_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that non-Atmos soundbar with low ceiling generates no Atmos warning."""
        config = {
            "soundbar_type": "premium",
            "dolby_atmos": False,
            "ceiling_clearance": 18.0,
        }
        result = component.validate(config, standard_context)
        # No Atmos-related warnings
        assert not any("Atmos" in warn for warn in result.warnings)


class TestSoundbarBelowEquipmentWarning:
    """Tests for soundbar below_equipment warning."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_below_equipment_true_generates_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that below_equipment=True generates warning about blocked sound."""
        config = {"soundbar_type": "standard", "below_equipment": True}
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("blocked sound projection" in warn for warn in result.warnings)

    def test_below_equipment_false_no_warning(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that below_equipment=False generates no warning."""
        config = {"soundbar_type": "standard", "below_equipment": False}
        result = component.validate(config, standard_context)
        assert not any("blocked" in warn for warn in result.warnings)


class TestSoundbarShelfGenerationDetails:
    """Detailed tests for SoundbarShelfComponent.generate() method."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_shelf_panel_has_correct_metadata(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf panel has all required metadata fields."""
        config = {"soundbar_type": "compact"}
        result = component.generate(config, standard_context)
        shelf_panel = next(p for p in result.panels if p.panel_type == PanelType.SHELF)
        assert shelf_panel.metadata["component"] == "media.soundbar_shelf"
        assert shelf_panel.metadata["soundbar_type"] == "compact"
        assert shelf_panel.metadata["is_soundbar_shelf"] is True
        assert shelf_panel.metadata["open_back"] is True

    def test_shelf_depth_equals_soundbar_depth_plus_2(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that shelf depth = soundbar_depth + 2 for placement tolerance."""
        # Test compact (depth = 3.0)
        config = {"soundbar_type": "compact"}
        result = component.generate(config, standard_context)
        shelf_panel = next(p for p in result.panels if p.panel_type == PanelType.SHELF)
        assert shelf_panel.height == 3.0 + 2.0  # soundbar_depth + 2"

        # Test standard (depth = 4.0)
        config = {"soundbar_type": "standard"}
        result = component.generate(config, standard_context)
        shelf_panel = next(p for p in result.panels if p.panel_type == PanelType.SHELF)
        assert shelf_panel.height == 4.0 + 2.0  # soundbar_depth + 2"

        # Test premium (depth = 5.0)
        config = {"soundbar_type": "premium"}
        result = component.generate(config, standard_context)
        shelf_panel = next(p for p in result.panels if p.panel_type == PanelType.SHELF)
        assert shelf_panel.height == 5.0 + 2.0  # soundbar_depth + 2"

    def test_include_mount_adds_wall_mount_bracket_hardware(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that include_mount=True adds Soundbar Wall Mount Bracket hardware."""
        config = {"soundbar_type": "standard", "include_mount": True}
        result = component.generate(config, standard_context)
        mount_items = [
            h for h in result.hardware if "Soundbar Wall Mount Bracket" in h.name
        ]
        assert len(mount_items) == 1
        assert mount_items[0].sku == "SOUNDBAR-MOUNT-UNIV"
        assert mount_items[0].quantity == 1

    def test_include_mount_false_no_bracket_hardware(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that include_mount=False (default) adds no mount hardware."""
        config = {"soundbar_type": "standard", "include_mount": False}
        result = component.generate(config, standard_context)
        mount_items = [h for h in result.hardware if "Mount" in h.name]
        assert len(mount_items) == 0

    def test_metadata_includes_soundbar_dimensions(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that result metadata includes soundbar dimensions tuple."""
        config = {"soundbar_type": "premium"}
        result = component.generate(config, standard_context)
        assert result.metadata["soundbar_type"] == "premium"
        assert result.metadata["soundbar_dimensions"] == (48.0, 4.0, 5.0)
        assert result.metadata["open_back"] is True


class TestSoundbarShelfHardwareMethod:
    """Tests for SoundbarShelfComponent.hardware() method."""

    @pytest.fixture
    def component(self) -> SoundbarShelfComponent:
        """Create a SoundbarShelfComponent instance."""
        return SoundbarShelfComponent()

    def test_hardware_with_mount_returns_bracket(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns bracket when include_mount=True."""
        from cabinets.domain.components.results import HardwareItem

        config = {"soundbar_type": "standard", "include_mount": True}
        hardware = component.hardware(config, standard_context)
        assert isinstance(hardware, list)
        assert len(hardware) == 1
        assert hardware[0].name == "Soundbar Wall Mount Bracket"
        assert hardware[0].sku == "SOUNDBAR-MOUNT-UNIV"

    def test_hardware_without_mount_returns_empty(
        self, component: SoundbarShelfComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns empty list when include_mount=False."""
        config = {"soundbar_type": "standard", "include_mount": False}
        hardware = component.hardware(config, standard_context)
        assert isinstance(hardware, list)
        assert len(hardware) == 0


# =============================================================================
# Task 06: Speaker Alcove Component - Comprehensive Tests (FRD-19 Phase 3)
# =============================================================================


class TestSpeakerPresetDimensions:
    """Tests for SPEAKER_PRESETS dictionary values."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_speaker_presets_center_channel_dimensions(
        self, component: SpeakerAlcoveComponent
    ) -> None:
        """Test center_channel preset dimensions (24.0, 8.0, 12.0) - horizontal."""
        assert "center_channel" in component.SPEAKER_PRESETS
        w, h, d = component.SPEAKER_PRESETS["center_channel"]
        assert w == 24.0
        assert h == 8.0
        assert d == 12.0

    def test_speaker_presets_bookshelf_dimensions(
        self, component: SpeakerAlcoveComponent
    ) -> None:
        """Test bookshelf preset dimensions (8.0, 12.0, 10.0) - vertical."""
        assert "bookshelf" in component.SPEAKER_PRESETS
        w, h, d = component.SPEAKER_PRESETS["bookshelf"]
        assert w == 8.0
        assert h == 12.0
        assert d == 10.0

    def test_speaker_presets_subwoofer_dimensions(
        self, component: SpeakerAlcoveComponent
    ) -> None:
        """Test subwoofer preset dimensions (15.0, 15.0, 18.0)."""
        assert "subwoofer" in component.SPEAKER_PRESETS
        w, h, d = component.SPEAKER_PRESETS["subwoofer"]
        assert w == 15.0
        assert h == 15.0
        assert d == 18.0


class TestSpeakerMinSubwooferPortClearance:
    """Tests for MIN_SUBWOOFER_PORT_CLEARANCE constant."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_min_subwoofer_port_clearance_value(
        self, component: SpeakerAlcoveComponent
    ) -> None:
        """Test that MIN_SUBWOOFER_PORT_CLEARANCE equals 4.0 inches."""
        assert component.MIN_SUBWOOFER_PORT_CLEARANCE == 4.0


class TestSpeakerCenterChannelHeightValidation:
    """Tests for center channel speaker height validation."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_center_channel_below_30_inches_warning(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test center_channel at height < 30 generates below ear level warning."""
        config = {"speaker_type": "center_channel", "alcove_height_from_floor": 28.0}
        result = component.validate(config, standard_context)
        assert len(result.warnings) >= 1
        assert any("below ear level" in warn for warn in result.warnings)
        assert any("36-42" in warn for warn in result.warnings)

    def test_center_channel_exactly_30_inches_no_warning(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test center_channel at height = 30 generates no ear level warning."""
        config = {"speaker_type": "center_channel", "alcove_height_from_floor": 30.0}
        result = component.validate(config, standard_context)
        assert not any("ear level" in warn for warn in result.warnings)

    def test_center_channel_at_recommended_height_no_warning(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test center_channel at 36-42 inches generates no warning."""
        for height in [36.0, 40.0, 42.0]:
            config = {"speaker_type": "center_channel", "alcove_height_from_floor": height}
            result = component.validate(config, standard_context)
            assert not any("ear level" in warn for warn in result.warnings)

    def test_bookshelf_low_height_no_ear_level_warning(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that bookshelf speaker type does not trigger ear level warning."""
        config = {"speaker_type": "bookshelf", "alcove_height_from_floor": 20.0}
        result = component.validate(config, standard_context)
        # Bookshelf speakers don't require ear level validation
        assert not any("ear level" in warn for warn in result.warnings)


class TestSpeakerSubwooferPortClearanceValidation:
    """Tests for subwoofer port clearance validation."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_subwoofer_port_clearance_below_4_error(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test subwoofer with port_clearance < 4.0 generates ERROR."""
        config = {"speaker_type": "subwoofer", "port_clearance": 3.0}
        result = component.validate(config, standard_context)
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "port clearance" in result.errors[0]
        assert "insufficient" in result.errors[0]
        assert "4" in result.errors[0]

    def test_subwoofer_port_clearance_exactly_4_no_error(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test subwoofer with port_clearance = 4.0 generates no error."""
        config = {"speaker_type": "subwoofer", "port_clearance": 4.0}
        result = component.validate(config, standard_context)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_subwoofer_default_port_clearance_valid(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test subwoofer with default port_clearance (4.0) is valid."""
        config = {"speaker_type": "subwoofer"}  # Uses default 4.0
        result = component.validate(config, standard_context)
        assert result.is_valid


class TestSpeakerAlcoveGenerationPanels:
    """Tests for SpeakerAlcoveComponent.generate() panel creation."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_generates_left_side_panel_with_speaker_type_metadata(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that LEFT_SIDE panel is generated with speaker_type metadata."""
        config = {"speaker_type": "center_channel"}
        result = component.generate(config, standard_context)
        left_panels = [p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE]
        assert len(left_panels) == 1
        assert left_panels[0].metadata["component"] == "media.speaker_alcove"
        assert left_panels[0].metadata["speaker_type"] == "center_channel"

    def test_generates_right_side_panel_with_speaker_type_metadata(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that RIGHT_SIDE panel is generated with speaker_type metadata."""
        config = {"speaker_type": "bookshelf"}
        result = component.generate(config, standard_context)
        right_panels = [p for p in result.panels if p.panel_type == PanelType.RIGHT_SIDE]
        assert len(right_panels) == 1
        assert right_panels[0].metadata["component"] == "media.speaker_alcove"
        assert right_panels[0].metadata["speaker_type"] == "bookshelf"

    def test_generates_bottom_panel_with_open_back_metadata(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that BOTTOM panel is generated with open_back=True metadata."""
        config = {"speaker_type": "center_channel"}
        result = component.generate(config, standard_context)
        bottom_panels = [p for p in result.panels if p.panel_type == PanelType.BOTTOM]
        assert len(bottom_panels) == 1
        assert bottom_panels[0].metadata["component"] == "media.speaker_alcove"
        assert bottom_panels[0].metadata["speaker_type"] == "center_channel"
        assert bottom_panels[0].metadata["open_back"] is True

    def test_no_back_panel_generated(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that no BACK panel is generated (for acoustic reasons)."""
        config = {"speaker_type": "center_channel"}
        result = component.generate(config, standard_context)
        back_panels = [p for p in result.panels if p.panel_type == PanelType.BACK]
        assert len(back_panels) == 0

    def test_panel_dimensions_include_2_inch_clearance(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that panel dimensions = speaker dimensions + 2 for clearance."""
        # Test center_channel (24.0, 8.0, 12.0)
        config = {"speaker_type": "center_channel"}
        result = component.generate(config, standard_context)

        # Side panels: width = depth + 2, height = speaker_height + 2
        left_panel = next(p for p in result.panels if p.panel_type == PanelType.LEFT_SIDE)
        assert left_panel.width == 12.0 + 2.0  # depth + 2
        assert left_panel.height == 8.0 + 2.0  # height + 2

        # Bottom panel: width = speaker_width + 2, height = depth + 2
        bottom_panel = next(p for p in result.panels if p.panel_type == PanelType.BOTTOM)
        assert bottom_panel.width == 24.0 + 2.0  # width + 2
        assert bottom_panel.height == 12.0 + 2.0  # depth + 2


class TestSpeakerAlcoveAcousticDampening:
    """Tests for acoustic dampening hardware in speaker alcove."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_include_dampening_true_adds_foam_hardware(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that include_dampening=True (default) adds Acoustic Dampening Foam."""
        config = {"speaker_type": "center_channel", "include_dampening": True}
        result = component.generate(config, standard_context)
        foam_items = [h for h in result.hardware if "Acoustic Dampening Foam" in h.name]
        assert len(foam_items) == 1
        assert foam_items[0].sku == "ACOUSTIC-FOAM-SHEET"
        assert foam_items[0].quantity == 1

    def test_include_dampening_default_adds_foam(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that include_dampening defaults to True and adds foam."""
        config = {"speaker_type": "center_channel"}  # No include_dampening specified
        result = component.generate(config, standard_context)
        foam_items = [h for h in result.hardware if "Acoustic Dampening Foam" in h.name]
        assert len(foam_items) == 1

    def test_include_dampening_false_no_foam(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that include_dampening=False excludes foam hardware."""
        config = {"speaker_type": "center_channel", "include_dampening": False}
        result = component.generate(config, standard_context)
        foam_items = [h for h in result.hardware if "Foam" in h.name]
        assert len(foam_items) == 0


class TestSpeakerAlcoveHardwareMethod:
    """Tests for SpeakerAlcoveComponent.hardware() method."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_hardware_returns_acoustic_foam_with_correct_sku(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware() returns Acoustic Dampening Foam with correct SKU."""
        from cabinets.domain.components.results import HardwareItem

        config = {"speaker_type": "center_channel", "include_dampening": True}
        hardware = component.hardware(config, standard_context)
        assert isinstance(hardware, list)
        assert len(hardware) == 1
        assert isinstance(hardware[0], HardwareItem)
        assert hardware[0].name == "Acoustic Dampening Foam"
        assert hardware[0].sku == "ACOUSTIC-FOAM-SHEET"

    def test_hardware_notes_include_speaker_type(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that hardware notes include speaker type reference."""
        config = {"speaker_type": "subwoofer", "include_dampening": True}
        hardware = component.hardware(config, standard_context)
        assert len(hardware) == 1
        assert "subwoofer" in hardware[0].notes


class TestSpeakerAlcoveMetadata:
    """Tests for SpeakerAlcoveComponent.generate() metadata."""

    @pytest.fixture
    def component(self) -> SpeakerAlcoveComponent:
        """Create a SpeakerAlcoveComponent instance."""
        return SpeakerAlcoveComponent()

    def test_metadata_includes_speaker_type(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that result metadata includes speaker_type."""
        config = {"speaker_type": "bookshelf"}
        result = component.generate(config, standard_context)
        assert result.metadata["speaker_type"] == "bookshelf"

    def test_metadata_includes_speaker_dimensions(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that result metadata includes speaker dimensions tuple."""
        config = {"speaker_type": "subwoofer"}
        result = component.generate(config, standard_context)
        assert result.metadata["speaker_dimensions"] == (15.0, 15.0, 18.0)

    def test_metadata_includes_open_back(
        self, component: SpeakerAlcoveComponent, standard_context: ComponentContext
    ) -> None:
        """Test that result metadata includes open_back=True."""
        config = {"speaker_type": "center_channel"}
        result = component.generate(config, standard_context)
        assert result.metadata["open_back"] is True
