import { LitElement, html, css } from 'lit';
import { customElement, state, query } from 'lit/decorators.js';
import { importConfig } from '@/state/cabinet-state';
import type { CabinetConfig } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/alert/alert.js';

@customElement('config-import')
export class ConfigImport extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .import-container {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .file-input {
      display: none;
    }

    sl-alert {
      margin-top: 0.5rem;
    }

    .success-message {
      color: var(--sl-color-success-700);
      font-size: 0.875rem;
    }
  `;

  @state()
  private importError: string | null = null;

  @state()
  private importSuccess: boolean = false;

  @query('input[type="file"]')
  private fileInput!: HTMLInputElement;

  private handleButtonClick(): void {
    this.fileInput.click();
  }

  private async handleFileSelect(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.importError = null;
    this.importSuccess = false;

    try {
      const text = await file.text();
      const config = JSON.parse(text) as CabinetConfig;

      // Basic validation
      if (!config.schema_version) {
        throw new Error('Missing schema_version in config file');
      }

      if (!config.cabinet) {
        throw new Error('Missing cabinet configuration');
      }

      if (typeof config.cabinet.width !== 'number' ||
          typeof config.cabinet.height !== 'number' ||
          typeof config.cabinet.depth !== 'number') {
        throw new Error('Invalid cabinet dimensions');
      }

      // Import the config
      importConfig(config);
      this.importSuccess = true;

      // Clear success message after 3 seconds
      setTimeout(() => {
        this.importSuccess = false;
      }, 3000);

    } catch (error) {
      if (error instanceof SyntaxError) {
        this.importError = 'Invalid JSON file format';
      } else if (error instanceof Error) {
        this.importError = error.message;
      } else {
        this.importError = 'Failed to import configuration';
      }
    }

    // Reset file input
    input.value = '';
  }

  render() {
    return html`
      <div class="import-container">
        <sl-button
          variant="default"
          size="small"
          @click=${this.handleButtonClick}
        >
          <sl-icon slot="prefix" name="upload"></sl-icon>
          Import JSON
        </sl-button>

        <input
          type="file"
          class="file-input"
          accept=".json,application/json"
          @change=${this.handleFileSelect}
        />

        ${this.importError ? html`
          <sl-alert variant="danger" open closable @sl-after-hide=${() => this.importError = null}>
            <sl-icon slot="icon" name="exclamation-octagon"></sl-icon>
            ${this.importError}
          </sl-alert>
        ` : null}

        ${this.importSuccess ? html`
          <span class="success-message">Configuration imported successfully</span>
        ` : null}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'config-import': ConfigImport;
  }
}
