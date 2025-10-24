/**
 * Character Drawer Module
 * Uses @svg-drawing/core library for professional SVG drawing interface
 * Generates pen-plotter-compatible stroke-based SVG characters
 */

const CharacterDrawer = (function() {
    let drawing;
    let collectionId;

    /**
     * Initialize the character drawer using @svg-drawing/core
     */
    function init(collId) {
        collectionId = collId;

        // Check if library is loaded
        if (typeof SVGDCore === 'undefined') {
            console.error('@svg-drawing/core library not loaded');
            return;
        }

        const container = document.getElementById('draw-area');
        if (!container) {
            console.error('Draw area element not found');
            return;
        }

        // Initialize SVG drawing with pen plotter compatible settings
        drawing = new SVGDCore.SvgDrawing(container, {
            width: 200,
            height: 300,
            penColor: '#000000',
            penWidth: 3,
            fill: 'none',  // Critical for pen plotter compatibility!
            close: false,
            curve: false   // Use straight lines for better plotter control
        });

        attachEventListeners();
    }

    /**
     * Attach event listeners for controls
     */
    function attachEventListeners() {
        // Control buttons
        document.getElementById('clear-canvas').addEventListener('click', clearCanvas);
        document.getElementById('undo-stroke').addEventListener('click', undoStroke);
        document.getElementById('save-drawing').addEventListener('click', saveDrawing);

        // Stroke width change - update drawing settings
        document.getElementById('draw-stroke-width').addEventListener('change', updateStrokeWidth);
    }

    /**
     * Update stroke width in drawing instance
     */
    function updateStrokeWidth() {
        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;
        if (drawing) {
            drawing.penWidth = strokeWidth;
        }
    }

    /**
     * Clear the drawing
     */
    function clearCanvas() {
        if (drawing) {
            drawing.clear();
        }
    }

    /**
     * Undo the last stroke
     */
    function undoStroke() {
        if (drawing) {
            drawing.undo();
        }
    }

    /**
     * Convert drawing to pen-plotter-compatible SVG
     */
    function drawingToSVG() {
        if (!drawing) {
            return null;
        }

        // Get the SVG object from the drawing
        const svgObj = drawing.getSvgObject();

        if (!svgObj.paths || svgObj.paths.length === 0) {
            return null;
        }

        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;

        // Build pen-plotter-compatible SVG with stroke-based paths
        let svgPaths = '';

        svgObj.paths.forEach(path => {
            // Ensure we're using stroke, not fill (critical for pen plotter!)
            const pathAttrs = Object.entries(path)
                .filter(([key]) => key !== 'd')
                .map(([key, value]) => `${key}="${value}"`)
                .join(' ');

            // Override to ensure stroke-based rendering
            svgPaths += `  <path d="${path.d}" stroke="black" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>\n`;
        });

        const svgData = `<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 ${svgObj.width} ${svgObj.height}" xmlns="http://www.w3.org/2000/svg">
${svgPaths}</svg>`;

        return svgData;
    }

    /**
     * Save the drawing as a character override
     */
    async function saveDrawing() {
        const character = document.getElementById('draw-character').value;
        const baselineOffset = parseFloat(document.getElementById('draw-baseline-offset').value) || 0;

        // Validation
        if (!character || character.length !== 1) {
            alert('Please enter exactly one character.');
            return;
        }

        if (!drawing) {
            alert('Drawing not initialized.');
            return;
        }

        const svgObj = drawing.getSvgObject();
        if (!svgObj.paths || svgObj.paths.length === 0) {
            alert('Please draw something first!');
            return;
        }

        // Convert to pen-plotter-compatible SVG
        const svgData = drawingToSVG();
        if (!svgData) {
            alert('Failed to generate SVG data.');
            return;
        }

        // Create form data
        const formData = new FormData();
        formData.append('character', character);
        formData.append('baseline_offset', baselineOffset);

        // Create a blob from SVG data and append as file
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        formData.append('svg_data', blob, `${character}.svg`);

        // Send to server
        try {
            const response = await fetch(`/admin/character-overrides/${collectionId}/draw`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                alert('Character saved successfully!');
                // Reload page to show the new character
                window.location.reload();
            } else {
                const error = await response.json();
                alert('Error saving character: ' + (error.error || 'Unknown error'));
            }
        } catch (err) {
            console.error('Error saving character:', err);
            alert('Network error: ' + err.message);
        }
    }

    // Public API
    return {
        init: init
    };
})();
