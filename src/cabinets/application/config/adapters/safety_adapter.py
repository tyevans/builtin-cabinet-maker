"""Safety configuration adapter functions.

This module provides conversion functions that transform Pydantic safety-related
configuration models into domain-level SafetyConfig objects.
"""

from typing import TYPE_CHECKING

from cabinets.application.config.schemas import (
    SafetyConfigSchema,
)

if TYPE_CHECKING:
    from cabinets.domain.services.safety import SafetyConfig


def config_to_safety(
    config: SafetyConfigSchema | None,
) -> "SafetyConfig":
    """Convert SafetyConfigSchema to domain SafetyConfig.

    Args:
        config: Safety configuration schema from JSON/YAML config file.

    Returns:
        Domain SafetyConfig object for use with SafetyService.

    Example:
        ```python
        from cabinets.application.config import load_config, config_to_safety

        cabinet_config = load_config("cabinet.json")
        safety_config = config_to_safety(cabinet_config.safety)
        service = SafetyService(safety_config)
        ```
    """
    # Lazy import to avoid circular dependencies
    from cabinets.domain.services.safety import SafetyConfig
    from cabinets.domain.value_objects import (
        ADAStandard,
        MaterialCertification,
        SeismicZone,
        VOCCategory,
    )

    if config is None:
        return SafetyConfig()

    # Parse deflection limit to integer ratio
    deflection_map = {
        "L/200": 200,
        "L/240": 240,
        "L/360": 360,
    }
    deflection_ratio = deflection_map.get(config.deflection_limit, 200)

    # Parse seismic zone
    seismic_zone = None
    if config.seismic_zone:
        seismic_zone = SeismicZone(config.seismic_zone)

    # Parse material certification
    certification_map = {
        "carb_phase2": MaterialCertification.CARB_PHASE2,
        "naf": MaterialCertification.NAF,
        "ulef": MaterialCertification.ULEF,
        "none": MaterialCertification.NONE,
        "unknown": MaterialCertification.UNKNOWN,
    }
    material_cert = certification_map.get(
        config.material_certification, MaterialCertification.UNKNOWN
    )

    # Parse VOC category
    voc_map = {
        "super_compliant": VOCCategory.SUPER_COMPLIANT,
        "compliant": VOCCategory.COMPLIANT,
        "standard": VOCCategory.STANDARD,
        "unknown": VOCCategory.UNKNOWN,
    }
    voc_category = voc_map.get(config.finish_voc_category, VOCCategory.UNKNOWN)

    # Parse accessibility config
    accessibility_enabled = False
    accessibility_standard = ADAStandard.ADA_2010
    if config.accessibility:
        accessibility_enabled = config.accessibility.enabled
        if config.accessibility.standard == "ADA_2010":
            accessibility_standard = ADAStandard.ADA_2010
        else:
            accessibility_standard = ADAStandard.ANSI_A117_1

    return SafetyConfig(
        accessibility_enabled=accessibility_enabled,
        accessibility_standard=accessibility_standard,
        child_safe_mode=config.child_safe_mode,
        seismic_zone=seismic_zone,
        safety_factor=config.safety_factor,
        deflection_limit_ratio=deflection_ratio,
        check_clearances=config.check_clearances,
        generate_labels=config.generate_labels,
        material_certification=material_cert,
        finish_voc_category=voc_category,
    )


__all__ = [
    "config_to_safety",
]
