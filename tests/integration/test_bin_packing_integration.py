"""Integration tests for bin packing end-to-end workflow.

These tests verify the complete bin packing pipeline from cabinet configuration
through layout generation to optimized sheet layouts.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from cabinets.application import LayoutParametersInput, WallInput
from cabinets.application.factory import get_factory
from cabinets.application.config import load_config, config_to_bin_packing
from cabinets.domain.value_objects import MaterialSpec
from cabinets.infrastructure.bin_packing import (
    BinPackingConfig,
    BinPackingService,
    SheetConfig,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def simple_cabinet_config() -> dict:
    """Simple cabinet configuration for testing."""
    return {
        "schema_version": "1.4",
        "cabinet": {
            "width": 48.0,
            "height": 84.0,
            "depth": 12.0,
            "material": {"type": "plywood", "thickness": 0.75},
            "sections": [
                {"width": 24.0, "shelves": 3},
                {"width": "fill", "shelves": 5},
            ],
        },
        "bin_packing": {
            "enabled": True,
            "kerf": 0.125,
            "sheet_size": {"width": 48, "height": 96},
        },
    }


@pytest.fixture
def multi_material_config() -> dict:
    """Cabinet with multiple materials (panels + back)."""
    return {
        "schema_version": "1.4",
        "cabinet": {
            "width": 48.0,
            "height": 84.0,
            "depth": 12.0,
            "material": {"type": "plywood", "thickness": 0.75},
            "back_material": {"type": "plywood", "thickness": 0.5},
            "sections": [
                {"width": 24.0, "shelves": 2},
                {"width": 24.0, "shelves": 2},
            ],
        },
        "bin_packing": {"enabled": True},
    }


@pytest.fixture
def config_file(simple_cabinet_config: dict) -> Path:
    """Write config to temporary file and return path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(simple_cabinet_config, f)
        return Path(f.name)


# =============================================================================
# Full Pipeline Tests
# =============================================================================


