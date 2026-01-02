"""Shared Data Transfer Objects for cross-layer communication.

This module contains DTOs that are shared between the application and
infrastructure layers, enabling loose coupling without circular dependencies.

These DTOs were originally defined in application/dtos.py and are now
provided here as the canonical source. The application layer re-exports
these for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cabinets.domain import (
    Cabinet,
    CutPiece,
    MaterialEstimate,
    MaterialSpec,
)
from cabinets.domain.components.results import HardwareItem
from cabinets.domain.entities import Room
from cabinets.domain.value_objects import SectionTransform

if TYPE_CHECKING:
    from cabinets.infrastructure.bin_packing import PackingResult


@dataclass
class CoreLayoutOutput:
    """Core layout generation results.

    Contains the essential output from layout generation that is always
    present regardless of optional features.

    Attributes:
        cabinet: Generated cabinet entity with sections, panels, and shelves.
        cut_list: List of cut pieces required to build the cabinet.
        material_estimates: Material estimates grouped by material type.
        total_estimate: Total material estimate across all materials.
        errors: List of error messages if generation failed.
    """

    cabinet: Cabinet
    cut_list: list[CutPiece]
    material_estimates: dict[MaterialSpec, MaterialEstimate]
    total_estimate: MaterialEstimate
    errors: list[str] = field(default_factory=list)


@dataclass
class WoodworkingOutput:
    """Woodworking-specific output.

    Contains hardware and other woodworking-related items generated
    during layout creation.

    Attributes:
        hardware: List of hardware items required for assembly.
    """

    hardware: list[HardwareItem] = field(default_factory=list)


@dataclass
class PackingOutput:
    """Bin packing optimization results.

    Contains the result of bin packing optimization when enabled.

    Attributes:
        packing_result: Result from bin packing optimization, if computed.
    """

    packing_result: "PackingResult | None" = None


@dataclass
class InstallationOutput:
    """Installation planning results.

    Contains installation-related hardware, instructions, and analysis
    when installation planning is enabled.

    Attributes:
        hardware: List of installation hardware items (e.g., screws, anchors).
        instructions: Installation instructions in markdown format.
        warnings: List of installation-related warnings.
        stud_analysis: Stud alignment analysis results as a dictionary.
    """

    hardware: list[HardwareItem] = field(default_factory=list)
    instructions: str | None = None
    warnings: list[str] = field(default_factory=list)
    stud_analysis: dict[str, Any] | None = None


class LayoutOutput:
    """Composite output DTO containing the generated layout results.

    Uses composition to organize output into logical groups while maintaining
    backward compatibility with the original flat structure through properties.

    This class supports two calling conventions:
    1. New composite style: LayoutOutput(core=CoreLayoutOutput(...), ...)
    2. Legacy flat style: LayoutOutput(cabinet=..., cut_list=..., ...)

    Attributes:
        core: Core layout generation results (cabinet, cut_list, estimates).
        woodworking: Woodworking-specific output (hardware).
        packing: Bin packing optimization results.
        installation: Installation planning results.
    """

    core: CoreLayoutOutput
    woodworking: WoodworkingOutput | None
    packing: PackingOutput | None
    installation: InstallationOutput | None

    def __init__(
        self,
        # New composite-style arguments
        core: CoreLayoutOutput | None = None,
        woodworking: WoodworkingOutput | None = None,
        packing: PackingOutput | None = None,
        installation: InstallationOutput | None = None,
        # Legacy flat-style arguments (for backward compatibility)
        cabinet: Cabinet | None = None,
        cut_list: list[CutPiece] | None = None,
        material_estimates: dict[MaterialSpec, MaterialEstimate] | None = None,
        total_estimate: MaterialEstimate | None = None,
        hardware: list[HardwareItem] | None = None,
        errors: list[str] | None = None,
        packing_result: "PackingResult | None" = None,
        installation_hardware: list[HardwareItem] | None = None,
        installation_instructions: str | None = None,
        installation_warnings: list[str] | None = None,
        stud_analysis: dict[str, Any] | None = None,
    ) -> None:
        """Initialize LayoutOutput with either composite or flat arguments.

        Args:
            core: CoreLayoutOutput instance (new style).
            woodworking: WoodworkingOutput instance (new style).
            packing: PackingOutput instance (new style).
            installation: InstallationOutput instance (new style).
            cabinet: Generated cabinet entity (legacy style).
            cut_list: List of cut pieces (legacy style).
            material_estimates: Material estimates by type (legacy style).
            total_estimate: Total material estimate (legacy style).
            hardware: Hardware items for assembly (legacy style).
            errors: Error messages (legacy style).
            packing_result: Bin packing result (legacy style).
            installation_hardware: Installation hardware items (legacy style).
            installation_instructions: Installation instructions (legacy style).
            installation_warnings: Installation warnings (legacy style).
            stud_analysis: Stud alignment analysis (legacy style).
        """
        if core is not None:
            # New composite style - use provided core directly
            self.core = core
            self.woodworking = woodworking
            self.packing = packing
            self.installation = installation
        else:
            # Legacy flat style - build composite from flat arguments
            self.core = CoreLayoutOutput(
                cabinet=cabinet,  # type: ignore
                cut_list=cut_list if cut_list is not None else [],
                material_estimates=material_estimates
                if material_estimates is not None
                else {},
                total_estimate=total_estimate,  # type: ignore
                errors=errors if errors is not None else [],
            )

            self.woodworking = WoodworkingOutput(
                hardware=hardware if hardware is not None else []
            )

            self.packing = (
                PackingOutput(packing_result=packing_result) if packing_result else None
            )

            if any(
                [
                    installation_hardware,
                    installation_instructions,
                    installation_warnings,
                    stud_analysis,
                ]
            ):
                self.installation = InstallationOutput(
                    hardware=installation_hardware
                    if installation_hardware is not None
                    else [],
                    instructions=installation_instructions,
                    warnings=installation_warnings
                    if installation_warnings is not None
                    else [],
                    stud_analysis=stud_analysis,
                )
            else:
                self.installation = None

    # Backward compatibility properties

    @property
    def cabinet(self) -> Cabinet:
        """Get the generated cabinet entity."""
        return self.core.cabinet

    @property
    def cut_list(self) -> list[CutPiece]:
        """Get the list of cut pieces."""
        return self.core.cut_list

    @property
    def material_estimates(self) -> dict[MaterialSpec, MaterialEstimate]:
        """Get material estimates grouped by material type."""
        return self.core.material_estimates

    @property
    def total_estimate(self) -> MaterialEstimate:
        """Get the total material estimate."""
        return self.core.total_estimate

    @property
    def errors(self) -> list[str]:
        """Get list of error messages."""
        return self.core.errors

    @property
    def hardware(self) -> list[HardwareItem]:
        """Get list of hardware items required for assembly."""
        if self.woodworking is None:
            return []
        return self.woodworking.hardware

    @property
    def packing_result(self) -> "PackingResult | None":
        """Get bin packing optimization result."""
        if self.packing is None:
            return None
        return self.packing.packing_result

    @packing_result.setter
    def packing_result(self, value: "PackingResult | None") -> None:
        """Set bin packing optimization result."""
        if self.packing is None:
            self.packing = PackingOutput(packing_result=value)
        else:
            self.packing.packing_result = value

    @property
    def installation_hardware(self) -> list[HardwareItem] | None:
        """Get list of installation hardware items."""
        if self.installation is None:
            return None
        return self.installation.hardware

    @property
    def installation_instructions(self) -> str | None:
        """Get installation instructions in markdown format."""
        if self.installation is None:
            return None
        return self.installation.instructions

    @property
    def installation_warnings(self) -> list[str] | None:
        """Get list of installation-related warnings."""
        if self.installation is None:
            return None
        return self.installation.warnings

    @property
    def stud_analysis(self) -> dict[str, Any] | None:
        """Get stud alignment analysis results."""
        if self.installation is None:
            return None
        return self.installation.stud_analysis

    @property
    def is_valid(self) -> bool:
        """Check if the layout was generated successfully."""
        return len(self.core.errors) == 0


@dataclass
class RoomLayoutOutput:
    """Output DTO from room layout generation.

    Contains the complete room layout with cabinets positioned on multiple walls,
    their 3D transforms for rendering, and combined material estimates.

    Attributes:
        room: The Room entity with wall segment definitions.
        cabinets: List of Cabinet entities, one per wall section.
        transforms: List of SectionTransform objects for 3D positioning.
        cut_list: Combined cut list from all cabinets.
        material_estimates: Material estimates grouped by material type.
        total_estimate: Total material estimate across all cabinets.
        errors: List of error messages if generation failed.
        packing_result: Result from bin packing optimization, if enabled.
        installation_hardware: List of installation hardware items.
        installation_instructions: Installation instructions in markdown format.
        installation_warnings: List of installation-related warnings.
        stud_analysis: Stud alignment analysis results as a dictionary.
    """

    room: Room
    cabinets: list[Cabinet]
    transforms: list[SectionTransform]
    cut_list: list[CutPiece]
    material_estimates: dict[MaterialSpec, MaterialEstimate]
    total_estimate: MaterialEstimate
    errors: list[str] = field(default_factory=list)
    packing_result: "PackingResult | None" = None
    installation_hardware: list[HardwareItem] | None = None
    installation_instructions: str | None = None
    installation_warnings: list[str] | None = None
    stud_analysis: dict | None = None

    @property
    def is_valid(self) -> bool:
        """Check if the room layout was generated successfully."""
        return len(self.errors) == 0


__all__ = [
    "CoreLayoutOutput",
    "InstallationOutput",
    "LayoutOutput",
    "PackingOutput",
    "RoomLayoutOutput",
    "WoodworkingOutput",
]
