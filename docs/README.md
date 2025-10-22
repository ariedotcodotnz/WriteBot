# WriteBot Documentation

This directory contains the Sphinx documentation for the WriteBot API.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -r requirements.txt
```

### Build HTML Documentation

**Using Make (Linux/Mac):**

```bash
cd docs
make html
```

**Using the build script:**

```bash
cd docs
chmod +x build_docs.sh
./build_docs.sh
```

## Viewing the Documentation

### Via Flask Application

The documentation is automatically served by the Flask application at:

```
http://localhost:5000/docs/
```

Make sure to build the documentation first before starting the Flask app.

## Documentation Structure

```
docs/
├── source/              # Source files
│   ├── api/            # API documentation
│   ├── conf.py         # Configuration
│   └── index.rst       # Homepage
├── build/              # Generated HTML
└── requirements.txt    # Dependencies
```

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
