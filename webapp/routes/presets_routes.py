"""
API endpoints for page size and template presets.
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from webapp.models import PageSizePreset, TemplatePreset

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
