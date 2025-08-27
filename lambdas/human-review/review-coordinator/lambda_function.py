"""
Review Coordinator Lambda

Coordinates human review workflow via GitHub PRs, tracks review status, and manages automated merge processes.
This lambda monitors PR reviews and handles the final merge based on configuration settings.

Author: AI Pipeline Orchestrator v2
Version: 1.0.0
"""

import json
import os
from typing import Dict, Any, List, Optional
import boto3
from datetime import datetime, timedelta
import requests

# Configure logging directly to avoid pydantic dependencies
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main lambda handler for review coordination.
    
    Args:
        event: Lambda event containing GitHub integration info and review configuration
        context: Lambda runtime context
        
    Returns:
        Dict containing review coordination results and next actions
    """
    execution_id = f"review_coord_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{context.aws_request_id[:8] if context else 'local'}"
    logger.info(f"Starting review coordination with execution_id: {execution_id}")
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        logger.info(f"Event type: {type(event)}, Keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
        
        # Extract execution context - handle sequential flow from GitHubOrchestrator
        github_result = event.get('githubOrchestratorResult', {}).get('Payload', {})
        
        if github_result.get('status') == 'success':
            # Extract project_id from the root level of the GitHub orchestrator response
            project_name = github_result.get('project_id', 'unknown')
            
            github_data = github_result.get('data', {})
            
            # Extract GitHub integration data from orchestrator result
            github_integration = {
                'repository_info': github_data.get('repository_info', {}),
                'pr_info': github_data.get('pr_info', {})
            }
            
            # Get pipeline context from data
            project_context = github_data.get('pipeline_context', {})
            execution_context = {
                'review_config': {
                    'enable_human_review': True,
                    'auto_merge_conditions': {
                        'min_approvals': 1,
                        'merge_method': 'squash'
                    },
                    'review_timeout_hours': 24
                }
            }
        else:
            # Fallback for direct invocation or error cases
            project_context = event.get('project_context', {}) if isinstance(event, dict) else {}
            execution_context = event.get('execution_context', {}) if isinstance(event, dict) else {}
            github_integration = event.get('github_integration', {}) if isinstance(event, dict) else {}
            project_name = project_context.get('project_name', 'unknown')
            
        review_config = execution_context.get('review_config', {})
        
        # For now, skip actual review coordination and return success
        if not github_integration.get('repository_info'):
            logger.info("No GitHub integration data available - skipping review coordination")
            return {
                "status": "success",
                "message": "Review coordination skipped - no GitHub integration data",
                "execution_id": execution_id,
                "stage": "review_coordination",
                "project_id": project_name,
                "timestamp": datetime.utcnow().isoformat(),
                "requiresReview": "false",  # No review needed when skipping
                "data": {
                    'review_coordination': {
                        'action_taken': {'action': 'skipped', 'reason': 'No GitHub integration data'},
                        'pipeline_complete': True
                    },
                    'pipeline_complete': True,
                    'next_stage': None
                }
            }
        
        logger.info(f"Starting review coordination for project: {project_name}")
        
        # Initialize services
        dynamodb = boto3.resource('dynamodb')
        github_service = GitHubReviewService()
        
        # Extract PR and repository information
        repository_full_name = github_integration['repository_info']['full_name']
        pr_number = github_integration['pr_info']['number']
        pr_url = github_integration['pr_info']['html_url']
        
        # Check review configuration
        enable_human_review = review_config.get('enable_human_review', True)
        auto_merge_conditions = review_config.get('auto_merge_conditions', {})
        review_timeout_hours = review_config.get('review_timeout_hours', 24)
        
        # Get current PR status and reviews
        pr_status = github_service.get_pull_request_status(repository_full_name, pr_number)
        pr_reviews = github_service.get_pull_request_reviews(repository_full_name, pr_number)
        pr_checks = github_service.get_pull_request_checks(repository_full_name, pr_number)
        
        # Determine review decision
        review_decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks, 
            enable_human_review, auto_merge_conditions, review_timeout_hours
        )
        
        # Execute decision
        action_taken = None
        if review_decision['action'] == 'merge':
            merge_result = github_service.merge_pull_request(
                repository_full_name, pr_number, review_decision['merge_method']
            )
            action_taken = {
                'action': 'merged',
                'merge_sha': merge_result.get('sha'),
                'merged_at': datetime.utcnow().isoformat()
            }
            
        elif review_decision['action'] == 'request_changes':
            comment_result = github_service.add_pr_comment(
                repository_full_name, pr_number, review_decision['comment']
            )
            action_taken = {
                'action': 'requested_changes',
                'comment_id': comment_result.get('id'),
                'comment_url': comment_result.get('html_url')
            }
            
        elif review_decision['action'] == 'wait':
            # Set up monitoring for continued review tracking
            action_taken = {
                'action': 'waiting',
                'wait_reason': review_decision['reason'],
                'next_check_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
        
        # Store review coordination results
        review_coordination = {
            'execution_id': execution_id,
            'project_name': project_name,
            'repository_full_name': repository_full_name,
            'pr_number': pr_number,
            'pr_url': pr_url,
            'review_decision': review_decision,
            'action_taken': action_taken,
            'pr_status': pr_status,
            'review_count': len(pr_reviews),
            'checks_passing': all(check.get('conclusion') == 'success' for check in pr_checks),
            'coordinated_at': datetime.utcnow().isoformat()
        }
        
        # Store in DynamoDB
        try:
            table_name = os.environ.get('REVIEW_REQUESTS_TABLE', 'ai-pipeline-v2-component-specs-dev')
            table = dynamodb.Table(table_name)
            table.put_item(
                Item={
                    'review_id': f"review-{execution_id}",
                    'created_at': datetime.utcnow().isoformat(),  # Add required created_at field
                    'review_coordination': review_coordination,
                    'ttl': int(datetime.utcnow().timestamp()) + (90 * 24 * 60 * 60)  # 90 days
                }
            )
        except Exception as e:
            logger.warning(f"Failed to store review coordination in DynamoDB: {str(e)}")
        
        # Determine if pipeline is complete
        pipeline_complete = action_taken and action_taken['action'] in ['merged', 'requested_changes']
        next_stage = None if pipeline_complete else 'review-monitor'
        
        # Determine if review is required (inverse of pipeline complete for Step Functions)
        requires_review = str(not pipeline_complete).lower()  # Convert boolean to "true"/"false" string
        
        # Prepare response as plain dictionary
        response = {
            "status": "success",
            "message": "Review coordination completed successfully",
            "execution_id": execution_id,
            "stage": "review_coordination",
            "project_id": project_context.get('project_id', 'unknown'),
            "timestamp": datetime.utcnow().isoformat(),
            "requiresReview": requires_review,  # Add this field for Step Functions workflow
            "data": {
                'review_coordination': review_coordination,
                'pipeline_complete': pipeline_complete,
                'next_stage': next_stage,
                'pr_url': pr_url,
                'action_summary': f"{action_taken['action'] if action_taken else 'no_action'} - {review_decision['reason']}"
            }
        }
        
        logger.info(f"Review coordination completed successfully for execution_id: {execution_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in review coordination: {str(e)}", exc_info=True)
        
        # Return proper error status - raise exception for Step Functions to handle
        error_msg = f"Review coordination failed: {str(e)}"
        raise RuntimeError(error_msg)


class GitHubReviewService:
    """Service for GitHub review operations."""
    
    def __init__(self):
        """Initialize GitHub review service with authentication."""
        self.base_url = "https://api.github.com"
        self.token = self._get_github_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    def _get_github_token(self) -> str:
        """Get GitHub token from AWS Secrets Manager."""
        try:
            secret_name = os.environ.get('GITHUB_TOKEN_SECRET_ARN', 'ai-pipeline-v2/github-token-dev')
            response = secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data.get('token', '')
        except Exception as e:
            logger.error(f"Failed to retrieve GitHub token: {str(e)}")
            raise ValueError("GitHub token not available")
    
    def get_pull_request_status(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request status and metadata."""
        response = requests.get(
            f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get PR status: {response.text}")
        
        pr_data = response.json()
        return {
            'state': pr_data['state'],
            'mergeable': pr_data.get('mergeable'),
            'mergeable_state': pr_data.get('mergeable_state'),
            'draft': pr_data.get('draft', False),
            'created_at': pr_data['created_at'],
            'updated_at': pr_data['updated_at']
        }
    
    def get_pull_request_reviews(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get pull request reviews."""
        response = requests.get(
            f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/reviews",
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to get PR reviews: {response.text}")
            return []
        
        reviews = response.json()
        return [
            {
                'id': review['id'],
                'user': review['user']['login'],
                'state': review['state'],
                'submitted_at': review.get('submitted_at'),
                'body': review.get('body', '')
            }
            for review in reviews
        ]
    
    def get_pull_request_checks(self, repo_full_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get pull request status checks."""
        # First get the PR to get the head SHA
        pr_response = requests.get(
            f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}",
            headers=self.headers
        )
        
        if pr_response.status_code != 200:
            logger.warning(f"Failed to get PR for checks: {pr_response.text}")
            return []
        
        head_sha = pr_response.json()['head']['sha']
        
        # Get check runs for the head SHA
        response = requests.get(
            f"{self.base_url}/repos/{repo_full_name}/commits/{head_sha}/check-runs",
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to get check runs: {response.text}")
            return []
        
        check_runs = response.json().get('check_runs', [])
        return [
            {
                'id': check['id'],
                'name': check['name'],
                'status': check['status'],
                'conclusion': check.get('conclusion'),
                'started_at': check.get('started_at'),
                'completed_at': check.get('completed_at')
            }
            for check in check_runs
        ]
    
    def merge_pull_request(self, repo_full_name: str, pr_number: int, merge_method: str = 'merge') -> Dict[str, Any]:
        """Merge a pull request."""
        merge_data = {
            'merge_method': merge_method,
            'commit_title': f'Merge AI-generated code (#{pr_number})',
            'commit_message': 'AI Pipeline Orchestrator v2 - Automated merge after review'
        }
        
        response = requests.put(
            f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/merge",
            headers=self.headers,
            json=merge_data
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to merge PR: {response.text}")
        
        return response.json()
    
    def add_pr_comment(self, repo_full_name: str, pr_number: int, comment: str) -> Dict[str, Any]:
        """Add comment to pull request."""
        comment_data = {'body': comment}
        
        response = requests.post(
            f"{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers=self.headers,
            json=comment_data
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to add PR comment: {response.text}")
        
        return response.json()


def evaluate_review_decision(pr_status: Dict[str, Any], pr_reviews: List[Dict[str, Any]], 
                           pr_checks: List[Dict[str, Any]], enable_human_review: bool,
                           auto_merge_conditions: Dict[str, Any], review_timeout_hours: int) -> Dict[str, Any]:
    """
    Evaluate what action to take based on PR status, reviews, and configuration.
    
    Returns:
        Dict with 'action', 'reason', and additional action-specific parameters
    """
    # Check if PR is draft or closed
    if pr_status.get('draft', False):
        return {'action': 'wait', 'reason': 'PR is in draft state'}
    
    if pr_status.get('state') == 'closed':
        return {'action': 'skip', 'reason': 'PR is already closed'}
    
    # Check if PR is mergeable
    if not pr_status.get('mergeable', True):
        return {
            'action': 'request_changes',
            'reason': 'PR has merge conflicts',
            'comment': '❌ This PR has merge conflicts that need to be resolved before merging.'
        }
    
    # Check status checks
    checks_passing = all(check.get('conclusion') == 'success' for check in pr_checks if check.get('status') == 'completed')
    checks_pending = any(check.get('status') == 'in_progress' for check in pr_checks)
    
    if checks_pending:
        return {'action': 'wait', 'reason': 'Checks are still running'}
    
    if not checks_passing:
        failing_checks = [check['name'] for check in pr_checks if check.get('conclusion') == 'failure']
        return {
            'action': 'request_changes',
            'reason': 'Some checks are failing',
            'comment': f'❌ The following checks are failing: {", ".join(failing_checks)}. Please fix these issues before merging.'
        }
    
    # Analyze reviews
    latest_reviews = {}
    for review in pr_reviews:
        user = review['user']
        # Keep only the latest review from each user
        if user not in latest_reviews or review['submitted_at'] > latest_reviews[user]['submitted_at']:
            latest_reviews[user] = review
    
    approved_reviews = [r for r in latest_reviews.values() if r['state'] == 'APPROVED']
    changes_requested = [r for r in latest_reviews.values() if r['state'] == 'CHANGES_REQUESTED']
    
    # Check if human review is required
    if enable_human_review:
        min_approvals = auto_merge_conditions.get('min_approvals', 1)
        
        if changes_requested:
            return {
                'action': 'wait',
                'reason': f'Changes requested by: {", ".join([r["user"] for r in changes_requested])}'
            }
        
        if len(approved_reviews) >= min_approvals:
            return {
                'action': 'merge',
                'reason': f'Approved by {len(approved_reviews)} reviewer(s)',
                'merge_method': auto_merge_conditions.get('merge_method', 'merge')
            }
        
        # Check for timeout
        created_at = datetime.fromisoformat(pr_status['created_at'].replace('Z', '+00:00'))
        hours_elapsed = (datetime.now(created_at.tzinfo) - created_at).total_seconds() / 3600
        
        if hours_elapsed >= review_timeout_hours:
            return {
                'action': 'merge',
                'reason': f'Review timeout reached ({review_timeout_hours}h), auto-merging',
                'merge_method': auto_merge_conditions.get('merge_method', 'merge')
            }
        
        return {
            'action': 'wait',
            'reason': f'Waiting for {min_approvals - len(approved_reviews)} more approval(s)'
        }
    
    else:
        # Auto-merge if human review is disabled and checks pass
        return {
            'action': 'merge',
            'reason': 'Human review disabled, auto-merging after checks pass',
            'merge_method': auto_merge_conditions.get('merge_method', 'merge')
        }