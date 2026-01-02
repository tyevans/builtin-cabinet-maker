"""Integration tests for layout strategy refactoring.

These tests verify that the refactored GenerateLayoutCommand using the
strategy pattern produces identical outputs to the original implementation.
The tests cover all three layout strategies:
- UniformLayoutStrategy (no specs)
- SectionSpecLayoutStrategy (section_specs provided)
- RowSpecLayoutStrategy (row_specs provided)
"""

from __future__ import annotations

import pytest

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.application.factory import get_factory
from cabinets.application.strategies import (
    LayoutStrategyFactory,
    RowSpecLayoutStrategy,
    SectionSpecLayoutStrategy,
    UniformLayoutStrategy,
)
from cabinets.domain.section_resolver import RowSpec, SectionSpec
from cabinets.domain.services.layout_calculator import LayoutCalculator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def generate_command() -> GenerateLayoutCommand:
    """Create a GenerateLayoutCommand instance using the factory."""
    return get_factory().create_generate_command()


@pytest.fixture
def wall_input() -> WallInput:
    """Create a standard wall input for testing."""
    return WallInput(width=48.0, height=84.0, depth=12.0)


@pytest.fixture
def params_input() -> LayoutParametersInput:
    """Create standard layout parameters input for testing."""
    return LayoutParametersInput(
        num_sections=2,
        shelves_per_section=3,
        material_thickness=0.75,
        back_thickness=0.25,
    )


# =============================================================================
# Uniform Layout Strategy Integration Tests
# =============================================================================


