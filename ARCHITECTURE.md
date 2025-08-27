# AI Pipeline Orchestrator v2 - Architecture

## Overview

AI Pipeline Orchestrator v2 is a complete redesign that transforms monolithic code generation into an incremental, story-based development workflow with GitHub Actions integration and human review capabilities.

## Key Principles

1. **Story-Based Development**: Generate code incrementally through user stories rather than all-at-once
2. **GitHub Actions Integration**: Native CI/CD with GitHub-hosted runners for build and test orchestration
3. **Focused Responsibility**: 7 specialized lambdas (200-300 lines each) with single responsibilities
4. **Multi-Document Intake**: Support PDFs, transcripts, emails, chats with project-based path organization
5. **Human-in-the-Loop**: Built-in GitHub PR review workflows with automated merge capabilities
6. **Direct API Integration**: Anthropic Claude API for cost optimization and performance

## System Architecture (GitHub Actions Integration)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Document      │    │  Requirements   │    │  Architecture   │    │     Story       │
│   Processor     │───▶│  Synthesizer    │───▶│   Planner      │───▶│   Executor      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│S3 Raw Documents │    │   DynamoDB      │    │   Component     │    │S3 Code Artifacts│
│{project}-{date}/│    │ User Stories    │    │ Specifications  │    │{project}-{date}/│
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

                                              ┌─────────────────┐
                                              │  Integration    │
                                              │   Validator     │
                                              └─────────┬───────┘
                                                       │
                                              ┌─────────▼───────┐
                                              │    GitHub       │
                                              │ Orchestrator    │
                                              └─────────┬───────┘
                                                       │
                     ┌─────────────────────────────────┼─────────────────────────────────┐
                     │                                 │                                 │
                     ▼                                 ▼                                 ▼
          ┌─────────────────┐                ┌─────────────────┐                ┌─────────────────┐
          │  GitHub Repo    │                │ GitHub Actions  │                │    Review       │
          │   Creation      │                │   Workflows     │                │  Coordinator    │
          └─────────────────┘                └─────────────────┘                └─────────────────┘
                     │                                 │                                 │
                     └─────────────────────────────────┼─────────────────────────────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              │                        │                        │
                              ▼                        ▼                        ▼
                    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
                    │   Build & Test  │      │   Human Review  │      │  Automated      │
                    │   (CI/CD)       │      │   (GitHub PR)   │      │    Merge        │
                    └─────────────────┘      └─────────────────┘      └─────────────────┘
```

## Lambda Functions (GitHub Actions Integration)

### ✅ Core Pipeline (Sequential) - COMPLETED

#### 1. Document Processor (200 lines) ✅
- **Purpose**: Multi-format document intake with versioning
- **Input**: PDFs, JSON transcripts, emails, chat logs, text files
- **Output**: Processed text with metadata and project-based path organization
- **Storage**: S3 processed bucket `{project-name}-{date}/processed/`

#### 2. Requirements Synthesizer (250 lines) ✅
- **Purpose**: Extract and consolidate requirements into user stories
- **Input**: Processed documents from multiple sources
- **Output**: Prioritized user stories with acceptance criteria
- **AI Integration**: Direct Anthropic Claude API for requirement analysis

#### 3. Architecture Planner (300 lines) ✅
- **Purpose**: Design tech stack and component architecture
- **Input**: User stories and requirements
- **Output**: Tech stack selection, component specifications, build config
- **Decision Logic**: React SPA, React Fullstack, Node API, Python API, Vue SPA

#### 4. Story Executor (435 lines) ✅
- **Purpose**: AI-powered incremental code generation
- **Input**: User story with component specifications
- **Output**: Generated code files with intelligent template vs AI routing
- **AI Integration**: Context-aware code generation with multi-tech-stack support
- **Storage**: S3 code artifacts bucket `{project-name}-{date}/generated/`

### 🔄 GitHub Integration Lambdas (Sequential) - IN PROGRESS

#### 5. Integration Validator (200 lines) ❌
- **Purpose**: Cross-component validation and GitHub repository setup
- **Input**: Generated components and their dependencies
- **Output**: Validation results, GitHub repository configuration
- **Functions**: Import/export consistency, GitHub Actions workflow generation
- **GitHub Integration**: Repository creation, workflow file generation

#### 6. GitHub Orchestrator (250 lines) ❌
- **Purpose**: GitHub repository management and build orchestration
- **Input**: Validated components and GitHub repository configuration
- **Output**: GitHub repository with code commits and Actions triggers
- **Functions**: Branch creation, code commits, GitHub Actions monitoring
- **GitHub Integration**: Repository management, build result collection

#### 7. Review Coordinator (200 lines) ❌
- **Purpose**: Human review workflow via GitHub PRs
- **Input**: Build results and code artifacts
- **Output**: GitHub PR with automated or human review coordination
- **Functions**: PR creation, review status tracking, automated merge
- **GitHub Integration**: Pull request management, review workflow coordination

### ❌ Removed Lambdas (Replaced by GitHub Actions)
- ~~Story Manager~~ → Functionality integrated into Story Executor
- ~~Component Generator~~ → Functionality integrated into Story Executor
- ~~Build Orchestrator~~ → Replaced by GitHub Actions workflows
- ~~Claude Agent Dispatcher~~ → Simplified to GitHub PR-based review
- ~~Quality Enforcer~~ → Integrated into GitHub Actions workflows

## Data Flow (GitHub Actions Integration)

### Phase 1: Intake & Planning (Sequential)
```
Multi-Document Input → Document Processing → Requirements Synthesis → Architecture Planning
                ↓                   ↓                     ↓                    ↓
        S3 Raw Storage → S3 Processed Storage → DynamoDB Stories → Component Specs
        {project}-{date}/  {project}-{date}/     Priority Queue     Tech Stack Config
