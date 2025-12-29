"""Unit tests for installation support data models and services."""

import pytest

from cabinets.domain.entities import Cabinet, Section, Shelf
from cabinets.domain.services.installation import (
    CleatSpec,
    InstallationConfig,
    InstallationPlan,
    InstallationService,
    StudHitAnalysis,
    WeightEstimate,
)
from cabinets.domain.value_objects import (
    LoadCategory,
    MaterialSpec,
    MaterialType,
    MountingSystem,
    Position,
    WallType,
)


class TestInstallationConfig:
    """Tests for InstallationConfig dataclass."""

    def test_default_values(self) -> None:
        """Test InstallationConfig has correct default values."""
        config = InstallationConfig()
        assert config.wall_type == WallType.DRYWALL
        assert config.wall_thickness == 0.5
        assert config.stud_spacing == 16.0
        assert config.stud_offset == 0.0
        assert config.mounting_system == MountingSystem.DIRECT_TO_STUD
        assert config.expected_load == LoadCategory.MEDIUM
        assert config.cleat_position_from_top == 4.0
        assert config.cleat_width_percentage == 90.0
        assert config.cleat_bevel_angle == 45.0

    def test_custom_values(self) -> None:
        """Test InstallationConfig with custom values."""
        config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            wall_thickness=0.75,
            stud_spacing=24.0,
            stud_offset=8.0,
            mounting_system=MountingSystem.FRENCH_CLEAT,
            expected_load=LoadCategory.HEAVY,
            cleat_position_from_top=6.0,
            cleat_width_percentage=80.0,
            cleat_bevel_angle=30.0,
        )
        assert config.wall_type == WallType.CONCRETE
        assert config.wall_thickness == 0.75
        assert config.stud_spacing == 24.0
        assert config.stud_offset == 8.0
        assert config.mounting_system == MountingSystem.FRENCH_CLEAT
        assert config.expected_load == LoadCategory.HEAVY
        assert config.cleat_position_from_top == 6.0
        assert config.cleat_width_percentage == 80.0
        assert config.cleat_bevel_angle == 30.0

    def test_negative_wall_thickness_raises_error(self) -> None:
        """Test that negative wall thickness raises ValueError."""
        with pytest.raises(ValueError, match="Wall thickness must be positive"):
            InstallationConfig(wall_thickness=-0.5)

    def test_zero_wall_thickness_raises_error(self) -> None:
        """Test that zero wall thickness raises ValueError."""
        with pytest.raises(ValueError, match="Wall thickness must be positive"):
            InstallationConfig(wall_thickness=0)

    def test_negative_stud_spacing_raises_error(self) -> None:
        """Test that negative stud spacing raises ValueError."""
        with pytest.raises(ValueError, match="Stud spacing must be positive"):
            InstallationConfig(stud_spacing=-16.0)

    def test_zero_stud_spacing_raises_error(self) -> None:
        """Test that zero stud spacing raises ValueError."""
        with pytest.raises(ValueError, match="Stud spacing must be positive"):
            InstallationConfig(stud_spacing=0)

    def test_negative_stud_offset_raises_error(self) -> None:
        """Test that negative stud offset raises ValueError."""
        with pytest.raises(ValueError, match="Stud offset must be non-negative"):
            InstallationConfig(stud_offset=-1.0)

    def test_zero_stud_offset_is_valid(self) -> None:
        """Test that zero stud offset is valid."""
        config = InstallationConfig(stud_offset=0.0)
        assert config.stud_offset == 0.0

    def test_negative_cleat_position_raises_error(self) -> None:
        """Test that negative cleat position raises ValueError."""
        with pytest.raises(
            ValueError, match="Cleat position from top must be non-negative"
        ):
            InstallationConfig(cleat_position_from_top=-1.0)

    def test_cleat_width_percentage_below_zero_raises_error(self) -> None:
        """Test that cleat width percentage <= 0 raises ValueError."""
        with pytest.raises(
            ValueError, match="Cleat width percentage must be between 0 and 100"
        ):
            InstallationConfig(cleat_width_percentage=0)

    def test_cleat_width_percentage_above_100_raises_error(self) -> None:
        """Test that cleat width percentage > 100 raises ValueError."""
        with pytest.raises(
            ValueError, match="Cleat width percentage must be between 0 and 100"
        ):
            InstallationConfig(cleat_width_percentage=101)

    def test_cleat_bevel_angle_at_zero_raises_error(self) -> None:
        """Test that cleat bevel angle at 0 raises ValueError."""
        with pytest.raises(
            ValueError, match="Cleat bevel angle must be between 0 and 90 degrees"
        ):
            InstallationConfig(cleat_bevel_angle=0)

    def test_cleat_bevel_angle_at_90_raises_error(self) -> None:
        """Test that cleat bevel angle at 90 raises ValueError."""
        with pytest.raises(
            ValueError, match="Cleat bevel angle must be between 0 and 90 degrees"
        ):
            InstallationConfig(cleat_bevel_angle=90)

    def test_config_is_frozen(self) -> None:
        """Test that InstallationConfig is immutable."""
        config = InstallationConfig()
        with pytest.raises(AttributeError):
            config.wall_type = WallType.CONCRETE  # type: ignore


