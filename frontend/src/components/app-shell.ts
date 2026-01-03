import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState, setLayout, setGenerating, setError } from '@/state/cabinet-state';
import { api } from '@/api/api';
import { debounce } from '@/state/store';

import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import './error-banner.js';

@customElement('app-shell')
export class AppShell extends LitElement {
  static styles = css`
    :host {
      display: grid;
      grid-template-columns: 440px 1fr;
      grid-template-rows: auto 1fr;
      height: 100vh;
      overflow: hidden;
      background: var(--sl-color-neutral-100);
    }

    .header {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1.5rem;
      background: var(--sl-color-neutral-0);
      border-bottom: 1px solid var(--sl-color-neutral-200);
      box-shadow: var(--sl-shadow-x-small);
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--sl-color-neutral-900);
    }

    .logo-icon {
      font-size: 1.5rem;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .sidebar {
      overflow-y: auto;
      background: var(--sl-color-neutral-0);
      border-right: 1px solid var(--sl-color-neutral-200);
    }

    .main {
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.25rem 0.75rem;
      border-radius: var(--sl-border-radius-pill);
      font-size: 0.875rem;
    }

    .status-badge.generating {
      background: var(--sl-color-primary-100);
      color: var(--sl-color-primary-700);
    }

    .status-badge.ready {
      background: var(--sl-color-success-100);
      color: var(--sl-color-success-700);
    }

    .status-badge.error {
      background: var(--sl-color-danger-100);
      color: var(--sl-color-danger-700);
    }

    .main-content {
      display: flex;
      flex-direction: column;
      overflow: hidden;
      height: 100%;
    }

    .preview-area {
      flex: 1;
      overflow: hidden;
    }
  `;

  @state()
  private cabinetState: CabinetState = cabinetStore.getState();

  private unsubscribe?: () => void;
  private debouncedGenerate: () => void;

  constructor() {
    super();
    this.debouncedGenerate = debounce(() => this.generateLayout(), 500);
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      const shouldRegenerate = this.cabinetState.isDirty !== state.isDirty && state.isDirty;
      this.cabinetState = state;
      if (shouldRegenerate) {
        this.debouncedGenerate();
      }
    });

    // Generate initial layout
    this.generateLayout();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private async generateLayout(): Promise<void> {
    // Clear any previous error before attempting - allows recovery from temporary invalid states
    setGenerating(true);
    cabinetStore.setState({ lastError: null });
    try {
      const layout = await api.generateLayout(this.cabinetState.config);
      setLayout(layout);
    } catch (error) {
      // Store the error for display - helps users understand what went wrong
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.warn('Layout generation failed:', errorMessage);
      setError(errorMessage);
    }
  }

  private getStatusBadge() {
    if (this.cabinetState.isGenerating) {
      return html`<span class="status-badge generating">Generating...</span>`;
    }
    if (this.cabinetState.lastError) {
      return html`<span class="status-badge error">Error</span>`;
    }
    if (this.cabinetState.layout?.is_valid) {
      return html`<span class="status-badge ready">Ready</span>`;
    }
    return null;
  }

  render() {
    return html`
      <header class="header">
        <div class="logo">
          <span class="logo-icon">&#128452;</span>
          Cabinet Designer
        </div>
        <div class="header-actions">
          ${this.getStatusBadge()}
          <export-menu></export-menu>
        </div>
      </header>

      <aside class="sidebar">
        <config-sidebar></config-sidebar>
      </aside>

      <main class="main">
        <div class="main-content">
          ${this.cabinetState.lastError
            ? html`<error-banner .error=${this.cabinetState.lastError}></error-banner>`
            : null}
          <div class="preview-area">
            <preview-panel></preview-panel>
          </div>
        </div>
      </main>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'app-shell': AppShell;
  }
}
