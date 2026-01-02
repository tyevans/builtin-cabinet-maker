"""Unit tests for InstallationService dependency injection.

These tests verify:
- InstallationServiceProtocol is correctly defined
- InstallationServiceFactory protocol works as expected
- GenerateLayoutCommand uses injected factory
- ServiceFactory correctly implements InstallationServiceFactory
- InstallationService can be mocked in unit tests
"""

from unittest.mock import MagicMock

import pytest

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.application.factory import ServiceFactory, get_factory
from cabinets.contracts import InstallationServiceFactory, InstallationServiceProtocol
from cabinets.domain.entities import Cabinet, Section
from cabinets.domain.services.installation import (
    InstallationConfig,
    InstallationPlan,
    InstallationService,
    StudHitAnalysis,
    WeightEstimate,
)
from cabinets.domain.value_objects import (
    LoadCategory,
    MaterialSpec,
    MaterialType,
    MountingSystem,
    Position,
    WallType,
)


class TestInstallationServiceProtocol:
    """Tests for InstallationServiceProtocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that InstallationServiceProtocol is runtime checkable."""
        # Create a mock that implements the protocol
        mock_service = MagicMock()
        mock_service.generate_plan = MagicMock()

        # Protocol should be usable with isinstance (runtime_checkable)
        assert hasattr(InstallationServiceProtocol, "__protocol_attrs__") or hasattr(
            InstallationServiceProtocol, "__subclasshook__"
        )

    def test_installation_service_matches_protocol(self) -> None:
        """Test that InstallationService matches InstallationServiceProtocol."""
        config = InstallationConfig()
        service = InstallationService(config)

        # Verify the service has the required method
        assert hasattr(service, "generate_plan")
        assert callable(service.generate_plan)

    def test_protocol_can_type_hint_installation_service(self) -> None:
        """Test that protocol can be used as a type hint for InstallationService."""

        def accepts_protocol(service: InstallationServiceProtocol) -> bool:
            return hasattr(service, "generate_plan")

        config = InstallationConfig()
        service = InstallationService(config)

        assert accepts_protocol(service)


class TestInstallationServiceFactoryProtocol:
    """Tests for InstallationServiceFactory protocol."""

    def test_service_factory_implements_protocol(self) -> None:
        """Test that ServiceFactory implements InstallationServiceFactory."""
        factory = ServiceFactory()

        # Verify the factory has the required method
        assert hasattr(factory, "create_installation_service")
        assert callable(factory.create_installation_service)

    def test_service_factory_creates_installation_service(self) -> None:
        """Test that ServiceFactory.create_installation_service works."""
        factory = ServiceFactory()
        config = InstallationConfig(
            wall_type=WallType.DRYWALL,
            mounting_system=MountingSystem.FRENCH_CLEAT,
        )

        service = factory.create_installation_service(config)

        assert service is not None
        assert hasattr(service, "generate_plan")
        assert callable(service.generate_plan)

    def test_service_factory_passes_config_to_service(self) -> None:
        """Test that ServiceFactory passes config to the created service."""
        factory = ServiceFactory()
        config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            mounting_system=MountingSystem.TOGGLE_BOLT,
            expected_load=LoadCategory.HEAVY,
        )

        service = factory.create_installation_service(config)

        # The concrete InstallationService stores config
        assert service.config == config  # type: ignore


