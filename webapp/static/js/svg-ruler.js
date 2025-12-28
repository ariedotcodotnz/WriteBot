/**
 * SVG Ruler and Coordinate Tracking System
 * Provides rulers and crosshair coordinate tracking for SVG preview
 */

class SVGRuler {
  /**
   * Initialize the SVG Ruler.
   * @param {string} containerId - The ID of the container element for the ruler.
   * @param {string} previewId - The ID of the preview element (SVG).
   */
  constructor(containerId, previewId) {
    this.container = document.getElementById(containerId);
    this.preview = document.getElementById(previewId);
    this.zoom = 1.0;
    this.svgWidth = 0;
    this.svgHeight = 0;
    this.unit = 'mm'; // mm or px

    this.init();
  }

  /**
   * Initialize the ruler structure and event listeners.
   */
  init() {
    // Create ruler elements
    this.createRulerStructure();

    // Attach event listeners
    this.attachEventListeners();
  }

  /**
   * Create the DOM structure for the rulers and crosshairs.
   */
  createRulerStructure() {
    // Clear any existing rulers
    const existing = this.container.querySelectorAll('.svg-ruler-wrapper, .ruler-crosshair-v, .ruler-crosshair-h, .ruler-coordinates');
    existing.forEach(el => el.remove());

    // Create wrapper for preview with rulers
    const wrapper = document.createElement('div');
    wrapper.className = 'svg-ruler-wrapper';

    // Create top ruler (horizontal)
    const topRuler = document.createElement('div');
    topRuler.className = 'svg-ruler svg-ruler-horizontal';
    topRuler.innerHTML = '<canvas class="ruler-canvas"></canvas>';

    // Create left ruler (vertical)
    const leftRuler = document.createElement('div');
    leftRuler.className = 'svg-ruler svg-ruler-vertical';
    leftRuler.innerHTML = '<canvas class="ruler-canvas"></canvas>';

    // Create corner square
    const corner = document.createElement('div');
    corner.className = 'svg-ruler-corner';

    // Create scrollable preview area
    const previewContainer = this.container.querySelector('.preview-container');

    // Create crosshairs (initially hidden)
    const crosshairV = document.createElement('div');
    crosshairV.className = 'ruler-crosshair-v';

    const crosshairH = document.createElement('div');
    crosshairH.className = 'ruler-crosshair-h';

    // Create coordinates display
    const coordsDisplay = document.createElement('div');
    coordsDisplay.className = 'ruler-coordinates';
    coordsDisplay.textContent = '0, 0';

    // Assemble structure
    wrapper.appendChild(corner);
    wrapper.appendChild(topRuler);
    wrapper.appendChild(leftRuler);
    wrapper.appendChild(previewContainer);
    wrapper.appendChild(crosshairV);
    wrapper.appendChild(crosshairH);
    wrapper.appendChild(coordsDisplay);

    // Replace container content
    this.container.innerHTML = '';
    this.container.appendChild(wrapper);

    // Store references
    this.topRuler = topRuler;
    this.leftRuler = leftRuler;
    this.topCanvas = topRuler.querySelector('canvas');
    this.leftCanvas = leftRuler.querySelector('canvas');
    this.crosshairV = crosshairV;
    this.crosshairH = crosshairH;
    this.coordsDisplay = coordsDisplay;
    this.previewContainer = previewContainer;

    // Move preview element into new container
    this.previewContainer.appendChild(this.preview);
  }

  /**
   * Attach event listeners for mouse movement and scrolling.
   */
  attachEventListeners() {
    // Mouse move on preview
    this.previewContainer.addEventListener('mousemove', (e) => {
      this.updateCrosshair(e);
    });

    // Mouse leave preview
    this.previewContainer.addEventListener('mouseleave', () => {
      this.hideCrosshair();
    });

    // Mouse enter preview
    this.previewContainer.addEventListener('mouseenter', () => {
      this.showCrosshair();
    });

    // Scroll events to update ruler positions
    this.previewContainer.addEventListener('scroll', () => {
      this.updateRulerOffsets();
    });
  }