class TestCleatSpec:
    """Tests for CleatSpec dataclass."""

    def test_valid_wall_cleat(self) -> None:
        """Test creating a valid wall cleat specification."""
        cleat = CleatSpec(
            width=36.0,
            height=3.0,
            thickness=0.75,
            bevel_angle=45.0,
            is_wall_cleat=True,
        )
        assert cleat.width == 36.0
        assert cleat.height == 3.0
        assert cleat.thickness == 0.75
        assert cleat.bevel_angle == 45.0
        assert cleat.is_wall_cleat is True

    def test_valid_cabinet_cleat(self) -> None:
        """Test creating a valid cabinet cleat specification."""
        cleat = CleatSpec(
            width=36.0,
            height=3.0,
            thickness=0.75,
            bevel_angle=45.0,
            is_wall_cleat=False,
        )
        assert cleat.is_wall_cleat is False

    def test_cleat_label_wall(self) -> None:
        """Test wall cleat label generation."""
        cleat = CleatSpec(
            width=36.0,
            height=3.0,
            thickness=0.75,
            bevel_angle=45.0,
            is_wall_cleat=True,
        )
        assert cleat.label == "French Wall Cleat"

    def test_cleat_label_cabinet(self) -> None:
        """Test cabinet cleat label generation."""
        cleat = CleatSpec(
            width=36.0,
            height=3.0,
            thickness=0.75,
            bevel_angle=45.0,
            is_wall_cleat=False,
        )
        assert cleat.label == "French Cabinet Cleat"

    def test_negative_width_raises_error(self) -> None:
        """Test that negative width raises ValueError."""
        with pytest.raises(ValueError, match="Cleat width must be positive"):
            CleatSpec(
                width=-36.0,
                height=3.0,
                thickness=0.75,
                bevel_angle=45.0,
                is_wall_cleat=True,
            )

    def test_zero_width_raises_error(self) -> None:
        """Test that zero width raises ValueError."""
        with pytest.raises(ValueError, match="Cleat width must be positive"):
            CleatSpec(
                width=0,
                height=3.0,
                thickness=0.75,
                bevel_angle=45.0,
                is_wall_cleat=True,
            )

    def test_negative_height_raises_error(self) -> None:
        """Test that negative height raises ValueError."""
        with pytest.raises(ValueError, match="Cleat height must be positive"):
            CleatSpec(
                width=36.0,
                height=-3.0,
                thickness=0.75,
                bevel_angle=45.0,
                is_wall_cleat=True,
            )

    def test_negative_thickness_raises_error(self) -> None:
        """Test that negative thickness raises ValueError."""
        with pytest.raises(ValueError, match="Cleat thickness must be positive"):
            CleatSpec(
                width=36.0,
                height=3.0,
                thickness=-0.75,
                bevel_angle=45.0,
                is_wall_cleat=True,
            )

    def test_bevel_angle_at_zero_raises_error(self) -> None:
        """Test that bevel angle at 0 raises ValueError."""
        with pytest.raises(
            ValueError, match="Bevel angle must be between 0 and 90 degrees"
        ):
            CleatSpec(
                width=36.0,
                height=3.0,
                thickness=0.75,
                bevel_angle=0,
                is_wall_cleat=True,
            )

    def test_bevel_angle_at_90_raises_error(self) -> None:
        """Test that bevel angle at 90 raises ValueError."""
        with pytest.raises(
            ValueError, match="Bevel angle must be between 0 and 90 degrees"
        ):
            CleatSpec(
                width=36.0,
                height=3.0,
                thickness=0.75,
                bevel_angle=90,
                is_wall_cleat=True,
            )

    def test_cleat_is_frozen(self) -> None:
        """Test that CleatSpec is immutable."""
        cleat = CleatSpec(
            width=36.0,
            height=3.0,
            thickness=0.75,
            bevel_angle=45.0,
            is_wall_cleat=True,
        )
        with pytest.raises(AttributeError):
            cleat.width = 48.0  # type: ignore


class TestStudHitAnalysis:
    """Tests for StudHitAnalysis dataclass."""

    def test_valid_stud_hit_analysis(self) -> None:
        """Test creating a valid stud hit analysis."""
        analysis = StudHitAnalysis(
            cabinet_left_edge=12.0,
            cabinet_width=48.0,
            stud_positions=(16.0, 32.0, 48.0),
            non_stud_positions=(8.0, 24.0),
            stud_hit_count=3,
            recommendation="Good stud alignment",
        )
        assert analysis.cabinet_left_edge == 12.0
        assert analysis.cabinet_width == 48.0
        assert analysis.stud_positions == (16.0, 32.0, 48.0)
        assert analysis.non_stud_positions == (8.0, 24.0)
        assert analysis.stud_hit_count == 3
        assert analysis.recommendation == "Good stud alignment"

    def test_stud_hit_analysis_no_recommendation(self) -> None:
        """Test stud hit analysis with default recommendation."""
        analysis = StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=36.0,
            stud_positions=(16.0,),
            non_stud_positions=(),
            stud_hit_count=1,
        )
        assert analysis.recommendation is None

    def test_total_mounting_points(self) -> None:
        """Test total mounting points calculation."""
        analysis = StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=48.0,
            stud_positions=(16.0, 32.0),
            non_stud_positions=(8.0, 24.0, 40.0),
            stud_hit_count=2,
        )
        assert analysis.total_mounting_points == 5

    def test_hit_percentage(self) -> None:
        """Test hit percentage calculation."""
        analysis = StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=48.0,
            stud_positions=(16.0, 32.0),
            non_stud_positions=(8.0, 24.0),
            stud_hit_count=2,
        )
        # 2 out of 4 = 50%
        assert analysis.hit_percentage == 50.0

    def test_hit_percentage_zero_points(self) -> None:
        """Test hit percentage with zero mounting points."""
        analysis = StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=24.0,
            stud_positions=(),
            non_stud_positions=(),
            stud_hit_count=0,
        )
        assert analysis.hit_percentage == 0.0

    def test_negative_cabinet_width_raises_error(self) -> None:
        """Test that negative cabinet width raises ValueError."""
        with pytest.raises(ValueError, match="Cabinet width must be positive"):
            StudHitAnalysis(
                cabinet_left_edge=0.0,
                cabinet_width=-48.0,
                stud_positions=(),
                non_stud_positions=(),
                stud_hit_count=0,
            )

    def test_negative_stud_hit_count_raises_error(self) -> None:
        """Test that negative stud hit count raises ValueError."""
        with pytest.raises(ValueError, match="Stud hit count must be non-negative"):
            StudHitAnalysis(
                cabinet_left_edge=0.0,
                cabinet_width=48.0,
                stud_positions=(),
                non_stud_positions=(),
                stud_hit_count=-1,
            )

    def test_stud_hit_count_exceeds_positions_raises_error(self) -> None:
        """Test that stud hit count exceeding positions raises ValueError."""
        with pytest.raises(
            ValueError, match="Stud hit count cannot exceed number of stud positions"
        ):
            StudHitAnalysis(
                cabinet_left_edge=0.0,
                cabinet_width=48.0,
                stud_positions=(16.0,),
                non_stud_positions=(),
                stud_hit_count=2,
            )

    def test_stud_hit_analysis_is_frozen(self) -> None:
        """Test that StudHitAnalysis is immutable."""
        analysis = StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=48.0,
            stud_positions=(),
            non_stud_positions=(),
            stud_hit_count=0,
        )
        with pytest.raises(AttributeError):
            analysis.cabinet_width = 60.0  # type: ignore


