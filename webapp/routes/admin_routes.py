"""
Admin routes for user management and statistics.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from webapp.models import db, User, UserActivity, UsageStatistics, PageSizePreset, TemplatePreset
from webapp.utils.auth_utils import admin_required, log_activity, get_user_statistics, get_user_activities, get_all_user_statistics
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """
    Admin dashboard with overview statistics.

    Displays overall user counts, recent activity, and system health metrics.
    """
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
    """
    List all users.

    Returns the user management page populated with a list of all registered users.
    """
    all_users = User.query.order_by(User.created_at.desc()).all()
    log_activity('admin_action', 'Viewed users list')
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """
    Create a new user.

    Handles both the form display (GET) and submission (POST) for creating users.
    """
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
    """
    Edit an existing user.

    Handles updating user details, roles, and status.
    """
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
    """
    Delete a user.

    Permanently removes the user account from the database.
    """
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
    """
    View user details, activities, and statistics.

    Shows comprehensive profile information and usage logs for a specific user.
    """
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
    """
    View all user activities.

    Displays a paginated log of system-wide user actions.
    """
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
    """
    View overall statistics and charts.

    Provides detailed analytics on system usage trends.
    """
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


# Page Size Presets Management
@admin_bp.route('/page-sizes')
@login_required
@admin_required
def page_sizes():
    """
    List all page size presets.

    Displays configured page sizes available for generation.
    """
    all_page_sizes = PageSizePreset.query.order_by(PageSizePreset.is_default.desc(), PageSizePreset.name).all()
    log_activity('admin_action', 'Viewed page size presets')
    return render_template('admin/page_sizes.html', page_sizes=all_page_sizes)


@admin_bp.route('/page-sizes/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_page_size():
    """
    Create a new page size preset.

    Handles form submission for adding new page dimensions.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        width = request.form.get('width', type=float)
        height = request.form.get('height', type=float)
        unit = request.form.get('unit', 'mm').strip()
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Name is required.', 'error')
            return render_template('admin/page_size_form.html', page_size=None, action='create')

        if PageSizePreset.query.filter_by(name=name).first():
            flash(f'Page size preset "{name}" already exists.', 'error')
            return render_template('admin/page_size_form.html', page_size=None, action='create')

        if not width or width <= 0:
            flash('Width must be a positive number.', 'error')
            return render_template('admin/page_size_form.html', page_size=None, action='create')

        if not height or height <= 0:
            flash('Height must be a positive number.', 'error')
            return render_template('admin/page_size_form.html', page_size=None, action='create')

        if unit not in ['mm', 'px']:
            flash('Unit must be either "mm" or "px".', 'error')
            return render_template('admin/page_size_form.html', page_size=None, action='create')

        # Create page size preset
        new_page_size = PageSizePreset(
            name=name,
            width=width,
            height=height,
            unit=unit,
            is_active=is_active,
            created_by=current_user.id
        )

        db.session.add(new_page_size)
        db.session.commit()

        log_activity('admin_action', f'Created page size preset: {name}')
        flash(f'Page size preset "{name}" created successfully.', 'success')
        return redirect(url_for('admin.page_sizes'))

    return render_template('admin/page_size_form.html', page_size=None, action='create')


