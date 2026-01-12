/**
 * Alpine.js Data Store for Generation Page
 * Main application state and methods
 */

document.addEventListener('alpine:init', () => {
  Alpine.data('generationApp', () => ({
    // State
    text: '',
    loading: false,
    lastSvgText: '',
    lastMetadata: {},

    // Styles
    styles: [],
    selectedStyleId: null,
    styleDropdownOpen: false,

    // Collections and presets
    characterOverrideCollections: [],
    pageSizePresets: [],
    templatePresets: [],

    // Page settings
    pageSize: '',
    orientation: 'portrait',
    units: 'mm',
    align: 'left',
    background: '',

    // Margins
    marginTop: '',
    marginRight: '',
    marginBottom: '',
    marginLeft: '',

    // Layout settings
    lineHeight: '',
    emptyLineSpacing: '',
    globalScale: '',
    autoSize: true,
    manualSizeScale: '',

    // Custom size
    pageWidth: '',
    pageHeight: '',

    // Style options
    legibility: 'normal',
    characterOverrideCollection: '',
    biases: '',
    perLineStyles: '',
    strokeColors: '',
    strokeWidths: '',
    xStretch: '',
    denoise: 'true',

    // Margin jitter (natural handwriting variation)
    marginJitterFrac: '',
    marginJitterCoherence: '',

    // Text wrapping
    wrapCharPx: '',
    wrapRatio: '',
    wrapUtil: '',

    // Chunked generation
    useChunked: true,
    adaptiveChunking: true,
    adaptiveStrategy: 'balanced',
    wordsPerChunk: '',
    chunkSpacing: '',
    maxLineWidth: '',

    // Modals
    savePresetModalOpen: false,
    batchPreviewModalOpen: false,
    presetName: '',
    presetDescription: '',
    batchPreviewTitle: '',
    batchPreviewContent: '',

    // Download menu
    downloadMenuOpen: false,

    // Batch processing
    csvFile: null,
    batchContainer: false,
    batchProgress: 0,
    batchTotal: 0,
    batchOk: 0,
    batchErr: 0,
    batchLog: 'Ready to process batch...',
    batchDownloadUrl: '',
    batchLiveItems: [],
    autoStartBatch: false,
    liveLimit: 12,
    batchDropzone: null,

    // Zoom
    zoom: 100,

    // Job Queue
    queueJobTitle: '',
    queuePriority: '3',
    queueIsPrivate: false,
    queueScheduledAt: '',
    queueSubmitting: false,

    // Initialize
    async init() {
      await Promise.all([
        this.loadStyles(),
        this.loadCharacterOverrideCollections(),
        this.loadPageSizePresets(),
        this.loadTemplatePresets()
      ]);

      this.setupKeyboardShortcuts();
      this.checkUrlPreset();

      this.$nextTick(() => {
        if (typeof feather !== 'undefined') feather.replace();
      });
    },

    // Load styles from API
    async loadStyles() {
      try {
        const res = await fetch('/api/styles');
        const data = await res.json();
        this.styles = (data && data.styles) || [];

        if (!this.styles.length) {
          this.styles = Array.from({ length: 13 }, (_, i) => ({ id: i, label: `Style ${i}` }));
        }

        if (this.styles.length > 0) {
          this.selectedStyleId = this.styles[0].id;
        }
      } catch (err) {
        console.error('Failed to load styles:', err);
        toastError('Failed to load styles: ' + err.message);
      }
    },

    // Load character override collections
    async loadCharacterOverrideCollections() {
      try {
        const res = await fetch('/api/collections');
        const data = await res.json();
        this.characterOverrideCollections = Array.isArray(data) ? data : [];
      } catch (err) {
        console.error('Failed to load character override collections:', err);
      }
    },

    // Load page size presets
    async loadPageSizePresets() {
      try {
        const res = await fetch('/api/page-sizes');
        const data = await res.json();
        this.pageSizePresets = data.page_sizes || [];

        if (this.pageSizePresets.length > 0) {
          this.pageSize = String(this.pageSizePresets[0].id);
        }
      } catch (err) {
        console.error('Failed to load page size presets:', err);
      }
    },

    // Load template presets
    async loadTemplatePresets() {
      try {
        const res = await fetch('/api/templates');
        const data = await res.json();
        this.templatePresets = data.templates || [];
      } catch (err) {
        console.error('Failed to load template presets:', err);
      }
    },

    // Select a style
    selectStyle(styleId) {
      this.selectedStyleId = styleId;
      this.styleDropdownOpen = false;
    },

    // Check if custom size fields should be visible
    get showCustomSize() {
      return this.pageSize === 'custom';
    },

    // Get page size name from preset ID
    resolvePageSize() {
      if (this.pageSize === 'custom') return 'custom';
      const preset = this.pageSizePresets.find(p => String(p.id) === String(this.pageSize));
      return preset ? preset.name : 'A4';
    },

    // Get page dimensions
    getPageDimensions() {
      if (this.pageSize === 'custom') {
        return {
          width: this.pageWidth ? Number(this.pageWidth) : null,
          height: this.pageHeight ? Number(this.pageHeight) : null,
          unit: this.units
        };
      }

      const preset = this.pageSizePresets.find(p => String(p.id) === String(this.pageSize));
      if (preset) {
        const predefinedSizes = ['A4', 'A5', 'Letter', 'Legal'];
        if (predefinedSizes.includes(preset.name)) {
          return { width: null, height: null, unit: null };
        }
        return {
          width: preset.width,
          height: preset.height,
          unit: preset.unit || 'mm'
        };
      }

      return { width: null, height: null, unit: null };
    },

    // Build margins object
    buildMargins() {
      const toNum = v => (v === '' || v === null || v === undefined) ? null : Number(v);
      const t = toNum(this.marginTop);
      const r = toNum(this.marginRight);
      const b = toNum(this.marginBottom);
      const l = toNum(this.marginLeft);

      if (t === null && r === null && b === null && l === null) return undefined;
      return { top: t ?? 20, right: r ?? 20, bottom: b ?? 20, left: l ?? 20 };
    },

    // Parse pipe-separated list
    parseList(s, cast) {
      return s ? s.split('|').map(v => cast(v.trim())) : undefined;
    },

    // Generate handwriting
    async generate() {
      if (!this.text.trim()) {
        toastError('Please enter some text');
        return;
      }

      const pageDimensions = this.getPageDimensions();
      const stylesList = this.perLineStyles
        ? this.parseList(this.perLineStyles, Number)
        : (this.selectedStyleId !== null ? [Number(this.selectedStyleId)] : undefined);

      const payload = {
        text: this.text,
        page_size: this.resolvePageSize(),
        units: this.units,
        margins: this.buildMargins(),
        line_height: this.lineHeight ? Number(this.lineHeight) : undefined,
        align: this.align,
        background: this.background || undefined,
        orientation: this.orientation,
        legibility: this.legibility,
        character_override_collection_id: this.characterOverrideCollection ? Number(this.characterOverrideCollection) : undefined,
        global_scale: this.globalScale ? Number(this.globalScale) : undefined,
        page_width: pageDimensions.width || undefined,
        page_height: pageDimensions.height || undefined,
        biases: this.parseList(this.biases, Number),
        styles: stylesList,
        stroke_colors: this.parseList(this.strokeColors, String),
        stroke_widths: this.parseList(this.strokeWidths, Number),
        wrap_char_px: this.wrapCharPx ? Number(this.wrapCharPx) : undefined,
        wrap_ratio: this.wrapRatio ? Number(this.wrapRatio) : undefined,
        wrap_utilization: this.wrapUtil ? Number(this.wrapUtil) : undefined,
        x_stretch: this.xStretch ? Number(this.xStretch) : undefined,
        denoise: this.denoise || undefined,
        margin_jitter_frac: this.marginJitterFrac ? Number(this.marginJitterFrac) : undefined,
        margin_jitter_coherence: this.marginJitterCoherence ? Number(this.marginJitterCoherence) : undefined,
        empty_line_spacing: this.emptyLineSpacing ? Number(this.emptyLineSpacing) : undefined,
        auto_size: this.autoSize,
        manual_size_scale: (!this.autoSize && this.manualSizeScale) ? Number(this.manualSizeScale) : undefined,
        use_chunked: this.useChunked,
        adaptive_chunking: this.adaptiveChunking,
        adaptive_strategy: this.adaptiveStrategy || undefined,
        words_per_chunk: this.wordsPerChunk ? Number(this.wordsPerChunk) : undefined,
        chunk_spacing: this.chunkSpacing ? Number(this.chunkSpacing) : undefined,
        max_line_width: this.maxLineWidth ? Number(this.maxLineWidth) : undefined,
      };

      this.loading = true;

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
        this.lastSvgText = data.svg;
        this.lastMetadata = data.meta || {};

        // Update SVG preview using ref for reliable rendering
        this.$nextTick(() => {
          if (this.$refs.svgPreview && this.lastSvgText) {
            this.$refs.svgPreview.innerHTML = this.lastSvgText;
          }
        });

        if (typeof updateRulerForSVG === 'function') {
          updateRulerForSVG(this.lastSvgText, this.lastMetadata);
        }

        // Show generation time in success message
        const genTime = this.lastMetadata.generation_time_seconds;
        const timeStr = genTime ? ` in ${genTime.toFixed(2)}s` : '';
        toastSuccess(`Handwriting generated successfully${timeStr}`);
      } catch (error) {
        toastError(error.message);
      } finally {
        this.loading = false;
      }
    },

    // Get formatted metadata
    get metadataInfo() {
      if (!this.lastMetadata || Object.keys(this.lastMetadata).length === 0) {
        return 'Generate handwriting to view metadata';
      }
      const lines = this.lastMetadata.lines || {};
      const page = this.lastMetadata.page || {};
      const genTime = this.lastMetadata.generation_time_seconds;
      const timeStr = genTime ? ` | Generated in ${genTime.toFixed(2)}s` : '';
      return `Lines: ${lines.wrapped_count || 0} (from ${lines.input_count || 0} input) | Page: ${page.width_mm || 0}×${page.height_mm || 0}mm | Orientation: ${page.orientation || 'portrait'}${timeStr}`;
    },

    // Download as specified format using svg-exportJS (UMD standalone)
    async downloadAs(format = 'svg') {
      if (!this.lastSvgText) {
        toastError('Please generate handwriting first');
        return;
      }

      // Check if svg-exportJS library is loaded
      if (!window.svgExport) {
        toastError('Export library not loaded. Please refresh the page.');
        return;
      }

      try {
        this.loading = true;
        this.downloadMenuOpen = false;

        const filename = 'handwriting';

        // Parse SVG string to element for svg-exportJS
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(this.lastSvgText, 'image/svg+xml');
        const svgElement = svgDoc.documentElement;

        // Check for parsing errors
        const parserError = svgDoc.querySelector('parsererror');
        if (parserError) {
          throw new Error('Failed to parse SVG: ' + parserError.textContent);
        }

        // Get page dimensions from metadata for better quality
        const options = {
          useCSS: true,
          scale: 2  // 2x for better raster quality
        };

        if (this.lastMetadata && this.lastMetadata.page) {
          const page = this.lastMetadata.page;
          // Use pixel dimensions for raster formats (96 DPI)
          const PX_PER_MM = 96.0 / 25.4;
          options.width = (page.width_mm || 210) * PX_PER_MM;
          options.height = (page.height_mm || 297) * PX_PER_MM;
        }

        // Call the appropriate export function based on format
        switch (format.toLowerCase()) {
          case 'svg':
            await svgExport.downloadSvg(svgElement, filename, options);
            break;
          case 'png':
            await svgExport.downloadPng(svgElement, filename, options);
            break;
          case 'jpeg':
          case 'jpg':
            await svgExport.downloadJpeg(svgElement, filename, {
              ...options,
              transparentBackgroundReplace: 'white'
            });
            break;
          case 'pdf':
            await svgExport.downloadPdf(svgElement, filename, {
              ...options,
              pdfOptions: {
                pageLayout: { margin: 20 },
                addTitleToPage: false
              }
            });
            break;
          default:
            throw new Error(`Unsupported export format: ${format}`);
        }

        const formatLabels = {
          svg: 'SVG',
          png: 'PNG',
          jpeg: 'JPEG',
          pdf: 'PDF'
        };

        toastSuccess(`${formatLabels[format] || format.toUpperCase()} downloaded successfully`);
      } catch (error) {
        console.error(`Error exporting to ${format}:`, error);
        toastError(`Failed to export as ${format}: ${error.message}`);
      } finally {
        this.loading = false;
      }
    },

    // Legacy method aliases for backward compatibility
    downloadSVG() {
      return this.downloadAs('svg');
    },

    downloadPDF() {
      return this.downloadAs('pdf');
    },

    // Copy SVG to clipboard
    copySvg() {
      if (!this.lastSvgText) {
        toastError('No SVG to copy. Generate handwriting first.');
        return;
      }

      navigator.clipboard.writeText(this.lastSvgText)
        .then(() => toastSuccess('SVG copied to clipboard'))
        .catch(() => toastError('Failed to copy to clipboard'));
    },

    // Apply template preset
    async applyTemplatePreset(templateId) {
      if (!templateId) return;

      try {
        const res = await fetch(`/api/templates/${templateId}`);
        const data = await res.json();
        const template = data.template;

        if (template.text) this.text = template.text;
        if (template.style !== undefined) this.selectedStyleId = template.style;
        if (template.legibility) this.legibility = template.legibility;
        if (template.page_size) this.pageSize = template.page_size;
        if (template.orientation) this.orientation = template.orientation;
        if (template.units) this.units = template.units;
        if (template.align) this.align = template.align;

        if (template.margins) {
          if (template.margins.top !== undefined) this.marginTop = template.margins.top;
          if (template.margins.right !== undefined) this.marginRight = template.margins.right;
          if (template.margins.bottom !== undefined) this.marginBottom = template.margins.bottom;
          if (template.margins.left !== undefined) this.marginLeft = template.margins.left;
        }

        if (template.line_height) this.lineHeight = template.line_height;
        if (template.background) this.background = template.background;

        toastSuccess(`Applied template: ${template.name || 'Template'}`);
      } catch (err) {
        console.error('Failed to apply template preset:', err);
        toastError('Failed to apply template preset');
      }
    },

    // Save preset
    async savePreset() {
      if (!this.presetName.trim()) {
        toastError('Please enter a template name');
        return;
      }

      if (this.pageSize === 'custom') {
        toastError('Cannot save template with custom page size. Please select a predefined page size.');
        return;
      }

      const templateData = {
        name: this.presetName.trim(),
        description: this.presetDescription.trim(),
        page_size_preset_id: parseInt(this.pageSize),
        orientation: this.orientation,
        margin_top: parseFloat(this.marginTop) || 10.0,
        margin_right: parseFloat(this.marginRight) || 10.0,
        margin_bottom: parseFloat(this.marginBottom) || 10.0,
        margin_left: parseFloat(this.marginLeft) || 10.0,
        margin_unit: this.units,
        line_height: this.lineHeight ? parseFloat(this.lineHeight) : null,
        line_height_unit: this.units,
        empty_line_spacing: this.emptyLineSpacing ? parseFloat(this.emptyLineSpacing) : null,
        text_alignment: this.align,
        global_scale: parseFloat(this.globalScale) || 1.0,
        auto_size: this.autoSize,
        manual_size_scale: this.manualSizeScale ? parseFloat(this.manualSizeScale) : null,
        background_color: this.background || null,
        biases: this.biases || null,
        per_line_styles: this.perLineStyles || null,
        stroke_colors: this.strokeColors || null,
        stroke_widths: this.strokeWidths || null,
        horizontal_stretch: parseFloat(this.xStretch) || 1.0,
        denoise: this.denoise === 'true',
        character_width: this.wrapCharPx ? parseFloat(this.wrapCharPx) : null,
        wrap_ratio: this.wrapRatio ? parseFloat(this.wrapRatio) : null,
        wrap_utilization: this.wrapUtil ? parseFloat(this.wrapUtil) : null,
        use_chunked_generation: this.useChunked,
        adaptive_chunking: this.adaptiveChunking,
        adaptive_strategy: this.adaptiveStrategy || null,
        words_per_chunk: this.wordsPerChunk ? parseInt(this.wordsPerChunk) : null,
        chunk_spacing: this.chunkSpacing ? parseFloat(this.chunkSpacing) : null,
        max_line_width: this.maxLineWidth ? parseFloat(this.maxLineWidth) : null
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
          this.savePresetModalOpen = false;
          this.presetName = '';
          this.presetDescription = '';
          await this.loadTemplatePresets();
        } else {
          toastError(result.error || 'Failed to save template');
        }
      } catch (err) {
        console.error('Failed to save template preset:', err);
        toastError('Failed to save template preset');
      }
    },

    // Initialize batch upload Dropzone
    initBatchDropzone() {
      if (this.batchDropzone) return;

      this.batchDropzone = new Dropzone('#csvDropzoneForm', {
        url: '/api/batch/upload-preview',  // Placeholder URL (we don't auto-upload)
        autoProcessQueue: false,
        maxFiles: 1,
        maxFilesize: 10, // MB
        acceptedFiles: '.csv,.xlsx',
        addRemoveLinks: true,
        dictDefaultMessage: '',
        dictRemoveFile: 'Remove',
        dictFileTooBig: 'File is too big ({{filesize}}MB). Max filesize: {{maxFilesize}}MB.',
        dictInvalidFileType: 'Only CSV and XLSX files are allowed.',
        init: function() {
          this.on('addedfile', function() {
            // Remove previous files (keep only latest)
            if (this.files.length > 1) {
              this.removeFile(this.files[0]);
            }
            // Reinitialize feather icons for new elements
            if (typeof feather !== 'undefined') {
              feather.replace();
            }
          });
        }
      });

      this.batchDropzone.on('addedfile', (file) => {
        this.csvFile = file;
        if (this.autoStartBatch) {
          this.batchGenerateStream();
        }
      });

      this.batchDropzone.on('removedfile', () => {
        this.csvFile = null;
      });

      this.batchDropzone.on('error', (file, message) => {
        toastError(typeof message === 'string' ? message : 'File upload error');
        this.batchDropzone.removeFile(file);
      });
    },

    // Clear batch UI
    clearBatchUI() {
      this.batchContainer = false;
      this.batchLiveItems = [];
      this.batchLog = 'Ready to process batch...';
      this.batchProgress = 0;
      this.batchTotal = 0;
      this.batchOk = 0;
      this.batchErr = 0;
      this.batchDownloadUrl = '';
    },

    // Batch generate with streaming
    async batchGenerateStream() {
      if (!this.csvFile) {
        toastError('Please select a CSV or XLSX file first');
        return;
      }

      this.clearBatchUI();
      this.batchContainer = true;
      this.loading = true;

      const formData = new FormData();
      formData.append('file', this.csvFile);

      // Add configuration
      formData.append('styles', this.selectedStyleId || '');
      formData.append('legibility', this.legibility);
      formData.append('character_override_collection_id', this.characterOverrideCollection || '');
      formData.append('page_size', this.resolvePageSize());
      formData.append('orientation', this.orientation);
      formData.append('units', this.units);
      formData.append('align', this.align);
      formData.append('background', this.background || '');

      const pageDimensions = this.getPageDimensions();
      if (pageDimensions.width) formData.append('page_width', String(pageDimensions.width));
      if (pageDimensions.height) formData.append('page_height', String(pageDimensions.height));

      formData.append('margin_top', this.marginTop || '');
      formData.append('margin_right', this.marginRight || '');
      formData.append('margin_bottom', this.marginBottom || '');
      formData.append('margin_left', this.marginLeft || '');
      formData.append('line_height', this.lineHeight || '');
      formData.append('empty_line_spacing', this.emptyLineSpacing || '');
      formData.append('global_scale', this.globalScale || '');
      formData.append('auto_size', this.autoSize ? 'true' : 'false');
      formData.append('manual_size_scale', this.manualSizeScale || '');
      formData.append('biases', this.biases || '');
      formData.append('stroke_colors', this.strokeColors || '');
      formData.append('stroke_widths', this.strokeWidths || '');
      formData.append('x_stretch', this.xStretch || '');
      formData.append('denoise', this.denoise || '');
      formData.append('margin_jitter_frac', this.marginJitterFrac || '');
      formData.append('margin_jitter_coherence', this.marginJitterCoherence || '');
      formData.append('wrap_char_px', this.wrapCharPx || '');
      formData.append('wrap_ratio', this.wrapRatio || '');
      formData.append('wrap_utilization', this.wrapUtil || '');
      formData.append('use_chunked', this.useChunked ? 'true' : 'false');
      formData.append('adaptive_chunking', this.adaptiveChunking ? 'true' : 'false');
      formData.append('adaptive_strategy', this.adaptiveStrategy || '');
      formData.append('words_per_chunk', this.wordsPerChunk || '');
      formData.append('chunk_spacing', this.chunkSpacing || '');
      formData.append('max_line_width', this.maxLineWidth || '');

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
                this.batchTotal = payload.total || 0;
                this.batchLog = '='.repeat(70) + '\n';
                this.batchLog += 'WriteBot Batch Processing Log\n';
                this.batchLog += '='.repeat(70) + '\n';
                this.batchLog += `Started at: ${new Date().toLocaleString()}\n`;
                this.batchLog += `Total rows to process: ${this.batchTotal}\n`;
                this.batchLog += '='.repeat(70) + '\n\n';
              } else if (payload.type === 'row') {
                if (payload.status === 'ok') {
                  this.batchOk++;
                  this.batchLog += `[✓] Row ${payload.row}: ${payload.file} - SUCCESS\n`;

                  if (payload.file && this.batchLiveItems.length < this.liveLimit) {
                    this.batchLiveItems.unshift({
                      filename: payload.file,
                      preview_url: payload.preview_url,  // Signed URL from server
                      status: 'generating',
                      svg: null
                    });
                  }
                } else {
                  this.batchErr++;
                  this.batchLog += `[✗] Row ${payload.row}: ERROR - ${payload.error}\n`;
                }
              } else if (payload.type === 'progress') {
                this.batchProgress = payload.completed || 0;
              } else if (payload.type === 'done') {
                this.batchDownloadUrl = payload.download;

                this.batchLog += '\n' + '='.repeat(70) + '\n';
                this.batchLog += 'Processing Complete\n';
                this.batchLog += '='.repeat(70) + '\n';
                this.batchLog += `Completed at: ${new Date().toLocaleString()}\n`;
                this.batchLog += `Total processed: ${payload.total}\n`;
                this.batchLog += `Successful: ${payload.success} (${((payload.success/payload.total)*100).toFixed(1)}%)\n`;
                this.batchLog += `Errors: ${payload.errors}\n`;
                this.batchLog += '='.repeat(70);

                toastSuccess(`Batch processing complete: ${this.batchOk} successful, ${this.batchErr} errors`);

                // Fetch SVG previews using signed URLs
                for (const item of this.batchLiveItems) {
                  if (item.preview_url) {
                    try {
                      const svgRes = await fetch(item.preview_url);
                      if (svgRes.ok) {
                        item.svg = await svgRes.text();
                        item.status = 'complete';
                      } else {
                        item.status = 'error';
                      }
                    } catch (e) {
                      item.status = 'error';
                    }
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
        this.loading = false;
      }
    },

    // Add batch job to queue (non-blocking - job processes in background on server)
    async addToQueue() {
      if (!this.csvFile) {
        toastError('Please select a CSV or XLSX file first');
        return;
      }

      if (this.queueSubmitting) {
        return; // Prevent double submission
      }

      this.queueSubmitting = true;

      try {
        const formData = new FormData();
        formData.append('file', this.csvFile);
        formData.append('title', this.queueJobTitle || this.csvFile.name || 'Batch Job');
        formData.append('priority', this.queuePriority);
        formData.append('is_private', this.queueIsPrivate ? 'true' : 'false');

        if (this.queueScheduledAt) {
          formData.append('scheduled_at', new Date(this.queueScheduledAt).toISOString());
        }

        // Build parameters JSON with current form settings
        const pageDimensions = this.getPageDimensions();
        const params = {
          styles: this.selectedStyleId,
          legibility: this.legibility,
          character_override_collection_id: this.characterOverrideCollection || null,
          page_size: this.resolvePageSize(),
          orientation: this.orientation,
          units: this.units,
          align: this.align,
          background: this.background || null,
          page_width: pageDimensions.width || null,
          page_height: pageDimensions.height || null,
          margin_top: this.marginTop || null,
          margin_right: this.marginRight || null,
          margin_bottom: this.marginBottom || null,
          margin_left: this.marginLeft || null,
          line_height: this.lineHeight || null,
          empty_line_spacing: this.emptyLineSpacing || null,
          global_scale: this.globalScale || null,
          auto_size: this.autoSize,
          manual_size_scale: this.manualSizeScale || null,
          biases: this.biases || null,
          stroke_colors: this.strokeColors || null,
          stroke_widths: this.strokeWidths || null,
          x_stretch: this.xStretch || null,
          denoise: this.denoise,
          margin_jitter_frac: this.marginJitterFrac || null,
          margin_jitter_coherence: this.marginJitterCoherence || null,
          wrap_char_px: this.wrapCharPx || null,
          wrap_ratio: this.wrapRatio || null,
          wrap_utilization: this.wrapUtil || null,
          use_chunked: this.useChunked,
          adaptive_chunking: this.adaptiveChunking,
          adaptive_strategy: this.adaptiveStrategy || null,
          words_per_chunk: this.wordsPerChunk || null,
          chunk_spacing: this.chunkSpacing || null,
          max_line_width: this.maxLineWidth || null
        };
        formData.append('parameters', JSON.stringify(params));

        const res = await fetch('/jobs/api/jobs', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();

        if (res.ok) {
          const jobTitle = this.queueJobTitle || this.csvFile.name || 'Batch Job';
          const scheduledMsg = this.queueScheduledAt ? ' (scheduled)' : '';
          toastSuccess(`Job "${jobTitle}" added to queue${scheduledMsg}`);
          // Reset queue options
          this.queueJobTitle = '';
          this.queueScheduledAt = '';
          this.queueIsPrivate = false;
          // Clear file selection after successful queue
          this.csvFile = null;
          // Reset file input if exists
          const fileInput = document.getElementById('csvFile');
          if (fileInput) fileInput.value = '';
          // Clear the dropzone if it exists
          const dropzone = document.getElementById('csvDropzoneForm');
          if (dropzone && dropzone.dropzone) {
            dropzone.dropzone.removeAllFiles(true);
          }
        } else {
          toastError(data.error || 'Failed to add job to queue');
        }
      } catch (error) {
        console.error('Failed to add job to queue:', error);
        toastError('Failed to add job to queue: ' + error.message);
      } finally {
        this.queueSubmitting = false;
      }
    },

    // Open batch preview modal
    openBatchPreview(filename, svgContent) {
      this.batchPreviewTitle = filename;
      this.batchPreviewContent = svgContent;
      this.batchPreviewModalOpen = true;

      // Update batch preview SVG using ref for reliable rendering
      this.$nextTick(() => {
        if (this.$refs.batchPreviewSvg && svgContent) {
          this.$refs.batchPreviewSvg.innerHTML = svgContent;
        }
      });
    },

    // Get progress percentage
    get progressPercent() {
      return this.batchTotal > 0 ? (this.batchProgress / this.batchTotal) * 100 : 0;
    },

    // Keyboard shortcuts
    setupKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.styleDropdownOpen = false;
          this.downloadMenuOpen = false;
          this.savePresetModalOpen = false;
          this.batchPreviewModalOpen = false;
        }
        if (e.ctrlKey || e.metaKey) {
          if (e.key === 'Enter') {
            e.preventDefault();
            this.generate();
          } else if (e.key === 's') {
            e.preventDefault();
            this.downloadSVG();
          }
        }
      });
    },

    // Check URL for preset parameter
    checkUrlPreset() {
      const urlParams = new URLSearchParams(window.location.search);
      const presetId = urlParams.get('preset');
      if (presetId) {
        setTimeout(() => this.applyTemplatePreset(presetId), 500);
      }
    },

    // Update zoom
    updateZoom() {
      // Directly apply transform to preview element (bypasses Alpine binding issues)
      const preview = document.getElementById('preview');
      if (preview) {
        preview.style.transform = `scale(${this.zoom / 100})`;
        preview.style.transformOrigin = 'top left';
      }

      // Update ruler zoom
      if (typeof window.svgRulerInstance !== 'undefined' && window.svgRulerInstance) {
        window.svgRulerInstance.zoom = this.zoom / 100;
        window.svgRulerInstance.drawRulers();
      }
    }
  }));
});

// Close dropdowns when clicking outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('.style-dropdown-wrapper')) {
    const dropdown = document.getElementById('styleDropdown');
    if (dropdown) dropdown.classList.remove('active');
  }
});

// Re-initialize feather icons after Alpine updates the DOM
document.addEventListener('alpine:initialized', () => {
  if (typeof feather !== 'undefined') {
    feather.replace();
  }
});
