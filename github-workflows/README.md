# GitHub Actions Workflow Templates

This directory contains production-ready GitHub Actions workflow templates for different technology stacks supported by AI Pipeline Orchestrator v2.

## Available Templates

### 1. React SPA (`react-spa.yml`)
**Tech Stack**: React + TypeScript + npm
**Features**:
- Multi-Node version testing (18, 20)
- Comprehensive testing suite (lint, type-check, unit tests)
- Code coverage reporting with Codecov
- Lighthouse performance audits
- Preview deployments on pull requests
- Production deployment to GitHub Pages
- Bundle size analysis and security auditing

**Required npm scripts**:
```json
{
  "lint": "eslint src/",
  "type-check": "tsc --noEmit",
  "test:ci": "jest --ci --coverage --watchAll=false",
  "test:coverage": "jest --coverage",
  "build": "react-scripts build",
  "analyze:bundle": "npm run build && npx bundle-analyzer build/static/js/*.js"
}
```

### 2. Node.js API (`node-api.yml`)
**Tech Stack**: Node.js + Express + PostgreSQL + Redis
**Features**:
- Database integration testing with PostgreSQL and Redis
- Unit, integration, and contract testing
- Docker containerization and testing
- API security scanning and load testing
- Staging and production deployment workflows
- Post-deployment health checks

**Required npm scripts**:
```json
{
  "lint": "eslint src/",
  "type-check": "tsc --noEmit",
  "db:migrate": "knex migrate:latest",
  "test:unit": "jest tests/unit/",
  "test:integration": "jest tests/integration/",
  "test:contract": "dredd",
  "test:load": "artillery run load-test.yml",
  "test:security": "npm audit && snyk test"
}
```

### 3. Python API (`python-api.yml`)
**Tech Stack**: Python + FastAPI + Poetry + PostgreSQL
**Features**:
- Multi-Python version testing (3.11, 3.12)
- Poetry dependency management with caching
- Code formatting, linting, and type checking
- Security auditing with Bandit and Safety
- Database migration testing with Alembic
- Container security scanning with Trivy
- OpenAPI schema validation

**Required Poetry configuration**:
```toml
[tool.poetry.scripts]
dev = "uvicorn src.main:app --reload"
test = "pytest"
lint = "flake8 src/"
format = "black src/ && isort src/"
type-check = "mypy src/"
security = "bandit -r src/ && safety check"
```

### 4. Vue SPA (`vue-spa.yml`)
**Tech Stack**: Vue 3 + Vite + TypeScript
**Features**:
- Component and unit testing with Vitest
- End-to-end testing with Playwright
- Accessibility testing with axe-core
- Visual regression testing
- Lighthouse performance audits
- Preview deployments with automatic PR comments
- Production deployment with environment-specific builds

**Required npm scripts**:
```json
{
  "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts",
  "type-check": "vue-tsc --noEmit",
  "test:unit": "vitest run",
  "test:component": "cypress run --component",
  "test:e2e": "playwright test",
  "test:a11y": "jest-axe",
  "test:visual": "percy exec -- cypress run",
  "build": "vite build",
  "preview": "vite preview"
}
```

### 5. React Fullstack (`react-fullstack.yml`)
**Tech Stack**: React frontend + Node.js backend
**Features**:
- Separate frontend and backend testing pipelines
- Full-stack integration testing
- Database migrations and seeding
- Security scanning for both frontend and backend
- Performance testing with Lighthouse and load testing
- Docker containerization
- Environment-specific deployments

**Required npm scripts**:
```json
{
  "lint:frontend": "eslint client/src/",
  "lint:backend": "eslint server/src/",
  "type-check:frontend": "tsc --noEmit --project client/",
  "type-check:backend": "tsc --noEmit --project server/",
  "test:frontend:unit": "jest client/",
  "test:backend:unit": "jest server/",
  "test:e2e": "playwright test",
  "build": "npm run build:frontend && npm run build:backend",
  "build:frontend": "cd client && npm run build",
  "build:backend": "cd server && npm run build"
}
```

## Workflow Features

