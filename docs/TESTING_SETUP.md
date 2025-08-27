# Testing Environment Setup & Manual Testing Guide

## Overview

This guide covers the setup and execution of testing environments for generated applications from AI Pipeline Orchestrator v2. The focus is on dev environment deployment with manual testing capabilities, designed to be extensible for future Playwright-based UAT automation.

## Quick Start

### 1. Prerequisites Setup

```bash
# 1. Configure AWS credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key" 
export AWS_DEFAULT_REGION="us-east-1"

# 2. Set up secrets in AWS Secrets Manager
./scripts/setup-secrets.sh dev

# 3. Deploy infrastructure
cd infrastructure
npm install
npm run deploy-dev

# 4. Deploy Lambda functions
cd ..
./scripts/deploy-all.sh dev
```

### 2. Test the Complete Pipeline

```bash
# Run end-to-end pipeline test
./scripts/test-lambda.sh story-executor dev test-data/end-to-end-test.json

# Monitor deployment progress
aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-dev --follow
```

### 3. Access Generated Applications

After successful pipeline execution, you'll receive deployment URLs:

- **Frontend (React/Vue)**: `https://{project-name}-dev.netlify.app`
- **Backend (Node/Python)**: `https://{project-name}-api-dev.example.com`
- **GitHub Repository**: `https://github.com/{username}/{project-name}`
- **Pull Request**: Check the PR URL in lambda output

## Deployment Architecture

### Frontend Deployment (Netlify)
- **Supported Stacks**: React SPA, Vue SPA, React Fullstack
- **Automatic Setup**: Site creation, environment variables, build configuration
- **Preview URLs**: Available for PR reviews
- **Monitoring**: Built-in Netlify analytics and error tracking

### Backend Deployment (ECS Fargate)
- **Supported Stacks**: Node API, Python API, React Fullstack backend
- **Infrastructure**: Auto-scaling containers with health checks
- **Load Balancing**: Application Load Balancer for HTTPS access
- **Logging**: CloudWatch logs with structured logging

## Manual Testing Procedures

### 1. Frontend Testing Checklist

For each generated frontend application:

#### Basic Functionality
- [ ] **Application Loads**: Navigate to deployment URL, application renders without errors
- [ ] **Responsive Design**: Test on desktop, tablet, mobile viewports
- [ ] **Navigation**: All routes/pages accessible, no broken links
- [ ] **UI Components**: Forms, buttons, modals, dialogs work correctly

#### User Story Validation
For each user story in the generated application:

1. **Review Acceptance Criteria**: Check the GitHub PR description for specific criteria
2. **Test Each Criterion**: Systematically verify each acceptance criterion
3. **Document Results**: Note any failures or unexpected behavior
4. **Cross-Browser Testing**: Test in Chrome, Firefox, Safari (if available)

#### Performance Testing
- [ ] **Load Time**: Initial page load under 3 seconds
- [ ] **Lighthouse Score**: Acceptable performance, accessibility, SEO scores
- [ ] **Bundle Size**: No unnecessarily large assets or dependencies

### 2. Backend API Testing Checklist

For each generated backend application:

#### Health Checks
- [ ] **Health Endpoint**: `GET /health` returns 200 OK
- [ ] **API Documentation**: `GET /docs` (for Python FastAPI) or equivalent
- [ ] **Base Route**: Root endpoint returns expected response

#### API Functionality
- [ ] **CRUD Operations**: Create, Read, Update, Delete operations work
- [ ] **Input Validation**: Invalid inputs return appropriate error responses
- [ ] **Authentication**: If implemented, auth endpoints function correctly
- [ ] **Error Handling**: Graceful error responses with proper HTTP status codes

#### Performance & Reliability
- [ ] **Response Times**: API endpoints respond within acceptable time limits
- [ ] **Concurrent Requests**: API handles multiple simultaneous requests
- [ ] **Error Recovery**: Application recovers from temporary failures

### 3. Integration Testing

#### Frontend-Backend Integration
- [ ] **API Calls**: Frontend successfully communicates with backend
- [ ] **Error Handling**: Frontend gracefully handles API errors
- [ ] **Data Flow**: Data flows correctly between frontend and backend
- [ ] **Authentication**: If applicable, auth tokens work across services

#### Third-Party Integrations
- [ ] **External APIs**: Any third-party service integrations function correctly
- [ ] **Database**: Data persistence and retrieval works as expected
- [ ] **File Uploads**: If implemented, file handling works correctly

## Testing Data Management

### Test User Accounts
Generated applications include default test accounts:

