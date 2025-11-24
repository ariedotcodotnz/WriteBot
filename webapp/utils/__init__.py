"""
Webapp utility modules for WriteBot.

This package provides helper functions for page layout, text processing,
and authentication within the web application.
"""

from .page_utils import (
    PX_PER_MM,
    PAPER_SIZES_MM,
    to_px,
    margins_to_px,
    resolve_page_px,
)
from .text_utils import (
    normalize_text_for_model,
    wrap_by_canvas,
    parse_margins,
    map_sequence_to_wrapped,
)

__all__ = [
    'PX_PER_MM',
    'PAPER_SIZES_MM',
    'to_px',
    'margins_to_px',
    'resolve_page_px',
    'normalize_text_for_model',
    'wrap_by_canvas',
    'parse_margins',
    'map_sequence_to_wrapped',
]
