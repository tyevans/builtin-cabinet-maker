"""Enhanced JSON exporter with normalized config, 3D positions, and joinery.

Exports comprehensive JSON with:
- FR-03.1: Normalized configuration (all defaults resolved)
- FR-03.2: All calculated dimensions per piece
- FR-03.3: 3D positions for each panel
- FR-03.4: Joinery specifications and validation warnings
- FR-03.5: Schema version field for compatibility
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from cabinets.domain.value_objects import BoundingBox3D, PanelType
from cabinets.infrastructure.exporters.base import ExporterRegistry

if TYPE_CHECKING:
    from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput
    from cabinets.domain.entities import Cabinet, Panel
    from cabinets.domain.services.woodworking import ConnectionJoinery


logger = logging.getLogger(__name__)


# Current schema version for enhanced JSON output
SCHEMA_VERSION = "1.0"


@ExporterRegistry.register("json")
class EnhancedJsonExporter:
    """Enhanced JSON exporter with comprehensive cabinet data.

    Exports cabinet layout data as JSON including:
    - Normalized input configuration
    - Cabinet dimensions and sections
    - Detailed piece list with 3D positions
    - Cut list for manufacturing
    - Bill of materials (sheet goods, hardware, edge banding)
    - Joinery specifications per piece
    - Validation warnings and advisories

    Attributes:
        format_name: "json"
        file_extension: "json"
    """

    format_name: ClassVar[str] = "json"
    file_extension: ClassVar[str] = "json"

    def __init__(
        self,
        include_3d_positions: bool = True,
        include_joinery: bool = True,
        include_warnings: bool = True,
        include_bom: bool = True,
        indent: int = 2,
    ) -> None:
        """Initialize the enhanced JSON exporter.

        Args:
            include_3d_positions: Whether to include 3D position data for panels.
            include_joinery: Whether to include joinery specifications.
            include_warnings: Whether to include validation warnings.
            include_bom: Whether to include bill of materials.
            indent: JSON indentation level (default 2 spaces).
        """
        self.include_3d_positions = include_3d_positions
        self.include_joinery = include_joinery
        self.include_warnings = include_warnings
        self.include_bom = include_bom
        self.indent = indent

    def export(self, output: LayoutOutput | RoomLayoutOutput, path: Path) -> None:
        """Export enhanced JSON to file.

        Args:
            output: The layout output to export.
            path: Path where the JSON file will be saved.
        """
        content = self.export_string(output)
        path.write_text(content)
        logger.info(f"Exported enhanced JSON to {path}")

    def export_string(self, output: LayoutOutput | RoomLayoutOutput) -> str:
        """Generate enhanced JSON string.

        Args:
            output: The layout output to export.

        Returns:
            JSON string with comprehensive cabinet data.
        """
        data = self._build_output(output)
        return json.dumps(data, indent=self.indent, default=str)

    def _build_output(self, output: LayoutOutput | RoomLayoutOutput) -> dict[str, Any]:
        """Build the complete JSON structure.

        Args:
            output: The layout output to convert.

        Returns:
            Dictionary containing all export data.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "config": self._extract_config(output),
        }

        if isinstance(output, RoomLayoutOutput):
            result["room"] = self._extract_room(output)
            result["cabinets"] = [
                self._extract_cabinet(cab) for cab in output.cabinets
            ]
            # Combine pieces from all cabinets
            all_pieces: list[dict[str, Any]] = []
            for i, cab in enumerate(output.cabinets):
                joinery_list = self._get_joinery_list(cab) if self.include_joinery else []
                cabinet_pieces = self._extract_pieces(cab, joinery_list, cabinet_index=i)
                all_pieces.extend(cabinet_pieces)
            result["pieces"] = all_pieces
        else:  # LayoutOutput
            result["cabinet"] = self._extract_cabinet(output.cabinet)
            joinery_list = self._get_joinery_list(output.cabinet) if self.include_joinery else []
            result["pieces"] = self._extract_pieces(output.cabinet, joinery_list)

        result["cut_list"] = self._extract_cut_list(output)

        if self.include_bom:
            result["bom"] = self._extract_bom(output)

        if self.include_warnings:
            result["warnings"] = self._extract_warnings(output)
        else:
            result["warnings"] = []

        return result

    def _extract_config(self, output: LayoutOutput | RoomLayoutOutput) -> dict[str, Any]:
        """Extract normalized configuration from output.

        Captures the resolved configuration including all defaults.

        Args:
            output: The layout output containing cabinet configuration.

        Returns:
            Dictionary with normalized configuration values.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        if isinstance(output, RoomLayoutOutput):
            if not output.cabinets:
                return {}
            # Use first cabinet for material info
            cabinet = output.cabinets[0]
            return {
                "type": "room_layout",
                "room_name": output.room.name,
                "wall_count": len(output.room.walls),
                "material": {
                    "type": cabinet.material.material_type.value,
                    "thickness": cabinet.material.thickness,
                },
                "back_material": {
                    "type": cabinet.back_material.material_type.value,
                    "thickness": cabinet.back_material.thickness,
                } if cabinet.back_material else None,
            }
        else:  # LayoutOutput
            cabinet = output.cabinet
            return {
                "type": "single_cabinet",
                "dimensions": {
                    "width": cabinet.width,
                    "height": cabinet.height,
                    "depth": cabinet.depth,
                },
                "material": {
                    "type": cabinet.material.material_type.value,
                    "thickness": cabinet.material.thickness,
                },
                "back_material": {
                    "type": cabinet.back_material.material_type.value,
                    "thickness": cabinet.back_material.thickness,
                } if cabinet.back_material else None,
                "section_count": len(cabinet.sections),
                "default_shelf_count": cabinet.default_shelf_count,
            }

    def _extract_room(self, output: RoomLayoutOutput) -> dict[str, Any]:
        """Extract room information for room layouts.

        Args:
            output: The room layout output.

        Returns:
            Dictionary with room dimensions and wall details.
        """
        room = output.room
        walls = []
        for wall in room.walls:
            walls.append({
                "length": wall.length,
                "height": wall.height,
                "depth": wall.depth,
                "angle": wall.angle,
                "name": wall.name,
            })

        return {
            "name": room.name,
            "walls": walls,
            "total_length": room.total_length,
            "bounding_box": {
                "width": room.bounding_box[0],
                "depth": room.bounding_box[1],
            },
            "is_closed": room.is_closed,
        }

    def _extract_cabinet(self, cabinet: Cabinet) -> dict[str, Any]:
        """Extract cabinet dimensions and sections.

        Args:
            cabinet: The cabinet entity to extract from.

        Returns:
            Dictionary with cabinet structure details.
        """
        sections = []
        for section in cabinet.sections:
            sections.append({
                "width": section.width,
                "height": section.height,
                "depth": section.depth,
                "position": {"x": section.position.x, "y": section.position.y},
                "shelf_count": len(section.shelves),
                "panel_count": len(section.panels),
                "section_type": section.section_type.value,
            })

        result: dict[str, Any] = {
            "dimensions": {
                "width": cabinet.width,
                "height": cabinet.height,
                "depth": cabinet.depth,
            },
            "interior_dimensions": {
                "width": cabinet.interior_width,
                "height": cabinet.interior_height,
                "depth": cabinet.interior_depth,
            },
            "sections": sections,
        }

        # Include zone information if present
        if cabinet.base_zone:
            result["base_zone"] = cabinet.base_zone
        if cabinet.crown_molding:
            result["crown_molding"] = cabinet.crown_molding
        if cabinet.light_rail:
            result["light_rail"] = cabinet.light_rail
        if cabinet.row_heights:
            result["row_heights"] = cabinet.row_heights

        return result

    def _extract_pieces(
        self,
        cabinet: Cabinet,
        joinery_list: list[ConnectionJoinery],
        cabinet_index: int | None = None,
    ) -> list[dict[str, Any]]:
        """Extract pieces with dimensions and 3D positions.

        Args:
            cabinet: The cabinet to extract pieces from.
            joinery_list: List of joinery connections for this cabinet.
            cabinet_index: Optional cabinet index for room layouts.

        Returns:
            List of piece dictionaries with full details.
        """
        from cabinets.domain.services import Panel3DMapper

        panels = cabinet.get_all_panels()
        mapper = Panel3DMapper(cabinet)

        pieces: list[dict[str, Any]] = []
        piece_id_counter: dict[str, int] = {}

        for panel in panels:
            # Generate unique piece ID
            panel_type_key = panel.panel_type.value.upper()[:2]
            if panel_type_key not in piece_id_counter:
                piece_id_counter[panel_type_key] = 0
            piece_id_counter[panel_type_key] += 1
            piece_id = f"{panel_type_key}-{piece_id_counter[panel_type_key]}"

            if cabinet_index is not None:
                piece_id = f"C{cabinet_index + 1}-{piece_id}"

            piece: dict[str, Any] = {
                "id": piece_id,
                "label": panel.panel_type.value.replace("_", " ").title(),
                "dimensions": {
                    "width": panel.width,
                    "height": panel.height,
                    "thickness": panel.material.thickness,
                },
                "panel_type": panel.panel_type.value,
                "material": {
                    "type": panel.material.material_type.value,
                    "thickness": panel.material.thickness,
                },
            }

            # Add 3D position if enabled
            if self.include_3d_positions:
                try:
                    bbox = mapper.map_panel(panel)
                    piece["position_3d"] = self._bbox_to_dict(bbox)
                except Exception as e:
                    logger.debug(f"Could not compute 3D position for {piece_id}: {e}")

            # Add joinery connections if enabled
            if self.include_joinery and joinery_list:
                panel_joinery = self._get_joinery_for_piece(panel, joinery_list)
                if panel_joinery:
                    piece["joinery"] = panel_joinery

            # Add panel metadata if present
            if panel.metadata:
                piece["metadata"] = panel.metadata
            if panel.cut_metadata:
                piece["cut_metadata"] = panel.cut_metadata

            pieces.append(piece)

        return pieces

    def _bbox_to_dict(self, bbox: BoundingBox3D) -> dict[str, float]:
        """Convert BoundingBox3D to dictionary.

        Args:
            bbox: The 3D bounding box to convert.

        Returns:
            Dictionary with position and size values.
        """
        return {
            "x": bbox.origin.x,
            "y": bbox.origin.y,
            "z": bbox.origin.z,
            "width": bbox.size_x,
            "depth": bbox.size_y,
            "height": bbox.size_z,
        }

    def _get_joinery_for_piece(
        self, panel: Panel, joinery_list: list[ConnectionJoinery]
    ) -> list[dict[str, Any]]:
        """Get joinery connections for a specific piece.

        Args:
            panel: The panel to find joinery for.
            joinery_list: Full list of joinery connections.

        Returns:
            List of joinery dictionaries for this panel.
        """
        connections: list[dict[str, Any]] = []

        for joint in joinery_list:
            # Check if this panel is involved in the joint
            if joint.from_panel == panel.panel_type:
                connections.append({
                    "connection_to": joint.to_panel.value,
                    "role": "receives",  # This panel receives the joint (e.g., has dado)
                    "joint_type": joint.joint.joint_type.value,
                    "depth": joint.joint.depth,
                    "width": joint.joint.width,
                    "location": joint.location_description,
                })
            elif joint.to_panel == panel.panel_type:
                connections.append({
                    "connection_to": joint.from_panel.value,
                    "role": "fits_into",  # This panel fits into the joint
                    "joint_type": joint.joint.joint_type.value,
                    "depth": joint.joint.depth,
                    "width": joint.joint.width,
                    "location": joint.location_description,
                })

        return connections

    def _get_joinery_list(self, cabinet: Cabinet) -> list[ConnectionJoinery]:
        """Get joinery connections for a cabinet.

        Args:
            cabinet: The cabinet to analyze.

        Returns:
            List of joinery connections.
        """
        try:
            from cabinets.domain.services.woodworking import WoodworkingIntelligence

            intel = WoodworkingIntelligence()
            return intel.get_joinery(cabinet)
        except Exception as e:
            logger.debug(f"Could not get joinery information: {e}")
            return []

    def _extract_cut_list(self, output: LayoutOutput | RoomLayoutOutput) -> list[dict[str, Any]]:
        """Extract cut list with all details.

        Args:
            output: The layout output to extract from.

        Returns:
            List of cut piece dictionaries.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
        else:
            cut_list = output.cut_list

        pieces: list[dict[str, Any]] = []
        for piece in cut_list:
            piece_dict: dict[str, Any] = {
                "label": piece.label,
                "panel_type": piece.panel_type.value,
                "dimensions": {
                    "width": piece.width,
                    "height": piece.height,
                    "thickness": piece.material.thickness,
                },
                "quantity": piece.quantity,
                "area_sq_in": piece.area,
                "area_sq_ft": piece.area / 144,
                "material": {
                    "type": piece.material.material_type.value,
                    "thickness": piece.material.thickness,
                },
            }

            # Include cut metadata if present
            if piece.cut_metadata:
                piece_dict["cut_metadata"] = piece.cut_metadata

            pieces.append(piece_dict)

        return pieces

    def _extract_bom(self, output: LayoutOutput | RoomLayoutOutput) -> dict[str, Any]:
        """Extract bill of materials.

        Args:
            output: The layout output to extract from.

        Returns:
            Dictionary with sheet goods, hardware, and edge banding.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        # Sheet goods calculation
        sheet_goods: list[dict[str, Any]] = []
        for material_spec, estimate in output.material_estimates.items():
            sheet_goods.append({
                "material": material_spec.material_type.value,
                "thickness": material_spec.thickness,
                "total_area_sqft": estimate.total_area_sqft,
                "sheet_count_4x8": estimate.sheet_count_4x8,
                "waste_percentage": estimate.waste_percentage,
            })

        # Hardware list
        hardware: list[dict[str, Any]] = []
        if isinstance(output, LayoutOutput) and output.hardware:
            for item in output.hardware:
                hardware.append({
                    "name": item.name,
                    "quantity": item.quantity,
                    "sku": item.sku,
                    "notes": item.notes,
                })

        # Edge banding estimate (approximate based on perimeter)
        edge_banding = self._estimate_edge_banding(output)

        return {
            "sheet_goods": sheet_goods,
            "hardware": hardware,
            "edge_banding": edge_banding,
            "totals": {
                "total_area_sqft": output.total_estimate.total_area_sqft,
                "total_sheets_4x8": output.total_estimate.sheet_count_4x8,
            },
        }

    def _estimate_edge_banding(
        self, output: LayoutOutput | RoomLayoutOutput
    ) -> list[dict[str, Any]]:
        """Estimate edge banding requirements.

        Calculates approximate edge banding needed based on exposed edges
        of visible panels (sides, shelves, top, bottom).

        Args:
            output: The layout output to analyze.

        Returns:
            List of edge banding requirements by material.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        # Panel types that typically need edge banding on front edges
        banded_types = {
            PanelType.LEFT_SIDE,
            PanelType.RIGHT_SIDE,
            PanelType.TOP,
            PanelType.BOTTOM,
            PanelType.SHELF,
            PanelType.DIVIDER,
        }

        # Group by material thickness
        banding_by_thickness: dict[float, float] = {}

        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
        else:
            cut_list = output.cut_list

        for piece in cut_list:
            if piece.panel_type in banded_types:
                # Estimate front edge length (width for horizontal, height for vertical)
                if piece.panel_type in (PanelType.LEFT_SIDE, PanelType.RIGHT_SIDE, PanelType.DIVIDER):
                    edge_length = piece.height * piece.quantity
                else:
                    edge_length = piece.width * piece.quantity

                thickness = piece.material.thickness
                if thickness not in banding_by_thickness:
                    banding_by_thickness[thickness] = 0
                banding_by_thickness[thickness] += edge_length

        # Convert to list format
        result: list[dict[str, Any]] = []
        for thickness, length_inches in banding_by_thickness.items():
            result.append({
                "thickness": thickness,
                "length_inches": length_inches,
                "length_feet": length_inches / 12,
                "length_with_waste": (length_inches / 12) * 1.1,  # 10% waste
            })

        return result

    def _extract_warnings(self, output: LayoutOutput | RoomLayoutOutput) -> list[dict[str, Any]]:
        """Extract validation warnings.

        Compiles warnings from errors, span warnings, and advisory messages.

        Args:
            output: The layout output to check.

        Returns:
            List of warning dictionaries with type and message.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        warnings: list[dict[str, Any]] = []

        # Add any errors from output
        if isinstance(output, RoomLayoutOutput):
            for error in output.errors:
                warnings.append({
                    "type": "error",
                    "message": error,
                })
        else:
            for error in output.errors:
                warnings.append({
                    "type": "error",
                    "message": error,
                })

        # Check for span warnings using WoodworkingIntelligence
        try:
            from cabinets.domain.services.woodworking import WoodworkingIntelligence

            intel = WoodworkingIntelligence()

            if isinstance(output, RoomLayoutOutput):
                cabinets = output.cabinets
            else:
                cabinets = [output.cabinet]

            for cabinet in cabinets:
                span_warnings = intel.check_span_limits(cabinet)
                for span_warning in span_warnings:
                    warnings.append({
                        "type": "span_warning",
                        "message": f"{span_warning.panel_label}: span of {span_warning.span:.1f}\" exceeds max {span_warning.max_span:.1f}\" for {span_warning.material.material_type.value}",
                        "suggestion": span_warning.suggestion,
                    })
        except Exception as e:
            logger.debug(f"Could not check span warnings: {e}")

        # Add advisory messages for best practices
        warnings.extend(self._generate_advisories(output))

        return warnings

    def _generate_advisories(
        self, output: LayoutOutput | RoomLayoutOutput
    ) -> list[dict[str, Any]]:
        """Generate advisory messages for best practices.

        Args:
            output: The layout output to analyze.

        Returns:
            List of advisory warning dictionaries.
        """
        from cabinets.application.dtos import LayoutOutput, RoomLayoutOutput

        advisories: list[dict[str, Any]] = []

        if isinstance(output, RoomLayoutOutput):
            cabinets = output.cabinets
        else:
            cabinets = [output.cabinet]

        for cabinet in cabinets:
            # Check for heavy load potential (wide shelves)
            for section in cabinet.sections:
                for shelf in section.shelves:
                    if shelf.width > 30:
                        advisories.append({
                            "type": "advisory",
                            "message": f"Shelf spanning {shelf.width:.1f}\" may benefit from center support or cleats for heavy loads",
                        })
                        break  # One advisory per cabinet is enough

            # Check for tall narrow sections that might need anchoring
            if cabinet.height > 72 and cabinet.depth < 16:
                advisories.append({
                    "type": "advisory",
                    "message": "Tall cabinet with shallow depth - consider wall anchoring for stability",
                })

        return advisories


# Export for module access
__all__ = ["EnhancedJsonExporter", "SCHEMA_VERSION"]
