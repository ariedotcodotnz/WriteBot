"""Style management endpoints for handwriting synthesis."""

import os
import sys
import re
from typing import List, Dict, Any
from flask import Blueprint, jsonify
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
        style_dir: Path to style directory

    Returns:
        Sorted list of style IDs
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

    Returns:
        JSON object: { styles: [ { id, label, text } ] }
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
