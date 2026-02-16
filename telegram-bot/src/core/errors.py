

class AppError(Exception):
    pass


class ConflictError(AppError):
    pass


class UnauthorizedError(AppError):
    pass


class ForbiddenError(AppError):
    pass
