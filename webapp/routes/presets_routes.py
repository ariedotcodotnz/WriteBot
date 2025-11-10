"""
API endpoints for page size and template presets.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from webapp.models import PageSizePreset, TemplatePreset, db
from webapp.utils.auth_utils import admin_required, log_activity

# Create blueprint
presets_bp = Blueprint('presets', __name__)


@presets_bp.route('/api/page-sizes', methods=['GET'])
@login_required
def list_page_sizes():
    """
    List all active page size presets.

    Returns:
        JSON object: { page_sizes: [ { id, name, width, height, unit, is_default } ] }
    """
    try:
        page_sizes = PageSizePreset.query.filter_by(is_active=True).order_by(
            PageSizePreset.is_default.desc(),
            PageSizePreset.name
        ).all()

        return jsonify({
            'page_sizes': [ps.to_dict() for ps in page_sizes]
        })
    except Exception as e:
        return jsonify({'page_sizes': [], 'error': str(e)}), 500


@presets_bp.route('/api/templates', methods=['GET'])
@login_required
def list_templates():
    """
    List all active template presets.

    Returns:
        JSON object: { templates: [ { id, name, description, page_size, orientation, margins, ... } ] }
    """
    try:
        templates = TemplatePreset.query.filter_by(is_active=True).order_by(
            TemplatePreset.name
        ).all()

        return jsonify({
            'templates': [t.to_dict() for t in templates]
        })
    except Exception as e:
        return jsonify({'templates': [], 'error': str(e)}), 500


@presets_bp.route('/api/templates/<int:template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """
    Get a specific template preset by ID.

    Args:
        template_id: The template ID

    Returns:
        JSON object with template details
    """
    try:
        template = TemplatePreset.query.get_or_404(template_id)

        return jsonify({
            'template': template.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@presets_bp.route('/api/templates/<int:template_id>', methods=['PATCH'])
@login_required
@admin_required
def update_template_status(template_id):
    """
    Update template preset properties (Admin only).
    Currently supports toggling is_active status.

    Args:
        template_id: The template ID

    Returns:
        JSON object with updated template details
    """
    try:
        template = TemplatePreset.query.get_or_404(template_id)
        data = request.get_json()

        # Update fields that are allowed
        if 'is_active' in data:
            template.is_active = bool(data['is_active'])

        if 'name' in data:
            name = data['name'].strip()
            if name and name != template.name:
                # Check if new name already exists
                existing = TemplatePreset.query.filter_by(name=name).first()
                if existing:
                    return jsonify({'error': f'Template with name "{name}" already exists'}), 400
                template.name = name

        if 'description' in data:
            template.description = data['description'].strip() or None

        db.session.commit()

        action = 'activated' if template.is_active else 'deactivated'
        log_activity('template_updated', f'Updated template preset: {template.name} ({action})')

        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'message': f'Template updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@presets_bp.route('/api/templates', methods=['POST'])
@login_required
@admin_required
def create_template_from_form():
    """
    Create a new template preset from form data (Admin only).

    Accepts JSON with all template fields from the main generation form.

    Returns:
        JSON object with created template details
    """
    try:
        data = request.get_json()

        # Required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Template name is required'}), 400

        # Check if template with this name already exists
        existing = TemplatePreset.query.filter_by(name=name).first()
        if existing:
            return jsonify({'error': f'Template with name "{name}" already exists'}), 400

        description = data.get('description', '').strip()
        page_size_preset_id = data.get('page_size_preset_id')

        if not page_size_preset_id:
            return jsonify({'error': 'Page size preset is required'}), 400

        # Create new template
        template = TemplatePreset(
            name=name,
            description=description if description else None,
            page_size_preset_id=page_size_preset_id,
            orientation=data.get('orientation', 'portrait'),

            # Margins
            margin_top=float(data.get('margin_top', 10.0)),
            margin_right=float(data.get('margin_right', 10.0)),
            margin_bottom=float(data.get('margin_bottom', 10.0)),
            margin_left=float(data.get('margin_left', 10.0)),
            margin_unit=data.get('margin_unit', 'mm'),

            # Line settings
            line_height=float(data['line_height']) if data.get('line_height') else None,
            line_height_unit=data.get('line_height_unit', 'mm'),
            empty_line_spacing=float(data['empty_line_spacing']) if data.get('empty_line_spacing') else None,

            # Text alignment and scaling
            text_alignment=data.get('text_alignment', 'left'),
            global_scale=float(data.get('global_scale', 1.0)),
            auto_size=data.get('auto_size', False),
            manual_size_scale=float(data['manual_size_scale']) if data.get('manual_size_scale') else None,

            # Styling
            background_color=data.get('background_color'),

            # Style control
            biases=data.get('biases'),
            per_line_styles=data.get('per_line_styles'),
            stroke_colors=data.get('stroke_colors'),
            stroke_widths=data.get('stroke_widths'),
            horizontal_stretch=float(data.get('horizontal_stretch', 1.0)),
            denoise=data.get('denoise', False),

            # Text wrapping
            character_width=float(data['character_width']) if data.get('character_width') else None,
            wrap_ratio=float(data['wrap_ratio']) if data.get('wrap_ratio') else None,
            wrap_utilization=float(data['wrap_utilization']) if data.get('wrap_utilization') else None,

            # Advanced generation
            use_chunked_generation=data.get('use_chunked_generation', False),
            adaptive_chunking=data.get('adaptive_chunking', False),
            adaptive_strategy=data.get('adaptive_strategy'),
            words_per_chunk=int(data['words_per_chunk']) if data.get('words_per_chunk') else None,
            chunk_spacing=float(data['chunk_spacing']) if data.get('chunk_spacing') else None,
            max_line_width=float(data['max_line_width']) if data.get('max_line_width') else None,

            # Active by default and track creator
            is_active=True,
            created_by=current_user.id
        )

        db.session.add(template)
        db.session.commit()

        log_activity('template_created', f'Created template preset: {name}')

        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'message': f'Template "{name}" created successfully'
        }), 201

    except ValueError as e:
        return jsonify({'error': f'Invalid value: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
