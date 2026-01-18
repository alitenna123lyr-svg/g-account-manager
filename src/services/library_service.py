"""
Library service for managing multiple account libraries.

Each library is an independent set of accounts, groups, and trash.
"""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import uuid

from ..config.settings import Settings
from ..models.app_state import AppState
from ..utils.exceptions import LibraryError
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LibraryInfo:
    """Information about a library."""
    id: str
    name: str
    file: str

    @property
    def file_path(self) -> Path:
        """Get the full file path for this library."""
        return Settings.DATA_DIR / self.file

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'file': self.file,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LibraryInfo':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            file=data['file'],
        )


class LibraryService:
    """
    Service for managing multiple account libraries.

    Libraries are stored in the data directory, with an index file
    tracking all available libraries.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the library service.

        Args:
            data_dir: Directory to store library data. If None, uses default from Settings.
        """
        self.data_dir = data_dir or Settings.DATA_DIR
        self.index_file = self.data_dir / Settings.LIBRARIES_INDEX_FILE
        self._current_library_id: Optional[str] = None

    def _ensure_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict:
        """Load library index from file."""
        if not self.index_file.exists():
            return {
                'current': Settings.DEFAULT_LIBRARY_ID,
                'libraries': []
            }

        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load library index: {e}")
            return {
                'current': Settings.DEFAULT_LIBRARY_ID,
                'libraries': []
            }

    def _save_index(self, data: dict) -> None:
        """Save library index to file."""
        self._ensure_dir()
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save library index: {e}")
            raise LibraryError("Failed to save library index", e)

    def _ensure_default_library(self) -> None:
        """Ensure the default library exists."""
        index = self._load_index()
        libraries = index.get('libraries', [])

        # Check if default library exists
        default_exists = any(lib['id'] == Settings.DEFAULT_LIBRARY_ID for lib in libraries)

        if not default_exists:
            # Create default library
            default_lib = LibraryInfo(
                id=Settings.DEFAULT_LIBRARY_ID,
                name=Settings.DEFAULT_LIBRARY_NAME,
                file=f"{Settings.DEFAULT_LIBRARY_ID}.json"
            )
            libraries.insert(0, default_lib.to_dict())
            index['libraries'] = libraries
            index['current'] = Settings.DEFAULT_LIBRARY_ID
            self._save_index(index)

            # Migrate existing data to default library if needed
            self._migrate_legacy_data(default_lib)

    def _migrate_legacy_data(self, library: LibraryInfo) -> None:
        """Migrate legacy data file to the library system."""
        legacy_file = Settings.DATA_FILE
        if legacy_file.exists() and not library.file_path.exists():
            try:
                self._ensure_dir()
                shutil.copy(legacy_file, library.file_path)
                logger.info(f"Migrated legacy data to library: {library.name}")
            except Exception as e:
                logger.warning(f"Failed to migrate legacy data: {e}")

    def initialize(self) -> None:
        """Initialize the library system."""
        self._ensure_dir()
        self._ensure_default_library()

    def list_libraries(self) -> list[LibraryInfo]:
        """
        List all available libraries.

        Returns:
            List of LibraryInfo objects.
        """
        self._ensure_default_library()
        index = self._load_index()
        libraries = []

        for item in index.get('libraries', []):
            try:
                libraries.append(LibraryInfo.from_dict(item))
            except Exception as e:
                logger.warning(f"Invalid library entry: {e}")

        return libraries

    def get_current_library(self) -> LibraryInfo:
        """
        Get the current active library.

        Returns:
            LibraryInfo for the current library.
        """
        self._ensure_default_library()
        index = self._load_index()
        current_id = index.get('current', Settings.DEFAULT_LIBRARY_ID)

        for item in index.get('libraries', []):
            if item['id'] == current_id:
                return LibraryInfo.from_dict(item)

        # Fallback to default
        libraries = self.list_libraries()
        if libraries:
            return libraries[0]

        raise LibraryError("No libraries available")

    def get_library_by_id(self, library_id: str) -> Optional[LibraryInfo]:
        """
        Get a library by its ID.

        Args:
            library_id: The library ID.

        Returns:
            LibraryInfo if found, None otherwise.
        """
        for lib in self.list_libraries():
            if lib.id == library_id:
                return lib
        return None

    def switch_library(self, library_id: str) -> LibraryInfo:
        """
        Switch to a different library.

        Args:
            library_id: ID of the library to switch to.

        Returns:
            LibraryInfo for the new current library.

        Raises:
            LibraryError: If library not found.
        """
        library = self.get_library_by_id(library_id)
        if not library:
            raise LibraryError(f"Library not found: {library_id}")

        index = self._load_index()
        index['current'] = library_id
        self._save_index(index)

        self._current_library_id = library_id
        logger.info(f"Switched to library: {library.name}")

        return library

    def create_library(self, name: str) -> LibraryInfo:
        """
        Create a new library.

        Args:
            name: Name for the new library.

        Returns:
            LibraryInfo for the created library.

        Raises:
            LibraryError: If creation fails.
        """
        self._ensure_dir()

        # Generate unique ID
        library_id = str(uuid.uuid4())[:8]
        filename = f"library_{library_id}.json"

        library = LibraryInfo(
            id=library_id,
            name=name,
            file=filename
        )

        # Create empty library file
        try:
            empty_state = AppState()
            with open(library.file_path, 'w', encoding='utf-8') as f:
                json.dump(empty_state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise LibraryError(f"Failed to create library file", e)

        # Update index
        index = self._load_index()
        index['libraries'].append(library.to_dict())
        self._save_index(index)

        logger.info(f"Created library: {name}")
        return library

    def rename_library(self, library_id: str, new_name: str) -> LibraryInfo:
        """
        Rename a library.

        Args:
            library_id: ID of the library to rename.
            new_name: New name for the library.

        Returns:
            Updated LibraryInfo.

        Raises:
            LibraryError: If library not found.
        """
        index = self._load_index()
        libraries = index.get('libraries', [])

        for lib in libraries:
            if lib['id'] == library_id:
                lib['name'] = new_name
                self._save_index(index)
                logger.info(f"Renamed library {library_id} to: {new_name}")
                return LibraryInfo.from_dict(lib)

        raise LibraryError(f"Library not found: {library_id}")

    def reorder_library(self, library_id: str, direction: int) -> None:
        """
        Move a library up or down in the list.

        Args:
            library_id: ID of the library to move.
            direction: -1 for up, +1 for down.
        """
        index = self._load_index()
        libraries = index.get('libraries', [])

        # Find current index
        current_idx = None
        for i, lib in enumerate(libraries):
            if lib['id'] == library_id:
                current_idx = i
                break

        if current_idx is None:
            return

        new_idx = current_idx + direction
        if new_idx < 0 or new_idx >= len(libraries):
            return

        # Swap
        libraries[current_idx], libraries[new_idx] = libraries[new_idx], libraries[current_idx]
        index['libraries'] = libraries
        self._save_index(index)
        logger.info(f"Reordered library {library_id} to position {new_idx}")

    def delete_library(self, library_id: str, keep_file: bool = False) -> Optional[dict]:
        """
        Delete a library.

        Args:
            library_id: ID of the library to delete.
            keep_file: If True, don't delete the library file (for undo support).

        Returns:
            Backup data dict if keep_file=True, None otherwise.

        Raises:
            LibraryError: If library not found or is the last library.
        """
        index = self._load_index()
        libraries = index.get('libraries', [])

        # Cannot delete the last library
        if len(libraries) <= 1:
            raise LibraryError("Cannot delete the last library")

        # Find and remove the library
        library_to_delete = None
        library_dict = None
        library_index = None
        for i, lib in enumerate(libraries):
            if lib['id'] == library_id:
                library_to_delete = LibraryInfo.from_dict(lib)
                library_dict = lib.copy()
                library_index = i
                libraries.remove(lib)
                break

        if not library_to_delete:
            raise LibraryError(f"Library not found: {library_id}")

        backup_data = None
        if keep_file:
            # Return backup data for undo
            backup_data = {
                'library': library_dict,
                'index': library_index,
                'was_current': index.get('current') == library_id
            }
        else:
            # Delete the library file
            try:
                if library_to_delete.file_path.exists():
                    library_to_delete.file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete library file: {e}")

        # If current library was deleted, switch to first available
        if index.get('current') == library_id:
            index['current'] = libraries[0]['id'] if libraries else Settings.DEFAULT_LIBRARY_ID

        index['libraries'] = libraries
        self._save_index(index)

        logger.info(f"Deleted library: {library_to_delete.name}")
        return backup_data

    def restore_library(self, backup_data: dict) -> LibraryInfo:
        """
        Restore a deleted library from backup data.

        Args:
            backup_data: Backup data from delete_library with keep_file=True.

        Returns:
            Restored LibraryInfo.
        """
        index = self._load_index()
        libraries = index.get('libraries', [])

        library_dict = backup_data['library']
        original_index = backup_data['index']
        was_current = backup_data['was_current']

        # Insert library back at original position
        if original_index <= len(libraries):
            libraries.insert(original_index, library_dict)
        else:
            libraries.append(library_dict)

        # Restore current if it was current before
        if was_current:
            index['current'] = library_dict['id']

        index['libraries'] = libraries
        self._save_index(index)

        logger.info(f"Restored library: {library_dict['name']}")
        return LibraryInfo.from_dict(library_dict)

    def permanently_delete_library_file(self, backup_data: dict) -> None:
        """
        Permanently delete the library file after undo timeout.

        Args:
            backup_data: Backup data from delete_library.
        """
        library_dict = backup_data['library']
        library = LibraryInfo.from_dict(library_dict)
        try:
            if library.file_path.exists():
                library.file_path.unlink()
                logger.info(f"Permanently deleted library file: {library.file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete library file: {e}")

    def load_library_state(self, library: LibraryInfo) -> AppState:
        """
        Load the application state for a library.

        Args:
            library: The library to load.

        Returns:
            AppState for the library.
        """
        if not library.file_path.exists():
            logger.info(f"Library file not found, creating empty state: {library.file_path}")
            return AppState()

        try:
            with open(library.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load library state: {e}")
            return AppState()

    def save_library_state(self, library: LibraryInfo, state: AppState) -> None:
        """
        Save application state to a library file.

        Args:
            library: The library to save to.
            state: The state to save.

        Raises:
            LibraryError: If save fails.
        """
        self._ensure_dir()

        try:
            with open(library.file_path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved library state: {library.name}")
        except Exception as e:
            logger.error(f"Failed to save library state: {e}")
            raise LibraryError(f"Failed to save library: {library.name}", e)


# Global singleton instance
_library_service: Optional[LibraryService] = None


def get_library_service() -> LibraryService:
    """Get the global LibraryService instance."""
    global _library_service
    if _library_service is None:
        _library_service = LibraryService()
        _library_service.initialize()
    return _library_service
