"""
Application settings and configuration.
"""

from pathlib import Path
from typing import Final


class Settings:
    """Application settings container."""

    # Get the project root directory (parent of src)
    _PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent

    # Data file paths
    DATA_FILE: Final[Path] = _PROJECT_ROOT / "2fa_data.json"
    BACKUP_DIR: Final[Path] = _PROJECT_ROOT / "backups"

    # Backup settings
    MAX_BACKUPS: Final[int] = 10
    BACKUP_PREFIX: Final[str] = "2fa_data_backup_"
    BACKUP_SUFFIX: Final[str] = ".json"

    # TOTP settings
    TOTP_PERIOD: Final[int] = 30
    TOTP_DIGITS: Final[int] = 6

    # UI settings
    TOAST_DURATION: Final[int] = 2000  # milliseconds
    TIMER_INTERVAL: Final[int] = 1000  # milliseconds

    # Window settings
    DEFAULT_WINDOW_WIDTH: Final[int] = 1400
    DEFAULT_WINDOW_HEIGHT: Final[int] = 800
    MIN_WINDOW_WIDTH: Final[int] = 1000
    MIN_WINDOW_HEIGHT: Final[int] = 600

    # Default language
    DEFAULT_LANGUAGE: Final[str] = "en"

    @classmethod
    def get_data_file_path(cls) -> str:
        """Get the data file path as string."""
        return str(cls.DATA_FILE)

    @classmethod
    def get_backup_dir_path(cls) -> str:
        """Get the backup directory path as string."""
        return str(cls.BACKUP_DIR)

    @classmethod
    def ensure_backup_dir(cls) -> Path:
        """Ensure backup directory exists and return its path."""
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return cls.BACKUP_DIR
