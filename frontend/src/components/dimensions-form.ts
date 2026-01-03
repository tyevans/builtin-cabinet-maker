import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, setDimensions } from '@/state/cabinet-state';
import type { Dimensions } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/input/input.js';

@customElement('dimensions-form')
export class DimensionsForm extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.75rem;
    }

    sl-input::part(form-control-label) {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input) {
      font-size: 0.875rem;
    }
  `;

  @state()
  private dimensions: Dimensions = {
    width: 48,
    height: 84,
    depth: 12,
  };

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      const { width, height, depth } = state.config.cabinet;
      this.dimensions = { width, height, depth };
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private handleInput(field: keyof Dimensions, event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = parseFloat(target.value);
    if (!isNaN(value) && value > 0) {
      setDimensions({ ...this.dimensions, [field]: value });
    }
  }

  render() {
    return html`
      <div class="form-grid">
        <sl-input
          type="number"
          label="Width (in)"
          .value=${String(this.dimensions.width)}
          min="6"
          max="240"
          step="0.25"
          @sl-input=${(e: Event) => this.handleInput('width', e)}
        ></sl-input>

        <sl-input
          type="number"
          label="Height (in)"
          .value=${String(this.dimensions.height)}
          min="6"
          max="120"
          step="0.25"
          @sl-input=${(e: Event) => this.handleInput('height', e)}
        ></sl-input>

        <sl-input
          type="number"
          label="Depth (in)"
          .value=${String(this.dimensions.depth)}
          min="6"
          max="36"
          step="0.25"
          @sl-input=${(e: Event) => this.handleInput('depth', e)}
        ></sl-input>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'dimensions-form': DimensionsForm;
  }
}
