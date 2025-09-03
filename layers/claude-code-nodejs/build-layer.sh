#!/bin/bash

# Build script for Claude Code Node.js Lambda Layer
# Creates a layer package with proper directory structure for AWS Lambda

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Claude Code Node.js Layer...${NC}"

# Clean up previous builds
echo -e "${YELLOW}Cleaning up previous builds...${NC}"
rm -rf nodejs node_modules claude-code-layer.zip package-lock.json

# Create the proper layer directory structure
echo -e "${YELLOW}Creating layer directory structure...${NC}"
mkdir -p nodejs

# Copy package.json to nodejs directory
cp package.json nodejs/

# Install dependencies in the nodejs directory
echo -e "${YELLOW}Installing dependencies...${NC}"
cd nodejs
npm install --production --no-save

# Remove unnecessary files to reduce layer size
echo -e "${YELLOW}Optimizing layer size...${NC}"
find . -name "*.md" -not -name "README.md" -delete 2>/dev/null || true
find . -name "*.test.js" -delete 2>/dev/null || true
find . -name "*.spec.js" -delete 2>/dev/null || true
find . -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "test" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "docs" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".github" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.ts" -delete 2>/dev/null || true
find . -name "*.map" -delete 2>/dev/null || true

# Go back to layer root
cd ..

# Create the zip file
echo -e "${YELLOW}Creating layer zip file...${NC}"
zip -rq claude-code-layer.zip nodejs/

# Display layer size
LAYER_SIZE=$(du -h claude-code-layer.zip | cut -f1)
echo -e "${GREEN}Layer created successfully: claude-code-layer.zip (${LAYER_SIZE})${NC}"

# Check if layer size is within AWS limits
LAYER_SIZE_BYTES=$(stat -f%z claude-code-layer.zip 2>/dev/null || stat -c%s claude-code-layer.zip 2>/dev/null)
MAX_SIZE=$((50 * 1024 * 1024)) # 50MB compressed limit

if [ "$LAYER_SIZE_BYTES" -gt "$MAX_SIZE" ]; then
    echo -e "${RED}WARNING: Layer size exceeds 50MB compressed limit!${NC}"
    echo -e "${RED}Current size: $(($LAYER_SIZE_BYTES / 1024 / 1024))MB${NC}"
    exit 1
else
    echo -e "${GREEN}Layer size is within AWS limits ($(($LAYER_SIZE_BYTES / 1024 / 1024))MB / 50MB)${NC}"
fi

echo -e "${GREEN}Build complete!${NC}"