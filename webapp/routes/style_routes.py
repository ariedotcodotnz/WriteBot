"""Style management endpoints for handwriting synthesis."""

import os
import sys
import re
from typing import List, Dict, Any
from flask import Blueprint, jsonify, send_file, Response
from flask_login import login_required
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.config import style_path as STYLE_DIR


# Create blueprint
style_bp = Blueprint('style', __name__)


def _iter_style_ids(style_dir: str) -> List[int]:
    """
    Iterate through style directory and extract style IDs.

    Args:
        style_dir: Path to style directory.

    Returns:
        Sorted list of integer style IDs found in the directory.
    """
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


@style_bp.route("/api/styles", methods=["GET"])
@login_required
def list_styles():
    """
    List available handwriting styles and their priming text.

    Scans the style directory for available styles, extracts their IDs and
    associated priming text (the text the model saw in that style), and
    returns a list of metadata objects.

    Returns:
        JSON object: { "styles": [ { "id": int, "label": str, "text": str }, ... ] }
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


@style_bp.route("/api/style-preview/<int:style_id>", methods=["GET"])
@login_required
def get_style_preview(style_id: int):
    """
    Serve SVG preview image for a specific style.

    Args:
        style_id: The style ID to get preview for.

    Returns:
        SVG file content with 'image/svg+xml' mimetype, or a placeholder/error SVG if not found.
    """
    try:
        # Look for SVG preview file
        svg_path = os.path.join(STYLE_DIR, f"style-{style_id}.svg")
        # Normalize path and check it remains within STYLE_DIR
        normalized_svg_path = os.path.normpath(os.path.abspath(svg_path))
        style_dir_abs = os.path.abspath(STYLE_DIR)

        if (normalized_svg_path.startswith(style_dir_abs + os.sep) or normalized_svg_path == style_dir_abs) and os.path.isfile(normalized_svg_path):
            return send_file(normalized_svg_path, mimetype='image/svg+xml')

        # If no preview exists, return a placeholder SVG
        placeholder_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" viewBox="0 0 120 40">
  <rect width="120" height="40" fill="#f4f4f4"/>
  <text x="60" y="22" font-family="Arial, sans-serif" font-size="12" fill="#525252" text-anchor="middle">
    Style {style_id}
  </text>
</svg>'''
        return Response(placeholder_svg, mimetype='image/svg+xml')

    except Exception as e:
        # Return error placeholder
        error_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" viewBox="0 0 120 40">
  <rect width="120" height="40" fill="#ffefef"/>
  <text x="60" y="22" font-family="Arial, sans-serif" font-size="10" fill="#da1e28" text-anchor="middle">
    Error loading preview
  </text>
</svg>'''
        return Response(error_svg, mimetype='image/svg+xml')
