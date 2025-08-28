#!/bin/bash

# Build script for Claude Code SDK Lambda Layer
# This creates a minimal layer without pydantic dependencies

set -e

echo "Building Claude Code SDK Lambda Layer..."
echo "========================================="

# Clean up any previous builds
rm -rf python/
rm -f claude-code-layer.zip

echo "Installing dependencies for Lambda runtime..."

# Use Lambda Python 3.11 runtime container to ensure compatibility
docker run --rm -v "$PWD":/var/task \
  --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.11 \
  -c "
    pip install --target /var/task/python \
      claude-code-sdk==0.0.20 && \
    pip install --target /var/task/python --no-deps \
      anyio \
      typing-extensions \
      sniffio \
      idna && \
    find /var/task/python -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /var/task/python -type f -name '*.pyc' -delete 2>/dev/null || true
  "

echo "Creating layer zip file..."

# Create the zip file with correct Lambda layer structure (python/ directory preserved)
zip -r9 claude-code-layer.zip python/

# Display the final size
echo ""
echo "Layer build complete!"
echo "Size: $(du -h claude-code-layer.zip | cut -f1)"

# Verify it's under Lambda layer limits
size_in_bytes=$(stat -f%z claude-code-layer.zip 2>/dev/null || stat --format=%s claude-code-layer.zip 2>/dev/null)
size_in_mb=$((size_in_bytes / 1024 / 1024))

if [ $size_in_mb -lt 50 ]; then
    echo "✅ Layer size is ${size_in_mb}MB - within Lambda limits (50MB)"
else
    echo "⚠️  Warning: Layer size is ${size_in_mb}MB - may exceed Lambda limits"
fi

echo ""
echo "To deploy this layer:"
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name claude-code-sdk \\"
echo "    --zip-file fileb://claude-code-layer.zip \\"
echo "    --compatible-runtimes python3.11 \\"
echo "    --compatible-architectures x86_64 arm64"