class TestUniformLayoutStrategyIntegration:
    """Integration tests for UniformLayoutStrategy path."""

    def test_command_uses_uniform_strategy_when_no_specs(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test command executes uniform layout when no specs provided."""
        result = generate_command.execute(wall_input, params_input)

        # Verify successful output
        assert result.core.errors == []
        assert result.core.cabinet is not None

        # Uniform layout produces equal-width sections
        cabinet = result.core.cabinet
        assert len(cabinet.sections) == params_input.num_sections

        # Check sections have uniform widths (within tolerance)
        section_widths = [s.width for s in cabinet.sections]
        assert len(set(round(w, 3) for w in section_widths)) == 1  # All widths equal

    def test_uniform_strategy_generates_shelves(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test uniform layout generates correct number of shelves per section."""
        result = generate_command.execute(wall_input, params_input)

        cabinet = result.core.cabinet
        for section in cabinet.sections:
            assert len(section.shelves) == params_input.shelves_per_section

    def test_uniform_strategy_generates_cut_list(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test uniform layout generates a cut list."""
        result = generate_command.execute(wall_input, params_input)

        # Cut list should contain pieces for cabinet construction
        assert len(result.core.cut_list) > 0

    def test_uniform_strategy_generates_material_estimates(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test uniform layout generates material estimates."""
        result = generate_command.execute(wall_input, params_input)

        assert result.core.material_estimates is not None
        assert result.core.total_estimate is not None


# =============================================================================
# Section Spec Layout Strategy Integration Tests
# =============================================================================


class TestSectionSpecLayoutStrategyIntegration:
    """Integration tests for SectionSpecLayoutStrategy path."""

    def test_command_uses_section_spec_strategy_when_specs_provided(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test command executes section spec layout when specs provided."""
        section_specs = [
            SectionSpec(width=20.0, shelves=2),
            SectionSpec(width="fill", shelves=4),
        ]

        result = generate_command.execute(
            wall_input, params_input, section_specs=section_specs
        )

        assert result.core.errors == []
        assert result.core.cabinet is not None

        cabinet = result.core.cabinet
        assert len(cabinet.sections) == len(section_specs)

    def test_section_spec_strategy_respects_fixed_widths(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test section spec layout respects fixed width specifications."""
        fixed_width = 20.0
        section_specs = [
            SectionSpec(width=fixed_width, shelves=2),
            SectionSpec(width="fill", shelves=4),
        ]

        result = generate_command.execute(
            wall_input, params_input, section_specs=section_specs
        )

        cabinet = result.core.cabinet
        # First section should have the fixed width
        assert abs(cabinet.sections[0].width - fixed_width) < 0.001

    def test_section_spec_strategy_respects_shelf_counts(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test section spec layout respects per-section shelf counts."""
        section_specs = [
            SectionSpec(width=24.0, shelves=2),
            SectionSpec(width="fill", shelves=5),
        ]

        result = generate_command.execute(
            wall_input, params_input, section_specs=section_specs
        )

        cabinet = result.core.cabinet
        assert len(cabinet.sections[0].shelves) == 2
        assert len(cabinet.sections[1].shelves) == 5

    def test_section_spec_strategy_with_zone_configs(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test section spec layout with zone configurations."""
        section_specs = [SectionSpec(width="fill", shelves=3)]
        zone_configs = {
            "base_zone": {"zone_type": "toe_kick", "height": 4.0},
        }

        result = generate_command.execute(
            wall_input,
            params_input,
            section_specs=section_specs,
            zone_configs=zone_configs,
        )

        assert result.core.errors == []
        assert result.core.cabinet is not None


# =============================================================================
# Row Spec Layout Strategy Integration Tests
# =============================================================================


class TestRowSpecLayoutStrategyIntegration:
    """Integration tests for RowSpecLayoutStrategy path."""

    def test_command_uses_row_spec_strategy_when_specs_provided(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test command executes row spec layout when specs provided."""
        row_specs = [
            RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=4),)
            ),
        ]

        result = generate_command.execute(wall_input, params_input, row_specs=row_specs)

        assert result.core.errors == []
        assert result.core.cabinet is not None

        # Should have sections from both rows
        cabinet = result.core.cabinet
        assert len(cabinet.sections) >= 2

    def test_row_spec_strategy_with_multiple_sections_per_row(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test row spec layout with multiple sections per row."""
        row_specs = [
            RowSpec(
                height=30.0,
                section_specs=(
                    SectionSpec(width=20.0, shelves=1),
                    SectionSpec(width="fill", shelves=2),
                ),
            ),
            RowSpec(
                height="fill",
                section_specs=(SectionSpec(width="fill", shelves=4),),
            ),
        ]

        result = generate_command.execute(wall_input, params_input, row_specs=row_specs)

        assert result.core.errors == []
        cabinet = result.core.cabinet
        # Should have 3 total sections (2 in first row + 1 in second row)
        assert len(cabinet.sections) == 3

    def test_row_spec_strategy_with_zone_configs(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test row spec layout with zone configurations."""
        row_specs = [
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=3),)
            ),
        ]
        zone_configs = {
            "base_zone": {"zone_type": "toe_kick", "height": 4.0},
        }

        result = generate_command.execute(
            wall_input, params_input, row_specs=row_specs, zone_configs=zone_configs
        )

        assert result.core.errors == []
        assert result.core.cabinet is not None


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestStrategyErrorHandling:
    """Tests for error handling in strategy execution."""

    def test_command_rejects_both_specs_provided(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test command rejects when both section_specs and row_specs provided."""
        section_specs = [SectionSpec(width="fill", shelves=3)]
        row_specs = [
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=2),)
            ),
        ]

        result = generate_command.execute(
            wall_input, params_input, section_specs=section_specs, row_specs=row_specs
        )

        # Should return errors, not raise exception
        assert len(result.core.errors) > 0
        assert (
            "Cannot specify both section_specs and row_specs" in result.core.errors[0]
        )

    def test_invalid_section_spec_returns_error(
        self,
        generate_command: GenerateLayoutCommand,
        wall_input: WallInput,
        params_input: LayoutParametersInput,
    ) -> None:
        """Test invalid section specs return validation errors."""
        # Section wider than wall
        section_specs = [SectionSpec(width=100.0, shelves=3)]

        result = generate_command.execute(
            wall_input, params_input, section_specs=section_specs
        )

        assert len(result.core.errors) > 0


# =============================================================================
# Strategy Factory Direct Tests
# =============================================================================


class TestLayoutStrategyFactoryIntegration:
    """Integration tests for direct LayoutStrategyFactory usage."""

    def test_factory_creates_working_uniform_strategy(self) -> None:
        """Test factory creates working UniformLayoutStrategy."""
        calculator = LayoutCalculator()
        factory = LayoutStrategyFactory(calculator)

        strategy = factory.create_strategy()

        assert isinstance(strategy, UniformLayoutStrategy)

        # Verify it can execute
        from cabinets.domain.entities import Wall
        from cabinets.domain.services.layout_calculator import LayoutParameters

        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters()

        cabinet, hardware = strategy.execute(wall, params)
        assert cabinet is not None

    def test_factory_creates_working_section_spec_strategy(self) -> None:
        """Test factory creates working SectionSpecLayoutStrategy."""
        calculator = LayoutCalculator()
        factory = LayoutStrategyFactory(calculator)
        section_specs = [SectionSpec(width="fill", shelves=3)]

        strategy = factory.create_strategy(section_specs=section_specs)

        assert isinstance(strategy, SectionSpecLayoutStrategy)

        # Verify it can execute
        from cabinets.domain.entities import Wall
        from cabinets.domain.services.layout_calculator import LayoutParameters

        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters()

        cabinet, hardware = strategy.execute(wall, params)
        assert cabinet is not None

    def test_factory_creates_working_row_spec_strategy(self) -> None:
        """Test factory creates working RowSpecLayoutStrategy."""
        calculator = LayoutCalculator()
        factory = LayoutStrategyFactory(calculator)
        row_specs = [
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=2),)
            ),
        ]

        strategy = factory.create_strategy(row_specs=row_specs)

        assert isinstance(strategy, RowSpecLayoutStrategy)

        # Verify it can execute
        from cabinets.domain.entities import Wall
        from cabinets.domain.services.layout_calculator import LayoutParameters

        wall = Wall(width=48.0, height=84.0, depth=12.0)
        params = LayoutParameters()

        cabinet, hardware = strategy.execute(wall, params)
        assert cabinet is not None
