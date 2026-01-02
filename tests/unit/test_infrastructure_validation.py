"""Unit tests for infrastructure configuration validation.

These tests verify the infrastructure-related validation rules (FRD-15):
- V-01: Cutout within panel bounds
- V-02: Cutout edge distance (min 1")
- V-03: Cutout overlap detection
- V-04: Outlet accessibility warning
- V-05: Grommet size validation
- V-06: Section index validation
- V-07: Ventilation adequacy warning
"""

from cabinets.application.config import (
    CabinetConfig,
    CabinetConfiguration,
    GrommetConfigSchema,
    InfrastructureConfigSchema,
    LightingConfigSchema,
    LightingLocationConfig,
    LightingTypeConfig,
    OutletConfigSchema,
    OutletTypeConfig,
    PositionConfigSchema,
    SectionConfig,
    VentilationConfigSchema,
    VentilationPatternConfig,
    check_infrastructure_advisories,
    validate_config,
)
from cabinets.application.config.validator import (
    STANDARD_GROMMET_SIZES,
    ValidationError,
    ValidationWarning,
    _cutouts_overlap,
    _get_panel_dimensions,
    _get_section_count,
)


class TestGetPanelDimensions:
    """Tests for _get_panel_dimensions helper function."""

    def test_back_panel_dimensions(self) -> None:
        """Back panel should have width x height dimensions."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        dims = _get_panel_dimensions(config, "back")
        assert dims == (48.0, 84.0)

    def test_left_side_panel_dimensions(self) -> None:
        """Left side panel should have depth x height dimensions."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        dims = _get_panel_dimensions(config, "left_side")
        assert dims == (12.0, 84.0)

    def test_right_side_panel_dimensions(self) -> None:
        """Right side panel should have depth x height dimensions."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        dims = _get_panel_dimensions(config, "right_side")
        assert dims == (12.0, 84.0)

    def test_top_panel_dimensions(self) -> None:
        """Top panel should have width x depth dimensions."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        dims = _get_panel_dimensions(config, "top")
        assert dims == (48.0, 12.0)

    def test_bottom_panel_dimensions(self) -> None:
        """Bottom panel should have width x depth dimensions."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        dims = _get_panel_dimensions(config, "bottom")
        assert dims == (48.0, 12.0)

    def test_unknown_panel_defaults_to_width_height(self) -> None:
        """Unknown panel names should default to cabinet width x height."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        dims = _get_panel_dimensions(config, "unknown")
        assert dims == (48.0, 84.0)


class TestCutoutsOverlap:
    """Tests for _cutouts_overlap helper function."""

    def test_non_overlapping_cutouts_horizontally(self) -> None:
        """Cutouts separated horizontally should not overlap."""
        result = _cutouts_overlap(
            (0, 0),
            (10, 10),
            (15, 0),
            (10, 10),
        )
        assert result is False

    def test_non_overlapping_cutouts_vertically(self) -> None:
        """Cutouts separated vertically should not overlap."""
        result = _cutouts_overlap(
            (0, 0),
            (10, 10),
            (0, 15),
            (10, 10),
        )
        assert result is False

    def test_overlapping_cutouts(self) -> None:
        """Cutouts that share area should overlap."""
        result = _cutouts_overlap(
            (0, 0),
            (10, 10),
            (5, 5),
            (10, 10),
        )
        assert result is True

    def test_touching_cutouts_do_not_overlap(self) -> None:
        """Cutouts that only touch edges should not overlap."""
        # Touching on right edge
        result = _cutouts_overlap(
            (0, 0),
            (10, 10),
            (10, 0),
            (10, 10),
        )
        assert result is False

        # Touching on top edge
        result = _cutouts_overlap(
            (0, 0),
            (10, 10),
            (0, 10),
            (10, 10),
        )
        assert result is False

    def test_identical_cutouts_overlap(self) -> None:
        """Identical cutouts should overlap."""
        result = _cutouts_overlap(
            (5, 5),
            (10, 10),
            (5, 5),
            (10, 10),
        )
        assert result is True

    def test_contained_cutout_overlaps(self) -> None:
        """A cutout fully inside another should overlap."""
        result = _cutouts_overlap(
            (0, 0),
            (20, 20),
            (5, 5),
            (5, 5),
        )
        assert result is True