  /**
   * Update crosshair position and coordinate display based on mouse event.
   * @param {MouseEvent} e - The mouse move event.
   */
  updateCrosshair(e) {
    const rect = this.previewContainer.getBoundingClientRect();

    // Position within the visible viewport (for crosshair display)
    const viewportX = e.clientX - rect.left;
    const viewportY = e.clientY - rect.top;

    // Position within the scrollable content (for SVG coordinates)
    const scrolledX = viewportX + this.previewContainer.scrollLeft;
    const scrolledY = viewportY + this.previewContainer.scrollTop;

    // Position crosshairs relative to the visible viewport
    this.crosshairV.style.left = viewportX + 'px';
    this.crosshairH.style.top = viewportY + 'px';

    // Calculate SVG coordinates using scrolled position
    const svgCoords = this.screenToSVGCoordinates(scrolledX, scrolledY);

    // Update coordinate display
    this.updateCoordinateDisplay(e.clientX, e.clientY, svgCoords);
  }

  /**
   * Convert screen coordinates to SVG coordinates.
   * @param {number} screenX - X coordinate on screen.
   * @param {number} screenY - Y coordinate on screen.
   * @returns {Object} - Object containing SVG coordinates (x, y) and pixel coordinates (px).
   */
  screenToSVGCoordinates(screenX, screenY) {
    // No padding - SVG starts at 0,0 aligned with rulers
    const svgX = screenX / this.zoom;
    const svgY = screenY / this.zoom;

    // Convert to selected unit (mm or px)
    let displayX = svgX;
    let displayY = svgY;

    if (this.unit === 'mm') {
      // Convert px to mm (96 DPI standard)
      const PX_PER_MM = 96.0 / 25.4;
      displayX = svgX / PX_PER_MM;
      displayY = svgY / PX_PER_MM;
    }

    return {
      x: Math.round(displayX * 10) / 10,
      y: Math.round(displayY * 10) / 10,
      px: { x: Math.round(svgX), y: Math.round(svgY) }
    };
  }

  /**
   * Update the coordinate display tooltip position and text.
   * @param {number} clientX - Mouse X coordinate.
   * @param {number} clientY - Mouse Y coordinate.
   * @param {Object} svgCoords - Calculated SVG coordinates.
   */
  updateCoordinateDisplay(clientX, clientY, svgCoords) {
    const unitLabel = this.unit;
    this.coordsDisplay.textContent = `${svgCoords.x} × ${svgCoords.y} ${unitLabel} (${svgCoords.px.x} × ${svgCoords.px.y} px)`;

    // Position coordinate display near mouse but keep it visible
    const padding = 15;
    let left = clientX + padding;
    let top = clientY + padding;

    // Keep within viewport
    const rect = this.coordsDisplay.getBoundingClientRect();
    if (left + rect.width > window.innerWidth - 10) {
      left = clientX - rect.width - padding;
    }
    if (top + rect.height > window.innerHeight - 10) {
      top = clientY - rect.height - padding;
    }

    this.coordsDisplay.style.left = left + 'px';
    this.coordsDisplay.style.top = top + 'px';
    this.coordsDisplay.style.display = 'block';
  }

  /**
   * Show the crosshairs.
   */
  showCrosshair() {
    this.crosshairV.style.display = 'block';
    this.crosshairH.style.display = 'block';
  }

  /**
   * Hide the crosshairs.
   */
  hideCrosshair() {
    this.crosshairV.style.display = 'none';
    this.crosshairH.style.display = 'none';
    this.coordsDisplay.style.display = 'none';
  }

  /**
   * Update the ruler canvas positions based on scroll offset.
   */
  updateRulerOffsets() {
    // Update ruler positions based on scroll
    const scrollLeft = this.previewContainer.scrollLeft;
    const scrollTop = this.previewContainer.scrollTop;

    this.topCanvas.style.transform = `translateX(${-scrollLeft}px)`;
    this.leftCanvas.style.transform = `translateY(${-scrollTop}px)`;
  }

  /**
   * Set the zoom level and redraw rulers.
   * @param {number} zoomPercent - Zoom level in percentage (e.g., 100).
   */
  setZoom(zoomPercent) {
    this.zoom = zoomPercent / 100;
    this.preview.style.transform = `scale(${this.zoom})`;
    this.preview.style.transformOrigin = 'top left';

    // Redraw rulers
    this.drawRulers();
  }

