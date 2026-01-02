"""Edge profile helpers and component.

This module provides:
- Helper functions for edge profile validation and detection
- EdgeProfileComponent for applying edge profiles to panels
"""

from __future__ import annotations

from typing import Any, Literal

from ...entities import Panel
from ...value_objects import PanelType
from ..context import ComponentContext
from ..registry import component_registry
from ..results import GenerationResult, HardwareItem, ValidationResult
from .configs import EdgeProfileConfig
from .enums import EdgeProfileType
from .metadata import ROUTER_BIT_RECOMMENDATIONS, EdgeProfileMetadata


def validate_edge_profile(
    config: EdgeProfileConfig,
    material_thickness: float,
) -> tuple[list[str], list[str]]:
    """Validate edge profile configuration against material.

    Checks:
    - Profile size is positive
    - Profile size doesn't exceed half the material thickness (structural)
    - Profile size doesn't exceed material thickness (impossible)

    Args:
        config: Edge profile configuration.
        material_thickness: Material thickness in inches.

    Returns:
        Tuple of (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Validate size is positive
    if config.size <= 0:
        errors.append("Profile size must be positive")
        return errors, warnings

    # FR-04.5: Profile size validation
    max_safe_size = material_thickness / 2
    if config.size > max_safe_size:
        warnings.append(
            f'Profile size {config.size}" exceeds half material thickness '
            f'({max_safe_size:.3f}"). May weaken edge.'
        )

    if config.size > material_thickness:
        errors.append(
            f'Profile size {config.size}" exceeds material thickness '
            f'({material_thickness}"). Cannot apply profile.'
        )

    return errors, warnings


def detect_visible_edges(
    panel_type: PanelType,
    is_left_edge: bool = False,
    is_right_edge: bool = False,
) -> list[str]:
    """Detect which edges of a panel are visible/exposed.

    Determines front-facing visible edges based on panel type and position.

    Args:
        panel_type: Type of panel.
        is_left_edge: Whether panel is at left edge of cabinet.
        is_right_edge: Whether panel is at right edge of cabinet.

    Returns:
        List of visible edge names ("top", "bottom", "left", "right", "front").
    """
    visible: list[str] = []

    # Shelf panels: front edge is always visible
    if panel_type == PanelType.SHELF:
        visible.append("front")  # Note: front = bottom edge for shelf
        # Left/right edges visible if at cabinet edge
        if is_left_edge:
            visible.append("left")
        if is_right_edge:
            visible.append("right")

    # Face frame pieces: all exposed edges
    elif panel_type in (PanelType.FACE_FRAME_STILE, PanelType.FACE_FRAME_RAIL):
        visible.extend(["top", "bottom", "left", "right"])

    # Valance: front and bottom typically visible
    elif panel_type == PanelType.VALANCE:
        visible.extend(["front", "bottom"])

    # Default: just front edge
    else:
        visible.append("front")

    return visible


def apply_edge_profile_metadata(
    panel: Panel,
    config: EdgeProfileConfig,
    visible_edges: list[str] | None = None,
) -> Panel:
    """Apply edge profile metadata to a panel.

    Creates a new Panel with edge profile metadata added.

    Args:
        panel: Original panel.
        config: Edge profile configuration.
        visible_edges: Override for visible edges (uses auto-detect if None).

    Returns:
        New Panel with edge_profile metadata.
    """
    # Determine edges to profile
    if visible_edges is None:
        visible_edges = detect_visible_edges(panel.panel_type)

    edges = config.get_edges(visible_edges)

    # Get router bit recommendation
    router_bit = ROUTER_BIT_RECOMMENDATIONS.get(config.profile_type)

    # Create metadata
    profile_metadata = EdgeProfileMetadata(
        profile_type=config.profile_type,
        size=config.size,
        edges=tuple(edges),
        router_bit=router_bit,
    )

    # Merge with existing metadata
    new_metadata = dict(panel.metadata)
    new_metadata["edge_profile"] = {
        "profile_type": profile_metadata.profile_type.value,
        "size": profile_metadata.size,
        "edges": list(profile_metadata.edges),
        "router_bit": profile_metadata.router_bit,
    }

    # Create new panel with updated metadata
    return Panel(
        panel_type=panel.panel_type,
        width=panel.width,
        height=panel.height,
        material=panel.material,
        position=panel.position,
        metadata=new_metadata,
        cut_metadata=panel.cut_metadata,
    )


@component_registry.register("decorative.edge_profile")
class EdgeProfileComponent:
    """Edge profile metadata component.

    This component does not generate physical panels - it applies
    edge profile metadata to existing panels. It's typically used
    in combination with shelf or other components.

    Configuration:
        profile_type: Type of edge profile (chamfer, roundover, etc.).
        size: Profile size/radius in inches.
        edges: Specific edges to profile, or "auto" for visible edges.

    Usage:
        Edge profiles are typically specified at the section level and
        applied to panels generated by other components (e.g., shelves).
        This component validates the configuration but generation is
        handled by the layout calculator or parent component.

    Example:
        config = {
            "edge_profile": {
                "profile_type": "roundover",
                "size": 0.25,
                "edges": "auto"
            }
        }
        result = component.validate(config, context)
    """

    def validate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> ValidationResult:
        """Validate edge profile configuration.

        Checks:
        - Profile size is positive
        - Profile size doesn't exceed material thickness (error)
        - Profile size exceeds half material thickness (warning)

        Args:
            config: Edge profile configuration.
            context: Component context with material information.

        Returns:
            ValidationResult with any errors or warnings.
        """
        edge_config = config.get("edge_profile", {})

        if not edge_config:
            return ValidationResult.ok()

        try:
            # Parse edges - can be "auto" string or list of edge names
            edges_value = edge_config.get("edges", "auto")
            if isinstance(edges_value, list):
                edges: tuple[str, ...] | Literal["auto"] = tuple(edges_value)
            else:
                edges = edges_value

            profile_config = EdgeProfileConfig(
                profile_type=EdgeProfileType(
                    edge_config.get("profile_type", "roundover")
                ),
                size=edge_config.get("size", 0.25),
                edges=edges,
            )
        except (ValueError, KeyError) as e:
            return ValidationResult.fail([str(e)])

        # Get material thickness
        material_thickness = context.material.thickness

        # Validate against material
        errors, warnings = validate_edge_profile(profile_config, material_thickness)

        return ValidationResult(tuple(errors), tuple(warnings))

    def generate(
        self, config: dict[str, Any], context: ComponentContext
    ) -> GenerationResult:
        """Edge profile does not generate panels directly.

        Edge profile metadata is applied to panels from other components.
        This method returns an empty result with profile config in metadata.

        Args:
            config: Edge profile configuration.
            context: Component context.

        Returns:
            Empty GenerationResult with profile config in metadata.
        """
        edge_config = config.get("edge_profile", {})

        if not edge_config:
            return GenerationResult()

        return GenerationResult(
            metadata={
                "edge_profile_config": edge_config,
                "note": "Edge profile applied to panels by parent component",
            }
        )

    def hardware(
        self, config: dict[str, Any], context: ComponentContext
    ) -> list[HardwareItem]:
        """Edge profiles require no hardware.

        Edge profiles are router cuts, not hardware installations.

        Args:
            config: Edge profile configuration.
            context: Component context.

        Returns:
            Empty list.
        """
        return []
