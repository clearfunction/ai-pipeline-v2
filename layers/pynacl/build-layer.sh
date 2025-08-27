#!/bin/bash
# Build script for PyNaCl Lambda Layer with x86_64 architecture
# This creates a properly compiled PyNaCl layer for AWS Lambda

set -e

echo "🔧 Building PyNaCl Lambda Layer for x86_64 architecture..."

# Set variables
LAYER_NAME="pynacl-layer"
BUILD_DIR="/tmp/${LAYER_NAME}-build"
OUTPUT_DIR="$(pwd)"
ZIP_FILE="${OUTPUT_DIR}/${LAYER_NAME}.zip"

# Clean up any existing build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/python"

# Clean up any existing zip
rm -f "$ZIP_FILE"

echo "📦 Installing PyNaCl and dependencies using Docker for x86_64..."

# Use AWS SAM build image to ensure compatibility with Lambda runtime
# Explicitly set platform to linux/amd64 for x86_64 architecture
docker run \
  --platform linux/amd64 \
  --rm \
  -v "$BUILD_DIR":/var/task \
  public.ecr.aws/sam/build-python3.11:latest \
  /bin/bash -c "
    echo '🔨 Installing PyNaCl with libsodium for x86_64...'
    pip install --platform manylinux2014_x86_64 --only-binary=:all: \
      -t /var/task/python \
      PyNaCl>=1.5.0 \
      cffi>=1.4.1 \
      pycparser
    
    echo '✅ Testing PyNaCl import...'
    cd /var/task/python
    python -c 'from nacl import encoding, public; print(\"✅ PyNaCl import successful\")'
    
    echo '📋 Installed packages:'
    pip list --path /var/task/python
  "

echo "📦 Creating Lambda layer zip..."
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" python/

echo "📊 Layer package details:"
echo "   Size: $(du -h $ZIP_FILE | cut -f1)"
echo "   Location: $ZIP_FILE"

# Verify the package
echo "🔍 Verifying layer contents..."
unzip -l "$ZIP_FILE" | grep -E "(nacl|cffi)" | head -10

echo ""
echo "✅ PyNaCl Lambda layer built successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Upload this layer to AWS Lambda:"
echo "      aws lambda publish-layer-version \\"
echo "        --layer-name pynacl-x86-64 \\"
echo "        --description \"PyNaCl with libsodium for GitHub secrets encryption\" \\"
echo "        --zip-file fileb://${ZIP_FILE} \\"
echo "        --compatible-runtimes python3.11 \\"
echo "        --compatible-architectures x86_64"
echo ""
echo "   2. Or use in CDK (see infrastructure update)"