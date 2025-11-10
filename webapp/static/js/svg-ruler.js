/**
 * SVG Ruler and Coordinate Tracking System
 * Provides rulers and crosshair coordinate tracking for SVG preview
 */

class SVGRuler {
  constructor(containerId, previewId) {
    this.container = document.getElementById(containerId);
    this.preview = document.getElementById(previewId);
    this.zoom = 1.0;
    this.svgWidth = 0;
    this.svgHeight = 0;
    this.unit = 'mm'; // mm or px

    this.init();
  }

  init() {
    // Create ruler elements
    this.createRulerStructure();

    // Attach event listeners
    this.attachEventListeners();
  }

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

  showCrosshair() {
    this.crosshairV.style.display = 'block';
    this.crosshairH.style.display = 'block';
  }

  hideCrosshair() {
    this.crosshairV.style.display = 'none';
    this.crosshairH.style.display = 'none';
    this.coordsDisplay.style.display = 'none';
  }

  updateRulerOffsets() {
    // Update ruler positions based on scroll
    const scrollLeft = this.previewContainer.scrollLeft;
    const scrollTop = this.previewContainer.scrollTop;

    this.topCanvas.style.transform = `translateX(${-scrollLeft}px)`;
    this.leftCanvas.style.transform = `translateY(${-scrollTop}px)`;
  }

  setZoom(zoomPercent) {
    this.zoom = zoomPercent / 100;
    this.preview.style.transform = `scale(${this.zoom})`;
    this.preview.style.transformOrigin = 'top left';

    // Redraw rulers
    this.drawRulers();
  }

  updateSVGDimensions(width, height, unit = 'mm') {
    this.svgWidth = width;
    this.svgHeight = height;
    this.unit = unit;

    // Redraw rulers with new dimensions
    this.drawRulers();
  }

  drawRulers() {
    this.drawHorizontalRuler();
    this.drawVerticalRuler();
  }

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

  destroy() {
    // Clean up event listeners and elements
    this.previewContainer.removeEventListener('mousemove', this.updateCrosshair);
    this.previewContainer.removeEventListener('mouseleave', this.hideCrosshair);
    this.previewContainer.removeEventListener('mouseenter', this.showCrosshair);
  }
}

// Global instance
let svgRulerInstance = null;

// Initialize ruler when DOM is ready
function initSVGRuler() {
  svgRulerInstance = new SVGRuler('previewContainerRuler', 'preview');

  // Initial zoom
  svgRulerInstance.setZoom(100);

  // Make instance globally available
  window.svgRulerInstance = svgRulerInstance;
}

// Update ruler dimensions when SVG is generated
function updateRulerForSVG(svgText, metadata) {
  if (!svgRulerInstance) return;

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
