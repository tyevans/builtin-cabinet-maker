"""Section and row spec adapter functions.

This module provides conversion functions that transform the Pydantic SectionConfig
and RowConfig models from the configuration schema into domain-level SectionSpec
and RowSpec objects.

Note: As of TD-07, SectionTypeConfig is now an alias for domain SectionType,
eliminating the need for enum conversion.
"""

from cabinets.application.config.schemas import (
    CabinetConfiguration,
    RowConfig,
    SectionConfig,
    SectionRowConfig,
    SectionTypeConfig,
)
from cabinets.domain.section_resolver import RowSpec, SectionRowSpec, SectionSpec


def config_to_section_specs(config: CabinetConfiguration) -> list[SectionSpec]:
    """Convert configuration sections to domain SectionSpec objects.

    This function transforms the Pydantic SectionConfig models from the
    configuration schema into domain-level SectionSpec objects that can
    be used with LayoutCalculator.generate_cabinet_from_specs().

    If no sections are specified in the config, returns a single "fill"
    section with 0 shelves (the default behavior).

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of SectionSpec objects ready for use with the domain layer.
        Will always contain at least one section.

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> section_specs = config_to_section_specs(config)
        >>> cabinet = calculator.generate_cabinet_from_specs(wall, params, section_specs)
    """
    sections = config.cabinet.sections

    if not sections:
        # Default: single fill section with no shelves
        return [SectionSpec(width="fill", shelves=0)]

    return [_section_config_to_spec(section) for section in sections]


def config_to_all_section_specs(config: CabinetConfiguration) -> list[SectionSpec]:
    """Extract all section specs from config, whether in flat sections or rows.

    This function is useful for room layouts where sections need to be
    extracted from either the flat sections list or from within rows,
    preserving wall assignments.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        List of all SectionSpec objects from the configuration.
        Returns sections from rows if rows are defined, otherwise from sections.
    """
    # If rows are defined, extract sections from each row
    if config.cabinet.rows:
        all_sections: list[SectionSpec] = []
        for row in config.cabinet.rows:
            for section in row.sections:
                all_sections.append(_section_config_to_spec(section))
        return all_sections

    # Otherwise use flat sections
    return config_to_section_specs(config)


def has_section_specs(config: CabinetConfiguration) -> bool:
    """Check if the configuration has explicit section specifications.

    This is useful for determining whether to use the new specs-based
    cabinet generation or the legacy uniform sections approach.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        True if the config has sections with explicit specifications
        (either fixed widths or varying shelf counts), False otherwise.
    """
    sections = config.cabinet.sections
    if not sections:
        return False

    # If there's only one section with fill width and default shelves,
    # we could use the legacy approach, but for consistency we'll
    # consider any explicit sections list as "having specs"
    return len(sections) > 0


def has_row_specs(config: CabinetConfiguration) -> bool:
    """Check if the configuration uses multi-row layout.

    This determines whether to use the row-based cabinet generation
    which supports vertically stacked sections.

    Args:
        config: A validated CabinetConfiguration instance

    Returns:
        True if the config has rows defined, False otherwise.
    """
    return config.cabinet.rows is not None and len(config.cabinet.rows) > 0


def config_to_row_specs(config: CabinetConfiguration) -> list[RowSpec]:
    """Convert configuration rows to domain RowSpec objects.

    This function transforms the Pydantic RowConfig models from the
    configuration schema into domain-level RowSpec objects that can
    be used with LayoutCalculator for multi-row cabinet generation.

    Each row contains one or more sections that are arranged horizontally
    within that row. Rows are stacked vertically from bottom to top.

    Args:
        config: A validated CabinetConfiguration instance with rows defined

    Returns:
        List of RowSpec objects ready for use with the domain layer.
        Will always contain at least one row if rows are defined.

    Raises:
        ValueError: If config does not have rows defined

    Example:
        >>> config = load_config(Path("my-cabinet.json"))
        >>> if has_row_specs(config):
        ...     row_specs = config_to_row_specs(config)
        ...     cabinet = calculator.generate_cabinet_from_row_specs(wall, params, row_specs)
    """
    if not config.cabinet.rows:
        raise ValueError(
            "Configuration does not have rows defined. Use config_to_section_specs() instead."
        )

    return [_row_config_to_spec(row) for row in config.cabinet.rows]


def _section_row_config_to_spec(row_config: SectionRowConfig) -> SectionRowSpec:
    """Convert a single SectionRowConfig to a SectionRowSpec.

    Args:
        row_config: The Pydantic section row configuration model

    Returns:
        A domain SectionRowSpec object
    """
    section_type = _section_type_config_to_domain(row_config.section_type)

    return SectionRowSpec(
        height=row_config.height,
        section_type=section_type,
        shelves=row_config.shelves,
        component_config=row_config.component_config,
        min_height=row_config.min_height,
        max_height=row_config.max_height,
    )


def _section_config_to_spec(section_config: SectionConfig) -> SectionSpec:
    """Convert a single SectionConfig to a SectionSpec.

    Args:
        section_config: The Pydantic section configuration model

    Returns:
        A domain SectionSpec object
    """
    # Map SectionTypeConfig to domain SectionType
    section_type = _section_type_config_to_domain(section_config.section_type)

    # Convert section rows if present
    row_specs: tuple[SectionRowSpec, ...] | None = None
    if section_config.rows:
        row_specs = tuple(
            _section_row_config_to_spec(row) for row in section_config.rows
        )

    return SectionSpec(
        width=section_config.width,
        shelves=section_config.shelves,
        wall=section_config.wall,
        height_mode=section_config.height_mode.value
        if section_config.height_mode
        else None,
        section_type=section_type,
        min_width=section_config.min_width,
        max_width=section_config.max_width,
        depth=section_config.depth,
        component_config=section_config.component_config,
        row_specs=row_specs,
    )


def _section_type_config_to_domain(config_type: SectionTypeConfig) -> SectionTypeConfig:
    """Return the section type directly (no conversion needed).

    As of TD-07, SectionTypeConfig is now an alias for domain SectionType,
    so no conversion is needed. This function is kept for backward compatibility
    but simply returns its input.

    Args:
        config_type: The configuration section type enum (which IS the domain enum)

    Returns:
        The same SectionType enum value (no conversion needed)
    """
    # Since TD-07, SectionTypeConfig is an alias for SectionType - no conversion needed
    return config_type


def _row_config_to_spec(row_config: RowConfig) -> RowSpec:
    """Convert a single RowConfig to a RowSpec.

    Args:
        row_config: The Pydantic row configuration model

    Returns:
        A domain RowSpec object
    """
    section_specs = tuple(
        _section_config_to_spec(section) for section in row_config.sections
    )

    return RowSpec(
        height=row_config.height,
        section_specs=section_specs,
        min_height=row_config.min_height,
        max_height=row_config.max_height,
    )


__all__ = [
    "config_to_all_section_specs",
    "config_to_row_specs",
    "config_to_section_specs",
    "has_row_specs",
    "has_section_specs",
]
