"""
Pytest configuration and shared fixtures.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.models.account import Account
from src.models.group import Group
from src.models.app_state import AppState
from src.services.account_service import AccountService
from src.services.group_service import GroupService


@pytest.fixture
def sample_account() -> Account:
    """Create a sample account for testing."""
    return Account(
        email="test@example.com",
        password="password123",
        backup="backup@example.com",
        secret="JBSWY3DPEHPK3PXP",
        id=1,
        import_time="2024-01-15 10:30",
        groups=["work"],
        notes="Test account"
    )


@pytest.fixture
def sample_accounts() -> list[Account]:
    """Create a list of sample accounts for testing."""
    return [
        Account(
            email="user1@example.com",
            password="pass1",
            secret="JBSWY3DPEHPK3PXP",
            id=1,
            groups=["work"]
        ),
        Account(
            email="user2@example.com",
            password="pass2",
            secret="HXDMVJECJJWSRB3HWIZR4IFUGFTMXBOZ",
            id=2,
            groups=["personal"]
        ),
        Account(
            email="user3@example.com",
            password="pass3",
            secret="",
            id=3,
            groups=[]
        ),
    ]


@pytest.fixture
def sample_group() -> Group:
    """Create a sample group for testing."""
    return Group(name="work", color="blue")


@pytest.fixture
def sample_groups() -> list[Group]:
    """Create a list of sample groups for testing."""
    return [
        Group(name="work", color="blue"),
        Group(name="personal", color="green"),
        Group(name="shared", color="purple"),
    ]


@pytest.fixture
def empty_state() -> AppState:
    """Create an empty application state."""
    return AppState()


@pytest.fixture
def populated_state(sample_accounts, sample_groups) -> AppState:
    """Create a populated application state."""
    state = AppState()
    state.accounts = sample_accounts.copy()
    state.groups = sample_groups.copy()
    state.next_id = 4
    return state


@pytest.fixture
def account_service(empty_state) -> AccountService:
    """Create an account service with empty state."""
    return AccountService(empty_state)


@pytest.fixture
def populated_account_service(populated_state) -> AccountService:
    """Create an account service with populated state."""
    return AccountService(populated_state)


@pytest.fixture
def group_service(empty_state) -> GroupService:
    """Create a group service with empty state."""
    return GroupService(empty_state)


@pytest.fixture
def populated_group_service(populated_state) -> GroupService:
    """Create a group service with populated state."""
    return GroupService(populated_state)


@pytest.fixture
def temp_data_file():
    """Create a temporary data file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        data = {
            "accounts": [
                {
                    "email": "test@example.com",
                    "password": "testpass",
                    "backup": "",
                    "secret": "JBSWY3DPEHPK3PXP",
                    "id": 1,
                    "import_time": "2024-01-15 10:30",
                    "groups": [],
                    "notes": ""
                }
            ],
            "trash": [],
            "groups": [],
            "next_id": 2,
            "language": "en"
        }
        json.dump(data, f)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
