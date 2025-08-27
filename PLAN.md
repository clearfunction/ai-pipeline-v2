# AI Pipeline Orchestrator v2 - Implementation Plan

## Architecture Overview

AI Pipeline Orchestrator v2 transforms monolithic code generation into an incremental, story-based development workflow with GitHub Actions integration and human review capabilities.

## Current State Analysis

The v1 system used a monolithic code_scaffolding lambda (6,300+ lines) that attempted to generate entire projects at once, leading to:
- File loss during processing (41 → 13 files)
- Complex error handling and self-healing
- Validation mismatches between frontend/backend
- ESLint integration gaps

## New Story-Based Architecture

Replace monolithic generation with incremental story-based development using focused, single-responsibility lambdas with GitHub Actions for build orchestration.

## Lambda Architecture (GitHub Actions Integration)

### ✅ Core Pipeline Lambdas (Sequential) - COMPLETED

1. ✅ **document-processor** (200 lines)
   - Multi-format intake: PDFs, JSON transcripts, emails, chats
   - Version tracking and lineage with project-based paths: `{project-name}-{date}/`
   - S3 storage with metadata

2. ✅ **requirements-synthesizer** (250 lines)
   - Enhanced PRD generation from multi-document inputs
   - User story extraction and prioritization
   - Dependencies mapping with Anthropic Claude integration

3. ✅ **architecture-planner** (300 lines)
   - Tech stack determination with intelligent routing
   - Component architecture design
   - Story-to-component mapping

4. ✅ **story-executor** (435 lines)
   - AI-powered incremental code generation
   - Intelligent template vs AI decision logic
   - Multi-tech-stack support (React SPA, Node API, Python API, Vue SPA)
   - Quality validation and code generation

### 🔄 GitHub Integration Lambdas (Sequential) - IN PROGRESS

5. ❌ **integration-validator** (200 lines)
   - Cross-component validation and consistency checks
   - GitHub repository setup and configuration
   - Workflow file generation for GitHub Actions

6. ❌ **github-orchestrator** (250 lines)
   - GitHub repository management and branch creation
   - Code commit and GitHub Actions triggering
   - Build monitoring and result collection

7. ❌ **review-coordinator** (200 lines)
   - Human review workflow via GitHub PRs
   - Review status tracking and coordination
   - Automated merge based on configuration

### ❌ Removed Lambdas (No Longer Needed)
- ~~story-manager~~ (functionality integrated into story-executor)
- ~~component-generator~~ (functionality integrated into story-executor)  
- ~~build-orchestrator~~ (replaced by GitHub Actions)
- ~~claude-agent-dispatcher~~ (simplified to review-coordinator)
- ~~quality-enforcer~~ (integrated into GitHub Actions workflows)

## Build and Test Strategy: GitHub Actions

### Platform Selection
- **Build Environment**: GitHub-hosted runners (ubuntu-latest)
- **Caching**: Native GitHub Actions caching (npm, poetry, etc.)
- **Multi-Stack Support**: Separate workflows for React, Node, Python
- **Integration**: Results reported back to AWS via Lambda
- **Cost**: Free for public repos, $0.008/minute for private repos

### Workflow Templates
- **React SPA**: Node.js 18, npm, TypeScript, Jest, Coverage
- **Node API**: Node.js 18, npm, integration tests, security audit
- **Python API**: Python 3.11, Poetry, mypy, pytest, bandit

### Advantages over AWS Lambda/ECS
- Zero infrastructure management
- Rich ecosystem (1000+ Actions)
- Familiar developer experience
- Built-in artifact storage and caching
- Community support and documentation

## Infrastructure as Code Design

### Composable CDK Structure

