"""Installation support package for cabinet mounting.

This package provides all components for cabinet installation planning:
- Configuration for installation parameters
- Data models for installation specifications
- Stud alignment analysis
- Weight estimation
- Mounting hardware generation
- French cleat specifications
- Markdown instruction generation

All public symbols are re-exported from this module for backward compatibility.
The original API is preserved through the InstallationService facade.

Example:
    >>> from cabinets.domain.services.installation import (
    ...     InstallationService,
    ...     InstallationConfig,
    ... )
    >>> config = InstallationConfig(
    ...     wall_type=WallType.DRYWALL,
    ...     mounting_system=MountingSystem.FRENCH_CLEAT,
    ... )
    >>> service = InstallationService(config)
    >>> plan = service.generate_plan(cabinet, left_edge_position=12.0)
"""

# Re-export configuration
from .config import InstallationConfig

# Re-export data models
from .models import (
    CleatSpec,
    InstallationPlan,
    StudHitAnalysis,
    WeightEstimate,
)

# Re-export specialized services (for advanced use cases)
from .cleat_service import CleatService
from .instruction_generator import InstructionGenerator
from .mounting_service import MountingService
from .stud_analyzer import StudAnalyzer
from .weight_estimator import WeightEstimator

# Re-export the main facade service
from .installation_facade import InstallationService

__all__ = [
    # Configuration
    "InstallationConfig",
    # Data models
    "CleatSpec",
    "InstallationPlan",
    "StudHitAnalysis",
    "WeightEstimate",
    # Main service facade (backward compatible API)
    "InstallationService",
    # Specialized services (for advanced use cases)
    "CleatService",
    "InstructionGenerator",
    "MountingService",
    "StudAnalyzer",
    "WeightEstimator",
]
