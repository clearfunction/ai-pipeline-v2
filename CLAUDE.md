# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Pipeline Orchestrator v2 is a story-based AI development pipeline with GitHub Actions integration and human review workflows. It transforms from monolithic code generation to a focused 7-lambda architecture that generates deployable applications through user stories with automated deployment to Netlify (frontend) and ECS Fargate (backend).

## Commands for Development

### Quick Setup & Deployment
```bash
# 1. Deploy infrastructure with IaC-managed secrets
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

# 4. Test the complete pipeline
./scripts/test-lambda.sh story-executor dev test-data/end-to-end-test.json
```

### Generated App Deployment & Testing
```bash
# Test deployed applications
./scripts/test-deployment.sh <project-name> dev        # Automated deployment verification
./scripts/monitor-deployments.sh dev --watch           # Real-time system monitoring
./scripts/collect-feedback.sh <project-name> dev       # Structured feedback collection

# Access generated applications
# Frontend: https://{project-name}-dev.netlify.app
# Backend:  https://{project-name}-api-dev.example.com
# GitHub:   https://github.com/{username}/{project-name}
```

### Infrastructure Deployment
```bash
# Deploy infrastructure (from infrastructure/ directory)
cd infrastructure && npm install
npm run deploy-dev     # Development environment
npm run deploy-prod    # Production environment
npx cdk synth         # Generate CloudFormation templates
npx cdk diff          # Show changes before deployment

# Full infrastructure teardown
npx cdk destroy
```

### Lambda Function Deployment
```bash
# Deploy all Lambda functions in sequence (7-function architecture)
./scripts/deploy-all.sh [environment]        # Default: dev
./scripts/deploy-all.sh dev                  # Development
./scripts/deploy-all.sh prod                 # Production

# Deploy individual Lambda function
./scripts/deploy-single.sh <lambda-name> [environment]
./scripts/deploy-single.sh story-executor dev
./scripts/deploy-single.sh github-orchestrator dev
```

### Testing Commands
```bash
# Test end-to-end pipeline
./scripts/test-lambda.sh story-executor dev test-data/end-to-end-test.json

# Python testing
python -m pytest tests/                      # Run all tests
python -m pytest tests/test_document_processor.py  # Specific test
python -m pytest -v --tb=short             # Verbose with short traceback

# Test individual Lambda functions
./scripts/test-lambda.sh <lambda-name> [environment] [test-file]
./scripts/test-lambda.sh document-processor dev
./scripts/test-lambda.sh github-orchestrator dev

# Secrets verification
./scripts/test-secrets.sh dev               # Verify AWS Secrets Manager setup
```

### Development Environment Setup
```bash
# Python environment setup
python -m venv venv
source venv/bin/activate                    # Linux/Mac
# venv\Scripts\activate                     # Windows
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-mock black isort mypy

# Code formatting and linting
black .                                     # Format Python code
isort .                                     # Sort imports
mypy shared/ lambdas/                       # Type checking
```

### Monitoring and Debugging
```bash
# Real-time deployment monitoring
./scripts/monitor-deployments.sh dev --watch       # Live system monitoring
./scripts/monitor-deployments.sh dev --report      # Generate status report

# View Lambda logs
aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-dev --follow
aws logs tail /aws/lambda/ai-pipeline-v2-story-executor-dev --follow

# Generated application testing
./scripts/test-deployment.sh <project-name> dev    # Test deployed apps
./scripts/collect-feedback.sh <project-name> dev   # Collect testing feedback

# Debug mode testing
export LOG_LEVEL=DEBUG
./scripts/test-lambda.sh story-executor dev test-data/end-to-end-test.json
```

## Architecture Overview

### Core Design Principles
- **Story-Based Development**: Incremental code generation through user stories vs monolithic generation
- **Human-in-the-Loop**: Built-in PR review workflows with Claude Code subagent integration  
- **Focused Responsibility**: 10 specialized Lambda functions (200-300 lines each) with single responsibilities
- **Multi-Document Intake**: Support for PDFs, transcripts, emails, chats with version tracking
- **Composable Infrastructure**: Individual Lambda deployment and testing capabilities

### Lambda Function Categories

#### Core Pipeline (Sequential Processing)
1. **document-processor** (200 lines): Multi-format document intake with versioning
2. **requirements-synthesizer** (250 lines): Extract and consolidate requirements into user stories
3. **architecture-planner** (300 lines): Design tech stack and component architecture

#### Story Execution (Parallel Processing)  
4. **story-manager** (200 lines): Queue management and story execution coordination
5. **component-generator** (250 lines): Generate individual components for user stories
6. **integration-validator** (200 lines): Validate cross-component integration and consistency
7. **build-orchestrator** (250 lines): Execute incremental builds and collect errors

#### Human Review Workflow
8. **review-coordinator** (200 lines): Manage PR creation and human review workflow
9. **claude-agent-dispatcher** (250 lines): Coordinate Claude Code subagents for automated fixes
10. **quality-enforcer** (200 lines): Automated quality checks and standards compliance

### Data Models and Shared Components

#### Shared Models (`shared/models/pipeline_models.py`)
- **DocumentMetadata**: Document processing and versioning
- **UserStory**: Story definitions with acceptance criteria and dependencies
- **ComponentSpec**: Component architecture and dependencies
- **ProjectArchitecture**: Overall project structure and tech stack
- **PipelineContext**: Execution context passed between Lambda stages
- **LambdaResponse**: Standardized response format across all functions

