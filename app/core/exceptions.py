class AppError(Exception):
    def __init__(self, detail: str, code: str, status_code: int = 400):
        self.detail = detail
        self.code = code
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "Recurso não encontrado", code: str = "NOT_FOUND"):
        super().__init__(detail, code, 404)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Não autorizado", code: str = "UNAUTHORIZED"):
        super().__init__(detail, code, 401)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Acesso negado", code: str = "FORBIDDEN"):
        super().__init__(detail, code, 403)


class ConflictError(AppError):
    def __init__(self, detail: str = "Conflito", code: str = "CONFLICT"):
        super().__init__(detail, code, 409)


class ValidationError(AppError):
    def __init__(self, detail: str = "Erro de validação", code: str = "VALIDATION_ERROR"):
        super().__init__(detail, code, 422)


class BusinessRuleError(AppError):
    def __init__(self, detail: str, code: str = "BUSINESS_RULE_VIOLATION"):
        super().__init__(detail, code, 400)


class RateLimitError(AppError):
    def __init__(self, detail: str = "Muitas requisições", code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(detail, code, 429)