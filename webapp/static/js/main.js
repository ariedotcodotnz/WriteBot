// State Management
let lastSvgText = '';
let lastMetadata = {};
let STYLE_LIST = [];
let SELECTED_STYLE_ID = null;
let CSV_FILE = null;
let CHARACTER_OVERRIDE_COLLECTIONS = [];
let PAGE_SIZE_PRESETS = [];
let TEMPLATE_PRESETS = [];
let rulerActive = false;

/**
 * Parse SVG dimensions from an SVG element.
 * @param {SVGElement} svgElement - The SVG element to parse.
 * @returns {Object|null} - Object containing width, height, and units, or null if failed.
 */
function parseSvgDimensions(svgElement) {
  if (!svgElement) return null;

  const width = svgElement.getAttribute('width');
  const height = svgElement.getAttribute('height');

  if (!width || !height) return null;

  // Parse dimensions with units (e.g., "210.0mm", "800px")
  const parseValue = (val) => {
    const match = val.match(/^([\d.]+)(\w+)?$/);
    if (!match) return { value: parseFloat(val), unit: 'px' };
    return { value: parseFloat(match[1]), unit: match[2] || 'px' };
  };

  const w = parseValue(width);
  const h = parseValue(height);

  return {
    width: w.value,
    height: h.value,
    widthUnit: w.unit,
    heightUnit: h.unit
  };
}

// UI Helper Functions

/**
 * Toggle the loading overlay.
 * @param {boolean} visible - Whether to show or hide the overlay.
 */
function setLoading(visible) {
  const overlay = document.getElementById('overlay');
  overlay.classList.toggle('visible', !!visible);
}

/**
 * Show a notification toast.
 * @param {string} type - Notification type ('success' or 'error').
 * @param {string} title - Notification title.
 * @param {string} message - Notification message content.
 * @param {number} [duration=5000] - Duration in milliseconds before auto-dismiss.
 */
function showNotification(type, title, message, duration = 5000) {
  const container = document.getElementById('notif');
  const id = 'notif-' + Date.now();

  const notification = document.createElement('div');
  notification.id = id;
  notification.className = `notification ${type}`;
  notification.innerHTML = `
    <div class="notification-icon">
      ${type === 'error' ? 
        '<i data-feather="alert-circle" style="color: #da1e28;"></i>' :
        '<i data-feather="check-circle" style="color: #24a148;"></i>'}
    </div>
    <div class="notification-content">
      <div class="notification-title">${title}</div>
      <div class="notification-message">${message}</div>
    </div>
    <button class="notification-close" onclick="this.parentElement.remove()">
      <i data-feather="x" style="width: 16px; height: 16px;"></i>
    </button>
  `;

  container.appendChild(notification);

  // Replace feather icons in notification
  if (typeof feather !== 'undefined') feather.replace();

  if (duration > 0) {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.remove();
    }, duration);
  }
}

/**
 * Show an error toast.
 * @param {string} msg - The error message.
 */
function toastError(msg) {
  showNotification('error', 'Error', msg);
}

/**
 * Show a success toast.
 * @param {string} msg - The success message.
 */
function toastSuccess(msg) {
  showNotification('success', 'Success', msg);
}

/**
 * Load available handwriting styles from the API.
 * Populates both the standard select and custom dropdown.
 */
async function loadStyles() {
  const sel = document.getElementById('styleSelect');
  const customDropdown = document.getElementById('styleDropdown');
  sel.innerHTML = '<option>Loading styles...</option>';

  try {
    const res = await fetch('/api/styles');
    const data = await res.json();
    STYLE_LIST = (data && data.styles) || [];

    if (!STYLE_LIST.length) {
      STYLE_LIST = Array.from({ length: 13 }, (_, i) => ({ id: i, label: `Style ${i}` }));
    }

    // Populate standard select (fallback)
    sel.innerHTML = '';
    STYLE_LIST.forEach(style => {
      const opt = document.createElement('option');
      opt.value = String(style.id);
      opt.textContent = `Style ${style.id} - ${style.label || 'Custom'}`;
      sel.appendChild(opt);
    });

    // Populate custom dropdown with SVG previews
    customDropdown.innerHTML = '';
    STYLE_LIST.forEach(style => {
      const optionDiv = document.createElement('div');
      optionDiv.className = 'style-option';
      optionDiv.dataset.styleId = String(style.id);

      // Create SVG preview element
      const preview = document.createElement('img');
      preview.className = 'style-preview-img';
      preview.src = `/api/style-preview/${style.id}`;
      preview.alt = `Style ${style.id} preview`;
      preview.onerror = function() {
        this.style.display = 'none';
      };

      // Create label
      const label = document.createElement('span');
      label.className = 'style-label';
      label.textContent = `Style ${style.id}${style.label ? ' - ' + style.label : ''}`;

      optionDiv.appendChild(preview);
      optionDiv.appendChild(label);

      // Click handler
      optionDiv.addEventListener('click', () => {
        selectStyle(style.id);
        closeStyleDropdown();
      });

      customDropdown.appendChild(optionDiv);
    });

    // Select first style by default
    if (STYLE_LIST.length > 0) {
      selectStyle(STYLE_LIST[0].id);
    }
  } catch (err) {
    console.error('Failed to load styles:', err);
    toastError('Failed to load styles: ' + err.message);
  }
}

