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

    # Archive settings
    ARCHIVE_DIR: Final[Path] = _PROJECT_ROOT / "archives"
    MAX_ARCHIVES: Final[int] = 50
    ARCHIVE_PREFIX: Final[str] = "archive_"
    ARCHIVE_INDEX_FILE: Final[str] = "archive_index.json"

    # Library settings (multi-account library)
    DATA_DIR: Final[Path] = _PROJECT_ROOT / "data"
    LIBRARIES_INDEX_FILE: Final[str] = "libraries.json"
    DEFAULT_LIBRARY_ID: Final[str] = "default"
    DEFAULT_LIBRARY_NAME: Final[str] = "默认"

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

    @classmethod
    def ensure_archive_dir(cls) -> Path:
        """Ensure archive directory exists and return its path."""
        cls.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        return cls.ARCHIVE_DIR

    @classmethod
    def ensure_data_dir(cls) -> Path:
        """Ensure data directory exists and return its path."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return cls.DATA_DIR

    @classmethod
    def get_archive_dir_path(cls) -> str:
        """Get the archive directory path as string."""
        return str(cls.ARCHIVE_DIR)

    @classmethod
    def get_data_dir_path(cls) -> str:
        """Get the data directory path as string."""
        return str(cls.DATA_DIR)
