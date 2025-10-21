"""
Text Processing Utilities for WebApp

This module provides improved text processing functions that can be used
by the webapp to replace the old basic text processing logic.
"""

import sys
import os

# Add parent directory to path to import text_processor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from text_processor import (
    TextProcessor,
    TextProcessingConfig,
    ParagraphStyle,
    create_alphabet_set
)
from typing import List, Tuple, Dict, Any, Optional


def process_text_for_handwriting(
    text: str,
    max_line_length: int = 75,
    alphabet: Optional[set] = None,
    paragraph_style: str = "preserve_breaks",
    preserve_empty_lines: bool = True,
    hyphenate_long_words: bool = False,
) -> Tuple[List[str], List[int]]:
    """
    Process text for handwriting synthesis with improved paragraph handling.

    This function replaces the old _wrap_by_canvas logic with improved text processing
    that better handles paragraphs, line wrapping, and text normalization.

    Args:
        text: Input text to process
        max_line_length: Maximum characters per line
        alphabet: Set of allowed characters (optional)
        paragraph_style: One of "preserve_breaks", "single_space", "no_breaks", "indent_first"
        preserve_empty_lines: Whether to preserve empty lines
        hyphenate_long_words: Whether to hyphenate long words

    Returns:
        Tuple of (lines, src_index) where:
        - lines is a list of processed text lines
        - src_index is a list tracking which original line each wrapped line came from
    """
    # Map paragraph style string to enum
    style_map = {
        "preserve_breaks": ParagraphStyle.PRESERVE_BREAKS,
        "single_space": ParagraphStyle.SINGLE_SPACE,
        "no_breaks": ParagraphStyle.NO_BREAKS,
        "indent_first": ParagraphStyle.INDENT_FIRST,
    }

    para_style = style_map.get(paragraph_style, ParagraphStyle.PRESERVE_BREAKS)

    # Create configuration
    config = TextProcessingConfig(
        max_line_length=max_line_length,
        lines_per_page=999999,  # Don't paginate, just wrap lines
        paragraph_style=para_style,
        preserve_empty_lines=preserve_empty_lines,
        hyphenate_long_words=hyphenate_long_words,
        normalize_whitespace=True,
    )

    # Create processor
    processor = TextProcessor(config)

    # Process text
    lines, metadata = processor.process_text(text, alphabet)

    # Create src_index (for compatibility with existing code)
    # Since we're not doing per-line tracking in the new system,
    # we'll create a simple sequential index
    src_index = list(range(len(lines)))

    return lines, src_index


def improved_wrap_by_canvas(
    raw_lines: List[str],
    content_width_px: float,
    max_chars_per_line: int = 75,
    approx_char_px: float = 13.0,
    utilization: float = 1.0,
) -> Tuple[List[str], List[int]]:
    """
    Improved replacement for _wrap_by_canvas that uses the new text processing system.

    This function maintains API compatibility with the old _wrap_by_canvas but uses
    improved text processing internally.

    Args:
        raw_lines: List of input text lines
        content_width_px: Available width in pixels
        max_chars_per_line: Maximum characters per line (hard limit)
        approx_char_px: Approximate character width in pixels
        utilization: Utilization factor (typically > 1.0 to pack more text)

    Returns:
        Tuple of (wrapped_lines, src_index)
    """
    # Calculate effective line length based on canvas width
    util = max(0.5, float(utilization))
    budget_chars = max(1, int((content_width_px * util) / max(1.0, approx_char_px)))
    budget_chars = min(budget_chars, max_chars_per_line)

    # Join lines into single text (preserving paragraph breaks)
    text = "\n".join(raw_lines)

    # Process using improved text processor
    lines, _ = process_text_for_handwriting(
        text=text,
        max_line_length=budget_chars,
        paragraph_style="preserve_breaks",
        preserve_empty_lines=True,
    )

    # Create src_index mapping
    # Map each wrapped line to its source line index
    src_index = []
    current_source = 0

    for line in lines:
        src_index.append(current_source)
        # If this is an empty line, it might indicate a paragraph break
        if not line.strip():
            current_source = min(current_source + 1, len(raw_lines) - 1)

    return lines, src_index


# Backward compatibility: export functions with old names
wrap_by_canvas = improved_wrap_by_canvas
process_text = process_text_for_handwriting
