"""Unit tests for LLM output models.

Tests cover:
- WarningSeverity enum validation
- SafetyWarning model validation
- ToolRecommendation model validation
- AssemblyStep model validation
- TroubleshootingTip model validation
- AssemblyInstructions model validation
- AssemblyDeps model validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cabinets.domain.entities import Cabinet, Section
from cabinets.domain.value_objects import MaterialSpec, MaterialType, Position
from cabinets.infrastructure.llm import (
    AssemblyDeps,
    AssemblyInstructions,
    AssemblyStep,
    SafetyWarning,
    ToolRecommendation,
    TroubleshootingTip,
    WarningSeverity,
)


# =============================================================================
# Test Class: WarningSeverity Enum
# =============================================================================


class TestWarningSeverity:
    """Tests for WarningSeverity enum."""

    def test_severity_values(self) -> None:
        """All expected severity values exist."""
        assert WarningSeverity.INFO.value == "info"
        assert WarningSeverity.CAUTION.value == "caution"
        assert WarningSeverity.WARNING.value == "warning"
        assert WarningSeverity.DANGER.value == "danger"

    def test_severity_is_string_enum(self) -> None:
        """WarningSeverity is a string enum and can be used as string."""
        assert str(WarningSeverity.DANGER) == "WarningSeverity.DANGER"
        assert WarningSeverity.DANGER.value == "danger"

    def test_all_severity_levels(self) -> None:
        """WarningSeverity has exactly four levels."""
        all_severities = list(WarningSeverity)
        assert len(all_severities) == 4
        assert WarningSeverity.INFO in all_severities
        assert WarningSeverity.CAUTION in all_severities
        assert WarningSeverity.WARNING in all_severities
        assert WarningSeverity.DANGER in all_severities

    def test_severity_can_be_compared(self) -> None:
        """WarningSeverity values can be compared."""
        assert WarningSeverity.INFO == WarningSeverity.INFO
        assert WarningSeverity.INFO != WarningSeverity.DANGER

    def test_severity_from_value(self) -> None:
        """WarningSeverity can be created from string value."""
        assert WarningSeverity("info") == WarningSeverity.INFO
        assert WarningSeverity("danger") == WarningSeverity.DANGER


# =============================================================================
# Test Class: SafetyWarning Model
# =============================================================================


class TestSafetyWarning:
    """Tests for SafetyWarning model."""

    def test_valid_warning(self) -> None:
        """Valid warning data creates model."""
        warning = SafetyWarning(
            severity=WarningSeverity.WARNING,
            message="Wear safety glasses",
            context="All cutting operations",
            mitigation="Keep glasses on at all times",
        )
        assert warning.severity == WarningSeverity.WARNING
        assert warning.message == "Wear safety glasses"
        assert warning.context == "All cutting operations"
        assert warning.mitigation == "Keep glasses on at all times"

    def test_all_severity_levels_accepted(self) -> None:
        """All severity levels are accepted."""
        for severity in WarningSeverity:
            warning = SafetyWarning(
                severity=severity,
                message="Test message",
                context="Test context",
                mitigation="Test mitigation",
            )
            assert warning.severity == severity

    def test_missing_required_field_message(self) -> None:
        """Missing message field raises ValidationError."""
        with pytest.raises(ValidationError):
            SafetyWarning(
                severity=WarningSeverity.WARNING,
                context="Test context",
                mitigation="Test mitigation",
            )  # type: ignore[call-arg]

    def test_missing_required_field_context(self) -> None:
        """Missing context field raises ValidationError."""
        with pytest.raises(ValidationError):
            SafetyWarning(
                severity=WarningSeverity.WARNING,
                message="Test message",
                mitigation="Test mitigation",
            )  # type: ignore[call-arg]

    def test_missing_required_field_mitigation(self) -> None:
        """Missing mitigation field raises ValidationError."""
        with pytest.raises(ValidationError):
            SafetyWarning(
                severity=WarningSeverity.WARNING,
                message="Test message",
                context="Test context",
            )  # type: ignore[call-arg]

    def test_warning_with_string_severity(self) -> None:
        """Warning can be created with string severity value."""
        warning = SafetyWarning(
            severity="danger",  # type: ignore[arg-type]
            message="Critical hazard",
            context="Power tool operation",
            mitigation="Follow safety protocol",
        )
        assert warning.severity == WarningSeverity.DANGER


# =============================================================================
# Test Class: ToolRecommendation Model
# =============================================================================


class TestToolRecommendation:
    """Tests for ToolRecommendation model."""

    def test_valid_tool(self) -> None:
        """Valid tool data creates model."""
        tool = ToolRecommendation(
            tool="Table saw",
            purpose="Cutting panels",
            alternatives=["Track saw", "Circular saw"],
            required=True,
        )
        assert tool.tool == "Table saw"
        assert tool.purpose == "Cutting panels"
        assert len(tool.alternatives) == 2
        assert tool.required is True

    def test_defaults(self) -> None:
        """Default values are applied."""
        tool = ToolRecommendation(
            tool="Clamps",
            purpose="Holding work",
        )
        assert tool.alternatives == []
        assert tool.required is True

    def test_optional_tool(self) -> None:
        """Tool can be marked as optional."""
        tool = ToolRecommendation(
            tool="Orbital sander",
            purpose="Surface preparation",
            required=False,
        )
        assert tool.required is False

    def test_empty_alternatives_list(self) -> None:
        """Empty alternatives list is valid."""
        tool = ToolRecommendation(
            tool="Unique tool",
            purpose="Special operation",
            alternatives=[],
        )
        assert tool.alternatives == []

    def test_missing_required_field_tool(self) -> None:
        """Missing tool field raises ValidationError."""
        with pytest.raises(ValidationError):
            ToolRecommendation(
                purpose="Test purpose",
            )  # type: ignore[call-arg]

    def test_missing_required_field_purpose(self) -> None:
        """Missing purpose field raises ValidationError."""
        with pytest.raises(ValidationError):
            ToolRecommendation(
                tool="Test tool",
            )  # type: ignore[call-arg]


# =============================================================================
# Test Class: AssemblyStep Model
# =============================================================================


class TestAssemblyStep:
    """Tests for AssemblyStep model."""

    def test_valid_step(self) -> None:
        """Valid step data creates model."""
        step = AssemblyStep(
            step_number=1,
            phase="Carcase Assembly",
            title="Prepare Panels",
            description="Lay out panels with inside faces up.",
            pieces_involved=["Left Side", "Right Side"],
        )
        assert step.step_number == 1
        assert step.phase == "Carcase Assembly"
        assert step.title == "Prepare Panels"
        assert len(step.pieces_involved) == 2

    def test_step_number_minimum(self) -> None:
        """Step number must be >= 1."""
        with pytest.raises(ValidationError):
            AssemblyStep(
                step_number=0,
                phase="Test",
                title="Test",
                description="Test",
                pieces_involved=[],
            )

    def test_negative_step_number(self) -> None:
        """Negative step number rejected."""
        with pytest.raises(ValidationError):
            AssemblyStep(
                step_number=-1,
                phase="Test",
                title="Test",
                description="Test",
                pieces_involved=[],
            )

    def test_valid_difficulty_easy(self) -> None:
        """Valid difficulty 'easy' is accepted."""
        step = AssemblyStep(
            step_number=1,
            phase="Test",
            title="Test",
            description="Test",
            pieces_involved=[],
            difficulty="easy",
        )
        assert step.difficulty == "easy"

    def test_valid_difficulty_moderate(self) -> None:
        """Valid difficulty 'moderate' is accepted."""
        step = AssemblyStep(
            step_number=1,
            phase="Test",
            title="Test",
            description="Test",
            pieces_involved=[],
            difficulty="moderate",
        )
        assert step.difficulty == "moderate"

    def test_valid_difficulty_challenging(self) -> None:
        """Valid difficulty 'challenging' is accepted."""
        step = AssemblyStep(
            step_number=1,
            phase="Test",
            title="Test",
            description="Test",
            pieces_involved=[],
            difficulty="challenging",
        )
        assert step.difficulty == "challenging"

    def test_invalid_difficulty(self) -> None:
        """Invalid difficulty rejected."""
        with pytest.raises(ValidationError):
            AssemblyStep(
                step_number=1,
                phase="Test",
                title="Test",
                description="Test",
                pieces_involved=[],
                difficulty="hard",  # Invalid
            )

    def test_optional_fields_defaults(self) -> None:
        """Optional fields have correct defaults."""
        step = AssemblyStep(
            step_number=1,
            phase="Test",
            title="Test",
            description="Test",
            pieces_involved=[],
        )
        assert step.joinery_details is None
        assert step.time_estimate is None
        assert step.difficulty is None
        assert step.quality_check is None
        assert step.common_mistakes == []

    def test_step_with_all_optional_fields(self) -> None:
        """Step with all optional fields populated."""
        step = AssemblyStep(
            step_number=2,
            phase="Carcase Assembly",
            title="Attach Top and Bottom",
            description="Apply glue to dados and insert panels.",
            pieces_involved=["Top", "Bottom", "Sides"],
            joinery_details="Use dado joints for strong connection",
            time_estimate="30 minutes",
            difficulty="moderate",
            quality_check="Check for square using diagonal measurements",
            common_mistakes=["Not checking for square", "Too much glue"],
        )
        assert step.joinery_details == "Use dado joints for strong connection"
        assert step.time_estimate == "30 minutes"
        assert step.difficulty == "moderate"
        assert step.quality_check == "Check for square using diagonal measurements"
        assert len(step.common_mistakes) == 2


# =============================================================================
# Test Class: TroubleshootingTip Model
# =============================================================================


class TestTroubleshootingTip:
    """Tests for TroubleshootingTip model."""

    def test_valid_tip(self) -> None:
        """Valid tip data creates model."""
        tip = TroubleshootingTip(
            issue="Panels not square",
            cause="Measurement error",
            solution="Use framing square",
            prevention="Measure twice",
        )
        assert tip.issue == "Panels not square"
        assert tip.cause == "Measurement error"
        assert tip.solution == "Use framing square"
        assert tip.prevention == "Measure twice"

    def test_optional_prevention(self) -> None:
        """Prevention field is optional."""
        tip = TroubleshootingTip(
            issue="Test issue",
            cause="Test cause",
            solution="Test solution",
        )
        assert tip.prevention is None

    def test_missing_required_field_issue(self) -> None:
        """Missing issue field raises ValidationError."""
        with pytest.raises(ValidationError):
            TroubleshootingTip(
                cause="Test cause",
                solution="Test solution",
            )  # type: ignore[call-arg]

    def test_missing_required_field_cause(self) -> None:
        """Missing cause field raises ValidationError."""
        with pytest.raises(ValidationError):
            TroubleshootingTip(
                issue="Test issue",
                solution="Test solution",
            )  # type: ignore[call-arg]

    def test_missing_required_field_solution(self) -> None:
        """Missing solution field raises ValidationError."""
        with pytest.raises(ValidationError):
            TroubleshootingTip(
                issue="Test issue",
                cause="Test cause",
            )  # type: ignore[call-arg]


# =============================================================================
# Test Class: AssemblyInstructions Model
# =============================================================================


class TestAssemblyInstructions:
    """Tests for AssemblyInstructions model."""

    def test_valid_instructions(self) -> None:
        """Valid complete instructions creates model."""
        instructions = AssemblyInstructions(
            title="Test Cabinet Assembly",
            skill_level="intermediate",
            cabinet_summary="48x84x12 cabinet",
            estimated_time="3-4 hours",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Apply finish",
        )
        assert instructions.title == "Test Cabinet Assembly"
        assert instructions.generated_by == "llm"  # Default

    def test_valid_skill_level_beginner(self) -> None:
        """Skill level 'beginner' is accepted."""
        instructions = AssemblyInstructions(
            title="Test",
            skill_level="beginner",
            cabinet_summary="Test",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Test",
        )
        assert instructions.skill_level == "beginner"

    def test_valid_skill_level_intermediate(self) -> None:
        """Skill level 'intermediate' is accepted."""
        instructions = AssemblyInstructions(
            title="Test",
            skill_level="intermediate",
            cabinet_summary="Test",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Test",
        )
        assert instructions.skill_level == "intermediate"

    def test_valid_skill_level_expert(self) -> None:
        """Skill level 'expert' is accepted."""
        instructions = AssemblyInstructions(
            title="Test",
            skill_level="expert",
            cabinet_summary="Test",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Test",
        )
        assert instructions.skill_level == "expert"

    def test_invalid_skill_level(self) -> None:
        """Invalid skill level rejected."""
        with pytest.raises(ValidationError):
            AssemblyInstructions(
                title="Test",
                skill_level="novice",  # Invalid
                cabinet_summary="Test",
                estimated_time="1 hour",
                safety_warnings=[],
                tools_needed=[],
                materials_checklist=[],
                steps=[],
                finishing_notes="Test",
            )

    def test_generated_by_llm(self) -> None:
        """Generated_by 'llm' is accepted."""
        instructions = AssemblyInstructions(
            title="Test",
            skill_level="intermediate",
            cabinet_summary="Test",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Test",
            generated_by="llm",
        )
        assert instructions.generated_by == "llm"

    def test_generated_by_template(self) -> None:
        """Generated_by 'template' is accepted."""
        instructions = AssemblyInstructions(
            title="Test",
            skill_level="intermediate",
            cabinet_summary="Test",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Test",
            generated_by="template",
        )
        assert instructions.generated_by == "template"

    def test_invalid_generated_by(self) -> None:
        """Invalid generated_by value rejected."""
        with pytest.raises(ValidationError):
            AssemblyInstructions(
                title="Test",
                skill_level="intermediate",
                cabinet_summary="Test",
                estimated_time="1 hour",
                safety_warnings=[],
                tools_needed=[],
                materials_checklist=[],
                steps=[],
                finishing_notes="Test",
                generated_by="manual",  # Invalid
            )

    def test_instructions_with_nested_models(self) -> None:
        """Instructions with nested models validates correctly."""
        instructions = AssemblyInstructions(
            title="Full Cabinet Assembly",
            skill_level="intermediate",
            cabinet_summary="48x84x12 plywood cabinet",
            estimated_time="3-4 hours",
            safety_warnings=[
                SafetyWarning(
                    severity=WarningSeverity.WARNING,
                    message="Wear safety glasses",
                    context="All operations",
                    mitigation="Keep glasses on",
                ),
            ],
            tools_needed=[
                ToolRecommendation(
                    tool="Table saw",
                    purpose="Cutting panels",
                    required=True,
                ),
            ],
            materials_checklist=["Plywood sheets", "Wood glue", "Screws"],
            steps=[
                AssemblyStep(
                    step_number=1,
                    phase="Preparation",
                    title="Gather materials",
                    description="Collect all materials and tools",
                    pieces_involved=[],
                ),
            ],
            troubleshooting=[
                TroubleshootingTip(
                    issue="Panel not square",
                    cause="Misalignment",
                    solution="Check with square",
                ),
            ],
            finishing_notes="Apply finish as desired.",
        )
        assert len(instructions.safety_warnings) == 1
        assert len(instructions.tools_needed) == 1
        assert len(instructions.materials_checklist) == 3
        assert len(instructions.steps) == 1
        assert len(instructions.troubleshooting) == 1

    def test_troubleshooting_defaults_to_empty_list(self) -> None:
        """Troubleshooting defaults to empty list."""
        instructions = AssemblyInstructions(
            title="Test",
            skill_level="intermediate",
            cabinet_summary="Test",
            estimated_time="1 hour",
            safety_warnings=[],
            tools_needed=[],
            materials_checklist=[],
            steps=[],
            finishing_notes="Test",
        )
        assert instructions.troubleshooting == []


# =============================================================================
# Test Class: AssemblyDeps Model
# =============================================================================


class TestAssemblyDeps:
    """Tests for AssemblyDeps model."""

    @pytest.fixture
    def sample_cabinet(self) -> Cabinet:
        """Create a sample cabinet for testing."""
        material = MaterialSpec(material_type=MaterialType.PLYWOOD, thickness=0.75)
        return Cabinet(
            width=48.0,
            height=84.0,
            depth=12.0,
            material=material,
            sections=[
                Section(
                    width=48.0,
                    height=84.0,
                    depth=12.0,
                    position=Position(0.0, 0.0),
                )
            ],
        )

    def test_valid_deps(self, sample_cabinet: Cabinet) -> None:
        """Valid deps data creates model."""
        deps = AssemblyDeps(
            cabinet=sample_cabinet,
            cut_list=[],
            joinery=[],
            skill_level="intermediate",
            material_type=MaterialType.PLYWOOD,
        )
        assert deps.cabinet == sample_cabinet
        assert deps.skill_level == "intermediate"
        assert deps.material_type == MaterialType.PLYWOOD

    def test_deps_with_optional_flags(self, sample_cabinet: Cabinet) -> None:
        """Deps with optional component flags."""
        deps = AssemblyDeps(
            cabinet=sample_cabinet,
            cut_list=[],
            joinery=[],
            skill_level="beginner",
            material_type=MaterialType.PLYWOOD,
            has_doors=True,
            has_drawers=True,
            has_decorative_elements=True,
        )
        assert deps.has_doors is True
        assert deps.has_drawers is True
        assert deps.has_decorative_elements is True

    def test_deps_optional_flags_default_false(self, sample_cabinet: Cabinet) -> None:
        """Optional component flags default to False."""
        deps = AssemblyDeps(
            cabinet=sample_cabinet,
            cut_list=[],
            joinery=[],
            skill_level="expert",
            material_type=MaterialType.MDF,
        )
        assert deps.has_doors is False
        assert deps.has_drawers is False
        assert deps.has_decorative_elements is False

    def test_deps_valid_skill_levels(self, sample_cabinet: Cabinet) -> None:
        """All valid skill levels are accepted."""
        for level in ["beginner", "intermediate", "expert"]:
            deps = AssemblyDeps(
                cabinet=sample_cabinet,
                cut_list=[],
                joinery=[],
                skill_level=level,  # type: ignore[arg-type]
                material_type=MaterialType.PLYWOOD,
            )
            assert deps.skill_level == level

    def test_deps_invalid_skill_level(self, sample_cabinet: Cabinet) -> None:
        """Invalid skill level rejected."""
        with pytest.raises(ValidationError):
            AssemblyDeps(
                cabinet=sample_cabinet,
                cut_list=[],
                joinery=[],
                skill_level="novice",  # type: ignore[arg-type]
                material_type=MaterialType.PLYWOOD,
            )

    def test_deps_material_types(self, sample_cabinet: Cabinet) -> None:
        """Various material types are accepted."""
        for material_type in [
            MaterialType.PLYWOOD,
            MaterialType.MDF,
            MaterialType.PARTICLE_BOARD,
        ]:
            deps = AssemblyDeps(
                cabinet=sample_cabinet,
                cut_list=[],
                joinery=[],
                skill_level="intermediate",
                material_type=material_type,
            )
            assert deps.material_type == material_type

    def test_deps_allows_arbitrary_types(self, sample_cabinet: Cabinet) -> None:
        """AssemblyDeps allows arbitrary types for domain objects."""
        # This tests that arbitrary_types_allowed is set correctly
        deps = AssemblyDeps(
            cabinet=sample_cabinet,
            cut_list=[],
            joinery=[],  # Using empty list for joinery (can hold any type)
            skill_level="intermediate",
            material_type=MaterialType.PLYWOOD,
        )
        assert deps.cabinet is sample_cabinet
