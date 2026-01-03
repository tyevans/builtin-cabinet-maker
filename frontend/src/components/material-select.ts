import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, setMaterial, setBackMaterial } from '@/state/cabinet-state';
import { MATERIAL_TYPE_LABELS, COMMON_THICKNESSES, type MaterialSpec, type MaterialType } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/divider/divider.js';

@customElement('material-select')
export class MaterialSelect extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .material-section {
      margin-bottom: 1rem;
    }

    .material-section:last-child {
      margin-bottom: 0;
    }

    .section-label {
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--sl-color-neutral-700);
      margin-bottom: 0.5rem;
      display: block;
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }

    sl-select::part(form-control-label) {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-select::part(combobox) {
      font-size: 0.875rem;
    }

    sl-divider {
      --spacing: 0.75rem;
    }
  `;

  @state()
  private material: MaterialSpec = {
    type: 'plywood',
    thickness: 0.75,
  };

  @state()
  private backMaterial: MaterialSpec = {
    type: 'plywood',
    thickness: 0.25,
  };

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      if (state.config.cabinet.material) {
        this.material = state.config.cabinet.material;
      }
      if (state.config.cabinet.back_material) {
        this.backMaterial = state.config.cabinet.back_material;
      }
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private handleTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    setMaterial({ ...this.material, type: target.value as MaterialType });
  }

  private handleThicknessChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const thickness = parseFloat(target.value);
    if (!isNaN(thickness)) {
      setMaterial({ ...this.material, thickness });
    }
  }

  private handleBackTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    setBackMaterial({ ...this.backMaterial, type: target.value as MaterialType });
  }

  private handleBackThicknessChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const thickness = parseFloat(target.value);
    if (!isNaN(thickness)) {
      setBackMaterial({ ...this.backMaterial, thickness });
    }
  }

  render() {
    const materialTypes = Object.entries(MATERIAL_TYPE_LABELS) as [MaterialType, string][];

    return html`
      <!-- Main Material -->
      <div class="material-section">
        <span class="section-label">Main Panels</span>
        <div class="form-grid">
          <sl-select
            label="Type"
            .value=${this.material.type}
            @sl-change=${this.handleTypeChange}
          >
            ${materialTypes.map(([value, label]) => html`
              <sl-option value=${value}>${label}</sl-option>
            `)}
          </sl-select>

          <sl-select
            label="Thickness"
            .value=${String(this.material.thickness)}
            @sl-change=${this.handleThicknessChange}
          >
            ${COMMON_THICKNESSES.map(({ value, label }) => html`
              <sl-option value=${String(value)}>${label}</sl-option>
            `)}
          </sl-select>
        </div>
      </div>

      <sl-divider></sl-divider>

      <!-- Back Panel Material -->
      <div class="material-section">
        <span class="section-label">Back Panel</span>
        <div class="form-grid">
          <sl-select
            label="Type"
            .value=${this.backMaterial.type}
            @sl-change=${this.handleBackTypeChange}
          >
            ${materialTypes.map(([value, label]) => html`
              <sl-option value=${value}>${label}</sl-option>
            `)}
          </sl-select>

          <sl-select
            label="Thickness"
            .value=${String(this.backMaterial.thickness)}
            @sl-change=${this.handleBackThicknessChange}
          >
            ${COMMON_THICKNESSES.map(({ value, label }) => html`
              <sl-option value=${String(value)}>${label}</sl-option>
            `)}
          </sl-select>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'material-select': MaterialSelect;
  }
}
