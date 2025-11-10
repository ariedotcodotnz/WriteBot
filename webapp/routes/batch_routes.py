"""Batch processing endpoints for handwriting synthesis."""

import os
import sys
import shutil
import tempfile
import time
import zipfile
import json
import uuid
from typing import List, Tuple, Dict, Any
from flask import Blueprint, jsonify, request, send_file, Response, stream_with_context
from flask_login import login_required

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from handwriting_synthesis.hand.Hand import Hand
from webapp.utils.generation_utils import parse_generation_params, generate_handwriting_to_file


# Create blueprint
batch_bp = Blueprint('batch', __name__)

# Initialize Hand model (shared across requests)
hand = Hand()

# Jobs directory for streaming batch processing
JOBS_ROOT = os.path.join(tempfile.gettempdir(), "writebot_jobs")
os.makedirs(JOBS_ROOT, exist_ok=True)


def _get_row_value(row: Dict[str, Any], key: str, default=None):
    """Get value from row, handling NaN values."""
    v = row.get(key)
    return default if (v is None or (isinstance(v, float) and str(v) == "nan")) else v


@batch_bp.route("/api/batch", methods=["POST"])
@login_required
def batch_generate():
    """Process batch CSV upload and generate multiple handwriting samples."""
    from webapp.utils.auth_utils import log_activity, track_generation
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
            # Merge row data with defaults
            merged_params = {**defaults, **{k: v for k, v in row_dict.items() if v not in (None, "", "nan")}}

            # Ensure we have text
            if not merged_params.get("text"):
                raise ValueError("Empty text")

            # Get filename
            filename = _get_row_value(row_dict, "filename", f"sample_{idx}.svg")
            out_path = os.path.join(out_dir, os.path.basename(filename))

            # Parse all generation parameters using shared utility
            params = parse_generation_params(merged_params, defaults)

            # Generate using shared utility
            generate_handwriting_to_file(hand, out_path, params)

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

    # Log the batch generation
    log_activity('batch', f'Generated batch with {len(generated_files)} files ({len(errors)} errors)')
    track_generation(lines_count=len(generated_files), chars_count=0,
                     processing_time=0, is_batch=True)

    return send_file(zip_path, mimetype="application/zip", as_attachment=True, download_name=os.path.basename(zip_path))


@batch_bp.route("/api/template-csv", methods=["GET"])
@login_required
def template_csv():
    """Download a template CSV file for batch processing."""
    # Comprehensive CSV template with all available parameters
    header = (
        "filename,text,"
        "page_size,units,page_width,page_height,margins,line_height,align,background,global_scale,orientation,"
        "biases,styles,stroke_colors,stroke_widths,"
        "legibility,x_stretch,denoise,empty_line_spacing,auto_size,manual_size_scale,character_override_collection_id,"
        "wrap_char_px,wrap_ratio,wrap_utilization,"
        "use_chunked,max_line_width,words_per_chunk,chunk_spacing,rotate_chunks,min_words_per_chunk,max_words_per_chunk,target_chars_per_chunk,adaptive_chunking,adaptive_strategy\n"
    )
    # Add example row to show users the format
    example = (
        "example.svg,The quick brown fox jumps over the lazy dog.,"
        "A4,mm,,,20,,,white,1.0,portrait,"
        ",,,,normal,1.0,true,,,1.0,"
        ",,,,true,800.0,3,8.0,true,2,8,25,true,balanced\n"
    )
    return Response(header + example, mimetype="text/csv", headers={
        'Content-Disposition': 'attachment; filename=writebot_template.csv'
    })


def _sse(obj: Dict[str, Any]) -> str:
    """Format Server-Sent Event message."""
    return f"data: {json.dumps(obj)}\n\n"


@batch_bp.route("/api/batch/stream", methods=["POST"])
@login_required
def batch_stream():
    """Process batch CSV with streaming progress updates."""
    # Debug: Print what we received
    print(f"DEBUG: request.files keys: {list(request.files.keys())}")
    print(f"DEBUG: request.form keys: {list(request.form.keys())}")

    if "file" not in request.files:
        error_msg = f"CSV file is required under 'file' field. Received files: {list(request.files.keys())}"
        print(f"ERROR: {error_msg}")
        return jsonify({"error": error_msg}), 400

    csv_file = request.files["file"]
    print(f"DEBUG: CSV file received: {csv_file.filename}")

    try:
        import pandas as pd
        # Important: Don't use first column as index
        df = pd.read_csv(csv_file, index_col=False)
        print(f"DEBUG: CSV parsed successfully. Rows: {len(df)}, Columns: {list(df.columns)}")
    except Exception as e:
        error_msg = f"Failed to read CSV: {e}"
        print(f"ERROR: {error_msg}")
        return jsonify({"error": error_msg}), 400

    # Get defaults from form, but filter out None/empty values
    defaults = {k: v for k, v in request.form.to_dict(flat=True).items() if v}
    print(f"DEBUG: Form defaults: {defaults}")

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

        for row_num, row in df.fillna("").iterrows():
            row_dict = row.to_dict()
            try:
                # CSV row values should override defaults, not the other way around
                # Filter out empty/nan values from CSV
                csv_values = {k: v for k, v in row_dict.items() if v not in (None, "", "nan", "NaN") and pd.notna(v)}

                # Merge: defaults first, then CSV overrides
                merged_params = {**defaults, **csv_values}

                # Ensure we have text
                if not merged_params.get("text"):
                    raise ValueError("Empty text")

                # Get filename
                filename = _get_row_value(row_dict, "filename", f"sample_{row_num}.svg")
                out_path = os.path.join(out_dir, os.path.basename(filename))

                print(f"DEBUG: Processing row {row_num}: filename={filename}")
                print(f"DEBUG: Merged params: {merged_params}")

                # Parse all generation parameters using shared utility
                params = parse_generation_params(merged_params, defaults)

                # Generate using shared utility
                generate_handwriting_to_file(hand, out_path, params)

                generated_files.append(out_path)
                yield _sse({
                    "type": "row",
                    "status": "ok",
                    "row": int(row_num),
                    "file": filename,
                    "job_id": job_id,
                })
            except Exception as e:
                print(f"ERROR: Row {row_num} failed: {e}")
                errors.append((int(row_num), str(e)))
                yield _sse({
                    "type": "row",
                    "status": "error",
                    "row": int(row_num),
                    "error": str(e),
                    "job_id": job_id,
                })

            yield _sse({"type": "progress", "completed": int(row_num) + 1, "total": int(len(df))})

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


@batch_bp.route("/api/batch/result/<job_id>", methods=["GET"])
@login_required
def batch_result(job_id: str):
    """Download batch processing results."""
    job_dir = os.path.join(JOBS_ROOT, job_id)
    zip_path = os.path.join(job_dir, "results.zip")
    if not os.path.isfile(zip_path):
        return jsonify({"error": "Result not found or expired"}), 404
    return send_file(zip_path, mimetype="application/zip", as_attachment=True, download_name=f"writebot_batch_{job_id}.zip")


@batch_bp.route("/api/batch/result/<job_id>/file/<path:filename>", methods=["GET"])
@login_required
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
