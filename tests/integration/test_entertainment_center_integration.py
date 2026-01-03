"""Integration tests for entertainment center generation (FRD-19).

These tests verify end-to-end entertainment center generation including:
- Console layout with equipment shelf, soundbar, and ventilation
- Wall unit layout with TV zone and flanking storage
- Tower layout with vertical equipment stack
- Gaming station with multiple consoles
- Home theater with receiver, speakers, and soundbar
- STL export rendering of all entertainment center panel types

Test run command:
    uv run pytest tests/integration/test_entertainment_center_integration.py -v
"""

from __future__ import annotations

import pytest

from cabinets.domain.components import ComponentContext, component_registry
from cabinets.domain.components.media import (
    EquipmentShelfComponent,
    SoundbarShelfComponent,
    SpeakerAlcoveComponent,
    VentilatedSectionComponent,
)
from cabinets.domain.entities import Cabinet, Panel
from cabinets.domain.services import Panel3DMapper
from cabinets.domain.services.entertainment_center import (
    CableChasePosition,
    EntertainmentCenterLayoutService,
    TVIntegration,
    TVZone,
)
from cabinets.domain.value_objects import (
    Dimensions,
    MaterialSpec,
    PanelType,
    Position,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ensure_media_components_registered() -> None:
    """Ensure all media components are registered for tests."""
    if "media.equipment_shelf" not in component_registry.list():
        component_registry.register("media.equipment_shelf")(EquipmentShelfComponent)
    if "media.ventilated_section" not in component_registry.list():
        component_registry.register("media.ventilated_section")(
            VentilatedSectionComponent
        )
    if "media.soundbar_shelf" not in component_registry.list():
        component_registry.register("media.soundbar_shelf")(SoundbarShelfComponent)
    if "media.speaker_alcove" not in component_registry.list():
        component_registry.register("media.speaker_alcove")(SpeakerAlcoveComponent)


@pytest.fixture
def standard_material() -> MaterialSpec:
    """Standard 3/4 inch plywood."""
    return MaterialSpec.standard_3_4()


@pytest.fixture
def back_material() -> MaterialSpec:
    """Standard 1/2 inch plywood for backs."""
    return MaterialSpec.standard_1_2()


@pytest.fixture
def console_context() -> ComponentContext:
    """Create context for console entertainment center (low profile, 72x24x18)."""
    return ComponentContext(
        width=72.0,
        height=24.0,
        depth=18.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=72.0,
        cabinet_height=24.0,
        cabinet_depth=18.0,
    )


@pytest.fixture
def wall_unit_context() -> ComponentContext:
    """Create context for wall unit entertainment center (full height, 96x84x16)."""
    return ComponentContext(
        width=96.0,
        height=84.0,
        depth=16.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=96.0,
        cabinet_height=84.0,
        cabinet_depth=16.0,
    )


@pytest.fixture
def tower_context() -> ComponentContext:
    """Create context for tower layout (narrow, deep, 30x72x20)."""
    return ComponentContext(
        width=30.0,
        height=72.0,
        depth=20.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=30.0,
        cabinet_height=72.0,
        cabinet_depth=20.0,
    )


@pytest.fixture
def gaming_context() -> ComponentContext:
    """Create context for gaming station (wide, 60x24x18)."""
    return ComponentContext(
        width=60.0,
        height=24.0,
        depth=18.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=60.0,
        cabinet_height=24.0,
        cabinet_depth=18.0,
    )


@pytest.fixture
def home_theater_context() -> ComponentContext:
    """Create context for home theater (wide, full height, 84x84x18)."""
    return ComponentContext(
        width=84.0,
        height=84.0,
        depth=18.0,
        material=MaterialSpec.standard_3_4(),
        position=Position(0, 0),
        section_index=0,
        cabinet_width=84.0,
        cabinet_height=84.0,
        cabinet_depth=18.0,
    )


@pytest.fixture
def entertainment_service() -> EntertainmentCenterLayoutService:
    """Create entertainment center layout service."""
    return EntertainmentCenterLayoutService()


# =============================================================================
# Test 1: Console Layout Integration Test
# =============================================================================


class TestConsoleLayoutIntegration:
    """Integration tests for console entertainment center layout.

    A console is a low-profile unit (16-30" height) designed for
    wall-mounted TVs above, containing equipment shelves, soundbar,
    and ventilation.
    """

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_console_layout_validation(
        self, entertainment_service: EntertainmentCenterLayoutService
    ) -> None:
        """Validate console layout dimensions are acceptable."""
        dimensions = Dimensions(width=72.0, height=24.0, depth=18.0)
        errors, warnings = entertainment_service.validate_layout("console", dimensions)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_console_with_equipment_soundbar_and_ventilation(
        self, console_context: ComponentContext
    ) -> None:
        """Generate console with equipment shelf, soundbar, and ventilation.

        Verifies all panels are created with correct metadata and
        hardware list includes grommets, cable ties, and ventilation grille.
        """
        # Generate equipment shelf for streaming device
        equipment = EquipmentShelfComponent()
        equipment_config = {
            "equipment_type": "streaming",
            "grommet_position": "center_rear",
            "grommet_diameter": 2.0,
        }
        equipment_result = equipment.generate(equipment_config, console_context)

        # Generate soundbar shelf
        soundbar = SoundbarShelfComponent()
        soundbar_config = {
            "soundbar_type": "standard",
            "include_mount": True,
        }
        soundbar_result = soundbar.generate(soundbar_config, console_context)

        # Generate ventilated section
        ventilated = VentilatedSectionComponent()
        vent_config = {
            "ventilation_type": "passive_rear",
            "vent_pattern": "grid",
            "open_area_percent": 30.0,
        }
        vent_result = ventilated.generate(vent_config, console_context)

        # Verify equipment shelf panel
        equipment_panels = [
            p for p in equipment_result.panels if p.panel_type == PanelType.SHELF
        ]
        assert len(equipment_panels) == 1
        assert equipment_panels[0].metadata.get("is_equipment_shelf") is True
        assert equipment_panels[0].metadata.get("equipment_type") == "streaming"

        # Verify soundbar shelf panel
        soundbar_panels = [
            p for p in soundbar_result.panels if p.panel_type == PanelType.SHELF
        ]
        assert len(soundbar_panels) == 1
        assert soundbar_panels[0].metadata.get("is_soundbar_shelf") is True
        assert soundbar_panels[0].metadata.get("open_back") is True

        # Verify ventilation back panel
        vent_panels = [p for p in vent_result.panels if p.panel_type == PanelType.BACK]
        assert len(vent_panels) == 1
        assert vent_panels[0].metadata.get("requires_vent_cutout") is True
        assert vent_panels[0].metadata.get("vent_pattern") == "grid"

        # Verify hardware includes expected items
        all_hardware = (
            list(equipment_result.hardware)
            + list(soundbar_result.hardware)
            + list(vent_result.hardware)
        )
        hardware_names = [h.name for h in all_hardware]

        # Check for grommet
        assert any("Grommet" in name for name in hardware_names)

        # Check for cable ties
        assert any("Cable Tie" in name for name in hardware_names)

        # Check for soundbar mount
        assert any("Soundbar" in name and "Mount" in name for name in hardware_names)

        # Check for ventilation grille
        assert any("Grille" in name for name in hardware_names)

    def test_console_equipment_validation_shallow_depth(
        self, console_context: ComponentContext
    ) -> None:
        """Test validation error for insufficient depth."""
        # Create context with shallow depth
        shallow_context = ComponentContext(
            width=72.0,
            height=24.0,
            depth=10.0,  # Too shallow for equipment
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=24.0,
            cabinet_depth=10.0,
        )

        equipment = EquipmentShelfComponent()
        config = {"equipment_type": "receiver", "depth": 10.0}
        result = equipment.validate(config, shallow_context)

        assert not result.is_valid
        assert any("too shallow" in error for error in result.errors)


# =============================================================================
# Test 2: Wall Unit Layout Integration Test
# =============================================================================


class TestWallUnitLayoutIntegration:
    """Integration tests for wall unit entertainment center layout.

    A wall unit is a full-height unit (72-96") with a central TV zone
    flanked by storage sections, cable chase for routing, and
    multiple equipment shelves.
    """

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_wall_unit_layout_validation(
        self, entertainment_service: EntertainmentCenterLayoutService
    ) -> None:
        """Validate wall unit layout dimensions are acceptable."""
        dimensions = Dimensions(width=96.0, height=84.0, depth=16.0)
        errors, warnings = entertainment_service.validate_layout(
            "wall_unit", dimensions
        )

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_wall_unit_tv_zone_calculation(
        self, entertainment_service: EntertainmentCenterLayoutService
    ) -> None:
        """Test TV zone calculation for wall unit."""
        tv = TVIntegration.from_screen_size(65)
        tv_zone = entertainment_service.calculate_tv_zone(tv, cabinet_width=96.0)

        assert isinstance(tv_zone, TVZone)
        # TV zone should be centered
        assert tv_zone.flanking_left_width == pytest.approx(
            tv_zone.flanking_right_width
        )
        # TV zone width should accommodate TV with clearance
        assert tv_zone.tv_zone_width >= tv.viewing_width + 4.0  # 2" clearance each side

    def test_wall_unit_with_multiple_equipment_shelves(
        self, wall_unit_context: ComponentContext
    ) -> None:
        """Generate wall unit with multiple equipment shelves and heat validation.

        Verifies that heat-generating equipment gets proper warnings
        and all shelves are created.
        """
        equipment = EquipmentShelfComponent()

        # Generate receiver shelf (heat-generating)
        receiver_config = {
            "equipment_type": "receiver",
            "grommet_position": "center_rear",
            "vertical_clearance": 12.0,  # Include equipment height + clearance
        }
        receiver_validation = equipment.validate(receiver_config, wall_unit_context)
        receiver_result = equipment.generate(receiver_config, wall_unit_context)

        # Generate streaming device shelf
        streaming_config = {
            "equipment_type": "streaming",
            "grommet_position": "left_rear",
        }
        streaming_result = equipment.generate(streaming_config, wall_unit_context)

        # Generate Blu-ray shelf
        bluray_config = {
            "equipment_type": "blu_ray",
            "grommet_position": "right_rear",
        }
        bluray_result = equipment.generate(bluray_config, wall_unit_context)

        # Verify receiver gets heat warning (clearance too low for 7" receiver + 8" clearance needed)
        assert len(receiver_validation.warnings) > 0
        assert any("heat" in warn.lower() for warn in receiver_validation.warnings)

        # Verify all shelves created
        all_panels = (
            list(receiver_result.panels)
            + list(streaming_result.panels)
            + list(bluray_result.panels)
        )
        shelf_panels = [p for p in all_panels if p.panel_type == PanelType.SHELF]
        assert len(shelf_panels) == 3

        # Verify equipment types are tracked in metadata
        equipment_types = {p.metadata.get("equipment_type") for p in shelf_panels}
        assert "receiver" in equipment_types
        assert "streaming" in equipment_types
        assert "blu_ray" in equipment_types

    def test_wall_unit_cable_chase_positioning(
        self, entertainment_service: EntertainmentCenterLayoutService
    ) -> None:
        """Test cable chase positioning for wall unit.

        Creates cable chase positions manually since the layout service
        provides TV zone calculation but cable chase planning is done
        during section generation.
        """
        tv = TVIntegration.from_screen_size(65)
        tv_zone = entertainment_service.calculate_tv_zone(tv, cabinet_width=96.0)

        # Create cable chase positions based on TV zone
        # Cable chases are typically placed at TV zone boundaries
        left_chase = CableChasePosition(
            x=tv_zone.tv_zone_start,
            y=0.0,
            width=3.0,
            purpose="Left side cable routing",
        )
        right_chase = CableChasePosition(
            x=tv_zone.tv_zone_end - 3.0,
            y=0.0,
            width=3.0,
            purpose="Right side cable routing",
        )

        # Verify chase positions are valid
        assert isinstance(left_chase, CableChasePosition)
        assert isinstance(right_chase, CableChasePosition)
        assert left_chase.x >= 0
        assert right_chase.x >= 0
        assert left_chase.width > 0
        assert right_chase.width > 0

        # Verify positions can be converted to Position value objects
        left_pos = left_chase.to_position()
        right_pos = right_chase.to_position()
        assert left_pos.x == left_chase.x
        assert right_pos.x == right_chase.x


# =============================================================================
# Test 3: Tower Layout Integration Test
# =============================================================================


class TestTowerLayoutIntegration:
    """Integration tests for tower entertainment center layout.

    A tower is a vertical equipment stack (24-36" width, 18"+ depth)
    with multiple equipment shelves, ventilated back panel, and
    cable chase for routing.
    """

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_tower_layout_validation(
        self, entertainment_service: EntertainmentCenterLayoutService
    ) -> None:
        """Validate tower layout dimensions are acceptable."""
        dimensions = Dimensions(width=30.0, height=72.0, depth=20.0)
        errors, warnings = entertainment_service.validate_layout("tower", dimensions)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_tower_with_receiver_and_consoles(
        self, tower_context: ComponentContext
    ) -> None:
        """Generate tower with receiver and gaming consoles.

        Verifies stacked equipment shelves and ventilation.
        Note: Active fan ventilation generates cutouts and hardware
        but not panels (panels are added separately or use passive_rear).
        """
        equipment = EquipmentShelfComponent()

        # Generate receiver shelf
        receiver_config = {
            "equipment_type": "receiver",
            "grommet_position": "center_rear",
        }
        receiver_result = equipment.generate(receiver_config, tower_context)

        # Generate console shelf (horizontal)
        console_config = {
            "equipment_type": "console_horizontal",
            "grommet_position": "left_rear",
        }
        console_result = equipment.generate(console_config, tower_context)

        # Generate ventilated back section with passive rear (generates panel)
        ventilated = VentilatedSectionComponent()
        vent_config = {
            "ventilation_type": "passive_rear",
            "vent_pattern": "slot",
        }
        vent_result = ventilated.generate(vent_config, tower_context)

        # Verify all equipment shelves generated
        assert len(receiver_result.panels) > 0
        assert len(console_result.panels) > 0

        # Verify ventilated section generated back panel
        assert len(vent_result.panels) > 0
        back_panels = [p for p in vent_result.panels if p.panel_type == PanelType.BACK]
        assert len(back_panels) == 1
        assert back_panels[0].metadata.get("requires_vent_cutout") is True

        # Verify heat-generating equipment metadata
        receiver_panel = next(
            p for p in receiver_result.panels if p.panel_type == PanelType.SHELF
        )
        console_panel = next(
            p for p in console_result.panels if p.panel_type == PanelType.SHELF
        )
        assert receiver_panel.metadata.get("generates_heat") is True
        assert console_panel.metadata.get("generates_heat") is True

        # Test active fan ventilation separately (generates cutouts and hardware, not panels)
        active_vent_config = {
            "ventilation_type": "active_fan",
            "fan_size_mm": 120,
        }
        active_vent_result = ventilated.generate(active_vent_config, tower_context)

        # Active fan generates hardware, not panels
        assert len(active_vent_result.panels) == 0
        fan_hardware = [
            h
            for h in active_vent_result.hardware
            if "Fan" in h.name or "fan" in h.name.lower()
        ]
        assert len(fan_hardware) > 0
        assert any("120mm" in h.name for h in fan_hardware)

        # Verify cutout in metadata
        assert "cutouts" in active_vent_result.metadata
        cutouts = active_vent_result.metadata["cutouts"]
        assert len(cutouts) > 0
        assert cutouts[0].cutout_type == "cooling_fan"


# =============================================================================
# Test 4: Gaming Station Integration Test
# =============================================================================


class TestGamingStationIntegration:
    """Integration tests for gaming station layout.

    A gaming station supports multiple gaming consoles with
    adequate ventilation for heat sources, cable management
    with grommets, and game storage.
    """

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_gaming_station_with_multiple_consoles(
        self, gaming_context: ComponentContext
    ) -> None:
        """Generate gaming station with multiple consoles.

        Verifies heat management and cable management for multiple
        heat-generating gaming consoles.
        """
        equipment = EquipmentShelfComponent()

        # Generate first console shelf with insufficient clearance to trigger heat warning
        # console_horizontal: height=4.0", requires 8" clearance above
        # If we set vertical_clearance to 10 (4 equipment + 6 clearance), we get warning
        ps_config = {
            "equipment_type": "console_horizontal",
            "grommet_position": "left_rear",
            "grommet_diameter": 2.5,
            "vertical_clearance": 10.0,  # 4" equipment + 6" clearance (below 8" recommended)
        }
        ps_result = equipment.generate(ps_config, gaming_context)
        ps_validation = equipment.validate(ps_config, gaming_context)

        # Generate second console shelf (Xbox style - horizontal)
        xbox_config = {
            "equipment_type": "console_horizontal",
            "grommet_position": "right_rear",
            "grommet_diameter": 2.5,
        }
        xbox_result = equipment.generate(xbox_config, gaming_context)

        # Generate streaming device shelf
        streaming_config = {
            "equipment_type": "streaming",
            "grommet_position": "center_rear",
        }
        streaming_result = equipment.generate(streaming_config, gaming_context)

        # Verify console with insufficient clearance generates heat warnings
        assert any("heat" in warn.lower() for warn in ps_validation.warnings)

        # Verify grommets for each console
        ps_hardware = [h for h in ps_result.hardware if "Grommet" in h.name]
        xbox_hardware = [h for h in xbox_result.hardware if "Grommet" in h.name]
        assert len(ps_hardware) > 0
        assert len(xbox_hardware) > 0

        # Verify cable tie mounts included
        all_hardware = (
            list(ps_result.hardware)
            + list(xbox_result.hardware)
            + list(streaming_result.hardware)
        )
        cable_ties = [h for h in all_hardware if "Cable Tie" in h.name]
        assert len(cable_ties) >= 3  # At least one set per shelf

    def test_gaming_station_ventilation_requirement(
        self, gaming_context: ComponentContext
    ) -> None:
        """Test that gaming station validates ventilation for heat sources."""
        ventilated = VentilatedSectionComponent()

        # Enclosed section without ventilation should generate error
        no_vent_config = {
            "ventilation_type": "none",
            "enclosed": True,
            "has_equipment": True,
        }
        result = ventilated.validate(no_vent_config, gaming_context)

        assert not result.is_valid
        assert any(
            "enclosed" in error.lower() or "ventilation" in error.lower()
            for error in result.errors
        )

    def test_gaming_station_hardware_list(
        self, gaming_context: ComponentContext
    ) -> None:
        """Verify complete hardware list for gaming station."""
        equipment = EquipmentShelfComponent()
        ventilated = VentilatedSectionComponent()

        # Generate components
        console_config = {
            "equipment_type": "console_horizontal",
            "grommet_position": "center_rear",
        }
        console_result = equipment.generate(console_config, gaming_context)

        vent_config = {
            "ventilation_type": "passive_rear",
            "vent_pattern": "slot",
        }
        vent_result = ventilated.generate(vent_config, gaming_context)

        # Collect all hardware
        all_hardware = list(console_result.hardware) + list(vent_result.hardware)
        hardware_names = {h.name for h in all_hardware}

        # Verify expected hardware types
        assert any("Grommet" in name for name in hardware_names)
        assert any("Cable Tie" in name for name in hardware_names)
        assert any("Grille" in name for name in hardware_names)


# =============================================================================
# Test 5: Home Theater Integration Test
# =============================================================================


class TestHomeTheaterIntegration:
    """Integration tests for home theater layout.

    A home theater setup includes equipment shelves for receiver,
    Blu-ray, and streaming devices, center channel speaker alcove,
    soundbar shelf with Dolby Atmos clearance, and complete
    hardware list validation.
    """

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_home_theater_complete_setup(
        self, home_theater_context: ComponentContext
    ) -> None:
        """Generate complete home theater with all components.

        Verifies receiver, Blu-ray, streaming, center channel,
        and soundbar are all correctly generated.
        """
        equipment = EquipmentShelfComponent()
        soundbar = SoundbarShelfComponent()
        speaker = SpeakerAlcoveComponent()

        # Generate receiver shelf
        receiver_config = {
            "equipment_type": "receiver",
            "grommet_position": "center_rear",
        }
        receiver_result = equipment.generate(receiver_config, home_theater_context)

        # Generate Blu-ray shelf
        bluray_config = {
            "equipment_type": "blu_ray",
            "grommet_position": "left_rear",
        }
        bluray_result = equipment.generate(bluray_config, home_theater_context)

        # Generate streaming shelf
        streaming_config = {
            "equipment_type": "streaming",
            "grommet_position": "right_rear",
        }
        streaming_result = equipment.generate(streaming_config, home_theater_context)

        # Generate center channel speaker alcove
        speaker_config = {
            "speaker_type": "center_channel",
            "include_dampening": True,
            "alcove_height_from_floor": 36.0,
        }
        speaker_result = speaker.generate(speaker_config, home_theater_context)

        # Generate soundbar with Atmos
        soundbar_config = {
            "soundbar_type": "premium",
            "dolby_atmos": True,
            "ceiling_clearance": 30.0,
            "include_mount": True,
        }
        soundbar_result = soundbar.generate(soundbar_config, home_theater_context)

        # Verify all components generated panels
        assert len(receiver_result.panels) > 0
        assert len(bluray_result.panels) > 0
        assert len(streaming_result.panels) > 0
        assert len(speaker_result.panels) > 0
        assert len(soundbar_result.panels) > 0

        # Verify speaker alcove has side panels and bottom (no back for acoustic reasons)
        speaker_panel_types = {p.panel_type for p in speaker_result.panels}
        assert PanelType.LEFT_SIDE in speaker_panel_types
        assert PanelType.RIGHT_SIDE in speaker_panel_types
        assert PanelType.BOTTOM in speaker_panel_types
        assert PanelType.BACK not in speaker_panel_types  # Open back for acoustics

        # Verify acoustic dampening foam included
        dampening_hardware = [
            h
            for h in speaker_result.hardware
            if "Acoustic" in h.name or "Dampening" in h.name or "Foam" in h.name
        ]
        assert len(dampening_hardware) > 0

    def test_home_theater_dolby_atmos_clearance(
        self, home_theater_context: ComponentContext
    ) -> None:
        """Test Dolby Atmos soundbar ceiling clearance validation."""
        soundbar = SoundbarShelfComponent()

        # Atmos soundbar with insufficient ceiling clearance
        low_clearance_config = {
            "soundbar_type": "premium",
            "dolby_atmos": True,
            "ceiling_clearance": 18.0,  # Below 24" recommended
        }
        result = soundbar.validate(low_clearance_config, home_theater_context)

        # Should get warning about Atmos height effects
        assert any("Atmos" in warn for warn in result.warnings)

    def test_home_theater_center_channel_height(
        self, home_theater_context: ComponentContext
    ) -> None:
        """Test center channel speaker height validation."""
        speaker = SpeakerAlcoveComponent()

        # Center channel at too low height
        low_config = {
            "speaker_type": "center_channel",
            "alcove_height_from_floor": 24.0,  # Below 30" recommended
        }
        result = speaker.validate(low_config, home_theater_context)

        # Should get warning about ear level
        assert any("ear level" in warn.lower() for warn in result.warnings)

    def test_home_theater_hardware_list_complete(
        self, home_theater_context: ComponentContext
    ) -> None:
        """Verify complete hardware list for home theater setup."""
        equipment = EquipmentShelfComponent()
        soundbar = SoundbarShelfComponent()
        speaker = SpeakerAlcoveComponent()
        ventilated = VentilatedSectionComponent()

        # Generate all components
        receiver_result = equipment.generate(
            {"equipment_type": "receiver", "grommet_position": "center_rear"},
            home_theater_context,
        )
        soundbar_result = soundbar.generate(
            {"soundbar_type": "premium", "include_mount": True},
            home_theater_context,
        )
        speaker_result = speaker.generate(
            {"speaker_type": "center_channel", "include_dampening": True},
            home_theater_context,
        )
        vent_result = ventilated.generate(
            {"ventilation_type": "passive_rear", "vent_pattern": "grid"},
            home_theater_context,
        )

        # Collect all hardware
        all_hardware = (
            list(receiver_result.hardware)
            + list(soundbar_result.hardware)
            + list(speaker_result.hardware)
            + list(vent_result.hardware)
        )
        hardware_names = {h.name for h in all_hardware}

        # Verify comprehensive hardware list
        assert any("Grommet" in name for name in hardware_names)
        assert any("Cable Tie" in name for name in hardware_names)
        assert any("Soundbar" in name and "Mount" in name for name in hardware_names)
        assert any("Acoustic" in name or "Foam" in name for name in hardware_names)
        assert any("Grille" in name for name in hardware_names)


# =============================================================================
# Test 6: STL Export Integration Test
# =============================================================================


class TestSTLExportIntegration:
    """Integration tests for STL export of entertainment center panels.

    Verifies that Panel3DMapper correctly handles all entertainment
    center panel types including CABLE_CHASE for cable routing.
    """

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_panel3d_mapper_handles_entertainment_panels(
        self, standard_material: MaterialSpec, back_material: MaterialSpec
    ) -> None:
        """Test that Panel3DMapper correctly renders entertainment center panels."""
        # Create a cabinet representing an entertainment center section
        cabinet = Cabinet(
            width=72.0,
            height=24.0,
            depth=18.0,
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(cabinet)

        # Create equipment shelf panel
        equipment_shelf = Panel(
            panel_type=PanelType.SHELF,
            width=70.5,  # Interior width
            height=17.5,  # Depth for horizontal panel
            material=standard_material,
            position=Position(x=0.75, y=12.0),
            metadata={"is_equipment_shelf": True},
        )

        # Map to 3D
        result = mapper.map_panel(equipment_shelf)

        # Verify 3D bounding box is valid
        assert result.size_x == pytest.approx(70.5)
        assert result.size_y == pytest.approx(17.5)  # Depth
        assert result.size_z == pytest.approx(standard_material.thickness)

    def test_cable_chase_panel_rendering(
        self, standard_material: MaterialSpec, back_material: MaterialSpec
    ) -> None:
        """Test CABLE_CHASE panel renders correctly in 3D."""
        cabinet = Cabinet(
            width=72.0,
            height=84.0,
            depth=18.0,
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(cabinet)

        # Create cable chase panel
        cable_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.0,  # Standard chase width
            height=80.0,  # Full interior height
            material=MaterialSpec.standard_1_4(),  # Thin material
            position=Position(x=36.0, y=0.75),  # Centered horizontally, at bottom
            metadata={"purpose": "TV cable routing"},
        )

        # Map to 3D
        result = mapper.map_panel(cable_chase)

        # Verify cable chase is at rear of cabinet (just in front of back panel)
        expected_y = mapper.back_thickness
        assert result.origin.y == pytest.approx(expected_y)

        # Verify dimensions
        assert result.size_x == pytest.approx(3.0)  # Chase width
        assert result.size_z == pytest.approx(80.0)  # Height

    def test_cable_chase_different_positions(
        self, standard_material: MaterialSpec, back_material: MaterialSpec
    ) -> None:
        """Test CABLE_CHASE at different horizontal positions."""
        cabinet = Cabinet(
            width=96.0,
            height=84.0,
            depth=16.0,
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(cabinet)

        # Left chase
        left_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.0,
            height=80.0,
            material=MaterialSpec.standard_1_4(),
            position=Position(x=12.0, y=0.75),
        )

        # Center chase
        center_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=4.0,
            height=80.0,
            material=MaterialSpec.standard_1_4(),
            position=Position(x=46.0, y=0.75),
        )

        # Right chase
        right_chase = Panel(
            panel_type=PanelType.CABLE_CHASE,
            width=3.0,
            height=80.0,
            material=MaterialSpec.standard_1_4(),
            position=Position(x=81.0, y=0.75),
        )

        left_result = mapper.map_panel(left_chase)
        center_result = mapper.map_panel(center_chase)
        right_result = mapper.map_panel(right_chase)

        # Verify X positions are correct
        assert left_result.origin.x == pytest.approx(12.0)
        assert center_result.origin.x == pytest.approx(46.0)
        assert right_result.origin.x == pytest.approx(81.0)

        # All should be at rear of cabinet (same Y)
        assert left_result.origin.y == pytest.approx(center_result.origin.y)
        assert center_result.origin.y == pytest.approx(right_result.origin.y)

    def test_full_entertainment_center_stl_mapping(
        self, standard_material: MaterialSpec, back_material: MaterialSpec
    ) -> None:
        """Test mapping a complete entertainment center to 3D.

        Creates multiple panel types and verifies all can be mapped.
        """
        cabinet = Cabinet(
            width=72.0,
            height=24.0,
            depth=18.0,
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(cabinet)

        # Generate panels from components
        equipment = EquipmentShelfComponent()
        context = ComponentContext(
            width=70.5,
            height=22.5,
            depth=17.5,
            material=standard_material,
            position=Position(0.75, 0.75),
            section_index=0,
            cabinet_width=72.0,
            cabinet_height=24.0,
            cabinet_depth=18.0,
        )

        equipment_result = equipment.generate(
            {"equipment_type": "receiver", "grommet_position": "center_rear"},
            context,
        )

        # Map all generated panels
        for panel in equipment_result.panels:
            result = mapper.map_panel(panel)
            # All panels should map to valid 3D boxes
            assert result.size_x > 0
            assert result.size_y > 0
            assert result.size_z > 0


# =============================================================================
# Test 7: End-to-End Workflow Tests
# =============================================================================


class TestEndToEndWorkflow:
    """End-to-end tests for complete entertainment center workflows."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_media_components_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_console_workflow_validate_generate_render(
        self,
        console_context: ComponentContext,
        standard_material: MaterialSpec,
        back_material: MaterialSpec,
    ) -> None:
        """Test complete workflow: validate -> generate -> render for console."""
        equipment = EquipmentShelfComponent()

        # Step 1: Validate configuration
        config = {
            "equipment_type": "streaming",
            "grommet_position": "center_rear",
        }
        validation = equipment.validate(config, console_context)
        assert validation.is_valid

        # Step 2: Generate panels
        result = equipment.generate(config, console_context)
        assert len(result.panels) > 0

        # Step 3: Render to 3D
        cabinet = Cabinet(
            width=console_context.cabinet_width,
            height=console_context.cabinet_height,
            depth=console_context.cabinet_depth,
            material=standard_material,
            back_material=back_material,
        )
        mapper = Panel3DMapper(cabinet)

        for panel in result.panels:
            box = mapper.map_panel(panel)
            # Verify valid 3D representation
            assert box.size_x > 0
            assert box.size_y > 0
            assert box.size_z > 0

    def test_wall_unit_workflow_with_tv_zone(
        self,
        wall_unit_context: ComponentContext,
        entertainment_service: EntertainmentCenterLayoutService,
        standard_material: MaterialSpec,
        back_material: MaterialSpec,
    ) -> None:
        """Test wall unit workflow with TV zone calculation."""
        # Step 1: Calculate TV zone
        tv = TVIntegration.from_screen_size(65)
        tv_zone = entertainment_service.calculate_tv_zone(tv, cabinet_width=96.0)
        assert tv_zone.tv_zone_width > tv.viewing_width

        # Step 2: Validate layout
        dimensions = Dimensions(
            width=wall_unit_context.cabinet_width,
            height=wall_unit_context.cabinet_height,
            depth=wall_unit_context.cabinet_depth,
        )
        errors, warnings = entertainment_service.validate_layout(
            "wall_unit", dimensions
        )
        assert len(errors) == 0

        # Step 3: Generate flanking equipment
        equipment = EquipmentShelfComponent()
        left_context = ComponentContext(
            width=tv_zone.flanking_left_width,
            height=wall_unit_context.height,
            depth=wall_unit_context.depth,
            material=standard_material,
            position=Position(0, 0),
            section_index=0,
            cabinet_width=wall_unit_context.cabinet_width,
            cabinet_height=wall_unit_context.cabinet_height,
            cabinet_depth=wall_unit_context.cabinet_depth,
        )

        if tv_zone.flanking_left_width > 12.0:  # Only if wide enough
            result = equipment.generate(
                {"equipment_type": "streaming"},
                left_context,
            )
            assert len(result.panels) > 0

    def test_validation_errors_block_generation(
        self, console_context: ComponentContext
    ) -> None:
        """Test that validation errors would prevent unsafe generation."""
        equipment = EquipmentShelfComponent()

        # Invalid config - equipment too wide
        wide_context = ComponentContext(
            width=10.0,  # Very narrow
            height=24.0,
            depth=18.0,
            material=MaterialSpec.standard_3_4(),
            position=Position(0, 0),
            section_index=0,
            cabinet_width=10.0,
            cabinet_height=24.0,
            cabinet_depth=18.0,
        )

        config = {"equipment_type": "receiver"}  # 17.5" wide receiver
        validation = equipment.validate(config, wide_context)

        # Should have error about width
        assert not validation.is_valid
        assert any(
            "width" in error.lower() or "exceeds" in error.lower()
            for error in validation.errors
        )

    def test_multiple_components_hardware_aggregation(
        self, home_theater_context: ComponentContext
    ) -> None:
        """Test hardware aggregation from multiple components."""
        equipment = EquipmentShelfComponent()
        soundbar = SoundbarShelfComponent()
        speaker = SpeakerAlcoveComponent()
        ventilated = VentilatedSectionComponent()

        # Generate all components
        results = [
            equipment.generate(
                {"equipment_type": "receiver"},
                home_theater_context,
            ),
            equipment.generate(
                {"equipment_type": "blu_ray"},
                home_theater_context,
            ),
            soundbar.generate(
                {"soundbar_type": "premium", "include_mount": True},
                home_theater_context,
            ),
            speaker.generate(
                {"speaker_type": "center_channel", "include_dampening": True},
                home_theater_context,
            ),
            ventilated.generate(
                {"ventilation_type": "active_fan", "fan_size_mm": 120},
                home_theater_context,
            ),
        ]

        # Aggregate all hardware
        all_hardware: list = []
        for result in results:
            all_hardware.extend(result.hardware)

        # Verify expected hardware counts
        grommets = [h for h in all_hardware if "Grommet" in h.name]
        cable_ties = [h for h in all_hardware if "Cable Tie" in h.name]
        fans = [h for h in all_hardware if "Fan" in h.name]
        mounts = [h for h in all_hardware if "Mount" in h.name]

        assert len(grommets) >= 2  # At least one per equipment shelf
        assert len(cable_ties) >= 2  # At least one set per equipment shelf
        assert len(fans) >= 1  # Active ventilation
        assert len(mounts) >= 1  # Soundbar mount
