"""Integration tests for room-aware cabinet generation (FRD-02).

These tests verify end-to-end room layout generation including:
- Loading room configurations from JSON files
- Converting room configs to domain entities
- Generating cabinet layouts for multi-wall rooms
- Validating backward compatibility with v1.0 configs
- STL export with room transforms
"""

import json
from pathlib import Path

import pytest

from cabinets.application.factory import get_factory
from cabinets.application.config import (
    config_to_dtos,
    config_to_room,
    config_to_section_specs,
    load_config,
)
from cabinets.domain.services import PanelGenerationService, RoomLayoutService
from cabinets.infrastructure.stl_exporter import StlExporter


# Path to fixture configs
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "configs"


class TestLoadRoomConfigs:
    """Tests for loading room configurations from JSON files."""

    def test_load_single_wall_room_config(self) -> None:
        """Test loading a single wall room configuration."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        assert config.schema_version == "1.1"
        assert config.room is not None
        assert config.room.name == "alcove"
        assert len(config.room.walls) == 1
        assert config.room.walls[0].name == "back"
        assert config.room.walls[0].length == 72
        assert config.room.walls[0].height == 84
        assert config.room.walls[0].angle == 0

    def test_load_l_shaped_room_config(self) -> None:
        """Test loading an L-shaped room configuration."""
        config_path = FIXTURES_PATH / "room_l_shape.json"
        config = load_config(config_path)

        assert config.schema_version == "1.1"
        assert config.room is not None
        assert config.room.name == "corner-unit"
        assert len(config.room.walls) == 2
        assert config.room.walls[0].name == "left"
        assert config.room.walls[1].name == "right"
        assert config.room.walls[1].angle == 90

    def test_load_u_shaped_room_config(self) -> None:
        """Test loading a U-shaped room configuration."""
        config_path = FIXTURES_PATH / "room_u_shape.json"
        config = load_config(config_path)

        assert config.schema_version == "1.1"
        assert config.room is not None
        assert config.room.name == "kitchen-u-shape"
        assert len(config.room.walls) == 3
        assert config.room.walls[0].name == "south"
        assert config.room.walls[1].name == "west"
        assert config.room.walls[2].name == "north"

    def test_load_backward_compat_config(self) -> None:
        """Test loading a v1.0 config without room definition."""
        config_path = FIXTURES_PATH / "room_backward_compat.json"
        config = load_config(config_path)

        assert config.schema_version == "1.0"
        assert config.room is None
        assert config.cabinet is not None
        assert config.cabinet.width == 72


class TestConfigToRoom:
    """Tests for converting configuration to Room domain entities."""

    def test_convert_single_wall_config_to_room(self) -> None:
        """Test converting a single wall config to a Room entity."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        room = config_to_room(config)

        assert room is not None
        assert room.name == "alcove"
        assert len(room.walls) == 1
        assert room.walls[0].length == 72
        assert room.walls[0].height == 84
        assert room.walls[0].name == "back"

    def test_convert_l_shaped_config_to_room(self) -> None:
        """Test converting an L-shaped config to a Room entity."""
        config_path = FIXTURES_PATH / "room_l_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)

        assert room is not None
        assert room.name == "corner-unit"
        assert len(room.walls) == 2

        # Check wall positions
        positions = room.get_wall_positions()
        assert len(positions) == 2

        # First wall runs along X axis
        assert positions[0].direction == pytest.approx(0.0)
        assert positions[0].start.x == pytest.approx(0.0)
        assert positions[0].start.y == pytest.approx(0.0)
        assert positions[0].end.x == pytest.approx(72.0)
        assert positions[0].end.y == pytest.approx(0.0)

        # Second wall turns 90 degrees right (clockwise)
        assert positions[1].direction == pytest.approx(270.0)

    def test_convert_u_shaped_config_to_room(self) -> None:
        """Test converting a U-shaped config to a Room entity."""
        config_path = FIXTURES_PATH / "room_u_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)

        assert room is not None
        assert room.name == "kitchen-u-shape"
        assert len(room.walls) == 3

        # Check bounding box
        width, depth = room.bounding_box
        assert width == pytest.approx(96.0)  # South wall length
        assert depth == pytest.approx(60.0)  # West wall length

    def test_backward_compat_config_returns_none_room(self) -> None:
        """Test that v1.0 config without room returns None."""
        config_path = FIXTURES_PATH / "room_backward_compat.json"
        config = load_config(config_path)

        room = config_to_room(config)

        assert room is None


