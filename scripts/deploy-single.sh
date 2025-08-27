#!/usr/bin/env bash

# Deploy a single Lambda function
# Usage: ./scripts/deploy-single.sh <lambda-name> [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LAMBDA_NAME=$1
ENVIRONMENT=${2:-dev}
AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/scripts/lambda-deployment-config.json"

# Function to get lambda path
get_lambda_path() {
    case "$1" in
        "document-processor") echo "lambdas/core/document-processor" ;;
        "requirements-synthesizer") echo "lambdas/core/requirements-synthesizer" ;;
        "architecture-planner") echo "lambdas/core/architecture-planner" ;;
        "story-executor") echo "lambdas/core/story-executor" ;;
        "s3-trigger") echo "lambdas/core/s3-trigger" ;;
        "integration-validator") echo "lambdas/story-execution/integration-validator" ;;
        "github-orchestrator") echo "lambdas/story-execution/github-orchestrator" ;;
        "review-coordinator") echo "lambdas/human-review/review-coordinator" ;;
        "pr-status-checker") echo "lambdas/human-review/pr-status-checker" ;;
        *) echo "" ;;
    esac
}

usage() {
    echo -e "${YELLOW}Usage: $0 <lambda-name> [environment]${NC}"
    echo ""
    echo "Available lambda functions:"
    echo "  - document-processor"
    echo "  - requirements-synthesizer"
    echo "  - architecture-planner"
    echo "  - story-executor"
    echo "  - s3-trigger"
    echo "  - integration-validator"
    echo "  - github-orchestrator"
    echo "  - review-coordinator"
    echo "  - pr-status-checker"
    echo ""
    echo "Environments: dev, staging, prod (default: dev)"
    exit 1
}

# Validate inputs
if [ -z "$LAMBDA_NAME" ]; then
    echo -e "${RED}Error: Lambda name is required${NC}"
    usage
fi

# Check deployment configuration
if [ -f "$CONFIG_FILE" ]; then
    # Check if this Lambda is CDK-managed
    DEPLOYMENT_METHOD=$(jq -r ".lambdas[\"$LAMBDA_NAME\"].deployment_method // \"unknown\"" "$CONFIG_FILE")
    CDK_MANAGED=$(jq -r ".lambdas[\"$LAMBDA_NAME\"].cdk_managed // false" "$CONFIG_FILE")
    WARNING_MSG=$(jq -r ".lambdas[\"$LAMBDA_NAME\"].warning // \"\"" "$CONFIG_FILE")
    
    if [ "$DEPLOYMENT_METHOD" = "cdk_bundled" ] || [ "$CDK_MANAGED" = "true" ]; then
        echo -e "${RED}════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}ERROR: Cannot deploy $LAMBDA_NAME using deploy-single.sh${NC}"
        echo -e "${RED}════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}This Lambda is managed by CDK with bundled dependencies.${NC}"
        echo -e "${YELLOW}Using deploy-single.sh will break this Lambda!${NC}"
        echo ""
        if [ -n "$WARNING_MSG" ] && [ "$WARNING_MSG" != "null" ]; then
            echo -e "${BLUE}$WARNING_MSG${NC}"
        fi
        echo ""
        echo -e "${GREEN}To deploy this Lambda, use one of these methods:${NC}"
        echo -e "${GREEN}1. CDK deployment (recommended):${NC}"
        echo "   cd $PROJECT_ROOT/infrastructure"
        echo "   npm run deploy-$ENVIRONMENT"
        echo ""
        echo -e "${GREEN}2. Emergency code-only update:${NC}"
        echo "   $PROJECT_ROOT/scripts/deploy-github-orchestrator.sh $ENVIRONMENT"
        echo ""
        exit 1
    fi
fi

LAMBDA_PATH=$(get_lambda_path "$LAMBDA_NAME")
if [ -z "$LAMBDA_PATH" ]; then
    echo -e "${RED}Error: Unknown lambda function: $LAMBDA_NAME${NC}"
    usage
fi
LAMBDA_DIR="$PROJECT_ROOT/$LAMBDA_PATH"

# Special handling for PR Status Checker which was renamed in CDK to avoid conflicts
if [ "$LAMBDA_NAME" = "pr-status-checker" ]; then
    FUNCTION_NAME="ai-pipeline-v2-pr-status-checker-v2-$ENVIRONMENT"
else
    FUNCTION_NAME="ai-pipeline-v2-$LAMBDA_NAME-$ENVIRONMENT"
