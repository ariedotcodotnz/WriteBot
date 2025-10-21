import io
import os
import shutil
import tempfile
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple, Union
import re
import unicodedata
import uuid
import json

from flask import Flask, jsonify, request, send_file, send_from_directory, Response, stream_with_context
try:
    from flask_compress import Compress  # optional
except Exception:  # pragma: no cover
    Compress = None
import base64
import numpy as np

import sys

# Ensure project root is in sys.path so 'handwriting_synthesis' can be imported when running from webapp/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.hand.Hand import Hand
from handwriting_synthesis.config import style_path as STYLE_DIR
from handwriting_synthesis.drawing import operations as draw_ops


_DIST_DIR = os.path.join(os.path.dirname(__file__), 'dist')

app = Flask(__name__, static_folder="static", static_url_path="/static")
if Compress is not None:
    try:
        Compress(app)
    except Exception:
        pass


# Unit conversion and paper sizes (mirror drawing constants)
PX_PER_MM = 96.0 / 25.4
PAPER_SIZES_MM = {
    'A5': (148.0, 210.0),
    'A4': (210.0, 297.0),
    'Letter': (215.9, 279.4),
    'Legal': (215.9, 355.6),
}


def _to_px(v: float, units: str) -> float:
    try:
        f = float(v)
    except Exception:
        return 0.0
    return f * PX_PER_MM if units == 'mm' else f


def _margins_to_px(margins: Union[float, int, List[float], Dict[str, float]], units: str) -> Tuple[float, float, float, float]:
    # Reuse semantics of _parse_margins input; convert to px
    def to_tuple(m) -> Tuple[float, float, float, float]:
        if isinstance(m, (int, float)):
            t = r = b = l = float(m)
        elif isinstance(m, (list, tuple)) and len(m) == 4:
            t, r, b, l = [float(x) for x in m]
        elif isinstance(m, dict):
            t = float(m.get('top', 0)); r = float(m.get('right', 0)); b = float(m.get('bottom', 0)); l = float(m.get('left', 0))
        else:
            t = r = b = l = 0.0
        return t, r, b, l
    t, r, b, l = to_tuple(margins)
    return _to_px(t, units), _to_px(r, units), _to_px(b, units), _to_px(l, units)


def _resolve_page_px(page_size: Union[str, List[float], Tuple[float, float]], units: str, page_width: Optional[float], page_height: Optional[float], orientation: str) -> Tuple[float, float]:
    # page_size may be a std name or ignored if explicit width/height provided
    if page_width and page_height:
        w_px, h_px = _to_px(page_width, units), _to_px(page_height, units)
    elif isinstance(page_size, str) and page_size in PAPER_SIZES_MM:
        w_mm, h_mm = PAPER_SIZES_MM[page_size]
        w_px, h_px = _to_px(w_mm, 'mm'), _to_px(h_mm, 'mm')
    elif isinstance(page_size, (list, tuple)) and len(page_size) == 2:
        w_px, h_px = _to_px(page_size[0], units), _to_px(page_size[1], units)
    else:
        # Default
        w_px, h_px = _to_px(210, 'mm'), _to_px(297, 'mm')
    if orientation == 'landscape':
        w_px, h_px = h_px, w_px
    return w_px, h_px
