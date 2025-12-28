"""
Celery tasks for WriteBot handwriting generation.

These tasks handle handwriting generation asynchronously, allowing
multiple users to queue requests without crashing the server.
"""

import os
import sys
import shutil
import tempfile
import time
import uuid
import zipfile
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from webapp.celery_app import celery_app

# Lazy-load Hand to avoid loading TensorFlow at import time
_hand_instance = None


def get_hand():
    """
    Get or create the Hand instance.

    Uses lazy loading to avoid TensorFlow initialization until needed.
    The Hand instance is cached per worker process.
    """
    global _hand_instance
    if _hand_instance is None:
        from handwriting_synthesis.hand.Hand import Hand
        _hand_instance = Hand()
    return _hand_instance


# Task result storage directory
TASK_RESULTS_DIR = os.path.join(tempfile.gettempdir(), "writebot_task_results")
os.makedirs(TASK_RESULTS_DIR, exist_ok=True)


def get_task_result_path(task_id: str, filename: str = "output.svg") -> str:
    """Get the path for a task result file."""
    task_dir = os.path.join(TASK_RESULTS_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    return os.path.join(task_dir, filename)


def cleanup_task_result(task_id: str) -> None:
    """Clean up task result files."""
    task_dir = os.path.join(TASK_RESULTS_DIR, task_id)
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)


