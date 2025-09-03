#!/bin/bash

# Deploy Sequential Pipeline Infrastructure and Lambdas
# Usage: ./deploy-sequential-pipeline.sh [environment]

set -e

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo "========================================"
echo "Deploying Sequential Pipeline"
echo "========================================"
echo "Environment: $ENVIRONMENT"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Step 1: Deploy CDK Infrastructure
print_status "Deploying CDK infrastructure with Sequential Stack..."
cd infrastructure
npm install
npx cdk bootstrap aws://${AWS_ACCOUNT}/${AWS_REGION} || true
npx cdk deploy AIPipelineV2Stack-${ENVIRONMENT} \
    --context environment=${ENVIRONMENT} \
    --require-approval never \
    --outputs-file cdk-outputs-${ENVIRONMENT}.json

print_status "CDK infrastructure deployed successfully"

# Step 2: Deploy Story Executor Lambda
print_status "Deploying Story Executor Lambda..."
cd ../lambdas/core/story-executor
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -t .
fi
zip -r story-executor.zip . -x "*.pyc" -x "__pycache__/*" -x ".git/*"

aws lambda update-function-code \
    --function-name ai-pipeline-v2-story-executor-${ENVIRONMENT} \
    --zip-file fileb://story-executor.zip \
    --region ${AWS_REGION} 2>/dev/null || \
aws lambda create-function \
    --function-name ai-pipeline-v2-story-executor-${ENVIRONMENT} \
    --runtime python3.11 \
    --role arn:aws:iam::${AWS_ACCOUNT}:role/ai-pipeline-v2-lambda-role-${ENVIRONMENT} \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://story-executor.zip \
    --timeout 900 \
    --memory-size 1024 \
    --region ${AWS_REGION}

rm story-executor.zip
print_status "Story Executor Lambda deployed"

# Step 3: Deploy Story Validator Lambda
print_status "Deploying Story Validator Lambda..."
cd ../../story-execution/story-validator
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -t .
fi
zip -r story-validator.zip . -x "*.pyc" -x "__pycache__/*" -x ".git/*"

aws lambda update-function-code \
    --function-name ai-pipeline-v2-story-validator-${ENVIRONMENT} \
    --zip-file fileb://story-validator.zip \
    --region ${AWS_REGION} 2>/dev/null || \
aws lambda create-function \
    --function-name ai-pipeline-v2-story-validator-${ENVIRONMENT} \
    --runtime python3.11 \
    --role arn:aws:iam::${AWS_ACCOUNT}:role/ai-pipeline-v2-lambda-role-${ENVIRONMENT} \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://story-validator.zip \
    --timeout 300 \
    --memory-size 512 \
    --region ${AWS_REGION}

rm story-validator.zip
print_status "Story Validator Lambda deployed"

# Step 4: Deploy Build Orchestrator Lambda
print_status "Deploying Build Orchestrator Lambda..."
cd ../build-orchestrator
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -t .
fi
zip -r build-orchestrator.zip . -x "*.pyc" -x "__pycache__/*" -x ".git/*"

aws lambda update-function-code \
    --function-name ai-pipeline-v2-build-orchestrator-${ENVIRONMENT} \
    --zip-file fileb://build-orchestrator.zip \
    --region ${AWS_REGION} 2>/dev/null || \
aws lambda create-function \
    --function-name ai-pipeline-v2-build-orchestrator-${ENVIRONMENT} \
    --runtime python3.11 \
    --role arn:aws:iam::${AWS_ACCOUNT}:role/ai-pipeline-v2-lambda-role-${ENVIRONMENT} \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://build-orchestrator.zip \
    --timeout 600 \
    --memory-size 2048 \
    --region ${AWS_REGION}

rm build-orchestrator.zip
print_status "Build Orchestrator Lambda deployed"

# Step 5: Deploy Updated Integration Validator
print_status "Deploying updated Integration Validator Lambda..."
cd ../integration-validator
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -t .
fi
zip -r integration-validator.zip . -x "*.pyc" -x "__pycache__/*" -x ".git/*"

aws lambda update-function-code \
    --function-name ai-pipeline-v2-integration-validator-${ENVIRONMENT} \
    --zip-file fileb://integration-validator.zip \
    --region ${AWS_REGION}

rm integration-validator.zip
print_status "Integration Validator Lambda updated"

# Step 6: Deploy Updated GitHub Orchestrator
print_status "Deploying updated GitHub Orchestrator Lambda..."
cd ../github-orchestrator
./deploy-github-orchestrator.sh ${ENVIRONMENT} || ../../../scripts/deploy-github-orchestrator.sh ${ENVIRONMENT}
print_status "GitHub Orchestrator Lambda updated"

