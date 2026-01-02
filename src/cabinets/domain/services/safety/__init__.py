"""Safety and compliance analysis package for cabinet configurations.

This package provides comprehensive safety analysis including:
- Weight capacity calculations with safety factors
- Anti-tip requirement identification
- ADA accessibility validation
- Building code clearance checking
- Material safety tracking
- Seismic zone requirements
- Child safety mode recommendations

All safety guidance includes appropriate disclaimers as this software
provides advisory information only, not engineering certification.

The package is organized into specialized sub-services:
- StructuralSafetyService: Weight capacity and span limit checking
- StabilityService: Anti-tip requirements and stability analysis
- AccessibilityService: ADA compliance checking
- ClearanceService: Building code clearance validation
- MaterialComplianceService: Material certification checking
- SeismicService: Seismic zone requirements
- ReportingService: Label and report generation

The SafetyService facade provides backward-compatible API while
delegating to specialized sub-services.

Example:
    from cabinets.domain.services.safety import SafetyService, SafetyConfig

    config = SafetyConfig(accessibility_enabled=True, safety_factor=4.0)
    service = SafetyService(config)
    assessment = service.analyze(cabinet, obstacles)

    if assessment.has_errors:
        for error in assessment.get_errors():
            print(error.formatted_message)
"""

# Re-export constants
from .constants import (
    # Anti-tip
    ANTI_TIP_HEIGHT_THRESHOLD,
    # ADA
    ADA_DISCLAIMER,
    ADA_KNEE_CLEARANCE_DEPTH,
    ADA_KNEE_CLEARANCE_HEIGHT,
    ADA_KNEE_CLEARANCE_WIDTH,
    ADA_MAX_OBSTRUCTION_DEPTH,
    ADA_MAX_REACH_OBSTRUCTED,
    ADA_MAX_REACH_UNOBSTRUCTED,
    ADA_MIN_ACCESSIBLE_PERCENTAGE,
    ADA_MIN_REACH,
    # Child safety
    CHILD_ENTRAPMENT_VOLUME_THRESHOLD,
    # Closet lighting
    CLOSET_LIGHT_CFL_CLEARANCE,
    CLOSET_LIGHT_INCANDESCENT_CLEARANCE,
    CLOSET_LIGHT_RECESSED_CLEARANCE,
    # Egress
    EGRESS_ADJACENT_WARNING,
    # Heat source
    HEAT_SOURCE_HORIZONTAL_CLEARANCE,
    HEAT_SOURCE_VERTICAL_CLEARANCE,
    # Seismic
    HIGH_SEISMIC_ZONES,
    # Structural
    KCMA_SHELF_LOAD_PSF,
    # Disclaimers
    MATERIAL_DISCLAIMER,
    NEC_PANEL_FRONT_CLEARANCE,
    NEC_PANEL_HEIGHT_CLEARANCE,
    NEC_PANEL_WIDTH_CLEARANCE,
    SAFETY_GENERAL_DISCLAIMER,
    WEIGHT_CAPACITY_DISCLAIMER,
)

# Re-export models (dataclasses)
from .models import (
    AccessibilityReport,
    SafetyAssessment,
    SafetyCheckResult,
    SafetyLabel,
    WeightCapacityEstimate,
)

# Re-export value objects used by safety module (for backward compatibility)
from cabinets.domain.value_objects import (
    SafetyCategory,
    SafetyCheckStatus,
)

# Re-export config
from .config import SafetyConfig

# Re-export main facade
from .safety_facade import SafetyService

# Re-export sub-services for advanced usage
from .structural_safety import StructuralSafetyService
from .stability_service import StabilityService
from .accessibility_service import AccessibilityService
from .clearance_service import ClearanceService
from .material_compliance import MaterialComplianceService
from .seismic_service import SeismicService
from .reporting_service import ReportingService

__all__ = [
    # Value objects (re-exported for backward compatibility)
    "SafetyCategory",
    "SafetyCheckStatus",
    # Constants - Anti-tip
    "ANTI_TIP_HEIGHT_THRESHOLD",
    # Constants - ADA
    "ADA_MIN_REACH",
    "ADA_MAX_REACH_UNOBSTRUCTED",
    "ADA_MAX_REACH_OBSTRUCTED",
    "ADA_MAX_OBSTRUCTION_DEPTH",
    "ADA_MIN_ACCESSIBLE_PERCENTAGE",
    "ADA_KNEE_CLEARANCE_HEIGHT",
    "ADA_KNEE_CLEARANCE_WIDTH",
    "ADA_KNEE_CLEARANCE_DEPTH",
    # Constants - Building codes
    "NEC_PANEL_FRONT_CLEARANCE",
    "NEC_PANEL_WIDTH_CLEARANCE",
    "NEC_PANEL_HEIGHT_CLEARANCE",
    "HEAT_SOURCE_VERTICAL_CLEARANCE",
    "HEAT_SOURCE_HORIZONTAL_CLEARANCE",
    "EGRESS_ADJACENT_WARNING",
    "CLOSET_LIGHT_INCANDESCENT_CLEARANCE",
    "CLOSET_LIGHT_RECESSED_CLEARANCE",
    "CLOSET_LIGHT_CFL_CLEARANCE",
    # Constants - Structural
    "KCMA_SHELF_LOAD_PSF",
    # Constants - Child safety
    "CHILD_ENTRAPMENT_VOLUME_THRESHOLD",
    # Constants - Seismic
    "HIGH_SEISMIC_ZONES",
    # Constants - Disclaimers
    "WEIGHT_CAPACITY_DISCLAIMER",
    "SAFETY_GENERAL_DISCLAIMER",
    "ADA_DISCLAIMER",
    "MATERIAL_DISCLAIMER",
    # Models
    "SafetyCheckResult",
    "WeightCapacityEstimate",
    "AccessibilityReport",
    "SafetyLabel",
    "SafetyAssessment",
    # Config
    "SafetyConfig",
    # Main service facade
    "SafetyService",
    # Sub-services (for advanced usage)
    "StructuralSafetyService",
    "StabilityService",
    "AccessibilityService",
    "ClearanceService",
    "MaterialComplianceService",
    "SeismicService",
    "ReportingService",
]
