"""
Application state container.
"""

from dataclasses import dataclass, field
from typing import Optional

from .account import Account
from .group import Group


@dataclass
class AppState:
    """
    Container for the entire application state.

    This class holds all data that needs to be persisted and shared
    across the application.

    Attributes:
        accounts: List of all active accounts.
        trash: List of deleted accounts (recoverable).
        groups: List of custom groups.
        next_id: Counter for generating unique account IDs.
        language: Current UI language ('en' or 'zh').
        current_filter: Current filter for account display.
        selected_rows: Set of currently selected row indices.
        show_full_info: Whether to show full or masked account info.
        sidebar_collapsed: Whether the sidebar is collapsed.
    """
    accounts: list[Account] = field(default_factory=list)
    trash: list[Account] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    next_id: int = 1
    language: str = "en"

    # UI state (not persisted)
    current_filter: str = "all"
    selected_rows: set[int] = field(default_factory=set)
    show_full_info: bool = False
    sidebar_collapsed: bool = False

    # Undo state
    deleted_group_backup: Optional[dict] = None

    @property
    def existing_emails(self) -> set[str]:
        """Get set of all existing account emails (normalized)."""
        return {acc.email_normalized for acc in self.accounts}

    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """Find an account by its ID."""
        for acc in self.accounts:
            if acc.id == account_id:
                return acc
        return None

    def get_account_by_email(self, email: str) -> Optional[Account]:
        """Find an account by its email (case-insensitive)."""
        normalized = email.lower().strip()
        for acc in self.accounts:
            if acc.email_normalized == normalized:
                return acc
        return None

    def get_accounts_in_group(self, group_name: str) -> list[Account]:
        """Get all accounts in a specific group."""
        return [acc for acc in self.accounts if acc.is_in_group(group_name)]

    def get_ungrouped_accounts(self) -> list[Account]:
        """Get all accounts that are not in any group."""
        return [acc for acc in self.accounts if acc.is_ungrouped]

    def get_group_by_name(self, name: str) -> Optional[Group]:
        """Find a group by its name."""
        for group in self.groups:
            if group.name == name:
                return group
        return None

    def is_duplicate_email(self, email: str) -> bool:
        """Check if an email already exists in accounts."""
        return email.lower().strip() in self.existing_emails

    def generate_next_id(self) -> int:
        """Generate and return the next unique account ID."""
        current_id = self.next_id
        self.next_id += 1
        return current_id

    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            'accounts': [acc.to_dict() for acc in self.accounts],
            'trash': [acc.to_dict() for acc in self.trash],
            'groups': [grp.to_dict() for grp in self.groups],
            'next_id': self.next_id,
            'language': self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AppState':
        """Create an AppState from a dictionary."""
        return cls(
            accounts=[Account.from_dict(acc) for acc in data.get('accounts', [])],
            trash=[Account.from_dict(acc) for acc in data.get('trash', [])],
            groups=[Group.from_dict(grp) for grp in data.get('groups', [])],
            next_id=data.get('next_id', 1),
            language=data.get('language', 'en'),
        )

    def clear_selection(self) -> None:
        """Clear all selected rows."""
        self.selected_rows.clear()

    def toggle_selection(self, row: int) -> None:
        """Toggle selection state for a row."""
        if row in self.selected_rows:
            self.selected_rows.discard(row)
        else:
            self.selected_rows.add(row)

    @property
    def selection_count(self) -> int:
        """Get the number of selected rows."""
        return len(self.selected_rows)
