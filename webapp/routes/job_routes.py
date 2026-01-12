"""
Job queue management routes for batch processing.

This module provides API endpoints and page views for managing batch jobs,
including creating, listing, cancelling, and downloading job results.
"""

import os
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, send_file, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from webapp.models import db, BatchJob
from webapp.utils.auth_utils import log_activity

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')


# ============================================================================
# Page Routes
# ============================================================================

@jobs_bp.route('/')
@login_required
def jobs_page():
    """
    Render the jobs management page.

    Returns:
        Rendered jobs list template.
    """
    log_activity('page_view', 'Accessed jobs management page')
    return render_template('jobs/list.html')


# ============================================================================
# API Routes
# ============================================================================

@jobs_bp.route('/api/jobs', methods=['GET'])
@login_required
def list_jobs():
    """
    List batch jobs with filtering and pagination.

    Query params:
        status: Filter by job status (pending, queued, processing, completed, failed, cancelled)
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)

    Returns:
        JSON response with jobs list and pagination info.
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status', '').strip()

    query = BatchJob.query

    # Access control: non-admin users see only their own jobs + public jobs
    if not current_user.is_admin():
        query = query.filter(
            db.or_(
                BatchJob.user_id == current_user.id,
                BatchJob.is_private == False
            )
        )

    # Status filter
    if status:
        query = query.filter(BatchJob.status == status)

    # Order by priority (desc) then created_at (desc)
    query = query.order_by(BatchJob.priority.desc(), BatchJob.created_at.desc())

    # Paginate
    jobs_page = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'jobs': [job.to_dict(current_user_id=current_user.id) for job in jobs_page.items],
        'pagination': {
            'page': jobs_page.page,
            'per_page': jobs_page.per_page,
            'total': jobs_page.total,
            'pages': jobs_page.pages
        }
    })


@jobs_bp.route('/api/jobs', methods=['POST'])
@login_required
def create_job():
    """
    Add a new job to the queue.

    Expects multipart form with:
        file: CSV/XLSX file (required)
        title: Job title (optional, defaults to filename)
        priority: 1-5 (default 3)
        is_private: boolean (default false)
        scheduled_at: ISO datetime (optional, for delayed execution)
        parameters: JSON string of generation params (optional)

    Returns:
        JSON response with created job details.
    """
    from webapp.tasks import process_batch_job

    # Validate file upload
    if 'file' not in request.files:
        return jsonify({'error': 'File is required'}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    filename = uploaded_file.filename.lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx')):
        return jsonify({'error': 'Only CSV and XLSX files are supported'}), 400

    # Get form parameters
    title = request.form.get('title', uploaded_file.filename or 'Untitled Job').strip()
    priority = request.form.get('priority', 3, type=int)
    is_private = request.form.get('is_private', 'false').lower() == 'true'
    scheduled_at_str = request.form.get('scheduled_at', '').strip()
    parameters = request.form.get('parameters', '{}')

    # Validate priority (1-5)
    priority = max(1, min(5, priority))

    # Validate parameters JSON
    try:
        json.loads(parameters)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid parameters JSON'}), 400

    # Parse scheduled time
    scheduled_at = None
    if scheduled_at_str:
        try:
            # Handle ISO format with optional timezone
            scheduled_at_str = scheduled_at_str.replace('Z', '+00:00')
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except ValueError:
            return jsonify({'error': 'Invalid scheduled_at format. Use ISO 8601.'}), 400

    # Create job record
    job = BatchJob(
        user_id=current_user.id,
        title=title[:255],  # Limit title length
        status='pending' if scheduled_at else 'queued',
        priority=priority,
        is_private=is_private,
        scheduled_at=scheduled_at,
        parameters=parameters
    )
    db.session.add(job)
    db.session.commit()

    # Create job directory in secure storage
    job_dir = os.path.join(current_app.config['JOB_FILES_DIR'], str(job.id))
    os.makedirs(job_dir, exist_ok=True)

    # Save uploaded file
    safe_filename = secure_filename(uploaded_file.filename)
    input_path = os.path.join(job_dir, f'input_{safe_filename}')
    uploaded_file.save(input_path)

    job.input_file_path = input_path
    db.session.commit()

    # Queue immediately if not scheduled
    if not scheduled_at:
        try:
            task = process_batch_job.apply_async(
                args=[job.id],
                priority=priority
            )
            job.celery_task_id = task.id
            db.session.commit()
        except Exception as e:
            job.status = 'failed'
            job.error_message = f'Failed to queue job: {str(e)}'
            db.session.commit()
            return jsonify({'error': 'Failed to queue job', 'details': str(e)}), 500

    log_activity('job_created', f'Created batch job: {title} (ID: {job.id})', {
        'job_id': job.id,
        'priority': priority,
        'scheduled': bool(scheduled_at),
        'is_private': is_private
    })

    return jsonify({
        'message': 'Job created successfully',
        'job': job.to_dict(current_user_id=current_user.id)
    }), 201


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """
    Get job details.

    Args:
        job_id: The job ID.

    Returns:
        JSON response with job details.
    """
    job = BatchJob.query.get_or_404(job_id)

    # Access control
    if not current_user.is_admin():
        if job.is_private and job.user_id != current_user.id:
            abort(403)

    return jsonify({'job': job.to_dict(current_user_id=current_user.id)})


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@login_required
def delete_job(job_id):
    """
    Cancel or delete a job.

    If job is queued/processing, it will be cancelled.
    If job is completed/failed/cancelled, it will be deleted.

    Args:
        job_id: The job ID.

    Returns:
        JSON response confirming action.
    """
    job = BatchJob.query.get_or_404(job_id)

    # Access control: only owner or admin can delete
    if not current_user.is_admin() and job.user_id != current_user.id:
        abort(403)

    # If processing or queued, try to revoke Celery task
    if job.status in ('queued', 'processing') and job.celery_task_id:
        try:
            from webapp.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass

        job.status = 'cancelled'
        job.completed_at = datetime.utcnow()
        db.session.commit()

        log_activity('job_cancelled', f'Cancelled job: {job.title} (ID: {job.id})')
        return jsonify({'message': 'Job cancelled', 'status': 'cancelled'})

    # Clean up files
    if job.input_file_path:
        job_dir = os.path.dirname(job.input_file_path)
        if os.path.exists(job_dir):
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)

    db.session.delete(job)
    db.session.commit()

    log_activity('job_deleted', f'Deleted job: {job.title} (ID: {job_id})')

    return jsonify({'message': 'Job deleted', 'status': 'deleted'})


@jobs_bp.route('/api/jobs/<int:job_id>/download', methods=['GET'])
@login_required
def download_job(job_id):
    """
    Download completed job results.

    Args:
        job_id: The job ID.

    Returns:
        ZIP file download or error response.
    """
    job = BatchJob.query.get_or_404(job_id)

    # Access control
    if not current_user.is_admin():
        if job.is_private and job.user_id != current_user.id:
            abort(403)

    if job.status != 'completed':
        return jsonify({'error': 'Job is not completed'}), 400

    if not job.output_file_path:
        return jsonify({'error': 'No output file available'}), 404

    if not os.path.exists(job.output_file_path):
        return jsonify({'error': 'Output file not found'}), 404

    log_activity('job_download', f'Downloaded job results: {job.title} (ID: {job.id})')

    # Generate safe download filename
    safe_title = "".join(c for c in job.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title[:50] if safe_title else 'results'
    download_name = f'writebot_job_{job.id}_{safe_title}.zip'

    return send_file(
        job.output_file_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name
    )


@jobs_bp.route('/api/jobs/stats', methods=['GET'])
@login_required
def job_stats():
    """
    Get job statistics for the current user.

    Returns:
        JSON response with job counts by status.
    """
    if current_user.is_admin():
        base_query = BatchJob.query
    else:
        base_query = BatchJob.query.filter(
            db.or_(
                BatchJob.user_id == current_user.id,
                BatchJob.is_private == False
            )
        )

    stats = {
        'pending': base_query.filter(BatchJob.status == 'pending').count(),
        'queued': base_query.filter(BatchJob.status == 'queued').count(),
        'processing': base_query.filter(BatchJob.status == 'processing').count(),
        'completed': base_query.filter(BatchJob.status == 'completed').count(),
        'failed': base_query.filter(BatchJob.status == 'failed').count(),
        'cancelled': base_query.filter(BatchJob.status == 'cancelled').count(),
    }
    stats['total'] = sum(stats.values())

    return jsonify(stats)