class TestGetSectionCount:
    """Tests for _get_section_count helper function."""

    def test_single_row_layout_with_sections(self) -> None:
        """Single-row layout should count sections directly."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=16.0),
                    SectionConfig(width=16.0),
                    SectionConfig(width="fill"),
                ],
            ),
        )
        count = _get_section_count(config)
        assert count == 3

    def test_empty_sections_returns_one(self) -> None:
        """Empty sections list should return 1 (implicit single section)."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )
        count = _get_section_count(config)
        assert count == 1


class TestV01CutoutWithinPanelBounds:
    """Tests for V-01: Cutout within panel bounds."""

    def test_outlet_within_bounds(self) -> None:
        """Outlet fully within panel should pass validation."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    )
                ]
            ),
        )

        result = validate_config(config)
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) == 0

    def test_outlet_exceeds_panel_width(self) -> None:
        """Outlet extending beyond panel width should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(
                            x=47.0, y=40.0
                        ),  # x + outlet_width > 48
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) >= 1

    def test_outlet_exceeds_panel_height(self) -> None:
        """Outlet extending beyond panel height should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(
                            x=20.0, y=82.0
                        ),  # y + outlet_height > 84
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) >= 1

    def test_grommet_within_bounds(self) -> None:
        """Grommet fully within panel should pass validation."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    )
                ]
            ),
        )

        result = validate_config(config)
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) == 0

    def test_grommet_exceeds_panel_bounds(self) -> None:
        """Grommet extending beyond panel should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=3.0,
                        panel="back",
                        position=PositionConfigSchema(x=46.0, y=40.0),  # x + 3 > 48
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) >= 1

    def test_ventilation_within_bounds(self) -> None:
        """Ventilation area fully within panel should pass validation."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                ventilation=[
                    VentilationConfigSchema(
                        pattern=VentilationPatternConfig.GRID,
                        panel="back",
                        position=PositionConfigSchema(x=10.0, y=10.0),
                        width=10.0,
                        height=10.0,
                    )
                ]
            ),
        )

        result = validate_config(config)
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) == 0

    def test_ventilation_exceeds_panel_bounds(self) -> None:
        """Ventilation area extending beyond panel should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                ventilation=[
                    VentilationConfigSchema(
                        pattern=VentilationPatternConfig.GRID,
                        panel="back",
                        position=PositionConfigSchema(x=40.0, y=10.0),
                        width=15.0,  # 40 + 15 > 48
                        height=10.0,
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        bounds_errors = [
            e for e in result.errors if "exceeds panel dimensions" in e.message
        ]
        assert len(bounds_errors) >= 1


class TestV02CutoutEdgeDistance:
    """Tests for V-02: Cutout edge distance (min 1")."""

    def test_outlet_with_proper_edge_distance(self) -> None:
        """Outlet with adequate edge distance should pass validation."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    )
                ]
            ),
        )

        result = validate_config(config)
        edge_errors = [e for e in result.errors if "too close to edge" in e.message]
        assert len(edge_errors) == 0

    def test_outlet_too_close_to_left_edge(self) -> None:
        """Outlet too close to left edge should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=0.5, y=40.0),  # < 1" from left
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        edge_errors = [e for e in result.errors if "too close to edge" in e.message]
        assert len(edge_errors) >= 1

    def test_outlet_too_close_to_bottom_edge(self) -> None:
        """Outlet too close to bottom edge should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(
                            x=20.0, y=0.5
                        ),  # < 1" from bottom
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        edge_errors = [e for e in result.errors if "too close to edge" in e.message]
        assert len(edge_errors) >= 1

    def test_outlet_too_close_to_right_edge(self) -> None:
        """Outlet too close to right edge should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        # Single outlet is ~2.75" wide, position at 45.0 puts right edge at 47.75
                        # Panel is 48" so right edge distance is 0.25" < 1"
                        position=PositionConfigSchema(x=45.0, y=40.0),
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        edge_errors = [e for e in result.errors if "too close to edge" in e.message]
        assert len(edge_errors) >= 1

    def test_grommet_too_close_to_edge(self) -> None:
        """Grommet too close to edge should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=0.5, y=40.0),  # < 1" from left
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        edge_errors = [e for e in result.errors if "too close to edge" in e.message]
        assert len(edge_errors) >= 1


class TestV03CutoutOverlapDetection:
    """Tests for V-03: Cutout overlap detection."""

    def test_non_overlapping_cutouts(self) -> None:
        """Non-overlapping cutouts on same panel should pass validation."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=10.0, y=40.0),
                    ),
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(
                            x=30.0, y=40.0
                        ),  # Far from first outlet
                    ),
                ]
            ),
        )

        result = validate_config(config)
        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) == 0

    def test_overlapping_outlets_on_same_panel(self) -> None:
        """Overlapping outlets on same panel should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    ),
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(
                            x=21.0, y=41.0
                        ),  # Overlaps with first
                    ),
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) >= 1

    def test_overlapping_outlet_and_grommet(self) -> None:
        """Overlapping outlet and grommet on same panel should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    ),
                ],
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(
                            x=21.0, y=41.0
                        ),  # Overlaps with outlet
                    ),
                ],
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) >= 1

    def test_cutouts_on_different_panels_no_overlap(self) -> None:
        """Cutouts at same position on different panels should not overlap."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=5.0, y=40.0),
                    ),
                ],
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="left_side",  # Different panel
                        position=PositionConfigSchema(x=5.0, y=40.0),
                    ),
                ],
            ),
        )

        result = validate_config(config)
        overlap_errors = [e for e in result.errors if "overlap" in e.message.lower()]
        assert len(overlap_errors) == 0


class TestV04OutletAccessibility:
    """Tests for V-04: Outlet accessibility warning."""

    def test_outlet_not_behind_shelf(self) -> None:
        """Outlet in section without shelves should not produce warning."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=0),  # No shelves
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=10.0, y=40.0),
                    ),
                ]
            ),
        )

        result = validate_config(config)
        shelf_warnings = [
            w for w in result.warnings if "behind fixed shelf" in w.message
        ]
        assert len(shelf_warnings) == 0

    def test_outlet_behind_shelf_produces_warning(self) -> None:
        """Outlet in section with shelves should produce warning."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=3),  # Has shelves
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=10.0, y=40.0),
                    ),
                ]
            ),
        )

        result = validate_config(config)
        shelf_warnings = [
            w for w in result.warnings if "behind fixed shelf" in w.message
        ]
        assert len(shelf_warnings) >= 1

    def test_outlet_on_side_panel_no_shelf_warning(self) -> None:
        """Outlet on side panel should not produce shelf accessibility warning."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0, shelves=3),  # Has shelves
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="left_side",  # Not on back panel
                        position=PositionConfigSchema(x=5.0, y=40.0),
                    ),
                ]
            ),
        )

        result = validate_config(config)
        shelf_warnings = [
            w for w in result.warnings if "behind fixed shelf" in w.message
        ]
        assert len(shelf_warnings) == 0


