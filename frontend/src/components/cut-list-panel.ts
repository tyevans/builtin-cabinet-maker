import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import type { CutPiece, CabinetConfig } from '@/api/types';
import { api, type CutLayoutsResponse, type SheetLayout } from '@/api/api';

import '@shoelace-style/shoelace/dist/components/tab-group/tab-group.js';
import '@shoelace-style/shoelace/dist/components/tab/tab.js';
import '@shoelace-style/shoelace/dist/components/tab-panel/tab-panel.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/alert/alert.js';
import '@shoelace-style/shoelace/dist/components/dialog/dialog.js';

@customElement('cut-list-panel')
export class CutListPanel extends LitElement {
  static styles = css`
    /* Mobile-first: reduced padding */
    :host {
      display: block;
      padding: 0.5rem;
    }

    @media (min-width: 768px) {
      :host {
        padding: 1rem;
      }
    }

    .table-container {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      background: var(--sl-color-neutral-0);
      border-radius: var(--sl-border-radius-medium);
      border: 1px solid var(--sl-color-neutral-200);
    }

    /* Mobile-first: smaller font and tighter padding */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.75rem;
    }

    @media (min-width: 768px) {
      table {
        font-size: 0.875rem;
      }
    }

    th {
      text-align: left;
      padding: 0.5rem;
      background: var(--sl-color-neutral-50);
      border-bottom: 2px solid var(--sl-color-neutral-200);
      font-weight: 600;
      color: var(--sl-color-neutral-700);
      white-space: nowrap;
    }

    @media (min-width: 768px) {
      th {
        padding: 0.75rem 1rem;
      }
    }

    td {
      padding: 0.5rem;
      border-bottom: 1px solid var(--sl-color-neutral-100);
      color: var(--sl-color-neutral-800);
    }

    @media (min-width: 768px) {
      td {
        padding: 0.75rem 1rem;
      }
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover td {
      background: var(--sl-color-primary-50);
    }

    .numeric {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    .quantity {
      font-weight: 600;
      color: var(--sl-color-primary-700);
    }

    .material-badge {
      display: inline-block;
      padding: 0.125rem 0.5rem;
      border-radius: var(--sl-border-radius-pill);
      background: var(--sl-color-neutral-100);
      font-size: 0.75rem;
      color: var(--sl-color-neutral-700);
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem;
      text-align: center;
      color: var(--sl-color-neutral-500);
    }

    .empty-state-icon {
      font-size: 2rem;
      margin-bottom: 0.5rem;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }

    .summary-card {
      background: var(--sl-color-neutral-0);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 1rem;
    }

    .summary-label {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .summary-value {
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--sl-color-neutral-900);
      margin-top: 0.25rem;
    }

    /* Cut Layouts Section */
    .cut-layouts-section {
      margin-top: 2rem;
    }

    /* Mobile: sticky button bar at bottom */
    .cut-layouts-header-mobile {
      display: block;
      position: sticky;
      bottom: 0;
      left: 0;
      right: 0;
      background: var(--sl-color-neutral-0);
      border-top: 1px solid var(--sl-color-neutral-200);
      padding: 0.75rem;
      margin: 1rem -0.5rem -0.5rem -0.5rem;
      box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
      z-index: 10;
    }

    .cut-layouts-header-mobile sl-button {
      width: 100%;
    }

    @media (min-width: 768px) {
      .cut-layouts-header-mobile {
        display: none;
      }
    }

    .section-header {
      display: none;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }

    @media (min-width: 768px) {
      .section-header {
        display: flex;
      }
    }

    .section-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--sl-color-neutral-900);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .section-subtitle {
      font-size: 0.875rem;
      color: var(--sl-color-neutral-600);
      margin-top: 0.25rem;
    }

    .sheet-tabs {
      margin-top: 1rem;
    }

    .sheet-info {
      display: flex;
      gap: 1.5rem;
      padding: 0.5rem 0;
      font-size: 0.875rem;
      color: var(--sl-color-neutral-600);
      border-bottom: 1px solid var(--sl-color-neutral-200);
      margin-bottom: 0.5rem;
    }

    .sheet-info span {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .svg-container {
      background: var(--sl-color-neutral-0);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 1rem;
      overflow-x: auto;
    }

    .svg-container svg {
      max-width: 100%;
      height: auto;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      gap: 1rem;
      color: var(--sl-color-neutral-600);
    }

    .waste-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.125rem 0.5rem;
      border-radius: var(--sl-border-radius-pill);
      font-size: 0.75rem;
      font-weight: 500;
    }

    .waste-badge.low {
      background: var(--sl-color-success-100);
      color: var(--sl-color-success-700);
    }

    .waste-badge.medium {
      background: var(--sl-color-warning-100);
      color: var(--sl-color-warning-700);
    }

    .waste-badge.high {
      background: var(--sl-color-danger-100);
      color: var(--sl-color-danger-700);
    }

    .sheets-summary {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      margin-top: 0.5rem;
    }

    .sheets-summary-card {
      background: var(--sl-color-neutral-50);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.75rem 1rem;
      flex: 1;
      min-width: 140px;
    }

    .sheets-summary-label {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .sheets-summary-value {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--sl-color-neutral-900);
      margin-top: 0.125rem;
    }

    sl-tab::part(base) {
      font-size: 0.875rem;
    }

    sl-tab-panel::part(base) {
      padding: 1rem 0;
    }

    /* Mobile gallery view */
    .sheets-gallery {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.75rem;
      margin-top: 1rem;
    }

    @media (min-width: 768px) {
      .sheets-gallery {
        display: none;
      }
    }

    .gallery-item {
      background: var(--sl-color-neutral-0);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.5rem;
      cursor: pointer;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .gallery-item:hover,
    .gallery-item:focus {
      border-color: var(--sl-color-primary-500);
      box-shadow: 0 0 0 1px var(--sl-color-primary-500);
      outline: none;
    }

    .gallery-item:active {
      background: var(--sl-color-primary-50);
    }

    .gallery-thumbnail {
      aspect-ratio: 4 / 3;
      overflow: hidden;
      border-radius: var(--sl-border-radius-small);
      background: var(--sl-color-neutral-50);
      margin-bottom: 0.5rem;
    }

    .gallery-thumbnail svg {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    .gallery-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
    }

    .gallery-label {
      font-weight: 600;
      color: var(--sl-color-neutral-800);
    }

    /* Desktop tabs - hidden on mobile */
    .desktop-tabs {
      display: none;
    }

    @media (min-width: 768px) {
      .desktop-tabs {
        display: block;
      }
    }

    /* Dialog styles */
    .dialog-sheet-info {
      display: flex;
      gap: 1.5rem;
      padding: 0.5rem 0 1rem;
      font-size: 0.875rem;
      color: var(--sl-color-neutral-600);
      border-bottom: 1px solid var(--sl-color-neutral-200);
      margin-bottom: 1rem;
    }

    .dialog-svg-container {
      overflow: auto;
      max-height: 60vh;
      background: var(--sl-color-neutral-50);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.5rem;
    }

    .dialog-svg-container svg {
      width: 100%;
      height: auto;
    }

    sl-dialog::part(panel) {
      width: min(95vw, 600px);
    }
  `;

