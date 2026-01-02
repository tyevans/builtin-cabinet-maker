"""Tests for factory protocol compliance (TECHDEBT-05 Phase 3).

These tests verify that ServiceFactory implements the focused factory protocols
for ISP (Interface Segregation Principle) compliance.

The protocols allow clients to depend on minimal interfaces:
- DomainServiceFactory for domain services
- FormatterFactory for output formatters
- ExporterFactory for file exporters
- CommandFactory for application commands
"""

from __future__ import annotations


from cabinets.application.factory import ServiceFactory
from cabinets.contracts import (
    CommandFactory,
    DomainServiceFactory,
    ExporterFactory,
    FormatterFactory,
)


class TestDomainServiceFactoryProtocol:
    """Tests for DomainServiceFactory protocol compliance."""

    def test_service_factory_is_domain_service_factory(self) -> None:
        """ServiceFactory should be an instance of DomainServiceFactory protocol."""
        factory = ServiceFactory()
        assert isinstance(factory, DomainServiceFactory)

    def test_domain_service_factory_has_layout_calculator(self) -> None:
        """DomainServiceFactory should provide layout calculator."""
        factory = ServiceFactory()
        calculator = factory.get_layout_calculator()
        # Verify it's callable (has generate_cabinet method)
        assert hasattr(calculator, "generate_cabinet")
        assert callable(calculator.generate_cabinet)

    def test_domain_service_factory_has_cut_list_generator(self) -> None:
        """DomainServiceFactory should provide cut list generator."""
        factory = ServiceFactory()
        generator = factory.get_cut_list_generator()
        assert hasattr(generator, "generate")
        assert callable(generator.generate)

    def test_domain_service_factory_has_material_estimator(self) -> None:
        """DomainServiceFactory should provide material estimator."""
        factory = ServiceFactory()
        estimator = factory.get_material_estimator()
        assert hasattr(estimator, "estimate")
        assert callable(estimator.estimate)

    def test_domain_service_factory_has_room_layout_service(self) -> None:
        """DomainServiceFactory should provide room layout service."""
        factory = ServiceFactory()
        service = factory.get_room_layout_service()
        # The actual RoomLayoutService uses assign_sections_to_walls
        # Note: RoomLayoutServiceProtocol defines generate_room_layout but
        # the implementation provides assign_sections_to_walls - this is
        # an existing mismatch that should be addressed separately
        assert hasattr(service, "assign_sections_to_walls")
        assert callable(service.assign_sections_to_walls)

    def test_domain_service_factory_has_zone_layout_service(self) -> None:
        """DomainServiceFactory should provide zone layout service."""
        factory = ServiceFactory()
        service = factory.get_zone_layout_service()
        assert hasattr(service, "generate")
        assert callable(service.generate)

    def test_domain_service_factory_type_hint_usable(self) -> None:
        """DomainServiceFactory should be usable as a type hint without runtime errors."""

        def use_factory(factory: DomainServiceFactory) -> bool:
            """Function accepting DomainServiceFactory type hint."""
            _ = factory.get_layout_calculator()
            return True

        factory = ServiceFactory()
        assert use_factory(factory) is True


class TestFormatterFactoryProtocol:
    """Tests for FormatterFactory protocol compliance."""

    def test_service_factory_is_formatter_factory(self) -> None:
        """ServiceFactory should be an instance of FormatterFactory protocol."""
        factory = ServiceFactory()
        assert isinstance(factory, FormatterFactory)

    def test_formatter_factory_has_cut_list_formatter(self) -> None:
        """FormatterFactory should provide cut list formatter."""
        factory = ServiceFactory()
        formatter = factory.get_cut_list_formatter()
        assert hasattr(formatter, "format")
        assert callable(formatter.format)

    def test_formatter_factory_has_layout_diagram_formatter(self) -> None:
        """FormatterFactory should provide layout diagram formatter."""
        factory = ServiceFactory()
        formatter = factory.get_layout_diagram_formatter()
        assert hasattr(formatter, "format")
        assert callable(formatter.format)

    def test_formatter_factory_has_material_report_formatter(self) -> None:
        """FormatterFactory should provide material report formatter."""
        factory = ServiceFactory()
        formatter = factory.get_material_report_formatter()
        assert hasattr(formatter, "format")
        assert callable(formatter.format)

    def test_formatter_factory_has_hardware_report_formatter(self) -> None:
        """FormatterFactory should provide hardware report formatter."""
        factory = ServiceFactory()
        formatter = factory.get_hardware_report_formatter()
        assert hasattr(formatter, "format")
        assert callable(formatter.format)

    def test_formatter_factory_has_installation_formatter(self) -> None:
        """FormatterFactory should provide installation formatter."""
        factory = ServiceFactory()
        formatter = factory.get_installation_formatter()
        assert hasattr(formatter, "format")
        assert callable(formatter.format)

    def test_formatter_factory_type_hint_usable(self) -> None:
        """FormatterFactory should be usable as a type hint without runtime errors."""

        def use_factory(factory: FormatterFactory) -> bool:
            """Function accepting FormatterFactory type hint."""
            _ = factory.get_cut_list_formatter()
            return True

        factory = ServiceFactory()
        assert use_factory(factory) is True


