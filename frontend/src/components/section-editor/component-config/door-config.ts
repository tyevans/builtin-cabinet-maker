import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import {
  HINGE_SIDE_LABELS,
  HANDLE_POSITION_LABELS,
  type DoorComponentConfig,
  type HingeSide,
  type HandlePosition,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/switch/switch.js';

@customElement('door-config')
export class DoorConfig extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .config-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    .switch-row {
      grid-column: 1 / -1;
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
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input),
    sl-select::part(combobox) {
      font-size: 0.875rem;
    }
  `;

  @property({ type: Object })
  config!: DoorComponentConfig;

  private dispatchUpdate(updates: Partial<DoorComponentConfig>): void {
    this.dispatchEvent(new CustomEvent('config-update', {
      detail: updates,
      bubbles: true,
      composed: true,
    }));
  }

  private handleCountChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const count = parseInt(target.value, 10);
    if (!isNaN(count) && (count === 1 || count === 2)) {
      this.dispatchUpdate({ count: count as 1 | 2 });
    }
  }

  private handleHingeSideChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.dispatchUpdate({ hinge_side: target.value as HingeSide });
  }

  private handleRevealChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const reveal = parseFloat(target.value);
    if (!isNaN(reveal) && reveal >= 0) {
      this.dispatchUpdate({ reveal });
    }
  }

  private handleOverlayChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const overlay = parseFloat(target.value);
    if (!isNaN(overlay) && overlay >= 0) {
      this.dispatchUpdate({ overlay });
    }
  }

  private handleSoftCloseChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.dispatchUpdate({ soft_close: target.checked });
  }

  private handleHandlePositionChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.dispatchUpdate({ handle_position: target.value as HandlePosition });
  }

  render() {
    const hingeSides = Object.entries(HINGE_SIDE_LABELS) as [HingeSide, string][];
    const handlePositions = Object.entries(HANDLE_POSITION_LABELS) as [HandlePosition, string][];

    return html`
      <div class="config-grid">
        <sl-input
          type="number"
          label="Door Count"
          .value=${String(this.config.count)}
          min="1"
          max="2"
          @sl-input=${this.handleCountChange}
        ></sl-input>

        <sl-select
          label="Hinge Side"
          .value=${this.config.hinge_side}
          @sl-change=${this.handleHingeSideChange}
        >
          ${hingeSides.map(([value, label]) => html`
            <sl-option value=${value}>${label}</sl-option>
          `)}
        </sl-select>

        <sl-input
          type="number"
          label="Reveal (in)"
          .value=${String(this.config.reveal)}
          min="0"
          max="0.5"
          step="0.0625"
          @sl-input=${this.handleRevealChange}
        ></sl-input>

        <sl-input
          type="number"
          label="Overlay (in)"
          .value=${String(this.config.overlay)}
          min="0"
          max="1"
          step="0.125"
          @sl-input=${this.handleOverlayChange}
        ></sl-input>

        <sl-select
          label="Handle Position"
          .value=${this.config.handle_position}
          @sl-change=${this.handleHandlePositionChange}
          class="full-width"
        >
          ${handlePositions.map(([value, label]) => html`
            <sl-option value=${value}>${label}</sl-option>
          `)}
        </sl-select>

        <div class="switch-row">
          <span class="switch-label">Soft-close hinges</span>
          <sl-switch
            ?checked=${this.config.soft_close}
            @sl-change=${this.handleSoftCloseChange}
          ></sl-switch>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'door-config': DoorConfig;
  }
}
