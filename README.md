# AI Pipeline Orchestrator v2

A story-based AI development pipeline with human review workflows and incremental code generation.

## Architecture

This system replaces the monolithic code generation approach with focused, single-responsibility lambdas that work together to create applications incrementally through user stories.

### Core Components

- **7 Focused Lambdas**: Each averaging 200-300 lines with single responsibility
- **Story-Based Generation**: Incremental development via GitHub Actions CI/CD
- **Human Review Integration**: Built-in PR workflows with Netlify/ECS deployment
- **Multi-Document Intake**: PDFs, transcripts, emails, chats with versioning
- **Composable Infrastructure**: Individual lambda deployment and testing

## Project Structure

```
ai-pipeline-v2/
├── lambdas/                    # 7 Lambda functions
│   ├── core/                   # Sequential pipeline (3 functions)
│   │   ├── document-processor/         # Multi-format document intake
│   │   ├── requirements-synthesizer/   # Story extraction and synthesis  
│   │   └── architecture-planner/       # Tech stack and component design
│   ├── story-execution/        # Parallel story processing (3 functions)
│   │   ├── story-executor/             # GitHub repo creation and coding
│   │   ├── integration-validator/      # Cross-component validation
│   │   └── github-orchestrator/        # Netlify/ECS deployment + PR creation
│   └── human-review/           # Review workflow (1 function)
│       └── review-coordinator/         # PR management and feedback
├── infrastructure/             # CDK infrastructure code
├── shared/                     # Common libraries and utilities
├── scripts/                    # Deployment and testing scripts
├── github-workflows/           # GitHub Actions CI/CD templates
├── docs/                       # Testing guides and templates
└── tests/                      # Integration and E2E tests
```

## Development Workflow

1. **Document Processing**: Multi-format intake with versioning
2. **Requirements Synthesis**: Story extraction and prioritization  
3. **Architecture Planning**: Tech stack and component design
4. **Story Execution**: GitHub repo creation with GitHub Actions CI/CD
5. **Integration Validation**: Cross-component consistency and testing
6. **Deployment Orchestration**: Automated Netlify (frontend) and ECS (backend) deployment
7. **Human Review**: PR-based feedback with automated deployment pipeline

## Recent Architecture Updates (2025-08-27)

### PyNaCl Lambda Layer for GitHub Secrets Encryption

**Problem Solved**: GitHub orchestrator Lambda was failing with PyNaCl native library loading errors due to architecture mismatch (ARM64 vs x86_64).

**Solution**: Created a dedicated Lambda layer with properly compiled PyNaCl for x86_64 architecture.

#### Building the PyNaCl Layer
```bash
# Build the PyNaCl layer with x86_64 architecture
cd layers/pynacl
./build-layer.sh  # Uses Docker with --platform linux/amd64 for proper compilation
```

#### Key Changes:
- **Removed base64 fallback**: GitHub API requires libsodium encryption - no alternatives
- **Dedicated PyNaCl layer**: Properly compiled for Lambda x86_64 runtime
- **CDK integration**: Layer automatically attached to GitHub orchestrator Lambda
- **Architecture enforcement**: Lambda explicitly set to X86_64 to match layer

The layer ensures reliable GitHub repository secret management for CI/CD workflows.

## Quick Setup & Deployment

### Complete Infrastructure Deployment (IaC)

The entire infrastructure including S3 trigger, Lambda functions, Step Functions, and secrets management can be deployed through Infrastructure as Code:

```bash
# 1. Deploy complete CDK infrastructure with secrets management
cd infrastructure && npm install
npm run deploy-dev                          # Deploy AWS infrastructure with secrets stack

# 2. Update secrets with real API tokens (required for GitHub integration)
source .env  # Ensure .env file exists with GITHUB_TOKEN and ANTHROPIC_API_KEY
aws secretsmanager put-secret-value --secret-id "ai-pipeline-v2/github-token-dev" \
  --secret-string "{\"token\":\"${GITHUB_TOKEN}\",\"username\":\"ai-pipeline\"}"
aws secretsmanager put-secret-value --secret-id "ai-pipeline-v2/anthropic-api-key-dev" \
  --secret-string "{\"apiKey\":\"${ANTHROPIC_API_KEY}\",\"model\":\"claude-3-sonnet-20240229\"}"

# 3. Deploy Lambda functions (7-function GitHub Actions architecture)
./scripts/deploy-all.sh dev                 # Deploy all lambdas to dev environment

# 4. Test the complete pipeline by uploading a document
echo "Your project requirements here..." > test-document.txt
aws s3 cp test-document.txt s3://ai-pipeline-v2-raw-{account-id}-{region}/
# This automatically triggers the pipeline via S3 notifications
```

