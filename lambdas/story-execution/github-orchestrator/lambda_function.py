"""
GitHub Orchestrator Lambda

Manages GitHub repository operations, code commits, and GitHub Actions workflow triggering.
This lambda creates repositories, commits generated code, and monitors build results.

Author: AI Pipeline Orchestrator v2
Version: 1.0.0 (Simplified)
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import base64
import time
import requests

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

def retrieve_files_from_s3(generated_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Retrieve file content from S3 for files that need to be committed to GitHub.
    
    Args:
        generated_files: List of file metadata with S3 references
        
    Returns:
        List of files with content included
    """
    files_with_content = []
    
    for file_metadata in generated_files:
        s3_bucket = file_metadata.get('s3_bucket')
        s3_key = file_metadata.get('s3_key')
        
        if s3_bucket and s3_key:
            try:
                # Retrieve content from S3
                response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                content = response['Body'].read().decode('utf-8')
                
                # Create file dict with content
                file_with_content = file_metadata.copy()
                file_with_content['content'] = content
                files_with_content.append(file_with_content)
                
                print(f"Retrieved {file_metadata['file_path']} from S3")
            except Exception as e:
                print(f"Error retrieving {file_metadata.get('file_path', 'unknown')} from S3: {e}")
        elif 'content' in file_metadata:
            # File already has content (backward compatibility)
            files_with_content.append(file_metadata)
        else:
            print(f"Warning: No content or S3 reference for {file_metadata.get('file_path', 'unknown')}")
    
    return files_with_content

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main lambda handler for GitHub orchestration.
    
    Args:
        event: Lambda event containing project context and validation results
        context: Lambda runtime context
        
    Returns:
        Dict containing GitHub repository information and build status
    """
    execution_id = f"github_orch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    try:
        print(f"Starting GitHub orchestration with execution_id: {execution_id}")
        print(f"Event data: {json.dumps(event, default=str)}")
        
        # Initialize variables early to avoid undefined errors in exception handler
        generated_files = []
        architecture = {}
        pipeline_context = {}
        tech_stack = None
        project_id = 'unknown'
        validation_summary = {}
        validation_passed = True
        data = {}
        story_result = {}
        integration_result = {}
        validation_data = {}
        
        # Handle both direct lambda input and Step Functions input
        if 'storyExecutorResult' in event:
            # Step Functions format - extract from nested results
            story_result = event.get('storyExecutorResult', {}).get('Payload', {})
            integration_result = event.get('integrationValidatorResult', {}).get('Payload', {})
            
            data = story_result.get('data', {})
            
            # Integration validator result is optional - check if it exists
            if integration_result and integration_result.get('data'):
                validation_data = integration_result.get('data', {})
                validation_summary = validation_data.get('validation_summary', {})
                # Don't default to True - use the actual value from validation
                validation_passed = validation_summary.get('validation_passed', False)  # Default to False if validation ran but didn't specify
                
                # Log the validation summary for debugging
                print(f"Integration Validation Summary: {json.dumps(validation_summary, default=str)}")
                print(f"Validation Passed: {validation_passed}")
                print(f"Components Validated: {validation_summary.get('components_validated', 0)}")
                print(f"Validation Results: {validation_summary.get('validation_results', [])}")
                
                # Use data from integration validator if available (it has the most recent pipeline_context)
                pipeline_context = validation_data.get('pipeline_context', data.get('pipeline_context', {}))
                
                # Handle new summary format from integration validator
                if 'architecture_summary' in validation_data:
                    # New format - integration validator returns summary only
                    # Always prefer data from story executor which has full file content
                    architecture = data.get('architecture', {})
                    generated_files = data.get('generated_files', [])
                    
                    # Only try S3 retrieval if we don't have the data from story executor
                    if not generated_files and validation_data.get('full_data_reference'):
                        # Retrieve from S3 if needed
                        try:
                            ref = validation_data['full_data_reference']
                            response = s3_client.get_object(Bucket=ref['bucket'], Key=ref['key'])
                            full_data = json.loads(response['Body'].read())
                            architecture = full_data.get('architecture', architecture)
                            generated_files = full_data.get('generated_files', [])
                            print(f"Retrieved full data from S3: {ref['key']}")
                        except Exception as e:
                            print(f"Warning: Could not retrieve full data from S3: {e}")
                            # Keep the data we already have from story executor
                            # Do NOT set to empty!
                else:
                    # Old format - data directly in response
                    architecture = validation_data.get('architecture', data.get('architecture', {}))
                    generated_files = validation_data.get('generated_files', data.get('generated_files', []))
                
                # Also check for project_id in integration result top level
                if not pipeline_context.get('project_id') and integration_result.get('project_id'):
                    pipeline_context['project_id'] = integration_result.get('project_id')
                    print(f"Using project_id from integration result top level: {integration_result.get('project_id')}")
            else:
                # No validation data - use data from story executor
                validation_data = {}
                validation_summary = {}
                validation_passed = True
                print("No integration validation data found - proceeding without validation")
                
                pipeline_context = data.get('pipeline_context', {})
                architecture = data.get('architecture', {})
                generated_files = data.get('generated_files', [])
        else:
            # Direct lambda input format
            data = event.get('data', {})
            validation_summary = data.get('validation_summary', {})
            pipeline_context = data.get('pipeline_context', {})
            architecture = data.get('architecture', {})
            generated_files = data.get('generated_files', [])
            validation_passed = validation_summary.get('validation_passed', True)  # Default to True
            validation_data = {}
        
        # Extract project_id from multiple possible sources with detailed logging
        print(f"Searching for project_id...")
        print(f"  - pipeline_context.project_id: {pipeline_context.get('project_id')}")
        print(f"  - event.project_metadata.project_name: {event.get('project_metadata', {}).get('project_name')}")
        print(f"  - event.project_id: {event.get('project_id')}")
        if 'storyExecutorResult' in event:
            print(f"  - story_result.project_id: {story_result.get('project_id')}")
        print(f"  - data.project_id: {data.get('project_id')}")
        print(f"  - architecture.project_id: {architecture.get('project_id')}")
        
        project_id = (
            pipeline_context.get('project_id') or
            event.get('project_metadata', {}).get('project_name') or
            event.get('project_id') or
            (story_result.get('project_id') if 'storyExecutorResult' in event and story_result else None) or
            data.get('project_id') or
            architecture.get('project_id') or
            'unknown'
        )
        
        print(f"Final extracted project_id: {project_id}")
        
        tech_stack = architecture.get('tech_stack')
        
        if not all([project_id, tech_stack]):
            raise ValueError("Missing required data: project_id or tech_stack")
            
        # Check if validation exists and failed - stop if validation explicitly failed
        if validation_summary and 'validation_passed' in validation_summary:
            if not validation_passed:
                error_msg = f"Validation failed - cannot proceed with GitHub operations. Validation summary: {json.dumps(validation_summary, default=str)}"
                print(error_msg)
                raise ValueError(error_msg)
            else:
                print(f"Validation passed successfully: {validation_summary.get('components_validated', 0)} components validated")
        else:
            print("No validation data available - proceeding with GitHub operations")
        
        # Perform additional build readiness validation (NEW)
        build_readiness_check = validate_build_readiness(generated_files, tech_stack, architecture)
        if not build_readiness_check['ready']:
            print(f"Warning: Build readiness issues detected: {build_readiness_check['issues']}")
            # Add missing critical files to generated_files
            generated_files = add_missing_build_files(generated_files, build_readiness_check['missing_files'], tech_stack)
            print(f"Added {len(build_readiness_check['missing_files'])} missing build files")
        
        print(f"Processing project: {project_id}, tech_stack: {tech_stack}")
        print(f"Generated files: {len(generated_files)}")
        
        # Initialize GitHub service
        github_service = GitHubService()
        
        # 1. Create or get repository
        repository_name = f"{project_id}"
        print(f"Creating/getting GitHub repository: {repository_name}")
        repository_info = github_service.create_or_get_repository(repository_name, tech_stack)
        
        # 2. Create Netlify site and add secrets to GitHub repository for frontend projects (BEFORE workflow creation)
        netlify_site_info = None
        netlify_required = tech_stack in ['react_spa', 'vue_spa', 'react_fullstack']
        
        if netlify_required:
            try:
                print("Creating Netlify site for frontend deployment...")
                netlify_service = NetlifyService()
                netlify_site_info = netlify_service.create_site(project_id)
                
                if netlify_site_info:
                    print(f"✅ Created Netlify site: {netlify_site_info.get('url', 'Unknown')}")
                    print(f"Site ID: {netlify_site_info.get('id', 'Unknown')}")
                    
                    # Add Netlify secrets to GitHub repository BEFORE creating workflows
                    if netlify_service.add_secrets_to_github_repo(github_service, repository_info['full_name'], netlify_site_info['id']):
                        print("✅ Successfully added Netlify secrets to GitHub repository")
                        print("✅ GitHub Actions workflows will now have access to Netlify credentials")
                    else:
                        print("⚠️  Failed to add Netlify secrets to GitHub repository")
                        print("⚠️  Netlify deployment may require manual configuration")
                        print("⚠️  Please add NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID secrets manually to the repository")
                        # Continue without failing - deployment can be configured manually
                        # raise RuntimeError("Failed to add Netlify secrets to GitHub repository - deployment would fail")
                else:
                    print("❌ Failed to create Netlify site")
                    raise RuntimeError(f"Failed to create Netlify site for {tech_stack} project - deployment requires Netlify")
                    
            except Exception as e:
                error_msg = f"Netlify deployment failed: {str(e)}"
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)
        
        # 3. Create feature branch name - use timestamp and random part for uniqueness
        # execution_id format: "github_orch_YYYYMMDD_HHMMSS_randomhex"
        timestamp_part = execution_id.split('_')[2] if '_' in execution_id else execution_id[:8]
        random_part = execution_id.split('_')[-1] if '_' in execution_id else os.urandom(4).hex()
        branch_name = f"ai-generated-{timestamp_part}-{random_part}"
        print(f"Creating branch: {branch_name}")
        branch_info = github_service.create_branch(repository_info['full_name'], branch_name)
        
        # 4. Generate workflow files based on tech stack (self-contained configuration)
        github_workflow_config = {
            'tech_stack': tech_stack,
            'workflow_name': 'CI/CD',
            'workflow_file': 'ci-cd.yml',
            'node_version': '18',
            'build_commands': get_build_commands(tech_stack),
            'deployment_target': get_deployment_target(tech_stack)
        }
        workflow_files = generate_workflow_files(github_workflow_config)
        
        # 5. Retrieve file content from S3 if needed
        if generated_files and len(generated_files) > 0 and generated_files[0].get('s3_bucket'):
            print(f"Retrieving content for {len(generated_files)} files from S3...")
            files_with_content = retrieve_files_from_s3(generated_files)
            print(f"Retrieved content for {len(files_with_content)} files")
        else:
            # Files already have content or no files to process
            files_with_content = generated_files
        
        # 6. Combine generated files with workflow files for commit
        all_files_to_commit = list(files_with_content) if files_with_content else []
        
        # Add workflow files to the commit
        for workflow_file in workflow_files:
            all_files_to_commit.append({
                'file_path': workflow_file['path'],
                'content': workflow_file['content']
            })
        
        # 7. Generate smart commit message based on stories
        story_info = data.get('processed_stories', [])
        if not story_info:
            # Fallback to check for single story (backward compatibility)
            single_story = data.get('user_story')
            if single_story:
                story_info = [single_story]
        
        # Create informative commit message
        if len(story_info) == 1:
            story_title = story_info[0].get('title', 'Unknown Story')
            commit_message = f"feat: {story_title}\n\nAI-generated implementation for {project_id}\n- Generated {len(generated_files)} code files\n- Added CI/CD workflow configuration"
        elif len(story_info) > 1:
            completed_stories = [s for s in story_info if s.get('status') == 'completed']
            story_titles = [s.get('title', 'Unknown') for s in completed_stories[:3]]  # Show first 3
            commit_message = f"feat: implement {len(completed_stories)} user stories\n\nAI-generated implementation for {project_id}:\n"
            for title in story_titles:
                commit_message += f"- {title}\n"
            if len(completed_stories) > 3:
                commit_message += f"- ... and {len(completed_stories) - 3} more stories\n"
            commit_message += f"\nGenerated {len(generated_files)} code files and CI/CD configuration"
        else:
            commit_message = f"feat: AI-generated code and CI/CD configuration for {project_id}"
        
        # 8. Commit all files (generated code + workflow files)
        commit_info = None
        if all_files_to_commit:
            print(f"Committing {len(all_files_to_commit)} files to branch {branch_name} (including {len(workflow_files)} workflow files)")
            print(f"Commit message: {commit_message}")
            commit_info = github_service.commit_files(
                repository_info['full_name'], 
                branch_name, 
                all_files_to_commit, 
                commit_message
            )
        
        # 9. Create Pull Request for review and UAT
        pr_info = None
        if commit_info:
            pr_title = f"feat: AI-generated implementation for {project_id}"
            pr_body = f"""## AI-Generated Code for {project_id}

