"""Integration tests for infrastructure integration (FRD-15).

These tests verify that infrastructure configuration parsing, component generation,
cut list formatting, and hardware list generation work together correctly
through the full pipeline.

Phase 6: Integration Testing
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from cabinets.application.commands import GenerateLayoutCommand
from cabinets.application.config.adapter import config_to_section_specs
from cabinets.application.config.schema import (
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
)
from cabinets.application.dtos import LayoutParametersInput, WallInput
from cabinets.domain.components import ComponentContext, component_registry
from cabinets.domain.components.infrastructure import (
    CableManagementComponent,
    ElectricalComponent,
    LightingComponent,
    VentilationComponent,
)
from cabinets.domain.components.results import HardwareItem
from cabinets.domain.entities import Cabinet
from cabinets.domain.services import MaterialEstimate
from cabinets.domain.value_objects import (
    CutPiece,
    CutoutShape,
    MaterialSpec,
    PanelCutout,
    PanelType,
    Point2D,
)
from cabinets.infrastructure.exporters import CutListFormatter, JsonExporter


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ensure_infrastructure_registered() -> None:
    """Ensure infrastructure components are registered for tests."""
    if "infrastructure.lighting" not in component_registry.list():
        component_registry.register("infrastructure.lighting")(LightingComponent)
    if "infrastructure.electrical" not in component_registry.list():
        component_registry.register("infrastructure.electrical")(ElectricalComponent)
    if "infrastructure.cable_management" not in component_registry.list():
        component_registry.register("infrastructure.cable_management")(CableManagementComponent)
    if "infrastructure.ventilation" not in component_registry.list():
        component_registry.register("infrastructure.ventilation")(VentilationComponent)


@pytest.fixture
def simple_cabinet() -> Cabinet:
    """Create a simple cabinet for testing."""
    return Cabinet(
        width=48.0,
        height=84.0,
        depth=12.0,
        material=MaterialSpec.standard_3_4(),
        back_material=MaterialSpec.standard_1_2(),
    )


@pytest.fixture
def component_context() -> ComponentContext:
    """Create a component context for testing."""
    return ComponentContext(
        width=24.0,
        height=72.0,
        depth=11.5,
        material=MaterialSpec.standard_3_4(),
        position=Point2D(0.75, 0.75),
        section_index=0,
        cabinet_width=48.0,
        cabinet_height=84.0,
        cabinet_depth=12.0,
    )


# =============================================================================
# Test 1: Full cabinet with lighting generates cutouts
# =============================================================================


class TestFullCabinetWithLighting:
    """Tests for cabinet with lighting generating cutouts."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_led_strip_lighting_generates_metadata(
        self, component_context: ComponentContext
    ) -> None:
        """LED strip lighting generates proper hardware and metadata."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0],
            "length": 24.0,
        }

        result = component.generate(config, component_context)

        # Verify hardware includes LED components
        hardware_names = [h.name for h in result.hardware]
        assert "LED Strip Light" in hardware_names
        assert "LED Aluminum Channel" in hardware_names
        assert "LED Driver/Transformer" in hardware_names

        # Verify metadata contains lighting specs
        assert "lighting_specs" in result.metadata
        specs = result.metadata["lighting_specs"]
        assert len(specs) == 1
        assert specs[0].length == 24.0

    def test_puck_light_generates_circular_cutouts(
        self, component_context: ComponentContext
    ) -> None:
        """Puck lights generate circular cutout specifications."""
        component = LightingComponent()
        config = {
            "light_type": "puck_light",
            "location": "in_cabinet",
            "section_indices": [0],
            "puck_diameter": 3.0,
            "puck_positions": [
                {"x": 12.0, "y": 6.0},
                {"x": 18.0, "y": 6.0},
            ],
        }

        result = component.generate(config, component_context)

        # Verify cutouts are generated
        assert "cutouts" in result.metadata
        cutouts = result.metadata["cutouts"]
        assert len(cutouts) == 2

        # Verify cutout properties
        for cutout in cutouts:
            assert cutout["cutout_type"] == "puck_light"
            assert cutout["shape"] == "circular"
            assert cutout["diameter"] == 3.0

        # Verify hardware includes puck lights
        hardware_names = [h.name for h in result.hardware]
        assert any("Puck Light" in name for name in hardware_names)

    def test_lighting_config_with_multiple_sections(
        self, component_context: ComponentContext
    ) -> None:
        """Lighting config spanning multiple sections."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0, 1, 2],
            "length": 72.0,
        }

        result = component.generate(config, component_context)

        # Verify lighting spec covers all sections
        assert "lighting_specs" in result.metadata
        specs = result.metadata["lighting_specs"]
        assert len(specs) == 1
        assert set(specs[0].section_indices) == {0, 1, 2}