class TestRoomLayoutGeneration:
    """Tests for end-to-end room layout generation."""

    def test_generate_single_wall_room_layout(self) -> None:
        """Test generating layout for a single wall room."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 3  # 3 sections
        assert len(result.transforms) == 3
        assert len(result.cut_list) > 0

    def test_generate_l_shaped_room_layout(self) -> None:
        """Test generating layout for an L-shaped room."""
        config_path = FIXTURES_PATH / "room_l_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 3  # 2 on left wall, 1 on right wall
        assert len(result.transforms) == 3

        # Check that transforms have different rotations for different walls
        wall_0_transforms = [t for t in result.transforms if t.wall_index == 0]
        wall_1_transforms = [t for t in result.transforms if t.wall_index == 1]

        assert len(wall_0_transforms) == 2
        assert len(wall_1_transforms) == 1

        # Wall 0 should have rotation 0, wall 1 should have rotation 90
        # (negated from wall direction 270 to face into the room)
        for t in wall_0_transforms:
            assert t.rotation_z == pytest.approx(0.0)
        for t in wall_1_transforms:
            assert t.rotation_z == pytest.approx(90.0)

    def test_generate_u_shaped_room_layout(self) -> None:
        """Test generating layout for a U-shaped room."""
        config_path = FIXTURES_PATH / "room_u_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) == 6  # 3 on south, 1 on west, 2 on north
        assert len(result.transforms) == 6

        # Check material estimates are aggregated
        assert result.total_estimate is not None
        assert result.total_estimate.total_area_sqft > 0


class TestBackwardCompatibility:
    """Tests for backward compatibility with v1.0 configs."""

    def test_v10_config_produces_valid_cabinet(self) -> None:
        """Test that v1.0 config without room still produces valid cabinets."""
        config_path = FIXTURES_PATH / "room_backward_compat.json"
        config = load_config(config_path)

        # Should not have room
        room = config_to_room(config)
        assert room is None

        # Should still produce valid cabinet using standard generation
        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid
        assert result.cabinet is not None
        assert len(result.cabinet.sections) == 3

    def test_v10_config_generates_correct_sections(self) -> None:
        """Test that v1.0 config generates correct section layout."""
        config_path = FIXTURES_PATH / "room_backward_compat.json"
        config = load_config(config_path)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid

        # Two fixed 24" sections and one fill section
        sections = result.cabinet.sections
        assert sections[0].width == pytest.approx(24.0, rel=1e-6)
        assert sections[1].width == pytest.approx(24.0, rel=1e-6)
        # Fill section should use remaining space
        # 72" - 2*0.75" sides - 2*0.75" dividers - 24 - 24 = 21"
        assert sections[2].width == pytest.approx(21.0, rel=1e-6)

    def test_v10_config_generates_cut_list(self) -> None:
        """Test that v1.0 config generates a complete cut list."""
        config_path = FIXTURES_PATH / "room_backward_compat.json"
        config = load_config(config_path)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid
        assert len(result.cut_list) > 0

        # Should have shelves for all sections (5 shelves each, 3 sections = 15)
        shelf_pieces = [p for p in result.cut_list if "Shelf" in p.label]
        total_shelves = sum(p.quantity for p in shelf_pieces)
        assert total_shelves == 15


class TestCabinetObjectsFromRoomConfigs:
    """Tests that room configs produce valid Cabinet domain objects."""

    def test_cabinet_has_correct_dimensions(self) -> None:
        """Test that generated cabinets have correct dimensions."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        for cabinet in result.cabinets:
            assert cabinet.height == 84
            assert cabinet.depth == 12

    def test_cabinet_has_shelves(self) -> None:
        """Test that generated cabinets have the correct number of shelves."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        for cabinet in result.cabinets:
            # Each cabinet section has 1 section with 4 shelves
            assert len(cabinet.sections) == 1
            assert len(cabinet.sections[0].shelves) == 4

    def test_cabinet_has_all_panels(self) -> None:
        """Test that generated cabinets have all required panels."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        panel_service = PanelGenerationService()
        for cabinet in result.cabinets:
            panels = panel_service.get_all_panels(cabinet)
            panel_types = {p.panel_type.value for p in panels}

            # Should have top, bottom, sides, and back
            assert "top" in panel_types
            assert "bottom" in panel_types
            assert "left_side" in panel_types
            assert "right_side" in panel_types
            assert "back" in panel_types


