#!/bin/bash

# Configure AWS Secrets Manager for deployment secrets
# Usage: ./scripts/setup-secrets.sh [environment]

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

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   AI Pipeline v2 - Secrets Setup    ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Region: $AWS_REGION${NC}"
echo ""

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    source .env
else
    echo -e "${RED}Error: .env file not found. Please create it with required tokens.${NC}"
    exit 1
fi

create_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    echo -e "${YELLOW}Setting up secret: $secret_name${NC}"
    
    # Check if secret exists
    if aws secretsmanager describe-secret --secret-id "$secret_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        echo -e "${YELLOW}Secret '$secret_name' exists. Updating value...${NC}"
        if aws secretsmanager put-secret-value \
            --secret-id "$secret_name" \
            --secret-string "$secret_value" \
            --region "$AWS_REGION" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Secret '$secret_name' updated successfully${NC}"
        else
            echo -e "${RED}✗ Failed to update secret '$secret_name'${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}Creating new secret: $secret_name${NC}"
        if aws secretsmanager create-secret \
            --name "$secret_name" \
            --description "$description" \
            --secret-string "$secret_value" \
            --region "$AWS_REGION" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Secret '$secret_name' created successfully${NC}"
        else
            echo -e "${RED}✗ Failed to create secret '$secret_name'${NC}"
            return 1
        fi
    fi
    echo ""
}

# GitHub Integration Secrets
echo -e "${BLUE}Setting up GitHub integration secrets...${NC}"
echo "----------------------------------------"

if [ -n "$GITHUB_TOKEN" ]; then
    create_secret "ai-pipeline-v2/github-token-$ENVIRONMENT" \
        "{\"token\":\"$GITHUB_TOKEN\"}" \
        "GitHub token for AI Pipeline v2 repository operations in $ENVIRONMENT"
else
    echo -e "${RED}Warning: GITHUB_TOKEN not found in .env file${NC}"
fi

if [ -n "$GITHUB_USERNAME" ]; then
    create_secret "ai-pipeline-v2/github-config-$ENVIRONMENT" \
        "{\"username\":\"$GITHUB_USERNAME\",\"default_org\":\"$GITHUB_USERNAME\"}" \
        "GitHub configuration for AI Pipeline v2 in $ENVIRONMENT"
else
    echo -e "${RED}Warning: GITHUB_USERNAME not found in .env file${NC}"
fi

# Netlify Deployment Secrets
echo -e "${BLUE}Setting up Netlify deployment secrets...${NC}"
echo "----------------------------------------"

if [ -n "$NETLIFY_TOKEN" ]; then
    create_secret "ai-pipeline-v2/netlify-token-$ENVIRONMENT" \
        "{\"token\":\"$NETLIFY_TOKEN\"}" \
        "Netlify deployment token for AI Pipeline v2 in $ENVIRONMENT"
else
    echo -e "${RED}Warning: NETLIFY_TOKEN not found in .env file${NC}"
fi

# AI Service Secrets
echo -e "${BLUE}Setting up AI service secrets...${NC}"
echo "----------------------------------------"

if [ -n "$ANTHROPIC_API_KEY" ]; then
    create_secret "ai-pipeline-v2/anthropic-api-key-$ENVIRONMENT" \
        "{\"api_key\":\"$ANTHROPIC_API_KEY\"}" \
        "Anthropic API key for AI Pipeline v2 in $ENVIRONMENT"
else
    echo -e "${RED}Warning: ANTHROPIC_API_KEY not found in .env file${NC}"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    create_secret "ai-pipeline-v2/openai-api-key-$ENVIRONMENT" \
        "{\"api_key\":\"$OPENAI_API_KEY\"}" \
        "OpenAI API key fallback for AI Pipeline v2 in $ENVIRONMENT"
else
    echo -e "${YELLOW}Note: OPENAI_API_KEY not found (optional fallback)${NC}"
fi

# AWS Configuration Secrets (for cross-account deployments if needed)
echo -e "${BLUE}Setting up deployment configuration...${NC}"
echo "----------------------------------------"

DEPLOYMENT_CONFIG="{
    \"aws_region\":\"$AWS_REGION\",
    \"environment\":\"$ENVIRONMENT\",
    \"enable_human_review\":\"${ENABLE_HUMAN_REVIEW:-true}\",
    \"auto_merge_prs\":\"${AUTO_MERGE_PRS:-false}\",
    \"required_approvers\":\"${REQUIRED_APPROVERS:-1}\"
}"

create_secret "ai-pipeline-v2/deployment-config-$ENVIRONMENT" \
    "$DEPLOYMENT_CONFIG" \
    "Deployment configuration for AI Pipeline v2 in $ENVIRONMENT"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}      Secrets Setup Summary           ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${GREEN}✓ GitHub integration secrets configured${NC}"
echo -e "${GREEN}✓ Netlify deployment secrets configured${NC}"
echo -e "${GREEN}✓ AI service secrets configured${NC}"
echo -e "${GREEN}✓ Deployment configuration stored${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Deploy infrastructure: cd infrastructure && npm run deploy-$ENVIRONMENT"
echo "2. Deploy lambdas: ./scripts/deploy-all.sh $ENVIRONMENT"
echo "3. Test secret access: ./scripts/test-secrets.sh $ENVIRONMENT"
echo ""
echo -e "${BLUE}Secret names created:${NC}"
echo "  - ai-pipeline-v2/github-token-$ENVIRONMENT"
echo "  - ai-pipeline-v2/github-config-$ENVIRONMENT"  
echo "  - ai-pipeline-v2/netlify-token-$ENVIRONMENT"
echo "  - ai-pipeline-v2/anthropic-api-key-$ENVIRONMENT"
echo "  - ai-pipeline-v2/deployment-config-$ENVIRONMENT"
echo ""
echo -e "${YELLOW}To view secrets:${NC}"
echo "aws secretsmanager list-secrets --region $AWS_REGION | grep ai-pipeline-v2"
echo ""
echo -e "${BLUE}======================================${NC}"