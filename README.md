# WriteBot - Handwriting Synthesis Application

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![TensorFlow](https://img.shields.io/badge/tensorflow-2.12-orange.svg)](https://www.tensorflow.org/)

WriteBot is an advanced handwriting synthesis application that converts digital text into realistic handwritten documents. It uses machine learning models trained on real handwriting data to generate natural-looking handwritten text in SVG format.

## ✨ Features

- **🖊️ Realistic Handwriting Generation**: Generate handwritten text that looks authentic
- **📄 Multi-Page Support**: Automatically handle long documents with intelligent pagination
- **🎨 Customizable Styles**: Multiple handwriting styles to choose from
- **⚙️ Flexible Configuration**: Control line height, margins, page size, colors, and more
- **📦 Batch Processing**: Process multiple texts at once from CSV files
- **🔐 User Authentication**: Secure multi-user system with admin controls
- **📊 Template System**: Pre-configured page templates for common document types
- **🌐 Web Interface**: User-friendly web application with real-time preview
- **📱 REST API**: Full-featured API for programmatic access
- **📖 Comprehensive Documentation**: Detailed guides and API documentation

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
   This will create an admin user and set up the database.

4. **Start the application**
   ```bash
   python webapp/app.py
   ```

5. **Open your browser**
   Navigate to `http://localhost:5000` and log in with your admin credentials.

## 📖 Documentation

### Getting Started
- [Quick Start Guide](#-quick-start) - Get up and running quickly
- [Installation Guide](docs/README.md) - Detailed installation instructions
- [User Guide](docs/TEXT_PROCESSING_GUIDE.md) - How to use WriteBot

### Features & Configuration
- [Authentication System](docs/AUTHENTICATION.md) - User management and security
- [Template Presets](PRESETS_FEATURE.md) - Page templates and configurations
- [Database Migrations](MIGRATIONS.md) - Database management
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
2. Enter your text in the text area
3. Configure page settings (size, margins, style)
4. Click "Generate Handwriting"
5. Preview and download your handwritten document

### Python API

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

# Define alphabet
alphabet = [' ', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 
            'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 
            'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 
            'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 
            'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', 
            '2', '3', '4', '5', '6', '7', '8', '9', '.', ',', '!', 
            '?', "'", '"', '-', '(', ')', ':', ';']

# Page parameters [line_height, lines_per_page, height, width, 
#                  margin_left, margin_top, page_color, margin_color, line_color]
page_params = [32, 24, 896, 633.472, -64, -96, "white", "red", "lightgray"]

# Generate handwriting
result = processor.process_and_write(
    input_text="Hello, World! This is a test of WriteBot.",
    output_dir='output',
    alphabet=alphabet,
    biases=0.75,
    styles=1,
    stroke_colors="Black",
    stroke_widths=1.0,
    page_params=page_params
)

print(f"Generated {result['num_pages']} pages")
```

### REST API

```bash
# Generate handwriting via API
curl -X POST http://localhost:5000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your text here",
    "style": 1,
    "bias": 0.75,
    "stroke_color": "Black",
    "stroke_width": 1.0
  }'
```

## 🎯 Key Features Explained

### Intelligent Text Processing
WriteBot includes advanced text processing that handles:
- **Paragraph Detection**: Preserves document structure
- **Smart Word Wrapping**: Breaks at word boundaries
- **Hyphenation Support**: Handles long words intelligently
- **Multiple Formatting Styles**: Choose how paragraphs are formatted

### Customizable Output
Control every aspect of the generated handwriting:
- **Page Size**: A4, A5, Letter, Legal, or custom dimensions
- **Orientation**: Portrait or landscape
- **Margins**: Fully customizable margins
- **Line Height**: Adjust spacing between lines
- **Colors**: Page background, margin guides, line guides, and stroke color
- **Style**: Multiple handwriting styles with adjustable randomness

### Batch Processing
Process multiple documents efficiently:
- **CSV Input**: Load multiple texts from a CSV file
- **Parallel Processing**: Generate multiple documents at once
- **Bulk Download**: Download all generated files as a ZIP archive

## 🏗️ Architecture

WriteBot is built with a modular architecture:

```
WriteBot/
├── webapp/              # Flask web application
│   ├── routes/         # API endpoints and routes
│   ├── templates/      # HTML templates
│   ├── static/         # CSS, JS, and assets
│   ├── migrations/     # Database migration system
│   └── utils/          # Utility functions
├── handwriting_synthesis/  # Core handwriting generation engine
├── text_processor.py   # Text processing module
├── handwriting_processor.py  # Integration layer
├── model/              # Pre-trained models and training scripts
├── docs/               # Documentation
└── examples/           # Example scripts
```

## 🔒 Security

WriteBot includes comprehensive security features:
- **Bcrypt Password Hashing**: Secure password storage
- **Session Management**: Secure user sessions
- **Role-Based Access Control**: User and admin roles
- **Activity Logging**: Audit trail of all actions
- **CSRF Protection**: Cross-site request forgery prevention
- **Input Validation**: Sanitization of all user inputs

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Code style and standards
- How to submit pull requests
- Testing requirements
- Documentation guidelines

## 📊 Database Management

WriteBot includes a comprehensive migration system:

```bash
# Check migration status
cd webapp
python migrations/migrate.py status

# Run pending migrations
python migrations/migrate.py up

# Backup database
python migrations/db_utils.py backup

# View statistics
python migrations/db_utils.py stats
```

See [MIGRATIONS.md](MIGRATIONS.md) for complete documentation.

## 🧪 Testing

Run the demonstration scripts to see features in action:

```bash
# Test text processing
python examples/demo_text_processing.py

# Test batch processing
python scripts/test_batch.py
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: Application won't start
- **Solution**: Ensure all dependencies are installed with `pip install -r requirements.txt`
- **Solution**: Check that Python 3.8+ is installed with `python --version`

**Issue**: Login doesn't work
- **Solution**: Make sure you ran `python init_db.py` to create the admin user
- **Solution**: Check that `SECRET_KEY` environment variable is set

**Issue**: Generated handwriting looks strange
- **Solution**: Verify your text only contains supported characters (see alphabet list)
- **Solution**: Try adjusting the bias parameter (0.5-0.95 recommended)

**Issue**: Database errors
- **Solution**: Delete `writebot.db` and run `python init_db.py` again
- **Solution**: Check database permissions

For more help, see the detailed documentation in the [docs/](docs/) directory.

## 📝 License

This project is available under the MIT License. See the LICENSE file for details.

## 🙏 Acknowledgments

- Based on handwriting synthesis research and models
- Uses the IAM On-Line Handwriting Database for training
- Built with Flask, TensorFlow, and other open-source technologies

## 📞 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs via GitHub Issues
- **Questions**: Open a discussion on GitHub

## 🗺️ Roadmap

Future enhancements planned:
- [ ] Additional handwriting styles
- [ ] Real-time preview in web interface
- [ ] Mobile app support
- [ ] Cloud deployment options
- [ ] Multiple language support
- [ ] Custom font training
- [ ] PDF export option
- [ ] Batch API endpoints

---

**Version**: 1.0.0  
**Last Updated**: October 2025  
**Status**: Active Development

Made with ❤️ by the WriteBot team
