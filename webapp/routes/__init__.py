"""
Route modules for WriteBot Flask application.

This package contains the Flask blueprints that define the application's
routes and view functions, organized by functionality.
"""

from .generation_routes import generation_bp
from .batch_routes import batch_bp
from .style_routes import style_bp
from .presets_routes import presets_bp

__all__ = ['generation_bp', 'batch_bp', 'style_bp', 'presets_bp']
