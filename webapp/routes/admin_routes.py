"""
Admin routes for user management and statistics.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from webapp.models import db, User, UserActivity, UsageStatistics
from webapp.utils.auth_utils import admin_required, log_activity, get_user_statistics, get_user_activities, get_all_user_statistics
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with overview statistics."""
    # Get overall statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role='admin').count()

    # Get statistics for last 7 days
    stats_7d = get_all_user_statistics(days=7)

    # Get recent activities (last 50)
    recent_activities = UserActivity.query.order_by(desc(UserActivity.timestamp)).limit(50).all()

    # Get top users by generation count (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    top_users = db.session.query(
        User.username,
        User.full_name,
        func.sum(UsageStatistics.svg_generations + UsageStatistics.batch_generations).label('total_generations')
    ).join(UsageStatistics).filter(
        UsageStatistics.date >= thirty_days_ago
    ).group_by(User.id).order_by(desc('total_generations')).limit(10).all()

    log_activity('admin_action', 'Viewed admin dashboard')

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           admin_users=admin_users,
                           stats_7d=stats_7d,
                           recent_activities=recent_activities,
                           top_users=top_users)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    log_activity('admin_action', 'Viewed users list')
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'user')
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not username:
            flash('Username is required.', 'error')
            return render_template('admin/user_form.html', user=None, action='create')

        if not password:
            flash('Password is required.', 'error')
            return render_template('admin/user_form.html', user=None, action='create')

        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" already exists.', 'error')
            return render_template('admin/user_form.html', user=None, action='create')

        if role not in ['user', 'admin']:
            flash('Invalid role selected.', 'error')
            return render_template('admin/user_form.html', user=None, action='create')

        # Create user
        new_user = User(
            username=username,
            full_name=full_name,
            role=role,
            is_active=is_active
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        log_activity('admin_action', f'Created user: {username}')
        flash(f'User "{username}" created successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', user=None, action='create')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user."""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'user')
        is_active = request.form.get('is_active') == 'on'
        password = request.form.get('password', '')

        # Validation
        if not username:
            flash('Username is required.', 'error')
            return render_template('admin/user_form.html', user=user, action='edit')

        # Check if username is taken by another user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            flash(f'Username "{username}" already exists.', 'error')
            return render_template('admin/user_form.html', user=user, action='edit')

        if role not in ['user', 'admin']:
            flash('Invalid role selected.', 'error')
            return render_template('admin/user_form.html', user=user, action='edit')

        # Update user
        user.username = username
        user.full_name = full_name
        user.role = role
        user.is_active = is_active

        # Update password if provided
        if password:
            user.set_password(password)

        db.session.commit()

        log_activity('admin_action', f'Updated user: {username} (ID: {user_id})')
        flash(f'User "{username}" updated successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', user=user, action='edit')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    log_activity('admin_action', f'Deleted user: {username} (ID: {user_id})')
    flash(f'User "{username}" deleted successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View user details, activities, and statistics."""
    user = User.query.get_or_404(user_id)

    # Get user activities (last 100)
    activities = get_user_activities(user_id, limit=100)

    # Get user statistics (last 30 days)
    statistics = get_user_statistics(user_id, days=30)

    # Calculate totals
    total_svg = sum(s.svg_generations for s in statistics)
    total_batch = sum(s.batch_generations for s in statistics)
    total_lines = sum(s.total_lines_generated for s in statistics)
    total_chars = sum(s.total_characters_generated for s in statistics)
    total_time = sum(s.total_processing_time for s in statistics)

    log_activity('admin_action', f'Viewed user details: {user.username} (ID: {user_id})')

    return render_template('admin/user_details.html',
                           user=user,
                           activities=activities,
                           statistics=statistics,
                           total_svg=total_svg,
                           total_batch=total_batch,
                           total_lines=total_lines,
                           total_chars=total_chars,
                           total_time=total_time)


@admin_bp.route('/activities')
@login_required
@admin_required
def activities():
    """View all user activities."""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Filter by user if specified
    user_id = request.args.get('user_id', type=int)
    activity_type = request.args.get('type', '').strip()

    query = UserActivity.query

    if user_id:
        query = query.filter_by(user_id=user_id)

    if activity_type:
        query = query.filter_by(activity_type=activity_type)

    activities_page = query.order_by(desc(UserActivity.timestamp)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    log_activity('admin_action', 'Viewed activities log')

    return render_template('admin/activities.html',
                           activities=activities_page.items,
                           pagination=activities_page,
                           current_user_id=user_id,
                           current_type=activity_type)


@admin_bp.route('/statistics')
@login_required
@admin_required
def statistics():
    """View overall statistics and charts."""
    # Get stats for different periods
    stats_7d = get_all_user_statistics(days=7)
    stats_30d = get_all_user_statistics(days=30)
    stats_90d = get_all_user_statistics(days=90)

    # Get daily statistics for charts (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    daily_stats = db.session.query(
        UsageStatistics.date,
        func.sum(UsageStatistics.svg_generations).label('svg'),
        func.sum(UsageStatistics.batch_generations).label('batch'),
        func.sum(UsageStatistics.total_lines_generated).label('lines')
    ).filter(
        UsageStatistics.date >= thirty_days_ago
    ).group_by(UsageStatistics.date).order_by(UsageStatistics.date).all()

    log_activity('admin_action', 'Viewed statistics dashboard')

    return render_template('admin/statistics.html',
                           stats_7d=stats_7d,
                           stats_30d=stats_30d,
                           stats_90d=stats_90d,
                           daily_stats=daily_stats)
