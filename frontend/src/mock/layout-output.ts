import type { LayoutOutput, CabinetConfig, CutPiece } from '@/api/types';

/**
 * Generate a mock layout output based on cabinet configuration
 */
export function generateMockLayout(config: CabinetConfig): LayoutOutput {
  const { width, height, depth } = config.cabinet;
  const sections = config.cabinet.sections || [];
  const materialThickness = config.cabinet.material?.thickness || 0.75;
  const backThickness = config.cabinet.back_material?.thickness || 0.25;
  const materialType = config.cabinet.material?.type || 'plywood';

  const numSections = sections.length || 1;
  const totalShelves = sections.reduce((sum, s) => sum + (s.shelves || 0), 0);

  // Calculate interior dimensions
  const interiorWidth = width - (2 * materialThickness);
  const interiorHeight = height - (2 * materialThickness);
  const interiorDepth = depth - materialThickness - backThickness;

  // Calculate section width (assuming equal distribution for 'fill')
  const sectionWidth = interiorWidth / numSections;

  const cutList: CutPiece[] = [
    // Outer panels
    {
      label: 'Left Side',
      width: interiorDepth,
      height: interiorHeight,
      thickness: materialThickness,
      material_type: materialType,
      quantity: 1,
    },
    {
      label: 'Right Side',
      width: interiorDepth,
      height: interiorHeight,
      thickness: materialThickness,
      material_type: materialType,
      quantity: 1,
    },
    {
      label: 'Top',
      width: interiorWidth,
      height: interiorDepth,
      thickness: materialThickness,
      material_type: materialType,
      quantity: 1,
    },
    {
      label: 'Bottom',
      width: interiorWidth,
      height: interiorDepth,
      thickness: materialThickness,
      material_type: materialType,
      quantity: 1,
    },
    {
      label: 'Back Panel',
      width: width,
      height: height,
      thickness: backThickness,
      material_type: materialType,
      quantity: 1,
    },
  ];

  // Add dividers between sections
  if (numSections > 1) {
    cutList.push({
      label: 'Section Divider',
      width: interiorDepth,
      height: interiorHeight,
      thickness: materialThickness,
      material_type: materialType,
      quantity: numSections - 1,
    });
  }

  // Add shelves
  if (totalShelves > 0) {
    cutList.push({
      label: 'Shelf',
      width: sectionWidth - materialThickness,
      height: interiorDepth - 0.5, // Slightly shorter for clearance
      thickness: materialThickness,
      material_type: materialType,
      quantity: totalShelves,
    });
  }

  // Calculate total area
  const totalAreaSqIn = cutList.reduce((sum, piece) => {
    return sum + (piece.width * piece.height * piece.quantity);
  }, 0);
  const totalAreaSqFt = totalAreaSqIn / 144;

  // Estimate sheet count (assuming 4x8 sheets = 32 sq ft)
  const sheetArea = 32;
  const sheetCount = Math.ceil(totalAreaSqFt / (sheetArea * 0.75)); // 75% efficiency

  return {
    is_valid: true,
    errors: [],
    cabinet: {
      width,
      height,
      depth,
      num_sections: numSections,
      total_shelves: totalShelves,
    },
    cut_list: cutList,
    material_estimates: {
      [`${materialType}_${materialThickness}`]: {
        sheet_count: sheetCount,
        total_area_sqft: totalAreaSqFt,
        waste_percentage: 15,
      },
    },
    total_estimate: {
      sheet_count: sheetCount,
      total_area_sqft: totalAreaSqFt,
      waste_percentage: 15,
    },
  };
}
