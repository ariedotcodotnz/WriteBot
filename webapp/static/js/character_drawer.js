/**
 * Character Drawer Module
 * Simple vanilla JavaScript SVG drawing interface
 * Generates pen-plotter-compatible stroke-based SVG characters
 */

const CharacterDrawer = (function() {
    let svg;
    let currentPath;
    let isDrawing = false;
    let paths = [];
    let collectionId;
    let penWidth = 3;

    /**
     * Initialize the character drawer with vanilla SVG
     */
    function init(collId) {
        collectionId = collId;

        const container = document.getElementById('draw-area');
        if (!container) {
            console.error('Draw area element not found');
            return;
        }

        try {
            // Create SVG element
            svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '200');
            svg.setAttribute('height', '300');
            svg.setAttribute('viewBox', '0 0 200 300');
            svg.style.cursor = 'crosshair';
            svg.style.touchAction = 'none'; // Prevent scrolling on touch devices
            
            // Clear container and add SVG
            container.innerHTML = '';
            container.appendChild(svg);

            // Attach drawing event listeners
            attachDrawingListeners();
            attachEventListeners();

            console.log('Character drawer initialized successfully');
        } catch (error) {
            console.error('Error initializing SVG drawing:', error);
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #da1e28;">Error initializing drawing canvas: ' + error.message + '</div>';
        }
    }

    /**
     * Attach event listeners for drawing
     */
    function attachDrawingListeners() {
        // Mouse events
        svg.addEventListener('mousedown', startDrawing);
        svg.addEventListener('mousemove', draw);
        svg.addEventListener('mouseup', stopDrawing);
        svg.addEventListener('mouseleave', stopDrawing);

        // Touch events for mobile
        svg.addEventListener('touchstart', handleTouchStart);
        svg.addEventListener('touchmove', handleTouchMove);
        svg.addEventListener('touchend', stopDrawing);
    }

    /**
     * Get coordinates relative to SVG
     */
    function getCoordinates(event) {
        const rect = svg.getBoundingClientRect();
        const scaleX = 200 / rect.width;
        const scaleY = 300 / rect.height;
        
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
     * Start drawing a new path
     */
    function startDrawing(event) {
        event.preventDefault();
        isDrawing = true;
        
        const coords = getCoordinates(event);
        
        // Create new path element
        currentPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        currentPath.setAttribute('stroke', 'black');
        currentPath.setAttribute('stroke-width', penWidth);
        currentPath.setAttribute('stroke-linecap', 'round');
        currentPath.setAttribute('stroke-linejoin', 'round');
        currentPath.setAttribute('fill', 'none');
        currentPath.setAttribute('d', `M ${coords.x} ${coords.y}`);
        
        svg.appendChild(currentPath);
    }

    /**
     * Continue drawing the current path
     */
    function draw(event) {
        if (!isDrawing || !currentPath) return;
        
        event.preventDefault();
        const coords = getCoordinates(event);
        
        const d = currentPath.getAttribute('d');
        currentPath.setAttribute('d', `${d} L ${coords.x} ${coords.y}`);
    }

    /**
     * Stop drawing and save the path
     */
    function stopDrawing(event) {
        if (!isDrawing) return;
        
        event.preventDefault();
        isDrawing = false;
        
        if (currentPath) {
            // Only save if path has actual movement
            const d = currentPath.getAttribute('d');
            if (d && d.includes('L')) {
                paths.push(currentPath.cloneNode(true));
            }
            currentPath = null;
        }
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
    function attachEventListeners() {
        // Control buttons
        document.getElementById('clear-canvas').addEventListener('click', clearCanvas);
        document.getElementById('undo-stroke').addEventListener('click', undoStroke);
        document.getElementById('save-drawing').addEventListener('click', saveDrawing);

        // Stroke width change
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
        // Remove all paths from SVG
        while (svg.firstChild) {
            svg.removeChild(svg.firstChild);
        }
        paths = [];
        currentPath = null;
        isDrawing = false;
    }

    /**
     * Undo the last stroke
     */
    function undoStroke() {
        if (paths.length > 0) {
            // Remove last saved path
            paths.pop();
            
            // Redraw all remaining paths
            while (svg.firstChild) {
                svg.removeChild(svg.firstChild);
            }
            
            paths.forEach(path => {
                svg.appendChild(path.cloneNode(true));
            });
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
        if (!svg) {
            return null;
        }

        // Get all path elements
        const pathElements = svg.querySelectorAll('path');

        if (pathElements.length === 0) {
            return null;
        }

        const strokeWidth = parseFloat(document.getElementById('draw-stroke-width').value) || 3;

        // Calculate bounding box of all paths
        const bbox = calculateBoundingBox(pathElements);

        // Add padding around the content (include stroke width in padding)
        const padding = strokeWidth * 2 + 5;
        const viewBoxX = Math.max(0, bbox.minX - padding);
        const viewBoxY = Math.max(0, bbox.minY - padding);
        const viewBoxWidth = (bbox.maxX - bbox.minX) + (padding * 2);
        const viewBoxHeight = (bbox.maxY - bbox.minY) + (padding * 2);

        // Build pen-plotter-compatible SVG with stroke-based paths
        let svgPaths = '';

        pathElements.forEach(path => {
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

        if (!svg) {
            alert('Drawing not initialized.');
            return;
        }

        // Check if there are any drawn paths
        const pathElements = svg.querySelectorAll('path');

        if (pathElements.length === 0) {
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