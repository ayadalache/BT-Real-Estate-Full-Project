import logging
import time

security_logger = logging.getLogger("security")

SENSITIVE_PATHS = ("/api/v1/auth/",)


class SecurityAuditLogMiddleware:
    """
    Lightweight audit trail for security-sensitive endpoints (auth, password
    reset, etc). Logs method, path, status, latency, user, and client IP —
    never request bodies (which may contain passwords).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)

        if request.path.startswith(SENSITIVE_PATHS):
            duration_ms = (time.monotonic() - start) * 1000
            user = getattr(request, "user", None)
            user_repr = getattr(user, "id", "anonymous") if user and user.is_authenticated else "anonymous"
            security_logger.info(
                "%s %s status=%s user=%s ip=%s duration_ms=%.1f",
                request.method,
                request.path,
                response.status_code,
                user_repr,
                self._client_ip(request),
                duration_ms,
            )
        return response

    @staticmethod
    def _client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
