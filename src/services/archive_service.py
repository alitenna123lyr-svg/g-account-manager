"""
Archive service for creating and managing application state archives.

Archives are automatic snapshots saved when the application exits.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config.settings import Settings
from ..models.app_state import AppState
from ..utils.exceptions import ArchiveError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ArchiveInfo:
    """Information about an archive."""
    filename: str
    timestamp: datetime
    account_count: int
    group_count: int
    file_path: Path

    @property
    def display_time(self) -> str:
        """Get formatted display time."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'filename': self.filename,
            'timestamp': self.timestamp.isoformat(),
            'account_count': self.account_count,
            'group_count': self.group_count,
        }

    @classmethod
    def from_dict(cls, data: dict, archive_dir: Path) -> 'ArchiveInfo':
        """Create from dictionary."""
        return cls(
            filename=data['filename'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            account_count=data.get('account_count', 0),
            group_count=data.get('group_count', 0),
            file_path=archive_dir / data['filename'],
        )


class ArchiveService:
    """
    Service for managing application state archives.

    Archives are snapshots of the application state that are created
    automatically when the application exits.
    """

    def __init__(self, archive_dir: Optional[Path] = None):
        """
        Initialize the archive service.

        Args:
            archive_dir: Directory to store archives. If None, uses default from Settings.
        """
        self.archive_dir = archive_dir or Settings.ARCHIVE_DIR
        self.max_archives = Settings.MAX_ARCHIVES
        self.index_file = self.archive_dir / Settings.ARCHIVE_INDEX_FILE

    def _ensure_dir(self) -> None:
        """Ensure archive directory exists."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> list[dict]:
        """Load archive index from file."""
        if not self.index_file.exists():
            return []

        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('archives', [])
        except Exception as e:
            logger.warning(f"Failed to load archive index: {e}")
            return []

    def _save_index(self, archives: list[dict]) -> None:
        """Save archive index to file."""
        self._ensure_dir()
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump({'archives': archives}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save archive index: {e}")
            raise ArchiveError("Failed to save archive index", e)

    def create_archive(self, state: AppState) -> ArchiveInfo:
        """
        Create a new archive from the current application state.

        Args:
            state: The application state to archive.

        Returns:
            ArchiveInfo object with archive details.

        Raises:
            ArchiveError: If archive creation fails.
        """
        self._ensure_dir()

        # Generate filename with timestamp
        timestamp = datetime.now()
        filename = f"{Settings.ARCHIVE_PREFIX}{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        file_path = self.archive_dir / filename

        try:
            # Save state to archive file
            data = state.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Create archive info
            archive_info = ArchiveInfo(
                filename=filename,
                timestamp=timestamp,
                account_count=len(state.accounts),
                group_count=len(state.groups),
                file_path=file_path,
            )

            # Update index
            index = self._load_index()
            index.insert(0, archive_info.to_dict())
            self._save_index(index)

            # Clean up old archives
            self._cleanup_old_archives()

            logger.info(f"Created archive: {filename} ({len(state.accounts)} accounts)")
            return archive_info

        except Exception as e:
            logger.error(f"Failed to create archive: {e}")
            raise ArchiveError("Failed to create archive", e)

    def list_archives(self) -> list[ArchiveInfo]:
        """
        List all available archives.

        Returns:
            List of ArchiveInfo objects, sorted by timestamp (newest first).
        """
        index = self._load_index()
        archives = []

        for item in index:
            try:
                archive_info = ArchiveInfo.from_dict(item, self.archive_dir)
                # Only include archives that still exist
                if archive_info.file_path.exists():
                    archives.append(archive_info)
            except Exception as e:
                logger.warning(f"Invalid archive entry: {e}")
                continue

        return archives

    def restore_archive(self, archive_info: ArchiveInfo) -> AppState:
        """
        Restore application state from an archive.

        Args:
            archive_info: The archive to restore.

        Returns:
            The restored AppState.

        Raises:
            ArchiveError: If restoration fails.
        """
        if not archive_info.file_path.exists():
            raise ArchiveError(f"Archive file not found: {archive_info.filename}")

        try:
            with open(archive_info.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            state = AppState.from_dict(data)
            logger.info(f"Restored archive: {archive_info.filename}")
            return state

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in archive: {e}")
            raise ArchiveError(f"Invalid archive format: {archive_info.filename}", e)
        except Exception as e:
            logger.error(f"Failed to restore archive: {e}")
            raise ArchiveError(f"Failed to restore archive: {archive_info.filename}", e)

    def delete_archive(self, archive_info: ArchiveInfo) -> None:
        """
        Delete an archive.

        Args:
            archive_info: The archive to delete.

        Raises:
            ArchiveError: If deletion fails.
        """
        try:
            # Remove file
            if archive_info.file_path.exists():
                archive_info.file_path.unlink()

            # Update index
            index = self._load_index()
            index = [a for a in index if a['filename'] != archive_info.filename]
            self._save_index(index)

            logger.info(f"Deleted archive: {archive_info.filename}")

        except Exception as e:
            logger.error(f"Failed to delete archive: {e}")
            raise ArchiveError(f"Failed to delete archive: {archive_info.filename}", e)

    def _cleanup_old_archives(self) -> None:
        """Remove old archives that exceed the maximum limit."""
        index = self._load_index()

        if len(index) <= self.max_archives:
            return

        # Keep only the most recent archives
        to_delete = index[self.max_archives:]
        index = index[:self.max_archives]

        # Delete old archive files
        for item in to_delete:
            try:
                file_path = self.archive_dir / item['filename']
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleaned up old archive: {item['filename']}")
            except Exception as e:
                logger.warning(f"Failed to delete old archive {item['filename']}: {e}")

        # Save updated index
        self._save_index(index)

    def get_archive_by_filename(self, filename: str) -> Optional[ArchiveInfo]:
        """
        Get archive info by filename.

        Args:
            filename: The archive filename.

        Returns:
            ArchiveInfo if found, None otherwise.
        """
        archives = self.list_archives()
        for archive in archives:
            if archive.filename == filename:
                return archive
        return None


# Global singleton instance
_archive_service: Optional[ArchiveService] = None


def get_archive_service() -> ArchiveService:
    """Get the global ArchiveService instance."""
    global _archive_service
    if _archive_service is None:
        _archive_service = ArchiveService()
    return _archive_service
