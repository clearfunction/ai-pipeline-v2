# AI Pipeline Orchestrator v2 - Deployment Guide

## Prerequisites

### System Requirements
- **AWS CLI**: Version 2.x configured with appropriate permissions
- **Node.js**: Version 18+ for CDK infrastructure
- **Python**: Version 3.11+ for Lambda development
- **Docker**: For container-based deployments (if needed)
- **jq**: For JSON processing in scripts

### AWS Permissions
Required IAM permissions for deployment:
- Lambda: Create, update, delete functions
- S3: Create buckets, manage objects
- DynamoDB: Create tables, manage items
- Step Functions: Create state machines
- IAM: Create roles and policies
- CloudFormation: Deploy stacks
- Bedrock: Access foundation models

### Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd ai-pipeline-v2

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies for infrastructure
cd infrastructure
npm install
```

## Configuration

### Environment Variables
Copy and configure environment variables:
```bash
cp .env.example .env
```

Required configuration:
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# LLM Configuration
PRIMARY_LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Review Workflow
ENABLE_HUMAN_REVIEW=true
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_username
```

### AWS Bedrock Setup
Enable required models in AWS Bedrock:
1. Navigate to AWS Bedrock console
2. Go to Model Access → Manage model access
3. Enable "Claude 3 Sonnet" and "Claude 3 Haiku"
4. Wait for access approval (usually immediate)

## Deployment Process

### Method 1: Full Automated Deployment

```bash
# Deploy everything in sequence
./deploy.sh [environment]

# Example for development environment
./deploy.sh dev
```

This script will:
1. Deploy infrastructure (S3, DynamoDB, IAM roles)
2. Create shared Lambda layer
3. Deploy all Lambda functions
4. Create Step Functions workflow
5. Run integration tests

### Method 2: Step-by-Step Deployment

#### Step 1: Deploy Infrastructure
```bash
cd infrastructure

# Development environment
npm run deploy-dev

# Production environment
npm run deploy-prod

# Custom environment
npx cdk deploy --context environment=staging
```

#### Step 2: Deploy Lambda Functions
```bash
# Deploy all functions
./scripts/deploy-all.sh dev

# Deploy individual function
./scripts/deploy-single.sh document-processor dev
```

#### Step 3: Verify Deployment
```bash
# Test individual lambda
./scripts/test-lambda.sh document-processor dev

# Run integration tests
python tests/test_integration.py
```

## Environment-Specific Deployments

### Development Environment
- **Purpose**: Individual developer testing
- **Retention**: 7 days for logs, 30 days for data
- **Resources**: Minimal sizing for cost optimization
- **Monitoring**: Basic CloudWatch metrics

```bash
# Deploy development environment
./scripts/deploy-all.sh dev
```

### Staging Environment
- **Purpose**: Integration testing and QA
- **Retention**: 30 days for logs, 90 days for data
- **Resources**: Production-like sizing
- **Monitoring**: Enhanced metrics and alerting

```bash
# Deploy staging environment
./scripts/deploy-all.sh staging
```

### Production Environment
- **Purpose**: Live customer workloads
- **Retention**: 1 year for logs, indefinite for data
- **Resources**: Auto-scaling with high availability
- **Monitoring**: Full observability suite

```bash
# Deploy production environment
./scripts/deploy-all.sh prod
```

## Deployment Verification

### Infrastructure Verification
```bash
# Check S3 buckets
aws s3 ls | grep ai-pipeline-v2

# Check DynamoDB tables
aws dynamodb list-tables --query "TableNames[?contains(@, 'ai-pipeline-v2')]"

# Check Lambda functions
aws lambda list-functions --query "Functions[?contains(FunctionName, 'ai-pipeline-v2')]"

# Check Step Functions
aws stepfunctions list-state-machines --query "stateMachines[?contains(name, 'ai-pipeline')]"
```

### Functional Testing
```bash
# Test document processing
./scripts/test-lambda.sh document-processor dev test-data/sample-pdf.json

# Test requirements synthesis
./scripts/test-lambda.sh requirements-synthesizer dev test-data/sample-stories.json

# Test architecture planning
./scripts/test-lambda.sh architecture-planner dev test-data/sample-architecture.json

# End-to-end pipeline test
python tests/test_e2e_pipeline.py --environment dev
```

## Monitoring & Observability

### CloudWatch Dashboards
After deployment, create monitoring dashboards:

```bash
# Create custom dashboard
aws cloudwatch put-dashboard --dashboard-name "AI-Pipeline-v2-${ENVIRONMENT}" --dashboard-body file://monitoring/dashboard.json
```

### Log Monitoring
```bash
# View real-time logs for all functions
aws logs tail /aws/lambda/ai-pipeline-v2 --follow

# View specific function logs
aws logs tail /aws/lambda/ai-pipeline-v2-document-processor-dev --follow

# Search for errors
aws logs filter-log-events --log-group-name "/aws/lambda/ai-pipeline-v2-document-processor-dev" --filter-pattern "ERROR"
```

