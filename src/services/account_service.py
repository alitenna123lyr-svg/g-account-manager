"""
Account management service.
"""

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..models.account import Account
from ..models.app_state import AppState
from ..utils.exceptions import DuplicateAccountError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AccountService(QObject):
    """
    Service for managing accounts (CRUD operations).

    Signals:
        account_added: Emitted when an account is added.
        account_updated: Emitted when an account is updated.
        account_deleted: Emitted when an account is deleted.
        account_restored: Emitted when an account is restored from trash.
    """

    account_added = pyqtSignal(Account)
    account_updated = pyqtSignal(Account)
    account_deleted = pyqtSignal(int)  # account id
    account_restored = pyqtSignal(Account)

    def __init__(self, state: AppState):
        """
        Initialize the account service.

        Args:
            state: The application state to operate on.
        """
        super().__init__()
        self.state = state

    def add(self, account: Account, check_duplicate: bool = True) -> Account:
        """
        Add a new account.

        Args:
            account: The account to add.
            check_duplicate: Whether to check for duplicate emails.

        Returns:
            The added account with assigned ID.

        Raises:
            DuplicateAccountError: If an account with the same email exists.
        """
        if check_duplicate and self.state.is_duplicate_email(account.email):
            raise DuplicateAccountError(account.email)

        # Assign ID if not set
        if account.id is None:
            account.id = self.state.generate_next_id()

        self.state.accounts.append(account)
        logger.info(f"Added account: {account.email_normalized}")
        self.account_added.emit(account)
        return account

    def update(self, account: Account) -> None:
        """
        Update an existing account.

        Args:
            account: The account with updated data.
        """
        for i, acc in enumerate(self.state.accounts):
            if acc.id == account.id:
                self.state.accounts[i] = account
                logger.info(f"Updated account: {account.email_normalized}")
                self.account_updated.emit(account)
                return

        logger.warning(f"Account not found for update: {account.id}")

    def delete(self, account_id: int, move_to_trash: bool = True) -> Optional[Account]:
        """
        Delete an account.

        Args:
            account_id: The ID of the account to delete.
            move_to_trash: If True, move to trash instead of permanent delete.

        Returns:
            The deleted account, or None if not found.
        """
        for i, acc in enumerate(self.state.accounts):
            if acc.id == account_id:
                deleted = self.state.accounts.pop(i)

                if move_to_trash:
                    self.state.trash.append(deleted)
                    logger.info(f"Moved to trash: {deleted.email_normalized}")
                else:
                    logger.info(f"Permanently deleted: {deleted.email_normalized}")

                self.account_deleted.emit(account_id)
                return deleted

        logger.warning(f"Account not found for deletion: {account_id}")
        return None

    def delete_by_email(self, email: str, move_to_trash: bool = True) -> Optional[Account]:
        """
        Delete an account by email.

        Args:
            email: The email of the account to delete.
            move_to_trash: If True, move to trash instead of permanent delete.

        Returns:
            The deleted account, or None if not found.
        """
        account = self.state.get_account_by_email(email)
        if account and account.id:
            return self.delete(account.id, move_to_trash)
        return None

    def restore_from_trash(self, account_id: int) -> Optional[Account]:
        """
        Restore an account from trash.

        Args:
            account_id: The ID of the account to restore.

        Returns:
            The restored account, or None if not found.
        """
        for i, acc in enumerate(self.state.trash):
            if acc.id == account_id:
                restored = self.state.trash.pop(i)
                self.state.accounts.append(restored)
                logger.info(f"Restored from trash: {restored.email_normalized}")
                self.account_restored.emit(restored)
                return restored

        logger.warning(f"Account not found in trash: {account_id}")
        return None

    def empty_trash(self) -> int:
        """
        Permanently delete all items in trash.

        Returns:
            Number of items deleted.
        """
        count = len(self.state.trash)
        self.state.trash.clear()
        logger.info(f"Emptied trash: {count} items deleted")
        return count

    def delete_from_trash(self, account_id: int) -> Optional[Account]:
        """
        Permanently delete an account from trash.

        Args:
            account_id: The ID of the account to delete.

        Returns:
            The deleted account, or None if not found.
        """
        for i, acc in enumerate(self.state.trash):
            if acc.id == account_id:
                deleted = self.state.trash.pop(i)
                logger.info(f"Permanently deleted from trash: {deleted.email_normalized}")
                return deleted
        return None

    def find_by_email(self, email: str) -> Optional[Account]:
        """
        Find an account by email.

        Args:
            email: The email to search for.

        Returns:
            The account if found, None otherwise.
        """
        return self.state.get_account_by_email(email)

    def find_by_id(self, account_id: int) -> Optional[Account]:
        """
        Find an account by ID.

        Args:
            account_id: The ID to search for.

        Returns:
            The account if found, None otherwise.
        """
        return self.state.get_account_by_id(account_id)

    def find_duplicates(self, accounts: list[Account]) -> list[tuple[Account, Account, int]]:
        """
        Find accounts that would be duplicates if added.

        Args:
            accounts: List of accounts to check.

        Returns:
            List of tuples (new_account, existing_account, existing_index).
        """
        duplicates = []
        for new_acc in accounts:
            for i, existing in enumerate(self.state.accounts):
                if new_acc.email_normalized == existing.email_normalized:
                    duplicates.append((new_acc, existing, i))
                    break
        return duplicates

    def clear_all(self, move_to_trash: bool = True) -> int:
        """
        Delete all accounts.

        Args:
            move_to_trash: If True, move to trash instead of permanent delete.

        Returns:
            Number of accounts deleted.
        """
        count = len(self.state.accounts)

        if move_to_trash:
            self.state.trash.extend(self.state.accounts)

        self.state.accounts.clear()
        logger.info(f"Cleared all accounts: {count} items")
        return count

    def get_account_count(self) -> int:
        """Get the total number of active accounts."""
        return len(self.state.accounts)

    def get_trash_count(self) -> int:
        """Get the number of items in trash."""
        return len(self.state.trash)
