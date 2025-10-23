"""
Routes for managing page size and template presets in the admin panel.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from webapp.models import db, PageSizePreset, TemplatePreset
from webapp.utils.auth_utils import admin_required

preset_bp = Blueprint('presets', __name__, url_prefix='/admin/presets')


# ==================== Page Size Preset Routes ====================

@preset_bp.route('/page-sizes/')
@login_required
@admin_required
def list_page_sizes():
    """List all page size presets."""
    search_query = request.args.get('search', '').strip()

    query = PageSizePreset.query

    if search_query:
        query = query.filter(
            or_(
                PageSizePreset.name.ilike(f'%{search_query}%'),
                PageSizePreset.description.ilike(f'%{search_query}%')
            )
        )

    page_sizes = query.order_by(PageSizePreset.is_default.desc(), PageSizePreset.name).all()

    return render_template(
        'admin/presets/page_sizes.html',
        page_sizes=page_sizes,
        search_query=search_query
    )


@preset_bp.route('/page-sizes/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_page_size():
    """Create a new page size preset."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        width = request.form.get('width', '').strip()
        height = request.form.get('height', '').strip()
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Page size name is required.', 'error')
            return render_template('admin/presets/page_size_form.html', action='create')

        if not width or not height:
            flash('Width and height are required.', 'error')
            return render_template('admin/presets/page_size_form.html', action='create')

        # Check for duplicate name
        existing = PageSizePreset.query.filter_by(name=name).first()
        if existing:
            flash(f'A page size with name "{name}" already exists.', 'error')
            return render_template('admin/presets/page_size_form.html', action='create')

        try:
            width_float = float(width)
            height_float = float(height)

            if width_float <= 0 or height_float <= 0:
                flash('Width and height must be positive numbers.', 'error')
                return render_template('admin/presets/page_size_form.html', action='create')

            # Create new preset
            preset = PageSizePreset(
                name=name,
                description=description or None,
                width=width_float,
                height=height_float,
                is_default=False,
                is_active=is_active,
                created_by=current_user.id
            )

            db.session.add(preset)
            db.session.commit()

            flash(f'Page size preset "{name}" created successfully!', 'success')
            return redirect(url_for('presets.list_page_sizes'))

        except ValueError:
            flash('Invalid width or height value. Please enter valid numbers.', 'error')
            return render_template('admin/presets/page_size_form.html', action='create')

    return render_template('admin/presets/page_size_form.html', action='create')


