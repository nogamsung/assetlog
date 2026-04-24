from http import HTTPStatus


class AppError(Exception):
    """Base class for all domain exceptions."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail if detail is not None else self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    """Resource was not found."""

    status_code: int = HTTPStatus.NOT_FOUND.value
    detail: str = "The requested resource was not found."


class ConflictError(AppError):
    """Resource already exists or state conflict."""

    status_code: int = HTTPStatus.CONFLICT.value
    detail: str = "A conflict occurred with the current state of the resource."


class UnauthorizedError(AppError):
    """Authentication required or credentials invalid."""

    status_code: int = HTTPStatus.UNAUTHORIZED.value
    detail: str = "Authentication credentials are missing or invalid."


class ValidationError(AppError):
    """Input validation failed at domain level."""

    status_code: int = HTTPStatus.UNPROCESSABLE_ENTITY.value
    detail: str = "The provided input is invalid."


class InsufficientHoldingError(ValueError):  # ADDED
    """Raised when a SELL exceeds current remaining quantity."""

    status_code: int = HTTPStatus.CONFLICT.value
    detail: str = "Insufficient holding quantity for this SELL transaction."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail if detail is not None else self.__class__.detail
        super().__init__(self.detail)
