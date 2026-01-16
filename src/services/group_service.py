"""
Group management service.
"""

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..models.account import Account
from ..models.group import Group
from ..models.app_state import AppState
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GroupService(QObject):
    """
    Service for managing groups.

    Signals:
        group_added: Emitted when a group is added.
        group_updated: Emitted when a group is updated.
        group_deleted: Emitted when a group is deleted.
        group_reordered: Emitted when groups are reordered.
    """

    group_added = pyqtSignal(Group)
    group_updated = pyqtSignal(Group)
    group_deleted = pyqtSignal(str)  # group name
    group_reordered = pyqtSignal()

    def __init__(self, state: AppState):
        """
        Initialize the group service.

        Args:
            state: The application state to operate on.
        """
        super().__init__()
        self.state = state

    def create(self, name: str, color: str = "red") -> Group:
        """
        Create a new group.

        Args:
            name: The group name.
            color: The group color (name or hex).

        Returns:
            The created group.
        """
        group = Group(name=name, color=color)
        self.state.groups.append(group)
        logger.info(f"Created group: {name}")
        self.group_added.emit(group)
        return group

    def delete(self, name: str) -> Optional[dict]:
        """
        Delete a group and remove it from all accounts.

        Args:
            name: The name of the group to delete.

        Returns:
            Backup data for undo, or None if group not found.
        """
        # Find the group
        group_index = None
        for i, group in enumerate(self.state.groups):
            if group.name == name:
                group_index = i
                break

        if group_index is None:
            logger.warning(f"Group not found: {name}")
            return None

        # Create backup for undo
        group = self.state.groups[group_index]
        affected_accounts = []

        # Remove group from all accounts
        for account in self.state.accounts:
            if account.is_in_group(name):
                affected_accounts.append(account.id)
                account.remove_from_group(name)

        backup = {
            'group': group.to_dict(),
            'index': group_index,
            'affected_accounts': affected_accounts
        }

        # Store backup for undo
        self.state.deleted_group_backup = backup

        # Remove the group
        self.state.groups.pop(group_index)
        logger.info(f"Deleted group: {name}, affected {len(affected_accounts)} accounts")
        self.group_deleted.emit(name)

        return backup

    def rename(self, old_name: str, new_name: str) -> bool:
        """
        Rename a group.

        Args:
            old_name: The current group name.
            new_name: The new group name.

        Returns:
            True if renamed, False if group not found.
        """
        group = self.state.get_group_by_name(old_name)
        if not group:
            return False

        # Update group name
        group.name = new_name

        # Update all accounts
        for account in self.state.accounts:
            if old_name in account.groups:
                account.groups.remove(old_name)
                account.groups.append(new_name)

        logger.info(f"Renamed group: {old_name} -> {new_name}")
        self.group_updated.emit(group)
        return True

    def update_color(self, name: str, color: str) -> bool:
        """
        Update a group's color.

        Args:
            name: The group name.
            color: The new color.

        Returns:
            True if updated, False if group not found.
        """
        group = self.state.get_group_by_name(name)
        if not group:
            return False

        group.color = color
        logger.info(f"Updated group color: {name} -> {color}")
        self.group_updated.emit(group)
        return True

    def reorder(self, new_order: list[str]) -> None:
        """
        Reorder groups according to the given name order.

        Args:
            new_order: List of group names in the desired order.
        """
        # Create a mapping of name to group
        name_to_group = {g.name: g for g in self.state.groups}

        # Rebuild groups list in new order
        new_groups = []
        for name in new_order:
            if name in name_to_group:
                new_groups.append(name_to_group[name])

        # Add any groups not in new_order (shouldn't happen, but be safe)
        for group in self.state.groups:
            if group not in new_groups:
                new_groups.append(group)

        self.state.groups = new_groups
        logger.info(f"Reordered groups: {new_order}")
        self.group_reordered.emit()

    def undo_delete(self) -> Optional[Group]:
        """
        Undo the last group deletion.

        Returns:
            The restored group, or None if nothing to undo.
        """
        backup = self.state.deleted_group_backup
        if not backup:
            return None

        # Restore the group
        group = Group.from_dict(backup['group'])
        index = backup['index']

        # Insert at original position
        if index >= len(self.state.groups):
            self.state.groups.append(group)
        else:
            self.state.groups.insert(index, group)

        # Restore group membership for affected accounts
        for account_id in backup['affected_accounts']:
            account = self.state.get_account_by_id(account_id)
            if account:
                account.add_to_group(group.name)

        # Clear backup
        self.state.deleted_group_backup = None

        logger.info(f"Restored group: {group.name}")
        self.group_added.emit(group)
        return group

    def add_accounts_to_group(self, accounts: list[Account], group_name: str) -> int:
        """
        Add multiple accounts to a group.

        Args:
            accounts: List of accounts to add.
            group_name: The group to add them to.

        Returns:
            Number of accounts added (that weren't already in the group).
        """
        count = 0
        for account in accounts:
            if account.add_to_group(group_name):
                count += 1
        logger.info(f"Added {count} accounts to group: {group_name}")
        return count

    def remove_accounts_from_group(self, accounts: list[Account], group_name: str) -> int:
        """
        Remove multiple accounts from a group.

        Args:
            accounts: List of accounts to remove.
            group_name: The group to remove them from.

        Returns:
            Number of accounts removed.
        """
        count = 0
        for account in accounts:
            if account.remove_from_group(group_name):
                count += 1
        logger.info(f"Removed {count} accounts from group: {group_name}")
        return count

    def get_group_count(self) -> int:
        """Get the number of groups."""
        return len(self.state.groups)

    def get_all_groups(self) -> list[Group]:
        """Get all groups."""
        return self.state.groups.copy()
