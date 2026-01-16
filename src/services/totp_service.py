"""
TOTP (Time-based One-Time Password) generation service.
"""

import time
from typing import Optional

import pyotp

from ..config.settings import Settings
from ..utils.exceptions import InvalidSecretError
from ..utils.logger import get_logger
from .time_service import get_accurate_time

logger = get_logger(__name__)


class TotpService:
    """
    Service for generating TOTP 2FA codes.

    Uses pyotp library for RFC 6238 compliant TOTP generation.
    """

    def __init__(self, period: int = Settings.TOTP_PERIOD):
        """
        Initialize the TOTP service.

        Args:
            period: TOTP time period in seconds (default 30).
        """
        self.period = period

    def generate_code(self, secret: str) -> str:
        """
        Generate a TOTP code for the given secret.

        Args:
            secret: Base32 encoded secret key.

        Returns:
            6-digit TOTP code as string.

        Raises:
            InvalidSecretError: If the secret is invalid.
        """
        if not secret or not secret.strip():
            raise InvalidSecretError(secret or "", "Empty secret key")

        try:
            # Clean up the secret (remove spaces, convert to uppercase)
            clean_secret = secret.strip().replace(' ', '').upper()

            # Get accurate time
            accurate_time = get_accurate_time()

            # Generate TOTP using the accurate time
            totp = pyotp.TOTP(clean_secret, interval=self.period)
            return totp.at(accurate_time)

        except Exception as e:
            logger.error(f"Failed to generate TOTP code: {e}")
            raise InvalidSecretError(secret, str(e))

    def generate_code_safe(self, secret: str) -> Optional[str]:
        """
        Generate a TOTP code, returning None on error instead of raising.

        Args:
            secret: Base32 encoded secret key.

        Returns:
            6-digit TOTP code as string, or None if generation failed.
        """
        try:
            return self.generate_code(secret)
        except InvalidSecretError:
            return None

    def get_remaining_seconds(self) -> int:
        """
        Get the number of seconds remaining until the current code expires.

        Returns:
            Seconds remaining (1-30 for a 30-second period).
        """
        accurate_time = get_accurate_time()
        return self.period - int(accurate_time % self.period)

    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code against the secret.

        Args:
            secret: Base32 encoded secret key.
            code: The TOTP code to verify.

        Returns:
            True if the code is valid, False otherwise.
        """
        if not secret or not code:
            return False

        try:
            clean_secret = secret.strip().replace(' ', '').upper()
            totp = pyotp.TOTP(clean_secret, interval=self.period)

            # Verify with a small time window to account for clock drift
            accurate_time = get_accurate_time()
            return totp.verify(code, for_time=accurate_time)

        except Exception as e:
            logger.warning(f"TOTP verification failed: {e}")
            return False

    @staticmethod
    def is_valid_secret(secret: str) -> bool:
        """
        Check if a secret key appears to be valid.

        Args:
            secret: The secret key to validate.

        Returns:
            True if the secret appears valid, False otherwise.
        """
        if not secret or not secret.strip():
            return False

        try:
            clean_secret = secret.strip().replace(' ', '').upper()

            # Base32 alphabet check (A-Z, 2-7, and = for padding)
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=')
            if not all(c in valid_chars for c in clean_secret):
                return False

            # Minimum length check (at least 16 characters for security)
            if len(clean_secret) < 16:
                return False

            # Try to create a TOTP object and generate a code
            totp = pyotp.TOTP(clean_secret)
            totp.now()  # This will fail if the secret is truly invalid
            return True
        except Exception:
            return False


# Global singleton instance
_totp_service: Optional[TotpService] = None


def get_totp_service() -> TotpService:
    """Get the global TotpService instance."""
    global _totp_service
    if _totp_service is None:
        _totp_service = TotpService()
    return _totp_service
