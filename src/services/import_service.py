"""
Import service for parsing and importing account data.
"""

from datetime import datetime
from typing import Optional

from ..models.account import Account
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImportService:
    """
    Service for importing accounts from various formats.
    """

    # Separator priority (highest to lowest)
    SEPARATORS = [
        '----',  # 4 dashes
        '---',   # 3 dashes
        '--',    # 2 dashes
        '||',    # double pipe
        '|',     # single pipe
        '\t',    # tab
        ',',     # comma
    ]

    def detect_separator(self, lines: list[str]) -> str:
        """
        Auto-detect the separator used in the data.

        Analyzes the first few non-empty lines to determine the most
        likely separator.

        Args:
            lines: List of lines to analyze.

        Returns:
            The detected separator string.
        """
        # Sample first 5 non-empty lines
        sample_lines = []
        for line in lines:
            if line.strip():
                sample_lines.append(line)
                if len(sample_lines) >= 5:
                    break

        if not sample_lines:
            return '----'  # Default

        # Try each separator in priority order
        for sep in self.SEPARATORS:
            matches = 0
            for line in sample_lines:
                parts = line.split(sep)
                # A valid separator should give us at least 2 parts
                if len(parts) >= 2:
                    # Check that parts have reasonable content
                    if all(p.strip() or True for p in parts[:2]):
                        matches += 1

            # If most lines match, use this separator
            if matches >= len(sample_lines) * 0.6:
                logger.info(f"Detected separator: {repr(sep)}")
                return sep

        # Default to 4 dashes
        logger.info("Using default separator: ----")
        return '----'

    def parse_line(self, line: str, separator: Optional[str] = None) -> Optional[Account]:
        """
        Parse a single line into an Account object.

        Expected format: email[sep]password[sep]backup_email[sep]2fa_secret

        Args:
            line: The line to parse.
            separator: The separator to use. If None, auto-detects.

        Returns:
            Account object, or None if line is empty/invalid.
        """
        line = line.strip()
        if not line:
            return None

        # Auto-detect separator if not provided
        if separator is None:
            separator = self.detect_separator([line])

        parts = line.split(separator)

        # Need at least an email
        if not parts or not parts[0].strip():
            return None

        email = parts[0].strip()
        password = parts[1].strip() if len(parts) > 1 else ""
        backup = parts[2].strip() if len(parts) > 2 else ""
        secret = parts[3].strip() if len(parts) > 3 else ""

        return Account(
            email=email,
            password=password,
            backup=backup,
            secret=secret,
            import_time=datetime.now().strftime("%Y-%m-%d %H:%M")
        )

    def parse_text(self, text: str, separator: Optional[str] = None) -> list[Account]:
        """
        Parse multi-line text into a list of accounts.

        Args:
            text: Multi-line text to parse.
            separator: The separator to use. If None, auto-detects.

        Returns:
            List of Account objects.
        """
        lines = text.strip().split('\n')

        if not lines:
            return []

        # Auto-detect separator from all lines if not provided
        if separator is None:
            separator = self.detect_separator(lines)

        accounts = []
        for line in lines:
            account = self.parse_line(line, separator)
            if account:
                accounts.append(account)

        logger.info(f"Parsed {len(accounts)} accounts from text")
        return accounts

    def parse_file(self, file_path: str, separator: Optional[str] = None) -> list[Account]:
        """
        Parse a file into a list of accounts.

        Args:
            file_path: Path to the file.
            separator: The separator to use. If None, auto-detects.

        Returns:
            List of Account objects.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            IOError: If the file cannot be read.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        accounts = self.parse_text(text, separator)
        logger.info(f"Parsed {len(accounts)} accounts from file: {file_path}")
        return accounts

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Basic validation that a string looks like an email.

        Args:
            email: The string to validate.

        Returns:
            True if it looks like an email, False otherwise.
        """
        email = email.strip()
        if not email or len(email) < 5:
            return False
        if '@' not in email or '.' not in email:
            return False
        # Check that @ is not at the start or end
        at_pos = email.index('@')
        if at_pos == 0 or at_pos == len(email) - 1:
            return False
        # Check that there's something after @
        domain = email[at_pos + 1:]
        if not domain or '.' not in domain:
            return False
        return True


# Global singleton instance
_import_service: Optional[ImportService] = None


def get_import_service() -> ImportService:
    """Get the global ImportService instance."""
    global _import_service
    if _import_service is None:
        _import_service = ImportService()
    return _import_service
