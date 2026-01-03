import type { CabinetConfig, LayoutOutput, ExportFormat } from './types';

/** Single sheet layout with SVG */
export interface SheetLayout {
  sheet_index: number;
  piece_count: number;
  waste_percentage: number;
  svg: string;
}

/** Response from cut-layouts endpoint */
export interface CutLayoutsResponse {
  total_sheets: number;
  total_waste_percentage: number;
  sheets: SheetLayout[];
  combined_svg: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Convert CabinetConfig to the export request format expected by the backend
 */
function configToExportRequest(config: CabinetConfig) {
  const sections = config.cabinet.sections || [];
  const numSections = sections.length || 1;
  const shelvesPerSection = sections[0]?.shelves ?? 3;

  return {
    dimensions: {
      width: config.cabinet.width,
      height: config.cabinet.height,
      depth: config.cabinet.depth,
    },
    num_sections: numSections,
    shelves_per_section: shelvesPerSection,
    material: {
      type: config.cabinet.material?.type || 'plywood',
      thickness: config.cabinet.material?.thickness || 0.75,
    },
    back_thickness: config.cabinet.back_material?.thickness || 0.25,
  };
}

/**
 * Real API client for the FastAPI backend
 */
export const api = {
  /**
   * Generate layout from configuration
   */
  async generateLayout(config: CabinetConfig): Promise<LayoutOutput> {
    const response = await fetch(`${API_BASE_URL}/generate/from-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      // Preserve the full error structure for rich error display
      // The error-banner component can parse and display this appropriately
      if (error.error && error.details) {
        throw new Error(JSON.stringify(error));
      }
      throw new Error(error.detail?.error || error.detail || error.error || 'Failed to generate layout');
    }

    return response.json();
  },

  /**
   * Get available export formats
   */
  async getExportFormats(): Promise<ExportFormat[]> {
    const response = await fetch(`${API_BASE_URL}/export/formats`);
    if (!response.ok) {
      throw new Error('Failed to fetch export formats');
    }
    const data = await response.json();
    return data.formats;
  },

  /**
   * Export to a specific format and download
   */
  async downloadExport(format: ExportFormat, config: CabinetConfig, filename?: string): Promise<void> {
    const exportRequest = configToExportRequest(config);

    const response = await fetch(`${API_BASE_URL}/export/${format}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(exportRequest),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail?.error || error.detail || `Failed to export ${format}`);
    }

    // Get the blob and determine filename
    const blob = await response.blob();
    const contentDisposition = response.headers.get('Content-Disposition');
    let defaultFilename = `cabinet.${format}`;

    if (contentDisposition) {
      const match = contentDisposition.match(/filename=([^;]+)/);
      if (match) {
        defaultFilename = match[1].replace(/"/g, '');
      }
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

  /**
   * Export as STL (legacy - uses simplified request)
   */
  async exportStl(config: CabinetConfig): Promise<Blob> {
    const exportRequest = configToExportRequest(config);

    const response = await fetch(`${API_BASE_URL}/export/stl`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(exportRequest),
    });

    if (!response.ok) {
      throw new Error('Failed to export STL');
    }

    return response.blob();
  },

  /**
   * Get STL from full configuration (for 3D preview)
   * This ensures the 3D model matches exactly what the backend generates
   */
  async getStlFromConfig(config: CabinetConfig): Promise<ArrayBuffer> {
    const response = await fetch(`${API_BASE_URL}/export/stl-from-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    });

    if (!response.ok) {
      throw new Error('Failed to get STL');
    }

    return response.arrayBuffer();
  },

  /**
   * Export as JSON
   */
  async exportJson(config: CabinetConfig): Promise<object> {
    const exportRequest = configToExportRequest(config);

    const response = await fetch(`${API_BASE_URL}/export/json`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(exportRequest),
    });

    if (!response.ok) {
      throw new Error('Failed to export JSON');
    }

    return response.json();
  },

  /**
   * Get assembly instructions as markdown text
   */
  async getAssemblyInstructions(config: CabinetConfig): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/export/assembly-from-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail?.error || error.detail || 'Failed to get assembly instructions');
    }

    return response.text();
  },

  /**
   * Get bill of materials as text
   */
  async getBillOfMaterials(config: CabinetConfig): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/export/bom-from-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail?.error || error.detail || 'Failed to get bill of materials');
    }

    return response.text();
  },

  /**
   * Get cut layout SVGs showing bin-packed pieces on 4x8 sheets
   */
  async getCutLayouts(config: CabinetConfig): Promise<CutLayoutsResponse> {
    const response = await fetch(`${API_BASE_URL}/export/cut-layouts-from-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail?.error || error.detail || 'Failed to get cut layouts');
    }

    return response.json();
  },
};