@celery_app.task(bind=True, name='webapp.tasks.generate_handwriting_task')
def generate_handwriting_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery task for generating handwriting asynchronously.

    Args:
        params: Generation parameters (from parse_generation_params).

    Returns:
        Dict containing task_id, status, and result path or error.
    """
    task_id = self.request.id
    start_time = time.time()

    try:
        # Update task state to STARTED
        self.update_state(state='STARTED', meta={
            'status': 'Initializing model...',
            'progress': 10,
        })

        # Get Hand instance (lazy loaded)
        hand = get_hand()

        self.update_state(state='STARTED', meta={
            'status': 'Generating handwriting...',
            'progress': 30,
        })

        # Import generation utilities
        from webapp.utils.generation_utils import generate_handwriting_to_file, parse_generation_params

        # Generate to task result directory
        output_path = get_task_result_path(task_id, "output.svg")

        # Generate the handwriting
        generate_handwriting_to_file(hand, output_path, params)

        self.update_state(state='STARTED', meta={
            'status': 'Reading result...',
            'progress': 90,
        })

        # Read the generated SVG
        with open(output_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        processing_time = time.time() - start_time

        return {
            'status': 'SUCCESS',
            'task_id': task_id,
            'svg': svg_content,
            'result_path': output_path,
            'processing_time': round(processing_time, 2),
        }

    except Exception as e:
        processing_time = time.time() - start_time
        return {
            'status': 'FAILURE',
            'task_id': task_id,
            'error': str(e),
            'processing_time': round(processing_time, 2),
        }


@celery_app.task(bind=True, name='webapp.tasks.generate_batch_task')
def generate_batch_task(
    self,
    rows: List[Dict[str, Any]],
    defaults: Dict[str, Any],
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Celery task for batch handwriting generation.

    Args:
        rows: List of row dictionaries from CSV/XLSX.
        defaults: Default parameters.
        job_id: Optional job ID for result storage.

    Returns:
        Dict containing job_id, status, and results.
    """
    task_id = self.request.id
    job_id = job_id or task_id
    start_time = time.time()

    try:
        from webapp.utils.generation_utils import generate_handwriting_to_file, parse_generation_params

        # Create job directory
        job_dir = os.path.join(TASK_RESULTS_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        out_dir = os.path.join(job_dir, "out")
        os.makedirs(out_dir, exist_ok=True)

        # Update initial state
        total_rows = len(rows)
        self.update_state(state='STARTED', meta={
            'status': 'Initializing...',
            'progress': 0,
            'total': total_rows,
            'completed': 0,
            'job_id': job_id,
        })

        # Get Hand instance
        hand = get_hand()

        generated_files = []
        errors = []
        log_lines = [
            '=' * 70,
            'WriteBot Batch Processing Log',
            '=' * 70,
            f'Job ID: {job_id}',
            f'Started at: {time.strftime("%Y-%m-%d %H:%M:%S")}',
            f'Total rows to process: {total_rows}',
            '=' * 70,
            '',
        ]

        for idx, row in enumerate(rows):
            try:
                # Merge row with defaults
                merged = {**defaults, **{k: v for k, v in row.items() if v not in (None, "", "nan")}}

                if not merged.get("text"):
                    raise ValueError("Empty text")

                # Handle line breaks
                if "text" in merged:
                    merged["text"] = merged["text"].replace("\\n", "\n")

                # Get filename
                filename = row.get("filename", f"sample_{idx}.svg")
                if not filename.lower().endswith('.svg'):
                    filename = filename + '.svg'
                out_path = os.path.join(out_dir, os.path.basename(filename))

                # Parse and generate
                params = parse_generation_params(merged, defaults)
                row_start = time.time()
                generate_handwriting_to_file(hand, out_path, params)
                row_time = time.time() - row_start

                generated_files.append(out_path)
                log_lines.append(f'[OK] Row {idx}: {filename} - SUCCESS (took {row_time:.2f}s)')

            except Exception as e:
                errors.append({'row': idx, 'error': str(e)})
                log_lines.append(f'[ERR] Row {idx}: ERROR - {str(e)}')

            # Update progress
            progress = int(((idx + 1) / total_rows) * 100)
            self.update_state(state='STARTED', meta={
                'status': f'Processing row {idx + 1}/{total_rows}...',
                'progress': progress,
                'total': total_rows,
                'completed': idx + 1,
                'success_count': len(generated_files),
                'error_count': len(errors),
                'job_id': job_id,
            })

        # Add completion summary
        total_time = time.time() - start_time
        log_lines.extend([
            '',
            '=' * 70,
            'Processing Complete',
            '=' * 70,
            f'Completed at: {time.strftime("%Y-%m-%d %H:%M:%S")}',
            f'Total time: {total_time:.2f}s',
            f'Successful: {len(generated_files)}',
            f'Errors: {len(errors)}',
            '=' * 70,
        ])

        # Write log
        log_path = os.path.join(job_dir, "processing_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(log_lines))

        # Create ZIP
        zip_path = os.path.join(job_dir, "results.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in generated_files:
                zf.write(path, arcname=os.path.basename(path))
            zf.write(log_path, arcname="processing_log.txt")

        return {
            'status': 'SUCCESS',
            'task_id': task_id,
            'job_id': job_id,
            'zip_path': zip_path,
            'total': total_rows,
            'success_count': len(generated_files),
            'error_count': len(errors),
            'errors': errors,
            'processing_time': round(total_time, 2),
        }

    except Exception as e:
        return {
            'status': 'FAILURE',
            'task_id': task_id,
            'job_id': job_id,
            'error': str(e),
            'processing_time': round(time.time() - start_time, 2),
        }


@celery_app.task(name='webapp.tasks.cleanup_old_results')
def cleanup_old_results(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Periodic task to clean up old task results.

    Args:
        max_age_hours: Maximum age in hours before cleanup.

    Returns:
        Dict with cleanup statistics.
    """
    import time

    cleaned = 0
    errors = 0
    cutoff = time.time() - (max_age_hours * 3600)

    if os.path.exists(TASK_RESULTS_DIR):
        for task_dir in os.listdir(TASK_RESULTS_DIR):
            task_path = os.path.join(TASK_RESULTS_DIR, task_dir)
            try:
                if os.path.isdir(task_path):
                    mtime = os.path.getmtime(task_path)
                    if mtime < cutoff:
                        shutil.rmtree(task_path, ignore_errors=True)
                        cleaned += 1
            except Exception:
                errors += 1

    return {
        'cleaned': cleaned,
        'errors': errors,
    }