fi

echo -e "${GREEN}Deploying Lambda function: $FUNCTION_NAME${NC}"
echo -e "${YELLOW}Path: $LAMBDA_PATH${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"

# Show deployment method info if config exists
if [ -f "$CONFIG_FILE" ]; then
    DEPLOYMENT_METHOD=$(jq -r ".lambdas[\"$LAMBDA_NAME\"].deployment_method // \"unknown\"" "$CONFIG_FILE")
    USES_LAYERS=$(jq -r ".lambdas[\"$LAMBDA_NAME\"].uses_layers // false" "$CONFIG_FILE")
    DESCRIPTION=$(jq -r ".lambdas[\"$LAMBDA_NAME\"].description // \"\"" "$CONFIG_FILE")
    
    echo -e "${BLUE}Deployment Method: $DEPLOYMENT_METHOD${NC}"
    if [ "$USES_LAYERS" = "true" ]; then
        echo -e "${BLUE}Uses Shared Layers: Yes${NC}"
    fi
    if [ -n "$DESCRIPTION" ] && [ "$DESCRIPTION" != "null" ]; then
        echo -e "${BLUE}Info: $DESCRIPTION${NC}"
    fi
fi
echo ""

# Check if lambda directory exists
if [ ! -d "$LAMBDA_DIR" ]; then
    echo -e "${RED}Error: Lambda directory not found: $LAMBDA_DIR${NC}"
    exit 1
fi

# Create temporary deployment package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"

echo -e "${YELLOW}Creating deployment package...${NC}"

# Create package structure
mkdir -p "$PACKAGE_DIR"

