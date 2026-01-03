import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  isCompositeSection,
  type SectionSpec,
  type SectionSelection,
  type WallSegmentSpec,
} from '@/api/types';
import {
  cabinetStore,
  addSection,
  addSectionRow,
  removeSection,
  removeSectionRow,
  reorderSections,
  reorderSectionRows,
} from '@/state/cabinet-state';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/dropdown/dropdown.js';
import '@shoelace-style/shoelace/dist/components/menu/menu.js';
import '@shoelace-style/shoelace/dist/components/menu-item/menu-item.js';

import './tree-node.js';
import type { TreeNodeData } from './tree-node.js';

@customElement('section-tree')
export class SectionTree extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .tree-container {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    .add-button {
      margin-top: 0.5rem;
    }

    .add-button::part(base) {
      width: 100%;
      border-style: dashed;
    }

    .empty-state {
      text-align: center;
      padding: 1.5rem;
      background: var(--sl-color-neutral-50);
      border: 2px dashed var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      color: var(--sl-color-neutral-500);
      font-size: 0.875rem;
    }

    .empty-state sl-icon {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }
  `;

  @property({ type: Array })
  sections: SectionSpec[] = [];

  @property({ type: Object })
  selectedSection: SectionSelection | null = null;

  @state()
  private expandedSections: Set<number> = new Set();

  @state()
  private walls: WallSegmentSpec[] = [];

  private unsubscribe?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    // Subscribe to store to get walls
    this.unsubscribe = cabinetStore.subscribe(state => {
      this.walls = state.config.room?.walls || [];
    });
    // Initially expand all sections to show their content
    this.sections.forEach((_, index) => {
      this.expandedSections.add(index);
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
  }

  updated(changedProperties: Map<string, unknown>): void {
    super.updated(changedProperties);
    // Auto-expand any new sections that were added
    if (changedProperties.has('sections')) {
      this.sections.forEach((_, index) => {
        if (!this.expandedSections.has(index)) {
          const newExpanded = new Set(this.expandedSections);
          newExpanded.add(index);
          this.expandedSections = newExpanded;
        }
      });
    }
  }

  private isSelected(sectionIndex: number, rowIndex?: number): boolean {
    if (!this.selectedSection) return false;
    if (this.selectedSection.sectionIndex !== sectionIndex) return false;

    const section = this.sections[sectionIndex];
    const isSimpleSection = section && !isCompositeSection(section);

    if (rowIndex === undefined) {
      // Selecting the section header
      return this.selectedSection.rowIndex === undefined;
    }

    // For simple sections, the synthetic row is selected when the section is selected
    if (isSimpleSection && rowIndex === 0) {
      return this.selectedSection.rowIndex === undefined;
    }

    return this.selectedSection.rowIndex === rowIndex;
  }

  private handleNodeSelect(e: CustomEvent<TreeNodeData>): void {
    const { sectionIndex, rowIndex, type } = e.detail;
    const section = this.sections[sectionIndex];
    const isSimpleSection = section && !isCompositeSection(section);

    // For simple sections, clicking on the synthetic row should edit the section itself
    // since the row is just a visual representation of the section's content
    if (type === 'row' && isSimpleSection) {
      this.dispatchEvent(new CustomEvent('selection-change', {
        detail: { sectionIndex }, // No rowIndex - edits the section
        bubbles: true,
        composed: true,
      }));
    } else {
      this.dispatchEvent(new CustomEvent('selection-change', {
        detail: { sectionIndex, rowIndex },
        bubbles: true,
        composed: true,
      }));
    }
  }

  private handleNodeToggle(e: CustomEvent<TreeNodeData>): void {
    const { sectionIndex } = e.detail;
    const newExpanded = new Set(this.expandedSections);
    if (newExpanded.has(sectionIndex)) {
      newExpanded.delete(sectionIndex);
    } else {
      newExpanded.add(sectionIndex);
    }
    this.expandedSections = newExpanded;
  }

  private handleNodeDrop(e: CustomEvent<{ from: TreeNodeData; to: TreeNodeData }>): void {
    const { from, to } = e.detail;

    // Same type reordering
    if (from.type === 'section' && to.type === 'section') {
      // Reorder sections
      reorderSections(from.sectionIndex, to.sectionIndex);
    } else if (
      from.type === 'row' &&
      to.type === 'row' &&
      from.sectionIndex === to.sectionIndex &&
      from.rowIndex !== undefined &&
      to.rowIndex !== undefined
    ) {
      // Reorder rows within same section
      reorderSectionRows(from.sectionIndex, from.rowIndex, to.rowIndex);
    }
    // Cross-section row moves not supported for simplicity
  }

  private handleAddRow(e: CustomEvent<TreeNodeData>): void {
    const { sectionIndex } = e.detail;
    addSectionRow(sectionIndex);
    // Auto-expand the section when adding a row
    const newExpanded = new Set(this.expandedSections);
    newExpanded.add(sectionIndex);
    this.expandedSections = newExpanded;
  }

  private handleDeleteNode(e: CustomEvent<TreeNodeData>): void {
    const { type, sectionIndex, rowIndex } = e.detail;
    const section = this.sections[sectionIndex];
    const isSimpleSection = section && !isCompositeSection(section);

    if (type === 'row' && rowIndex !== undefined) {
      // For simple sections, deleting the synthetic row deletes the section
      if (isSimpleSection) {
        if (this.sections.length > 1) {
          removeSection(sectionIndex);
          this.dispatchEvent(new CustomEvent('selection-change', {
            detail: null,
            bubbles: true,
            composed: true,
          }));
        }
      } else {
        // For composite sections, removeSectionRow handles:
        // - 2+ rows remaining: just removes the row
        // - 1 row remaining: converts to simple section
        // - 0 rows remaining: deletes section and clears selection
        removeSectionRow(sectionIndex, rowIndex);
        // Clear selection - it will be invalid if section was deleted or converted
        this.dispatchEvent(new CustomEvent('selection-change', {
          detail: null,
          bubbles: true,
          composed: true,
        }));
      }
    } else if (type === 'section') {
      // Only allow delete if more than one section
      if (this.sections.length > 1) {
        removeSection(sectionIndex);
        this.dispatchEvent(new CustomEvent('selection-change', {
          detail: null,
          bubbles: true,
          composed: true,
        }));
      }
    }
  }

  private handleAddSection(wall?: number): void {
    addSection(wall);
  }

  private handleAddSectionToWall(e: CustomEvent): void {
    const item = e.detail.item as HTMLElement;
    const wallIndex = item.dataset.wall;
    if (wallIndex !== undefined) {
      addSection(parseInt(wallIndex, 10));
    } else {
      addSection();
    }
  }

  private renderSection(section: SectionSpec, index: number) {
    const isComposite = isCompositeSection(section);
    const isExpanded = this.expandedSections.has(index);

    // For simple sections, create a synthetic row from the section's content
    // This makes all sections display uniformly as expandable with child rows
    const rows = isComposite
      ? (section.rows || [])
      : [{
          height: 'fill' as const,
          section_type: section.section_type || 'open',
          shelves: section.shelves,
          component_config: section.component_config,
        }];

    return html`
      <tree-node
        .data=${{ type: 'section', sectionIndex: index, section }}
        .selected=${this.isSelected(index)}
        .expanded=${isExpanded}
        .showExpand=${true}
        @node-select=${this.handleNodeSelect}
        @node-toggle=${this.handleNodeToggle}
        @node-drop=${this.handleNodeDrop}
        @add-row=${this.handleAddRow}
        @delete-node=${this.handleDeleteNode}
      ></tree-node>

