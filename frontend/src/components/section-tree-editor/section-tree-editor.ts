import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import type { SectionSpec, SectionSelection } from '@/api/types';
import {
  cabinetStore,
  setSelectedSection,
  clearSelectedSection,
} from '@/state/cabinet-state';

import '@shoelace-style/shoelace/dist/components/details/details.js';
import '@shoelace-style/shoelace/dist/components/badge/badge.js';

import './section-tree.js';
import './section-properties.js';

@customElement('section-tree-editor')
export class SectionTreeEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    sl-details {
      margin-bottom: 0.5rem;
    }

    sl-details::part(base) {
      border: none;
      background: transparent;
    }

    sl-details::part(header) {
      padding: 0.5rem 0;
      font-weight: 500;
    }

    sl-details::part(content) {
      padding: 0.5rem 0;
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .section-header sl-badge {
      font-size: 0.7rem;
    }
  `;

  @state()
  private sections: SectionSpec[] = [];

  @state()
  private selectedSection: SectionSelection | null = null;

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      this.sections = state.config.cabinet.sections || [];
      this.selectedSection = state.selectedSection;
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private handleSelectionChange(e: CustomEvent<SectionSelection>): void {
    setSelectedSection(e.detail);
  }

  private handleClearSelection(): void {
    clearSelectedSection();
  }

  private getSelectedLabel(): string {
    if (!this.selectedSection) return 'None';
    const { sectionIndex, rowIndex } = this.selectedSection;
    if (rowIndex !== undefined) {
      return `Section ${sectionIndex + 1}, Row ${rowIndex + 1}`;
    }
    return `Section ${sectionIndex + 1}`;
  }

  render() {
    return html`
      <sl-details open>
        <div slot="summary" class="section-header">
          <span>Structure</span>
          <sl-badge variant="neutral" pill>${this.sections.length}</sl-badge>
        </div>
        <section-tree
          .sections=${this.sections}
          .selectedSection=${this.selectedSection}
          @selection-change=${this.handleSelectionChange}
        ></section-tree>
      </sl-details>

      <sl-details ?open=${this.selectedSection !== null}>
        <div slot="summary" class="section-header">
          <span>Properties</span>
          ${this.selectedSection ? html`
            <sl-badge variant="primary" pill>${this.getSelectedLabel()}</sl-badge>
          ` : null}
        </div>
        <section-properties
          .sections=${this.sections}
          .selectedSection=${this.selectedSection}
          @selection-change=${this.handleSelectionChange}
          @clear-selection=${this.handleClearSelection}
        ></section-properties>
      </sl-details>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'section-tree-editor': SectionTreeEditor;
  }
}