  @property({ type: Array })
  cutList: CutPiece[] = [];

  @property({ type: Object })
  config: CabinetConfig | null = null;

  @state()
  private cutLayouts: CutLayoutsResponse | null = null;

  @state()
  private isLoadingLayouts = false;

  @state()
  private layoutsError: string | null = null;

  @state()
  private showLayouts = false;

  @state()
  private selectedSheetIndex: number | null = null;

  private formatDimension(value: number): string {
    return value.toFixed(2);
  }

  private getTotalPieces(): number {
    return this.cutList.reduce((sum, piece) => sum + piece.quantity, 0);
  }

  private getTotalArea(): number {
    return this.cutList.reduce((sum, piece) => {
      return sum + (piece.width * piece.height * piece.quantity) / 144;
    }, 0);
  }

  private getWasteBadgeClass(wastePercentage: number): string {
    if (wastePercentage < 20) return 'low';
    if (wastePercentage < 35) return 'medium';
    return 'high';
  }

  private async loadCutLayouts(): Promise<void> {
    if (!this.config || this.isLoadingLayouts) return;

    this.isLoadingLayouts = true;
    this.layoutsError = null;
    this.showLayouts = true;

    try {
      this.cutLayouts = await api.getCutLayouts(this.config);
    } catch (error) {
      this.layoutsError = error instanceof Error ? error.message : 'Failed to load cut layouts';
    } finally {
      this.isLoadingLayouts = false;
    }
  }

