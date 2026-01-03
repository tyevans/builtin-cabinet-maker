"""Safety compliance value objects (FRD-21)."""

from __future__ import annotations

from enum import Enum


class SafetyCheckStatus(str, Enum):
    """Result status for safety checks.

    Indicates the outcome of a safety validation check.

    Attributes:
        PASS: Check passed successfully - no safety concerns.
        WARNING: Check identified a potential concern that should be reviewed.
        ERROR: Check identified a violation that must be addressed.
        NOT_APPLICABLE: Check was skipped - not relevant to this configuration.
    """

    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


class SafetyCategory(str, Enum):
    """Categories of safety checks.

    Groups safety checks by their domain for organized reporting
    and selective enabling/disabling of check categories.

    Attributes:
        STRUCTURAL: Weight capacity, deflection, span limits.
        STABILITY: Anti-tip requirements, center of gravity analysis.
        ACCESSIBILITY: ADA reach ranges, accessible storage percentage.
        CLEARANCE: Building code clearances (electrical, heat, egress).
        MATERIAL: Formaldehyde emissions, VOC compliance.
        CHILD_SAFETY: Entrapment hazards, sharp edges, soft-close hardware.
        SEISMIC: Earthquake zone anchoring requirements.
    """

    STRUCTURAL = "structural"
    STABILITY = "stability"
    ACCESSIBILITY = "accessibility"
    CLEARANCE = "clearance"
    MATERIAL = "material"
    CHILD_SAFETY = "child_safety"
    SEISMIC = "seismic"


class SeismicZone(str, Enum):
    """IBC Seismic Design Categories.

    Defines seismic risk zones per International Building Code.
    Higher letters indicate greater seismic risk and stricter
    anchoring requirements.

    Attributes:
        A: Low seismic risk - minimal anchoring.
        B: Low-moderate seismic risk.
        C: Moderate seismic risk.
        D: High seismic risk - enhanced anchoring required.
        E: Very high seismic risk - enhanced anchoring required.
        F: Very high seismic risk near major faults.

    Note:
        Zones D, E, F require seismic-rated anchoring hardware
        and may require structural engineering review.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class MaterialCertification(str, Enum):
    """Material certification levels for formaldehyde emissions.

    Tracks compliance with CARB ATCM 93120 and EPA TSCA Title VI
    requirements for composite wood products.

    Attributes:
        CARB_PHASE2: CARB Phase 2 compliant (TSCA Title VI equivalent).
        NAF: No Added Formaldehyde - exempt resin systems.
        ULEF: Ultra-Low Emitting Formaldehyde - below Phase 2 limits.
        NONE: Known non-compliant or no certification.
        UNKNOWN: Certification status not specified.

    Note:
        NAF and ULEF certifications exceed Phase 2 requirements and
        are considered best practice for indoor air quality.
    """

    CARB_PHASE2 = "carb_phase2"
    NAF = "naf"
    ULEF = "ulef"
    NONE = "none"
    UNKNOWN = "unknown"


class VOCCategory(str, Enum):
    """VOC content categories for finishes and coatings.

    Categorizes finishes by volatile organic compound content
    per SCAQMD Rule 1113 guidelines.

    Attributes:
        SUPER_COMPLIANT: Less than 10 g/L VOC content.
        COMPLIANT: Less than 50 g/L VOC content.
        STANDARD: Standard VOC content (may exceed 50 g/L).
        UNKNOWN: VOC category not specified.
    """

    SUPER_COMPLIANT = "super_compliant"
    COMPLIANT = "compliant"
    STANDARD = "standard"
    UNKNOWN = "unknown"


class ADAStandard(str, Enum):
    """ADA accessibility standard versions.

    Specifies which accessibility standard to use for compliance
    checking. Different standards may have different requirements.

    Attributes:
        ADA_2010: 2010 ADA Standards for Accessible Design (federal).
        ANSI_A117_1: ANSI A117.1 Accessible and Usable Buildings standard.
    """

    ADA_2010 = "ADA_2010"
    ANSI_A117_1 = "ANSI_A117.1"
