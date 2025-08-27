"""Tests for Review Coordinator Lambda."""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Mock AWS services before importing lambda function
with patch('boto3.client'), patch('requests.get'), patch('requests.post'):
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from lambda_function import (
        lambda_handler,
        GitHubReviewService,
        evaluate_review_decision
    )


class TestReviewCoordinator:
    """Test cases for Review Coordinator Lambda."""

    @pytest.fixture
    def sample_event(self):
        """Sample event data for testing."""
        return {
            'project_context': {
                'project_name': 'test-project',
                'project_date': '2024-01-15'
            },
            'execution_context': {
                'execution_id': 'test-exec-123',
                'review_config': {
                    'enable_human_review': True,
                    'auto_merge_conditions': {
                        'min_approvals': 1,
                        'merge_method': 'merge'
                    },
                    'review_timeout_hours': 24
                }
            },
            'github_integration': {
                'repository_info': {
                    'full_name': 'test-owner/test-project-generated'
                },
                'pr_info': {
                    'number': 1,
                    'html_url': 'https://github.com/test-owner/test-project-generated/pull/1'
                }
            }
        }

    @pytest.fixture
    def lambda_context(self):
        """Mock Lambda context."""
        context = Mock()
        context.function_name = 'review-coordinator'
        context.function_version = '1'
        context.aws_request_id = 'test-request-id-123'
        return context

    @pytest.fixture
    def mock_github_service(self):
        """Mock GitHub review service."""
        service = Mock(spec=GitHubReviewService)
        service.get_pull_request_status.return_value = {
            'state': 'open',
            'mergeable': True,
            'mergeable_state': 'clean',
            'draft': False,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        service.get_pull_request_reviews.return_value = []
        service.get_pull_request_checks.return_value = [
            {
                'id': 1,
                'name': 'build',
                'status': 'completed',
                'conclusion': 'success'
            }
        ]
        return service

    @patch.dict(os.environ, {
        'COMPONENT_SPECS_TABLE': 'test-table',
        'GITHUB_TOKEN_SECRET': 'test-secret'
    })
    @patch('lambda_function.DynamoDBService')
    @patch('lambda_function.GitHubReviewService')
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    @patch('lambda_function.log_lambda_end')
    def test_lambda_handler_success_auto_merge(self, mock_log_end, mock_log_start, mock_setup_logger,
                                              mock_github_service_class, mock_dynamodb_service,
                                              sample_event, lambda_context, mock_github_service):
        """Test successful lambda handler with auto-merge."""
        # Setup mocks
        mock_log_start.return_value = 'test-execution-id'
        mock_setup_logger.return_value = Mock()
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb_service.return_value = mock_dynamodb_instance
        
        mock_github_service_class.return_value = mock_github_service
        mock_github_service.merge_pull_request.return_value = {'sha': 'merge-commit-sha'}
        
        # Modify event for auto-merge scenario (no human review required)
        sample_event['execution_context']['review_config']['enable_human_review'] = False
        
        # Execute
        result = lambda_handler(sample_event, lambda_context)
        
        # Verify
        assert result['success'] is True
        assert result['data']['pipeline_complete'] is True
        assert 'merged' in result['data']['action_summary']
        
        # Verify GitHub service calls
        mock_github_service.get_pull_request_status.assert_called_once()
        mock_github_service.merge_pull_request.assert_called_once()

    @patch.dict(os.environ, {
        'COMPONENT_SPECS_TABLE': 'test-table',
        'GITHUB_TOKEN_SECRET': 'test-secret'
    })
    @patch('lambda_function.DynamoDBService')
    @patch('lambda_function.GitHubReviewService')
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    @patch('lambda_function.log_lambda_end')
    def test_lambda_handler_waiting_for_review(self, mock_log_end, mock_log_start, mock_setup_logger,
                                             mock_github_service_class, mock_dynamodb_service,
                                             sample_event, lambda_context, mock_github_service):
        """Test lambda handler waiting for human review."""
        # Setup mocks
        mock_log_start.return_value = 'test-execution-id'
        mock_setup_logger.return_value = Mock()
        
        mock_dynamodb_instance = Mock()
        mock_dynamodb_service.return_value = mock_dynamodb_instance
        
        mock_github_service_class.return_value = mock_github_service
        # No reviews yet
        mock_github_service.get_pull_request_reviews.return_value = []
        
        # Execute
        result = lambda_handler(sample_event, lambda_context)
        
        # Verify
        assert result['success'] is True
        assert result['data']['pipeline_complete'] is False
        assert result['data']['next_stage'] == 'review-monitor'
        assert 'waiting' in result['data']['action_summary']

    @patch('lambda_function.secrets_client')
    def test_github_service_initialization(self, mock_secrets_client):
        """Test GitHub review service initialization."""
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        service = GitHubReviewService()
        
        assert service.token == 'test-token'
        assert 'Bearer test-token' in service.headers['Authorization']

    @patch('lambda_function.requests.get')
    @patch('lambda_function.secrets_client')
    def test_get_pull_request_status(self, mock_secrets_client, mock_get):
        """Test getting pull request status."""
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'state': 'open',
            'mergeable': True,
            'mergeable_state': 'clean',
            'draft': False,
            'created_at': '2024-01-15T10:00:00Z',
            'updated_at': '2024-01-15T11:00:00Z'
        }
        
        service = GitHubReviewService()
        status = service.get_pull_request_status('test-owner/test-repo', 1)
        
        assert status['state'] == 'open'
        assert status['mergeable'] is True
        assert status['draft'] is False

    @patch('lambda_function.requests.get')
    @patch('lambda_function.secrets_client')
    def test_get_pull_request_reviews(self, mock_secrets_client, mock_get):
        """Test getting pull request reviews."""
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                'id': 1,
                'user': {'login': 'reviewer1'},
                'state': 'APPROVED',
                'submitted_at': '2024-01-15T12:00:00Z',
                'body': 'Looks good!'
            },
            {
                'id': 2,
                'user': {'login': 'reviewer2'},
                'state': 'CHANGES_REQUESTED',
                'submitted_at': '2024-01-15T13:00:00Z',
                'body': 'Please fix the bug'
            }
        ]
        
        service = GitHubReviewService()
        reviews = service.get_pull_request_reviews('test-owner/test-repo', 1)
        
        assert len(reviews) == 2
        assert reviews[0]['state'] == 'APPROVED'
        assert reviews[1]['state'] == 'CHANGES_REQUESTED'

    @patch('lambda_function.requests.put')
    @patch('lambda_function.secrets_client')
    def test_merge_pull_request(self, mock_secrets_client, mock_put):
        """Test merging pull request."""
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'github_token': 'test-token'})
        }
        
        mock_put.return_value.status_code = 200
        mock_put.return_value.json.return_value = {
            'sha': 'merge-commit-sha',
            'merged': True,
            'message': 'Pull Request successfully merged'
        }
        
        service = GitHubReviewService()
        result = service.merge_pull_request('test-owner/test-repo', 1)
        
        assert result['merged'] is True
        assert 'sha' in result

    def test_evaluate_review_decision_auto_merge_disabled(self):
        """Test review decision evaluation with human review disabled."""
        pr_status = {'state': 'open', 'mergeable': True, 'draft': False}
        pr_reviews = []
        pr_checks = [{'status': 'completed', 'conclusion': 'success'}]
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=False,
            auto_merge_conditions={'merge_method': 'squash'},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'merge'
        assert decision['merge_method'] == 'squash'
        assert 'auto-merging' in decision['reason']

    def test_evaluate_review_decision_draft_pr(self):
        """Test review decision for draft PR."""
        pr_status = {'state': 'open', 'mergeable': True, 'draft': True}
        pr_reviews = []
        pr_checks = []
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'wait'
        assert 'draft' in decision['reason']

    def test_evaluate_review_decision_merge_conflicts(self):
        """Test review decision with merge conflicts."""
        pr_status = {'state': 'open', 'mergeable': False, 'draft': False}
        pr_reviews = []
        pr_checks = []
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'request_changes'
        assert 'merge conflicts' in decision['reason']
        assert 'comment' in decision

    def test_evaluate_review_decision_checks_pending(self):
        """Test review decision with pending checks."""
        pr_status = {'state': 'open', 'mergeable': True, 'draft': False}
        pr_reviews = []
        pr_checks = [{'status': 'in_progress', 'conclusion': None}]
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'wait'
        assert 'still running' in decision['reason']

    def test_evaluate_review_decision_checks_failing(self):
        """Test review decision with failing checks."""
        pr_status = {'state': 'open', 'mergeable': True, 'draft': False}
        pr_reviews = []
        pr_checks = [
            {'status': 'completed', 'conclusion': 'failure', 'name': 'build'},
            {'status': 'completed', 'conclusion': 'success', 'name': 'lint'}
        ]
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'request_changes'
        assert 'failing' in decision['reason']
        assert 'build' in decision['comment']

    def test_evaluate_review_decision_approved_review(self):
        """Test review decision with sufficient approvals."""
        pr_status = {'state': 'open', 'mergeable': True, 'draft': False}
        pr_reviews = [
            {
                'user': 'reviewer1',
                'state': 'APPROVED',
                'submitted_at': '2024-01-15T12:00:00Z'
            }
        ]
        pr_checks = [{'status': 'completed', 'conclusion': 'success'}]
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={'min_approvals': 1, 'merge_method': 'squash'},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'merge'
        assert decision['merge_method'] == 'squash'
        assert 'Approved' in decision['reason']

    def test_evaluate_review_decision_changes_requested(self):
        """Test review decision with changes requested."""
        pr_status = {'state': 'open', 'mergeable': True, 'draft': False}
        pr_reviews = [
            {
                'user': 'reviewer1',
                'state': 'CHANGES_REQUESTED',
                'submitted_at': '2024-01-15T12:00:00Z'
            }
        ]
        pr_checks = [{'status': 'completed', 'conclusion': 'success'}]
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={'min_approvals': 1},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'wait'
        assert 'Changes requested' in decision['reason']

    def test_evaluate_review_decision_timeout(self):
        """Test review decision with timeout."""
        # PR created 25 hours ago
        created_time = datetime.utcnow() - timedelta(hours=25)
        pr_status = {
            'state': 'open',
            'mergeable': True,
            'draft': False,
            'created_at': created_time.isoformat() + 'Z'
        }
        pr_reviews = []  # No reviews
        pr_checks = [{'status': 'completed', 'conclusion': 'success'}]
        
        decision = evaluate_review_decision(
            pr_status, pr_reviews, pr_checks,
            enable_human_review=True,
            auto_merge_conditions={'min_approvals': 1},
            review_timeout_hours=24
        )
        
        assert decision['action'] == 'merge'
        assert 'timeout' in decision['reason']

    @patch.dict(os.environ, {'COMPONENT_SPECS_TABLE': 'test-table'})
    @patch('lambda_function.setup_logger')
    @patch('lambda_function.log_lambda_start')
    def test_lambda_handler_missing_context(self, mock_log_start, mock_setup_logger, lambda_context):
        """Test lambda handler with missing required context."""
        mock_log_start.return_value = 'test-execution-id'
        mock_setup_logger.return_value = Mock()
        
        # Missing github_integration
        event = {
            'project_context': {
                'project_name': 'test-project'
            },
            'execution_context': {}
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['success'] is False
        assert 'Missing required context' in result['error']


if __name__ == '__main__':
    pytest.main([__file__])