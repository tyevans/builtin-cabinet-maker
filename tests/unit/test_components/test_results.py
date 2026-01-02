"""Tests for ValidationResult, GenerationResult, and HardwareItem."""

import pytest

from cabinets.domain.components.results import (
    GenerationResult,
    HardwareItem,
    ValidationResult,
)
from cabinets.domain.entities import Panel
from cabinets.domain.value_objects import CutPiece, MaterialSpec, PanelType, Position


class TestHardwareItem:
    """Tests for HardwareItem dataclass."""

    def test_create_hardware_item_with_required_fields(self) -> None:
        """Test creating a HardwareItem with required fields only."""
        item = HardwareItem(name="Wood Screw #8 x 1.5in", quantity=24)

        assert item.name == "Wood Screw #8 x 1.5in"
        assert item.quantity == 24
        assert item.sku is None
        assert item.notes is None

    def test_create_hardware_item_with_all_fields(self) -> None:
        """Test creating a HardwareItem with all fields."""
        item = HardwareItem(
            name="European Cabinet Hinge",
            quantity=4,
            sku="BLUM-35MM-110",
            notes="Use 35mm boring bit",
        )

        assert item.name == "European Cabinet Hinge"
        assert item.quantity == 4
        assert item.sku == "BLUM-35MM-110"
        assert item.notes == "Use 35mm boring bit"

    def test_hardware_item_is_immutable(self) -> None:
        """Test that HardwareItem is frozen and cannot be modified."""
        item = HardwareItem(name="Shelf Pin", quantity=16)

        with pytest.raises(AttributeError):
            item.name = "Different Name"  # type: ignore[misc]

        with pytest.raises(AttributeError):
            item.quantity = 32  # type: ignore[misc]

    def test_hardware_item_equality(self) -> None:
        """Test that two HardwareItems with same values are equal."""
        item1 = HardwareItem(name="Shelf Pin", quantity=16, sku="SP-5MM")
        item2 = HardwareItem(name="Shelf Pin", quantity=16, sku="SP-5MM")

        assert item1 == item2

    def test_hardware_item_hashable(self) -> None:
        """Test that HardwareItem can be used in sets and as dict keys."""
        item = HardwareItem(name="Shelf Pin", quantity=16)

        item_set = {item}
        assert item in item_set

        item_dict = {item: "test"}
        assert item_dict[item] == "test"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_validation_result_is_valid(self) -> None:
        """Test that default ValidationResult has no errors or warnings."""
        result = ValidationResult()

        assert result.errors == ()
        assert result.warnings == ()
        assert result.is_valid is True

    def test_validation_result_ok_without_warnings(self) -> None:
        """Test ValidationResult.ok() without warnings."""
        result = ValidationResult.ok()

        assert result.errors == ()
        assert result.warnings == ()
        assert result.is_valid is True

    def test_validation_result_ok_with_warnings(self) -> None:
        """Test ValidationResult.ok() with warnings."""
        result = ValidationResult.ok(
            warnings=["Width is near minimum", "Consider thicker material"]
        )

        assert result.errors == ()
        assert result.warnings == ("Width is near minimum", "Consider thicker material")
        assert result.is_valid is True

    def test_validation_result_fail_with_errors_only(self) -> None:
        """Test ValidationResult.fail() with errors only."""
        result = ValidationResult.fail(errors=["Width too small", "Invalid material"])

        assert result.errors == ("Width too small", "Invalid material")
        assert result.warnings == ()
        assert result.is_valid is False

    def test_validation_result_fail_with_errors_and_warnings(self) -> None:
        """Test ValidationResult.fail() with both errors and warnings."""
        result = ValidationResult.fail(
            errors=["Width too small"],
            warnings=["Depth is near minimum"],
        )

        assert result.errors == ("Width too small",)
        assert result.warnings == ("Depth is near minimum",)
        assert result.is_valid is False

    def test_validation_result_is_immutable(self) -> None:
        """Test that ValidationResult is frozen and cannot be modified."""
        result = ValidationResult.ok()

        with pytest.raises(AttributeError):
            result.errors = ("new error",)  # type: ignore[misc]

        with pytest.raises(AttributeError):
            result.warnings = ("new warning",)  # type: ignore[misc]

    def test_validation_result_equality(self) -> None:
        """Test that two ValidationResults with same values are equal."""
        result1 = ValidationResult.fail(errors=["Error 1"], warnings=["Warning 1"])
        result2 = ValidationResult.fail(errors=["Error 1"], warnings=["Warning 1"])

        assert result1 == result2

    def test_validation_result_hashable(self) -> None:
        """Test that ValidationResult can be used in sets and as dict keys."""
        result = ValidationResult.ok(warnings=["test warning"])

        result_set = {result}
        assert result in result_set

        result_dict = {result: "test"}
        assert result_dict[result] == "test"

    def test_validation_result_ok_with_empty_list(self) -> None:
        """Test ValidationResult.ok() with empty warnings list."""
        result = ValidationResult.ok(warnings=[])

        assert result.warnings == ()
        assert result.is_valid is True

    def test_validation_result_fail_with_empty_warnings(self) -> None:
        """Test ValidationResult.fail() with empty warnings list."""
        result = ValidationResult.fail(errors=["Error"], warnings=[])

        assert result.errors == ("Error",)
        assert result.warnings == ()
        assert result.is_valid is False


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_default_generation_result_is_empty(self) -> None:
        """Test that default GenerationResult has empty tuples."""
        result = GenerationResult()

        assert result.panels == ()
        assert result.cut_pieces == ()
        assert result.hardware == ()

    def test_generation_result_with_panels(self) -> None:
        """Test creating GenerationResult with panels."""
        material = MaterialSpec.standard_3_4()
        panel = Panel(
            panel_type=PanelType.SHELF,
            width=23.25,
            height=11.5,
            material=material,
            position=Position(0.75, 20.0),
        )

        result = GenerationResult(panels=(panel,))

        assert len(result.panels) == 1
        assert result.panels[0] == panel

    def test_generation_result_with_cut_pieces(self) -> None:
        """Test creating GenerationResult with cut pieces."""
        material = MaterialSpec.standard_3_4()
        cut_piece = CutPiece(
            width=23.25,
            height=11.5,
            quantity=3,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=material,
        )

        result = GenerationResult(cut_pieces=(cut_piece,))

        assert len(result.cut_pieces) == 1
        assert result.cut_pieces[0] == cut_piece

    def test_generation_result_with_hardware(self) -> None:
        """Test creating GenerationResult with hardware items."""
        hardware = HardwareItem(name="Shelf Pin", quantity=4)

        result = GenerationResult(hardware=(hardware,))

        assert len(result.hardware) == 1
        assert result.hardware[0] == hardware

    def test_generation_result_with_all_fields(self) -> None:
        """Test creating GenerationResult with all fields populated."""
        material = MaterialSpec.standard_3_4()

        panel = Panel(
            panel_type=PanelType.SHELF,
            width=23.25,
            height=11.5,
            material=material,
            position=Position(0.75, 20.0),
        )

        cut_piece = CutPiece(
            width=23.25,
            height=11.5,
            quantity=1,
            label="Shelf",
            panel_type=PanelType.SHELF,
            material=material,
        )

        hardware = HardwareItem(name="Shelf Pin", quantity=4)

        result = GenerationResult(
            panels=(panel,),
            cut_pieces=(cut_piece,),
            hardware=(hardware,),
        )

        assert len(result.panels) == 1
        assert len(result.cut_pieces) == 1
        assert len(result.hardware) == 1

    def test_generation_result_from_panels(self) -> None:
        """Test GenerationResult.from_panels() factory method."""
        material = MaterialSpec.standard_3_4()

        panels = [
            Panel(
                panel_type=PanelType.SHELF,
                width=23.25,
                height=11.5,
                material=material,
                position=Position(0.75, 20.0),
            ),
            Panel(
                panel_type=PanelType.SHELF,
                width=23.25,
                height=11.5,
                material=material,
                position=Position(0.75, 40.0),
            ),
        ]

        result = GenerationResult.from_panels(panels)

        assert len(result.panels) == 2
        assert result.panels[0] == panels[0]
        assert result.panels[1] == panels[1]
        assert result.cut_pieces == ()
        assert result.hardware == ()

    def test_generation_result_from_panels_with_empty_list(self) -> None:
        """Test GenerationResult.from_panels() with empty list."""
        result = GenerationResult.from_panels([])

        assert result.panels == ()
        assert result.cut_pieces == ()
        assert result.hardware == ()

    def test_generation_result_is_immutable(self) -> None:
        """Test that GenerationResult is frozen and cannot be modified."""
        result = GenerationResult()

        with pytest.raises(AttributeError):
            result.panels = ()  # type: ignore[misc]

        with pytest.raises(AttributeError):
            result.cut_pieces = ()  # type: ignore[misc]

        with pytest.raises(AttributeError):
            result.hardware = ()  # type: ignore[misc]

    def test_generation_result_equality(self) -> None:
        """Test that two GenerationResults with same values are equal."""
        hardware = HardwareItem(name="Shelf Pin", quantity=4)

        result1 = GenerationResult(hardware=(hardware,))
        result2 = GenerationResult(hardware=(hardware,))

        assert result1 == result2

    def test_generation_result_not_hashable_due_to_metadata(self) -> None:
        """Test that GenerationResult is not hashable due to mutable metadata dict.

        The metadata field uses dict[str, Any] for flexibility, which makes
        the dataclass unhashable. This is an intentional trade-off to allow
        components to include structured data like DadoSpec and PinHolePattern.
        """
        result = GenerationResult()

        with pytest.raises(TypeError, match="unhashable type"):
            hash(result)

    def test_generation_result_metadata_defaults_to_empty_dict(self) -> None:
        """Test that metadata field defaults to an empty dict."""
        result = GenerationResult()

        assert result.metadata == {}
        assert isinstance(result.metadata, dict)

    def test_generation_result_from_panels_metadata_defaults_to_empty_dict(
        self,
    ) -> None:
        """Test that from_panels() factory leaves metadata as empty dict."""
        material = MaterialSpec.standard_3_4()
        panels = [
            Panel(
                panel_type=PanelType.SHELF,
                width=23.25,
                height=11.5,
                material=material,
                position=Position(0.75, 20.0),
            ),
        ]

        result = GenerationResult.from_panels(panels)

        assert result.metadata == {}

    def test_generation_result_with_metadata(self) -> None:
        """Test creating GenerationResult with metadata."""
        metadata = {
            "dado_specs": [{"depth": 0.25, "width": 0.75}],
            "pin_hole_patterns": [],
        }

        result = GenerationResult(metadata=metadata)

        assert result.metadata == metadata
        assert result.metadata["dado_specs"] == [{"depth": 0.25, "width": 0.75}]

    def test_generation_result_metadata_field_cannot_be_reassigned(self) -> None:
        """Test that metadata field cannot be reassigned (frozen dataclass)."""
        result = GenerationResult()

        with pytest.raises(AttributeError):
            result.metadata = {"new": "value"}  # type: ignore[misc]

    def test_generation_result_panels_are_tuples_not_lists(self) -> None:
        """Test that from_panels converts lists to tuples."""
        material = MaterialSpec.standard_3_4()
        panels = [
            Panel(
                panel_type=PanelType.SHELF,
                width=23.25,
                height=11.5,
                material=material,
                position=Position(0.75, 20.0),
            ),
        ]

        result = GenerationResult.from_panels(panels)

        assert isinstance(result.panels, tuple)