### Performance Metrics
Key metrics to monitor:
- **Lambda Duration**: Function execution time
- **Lambda Errors**: Error rate and types
- **Step Functions**: Workflow success/failure rate
- **S3 Operations**: Document processing throughput
- **DynamoDB**: Read/write capacity and throttling
- **Bedrock**: API calls and cost

## Troubleshooting

### Common Issues

#### 1. Lambda Deployment Fails
```bash
# Check function size
aws lambda get-function --function-name ai-pipeline-v2-document-processor-dev --query "Configuration.CodeSize"

# If package too large, check dependencies
pip list --format=freeze > current-dependencies.txt

# Redeploy with size optimization
./scripts/deploy-single.sh document-processor dev --optimize
```

#### 2. Bedrock Access Denied
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1

# Request access if needed
echo "Navigate to AWS Bedrock console → Model Access"
```

#### 3. S3 Bucket Creation Fails
```bash
# Check bucket naming conflicts
aws s3 ls s3://ai-pipeline-v2-raw-$(aws sts get-caller-identity --query Account --output text)-us-east-1

# Use unique suffix if needed
export BUCKET_SUFFIX="-$(date +%s)"
./scripts/deploy-all.sh dev
```

#### 4. DynamoDB Throttling
```bash
# Check table metrics
aws dynamodb describe-table --table-name ai-pipeline-v2-user-stories-dev

# Increase provisioned capacity if needed
aws dynamodb modify-table --table-name ai-pipeline-v2-user-stories-dev --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10
```

### Debug Mode
Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
./scripts/test-lambda.sh document-processor dev
```

### Health Checks
```bash
# Run health check for all components
python scripts/health_check.py --environment dev

# Check individual components
python scripts/health_check.py --component document-processor --environment dev
```

## Rollback Procedures

### Lambda Function Rollback
```bash
# List function versions
aws lambda list-versions-by-function --function-name ai-pipeline-v2-document-processor-dev

# Rollback to previous version
aws lambda update-alias --function-name ai-pipeline-v2-document-processor-dev --name LIVE --function-version 1
```

### Infrastructure Rollback
```bash
cd infrastructure

# Rollback CDK stack
npx cdk deploy --rollback

# Emergency: Delete and recreate
npx cdk destroy
npx cdk deploy
```

### Data Recovery
```bash
# Restore DynamoDB table from point-in-time
aws dynamodb restore-table-from-backup --target-table-name ai-pipeline-v2-user-stories-dev-restored --backup-arn arn:aws:dynamodb:...

# Restore S3 objects from versioning
aws s3api list-object-versions --bucket ai-pipeline-v2-processed-...
aws s3api restore-object --bucket ... --key ... --version-id ...
```

## Cost Optimization

### Resource Sizing
```bash
# Monitor Lambda memory usage
aws logs filter-log-events --log-group-name "/aws/lambda/ai-pipeline-v2-document-processor-dev" --filter-pattern "REPORT" | grep "Max Memory Used"

# Adjust memory allocation
aws lambda update-function-configuration --function-name ai-pipeline-v2-document-processor-dev --memory-size 512
```

### Usage Monitoring
```bash
# Daily cost report
python scripts/cost_analysis.py --period daily --environment dev

# LLM usage tracking
python scripts/llm_usage.py --period weekly
```

## Security Considerations

### Secret Management
```bash
# Store GitHub token in Secrets Manager
aws secretsmanager create-secret --name "github-token-dev" --secret-string "$GITHUB_TOKEN"

# Update Lambda environment variables
aws lambda update-function-configuration --function-name ai-pipeline-v2-review-coordinator-dev --environment Variables="{GITHUB_TOKEN_SECRET=github-token-dev}"
```

### Network Security
- All Lambda functions run in AWS managed VPC
- S3 buckets have public access blocked
- DynamoDB tables use encryption at rest
- IAM roles follow least privilege principle

### Compliance
- Enable CloudTrail for audit logging
- Set up AWS Config for compliance monitoring
- Implement backup and retention policies
- Regular security scanning with AWS Inspector

## Maintenance

### Regular Updates
```bash
# Update Lambda runtime
./scripts/update-runtime.sh python3.11

# Update dependencies
pip-review --auto
npm update

# Redeploy with updates
./scripts/deploy-all.sh dev
```

### Backup Procedures
```bash
# Backup DynamoDB tables
python scripts/backup_dynamodb.py --environment dev

# Backup S3 data
aws s3 sync s3://ai-pipeline-v2-processed-... ./backups/$(date +%Y-%m-%d)/
```

### Performance Tuning
```bash
# Analyze performance metrics
python scripts/performance_analysis.py --period 7days --environment prod

# Optimize based on recommendations
./scripts/optimize-performance.sh
```