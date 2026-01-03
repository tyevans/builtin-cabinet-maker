// Shoelace setup
import '@shoelace-style/shoelace/dist/themes/light.css';
import { setBasePath } from '@shoelace-style/shoelace/dist/utilities/base-path.js';

// Set Shoelace base path for assets (icons, etc.)
// Use CDN for production compatibility
setBasePath('https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.19.1/cdn');

// Styles
import './styles/main.css';

// Register all components
import './components/app-shell';
import './components/config-sidebar';
import './components/dimensions-form';
import './components/material-select';
import './components/section-tree-editor/section-tree-editor';
import './components/preview-panel';
import './components/stl-viewer';
import './components/cut-list-panel';
import './components/export-menu';

// Config I/O components
import './components/config-io/config-import';
import './components/config-io/config-export';

// Decorative components
import './components/decorative-editor/decorative-editor';

// Room & Obstacle components
import './components/room-editor/room-editor';
import './components/obstacle-editor/obstacle-editor';

// Infrastructure & Installation components
import './components/infrastructure-editor/infrastructure-editor';
import './components/installation-editor/installation-editor';

// Initialize application
console.log('Cabinet Designer initialized');
