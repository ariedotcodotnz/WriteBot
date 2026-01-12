"""
Celery application configuration for WriteBot.

This module configures Celery for async task processing, enabling
concurrent handwriting generation without server crashes.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Redis connection URL (defaults to localhost for development)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)

# Create Celery app
celery_app = Celery(
    'writebot',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['webapp.tasks']
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes (prevents loss on crash)
    task_reject_on_worker_lost=True,  # Requeue if worker dies

    # Worker settings - CRITICAL for TensorFlow
    worker_concurrency=1,  # Only 1 concurrent task per worker (TensorFlow is not thread-safe)
    worker_prefetch_multiplier=1,  # Don't prefetch tasks (memory management)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevents memory leaks)

    # Result settings
    result_expires=3600,  # Results expire after 1 hour

    # Task time limits
    task_soft_time_limit=120,  # Soft limit: 2 minutes
    task_time_limit=180,  # Hard limit: 3 minutes

    # Rate limiting (prevents overload)
    task_annotations={
        'webapp.tasks.generate_handwriting_task': {
            'rate_limit': '10/m',  # Max 10 tasks per minute per worker
        },
        'webapp.tasks.generate_batch_task': {
            'rate_limit': '2/m',  # Max 2 batch tasks per minute per worker
        },
    },

    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'generation': {
            'exchange': 'generation',
            'routing_key': 'generation',
        },
        'batch': {
            'exchange': 'batch',
            'routing_key': 'batch',
        },
    },

    # Route tasks to specific queues
    task_routes={
        'webapp.tasks.generate_handwriting_task': {'queue': 'generation'},
        'webapp.tasks.generate_batch_task': {'queue': 'batch'},
        'webapp.tasks.process_batch_job': {'queue': 'batch'},
    },

    # Celery Beat schedule for periodic tasks
    beat_schedule={
        'check-scheduled-jobs': {
            'task': 'webapp.tasks.check_scheduled_jobs',
            'schedule': 60.0,  # Every 60 seconds
        },
        'cleanup-old-jobs': {
            'task': 'webapp.tasks.cleanup_old_jobs',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM UTC
        },
        'cleanup-old-task-results': {
            'task': 'webapp.tasks.cleanup_old_results',
            'schedule': crontab(hour=3, minute=0),  # Daily at 3:00 AM UTC
            'kwargs': {'max_age_hours': 48},
        },
    },
)


def get_celery_app():
    """Get the configured Celery app instance."""
    return celery_app
