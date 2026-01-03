import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { cabinetStore, type CabinetState } from '@/state/cabinet-state';
import { api } from '@/api/api';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

import '@shoelace-style/shoelace/dist/components/spinner/spinner.js';
import '@shoelace-style/shoelace/dist/components/icon/icon.js';
import '@shoelace-style/shoelace/dist/components/icon-button/icon-button.js';
import '@shoelace-style/shoelace/dist/components/tooltip/tooltip.js';

// Material for the cabinet
const CABINET_MATERIAL = new THREE.MeshStandardMaterial({
  color: 0xd4a574,
  roughness: 0.8,
  metalness: 0.1,
});

const EDGE_MATERIAL = new THREE.LineBasicMaterial({ color: 0x8b6914 });

@customElement('stl-viewer')
export class StlViewer extends LitElement {
  static styles = css`
    /* Mobile-first: smaller min-height */
    :host {
      display: block;
      width: 100%;
      height: 100%;
      min-height: 300px;
      position: relative;
      background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
      touch-action: none; /* Prevent browser handling of touch gestures */
    }

    @media (min-width: 768px) {
      :host {
        min-height: 400px;
      }
    }

    .canvas-container {
      width: 100%;
      height: 100%;
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
      touch-action: none;
    }

    .loading-indicator {
      position: absolute;
      top: 0.5rem;
      left: 0.5rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0.75rem;
      background: rgba(0, 0, 0, 0.6);
      color: white;
      font-size: 0.75rem;
      border-radius: var(--sl-border-radius-medium);
      z-index: 10;
      opacity: 0;
      transition: opacity 0.15s ease-in-out;
    }

    @media (min-width: 768px) {
      .loading-indicator {
        top: 1rem;
        left: 1rem;
      }
    }

    .loading-indicator.visible {
      opacity: 1;
    }

    .empty-state {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.9);
      z-index: 10;
      padding: 1rem;
      text-align: center;
    }

    .empty-state.hidden {
      display: none;
    }

    .empty-state-icon {
      font-size: 2.5rem;
      color: var(--sl-color-neutral-400);
      margin-bottom: 0.75rem;
    }

    @media (min-width: 768px) {
      .empty-state-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
      }
    }

    .empty-state-text {
      color: var(--sl-color-neutral-600);
      font-size: 0.875rem;
    }

    /* Hide controls hint on mobile - touch is intuitive */
    .controls-hint {
      display: none;
      position: absolute;
      bottom: 1rem;
      left: 1rem;
      padding: 0.5rem 0.75rem;
      background: rgba(0, 0, 0, 0.6);
      color: white;
      font-size: 0.75rem;
      border-radius: var(--sl-border-radius-medium);
      pointer-events: none;
    }

    @media (min-width: 768px) {
      .controls-hint {
        display: block;
      }
    }

    /* Larger tap target for reset button on mobile */
    .reset-button {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      z-index: 5;
    }

    .reset-button sl-icon-button::part(base) {
      font-size: 1.25rem;
      padding: 0.5rem;
    }

    @media (min-width: 768px) {
      .reset-button {
        top: 1rem;
        right: 1rem;
      }

      .reset-button sl-icon-button::part(base) {
        font-size: 1rem;
        padding: 0.25rem;
      }
    }
  `;

  @state()
  private isLoading = false;

  @state()
  private hasModel = false;

  @state()
  private cabinetState: CabinetState = cabinetStore.getState();

  private container: HTMLDivElement | null = null;

  private scene?: THREE.Scene;
  private camera?: THREE.PerspectiveCamera;
  private renderer?: THREE.WebGLRenderer;
  private controls?: OrbitControls;

  private cabinetGroup?: THREE.Group;
  private stlLoader = new STLLoader();

  private animationId?: number;
  private resizeObserver?: ResizeObserver;
  private unsubscribe?: () => void;
  private isInitialLoad = true;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribe = cabinetStore.subscribe(state => {
      const layoutChanged = state.layout !== this.cabinetState.layout;
      this.cabinetState = state;

      // Reload STL when layout changes (not just config)
      if (layoutChanged && state.layout && this.scene) {
        this.loadStlFromBackend();
      }
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribe?.();
    this.cleanup();
  }

  firstUpdated(): void {
    this.container = this.shadowRoot?.querySelector('.canvas-container') as HTMLDivElement;
    this.initThreeJS();
  }

  private initThreeJS(): void {
    if (!this.container) return;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf0f0f0);

    // Camera
    const aspect = this.container.clientWidth / this.container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 10000);
    this.camera.position.set(150, 100, 150);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.shadowMap.enabled = true;
    this.container.appendChild(this.renderer.domElement);

    // Controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(100, 100, 50);
    directionalLight.castShadow = true;
    this.scene.add(directionalLight);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight2.position.set(-50, 50, -50);
    this.scene.add(directionalLight2);

    // Grid helper
    const gridHelper = new THREE.GridHelper(200, 20, 0xcccccc, 0xe0e0e0);
    this.scene.add(gridHelper);

    // Handle resize
    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(this.container);

    // Start animation loop
    this.renderLoop();

    // Load initial STL if layout exists
    if (this.cabinetState.layout) {
      this.loadStlFromBackend();
    }
  }

  private async loadStlFromBackend(): Promise<void> {
    this.isLoading = true;

    try {
      const stlData = await api.getStlFromConfig(this.cabinetState.config);
      this.updateCabinetFromStl(stlData);
    } catch (error) {
      console.warn('Failed to load STL from backend:', error);
    } finally {
      this.isLoading = false;
    }
  }

  private updateCabinetFromStl(stlData: ArrayBuffer): void {
    if (!this.scene) return;

    // Remove existing cabinet
    if (this.cabinetGroup) {
      this.scene.remove(this.cabinetGroup);
      this.cabinetGroup = undefined;
    }

    // Parse STL
    const geometry = this.stlLoader.parse(stlData);
    geometry.computeVertexNormals();

    // Create mesh
    const mesh = new THREE.Mesh(geometry, CABINET_MATERIAL);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    // Add edges for definition
    const edges = new THREE.EdgesGeometry(geometry, 30);
    const line = new THREE.LineSegments(edges, EDGE_MATERIAL);
    mesh.add(line);

    // Create group and center it
    this.cabinetGroup = new THREE.Group();
    this.cabinetGroup.add(mesh);

    // Center the model
    const box = new THREE.Box3().setFromObject(this.cabinetGroup);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    // Move to center horizontally, keep bottom at y=0
    this.cabinetGroup.position.set(-center.x, -box.min.y, -center.z);

    this.scene.add(this.cabinetGroup);
    this.hasModel = true;

    // Only adjust camera on initial load to preserve user's view
    if (this.isInitialLoad && this.camera && this.controls) {
      this.resetCamera();
      this.isInitialLoad = false;
    }
  }

  private resetCamera(): void {
    if (!this.cabinetGroup || !this.camera || !this.controls) return;

    const box = new THREE.Box3().setFromObject(this.cabinetGroup);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);

    this.camera.position.set(maxDim * 1.5, maxDim, maxDim * 1.5);
    this.controls.target.set(0, size.y / 2, 0);
    this.controls.update();
  }

  private handleResize(): void {
    if (!this.container || !this.camera || !this.renderer) return;

    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  private renderLoop = (): void => {
    this.animationId = requestAnimationFrame(this.renderLoop);
    this.controls?.update();
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  };

  private cleanup(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    this.resizeObserver?.disconnect();
    this.renderer?.dispose();
  }

  render() {
    const showEmptyState = !this.hasModel && !this.isLoading;

    return html`
      <div class="canvas-container"></div>

      <sl-tooltip content="Reset view" class="reset-button">
        <sl-icon-button
          name="arrows-fullscreen"
          label="Reset view"
          @click=${this.resetCamera}
        ></sl-icon-button>
      </sl-tooltip>

      <div class="loading-indicator ${this.isLoading ? 'visible' : ''}">
        <sl-spinner style="font-size: 1rem;"></sl-spinner>
        <span>Updating...</span>
      </div>

      <div class="empty-state ${showEmptyState ? '' : 'hidden'}">
        <sl-icon name="box" class="empty-state-icon"></sl-icon>
        <span class="empty-state-text">Configure cabinet to see 3D preview</span>
      </div>

      <div class="controls-hint">
        Drag to rotate | Scroll to zoom | Right-click to pan
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'stl-viewer': StlViewer;
  }
}