class TestV05GrommetSizeValidation:
    """Tests for V-05: Grommet size validation."""

    def test_standard_grommet_sizes(self) -> None:
        """Standard grommet sizes (2, 2.5, 3) should pass validation."""
        for size in STANDARD_GROMMET_SIZES:
            config = CabinetConfiguration(
                schema_version="1.6",
                cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
                infrastructure=InfrastructureConfigSchema(
                    grommets=[
                        GrommetConfigSchema(
                            size=size,
                            panel="back",
                            position=PositionConfigSchema(x=20.0, y=40.0),
                        )
                    ]
                ),
            )

            result = validate_config(config)
            size_errors = [
                e for e in result.errors if "Invalid grommet size" in e.message
            ]
            assert len(size_errors) == 0, f"Size {size} should be valid"

    def test_non_standard_grommet_size(self) -> None:
        """Non-standard grommet size should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=1.5,  # Non-standard size
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        size_errors = [e for e in result.errors if "Invalid grommet size" in e.message]
        assert len(size_errors) >= 1
        assert "1.5" in size_errors[0].message
        assert "2, 2.5, or 3" in size_errors[0].message


class TestV06SectionIndexValidation:
    """Tests for V-06: Section index validation."""

    def test_valid_section_index_for_outlet(self) -> None:
        """Outlet with valid section index should pass validation."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0),
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=1,  # Valid - sections 0 and 1 exist
                        panel="back",
                        position=PositionConfigSchema(x=30.0, y=40.0),
                    ),
                ]
            ),
        )

        result = validate_config(config)
        index_errors = [e for e in result.errors if "out of range" in e.message]
        assert len(index_errors) == 0

    def test_invalid_section_index_for_outlet(self) -> None:
        """Outlet with invalid section index should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0),
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=5,  # Invalid - only 2 sections exist
                        panel="back",
                        position=PositionConfigSchema(x=30.0, y=40.0),
                    ),
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        index_errors = [e for e in result.errors if "out of range" in e.message]
        assert len(index_errors) >= 1
        assert "5" in index_errors[0].message

    def test_invalid_section_index_for_lighting(self) -> None:
        """Lighting with invalid section index should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0),
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                lighting=[
                    LightingConfigSchema(
                        type=LightingTypeConfig.LED_STRIP,
                        location=LightingLocationConfig.UNDER_CABINET,
                        section_indices=[0, 1, 5],  # 5 is invalid
                        length=24.0,
                    ),
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        index_errors = [e for e in result.errors if "out of range" in e.message]
        assert len(index_errors) >= 1

    def test_invalid_section_index_for_grommet(self) -> None:
        """Grommet with invalid section index should produce error."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
                sections=[
                    SectionConfig(width=24.0),
                    SectionConfig(width="fill"),
                ],
            ),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                        section_index=10,  # Invalid - only 2 sections exist
                    )
                ]
            ),
        )

        result = validate_config(config)
        assert not result.is_valid
        index_errors = [e for e in result.errors if "out of range" in e.message]
        assert len(index_errors) >= 1


class TestV07VentilationAdequacy:
    """Tests for V-07: Ventilation adequacy warning."""

    def test_outlets_without_ventilation_produces_warning(self) -> None:
        """Configuration with outlets but no ventilation should produce warning."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    ),
                ]
            ),
        )

        result = validate_config(config)
        vent_warnings = [
            w for w in result.warnings if "ventilation" in w.message.lower()
        ]
        assert len(vent_warnings) >= 1

    def test_outlets_with_ventilation_no_warning(self) -> None:
        """Configuration with both outlets and ventilation should not produce warning."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=10.0, y=40.0),
                    ),
                ],
                ventilation=[
                    VentilationConfigSchema(
                        pattern=VentilationPatternConfig.GRID,
                        panel="back",
                        position=PositionConfigSchema(x=30.0, y=10.0),
                        width=10.0,
                        height=10.0,
                    )
                ],
            ),
        )

        result = validate_config(config)
        vent_warnings = [
            w for w in result.warnings if "ventilation" in w.message.lower()
        ]
        assert len(vent_warnings) == 0

    def test_no_outlets_no_ventilation_no_warning(self) -> None:
        """Configuration without outlets should not produce ventilation warning."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    )
                ]
            ),
        )

        result = validate_config(config)
        vent_warnings = [
            w for w in result.warnings if "ventilation" in w.message.lower()
        ]
        assert len(vent_warnings) == 0