@preset_bp.route('/page-sizes/<int:preset_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_page_size(preset_id):
    """Edit an existing page size preset."""
    preset = PageSizePreset.query.get_or_404(preset_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        width = request.form.get('width', '').strip()
        height = request.form.get('height', '').strip()
        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Page size name is required.', 'error')
            return render_template('admin/presets/page_size_form.html', action='edit', preset=preset)

        if not width or not height:
            flash('Width and height are required.', 'error')
            return render_template('admin/presets/page_size_form.html', action='edit', preset=preset)

        # Check for duplicate name (excluding current preset)
        existing = PageSizePreset.query.filter(
            PageSizePreset.name == name,
            PageSizePreset.id != preset_id
        ).first()
        if existing:
            flash(f'A page size with name "{name}" already exists.', 'error')
            return render_template('admin/presets/page_size_form.html', action='edit', preset=preset)

        try:
            width_float = float(width)
            height_float = float(height)

            if width_float <= 0 or height_float <= 0:
                flash('Width and height must be positive numbers.', 'error')
                return render_template('admin/presets/page_size_form.html', action='edit', preset=preset)

            # Update preset
            preset.name = name
            preset.description = description or None
            preset.width = width_float
            preset.height = height_float
            preset.is_active = is_active

            db.session.commit()

            flash(f'Page size preset "{name}" updated successfully!', 'success')
            return redirect(url_for('presets.list_page_sizes'))

        except ValueError:
            flash('Invalid width or height value. Please enter valid numbers.', 'error')
            return render_template('admin/presets/page_size_form.html', action='edit', preset=preset)

    return render_template('admin/presets/page_size_form.html', action='edit', preset=preset)


@preset_bp.route('/page-sizes/<int:preset_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_page_size(preset_id):
    """Delete a page size preset."""
    preset = PageSizePreset.query.get_or_404(preset_id)

    # Prevent deletion of default presets
    if preset.is_default:
        flash('Cannot delete default page size presets.', 'error')
        return redirect(url_for('presets.list_page_sizes'))

    # Check if used by templates
    template_count = preset.templates.count()
    if template_count > 0:
        flash(f'Cannot delete page size "{preset.name}" because it is used by {template_count} template(s).', 'error')
        return redirect(url_for('presets.list_page_sizes'))

    name = preset.name
    db.session.delete(preset)
    db.session.commit()

    flash(f'Page size preset "{name}" deleted successfully.', 'success')
    return redirect(url_for('presets.list_page_sizes'))


# ==================== Template Preset Routes ====================

@preset_bp.route('/templates/')
@login_required
@admin_required
def list_templates():
    """List all template presets."""
    search_query = request.args.get('search', '').strip()

    query = TemplatePreset.query

    if search_query:
        query = query.filter(
            or_(
                TemplatePreset.name.ilike(f'%{search_query}%'),
                TemplatePreset.description.ilike(f'%{search_query}%')
            )
        )

    templates = query.order_by(TemplatePreset.is_default.desc(), TemplatePreset.name).all()

    return render_template(
        'admin/presets/templates.html',
        templates=templates,
        search_query=search_query
    )


@preset_bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_template():
    """Create a new template preset."""
    page_sizes = PageSizePreset.query.filter_by(is_active=True).order_by(PageSizePreset.name).all()

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        page_size_id = request.form.get('page_size_id', '').strip()
        custom_width = request.form.get('custom_width', '').strip()
        custom_height = request.form.get('custom_height', '').strip()
        orientation = request.form.get('orientation', 'portrait')

        # Margins
        margin_top = request.form.get('margin_top', '20.0').strip()
        margin_right = request.form.get('margin_right', '20.0').strip()
        margin_bottom = request.form.get('margin_bottom', '20.0').strip()
        margin_left = request.form.get('margin_left', '20.0').strip()

        # Layout
        line_height = request.form.get('line_height', '60.0').strip()
        alignment = request.form.get('alignment', 'left')
        background = request.form.get('background', 'white').strip()

        # Writing settings
        global_scale = request.form.get('global_scale', '1.0').strip()
        default_style = request.form.get('default_style', '9').strip()
        default_bias = request.form.get('default_bias', '0.75').strip()
        legibility = request.form.get('legibility', '0.0').strip()

        # Stroke settings
        stroke_color = request.form.get('stroke_color', 'black').strip()
        stroke_width = request.form.get('stroke_width', '2').strip()

        # Advanced settings
        x_stretch = request.form.get('x_stretch', '1.0').strip()
        denoise = request.form.get('denoise') == 'on'
        use_chunked = request.form.get('use_chunked') == 'on'

        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Template name is required.', 'error')
            return render_template('admin/presets/template_form.html', action='create', page_sizes=page_sizes)

        # Check for duplicate name
        existing = TemplatePreset.query.filter_by(name=name).first()
        if existing:
            flash(f'A template with name "{name}" already exists.', 'error')
            return render_template('admin/presets/template_form.html', action='create', page_sizes=page_sizes)

        try:
            # Create new template
            template = TemplatePreset(
                name=name,
                description=description or None,
                page_size_id=int(page_size_id) if page_size_id else None,
                custom_width=float(custom_width) if custom_width else None,
                custom_height=float(custom_height) if custom_height else None,
                orientation=orientation,
                margin_top=float(margin_top),
                margin_right=float(margin_right),
                margin_bottom=float(margin_bottom),
                margin_left=float(margin_left),
                line_height=float(line_height),
                alignment=alignment,
                background=background,
                global_scale=float(global_scale),
                default_style=int(default_style),
                default_bias=float(default_bias),
                legibility=float(legibility),
                stroke_color=stroke_color,
                stroke_width=int(stroke_width),
                x_stretch=float(x_stretch),
                denoise=denoise,
                use_chunked=use_chunked,
                is_default=False,
                is_active=is_active,
                created_by=current_user.id
            )

            db.session.add(template)
            db.session.commit()

            flash(f'Template preset "{name}" created successfully!', 'success')
            return redirect(url_for('presets.list_templates'))

        except ValueError as e:
            flash(f'Invalid input value: {str(e)}', 'error')
            return render_template('admin/presets/template_form.html', action='create', page_sizes=page_sizes)

    return render_template('admin/presets/template_form.html', action='create', page_sizes=page_sizes)


@preset_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_template(template_id):
    """Edit an existing template preset."""
    template = TemplatePreset.query.get_or_404(template_id)
    page_sizes = PageSizePreset.query.filter_by(is_active=True).order_by(PageSizePreset.name).all()

    if request.method == 'POST':
        # Get form data (same as create)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        page_size_id = request.form.get('page_size_id', '').strip()
        custom_width = request.form.get('custom_width', '').strip()
        custom_height = request.form.get('custom_height', '').strip()
        orientation = request.form.get('orientation', 'portrait')

        # Margins
        margin_top = request.form.get('margin_top', '20.0').strip()
        margin_right = request.form.get('margin_right', '20.0').strip()
        margin_bottom = request.form.get('margin_bottom', '20.0').strip()
        margin_left = request.form.get('margin_left', '20.0').strip()

        # Layout
        line_height = request.form.get('line_height', '60.0').strip()
        alignment = request.form.get('alignment', 'left')
        background = request.form.get('background', 'white').strip()

        # Writing settings
        global_scale = request.form.get('global_scale', '1.0').strip()
        default_style = request.form.get('default_style', '9').strip()
        default_bias = request.form.get('default_bias', '0.75').strip()
        legibility = request.form.get('legibility', '0.0').strip()

        # Stroke settings
        stroke_color = request.form.get('stroke_color', 'black').strip()
        stroke_width = request.form.get('stroke_width', '2').strip()

        # Advanced settings
        x_stretch = request.form.get('x_stretch', '1.0').strip()
        denoise = request.form.get('denoise') == 'on'
        use_chunked = request.form.get('use_chunked') == 'on'

        is_active = request.form.get('is_active') == 'on'

        # Validation
        if not name:
            flash('Template name is required.', 'error')
            return render_template('admin/presets/template_form.html', action='edit', template=template, page_sizes=page_sizes)

        # Check for duplicate name (excluding current template)
        existing = TemplatePreset.query.filter(
            TemplatePreset.name == name,
            TemplatePreset.id != template_id
        ).first()
        if existing:
            flash(f'A template with name "{name}" already exists.', 'error')
            return render_template('admin/presets/template_form.html', action='edit', template=template, page_sizes=page_sizes)

        try:
            # Update template
            template.name = name
            template.description = description or None
            template.page_size_id = int(page_size_id) if page_size_id else None
            template.custom_width = float(custom_width) if custom_width else None
            template.custom_height = float(custom_height) if custom_height else None
            template.orientation = orientation
            template.margin_top = float(margin_top)
            template.margin_right = float(margin_right)
            template.margin_bottom = float(margin_bottom)
            template.margin_left = float(margin_left)
            template.line_height = float(line_height)
            template.alignment = alignment
            template.background = background
            template.global_scale = float(global_scale)
            template.default_style = int(default_style)
            template.default_bias = float(default_bias)
            template.legibility = float(legibility)
            template.stroke_color = stroke_color
            template.stroke_width = int(stroke_width)
            template.x_stretch = float(x_stretch)
            template.denoise = denoise
            template.use_chunked = use_chunked
            template.is_active = is_active

            db.session.commit()

            flash(f'Template preset "{name}" updated successfully!', 'success')
            return redirect(url_for('presets.list_templates'))

        except ValueError as e:
            flash(f'Invalid input value: {str(e)}', 'error')
            return render_template('admin/presets/template_form.html', action='edit', template=template, page_sizes=page_sizes)

    return render_template('admin/presets/template_form.html', action='edit', template=template, page_sizes=page_sizes)


@preset_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_template(template_id):
    """Delete a template preset."""
    template = TemplatePreset.query.get_or_404(template_id)

    # Prevent deletion of default templates
    if template.is_default:
        flash('Cannot delete default template presets.', 'error')
        return redirect(url_for('presets.list_templates'))

    name = template.name
    db.session.delete(template)
    db.session.commit()

    flash(f'Template preset "{name}" deleted successfully.', 'success')
    return redirect(url_for('presets.list_templates'))


@preset_bp.route('/templates/<int:template_id>/view')
@login_required
@admin_required
def view_template(template_id):
    """View template details in JSON format."""
    template = TemplatePreset.query.get_or_404(template_id)
    return jsonify(template.to_dict())
