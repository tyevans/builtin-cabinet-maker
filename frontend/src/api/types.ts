/**
 * TypeScript types matching the backend schemas
 */

// Material types matching backend MaterialTypeEnum
export type MaterialType = 'plywood' | 'mdf' | 'particle_board' | 'solid_wood';

// Section types matching backend SectionTypeEnum
export type SectionType = 'open' | 'doored' | 'drawers' | 'cubby';

// Dimensions
export interface Dimensions {
  width: number;  // 0 < width <= 240
  height: number; // 0 < height <= 120
  depth: number;  // 0 < depth <= 36
}

// Material specification
export interface MaterialSpec {
  type: MaterialType;
  thickness: number; // 0.25 to 2.0
}

// Section specification
// Note: section_type and shelves are optional when rows is present (composite section)
export interface SectionSpec {
  width: number | 'fill';
  shelves?: number;
  section_type?: SectionType;
  min_width?: number;
  max_width?: number | null;
  // Enhanced fields for backend parity
  wall?: string | number | null;
  height_mode?: HeightMode | null;
  depth?: number | null;
  component_config?: ComponentConfig;
  rows?: SectionRowSpec[] | null;
  arch_top?: ArchTopSpec | null;
  edge_profile?: EdgeProfileSpec | null;
  scallop?: ScallopSpec | null;
}

// Full cabinet configuration matching RootConfigSchema
export interface CabinetConfig {
  schema_version: string;
  cabinet: {
    width: number;
    height: number;
    depth: number;
    material?: MaterialSpec;
    back_material?: MaterialSpec;
    sections?: SectionSpec[];
    rows?: RowSpec[] | null; // Multi-row layout (alternative to sections)
    default_shelves?: number;
    // Decorative elements
    face_frame?: FaceFrameSpec;
    crown_molding?: CrownMoldingSpec;
    base_zone?: BaseZoneSpec;
    light_rail?: LightRailSpec;
    // Zone stack (FRD-22) - alternative to sections/rows
    zone_stack?: ZoneStackSpec | null;
  };
  room?: RoomSpec;
  obstacles?: ObstacleSpec[];
  // Infrastructure (FRD-15)
  infrastructure?: InfrastructureSpec | null;
  // Installation (FRD-17)
  installation?: InstallationSpec | null;
  output?: {
    format?: string;
  };
}

// Cabinet summary in layout output
export interface CabinetSummary {
  width: number;
  height: number;
  depth: number;
  num_sections: number;
  total_shelves: number;
}

// Cut piece information
export interface CutPiece {
  label: string;
  width: number;
  height: number;
  thickness: number;
  material_type: string;
  quantity: number;
  notes?: string;
}

// Material estimate
export interface MaterialEstimate {
  sheet_count: number;
  total_area_sqft: number;
  waste_percentage: number;
}

// Layout output from generation
export interface LayoutOutput {
  is_valid: boolean;
  errors: string[];
  cabinet: CabinetSummary | null;
  cut_list: CutPiece[];
  material_estimates: Record<string, MaterialEstimate>;
  total_estimate: MaterialEstimate | null;
}

// Export format types
export type ExportFormat = 'stl' | 'dxf' | 'svg' | 'json' | 'assembly' | 'bom';

// Material type display names
export const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  plywood: 'Plywood',
  mdf: 'MDF',
  particle_board: 'Particle Board',
  solid_wood: 'Solid Wood',
};

// Section type display names
export const SECTION_TYPE_LABELS: Record<SectionType, string> = {
  open: 'Open Shelves',
  doored: 'With Doors',
  drawers: 'Drawers',
  cubby: 'Cubbies',
};

// Common material thicknesses (inches)
export const COMMON_THICKNESSES = [
  { value: 0.25, label: '1/4"' },
  { value: 0.5, label: '1/2"' },
  { value: 0.75, label: '3/4"' },
  { value: 1.0, label: '1"' },
  { value: 1.5, label: '1-1/2"' },
];

