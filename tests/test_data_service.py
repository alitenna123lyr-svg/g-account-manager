"""
Tests for the data service.
"""

import json
import pytest
from pathlib import Path

from src.models.account import Account
from src.models.group import Group
from src.models.app_state import AppState
from src.services.data_service import DataService
from src.utils.exceptions import DataLoadError


class TestDataService:
    """Tests for DataService."""

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty state."""
        data_file = tmp_path / "nonexistent.json"
        service = DataService(data_file)

        state = service.load()

        assert len(state.accounts) == 0
        assert len(state.groups) == 0
        assert state.next_id == 1

    def test_load_existing_file(self, temp_data_file):
        """Test loading from existing file."""
        service = DataService(temp_data_file)

        state = service.load()

        assert len(state.accounts) == 1
        assert state.accounts[0].email == "test@example.com"
        assert state.next_id == 2

    def test_load_invalid_json_raises(self, tmp_path):
        """Test that invalid JSON raises DataLoadError."""
        data_file = tmp_path / "invalid.json"
        data_file.write_text("not valid json {{{")

        service = DataService(data_file)

        with pytest.raises(DataLoadError):
            service.load()

    def test_save_creates_file(self, tmp_path):
        """Test that save creates the file."""
        data_file = tmp_path / "new_data.json"
        service = DataService(data_file)

        state = AppState()
        state.accounts.append(Account(email="test@example.com", id=1))
        state.next_id = 2

        service.save(state)

        assert data_file.exists()

        # Verify content
        with open(data_file) as f:
            data = json.load(f)
        assert len(data['accounts']) == 1
        assert data['accounts'][0]['email'] == "test@example.com"

    def test_save_overwrites_existing(self, temp_data_file):
        """Test that save overwrites existing file."""
        service = DataService(temp_data_file)

        state = AppState()
        state.accounts.append(Account(email="new@example.com", id=1))
        state.next_id = 2

        service.save(state)

        # Reload and verify
        loaded = service.load()
        assert len(loaded.accounts) == 1
        assert loaded.accounts[0].email == "new@example.com"

    def test_save_preserves_groups(self, tmp_path):
        """Test that groups are saved correctly."""
        data_file = tmp_path / "data.json"
        service = DataService(data_file)

        state = AppState()
        state.groups.append(Group(name="work", color="blue"))
        state.groups.append(Group(name="personal", color="green"))

        service.save(state)

        loaded = service.load()
        assert len(loaded.groups) == 2
        assert loaded.groups[0].name == "work"
        assert loaded.groups[0].color == "blue"

    def test_save_preserves_trash(self, tmp_path):
        """Test that trash is saved correctly."""
        data_file = tmp_path / "data.json"
        service = DataService(data_file)

        state = AppState()
        state.trash.append(Account(email="deleted@example.com", id=1))

        service.save(state)

        loaded = service.load()
        assert len(loaded.trash) == 1
        assert loaded.trash[0].email == "deleted@example.com"

    def test_exists(self, temp_data_file, tmp_path):
        """Test exists method."""
        existing_service = DataService(temp_data_file)
        assert existing_service.exists() is True

        nonexistent_service = DataService(tmp_path / "nonexistent.json")
        assert nonexistent_service.exists() is False

    def test_roundtrip(self, tmp_path):
        """Test complete save/load roundtrip."""
        data_file = tmp_path / "data.json"
        service = DataService(data_file)

        # Create state with various data
        original = AppState()
        original.accounts = [
            Account(email="user1@test.com", password="pass1", id=1, groups=["work"]),
            Account(email="user2@test.com", password="pass2", id=2, groups=["personal"]),
        ]
        original.trash = [
            Account(email="deleted@test.com", id=3),
        ]
        original.groups = [
            Group(name="work", color="blue"),
            Group(name="personal", color="green"),
        ]
        original.next_id = 4
        original.language = "zh"

        # Save
        service.save(original)

        # Load
        loaded = service.load()

        # Verify
        assert len(loaded.accounts) == 2
        assert len(loaded.trash) == 1
        assert len(loaded.groups) == 2
        assert loaded.next_id == 4
        assert loaded.language == "zh"
        assert loaded.accounts[0].groups == ["work"]