#### Shared Services
- **LLMService** (`shared/services/llm_service.py`): Bedrock-first LLM integration with OpenAI fallbacks
- **Logger** (`shared/utils/logger.py`): Structured logging with execution context tracking

### Technology Stack
- **Infrastructure**: AWS CDK (TypeScript), Step Functions for orchestration
- **Compute**: AWS Lambda (Python 3.11), shared layers for common dependencies  
- **Storage**: S3 (documents/artifacts), DynamoDB (metadata/state), versioning enabled
- **AI/ML**: AWS Bedrock (Claude 3 Sonnet/Haiku), LangChain/CrewAI for orchestration
- **Integration**: GitHub API for PR management, Claude Code for subagent coordination

### Development Workflow

#### Document Processing Flow
```
Multi-format Documents → Document Processor → S3 Processed Storage
                                  ↓
Requirements Synthesizer → User Stories → DynamoDB
                                  ↓  
Architecture Planner → Component Specs → Story Queue
```

#### Story Execution Flow (Parallel)
```
Story Manager → Component Generator → Integration Validator → Build Orchestrator
                        ↓
Review Coordinator → GitHub PR → Human Review → Claude Agent → Auto-fixes
```

### Environment Configuration

#### Development Environment Variables
```bash
# AWS Configuration (required)
AWS_DEFAULT_REGION=us-east-1
RAW_BUCKET_NAME=ai-pipeline-v2-raw-{account}-{region}
PROCESSED_BUCKET_NAME=ai-pipeline-v2-processed-{account}-{region}

# LLM Configuration
PRIMARY_LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Review Workflow
ENABLE_HUMAN_REVIEW=true
GITHUB_TOKEN=<stored-in-secrets-manager>
```

#### Lambda Environment Configuration
- All functions use Python 3.11 runtime
- Shared layer contains common dependencies (boto3, pydantic, loguru)
- Individual function timeouts: 5-15 minutes depending on complexity
- Memory allocation: 512MB-3GB based on processing requirements

### Testing Strategy

#### Test Data Structure (`test-data/`)
- `sample-documents.json`: Multi-format document examples
- `sample-stories.json`: User story test cases
- `sample-architecture.json`: Architecture planning examples
- `end-to-end-test.json`: Complete pipeline test data

#### Testing Approach
- **Unit Tests**: Each Lambda function has isolated tests
- **Integration Tests**: Cross-function workflow validation
- **End-to-End Tests**: Complete pipeline execution with real AWS resources
- **Performance Tests**: Large story set processing validation

### Code Standards and Conventions

#### Python Code Style
- Use **Pydantic** models for all data structures and validation
- **Loguru** for structured logging with execution context
- **Type hints** required for all function parameters and returns
- **Error handling** with proper exception context and logging
- **AWS SDK patterns** using boto3 with proper error handling

#### Lambda Function Structure
```python
# Standard lambda function pattern:
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    setup_logger("function-name")
    execution_id = log_lambda_start(event, context)
    try:
        # Business logic
        response = LambdaResponse(...)
        log_lambda_end(execution_id, response.dict())
        return response.dict()
    except Exception as e:
        log_error(e, execution_id, "stage_name")
        return error_response.dict()
```

#### Infrastructure Patterns
- **CDK Stacks**: Modular stack design with core/lambdas/workflows separation
- **IAM Principle**: Least privilege with resource-scoped permissions
- **Naming Convention**: `ai-pipeline-v2-{component}-{environment}`
- **Resource Tagging**: Environment, project, and cost center tags

### Deployment and Operations

#### Deployment Order
1. Infrastructure deployment (CDK stacks)
2. Shared Lambda layer creation
3. Lambda function deployment (core → story → review)
4. Step Functions workflow deployment
5. Integration testing and validation

#### Monitoring and Observability
- **CloudWatch Logs**: Structured JSON logging with execution tracing
- **Metrics**: Lambda duration, errors, concurrent executions, custom story completion rates
- **Alerting**: Error rate thresholds, execution time degradation, cost budgets
- **Dashboards**: Environment-specific monitoring with key performance indicators

#### Production Considerations
- **Blue/Green Deployments**: Zero-downtime updates using Lambda aliases
- **Error Handling**: Retry logic with exponential backoff and dead letter queues
- **Cost Optimization**: Right-sized memory allocation, LLM usage tracking
- **Security**: Secrets Manager for tokens, encryption at rest, VPC isolation where needed

### Key Dependencies and Versions

#### Python Dependencies (requirements.txt)
- `boto3>=1.34.0` - AWS SDK
- `pydantic>=2.5.0` - Data validation
- `loguru>=0.7.0` - Logging
- `langchain>=0.1.0` - LLM orchestration
- `crewai>=0.22.0` - AI agent coordination
- `pypdf>=3.17.0` - PDF processing
- `fastapi>=0.100.0` - API framework

#### Infrastructure Dependencies
- `aws-cdk-lib@2.100.0` - Infrastructure as Code
- `constructs@^10.0.0` - CDK constructs
- Node.js 18+ for CDK development
- TypeScript ~5.2.2 for type safety

This architecture enables incremental, story-driven development with built-in human review and automated quality enforcement, replacing the previous monolithic approach with a composable, scalable pipeline system.
- Always activate venv when doing local testing and development of python applications
- virtual environment is in .venv and not venv
- look for environment variables and secrets in .env file in the project