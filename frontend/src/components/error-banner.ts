import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

import '@shoelace-style/shoelace/dist/components/alert/alert.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';

/**
 * Error banner component for displaying generation errors prominently.
 *
 * Parses API error responses and displays them in a user-friendly format.
 */
@customElement('error-banner')
export class ErrorBanner extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .error-alert {
      margin: 1rem;
    }

    .error-alert::part(base) {
      background: var(--sl-color-danger-50);
      border-color: var(--sl-color-danger-400);
    }

    .error-alert::part(icon) {
      color: var(--sl-color-danger-600);
    }

    .error-content {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .error-title {
      font-weight: 600;
      color: var(--sl-color-danger-700);
      font-size: 0.95rem;
    }

    .error-details {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .error-message {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      padding: 0.5rem 0.75rem;
      background: var(--sl-color-danger-100);
      border-radius: var(--sl-border-radius-medium);
      font-size: 0.9rem;
      color: var(--sl-color-danger-800);
      line-height: 1.4;
    }

    .error-message sl-icon {
      flex-shrink: 0;
      margin-top: 0.1rem;
    }

    .hidden {
      display: none;
    }
  `;

  @property({ type: String })
  error: string | null = null;

  /**
   * Parse the error string/message to extract detailed messages.
   * Handles both simple strings and JSON error structures.
   */
  private parseError(): { title: string; messages: string[] } {
    if (!this.error) {
      return { title: '', messages: [] };
    }

    // Try to parse as JSON first (API errors often come as JSON strings)
    try {
      const parsed = JSON.parse(this.error);

      // Handle structured API error: {"error":"...", "details":[{"message":"..."}]}
      if (parsed.error && Array.isArray(parsed.details)) {
        const title = parsed.error;
        const messages = parsed.details
          .map((d: { message?: string }) => d.message)
          .filter((m: string | undefined): m is string => !!m);
        return { title, messages: messages.length ? messages : [title] };
      }

      // Handle simple error object: {"error":"..."}
      if (parsed.error) {
        return { title: 'Generation Error', messages: [parsed.error] };
      }

      // Handle detail field (FastAPI validation errors)
      if (parsed.detail) {
        if (typeof parsed.detail === 'string') {
          return { title: 'Error', messages: [parsed.detail] };
        }
        if (parsed.detail.error) {
          return { title: 'Error', messages: [parsed.detail.error] };
        }
      }
    } catch {
      // Not JSON, treat as plain string
    }

    // Plain string error
    return { title: 'Generation Error', messages: [this.error] };
  }

  render() {
    if (!this.error) {
      return null;
    }

    const { title, messages } = this.parseError();

    return html`
      <sl-alert variant="danger" open class="error-alert">
        <sl-icon slot="icon" name="exclamation-octagon"></sl-icon>
        <div class="error-content">
          <div class="error-title">${title}</div>
          <div class="error-details">
            ${messages.map(
              msg => html`
                <div class="error-message">
                  <sl-icon name="x-circle"></sl-icon>
                  <span>${msg}</span>
                </div>
              `
            )}
          </div>
        </div>
      </sl-alert>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'error-banner': ErrorBanner;
  }
}
