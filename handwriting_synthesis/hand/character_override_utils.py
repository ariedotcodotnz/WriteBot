"""
Utility functions for processing character overrides in generated SVG.

This module provides functionality to inject manually uploaded character SVGs
into AI-generated handwriting for seamless integration.
"""

import random
import re
import xml.etree.ElementTree as ET


def get_character_overrides(collection_id):
    """
    Load character overrides from the database for a given collection.

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

            result[char].append({
                'svg_data': override.svg_data,
                'viewbox_x': override.viewbox_x,
                'viewbox_y': override.viewbox_y,
                'viewbox_width': override.viewbox_width,
                'viewbox_height': override.viewbox_height,
                'baseline_offset': override.baseline_offset,
            })

        return result
    except Exception as e:
        print(f"Error loading character overrides: {e}")
        return {}


def get_random_override(overrides_dict, character):
    """
    Get a random override for the given character.

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

    Args:
        svg_data: SVG file content as string

    Returns:
        Tuple of (paths_string, viewbox_data) or (None, None) on error
    """
    try:
        root = ET.fromstring(svg_data)

        # Extract all path elements
        paths = []
        for path in root.iter():
            if path.tag.endswith('path') or path.tag.endswith('polygon') or path.tag.endswith('polyline') or path.tag.endswith('line') or path.tag.endswith('rect') or path.tag.endswith('circle') or path.tag.endswith('ellipse'):
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

    Args:
        override_data: Override data dict with viewbox info
        target_height: Target height for rendering
        x_stretch: Horizontal stretch factor

    Returns:
        Estimated width in pixels
    """
    vb_width = override_data['viewbox_width']
    vb_height = override_data['viewbox_height']

    if vb_height <= 0:
        return target_height * x_stretch

    # Scale based on aspect ratio
    scale = target_height / vb_height
    return vb_width * scale * x_stretch


def expand_alphabet_with_overrides(overrides_dict, base_alphabet):
    """
    Expand the base alphabet with characters from overrides.

    This allows the system to accept and render characters that aren't
    in the original AI model's alphabet.

    Args:
        overrides_dict: Dictionary of character overrides
        base_alphabet: Original alphabet list

    Returns:
        Expanded alphabet list
    """
    expanded = list(base_alphabet)

    for char in overrides_dict.keys():
        if char not in expanded:
            expanded.append(char)

    return expanded