  /**
   * Update the SVG dimensions and redraw rulers.
   * @param {number} width - SVG width.
   * @param {number} height - SVG height.
   * @param {string} [unit='mm'] - Unit of measurement.
   */
  updateSVGDimensions(width, height, unit = 'mm') {
    this.svgWidth = width;
    this.svgHeight = height;
    this.unit = unit;

    // Redraw rulers with new dimensions
    this.drawRulers();
  }

  /**
   * Redraw both horizontal and vertical rulers.
   */
  drawRulers() {
    this.drawHorizontalRuler();
    this.drawVerticalRuler();
  }

  /**
   * Draw the horizontal ruler.
   */
  drawHorizontalRuler() {
    const canvas = this.topCanvas;
    const ctx = canvas.getContext('2d');

    // Set canvas size
    const rulerHeight = 30;
    const width = this.previewContainer.scrollWidth;
    canvas.width = width;
    canvas.height = rulerHeight;
    canvas.style.height = rulerHeight + 'px';

    // Clear canvas
    ctx.clearRect(0, 0, width, rulerHeight);

    // Draw ruler background
    ctx.fillStyle = '#f4f4f4';
    ctx.fillRect(0, 0, width, rulerHeight);

    // Draw ruler markings
    this.drawRulerMarkings(ctx, 'horizontal', width, rulerHeight);
  }

  /**
   * Draw the vertical ruler.
   */
  drawVerticalRuler() {
    const canvas = this.leftCanvas;
    const ctx = canvas.getContext('2d');

    // Set canvas size
    const rulerWidth = 30;
    const height = this.previewContainer.scrollHeight;
    canvas.width = rulerWidth;
    canvas.height = height;
    canvas.style.width = rulerWidth + 'px';

    // Clear canvas
    ctx.clearRect(0, 0, rulerWidth, height);

    // Draw ruler background
    ctx.fillStyle = '#f4f4f4';
    ctx.fillRect(0, 0, rulerWidth, height);

    // Draw ruler markings
    this.drawRulerMarkings(ctx, 'vertical', rulerWidth, height);
  }

  /**
   * Draw markings on the ruler canvas.
   * @param {CanvasRenderingContext2D} ctx - Canvas context.
   * @param {string} orientation - 'horizontal' or 'vertical'.
   * @param {number} width - Canvas width.
   * @param {number} height - Canvas height.
   */
  drawRulerMarkings(ctx, orientation, width, height) {
    const PX_PER_MM = 96.0 / 25.4;

    // Determine increment based on unit and zoom
    let majorIncrement = this.unit === 'mm' ? 10 : 50; // 10mm or 50px
    let minorIncrement = this.unit === 'mm' ? 5 : 10;  // 5mm or 10px

    // Adjust for zoom
    const zoomedMajor = majorIncrement * (this.unit === 'mm' ? PX_PER_MM : 1) * this.zoom;
    const zoomedMinor = minorIncrement * (this.unit === 'mm' ? PX_PER_MM : 1) * this.zoom;

    // Skip if too dense
    if (zoomedMajor < 20) {
      majorIncrement *= 5;
      minorIncrement *= 5;
    } else if (zoomedMajor < 40) {
      majorIncrement *= 2;
      minorIncrement *= 2;
    }

    const maxDimension = orientation === 'horizontal' ? width : height;
    const rulerSize = orientation === 'horizontal' ? height : width;

    // Draw markings
    ctx.strokeStyle = '#666';
    ctx.fillStyle = '#333';
    ctx.font = '10px sans-serif';
    ctx.lineWidth = 1;

    // Calculate SVG dimensions in current units
    const svgDimension = orientation === 'horizontal' ? this.svgWidth : this.svgHeight;
    const svgDimensionPx = this.unit === 'mm' ? svgDimension * PX_PER_MM : svgDimension;
    const maxValue = svgDimensionPx / (this.unit === 'mm' ? PX_PER_MM : 1);

    // Draw major and minor ticks - starting at 0 (no padding offset)
    for (let i = 0; i <= maxValue; i += minorIncrement) {
      const isMajor = i % majorIncrement === 0;
      const pos = i * (this.unit === 'mm' ? PX_PER_MM : 1) * this.zoom;

      if (pos > maxDimension) break;

      const tickLength = isMajor ? 12 : 6;

      ctx.beginPath();
      if (orientation === 'horizontal') {
        ctx.moveTo(pos, rulerSize - tickLength);
        ctx.lineTo(pos, rulerSize);

        // Draw label for major ticks
        if (isMajor) {
          ctx.fillText(i.toString(), pos + 2, rulerSize - 15);
        }
      } else {
        ctx.moveTo(rulerSize - tickLength, pos);
        ctx.lineTo(rulerSize, pos);

        // Draw label for major ticks
        if (isMajor) {
          ctx.save();
          ctx.translate(rulerSize - 15, pos - 2);
          ctx.rotate(-Math.PI / 2);
          ctx.fillText(i.toString(), 0, 0);
          ctx.restore();
        }
      }
      ctx.stroke();
    }

    // Draw unit label
    ctx.fillStyle = '#999';
    ctx.font = 'bold 9px sans-serif';
    if (orientation === 'horizontal') {
      ctx.fillText(this.unit, 5, 12);
    } else {
      ctx.save();
      ctx.translate(8, 15);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(this.unit, 0, 0);
      ctx.restore();
    }
  }

