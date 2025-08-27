"""Shared logging configuration for all lambdas."""

import os
import sys
from loguru import logger
from typing import Optional


def setup_logger(
    lambda_name: str,
    log_level: Optional[str] = None,
    execution_id: Optional[str] = None
) -> None:
    """
    Set up structured logging for lambda functions.
    
    Args:
        lambda_name: Name of the lambda function
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        execution_id: Unique execution ID for tracing
    """
    # Remove default logger
    logger.remove()
    
    # Get log level from environment or parameter
    level = log_level or os.environ.get("LOG_LEVEL", "INFO")
    
    # Create custom format with execution context
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        f"<cyan>{lambda_name}</cyan> | "
        f"<yellow>{execution_id or 'N/A'}</yellow> | "
        "<level>{message}</level>"
    )
    
    # Add handler for CloudWatch (stdout)
    logger.add(
        sys.stdout,
        format=log_format,
        level=level,
        serialize=False
    )
    
    # Add execution context to all logs
    logger.configure(
        extra={
            "lambda_name": lambda_name,
            "execution_id": execution_id
        }
    )


def get_logger():
    """Get the configured logger instance."""
    return logger


def log_lambda_start(event: dict, context: dict) -> str:
    """
    Log lambda function start with event details.
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        execution_id: Unique execution identifier
    """
    execution_id = getattr(context, 'aws_request_id', 'unknown')
    
    logger.info(
        "Lambda execution started",
        event_keys=list(event.keys()) if event else [],
        execution_id=execution_id,
        remaining_time_ms=getattr(context, 'get_remaining_time_in_millis', lambda: 0)()
    )
    
    return execution_id


def log_lambda_end(execution_id: str, result: dict) -> None:
    """
    Log lambda function completion.
    
    Args:
        execution_id: Execution identifier
        result: Lambda response data
    """
    logger.info(
        "Lambda execution completed",
        execution_id=execution_id,
        status=result.get('status', 'unknown'),
        message=result.get('message', '')
    )


def log_error(error: Exception, execution_id: str, stage: str) -> None:
    """
    Log errors with context.
    
    Args:
        error: Exception that occurred
        execution_id: Execution identifier
        stage: Current processing stage
    """
    logger.error(
        f"Error in {stage}",
        execution_id=execution_id,
        error_type=type(error).__name__,
        error_message=str(error),
        exc_info=True
    )