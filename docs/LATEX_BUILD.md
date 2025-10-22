# Building PDF Documentation

This guide explains how to build the WriteBot documentation as a PDF using LaTeX.

## Prerequisites

To build the PDF, you need:

1. Python dependencies (already configured in `requirements.txt`):
   - sphinx>=7.0.0
   - sphinx-rtd-theme>=2.0.0
   - sphinxcontrib-httpdomain>=1.8.1

2. LaTeX distribution with pdflatex (one of the following):
   - **Linux**: `sudo apt-get install texlive-latex-base texlive-latex-extra texlive-fonts-recommended`
   - **macOS**: Install MacTeX from https://www.tug.org/mactex/
   - **Windows**: Install MiKTeX from https://miktex.org/

## Building LaTeX Sources

From the `docs` directory, generate LaTeX sources:

```bash
cd docs
make latex
```

This creates LaTeX files in `build/latex/`, including the main file `WriteBot.tex`.

## Compiling to PDF

### Option 1: Using the Makefile (recommended)

From the `docs` directory:

```bash
make latexpdf
```

This automatically generates LaTeX sources and compiles them to PDF. The resulting PDF will be at:
`docs/build/latex/WriteBot.pdf`

### Option 2: Manual compilation

Navigate to the LaTeX build directory and run make:

```bash
cd build/latex
make
```

Or compile directly with pdflatex:

```bash
cd build/latex
pdflatex WriteBot.tex
pdflatex WriteBot.tex  # Run twice for proper cross-references
makeindex -s python.ist WriteBot.idx  # Generate index
pdflatex WriteBot.tex  # Run again to include index
```

## Configuration

LaTeX output settings are configured in `source/conf.py`:

- **latex_engine**: Set to 'pdflatex'
- **latex_elements**: Customizes paper size, fonts, and formatting
- **latex_documents**: Defines the document structure and metadata

## Customization

To customize the PDF output, edit `source/conf.py`:

```python
latex_elements = {
    'papersize': 'letterpaper',  # or 'a4paper'
    'pointsize': '10pt',         # or '11pt', '12pt'
    'preamble': r'''
\usepackage{charter}
\usepackage[defaultsans]{lato}
\usepackage{inconsolata}
''',
}
```

## Troubleshooting

### Missing LaTeX packages

If you get errors about missing LaTeX packages, install the complete TeXLive distribution:

```bash
sudo apt-get install texlive-full  # Linux
```

### Font issues

The configuration uses Charter, Lato, and Inconsolata fonts. These are included in most LaTeX distributions. If you encounter font errors, you can modify the `preamble` section in `conf.py`.

### Build warnings

Some autodoc warnings about missing modules (e.g., flask_sqlalchemy, numpy) are expected and don't prevent PDF generation. These occur because not all application dependencies are required for documentation building.

## Output Location

The compiled PDF will be located at:

```
docs/build/latex/WriteBot.pdf
```

## Quick Start

```bash
# Install Python dependencies
pip install -r docs/requirements.txt

# Build PDF (requires LaTeX installation)
cd docs
make latexpdf

# View the PDF
open build/latex/WriteBot.pdf  # macOS
xdg-open build/latex/WriteBot.pdf  # Linux
```