def _generate_svg_text_from_payload(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
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

    # New chunk-based generation params (now default for better long-range dependency handling)
    use_chunked = payload.get("use_chunked", True)  # Changed default to True
    words_per_chunk = int(payload.get("words_per_chunk", 3))  # Increased to 3 for better context with dynamic sizing
    chunk_spacing = float(payload.get("chunk_spacing", 8.0))
    rotate_chunks = payload.get("rotate_chunks", True)  # NEW: Enable rotation correction
    min_words_per_chunk = int(payload.get("min_words_per_chunk", 2))  # NEW: Minimum words per chunk
    max_words_per_chunk = int(payload.get("max_words_per_chunk", 8))  # NEW: Maximum words per chunk
    target_chars_per_chunk = int(payload.get("target_chars_per_chunk", 25))  # NEW: Target chars per chunk

    # Compute content width in px for wrapping
    w_px, h_px = _resolve_page_px(page_size, units, page_width, page_height, orientation)
    m_top, m_right, m_bottom, m_left = _margins_to_px(margins, units)
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

    norm_lines_in = ["" if ln.strip() == "\\" else _normalize_text_for_model(ln) for ln in lines_in]

    # Generate to temp file, then read text
    tmp_dir = tempfile.mkdtemp(prefix="writebot_api_")
    out_path = os.path.join(tmp_dir, "output.svg")

    try:
        if use_chunked:
            # Chunk-based generation: preserve newlines for line breaks and blank lines
            full_text = '\n'.join(norm_lines_in)

            # Calculate max_line_width in coordinate units
            # Estimate based on content width: roughly 600 units fits ~75 chars before scaling
            # So we scale proportionally: max_line_width = 600 * (content_width_px / expected_scaled_width)
            # For simplicity, use a configurable default with adjustment for content width
            util = None
            lines = []
            max_line_width = None
            max_line_width_param = payload.get("max_line_width")
            if max_line_width_param is not None:
                max_line_width = float(max_line_width_param)
            else:
                # Default: 800 units allows for longer lines (increased from 550)
                # Can be adjusted based on content_width_px if needed
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
            )
        else:
            # Traditional line-by-line generation
            util = float(wrap_utilization) if wrap_utilization is not None else 1.35
            lines, src_index = _wrap_by_canvas(
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
            )

        with open(out_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    meta = {
        "page": {
            "width_px": w_px,
            "height_px": h_px,
            "width_mm": round(w_px / PX_PER_MM, 3),
            "height_mm": round(h_px / PX_PER_MM, 3),
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
            "wrapped_count": len(lines),
        },
        "render": {
            "legibility": legibility,
            "x_stretch": float(x_stretch) if x_stretch is not None else 1.0,
            "denoise": not ((isinstance(denoise, str) and denoise.lower() == 'false') or denoise is False),
        },
    }
    return svg_text, meta


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model_ready": True,
        "version": 1,
    })


@app.route("/api/v1/generate", methods=["POST"])
def api_v1_generate():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    try:
        svg_text, meta = _generate_svg_text_from_payload(payload or {})
        return jsonify({"svg": svg_text, "meta": meta})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/v1/generate/svg", methods=["POST"])