### Key Features of Complete IaC Solution

✅ **Zero Circular Dependencies**: Fixed through conditional deployment approach
✅ **Secrets Management**: API keys managed through AWS Secrets Manager with IaC
✅ **S3 Trigger Integration**: Automatic pipeline start on document uploads  
✅ **Complete Infrastructure**: Single command deployment of entire system
✅ **Production Ready**: Proper IAM, monitoring, and security configuration

## Legacy Quick Setup (if needed)

```bash
# 1. Clone and setup environment
git clone <repository-url>
cd ai-pipeline-v2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure AWS and secrets
aws configure  # Set up AWS credentials
./scripts/setup-secrets.sh dev  # Configure GitHub, Netlify, Anthropic tokens

# 3. Deploy infrastructure
cd infrastructure && npm install
npm run deploy-dev  # Deploy to development environment

# 4. Deploy all Lambda functions
./scripts/deploy-all.sh dev

# 5. Verify deployment
./scripts/monitor-deployments.sh dev
```

## Usage Instructions

### Core Pipeline Execution

#### 1. Document Processing
```bash
# Test document processor with sample documents
./scripts/test-lambda.sh document-processor dev test-data/sample-documents.json

# Process your own documents
python -c "
import json
import boto3
from shared.services.s3_service import S3Service

# Upload document and trigger pipeline
s3_service = S3Service()
result = s3_service.upload_document('path/to/your/document.pdf', 'your-project-name')
print(f'Document uploaded: {result}')
"
```

#### 2. Story-Based Code Generation
```bash
# Monitor story execution pipeline
./scripts/monitor-deployments.sh dev --watch

# Check generated code artifacts
aws s3 ls s3://ai-pipeline-v2-code-artifacts-<account>-<region>/projects/your-project-name/ --recursive

# Review generated GitHub repositories
gh repo list --limit 10  # View your GitHub repositories
```

### Generated App Deployment & Testing

#### Deploy Generated Applications
```bash
# Test the deployment of a generated project
./scripts/test-deployment.sh <project-name> dev

# Collect feedback after manual testing
./scripts/collect-feedback.sh <project-name> dev

# Monitor deployment health
./scripts/monitor-deployments.sh dev --report
```

#### Access Your Generated Applications
```bash
# Frontend applications (React SPA, Vue SPA)
# URL: https://<project-name>-dev.netlify.app

# Backend APIs (Node.js API, Python FastAPI)
# URL: https://<project-name>-api-dev.<ecs-domain>

# GitHub repository with CI/CD
# URL: https://github.com/<username>/<project-name>
```

### Manual Testing Process
```bash
# 1. Use automated testing first
./scripts/test-deployment.sh my-react-app dev

# 2. Follow manual testing checklist
cp docs/templates/MANUAL_TESTING_CHECKLIST.md testing-checklist-my-app.md
# Fill out the checklist while testing

# 3. Submit feedback
./scripts/collect-feedback.sh my-react-app dev

# 4. Review GitHub PR and approve/request changes
gh pr view --repo <username>/my-react-app
gh pr review --approve --body "Manual testing passed" --repo <username>/my-react-app
```

## Development Commands

### Lambda Function Development
```bash
# Deploy individual functions
./scripts/deploy-single.sh story-executor dev
./scripts/deploy-single.sh github-orchestrator dev

# Run unit tests
python -m pytest tests/unit/ -v
ANTHROPIC_API_KEY=your-key python -m pytest tests/unit/test_story_executor.py -v

# Run integration tests  
python -m pytest tests/integration/ -v
```

### Infrastructure Management
```bash
# Infrastructure deployment
cd infrastructure && npm install
npm run deploy-dev     # Development environment
npm run deploy-prod    # Production environment
npx cdk synth         # Generate CloudFormation templates
npx cdk diff          # Show changes before deployment

# Complete teardown
npx cdk destroy
```