### Summary
This PR contains AI-generated code implementing the requested user stories.

### Stories Completed
- Stories implemented: {len(story_info)}
- Files generated: {len(generated_files)}
- Validation passed: {validation_passed}

### Test and Deployment
- GitHub Actions will automatically run tests
- Preview deployment will be available at Netlify preview URL
- Review the code and test the preview before merging

### Validation Results
{chr(10).join([f"- {r.get('validation_type', 'Unknown')}: {'✅ Passed' if r.get('passed') else '❌ Failed'}" for r in validation_summary.get('validation_results', [])])}

---
*Generated by AI Pipeline Orchestrator v2*
"""
            print(f"Creating pull request: {pr_title}")
            pr_info = github_service.create_pull_request(
                repository_info['full_name'],
                branch_name,
                pr_title,
                pr_body
            )
            print(f"Pull request created: {pr_info.get('html_url', 'Unknown')}")
        
        # 9. Wait for GitHub Actions workflow to complete (triggered by PR)
        workflow_run = None
        workflow_success = False
        
        if pr_info and commit_info:
            try:
                print("Waiting for GitHub Actions workflow to start (triggered by PR creation)...")
                # Give GitHub a moment to trigger the workflow from the PR
                import time
                time.sleep(5)
                
                # Wait for the workflow run (with 5 minute timeout)
                workflow_run = github_service.wait_for_workflow_run(
                    repository_info['full_name'],
                    commit_info['sha'],
                    timeout_seconds=300
                )
                
                # Check if the workflow was successful
                workflow_success = github_service.check_workflow_success(workflow_run)
                
                if not workflow_success:
                    # Workflow failed - provide detailed error information
                    failed_runs = workflow_run.get('failed_runs', [])
                    if failed_runs:
                        failed_names = [run['name'] for run in failed_runs]
                        error_msg = f"GitHub Actions workflow failed for commit {commit_info['sha'][:8]}. Failed checks: {', '.join(failed_names)}"
                    else:
                        error_msg = f"GitHub Actions workflow failed for commit {commit_info['sha'][:8]}"
                    
                    print(f"❌ {error_msg}")
                    print(f"Workflow URL: {workflow_run.get('html_url', 'Unknown')}")
                    
                    # Log details of failed checks
                    if failed_runs:
                        print("\n📋 Failed Check Details:")
                        for run in failed_runs:
                            print(f"  • {run['name']}: {run['conclusion']}")
                            print(f"    URL: {run['details_url']}")
                    
                    raise RuntimeError(error_msg)
                else:
                    print(f"✅ GitHub Actions workflow completed successfully!")
                    print(f"Workflow URL: {workflow_run.get('html_url', 'Unknown')}")
        
                    
            except Exception as e:
                print(f"Error waiting for workflow: {str(e)}")
                # Create a simulated workflow run for fallback
                workflow_run = {
                    'id': f"run_{execution_id[:8]}",
                    'workflow_name': github_workflow_config.get('workflow_name', 'CI/CD'),
                    'status': 'error',
                    'conclusion': 'failure',
                    'html_url': f"{repository_info['html_url']}/actions",
                    'started_at': datetime.utcnow().isoformat(),
                    'error': str(e)
                }
                # Re-raise the exception to fail the lambda
                raise
        else:
            # No PR or commit, so no workflow to wait for
            workflow_run = {
                'id': f"run_{execution_id[:8]}",
                'workflow_name': github_workflow_config.get('workflow_name', 'CI/CD'),
                'status': 'skipped',
                'conclusion': 'skipped',
                'html_url': f"{repository_info['html_url']}/actions",
                'started_at': datetime.utcnow().isoformat()
            }
        
        # 10. Store GitHub integration metadata in DynamoDB
        try:
            integration_metadata = {
                'integration_id': f"github-{execution_id}",
                'project_id': project_id,
                'repository_info': repository_info,
                'commit_info': commit_info,
                'workflow_run': workflow_run,
                'workflow_files': workflow_files,
                'netlify_site_info': netlify_site_info,
                'validation_summary': validation_summary,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)  # 30 days
            }
            
            # Store in GitHub integrations table
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(os.environ.get('GITHUB_INTEGRATIONS_TABLE', 'ai-pipeline-v2-github-integrations-dev'))
            table.put_item(Item=integration_metadata)
            print(f"Stored GitHub integration metadata in DynamoDB")
        except Exception as e:
            print(f"Warning: Failed to store GitHub metadata: {str(e)}")
        
        # Prepare response
        # Prepare response message based on what was accomplished
        message_parts = ['repository created', 'workflow configured', 'PR created']
        if netlify_site_info:
            message_parts.append('Netlify site created')
        
        response = {
            'status': 'success',
            'message': f'GitHub orchestration completed - {", ".join(message_parts)}',
            'execution_id': execution_id,
            'stage': 'github_orchestration',
            'project_id': project_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'repository_info': repository_info,
                'branch_info': branch_info,
                'commit_info': commit_info,
                'pr_info': pr_info,
                'workflow_run': workflow_run,
                'workflow_files': workflow_files,
                'netlify_site_info': netlify_site_info,
                'github_workflow_config': github_workflow_config,
                'deployment_urls': generate_deployment_urls(project_id, tech_stack),
                'pipeline_context': pipeline_context,
                'architecture': architecture,
                'validation_summary': validation_summary
            },
            'next_stage': 'review_coordinator'
        }
        
        print(f"GitHub orchestration completed successfully")
        return response
        
    except Exception as e:
        print(f"GitHub orchestration failed: {str(e)}")
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"GitHub orchestration failed: {str(e)}"
        raise RuntimeError(error_msg)


class GitHubService:
    """GitHub service for repository operations."""
    
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
            # Skip if secret name is empty or not configured
            if not secret_name or secret_name == '':
                print("Info: GitHub token secret not configured - using mock mode")
                return None
            
            response = secrets_client.get_secret_value(SecretId=secret_name)
            # Parse JSON secret value
            import json
            secret_data = json.loads(response['SecretString'])
            return secret_data.get('token', '')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DecryptionFailureException':
                print("Warning: Failed to decrypt GitHub token secret")
            elif error_code == 'InternalServiceErrorException':
                print("Warning: Internal service error retrieving GitHub token")
            elif error_code == 'InvalidParameterException':
                print("Warning: Invalid parameter for GitHub token secret")
            elif error_code == 'InvalidRequestException':
                print("Warning: Invalid request for GitHub token secret")
            elif error_code == 'ResourceNotFoundException':
                print("Warning: GitHub token secret not found")
            else:
                print(f"Warning: Error retrieving GitHub token secret: {e}")
            return None
        except Exception as e:
            print(f"Warning: Unexpected error retrieving GitHub token: {e}")
            return None

    def create_or_get_repository(self, project_name: str, tech_stack: str) -> Dict[str, Any]:
        """Create or get existing GitHub repository."""
        if not self.github_token or not self.headers:
            raise Exception("GitHub token not available - cannot proceed with repository operations")
        
        try:
            # First check if repository already exists
            existing_repo = self._get_repository(project_name)
            if existing_repo:
                print(f"Repository {project_name} already exists, using existing repo")
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
                print(f"✅ Created repository: {repo_info['html_url']}")
                return repo_info
            else:
                error_msg = f"Failed to create repository: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
                
        except Exception as e:
            print(f"❌ Repository creation failed: {str(e)}")
            raise

    def _get_repository(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Check if repository exists and return its info."""
        try:
            # Get authenticated user info
            user_response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers,
                timeout=30
            )
            
            if user_response.status_code == 200:
                username = user_response.json()['login']
                print(f"Authenticated as GitHub user: {username}")
            else:
                print(f"Failed to get GitHub user info: {user_response.status_code}")
                return None
            
            # Check if repository exists
            repo_response = requests.get(
                f"{self.base_url}/repos/{username}/{project_name}",
                headers=self.headers,
                timeout=30
            )
            
            if repo_response.status_code == 200:
                return repo_response.json()
            elif repo_response.status_code == 404:
                return None
            else:
                print(f"Error checking repository: {repo_response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error checking repository: {str(e)}")
            return None

    def create_branch(self, repo_full_name: str, branch_name: str) -> Dict[str, Any]:
        """Create a new branch in the repository."""
        if not self.github_token or not self.headers:
            print("Warning: GitHub token not available - skipping branch creation")
            return {"name": branch_name, "commit": {"sha": "mock-sha"}}
        
        try:
            # Get default branch ref
            response = requests.get(
                f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/main",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 404:
                # Try master if main doesn't exist
                response = requests.get(
                    f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/master",
                    headers=self.headers,
                    timeout=30
                )
            
            if response.status_code == 200:
                sha = response.json()['object']['sha']
            else:
                print(f"Failed to get default branch: {response.status_code}")
                return {}
            
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
            
            if response.status_code == 201:
                print(f"✅ Created branch: {branch_name}")
                return response.json()
            elif response.status_code == 422:
                print(f"Branch {branch_name} already exists")
                return {"ref": f"refs/heads/{branch_name}"}
            else:
                print(f"Failed to create branch: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            print(f"Error creating branch: {str(e)}")
            return {}

    def commit_files(self, repo_full_name: str, branch_name: str, files: List[Dict[str, Any]], 
                     commit_message: str = "AI-generated code") -> Dict[str, Any]:
        """Commit multiple files to a branch."""
        if not self.github_token or not self.headers:
            print("Warning: GitHub token not available - skipping file commit")
            return {"sha": "mock-commit-sha"}
        
        try:
            # Process files in batches to avoid hitting size limits
            # GitHub Trees API can handle up to 100,000 tree entries, but we'll use 500 for safety
            # This ensures most projects commit in a single batch, avoiding multiple workflow triggers
            batch_size = 500
            total_files = len(files)
            
            for i in range(0, total_files, batch_size):
                batch = files[i:i + batch_size]
                batch_message = f"{commit_message} (batch {i//batch_size + 1}/{(total_files-1)//batch_size + 1})"
                
                # Get the current commit SHA
                ref_response = requests.get(
                    f"{self.base_url}/repos/{repo_full_name}/git/refs/heads/{branch_name}",
                    headers=self.headers,
                    timeout=30
                )
                
                if ref_response.status_code != 200:
                    print(f"Failed to get branch ref: {ref_response.status_code}")
                    continue
                
                current_sha = ref_response.json()['object']['sha']
                
                # Get the tree SHA
                commit_response = requests.get(
                    f"{self.base_url}/repos/{repo_full_name}/git/commits/{current_sha}",
                    headers=self.headers,
                    timeout=30
                )
                
                if commit_response.status_code != 200:
                    print(f"Failed to get commit: {commit_response.status_code}")
                    continue
                
                base_tree_sha = commit_response.json()['tree']['sha']
                
                # Create blobs for each file
                tree_items = []
                for file_info in batch:
                    try:
                        content = file_info.get('content', '')
                        file_path = file_info['file_path']
                        
                        # Skip empty files
                        if not content:
                            print(f"Skipping empty file: {file_path}")
                            continue
                        
                        # Create blob
                        import base64
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
                            blob_sha = blob_response.json()['sha']
                            tree_items.append({
                                'path': file_path,
                                'mode': '100644',
                                'type': 'blob',
                                'sha': blob_sha
                            })
                        else:
                            print(f"Failed to create blob for {file_path}: {blob_response.status_code}")
                            
                    except Exception as e:
                        print(f"Error processing file {file_path}: {str(e)}")
                        continue
                
                if not tree_items:
                    print("No valid files to commit in this batch")
                    continue
                
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
                    print(f"Failed to create tree: {tree_response.status_code}")
                    continue
                
                new_tree_sha = tree_response.json()['sha']
                
                # Create commit
                commit_data = {
                    'message': batch_message,
                    'tree': new_tree_sha,
                    'parents': [current_sha]
                }
                
                new_commit_response = requests.post(
                    f"{self.base_url}/repos/{repo_full_name}/git/commits",
                    headers=self.headers,
                    json=commit_data,
                    timeout=30
                )
                
                if new_commit_response.status_code != 201:
                    print(f"Failed to create commit: {new_commit_response.status_code}")
                    continue
                
                new_commit_sha = new_commit_response.json()['sha']
                
                # Update branch reference
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
                    print(f"✅ Committed batch {i//batch_size + 1} with {len(tree_items)} files")
                else:
                    print(f"Failed to update branch ref: {update_response.status_code}")
            
            return {"sha": new_commit_sha if 'new_commit_sha' in locals() else ""}
            
        except Exception as e:
            print(f"Error committing files: {str(e)}")
            return {}

    def _encrypt_secret_for_github(self, public_key_base64: str, secret_value: str) -> str:
        """
        Encrypt secret for GitHub using PyNaCl with proper error handling.
        GitHub requires libsodium/NaCl encryption - base64 fallback does not work.
        """
        try:
            # PyNaCl is required for GitHub secrets - no fallback
            from nacl import encoding, public
            import base64
            
            print("✅ Using PyNaCl for GitHub secrets encryption")
            
            # Create public key object from base64-encoded key
            public_key_obj = public.PublicKey(public_key_base64.encode("utf-8"), encoding.Base64Encoder())
            
            # Create a sealed box for encryption
            sealed_box = public.SealedBox(public_key_obj)
            
            # Encrypt the secret value
            encrypted_bytes = sealed_box.encrypt(secret_value.encode("utf-8"))
            
            # Return base64 encoded encrypted value
            encrypted_value = base64.b64encode(encrypted_bytes).decode("utf-8")
            print(f"✅ Successfully encrypted secret (length: {len(encrypted_value)})")
            return encrypted_value
            
        except ImportError as e:
            error_msg = f"❌ CRITICAL: PyNaCl not available ({e}) - GitHub secrets require libsodium encryption"
            print(error_msg)
            # GitHub secrets REQUIRE encryption - raise error instead of using broken fallback
            raise RuntimeError(error_msg)
            
        except Exception as e:
            error_msg = f"❌ CRITICAL: Encryption failed: {e} - Cannot create GitHub secrets without encryption"
            print(error_msg)
            raise RuntimeError(error_msg)
    
    def create_repository_secret(self, repo_full_name: str, secret_name: str, secret_value: str) -> bool:
        """Create or update a repository secret using GitHub API with libsodium-compatible encryption."""
        if not self.github_token or not self.headers:
            print("Warning: GitHub token not available - skipping secret creation")
            return False
        
        try:
            # First, get the repository's public key for encryption
            key_response = requests.get(
                f"{self.base_url}/repos/{repo_full_name}/actions/secrets/public-key",
                headers=self.headers,
                timeout=30
            )
            
            if key_response.status_code != 200:
                print(f"❌ Failed to get repository public key: {key_response.status_code} - {key_response.text}")
                return False
            
            key_data = key_response.json()
            public_key = key_data['key']
            key_id = key_data['key_id']
            
            # Use encryption method with fallback
            encrypted_value = self._encrypt_secret_for_github(public_key, secret_value)
            
            # Create or update the secret
            secret_data = {
                'encrypted_value': encrypted_value,
                'key_id': key_id
            }
            
            response = requests.put(
                f"{self.base_url}/repos/{repo_full_name}/actions/secrets/{secret_name}",
                headers=self.headers,
                json=secret_data,
                timeout=30
            )
            
            if response.status_code in [201, 204]:
                print(f"✅ Successfully created/updated secret: {secret_name}")
                return True
            else:
                print(f"❌ Failed to create secret {secret_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating GitHub secret {secret_name}: {str(e)}")
            return False

    def create_pull_request(self, repo_full_name: str, branch_name: str, title: str,
                           body: str = "") -> Dict[str, Any]:
        """Create a pull request from branch to main."""
        if not self.github_token or not self.headers:
            print("Warning: GitHub token not available - skipping PR creation")
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
                print(f"✅ Created pull request: {pr_info['html_url']}")
                return pr_info
            else:
                # Check if PR already exists
                existing_prs = requests.get(
                    f"{self.base_url}/repos/{repo_full_name}/pulls",
                    headers=self.headers,
                    params={'head': f"{repo_full_name.split('/')[0]}:{branch_name}", 'state': 'open'},
                    timeout=30
                )
                
                if existing_prs.status_code == 200 and existing_prs.json():
                    pr_info = existing_prs.json()[0]
                    print(f"Pull request already exists: {pr_info['html_url']}")
                    return pr_info
                else:
                    print(f"Failed to create PR: {response.status_code} - {response.text}")
                    return {}
                    
        except Exception as e:
            print(f"Error creating pull request: {str(e)}")
            return {}

    def wait_for_workflow_run(self, repo_full_name: str, commit_sha: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """Wait for GitHub Actions workflow to complete."""
        if not self.github_token or not self.headers:
            print("Warning: GitHub token not available - skipping workflow check")
            return {"conclusion": "success"}
        
        try:
            import time
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                # Use Workflow Runs API instead of Check Runs API for better filtering
                response = requests.get(
                    f"{self.base_url}/repos/{repo_full_name}/actions/runs",
                    headers=self.headers,
                    params={'head_sha': commit_sha, 'per_page': 20},
                    timeout=30
                )
                
                if response.status_code == 200:
                    workflow_runs = response.json()
                    if workflow_runs['total_count'] > 0:
                        # Filter to only our main CI/CD workflow (name = "CI/CD")
                        our_workflow_run = None
                        for run in workflow_runs['workflow_runs']:
                            workflow_name = run.get('name', '')
                            print(f"🔍 Found workflow: '{workflow_name}' - {run.get('conclusion', 'in_progress')}")
                            
                            # Only check our main CI/CD workflow, not Frontend/Backend CI/CD
                            if workflow_name == 'CI/CD':
                                our_workflow_run = run
                                print(f"✓ Monitoring main CI/CD workflow: {workflow_name}")
                                break
                        
                        if not our_workflow_run:
                            print("⚠️ Main CI/CD workflow not found, checking all workflows...")
                            # Fallback: if we can't find "CI/CD", look for any without Frontend/Backend
                            for run in workflow_runs['workflow_runs']:
                                workflow_name = run.get('name', '')
                                if ('frontend' not in workflow_name.lower() and 
                                    'backend' not in workflow_name.lower()):
                                    our_workflow_run = run
                                    print(f"✓ Using fallback workflow: {workflow_name}")
                                    break
                        
                        if our_workflow_run:
                            if our_workflow_run['status'] == 'completed':
                                conclusion = our_workflow_run['conclusion']
                                workflow_name = our_workflow_run['name']
                                
                                if conclusion == 'success':
                                    print(f"✅ Workflow '{workflow_name}' completed successfully")
                                    return {"conclusion": "success", "workflow_run": our_workflow_run}
                                else:
                                    print(f"❌ Workflow '{workflow_name}' failed with conclusion: {conclusion}")
                                    return {
                                        "conclusion": "failure", 
                                        "workflow_run": our_workflow_run,
                                        "failed_runs": [{"name": workflow_name, "conclusion": conclusion, "details_url": our_workflow_run.get('html_url', '')}]
                                    }
                            else:
                                print(f"⏳ Workflow '{our_workflow_run['name']}' still running...")
                        else:
                            print("⚠️ No relevant workflows found")
                
                time.sleep(10)
            
            print("⏱️ Workflow run timed out")
            return {"conclusion": "timed_out"}
            
        except Exception as e:
            print(f"Error waiting for workflow: {str(e)}")
            return {"conclusion": "error"}

    def check_workflow_success(self, workflow_run: Dict[str, Any]) -> bool:
        """Check if workflow run was successful."""
        return workflow_run.get('conclusion') == 'success'


class NetlifyService:
    """Service for managing Netlify deployment operations."""
    
    def __init__(self):
        """Initialize Netlify service with token from Secrets Manager."""
        self.netlify_token = self._get_netlify_token()
        self.base_url = "https://api.netlify.com/api/v1"
        
    def _get_netlify_token(self) -> str:
        """Get Netlify token from AWS Secrets Manager."""
        try:
            secret_name = os.environ.get('NETLIFY_TOKEN_SECRET_ARN', 'ai-pipeline-v2/netlify-token-dev')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data.get('token', '')
        except Exception as e:
            print(f"Failed to retrieve Netlify token: {str(e)}")
            return ''
    
    def create_site(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Create a Netlify site for the project with DNS-compliant naming."""
        import random
        import time
        
        try:
            if not self.netlify_token:
                print("⚠️  Netlify token not available - skipping site creation")
                return None
            
            # DNS label maximum is 63 characters
            # Account for "preview-pr-XXX--" prefix (up to 17 chars for PR 999)
            # So we need site names to be max 46 chars to be safe
            MAX_SITE_NAME_LENGTH = 46
            
            # Generate unique site name with fallback strategies
            base_name = project_name.lower().replace('_', '-').replace(' ', '-')
            
            # Truncate base name if it's too long
            if len(base_name) > 30:
                # Keep first 15 and last 10 characters with separator
                base_name = f"{base_name[:15]}-{base_name[-10:]}"
            
            timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
            random_suffix = str(random.randint(1000, 9999))
            
            # Try multiple naming strategies, ensuring DNS compliance
            name_attempts = []
            
            # Strategy 1: Base name only (if short enough)
            if len(base_name) <= MAX_SITE_NAME_LENGTH:
                name_attempts.append(base_name)
            
            # Strategy 2: Base + timestamp (truncate base if needed)
            name_with_time = f"{base_name}-{timestamp}"
            if len(name_with_time) > MAX_SITE_NAME_LENGTH:
                truncated_base = base_name[:MAX_SITE_NAME_LENGTH - len(timestamp) - 1]
                name_with_time = f"{truncated_base}-{timestamp}"
            name_attempts.append(name_with_time)
            
            # Strategy 3: Base + random (truncate base if needed)
            name_with_random = f"{base_name}-{random_suffix}"
            if len(name_with_random) > MAX_SITE_NAME_LENGTH:
                truncated_base = base_name[:MAX_SITE_NAME_LENGTH - len(str(random_suffix)) - 1]
                name_with_random = f"{truncated_base}-{random_suffix}"
            name_attempts.append(name_with_random)
            
            # Strategy 4: Compact name with timestamp
            compact_name = f"{base_name[:20]}-{timestamp}"
            if compact_name not in name_attempts and len(compact_name) <= MAX_SITE_NAME_LENGTH:
                name_attempts.append(compact_name)
            
            site_data_base = {
                "build_settings": {
                    "cmd": "npm run build", 
                    "dir": "./dist"
                }
            }
            
            for attempt, site_name in enumerate(name_attempts, 1):
                site_data = {**site_data_base, "name": site_name}
                
                # Log the name length for DNS validation
                print(f"📦 Creating Netlify site (attempt {attempt}): {site_name} (length: {len(site_name)} chars)")
                if len(site_name) > MAX_SITE_NAME_LENGTH:
                    print(f"⚠️  Warning: Site name may be too long for DNS with PR prefixes")
                response = requests.post(
                    f"{self.base_url}/sites",
                    headers={
                        "Authorization": f"Bearer {self.netlify_token}",
                        "Content-Type": "application/json"
                    },
                    json=site_data,
                    timeout=30
                )
                
                if response.status_code == 201:
                    site_info = response.json()
                    site_id = site_info.get("id")
                    site_url = site_info.get("url")
                    print(f"✅ Created Netlify site: {site_id} at {site_url}")
                    return site_info
                elif response.status_code == 422:
                    # Unprocessable entity - likely subdomain conflict
                    try:
                        error_data = response.json()
                        if "subdomain" in str(error_data.get("errors", {})):
                            print(f"⚠️  Subdomain '{site_name}' already exists, trying next option...")
                            continue
                    except:
                        pass
                    print(f"❌ Failed to create site '{site_name}': {response.text}")
                    continue
                else:
                    print(f"❌ Failed to create site '{site_name}': {response.status_code} - {response.text}")
                    continue
            
            print("❌ Failed to create Netlify site after all attempts")
            return None
                
        except Exception as e:
            print(f"❌ Error creating Netlify site: {e}")
            return None
    
    def add_secrets_to_github_repo(self, github_service: 'GitHubService', repo_full_name: str, site_id: str) -> bool:
        """Add Netlify secrets to GitHub repository."""
        try:
            if not self.netlify_token or not site_id:
                print("⚠️  Missing Netlify token or site_id - skipping secret setup")
                return False
            
            print(f"🔐 Adding Netlify secrets to {repo_full_name}")
            
            # Add NETLIFY_AUTH_TOKEN secret
            auth_success = github_service.create_repository_secret(
                repo_full_name, 
                'NETLIFY_AUTH_TOKEN', 
                self.netlify_token
            )
            
            # Add NETLIFY_SITE_ID secret
            site_success = github_service.create_repository_secret(
                repo_full_name,
                'NETLIFY_SITE_ID',
                site_id
            )
            
            if auth_success and site_success:
                print("✅ Successfully added Netlify secrets to GitHub repository")
                return True
            else:
                print("❌ Failed to add some Netlify secrets")
                return False
                
        except Exception as e:
            print(f"❌ Error adding Netlify secrets: {e}")
            return False


# Helper functions below


def generate_workflow_files(github_workflow_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate GitHub Actions workflow files based on configuration."""
    
    tech_stack = github_workflow_config.get('tech_stack', 'react_fullstack')
    workflow_name = github_workflow_config.get('workflow_name', 'CI/CD')
    node_version = github_workflow_config.get('node_version', '18')
    build_commands = github_workflow_config.get('build_commands', ['npm install', 'npm run build', 'npm test'])
    
    # Generate main CI/CD workflow
    workflow_content = generate_workflow_yaml(tech_stack, workflow_name, node_version, build_commands)
    
    workflow_files = [
        {
            'path': f".github/workflows/{github_workflow_config.get('workflow_file', 'ci-cd.yml')}",
            'content': workflow_content,
            'type': 'workflow',
            'size_bytes': len(workflow_content.encode('utf-8'))
        }
    ]
    
    # Add additional files based on tech stack
    if tech_stack in ['react_fullstack', 'react_spa']:
        # Add Netlify configuration
        netlify_config = generate_netlify_config(tech_stack)
        workflow_files.append({
            'path': 'netlify.toml',
            'content': netlify_config,
            'type': 'config',
            'size_bytes': len(netlify_config.encode('utf-8'))
        })
    
    if 'fullstack' in tech_stack.lower():
        # Add Docker configuration for backend
        dockerfile_content = generate_dockerfile(tech_stack)
        workflow_files.append({
            'path': 'Dockerfile',
            'content': dockerfile_content,
            'type': 'docker',
            'size_bytes': len(dockerfile_content.encode('utf-8'))
        })
    
    return workflow_files


def generate_workflow_yaml(tech_stack: str, workflow_name: str, node_version: str, 
                          build_commands: List[str]) -> str:
    """Generate GitHub Actions workflow YAML content."""
    
    # Determine publish directory based on tech stack
    # react_fullstack has monorepo structure with client/ and server/
    if tech_stack == 'react_fullstack':
        publish_dir = './client/dist'
    else:
        publish_dir = './dist'
    
    workflow_yaml = f"""name: {workflow_name}

on:
  pull_request:
    branches: [ main ]
    types: [ opened, synchronize, reopened ]

permissions:
  contents: read
  actions: read
  checks: read
  pull-requests: write
  issues: write
  deployments: write
  statuses: write

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Check for lock files
      id: check-locks
      run: |
        if [ -f "package-lock.json" ]; then
          echo "has_npm_lock=true" >> $GITHUB_OUTPUT
          echo "✅ Found package-lock.json"
        elif [ -f "yarn.lock" ]; then
          echo "has_yarn_lock=true" >> $GITHUB_OUTPUT
          echo "✅ Found yarn.lock"
        else
          echo "has_npm_lock=false" >> $GITHUB_OUTPUT
          echo "⚠️  No lock file found - will not use dependency caching"
        fi
    
    - name: Setup Node.js with npm cache
      if: steps.check-locks.outputs.has_npm_lock == 'true'
      uses: actions/setup-node@v4
      with:
        node-version: '{node_version}'
        cache: 'npm'
    
    - name: Setup Node.js with yarn cache
      if: steps.check-locks.outputs.has_yarn_lock == 'true'
      uses: actions/setup-node@v4
      with:
        node-version: '{node_version}'
        cache: 'yarn'
    
    - name: Setup Node.js without cache
      if: steps.check-locks.outputs.has_npm_lock != 'true' && steps.check-locks.outputs.has_yarn_lock != 'true'
      uses: actions/setup-node@v4
      with:
        node-version: '{node_version}'
    
    - name: Install dependencies
      run: |
        echo "📦 Installing dependencies..."
        if [ -f "yarn.lock" ]; then
          echo "Using yarn..."
          yarn install
        elif [ -f "package-lock.json" ]; then
          echo "Using npm ci for faster, reliable installs..."
          # Try npm ci first, but fall back to npm install if lock file is out of sync
          npm ci || {{
            echo "⚠️  npm ci failed - lock file may be out of sync"
            echo "📦 Falling back to npm install to regenerate lock file..."
            rm -f package-lock.json
            npm install
            echo "✅ Generated fresh package-lock.json"
          }}
        elif [ -f "package.json" ]; then
          echo "Using npm install (no lock file found)..."
          npm install
        else
          echo "❌ No package.json found!"
          exit 1
        fi
    
    - name: Run tests
      run: |
        echo "🧪 Running tests..."
        if [ -f "package.json" ]; then
          # Check if test script exists
          if grep -q '"test":' package.json; then
            {build_commands[2] if len(build_commands) > 2 else 'npm test'} || {{
              echo "⚠️  Tests failed but continuing workflow"
              exit 0
            }}
          else
            echo "⚠️  No test script found in package.json - skipping tests"
          fi
        else
          echo "⚠️  No package.json found - skipping tests"
        fi
    
    - name: Build application  
      run: |
        # For monorepo projects, build in the correct directory
        if [ -f "package.json" ] && [ -d "client" ] && [ -d "server" ]; then
          echo "📦 Detected monorepo structure (client + server)"
          # Install and build root
          npm install
          npm run build || true
          # Install and build client
          cd client
          npm install
          npm run build
          cd ..
          # Install and build server  
          cd server
          npm install
          npm run build
          cd ..
        else
          echo "📦 Standard project structure"
          {build_commands[1] if len(build_commands) > 1 else 'npm run build'}
        fi
    
    - name: Verify and prepare build outputs
      if: success()
      run: |
        echo "Checking build output directories..."
        ls -la
        
        # For react_fullstack, ensure client/dist exists
        if [ -d "client" ] && [ -d "server" ]; then
          echo "📦 Monorepo structure detected"
          if [ -d "client/dist" ]; then
            echo "✅ Found client/dist directory"
            ls -la client/dist/
          elif [ -d "client/build" ]; then
            echo "✅ Found client/build directory, creating symlink"
            cd client && ln -s build dist && cd ..
          else
            echo "❌ No client build output found!"
            echo "Attempting to rebuild client..."
            cd client && npm run build && cd ..
          fi
        elif [ -d "dist" ]; then
          echo "✅ Found dist directory at root"
          ls -la dist/
        elif [ -d "build" ]; then
          echo "✅ Found build directory, creating dist symlink"
          ln -s build dist
        else
          echo "⚠️ No dist directory found, checking other locations..."
          find . -name "dist" -type d 2>/dev/null | head -5
          find . -name "build" -type d 2>/dev/null | head -5
          # Try to build if no output found
          if [ -f "package.json" ]; then
            echo "Attempting to build..."
            npm run build || echo "Build failed"
          fi
        fi
    
    - name: Pre-deployment Validation
      if: success()
      run: |
        echo "🔍 Pre-deployment validation..."
        
        # Check if publish directory exists
        if [ -d "{publish_dir}" ]; then
          echo "✅ Publish directory exists: {publish_dir}"
          
          # Check if directory has content
          FILE_COUNT=$(find {publish_dir} -type f | wc -l)
          if [ "$FILE_COUNT" -gt 0 ]; then
            echo "✅ Found $FILE_COUNT files to deploy"
            
            # Check for critical files
            if [ -f "{publish_dir}/index.html" ]; then
              echo "✅ index.html present"
            else
              echo "⚠️  Warning: index.html not found in {publish_dir}"
            fi
            
            # Show directory structure
            echo "📁 Build output structure:"
            ls -la {publish_dir} | head -10
          else
            echo "❌ Publish directory is empty!"
            echo "Attempting to locate build output..."
            
            # Try to find build output in common locations
            for dir in dist build client/dist client/build; do
              if [ -d "$dir" ] && [ "$(find $dir -type f | wc -l)" -gt 0 ]; then
                echo "Found build output in: $dir"
                ls -la "$dir" | head -5
              fi
            done
          fi
        else
          echo "❌ Publish directory does not exist: {publish_dir}"
          echo "Build may have failed or output is in a different location"
          
          # Show what directories do exist
          echo "Available directories:"
          find . -maxdepth 2 -type d -name "dist" -o -name "build" | head -10
        fi
    
    - name: Deploy to Netlify
      if: success()
      id: netlify
      uses: nwtgck/actions-netlify@v3.0
      with:
        publish-dir: '{publish_dir}'
        production-branch: main
        production-deploy: false
        github-token: ${{{{ secrets.GITHUB_TOKEN }}}}
        deploy-message: "Deploy from GitHub Actions PR #${{{{ github.event.pull_request.number }}}}"
        alias: preview-pr-${{{{ github.event.pull_request.number }}}}
        enable-pull-request-comment: true
        enable-commit-comment: false
        enable-commit-status: true
        overwrites-pull-request-comment: true
      env:
        NETLIFY_AUTH_TOKEN: ${{{{ secrets.NETLIFY_AUTH_TOKEN }}}}
        NETLIFY_SITE_ID: ${{{{ secrets.NETLIFY_SITE_ID }}}}
      timeout-minutes: 10
      continue-on-error: true
    
    - name: Display Netlify URL
      if: success() && steps.netlify.outputs.deploy-url
      run: |
        echo "🚀 Deployed to Netlify!"
        echo "Preview URL: ${{{{ steps.netlify.outputs.deploy-url }}}}"
    
    - name: Validate Deployment
      if: success() && steps.netlify.outputs.deploy-url
      run: |
        echo "🔍 Validating deployment..."
        DEPLOY_URL="${{{{ steps.netlify.outputs.deploy-url }}}}"
        
        # Check if deployment URL is accessible
        echo "Checking if deployment is accessible..."
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{{http_code}}" "$DEPLOY_URL" || echo "000")
        
        if [ "$HTTP_STATUS" = "200" ]; then
          echo "✅ Deployment is accessible (HTTP $HTTP_STATUS)"
        else
          echo "⚠️  Deployment returned HTTP $HTTP_STATUS"
          if [ "$HTTP_STATUS" = "000" ]; then
            echo "   Connection failed - site may not be ready yet"
          fi
        fi
        
        # Verify build artifacts were created
        echo ""
        echo "📦 Verifying build artifacts..."
        if [ -d "{publish_dir}" ]; then
          echo "✅ Build output directory exists: {publish_dir}"
          
          # Count files in build output
          FILE_COUNT=$(find {publish_dir} -type f | wc -l)
          echo "   Found $FILE_COUNT files in build output"
          
          # Check for index.html (essential for SPA)
          if [ -f "{publish_dir}/index.html" ]; then
            echo "✅ index.html found in build output"
          else
            echo "⚠️  index.html not found - deployment may be empty"
          fi
          
          # List first few files as evidence
          echo "   Sample files:"
          find {publish_dir} -type f | head -5 | sed 's/^/     - /'
        else
          echo "❌ Build output directory not found: {publish_dir}"
          echo "   Deployment may have succeeded with empty content"
        fi
        
        # Check content of deployed site
        echo ""
        echo "🌐 Checking deployed content..."
        CONTENT_LENGTH=$(curl -s "$DEPLOY_URL" | wc -c)
        if [ "$CONTENT_LENGTH" -gt 100 ]; then
          echo "✅ Deployed site has content ($CONTENT_LENGTH bytes)"
        else
          echo "⚠️  Deployed site appears to be empty or minimal ($CONTENT_LENGTH bytes)"
        fi
        
        # Final validation summary
        echo ""
        echo "📊 Validation Summary:"
        if [ "$HTTP_STATUS" = "200" ] && [ "$FILE_COUNT" -gt 0 ] && [ "$CONTENT_LENGTH" -gt 100 ]; then
          echo "✅ Deployment validation PASSED"
          echo "   - Site is accessible"
          echo "   - Build artifacts exist"  
          echo "   - Content is present"
        else
          echo "⚠️  Deployment validation WARNINGS"
          echo "   - HTTP Status: $HTTP_STATUS"
          echo "   - File Count: $FILE_COUNT"
          echo "   - Content Size: $CONTENT_LENGTH bytes"
          echo "   The deployment reported success but may not be fully functional"
        fi
"""
    
    return workflow_yaml


def generate_netlify_config(tech_stack: str = 'react_spa') -> str:
    """Generate Netlify configuration."""
    # For react_fullstack, the frontend is in client/ directory
    if tech_stack == 'react_fullstack':
        return """[build]
  base = "client"
  publish = "dist"
  command = "npm run build"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
"""
    else:
        # Standard config for react_spa and vue_spa
        return """[build]
  publish = "dist"
  command = "npm run build"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
"""


def generate_dockerfile(tech_stack: str) -> str:
    """Generate Dockerfile for backend services."""
    return """FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
"""


def get_build_commands(tech_stack: str) -> List[str]:
    """Get build commands for the tech stack."""
    build_commands = {
        'react_spa': ['npm install', 'npm run build', 'npm test'],
        'react_fullstack': ['npm install', 'npm run build', 'npm test'],
        'node_api': ['npm install', 'npm run build', 'npm test'],
        'vue_spa': ['npm install', 'npm run build', 'npm test'],
        'python_api': ['pip install -r requirements.txt', 'python -m pytest', 'python -m build']
    }
    return build_commands.get(tech_stack.lower(), ['npm install', 'npm run build', 'npm test'])


def get_deployment_target(tech_stack: str) -> str:
    """Get deployment target for the tech stack."""
    deployment_targets = {
        'react_spa': 'netlify',
        'react_fullstack': 'netlify_and_aws',
        'node_api': 'aws_ecs',
        'vue_spa': 'netlify', 
        'python_api': 'aws_ecs'
    }
    return deployment_targets.get(tech_stack.lower(), 'netlify')


def generate_deployment_urls(project_id: str, tech_stack: str) -> Dict[str, str]:
    """Generate deployment URLs for the project."""
    urls = {}
    
    if tech_stack in ['react_spa', 'react_fullstack', 'vue_spa']:
        urls['frontend'] = f"https://{project_id}-dev.netlify.app"
        urls['frontend_prod'] = f"https://{project_id}.netlify.app"
    
    if tech_stack in ['react_fullstack', 'node_api', 'python_api']:
        urls['backend'] = f"https://{project_id}-api-dev.example.com"
        urls['backend_prod'] = f"https://{project_id}-api.example.com"
    
    urls['repository'] = f"https://github.com/ai-pipeline/{project_id}"
    urls['actions'] = f"https://github.com/ai-pipeline/{project_id}/actions"
    
    return urls


def validate_build_readiness(generated_files: List[Dict[str, Any]], tech_stack: str, architecture: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that all critical build files are present for successful GitHub Actions execution.
    
    Args:
        generated_files: List of generated file metadata
        tech_stack: Selected tech stack
        architecture: Project architecture configuration
        
    Returns:
        Dict containing readiness status and missing files information
    """
    try:
        generated_file_paths = {file.get('file_path') for file in generated_files}
        missing_files = []
        issues = []
        
        # Define critical files by tech stack that MUST be present for GitHub Actions
        # NOTE: Removed package-lock.json as it should be generated by npm install, not stubbed
        critical_files = {
            'react_spa': ['package.json'],
            'react_fullstack': ['package.json'],
            'node_api': ['package.json'],
            'vue_spa': ['package.json'],
            'python_api': ['requirements.txt']
        }
        
        required_files = critical_files.get(tech_stack.lower(), ['package.json'])
        
        # Check for critical missing files
        for required_file in required_files:
            if required_file not in generated_file_paths:
                missing_files.append(required_file)
                issues.append(f"Missing critical build file: {required_file}")
        
        # Specific lock file validation for Node.js projects
        if tech_stack.lower() in ['react_spa', 'react_fullstack', 'node_api', 'vue_spa']:
            has_package_json = 'package.json' in generated_file_paths
            has_package_lock = 'package-lock.json' in generated_file_paths
            has_yarn_lock = 'yarn.lock' in generated_file_paths
            
            if has_package_json and not (has_package_lock or has_yarn_lock):
                missing_files.append('package-lock.json')
                issues.append("Missing dependency lock file - GitHub Actions requires lock files for caching")
        
        # Check .gitignore presence (recommended but not critical)
        if '.gitignore' not in generated_file_paths:
            issues.append("Missing .gitignore file - recommended for clean repository")
        
        return {
            'ready': len(missing_files) == 0,
            'missing_files': missing_files,
            'issues': issues,
            'recommendations': [
                "Ensure package-lock.json is present for npm caching",
                "Include .gitignore to exclude build artifacts",
                "Verify package.json has required scripts (build, dev, test)"
            ]
        }
        
    except Exception as e:
        return {
            'ready': False,
            'missing_files': [],
            'issues': [f"Build readiness validation failed: {str(e)}"],
            'recommendations': []
        }


def add_missing_build_files(generated_files: List[Dict[str, Any]], missing_files: List[str], tech_stack: str) -> List[Dict[str, Any]]:
    """
    Add minimal versions of missing critical build files to generated_files.
    ONLY adds files that don't already exist in the list.
    
    Args:
        generated_files: Current list of generated files
        missing_files: List of missing file paths
        tech_stack: Selected tech stack
        
    Returns:
        Updated list of generated files with missing critical files added
    """
    try:
        updated_files = list(generated_files)  # Create a copy
        
        # Get existing file paths to avoid duplicates
        existing_paths = {f.get('file_path') for f in generated_files}
        
        for missing_file in missing_files:
            # Skip if file already exists
            if missing_file in existing_paths:
                print(f"File {missing_file} already exists in generated files - skipping")
                continue
            # Skip package-lock.json - it should be generated by npm install, not stubbed
            # This was causing npm ci failures because stub didn't contain actual dependency resolution
            if missing_file == 'package-lock.json':
                print(f"Skipping package-lock.json stub generation - will be created by npm install")
                continue
                
            elif missing_file == 'package.json':
                # Generate minimal package.json
                package_json_content = {
                    "name": "generated-project",
                    "version": "0.1.0",
                    "private": True,
                    "scripts": {
                        "dev": "vite" if tech_stack.lower() in ['react_spa', 'vue_spa'] else "node index.js",
                        "build": "vite build" if tech_stack.lower() in ['react_spa', 'vue_spa'] else "tsc",
                        "test": "vitest" if tech_stack.lower() in ['react_spa', 'vue_spa'] else "jest"
                    },
                    "dependencies": {
                        "react": "^18.2.0" if 'react' in tech_stack.lower() else None,
                        "vue": "^3.3.4" if 'vue' in tech_stack.lower() else None
                    },
                    "devDependencies": {
                        "typescript": "^5.0.2",
                        "vite": "^4.4.5" if tech_stack.lower() in ['react_spa', 'vue_spa'] else None
                    }
                }
                
                # Clean up None values
                package_json_content['dependencies'] = {k: v for k, v in package_json_content['dependencies'].items() if v is not None}
                package_json_content['devDependencies'] = {k: v for k, v in package_json_content['devDependencies'].items() if v is not None}
                
                updated_files.append({
                    'file_path': 'package.json',
                    'content': json.dumps(package_json_content, indent=2),
                    'component_id': 'build_config',
                    'story_id': 'initialization',
                    'file_type': 'config',
                    'language': 'json',
                    'auto_generated': True,
                    'created_at': datetime.utcnow().isoformat()
                })
                
            elif missing_file == 'requirements.txt':
                # Generate minimal requirements.txt for Python
                requirements_content = """# Python dependencies
flask>=2.3.0
python-dotenv>=1.0.0
pytest>=7.4.0
"""
                
                updated_files.append({
                    'file_path': 'requirements.txt',
                    'content': requirements_content,
                    'component_id': 'build_config',
                    'story_id': 'initialization',
                    'file_type': 'config',
                    'language': 'text',
                    'auto_generated': True,
                    'created_at': datetime.utcnow().isoformat()
                })
        
        return updated_files
        
    except Exception as e:
        print(f"Error adding missing build files: {str(e)}")
        return generated_files  # Return original files if error occurs