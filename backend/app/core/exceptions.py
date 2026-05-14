from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base for domain errors. Subclasses set status_code + a stable error code."""

    code: str = "app_error"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            status_code=self.status_code,
            detail={"code": self.code, "message": detail or self.code},
        )


class NotFound(AppError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND


class Forbidden(AppError):
    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN


class Unauthorized(AppError):
    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED


class Conflict(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT


class ValidationFailed(AppError):
    code = "validation_failed"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
