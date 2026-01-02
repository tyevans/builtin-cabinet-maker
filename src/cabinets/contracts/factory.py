"""Factory protocols for Interface Segregation Principle compliance.

This module defines focused factory protocols that segregate the ServiceFactory
interface into domain-specific concerns. Clients should depend on the minimum
required protocol rather than the full ServiceFactory interface.

Protocols:
    DomainServiceFactory: Creates domain services (layout calculator, cut list, etc.)
    FormatterFactory: Creates output formatters (cut list, diagram, material report)
    ExporterFactory: Creates file exporters (STL, JSON, assembly instructions)
    CommandFactory: Creates application commands

These protocols enable ISP compliance:
    - CLI commands needing only formatters depend on FormatterFactory
    - Export operations depend on ExporterFactory
    - Layout generation depends on DomainServiceFactory
    - Full orchestration can use the complete ServiceFactory

Example:
    ```python
    from cabinets.contracts import FormatterFactory

    def format_output(factory: FormatterFactory) -> str:
        formatter = factory.get_cut_list_formatter()
        return formatter.format(cut_list)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cabinets.application.commands import GenerateLayoutCommand
    from cabinets.contracts.exporters import JsonExporterProtocol, StlExporterProtocol
    from cabinets.contracts.formatters import (
        CutListFormatterProtocol,
        LayoutDiagramFormatterProtocol,
        MaterialReportFormatterProtocol,
    )
    from cabinets.contracts.protocols import (
        CutListGeneratorProtocol,
        InstallationServiceProtocol,
        LayoutCalculatorProtocol,
        MaterialEstimatorProtocol,
        RoomLayoutServiceProtocol,
    )
    from cabinets.domain.services.installation.config import InstallationConfig
    from cabinets.domain.services.zone_layout import ZoneLayoutService
    from cabinets.infrastructure.exporters import AssemblyInstructionGenerator
    from cabinets.infrastructure.formatters import (
        HardwareReportFormatter,
        InstallationFormatter,
    )
    from cabinets.infrastructure.llm import LLMAssemblyGenerator


@runtime_checkable
class DomainServiceFactory(Protocol):
    """Protocol for factories that create domain services.

    Domain services handle core business logic:
    - Layout calculation for cabinets and sections
    - Cut list generation from cabinet layouts
    - Material estimation from cut lists
    - Room layout for multi-wall configurations
    - Zone layout for vertical zone stacks

    Implementations must provide lazy-instantiated, cached services.

    Example:
        ```python
        def generate_layout(factory: DomainServiceFactory, wall: Wall) -> Cabinet:
            calculator = factory.get_layout_calculator()
            return calculator.generate_cabinet(wall, params)
        ```
    """

    def get_layout_calculator(self) -> "LayoutCalculatorProtocol":
        """Get or create layout calculator instance.

        Returns:
            LayoutCalculatorProtocol implementation for cabinet layout calculation.
        """
        ...

    def get_cut_list_generator(self) -> "CutListGeneratorProtocol":
        """Get or create cut list generator instance.

        Returns:
            CutListGeneratorProtocol implementation for cut list generation.
        """
        ...

    def get_material_estimator(self) -> "MaterialEstimatorProtocol":
        """Get or create material estimator instance.

        Returns:
            MaterialEstimatorProtocol implementation for material estimation.
        """
        ...

    def get_room_layout_service(self) -> "RoomLayoutServiceProtocol":
        """Get or create room layout service instance.

        Returns:
            RoomLayoutServiceProtocol implementation for multi-wall room layouts.
        """
        ...

    def get_zone_layout_service(self) -> "ZoneLayoutService":
        """Get or create zone layout service instance.

        Returns:
            ZoneLayoutService for vertical zone stack generation.
        """
        ...


@runtime_checkable
class FormatterFactory(Protocol):
    """Protocol for factories that create output formatters.

    Formatters convert domain objects to human-readable output:
    - Cut list tables with dimensions and quantities
    - ASCII layout diagrams
    - Material requirement reports
    - Hardware lists
    - Installation instructions

    Formatters are typically stateless and can be created fresh each time.

    Example:
        ```python
        def print_cut_list(factory: FormatterFactory, cut_list: list[CutPiece]) -> None:
            formatter = factory.get_cut_list_formatter()
            print(formatter.format(cut_list))
        ```
    """

    def get_cut_list_formatter(self) -> "CutListFormatterProtocol":
        """Create cut list formatter instance.

        Returns:
            CutListFormatterProtocol for formatting cut lists as tables.
        """
        ...

    def get_layout_diagram_formatter(self) -> "LayoutDiagramFormatterProtocol":
        """Create layout diagram formatter instance.

        Returns:
            LayoutDiagramFormatterProtocol for ASCII cabinet diagrams.
        """
        ...

    def get_material_report_formatter(self) -> "MaterialReportFormatterProtocol":
        """Create material report formatter instance.

        Returns:
            MaterialReportFormatterProtocol for material estimate reports.
        """
        ...

    def get_hardware_report_formatter(self) -> "HardwareReportFormatter":
        """Create hardware report formatter instance.

        Returns:
            HardwareReportFormatter for hardware list formatting.
        """
        ...

    def get_installation_formatter(self) -> "InstallationFormatter":
        """Create installation formatter instance.

        Returns:
            InstallationFormatter for installation instructions.
        """
        ...


@runtime_checkable
class ExporterFactory(Protocol):
    """Protocol for factories that create file exporters.

    Exporters convert layout output to file formats:
    - STL for 3D visualization and printing
    - JSON for data exchange and storage
    - Assembly instructions in markdown
    - LLM-generated assembly instructions

    Exporters may have configuration options and are created fresh each time.

    Example:
        ```python
        def export_to_stl(factory: ExporterFactory, output: LayoutOutput, path: Path) -> None:
            exporter = factory.get_stl_exporter()
            exporter.export(output, path)
        ```
    """

    def get_stl_exporter(self) -> "StlExporterProtocol":
        """Create STL exporter instance.

        Returns:
            StlExporterProtocol for STL file export.
        """
        ...

    def get_json_exporter(self) -> "JsonExporterProtocol":
        """Create JSON exporter instance.

        Returns:
            JsonExporterProtocol for JSON file export.
        """
        ...

    def get_assembly_instruction_generator(self) -> "AssemblyInstructionGenerator":
        """Create assembly instruction generator instance.

        Returns:
            AssemblyInstructionGenerator for markdown assembly instructions.
        """
        ...

    def get_llm_assembly_generator(self) -> "LLMAssemblyGenerator":
        """Create LLM assembly generator instance.

        Returns:
            LLMAssemblyGenerator for LLM-enhanced assembly instructions.
        """
        ...


@runtime_checkable
class InstallationServiceFactory(Protocol):
    """Protocol for factories that create installation services.

    Installation services generate installation plans including mounting
    hardware, French cleat specifications, stud alignment analysis, and
    step-by-step installation instructions.

    This protocol enables dependency injection for installation service
    creation, allowing the GenerateLayoutCommand to receive installation
    services without directly instantiating them.

    Example:
        ```python
        def create_installation_plan(
            factory: InstallationServiceFactory,
            config: InstallationConfig,
            cabinet: Cabinet,
        ) -> InstallationPlan:
            service = factory.create_installation_service(config)
            return service.generate_plan(cabinet)
        ```
    """

    def create_installation_service(
        self, config: "InstallationConfig"
    ) -> "InstallationServiceProtocol":
        """Create an installation service with the given configuration.

        Args:
            config: Installation configuration parameters.

        Returns:
            InstallationServiceProtocol implementation for installation planning.
        """
        ...


@runtime_checkable
class CommandFactory(Protocol):
    """Protocol for factories that create application commands.

    Commands are use cases that orchestrate domain services to perform
    complex operations. They encapsulate the workflow logic.

    Example:
        ```python
        def run_generation(factory: CommandFactory, config: dict) -> LayoutOutput:
            command = factory.create_generate_command()
            return command.execute(config)
        ```
    """

    def create_generate_command(self) -> "GenerateLayoutCommand":
        """Create GenerateLayoutCommand with all dependencies.

        Returns:
            GenerateLayoutCommand configured with required services.
        """
        ...


__all__ = [
    "CommandFactory",
    "DomainServiceFactory",
    "ExporterFactory",
    "FormatterFactory",
    "InstallationServiceFactory",
]
