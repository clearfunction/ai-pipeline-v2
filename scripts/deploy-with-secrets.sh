#!/bin/bash

# Deploy CDK with real secrets from .env file
# Usage: ./scripts/deploy-with-secrets.sh [environment]

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "🔐 Loading secrets from .env file..."
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Export all environment variables from .env file
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found at $PROJECT_ROOT/.env"
    exit 1
fi

echo "📦 Deploying CDK stack with real secrets for environment: $ENVIRONMENT"
cd "$PROJECT_ROOT/infrastructure"

# Ensure dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing CDK dependencies..."
    npm install
fi

# Deploy with environment variables available to CDK
echo "🚀 Deploying CDK stack..."
npx cdk deploy --context environment=$ENVIRONMENT --require-approval never

echo "✅ Deployment complete with real secrets from .env file"

# Verify secrets were created/updated correctly
echo ""
echo "🔍 Verifying secrets in AWS Secrets Manager..."
aws secretsmanager get-secret-value --secret-id "ai-pipeline-v2/github-token-$ENVIRONMENT" --query 'SecretString' --output text | jq -r '.token' | head -c 20 && echo "... (GitHub token verified)"
aws secretsmanager get-secret-value --secret-id "ai-pipeline-v2/netlify-token-$ENVIRONMENT" --query 'SecretString' --output text | jq -r '.token' | head -c 20 && echo "... (Netlify token verified)"
aws secretsmanager get-secret-value --secret-id "ai-pipeline-v2/anthropic-api-key-$ENVIRONMENT" --query 'SecretString' --output text | jq -r '.apiKey' | head -c 20 && echo "... (Anthropic API key verified)"

echo ""
echo "✅ All secrets verified successfully!"