```json
{
  "test_users": [
    {
      "email": "admin@test.com",
      "password": "TestPassword123!",
      "role": "admin"
    },
    {
      "email": "user@test.com", 
      "password": "TestPassword123!",
      "role": "user"
    }
  ]
}
```

### Sample Data
Each generated application includes realistic sample data:

- **Database Seeding**: Pre-populated with representative data
- **API Responses**: Meaningful sample responses for testing
- **File Uploads**: Sample files for upload testing

## Environment URLs & Access

### Development Environment Access
All generated applications in dev environment are publicly accessible:

- **No Authentication Required**: For easy testing access
- **Debug Mode Enabled**: Detailed error messages and logging
- **CORS Configured**: Allows cross-origin requests for testing

### Repository Access
- **GitHub Repository**: Public repository with generated code
- **Pull Request**: Contains deployment information and testing instructions
- **GitHub Actions**: Automated CI/CD pipeline status visible

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. Deployment Failures

**Symptom**: Application not accessible at deployment URL
**Diagnosis**:
```bash
# Check lambda logs
aws logs tail /aws/lambda/ai-pipeline-v2-github-orchestrator-dev --since 30m

# Check GitHub Actions status
gh run list --repo {username}/{project-name}
```

**Solutions**:
- Verify AWS credentials and permissions
- Check Secrets Manager configuration
- Review GitHub Actions workflow logs
- Ensure Netlify/ECS resources are properly configured

#### 2. API Connection Issues

**Symptom**: Frontend cannot connect to backend API
**Diagnosis**:
```bash
# Test API directly
curl -f https://{project-name}-api-dev.example.com/health

# Check ECS service status  
aws ecs describe-services --cluster ai-pipeline-v2-dev --services {project-name}-api-dev
```

**Solutions**:
- Verify ECS service is running and healthy
- Check security group configurations
- Validate environment variables in frontend build
- Ensure CORS is properly configured

#### 3. Build/Test Failures

**Symptom**: GitHub Actions workflows fail
**Diagnosis**:
- Review GitHub Actions logs in repository
- Check for missing dependencies or configuration
- Verify environment variables and secrets

**Solutions**:
- Update package.json scripts if needed
- Add missing environment variables
- Fix code quality issues (linting, type errors)

### Getting Help

1. **Check Logs First**: Always review CloudWatch and GitHub Actions logs
2. **GitHub Issues**: Use GitHub PR comments to report issues
3. **Manual Fixes**: For urgent issues, manual repository fixes are acceptable
4. **Re-run Pipeline**: Some issues resolve with a fresh pipeline execution

## Future UAT Automation Framework

### Playwright Integration Points

The manual testing procedures above are designed to be easily automated:

#### 1. Test Structure
```javascript
// Example test structure for future automation
describe('User Story: User Registration', () => {
  test('User can create account with valid email', async ({ page }) => {
    // This maps directly to manual acceptance criteria
    await page.goto(deploymentUrl);
    await page.fill('#email', 'test@example.com');
    await page.fill('#password', 'Password123!');
    await page.click('#submit-button');
    await expect(page.locator('#success-message')).toBeVisible();
  });
});
```

#### 2. Test Data Management
- Standardized test data format compatible with automation
- Database seeding scripts that work with both manual and automated testing
- Environment variables for test configuration

#### 3. Reporting Integration
- Test results structured to integrate with review workflow
- Screenshots and videos for failed tests
- Performance metrics collection during automated runs

### Implementation Roadmap

1. **Phase 1** (Current): Manual testing with structured checklist
2. **Phase 2**: Playwright test generation from user story acceptance criteria
3. **Phase 3**: Automated test execution integrated with review workflow
4. **Phase 4**: AI-powered test case generation and self-healing tests

## Monitoring & Analytics

### Application Performance
- **Netlify Analytics**: Traffic, performance, and error tracking for frontend
- **CloudWatch Metrics**: ECS container performance and health metrics
- **GitHub Actions**: Build time and deployment success rates

### Testing Metrics
Track the following metrics for continuous improvement:

- **Manual Testing Time**: Average time per application testing cycle
- **Defect Detection Rate**: Issues found during manual testing
- **Deployment Success Rate**: Percentage of successful deployments
- **User Story Coverage**: Percentage of acceptance criteria validated

### Reports & Dashboards

Generate weekly reports including:

- Deployment status summary
- Testing completion rates
- Common issues and resolutions
- Performance trends

This structured approach ensures thorough testing while building toward automated testing capabilities that will enhance the overall development pipeline.