class TestWeightEstimate:
    """Tests for WeightEstimate dataclass."""

    def test_valid_weight_estimate(self) -> None:
        """Test creating a valid weight estimate."""
        estimate = WeightEstimate(
            empty_weight_lbs=45.0,
            expected_load_per_foot=30.0,
            total_estimated_load_lbs=165.0,
        )
        assert estimate.empty_weight_lbs == 45.0
        assert estimate.expected_load_per_foot == 30.0
        assert estimate.total_estimated_load_lbs == 165.0
        assert estimate.capacity_warning is None

    def test_weight_estimate_with_warning(self) -> None:
        """Test weight estimate with capacity warning."""
        estimate = WeightEstimate(
            empty_weight_lbs=85.0,
            expected_load_per_foot=50.0,
            total_estimated_load_lbs=285.0,
            capacity_warning="Heavy load - ensure proper stud mounting",
        )
        assert estimate.capacity_warning == "Heavy load - ensure proper stud mounting"

    def test_weight_estimate_disclaimer(self) -> None:
        """Test that weight estimate includes disclaimer."""
        estimate = WeightEstimate(
            empty_weight_lbs=45.0,
            expected_load_per_foot=30.0,
            total_estimated_load_lbs=165.0,
        )
        assert "advisory only" in estimate.disclaimer.lower()
        assert "wall construction" in estimate.disclaimer.lower()

    def test_formatted_summary(self) -> None:
        """Test formatted summary generation."""
        estimate = WeightEstimate(
            empty_weight_lbs=45.0,
            expected_load_per_foot=30.0,
            total_estimated_load_lbs=165.0,
        )
        summary = estimate.formatted_summary
        assert "45.0 lbs" in summary
        assert "30.0 lbs/ft" in summary
        assert "165.0 lbs" in summary

    def test_formatted_summary_with_warning(self) -> None:
        """Test formatted summary includes warning."""
        estimate = WeightEstimate(
            empty_weight_lbs=85.0,
            expected_load_per_foot=50.0,
            total_estimated_load_lbs=285.0,
            capacity_warning="Heavy load",
        )
        summary = estimate.formatted_summary
        assert "WARNING" in summary
        assert "Heavy load" in summary

    def test_negative_empty_weight_raises_error(self) -> None:
        """Test that negative empty weight raises ValueError."""
        with pytest.raises(ValueError, match="Empty weight must be non-negative"):
            WeightEstimate(
                empty_weight_lbs=-10.0,
                expected_load_per_foot=30.0,
                total_estimated_load_lbs=165.0,
            )

    def test_negative_load_per_foot_raises_error(self) -> None:
        """Test that negative load per foot raises ValueError."""
        with pytest.raises(
            ValueError, match="Expected load per foot must be non-negative"
        ):
            WeightEstimate(
                empty_weight_lbs=45.0,
                expected_load_per_foot=-30.0,
                total_estimated_load_lbs=165.0,
            )

    def test_negative_total_load_raises_error(self) -> None:
        """Test that negative total load raises ValueError."""
        with pytest.raises(
            ValueError, match="Total estimated load must be non-negative"
        ):
            WeightEstimate(
                empty_weight_lbs=45.0,
                expected_load_per_foot=30.0,
                total_estimated_load_lbs=-165.0,
            )

    def test_zero_values_are_valid(self) -> None:
        """Test that zero values are valid for weight estimate."""
        estimate = WeightEstimate(
            empty_weight_lbs=0.0,
            expected_load_per_foot=0.0,
            total_estimated_load_lbs=0.0,
        )
        assert estimate.empty_weight_lbs == 0.0
        assert estimate.expected_load_per_foot == 0.0
        assert estimate.total_estimated_load_lbs == 0.0

    def test_weight_estimate_is_frozen(self) -> None:
        """Test that WeightEstimate is immutable."""
        estimate = WeightEstimate(
            empty_weight_lbs=45.0,
            expected_load_per_foot=30.0,
            total_estimated_load_lbs=165.0,
        )
        with pytest.raises(AttributeError):
            estimate.empty_weight_lbs = 50.0  # type: ignore


class TestInstallationPlan:
    """Tests for InstallationPlan dataclass."""

    @pytest.fixture
    def sample_stud_analysis(self) -> StudHitAnalysis:
        """Create a sample stud hit analysis."""
        return StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=48.0,
            stud_positions=(16.0, 32.0),
            non_stud_positions=(),
            stud_hit_count=2,
        )

    @pytest.fixture
    def sample_weight_estimate(self) -> WeightEstimate:
        """Create a sample weight estimate."""
        return WeightEstimate(
            empty_weight_lbs=45.0,
            expected_load_per_foot=30.0,
            total_estimated_load_lbs=165.0,
        )

    def test_valid_installation_plan(
        self,
        sample_stud_analysis: StudHitAnalysis,
        sample_weight_estimate: WeightEstimate,
    ) -> None:
        """Test creating a valid installation plan."""
        plan = InstallationPlan(
            mounting_hardware=(),
            cleat_cut_pieces=(),
            stud_analysis=sample_stud_analysis,
            weight_estimate=sample_weight_estimate,
            instructions="## Installation\n\nStep 1: ...",
            warnings=(),
        )
        assert plan.mounting_hardware == ()
        assert plan.cleat_cut_pieces == ()
        assert plan.stud_analysis == sample_stud_analysis
        assert plan.weight_estimate == sample_weight_estimate
        assert "Installation" in plan.instructions
        assert plan.warnings == ()

    def test_has_warnings_false(
        self,
        sample_stud_analysis: StudHitAnalysis,
        sample_weight_estimate: WeightEstimate,
    ) -> None:
        """Test has_warnings property when no warnings."""
        plan = InstallationPlan(
            mounting_hardware=(),
            cleat_cut_pieces=(),
            stud_analysis=sample_stud_analysis,
            weight_estimate=sample_weight_estimate,
            instructions="",
            warnings=(),
        )
        assert plan.has_warnings is False

    def test_has_warnings_true(
        self,
        sample_stud_analysis: StudHitAnalysis,
        sample_weight_estimate: WeightEstimate,
    ) -> None:
        """Test has_warnings property when warnings present."""
        plan = InstallationPlan(
            mounting_hardware=(),
            cleat_cut_pieces=(),
            stud_analysis=sample_stud_analysis,
            weight_estimate=sample_weight_estimate,
            instructions="",
            warnings=("Warning 1", "Warning 2"),
        )
        assert plan.has_warnings is True

    def test_uses_cleats_false(
        self,
        sample_stud_analysis: StudHitAnalysis,
        sample_weight_estimate: WeightEstimate,
    ) -> None:
        """Test uses_cleats property when no cleats."""
        plan = InstallationPlan(
            mounting_hardware=(),
            cleat_cut_pieces=(),
            stud_analysis=sample_stud_analysis,
            weight_estimate=sample_weight_estimate,
            instructions="",
            warnings=(),
        )
        assert plan.uses_cleats is False

    def test_hardware_count(
        self,
        sample_stud_analysis: StudHitAnalysis,
        sample_weight_estimate: WeightEstimate,
    ) -> None:
        """Test hardware count calculation."""
        from cabinets.domain.components.results import HardwareItem

        hardware = (
            HardwareItem(name="Cabinet screw", quantity=8),
            HardwareItem(name="Toggle bolt", quantity=2),
        )
        plan = InstallationPlan(
            mounting_hardware=hardware,
            cleat_cut_pieces=(),
            stud_analysis=sample_stud_analysis,
            weight_estimate=sample_weight_estimate,
            instructions="",
            warnings=(),
        )
        assert plan.hardware_count == 10


