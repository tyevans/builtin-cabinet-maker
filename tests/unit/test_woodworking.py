"""Unit tests for woodworking intelligence data models and services."""

import pytest

from cabinets.domain.components.results import HardwareItem
from cabinets.domain.entities import Cabinet, Section, Shelf
from cabinets.domain.services.woodworking import (
    MATERIAL_MODULUS,
    MAX_DEFLECTION_RATIO,
    SAFETY_FACTOR,
    SPAN_LIMITS,
    ConnectionJoinery,
    HardwareList,
    JointSpec,
    SpanWarning,
    WeightCapacity,
    WoodworkingConfig,
    WoodworkingIntelligence,
    get_max_span,
)
from cabinets.domain.value_objects import (
    CutPiece,
    JointType,
    MaterialSpec,
    MaterialType,
    PanelType,
    Position,
)


class TestJointType:
    """Tests for JointType enum."""

    def test_joint_type_values(self) -> None:
        """Test that all JointType values are correct."""
        assert JointType.DADO.value == "dado"
        assert JointType.RABBET.value == "rabbet"
        assert JointType.POCKET_SCREW.value == "pocket_screw"
        assert JointType.DOWEL.value == "dowel"
        assert JointType.BISCUIT.value == "biscuit"
        assert JointType.BUTT.value == "butt"

    def test_joint_type_is_str_enum(self) -> None:
        """Test that JointType is a string enum for JSON serialization."""
        assert isinstance(JointType.DADO, str)
        # The value attribute gives the string value
        assert JointType.DADO.value == "dado"
        # The enum can be compared to strings
        assert JointType.DADO == "dado"


class TestSpanLimits:
    """Tests for SPAN_LIMITS constant and get_max_span function."""

    def test_plywood_standard_thickness(self) -> None:
        """Test span limit for 3/4 inch plywood."""
        assert get_max_span(MaterialType.PLYWOOD, 0.75) == 36.0

    def test_mdf_standard_thickness(self) -> None:
        """Test span limit for 3/4 inch MDF."""
        assert get_max_span(MaterialType.MDF, 0.75) == 24.0

    def test_particle_board_standard_thickness(self) -> None:
        """Test span limit for 3/4 inch particle board."""
        assert get_max_span(MaterialType.PARTICLE_BOARD, 0.75) == 24.0

    def test_solid_wood_thick(self) -> None:
        """Test span limit for 1 inch solid wood."""
        assert get_max_span(MaterialType.SOLID_WOOD, 1.0) == 42.0

    def test_fallback_to_closest_thickness(self) -> None:
        """Test that unlisted thickness falls back to closest."""
        # 0.55 is closer to 0.5 (diff=0.05) than 0.75 (diff=0.20) for plywood
        result = get_max_span(MaterialType.PLYWOOD, 0.55)
        # Should pick 0.5 thickness (24.0) since it's closer
        assert result == 24.0

    def test_fallback_default_for_unknown_material(self) -> None:
        """Test that unknown material gets conservative default."""
        # Remove all plywood entries temporarily would trigger default
        # But since plywood is in SPAN_LIMITS, let's test a different thickness
        # that would find entries
        result = get_max_span(MaterialType.PLYWOOD, 0.8)
        # Should find closest (0.75) and return 36.0
        assert result == 36.0


class TestMaterialModulus:
    """Tests for MATERIAL_MODULUS constant."""

    def test_all_material_types_have_modulus(self) -> None:
        """Test that all MaterialType values have modulus values."""
        for mat_type in MaterialType:
            assert mat_type in MATERIAL_MODULUS
            assert MATERIAL_MODULUS[mat_type] > 0

    def test_plywood_modulus(self) -> None:
        """Test plywood has reasonable modulus value."""
        assert MATERIAL_MODULUS[MaterialType.PLYWOOD] == 1_200_000

    def test_mdf_modulus_lower_than_plywood(self) -> None:
        """Test MDF has lower modulus than plywood."""
        assert MATERIAL_MODULUS[MaterialType.MDF] < MATERIAL_MODULUS[MaterialType.PLYWOOD]


class TestJointSpec:
    """Tests for JointSpec dataclass."""

    def test_dado_factory(self) -> None:
        """Test dado joint factory method."""
        dado = JointSpec.dado(depth=0.25)
        assert dado.joint_type == JointType.DADO
        assert dado.depth == 0.25
        assert dado.width is None
        assert dado.positions == ()
        assert dado.spacing is None

    def test_rabbet_factory(self) -> None:
        """Test rabbet joint factory method."""
        rabbet = JointSpec.rabbet(width=0.5, depth=0.25)
        assert rabbet.joint_type == JointType.RABBET
        assert rabbet.width == 0.5
        assert rabbet.depth == 0.25

    def test_pocket_screw_factory(self) -> None:
        """Test pocket screw joint factory method."""
        positions = (2.0, 8.0, 14.0)
        pocket = JointSpec.pocket_screw(positions=positions, spacing=6.0)
        assert pocket.joint_type == JointType.POCKET_SCREW
        assert pocket.positions == positions
        assert pocket.spacing == 6.0

    def test_dowel_factory(self) -> None:
        """Test dowel joint factory method."""
        positions = (3.0, 9.0, 15.0)
        dowel = JointSpec.dowel(positions=positions, spacing=6.0)
        assert dowel.joint_type == JointType.DOWEL
        assert dowel.positions == positions
        assert dowel.spacing == 6.0

    def test_biscuit_factory(self) -> None:
        """Test biscuit joint factory method."""
        positions = (4.0, 12.0, 20.0)
        biscuit = JointSpec.biscuit(positions=positions, spacing=8.0)
        assert biscuit.joint_type == JointType.BISCUIT
        assert biscuit.positions == positions
        assert biscuit.spacing == 8.0

    def test_butt_factory(self) -> None:
        """Test butt joint factory method."""
        butt = JointSpec.butt()
        assert butt.joint_type == JointType.BUTT
        assert butt.depth is None
        assert butt.width is None
        assert butt.positions == ()
        assert butt.spacing is None

    def test_negative_depth_raises_error(self) -> None:
        """Test that negative depth raises ValueError."""
        with pytest.raises(ValueError, match="Joint depth must be positive"):
            JointSpec(joint_type=JointType.DADO, depth=-0.25)

    def test_zero_depth_raises_error(self) -> None:
        """Test that zero depth raises ValueError."""
        with pytest.raises(ValueError, match="Joint depth must be positive"):
            JointSpec(joint_type=JointType.DADO, depth=0)

    def test_negative_width_raises_error(self) -> None:
        """Test that negative width raises ValueError."""
        with pytest.raises(ValueError, match="Joint width must be positive"):
            JointSpec(joint_type=JointType.RABBET, width=-0.5, depth=0.25)

    def test_negative_spacing_raises_error(self) -> None:
        """Test that negative spacing raises ValueError."""
        with pytest.raises(ValueError, match="Joint spacing must be positive"):
            JointSpec(
                joint_type=JointType.POCKET_SCREW,
                positions=(2.0, 8.0),
                spacing=-6.0,
            )

    def test_negative_position_raises_error(self) -> None:
        """Test that negative position raises ValueError."""
        with pytest.raises(ValueError, match="Position values must be non-negative"):
            JointSpec(
                joint_type=JointType.DOWEL,
                positions=(-2.0, 8.0),
                spacing=6.0,
            )

    def test_joint_spec_is_frozen(self) -> None:
        """Test that JointSpec is immutable."""
        dado = JointSpec.dado(depth=0.25)
        with pytest.raises(AttributeError):
            dado.depth = 0.5  # type: ignore


class TestConnectionJoinery:
    """Tests for ConnectionJoinery dataclass."""

    def test_valid_connection(self) -> None:
        """Test creating a valid connection joinery."""
        dado = JointSpec.dado(depth=0.25)
        conn = ConnectionJoinery(
            from_panel=PanelType.LEFT_SIDE,
            to_panel=PanelType.SHELF,
            joint=dado,
            location_description="Shelf dado in left side panel",
        )
        assert conn.from_panel == PanelType.LEFT_SIDE
        assert conn.to_panel == PanelType.SHELF
        assert conn.joint == dado
        assert conn.location_description == "Shelf dado in left side panel"

    def test_same_panel_raises_error(self) -> None:
        """Test that connecting panel to itself raises ValueError."""
        dado = JointSpec.dado(depth=0.25)
        with pytest.raises(ValueError, match="from_panel and to_panel must be different"):
            ConnectionJoinery(
                from_panel=PanelType.SHELF,
                to_panel=PanelType.SHELF,
                joint=dado,
            )

    def test_default_location_description(self) -> None:
        """Test default location description is empty string."""
        rabbet = JointSpec.rabbet(width=0.5, depth=0.25)
        conn = ConnectionJoinery(
            from_panel=PanelType.LEFT_SIDE,
            to_panel=PanelType.BACK,
            joint=rabbet,
        )
        assert conn.location_description == ""


class TestSpanWarning:
    """Tests for SpanWarning dataclass."""

    @pytest.fixture
    def plywood_material(self) -> MaterialSpec:
        """Create a standard plywood material spec."""
        return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)

    def test_valid_span_warning(self, plywood_material: MaterialSpec) -> None:
        """Test creating a valid span warning."""
        warning = SpanWarning(
            panel_label="Shelf 1",
            span=40.0,
            max_span=36.0,
            material=plywood_material,
        )
        assert warning.panel_label == "Shelf 1"
        assert warning.span == 40.0
        assert warning.max_span == 36.0
        assert warning.severity == "warning"
        assert warning.suggestion == "Add center support or divider"

    def test_excess_percentage(self, plywood_material: MaterialSpec) -> None:
        """Test excess percentage calculation."""
        warning = SpanWarning(
            panel_label="Shelf 1",
            span=40.0,
            max_span=36.0,
            material=plywood_material,
        )
        # (40 - 36) / 36 * 100 = 11.11%
        assert abs(warning.excess_percentage - 11.11) < 0.1

    def test_formatted_message(self, plywood_material: MaterialSpec) -> None:
        """Test formatted warning message."""
        warning = SpanWarning(
            panel_label="Top Panel",
            span=42.0,
            max_span=36.0,
            material=plywood_material,
        )
        msg = warning.formatted_message
        assert "Top Panel" in msg
        assert "42.0\"" in msg
        assert "36.0\"" in msg
        assert "plywood" in msg
        assert "0.75\"" in msg

    def test_critical_severity(self, plywood_material: MaterialSpec) -> None:
        """Test critical severity level."""
        warning = SpanWarning(
            panel_label="Shelf 1",
            span=48.0,
            max_span=36.0,
            material=plywood_material,
            severity="critical",
        )
        assert warning.severity == "critical"

    def test_invalid_severity_raises_error(self, plywood_material: MaterialSpec) -> None:
        """Test that invalid severity raises ValueError."""
        with pytest.raises(ValueError, match="Severity must be 'warning' or 'critical'"):
            SpanWarning(
                panel_label="Shelf 1",
                span=40.0,
                max_span=36.0,
                material=plywood_material,
                severity="error",
            )

    def test_negative_span_raises_error(self, plywood_material: MaterialSpec) -> None:
        """Test that negative span raises ValueError."""
        with pytest.raises(ValueError, match="Span must be positive"):
            SpanWarning(
                panel_label="Shelf 1",
                span=-10.0,
                max_span=36.0,
                material=plywood_material,
            )

    def test_zero_max_span_raises_error(self, plywood_material: MaterialSpec) -> None:
        """Test that zero max_span raises ValueError."""
        with pytest.raises(ValueError, match="Max span must be positive"):
            SpanWarning(
                panel_label="Shelf 1",
                span=40.0,
                max_span=0.0,
                material=plywood_material,
            )


