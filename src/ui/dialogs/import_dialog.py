"""
Import dialog for batch importing accounts.
"""

from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QComboBox, QWidget, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QColor

from ...models.account import Account
from ...services.import_service import get_import_service
from ..theme import get_theme, get_theme_manager
from ..icons_new import icon_import, icon_file


class ImportDialog(QDialog):
    """Dialog for importing accounts from text or file."""

    def __init__(self, parent: Optional[QWidget] = None, language: str = 'zh'):
        super().__init__(parent)
        self.language = language
        self.import_service = get_import_service()
        self.imported_accounts: List[Account] = []

        self._init_ui()
        self._apply_theme()

    def _init_ui(self):
        """Initialize the dialog UI."""
        zh = self.language == 'zh'
        t = get_theme()

        self.setWindowTitle("批量导入" if zh else "Batch Import")
        self.setMinimumSize(750, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header section
        header = QFrame()
        header.setObjectName("importHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(12)

        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setPixmap(icon_import(24, t.text_primary))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)

        # Title and description
        title_section = QVBoxLayout()
        title_section.setSpacing(4)

        title = QLabel("批量导入账户" if zh else "Batch Import Accounts")
        title.setObjectName("importTitle")
        title_section.addWidget(title)

        subtitle = QLabel(
            "从文本或文件批量导入账户数据" if zh else
            "Import account data from text or file"
        )
        subtitle.setObjectName("importSubtitle")
        title_section.addWidget(subtitle)

        header_layout.addLayout(title_section)
        header_layout.addStretch()

        layout.addWidget(header)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        # Format info card
        format_card = QFrame()
        format_card.setObjectName("formatCard")
        format_card_layout = QVBoxLayout(format_card)
        format_card_layout.setContentsMargins(16, 12, 16, 12)
        format_card_layout.setSpacing(8)

        format_title = QLabel("支持的格式" if zh else "Supported Formats")
        format_title.setObjectName("formatTitle")
        format_card_layout.addWidget(format_title)

        format_text = QLabel(
            "每行一个账户: 邮箱----密码----备用邮箱----2FA密钥\n"
            "支持分隔符: ----  ---  --  ||  |  Tab  ," if zh else
            "One account per line: email----password----backup----2fa_secret\n"
            "Supported separators: ----  ---  --  ||  |  Tab  ,"
        )
        format_text.setObjectName("formatText")
        format_text.setWordWrap(True)
        format_card_layout.addWidget(format_text)

        content_layout.addWidget(format_card)

        # Controls row
        controls = QHBoxLayout()
        controls.setSpacing(12)

        # Separator selection
        sep_label = QLabel("分隔符" if zh else "Separator")
        sep_label.setObjectName("controlLabel")
        controls.addWidget(sep_label)

        self.sep_combo = QComboBox()
        self.sep_combo.setObjectName("sepCombo")
        self.sep_combo.setMinimumWidth(140)
        self.sep_combo.addItem("自动检测" if zh else "Auto-detect", None)
        self.sep_combo.addItem("----", "----")
        self.sep_combo.addItem("---", "---")
        self.sep_combo.addItem("--", "--")
        self.sep_combo.addItem("||", "||")
        self.sep_combo.addItem("|", "|")
        self.sep_combo.addItem("Tab ↹", "\t")
        self.sep_combo.addItem(",", ",")
        self.sep_combo.currentIndexChanged.connect(self._on_separator_changed)
        controls.addWidget(self.sep_combo)

        controls.addStretch()

        # File import button
        self.btn_file = QPushButton()
        self.btn_file.setObjectName("fileBtn")
        self.btn_file.setIcon(QIcon(icon_file(16, t.text_secondary)))
        self.btn_file.setText(" " + ("从文件导入" if zh else "Import from File"))
        self.btn_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_file.clicked.connect(self._import_from_file)
        controls.addWidget(self.btn_file)

        content_layout.addLayout(controls)

        # Splitter for input and preview
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setObjectName("importSplitter")

        # Text input section
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        input_label = QLabel("输入数据" if zh else "Input Data")
        input_label.setObjectName("sectionLabel")
        input_layout.addWidget(input_label)

        self.text_input = QTextEdit()
        self.text_input.setObjectName("textInput")
        self.text_input.setPlaceholderText(
            "在此粘贴账户数据...\n\n"
            "示例:\n"
            "user1@gmail.com----password1----backup1@gmail.com----JBSWY3DPEHPK3PXP\n"
            "user2@gmail.com----password2\n"
            "user3@gmail.com" if zh else
            "Paste account data here...\n\n"
            "Example:\n"
            "user1@gmail.com----password1----backup1@gmail.com----JBSWY3DPEHPK3PXP\n"
            "user2@gmail.com----password2\n"
            "user3@gmail.com"
        )
        self.text_input.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.text_input)

        splitter.addWidget(input_container)

        # Preview section
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)

        preview_header = QHBoxLayout()
        preview_header.setSpacing(8)

        preview_label = QLabel("预览" if zh else "Preview")
        preview_label.setObjectName("sectionLabel")
        preview_header.addWidget(preview_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        preview_header.addWidget(self.status_label)

        preview_header.addStretch()
        preview_layout.addLayout(preview_header)

        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setObjectName("previewTable")
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels([
            "邮箱" if zh else "Email",
            "密码" if zh else "Password",
            "备用邮箱" if zh else "Backup",
            "2FA密钥" if zh else "2FA Secret",
            "状态" if zh else "Status"
        ])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        preview_layout.addWidget(self.preview_table)

        splitter.addWidget(preview_container)

        # Set initial splitter sizes (40% input, 60% preview)
        splitter.setSizes([200, 350])

        content_layout.addWidget(splitter, 1)

        layout.addWidget(content, 1)

        # Footer with buttons
        footer = QFrame()
        footer.setObjectName("importFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.setSpacing(12)

        # Account count
        self.count_label = QLabel("")
        self.count_label.setObjectName("countLabel")
        footer_layout.addWidget(self.count_label)

        footer_layout.addStretch()

        self.btn_cancel = QPushButton("取消" if zh else "Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        self.btn_import = QPushButton("导入" if zh else "Import")
        self.btn_import.setObjectName("importBtn")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.clicked.connect(self._do_import)
        self.btn_import.setEnabled(False)
        footer_layout.addWidget(self.btn_import)

        layout.addWidget(footer)

    def _apply_theme(self):
        """Apply current theme."""
        t = get_theme()
        is_dark = get_theme_manager().is_dark

        # Adjust colors for dark mode
        card_bg = t.bg_secondary if is_dark else "#F8FAFC"
        card_border = t.border
        alt_row_color = t.bg_secondary if is_dark else "#F9FAFB"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}

            #importHeader {{
                background-color: {t.bg_secondary};
                border-bottom: 1px solid {t.border};
            }}

            #importTitle {{
                font-size: 18px;
                font-weight: 600;
                color: {t.text_primary};
            }}

            #importSubtitle {{
                font-size: 13px;
                color: {t.text_tertiary};
            }}

            #formatCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
            }}

            #formatTitle {{
                font-size: 13px;
                font-weight: 600;
                color: {t.text_primary};
            }}

            #formatText {{
                font-size: 12px;
                color: {t.text_secondary};
                line-height: 1.5;
            }}

            #controlLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {t.text_secondary};
            }}

            #sepCombo {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                color: {t.text_primary};
            }}
            #sepCombo::drop-down {{
                border: none;
                width: 24px;
            }}
            #sepCombo QAbstractItemView {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                selection-background-color: {t.bg_hover};
                color: {t.text_primary};
            }}

            #fileBtn {{
                background-color: transparent;
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                color: {t.text_primary};
            }}
            #fileBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #sectionLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {t.text_secondary};
            }}

            #textInput {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 12px;
                font-family: "Consolas", "Monaco", "Microsoft YaHei UI", monospace;
                font-size: 13px;
                color: {t.text_primary};
            }}
            #textInput:focus {{
                border-color: {t.text_secondary};
            }}

            #statusLabel {{
                font-size: 12px;
                color: {t.text_tertiary};
            }}

            #previewTable {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                gridline-color: {t.border};
            }}
            #previewTable::item {{
                padding: 8px;
                border: none;
            }}
            #previewTable::item:selected {{
                background-color: {t.bg_hover};
            }}
            #previewTable QHeaderView::section {{
                background-color: {t.bg_secondary};
                color: {t.text_secondary};
                font-size: 12px;
                font-weight: 500;
                padding: 8px;
                border: none;
                border-bottom: 1px solid {t.border};
            }}
            #previewTable::item:alternate {{
                background-color: {alt_row_color};
            }}

            QSplitter::handle {{
                background-color: transparent;
                height: 8px;
            }}

            #importFooter {{
                background-color: {t.bg_secondary};
                border-top: 1px solid {t.border};
            }}

            #countLabel {{
                font-size: 13px;
                color: {t.text_secondary};
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

            #importBtn {{
                background-color: {t.text_primary};
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 500;
                color: {t.bg_primary};
            }}
            #importBtn:hover {{
                background-color: {t.text_secondary};
            }}
            #importBtn:disabled {{
                background-color: {t.text_tertiary};
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

    def _on_separator_changed(self):
        """Handle separator selection change."""
        self._parse_and_preview()

    def _on_text_changed(self):
        """Handle text input change."""
        self._parse_and_preview()

    def _import_from_file(self):
        """Import from a file."""
        zh = self.language == 'zh'

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件" if zh else "Select File",
            "",
            "文本文件 (*.txt);;CSV 文件 (*.csv);;所有文件 (*.*)" if zh else
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*.*)"
        )

        if file_path:
            try:
                # Try different encodings
                content = None
                for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue

                if content:
                    self.text_input.setPlainText(content)
                else:
                    self._show_error("无法读取文件编码" if zh else "Unable to read file encoding")
            except Exception as e:
                self._show_error(f"无法读取文件: {e}" if zh else f"Failed to read file: {e}")

    def _parse_and_preview(self):
        """Parse input and update preview."""
        zh = self.language == 'zh'
        t = get_theme()
        text = self.text_input.toPlainText().strip()

        # Clear preview
        self.preview_table.setRowCount(0)
        self.imported_accounts = []

        if not text:
            self.status_label.setText("")
            self.count_label.setText("")
            self.btn_import.setEnabled(False)
            return

        separator = self.sep_combo.currentData()

        try:
            accounts = self.import_service.parse_text(text, separator)
            self.imported_accounts = accounts

            # Update preview table
            self.preview_table.setRowCount(len(accounts))

            for row, account in enumerate(accounts):
                # Email
                email_item = QTableWidgetItem(account.email)
                email_item.setForeground(Qt.GlobalColor.white if get_theme_manager().is_dark else Qt.GlobalColor.black)
                self.preview_table.setItem(row, 0, email_item)

                # Password (masked)
                pwd_text = "••••••••" if account.password else "-"
                pwd_item = QTableWidgetItem(pwd_text)
                self.preview_table.setItem(row, 1, pwd_item)

                # Backup
                backup = getattr(account, 'backup', '') or getattr(account, 'backup_email', '') or ''
                backup_item = QTableWidgetItem(backup if backup else "-")
                self.preview_table.setItem(row, 2, backup_item)

                # 2FA Secret (masked)
                secret_text = "••••••••" if account.secret else "-"
                secret_item = QTableWidgetItem(secret_text)
                self.preview_table.setItem(row, 3, secret_item)

                # Status - OK indicator using theme success color
                status_item = QTableWidgetItem("OK")
                status_item.setForeground(QColor(t.success))
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.preview_table.setItem(row, 4, status_item)

            # Update status
            if accounts:
                self.status_label.setText(
                    f"已检测到 {len(accounts)} 个账户" if zh else
                    f"Found {len(accounts)} accounts"
                )
                self.status_label.setStyleSheet(f"color: {t.success}; font-weight: 500;")
                self.count_label.setText(
                    f"将导入 {len(accounts)} 个账户" if zh else
                    f"Will import {len(accounts)} accounts"
                )
                self.btn_import.setEnabled(True)
            else:
                self.status_label.setText("未检测到有效账户" if zh else "No valid accounts")
                self.status_label.setStyleSheet(f"color: {t.warning};")
                self.count_label.setText("")
                self.btn_import.setEnabled(False)

        except Exception as e:
            self.status_label.setText("解析错误" if zh else "Parse error")
            self.status_label.setStyleSheet(f"color: {t.error};")
            self.count_label.setText(str(e))
            self.btn_import.setEnabled(False)

    def _show_error(self, message: str):
        """Show error in status."""
        t = get_theme()
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {t.error};")

    def _do_import(self):
        """Perform the import."""
        if self.imported_accounts:
            self.accept()

    def get_accounts(self) -> List[Account]:
        """Get the imported accounts."""
        return self.imported_accounts
