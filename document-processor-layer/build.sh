#!/bin/bash

# Build script for document processor Lambda layer
echo "Building document processor layer..."

# Create layer structure
rm -rf python
mkdir -p python

# Install dependencies
pip install -r requirements.txt -t python/ --no-cache-dir

# Remove unnecessary files to reduce layer size
find python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find python -type f -name "*.pyc" -exec rm -f {} + 2>/dev/null || true
find python -type f -name "*.pyo" -exec rm -f {} + 2>/dev/null || true
find python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

echo "Document processor layer build complete"