"""
Handwriting stroke operation modules.

This package exposes various operations for manipulating handwriting strokes,
chunking text, and sampling from the model.
"""

from .stroke_ops import (
    get_stroke_width,
    calculate_baseline_angle,
    rotate_stroke,
    get_baseline_y,
    smooth_chunk_boundary,
    calculate_adaptive_spacing,
    stitch_strokes,
)
from .chunking import split_text_into_chunks
from .sampling import sample_strokes

__all__ = [
    'get_stroke_width',
    'calculate_baseline_angle',
    'rotate_stroke',
    'get_baseline_y',
    'smooth_chunk_boundary',
    'calculate_adaptive_spacing',
    'stitch_strokes',
    'split_text_into_chunks',
    'sample_strokes',
]
