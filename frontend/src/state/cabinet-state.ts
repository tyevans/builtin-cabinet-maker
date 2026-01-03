import { Store } from './store';
import type {
  CabinetConfig,
  LayoutOutput,
  Dimensions,
  MaterialSpec,
  SectionSpec,
  SectionRowSpec,
  SectionSelection,
  RoomSpec,
  WallSegmentSpec,
  ObstacleSpec,
  FaceFrameSpec,
  CrownMoldingSpec,
  BaseZoneSpec,
  LightRailSpec,
  // Infrastructure & Installation types
  InfrastructureSpec,
  InstallationSpec,
  ComponentConfig,
} from '@/api/types';

export interface CabinetState {
  config: CabinetConfig;
  layout: LayoutOutput | null;
  isGenerating: boolean;
  isDirty: boolean;
  lastError: string | null;
  selectedSection: SectionSelection | null;
}

const defaultConfig: CabinetConfig = {
  schema_version: '1.0',
  cabinet: {
    width: 48,
    height: 84,
    depth: 12,
    material: { type: 'plywood', thickness: 0.75 },
    back_material: { type: 'plywood', thickness: 0.25 },
    sections: [{ width: 'fill', shelves: 3, section_type: 'open' }],
  },
};

export const cabinetStore = new Store<CabinetState>({
  config: defaultConfig,
  layout: null,
  isGenerating: false,
  isDirty: false,
  lastError: null,
  selectedSection: null,
});

// Actions
export function setDimensions(dimensions: Dimensions): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: { ...prev.config.cabinet, ...dimensions },
    },
    isDirty: true,
    lastError: null,
  }));
}

export function setMaterial(material: MaterialSpec): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: { ...prev.config.cabinet, material },
    },
    isDirty: true,
    lastError: null,
  }));
}

export function setSections(sections: SectionSpec[]): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: { ...prev.config.cabinet, sections },
    },
    isDirty: true,
    lastError: null,
  }));
}

export function addSection(wall?: number | null): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const newSection: SectionSpec = {
      width: 'fill',
      shelves: 3,
      section_type: 'open',
      ...(wall !== undefined && wall !== null ? { wall } : {}),
    };
    return {
      config: {
        ...prev.config,
        cabinet: {
          ...prev.config.cabinet,
          sections: [...currentSections, newSection],
        },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function removeSection(index: number): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    if (currentSections.length <= 1) return prev; // Keep at least one section
    return {
      config: {
        ...prev.config,
        cabinet: {
          ...prev.config.cabinet,
          sections: currentSections.filter((_, i) => i !== index),
        },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function updateSection(index: number, updates: Partial<SectionSpec>): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const updatedSections = currentSections.map((section, i) =>
      i === index ? { ...section, ...updates } : section
    );
    return {
      config: {
        ...prev.config,
        cabinet: {
          ...prev.config.cabinet,
          sections: updatedSections,
        },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function setLayout(layout: LayoutOutput): void {
  cabinetStore.setState({ layout, isGenerating: false, lastError: null, isDirty: false });
}

export function setGenerating(isGenerating: boolean): void {
  cabinetStore.setState({ isGenerating });
}

export function setError(error: string): void {
  cabinetStore.setState({ lastError: error, isGenerating: false });
}

export function loadConfig(config: CabinetConfig): void {
  cabinetStore.setState({ config, isDirty: false, layout: null, lastError: null });
}

export function resetConfig(): void {
  cabinetStore.setState({
    config: defaultConfig,
    isDirty: false,
    layout: null,
    lastError: null
  });
}

// ============================================================================
// Back Material Actions
// ============================================================================

export function setBackMaterial(material: MaterialSpec): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: { ...prev.config.cabinet, back_material: material },
    },
    isDirty: true,
    lastError: null,
  }));
}

// ============================================================================
// Room Actions
// ============================================================================

export function setRoom(room: RoomSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      room: room || undefined,
    },
    isDirty: true,
    lastError: null,
  }));
}

