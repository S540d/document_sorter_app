"""
Global Error Handlers for Document Sorter Application
Provides comprehensive error handling, recovery, and user-friendly error responses
"""

import traceback
from datetime import datetime
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from .monitoring import get_logger, ErrorReporter

logger = get_logger('error_handlers')
error_reporter = ErrorReporter()


def register_error_handlers(app):
    """Register global error handlers with Flask app"""

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        logger.warning("404 Not Found",
                      path=request.path,
                      method=request.method,
                      remote_addr=request.remote_addr)

        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404,
            'timestamp': datetime.now().isoformat()
        }), 404

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors"""
        logger.warning("400 Bad Request",
                      path=request.path,
                      method=request.method,
                      error_description=str(error))

        return jsonify({
            'error': 'Bad Request',
            'message': 'The request contains invalid data',
            'status_code': 400,
            'timestamp': datetime.now().isoformat()
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        logger.warning("401 Unauthorized",
                      path=request.path,
                      method=request.method,
                      remote_addr=request.remote_addr)

        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'status_code': 401,
            'timestamp': datetime.now().isoformat()
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        logger.warning("403 Forbidden",
                      path=request.path,
                      method=request.method,
                      remote_addr=request.remote_addr)

        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied',
            'status_code': 403,
            'timestamp': datetime.now().isoformat()
        }), 403

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Rate Limit Exceeded errors"""
        logger.warning("429 Rate Limit Exceeded",
                      path=request.path,
                      method=request.method,
                      remote_addr=request.remote_addr)

        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later.',
            'status_code': 429,
            'timestamp': datetime.now().isoformat()
        }), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error"""
        error_id = error_reporter.report_error(
            'internal_server_error',
            str(error),
            {
                'path': request.path,
                'method': request.method,
                'remote_addr': request.remote_addr,
                'traceback': traceback.format_exc()
            }
        )

        logger.error("500 Internal Server Error",
                    path=request.path,
                    method=request.method,
                    error_id=error_id,
                    exception=error)

        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'error_id': error_id,
            'status_code': 500,
            'timestamp': datetime.now().isoformat()
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle general HTTP exceptions"""
        logger.warning("HTTP Exception",
                      status_code=error.code,
                      path=request.path,
                      method=request.method,
                      description=error.description)

        return jsonify({
            'error': error.name,
            'message': error.description,
            'status_code': error.code,
            'timestamp': datetime.now().isoformat()
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected exceptions"""
        error_id = error_reporter.report_error(
            'unexpected_error',
            str(error),
            {
                'path': request.path,
                'method': request.method,
                'remote_addr': request.remote_addr,
                'traceback': traceback.format_exc(),
                'error_type': type(error).__name__
            }
        )

        logger.critical("Unexpected error",
                       path=request.path,
                       method=request.method,
                       error_id=error_id,
                       error_type=type(error).__name__,
                       exception=error)

        return jsonify({
            'error': 'Unexpected Error',
            'message': 'An unexpected error occurred. The development team has been notified.',
            'error_id': error_id,
            'status_code': 500,
            'timestamp': datetime.now().isoformat()
        }), 500


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""
    def __init__(self, message, file_path=None, error_code=None):
        super().__init__(message)
        self.file_path = file_path
        self.error_code = error_code


class ClassificationError(Exception):
    """Custom exception for AI classification errors"""
    def __init__(self, message, document_text_length=None, error_code=None):
        super().__init__(message)
        self.document_text_length = document_text_length
        self.error_code = error_code


class WorkflowError(Exception):
    """Custom exception for workflow processing errors"""
    def __init__(self, message, rule_id=None, error_code=None):
        super().__init__(message)
        self.rule_id = rule_id
        self.error_code = error_code


def safe_execute(func, fallback_value=None, error_message="Operation failed"):
    """
    Safely execute a function with error handling and logging

    Args:
        func: Function to execute
        fallback_value: Value to return if function fails
        error_message: Custom error message for logging

    Returns:
        Function result or fallback_value if error occurs
    """
    try:
        return func()
    except Exception as e:
        logger.error(f"Safe execution failed: {error_message}",
                    exception=e,
                    function_name=func.__name__ if hasattr(func, '__name__') else 'unknown')
        return fallback_value


def with_error_recovery(max_retries=3, delay=1.0):
    """
    Decorator for automatic error recovery with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time

            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(f"Function {func.__name__} failed, retrying in {current_delay}s",
                                     attempt=attempt + 1,
                                     max_retries=max_retries,
                                     exception=e)
                        time.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries",
                                   exception=e)

            # If all retries failed, raise the last exception
            raise last_exception

        return wrapper
    return decorator


def validate_file_path(file_path):
    """
    Validate file path for security and existence

    Args:
        file_path: Path to validate

    Raises:
        ValueError: If path is invalid
        FileNotFoundError: If file doesn't exist
    """
    import os
    from pathlib import Path

    if not file_path:
        raise ValueError("File path cannot be empty")

    # Convert to Path object
    path_obj = Path(file_path)

    # Check for path traversal attempts
    abs_path = str(path_obj.resolve())
    if '..' in str(path_obj):
        raise ValueError("Invalid file path: potential security risk")

    # Allow absolute paths for temp files and app directories
    if abs_path.startswith('/'):
        allowed_prefixes = ['/tmp/', '/app/', '/var/folders/', '/private/var/folders/']
        if not any(abs_path.startswith(prefix) for prefix in allowed_prefixes):
            # Only raise error for suspicious absolute paths, not all absolute paths
            if abs_path.startswith(('/etc/', '/usr/', '/bin/', '/sbin/')):
                raise ValueError("Invalid file path: potential security risk")

    # Check if file exists
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check if it's actually a file
    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    return str(path_obj.resolve())


def create_error_response(error_type, message, status_code=500, details=None):
    """
    Create standardized error response

    Args:
        error_type: Type of error (string)
        message: Error message
        status_code: HTTP status code
        details: Additional error details (dict)

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'error': error_type,
        'message': message,
        'status_code': status_code,
        'timestamp': datetime.now().isoformat()
    }

    if details:
        response['details'] = details

    return response, status_code