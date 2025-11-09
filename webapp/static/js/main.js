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

// Parse SVG dimensions
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

// Ruler Functions
function initializeRuler() {
  const preview = document.getElementById('preview');
  const container = document.getElementById('previewContainerRuler');

  if (!preview || !container || !lastSvgText) {
    console.log('Ruler init skipped: missing elements or SVG');
    return;
  }

  // Clear existing ruler
  clearRuler();

  // FIX: This line is the required change.
  container.style.position = 'relative';

  // Get the SVG element
  const svgElement = preview.querySelector('svg');
  if (!svgElement) {
    console.log('Ruler init skipped: no SVG element found');
    return;
  }

  // Parse SVG dimensions
  const dims = parseSvgDimensions(svgElement);
  if (!dims) {
    console.warn('Could not parse SVG dimensions');
    return;
  }

  console.log('SVG Dimensions:', dims);
  console.log('Container dimensions:', container.offsetWidth, 'x', container.offsetHeight);

  // Only initialize ruler if there's SVG content and dimensions
  if (window.Ruler) {
    // Wait for next frame to ensure SVG is rendered and container has dimensions
    requestAnimationFrame(() => {
      // Double check container has dimensions
      if (container.offsetWidth === 0 || container.offsetHeight === 0) {
        console.warn('Container has no dimensions, retrying...');
        setTimeout(() => initializeRuler(), 100);
        return;
      }

      try {
        console.log('Creating ruler...');

        // Create ruler with mm units (matching SVG)
        Ruler.create(container, {
          unit: 'mm',
          unitPrecision: 0,
          showCrosshair: true,
          showMousePos: true,
          tickColor: '#161616',
          crosshairColor: '#0f62fe',
          crosshairStyle: 'solid',
          mouseBoxBg: '#161616',
          mouseBoxColor: '#fff',
          vRuleSize: 30,
          hRuleSize: 30
        });

        rulerActive = true;
        console.log('Ruler initialized successfully');
      } catch (e) {
        console.error('Failed to initialize ruler:', e);
      }
    });
  } else {
    console.error('Ruler library not loaded!');
  }
}

function clearRuler() {
  const container = document.getElementById('previewContainerRuler');
  if (window.Ruler && rulerActive && container) {
    try {
      Ruler.clear(container);
      console.log('Ruler cleared');
    } catch (e) {
      console.error('Error clearing ruler:', e);
    }
    rulerActive = false;
  }
}

// UI Helper Functions
function setLoading(visible) {
  const overlay = document.getElementById('overlay');
  overlay.classList.toggle('visible', !!visible);
}

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

function toastError(msg) {
  showNotification('error', 'Error', msg);
}

function toastSuccess(msg) {
  showNotification('success', 'Success', msg);
}

// Style Loading with Custom Dropdown
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

function toggleStyleDropdown() {
  const dropdown = document.getElementById('styleDropdown');
  dropdown.classList.toggle('active');
}

function closeStyleDropdown() {
  const dropdown = document.getElementById('styleDropdown');
  dropdown.classList.remove('active');
}

