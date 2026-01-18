"""
Account dialog for adding and editing accounts.
"""

from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QComboBox, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ...models.account import Account
from ...models.group import Group
from ..theme import get_theme, get_theme_manager
from ..icons_new import icon_eye, icon_eye_off, icon_user, icon_plus


class AccountDialog(QDialog):
    """Dialog for adding or editing an account."""

    def __init__(self, parent=None, account: Optional[Account] = None,
                 groups: List[Group] = None, language: str = 'zh'):
        super().__init__(parent)
        self.account = account
        self.groups = groups or []
        self.language = language
        self.is_edit = account is not None
        self.result_account: Optional[Account] = None

        self._init_ui()
        self._apply_theme()

        if self.is_edit:
            self._load_account_data()

    def _init_ui(self):
        """Initialize the dialog UI."""
        zh = self.language == 'zh'
        t = get_theme()

        if self.is_edit:
            self.setWindowTitle("编辑账户" if zh else "Edit Account")
        else:
            self.setWindowTitle("添加账户" if zh else "Add Account")

        self.setMinimumSize(480, 520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header section
        header = QFrame()
        header.setObjectName("dialogHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        if self.is_edit:
            icon_label.setPixmap(icon_user(24, t.text_primary))
        else:
            icon_label.setPixmap(icon_plus(24, t.text_primary))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)

        # Title and description
        title_section = QVBoxLayout()
        title_section.setSpacing(4)

        title = QLabel("编辑账户" if self.is_edit else "添加账户" if zh else "Edit Account" if self.is_edit else "Add Account")
        title.setObjectName("dialogTitle")
        title_section.addWidget(title)

        subtitle = QLabel(
            "修改账户信息" if self.is_edit else "添加新的账户信息" if zh else
            "Modify account information" if self.is_edit else "Add new account information"
        )
        subtitle.setObjectName("dialogSubtitle")
        title_section.addWidget(subtitle)

        header_layout.addLayout(title_section)
        header_layout.addStretch()

        layout.addWidget(header)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        # Form scroll area
        scroll = QScrollArea()
        scroll.setObjectName("formScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(16)

        # Email field
        self.email_input = self._create_field(
            form_layout,
            "邮箱 / 账户名" if zh else "Email / Username",
            "user@example.com"
        )

        # Password field
        self.password_input = self._create_password_field(
            form_layout,
            "密码" if zh else "Password",
            "可选" if zh else "Optional"
        )

        # Secret key field
        self.secret_input = self._create_password_field(
            form_layout,
            "2FA 密钥" if zh else "2FA Secret Key",
            "JBSWY3DPEHPK3PXP"
        )

        # Group selection
        group_label = QLabel("分组" if zh else "Group")
        group_label.setObjectName("fieldLabel")
        form_layout.addWidget(group_label)

        self.group_combo = QComboBox()
        self.group_combo.setObjectName("groupCombo")
        self.group_combo.addItem("无" if zh else "None", None)
        for group in self.groups:
            self.group_combo.addItem(group.name, group.name)
        form_layout.addWidget(self.group_combo)

        # Notes field
        self.notes_input = self._create_field(
            form_layout,
            "备注" if zh else "Notes",
            "可选" if zh else "Optional"
        )

        form_layout.addStretch()
        scroll.setWidget(form_widget)
        content_layout.addWidget(scroll, 1)

        layout.addWidget(content, 1)

        # Footer with buttons
        footer = QFrame()
        footer.setObjectName("dialogFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.setSpacing(12)

        footer_layout.addStretch()

        self.btn_cancel = QPushButton("取消" if zh else "Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("保存" if zh else "Save")
        self.btn_save.setObjectName("saveBtn")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        footer_layout.addWidget(self.btn_save)

        layout.addWidget(footer)

    def _create_field(self, layout: QVBoxLayout, label: str, placeholder: str) -> QLineEdit:
        """Create a form field."""
        field_label = QLabel(label)
        field_label.setObjectName("fieldLabel")
        layout.addWidget(field_label)

        field_input = QLineEdit()
        field_input.setPlaceholderText(placeholder)
        field_input.setObjectName("fieldInput")
        layout.addWidget(field_input)

        return field_input

    def _create_password_field(self, layout: QVBoxLayout, label: str, placeholder: str) -> QLineEdit:
        """Create a password field with toggle."""
        t = get_theme()

        field_label = QLabel(label)
        field_label.setObjectName("fieldLabel")
        layout.addWidget(field_label)

        row = QHBoxLayout()
        row.setSpacing(8)

        field_input = QLineEdit()
        field_input.setPlaceholderText(placeholder)
        field_input.setEchoMode(QLineEdit.EchoMode.Password)
        field_input.setObjectName("fieldInput")
        row.addWidget(field_input, 1)

        toggle_btn = QPushButton()
        toggle_btn.setObjectName("toggleBtn")
        toggle_btn.setFixedSize(40, 40)
        toggle_btn.setIcon(QIcon(icon_eye(16, t.text_secondary)))
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def toggle():
            if field_input.echoMode() == QLineEdit.EchoMode.Password:
                field_input.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setIcon(QIcon(icon_eye_off(16, t.text_secondary)))
            else:
                field_input.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setIcon(QIcon(icon_eye(16, t.text_secondary)))

        toggle_btn.clicked.connect(toggle)
        row.addWidget(toggle_btn)

        container = QWidget()
        container.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(container)

        return field_input

    def _apply_theme(self):
        """Apply current theme."""
        t = get_theme()
        is_dark = get_theme_manager().is_dark

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}

            #dialogHeader {{
                background-color: {t.bg_secondary};
                border-bottom: 1px solid {t.border};
            }}

            #dialogTitle {{
                font-size: 18px;
                font-weight: 600;
                color: {t.text_primary};
            }}

            #dialogSubtitle {{
                font-size: 13px;
                color: {t.text_tertiary};
            }}

            #fieldLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {t.text_secondary};
            }}

            #fieldInput {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                color: {t.text_primary};
            }}
            #fieldInput:focus {{
                border-color: {t.text_secondary};
            }}

            #toggleBtn {{
                background-color: transparent;
                border: 1px solid {t.border};
                border-radius: 6px;
            }}
            #toggleBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #groupCombo {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                color: {t.text_primary};
            }}
            #groupCombo::drop-down {{
                border: none;
                width: 30px;
            }}
            #groupCombo QAbstractItemView {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                selection-background-color: {t.bg_hover};
                color: {t.text_primary};
            }}

            #formScroll {{
                background: transparent;
                border: none;
            }}
            #formScroll > QWidget > QWidget {{
                background: transparent;
            }}

            #dialogFooter {{
                background-color: {t.bg_secondary};
                border-top: 1px solid {t.border};
            }}

            #cancelBtn {{
                background-color: transparent;
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                color: {t.text_primary};
            }}
            #cancelBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #saveBtn {{
                background-color: {t.text_primary};
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                color: {t.bg_primary};
            }}
            #saveBtn:hover {{
                background-color: {t.text_secondary};
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t.text_tertiary};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t.text_secondary};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

    def _load_account_data(self):
        """Load existing account data for editing."""
        if not self.account:
            return

        self.email_input.setText(self.account.email)

        if self.account.password:
            self.password_input.setText(self.account.password)

        if self.account.secret:
            self.secret_input.setText(self.account.secret)

        if self.account.groups:
            index = self.group_combo.findData(self.account.groups[0])
            if index >= 0:
                self.group_combo.setCurrentIndex(index)

        if self.account.notes:
            self.notes_input.setText(self.account.notes)

    def _save(self):
        """Save the account."""
        email = self.email_input.text().strip()
        if not email:
            self.email_input.setFocus()
            return

        password = self.password_input.text().strip() or None
        secret = self.secret_input.text().strip() or None
        notes = self.notes_input.text().strip() or None

        group = self.group_combo.currentData()
        groups = [group] if group else []

        if self.is_edit and self.account:
            # Update existing account
            self.account.email = email
            self.account.password = password
            self.account.secret = secret
            self.account.notes = notes
            self.account.groups = groups
            self.result_account = self.account
        else:
            # Create new account
            self.result_account = Account(
                email=email,
                password=password,
                secret=secret,
                notes=notes,
                groups=groups
            )

        self.accept()

    def get_account(self) -> Optional[Account]:
        """Get the resulting account."""
        return self.result_account
