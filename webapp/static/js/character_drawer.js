/**
 * Character Drawer Module
 * Provides a canvas-based drawing interface for creating pen-plotter-compatible
 * character override SVGs.
 */

const CharacterDrawer = (function() {
    let canvas, ctx;
    let isDrawing = false;
    let strokes = [];  // Array of stroke arrays
    let currentStroke = [];  // Current stroke being drawn
    let collectionId;

    /**
     * Initialize the character drawer
     */
    function init(collId) {
        collectionId = collId;
        canvas = document.getElementById('draw-canvas');
        if (!canvas) {
            console.error('Canvas element not found');
            return;
        }

        ctx = canvas.getContext('2d');
        setupCanvas();
        attachEventListeners();
    }

    /**
     * Set up canvas with proper styling
     */
    function setupCanvas() {
        ctx.strokeStyle = '#000000';
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        updateStrokeWidth();
    }

    /**
     * Update stroke width from input
     */
    function updateStrokeWidth() {
        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;
        ctx.lineWidth = strokeWidth;
    }

    /**
     * Attach event listeners for drawing and controls
     */
    function attachEventListeners() {
        // Mouse events
        canvas.addEventListener('mousedown', startDrawing);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDrawing);
        canvas.addEventListener('mouseout', stopDrawing);

        // Touch events
        canvas.addEventListener('touchstart', handleTouchStart, {passive: false});
        canvas.addEventListener('touchmove', handleTouchMove, {passive: false});
        canvas.addEventListener('touchend', stopDrawing, {passive: false});

        // Control buttons
        document.getElementById('clear-canvas').addEventListener('click', clearCanvas);
        document.getElementById('undo-stroke').addEventListener('click', undoStroke);
        document.getElementById('save-drawing').addEventListener('click', saveDrawing);

        // Stroke width change
        document.getElementById('draw-stroke-width').addEventListener('change', updateStrokeWidth);
    }

    /**
     * Get canvas coordinates from mouse event
     */
    function getCanvasCoords(e) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    /**
     * Get canvas coordinates from touch event
     */
    function getTouchCoords(e) {
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches[0];
        return {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top
        };
    }

    /**
     * Start drawing a new stroke
     */
    function startDrawing(e) {
        e.preventDefault();
        isDrawing = true;
        currentStroke = [];
        const coords = getCanvasCoords(e);
        currentStroke.push(coords);

        ctx.beginPath();
        ctx.moveTo(coords.x, coords.y);
    }

    /**
     * Continue drawing the current stroke
     */
    function draw(e) {
        if (!isDrawing) return;
        e.preventDefault();

        const coords = getCanvasCoords(e);
        currentStroke.push(coords);

        ctx.lineTo(coords.x, coords.y);
        ctx.stroke();
    }

    /**
     * Stop drawing and save the current stroke
     */
    function stopDrawing(e) {
        if (!isDrawing) return;
        e.preventDefault();

        isDrawing = false;

        if (currentStroke.length > 0) {
            strokes.push([...currentStroke]);
            currentStroke = [];
        }
    }

    /**
     * Handle touch start
     */
    function handleTouchStart(e) {
        e.preventDefault();
        isDrawing = true;
        currentStroke = [];
        const coords = getTouchCoords(e);
        currentStroke.push(coords);

        ctx.beginPath();
        ctx.moveTo(coords.x, coords.y);
    }

    /**
     * Handle touch move
     */
    function handleTouchMove(e) {
        if (!isDrawing) return;
        e.preventDefault();

        const coords = getTouchCoords(e);
        currentStroke.push(coords);

        ctx.lineTo(coords.x, coords.y);
        ctx.stroke();
    }

    /**
     * Clear the entire canvas and all strokes
     */
    function clearCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        strokes = [];
        currentStroke = [];
    }

    /**
     * Undo the last stroke
     */
    function undoStroke() {
        if (strokes.length === 0) return;

        strokes.pop();
        redrawCanvas();
    }

    /**
     * Redraw all strokes on the canvas
     */
    function redrawCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;
        ctx.lineWidth = strokeWidth;

        strokes.forEach(stroke => {
            if (stroke.length === 0) return;

            ctx.beginPath();
            ctx.moveTo(stroke[0].x, stroke[0].y);

            for (let i = 1; i < stroke.length; i++) {
                ctx.lineTo(stroke[i].x, stroke[i].y);
            }

            ctx.stroke();
        });
    }

    /**
     * Convert strokes to SVG path data
     */
    function strokesToSVG() {
        if (strokes.length === 0) {
            return null;
        }

        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;
        const width = canvas.width;
        const height = canvas.height;

        // Build SVG with stroke-based paths (pen plotter compatible)
        let svgPaths = '';

        strokes.forEach(stroke => {
            if (stroke.length === 0) return;

            let pathData = `M ${stroke[0].x},${stroke[0].y}`;

            for (let i = 1; i < stroke.length; i++) {
                pathData += ` L ${stroke[i].x},${stroke[i].y}`;
            }

            // Create stroke-based path (NOT filled - pen plotter compatible!)
            svgPaths += `  <path d="${pathData}" stroke="black" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>\n`;
        });

        const svgData = `<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
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

        if (strokes.length === 0) {
            alert('Please draw something first!');
            return;
        }

        // Convert to SVG
        const svgData = strokesToSVG();
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
