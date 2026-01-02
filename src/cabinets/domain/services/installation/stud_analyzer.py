"""Stud hit analysis service.

This module provides the StudAnalyzer class for analyzing wall stud
alignment with cabinet mounting points.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import InstallationConfig
from .models import StudHitAnalysis

if TYPE_CHECKING:
    from ...entities import Cabinet


class StudAnalyzer:
    """Service for analyzing wall stud alignment with cabinet mounting points.

    Determines potential mounting point positions across the cabinet width
    and checks which ones align with wall studs based on the configured
    stud spacing and offset.
    """

    def __init__(self, config: InstallationConfig) -> None:
        """Initialize the stud analyzer.

        Args:
            config: Installation configuration parameters.
        """
        self.config = config

    def calculate_stud_hits(
        self, cabinet: "Cabinet", left_edge: float
    ) -> StudHitAnalysis:
        """Analyze which mounting points align with wall studs.

        Determines potential mounting point positions across the cabinet
        width and checks which ones align with wall studs based on the
        configured stud spacing and offset.

        Args:
            cabinet: Cabinet to analyze.
            left_edge: Position of cabinet left edge from wall start.

        Returns:
            StudHitAnalysis with stud alignment information.
        """
        cabinet_right_edge = left_edge + cabinet.width
        stud_positions: list[float] = []
        non_stud_positions: list[float] = []

        # Calculate all stud positions that fall within the cabinet span
        # First stud is at stud_offset from wall start
        current_stud = self.config.stud_offset
        while current_stud <= cabinet_right_edge:
            if current_stud >= left_edge:
                # This stud is within cabinet span
                # Record the position relative to the wall (absolute position)
                stud_positions.append(current_stud)
            current_stud += self.config.stud_spacing

        # Calculate potential mounting points that miss studs
        # Mounting points are typically at the cabinet edges and at regular intervals
        # Standard mounting points: near left edge, near right edge, and any in between
        mounting_interval = 16.0  # Standard mounting point spacing
        edge_offset = 3.0  # Offset from cabinet edge for mounting points

        # Collect all potential mounting point positions
        potential_points: list[float] = []
        potential_points.append(left_edge + edge_offset)  # Near left edge
        potential_points.append(cabinet_right_edge - edge_offset)  # Near right edge

        # Add intermediate points if cabinet is wide enough
        current_point = left_edge + edge_offset + mounting_interval
        while current_point < cabinet_right_edge - edge_offset:
            potential_points.append(current_point)
            current_point += mounting_interval

        # Determine which points hit studs (within 0.5" tolerance)
        stud_tolerance = 0.5
        for point in potential_points:
            hits_stud = False
            for stud_pos in stud_positions:
                if abs(point - stud_pos) <= stud_tolerance:
                    hits_stud = True
                    break
            if not hits_stud:
                non_stud_positions.append(point)

        stud_hit_count = len(stud_positions)
        recommendation: str | None = None

        if stud_hit_count < 2:
            if stud_hit_count == 0:
                recommendation = (
                    "No stud hits detected within cabinet span. "
                    "Consider using toggle bolts, wall anchors, or repositioning "
                    "the cabinet for better stud alignment."
                )
            else:
                recommendation = (
                    "Only 1 stud hit detected. For secure mounting, consider "
                    "using toggle bolts for non-stud locations or repositioning "
                    "cabinet to align with at least 2 studs."
                )

        return StudHitAnalysis(
            cabinet_left_edge=left_edge,
            cabinet_width=cabinet.width,
            stud_positions=tuple(stud_positions),
            non_stud_positions=tuple(non_stud_positions),
            stud_hit_count=stud_hit_count,
            recommendation=recommendation,
        )