      ${isExpanded ? html`
        ${[...rows].reverse().map((row, reversedIdx) => {
          const rowIndex = rows.length - 1 - reversedIdx;
          return html`
            <tree-node
              .data=${{ type: 'row', sectionIndex: index, rowIndex, row }}
              .selected=${this.isSelected(index, rowIndex)}
              .indent=${1}
              @node-select=${this.handleNodeSelect}
              @node-drop=${this.handleNodeDrop}
              @delete-node=${this.handleDeleteNode}
            ></tree-node>
          `;
        })}
      ` : null}
    `;
  }

  private renderAddSectionButton() {
    // If multiple walls exist, show a dropdown
    if (this.walls.length > 1) {
      return html`
        <sl-dropdown>
          <sl-button
            slot="trigger"
            class="add-button"
            variant="default"
            size="small"
            caret
          >
            <sl-icon slot="prefix" name="plus-lg"></sl-icon>
            Add Section
          </sl-button>
          <sl-menu @sl-select=${this.handleAddSectionToWall}>
            ${this.walls.map((wall, index) => html`
              <sl-menu-item data-wall=${index}>
                Wall ${index + 1}${wall.name ? ` - ${wall.name}` : ''}
              </sl-menu-item>
            `)}
          </sl-menu>
        </sl-dropdown>
      `;
    }

    // Single wall or no walls - simple button
    return html`
      <sl-button
        class="add-button"
        variant="default"
        size="small"
        @click=${() => this.handleAddSection(this.walls.length === 1 ? 0 : undefined)}
      >
        <sl-icon slot="prefix" name="plus-lg"></sl-icon>
        Add Section
      </sl-button>
    `;
  }

  render() {
    if (this.sections.length === 0) {
      return html`
        <div class="empty-state">
          <sl-icon name="columns-gap"></sl-icon>
          <p>No sections configured</p>
        </div>
        ${this.renderAddSectionButton()}
      `;
    }

    return html`
      <div class="tree-container">
        ${this.sections.map((section, index) => this.renderSection(section, index))}
      </div>
      ${this.renderAddSectionButton()}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'section-tree': SectionTree;
  }
}
