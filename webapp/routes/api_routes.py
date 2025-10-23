"""
API routes for accessing presets and configuration data.
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from webapp.models import PageSizePreset, TemplatePreset

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/presets/page-sizes')
@login_required
def get_page_sizes():
    """Get all active page size presets."""
    page_sizes = PageSizePreset.query.filter_by(is_active=True).order_by(PageSizePreset.name).all()
    return jsonify({
        'page_sizes': [preset.to_dict() for preset in page_sizes]
    })


@api_bp.route('/presets/page-sizes/<int:preset_id>')
@login_required
def get_page_size(preset_id):
    """Get a specific page size preset."""
    preset = PageSizePreset.query.get_or_404(preset_id)
    return jsonify(preset.to_dict())


@api_bp.route('/presets/templates')
@login_required
def get_templates():
    """Get all active template presets."""
    templates = TemplatePreset.query.filter_by(is_active=True).order_by(TemplatePreset.name).all()
    return jsonify({
        'templates': [template.to_dict() for template in templates]
    })


@api_bp.route('/presets/templates/<int:template_id>')
@login_required
def get_template(template_id):
    """Get a specific template preset with all details."""
    template = TemplatePreset.query.get_or_404(template_id)
    return jsonify(template.to_dict())
