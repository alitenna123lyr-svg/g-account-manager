"""
Time synchronization service for accurate TOTP generation.
"""

import time
import urllib.request
from email.utils import parsedate_to_datetime
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TimeService:
    """
    Service for network time synchronization.

    This service fetches time from Google's servers to ensure accurate
    TOTP code generation, even if the local system clock is off.
    """

    # Google's homepage is used as a reliable time source
    TIME_SERVER_URL = 'https://www.google.com'
    TIMEOUT = 5  # seconds

    def __init__(self):
        """Initialize the time service and calculate initial offset."""
        self._time_offset: float = 0.0
        self._last_sync: float = 0.0
        self._sync_interval: float = 3600.0  # Re-sync every hour

        # Calculate initial offset
        self._time_offset = self._calculate_offset()

    def _get_internet_time(self) -> Optional[float]:
        """
        Get current time from internet (Google's server).

        Returns:
            Unix timestamp from server, or None if failed.
        """
        try:
            response = urllib.request.urlopen(self.TIME_SERVER_URL, timeout=self.TIMEOUT)
            date_str = response.headers['Date']
            server_time = parsedate_to_datetime(date_str)
            return server_time.timestamp()
        except Exception as e:
            logger.warning(f"Failed to get internet time: {e}")
            return None

    def _calculate_offset(self) -> float:
        """
        Calculate offset between local time and internet time.

        Returns:
            Time offset in seconds (positive if local clock is behind).
        """
        internet_time = self._get_internet_time()
        if internet_time is not None:
            local_time = time.time()
            offset = internet_time - local_time
            self._last_sync = time.time()
            logger.info(f"Time offset calculated: {offset:.2f} seconds")
            return offset
        logger.warning("Could not calculate time offset, using local time")
        return 0.0

    @property
    def time_offset(self) -> float:
        """Get the current time offset."""
        # Check if we need to re-sync
        if time.time() - self._last_sync > self._sync_interval:
            self._time_offset = self._calculate_offset()
        return self._time_offset

    def get_accurate_time(self) -> float:
        """
        Get accurate current time using the calculated offset.

        Returns:
            Unix timestamp adjusted for time offset.
        """
        return time.time() + self.time_offset

    def resync(self) -> float:
        """
        Force a resynchronization with the time server.

        Returns:
            The new time offset.
        """
        self._time_offset = self._calculate_offset()
        return self._time_offset

    def get_remaining_seconds(self, period: int = 30) -> int:
        """
        Get remaining seconds until next TOTP period.

        Args:
            period: TOTP period in seconds (default 30).

        Returns:
            Remaining seconds (1-30).
        """
        current_time = self.get_accurate_time()
        elapsed = int(current_time) % period
        remaining = period - elapsed
        return remaining if remaining > 0 else period


# Global singleton instance
_time_service: Optional[TimeService] = None


def get_time_service() -> TimeService:
    """Get the global TimeService instance."""
    global _time_service
    if _time_service is None:
        _time_service = TimeService()
    return _time_service


def get_accurate_time() -> float:
    """Convenience function to get accurate time."""
    return get_time_service().get_accurate_time()