  private toggleLayouts(): void {
    if (this.showLayouts) {
      this.showLayouts = false;
    } else {
      if (!this.cutLayouts) {
        this.loadCutLayouts();
      } else {
        this.showLayouts = true;
      }
    }
  }

  private renderCutLayoutsSection() {
    if (!this.config) return null;

    return html`
      <div class="cut-layouts-section">
        <div class="section-header">
          <div>
            <div class="section-title">
              Sheet Cut Layouts
            </div>
            <div class="section-subtitle">
              Optimized placement of pieces on 4'x8' sheets
            </div>
          </div>
          <sl-button
            variant=${this.showLayouts ? 'default' : 'primary'}
            size="small"
            @click=${this.toggleLayouts}
          >
            ${this.showLayouts ? 'Hide Layouts' : 'Show Cut Layouts'}
          </sl-button>
        </div>

        ${this.showLayouts ? this.renderCutLayouts() : null}
      </div>
    `;
  }

  private renderCutLayouts() {
    if (this.isLoadingLayouts) {
      return html`
        <div class="loading-state">
          <sl-spinner style="font-size: 2rem;"></sl-spinner>
          <span>Optimizing cut layouts...</span>
        </div>
      `;
    }

    if (this.layoutsError) {
      return html`
        <sl-alert variant="danger" open>
          <strong>Error loading cut layouts:</strong> ${this.layoutsError}
        </sl-alert>
      `;
    }

    if (!this.cutLayouts || this.cutLayouts.sheets.length === 0) {
      return html`
        <div class="empty-state">
          <span class="empty-state-icon">&#128196;</span>
          <span>No cut layouts available</span>
        </div>
      `;
    }

    const { sheets, total_sheets, total_waste_percentage } = this.cutLayouts;

    return html`
      <div class="sheets-summary">
        <div class="sheets-summary-card">
          <div class="sheets-summary-label">Total Sheets</div>
          <div class="sheets-summary-value">${total_sheets}</div>
        </div>
        <div class="sheets-summary-card">
          <div class="sheets-summary-label">Total Waste</div>
          <div class="sheets-summary-value">
            <span class="waste-badge ${this.getWasteBadgeClass(total_waste_percentage)}">
              ${total_waste_percentage.toFixed(1)}%
            </span>
          </div>
        </div>
        <div class="sheets-summary-card">
          <div class="sheets-summary-label">Sheet Size</div>
          <div class="sheets-summary-value">4' x 8'</div>
        </div>
      </div>

      <!-- Mobile: Gallery view -->
      ${this.renderGallery(sheets)}

      <!-- Desktop: Tabs or single sheet view -->
      <div class="desktop-tabs">
        ${sheets.length === 1
          ? this.renderSingleSheet(sheets[0])
          : this.renderMultipleSheets(sheets)
        }
      </div>

      <!-- Dialog for full-size view -->
      ${this.renderSheetDialog(sheets)}
    `;
  }

  private renderGallery(sheets: SheetLayout[]) {
    return html`
      <div class="sheets-gallery">
        ${sheets.map((sheet, i) => html`
          <button
            class="gallery-item"
            @click=${() => this.openSheetDialog(i)}
            aria-label="View sheet ${i + 1}"
          >
            <div class="gallery-thumbnail">
              ${unsafeHTML(sheet.svg)}
            </div>
            <div class="gallery-info">
              <span class="gallery-label">Sheet ${i + 1}</span>
              <span class="waste-badge ${this.getWasteBadgeClass(sheet.waste_percentage)}">
                ${sheet.waste_percentage.toFixed(0)}%
              </span>
            </div>
          </button>
        `)}
      </div>
    `;
  }

  private openSheetDialog(index: number): void {
    this.selectedSheetIndex = index;
  }

  private closeSheetDialog(): void {
    this.selectedSheetIndex = null;
  }