// Character Override Collections
async function loadCharacterOverrideCollections() {
  try {
    const res = await fetch('/api/character-override-collections');
    const data = await res.json();
    CHARACTER_OVERRIDE_COLLECTIONS = data.collections || [];

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

// Page Size Presets
async function loadPageSizePresets() {
  try {
    const res = await fetch('/api/page-size-presets');
    const data = await res.json();
    PAGE_SIZE_PRESETS = data.presets || [];

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

// Template Presets
async function loadTemplatePresets() {
  try {
    const res = await fetch('/api/template-presets');
    const data = await res.json();
    TEMPLATE_PRESETS = data.presets || [];

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

async function applyTemplatePreset(templateId) {
  if (!templateId) return;

  try {
    const res = await fetch(`/api/template-preset/${templateId}`);
    const template = await res.json();

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

// Custom Size Visibility
function syncCustomSizeVisibility() {
  const pageSize = document.getElementById('pageSize').value;
  const customFields = document.getElementById('customSizeFields');
  customFields.style.display = pageSize === 'custom' ? 'block' : 'none';
}

// Build Margins Object
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

// Apply Presets
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

// Copy SVG
function copySvg() {
  if (!lastSvgText) {
    toastError('No SVG to copy. Generate handwriting first.');
    return;
  }

  navigator.clipboard.writeText(lastSvgText)
    .then(() => toastSuccess('SVG copied to clipboard'))
    .catch(() => toastError('Failed to copy to clipboard'));
}

// Main Generation
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

  const payload = {
    text,
    page_size: pageSize,
    units,
    margins,
    line_height: lineHeight ? Number(lineHeight) : undefined,
    align,
    background: background || undefined,
    orientation,
    legibility,
    character_override_collection_id: characterOverrideCollectionId ? Number(characterOverrideCollectionId) : undefined,
    global_scale: globalScale ? Number(globalScale) : undefined,
    page_width: pageWidth ? Number(pageWidth) : undefined,
    page_height: pageHeight ? Number(pageHeight) : undefined,
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
    manual_size_scale: manualSizeScale ? Number(manualSizeScale) : undefined,
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

    // Initialize ruler with the preview
    clearRuler();
    initializeRuler();

    toastSuccess('Handwriting generated successfully');
  } catch (error) {
    toastError(error.message);
  } finally {
    setLoading(false);
  }
}

// Download SVG
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

// Batch Processing
function clearBatchUI() {
  document.getElementById('batchContainer').style.display = 'none';
  document.getElementById('batchLiveGrid').innerHTML = '';
  document.getElementById('batchLog').innerHTML = '';
  document.getElementById('batchProg').textContent = '0';
  document.getElementById('batchTotal').textContent = '0';
  document.getElementById('batchOk').textContent = '0';
  document.getElementById('batchErr').textContent = '0';
  document.getElementById('progressFill').style.width = '0%';
  document.getElementById('batchDownload').style.display = 'none';
}

async function batchGenerateStream() {
  if (!CSV_FILE) {
    toastError('Please select a CSV file first');
    return;
  }

  clearBatchUI();
  document.getElementById('batchContainer').style.display = 'block';
  setLoading(true);

  const formData = new FormData();
  formData.append('csv', CSV_FILE);

  // Add current configuration as defaults
  const config = {
    style: SELECTED_STYLE_ID,
    legibility: document.getElementById('legibility').value,
    page_size: document.getElementById('pageSize').value,
    orientation: document.getElementById('orientation').value,
    units: document.getElementById('units').value,
    margins: buildMargins(),
  };

  formData.append('config', JSON.stringify(config));

  let ok = 0, err = 0, total = 0;
  const liveGrid = document.getElementById('batchLiveGrid');
  const liveLimit = () => parseInt(document.getElementById('liveLimit').value) || 12;

  try {
    const response = await fetch('/api/batch-generate-stream', {
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
          } else if (payload.type === 'row') {
            const log = document.getElementById('batchLog');
            const entry = document.createElement('div');

            if (payload.status === 'ok') {
              ok += 1;
              entry.className = 'batch-log-entry success';
              entry.innerHTML = `<i data-feather="check"></i> Row ${payload.row}: ${payload.file}`;
              document.getElementById('batchOk').textContent = String(ok);

              if (payload.file && liveGrid.children.length < liveLimit()) {
                const card = document.createElement('div');
                card.className = 'live-preview-card';
                card.setAttribute('data-filename', payload.file);
                card.innerHTML = `
                  <div class="live-preview-filename">${payload.file}</div>
                  <div class="live-preview-status">Generating...</div>
                `;
                liveGrid.insertBefore(card, liveGrid.firstChild);
              }
            } else {
              err += 1;
              entry.className = 'batch-log-entry error';
              entry.innerHTML = `<i data-feather="x"></i> Row ${payload.row}: ${payload.error}`;
              document.getElementById('batchErr').textContent = String(err);
            }

            log.appendChild(entry);
            if (typeof feather !== 'undefined') feather.replace();
            log.scrollTop = log.scrollHeight;
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
function setupCsvDragDrop() {
  const dropzone = document.getElementById('csvDrop');
  const input = document.getElementById('csv');
  const info = document.getElementById('csvInfo');

  function showFileInfo(file) {
    if (!file) {
      info.style.display = 'none';
      return;
    }

    info.innerHTML = `
      <div class="file-info">
        <span class="file-info-name">${file.name}</span>
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

    const file = Array.from(files).find(f => f.name.toLowerCase().endsWith('.csv')) || files[0];
    CSV_FILE = file;
    showFileInfo(CSV_FILE);

    if (file.name.toLowerCase().endsWith('.csv')) {
      batchGenerateStream();
    }
  });
}

// Zoom Control
function setupZoomControl() {
  const zoom = document.getElementById('zoom');
  const zoomVal = document.getElementById('zoomVal');

  zoom.addEventListener('input', () => {
    const value = Number(zoom.value);
    zoomVal.textContent = `${value}%`;

    const preview = document.getElementById('preview');
    preview.style.transform = `scale(${value / 100})`;
    preview.style.transformOrigin = 'top left';
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