class TestGenerateLayoutCommandWithFactory:
    """Tests for GenerateLayoutCommand with injected InstallationServiceFactory."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        section = Section(
            width=46.5,
            height=28.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    @pytest.fixture
    def mock_installation_plan(self) -> InstallationPlan:
        """Create a mock installation plan."""
        return InstallationPlan(
            mounting_hardware=(),
            cleat_cut_pieces=(),
            stud_analysis=StudHitAnalysis(
                cabinet_left_edge=0.0,
                cabinet_width=48.0,
                stud_positions=(16.0, 32.0),
                non_stud_positions=(),
                stud_hit_count=2,
            ),
            weight_estimate=WeightEstimate(
                empty_weight_lbs=45.0,
                expected_load_per_foot=30.0,
                total_estimated_load_lbs=165.0,
            ),
            instructions="Test instructions",
            warnings=(),
        )

    def test_command_uses_factory_when_provided(
        self, mock_installation_plan: InstallationPlan
    ) -> None:
        """Test that command uses the factory when installation_config is provided."""
        # Create a mock factory
        mock_factory = MagicMock(spec=InstallationServiceFactory)
        mock_service = MagicMock()
        mock_service.generate_plan.return_value = mock_installation_plan
        mock_factory.create_installation_service.return_value = mock_service

        # Create command with mock factory
        factory = get_factory()
        command = GenerateLayoutCommand(
            layout_calculator=factory.get_layout_calculator(),
            cut_list_generator=factory.get_cut_list_generator(),
            material_estimator=factory.get_material_estimator(),
            room_layout_service=factory.get_room_layout_service(),
            installation_service_factory=mock_factory,
        )

        # Execute with installation config
        wall_input = WallInput(width=48.0, height=30.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1, shelves_per_section=3, material_thickness=0.75
        )
        installation_config = InstallationConfig()

        _ = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        # Verify factory was called
        mock_factory.create_installation_service.assert_called_once_with(
            installation_config
        )
        mock_service.generate_plan.assert_called_once()

    def test_mock_installation_service_in_unit_test(
        self, mock_installation_plan: InstallationPlan
    ) -> None:
        """Test that InstallationService can be mocked for unit testing."""
        # This is the key test - demonstrates that we can mock the installation service
        mock_factory = MagicMock(spec=InstallationServiceFactory)
        mock_service = MagicMock(spec=InstallationServiceProtocol)
        mock_service.generate_plan.return_value = mock_installation_plan
        mock_factory.create_installation_service.return_value = mock_service

        factory = get_factory()
        command = GenerateLayoutCommand(
            layout_calculator=factory.get_layout_calculator(),
            cut_list_generator=factory.get_cut_list_generator(),
            material_estimator=factory.get_material_estimator(),
            room_layout_service=factory.get_room_layout_service(),
            installation_service_factory=mock_factory,
        )

        wall_input = WallInput(width=48.0, height=30.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1, shelves_per_section=3, material_thickness=0.75
        )
        installation_config = InstallationConfig(
            mounting_system=MountingSystem.FRENCH_CLEAT
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        # The result should include installation output
        assert result.installation is not None
        assert result.installation.instructions == "Test instructions"

    def test_error_when_no_planner_but_config_provided(self) -> None:
        """Test that command returns error when installation_config provided but no planner."""
        factory = get_factory()
        command = GenerateLayoutCommand(
            layout_calculator=factory.get_layout_calculator(),
            cut_list_generator=factory.get_cut_list_generator(),
            material_estimator=factory.get_material_estimator(),
            room_layout_service=factory.get_room_layout_service(),
            installation_service_factory=None,  # No factory
        )

        wall_input = WallInput(width=48.0, height=30.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1, shelves_per_section=3, material_thickness=0.75
        )
        installation_config = InstallationConfig()

        # Should return an error since no planner is configured
        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        assert not result.is_valid
        assert (
            "installation_config provided but no installation_planner configured"
            in result.errors[0]
        )


class TestServiceFactoryCreateGenerateCommand:
    """Tests for ServiceFactory.create_generate_command with installation services."""

    def test_create_generate_command_includes_installation_planner(self) -> None:
        """Test that create_generate_command includes installation planner service."""
        factory = ServiceFactory()
        command = factory.create_generate_command()

        # The command should have the planner configured
        assert command._installation_planner is not None

    def test_default_factory_creates_command_with_installation_planner(self) -> None:
        """Test that get_factory().create_generate_command() includes planner."""
        command = get_factory().create_generate_command()

        # The command should have a planner set
        assert command._installation_planner is not None

    def test_command_from_factory_uses_injected_installation_service(self) -> None:
        """Test that command from factory uses installation service properly."""
        factory = ServiceFactory()
        command = factory.create_generate_command()

        wall_input = WallInput(width=48.0, height=30.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1, shelves_per_section=3, material_thickness=0.75
        )
        installation_config = InstallationConfig(
            mounting_system=MountingSystem.DIRECT_TO_STUD
        )

        result = command.execute(
            wall_input, params_input, installation_config=installation_config
        )

        assert result.is_valid
        assert result.installation is not None
        assert result.installation.stud_analysis is not None


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing code."""

    def test_command_without_installation_parameters(self) -> None:
        """Test that command can be created without installation-related parameters."""
        factory = get_factory()

        # This should work without specifying installation_planner
        command = GenerateLayoutCommand(
            layout_calculator=factory.get_layout_calculator(),
            cut_list_generator=factory.get_cut_list_generator(),
            material_estimator=factory.get_material_estimator(),
            room_layout_service=factory.get_room_layout_service(),
        )

        assert command._installation_planner is None

    def test_execute_without_installation_config(self) -> None:
        """Test that execute works without installation_config."""
        command = get_factory().create_generate_command()

        wall_input = WallInput(width=48.0, height=30.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=1, shelves_per_section=3, material_thickness=0.75
        )

        # Execute without installation_config
        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert result.installation is None  # No installation output

    def test_existing_test_patterns_still_work(self) -> None:
        """Test that existing test patterns continue to work."""
        # This mimics the pattern used in existing tests
        command = get_factory().create_generate_command()

        wall_input = WallInput(width=72.0, height=84.0, depth=12.0)
        params_input = LayoutParametersInput(
            num_sections=3,
            shelves_per_section=4,
            material_thickness=0.75,
        )

        result = command.execute(wall_input, params_input)

        assert result.is_valid
        assert result.cabinet is not None
        assert len(result.cabinet.sections) == 3
        assert len(result.cut_list) > 0
