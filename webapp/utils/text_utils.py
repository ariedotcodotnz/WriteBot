"""Text processing and normalization utilities."""

import re
import unicodedata
from typing import List, Tuple, Optional, Any, Union, Dict

# Import drawing operations for alphabet
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.drawing import operations as draw_ops


# Allowed characters and replacements
ALLOWED_CHARS = set(draw_ops.alphabet)

_REPLACEMENTS = {
    '\u2019': "'",  # right single quote
    '\u2018': "'",  # left single quote
    '\u201C': '"',   # left double quote
    '\u201D': '"',   # right double quote
    '\u2013': '-',   # en dash
    '\u2014': '-',   # em dash
    '\u2212': '-',   # minus sign
    '\u2026': '...', # ellipsis
    '\u00A0': ' ',   # non-breaking space
    '\u2022': '-',   # bullet
}


def normalize_text_for_model(s: str) -> str:
    """
    Normalize text to fit the model's allowed alphabet.

    Args:
        s: Input string

    Returns:
        Normalized string with only allowed characters
    """
    if s is None:
        return ''

    # Apply typographic replacements
    for k, v in _REPLACEMENTS.items():
        s = s.replace(k, v)

    # Strip accents/diacritics to ASCII
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')

    # Map disallowed uppercase letters to lowercase if that becomes allowed
    out_chars: List[str] = []
    for ch in s:
        if ch in ALLOWED_CHARS:
            out_chars.append(ch)
            continue
        lower = ch.lower()
        if lower in ALLOWED_CHARS:
            out_chars.append(lower)
            continue
        # Replace anything else with space
        out_chars.append(' ')

    out = ''.join(out_chars)
    # Collapse repeated spaces
    out = re.sub(r'\s+', ' ', out).strip()
    return out


def wrap_by_canvas(
    raw_lines: List[str],
    content_width_px: float,
    max_chars_per_line: int = 75,
    approx_char_px: float = 13.0,
    utilization: float = 1.0,
) -> Tuple[List[str], List[int]]:
    """
    Enhanced text wrapping using improved text processor.

    This function now uses the text_processor module for intelligent paragraph
    handling, better word wrapping, and empty line preservation.

    Args:
        raw_lines: List of input lines
        content_width_px: Available content width in pixels
        max_chars_per_line: Maximum characters per line
        approx_char_px: Approximate character width in pixels
        utilization: Line utilization factor (> 1.0 packs more characters)

    Returns:
        Tuple of (wrapped_lines, source_indices)
    """
    try:
        # Try to use improved text processing
        from text_processor import TextProcessor, TextProcessingConfig, ParagraphStyle

        # Calculate effective line length
        util = max(0.5, float(utilization))
        budget_chars = max(1, int((content_width_px * util) / max(1.0, approx_char_px)))
        budget_chars = min(budget_chars, max_chars_per_line)

        # Join raw lines into text
        text = "\n".join(raw_lines)

        # Configure improved text processor
        config = TextProcessingConfig(
            max_line_length=budget_chars,
            lines_per_page=999999,  # Don't paginate
            paragraph_style=ParagraphStyle.PRESERVE_BREAKS,
            preserve_empty_lines=True,
            hyphenate_long_words=False,
            normalize_whitespace=True,
        )

        processor = TextProcessor(config)
        lines_out, _ = processor.process_text(text, alphabet=None)

        # Create src_index (track which original line each wrapped line came from)
        src_index = []
        current_source = 0
        for line in lines_out:
            src_index.append(current_source)
            # Empty line might indicate paragraph break
            if not line.strip():
                current_source = min(current_source + 1, len(raw_lines) - 1)

        return lines_out, src_index

    except ImportError:
        # Fallback to original implementation if text_processor not available
        pass

    # ORIGINAL IMPLEMENTATION (fallback)
    lines_out: List[str] = []
    src_index: List[int] = []

    for idx, raw in enumerate(raw_lines):
        # Treat a single backslash as a blank spacer line
        if raw.strip() == '\\':
            lines_out.append("")
            src_index.append(idx)
            continue

        s = str(raw)
        # Allow intentional empty lines (just pass through)
        if s.strip() == "":
            lines_out.append("")
            src_index.append(idx)
            continue

        words = s.split()
        if not words:
            lines_out.append("")
            src_index.append(idx)
            continue

        # utilization > 1 allows packing more words before wrapping (use cautiously)
        util = max(0.5, float(utilization))
        budget_chars = max(1, int((content_width_px * util) / max(1.0, approx_char_px)))
        budget_chars = min(budget_chars, max_chars_per_line)

        cur: List[str] = []
        cur_len = 0
        for w in words:
            extra = len(w) if cur_len == 0 else len(w) + 1
            if cur_len + extra <= budget_chars:
                cur.append(w)
                cur_len += extra
            else:
                # push current line (also ensure <= 75 chars)
                if cur:
                    lines_out.append(" ".join(cur)[:max_chars_per_line])
                    src_index.append(idx)
                # if single word longer than budget, hard-split
                while len(w) > budget_chars:
                    lines_out.append(w[:budget_chars][:max_chars_per_line])
                    src_index.append(idx)
                    w = w[budget_chars:]
                cur = [w]
                cur_len = len(w)

        if cur:
            lines_out.append(" ".join(cur)[:max_chars_per_line])
            src_index.append(idx)

    return lines_out, src_index


