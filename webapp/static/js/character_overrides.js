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
   * Switch between upload tabs (draw/single/batch)
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
   * Initialize tab switching functionality
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
   * Show file count for multi-file uploads
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
   * Add click-to-zoom functionality for variant previews
   */
  function initSVGZoom() {
    const variantPreviews = document.querySelectorAll('.variant-preview');

    variantPreviews.forEach(preview => {
      preview.style.cursor = 'pointer';
      preview.addEventListener('click', function () {
        const img = this.querySelector('img');
        if (!img) return;

        // Create modal overlay
        const modal = document.createElement('div');
        modal.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.9);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
          cursor: pointer;
          animation: fadeIn 0.2s ease;
        `;

        // Create zoomed image
        const zoomedImg = document.createElement('img');
        zoomedImg.src = img.src;
        zoomedImg.style.cssText = `
          max-width: 90%;
          max-height: 90%;
          object-fit: contain;
          animation: zoomIn 0.2s ease;
        `;

        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
          position: absolute;
          top: 20px;
          right: 20px;
          background: white;
          color: #161616;
          border: none;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          font-size: 24px;
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
          transition: all 0.2s ease;
        `;

        closeBtn.addEventListener('mouseenter', function () {
          this.style.background = '#da1e28';
          this.style.color = 'white';
        });

        closeBtn.addEventListener('mouseleave', function () {
          this.style.background = 'white';
          this.style.color = '#161616';
        });

        modal.appendChild(zoomedImg);
        modal.appendChild(closeBtn);
        document.body.appendChild(modal);

        // Close on click
        modal.addEventListener('click', function () {
          modal.style.animation = 'fadeOut 0.2s ease';
          setTimeout(() => {
            document.body.removeChild(modal);
          }, 200);
        });

        // Prevent image click from closing modal
        zoomedImg.addEventListener('click', function (e) {
          e.stopPropagation();
        });

        // Add animations
        const style = document.createElement('style');
        style.textContent = `
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
          }
          @keyframes zoomIn {
            from { transform: scale(0.8); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
          }
        `;
        document.head.appendChild(style);
      });
    });
  }

  // ============================================
  // Character Badge Animation
  // ============================================

  /**
   * Add hover animation to character badges
   */
  function initCharacterBadgeAnimation() {
    const badges = document.querySelectorAll('.character-badge');

    badges.forEach(badge => {
      badge.addEventListener('mouseenter', function () {
        this.style.transform = 'rotate(360deg) scale(1.1)';
        this.style.transition = 'transform 0.5s ease';
      });

      badge.addEventListener('mouseleave', function () {
        this.style.transform = 'rotate(0deg) scale(1)';
      });
    });
  }

  // ============================================
  // Form Validation
  // ============================================

  /**
   * Validate character input (must be single character)
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
   * Enhanced delete confirmation with character preview
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
   * Add keyboard shortcuts for common actions
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
   * Display statistics about variants
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
   * Add drag and drop functionality for file uploads
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
    initCharacterBadgeAnimation();
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
