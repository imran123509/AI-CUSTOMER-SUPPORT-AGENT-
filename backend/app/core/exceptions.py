"""Domain exceptions mapped to HTTP errors by FastAPI handlers."""
from __future__ import annotations


class AppError(Exception):
    """Base for all expected application errors."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str = "", *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message or self.__class__.__name__
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"


class CircuitOpenError(ExternalServiceError):
    code = "circuit_open"
