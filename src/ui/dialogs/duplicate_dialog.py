"""
Dialog for handling duplicate account conflicts during import.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QWidget
)

from ...config.translations import get_conflict_translation
from ..styles import PRIMARY_BUTTON_STYLE, SUCCESS_BUTTON_STYLE, SECONDARY_BUTTON_STYLE


class DuplicateConflictDialog(QDialog):
    """
    Dialog to handle duplicate account conflicts during import.

    Shows a comparison of new vs existing accounts and lets the user
    choose to keep the original or replace with the new data.
    """

    def __init__(
        self,
        conflicts: list[tuple[dict, dict, int]],
        language: str = 'en',
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the conflict dialog.

        Args:
            conflicts: List of tuples (new_account, existing_account, existing_index).
            language: Current UI language ('en' or 'zh').
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.conflicts = conflicts
        self.language = language
        self.choices: dict[int, str] = {}  # index -> 'keep' or 'replace'

        self._setup_ui()

    def _tr(self, key: str) -> str:
        """Get translated text for the given key."""
        return get_conflict_translation(key, self.language)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle(self._tr('conflict_title'))
        self.setMinimumSize(800, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header label
        header = QLabel(self._tr('conflict_header').format(len(self.conflicts)))
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        layout.addWidget(header)

        # Create table
        self._create_table()
        layout.addWidget(self.table)

        # Button row
        self._create_buttons(layout)

    def _create_table(self) -> None:
        """Create the conflict comparison table."""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Email',
            self._tr('original_password'),
            self._tr('new_password'),
            self._tr('original_2fa'),
            self._tr('new_2fa'),
            self._tr('action')
        ])
        self.table.setRowCount(len(self.conflicts))
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        # Set column widths
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 5):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 180)

        # Populate table
        for row, (new_acc, old_acc, _) in enumerate(self.conflicts):
            self._populate_row(row, new_acc, old_acc)

    def _populate_row(self, row: int, new_acc: dict, old_acc: dict) -> None:
        """
        Populate a single row in the table.

        Args:
            row: Row index.
            new_acc: New account data.
            old_acc: Existing account data.
        """
        # Email
        email_item = QTableWidgetItem(new_acc.get('email', ''))
        email_item.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        self.table.setItem(row, 0, email_item)

        # Original password (masked)
        old_pwd = old_acc.get('password', '')
        old_pwd_display = old_pwd[:2] + '***' if len(old_pwd) > 2 else '***'
        self.table.setItem(row, 1, QTableWidgetItem(old_pwd_display))

        # New password (masked)
        new_pwd = new_acc.get('password', '')
        new_pwd_display = new_pwd[:2] + '***' if len(new_pwd) > 2 else '***'
        new_pwd_item = QTableWidgetItem(new_pwd_display)
        if old_pwd != new_pwd:
            new_pwd_item.setForeground(QColor("#DC2626"))  # Red if different
        self.table.setItem(row, 2, new_pwd_item)

        # Original 2FA (masked)
        old_2fa = old_acc.get('secret', '')
        old_2fa_display = old_2fa[:4] + '...' if len(old_2fa) > 4 else old_2fa or '-'
        self.table.setItem(row, 3, QTableWidgetItem(old_2fa_display))

        # New 2FA (masked)
        new_2fa = new_acc.get('secret', '')
        new_2fa_display = new_2fa[:4] + '...' if len(new_2fa) > 4 else new_2fa or '-'
        new_2fa_item = QTableWidgetItem(new_2fa_display)
        if old_2fa != new_2fa:
            new_2fa_item.setForeground(QColor("#DC2626"))  # Red if different
        self.table.setItem(row, 4, new_2fa_item)

        # Action combo box
        combo = QComboBox()
        combo.addItem(self._tr('keep_original'), 'keep')
        combo.addItem(self._tr('use_new'), 'replace')
        combo.setCurrentIndex(0)  # Default to keep original
        combo.currentIndexChanged.connect(lambda idx, r=row: self._on_choice_changed(r))
        self.choices[row] = 'keep'
        self.table.setCellWidget(row, 5, combo)

    def _create_buttons(self, layout: QVBoxLayout) -> None:
        """Create the button row."""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Keep All button
        btn_keep_all = QPushButton(self._tr('keep_all_original'))
        btn_keep_all.setStyleSheet(SECONDARY_BUTTON_STYLE)
        btn_keep_all.clicked.connect(self._keep_all)
        btn_layout.addWidget(btn_keep_all)

        # Replace All button
        btn_replace_all = QPushButton(self._tr('use_all_new'))
        btn_replace_all.setStyleSheet(PRIMARY_BUTTON_STYLE)
        btn_replace_all.clicked.connect(self._replace_all)
        btn_layout.addWidget(btn_replace_all)

        btn_layout.addStretch()

        # Confirm button
        btn_confirm = QPushButton(self._tr('confirm_selection'))
        btn_confirm.setStyleSheet(SUCCESS_BUTTON_STYLE)
        btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(btn_confirm)

        layout.addLayout(btn_layout)

    def _on_choice_changed(self, row: int) -> None:
        """Handle choice change in combo box."""
        combo = self.table.cellWidget(row, 5)
        if isinstance(combo, QComboBox):
            self.choices[row] = combo.currentData()

    def _keep_all(self) -> None:
        """Set all choices to keep original."""
        for row in range(len(self.conflicts)):
            combo = self.table.cellWidget(row, 5)
            if isinstance(combo, QComboBox):
                combo.setCurrentIndex(0)
            self.choices[row] = 'keep'

    def _replace_all(self) -> None:
        """Set all choices to use new."""
        for row in range(len(self.conflicts)):
            combo = self.table.cellWidget(row, 5)
            if isinstance(combo, QComboBox):
                combo.setCurrentIndex(1)
            self.choices[row] = 'replace'

    def get_choices(self) -> dict[int, str]:
        """
        Get the user's choices for each conflict.

        Returns:
            Dict mapping conflict index to choice ('keep' or 'replace').
        """
        return self.choices.copy()
