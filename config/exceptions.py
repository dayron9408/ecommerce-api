import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides a consistent error response format.

    Response format:
    {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human-readable message",
            "details": { ... }  # Optional field-level errors
        }
    }
    """
    # Log the exception for debugging (with request context)
    view = context.get('view', None)
    request = context.get('request', None)
    view_name = view.__class__.__name__ if view else 'Unknown'
    request_method = request.method if request else 'Unknown'
    request_path = request.path if request else 'Unknown'

    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'error': {
                'code': _get_error_code(response.status_code, exc),
                'message': _get_error_message(response),
                'details': _get_error_details(response.data),
            }
        }
        response.data = error_data

        if response.status_code >= 500:
            logger.error(
                'Server error in %s %s (view: %s): %s',
                request_method, request_path, view_name, exc,
                exc_info=True,
            )
        elif response.status_code >= 400:
            logger.warning(
                'Client error in %s %s (view: %s): %s',
                request_method, request_path, view_name, exc,
            )

        return response

    # Handle Django validation errors not caught by DRF
    if isinstance(exc, DjangoValidationError):
        logger.warning(
            'Validation error in %s %s (view: %s): %s',
            request_method, request_path, view_name, exc,
        )
        return Response(
            {
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Validation failed.',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages},
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Handle unhandled exceptions - log them critically
    logger.critical(
        'Unhandled exception in %s %s (view: %s): %s',
        request_method, request_path, view_name, exc,
        exc_info=True,
    )
    return Response(
        {
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An unexpected error occurred.',
                'details': {},
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_code(status_code, exc):
    """Map HTTP status codes to semantic error codes."""
    code_map = {
        400: 'VALIDATION_ERROR',
        401: 'AUTHENTICATION_ERROR',
        403: 'PERMISSION_DENIED',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        429: 'THROTTLED',
        500: 'INTERNAL_SERVER_ERROR',
    }

    # Check for DRF-specific exception types
    from rest_framework.exceptions import (
        ValidationError,
        AuthenticationFailed,
        PermissionDenied,
        NotFound,
        Throttled,
    )

    if isinstance(exc, ValidationError):
        return 'VALIDATION_ERROR'
    if isinstance(exc, AuthenticationFailed):
        return 'AUTHENTICATION_ERROR'
    if isinstance(exc, PermissionDenied):
        return 'PERMISSION_DENIED'
    if isinstance(exc, NotFound):
        return 'NOT_FOUND'
    if isinstance(exc, Throttled):
        return 'THROTTLED'

    return code_map.get(status_code, 'UNKNOWN_ERROR')


def _get_error_message(response):
    """Extract a human-readable message from the response data."""
    data = response.data
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'message' in data:
            return str(data['message'])
        # Get first error from field errors
        for key, value in data.items():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str):
                return value
    if isinstance(data, list) and data:
        return str(data[0])
    return 'An error occurred.'


def _get_error_details(data):
    """Extract field-level error details."""
    if isinstance(data, dict):
        details = {}
        for key, value in data.items():
            if key in ('detail', 'message'):
                continue
            if isinstance(value, list):
                details[key] = [str(v) for v in value]
            else:
                details[key] = str(value)
        return details if details else {}
    return {}