### Common Features Across All Templates
- **Multi-environment support**: Development, staging, production
- **Security scanning**: Dependency auditing, vulnerability scanning
- **Code quality**: Linting, type checking, test coverage
- **Caching**: npm/yarn cache optimization for faster builds
- **Artifact management**: Test reports, build artifacts, documentation
- **Environment variables**: Configurable via GitHub repository settings

### Advanced Features
- **Preview deployments**: Automatic deployment of PR previews
- **Performance monitoring**: Lighthouse audits and bundle analysis
- **Security compliance**: OWASP scanning, container security
- **Database integration**: Automated migrations and seeding
- **Multi-stage deployments**: Staging validation before production
- **Post-deployment verification**: Health checks and smoke tests

## Configuration

### Environment Variables
Configure these in your GitHub repository settings under **Settings > Secrets and Variables > Actions**:

**Variables (Public)**:
- `CUSTOM_DOMAIN`: Custom domain for production deployments
- `STAGING_API_URL`: Staging API endpoint
- `PRODUCTION_API_URL`: Production API endpoint
- `API_DOCS_URL`: API documentation URL

**Secrets (Private)**:
- `CODECOV_TOKEN`: Codecov integration token
- `DOCKER_REGISTRY_TOKEN`: Container registry authentication
- `DEPLOYMENT_TOKEN`: Production deployment authentication

### Repository Settings
1. **Enable GitHub Pages** for preview and production deployments
2. **Configure branch protection** rules for main/develop branches
3. **Set up environments** (staging, production) with approval requirements
4. **Configure status checks** to require workflow completion

### Custom Configuration Files
Each template expects certain configuration files in the repository root:

- `lighthouserc.json`: Lighthouse CI configuration
- `.eslintrc.js`: ESLint configuration
- `jest.config.js`: Jest testing configuration
- `playwright.config.ts`: Playwright E2E test configuration
- `Dockerfile`: Container build configuration (for API projects)

## Usage with AI Pipeline Orchestrator v2

These templates are automatically selected and configured by the **integration-validator** lambda based on the detected technology stack. The **github-orchestrator** lambda commits the appropriate workflow file to the generated repository's `.github/workflows/` directory.

### Template Selection Logic
```python
tech_stack_templates = {
    'REACT_SPA': 'react-spa.yml',
    'NODE_API': 'node-api.yml', 
    'PYTHON_API': 'python-api.yml',
    'VUE_SPA': 'vue-spa.yml',
    'REACT_FULLSTACK': 'react-fullstack.yml'
}
```

### Customization
Templates can be customized by:
1. **Environment-specific variables**: Configure different API URLs, domains, etc.
2. **Feature flags**: Enable/disable specific jobs via repository variables
3. **Custom scripts**: Modify npm scripts to match your project structure
4. **Additional steps**: Add project-specific build or deployment steps

## Best Practices

### Security
- Store sensitive data in GitHub Secrets, not Variables
- Use scoped tokens with minimal required permissions
- Enable vulnerability alerts and dependency updates
- Regularly audit and rotate authentication tokens

### Performance
- Leverage GitHub Actions caching for dependencies
- Use matrix strategies for parallel testing across versions
- Optimize Docker builds with multi-stage builds and layer caching
- Monitor workflow execution time and costs

### Reliability
- Include comprehensive test coverage requirements
- Set up proper staging environments for validation
- Implement rollback strategies for failed deployments
- Use environment-specific approval workflows for production

### Monitoring
- Set up status badges in repository README
- Configure notifications for build failures
- Track deployment frequency and success rates
- Monitor application performance post-deployment

## Support and Troubleshooting

### Common Issues
1. **Test failures**: Ensure all required npm scripts are defined
2. **Build errors**: Check Node.js/Python version compatibility
3. **Deployment failures**: Verify environment variables and secrets
4. **Permission errors**: Check repository and token permissions

### Debugging
- Enable debug logging with `ACTIONS_RUNNER_DEBUG=true`
- Use `actions/upload-artifact` to inspect build outputs
- Check workflow logs for specific error messages
- Test locally with `act` or similar GitHub Actions emulation tools

For more information, see the [GitHub Actions documentation](https://docs.github.com/en/actions) and the [AI Pipeline Orchestrator v2 Architecture Guide](../ARCHITECTURE.md).