```
infrastructure/
├── lib/
│   ├── core/
│   │   ├── storage-stack.ts         # S3, DynamoDB (updated)
│   │   ├── iam-stack.ts             # Roles and policies
│   │   └── networking-stack.ts      # VPC (if needed)
│   ├── lambdas/
│   │   ├── pipeline-lambdas.ts      # Core sequential lambdas
│   │   ├── story-lambdas.ts         # Story + GitHub integration
│   │   └── review-lambdas.ts        # Review coordination
│   ├── workflows/
│   │   ├── main-pipeline.ts         # Updated Step Functions
│   │   └── github-workflows.ts      # GitHub Actions templates
│   └── shared/
│       ├── lambda-config.ts         # Common lambda configuration
│       └── github-config.ts         # GitHub API configuration
├── bin/
│   └── ai-pipeline-v2.ts           # CDK app entry point
└── scripts/
    ├── deploy-single.sh             # Individual lambda deployment
    ├── deploy-all.sh                # Full stack deployment
    └── test-lambda.sh               # Individual lambda testing
```

## Storage Design (Updated)

### S3 Buckets (Project-Based Organization)
- **Raw Documents**: `ai-pipeline-v2-raw-{account}-{region}`
  - Path: `{project-name}-{date}/raw/{filename}`
- **Processed Content**: `ai-pipeline-v2-processed-{account}-{region}`
  - Path: `{project-name}-{date}/processed/{execution-id}/{doc-id}.txt`
- **Code Artifacts**: `ai-pipeline-v2-code-artifacts-{account}-{region}` (NEW)
  - Path: `{project-name}-{date}/generated/{execution-id}/{file-path}`

### DynamoDB Tables (Updated)
- **Document Metadata**: Version tracking and lineage
- **User Stories**: Story definitions and status
- **Component Specs**: Component architecture and dependencies
- **GitHub Integrations**: Repository and branch tracking (NEW)
- **Build Results**: GitHub Actions build status and results (NEW)

## Step Functions Workflow Design (Updated)

### Main Pipeline (Sequential)
```
Document Processing → Requirements → Architecture → Story Execution
    ↓
Integration Validation → GitHub Orchestration → Review Coordination
    ↓
Human Review (Optional) → Automated Merge → Completion
```

### GitHub Actions Integration
- **Trigger**: Lambda creates repository and commits code
- **Build**: GitHub Actions runs tech-stack specific workflows
- **Report**: Results sent back to AWS via webhook/Lambda
- **Review**: Human review via GitHub PR interface

## LLM Provider Configuration

### Direct Anthropic API Integration

```python
llm_config = {
    "provider": "anthropic",
    "models": {
        "primary": "claude-3-5-sonnet-20241022",
        "fast": "claude-3-haiku-20240307",
        "powerful": "claude-3-opus-20240229"
    },
    "intelligent_routing": {
        "document_processing": "fast",
        "requirements_synthesis": "primary",
        "architecture_planning": "powerful",
        "component_generation": "primary",
        "code_review": "primary"
    },
    "connection_config": {
        "timeout": 120,
        "max_retries": 3,
        "retry_delay": [1, 2, 4],
        "connection_pool_size": 50
    },
    "cost_optimization": {
        "enable_caching": True,
        "cache_ttl_minutes": 60,
        "batch_processing": True,
        "usage_monitoring": True
    }
}
```

## Development Workflow

### Local Development
```bash
# Individual lambda development
cd ai-pipeline-v2/lambdas/integration-validator
python -m pytest tests/
./scripts/deploy-single.sh integration-validator

# Full system testing
./scripts/deploy-all.sh --env dev
python scripts/test-github-workflow.py
```

### Testing Strategy
- **Unit Tests**: Each lambda function (pytest)
- **Integration Tests**: GitHub workflow integration
- **End-to-End Tests**: Complete pipeline with real repositories
- **Performance Tests**: Large story sets and build times

## Cost Analysis: Anthropic API vs AWS Bedrock