def parse_margins(value: Union[None, float, int, List[float], Dict[str, float]]):
    """
    Parse margin value into a standard format.

    Args:
        value: Margin specification

    Returns:
        Parsed margin value (number, list, or dict)
    """
    if value is None:
        return 20

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, list) and len(value) == 4:
        return [float(x) for x in value]

    if isinstance(value, dict):
        return {
            "top": float(value.get("top", 0)),
            "right": float(value.get("right", 0)),
            "bottom": float(value.get("bottom", 0)),
            "left": float(value.get("left", 0)),
        }

    # Attempt to parse "t,r,b,l" format
    if isinstance(value, str):
        try:
            parts = [float(x.strip()) for x in value.split(",")]
            if len(parts) == 4:
                return parts
        except Exception:
            pass

    return 20


def map_sequence_to_wrapped(
    seq: Optional[List[Any]],
    src_index: List[int],
    original_len: int,
    wrapped_len: int
) -> Optional[List[Any]]:
    """
    Map a per-original-line sequence to per-wrapped-line using src_index.

    Args:
        seq: Original sequence (or None)
        src_index: Source indices mapping wrapped lines to original lines
        original_len: Number of original lines
        wrapped_len: Number of wrapped lines

    Returns:
        Mapped sequence or None

    Logic:
    - If seq is None → None
    - If len == 1 → broadcast to wrapped_len
    - If len == original_len → map by src_index
    - If len == wrapped_len → return as-is
    - Else → broadcast first value to wrapped_len
    """
    if seq is None:
        return None

    try:
        n = len(seq)
    except Exception:
        # scalar fallback
        return [seq] * wrapped_len

    if n == 0:
        return None
    if n == 1:
        return [seq[0]] * wrapped_len
    if n == original_len:
        return [seq[i] for i in src_index]
    if n == wrapped_len:
        return seq

    return [seq[0]] * wrapped_len


def parse_optional_list(value, cast_fn):
    """
    Parse optional list parameter.

    Args:
        value: Value to parse (can be None, single value, or list)
        cast_fn: Function to cast values

    Returns:
        List of cast values or None
    """
    if value is None:
        return None
    if isinstance(value, list):
        return [cast_fn(v) for v in value]
    return [cast_fn(value)]


def parse_lines(data: Dict[str, Any]) -> List[str]:
    """
    Parse lines from request data.

    Args:
        data: Request data dictionary

    Returns:
        List of text lines
    """
    if isinstance(data.get("lines"), list):
        return [str(x) for x in data["lines"]]

    text = data.get("text", "")
    if not isinstance(text, str):
        text = str(text)

    # Normalize newlines; preserve backslash-only lines for blank spacing
    return text.splitlines()


def wrap_text_lines(lines: List[str], max_chars: int = 75) -> List[str]:
    """
    Simple text wrapping by character count.

    Args:
        lines: Input lines
        max_chars: Maximum characters per line

    Returns:
        Wrapped lines
    """
    wrapped: List[str] = []
    for line in lines:
        s = str(line)
        while len(s) > max_chars:
            # Try break at last space within limit
            chunk = s[:max_chars]
            space_idx = chunk.rfind(' ')
            if space_idx == -1 or space_idx < max_chars * 0.6:
                wrapped.append(chunk)
                s = s[max_chars:]
            else:
                wrapped.append(s[:space_idx])
                s = s[space_idx+1:]
        if s:
            wrapped.append(s)
    return wrapped