def api_v1_generate_svg():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    try:
        svg_text, _ = _generate_svg_text_from_payload(payload or {})
        return Response(svg_text, mimetype="image/svg+xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def _wrap_by_canvas(
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
    """
    try:
        # Try to use improved text processing
        import sys
        import os
        # Add parent directory to path
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

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


# ---- Text normalization to model's allowed alphabet ----
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


def _normalize_text_for_model(s: str) -> str:
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
hand = Hand()


def _parse_lines(data: Dict[str, Any]) -> List[str]:
    if isinstance(data.get("lines"), list):
        return [str(x) for x in data["lines"]]
    text = data.get("text", "")
    if not isinstance(text, str):
        text = str(text)
    # Normalize newlines; preserve backslash-only lines for blank spacing
    return text.splitlines()


def _line_height_px(units: str, line_height_value: Optional[Union[float, int]]) -> float:
    if line_height_value is None or str(line_height_value).strip() == "":
        return 60.0
    try:
        return _to_px(float(line_height_value), units)
    except Exception:
        return 60.0


def _wrap_text_lines(lines: List[str], max_chars: int = 75) -> List[str]:
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


def _parse_optional_list(value, cast_fn):
    if value is None:
        return None
    if isinstance(value, list):
        return [cast_fn(v) for v in value]
    return [cast_fn(value)]


def _parse_margins(value: Union[None, float, int, List[float], Dict[str, float]]):
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
    # Attempt to parse "t,r,b,l"
    if isinstance(value, str):
        try:
            parts = [float(x.strip()) for x in value.split(",")]
            if len(parts) == 4:
                return parts
        except Exception:
            pass
    return 20


def _map_sequence_to_wrapped(seq: Optional[List[Any]], src_index: List[int], original_len: int, wrapped_len: int) -> Optional[List[Any]]:
    """Map a per-original-line sequence to per-wrapped-line using src_index.
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

@app.route("/")
def index():
    # If a built dist exists, serve hashed index; otherwise serve static index as-is
    dist_index_candidates = []
    if os.path.isdir(_DIST_DIR):
        for name in os.listdir(_DIST_DIR):
            if name.startswith('index.') and name.endswith('.html'):
                dist_index_candidates.append(name)
    if dist_index_candidates:
        return send_from_directory(_DIST_DIR, sorted(dist_index_candidates)[-1])
    # Fallback: serve original static index without transformation to ensure stability
    return send_from_directory(app.static_folder, "index.html")


def _iter_style_ids(style_dir: str) -> List[int]:
    ids: List[int] = []
    if not os.path.isdir(style_dir):
        return ids
    for name in os.listdir(style_dir):
        if name.startswith('style-') and name.endswith('-chars.npy'):
            m = re.match(r"style-(\d+)-chars\.npy$", name)
            if m:
                try:
                    ids.append(int(m.group(1)))
                except Exception:
                    continue
    return sorted(set(ids))


@app.route("/api/styles", methods=["GET"])
def list_styles():
    """List available handwriting styles and their priming text.

    Returns a JSON object: { styles: [ { id, label, text } ] }
    """
    styles: List[Dict[str, Any]] = []
    try:
        if os.path.isdir(STYLE_DIR):
            for name in sorted(os.listdir(STYLE_DIR)):
                # Expect files like style-<id>-chars.npy
                if not name.startswith("style-") or not name.endswith("-chars.npy"):
                    continue
                try:
                    m = re.match(r"style-(\d+)-chars\.npy$", name)
                    if not m:
                        continue
                    sid = int(m.group(1))
                    chars_path = os.path.join(STYLE_DIR, name)
                    try:
                        # numpy >=1.19 recommends .tobytes(); maintain compatibility
                        arr = np.load(chars_path, allow_pickle=False)
                        # Stored as bytes representing utf-8 string
                        try:
                            priming_text = arr.tobytes().decode("utf-8", errors="ignore")
                        except Exception:
                            # Fallback for legacy .tostring
                            priming_text = arr.tostring().decode("utf-8", errors="ignore")  # type: ignore[attr-defined]
                    except Exception:
                        priming_text = ""
                    styles.append({
                        "id": sid,
                        "label": f"Style {sid}",
                        "text": priming_text,
                    })
                except Exception:
                    continue
        styles.sort(key=lambda x: int(x.get("id", 0)))
        return jsonify({"styles": styles})
    except Exception as e:
        return jsonify({"styles": [], "error": str(e)}), 200


# Removed: /api/styles/<id>/sample


@app.route("/api/generate", methods=["POST"])
def generate_svg():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    lines_in = _parse_lines(payload)
    if not lines_in:
        return jsonify({"error": "No text or lines provided"}), 400

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

    # Compute content width in px for wrapping
    w_px, h_px = _resolve_page_px(page_size, units, page_width, page_height, orientation)
    m_top, m_right, m_bottom, m_left = _margins_to_px(margins, units)
    content_width_px = max(1.0, w_px - (m_left + m_right))
    # Estimate character width using line-height-based ratio (tunable)
    lh_px = _line_height_px(units, line_height)
    wrap_char_px = payload.get("wrap_char_px")
    wrap_ratio = payload.get("wrap_ratio")
    wrap_utilization = payload.get("wrap_utilization")
    # Default to a constant character width so wrapping is independent of line height
    approx_char_px = (
        float(wrap_char_px)
        if wrap_char_px is not None
        else (lh_px * float(wrap_ratio) if wrap_ratio is not None else 10.5)
    )

    # Greedy word-wrap by canvas width; also respects per-line 75-char model cap
    # Normalize characters per model alphabet; preserve backslash-only lines
    norm_lines_in = ["" if ln.strip() == "\\" else _normalize_text_for_model(ln) for ln in lines_in]
    util = float(wrap_utilization) if wrap_utilization is not None else 1.35
    lines, src_index = _wrap_by_canvas(
        norm_lines_in,
        content_width_px,
        max_chars_per_line=75,
        approx_char_px=approx_char_px,
        utilization=util,
    )
    orig_len = len(norm_lines_in)
    wrapped_len = len(lines)
    biases_m = _map_sequence_to_wrapped(biases, src_index, orig_len, wrapped_len)
    styles_m = _map_sequence_to_wrapped(styles, src_index, orig_len, wrapped_len)
    stroke_colors_m = _map_sequence_to_wrapped(stroke_colors, src_index, orig_len, wrapped_len)
    stroke_widths_m = _map_sequence_to_wrapped(stroke_widths, src_index, orig_len, wrapped_len)
    # Validate at least one non-empty line remains (blank lines allowed)
    if not any(line.strip() for line in lines):
        return jsonify({"error": "No non-empty text lines provided"}), 400

    # Write to a temporary file then stream back
    tmp_dir = tempfile.mkdtemp(prefix="writebot_")
    try:
        out_path = os.path.join(tmp_dir, "output.svg")
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
        )
        return send_file(out_path, mimetype="image/svg+xml", as_attachment=False, download_name="handwriting.svg")
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        # Clean up the temp dir on next GC cycle
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _get_row_value(row: Dict[str, Any], key: str, default=None):
    v = row.get(key)
    return default if (v is None or (isinstance(v, float) and str(v) == "nan")) else v