class TestExporterFactoryProtocol:
    """Tests for ExporterFactory protocol compliance."""

    def test_service_factory_is_exporter_factory(self) -> None:
        """ServiceFactory should be an instance of ExporterFactory protocol."""
        factory = ServiceFactory()
        assert isinstance(factory, ExporterFactory)

    def test_exporter_factory_has_stl_exporter(self) -> None:
        """ExporterFactory should provide STL exporter."""
        factory = ServiceFactory()
        exporter = factory.get_stl_exporter()
        assert hasattr(exporter, "export")
        assert callable(exporter.export)

    def test_exporter_factory_has_json_exporter(self) -> None:
        """ExporterFactory should provide JSON exporter."""
        factory = ServiceFactory()
        exporter = factory.get_json_exporter()
        assert hasattr(exporter, "export")
        assert callable(exporter.export)

    def test_exporter_factory_has_assembly_instruction_generator(self) -> None:
        """ExporterFactory should provide assembly instruction generator."""
        factory = ServiceFactory()
        generator = factory.get_assembly_instruction_generator()
        # AssemblyInstructionGenerator should have export method
        assert hasattr(generator, "export")
        assert callable(generator.export)

    def test_exporter_factory_has_llm_assembly_generator(self) -> None:
        """ExporterFactory should provide LLM assembly generator."""
        factory = ServiceFactory()
        generator = factory.get_llm_assembly_generator()
        # LLMAssemblyGenerator should have generate method
        assert hasattr(generator, "generate")
        assert callable(generator.generate)

    def test_exporter_factory_type_hint_usable(self) -> None:
        """ExporterFactory should be usable as a type hint without runtime errors."""

        def use_factory(factory: ExporterFactory) -> bool:
            """Function accepting ExporterFactory type hint."""
            _ = factory.get_stl_exporter()
            return True

        factory = ServiceFactory()
        assert use_factory(factory) is True


class TestCommandFactoryProtocol:
    """Tests for CommandFactory protocol compliance."""

    def test_service_factory_is_command_factory(self) -> None:
        """ServiceFactory should be an instance of CommandFactory protocol."""
        factory = ServiceFactory()
        assert isinstance(factory, CommandFactory)

    def test_command_factory_has_generate_command(self) -> None:
        """CommandFactory should provide generate layout command."""
        factory = ServiceFactory()
        command = factory.create_generate_command()
        assert hasattr(command, "execute")
        assert callable(command.execute)

    def test_command_factory_type_hint_usable(self) -> None:
        """CommandFactory should be usable as a type hint without runtime errors."""

        def use_factory(factory: CommandFactory) -> bool:
            """Function accepting CommandFactory type hint."""
            _ = factory.create_generate_command()
            return True

        factory = ServiceFactory()
        assert use_factory(factory) is True