export function addWallSegment(segment: WallSegmentSpec): void {
  cabinetStore.setState(prev => {
    const currentRoom = prev.config.room || { name: 'Room', walls: [], is_closed: false };
    return {
      config: {
        ...prev.config,
        room: {
          ...currentRoom,
          walls: [...currentRoom.walls, segment],
        },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function updateWallSegment(index: number, updates: Partial<WallSegmentSpec>): void {
  cabinetStore.setState(prev => {
    const currentRoom = prev.config.room;
    if (!currentRoom) return prev;

    const updatedWalls = currentRoom.walls.map((wall, i) =>
      i === index ? { ...wall, ...updates } : wall
    );
    return {
      config: {
        ...prev.config,
        room: { ...currentRoom, walls: updatedWalls },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function removeWallSegment(index: number): void {
  cabinetStore.setState(prev => {
    const currentRoom = prev.config.room;
    if (!currentRoom) return prev;

    const updatedWalls = currentRoom.walls.filter((_, i) => i !== index);
    return {
      config: {
        ...prev.config,
        room: updatedWalls.length > 0
          ? { ...currentRoom, walls: updatedWalls }
          : undefined,
      },
      isDirty: true,
      lastError: null,
    };
  });
}

// ============================================================================
// Obstacle Actions
// ============================================================================

export function addObstacle(obstacle: ObstacleSpec): void {
  cabinetStore.setState(prev => {
    const currentObstacles = prev.config.obstacles || [];
    return {
      config: {
        ...prev.config,
        obstacles: [...currentObstacles, obstacle],
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function updateObstacle(index: number, updates: Partial<ObstacleSpec>): void {
  cabinetStore.setState(prev => {
    const currentObstacles = prev.config.obstacles || [];
    const updatedObstacles = currentObstacles.map((obs, i) =>
      i === index ? { ...obs, ...updates } : obs
    );
    return {
      config: {
        ...prev.config,
        obstacles: updatedObstacles,
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function removeObstacle(index: number): void {
  cabinetStore.setState(prev => {
    const currentObstacles = prev.config.obstacles || [];
    const updatedObstacles = currentObstacles.filter((_, i) => i !== index);
    return {
      config: {
        ...prev.config,
        obstacles: updatedObstacles.length > 0 ? updatedObstacles : undefined,
      },
      isDirty: true,
      lastError: null,
    };
  });
}

// ============================================================================
// Decorative Element Actions
// ============================================================================

export function setFaceFrame(config: FaceFrameSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: {
        ...prev.config.cabinet,
        face_frame: config || undefined,
      },
    },
    isDirty: true,
    lastError: null,
  }));
}

export function setCrownMolding(config: CrownMoldingSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: {
        ...prev.config.cabinet,
        crown_molding: config || undefined,
      },
    },
    isDirty: true,
    lastError: null,
  }));
}

export function setBaseZone(config: BaseZoneSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: {
        ...prev.config.cabinet,
        base_zone: config || undefined,
      },
    },
    isDirty: true,
    lastError: null,
  }));
}

export function setLightRail(config: LightRailSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      cabinet: {
        ...prev.config.cabinet,
        light_rail: config || undefined,
      },
    },
    isDirty: true,
    lastError: null,
  }));
}

// ============================================================================
// Config Import/Export Actions
// ============================================================================

export function importConfig(config: CabinetConfig): void {
  cabinetStore.setState({
    config,
    isDirty: true,
    layout: null,
    lastError: null,
  });
}

// ============================================================================
// Section Component Config Actions
// ============================================================================

export function setSectionComponentConfig(
  sectionIndex: number,
  componentConfig: ComponentConfig | null
): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const updatedSections = currentSections.map((section, i) =>
      i === sectionIndex
        ? { ...section, component_config: componentConfig || undefined }
        : section
    );
    return {
      config: {
        ...prev.config,
        cabinet: {
          ...prev.config.cabinet,
          sections: updatedSections,
        },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

// ============================================================================
// Infrastructure Actions (FRD-15)
// ============================================================================

export function setInfrastructure(infrastructure: InfrastructureSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      infrastructure: infrastructure || undefined,
    },
    isDirty: true,
    lastError: null,
  }));
}

// ============================================================================
// Installation Actions (FRD-17)
// ============================================================================

export function setInstallation(installation: InstallationSpec | null): void {
  cabinetStore.setState(prev => ({
    config: {
      ...prev.config,
      installation: installation || undefined,
    },
    isDirty: true,
    lastError: null,
  }));
}

// ============================================================================
// Section Selection Actions (Tree View Editor)
// ============================================================================

export function setSelectedSection(selection: SectionSelection | null): void {
  cabinetStore.setState({ selectedSection: selection });
}

export function clearSelectedSection(): void {
  cabinetStore.setState({ selectedSection: null });
}

// ============================================================================
// Section Row Actions (Composite Section Management)
// ============================================================================

export function addSectionRow(sectionIndex: number): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const section = currentSections[sectionIndex];
    if (!section) return prev;

    const newRow: SectionRowSpec = {
      height: 'fill',
      section_type: 'open',
      shelves: 3,
    };

    const updatedSection: SectionSpec = {
      ...section,
      rows: [...(section.rows || []), newRow],
      // Clear top-level section_type/shelves when converting to composite
      section_type: undefined,
      shelves: undefined,
    };

    const updatedSections = currentSections.map((s, i) =>
      i === sectionIndex ? updatedSection : s
    );

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections: updatedSections },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function removeSectionRow(sectionIndex: number, rowIndex: number): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const section = currentSections[sectionIndex];
    if (!section?.rows) return prev;

    const updatedRows = section.rows.filter((_, i) => i !== rowIndex);

    let updatedSection: SectionSpec;
    if (updatedRows.length === 0) {
      // Convert back to simple section
      updatedSection = {
        ...section,
        rows: undefined,
        section_type: 'open',
        shelves: 3,
      };
    } else {
      updatedSection = { ...section, rows: updatedRows };
    }

    const updatedSections = currentSections.map((s, i) =>
      i === sectionIndex ? updatedSection : s
    );

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections: updatedSections },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function updateSectionRow(
  sectionIndex: number,
  rowIndex: number,
  updates: Partial<SectionRowSpec>
): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const section = currentSections[sectionIndex];
    if (!section?.rows) return prev;

    const updatedRows = section.rows.map((row, i) =>
      i === rowIndex ? { ...row, ...updates } : row
    );

    const updatedSections = currentSections.map((s, i) =>
      i === sectionIndex ? { ...s, rows: updatedRows } : s
    );

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections: updatedSections },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function convertToComposite(sectionIndex: number): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const section = currentSections[sectionIndex];
    if (!section || section.rows) return prev; // Already composite

    // Convert existing section to a single row
    const row: SectionRowSpec = {
      height: 'fill',
      section_type: section.section_type || 'open',
      shelves: section.shelves,
      component_config: section.component_config as Record<string, unknown>,
    };

    const updatedSection: SectionSpec = {
      ...section,
      rows: [row],
      section_type: undefined,
      shelves: undefined,
      component_config: undefined,
    };

    const updatedSections = currentSections.map((s, i) =>
      i === sectionIndex ? updatedSection : s
    );

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections: updatedSections },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

