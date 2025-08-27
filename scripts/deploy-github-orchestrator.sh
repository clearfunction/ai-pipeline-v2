#!/usr/bin/env bash

# Special deployment script for GitHub Orchestrator Lambda
# This Lambda requires bundled dependencies and should not use the standard deploy-single.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_NAME="github-orchestrator"
FUNCTION_NAME="ai-pipeline-v2-github-orchestrator-$ENVIRONMENT"
LAMBDA_DIR="$PROJECT_ROOT/lambdas/story-execution/github-orchestrator"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}GitHub Orchestrator Deployment Script${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: This Lambda uses CDK bundling!${NC}"
echo -e "${YELLOW}   For infrastructure changes, use: cd infrastructure && npm run deploy-${ENVIRONMENT}${NC}"
echo -e "${YELLOW}   This script is for emergency code-only updates.${NC}"
echo ""

# Check if lambda directory exists
if [ ! -d "$LAMBDA_DIR" ]; then
    echo -e "${RED}Error: Lambda directory not found: $LAMBDA_DIR${NC}"
    exit 1
fi

# Auto-proceed without confirmation (removed for faster deployments)
echo -e "${YELLOW}Deploying GitHub Orchestrator with bundled dependencies.${NC}"
echo -e "${YELLOW}Note: This will override any CDK deployment.${NC}"

echo -e "${GREEN}Deploying GitHub Orchestrator Lambda${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Function: $FUNCTION_NAME${NC}"
echo ""

# Create temporary directory for deployment package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"

echo -e "${YELLOW}Creating deployment package with dependencies...${NC}"

# Create package structure
mkdir -p "$PACKAGE_DIR"

# Copy lambda function code
cp -r "$LAMBDA_DIR"/* "$PACKAGE_DIR/"

# Install dependencies
cd "$PACKAGE_DIR"
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt -t . --platform manylinux2014_x86_64 --only-binary=:all: --quiet
    
    # Clean up
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    rm -f requirements.txt
else
    echo -e "${RED}Warning: No requirements.txt found${NC}"
fi

# Create deployment zip
echo -e "${YELLOW}Creating zip package...${NC}"
PACKAGE_ZIP="$TEMP_DIR/${FUNCTION_NAME}.zip"
zip -r "$PACKAGE_ZIP" . -q -x "*.pyc" "__pycache__/*" "*.pyo" ".git/*" ".gitignore" "tests/__pycache__/*"

# Show package size
PACKAGE_SIZE=$(du -h "$PACKAGE_ZIP" | cut -f1)
echo -e "${GREEN}Package size: $PACKAGE_SIZE${NC}"

# Check if function exists
echo -e "${YELLOW}Checking Lambda function status...${NC}"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo -e "${GREEN}Lambda function exists. Updating...${NC}"
    
    # Wait for function to be ready
    STATUS=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null)
    if [ "$STATUS" = "InProgress" ]; then
        echo -e "${YELLOW}Waiting for previous update to complete...${NC}"
        aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
    fi
    
    # Update function code
    echo -e "${YELLOW}Updating function code...${NC}"
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$PACKAGE_ZIP" \
        --region "$AWS_REGION" > /dev/null
    
    echo -e "${GREEN}Function code updated successfully${NC}"
    
    # Wait for update to complete
    echo -e "${YELLOW}Waiting for deployment to complete...${NC}"
    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
    
else
    echo -e "${RED}Lambda function does not exist!${NC}"
    echo -e "${YELLOW}Please deploy the infrastructure first:${NC}"
    echo -e "${YELLOW}  cd $PROJECT_ROOT/infrastructure${NC}"
    echo -e "${YELLOW}  npm run deploy-${ENVIRONMENT}${NC}"
    exit 1
fi

# Test the function
echo -e "${YELLOW}Testing function...${NC}"
TEST_PAYLOAD='{"test": true}'
TEST_RESPONSE="$TEMP_DIR/test-response.json"

if aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --cli-binary-format raw-in-base64-out \
    --payload "$TEST_PAYLOAD" \
    "$TEST_RESPONSE" \
    --region "$AWS_REGION" > /dev/null 2>&1; then
    
    # Check for errors in response
    if grep -q "errorMessage" "$TEST_RESPONSE"; then
        ERROR_MSG=$(cat "$TEST_RESPONSE" | jq -r '.errorMessage // "Unknown error"' 2>/dev/null || echo "Unable to parse error")
        if [[ "$ERROR_MSG" == *"Missing required data"* ]] || [[ "$ERROR_MSG" == *"GitHub orchestration failed"* ]]; then
            echo -e "${GREEN}✅ Function deployed successfully (validation error expected with test payload)${NC}"
        elif [[ "$ERROR_MSG" == *"No module named"* ]]; then
            echo -e "${RED}❌ Import error detected: $ERROR_MSG${NC}"
            echo -e "${RED}   Deployment may have failed!${NC}"
        else
            echo -e "${YELLOW}⚠️  Function returned error: $ERROR_MSG${NC}"
        fi
    else
        echo -e "${GREEN}✅ Function test successful${NC}"
    fi
else
    echo -e "${RED}Function test failed${NC}"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GitHub Orchestrator deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Monitor logs:${NC}"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"
echo ""
echo -e "${BLUE}Note: For infrastructure changes, always use CDK:${NC}"
echo "  cd $PROJECT_ROOT/infrastructure && npm run deploy-$ENVIRONMENT"