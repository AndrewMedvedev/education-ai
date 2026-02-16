

class AppError(Exception):
    pass


class UnauthorizedError(AppError):
    pass


class ForbiddenError(AppError):
    pass