@app.route("/api/batch", methods=["POST"])
def batch_generate():
    if "file" not in request.files:
        return jsonify({"error": "CSV file is required under 'file' field"}), 400

    csv_file = request.files["file"]
    try:
        import pandas as pd
        df = pd.read_csv(csv_file)
    except Exception:
        return jsonify({"error": "Failed to read CSV"}), 400

    # Defaults from query/body
    defaults = request.form.to_dict(flat=True)
    # Non-form JSON defaults if provided
    try:
        json_defaults = request.get_json(silent=True) or {}
        defaults.update(json_defaults)
    except Exception:
        pass

    tmp_dir = tempfile.mkdtemp(prefix="writebot_batch_")
    out_dir = os.path.join(tmp_dir, "out")
    os.makedirs(out_dir, exist_ok=True)

    generated_files: List[str] = []
    errors: List[Tuple[int, str]] = []

    for idx, row in df.fillna("").iterrows():
        row_dict = row.to_dict()
        try:
            text = _get_row_value(row_dict, "text", defaults.get("text", ""))
            if not isinstance(text, str):
                text = str(text)
            lines_in = text.splitlines()
            if not lines_in:
                raise ValueError("Empty text")

            filename = _get_row_value(row_dict, "filename", f"sample_{idx}.svg")

            biases = _get_row_value(row_dict, "biases", defaults.get("biases"))
            styles = _get_row_value(row_dict, "styles", defaults.get("styles"))
            stroke_colors = _get_row_value(row_dict, "stroke_colors", defaults.get("stroke_colors"))
            stroke_widths = _get_row_value(row_dict, "stroke_widths", defaults.get("stroke_widths"))
            page_size = _get_row_value(row_dict, "page_size", defaults.get("page_size", "A4"))
            units = _get_row_value(row_dict, "units", defaults.get("units", "mm"))
            page_width = _get_row_value(row_dict, "page_width", defaults.get("page_width"))
            page_height = _get_row_value(row_dict, "page_height", defaults.get("page_height"))
            margins = _get_row_value(row_dict, "margins", defaults.get("margins", 20))
            line_height = _get_row_value(row_dict, "line_height", defaults.get("line_height"))
            align = _get_row_value(row_dict, "align", defaults.get("align", "left"))
            background = _get_row_value(row_dict, "background", defaults.get("background", "white"))
            global_scale = float(_get_row_value(row_dict, "global_scale", defaults.get("global_scale", 1.0)))
            orientation = _get_row_value(row_dict, "orientation", defaults.get("orientation", "portrait"))

            # Convert some string-encoded lists
            def parse_list(v, cast):
                if v is None or v == "":
                    return None
                # Normalize list-like inputs
                if isinstance(v, list):
                    out = []
                    for x in v:
                        s = str(x).strip()
                        if s == "" or s.lower() == "nan":
                            continue
                        try:
                            out.append(cast(s))
                        except Exception:
                            # skip invalid tokens
                            continue
                    return out or None
                if isinstance(v, str):
                    out = []
                    for p in v.split("|"):
                        s = p.strip()
                        if s == "" or s.lower() == "nan":
                            continue
                        try:
                            out.append(cast(s))
                        except Exception:
                            continue
                    return out or None
                try:
                    return [cast(v)]
                except Exception:
                    return None

            biases = parse_list(biases, float)
            styles = parse_list(styles, int)
            stroke_colors = parse_list(stroke_colors, str)
            stroke_widths = parse_list(stroke_widths, float)
            margins = _parse_margins(margins)

            # Compute wrapping by canvas width
            w_px, h_px = _resolve_page_px(page_size, units, page_width, page_height, orientation)
            m_top, m_right, m_bottom, m_left = _margins_to_px(margins, units)
            content_width_px = max(1.0, w_px - (m_left + m_right))
            norm_lines_in = ["" if ln.strip() == "\\" else _normalize_text_for_model(ln) for ln in lines_in]
            lh_px = _line_height_px(units, line_height)
            wrap_char_px = _get_row_value(row_dict, "wrap_char_px", defaults.get("wrap_char_px"))
            wrap_ratio = _get_row_value(row_dict, "wrap_ratio", defaults.get("wrap_ratio"))
            wrap_utilization = _get_row_value(row_dict, "wrap_utilization", defaults.get("wrap_utilization"))
            approx_char_px = (
                float(wrap_char_px)
                if wrap_char_px not in (None, "")
                else (lh_px * float(wrap_ratio) if wrap_ratio not in (None, "") else 10.5)
            )
            util = float(wrap_utilization) if wrap_utilization not in (None, "") else 1.35
            lines, src_index = _wrap_by_canvas(
                norm_lines_in,
                content_width_px,
                max_chars_per_line=75,
                approx_char_px=approx_char_px,
                utilization=util,
            )
            orig_len = len(norm_lines_in)
            wrapped_len = len(lines)
            biases_m = _map_sequence_to_wrapped(biases, src_index, orig_len, wrapped_len)
            styles_m = _map_sequence_to_wrapped(styles, src_index, orig_len, wrapped_len)
            stroke_colors_m = _map_sequence_to_wrapped(stroke_colors, src_index, orig_len, wrapped_len)
            stroke_widths_m = _map_sequence_to_wrapped(stroke_widths, src_index, orig_len, wrapped_len)
            if not any(line.strip() for line in lines):
                raise ValueError("No non-empty text lines provided")

            out_path = os.path.join(out_dir, os.path.basename(filename))

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
            )
            generated_files.append(out_path)
        except Exception as e:
            errors.append((idx, str(e)))

    # Package ZIP
    zip_path = os.path.join(tmp_dir, f"writebot_batch_{int(time.time())}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in generated_files:
            zf.write(path, arcname=os.path.basename(path))

    # If there were errors, add a log file
    if errors:
        error_log = os.path.join(tmp_dir, "errors.txt")
        with open(error_log, "w", encoding="utf-8") as f:
            for idx, msg in errors:
                f.write(f"row {idx}: {msg}\n")
        with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED) as zf:
            zf.write(error_log, arcname="errors.txt")

    return send_file(zip_path, mimetype="application/zip", as_attachment=True, download_name=os.path.basename(zip_path))


