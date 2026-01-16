"""
Data persistence service for loading and saving application data.
"""

import json
from pathlib import Path
from typing import Optional

from ..config.settings import Settings
from ..models.app_state import AppState
from ..utils.exceptions import DataLoadError, DataSaveError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataService:
    """
    Service for loading and saving application data to JSON files.
    """

    def __init__(self, data_file: Optional[Path] = None):
        """
        Initialize the data service.

        Args:
            data_file: Path to the data file. If None, uses default from Settings.
        """
        self.data_file = data_file or Settings.DATA_FILE

    def load(self) -> AppState:
        """
        Load application state from the data file.

        Returns:
            AppState object with loaded data, or empty state if file doesn't exist.

        Raises:
            DataLoadError: If the file exists but cannot be read/parsed.
        """
        if not self.data_file.exists():
            logger.info(f"Data file not found, starting with empty state: {self.data_file}")
            return AppState()

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            state = AppState.from_dict(data)
            logger.info(f"Loaded {len(state.accounts)} accounts from {self.data_file}")
            return state

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in data file: {e}")
            raise DataLoadError(str(self.data_file), e)
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise DataLoadError(str(self.data_file), e)

    def save(self, state: AppState) -> None:
        """
        Save application state to the data file.

        Args:
            state: The AppState to save.

        Raises:
            DataSaveError: If the file cannot be written.
        """
        try:
            # Ensure parent directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)

            data = state.to_dict()

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(state.accounts)} accounts to {self.data_file}")

        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise DataSaveError(str(self.data_file), e)

    def exists(self) -> bool:
        """Check if the data file exists."""
        return self.data_file.exists()

    def get_file_size(self) -> int:
        """Get the size of the data file in bytes."""
        if self.data_file.exists():
            return self.data_file.stat().st_size
        return 0


# Global singleton instance
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """Get the global DataService instance."""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
