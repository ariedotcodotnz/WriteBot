"""Generation endpoints for handwriting synthesis."""

import os
import sys
import shutil
import tempfile
import time
from typing import Any, Dict
from flask import Blueprint, jsonify, request, Response, current_app
from flask_login import login_required

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.hand.Hand import Hand
from webapp.extensions import limiter
from webapp.utils.generation_utils import parse_generation_params, generate_svg_from_params
from webapp.utils.text_utils import parse_lines as _parse_lines


# Create blueprint
generation_bp = Blueprint('generation', __name__)

# Initialize Hand model (shared across requests)
hand = Hand()


# Helper function to apply rate limiting conditionally
def apply_rate_limit(limit_string):
    """Apply rate limiting decorator if limiter is available."""
    def decorator(f):
        if limiter:
            return limiter.limit(limit_string)(f)
        return f
    return decorator


def _generate_svg_text_from_payload(payload: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    Core generation logic extracted for reuse.

    Parses the payload, normalizes text and parameters, and invokes the Hand model
    to generate the SVG.

    Args:
        payload: Request payload with generation parameters.

    Returns:
        Tuple of (svg_text, metadata).
    """
    # Parse lines from payload if using legacy format
    lines_in = _parse_lines(payload)
    if lines_in:
        # Convert lines to text for the shared utility
        payload = {**payload, "text": "\n".join(lines_in)}

    if not payload.get("text") and not payload.get("lines"):
        raise ValueError("No text or lines provided")

    # Parse and normalize all parameters using shared utility
    params = parse_generation_params(payload)

    # Generate using shared utility
    svg_text, meta = generate_svg_from_params(hand, params)

    return svg_text, meta


@generation_bp.route("/api/v1/generate", methods=["POST"])
@login_required
@apply_rate_limit("10 per minute")
def api_v1_generate():
    """
    Generate handwriting and return SVG with metadata.

    This is the primary API endpoint for generation, returning a JSON object
    containing both the generated SVG string and comprehensive metadata about
    the generation process.

    Returns:
        JSON response with 'svg' and 'meta' keys.
    """
    from webapp.utils.auth_utils import log_activity, track_generation

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    start_time = time.time()
    try:
        svg_text, meta = _generate_svg_text_from_payload(payload or {})

        # Track statistics
        processing_time = time.time() - start_time
        lines_count = meta.get('lines', {}).get('input_count', 0)
        text_content = payload.get('text', '') if isinstance(payload, dict) else ''
        chars_count = len(text_content)

        track_generation(lines_count=lines_count, chars_count=chars_count,
                         processing_time=processing_time, is_batch=False)
        log_activity('generate', f'Generated {lines_count} lines')

        # Add generation time to meta
        meta['generation_time_seconds'] = round(processing_time, 3)

        return jsonify({"svg": svg_text, "meta": meta})
    except ValueError as e:
        # ValueError is typically a validation error (invalid params), safe to show
        current_app.logger.warning(f'Generation validation error: {e}')
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception('Generation error')
        return jsonify({"error": "Failed to generate handwriting. Please check your parameters."}), 400


@generation_bp.route("/api/v1/generate/svg", methods=["POST"])
@login_required
@apply_rate_limit("10 per minute")
def api_v1_generate_svg():
    """
    Generate handwriting and return raw SVG.

    This endpoint returns the raw SVG data directly with the appropriate MIME type,
    suitable for embedding directly in `<img>` tags or downloading.

    Returns:
        Response object with SVG content and 'image/svg+xml' mimetype.
    """
    from webapp.utils.auth_utils import log_activity, track_generation

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    start_time = time.time()
    try:
        svg_text, meta = _generate_svg_text_from_payload(payload or {})

        # Track statistics
        processing_time = time.time() - start_time
        lines_count = meta.get('lines', {}).get('input_count', 0)
        text_content = payload.get('text', '') if isinstance(payload, dict) else ''
        chars_count = len(text_content)

        track_generation(lines_count=lines_count, chars_count=chars_count,
                         processing_time=processing_time, is_batch=False)
        log_activity('generate', f'Generated {lines_count} lines (SVG only)')

        return Response(svg_text, mimetype="image/svg+xml")
    except ValueError as e:
        current_app.logger.warning(f'Generation validation error: {e}')
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception('Generation error (SVG)')
        return jsonify({"error": "Failed to generate handwriting. Please check your parameters."}), 400


@generation_bp.route("/api/generate", methods=["POST"])
@login_required
@apply_rate_limit("10 per minute")
def generate_svg():
    """
    Legacy generation endpoint (for backwards compatibility).

    Maintained for compatibility with older clients. Behaves like `/api/v1/generate/svg`.

    Returns:
        Response object with SVG content.
    """
    from webapp.utils.auth_utils import log_activity, track_generation

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    start_time = time.time()
    try:
        svg_text, meta = _generate_svg_text_from_payload(payload or {})

        # Track statistics
        processing_time = time.time() - start_time
        lines_count = meta.get('lines', {}).get('input_count', 0)
        text_content = payload.get('text', '') if isinstance(payload, dict) else ''
        chars_count = len(text_content)

        track_generation(lines_count=lines_count, chars_count=chars_count,
                         processing_time=processing_time, is_batch=False)
        log_activity('generate', f'Generated {lines_count} lines (legacy)')

        return Response(svg_text, mimetype="image/svg+xml")
    except ValueError as e:
        current_app.logger.warning(f'Generation validation error (legacy): {e}')
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.exception('Generation error (legacy)')
        return jsonify({"error": "Failed to generate handwriting. Please check your parameters."}), 400