@app.route("/api/template-csv", methods=["GET"])
def template_csv():
    header = (
        "filename,text,page_size,units,page_width,page_height,margins,line_height,align,background,global_scale,orientation,biases,styles,stroke_colors,stroke_widths,wrap_char_px,wrap_ratio,wrap_utilization,legibility,x_stretch,denoise,use_chunked,words_per_chunk,chunk_spacing,rotate_chunks,min_words_per_chunk,max_words_per_chunk,target_chars_per_chunk\n"
    )
    return Response(header, mimetype="text/csv", headers={
        'Content-Disposition': 'attachment; filename=writebot_template.csv'
    })


# ---- Streaming batch processing (SSE-like over fetch streaming) ----
JOBS_ROOT = os.path.join(tempfile.gettempdir(), "writebot_jobs")
os.makedirs(JOBS_ROOT, exist_ok=True)


def _sse(obj: Dict[str, Any]) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.route("/api/batch/stream", methods=["POST"])
def batch_stream():
    if "file" not in request.files:
        return jsonify({"error": "CSV file is required under 'file' field"}), 400

    csv_file = request.files["file"]
    try:
        import pandas as pd
        df = pd.read_csv(csv_file)
    except Exception as e:
        return jsonify({"error": f"Failed to read CSV: {e}"}), 400

    defaults = request.form.to_dict(flat=True)

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(JOBS_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)
    out_dir = os.path.join(job_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(job_dir, "results.zip")

    def gen():
        # Start event
        yield _sse({"type": "start", "job_id": job_id, "total": int(len(df))})

        generated_files: List[str] = []
        errors: List[Tuple[int, str]] = []

        def parse_list(v, cast):
            if v is None or v == "":
                return None
            if isinstance(v, list):
                out = []
                for x in v:
                    s = str(x).strip()
                    if s == "" or s.lower() == "nan":
                        continue
                    try:
                        out.append(cast(s))
                    except Exception:
                        continue
                return out or None
            if isinstance(v, str):
                out = []
                for p in v.split("|"):
                    s = p.strip()
                    if s == "" or s.lower() == "nan":
                        continue
                    try:
                        out.append(cast(s))
                    except Exception:
                        continue
                return out or None
            try:
                return [cast(v)]
            except Exception:
                return None

        for idx, row in df.fillna("").iterrows():
            row_dict = row.to_dict()
            try:
                text = _get_row_value(row_dict, "text", defaults.get("text", ""))
                if not isinstance(text, str):
                    text = str(text)
                lines_in = text.splitlines()
                if not lines_in:
                    raise ValueError("Empty text")

                filename = _get_row_value(row_dict, "filename", f"sample_{idx}.svg")

                biases = _get_row_value(row_dict, "biases", defaults.get("biases"))
                styles = _get_row_value(row_dict, "styles", defaults.get("styles"))
                stroke_colors = _get_row_value(row_dict, "stroke_colors", defaults.get("stroke_colors"))
                stroke_widths = _get_row_value(row_dict, "stroke_widths", defaults.get("stroke_widths"))
                page_size = _get_row_value(row_dict, "page_size", defaults.get("page_size", "A4"))
                units = _get_row_value(row_dict, "units", defaults.get("units", "mm"))
                page_width = _get_row_value(row_dict, "page_width", defaults.get("page_width"))
                page_height = _get_row_value(row_dict, "page_height", defaults.get("page_height"))
                margins = _get_row_value(row_dict, "margins", defaults.get("margins", 20))
                line_height = _get_row_value(row_dict, "line_height", defaults.get("line_height"))
                align = _get_row_value(row_dict, "align", defaults.get("align", "left"))
                background = _get_row_value(row_dict, "background", defaults.get("background", "white"))
                global_scale = float(_get_row_value(row_dict, "global_scale", defaults.get("global_scale", 1.0)))
                orientation = _get_row_value(row_dict, "orientation", defaults.get("orientation", "portrait"))
                wrap_char_px = _get_row_value(row_dict, "wrap_char_px", defaults.get("wrap_char_px"))
                wrap_ratio = _get_row_value(row_dict, "wrap_ratio", defaults.get("wrap_ratio"))
                wrap_utilization = _get_row_value(row_dict, "wrap_utilization", defaults.get("wrap_utilization"))
                legibility = _get_row_value(row_dict, "legibility", defaults.get("legibility", "normal"))
                x_stretch = _get_row_value(row_dict, "x_stretch", defaults.get("x_stretch"))
                denoise = _get_row_value(row_dict, "denoise", defaults.get("denoise"))

                biases = parse_list(biases, float)
                styles = parse_list(styles, int)
                stroke_colors = parse_list(stroke_colors, str)
                stroke_widths = parse_list(stroke_widths, float)
                margins = _parse_margins(margins)

                # Wrapping by canvas width
                w_px, h_px = _resolve_page_px(page_size, units, page_width, page_height, orientation)
                m_top, m_right, m_bottom, m_left = _margins_to_px(margins, units)
                content_width_px = max(1.0, w_px - (m_left + m_right))
                norm_lines_in = ["" if ln.strip() == "\\" else _normalize_text_for_model(ln) for ln in lines_in]
                lh_px = _line_height_px(units, line_height)
                approx_char_px = (
                    float(wrap_char_px)
                    if wrap_char_px not in (None, "")
                    else (lh_px * float(wrap_ratio) if wrap_ratio not in (None, "") else 10.5)
                )
                util = float(wrap_utilization) if wrap_utilization not in (None, "") else 1.35
                lines, src_index = _wrap_by_canvas(
                    norm_lines_in,
                    content_width_px,
                    max_chars_per_line=75,
                    approx_char_px=approx_char_px,
                    utilization=util,
                )
                orig_len = len(norm_lines_in)
                wrapped_len = len(lines)
                biases_m = _map_sequence_to_wrapped(biases, src_index, orig_len, wrapped_len)
                styles_m = _map_sequence_to_wrapped(styles, src_index, orig_len, wrapped_len)
                stroke_colors_m = _map_sequence_to_wrapped(stroke_colors, src_index, orig_len, wrapped_len)
                stroke_widths_m = _map_sequence_to_wrapped(stroke_widths, src_index, orig_len, wrapped_len)
                if not any(line.strip() for line in lines):
                    raise ValueError("No non-empty text lines provided")

                out_path = os.path.join(out_dir, os.path.basename(filename))

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
                    x_stretch=float(x_stretch) if x_stretch not in (None, "") else 1.0,
                    denoise=False if str(denoise).lower() == 'false' else True,
                )
                generated_files.append(out_path)
                yield _sse({
                    "type": "row",
                    "status": "ok",
                    "row": int(idx),
                    "file": os.path.basename(out_path),
                    "job_id": job_id,
                })
            except Exception as e:
                errors.append((int(idx), str(e)))
                yield _sse({
                    "type": "row",
                    "status": "error",
                    "row": int(idx),
                    "error": str(e),
                    "job_id": job_id,
                })

            yield _sse({"type": "progress", "completed": int(idx) + 1, "total": int(len(df))})

        # Package zip
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in generated_files:
                zf.write(path, arcname=os.path.basename(path))
            if errors:
                error_log = os.path.join(job_dir, "errors.txt")
                with open(error_log, "w", encoding="utf-8") as f:
                    for idx, msg in errors:
                        f.write(f"row {idx}: {msg}\n")
                zf.write(error_log, arcname="errors.txt")

        download_url = f"/api/batch/result/{job_id}"
        yield _sse({
            "type": "done",
            "job_id": job_id,
            "download": download_url,
            "total": int(len(df)),
            "success": int(len(generated_files)),
            "errors": int(len(errors)),
        })

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return Response(stream_with_context(gen()), headers=headers)


