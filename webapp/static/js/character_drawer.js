/**
 * Character Drawer Module - Canvas API Implementation
 *
 * Built from scratch using HTML5 Canvas for drawing
 * Converts strokes to pen-plotter-compatible SVG format
 * Features:
 * - High-quality smooth bezier curves (no jagged lines!)
 * - Real-time smooth rendering during drawing
 * - Point simplification to reduce file size
 * - Auto-cropping and proper viewBox calculation
 * - Pen-plotter compatible stroke-based SVG output
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
     * Continue drawing the current stroke with smooth curves
     */
    function draw(event) {
        if (!isDrawing || !currentStroke) return;

        event.preventDefault();
        const coords = getCoordinates(event);

        // Add point to current stroke
        currentStroke.push({ x: coords.x, y: coords.y });

        // For smooth real-time drawing, redraw the entire current stroke
        // This is efficient enough for modern browsers
        redrawCanvas();

        // Draw the current stroke being drawn
        if (currentStroke.length >= 2) {
            drawSmoothStroke(currentStroke, penWidth);
        }
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
     * Draw a smooth stroke on the canvas using the same curve smoothing as SVG export
     */
    function drawSmoothStroke(points, width) {
        if (points.length < 2) return;

        ctx.beginPath();
        ctx.lineWidth = width;

        if (points.length === 2) {
            // For 2 points, draw a straight line
            ctx.moveTo(points[0].x, points[0].y);
            ctx.lineTo(points[1].x, points[1].y);
        } else {
            // For more points, draw smooth curves using quadratic bezier
            ctx.moveTo(points[0].x, points[0].y);

            // Draw curve through all points
            for (let i = 1; i < points.length - 1; i++) {
                // Calculate midpoint between current and next point
                const xc = (points[i].x + points[i + 1].x) / 2;
                const yc = (points[i].y + points[i + 1].y) / 2;

                // Draw quadratic curve to midpoint, using current point as control
                ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
            }

            // Draw final curve to the last point
            const lastIdx = points.length - 1;
            ctx.quadraticCurveTo(
                points[lastIdx - 1].x,
                points[lastIdx - 1].y,
                points[lastIdx].x,
                points[lastIdx].y
            );
        }

        ctx.stroke();
    }

    /**
     * Redraw all strokes on canvas with smooth curves
     */
    function redrawCanvas() {
        // Clear canvas
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        // Redraw all strokes with smooth curves
        strokes.forEach(stroke => {
            if (stroke.points.length < 2) return;
            drawSmoothStroke(stroke.points, stroke.width);
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
     * Simplify points using distance-based algorithm
     * Removes points that are too close together to reduce redundancy
     */
    function simplifyPoints(points, tolerance = 2.0) {
        if (points.length < 3) return points;

        const simplified = [points[0]];

        for (let i = 1; i < points.length - 1; i++) {
            const prev = simplified[simplified.length - 1];
            const curr = points[i];
            const distance = Math.sqrt(
                Math.pow(curr.x - prev.x, 2) +
                Math.pow(curr.y - prev.y, 2)
            );

            // Only add point if it's far enough from the previous point
            if (distance >= tolerance) {
                simplified.push(curr);
            }
        }

        // Always include the last point
        simplified.push(points[points.length - 1]);

        return simplified;
    }

    /**
     * Calculate control point for quadratic bezier curve
     * This creates smooth curves through the points
     */
    function getControlPoint(p0, p1, p2, smoothing = 0.2) {
        // Calculate vectors
        const dx1 = p1.x - p0.x;
        const dy1 = p1.y - p0.y;
        const dx2 = p2.x - p1.x;
        const dy2 = p2.y - p1.y;

        // Calculate the control point by averaging directions
        const cpx = p1.x + (dx1 - dx2) * smoothing;
        const cpy = p1.y + (dy1 - dy2) * smoothing;

        return { x: cpx, y: cpy };
    }

    /**
     * Convert canvas strokes to smooth pen-plotter-compatible SVG path data
     * Uses quadratic bezier curves for smooth, natural-looking strokes
     */
    function strokeToSVGPath(stroke) {
        if (!stroke.points || stroke.points.length < 2) {
            return '';
        }

        // Simplify points first to remove redundancy
        const simplified = simplifyPoints(stroke.points, 2.5);

        if (simplified.length < 2) {
            return '';
        }

        // Start with move to first point
        let pathData = `M ${simplified[0].x.toFixed(2)} ${simplified[0].y.toFixed(2)}`;

        if (simplified.length === 2) {
            // If only 2 points, use a straight line
            pathData += ` L ${simplified[1].x.toFixed(2)} ${simplified[1].y.toFixed(2)}`;
        } else if (simplified.length === 3) {
            // For 3 points, use a simple quadratic bezier
            const cp = getControlPoint(simplified[0], simplified[1], simplified[2]);
            pathData += ` Q ${cp.x.toFixed(2)} ${cp.y.toFixed(2)}, ${simplified[2].x.toFixed(2)} ${simplified[2].y.toFixed(2)}`;
        } else {
            // For more points, create smooth curves using quadratic bezier curves
            // Use Catmull-Rom style smoothing for natural curves

            // First curve - from point 0 to point 1
            const cp0 = {
                x: (simplified[0].x + simplified[1].x) / 2,
                y: (simplified[0].y + simplified[1].y) / 2
            };
            pathData += ` Q ${simplified[1].x.toFixed(2)} ${simplified[1].y.toFixed(2)}, ${cp0.x.toFixed(2)} ${cp0.y.toFixed(2)}`;

            // Middle curves
            for (let i = 1; i < simplified.length - 2; i++) {
                const cp = {
                    x: (simplified[i].x + simplified[i + 1].x) / 2,
                    y: (simplified[i].y + simplified[i + 1].y) / 2
                };
                pathData += ` Q ${simplified[i + 1].x.toFixed(2)} ${simplified[i + 1].y.toFixed(2)}, ${cp.x.toFixed(2)} ${cp.y.toFixed(2)}`;
            }

            // Last curve - to the final point
            const lastIdx = simplified.length - 1;
            pathData += ` Q ${simplified[lastIdx - 1].x.toFixed(2)} ${simplified[lastIdx - 1].y.toFixed(2)}, ${simplified[lastIdx].x.toFixed(2)} ${simplified[lastIdx].y.toFixed(2)}`;
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
                // Pen-plotter compatible attributes with high-quality rendering:
                // - stroke="black" for black ink
                // - stroke-width for line thickness
                // - stroke-linecap="round" for smooth line endings
                // - stroke-linejoin="round" for smooth corners
                // - fill="none" critical for pen plotter (no filling!)
                // - shape-rendering="geometricPrecision" for high-quality curves
                // - vector-effect="non-scaling-stroke" keeps stroke width consistent
                svgPaths += `  <path d="${pathData}" stroke="black" stroke-width="${stroke.width}" stroke-linecap="round" stroke-linejoin="round" fill="none" shape-rendering="geometricPrecision"/>\n`;
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
