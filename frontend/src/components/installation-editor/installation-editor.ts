import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  cabinetStore,
  setInstallation,
} from '@/state/cabinet-state';
import {
  WALL_TYPE_LABELS,
  MOUNTING_SYSTEM_LABELS,
  LOAD_CATEGORY_LABELS,
  DEFAULT_INSTALLATION,
  DEFAULT_CLEAT,
  type InstallationSpec,
  type CleatSpec,
  type WallType,
  type MountingSystem,
  type LoadCategory,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/switch/switch.js';
import '@shoelace-style/shoelace/dist/components/details/details.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';

@customElement('installation-editor')
export class InstallationEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .section {
      margin-bottom: 1rem;
    }

    .section-title {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-neutral-600);
      margin-bottom: 0.5rem;
    }

    .fields-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    .cleat-section {
      margin-top: 1rem;
      padding: 0.75rem;
      background: var(--sl-color-neutral-50);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
    }

    .cleat-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.75rem;
    }

    .cleat-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--sl-color-neutral-700);
    }

    .switch-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.5rem 0;
    }

    .switch-label {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(form-control-label),
    sl-select::part(form-control-label) {
      font-size: 0.7rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input),
    sl-select::part(combobox) {
      font-size: 0.8rem;
    }

    .info-text {
      font-size: 0.7rem;
      color: var(--sl-color-neutral-500);
      margin-top: 0.5rem;
      line-height: 1.4;
    }
  `;

  @state()
  private installation: InstallationSpec | null = null;

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      this.installation = state.config.installation || null;
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private getOrCreateInstallation(): InstallationSpec {
    return this.installation || { ...DEFAULT_INSTALLATION };
  }

  private updateInstallation(updates: Partial<InstallationSpec>): void {
    const current = this.getOrCreateInstallation();
    setInstallation({ ...current, ...updates });
  }

  private handleWallTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.updateInstallation({ wall_type: target.value as WallType });
  }

  private handleMountingSystemChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const mounting_system = target.value as MountingSystem;
    const updates: Partial<InstallationSpec> = { mounting_system };

    // Initialize cleat config if switching to french_cleat
    if (mounting_system === 'french_cleat' && !this.installation?.cleat) {
      updates.cleat = { ...DEFAULT_CLEAT };
    } else if (mounting_system !== 'french_cleat') {
      updates.cleat = undefined;
    }

    this.updateInstallation(updates);
  }

  private handleLoadChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.updateInstallation({ expected_load: target.value as LoadCategory });
  }

  private handleStudSpacingChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const val = parseFloat(target.value);
    if (!isNaN(val)) {
      this.updateInstallation({ stud_spacing: val });
    }
  }

  private handleStudOffsetChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const val = parseFloat(target.value);
    if (!isNaN(val)) {
      this.updateInstallation({ stud_offset: val });
    }
  }

  private updateCleat(updates: Partial<CleatSpec>): void {
    const current = this.installation?.cleat || { ...DEFAULT_CLEAT };
    this.updateInstallation({ cleat: { ...current, ...updates } });
  }

  private renderCleatSection() {
    if (this.installation?.mounting_system !== 'french_cleat') {
      return null;
    }

    const cleat = this.installation.cleat || { ...DEFAULT_CLEAT };

    return html`
      <div class="cleat-section">
        <div class="cleat-header">
          <span class="cleat-label">French Cleat Settings</span>
        </div>

        <div class="fields-grid">
          <sl-input
            type="number"
            label="Position from Top (in)"
            size="small"
            .value=${String(cleat.position_from_top)}
            min="1"
            max="24"
            step="0.5"
            @sl-input=${(e: Event) => {
              const val = parseFloat((e.target as HTMLInputElement).value);
              if (!isNaN(val)) this.updateCleat({ position_from_top: val });
            }}
          ></sl-input>

          <sl-input
            type="number"
            label="Bevel Angle"
            size="small"
            .value=${String(cleat.bevel_angle)}
            min="30"
            max="60"
            step="5"
            @sl-input=${(e: Event) => {
              const val = parseFloat((e.target as HTMLInputElement).value);
              if (!isNaN(val)) this.updateCleat({ bevel_angle: val });
            }}
          ></sl-input>

          <sl-input
            type="number"
            label="Width (%)"
            size="small"
            .value=${String(cleat.width_percentage)}
            min="50"
            max="100"
            step="5"
            @sl-input=${(e: Event) => {
              const val = parseFloat((e.target as HTMLInputElement).value);
              if (!isNaN(val)) this.updateCleat({ width_percentage: val });
            }}
          ></sl-input>
        </div>

        <div class="info-text">
          French cleats provide strong, adjustable wall mounting.
          Standard bevel angle is 45 degrees.
        </div>
      </div>
    `;
  }

  render() {
    const wallTypes = Object.entries(WALL_TYPE_LABELS) as [WallType, string][];
    const mountingSystems = Object.entries(MOUNTING_SYSTEM_LABELS) as [MountingSystem, string][];
    const loadCategories = Object.entries(LOAD_CATEGORY_LABELS) as [LoadCategory, string][];

    const current = this.getOrCreateInstallation();

    return html`
      <div class="section">
        <div class="section-title">Wall & Mounting</div>
        <div class="fields-grid">
          <sl-select
            label="Wall Type"
            size="small"
            .value=${current.wall_type}
            @sl-change=${this.handleWallTypeChange}
          >
            ${wallTypes.map(([val, label]) => html`
              <sl-option value=${val}>${label}</sl-option>
            `)}
          </sl-select>

          <sl-select
            label="Mounting System"
            size="small"
            .value=${current.mounting_system}
            @sl-change=${this.handleMountingSystemChange}
          >
            ${mountingSystems.map(([val, label]) => html`
              <sl-option value=${val}>${label}</sl-option>
            `)}
          </sl-select>

          <sl-select
            label="Expected Load"
            size="small"
            .value=${current.expected_load}
            @sl-change=${this.handleLoadChange}
          >
            ${loadCategories.map(([val, label]) => html`
              <sl-option value=${val}>${label}</sl-option>
            `)}
          </sl-select>

          <sl-input
            type="number"
            label="Stud Spacing (in)"
            size="small"
            .value=${String(current.stud_spacing)}
            min="12"
            max="24"
            step="4"
            @sl-input=${this.handleStudSpacingChange}
          ></sl-input>
        </div>

        <div class="info-text">
          Wall type determines fastener recommendations.
          Expected load affects structural requirements.
        </div>
      </div>

      ${this.renderCleatSection()}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'installation-editor': InstallationEditor;
  }
}