### Direct Anthropic API Benefits
- **Cost Reduction**: 10-15% savings by eliminating AWS markup
- **Transparent Pricing**: Direct per-token pricing without service fees
- **Usage Optimization**: Custom batching and caching strategies
- **No Infrastructure Overhead**: Eliminates API Gateway, VPC, and service costs

### Cost Comparison (per 1M tokens)
- **Anthropic Direct**: $3.00 (Claude 3 Sonnet)
- **AWS Bedrock**: $3.50-4.00 (with AWS markup and service costs)
- **Monthly Savings**: $500-1000 for typical enterprise usage

### GitHub Actions Cost Comparison
- **Public Repositories**: Free (2,000 minutes/month)
- **Private Repositories**: $0.008/minute
- **vs AWS ECS**: $0.04048 per build (10 min avg)
- **Monthly (1000 builds)**: GitHub: $80 (private) / Free (public) vs AWS: $41

## Security Architecture for External API Integration

### API Key Management
- Store Anthropic API keys in AWS Secrets Manager
- Implement automatic key rotation (30-day cycle)
- Use IAM roles for Lambda access to secrets
- Monitor API key usage and detect anomalies

### GitHub Integration Security
- GitHub App with minimal required permissions
- Webhook signature validation
- Rate limiting to prevent abuse
- Audit trails for all repository operations

### Data Protection
- No data persistence in external API calls
- Request/response logging with sensitive data redaction
- Implement data residency controls if required
- Audit trails for all API interactions

## Implementation Phases

### Phase 1 (Week 1): Complete Missing Lambdas
- Implement integration-validator lambda
- Implement github-orchestrator lambda  
- Implement review-coordinator lambda
- Unit testing for all new functions

### Phase 2 (Week 2): GitHub Actions Templates
- Create workflow templates for React SPA, Node API, Python API
- Implement build result reporting back to AWS
- Set up GitHub App permissions and webhooks
- Test GitHub repository creation and management

### Phase 3 (Week 3): Infrastructure Updates
- Deploy new S3 bucket for code artifacts
- Deploy new DynamoDB tables for GitHub integration
- Update Step Functions workflow
- Update existing lambdas with new S3 paths

### Phase 4 (Week 4): Integration Testing
- End-to-end testing with real GitHub repositories
- Build and test validation across tech stacks
- Human review workflow testing
- Performance testing and optimization

### Phase 5 (Week 5): Production Deployment
- Production infrastructure deployment
- Security validation and penetration testing
- Documentation and operational runbooks
- Monitoring and alerting setup

## Benefits of GitHub Actions Integration

1. **Developer Experience**: Familiar GitHub interface for code review and builds
2. **Ecosystem Integration**: 1000+ Actions available for extended functionality  
3. **Cost Effective**: Free for public repos, predictable pricing for private
4. **Zero Infrastructure**: No build servers to manage or scale
5. **Native CI/CD**: Built-in deployment pipelines and artifact management
6. **Community Support**: Extensive documentation and community contributions

## Key Differences from v1

1. **Granular Responsibility**: 7 focused lambdas vs 1 monolithic
2. **GitHub Integration**: Native PR workflow vs external tooling
3. **Build Strategy**: GitHub Actions vs custom Lambda orchestration
4. **Human-in-Loop**: Built-in PR review vs post-generation review
5. **Multi-Document**: PDF/transcript support vs single input
6. **Project Organization**: `{project-name}-{date}` path structure
7. **Direct API Integration**: Anthropic-only vs multi-provider complexity

## Migration Strategy

Since no backward compatibility is required:
- Clean slate development in ai-pipeline-v2/
- Separate AWS resources (new buckets, functions, etc.)
- Independent testing and validation
- Direct Anthropic API integration from day one
- GitHub Actions integration from the start
- Simplified deployment without complex fallbacks

This architecture maintains the scalable, maintainable foundation for AI-assisted development workflows while providing an excellent developer experience through GitHub integration and eliminating the complexity of custom build infrastructure.