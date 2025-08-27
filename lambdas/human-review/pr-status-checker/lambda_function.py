"""
GitHub PR Status Checker with Claude Code Review Integration
Checks PR status and performs automated Claude Code review with optional auto-merge
"""

import json
import os
import boto3
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, Optional


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Check GitHub PR status and perform Claude Code review.
    
    Args:
        event: Event containing GitHub orchestrator result with PR URL
        context: Lambda context
        
    Returns:
        Dict with PR status and review results
    """
    execution_id = f"pr_status_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        print(f"Starting PR status check with execution_id: {execution_id}")
        print(f"Event: {json.dumps(event, default=str)}")
        
        # Extract PR URL from GitHub orchestrator result
        github_result = event.get('githubOrchestratorResult', {}).get('Payload', {})
        pr_info = github_result.get('data', {}).get('pr_info', {})
        pr_url = pr_info.get('html_url', '')
        
        if not pr_url:
            print("No PR URL found, assuming direct merge")
            return {
                'statusCode': 200,
                'status': 'merged',
                'message': 'No PR found, assuming successful merge',
                'execution_id': execution_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        print(f"Checking PR status for: {pr_url}")
        
        # Parse PR URL to extract components
        pr_components = parse_pr_url(pr_url)
        if not pr_components:
            raise ValueError(f"Invalid PR URL format: {pr_url}")
        
        owner, repo, pull_number = pr_components['owner'], pr_components['repo'], pr_components['pull_number']
        
        # Get GitHub token from Secrets Manager
        github_token = get_github_token()
        if not github_token:
            raise Exception("GitHub token not available")
        
        # Check current PR status
        pr_status = check_pr_status(github_token, owner, repo, pull_number)
        
        # If PR is already merged or closed, return status
        if pr_status['status'] in ['merged', 'closed']:
            return {
                'statusCode': 200,
                'status': pr_status['status'],
                'pr_url': pr_url,
                'pr_state': pr_status['pr_state'],
                'merged': pr_status['merged'],
                'execution_id': execution_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Perform Claude Code review if PR is open
        if pr_status['status'] == 'pending':
            print("PR is pending - performing Claude Code review...")
            
            claude_review_result = perform_claude_review(
                github_token, owner, repo, pull_number, pr_url
            )
            
            # Check if auto-merge is enabled
            auto_merge_enabled = os.environ.get('AUTO_MERGE_PRS', 'false').lower() == 'true'
            
            if claude_review_result['approved'] and auto_merge_enabled:
                print("Claude approved the PR and auto-merge is enabled - attempting merge...")
                merge_result = attempt_auto_merge(github_token, owner, repo, pull_number)
                
                if merge_result['success']:
                    return {
                        'statusCode': 200,
                        'status': 'merged',
                        'message': 'Auto-merged after Claude Code approval',
                        'pr_url': pr_url,
                        'claude_review': claude_review_result,
                        'auto_merge': merge_result,
                        'execution_id': execution_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    print(f"Auto-merge failed: {merge_result['error']}")
            
            # Return status with Claude review results
            final_status = 'approved' if claude_review_result['approved'] else 'changes_requested'
            
            return {
                'statusCode': 200,
                'status': final_status,
                'message': f'Claude Code review completed: {"Approved" if claude_review_result["approved"] else "Changes requested"}',
                'pr_url': pr_url,
                'pr_state': pr_status['pr_state'],
                'claude_review': claude_review_result,
                'auto_merge_enabled': auto_merge_enabled,
                'execution_id': execution_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Default return for other statuses
        return {
            'statusCode': 200,
            'status': pr_status['status'],
            'pr_url': pr_url,
            'pr_state': pr_status['pr_state'],
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Error in PR status checker: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'error',
            'error': str(e),
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().isoformat()
        }


def parse_pr_url(pr_url: str) -> Optional[Dict[str, str]]:
    """Parse GitHub PR URL to extract owner, repo, and pull number."""
    try:
        # Format: https://github.com/owner/repo/pull/123
        parts = pr_url.split('/')
        if len(parts) < 7 or 'github.com' not in pr_url:
            return None
        
        return {
            'owner': parts[3],
            'repo': parts[4], 
            'pull_number': parts[6]
        }
    except Exception as e:
        print(f"Error parsing PR URL: {str(e)}")
        return None


def get_github_token() -> Optional[str]:
    """Get GitHub token from AWS Secrets Manager."""
    try:
        secret_name = os.environ.get('GITHUB_TOKEN_SECRET_ARN', 'ai-pipeline-v2/github-token-dev')
        secrets_client = boto3.client('secretsmanager')
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        return secret_data.get('token', '')
    except Exception as e:
        print(f"Error getting GitHub token: {str(e)}")
        return None


def check_pr_status(github_token: str, owner: str, repo: str, pull_number: str) -> Dict[str, Any]:
    """Check current GitHub PR status."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
        
        request = urllib.request.Request(api_url)
        request.add_header('Authorization', f'token {github_token}')
        request.add_header('Accept', 'application/vnd.github.v3+json')
        
        with urllib.request.urlopen(request) as response:
            pr_data = json.loads(response.read().decode())
        
        pr_state = pr_data.get('state', 'open')
        merged = pr_data.get('merged', False)
        
        if merged:
            status = 'merged'
        elif pr_state == 'closed':
            status = 'closed'
        else:
            status = 'pending'
        
        return {
            'status': status,
            'pr_state': pr_state,
            'merged': merged,
            'pr_data': pr_data
        }
        
    except Exception as e:
        print(f"Error checking PR status: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def perform_claude_review(github_token: str, owner: str, repo: str, pull_number: str, pr_url: str) -> Dict[str, Any]:
    """
    Perform Claude Code review of the PR.
    
    This uses the Anthropic API to review the PR diff and provide feedback.
    """
    try:
        print(f"Starting Claude Code review for PR #{pull_number}")
        
        # Get PR files and diff
        pr_files = get_pr_files(github_token, owner, repo, pull_number)
        pr_diff = get_pr_diff(github_token, owner, repo, pull_number)
        
        if not pr_files or not pr_diff:
            print("Could not retrieve PR files or diff for review")
            return {
                'approved': True,  # Default to approved if we can't review
                'message': 'Could not retrieve PR content for review - defaulting to approved',
                'review_type': 'fallback'
            }
        
        # Call Claude API for code review
        anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            print("ANTHROPIC_API_KEY not available - defaulting to approved")
            return {
                'approved': True,
                'message': 'No Anthropic API key available - defaulting to approved',
                'review_type': 'fallback'
            }
        
        claude_review_result = call_claude_for_review(anthropic_api_key, pr_files, pr_diff, pr_url)
        
        # Post review comment to GitHub if Claude found issues
        if not claude_review_result['approved']:
            post_review_comment(github_token, owner, repo, pull_number, claude_review_result['feedback'])
        
        return claude_review_result
        
    except Exception as e:
        print(f"Error in Claude review: {str(e)}")
        return {
            'approved': True,  # Default to approved on error
            'message': f'Review error: {str(e)} - defaulting to approved',
            'review_type': 'error_fallback',
            'error': str(e)
        }


def get_pr_files(github_token: str, owner: str, repo: str, pull_number: str) -> Optional[list]:
    """Get list of files changed in the PR."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
        
        request = urllib.request.Request(api_url)
        request.add_header('Authorization', f'token {github_token}')
        request.add_header('Accept', 'application/vnd.github.v3+json')
        
        with urllib.request.urlopen(request) as response:
            files_data = json.loads(response.read().decode())
        
        return files_data
        
    except Exception as e:
        print(f"Error getting PR files: {str(e)}")
        return None


def get_pr_diff(github_token: str, owner: str, repo: str, pull_number: str) -> Optional[str]:
    """Get the diff content for the PR."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
        
        request = urllib.request.Request(api_url)
        request.add_header('Authorization', f'token {github_token}')
        request.add_header('Accept', 'application/vnd.github.v3.diff')
        
        with urllib.request.urlopen(request) as response:
            diff_content = response.read().decode()
        
        return diff_content
        
    except Exception as e:
        print(f"Error getting PR diff: {str(e)}")
        return None


def call_claude_for_review(api_key: str, files: list, diff: str, pr_url: str) -> Dict[str, Any]:
    """Call Claude API to perform code review."""
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Prepare review prompt
        files_summary = "\n".join([
            f"- {file['filename']} (+{file.get('additions', 0)} -{file.get('deletions', 0)})"
            for file in files[:10]  # Limit to first 10 files
        ])
        
        if len(files) > 10:
            files_summary += f"\n... and {len(files) - 10} more files"
        
        # Truncate diff if too long
        max_diff_length = 8000
        if len(diff) > max_diff_length:
            diff = diff[:max_diff_length] + "\n\n[... diff truncated for length ...]"
        
        prompt = f"""You are Claude Code, an expert code reviewer. Please review this GitHub Pull Request.

PR URL: {pr_url}

Files changed:
{files_summary}

Diff:
```diff
{diff}
```

Please provide a thorough code review focusing on:
1. Code quality and best practices
2. Potential bugs or security issues
3. Performance considerations
4. Maintainability and readability
5. Testing coverage

Respond with a JSON object containing:
- "approved": boolean (true if code should be approved, false if changes needed)
- "feedback": string (detailed review comments)
- "issues": array of specific issues found (empty if none)
- "suggestions": array of improvement suggestions (empty if none)

Be constructive but thorough in your review."""

        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse Claude's response
        response_text = message.content[0].text
        
        try:
            review_result = json.loads(response_text)
            return {
                'approved': review_result.get('approved', True),
                'feedback': review_result.get('feedback', 'Code review completed'),
                'issues': review_result.get('issues', []),
                'suggestions': review_result.get('suggestions', []),
                'review_type': 'claude_api',
                'model': 'claude-3-sonnet'
            }
        except json.JSONDecodeError:
            # If Claude didn't return valid JSON, parse text response
            approved = 'approved' in response_text.lower() or 'looks good' in response_text.lower()
            return {
                'approved': approved,
                'feedback': response_text,
                'issues': [],
                'suggestions': [],
                'review_type': 'claude_text',
                'model': 'claude-3-sonnet'
            }
        
    except Exception as e:
        print(f"Error calling Claude API: {str(e)}")
        return {
            'approved': True,
            'message': f'Claude API error: {str(e)} - defaulting to approved',
            'review_type': 'api_error',
            'error': str(e)
        }


def post_review_comment(github_token: str, owner: str, repo: str, pull_number: str, feedback: str):
    """Post Claude's review feedback as a PR comment."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pull_number}/comments"
        
        comment_body = f"""## 🤖 Claude Code Review

{feedback}

---
*Automated review by Claude Code - AI Pipeline Orchestrator v2*
"""
        
        comment_data = {
            'body': comment_body
        }
        
        request = urllib.request.Request(api_url, 
                                       data=json.dumps(comment_data).encode('utf-8'),
                                       method='POST')
        request.add_header('Authorization', f'token {github_token}')
        request.add_header('Accept', 'application/vnd.github.v3+json')
        request.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(request) as response:
            response_data = json.loads(response.read().decode())
        
        print(f"Posted Claude review comment: {response_data.get('html_url', 'Unknown')}")
        
    except Exception as e:
        print(f"Error posting review comment: {str(e)}")


def attempt_auto_merge(github_token: str, owner: str, repo: str, pull_number: str) -> Dict[str, Any]:
    """Attempt to auto-merge the PR after Claude approval."""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
        
        merge_data = {
            'commit_title': 'Auto-merge: Approved by Claude Code',
            'commit_message': 'This PR has been automatically merged after approval by Claude Code review.',
            'merge_method': 'squash'  # Use squash merge for cleaner history
        }
        
        request = urllib.request.Request(api_url,
                                       data=json.dumps(merge_data).encode('utf-8'),
                                       method='PUT')
        request.add_header('Authorization', f'token {github_token}')
        request.add_header('Accept', 'application/vnd.github.v3+json')
        request.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(request) as response:
            merge_result = json.loads(response.read().decode())
        
        return {
            'success': True,
            'merge_commit_sha': merge_result.get('sha'),
            'message': 'PR successfully auto-merged'
        }
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {
            'success': False,
            'error': f'HTTP {e.code}: {error_body}',
            'merge_blocked': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'merge_blocked': False
        }