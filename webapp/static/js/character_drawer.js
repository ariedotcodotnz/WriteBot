/**
 * Character Drawer Module - Canvas API Implementation
 *
 * Built from scratch using HTML5 Canvas for drawing
 * Converts strokes to pen-plotter-compatible SVG format
 * Features auto-cropping and proper viewBox calculation
 */

const CharacterDrawer = (function() {
    let canvas;
    let ctx;
    let isDrawing = false;
    let strokes = []; // Array of strokes, each stroke is an array of points
    let currentStroke = null;
    let collectionId;
    let penWidth = 3;

    // Canvas dimensions
    const CANVAS_WIDTH = 400;
    const CANVAS_HEIGHT = 600;

    /**
     * Initialize the character drawer with HTML5 Canvas
     */
    function init(collId) {
        collectionId = collId;

        const container = document.getElementById('draw-area');
        if (!container) {
            console.error('Draw area element not found');
            return;
        }

        try {
            // Create canvas element
            canvas = document.createElement('canvas');
            canvas.width = CANVAS_WIDTH;
            canvas.height = CANVAS_HEIGHT;
            canvas.style.cursor = 'crosshair';
            canvas.style.touchAction = 'none'; // Prevent scrolling on touch devices
            canvas.style.borderRadius = '4px';

            // Get 2D context
            ctx = canvas.getContext('2d');

            // Set initial canvas style
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.strokeStyle = '#000000';

            // Clear container and add canvas
            container.innerHTML = '';
            container.appendChild(canvas);

            // Clear canvas with white background
            clearCanvas();

            // Attach drawing event listeners
            attachDrawingListeners();
            attachControlListeners();

            console.log('Character drawer initialized successfully with Canvas API');
        } catch (error) {
            console.error('Error initializing Canvas drawing:', error);
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #da1e28;">Error initializing drawing canvas: ' + error.message + '</div>';
        }
    }

    /**
     * Attach event listeners for drawing
     */
    function attachDrawingListeners() {
        // Mouse events
        canvas.addEventListener('mousedown', startDrawing);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDrawing);
        canvas.addEventListener('mouseleave', stopDrawing);

        // Touch events for mobile
        canvas.addEventListener('touchstart', handleTouchStart, { passive: false });
        canvas.addEventListener('touchmove', handleTouchMove, { passive: false });
        canvas.addEventListener('touchend', stopDrawing);
        canvas.addEventListener('touchcancel', stopDrawing);
    }

    /**
     * Get coordinates relative to canvas
     */
    function getCoordinates(event) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = CANVAS_WIDTH / rect.width;
        const scaleY = CANVAS_HEIGHT / rect.height;

        let clientX, clientY;
        if (event.touches && event.touches.length > 0) {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        } else {
            clientX = event.clientX;
            clientY = event.clientY;
        }

        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY
        };
    }

    /**
     * Start drawing a new stroke
     */
    function startDrawing(event) {
        event.preventDefault();
        isDrawing = true;

        const coords = getCoordinates(event);

        // Start new stroke
        currentStroke = [{ x: coords.x, y: coords.y }];

        // Begin canvas path
        ctx.beginPath();
        ctx.moveTo(coords.x, coords.y);
    }

    /**
     * Continue drawing the current stroke
     */
    function draw(event) {
        if (!isDrawing || !currentStroke) return;

        event.preventDefault();
        const coords = getCoordinates(event);

        // Add point to current stroke
        currentStroke.push({ x: coords.x, y: coords.y });

        // Draw line on canvas
        ctx.lineWidth = penWidth;
        ctx.lineTo(coords.x, coords.y);
        ctx.stroke();
    }

    /**
     * Stop drawing and save the stroke
     */
    function stopDrawing(event) {
        if (!isDrawing) return;

        event.preventDefault();
        isDrawing = false;

        if (currentStroke && currentStroke.length > 1) {
            // Save the stroke
            strokes.push({
                points: currentStroke,
                width: penWidth
            });
        }

        currentStroke = null;
    }

    /**
     * Handle touch start event
     */
    function handleTouchStart(event) {
        event.preventDefault();
        startDrawing(event);
    }

    /**
     * Handle touch move event
     */
    function handleTouchMove(event) {
        event.preventDefault();
        draw(event);
    }

    /**
     * Attach event listeners for controls
     */
    function attachControlListeners() {
        document.getElementById('clear-canvas').addEventListener('click', clearCanvas);
        document.getElementById('undo-stroke').addEventListener('click', undoStroke);
        document.getElementById('save-drawing').addEventListener('click', saveDrawing);
        document.getElementById('draw-stroke-width').addEventListener('change', updateStrokeWidth);
    }

    /**
     * Update stroke width
     */
    function updateStrokeWidth() {
        penWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;
    }

    /**
     * Clear the drawing
     */
    function clearCanvas() {
        if (!ctx) return;

        // Clear all strokes
        strokes = [];
        currentStroke = null;
        isDrawing = false;

        // Clear canvas and set white background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    }

    /**
     * Undo the last stroke
     */
    function undoStroke() {
        if (strokes.length === 0) return;

        // Remove last stroke
        strokes.pop();

        // Redraw all remaining strokes
        redrawCanvas();
    }

    /**
     * Redraw all strokes on canvas
     */
    function redrawCanvas() {
        // Clear canvas
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // Redraw all strokes
        strokes.forEach(stroke => {
            if (stroke.points.length < 2) return;

            ctx.beginPath();
            ctx.lineWidth = stroke.width;
            ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

            for (let i = 1; i < stroke.points.length; i++) {
                ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
            }

            ctx.stroke();
        });
    }

    /**
     * Calculate bounding box of all strokes
     */
    function calculateBoundingBox() {
        if (strokes.length === 0) {
            return null;
        }

        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;
        let maxStrokeWidth = 0;

        strokes.forEach(stroke => {
            maxStrokeWidth = Math.max(maxStrokeWidth, stroke.width);

            stroke.points.forEach(point => {
                minX = Math.min(minX, point.x);
                minY = Math.min(minY, point.y);
                maxX = Math.max(maxX, point.x);
                maxY = Math.max(maxY, point.y);
            });
        });

        return { minX, minY, maxX, maxY, maxStrokeWidth };
    }

    /**
     * Convert canvas strokes to pen-plotter-compatible SVG path data
     */
    function strokeToSVGPath(stroke) {
        if (!stroke.points || stroke.points.length < 2) {
            return '';
        }

        let pathData = `M ${stroke.points[0].x.toFixed(2)} ${stroke.points[0].y.toFixed(2)}`;

        for (let i = 1; i < stroke.points.length; i++) {
            pathData += ` L ${stroke.points[i].x.toFixed(2)} ${stroke.points[i].y.toFixed(2)}`;
        }

        return pathData;
    }

    /**
     * Convert canvas drawing to pen-plotter-compatible SVG with auto-crop
     *
     * This function generates an SVG that is:
     * - Stroke-based (not fill-based) for pen plotter compatibility
     * - Auto-cropped to the drawing bounds with padding
     * - Compatible with the existing codebase's viewBox handling
     */
    function canvasToSVG() {
        if (strokes.length === 0) {
            return null;
        }

        // Calculate bounding box with stroke width consideration
        const bbox = calculateBoundingBox();
        if (!bbox) {
            return null;
        }

        // Add padding around the content (include max stroke width in padding)
        const padding = Math.max(bbox.maxStrokeWidth * 2, 10);
        const viewBoxX = Math.max(0, bbox.minX - padding);
        const viewBoxY = Math.max(0, bbox.minY - padding);
        const viewBoxWidth = (bbox.maxX - bbox.minX) + (padding * 2);
        const viewBoxHeight = (bbox.maxY - bbox.minY) + (padding * 2);

        // Build pen-plotter-compatible SVG with stroke-based paths
        let svgPaths = '';

        strokes.forEach(stroke => {
            const pathData = strokeToSVGPath(stroke);
            if (pathData) {
                // Pen-plotter compatible attributes:
                // - stroke="black" for black ink
                // - stroke-width for line thickness
                // - stroke-linecap="round" for smooth line endings
                // - stroke-linejoin="round" for smooth corners
                // - fill="none" critical for pen plotter (no filling!)
                svgPaths += `  <path d="${pathData}" stroke="black" stroke-width="${stroke.width}" stroke-linecap="round" stroke-linejoin="round" fill="none"/>\n`;
            }
        });

        // Generate final SVG with proper XML declaration and viewBox for auto-crop
        const svgData = `<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="${viewBoxX.toFixed(2)} ${viewBoxY.toFixed(2)} ${viewBoxWidth.toFixed(2)} ${viewBoxHeight.toFixed(2)}" xmlns="http://www.w3.org/2000/svg">
  <!-- Auto-generated from Canvas drawing -->
  <!-- Pen-plotter compatible: stroke-based, not filled -->
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

        // Convert canvas to pen-plotter-compatible SVG
        const svgData = canvasToSVG();
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
