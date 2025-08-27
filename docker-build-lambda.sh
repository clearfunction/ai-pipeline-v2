#!/bin/bash
# Build Lambda deployment packages using Docker for proper Linux compatibility

set -e

LAMBDA_NAME=$1
ENVIRONMENT=${2:-dev}

if [ -z "$LAMBDA_NAME" ]; then
    echo "Usage: $0 <lambda-name> [environment]"
    exit 1
fi

# Get lambda path
get_lambda_path() {
    case "$1" in
        "document-processor") echo "lambdas/core/document-processor" ;;
        "requirements-synthesizer") echo "lambdas/core/requirements-synthesizer" ;;
        "architecture-planner") echo "lambdas/core/architecture-planner" ;;
        "story-executor") echo "lambdas/core/story-executor" ;;
        "integration-validator") echo "lambdas/story-execution/integration-validator" ;;
        "github-orchestrator") echo "lambdas/story-execution/github-orchestrator" ;;
        "review-coordinator") echo "lambdas/human-review/review-coordinator" ;;
        *) echo "" ;;
    esac
}

LAMBDA_PATH=$(get_lambda_path "$LAMBDA_NAME")
if [ -z "$LAMBDA_PATH" ]; then
    echo "Unknown lambda function: $LAMBDA_NAME"
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="$PROJECT_ROOT/$LAMBDA_PATH"
FUNCTION_NAME="ai-pipeline-v2-$LAMBDA_NAME-$ENVIRONMENT"

echo "Building Lambda package for $FUNCTION_NAME using Docker..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"

# Create the package directory structure
mkdir -p "$PACKAGE_DIR"

# Copy lambda function code
cp -r "$LAMBDA_DIR"/* "$PACKAGE_DIR/"

# Copy shared dependencies
if [ -d "$PROJECT_ROOT/shared" ]; then
    mkdir -p "$PACKAGE_DIR/shared"
    cp -r "$PROJECT_ROOT/shared"/* "$PACKAGE_DIR/shared/"
fi

# Create Dockerfile for building dependencies
cat > "$TEMP_DIR/Dockerfile" << 'EOF'
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum update -y && yum install -y gcc

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt -t /var/task/

# Copy the function code
COPY . /var/task/

# Set the working directory
WORKDIR /var/task
EOF

# Build the Docker image and extract the package
cd "$TEMP_DIR"
docker build -t lambda-build-$LAMBDA_NAME .

# Extract the built package
CONTAINER_ID=$(docker create lambda-build-$LAMBDA_NAME)
docker cp $CONTAINER_ID:/var/task "$TEMP_DIR/extracted"
docker rm $CONTAINER_ID

# Create deployment zip
cd "$TEMP_DIR/extracted"
zip -r "$TEMP_DIR/${FUNCTION_NAME}.zip" .

echo "Package created: $TEMP_DIR/${FUNCTION_NAME}.zip"
echo "Package size: $(du -h "$TEMP_DIR/${FUNCTION_NAME}.zip" | cut -f1)"

# Deploy using AWS CLI
echo "Updating Lambda function..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$TEMP_DIR/${FUNCTION_NAME}.zip" \
    --region us-east-1

echo "Deployment completed successfully!"

# Cleanup
rm -rf "$TEMP_DIR"