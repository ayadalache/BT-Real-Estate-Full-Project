"""
Standard response envelope used by every endpoint in the API:

    {
        "success": bool,
        "message": str,
        "data": <any> | null,
        "errors": <any> | null
    }

Keeping this in one place guarantees every view returns a consistent shape,
which the frontend can rely on without per-endpoint special-casing.
"""
from rest_framework.response import Response


def success_response(data=None, message="Success", status_code=200, headers=None):
    return Response(
        {"success": True, "message": message, "data": data, "errors": None},
        status=status_code,
        headers=headers,
    )


def error_response(message="An error occurred", errors=None, status_code=400):
    return Response(
        {"success": False, "message": message, "data": None, "errors": errors},
        status=status_code,
    )