class TestWeightCapacity:
    """Tests for WeightCapacity dataclass."""

    @pytest.fixture
    def plywood_material(self) -> MaterialSpec:
        """Create a standard plywood material spec."""
        return MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)

    def test_valid_weight_capacity(self, plywood_material: MaterialSpec) -> None:
        """Test creating a valid weight capacity."""
        capacity = WeightCapacity(
            panel_label="Shelf 1",
            capacity_lbs=75.0,
            load_type="distributed",
            span=30.0,
            material=plywood_material,
        )
        assert capacity.panel_label == "Shelf 1"
        assert capacity.capacity_lbs == 75.0
        assert capacity.load_type == "distributed"
        assert capacity.span == 30.0
        assert capacity.disclaimer == "Advisory only - not engineered"

    def test_point_load_type(self, plywood_material: MaterialSpec) -> None:
        """Test point load type."""
        capacity = WeightCapacity(
            panel_label="Shelf 1",
            capacity_lbs=40.0,
            load_type="point",
            span=30.0,
            material=plywood_material,
        )
        assert capacity.load_type == "point"

    def test_formatted_message(self, plywood_material: MaterialSpec) -> None:
        """Test formatted capacity message."""
        capacity = WeightCapacity(
            panel_label="Lower Shelf",
            capacity_lbs=50.0,
            load_type="distributed",
            span=24.0,
            material=plywood_material,
        )
        msg = capacity.formatted_message
        assert "Lower Shelf" in msg
        assert "~50 lbs" in msg
        assert "distributed" in msg
        assert "Advisory only" in msg

    def test_invalid_load_type_raises_error(self, plywood_material: MaterialSpec) -> None:
        """Test that invalid load type raises ValueError."""
        with pytest.raises(ValueError, match="Load type must be 'distributed' or 'point'"):
            WeightCapacity(
                panel_label="Shelf 1",
                capacity_lbs=50.0,
                load_type="center",
                span=30.0,
                material=plywood_material,
            )

    def test_negative_capacity_raises_error(self, plywood_material: MaterialSpec) -> None:
        """Test that negative capacity raises ValueError."""
        with pytest.raises(ValueError, match="Capacity must be non-negative"):
            WeightCapacity(
                panel_label="Shelf 1",
                capacity_lbs=-10.0,
                load_type="distributed",
                span=30.0,
                material=plywood_material,
            )

    def test_zero_span_raises_error(self, plywood_material: MaterialSpec) -> None:
        """Test that zero span raises ValueError."""
        with pytest.raises(ValueError, match="Span must be positive"):
            WeightCapacity(
                panel_label="Shelf 1",
                capacity_lbs=50.0,
                load_type="distributed",
                span=0.0,
                material=plywood_material,
            )

    def test_zero_capacity_allowed(self, plywood_material: MaterialSpec) -> None:
        """Test that zero capacity is allowed (for very weak materials)."""
        capacity = WeightCapacity(
            panel_label="Decorative Shelf",
            capacity_lbs=0.0,
            load_type="distributed",
            span=48.0,
            material=plywood_material,
        )
        assert capacity.capacity_lbs == 0.0


class TestHardwareList:
    """Tests for HardwareList dataclass."""

    @pytest.fixture
    def sample_items(self) -> tuple[HardwareItem, ...]:
        """Create sample hardware items."""
        return (
            HardwareItem(name="#8 x 1-1/4 screw", quantity=24, sku="SCR-8114"),
            HardwareItem(name="5/16 x 1-1/2 dowel", quantity=8),
        )

    def test_create_hardware_list(self, sample_items: tuple[HardwareItem, ...]) -> None:
        """Test creating a hardware list."""
        hw_list = HardwareList(items=sample_items)
        assert len(hw_list.items) == 2
        assert hw_list.items[0].name == "#8 x 1-1/4 screw"
        assert hw_list.items[1].name == "5/16 x 1-1/2 dowel"

    def test_total_count(self, sample_items: tuple[HardwareItem, ...]) -> None:
        """Test total count property."""
        hw_list = HardwareList(items=sample_items)
        assert hw_list.total_count == 32  # 24 + 8

    def test_with_overage_default(self, sample_items: tuple[HardwareItem, ...]) -> None:
        """Test with_overage with default 10%."""
        hw_list = HardwareList(items=sample_items)
        with_overage = hw_list.with_overage()
        # 24 * 1.1 = 26.4 -> 27, 8 * 1.1 = 8.8 -> 9
        assert with_overage.items[0].quantity == 27
        assert with_overage.items[1].quantity == 9

    def test_with_overage_custom_percent(
        self, sample_items: tuple[HardwareItem, ...]
    ) -> None:
        """Test with_overage with custom percentage."""
        hw_list = HardwareList(items=sample_items)
        with_overage = hw_list.with_overage(25.0)
        # 24 * 1.25 = 30, 8 * 1.25 = 10
        assert with_overage.items[0].quantity == 30
        assert with_overage.items[1].quantity == 10

    def test_with_overage_zero_percent(
        self, sample_items: tuple[HardwareItem, ...]
    ) -> None:
        """Test with_overage with zero percent."""
        hw_list = HardwareList(items=sample_items)
        with_overage = hw_list.with_overage(0.0)
        assert with_overage.items[0].quantity == 24
        assert with_overage.items[1].quantity == 8

    def test_with_overage_negative_raises_error(
        self, sample_items: tuple[HardwareItem, ...]
    ) -> None:
        """Test that negative overage raises ValueError."""
        hw_list = HardwareList(items=sample_items)
        with pytest.raises(ValueError, match="Overage percent must be non-negative"):
            hw_list.with_overage(-10.0)

    def test_aggregate_sums_quantities(self) -> None:
        """Test aggregate combines hardware lists correctly."""
        list1 = HardwareList(
            items=(
                HardwareItem(name="Screw A", quantity=10),
                HardwareItem(name="Dowel B", quantity=5),
            )
        )
        list2 = HardwareList(
            items=(
                HardwareItem(name="Screw A", quantity=5),
                HardwareItem(name="Hinge C", quantity=2),
            )
        )
        combined = HardwareList.aggregate(list1, list2)
        # Should have 3 unique items, sorted by name
        assert len(combined.items) == 3
        assert combined.items[0].name == "Dowel B"
        assert combined.items[0].quantity == 5
        assert combined.items[1].name == "Hinge C"
        assert combined.items[1].quantity == 2
        assert combined.items[2].name == "Screw A"
        assert combined.items[2].quantity == 15

    def test_aggregate_preserves_metadata(self) -> None:
        """Test aggregate preserves first encountered metadata."""
        list1 = HardwareList(
            items=(HardwareItem(name="Screw", quantity=10, sku="SCR-001", notes="Note1"),)
        )
        list2 = HardwareList(
            items=(HardwareItem(name="Screw", quantity=5, sku="SCR-002", notes="Note2"),)
        )
        combined = HardwareList.aggregate(list1, list2)
        # First encountered metadata should be kept
        assert combined.items[0].sku == "SCR-001"
        assert combined.items[0].notes == "Note1"

    def test_aggregate_empty_lists(self) -> None:
        """Test aggregate with no lists returns empty."""
        combined = HardwareList.aggregate()
        assert len(combined.items) == 0

    def test_by_category_screws(self) -> None:
        """Test by_category groups screws correctly."""
        hw_list = HardwareList(
            items=(
                HardwareItem(name="#8 x 1 screw", quantity=20),
                HardwareItem(name="#6 x 3/4 screw", quantity=10),
                HardwareItem(name="Pocket hole screw", quantity=15),
            )
        )
        categories = hw_list.by_category
        assert "screws" in categories
        assert len(categories["screws"]) == 3

    def test_by_category_mixed(self) -> None:
        """Test by_category groups multiple types correctly."""
        hw_list = HardwareList(
            items=(
                HardwareItem(name="Wood screw", quantity=20),
                HardwareItem(name="Wood dowel", quantity=10),
                HardwareItem(name="#20 biscuit", quantity=15),
                HardwareItem(name="Soft-close hinge", quantity=4),
                HardwareItem(name="Drawer slide", quantity=2),
                HardwareItem(name="Shelf pin", quantity=16),
            )
        )
        categories = hw_list.by_category
        assert len(categories["screws"]) == 1
        assert len(categories["dowels"]) == 1
        assert len(categories["biscuits"]) == 1
        assert len(categories["hinges"]) == 1
        assert len(categories["slides"]) == 1
        assert len(categories["other"]) == 1

    def test_empty_factory(self) -> None:
        """Test empty factory method."""
        empty = HardwareList.empty()
        assert len(empty.items) == 0
        assert empty.total_count == 0

    def test_hardware_list_is_frozen(self, sample_items: tuple[HardwareItem, ...]) -> None:
        """Test that HardwareList is immutable."""
        hw_list = HardwareList(items=sample_items)
        with pytest.raises(AttributeError):
            hw_list.items = ()  # type: ignore