@admin_bp.route('/page-sizes/<int:page_size_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_page_size(page_size_id):
    """
    Edit an existing page size preset.

    Updates dimensions or status of a page size preset.
    """
    page_size = PageSizePreset.query.get_or_404(page_size_id)

    # Prevent editing system defaults
    if page_size.is_default:
        flash('System default page sizes cannot be edited.', 'error')
        return redirect(url_for('admin.page_sizes'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        width = request.form.get('width', type=float)
        height = request.form.get('height', type=float)
        unit = request.form.get('unit', 'mm').strip()
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Name is required.', 'error')
            return render_template('admin/page_size_form.html', page_size=page_size, action='edit')

        # Check if name is taken by another preset
        existing = PageSizePreset.query.filter_by(name=name).first()
        if existing and existing.id != page_size_id:
            flash(f'Page size preset "{name}" already exists.', 'error')
            return render_template('admin/page_size_form.html', page_size=page_size, action='edit')

        if not width or width <= 0:
            flash('Width must be a positive number.', 'error')
            return render_template('admin/page_size_form.html', page_size=page_size, action='edit')

        if not height or height <= 0:
            flash('Height must be a positive number.', 'error')
            return render_template('admin/page_size_form.html', page_size=page_size, action='edit')

        if unit not in ['mm', 'px']:
            flash('Unit must be either "mm" or "px".', 'error')
            return render_template('admin/page_size_form.html', page_size=page_size, action='edit')

        # Update page size preset
        page_size.name = name
        page_size.width = width
        page_size.height = height
        page_size.unit = unit
        page_size.is_active = is_active

        db.session.commit()

        log_activity('admin_action', f'Updated page size preset: {name} (ID: {page_size_id})')
        flash(f'Page size preset "{name}" updated successfully.', 'success')
        return redirect(url_for('admin.page_sizes'))

    return render_template('admin/page_size_form.html', page_size=page_size, action='edit')


@admin_bp.route('/page-sizes/<int:page_size_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_page_size(page_size_id):
    """
    Delete a page size preset.

    Removes a custom page size. System defaults cannot be deleted.
    """
    page_size = PageSizePreset.query.get_or_404(page_size_id)

    # Prevent deleting system defaults
    if page_size.is_default:
        flash('System default page sizes cannot be deleted.', 'error')
        return redirect(url_for('admin.page_sizes'))

    # Check if page size is used in any templates
    template_count = TemplatePreset.query.filter_by(page_size_preset_id=page_size_id).count()
    if template_count > 0:
        flash(f'Cannot delete page size "{page_size.name}" because it is used in {template_count} template(s).', 'error')
        return redirect(url_for('admin.page_sizes'))

    name = page_size.name
    db.session.delete(page_size)
    db.session.commit()

    log_activity('admin_action', f'Deleted page size preset: {name} (ID: {page_size_id})')
    flash(f'Page size preset "{name}" deleted successfully.', 'success')
    return redirect(url_for('admin.page_sizes'))


# Template Presets Management
@admin_bp.route('/templates')
@login_required
@admin_required
def templates():
    """
    List all template presets.

    Displays a list of configured generation templates.
    """
    all_templates = TemplatePreset.query.order_by(TemplatePreset.name).all()
    log_activity('admin_action', 'Viewed template presets')
    return render_template('admin/templates.html', templates=all_templates)


@admin_bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_template():
    """
    Create a new template preset.

    Handles creation of complex generation templates.
    """
    page_sizes = PageSizePreset.query.filter_by(is_active=True).order_by(PageSizePreset.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        page_size_preset_id = request.form.get('page_size_preset_id', type=int)
        orientation = request.form.get('orientation', 'portrait').strip()
        margin_top = request.form.get('margin_top', type=float)
        margin_right = request.form.get('margin_right', type=float)
        margin_bottom = request.form.get('margin_bottom', type=float)
        margin_left = request.form.get('margin_left', type=float)
        margin_unit = request.form.get('margin_unit', 'mm').strip()
        line_height = request.form.get('line_height', type=float)
        line_height_unit = request.form.get('line_height_unit', 'mm').strip()
        empty_line_spacing = request.form.get('empty_line_spacing', type=float)
        text_alignment = request.form.get('text_alignment', 'left').strip()
        global_scale = request.form.get('global_scale', type=float) or 1.0
        auto_size = request.form.get('auto_size') == 'on'
        manual_size_scale = request.form.get('manual_size_scale', type=float)
        background_color = request.form.get('background_color', '').strip()
        biases = request.form.get('biases', '').strip()
        per_line_styles = request.form.get('per_line_styles', '').strip()
        stroke_colors = request.form.get('stroke_colors', '').strip()
        stroke_widths = request.form.get('stroke_widths', '').strip()
        horizontal_stretch = request.form.get('horizontal_stretch', type=float) or 1.0
        denoise = request.form.get('denoise') == 'on'
        character_width = request.form.get('character_width', type=float)
        wrap_ratio = request.form.get('wrap_ratio', type=float)
        wrap_utilization = request.form.get('wrap_utilization', type=float)
        use_chunked_generation = request.form.get('use_chunked_generation') == 'on'
        adaptive_chunking = request.form.get('adaptive_chunking') == 'on'
        adaptive_strategy = request.form.get('adaptive_strategy', '').strip()
        words_per_chunk = request.form.get('words_per_chunk', type=int)
        chunk_spacing = request.form.get('chunk_spacing', type=float)
        max_line_width = request.form.get('max_line_width', type=float)
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Name is required.', 'error')
            return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')

        if TemplatePreset.query.filter_by(name=name).first():
            flash(f'Template preset "{name}" already exists.', 'error')
            return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')

        if not page_size_preset_id or not PageSizePreset.query.get(page_size_preset_id):
            flash('Valid page size is required.', 'error')
            return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')

        if orientation not in ['portrait', 'landscape']:
            flash('Orientation must be either "portrait" or "landscape".', 'error')
            return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')

        if margin_unit not in ['mm', 'px']:
            flash('Margin unit must be either "mm" or "px".', 'error')
            return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')

        if line_height_unit not in ['mm', 'px']:
            flash('Line height unit must be either "mm" or "px".', 'error')
            return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')

        # Create template preset
        new_template = TemplatePreset(
            name=name,
            description=description,
            page_size_preset_id=page_size_preset_id,
            orientation=orientation,
            margin_top=margin_top or 10.0,
            margin_right=margin_right or 10.0,
            margin_bottom=margin_bottom or 10.0,
            margin_left=margin_left or 10.0,
            margin_unit=margin_unit,
            line_height=line_height,
            line_height_unit=line_height_unit,
            empty_line_spacing=empty_line_spacing,
            text_alignment=text_alignment,
            global_scale=global_scale,
            auto_size=auto_size,
            manual_size_scale=manual_size_scale,
            background_color=background_color or None,
            biases=biases or None,
            per_line_styles=per_line_styles or None,
            stroke_colors=stroke_colors or None,
            stroke_widths=stroke_widths or None,
            horizontal_stretch=horizontal_stretch,
            denoise=denoise,
            character_width=character_width,
            wrap_ratio=wrap_ratio,
            wrap_utilization=wrap_utilization,
            use_chunked_generation=use_chunked_generation,
            adaptive_chunking=adaptive_chunking,
            adaptive_strategy=adaptive_strategy or None,
            words_per_chunk=words_per_chunk,
            chunk_spacing=chunk_spacing,
            max_line_width=max_line_width,
            is_active=is_active,
            created_by=current_user.id
        )

        db.session.add(new_template)
        db.session.commit()

        log_activity('admin_action', f'Created template preset: {name}')
        flash(f'Template preset "{name}" created successfully.', 'success')
        return redirect(url_for('admin.templates'))

    return render_template('admin/template_form.html', template=None, page_sizes=page_sizes, action='create')


@admin_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_template(template_id):
    """
    Edit an existing template preset.

    Updates configuration of a generation template.
    """
    template = TemplatePreset.query.get_or_404(template_id)
    page_sizes = PageSizePreset.query.filter_by(is_active=True).order_by(PageSizePreset.name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        page_size_preset_id = request.form.get('page_size_preset_id', type=int)
        orientation = request.form.get('orientation', 'portrait').strip()
        margin_top = request.form.get('margin_top', type=float)
        margin_right = request.form.get('margin_right', type=float)
        margin_bottom = request.form.get('margin_bottom', type=float)
        margin_left = request.form.get('margin_left', type=float)
        margin_unit = request.form.get('margin_unit', 'mm').strip()
        line_height = request.form.get('line_height', type=float)
        line_height_unit = request.form.get('line_height_unit', 'mm').strip()
        empty_line_spacing = request.form.get('empty_line_spacing', type=float)
        text_alignment = request.form.get('text_alignment', 'left').strip()
        global_scale = request.form.get('global_scale', type=float) or 1.0
        auto_size = request.form.get('auto_size') == 'on'
        manual_size_scale = request.form.get('manual_size_scale', type=float)
        background_color = request.form.get('background_color', '').strip()
        biases = request.form.get('biases', '').strip()
        per_line_styles = request.form.get('per_line_styles', '').strip()
        stroke_colors = request.form.get('stroke_colors', '').strip()
        stroke_widths = request.form.get('stroke_widths', '').strip()
        horizontal_stretch = request.form.get('horizontal_stretch', type=float) or 1.0
        denoise = request.form.get('denoise') == 'on'
        character_width = request.form.get('character_width', type=float)
        wrap_ratio = request.form.get('wrap_ratio', type=float)
        wrap_utilization = request.form.get('wrap_utilization', type=float)
        use_chunked_generation = request.form.get('use_chunked_generation') == 'on'
        adaptive_chunking = request.form.get('adaptive_chunking') == 'on'
        adaptive_strategy = request.form.get('adaptive_strategy', '').strip()
        words_per_chunk = request.form.get('words_per_chunk', type=int)
        chunk_spacing = request.form.get('chunk_spacing', type=float)
        max_line_width = request.form.get('max_line_width', type=float)
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Name is required.', 'error')
            return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')

        # Check if name is taken by another template
        existing = TemplatePreset.query.filter_by(name=name).first()
        if existing and existing.id != template_id:
            flash(f'Template preset "{name}" already exists.', 'error')
            return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')

        if not page_size_preset_id or not PageSizePreset.query.get(page_size_preset_id):
            flash('Valid page size is required.', 'error')
            return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')

        if orientation not in ['portrait', 'landscape']:
            flash('Orientation must be either "portrait" or "landscape".', 'error')
            return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')

        if margin_unit not in ['mm', 'px']:
            flash('Margin unit must be either "mm" or "px".', 'error')
            return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')

        if line_height_unit not in ['mm', 'px']:
            flash('Line height unit must be either "mm" or "px".', 'error')
            return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')

        # Update template preset
        template.name = name
        template.description = description
        template.page_size_preset_id = page_size_preset_id
        template.orientation = orientation
        template.margin_top = margin_top or 10.0
        template.margin_right = margin_right or 10.0
        template.margin_bottom = margin_bottom or 10.0
        template.margin_left = margin_left or 10.0
        template.margin_unit = margin_unit
        template.line_height = line_height
        template.line_height_unit = line_height_unit
        template.empty_line_spacing = empty_line_spacing
        template.text_alignment = text_alignment
        template.global_scale = global_scale
        template.auto_size = auto_size
        template.manual_size_scale = manual_size_scale
        template.background_color = background_color or None
        template.biases = biases or None
        template.per_line_styles = per_line_styles or None
        template.stroke_colors = stroke_colors or None
        template.stroke_widths = stroke_widths or None
        template.horizontal_stretch = horizontal_stretch
        template.denoise = denoise
        template.character_width = character_width
        template.wrap_ratio = wrap_ratio
        template.wrap_utilization = wrap_utilization
        template.use_chunked_generation = use_chunked_generation
        template.adaptive_chunking = adaptive_chunking
        template.adaptive_strategy = adaptive_strategy or None
        template.words_per_chunk = words_per_chunk
        template.chunk_spacing = chunk_spacing
        template.max_line_width = max_line_width
        template.is_active = is_active

        db.session.commit()

        log_activity('admin_action', f'Updated template preset: {name} (ID: {template_id})')
        flash(f'Template preset "{name}" updated successfully.', 'success')
        return redirect(url_for('admin.templates'))

    return render_template('admin/template_form.html', template=template, page_sizes=page_sizes, action='edit')


@admin_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_template(template_id):
    """
    Delete a template preset.

    Removes the template from the system.
    """
    template = TemplatePreset.query.get_or_404(template_id)

    name = template.name
    db.session.delete(template)
    db.session.commit()

    log_activity('admin_action', f'Deleted template preset: {name} (ID: {template_id})')
    flash(f'Template preset "{name}" deleted successfully.', 'success')
    return redirect(url_for('admin.templates'))
