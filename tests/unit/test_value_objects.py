"""Unit tests for domain value objects.

These tests verify:
- CeilingSlope creation, validation, and height_at_position calculation
- Skylight creation, validation, and void_at_depth calculation
- OutsideCornerConfig creation and validation
- AngleCut, TaperSpec, NotchSpec, PanelCutMetadata creation and validation
- CutPiece cut_metadata support
"""

from math import tan, radians

import pytest

from cabinets.domain.value_objects import (
    AngleCut,
    CeilingSlope,
    CutPiece,
    MaterialSpec,
    NotchSpec,
    OutsideCornerConfig,
    PanelCutMetadata,
    PanelType,
    Skylight,
    TaperSpec,
)


class TestCeilingSlope:
    """Tests for CeilingSlope value object."""

    def test_valid_creation_minimal(self) -> None:
        """CeilingSlope should be created with required fields."""
        slope = CeilingSlope(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert slope.angle == 30.0
        assert slope.start_height == 96.0
        assert slope.direction == "left_to_right"
        assert slope.min_height == 24.0  # default

    def test_valid_creation_full(self) -> None:
        """CeilingSlope should accept all fields."""
        slope = CeilingSlope(
            angle=45.0,
            start_height=108.0,
            direction="right_to_left",
            min_height=30.0,
        )
        assert slope.angle == 45.0
        assert slope.start_height == 108.0
        assert slope.direction == "right_to_left"
        assert slope.min_height == 30.0

    def test_valid_direction_front_to_back(self) -> None:
        """CeilingSlope should accept front_to_back direction."""
        slope = CeilingSlope(
            angle=20.0,
            start_height=96.0,
            direction="front_to_back",
        )
        assert slope.direction == "front_to_back"

    def test_valid_angle_zero(self) -> None:
        """CeilingSlope should accept 0 degree angle (flat ceiling)."""
        slope = CeilingSlope(
            angle=0.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert slope.angle == 0.0

    def test_valid_angle_sixty(self) -> None:
        """CeilingSlope should accept 60 degree angle (maximum)."""
        slope = CeilingSlope(
            angle=60.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert slope.angle == 60.0

    def test_valid_min_height_zero(self) -> None:
        """CeilingSlope should accept 0 minimum height."""
        slope = CeilingSlope(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
            min_height=0.0,
        )
        assert slope.min_height == 0.0

    def test_rejects_angle_below_zero(self) -> None:
        """CeilingSlope should reject negative angles."""
        with pytest.raises(ValueError) as exc_info:
            CeilingSlope(
                angle=-5.0,
                start_height=96.0,
                direction="left_to_right",
            )
        assert "Slope angle must be between 0 and 60 degrees" in str(exc_info.value)

    def test_rejects_angle_above_sixty(self) -> None:
        """CeilingSlope should reject angles above 60 degrees."""
        with pytest.raises(ValueError) as exc_info:
            CeilingSlope(
                angle=65.0,
                start_height=96.0,
                direction="left_to_right",
            )
        assert "Slope angle must be between 0 and 60 degrees" in str(exc_info.value)

    def test_rejects_zero_start_height(self) -> None:
        """CeilingSlope should reject zero start height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingSlope(
                angle=30.0,
                start_height=0.0,
                direction="left_to_right",
            )
        assert "Start height must be positive" in str(exc_info.value)

    def test_rejects_negative_start_height(self) -> None:
        """CeilingSlope should reject negative start height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingSlope(
                angle=30.0,
                start_height=-10.0,
                direction="left_to_right",
            )
        assert "Start height must be positive" in str(exc_info.value)

    def test_rejects_negative_min_height(self) -> None:
        """CeilingSlope should reject negative minimum height."""
        with pytest.raises(ValueError) as exc_info:
            CeilingSlope(
                angle=30.0,
                start_height=96.0,
                direction="left_to_right",
                min_height=-5.0,
            )
        assert "Minimum height cannot be negative" in str(exc_info.value)

    def test_height_at_position_zero(self) -> None:
        """Height at position 0 should equal start_height."""
        slope = CeilingSlope(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert slope.height_at_position(0) == pytest.approx(96.0)

    def test_height_at_position_flat_ceiling(self) -> None:
        """Height should be constant for 0 degree angle."""
        slope = CeilingSlope(
            angle=0.0,
            start_height=96.0,
            direction="left_to_right",
        )
        assert slope.height_at_position(0) == pytest.approx(96.0)
        assert slope.height_at_position(24.0) == pytest.approx(96.0)
        assert slope.height_at_position(48.0) == pytest.approx(96.0)

    def test_height_at_position_45_degrees(self) -> None:
        """Height should decrease by position for 45 degree angle (tan(45) = 1)."""
        slope = CeilingSlope(
            angle=45.0,
            start_height=96.0,
            direction="left_to_right",
        )
        # tan(45) = 1, so height decreases by position
        assert slope.height_at_position(0) == pytest.approx(96.0)
        assert slope.height_at_position(24.0) == pytest.approx(96.0 - 24.0)
        assert slope.height_at_position(48.0) == pytest.approx(96.0 - 48.0)

    def test_height_at_position_30_degrees(self) -> None:
        """Height calculation should use correct trigonometry for 30 degrees."""
        slope = CeilingSlope(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
        )
        expected_at_24 = 96.0 - (24.0 * tan(radians(30.0)))
        assert slope.height_at_position(24.0) == pytest.approx(expected_at_24)

    def test_is_frozen(self) -> None:
        """CeilingSlope should be immutable."""
        slope = CeilingSlope(
            angle=30.0,
            start_height=96.0,
            direction="left_to_right",
        )
        with pytest.raises(AttributeError):
            slope.angle = 45.0  # type: ignore


class TestSkylight:
    """Tests for Skylight value object."""

    def test_valid_creation_minimal(self) -> None:
        """Skylight should be created with required fields."""
        skylight = Skylight(
            x_position=24.0,
            width=36.0,
            projection_depth=6.0,
        )
        assert skylight.x_position == 24.0
        assert skylight.width == 36.0
        assert skylight.projection_depth == 6.0
        assert skylight.projection_angle == 90.0  # default

    def test_valid_creation_full(self) -> None:
        """Skylight should accept all fields."""
        skylight = Skylight(
            x_position=12.0,
            width=48.0,
            projection_depth=8.0,
            projection_angle=75.0,
        )
        assert skylight.x_position == 12.0
        assert skylight.width == 48.0
        assert skylight.projection_depth == 8.0
        assert skylight.projection_angle == 75.0

    def test_valid_x_position_zero(self) -> None:
        """Skylight should accept 0 for x_position."""
        skylight = Skylight(
            x_position=0.0,
            width=36.0,
            projection_depth=6.0,
        )
        assert skylight.x_position == 0.0

    def test_valid_projection_angle_180(self) -> None:
        """Skylight should accept 180 degree projection angle."""
        skylight = Skylight(
            x_position=24.0,
            width=36.0,
            projection_depth=6.0,
            projection_angle=180.0,
        )
        assert skylight.projection_angle == 180.0

    def test_rejects_zero_width(self) -> None:
        """Skylight should reject zero width."""
        with pytest.raises(ValueError) as exc_info:
            Skylight(
                x_position=24.0,
                width=0.0,
                projection_depth=6.0,
            )
        assert "Skylight width must be positive" in str(exc_info.value)

    def test_rejects_negative_width(self) -> None:
        """Skylight should reject negative width."""
        with pytest.raises(ValueError) as exc_info:
            Skylight(
                x_position=24.0,
                width=-10.0,
                projection_depth=6.0,
            )
        assert "Skylight width must be positive" in str(exc_info.value)

    def test_rejects_zero_projection_depth(self) -> None:
        """Skylight should reject zero projection depth."""
        with pytest.raises(ValueError) as exc_info:
            Skylight(
                x_position=24.0,
                width=36.0,
                projection_depth=0.0,
            )
        assert "Projection depth must be positive" in str(exc_info.value)

    def test_rejects_negative_projection_depth(self) -> None:
        """Skylight should reject negative projection depth."""
        with pytest.raises(ValueError) as exc_info:
            Skylight(
                x_position=24.0,
                width=36.0,
                projection_depth=-5.0,
            )
        assert "Projection depth must be positive" in str(exc_info.value)

    def test_rejects_zero_projection_angle(self) -> None:
        """Skylight should reject zero projection angle."""
        with pytest.raises(ValueError) as exc_info:
            Skylight(
                x_position=24.0,
                width=36.0,
                projection_depth=6.0,
                projection_angle=0.0,
            )
        assert "Projection angle must be between 0 and 180 degrees" in str(
            exc_info.value
        )

    def test_rejects_projection_angle_above_180(self) -> None:
        """Skylight should reject projection angle above 180 degrees."""
        with pytest.raises(ValueError) as exc_info:
            Skylight(
                x_position=24.0,
                width=36.0,
                projection_depth=6.0,
                projection_angle=200.0,
            )
        assert "Projection angle must be between 0 and 180 degrees" in str(
            exc_info.value
        )

    def test_void_at_depth_vertical_projection(self) -> None:
        """Void at depth should equal original dimensions for 90 degree angle."""
        skylight = Skylight(
            x_position=24.0,
            width=36.0,
            projection_depth=6.0,
            projection_angle=90.0,
        )
        void_start, void_width = skylight.void_at_depth(12.0)
        assert void_start == pytest.approx(24.0)
        assert void_width == pytest.approx(36.0)

    def test_void_at_depth_angled_projection(self) -> None:
        """Void should expand for angled projection."""
        skylight = Skylight(
            x_position=24.0,
            width=36.0,
            projection_depth=6.0,
            projection_angle=45.0,
        )
        void_start, void_width = skylight.void_at_depth(12.0)
        # At 45 degrees from ceiling, 90-45=45 degrees from vertical
        # tan(45) = 1, so expansion = 12.0 * 1 = 12.0
        expected_expansion = 12.0 * tan(radians(45.0))
        assert void_start == pytest.approx(24.0 - expected_expansion / 2)
        assert void_width == pytest.approx(36.0 + expected_expansion)

    def test_void_at_depth_zero_cabinet_depth(self) -> None:
        """Void at zero depth should equal original dimensions."""
        skylight = Skylight(
            x_position=24.0,
            width=36.0,
            projection_depth=6.0,
            projection_angle=60.0,
        )
        void_start, void_width = skylight.void_at_depth(0.0)
        assert void_start == pytest.approx(24.0)
        assert void_width == pytest.approx(36.0)

    def test_is_frozen(self) -> None:
        """Skylight should be immutable."""
        skylight = Skylight(
            x_position=24.0,
            width=36.0,
            projection_depth=6.0,
        )
        with pytest.raises(AttributeError):
            skylight.width = 48.0  # type: ignore


class TestOutsideCornerConfig:
    """Tests for OutsideCornerConfig value object."""

    def test_valid_creation_defaults(self) -> None:
        """OutsideCornerConfig should be created with defaults."""
        config = OutsideCornerConfig()
        assert config.treatment == "angled_face"
        assert config.filler_width == 3.0
        assert config.face_angle == 45.0

    def test_valid_creation_angled_face(self) -> None:
        """OutsideCornerConfig should accept angled_face treatment."""
        config = OutsideCornerConfig(
            treatment="angled_face",
            face_angle=30.0,
        )
        assert config.treatment == "angled_face"
        assert config.face_angle == 30.0

    def test_valid_creation_butted_filler(self) -> None:
        """OutsideCornerConfig should accept butted_filler treatment."""
        config = OutsideCornerConfig(
            treatment="butted_filler",
            filler_width=4.0,
        )
        assert config.treatment == "butted_filler"
        assert config.filler_width == 4.0

    def test_valid_creation_wrap_around(self) -> None:
        """OutsideCornerConfig should accept wrap_around treatment."""
        config = OutsideCornerConfig(treatment="wrap_around")
        assert config.treatment == "wrap_around"

    def test_valid_face_angle_near_zero(self) -> None:
        """OutsideCornerConfig should accept face angle close to 0."""
        config = OutsideCornerConfig(face_angle=0.1)
        assert config.face_angle == pytest.approx(0.1)

    def test_valid_face_angle_near_ninety(self) -> None:
        """OutsideCornerConfig should accept face angle close to 90."""
        config = OutsideCornerConfig(face_angle=89.9)
        assert config.face_angle == pytest.approx(89.9)

    def test_rejects_zero_filler_width(self) -> None:
        """OutsideCornerConfig should reject zero filler width."""
        with pytest.raises(ValueError) as exc_info:
            OutsideCornerConfig(filler_width=0.0)
        assert "Filler width must be positive" in str(exc_info.value)

    def test_rejects_negative_filler_width(self) -> None:
        """OutsideCornerConfig should reject negative filler width."""
        with pytest.raises(ValueError) as exc_info:
            OutsideCornerConfig(filler_width=-2.0)
        assert "Filler width must be positive" in str(exc_info.value)

    def test_rejects_zero_face_angle(self) -> None:
        """OutsideCornerConfig should reject zero face angle."""
        with pytest.raises(ValueError) as exc_info:
            OutsideCornerConfig(face_angle=0.0)
        assert "Face angle must be between 0 and 90 degrees" in str(exc_info.value)

    def test_rejects_ninety_degree_face_angle(self) -> None:
        """OutsideCornerConfig should reject 90 degree face angle."""
        with pytest.raises(ValueError) as exc_info:
            OutsideCornerConfig(face_angle=90.0)
        assert "Face angle must be between 0 and 90 degrees" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """OutsideCornerConfig should be immutable."""
        config = OutsideCornerConfig()
        with pytest.raises(AttributeError):
            config.treatment = "wrap_around"  # type: ignore


class TestAngleCut:
    """Tests for AngleCut value object."""

    def test_valid_creation_minimal(self) -> None:
        """AngleCut should be created with required fields."""
        cut = AngleCut(edge="left", angle=45.0)
        assert cut.edge == "left"
        assert cut.angle == 45.0
        assert cut.bevel is False  # default

    def test_valid_creation_with_bevel(self) -> None:
        """AngleCut should accept bevel parameter."""
        cut = AngleCut(edge="right", angle=30.0, bevel=True)
        assert cut.edge == "right"
        assert cut.angle == 30.0
        assert cut.bevel is True

    def test_valid_edges(self) -> None:
        """AngleCut should accept all valid edge values."""
        for edge in ["left", "right", "top", "bottom"]:
            cut = AngleCut(edge=edge, angle=45.0)  # type: ignore
            assert cut.edge == edge

    def test_valid_angle_zero(self) -> None:
        """AngleCut should accept 0 degree angle (perpendicular)."""
        cut = AngleCut(edge="left", angle=0.0)
        assert cut.angle == 0.0

    def test_valid_angle_ninety(self) -> None:
        """AngleCut should accept 90 degree angle."""
        cut = AngleCut(edge="left", angle=90.0)
        assert cut.angle == 90.0

    def test_rejects_negative_angle(self) -> None:
        """AngleCut should reject negative angles."""
        with pytest.raises(ValueError) as exc_info:
            AngleCut(edge="left", angle=-5.0)
        assert "Cut angle must be between 0 and 90 degrees" in str(exc_info.value)

    def test_rejects_angle_above_ninety(self) -> None:
        """AngleCut should reject angles above 90 degrees."""
        with pytest.raises(ValueError) as exc_info:
            AngleCut(edge="left", angle=95.0)
        assert "Cut angle must be between 0 and 90 degrees" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """AngleCut should be immutable."""
        cut = AngleCut(edge="left", angle=45.0)
        with pytest.raises(AttributeError):
            cut.angle = 30.0  # type: ignore


class TestTaperSpec:
    """Tests for TaperSpec value object."""

    def test_valid_creation(self) -> None:
        """TaperSpec should be created with valid values."""
        taper = TaperSpec(
            start_height=96.0,
            end_height=72.0,
            direction="left_to_right",
        )
        assert taper.start_height == 96.0
        assert taper.end_height == 72.0
        assert taper.direction == "left_to_right"

    def test_valid_direction_right_to_left(self) -> None:
        """TaperSpec should accept right_to_left direction."""
        taper = TaperSpec(
            start_height=84.0,
            end_height=60.0,
            direction="right_to_left",
        )
        assert taper.direction == "right_to_left"

    def test_valid_increasing_taper(self) -> None:
        """TaperSpec should accept end_height greater than start_height."""
        taper = TaperSpec(
            start_height=60.0,
            end_height=84.0,
            direction="left_to_right",
        )
        assert taper.start_height == 60.0
        assert taper.end_height == 84.0

    def test_valid_equal_heights(self) -> None:
        """TaperSpec should accept equal start and end heights."""
        taper = TaperSpec(
            start_height=72.0,
            end_height=72.0,
            direction="left_to_right",
        )
        assert taper.start_height == taper.end_height

    def test_rejects_zero_start_height(self) -> None:
        """TaperSpec should reject zero start height."""
        with pytest.raises(ValueError) as exc_info:
            TaperSpec(
                start_height=0.0,
                end_height=72.0,
                direction="left_to_right",
            )
        assert "Heights must be positive" in str(exc_info.value)

    def test_rejects_negative_start_height(self) -> None:
        """TaperSpec should reject negative start height."""
        with pytest.raises(ValueError) as exc_info:
            TaperSpec(
                start_height=-10.0,
                end_height=72.0,
                direction="left_to_right",
            )
        assert "Heights must be positive" in str(exc_info.value)

    def test_rejects_zero_end_height(self) -> None:
        """TaperSpec should reject zero end height."""
        with pytest.raises(ValueError) as exc_info:
            TaperSpec(
                start_height=96.0,
                end_height=0.0,
                direction="left_to_right",
            )
        assert "Heights must be positive" in str(exc_info.value)

    def test_rejects_negative_end_height(self) -> None:
        """TaperSpec should reject negative end height."""
        with pytest.raises(ValueError) as exc_info:
            TaperSpec(
                start_height=96.0,
                end_height=-10.0,
                direction="left_to_right",
            )
        assert "Heights must be positive" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """TaperSpec should be immutable."""
        taper = TaperSpec(
            start_height=96.0,
            end_height=72.0,
            direction="left_to_right",
        )
        with pytest.raises(AttributeError):
            taper.start_height = 84.0  # type: ignore


class TestNotchSpec:
    """Tests for NotchSpec value object."""

    def test_valid_creation(self) -> None:
        """NotchSpec should be created with valid values."""
        notch = NotchSpec(
            x_offset=12.0,
            width=24.0,
            depth=6.0,
            edge="top",
        )
        assert notch.x_offset == 12.0
        assert notch.width == 24.0
        assert notch.depth == 6.0
        assert notch.edge == "top"

    def test_valid_edges(self) -> None:
        """NotchSpec should accept all valid edge values."""
        for edge in ["top", "bottom", "left", "right"]:
            notch = NotchSpec(
                x_offset=12.0,
                width=24.0,
                depth=6.0,
                edge=edge,  # type: ignore
            )
            assert notch.edge == edge

    def test_valid_zero_x_offset(self) -> None:
        """NotchSpec should accept zero x_offset."""
        notch = NotchSpec(
            x_offset=0.0,
            width=24.0,
            depth=6.0,
            edge="top",
        )
        assert notch.x_offset == 0.0

    def test_rejects_negative_x_offset(self) -> None:
        """NotchSpec should reject negative x_offset."""
        with pytest.raises(ValueError) as exc_info:
            NotchSpec(
                x_offset=-5.0,
                width=24.0,
                depth=6.0,
                edge="top",
            )
        assert "Notch x_offset cannot be negative" in str(exc_info.value)

    def test_rejects_zero_width(self) -> None:
        """NotchSpec should reject zero width."""
        with pytest.raises(ValueError) as exc_info:
            NotchSpec(
                x_offset=12.0,
                width=0.0,
                depth=6.0,
                edge="top",
            )
        assert "Notch width must be positive" in str(exc_info.value)

    def test_rejects_negative_width(self) -> None:
        """NotchSpec should reject negative width."""
        with pytest.raises(ValueError) as exc_info:
            NotchSpec(
                x_offset=12.0,
                width=-10.0,
                depth=6.0,
                edge="top",
            )
        assert "Notch width must be positive" in str(exc_info.value)

    def test_rejects_zero_depth(self) -> None:
        """NotchSpec should reject zero depth."""
        with pytest.raises(ValueError) as exc_info:
            NotchSpec(
                x_offset=12.0,
                width=24.0,
                depth=0.0,
                edge="top",
            )
        assert "Notch depth must be positive" in str(exc_info.value)

    def test_rejects_negative_depth(self) -> None:
        """NotchSpec should reject negative depth."""
        with pytest.raises(ValueError) as exc_info:
            NotchSpec(
                x_offset=12.0,
                width=24.0,
                depth=-3.0,
                edge="top",
            )
        assert "Notch depth must be positive" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """NotchSpec should be immutable."""
        notch = NotchSpec(
            x_offset=12.0,
            width=24.0,
            depth=6.0,
            edge="top",
        )
        with pytest.raises(AttributeError):
            notch.width = 36.0  # type: ignore


class TestPanelCutMetadata:
    """Tests for PanelCutMetadata value object."""

    def test_valid_creation_empty(self) -> None:
        """PanelCutMetadata should be created with defaults."""
        metadata = PanelCutMetadata()
        assert metadata.angle_cuts == ()
        assert metadata.taper is None
        assert metadata.notches == ()

    def test_valid_creation_with_angle_cuts(self) -> None:
        """PanelCutMetadata should accept angle cuts."""
        angle_cut = AngleCut(edge="left", angle=45.0)
        metadata = PanelCutMetadata(angle_cuts=(angle_cut,))
        assert len(metadata.angle_cuts) == 1
        assert metadata.angle_cuts[0] == angle_cut

    def test_valid_creation_with_multiple_angle_cuts(self) -> None:
        """PanelCutMetadata should accept multiple angle cuts."""
        cut1 = AngleCut(edge="left", angle=45.0)
        cut2 = AngleCut(edge="right", angle=30.0, bevel=True)
        metadata = PanelCutMetadata(angle_cuts=(cut1, cut2))
        assert len(metadata.angle_cuts) == 2

    def test_valid_creation_with_taper(self) -> None:
        """PanelCutMetadata should accept taper specification."""
        taper = TaperSpec(
            start_height=96.0,
            end_height=72.0,
            direction="left_to_right",
        )
        metadata = PanelCutMetadata(taper=taper)
        assert metadata.taper == taper

    def test_valid_creation_with_notches(self) -> None:
        """PanelCutMetadata should accept notches."""
        notch = NotchSpec(
            x_offset=12.0,
            width=24.0,
            depth=6.0,
            edge="top",
        )
        metadata = PanelCutMetadata(notches=(notch,))
        assert len(metadata.notches) == 1
        assert metadata.notches[0] == notch

    def test_valid_creation_full(self) -> None:
        """PanelCutMetadata should accept all fields."""
        angle_cut = AngleCut(edge="left", angle=45.0)
        taper = TaperSpec(
            start_height=96.0,
            end_height=72.0,
            direction="left_to_right",
        )
        notch = NotchSpec(
            x_offset=12.0,
            width=24.0,
            depth=6.0,
            edge="top",
        )
        metadata = PanelCutMetadata(
            angle_cuts=(angle_cut,),
            taper=taper,
            notches=(notch,),
        )
        assert len(metadata.angle_cuts) == 1
        assert metadata.taper == taper
        assert len(metadata.notches) == 1

    def test_is_frozen(self) -> None:
        """PanelCutMetadata should be immutable."""
        metadata = PanelCutMetadata()
        with pytest.raises(AttributeError):
            metadata.taper = TaperSpec(  # type: ignore
                start_height=96.0,
                end_height=72.0,
                direction="left_to_right",
            )


class TestCutPieceCutMetadata:
    """Tests for CutPiece cut_metadata field."""

    def test_cut_piece_default_no_metadata(self) -> None:
        """CutPiece should default cut_metadata to None."""
        piece = CutPiece(
            width=24.0,
            height=36.0,
            quantity=1,
            label="Test Panel",
            panel_type=PanelType.SHELF,
            material=MaterialSpec.standard_3_4(),
        )
        assert piece.cut_metadata is None

    def test_cut_piece_with_dict_metadata(self) -> None:
        """CutPiece should accept dict cut_metadata."""
        metadata = {
            "angle_cuts": [{"edge": "left", "angle": 45.0}],
            "has_taper": True,
        }
        piece = CutPiece(
            width=24.0,
            height=36.0,
            quantity=1,
            label="Angled Panel",
            panel_type=PanelType.LEFT_SIDE,
            material=MaterialSpec.standard_3_4(),
            cut_metadata=metadata,
        )
        assert piece.cut_metadata == metadata
        assert piece.cut_metadata["has_taper"] is True

    def test_cut_piece_with_empty_dict_metadata(self) -> None:
        """CutPiece should accept empty dict cut_metadata."""
        piece = CutPiece(
            width=24.0,
            height=36.0,
            quantity=1,
            label="Test Panel",
            panel_type=PanelType.SHELF,
            material=MaterialSpec.standard_3_4(),
            cut_metadata={},
        )
        assert piece.cut_metadata == {}

    def test_cut_piece_metadata_preserved_in_frozen(self) -> None:
        """CutPiece cut_metadata should be accessible after creation."""
        metadata = {"notches": [{"x_offset": 12.0, "width": 24.0}]}
        piece = CutPiece(
            width=24.0,
            height=36.0,
            quantity=1,
            label="Notched Panel",
            panel_type=PanelType.TOP,
            material=MaterialSpec.standard_3_4(),
            cut_metadata=metadata,
        )
        # Frozen dataclass should allow reading attributes
        assert piece.cut_metadata is not None
        assert "notches" in piece.cut_metadata
