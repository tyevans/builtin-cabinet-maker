import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import {
  cabinetStore,
  type CabinetState,
  setRoom,
  addWallSegment,
  updateWallSegment,
  removeWallSegment,
} from '@/state/cabinet-state';
import type { WallSegmentSpec, BaseZoneSpec } from '@/api/types';
import { DEFAULT_BASE_ZONE } from '@/api/types';

import '@shoelace-style/shoelace/dist/components/switch/switch.js';
import '@shoelace-style/shoelace/dist/components/button/button.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/card/card.js';
import '@shoelace-style/shoelace/dist/components/details/details.js';

@customElement('room-editor')
export class RoomEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
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

    .wall-list {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .wall-card {
      background: var(--sl-color-neutral-50);
      border: 1px solid var(--sl-color-neutral-200);
      border-radius: var(--sl-border-radius-medium);
      padding: 0.75rem;
    }

    .wall-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }

    .wall-number {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--sl-color-neutral-600);
    }

    .wall-fields {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 0.5rem;
    }

    sl-input::part(form-control-label) {
      font-size: 0.7rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input) {
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

    .room-controls {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .toekick-section {
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px dashed var(--sl-color-neutral-200);
    }

    .toekick-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }

    .toekick-label {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    .toekick-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem;
      margin-top: 0.5rem;
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

  private get room() {
    return this.cabinetState.config.room;
  }

  private get walls(): WallSegmentSpec[] {
    return this.room?.walls || [];
  }

  private handleRoomToggle(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      setRoom({
        name: 'Room',
        walls: [{ length: 120, height: 96 }],
        is_closed: false,
      });
    } else {
      setRoom(null);
    }
  }

  private handleAddWall(): void {
    addWallSegment({ length: 48, height: 96 });
  }

  private handleRemoveWall(index: number): void {
    removeWallSegment(index);
  }

  private handleWallChange(index: number, field: keyof WallSegmentSpec, event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = parseFloat(target.value);
    if (!isNaN(value)) {
      updateWallSegment(index, { [field]: value });
    }
  }

  private handleToekickToggle(index: number, event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      updateWallSegment(index, { base_zone: { ...DEFAULT_BASE_ZONE, enabled: true } });
    } else {
      updateWallSegment(index, { base_zone: undefined });
    }
  }

  private handleToekickChange(index: number, field: keyof BaseZoneSpec, event: Event): void {
    const target = event.target as HTMLInputElement;
    const value = parseFloat(target.value);
    const wall = this.walls[index];
    if (!isNaN(value) && wall.base_zone) {
      updateWallSegment(index, { base_zone: { ...wall.base_zone, [field]: value } });
    }
  }

  render() {
    const hasRoom = this.room !== undefined;

    return html`
      <div class="section-header">
        <span class="section-title">Room Geometry</span>
        <div class="room-controls">
          <sl-switch
            ?checked=${hasRoom}
            @sl-change=${this.handleRoomToggle}
          ></sl-switch>
        </div>
      </div>

      ${hasRoom ? html`
        ${this.walls.length > 0 ? html`
          <div class="wall-list">
            ${this.walls.map((wall, index) => html`
              <div class="wall-card">
                <div class="wall-header">
                  <span class="wall-number">Wall ${index + 1}</span>
                  ${this.walls.length > 1 ? html`
                    <sl-icon-button
                      name="trash"
                      label="Remove wall"
                      @click=${() => this.handleRemoveWall(index)}
                    ></sl-icon-button>
                  ` : null}
                </div>
                <div class="wall-fields">
                  <sl-input
                    type="number"
                    label="Length"
                    size="small"
                    min="12"
                    max="480"
                    step="0.25"
                    .value=${String(wall.length)}
                    @sl-change=${(e: Event) => this.handleWallChange(index, 'length', e)}
                  >
                    <span slot="suffix">in</span>
                  </sl-input>
                  <sl-input
                    type="number"
                    label="Height"
                    size="small"
                    min="48"
                    max="144"
                    step="0.25"
                    .value=${String(wall.height)}
                    @sl-change=${(e: Event) => this.handleWallChange(index, 'height', e)}
                  >
                    <span slot="suffix">in</span>
                  </sl-input>
                  <sl-input
                    type="number"
                    label="Join Angle"
                    size="small"
                    min="0"
                    max="360"
                    step="1"
                    .value=${String(wall.angle ?? 90)}
                    @sl-change=${(e: Event) => this.handleWallChange(index, 'angle', e)}
                  >
                    <span slot="suffix">°</span>
                  </sl-input>
                </div>
                <!-- Per-wall Toe Kick -->
                <div class="toekick-section">
                  <div class="toekick-header">
                    <span class="toekick-label">Toe Kick</span>
                    <sl-switch
                      size="small"
                      ?checked=${wall.base_zone?.enabled}
                      @sl-change=${(e: Event) => this.handleToekickToggle(index, e)}
                    ></sl-switch>
                  </div>
                  ${wall.base_zone?.enabled ? html`
                    <div class="toekick-fields">
                      <sl-input
                        type="number"
                        label="Height"
                        size="small"
                        min="2"
                        max="8"
                        step="0.25"
                        .value=${String(wall.base_zone.height)}
                        @sl-change=${(e: Event) => this.handleToekickChange(index, 'height', e)}
                      >
                        <span slot="suffix">in</span>
                      </sl-input>
                      <sl-input
                        type="number"
                        label="Setback"
                        size="small"
                        min="1"
                        max="6"
                        step="0.25"
                        .value=${String(wall.base_zone.setback)}
                        @sl-change=${(e: Event) => this.handleToekickChange(index, 'setback', e)}
                      >
                        <span slot="suffix">in</span>
                      </sl-input>
                    </div>
                  ` : null}
                </div>
              </div>
            `)}
          </div>

          <sl-button
            class="add-button"
            variant="text"
            size="small"
            @click=${this.handleAddWall}
          >
            <sl-icon slot="prefix" name="plus-lg"></sl-icon>
            Add Wall Segment
          </sl-button>
        ` : html`
          <div class="empty-state">
            No wall segments defined
          </div>
        `}
      ` : html`
        <div class="empty-state">
          Enable room geometry to define wall segments
        </div>
      `}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'room-editor': RoomEditor;
  }
}
