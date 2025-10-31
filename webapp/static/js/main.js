// State Management
let lastSvgText = '';
let lastMetadata = {};
let STYLE_LIST = [];
let SELECTED_STYLE_ID = null;
let CSV_FILE = null;
let CHARACTER_OVERRIDE_COLLECTIONS = [];
let PAGE_SIZE_PRESETS = [];
let TEMPLATE_PRESETS = [];

// Lightbox Functions
function openLightbox(svgContent) {
  const lightbox = document.getElementById('lightbox');
  const lightboxSvg = document.getElementById('lightboxSvg');

  // Clear any existing ruler first before modifying DOM
  if (window.Ruler) {
    Ruler.clear(lightbox);
  }

  lightboxSvg.innerHTML = svgContent;
  lightbox.classList.add('active');
  document.body.style.overflow = 'hidden';

  // Initialize ruler after the lightbox is fully rendered
  // This prevents race conditions and ensures proper initialization
  if (window.Ruler) {
    requestAnimationFrame(() => {
      // Double-check the lightbox is still active before creating ruler
      if (lightbox.classList.contains('active')) {
        Ruler.create(lightbox, {
          unit: 'mm',
          unitPrecision: 1,
          showCrosshair: true,
          showMousePos: true,
          tickColor: '#666',
          crosshairColor: '#ff6b6b',
          crosshairStyle: 'dotted',
          mouseBoxBg: '#323232',
          mouseBoxColor: '#fff',
          vRuleSize: 20,
          hRuleSize: 20
        });
      }
    });
  }
}

function closeLightbox(event) {
  if (event && event.target !== event.currentTarget && !event.target.classList.contains('lightbox')) {
    return;
  }
  const lightbox = document.getElementById('lightbox');

  // Remove active class first
  lightbox.classList.remove('active');
  document.body.style.overflow = '';

  // Clear ruler after closing to ensure proper cleanup
  // Use setTimeout to allow the lightbox to finish closing animation
  if (window.Ruler) {
    setTimeout(() => {
      Ruler.clear(lightbox);
    }, 10);
  }
}

