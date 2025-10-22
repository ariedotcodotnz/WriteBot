"""Generation endpoints for handwriting synthesis."""

import os
import sys
import shutil
import tempfile
from typing import Any, Dict
from flask import Blueprint, jsonify, request, Response

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.hand.Hand import Hand
from webapp.utils.page_utils import (
    resolve_page_px,
    margins_to_px,
    line_height_px as _line_height_px,
)
from webapp.utils.text_utils import (
    normalize_text_for_model,
    wrap_by_canvas,
    parse_lines as _parse_lines,
    parse_optional_list as _parse_optional_list,
    parse_margins as _parse_margins,
    map_sequence_to_wrapped as _map_sequence_to_wrapped,
)


# Create blueprint
generation_bp = Blueprint('generation', __name__)

# Initialize Hand model (shared across requests)
hand = Hand()


def _generate_svg_text_from_payload(payload: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Core generation logic extracted for reuse.

    Args:
        payload: Request payload with generation parameters

    Returns:
        Tuple of (svg_text, metadata)
    """
    lines_in = _parse_lines(payload)
    if not lines_in:
        raise ValueError("No text or lines provided")

    # Optional params
    biases = _parse_optional_list(payload.get("biases"), float)
    styles = _parse_optional_list(payload.get("styles"), int)
    stroke_colors = _parse_optional_list(payload.get("stroke_colors"), str)
    stroke_widths = _parse_optional_list(payload.get("stroke_widths"), float)
    page_size = payload.get("page_size", "A4")
    units = payload.get("units", "mm")
    margins = _parse_margins(payload.get("margins"))
    line_height = payload.get("line_height")
    align = payload.get("align", "left")
    background = payload.get("background")
    global_scale = float(payload.get("global_scale", 1.0))
    orientation = payload.get("orientation", "portrait")
    page_width = payload.get("page_width")
    page_height = payload.get("page_height")
    legibility = payload.get("legibility", "normal")
    x_stretch = payload.get("x_stretch")
    denoise = payload.get("denoise")

    # New spacing and sizing parameters
    empty_line_spacing = payload.get("empty_line_spacing")
    auto_size = payload.get("auto_size", True)
    if isinstance(auto_size, str):
        auto_size = auto_size.lower() not in ('false', '0', 'no')
    manual_size_scale = float(payload.get("manual_size_scale", 1.0))

    # Chunk-based generation params
    use_chunked = payload.get("use_chunked", True)
    words_per_chunk = int(payload.get("words_per_chunk", 3))
    chunk_spacing = float(payload.get("chunk_spacing", 8.0))
    rotate_chunks = payload.get("rotate_chunks", True)
    min_words_per_chunk = int(payload.get("min_words_per_chunk", 2))
    max_words_per_chunk = int(payload.get("max_words_per_chunk", 8))
    target_chars_per_chunk = int(payload.get("target_chars_per_chunk", 25))
    adaptive_chunking = payload.get("adaptive_chunking", True)
    adaptive_strategy = payload.get("adaptive_strategy", "balanced")

    # Compute content width in px for wrapping
    w_px, h_px = resolve_page_px(page_size, units, page_width, page_height, orientation)
    m_top, m_right, m_bottom, m_left = margins_to_px(margins, units)
    content_width_px = max(1.0, w_px - (m_left + m_right))

    # Estimate character width
    lh_px = _line_height_px(units, line_height)
    wrap_char_px = payload.get("wrap_char_px")
    wrap_ratio = payload.get("wrap_ratio")
    wrap_utilization = payload.get("wrap_utilization")
    approx_char_px = (
        float(wrap_char_px)
        if wrap_char_px is not None
        else (lh_px * float(wrap_ratio) if wrap_ratio is not None else 10.5)
    )

    norm_lines_in = ["" if ln.strip() == "\\" else normalize_text_for_model(ln) for ln in lines_in]

    # Generate to temp file, then read text
    tmp_dir = tempfile.mkdtemp(prefix="writebot_api_")
    out_path = os.path.join(tmp_dir, "output.svg")

    try:
        if use_chunked:
            # Chunk-based generation: preserve newlines for line breaks and blank lines
            full_text = '\n'.join(norm_lines_in)

            # Calculate max_line_width
            util = None
            lines = []
            max_line_width = None
            max_line_width_param = payload.get("max_line_width")
            if max_line_width_param is not None:
                max_line_width = float(max_line_width_param)
            else:
                max_line_width = 800.0

            # Use first bias/style if provided, otherwise None
            bias_val = biases[0] if biases and len(biases) > 0 else None
            style_val = styles[0] if styles and len(styles) > 0 else None
            color_val = stroke_colors[0] if stroke_colors and len(stroke_colors) > 0 else None
            width_val = stroke_widths[0] if stroke_widths and len(stroke_widths) > 0 else None

            hand.write_chunked(
                filename=out_path,
                text=full_text,
                max_line_width=max_line_width,
                words_per_chunk=words_per_chunk,
                chunk_spacing=chunk_spacing,
                rotate_chunks=rotate_chunks,
                min_words_per_chunk=min_words_per_chunk,
                max_words_per_chunk=max_words_per_chunk,
                target_chars_per_chunk=target_chars_per_chunk,
                adaptive_chunking=adaptive_chunking,
                adaptive_strategy=adaptive_strategy,
                biases=bias_val,
                styles=style_val,
                stroke_colors=color_val,
                stroke_widths=width_val,
                page_size=page_size if not (page_width and page_height) else [float(page_width), float(page_height)],
                units=units,
                margins=margins,
                line_height=line_height,
                align=align,
                background=background,
                global_scale=global_scale,
                orientation=orientation,
                legibility=legibility,
                x_stretch=float(x_stretch) if x_stretch is not None else 1.0,
                denoise=False if (isinstance(denoise, str) and denoise.lower() == 'false') or denoise is False else True,
                empty_line_spacing=empty_line_spacing,
                auto_size=auto_size,
                manual_size_scale=manual_size_scale,
            )
        else:
            # Traditional line-by-line generation
            util = float(wrap_utilization) if wrap_utilization is not None else 1.35
            lines, src_index = wrap_by_canvas(
                norm_lines_in,
                content_width_px,
                max_chars_per_line=75,
                approx_char_px=approx_char_px,
                utilization=util,
            )
            if not any(line.strip() for line in lines):
                raise ValueError("No non-empty text lines provided")

            # Map per-original-line sequences to wrapped
            orig_len = len(norm_lines_in)
            wrapped_len = len(lines)
            biases_m = _map_sequence_to_wrapped(biases, src_index, orig_len, wrapped_len)
            styles_m = _map_sequence_to_wrapped(styles, src_index, orig_len, wrapped_len)
            stroke_colors_m = _map_sequence_to_wrapped(stroke_colors, src_index, orig_len, wrapped_len)
            stroke_widths_m = _map_sequence_to_wrapped(stroke_widths, src_index, orig_len, wrapped_len)

            hand.write(
                filename=out_path,
                lines=lines,
                biases=biases_m,
                styles=styles_m,
                stroke_colors=stroke_colors_m,
                stroke_widths=stroke_widths_m,
                page_size=page_size if not (page_width and page_height) else [float(page_width), float(page_height)],
                units=units,
                margins=margins,
                line_height=line_height,
                align=align,
                background=background,
                global_scale=global_scale,
                orientation=orientation,
                legibility=legibility,
                x_stretch=float(x_stretch) if x_stretch is not None else 1.0,
                denoise=False if (isinstance(denoise, str) and denoise.lower() == 'false') or denoise is False else True,
                empty_line_spacing=empty_line_spacing,
                auto_size=auto_size,
                manual_size_scale=manual_size_scale,
            )

        with open(out_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    meta = {
        "page": {
            "width_px": w_px,
            "height_px": h_px,
            "width_mm": round(w_px / (96.0 / 25.4), 3),
            "height_mm": round(h_px / (96.0 / 25.4), 3),
            "units": units,
            "orientation": orientation,
            "margins_px": [m_top, m_right, m_bottom, m_left],
        },
        "wrap": {
            "approx_char_px": approx_char_px,
            "utilization": util,
        },
        "lines": {
            "input_count": len(lines_in),
            "wrapped_count": len(lines) if not use_chunked else None,
        },
        "render": {
            "legibility": legibility,
            "x_stretch": float(x_stretch) if x_stretch is not None else 1.0,
            "denoise": not ((isinstance(denoise, str) and denoise.lower() == 'false') or denoise is False),
        },
    }
    return svg_text, meta


@generation_bp.route("/api/v1/generate", methods=["POST"])
def api_v1_generate():
    """Generate handwriting and return SVG with metadata."""
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        svg_text, meta = _generate_svg_text_from_payload(payload or {})
        return jsonify({"svg": svg_text, "meta": meta})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@generation_bp.route("/api/v1/generate/svg", methods=["POST"])
def api_v1_generate_svg():
    """Generate handwriting and return raw SVG."""
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        svg_text, _ = _generate_svg_text_from_payload(payload or {})
        return Response(svg_text, mimetype="image/svg+xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@generation_bp.route("/api/generate", methods=["POST"])
def generate_svg():
    """Legacy generation endpoint (for backwards compatibility)."""
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    try:
        svg_text, _ = _generate_svg_text_from_payload(payload or {})
        return Response(svg_text, mimetype="image/svg+xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 400
