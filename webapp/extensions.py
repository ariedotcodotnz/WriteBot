"""
Flask extensions initialization module.

This module provides centralized access to Flask extensions like caching and rate limiting.
Import from this module when you need to use these extensions in your routes or utilities.
"""

# These will be initialized in app.py
cache = None
limiter = None
assets = None

def init_extensions(cache_instance=None, limiter_instance=None, assets_instance=None):
    """
    Initialize extension instances.

    This function is called from app.py after extensions are initialized.
    It populates the module-level variables for use elsewhere in the application.

    Args:
        cache_instance: Flask-Caching instance.
        limiter_instance: Flask-Limiter instance.
        assets_instance: Flask-Assets instance.
    """
    global cache, limiter, assets
    cache = cache_instance
    limiter = limiter_instance
    assets = assets_instance
