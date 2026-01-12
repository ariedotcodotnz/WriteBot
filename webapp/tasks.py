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


@celery_app.task(bind=True, name='webapp.tasks.process_batch_job')
def process_batch_job(self, job_id: int) -> Dict[str, Any]:
    """
    Process a queued batch job from the database.

    This task is the main entry point for processing jobs added via the queue.

    Args:
        job_id: The database ID of the BatchJob to process.

    Returns:
        Dict containing job_id, status, and processing results.
    """
    import json
    import pandas as pd
    from datetime import datetime

    # Import Flask app for application context
    from webapp.app import app
    from webapp.models import db, BatchJob

    with app.app_context():
        job = BatchJob.query.get(job_id)
        if not job:
            return {'status': 'ERROR', 'error': 'Job not found', 'job_id': job_id}

        # Update job status to processing
        job.status = 'processing'
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        db.session.commit()

        start_time = time.time()

        try:
            from webapp.utils.generation_utils import generate_handwriting_to_file, parse_generation_params

            # Read input file
            input_path = job.input_file_path
            if input_path.lower().endswith('.xlsx'):
                df = pd.read_excel(input_path, sheet_name=0, engine='openpyxl')
            else:
                df = pd.read_csv(input_path)

            job.row_count = len(df)
            db.session.commit()

            # Parse default parameters
            defaults = json.loads(job.parameters or '{}')

            # Create output directory
            job_dir = os.path.dirname(input_path)
            out_dir = os.path.join(job_dir, 'out')
            os.makedirs(out_dir, exist_ok=True)

            # Get Hand instance
            hand = get_hand()

            generated_files = []
            errors = []
            log_lines = [
                '=' * 70,
                'WriteBot Batch Job Processing Log',
                '=' * 70,
                f'Job ID: {job_id}',
                f'Job Title: {job.title}',
                f'Started at: {time.strftime("%Y-%m-%d %H:%M:%S")}',
                f'Total rows to process: {job.row_count}',
                '=' * 70,
                '',
            ]

            for idx, row in df.fillna("").iterrows():
                try:
                    row_dict = row.to_dict()
                    merged = {**defaults, **{k: v for k, v in row_dict.items() if v not in (None, "", "nan")}}

                    if not merged.get("text"):
                        raise ValueError("Empty text")

                    # Handle line breaks
                    if "text" in merged:
                        merged["text"] = str(merged["text"]).replace("\\n", "\n")

                    # Get filename
                    filename = row_dict.get("filename", f"sample_{idx}.svg")
                    if not str(filename).lower().endswith('.svg'):
                        filename = str(filename) + '.svg'
                    out_path = os.path.join(out_dir, os.path.basename(str(filename)))

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

                # Update job progress in database
                job.success_count = len(generated_files)
                job.error_count = len(errors)
                db.session.commit()

                # Update Celery task state
                progress = int(((idx + 1) / job.row_count) * 100)
                self.update_state(state='PROGRESS', meta={
                    'status': f'Processing row {idx + 1}/{job.row_count}...',
                    'progress': progress,
                    'total': job.row_count,
                    'completed': idx + 1,
                    'success_count': len(generated_files),
                    'error_count': len(errors),
                    'job_id': job_id,
                })

            # Completion summary
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

            # Write processing log
            log_path = os.path.join(job_dir, "processing_log.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write('\n'.join(log_lines))

            # Create ZIP
            zip_path = os.path.join(job_dir, "results.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in generated_files:
                    zf.write(path, arcname=os.path.basename(path))
                zf.write(log_path, arcname="processing_log.txt")

            # Update job record
            job.output_file_path = zip_path
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.processing_log = '\n'.join(log_lines[-20:])  # Store last 20 lines
            db.session.commit()

            # Send email notification
            send_job_notification.delay(job_id, 'completed')

            return {
                'status': 'SUCCESS',
                'job_id': job_id,
                'total': job.row_count,
                'success_count': len(generated_files),
                'error_count': len(errors),
                'processing_time': round(total_time, 2),
            }

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.session.commit()

            # Send failure notification
            send_job_notification.delay(job_id, 'failed')

            return {
                'status': 'FAILURE',
                'job_id': job_id,
                'error': str(e),
                'processing_time': round(time.time() - start_time, 2),
            }


@celery_app.task(name='webapp.tasks.send_job_notification')
def send_job_notification(job_id: int, status: str) -> Dict[str, Any]:
    """
    Send email notification for job completion or failure.

    Args:
        job_id: The database ID of the BatchJob.
        status: Either 'completed' or 'failed'.

    Returns:
        Dict with notification status.
    """
    from webapp.app import app, mail
    from webapp.models import db, BatchJob

    with app.app_context():
        if not mail:
            return {'status': 'SKIPPED', 'reason': 'Mail not configured'}

        job = BatchJob.query.get(job_id)
        if not job:
            return {'status': 'SKIPPED', 'reason': 'Job not found'}

        if job.email_notification_sent:
            return {'status': 'SKIPPED', 'reason': 'Already sent'}

        user = job.user
        if not user or not getattr(user, 'email', None):
            return {'status': 'SKIPPED', 'reason': 'No user email'}

        try:
            from flask_mailman import EmailMessage
            from flask import render_template, url_for

            if status == 'completed':
                subject = f'WriteBot: Job "{job.title}" completed'
                template = 'email/job_completed.html'
            else:
                subject = f'WriteBot: Job "{job.title}" failed'
                template = 'email/job_failed.html'

            # Render email body
            html_body = render_template(template, job=job, user=user)

            msg = EmailMessage(
                subject=subject,
                to=[user.email],
                body=html_body,
            )
            msg.content_subtype = 'html'
            msg.send()

            job.email_notification_sent = True
            db.session.commit()

            return {'status': 'SENT', 'job_id': job_id, 'email': user.email}

        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}


@celery_app.task(name='webapp.tasks.check_scheduled_jobs')
def check_scheduled_jobs() -> Dict[str, Any]:
    """
    Check for scheduled jobs that are due and queue them for processing.

    This task runs periodically to find jobs with scheduled_at <= now
    and status == 'pending', then queues them.

    Returns:
        Dict with count of jobs queued.
    """
    from datetime import datetime
    from webapp.app import app
    from webapp.models import db, BatchJob

    with app.app_context():
        now = datetime.utcnow()
        due_jobs = BatchJob.query.filter(
            BatchJob.status == 'pending',
            BatchJob.scheduled_at <= now
        ).all()

        queued_count = 0
        for job in due_jobs:
            try:
                task = process_batch_job.apply_async(
                    args=[job.id],
                    priority=job.priority
                )
                job.celery_task_id = task.id
                job.status = 'queued'
                queued_count += 1
            except Exception:
                pass

        db.session.commit()

        return {'queued': queued_count, 'checked_at': now.isoformat()}


@celery_app.task(name='webapp.tasks.cleanup_old_jobs')
def cleanup_old_jobs() -> Dict[str, Any]:
    """
    Clean up jobs older than the retention period.

    This task runs daily to delete completed/failed/cancelled jobs
    that are older than JOB_RETENTION_DAYS.

    Returns:
        Dict with cleanup statistics.
    """
    from datetime import datetime, timedelta
    from webapp.app import app
    from webapp.models import db, BatchJob

    with app.app_context():
        retention_days = app.config.get('JOB_RETENTION_DAYS', 30)
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        old_jobs = BatchJob.query.filter(
            BatchJob.created_at < cutoff,
            BatchJob.status.in_(['completed', 'failed', 'cancelled'])
        ).all()

        cleaned = 0
        errors = 0

        for job in old_jobs:
            try:
                # Clean up files
                if job.input_file_path:
                    job_dir = os.path.dirname(job.input_file_path)
                    if os.path.exists(job_dir):
                        shutil.rmtree(job_dir, ignore_errors=True)

                db.session.delete(job)
                cleaned += 1
            except Exception:
                errors += 1

        db.session.commit()

        return {
            'cleaned': cleaned,
            'errors': errors,
            'retention_days': retention_days,
            'cutoff': cutoff.isoformat(),
        }
