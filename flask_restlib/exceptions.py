from marshmallow import ValidationError


__all__ = (
    'ApiError', 'ValidationError',
)


class ApiError(Exception):
    """Любая ошибка, возникшая при использовании API."""
    def __init__(self, description, status=400):
        self.description = description
        self.status = status

    def to_response(self):
        """Возвращает ошибку в формате ответа."""
        return {'message': self.description}, self.status