# =============================================================================
# Test 2: Multiple outlet types in single cabinet
# =============================================================================


class TestMultipleOutletTypes:
    """Tests for multiple outlet types in a single cabinet."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_single_outlet_dimensions(
        self, component_context: ComponentContext
    ) -> None:
        """Single outlet generates correct cutout dimensions."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "single",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
        }

        result = component.generate(config, component_context)

        cutouts = result.metadata["cutouts"]
        assert len(cutouts) == 1
        assert cutouts[0]["width"] == pytest.approx(2.25)  # Standard single outlet width
        assert cutouts[0]["height"] == pytest.approx(4.0)  # Standard outlet height

    def test_double_outlet_dimensions(
        self, component_context: ComponentContext
    ) -> None:
        """Double outlet generates correct cutout dimensions."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "double",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
        }

        result = component.generate(config, component_context)

        cutouts = result.metadata["cutouts"]
        assert len(cutouts) == 1
        assert cutouts[0]["width"] == pytest.approx(4.25)  # Double outlet width
        assert cutouts[0]["height"] == pytest.approx(4.0)

    def test_gfi_outlet_dimensions(
        self, component_context: ComponentContext
    ) -> None:
        """GFI outlet generates correct cutout dimensions."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "gfi",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
        }

        result = component.generate(config, component_context)

        cutouts = result.metadata["cutouts"]
        assert len(cutouts) == 1
        assert cutouts[0]["width"] == pytest.approx(3.0)  # GFI outlet width
        assert cutouts[0]["height"] == pytest.approx(4.75)  # Taller for GFI

    def test_outlet_metadata_includes_conduit_direction(
        self, component_context: ComponentContext
    ) -> None:
        """Outlet metadata includes conduit direction."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "single",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
            "conduit_direction": "top",
        }

        result = component.generate(config, component_context)

        assert "outlet_spec" in result.metadata
        assert result.metadata["outlet_spec"]["conduit_direction"] == "top"


# =============================================================================
# Test 3: Cable management across multiple sections
# =============================================================================


class TestCableManagementAcrossSections:
    """Tests for cable management (grommets) across multiple sections."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_multiple_grommets_different_sizes(
        self, component_context: ComponentContext
    ) -> None:
        """Multiple grommets with different sizes generate correct cutouts."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.0, "panel": "back", "position": {"x": 6.0, "y": 12.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 24.0}},
                {"size": 3.0, "panel": "bottom", "position": {"x": 6.0, "y": 6.0}},
            ]
        }

        result = component.generate(config, component_context)

        # Verify cutouts
        cutouts = result.metadata["cutouts"]
        assert len(cutouts) == 3

        # All should be circular
        for cutout in cutouts:
            assert cutout["shape"] == "circular"

        # Verify sizes match
        sizes = [c["diameter"] for c in cutouts]
        assert sorted(sizes) == [2.0, 2.5, 3.0]

    def test_grommet_hardware_aggregation_by_size(
        self, component_context: ComponentContext
    ) -> None:
        """Hardware list aggregates grommets by size with correct SKUs."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.0, "panel": "back", "position": {"x": 6.0, "y": 12.0}},
                {"size": 2.0, "panel": "back", "position": {"x": 18.0, "y": 12.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 24.0}},
                {"size": 2.5, "panel": "bottom", "position": {"x": 6.0, "y": 6.0}},
                {"size": 2.5, "panel": "bottom", "position": {"x": 12.0, "y": 6.0}},
                {"size": 3.0, "panel": "back", "position": {"x": 6.0, "y": 36.0}},
            ]
        }

        result = component.generate(config, component_context)

        # Verify hardware aggregation
        hardware_dict = {h.sku: h for h in result.hardware}

        # 2.0" grommets: 2 total
        assert "GRM-200-BLK" in hardware_dict
        assert hardware_dict["GRM-200-BLK"].quantity == 2

        # 2.5" grommets: 3 total
        assert "GRM-250-BLK" in hardware_dict
        assert hardware_dict["GRM-250-BLK"].quantity == 3

        # 3.0" grommets: 1 total
        assert "GRM-300-BLK" in hardware_dict
        assert hardware_dict["GRM-300-BLK"].quantity == 1

    def test_grommet_sku_format(
        self, component_context: ComponentContext
    ) -> None:
        """Verify grommet SKU format (GRM-200-BLK, GRM-250-BLK, GRM-300-BLK)."""
        component = CableManagementComponent()

        for size, expected_sku in [(2.0, "GRM-200-BLK"), (2.5, "GRM-250-BLK"), (3.0, "GRM-300-BLK")]:
            config = {
                "grommets": [
                    {"size": size, "panel": "back", "position": {"x": 12.0, "y": 12.0}},
                ]
            }
            result = component.generate(config, component_context)

            assert len(result.hardware) == 1
            assert result.hardware[0].sku == expected_sku