# Copy lambda function code
cp -r "$LAMBDA_DIR"/* "$PACKAGE_DIR/"

# Determine if this Lambda uses shared layers (from CDK configuration)
# Lambdas that use shared layers should not bundle common dependencies
USES_LAYERS=false
if [ "$LAMBDA_NAME" = "review-coordinator" ] || [ "$LAMBDA_NAME" = "pr-status-checker" ]; then
    echo -e "${GREEN}This Lambda uses shared layers - will exclude layer dependencies${NC}"
    USES_LAYERS=true
fi

# GitHub Orchestrator has CDK bundling - skip dependency installation
if [ "$LAMBDA_NAME" = "github-orchestrator" ]; then
    echo -e "${GREEN}GitHub Orchestrator uses CDK bundling - creating simple package${NC}"
    cd "$PACKAGE_DIR"
    # Only package Python files, requirements.txt will be handled by CDK
    PACKAGE_ZIP="$TEMP_DIR/${FUNCTION_NAME}.zip"
    zip -r "$PACKAGE_ZIP" *.py tests/ 2>/dev/null || zip -r "$PACKAGE_ZIP" *.py 2>/dev/null
    echo -e "${YELLOW}Simple package created for CDK bundling${NC}"
elif [ "$USES_LAYERS" = true ] && [ -f "$PACKAGE_DIR/requirements.txt" ]; then
    # For lambdas using layers, only install dependencies NOT in the layer
    echo -e "${YELLOW}Lambda uses shared layers - filtering dependencies...${NC}"
    
    cd "$PACKAGE_DIR"
    
    # Create a filtered requirements file excluding layer dependencies
    # Layer dependencies: boto3, requests, urllib3, anthropic, pydantic
    grep -v -E '^(boto3|requests|urllib3|anthropic|pydantic|certifi|idna|charset[_-]normalizer)' requirements.txt > filtered_requirements.txt 2>/dev/null || true
    
    if [ -s filtered_requirements.txt ]; then
        echo -e "${YELLOW}Installing non-layer dependencies...${NC}"
        pip install -r filtered_requirements.txt -t . --no-deps --platform linux_x86_64 --only-binary=:all: || {
            echo -e "${YELLOW}Platform-specific install failed, trying regular install...${NC}"
            pip install -r filtered_requirements.txt -t .
        }
    else
        echo -e "${GREEN}No additional dependencies needed beyond layers${NC}"
    fi
    
    # Clean up
    rm -f filtered_requirements.txt requirements.txt
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    
    # Create deployment zip
    PACKAGE_ZIP="$TEMP_DIR/${FUNCTION_NAME}.zip"
    zip -r "$PACKAGE_ZIP" . > /dev/null
    echo -e "${YELLOW}Layer-aware package created${NC}"
elif [ -f "$PACKAGE_DIR/requirements.txt" ]; then
    # Standard lambda without layers - install all dependencies
    echo -e "${YELLOW}Installing Python dependencies locally...${NC}"
    
    cd "$PACKAGE_DIR"
    pip install -r requirements.txt -t . --no-deps --platform linux_x86_64 --only-binary=:all: || {
        echo -e "${YELLOW}Platform-specific install failed, trying regular install...${NC}"
        pip install -r requirements.txt -t .
    }
    
    # Remove unnecessary files to reduce package size
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    rm -f requirements.txt
    
    # Create deployment zip
    PACKAGE_ZIP="$TEMP_DIR/${FUNCTION_NAME}.zip"
    zip -r "$PACKAGE_ZIP" . > /dev/null
    echo -e "${YELLOW}Full package created${NC}"
else
    # No requirements.txt, create a simple zip
    echo -e "${YELLOW}No requirements.txt found, creating simple zip package...${NC}"
    PACKAGE_ZIP="$TEMP_DIR/${FUNCTION_NAME}.zip"
    cd "$PACKAGE_DIR"
    zip -r "$PACKAGE_ZIP" . > /dev/null
fi

echo -e "${YELLOW}Package size: $(du -h "$PACKAGE_ZIP" | cut -f1)${NC}"

# Function to wait for Lambda function to be available for updates (from v1)
wait_for_lambda_available() {
    local function_name=$1
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Checking if Lambda function '$function_name' is available for updates...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        local status=$(aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" --query 'Configuration.LastUpdateStatus' --output text 2>/dev/null)
        local state=$(aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" --query 'Configuration.State' --output text 2>/dev/null)
        
        if [ "$status" = "Successful" ] && [ "$state" = "Active" ]; then
            echo -e "${GREEN}Lambda function '$function_name' is available for updates${NC}"
            return 0
        elif [ "$status" = "InProgress" ] || [ "$state" = "Pending" ]; then
            echo -e "${YELLOW}Lambda function '$function_name' is currently updating (attempt $attempt/$max_attempts). Waiting 10 seconds...${NC}"
            sleep 10
            attempt=$((attempt + 1))
        else
            echo -e "${YELLOW}Lambda function '$function_name' status: $status, state: $state${NC}"
            sleep 5
            attempt=$((attempt + 1))
        fi
    done
    
    echo -e "${RED}ERROR: Lambda function '$function_name' did not become available after $max_attempts attempts${NC}"
    return 1
}

# Check if function exists
function_exists=false
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    function_exists=true
    echo -e "${GREEN}Lambda function '$FUNCTION_NAME' exists. Will update${NC}"
    
    # Wait for function to be available
    if ! wait_for_lambda_available "$FUNCTION_NAME"; then
        echo -e "${RED}Function is not available for updates${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Lambda function '$FUNCTION_NAME' does not exist${NC}"
    echo -e "${YELLOW}Please deploy the infrastructure first: cd infrastructure && npm run deploy${NC}"
    exit 1
fi

# Update function code
echo -e "${YELLOW}Updating function code...${NC}"
if aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$PACKAGE_ZIP" \
    --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${GREEN}Function code updated successfully${NC}"
else
    echo -e "${RED}Failed to update function code${NC}"
    exit 1
fi

# Wait for code update to complete
echo -e "${YELLOW}Waiting for code update to complete...${NC}"
aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION"

# Update function configuration
echo -e "${YELLOW}Updating function configuration...${NC}"
if aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 900 \
    --memory-size 1024 \
    --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${GREEN}Function configuration updated successfully${NC}"
else
    echo -e "${YELLOW}Function configuration update failed, but continuing...${NC}"
fi

# Wait for update to complete
echo -e "${YELLOW}Waiting for deployment to complete...${NC}"
aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION"

# Test function
echo -e "${YELLOW}Testing function...${NC}"
INVOKE_RESULT=$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload '{"test": true}' \
    --region "$AWS_REGION" \
    "$TEMP_DIR/response.json" 2>&1)

if echo "$INVOKE_RESULT" | grep -q "StatusCode.*200"; then
    echo -e "${GREEN}Function test successful${NC}"
else
    echo -e "${RED}Function test failed:${NC}"
    echo "$INVOKE_RESULT"
    cat "$TEMP_DIR/response.json" 2>/dev/null || true
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}Deployment completed for $FUNCTION_NAME${NC}"
echo -e "${YELLOW}You can monitor logs with:${NC}"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"