"""
G-Account Manager (谷歌账号管家)
A desktop tool to manage Google accounts and generate TOTP 2FA codes.
Features: batch import, group management, auto-refresh, backup & restore.
"""
import sys
import time
import json
import os
import shutil
from datetime import datetime
import pyotp
import urllib.request
from email.utils import parsedate_to_datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QProgressBar, QPlainTextEdit, QGroupBox,
    QAbstractItemView, QDialog, QSplitter, QListWidget, QListWidgetItem,
    QCheckBox, QFrame, QMenu, QInputDialog, QToolButton, QComboBox,
    QSizePolicy
)
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QSize, QMimeData, QPoint
from PyQt6.QtGui import QFont, QColor, QAction, QCursor, QDrag


def get_internet_time():
    """Get current time from internet (Google's server)"""
    try:
        response = urllib.request.urlopen('https://www.google.com', timeout=5)
        date_str = response.headers['Date']
        server_time = parsedate_to_datetime(date_str)
        return server_time.timestamp()
    except:
        return None


def get_time_offset():
    """Calculate offset between local time and internet time"""
    internet_time = get_internet_time()
    if internet_time:
        local_time = time.time()
        offset = internet_time - local_time
        return offset
    return 0  # If can't get internet time, use local time


# Global time offset (calculated once at startup)
TIME_OFFSET = get_time_offset()

# Available color icons for custom groups
GROUP_COLORS = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪']

# Data file path
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '2fa_data.json')


def get_accurate_time():
    """Get accurate time using internet offset"""
    return time.time() + TIME_OFFSET


class ToastNotification(QWidget):
    """Small popup notification that disappears after a timeout"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setStyleSheet("""
            QLabel {
                background-color: #1F2937;
                color: white;
                padding: 12px 24px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.hide()

    def show_message(self, message, parent_widget, duration=2000):
        """Show toast message near the center of parent widget"""
        self.label.setText(message)
        self.label.adjustSize()
        self.adjustSize()

        # Position in center of parent window
        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)

        self.show()
        QTimer.singleShot(duration, self.hide)


class DraggableGroupList(QListWidget):
    """Custom QListWidget that calls a callback after drag-drop reordering"""
    def __init__(self, reorder_callback, parent=None):
        super().__init__(parent)
        self.reorder_callback = reorder_callback

    def dropEvent(self, event):
        super().dropEvent(event)
        # Call the reorder callback after the drop is complete
        if self.reorder_callback:
            QTimer.singleShot(0, self.reorder_callback)


class DragHandle(QLabel):
    """Custom drag handle that initiates drag on the parent QListWidget"""
    def __init__(self, list_widget, list_item, parent=None):
        super().__init__("⋮⋮", parent)
        self.list_widget = list_widget
        self.list_item = list_item
        self.drag_start_pos = None
        self.setFixedWidth(20)
        self.setStyleSheet("color: #9CA3AF; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            # Select the item in the list
            self.list_widget.setCurrentItem(self.list_item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.pos() - self.drag_start_pos).manhattanLength()
            if distance >= 10:  # Minimum drag distance
                # Start drag operation using QListWidget's startDrag
                self.list_widget.setCurrentItem(self.list_item)
                drag = QDrag(self.list_widget)
                mime_data = QMimeData()
                row = self.list_widget.row(self.list_item)
                mime_data.setData("application/x-qabstractitemmodeldatalist", b"")
                mime_data.setText(str(row))
                drag.setMimeData(mime_data)
                drag.exec(Qt.DropAction.MoveAction)
                self.drag_start_pos = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)