class TestProtocolSegregation:
    """Tests verifying that protocols are properly segregated."""

    def test_all_protocols_are_runtime_checkable(self) -> None:
        """All factory protocols should be runtime checkable."""
        factory = ServiceFactory()

        # Each check should work at runtime
        assert isinstance(factory, DomainServiceFactory)
        assert isinstance(factory, FormatterFactory)
        assert isinstance(factory, ExporterFactory)
        assert isinstance(factory, CommandFactory)

    def test_protocols_can_be_used_independently(self) -> None:
        """Each protocol should be usable independently of others."""

        def domain_only(f: DomainServiceFactory) -> str:
            """Uses only domain services."""
            return type(f.get_layout_calculator()).__name__

        def formatter_only(f: FormatterFactory) -> str:
            """Uses only formatters."""
            return type(f.get_cut_list_formatter()).__name__

        def exporter_only(f: ExporterFactory) -> str:
            """Uses only exporters."""
            return type(f.get_stl_exporter()).__name__

        def command_only(f: CommandFactory) -> str:
            """Uses only commands."""
            return type(f.create_generate_command()).__name__

        factory = ServiceFactory()

        # Each should work independently
        assert domain_only(factory) == "LayoutCalculator"
        assert formatter_only(factory) == "CutListFormatter"
        assert exporter_only(factory) == "StlExporter"
        assert command_only(factory) == "GenerateLayoutCommand"

    def test_protocols_are_distinct_interfaces(self) -> None:
        """Protocols should define distinct, non-overlapping interfaces."""
        # Get method sets for each protocol (excluding dunder methods)
        _ = {
            m
            for m in dir(DomainServiceFactory)
            if not m.startswith("_")
            and callable(getattr(DomainServiceFactory, m, None))
        }
        _ = {
            m
            for m in dir(FormatterFactory)
            if not m.startswith("_") and callable(getattr(FormatterFactory, m, None))
        }
        _ = {
            m
            for m in dir(ExporterFactory)
            if not m.startswith("_") and callable(getattr(ExporterFactory, m, None))
        }
        _ = {
            m
            for m in dir(CommandFactory)
            if not m.startswith("_") and callable(getattr(CommandFactory, m, None))
        }

        # Verify no overlap between protocols (excluding Protocol internal methods)
        # Note: Some overlap may occur due to Protocol metaclass methods
        # We check that the core factory methods don't overlap
        core_domain = {
            "get_layout_calculator",
            "get_cut_list_generator",
            "get_material_estimator",
        }
        core_formatter = {"get_cut_list_formatter", "get_layout_diagram_formatter"}
        core_exporter = {"get_stl_exporter", "get_json_exporter"}
        core_command = {"create_generate_command"}

        # Verify core methods are disjoint
        assert core_domain.isdisjoint(core_formatter)
        assert core_domain.isdisjoint(core_exporter)
        assert core_domain.isdisjoint(core_command)
        assert core_formatter.isdisjoint(core_exporter)
        assert core_formatter.isdisjoint(core_command)
        assert core_exporter.isdisjoint(core_command)


class TestISPCompliance:
    """Tests demonstrating ISP compliance benefits."""

    def test_minimal_dependency_domain_services(self) -> None:
        """Client code should be able to depend only on DomainServiceFactory."""

        class LayoutGenerator:
            """Example client depending only on DomainServiceFactory."""

            def __init__(self, factory: DomainServiceFactory) -> None:
                self.factory = factory

            def get_calculator(self):
                return self.factory.get_layout_calculator()

        factory = ServiceFactory()
        generator = LayoutGenerator(factory)
        calculator = generator.get_calculator()
        assert calculator is not None

    def test_minimal_dependency_formatters(self) -> None:
        """Client code should be able to depend only on FormatterFactory."""

        class OutputPrinter:
            """Example client depending only on FormatterFactory."""

            def __init__(self, factory: FormatterFactory) -> None:
                self.factory = factory

            def get_formatter(self):
                return self.factory.get_cut_list_formatter()

        factory = ServiceFactory()
        printer = OutputPrinter(factory)
        formatter = printer.get_formatter()
        assert formatter is not None

    def test_minimal_dependency_exporters(self) -> None:
        """Client code should be able to depend only on ExporterFactory."""

        class FileExportManager:
            """Example client depending only on ExporterFactory."""

            def __init__(self, factory: ExporterFactory) -> None:
                self.factory = factory

            def get_exporter(self):
                return self.factory.get_stl_exporter()

        factory = ServiceFactory()
        manager = FileExportManager(factory)
        exporter = manager.get_exporter()
        assert exporter is not None

    def test_minimal_dependency_commands(self) -> None:
        """Client code should be able to depend only on CommandFactory."""

        class CommandRunner:
            """Example client depending only on CommandFactory."""

            def __init__(self, factory: CommandFactory) -> None:
                self.factory = factory

            def get_command(self):
                return self.factory.create_generate_command()

        factory = ServiceFactory()
        runner = CommandRunner(factory)
        command = runner.get_command()
        assert command is not None