@app.route("/api/batch/result/<job_id>", methods=["GET"])
def batch_result(job_id: str):
    job_dir = os.path.join(JOBS_ROOT, job_id)
    zip_path = os.path.join(job_dir, "results.zip")
    if not os.path.isfile(zip_path):
        return jsonify({"error": "Result not found or expired"}), 404
    return send_file(zip_path, mimetype="application/zip", as_attachment=True, download_name=f"writebot_batch_{job_id}.zip")


@app.route("/api/batch/result/<job_id>/file/<path:filename>", methods=["GET"])
def batch_result_file(job_id: str, filename: str):
    """Serve an individual generated file from a batch job for live preview."""
    job_dir = os.path.join(JOBS_ROOT, job_id)
    out_dir = os.path.join(job_dir, "out")
    if not os.path.isdir(out_dir):
        return jsonify({"error": "Job not found or expired"}), 404
    # Prevent path traversal
    safe_name = os.path.basename(filename)
    file_path = os.path.join(out_dir, safe_name)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404
    # Guess mimetype by extension (default to SVG for .svg)
    mime = "image/svg+xml" if safe_name.lower().endswith(".svg") else None
    return send_file(file_path, mimetype=mime or "application/octet-stream", as_attachment=False, download_name=safe_name)


if __name__ == "__main__":
    # Single-threaded to avoid TF session concurrency issues
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=False)


