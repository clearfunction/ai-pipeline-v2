#!/bin/bash
set -e

echo "Building shared-ai-services Lambda layer..."

# Navigate to layer directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Clean up any existing build artifacts
rm -rf python/shared
rm -f shared-ai-services-layer.zip

# Create the layer structure
echo "Creating layer structure..."
mkdir -p python/shared/{services,models,utils}

# Copy shared services (including the fixed claude_code_service.py)
echo "Copying shared services..."
cp ../shared/services/*.py python/shared/services/ 2>/dev/null || true

# Copy shared models
echo "Copying shared models..."
cp ../shared/models/*.py python/shared/models/ 2>/dev/null || true

# Copy shared utils
echo "Copying shared utils..."
cp ../shared/utils/*.py python/shared/utils/ 2>/dev/null || true

# Copy __init__ files
echo "Copying __init__ files..."
cp ../shared/__init__.py python/shared/ 2>/dev/null || true
cp ../shared/services/__init__.py python/shared/services/ 2>/dev/null || true
cp ../shared/models/__init__.py python/shared/models/ 2>/dev/null || true
cp ../shared/utils/__init__.py python/shared/utils/ 2>/dev/null || true

# Install dependencies
echo "Installing dependencies..."
pip install --target python/ -r requirements.txt --upgrade

# Create the layer zip with proper structure
echo "Creating layer zip..."
zip -r9 shared-ai-services-layer.zip python/ -x "*.pyc" -x "*__pycache__*"

# Calculate hash for tracking
HASH=$(sha256sum shared-ai-services-layer.zip | cut -d' ' -f1)
echo "Layer built successfully!"
echo "SHA256: $HASH"
echo "Size: $(du -h shared-ai-services-layer.zip | cut -f1)"

# Save build metadata
cat > build-metadata.json <<EOF
{
  "buildTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "sha256": "$HASH",
  "size": "$(stat -f%z shared-ai-services-layer.zip 2>/dev/null || stat -c%s shared-ai-services-layer.zip)",
  "includedServices": [
    "anthropic_service.py",
    "claude_code_service.py",
    "dynamodb_service.py",
    "logger.py",
    "s3_service.py"
  ]
}
EOF

echo "Build metadata saved to build-metadata.json"