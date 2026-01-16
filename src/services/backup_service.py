"""
Backup service for creating and managing data backups.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config.settings import Settings
from ..utils.exceptions import BackupError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BackupService:
    """
    Service for creating and managing backup files.
    """

    def __init__(
        self,
        data_file: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        max_backups: int = Settings.MAX_BACKUPS
    ):
        """
        Initialize the backup service.

        Args:
            data_file: Path to the data file to backup.
            backup_dir: Directory for storing backups.
            max_backups: Maximum number of backups to keep.
        """
        self.data_file = data_file or Settings.DATA_FILE
        self.backup_dir = backup_dir or Settings.BACKUP_DIR
        self.max_backups = max_backups

    def create_backup(self) -> Optional[Path]:
        """
        Create a backup of the data file.

        Returns:
            Path to the created backup file, or None if source doesn't exist.

        Raises:
            BackupError: If the backup operation fails.
        """
        if not self.data_file.exists():
            logger.warning(f"Data file not found, skipping backup: {self.data_file}")
            return None

        try:
            # Ensure backup directory exists
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{Settings.BACKUP_PREFIX}{timestamp}{Settings.BACKUP_SUFFIX}"
            backup_path = self.backup_dir / backup_filename

            # Copy data file to backup
            shutil.copy2(self.data_file, backup_path)

            # Clean up old backups
            self.cleanup_old_backups()

            logger.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise BackupError("Failed to create backup", e)

    def cleanup_old_backups(self) -> int:
        """
        Remove old backups, keeping only the most recent ones.

        Returns:
            Number of backups removed.
        """
        if not self.backup_dir.exists():
            return 0

        try:
            # Get all backup files, sorted by name (which includes timestamp)
            backups = sorted([
                f for f in self.backup_dir.iterdir()
                if f.name.startswith(Settings.BACKUP_PREFIX) and f.name.endswith(Settings.BACKUP_SUFFIX)
            ], key=lambda f: f.name, reverse=True)

            # Remove old backups beyond the limit
            removed = 0
            for old_backup in backups[self.max_backups:]:
                old_backup.unlink()
                removed += 1
                logger.debug(f"Removed old backup: {old_backup.name}")

            if removed > 0:
                logger.info(f"Cleaned up {removed} old backups")

            return removed

        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
            return 0

    def list_backups(self) -> list[Path]:
        """
        List all existing backup files.

        Returns:
            List of backup file paths, sorted newest first.
        """
        if not self.backup_dir.exists():
            return []

        backups = sorted([
            f for f in self.backup_dir.iterdir()
            if f.name.startswith(Settings.BACKUP_PREFIX) and f.name.endswith(Settings.BACKUP_SUFFIX)
        ], key=lambda f: f.name, reverse=True)

        return backups

    def get_latest_backup(self) -> Optional[Path]:
        """
        Get the most recent backup file.

        Returns:
            Path to the latest backup, or None if no backups exist.
        """
        backups = self.list_backups()
        return backups[0] if backups else None

    def restore_from_backup(self, backup_path: Path) -> bool:
        """
        Restore data from a backup file.

        Args:
            backup_path: Path to the backup file to restore.

        Returns:
            True if restored successfully, False otherwise.
        """
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            # Create a backup of current data before restoring
            if self.data_file.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pre_restore_backup = self.backup_dir / f"pre_restore_{timestamp}.json"
                shutil.copy2(self.data_file, pre_restore_backup)

            # Restore from backup
            shutil.copy2(backup_path, self.data_file)
            logger.info(f"Restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def get_backup_count(self) -> int:
        """Get the number of existing backups."""
        return len(self.list_backups())


# Global singleton instance
_backup_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get the global BackupService instance."""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service
