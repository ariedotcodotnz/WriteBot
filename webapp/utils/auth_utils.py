"""
Authentication utilities including decorators and activity logging.
"""
from functools import wraps
from datetime import datetime, date
from flask import request, jsonify, abort
from flask_login import current_user
from webapp.models import db, UserActivity, UsageStatistics
import json


def admin_required(f):
    """
    Decorator to require admin role for a route.

    Checks if the current user is authenticated and has the 'admin' role.
    Returns 401 Unauthorized if not logged in, 403 Forbidden if not an admin.

    Args:
        f: The view function to decorate.

    Returns:
        The decorated function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized
        if not current_user.is_admin():
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function


def log_activity(activity_type, description=None, metadata=None):
    """
    Log user activity to the database.

    Records actions performed by authenticated users for auditing purposes.

    Args:
        activity_type: Type of activity (e.g., 'login', 'generate', 'admin_action').
        description: Optional text description of the activity.
        metadata: Optional dictionary of additional data to store as JSON.
    """
    if not current_user.is_authenticated:
        return

    try:
        activity = UserActivity(
            user_id=current_user.id,
            activity_type=activity_type,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:255],
            extra_data=json.dumps(metadata) if metadata else None,
            timestamp=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        # Log the error but don't break the application
        print(f"Error logging activity: {e}")
        db.session.rollback()


def track_generation(lines_count=0, chars_count=0, processing_time=0.0, is_batch=False):
    """
    Track generation statistics for the current user.

    Updates the daily usage statistics for the user, incrementing counters
    and cumulative metrics. Creates a new record for the day if one doesn't exist.

    Args:
        lines_count: Number of lines generated.
        chars_count: Number of characters generated.
        processing_time: Processing time in seconds.
        is_batch: Boolean indicating if this was a batch generation job.
    """
    if not current_user.is_authenticated:
        return

    try:
        today = date.today()

        # Get or create today's statistics record
        stats = UsageStatistics.query.filter_by(
            user_id=current_user.id,
            date=today
        ).first()

        if not stats:
            stats = UsageStatistics(
                user_id=current_user.id,
                date=today,
                svg_generations=0,
                batch_generations=0,
                total_lines_generated=0,
                total_characters_generated=0,
                total_processing_time=0.0
            )
            db.session.add(stats)

        # Ensure all numeric fields are initialized (handle potential NULL values in existing records)
        if stats.batch_generations is None:
            stats.batch_generations = 0
        if stats.svg_generations is None:
            stats.svg_generations = 0
        if stats.total_lines_generated is None:
            stats.total_lines_generated = 0
        if stats.total_characters_generated is None:
            stats.total_characters_generated = 0
        if stats.total_processing_time is None:
            stats.total_processing_time = 0.0

        # Update statistics
        if is_batch:
            stats.batch_generations += 1
        else:
            stats.svg_generations += 1

        stats.total_lines_generated += lines_count
        stats.total_characters_generated += chars_count
        stats.total_processing_time += processing_time
        stats.updated_at = datetime.utcnow()

        db.session.commit()
    except Exception as e:
        # Log the error but don't break the application
        print(f"Error tracking generation: {e}")
        db.session.rollback()


def get_user_statistics(user_id, days=30):
    """
    Get user statistics for the last N days.

    Args:
        user_id: User ID to get statistics for.
        days: Number of days to retrieve (default 30).

    Returns:
        List of UsageStatistics objects ordered by date (descending).
    """
    from datetime import timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    stats = UsageStatistics.query.filter(
        UsageStatistics.user_id == user_id,
        UsageStatistics.date >= start_date,
        UsageStatistics.date <= end_date
    ).order_by(UsageStatistics.date.desc()).all()

    return stats


def get_user_activities(user_id, limit=100):
    """
    Get recent activities for a user.

    Args:
        user_id: User ID to get activities for.
        limit: Maximum number of activities to retrieve (default 100).

    Returns:
        List of UserActivity objects ordered by timestamp (descending).
    """
    activities = UserActivity.query.filter_by(
        user_id=user_id
    ).order_by(UserActivity.timestamp.desc()).limit(limit).all()

    return activities


def get_all_user_statistics(days=7):
    """
    Get aggregated statistics for all users over the last N days.

    Calculates totals for generations, lines, characters, and processing time.

    Args:
        days: Number of days to aggregate (default 7).

    Returns:
        Dictionary with aggregated statistics keys:
        - svg_generations
        - batch_generations
        - total_lines
        - total_characters
        - total_processing_time
        - period_days
    """
    from datetime import timedelta
    from sqlalchemy import func

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    stats = db.session.query(
        func.sum(UsageStatistics.svg_generations).label('total_svg'),
        func.sum(UsageStatistics.batch_generations).label('total_batch'),
        func.sum(UsageStatistics.total_lines_generated).label('total_lines'),
        func.sum(UsageStatistics.total_characters_generated).label('total_chars'),
        func.sum(UsageStatistics.total_processing_time).label('total_time')
    ).filter(
        UsageStatistics.date >= start_date,
        UsageStatistics.date <= end_date
    ).first()

    return {
        'svg_generations': stats.total_svg or 0,
        'batch_generations': stats.total_batch or 0,
        'total_lines': stats.total_lines or 0,
        'total_characters': stats.total_chars or 0,
        'total_processing_time': stats.total_time or 0.0,
        'period_days': days
    }
