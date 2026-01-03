import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  SECTION_TYPE_LABELS,
  DEFAULT_DOOR_CONFIG,
  DEFAULT_DRAWER_CONFIG,
  DEFAULT_CUBBY_CONFIG,
  isCompositeSection,
  type SectionSpec,
  type SectionType,
  type SectionRowSpec,
  type DoorComponentConfig,
  type DrawerComponentConfig,
  type CubbyComponentConfig,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/details/details.js';

import './component-config/door-config.js';
import './component-config/drawer-config.js';
import './component-config/cubby-config.js';

@customElement('section-card')
export class SectionCard extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .section-card {
      background: var(--sl-color-neutral-50);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.75rem;
    }

    .section-card.doored {
      border-left: 3px solid var(--sl-color-blue-500);
    }

    .section-card.drawers {
      border-left: 3px solid var(--sl-color-green-500);
    }

    .section-card.cubby {
      border-left: 3px solid var(--sl-color-purple-500);
    }

    .section-card.open {
      border-left: 3px solid var(--sl-color-neutral-400);
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.75rem;
    }

    .section-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--sl-color-neutral-700);
    }

    .section-type-badge {
      font-size: 0.7rem;
      padding: 0.125rem 0.375rem;
      border-radius: var(--sl-border-radius-small);
      background: var(--sl-color-neutral-200);
      color: var(--sl-color-neutral-700);
      margin-left: 0.5rem;
    }

    .section-fields {
      display: grid;
      grid-template-columns: 5rem 1fr;
      gap: 0.5rem;
    }

    .section-fields.three-col {
      grid-template-columns: 5rem 5rem 1fr;
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

    sl-icon-button::part(base) {
      color: var(--sl-color-neutral-500);
    }

    sl-icon-button::part(base):hover {
      color: var(--sl-color-danger-600);
    }

    .component-config {
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px dashed var(--sl-color-neutral-200);
    }

    .config-header {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-neutral-600);
      margin-bottom: 0.5rem;
    }

    sl-details {
      margin-top: 0.5rem;
    }

    sl-details::part(base) {
      border: none;
      background: transparent;
    }

    sl-details::part(header) {
      padding: 0.25rem 0;
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-neutral-500);
    }

    sl-details::part(content) {
      padding: 0.5rem 0 0;
    }

    /* Composite section (with rows) styles */
    .section-card.composite {
      border-left: 3px solid var(--sl-color-amber-500);
    }

    .composite-badge {
      font-size: 0.7rem;
      padding: 0.125rem 0.375rem;
      border-radius: var(--sl-border-radius-small);
      background: var(--sl-color-amber-100);
      color: var(--sl-color-amber-800);
      margin-left: 0.5rem;
    }

    .rows-list {
      margin-top: 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .row-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem;
      background: var(--sl-color-neutral-100);
      border-radius: var(--sl-border-radius-small);
      font-size: 0.8rem;
    }

    .row-height {
      font-weight: 500;
      color: var(--sl-color-neutral-700);
      min-width: 3rem;
    }

    .row-type {
      padding: 0.125rem 0.375rem;
      border-radius: var(--sl-border-radius-small);
      background: var(--sl-color-neutral-200);
      color: var(--sl-color-neutral-700);
      font-size: 0.7rem;
    }

    .row-type.doored { background: var(--sl-color-blue-100); color: var(--sl-color-blue-700); }
    .row-type.drawers { background: var(--sl-color-green-100); color: var(--sl-color-green-700); }
    .row-type.cubby { background: var(--sl-color-purple-100); color: var(--sl-color-purple-700); }
    .row-type.open { background: var(--sl-color-neutral-200); color: var(--sl-color-neutral-700); }

    .row-details {
      color: var(--sl-color-neutral-500);
      font-size: 0.75rem;
    }
  `;

  @property({ type: Object })
  section!: SectionSpec;

  @property({ type: Number })
  index = 0;

  @property({ type: Boolean })
  canRemove = true;

  @state()
  private showAdvanced = false;

  private dispatchUpdate(updates: Partial<SectionSpec>): void {
    this.dispatchEvent(new CustomEvent('section-update', {
      detail: updates,
      bubbles: true,
      composed: true,
    }));
  }

  private dispatchRemove(): void {
    this.dispatchEvent(new CustomEvent('section-remove', {
      bubbles: true,
      composed: true,
    }));
  }

  private handleTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const newType = target.value as SectionType;
    const updates: Partial<SectionSpec> = { section_type: newType };

    // Set default component config based on type
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

    this.dispatchUpdate(updates);
  }

  private handleShelvesChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const shelves = parseInt(target.value, 10);
    if (!isNaN(shelves) && shelves >= 0) {
      this.dispatchUpdate({ shelves });
    }
  }

  private handleWidthChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = target.value.trim();

    if (value === 'fill' || value === '') {
      this.dispatchUpdate({ width: 'fill' });
    } else {
      const width = parseFloat(value);
      if (!isNaN(width) && width > 0) {
        this.dispatchUpdate({ width });
      }
    }
  }

  private handleComponentConfigUpdate(event: CustomEvent): void {
    const updates = event.detail;
    const currentConfig = this.section.component_config || {};
    this.dispatchUpdate({
      component_config: { ...currentConfig, ...updates }
    });
  }

  private renderComponentConfig() {
    const { section_type, component_config } = this.section;

    if (!section_type || section_type === 'open') {
      return null;
    }

    return html`
      <div class="component-config">
        <div class="config-header">${SECTION_TYPE_LABELS[section_type]} Options</div>
        ${section_type === 'doored' ? html`
          <door-config
            .config=${component_config as DoorComponentConfig || DEFAULT_DOOR_CONFIG}
            @config-update=${this.handleComponentConfigUpdate}
          ></door-config>
        ` : null}
        ${section_type === 'drawers' ? html`
          <drawer-config
            .config=${component_config as DrawerComponentConfig || DEFAULT_DRAWER_CONFIG}
            @config-update=${this.handleComponentConfigUpdate}
          ></drawer-config>
        ` : null}
        ${section_type === 'cubby' ? html`
          <cubby-config
            .config=${component_config as CubbyComponentConfig || DEFAULT_CUBBY_CONFIG}
            @config-update=${this.handleComponentConfigUpdate}
          ></cubby-config>
        ` : null}
      </div>
    `;
  }

  private renderRowItem(row: SectionRowSpec, index: number) {
    const heightDisplay = row.height === 'fill' ? 'fill' : `${row.height}"`;
    const typeLabel = SECTION_TYPE_LABELS[row.section_type] || row.section_type;
    const shelvesInfo = row.shelves !== undefined && row.shelves > 0 ? `${row.shelves} shelves` : '';

    return html`
      <div class="row-item">
        <span class="row-height">${heightDisplay}</span>
        <span class="row-type ${row.section_type}">${typeLabel}</span>
        ${shelvesInfo ? html`<span class="row-details">${shelvesInfo}</span>` : null}
      </div>
    `;
  }

  private renderCompositeSection() {
    const widthDisplay = this.section.width === 'fill' ? '' : String(this.section.width);
    const rows = this.section.rows || [];

    return html`
      <div class="section-card composite">
        <div class="section-header">
          <span class="section-label">
            Section ${this.index + 1}
            <span class="composite-badge">Composite (${rows.length} rows)</span>
          </span>
          ${this.canRemove ? html`
            <sl-icon-button
              name="x-lg"
              label="Remove section"
              @click=${this.dispatchRemove}
            ></sl-icon-button>
          ` : null}
        </div>

        <div class="section-fields">
          <sl-input
            type="text"
            label="Width"
            .value=${widthDisplay}
            placeholder="fill"
            @sl-input=${this.handleWidthChange}
          ></sl-input>
        </div>

        <div class="rows-list">
          ${[...rows].reverse().map((row, idx) => this.renderRowItem(row, rows.length - 1 - idx))}
        </div>
      </div>
    `;
  }

  render() {
    // Handle composite sections (with rows) differently
    if (isCompositeSection(this.section)) {
      return this.renderCompositeSection();
    }

    const sectionTypes = Object.entries(SECTION_TYPE_LABELS) as [SectionType, string][];
    const widthDisplay = this.section.width === 'fill' ? '' : String(this.section.width);
    const sectionType = this.section.section_type || 'open';
    // Only show shelves for section types that use them
    const showShelves = sectionType === 'open' || sectionType === 'doored';

    return html`
      <div class="section-card ${sectionType}">
        <div class="section-header">
          <span class="section-label">
            Section ${this.index + 1}
            <span class="section-type-badge">${SECTION_TYPE_LABELS[sectionType]}</span>
          </span>
          ${this.canRemove ? html`
            <sl-icon-button
              name="x-lg"
              label="Remove section"
              @click=${this.dispatchRemove}
            ></sl-icon-button>
          ` : null}
        </div>

        <div class="section-fields ${showShelves ? 'three-col' : ''}">
          <sl-input
            type="text"
            label="Width"
            .value=${widthDisplay}
            placeholder="fill"
            @sl-input=${this.handleWidthChange}
          ></sl-input>

          ${showShelves ? html`
            <sl-input
              type="number"
              label="Shelves"
              .value=${String(this.section.shelves ?? 0)}
              min="0"
              max="20"
              @sl-input=${this.handleShelvesChange}
            ></sl-input>
          ` : null}

          <sl-select
            label="Type"
            .value=${sectionType}
            @sl-change=${this.handleTypeChange}
          >
            ${sectionTypes.map(([value, label]) => html`
              <sl-option value=${value}>${label}</sl-option>
            `)}
          </sl-select>
        </div>

        ${this.renderComponentConfig()}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'section-card': SectionCard;
  }
}
