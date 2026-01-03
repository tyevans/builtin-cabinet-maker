import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { type CubbyComponentConfig } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/switch/switch.js';

@customElement('cubby-config')
export class CubbyConfig extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .config-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    .switch-row {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.5rem 0;
    }

    .switch-label {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    .dimensions-section {
      grid-column: 1 / -1;
      margin-top: 0.5rem;
      padding: 0.5rem;
      background: var(--sl-color-neutral-100);
      border-radius: var(--sl-border-radius-small);
    }

    .dimensions-label {
      font-size: 0.7rem;
      color: var(--sl-color-neutral-600);
      margin-bottom: 0.5rem;
      font-weight: 500;
    }

    .dimensions-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.25rem;
    }

    .dimensions-input {
      font-size: 0.75rem;
    }

    sl-input::part(form-control-label) {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input) {
      font-size: 0.875rem;
    }
  `;

  @property({ type: Object })
  config!: CubbyComponentConfig;

  private dispatchUpdate(updates: Partial<CubbyComponentConfig>): void {
    this.dispatchEvent(new CustomEvent('config-update', {
      detail: updates,
      bubbles: true,
      composed: true,
    }));
  }

  private handleRowsChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const rows = parseInt(target.value, 10);
    if (!isNaN(rows) && rows >= 1 && rows <= 8) {
      // Update row_heights to match new row count
      const currentHeights = this.config.row_heights || [];
      let row_heights: number[] | undefined;
      if (currentHeights.length > 0) {
        if (rows > currentHeights.length) {
          // Add equal heights for new rows
          const avgHeight = currentHeights.reduce((a, b) => a + b, 0) / currentHeights.length;
          row_heights = [...currentHeights, ...Array(rows - currentHeights.length).fill(avgHeight)];
        } else {
          row_heights = currentHeights.slice(0, rows);
        }
      }
      this.dispatchUpdate({ rows, row_heights });
    }
  }

  private handleColumnsChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const columns = parseInt(target.value, 10);
    if (!isNaN(columns) && columns >= 1 && columns <= 8) {
      // Update column_widths to match new column count
      const currentWidths = this.config.column_widths || [];
      let column_widths: number[] | undefined;
      if (currentWidths.length > 0) {
        if (columns > currentWidths.length) {
          const avgWidth = currentWidths.reduce((a, b) => a + b, 0) / currentWidths.length;
          column_widths = [...currentWidths, ...Array(columns - currentWidths.length).fill(avgWidth)];
        } else {
          column_widths = currentWidths.slice(0, columns);
        }
      }
      this.dispatchUpdate({ columns, column_widths });
    }
  }

  private handleEdgeBandChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.dispatchUpdate({ edge_band_front: target.checked });
  }

  private handleRowHeightChange(index: number, event: Event): void {
    const target = event.target as HTMLInputElement;
    const height = parseFloat(target.value);
    if (!isNaN(height) && height > 0) {
      const row_heights = [...(this.config.row_heights || Array(this.config.rows).fill(6))];
      row_heights[index] = height;
      this.dispatchUpdate({ row_heights });
    }
  }

  private handleColumnWidthChange(index: number, event: Event): void {
    const target = event.target as HTMLInputElement;
    const width = parseFloat(target.value);
    if (!isNaN(width) && width > 0) {
      const column_widths = [...(this.config.column_widths || Array(this.config.columns).fill(6))];
      column_widths[index] = width;
      this.dispatchUpdate({ column_widths });
    }
  }

  private renderVariableDimensions() {
    const hasVariableRows = this.config.row_heights && this.config.row_heights.length > 0;
    const hasVariableCols = this.config.column_widths && this.config.column_widths.length > 0;

    if (!hasVariableRows && !hasVariableCols) {
      return null;
    }

    return html`
      <div class="dimensions-section">
        ${hasVariableRows ? html`
          <div class="dimensions-label">Row Heights (in)</div>
          <div class="dimensions-grid">
            ${(this.config.row_heights || []).map((height, i) => html`
              <sl-input
                type="number"
                size="small"
                placeholder="Row ${i + 1}"
                .value=${String(height)}
                min="2"
                max="24"
                step="0.5"
                @sl-input=${(e: Event) => this.handleRowHeightChange(i, e)}
              ></sl-input>
            `)}
          </div>
        ` : null}

        ${hasVariableCols ? html`
          <div class="dimensions-label" style="${hasVariableRows ? 'margin-top: 0.5rem;' : ''}">Column Widths (in)</div>
          <div class="dimensions-grid">
            ${(this.config.column_widths || []).map((width, i) => html`
              <sl-input
                type="number"
                size="small"
                placeholder="Col ${i + 1}"
                .value=${String(width)}
                min="3"
                max="24"
                step="0.5"
                @sl-input=${(e: Event) => this.handleColumnWidthChange(i, e)}
              ></sl-input>
            `)}
          </div>
        ` : null}
      </div>
    `;
  }

  render() {
    return html`
      <div class="config-grid">
        <sl-input
          type="number"
          label="Rows"
          .value=${String(this.config.rows)}
          min="1"
          max="8"
          @sl-input=${this.handleRowsChange}
        ></sl-input>

        <sl-input
          type="number"
          label="Columns"
          .value=${String(this.config.columns)}
          min="1"
          max="8"
          @sl-input=${this.handleColumnsChange}
        ></sl-input>

        <div class="switch-row">
          <span class="switch-label">Edge band front openings</span>
          <sl-switch
            ?checked=${this.config.edge_band_front}
            @sl-change=${this.handleEdgeBandChange}
          ></sl-switch>
        </div>

        ${this.renderVariableDimensions()}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'cubby-config': CubbyConfig;
  }
}
