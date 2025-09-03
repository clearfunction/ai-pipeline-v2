#!/bin/bash

# Helper script to build the Claude Code Node.js layer
# This script should be run before deploying the infrastructure

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAYER_DIR="$PROJECT_ROOT/layers/claude-code-nodejs"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Claude Code Layer Build Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if layer directory exists
if [ ! -d "$LAYER_DIR" ]; then
    echo -e "${RED}Error: Layer directory not found at $LAYER_DIR${NC}"
    exit 1
fi

# Navigate to layer directory
cd "$LAYER_DIR"

# Check if build script exists
if [ ! -f "build-layer.sh" ]; then
    echo -e "${RED}Error: build-layer.sh not found in $LAYER_DIR${NC}"
    exit 1
fi

# Run the build script
echo -e "${YELLOW}Building Claude Code layer...${NC}"
./build-layer.sh

# Check if build was successful
if [ -f "claude-code-layer.zip" ]; then
    echo -e "${GREEN}✓ Layer build successful!${NC}"
    echo -e "${GREEN}  Location: $LAYER_DIR/claude-code-layer.zip${NC}"
    
    # Display layer information
    LAYER_SIZE=$(du -h claude-code-layer.zip | cut -f1)
    echo -e "${BLUE}  Size: ${LAYER_SIZE}${NC}"
    
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "${YELLOW}1. Deploy infrastructure with CDK:${NC}"
    echo "   cd $PROJECT_ROOT/infrastructure"
    echo "   npm run deploy-dev"
    echo ""
    echo -e "${YELLOW}2. Test the Lambda function:${NC}"
    echo "   $PROJECT_ROOT/scripts/test-lambda.sh story-executor dev"
else
    echo -e "${RED}✗ Layer build failed!${NC}"
    echo -e "${RED}  Check the build output above for errors${NC}"
    exit 1
fi