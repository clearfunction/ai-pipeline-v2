# Deployment Updates - AI Pipeline v2

## 2025-08-27: PyNaCl Lambda Layer Architecture Update

### Background
The GitHub orchestrator Lambda function requires PyNaCl (libsodium) for encrypting repository secrets as per GitHub API requirements. The CDK auto-bundling was installing ARM64 binaries on M1/M2 Macs, causing runtime failures on AWS Lambda's x86_64 environment.

### Solution Implementation

#### 1. PyNaCl Layer Creation
Created a dedicated Lambda layer with PyNaCl compiled specifically for x86_64 architecture:

**Location**: `/layers/pynacl/`
- `build-layer.sh` - Build script using Docker with explicit platform targeting
- `pynacl-layer.zip` - Compiled layer package (2.1MB)

**Build Process**:
```bash
cd layers/pynacl
./build-layer.sh
```

The script:
- Uses AWS SAM build image with `--platform linux/amd64`
- Installs PyNaCl with `--platform manylinux2014_x86_64 --only-binary=:all:`
- Includes all required dependencies (cffi, pycparser)
- Tests the import within the container to verify compilation

#### 2. CDK Infrastructure Updates

**File**: `infrastructure/lib/lambdas/story-lambdas.ts`

**Changes**:
1. Added PyNaCl layer definition:
```typescript
const pynaclLayer = new lambda.LayerVersion(this, 'PyNaClLayer', {
  layerVersionName: `ai-pipeline-v2-pynacl-${props.environment}`,
  description: 'PyNaCl with libsodium for GitHub secrets encryption (x86_64)',
  code: lambda.Code.fromAsset('../layers/pynacl/pynacl-layer.zip'),
  compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
  compatibleArchitectures: [lambda.Architecture.X86_64],
});
```

2. Updated GitHub orchestrator to use the layer:
```typescript
layers: [
  ...githubOrchestratorConfig.layers,
  pynaclLayer
],
architecture: lambda.Architecture.X86_64, // Explicitly set architecture
```

3. Modified bundling command to exclude PyNaCl:
```bash
pip install -r requirements.txt --no-deps -t /asset-output && 
pip install requests -t /asset-output && 
cp -au . /asset-output
```

#### 3. Lambda Function Updates

**File**: `lambdas/story-execution/github-orchestrator/lambda_function.py`

**Changes**:
- Removed base64 fallback in `_encrypt_secret_for_github()` method
- Now properly fails with clear error if PyNaCl is not available
- No fallback because GitHub API mandates libsodium encryption

### Deployment Steps

#### Full Deployment (New Environment)
```bash
# 1. Build the PyNaCl layer
cd layers/pynacl
./build-layer.sh

# 2. Deploy infrastructure with the new layer
cd infrastructure
npm run deploy-dev

# 3. Deploy the updated Lambda functions
cd ../
./scripts/deploy-all.sh dev
```

#### Update Existing Deployment
```bash
# 1. Build the PyNaCl layer if not exists
cd layers/pynacl
./build-layer.sh

# 2. Update CDK stack (creates/updates the layer)
cd infrastructure
npx cdk deploy "*StoryLambdas*" --require-approval never

# 3. Force update of GitHub orchestrator
aws lambda update-function-configuration \
  --function-name ai-pipeline-v2-github-orchestrator-dev \
  --architectures x86_64

# 4. Test the updated function
./scripts/test-lambda.sh github-orchestrator dev test-data/github-orchestrator-test.json
```

### Verification

#### Test PyNaCl Encryption
```bash
# Test that PyNaCl is working correctly
aws lambda invoke \
  --function-name ai-pipeline-v2-github-orchestrator-dev \
  --payload '{"test": "pynacl_verification"}' \
  response.json

# Check logs for successful PyNaCl import
aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-dev --follow | grep PyNaCl
```

#### Expected Output
```
✅ Using PyNaCl for GitHub secrets encryption
✅ Successfully encrypted secret for GitHub repository
```

### Architecture Decisions

1. **Why a separate layer?**
   - Ensures consistent x86_64 compilation regardless of development machine
   - Reduces Lambda package size by sharing the layer
   - Allows independent updates of PyNaCl without redeploying functions

2. **Why remove base64 fallback?**
   - GitHub API rejects base64-encoded values as invalid
   - Proper libsodium encryption is mandatory, not optional
   - Clear failures are better than silent encryption failures

3. **Why explicit x86_64 architecture?**
   - AWS Lambda Python runtime is x86_64
   - Prevents architecture mismatches from ARM64 development machines
   - Ensures compatibility with all Lambda features

### Troubleshooting

#### Issue: PyNaCl import still failing
**Solution**: Ensure the Lambda function has x86_64 architecture set:
```bash
aws lambda get-function-configuration \
  --function-name ai-pipeline-v2-github-orchestrator-dev \
  --query 'Architectures'
# Should output: ["x86_64"]
```

#### Issue: Layer not attached to function
**Solution**: Verify layer attachment:
```bash
aws lambda get-function-configuration \
  --function-name ai-pipeline-v2-github-orchestrator-dev \
  --query 'Layers[].Arn'
# Should include the PyNaCl layer ARN
```

#### Issue: Old bundled PyNaCl conflicts
**Solution**: Clear and rebuild:
```bash
cd lambdas/story-execution/github-orchestrator
rm -rf __pycache__ *.pyc
# Redeploy the function
```

### Benefits

✅ **Reliability**: No more architecture-related failures  
✅ **Security**: Proper encryption for GitHub secrets  
✅ **Maintainability**: Centralized PyNaCl management via layer  
✅ **Performance**: Reduced Lambda cold start with shared layer  
✅ **Consistency**: Same PyNaCl version across all deployments  

### Migration from Previous Version

If migrating from the bundled version:

1. **Remove PyNaCl from requirements.txt** in github-orchestrator
2. **Build and deploy the layer** using the steps above
3. **Update CDK and redeploy** to attach the layer
4. **Test thoroughly** with actual GitHub repository creation

### Related Files

- `/layers/pynacl/build-layer.sh` - Layer build script
- `/infrastructure/lib/lambdas/story-lambdas.ts` - CDK configuration
- `/lambdas/story-execution/github-orchestrator/lambda_function.py` - Updated encryption method
- `/scripts/deploy-all.sh` - Deployment automation
- `/test-data/github-orchestrator-test.json` - Test payload

### Next Steps

1. Monitor CloudWatch logs for any PyNaCl-related errors
2. Consider creating similar layers for other binary dependencies
3. Document layer versioning strategy for production updates