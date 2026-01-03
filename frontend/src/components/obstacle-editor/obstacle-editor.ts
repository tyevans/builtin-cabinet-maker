import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  cabinetStore,
  type CabinetState,
  addObstacle,
  updateObstacle,
  removeObstacle,
} from '@/state/cabinet-state';
import {
  type ObstacleSpec,
  type ObstacleType,
  OBSTACLE_TYPE_LABELS,
  OBSTACLE_DEFAULTS,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/divider/divider.js';

@customElement('obstacle-editor')
export class ObstacleEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
      margin-top: 1rem;
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.75rem;
    }

    .section-title {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--sl-color-neutral-800);
    }

    .obstacle-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .obstacle-card {
      background: var(--sl-color-neutral-50);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.75rem;
    }

    .obstacle-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }

    .obstacle-type-badge {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--sl-color-neutral-700);
      background: var(--sl-color-neutral-100);
      padding: 0.25rem 0.5rem;
      border-radius: var(--sl-border-radius-small);
    }

    .obstacle-fields {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 0.5rem;
    }

    .obstacle-fields.four-col {
      grid-template-columns: repeat(4, 1fr);
    }

    sl-input::part(form-control-label),
    sl-select::part(form-control-label) {
      font-size: 0.7rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input),
    sl-select::part(combobox) {
      font-size: 0.875rem;
    }

    .add-button {
      margin-top: 0.75rem;
    }

    .empty-state {
      color: var(--sl-color-neutral-500);
      font-size: 0.875rem;
      text-align: center;
      padding: 1rem;
      background: var(--sl-color-neutral-50);
      border-radius: var(--sl-border-radius-medium);
    }

    sl-divider {
      --spacing: 0.5rem;
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

  private get obstacles(): ObstacleSpec[] {
    return this.cabinetState.config.obstacles || [];
  }

  private handleAddObstacle(): void {
    const defaults = OBSTACLE_DEFAULTS.window;
    addObstacle({
      obstacle_type: 'window',
      wall_index: 0,
      horizontal_offset: 12,
      bottom: 36,
      width: defaults.width,
      height: defaults.height,
    });
  }

  private handleRemoveObstacle(index: number): void {
    removeObstacle(index);
  }

  private handleObstacleTypeChange(index: number, event: Event): void {
    const target = event.target as HTMLSelectElement;
    const newType = target.value as ObstacleType;
    const defaults = OBSTACLE_DEFAULTS[newType];
    updateObstacle(index, {
      obstacle_type: newType,
      width: defaults.width,
      height: defaults.height,
    });
  }

  private handleObstacleChange(index: number, field: keyof ObstacleSpec, event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = parseFloat(target.value);
    if (!isNaN(value)) {
      updateObstacle(index, { [field]: value });
    }
  }

  private handleObstacleNameChange(index: number, event: Event): void {
    const target = event.target as HTMLInputElement;
    updateObstacle(index, { name: target.value || undefined });
  }

  private getObstacleIcon(type: ObstacleType): string {
    const icons: Record<ObstacleType, string> = {
      window: 'grid-1x2',
      door: 'door-open',
      outlet: 'plug',
      switch: 'toggles',
      vent: 'wind',
      custom: 'square',
    };
    return icons[type] || 'square';
  }

  render() {
    const obstacleTypes = Object.entries(OBSTACLE_TYPE_LABELS) as [ObstacleType, string][];

    return html`
      <div class="section-header">
        <span class="section-title">Obstacles</span>
      </div>

      ${this.obstacles.length > 0 ? html`
        <div class="obstacle-list">
          ${this.obstacles.map((obstacle, index) => html`
            <div class="obstacle-card">
              <div class="obstacle-header">
                <span class="obstacle-type-badge">
                  <sl-icon name=${this.getObstacleIcon(obstacle.obstacle_type)}></sl-icon>
                  ${OBSTACLE_TYPE_LABELS[obstacle.obstacle_type]}
                </span>
                <sl-icon-button
                  name="trash"
                  label="Remove obstacle"
                  @click=${() => this.handleRemoveObstacle(index)}
                ></sl-icon-button>
              </div>

              <div class="obstacle-fields">
                <sl-select
                  label="Type"
                  size="small"
                  .value=${obstacle.obstacle_type}
                  @sl-change=${(e: Event) => this.handleObstacleTypeChange(index, e)}
                >
                  ${obstacleTypes.map(([value, label]) => html`
                    <sl-option value=${value}>${label}</sl-option>
                  `)}
                </sl-select>
                <sl-input
                  type="text"
                  label="Name"
                  size="small"
                  placeholder="Optional"
                  .value=${obstacle.name || ''}
                  @sl-change=${(e: Event) => this.handleObstacleNameChange(index, e)}
                ></sl-input>
              </div>

              <sl-divider></sl-divider>

              <div class="obstacle-fields four-col">
                <sl-input
                  type="number"
                  label="Offset"
                  size="small"
                  min="0"
                  step="0.25"
                  .value=${String(obstacle.horizontal_offset)}
                  @sl-change=${(e: Event) => this.handleObstacleChange(index, 'horizontal_offset', e)}
                >
                  <span slot="suffix">in</span>
                </sl-input>
                <sl-input
                  type="number"
                  label="Bottom"
                  size="small"
                  min="0"
                  step="0.25"
                  .value=${String(obstacle.bottom)}
                  @sl-change=${(e: Event) => this.handleObstacleChange(index, 'bottom', e)}
                >
                  <span slot="suffix">in</span>
                </sl-input>
                <sl-input
                  type="number"
                  label="Width"
                  size="small"
                  min="1"
                  step="0.25"
                  .value=${String(obstacle.width)}
                  @sl-change=${(e: Event) => this.handleObstacleChange(index, 'width', e)}
                >
                  <span slot="suffix">in</span>
                </sl-input>
                <sl-input
                  type="number"
                  label="Height"
                  size="small"
                  min="1"
                  step="0.25"
                  .value=${String(obstacle.height)}
                  @sl-change=${(e: Event) => this.handleObstacleChange(index, 'height', e)}
                >
                  <span slot="suffix">in</span>
                </sl-input>
              </div>
            </div>
          `)}
        </div>
      ` : html`
        <div class="empty-state">
          No obstacles defined. Add windows, doors, outlets, etc.
        </div>
      `}

      <sl-button
        class="add-button"
        variant="text"
        size="small"
        @click=${this.handleAddObstacle}
      >
        <sl-icon slot="prefix" name="plus-lg"></sl-icon>
        Add Obstacle
      </sl-button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'obstacle-editor': ObstacleEditor;
  }
}