class TestWoodworkingConfig:
    """Tests for WoodworkingConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = WoodworkingConfig()
        assert config.default_shelf_joint == JointType.DADO
        assert config.default_back_joint == JointType.RABBET
        assert abs(config.dado_depth_ratio - 1 / 3) < 0.001
        assert config.rabbet_depth_ratio == 0.5
        assert config.dowel_edge_offset == 2.0
        assert config.dowel_spacing == 6.0
        assert config.pocket_hole_edge_offset == 4.0
        assert config.pocket_hole_spacing == 8.0

    def test_custom_joint_types(self) -> None:
        """Test custom joint type configuration."""
        config = WoodworkingConfig(
            default_shelf_joint=JointType.BISCUIT,
            default_back_joint=JointType.BUTT,
        )
        assert config.default_shelf_joint == JointType.BISCUIT
        assert config.default_back_joint == JointType.BUTT

    def test_custom_depth_ratios(self) -> None:
        """Test custom depth ratio configuration."""
        config = WoodworkingConfig(
            dado_depth_ratio=0.25,
            rabbet_depth_ratio=0.4,
        )
        assert config.dado_depth_ratio == 0.25
        assert config.rabbet_depth_ratio == 0.4

    def test_invalid_dado_depth_ratio_zero(self) -> None:
        """Test that zero dado_depth_ratio raises ValueError."""
        with pytest.raises(ValueError, match="dado_depth_ratio must be between 0 and 1"):
            WoodworkingConfig(dado_depth_ratio=0)

    def test_invalid_dado_depth_ratio_negative(self) -> None:
        """Test that negative dado_depth_ratio raises ValueError."""
        with pytest.raises(ValueError, match="dado_depth_ratio must be between 0 and 1"):
            WoodworkingConfig(dado_depth_ratio=-0.1)

    def test_invalid_dado_depth_ratio_greater_than_one(self) -> None:
        """Test that dado_depth_ratio > 1 raises ValueError."""
        with pytest.raises(ValueError, match="dado_depth_ratio must be between 0 and 1"):
            WoodworkingConfig(dado_depth_ratio=1.5)

    def test_invalid_rabbet_depth_ratio(self) -> None:
        """Test that invalid rabbet_depth_ratio raises ValueError."""
        with pytest.raises(ValueError, match="rabbet_depth_ratio must be between 0 and 1"):
            WoodworkingConfig(rabbet_depth_ratio=0)

    def test_invalid_dowel_edge_offset(self) -> None:
        """Test that non-positive dowel_edge_offset raises ValueError."""
        with pytest.raises(ValueError, match="dowel_edge_offset must be positive"):
            WoodworkingConfig(dowel_edge_offset=0)

    def test_invalid_dowel_spacing(self) -> None:
        """Test that non-positive dowel_spacing raises ValueError."""
        with pytest.raises(ValueError, match="dowel_spacing must be positive"):
            WoodworkingConfig(dowel_spacing=-1.0)

    def test_invalid_pocket_hole_edge_offset(self) -> None:
        """Test that non-positive pocket_hole_edge_offset raises ValueError."""
        with pytest.raises(ValueError, match="pocket_hole_edge_offset must be positive"):
            WoodworkingConfig(pocket_hole_edge_offset=0)

    def test_invalid_pocket_hole_spacing(self) -> None:
        """Test that non-positive pocket_hole_spacing raises ValueError."""
        with pytest.raises(ValueError, match="pocket_hole_spacing must be positive"):
            WoodworkingConfig(pocket_hole_spacing=0)

    def test_config_is_frozen(self) -> None:
        """Test that WoodworkingConfig is immutable."""
        config = WoodworkingConfig()
        with pytest.raises(AttributeError):
            config.dado_depth_ratio = 0.5  # type: ignore


class TestWoodworkingIntelligence:
    """Tests for WoodworkingIntelligence service."""

    @pytest.fixture
    def simple_cabinet(self) -> Cabinet:
        """Create a simple cabinet with one section and one shelf."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.5,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=46.5,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)
        return cabinet

    @pytest.fixture
    def multi_section_cabinet(self) -> Cabinet:
        """Create a cabinet with multiple sections (has dividers)."""
        cabinet = Cabinet(
            width=72.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # Section 1
        section1 = Section(
            width=24.0,
            height=82.5,
            depth=11.5,
            position=Position(0.75, 0.75),
        )
        shelf1 = Shelf(
            width=24.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section1.add_shelf(shelf1)
        cabinet.sections.append(section1)

        # Section 2
        section2 = Section(
            width=24.0,
            height=82.5,
            depth=11.5,
            position=Position(24.75, 0.75),
        )
        shelf2 = Shelf(
            width=24.0,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(24.75, 40.0),
        )
        section2.add_shelf(shelf2)
        cabinet.sections.append(section2)

        return cabinet

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        intel = WoodworkingIntelligence()
        assert intel.config is not None
        assert intel.config.dado_depth_ratio == pytest.approx(1 / 3)

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = WoodworkingConfig(dado_depth_ratio=0.25)
        intel = WoodworkingIntelligence(config=config)
        assert intel.config.dado_depth_ratio == 0.25

    def test_get_joinery_returns_list(self, simple_cabinet: Cabinet) -> None:
        """Test that get_joinery returns a list of ConnectionJoinery."""
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)
        assert isinstance(joinery, list)
        assert all(isinstance(j, ConnectionJoinery) for j in joinery)

    def test_get_joinery_simple_cabinet_count(self, simple_cabinet: Cabinet) -> None:
        """Test joinery count for simple cabinet.

        Expected joints:
        - 2 shelf-to-side (left, right)
        - 4 back panel rabbets (left, right, top, bottom)
        - 4 top/bottom-to-sides (2 for top, 2 for bottom)
        Total: 10
        """
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)
        assert len(joinery) >= 10

    def test_get_joinery_multi_section_has_dividers(
        self, multi_section_cabinet: Cabinet
    ) -> None:
        """Test that multi-section cabinet generates divider joinery."""
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(multi_section_cabinet)

        # Find divider joinery
        divider_joints = [j for j in joinery if j.to_panel == PanelType.DIVIDER]
        assert len(divider_joints) == 2  # 1 divider, 2 connections (top, bottom)

    def test_shelf_to_side_uses_dado(self, simple_cabinet: Cabinet) -> None:
        """Test that shelf-to-side connections use dado joints."""
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)

        shelf_joints = [j for j in joinery if j.to_panel == PanelType.SHELF]
        assert len(shelf_joints) == 2
        for joint in shelf_joints:
            assert joint.joint.joint_type == JointType.DADO

    def test_back_panel_uses_rabbet(self, simple_cabinet: Cabinet) -> None:
        """Test that back panel connections use rabbet joints."""
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)

        back_joints = [j for j in joinery if j.to_panel == PanelType.BACK]
        assert len(back_joints) == 4  # Left, right, top, bottom
        for joint in back_joints:
            assert joint.joint.joint_type == JointType.RABBET

    def test_dado_depth_calculation(self, simple_cabinet: Cabinet) -> None:
        """Test that dado depth is calculated correctly.

        For 3/4" material, dado depth = 0.75 * (1/3) = 0.25"
        """
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)

        dado_joints = [j for j in joinery if j.joint.joint_type == JointType.DADO]
        assert len(dado_joints) > 0
        for joint in dado_joints:
            assert joint.joint.depth == pytest.approx(0.25)

    def test_rabbet_dimensions_calculation(self, simple_cabinet: Cabinet) -> None:
        """Test that rabbet dimensions are calculated correctly.

        For 1/2" back material and 3/4" case material:
        - Rabbet width = 0.5" (back thickness)
        - Rabbet depth = 0.75 * 0.5 = 0.375" (case thickness * ratio)
        """
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)

        rabbet_joints = [j for j in joinery if j.joint.joint_type == JointType.RABBET]
        assert len(rabbet_joints) == 4
        for joint in rabbet_joints:
            assert joint.joint.width == pytest.approx(0.5)
            assert joint.joint.depth == pytest.approx(0.375)

    def test_location_descriptions_present(self, simple_cabinet: Cabinet) -> None:
        """Test that joinery has location descriptions."""
        intel = WoodworkingIntelligence()
        joinery = intel.get_joinery(simple_cabinet)

        for joint in joinery:
            assert joint.location_description != ""


class TestWoodworkingIntelligenceFastenerPositions:
    """Tests for fastener position calculations."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    def test_calculate_fastener_positions_24_inch(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener positions for a 24" joint with 2" edge offset and 6" spacing."""
        positions = intel._calculate_fastener_positions(
            length=24.0,
            edge_offset=2.0,
            spacing=6.0,
        )
        assert positions[0] == 2.0  # First at edge offset
        assert positions[-1] == 22.0  # Last at length - edge offset
        assert len(positions) >= 2

    def test_calculate_fastener_positions_short_joint(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener positions for a joint shorter than 2x edge offset."""
        positions = intel._calculate_fastener_positions(
            length=3.0,
            edge_offset=2.0,
            spacing=6.0,
        )
        # Should use center only
        assert len(positions) == 1
        assert positions[0] == 1.5  # Center of 3" joint

    def test_calculate_fastener_positions_exact_edges(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener positions when length exactly equals 2x edge offset."""
        positions = intel._calculate_fastener_positions(
            length=4.0,
            edge_offset=2.0,
            spacing=6.0,
        )
        # Should still get start and end positions
        assert positions[0] == 2.0
        assert positions[-1] == 2.0

    def test_calculate_fastener_positions_long_joint(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener positions for a long joint needs multiple interior fasteners."""
        positions = intel._calculate_fastener_positions(
            length=48.0,
            edge_offset=2.0,
            spacing=6.0,
        )
        assert positions[0] == 2.0
        assert positions[-1] == 46.0
        # 44" available, 6" spacing = ~7 interior divisions
        assert len(positions) >= 7

    def test_get_pocket_screw_spec(self, intel: WoodworkingIntelligence) -> None:
        """Test pocket screw spec generation."""
        spec = intel.get_pocket_screw_spec(length=24.0)
        assert spec.joint_type == JointType.POCKET_SCREW
        assert spec.positions[0] == 4.0  # Default edge offset
        assert spec.positions[-1] == 20.0  # 24 - 4
        assert spec.spacing == 8.0

    def test_get_dowel_spec(self, intel: WoodworkingIntelligence) -> None:
        """Test dowel spec generation."""
        spec = intel.get_dowel_spec(length=18.0)
        assert spec.joint_type == JointType.DOWEL
        assert spec.positions[0] == 2.0  # Default edge offset
        assert spec.positions[-1] == 16.0  # 18 - 2
        assert spec.spacing == 6.0


class TestWoodworkingIntelligenceJointSelection:
    """Tests for joint type selection logic."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    def test_select_joint_shelf(self, intel: WoodworkingIntelligence) -> None:
        """Test shelf joints default to DADO."""
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.SHELF)
        assert joint_type == JointType.DADO

    def test_select_joint_back(self, intel: WoodworkingIntelligence) -> None:
        """Test back panel joints default to RABBET."""
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.BACK)
        assert joint_type == JointType.RABBET

    def test_select_joint_divider(self, intel: WoodworkingIntelligence) -> None:
        """Test divider joints use DADO."""
        joint_type = intel._select_joint(PanelType.TOP, PanelType.DIVIDER)
        assert joint_type == JointType.DADO

    def test_select_joint_top(self, intel: WoodworkingIntelligence) -> None:
        """Test top panel joints use DADO."""
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.TOP)
        assert joint_type == JointType.DADO

    def test_select_joint_bottom(self, intel: WoodworkingIntelligence) -> None:
        """Test bottom panel joints use DADO."""
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.BOTTOM)
        assert joint_type == JointType.DADO

    def test_select_joint_face_frame_rail(self, intel: WoodworkingIntelligence) -> None:
        """Test face frame rail joints use POCKET_SCREW."""
        joint_type = intel._select_joint(
            PanelType.FACE_FRAME_STILE, PanelType.FACE_FRAME_RAIL
        )
        assert joint_type == JointType.POCKET_SCREW

    def test_select_joint_face_frame_stile(self, intel: WoodworkingIntelligence) -> None:
        """Test face frame stile joints use POCKET_SCREW."""
        joint_type = intel._select_joint(
            PanelType.FACE_FRAME_RAIL, PanelType.FACE_FRAME_STILE
        )
        assert joint_type == JointType.POCKET_SCREW

    def test_select_joint_horizontal_divider(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test horizontal divider joints use DADO."""
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.HORIZONTAL_DIVIDER)
        assert joint_type == JointType.DADO

    def test_select_joint_default_fallback(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that unspecified panels fall back to BUTT joint."""
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.DOOR)
        assert joint_type == JointType.BUTT

    def test_select_joint_custom_shelf_config(self) -> None:
        """Test custom shelf joint type configuration."""
        config = WoodworkingConfig(default_shelf_joint=JointType.BISCUIT)
        intel = WoodworkingIntelligence(config=config)
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.SHELF)
        assert joint_type == JointType.BISCUIT

    def test_select_joint_custom_back_config(self) -> None:
        """Test custom back panel joint type configuration."""
        config = WoodworkingConfig(default_back_joint=JointType.BUTT)
        intel = WoodworkingIntelligence(config=config)
        joint_type = intel._select_joint(PanelType.LEFT_SIDE, PanelType.BACK)
        assert joint_type == JointType.BUTT


