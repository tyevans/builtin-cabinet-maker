import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import {
  SECTION_TYPE_LABELS,
  isCompositeSection,
  type SectionSpec,
  type SectionRowSpec,
  type SectionType,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/tooltip/tooltip.js';

export type TreeNodeType = 'section' | 'row';

export interface TreeNodeData {
  type: TreeNodeType;
  sectionIndex: number;
  rowIndex?: number;
  section?: SectionSpec;
  row?: SectionRowSpec;
}

@customElement('tree-node')
export class TreeNode extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .tree-node {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.375rem 0.5rem;
      cursor: pointer;
      border-radius: var(--sl-border-radius-small);
      user-select: none;
      transition: background-color 0.1s ease;
    }

    .tree-node:hover {
      background: var(--sl-color-neutral-100);
    }

    .tree-node.selected {
      background: var(--sl-color-primary-100);
    }

    .tree-node.drag-over {
      border-top: 2px solid var(--sl-color-primary-500);
    }

    .tree-node.dragging {
      opacity: 0.5;
    }

    .indent {
      width: 1rem;
      flex-shrink: 0;
    }

    .expand-icon {
      width: 1rem;
      height: 1rem;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      color: var(--sl-color-neutral-500);
      transition: transform 0.15s ease;
    }

    .expand-icon.expanded {
      transform: rotate(90deg);
    }

    .expand-icon.hidden {
      visibility: hidden;
    }

    .type-icon {
      width: 1rem;
      height: 1rem;
      flex-shrink: 0;
    }

    .type-icon.open { color: var(--sl-color-neutral-500); }
    .type-icon.doored { color: var(--sl-color-blue-500); }
    .type-icon.drawers { color: var(--sl-color-green-500); }
    .type-icon.cubby { color: var(--sl-color-purple-500); }
    .type-icon.composite { color: var(--sl-color-amber-500); }

    .node-label {
      flex: 1;
      font-size: 0.8rem;
      color: var(--sl-color-neutral-700);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .node-badge {
      font-size: 0.65rem;
      padding: 0.1rem 0.3rem;
      border-radius: var(--sl-border-radius-small);
      background: var(--sl-color-neutral-200);
      color: var(--sl-color-neutral-600);
    }

    .node-badge.open { background: var(--sl-color-neutral-100); }
    .node-badge.doored { background: var(--sl-color-blue-100); color: var(--sl-color-blue-700); }
    .node-badge.drawers { background: var(--sl-color-green-100); color: var(--sl-color-green-700); }
    .node-badge.cubby { background: var(--sl-color-purple-100); color: var(--sl-color-purple-700); }

    .drag-handle {
      cursor: grab;
      color: var(--sl-color-neutral-400);
      transition: opacity 0.1s ease;
    }

    .drag-handle:active {
      cursor: grabbing;
    }

    .inline-actions {
      display: flex;
      align-items: center;
      gap: 0.125rem;
      transition: opacity 0.1s ease;
    }

    /* Desktop: dim actions until hover */
    @media (hover: hover) and (pointer: fine) {
      .drag-handle {
        opacity: 0.5;
      }

      .tree-node:hover .drag-handle {
        opacity: 1;
      }

      .inline-actions {
        opacity: 0.5;
      }

      .tree-node:hover .inline-actions {
        opacity: 1;
      }
    }

    .inline-actions sl-icon-button::part(base) {
      padding: 0.125rem;
      font-size: 0.75rem;
    }

    .inline-actions sl-icon-button.add-row::part(base) {
      color: var(--sl-color-success-600);
    }

    .inline-actions sl-icon-button.add-row::part(base):hover {
      color: var(--sl-color-success-700);
      background: var(--sl-color-success-100);
    }

    .inline-actions sl-icon-button.delete::part(base) {
      color: var(--sl-color-neutral-400);
    }

    .inline-actions sl-icon-button.delete::part(base):hover {
      color: var(--sl-color-danger-600);
      background: var(--sl-color-danger-100);
    }
  `;

  @property({ type: Object })
  data!: TreeNodeData;

  @property({ type: Boolean })
  selected = false;

  @property({ type: Boolean })
  expanded = true;

  @property({ type: Number })
  indent = 0;

  @property({ type: Boolean, attribute: 'show-expand' })
  showExpand = false;

  private getTypeIcon(type: SectionType | 'composite'): string {
    switch (type) {
      case 'doored': return 'door-closed';
      case 'drawers': return 'stack';
      case 'cubby': return 'grid-3x3';
      case 'composite': return 'layers';
      default: return 'bookshelf';
    }
  }

  private getSectionLabel(): string {
    const { section, sectionIndex } = this.data;
    if (!section) return `Section ${sectionIndex + 1}`;

    const width = section.width === 'fill' ? 'fill' : `${section.width}"`;
    return `Section ${sectionIndex + 1} (${width})`;
  }

  private getRowLabel(): string {
    const { row, rowIndex } = this.data;
    if (!row || rowIndex === undefined) return 'Row';

    const height = row.height === 'fill' ? 'fill' : `${row.height}"`;
    return `${SECTION_TYPE_LABELS[row.section_type]} (${height})`;
  }

  private getSectionType(): SectionType | 'composite' {
    const { type, section, row } = this.data;

    if (type === 'row' && row) {
      return row.section_type;
    }

    if (section) {
      if (isCompositeSection(section)) {
        return 'composite';
      }
      return section.section_type || 'open';
    }

    return 'open';
  }

  private handleClick(e: MouseEvent): void {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent('node-select', {
      detail: this.data,
      bubbles: true,
      composed: true,
    }));
  }

  private handleExpandClick(e: MouseEvent): void {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent('node-toggle', {
      detail: this.data,
      bubbles: true,
      composed: true,
    }));
  }

  private handleAddRow(e: MouseEvent): void {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent('add-row', {
      detail: this.data,
      bubbles: true,
      composed: true,
    }));
  }

  private handleDelete(e: MouseEvent): void {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent('delete-node', {
      detail: this.data,
      bubbles: true,
      composed: true,
    }));
  }

  private handleDragStart(e: DragEvent): void {
    if (!e.dataTransfer) return;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/json', JSON.stringify(this.data));
    this.classList.add('dragging');

    this.dispatchEvent(new CustomEvent('node-drag-start', {
      detail: this.data,
      bubbles: true,
      composed: true,
    }));
  }

  private handleDragEnd(): void {
    this.classList.remove('dragging');
    this.dispatchEvent(new CustomEvent('node-drag-end', {
      bubbles: true,
      composed: true,
    }));
  }

  private handleDragOver(e: DragEvent): void {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'move';
    }
    this.classList.add('drag-over');
  }

  private handleDragLeave(): void {
    this.classList.remove('drag-over');
  }

  private handleDrop(e: DragEvent): void {
    e.preventDefault();
    this.classList.remove('drag-over');

    if (!e.dataTransfer) return;
    const dataStr = e.dataTransfer.getData('application/json');
    if (!dataStr) return;

    try {
      const draggedData = JSON.parse(dataStr) as TreeNodeData;
      this.dispatchEvent(new CustomEvent('node-drop', {
        detail: { from: draggedData, to: this.data },
        bubbles: true,
        composed: true,
      }));
    } catch {
      // Invalid JSON, ignore
    }
  }

  render() {
    const { type } = this.data;
    const label = type === 'section' ? this.getSectionLabel() : this.getRowLabel();
    const nodeType = this.getSectionType();
    const isRow = type === 'row';

    return html`
      <div
        class="tree-node ${this.selected ? 'selected' : ''}"
        draggable="true"
        @click=${this.handleClick}
        @dragstart=${this.handleDragStart}
        @dragend=${this.handleDragEnd}
        @dragover=${this.handleDragOver}
        @dragleave=${this.handleDragLeave}
        @drop=${this.handleDrop}
      >
        ${Array(this.indent).fill(null).map(() => html`<span class="indent"></span>`)}

        <span
          class="expand-icon ${this.expanded ? 'expanded' : ''} ${!this.showExpand ? 'hidden' : ''}"
          @click=${this.handleExpandClick}
        >
          <sl-icon name="chevron-right"></sl-icon>
        </span>

        <sl-icon
          class="type-icon ${nodeType}"
          name=${this.getTypeIcon(nodeType)}
        ></sl-icon>

        <span class="node-label">${label}</span>

        ${isRow && nodeType !== 'composite' ? html`
          <span class="node-badge ${nodeType}">${SECTION_TYPE_LABELS[nodeType as SectionType]}</span>
        ` : null}

        <span class="inline-actions">
          ${!isRow ? html`
            <sl-tooltip content="Add row">
              <sl-icon-button
                class="add-row"
                name="plus-circle"
                @click=${this.handleAddRow}
              ></sl-icon-button>
            </sl-tooltip>
          ` : null}
          <sl-tooltip content="${isRow ? 'Delete row' : 'Delete section'}">
            <sl-icon-button
              class="delete"
              name="x-circle"
              @click=${this.handleDelete}
            ></sl-icon-button>
          </sl-tooltip>
        </span>

        <sl-icon class="drag-handle" name="grip-vertical"></sl-icon>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'tree-node': TreeNode;
  }
}