class TestInstallationService:
    """Tests for InstallationService class."""

    @pytest.fixture
    def default_config(self) -> InstallationConfig:
        """Create a default installation configuration."""
        return InstallationConfig()

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        # Create a section with proper parameters
        section = Section(
            width=46.5,
            height=28.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        # Add a shelf to the section
        shelf = Shelf(
            width=46.5,
            depth=11.25,
            material=material,
            position=Position(0.75, 15.0),
        )
        section.add_shelf(shelf)
        cabinet.sections.append(section)
        return cabinet

    def test_service_instantiation(self, default_config: InstallationConfig) -> None:
        """Test that InstallationService can be instantiated."""
        service = InstallationService(default_config)
        assert service.config == default_config

    def test_service_with_custom_config(self) -> None:
        """Test InstallationService with custom configuration."""
        config = InstallationConfig(
            wall_type=WallType.PLASTER,
            mounting_system=MountingSystem.FRENCH_CLEAT,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        assert service.config.wall_type == WallType.PLASTER
        assert service.config.mounting_system == MountingSystem.FRENCH_CLEAT
        assert service.config.expected_load == LoadCategory.HEAVY

    def test_material_densities_defined(
        self, default_config: InstallationConfig
    ) -> None:
        """Test that MATERIAL_DENSITIES constant is defined."""
        service = InstallationService(default_config)
        assert hasattr(service, "MATERIAL_DENSITIES")
        assert MaterialType.PLYWOOD in service.MATERIAL_DENSITIES
        assert MaterialType.MDF in service.MATERIAL_DENSITIES
        assert MaterialType.PARTICLE_BOARD in service.MATERIAL_DENSITIES
        assert MaterialType.SOLID_WOOD in service.MATERIAL_DENSITIES

    def test_material_densities_values(
        self, default_config: InstallationConfig
    ) -> None:
        """Test that MATERIAL_DENSITIES values are reasonable."""
        service = InstallationService(default_config)
        for material_type, density in service.MATERIAL_DENSITIES.items():
            assert density > 0, f"{material_type} has non-positive density"

    def test_load_ratings_defined(self, default_config: InstallationConfig) -> None:
        """Test that LOAD_RATINGS constant is defined."""
        service = InstallationService(default_config)
        assert hasattr(service, "LOAD_RATINGS")
        assert LoadCategory.LIGHT in service.LOAD_RATINGS
        assert LoadCategory.MEDIUM in service.LOAD_RATINGS
        assert LoadCategory.HEAVY in service.LOAD_RATINGS

    def test_load_ratings_values(self, default_config: InstallationConfig) -> None:
        """Test that LOAD_RATINGS values follow expected order."""
        service = InstallationService(default_config)
        light = service.LOAD_RATINGS[LoadCategory.LIGHT]
        medium = service.LOAD_RATINGS[LoadCategory.MEDIUM]
        heavy = service.LOAD_RATINGS[LoadCategory.HEAVY]
        assert light < medium < heavy
        assert light == 15.0
        assert medium == 30.0
        assert heavy == 50.0

    def test_safety_factor_defined(self, default_config: InstallationConfig) -> None:
        """Test that SAFETY_FACTOR constant is defined."""
        service = InstallationService(default_config)
        assert hasattr(service, "SAFETY_FACTOR")
        assert service.SAFETY_FACTOR == 4.0

    def test_calculate_stud_hits_returns_analysis(
        self, default_config: InstallationConfig, sample_cabinet: Cabinet
    ) -> None:
        """Test that calculate_stud_hits returns StudHitAnalysis."""
        service = InstallationService(default_config)
        analysis = service.calculate_stud_hits(sample_cabinet, left_edge=0.0)
        assert isinstance(analysis, StudHitAnalysis)
        assert analysis.cabinet_width == sample_cabinet.width

    def test_estimate_weight_returns_estimate(
        self, default_config: InstallationConfig, sample_cabinet: Cabinet
    ) -> None:
        """Test that estimate_weight returns WeightEstimate."""
        service = InstallationService(default_config)
        estimate = service.estimate_weight(sample_cabinet)
        assert isinstance(estimate, WeightEstimate)

    def test_estimate_weight_uses_load_rating(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that estimate_weight uses configured load rating."""
        config = InstallationConfig(expected_load=LoadCategory.HEAVY)
        service = InstallationService(config)
        estimate = service.estimate_weight(sample_cabinet)
        assert estimate.expected_load_per_foot == 50.0  # HEAVY rating

    def test_generate_cleats_returns_list(
        self, default_config: InstallationConfig, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_cleats returns a list."""
        service = InstallationService(default_config)
        cleats = service.generate_cleats(sample_cabinet)
        assert isinstance(cleats, list)

    def test_generate_hardware_returns_list(
        self, default_config: InstallationConfig, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_hardware returns a list."""
        service = InstallationService(default_config)
        analysis = service.calculate_stud_hits(sample_cabinet, left_edge=0.0)
        hardware = service.generate_hardware(sample_cabinet, analysis)
        assert isinstance(hardware, list)

    def test_generate_instructions_returns_markdown(
        self, default_config: InstallationConfig, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_instructions returns markdown string."""
        service = InstallationService(default_config)
        instructions = service.generate_instructions(sample_cabinet, None)
        assert isinstance(instructions, str)
        assert "##" in instructions  # Markdown header

    def test_generate_plan_returns_plan(
        self, default_config: InstallationConfig, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_plan returns InstallationPlan."""
        service = InstallationService(default_config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)
        assert isinstance(plan, InstallationPlan)
        assert plan.stud_analysis.cabinet_width == sample_cabinet.width


class TestWallTypeEnum:
    """Tests for WallType enum values."""

    def test_wall_type_values(self) -> None:
        """Test that all WallType values are correct."""
        assert WallType.DRYWALL.value == "drywall"
        assert WallType.PLASTER.value == "plaster"
        assert WallType.CONCRETE.value == "concrete"
        assert WallType.CMU.value == "cmu"
        assert WallType.BRICK.value == "brick"

    def test_wall_type_is_str_enum(self) -> None:
        """Test that WallType is a string enum."""
        assert isinstance(WallType.DRYWALL, str)
        assert WallType.DRYWALL == "drywall"


class TestMountingSystemEnum:
    """Tests for MountingSystem enum values."""

    def test_mounting_system_values(self) -> None:
        """Test that all MountingSystem values are correct."""
        assert MountingSystem.DIRECT_TO_STUD.value == "direct_to_stud"
        assert MountingSystem.FRENCH_CLEAT.value == "french_cleat"
        assert MountingSystem.HANGING_RAIL.value == "hanging_rail"
        assert MountingSystem.TOGGLE_BOLT.value == "toggle_bolt"

    def test_mounting_system_is_str_enum(self) -> None:
        """Test that MountingSystem is a string enum."""
        assert isinstance(MountingSystem.DIRECT_TO_STUD, str)
        assert MountingSystem.DIRECT_TO_STUD == "direct_to_stud"


class TestLoadCategoryEnum:
    """Tests for LoadCategory enum values."""

    def test_load_category_values(self) -> None:
        """Test that all LoadCategory values are correct."""
        assert LoadCategory.LIGHT.value == "light"
        assert LoadCategory.MEDIUM.value == "medium"
        assert LoadCategory.HEAVY.value == "heavy"

    def test_load_category_is_str_enum(self) -> None:
        """Test that LoadCategory is a string enum."""
        assert isinstance(LoadCategory.LIGHT, str)
        assert LoadCategory.LIGHT == "light"


# ============================================================================
# Phase 3-5 Implementation Tests
# ============================================================================


class TestCalculateStudHits:
    """Tests for InstallationService.calculate_stud_hits() method."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        section = Section(
            width=46.5,
            height=28.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_stud_hits_with_standard_spacing(self, sample_cabinet: Cabinet) -> None:
        """Test stud hit calculation with default 16\" OC spacing."""
        config = InstallationConfig(stud_spacing=16.0, stud_offset=0.0)
        service = InstallationService(config)
        analysis = service.calculate_stud_hits(sample_cabinet, left_edge=0.0)

        # Cabinet is 48" wide, studs at 0, 16, 32, 48
        # Studs at 0, 16, 32, 48 should all be within [0, 48]
        assert analysis.stud_hit_count == 4
        assert len(analysis.stud_positions) == 4
        assert 0.0 in analysis.stud_positions
        assert 16.0 in analysis.stud_positions
        assert 32.0 in analysis.stud_positions
        assert 48.0 in analysis.stud_positions
        assert analysis.recommendation is None

    def test_stud_hits_with_offset(self, sample_cabinet: Cabinet) -> None:
        """Test stud hit calculation with stud offset."""
        config = InstallationConfig(stud_spacing=16.0, stud_offset=8.0)
        service = InstallationService(config)
        analysis = service.calculate_stud_hits(sample_cabinet, left_edge=0.0)

        # Studs at 8, 24, 40 within [0, 48]
        assert analysis.stud_hit_count == 3
        assert 8.0 in analysis.stud_positions
        assert 24.0 in analysis.stud_positions
        assert 40.0 in analysis.stud_positions

    def test_stud_hits_with_cabinet_offset(self, sample_cabinet: Cabinet) -> None:
        """Test stud hits when cabinet is offset from wall start."""
        config = InstallationConfig(stud_spacing=16.0, stud_offset=0.0)
        service = InstallationService(config)
        analysis = service.calculate_stud_hits(sample_cabinet, left_edge=12.0)

        # Cabinet spans [12, 60], studs at 0, 16, 32, 48, 64...
        # Studs within cabinet: 16, 32, 48 (not 0, not 64)
        assert analysis.cabinet_left_edge == 12.0
        assert 16.0 in analysis.stud_positions
        assert 32.0 in analysis.stud_positions
        assert 48.0 in analysis.stud_positions
        assert 0.0 not in analysis.stud_positions

    def test_stud_warning_with_zero_hits(self) -> None:
        """Test warning when no studs hit."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        narrow_cabinet = Cabinet(
            width=12.0,  # Very narrow cabinet
            height=30.0,
            depth=12.0,
            material=material,
        )
        # Offset so no studs fall within cabinet
        config = InstallationConfig(stud_spacing=16.0, stud_offset=0.0)
        service = InstallationService(config)
        analysis = service.calculate_stud_hits(narrow_cabinet, left_edge=2.0)

        # Cabinet [2, 14] misses studs at 0 and 16
        assert analysis.stud_hit_count == 0
        assert analysis.recommendation is not None
        assert "No stud hits" in analysis.recommendation

    def test_stud_warning_with_one_hit(self, sample_cabinet: Cabinet) -> None:
        """Test warning when only 1 stud hit."""
        # Create narrow cabinet that hits only one stud
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        narrow_cabinet = Cabinet(
            width=14.0,
            height=30.0,
            depth=12.0,
            material=material,
        )
        config = InstallationConfig(stud_spacing=16.0, stud_offset=0.0)
        service = InstallationService(config)
        analysis = service.calculate_stud_hits(narrow_cabinet, left_edge=10.0)

        # Cabinet [10, 24] includes stud at 16
        assert analysis.stud_hit_count == 1
        assert analysis.recommendation is not None
        assert "Only 1 stud hit" in analysis.recommendation

    def test_stud_hits_24_inch_spacing(self, sample_cabinet: Cabinet) -> None:
        """Test stud calculation with 24\" OC spacing."""
        config = InstallationConfig(stud_spacing=24.0, stud_offset=0.0)
        service = InstallationService(config)
        analysis = service.calculate_stud_hits(sample_cabinet, left_edge=0.0)

        # Studs at 0, 24, 48 within 48" cabinet
        assert analysis.stud_hit_count == 3
        assert 0.0 in analysis.stud_positions
        assert 24.0 in analysis.stud_positions
        assert 48.0 in analysis.stud_positions


class TestEstimateWeight:
    """Tests for InstallationService.estimate_weight() method."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        section = Section(
            width=46.5,
            height=28.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_weight_estimate_returns_positive_values(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that weight estimate returns positive values."""
        config = InstallationConfig()
        service = InstallationService(config)
        estimate = service.estimate_weight(sample_cabinet)

        assert estimate.empty_weight_lbs > 0
        assert estimate.expected_load_per_foot > 0
        assert estimate.total_estimated_load_lbs > 0

    def test_weight_estimate_uses_load_category(self, sample_cabinet: Cabinet) -> None:
        """Test that weight estimate uses configured load category."""
        for load, expected_rate in [
            (LoadCategory.LIGHT, 15.0),
            (LoadCategory.MEDIUM, 30.0),
            (LoadCategory.HEAVY, 50.0),
        ]:
            config = InstallationConfig(expected_load=load)
            service = InstallationService(config)
            estimate = service.estimate_weight(sample_cabinet)
            assert estimate.expected_load_per_foot == expected_rate

    def test_weight_estimate_for_different_materials(self) -> None:
        """Test weight estimation for different material types."""
        # MDF should be heavier than plywood
        plywood_cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD),
        )
        mdf_cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.MDF),
        )

        config = InstallationConfig()
        service = InstallationService(config)

        plywood_estimate = service.estimate_weight(plywood_cabinet)
        mdf_estimate = service.estimate_weight(mdf_cabinet)

        # MDF is denser (4.0 lbs/sqft/inch) than plywood (3.0 lbs/sqft/inch)
        assert mdf_estimate.empty_weight_lbs > plywood_estimate.empty_weight_lbs

    def test_weight_capacity_warning_for_toggle_bolts(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test capacity warning for heavy toggle bolt installations."""
        # Create a large, heavy cabinet
        heavy_cabinet = Cabinet(
            width=96.0,  # 8 feet wide
            height=84.0,  # 7 feet tall
            depth=24.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.MDF),
        )

        config = InstallationConfig(
            mounting_system=MountingSystem.TOGGLE_BOLT,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        estimate = service.estimate_weight(heavy_cabinet)

        assert estimate.capacity_warning is not None
        assert "toggle bolt" in estimate.capacity_warning.lower()

    def test_weight_capacity_warning_for_heavy_loads(self) -> None:
        """Test capacity warning for very heavy loads."""
        heavy_cabinet = Cabinet(
            width=96.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.MDF),
        )

        config = InstallationConfig(
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        estimate = service.estimate_weight(heavy_cabinet)

        # Very heavy load should trigger warning
        assert estimate.total_estimated_load_lbs > 200


class TestGenerateCleats:
    """Tests for InstallationService.generate_cleats() method."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        return cabinet

    def test_generate_cleats_returns_empty_for_non_cleat_mounting(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_cleats returns empty list for non-cleat systems."""
        for mounting_system in [
            MountingSystem.DIRECT_TO_STUD,
            MountingSystem.TOGGLE_BOLT,
            MountingSystem.HANGING_RAIL,
        ]:
            config = InstallationConfig(mounting_system=mounting_system)
            service = InstallationService(config)
            cleats = service.generate_cleats(sample_cabinet)
            assert cleats == []

    def test_generate_cleats_returns_two_pieces_for_french_cleat(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_cleats returns 2 pieces for French cleat system."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        cleats = service.generate_cleats(sample_cabinet)

        assert len(cleats) == 2
        labels = [cleat.label for cleat in cleats]
        assert "French Cleat (Wall)" in labels
        assert "French Cleat (Cabinet)" in labels

    def test_cleat_dimensions(self, sample_cabinet: Cabinet) -> None:
        """Test cleat dimensions are calculated correctly."""
        config = InstallationConfig(
            mounting_system=MountingSystem.FRENCH_CLEAT,
            cleat_width_percentage=90.0,
        )
        service = InstallationService(config)
        cleats = service.generate_cleats(sample_cabinet)

        expected_width = 48.0 * 0.90  # 43.2"
        for cleat in cleats:
            assert cleat.width == pytest.approx(expected_width, rel=0.01)
            assert cleat.height == 3.0  # Standard cleat height
            assert cleat.quantity == 1

    def test_cleat_metadata_includes_bevel_info(self, sample_cabinet: Cabinet) -> None:
        """Test cleat cut_metadata includes bevel angle and edge."""
        config = InstallationConfig(
            mounting_system=MountingSystem.FRENCH_CLEAT,
            cleat_bevel_angle=45.0,
        )
        service = InstallationService(config)
        cleats = service.generate_cleats(sample_cabinet)

        wall_cleat = next(c for c in cleats if "Wall" in c.label)
        cabinet_cleat = next(c for c in cleats if "Cabinet" in c.label)

        assert wall_cleat.cut_metadata is not None
        assert wall_cleat.cut_metadata["bevel_angle"] == 45.0
        assert wall_cleat.cut_metadata["bevel_edge"] == "top"
        assert wall_cleat.cut_metadata["grain_direction"] == "length"

        assert cabinet_cleat.cut_metadata is not None
        assert cabinet_cleat.cut_metadata["bevel_angle"] == 45.0
        assert cabinet_cleat.cut_metadata["bevel_edge"] == "bottom"

    def test_cleat_panel_type_is_nailer(self, sample_cabinet: Cabinet) -> None:
        """Test cleats have NAILER panel type."""
        from cabinets.domain.value_objects import PanelType

        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        cleats = service.generate_cleats(sample_cabinet)

        for cleat in cleats:
            assert cleat.panel_type == PanelType.NAILER


class TestGenerateHardware:
    """Tests for InstallationService.generate_hardware() method."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        return cabinet

    @pytest.fixture
    def stud_analysis_2_hits(self, sample_cabinet: Cabinet) -> StudHitAnalysis:
        """Create stud analysis with 2 stud hits."""
        return StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=sample_cabinet.width,
            stud_positions=(16.0, 32.0),
            non_stud_positions=(3.0, 45.0),
            stud_hit_count=2,
        )

    @pytest.fixture
    def stud_analysis_0_hits(self, sample_cabinet: Cabinet) -> StudHitAnalysis:
        """Create stud analysis with 0 stud hits."""
        return StudHitAnalysis(
            cabinet_left_edge=0.0,
            cabinet_width=sample_cabinet.width,
            stud_positions=(),
            non_stud_positions=(3.0, 19.0, 35.0, 45.0),
            stud_hit_count=0,
        )

    def test_direct_to_stud_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for direct-to-stud mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.DIRECT_TO_STUD)
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        assert len(hardware) == 1
        assert "cabinet screw" in hardware[0].name.lower()
        # 2 stud hits * 2 screws per stud = 4 screws
        assert hardware[0].quantity == 4

    def test_toggle_bolt_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_0_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for toggle bolt mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.TOGGLE_BOLT)
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_0_hits)

        assert len(hardware) == 1
        assert "toggle bolt" in hardware[0].name.lower()
        assert hardware[0].quantity >= 4  # Minimum 4 toggle bolts

    def test_toggle_bolt_size_for_heavy_load(
        self, sample_cabinet: Cabinet, stud_analysis_0_hits: StudHitAnalysis
    ) -> None:
        """Test toggle bolt size is larger for heavy loads."""
        config = InstallationConfig(
            mounting_system=MountingSystem.TOGGLE_BOLT,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_0_hits)

        assert '3/8"' in hardware[0].name  # Larger toggle for heavy load

    def test_french_cleat_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for French cleat mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        # Should have lag bolts, washers, and cabinet screws
        hardware_names = [h.name.lower() for h in hardware]
        assert any("lag bolt" in name for name in hardware_names)
        assert any("washer" in name for name in hardware_names)
        assert any("wood screw" in name for name in hardware_names)

    def test_hanging_rail_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for hanging rail mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.HANGING_RAIL)
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        hardware_names = [h.name.lower() for h in hardware]
        assert any("hanging rail" in name for name in hardware_names)
        assert any("bracket" in name for name in hardware_names)

    def test_concrete_wall_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for concrete wall."""
        config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            mounting_system=MountingSystem.DIRECT_TO_STUD,  # Ignored for masonry
        )
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        hardware_names = [h.name.lower() for h in hardware]
        assert any("tapcon" in name for name in hardware_names)
        assert any("drill bit" in name for name in hardware_names)

    def test_cmu_wall_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for CMU wall."""
        config = InstallationConfig(
            wall_type=WallType.CMU,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
        )
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        hardware_names = [h.name.lower() for h in hardware]
        assert any("tapcon" in name for name in hardware_names)

    def test_brick_wall_hardware(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test hardware generation for brick wall."""
        config = InstallationConfig(
            wall_type=WallType.BRICK,
            mounting_system=MountingSystem.DIRECT_TO_STUD,
        )
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        hardware_names = [h.name.lower() for h in hardware]
        assert any("tapcon" in name for name in hardware_names)
        assert any("brick" in h.notes.lower() for h in hardware if h.notes)

    def test_screw_length_calculation(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test screw length is calculated correctly."""
        # 0.25" back + 0.5" wall + 1.5" penetration = 2.25"
        config = InstallationConfig(
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            wall_thickness=0.5,
        )
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        screw_item = hardware[0]
        # Should round up to 2.25"
        assert '2.25"' in screw_item.name

    def test_masonry_tapcon_size_for_heavy_load(
        self, sample_cabinet: Cabinet, stud_analysis_2_hits: StudHitAnalysis
    ) -> None:
        """Test Tapcon size is larger for heavy loads on masonry."""
        config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        hardware = service.generate_hardware(sample_cabinet, stud_analysis_2_hits)

        tapcon_item = next(h for h in hardware if "tapcon" in h.name.lower())
        assert '1/4"' in tapcon_item.name  # Larger Tapcon for heavy load


class TestGeneratePlanIntegration:
    """Integration tests for InstallationService.generate_plan() method."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        section = Section(
            width=46.5,
            height=28.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_generate_plan_integrates_all_components(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_plan integrates stud, weight, hardware, cleats."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)

        # Plan should have all components
        assert plan.stud_analysis is not None
        assert plan.weight_estimate is not None
        assert len(plan.mounting_hardware) > 0
        assert len(plan.cleat_cut_pieces) == 2  # Wall and cabinet cleats

    def test_generate_plan_includes_stud_warning(self) -> None:
        """Test that generate_plan includes stud warning when applicable."""
        # Create narrow cabinet that misses studs
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        narrow_cabinet = Cabinet(
            width=12.0,
            height=30.0,
            depth=12.0,
            material=material,
        )

        config = InstallationConfig(stud_spacing=16.0, stud_offset=0.0)
        service = InstallationService(config)
        plan = service.generate_plan(narrow_cabinet, left_edge_position=2.0)

        assert plan.has_warnings
        assert any("stud" in w.lower() for w in plan.warnings)

    def test_generate_plan_includes_weight_warning(self) -> None:
        """Test that generate_plan includes weight warning when applicable."""
        heavy_cabinet = Cabinet(
            width=96.0,
            height=84.0,
            depth=24.0,
            material=MaterialSpec(thickness=0.75, material_type=MaterialType.MDF),
        )

        config = InstallationConfig(
            mounting_system=MountingSystem.TOGGLE_BOLT,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        plan = service.generate_plan(heavy_cabinet, left_edge_position=0.0)

        assert plan.has_warnings
        assert any("capacity" in w.lower() or "load" in w.lower() for w in plan.warnings)

    def test_generate_plan_without_cleats_for_direct_mount(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_plan has no cleats for direct-to-stud mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.DIRECT_TO_STUD)
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)

        assert plan.uses_cleats is False
        assert len(plan.cleat_cut_pieces) == 0

    def test_generate_plan_hardware_count(self, sample_cabinet: Cabinet) -> None:
        """Test hardware count property."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)

        # Hardware count should sum all quantities
        total_count = sum(h.quantity for h in plan.mounting_hardware)
        assert plan.hardware_count == total_count
        assert plan.hardware_count > 0


class TestScrewLengthCalculation:
    """Tests for screw length calculation helper method."""

    def test_screw_length_rounds_up_to_standard(self) -> None:
        """Test screw length rounds up to next standard size."""
        config = InstallationConfig(wall_thickness=0.5)  # 1/2" drywall
        service = InstallationService(config)

        # 0.25" back + 0.5" wall + 1.5" penetration = 2.25" -> 2.25"
        length = service._calculate_screw_length(back_thickness=0.25)
        assert length == 2.25

    def test_screw_length_for_thick_wall(self) -> None:
        """Test screw length for thicker walls."""
        config = InstallationConfig(wall_thickness=1.5)  # Thicker plaster
        service = InstallationService(config)

        # 0.25" back + 1.5" wall + 1.5" penetration = 3.25" -> 3.5"
        length = service._calculate_screw_length(back_thickness=0.25)
        assert length == 3.5

    def test_screw_length_uses_maximum_for_extreme_cases(self) -> None:
        """Test screw length returns max for very thick walls."""
        config = InstallationConfig(wall_thickness=2.0)  # Very thick
        service = InstallationService(config)

        # 0.75" back + 2.0" wall + 1.5" penetration = 4.25" -> 4.0" (max)
        length = service._calculate_screw_length(back_thickness=0.75)
        assert length == 4.0  # Maximum standard length


# ============================================================================
# Phase 6 Implementation Tests - Installation Instructions Generation
# ============================================================================


class TestGenerateInstructions:
    """Tests for InstallationService.generate_instructions() method."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        cabinet = Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
            back_material=MaterialSpec.standard_1_4(),
        )
        section = Section(
            width=46.5,
            height=28.5,
            depth=11.25,
            position=Position(0.75, 0.75),
        )
        cabinet.sections.append(section)
        return cabinet

    def test_instructions_include_cabinet_dimensions(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include cabinet dimensions."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "48.0" in instructions  # Width
        assert "30.0" in instructions  # Height
        assert "12.0" in instructions  # Depth

    def test_instructions_include_tools_required_section(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include Tools Required section."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "## Tools Required" in instructions
        assert "Level" in instructions
        assert "Tape measure" in instructions
        assert "Drill/driver" in instructions

    def test_instructions_include_stud_finder_for_direct_to_stud(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that stud finder is listed for stud-based mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.DIRECT_TO_STUD)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Stud finder" in instructions

    def test_instructions_include_safety_notes_section(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include Safety Notes section."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "## Safety Notes" in instructions
        assert "helper" in instructions.lower()

    def test_instructions_include_disclaimer(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include required disclaimer."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "## Disclaimer" in instructions
        assert "For reference only" in instructions
        assert "professional installer" in instructions.lower()
        assert "local codes" in instructions.lower()

    def test_instructions_vary_by_mounting_system_direct_to_stud(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions vary for direct-to-stud mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.DIRECT_TO_STUD)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Locate Wall Studs" in instructions
        assert "Pre-drill Mounting Holes" in instructions
        assert "pilot holes" in instructions.lower()

    def test_instructions_vary_by_mounting_system_french_cleat(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions vary for French cleat mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "French Cleat" in instructions
        assert "Wall Cleat" in instructions
        assert "Cabinet Cleat" in instructions
        assert "bevel" in instructions.lower()
        assert "lag bolts" in instructions.lower()

    def test_instructions_vary_by_mounting_system_toggle_bolt(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions vary for toggle bolt mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.TOGGLE_BOLT)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Toggle Bolt" in instructions
        assert "toggle" in instructions.lower()
        assert "wings" in instructions.lower()

    def test_instructions_vary_by_mounting_system_hanging_rail(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions vary for hanging rail mounting."""
        config = InstallationConfig(mounting_system=MountingSystem.HANGING_RAIL)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Hanging Rail" in instructions
        assert "brackets" in instructions.lower()
        assert "rail" in instructions.lower()

    def test_instructions_include_masonry_steps_for_concrete(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include masonry-specific steps for concrete walls."""
        config = InstallationConfig(wall_type=WallType.CONCRETE)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Concrete" in instructions
        assert "hammer drill" in instructions.lower()
        assert "masonry" in instructions.lower()
        assert "Tapcon" in instructions

    def test_instructions_include_masonry_steps_for_cmu(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include masonry-specific steps for CMU walls."""
        config = InstallationConfig(wall_type=WallType.CMU)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "cmu" in instructions.lower()
        assert "hammer drill" in instructions.lower()
        assert "Tapcon" in instructions

    def test_instructions_include_masonry_steps_for_brick(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include masonry-specific steps for brick walls."""
        config = InstallationConfig(wall_type=WallType.BRICK)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "brick" in instructions.lower()
        assert "mortar joints" in instructions.lower()
        assert "Tapcon" in instructions

    def test_instructions_reference_hardware_items_from_plan(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions reference hardware items when plan is provided."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)
        instructions = service.generate_instructions(sample_cabinet, plan)

        # Instructions should include Hardware Required section
        assert "## Hardware Required" in instructions
        # Should list specific hardware items
        assert "lag bolt" in instructions.lower()

    def test_instructions_include_load_capacity_in_safety_notes(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that safety notes include load capacity from weight estimate."""
        config = InstallationConfig()
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)
        instructions = service.generate_instructions(sample_cabinet, plan)

        # Safety notes should reference the weight estimate
        assert "lbs" in instructions
        assert "capacity" in instructions.lower() or "load" in instructions.lower()

    def test_instructions_include_helper_requirement(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions emphasize using a helper."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "helper" in instructions.lower()
        assert "two people" in instructions.lower() or "alone" in instructions.lower()

    def test_instructions_include_level_usage(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions mention using a level."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        # Level should be in tools and procedure
        assert instructions.lower().count("level") >= 2

    def test_instructions_format_is_valid_markdown(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions are valid markdown format."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        # Should have proper markdown headers
        assert "# Cabinet Installation Instructions" in instructions
        assert "## " in instructions
        assert "### Step" in instructions

        # Should have proper list formatting
        assert "- " in instructions

    def test_instructions_include_all_five_steps(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that instructions include 5 procedural steps."""
        config = InstallationConfig()
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Step 1" in instructions
        assert "Step 2" in instructions
        assert "Step 3" in instructions
        assert "Step 4" in instructions
        assert "Step 5" in instructions

    def test_instructions_tools_include_masonry_drill_for_concrete(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that masonry tools are listed for concrete walls."""
        config = InstallationConfig(wall_type=WallType.CONCRETE)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Hammer drill" in instructions
        assert "masonry drill bit" in instructions.lower()

    def test_instructions_tools_include_toggle_bolt_drill_size(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that correct drill bit size is listed for toggle bolts."""
        config = InstallationConfig(
            mounting_system=MountingSystem.TOGGLE_BOLT,
            expected_load=LoadCategory.MEDIUM,
        )
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert '1/4"' in instructions  # Standard toggle bolt drill size

    def test_instructions_tools_include_larger_toggle_for_heavy_load(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that larger toggle bolt drill size is used for heavy loads."""
        config = InstallationConfig(
            mounting_system=MountingSystem.TOGGLE_BOLT,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert '3/8"' in instructions  # Heavy load toggle bolt drill size

    def test_instructions_include_eye_protection_for_masonry(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that safety notes include eye protection for masonry."""
        config = InstallationConfig(wall_type=WallType.CONCRETE)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "safety glasses" in instructions.lower() or "eye" in instructions.lower()

    def test_instructions_stud_spacing_is_mentioned(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that stud spacing is mentioned for stud-based mounting."""
        config = InstallationConfig(
            mounting_system=MountingSystem.DIRECT_TO_STUD,
            stud_spacing=16.0,
        )
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "16" in instructions  # 16" on center

    def test_instructions_cleat_position_is_mentioned(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that cleat position is mentioned for French cleat mounting."""
        config = InstallationConfig(
            mounting_system=MountingSystem.FRENCH_CLEAT,
            cleat_position_from_top=4.0,
        )
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert '4"' in instructions or "4\"" in instructions

    def test_generate_plan_includes_complete_instructions(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_plan produces complete instructions."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)

        # Instructions should be complete, not placeholder
        assert plan.instructions != ""
        assert "Installation Instructions" in plan.instructions
        assert "Tools Required" in plan.instructions
        assert "Disclaimer" in plan.instructions

    def test_generate_plan_instructions_include_hardware_list(
        self, sample_cabinet: Cabinet
    ) -> None:
        """Test that generate_plan instructions include hardware list."""
        config = InstallationConfig(mounting_system=MountingSystem.DIRECT_TO_STUD)
        service = InstallationService(config)
        plan = service.generate_plan(sample_cabinet, left_edge_position=0.0)

        assert "## Hardware Required" in plan.instructions
        # Should list screws for direct-to-stud
        assert "screw" in plan.instructions.lower()


class TestInstructionsMountingSystemFormatting:
    """Tests for mounting system name formatting in instructions."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        return Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
        )

    def test_direct_to_stud_formatting(self, sample_cabinet: Cabinet) -> None:
        """Test Direct to Stud is properly formatted."""
        config = InstallationConfig(mounting_system=MountingSystem.DIRECT_TO_STUD)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Direct to Stud" in instructions

    def test_french_cleat_formatting(self, sample_cabinet: Cabinet) -> None:
        """Test French Cleat is properly formatted."""
        config = InstallationConfig(mounting_system=MountingSystem.FRENCH_CLEAT)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "French Cleat" in instructions

    def test_toggle_bolt_formatting(self, sample_cabinet: Cabinet) -> None:
        """Test Toggle Bolt is properly formatted."""
        config = InstallationConfig(mounting_system=MountingSystem.TOGGLE_BOLT)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Toggle Bolt" in instructions

    def test_hanging_rail_formatting(self, sample_cabinet: Cabinet) -> None:
        """Test Hanging Rail is properly formatted."""
        config = InstallationConfig(mounting_system=MountingSystem.HANGING_RAIL)
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "Hanging Rail" in instructions


class TestInstructionsEmbedmentDepth:
    """Tests for embedment depth in masonry instructions."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(thickness=0.75, material_type=MaterialType.PLYWOOD)
        return Cabinet(
            width=48.0,
            height=30.0,
            depth=12.0,
            material=material,
        )

    def test_embedment_depth_for_medium_load(self, sample_cabinet: Cabinet) -> None:
        """Test embedment depth is mentioned for medium load masonry."""
        config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            expected_load=LoadCategory.MEDIUM,
        )
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "embedment" in instructions.lower()
        assert '2"' in instructions

    def test_embedment_depth_for_heavy_load(self, sample_cabinet: Cabinet) -> None:
        """Test embedment depth is larger for heavy load masonry."""
        config = InstallationConfig(
            wall_type=WallType.CONCRETE,
            expected_load=LoadCategory.HEAVY,
        )
        service = InstallationService(config)
        instructions = service.generate_instructions(sample_cabinet, None)

        assert "embedment" in instructions.lower()
        assert '2-1/4"' in instructions
