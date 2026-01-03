import type { CabinetConfig, LayoutOutput, ExportFormat } from './types';
import { generateMockLayout } from '@/mock/layout-output';

/**
 * Simulate network delay
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Mock API client for development
 */
export const mockApi = {
  /**
   * Generate layout from configuration
   */
  async generateLayout(config: CabinetConfig): Promise<LayoutOutput> {
    await delay(300);
    return generateMockLayout(config);
  },

  /**
   * Get available export formats
   */
  async getExportFormats(): Promise<ExportFormat[]> {
    await delay(100);
    return ['stl', 'json', 'svg', 'assembly', 'bom'];
  },

  /**
   * Export as STL - returns a simple cube as demonstration
   */
  async exportStl(config: CabinetConfig): Promise<Blob> {
    await delay(500);

    // Generate a simple ASCII STL for the cabinet bounding box
    const { width, height, depth } = config.cabinet;
    const stlContent = generateSimpleStl(width, height, depth);
    return new Blob([stlContent], { type: 'model/stl' });
  },

  /**
   * Export as JSON
   */
  async exportJson(config: CabinetConfig): Promise<object> {
    await delay(200);
    const layout = generateMockLayout(config);
    return {
      config,
      layout,
      exported_at: new Date().toISOString(),
    };
  },

  /**
   * Export assembly instructions
   */
  async exportAssembly(config: CabinetConfig): Promise<string> {
    await delay(300);
    const layout = generateMockLayout(config);
    return generateAssemblyInstructions(config, layout);
  },

  /**
   * Export bill of materials
   */
  async exportBom(config: CabinetConfig): Promise<string> {
    await delay(200);
    const layout = generateMockLayout(config);
    return generateBom(layout);
  },

  /**
   * Download export as file
   */
  async downloadExport(format: ExportFormat, config: CabinetConfig, filename?: string): Promise<void> {
    let blob: Blob;
    let defaultFilename: string;

    switch (format) {
      case 'stl':
        blob = await this.exportStl(config);
        defaultFilename = 'cabinet.stl';
        break;
      case 'json': {
        const json = await this.exportJson(config);
        blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
        defaultFilename = 'cabinet.json';
        break;
      }
      case 'assembly': {
        const assembly = await this.exportAssembly(config);
        blob = new Blob([assembly], { type: 'text/markdown' });
        defaultFilename = 'cabinet-assembly.md';
        break;
      }
      case 'bom': {
        const bom = await this.exportBom(config);
        blob = new Blob([bom], { type: 'text/csv' });
        defaultFilename = 'cabinet-bom.csv';
        break;
      }
      default:
        throw new Error(`Export format ${format} not yet implemented`);
    }

    // Trigger download
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename ?? defaultFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

/**
 * Generate a simple ASCII STL for a rectangular box
 */
function generateSimpleStl(width: number, height: number, depth: number): string {
  // Scale from inches to mm for STL (common practice)
  const w = width * 25.4;
  const h = height * 25.4;
  const d = depth * 25.4;

  const facets = [
    // Bottom face
    { normal: [0, 0, -1], vertices: [[0, 0, 0], [w, 0, 0], [w, d, 0]] },
    { normal: [0, 0, -1], vertices: [[0, 0, 0], [w, d, 0], [0, d, 0]] },
    // Top face
    { normal: [0, 0, 1], vertices: [[0, 0, h], [w, d, h], [w, 0, h]] },
    { normal: [0, 0, 1], vertices: [[0, 0, h], [0, d, h], [w, d, h]] },
    // Front face
    { normal: [0, -1, 0], vertices: [[0, 0, 0], [w, 0, h], [w, 0, 0]] },
    { normal: [0, -1, 0], vertices: [[0, 0, 0], [0, 0, h], [w, 0, h]] },
    // Back face
    { normal: [0, 1, 0], vertices: [[0, d, 0], [w, d, 0], [w, d, h]] },
    { normal: [0, 1, 0], vertices: [[0, d, 0], [w, d, h], [0, d, h]] },
    // Left face
    { normal: [-1, 0, 0], vertices: [[0, 0, 0], [0, d, 0], [0, d, h]] },
    { normal: [-1, 0, 0], vertices: [[0, 0, 0], [0, d, h], [0, 0, h]] },
    // Right face
    { normal: [1, 0, 0], vertices: [[w, 0, 0], [w, d, h], [w, d, 0]] },
    { normal: [1, 0, 0], vertices: [[w, 0, 0], [w, 0, h], [w, d, h]] },
  ];

  let stl = 'solid cabinet\n';
  for (const facet of facets) {
    stl += `  facet normal ${facet.normal.join(' ')}\n`;
    stl += '    outer loop\n';
    for (const vertex of facet.vertices) {
      stl += `      vertex ${vertex.join(' ')}\n`;
    }
    stl += '    endloop\n';
    stl += '  endfacet\n';
  }
  stl += 'endsolid cabinet\n';

  return stl;
}

/**
 * Generate assembly instructions markdown
 */
function generateAssemblyInstructions(config: CabinetConfig, layout: LayoutOutput): string {
  const { width, height, depth } = config.cabinet;
  const numSections = layout.cabinet?.num_sections || 1;
  const totalShelves = layout.cabinet?.total_shelves || 0;

  return `# Cabinet Assembly Instructions

## Overview
- **Dimensions**: ${width}" W x ${height}" H x ${depth}" D
- **Sections**: ${numSections}
- **Total Shelves**: ${totalShelves}

## Cut List

| Part | Quantity | Dimensions |
|------|----------|------------|
${layout.cut_list.map(p => `| ${p.label} | ${p.quantity} | ${p.width.toFixed(2)}" x ${p.height.toFixed(2)}" |`).join('\n')}

## Assembly Steps

1. **Prepare all pieces** - Cut all panels according to the cut list above
2. **Assemble the carcase**
   - Attach the bottom panel to the left side using pocket screws or dado joints
   - Attach the right side panel
   - Install the top panel
3. **Install dividers** - If applicable, install section dividers
4. **Install shelves** - Add shelf pins or cleats, then install shelves
5. **Attach back panel** - Secure the back panel with brad nails or screws
6. **Install in location** - Secure to wall studs

## Materials Needed

- Wood glue
- Pocket screws or wood screws
- Brad nails (for back panel)
- Shelf pins (for adjustable shelves)
- Wall mounting hardware

---
Generated by Cabinet Designer
`;
}

/**
 * Generate bill of materials CSV
 */
function generateBom(layout: LayoutOutput): string {
  let csv = 'Part,Quantity,Width (in),Height (in),Thickness (in),Material,Area (sq ft)\n';

  for (const piece of layout.cut_list) {
    const areaSqFt = ((piece.width * piece.height) / 144).toFixed(2);
    csv += `"${piece.label}",${piece.quantity},${piece.width.toFixed(2)},${piece.height.toFixed(2)},${piece.thickness},"${piece.material_type}",${areaSqFt}\n`;
  }

  if (layout.total_estimate) {
    csv += `\nTotal Sheets Required:,${layout.total_estimate.sheet_count}\n`;
    csv += `Total Area (sq ft):,${layout.total_estimate.total_area_sqft.toFixed(2)}\n`;
    csv += `Estimated Waste:,${layout.total_estimate.waste_percentage}%\n`;
  }

  return csv;
}