```

### Phase 2: Story Execution (AI-Powered)
```
Story Executor: User Stories → AI Code Generation → Component Files
                     ↓                ↓                  ↓
              Template vs AI     Multi-Tech Stack    S3 Code Storage
              Decision Logic     Support (React,     {project}-{date}/
                                Node, Python, Vue)   generated/
```

### Phase 3: GitHub Integration (Automated)
```
Integration Validator → GitHub Orchestrator → Review Coordinator
        ↓                      ↓                      ↓
Cross-Component           Repository Creation     GitHub PR Creation
    Validation           GitHub Actions Setup      Human Review
        ↓                      ↓                      ↓
Workflow Generation      Build & Test Execution   Automated Merge
```

### Phase 4: Build & Test (GitHub Actions)
```
GitHub Repository → GitHub Actions Workflows → Build Results
        ↓                    ↓                      ↓
    Code Commit         Tech Stack Specific       Status Report
   Branch Creation      Workflows (React,         Back to AWS
                       Node, Python)
```

## Technology Stack

### Infrastructure
- **AWS Step Functions**: Workflow orchestration
- **AWS Lambda**: Serverless compute (Python 3.11)
- **AWS S3**: Document and artifact storage with project-based paths
- **AWS DynamoDB**: Metadata and state management
- **AWS CDK**: Infrastructure as Code (TypeScript)
- **GitHub Actions**: CI/CD and build orchestration

### AI & LLM Integration
- **Anthropic Claude API**: Direct API integration (primary)
- **Models**: Claude 3.5 Sonnet (primary), Claude 3 Haiku (fast), Claude 3 Opus (powerful)
- **Intelligent Routing**: Model selection based on task complexity
- **Cost Optimization**: Direct API calls, custom caching, usage monitoring

### Development Runtime
- **Python 3.11**: Lambda runtime with shared layers
- **Pydantic**: Data validation and serialization
- **Loguru**: Structured logging with execution tracing
- **Boto3**: AWS SDK with optimized connection pooling
- **PyPDF**: Multi-format document processing

### GitHub Integration
- **GitHub API**: Repository management and PR workflows
- **GitHub Actions**: Build and test orchestration
- **GitHub Webhooks**: Build status reporting back to AWS
- **GitHub App**: Secure authentication and permissions

### Build & Test Orchestration
- **React SPA**: Node.js 18, npm, TypeScript, Jest, Coverage reporting
- **Node API**: Node.js 18, npm, integration tests, security auditing
- **Python API**: Python 3.11, Poetry, mypy, pytest, bandit security
- **Vue SPA**: Node.js 18, npm, Vue CLI, unit and component testing

## Storage Design (Project-Based Organization)

### S3 Buckets
- **Raw Documents**: `ai-pipeline-v2-raw-{account}-{region}`
  - Path: `{project-name}-{date}/raw/{filename}`
  - Multi-format document intake with versioning
- **Processed Content**: `ai-pipeline-v2-processed-{account}-{region}`
  - Path: `{project-name}-{date}/processed/{execution-id}/{doc-id}.txt`
  - Processed text with metadata and lineage tracking
- **Code Artifacts**: `ai-pipeline-v2-code-artifacts-{account}-{region}` (NEW)
  - Path: `{project-name}-{date}/generated/{execution-id}/{file-path}`
  - Generated code files and project structure
- **Vector Store**: `ai-pipeline-v2-vectors-{account}-{region}`
  - Path: `{project-name}-{date}/vectors/{embedding-type}`
  - Document embeddings for semantic search

### DynamoDB Tables
- **Document Metadata**: Version tracking and lineage with project organization
- **User Stories**: Story definitions with status and priority queuing
- **Component Specs**: Component architecture and dependencies mapping
- **GitHub Integrations**: Repository and branch tracking (NEW)
- **Build Results**: GitHub Actions build status and results (NEW)
- **Execution State**: Pipeline execution tracking with GitHub workflow IDs

## Workflow Orchestration (GitHub Actions Integration)

### Main Pipeline (Step Functions)
```json
{
  "Comment": "AI Pipeline Orchestrator v2 with GitHub Actions Integration",
  "StartAt": "DocumentProcessor",
  "States": {
    "DocumentProcessor": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-document-processor-${env}",
      "Next": "RequirementsSynthesizer"
    },
    "RequirementsSynthesizer": {
      "Type": "Task", 
      "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-requirements-synthesizer-${env}",
      "Next": "ArchitecturePlanner"
    },
    "ArchitecturePlanner": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-architecture-planner-${env}",
      "Next": "StoryExecutor"
    },
    "StoryExecutor": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-story-executor-${env}",
      "TimeoutSeconds": 900,
      "Next": "GitHubIntegration"
    },
    "GitHubIntegration": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "IntegrationValidator",
          "States": {
            "IntegrationValidator": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-integration-validator-${env}",
              "End": true
            }
          }
        },
        {
          "StartAt": "GitHubOrchestrator", 
          "States": {
            "GitHubOrchestrator": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-github-orchestrator-${env}",
              "End": true
            }
          }
        }
      ],
      "Next": "ReviewCoordinator"
    },
    "ReviewCoordinator": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${region}:${account}:function:ai-pipeline-v2-review-coordinator-${env}",
      "End": true
    }
  }
}
```

### GitHub Actions Workflows (Generated by Integration Validator)
- **React SPA Workflow**: TypeScript, Jest, ESLint, build validation
- **Node API Workflow**: Node.js testing, security audit, API validation
- **Python API Workflow**: pytest, mypy, bandit, coverage reporting
- **Vue SPA Workflow**: Vue CLI, unit testing, component testing

## Security & Compliance

### IAM Permissions
- **Principle of Least Privilege**: Each lambda has minimal required permissions
- **Resource-Scoped**: Permissions limited to specific S3 buckets and DynamoDB tables
- **API Key Management**: Anthropic API keys stored in AWS Secrets Manager
- **GitHub Integration**: GitHub App tokens with scoped repository permissions

### External API Security
- **Anthropic API**: Direct API integration with key rotation and usage monitoring
- **GitHub API**: OAuth app with minimal repository permissions
- **API Key Rotation**: Automated 30-day rotation cycle
- **Rate Limiting**: Built-in rate limiting and request throttling
- **Usage Monitoring**: API usage tracking and anomaly detection

### Data Protection
- **Encryption at Rest**: S3 and DynamoDB encryption enabled
- **Encryption in Transit**: TLS 1.3 for all API communications
- **Version Control**: Document lineage and change tracking
- **Access Logging**: CloudTrail for audit compliance
- **Data Residency**: Configurable data residency controls for compliance
- **Sensitive Data Redaction**: Request/response logging with PII redaction

## Scalability & Performance

### Concurrency
- **Sequential Core Pipeline**: Document processing through story execution
- **Parallel GitHub Integration**: Integration validation and orchestration run in parallel
- **Independent Lambda Scaling**: Each function scales based on demand
- **GitHub Actions Scaling**: Unlimited concurrent builds with GitHub-hosted runners

### Cost Optimization
- **Pay-per-Use**: Serverless architecture with no idle costs
- **Direct API Integration**: 10-15% savings over AWS Bedrock markup
- **GitHub Actions**: Free for public repos, $0.008/minute for private repos
- **Efficient Packaging**: Shared layers reduce deployment size
- **AI Cost Management**: Intelligent model routing and usage monitoring
- **Project-Based Storage**: Lifecycle policies for cost-effective storage management

## Monitoring & Observability

### Logging
- **Structured Logging**: JSON format with execution context and project correlation
- **CloudWatch Integration**: Centralized log aggregation with project-based filtering
- **Execution Tracing**: Request ID tracking across AWS and GitHub integrations
- **GitHub Actions Logs**: Build and test logs accessible via GitHub API

### Metrics
- **Lambda Metrics**: Duration, errors, concurrent executions, memory utilization
- **Custom Metrics**: Story completion rate, GitHub build success rate, AI decision accuracy
- **GitHub Actions Metrics**: Build duration, test success rate, workflow efficiency
- **API Usage Metrics**: Anthropic API calls, costs, and performance
- **Cost Tracking**: Per-lambda, per-project, and per-execution cost analysis

### Alerting
- **Error Rate**: Lambda function failure alerts with GitHub integration status
- **Execution Time**: Performance degradation alerts across pipeline stages
- **Build Failure**: GitHub Actions build failure notifications
- **API Rate Limits**: Anthropic API rate limiting and quota alerts
- **Cost Thresholds**: Budget alerts for AI usage and GitHub Actions consumption

## Deployment Strategy

### Environment Management
- **Development**: Individual developer environments with GitHub integration testing
- **Staging**: Full pipeline testing with real GitHub repositories
- **Production**: Live customer environment with production GitHub App

### Deployment Process
1. **Infrastructure**: CDK deployment of AWS resources (S3, DynamoDB, Lambda)
2. **GitHub App Setup**: Production GitHub App with repository permissions
3. **Shared Layer**: Common utilities, models, and GitHub API clients
4. **Lambda Functions**: Individual function deployment with GitHub integration
5. **GitHub Workflow Templates**: Deployment of workflow templates to S3
6. **Integration Testing**: End-to-end pipeline with real GitHub repositories
7. **Rollback**: Automated rollback with GitHub repository cleanup

### CI/CD Integration
- **GitHub Actions**: Automated testing and deployment of pipeline infrastructure
- **Feature Branches**: Isolated development with test GitHub repositories
- **Blue/Green**: Zero-downtime production deployments with GitHub failover
- **Infrastructure as Code**: CDK for AWS resources and GitHub repository templates

## Benefits of GitHub Actions Integration

### Developer Experience
- **Familiar Interface**: Developers work with GitHub's native PR and build interface
- **Rich Ecosystem**: Access to 1000+ GitHub Actions for extended functionality
- **Community Support**: Extensive documentation and community contributions
- **Native CI/CD**: Built-in deployment pipelines and artifact management

### Cost & Operational Benefits
- **Zero Infrastructure**: No build servers to manage, scale, or maintain
- **Cost Effective**: Free for public repositories, predictable pricing for private
- **Scalable**: Unlimited concurrent builds with GitHub-hosted runners
- **Reduced Complexity**: Eliminates custom build orchestration and Lambda infrastructure

### Integration Advantages
- **Native PR Workflow**: Built-in code review, approval, and merge capabilities
- **Build Status Integration**: Real-time build status visible in GitHub interface
- **Webhook Architecture**: Efficient event-driven communication back to AWS
- **Security**: GitHub App model provides secure, scoped repository access

## Key Differences from v1

1. **Architecture Scale**: 7 focused lambdas vs 10+ originally planned
2. **Build Strategy**: GitHub Actions vs custom AWS Lambda/ECS orchestration
3. **AI Integration**: Direct Anthropic API vs AWS Bedrock with fallbacks
4. **Storage Organization**: Project-based `{project-name}-{date}` paths vs execution-based
5. **Human Review**: Native GitHub PR workflow vs external tooling
6. **Cost Model**: Direct API pricing vs AWS markup and infrastructure overhead
7. **Developer Experience**: GitHub-native interface vs custom dashboards and tooling

This architecture provides a scalable, maintainable, and cost-effective foundation for AI-assisted development workflows while leveraging the mature GitHub ecosystem for build, test, and review processes.