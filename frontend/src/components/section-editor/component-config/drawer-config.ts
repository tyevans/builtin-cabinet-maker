import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import {
  SLIDE_TYPE_LABELS,
  FRONT_STYLE_LABELS,
  type DrawerComponentConfig,
  type SlideType,
  type FrontStyle,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/switch/switch.js';

@customElement('drawer-config')
export class DrawerConfig extends LitElement {
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
  config!: DrawerComponentConfig;

  private dispatchUpdate(updates: Partial<DrawerComponentConfig>): void {
    this.dispatchEvent(new CustomEvent('config-update', {
      detail: updates,
      bubbles: true,
      composed: true,
    }));
  }

  private handleCountChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const count = parseInt(target.value, 10);
    if (!isNaN(count) && count >= 1 && count <= 8) {
      this.dispatchUpdate({ count });
    }
  }

  private handleFrontHeightChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const front_height = parseFloat(target.value);
    if (!isNaN(front_height) && front_height > 0) {
      this.dispatchUpdate({ front_height });
    }
  }

  private handleSlideTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.dispatchUpdate({ slide_type: target.value as SlideType });
  }

  private handleSlideLengthChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const slide_length = parseFloat(target.value);
    if (!isNaN(slide_length) && slide_length > 0) {
      this.dispatchUpdate({ slide_length });
    }
  }

  private handleSoftCloseChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.dispatchUpdate({ soft_close: target.checked });
  }

  private handleFrontStyleChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.dispatchUpdate({ front_style: target.value as FrontStyle });
  }

  render() {
    const slideTypes = Object.entries(SLIDE_TYPE_LABELS) as [SlideType, string][];
    const frontStyles = Object.entries(FRONT_STYLE_LABELS) as [FrontStyle, string][];

    return html`
      <div class="config-grid">
        <sl-input
          type="number"
          label="Drawer Count"
          .value=${String(this.config.count)}
          min="1"
          max="8"
          @sl-input=${this.handleCountChange}
        ></sl-input>

        <sl-input
          type="number"
          label="Front Height (in)"
          .value=${String(this.config.front_height)}
          min="3"
          max="12"
          step="0.5"
          @sl-input=${this.handleFrontHeightChange}
        ></sl-input>

        <sl-select
          label="Slide Type"
          .value=${this.config.slide_type}
          @sl-change=${this.handleSlideTypeChange}
        >
          ${slideTypes.map(([value, label]) => html`
            <sl-option value=${value}>${label}</sl-option>
          `)}
        </sl-select>

        <sl-input
          type="number"
          label="Slide Length (in)"
          .value=${String(this.config.slide_length)}
          min="12"
          max="24"
          step="1"
          @sl-input=${this.handleSlideLengthChange}
        ></sl-input>

        <sl-select
          label="Front Style"
          .value=${this.config.front_style}
          @sl-change=${this.handleFrontStyleChange}
          class="full-width"
        >
          ${frontStyles.map(([value, label]) => html`
            <sl-option value=${value}>${label}</sl-option>
          `)}
        </sl-select>

        <div class="switch-row">
          <span class="switch-label">Soft-close slides</span>
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
    'drawer-config': DrawerConfig;
  }
}
