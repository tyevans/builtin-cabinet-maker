"""Contracts module - protocols and shared DTOs for cross-layer communication.

This module provides:
- Protocol definitions for dependency injection and interface contracts
- Shared DTOs that can be used by both application and infrastructure layers

By depending on protocols rather than concrete implementations, layers remain
loosely coupled and testable.

Example:
    ```python
    from cabinets.contracts import (
        LayoutOutput,
        RoomLayoutOutput,
        LayoutCalculatorProtocol,
        CutListFormatterProtocol,
    )

    # Type hint a parameter with a protocol
    def process_layout(calculator: LayoutCalculatorProtocol) -> LayoutOutput:
        ...
    ```
"""

# DTOs
from .dtos import (
    CoreLayoutOutput as CoreLayoutOutput,
    InstallationOutput as InstallationOutput,
    LayoutOutput as LayoutOutput,
    PackingOutput as PackingOutput,
    RoomLayoutOutput as RoomLayoutOutput,
    WoodworkingOutput as WoodworkingOutput,
)

# Exporter protocols
from .exporters import (
    ExporterProtocol as ExporterProtocol,
    JsonExporterProtocol as JsonExporterProtocol,
    StlExporterProtocol as StlExporterProtocol,
)

# Formatter protocols
from .formatters import (
    CutListFormatterProtocol as CutListFormatterProtocol,
    FormatterProtocol as FormatterProtocol,
    LayoutDiagramFormatterProtocol as LayoutDiagramFormatterProtocol,
    MaterialReportFormatterProtocol as MaterialReportFormatterProtocol,
)

# Service protocols
from .protocols import (
    CutListGeneratorProtocol as CutListGeneratorProtocol,
    InputValidatorProtocol as InputValidatorProtocol,
    InstallationPlannerProtocol as InstallationPlannerProtocol,
    InstallationPlanResult as InstallationPlanResult,
    InstallationServiceProtocol as InstallationServiceProtocol,
    LayoutCalculatorProtocol as LayoutCalculatorProtocol,
    MaterialEstimatorProtocol as MaterialEstimatorProtocol,
    OutputAssemblerProtocol as OutputAssemblerProtocol,
    RoomLayoutOrchestratorProtocol as RoomLayoutOrchestratorProtocol,
    RoomLayoutServiceProtocol as RoomLayoutServiceProtocol,
    SectionWidthResolverProtocol as SectionWidthResolverProtocol,
)

# Strategy protocols
from .strategies import (
    LayoutStrategy as LayoutStrategy,
)

# Validator protocol
from .validators import Validator as Validator

# Factory protocols
from .factory import (
    CommandFactory as CommandFactory,
    DomainServiceFactory as DomainServiceFactory,
    ExporterFactory as ExporterFactory,
    FormatterFactory as FormatterFactory,
    InstallationServiceFactory as InstallationServiceFactory,
)

# All imported names are automatically available for direct import.
