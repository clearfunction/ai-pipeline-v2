#!/bin/bash

# Build script for shared Lambda layers
# This script ensures all layers are built consistently and include all necessary files

set -e

echo "Building Shared Lambda Layers for AI Pipeline v2"
echo "================================================"

# Clean up any previous builds
echo "Cleaning up previous builds..."
rm -rf shared-models-layer/python/
rm -rf shared-ai-services-layer/python/

echo ""
echo "Building shared-models-layer..."
echo "==============================="

# Create models layer structure
mkdir -p shared-models-layer/python/shared/{models,utils}

# Copy shared models and utilities (no external dependencies)
cp -r shared/models/* shared-models-layer/python/shared/models/
cp -r shared/utils/* shared-models-layer/python/shared/utils/
cp shared/__init__.py shared-models-layer/python/shared/

# Create __init__.py files
touch shared-models-layer/python/shared/models/__init__.py
touch shared-models-layer/python/shared/utils/__init__.py

echo "✅ Shared models layer built successfully"

echo ""
echo "Building shared-ai-services-layer..."
echo "===================================="

# Create AI services layer structure  
mkdir -p shared-ai-services-layer/python

# Install external AI dependencies using pip
echo "Installing external dependencies..."
pip install --target shared-ai-services-layer/python \
    anthropic>=0.64.0 \
    pydantic>=2.5.0 \
    requests>=2.32.0 \
    boto3>=1.34.0 \
    anyio>=4.0.0 \
    typing-extensions>=4.0.0

# Copy shared services and models (include claude_code_service.py)
echo "Copying shared Python modules..."
mkdir -p shared-ai-services-layer/python/shared/{models,services,utils}

cp -r shared/models/* shared-ai-services-layer/python/shared/models/
cp -r shared/services/* shared-ai-services-layer/python/shared/services/
cp -r shared/utils/* shared-ai-services-layer/python/shared/utils/
cp shared/__init__.py shared-ai-services-layer/python/shared/

# Ensure all __init__.py files exist
touch shared-ai-services-layer/python/shared/models/__init__.py
touch shared-ai-services-layer/python/shared/services/__init__.py
touch shared-ai-services-layer/python/shared/utils/__init__.py

# Create requirements.txt for the AI services layer
cat > shared-ai-services-layer/requirements.txt << EOF
# AI Service Dependencies for Lambda Layer
anthropic>=0.64.0
pydantic>=2.5.0
requests>=2.32.0
boto3>=1.34.0
anyio>=4.0.0
typing-extensions>=4.0.0
EOF

echo "✅ Shared AI services layer built successfully"

echo ""
echo "Layer build summary:"
echo "==================="
echo "✅ shared-models-layer: $(du -sh shared-models-layer | cut -f1)"
echo "✅ shared-ai-services-layer: $(du -sh shared-ai-services-layer | cut -f1)"

# Verify important files are included
echo ""
echo "Verifying critical files:"
echo "========================"

if [ -f "shared-ai-services-layer/python/shared/services/claude_code_service.py" ]; then
    echo "✅ claude_code_service.py included in AI services layer"
else
    echo "❌ claude_code_service.py missing from AI services layer"
    exit 1
fi

if [ -f "shared-models-layer/python/shared/models/pipeline_models.py" ]; then
    echo "✅ pipeline_models.py included in models layer"
else
    echo "❌ pipeline_models.py missing from models layer"
    exit 1
fi

echo ""
echo "🎉 All shared layers built successfully!"
echo ""
echo "To deploy these layers, run:"
echo "  cd infrastructure && npm run deploy-dev"
echo ""
echo "This script ensures reproducible builds across all environments."