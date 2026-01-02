"""Woodworking intelligence domain services and data models.

This package provides:
- Data models for woodworking intelligence features
- Joint specifications for panel connections
- Span limits for material safety
- Weight capacity estimations
- Hardware aggregation
- WoodworkingIntelligence service for joinery analysis

This module maintains full backward compatibility with the original
woodworking.py module by re-exporting all public APIs.
"""

from __future__ import annotations

# Re-export constants (used by safety.py and others)
from .constants import (
    # Span and material constants
    SPAN_LIMITS,
    MATERIAL_MODULUS,
    SAFETY_FACTOR,
    MAX_DEFLECTION_RATIO,
    # Hardware constants
    CASE_SCREW_SPEC,
    CASE_SCREW_SPACING,
    BACK_PANEL_SCREW_SPEC,
    BACK_PANEL_SCREW_SPACING,
    POCKET_SCREW_SPEC,
    POCKET_SCREW_COARSE_NOTE,
    POCKET_SCREW_FINE_NOTE,
    DOWEL_SPEC,
    BISCUIT_SPEC_10,
    BISCUIT_SPEC_20,
    # Functions
    get_max_span,
)

# Re-export config
from .config import WoodworkingConfig

# Re-export models
from .models import (
    JointSpec,
    ConnectionJoinery,
    SpanWarning,
    WeightCapacity,
    HardwareList,
    GrainAnnotation,
)

# Re-export joint selection (Strategy pattern)
from .joint_selection import (
    JointSelector,
    ShelfJointSelector,
    BackPanelJointSelector,
    DividerJointSelector,
    HorizontalDividerJointSelector,
    TopPanelJointSelector,
    BottomPanelJointSelector,
    FaceFrameJointSelector,
    DefaultJointSelector,
    JOINT_SELECTORS,
    select_joint,
    JointSpecCalculator,
)

# Re-export specialized services
from .span_checker import SpanChecker
from .capacity_calculator import CapacityCalculator
from .hardware_calculator import HardwareCalculator
from .grain_advisor import GrainAdvisor

# Re-export main facade
from .woodworking_facade import WoodworkingIntelligence

__all__ = [
    # Constants
    "SPAN_LIMITS",
    "MATERIAL_MODULUS",
    "SAFETY_FACTOR",
    "MAX_DEFLECTION_RATIO",
    "CASE_SCREW_SPEC",
    "CASE_SCREW_SPACING",
    "BACK_PANEL_SCREW_SPEC",
    "BACK_PANEL_SCREW_SPACING",
    "POCKET_SCREW_SPEC",
    "POCKET_SCREW_COARSE_NOTE",
    "POCKET_SCREW_FINE_NOTE",
    "DOWEL_SPEC",
    "BISCUIT_SPEC_10",
    "BISCUIT_SPEC_20",
    "get_max_span",
    # Config
    "WoodworkingConfig",
    # Models
    "JointSpec",
    "ConnectionJoinery",
    "SpanWarning",
    "WeightCapacity",
    "HardwareList",
    "GrainAnnotation",
    # Joint selection (Strategy pattern)
    "JointSelector",
    "ShelfJointSelector",
    "BackPanelJointSelector",
    "DividerJointSelector",
    "HorizontalDividerJointSelector",
    "TopPanelJointSelector",
    "BottomPanelJointSelector",
    "FaceFrameJointSelector",
    "DefaultJointSelector",
    "JOINT_SELECTORS",
    "select_joint",
    "JointSpecCalculator",
    # Specialized services
    "SpanChecker",
    "CapacityCalculator",
    "HardwareCalculator",
    "GrainAdvisor",
    # Main facade
    "WoodworkingIntelligence",
]
