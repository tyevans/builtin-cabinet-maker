import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  SECTION_TYPE_LABELS,
  DEFAULT_DOOR_CONFIG,
  DEFAULT_DRAWER_CONFIG,
  DEFAULT_CUBBY_CONFIG,
  isCompositeSection,
  type SectionSpec,
  type SectionRowSpec,
  type SectionType,
  type SectionSelection,
  type DoorComponentConfig,
  type DrawerComponentConfig,
  type CubbyComponentConfig,
  type WallSegmentSpec,
} from '@/api/types';
import {
  cabinetStore,
  type CabinetState,
  updateSection,
  removeSection,
  updateSectionRow,
  removeSectionRow,
  addSectionRow,
  convertToComposite,
  convertToSimple,
} from '@/state/cabinet-state';

import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/divider/divider.js';

import '../section-editor/component-config/door-config.js';
import '../section-editor/component-config/drawer-config.js';
import '../section-editor/component-config/cubby-config.js';

@customElement('section-properties')
export class SectionProperties extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .empty-state {
      text-align: center;
      padding: 2rem 1rem;
      color: var(--sl-color-neutral-500);
    }

    .empty-state sl-icon {
      font-size: 2rem;
      margin-bottom: 0.5rem;
    }

    .properties-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }

    .properties-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--sl-color-neutral-700);
    }

    .properties-badge {
      font-size: 0.7rem;
      padding: 0.125rem 0.5rem;
      border-radius: var(--sl-border-radius-small);
      background: var(--sl-color-neutral-200);
      color: var(--sl-color-neutral-600);
    }

    .properties-badge.composite {
      background: var(--sl-color-amber-100);
      color: var(--sl-color-amber-800);
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }

    .form-grid.single-col {
      grid-template-columns: 1fr;
    }

    .form-group {
      grid-column: span 1;
    }

    .form-group.full-width {
      grid-column: span 2;
    }

    sl-input::part(form-control-label),
    sl-select::part(form-control-label) {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input),
    sl-select::part(combobox) {
      font-size: 0.875rem;
    }

    .component-config {
      margin-top: 1rem;
    }

    .config-label {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-neutral-600);
      margin-bottom: 0.5rem;
    }

    .actions {
      margin-top: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .action-row {
      display: flex;
      gap: 0.5rem;
    }

    sl-divider {
      --spacing: 1rem;
    }

    .danger-zone {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px dashed var(--sl-color-neutral-200);
    }

    .danger-zone-title {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-danger-600);
      margin-bottom: 0.5rem;
    }
  `;

  @property({ type: Array })
  sections: SectionSpec[] = [];

  @property({ type: Object })
  selectedSection: SectionSelection | null = null;

  @state()
  private cabinetState: CabinetState = cabinetStore.getState();

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      this.cabinetState = state;
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private get walls(): WallSegmentSpec[] {
    return this.cabinetState.config.room?.walls || [];
  }

  /**
   * Resolves a wall reference (name or index) to a wall index.
   * Returns null if not assigned or not found.
   */
  private resolveWallIndex(wall: string | number | null | undefined): number | null {
    if (wall === null || wall === undefined) return null;

    if (typeof wall === 'number') {
      return wall < this.walls.length ? wall : null;
    }

    // It's a string - find by name
    const index = this.walls.findIndex(w => w.name === wall);
    return index >= 0 ? index : null;
  }

  private get currentSection(): SectionSpec | null {
    if (!this.selectedSection) return null;
    return this.sections[this.selectedSection.sectionIndex] || null;
  }

  private get currentRow(): SectionRowSpec | null {
    const section = this.currentSection;
    if (!section?.rows || this.selectedSection?.rowIndex === undefined) return null;
    return section.rows[this.selectedSection.rowIndex] || null;
  }

  private get isEditingRow(): boolean {
    return this.selectedSection?.rowIndex !== undefined;
  }

  private handleWidthChange(e: Event): void {
    if (!this.selectedSection) return;
    const target = e.target as HTMLInputElement;
    const value = target.value.trim();

    let width: number | 'fill' = 'fill';
    if (value !== '' && value !== 'fill') {
      const parsed = parseFloat(value);
      if (!isNaN(parsed) && parsed > 0) {
        width = parsed;
      }
    }

    updateSection(this.selectedSection.sectionIndex, { width });
  }

  private handleWallChange(e: Event): void {
    if (!this.selectedSection) return;
    const target = e.target as HTMLSelectElement;
    const value = target.value;

    // Convert value: empty string = null (unassigned), otherwise parse as number
    const wall = value === '' ? null : parseInt(value, 10);
    updateSection(this.selectedSection.sectionIndex, { wall });
  }

  private handleHeightChange(e: Event): void {
    if (!this.selectedSection || this.selectedSection.rowIndex === undefined) return;
    const target = e.target as HTMLInputElement;
    const value = target.value.trim();

    let height: number | 'fill' = 'fill';
    if (value !== '' && value !== 'fill') {
      const parsed = parseFloat(value);
      if (!isNaN(parsed) && parsed > 0) {
        height = parsed;
      }
    }

    updateSectionRow(
      this.selectedSection.sectionIndex,
      this.selectedSection.rowIndex,
      { height }
    );
  }

  private handleSectionTypeChange(e: Event): void {
    if (!this.selectedSection) return;
    const target = e.target as HTMLSelectElement;
    const newType = target.value as SectionType;

    if (this.isEditingRow && this.selectedSection.rowIndex !== undefined) {
      // Update row type
      const updates: Partial<SectionRowSpec> = { section_type: newType };

      switch (newType) {
        case 'doored':
          updates.component_config = { ...DEFAULT_DOOR_CONFIG };
          break;
        case 'drawers':
          updates.component_config = { ...DEFAULT_DRAWER_CONFIG };
          break;
        case 'cubby':
          updates.component_config = { ...DEFAULT_CUBBY_CONFIG };
          break;
        default:
          updates.component_config = undefined;
      }

      updateSectionRow(
        this.selectedSection.sectionIndex,
        this.selectedSection.rowIndex,
        updates
      );
    } else {
      // Update section type
      const updates: Partial<SectionSpec> = { section_type: newType };

      switch (newType) {
        case 'doored':
          updates.component_config = { ...DEFAULT_DOOR_CONFIG };
          break;
        case 'drawers':
          updates.component_config = { ...DEFAULT_DRAWER_CONFIG };
          break;
        case 'cubby':
          updates.component_config = { ...DEFAULT_CUBBY_CONFIG };
          break;
        default:
          updates.component_config = undefined;
      }

      updateSection(this.selectedSection.sectionIndex, updates);
    }
  }

  private handleShelvesChange(e: Event): void {
    if (!this.selectedSection) return;
    const target = e.target as HTMLInputElement;
    const shelves = parseInt(target.value, 10);
    if (isNaN(shelves) || shelves < 0) return;

    if (this.isEditingRow && this.selectedSection.rowIndex !== undefined) {
      updateSectionRow(
        this.selectedSection.sectionIndex,
        this.selectedSection.rowIndex,
        { shelves }
      );
    } else {
      updateSection(this.selectedSection.sectionIndex, { shelves });
    }
  }

  private handleComponentConfigUpdate(e: CustomEvent): void {
    if (!this.selectedSection) return;
    const updates = e.detail;

    if (this.isEditingRow && this.selectedSection.rowIndex !== undefined) {
      const currentConfig = this.currentRow?.component_config || {};
      updateSectionRow(
        this.selectedSection.sectionIndex,
        this.selectedSection.rowIndex,
        { component_config: { ...currentConfig, ...updates } }
      );
    } else {
      const currentConfig = this.currentSection?.component_config || {};
      updateSection(this.selectedSection.sectionIndex, {
        component_config: { ...currentConfig, ...updates }
      });
    }
  }

  private handleAddRow(): void {
    if (!this.selectedSection) return;
    addSectionRow(this.selectedSection.sectionIndex);
  }

  private handleConvertToComposite(): void {
    if (!this.selectedSection) return;
    convertToComposite(this.selectedSection.sectionIndex);
  }

  private handleConvertToSimple(): void {
    if (!this.selectedSection) return;
    convertToSimple(this.selectedSection.sectionIndex);
  }

  private handleDeleteSection(): void {
    if (!this.selectedSection) return;
    removeSection(this.selectedSection.sectionIndex);
    this.dispatchEvent(new CustomEvent('clear-selection', {
      bubbles: true,
      composed: true,
    }));
  }

  private handleDeleteRow(): void {
    if (!this.selectedSection || this.selectedSection.rowIndex === undefined) return;
    removeSectionRow(
      this.selectedSection.sectionIndex,
      this.selectedSection.rowIndex
    );
    // Select the parent section after deleting
    this.dispatchEvent(new CustomEvent('selection-change', {
      detail: { sectionIndex: this.selectedSection.sectionIndex },
      bubbles: true,
      composed: true,
    }));
  }

  private renderComponentConfig(type: SectionType, config: unknown) {
    if (type === 'open') return null;

    return html`
      <div class="component-config">
        <div class="config-label">${SECTION_TYPE_LABELS[type]} Options</div>
        ${type === 'doored' ? html`
          <door-config
            .config=${(config as DoorComponentConfig) || DEFAULT_DOOR_CONFIG}
            @config-update=${this.handleComponentConfigUpdate}
          ></door-config>
        ` : null}
        ${type === 'drawers' ? html`
          <drawer-config
            .config=${(config as DrawerComponentConfig) || DEFAULT_DRAWER_CONFIG}
            @config-update=${this.handleComponentConfigUpdate}
          ></drawer-config>
        ` : null}
        ${type === 'cubby' ? html`
          <cubby-config
            .config=${(config as CubbyComponentConfig) || DEFAULT_CUBBY_CONFIG}
            @config-update=${this.handleComponentConfigUpdate}
          ></cubby-config>
        ` : null}
      </div>
    `;
  }

  private renderRowProperties() {
    const row = this.currentRow;
    if (!row) return null;

    const heightDisplay = row.height === 'fill' ? '' : String(row.height);
    const sectionTypes = Object.entries(SECTION_TYPE_LABELS) as [SectionType, string][];
    const showShelves = row.section_type === 'open' || row.section_type === 'doored';

    return html`
      <div class="properties-header">
        <span class="properties-title">Row Properties</span>
        <span class="properties-badge">${SECTION_TYPE_LABELS[row.section_type]}</span>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <sl-input
            type="text"
            label="Height"
            .value=${heightDisplay}
            placeholder="fill"
            @sl-input=${this.handleHeightChange}
          ></sl-input>
        </div>

        <div class="form-group">
          <sl-select
            label="Type"
            .value=${row.section_type}
            @sl-change=${this.handleSectionTypeChange}
          >
            ${sectionTypes.map(([value, label]) => html`
              <sl-option value=${value}>${label}</sl-option>
            `)}
          </sl-select>
        </div>

        ${showShelves ? html`
          <div class="form-group">
            <sl-input
              type="number"
              label="Shelves"
              .value=${String(row.shelves ?? 0)}
              min="0"
              max="20"
              @sl-input=${this.handleShelvesChange}
            ></sl-input>
          </div>
        ` : null}
      </div>

      ${this.renderComponentConfig(row.section_type, row.component_config)}

      <div class="danger-zone">
        <div class="danger-zone-title">Danger Zone</div>
        <sl-button
          variant="danger"
          size="small"
          outline
          @click=${this.handleDeleteRow}
        >
          <sl-icon slot="prefix" name="trash"></sl-icon>
          Delete Row
        </sl-button>
      </div>
    `;
  }

  private renderSectionProperties() {
    const section = this.currentSection;
    if (!section) return null;

    const isComposite = isCompositeSection(section);
    const widthDisplay = section.width === 'fill' ? '' : String(section.width);
    const sectionTypes = Object.entries(SECTION_TYPE_LABELS) as [SectionType, string][];
    const sectionType = section.section_type || 'open';
    const showShelves = !isComposite && (sectionType === 'open' || sectionType === 'doored');
    const canConvertToSimple = isComposite && section.rows?.length === 1;

    return html`
      <div class="properties-header">
        <span class="properties-title">Section Properties</span>
        ${isComposite ? html`
          <span class="properties-badge composite">Composite (${section.rows?.length} rows)</span>
        ` : html`
          <span class="properties-badge">${SECTION_TYPE_LABELS[sectionType]}</span>
        `}
      </div>

      <div class="form-grid ${isComposite ? 'single-col' : ''}">
        <div class="form-group">
          <sl-input
            type="text"
            label="Width"
            .value=${widthDisplay}
            placeholder="fill"
            @sl-input=${this.handleWidthChange}
          ></sl-input>
        </div>

        ${!isComposite ? html`
          <div class="form-group">
            <sl-select
              label="Type"
              .value=${sectionType}
              @sl-change=${this.handleSectionTypeChange}
            >
              ${sectionTypes.map(([value, label]) => html`
                <sl-option value=${value}>${label}</sl-option>
              `)}
            </sl-select>
          </div>

          ${showShelves ? html`
            <div class="form-group">
              <sl-input
                type="number"
                label="Shelves"
                .value=${String(section.shelves ?? 0)}
                min="0"
                max="20"
                @sl-input=${this.handleShelvesChange}
              ></sl-input>
            </div>
          ` : null}
        ` : null}
      </div>

      ${this.walls.length > 0 ? html`
        <div class="form-grid single-col" style="margin-top: 0.75rem;">
          <div class="form-group">
            <sl-select
              label="Assigned Wall"
              .value=${(() => {
                const resolvedIndex = this.resolveWallIndex(section.wall);
                return resolvedIndex !== null ? String(resolvedIndex) : '';
              })()}
              @sl-change=${this.handleWallChange}
              placeholder="No wall assigned"
              clearable
            >
              ${this.walls.map((wall, index) => html`
                <sl-option value=${String(index)}>
                  Wall ${index + 1}${wall.name ? ` - ${wall.name}` : ''} (${wall.length}" × ${wall.height}")
                </sl-option>
              `)}
            </sl-select>
          </div>
        </div>
      ` : null}

      ${!isComposite ? this.renderComponentConfig(sectionType, section.component_config) : null}

      <div class="actions">
        ${isComposite ? html`
          <sl-button
            size="small"
            @click=${this.handleAddRow}
          >
            <sl-icon slot="prefix" name="plus-lg"></sl-icon>
            Add Row
          </sl-button>
          ${canConvertToSimple ? html`
            <sl-button
              size="small"
              variant="default"
              @click=${this.handleConvertToSimple}
            >
              <sl-icon slot="prefix" name="arrow-down-up"></sl-icon>
              Convert to Simple Section
            </sl-button>
          ` : null}
        ` : html`
          <sl-button
            size="small"
            variant="default"
            @click=${this.handleConvertToComposite}
          >
            <sl-icon slot="prefix" name="layers"></sl-icon>
            Convert to Composite (add rows)
          </sl-button>
        `}
      </div>

      <div class="danger-zone">
        <div class="danger-zone-title">Danger Zone</div>
        <sl-button
          variant="danger"
          size="small"
          outline
          ?disabled=${this.sections.length <= 1}
          @click=${this.handleDeleteSection}
        >
          <sl-icon slot="prefix" name="trash"></sl-icon>
          Delete Section
        </sl-button>
      </div>
    `;
  }

  render() {
    if (!this.selectedSection) {
      return html`
        <div class="empty-state">
          <sl-icon name="hand-index"></sl-icon>
          <p>Select a section or row to edit its properties</p>
        </div>
      `;
    }

    return this.isEditingRow
      ? this.renderRowProperties()
      : this.renderSectionProperties();
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'section-properties': SectionProperties;
  }
}