/**
 * Select a handwriting style.
 * @param {number|string} styleId - The ID of the style to select.
 */
function selectStyle(styleId) {
  SELECTED_STYLE_ID = styleId;
  const sel = document.getElementById('styleSelect');
  sel.value = String(styleId);

  // Update visual selection in custom dropdown
  document.querySelectorAll('.style-option').forEach(opt => {
    opt.classList.remove('selected');
    if (opt.dataset.styleId === String(styleId)) {
      opt.classList.add('selected');
    }
  });
}

/**
 * Toggle visibility of the custom style dropdown.
 */
function toggleStyleDropdown() {
  const dropdown = document.getElementById('styleDropdown');
  dropdown.classList.toggle('active');
}

/**
 * Close the custom style dropdown.
 */
function closeStyleDropdown() {
  const dropdown = document.getElementById('styleDropdown');
  dropdown.classList.remove('active');
}

/**
 * Load character override collections from the API.
 */
async function loadCharacterOverrideCollections() {
  try {
    const res = await fetch('/api/collections');
    const data = await res.json();
    CHARACTER_OVERRIDE_COLLECTIONS = Array.isArray(data) ? data : [];

    const sel = document.getElementById('characterOverrideCollection');
    sel.innerHTML = '<option value="">None (use AI)</option>';

    CHARACTER_OVERRIDE_COLLECTIONS.forEach(col => {
      const opt = document.createElement('option');
      opt.value = col.id;
      opt.textContent = col.name;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error('Failed to load character override collections:', err);
  }
}

/**
 * Load page size presets from the API.
 */
async function loadPageSizePresets() {
  try {
    const res = await fetch('/api/page-sizes');
    const data = await res.json();
    PAGE_SIZE_PRESETS = data.page_sizes || [];

    const sel = document.getElementById('pageSize');
    sel.innerHTML = '';

    PAGE_SIZE_PRESETS.forEach(preset => {
      const opt = document.createElement('option');
      opt.value = preset.id;
      opt.textContent = preset.name;
      sel.appendChild(opt);
    });

    // Add custom option
    const customOpt = document.createElement('option');
    customOpt.value = 'custom';
    customOpt.textContent = 'Custom';
    sel.appendChild(customOpt);

    // Select first preset by default
    if (PAGE_SIZE_PRESETS.length > 0) {
      sel.value = PAGE_SIZE_PRESETS[0].id;
    }
  } catch (err) {
    console.error('Failed to load page size presets:', err);
  }
}

/**
 * Load template presets from the API.
 */
async function loadTemplatePresets() {
  try {
    const res = await fetch('/api/templates');
    const data = await res.json();
    TEMPLATE_PRESETS = data.templates || [];

    const sel = document.getElementById('templatePreset');
    sel.innerHTML = '<option value="">None (Manual Settings)</option>';

    TEMPLATE_PRESETS.forEach(preset => {
      const opt = document.createElement('option');
      opt.value = preset.id;
      opt.textContent = preset.name;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error('Failed to load template presets:', err);
  }
}

/**
 * Apply a selected template preset to the form fields.
 * @param {string} templateId - The ID of the template to apply.
 */
async function applyTemplatePreset(templateId) {
  if (!templateId) return;

  try {
    const res = await fetch(`/api/templates/${templateId}`);
    const data = await res.json();
    const template = data.template;

    // Apply all template fields
    if (template.text) document.getElementById('text').value = template.text;
    if (template.style !== undefined) selectStyle(template.style);
    if (template.legibility) document.getElementById('legibility').value = template.legibility;
    if (template.page_size) document.getElementById('pageSize').value = template.page_size;
    if (template.orientation) document.getElementById('orientation').value = template.orientation;
    if (template.units) document.getElementById('units').value = template.units;
    if (template.align) document.getElementById('align').value = template.align;

    // Margins
    if (template.margins) {
      if (template.margins.top !== undefined) document.getElementById('marginTop').value = template.margins.top;
      if (template.margins.right !== undefined) document.getElementById('marginRight').value = template.margins.right;
      if (template.margins.bottom !== undefined) document.getElementById('marginBottom').value = template.margins.bottom;
      if (template.margins.left !== undefined) document.getElementById('marginLeft').value = template.margins.left;
    }

    if (template.line_height) document.getElementById('lineHeight').value = template.line_height;
    if (template.background) document.getElementById('background').value = template.background;

    syncCustomSizeVisibility();
    toastSuccess(`Applied template: ${template.name || 'Template'}`);
  } catch (err) {
    console.error('Failed to apply template preset:', err);
    toastError('Failed to apply template preset');
  }
}

// Save Preset Modal Functions

/**
 * Open the modal to save current settings as a preset.
 */
function openSavePresetModal() {
  const modal = document.getElementById('savePresetModal');
  modal.style.display = 'flex';
  document.getElementById('presetName').value = '';
  document.getElementById('presetDescription').value = '';
  document.getElementById('presetName').focus();
}

/**
 * Close the save preset modal.
 */
function closeSavePresetModal() {
  const modal = document.getElementById('savePresetModal');
  modal.style.display = 'none';
}

/**
 * Save current form settings as a new template preset via API.
 */
async function savePreset() {
  const name = document.getElementById('presetName').value.trim();
  const description = document.getElementById('presetDescription').value.trim();

  if (!name) {
    toastError('Please enter a template name');
    return;
  }

  // Gather all form data
  const pageSize = document.getElementById('pageSize').value;

  // Validate that a preset page size is selected (not custom)
  if (pageSize === 'custom') {
    toastError('Cannot save template with custom page size. Please select a predefined page size.');
    return;
  }
  const orientation = document.getElementById('orientation').value;
  const units = document.getElementById('units').value;
  const align = document.getElementById('align').value;

  // Margins
  const marginTop = parseFloat(document.getElementById('marginTop').value) || 10.0;
  const marginRight = parseFloat(document.getElementById('marginRight').value) || 10.0;
  const marginBottom = parseFloat(document.getElementById('marginBottom').value) || 10.0;
  const marginLeft = parseFloat(document.getElementById('marginLeft').value) || 10.0;

  // Line settings
  const lineHeight = document.getElementById('lineHeight').value ? parseFloat(document.getElementById('lineHeight').value) : null;
  const emptyLineSpacing = document.getElementById('emptyLineSpacing').value ? parseFloat(document.getElementById('emptyLineSpacing').value) : null;

  // Scaling
  const globalScale = parseFloat(document.getElementById('globalScale').value) || 1.0;
  const autoSize = document.getElementById('autoSize').checked;
  const manualSizeScale = document.getElementById('manualSizeScale').value ? parseFloat(document.getElementById('manualSizeScale').value) : null;

  // Background
  const background = document.getElementById('background').value || null;

  // Advanced style options
  const biases = document.getElementById('biases').value || null;
  const styles = document.getElementById('styles').value || null;
  const strokeColors = document.getElementById('strokeColors').value || null;
  const strokeWidths = document.getElementById('strokeWidths').value || null;
  const xStretch = parseFloat(document.getElementById('xStretch').value) || 1.0;
  const denoise = document.getElementById('denoise').value === 'true';

  // Text wrapping
  const wrapCharPx = document.getElementById('wrapCharPx').value ? parseFloat(document.getElementById('wrapCharPx').value) : null;
  const wrapRatio = document.getElementById('wrapRatio').value ? parseFloat(document.getElementById('wrapRatio').value) : null;
  const wrapUtil = document.getElementById('wrapUtil').value ? parseFloat(document.getElementById('wrapUtil').value) : null;

  // Chunked generation
  const useChunked = document.getElementById('useChunked').checked;
  const adaptiveChunking = document.getElementById('adaptiveChunking').checked;
  const adaptiveStrategy = document.getElementById('adaptiveStrategy').value || null;
  const wordsPerChunk = document.getElementById('wordsPerChunk').value ? parseInt(document.getElementById('wordsPerChunk').value) : null;
  const chunkSpacing = document.getElementById('chunkSpacing').value ? parseFloat(document.getElementById('chunkSpacing').value) : null;
  const maxLineWidth = document.getElementById('maxLineWidth').value ? parseFloat(document.getElementById('maxLineWidth').value) : null;

  const templateData = {
    name,
    description,
    page_size_preset_id: parseInt(pageSize),
    orientation,
    margin_top: marginTop,
    margin_right: marginRight,
    margin_bottom: marginBottom,
    margin_left: marginLeft,
    margin_unit: units,
    line_height: lineHeight,
    line_height_unit: units,
    empty_line_spacing: emptyLineSpacing,
    text_alignment: align,
    global_scale: globalScale,
    auto_size: autoSize,
    manual_size_scale: manualSizeScale,
    background_color: background,
    biases,
    per_line_styles: styles,
    stroke_colors: strokeColors,
    stroke_widths: strokeWidths,
    horizontal_stretch: xStretch,
    denoise,
    character_width: wrapCharPx,
    wrap_ratio: wrapRatio,
    wrap_utilization: wrapUtil,
    use_chunked_generation: useChunked,
    adaptive_chunking: adaptiveChunking,
    adaptive_strategy: adaptiveStrategy,
    words_per_chunk: wordsPerChunk,
    chunk_spacing: chunkSpacing,
    max_line_width: maxLineWidth
  };

  try {
    const res = await fetch('/api/templates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(templateData)
    });

    const result = await res.json();

    if (res.ok) {
      toastSuccess(result.message || 'Template saved successfully');
      closeSavePresetModal();
      // Refresh the presets dropdown
      await loadTemplatePresets();
    } else {
      toastError(result.error || 'Failed to save template');
    }
  } catch (err) {
    console.error('Failed to save template preset:', err);
    toastError('Failed to save template preset');
  }
}

/**
 * Show/hide custom page dimension fields based on page size selection.
 */
function syncCustomSizeVisibility() {
  const pageSize = document.getElementById('pageSize').value;
  const customFields = document.getElementById('customSizeFields');
  customFields.style.display = pageSize === 'custom' ? 'block' : 'none';
}

/**
 * Build the margins object from input fields.
 * @returns {Object|undefined} - Margins object or undefined if all fields empty.
 */
function buildMargins() {
  const mt = document.getElementById('marginTop').value;
  const mr = document.getElementById('marginRight').value;
  const mb = document.getElementById('marginBottom').value;
  const ml = document.getElementById('marginLeft').value;

  const toNum = v => (v === '' || v === null || v === undefined) ? null : Number(v);
  const t = toNum(mt), r = toNum(mr), b = toNum(mb), l = toNum(ml);

  if (t === null && r === null && b === null && l === null) return undefined;
  return { top: t ?? 20, right: r ?? 20, bottom: b ?? 20, left: l ?? 20 };
}

/**
 * Apply generic preset values to the form.
 * @param {string} size - Page size ID.
 * @param {string} orient - Orientation ('portrait'/'landscape').
 * @param {number} margin - Margin size.
 */
function applyPreset(size, orient, margin) {
  document.getElementById('pageSize').value = size;
  document.getElementById('orientation').value = orient;
  document.getElementById('marginTop').value = margin;
  document.getElementById('marginRight').value = margin;
  document.getElementById('marginBottom').value = margin;
  document.getElementById('marginLeft').value = margin;
  syncCustomSizeVisibility();
  toastSuccess(`Applied preset: ${size} ${orient}`);
}

/**
 * Copy the generated SVG code to clipboard.
 */
function copySvg() {
  if (!lastSvgText) {
    toastError('No SVG to copy. Generate handwriting first.');
    return;
  }

  navigator.clipboard.writeText(lastSvgText)
    .then(() => toastSuccess('SVG copied to clipboard'))
    .catch(() => toastError('Failed to copy to clipboard'));
}

/**
 * Helper to resolve page size from preset ID to name.
 * @param {string} pageSizeValue - The selected page size value (ID or 'custom').
 * @returns {string} - The page size name.
 */
function resolvePageSize(pageSizeValue) {
  if (pageSizeValue === 'custom') {
    return 'custom';
  }
  const preset = PAGE_SIZE_PRESETS.find(p => String(p.id) === String(pageSizeValue));
  return preset ? preset.name : 'A4';
}

/**
 * Get page dimensions from preset or custom inputs.
 * @param {string} pageSizeValue - The selected page size value (ID or 'custom').
 * @returns {object} - Object with width, height, and unit (or nulls if using predefined size).
 */
function getPageDimensions(pageSizeValue) {
  if (pageSizeValue === 'custom') {
    // Use custom input fields
    const pageWidth = document.getElementById('pageWidth').value;
    const pageHeight = document.getElementById('pageHeight').value;
    return {
      width: pageWidth ? Number(pageWidth) : null,
      height: pageHeight ? Number(pageHeight) : null,
      unit: document.getElementById('units').value
    };
  }

  // Find the preset and get its dimensions
  const preset = PAGE_SIZE_PRESETS.find(p => String(p.id) === String(pageSizeValue));
  if (preset) {
    // Check if this is a predefined size (A4, A5, Letter, Legal) that the backend knows about
    const predefinedSizes = ['A4', 'A5', 'Letter', 'Legal'];
    if (predefinedSizes.includes(preset.name)) {
      // Backend knows this size by name, no need to send dimensions
      return { width: null, height: null, unit: null };
    }
    // Custom preset - send the actual dimensions so backend can use them
    return {
      width: preset.width,
      height: preset.height,
      unit: preset.unit || 'mm'
    };
  }

  // Fallback - no dimensions
  return { width: null, height: null, unit: null };
}

/**
 * Trigger handwriting generation.
 * Collects all form parameters and sends them to the generation API.
 */
async function generate() {
  const text = document.getElementById('text').value;
  if (!text.trim()) {
    toastError('Please enter some text');
    return;
  }

  const pageSize = document.getElementById('pageSize').value;
  const units = document.getElementById('units').value;
  const margins = buildMargins();
  const lineHeight = document.getElementById('lineHeight').value;
  const align = document.getElementById('align').value;
  const background = document.getElementById('background').value;
  const orientation = document.getElementById('orientation').value;
  const legibility = document.getElementById('legibility').value;
  const characterOverrideCollectionId = document.getElementById('characterOverrideCollection').value;
  const biases = document.getElementById('biases').value;
  const stylesOverride = document.getElementById('styles').value;
  const globalStyle = SELECTED_STYLE_ID ? String(SELECTED_STYLE_ID) : '';
  const strokeColors = document.getElementById('strokeColors').value;
  const strokeWidths = document.getElementById('strokeWidths').value;
  const pageWidth = document.getElementById('pageWidth').value;
  const pageHeight = document.getElementById('pageHeight').value;
  const wrapCharPx = document.getElementById('wrapCharPx').value;
  const wrapRatio = document.getElementById('wrapRatio').value;
  const wrapUtil = document.getElementById('wrapUtil').value;
  const xStretch = document.getElementById('xStretch').value;
  const denoise = document.getElementById('denoise').value;
  const globalScale = document.getElementById('globalScale').value;
  const emptyLineSpacing = document.getElementById('emptyLineSpacing').value;
  const autoSize = document.getElementById('autoSize').checked;
  const manualSizeScale = document.getElementById('manualSizeScale').value;
  const useChunked = document.getElementById('useChunked').checked;
  const adaptiveChunking = document.getElementById('adaptiveChunking').checked;
  const adaptiveStrategy = document.getElementById('adaptiveStrategy').value;
  const wordsPerChunk = document.getElementById('wordsPerChunk').value;
  const chunkSpacing = document.getElementById('chunkSpacing').value;
  const maxLineWidth = document.getElementById('maxLineWidth').value;

  const parseList = (s, cast) => s ? s.split('|').map(v => cast(v.trim())) : undefined;
  const stylesList = stylesOverride ? parseList(stylesOverride, Number) : (globalStyle ? [Number(globalStyle)] : undefined);

  // Get page dimensions from preset or custom inputs
  const pageDimensions = getPageDimensions(pageSize);

  const payload = {
    text,
    page_size: resolvePageSize(pageSize),
    units,
    margins,
    line_height: lineHeight ? Number(lineHeight) : undefined,
    align,
    background: background || undefined,
    orientation,
    legibility,
    character_override_collection_id: characterOverrideCollectionId ? Number(characterOverrideCollectionId) : undefined,
    global_scale: globalScale ? Number(globalScale) : undefined,
    // Send page dimensions from preset or custom inputs
    page_width: pageDimensions.width || undefined,
    page_height: pageDimensions.height || undefined,
    biases: parseList(biases, Number),
    styles: stylesList,
    stroke_colors: parseList(strokeColors, String),
    stroke_widths: parseList(strokeWidths, Number),
    wrap_char_px: wrapCharPx ? Number(wrapCharPx) : undefined,
    wrap_ratio: wrapRatio ? Number(wrapRatio) : undefined,
    wrap_utilization: wrapUtil ? Number(wrapUtil) : undefined,
    x_stretch: xStretch ? Number(xStretch) : undefined,
    denoise: denoise || undefined,
    empty_line_spacing: emptyLineSpacing ? Number(emptyLineSpacing) : undefined,
    auto_size: autoSize,
    // Only send manual size scale when auto size is disabled
    manual_size_scale: (!autoSize && manualSizeScale) ? Number(manualSizeScale) : undefined,
    use_chunked: useChunked,
    adaptive_chunking: adaptiveChunking,
    adaptive_strategy: adaptiveStrategy || undefined,
    words_per_chunk: wordsPerChunk ? Number(wordsPerChunk) : undefined,
    chunk_spacing: chunkSpacing ? Number(chunkSpacing) : undefined,
    max_line_width: maxLineWidth ? Number(maxLineWidth) : undefined,
  };

  setLoading(true);

  try {
    const res = await fetch('/api/v1/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || res.statusText);
    }

    const data = await res.json();
    lastSvgText = data.svg;
    lastMetadata = data.meta || {};

    // Update preview
    const preview = document.getElementById('preview');
    preview.innerHTML = lastSvgText;

    // Update source code
    document.getElementById('output').querySelector('code').textContent = lastSvgText;

    // Update metadata info
    const metaInfo = document.getElementById('metaInfo');
    if (lastMetadata && Object.keys(lastMetadata).length > 0) {
      const lines = lastMetadata.lines || {};
      const page = lastMetadata.page || {};
      metaInfo.innerHTML = `
        Lines: ${lines.wrapped_count || 0} (from ${lines.input_count || 0} input) | 
        Page: ${page.width_mm || 0}×${page.height_mm || 0}mm | 
        Orientation: ${page.orientation || 'portrait'}
      `;
    }

    // Update ruler with SVG dimensions
    if (typeof updateRulerForSVG === 'function') {
      updateRulerForSVG(lastSvgText, lastMetadata);
    }

    toastSuccess('Handwriting generated successfully');
  } catch (error) {
    toastError(error.message);
  } finally {
    setLoading(false);
  }
}

/**
 * Download the generated handwriting as an SVG file.
 */
function downloadSVG() {
  if (!lastSvgText) {
    toastError('Please generate handwriting first');
    return;
  }

  const filename = 'handwriting.svg';
  const blob = new Blob([lastSvgText], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  toastSuccess('SVG downloaded');
}

/**
 * Download the generated handwriting as a PDF file.
 * Uses jsPDF and svg2pdf libraries.
 */
async function downloadPDF() {
  if (!lastSvgText) {
    toastError('Please generate handwriting first');
    return;
  }

  // Check if jsPDF is loaded - try multiple ways it might be exposed
  const jsPDF = window.jspdf?.jsPDF || window.jsPDF;

  if (!jsPDF) {
    console.error('jsPDF not found. window.jspdf:', window.jspdf, 'window.jsPDF:', window.jsPDF);
    toastError('PDF library not loaded. Please refresh the page.');
    return;
  }

  try {
    setLoading(true);

    // Parse the SVG string to get the element
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(lastSvgText, 'image/svg+xml');
    const svgElement = svgDoc.documentElement;

    // Check for parsing errors
    const parserError = svgDoc.querySelector('parsererror');
    if (parserError) {
      throw new Error('Failed to parse SVG: ' + parserError.textContent);
    }

    // Clone the SVG element to avoid modifying the original
    const svgClone = svgElement.cloneNode(true);

    // Get SVG dimensions
    const viewBox = svgClone.getAttribute('viewBox');
    let width, height;

    if (viewBox) {
      const viewBoxValues = viewBox.split(/\s+|,/).map(v => parseFloat(v.trim()));
      width = viewBoxValues[2] - (viewBoxValues[0] || 0);
      height = viewBoxValues[3] - (viewBoxValues[1] || 0);
    } else {
      width = parseFloat(svgClone.getAttribute('width')) || 800;
      height = parseFloat(svgClone.getAttribute('height')) || 600;
    }

    // Ensure dimensions are valid
    if (!width || !height || width <= 0 || height <= 0 || !isFinite(width) || !isFinite(height)) {
      throw new Error(`Invalid SVG dimensions: ${width}x${height}`);
    }

    // Convert to points (1px = 0.75pt is standard)
    const widthPt = Math.max(width * 0.75, 100);
    const heightPt = Math.max(height * 0.75, 100);

    // Create PDF with appropriate orientation
    const orientation = widthPt > heightPt ? 'l' : 'p';
    const pdf = new jsPDF({
      orientation: orientation,
      unit: 'pt',
      format: [widthPt, heightPt],
      compress: true
    });

    // Set PDF metadata
    pdf.setProperties({
      title: 'Handwriting Document',
      subject: 'AI-Generated Handwriting',
      author: 'WriteBot',
      creator: 'WriteBot - Handwriting Synthesis',
      producer: 'WriteBot'
    });

    // Check if svg method exists
    if (typeof pdf.svg !== 'function') {
      throw new Error('svg2pdf.js not loaded properly. The pdf.svg() method is not available.');
    }

    console.log('Converting SVG to PDF...', {
      width: widthPt,
      height: heightPt,
      orientation,
      originalWidth: width,
      originalHeight: height
    });

    // Convert SVG to PDF with proper options
    await pdf.svg(svgClone, {
      x: 0,
      y: 0,
      width: widthPt,
      height: heightPt
    });

    // Save the PDF
    pdf.save('handwriting.pdf');

    setLoading(false);
    toastSuccess('PDF downloaded successfully');
  } catch (error) {
    setLoading(false);
    console.error('Error converting to PDF:', error);

    // Provide more helpful error messages
    let errorMsg = 'Failed to convert to PDF';
    if (error.message.includes('rect')) {
      errorMsg += ': SVG contains invalid shapes or dimensions';
    } else if (error.message.includes('dimensions')) {
      errorMsg += ': ' + error.message;
    } else {
      errorMsg += ': ' + error.message;
    }

    toastError(errorMsg);
  }
}

// Batch Processing
let BATCH_LOG_TEXT = ''; // Store the ASCII log

/**
 * Clear the batch processing UI.
 */
function clearBatchUI() {
  document.getElementById('batchContainer').style.display = 'none';
  document.getElementById('batchLiveGrid').innerHTML = '';
  BATCH_LOG_TEXT = '';
  document.getElementById('batchLog').textContent = 'Ready to process batch...';
  document.getElementById('batchProg').textContent = '0';
  document.getElementById('batchTotal').textContent = '0';
  document.getElementById('batchOk').textContent = '0';
  document.getElementById('batchErr').textContent = '0';
  document.getElementById('progressFill').style.width = '0%';
  document.getElementById('batchDownload').style.display = 'none';
}

/**
 * Open the batch preview modal for a generated file.
 * @param {string} filename - Name of the file.
 * @param {string} svgContent - SVG content.
 */
function openBatchPreview(filename, svgContent) {
  const modal = document.getElementById('batchPreviewModal');
  const title = document.getElementById('batchPreviewTitle');
  const content = document.getElementById('batchPreviewContent');

  title.textContent = filename;
  content.innerHTML = svgContent;
  modal.style.display = 'flex';

  // Re-initialize feather icons if needed
  if (typeof feather !== 'undefined') feather.replace();
}

/**
 * Close the batch preview modal.
 */
function closeBatchPreview() {
  const modal = document.getElementById('batchPreviewModal');
  modal.style.display = 'none';
}

/**
 * Append a message to the batch processing log.
 * @param {string} message - Message to append.
 */
function appendLog(message) {
  BATCH_LOG_TEXT += message + '\n';
  document.getElementById('batchLog').textContent = BATCH_LOG_TEXT;
  // Auto-scroll to bottom
  const logElement = document.getElementById('batchLog').parentElement;
  logElement.scrollTop = logElement.scrollHeight;
}

/**
 * Process batch generation via streaming response.
 * Sends CSV file and configuration to the backend and handles SSE updates.
 */
async function batchGenerateStream() {
  if (!CSV_FILE) {
    toastError('Please select a CSV or XLSX file first');
    return;
  }

  clearBatchUI();
  document.getElementById('batchContainer').style.display = 'block';
  setLoading(true);

  const formData = new FormData();
  formData.append('file', CSV_FILE);

  // Add current configuration as defaults (as form fields, not JSON)
  // Style settings
  formData.append('styles', SELECTED_STYLE_ID || '');
  formData.append('legibility', document.getElementById('legibility').value);
  formData.append('character_override_collection_id', document.getElementById('characterOverrideCollection').value || '');

  // Page settings
  const pageSize = document.getElementById('pageSize').value;
  formData.append('page_size', resolvePageSize(pageSize));
  formData.append('orientation', document.getElementById('orientation').value);
  formData.append('units', document.getElementById('units').value);
  formData.append('align', document.getElementById('align').value);
  formData.append('background', document.getElementById('background').value || '');

  // Page dimensions from preset or custom inputs
  const pageDimensions = getPageDimensions(pageSize);
  if (pageDimensions.width) {
    formData.append('page_width', String(pageDimensions.width));
  }
  if (pageDimensions.height) {
    formData.append('page_height', String(pageDimensions.height));
  }

  // Margins - send as individual fields, not as an object
  formData.append('margin_top', document.getElementById('marginTop').value || '');
  formData.append('margin_right', document.getElementById('marginRight').value || '');
  formData.append('margin_bottom', document.getElementById('marginBottom').value || '');
  formData.append('margin_left', document.getElementById('marginLeft').value || '');

  // Line settings
  formData.append('line_height', document.getElementById('lineHeight').value || '');
  formData.append('empty_line_spacing', document.getElementById('emptyLineSpacing').value || '');
  formData.append('global_scale', document.getElementById('globalScale').value || '');

  // Writing size settings
  formData.append('auto_size', document.getElementById('autoSize').checked ? 'true' : 'false');
  formData.append('manual_size_scale', document.getElementById('manualSizeScale').value || '');

  // Advanced style options
  formData.append('biases', document.getElementById('biases').value || '');
  formData.append('stroke_colors', document.getElementById('strokeColors').value || '');
  formData.append('stroke_widths', document.getElementById('strokeWidths').value || '');
  formData.append('x_stretch', document.getElementById('xStretch').value || '');
  formData.append('denoise', document.getElementById('denoise').value || '');

  // Text wrapping options
  formData.append('wrap_char_px', document.getElementById('wrapCharPx').value || '');
  formData.append('wrap_ratio', document.getElementById('wrapRatio').value || '');
  formData.append('wrap_utilization', document.getElementById('wrapUtil').value || '');

  // Text generation options
  formData.append('use_chunked', document.getElementById('useChunked').checked ? 'true' : 'false');
  formData.append('adaptive_chunking', document.getElementById('adaptiveChunking').checked ? 'true' : 'false');
  formData.append('adaptive_strategy', document.getElementById('adaptiveStrategy').value || '');
  formData.append('words_per_chunk', document.getElementById('wordsPerChunk').value || '');
  formData.append('chunk_spacing', document.getElementById('chunkSpacing').value || '');
  formData.append('max_line_width', document.getElementById('maxLineWidth').value || '');

  let ok = 0, err = 0, total = 0;
  const liveGrid = document.getElementById('batchLiveGrid');
  const liveLimit = () => parseInt(document.getElementById('liveLimit').value) || 12;

  try {
    const response = await fetch('/api/batch/stream', {
      method: 'POST',
      body: formData
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();

      for (const chunk of parts) {
        if (!chunk.startsWith('data:')) continue;

        try {
          const payload = JSON.parse(chunk.replace(/^data:\s*/, ''));

          if (payload.type === 'start') {
            total = payload.total || 0;
            document.getElementById('batchTotal').textContent = String(total);
            BATCH_LOG_TEXT = '';
            appendLog('='.repeat(70));
            appendLog('WriteBot Batch Processing Log');
            appendLog('='.repeat(70));
            appendLog(`Started at: ${new Date().toLocaleString()}`);
            appendLog(`Total rows to process: ${total}`);
            appendLog('='.repeat(70));
            appendLog('');
          } else if (payload.type === 'row') {
            if (payload.status === 'ok') {
              ok += 1;
              appendLog(`[✓] Row ${payload.row}: ${payload.file} - SUCCESS`);
              document.getElementById('batchOk').textContent = String(ok);

              if (payload.file && liveGrid.children.length < liveLimit()) {
                const card = document.createElement('div');
                card.className = 'live-preview-card';
                card.setAttribute('data-filename', payload.file);
                card.style.cursor = 'pointer';
                card.innerHTML = `
                  <div class="live-preview-filename">${payload.file}</div>
                  <div class="live-preview-status">Generating...</div>
                `;
                liveGrid.insertBefore(card, liveGrid.firstChild);
              }
            } else {
              err += 1;
              appendLog(`[✗] Row ${payload.row}: ERROR - ${payload.error}`);
              document.getElementById('batchErr').textContent = String(err);
            }
          } else if (payload.type === 'progress') {
            const completed = payload.completed || 0;
            document.getElementById('batchProg').textContent = String(completed);
            if (total > 0) {
              const percent = (completed / total) * 100;
              document.getElementById('progressFill').style.width = `${percent}%`;
            }
          } else if (payload.type === 'done') {
            const dl = document.getElementById('batchDownload');
            dl.href = payload.download;
            dl.style.display = 'inline-flex';

            // Add completion summary to log
            appendLog('');
            appendLog('='.repeat(70));
            appendLog('Processing Complete');
            appendLog('='.repeat(70));
            appendLog(`Completed at: ${new Date().toLocaleString()}`);
            appendLog(`Total processed: ${payload.total}`);
            appendLog(`Successful: ${payload.success} (${((payload.success/payload.total)*100).toFixed(1)}%)`);
            appendLog(`Errors: ${payload.errors}`);
            appendLog('='.repeat(70));

            if (typeof feather !== 'undefined') feather.replace();

            toastSuccess(`Batch processing complete: ${ok} successful, ${err} errors`);

            const jobId = payload.job_id;
            if (jobId) {
              const cards = Array.from(liveGrid.children);
              for (const card of cards) {
                const fname = card.getAttribute('data-filename');
                if (!fname) continue;

                fetch(`/api/batch/result/${jobId}/file/${encodeURIComponent(fname)}`)
                  .then(r => r.text())
                  .then(svg => {
                    card.innerHTML = `
                      <div class="live-preview-filename">${fname}</div>
                      <div class="batch-svg-preview">
                        ${svg}
                      </div>
                      <div class="live-preview-status">Complete</div>
                    `;
                    // Make card clickable to view larger preview
                    card.onclick = () => openBatchPreview(fname, svg);
                  })
                  .catch(() => {});
              }
            }
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      }
    }
  } catch (error) {
    toastError(error.message);
  } finally {
    setLoading(false);
  }
}

// CSV Drag and Drop

/**
 * Setup drag and drop functionality for CSV files.
 */
function setupCsvDragDrop() {
  const dropzone = document.getElementById('csvDrop');
  const input = document.getElementById('csv');
  const info = document.getElementById('csvInfo');

  // Escape HTML meta-characters in text
  function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"'\/]/g, function(s) {
      const entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;'
      };
      return entityMap[s];
    });
  }

  function showFileInfo(file) {
    if (!file) {
      info.style.display = 'none';
      return;
    }

    info.innerHTML = `
      <div class="file-info">
        <span class="file-info-name">${escapeHtml(file.name)}</span>
        <span class="file-info-size">${(file.size / 1024).toFixed(1)} KB</span>
      </div>
    `;
    info.style.display = 'block';
  }

  input.addEventListener('change', () => {
    CSV_FILE = input.files[0];
    showFileInfo(CSV_FILE);
  });

  ['dragenter', 'dragover'].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer?.files;
    if (!files?.length) return;

    const file = Array.from(files).find(f => {
      const name = f.name.toLowerCase();
      return name.endsWith('.csv') || name.endsWith('.xlsx');
    }) || files[0];
    CSV_FILE = file;
    showFileInfo(CSV_FILE);

    // Only auto-start if checkbox is enabled
    const filename = file.name.toLowerCase();
    if (filename.endsWith('.csv') || filename.endsWith('.xlsx')) {
      const autoStart = document.getElementById('autoStartBatch');
      if (autoStart && autoStart.checked) {
        batchGenerateStream();
      }
    }
  });
}

// Zoom Control

/**
 * Setup zoom controls for the preview area.
 */
function setupZoomControl() {
  const zoom = document.getElementById('zoom');
  const zoomVal = document.getElementById('zoomVal');

  zoom.addEventListener('input', () => {
    const value = Number(zoom.value);
    zoomVal.textContent = `${value}%`;

    const preview = document.getElementById('preview');
    preview.style.transform = `scale(${value / 100})`;
    preview.style.transformOrigin = 'top left';

    // Update ruler zoom if available
    if (typeof window.svgRulerInstance !== 'undefined' && window.svgRulerInstance) {
      window.svgRulerInstance.zoom = value / 100;
      window.svgRulerInstance.drawRulers();
    }
  });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadStyles();
  loadCharacterOverrideCollections();
  loadPageSizePresets();
  loadTemplatePresets();
  syncCustomSizeVisibility();
  setupCsvDragDrop();
  setupZoomControl();

  // Auto-load preset from URL parameter
  const urlParams = new URLSearchParams(window.location.search);
  const presetId = urlParams.get('preset');
  if (presetId) {
    // Wait a bit for presets to load, then apply
    setTimeout(() => {
      const presetSelect = document.getElementById('templatePreset');
      presetSelect.value = presetId;
      applyTemplatePreset(presetId);
    }, 500);
  }

  document.getElementById('pageSize').addEventListener('change', syncCustomSizeVisibility);

  // Template preset selection
  const templatePresetSelect = document.getElementById('templatePreset');
  if (templatePresetSelect) {
    templatePresetSelect.addEventListener('change', (e) => {
      const templateId = e.target.value;
      applyTemplatePreset(templateId);
    });
  }

  // Setup custom style dropdown trigger
  const selectWrapper = document.querySelector('.style-select-trigger');
  if (selectWrapper) {
    selectWrapper.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleStyleDropdown();
    });
  }

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.style-dropdown-wrapper')) {
      closeStyleDropdown();
    }
  });

  // Toggle manual size scale input based on auto size checkbox
  const autoSizeCheckbox = document.getElementById('autoSize');
  const manualSizeScaleInput = document.getElementById('manualSizeScale');
  autoSizeCheckbox.addEventListener('change', () => {
    manualSizeScaleInput.disabled = autoSizeCheckbox.checked;
  });

  // Add keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeStyleDropdown();
    }
    if (e.ctrlKey || e.metaKey) {
      if (e.key === 'Enter') {
        e.preventDefault();
        generate();
      } else if (e.key === 's') {
        e.preventDefault();
        downloadSVG();
      }
    }
  });
});
