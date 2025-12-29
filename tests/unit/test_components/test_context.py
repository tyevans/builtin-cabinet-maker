"""Tests for ComponentContext."""

import pytest

from cabinets.domain.components.context import ComponentContext
from cabinets.domain.value_objects import MaterialSpec, Position


class TestComponentContext:
    """Tests for ComponentContext dataclass."""

    def test_create_context_with_required_fields(self) -> None:
        """Test creating a ComponentContext with all required fields."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=10.0, y=5.0)

        context = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert context.width == 24.0
        assert context.height == 30.0
        assert context.depth == 12.0
        assert context.material == material
        assert context.position == position
        assert context.section_index == 0
        assert context.cabinet_width == 48.0
        assert context.cabinet_height == 84.0
        assert context.cabinet_depth == 12.0

    def test_create_context_with_optional_adjacency_fields(self) -> None:
        """Test creating a ComponentContext with adjacency information."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=10.0, y=5.0)

        context = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=1,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
            adjacent_left="shelf",
            adjacent_right="divider",
            adjacent_above="top_panel",
            adjacent_below="bottom_panel",
        )

        assert context.adjacent_left == "shelf"
        assert context.adjacent_right == "divider"
        assert context.adjacent_above == "top_panel"
        assert context.adjacent_below == "bottom_panel"

    def test_optional_adjacency_fields_default_to_none(self) -> None:
        """Test that optional adjacency fields default to None."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=0.0, y=0.0)

        context = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert context.adjacent_left is None
        assert context.adjacent_right is None
        assert context.adjacent_above is None
        assert context.adjacent_below is None

    def test_context_is_immutable(self) -> None:
        """Test that ComponentContext is frozen and cannot be modified."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=0.0, y=0.0)

        context = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        with pytest.raises(AttributeError):
            context.width = 30.0  # type: ignore[misc]

        with pytest.raises(AttributeError):
            context.section_index = 1  # type: ignore[misc]

        with pytest.raises(AttributeError):
            context.adjacent_left = "shelf"  # type: ignore[misc]

    def test_context_equality(self) -> None:
        """Test that two contexts with same values are equal."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=10.0, y=5.0)

        context1 = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        context2 = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert context1 == context2

    def test_context_hashable(self) -> None:
        """Test that ComponentContext can be used in sets and as dict keys."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=10.0, y=5.0)

        context = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        # Should be hashable
        context_set = {context}
        assert context in context_set

        # Can be used as dict key
        context_dict = {context: "test"}
        assert context_dict[context] == "test"

    def test_context_with_different_materials(self) -> None:
        """Test creating contexts with different material specifications."""
        position = Position(x=0.0, y=0.0)

        # Standard 3/4 inch plywood
        context_3_4 = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_3_4(),
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        # Standard 1/2 inch plywood
        context_1_2 = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=MaterialSpec.standard_1_2(),
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert context_3_4.material.thickness == 0.75
        assert context_1_2.material.thickness == 0.5
        assert context_3_4 != context_1_2

    def test_context_with_different_section_indices(self) -> None:
        """Test creating contexts for different sections."""
        material = MaterialSpec.standard_3_4()
        position = Position(x=0.0, y=0.0)

        context_section_0 = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=0,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        context_section_1 = ComponentContext(
            width=24.0,
            height=30.0,
            depth=12.0,
            material=material,
            position=position,
            section_index=1,
            cabinet_width=48.0,
            cabinet_height=84.0,
            cabinet_depth=12.0,
        )

        assert context_section_0.section_index == 0
        assert context_section_1.section_index == 1
        assert context_section_0 != context_section_1
