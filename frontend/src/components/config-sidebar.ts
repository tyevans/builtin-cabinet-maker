import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  cabinetStore,
  type CabinetState,
  resetConfig,
} from '@/state/cabinet-state';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/details/details.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';

@customElement('config-sidebar')
export class ConfigSidebar extends LitElement {
  static styles = css`
    /* Mobile-first: reduced padding */
    :host {
      display: block;
      padding: 0.75rem;
      overflow-y: auto;
    }

    /* Desktop: more padding */
    @media (min-width: 768px) {
      :host {
        padding: 1rem;
      }
    }

    .summary {
      background: var(--sl-color-neutral-50);
      border-radius: var(--sl-border-radius-medium);
      padding: 1rem;
      margin-bottom: 1rem;
    }

    .summary-row {
      display: flex;
      justify-content: space-between;
      padding: 0.25rem 0;
      font-size: 0.875rem;
    }

    .summary-label {
      color: var(--sl-color-neutral-600);
    }

    .summary-value {
      font-weight: 500;
      color: var(--sl-color-neutral-900);
    }

    .accordion {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    sl-details {
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
    }

    sl-details::part(base) {
      border: none;
    }

    sl-details::part(header) {
      padding: 0.75rem 1rem;
      font-weight: 500;
      font-size: 0.875rem;
    }

    sl-details::part(content) {
      padding: 0 1rem 1rem;
    }

    sl-details[open] {
      border-color: var(--sl-color-primary-300);
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .section-header sl-badge {
      font-size: 0.7rem;
    }

    .footer {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid var(--sl-color-neutral-200);
    }

    .footer-buttons {
      display: flex;
      gap: 0.5rem;
    }

    .io-buttons {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
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

  private handleReset(): void {
    resetConfig();
  }

  private getDecorativeCount(): number {
    const { cabinet } = this.cabinetState.config;
    let count = 0;
    if (cabinet.face_frame?.enabled) count++;
    if (cabinet.crown_molding?.enabled) count++;
    if (cabinet.base_zone?.enabled) count++;
    if (cabinet.light_rail?.enabled) count++;
    return count;
  }

  render() {
    const { config, layout } = this.cabinetState;
    const { width, height, depth } = config.cabinet;
    const sections = config.cabinet.sections || [];
    const totalShelves = sections.reduce((sum, s) => {
      // For composite sections, count shelves from rows
      if (s.rows && s.rows.length > 0) {
        return sum + s.rows.reduce((rowSum, r) => rowSum + (r.shelves ?? 0), 0);
      }
      return sum + (s.shelves ?? 0);
    }, 0);
    const obstacleCount = config.obstacles?.length || 0;
    const wallCount = config.room?.walls?.length || 0;
    const decorativeCount = this.getDecorativeCount();

    return html`
      <!-- Summary Card -->
      <div class="summary">
        <div class="summary-row">
          <span class="summary-label">Dimensions</span>
          <span class="summary-value">${width}" x ${height}" x ${depth}"</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Sections</span>
          <span class="summary-value">${sections.length}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">Total Shelves</span>
          <span class="summary-value">${totalShelves}</span>
        </div>
        ${layout?.total_estimate ? html`
          <div class="summary-row">
            <span class="summary-label">Sheet Estimate</span>
            <span class="summary-value">${layout.total_estimate.sheet_count} sheets</span>
          </div>
        ` : null}
      </div>

      <!-- Accordion Sections -->
      <div class="accordion">
        <!-- Cabinet Dimensions -->
        <sl-details summary="Cabinet Dimensions" open>
          <dimensions-form></dimensions-form>
        </sl-details>

        <!-- Materials -->
        <sl-details summary="Materials" open>
          <material-select></material-select>
        </sl-details>

        <!-- Sections -->
        <section-tree-editor></section-tree-editor>

        <!-- Room & Obstacles -->
        <sl-details>
          <div slot="summary" class="section-header">
            <span>Room & Obstacles</span>
            ${wallCount > 0 || obstacleCount > 0 ? html`
              <sl-badge variant="neutral" pill>${wallCount + obstacleCount}</sl-badge>
            ` : null}
          </div>
          <room-editor></room-editor>
          <obstacle-editor></obstacle-editor>
        </sl-details>

        <!-- Decorative Elements -->
        <sl-details>
          <div slot="summary" class="section-header">
            <span>Decorative Elements</span>
            ${decorativeCount > 0 ? html`
              <sl-badge variant="neutral" pill>${decorativeCount}</sl-badge>
            ` : null}
          </div>
          <decorative-editor></decorative-editor>
        </sl-details>

        <!-- Infrastructure -->
        <sl-details>
          <div slot="summary" class="section-header">
            <span>Infrastructure</span>
          </div>
          <infrastructure-editor></infrastructure-editor>
        </sl-details>

        <!-- Installation -->
        <sl-details>
          <div slot="summary" class="section-header">
            <span>Installation</span>
          </div>
          <installation-editor></installation-editor>
        </sl-details>

        <!-- Import/Export -->
        <sl-details summary="Import / Export">
          <div class="io-buttons">
            <config-import></config-import>
            <config-export></config-export>
          </div>
        </sl-details>
      </div>

      <!-- Footer -->
      <div class="footer">
        <sl-button
          variant="text"
          size="small"
          @click=${this.handleReset}
        >
          <sl-icon slot="prefix" name="arrow-counterclockwise"></sl-icon>
          Reset to Defaults
        </sl-button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'config-sidebar': ConfigSidebar;
  }
}
