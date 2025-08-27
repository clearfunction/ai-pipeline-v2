# S3 Path Structure Testing Guide

## Overview

This document describes the comprehensive testing approach for the updated S3 path structure in AI Pipeline v2. The system now uses `{project_name}-{date}/generated/{execution_id}/{file_path}` format across all lambdas.

## Testing Structure

### Unit Tests: `tests/unit/test_story_executor_s3_paths.py`

Tests the core S3 path functionality in the story-executor lambda:

#### Test Methods:
1. **`test_s3_path_with_project_name_and_date`** - Verifies new path format
2. **`test_backward_compatibility_fallback`** - Tests fallback to old format
3. **`test_s3_path_compatibility_with_other_lambdas`** - Cross-lambda compatibility
4. **`test_project_name_sanitization`** - Project name formatting
5. **`test_date_format_consistency`** - Date format validation
6. **`test_multiple_files_same_execution`** - Multi-file path consistency

### Integration Tests: `tests/integration/test_s3_path_compatibility.py`

Tests S3 path compatibility across all lambdas:

#### Test Methods:
1. **`test_s3_service_can_list_with_project_prefix`** - S3Service functionality
2. **`test_integration_validator_can_read_stored_files`** - Cross-lambda reading
3. **`test_github_orchestrator_can_list_stored_files`** - File listing compatibility
4. **`test_end_to_end_path_consistency`** - Complete workflow validation
5. **`test_path_format_validation`** - Path structure validation
6. **`test_cross_lambda_file_operations`** - Multi-lambda operations
7. **`test_date_consistency_across_lambdas`** - Date format consistency

## Test Dependencies

### Required Python Packages:
```bash
pip install pytest pytest-asyncio moto boto3
```

### Required Environment:
- AWS credentials configured (for moto mocking)
- Python 3.11+
- pytest with async support

## Running Tests

### Unit Tests:
```bash
# Run S3 path unit tests
source venv/bin/activate
python -m pytest tests/unit/test_story_executor_s3_paths.py -v

# Run with coverage
python -m pytest tests/unit/test_story_executor_s3_paths.py --cov=lambdas.core.story-executor -v
```

### Integration Tests:
```bash
# Run S3 path integration tests
source venv/bin/activate  
python -m pytest tests/integration/test_s3_path_compatibility.py -v

# Run all S3-related tests
python -m pytest tests/ -k "s3" -v
```

### Full Test Suite:
```bash
# Run all tests related to S3 paths
python -m pytest tests/unit/test_story_executor_s3_paths.py tests/integration/test_s3_path_compatibility.py -v
```

## Test Coverage

### Path Format Validation ✓
- Tests `{project_name}-{date}/generated/{execution_id}/{file_path}` structure
- Validates project name sanitization (spaces → hyphens, lowercase)
- Verifies date format consistency (YYYYMMDD)

### Backward Compatibility ✓
- Tests fallback to `{execution_id}/{file_path}` when project info missing
- Ensures existing deployments continue working

### Cross-Lambda Integration ✓
- **story-executor** → **integration-validator**: File validation workflows
- **story-executor** → **github-orchestrator**: File listing and commit workflows
- **Shared S3Service**: Consistent prefix-based operations

### Error Scenarios ✓
- Missing project information
- Invalid project names
- S3 access failures
- Malformed paths

## Manual Testing

### Path Structure Verification:
```bash
# Check actual S3 structure after pipeline run
aws s3 ls s3://ai-pipeline-v2-code-artifacts-{account}-{region}/

# Expected structure:
# project-name-YYYYMMDD/
#   generated/
#     execution-id-1/
#       src/App.tsx
#       package.json
#     execution-id-2/
#       src/components/Header.tsx
```

### Cross-Lambda Testing:
```bash
# Test integration-validator with stored files
./scripts/test-lambda.sh integration-validator dev

# Test github-orchestrator file listing
./scripts/test-lambda.sh github-orchestrator dev

# Monitor S3 operations
aws logs tail /aws/lambda/ai-pipeline-v2-story-executor-dev --follow | grep -i s3
```

## Implementation Changes Tested

### 1. Story Executor Updates ✓
- `_store_generated_code()` method signature updated
- S3 key construction with project-date prefix
- DynamoDB metadata includes project information
- Fallback compatibility maintained

### 2. Integration Validator Compatibility ✓
- Reads files using project-date prefix
- `validate_imports_exports()` function unchanged (already used correct paths)

### 3. GitHub Orchestrator Compatibility ✓
- Lists files using project-date prefix  
- Retrieval logic unchanged (already used correct paths)

### 4. Shared Services Compatibility ✓
- `S3Service.list_objects()` supports prefix filtering
- No changes needed (already supported required functionality)

## Regression Testing

### Critical Path Tests:
1. **Document Upload → Story Generation → File Storage**: End-to-end path consistency
2. **File Storage → Integration Validation**: Cross-component dependency checking
3. **File Storage → GitHub Commit**: Repository creation and file commits
4. **Multiple Executions**: Path isolation and organization

### Performance Impact:
- Path length increase: ~20-30 characters (minimal impact)
- S3 prefix filtering: No performance degradation
- DynamoDB queries: Additional metadata fields (minimal impact)

## Test Results Summary

When executed, these tests verify:

✅ **Path Format**: All stored files use `{project_name}-{date}/generated/{execution_id}/{file_path}`  
✅ **Cross-Lambda Compatibility**: Integration-validator and github-orchestrator can read story-executor files  
✅ **Backward Compatibility**: Old format still works when project info unavailable  
✅ **Project Name Handling**: Proper sanitization and formatting  
✅ **Date Consistency**: YYYYMMDD format used consistently  
✅ **Multi-File Operations**: Multiple files per execution use consistent paths  
✅ **Error Handling**: Graceful fallback and error reporting  

## Deployment Testing

### Pre-Deployment:
```bash
# Run all S3 path tests
python -m pytest tests/unit/test_story_executor_s3_paths.py tests/integration/test_s3_path_compatibility.py -v

# Verify no regression in existing tests
python -m pytest tests/unit/test_code_generator.py -v
```

### Post-Deployment:
```bash
# Test actual lambda deployment
./scripts/test-lambda.sh story-executor dev

# Monitor S3 path structure
aws s3 ls s3://ai-pipeline-v2-code-artifacts-$(aws sts get-caller-identity --query Account --output text)-us-east-1/ --recursive | head -20

# Verify cross-lambda operations
./scripts/test-deployment.sh sample-project dev
```

This comprehensive testing approach ensures the S3 path structure changes are thoroughly validated before and after deployment.