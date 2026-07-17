"""Единый формат ошибок для API.

Контракт зафиксирован в docs/01-architecture-and-design.md, раздел 5:
ошибки всегда возвращаются как ProblemDetail (RFC 7807-подобный).
"""

from pydantic import BaseModel


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None


class AppError(Exception):
    """Базовое доменное исключение. Модули определяют свои наследники
    в exceptions секции сервисов, но всегда через этот класс — чтобы
    exception handler в main.py мог единообразно превратить их в ProblemDetail.
    """

    status_code: int = 400
    error_type: str = "about:blank"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404
    error_type = "not-found"


class PermissionDeniedError(AppError):
    status_code = 403
    error_type = "permission-denied"


class ValidationAppError(AppError):
    status_code = 422
    error_type = "validation-error"


class UnauthorizedError(AppError):
    status_code = 401
    error_type = "unauthorized"


class ConflictError(AppError):
    status_code = 409
    error_type = "conflict"
