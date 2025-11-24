"""
Utility functions for processing character overrides in generated SVG.

This module provides functionality to inject manually uploaded character SVGs
into AI-generated handwriting for seamless integration. It handles loading
overrides, splitting text, and estimating dimensions for layout.
"""

import random
import re
import xml.etree.ElementTree as ET


def calculate_baseline_offset(svg_data, viewbox_height):
    """
    Calculate baseline offset by analyzing SVG path data.

    For handwriting, the baseline is typically where letters like 'a', 'e', 'n' sit.
    This is usually around 70-85% from the top of the bounding box. This function
    attempts to heuristically determine the baseline from the Y-coordinates of
    the path data.

    Args:
        svg_data: SVG content as string
        viewbox_height: Height of the viewbox

    Returns:
        Baseline offset from bottom of viewbox
    """
    try:
        root = ET.fromstring(svg_data)

        # Extract all y-coordinates from paths
        y_coords = []
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name == 'path':
                d = elem.get('d', '')
                # Simple regex to extract y coordinates
                # Match numbers that come after command letters or commas
                coords = re.findall(r'[MLCQHVmlcqhv]\s*([-\d.]+)[,\s]+([-\d.]+)', d)
                for x, y in coords:
                    try:
                        y_coords.append(float(y))
                    except ValueError:
                        continue

        if y_coords:
            # Find the most common y-value in the lower region (likely baseline)
            # Get values in the bottom 30% of the viewbox
            lower_threshold = viewbox_height * 0.7
            baseline_candidates = [y for y in y_coords if y >= lower_threshold]

            if baseline_candidates:
                # Use median of lower region as baseline
                baseline_candidates.sort()
                baseline_y = baseline_candidates[len(baseline_candidates) // 2]
                # Return distance from bottom
                return viewbox_height - baseline_y

        # Default fallback: 80% from top = 20% from bottom
        return viewbox_height * 0.2

    except Exception as e:
        print(f"Error calculating baseline offset: {e}")
        # Default fallback
        return viewbox_height * 0.2


def get_character_overrides(collection_id):
    """
    Load character overrides from the database for a given collection.

    Retrieves all active character overrides for the specified collection ID.
    If no baseline offset is stored, it attempts to auto-calculate it.

    Args:
        collection_id: ID of the character override collection

    Returns:
        Dictionary mapping characters to lists of override data:
        {
            'a': [{'svg_data': '...', 'viewbox_width': 100, ...}, ...],
            'b': [...],
            ...
        }
    """
    if collection_id is None:
        return {}

    try:
        # Import here to avoid circular dependencies
        from webapp.models import CharacterOverride

        overrides = CharacterOverride.query.filter_by(collection_id=collection_id).all()

        result = {}
        for override in overrides:
            char = override.character
            if char not in result:
                result[char] = []

            # Calculate baseline if not provided or zero
            baseline_offset = override.baseline_offset
            if baseline_offset is None or baseline_offset == 0:
                baseline_offset = calculate_baseline_offset(
                    override.svg_data,
                    override.viewbox_height
                )
                print(f"Auto-calculated baseline for '{char}': {baseline_offset:.2f}")

            result[char].append({
                'svg_data': override.svg_data,
                'viewbox_x': override.viewbox_x,
                'viewbox_y': override.viewbox_y,
                'viewbox_width': override.viewbox_width,
                'viewbox_height': override.viewbox_height,
                'baseline_offset': baseline_offset,
            })

        return result
    except Exception as e:
        print(f"Error loading character overrides: {e}")
        return {}


def get_random_override(overrides_dict, character):
    """
    Get a random override for the given character.

    If multiple overrides exist for a single character (e.g., variations of 'a'),
    this function randomly selects one.

    Args:
        overrides_dict: Dictionary of character overrides
        character: The character to look up

    Returns:
        Override data dict or None if no override exists
    """
    if character not in overrides_dict:
        return None

    variants = overrides_dict[character]
    if not variants:
        return None

    return random.choice(variants)


def extract_svg_path(svg_data):
    """
    Extract the main path/content from an SVG string.

    Also extracts the viewBox information.

    Args:
        svg_data: SVG file content as string

    Returns:
        Tuple of (paths_string, viewbox_data) or (None, None) on error.
        viewbox_data is a dict with keys 'x', 'y', 'width', 'height'.
    """
    try:
        root = ET.fromstring(svg_data)

        # Extract all path elements
        paths = []
        for path in root.iter():
            tag_name = path.tag.split('}')[-1] if '}' in path.tag else path.tag
            if tag_name in ('path', 'polygon', 'polyline', 'line', 'rect', 'circle', 'ellipse'):
                paths.append(ET.tostring(path, encoding='unicode'))

        if not paths:
            return None, None

        # Get viewBox
        viewbox = root.get('viewBox')
        if viewbox:
            parts = [float(x) for x in viewbox.split()]
            viewbox_data = {
                'x': parts[0],
                'y': parts[1],
                'width': parts[2],
                'height': parts[3],
            }
        else:
            viewbox_data = None

        return '\n'.join(paths), viewbox_data
    except Exception as e:
        print(f"Error extracting SVG path: {e}")
        return None, None


def split_text_with_overrides(text, overrides_dict):
    """
    Split text into chunks, separating override characters from regular text.

    This function identifies characters that have overrides and splits the
    input text so that overrides can be handled separately from standard
    generated handwriting.

    Args:
        text: Input text string
        overrides_dict: Dictionary of character overrides

    Returns:
        List of tuples (chunk_text, is_override):
        - chunk_text: The text chunk
        - is_override: True if this chunk is a single override character, False otherwise

    Example:
        text = "Hello world"
        overrides_dict = {'o': [...]}
        Returns: [("Hell", False), ("o", True), (" w", False), ("o", True), ("rld", False)]
    """
    if not overrides_dict or not text:
        return [(text, False)]

    chunks = []
    current_chunk = []

    for char in text:
        if char in overrides_dict:
            # Save any accumulated regular text
            if current_chunk:
                chunks.append((''.join(current_chunk), False))
                current_chunk = []
            # Add the override character as its own chunk
            chunks.append((char, True))
        else:
            # Accumulate regular text
            current_chunk.append(char)

    # Save any remaining regular text
    if current_chunk:
        chunks.append((''.join(current_chunk), False))

    return chunks


def estimate_override_width(override_data, target_height, x_stretch=1.0):
    """
    Estimate the width an override character will take when rendered.

    This MUST match the calculation in _draw.py for proper line wrapping.
    It parses the SVG path data to determine the bounding box and scales
    it to match the target line height.

    Args:
        override_data: Override data dict with SVG data
        target_height: Target height for rendering
        x_stretch: Horizontal stretch factor

    Returns:
        Estimated width in pixels
    """
    import xml.etree.ElementTree as ET
    import re

    try:
        # Parse SVG to get actual character bounds
        svg_root = ET.fromstring(override_data['svg_data'])
        all_x_coords = []
        all_y_coords = []

        for elem in svg_root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name == 'path':
                d = elem.get('d', '')
                coords = re.findall(r'[ML]\s*([-\d.]+)\s+([-\d.]+)', d)
                for x, y in coords:
                    all_x_coords.append(float(x))
                    all_y_coords.append(float(y))

        if all_x_coords and all_y_coords:
            char_width = max(all_x_coords) - min(all_x_coords)
            char_height = max(all_y_coords) - min(all_y_coords)

            # Scale based on character height
            if char_height > 0:
                scale = target_height / char_height
            else:
                scale = 1.0

            return char_width * scale * x_stretch

        # Fallback
        return target_height * 0.6

    except Exception as e:
        print(f"Error estimating override width: {e}")
        return target_height * 0.6


def expand_alphabet_with_overrides(overrides_dict, base_alphabet):
    """
    Expand the base alphabet with characters from overrides.

    This allows the system to accept and render characters that aren't
    in the original AI model's alphabet (e.g., special symbols or foreign characters
    provided via overrides).

    Args:
        overrides_dict: Dictionary of character overrides
        base_alphabet: Original alphabet list

    Returns:
        Expanded alphabet list containing unique characters from base and overrides.
    """
    expanded = list(base_alphabet)

    for char in overrides_dict.keys():
        if char not in expanded:
            expanded.append(char)

    return expanded


def analyze_svg_bounds(svg_data):
    """
    Analyze SVG to extract accurate bounding box information.

    Parses path, rect, circle, and ellipse elements to find the
    min/max x and y coordinates.

    Args:
        svg_data: SVG content as string

    Returns:
        Dictionary with min_x, max_x, min_y, max_y, width, height.
        Returns None if analysis fails.
    """
    try:
        root = ET.fromstring(svg_data)

        all_x = []
        all_y = []

        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            if tag_name == 'path':
                d = elem.get('d', '')
                # Extract coordinates
                coords = re.findall(r'([-\d.]+)[,\s]+([-\d.]+)', d)
                for x, y in coords:
                    try:
                        all_x.append(float(x))
                        all_y.append(float(y))
                    except ValueError:
                        continue

            elif tag_name == 'rect':
                x = float(elem.get('x', 0))
                y = float(elem.get('y', 0))
                w = float(elem.get('width', 0))
                h = float(elem.get('height', 0))
                all_x.extend([x, x + w])
                all_y.extend([y, y + h])

            elif tag_name == 'circle':
                cx = float(elem.get('cx', 0))
                cy = float(elem.get('cy', 0))
                r = float(elem.get('r', 0))
                all_x.extend([cx - r, cx + r])
                all_y.extend([cy - r, cy + r])

            elif tag_name == 'ellipse':
                cx = float(elem.get('cx', 0))
                cy = float(elem.get('cy', 0))
                rx = float(elem.get('rx', 0))
                ry = float(elem.get('ry', 0))
                all_x.extend([cx - rx, cx + rx])
                all_y.extend([cy - ry, cy + ry])

        if all_x and all_y:
            return {
                'min_x': min(all_x),
                'max_x': max(all_x),
                'min_y': min(all_y),
                'max_y': max(all_y),
                'width': max(all_x) - min(all_x),
                'height': max(all_y) - min(all_y),
            }

        return None

    except Exception as e:
        print(f"Error analyzing SVG bounds: {e}")
        return None


def validate_override_svg(svg_data):
    """
    Validate that an SVG is suitable for use as a character override.

    Checks for:
    1. Valid XML structure.
    2. Presence of a valid viewBox.
    3. Presence of at least one drawable element.

    Args:
        svg_data: SVG content as string

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        root = ET.fromstring(svg_data)

        # Check for viewBox
        viewbox = root.get('viewBox')
        if not viewbox:
            return False, "SVG missing viewBox attribute"

        # Parse viewBox
        try:
            parts = [float(x) for x in viewbox.split()]
            if len(parts) != 4:
                return False, "Invalid viewBox format (needs 4 values)"
            if parts[2] <= 0 or parts[3] <= 0:
                return False, "viewBox width/height must be positive"
        except (ValueError, IndexError):
            return False, "Could not parse viewBox values"

        # Check for at least one drawable element
        has_content = False
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name in ('path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line'):
                has_content = True
                break

        if not has_content:
            return False, "SVG contains no drawable elements"

        return True, "Valid"

    except ET.ParseError as e:
        return False, f"XML parse error: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"
