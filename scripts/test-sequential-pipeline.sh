#!/bin/bash

# Test Sequential Pipeline - End-to-end test of the refactored pipeline
# This script tests the sequential story processing with validation after each story

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
PROJECT_ID="test-sequential-$(date +%s)"
REGION="${AWS_REGION:-us-east-1}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Testing Sequential Pipeline v2${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Function to check Lambda function exists
check_lambda() {
    local function_name=$1
    echo -n "Checking Lambda $function_name... "
    if aws lambda get-function --function-name "$function_name" --region "$REGION" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Function to test individual Lambda
test_lambda() {
    local function_name=$1
    local payload=$2
    local expected_status=${3:-"success"}
    
    echo -e "\n${YELLOW}Testing $function_name...${NC}"
    
    # Invoke Lambda
    response=$(aws lambda invoke \
        --function-name "$function_name" \
        --payload "$payload" \
        --region "$REGION" \
        --cli-binary-format raw-in-base64-out \
        /tmp/lambda-response.json 2>&1)
    
    # Check response
    if [ -f /tmp/lambda-response.json ]; then
        status=$(jq -r '.status // "unknown"' /tmp/lambda-response.json)
        if [ "$status" = "$expected_status" ]; then
            echo -e "${GREEN}✓ Lambda returned status: $status${NC}"
            return 0
        else
            echo -e "${RED}✗ Lambda returned status: $status (expected: $expected_status)${NC}"
            cat /tmp/lambda-response.json
            return 1
        fi
    else
        echo -e "${RED}✗ No response from Lambda${NC}"
        return 1
    fi
}

# Check all required Lambdas exist
echo -e "\n${YELLOW}Checking Lambda Functions...${NC}"
check_lambda "ai-pipeline-v2-document-processor-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-requirements-synthesizer-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-architecture-planner-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-story-executor-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-story-validator-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-build-orchestrator-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-integration-validator-$ENVIRONMENT"
check_lambda "ai-pipeline-v2-github-orchestrator-$ENVIRONMENT"

# Create test data
echo -e "\n${YELLOW}Creating test data...${NC}"

# Create test document
cat > /tmp/test-document.json <<EOF
{
    "document_id": "test-doc-001",
    "content": "Build a simple todo application with React. Users should be able to add, edit, delete, and mark todos as complete. The app should have a clean, modern UI.",
    "project_metadata": {
        "project_name": "$PROJECT_ID",
        "description": "Test sequential pipeline with todo app"
    }
}
EOF

# Upload test document to S3
RAW_BUCKET="ai-pipeline-v2-raw-008537862626-$REGION"
echo "Uploading test document to S3..."
aws s3 cp /tmp/test-document.json "s3://$RAW_BUCKET/documents/$PROJECT_ID/test-document.json"

# Test 1: Document Processor
echo -e "\n${YELLOW}Test 1: Document Processor${NC}"
test_lambda "ai-pipeline-v2-document-processor-$ENVIRONMENT" '{
    "document_key": "documents/'$PROJECT_ID'/test-document.json",
    "bucket_name": "'$RAW_BUCKET'"
}'

# Test 2: Sequential Story Executor (Mock)
echo -e "\n${YELLOW}Test 2: Story Executor with Sequential Mode${NC}"

# Create test payload with multiple stories
cat > /tmp/story-executor-payload.json <<EOF
{
    "operation_mode": "sequential_execution",
    "data": {
        "user_stories": [
            {
                "story_id": "story-001",
                "title": "Create Todo List UI",
                "description": "Build the main todo list interface",
                "acceptance_criteria": [
                    "Display list of todos",
                    "Show todo status (complete/incomplete)",
                    "Responsive design"
                ]
            },
            {
                "story_id": "story-002",
                "title": "Add Todo Functionality",
                "description": "Implement ability to add new todos",
                "acceptance_criteria": [
                    "Input field for new todo",
                    "Add button",
                    "Validation for empty input"
                ]
            },
            {
                "story_id": "story-003",
                "title": "Edit and Delete Todos",
                "description": "Allow users to edit and delete todos",
                "acceptance_criteria": [
                    "Edit button for each todo",
                    "Delete button with confirmation",
                    "Update UI after changes"
                ]
            }
        ],
        "architecture": {
            "project_id": "$PROJECT_ID",
            "tech_stack": "react_spa",
            "framework": "React",
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "typescript": "^5.0.0"
            }
        },
        "pipeline_context": {
            "project_id": "$PROJECT_ID",
            "execution_id": "test-exec-$(date +%s)"
        }
    }
}
EOF

# Test Story Executor
test_lambda "ai-pipeline-v2-story-executor-$ENVIRONMENT" "$(cat /tmp/story-executor-payload.json)"

# Test 3: Story Validator
echo -e "\n${YELLOW}Test 3: Story Validator${NC}"

cat > /tmp/validator-payload.json <<EOF
{
    "story_files": [
        {
            "file_path": "src/components/TodoList.tsx",
            "content": "import React from 'react';\n\nexport const TodoList = () => {\n  return <div>Todo List</div>;\n};",
            "story_id": "story-001"
        }
    ],
    "existing_files": [],
    "story_metadata": {
        "story_id": "story-001",
        "title": "Create Todo List UI",
        "index": 0,
        "is_first_story": true,
        "is_last_story": false
    },
    "architecture": {
        "tech_stack": "react_spa"
    },
    "project_context": {
        "project_id": "$PROJECT_ID"
    }
}
EOF

