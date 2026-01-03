import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { marked } from 'marked';
import { cabinetStore, type CabinetState } from '@/state/cabinet-state';
import { api } from '@/api/api';

import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';

@customElement('assembly-panel')
export class AssemblyPanel extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 1rem;
      height: 100%;
      overflow: auto;
    }

    .markdown-content {
      background: var(--sl-color-neutral-0);
      border-radius: var(--sl-border-radius-medium);
      border: 1px solid var(--sl-color-neutral-200);
      padding: 1.5rem 2rem;
      font-size: 0.9rem;
      line-height: 1.6;
      color: var(--sl-color-neutral-800);
    }

    .markdown-content h1 {
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--sl-color-neutral-900);
      margin: 0 0 1rem 0;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--sl-color-primary-500);
    }

    .markdown-content h2 {
      font-size: 1.35rem;
      font-weight: 600;
      color: var(--sl-color-neutral-900);
      margin: 1.5rem 0 0.75rem 0;
    }

    .markdown-content h3 {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--sl-color-neutral-800);
      margin: 1.25rem 0 0.5rem 0;
    }

    .markdown-content h4 {
      font-size: 1rem;
      font-weight: 600;
      color: var(--sl-color-neutral-700);
      margin: 1rem 0 0.5rem 0;
    }

    .markdown-content p {
      margin: 0.5rem 0;
    }

    .markdown-content ul,
    .markdown-content ol {
      margin: 0.5rem 0;
      padding-left: 1.5rem;
    }

    .markdown-content li {
      margin: 0.25rem 0;
    }

    .markdown-content strong {
      font-weight: 600;
      color: var(--sl-color-neutral-900);
    }

    .markdown-content em {
      font-style: italic;
    }

    .markdown-content code {
      background: var(--sl-color-neutral-100);
      padding: 0.125rem 0.375rem;
      border-radius: var(--sl-border-radius-small);
      font-family: var(--sl-font-mono);
      font-size: 0.85em;
    }

    .markdown-content blockquote {
      margin: 1rem 0;
      padding: 0.75rem 1rem;
      border-left: 4px solid var(--sl-color-warning-500);
      background: var(--sl-color-warning-50);
      color: var(--sl-color-warning-800);
    }

    .markdown-content hr {
      border: none;
      border-top: 1px solid var(--sl-color-neutral-200);
      margin: 1.5rem 0;
    }

    .markdown-content table {
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
    }

    .markdown-content th,
    .markdown-content td {
      padding: 0.5rem 0.75rem;
      border: 1px solid var(--sl-color-neutral-200);
      text-align: left;
    }

    .markdown-content th {
      background: var(--sl-color-neutral-50);
      font-weight: 600;
    }

    .loading-state,
    .empty-state,
    .error-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem;
      text-align: center;
      color: var(--sl-color-neutral-500);
    }

    .loading-state sl-spinner {
      font-size: 2rem;
      margin-bottom: 1rem;
    }

    .empty-state-icon,
    .error-state-icon {
      font-size: 2rem;
      margin-bottom: 0.5rem;
    }

    .error-state {
      color: var(--sl-color-danger-600);
    }

    .retry-button {
      margin-top: 1rem;
    }
  `;

  @state()
  private markdown: string = '';

  @state()
  private isLoading: boolean = false;

  @state()
  private error: string | null = null;

  @state()
  private cabinetState: CabinetState = cabinetStore.getState();

  private unsubscribe?: () => void;
  private lastConfigJson: string = '';

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      const newConfigJson = JSON.stringify(state.config);
      const configChanged = newConfigJson !== this.lastConfigJson;
      this.cabinetState = state;

      // Reload assembly instructions when config changes and we have a layout
      if (configChanged && state.layout && !state.isGenerating) {
        this.lastConfigJson = newConfigJson;
        this.loadAssemblyInstructions();
      }
    });

    // Initial load if we already have a layout
    if (this.cabinetState.layout) {
      this.lastConfigJson = JSON.stringify(this.cabinetState.config);
      this.loadAssemblyInstructions();
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private async loadAssemblyInstructions(): Promise<void> {
    this.isLoading = true;
    this.error = null;

    try {
      const markdown = await api.getAssemblyInstructions(this.cabinetState.config);
      this.markdown = markdown;
    } catch (err) {
      this.error = err instanceof Error ? err.message : 'Failed to load assembly instructions';
    } finally {
      this.isLoading = false;
    }
  }

  private renderMarkdown(): string {
    return marked(this.markdown) as string;
  }

  render() {
    if (!this.cabinetState.layout) {
      return html`
        <div class="empty-state">
          <span class="empty-state-icon">&#128221;</span>
          <span>No assembly instructions available</span>
          <small>Configure cabinet dimensions to generate instructions</small>
        </div>
      `;
    }

    if (this.isLoading) {
      return html`
        <div class="loading-state">
          <sl-spinner></sl-spinner>
          <span>Generating assembly instructions...</span>
        </div>
      `;
    }

    if (this.error) {
      return html`
        <div class="error-state">
          <span class="error-state-icon">&#9888;</span>
          <span>${this.error}</span>
          <sl-button
            class="retry-button"
            variant="primary"
            size="small"
            @click=${this.loadAssemblyInstructions}
          >
            Retry
          </sl-button>
        </div>
      `;
    }

    return html`
      <div class="markdown-content" .innerHTML=${this.renderMarkdown()}></div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'assembly-panel': AssemblyPanel;
  }
}
