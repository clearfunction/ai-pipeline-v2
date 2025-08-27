#!/bin/bash

# Test AWS Secrets Manager access for deployment secrets
# Usage: ./scripts/test-secrets.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo -e "${YELLOW}Testing secret access for environment: $ENVIRONMENT${NC}"
echo ""

test_secret() {
    local secret_name=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    if aws secretsmanager get-secret-value --secret-id "$secret_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Test all required secrets
FAILED_TESTS=0

test_secret "ai-pipeline-v2/github-token-$ENVIRONMENT" "GitHub token" || ((FAILED_TESTS++))
test_secret "ai-pipeline-v2/github-config-$ENVIRONMENT" "GitHub config" || ((FAILED_TESTS++))
test_secret "ai-pipeline-v2/netlify-token-$ENVIRONMENT" "Netlify token" || ((FAILED_TESTS++))
test_secret "ai-pipeline-v2/anthropic-api-key-$ENVIRONMENT" "Anthropic API key" || ((FAILED_TESTS++))
test_secret "ai-pipeline-v2/deployment-config-$ENVIRONMENT" "Deployment config" || ((FAILED_TESTS++))

echo ""
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All secrets accessible successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Sample secret retrieval (GitHub config):${NC}"
    aws secretsmanager get-secret-value --secret-id "ai-pipeline-v2/github-config-$ENVIRONMENT" --region "$AWS_REGION" --query 'SecretString' --output text | jq .
    exit 0
else
    echo -e "${RED}✗ $FAILED_TESTS secret(s) failed access test${NC}"
    echo ""
    echo -e "${YELLOW}To fix missing secrets, run:${NC}"
    echo "./scripts/setup-secrets.sh $ENVIRONMENT"
    exit 1
fi