import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState, setFaceFrame, setCrownMolding, setBaseZone, setLightRail } from '@/state/cabinet-state';
import {
  type FaceFrameSpec,
  type CrownMoldingSpec,
  type BaseZoneSpec,
  type LightRailSpec,
  DEFAULT_FACE_FRAME,
  DEFAULT_CROWN_MOLDING,
  DEFAULT_BASE_ZONE,
  DEFAULT_LIGHT_RAIL,
} from '@/api/types';

import '@shoelace-style/shoelace/dist/components/switch/switch.js';
import '@shoelace-style/shoelace/dist/components/input/input.js';
import '@shoelace-style/shoelace/dist/components/select/select.js';
import '@shoelace-style/shoelace/dist/components/option/option.js';
import '@shoelace-style/shoelace/dist/components/divider/divider.js';

@customElement('decorative-editor')
export class DecorativeEditor extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    .decorative-section {
      margin-bottom: 1rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--sl-color-neutral-200);
    }

    .decorative-section:last-child {
      border-bottom: none;
      margin-bottom: 0;
      padding-bottom: 0;
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

    .section-fields {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      margin-top: 0.75rem;
    }

    .section-fields.three-col {
      grid-template-columns: 1fr 1fr 1fr;
    }

    sl-input::part(form-control-label),
    sl-select::part(form-control-label) {
      font-size: 0.75rem;
      color: var(--sl-color-neutral-600);
    }

    sl-input::part(input),
    sl-select::part(combobox) {
      font-size: 0.875rem;
    }

    .empty-state {
      color: var(--sl-color-neutral-500);
      font-size: 0.875rem;
      text-align: center;
      padding: 1rem;
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

  private get faceFrame(): FaceFrameSpec | undefined {
    return this.cabinetState.config.cabinet.face_frame;
  }

  private get crownMolding(): CrownMoldingSpec | undefined {
    return this.cabinetState.config.cabinet.crown_molding;
  }

  private get baseZone(): BaseZoneSpec | undefined {
    return this.cabinetState.config.cabinet.base_zone;
  }

  private get lightRail(): LightRailSpec | undefined {
    return this.cabinetState.config.cabinet.light_rail;
  }

  // Face Frame handlers
  private handleFaceFrameToggle(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      setFaceFrame({ ...DEFAULT_FACE_FRAME, enabled: true });
    } else {
      setFaceFrame(null);
    }
  }

  private handleFaceFrameChange(field: keyof FaceFrameSpec, value: number | string): void {
    if (this.faceFrame) {
      setFaceFrame({ ...this.faceFrame, [field]: value });
    }
  }

  // Crown Molding handlers
  private handleCrownToggle(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      setCrownMolding({ ...DEFAULT_CROWN_MOLDING, enabled: true });
    } else {
      setCrownMolding(null);
    }
  }

  private handleCrownChange(field: keyof CrownMoldingSpec, value: number): void {
    if (this.crownMolding) {
      setCrownMolding({ ...this.crownMolding, [field]: value });
    }
  }

  // Base Zone handlers
  private handleBaseZoneToggle(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      setBaseZone({ ...DEFAULT_BASE_ZONE, enabled: true });
    } else {
      setBaseZone(null);
    }
  }

  private handleBaseZoneChange(field: keyof BaseZoneSpec, value: number): void {
    if (this.baseZone) {
      setBaseZone({ ...this.baseZone, [field]: value });
    }
  }

  // Light Rail handlers
  private handleLightRailToggle(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      setLightRail({ ...DEFAULT_LIGHT_RAIL, enabled: true });
    } else {
      setLightRail(null);
    }
  }

  private handleLightRailChange(field: keyof LightRailSpec, value: number): void {
    if (this.lightRail) {
      setLightRail({ ...this.lightRail, [field]: value });
    }
  }

  private parseNumberInput(event: Event): number {
    const target = event.target as HTMLInputElement;
    return parseFloat(target.value) || 0;
  }

  render() {
    return html`
      <!-- Face Frame -->
      <div class="decorative-section">
        <div class="section-header">
          <span class="section-title">Face Frame</span>
          <sl-switch
            ?checked=${this.faceFrame?.enabled}
            @sl-change=${this.handleFaceFrameToggle}
          ></sl-switch>
        </div>
        ${this.faceFrame?.enabled ? html`
          <div class="section-fields three-col">
            <sl-input
              type="number"
              label="Stile Width"
              size="small"
              min="0.5"
              max="4"
              step="0.125"
              .value=${String(this.faceFrame.stile_width)}
              @sl-change=${(e: Event) => this.handleFaceFrameChange('stile_width', this.parseNumberInput(e))}
            >
              <span slot="suffix">in</span>
            </sl-input>
            <sl-input
              type="number"
              label="Rail Width"
              size="small"
              min="0.5"
              max="4"
              step="0.125"
              .value=${String(this.faceFrame.rail_width)}
              @sl-change=${(e: Event) => this.handleFaceFrameChange('rail_width', this.parseNumberInput(e))}
            >
              <span slot="suffix">in</span>
            </sl-input>
            <sl-select
              label="Joinery"
              size="small"
              .value=${this.faceFrame.joinery}
              @sl-change=${(e: Event) => this.handleFaceFrameChange('joinery', (e.target as HTMLSelectElement).value)}
            >
              <sl-option value="pocket_screw">Pocket Screw</sl-option>
              <sl-option value="mortise_tenon">Mortise & Tenon</sl-option>
              <sl-option value="dowel">Dowel</sl-option>
            </sl-select>
          </div>
        ` : null}
      </div>

      <!-- Crown Molding -->
      <div class="decorative-section">
        <div class="section-header">
          <span class="section-title">Crown Molding</span>
          <sl-switch
            ?checked=${this.crownMolding?.enabled}
            @sl-change=${this.handleCrownToggle}
          ></sl-switch>
        </div>
        ${this.crownMolding?.enabled ? html`
          <div class="section-fields">
            <sl-input
              type="number"
              label="Height"
              size="small"
              min="1"
              max="12"
              step="0.25"
              .value=${String(this.crownMolding.height)}
              @sl-change=${(e: Event) => this.handleCrownChange('height', this.parseNumberInput(e))}
            >
              <span slot="suffix">in</span>
            </sl-input>
            <sl-input
              type="number"
              label="Setback"
              size="small"
              min="0"
              max="4"
              step="0.125"
              .value=${String(this.crownMolding.setback)}
              @sl-change=${(e: Event) => this.handleCrownChange('setback', this.parseNumberInput(e))}
            >
              <span slot="suffix">in</span>
            </sl-input>
          </div>
        ` : null}
      </div>

      <!-- Base Zone / Toe Kick -->
      <div class="decorative-section">
        <div class="section-header">
          <span class="section-title">Toe Kick</span>
          <sl-switch
            ?checked=${this.baseZone?.enabled}
            @sl-change=${this.handleBaseZoneToggle}
          ></sl-switch>
        </div>
        ${this.baseZone?.enabled ? html`
          <div class="section-fields">
            <sl-input
              type="number"
              label="Height"
              size="small"
              min="2"
              max="8"
              step="0.25"
              .value=${String(this.baseZone.height)}
              @sl-change=${(e: Event) => this.handleBaseZoneChange('height', this.parseNumberInput(e))}
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
              .value=${String(this.baseZone.setback)}
              @sl-change=${(e: Event) => this.handleBaseZoneChange('setback', this.parseNumberInput(e))}
            >
              <span slot="suffix">in</span>
            </sl-input>
          </div>
        ` : null}
      </div>

      <!-- Light Rail -->
      <div class="decorative-section">
        <div class="section-header">
          <span class="section-title">Light Rail</span>
          <sl-switch
            ?checked=${this.lightRail?.enabled}
            @sl-change=${this.handleLightRailToggle}
          ></sl-switch>
        </div>
        ${this.lightRail?.enabled ? html`
          <div class="section-fields">
            <sl-input
              type="number"
              label="Height"
              size="small"
              min="0.5"
              max="4"
              step="0.25"
              .value=${String(this.lightRail.height)}
              @sl-change=${(e: Event) => this.handleLightRailChange('height', this.parseNumberInput(e))}
            >
              <span slot="suffix">in</span>
            </sl-input>
          </div>
        ` : null}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'decorative-editor': DecorativeEditor;
  }
}
