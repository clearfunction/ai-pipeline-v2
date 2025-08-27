#!/bin/bash

# Deploy all Lambda functions
# Usage: ./scripts/deploy-all.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   AI Pipeline v2 - Full Deployment  ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo ""

# Core pipeline lambdas (sequential deployment)
CORE_LAMBDAS=(
    "document-processor"
    "requirements-synthesizer" 
    "architecture-planner"
)

# Story execution lambdas (GitHub Actions integration)
STORY_LAMBDAS=(
    "story-executor"
    "integration-validator"
    "github-orchestrator"
)

# Human review lambdas (GitHub PR workflow)
REVIEW_LAMBDAS=(
    "review-coordinator"
    "pr-status-checker"
)

deploy_lambda() {
    local lambda_name=$1
    local category=$2
    
    echo -e "${YELLOW}[$category] Deploying $lambda_name...${NC}"
    
    if "$SCRIPT_DIR/deploy-single.sh" "$lambda_name" "$ENVIRONMENT"; then
        echo -e "${GREEN}[$category] ✓ $lambda_name deployed successfully${NC}"
        return 0
    else
        echo -e "${RED}[$category] ✗ $lambda_name deployment failed${NC}"
        return 1
    fi
}

# Track deployment status
declare -a FAILED_DEPLOYMENTS=()
TOTAL_LAMBDAS=$((${#CORE_LAMBDAS[@]} + ${#STORY_LAMBDAS[@]} + ${#REVIEW_LAMBDAS[@]}))
DEPLOYED_COUNT=0

echo -e "${BLUE}Phase 1: Core Pipeline Lambdas${NC}"
echo "----------------------------------------"

for lambda in "${CORE_LAMBDAS[@]}"; do
    if deploy_lambda "$lambda" "CORE"; then
        ((DEPLOYED_COUNT++))
    else
        FAILED_DEPLOYMENTS+=("$lambda")
    fi
    echo ""
done

echo -e "${BLUE}Phase 2: Story Execution Lambdas (GitHub Actions Integration)${NC}"
echo "----------------------------------------"

# Deploy story lambdas sequentially for GitHub integration dependencies
for lambda in "${STORY_LAMBDAS[@]}"; do
    if deploy_lambda "$lambda" "STORY"; then
        ((DEPLOYED_COUNT++))
    else
        FAILED_DEPLOYMENTS+=("$lambda")
    fi
    echo ""
done

echo ""
echo -e "${BLUE}Phase 3: Human Review Lambdas (GitHub PR Workflow)${NC}"
echo "----------------------------------------"

for lambda in "${REVIEW_LAMBDAS[@]}"; do
    if deploy_lambda "$lambda" "REVIEW"; then
        ((DEPLOYED_COUNT++))
    else
        FAILED_DEPLOYMENTS+=("$lambda")
    fi
    echo ""
done

# Deployment summary
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}      Deployment Summary              ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Total Lambdas: $TOTAL_LAMBDAS${NC}"
echo -e "${GREEN}Successfully Deployed: $DEPLOYED_COUNT${NC}"
echo -e "${RED}Failed Deployments: ${#FAILED_DEPLOYMENTS[@]}${NC}"

if [ ${#FAILED_DEPLOYMENTS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed Lambda Functions:${NC}"
    for failed in "${FAILED_DEPLOYMENTS[@]}"; do
        echo -e "${RED}  - $failed${NC}"
    done
    echo ""
    echo -e "${YELLOW}To retry failed deployments:${NC}"
    for failed in "${FAILED_DEPLOYMENTS[@]}"; do
        echo "./scripts/deploy-single.sh $failed $ENVIRONMENT"
    done
    exit 1
else
    echo ""
    echo -e "${GREEN}🎉 All Lambda functions deployed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Deploy infrastructure: cd infrastructure && npm run deploy-$ENVIRONMENT"
    echo "2. Test the pipeline: ./scripts/test-lambda.sh story-executor $ENVIRONMENT test-data/end-to-end-test.json"
    echo "3. Monitor logs: aws logs tail /aws/lambda/ai-pipeline-v2-* --follow"
    echo "4. GitHub integration: Check generated repositories and deployment status"
fi

echo ""
echo -e "${BLUE}======================================${NC}"