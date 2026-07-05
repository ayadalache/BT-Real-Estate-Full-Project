"""
Global exception handler for DRF.

Guarantees:
- Every error response uses the standard envelope (success/message/data/errors).
- Stack traces / internal exception messages are NEVER exposed to the client.
- Unhandled exceptions are logged server-side with full detail for debugging,
  while the client only ever sees a generic, safe message.
"""
import logging
import uuid

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger("apps")
security_logger = logging.getLogger("security")


def custom_exception_handler(exc, context):
    # Let DRF build its default response first (handles validation errors,
    # auth errors, throttling, etc. in a structured way).
    response = drf_default_handler(exc, context)

    request = context.get("request")
    view = context.get("view")

    if isinstance(exc, (drf_exceptions.AuthenticationFailed, drf_exceptions.NotAuthenticated)):
        security_logger.warning(
            "Authentication failure on %s from %s",
            getattr(request, "path", "unknown"),
            _client_ip(request),
        )

    if isinstance(exc, drf_exceptions.PermissionDenied) or isinstance(exc, PermissionDenied):
        security_logger.warning(
            "Permission denied on %s for user=%s from %s",
            getattr(request, "path", "unknown"),
            getattr(getattr(request, "user", None), "id", "anonymous"),
            _client_ip(request),
        )

    if response is not None:
        errors = _normalize_errors(response.data)
        message = _top_level_message(exc, errors)
        response.data = {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors,
        }
        return response

    # Unhandled exception -> never leak details, log with a correlation id.
    if isinstance(exc, Http404):
        return Response(
            {"success": False, "message": "Resource not found.", "data": None, "errors": None},
            status=404,
        )

    error_id = uuid.uuid4().hex
    logger.error("Unhandled exception [%s] on %s", error_id, getattr(request, "path", "unknown"), exc_info=exc)

    return Response(
        {
            "success": False,
            "message": "An unexpected error occurred. Please try again later.",
            "data": None,
            "errors": {"reference_id": error_id},
        },
        status=500,
    )


def _normalize_errors(data):
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        return None
    return data


def _top_level_message(exc, errors):
    if hasattr(exc, "detail"):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        if isinstance(detail, dict) and "detail" in detail:
            return str(detail["detail"])
    return "Request failed validation."


def _client_ip(request):
    if request is None:
        return "unknown"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
