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

# Import Flask-Mailman for email notifications
try:
    from flask_mailman import Mail
    _mail_available = True
except ImportError:
    Mail = None
    _mail_available = False

# Import Sentry for error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    _sentry_available = True
except ImportError:
    sentry_sdk = None
    _sentry_available = False

# Import structlog for structured logging
try:
    import structlog
    _structlog_available = True
except ImportError:
    structlog = None
    _structlog_available = False

# Import database and models
from webapp.models import db, User

# Import extensions module
from webapp.extensions import init_extensions

# Import GPU configuration for status reporting
try:
    from handwriting_synthesis.tf.gpu_config import get_gpu_config, initialize_gpu
    _gpu_available = True
except ImportError:
    _gpu_available = False
    get_gpu_config = None
    initialize_gpu = None

# Import Redis for health checks
try:
    import redis
    _redis_available = True
except ImportError:
    _redis_available = False
    redis = None

# Redis URL from environment (same as celery_app.py)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Import route blueprints
from webapp.routes import generation_bp, batch_bp, style_bp, presets_bp


# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '0ea55211309ed371c3d266185fb4123f')

# Set database path - use instance folder for consistency
if not os.environ.get('DATABASE_URL'):
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'writebot.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

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
    """
    Load user by ID for Flask-Login.

    Args:
        user_id: The user ID to load.

    Returns:
        User object or None.
    """
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

        # Define CSS bundle - modular CSS files combined and minified
        css_common = Bundle(
            # Base styles
            'css/base/variables.css',
            'css/base/reset.css',
            # Layout
            'css/layout/grid.css',
            'css/layout/actions.css',
            # Components
            'css/components/cards.css',
            'css/components/forms.css',
            'css/components/buttons.css',
            'css/components/tooltips.css',
            'css/components/modals.css',
            'css/components/style-dropdown.css',
            'css/components/preview.css',
            'css/components/code.css',
            'css/components/dropzone.css',
            'css/components/batch.css',
            'css/components/notifications.css',
            'css/components/loading.css',
            'css/components/footer.css',
            # Utilities and responsive
            'css/utilities.css',
            'css/responsive.css',
            # External libraries
            'css/carbon-components.min.css',
            filters='rcssmin',
            output='common.css'
        )

        # Define CSS bundle for admin pages
        css_admin = Bundle(
            'css/admin.css',
            'css/character_overrides.css',
            filters='rcssmin',
            output='admin.css'
        )

        # Define JS bundle - modular JS files combined and minified
        js_common = Bundle(
            # Module: Notifications (must come first as other modules depend on it)
            'js/modules/notifications.js',
            # Module: Alpine.js Application
            'js/modules/alpine-app.js',
            # External libraries
            'js/libraries/carbon-components.min.js',
            filters='rjsmin',
            output='common.js'
        )

        # Define JS bundle for generator page (SVG ruler)
        js_generator = Bundle(
            'js/svg-ruler.js',
            filters='rjsmin',
            output='generator.js'
        )

        # Define JS bundle for admin pages
        js_admin = Bundle(
            'js/admin.js',
            'js/character_overrides.js',
            filters='rjsmin',
            output='admin.js'
        )

        assets.register('css_admin', css_admin)
        assets.register('js_admin', js_admin)

        assets.register('js_generator', js_generator)

        assets.register('css_common', css_common)
        assets.register('js_common', js_common)


    except Exception as e:
        print(f"Flask-Assets initialization failed: {e}")
        pass

