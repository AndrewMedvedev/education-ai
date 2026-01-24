

class AppError(Exception):
    pass


class ForbiddenError(AppError):
    """Нет доступа к ресурсу"""
