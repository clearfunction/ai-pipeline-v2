#!/bin/bash

# Test individual Lambda function
# Usage: ./scripts/test-lambda.sh <lambda-name> [environment] [test-file]

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
TEST_FILE=$3
AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    echo -e "${YELLOW}Usage: $0 <lambda-name> [environment] [test-file]${NC}"
    echo ""
    echo "Examples:"
    echo "  $0 document-processor dev"
    echo "  $0 requirements-synthesizer prod test-data/sample-documents.json"
    echo ""
    echo "Available lambda functions:"
    echo "  Core: document-processor, requirements-synthesizer, architecture-planner"
    echo "  Story: story-manager, component-generator, integration-validator, build-orchestrator"
    echo "  Review: review-coordinator, claude-agent-dispatcher, quality-enforcer"
    exit 1
}

# Validate inputs
if [ -z "$LAMBDA_NAME" ]; then
    echo -e "${RED}Error: Lambda name is required${NC}"
    usage
fi

FUNCTION_NAME="ai-pipeline-v2-$LAMBDA_NAME-$ENVIRONMENT"

echo -e "${BLUE}Testing Lambda Function: $FUNCTION_NAME${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Region: $AWS_REGION${NC}"
echo ""

# Check if function exists
if ! aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${RED}Error: Function $FUNCTION_NAME does not exist${NC}"
    echo -e "${YELLOW}Available functions:${NC}"
    aws lambda list-functions --region "$AWS_REGION" --query "Functions[?starts_with(FunctionName, 'ai-pipeline-v2-')].FunctionName" --output table
    exit 1
fi

# Determine test payload
TEST_PAYLOAD="{\"test\": true, \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

if [ -n "$TEST_FILE" ]; then
    if [ -f "$TEST_FILE" ]; then
        echo -e "${YELLOW}Using test file: $TEST_FILE${NC}"
        TEST_PAYLOAD=$(cat "$TEST_FILE")
    elif [ -f "$PROJECT_ROOT/$TEST_FILE" ]; then
        echo -e "${YELLOW}Using test file: $PROJECT_ROOT/$TEST_FILE${NC}"
        TEST_PAYLOAD=$(cat "$PROJECT_ROOT/$TEST_FILE")
    else
        echo -e "${RED}Error: Test file not found: $TEST_FILE${NC}"
        exit 1
    fi
else
    # Generate lambda-specific test payload
    case "$LAMBDA_NAME" in
        "document-processor")
            TEST_PAYLOAD='{
                "input_sources": [
                    {
                        "type": "text",
                        "path": "/tmp/test-document.txt",
                        "content": "This is a test document for processing."
                    }
                ],
                "project_id": "test-project-123"
            }'
            ;;
        "requirements-synthesizer")
            TEST_PAYLOAD='{
                "data": {
                    "pipeline_context": {
                        "execution_id": "test-exec-123",
                        "project_id": "test-project-123",
                        "stage": "document_processing",
                        "input_documents": [
                            {
                                "document_id": "test-doc-1",
                                "document_type": "text",
                                "source_path": "/tmp/test.txt",
                                "processed_at": "2024-01-01T00:00:00Z",
                                "version_hash": "abc123",
                                "size_bytes": 100
                            }
                        ]
                    }
                }
            }'
            ;;
        "architecture-planner")
            TEST_PAYLOAD='{
                "data": {
                    "pipeline_context": {
                        "execution_id": "test-exec-123",
                        "project_id": "test-project-123",
                        "stage": "requirements_synthesis"
                    },
                    "user_stories": [
                        {
                            "story_id": "story-1",
                            "title": "User Login",
                            "description": "As a user, I want to log in so that I can access my account",
                            "acceptance_criteria": ["User can enter credentials", "Invalid login shows error"],
                            "priority": 1,
                            "estimated_effort": 5,
                            "dependencies": [],
                            "status": "pending",
                            "assigned_components": []
                        }
                    ]
                }
            }'
            ;;
        *)
            echo -e "${YELLOW}Using generic test payload${NC}"
            ;;
    esac
fi

echo -e "${YELLOW}Test payload preview:${NC}"
echo "$TEST_PAYLOAD" | jq . 2>/dev/null || echo "$TEST_PAYLOAD"
echo ""

# Create temporary files
TEMP_DIR=$(mktemp -d)
RESPONSE_FILE="$TEMP_DIR/response.json"
LOG_FILE="$TEMP_DIR/logs.txt"

echo -e "${YELLOW}Invoking function...${NC}"

# Invoke function
START_TIME=$(date +%s)
INVOKE_RESULT=$(aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload "$TEST_PAYLOAD" \
    --region "$AWS_REGION" \
    --log-type Tail \
    "$RESPONSE_FILE" 2>&1)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${YELLOW}Execution completed in ${DURATION}s${NC}"
echo ""

# Check invocation result
if echo "$INVOKE_RESULT" | grep -q "StatusCode.*200"; then
    echo -e "${GREEN}✓ Function invocation successful${NC}"
    
    # Display response
    echo -e "${YELLOW}Response:${NC}"
    if command -v jq > /dev/null; then
        cat "$RESPONSE_FILE" | jq .
    else
        cat "$RESPONSE_FILE"
    fi
    
    # Extract and display logs
    if echo "$INVOKE_RESULT" | grep -q "LogResult"; then
        echo ""
        echo -e "${YELLOW}Execution logs:${NC}"
        echo "$INVOKE_RESULT" | grep "LogResult" | sed 's/.*"LogResult": "//' | sed 's/".*//' | base64 -d
    fi
    
else
    echo -e "${RED}✗ Function invocation failed${NC}"
    echo "$INVOKE_RESULT"
    
    if [ -f "$RESPONSE_FILE" ]; then
        echo ""
        echo -e "${YELLOW}Error response:${NC}"
        cat "$RESPONSE_FILE"
    fi
    
    # Get recent logs
    echo ""
    echo -e "${YELLOW}Recent CloudWatch logs:${NC}"
    aws logs filter-log-events \
        --log-group-name "/aws/lambda/$FUNCTION_NAME" \
        --start-time $(($(date +%s) - 300))000 \
        --region "$AWS_REGION" \
        --query 'events[*].message' \
        --output text | tail -20
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo -e "${BLUE}Test completed for $FUNCTION_NAME${NC}"
echo -e "${YELLOW}To view live logs:${NC}"
echo "aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"