"""Unit tests for layout strategy pattern implementation.

This module tests the Strategy pattern classes used for cabinet layout generation:
- LayoutStrategyFactory: Selects the correct strategy based on inputs
- UniformLayoutStrategy: Equal-width sections with uniform shelves
- SectionSpecLayoutStrategy: Custom section widths and shelf counts
- RowSpecLayoutStrategy: Multi-row cabinets with vertical stacking
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from cabinets.application.strategies import (
    LayoutStrategyFactory,
    RowSpecLayoutStrategy,
    SectionSpecLayoutStrategy,
    UniformLayoutStrategy,
)
from cabinets.contracts.strategies import LayoutStrategy
from cabinets.domain.entities import Cabinet, Wall
from cabinets.domain.section_resolver import RowSpec, SectionSpec
from cabinets.domain.services.layout_calculator import (
    LayoutCalculator,
    LayoutParameters,
)
from cabinets.domain.value_objects import MaterialSpec

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def wall() -> Wall:
    """Create a standard wall for testing."""
    return Wall(width=48.0, height=84.0, depth=12.0)


@pytest.fixture
def layout_params() -> LayoutParameters:
    """Create standard layout parameters for testing."""
    return LayoutParameters(
        num_sections=2,
        shelves_per_section=3,
        material=MaterialSpec.standard_3_4(),
        back_material=MaterialSpec.standard_1_4(),
    )


@pytest.fixture
def mock_calculator() -> Mock:
    """Create a mock layout calculator."""
    calculator = Mock(spec=LayoutCalculator)

    # Mock generate_cabinet to return a cabinet with empty hardware list
    mock_cabinet = Mock(spec=Cabinet)
    calculator.generate_cabinet.return_value = mock_cabinet
    calculator.generate_cabinet_from_specs.return_value = (mock_cabinet, [])
    calculator.generate_cabinet_from_row_specs.return_value = (mock_cabinet, [])

    return calculator


@pytest.fixture
def layout_calculator() -> LayoutCalculator:
    """Create a real layout calculator for integration-style tests."""
    return LayoutCalculator()


# =============================================================================
# LayoutStrategyFactory Tests
# =============================================================================


class TestLayoutStrategyFactory:
    """Tests for LayoutStrategyFactory."""

    def test_factory_creates_uniform_strategy_when_no_specs(
        self, mock_calculator: Mock
    ) -> None:
        """Test factory creates UniformLayoutStrategy when no specs provided."""
        factory = LayoutStrategyFactory(mock_calculator)

        strategy = factory.create_strategy()

        assert isinstance(strategy, UniformLayoutStrategy)

    def test_factory_creates_section_spec_strategy(self, mock_calculator: Mock) -> None:
        """Test factory creates SectionSpecLayoutStrategy when section_specs provided."""
        factory = LayoutStrategyFactory(mock_calculator)
        section_specs = [SectionSpec(width="fill", shelves=3)]

        strategy = factory.create_strategy(section_specs=section_specs)

        assert isinstance(strategy, SectionSpecLayoutStrategy)

    def test_factory_creates_row_spec_strategy(self, mock_calculator: Mock) -> None:
        """Test factory creates RowSpecLayoutStrategy when row_specs provided."""
        factory = LayoutStrategyFactory(mock_calculator)
        row_specs = [
            RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
        ]

        strategy = factory.create_strategy(row_specs=row_specs)

        assert isinstance(strategy, RowSpecLayoutStrategy)

    def test_factory_raises_error_when_both_specs_provided(
        self, mock_calculator: Mock
    ) -> None:
        """Test factory raises ValueError when both section_specs and row_specs provided."""
        factory = LayoutStrategyFactory(mock_calculator)
        section_specs = [SectionSpec(width="fill", shelves=3)]
        row_specs = [
            RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
        ]

        with pytest.raises(
            ValueError, match="Cannot specify both section_specs and row_specs"
        ):
            factory.create_strategy(section_specs=section_specs, row_specs=row_specs)

    def test_factory_returns_layout_strategy_protocol(
        self, mock_calculator: Mock
    ) -> None:
        """Test that all created strategies implement LayoutStrategy protocol."""
        factory = LayoutStrategyFactory(mock_calculator)
        section_specs = [SectionSpec(width="fill", shelves=3)]
        row_specs = [
            RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
        ]

        uniform = factory.create_strategy()
        section_spec = factory.create_strategy(section_specs=section_specs)
        row_spec = factory.create_strategy(row_specs=row_specs)

        # All strategies should satisfy the LayoutStrategy protocol
        assert isinstance(uniform, LayoutStrategy)
        assert isinstance(section_spec, LayoutStrategy)
        assert isinstance(row_spec, LayoutStrategy)


# =============================================================================
# UniformLayoutStrategy Tests
# =============================================================================


class TestUniformLayoutStrategy:
    """Tests for UniformLayoutStrategy."""

    def test_execute_calls_generate_cabinet(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute calls generate_cabinet on the calculator."""
        strategy = UniformLayoutStrategy(mock_calculator)

        cabinet, hardware = strategy.execute(wall, layout_params)

        mock_calculator.generate_cabinet.assert_called_once_with(wall, layout_params)

    def test_execute_returns_empty_hardware_list(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute returns empty hardware list for uniform layout."""
        strategy = UniformLayoutStrategy(mock_calculator)

        cabinet, hardware = strategy.execute(wall, layout_params)

        assert hardware == []

    def test_execute_ignores_zone_configs(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute ignores zone_configs (uniform layout doesn't support zones)."""
        strategy = UniformLayoutStrategy(mock_calculator)
        zone_configs = {"base_zone": {"zone_type": "toe_kick", "height": 4.0}}

        cabinet, hardware = strategy.execute(
            wall, layout_params, zone_configs=zone_configs
        )

        # generate_cabinet should still be called without zone_configs
        mock_calculator.generate_cabinet.assert_called_once_with(wall, layout_params)

    def test_execute_with_real_calculator(
        self,
        layout_calculator: LayoutCalculator,
        wall: Wall,
        layout_params: LayoutParameters,
    ) -> None:
        """Test execute works with real layout calculator."""
        strategy = UniformLayoutStrategy(layout_calculator)

        cabinet, hardware = strategy.execute(wall, layout_params)

        assert isinstance(cabinet, Cabinet)
        assert cabinet.width == wall.width
        assert cabinet.height == wall.height
        assert len(cabinet.sections) == layout_params.num_sections
        assert hardware == []


# =============================================================================
# SectionSpecLayoutStrategy Tests
# =============================================================================


class TestSectionSpecLayoutStrategy:
    """Tests for SectionSpecLayoutStrategy."""

    def test_execute_calls_generate_cabinet_from_specs(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute calls generate_cabinet_from_specs on the calculator."""
        section_specs = [
            SectionSpec(width=24.0, shelves=3),
            SectionSpec(width="fill", shelves=5),
        ]
        strategy = SectionSpecLayoutStrategy(mock_calculator, section_specs)

        cabinet, hardware = strategy.execute(wall, layout_params)

        mock_calculator.generate_cabinet_from_specs.assert_called_once_with(
            wall=wall,
            params=layout_params,
            section_specs=section_specs,
            zone_configs=None,
        )

    def test_execute_passes_zone_configs(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute passes zone_configs to calculator."""
        section_specs = [SectionSpec(width="fill", shelves=3)]
        strategy = SectionSpecLayoutStrategy(mock_calculator, section_specs)
        zone_configs = {"base_zone": {"zone_type": "toe_kick", "height": 4.0}}

        cabinet, hardware = strategy.execute(
            wall, layout_params, zone_configs=zone_configs
        )

        mock_calculator.generate_cabinet_from_specs.assert_called_once_with(
            wall=wall,
            params=layout_params,
            section_specs=section_specs,
            zone_configs=zone_configs,
        )

    def test_execute_with_real_calculator(
        self,
        layout_calculator: LayoutCalculator,
        wall: Wall,
        layout_params: LayoutParameters,
    ) -> None:
        """Test execute works with real layout calculator."""
        section_specs = [
            SectionSpec(width=20.0, shelves=2),
            SectionSpec(width="fill", shelves=4),
        ]
        strategy = SectionSpecLayoutStrategy(layout_calculator, section_specs)

        cabinet, hardware = strategy.execute(wall, layout_params)

        assert isinstance(cabinet, Cabinet)
        assert cabinet.width == wall.width
        assert len(cabinet.sections) == len(section_specs)


# =============================================================================
# RowSpecLayoutStrategy Tests
# =============================================================================


class TestRowSpecLayoutStrategy:
    """Tests for RowSpecLayoutStrategy."""

    def test_execute_calls_generate_cabinet_from_row_specs(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute calls generate_cabinet_from_row_specs on the calculator."""
        row_specs = [
            RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=4),)
            ),
        ]
        strategy = RowSpecLayoutStrategy(mock_calculator, row_specs)

        cabinet, hardware = strategy.execute(wall, layout_params)

        mock_calculator.generate_cabinet_from_row_specs.assert_called_once_with(
            wall=wall,
            params=layout_params,
            row_specs=row_specs,
            zone_configs=None,
        )

    def test_execute_passes_zone_configs(
        self, mock_calculator: Mock, wall: Wall, layout_params: LayoutParameters
    ) -> None:
        """Test execute passes zone_configs to calculator."""
        row_specs = [
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=3),)
            ),
        ]
        strategy = RowSpecLayoutStrategy(mock_calculator, row_specs)
        zone_configs = {"base_zone": {"zone_type": "toe_kick", "height": 4.0}}

        cabinet, hardware = strategy.execute(
            wall, layout_params, zone_configs=zone_configs
        )

        mock_calculator.generate_cabinet_from_row_specs.assert_called_once_with(
            wall=wall,
            params=layout_params,
            row_specs=row_specs,
            zone_configs=zone_configs,
        )

    def test_execute_with_real_calculator(
        self,
        layout_calculator: LayoutCalculator,
        wall: Wall,
        layout_params: LayoutParameters,
    ) -> None:
        """Test execute works with real layout calculator."""
        row_specs = [
            RowSpec(height=30.0, section_specs=(SectionSpec(width="fill", shelves=2),)),
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=4),)
            ),
        ]
        strategy = RowSpecLayoutStrategy(layout_calculator, row_specs)

        cabinet, hardware = strategy.execute(wall, layout_params)

        assert isinstance(cabinet, Cabinet)
        assert cabinet.width == wall.width
        # Cabinet should have sections from all rows
        assert len(cabinet.sections) >= 2


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestLayoutStrategyProtocol:
    """Tests for LayoutStrategy protocol compliance."""

    def test_all_strategies_are_runtime_checkable(self, mock_calculator: Mock) -> None:
        """Test that all strategies pass runtime protocol checks."""
        section_specs = [SectionSpec(width="fill", shelves=3)]
        row_specs = [
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=2),)
            ),
        ]

        uniform = UniformLayoutStrategy(mock_calculator)
        section_spec = SectionSpecLayoutStrategy(mock_calculator, section_specs)
        row_spec = RowSpecLayoutStrategy(mock_calculator, row_specs)

        # Runtime protocol check
        assert isinstance(uniform, LayoutStrategy)
        assert isinstance(section_spec, LayoutStrategy)
        assert isinstance(row_spec, LayoutStrategy)

    def test_strategies_have_execute_method(self, mock_calculator: Mock) -> None:
        """Test all strategies have the execute method with correct signature."""
        section_specs = [SectionSpec(width="fill", shelves=3)]
        row_specs = [
            RowSpec(
                height="fill", section_specs=(SectionSpec(width="fill", shelves=2),)
            ),
        ]

        strategies = [
            UniformLayoutStrategy(mock_calculator),
            SectionSpecLayoutStrategy(mock_calculator, section_specs),
            RowSpecLayoutStrategy(mock_calculator, row_specs),
        ]

        for strategy in strategies:
            assert hasattr(strategy, "execute")
            assert callable(strategy.execute)