test_lambda "ai-pipeline-v2-story-validator-$ENVIRONMENT" "$(cat /tmp/validator-payload.json)"

# Test 4: Build Orchestrator
echo -e "\n${YELLOW}Test 4: Build Orchestrator${NC}"

cat > /tmp/build-payload.json <<EOF
{
    "story_files": [
        {
            "file_path": "package.json",
            "content": "{\n  \"name\": \"todo-app\",\n  \"version\": \"1.0.0\",\n  \"scripts\": {\n    \"build\": \"echo 'build'\",\n    \"test\": \"echo 'test'\"\n  }\n}"
        }
    ],
    "existing_files": [],
    "tech_stack": "react_spa",
    "story_metadata": {
        "story_id": "story-001",
        "title": "Create Todo List UI"
    }
}
EOF

test_lambda "ai-pipeline-v2-build-orchestrator-$ENVIRONMENT" "$(cat /tmp/build-payload.json)"

# Test 5: GitHub Orchestrator (Setup Mode)
echo -e "\n${YELLOW}Test 5: GitHub Orchestrator - Setup Mode${NC}"

cat > /tmp/github-setup-payload.json <<EOF
{
    "operation_mode": "setup_deployment",
    "project_id": "$PROJECT_ID",
    "tech_stack": "react_spa",
    "architecture": {
        "project_id": "$PROJECT_ID",
        "tech_stack": "react_spa"
    }
}
EOF

# Note: This will fail if GitHub token is not configured
echo "Note: GitHub operations require valid GitHub token in Secrets Manager"

# Test 6: Integration Validator (Incremental Mode)
echo -e "\n${YELLOW}Test 6: Integration Validator - Incremental Mode${NC}"

cat > /tmp/integration-payload.json <<EOF
{
    "story_files": [
        {
            "file_path": "src/components/TodoItem.tsx",
            "content": "import React from 'react';\n\nexport const TodoItem = () => {\n  return <div>Todo Item</div>;\n};"
        }
    ],
    "existing_files": [
        {
            "file_path": "src/components/TodoList.tsx",
            "content": "import React from 'react';\n\nexport const TodoList = () => {\n  return <div>Todo List</div>;\n};"
        }
    ],
    "story_metadata": {
        "story_id": "story-002",
        "title": "Add Todo Functionality"
    },
    "architecture": {
        "tech_stack": "react_spa"
    },
    "project_context": {
        "project_id": "$PROJECT_ID"
    }
}
EOF

test_lambda "ai-pipeline-v2-integration-validator-$ENVIRONMENT" "$(cat /tmp/integration-payload.json)"

# Test Step Functions Workflow
echo -e "\n${YELLOW}Testing Step Functions Workflow...${NC}"

# Check if state machine exists
STATE_MACHINE_ARN="arn:aws:states:$REGION:$(aws sts get-caller-identity --query Account --output text):stateMachine:ai-pipeline-v2-sequential-$ENVIRONMENT"

if aws stepfunctions describe-state-machine --state-machine-arn "$STATE_MACHINE_ARN" &>/dev/null; then
    echo -e "${GREEN}✓ State machine exists${NC}"
    
    # Start execution
    echo "Starting state machine execution..."
    EXECUTION_NAME="test-execution-$(date +%s)"
    
    cat > /tmp/state-machine-input.json <<EOF
{
    "document_key": "documents/$PROJECT_ID/test-document.json",
    "bucket_name": "$RAW_BUCKET",
    "project_metadata": {
        "project_name": "$PROJECT_ID",
        "description": "Sequential pipeline test"
    }
}
EOF
    
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-arn "$STATE_MACHINE_ARN" \
        --name "$EXECUTION_NAME" \
        --input file:///tmp/state-machine-input.json \
        --query 'executionArn' \
        --output text)
    
    echo "Execution started: $EXECUTION_ARN"
    echo "Waiting for execution to complete (timeout: 5 minutes)..."
    
    # Wait for execution to complete
    TIMEOUT=300
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        STATUS=$(aws stepfunctions describe-execution \
            --execution-arn "$EXECUTION_ARN" \
            --query 'status' \
            --output text)
        
        if [ "$STATUS" = "SUCCEEDED" ]; then
            echo -e "${GREEN}✓ State machine execution succeeded${NC}"
            break
        elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "TIMED_OUT" ] || [ "$STATUS" = "ABORTED" ]; then
            echo -e "${RED}✗ State machine execution failed with status: $STATUS${NC}"
            
            # Get error details
            aws stepfunctions describe-execution \
                --execution-arn "$EXECUTION_ARN" \
                --query 'error' \
                --output json
            break
        fi
        
        echo -n "."
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    done
    
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo -e "${YELLOW}⚠ Execution timed out${NC}"
    fi
else
    echo -e "${YELLOW}⚠ State machine not found - skipping workflow test${NC}"
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo "✓ Lambda functions validated"
echo "✓ Sequential processing tested"
echo "✓ Story validation tested"
echo "✓ Build orchestration tested"
echo "✓ Integration validation tested"

# Cleanup
echo -e "\n${YELLOW}Cleaning up test files...${NC}"
rm -f /tmp/test-document.json
rm -f /tmp/story-executor-payload.json
rm -f /tmp/validator-payload.json
rm -f /tmp/build-payload.json
rm -f /tmp/github-setup-payload.json
rm -f /tmp/integration-payload.json
rm -f /tmp/state-machine-input.json
rm -f /tmp/lambda-response.json

echo -e "\n${GREEN}Sequential pipeline test completed!${NC}"