# =============================================================================
# Test 4: Cut list includes all infrastructure notes
# =============================================================================


class TestCutListIncludesInfrastructureNotes:
    """Tests for cut list output including infrastructure notes."""

    def test_cut_list_shows_cutout_notes(self) -> None:
        """Cut list includes cutout notes for infrastructure pieces."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=24.0,
                height=72.0,
                quantity=1,
                label="Back Panel",
                panel_type=PanelType.BACK,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "outlet",
                            "shape": "rectangular",
                            "x": 12.0,
                            "y": 36.0,
                            "width": 4.25,
                            "height": 4.0,
                        },
                        {
                            "type": "grommet",
                            "shape": "circular",
                            "x": 6.0,
                            "y": 12.0,
                            "diameter": 2.5,
                        },
                    ],
                },
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        # Verify cutout information appears in output
        assert "Outlet" in output
        assert "Grommet" in output

    def test_cut_list_shows_ventilation_pattern(self) -> None:
        """Cut list includes ventilation pattern information."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=24.0,
                height=72.0,
                quantity=1,
                label="Back Panel",
                panel_type=PanelType.BACK,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "ventilation",
                            "shape": "rectangular",
                            "pattern": "grid",
                            "x": 12.0,
                            "y": 12.0,
                            "width": 6.0,
                            "height": 4.0,
                        },
                    ],
                },
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        # Verify ventilation pattern appears in output
        assert "Ventilation" in output
        assert "grid" in output.lower()

    def test_cut_list_with_mixed_infrastructure(self) -> None:
        """Cut list handles mix of lighting, outlets, grommets, ventilation."""
        material = MaterialSpec(thickness=0.75)
        pieces = [
            CutPiece(
                width=24.0,
                height=72.0,
                quantity=1,
                label="Back Panel Section 1",
                panel_type=PanelType.BACK,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "outlet",
                            "shape": "rectangular",
                            "x": 12.0,
                            "y": 36.0,
                            "width": 2.25,
                            "height": 4.0,
                        },
                    ],
                },
            ),
            CutPiece(
                width=24.0,
                height=72.0,
                quantity=1,
                label="Back Panel Section 2",
                panel_type=PanelType.BACK,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "grommet",
                            "shape": "circular",
                            "x": 12.0,
                            "y": 24.0,
                            "diameter": 2.5,
                        },
                        {
                            "type": "ventilation",
                            "shape": "rectangular",
                            "pattern": "slot",
                            "x": 12.0,
                            "y": 6.0,
                            "width": 8.0,
                            "height": 2.0,
                        },
                    ],
                },
            ),
            CutPiece(
                width=46.5,
                height=11.5,
                quantity=1,
                label="Bottom Panel",
                panel_type=PanelType.BOTTOM,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "puck_light",
                            "shape": "circular",
                            "x": 12.0,
                            "y": 6.0,
                            "diameter": 3.0,
                        },
                    ],
                },
            ),
        ]

        formatter = CutListFormatter()
        output = formatter.format(pieces)

        # Verify all infrastructure types appear
        assert "Outlet" in output
        assert "Grommet" in output
        assert "Ventilation" in output
        assert "Puck Light" in output


