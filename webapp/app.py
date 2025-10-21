"""
WriteBot Flask Application - Refactored and Modular

This is the main Flask application that ties together all the routes and utilities
for handwriting synthesis via web API.
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import Flask-Compress if available
try:
    from flask_compress import Compress
except Exception:
    Compress = None

# Import route blueprints
from webapp.routes import generation_bp, batch_bp, style_bp


# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Enable compression if available
if Compress is not None:
    try:
        Compress(app)
    except Exception:
        pass

# Register blueprints
app.register_blueprint(generation_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(style_bp)


# Configuration
_DIST_DIR = os.path.join(os.path.dirname(__file__), 'dist')


@app.route("/")
def index():
    """Serve the main application page."""
    # If a built dist exists, serve hashed index; otherwise serve static index as-is
    dist_index_candidates = []
    if os.path.isdir(_DIST_DIR):
        for name in os.listdir(_DIST_DIR):
            if name.startswith('index.') and name.endswith('.html'):
                dist_index_candidates.append(name)

    if dist_index_candidates:
        return send_from_directory(_DIST_DIR, sorted(dist_index_candidates)[-1])

    # Fallback: serve original static index without transformation to ensure stability
    return send_from_directory(app.static_folder, "index.html")


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
