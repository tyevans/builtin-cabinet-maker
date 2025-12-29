"""Tests for OutsideCornerService."""

import pytest

from cabinets.domain.entities import Panel
from cabinets.domain.services import OutsideCornerService
from cabinets.domain.value_objects import (
    AngleCut,
    MaterialSpec,
    OutsideCornerConfig,
    PanelType,
)


class TestOutsideCornerServiceIsOutsideCorner:
    """Tests for is_outside_corner()"""

    def test_90_degrees_is_not_outside(self):
        """90-degree angle is an inside corner."""
        service = OutsideCornerService()
        assert service.is_outside_corner(90) is False
        assert service.is_outside_corner(-90) is False

    def test_0_degrees_is_not_outside(self):
        """0-degree angle (straight) is not an outside corner."""
        service = OutsideCornerService()
        assert service.is_outside_corner(0) is False

    def test_120_degrees_is_outside(self):
        """Angles > 90 are outside corners."""
        service = OutsideCornerService()
        assert service.is_outside_corner(120) is True
        assert service.is_outside_corner(-120) is True

    def test_135_degrees_is_outside(self):
        """135-degree angle is an outside corner."""
        service = OutsideCornerService()
        assert service.is_outside_corner(135) is True
        assert service.is_outside_corner(-135) is True


class TestOutsideCornerServiceAngledFacePanel:
    """Tests for calculate_angled_face_panel()"""

    def test_generates_diagonal_face_panel(self):
        """Creates a DIAGONAL_FACE panel."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="angled_face", face_angle=45)
        material = MaterialSpec(thickness=0.75)

        panel = service.calculate_angled_face_panel(config, 84, 12, material)

        assert panel.panel_type == PanelType.DIAGONAL_FACE
        assert panel.height == 84
        assert panel.material == material

    def test_panel_has_angle_cut_metadata(self):
        """Panel includes cut metadata for angled edges."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="angled_face", face_angle=45)
        material = MaterialSpec(thickness=0.75)

        panel = service.calculate_angled_face_panel(config, 84, 12, material)

        assert panel.cut_metadata is not None
        assert "angle_cuts" in panel.cut_metadata
        assert panel.cut_metadata["corner_treatment"] == "angled_face"

    def test_panel_width_calculation(self):
        """Panel width is calculated based on depth and face angle."""
        import math

        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="angled_face", face_angle=45)
        material = MaterialSpec(thickness=0.75)
        depth = 12

        panel = service.calculate_angled_face_panel(config, 84, depth, material)

        # Expected width = 2 * depth * tan(face_angle/2)
        expected_width = 2 * depth * math.tan(math.radians(45 / 2))
        assert panel.width == pytest.approx(expected_width)


class TestOutsideCornerServiceFillerPanel:
    """Tests for calculate_filler_panel()"""

    def test_generates_filler_panel(self):
        """Creates a FILLER panel."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="butted_filler", filler_width=4)
        material = MaterialSpec(thickness=0.75)

        panel = service.calculate_filler_panel(config, 84, material)

        assert panel.panel_type == PanelType.FILLER
        assert panel.width == 4
        assert panel.height == 84

    def test_panel_has_filler_metadata(self):
        """Panel includes butted_filler metadata."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="butted_filler", filler_width=3)
        material = MaterialSpec(thickness=0.75)

        panel = service.calculate_filler_panel(config, 84, material)

        assert panel.cut_metadata is not None
        assert panel.cut_metadata["corner_treatment"] == "butted_filler"


class TestOutsideCornerServiceGenerateCornerPanels:
    """Tests for generate_corner_panels()"""

    def test_angled_face_returns_one_panel(self):
        """angled_face treatment returns one DIAGONAL_FACE panel."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="angled_face")
        material = MaterialSpec(thickness=0.75)

        panels = service.generate_corner_panels(config, 84, 12, material)

        assert len(panels) == 1
        assert panels[0].panel_type == PanelType.DIAGONAL_FACE

    def test_butted_filler_returns_one_panel(self):
        """butted_filler treatment returns one FILLER panel."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="butted_filler")
        material = MaterialSpec(thickness=0.75)

        panels = service.generate_corner_panels(config, 84, 12, material)

        assert len(panels) == 1
        assert panels[0].panel_type == PanelType.FILLER

    def test_wrap_around_falls_back_to_angled_face(self):
        """wrap_around treatment falls back to angled_face (deferred feature)."""
        service = OutsideCornerService()
        config = OutsideCornerConfig(treatment="wrap_around")
        material = MaterialSpec(thickness=0.75)

        panels = service.generate_corner_panels(config, 84, 12, material)

        assert len(panels) == 1
        assert panels[0].panel_type == PanelType.DIAGONAL_FACE


class TestOutsideCornerServiceSidePanelAngleCut:
    """Tests for calculate_side_panel_angle_cut()"""

    def test_no_cut_for_90_degrees(self):
        """Returns None for standard 90-degree junction."""
        service = OutsideCornerService()

        assert service.calculate_side_panel_angle_cut(90, "left") is None
        assert service.calculate_side_panel_angle_cut(-90, "right") is None
        assert service.calculate_side_panel_angle_cut(0, "left") is None

    def test_angle_cut_for_45_degree_wall(self):
        """Calculates angle cut for 45-degree wall junction."""
        service = OutsideCornerService()

        cut = service.calculate_side_panel_angle_cut(45, "right")

        assert cut is not None
        assert cut.edge == "right"
        assert cut.angle == pytest.approx(22.5)  # (90 - 45) / 2
        assert cut.bevel is True

    def test_angle_cut_for_135_degree_wall(self):
        """Calculates angle cut for 135-degree outside corner."""
        service = OutsideCornerService()

        cut = service.calculate_side_panel_angle_cut(135, "left")

        assert cut is not None
        assert cut.edge == "left"
        assert cut.angle == pytest.approx(22.5)  # (135 - 90) / 2
        assert cut.bevel is True

    def test_angle_cut_left_side(self):
        """Verifies left side cuts have left edge."""
        service = OutsideCornerService()

        cut = service.calculate_side_panel_angle_cut(60, "left")

        assert cut is not None
        assert cut.edge == "left"
        assert cut.angle == pytest.approx(15.0)  # (90 - 60) / 2

    def test_angle_cut_negative_angle(self):
        """Handles negative wall angles correctly."""
        service = OutsideCornerService()

        cut = service.calculate_side_panel_angle_cut(-45, "right")

        assert cut is not None
        assert cut.edge == "right"
        assert cut.angle == pytest.approx(22.5)  # (90 - 45) / 2
        assert cut.bevel is True
