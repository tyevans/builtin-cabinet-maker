import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  cabinetStore,
  setInfrastructure,
} from '@/state/cabinet-state';
import {
  LIGHTING_TYPE_LABELS,
  LIGHTING_LOCATION_LABELS,
  OUTLET_TYPE_LABELS,
  VENTILATION_PATTERN_LABELS,
  DEFAULT_INFRASTRUCTURE,
  type InfrastructureSpec,
  type LightingSpec,
  type InfraOutletSpec,
  type VentilationSpec,
  type LightingType,
  type LightingLocation,
  type OutletType,
  type VentilationPattern,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/switch/switch.js';
import '@shoelace-style/shoelace/dist/components/details/details.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';

@customElement('infrastructure-editor')
export class InfrastructureEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .items-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .item-card {
      background: var(--sl-color-neutral-50);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.5rem;
    }

    .item-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }

    .item-label {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-neutral-600);
    }

    .item-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }

    .add-button {
      margin-top: 0.5rem;
    }

    .add-button::part(base) {
      width: 100%;
      border-style: dashed;
      font-size: 0.75rem;
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

    sl-icon-button::part(base) {
      color: var(--sl-color-neutral-500);
      font-size: 0.875rem;
    }

    sl-icon-button::part(base):hover {
      color: var(--sl-color-danger-600);
    }

    sl-details::part(header) {
      font-size: 0.875rem;
      font-weight: 500;
      padding: 0.5rem 0.75rem;
    }

    sl-details::part(content) {
      padding: 0.5rem 0.75rem 0.75rem;
    }
  `;

  @state()
  private infrastructure: InfrastructureSpec | null = null;

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      this.infrastructure = state.config.infrastructure || null;
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private getOrCreateInfra(): InfrastructureSpec {
    return this.infrastructure || { ...DEFAULT_INFRASTRUCTURE };
  }

  private updateInfra(updates: Partial<InfrastructureSpec>): void {
    const current = this.getOrCreateInfra();
    setInfrastructure({ ...current, ...updates });
  }

  // Lighting handlers
  private addLighting(): void {
    const newLighting: LightingSpec = {
      type: 'led_strip',
      location: 'under_cabinet',
      section_indices: [0], // Default to first section
      length: 24.0, // Default 24" LED strip length
    };
    const current = this.getOrCreateInfra();
    this.updateInfra({ lighting: [...current.lighting, newLighting] });
  }

  private updateLighting(index: number, updates: Partial<LightingSpec>): void {
    const current = this.getOrCreateInfra();
    const lighting = current.lighting.map((l, i) =>
      i === index ? { ...l, ...updates } : l
    );
    this.updateInfra({ lighting });
  }

  private removeLighting(index: number): void {
    const current = this.getOrCreateInfra();
    this.updateInfra({ lighting: current.lighting.filter((_, i) => i !== index) });
  }

  // Outlet handlers
  private addOutlet(): void {
    const newOutlet: InfraOutletSpec = {
      type: 'single',
      section_index: 0,
      panel: 'back',
      position: { x: 0, y: 36 },
    };
    const current = this.getOrCreateInfra();
    this.updateInfra({ outlets: [...current.outlets, newOutlet] });
  }

  private updateOutlet(index: number, updates: Partial<InfraOutletSpec>): void {
    const current = this.getOrCreateInfra();
    const outlets = current.outlets.map((o, i) =>
      i === index ? { ...o, ...updates } : o
    );
    this.updateInfra({ outlets });
  }

  private removeOutlet(index: number): void {
    const current = this.getOrCreateInfra();
    this.updateInfra({ outlets: current.outlets.filter((_, i) => i !== index) });
  }

  // Ventilation handlers
  private addVentilation(): void {
    const newVent: VentilationSpec = {
      pattern: 'grid',
      panel: 'back',
      position: { x: 0, y: 0 },
      width: 4,
      height: 2,
    };
    const current = this.getOrCreateInfra();
    this.updateInfra({ ventilation: [...current.ventilation, newVent] });
  }

  private updateVentilation(index: number, updates: Partial<VentilationSpec>): void {
    const current = this.getOrCreateInfra();
    const ventilation = current.ventilation.map((v, i) =>
      i === index ? { ...v, ...updates } : v
    );
    this.updateInfra({ ventilation });
  }

  private removeVentilation(index: number): void {
    const current = this.getOrCreateInfra();
    this.updateInfra({ ventilation: current.ventilation.filter((_, i) => i !== index) });
  }

  private renderLightingSection() {
    const lighting = this.infrastructure?.lighting || [];
    const lightingTypes = Object.entries(LIGHTING_TYPE_LABELS) as [LightingType, string][];
    const locations = Object.entries(LIGHTING_LOCATION_LABELS) as [LightingLocation, string][];

    return html`
      <sl-details>
        <div slot="summary">
          Lighting
          ${lighting.length > 0 ? html`<sl-badge variant="neutral" pill>${lighting.length}</sl-badge>` : null}
        </div>

        <div class="items-list">
          ${lighting.map((light, index) => html`
            <div class="item-card">
              <div class="item-header">
                <span class="item-label">Light ${index + 1}</span>
                <sl-icon-button
                  name="x-lg"
                  label="Remove"
                  @click=${() => this.removeLighting(index)}
                ></sl-icon-button>
              </div>
              <div class="item-fields">
                <sl-select
                  label="Type"
                  size="small"
                  .value=${light.type}
                  @sl-change=${(e: Event) => this.updateLighting(index, { type: (e.target as HTMLSelectElement).value as LightingType })}
                >
                  ${lightingTypes.map(([val, label]) => html`
                    <sl-option value=${val}>${label}</sl-option>
                  `)}
                </sl-select>
                <sl-select
                  label="Location"
                  size="small"
                  .value=${light.location}
                  @sl-change=${(e: Event) => this.updateLighting(index, { location: (e.target as HTMLSelectElement).value as LightingLocation })}
                >
                  ${locations.map(([val, label]) => html`
                    <sl-option value=${val}>${label}</sl-option>
                  `)}
                </sl-select>
              </div>
            </div>
          `)}
        </div>

        <sl-button
          class="add-button"
          variant="default"
          size="small"
          @click=${this.addLighting}
        >
          <sl-icon slot="prefix" name="plus-lg"></sl-icon>
          Add Lighting
        </sl-button>
      </sl-details>
    `;
  }

  private renderOutletSection() {
    const outlets = this.infrastructure?.outlets || [];
    const outletTypes = Object.entries(OUTLET_TYPE_LABELS) as [OutletType, string][];

    return html`
      <sl-details>
        <div slot="summary">
          Outlets
          ${outlets.length > 0 ? html`<sl-badge variant="neutral" pill>${outlets.length}</sl-badge>` : null}
        </div>

        <div class="items-list">
          ${outlets.map((outlet, index) => html`
            <div class="item-card">
              <div class="item-header">
                <span class="item-label">Outlet ${index + 1}</span>
                <sl-icon-button
                  name="x-lg"
                  label="Remove"
                  @click=${() => this.removeOutlet(index)}
                ></sl-icon-button>
              </div>
              <div class="item-fields">
                <sl-select
                  label="Type"
                  size="small"
                  .value=${outlet.type}
                  @sl-change=${(e: Event) => this.updateOutlet(index, { type: (e.target as HTMLSelectElement).value as OutletType })}
                >
                  ${outletTypes.map(([val, label]) => html`
                    <sl-option value=${val}>${label}</sl-option>
                  `)}
                </sl-select>
                <sl-input
                  type="number"
                  label="Height (in)"
                  size="small"
                  .value=${String(outlet.position?.y || 36)}
                  min="0"
                  max="120"
                  @sl-input=${(e: Event) => {
                    const val = parseFloat((e.target as HTMLInputElement).value);
                    if (!isNaN(val)) this.updateOutlet(index, {
                      position: { x: outlet.position?.x || 0, y: val }
                    });
                  }}
                ></sl-input>
              </div>
            </div>
          `)}
        </div>

        <sl-button
          class="add-button"
          variant="default"
          size="small"
          @click=${this.addOutlet}
        >
          <sl-icon slot="prefix" name="plus-lg"></sl-icon>
          Add Outlet
        </sl-button>
      </sl-details>
    `;
  }

  private renderVentilationSection() {
    const ventilation = this.infrastructure?.ventilation || [];
    const patterns = Object.entries(VENTILATION_PATTERN_LABELS) as [VentilationPattern, string][];

    return html`
      <sl-details>
        <div slot="summary">
          Ventilation
          ${ventilation.length > 0 ? html`<sl-badge variant="neutral" pill>${ventilation.length}</sl-badge>` : null}
        </div>

        <div class="items-list">
          ${ventilation.map((vent, index) => html`
            <div class="item-card">
              <div class="item-header">
                <span class="item-label">Vent ${index + 1}</span>
                <sl-icon-button
                  name="x-lg"
                  label="Remove"
                  @click=${() => this.removeVentilation(index)}
                ></sl-icon-button>
              </div>
              <div class="item-fields">
                <sl-select
                  label="Pattern"
                  size="small"
                  .value=${vent.pattern}
                  @sl-change=${(e: Event) => this.updateVentilation(index, { pattern: (e.target as HTMLSelectElement).value as VentilationPattern })}
                >
                  ${patterns.map(([val, label]) => html`
                    <sl-option value=${val}>${label}</sl-option>
                  `)}
                </sl-select>
                <sl-select
                  label="Panel"
                  size="small"
                  .value=${vent.panel || 'back'}
                  @sl-change=${(e: Event) => this.updateVentilation(index, { panel: (e.target as HTMLSelectElement).value })}
                >
                  <sl-option value="back">Back Panel</sl-option>
                  <sl-option value="bottom">Bottom</sl-option>
                  <sl-option value="side">Side Panel</sl-option>
                </sl-select>
                <sl-input
                  type="number"
                  label="Width (in)"
                  size="small"
                  .value=${String(vent.width || 4)}
                  min="1"
                  max="24"
                  step="0.5"
                  @sl-input=${(e: Event) => {
                    const val = parseFloat((e.target as HTMLInputElement).value);
                    if (!isNaN(val)) this.updateVentilation(index, { width: val });
                  }}
                ></sl-input>
                <sl-input
                  type="number"
                  label="Height (in)"
                  size="small"
                  .value=${String(vent.height || 2)}
                  min="0.5"
                  max="12"
                  step="0.5"
                  @sl-input=${(e: Event) => {
                    const val = parseFloat((e.target as HTMLInputElement).value);
                    if (!isNaN(val)) this.updateVentilation(index, { height: val });
                  }}
                ></sl-input>
              </div>
            </div>
          `)}
        </div>

        <sl-button
          class="add-button"
          variant="default"
          size="small"
          @click=${this.addVentilation}
        >
          <sl-icon slot="prefix" name="plus-lg"></sl-icon>
          Add Ventilation
        </sl-button>
      </sl-details>
    `;
  }

  render() {
    return html`
      ${this.renderLightingSection()}
      ${this.renderOutletSection()}
      ${this.renderVentilationSection()}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'infrastructure-editor': InfrastructureEditor;
  }
}
