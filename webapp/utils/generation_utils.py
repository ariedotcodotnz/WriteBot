"""Shared utilities for handwriting generation (individual and batch)."""

import os
import shutil
import tempfile
from typing import Any, Dict, Optional, List, Tuple

from handwriting_synthesis.hand.Hand import Hand
from webapp.utils.page_utils import resolve_page_px, margins_to_px, line_height_px as _line_height_px
from webapp.utils.text_utils import (
    normalize_text_for_model,
    wrap_by_canvas,
    parse_optional_list as _parse_optional_list,
    parse_margins as _parse_margins,
    map_sequence_to_wrapped as _map_sequence_to_wrapped,
)


def parse_generation_params(params: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse and normalize generation parameters from a dictionary.

    This function handles parameter parsing for both individual and batch generation,
    ensuring consistent behavior across all generation endpoints.

    Args:
        params: Dictionary containing generation parameters (from request payload or CSV row).
        defaults: Optional defaults to fall back to for missing parameters.

    Returns:
        Dictionary with normalized generation parameters.
    """
    if defaults is None:
        defaults = {}

    def _get(key: str, default=None):
        """Get value with fallback to defaults."""
        val = params.get(key)
        if val is None or val == "" or (isinstance(val, float) and str(val) == "nan"):
            return defaults.get(key, default)
        return val

    def _parse_bool(val, default=True):
        """Parse boolean value."""
        if val is None or val == "":
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on")
        return bool(val)

    def _parse_float(val, default=None):
        """Parse float value."""
        if val is None or val == "" or (isinstance(val, str) and not val.strip()):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def _parse_int(val, default=None):
        """Parse int value."""
        if val is None or val == "" or (isinstance(val, str) and not val.strip()):
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    # Parse text/lines
    text = _get("text")
    lines = _get("lines")

    # Parse list parameters
    biases = _parse_optional_list(_get("biases"), float)
    styles = _parse_optional_list(_get("styles"), int)
    stroke_colors = _parse_optional_list(_get("stroke_colors"), str)
    stroke_widths = _parse_optional_list(_get("stroke_widths"), float)

    # Page parameters
    page_size = _get("page_size", "A4")
    units = _get("units", "mm")
    page_width = _parse_float(_get("page_width"))
    page_height = _parse_float(_get("page_height"))

    # Handle margins - check for individual margin fields first, then fall back to "margins"
    margin_top = _parse_float(_get("margin_top"))
    margin_right = _parse_float(_get("margin_right"))
    margin_bottom = _parse_float(_get("margin_bottom"))
    margin_left = _parse_float(_get("margin_left"))

    if any(x is not None for x in [margin_top, margin_right, margin_bottom, margin_left]):
        # Individual margins specified - build dict
        margins = {
            "top": margin_top if margin_top is not None else 20.0,
            "right": margin_right if margin_right is not None else 20.0,
            "bottom": margin_bottom if margin_bottom is not None else 20.0,
            "left": margin_left if margin_left is not None else 20.0,
        }
    else:
        # Fall back to old "margins" field (single value or comma-separated)
        margins = _parse_margins(_get("margins", 20))

    line_height = _get("line_height")
    align = _get("align", "left")
    background = _get("background")
    global_scale = _parse_float(_get("global_scale"), 1.0)
    orientation = _get("orientation", "portrait")

    # Quality parameters
    legibility = _get("legibility", "normal")
    x_stretch = _parse_float(_get("x_stretch"), 1.0)
    denoise = _parse_bool(_get("denoise", "true"), True)

    # Spacing and sizing
    empty_line_spacing = _parse_float(_get("empty_line_spacing"))
    auto_size = _parse_bool(_get("auto_size", "true"), True)
    manual_size_scale = _parse_float(_get("manual_size_scale"), 1.0)

    # Handwriting size - can be preset name ('small', 'large', 'christmas') or numeric multiplier
    handwriting_size = _get("handwriting_size")
    # Try to parse as float if it looks like a number, otherwise keep as string preset
    if handwriting_size is not None:
        try:
            handwriting_size = float(handwriting_size)
        except (ValueError, TypeError):
            pass  # Keep as string preset name

    # Character overrides
    character_override_collection_id = _parse_int(_get("character_override_collection_id"))

    # Wrapping parameters
    wrap_char_px = _parse_float(_get("wrap_char_px"))
    wrap_ratio = _parse_float(_get("wrap_ratio"))
    wrap_utilization = _parse_float(_get("wrap_utilization"))

    # Chunked mode parameters
    use_chunked = _parse_bool(_get("use_chunked", "true"), True)
    max_line_width = _parse_float(_get("max_line_width"), 800.0)
    words_per_chunk = _parse_int(_get("words_per_chunk"), 3)
    chunk_spacing = _parse_float(_get("chunk_spacing"), 8.0)
    rotate_chunks = _parse_bool(_get("rotate_chunks", "true"), True)
    min_words_per_chunk = _parse_int(_get("min_words_per_chunk"), 2)
    max_words_per_chunk = _parse_int(_get("max_words_per_chunk"), 8)
    target_chars_per_chunk = _parse_int(_get("target_chars_per_chunk"), 25)
    adaptive_chunking = _parse_bool(_get("adaptive_chunking", "true"), True)
    adaptive_strategy = _get("adaptive_strategy", "balanced")

    return {
        "text": text,
        "lines": lines,
        "biases": biases,
        "styles": styles,
        "stroke_colors": stroke_colors,
        "stroke_widths": stroke_widths,
        "page_size": page_size,
        "units": units,
        "page_width": page_width,
        "page_height": page_height,
        "margins": margins,
        "line_height": line_height,
        "align": align,
        "background": background,
        "global_scale": global_scale,
        "orientation": orientation,
        "legibility": legibility,
        "x_stretch": x_stretch,
        "denoise": denoise,
        "empty_line_spacing": empty_line_spacing,
        "auto_size": auto_size,
        "manual_size_scale": manual_size_scale,
        "handwriting_size": handwriting_size,
        "character_override_collection_id": character_override_collection_id,
        "wrap_char_px": wrap_char_px,
        "wrap_ratio": wrap_ratio,
        "wrap_utilization": wrap_utilization,
        "use_chunked": use_chunked,
        "max_line_width": max_line_width,
        "words_per_chunk": words_per_chunk,
        "chunk_spacing": chunk_spacing,
        "rotate_chunks": rotate_chunks,
        "min_words_per_chunk": min_words_per_chunk,
        "max_words_per_chunk": max_words_per_chunk,
        "target_chars_per_chunk": target_chars_per_chunk,
        "adaptive_chunking": adaptive_chunking,
        "adaptive_strategy": adaptive_strategy,
    }


def generate_handwriting_to_file(
    hand: Hand,
    filename: str,
    params: Dict[str, Any],
) -> None:
    """
    Generate handwriting to a file using parsed parameters.

    This is the core generation function that handles both chunked and non-chunked
    generation modes. It's used by both individual and batch generation.

    Args:
        hand: Hand instance to use for generation.
        filename: Output file path.
        params: Normalized parameters from parse_generation_params().
    """
    # Parse lines from text or lines parameter
    if params["text"] is not None:
        lines_in = params["text"].splitlines() if isinstance(params["text"], str) else params["text"]
    elif params["lines"] is not None:
        lines_in = params["lines"] if isinstance(params["lines"], list) else [params["lines"]]
    else:
        raise ValueError("No text or lines provided")

    if not lines_in:
        raise ValueError("Empty text provided")

    # Load character overrides to get override characters BEFORE text normalization
    override_chars = None
    if params["character_override_collection_id"] is not None:
        try:
            from handwriting_synthesis.hand.character_override_utils import get_character_overrides
            overrides_dict = get_character_overrides(params["character_override_collection_id"])
            if overrides_dict:
                override_chars = set(overrides_dict.keys())
        except Exception as e:
            print(f"Warning: Could not load character overrides: {e}")

    # Normalize text, preserving characters that have overrides
    norm_lines_in = ["" if ln.strip() == "\\" else normalize_text_for_model(ln, override_chars) for ln in lines_in]

    # Compute page dimensions for wrapping
    w_px, h_px = resolve_page_px(
        params["page_size"],
        params["units"],
        params["page_width"],
        params["page_height"],
        params["orientation"]
    )
    m_top, m_right, m_bottom, m_left = margins_to_px(params["margins"], params["units"])
    content_width_px = max(1.0, w_px - (m_left + m_right))

    # Build page size parameter
    if params["page_width"] and params["page_height"]:
        page_size_param = [float(params["page_width"]), float(params["page_height"])]
    else:
        page_size_param = params["page_size"]

    if params["use_chunked"]:
        # Chunked generation mode
        full_text = '\n'.join(norm_lines_in)

        # Use first value from lists for chunked mode
        bias_val = params["biases"][0] if params["biases"] and len(params["biases"]) > 0 else None
        style_val = params["styles"][0] if params["styles"] and len(params["styles"]) > 0 else None
        color_val = params["stroke_colors"][0] if params["stroke_colors"] and len(params["stroke_colors"]) > 0 else None
        width_val = params["stroke_widths"][0] if params["stroke_widths"] and len(params["stroke_widths"]) > 0 else None

        hand.write_chunked(
            filename=filename,
            text=full_text,
            max_line_width=params["max_line_width"],
            words_per_chunk=params["words_per_chunk"],
            chunk_spacing=params["chunk_spacing"],
            rotate_chunks=params["rotate_chunks"],
            min_words_per_chunk=params["min_words_per_chunk"],
            max_words_per_chunk=params["max_words_per_chunk"],
            target_chars_per_chunk=params["target_chars_per_chunk"],
            adaptive_chunking=params["adaptive_chunking"],
            adaptive_strategy=params["adaptive_strategy"],
            biases=bias_val,
            styles=style_val,
            stroke_colors=color_val,
            stroke_widths=width_val,
            page_size=page_size_param,
            units=params["units"],
            margins=params["margins"],
            line_height=params["line_height"],
            align=params["align"],
            background=params["background"],
            global_scale=params["global_scale"],
            orientation=params["orientation"],
            legibility=params["legibility"],
            x_stretch=params["x_stretch"],
            denoise=params["denoise"],
            empty_line_spacing=params["empty_line_spacing"],
            auto_size=params["auto_size"],
            manual_size_scale=params["manual_size_scale"],
            handwriting_size=params["handwriting_size"],
            character_override_collection_id=params["character_override_collection_id"],
        )
    else:
        # Traditional line-by-line generation with wrapping
        lh_px = _line_height_px(params["units"], params["line_height"])
        approx_char_px = (
            float(params["wrap_char_px"])
            if params["wrap_char_px"] is not None
            else (lh_px * float(params["wrap_ratio"]) if params["wrap_ratio"] is not None else 10.5)
        )
        util = float(params["wrap_utilization"]) if params["wrap_utilization"] is not None else 1.35

        lines, src_index = wrap_by_canvas(
            norm_lines_in,
            content_width_px,
            max_chars_per_line=75,
            approx_char_px=approx_char_px,
            utilization=util,
        )

        if not any(line.strip() for line in lines):
            raise ValueError("No non-empty text lines provided")

        # Map per-original-line sequences to wrapped lines
        orig_len = len(norm_lines_in)
        wrapped_len = len(lines)
        biases_m = _map_sequence_to_wrapped(params["biases"], src_index, orig_len, wrapped_len)
        styles_m = _map_sequence_to_wrapped(params["styles"], src_index, orig_len, wrapped_len)
        stroke_colors_m = _map_sequence_to_wrapped(params["stroke_colors"], src_index, orig_len, wrapped_len)
        stroke_widths_m = _map_sequence_to_wrapped(params["stroke_widths"], src_index, orig_len, wrapped_len)

        hand.write(
            filename=filename,
            lines=lines,
            biases=biases_m,
            styles=styles_m,
            stroke_colors=stroke_colors_m,
            stroke_widths=stroke_widths_m,
            page_size=page_size_param,
            units=params["units"],
            margins=params["margins"],
            line_height=params["line_height"],
            align=params["align"],
            background=params["background"],
            global_scale=params["global_scale"],
            orientation=params["orientation"],
            legibility=params["legibility"],
            x_stretch=params["x_stretch"],
            denoise=params["denoise"],
            empty_line_spacing=params["empty_line_spacing"],
            auto_size=params["auto_size"],
            manual_size_scale=params["manual_size_scale"],
            handwriting_size=params["handwriting_size"],
            character_override_collection_id=params["character_override_collection_id"],
        )


def generate_svg_from_params(hand: Hand, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Generate handwriting SVG from parameters and return the SVG text with metadata.

    This is used by the individual generation API endpoints.

    Args:
        hand: Hand instance to use for generation.
        params: Normalized parameters from parse_generation_params().

    Returns:
        Tuple of (svg_text, metadata_dict).
    """
    # Generate to temp file, then read
    tmp_dir = tempfile.mkdtemp(prefix="writebot_api_")
    out_path = os.path.join(tmp_dir, "output.svg")

    try:
        generate_handwriting_to_file(hand, out_path, params)

        with open(out_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Build metadata
    w_px, h_px = resolve_page_px(
        params["page_size"],
        params["units"],
        params["page_width"],
        params["page_height"],
        params["orientation"]
    )
    m_top, m_right, m_bottom, m_left = margins_to_px(params["margins"], params["units"])

    # Parse lines for metadata
    if params["text"] is not None:
        lines_in = params["text"].splitlines() if isinstance(params["text"], str) else params["text"]
    elif params["lines"] is not None:
        lines_in = params["lines"] if isinstance(params["lines"], list) else [params["lines"]]
    else:
        lines_in = []

    meta = {
        "page": {
            "width_px": w_px,
            "height_px": h_px,
            "width_mm": round(w_px / (96.0 / 25.4), 3),
            "height_mm": round(h_px / (96.0 / 25.4), 3),
            "units": params["units"],
            "orientation": params["orientation"],
            "margins_px": [m_top, m_right, m_bottom, m_left],
        },
        "wrap": {
            "approx_char_px": params.get("wrap_char_px"),
            "utilization": params.get("wrap_utilization"),
        },
        "lines": {
            "input_count": len(lines_in),
        },
        "render": {
            "legibility": params["legibility"],
            "x_stretch": params["x_stretch"],
            "denoise": params["denoise"],
            "use_chunked": params["use_chunked"],
        },
    }

    return svg_text, meta
