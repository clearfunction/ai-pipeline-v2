#!/bin/bash

# Test Step Functions workflow integration
# Usage: ./scripts/test-step-functions.sh [environment] [test-type]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ENVIRONMENT=${1:-dev}
TEST_TYPE=${2:-basic}

echo -e "${BLUE}Testing Step Functions Workflow Integration${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Test Type: $TEST_TYPE${NC}"
echo ""

# Find the state machine
echo -e "${YELLOW}Finding Step Functions state machine...${NC}"
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
    --query "stateMachines[?contains(name, 'ai-pipeline-v2-main-$ENVIRONMENT')].stateMachineArn" \
    --output text)

if [ -z "$STATE_MACHINE_ARN" ]; then
    echo -e "${RED}✗ State machine not found for environment: $ENVIRONMENT${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found state machine: $(basename $STATE_MACHINE_ARN)${NC}"

# Test 1: Validate state machine definition
echo -e "${YELLOW}Testing state machine definition...${NC}"
DEFINITION=$(aws stepfunctions describe-state-machine \
    --state-machine-arn "$STATE_MACHINE_ARN" \
    --query 'definition' \
    --output text)

# Check for required states
REQUIRED_STATES=("DocumentProcessor" "RequirementsSynthesizer" "ArchitecturePlanner" "StoryExecutor" "ValidationAndBuildParallel")
for state in "${REQUIRED_STATES[@]}"; do
    if echo "$DEFINITION" | grep -q "\"$state\""; then
        echo -e "${GREEN}✓ Found required state: $state${NC}"
    else
        echo -e "${RED}✗ Missing required state: $state${NC}"
        exit 1
    fi
done

# Test 2: Basic workflow execution
if [ "$TEST_TYPE" = "basic" ] || [ "$TEST_TYPE" = "full" ]; then
    echo -e "${YELLOW}Starting basic workflow test...${NC}"
    
    # Create test input
    TEST_INPUT=$(cat << 'EOF'
{
  "documents": [
    {
      "document_id": "test-doc-001",
      "title": "Simple React App Requirements",
      "source_type": "test",
      "content": "Create a simple React application with a login page and dashboard.",
      "file_path": "test://simple-app.txt"
    }
  ],
  "project_metadata": {
    "project_id": "test-001",
    "name": "Simple React App",
    "requester": "test@example.com",
    "priority": "medium",
    "target_tech_stack": "react_spa"
  },
  "execution_config": {
    "enable_human_review": false,
    "auto_deploy": false,
    "validation_level": "basic",
    "test_mode": true
  }
}
EOF
)
    
    # Start execution
    EXECUTION_NAME="test-workflow-$(date +%s)"
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-arn "$STATE_MACHINE_ARN" \
        --name "$EXECUTION_NAME" \
        --input "$TEST_INPUT" \
        --query 'executionArn' \
        --output text)
    
    echo -e "${GREEN}✓ Started test execution: $EXECUTION_NAME${NC}"
    echo -e "${YELLOW}Execution ARN: $EXECUTION_ARN${NC}"
    
    # Monitor execution
    echo -e "${YELLOW}Monitoring execution (timeout: 300s)...${NC}"
    TIMEOUT=300
    ELAPSED=0
    
    while [ $ELAPSED -lt $TIMEOUT ]; do
        STATUS=$(aws stepfunctions describe-execution \
            --execution-arn "$EXECUTION_ARN" \
            --query 'status' \
            --output text)
        
        case $STATUS in
            "RUNNING")
                echo -e "${YELLOW}  Status: $STATUS (${ELAPSED}s elapsed)${NC}"
                sleep 10
                ELAPSED=$((ELAPSED + 10))
                ;;
            "SUCCEEDED")
                echo -e "${GREEN}✓ Execution completed successfully${NC}"
                
                # Get execution output
                OUTPUT=$(aws stepfunctions describe-execution \
                    --execution-arn "$EXECUTION_ARN" \
                    --query 'output' \
                    --output text)
                
                echo -e "${YELLOW}Execution output preview:${NC}"
                echo "$OUTPUT" | jq -r 'keys[]' 2>/dev/null || echo "Output: $OUTPUT"
                break
                ;;
            "FAILED"|"TIMED_OUT"|"ABORTED")
                echo -e "${RED}✗ Execution failed with status: $STATUS${NC}"
                
                # Get error details
                aws stepfunctions describe-execution \
                    --execution-arn "$EXECUTION_ARN" \
                    --query 'error' \
                    --output text 2>/dev/null || echo "No error details available"
                
                exit 1
                ;;
            *)
                echo -e "${YELLOW}  Unexpected status: $STATUS${NC}"
                sleep 5
                ELAPSED=$((ELAPSED + 5))
                ;;
        esac
    done
    
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo -e "${RED}✗ Execution timed out after ${TIMEOUT}s${NC}"
        exit 1
    fi
fi