  private renderSheetDialog(sheets: SheetLayout[]) {
    if (this.selectedSheetIndex === null) return null;

    const sheet = sheets[this.selectedSheetIndex];
    if (!sheet) return null;

    return html`
      <sl-dialog
        label="Sheet ${this.selectedSheetIndex + 1} of ${sheets.length}"
        ?open=${this.selectedSheetIndex !== null}
        @sl-hide=${this.closeSheetDialog}
      >
        <div class="dialog-sheet-info">
          <span><strong>Pieces:</strong> ${sheet.piece_count}</span>
          <span>
            <strong>Waste:</strong>
            <span class="waste-badge ${this.getWasteBadgeClass(sheet.waste_percentage)}">
              ${sheet.waste_percentage.toFixed(1)}%
            </span>
          </span>
        </div>
        <div class="dialog-svg-container">
          ${unsafeHTML(sheet.svg)}
        </div>
      </sl-dialog>
    `;
  }

  private renderSingleSheet(sheet: SheetLayout) {
    return html`
      <div class="sheet-info">
        <span><strong>Pieces:</strong> ${sheet.piece_count}</span>
        <span>
          <strong>Waste:</strong>
          <span class="waste-badge ${this.getWasteBadgeClass(sheet.waste_percentage)}">
            ${sheet.waste_percentage.toFixed(1)}%
          </span>
        </span>
      </div>
      <div class="svg-container">
        ${unsafeHTML(sheet.svg)}
      </div>
    `;
  }

  private renderMultipleSheets(sheets: SheetLayout[]) {
    return html`
      <sl-tab-group>
        ${sheets.map((sheet, i) => html`
          <sl-tab slot="nav" panel="sheet-${i}">
            Sheet ${i + 1}
            <span class="waste-badge ${this.getWasteBadgeClass(sheet.waste_percentage)}">
              ${sheet.waste_percentage.toFixed(0)}%
            </span>
          </sl-tab>
        `)}

        ${sheets.map((sheet, i) => html`
          <sl-tab-panel name="sheet-${i}">
            <div class="sheet-info">
              <span><strong>Pieces:</strong> ${sheet.piece_count}</span>
              <span>
                <strong>Waste:</strong>
                <span class="waste-badge ${this.getWasteBadgeClass(sheet.waste_percentage)}">
                  ${sheet.waste_percentage.toFixed(1)}%
                </span>
              </span>
            </div>
            <div class="svg-container">
              ${unsafeHTML(sheet.svg)}
            </div>
          </sl-tab-panel>
        `)}
      </sl-tab-group>
    `;
  }

  render() {
    if (this.cutList.length === 0) {
      return html`
        <div class="empty-state">
          <span class="empty-state-icon">&#128220;</span>
          <span>No cut list available</span>
          <small>Configure cabinet dimensions to generate a cut list</small>
        </div>
      `;
    }

    const totalPieces = this.getTotalPieces();
    const totalArea = this.getTotalArea();

    return html`
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Part</th>
              <th class="numeric">Qty</th>
              <th class="numeric">Width</th>
              <th class="numeric">Height</th>
              <th class="numeric">Thickness</th>
              <th>Material</th>
            </tr>
          </thead>
          <tbody>
            ${this.cutList.map(piece => html`
              <tr>
                <td>${piece.label}</td>
                <td class="numeric quantity">${piece.quantity}</td>
                <td class="numeric">${this.formatDimension(piece.width)}"</td>
                <td class="numeric">${this.formatDimension(piece.height)}"</td>
                <td class="numeric">${piece.thickness}"</td>
                <td>
                  <span class="material-badge">${piece.material_type}</span>
                </td>
              </tr>
            `)}
          </tbody>
        </table>
      </div>

      <div class="summary">
        <div class="summary-card">
          <div class="summary-label">Total Pieces</div>
          <div class="summary-value">${totalPieces}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Total Area</div>
          <div class="summary-value">${totalArea.toFixed(1)} sq ft</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Unique Parts</div>
          <div class="summary-value">${this.cutList.length}</div>
        </div>
      </div>

      ${this.renderCutLayoutsSection()}

      <!-- Mobile sticky button -->
      ${this.config ? html`
        <div class="cut-layouts-header-mobile">
          <sl-button
            variant=${this.showLayouts ? 'default' : 'primary'}
            @click=${this.toggleLayouts}
          >
            ${this.showLayouts ? 'Hide Cut Layouts' : 'Show Cut Layouts'}
          </sl-button>
        </div>
      ` : null}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cut-list-panel': CutListPanel;
  }
}