# =============================================================================
# Test 5: Hardware list includes grommets with SKUs
# =============================================================================


class TestHardwareListWithGrommets:
    """Tests for hardware list including grommets with proper SKUs."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_hardware_list_aggregates_same_size_grommets(
        self, component_context: ComponentContext
    ) -> None:
        """Same-size grommets are aggregated into single hardware item."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.5, "panel": "back", "position": {"x": 6.0, "y": 12.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 12.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 18.0, "y": 12.0}},
            ]
        }

        result = component.generate(config, component_context)

        # Should have exactly one hardware item for 2.5" grommets
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 1
        assert grommet_items[0].quantity == 3
        assert grommet_items[0].sku == "GRM-250-BLK"

    def test_hardware_list_separates_different_sizes(
        self, component_context: ComponentContext
    ) -> None:
        """Different grommet sizes are listed as separate hardware items."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 2.0, "panel": "back", "position": {"x": 6.0, "y": 12.0}},
                {"size": 2.5, "panel": "back", "position": {"x": 12.0, "y": 12.0}},
                {"size": 3.0, "panel": "back", "position": {"x": 18.0, "y": 12.0}},
            ]
        }

        result = component.generate(config, component_context)

        # Should have three hardware items, one per size
        grommet_items = [h for h in result.hardware if "Grommet" in h.name]
        assert len(grommet_items) == 3

        # Verify each size has correct SKU
        skus = {h.sku for h in grommet_items}
        assert skus == {"GRM-200-BLK", "GRM-250-BLK", "GRM-300-BLK"}


# =============================================================================
# Test 6: JSON export includes cutouts
# =============================================================================


class TestJsonExportWithCutouts:
    """Tests for JSON export including cutout information."""

    @pytest.fixture
    def cabinet_with_cutouts(self, simple_cabinet: Cabinet) -> Cabinet:
        """Return the simple cabinet fixture."""
        return simple_cabinet

    def test_json_export_includes_cutouts_array(
        self, cabinet_with_cutouts: Cabinet
    ) -> None:
        """JSON export includes cutouts array in piece data."""
        from cabinets.application.dtos import LayoutOutput

        material = MaterialSpec(thickness=0.75)
        cut_list = [
            CutPiece(
                width=24.0,
                height=72.0,
                quantity=1,
                label="Back Panel",
                panel_type=PanelType.BACK,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "outlet",
                            "shape": "rectangular",
                            "x": 12.0,
                            "y": 36.0,
                            "width": 4.25,
                            "height": 4.0,
                        },
                    ],
                },
            ),
        ]

        output = LayoutOutput(
            cabinet=cabinet_with_cutouts,
            cut_list=cut_list,
            material_estimates={},
            total_estimate=MaterialEstimate(
                total_area_sqin=1728.0,
                total_area_sqft=12.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
        )

        exporter = JsonExporter()
        json_str = exporter.export(output)
        data = json.loads(json_str)

        # Verify cutouts array exists in cut list piece
        assert "cut_list" in data
        assert len(data["cut_list"]) == 1
        piece = data["cut_list"][0]
        assert "cutouts" in piece

    def test_json_export_cutout_structure(
        self, cabinet_with_cutouts: Cabinet
    ) -> None:
        """JSON export has correct cutout structure."""
        from cabinets.application.dtos import LayoutOutput

        material = MaterialSpec(thickness=0.75)
        cut_list = [
            CutPiece(
                width=24.0,
                height=72.0,
                quantity=1,
                label="Back Panel",
                panel_type=PanelType.BACK,
                material=material,
                cut_metadata={
                    "cutouts": [
                        {
                            "type": "grommet",
                            "shape": "circular",
                            "x": 12.0,
                            "y": 24.0,
                            "diameter": 2.5,
                        },
                        {
                            "type": "outlet",
                            "shape": "rectangular",
                            "x": 6.0,
                            "y": 36.0,
                            "width": 2.25,
                            "height": 4.0,
                        },
                    ],
                },
            ),
        ]

        output = LayoutOutput(
            cabinet=cabinet_with_cutouts,
            cut_list=cut_list,
            material_estimates={},
            total_estimate=MaterialEstimate(
                total_area_sqin=1728.0,
                total_area_sqft=12.0,
                sheet_count_4x8=1,
                sheet_count_5x5=1,
                waste_percentage=0.15,
            ),
        )

        exporter = JsonExporter()
        json_str = exporter.export(output)
        data = json.loads(json_str)

        cutouts = data["cut_list"][0]["cutouts"]
        assert len(cutouts) == 2

        # Check circular cutout structure
        grommet_cutout = next(c for c in cutouts if c["type"] == "grommet")
        assert grommet_cutout["shape"] == "circular"
        assert grommet_cutout["diameter"] == 2.5
        assert grommet_cutout["position"] == {"x": 12.0, "y": 24.0}

        # Check rectangular cutout structure
        outlet_cutout = next(c for c in cutouts if c["type"] == "outlet")
        assert outlet_cutout["shape"] == "rectangular"
        assert outlet_cutout["dimensions"] == {"width": 2.25, "height": 4.0}
        assert outlet_cutout["position"] == {"x": 6.0, "y": 36.0}


# =============================================================================
# Test 7: Validation errors for invalid configs
# =============================================================================


class TestInfrastructureValidationErrors:
    """Tests for validation errors with invalid infrastructure configs."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_outlet_out_of_bounds_error(
        self, component_context: ComponentContext
    ) -> None:
        """Outlet position out of panel bounds generates error."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "single",
            "panel": "back",
            "position": {"x": 0.5, "y": 36.0},  # Too close to left edge
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("edge" in err.lower() for err in result.errors)

    def test_outlet_position_too_close_to_right_edge(
        self, component_context: ComponentContext
    ) -> None:
        """Outlet too close to right edge generates error."""
        component = ElectricalComponent()
        config = {
            "outlet_type": "double",
            "panel": "back",
            "position": {"x": 22.0, "y": 36.0},  # Too close to right (24" panel, 4.25" outlet)
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("edge" in err.lower() for err in result.errors)

    def test_grommet_invalid_size_error(
        self, component_context: ComponentContext
    ) -> None:
        """Grommet with invalid size generates error."""
        component = CableManagementComponent()
        config = {
            "grommets": [
                {"size": 1.5, "panel": "back", "position": {"x": 12.0, "y": 36.0}},
            ]
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("size" in err.lower() for err in result.errors)

    def test_ventilation_out_of_bounds_error(
        self, component_context: ComponentContext
    ) -> None:
        """Ventilation area out of bounds generates error."""
        component = VentilationComponent()
        config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 2.0, "y": 36.0},  # Too close to left edge for 8" width
            "width": 8.0,
            "height": 4.0,
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("edge" in err.lower() for err in result.errors)

    def test_lighting_invalid_type_error(
        self, component_context: ComponentContext
    ) -> None:
        """Invalid lighting type generates error."""
        component = LightingComponent()
        config = {
            "light_type": "invalid_type",
            "location": "under_cabinet",
            "section_indices": [0],
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("light_type" in err.lower() for err in result.errors)

    def test_lighting_missing_length_for_led_strip(
        self, component_context: ComponentContext
    ) -> None:
        """LED strip without length generates error."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [0],
            # length is missing
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("length" in err.lower() for err in result.errors)

    def test_section_index_negative_error(
        self, component_context: ComponentContext
    ) -> None:
        """Negative section index generates error."""
        component = LightingComponent()
        config = {
            "light_type": "led_strip",
            "location": "under_cabinet",
            "section_indices": [-1],
            "length": 24.0,
        }

        result = component.validate(config, component_context)

        assert not result.is_valid
        assert any("negative" in err.lower() for err in result.errors)