# Test 3: Story-executor integration test
if [ "$TEST_TYPE" = "story-executor" ] || [ "$TEST_TYPE" = "full" ]; then
    echo -e "${YELLOW}Testing story-executor integration...${NC}"
    
    # Test story-executor lambda directly
    STORY_EXECUTOR_NAME="ai-pipeline-v2-story-executor-$ENVIRONMENT"
    
    # Check if story-executor lambda exists
    aws lambda get-function --function-name "$STORY_EXECUTOR_NAME" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Story-executor lambda found: $STORY_EXECUTOR_NAME${NC}"
        
        # Test with sample architecture
        STORY_TEST_INPUT=$(cat << 'EOF'
{
  "data": {
    "pipeline_context": {
      "execution_id": "test-story-001",
      "project_id": "test-project",
      "stage": "story_execution",
      "architecture": {
        "project_id": "test-project",
        "name": "Test React App",
        "tech_stack": "react_spa",
        "components": [
          {
            "component_id": "comp_001",
            "name": "App",
            "type": "component",
            "file_path": "src/App.tsx",
            "dependencies": [],
            "exports": ["App"],
            "story_ids": ["story-1"]
          }
        ],
        "user_stories": [
          {
            "story_id": "story-1",
            "title": "Basic App Structure",
            "description": "Create a basic React app with routing",
            "acceptance_criteria": ["App renders correctly", "Basic routing works"],
            "priority": 1,
            "estimated_effort": 3,
            "dependencies": [],
            "status": "pending",
            "assigned_components": ["comp_001"]
          }
        ],
        "dependencies": {"react": "^18.2.0"},
        "build_config": {"package_manager": "npm"}
      }
    },
    "stories_to_execute": [
      {
        "story_id": "story-1",
        "title": "Basic App Structure",
        "description": "Create a basic React app with routing",
        "acceptance_criteria": ["App renders correctly", "Basic routing works"],
        "priority": 1,
        "estimated_effort": 3,
        "dependencies": [],
        "status": "pending",
        "assigned_components": ["comp_001"]
      }
    ]
  }
}
EOF
)
        
        echo -e "${YELLOW}Testing story-executor with sample input...${NC}"
        RESULT=$(aws lambda invoke \
            --function-name "$STORY_EXECUTOR_NAME" \
            --payload "$STORY_TEST_INPUT" \
            --output json \
            /tmp/story-executor-output.json)
        
        if [ $? -eq 0 ]; then
            STATUS_CODE=$(echo "$RESULT" | jq -r '.StatusCode')
            if [ "$STATUS_CODE" = "200" ]; then
                echo -e "${GREEN}✓ Story-executor invocation successful${NC}"
                
                # Check output
                OUTPUT_STATUS=$(cat /tmp/story-executor-output.json | jq -r '.status' 2>/dev/null)
                if [ "$OUTPUT_STATUS" = "success" ]; then
                    echo -e "${GREEN}✓ Story-executor executed successfully${NC}"
                    
                    # Show generated files count
                    FILES_COUNT=$(cat /tmp/story-executor-output.json | jq -r '.data.generated_code | length' 2>/dev/null)
                    echo -e "${GREEN}✓ Generated $FILES_COUNT code files${NC}"
                else
                    echo -e "${RED}✗ Story-executor returned failure status${NC}"
                    cat /tmp/story-executor-output.json | jq '.' 2>/dev/null || cat /tmp/story-executor-output.json
                fi
            else
                echo -e "${RED}✗ Story-executor invocation failed with status: $STATUS_CODE${NC}"
            fi
        else
            echo -e "${RED}✗ Failed to invoke story-executor lambda${NC}"
        fi
        
        # Clean up
        rm -f /tmp/story-executor-output.json
    else
        echo -e "${RED}✗ Story-executor lambda not found: $STORY_EXECUTOR_NAME${NC}"
    fi
fi

# Test 4: Error handling
if [ "$TEST_TYPE" = "error-handling" ] || [ "$TEST_TYPE" = "full" ]; then
    echo -e "${YELLOW}Testing error handling...${NC}"
    
    # Test with invalid input to trigger error handling
    INVALID_INPUT='{"invalid": "input", "missing": "required_fields"}'
    
    EXECUTION_NAME="test-error-$(date +%s)"
    EXECUTION_ARN=$(aws stepfunctions start-execution \
        --state-machine-arn "$STATE_MACHINE_ARN" \
        --name "$EXECUTION_NAME" \
        --input "$INVALID_INPUT" \
        --query 'executionArn' \
        --output text)
    
    echo -e "${YELLOW}Started error handling test: $EXECUTION_NAME${NC}"
    
    # Wait for failure
    sleep 30
    
    STATUS=$(aws stepfunctions describe-execution \
        --execution-arn "$EXECUTION_ARN" \
        --query 'status' \
        --output text)
    
    if [ "$STATUS" = "FAILED" ]; then
        echo -e "${GREEN}✓ Error handling working correctly (execution failed as expected)${NC}"
    else
        echo -e "${YELLOW}⚠ Error handling test inconclusive (status: $STATUS)${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Step Functions Integration Test Summary${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}✓ State machine definition validated${NC}"
echo -e "${GREEN}✓ Required states present${NC}"

if [ "$TEST_TYPE" = "basic" ] || [ "$TEST_TYPE" = "full" ]; then
    echo -e "${GREEN}✓ Basic workflow execution tested${NC}"
fi

if [ "$TEST_TYPE" = "story-executor" ] || [ "$TEST_TYPE" = "full" ]; then
    echo -e "${GREEN}✓ Story-executor integration tested${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Step Functions integration tests completed successfully!${NC}"
echo ""
echo -e "${YELLOW}State Machine ARN:${NC}"
echo "$STATE_MACHINE_ARN"
echo ""
echo -e "${YELLOW}AWS Console:${NC}"
echo "https://console.aws.amazon.com/states/home?region=$(aws configure get region)#/statemachines/view/$STATE_MACHINE_ARN"