export function convertToSimple(sectionIndex: number): void {
  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const section = currentSections[sectionIndex];
    if (!section?.rows || section.rows.length !== 1) return prev; // Must have exactly 1 row

    const row = section.rows[0];
    const updatedSection: SectionSpec = {
      ...section,
      rows: undefined,
      section_type: row.section_type,
      shelves: row.shelves,
      component_config: row.component_config as ComponentConfig,
    };

    const updatedSections = currentSections.map((s, i) =>
      i === sectionIndex ? updatedSection : s
    );

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections: updatedSections },
      },
      isDirty: true,
      lastError: null,
    };
  });
}

// ============================================================================
// Section Reorder Actions (Drag and Drop)
// ============================================================================

export function reorderSections(fromIndex: number, toIndex: number): void {
  if (fromIndex === toIndex) return;

  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    if (fromIndex < 0 || fromIndex >= currentSections.length) return prev;
    if (toIndex < 0 || toIndex >= currentSections.length) return prev;

    const sections = [...currentSections];
    const [removed] = sections.splice(fromIndex, 1);
    sections.splice(toIndex, 0, removed);

    // Update selection if needed
    let selectedSection = prev.selectedSection;
    if (selectedSection) {
      if (selectedSection.sectionIndex === fromIndex) {
        selectedSection = { ...selectedSection, sectionIndex: toIndex };
      } else if (
        fromIndex < selectedSection.sectionIndex &&
        toIndex >= selectedSection.sectionIndex
      ) {
        selectedSection = { ...selectedSection, sectionIndex: selectedSection.sectionIndex - 1 };
      } else if (
        fromIndex > selectedSection.sectionIndex &&
        toIndex <= selectedSection.sectionIndex
      ) {
        selectedSection = { ...selectedSection, sectionIndex: selectedSection.sectionIndex + 1 };
      }
    }

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections },
      },
      isDirty: true,
      lastError: null,
      selectedSection,
    };
  });
}

export function reorderSectionRows(
  sectionIndex: number,
  fromIndex: number,
  toIndex: number
): void {
  if (fromIndex === toIndex) return;

  cabinetStore.setState(prev => {
    const currentSections = prev.config.cabinet.sections || [];
    const section = currentSections[sectionIndex];
    if (!section?.rows) return prev;
    if (fromIndex < 0 || fromIndex >= section.rows.length) return prev;
    if (toIndex < 0 || toIndex >= section.rows.length) return prev;

    const rows = [...section.rows];
    const [removed] = rows.splice(fromIndex, 1);
    rows.splice(toIndex, 0, removed);

    const updatedSections = currentSections.map((s, i) =>
      i === sectionIndex ? { ...s, rows } : s
    );

    // Update selection if needed
    let selectedSection = prev.selectedSection;
    if (selectedSection?.sectionIndex === sectionIndex && selectedSection.rowIndex !== undefined) {
      if (selectedSection.rowIndex === fromIndex) {
        selectedSection = { ...selectedSection, rowIndex: toIndex };
      } else if (
        fromIndex < selectedSection.rowIndex &&
        toIndex >= selectedSection.rowIndex
      ) {
        selectedSection = { ...selectedSection, rowIndex: selectedSection.rowIndex - 1 };
      } else if (
        fromIndex > selectedSection.rowIndex &&
        toIndex <= selectedSection.rowIndex
      ) {
        selectedSection = { ...selectedSection, rowIndex: selectedSection.rowIndex + 1 };
      }
    }

    return {
      config: {
        ...prev.config,
        cabinet: { ...prev.config.cabinet, sections: updatedSections },
      },
      isDirty: true,
      lastError: null,
      selectedSection,
    };
  });
}
