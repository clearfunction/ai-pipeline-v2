"""
Structured logging service for AI Pipeline Orchestrator v2.

Provides centralized logging with execution context tracking and structured JSON output.
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger as loguru_logger
import uuid


def setup_logger(service_name: str) -> Any:
    """
    Setup structured logger for a Lambda function.
    
    Args:
        service_name: Name of the service/lambda function
        
    Returns:
        Configured logger instance
    """
    # Remove default handler
    loguru_logger.remove()
    
    # Add structured JSON handler for CloudWatch
    loguru_logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level="INFO",
        serialize=True
    )
    
    # Add service context
    service_logger = loguru_logger.bind(service=service_name)
    
    return service_logger


def log_lambda_start(event: Dict[str, Any], context: Any) -> str:
    """
    Log lambda function start with execution context.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Generated execution ID
    """
    execution_id = str(uuid.uuid4())
    
    loguru_logger.info(
        "Lambda execution started",
        execution_id=execution_id,
        function_name=getattr(context, 'function_name', 'unknown'),
        aws_request_id=getattr(context, 'aws_request_id', 'unknown'),
        remaining_time_ms=getattr(context, 'get_remaining_time_in_millis', lambda: 0)(),
        event_keys=list(event.keys()) if isinstance(event, dict) else [],
        timestamp=datetime.utcnow().isoformat()
    )
    
    return execution_id


def log_lambda_end(execution_id: str, response: Dict[str, Any]) -> None:
    """
    Log lambda function completion.
    
    Args:
        execution_id: Execution ID from lambda start
        response: Lambda response data
    """
    loguru_logger.info(
        "Lambda execution completed",
        execution_id=execution_id,
        success=response.get('success', False),
        response_keys=list(response.keys()) if isinstance(response, dict) else [],
        timestamp=datetime.utcnow().isoformat()
    )


def log_error(error: Exception, execution_id: str, stage: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log error with structured context.
    
    Args:
        error: Exception that occurred
        execution_id: Execution ID for tracking
        stage: Stage/component where error occurred
        context: Additional context data
    """
    error_context = {
        "execution_id": execution_id,
        "stage": stage,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if context:
        error_context.update(context)
    
    loguru_logger.error(
        f"Error in {stage}",
        **error_context
    )


def log_validation_result(validation_type: str, passed: bool, issues: list, execution_id: str) -> None:
    """
    Log validation results with structured data.
    
    Args:
        validation_type: Type of validation performed
        passed: Whether validation passed
        issues: List of validation issues
        execution_id: Execution ID for tracking
    """
    loguru_logger.info(
        f"Validation completed: {validation_type}",
        execution_id=execution_id,
        validation_type=validation_type,
        validation_passed=passed,
        issue_count=len(issues),
        issues=issues[:5] if len(issues) > 5 else issues,  # Limit issues in logs
        timestamp=datetime.utcnow().isoformat()
    )


def log_github_workflow_generation(tech_stack: str, workflow_name: str, execution_id: str) -> None:
    """
    Log GitHub workflow generation.
    
    Args:
        tech_stack: Technology stack
        workflow_name: Generated workflow name
        execution_id: Execution ID for tracking
    """
    loguru_logger.info(
        "GitHub workflow generated",
        execution_id=execution_id,
        tech_stack=tech_stack,
        workflow_name=workflow_name,
        timestamp=datetime.utcnow().isoformat()
    )