# =============================================================================
# Test 8: Backward compatibility
# =============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility with older schema versions."""

    def test_config_without_infrastructure_works(self) -> None:
        """Configuration without infrastructure section still works."""
        config_json = """
        {
            "schema_version": "1.0",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {"width": 24.0, "shelves": 3},
                    {"width": "fill", "shelves": 5}
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        assert config.infrastructure is None
        assert config.cabinet.width == 48.0
        assert len(config.cabinet.sections) == 2

    def test_schema_version_10_supported(self) -> None:
        """Schema version 1.0 is supported."""
        config = CabinetConfiguration(
            schema_version="1.0",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
        )
        assert config.schema_version == "1.0"
        assert config.infrastructure is None

    def test_schema_version_11_supported(self) -> None:
        """Schema version 1.1 is supported."""
        config = CabinetConfiguration(
            schema_version="1.1",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
        )
        assert config.schema_version == "1.1"

    def test_schema_version_12_supported(self) -> None:
        """Schema version 1.2 is supported."""
        config = CabinetConfiguration(
            schema_version="1.2",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
        )
        assert config.schema_version == "1.2"

    def test_schema_version_13_supported(self) -> None:
        """Schema version 1.3 is supported."""
        config = CabinetConfiguration(
            schema_version="1.3",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
        )
        assert config.schema_version == "1.3"

    def test_schema_version_14_supported(self) -> None:
        """Schema version 1.4 is supported."""
        config = CabinetConfiguration(
            schema_version="1.4",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
        )
        assert config.schema_version == "1.4"

    def test_schema_version_15_supported(self) -> None:
        """Schema version 1.5 is supported."""
        config = CabinetConfiguration(
            schema_version="1.5",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
        )
        assert config.schema_version == "1.5"

    def test_schema_version_16_with_infrastructure(self) -> None:
        """Schema version 1.6 supports infrastructure section."""
        config = CabinetConfiguration(
            schema_version="1.6",
            cabinet=CabinetConfig(
                width=48.0,
                height=84.0,
                depth=12.0,
            ),
            infrastructure=InfrastructureConfigSchema(
                grommets=[
                    GrommetConfigSchema(
                        size=2.5,
                        panel="back",
                        position=PositionConfigSchema(x=12.0, y=36.0),
                    ),
                ],
            ),
        )
        assert config.schema_version == "1.6"
        assert config.infrastructure is not None
        assert len(config.infrastructure.grommets) == 1


# =============================================================================
# Configuration Parsing Tests
# =============================================================================


class TestInfrastructureConfigParsing:
    """Tests for parsing infrastructure configuration from JSON."""

    def test_parse_lighting_config(self) -> None:
        """Parse cabinet config with lighting."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            },
            "infrastructure": {
                "lighting": [
                    {
                        "type": "led_strip",
                        "location": "under_cabinet",
                        "section_indices": [0, 1],
                        "length": 48.0
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        assert config.infrastructure is not None
        assert len(config.infrastructure.lighting) == 1
        lighting = config.infrastructure.lighting[0]
        assert lighting.type == LightingTypeConfig.LED_STRIP
        assert lighting.location == LightingLocationConfig.UNDER_CABINET
        assert lighting.section_indices == [0, 1]
        assert lighting.length == 48.0

    def test_parse_outlet_config(self) -> None:
        """Parse cabinet config with outlets."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            },
            "infrastructure": {
                "outlets": [
                    {
                        "type": "double",
                        "section_index": 0,
                        "panel": "back",
                        "position": {"x": 12.0, "y": 36.0},
                        "conduit_direction": "bottom"
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        assert config.infrastructure is not None
        assert len(config.infrastructure.outlets) == 1
        outlet = config.infrastructure.outlets[0]
        assert outlet.type == OutletTypeConfig.DOUBLE
        assert outlet.section_index == 0
        assert outlet.panel == "back"
        assert outlet.position.x == 12.0
        assert outlet.position.y == 36.0

    def test_parse_grommet_config(self) -> None:
        """Parse cabinet config with grommets."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            },
            "infrastructure": {
                "grommets": [
                    {
                        "size": 2.5,
                        "panel": "back",
                        "position": {"x": 12.0, "y": 36.0},
                        "section_index": 0
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        assert config.infrastructure is not None
        assert len(config.infrastructure.grommets) == 1
        grommet = config.infrastructure.grommets[0]
        assert grommet.size == 2.5
        assert grommet.panel == "back"
        assert grommet.section_index == 0

    def test_parse_ventilation_config(self) -> None:
        """Parse cabinet config with ventilation."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            },
            "infrastructure": {
                "ventilation": [
                    {
                        "pattern": "grid",
                        "panel": "back",
                        "position": {"x": 24.0, "y": 12.0},
                        "width": 6.0,
                        "height": 4.0,
                        "hole_size": 0.25
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        assert config.infrastructure is not None
        assert len(config.infrastructure.ventilation) == 1
        vent = config.infrastructure.ventilation[0]
        assert vent.pattern == VentilationPatternConfig.GRID
        assert vent.panel == "back"
        assert vent.width == 6.0
        assert vent.height == 4.0

    def test_parse_full_infrastructure_config(self) -> None:
        """Parse cabinet with all infrastructure elements."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0,
                "sections": [
                    {"width": 24.0, "shelves": 3},
                    {"width": "fill", "shelves": 5}
                ]
            },
            "infrastructure": {
                "lighting": [
                    {
                        "type": "puck_light",
                        "location": "in_cabinet",
                        "section_indices": [0],
                        "diameter": 3.0
                    }
                ],
                "outlets": [
                    {
                        "type": "single",
                        "section_index": 1,
                        "panel": "back",
                        "position": {"x": 6.0, "y": 12.0}
                    }
                ],
                "grommets": [
                    {
                        "size": 2.5,
                        "panel": "back",
                        "position": {"x": 12.0, "y": 36.0},
                        "section_index": 0
                    }
                ],
                "ventilation": [
                    {
                        "pattern": "grid",
                        "panel": "back",
                        "position": {"x": 24.0, "y": 12.0},
                        "width": 6.0,
                        "height": 4.0
                    }
                ]
            },
            "output": {"format": "all"}
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)

        # Verify all infrastructure elements parsed
        assert config.infrastructure is not None
        assert len(config.infrastructure.lighting) == 1
        assert len(config.infrastructure.outlets) == 1
        assert len(config.infrastructure.grommets) == 1
        assert len(config.infrastructure.ventilation) == 1

        # Verify cabinet sections
        assert len(config.cabinet.sections) == 2


# =============================================================================
# LED Strip Validation Tests
# =============================================================================


class TestLedStripValidation:
    """Tests for LED strip length validation."""

    def test_led_strip_requires_length(self) -> None:
        """LED strip configuration requires length."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            },
            "infrastructure": {
                "lighting": [
                    {
                        "type": "led_strip",
                        "location": "under_cabinet",
                        "section_indices": [0]
                    }
                ]
            }
        }
        """
        with pytest.raises(ValidationError):
            CabinetConfiguration.model_validate_json(config_json)

    def test_led_strip_with_length_validates(self) -> None:
        """LED strip with length passes validation."""
        config_json = """
        {
            "schema_version": "1.6",
            "cabinet": {
                "width": 48.0,
                "height": 84.0,
                "depth": 12.0
            },
            "infrastructure": {
                "lighting": [
                    {
                        "type": "led_strip",
                        "location": "under_cabinet",
                        "section_indices": [0],
                        "length": 24.0
                    }
                ]
            }
        }
        """
        config = CabinetConfiguration.model_validate_json(config_json)
        assert config.infrastructure.lighting[0].length == 24.0


# =============================================================================
# Puck Light Generation Tests
# =============================================================================


class TestPuckLightGeneration:
    """Tests for puck light cutout generation."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_puck_light_generates_hardware(
        self, component_context: ComponentContext
    ) -> None:
        """Puck lights generate appropriate hardware items."""
        component = LightingComponent()
        config = {
            "light_type": "puck_light",
            "location": "in_cabinet",
            "section_indices": [0],
            "puck_diameter": 2.5,
            "puck_positions": [
                {"x": 8.0, "y": 4.0},
                {"x": 16.0, "y": 4.0},
            ],
        }

        result = component.generate(config, component_context)

        # Verify puck light hardware (excludes wire harness)
        puck_items = [h for h in result.hardware if "Puck Light (" in h.name]
        assert len(puck_items) == 1
        assert puck_items[0].quantity == 2

        # Verify wire harness
        harness_items = [h for h in result.hardware if "Harness" in h.name]
        assert len(harness_items) == 1


# =============================================================================
# Ventilation Pattern Tests
# =============================================================================


class TestVentilationPatterns:
    """Tests for ventilation pattern generation."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_grid_pattern_generates_hole_count(
        self, component_context: ComponentContext
    ) -> None:
        """Grid pattern generates appropriate hole count metadata."""
        component = VentilationComponent()
        config = {
            "pattern": "grid",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
            "width": 4.0,
            "height": 2.0,
            "hole_size": 0.25,
        }

        result = component.generate(config, component_context)

        assert "ventilation_spec" in result.metadata
        spec = result.metadata["ventilation_spec"]
        assert spec["pattern"] == "grid"
        assert spec["hole_count"] > 0

    def test_slot_pattern_validates(
        self, component_context: ComponentContext
    ) -> None:
        """Slot pattern configuration validates."""
        component = VentilationComponent()
        config = {
            "pattern": "slot",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
            "width": 6.0,
            "height": 3.0,
        }

        result = component.validate(config, component_context)
        assert result.is_valid

    def test_circular_pattern_validates(
        self, component_context: ComponentContext
    ) -> None:
        """Circular pattern configuration validates."""
        component = VentilationComponent()
        config = {
            "pattern": "circular",
            "panel": "back",
            "position": {"x": 12.0, "y": 36.0},
            "width": 4.0,
            "height": 4.0,
        }

        result = component.validate(config, component_context)
        assert result.is_valid


# =============================================================================
# Component Registration Tests
# =============================================================================


class TestInfrastructureComponentRegistration:
    """Tests for infrastructure component registration."""

    @pytest.fixture(autouse=True)
    def setup(self, ensure_infrastructure_registered: None) -> None:
        """Ensure registry is set up before each test."""
        pass

    def test_lighting_component_registered(self) -> None:
        """Lighting component is registered in registry."""
        assert "infrastructure.lighting" in component_registry.list()

    def test_electrical_component_registered(self) -> None:
        """Electrical component is registered in registry."""
        assert "infrastructure.electrical" in component_registry.list()

    def test_cable_management_component_registered(self) -> None:
        """Cable management component is registered in registry."""
        assert "infrastructure.cable_management" in component_registry.list()

    def test_ventilation_component_registered(self) -> None:
        """Ventilation component is registered in registry."""
        assert "infrastructure.ventilation" in component_registry.list()

    def test_components_retrievable_from_registry(self) -> None:
        """Infrastructure components can be retrieved from registry."""
        lighting_class = component_registry.get("infrastructure.lighting")
        assert lighting_class == LightingComponent

        electrical_class = component_registry.get("infrastructure.electrical")
        assert electrical_class == ElectricalComponent

        cable_class = component_registry.get("infrastructure.cable_management")
        assert cable_class == CableManagementComponent

        vent_class = component_registry.get("infrastructure.ventilation")
        assert vent_class == VentilationComponent
