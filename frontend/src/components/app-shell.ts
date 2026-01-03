import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState, setLayout, setGenerating, setError } from '@/state/cabinet-state';
import { api } from '@/api/api';
import { debounce } from '@/state/store';

import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/drawer/drawer.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import './error-banner.js';

@customElement('app-shell')
export class AppShell extends LitElement {
  static styles = css`
    /* Mobile-first: single column layout */
    :host {
      display: grid;
      grid-template-columns: 1fr;
      grid-template-rows: auto 1fr;
      height: 100vh;
      overflow: hidden;
      background: var(--sl-color-neutral-100);
    }

    /* Desktop: two-column layout */
    @media (min-width: 768px) {
      :host {
        grid-template-columns: 440px 1fr;
      }
    }

    .header {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.5rem 1rem;
      background: var(--sl-color-neutral-0);
      border-bottom: 1px solid var(--sl-color-neutral-200);
      box-shadow: var(--sl-shadow-x-small);
    }

    @media (min-width: 768px) {
      .header {
        padding: 0.75rem 1.5rem;
      }
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .mobile-menu-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      font-size: 1.5rem;
      background: transparent;
      border: none;
      border-radius: var(--sl-border-radius-medium);
      color: var(--sl-color-neutral-700);
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }

    .mobile-menu-btn:hover,
    .mobile-menu-btn:focus {
      background: var(--sl-color-neutral-100);
      color: var(--sl-color-primary-600);
      outline: none;
    }

    .mobile-menu-btn:active {
      background: var(--sl-color-neutral-200);
    }

    @media (min-width: 768px) {
      .mobile-menu-btn {
        display: none;
      }
    }

    .logo {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--sl-color-neutral-900);
    }

    @media (min-width: 768px) {
      .logo {
        gap: 0.75rem;
        font-size: 1.25rem;
      }
    }

    .logo-icon {
      font-size: 1.25rem;
    }

    @media (min-width: 768px) {
      .logo-icon {
        font-size: 1.5rem;
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    @media (min-width: 768px) {
      .header-actions {
        gap: 0.75rem;
      }
    }

    /* Desktop sidebar - hidden on mobile */
    .sidebar {
      display: none;
      overflow-y: auto;
      background: var(--sl-color-neutral-0);
      border-right: 1px solid var(--sl-color-neutral-200);
    }

    @media (min-width: 768px) {
      .sidebar {
        display: block;
      }
    }

    .main {
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .status-badge {
      display: none;
      align-items: center;
      gap: 0.5rem;
      padding: 0.25rem 0.75rem;
      border-radius: var(--sl-border-radius-pill);
      font-size: 0.75rem;
    }

    @media (min-width: 768px) {
      .status-badge {
        display: flex;
        font-size: 0.875rem;
      }
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

    /* Drawer styling for mobile */
    sl-drawer::part(panel) {
      width: min(400px, 85vw);
    }

    sl-drawer::part(body) {
      padding: 0;
    }
  `;

  @state()
  private cabinetState: CabinetState = cabinetStore.getState();

  @state()
  private drawerOpen = false;

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

  private openDrawer(): void {
    this.drawerOpen = true;
  }

  private handleDrawerHide(e: Event): void {
    // Only close if the event is from the drawer itself, not from nested sl-details
    const target = e.target as HTMLElement;
    if (target.tagName === 'SL-DRAWER') {
      this.drawerOpen = false;
    }
  }

  render() {
    return html`
      <header class="header">
        <div class="header-left">
          <button
            class="mobile-menu-btn"
            aria-label="Open configuration"
            @click=${this.openDrawer}
          >&#9776;</button>
          <div class="logo">
            <span class="logo-icon">&#128452;</span>
            Cabinet Designer
          </div>
        </div>
        <div class="header-actions">
          ${this.getStatusBadge()}
          <export-menu></export-menu>
        </div>
      </header>

      <!-- Desktop sidebar -->
      <aside class="sidebar">
        <config-sidebar></config-sidebar>
      </aside>

      <!-- Mobile drawer -->
      <sl-drawer
        label="Configuration"
        ?open=${this.drawerOpen}
        @sl-hide=${this.handleDrawerHide}
      >
        <config-sidebar></config-sidebar>
      </sl-drawer>

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