// ============================================================================
// Obstacle Types
// ============================================================================

export type ObstacleType = 'window' | 'door' | 'outlet' | 'switch' | 'vent' | 'custom';

export interface Clearance {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface ObstacleSpec {
  obstacle_type: ObstacleType;
  wall_index: number;
  horizontal_offset: number;
  bottom: number;
  width: number;
  height: number;
  clearance_override?: Clearance;
  name?: string;
  is_egress?: boolean;
}

export const OBSTACLE_TYPE_LABELS: Record<ObstacleType, string> = {
  window: 'Window',
  door: 'Door',
  outlet: 'Outlet',
  switch: 'Switch',
  vent: 'Vent',
  custom: 'Custom',
};

export const OBSTACLE_DEFAULTS: Record<ObstacleType, { width: number; height: number }> = {
  window: { width: 36, height: 48 },
  door: { width: 36, height: 80 },
  outlet: { width: 2.75, height: 4.5 },
  switch: { width: 2.75, height: 4.5 },
  vent: { width: 12, height: 6 },
  custom: { width: 12, height: 12 },
};

// ============================================================================
// Room Geometry Types
// ============================================================================

export interface WallSegmentSpec {
  length: number;
  height: number;
  angle?: number;
  name?: string;
  depth?: number;
  base_zone?: BaseZoneSpec;
}

export interface RoomSpec {
  name: string;
  walls: WallSegmentSpec[];
  is_closed?: boolean;
}

// ============================================================================
// Decorative Element Types
// ============================================================================

export type JoineryType = 'dado' | 'rabbet' | 'pocket_screw' | 'mortise_tenon' | 'dowel' | 'biscuit' | 'butt';
export type EdgeProfileType = 'chamfer' | 'roundover' | 'ogee' | 'bevel' | 'cove' | 'roman_ogee';

export interface FaceFrameSpec {
  enabled: boolean;
  stile_width: number;
  rail_width: number;
  joinery: JoineryType;
  material_thickness?: number;
}

export interface CrownMoldingSpec {
  enabled: boolean;
  height: number;
  setback: number;
  nailer_width?: number;
}

export interface BaseZoneSpec {
  enabled: boolean;
  height: number;
  setback: number;
}

export interface LightRailSpec {
  enabled: boolean;
  height: number;
  setback?: number;
}

export const JOINERY_TYPE_LABELS: Record<JoineryType, string> = {
  dado: 'Dado',
  rabbet: 'Rabbet',
  pocket_screw: 'Pocket Screw',
  mortise_tenon: 'Mortise & Tenon',
  dowel: 'Dowel',
  biscuit: 'Biscuit',
  butt: 'Butt Joint',
};

export const DEFAULT_FACE_FRAME: FaceFrameSpec = {
  enabled: false,
  stile_width: 1.5,
  rail_width: 1.5,
  joinery: 'pocket_screw',
  material_thickness: 0.75,
};

export const DEFAULT_CROWN_MOLDING: CrownMoldingSpec = {
  enabled: false,
  height: 3.0,
  setback: 0.75,
  nailer_width: 1.5,
};

export const DEFAULT_BASE_ZONE: BaseZoneSpec = {
  enabled: false,
  height: 3.5,
  setback: 3.0,
};

export const DEFAULT_LIGHT_RAIL: LightRailSpec = {
  enabled: false,
  height: 1.5,
  setback: 0.25,
};

// ============================================================================
// Zone Stack Types (FRD-22)
// ============================================================================

export type ZoneType = 'base' | 'upper' | 'gap' | 'bench' | 'open';
export type ZoneMounting = 'floor' | 'wall' | 'suspended' | 'on_base';
export type GapPurpose = 'backsplash' | 'mirror' | 'hooks' | 'workspace' | 'display';
export type ZonePreset = 'kitchen' | 'mudroom' | 'vanity' | 'hutch' | 'custom';
export type CountertopEdgeType = 'square' | 'eased' | 'bullnose' | 'beveled' | 'waterfall';

export const ZONE_TYPE_LABELS: Record<ZoneType, string> = {
  base: 'Base Cabinet',
  upper: 'Upper Cabinet',
  gap: 'Gap Zone',
  bench: 'Bench',
  open: 'Open Shelving',
};

export const ZONE_MOUNTING_LABELS: Record<ZoneMounting, string> = {
  floor: 'Floor Standing',
  wall: 'Wall Mounted',
  suspended: 'Suspended',
  on_base: 'On Base',
};

export const GAP_PURPOSE_LABELS: Record<GapPurpose, string> = {
  backsplash: 'Backsplash',
  mirror: 'Mirror',
  hooks: 'Hooks',
  workspace: 'Workspace',
  display: 'Display',
};

export const ZONE_PRESET_LABELS: Record<ZonePreset, string> = {
  kitchen: 'Kitchen',
  mudroom: 'Mudroom',
  vanity: 'Vanity',
  hutch: 'Hutch',
  custom: 'Custom',
};

export const COUNTERTOP_EDGE_LABELS: Record<CountertopEdgeType, string> = {
  square: 'Square',
  eased: 'Eased',
  bullnose: 'Bullnose',
  beveled: 'Beveled',
  waterfall: 'Waterfall',
};

export interface CountertopOverhangSpec {
  front: number;
  left: number;
  right: number;
  back: number;
}

export interface CountertopSpec {
  thickness: number;
  overhang: CountertopOverhangSpec;
  edge_treatment: CountertopEdgeType;
  support_brackets: boolean;
  material?: MaterialSpec;
}

export interface VerticalZoneSpec {
  zone_type: ZoneType;
  height: number;
  depth: number;
  mounting: ZoneMounting;
  mounting_height?: number;
  gap_purpose?: GapPurpose;
  sections: SectionSpec[];
}

export interface ZoneStackSpec {
  preset: ZonePreset;
  zones: VerticalZoneSpec[];
  countertop?: CountertopSpec;
  full_height_sides: boolean;
  upper_cabinet_height: number;
}

export const DEFAULT_COUNTERTOP: CountertopSpec = {
  thickness: 1.0,
  overhang: { front: 1.0, left: 0.0, right: 0.0, back: 0.0 },
  edge_treatment: 'square',
  support_brackets: false,
};

// ============================================================================
// Multi-Row Layout Types
// ============================================================================

export type HeightMode = 'full' | 'lower' | 'upper' | 'auto';

export const HEIGHT_MODE_LABELS: Record<HeightMode, string> = {
  full: 'Full Height',
  lower: 'Lower (below obstacles)',
  upper: 'Upper (above obstacles)',
  auto: 'Auto',
};

export interface SectionRowSpec {
  height: number | 'fill';
  section_type: SectionType;
  shelves?: number;
  component_config?: Record<string, unknown>;
  min_height?: number;
  max_height?: number;
}

/**
 * Check if a section is a composite section (has rows instead of direct section_type).
 */
export function isCompositeSection(section: SectionSpec): boolean {
  return Array.isArray(section.rows) && section.rows.length > 0;
}

export interface RowSpec {
  height: number | 'fill';
  sections: SectionSpec[];
  min_height?: number;
  max_height?: number;
}

// ============================================================================
// Section Decorative Elements (FRD-12)
// ============================================================================

export type ArchType = 'full_round' | 'segmental' | 'elliptical';

export const ARCH_TYPE_LABELS: Record<ArchType, string> = {
  full_round: 'Full Round',
  segmental: 'Segmental',
  elliptical: 'Elliptical',
};

export interface ArchTopSpec {
  arch_type: ArchType;
  radius: number | 'auto';
  spring_height: number;
}

export interface EdgeProfileSpec {
  profile_type: EdgeProfileType;
  size: number;
  edges: ('top' | 'bottom' | 'left' | 'right' | 'front')[] | 'auto';
}

export interface ScallopSpec {
  depth: number;
  width: number;
  count: number | 'auto';
}

// ============================================================================
// Component Configuration Types
// ============================================================================

export type DoorStyle = 'door.hinged.overlay' | 'door.hinged.inset' | 'door.hinged.partial';
export type DrawerStyle = 'drawer.standard' | 'drawer.file';
export type SlideType = 'side_mount' | 'undermount' | 'center_mount';
export type FrontStyle = 'overlay' | 'inset';
export type HandlePosition = 'upper' | 'lower';
export type HingeSide = 'left' | 'right';
export type CubbyStyle = 'cubby.uniform' | 'cubby.variable';

export const DOOR_STYLE_LABELS: Record<DoorStyle, string> = {
  'door.hinged.overlay': 'Overlay',
  'door.hinged.inset': 'Inset',
  'door.hinged.partial': 'Partial Overlay',
};

export const SLIDE_TYPE_LABELS: Record<SlideType, string> = {
  side_mount: 'Side Mount',
  undermount: 'Undermount',
  center_mount: 'Center Mount',
};

export const FRONT_STYLE_LABELS: Record<FrontStyle, string> = {
  overlay: 'Overlay',
  inset: 'Inset',
};

export const HANDLE_POSITION_LABELS: Record<HandlePosition, string> = {
  upper: 'Upper',
  lower: 'Lower',
};

export const HINGE_SIDE_LABELS: Record<HingeSide, string> = {
  left: 'Left',
  right: 'Right',
};

export interface DoorComponentConfig {
  component?: DoorStyle;
  count: 1 | 2;
  hinge_side?: HingeSide;
  reveal?: number;
  overlay?: number;
  soft_close?: boolean;
  handle_position?: HandlePosition;
}

export interface DrawerComponentConfig {
  component?: DrawerStyle;
  count: number;
  front_height?: number;
  slide_type?: SlideType;
  slide_length?: number;
  soft_close?: boolean;
  front_style?: FrontStyle;
}

export interface CubbyComponentConfig {
  component?: CubbyStyle;
  rows: number;
  columns: number;
  row_heights?: number[];
  column_widths?: number[];
  edge_band_front?: boolean;
}

export type ComponentConfig = DoorComponentConfig | DrawerComponentConfig | CubbyComponentConfig | Record<string, unknown>;

export const DEFAULT_DOOR_CONFIG: DoorComponentConfig = {
  component: 'door.hinged.overlay',
  count: 1,
  hinge_side: 'left',
  reveal: 0.125,
  overlay: 0.5,
  soft_close: true,
  handle_position: 'upper',
};

export const DEFAULT_DRAWER_CONFIG: DrawerComponentConfig = {
  component: 'drawer.standard',
  count: 3,
  slide_type: 'side_mount',
  soft_close: true,
  front_style: 'overlay',
};

export const DEFAULT_CUBBY_CONFIG: CubbyComponentConfig = {
  component: 'cubby.uniform',
  rows: 3,
  columns: 4,
  edge_band_front: true,
};

// ============================================================================
// Infrastructure Types (FRD-15)
// ============================================================================

export type LightingType = 'led_strip' | 'puck_light' | 'accent';
export type LightingLocation = 'under_cabinet' | 'in_cabinet' | 'toe_kick' | 'above_cabinet';
export type OutletType = 'single' | 'double' | 'gfi';
export type VentilationPattern = 'grid' | 'slot' | 'circular';
export type ConduitDirection = 'top' | 'bottom' | 'left' | 'right';

export const LIGHTING_TYPE_LABELS: Record<LightingType, string> = {
  led_strip: 'LED Strip',
  puck_light: 'Puck Light',
  accent: 'Accent',
};

export const LIGHTING_LOCATION_LABELS: Record<LightingLocation, string> = {
  under_cabinet: 'Under Cabinet',
  in_cabinet: 'In Cabinet',
  toe_kick: 'Toe Kick',
  above_cabinet: 'Above Cabinet',
};

export const OUTLET_TYPE_LABELS: Record<OutletType, string> = {
  single: 'Single',
  double: 'Double',
  gfi: 'GFI',
};

export const VENTILATION_PATTERN_LABELS: Record<VentilationPattern, string> = {
  grid: 'Grid',
  slot: 'Slot',
  circular: 'Circular',
};

export interface Position2D {
  x: number;
  y: number;
}

export interface LightingSpec {
  type: LightingType;
  location: LightingLocation;
  section_indices: number[];
  length?: number;
  diameter?: number;
  channel_width?: number;
  channel_depth?: number;
  position?: Position2D;
}

export interface InfraOutletSpec {
  type: OutletType;
  section_index: number;
  panel: 'back' | 'left_side' | 'right_side';
  position: Position2D;
  conduit_direction?: ConduitDirection;
}

export interface GrommetSpec {
  size: number;
  panel: string;
  position: Position2D;
  section_index?: number;
}

export interface CableChannelSpec {
  start: Position2D;
  end: Position2D;
  width?: number;
  depth?: number;
}

export interface VentilationSpec {
  pattern: VentilationPattern;
  panel: string;
  position: Position2D;
  width: number;
  height: number;
  hole_size?: number;
}

export interface WireRouteSpec {
  waypoints: Position2D[];
  hole_diameter?: number;
  panel_penetrations?: string[];
}

export interface InfrastructureSpec {
  lighting: LightingSpec[];
  outlets: InfraOutletSpec[];
  grommets: GrommetSpec[];
  cable_channels: CableChannelSpec[];
  ventilation: VentilationSpec[];
  wire_routes: WireRouteSpec[];
}

export const DEFAULT_INFRASTRUCTURE: InfrastructureSpec = {
  lighting: [],
  outlets: [],
  grommets: [],
  cable_channels: [],
  ventilation: [],
  wire_routes: [],
};

// ============================================================================
// Installation Types (FRD-17)
// ============================================================================

export type WallType = 'drywall' | 'plaster' | 'concrete' | 'cmu' | 'brick';
export type MountingSystem = 'direct_to_stud' | 'toggle_bolt' | 'french_cleat' | 'z_clip';
export type LoadCategory = 'light' | 'medium' | 'heavy' | 'extra_heavy';

export const WALL_TYPE_LABELS: Record<WallType, string> = {
  drywall: 'Drywall',
  plaster: 'Plaster',
  concrete: 'Concrete',
  cmu: 'CMU (Concrete Block)',
  brick: 'Brick',
};

export const MOUNTING_SYSTEM_LABELS: Record<MountingSystem, string> = {
  direct_to_stud: 'Direct to Stud',
  toggle_bolt: 'Toggle Bolt',
  french_cleat: 'French Cleat',
  z_clip: 'Z-Clip',
};

export const LOAD_CATEGORY_LABELS: Record<LoadCategory, string> = {
  light: 'Light',
  medium: 'Medium',
  heavy: 'Heavy',
  extra_heavy: 'Extra Heavy',
};

export interface CleatSpec {
  position_from_top: number;
  width_percentage: number;
  bevel_angle: number;
}

export interface InstallationSpec {
  wall_type: WallType;
  wall_thickness: number;
  stud_spacing: number;
  stud_offset: number;
  mounting_system: MountingSystem;
  expected_load: LoadCategory;
  cleat?: CleatSpec;
  generate_instructions: boolean;
}

export const DEFAULT_CLEAT: CleatSpec = {
  position_from_top: 4.0,
  width_percentage: 90.0,
  bevel_angle: 45.0,
};

export const DEFAULT_INSTALLATION: InstallationSpec = {
  wall_type: 'drywall',
  wall_thickness: 0.5,
  stud_spacing: 16.0,
  stud_offset: 0.0,
  mounting_system: 'direct_to_stud',
  expected_load: 'medium',
  generate_instructions: true,
};

// ============================================================================
// Section Selection (for tree view editor)
// ============================================================================

export interface SectionSelection {
  sectionIndex: number;
  rowIndex?: number;  // undefined = section selected, number = row within section selected
}
