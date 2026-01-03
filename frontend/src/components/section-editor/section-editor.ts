import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, addSection, removeSection, updateSection } from '@/state/cabinet-state';
import { type SectionSpec } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';

import './section-card.js';

@customElement('section-editor')
export class SectionEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .sections-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .add-button {
      margin-top: 0.75rem;
    }

    .add-button::part(base) {
      width: 100%;
      border-style: dashed;
    }

    .empty-state {
      text-align: center;
      padding: 2rem;
      background: var(--sl-color-neutral-50);
      border: 2px dashed var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      color: var(--sl-color-neutral-500);
    }

    .empty-state p {
      margin: 0.5rem 0;
    }
  `;

  @state()
  private sections: SectionSpec[] = [];

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      this.sections = state.config.cabinet.sections || [];
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  private handleAddSection(): void {
    addSection();
  }

  private handleRemoveSection(index: number): void {
    removeSection(index);
  }

  private handleSectionUpdate(index: number, updates: Partial<SectionSpec>): void {
    updateSection(index, updates);
  }

  render() {
    const canRemove = this.sections.length > 1;

    return html`
      ${this.sections.length === 0 ? html`
        <div class="empty-state">
          <sl-icon name="columns-gap" style="font-size: 2rem;"></sl-icon>
          <p>No sections configured</p>
          <p>Add sections to divide your cabinet horizontally</p>
        </div>
      ` : html`
        <div class="sections-list">
          ${this.sections.map((section, index) => html`
            <section-card
              .section=${section}
              .index=${index}
              .canRemove=${canRemove}
              @section-update=${(e: CustomEvent) => this.handleSectionUpdate(index, e.detail)}
              @section-remove=${() => this.handleRemoveSection(index)}
            ></section-card>
          `)}
        </div>
      `}

      <sl-button
        class="add-button"
        variant="default"
        size="small"
        @click=${this.handleAddSection}
      >
        <sl-icon slot="prefix" name="plus-lg"></sl-icon>
        Add Section
      </sl-button>
    `;
  }
}

// Re-export for backwards compatibility
declare global {
  interface HTMLElementTagNameMap {
    'section-editor': SectionEditor;
  }
}
