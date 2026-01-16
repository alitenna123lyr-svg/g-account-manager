"""
Tests for the account service.
"""

import pytest

from src.models.account import Account
from src.models.app_state import AppState
from src.services.account_service import AccountService
from src.utils.exceptions import DuplicateAccountError


class TestAccountService:
    """Tests for AccountService."""

    def test_add_new_account(self, account_service):
        """Test adding a new account."""
        account = Account(email="test@example.com", password="pass123")
        result = account_service.add(account)

        assert result.id is not None
        assert result.email == "test@example.com"
        assert account_service.get_account_count() == 1

    def test_add_assigns_id(self, account_service):
        """Test that add assigns an ID to account."""
        account = Account(email="test@example.com")
        assert account.id is None

        result = account_service.add(account)
        assert result.id == 1

    def test_add_increments_id(self, account_service):
        """Test that IDs increment correctly."""
        acc1 = account_service.add(Account(email="test1@example.com"))
        acc2 = account_service.add(Account(email="test2@example.com"))

        assert acc1.id == 1
        assert acc2.id == 2

    def test_add_duplicate_raises(self, account_service):
        """Test that adding duplicate email raises error."""
        account_service.add(Account(email="test@example.com"))

        with pytest.raises(DuplicateAccountError):
            account_service.add(Account(email="test@example.com"))

    def test_add_duplicate_case_insensitive(self, account_service):
        """Test that duplicate check is case-insensitive."""
        account_service.add(Account(email="Test@Example.com"))

        with pytest.raises(DuplicateAccountError):
            account_service.add(Account(email="test@example.com"))

    def test_add_skip_duplicate_check(self, account_service):
        """Test adding without duplicate check."""
        account_service.add(Account(email="test@example.com"))
        # Should not raise with check_duplicate=False
        account_service.add(Account(email="test@example.com"), check_duplicate=False)

        assert account_service.get_account_count() == 2

    def test_delete_moves_to_trash(self, populated_account_service):
        """Test that delete moves account to trash."""
        service = populated_account_service
        initial_count = service.get_account_count()

        deleted = service.delete(1, move_to_trash=True)

        assert deleted is not None
        assert deleted.id == 1
        assert service.get_account_count() == initial_count - 1
        assert service.get_trash_count() == 1

    def test_delete_permanent(self, populated_account_service):
        """Test permanent deletion."""
        service = populated_account_service

        deleted = service.delete(1, move_to_trash=False)

        assert deleted is not None
        assert service.get_trash_count() == 0

    def test_delete_nonexistent(self, account_service):
        """Test deleting non-existent account."""
        result = account_service.delete(999)
        assert result is None

    def test_restore_from_trash(self, populated_account_service):
        """Test restoring account from trash."""
        service = populated_account_service
        service.delete(1, move_to_trash=True)

        restored = service.restore_from_trash(1)

        assert restored is not None
        assert restored.id == 1
        assert service.get_trash_count() == 0

    def test_empty_trash(self, populated_account_service):
        """Test emptying trash."""
        service = populated_account_service
        service.delete(1, move_to_trash=True)
        service.delete(2, move_to_trash=True)

        count = service.empty_trash()

        assert count == 2
        assert service.get_trash_count() == 0

    def test_find_by_email(self, populated_account_service):
        """Test finding account by email."""
        service = populated_account_service

        found = service.find_by_email("user1@example.com")
        assert found is not None
        assert found.id == 1

    def test_find_by_email_case_insensitive(self, populated_account_service):
        """Test that find_by_email is case-insensitive."""
        service = populated_account_service

        found = service.find_by_email("USER1@EXAMPLE.COM")
        assert found is not None
        assert found.email == "user1@example.com"

    def test_find_by_email_not_found(self, populated_account_service):
        """Test find_by_email with non-existent email."""
        result = populated_account_service.find_by_email("nonexistent@example.com")
        assert result is None

    def test_find_by_id(self, populated_account_service):
        """Test finding account by ID."""
        found = populated_account_service.find_by_id(2)
        assert found is not None
        assert found.email == "user2@example.com"

    def test_find_duplicates(self, populated_account_service):
        """Test finding duplicate accounts."""
        service = populated_account_service
        new_accounts = [
            Account(email="user1@example.com", password="newpass"),  # duplicate
            Account(email="newuser@example.com", password="pass"),   # new
        ]

        duplicates = service.find_duplicates(new_accounts)

        assert len(duplicates) == 1
        assert duplicates[0][0].email == "user1@example.com"

    def test_clear_all(self, populated_account_service):
        """Test clearing all accounts."""
        service = populated_account_service
        initial_count = service.get_account_count()

        cleared = service.clear_all(move_to_trash=True)

        assert cleared == initial_count
        assert service.get_account_count() == 0
        assert service.get_trash_count() == initial_count

    def test_update_account(self, populated_account_service):
        """Test updating an account."""
        service = populated_account_service
        account = service.find_by_id(1)
        account.password = "newpassword"

        service.update(account)

        updated = service.find_by_id(1)
        assert updated.password == "newpassword"
