"""
Account data model.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Account:
    """
    Represents a Google account with 2FA credentials.

    Attributes:
        email: The account email address.
        password: The account password.
        backup: Secondary/backup email address.
        secret: The 2FA TOTP secret key.
        id: Unique identifier for the account.
        import_time: Timestamp when the account was imported.
        groups: List of group names this account belongs to.
        notes: Additional notes for the account.
    """
    email: str
    password: str = ""
    backup: str = ""
    secret: str = ""
    id: Optional[int] = None
    import_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    groups: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def email_normalized(self) -> str:
        """Get normalized email for comparison (lowercase, stripped)."""
        return self.email.lower().strip()

    @property
    def has_2fa(self) -> bool:
        """Check if account has a 2FA secret."""
        return bool(self.secret and self.secret.strip())

    def to_dict(self) -> dict:
        """Convert account to dictionary for JSON serialization."""
        return {
            'email': self.email,
            'password': self.password,
            'backup': self.backup,
            'secret': self.secret,
            'id': self.id,
            'import_time': self.import_time,
            'groups': self.groups.copy(),
            'notes': self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Account':
        """Create an Account from a dictionary."""
        return cls(
            email=data.get('email', ''),
            password=data.get('password', ''),
            backup=data.get('backup', ''),
            secret=data.get('secret', ''),
            id=data.get('id'),
            import_time=data.get('import_time', datetime.now().strftime("%Y-%m-%d %H:%M")),
            groups=data.get('groups', []).copy() if data.get('groups') else [],
            notes=data.get('notes', ''),
        )

    def add_to_group(self, group_name: str) -> bool:
        """
        Add account to a group.

        Returns:
            True if added, False if already in group.
        """
        if group_name not in self.groups:
            self.groups.append(group_name)
            return True
        return False

    def remove_from_group(self, group_name: str) -> bool:
        """
        Remove account from a group.

        Returns:
            True if removed, False if not in group.
        """
        if group_name in self.groups:
            self.groups.remove(group_name)
            return True
        return False

    def is_in_group(self, group_name: str) -> bool:
        """Check if account is in the specified group."""
        return group_name in self.groups

    @property
    def is_ungrouped(self) -> bool:
        """Check if account has no groups."""
        return len(self.groups) == 0

    def __eq__(self, other: object) -> bool:
        """Two accounts are equal if they have the same normalized email."""
        if not isinstance(other, Account):
            return False
        return self.email_normalized == other.email_normalized

    def __hash__(self) -> int:
        """Hash based on normalized email."""
        return hash(self.email_normalized)
