"""
Library management dialog.
"""

from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ...services.library_service import LibraryService, LibraryInfo
from ..theme import get_theme
from ..icons_new import icon_library, icon_edit, icon_trash, icon_plus


class LibraryDialog(QDialog):
    """Dialog for managing account libraries."""

    def __init__(self, parent=None, library_service: LibraryService = None, language: str = 'zh'):
        super().__init__(parent)
        self.library_service = library_service
        self.language = language
        self.libraries_changed = False

        self._init_ui()
        self._apply_theme()
        self._load_libraries()

    def _init_ui(self):
        """Initialize the dialog UI."""
        zh = self.language == 'zh'

        self.setWindowTitle("管理账号库" if zh else "Manage Libraries")
        self.setMinimumSize(450, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("管理账号库" if zh else "Manage Libraries")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # Library list
        self.library_list = QListWidget()
        self.library_list.setObjectName("libraryList")
        self.library_list.itemClicked.connect(self._on_library_selected)
        self.library_list.itemDoubleClicked.connect(self._rename_library)
        layout.addWidget(self.library_list, 1)

        # Action buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self.btn_add = QPushButton("新建" if zh else "New")
        self.btn_add.setObjectName("actionBtn")
        self.btn_add.clicked.connect(self._create_library)
        action_layout.addWidget(self.btn_add)

        self.btn_rename = QPushButton("重命名" if zh else "Rename")
        self.btn_rename.setObjectName("actionBtn")
        self.btn_rename.setEnabled(False)
        self.btn_rename.clicked.connect(self._rename_library)
        action_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("删除" if zh else "Delete")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_library)
        action_layout.addWidget(self.btn_delete)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_close = QPushButton("关闭" if zh else "Close")
        self.btn_close.setObjectName("closeBtn")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _apply_theme(self):
        """Apply current theme."""
        t = get_theme()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}

            #dialogTitle {{
                font-size: 18px;
                font-weight: 600;
                color: {t.text_primary};
            }}

            #libraryList {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px;
            }}
            #libraryList::item {{
                padding: 12px;
                border-radius: 6px;
                margin: 2px 0;
                color: {t.text_primary};
            }}
            #libraryList::item:hover {{
                background-color: {t.bg_hover};
            }}
            #libraryList::item:selected {{
                background-color: {t.bg_selected};
            }}

            #actionBtn {{
                background-color: transparent;
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                color: {t.text_primary};
            }}
            #actionBtn:hover {{
                background-color: {t.bg_hover};
            }}
            #actionBtn:disabled {{
                color: {t.text_tertiary};
                border-color: {t.bg_tertiary};
            }}

            #dangerBtn {{
                background-color: transparent;
                border: 1px solid {t.error};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                color: {t.error};
            }}
            #dangerBtn:hover {{
                background-color: {t.error};
                color: white;
            }}
            #dangerBtn:disabled {{
                color: {t.text_tertiary};
                border-color: {t.text_tertiary};
            }}

            #closeBtn {{
                background-color: {t.accent};
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                color: white;
            }}
            #closeBtn:hover {{
                opacity: 0.9;
            }}
        """)

    def _load_libraries(self):
        """Load libraries into the list."""
        self.library_list.clear()

        if not self.library_service:
            return

        t = get_theme()
        current = self.library_service.get_current_library()
        libraries = self.library_service.list_libraries()

        for lib in libraries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, lib)

            if lib.id == current.id:
                item.setText(f"{lib.name}  (当前)" if self.language == 'zh' else f"{lib.name}  (current)")
            else:
                item.setText(lib.name)

            item.setIcon(QIcon(icon_library(18, t.text_secondary)))
            self.library_list.addItem(item)

    def _on_library_selected(self, item: QListWidgetItem):
        """Handle library selection."""
        lib = item.data(Qt.ItemDataRole.UserRole)
        if lib:
            libraries = self.library_service.list_libraries()
            # Can't delete if only one library or if it's the current one
            current = self.library_service.get_current_library()
            self.btn_rename.setEnabled(True)
            self.btn_delete.setEnabled(len(libraries) > 1 and lib.id != current.id)

    def _create_library(self):
        """Create a new library."""
        zh = self.language == 'zh'
        name, ok = QInputDialog.getText(
            self,
            "新建账号库" if zh else "New Library",
            "账号库名称:" if zh else "Library name:"
        )

        if ok and name.strip():
            self.library_service.create_library(name.strip())
            self.libraries_changed = True
            self._load_libraries()

    def _rename_library(self):
        """Rename selected library."""
        item = self.library_list.currentItem()
        if not item:
            return

        lib = item.data(Qt.ItemDataRole.UserRole)
        if not lib:
            return

        zh = self.language == 'zh'
        name, ok = QInputDialog.getText(
            self,
            "重命名账号库" if zh else "Rename Library",
            "新名称:" if zh else "New name:",
            text=lib.name
        )

        if ok and name.strip() and name.strip() != lib.name:
            self.library_service.rename_library(lib.id, name.strip())
            self.libraries_changed = True
            self._load_libraries()

    def _delete_library(self):
        """Delete selected library."""
        item = self.library_list.currentItem()
        if not item:
            return

        lib = item.data(Qt.ItemDataRole.UserRole)
        if not lib:
            return

        libraries = self.library_service.list_libraries()
        if len(libraries) <= 1:
            return

        current = self.library_service.get_current_library()
        if lib.id == current.id:
            return

        zh = self.language == 'zh'
        msg = f"确定要删除账号库 \"{lib.name}\" 吗？\n所有账户数据将被永久删除。" if zh else f"Delete library \"{lib.name}\"?\nAll account data will be permanently deleted."

        reply = QMessageBox.warning(
            self,
            "确认删除" if zh else "Confirm Delete",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.library_service.delete_library(lib.id)
            self.libraries_changed = True
            self._load_libraries()
            self.btn_rename.setEnabled(False)
            self.btn_delete.setEnabled(False)

    def has_changes(self) -> bool:
        """Check if libraries were modified."""
        return self.libraries_changed