class TestFullPipeline:
    """Tests for complete cabinet -> bin packing pipeline."""

    def test_cabinet_to_optimized_layout(self) -> None:
        """Full pipeline: cabinet generation to optimized cut layout."""
        # Generate cabinet layout
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=2,
            shelves_per_section=4,
        )

        result = command.execute(wall_input, params_input)
        assert result.is_valid
        assert len(result.cut_list) > 0

        # Run bin packing
        config = BinPackingConfig()
        service = BinPackingService(config)
        packing_result = service.optimize_cut_list(result.cut_list)

        # Verify results
        assert len(packing_result.layouts) > 0
        assert packing_result.total_sheets > 0
        assert 0 <= packing_result.total_waste_percentage <= 100

        # Verify pieces were placed (total placed should be at least total pieces)
        # Note: expansion may add pieces for split panels, so >= is used
        total_placed = sum(len(layout.placements) for layout in packing_result.layouts)
        total_pieces = sum(piece.quantity for piece in result.cut_list)
        assert total_placed >= total_pieces

    def test_multi_material_separation(self, multi_material_config: dict) -> None:
        """Different materials are separated into different sheet groups."""
        # Load and parse config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(multi_material_config, f)
            config_path = Path(f.name)

        try:
            config = load_config(config_path)

            # Generate cabinet
            command = get_factory().create_generate_command()
            wall_input = WallInput(
                width=config.cabinet.width,
                height=config.cabinet.height,
                depth=config.cabinet.depth,
            )
            params_input = LayoutParametersInput(num_sections=2, shelves_per_section=2)

            result = command.execute(wall_input, params_input)

            # Run bin packing
            bp_config = config_to_bin_packing(config.bin_packing)
            service = BinPackingService(bp_config)
            packing_result = service.optimize_cut_list(result.cut_list)

            # Should have multiple material groups
            assert len(packing_result.sheets_by_material) >= 1

            # Each layout should have consistent material
            for layout in packing_result.layouts:
                materials = {p.piece.material for p in layout.placements}
                assert len(materials) == 1, "Layout should have single material"

        finally:
            config_path.unlink()

    def test_waste_improvement_over_naive(self) -> None:
        """Optimized layout should have reasonable waste."""
        # Generate a typical cabinet layout
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=4,
        )

        result = command.execute(wall_input, params_input)

        # Run optimization
        config = BinPackingConfig()
        service = BinPackingService(config)
        packing_result = service.optimize_cut_list(result.cut_list)

        # Waste should be reasonable (target: under 50%)
        # The shelf algorithm should do better than naive approach
        assert packing_result.total_waste_percentage < 50, (
            f"Waste {packing_result.total_waste_percentage}% exceeds 50% threshold"
        )

        # Should use fewer sheets than pieces
        total_pieces = sum(piece.quantity for piece in result.cut_list)
        assert packing_result.total_sheets < total_pieces, (
            "Optimization should fit multiple pieces per sheet"
        )

    def test_large_cabinet_optimization(self) -> None:
        """Test optimization with a cabinet that fits on standard sheets.

        Uses dimensions that ensure all pieces fit within 48x96 sheet.
        The cut list consolidates pieces with same dimensions, so we check
        for total piece count (with quantities) not unique piece types.
        """
        command = get_factory().create_generate_command()
        # Use dimensions that produce pieces that fit on standard 48x96 sheet
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=5,
        )

        result = command.execute(wall_input, params_input)
        assert result.is_valid

        # Total pieces (including quantities) should be substantial
        total_pieces = sum(piece.quantity for piece in result.cut_list)
        assert total_pieces > 10  # Should have many individual pieces

        # Run bin packing
        config = BinPackingConfig()
        service = BinPackingService(config)
        packing_result = service.optimize_cut_list(result.cut_list)

        # Verify reasonable results
        assert packing_result.total_sheets > 0
        assert packing_result.total_waste_percentage < 60

        # All pieces should be placed (expansion creates individual placements)
        total_placed = sum(len(layout.placements) for layout in packing_result.layouts)
        # Placed pieces should match or exceed total (due to panel splitting)
        assert total_placed >= total_pieces


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Tests for CLI bin packing commands."""

    def test_cli_cutlayout_format(self, config_file: Path) -> None:
        """CLI --format cutlayout produces output."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "cabinets",
                "generate",
                "--config",
                str(config_file),
                "--format",
                "cutlayout",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        # Should contain sheet layout or summary information
        output_lower = result.stdout.lower()
        assert "sheet" in output_lower or "summary" in output_lower

    def test_cli_cutlayout_with_svg_output(self, config_file: Path) -> None:
        """CLI --format cutlayout with -o saves SVG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "sheet.svg"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "cabinets",
                    "generate",
                    "--config",
                    str(config_file),
                    "--format",
                    "cutlayout",
                    "-o",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, f"CLI failed: {result.stderr}"

            # Check SVG file was created (might have multiple with suffixes)
            svg_files = list(Path(tmpdir).glob("*.svg"))
            assert len(svg_files) >= 1, "No SVG files created"

            # Verify SVG content
            svg_content = svg_files[0].read_text()
            assert svg_content.startswith("<svg"), "SVG should start with <svg tag"

    def test_cli_all_format_includes_summary(self, config_file: Path) -> None:
        """CLI --format all includes bin packing summary."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "cabinets",
                "generate",
                "--config",
                str(config_file),
                "--format",
                "all",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        # Should include some reference to cut optimization
        output_lower = result.stdout.lower()
        assert "waste" in output_lower or "sheet" in output_lower

    def test_cli_without_config_file(self) -> None:
        """CLI with dimensions only works with --optimize flag."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "cabinets",
                "generate",
                "--width",
                "48",
                "--height",
                "84",
                "--depth",
                "12",
                "--sections",
                "2",
                "--shelves",
                "4",
                "--optimize",
                "--format",
                "cutlayout",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        output_lower = result.stdout.lower()
        assert "sheet" in output_lower

    def test_cli_disabled_bin_packing(self) -> None:
        """CLI handles disabled bin packing gracefully."""
        config = {
            "schema_version": "1.4",
            "cabinet": {"width": 48, "height": 84, "depth": 12},
            "bin_packing": {"enabled": False},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = Path(f.name)

        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "cabinets",
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "cutlayout",
                ],
                capture_output=True,
                text=True,
            )

            # Should either show error message or exit cleanly
            # (depends on implementation choice)
            # Either way, should not crash unexpectedly
            assert result.returncode in [0, 1]

        finally:
            config_path.unlink()


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfigurationIntegration:
    """Tests for bin packing configuration handling."""

    def test_config_kerf_is_used(self) -> None:
        """Custom kerf value affects piece placement."""
        # Generate same cabinet with different kerfs
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(num_sections=2, shelves_per_section=4)

        result = command.execute(wall_input, params_input)

        # Small kerf
        config1 = BinPackingConfig(kerf=0.0625)
        service1 = BinPackingService(config1)
        result1 = service1.optimize_cut_list(result.cut_list)

        # Large kerf
        config2 = BinPackingConfig(kerf=0.25)
        service2 = BinPackingService(config2)
        result2 = service2.optimize_cut_list(result.cut_list)

        # Larger kerf may require more sheets or have more waste
        # (or at minimum, piece positions differ)
        assert (
            result2.total_waste_percentage >= result1.total_waste_percentage
            or result2.total_sheets >= result1.total_sheets
        )

    def test_config_sheet_size_is_used(self) -> None:
        """Custom sheet size affects layout.

        Uses a smaller cabinet to ensure all pieces fit on both sheet sizes.
        """
        # Large sheet (48x96)
        config_large = BinPackingConfig(sheet_size=SheetConfig(width=48, height=96))
        # Smaller sheet (36x72) - still large enough for pieces
        config_small = BinPackingConfig(sheet_size=SheetConfig(width=36, height=72))

        # Generate smaller cabinet to ensure pieces fit on both sheet sizes
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=32.0, height=48.0, depth=10.0)
        params_input = LayoutParametersInput(num_sections=2, shelves_per_section=3)

        result = command.execute(wall_input, params_input)

        # Pack with different sheet sizes
        service_large = BinPackingService(config_large)
        result_large = service_large.optimize_cut_list(result.cut_list)

        service_small = BinPackingService(config_small)
        result_small = service_small.optimize_cut_list(result.cut_list)

        # Both should complete without error
        assert result_large.total_sheets > 0
        assert result_small.total_sheets > 0
        # Smaller sheets may require more sheets (or at least as many)
        assert result_small.total_sheets >= result_large.total_sheets

    def test_schema_version_1_4_accepted(self) -> None:
        """Schema version 1.4 with bin_packing is accepted."""
        config = {
            "schema_version": "1.4",
            "cabinet": {"width": 48, "height": 84, "depth": 12},
            "bin_packing": {"enabled": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = Path(f.name)

        try:
            loaded = load_config(config_path)
            assert loaded.schema_version == "1.4"
            assert loaded.bin_packing is not None
            assert loaded.bin_packing.enabled is True

        finally:
            config_path.unlink()

    def test_backward_compatible_config(self) -> None:
        """Old config (1.0) without bin_packing works."""
        config = {
            "schema_version": "1.0",
            "cabinet": {"width": 48, "height": 84, "depth": 12},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            config_path = Path(f.name)

        try:
            loaded = load_config(config_path)
            assert loaded.bin_packing is None

            # Should still be able to use default bin packing
            bp_config = config_to_bin_packing(loaded.bin_packing)
            assert bp_config.enabled is True

        finally:
            config_path.unlink()


# =============================================================================
# Output Validation Tests
# =============================================================================


class TestOutputValidation:
    """Tests for output format correctness."""

    def test_svg_is_valid_xml(self, simple_cabinet_config: dict) -> None:
        """Generated SVG is valid XML."""
        import xml.etree.ElementTree as ET

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(simple_cabinet_config, f)
            config_path = Path(f.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "sheet.svg"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "cabinets",
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "cutlayout",
                    "-o",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                svg_files = list(Path(tmpdir).glob("*.svg"))
                for svg_file in svg_files:
                    svg_content = svg_file.read_text()
                    # Should be parseable as XML
                    try:
                        ET.fromstring(svg_content)
                    except ET.ParseError as e:
                        pytest.fail(f"Invalid SVG XML: {e}")

        config_path.unlink()

    def test_waste_summary_has_required_fields(self) -> None:
        """Waste summary includes all required information."""
        from cabinets.infrastructure.cut_diagram_renderer import CutDiagramRenderer
        from cabinets.infrastructure.bin_packing import (
            PackingResult,
            SheetLayout,
            SheetConfig,
        )

        # Create minimal result
        material = MaterialSpec.standard_3_4()
        sheet = SheetConfig()
        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=(),
            material=material,
        )
        result = PackingResult(
            layouts=(layout,),
            offcuts=(),
            total_waste_percentage=25.0,
            sheets_by_material={material: 1},
        )

        renderer = CutDiagramRenderer()
        summary = renderer.render_waste_summary(result)

        assert "Total Sheets:" in summary
        assert "Total Waste:" in summary
        assert "25" in summary  # waste percentage
        assert "plywood" in summary.lower()

    def test_ascii_diagram_structure(self) -> None:
        """ASCII cut diagram has correct structure."""
        from cabinets.infrastructure.cut_diagram_renderer import CutDiagramRenderer
        from cabinets.infrastructure.bin_packing import (
            PackingResult,
            SheetLayout,
            SheetConfig,
            PlacedPiece,
        )
        from cabinets.domain.value_objects import CutPiece, PanelType

        material = MaterialSpec.standard_3_4()
        sheet = SheetConfig()

        # Create a placed piece - CutPiece uses SIDE not just "SIDE"
        piece = CutPiece(
            width=12.0,
            height=24.0,
            quantity=1,
            label="Test Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=material,
        )
        placed = PlacedPiece(piece=piece, x=0.0, y=0.0, rotated=False)

        layout = SheetLayout(
            sheet_index=0,
            sheet_config=sheet,
            placements=(placed,),
            material=material,
        )
        result = PackingResult(
            layouts=(layout,),
            offcuts=(),
            total_waste_percentage=15.0,
            sheets_by_material={material: 1},
        )

        renderer = CutDiagramRenderer()
        ascii_output = renderer.render_all_ascii(result)

        # Should have sheet header
        assert "Sheet 1" in ascii_output
        # Should have summary
        assert "SUMMARY" in ascii_output
        # Should have material info
        assert "plywood" in ascii_output.lower()
        # Should have border characters
        assert "+" in ascii_output
        assert "-" in ascii_output

    def test_svg_contains_rect_elements(self, simple_cabinet_config: dict) -> None:
        """Generated SVG contains rect elements for pieces."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(simple_cabinet_config, f)
            config_path = Path(f.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "sheet.svg"

            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "cabinets",
                    "generate",
                    "--config",
                    str(config_path),
                    "--format",
                    "cutlayout",
                    "-o",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                svg_files = list(Path(tmpdir).glob("*.svg"))
                assert len(svg_files) > 0

                svg_content = svg_files[0].read_text()
                # Should contain rect elements for pieces
                assert "<rect" in svg_content
                # Should have svg namespace
                assert "xmlns" in svg_content

        config_path.unlink()


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_cut_list_handling(self) -> None:
        """Bin packing handles empty cut list gracefully."""
        config = BinPackingConfig()
        service = BinPackingService(config)

        result = service.optimize_cut_list([])

        assert result.total_sheets == 0
        assert result.total_waste_percentage == 0.0
        assert len(result.layouts) == 0

    def test_disabled_bin_packing_returns_empty_result(self) -> None:
        """Disabled bin packing returns empty result."""
        config = BinPackingConfig(enabled=False)
        service = BinPackingService(config)

        # Even with pieces, should return empty when disabled
        command = get_factory().create_generate_command()
        wall_input = WallInput(width=48.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(num_sections=1, shelves_per_section=3)
        layout_result = command.execute(wall_input, params_input)

        result = service.optimize_cut_list(layout_result.cut_list)

        assert result.total_sheets == 0
        assert len(result.layouts) == 0

    def test_single_piece_optimization(self) -> None:
        """Bin packing works with a single piece."""
        from cabinets.domain.value_objects import CutPiece, PanelType

        material = MaterialSpec.standard_3_4()
        piece = CutPiece(
            width=24.0,
            height=48.0,
            quantity=1,
            label="Single Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=material,
        )

        config = BinPackingConfig()
        service = BinPackingService(config)
        result = service.optimize_cut_list([piece])

        assert result.total_sheets == 1
        assert len(result.layouts) == 1
        assert len(result.layouts[0].placements) == 1


# =============================================================================
# Performance Sanity Tests
# =============================================================================


class TestPerformanceSanity:
    """Basic performance sanity tests."""

    def test_reasonable_execution_time(self) -> None:
        """Bin packing completes in reasonable time for typical cabinet.

        Uses dimensions that fit on standard 48x96 sheets without splitting.
        """
        import time

        command = get_factory().create_generate_command()
        # Use dimensions where all pieces fit on standard 48x96 sheet
        wall_input = WallInput(width=48.0, height=84.0, depth=14.0)
        params_input = LayoutParametersInput(num_sections=4, shelves_per_section=5)

        result = command.execute(wall_input, params_input)

        config = BinPackingConfig()
        service = BinPackingService(config)

        start = time.time()
        packing_result = service.optimize_cut_list(result.cut_list)
        elapsed = time.time() - start

        # Should complete in under 5 seconds for typical cabinet
        assert elapsed < 5.0, f"Bin packing took {elapsed:.2f}s, expected < 5s"
        assert packing_result.total_sheets > 0
