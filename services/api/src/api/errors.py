"""Safe HTTP error envelope; never leaks source, answers or provider details."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


def envelope(error: ApiError) -> tuple[int, dict]:
    return error.status, {"error": error.as_dict()}


LEARNING_ERROR_STATUS = {
    "INVALID_INPUT": 400,
    "INSUFFICIENT_EVIDENCE": 400,
    "STALE_SNAPSHOT": 409,
    "PAYLOAD_TOO_LARGE": 413,
    "TOKEN_BUDGET_EXCEEDED": 413,
}


def from_learning_error(error) -> ApiError:
    """Map engine LearningError to the shared HTTP boundary."""
    status = LEARNING_ERROR_STATUS.get(error.code, 500)
    if status == 500:
        return ApiError(500, "INTERNAL", "İşlem tamamlanamadı.", True)
    return ApiError(status, error.code, error.message, error.retryable)