### Monitoring and Debugging
```bash
# Real-time monitoring
./scripts/monitor-deployments.sh dev --watch

# View Lambda logs
aws logs tail /aws/lambda/ai-pipeline-v2-story-executor-dev --follow
aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-dev --follow

# Debug individual functions
export LOG_LEVEL=DEBUG
./scripts/test-lambda.sh story-executor dev

# Health checks
python scripts/health_check.py --environment dev
python scripts/health_check.py --component github-orchestrator --environment dev
```

## Examples and Use Cases

### Example 1: Simple React App
```bash
# 1. Create a requirements document describing a simple React app
echo "Build a React todo application with add, edit, delete functionality" > my-todo-app-requirements.md

# 2. Process the document through the pipeline
# Upload to S3 raw bucket or use document processor API

# 3. Monitor the generated repository
gh repo view my-todo-app

# 4. Test the deployed application
./scripts/test-deployment.sh my-todo-app dev

# Expected output: React SPA deployed to Netlify with GitHub Actions CI/CD
```

### Example 2: Full-Stack Node.js API
```bash
# 1. Requirements for a REST API
echo "Build a Node.js Express API for user management with authentication, CRUD operations, and PostgreSQL database" > user-management-api.md

# 2. After pipeline processing, check generated components:
aws s3 ls s3://ai-pipeline-v2-code-artifacts-<account>-<region>/projects/user-management-api/

# 3. Test the deployed backend
curl https://user-management-api-dev.<ecs-domain>/health
curl https://user-management-api-dev.<ecs-domain>/api/docs

# Expected output: Node.js API deployed to ECS Fargate with auto-scaling
```

## Troubleshooting

### Common Issues

#### 1. Lambda Function Deployment Failures
```bash
# Check deployment logs
./scripts/monitor-deployments.sh dev

# Redeploy individual function
./scripts/deploy-single.sh github-orchestrator dev

# Check IAM permissions
aws iam get-role --role-name ai-pipeline-v2-lambda-execution-role-dev
```

#### 2. GitHub Integration Issues
```bash
# Verify GitHub token
./scripts/test-secrets.sh dev

# Check GitHub API access
gh auth status

# Review GitHub Actions runs
gh run list --repo <username>/<project-name>
```

#### 3. Netlify Deployment Problems
```bash
# Check Netlify site status via CLI
netlify status

# Verify deployment from logs  
aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-dev --follow | grep -i netlify

# Manual deployment test
netlify deploy --prod --dir=build --site=<site-name>
```

#### 4. ECS Backend Deployment Issues
```bash
# Check ECS service status
aws ecs describe-services --cluster ai-pipeline-v2-dev --services <project-name>-api-dev

# View container logs
aws logs tail /aws/ecs/<project-name>-api-dev --follow

# Check task definition
aws ecs describe-task-definition --task-definition <project-name>-api-dev
```

### Performance Optimization

```bash
# Monitor Lambda performance
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=ai-pipeline-v2-story-executor-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Optimize costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '7 days ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## Architecture Details

### Technology Stack
- **Infrastructure**: AWS CDK (TypeScript), Step Functions for orchestration
- **Compute**: AWS Lambda (Python 3.11), ECS Fargate (containerized backends)
- **Storage**: S3 (documents/code artifacts), DynamoDB (metadata/state)
- **CI/CD**: GitHub Actions with Netlify (frontend) and ECS (backend) deployment
- **AI/ML**: Anthropic Claude API (direct integration), with AWS Bedrock fallback
- **Integration**: GitHub API for repository management, Netlify API for frontend hosting

### Security and Compliance
- **Secrets Management**: AWS Secrets Manager for tokens and credentials
- **IAM**: Least privilege access with resource-scoped permissions
- **Encryption**: S3 server-side encryption, DynamoDB encryption at rest
- **Network**: VPC isolation for ECS workloads, ALB with HTTPS termination
- **Audit**: CloudTrail logging, structured Lambda logging with execution tracing

### Monitoring and Observability
- **Metrics**: CloudWatch custom metrics for story completion rates, deployment success
- **Alerts**: Error rate thresholds, execution time degradation, cost budget alerts
- **Dashboards**: Environment-specific monitoring with key performance indicators
- **Logs**: Structured JSON logging with correlation IDs across Lambda functions