import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState } from '@/state/cabinet-state';

import '@shoelace-style/shoelace/dist/components/tab-group/tab-group.js';
import '@shoelace-style/shoelace/dist/components/tab/tab.js';
import '@shoelace-style/shoelace/dist/components/tab-panel/tab-panel.js';

import './assembly-panel.js';
import './bom-panel.js';

@customElement('preview-panel')
export class PreviewPanel extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--sl-color-neutral-50);
    }

    .tab-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    sl-tab-group {
      height: 100%;
    }

    sl-tab-group::part(base) {
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    sl-tab-group::part(body) {
      flex: 1;
      overflow: hidden;
    }

    sl-tab-group::part(nav) {
      background: var(--sl-color-neutral-0);
      border-bottom: 1px solid var(--sl-color-neutral-200);
      padding: 0 1rem;
    }

    sl-tab-panel {
      height: 100%;
      padding: 0;
    }

    sl-tab-panel::part(base) {
      height: 100%;
      padding: 0;
    }

    .panel-content {
      height: 100%;
      overflow: auto;
    }

    .error-message {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      padding: 2rem;
      text-align: center;
      color: var(--sl-color-danger-600);
    }

    .error-message h3 {
      margin: 0 0 0.5rem 0;
    }

    .error-message p {
      margin: 0;
      color: var(--sl-color-neutral-600);
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

  render() {
    const { layout, lastError } = this.cabinetState;

    if (lastError) {
      return html`
        <div class="error-message">
          <h3>Error</h3>
          <p>${lastError}</p>
        </div>
      `;
    }

    return html`
      <div class="tab-container">
        <sl-tab-group>
          <sl-tab slot="nav" panel="3d-view">3D Preview</sl-tab>
          <sl-tab slot="nav" panel="cut-list">Cut List</sl-tab>
          <sl-tab slot="nav" panel="bom">BOM</sl-tab>
          <sl-tab slot="nav" panel="assembly">Assembly</sl-tab>

          <sl-tab-panel name="3d-view">
            <div class="panel-content">
              <stl-viewer></stl-viewer>
            </div>
          </sl-tab-panel>

          <sl-tab-panel name="cut-list">
            <div class="panel-content">
              <cut-list-panel
                .cutList=${layout?.cut_list || []}
                .config=${this.cabinetState.config}
              ></cut-list-panel>
            </div>
          </sl-tab-panel>

          <sl-tab-panel name="bom">
            <div class="panel-content">
              <bom-panel></bom-panel>
            </div>
          </sl-tab-panel>

          <sl-tab-panel name="assembly">
            <div class="panel-content">
              <assembly-panel></assembly-panel>
            </div>
          </sl-tab-panel>
        </sl-tab-group>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'preview-panel': PreviewPanel;
  }
}