# Initialize Sentry for error tracking
if _sentry_available and os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.environ['SENTRY_DSN'],
        integrations=[FlaskIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

# Initialize Flask-Mailman for email notifications
mail = None
if _mail_available:
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    try:
        mail = Mail(app)
    except Exception as e:
        print(f"Flask-Mailman initialization failed: {e}")
        mail = None

# Initialize structlog for structured logging
if _structlog_available:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Job storage configuration
app.config['JOB_FILES_DIR'] = os.environ.get('JOB_FILES_DIR',
    os.path.join(os.path.dirname(__file__), 'job_storage'))
app.config['JOB_RETENTION_DAYS'] = int(os.environ.get('JOB_RETENTION_DAYS', 30))
os.makedirs(app.config['JOB_FILES_DIR'], exist_ok=True)

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
app.register_blueprint(presets_bp)

# Import and register auth blueprint
from webapp.routes.auth_routes import auth_bp
app.register_blueprint(auth_bp)

# Import and register admin blueprint
from webapp.routes.admin_routes import admin_bp
app.register_blueprint(admin_bp)

# Import and register character override blueprint
from webapp.routes.character_override_routes import character_override_bp
app.register_blueprint(character_override_bp)

# Import and register jobs blueprint
from webapp.routes.job_routes import jobs_bp
app.register_blueprint(jobs_bp)

# Public API endpoint for character override collections (not under admin prefix)
@app.route('/api/collections')
@login_required
def get_character_override_collections():
    """
    API endpoint to get all active character override collections for generation form.

    Returns:
        JSON response containing a list of override collections.
    """
    from webapp.models import CharacterOverrideCollection
    collections = CharacterOverrideCollection.query.filter_by(is_active=True).order_by(CharacterOverrideCollection.name).all()

    return jsonify([{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'character_count': c.get_character_count(),
        'unique_characters': len(c.get_unique_characters())
    } for c in collections])


@app.route("/")
def index():
    """
    Serve the main application page using Flask templates.

    Requires login. Logs the page view activity.
    """
    from flask_login import login_required
    from webapp.utils.auth_utils import log_activity

    @login_required
    def protected_index():
        log_activity('page_view', 'Accessed main application page')
        return render_template('index.html')

    return protected_index()


@app.route("/api/health", methods=["GET"])
def health():
    """
    Health check endpoint (cached for 60 seconds).

    Returns:
        JSON status response with database, Redis, and GPU info.
    """
    def _get_health_status():
        status = {
            "status": "ok",
            "model_ready": True,
            "version": 2,
        }

        # Check database status
        try:
            db.session.execute(db.text('SELECT 1'))
            status["database"] = {"status": "ok"}
        except Exception as e:
            status["database"] = {"status": "error", "message": str(e)}
            status["status"] = "degraded"

        # Check Redis status
        if _redis_available and REDIS_URL:
            try:
                r = redis.from_url(REDIS_URL, socket_timeout=2)
                r.ping()
                status["redis"] = {"status": "ok"}
            except Exception as e:
                status["redis"] = {"status": "error", "message": str(e)}
                status["status"] = "degraded"
        else:
            status["redis"] = {"status": "unavailable", "message": "Redis not configured"}

        # Add GPU status if available
        if _gpu_available and get_gpu_config:
            gpu_config = get_gpu_config()
            if gpu_config:
                status["gpu"] = {
                    "available": gpu_config.is_gpu_available,
                    "count": gpu_config.gpu_count,
                    "mixed_precision": gpu_config.is_mixed_precision_enabled,
                }
                if gpu_config.is_gpu_available:
                    status["compute_mode"] = "GPU"
                else:
                    status["compute_mode"] = "CPU"
            else:
                status["compute_mode"] = "CPU"
                status["gpu"] = {"available": False}
        else:
            status["compute_mode"] = "CPU"
            status["gpu"] = {"available": False}

        return jsonify(status)

    # Example of using cache decorator - cache this endpoint for 60 seconds
    if cache:
        @cache.cached(timeout=60, key_prefix='health_check')
        def _cached_health():
            return _get_health_status()
        return _cached_health()
    else:
        return _get_health_status()

@app.route('/robots.txt')
def robots():
    """
    robots.txt endpoint.

    Returns:
        Static robots.txt file.
    """
    return send_from_directory(app.static_folder, 'robots.txt')

@app.route('/.well-known/security.txt')
@app.route('/security.txt')
def security():
    """
    security.txt endpoint.

    Returns:
        Static security.txt file.
    """
    return send_from_directory(app.static_folder, 'security.txt')


@app.route('/docs/')
@app.route('/docs/<path:filename>')
@login_required
def serve_docs(filename='index.html'):
    """
    Serve Sphinx documentation.

    Args:
        filename: The documentation file to serve.

    Returns:
        The requested file or a 404 error if documentation is not built.
    """
    docs_dir = os.path.join(PROJECT_ROOT, 'docs', 'build', 'html')

    # Check if documentation exists
    if not os.path.exists(docs_dir):
        return jsonify({
            "error": "Documentation not built",
            "message": "Please run 'cd docs && make html' to build the documentation"
        }), 404

    return send_from_directory(docs_dir, filename)


# Custom error handlers
@app.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request errors."""
    return render_template('error.html',
        error_code=400,
        error_title="Bad Request",
        error_message="The server could not understand your request. Please check your input and try again."
    ), 400


@app.errorhandler(403)
def forbidden(e):
    """Handle 403 Forbidden errors."""
    return render_template('error.html',
        error_code=403,
        error_title="Access Denied",
        error_message="You don't have permission to access this resource. Please contact an administrator if you believe this is an error."
    ), 403


@app.errorhandler(404)
def not_found(e):
    """Handle 404 Not Found errors."""
    return render_template('error.html',
        error_code=404,
        error_title="Page Not Found",
        error_message="The page you're looking for doesn't exist or has been moved."
    ), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 Internal Server errors."""
    return render_template('error.html',
        error_code=500,
        error_title="Internal Server Error",
        error_message="Something went wrong on our end. Please try again later or contact support if the problem persists."
    ), 500


@app.errorhandler(503)
def service_unavailable(e):
    """Handle 503 Service Unavailable errors."""
    return render_template('error.html',
        error_code=503,
        error_title="Service Unavailable",
        error_message="The service is temporarily unavailable. Please try again in a few moments."
    ), 503


if __name__ == "__main__":
    # Single-threaded to avoid TF session concurrency issues
    app.run(host="0.0.0.0", port=5000, threaded=False)