# Step 7: Deploy Step Functions State Machine
print_status "Deploying Sequential Step Functions workflow..."
cd ../../../infrastructure

# Get the state machine ARN from CDK outputs
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
    --stack-name AIPipelineV2Stack-${ENVIRONMENT} \
    --query "Stacks[0].Outputs[?OutputKey=='SequentialStateMachineArn'].OutputValue" \
    --output text \
    --region ${AWS_REGION})

if [ -z "$STATE_MACHINE_ARN" ]; then
    print_warning "Sequential State Machine not found in stack outputs. Running CDK deploy again..."
    npx cdk deploy AIPipelineV2Stack-${ENVIRONMENT} \
        --context environment=${ENVIRONMENT} \
        --require-approval never
    
    STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
        --stack-name AIPipelineV2Stack-${ENVIRONMENT} \
        --query "Stacks[0].Outputs[?OutputKey=='SequentialStateMachineArn'].OutputValue" \
        --output text \
        --region ${AWS_REGION})
fi

print_status "Sequential State Machine ARN: $STATE_MACHINE_ARN"

# Step 8: Configure CloudWatch Log Groups
print_status "Setting up CloudWatch Log Groups..."
aws logs create-log-group \
    --log-group-name /aws/lambda/ai-pipeline-v2-story-executor-${ENVIRONMENT} \
    --region ${AWS_REGION} 2>/dev/null || true

aws logs create-log-group \
    --log-group-name /aws/lambda/ai-pipeline-v2-story-validator-${ENVIRONMENT} \
    --region ${AWS_REGION} 2>/dev/null || true

aws logs create-log-group \
    --log-group-name /aws/lambda/ai-pipeline-v2-build-orchestrator-${ENVIRONMENT} \
    --region ${AWS_REGION} 2>/dev/null || true

aws logs create-log-group \
    --log-group-name /aws/stepfunctions/ai-pipeline-v2-sequential-${ENVIRONMENT} \
    --region ${AWS_REGION} 2>/dev/null || true

print_status "CloudWatch Log Groups configured"

# Step 9: Set up CloudWatch Alarms
print_status "Setting up CloudWatch Alarms..."
aws cloudwatch put-metric-alarm \
    --alarm-name ai-pipeline-v2-story-executor-errors-${ENVIRONMENT} \
    --alarm-description "Story Executor Lambda error rate" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value=ai-pipeline-v2-story-executor-${ENVIRONMENT} \
    --evaluation-periods 1 \
    --region ${AWS_REGION} 2>/dev/null || true

aws cloudwatch put-metric-alarm \
    --alarm-name ai-pipeline-v2-build-orchestrator-duration-${ENVIRONMENT} \
    --alarm-description "Build Orchestrator Lambda duration" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --threshold 300000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value=ai-pipeline-v2-build-orchestrator-${ENVIRONMENT} \
    --evaluation-periods 1 \
    --region ${AWS_REGION} 2>/dev/null || true

print_status "CloudWatch Alarms configured"

# Step 10: Verify Deployment
print_status "Verifying deployment..."
echo ""
echo "Lambda Functions Status:"
echo "------------------------"

LAMBDAS=(
    "ai-pipeline-v2-story-executor-${ENVIRONMENT}"
    "ai-pipeline-v2-story-validator-${ENVIRONMENT}"
    "ai-pipeline-v2-build-orchestrator-${ENVIRONMENT}"
    "ai-pipeline-v2-integration-validator-${ENVIRONMENT}"
    "ai-pipeline-v2-github-orchestrator-${ENVIRONMENT}"
)

for lambda in "${LAMBDAS[@]}"; do
    STATUS=$(aws lambda get-function --function-name $lambda --query "Configuration.State" --output text --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")
    if [ "$STATUS" == "Active" ]; then
        print_status "$lambda: $STATUS"
    else
        print_error "$lambda: $STATUS"
    fi
done

echo ""
echo "========================================"
echo "Sequential Pipeline Deployment Complete!"
echo "========================================"
echo ""
echo "Next Steps:"
echo "1. Run test: ./scripts/test-sequential-pipeline.sh ${ENVIRONMENT}"
echo "2. Monitor logs: aws logs tail /aws/lambda/ai-pipeline-v2-story-executor-${ENVIRONMENT} --follow"
echo "3. View metrics: aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration"
echo ""
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""