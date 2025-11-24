/**
 * WriteBot Admin Dashboard JavaScript
 * Common interactive features for admin pages
 */

(function () {
  'use strict';

  // ============================================
  // Confirmation Dialogs
  // ============================================

  /**
   * Add confirmation dialog to delete forms.
   * Intercepts form submission and prompts the user for confirmation.
   * Uses the 'data-confirm' attribute for the custom message.
   */
  function initDeleteConfirmations() {
    const deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(form => {
      form.addEventListener('submit', function (e) {
        const message = this.getAttribute('data-confirm') || 'Are you sure you want to delete this item?';
        if (!confirm(message)) {
          e.preventDefault();
          return false;
        }
      });
    });
  }

  /**
   * Add confirmation dialog to delete buttons.
   * Intercepts button click and prompts the user for confirmation.
   * Uses the 'data-confirm-action' attribute for the custom message.
   */
  function initDeleteButtons() {
    const deleteButtons = document.querySelectorAll('[data-confirm-action]');
    deleteButtons.forEach(button => {
      button.addEventListener('click', function (e) {
        const message = this.getAttribute('data-confirm-action') || 'Are you sure you want to perform this action?';
        if (!confirm(message)) {
          e.preventDefault();
          return false;
        }
      });
    });
  }

  // ============================================
  // Table Enhancements
  // ============================================

  /**
   * Add hover effect highlighting to table rows.
   * Adds a pointer cursor to indicate interactivity.
   */
  function initTableHighlighting() {
    const tables = document.querySelectorAll('.admin-table');
    tables.forEach(table => {
      const rows = table.querySelectorAll('tbody tr');
      rows.forEach(row => {
        row.addEventListener('mouseenter', function () {
          this.style.cursor = 'pointer';
        });
      });
    });
  }

  /**
   * Enable table sorting (basic implementation).
   * Adds sorting functionality to table headers with the 'data-sortable' attribute.
   * Supports numeric and string sorting in ascending and descending order.
   */
  function initTableSorting() {
    const sortableHeaders = document.querySelectorAll('[data-sortable]');
    sortableHeaders.forEach(header => {
      header.style.cursor = 'pointer';
      header.addEventListener('click', function () {
        const table = this.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(this.parentElement.children).indexOf(this);
        const currentOrder = this.getAttribute('data-order') || 'asc';
        const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

        rows.sort((a, b) => {
          const aValue = a.children[columnIndex].textContent.trim();
          const bValue = b.children[columnIndex].textContent.trim();

          if (!isNaN(aValue) && !isNaN(bValue)) {
            return newOrder === 'asc'
              ? parseFloat(aValue) - parseFloat(bValue)
              : parseFloat(bValue) - parseFloat(aValue);
          }

          return newOrder === 'asc'
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue);
        });

        rows.forEach(row => tbody.appendChild(row));
        this.setAttribute('data-order', newOrder);

        // Update visual indicator
        sortableHeaders.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
        this.classList.add(`sorted-${newOrder}`);
      });
    });
  }

  // ============================================
  // Auto-dismiss Alerts
  // ============================================

  /**
   * Auto-dismiss success alerts after a delay.
   * Success alerts will fade out and be removed from the DOM after 5 seconds.
   */
  function initAutoDismissAlerts() {
    const successAlerts = document.querySelectorAll('.alert-success');
    successAlerts.forEach(alert => {
      setTimeout(() => {
        alert.style.transition = 'opacity 0.5s ease';
        alert.style.opacity = '0';
        setTimeout(() => {
          alert.remove();
        }, 500);
      }, 5000); // Dismiss after 5 seconds
    });
  }

  // ============================================
  // Form Validation Helpers
  // ============================================

  /**
   * Add real-time validation feedback to forms.
   * Validates required fields on blur and on form submission.
   * Displays error messages below invalid inputs.
   */
  function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
      const requiredInputs = form.querySelectorAll('[required]');

      requiredInputs.forEach(input => {
        input.addEventListener('blur', function () {
          validateInput(this);
        });

        input.addEventListener('input', function () {
          if (this.classList.contains('is-invalid')) {
            validateInput(this);
          }
        });
      });

      form.addEventListener('submit', function (e) {
        let isValid = true;
        requiredInputs.forEach(input => {
          if (!validateInput(input)) {
            isValid = false;
          }
        });

        if (!isValid) {
          e.preventDefault();
          const firstInvalid = form.querySelector('.is-invalid');
          if (firstInvalid) {
            firstInvalid.focus();
          }
        }
      });
    });
  }

  /**
   * Validate a single input field.
   * @param {HTMLElement} input - The input element to validate.
   * @returns {boolean} - True if valid, False otherwise.
   */
  function validateInput(input) {
    const value = input.value.trim();
    const isValid = value !== '';

    if (isValid) {
      input.classList.remove('is-invalid');
      input.classList.add('is-valid');
      removeErrorMessage(input);
    } else {
      input.classList.remove('is-valid');
      input.classList.add('is-invalid');
      showErrorMessage(input, 'This field is required');
    }

    return isValid;
  }

  /**
   * Show an error message for an input.
   * @param {HTMLElement} input - The input element.
   * @param {string} message - The error message to display.
   */
  function showErrorMessage(input, message) {
    removeErrorMessage(input);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'form-error';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
  }

  /**
   * Remove the error message for an input.
   * @param {HTMLElement} input - The input element.
   */
  function removeErrorMessage(input) {
    const existingError = input.parentNode.querySelector('.form-error');
    if (existingError) {
      existingError.remove();
    }
  }

  // ============================================
  // Tooltips
  // ============================================

  /**
   * Initialize tooltips for elements with data-tooltip attribute.
   * Creates a tooltip element on mouseenter and removes it on mouseleave.
   */
  function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
      element.style.position = 'relative';
      element.style.cursor = 'help';

      element.addEventListener('mouseenter', function () {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = this.getAttribute('data-tooltip');
        tooltip.style.cssText = `
          position: absolute;
          bottom: 100%;
          left: 50%;
          transform: translateX(-50%);
          background: #161616;
          color: white;
          padding: 8px 12px;
          border-radius: 4px;
          font-size: 12px;
          white-space: nowrap;
          z-index: 1000;
          margin-bottom: 8px;
        `;
        this.appendChild(tooltip);
      });

      element.addEventListener('mouseleave', function () {
        const tooltip = this.querySelector('.tooltip');
        if (tooltip) {
          tooltip.remove();
        }
      });
    });
  }

  // ============================================
  // Search/Filter Tables
  // ============================================

  /**
   * Add search functionality to tables.
   * Links a search input (with 'data-table-search' attribute) to a table.
   * Filters rows in real-time based on text content.
   */
  function initTableSearch() {
    const searchInputs = document.querySelectorAll('[data-table-search]');
    searchInputs.forEach(input => {
      const tableId = input.getAttribute('data-table-search');
      const table = document.getElementById(tableId);
      if (!table) return;

      const tbody = table.querySelector('tbody');
      const rows = tbody.querySelectorAll('tr');

      input.addEventListener('input', function () {
        const searchTerm = this.value.toLowerCase();

        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
      });
    });
  }

  // ============================================
  // Statistics Animation
  // ============================================

  /**
   * Animate stat card numbers on page load.
   * Counts up from 0 to the final value for elements with class 'stat-card__value'.
   */
  function initStatAnimations() {
    const statValues = document.querySelectorAll('.stat-card__value');
    statValues.forEach(stat => {
      const finalValue = parseInt(stat.textContent.replace(/,/g, ''));
      if (isNaN(finalValue)) return;

      let currentValue = 0;
      const increment = Math.ceil(finalValue / 50);
      const duration = 1000;
      const stepTime = duration / (finalValue / increment);

      const timer = setInterval(() => {
        currentValue += increment;
        if (currentValue >= finalValue) {
          currentValue = finalValue;
          clearInterval(timer);
        }
        stat.textContent = currentValue.toLocaleString();
      }, stepTime);
    });
  }

  // ============================================
  // Clipboard Copy
  // ============================================

  /**
   * Copy text to clipboard when clicking elements with data-copy attribute.
   * Provides visual feedback upon successful copy.
   */
  function initClipboardCopy() {
    const copyElements = document.querySelectorAll('[data-copy]');
    copyElements.forEach(element => {
      element.style.cursor = 'pointer';
      element.addEventListener('click', function () {
        const textToCopy = this.getAttribute('data-copy');
        navigator.clipboard.writeText(textToCopy).then(() => {
          // Show feedback
          const originalText = this.textContent;
          this.textContent = 'Copied!';
          setTimeout(() => {
            this.textContent = originalText;
          }, 2000);
        });
      });
    });
  }

  // ============================================
  // Initialize All Features
  // ============================================

  /**
   * Main initialization function.
   * Checks DOM readiness and calls feature initializers.
   */
  function init() {
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    // Initialize all features
    initDeleteConfirmations();
    initDeleteButtons();
    initTableHighlighting();
    initTableSorting();
    initAutoDismissAlerts();
    initFormValidation();
    initTooltips();
    initTableSearch();
    initStatAnimations();
    initClipboardCopy();

    console.log('WriteBot Admin JS initialized');
  }

  // Run initialization
  init();

})();
