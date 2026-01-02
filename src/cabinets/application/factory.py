"""Service factory for dependency injection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from cabinets.contracts.protocols import (
        CutListGeneratorProtocol,
        InputValidatorProtocol,
        InstallationPlannerProtocol,
        InstallationServiceProtocol,
        LayoutCalculatorProtocol,
        MaterialEstimatorProtocol,
        OutputAssemblerProtocol,
        RoomLayoutOrchestratorProtocol,
        RoomLayoutServiceProtocol,
        SectionWidthResolverProtocol,
    )
    from cabinets.contracts.formatters import (
        CutListFormatterProtocol,
        LayoutDiagramFormatterProtocol,
        MaterialReportFormatterProtocol,
    )
    from cabinets.contracts.exporters import (
        StlExporterProtocol,
        JsonExporterProtocol,
    )
    from cabinets.application.commands import GenerateLayoutCommand
    from cabinets.domain.services.installation.config import InstallationConfig
    from cabinets.domain.services.zone_layout import ZoneLayoutService
    from cabinets.infrastructure.formatters import (
        HardwareReportFormatter,
        InstallationFormatter,
    )
    from cabinets.infrastructure.exporters import AssemblyInstructionGenerator
    from cabinets.infrastructure.llm import LLMAssemblyGenerator


@dataclass
class ServiceFactory:
    """Factory for creating service instances.

    Centralizes service instantiation to support:
    - Dependency injection for testing
    - Configuration-based service selection
    - Lazy initialization of expensive services

    This factory implements the following focused protocols for ISP compliance:
    - DomainServiceFactory: Domain services (layout calculator, cut list, etc.)
    - FormatterFactory: Output formatters (cut list, diagram, material report)
    - ExporterFactory: File exporters (STL, JSON, assembly instructions)
    - CommandFactory: Application commands (GenerateLayoutCommand)
    - InstallationServiceFactory: Installation services (InstallationService)

    Clients should depend on the minimum required protocol rather than the
    full ServiceFactory interface. For example, code that only needs to
    format output should depend on FormatterFactory, not ServiceFactory.

    Example:
        ```python
        from cabinets.contracts import FormatterFactory

        def format_cut_list(factory: FormatterFactory, cut_list: list) -> str:
            formatter = factory.get_cut_list_formatter()
            return formatter.format(cut_list)

        # Works with ServiceFactory since it implements FormatterFactory
        factory = ServiceFactory()
        result = format_cut_list(factory, my_cut_list)
        ```
    """

    # Cached instances (use field with init=False for dataclass)
    _layout_calculator: "LayoutCalculatorProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _cut_list_generator: "CutListGeneratorProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _material_estimator: "MaterialEstimatorProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _room_layout_service: "RoomLayoutServiceProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _zone_layout_service: "ZoneLayoutService | None" = field(
        default=None, init=False, repr=False
    )

    # New services for decomposed command
    _input_validator: "InputValidatorProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _output_assembler: "OutputAssemblerProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _installation_planner: "InstallationPlannerProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _section_width_resolver: "SectionWidthResolverProtocol | None" = field(
        default=None, init=False, repr=False
    )
    _room_orchestrator: "RoomLayoutOrchestratorProtocol | None" = field(
        default=None, init=False, repr=False
    )

    def get_layout_calculator(self) -> "LayoutCalculatorProtocol":
        """Get or create layout calculator instance."""
        if self._layout_calculator is None:
            from cabinets.domain.services import LayoutCalculator

            self._layout_calculator = cast(
                "LayoutCalculatorProtocol", LayoutCalculator()
            )
        assert self._layout_calculator is not None
        return self._layout_calculator

    def get_cut_list_generator(self) -> "CutListGeneratorProtocol":
        """Get or create cut list generator instance."""
        if self._cut_list_generator is None:
            from cabinets.domain.services import CutListGenerator

            self._cut_list_generator = CutListGenerator()
        return self._cut_list_generator

    def get_material_estimator(self) -> "MaterialEstimatorProtocol":
        """Get or create material estimator instance."""
        if self._material_estimator is None:
            from cabinets.domain.services import MaterialEstimator

            self._material_estimator = MaterialEstimator()
        return self._material_estimator

    def get_room_layout_service(self) -> "RoomLayoutServiceProtocol":
        """Get or create room layout service instance."""
        if self._room_layout_service is None:
            from cabinets.domain.services import RoomLayoutService

            self._room_layout_service = cast(
                "RoomLayoutServiceProtocol", RoomLayoutService()
            )
        assert self._room_layout_service is not None
        return self._room_layout_service

    def get_zone_layout_service(self) -> "ZoneLayoutService":
        """Get or create zone layout service instance."""
        if self._zone_layout_service is None:
            from cabinets.domain.services import ZoneLayoutService

            self._zone_layout_service = ZoneLayoutService()
        return self._zone_layout_service

    def get_cut_list_formatter(self) -> "CutListFormatterProtocol":
        """Create cut list formatter instance."""
        from cabinets.infrastructure.formatters import CutListFormatter

        return CutListFormatter()

    def get_layout_diagram_formatter(self) -> "LayoutDiagramFormatterProtocol":
        """Create layout diagram formatter instance."""
        from cabinets.infrastructure.formatters import LayoutDiagramFormatter

        return LayoutDiagramFormatter()

    def get_material_report_formatter(self) -> "MaterialReportFormatterProtocol":
        """Create material report formatter instance."""
        from cabinets.infrastructure.formatters import MaterialReportFormatter

        return MaterialReportFormatter()

    def get_hardware_report_formatter(self) -> "HardwareReportFormatter":
        """Create hardware report formatter instance."""
        from cabinets.infrastructure.formatters import HardwareReportFormatter

        return HardwareReportFormatter()

    def get_installation_formatter(self) -> "InstallationFormatter":
        """Create installation formatter instance."""
        from cabinets.infrastructure.formatters import InstallationFormatter

        return InstallationFormatter()

    def get_stl_exporter(self) -> "StlExporterProtocol":
        """Create STL exporter instance."""
        from cabinets.infrastructure import StlExporter

        return StlExporter()

    def get_json_exporter(self) -> "JsonExporterProtocol":
        """Create JSON exporter instance."""
        from cabinets.infrastructure.exporters import JsonExporter

        return JsonExporter()

    def get_assembly_instruction_generator(self) -> "AssemblyInstructionGenerator":
        """Create assembly instruction generator instance."""
        from cabinets.infrastructure.exporters import AssemblyInstructionGenerator

        return AssemblyInstructionGenerator()

    def get_llm_assembly_generator(self) -> "LLMAssemblyGenerator":
        """Create LLM assembly generator instance."""
        from cabinets.infrastructure.llm import LLMAssemblyGenerator

        return LLMAssemblyGenerator()

    def create_installation_service(
        self, config: "InstallationConfig"
    ) -> "InstallationServiceProtocol":
        """Create an installation service with the given configuration.

        Args:
            config: Installation configuration parameters.

        Returns:
            InstallationServiceProtocol implementation for installation planning.
        """
        from cabinets.domain.services.installation import InstallationService

        return InstallationService(config)

    # New services for decomposed command

    def get_input_validator(self) -> "InputValidatorProtocol":
        """Get or create input validator instance."""
        if self._input_validator is None:
            from cabinets.application.services import InputValidatorService

            self._input_validator = InputValidatorService()
        return self._input_validator

    def get_output_assembler(self) -> "OutputAssemblerProtocol":
        """Get or create output assembler instance."""
        if self._output_assembler is None:
            from cabinets.application.services import OutputAssemblerService

            self._output_assembler = OutputAssemblerService()
        return self._output_assembler

    def get_installation_planner(self) -> "InstallationPlannerProtocol":
        """Get or create installation planner instance."""
        if self._installation_planner is None:
            from cabinets.application.services import InstallationPlannerService

            self._installation_planner = InstallationPlannerService(self)
        return self._installation_planner

    def get_section_width_resolver(self) -> "SectionWidthResolverProtocol":
        """Get or create section width resolver instance."""
        if self._section_width_resolver is None:
            from cabinets.application.services import SectionWidthResolverService

            self._section_width_resolver = SectionWidthResolverService()
        return self._section_width_resolver

    def get_room_orchestrator(self) -> "RoomLayoutOrchestratorProtocol":
        """Get or create room layout orchestrator instance."""
        if self._room_orchestrator is None:
            from cabinets.application.services import RoomLayoutOrchestratorService

            self._room_orchestrator = RoomLayoutOrchestratorService(
                input_validator=self.get_input_validator(),
                room_layout_service=self.get_room_layout_service(),
                layout_calculator=self.get_layout_calculator(),
                cut_list_generator=self.get_cut_list_generator(),
                section_width_resolver=self.get_section_width_resolver(),
                output_assembler=self.get_output_assembler(),
                material_estimator=self.get_material_estimator(),
            )
        return self._room_orchestrator

    def create_generate_command(self) -> "GenerateLayoutCommand":
        """Create GenerateLayoutCommand with all dependencies.

        The command receives both legacy dependencies (for backward compatibility)
        and new decomposed services for improved SRP adherence.
        """
        from cabinets.application.commands import GenerateLayoutCommand

        return GenerateLayoutCommand(
            layout_calculator=self.get_layout_calculator(),
            cut_list_generator=self.get_cut_list_generator(),
            material_estimator=self.get_material_estimator(),
            room_layout_service=self.get_room_layout_service(),
            input_validator=self.get_input_validator(),
            output_assembler=self.get_output_assembler(),
            installation_planner=self.get_installation_planner(),
            room_orchestrator=self.get_room_orchestrator(),
        )


# Default factory instance
_default_factory: ServiceFactory | None = None


def get_factory() -> ServiceFactory:
    """Get the default service factory."""
    global _default_factory
    if _default_factory is None:
        _default_factory = ServiceFactory()
    return _default_factory


def set_factory(factory: ServiceFactory | None) -> None:
    """Set a custom factory (for testing)."""
    global _default_factory
    _default_factory = factory


def reset_factory() -> None:
    """Reset the factory to default (for testing cleanup)."""
    global _default_factory
    _default_factory = None