class TestSTLExportWithRoomTransforms:
    """Tests for STL export with room transforms."""

    def test_stl_export_single_cabinet(self, tmp_path: Path) -> None:
        """Test STL export for a single cabinet from room config."""
        config_path = FIXTURES_PATH / "room_single_wall.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid
        assert len(result.cabinets) > 0

        # Export first cabinet to STL
        exporter = StlExporter()
        stl_path = tmp_path / "cabinet.stl"
        exporter.export_to_file(result.cabinets[0], stl_path)

        assert stl_path.exists()
        assert stl_path.stat().st_size > 0

    def test_stl_export_all_cabinets(self, tmp_path: Path) -> None:
        """Test STL export for all cabinets in a room."""
        config_path = FIXTURES_PATH / "room_l_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid

        # Export each cabinet to a separate STL file
        exporter = StlExporter()
        for i, cabinet in enumerate(result.cabinets):
            stl_path = tmp_path / f"cabinet_{i}.stl"
            exporter.export_to_file(cabinet, stl_path)
            assert stl_path.exists()
            assert stl_path.stat().st_size > 0

    def test_stl_export_backward_compat_config(self, tmp_path: Path) -> None:
        """Test STL export works with v1.0 config."""
        config_path = FIXTURES_PATH / "room_backward_compat.json"
        config = load_config(config_path)

        wall_input, params_input = config_to_dtos(config)
        section_specs = config_to_section_specs(config)

        command = get_factory().create_generate_command()
        result = command.execute(wall_input, params_input, section_specs=section_specs)

        assert result.is_valid

        exporter = StlExporter()
        stl_path = tmp_path / "cabinet.stl"
        exporter.export_to_file(result.cabinet, stl_path)

        assert stl_path.exists()
        assert stl_path.stat().st_size > 0


class TestRoomGeometryValidation:
    """Tests for room geometry validation."""

    def test_l_shaped_room_valid_geometry(self) -> None:
        """Test that L-shaped room has valid geometry."""
        config_path = FIXTURES_PATH / "room_l_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        errors = room.validate_geometry()
        assert len(errors) == 0

    def test_u_shaped_room_valid_geometry(self) -> None:
        """Test that U-shaped room has valid geometry."""
        config_path = FIXTURES_PATH / "room_u_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        errors = room.validate_geometry()
        assert len(errors) == 0


class TestSectionAssignmentToWalls:
    """Tests for section assignment to walls in room configs."""

    def test_sections_assigned_to_named_walls(self) -> None:
        """Test that sections are correctly assigned to named walls."""
        config_path = FIXTURES_PATH / "room_l_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)

        service = RoomLayoutService()
        assignments = service.assign_sections_to_walls(room, section_specs)

        # First two sections on "left" wall (index 0)
        # Third section on "right" wall (index 1)
        assert assignments[0].wall_index == 0
        assert assignments[1].wall_index == 0
        assert assignments[2].wall_index == 1

    def test_sections_on_multiple_walls(self) -> None:
        """Test sections distributed across multiple walls."""
        config_path = FIXTURES_PATH / "room_u_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)

        service = RoomLayoutService()
        assignments = service.assign_sections_to_walls(room, section_specs)

        # 3 on south (index 0), 1 on west (index 1), 2 on north (index 2)
        wall_0_count = sum(1 for a in assignments if a.wall_index == 0)
        wall_1_count = sum(1 for a in assignments if a.wall_index == 1)
        wall_2_count = sum(1 for a in assignments if a.wall_index == 2)

        assert wall_0_count == 3
        assert wall_1_count == 1
        assert wall_2_count == 2


class TestFillSectionCalculation:
    """Tests for fill section width calculation in room context."""

    def test_fill_section_calculates_correct_width(self) -> None:
        """Test that fill sections calculate correct width on their wall."""
        config_path = FIXTURES_PATH / "room_u_shape.json"
        config = load_config(config_path)

        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        assert result.is_valid

        # Find the fill section (last one, on north wall)
        # North wall is 96", with one fixed 48" section
        # Fill section should be 48" (96 - 48)
        # The fill section is the 6th section (index 5)
        north_wall_cabinets = [
            c
            for i, c in enumerate(result.cabinets)
            if result.transforms[i].wall_index == 2
        ]

        # The fill cabinet should have width 48
        assert len(north_wall_cabinets) == 2
        # One should be 48", other should be 48" (fill)
        widths = [c.width for c in north_wall_cabinets]
        assert 48.0 in widths