  /**
   * Destroy the ruler instance and clean up event listeners.
   */
  destroy() {
    // Clean up event listeners and elements
    this.previewContainer.removeEventListener('mousemove', this.updateCrosshair);
    this.previewContainer.removeEventListener('mouseleave', this.hideCrosshair);
    this.previewContainer.removeEventListener('mouseenter', this.showCrosshair);
  }
}

// Global instance
let svgRulerInstance = null;

/**
 * Initialize the SVGRuler instance when the DOM is ready.
 */
function initSVGRuler() {
  svgRulerInstance = new SVGRuler('previewContainerRuler', 'preview');

  // Initial zoom
  svgRulerInstance.setZoom(100);

  // Make instance globally available
  window.svgRulerInstance = svgRulerInstance;
}

/**
 * Update the ruler dimensions based on the generated SVG and metadata.
 * Also updates the SVG preview content directly for reliability.
 * @param {string} svgText - The raw SVG XML string.
 * @param {Object} metadata - The metadata object returned by the generation API.
 */
function updateRulerForSVG(svgText, metadata) {
  if (!svgRulerInstance) return;

  // Directly update the SVG preview content (bypasses Alpine for reliability)
  const preview = document.getElementById('preview');
  if (preview && svgText) {
    // Find or create the SVG container
    let svgContainer = preview.querySelector('[x-ref="svgPreview"]') ||
                       preview.querySelector('.svg-content');

    if (!svgContainer) {
      // If no dedicated container, find the element with x-html or create one
      svgContainer = preview.querySelector('[x-html]');
      if (!svgContainer) {
        // Create a new container as fallback
        svgContainer = document.createElement('div');
        svgContainer.className = 'svg-content';
        preview.appendChild(svgContainer);
      }
    }

    // Set the SVG content directly
    svgContainer.innerHTML = svgText;
    svgContainer.style.display = 'block';

    // Hide the placeholder
    const placeholder = preview.querySelector('.preview-empty');
    if (placeholder) {
      placeholder.style.display = 'none';
    }
  }

  // Try to extract dimensions from metadata
  if (metadata && metadata.page) {
    const width = metadata.page.width_mm || 210; // default A4
    const height = metadata.page.height_mm || 297;
    const unit = metadata.page.units || 'mm';

    svgRulerInstance.updateSVGDimensions(width, height, unit);
  } else {
    // Try to parse from SVG
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgText, 'image/svg+xml');
    const svg = doc.querySelector('svg');

    if (svg) {
      const width = parseFloat(svg.getAttribute('width')) || 210;
      const height = parseFloat(svg.getAttribute('height')) || 297;

      svgRulerInstance.updateSVGDimensions(width, height, 'mm');
    }
  }

  // Redraw rulers
  svgRulerInstance.drawRulers();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SVGRuler, initSVGRuler, updateRulerForSVG };
}
