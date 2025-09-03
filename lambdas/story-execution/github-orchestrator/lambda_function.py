"""
GitHub Orchestrator Lambda (Refactored for Sequential Commits)

Manages incremental GitHub commits after each story validation rather than
committing everything at once. This enables immediate feedback and rollback
capability if issues are detected.

Author: AI Pipeline Orchestrator v2
Version: 2.0.0 (Sequential Story Commits)
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import base64
import time
import requests
import hashlib

# Fix Python path to include layer directory
if '/opt/python' not in sys.path:
    sys.path.insert(0, '/opt/python')

# Import PyNaCl from layer
try:
    from nacl import encoding, public
    PYNACL_AVAILABLE = True
except ImportError:
    PYNACL_AVAILABLE = False
    print("Warning: PyNaCl not available, GitHub secrets encryption will fail")

# Initialize AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

# Import shared services
from shared.utils.logger import setup_logger, log_lambda_start, log_lambda_end, log_error

logger = setup_logger("github-orchestrator")


class SequentialGitHubOrchestrator:
    """
    Manages sequential commits to GitHub for each validated story.
    Maintains commit history and enables rollback if needed.
    """
    
    def __init__(self):
        self.s3_client = s3_client
        self.secrets_client = secrets_client
        self.dynamodb = dynamodb
        
        # Get configuration from environment
        self.processed_bucket = os.environ.get('PROCESSED_BUCKET_NAME')
        self.github_table = os.environ.get('GITHUB_INTEGRATIONS_TABLE', 'ai-pipeline-v2-github-integrations-dev')
        
        # Initialize GitHub service
        self.github_service = GitHubService()
        
        # Load orchestration configuration
        self.config = self._load_orchestration_config()
    
    def _load_orchestration_config(self) -> Dict[str, Any]:
        """Load orchestration configuration."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.processed_bucket,
                Key='config/validation-config.json'
            )
            config = json.loads(response['Body'].read().decode('utf-8'))
            return config.get('sequential_processing', {})
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            return {
                "commit_after_each_story": True,
                "create_pr_after_all_stories": True,
                "maintain_commit_history": True,
                "enable_rollback": True
            }
    
    def commit_story_increment(
        self,
        story_files: List[Dict[str, Any]],
        story_metadata: Dict[str, Any],
        project_context: Dict[str, Any],
        architecture: Dict[str, Any],
        repository_info: Optional[Dict[str, Any]] = None,
        commit_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Commit a single story's files to GitHub incrementally.
        
        Args:
            story_files: Files generated for the current story
            story_metadata: Metadata about the current story
            project_context: Overall project context
            architecture: Project architecture specification
            repository_info: Existing repository info if available
            commit_history: Previous commits for this project
            
        Returns:
            Commit result with repository and commit information
        """
        execution_id = f"gh_inc_{story_metadata.get('story_id')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting incremental commit for story: {story_metadata.get('title')}")
        
        project_id = project_context.get('project_id')
        tech_stack = architecture.get('tech_stack')
        
        # 1. Create or get repository (only on first story)
        if not repository_info:
            repository_name = f"{project_id}"
            logger.info(f"Creating/getting GitHub repository: {repository_name}")
            repository_info = self.github_service.create_or_get_repository(repository_name, tech_stack)
            
            # Initialize repository with base files if new
            if self._is_new_repository(repository_info):
                base_files = self._generate_base_files(project_id, tech_stack, architecture)
                self._commit_base_files(repository_info, base_files)
        
        # 2. Determine branch strategy
        branch_name = self._get_branch_name(project_context, story_metadata, commit_history)
        
        # 3. Create branch if it doesn't exist
        if not self._branch_exists(repository_info['full_name'], branch_name):
            logger.info(f"Creating branch: {branch_name}")
            self.github_service.create_branch(repository_info['full_name'], branch_name)
        
        # 4. Retrieve file content from S3 if needed
        files_with_content = self._retrieve_file_content(story_files)
        
        # 5. Generate commit message for this story
        commit_message = self._generate_story_commit_message(story_metadata, len(files_with_content))
        
        # 6. Commit story files
        logger.info(f"Committing {len(files_with_content)} files for story: {story_metadata.get('title')}")
        commit_info = self.github_service.commit_files(
            repository_info['full_name'],
            branch_name,
            files_with_content,
            commit_message
        )
        
        # 7. Store commit in history
        commit_record = {
            'commit_id': commit_info.get('sha'),
            'story_id': story_metadata.get('story_id'),
            'story_title': story_metadata.get('title'),
            'files_count': len(files_with_content),
            'branch': branch_name,
            'timestamp': datetime.utcnow().isoformat(),
            'message': commit_message
        }
        
        if commit_history is None:
            commit_history = []
        commit_history.append(commit_record)
        
        # 8. Update commit history in DynamoDB
        self._store_commit_history(project_id, repository_info, commit_history)
        
        # 9. Check if this is the last story and should create PR
        should_create_pr = story_metadata.get('is_last_story', False) and self.config.get('create_pr_after_all_stories', True)
        
        pr_info = None
        if should_create_pr:
            pr_info = self._create_final_pull_request(
                repository_info,
                branch_name,
                project_id,
                commit_history,
                architecture
            )
        
        return {
            'execution_id': execution_id,
            'repository_info': repository_info,
            'branch_name': branch_name,
            'commit_info': commit_info,
            'commit_record': commit_record,
            'commit_history': commit_history,
            'pr_info': pr_info,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def setup_deployment_infrastructure(
        self,
        project_id: str,
        tech_stack: str,
        repository_info: Dict[str, Any],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up deployment infrastructure (Netlify, GitHub Actions, etc.) once at the beginning.
        This is called once before any stories are processed.
        """
        logger.info(f"Setting up deployment infrastructure for {project_id}")
        
        deployment_info = {}
        
        # 1. Create Netlify site for frontend projects
        if tech_stack in ['react_spa', 'vue_spa', 'react_fullstack']:
            try:
                logger.info("Creating Netlify site for frontend deployment...")
                netlify_service = NetlifyService()
                netlify_site_info = netlify_service.create_site(project_id)
                
                if netlify_site_info:
                    logger.info(f"✅ Created Netlify site: {netlify_site_info.get('url')}")
                    
                    # Add Netlify secrets to GitHub repository
                    if netlify_service.add_secrets_to_github_repo(
                        self.github_service,
                        repository_info['full_name'],
                        netlify_site_info['id']
                    ):
                        logger.info("✅ Added Netlify secrets to GitHub repository")
                    
                    deployment_info['netlify_site'] = netlify_site_info
                    
            except Exception as e:
                logger.error(f"Netlify setup failed: {e}")
                # Continue without Netlify - can be set up manually
        
        # 2. Add GitHub Actions workflow files
        workflow_files = self._generate_github_workflows(tech_stack, architecture)
        if workflow_files:
            # Commit workflow files to main branch
            self.github_service.commit_files(
                repository_info['full_name'],
                'main',
                workflow_files,
                "chore: add GitHub Actions CI/CD workflows"
            )
            deployment_info['workflows'] = [f['file_path'] for f in workflow_files]
        
        # 3. Store deployment configuration
        self._store_deployment_config(project_id, deployment_info)
        
        return deployment_info
    
    def rollback_to_checkpoint(
        self,
        project_id: str,
        checkpoint_id: str,
        repository_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rollback to a previous commit checkpoint if validation fails.
        """
        logger.info(f"Rolling back project {project_id} to checkpoint {checkpoint_id}")
        
        # Get commit history
        commit_history = self._get_commit_history(project_id)
        
        # Find the checkpoint
        checkpoint = next((c for c in commit_history if c['commit_id'] == checkpoint_id), None)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        # Reset branch to checkpoint
        branch_name = checkpoint['branch']
        reset_result = self.github_service.reset_branch_to_commit(
            repository_info['full_name'],
            branch_name,
            checkpoint_id
        )
        
        # Update commit history to remove commits after checkpoint
        checkpoint_index = commit_history.index(checkpoint)
        updated_history = commit_history[:checkpoint_index + 1]
        self._store_commit_history(project_id, repository_info, updated_history)
        
        return {
            'rolled_back_to': checkpoint_id,
            'story_id': checkpoint['story_id'],
            'removed_commits': len(commit_history) - len(updated_history),
            'current_history': updated_history
        }
    
    def _is_new_repository(self, repository_info: Dict[str, Any]) -> bool:
        """Check if repository is newly created (has only initial commit)."""
        # Simple check - could be enhanced with API call to check commit count
        return repository_info.get('created_at') == repository_info.get('updated_at')
    
    def _generate_base_files(
        self,
        project_id: str,
        tech_stack: str,
        architecture: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate base files for new repository (README, .gitignore, etc.)."""
        base_files = []
        
        # README.md
        readme_content = f"""# {project_id}

AI-generated {tech_stack} application.

## Tech Stack
- **Framework**: {architecture.get('framework', tech_stack)}
- **Language**: {architecture.get('language', 'TypeScript')}
- **Build Tool**: {architecture.get('build_tool', 'npm')}

## Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Project Structure
```
{self._generate_structure_tree(architecture)}
```

---
*Generated by AI Pipeline Orchestrator v2*
"""
        base_files.append({
            'file_path': 'README.md',
            'content': readme_content
        })
        
        # .gitignore
        gitignore_content = self._get_gitignore_template(tech_stack)
        base_files.append({
            'file_path': '.gitignore',
            'content': gitignore_content
        })
        
        return base_files
    
    def _get_gitignore_template(self, tech_stack: str) -> str:
        """Get appropriate .gitignore template for tech stack."""
        templates = {
            'react_spa': """# Dependencies
node_modules/
.pnp
.pnp.js

# Testing
coverage/

# Production
build/
dist/

# Misc
.DS_Store
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.idea/
.vscode/
*.swp
*.swo
""",
            'node_api': """# Dependencies
node_modules/

# Environment
.env
.env.*

# Logs
logs/
*.log

# Build
dist/
build/

# IDE
.idea/
.vscode/
""",
            'python_api': """# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual Environment
venv/
env/
ENV/

# Environment
.env
.env.*

# IDE
.idea/
.vscode/

# Distribution
dist/
build/
*.egg-info/
"""
        }
        
        return templates.get(tech_stack, templates['react_spa'])
    
    def _generate_structure_tree(self, architecture: Dict[str, Any]) -> str:
        """Generate project structure tree for README."""
        structure = architecture.get('directory_structure', {})
        # Simplified tree generation
        return """src/
├── components/
├── pages/
├── services/
├── utils/
└── styles/"""
    
    def _commit_base_files(
        self,
        repository_info: Dict[str, Any],
        base_files: List[Dict[str, str]]
    ):
        """Commit base files to main branch."""
        self.github_service.commit_files(
            repository_info['full_name'],
            'main',
            base_files,
            "chore: initialize repository with base files"
        )
    
    def _get_branch_name(
        self,
        project_context: Dict[str, Any],
        story_metadata: Dict[str, Any],
        commit_history: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Determine branch name for commits."""
        if self.config.get('commit_after_each_story') and not self.config.get('single_branch'):
            # Use story-specific branch
            story_id = story_metadata.get('story_id', 'unknown')
            return f"story/{story_id}"
        else:
            # Use single feature branch for all stories
            if commit_history and commit_history[0].get('branch'):
                return commit_history[0]['branch']
            else:
                execution_id = project_context.get('execution_id', datetime.utcnow().strftime('%Y%m%d_%H%M%S'))
                return f"feature/ai-generated-{execution_id[:8]}"
    
    def _branch_exists(self, repo_full_name: str, branch_name: str) -> bool:
        """Check if branch exists in repository."""
        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo_full_name}/git/refs/heads/{branch_name}",
                headers=self.github_service.headers,
                timeout=30
            )
            return response.status_code == 200
        except:
            return False
    
    def _retrieve_file_content(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retrieve file content from S3 if needed."""
        files_with_content = []
        
        for file_metadata in files:
            s3_bucket = file_metadata.get('s3_bucket')
            s3_key = file_metadata.get('s3_key')
            
            if s3_bucket and s3_key:
                try:
                    response = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                    content = response['Body'].read().decode('utf-8')
                    
                    file_with_content = file_metadata.copy()
                    file_with_content['content'] = content
                    files_with_content.append(file_with_content)
                    
                except Exception as e:
                    logger.error(f"Error retrieving file from S3: {e}")
            elif 'content' in file_metadata:
                files_with_content.append(file_metadata)
        
        return files_with_content
    
    def _generate_story_commit_message(
        self,
        story_metadata: Dict[str, Any],
        files_count: int
    ) -> str:
        """Generate commit message for a single story."""
        story_title = story_metadata.get('title', 'Unknown Story')
        story_id = story_metadata.get('story_id', 'unknown')
        
        message = f"feat: implement {story_title}\n\n"
        message += f"Story ID: {story_id}\n"
        message += f"Files: {files_count} files generated\n"
        
        if story_metadata.get('acceptance_criteria'):
            message += "\nAcceptance Criteria:\n"
            for criterion in story_metadata['acceptance_criteria'][:3]:
                message += f"- {criterion}\n"
        
        return message
    
    def _create_final_pull_request(
        self,
        repository_info: Dict[str, Any],
        branch_name: str,
        project_id: str,
        commit_history: List[Dict[str, Any]],
        architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create final PR after all stories are committed."""
        stories_count = len(commit_history)
        total_files = sum(c.get('files_count', 0) for c in commit_history)
        
        pr_title = f"feat: AI-generated implementation for {project_id} ({stories_count} stories)"
        
        pr_body = f"""## AI-Generated Implementation

### Summary
This PR contains AI-generated code implementing {stories_count} user stories.

### Stories Implemented
"""
        
        for commit in commit_history[:10]:  # Show first 10 stories
            pr_body += f"- [{commit['story_id']}] {commit['story_title']}\n"
        
        if stories_count > 10:
            pr_body += f"- ... and {stories_count - 10} more stories\n"
        
        pr_body += f"""
### Statistics
- Total Stories: {stories_count}
- Total Files: {total_files}
- Tech Stack: {architecture.get('tech_stack')}

### Commit History
"""
        
        for commit in commit_history[-5:]:  # Show last 5 commits
            pr_body += f"- `{commit['commit_id'][:8]}` - {commit['story_title']}\n"
        
        pr_body += """
### Testing
- GitHub Actions will automatically run tests
- Review the code and test results before merging

---
*Generated by AI Pipeline Orchestrator v2 - Sequential Processing*
"""
        
        return self.github_service.create_pull_request(
            repository_info['full_name'],
            branch_name,
            pr_title,
            pr_body
        )
    
    def _store_commit_history(
        self,
        project_id: str,
        repository_info: Dict[str, Any],
        commit_history: List[Dict[str, Any]]
    ):
        """Store commit history in DynamoDB."""
        try:
            table = self.dynamodb.Table(self.github_table)
            table.put_item(Item={
                'integration_id': f"commits-{project_id}",
                'project_id': project_id,
                'repository_info': repository_info,
                'commit_history': commit_history,
                'last_updated': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)
            })
        except Exception as e:
            logger.error(f"Failed to store commit history: {e}")
    
    def _get_commit_history(self, project_id: str) -> List[Dict[str, Any]]:
        """Retrieve commit history from DynamoDB."""
        try:
            table = self.dynamodb.Table(self.github_table)
            response = table.get_item(Key={'integration_id': f"commits-{project_id}"})
            if 'Item' in response:
                return response['Item'].get('commit_history', [])
        except Exception as e:
            logger.error(f"Failed to retrieve commit history: {e}")
        return []
    
    def _store_deployment_config(self, project_id: str, deployment_info: Dict[str, Any]):
        """Store deployment configuration."""
        try:
            table = self.dynamodb.Table(self.github_table)
            table.put_item(Item={
                'integration_id': f"deployment-{project_id}",
                'project_id': project_id,
                'deployment_info': deployment_info,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)
            })
        except Exception as e:
            logger.error(f"Failed to store deployment config: {e}")
    
    def _generate_github_workflows(
        self,
        tech_stack: str,
        architecture: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate GitHub Actions workflow files."""
        workflows = []
        
        # Main CI/CD workflow
        workflow_content = self._get_workflow_template(tech_stack, architecture)
        workflows.append({
            'file_path': '.github/workflows/ci-cd.yml',
            'content': workflow_content
        })
        
        return workflows
    
    def _get_workflow_template(self, tech_stack: str, architecture: Dict[str, Any]) -> str:
        """Get GitHub Actions workflow template."""
        if tech_stack in ['react_spa', 'vue_spa']:
            return """name: CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm test -- --passWithNoTests
    
    - name: Build
      run: npm run build
    
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Build
      run: npm run build
    
    - name: Deploy to Netlify
      uses: nwtgck/actions-netlify@v2.0
      with:
        publish-dir: './dist'
        production-branch: main
        github-token: ${{ secrets.GITHUB_TOKEN }}
        deploy-message: "Deploy from GitHub Actions"
      env:
        NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
        NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
"""
        else:
            # Default Node.js API workflow
            return """name: CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm test -- --passWithNoTests
    
    - name: Build
      run: npm run build
"""


class GitHubService:
    """Enhanced GitHub service for sequential operations."""
    
    def __init__(self):
        self.github_token = self._get_github_token()
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        } if self.github_token else None
    
    def _get_github_token(self) -> Optional[str]:
        """Retrieve GitHub token from AWS Secrets Manager."""
        try:
            secret_name = os.environ.get('GITHUB_TOKEN_SECRET_ARN', 'ai-pipeline-v2/github-token-dev')
            if not secret_name:
                logger.info("GitHub token secret not configured - using mock mode")
                return None
            
            response = secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data.get('token', '')
        except Exception as e:
            logger.warning(f"Failed to retrieve GitHub token: {e}")
            return None
    
    def create_or_get_repository(self, project_name: str, tech_stack: str) -> Dict[str, Any]:
        """Create or get existing GitHub repository."""
        if not self.github_token:
            raise Exception("GitHub token not available")
        
        try:
            # Check if repository exists
            existing_repo = self._get_repository(project_name)
            if existing_repo:
                logger.info(f"Repository {project_name} already exists")
                return existing_repo
            
            # Create new repository
            repo_data = {
                'name': project_name,
                'description': f"AI-generated {tech_stack} application",
                'private': False,
                'auto_init': True,
                'has_wiki': False,
                'has_projects': False
            }
            
            response = requests.post(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                json=repo_data,
                timeout=30
            )
            
            if response.status_code == 201:
                repo_info = response.json()
                logger.info(f"✅ Created repository: {repo_info['html_url']}")
                return repo_info
            else:
                raise Exception(f"Failed to create repository: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Repository creation failed: {e}")
            raise
    
    def _get_repository(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Check if repository exists."""
        try:
            user_response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=30
            )
            
            if user_response.status_code == 200:
                username = user_response.json()['login']
                
                repo_response = requests.get(
                    f"{self.base_url}/repos/{username}/{project_name}",
                    headers=self.headers,
                    timeout=30
                )
                
                if repo_response.status_code == 200:
                    return repo_response.json()
            
        except Exception as e:
            logger.error(f"Error checking repository: {e}")
        
        return None
    
    def create_branch(self, repo_full_name: str, branch_name: str) -> Dict[str, Any]:
        """Create a new branch."""
        try:
            # Get default branch SHA
            response = requests.get(
                f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/main",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 404:
                response = requests.get(
                    f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/master",
                    headers=self.headers,
                    timeout=30
                )
            
            if response.status_code == 200:
                sha = response.json()['object']['sha']
                
                # Create new branch
                branch_data = {
                    'ref': f'refs/heads/{branch_name}',
                    'sha': sha
                }
                
                response = requests.post(
                    f"{self.base_url}/repos/{repo_full_name}/git/refs",
                    headers=self.headers,
                    json=branch_data,
                    timeout=30
                )
                
                if response.status_code in [201, 422]:  # 422 = already exists
                    logger.info(f"Branch {branch_name} ready")
                    return response.json() if response.status_code == 201 else {"ref": f"refs/heads/{branch_name}"}
            
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
        
        return {}
    
    def commit_files(
        self,
        repo_full_name: str,
        branch_name: str,
        files: List[Dict[str, Any]],
        commit_message: str
    ) -> Dict[str, Any]:
        """Commit files to branch."""
        if not self.github_token:
            return {"sha": "mock-commit-sha"}
        
        try:
            # Get current branch SHA
            ref_response = requests.get(
                f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/{branch_name}",
                headers=self.headers,
                timeout=30
            )
            
            if ref_response.status_code != 200:
                logger.error(f"Failed to get branch ref: {ref_response.status_code}")
                return {}
            
            current_sha = ref_response.json()['object']['sha']
            
            # Get tree SHA
            commit_response = requests.get(
                f"{self.base_url}/repos/{repo_full_name}/git/commits/{current_sha}",
                headers=self.headers,
                timeout=30
            )
            
            if commit_response.status_code != 200:
                return {}
            
            base_tree_sha = commit_response.json()['tree']['sha']
            
            # Create blobs and tree
            tree_items = []
            for file_info in files:
                content = file_info.get('content', '')
                if not content:
                    continue
                
                # Create blob
                blob_data = {
                    'content': base64.b64encode(content.encode()).decode(),
                    'encoding': 'base64'
                }
                
                blob_response = requests.post(
                    f"{self.base_url}/repos/{repo_full_name}/git/blobs",
                    headers=self.headers,
                    json=blob_data,
                    timeout=30
                )
                
                if blob_response.status_code == 201:
                    tree_items.append({
                        'path': file_info['file_path'],
                        'mode': '100644',
                        'type': 'blob',
                        'sha': blob_response.json()['sha']
                    })
            
            if not tree_items:
                return {}
            
            # Create tree
            tree_data = {
                'base_tree': base_tree_sha,
                'tree': tree_items
            }
            
            tree_response = requests.post(
                f"{self.base_url}/repos/{repo_full_name}/git/trees",
                headers=self.headers,
                json=tree_data,
                timeout=60
            )
            
            if tree_response.status_code != 201:
                return {}
            
            # Create commit
            commit_data = {
                'message': commit_message,
                'tree': tree_response.json()['sha'],
                'parents': [current_sha]
            }
            
            new_commit_response = requests.post(
                f"{self.base_url}/repos/{repo_full_name}/git/commits",
                headers=self.headers,
                json=commit_data,
                timeout=30
            )
            
            if new_commit_response.status_code != 201:
                return {}
            
            new_commit_sha = new_commit_response.json()['sha']
            
            # Update branch
            update_ref_data = {
                'sha': new_commit_sha,
                'force': False
            }
            
            update_response = requests.patch(
                f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/{branch_name}",
                headers=self.headers,
                json=update_ref_data,
                timeout=30
            )
            
            if update_response.status_code == 200:
                logger.info(f"✅ Committed {len(tree_items)} files")
                return {"sha": new_commit_sha}
            
        except Exception as e:
            logger.error(f"Error committing files: {e}")
        
        return {}
    
    def reset_branch_to_commit(
        self,
        repo_full_name: str,
        branch_name: str,
        commit_sha: str
    ) -> Dict[str, Any]:
        """Reset branch to specific commit (for rollback)."""
        try:
            update_ref_data = {
                'sha': commit_sha,
                'force': True  # Force reset
            }
            
            response = requests.patch(
                f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/{branch_name}",
                headers=self.headers,
                json=update_ref_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Reset branch {branch_name} to {commit_sha[:8]}")
                return response.json()
            
        except Exception as e:
            logger.error(f"Error resetting branch: {e}")
        
        return {}
    
    def create_pull_request(
        self,
        repo_full_name: str,
        branch_name: str,
        title: str,
        body: str
    ) -> Dict[str, Any]:
        """Create pull request."""
        if not self.github_token:
            return {"html_url": "mock-pr-url", "number": 1}
        
        try:
            pr_data = {
                'title': title,
                'body': body,
                'head': branch_name,
                'base': 'main'
            }
            
            response = requests.post(
                f"{self.base_url}/repos/{repo_full_name}/pulls",
                headers=self.headers,
                json=pr_data,
                timeout=30
            )
            
            if response.status_code == 201:
                pr_info = response.json()
                logger.info(f"✅ Created pull request: {pr_info['html_url']}")
                return pr_info
            
        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
        
        return {}


class NetlifyService:
    """Netlify service for deployment setup."""
    
    def __init__(self):
        self.netlify_token = self._get_netlify_token()
        self.base_url = "https://api.netlify.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.netlify_token}",
            "Content-Type": "application/json"
        } if self.netlify_token else None
    
    def _get_netlify_token(self) -> Optional[str]:
        """Retrieve Netlify token from AWS Secrets Manager."""
        try:
            secret_name = os.environ.get('NETLIFY_TOKEN_SECRET_ARN', 'ai-pipeline-v2/netlify-token-dev')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data.get('token', '')
        except Exception as e:
            logger.warning(f"Failed to retrieve Netlify token: {e}")
            return None
    
    def create_site(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Create Netlify site."""
        if not self.netlify_token:
            logger.warning("Netlify token not available")
            return None
        
        try:
            site_data = {
                'name': f"{project_name}-{os.urandom(4).hex()}",
                'custom_domain': None
            }
            
            response = requests.post(
                f"{self.base_url}/sites",
                headers=self.headers,
                json=site_data,
                timeout=30
            )
            
            if response.status_code == 201:
                site_info = response.json()
                logger.info(f"✅ Created Netlify site: {site_info['url']}")
                return site_info
            
        except Exception as e:
            logger.error(f"Error creating Netlify site: {e}")
        
        return None
    
    def add_secrets_to_github_repo(
        self,
        github_service: GitHubService,
        repo_full_name: str,
        site_id: str
    ) -> bool:
        """Add Netlify secrets to GitHub repository."""
        if not self.netlify_token:
            return False
        
        try:
            # Add NETLIFY_AUTH_TOKEN
            github_service.create_repository_secret(
                repo_full_name,
                "NETLIFY_AUTH_TOKEN",
                self.netlify_token
            )
            
            # Add NETLIFY_SITE_ID
            github_service.create_repository_secret(
                repo_full_name,
                "NETLIFY_SITE_ID",
                site_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding Netlify secrets: {e}")
            return False


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for sequential GitHub orchestration.
    
    This refactored version handles incremental commits per story
    rather than committing everything at once.
    """
    execution_id = log_lambda_start(event, context)
    
    try:
        orchestrator = SequentialGitHubOrchestrator()
        
        # Determine operation mode
        operation_mode = event.get('operation_mode', 'incremental_commit')
        
        if operation_mode == 'setup_deployment':
            # Initial setup for deployment infrastructure
            project_id = event.get('project_id')
            tech_stack = event.get('tech_stack')
            architecture = event.get('architecture', {})
            
            repository_name = f"{project_id}"
            repository_info = orchestrator.github_service.create_or_get_repository(repository_name, tech_stack)
            
            deployment_info = orchestrator.setup_deployment_infrastructure(
                project_id,
                tech_stack,
                repository_info,
                architecture
            )
            
            response = {
                'status': 'success',
                'message': 'Deployment infrastructure setup complete',
                'execution_id': execution_id,
                'stage': 'github_setup',
                'data': {
                    'repository_info': repository_info,
                    'deployment_info': deployment_info
                }
            }
            
        elif operation_mode == 'incremental_commit':
            # Incremental commit for a single story
            story_files = event.get('story_files', [])
            story_metadata = event.get('story_metadata', {})
            project_context = event.get('project_context', {})
            architecture = event.get('architecture', {})
            repository_info = event.get('repository_info')
            commit_history = event.get('commit_history', [])
            
            commit_result = orchestrator.commit_story_increment(
                story_files,
                story_metadata,
                project_context,
                architecture,
                repository_info,
                commit_history
            )
            
            response = {
                'status': 'success',
                'message': f"Story '{story_metadata.get('title')}' committed successfully",
                'execution_id': execution_id,
                'stage': 'github_incremental_commit',
                'data': commit_result
            }
            
        elif operation_mode == 'rollback':
            # Rollback to previous checkpoint
            project_id = event.get('project_id')
            checkpoint_id = event.get('checkpoint_id')
            repository_info = event.get('repository_info')
            
            rollback_result = orchestrator.rollback_to_checkpoint(
                project_id,
                checkpoint_id,
                repository_info
            )
            
            response = {
                'status': 'success',
                'message': f"Rolled back to checkpoint {checkpoint_id[:8]}",
                'execution_id': execution_id,
                'stage': 'github_rollback',
                'data': rollback_result
            }
            
        else:
            raise ValueError(f"Unknown operation mode: {operation_mode}")
        
        log_lambda_end(execution_id, response)
        return response
        
    except Exception as e:
        error_msg = f"GitHub orchestration failed: {str(e)}"
        log_error(e, execution_id, "github_orchestration")
        
        error_response = {
            'status': 'error',
            'message': error_msg,
            'execution_id': execution_id,
            'stage': 'github_orchestration',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }
        
        log_lambda_end(execution_id, error_response)
        raise RuntimeError(error_msg)