import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState } from '@/state/cabinet-state';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';

@customElement('config-export')
export class ConfigExport extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
  `;

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

  private handleExport(): void {
    const config = this.cabinetState.config;

    // Create a clean copy without undefined values
    const cleanConfig = JSON.parse(JSON.stringify(config));

    const blob = new Blob([JSON.stringify(cleanConfig, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'cabinet-config.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    URL.revokeObjectURL(url);
  }

  render() {
    return html`
      <sl-button
        variant="default"
        size="small"
        @click=${this.handleExport}
      >
        <sl-icon slot="prefix" name="download"></sl-icon>
        Export JSON
      </sl-button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'config-export': ConfigExport;
  }
}
