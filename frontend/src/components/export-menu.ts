import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState } from '@/state/cabinet-state';
import { api } from '@/api/api';
import type { ExportFormat } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/dropdown/dropdown.js';
import '@shoelace-style/shoelace/dist/components/menu/menu.js';
import '@shoelace-style/shoelace/dist/components/menu-item/menu-item.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/divider/divider.js';

interface ExportOption {
  format: ExportFormat;
  label: string;
  description: string;
  icon: string;
}

const EXPORT_OPTIONS: ExportOption[] = [
  {
    format: 'stl',
    label: '3D Model (STL)',
    description: 'For 3D printing or CAD software',
    icon: 'box',
  },
  {
    format: 'json',
    label: 'Project Data (JSON)',
    description: 'Full project configuration and layout',
    icon: 'file-earmark-code',
  },
  {
    format: 'assembly',
    label: 'Assembly Instructions',
    description: 'Step-by-step build guide (Markdown)',
    icon: 'list-check',
  },
  {
    format: 'bom',
    label: 'Bill of Materials',
    description: 'Cut list and materials (CSV)',
    icon: 'table',
  },
];

@customElement('export-menu')
export class ExportMenu extends LitElement {
  static styles = css`
    :host {
      display: inline-block;
    }

    sl-menu-item::part(base) {
      padding: 0.75rem 1rem;
    }

    .menu-item-content {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    .menu-item-label {
      font-weight: 500;
    }

    .menu-item-description {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-500);
    }

    sl-button::part(label) {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .exporting {
      opacity: 0.7;
      pointer-events: none;
    }
  `;

  @state()
  private cabinetState: CabinetState = cabinetStore.getState();

  @state()
  private isExporting = false;

  @state()
  private exportingFormat: ExportFormat | null = null;

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

  private async handleExport(format: ExportFormat): Promise<void> {
    if (this.isExporting) return;

    this.isExporting = true;
    this.exportingFormat = format;

    try {
      await api.downloadExport(format, this.cabinetState.config);
    } catch (error) {
      console.error(`Export failed:`, error);
    } finally {
      this.isExporting = false;
      this.exportingFormat = null;
    }
  }

  render() {
    const isDisabled = !this.cabinetState.layout?.is_valid;

    return html`
      <sl-dropdown>
        <sl-button
          slot="trigger"
          variant="primary"
          ?disabled=${isDisabled}
          class=${this.isExporting ? 'exporting' : ''}
        >
          <sl-icon name="download"></sl-icon>
          ${this.isExporting ? 'Exporting...' : 'Export'}
          <sl-icon name="chevron-down"></sl-icon>
        </sl-button>

        <sl-menu @sl-select=${(e: CustomEvent) => this.handleExport(e.detail.item.value)}>
          ${EXPORT_OPTIONS.map(option => html`
            <sl-menu-item
              value=${option.format}
              ?disabled=${this.exportingFormat === option.format}
            >
              <sl-icon slot="prefix" name=${option.icon}></sl-icon>
              <div class="menu-item-content">
                <span class="menu-item-label">${option.label}</span>
                <span class="menu-item-description">${option.description}</span>
              </div>
            </sl-menu-item>
          `)}
        </sl-menu>
      </sl-dropdown>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'export-menu': ExportMenu;
  }
}