class TestErrorHandling:
    """Tests for error handling in room configuration."""

    def test_invalid_wall_reference_in_section(self, tmp_path: Path) -> None:
        """Test error handling for invalid wall reference in section."""
        config_data = {
            "schema_version": "1.1",
            "room": {
                "name": "test-room",
                "walls": [{"length": 72, "height": 84, "angle": 0, "name": "main"}],
            },
            "cabinet": {
                "width": 72,
                "height": 84,
                "depth": 12,
                "sections": [{"width": 36, "wall": "nonexistent", "shelves": 4}],
            },
        }
        config_file = tmp_path / "invalid_wall_ref.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(config_file)
        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        # Should have an error for invalid wall reference
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("not found" in e.lower() for e in result.errors)

    def test_sections_exceeding_wall_length(self, tmp_path: Path) -> None:
        """Test error handling when sections exceed wall length."""
        config_data = {
            "schema_version": "1.1",
            "room": {
                "name": "test-room",
                "walls": [{"length": 48, "height": 84, "angle": 0, "name": "main"}],
            },
            "cabinet": {
                "width": 72,
                "height": 84,
                "depth": 12,
                "sections": [
                    {"width": 36, "wall": "main", "shelves": 4},
                    {"width": 36, "wall": "main", "shelves": 4},
                ],
            },
        }
        config_file = tmp_path / "exceeds_wall.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(config_file)
        room = config_to_room(config)
        assert room is not None

        section_specs = config_to_section_specs(config)
        _, params_input = config_to_dtos(config)

        command = get_factory().create_generate_command()
        result = command.execute_room_layout(room, section_specs, params_input)

        # Should have an error for exceeding wall length
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("exceed" in e.lower() for e in result.errors)


class TestRoomConfigWithTempFiles:
    """Tests using temporary JSON configuration files."""

    def test_create_and_load_room_config(self, tmp_path: Path) -> None:
        """Test creating and loading a room configuration file."""
        config_data = {
            "schema_version": "1.1",
            "room": {
                "name": "test-room",
                "walls": [
                    {"length": 60, "height": 90, "angle": 0, "name": "wall1"},
                    {"length": 40, "height": 90, "angle": 90, "name": "wall2"},
                ],
            },
            "cabinet": {
                "width": 60,
                "height": 90,
                "depth": 14,
                "material": {"type": "plywood", "thickness": 0.75},
                "sections": [
                    {"width": 30, "wall": "wall1", "shelves": 3},
                    {"width": 30, "wall": "wall1", "shelves": 3},
                    {"width": 40, "wall": "wall2", "shelves": 4},
                ],
            },
        }
        config_file = tmp_path / "test_room.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(config_file)

        assert config.room is not None
        assert config.room.name == "test-room"
        assert len(config.room.walls) == 2

    def test_room_config_with_closed_polygon(self, tmp_path: Path) -> None:
        """Test room configuration with is_closed flag."""
        config_data = {
            "schema_version": "1.1",
            "room": {
                "name": "closed-room",
                "walls": [
                    {"length": 48, "height": 84, "angle": 0, "name": "south"},
                    {"length": 36, "height": 84, "angle": 90, "name": "west"},
                    {"length": 48, "height": 84, "angle": 90, "name": "north"},
                    {"length": 36, "height": 84, "angle": 90, "name": "east"},
                ],
                "is_closed": True,
            },
            "cabinet": {
                "width": 48,
                "height": 84,
                "depth": 12,
                "sections": [{"width": "fill", "wall": "south", "shelves": 4}],
            },
        }
        config_file = tmp_path / "closed_room.json"
        config_file.write_text(json.dumps(config_data))

        config = load_config(config_file)
        room = config_to_room(config)

        assert room is not None
        assert room.is_closed is True

        # Validate geometry should pass (forms closed rectangle)
        errors = room.validate_geometry()
        assert len(errors) == 0