class TwoFAGenerator(QMainWindow):
    # Language translations
    TRANSLATIONS = {
        'en': {
            'window_title': 'G-Account Manager',
            'format_hint': 'Format: email----password----secondary_email----2fa_key (auto-detected)',
            'import_accounts': 'Import Accounts',
            'paste_placeholder': 'Paste accounts here (one per line): email----password----secondary_email----2fa_key',
            'add_account': 'Add',
            'import_file': 'Import File',
            'paste_clipboard': 'Paste',
            'clear_all': 'Clear All',
            'remove_duplicates': 'Remove Duplicates',
            'code_expires': 'Code expires in:',
            'refresh_codes': 'Refresh',
            'id': 'ID',
            'email': 'Email',
            'password': 'Password',
            'secondary_email': 'Secondary Email',
            '2fa_key': '2FA Key',
            '2fa_code': '2FA Code',
            'import_time': 'Import Time',
            'delete': 'Delete',
            'accounts': 'Accounts',
            'trash_bin': 'Trash',
            'trash_empty': 'Trash Empty',
            'trash_empty_msg': 'Trash bin is empty.',
            'trash_title': 'Trash Bin ({} items)',
            'restore': 'Restore',
            'delete_permanent': 'Delete Forever',
            'clear_trash': 'Empty Trash',
            'confirm_empty_trash': 'Empty Trash?',
            'confirm_empty_trash_msg': 'Permanently delete all {} items in trash?',
            'language': '中文',
            'copied': 'Copied',
            'confirm_delete': 'Confirm Delete',
            'confirm_delete_msg': 'Move to trash?\n\n{}\n\nYou can restore it from trash later.',
            'confirm_clear': 'Confirm Clear',
            'confirm_clear_msg': 'Move all {} accounts to trash?\n\nYou can restore them from trash later.',
            'backup_created': 'Backup created: {}',
            'no_accounts': 'No Accounts',
            'no_accounts_msg': 'No accounts to process.',
            'no_duplicates': 'No Duplicates',
            'no_duplicates_msg': 'No duplicate accounts found.',
            'remove_duplicates_title': 'Remove Duplicates',
            'remove_duplicates_msg': 'Found {} duplicate account(s).\n\nRemove them and keep only unique accounts?',
            'duplicates_removed': 'Duplicates Removed',
            'duplicates_removed_msg': 'Removed {} duplicate(s).\n\n{} unique accounts remain.',
            'import_complete': 'Import Complete',
            'import_complete_msg': 'Imported {} accounts.\n\nFound {} duplicate(s) (marked yellow).\n\nClick \'Remove Duplicates\' to keep only unique accounts.',
            'imported_accounts': 'Imported {} accounts. Found {} duplicates (yellow). Click \'Remove Duplicates\' to clean.',
            'imported_no_dup': 'Imported {} accounts. No duplicates found.',
            'empty_input': 'Empty Input',
            'empty_input_msg': 'Please paste an account line in the text box first.',
            'empty_clipboard': 'Empty Clipboard',
            'empty_clipboard_msg': 'Clipboard is empty. Copy some account data first.',
            'all_accounts': 'All',
            'ungrouped': 'Ungrouped',
            'tags': 'Tags',
            'groups': 'Groups',
            'manage_groups': 'Manage Groups',
            'add_group': 'Add Group',
            'edit_group': 'Edit Group',
            'delete_group': 'Delete Group',
            'group_name': 'Group Name',
            'group_color': 'Color',
            'add_to_group': 'Add to Group',
            'remove_from_group': 'Remove from Group',
            'batch_add_group': 'Add Selected to Group',
            'batch_remove_group': 'Remove from Group',
            'batch_delete': 'Delete Selected',
            'selected_count': '{} selected',
            'click_to_copy': 'Click cell to copy',
            'confirm_delete_group': 'Delete this group?',
            'confirm_delete_group_msg': 'Delete group "{}"?\n\nAccounts in this group will be moved to Ungrouped.',
            'group_deleted': 'Group "{}" deleted',
            'undo': 'Undo',
            'collapse_import': 'Collapse',
            'expand_import': 'Expand',
            'select_all': 'Select All',
            'deselect_all': 'Deselect All',
            'show_full': 'Show Full',
            'hide_full': 'Hide Full',
            'notes': 'Notes',
            'edit_notes': 'Edit Notes',
            'notes_placeholder': 'Enter notes for this account...',
        },
        'zh': {
            'window_title': '谷歌账号管家',
            'format_hint': '格式: 邮箱----密码----辅助邮箱----2FA密钥 (自动检测)',
            'import_accounts': '导入账号',
            'paste_placeholder': '在此粘贴账号 (每行一个): 邮箱----密码----辅助邮箱----2FA密钥',
            'add_account': '添加',
            'import_file': '导入文件',
            'paste_clipboard': '粘贴',
            'clear_all': '清空全部',
            'remove_duplicates': '删除重复',
            'code_expires': '验证码过期时间:',
            'refresh_codes': '刷新',
            'id': '编号',
            'email': '邮箱',
            'password': '密码',
            'secondary_email': '辅助邮箱',
            '2fa_key': '2FA密钥',
            '2fa_code': '验证码',
            'import_time': '导入时间',
            'delete': '删除',
            'accounts': '账号数',
            'trash_bin': '回收站',
            'trash_empty': '回收站为空',
            'trash_empty_msg': '回收站里没有内容。',
            'trash_title': '回收站 ({} 项)',
            'restore': '恢复',
            'delete_permanent': '永久删除',
            'clear_trash': '清空回收站',
            'confirm_empty_trash': '清空回收站？',
            'confirm_empty_trash_msg': '永久删除回收站中的 {} 项内容？',
            'language': 'EN',
            'copied': '已复制',
            'confirm_delete': '确认删除',
            'confirm_delete_msg': '移到回收站？\n\n{}\n\n之后可以从回收站恢复。',
            'confirm_clear': '确认清空',
            'confirm_clear_msg': '将全部 {} 个账号移到回收站？\n\n之后可以从回收站恢复。',
            'backup_created': '备份已创建: {}',
            'no_accounts': '没有账号',
            'no_accounts_msg': '没有可处理的账号。',
            'no_duplicates': '没有重复',
            'no_duplicates_msg': '没有发现重复的账号。',
            'remove_duplicates_title': '删除重复',
            'remove_duplicates_msg': '发现 {} 个重复账号。\n\n删除它们只保留唯一账号吗?',
            'duplicates_removed': '重复已删除',
            'duplicates_removed_msg': '已删除 {} 个重复账号。\n\n剩余 {} 个唯一账号。',
            'import_complete': '导入完成',
            'import_complete_msg': '已导入 {} 个账号。\n\n发现 {} 个重复(黄色标记)。\n\n点击"删除重复"只保留唯一账号。',
            'imported_accounts': '已导入 {} 个账号。发现 {} 个重复(黄色)。点击"删除重复"清理。',
            'imported_no_dup': '已导入 {} 个账号。没有重复。',
            'empty_input': '输入为空',
            'empty_input_msg': '请先在文本框中粘贴账号信息。',
            'empty_clipboard': '剪贴板为空',
            'empty_clipboard_msg': '剪贴板为空,请先复制账号数据。',
            'all_accounts': '全部',
            'ungrouped': '未分组',
            'tags': '标签',
            'groups': '分组',
            'manage_groups': '管理分组',
            'add_group': '添加分组',
            'edit_group': '编辑分组',
            'delete_group': '删除分组',
            'group_name': '分组名称',
            'group_color': '颜色',
            'add_to_group': '添加到分组',
            'remove_from_group': '从分组移除',
            'batch_add_group': '批量添加到分组',
            'batch_remove_group': '从分组移除',
            'batch_delete': '删除所选',
            'selected_count': '已选 {}',
            'click_to_copy': '点击单元格复制',
            'confirm_delete_group': '删除分组？',
            'confirm_delete_group_msg': '删除分组"{}"？\n\n该分组中的账号将移至"未分组"。',
            'group_deleted': '分组"{}"已删除',
            'undo': '撤销',
            'collapse_import': '收起',
            'expand_import': '展开',
            'select_all': '全选',
            'deselect_all': '取消全选',
            'show_full': '显示完整',
            'hide_full': '隐藏信息',
            'notes': '备注',
            'edit_notes': '编辑备注',
            'notes_placeholder': '输入此账号的备注...',
        }
    }

    def __init__(self):
        super().__init__()
        self.accounts = []  # List of account dicts with 'groups' field
        self.existing_emails = set()  # Track emails to detect duplicates
        self.trash = []  # Trash bin for deleted accounts
        self.toast = ToastNotification()  # Small popup notification
        self.current_lang = 'en'  # Default language
        self.next_id = 1  # Unique ID counter for non-duplicate accounts

        # Group management
        self.custom_groups = []  # List of {'name': str, 'color': str (emoji)}
        self.deleted_group_backup = None  # Backup for undo: {'group': dict, 'index': int, 'affected_accounts': list}
        self.group_dialog = None  # Reference to open group management dialog
        self.current_filter = 'all'  # 'all', 'ungrouped', 'trash', or group name
        self.selected_rows = set()  # Track selected rows for batch operations
        self.show_full_info = False  # Toggle for showing full/masked account info

        # Load saved data
        self.load_data()

        self.init_ui()

        # Auto-refresh timer (every 1 second to update countdown)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(1000)

    def tr(self, key):
        """Get translated text for current language"""
        return self.TRANSLATIONS[self.current_lang].get(key, key)

    def load_data(self):
        """Load accounts and groups from JSON file"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', [])
                    self.trash = data.get('trash', [])
                    self.custom_groups = data.get('groups', [])
                    self.next_id = data.get('next_id', 1)
                    self.current_lang = data.get('language', 'en')
                    # Rebuild existing_emails set
                    for acc in self.accounts:
                        email = acc.get('email', '').lower().strip()
                        if email:
                            self.existing_emails.add(email)
            except Exception as e:
                print(f"Error loading data: {e}")

    def save_data(self):
        """Save accounts and groups to JSON file"""
        try:
            data = {
                'accounts': self.accounts,
                'trash': self.trash,
                'groups': self.custom_groups,
                'next_id': self.next_id,
                'language': self.current_lang
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")

    def create_backup(self):
        """Create a backup of the data file"""
        try:
            if os.path.exists(DATA_FILE):
                # Create backup directory if not exists
                backup_dir = os.path.join(os.path.dirname(DATA_FILE), 'backups')
                os.makedirs(backup_dir, exist_ok=True)

                # Create backup filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_filename = f'2fa_data_backup_{timestamp}.json'
                backup_path = os.path.join(backup_dir, backup_filename)

                # Copy current data file to backup
                shutil.copy2(DATA_FILE, backup_path)

                # Keep only last 10 backups
                self.cleanup_old_backups(backup_dir, keep=10)

                # Show notification
                self.toast.show_message(self.tr('backup_created').format(backup_filename))
                return backup_path
        except Exception as e:
            print(f"Error creating backup: {e}")
        return None

    def cleanup_old_backups(self, backup_dir, keep=10):
        """Remove old backups, keeping only the most recent ones"""
        try:
            backups = sorted([
                f for f in os.listdir(backup_dir)
                if f.startswith('2fa_data_backup_') and f.endswith('.json')
            ], reverse=True)

            # Remove old backups beyond the keep limit
            for old_backup in backups[keep:]:
                os.remove(os.path.join(backup_dir, old_backup))
        except Exception as e:
            print(f"Error cleaning up backups: {e}")

    def switch_language(self):
        """Toggle between English and Chinese"""
        self.current_lang = 'zh' if self.current_lang == 'en' else 'en'
        self.update_ui_language()
        self.save_data()

    def update_ui_language(self):
        """Update all UI elements with current language"""
        self.setWindowTitle(self.tr('window_title'))
        # Update only the suffix part (账号管家 / Account Manager)
        suffix = self.tr('window_title').replace('G-Account Manager', 'Account Manager').replace('谷歌账号管家', '账号管家')
        self.title_label.setText(" " + suffix)
        self.format_hint.setText(self.tr('format_hint'))
        self.btn_toggle_import.setText(
            "▼ " + self.tr('collapse_import') if self.import_content.isVisible()
            else "▶ " + self.tr('expand_import')
        )
        self.text_input.setPlaceholderText(self.tr('paste_placeholder'))
        self.btn_add_line.setText("➕ " + self.tr('add_account'))
        self.btn_import.setText("📂 " + self.tr('import_file'))
        self.btn_clear.setText("🧹 " + self.tr('clear_all'))
        self.btn_remove_duplicates.setText("🔍 " + self.tr('remove_duplicates'))
        self.btn_language.setToolTip(self.tr('language'))
        self.btn_add_group.setToolTip(self.tr('add_group'))
        self.table.setHorizontalHeaderLabels([
            '', self.tr('id'), self.tr('email'), self.tr('password'), self.tr('secondary_email'),
            self.tr('2fa_key'), self.tr('2fa_code'), self.tr('import_time'), self.tr('groups'), self.tr('notes'), ''
        ])
        self.count_label.setText(f"{self.tr('accounts')}: {self.table.rowCount()}")
        self.copy_hint_label.setText("💡 " + self.tr('click_to_copy'))
        self.btn_batch_add_group.setText("📁 " + self.tr('batch_add_group'))
        self.btn_batch_remove_group.setText("➖ " + self.tr('batch_remove_group'))
        self.btn_batch_delete.setText("🗑️ " + self.tr('batch_delete'))
        self.group_label.setText(self.tr('groups'))
        self.update_select_all_button()
        self.update_info_display_button()
        self.refresh_group_list()

    def init_ui(self):
        self.setWindowTitle(self.tr('window_title'))
        self.resize(1280, 800)

        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        main_widget.setLayout(main_layout)

        # Title row - centered modern design
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 5, 0, 5)

        # Left spacer for centering
        header_layout.addStretch()

        # Centered title with Google colors
        title_widget = QWidget()
        title_inner = QHBoxLayout(title_widget)
        title_inner.setContentsMargins(0, 0, 0, 0)
        title_inner.setSpacing(0)

        # Google-style colored letters: G(blue) o(red) o(yellow) g(blue) l(green) e(red)
        colors = ['#4285F4', '#EA4335', '#FBBC05', '#4285F4', '#34A853', '#EA4335']
        letters = ['G', 'o', 'o', 'g', 'l', 'e']
        for letter, color in zip(letters, colors):
            lbl = QLabel(letter)
            lbl.setFont(QFont("Microsoft YaHei", 26, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {color};")
            title_inner.addWidget(lbl)

        # "账号管家" / "Account Manager"
        self.title_label = QLabel(" " + self.tr('window_title').replace('G-Account Manager', 'Account Manager').replace('谷歌账号管家', '账号管家'))
        self.title_label.setFont(QFont("Microsoft YaHei", 26, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #5F6368;")
        title_inner.addWidget(self.title_label)

        header_layout.addWidget(title_widget)

        # Right spacer for centering
        header_layout.addStretch()

        # Language button
        self.btn_language = QPushButton()
        self.btn_language.setFixedSize(42, 42)
        self.btn_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_language.setToolTip(self.tr('language'))

        # Use a label inside for better emoji rendering
        lang_label = QLabel("🌐")
        lang_label.setFont(QFont("Segoe UI Emoji", 18))
        lang_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lang_label.setStyleSheet("background: transparent;")
        lang_layout = QHBoxLayout(self.btn_language)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.addWidget(lang_label)

        self.btn_language.setStyleSheet("""
            QPushButton {
                background-color: #F1F3F4;
                border: 1px solid #DADCE0;
                border-radius: 21px;
            }
            QPushButton:hover {
                background-color: #E8EAED;
                border-color: #4285F4;
            }
        """)
        self.btn_language.clicked.connect(self.switch_language)
        header_layout.addWidget(self.btn_language)

        main_layout.addWidget(header_container)

        # Import Section (Card Style)
        import_card = QFrame()
        import_card.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #E5E7EB; }
        """)
        import_card_layout = QVBoxLayout(import_card)
        import_card_layout.setContentsMargins(15, 15, 15, 15)
        import_card_layout.setSpacing(10)

        # Header for import
        import_header = QHBoxLayout()
        self.btn_toggle_import = QPushButton("▼ " + self.tr('collapse_import'))
        self.btn_toggle_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_import.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #6366F1; font-weight: 700;
                border: none; text-align: left; padding: 0; font-size: 14px;
            }
            QPushButton:hover { color: #4F46E5; }
        """)
        self.btn_toggle_import.clicked.connect(self.toggle_import_section)
        
        self.format_hint = QLabel(self.tr('format_hint'))
        self.format_hint.setStyleSheet("color: #6B7280; font-style: italic; font-size: 12px;")
        
        import_header.addWidget(self.btn_toggle_import)
        import_header.addStretch()
        import_header.addWidget(self.format_hint)
        import_card_layout.addLayout(import_header)

        # Import content
        self.import_content = QWidget()
        self.import_content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        import_content_layout = QVBoxLayout(self.import_content)
        import_content_layout.setContentsMargins(0, 10, 0, 0)
        import_content_layout.setSpacing(15)

        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(self.tr('paste_placeholder'))
        self.text_input.setFixedHeight(70)
        self.text_input.setStyleSheet("border: 1px solid #E5E7EB; background-color: #F9FAFB;")
        import_content_layout.addWidget(self.text_input)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        def create_action_btn(text, color_base, color_hover, icon=""):
            btn = QPushButton(icon + " " + text)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Modern button style
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_base}; color: white; font-weight: 600;
                    border: none; border-radius: 8px; padding: 0 16px;
                }}
                QPushButton:hover {{ background-color: {color_hover}; }}
            """)
            return btn

        self.btn_add_line = create_action_btn(self.tr('add_account'), "#10B981", "#059669", "➕")
        self.btn_add_line.clicked.connect(self.add_from_text_input)
        
        self.btn_import = create_action_btn(self.tr('import_file'), "#3B82F6", "#2563EB", "📂")
        self.btn_import.clicked.connect(self.import_from_file)
        
        self.btn_clear = create_action_btn(self.tr('clear_all'), "#EF4444", "#DC2626", "🧹")
        self.btn_clear.clicked.connect(self.clear_accounts)
        
        self.btn_remove_duplicates = create_action_btn(self.tr('remove_duplicates'), "#F59E0B", "#D97706", "🔍")
        self.btn_remove_duplicates.clicked.connect(self.remove_all_duplicates)

        btn_row.addWidget(self.btn_add_line)
        btn_row.addWidget(self.btn_import)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_remove_duplicates)
        btn_row.addWidget(self.btn_clear)

        import_content_layout.addLayout(btn_row)
        import_card_layout.addWidget(self.import_content)
        
        main_layout.addWidget(import_card)

        # Content Splitter (Sidebar + Table)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(1)
        content_splitter.setChildrenCollapsible(False)

        # Sidebar container
        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 15, 0)
        sidebar_layout.setSpacing(10)

        # Sidebar Header
        sidebar_header = QHBoxLayout()
        self.group_label = QLabel(self.tr('groups'))
        self.group_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.group_label.setStyleSheet("color: #4B5563;")

        sidebar_header.addWidget(self.group_label)
        sidebar_header.addStretch()
        
        # Add Group Button
        self.btn_add_group = QPushButton()
        self.btn_add_group.setFixedSize(28, 28)
        self.btn_add_group.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_group.setToolTip(self.tr('add_group'))
        add_label = QLabel("➕")
        add_label.setFont(QFont("Segoe UI Emoji", 14))
        add_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_label.setStyleSheet("background: transparent;")
        add_btn_layout = QHBoxLayout(self.btn_add_group)
        add_btn_layout.setContentsMargins(0, 0, 0, 0)
        add_btn_layout.addWidget(add_label)
        self.btn_add_group.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: #F3F4F6; border-radius: 4px; }
        """)
        self.btn_add_group.clicked.connect(lambda: self.show_manage_groups(open_add=True))
        sidebar_header.addWidget(self.btn_add_group)
        sidebar_layout.addLayout(sidebar_header)

        # List Widget
        self.group_list = QListWidget()
        self.group_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.group_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { 
                padding: 10px 12px; margin-bottom: 4px; border-radius: 8px; color: #4B5563; font-weight: 500;
            }
            QListWidget::item:hover { background-color: #E5E7EB; color: #1F2937; }
            QListWidget::item:selected { background-color: white; color: #6366F1; border: 1px solid #E5E7EB; }
        """)
        self.group_list.itemClicked.connect(self.on_group_selected)
        sidebar_layout.addWidget(self.group_list)
        
        content_splitter.addWidget(sidebar_container)

        # Table Container
        table_container = QFrame()
        table_container.setStyleSheet("""
            QFrame { background-color: white; border-radius: 12px; border: 1px solid #E5E7EB; }
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        # Toolbar above table
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: transparent; border-bottom: 1px solid #F3F4F6;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)

        # Toggle Info Button (Moved to Left)
        self.btn_toggle_info = QPushButton("🔓 " + self.tr('show_full'))
        self.btn_toggle_info.setFixedHeight(28)
        self.btn_toggle_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_info.setStyleSheet("""
            QPushButton { background-color: transparent; color: #8B5CF6; font-weight: 600; border: 1px solid #EDE9FE; border-radius: 6px; padding: 0 10px; }
            QPushButton:hover { background-color: #F5F3FF; }
        """)
        self.btn_toggle_info.clicked.connect(self.toggle_info_display)
        toolbar_layout.addWidget(self.btn_toggle_info)

        toolbar_layout.addSpacing(15)

        # Countdown timer - simple single label with clock icon
        self.countdown_label = QLabel("⏱ " + self.tr('code_expires') + " 30s")
        self.countdown_label.setFont(QFont("Segoe UI Emoji", 10))
        self.countdown_label.setStyleSheet("color: #10B981; font-weight: bold;")
        toolbar_layout.addWidget(self.countdown_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(30)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #E5E7EB; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #10B981; border-radius: 3px; }
        """)
        toolbar_layout.addWidget(self.progress_bar, 1)

        # Batch tools
        self.batch_toolbar = QWidget()
        batch_layout = QHBoxLayout(self.batch_toolbar)
        batch_layout.setContentsMargins(15, 0, 0, 0)
        batch_layout.setSpacing(8)

        self.selected_label = QLabel("")
        self.selected_label.setStyleSheet("color: #6366F1; font-weight: bold;")
        batch_layout.addWidget(self.selected_label)

        def create_mini_btn(text, color, func):
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            hover_color = ""
            if color == "#10B981": hover_color = "#059669"
            elif color == "#F59E0B": hover_color = "#D97706"
            elif color == "#EF4444": hover_color = "#DC2626"
            else: hover_color = color # Fallback

            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {color}; color: white; font-size: 12px; font-weight: 600; border: none; border-radius: 6px; padding: 0 10px; }}
                QPushButton:hover {{ background-color: {hover_color}; }}
            """)
            btn.clicked.connect(func)
            return btn

        self.btn_batch_add_group = create_mini_btn("📁 " + self.tr('batch_add_group'), "#10B981", self.batch_add_to_group)
        batch_layout.addWidget(self.btn_batch_add_group)

        self.btn_batch_remove_group = create_mini_btn("➖ " + self.tr('batch_remove_group'), "#F59E0B", self.batch_remove_from_group)
        batch_layout.addWidget(self.btn_batch_remove_group)

        self.btn_batch_delete = create_mini_btn("🗑️ " + self.tr('batch_delete'), "#EF4444", self.batch_delete)
        batch_layout.addWidget(self.btn_batch_delete)

        self.batch_toolbar.hide()
        toolbar_layout.addWidget(self.batch_toolbar)

        # Select All is now in header

        table_layout.addWidget(toolbar)

        # The Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        # Header labels (first column is empty since checkbox is in toolbar)
        self.table.setHorizontalHeaderLabels([
            '', self.tr('id'), self.tr('email'), self.tr('password'), self.tr('secondary_email'),
            self.tr('2fa_key'), self.tr('2fa_code'), self.tr('import_time'), self.tr('groups'), self.tr('notes'), ''
        ])
        
        # Table Styling
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False) # Disable for manual highlighting
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(55) # Taller rows
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: white; gridline-color: transparent; }
            QHeaderView::section {
                background-color: white;
                color: #9CA3AF;
                padding: 12px 10px;
                border: none;
                border-bottom: 2px solid #F3F4F6;
                font-weight: 700;
                font-size: 11px;
            }
            QToolTip { color: white; background-color: #1F2937; border: none; }
        """)

        # Column config - Stretch
        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self.on_header_clicked)
        
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed) # Checkbox
        self.table.setColumnWidth(0, 60)
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed) # ID
        self.table.setColumnWidth(1, 50)
        
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Email
        
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed) # Pass
        self.table.setColumnWidth(3, 120)
        
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Backup
        
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed) # Key
        self.table.setColumnWidth(5, 140)
        
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed) # Code
        self.table.setColumnWidth(6, 110)
        
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed) # Time
        self.table.setColumnWidth(7, 120)

        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed) # Tags
        self.table.setColumnWidth(8, 80)
        
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch) # Notes
        
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed) # Delete
        self.table.setColumnWidth(10, 50)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)
        
        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        table_layout.addWidget(self.table)

        # Create header checkbox container (same structure as row checkboxes)
        self.header_checkbox_widget = QWidget(self.table.horizontalHeader())
        header_checkbox_layout = QHBoxLayout(self.header_checkbox_widget)
        header_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        header_checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_checkbox = QCheckBox()
        self.header_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #D1D5DB;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #6366F1;
                border-color: #6366F1;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }
            QCheckBox::indicator:hover {
                border-color: #6366F1;
            }
        """)
        header_checkbox_layout.addWidget(self.header_checkbox)
        self.header_checkbox.stateChanged.connect(self.on_header_checkbox_changed)
        # Position will be updated in resizeEvent
        self.update_header_checkbox_position()
        
        # Footer / Status
        footer = QWidget()
        footer.setStyleSheet("background-color: transparent; border-top: 1px solid #F3F4F6;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 8, 15, 8)
        
        self.count_label = QLabel(f"{self.tr('accounts')}: 0")
        self.count_label.setStyleSheet("color: #6B7280; font-weight: 600; font-size: 12px;")
        footer_layout.addWidget(self.count_label)
        
        footer_layout.addSpacing(20)
        
        self.copy_hint_label = QLabel("💡 " + self.tr('click_to_copy'))
        self.copy_hint_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-style: italic;")
        footer_layout.addWidget(self.copy_hint_label)
        
        footer_layout.addStretch()
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        footer_layout.addWidget(self.status_label)
        
        table_layout.addWidget(footer)
        
        content_splitter.addWidget(table_container)
        
        # Set splitter properties
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([220, 900])
        
        main_layout.addWidget(content_splitter, 1)

        # Initialize group list
        self.refresh_group_list()

        # Load accounts from data into table (recalculates duplicates)
        self.load_accounts_to_table()
        self.save_data()  # Save any ID changes from duplicate recalculation

        # Initial display
        self.update_display()

    def get_remaining_seconds(self):
        """Get seconds remaining until next TOTP code change (using internet time)"""
        return 30 - (int(get_accurate_time()) % 30)

    def toggle_import_section(self):
        """Toggle the visibility of the import section"""
        if self.import_content.isVisible():
            self.import_content.hide()
            self.btn_toggle_import.setText("▶ " + self.tr('expand_import'))
        else:
            self.import_content.show()
            self.btn_toggle_import.setText("▼ " + self.tr('collapse_import'))

    def refresh_group_list(self):
        """Refresh the sidebar group list"""
        self.group_list.clear()

        # Count accounts in each category
        all_count = len(self.accounts)
        ungrouped_count = sum(1 for acc in self.accounts if not acc.get('groups'))
        trash_count = len(self.trash)

        # System groups
        all_item = QListWidgetItem(f"📧 {self.tr('all_accounts')} ({all_count})")
        all_item.setData(Qt.ItemDataRole.UserRole, 'all')
        self.group_list.addItem(all_item)

        ungrouped_item = QListWidgetItem(f"📄 {self.tr('ungrouped')} ({ungrouped_count})")
        ungrouped_item.setData(Qt.ItemDataRole.UserRole, 'ungrouped')
        self.group_list.addItem(ungrouped_item)

        # Custom groups
        for group in self.custom_groups:
            group_count = sum(1 for acc in self.accounts if group['name'] in acc.get('groups', []))
            item = QListWidgetItem(f"{group['color']} {group['name']} ({group_count})")
            item.setData(Qt.ItemDataRole.UserRole, group['name'])
            self.group_list.addItem(item)

        # Trash
        trash_item = QListWidgetItem(f"🗑️ {self.tr('trash_bin')} ({trash_count})")
        trash_item.setData(Qt.ItemDataRole.UserRole, 'trash')
        self.group_list.addItem(trash_item)

        # Select current filter
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_filter:
                self.group_list.setCurrentItem(item)
                break

    def on_group_selected(self, item):
        """Handle group selection in sidebar"""
        selected = item.data(Qt.ItemDataRole.UserRole)

        if selected == 'trash':
            # Show trash dialog
            self.show_trash()
            # Keep current filter, re-select the current item
            for i in range(self.group_list.count()):
                it = self.group_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self.current_filter:
                    self.group_list.setCurrentItem(it)
                    break
        else:
            self.current_filter = selected
            self.filter_table()

    def filter_table(self):
        """Filter table based on selected group"""
        for row in range(self.table.rowCount()):
            # Get account index from row
            id_item = self.table.item(row, 1)
            if not id_item:
                continue

            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is None or account_idx >= len(self.accounts):
                continue

            account = self.accounts[account_idx]
            show = False

            if self.current_filter == 'all':
                show = True
            elif self.current_filter == 'ungrouped':
                show = not account.get('groups')
            elif self.current_filter == 'trash':
                show = False  # Trash items are in self.trash, not in table
            else:
                # Custom group
                show = self.current_filter in account.get('groups', [])

            self.table.setRowHidden(row, not show)

        # Update count for visible rows
        visible_count = sum(1 for row in range(self.table.rowCount()) if not self.table.isRowHidden(row))
        self.count_label.setText(f"{self.tr('accounts')}: {visible_count}")

    def load_accounts_to_table(self):
        """Load all accounts from self.accounts into the table"""
        # Block signals to prevent triggering on_item_changed during load
        self.table.blockSignals(True)

        self.table.setRowCount(0)

        # Recalculate duplicates - first occurrence of each email is not a duplicate
        seen_emails = set()
        for i, account in enumerate(self.accounts):
            email = account.get('email', '').lower().strip()
            is_duplicate = email in seen_emails
            seen_emails.add(email)

            # Update account ID based on current duplicate status
            if is_duplicate:
                account['id'] = None
            elif account.get('id') is None:
                # Was a duplicate but original was deleted, assign new ID
                account['id'] = self.next_id
                self.next_id += 1

            self.add_account_row_to_table(account, i, is_duplicate)

        # Rebuild existing_emails to match current state
        self.existing_emails = seen_emails.copy()

        # Re-enable signals
        self.table.blockSignals(False)

        self.filter_table()

    def update_batch_toolbar(self):
        """Update batch toolbar visibility based on selection"""
        if self.selected_rows:
            self.selected_label.setText(self.tr('selected_count').format(len(self.selected_rows)))
            self.batch_toolbar.show()
        else:
            self.batch_toolbar.hide()

    def on_checkbox_clicked(self, row, checked):
        """Handle checkbox click"""
        if checked:
            self.selected_rows.add(row)
            self.highlight_row(row, True)
        else:
            self.selected_rows.discard(row)
            self.highlight_row(row, False)
        self.update_batch_toolbar()
        self.update_select_all_button()

    def on_checkbox_changed(self, row, state):
        """Handle checkbox state change (legacy)"""
        if state == Qt.CheckState.Checked.value:
            self.selected_rows.add(row)
            self.highlight_row(row, True)
        else:
            self.selected_rows.discard(row)
            self.highlight_row(row, False)
        self.update_batch_toolbar()
        self.update_select_all_button()

    def highlight_row(self, row, selected):
        """Highlight or unhighlight an entire row"""
        # Get account info to check if it's a duplicate
        id_item = self.table.item(row, 1)
        is_duplicate = False
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.accounts):
                is_duplicate = self.accounts[account_idx].get('id') is None

        # Set colors based on selection state
        if selected:
            bg_color = QColor("#E0E7FF")  # Indigo 100 for selected
        elif is_duplicate:
            bg_color = QColor("#FEF3C7")  # Amber 100 for duplicate
        else:
            bg_color = QColor("#FFFFFF")  # White for normal

        # Apply color to checkbox widget (column 0)
        checkbox_widget = self.table.cellWidget(row, 0)
        if checkbox_widget:
            checkbox_widget.setStyleSheet(f"background-color: {bg_color.name()};")

        # Apply color to all item cells (columns 1-9)
        for col in range(1, 10):
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg_color)

        # Apply color to delete button widget (column 10)
        delete_widget = self.table.cellWidget(row, 10)
        if delete_widget:
            delete_widget.setStyleSheet(f"background-color: {bg_color.name()};")

        # Force table to repaint
        self.table.viewport().update()

    def batch_add_to_group(self):
        """Add selected accounts to a group"""
        if not self.selected_rows:
            return

        if not self.custom_groups:
            QMessageBox.information(self, self.tr('groups'),
                                   "No custom groups. Please create a group first.")
            return

        # Show group selection dialog
        groups = [f"{g['color']} {g['name']}" for g in self.custom_groups]
        choice, ok = QInputDialog.getItem(self, self.tr('batch_add_group'),
                                          self.tr('add_to_group'), groups, 0, False)
        if ok and choice:
            # Extract group name (remove color emoji)
            group_name = choice.split(' ', 1)[1] if ' ' in choice else choice

            for row in self.selected_rows:
                id_item = self.table.item(row, 1)
                if id_item:
                    account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                    if account_idx is not None and account_idx < len(self.accounts):
                        if 'groups' not in self.accounts[account_idx]:
                            self.accounts[account_idx]['groups'] = []
                        if group_name not in self.accounts[account_idx]['groups']:
                            self.accounts[account_idx]['groups'].append(group_name)
                        # Update tags cell
                        self.update_tags_cell(row, account_idx)

            self.save_data()
            self.refresh_group_list()
            self.clear_selection()

    def batch_remove_from_group(self):
        """Remove selected accounts from a group (without deleting)"""
        if not self.selected_rows:
            return

        # Collect all groups that selected accounts belong to
        all_groups = set()
        for row in self.selected_rows:
            id_item = self.table.item(row, 1)
            if id_item:
                account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                if account_idx is not None and account_idx < len(self.accounts):
                    for g in self.accounts[account_idx].get('groups', []):
                        all_groups.add(g)

        if not all_groups:
            QMessageBox.information(self, self.tr('groups'),
                                   "Selected accounts are not in any group.")
            return

        # Show group selection dialog
        group_list = []
        for g in self.custom_groups:
            if g['name'] in all_groups:
                group_list.append(f"{g['color']} {g['name']}")

        if not group_list:
            return

        choice, ok = QInputDialog.getItem(self, self.tr('batch_remove_group'),
                                          self.tr('remove_from_group'), group_list, 0, False)
        if ok and choice:
            # Extract group name (remove color emoji)
            group_name = choice.split(' ', 1)[1] if ' ' in choice else choice

            for row in self.selected_rows:
                id_item = self.table.item(row, 1)
                if id_item:
                    account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                    if account_idx is not None and account_idx < len(self.accounts):
                        if group_name in self.accounts[account_idx].get('groups', []):
                            self.accounts[account_idx]['groups'].remove(group_name)
                        # Update tags cell
                        self.update_tags_cell(row, account_idx)

            self.save_data()
            self.refresh_group_list()
            self.filter_table()
            self.clear_selection()

    def batch_delete(self):
        """Delete selected accounts"""
        if not self.selected_rows:
            return

        reply = QMessageBox.question(
            self,
            self.tr('confirm_delete'),
            f"Move {len(self.selected_rows)} accounts to trash?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Sort in reverse to delete from bottom up
            rows_to_delete = sorted(self.selected_rows, reverse=True)
            for row in rows_to_delete:
                id_item = self.table.item(row, 1)
                if id_item:
                    account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                    if account_idx is not None and account_idx < len(self.accounts):
                        # Move to trash
                        self.trash.append(self.accounts[account_idx])
                        self.accounts.pop(account_idx)

            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()
            self.clear_selection()

    def clear_selection(self):
        """Clear all selected checkboxes and unhighlight rows"""
        # Unhighlight all previously selected rows
        for row in list(self.selected_rows):
            self.highlight_row(row, False)

        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self.selected_rows.clear()
        self.update_batch_toolbar()
        self.update_select_all_button()

    def toggle_select_all(self):
        """Toggle select all / deselect all"""
        # Check if all visible rows are selected
        visible_rows = [row for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)]
        all_selected = len(self.selected_rows) >= len(visible_rows) and len(visible_rows) > 0

        if all_selected:
            # Deselect all
            self.clear_selection()
        else:
            # Select all visible rows
            for row in visible_rows:
                widget = self.table.cellWidget(row, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)
            self.update_select_all_button()

    def update_header_checkbox_position(self):
        """Position the header checkbox container to fill first column header"""
        header = self.table.horizontalHeader()
        # Get actual column position and width
        col_x = header.sectionViewportPosition(0)
        col_width = header.sectionSize(0)
        header_height = header.height()
        # Position container to fill the entire column area (checkbox will be centered by layout)
        self.header_checkbox_widget.setGeometry(col_x, 0, col_width, header_height)

    def resizeEvent(self, event):
        """Handle resize to reposition header checkbox"""
        super().resizeEvent(event)
        if hasattr(self, 'header_checkbox_widget'):
            self.update_header_checkbox_position()

    def showEvent(self, event):
        """Handle show event to position header checkbox"""
        super().showEvent(event)
        if hasattr(self, 'header_checkbox_widget'):
            self.update_header_checkbox_position()

    def on_header_checkbox_changed(self, state):
        """Handle header checkbox state change for select all"""
        if state == Qt.CheckState.Checked.value:
            # Select all visible rows
            visible_rows = [row for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)]
            for row in visible_rows:
                widget = self.table.cellWidget(row, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox and not checkbox.isChecked():
                        checkbox.blockSignals(True)
                        checkbox.setChecked(True)
                        checkbox.blockSignals(False)
                        # Manually trigger the selection logic
                        self.selected_rows.add(row)
                        self.highlight_row(row, True)
        else:
            # Deselect all
            self.clear_selection()

    def update_select_all_button(self):
        """Update the select all header checkbox based on current selection"""
        visible_rows = [row for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)]
        all_selected = len(self.selected_rows) >= len(visible_rows) and len(visible_rows) > 0

        # Update header checkbox without triggering signal
        self.header_checkbox.blockSignals(True)
        self.header_checkbox.setChecked(all_selected)
        self.header_checkbox.blockSignals(False)

    def toggle_info_display(self):
        """Toggle between showing masked and full account information"""
        self.show_full_info = not self.show_full_info
        self.update_info_display_button()
        self.refresh_table_display()

    def update_info_display_button(self):
        """Update the toggle info button text"""
        if self.show_full_info:
            self.btn_toggle_info.setText("🔒 " + self.tr('hide_full'))
        else:
            self.btn_toggle_info.setText("🔓 " + self.tr('show_full'))

    def refresh_table_display(self):
        """Refresh the table to show/hide full information"""
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 1)
            if not id_item:
                continue
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is None or account_idx >= len(self.accounts):
                continue

            account = self.accounts[account_idx]

            # Update Email (column 2)
            email_full = account.get('email', '')
            email_item = self.table.item(row, 2)
            if email_item:
                if self.show_full_info:
                    email_item.setText(email_full)
                else:
                    email_item.setText(self.mask_text(email_full, 4))

            # Update Password (column 3)
            password = account.get('password', '')
            password_item = self.table.item(row, 3)
            if password_item:
                if self.show_full_info:
                    password_item.setText(password)
                else:
                    password_item.setText(self.mask_text(password, 2))

            # Update Secondary Email (column 4)
            backup = account.get('backup', '')
            backup_item = self.table.item(row, 4)
            if backup_item:
                if self.show_full_info:
                    backup_item.setText(backup)
                else:
                    backup_item.setText(self.mask_text(backup, 4))

            # Update 2FA Key (column 5)
            secret = account.get('secret', '')
            secret_item = self.table.item(row, 5)
            if secret_item:
                if self.show_full_info:
                    secret_item.setText(secret if secret else "(none)")
                else:
                    if secret:
                        display_secret = secret[:6] + "..." + secret[-4:] if len(secret) > 10 else secret
                    else:
                        display_secret = "(none)"
                    secret_item.setText(display_secret)

    def update_tags_cell(self, row, account_idx):
        """Update the tags cell for a row"""
        account = self.accounts[account_idx]
        groups = account.get('groups', [])

        # Create tags display
        tags_text = ""
        tooltip_parts = []
        for group_name in groups:
            for g in self.custom_groups:
                if g['name'] == group_name:
                    tags_text += g['color']
                    tooltip_parts.append(f"{g['color']} {g['name']}")
                    break

        tags_item = QTableWidgetItem(tags_text)
        tags_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if tooltip_parts:
            tags_item.setToolTip('\n'.join(tooltip_parts))
        self.table.setItem(row, 8, tags_item)

    def show_context_menu(self, pos):
        """Show right-click context menu"""
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)

        # Add to group submenu
        if self.custom_groups:
            add_menu = menu.addMenu("📁 " + self.tr('add_to_group'))
            for group in self.custom_groups:
                action = add_menu.addAction(f"{group['color']} {group['name']}")
                action.triggered.connect(lambda checked, g=group['name'], r=row: self.add_row_to_group(r, g))

        # Remove from group submenu
        id_item = self.table.item(row, 1)
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.accounts):
                account_groups = self.accounts[account_idx].get('groups', [])
                if account_groups:
                    remove_menu = menu.addMenu("➖ " + self.tr('remove_from_group'))
                    for group_name in account_groups:
                        for g in self.custom_groups:
                            if g['name'] == group_name:
                                action = remove_menu.addAction(f"{g['color']} {g['name']}")
                                action.triggered.connect(lambda checked, gn=group_name, r=row: self.remove_row_from_group(r, gn))
                                break

        menu.addSeparator()

        # Edit notes action
        notes_action = menu.addAction("📝 " + self.tr('edit_notes'))
        notes_action.triggered.connect(lambda: self.edit_notes(row))

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("🗑️ " + self.tr('delete'))
        delete_action.triggered.connect(lambda: self.delete_row(row))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def add_row_to_group(self, row, group_name):
        """Add a single row to a group"""
        id_item = self.table.item(row, 1)
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.accounts):
                if 'groups' not in self.accounts[account_idx]:
                    self.accounts[account_idx]['groups'] = []
                if group_name not in self.accounts[account_idx]['groups']:
                    self.accounts[account_idx]['groups'].append(group_name)
                self.update_tags_cell(row, account_idx)
                self.save_data()
                self.refresh_group_list()

    def remove_row_from_group(self, row, group_name):
        """Remove a single row from a group"""
        id_item = self.table.item(row, 1)
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.accounts):
                if group_name in self.accounts[account_idx].get('groups', []):
                    self.accounts[account_idx]['groups'].remove(group_name)
                self.update_tags_cell(row, account_idx)
                self.save_data()
                self.refresh_group_list()
                self.filter_table()

    def on_header_clicked(self, index):
        """Handle header section clicks (Select All)"""
        if index == 0:
            self.toggle_select_all()

    def show_manage_groups(self, open_add=False):
        """Show group management panel"""
        # If dialog already open, bring to front
        if hasattr(self, 'group_dialog') and self.group_dialog is not None:
            self.group_dialog.raise_()
            self.group_dialog.activateWindow()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr('manage_groups'))
        dialog.resize(420, 450)
        dialog.setStyleSheet("""
            QDialog { background-color: white; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        dialog.setLayout(layout)

        # Title row with add button
        title_row = QHBoxLayout()
        title = QLabel(self.tr('manage_groups'))
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #111827;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Add new group button
        btn_show_add = QPushButton()
        btn_show_add.setFixedSize(36, 36)
        btn_show_add.setCursor(Qt.CursorShape.PointingHandCursor)
        show_add_label = QLabel("➕")
        show_add_label.setFont(QFont("Segoe UI Emoji", 18))
        show_add_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        show_add_label.setStyleSheet("background: transparent;")
        show_add_layout = QHBoxLayout(btn_show_add)
        show_add_layout.setContentsMargins(0, 0, 0, 0)
        show_add_layout.addWidget(show_add_label)
        btn_show_add.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: #F3F4F6; border-radius: 8px; }
        """)
        title_row.addWidget(btn_show_add)
        layout.addLayout(title_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #E5E7EB;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # Add new group section (visible by default)
        add_section = QFrame()
        add_section.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)

        add_layout = QHBoxLayout(add_section)
        add_layout.setContentsMargins(12, 12, 12, 12)
        add_layout.setSpacing(10)

        # Icon selector (dropdown)
        self.icon_combo = QComboBox()
        self.icon_combo.setFixedSize(40, 36)
        self.icon_combo.setStyleSheet("""
            QComboBox {
                font-size: 16px;
                font-family: "Segoe UI Emoji";
                border: none;
                background: transparent;
                padding-left: 8px;
            }
            QComboBox:hover { background-color: #F3F4F6; border-radius: 6px; }
            QComboBox::drop-down { width: 0; border: none; }
            QComboBox::down-arrow { width: 0; height: 0; }
            QComboBox QAbstractItemView {
                font-size: 16px;
                font-family: "Segoe UI Emoji";
                selection-background-color: #EEF2FF;
            }
        """)
        for color in GROUP_COLORS:
            self.icon_combo.addItem(color)
        add_layout.addWidget(self.icon_combo)

        # Name input
        from PyQt6.QtWidgets import QLineEdit
        self.group_name_input = QLineEdit()
        self.group_name_input.setFixedHeight(36)
        self.group_name_input.setPlaceholderText(self.tr('group_name'))
        self.group_name_input.setStyleSheet("""
            QLineEdit {
                font-size: 13px;
                padding: 6px 10px;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                background-color: white;
            }
            QLineEdit:focus { border-color: #6366F1; }
        """)
        add_layout.addWidget(self.group_name_input, 1)
        # Auto focus on name input
        self.group_name_input.setFocus()

        # Confirm add button
        btn_add = QPushButton()
        btn_add.setFixedSize(36, 36)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        add_ok_label = QLabel("✅")
        add_ok_label.setFont(QFont("Segoe UI Emoji", 16))
        add_ok_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_ok_label.setStyleSheet("background: transparent;")
        add_ok_layout = QHBoxLayout(btn_add)
        add_ok_layout.setContentsMargins(0, 0, 0, 0)
        add_ok_layout.addWidget(add_ok_label)
        btn_add.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: #ECFDF5; border-radius: 8px; }
        """)
        add_layout.addWidget(btn_add)

        # Cancel button
        btn_cancel = QPushButton()
        btn_cancel.setFixedSize(36, 36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_label = QLabel("❌")
        cancel_label.setFont(QFont("Segoe UI Emoji", 16))
        cancel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cancel_label.setStyleSheet("background: transparent;")
        cancel_layout = QHBoxLayout(btn_cancel)
        cancel_layout.setContentsMargins(0, 0, 0, 0)
        cancel_layout.addWidget(cancel_label)
        btn_cancel.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: #FEF2F2; border-radius: 8px; }
        """)
        add_layout.addWidget(btn_cancel)

        layout.addWidget(add_section)

        def toggle_add_section():
            if add_section.isVisible():
                add_section.hide()
            else:
                add_section.show()
                self.group_name_input.clear()
                self.group_name_input.setFocus()

        btn_show_add.clicked.connect(toggle_add_section)
        btn_cancel.clicked.connect(lambda: add_section.hide())

        # Group list with drag & drop support
        self.groups_list_widget = DraggableGroupList(self.on_groups_reordered)
        self.groups_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.groups_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.groups_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.groups_list_widget.setSpacing(4)
        self.groups_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 0px;
            }
            QListWidget::item:selected {
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #D1D5DB;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9CA3AF;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        # Store dialog reference BEFORE populating (needed by refresh_group_items guard)
        self.group_dialog = dialog

        # Populate groups
        self.refresh_group_items()

        layout.addWidget(self.groups_list_widget, 1)

        def add_new_group():
            name = self.group_name_input.text().strip()
            if not name:
                return
            color = self.icon_combo.currentText()
            self.custom_groups.append({'name': name, 'color': color})
            self.save_data()
            self.refresh_group_list()
            self.refresh_group_items()
            self.group_name_input.clear()
            # Keep add section open for adding more groups

        btn_add.clicked.connect(add_new_group)

        # Use non-modal dialog so undo toast can be clicked
        dialog.setModal(False)
        dialog.finished.connect(lambda: setattr(self, 'group_dialog', None))
        dialog.show()

    def refresh_group_items(self):
        """Refresh the group items in the manage dialog"""
        # Check if dialog is open and widget exists
        if not hasattr(self, 'groups_list_widget') or self.groups_list_widget is None:
            return
        if not hasattr(self, 'group_dialog') or self.group_dialog is None:
            return

        # Clear existing items
        self.groups_list_widget.clear()

        # Add group items
        for i, group in enumerate(self.custom_groups):
            self.add_group_item_widget(group, i)

        if not self.custom_groups:
            # Show empty state
            empty_item = QListWidgetItem()
            empty_widget = QLabel("📂 " + ("暂无分组" if self.current_lang == 'zh' else "No groups yet"))
            empty_widget.setStyleSheet("color: #9CA3AF; padding: 30px; font-size: 14px;")
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setSizeHint(empty_widget.sizeHint())
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)  # Not selectable or draggable
            self.groups_list_widget.addItem(empty_item)
            self.groups_list_widget.setItemWidget(empty_item, empty_widget)

    def add_group_item_widget(self, group, index):
        """Add a single group item widget"""
        from PyQt6.QtWidgets import QLineEdit

        # Create list item first (needed for drag handle)
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 52))
        list_item.setData(Qt.ItemDataRole.UserRole, index)  # Store original index

        item_widget = QWidget()
        item_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }
            QWidget:hover {
                border-color: #6366F1;
                background-color: #FAFAFA;
            }
        """)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 8, 12, 8)
        item_layout.setSpacing(8)

        # Drag handle (uses custom DragHandle class)
        drag_handle = DragHandle(self.groups_list_widget, list_item)
        item_layout.addWidget(drag_handle)

        # Icon selector
        icon_combo = QComboBox()
        icon_combo.setFixedSize(36, 32)
        icon_combo.setStyleSheet("""
            QComboBox {
                font-size: 14px;
                font-family: "Segoe UI Emoji";
                border: none;
                background: transparent;
                padding-left: 7px;
            }
            QComboBox:hover { background-color: #E5E7EB; border-radius: 6px; }
            QComboBox::drop-down { width: 0; border: none; }
            QComboBox::down-arrow { width: 0; height: 0; }
            QComboBox QAbstractItemView {
                font-size: 14px;
                font-family: "Segoe UI Emoji";
            }
        """)
        for color in GROUP_COLORS:
            icon_combo.addItem(color)
        icon_combo.setCurrentText(group['color'])
        icon_combo.currentTextChanged.connect(lambda c, idx=index: self.update_group_color(idx, c))
        item_layout.addWidget(icon_combo)

        # Name input (single line)
        name_input = QLineEdit()
        name_input.setText(group['name'])
        name_input.setFixedHeight(32)
        name_input.setStyleSheet("""
            QLineEdit {
                font-size: 13px;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                background-color: #F9FAFB;
                padding: 4px 8px;
            }
            QLineEdit:focus { border-color: #6366F1; background-color: white; }
        """)
        name_input.textChanged.connect(lambda text, idx=index: self.update_group_name(idx, text.strip()))
        item_layout.addWidget(name_input, 1)

        # Delete button
        btn_delete = QPushButton()
        btn_delete.setFixedSize(28, 28)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_label = QLabel("🗑️")
        delete_label.setFont(QFont("Segoe UI Emoji", 12))
        delete_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delete_label.setStyleSheet("background: transparent; border: none;")
        delete_layout = QHBoxLayout(btn_delete)
        delete_layout.setContentsMargins(0, 0, 0, 0)
        delete_layout.addWidget(delete_label)
        btn_delete.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: #FEF2F2; border-radius: 6px; }
        """)
        btn_delete.clicked.connect(lambda checked, idx=index: self.delete_group_at(idx))
        item_layout.addWidget(btn_delete)

        # Add list item and set widget
        self.groups_list_widget.addItem(list_item)
        self.groups_list_widget.setItemWidget(list_item, item_widget)

    def update_group_color(self, index, new_color):
        """Update group color"""
        if index < len(self.custom_groups):
            self.custom_groups[index]['color'] = new_color
            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()

    def update_group_name(self, index, new_name):
        """Update group name"""
        if index < len(self.custom_groups) and new_name:
            old_name = self.custom_groups[index]['name']
            if old_name != new_name:
                # Update accounts with this group
                for acc in self.accounts:
                    if old_name in acc.get('groups', []):
                        acc['groups'].remove(old_name)
                        acc['groups'].append(new_name)
                self.custom_groups[index]['name'] = new_name
                self.save_data()
                self.load_accounts_to_table()
                self.refresh_group_list()

    def delete_group_at(self, index):
        """Delete group at index with confirmation and undo support"""
        if index < len(self.custom_groups):
            group = self.custom_groups[index]

            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                self.tr('confirm_delete_group'),
                self.tr('confirm_delete_group_msg').format(group['name']),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Backup for undo - store affected accounts
            affected_accounts = []
            for acc in self.accounts:
                if group['name'] in acc.get('groups', []):
                    affected_accounts.append(acc.get('id') or acc.get('email'))
                    acc['groups'].remove(group['name'])

            # Store backup
            self.deleted_group_backup = {
                'group': group.copy(),
                'index': index,
                'affected_accounts': affected_accounts
            }

            # Remove group
            self.custom_groups.pop(index)
            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()
            self.refresh_group_items()

            # Show undo toast
            self.show_undo_toast(group['name'])

    def show_undo_toast(self, group_name):
        """Show toast with undo button for deleted group"""
        # Hide any existing undo toast first
        self.hide_undo_toast()

        # Create undo toast as a modeless dialog to appear above modal dialogs
        self.undo_toast = QDialog()
        self.undo_toast.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.undo_toast.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.undo_toast.setModal(False)

        layout = QHBoxLayout(self.undo_toast)
        layout.setContentsMargins(0, 0, 0, 0)

        # Container with styling
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #1F2937;
                border-radius: 20px;
            }
        """)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(16, 10, 16, 10)
        container_layout.setSpacing(12)

        # Message label
        msg_label = QLabel(self.tr('group_deleted').format(group_name))
        msg_label.setStyleSheet("color: white; font-size: 13px; font-weight: 500; background: transparent;")
        container_layout.addWidget(msg_label)

        # Undo button
        undo_btn = QPushButton(self.tr('undo'))
        undo_btn.setStyleSheet("""
            QPushButton {
                color: #60A5FA;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
                padding: 4px 8px;
            }
            QPushButton:hover {
                color: #93C5FD;
                text-decoration: underline;
            }
        """)
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        undo_btn.clicked.connect(self.undo_delete_group)
        container_layout.addWidget(undo_btn)

        layout.addWidget(container)

        # Position at bottom center of main window
        self.undo_toast.adjustSize()
        parent_rect = self.geometry()
        toast_x = parent_rect.x() + (parent_rect.width() - self.undo_toast.width()) // 2
        toast_y = parent_rect.y() + parent_rect.height() - self.undo_toast.height() - 80
        self.undo_toast.move(toast_x, toast_y)
        self.undo_toast.show()
        self.undo_toast.raise_()  # Ensure it's on top

        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, self.hide_undo_toast)

    def hide_undo_toast(self):
        """Hide the undo toast"""
        if hasattr(self, 'undo_toast') and self.undo_toast:
            self.undo_toast.hide()
            self.undo_toast.deleteLater()
            self.undo_toast = None

    def undo_delete_group(self):
        """Restore the last deleted group"""
        try:
            if not self.deleted_group_backup:
                return

            backup = self.deleted_group_backup

            # Restore group at original position
            index = min(backup['index'], len(self.custom_groups))
            self.custom_groups.insert(index, backup['group'])

            # Restore group to affected accounts
            group_name = backup['group']['name']
            for acc in self.accounts:
                acc_id = acc.get('id') or acc.get('email')
                if acc_id in backup['affected_accounts']:
                    if 'groups' not in acc:
                        acc['groups'] = []
                    if group_name not in acc['groups']:
                        acc['groups'].append(group_name)

            # Clear backup
            self.deleted_group_backup = None

            # Save and refresh
            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()

            # Only refresh group items if dialog is still open and valid
            try:
                if self.group_dialog is not None and self.group_dialog.isVisible():
                    self.refresh_group_items()
            except RuntimeError:
                pass  # Widget was deleted

            # Hide undo toast
            self.hide_undo_toast()

            # Show confirmation
            self.toast.show_message(f"✓ {group_name}")
        except Exception as e:
            print(f"Undo error: {e}")

    def move_group_up(self, index):
        """Move group up in the list"""
        if index > 0 and index < len(self.custom_groups):
            self.custom_groups[index], self.custom_groups[index - 1] = \
                self.custom_groups[index - 1], self.custom_groups[index]
            self.save_data()
            self.refresh_group_list()
            self.refresh_group_items()

    def move_group_down(self, index):
        """Move group down in the list"""
        if index >= 0 and index < len(self.custom_groups) - 1:
            self.custom_groups[index], self.custom_groups[index + 1] = \
                self.custom_groups[index + 1], self.custom_groups[index]
            self.save_data()
            self.refresh_group_list()
            self.refresh_group_items()

    def on_groups_reordered(self):
        """Handle group reordering after drag and drop"""
        if not hasattr(self, 'groups_list_widget'):
            return

        # Get new order from list widget
        new_order = []
        for i in range(self.groups_list_widget.count()):
            item = self.groups_list_widget.item(i)
            if item:
                original_index = item.data(Qt.ItemDataRole.UserRole)
                if original_index is not None and original_index < len(self.custom_groups):
                    new_order.append(self.custom_groups[original_index])

        # Update custom_groups with new order
        if len(new_order) == len(self.custom_groups):
            self.custom_groups = new_order
            self.save_data()
            self.refresh_group_list()
            # Refresh items to update stored indices
            self.refresh_group_items()

    def update_display(self):
        """Update countdown bar and refresh codes if needed"""
        remaining = self.get_remaining_seconds()
        self.progress_bar.setValue(remaining)

        # Update countdown label
        self.countdown_label.setText(f"⏱ {self.tr('code_expires')} {remaining}s")

        # Change color based on time remaining
        base_style = """
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #E5E7EB;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background-color: %s;
            }
        """
        if remaining <= 5:
            self.progress_bar.setStyleSheet(base_style % "#EF4444")
            self.countdown_label.setStyleSheet("color: #EF4444; font-weight: bold;")
        elif remaining <= 10:
            self.progress_bar.setStyleSheet(base_style % "#F59E0B")
            self.countdown_label.setStyleSheet("color: #F59E0B; font-weight: bold;")
        else:
            self.progress_bar.setStyleSheet(base_style % "#10B981")
            self.countdown_label.setStyleSheet("color: #10B981; font-weight: bold;")

        # Refresh codes when timer resets (remaining == 30)
        if remaining == 30:
            self.refresh_codes()

    def refresh_codes(self):
        """Refresh all 2FA codes in the table"""
        for row in range(self.table.rowCount()):
            secret_item = self.table.item(row, 5)  # 2FA Key is column 5
            if secret_item:
                secret = secret_item.data(Qt.ItemDataRole.UserRole)  # Get full secret from stored data
                if secret:
                    try:
                        code = self.generate_code(secret)
                        code_item = QTableWidgetItem(code)
                        code_item.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                        code_item.setForeground(QColor("#2196F3"))
                        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table.setItem(row, 6, code_item)  # 2FA Code is column 6
                    except:
                        pass

    def generate_code(self, secret):
        """Generate TOTP code from secret (using internet time)"""
        clean_secret = secret.strip().replace(" ", "").replace("-", "").upper()
        totp = pyotp.TOTP(clean_secret)
        # Use accurate internet time instead of local time
        accurate_time = get_accurate_time()
        return totp.at(accurate_time)

    def detect_separator(self, lines):
        """Auto-detect the separator used in the file"""
        # Check first line for separator declaration
        first_line = lines[0].strip() if lines else ""

        if first_line.startswith("分隔符="):
            sep = first_line.split("=")[1].strip().strip('"').strip("'")
            return sep, lines[1:]  # Return separator and remaining lines

        # Auto-detect from content
        # Priority order: explicit separators first, then space as fallback
        separators = ["----", "---", "||", "|", "\t", ","]

        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            for sep in separators:
                parts = line.split(sep)
                if len(parts) >= 2:  # At least email and something else
                    return sep, lines

            # If no explicit separator found, try space-separated format
            # Check if line has multiple @ symbols (likely multiple emails)
            # and splitting by space gives reasonable results
            if line.count('@') >= 1:
                parts = line.split()
                if len(parts) >= 2:
                    # Verify first part looks like an email
                    if '@' in parts[0]:
                        return " ", lines  # Use space as separator

        return "----", lines  # Default

    def parse_account_line(self, line, separator):
        """Parse a single account line into components"""
        # For space separator, use split() without args to handle multiple spaces
        if separator == " ":
            parts = line.split()
        else:
            parts = line.split(separator)

        account = {
            'email': parts[0].strip() if len(parts) > 0 else '',
            'password': parts[1].strip() if len(parts) > 1 else '',
            'backup': parts[2].strip() if len(parts) > 2 else '',
            'secret': parts[3].strip() if len(parts) > 3 else ''
        }

        return account

    def import_from_file(self):
        """Import accounts from a text file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Account File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.process_lines(lines)

        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to import file:\n{e}")

    def add_from_text_input(self):
        """Add accounts from the text input field (supports multiple lines)"""
        text = self.text_input.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, self.tr('empty_input'), self.tr('empty_input_msg'))
            return

        # Process multiple lines
        lines = text.split('\n')
        self.process_lines(lines)

        # Clear input
        self.text_input.clear()
        self.text_input.setFocus()

    def process_lines(self, lines):
        """Process lines of account data"""
        # Detect separator
        separator, data_lines = self.detect_separator(lines)

        # Block signals to prevent triggering on_item_changed during batch import
        self.table.blockSignals(True)

        count = 0
        duplicate_count = 0
        for line in data_lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            account = self.parse_account_line(line, separator)

            # Add account even if no 2FA key (will show empty code)
            # Use batch_mode to avoid saving for each account
            is_dup = self.add_account_to_table(account, batch_mode=True)
            count += 1
            if is_dup:
                duplicate_count += 1

        # Re-enable signals
        self.table.blockSignals(False)

        # Save once after all accounts are added
        if count > 0:
            self.save_data()
            self.refresh_group_list()
            self.filter_table()

        self.count_label.setText(f"{self.tr('accounts')}: {len(self.accounts)}")

        # Show summary with duplicate info
        if duplicate_count > 0:
            self.status_label.setText(self.tr('imported_accounts').format(count, duplicate_count))
            self.status_label.setStyleSheet("color: orange;")
            QMessageBox.information(
                self,
                self.tr('import_complete'),
                self.tr('import_complete_msg').format(count, duplicate_count)
            )
        else:
            self.status_label.setText(self.tr('imported_no_dup').format(count))
        self.status_label.setStyleSheet("color: green;")

    def mask_text(self, text, show_chars=3):
        """Mask middle part of text, show first and last few characters"""
        if not text or len(text) <= show_chars * 2:
            return text
        return text[:show_chars] + "***" + text[-show_chars:]

    def add_account_to_table(self, account, batch_mode=False):
        """Add a NEW account to both self.accounts and the table. Returns True if duplicate.
        Set batch_mode=True to skip saving (for batch imports)."""
        email = account.get('email', '').lower().strip()

        # Check for duplicate
        is_duplicate = email in self.existing_emails

        # Add to tracking set
        self.existing_emails.add(email)

        # Assign ID if not duplicate
        if not is_duplicate:
            account['id'] = self.next_id
            self.next_id += 1
        else:
            account['id'] = None

        # Add import time if not present
        if 'import_time' not in account:
            account['import_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Initialize groups list
        if 'groups' not in account:
            account['groups'] = []

        # Add to accounts list
        account_idx = len(self.accounts)
        self.accounts.append(account)

        # Add row to table
        self.add_account_row_to_table(account, account_idx, is_duplicate)

        # Save data (skip in batch mode)
        if not batch_mode:
            self.save_data()
            self.refresh_group_list()

        return is_duplicate

    def add_account_row_to_table(self, account, account_idx, is_duplicate=False):
        """Add a row to the table for an existing account in self.accounts."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Column 0: Checkbox - centered in widget
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #D1D5DB;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #6366F1;
                border-color: #6366F1;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }
            QCheckBox::indicator:hover {
                border-color: #6366F1;
            }
        """)
        checkbox.clicked.connect(lambda checked, r=row: self.on_checkbox_clicked(r, checked))
        checkbox_layout.addWidget(checkbox)
        self.table.setCellWidget(row, 0, checkbox_widget)

        # Column 1: ID
        acc_id = account.get('id')
        if acc_id is None:
            id_item = QTableWidgetItem("-")
            id_item.setForeground(QColor("#9CA3AF"))
        else:
            id_item = QTableWidgetItem(str(acc_id))
            id_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # Store account index for later reference
        id_item.setData(Qt.ItemDataRole.UserRole + 1, account_idx)
        # Make non-editable
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            id_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 1, id_item)

        # Column 2: Email (masked or full based on setting, store original)
        email_full = account.get('email', '')
        email_display = email_full if self.show_full_info else self.mask_text(email_full, 4)
        email_item = QTableWidgetItem(email_display)
        email_item.setData(Qt.ItemDataRole.UserRole, email_full)
        email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            email_item.setBackground(QColor("#FEF3C7"))
            email_item.setToolTip("DUPLICATE - This email already exists!")
        self.table.setItem(row, 2, email_item)

        # Column 3: Password (masked or full based on setting, store original)
        password = account.get('password', '')
        password_display = password if self.show_full_info else self.mask_text(password, 2)
        password_item = QTableWidgetItem(password_display)
        password_item.setData(Qt.ItemDataRole.UserRole, password)
        password_item.setFlags(password_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            password_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 3, password_item)

        # Column 4: Secondary Email (masked or full based on setting, store original)
        backup = account.get('backup', '')
        backup_display = backup if self.show_full_info else self.mask_text(backup, 4)
        backup_item = QTableWidgetItem(backup_display)
        backup_item.setData(Qt.ItemDataRole.UserRole, backup)
        backup_item.setFlags(backup_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            backup_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 4, backup_item)

        # Column 5: 2FA Key (masked or full based on setting, store full)
        secret = account.get('secret', '')
        if self.show_full_info:
            display_secret = secret if secret else "(none)"
        else:
            if secret:
                display_secret = secret[:6] + "..." + secret[-4:] if len(secret) > 10 else secret
            else:
                display_secret = "(none)"
        secret_item = QTableWidgetItem(display_secret)
        secret_item.setData(Qt.ItemDataRole.UserRole, secret)
        secret_item.setFlags(secret_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            secret_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 5, secret_item)

        # Column 6: 2FA Code
        if secret:
            try:
                code = self.generate_code(secret)
                code_item = QTableWidgetItem(code)
                code_item.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                code_item.setForeground(QColor("#2563EB"))
                code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception as e:
                code_item = QTableWidgetItem("ERROR")
                code_item.setForeground(QColor("#EF4444"))
                code_item.setToolTip(str(e))
        else:
            code_item = QTableWidgetItem("-")
            code_item.setForeground(QColor("#9CA3AF"))
        code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            code_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 6, code_item)

        # Column 7: Import Time
        import_time = account.get('import_time', datetime.now().strftime("%Y-%m-%d %H:%M"))
        time_item = QTableWidgetItem(import_time)
        time_item.setForeground(QColor("#6B7280"))
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            time_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 7, time_item)

        # Column 8: Tags (group indicators)
        groups = account.get('groups', [])
        tags_text = ""
        tooltip_parts = []
        for group_name in groups:
            for g in self.custom_groups:
                if g['name'] == group_name:
                    tags_text += g['color']
                    tooltip_parts.append(f"{g['color']} {g['name']}")
                    break
        tags_item = QTableWidgetItem(tags_text)
        tags_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        tags_item.setFlags(tags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if tooltip_parts:
            tags_item.setToolTip('\n'.join(tooltip_parts))
        self.table.setItem(row, 8, tags_item)

        # Column 9: Notes (editable)
        notes = account.get('notes', '')
        notes_item = QTableWidgetItem(notes)
        notes_item.setForeground(QColor("#6B7280"))
        # Make notes column editable
        notes_item.setFlags(notes_item.flags() | Qt.ItemFlag.ItemIsEditable)
        if is_duplicate:
            notes_item.setBackground(QColor("#FEF3C7"))
        self.table.setItem(row, 9, notes_item)

        # Column 10: Delete button (centered)
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_delete = QPushButton("🗑")
        btn_delete.setFixedSize(26, 26)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                border-radius: 6px;
            }
        """)
        btn_delete.setToolTip("Delete this account")
        btn_delete.clicked.connect(lambda checked, r=row: self.delete_row(r))
        btn_layout.addWidget(btn_delete)
        self.table.setCellWidget(row, 10, btn_container)

    def on_item_changed(self, item):
        """Handle item changes (for inline notes editing)"""
        if item is None:
            return

        column = item.column()
        row = item.row()

        # Only handle notes column (9)
        if column != 9:
            return

        # Get account index from ID column
        id_item = self.table.item(row, 1)
        if not id_item:
            return

        account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
        if account_idx is None or account_idx >= len(self.accounts):
            return

        # Update account notes
        new_notes = item.text()
        self.accounts[account_idx]['notes'] = new_notes

        # Save data
        self.save_data()

    def on_cell_clicked(self, row, column):
        """Copy cell content to clipboard when clicked, or edit notes/tags"""
        # Don't copy: Checkbox(0), ID(1), Import Time(7), Delete button(10)
        if column in [0, 1, 7, 10]:
            return

        # Show tag removal popup (column 8)
        if column == 8:
            self.show_tag_popup(row)
            return

        # Edit notes directly in cell on click (column 9)
        if column == 9:
            item = self.table.item(row, column)
            if item:
                self.table.editItem(item)
            return

        item = self.table.item(row, column)
        if item:
            # Get original (unmasked) value from UserRole for columns 2-5
            if column in [2, 3, 4, 5]:
                text = item.data(Qt.ItemDataRole.UserRole)
            else:
                text = item.text()

            if text and text != "(none)" and text != "-":
                clipboard = QApplication.clipboard()
                clipboard.setText(text)

                # Visual feedback - highlight the copied cell yellow
                original_bg = item.background()
                item.setBackground(QColor("#FEF08A"))  # Yellow highlight

                # Reset background after 500ms
                QTimer.singleShot(500, lambda: item.setBackground(original_bg))

                # Show which column was copied using translations
                # Columns: 0=checkbox, 1=id, 2=email, 3=password, 4=secondary, 5=2fa_key, 6=2fa_code, 7=time, 8=tags, 9=notes, 10=delete
                column_keys = ['', 'id', 'email', 'password', 'secondary_email', '2fa_key', '2fa_code', 'import_time', 'tags', 'notes', '']
                col_name = self.tr(column_keys[column]) if column < len(column_keys) else "Text"

                # Show toast notification popup
                toast_text = f"{self.tr('copied')}: {col_name}"
                self.toast.show_message(toast_text, self, 1000)

    def show_tag_popup(self, row):
        """Show a popup to manage tags for an account"""
        id_item = self.table.item(row, 1)
        if not id_item:
            return

        account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
        if account_idx is None or account_idx >= len(self.accounts):
            return

        account = self.accounts[account_idx]
        account_groups = account.get('groups', [])

        if not account_groups:
            # No groups, show option to add
            self.show_add_group_popup(row, account_idx)
            return

        # Create popup menu at cursor position
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px 8px 10px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #FEE2E2;
            }
        """)

        # Add header
        header_action = menu.addAction("📌 " + self.tr('remove_from_group'))
        header_action.setEnabled(False)
        menu.addSeparator()

        # Add each group as a removable item
        for group_name in account_groups:
            for g in self.custom_groups:
                if g['name'] == group_name:
                    action = menu.addAction(f"❌ {g['color']} {g['name']}")
                    action.triggered.connect(
                        lambda checked, gn=group_name, r=row, idx=account_idx: self.quick_remove_from_group(r, idx, gn)
                    )
                    break

        menu.addSeparator()

        # Add option to add more groups
        if self.custom_groups:
            add_menu = menu.addMenu("➕ " + self.tr('add_to_group'))
            for group in self.custom_groups:
                if group['name'] not in account_groups:
                    action = add_menu.addAction(f"{group['color']} {group['name']}")
                    action.triggered.connect(
                        lambda checked, gn=group['name'], r=row, idx=account_idx: self.quick_add_to_group(r, idx, gn)
                    )

        # Show menu at cursor position
        menu.exec(QCursor.pos())

    def show_add_group_popup(self, row, account_idx):
        """Show popup to add groups when account has no groups"""
        if not self.custom_groups:
            QMessageBox.information(self, self.tr('groups'), "No custom groups. Please create a group first.")
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px 8px 10px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #DBEAFE;
            }
        """)

        header_action = menu.addAction("➕ " + self.tr('add_to_group'))
        header_action.setEnabled(False)
        menu.addSeparator()

        for group in self.custom_groups:
            action = menu.addAction(f"{group['color']} {group['name']}")
            action.triggered.connect(
                lambda checked, gn=group['name'], r=row, idx=account_idx: self.quick_add_to_group(r, idx, gn)
            )

        menu.exec(QCursor.pos())

    def quick_remove_from_group(self, row, account_idx, group_name):
        """Quickly remove account from group via popup"""
        if account_idx < len(self.accounts):
            if group_name in self.accounts[account_idx].get('groups', []):
                self.accounts[account_idx]['groups'].remove(group_name)
                self.update_tags_cell(row, account_idx)
                self.save_data()
                self.refresh_group_list()
                self.filter_table()

    def quick_add_to_group(self, row, account_idx, group_name):
        """Quickly add account to group via popup"""
        if account_idx < len(self.accounts):
            if 'groups' not in self.accounts[account_idx]:
                self.accounts[account_idx]['groups'] = []
            if group_name not in self.accounts[account_idx]['groups']:
                self.accounts[account_idx]['groups'].append(group_name)
                self.update_tags_cell(row, account_idx)
                self.save_data()
                self.refresh_group_list()

    def edit_notes(self, row):
        """Edit notes for an account - start inline editing"""
        notes_item = self.table.item(row, 9)
        if notes_item:
            self.table.editItem(notes_item)

    def remove_all_duplicates(self):
        """Remove all duplicate accounts, keeping only the first occurrence of each email"""
        if not self.accounts:
            QMessageBox.information(self, self.tr('no_accounts'), self.tr('no_accounts_msg'))
            return

        seen_emails = set()
        indices_to_delete = []

        # Find all duplicate accounts (keep first occurrence, mark later ones for deletion)
        for i, acc in enumerate(self.accounts):
            email = acc.get('email', '').lower().strip()
            if email in seen_emails:
                indices_to_delete.append(i)
            else:
                seen_emails.add(email)

        if not indices_to_delete:
            QMessageBox.information(self, self.tr('no_duplicates'), self.tr('no_duplicates_msg'))
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            self.tr('remove_duplicates_title'),
            self.tr('remove_duplicates_msg').format(len(indices_to_delete)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete from bottom to top
            for i in reversed(indices_to_delete):
                self.accounts.pop(i)

            # Rebuild tracking set
            self.existing_emails.clear()
            for acc in self.accounts:
                email = acc.get('email', '').lower().strip()
                if email:
                    self.existing_emails.add(email)

            # Save and reload
            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()

            # Update UI
            self.count_label.setText(f"{self.tr('accounts')}: {len(self.accounts)}")
            self.status_label.setText(self.tr('duplicates_removed_msg').format(len(indices_to_delete), len(self.accounts)))
            self.status_label.setStyleSheet("color: green;")

            QMessageBox.information(
                self,
                self.tr('duplicates_removed'),
                self.tr('duplicates_removed_msg').format(len(indices_to_delete), len(self.accounts))
            )

    def copy_code(self, row):
        """Copy 2FA code to clipboard"""
        # Find the actual row (in case rows were deleted)
        actual_row = self.find_row_by_original(row)
        if actual_row < 0:
            return

        code_item = self.table.item(actual_row, 6)  # 2FA Code is column 6
        if code_item:
            code = code_item.text()
            if code and code != "-" and code != "ERROR":
                clipboard = QApplication.clipboard()
                clipboard.setText(code)
                self.status_label.setText(f"Copied code: {code}")
                self.status_label.setStyleSheet("color: blue;")
            else:
                self.status_label.setText("No valid code to copy")
                self.status_label.setStyleSheet("color: red;")

    def find_row_by_original(self, original_row):
        """Find the current row index (rows may shift after deletions)"""
        # For simplicity, we'll just return the row if it exists
        if original_row < self.table.rowCount():
            return original_row
        return -1

    def delete_row(self, row):
        """Move account to trash bin with confirmation"""
        # Get account index from ID column
        id_item = self.table.item(row, 1)
        if not id_item:
            return

        account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
        if account_idx is None or account_idx >= len(self.accounts):
            return

        account = self.accounts[account_idx]
        email = account.get('email', 'this account')

        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            self.tr('confirm_delete'),
            self.tr('confirm_delete_msg').format(email),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Move to trash
        self.trash.append(self.accounts.pop(account_idx))

        # Rebuild existing_emails
        self.existing_emails.clear()
        for acc in self.accounts:
            email_addr = acc.get('email', '').lower().strip()
            if email_addr:
                self.existing_emails.add(email_addr)

        # Save and reload
        self.save_data()
        self.load_accounts_to_table()
        self.refresh_group_list()

        # Show toast
        self.toast.show_message(f"{self.tr('trash_bin')}: +1", self, 1000)

    def reconnect_buttons(self):
        """Reconnect all button callbacks after row deletion - not needed with reload approach"""
        pass  # Table is fully reloaded, no need to reconnect

    def clear_accounts(self):
        """Clear all accounts - move to trash with backup"""
        if not self.accounts:
            return

        account_count = len(self.accounts)
        reply = QMessageBox.question(
            self,
            self.tr('confirm_clear'),
            self.tr('confirm_clear_msg').format(account_count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Create backup before clearing
            self.create_backup()

            # Move all accounts to trash instead of deleting
            for acc in self.accounts:
                acc['deleted_at'] = datetime.now().isoformat()
                self.trash.append(acc)

            # Clear accounts
            self.accounts.clear()
            self.existing_emails.clear()
            self.next_id = 1
            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()
            self.count_label.setText(f"{self.tr('accounts')}: 0")
            self.status_label.setText("")
            self.status_label.setStyleSheet("color: gray;")

    def show_trash(self):
        """Show trash bin dialog"""
        if not self.trash:
            QMessageBox.information(self, self.tr('trash_empty'), self.tr('trash_empty_msg'))
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr('trash_title').format(len(self.trash)))
        dialog.resize(800, 400)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # Create table for trash items (same style as main table)
        trash_table = QTableWidget()
        trash_table.setColumnCount(5)
        trash_table.setHorizontalHeaderLabels([
            self.tr('email'), self.tr('password'), self.tr('secondary_email'),
            self.tr('2fa_key'), self.tr('import_time')
        ])
        trash_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        trash_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        trash_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        trash_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        trash_table.verticalHeader().setDefaultSectionSize(50)
        trash_table.verticalHeader().setVisible(False)
        trash_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #E5E7EB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #DBEAFE;
                color: #1E40AF;
            }
            QHeaderView::section {
                background-color: #F3F4F6;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #E5E7EB;
                font-weight: bold;
            }
        """)

        # Fill table with trash items
        for i, account in enumerate(self.trash):
            trash_table.insertRow(i)
            trash_table.setItem(i, 0, QTableWidgetItem(account.get('email', '')))
            trash_table.setItem(i, 1, QTableWidgetItem(account.get('password', '')))
            trash_table.setItem(i, 2, QTableWidgetItem(account.get('backup', '')))
            secret = account.get('secret', '')
            display_secret = secret[:6] + "..." + secret[-4:] if len(secret) > 10 else secret
            secret_item = QTableWidgetItem(display_secret)
            secret_item.setData(Qt.ItemDataRole.UserRole, secret)
            trash_table.setItem(i, 3, secret_item)
            trash_table.setItem(i, 4, QTableWidgetItem(account.get('import_time', '')))

        layout.addWidget(trash_table)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_restore = QPushButton("♻️ " + self.tr('restore'))
        btn_restore.setFixedHeight(36)
        btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #10B981; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 15px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(btn_restore)

        btn_delete = QPushButton("❌ " + self.tr('delete_permanent'))
        btn_delete.setFixedHeight(36)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 15px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn_layout.addWidget(btn_delete)

        btn_clear = QPushButton("🗑️ " + self.tr('clear_trash'))
        btn_clear.setFixedHeight(36)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #6B7280; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 15px;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        btn_layout.addWidget(btn_clear)

        layout.addLayout(btn_layout)

        def restore_selected():
            selected = trash_table.selectedItems()
            if not selected:
                return
            rows = set(item.row() for item in selected)
            for row in sorted(rows, reverse=True):
                account = self.trash.pop(row)
                # Restore account to main list
                email = account.get('email', '').lower().strip()
                is_dup = email in self.existing_emails
                if not is_dup:
                    account['id'] = self.next_id
                    self.next_id += 1
                    self.existing_emails.add(email)
                else:
                    account['id'] = None
                self.accounts.append(account)
                trash_table.removeRow(row)

            self.save_data()
            self.load_accounts_to_table()
            self.refresh_group_list()
            self.count_label.setText(f"{self.tr('accounts')}: {len(self.accounts)}")
            if not self.trash:
                dialog.close()
            else:
                dialog.setWindowTitle(self.tr('trash_title').format(len(self.trash)))

        def delete_selected():
            selected = trash_table.selectedItems()
            if not selected:
                return
            rows = set(item.row() for item in selected)
            for row in sorted(rows, reverse=True):
                self.trash.pop(row)
                trash_table.removeRow(row)
            self.save_data()
            self.refresh_group_list()
            if not self.trash:
                dialog.close()
            else:
                dialog.setWindowTitle(self.tr('trash_title').format(len(self.trash)))

        def clear_all_trash():
            reply = QMessageBox.question(
                dialog,
                self.tr('confirm_empty_trash'),
                self.tr('confirm_empty_trash_msg').format(len(self.trash)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.trash.clear()
                self.save_data()
                self.refresh_group_list()
                dialog.close()

        btn_restore.clicked.connect(restore_selected)
        btn_delete.clicked.connect(delete_selected)
        btn_clear.clicked.connect(clear_all_trash)

        dialog.exec()


def main():
    app = QApplication(sys.argv)

    # Set font - use bold (黑体) for all text
    font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
    app.setFont(font)

    # Modern Global Stylesheet
    app.setStyleSheet("""
        QMainWindow { background-color: #F3F4F6; }
        QWidget { color: #374151; outline: none; }
        QToolTip { background-color: #1F2937; color: white; border: none; padding: 6px 10px; border-radius: 4px; }
        
        /* Scrollbars */
        QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; }
        QScrollBar::handle:vertical { background: #CBD5E1; min-height: 20px; border-radius: 4px; }
        QScrollBar::handle:vertical:hover { background: #94A3B8; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QScrollBar:horizontal { border: none; background: transparent; height: 8px; margin: 0px; }
        QScrollBar::handle:horizontal { background: #CBD5E1; min-width: 20px; border-radius: 4px; }
        QScrollBar::handle:horizontal:hover { background: #94A3B8; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

        /* Menus */
        QMenu { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 6px; }
        QMenu::item { padding: 8px 24px 8px 12px; border-radius: 6px; margin: 2px 0; }
        QMenu::item:selected { background-color: #EFF6FF; color: #2563EB; }
        QMenu::separator { height: 1px; background: #E5E7EB; margin: 4px 0; }

        /* Inputs */
        QLineEdit, QPlainTextEdit, QTextEdit { 
            border: 1px solid #D1D5DB; 
            border-radius: 8px; 
            padding: 10px; 
            background-color: white; 
            selection-background-color: #818CF8; 
            selection-color: white; 
        }
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus { 
            border: 1px solid #6366F1; 
            background-color: white;
        }

        /* Buttons (Generic) */
        QPushButton { border-radius: 6px; font-weight: 600; padding: 6px 16px; }
        
        /* Group Box */
        QGroupBox { border: 1px solid #E5E7EB; border-radius: 8px; margin-top: 1em; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; font-weight: bold; color: #4B5563; }
        
        /* Splitter */
        QSplitter::handle { background-color: #E5E7EB; width: 1px; }
    """)

    window = TwoFAGenerator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
