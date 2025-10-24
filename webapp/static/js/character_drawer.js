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

        // Check if library is loaded - try multiple possible global names
        const SvgLib = window.SVGDCore || window.svgDrawingCore || window.SvgDrawing;

        if (!SvgLib) {
            console.error('@svg-drawing/core library not loaded');
            console.error('Available window properties:', Object.keys(window).filter(k => k.toLowerCase().includes('svg')));
            return;
        }

        console.log('Found SVG library:', SvgLib);

        const container = document.getElementById('draw-area');
        if (!container) {
            console.error('Draw area element not found');
            return;
        }

        console.log('Initializing SvgDrawing with container:', container);

        try {
            // Initialize SVG drawing (container should have width/height set via CSS)
            drawing = new SvgLib.SvgDrawing(container, {
                width: 200,
                height: 300
            });

            console.log('SvgDrawing instance created:', drawing);

            // Set pen plotter compatible settings after instantiation
            drawing.penColor = '#000000';
            drawing.penWidth = 3;

            attachEventListeners();

            console.log('Character drawer initialized successfully');
        } catch (error) {
            console.error('Error initializing SvgDrawing:', error);
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #da1e28;">Error initializing drawing canvas: ' + error.message + '</div>';
        }
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
     * Calculate bounding box of path data
     */
    function calculateBoundingBox(paths) {
        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        paths.forEach(path => {
            const d = path.getAttribute('d');
            if (!d) return;

            // Extract all numbers from the path data
            // This regex matches numbers (including decimals and negatives)
            const numbers = d.match(/-?\d+\.?\d*/g);
            if (!numbers) return;

            // Process coordinate pairs (x, y)
            for (let i = 0; i < numbers.length - 1; i += 2) {
                const x = parseFloat(numbers[i]);
                const y = parseFloat(numbers[i + 1]);

                if (!isNaN(x) && !isNaN(y)) {
                    minX = Math.min(minX, x);
                    minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x);
                    maxY = Math.max(maxY, y);
                }
            }
        });

        return { minX, minY, maxX, maxY };
    }

    /**
     * Convert drawing to pen-plotter-compatible SVG with auto-crop
     */
    function drawingToSVG() {
        if (!drawing) {
            return null;
        }

        // Get the SVG element from the container
        const container = document.getElementById('draw-area');
        const svgElement = container.querySelector('svg');

        if (!svgElement) {
            console.error('SVG element not found in draw area');
            return null;
        }

        // Get all path elements
        const paths = svgElement.querySelectorAll('path');

        if (paths.length === 0) {
            return null;
        }

        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;

        // Calculate bounding box of all paths
        const bbox = calculateBoundingBox(paths);

        // Add padding around the content (include stroke width in padding)
        const padding = strokeWidth * 2 + 5;
        const viewBoxX = Math.max(0, bbox.minX - padding);
        const viewBoxY = Math.max(0, bbox.minY - padding);
        const viewBoxWidth = (bbox.maxX - bbox.minX) + (padding * 2);
        const viewBoxHeight = (bbox.maxY - bbox.minY) + (padding * 2);

        // Build pen-plotter-compatible SVG with stroke-based paths
        let svgPaths = '';

        paths.forEach(path => {
            const d = path.getAttribute('d');
            if (d) {
                // Override to ensure stroke-based rendering (critical for pen plotter!)
                svgPaths += `  <path d="${d}" stroke="black" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>\n`;
            }
        });

        const svgData = `<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}" xmlns="http://www.w3.org/2000/svg">
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

        // Check if there are any drawn paths
        const container = document.getElementById('draw-area');
        const svgElement = container ? container.querySelector('svg') : null;
        const paths = svgElement ? svgElement.querySelectorAll('path') : [];

        if (paths.length === 0) {
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