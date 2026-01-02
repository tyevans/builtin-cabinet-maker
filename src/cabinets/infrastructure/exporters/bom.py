"""Bill of Materials (BOM) Generator for cabinet layouts.

Generates comprehensive material lists including:
- Sheet goods: material, thickness, sheet size, quantity, square footage
- Hardware: fasteners, shelf pins, hinges, slides with quantities
- Edge banding: linear feet per material/color
- Optional cost estimation with unit costs

Output formats: text, csv, json

Based on FRD-16 FR-05.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from cabinets.infrastructure.exporters.base import ExporterRegistry

if TYPE_CHECKING:
    from cabinets.contracts.dtos import LayoutOutput, RoomLayoutOutput
    from cabinets.domain.value_objects import MaterialSpec


logger = logging.getLogger(__name__)


# Standard sheet sizes (width x height in inches)
STANDARD_SHEET_4X8 = (48.0, 96.0)
STANDARD_SHEET_5X5 = (60.0, 60.0)

# Panel types with visible edges that need edge banding
# Maps panel type to list of edges that are typically visible
# Edges are: "front", "back", "left", "right" (from front-facing view)
VISIBLE_EDGES: dict[str, list[str]] = {
    "left_side": ["front"],  # Front edge of side panel
    "right_side": ["front"],  # Front edge of side panel
    "top": ["front"],  # Front edge of top
    "bottom": ["front"],  # Front edge of bottom
    "shelf": ["front"],  # Front edge of shelf
    "divider": ["front"],  # Front edge of divider
    "horizontal_divider": ["front"],  # Front edge
    "door": ["top", "bottom", "left", "right"],  # All edges of door
    "drawer_front": ["top", "bottom", "left", "right"],  # All edges
    "face_frame_rail": ["front"],  # Visible face
    "face_frame_stile": ["front"],  # Visible face
}

# Hardware categories for grouping
HARDWARE_CATEGORIES = {
    "screw": "fasteners",
    "pocket": "fasteners",
    "dowel": "fasteners",
    "biscuit": "fasteners",
    "nail": "fasteners",
    "hinge": "hinges",
    "slide": "slides",
    "pin": "shelf_supports",
    "bracket": "shelf_supports",
    "knob": "hardware",
    "pull": "hardware",
    "handle": "hardware",
}


@dataclass(frozen=True)
class SheetGoodItem:
    """Sheet goods requirement for BOM.

    Represents a specific sheet material needed for the project,
    including quantity and area calculations.

    Attributes:
        material: Material type name (e.g., "Plywood", "MDF").
        thickness: Material thickness in inches.
        sheet_size: Tuple of (width, height) in inches.
        quantity: Number of sheets required.
        square_feet: Total area required in square feet.
        unit_cost: Optional cost per sheet for estimation.
    """

    material: str
    thickness: float
    sheet_size: tuple[float, float]
    quantity: int
    square_feet: float
    unit_cost: float | None = None

    @property
    def total_cost(self) -> float | None:
        """Calculate total cost if unit cost is available."""
        if self.unit_cost is None:
            return None
        return self.unit_cost * self.quantity

    @property
    def sheet_area_sqft(self) -> float:
        """Area of a single sheet in square feet."""
        return (self.sheet_size[0] * self.sheet_size[1]) / 144.0


@dataclass(frozen=True)
class EdgeBandingItem:
    """Edge banding requirement for BOM.

    Represents edge banding material needed to cover exposed panel edges.

    Attributes:
        material: Material type (e.g., "Maple", "Oak", "PVC").
        thickness: Banding thickness description (e.g., "3/4 inch").
        color: Color or finish (e.g., "Natural", "White").
        linear_feet: Total length required in linear feet.
        unit_cost: Optional cost per linear foot for estimation.
    """

    material: str
    thickness: str
    color: str
    linear_feet: float
    unit_cost: float | None = None

    @property
    def total_cost(self) -> float | None:
        """Calculate total cost if unit cost is available."""
        if self.unit_cost is None:
            return None
        return self.unit_cost * self.linear_feet


@dataclass(frozen=True)
class HardwareBomItem:
    """Hardware item for BOM.

    Represents a specific hardware item with quantity and categorization.

    Attributes:
        name: Descriptive name of hardware item.
        size: Size specification (e.g., "1-1/4 inch", "35mm").
        quantity: Number of items required.
        category: Category for grouping (e.g., "fasteners", "hinges").
        sku: Optional manufacturer or vendor SKU.
        unit_cost: Optional cost per item for estimation.
    """

    name: str
    size: str
    quantity: int
    category: str = ""
    sku: str = ""
    unit_cost: float | None = None

    @property
    def total_cost(self) -> float | None:
        """Calculate total cost if unit cost is available."""
        if self.unit_cost is None:
            return None
        return self.unit_cost * self.quantity


@dataclass
class BillOfMaterials:
    """Complete bill of materials for a cabinet project.

    Contains all materials organized by category: sheet goods,
    hardware, and edge banding.

    Attributes:
        sheet_goods: Tuple of sheet material requirements.
        hardware: Tuple of hardware items required.
        edge_banding: Tuple of edge banding requirements.
    """

    sheet_goods: tuple[SheetGoodItem, ...] = field(default_factory=tuple)
    hardware: tuple[HardwareBomItem, ...] = field(default_factory=tuple)
    edge_banding: tuple[EdgeBandingItem, ...] = field(default_factory=tuple)

    @property
    def total_cost(self) -> float | None:
        """Calculate total cost if all items have unit costs.

        Returns:
            Total cost in dollars, or None if any item lacks pricing.
        """
        total = 0.0
        has_any_cost = False

        for sheet_item in self.sheet_goods:
            if sheet_item.unit_cost is not None:
                total += sheet_item.total_cost or 0.0
                has_any_cost = True

        for hw_item in self.hardware:
            if hw_item.unit_cost is not None:
                total += hw_item.total_cost or 0.0
                has_any_cost = True

        for edge_item in self.edge_banding:
            if edge_item.unit_cost is not None:
                total += edge_item.total_cost or 0.0
                has_any_cost = True

        return total if has_any_cost else None

    @property
    def sheet_goods_cost(self) -> float | None:
        """Total cost of sheet goods."""
        total = 0.0
        has_cost = False
        for item in self.sheet_goods:
            if item.total_cost is not None:
                total += item.total_cost
                has_cost = True
        return total if has_cost else None

    @property
    def hardware_cost(self) -> float | None:
        """Total cost of hardware."""
        total = 0.0
        has_cost = False
        for item in self.hardware:
            if item.total_cost is not None:
                total += item.total_cost
                has_cost = True
        return total if has_cost else None

    @property
    def edge_banding_cost(self) -> float | None:
        """Total cost of edge banding."""
        total = 0.0
        has_cost = False
        for item in self.edge_banding:
            if item.total_cost is not None:
                total += item.total_cost
                has_cost = True
        return total if has_cost else None


@ExporterRegistry.register("bom")  # type: ignore[arg-type]
class BomGenerator:
    """Bill of Materials generator for cabinet layouts.

    Analyzes layout output to generate comprehensive material lists
    including sheet goods, hardware, and edge banding requirements.

    Supports multiple output formats: text, CSV, and JSON.

    Attributes:
        format_name: "bom"
        file_extension: ".txt", ".csv", or ".json" based on output_format
    """

    format_name: ClassVar[str] = "bom"
    # Note: file_extension is set dynamically in __init__ based on output_format

    def __init__(
        self,
        output_format: str = "text",
        include_costs: bool = False,
        sheet_size: tuple[float, float] = STANDARD_SHEET_4X8,
        edge_banding_default_color: str = "Natural",
    ) -> None:
        """Initialize the BOM generator.

        Args:
            output_format: Output format - "text", "csv", or "json".
            include_costs: Whether to include cost columns in output.
            sheet_size: Default sheet dimensions (width, height) in inches.
            edge_banding_default_color: Default color for edge banding.
        """
        self.output_format = output_format
        self.include_costs = include_costs
        self.sheet_size = sheet_size
        self.edge_banding_default_color = edge_banding_default_color

        # Set file extension based on format (without leading dot)
        self._file_extension = {
            "text": "txt",
            "csv": "csv",
            "json": "json",
        }.get(output_format, "txt")

    @property
    def file_extension(self) -> str:
        """Get the file extension for this output format."""
        return self._file_extension

    def generate(
        self,
        output: LayoutOutput | RoomLayoutOutput,
    ) -> BillOfMaterials:
        """Generate BOM from layout output.

        Analyzes the layout to extract all material requirements.

        Args:
            output: Layout output from cabinet generation.

        Returns:
            Complete BillOfMaterials with all requirements.
        """
        sheet_goods = self._calculate_sheet_goods(output)
        hardware = self._extract_hardware(output)
        edge_banding = self._calculate_edge_banding(output)

        return BillOfMaterials(
            sheet_goods=tuple(sheet_goods),
            hardware=tuple(hardware),
            edge_banding=tuple(edge_banding),
        )

    def export(
        self,
        output: LayoutOutput | RoomLayoutOutput,
        path: Path,
    ) -> None:
        """Export BOM to file.

        Args:
            output: Layout output to generate BOM from.
            path: Path where the file will be saved.
        """
        content = self.export_string(output)
        path.write_text(content)
        logger.info(f"Exported BOM to {path}")

    def export_string(
        self,
        output: LayoutOutput | RoomLayoutOutput,
    ) -> str:
        """Generate BOM in specified format as string.

        Args:
            output: Layout output to generate BOM from.

        Returns:
            Formatted BOM string in the configured output format.
        """
        bom = self.generate(output)

        if self.output_format == "csv":
            return self.format_csv(bom)
        elif self.output_format == "json":
            return self.format_json(bom)
        else:
            return self.format_text(bom)

    def format_for_console(
        self,
        output: LayoutOutput | RoomLayoutOutput,
    ) -> str:
        """Format BOM for console display.

        Always uses text format for console output regardless of
        the configured output_format, as text is most readable
        in a terminal.

        Args:
            output: Layout output to generate BOM from.

        Returns:
            Human-readable text BOM suitable for console display.
        """
        bom = self.generate(output)
        return self.format_text(bom)

    def format_text(self, bom: BillOfMaterials) -> str:
        """Format BOM as human-readable text.

        Args:
            bom: Bill of materials to format.

        Returns:
            Formatted text representation.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("BILL OF MATERIALS")
        lines.append("=" * 60)
        lines.append("")

        # Sheet Goods Section
        lines.append("SHEET GOODS")
        lines.append("-" * 40)

        if bom.sheet_goods:
            for item in bom.sheet_goods:
                lines.append(
                    f'  {item.material} {item.thickness}" - {item.quantity} sheet(s)'
                )
                lines.append(
                    f'    Size: {item.sheet_size[0]:.0f}" x {item.sheet_size[1]:.0f}"'
                )
                lines.append(f"    Area: {item.square_feet:.1f} sq ft")
                if self.include_costs and item.unit_cost is not None:
                    lines.append(
                        f"    Cost: ${item.unit_cost:.2f}/sheet = ${item.total_cost:.2f}"
                    )
        else:
            lines.append("  (No sheet goods)")
        lines.append("")

        # Hardware Section
        lines.append("HARDWARE")
        lines.append("-" * 40)

        if bom.hardware:
            # Group by category
            by_category: dict[str, list[HardwareBomItem]] = {}
            for hw_item in bom.hardware:
                cat = hw_item.category or "other"
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(hw_item)

            for category, items in sorted(by_category.items()):
                lines.append(f"  [{category.replace('_', ' ').title()}]")
                for hw in items:
                    cost_str = ""
                    if self.include_costs and hw.unit_cost is not None:
                        cost_str = f" @ ${hw.unit_cost:.2f} = ${hw.total_cost:.2f}"
                    lines.append(f"    {hw.name} ({hw.size}): {hw.quantity}{cost_str}")
        else:
            lines.append("  (No hardware)")
        lines.append("")

        # Edge Banding Section
        lines.append("EDGE BANDING")
        lines.append("-" * 40)

        if bom.edge_banding:
            for edge_item in bom.edge_banding:
                cost_str = ""
                if self.include_costs and edge_item.unit_cost is not None:
                    cost_str = f" @ ${edge_item.unit_cost:.2f}/ft = ${edge_item.total_cost:.2f}"
                lines.append(
                    f"  {edge_item.material} {edge_item.thickness} ({edge_item.color}): "
                    f"{edge_item.linear_feet:.1f} linear ft{cost_str}"
                )
        else:
            lines.append("  (No edge banding)")
        lines.append("")

        # Cost Summary (if costs included)
        if self.include_costs and bom.total_cost is not None:
            lines.append("=" * 60)
            lines.append("COST SUMMARY")
            lines.append("-" * 40)

            if bom.sheet_goods_cost is not None:
                lines.append(f"  Sheet Goods:  ${bom.sheet_goods_cost:>10.2f}")
            if bom.hardware_cost is not None:
                lines.append(f"  Hardware:     ${bom.hardware_cost:>10.2f}")
            if bom.edge_banding_cost is not None:
                lines.append(f"  Edge Banding: ${bom.edge_banding_cost:>10.2f}")
            lines.append("-" * 40)
            lines.append(f"  TOTAL:        ${bom.total_cost:>10.2f}")
            lines.append("")

        return "\n".join(lines)

    def format_csv(self, bom: BillOfMaterials) -> str:
        """Format BOM as CSV.

        Args:
            bom: Bill of materials to format.

        Returns:
            CSV formatted string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        if self.include_costs:
            writer.writerow(
                [
                    "Category",
                    "Item",
                    "Size",
                    "Quantity",
                    "Unit",
                    "Unit Cost",
                    "Total Cost",
                ]
            )
        else:
            writer.writerow(["Category", "Item", "Size", "Quantity", "Unit"])

        # Sheet Goods
        for sheet_item in bom.sheet_goods:
            size_str = (
                f'{sheet_item.sheet_size[0]:.0f}"x{sheet_item.sheet_size[1]:.0f}"'
            )
            if self.include_costs:
                writer.writerow(
                    [
                        "Sheet Goods",
                        f'{sheet_item.material} {sheet_item.thickness}"',
                        size_str,
                        sheet_item.quantity,
                        "sheets",
                        f"{sheet_item.unit_cost:.2f}" if sheet_item.unit_cost else "",
                        f"{sheet_item.total_cost:.2f}" if sheet_item.total_cost else "",
                    ]
                )
            else:
                writer.writerow(
                    [
                        "Sheet Goods",
                        f'{sheet_item.material} {sheet_item.thickness}"',
                        size_str,
                        sheet_item.quantity,
                        "sheets",
                    ]
                )

        # Hardware
        for hw_item in bom.hardware:
            if self.include_costs:
                writer.writerow(
                    [
                        f"Hardware - {hw_item.category.replace('_', ' ').title()}",
                        hw_item.name,
                        hw_item.size,
                        hw_item.quantity,
                        "count",
                        f"{hw_item.unit_cost:.2f}" if hw_item.unit_cost else "",
                        f"{hw_item.total_cost:.2f}" if hw_item.total_cost else "",
                    ]
                )
            else:
                writer.writerow(
                    [
                        f"Hardware - {hw_item.category.replace('_', ' ').title()}",
                        hw_item.name,
                        hw_item.size,
                        hw_item.quantity,
                        "count",
                    ]
                )

        # Edge Banding
        for edge_item in bom.edge_banding:
            if self.include_costs:
                writer.writerow(
                    [
                        "Edge Banding",
                        f"{edge_item.material} ({edge_item.color})",
                        edge_item.thickness,
                        f"{edge_item.linear_feet:.1f}",
                        "linear ft",
                        f"{edge_item.unit_cost:.2f}" if edge_item.unit_cost else "",
                        f"{edge_item.total_cost:.2f}" if edge_item.total_cost else "",
                    ]
                )
            else:
                writer.writerow(
                    [
                        "Edge Banding",
                        f"{edge_item.material} ({edge_item.color})",
                        edge_item.thickness,
                        f"{edge_item.linear_feet:.1f}",
                        "linear ft",
                    ]
                )

        return output.getvalue()

    def format_json(self, bom: BillOfMaterials) -> str:
        """Format BOM as JSON.

        Args:
            bom: Bill of materials to format.

        Returns:
            JSON formatted string.
        """
        data: dict[str, Any] = {
            "sheet_goods": [],
            "hardware": [],
            "edge_banding": [],
        }

        # Sheet Goods
        for sheet_item in bom.sheet_goods:
            sheet_dict: dict[str, Any] = {
                "material": sheet_item.material,
                "thickness": sheet_item.thickness,
                "sheet_size": {
                    "width": sheet_item.sheet_size[0],
                    "height": sheet_item.sheet_size[1],
                },
                "quantity": sheet_item.quantity,
                "square_feet": sheet_item.square_feet,
            }
            if self.include_costs and sheet_item.unit_cost is not None:
                sheet_dict["unit_cost"] = sheet_item.unit_cost
                sheet_dict["total_cost"] = sheet_item.total_cost
            data["sheet_goods"].append(sheet_dict)

        # Hardware
        for hw_item in bom.hardware:
            hw_dict: dict[str, Any] = {
                "name": hw_item.name,
                "size": hw_item.size,
                "quantity": hw_item.quantity,
                "category": hw_item.category,
            }
            if hw_item.sku:
                hw_dict["sku"] = hw_item.sku
            if self.include_costs and hw_item.unit_cost is not None:
                hw_dict["unit_cost"] = hw_item.unit_cost
                hw_dict["total_cost"] = hw_item.total_cost
            data["hardware"].append(hw_dict)

        # Edge Banding
        for edge_item in bom.edge_banding:
            edge_dict: dict[str, Any] = {
                "material": edge_item.material,
                "thickness": edge_item.thickness,
                "color": edge_item.color,
                "linear_feet": edge_item.linear_feet,
            }
            if self.include_costs and edge_item.unit_cost is not None:
                edge_dict["unit_cost"] = edge_item.unit_cost
                edge_dict["total_cost"] = edge_item.total_cost
            data["edge_banding"].append(edge_dict)

        # Cost summary
        if self.include_costs:
            data["cost_summary"] = {
                "sheet_goods": bom.sheet_goods_cost,
                "hardware": bom.hardware_cost,
                "edge_banding": bom.edge_banding_cost,
                "total": bom.total_cost,
            }

        return json.dumps(data, indent=2)

    def _calculate_sheet_goods(
        self,
        output: LayoutOutput | RoomLayoutOutput,
    ) -> list[SheetGoodItem]:
        """Calculate sheet goods from layout output.

        Uses packing result if available for accurate sheet counts,
        otherwise estimates from cut list area.

        Args:
            output: Layout output with cut list and optional packing result.

        Returns:
            List of SheetGoodItem requirements.
        """
        from cabinets.contracts.dtos import RoomLayoutOutput

        # Get cut list and packing result
        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
            packing_result = None  # RoomLayoutOutput doesn't have packing_result
        else:
            cut_list = output.cut_list
            packing_result = getattr(output, "packing_result", None)

        if not cut_list:
            return []

        # Group pieces by material

        materials: dict[MaterialSpec, list[Any]] = {}
        for piece in cut_list:
            if piece.material not in materials:
                materials[piece.material] = []
            materials[piece.material].append(piece)

        sheet_goods: list[SheetGoodItem] = []

        for material, pieces in materials.items():
            # Calculate total area in square inches
            total_area = sum(p.width * p.height * p.quantity for p in pieces)
            total_sqft = total_area / 144.0

            # Determine sheet count
            if packing_result and material in packing_result.sheets_by_material:
                # Use actual packing result
                sheet_count = packing_result.sheets_by_material[material]
            else:
                # Estimate from area with waste factor
                sheet_area = self.sheet_size[0] * self.sheet_size[1]
                # Assume 15% waste for estimation
                effective_area = sheet_area * 0.85
                sheet_count = max(1, math.ceil(total_area / effective_area))

            sheet_goods.append(
                SheetGoodItem(
                    material=material.material_type.value.title(),
                    thickness=material.thickness,
                    sheet_size=self.sheet_size,
                    quantity=sheet_count,
                    square_feet=total_sqft,
                    unit_cost=None,  # Cost not available from layout output
                )
            )

        return sheet_goods

    def _extract_hardware(
        self,
        output: LayoutOutput | RoomLayoutOutput,
    ) -> list[HardwareBomItem]:
        """Extract hardware items from layout output.

        Converts hardware from output format to BOM format with categorization.
        Consolidates duplicate items by summing their quantities.

        Args:
            output: Layout output with hardware list.

        Returns:
            List of HardwareBomItem requirements with duplicates consolidated.
        """
        from cabinets.contracts.dtos import RoomLayoutOutput

        # Get hardware list
        hardware_items: list[Any]
        if isinstance(output, RoomLayoutOutput):
            # RoomLayoutOutput doesn't have direct hardware access
            # We would need to aggregate from individual cabinets
            hardware_items = []
        else:
            hardware_items = getattr(output, "hardware", [])

        if not hardware_items:
            return []

        # Aggregate hardware by (name, size, category, sku) to consolidate duplicates
        aggregated: dict[tuple[str, str, str, str], int] = {}

        for item in hardware_items:
            # Determine category from item name
            category = "other"
            name_lower = item.name.lower()
            for keyword, cat in HARDWARE_CATEGORIES.items():
                if keyword in name_lower:
                    category = cat
                    break

            # Extract size from name (often in format "Name Size" or "Size Name")
            size = self._extract_size_from_name(item.name)
            sku = item.sku or ""

            # Use tuple as key for aggregation
            key = (item.name, size, category, sku)
            if key in aggregated:
                aggregated[key] += item.quantity
            else:
                aggregated[key] = item.quantity

        # Convert aggregated dict to list of HardwareBomItem
        bom_items: list[HardwareBomItem] = []
        for (name, size, category, sku), quantity in aggregated.items():
            bom_items.append(
                HardwareBomItem(
                    name=name,
                    size=size,
                    quantity=quantity,
                    category=category,
                    sku=sku,
                    unit_cost=None,
                )
            )

        return bom_items

    def _extract_size_from_name(self, name: str) -> str:
        """Extract size specification from hardware name.

        Looks for common size patterns like "1-1/4 inch" or "#8 x 1-1/4".

        Args:
            name: Hardware item name.

        Returns:
            Size string, or empty string if not found.
        """
        import re

        # Common patterns for hardware sizes
        patterns = [
            r'#\d+\s*x\s*[\d\-/]+["\']?',  # #8 x 1-1/4"
            r'[\d\-/]+\s*(?:inch|in|")',  # 1-1/4 inch or 1-1/4"
            r"\d+mm",  # 35mm
            r'[\d\-/]+["\']',  # 1/4"
        ]

        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(0)

        return ""

    def _calculate_edge_banding(
        self,
        output: LayoutOutput | RoomLayoutOutput,
    ) -> list[EdgeBandingItem]:
        """Calculate edge banding requirements from cut list.

        Determines visible edges for each panel type and calculates
        total linear footage needed.

        Args:
            output: Layout output with cut list.

        Returns:
            List of EdgeBandingItem requirements.
        """
        from cabinets.contracts.dtos import RoomLayoutOutput

        # Get cut list
        if isinstance(output, RoomLayoutOutput):
            cut_list = output.cut_list
        else:
            cut_list = output.cut_list

        if not cut_list:
            return []

        # Calculate linear feet by material/thickness

        banding_by_material: dict[tuple[str, float], float] = {}

        for piece in cut_list:
            panel_type = piece.panel_type.value
            visible_edges = VISIBLE_EDGES.get(panel_type, [])

            if not visible_edges:
                continue

            # Calculate total edge length for this piece
            edge_length = 0.0
            for edge in visible_edges:
                if edge in ("front", "back"):
                    edge_length += piece.width
                elif edge in ("left", "right"):
                    edge_length += piece.height
                elif edge in ("top", "bottom"):
                    edge_length += piece.width

            # Multiply by quantity
            total_length = edge_length * piece.quantity

            # Group by material type and thickness
            material_type = piece.material.material_type.value
            thickness = piece.material.thickness
            key = (material_type, thickness)

            if key not in banding_by_material:
                banding_by_material[key] = 0.0
            banding_by_material[key] += total_length

        # Convert to EdgeBandingItem list
        edge_banding: list[EdgeBandingItem] = []

        for (material_type, thickness), linear_inches in banding_by_material.items():
            linear_feet = linear_inches / 12.0

            # Format thickness as fraction
            thickness_str = self._format_thickness(thickness)

            edge_banding.append(
                EdgeBandingItem(
                    material=material_type.title(),
                    thickness=thickness_str,
                    color=self.edge_banding_default_color,
                    linear_feet=linear_feet,
                    unit_cost=None,
                )
            )

        return edge_banding

    def _format_thickness(self, thickness: float) -> str:
        """Format thickness as a readable string.

        Converts decimal thickness to common fraction if applicable.

        Args:
            thickness: Thickness in inches.

        Returns:
            Formatted thickness string.
        """
        # Common thicknesses and their fractions
        common_fractions = {
            0.25: "1/4 inch",
            0.5: "1/2 inch",
            0.625: "5/8 inch",
            0.75: "3/4 inch",
            1.0: "1 inch",
        }

        if thickness in common_fractions:
            return common_fractions[thickness]

        # For other values, use decimal format
        return f'{thickness:.3f}"'


# Additional exports for convenience
__all__ = [
    "BillOfMaterials",
    "BomGenerator",
    "EdgeBandingItem",
    "HardwareBomItem",
    "SheetGoodItem",
]
