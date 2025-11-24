# WriteBot - Handwriting Synthesis Application

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![TensorFlow](https://img.shields.io/badge/tensorflow-2.12-orange.svg)](https://www.tensorflow.org/)

WriteBot is an advanced handwriting synthesis application that converts digital text into realistic handwritten documents. It uses machine learning models trained on real handwriting data to generate natural-looking handwritten text in SVG format.

## ✨ Features

- **🖊️ Realistic Handwriting Generation**: Generate handwritten text that looks authentic using RNN models.
- **📄 Multi-Page Support**: Automatically handle long documents with intelligent pagination and layout.
- **🎨 Customizable Styles**: Choose from multiple pre-trained handwriting styles.
- **⚙️ Flexible Configuration**: Control line height, margins, page size, colors, biases, and more.
- **📦 Batch Processing**: Process multiple texts at once from CSV or Excel files with streaming progress updates.
- **🔐 User Authentication**: Secure multi-user system with role-based access control (Admin/User).
- **📊 Template System**: Pre-configured page templates for common document types and custom presets.
- **🖌️ Character Overrides**: Inject custom SVG characters to override generated handwriting for specific glyphs.
- **🌐 Web Interface**: User-friendly web application with real-time preview, rulers, and zoom controls.
- **📱 REST API**: Full-featured API for programmatic access and integration.
- **📖 Comprehensive Documentation**: Detailed guides and API documentation.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- 2GB+ RAM recommended

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ariedotcodotnz/WriteBot.git
   cd WriteBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python init_db.py
   ```
   This will create the SQLite database and an initial admin user.

4. **Start the application**
   ```bash
   python webapp/app.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:5000` and log in with your admin credentials (default credentials provided in console output of `init_db.py`).

## 📖 Documentation

### Getting Started
- [Quick Start Guide](#-quick-start) - Get up and running quickly
- [Installation Guide](docs/README.md) - Detailed installation instructions
- [User Guide](docs/TEXT_PROCESSING_GUIDE.md) - How to use WriteBot

### Features & Configuration
- [Authentication System](docs/AUTHENTICATION.md) - User management and security
- [Template Presets](PRESETS_FEATURE.md) - Page templates and configurations
- [Database Migrations](webapp/MIGRATIONS.md) - Database management
- [Text Processing](docs/TEXT_PROCESSING_GUIDE.md) - Advanced text processing features
- [Character Overrides](docs/CHARACTER_OVERRIDE_SVG_SPECS.md) - Custom character styling

### Development
- [Application Structure](docs/STRUCTURE.md) - Codebase organization
- [Model Training](model/README.md) - Training custom handwriting models
- [API Documentation](docs/build/html/index.html) - REST API reference
- [Flask Extensions](webapp/FLASK_EXTENSIONS.md) - Extension usage guide

## 💡 Usage Examples

### Web Interface

The easiest way to use WriteBot is through the web interface:

1. Log in at `http://localhost:5000`
2. Enter your text in the text area.
3. Configure page settings (size, margins, style, pen width, color).
4. Click "Generate Handwriting".
5. Preview the result with the interactive ruler and zoom tools.
6. Download your handwritten document as SVG or PDF.

### Python API

You can use the `HandwritingProcessor` class directly in your Python scripts:

```python
from handwriting_processor import HandwritingProcessor
from text_processor import TextProcessingConfig, ParagraphStyle

# Configure text processing
config = TextProcessingConfig(
    max_line_length=60,
    lines_per_page=24,
    paragraph_style=ParagraphStyle.PRESERVE_BREAKS
)

# Create processor
processor = HandwritingProcessor(text_config=config)

# Define page layout
page_params = [
    32,      # line_height
    24,      # total_lines_per_page
    896,     # view_height
    633.472, # view_width
    -64,     # margin_left
    -96,     # margin_top
    "white", # page_color
    "red",   # margin_color
    "lightgray" # line_color
]

# Generate handwriting
result = processor.process_and_write(
    input_text="Hello, World! This is a test of WriteBot.",
    output_dir='output',
    biases=0.75,
    styles=1,
    stroke_colors="Black",
    stroke_widths=1.0,
    page_params=page_params
)

print(f"Generated {result['num_pages']} pages in {result['output_dir']}")
```

### REST API

Generate handwriting programmatically via HTTP requests:

```bash
# Generate handwriting via API
curl -X POST http://localhost:5000/api/v1/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token_if_required>" \
  -d '{
    "text": "Your text here",
    "style": 1,
    "bias": 0.75,
    "stroke_color": "Black",
    "stroke_width": 1.0,
    "page_size": "A4"
  }'
```

## 🎯 Key Features Explained

### Intelligent Text Processing
WriteBot includes advanced text processing that handles:
- **Paragraph Detection**: Preserves document structure and formatting.
- **Smart Word Wrapping**: Breaks text naturally at word boundaries.
- **Hyphenation Support**: Handles long words intelligently (configurable).
- **Chunking**: Breaks long text into manageable chunks for the RNN model to maintain consistency.

### Customizable Output
Control every aspect of the generated handwriting:
- **Page Size**: A4, A5, Letter, Legal, or custom dimensions.
- **Orientation**: Portrait or landscape modes.
- **Margins**: Fully customizable margins for all sides.
- **Line Height**: Adjust vertical spacing between lines.
- **Colors**: Customize ink color and page background.
- **Style**: Multiple handwriting styles with adjustable randomness (bias).

### Batch Processing
Process multiple documents efficiently:
- **CSV/Excel Input**: Upload files with multiple rows of text and configuration.
- **Streaming Processing**: Real-time progress updates via Server-Sent Events (SSE).
- **Bulk Download**: Download all generated files as a single ZIP archive.
- **Templates**: Use downloadable templates to structure your batch requests.

## 🏗️ Architecture

WriteBot is built with a modular architecture:

```
WriteBot/
├── webapp/              # Flask web application
│   ├── routes/          # API endpoints (generation, batch, admin, auth)
│   ├── templates/       # HTML templates (Jinja2)
│   ├── static/          # CSS, JS, and assets
│   ├── models.py        # Database models (SQLAlchemy)
│   └── utils/           # Utility functions
├── handwriting_synthesis/  # Core handwriting generation engine (TensorFlow)
│   ├── hand/            # High-level Hand interface and drawing logic
│   ├── rnn/             # RNN model definitions
│   └── training/        # Training utilities
├── text_processor.py    # Advanced text processing module
├── handwriting_processor.py  # Integration layer
├── model/               # Pre-trained models and styles
├── docs/                # Documentation
└── examples/            # Example scripts
```

## 🔒 Security

WriteBot includes comprehensive security features:
- **Bcrypt Password Hashing**: Secure password storage.
- **Session Management**: Secure user sessions with Flask-Login.
- **Role-Based Access Control**: Granular permissions for Admin and User roles.
- **Activity Logging**: Audit trail of all actions (logins, generations, edits).
- **Input Validation**: Sanitization of all user inputs.
- **Rate Limiting**: API endpoints are rate-limited to prevent abuse.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Code style and standards
- How to submit pull requests
- Testing requirements
- Documentation guidelines

## 📊 Database Management

WriteBot uses SQLAlchemy and Flask-Migrate for database management:

```bash
# Initialize migrations
flask db init

# Generate a migration script
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

See [webapp/MIGRATIONS.md](webapp/MIGRATIONS.md) for complete documentation.

## 🧪 Testing

Run the demonstration scripts to see features in action:

```bash
# Test text processing
python examples/demo_text_processing.py

# Test batch processing API
python scripts/test_batch.py
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: Application won't start
- **Solution**: Ensure all dependencies are installed with `pip install -r requirements.txt`.
- **Solution**: Check that Python 3.8+ is installed with `python --version`.

**Issue**: Login doesn't work
- **Solution**: Make sure you ran `python init_db.py` to create the admin user.
- **Solution**: Check that `SECRET_KEY` environment variable is set (or uses default).

**Issue**: Generated handwriting looks strange
- **Solution**: Verify your text only contains supported characters (see alphabet list).
- **Solution**: Try adjusting the bias parameter (0.5-0.95 recommended).
- **Solution**: Enable "Chunked Generation" for longer texts.

**Issue**: Database errors
- **Solution**: Ensure the `instance` directory exists and is writable.
- **Solution**: Delete `instance/writebot.db` and run `python init_db.py` again for a clean slate.

For more help, see the detailed documentation in the [docs/](docs/) directory.

## 📝 License

This project is available under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Based on handwriting synthesis research and models (Alex Graves).
- Uses the IAM On-Line Handwriting Database for training.
- Built with Flask, TensorFlow, and other open-source technologies.

## 📞 Support

- **Documentation**: Check the [docs/](docs/) directory.
- **Issues**: Report bugs via GitHub Issues.
- **Questions**: Open a discussion on GitHub.

## 🗺️ Roadmap

Future enhancements planned:
- [ ] Additional handwriting styles and fine-tuning tools.
- [ ] Mobile app support.
- [ ] Cloud deployment configurations (Docker, Kubernetes).
- [ ] Multiple language support (beyond ASCII).
- [ ] Custom font training interface.
- [ ] Advanced PDF export options (metadata, security).

---

**Version**: 1.0.0
**Last Updated**: May 2024
**Status**: Active Development

Made with ❤️ by the WriteBot Team
