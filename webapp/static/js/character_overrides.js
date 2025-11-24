/**
 * Character Overrides Admin JavaScript
 * Interactive features for managing character override collections
 */

(function () {
  'use strict';

  // ============================================
  // Tab Switching
  // ============================================

  /**
   * Switch between upload tabs (draw/single/batch).
   * Updates the active tab button and toggles the visibility of content sections.
   * @param {string} tab - The ID of the tab to activate.
   */
  function switchTab(tab) {
    // Update tab buttons
    document.querySelectorAll('.upload-tab').forEach(btn => {
      btn.classList.remove('active');
      if (btn.getAttribute('data-tab') === tab) {
        btn.classList.add('active');
      }
    });

    // Update content visibility
    document.querySelectorAll('.upload-content').forEach(content => {
      content.classList.remove('active');
    });

    const targetContent = document.getElementById(tab + '-upload');
    if (targetContent) {
      targetContent.classList.add('active');
    }
  }

  /**
   * Initialize tab switching functionality.
   * Attaches click event listeners to tab buttons.
   */
  function initTabs() {
    const tabs = document.querySelectorAll('.upload-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', function () {
        const tabData = this.getAttribute('data-tab');
        if (tabData) {
          switchTab(tabData);
        } else {
          // Fallback for backward compatibility
          const tabType = this.textContent.toLowerCase().includes('batch') ? 'batch' :
                         this.textContent.toLowerCase().includes('draw') ? 'draw' : 'single';
          switchTab(tabType);
        }
      });
    });
  }

  // ============================================
  // File Upload Preview
  // ============================================

  /**
   * Show file count for multi-file uploads.
   * Updates the label text with the number of selected files.
   */
  function initFileUploadPreview() {
    const multiFileInputs = document.querySelectorAll('input[type="file"][multiple]');

    multiFileInputs.forEach(input => {
      input.addEventListener('change', function () {
        const fileCount = this.files.length;
        const label = this.closest('.form-group').querySelector('label');

        if (label) {
          const originalText = label.getAttribute('data-original-text') || label.textContent;
          if (!label.getAttribute('data-original-text')) {
            label.setAttribute('data-original-text', originalText);
          }

          if (fileCount > 0) {
            label.textContent = `${originalText} (${fileCount} file${fileCount > 1 ? 's' : ''} selected)`;
          } else {
            label.textContent = originalText;
          }
        }
      });
    });

    // Single file upload preview
    const singleFileInputs = document.querySelectorAll('input[type="file"]:not([multiple])');

    singleFileInputs.forEach(input => {
      input.addEventListener('change', function () {
        const fileName = this.files[0]?.name;
        const label = this.closest('.form-group').querySelector('label');

        if (label && fileName) {
          const originalText = label.getAttribute('data-original-text') || label.textContent;
          if (!label.getAttribute('data-original-text')) {
            label.setAttribute('data-original-text', originalText);
          }

          label.textContent = `${originalText} (${fileName})`;
        }
      });
    });
  }

  // ============================================
  // SVG Preview Zoom
  // ============================================

  /**
   * Add click-to-zoom functionality for variant previews.
   * Creates a modal overlay with the zoomed image when an image is clicked.
   */
  function initSVGZoom() {
    const variantPreviews = document.querySelectorAll('.variant-preview');

    variantPreviews.forEach(preview => {
      preview.style.cursor = 'pointer';
      preview.setAttribute('title', 'Click to enlarge');

      preview.addEventListener('click', function () {
        const img = this.querySelector('img');
        if (!img) return;

        // Create modal overlay with improved contrast
        const modal = document.createElement('div');
        modal.className = 'svg-modal-overlay';
        modal.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.95);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
          cursor: pointer;
          animation: fadeIn 0.2s ease-out;
          padding: 20px;
        `;

        // Create white container for better SVG contrast
        const imgContainer = document.createElement('div');
        imgContainer.style.cssText = `
          background: white;
          padding: 40px;
          border-radius: 8px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
          max-width: 90%;
          max-height: 90%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: default;
          animation: scaleIn 0.2s ease-out;
        `;

        // Create zoomed image
        const zoomedImg = document.createElement('img');
        zoomedImg.src = img.src;
        zoomedImg.alt = 'Character SVG Preview';
        zoomedImg.style.cssText = `
          max-width: 800px;
          max-height: 600px;
          width: auto;
          height: auto;
          object-fit: contain;
          image-rendering: -webkit-optimize-contrast;
          image-rendering: crisp-edges;
        `;

        // Add improved close button
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '✕';
        closeBtn.setAttribute('aria-label', 'Close preview');
        closeBtn.style.cssText = `
          position: absolute;
          top: 24px;
          right: 24px;
          background: white;
          color: #161616;
          border: 2px solid #e0e0e0;
          border-radius: 50%;
          width: 44px;
          height: 44px;
          font-size: 24px;
          font-weight: 300;
          line-height: 1;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10001;
        `;

        closeBtn.addEventListener('mouseenter', function () {
          this.style.background = '#f4f4f4';
          this.style.borderColor = '#0f62fe';
          this.style.color = '#0f62fe';
          this.style.transform = 'scale(1.1)';
        });

        closeBtn.addEventListener('mouseleave', function () {
          this.style.background = 'white';
          this.style.borderColor = '#e0e0e0';
          this.style.color = '#161616';
          this.style.transform = 'scale(1)';
        });

        // Add keyboard hint
        const hint = document.createElement('div');
        hint.textContent = 'Press ESC or click anywhere to close';
        hint.style.cssText = `
          position: absolute;
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
          background: rgba(255, 255, 255, 0.95);
          color: #525252;
          padding: 8px 16px;
          border-radius: 4px;
          font-size: 13px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
          pointer-events: none;
        `;

        imgContainer.appendChild(zoomedImg);
        modal.appendChild(imgContainer);
        modal.appendChild(closeBtn);
        modal.appendChild(hint);

        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes scaleIn {
            from { transform: scale(0.9); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
          }
          @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
          }
        `;
        document.head.appendChild(style);

        document.body.appendChild(modal);

        // Prevent body scroll when modal is open
        document.body.style.overflow = 'hidden';

        // Close modal function with fade out animation
        function closeModal() {
          modal.style.animation = 'fadeOut 0.15s ease-out';
          setTimeout(() => {
            if (document.body.contains(modal)) {
              document.body.removeChild(modal);
              document.body.style.overflow = '';
            }
          }, 150);
        }

        // Close on background click
        modal.addEventListener('click', closeModal);

        // Close on close button click
        closeBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          closeModal();
        });

        // Prevent image container click from closing modal
        imgContainer.addEventListener('click', function (e) {
          e.stopPropagation();
        });

        // Close on ESC key (already handled globally, but adding here for redundancy)
        function handleEscape(e) {
          if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', handleEscape);
          }
        }
        document.addEventListener('keydown', handleEscape);
      });
    });
  }


  // ============================================
  // Form Validation
  // ============================================

  /**
   * Validate character input (must be single character).
   * Limits the input length to 1 and provides visual feedback.
   */
  function initCharacterValidation() {
    const characterInputs = document.querySelectorAll('input[name="character"]');

    characterInputs.forEach(input => {
      input.addEventListener('input', function () {
        // Limit to single character
        if (this.value.length > 1) {
          this.value = this.value.charAt(0);
        }

        // Visual feedback
        if (this.value.length === 1) {
          this.style.borderColor = '#24a148';
          this.style.backgroundColor = '#defbe6';
        } else {
          this.style.borderColor = '#da1e28';
          this.style.backgroundColor = '#fff1f1';
        }
      });

      input.addEventListener('blur', function () {
        // Reset background on blur if valid
        if (this.value.length === 1) {
          this.style.backgroundColor = '';
          this.style.borderColor = '#24a148';
        }
      });
    });
  }

  // ============================================
  // Delete Confirmation Enhancement
  // ============================================

  /**
   * Enhanced delete confirmation with character preview.
   * Shows a custom confirmation dialog with details about the variant being deleted.
   */
  function initEnhancedDeleteConfirmation() {
    const deleteForms = document.querySelectorAll('.variant-card form');

    deleteForms.forEach(form => {
      form.addEventListener('submit', function (e) {
        const variantCard = this.closest('.variant-card');
        const characterGroup = this.closest('.character-group');
        const characterBadge = characterGroup?.querySelector('.character-badge');
        const character = characterBadge?.textContent.trim();
        const variantCount = characterGroup?.querySelectorAll('.variant-card').length;

        let message = 'Are you sure you want to delete this variant?';

        if (character) {
          message = `Delete variant for character "${character}"?`;
          if (variantCount === 1) {
            message += '\n\nThis is the only variant for this character. The character will be removed from the collection.';
          }
        }

        if (!confirm(message)) {
          e.preventDefault();
          return false;
        }
      });
    });
  }

  // ============================================
  // Keyboard Shortcuts
  // ============================================

  /**
   * Add keyboard shortcuts for common actions.
   * Ctrl/Cmd + U: Focus file input.
   * Escape: Close modals.
   * 1/2: Switch tabs.
   */
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
      // Ctrl/Cmd + U to focus upload file input
      if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        const fileInput = document.querySelector('.upload-content.active input[type="file"]');
        if (fileInput) {
          fileInput.click();
        }
      }

      // Escape to close any modals
      if (e.key === 'Escape') {
        const modal = document.querySelector('[style*="z-index: 10000"]');
        if (modal) {
          modal.click();
        }
      }

      // Tab 1/2 to switch upload tabs
      if (e.key === '1' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        const singleTab = document.querySelector('.upload-tab');
        if (singleTab) {
          singleTab.click();
        }
      }

      if (e.key === '2' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        const batchTab = document.querySelectorAll('.upload-tab')[1];
        if (batchTab) {
          batchTab.click();
        }
      }
    });
  }

  // ============================================
  // Variant Stats Display
  // ============================================

  /**
   * Display statistics about variants.
   * Updates the section title with total character and variant counts.
   */
  function updateVariantStats() {
    const characterGroups = document.querySelectorAll('.character-group');
    let totalVariants = 0;
    let totalCharacters = characterGroups.length;

    characterGroups.forEach(group => {
      const variants = group.querySelectorAll('.variant-card');
      totalVariants += variants.length;
    });

    // Update page title or add stats display
    const pageTitle = document.querySelector('.characters-section h3');
    if (pageTitle) {
      pageTitle.textContent = `Character Variants (${totalCharacters} characters, ${totalVariants} total variants)`;
    }
  }

  // ============================================
  // Drag and Drop File Upload
  // ============================================

  /**
   * Add drag and drop functionality for file uploads.
   * Highlights the drop zone when dragging files over it.
   */
  function initDragAndDrop() {
    const fileInputs = document.querySelectorAll('input[type="file"]');

    fileInputs.forEach(input => {
      const formGroup = input.closest('.form-group');
      if (!formGroup) return;

      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        formGroup.addEventListener(eventName, preventDefaults, false);
      });

      function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
      }

      ['dragenter', 'dragover'].forEach(eventName => {
        formGroup.addEventListener(eventName, () => {
          formGroup.style.borderColor = '#0f62fe';
          formGroup.style.backgroundColor = '#e8edf7';
        }, false);
      });

      ['dragleave', 'drop'].forEach(eventName => {
        formGroup.addEventListener(eventName, () => {
          formGroup.style.borderColor = '';
          formGroup.style.backgroundColor = '';
        }, false);
      });

      formGroup.addEventListener('drop', function (e) {
        const files = e.dataTransfer.files;
        input.files = files;

        // Trigger change event
        const event = new Event('change', { bubbles: true });
        input.dispatchEvent(event);
      }, false);
    });
  }

  // ============================================
  // Initialize All Features
  // ============================================

  /**
   * Initialize all features on DOMContentLoaded.
   */
  function init() {
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    // Initialize all features
    initTabs();
    initFileUploadPreview();
    initSVGZoom();
    initCharacterValidation();
    initEnhancedDeleteConfirmation();
    initKeyboardShortcuts();
    initDragAndDrop();
    updateVariantStats();

    console.log('Character Overrides JS initialized');
  }

  // Make switchTab available globally for inline onclick handlers (backward compatibility)
  window.switchTab = switchTab;

  // Run initialization
  init();
})();