class TestNoInfrastructure:
    """Tests for configs without infrastructure."""

    def test_no_infrastructure_config(self) -> None:
        """Config without infrastructure should not produce infrastructure errors."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        result = validate_config(config)
        infra_errors = [e for e in result.errors if "infrastructure" in e.path.lower()]
        assert len(infra_errors) == 0

    def test_empty_infrastructure_config(self) -> None:
        """Config with empty infrastructure should not produce errors."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(),
        )

        result = validate_config(config)
        infra_errors = [e for e in result.errors if "infrastructure" in e.path]
        assert len(infra_errors) == 0


class TestCheckInfrastructureAdvisoriesDirectly:
    """Tests for check_infrastructure_advisories function."""

    def test_returns_empty_list_for_no_infrastructure(self) -> None:
        """check_infrastructure_advisories should return empty list when no infrastructure."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
        )

        results = check_infrastructure_advisories(config)
        assert results == []

    def test_returns_validation_error_type(self) -> None:
        """check_infrastructure_advisories should return proper ValidationError type."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=1.75,  # Non-standard size
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    )
                ]
            ),
        )

        results = check_infrastructure_advisories(config)
        errors = [r for r in results if isinstance(r, ValidationError)]
        assert len(errors) >= 1

    def test_returns_validation_warning_type(self) -> None:
        """check_infrastructure_advisories should return proper ValidationWarning type."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(width=48.0, height=84.0, depth=12.0),
            infrastructure=InfrastructureConfigSchema(
                outlets=[
                    OutletConfigSchema(
                        type=OutletTypeConfig.SINGLE,
                        section_index=0,
                        panel="back",
                        position=PositionConfigSchema(x=20.0, y=40.0),
                    ),
                ]
            ),
        )

        results = check_infrastructure_advisories(config)
        warnings = [r for r in results if isinstance(r, ValidationWarning)]
        assert len(warnings) >= 1  # Should have ventilation warning
