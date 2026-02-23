"""
全域自訂例外類別。
Service 層拋出這些例外，Controller 層的 Exception Handler 攔截並轉換成 HTTP Response。
"""


class DomainException(Exception):
    """所有 Domain 例外的基底類別"""
    pass


class NotFoundException(DomainException):
    """資源不存在時拋出，對應 HTTP 404"""
    pass


class RateLimitException(DomainException):
    """超過速率限制時拋出，對應 HTTP 429"""
    pass


class UnauthorizedException(DomainException):
    """認證失敗時拋出，對應 HTTP 401"""
    pass


class ValidationException(DomainException):
    """業務邏輯驗證失敗時拋出，對應 HTTP 422"""
    pass