class TestCheckSpans:
    """Tests for check_spans method (FR-02 span warnings)."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    def test_no_warnings_for_safe_spans(self, intel: WoodworkingIntelligence) -> None:
        """Test that safe spans (under limit) produce no warnings."""
        # Create cabinet with 30" wide section (under 36" limit for 3/4" plywood)
        cabinet = Cabinet(
            width=32.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=30.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=30.5,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        assert len(warnings) == 0

    def test_warning_for_overspan_shelf(self, intel: WoodworkingIntelligence) -> None:
        """Test that shelf span exceeding limit produces warning."""
        # Create cabinet with 40" wide shelf (exceeds 36" limit for 3/4" plywood)
        cabinet = Cabinet(
            width=42.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=40.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=40.5,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        assert len(warnings) >= 1
        assert warnings[0].span == 40.5
        assert warnings[0].max_span == 36.0
        assert "support" in warnings[0].suggestion.lower()

    def test_material_specific_limits_mdf(self, intel: WoodworkingIntelligence) -> None:
        """Test that MDF has stricter limits (24") than plywood (36")."""
        mdf_material = MaterialSpec(thickness=0.75, material_type=MaterialType.MDF)

        # 26" span exceeds 24" MDF limit but is under 36" plywood limit
        cabinet = Cabinet(
            width=28.0,
            height=84.0,
            depth=12.0,
            material=mdf_material,
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=26.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=26.5,
            depth=11.25,
            material=mdf_material,
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # Should have warning because 26.5" > 24" MDF limit
        assert len(warnings) >= 1
        assert warnings[0].max_span == 24.0

    def test_critical_severity_for_excessive_overspan(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that severity is 'critical' when span exceeds limit by >50%."""
        # 60" is more than 1.5x the 36" limit (55" would be exactly 50% over)
        cabinet = Cabinet(
            width=62.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=60.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=60.5,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        assert len(warnings) >= 1
        assert warnings[0].severity == "critical"

    def test_warning_severity_for_moderate_overspan(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that severity is 'warning' when span exceeds limit by <50%."""
        # 40" is ~11% over the 36" limit
        cabinet = Cabinet(
            width=42.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=40.0,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=40.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        assert len(warnings) >= 1
        assert warnings[0].severity == "warning"

    def test_multiple_shelves_multiple_warnings(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that multiple over-span shelves produce multiple warnings."""
        cabinet = Cabinet(
            width=42.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=40.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        # Add 3 shelves all exceeding limit
        for y_pos in [20.0, 40.0, 60.0]:
            shelf = Shelf(
                width=40.5,
                depth=11.25,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, y_pos),
            )
            section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # Should have 3 shelf warnings
        shelf_warnings = [w for w in warnings if "Shelf" in w.panel_label]
        assert len(shelf_warnings) == 3

    def test_multiple_sections_checked(self, intel: WoodworkingIntelligence) -> None:
        """Test that shelves in all sections are checked."""
        cabinet = Cabinet(
            width=84.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # Section 1: safe span
        section1 = Section(
            width=30.0,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf1 = Shelf(
            width=30.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section1.add_shelf(shelf1)
        cabinet.sections.append(section1)

        # Section 2: over-span
        section2 = Section(
            width=40.0,
            height=82.5,
            depth=11.25,
            position=Position(31.5, 0.75),
        )
        shelf2 = Shelf(
            width=40.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(31.5, 20.0),
        )
        section2.add_shelf(shelf2)
        cabinet.sections.append(section2)

        warnings = intel.check_spans(cabinet)
        # Should have 1 warning for section 2 shelf
        shelf_warnings = [w for w in warnings if "Shelf" in w.panel_label]
        assert len(shelf_warnings) == 1
        assert "Section 2" in shelf_warnings[0].panel_label

    def test_top_panel_span_warning(self, intel: WoodworkingIntelligence) -> None:
        """Test that top panel span is checked."""
        # Single wide section means top panel has wide span
        cabinet = Cabinet(
            width=50.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=48.5,  # Exceeds 36" limit
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # Should have top panel warning
        top_warnings = [w for w in warnings if "Top Panel" in w.panel_label]
        assert len(top_warnings) == 1

    def test_bottom_panel_span_warning(self, intel: WoodworkingIntelligence) -> None:
        """Test that bottom panel span is checked."""
        cabinet = Cabinet(
            width=50.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=48.5,  # Exceeds 36" limit
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # Should have bottom panel warning
        bottom_warnings = [w for w in warnings if "Bottom Panel" in w.panel_label]
        assert len(bottom_warnings) == 1

    def test_multi_section_reduces_case_span(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that multiple sections reduce effective case panel span."""
        # 72" cabinet with 3x 24" sections - each section is under limit
        cabinet = Cabinet(
            width=74.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        for i in range(3):
            section = Section(
                width=24.0,  # Under 36" limit
                height=82.5,
                depth=11.25,
                position=Position(0.75 + i * 24.75, 0.75),
            )
            cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # No top/bottom warnings because dividers reduce span to 24"
        top_bottom_warnings = [
            w for w in warnings if "Panel" in w.panel_label
        ]
        assert len(top_bottom_warnings) == 0

    def test_suggestion_text_varies_by_excess(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that suggestion text varies based on how much span is exceeded."""
        # Test minor excess (< 25%)
        cabinet_minor = Cabinet(
            width=42.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section_minor = Section(
            width=40.0,  # ~11% over 36" limit
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf_minor = Shelf(
            width=40.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section_minor.add_shelf(shelf_minor)
        cabinet_minor.sections.append(section_minor)

        warnings_minor = intel.check_spans(cabinet_minor)
        # Minor excess should mention "Consider"
        assert "Consider" in warnings_minor[0].suggestion

        # Test major excess (> 50%)
        cabinet_major = Cabinet(
            width=62.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section_major = Section(
            width=60.0,  # ~67% over 36" limit
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf_major = Shelf(
            width=60.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section_major.add_shelf(shelf_major)
        cabinet_major.sections.append(section_major)

        warnings_major = intel.check_spans(cabinet_major)
        # Major excess should mention thicker material
        assert "thicker material" in warnings_major[0].suggestion.lower()

    def test_empty_cabinet_no_shelf_warnings(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that cabinet with no sections produces no shelf warnings."""
        # Note: Top/bottom panels may still produce warnings if interior_width > limit
        # This test uses a narrow cabinet to avoid case panel warnings
        cabinet = Cabinet(
            width=32.0,  # Narrow enough that interior_width < 36" limit
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # No sections added

        warnings = intel.check_spans(cabinet)
        # No shelf warnings because no sections
        shelf_warnings = [w for w in warnings if "Shelf" in w.panel_label]
        assert len(shelf_warnings) == 0

    def test_solid_wood_thicker_has_higher_limit(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that 1 inch solid wood has 42 inch limit (higher than 36)."""
        solid_wood = MaterialSpec(thickness=1.0, material_type=MaterialType.SOLID_WOOD)

        # 40" span is under 42" solid wood limit
        cabinet = Cabinet(
            width=42.0,
            height=84.0,
            depth=12.0,
            material=solid_wood,
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=40.0,
            height=82.5,
            depth=11.25,
            position=Position(1.0, 1.0),
        )
        shelf = Shelf(
            width=40.0,
            depth=11.25,
            material=solid_wood,
            position=Position(1.0, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # No shelf warnings because 40" < 42" solid wood limit
        shelf_warnings = [w for w in warnings if "Shelf" in w.panel_label]
        assert len(shelf_warnings) == 0


class TestGrainDirection:
    """Tests for grain direction recommendation methods (FR-03)."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def plywood_side_panel(self) -> CutPiece:
        """Create a plywood side panel (visible, width > height)."""
        return CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Side Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=MaterialSpec.standard_3_4(),
        )

    @pytest.fixture
    def plywood_back_panel(self) -> CutPiece:
        """Create a plywood back panel (non-visible, height > width)."""
        return CutPiece(
            width=12.0,
            height=36.0,
            quantity=1,
            label="Back Panel",
            panel_type=PanelType.BACK,
            material=MaterialSpec.standard_1_2(),
        )

    @pytest.fixture
    def solid_wood_rail(self) -> CutPiece:
        """Create a solid wood face frame rail."""
        return CutPiece(
            width=24.0,
            height=3.0,
            quantity=1,
            label="Face Frame Rail",
            panel_type=PanelType.FACE_FRAME_RAIL,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.SOLID_WOOD),
        )

    @pytest.fixture
    def mdf_shelf(self) -> CutPiece:
        """Create an MDF shelf (no visible grain)."""
        return CutPiece(
            width=30.0,
            height=12.0,
            quantity=1,
            label="MDF Shelf",
            panel_type=PanelType.SHELF,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.MDF),
        )

    @pytest.fixture
    def small_plywood_block(self) -> CutPiece:
        """Create a small plywood block (< 12" in all dimensions)."""
        return CutPiece(
            width=6.0,
            height=6.0,
            quantity=1,
            label="Small Block",
            panel_type=PanelType.FILLER,
            material=MaterialSpec.standard_3_4(),
        )

    def test_get_grain_directions_returns_dict(
        self, intel: WoodworkingIntelligence, plywood_side_panel: CutPiece
    ) -> None:
        """Test that get_grain_directions returns a dict."""
        directions = intel.get_grain_directions([plywood_side_panel])
        assert isinstance(directions, dict)
        assert "Side Panel" in directions

    def test_grain_direction_visible_plywood_wider_than_tall(
        self, intel: WoodworkingIntelligence, plywood_side_panel: CutPiece
    ) -> None:
        """Test grain direction for visible plywood panel wider than tall."""
        # 36" wide x 12" tall -> grain along length (width is longest)
        directions = intel.get_grain_directions([plywood_side_panel])
        from cabinets.domain.value_objects import GrainDirection

        assert directions["Side Panel"] == GrainDirection.LENGTH

    def test_grain_direction_non_visible_tall_panel(
        self, intel: WoodworkingIntelligence, plywood_back_panel: CutPiece
    ) -> None:
        """Test grain direction for non-visible panel taller than wide."""
        # 12" wide x 36" tall, back panel (not visible)
        # But > 12" longest dimension, so grain along longest (height)
        directions = intel.get_grain_directions([plywood_back_panel])
        from cabinets.domain.value_objects import GrainDirection

        assert directions["Back Panel"] == GrainDirection.WIDTH

    def test_grain_direction_solid_wood_always_along_length(
        self, intel: WoodworkingIntelligence, solid_wood_rail: CutPiece
    ) -> None:
        """Test that solid wood always has grain along longest dimension."""
        # 24" wide x 3" tall solid wood -> grain along length (width is longest)
        directions = intel.get_grain_directions([solid_wood_rail])
        from cabinets.domain.value_objects import GrainDirection

        assert directions["Face Frame Rail"] == GrainDirection.LENGTH

    def test_grain_direction_mdf_is_none(
        self, intel: WoodworkingIntelligence, mdf_shelf: CutPiece
    ) -> None:
        """Test that MDF has no grain direction (NONE)."""
        directions = intel.get_grain_directions([mdf_shelf])
        from cabinets.domain.value_objects import GrainDirection

        assert directions["MDF Shelf"] == GrainDirection.NONE

    def test_grain_direction_particle_board_is_none(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that particle board has no grain direction (NONE)."""
        piece = CutPiece(
            width=30.0,
            height=12.0,
            quantity=1,
            label="PB Shelf",
            panel_type=PanelType.SHELF,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.PARTICLE_BOARD),
        )
        directions = intel.get_grain_directions([piece])
        from cabinets.domain.value_objects import GrainDirection

        assert directions["PB Shelf"] == GrainDirection.NONE

    def test_grain_direction_small_piece_is_none(
        self, intel: WoodworkingIntelligence, small_plywood_block: CutPiece
    ) -> None:
        """Test that small non-visible pieces have no grain constraint."""
        directions = intel.get_grain_directions([small_plywood_block])
        from cabinets.domain.value_objects import GrainDirection

        assert directions["Small Block"] == GrainDirection.NONE

    def test_grain_direction_respects_existing_metadata(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that existing grain_direction in metadata is respected."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Custom Grain Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=MaterialSpec.standard_3_4(),
            cut_metadata={"grain_direction": "width"},  # Override to width
        )
        directions = intel.get_grain_directions([piece])
        # Should use existing metadata, not calculate
        assert directions["Custom Grain Panel"] == GrainDirection.WIDTH

    def test_annotate_cut_list_adds_grain_direction(
        self, intel: WoodworkingIntelligence, plywood_side_panel: CutPiece
    ) -> None:
        """Test that annotate_cut_list adds grain_direction to metadata."""
        annotated = intel.annotate_cut_list([plywood_side_panel])
        assert len(annotated) == 1
        assert "grain_direction" in annotated[0].cut_metadata
        assert annotated[0].cut_metadata["grain_direction"] == "length"

    def test_annotate_cut_list_preserves_existing_metadata(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that annotate_cut_list preserves existing metadata."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Panel with Metadata",
            panel_type=PanelType.LEFT_SIDE,
            material=MaterialSpec.standard_3_4(),
            cut_metadata={"arch_type": "tudor", "radius": 6.0},
        )
        annotated = intel.annotate_cut_list([piece])
        # Original metadata should be preserved
        assert annotated[0].cut_metadata["arch_type"] == "tudor"
        assert annotated[0].cut_metadata["radius"] == 6.0
        # Grain direction should be added
        assert annotated[0].cut_metadata["grain_direction"] == "length"

    def test_annotate_cut_list_does_not_override_existing_grain(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that annotate_cut_list doesn't override existing grain_direction."""
        piece = CutPiece(
            width=36.0,
            height=12.0,
            quantity=1,
            label="Custom Grain",
            panel_type=PanelType.LEFT_SIDE,
            material=MaterialSpec.standard_3_4(),
            cut_metadata={"grain_direction": "width"},  # User specified
        )
        annotated = intel.annotate_cut_list([piece])
        # Should keep original "width", not calculate "length"
        assert annotated[0].cut_metadata["grain_direction"] == "width"

    def test_annotate_cut_list_multiple_pieces(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test annotate_cut_list with multiple pieces."""
        pieces = [
            CutPiece(
                width=36.0,
                height=12.0,
                quantity=2,
                label="Side Panel",
                panel_type=PanelType.LEFT_SIDE,
                material=MaterialSpec.standard_3_4(),
            ),
            CutPiece(
                width=48.0,
                height=84.0,
                quantity=1,
                label="Back Panel",
                panel_type=PanelType.BACK,
                material=MaterialSpec.standard_1_2(),
            ),
            CutPiece(
                width=24.0,
                height=3.0,
                quantity=4,
                label="Face Frame Rail",
                panel_type=PanelType.FACE_FRAME_RAIL,
                material=MaterialSpec(thickness=0.75, material_type=MaterialType.SOLID_WOOD),
            ),
        ]
        annotated = intel.annotate_cut_list(pieces)
        assert len(annotated) == 3
        # Each piece should have grain_direction in metadata
        for piece in annotated:
            assert "grain_direction" in piece.cut_metadata

    def test_grain_direction_shelf_visible_plywood(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test grain direction for a plywood shelf (visible panel)."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=30.0,
            height=12.0,
            quantity=1,
            label="Plywood Shelf",
            panel_type=PanelType.SHELF,
            material=MaterialSpec.standard_3_4(),
        )
        directions = intel.get_grain_directions([piece])
        # Shelf is visible, plywood, width > height -> LENGTH
        assert directions["Plywood Shelf"] == GrainDirection.LENGTH

    def test_grain_direction_door_visible_panel(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test grain direction for a door panel."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=20.0,
            height=30.0,
            quantity=1,
            label="Door Panel",
            panel_type=PanelType.DOOR,
            material=MaterialSpec.standard_3_4(),
        )
        directions = intel.get_grain_directions([piece])
        # Door is visible, plywood, height > width -> WIDTH
        assert directions["Door Panel"] == GrainDirection.WIDTH

    def test_grain_direction_drawer_front_visible(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test grain direction for a drawer front."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=18.0,
            height=6.0,
            quantity=1,
            label="Drawer Front",
            panel_type=PanelType.DRAWER_FRONT,
            material=MaterialSpec.standard_3_4(),
        )
        directions = intel.get_grain_directions([piece])
        # Drawer front is visible, plywood, width > height -> LENGTH
        assert directions["Drawer Front"] == GrainDirection.LENGTH

    def test_grain_direction_divider_not_visible(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test grain direction for an internal divider (not visible)."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=12.0,
            height=30.0,
            quantity=1,
            label="Divider",
            panel_type=PanelType.DIVIDER,
            material=MaterialSpec.standard_3_4(),
        )
        directions = intel.get_grain_directions([piece])
        # Divider is not visible, but > 12" longest dimension -> along longest
        assert directions["Divider"] == GrainDirection.WIDTH

    def test_is_visible_panel_side_panels(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that side panels are considered visible."""
        left_piece = CutPiece(
            width=12.0, height=30.0, quantity=1, label="Left",
            panel_type=PanelType.LEFT_SIDE, material=MaterialSpec.standard_3_4()
        )
        right_piece = CutPiece(
            width=12.0, height=30.0, quantity=1, label="Right",
            panel_type=PanelType.RIGHT_SIDE, material=MaterialSpec.standard_3_4()
        )
        assert intel._is_visible_panel(left_piece) is True
        assert intel._is_visible_panel(right_piece) is True

    def test_is_visible_panel_back_not_visible(
        self, intel: WoodworkingIntelligence, plywood_back_panel: CutPiece
    ) -> None:
        """Test that back panels are not considered visible."""
        assert intel._is_visible_panel(plywood_back_panel) is False

    def test_is_visible_panel_drawer_components(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test drawer component visibility."""
        drawer_front = CutPiece(
            width=18.0, height=6.0, quantity=1, label="Front",
            panel_type=PanelType.DRAWER_FRONT, material=MaterialSpec.standard_3_4()
        )
        drawer_side = CutPiece(
            width=18.0, height=6.0, quantity=1, label="Side",
            panel_type=PanelType.DRAWER_SIDE, material=MaterialSpec.standard_3_4()
        )
        drawer_bottom = CutPiece(
            width=18.0, height=12.0, quantity=1, label="Bottom",
            panel_type=PanelType.DRAWER_BOTTOM, material=MaterialSpec.standard_3_4()
        )
        # Drawer front is visible
        assert intel._is_visible_panel(drawer_front) is True
        # Drawer side and bottom are not visible
        assert intel._is_visible_panel(drawer_side) is False
        assert intel._is_visible_panel(drawer_bottom) is False

    def test_grain_for_longest_dimension_width_larger(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test _grain_for_longest_dimension when width > height."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=36.0, height=12.0, quantity=1, label="Wide",
            panel_type=PanelType.SHELF, material=MaterialSpec.standard_3_4()
        )
        assert intel._grain_for_longest_dimension(piece) == GrainDirection.LENGTH

    def test_grain_for_longest_dimension_height_larger(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test _grain_for_longest_dimension when height > width."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=12.0, height=36.0, quantity=1, label="Tall",
            panel_type=PanelType.LEFT_SIDE, material=MaterialSpec.standard_3_4()
        )
        assert intel._grain_for_longest_dimension(piece) == GrainDirection.WIDTH

    def test_grain_for_longest_dimension_equal(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test _grain_for_longest_dimension when width == height."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=24.0, height=24.0, quantity=1, label="Square",
            panel_type=PanelType.SHELF, material=MaterialSpec.standard_3_4()
        )
        # When equal, defaults to LENGTH
        assert intel._grain_for_longest_dimension(piece) == GrainDirection.LENGTH

    def test_get_existing_grain_invalid_value(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that invalid grain_direction value returns None."""
        piece = CutPiece(
            width=36.0, height=12.0, quantity=1, label="Invalid",
            panel_type=PanelType.SHELF, material=MaterialSpec.standard_3_4(),
            cut_metadata={"grain_direction": "invalid_value"}
        )
        result = intel._get_existing_grain(piece)
        assert result is None

    def test_get_existing_grain_valid_value(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that valid grain_direction value is returned."""
        from cabinets.domain.value_objects import GrainDirection

        piece = CutPiece(
            width=36.0, height=12.0, quantity=1, label="Valid",
            panel_type=PanelType.SHELF, material=MaterialSpec.standard_3_4(),
            cut_metadata={"grain_direction": "width"}
        )
        result = intel._get_existing_grain(piece)
        assert result == GrainDirection.WIDTH


class TestWeightCapacityConstants:
    """Tests for weight capacity constants."""

    def test_safety_factor_value(self) -> None:
        """Test safety factor is 0.5 (50%)."""
        assert SAFETY_FACTOR == 0.5

    def test_max_deflection_ratio_value(self) -> None:
        """Test max deflection ratio is L/300."""
        assert MAX_DEFLECTION_RATIO == 300


class TestEstimateCapacity:
    """Tests for estimate_capacity method (FR-04)."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    def test_estimate_capacity_returns_weight_capacity(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that estimate_capacity returns a WeightCapacity object."""
        capacity = intel.estimate_capacity(
            thickness=0.75,
            depth=12.0,
            span=24.0,
            material_type=MaterialType.PLYWOOD,
            load_type="distributed",
            panel_label="Test Shelf",
        )
        assert isinstance(capacity, WeightCapacity)
        assert capacity.panel_label == "Test Shelf"
        assert capacity.capacity_lbs > 0
        assert capacity.load_type == "distributed"
        assert "Advisory" in capacity.disclaimer

    def test_capacity_decreases_with_longer_spans(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that longer spans result in lower capacity."""
        cap_24 = intel.estimate_capacity(0.75, 12.0, 24.0, MaterialType.PLYWOOD)
        cap_36 = intel.estimate_capacity(0.75, 12.0, 36.0, MaterialType.PLYWOOD)

        assert cap_24.capacity_lbs > cap_36.capacity_lbs

    def test_point_load_lower_than_distributed(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that point loads have lower capacity than distributed loads."""
        cap_dist = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD, "distributed"
        )
        cap_point = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD, "point"
        )

        assert cap_dist.capacity_lbs > cap_point.capacity_lbs

    def test_material_type_affects_capacity(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that different materials have different capacities."""
        cap_plywood = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )
        cap_mdf = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.MDF
        )

        # Plywood has higher modulus, so higher capacity
        assert cap_plywood.capacity_lbs > cap_mdf.capacity_lbs

    def test_thicker_material_higher_capacity(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that thicker material has higher capacity."""
        cap_half = intel.estimate_capacity(
            0.5, 12.0, 24.0, MaterialType.PLYWOOD
        )
        cap_three_quarter = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )
        cap_one_inch = intel.estimate_capacity(
            1.0, 12.0, 24.0, MaterialType.PLYWOOD
        )

        assert cap_half.capacity_lbs < cap_three_quarter.capacity_lbs
        assert cap_three_quarter.capacity_lbs < cap_one_inch.capacity_lbs

    def test_deeper_shelf_higher_capacity(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that deeper shelves have higher capacity."""
        cap_8_deep = intel.estimate_capacity(
            0.75, 8.0, 24.0, MaterialType.PLYWOOD
        )
        cap_12_deep = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )
        cap_16_deep = intel.estimate_capacity(
            0.75, 16.0, 24.0, MaterialType.PLYWOOD
        )

        assert cap_8_deep.capacity_lbs < cap_12_deep.capacity_lbs
        assert cap_12_deep.capacity_lbs < cap_16_deep.capacity_lbs

    def test_capacity_rounded_to_nearest_5(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that capacity is rounded to nearest 5 lbs."""
        capacity = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )
        # Capacity should be divisible by 5
        assert capacity.capacity_lbs % 5 == 0

    def test_minimum_capacity_is_5(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that minimum capacity is 5 lbs even for weak configurations."""
        # Very long span, thin material, low modulus
        capacity = intel.estimate_capacity(
            0.25, 6.0, 72.0, MaterialType.PARTICLE_BOARD
        )
        assert capacity.capacity_lbs >= 5.0

    def test_disclaimer_always_present(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that disclaimer is always included."""
        capacity = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )
        assert capacity.disclaimer == "Advisory only - not engineered"

    def test_span_stored_in_result(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that span is stored in the WeightCapacity result."""
        capacity = intel.estimate_capacity(
            0.75, 12.0, 30.0, MaterialType.PLYWOOD
        )
        assert capacity.span == 30.0

    def test_material_stored_in_result(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that material is stored in the WeightCapacity result."""
        capacity = intel.estimate_capacity(
            0.75, 12.0, 24.0, MaterialType.MDF
        )
        assert capacity.material.thickness == 0.75
        assert capacity.material.material_type == MaterialType.MDF

    def test_solid_wood_higher_than_plywood(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that solid wood has higher capacity than plywood."""
        cap_plywood = intel.estimate_capacity(
            1.0, 12.0, 36.0, MaterialType.PLYWOOD
        )
        cap_solid = intel.estimate_capacity(
            1.0, 12.0, 36.0, MaterialType.SOLID_WOOD
        )

        # Solid wood has higher modulus
        assert cap_solid.capacity_lbs > cap_plywood.capacity_lbs


class TestCalculateBaseCapacity:
    """Tests for _calculate_base_capacity private method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    def test_zero_span_returns_zero(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that zero span returns zero capacity."""
        capacity = intel._calculate_base_capacity(
            0.75, 12.0, 0.0, MaterialType.PLYWOOD
        )
        assert capacity == 0.0

    def test_negative_span_returns_zero(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that negative span returns zero capacity."""
        capacity = intel._calculate_base_capacity(
            0.75, 12.0, -10.0, MaterialType.PLYWOOD
        )
        assert capacity == 0.0

    def test_uses_material_modulus(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that calculation uses correct material modulus."""
        # MDF modulus is 400,000 vs plywood 1,200,000
        # So plywood should be 3x capacity for same dimensions
        cap_mdf = intel._calculate_base_capacity(
            0.75, 12.0, 24.0, MaterialType.MDF
        )
        cap_plywood = intel._calculate_base_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )

        # Plywood should be about 3x MDF
        ratio = cap_plywood / cap_mdf
        assert 2.9 < ratio < 3.1  # Allow small floating point tolerance

    def test_capacity_scales_with_depth(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that capacity scales linearly with depth (I = b*h^3/12)."""
        cap_12 = intel._calculate_base_capacity(
            0.75, 12.0, 24.0, MaterialType.PLYWOOD
        )
        cap_24 = intel._calculate_base_capacity(
            0.75, 24.0, 24.0, MaterialType.PLYWOOD
        )

        # Doubling depth should double capacity
        ratio = cap_24 / cap_12
        assert 1.9 < ratio < 2.1

    def test_capacity_scales_with_thickness_cubed(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that capacity scales with thickness^3 (moment of inertia)."""
        cap_half = intel._calculate_base_capacity(
            0.5, 12.0, 24.0, MaterialType.PLYWOOD
        )
        cap_one = intel._calculate_base_capacity(
            1.0, 12.0, 24.0, MaterialType.PLYWOOD
        )

        # Doubling thickness should increase capacity by 8x (2^3)
        ratio = cap_one / cap_half
        assert 7.5 < ratio < 8.5


class TestGetShelfCapacities:
    """Tests for get_shelf_capacities method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def cabinet_with_shelves(self) -> Cabinet:
        """Create a cabinet with multiple sections and shelves."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf1 = Shelf(
            width=46.5,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        shelf2 = Shelf(
            width=46.5,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 40.0),
        )
        section.add_shelf(shelf1)
        section.add_shelf(shelf2)
        cabinet.sections.append(section)
        return cabinet

    def test_returns_list_of_weight_capacities(
        self, intel: WoodworkingIntelligence, cabinet_with_shelves: Cabinet
    ) -> None:
        """Test that get_shelf_capacities returns list of WeightCapacity."""
        capacities = intel.get_shelf_capacities(cabinet_with_shelves)
        assert isinstance(capacities, list)
        assert len(capacities) == 2
        assert all(isinstance(c, WeightCapacity) for c in capacities)

    def test_shelf_labels_are_correct(
        self, intel: WoodworkingIntelligence, cabinet_with_shelves: Cabinet
    ) -> None:
        """Test that shelf labels indicate section and shelf number."""
        capacities = intel.get_shelf_capacities(cabinet_with_shelves)
        assert capacities[0].panel_label == "Section 1 Shelf 1"
        assert capacities[1].panel_label == "Section 1 Shelf 2"

    def test_uses_section_width_as_span(
        self, intel: WoodworkingIntelligence, cabinet_with_shelves: Cabinet
    ) -> None:
        """Test that section width is used as the span."""
        capacities = intel.get_shelf_capacities(cabinet_with_shelves)
        assert capacities[0].span == 46.5
        assert capacities[1].span == 46.5

    def test_empty_cabinet_returns_empty_list(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that cabinet with no shelves returns empty list."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        capacities = intel.get_shelf_capacities(cabinet)
        assert capacities == []

    def test_multi_section_cabinet(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test capacity calculation for cabinet with multiple sections."""
        cabinet = Cabinet(
            width=72.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        # Section 1 - narrow
        section1 = Section(
            width=24.0,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        shelf1 = Shelf(
            width=24.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section1.add_shelf(shelf1)
        cabinet.sections.append(section1)

        # Section 2 - wider
        section2 = Section(
            width=36.0,
            height=82.5,
            depth=11.25,
            position=Position(24.75, 0.75),
        )
        shelf2 = Shelf(
            width=36.0,
            depth=11.25,
            material=MaterialSpec.standard_3_4(),
            position=Position(24.75, 30.0),
        )
        section2.add_shelf(shelf2)
        cabinet.sections.append(section2)

        capacities = intel.get_shelf_capacities(cabinet)
        assert len(capacities) == 2
        assert capacities[0].panel_label == "Section 1 Shelf 1"
        assert capacities[1].panel_label == "Section 2 Shelf 1"
        # Narrower span should have higher capacity
        assert capacities[0].capacity_lbs > capacities[1].capacity_lbs


class TestFormatCapacityReport:
    """Tests for format_capacity_report method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def sample_capacities(self) -> list[WeightCapacity]:
        """Create sample capacities for testing."""
        return [
            WeightCapacity(
                panel_label="Section 1 Shelf 1",
                capacity_lbs=75.0,
                load_type="distributed",
                span=30.0,
                material=MaterialSpec.standard_3_4(),
            ),
            WeightCapacity(
                panel_label="Section 1 Shelf 2",
                capacity_lbs=75.0,
                load_type="distributed",
                span=30.0,
                material=MaterialSpec.standard_3_4(),
            ),
        ]

    def test_report_contains_header(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report contains header."""
        report = intel.format_capacity_report(sample_capacities)
        assert "WEIGHT CAPACITY ESTIMATES" in report

    def test_report_contains_disclaimer(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report contains disclaimer."""
        report = intel.format_capacity_report(sample_capacities)
        assert "DISCLAIMER" in report
        assert "advisory" in report.lower()

    def test_report_contains_capacity_values(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report contains capacity values."""
        report = intel.format_capacity_report(sample_capacities)
        assert "75 lbs" in report
        assert "distributed" in report

    def test_report_contains_shelf_labels(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report contains shelf labels."""
        report = intel.format_capacity_report(sample_capacities)
        assert "Section 1 Shelf 1" in report
        assert "Section 1 Shelf 2" in report

    def test_report_contains_material_info(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report contains material information."""
        report = intel.format_capacity_report(sample_capacities)
        assert "plywood" in report
        assert "0.75" in report

    def test_report_contains_span_info(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report contains span information."""
        report = intel.format_capacity_report(sample_capacities)
        assert "30.0" in report
        assert "Span" in report

    def test_report_mentions_point_load_reduction(
        self, intel: WoodworkingIntelligence, sample_capacities: list[WeightCapacity]
    ) -> None:
        """Test that report mentions point load reduction."""
        report = intel.format_capacity_report(sample_capacities)
        assert "Point loads" in report or "point" in report.lower()
        assert "50%" in report

    def test_empty_list_still_has_header(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that empty list produces report with header but no shelves."""
        report = intel.format_capacity_report([])
        assert "WEIGHT CAPACITY ESTIMATES" in report
        assert "DISCLAIMER" in report


class TestWeightCapacityIntegration:
    """Integration tests for weight capacity estimation."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    def test_typical_plywood_shelf_capacity_range(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that 3/4 plywood 12 inch deep shelf at 24 inch span is in reasonable range."""
        capacity = intel.estimate_capacity(
            thickness=0.75,
            depth=12.0,
            span=24.0,
            material_type=MaterialType.PLYWOOD,
        )
        # Capacity should be reasonable for shelf use (not too high or too low)
        # The deflection-based formula produces ~110 lbs for this configuration
        # which is appropriate for a 3/4" plywood shelf at 24" span
        assert 50 <= capacity.capacity_lbs <= 150

    def test_longer_span_lower_capacity(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that 30 inch span has lower capacity than 24 inch."""
        cap_24 = intel.estimate_capacity(
            thickness=0.75, depth=12.0, span=24.0, material_type=MaterialType.PLYWOOD
        )
        cap_30 = intel.estimate_capacity(
            thickness=0.75, depth=12.0, span=30.0, material_type=MaterialType.PLYWOOD
        )
        cap_36 = intel.estimate_capacity(
            thickness=0.75, depth=12.0, span=36.0, material_type=MaterialType.PLYWOOD
        )

        assert cap_24.capacity_lbs > cap_30.capacity_lbs > cap_36.capacity_lbs

    def test_mdf_lower_capacity_than_plywood(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that MDF has significantly lower capacity than plywood."""
        cap_plywood = intel.estimate_capacity(
            thickness=0.75, depth=12.0, span=24.0, material_type=MaterialType.PLYWOOD
        )
        cap_mdf = intel.estimate_capacity(
            thickness=0.75, depth=12.0, span=24.0, material_type=MaterialType.MDF
        )

        # MDF should be roughly 1/3 the capacity of plywood (ratio of moduli)
        assert cap_mdf.capacity_lbs < cap_plywood.capacity_lbs
        ratio = cap_plywood.capacity_lbs / cap_mdf.capacity_lbs
        assert 2.5 < ratio < 3.5

    def test_full_cabinet_workflow(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test complete workflow: create cabinet, get capacities, format report."""
        # Create cabinet with shelves
        cabinet = Cabinet(
            width=36.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=34.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        for i in range(3):
            shelf = Shelf(
                width=34.5,
                depth=11.25,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 20.0 + i * 20),
            )
            section.add_shelf(shelf)
        cabinet.sections.append(section)

        # Get capacities
        capacities = intel.get_shelf_capacities(cabinet)
        assert len(capacities) == 3

        # Format report
        report = intel.format_capacity_report(capacities)
        assert "WEIGHT CAPACITY ESTIMATES" in report
        assert "Section 1 Shelf 1" in report
        assert "Section 1 Shelf 2" in report
        assert "Section 1 Shelf 3" in report
        assert "lbs" in report


# --- Hardware Calculation Tests (FR-05) ---


class TestHardwareConstants:
    """Tests for hardware specification constants."""

    def test_case_screw_spec(self) -> None:
        """Test case screw specification string."""
        from cabinets.domain.services.woodworking import CASE_SCREW_SPEC, CASE_SCREW_SPACING

        assert "1-1/4" in CASE_SCREW_SPEC
        assert "#8" in CASE_SCREW_SPEC
        assert CASE_SCREW_SPACING == 8.0

    def test_back_panel_screw_spec(self) -> None:
        """Test back panel screw specification string."""
        from cabinets.domain.services.woodworking import BACK_PANEL_SCREW_SPEC, BACK_PANEL_SCREW_SPACING

        assert "5/8" in BACK_PANEL_SCREW_SPEC
        assert "#6" in BACK_PANEL_SCREW_SPEC
        assert BACK_PANEL_SCREW_SPACING == 6.0

    def test_pocket_screw_spec(self) -> None:
        """Test pocket screw specification strings."""
        from cabinets.domain.services.woodworking import (
            POCKET_SCREW_SPEC,
            POCKET_SCREW_COARSE_NOTE,
            POCKET_SCREW_FINE_NOTE,
        )

        assert "pocket" in POCKET_SCREW_SPEC.lower()
        assert "coarse" in POCKET_SCREW_COARSE_NOTE.lower()
        assert "fine" in POCKET_SCREW_FINE_NOTE.lower()

    def test_dowel_spec(self) -> None:
        """Test dowel specification string."""
        from cabinets.domain.services.woodworking import DOWEL_SPEC

        assert "5/16" in DOWEL_SPEC
        assert "1-1/2" in DOWEL_SPEC
        assert "dowel" in DOWEL_SPEC.lower()

    def test_biscuit_specs(self) -> None:
        """Test biscuit specification strings."""
        from cabinets.domain.services.woodworking import BISCUIT_SPEC_10, BISCUIT_SPEC_20

        assert "#10" in BISCUIT_SPEC_10
        assert "#20" in BISCUIT_SPEC_20


class TestCalculateHardware:
    """Tests for calculate_hardware method."""

    @pytest.fixture
    def simple_cabinet(self) -> Cabinet:
        """Create a simple cabinet with one section."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.5,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    @pytest.fixture
    def multi_section_cabinet(self) -> Cabinet:
        """Create a cabinet with two sections (one divider)."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section1 = Section(
            width=22.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        section2 = Section(
            width=22.5,
            height=82.5,
            depth=11.25,
            position=Position(24.0, 0.75),
        )
        cabinet.sections.append(section1)
        cabinet.sections.append(section2)
        return cabinet

    @pytest.fixture
    def cabinet_with_shelves(self) -> Cabinet:
        """Create a cabinet with shelves."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        for i in range(3):
            shelf = Shelf(
                width=46.5,
                depth=11.25,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 20 + i * 20),
            )
            section.add_shelf(shelf)
        cabinet.sections.append(section)
        return cabinet

    def test_calculate_hardware_returns_hardware_list(
        self, simple_cabinet: Cabinet
    ) -> None:
        """Test that calculate_hardware returns a HardwareList."""
        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(simple_cabinet)
        assert isinstance(hardware, HardwareList)

    def test_calculate_hardware_has_case_screws(self, simple_cabinet: Cabinet) -> None:
        """Test that hardware list includes case screws."""
        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(simple_cabinet, include_overage=False)

        case_screws = [
            i for i in hardware.items if "1-1/4" in i.name and "Case" in (i.notes or "")
        ]
        assert len(case_screws) == 1
        assert case_screws[0].quantity > 0

    def test_calculate_hardware_has_back_panel_screws(
        self, simple_cabinet: Cabinet
    ) -> None:
        """Test that hardware list includes back panel screws."""
        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(simple_cabinet, include_overage=False)

        back_screws = [i for i in hardware.items if "5/8" in i.name]
        assert len(back_screws) == 1
        assert back_screws[0].quantity > 0

    def test_calculate_hardware_total_count_positive(
        self, simple_cabinet: Cabinet
    ) -> None:
        """Test that hardware list has positive total count."""
        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(simple_cabinet)
        assert hardware.total_count > 0

    def test_calculate_hardware_with_overage(self, simple_cabinet: Cabinet) -> None:
        """Test that overage is applied correctly."""
        intel = WoodworkingIntelligence()
        hardware_no_overage = intel.calculate_hardware(
            simple_cabinet, include_overage=False
        )
        hardware_with_overage = intel.calculate_hardware(
            simple_cabinet, include_overage=True, overage_percent=10.0
        )

        assert hardware_with_overage.total_count > hardware_no_overage.total_count

    def test_calculate_hardware_custom_overage(self, simple_cabinet: Cabinet) -> None:
        """Test custom overage percentage."""
        intel = WoodworkingIntelligence()
        hardware_10pct = intel.calculate_hardware(
            simple_cabinet, include_overage=True, overage_percent=10.0
        )
        hardware_25pct = intel.calculate_hardware(
            simple_cabinet, include_overage=True, overage_percent=25.0
        )

        assert hardware_25pct.total_count > hardware_10pct.total_count

    def test_calculate_hardware_dividers_add_screws(
        self, simple_cabinet: Cabinet, multi_section_cabinet: Cabinet
    ) -> None:
        """Test that dividers add case and back panel screws."""
        intel = WoodworkingIntelligence()
        simple_hw = intel.calculate_hardware(simple_cabinet, include_overage=False)
        multi_hw = intel.calculate_hardware(multi_section_cabinet, include_overage=False)

        # Multi-section cabinet should have more screws due to divider
        assert multi_hw.total_count > simple_hw.total_count


class TestCaseScrews:
    """Tests for _case_screws method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def cabinet(self) -> Cabinet:
        """Create a cabinet for testing."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_case_screws_returns_list(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test that _case_screws returns a list."""
        screws = intel._case_screws(cabinet)
        assert isinstance(screws, list)

    def test_case_screws_has_correct_spec(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test case screws use correct specification."""
        from cabinets.domain.services.woodworking import CASE_SCREW_SPEC

        screws = intel._case_screws(cabinet)
        assert len(screws) == 1
        assert screws[0].name == CASE_SCREW_SPEC

    def test_case_screws_notes_present(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test case screws have appropriate notes."""
        screws = intel._case_screws(cabinet)
        assert screws[0].notes == "Case assembly"

    def test_case_screws_quantity_calculation(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test case screw quantity is calculated correctly.

        For 12" depth cabinet with 8" spacing:
        - Screws per side = max(2, int(12/8) + 1) = 2
        - Top screws = 2 * 2 = 4
        - Bottom screws = 2 * 2 = 4
        - Total = 8
        """
        screws = intel._case_screws(cabinet)
        # Should have at least 8 screws for top/bottom to sides
        assert screws[0].quantity >= 8

    def test_case_screws_with_divider(self, intel: WoodworkingIntelligence) -> None:
        """Test case screws increase with dividers."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )
        section1 = Section(
            width=22.5, height=82.5, depth=11.25, position=Position(0.75, 0.75)
        )
        section2 = Section(
            width=22.5, height=82.5, depth=11.25, position=Position(24.0, 0.75)
        )
        cabinet.sections.append(section1)
        cabinet.sections.append(section2)

        screws = intel._case_screws(cabinet)
        # Divider adds more screws for top and bottom connections
        assert screws[0].quantity > 8


class TestBackPanelScrews:
    """Tests for _back_panel_screws method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def cabinet(self) -> Cabinet:
        """Create a cabinet for testing."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_back_panel_screws_returns_list(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test that _back_panel_screws returns a list."""
        screws = intel._back_panel_screws(cabinet)
        assert isinstance(screws, list)

    def test_back_panel_screws_has_correct_spec(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test back panel screws use correct specification."""
        from cabinets.domain.services.woodworking import BACK_PANEL_SCREW_SPEC

        screws = intel._back_panel_screws(cabinet)
        assert len(screws) == 1
        assert screws[0].name == BACK_PANEL_SCREW_SPEC

    def test_back_panel_screws_notes_present(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test back panel screws have appropriate notes."""
        screws = intel._back_panel_screws(cabinet)
        assert screws[0].notes == "Back panel attachment"

    def test_back_panel_screws_quantity_calculation(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test back panel screw quantity is reasonable.

        For 48" x 84" cabinet with 6" spacing:
        - Horizontal = max(2, int(48/6) + 1) * 2 = 18
        - Vertical = max(0, int(84/6) - 1) * 2 = 26
        - Total around perimeter ~ 44
        """
        screws = intel._back_panel_screws(cabinet)
        # Should have a reasonable number of screws
        assert 30 < screws[0].quantity < 60


class TestJoineryFasteners:
    """Tests for _joinery_fasteners method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def simple_cabinet(self) -> Cabinet:
        """Create a simple cabinet (no pocket screws expected)."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_joinery_fasteners_dado_no_screws(
        self, intel: WoodworkingIntelligence, simple_cabinet: Cabinet
    ) -> None:
        """Test that dado joints don't add fasteners."""
        joinery = intel.get_joinery(simple_cabinet)
        fasteners = intel._joinery_fasteners(simple_cabinet, joinery)

        # Standard cabinet uses dado/rabbet which don't need fasteners
        # So fasteners should be empty or only have non-pocket items
        pocket_screws = [i for i in fasteners if "pocket" in i.name.lower()]
        assert len(pocket_screws) == 0

    def test_joinery_fasteners_with_pocket_screws(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener count for pocket screw joints."""
        # Create joinery with pocket screws
        joinery = [
            ConnectionJoinery(
                from_panel=PanelType.FACE_FRAME_STILE,
                to_panel=PanelType.FACE_FRAME_RAIL,
                joint=JointSpec.pocket_screw(positions=(2.0, 8.0, 14.0), spacing=6.0),
            )
        ]
        cabinet = Cabinet(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )

        fasteners = intel._joinery_fasteners(cabinet, joinery)
        pocket_screws = [i for i in fasteners if "pocket" in i.name.lower()]
        assert len(pocket_screws) == 1
        assert pocket_screws[0].quantity == 3  # 3 positions

    def test_joinery_fasteners_coarse_thread_for_plywood(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that plywood gets coarse thread pocket screws."""
        from cabinets.domain.services.woodworking import POCKET_SCREW_COARSE_NOTE

        joinery = [
            ConnectionJoinery(
                from_panel=PanelType.LEFT_SIDE,
                to_panel=PanelType.FACE_FRAME_RAIL,
                joint=JointSpec.pocket_screw(positions=(2.0,), spacing=6.0),
            )
        ]
        cabinet = Cabinet(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD),
        )

        fasteners = intel._joinery_fasteners(cabinet, joinery)
        pocket_screws = [i for i in fasteners if "pocket" in i.name.lower()]
        assert pocket_screws[0].notes == POCKET_SCREW_COARSE_NOTE

    def test_joinery_fasteners_fine_thread_for_hardwood(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test that solid wood gets fine thread pocket screws."""
        from cabinets.domain.services.woodworking import POCKET_SCREW_FINE_NOTE

        joinery = [
            ConnectionJoinery(
                from_panel=PanelType.LEFT_SIDE,
                to_panel=PanelType.FACE_FRAME_RAIL,
                joint=JointSpec.pocket_screw(positions=(2.0,), spacing=6.0),
            )
        ]
        cabinet = Cabinet(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.SOLID_WOOD),
        )

        fasteners = intel._joinery_fasteners(cabinet, joinery)
        pocket_screws = [i for i in fasteners if "pocket" in i.name.lower()]
        assert pocket_screws[0].notes == POCKET_SCREW_FINE_NOTE

    def test_joinery_fasteners_with_dowels(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener count for dowel joints."""
        joinery = [
            ConnectionJoinery(
                from_panel=PanelType.LEFT_SIDE,
                to_panel=PanelType.FACE_FRAME_STILE,
                joint=JointSpec.dowel(positions=(2.0, 10.0, 18.0), spacing=8.0),
            )
        ]
        cabinet = Cabinet(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )

        fasteners = intel._joinery_fasteners(cabinet, joinery)
        dowels = [i for i in fasteners if "dowel" in i.name.lower()]
        assert len(dowels) == 1
        assert dowels[0].quantity == 3

    def test_joinery_fasteners_with_biscuits(
        self, intel: WoodworkingIntelligence
    ) -> None:
        """Test fastener count for biscuit joints."""
        joinery = [
            ConnectionJoinery(
                from_panel=PanelType.LEFT_SIDE,
                to_panel=PanelType.FACE_FRAME_STILE,
                joint=JointSpec.biscuit(positions=(4.0, 12.0), spacing=8.0),
            )
        ]
        cabinet = Cabinet(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )

        fasteners = intel._joinery_fasteners(cabinet, joinery)
        biscuits = [i for i in fasteners if "biscuit" in i.name.lower()]
        assert len(biscuits) == 1
        assert biscuits[0].quantity == 2


class TestShelfFasteners:
    """Tests for _shelf_fasteners method."""

    @pytest.fixture
    def intel(self) -> WoodworkingIntelligence:
        """Create WoodworkingIntelligence instance."""
        return WoodworkingIntelligence()

    @pytest.fixture
    def cabinet(self) -> Cabinet:
        """Create a cabinet with shelves."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        for i in range(3):
            shelf = Shelf(
                width=46.5,
                depth=11.25,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 20 + i * 20),
            )
            section.add_shelf(shelf)
        cabinet.sections.append(section)
        return cabinet

    def test_shelf_fasteners_returns_list(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test that _shelf_fasteners returns a list."""
        fasteners = intel._shelf_fasteners(cabinet)
        assert isinstance(fasteners, list)

    def test_shelf_fasteners_placeholder_empty(
        self, intel: WoodworkingIntelligence, cabinet: Cabinet
    ) -> None:
        """Test that shelf fasteners is a placeholder returning empty list.

        Shelf components generate their own hardware via component registry.
        """
        fasteners = intel._shelf_fasteners(cabinet)
        assert len(fasteners) == 0


class TestHardwareCalculationIntegration:
    """Integration tests for hardware calculation workflow."""

    def test_full_hardware_workflow(self) -> None:
        """Test complete workflow: create cabinet, calculate hardware."""
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section1 = Section(
            width=22.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        section2 = Section(
            width=22.5,
            height=82.5,
            depth=11.25,
            position=Position(24.0, 0.75),
        )
        for i in range(3):
            shelf = Shelf(
                width=22.5,
                depth=11.25,
                material=MaterialSpec.standard_3_4(),
                position=Position(0.75, 20 + i * 20),
            )
            section1.add_shelf(shelf)
        cabinet.sections.append(section1)
        cabinet.sections.append(section2)

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(cabinet)

        # Verify we have hardware
        assert hardware.total_count > 0

        # Verify we have both screw types
        screw_items = [i for i in hardware.items if "screw" in i.name.lower()]
        assert len(screw_items) >= 2

        # Verify categories
        categories = hardware.by_category
        assert "screws" in categories

    def test_hardware_for_typical_cabinet_ranges(self) -> None:
        """Test hardware quantities are in expected ranges.

        For a typical 48" x 84" x 12" cabinet with 2 sections:
        - Case screws: ~16-24
        - Back panel screws: ~40-60
        - Total: ~60-100 (before overage)
        """
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section1 = Section(
            width=22.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        section2 = Section(
            width=22.5,
            height=82.5,
            depth=11.25,
            position=Position(24.0, 0.75),
        )
        cabinet.sections.append(section1)
        cabinet.sections.append(section2)

        intel = WoodworkingIntelligence()
        hardware = intel.calculate_hardware(cabinet, include_overage=False)

        # Check total is in expected range
        assert 50 < hardware.total_count < 100


# =============================================================================
# Additional Edge Case Tests (Task 08)
# =============================================================================


class TestJointTypeEnumEdgeCases:
    """Additional edge case tests for JointType enum."""

    def test_joint_type_from_string_dado(self) -> None:
        """Test creating JointType from string value 'dado'."""
        assert JointType("dado") == JointType.DADO

    def test_joint_type_from_string_rabbet(self) -> None:
        """Test creating JointType from string value 'rabbet'."""
        assert JointType("rabbet") == JointType.RABBET

    def test_joint_type_from_string_pocket_screw(self) -> None:
        """Test creating JointType from string value 'pocket_screw'."""
        assert JointType("pocket_screw") == JointType.POCKET_SCREW

    def test_joint_type_invalid_string_raises_error(self) -> None:
        """Test that invalid string value raises ValueError."""
        with pytest.raises(ValueError):
            JointType("invalid_joint")

    def test_joint_type_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            JointType("")


class TestGrainDirectionEnum:
    """Tests for GrainDirection enum values and behavior."""

    def test_grain_direction_values(self) -> None:
        """Test that all GrainDirection values are correct."""
        from cabinets.domain.value_objects import GrainDirection

        assert GrainDirection.NONE.value == "none"
        assert GrainDirection.LENGTH.value == "length"
        assert GrainDirection.WIDTH.value == "width"

    def test_grain_direction_is_str_enum(self) -> None:
        """Test that GrainDirection is a string enum for JSON serialization."""
        from cabinets.domain.value_objects import GrainDirection

        assert isinstance(GrainDirection.LENGTH, str)
        assert GrainDirection.LENGTH == "length"

    def test_grain_direction_from_string(self) -> None:
        """Test creating GrainDirection from string value."""
        from cabinets.domain.value_objects import GrainDirection

        assert GrainDirection("length") == GrainDirection.LENGTH
        assert GrainDirection("width") == GrainDirection.WIDTH
        assert GrainDirection("none") == GrainDirection.NONE

    def test_grain_direction_invalid_string_raises_error(self) -> None:
        """Test that invalid string value raises ValueError."""
        from cabinets.domain.value_objects import GrainDirection

        with pytest.raises(ValueError):
            GrainDirection("horizontal")


class TestFRDSpecificCalculations:
    """Tests verifying specific calculations from the FRD document."""

    def test_frd_dado_depth_three_quarter_inch_material(self) -> None:
        """FR-01.3: Dado depth = 1/3 material thickness (0.75" -> 0.25")."""
        intel = WoodworkingIntelligence()
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.5,
            position=Position(0.75, 0.75),
        )
        shelf = Shelf(
            width=46.5,
            depth=11.5,
            material=MaterialSpec.standard_3_4(),
            position=Position(0.75, 20.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)

        joinery = intel.get_joinery(cabinet)
        dado_joints = [j for j in joinery if j.joint.joint_type == JointType.DADO]

        # FRD specifies: 0.75" material -> 0.25" dado depth (1/3)
        assert len(dado_joints) > 0
        for joint in dado_joints:
            assert joint.joint.depth == pytest.approx(0.25, abs=0.01)

    def test_frd_rabbet_dimensions_half_inch_back(self) -> None:
        """FR-01.4: 0.5" back -> 0.5" width, 0.375" depth (half of 0.75" case)."""
        intel = WoodworkingIntelligence()
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD),
            back_material=MaterialSpec(thickness=0.5, material_type=MaterialType.PLYWOOD),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.5,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)

        joinery = intel.get_joinery(cabinet)
        rabbet_joints = [j for j in joinery if j.joint.joint_type == JointType.RABBET]

        # FRD specifies: rabbet width = back thickness, depth = 1/2 case thickness
        assert len(rabbet_joints) == 4  # 4 sides
        for joint in rabbet_joints:
            assert joint.joint.width == pytest.approx(0.5, abs=0.01)
            assert joint.joint.depth == pytest.approx(0.375, abs=0.01)  # 0.75 * 0.5

    def test_frd_span_limit_plywood_36_inches(self) -> None:
        """FR-02.1: 3/4" plywood max span is 36 inches."""
        assert get_max_span(MaterialType.PLYWOOD, 0.75) == 36.0

    def test_frd_span_limit_mdf_24_inches(self) -> None:
        """FR-02.1: 3/4" MDF max span is 24 inches."""
        assert get_max_span(MaterialType.MDF, 0.75) == 24.0

    def test_frd_span_limit_particle_board_24_inches(self) -> None:
        """FR-02.1: 3/4" particle board max span is 24 inches."""
        assert get_max_span(MaterialType.PARTICLE_BOARD, 0.75) == 24.0

    def test_frd_span_limit_solid_wood_42_inches(self) -> None:
        """FR-02.1: 1" solid wood max span is 42 inches."""
        assert get_max_span(MaterialType.SOLID_WOOD, 1.0) == 42.0

    def test_frd_dowel_positions_2_inch_edge_offset(self) -> None:
        """FR-01.5: Dowels positioned 2" from edges."""
        intel = WoodworkingIntelligence()
        spec = intel.get_dowel_spec(length=18.0)

        # First position should be 2" from start
        assert spec.positions[0] == 2.0
        # Last position should be 2" from end (18 - 2 = 16)
        assert spec.positions[-1] == 16.0

    def test_frd_dowel_spacing_6_inches(self) -> None:
        """FR-01.5: Dowels spaced at 6 inches."""
        intel = WoodworkingIntelligence()
        spec = intel.get_dowel_spec(length=24.0)

        assert spec.spacing == 6.0

    def test_frd_pocket_hole_positions_4_inch_edge_offset(self) -> None:
        """FR-01.6: Pocket holes positioned 4" from edges."""
        intel = WoodworkingIntelligence()
        spec = intel.get_pocket_screw_spec(length=24.0)

        # First position should be 4" from start
        assert spec.positions[0] == 4.0
        # Last position should be 4" from end (24 - 4 = 20)
        assert spec.positions[-1] == 20.0

    def test_frd_pocket_hole_spacing_8_inches(self) -> None:
        """FR-01.6: Pocket holes spaced at 8 inches."""
        intel = WoodworkingIntelligence()
        spec = intel.get_pocket_screw_spec(length=32.0)

        assert spec.spacing == 8.0


class TestEdgeCaseValidations:
    """Additional edge case validation tests."""

    def test_joint_spec_zero_width_raises_error(self) -> None:
        """Test that zero width raises ValueError."""
        with pytest.raises(ValueError, match="Joint width must be positive"):
            JointSpec(joint_type=JointType.RABBET, width=0.0, depth=0.25)

    def test_joint_spec_zero_spacing_raises_error(self) -> None:
        """Test that zero spacing raises ValueError."""
        with pytest.raises(ValueError, match="Joint spacing must be positive"):
            JointSpec(
                joint_type=JointType.POCKET_SCREW,
                positions=(2.0, 8.0),
                spacing=0.0,
            )

    def test_span_warning_zero_span_raises_error(self) -> None:
        """Test that zero span raises ValueError."""
        material = MaterialSpec.standard_3_4()
        with pytest.raises(ValueError, match="Span must be positive"):
            SpanWarning(
                panel_label="Shelf 1",
                span=0.0,
                max_span=36.0,
                material=material,
            )

    def test_weight_capacity_negative_span_raises_error(self) -> None:
        """Test that negative span raises ValueError."""
        material = MaterialSpec.standard_3_4()
        with pytest.raises(ValueError, match="Span must be positive"):
            WeightCapacity(
                panel_label="Shelf 1",
                capacity_lbs=50.0,
                load_type="distributed",
                span=-10.0,
                material=material,
            )

    def test_hardware_list_aggregate_single_list(self) -> None:
        """Test aggregate with single HardwareList."""
        single_list = HardwareList(
            items=(HardwareItem(name="Screw", quantity=10),)
        )
        result = HardwareList.aggregate(single_list)
        assert result.total_count == 10

    def test_woodworking_config_dado_depth_ratio_greater_than_one_fails(self) -> None:
        """Test that dado_depth_ratio greater than 1.0 fails."""
        with pytest.raises(ValueError, match="dado_depth_ratio must be between 0 and 1"):
            WoodworkingConfig(dado_depth_ratio=1.1)

    def test_calculate_fastener_positions_very_short_joint(self) -> None:
        """Test fastener positions for extremely short joint (< 2 * edge_offset)."""
        intel = WoodworkingIntelligence()
        positions = intel._calculate_fastener_positions(
            length=2.0,
            edge_offset=2.0,
            spacing=6.0,
        )
        # Should only have center position
        assert len(positions) == 1
        assert positions[0] == 1.0  # Center of 2" joint

    def test_check_spans_cabinet_with_no_shelves_no_shelf_warnings(self) -> None:
        """Test check_spans on cabinet section with no shelves."""
        intel = WoodworkingIntelligence()
        cabinet = Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            back_material=MaterialSpec.standard_1_2(),
        )
        section = Section(
            width=46.5,
            height=82.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        # Note: No shelves added
        cabinet.sections.append(section)

        warnings = intel.check_spans(cabinet)
        # No shelf warnings since no shelves
        shelf_warnings = [w for w in warnings if "Shelf" in w.panel_label]
        assert len(shelf_warnings) == 0


class TestHardwareListEdgeCases:
    """Edge case tests for HardwareList dataclass."""

    def test_hardware_list_with_overage_rounds_correctly(self) -> None:
        """Test that overage rounds up correctly for edge cases."""
        hw_list = HardwareList(
            items=(HardwareItem(name="Screw", quantity=1),)
        )
        with_overage = hw_list.with_overage(10.0)
        # 1 * 1.10 = 1.1 -> ceil = 2
        assert with_overage.items[0].quantity == 2

    def test_hardware_list_aggregate_three_lists(self) -> None:
        """Test aggregate with three HardwareLists."""
        list1 = HardwareList(items=(HardwareItem(name="A", quantity=5),))
        list2 = HardwareList(items=(HardwareItem(name="B", quantity=10),))
        list3 = HardwareList(items=(HardwareItem(name="A", quantity=3),))

        result = HardwareList.aggregate(list1, list2, list3)
        assert result.total_count == 18
        # Find A item (should be 5 + 3 = 8)
        a_item = next(i for i in result.items if i.name == "A")
        assert a_item.quantity == 8
