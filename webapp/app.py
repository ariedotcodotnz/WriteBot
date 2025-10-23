"""
WriteBot Flask Application - Refactored and Modular

This is the main Flask application that ties together all the routes and utilities
for handwriting synthesis via web API.
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory, render_template
from flask_login import LoginManager, login_required

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import Flask extensions
try:
    from flask_compress import Compress
except Exception:
    Compress = None

try:
    from flask_caching import Cache
except Exception:
    Cache = None

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:
    Limiter = None
    get_remote_address = None

try:
    from flask_minify import Minify
except Exception:
    Minify = None

try:
    from flask_assets import Environment, Bundle
except Exception:
    Environment = None
    Bundle = None

# Import database and models
from webapp.models import db, User

# Import extensions module
from webapp.extensions import init_extensions

# Import route blueprints
from webapp.routes import generation_bp, batch_bp, style_bp


# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '0ea55211309ed371c3d266185fb4123f')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///writebot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask-Caching configuration
app.config['CACHE_TYPE'] = 'SimpleCache'  # Use simple in-memory cache
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Default timeout: 5 minutes

# Flask-Limiter configuration
app.config['RATELIMIT_STORAGE_URL'] = 'memory://'  # Use in-memory storage for rate limiting
app.config['RATELIMIT_HEADERS_ENABLED'] = True  # Enable rate limit headers in responses

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return db.session.get(User, int(user_id))

# Initialize Flask-Caching
cache = None
if Cache is not None:
    try:
        cache = Cache(app)
    except Exception:
        pass

# Initialize Flask-Limiter
limiter = None
if Limiter is not None and get_remote_address is not None:
    try:
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["2000 per day", "200 per hour"],
            storage_uri=app.config.get('RATELIMIT_STORAGE_URL')
        )
    except Exception:
        pass

# Initialize Flask-Minify
if Minify is not None:
    try:
        Minify(app=app, html=True, js=True, cssless=True, json=False, force=True, svg=False)
    except Exception:
        pass

# Initialize Flask-Assets
assets = None
if Environment is not None and Bundle is not None:
    try:
        assets = Environment(app)
        assets.url = app.static_url_path
        assets.directory = app.static_folder

        # Define CSS bundle - will minify and combine CSS files
        css_common = Bundle(
            'css/main.css',
            'css/carbon-components.min.css',
            # Add more CSS files as needed
            filters='rcssmin',  # Use rcssmin filter
            output='common.css'
        )

        # Define CSS bundle - will minify and combine CSS files
        css_admin = Bundle(
            'css/admin.css',
            'css/character_overrides.css',
            # Add more CSS files as needed
            filters='rcssmin',  # Use rcssmin filter
            output='admin.css'
        )

        # Define JS bundle - will minify and combine JS files
        js_common = Bundle(
            'js/main.js',  # List your JS files explicitly
            'js/carbon-components.min.js',
            # Add more JS files as needed
            filters='rjsmin',  # Use rjsmin filter
            output='common.js'
        )

        # Define JS bundle - will minify and combine JS files
        js_admin = Bundle(
            'js/admin.js',  # List your JS files explicitly
            'js/character_overrides.js',
            # Add more JS files as needed
            filters='rjsmin',  # Use rjsmin filter
            output='admin.js'
        )

        assets.register('css_admin', css_admin)
        assets.register('js_admin', js_admin)

        assets.register('css_common', css_common)
        assets.register('js_common', js_common)


    except Exception as e:
        print(f"Flask-Assets initialization failed: {e}")
        pass

# Enable compression if available
if Compress is not None:
    try:
        Compress(app)
    except Exception:
        pass

# Make extensions available globally
init_extensions(cache_instance=cache, limiter_instance=limiter, assets_instance=assets)

# Register blueprints (auth blueprint imported later to avoid circular imports)
app.register_blueprint(generation_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(style_bp)

# Import and register auth blueprint
from webapp.routes.auth_routes import auth_bp
app.register_blueprint(auth_bp)

# Import and register admin blueprint
from webapp.routes.admin_routes import admin_bp
app.register_blueprint(admin_bp)

# Import and register character override blueprint
from webapp.routes.character_override_routes import character_override_bp
app.register_blueprint(character_override_bp)


@app.route("/")
def index():
    """Serve the main application page using Flask templates."""
    from flask_login import login_required
    from webapp.utils.auth_utils import log_activity

    @login_required
    def protected_index():
        log_activity('page_view', 'Accessed main application page')
        return render_template('index.html')

    return protected_index()


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint (cached for 60 seconds)."""
    # Example of using cache decorator - cache this endpoint for 60 seconds
    if cache:
        @cache.cached(timeout=60, key_prefix='health_check')
        def _cached_health():
            return jsonify({
                "status": "ok",
                "model_ready": True,
                "version": 1,
            })
        return _cached_health()
    else:
        return jsonify({
            "status": "ok",
            "model_ready": True,
            "version": 1,
        })

@app.route('/robots.txt')
def robots():
    """robots.txt endpoint."""
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/.well-known/security.txt')
@app.route('/security.txt')
def security():
    """security.txt endpoint."""
    return send_from_directory(app.static_folder, 'security.txt')


@app.route('/docs/')
@app.route('/docs/<path:filename>')
@login_required
def serve_docs(filename='index.html'):
    """Serve Sphinx documentation."""
    docs_dir = os.path.join(PROJECT_ROOT, 'docs', 'build', 'html')

    # Check if documentation exists
    if not os.path.exists(docs_dir):
        return jsonify({
            "error": "Documentation not built",
            "message": "Please run 'cd docs && make html' to build the documentation"
        }), 404

    return send_from_directory(docs_dir, filename)


if __name__ == "__main__":
    # Single-threaded to avoid TF session concurrency issues
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=False)
