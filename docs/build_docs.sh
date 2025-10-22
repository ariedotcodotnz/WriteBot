#!/bin/bash
# Build Sphinx documentation

set -e

echo "Building WriteBot documentation..."

# Clean previous build
rm -rf build

# Build HTML documentation
sphinx-build -b html source build/html

echo "Documentation built successfully!"
echo "Open build/html/index.html in your browser"
