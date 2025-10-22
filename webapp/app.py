"""
WriteBot Flask Application - Refactored and Modular

This is the main Flask application that ties together all the routes and utilities
for handwriting synthesis via web API.
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory, render_template
from flask_login import LoginManager

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import Flask-Compress if available
try:
    from flask_compress import Compress
except Exception:
    Compress = None

# Import database and models
from webapp.models import db, User

# Import route blueprints
from webapp.routes import generation_bp, batch_bp, style_bp


# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '0ea55211309ed371c3d266185fb4123f')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///writebot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    return User.query.get(int(user_id))

# Enable compression if available
if Compress is not None:
    try:
        Compress(app)
    except Exception:
        pass

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
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "model_ready": True,
        "version": 1,
    })


if __name__ == "__main__":
    # Single-threaded to avoid TF session concurrency issues
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=False)
