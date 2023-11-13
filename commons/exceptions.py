from rest_framework.exceptions import ValidationError


class CustomValidationError(ValidationError):
    def __init__(self, message, code=None):
        super().__init__(message, code)
