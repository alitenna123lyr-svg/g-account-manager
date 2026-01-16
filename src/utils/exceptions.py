"""
Custom exceptions for the application.
"""


class AppError(Exception):
    """Base exception for all application errors."""
    pass


class InvalidSecretError(AppError):
    """Raised when a 2FA secret key is invalid."""

    def __init__(self, secret: str, message: str = "Invalid 2FA secret key"):
        self.secret = secret
        self.message = message
        super().__init__(f"{message}: {secret[:4]}..." if len(secret) > 4 else message)


class DuplicateAccountError(AppError):
    """Raised when attempting to add a duplicate account."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Account already exists: {email}")


class DataLoadError(AppError):
    """Raised when data cannot be loaded from file."""

    def __init__(self, file_path: str, cause: Exception | None = None):
        self.file_path = file_path
        self.cause = cause
        message = f"Failed to load data from: {file_path}"
        if cause:
            message += f" ({cause})"
        super().__init__(message)


class DataSaveError(AppError):
    """Raised when data cannot be saved to file."""

    def __init__(self, file_path: str, cause: Exception | None = None):
        self.file_path = file_path
        self.cause = cause
        message = f"Failed to save data to: {file_path}"
        if cause:
            message += f" ({cause})"
        super().__init__(message)


class BackupError(AppError):
    """Raised when backup operation fails."""

    def __init__(self, message: str = "Backup operation failed", cause: Exception | None = None):
        self.cause = cause
        if cause:
            message += f" ({cause})"
        super().__init__(message)


class ImportError(AppError):
    """Raised when import operation fails."""

    def __init__(self, message: str = "Import operation failed", line_number: int | None = None):
        self.line_number = line_number
        if line_number is not None:
            message += f" at line {line_number}"
        super().__init__(message)
