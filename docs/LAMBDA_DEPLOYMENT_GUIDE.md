# Lambda Deployment Guide

## Overview

This guide explains the deployment strategies for Lambda functions in the AI Pipeline v2 project. Different Lambda functions use different deployment methods based on their requirements and dependencies.

## Deployment Methods

### 1. Layer-Based Deployment
**Used by:** document-processor, requirements-synthesizer, architecture-planner, review-coordinator, pr-status-checker

These Lambda functions use shared Lambda layers for their dependencies:
- **shared-models-layer**: Contains data models and utilities (no external dependencies)
- **shared-ai-services-layer**: Contains AI service dependencies (requests, anthropic, boto3, pydantic)

**How to deploy:**
```bash
./scripts/deploy-single.sh <lambda-name> <environment>
# Example:
./scripts/deploy-single.sh review-coordinator dev
```

### 2. CDK-Bundled Deployment
**Used by:** github-orchestrator

This Lambda is fully managed by CDK, which handles all dependency bundling during deployment.

**⚠️ WARNING:** DO NOT use deploy-single.sh for this Lambda!

**How to deploy:**
```bash
# Option 1: Full CDK deployment (recommended)
cd infrastructure
npm run deploy-dev

# Option 2: Emergency code-only update
./scripts/deploy-github-orchestrator.sh dev
```

### 3. Isolated Deployment
**Used by:** story-executor, integration-validator

These Lambda functions run independently:
- **story-executor**: Bundles its own dependencies
- **integration-validator**: Uses only Python standard library

**How to deploy:**
```bash
./scripts/deploy-single.sh <lambda-name> <environment>
# Example:
./scripts/deploy-single.sh story-executor dev
```

## Deployment Configuration

All Lambda deployment configurations are stored in `scripts/lambda-deployment-config.json`. This file defines:
- Deployment method for each Lambda
- Layer dependencies
- CDK-managed status
- Special warnings and notes

## Protection Mechanisms

### CDK-Bundled Lambda Protection
The deployment scripts include protection to prevent accidentally breaking CDK-bundled Lambdas:

```bash
# This will be blocked with an error
./scripts/deploy-single.sh github-orchestrator dev
# ERROR: Cannot deploy github-orchestrator using deploy-single.sh
```

### Layer Dependency Management
For Lambdas using shared layers, the deployment script automatically:
1. Detects layer usage from configuration
2. Excludes layer-provided dependencies from the deployment package
3. Creates minimal packages with only Lambda-specific code

## Best Practices

### DO ✅
- Always use the correct deployment method for each Lambda
- Check `lambda-deployment-config.json` if unsure about deployment method
- Use CDK for infrastructure changes
- Test Lambda functions after deployment

### DON'T ❌
- Never use `deploy-single.sh` for CDK-bundled Lambdas
- Don't manually install dependencies in Lambda directories
- Don't bypass the protection mechanisms
- Don't modify layer structure without updating all dependent Lambdas

## Troubleshooting

### "No module named 'requests'" Error
**Cause:** Lambda layers not properly attached or structured incorrectly

**Solution:**
1. Check layer attachment:
```bash
aws lambda get-function-configuration --function-name <function-name> \
  --query 'Layers[*].Arn' --output json
```

2. Verify layer structure (must have `python/` directory):
```bash
# Download and inspect layer
aws lambda get-layer-version --layer-name <layer-name> --version-number <version>
```

3. Redeploy infrastructure if needed:
```bash
cd infrastructure
npm run deploy-dev
```

### CDK-Bundled Lambda Broken After Manual Deployment
**Cause:** Used `deploy-single.sh` on a CDK-managed Lambda

**Solution:**
1. Redeploy with CDK:
```bash
cd infrastructure
npm run deploy-dev
```

2. Or use the specialized script:
```bash
./scripts/deploy-github-orchestrator.sh dev
```

### Layer Dependencies Not Found
**Cause:** Dependencies installed in wrong location or layer not updated

**Solution:**
1. Ensure dependencies are in `python/` directory within layer
2. Redeploy the layer through CDK
3. Verify Lambda is using the latest layer version

## Layer Management

### Updating Shared Layers

To update dependencies in shared layers:

1. **Update requirements in layer directory:**
```bash
cd shared-ai-services-layer
# Edit requirements.txt
pip install -r requirements.txt -t python/
```

2. **Deploy through CDK:**
```bash
cd infrastructure
npm run deploy-dev
```

3. **Verify layer version updated:**
```bash
aws lambda list-layer-versions --layer-name ai-pipeline-v2-shared-ai-services-dev
```

## Deployment Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy-single.sh` | Deploy individual Lambdas (except CDK-bundled) | `./scripts/deploy-single.sh <lambda> <env>` |
| `deploy-all.sh` | Deploy all eligible Lambdas | `./scripts/deploy-all.sh <env>` |
| `deploy-github-orchestrator.sh` | Emergency deployment for GitHub Orchestrator | `./scripts/deploy-github-orchestrator.sh <env>` |
| CDK deployment | Full infrastructure deployment | `cd infrastructure && npm run deploy-<env>` |

## Environment Variables

All Lambda functions have access to these environment variables:
- `ENVIRONMENT`: Current environment (dev/staging/prod)
- `AWS_REGION`: AWS region
- `LOG_LEVEL`: Logging verbosity
- Secret ARNs for various services (GitHub, Anthropic, etc.)
- S3 bucket names
- DynamoDB table names

## Monitoring Deployments

After deployment, monitor your Lambda functions:

```bash
# View logs
aws logs tail /aws/lambda/<function-name> --follow

# Check function configuration
aws lambda get-function-configuration --function-name <function-name>

# Test function
aws lambda invoke --function-name <function-name> \
  --cli-binary-format raw-in-base64-out \
  --payload '{"test": true}' response.json
```

## Configuration File Structure

The `lambda-deployment-config.json` file structure:

```json
{
  "lambdas": {
    "<lambda-name>": {
      "path": "relative/path/to/lambda",
      "deployment_method": "layer|cdk_bundled|isolated",
      "uses_layers": true|false,
      "cdk_managed": true|false,
      "warning": "Optional warning message",
      "description": "Lambda description"
    }
  },
  "layers": {
    "<layer-name>": {
      "path": "relative/path/to/layer",
      "description": "Layer description"
    }
  }
}
```

This configuration ensures consistent and safe deployments across all Lambda functions in the project.