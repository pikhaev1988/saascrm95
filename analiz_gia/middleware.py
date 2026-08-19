import logging
import time
from uuid import uuid4


logger = logging.getLogger("performance.request")
audit_logger = logging.getLogger("security.audit")

SENSITIVE_ENDPOINT_PREFIXES = (
    "/cabinet/school/export-word/",
    "/cabinet/school/export-pptx/",
    "/api/uploads/",
    "/api/users/",
)

EXPORT_IFRAME_PREFIXES = (
    "/cabinet/school/export-",
    "/cabinet/district/export-",
)


class ExportIframeMiddleware:
    """Разрешает встраивание export-URL в скрытый iframe для скачивания без ухода со страницы."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path or ""
        if any(path.startswith(prefix) for prefix in EXPORT_IFRAME_PREFIXES):
            response.headers.pop("X-Frame-Options", None)
        return response


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        path = request.path or ""
        if path.startswith("/static/") or path.startswith("/media/") or path == "/favicon.ico":
            return response

        # Генерация отчётов с GigaChat обычно 3–30 с — это ожидаемо, не SLOW_REQUEST.
        is_export = any(path.startswith(prefix) for prefix in EXPORT_IFRAME_PREFIXES)
        threshold_ms = 60000 if is_export else 800
        method = request.method
        status_code = getattr(response, "status_code", 0)

        if elapsed_ms >= threshold_ms:
            logger.warning(
                "SLOW_REQUEST method=%s path=%s status=%s duration_ms=%.1f",
                method,
                path,
                status_code,
                elapsed_ms,
            )
        else:
            logger.info(
                "REQUEST_TIMING method=%s path=%s status=%s duration_ms=%.1f",
                method,
                path,
                status_code,
                elapsed_ms,
            )
        return response


class SecurityAuditMiddleware:
    """
    Adds request correlation id and audit events for sensitive endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid4().hex
        request.audit_request_id = request_id
        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        path = request.path or ""
        if path.startswith(SENSITIVE_ENDPOINT_PREFIXES):
            user_id = getattr(request.user, "id", None) if hasattr(request, "user") else None
            role = getattr(request.user, "role", "") if hasattr(request, "user") else ""
            audit_logger.info(
                "AUDIT endpoint=%s method=%s status=%s user_id=%s role=%s request_id=%s remote_addr=%s",
                path,
                request.method,
                getattr(response, "status_code", 0),
                user_id,
                role,
                request_id,
                request.META.get("REMOTE_ADDR", ""),
            )
        return response