// Setup clickable SVG previews
function makePreviewClickable() {
  const preview = document.getElementById('preview');
  const hint = document.getElementById('previewHint');
  if (lastSvgText) {
    preview.classList.add('has-content');
    // Remove any existing click handler first
    preview.onclick = null;
    // Use addEventListener for more reliable event handling
    preview.onclick = (e) => {
      if (e.target.closest('#preview')) {
        openLightbox(lastSvgText);
      }
    };
    hint.style.display = 'block';
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
    <svg class="notification-icon" viewBox="0 0 20 20">
      ${type === 'error' ? 
        '<path fill="#da1e28" d="M10 0C4.5 0 0 4.5 0 10s4.5 10 10 10 10-4.5 10-10S15.5 0 10 0zm5 13.6L13.6 15 10 11.4 6.4 15 5 13.6 8.6 10 5 6.4 6.4 5 10 8.6 13.6 5 15 6.4 11.4 10 15 13.6z"/>' :
        '<path fill="#24a148" d="M10 0C4.5 0 0 4.5 0 10s4.5 10 10 10 10-4.5 10-10S15.5 0 10 0zm4.2 8.3l-5 5c-.2.2-.5.3-.7.3s-.5-.1-.7-.3l-2-2c-.4-.4-.4-1 0-1.4s1-.4 1.4 0l1.3 1.3 4.3-4.3c.4-.4 1-.4 1.4 0s.4 1 0 1.4z"/>'}
    </svg>
    <div class="notification-content">
      <div class="notification-title">${title}</div>
      <div class="notification-message">${message}</div>
    </div>
    <button class="notification-close" onclick="this.parentElement.remove()">
      <svg width="16" height="16" viewBox="0 0 16 16">
        <path fill="currentColor" d="M12 4.7L11.3 4 8 7.3 4.7 4 4 4.7 7.3 8 4 11.3l.7.7L8 8.7l3.3 3.3.7-.7L8.7 8z"/>
      </svg>
    </button>
  `;
  
  container.appendChild(notification);
  
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
        // Fallback if SVG doesn't load
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

    SELECTED_STYLE_ID = STYLE_LIST[0].id;
    sel.value = String(SELECTED_STYLE_ID);
    updateSelectedStyle(SELECTED_STYLE_ID);

    // Standard select change handler (fallback)
    sel.addEventListener('change', () => {
      SELECTED_STYLE_ID = sel.value;
      updateSelectedStyle(SELECTED_STYLE_ID);
    });
  } catch (e) {
    console.error('Failed to load styles:', e);
    sel.innerHTML = '';
    for (let i = 0; i <= 12; i++) {
      const opt = document.createElement('option');
      opt.value = String(i);
      opt.textContent = `Style ${i}`;
      sel.appendChild(opt);
    }
    SELECTED_STYLE_ID = '9';
    sel.value = '9';
  }
}

// Load Character Override Collections
async function loadCharacterOverrideCollections() {
  const sel = document.getElementById('characterOverrideCollection');
  if (!sel) return; // Element might not exist

  sel.innerHTML = '<option value="">None (use AI)</option>';

  try {
    const res = await fetch('/admin/character-overrides/api/collections');
    if (!res.ok) {
      throw new Error('Failed to load collections');
    }
    const collections = await res.json();
    CHARACTER_OVERRIDE_COLLECTIONS = collections || [];

    collections.forEach(collection => {
      const opt = document.createElement('option');
      opt.value = String(collection.id);
      opt.textContent = `${collection.name} (${collection.unique_characters} chars, ${collection.character_count} variants)`;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load character override collections:', e);
    // Keep the default "None" option
  }
}

// Load Page Size Presets
async function loadPageSizePresets() {
  const sel = document.getElementById('pageSize');
  if (!sel) return;

  sel.innerHTML = '<option value="">Loading...</option>';

  try {
    const res = await fetch('/api/page-sizes');
    if (!res.ok) {
      throw new Error('Failed to load page size presets');
    }
    const data = await res.json();
    PAGE_SIZE_PRESETS = data.page_sizes || [];

    sel.innerHTML = '';
    PAGE_SIZE_PRESETS.forEach(pageSize => {
      const opt = document.createElement('option');
      opt.value = pageSize.name;
      opt.dataset.id = pageSize.id;
      opt.dataset.width = pageSize.width;
      opt.dataset.height = pageSize.height;
      opt.dataset.unit = pageSize.unit;
      opt.textContent = `${pageSize.name} (${pageSize.width} × ${pageSize.height} ${pageSize.unit})`;
      sel.appendChild(opt);
    });

    // Add custom option at the end
    const customOpt = document.createElement('option');
    customOpt.value = 'custom';
    customOpt.textContent = 'Custom Size';
    sel.appendChild(customOpt);

    // Set default to A4 if available
    const a4Option = Array.from(sel.options).find(opt => opt.value === 'A4');
    if (a4Option) {
      sel.value = 'A4';
    }
  } catch (e) {
    console.error('Failed to load page size presets:', e);
    // Fallback to hardcoded options
    sel.innerHTML = `
      <option value="A4">A4 (210 × 297 mm)</option>
      <option value="A5">A5 (148 × 210 mm)</option>
      <option value="Letter">Letter (8.5 × 11")</option>
      <option value="Legal">Legal (8.5 × 14")</option>
      <option value="custom">Custom Size</option>
    `;
  }
}

// Load Template Presets
async function loadTemplatePresets() {
  const sel = document.getElementById('templatePreset');
  if (!sel) return;

  try {
    const res = await fetch('/api/templates');
    if (!res.ok) {
      throw new Error('Failed to load template presets');
    }
    const data = await res.json();
    TEMPLATE_PRESETS = data.templates || [];

    // Keep the "None" option and add templates
    sel.innerHTML = '<option value="">None (Manual Settings)</option>';
    TEMPLATE_PRESETS.forEach(template => {
      const opt = document.createElement('option');
      opt.value = String(template.id);
      opt.textContent = template.name;
      if (template.description) {
        opt.title = template.description;
      }
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load template presets:', e);
    // Keep the default "None" option
  }
}

// Apply Template Preset
function applyTemplatePreset(templateId) {
  if (!templateId) return;

  const template = TEMPLATE_PRESETS.find(t => t.id === parseInt(templateId));
  if (!template) return;

  // Set page size
  const pageSizeSelect = document.getElementById('pageSize');
  const pageSizeOption = Array.from(pageSizeSelect.options).find(
    opt => opt.dataset.id === String(template.page_size_preset_id)
  );
  if (pageSizeOption) {
    pageSizeSelect.value = pageSizeOption.value;
  }

  // Set orientation
  document.getElementById('orientation').value = template.orientation;

  // Set margins
  if (template.margins) {
    document.getElementById('marginTop').value = template.margins.top || '';
    document.getElementById('marginRight').value = template.margins.right || '';
    document.getElementById('marginBottom').value = template.margins.bottom || '';
    document.getElementById('marginLeft').value = template.margins.left || '';
  }

  // Set line height if specified
  if (template.line_height) {
    document.getElementById('lineHeight').value = template.line_height;
  }

  // Set background color if specified
  if (template.background_color) {
    document.getElementById('background').value = template.background_color;
  }

  // Update units if needed (assuming margins and template use same units)
  if (template.margins && template.margins.unit) {
    document.getElementById('units').value = template.margins.unit;
  }

  toastSuccess(`Applied template: ${template.name}`);
}

// Custom Dropdown Functions
function selectStyle(styleId) {
  SELECTED_STYLE_ID = styleId;
  document.getElementById('styleSelect').value = String(styleId);
  updateSelectedStyle(styleId);
}

function updateSelectedStyle(styleId) {
  const options = document.querySelectorAll('.style-option');
  options.forEach(opt => {
    if (opt.dataset.styleId === String(styleId)) {
      opt.classList.add('selected');
    } else {
      opt.classList.remove('selected');
    }
  });
}

function toggleStyleDropdown() {
  const dropdown = document.getElementById('styleDropdown');
  dropdown.classList.toggle('active');

  // Close on outside click
  if (dropdown.classList.contains('active')) {
    setTimeout(() => {
      document.addEventListener('click', outsideClickHandler);
    }, 0);
  } else {
    document.removeEventListener('click', outsideClickHandler);
  }
}

function closeStyleDropdown() {
  const dropdown = document.getElementById('styleDropdown');
  dropdown.classList.remove('active');
  document.removeEventListener('click', outsideClickHandler);
}

function outsideClickHandler(event) {
  const wrapper = document.getElementById('styleSelectWrapper');
  if (!wrapper.contains(event.target)) {
    closeStyleDropdown();
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

// Copy SVG to Clipboard
function copySvg() {
  if (!lastSvgText) {
    toastError('No SVG to copy. Please generate first.');
    return;
  }
  
  navigator.clipboard.writeText(lastSvgText)
    .then(() => toastSuccess('SVG copied to clipboard'))
    .catch(() => toastError('Failed to copy to clipboard'));
}

// Generate Handwriting
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

  // New spacing and sizing options
  const emptyLineSpacing = document.getElementById('emptyLineSpacing').value;
  const autoSize = document.getElementById('autoSize').checked;
  const manualSizeScale = document.getElementById('manualSizeScale').value;

  // Chunked generation options
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
    // New spacing and sizing options
    empty_line_spacing: emptyLineSpacing ? Number(emptyLineSpacing) : undefined,
    auto_size: autoSize,
    manual_size_scale: manualSizeScale ? Number(manualSizeScale) : undefined,
    // Chunked generation options
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
    makePreviewClickable();
    
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
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 0);
  
  toastSuccess(`Downloaded ${filename}`);
}

// Batch Processing
function clearBatchUI() {
  document.getElementById('batchProg').textContent = '0';
  document.getElementById('batchTotal').textContent = '0';
  document.getElementById('batchOk').textContent = '0';
  document.getElementById('batchErr').textContent = '0';
  document.getElementById('batchLog').innerHTML = '';
  document.getElementById('batchLiveGrid').innerHTML = '';
  document.getElementById('progressFill').style.width = '0%';
  
  const dl = document.getElementById('batchDownload');
  dl.style.display = 'none';
  dl.removeAttribute('href');
  
  document.getElementById('batchContainer').style.display = 'none';
}

async function batchGenerateStream() {
  const file = CSV_FILE || document.getElementById('csv').files[0];
  if (!file) {
    toastError('Please select a CSV file');
    return;
  }
  
  clearBatchUI();
  document.getElementById('batchContainer').style.display = 'block';
  
  const form = new FormData();
  form.append('file', file);
  
  setLoading(true);
  
  try {
    const res = await fetch('/api/batch/stream', {
      method: 'POST',
      body: form
    });
    
    if (!res.ok || !res.body) {
      throw new Error('Failed to start batch processing');
    }
    
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let ok = 0, err = 0, total = 0;
    
    const liveGrid = document.getElementById('batchLiveGrid');
    const liveLimit = () => {
      const el = document.getElementById('liveLimit');
      return Math.max(1, Math.min(50, Number(el?.value) || 12));
    };
    
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
              entry.textContent = `✓ Row ${payload.row}: ${payload.file}`;
              document.getElementById('batchOk').textContent = String(ok);
              
              // Add live preview card
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
              entry.textContent = `✗ Row ${payload.row}: ${payload.error}`;
              document.getElementById('batchErr').textContent = String(err);
            }
            
            log.appendChild(entry);
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
            
            toastSuccess(`Batch processing complete: ${ok} successful, ${err} errors`);
            
            // Load preview SVGs
            const jobId = payload.job_id;
               if (jobId) {
              const cards = Array.from(liveGrid.children);
              for (const card of cards) {
                const fname = card.getAttribute('data-filename');
                if (!fname) continue;
                
                fetch(`/api/batch/result/${jobId}/file/${encodeURIComponent(fname)}`)
                   .then(r => r.text())
                   .then(svg => {
                     const encoded = encodeURIComponent(svg);
                     card.innerHTML = `
                       <div class="live-preview-filename">${fname}</div>
                       <div class="clickable-svg" data-svg="${encoded}">
                         ${svg}
                       </div>
                       <div class="live-preview-status">Complete</div>
                     `;
                     // Add click handler after inserting HTML
                     const svgDiv = card.querySelector('.clickable-svg');
                     svgDiv.addEventListener('click', () => {
                       const raw = decodeURIComponent(svgDiv.getAttribute('data-svg'));
                       openLightbox(raw);
                     });
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
    
    // Auto-start batch processing
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
            if (templateId) {
                applyTemplatePreset(templateId);
            }
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

    // Toggle manual size scale input based on auto size checkbox
    const autoSizeCheckbox = document.getElementById('autoSize');
    const manualSizeScaleInput = document.getElementById('manualSizeScale');
    autoSizeCheckbox.addEventListener('change', () => {
        manualSizeScaleInput.disabled = autoSizeCheckbox.checked;
    });

    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeLightbox();
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
})
