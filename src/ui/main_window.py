"""
Main window for G-Account Manager.
This is the refactored version using the new service layer.
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QProgressBar, QPlainTextEdit,
    QAbstractItemView, QDialog, QSplitter, QListWidget, QListWidgetItem,
    QCheckBox, QFrame, QMenu, QInputDialog, QToolButton,
    QSizePolicy, QLineEdit, QGridLayout, QColorDialog, QWidgetAction
)
from PyQt6.QtCore import Qt, QTimer, QSize, QMimeData
from PyQt6.QtGui import QFont, QColor, QIcon, QFontMetrics, QDrag

from ..config.settings import Settings
from ..config.translations import TRANSLATIONS, get_translation
from ..config.constants import GROUP_COLORS, get_color_hex
from ..models.app_state import AppState
from ..models.account import Account
from ..models.group import Group
from ..services.totp_service import TotpService, get_totp_service
from ..services.time_service import get_accurate_time
from ..services.data_service import DataService
from ..services.account_service import AccountService
from ..services.group_service import GroupService
from ..services.import_service import ImportService
from ..services.backup_service import BackupService
from ..utils.logger import get_logger
from .icons import (
    create_color_icon, create_tag_icon, create_dot_icon, create_arrow_icon, create_list_icon,
    create_folder_icon, create_trash_icon, create_plus_icon,
    create_import_icon, create_clear_icon, create_lock_icon,
    create_clock_icon, create_minus_icon, create_check_icon, create_close_icon,
    create_edit_icon, create_restore_icon, get_pastel_color,
)
from .widgets.toast import ToastNotification
from .dialogs.duplicate_dialog import DuplicateConflictDialog

logger = get_logger(__name__)

# 获取 check.svg 的绝对路径（项目根目录）
CHECK_SVG_PATH = str(Path(__file__).parent.parent.parent / "check.svg").replace("\\", "/")


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


class MainWindow(QMainWindow):
    """
    Main application window with refactored architecture.

    Uses dependency injection for services to enable testing and modularity.
    """

    def __init__(
        self,
        data_service: Optional[DataService] = None,
        backup_service: Optional[BackupService] = None,
    ):
        super().__init__()

        # Initialize services
        self.data_service = data_service or DataService()
        self.backup_service = backup_service or BackupService()
        self.totp_service = get_totp_service()
        self.import_service = ImportService()

        # Load application state
        self.state = self.data_service.load()

        # Initialize state-dependent services
        self.account_service = AccountService(self.state)
        self.group_service = GroupService(self.state)

        # UI components
        self.toast = ToastNotification()

        # UI state
        self.selected_rows: set[int] = set()
        self.show_full_info = False
        self.sidebar_collapsed = False
        self.group_dialog = None
        self.deleted_group_backup = None  # For undo: {'group': Group, 'index': int, 'affected_accounts': list}
        self.undo_toast = None

        # Build UI
        self._init_ui()

        # Auto-refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_display)
        self.timer.start(Settings.TIMER_INTERVAL)

        logger.info("MainWindow initialized")

    def tr(self, key: str) -> str:
        """Get translated text for current language."""
        return get_translation(key, self.state.language)

    def _init_ui(self) -> None:
        """Initialize the user interface - Notion style."""
        self.setWindowTitle(self.tr('window_title'))
        self.resize(Settings.DEFAULT_WINDOW_WIDTH, Settings.DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(Settings.MIN_WINDOW_WIDTH, Settings.MIN_WINDOW_HEIGHT)

        # Set Notion-style background
        self.setStyleSheet("QMainWindow { background-color: #FFFFFF; }")

        # Main widget
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #FFFFFF;")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        main_widget.setLayout(main_layout)

        # Header
        self._create_header(main_layout)

        # Import section
        self._create_import_section(main_layout)

        # Content splitter (sidebar + table)
        self._create_content_area(main_layout)

        # Initialize data
        self._refresh_group_list()
        self._load_accounts_to_table()
        self._update_display()

    def _create_header(self, layout: QVBoxLayout) -> None:
        """Create the header with title and language button (Notion style)."""
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)

        # Simple title - Notion style
        self.title_label = QLabel(self.tr('window_title'))
        self.title_label.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: #37352F;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Language button - minimal style
        self.btn_language = QPushButton()
        self.btn_language.setFixedSize(80, 28)
        self.btn_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_language.setFont(QFont("Microsoft YaHei UI", 10))
        self.btn_language.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #E9E9E7;
                border-radius: 4px;
                padding: 0 10px;
                color: #787774;
            }
            QPushButton:hover {
                background-color: #F7F6F3;
            }
        """)
        self.btn_language.clicked.connect(self._switch_language)
        self._update_language_button()
        header_layout.addWidget(self.btn_language)

        layout.addWidget(header_container)

    def _create_import_section(self, layout: QVBoxLayout) -> None:
        """Create the import card section."""
        import_card = QFrame()
        import_card.setStyleSheet("""
            QFrame { background-color: #FBFBFA; border-radius: 4px; border: none; }
        """)
        import_card_layout = QVBoxLayout(import_card)
        import_card_layout.setContentsMargins(15, 15, 15, 15)
        import_card_layout.setSpacing(10)

        # Header
        import_header = QHBoxLayout()
        self.btn_toggle_import = QPushButton("▼ " + self.tr('collapse_import'))
        self.btn_toggle_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_import.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #37352F; font-weight: 600;
                border: none; text-align: left; padding: 0; font-size: 13px;
            }
            QPushButton:hover { color: #787774; }
        """)
        self.btn_toggle_import.clicked.connect(self._toggle_import_section)

        self.format_hint = QLabel(self.tr('format_hint'))
        self.format_hint.setStyleSheet("color: #6B7280; font-style: italic; font-size: 12px;")

        import_header.addWidget(self.btn_toggle_import)
        import_header.addStretch()
        import_header.addWidget(self.format_hint)
        import_card_layout.addLayout(import_header)

        # Content
        self.import_content = QWidget()
        self.import_content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        import_content_layout = QVBoxLayout(self.import_content)
        import_content_layout.setContentsMargins(0, 10, 0, 0)
        import_content_layout.setSpacing(15)

        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText(self.tr('paste_placeholder'))
        self.text_input.setFixedHeight(70)
        self.text_input.setStyleSheet("border: 1px solid #E9E9E7; border-radius: 4px; background-color: #FFFFFF; padding: 8px;")
        import_content_layout.addWidget(self.text_input)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_add_line = self._create_action_btn(
            self.tr('add_account'), "#10B981", "#059669",
            create_plus_icon(18, '#FFFFFF')
        )
        self.btn_add_line.clicked.connect(self._add_from_text_input)

        self.btn_import = self._create_action_btn(
            self.tr('import_file'), "#3B82F6", "#2563EB",
            create_import_icon(18, '#FFFFFF')
        )
        self.btn_import.clicked.connect(self._import_from_file)

        self.btn_clear = self._create_action_btn(
            self.tr('clear_all'), "#EF4444", "#DC2626",
            create_clear_icon(18, '#FFFFFF')
        )
        self.btn_clear.clicked.connect(self._clear_accounts)

        btn_row.addWidget(self.btn_add_line)
        btn_row.addWidget(self.btn_import)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_clear)

        import_content_layout.addLayout(btn_row)
        import_card_layout.addWidget(self.import_content)

        layout.addWidget(import_card)

    def _create_action_btn(self, text: str, color_base: str, color_hover: str, icon_pixmap=None) -> QPushButton:
        """Create a styled action button."""
        btn = QPushButton(text)
        btn.setFixedHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_pixmap:
            btn.setIcon(QIcon(icon_pixmap))
            btn.setIconSize(QSize(18, 18))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_base}; color: white; font-weight: 600;
                border: none; border-radius: 8px; padding: 0 16px;
            }}
            QPushButton:hover {{ background-color: {color_hover}; }}
        """)
        return btn

    def _create_content_area(self, layout: QVBoxLayout) -> None:
        """Create the main content area with sidebar and table."""
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setHandleWidth(1)
        self.content_splitter.setChildrenCollapsible(False)

        # Sidebar
        self._create_sidebar()

        # Table
        self._create_table_area()

        self.content_splitter.setStretchFactor(0, 0)
        self.content_splitter.setStretchFactor(1, 1)
        self.content_splitter.setSizes([180, 900])

        layout.addWidget(self.content_splitter, 1)

    def _create_sidebar(self) -> None:
        """Create the sidebar with group list."""
        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 15, 0)
        sidebar_layout.setSpacing(10)

        # Header
        sidebar_header = QHBoxLayout()
        self.group_label = QLabel(self.tr('groups'))
        self.group_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.group_label.setStyleSheet("color: #5F6368;")
        sidebar_header.addWidget(self.group_label)
        sidebar_header.addStretch()

        # Add group button
        self.btn_add_group = QToolButton()
        self.btn_add_group.setFixedSize(24, 24)
        self.btn_add_group.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_group.setToolTip(self.tr('add_group'))
        self.btn_add_group.setIcon(QIcon(create_plus_icon(16, '#787774')))
        self.btn_add_group.setIconSize(QSize(16, 16))
        self.btn_add_group.setStyleSheet("""
            QToolButton { background: transparent; border: none; }
            QToolButton:hover { background-color: #EFEFEF; border-radius: 4px; }
        """)
        self.btn_add_group.clicked.connect(lambda: self._show_manage_groups(open_add=True))
        sidebar_header.addWidget(self.btn_add_group)

        # Collapse button
        self.btn_collapse_sidebar = QToolButton()
        self.btn_collapse_sidebar.setFixedSize(24, 24)
        self.btn_collapse_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse_sidebar.setToolTip(self.tr('collapse_sidebar'))
        self.btn_collapse_sidebar.setIcon(QIcon(create_arrow_icon('left', 16, '#787774')))
        self.btn_collapse_sidebar.setIconSize(QSize(16, 16))
        self.btn_collapse_sidebar.setStyleSheet("""
            QToolButton { background: transparent; border: none; }
            QToolButton:hover { background-color: #EFEFEF; border-radius: 4px; }
        """)
        self.btn_collapse_sidebar.clicked.connect(self._toggle_sidebar)
        sidebar_header.addWidget(self.btn_collapse_sidebar)

        sidebar_layout.addLayout(sidebar_header)

        # Group list - Notion style
        self.group_list = QListWidget()
        self.group_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.group_list.setFont(QFont("Microsoft YaHei UI", 9))
        self.group_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item {
                padding: 7px 10px; margin-bottom: 1px; border-radius: 4px;
                color: #37352F;
            }
            QListWidget::item:hover { background-color: #EFEFEF; }
            QListWidget::item:selected { background-color: #E9E9E7; color: #37352F; border: none; }
        """)
        self.group_list.itemClicked.connect(self._on_group_selected)
        sidebar_layout.addWidget(self.group_list)

        self.content_splitter.addWidget(sidebar_container)

    def _create_table_area(self) -> None:
        """Create the table container with toolbar."""
        table_container = QFrame()
        table_container.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 4px; border: none; }
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        # Toolbar
        self._create_toolbar(table_layout)

        # Table
        self._create_table(table_layout)

        # Footer
        self._create_footer(table_layout)

        self.content_splitter.addWidget(table_container)

    def _create_toolbar(self, layout: QVBoxLayout) -> None:
        """Create the toolbar above the table."""
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: transparent; border-bottom: 1px solid #E9E9E7;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)

        # Toggle info button
        self.btn_toggle_info = QPushButton(self.tr('show_full'))
        self.btn_toggle_info.setIcon(QIcon(create_lock_icon(False, 16)))
        self.btn_toggle_info.setIconSize(QSize(16, 16))
        self.btn_toggle_info.setFixedHeight(28)
        self.btn_toggle_info.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_toggle_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_info.setStyleSheet("""
            QPushButton { background-color: transparent; color: #5F6368;
                         border: 1px solid #E0E0E0; border-radius: 4px; padding: 0 10px; }
            QPushButton:hover { background-color: #F7F6F3; border-color: #D0D0D0; }
        """)
        self.btn_toggle_info.clicked.connect(self._toggle_info_display)
        toolbar_layout.addWidget(self.btn_toggle_info)

        toolbar_layout.addSpacing(15)

        # Countdown
        countdown_container = QWidget()
        countdown_layout = QHBoxLayout(countdown_container)
        countdown_layout.setContentsMargins(0, 0, 0, 0)
        countdown_layout.setSpacing(4)

        self.clock_icon_label = QLabel()
        self.clock_icon_label.setPixmap(create_clock_icon(14, '#10B981'))
        countdown_layout.addWidget(self.clock_icon_label)

        self.countdown_label = QLabel(self.tr('code_expires') + " 30s")
        self.countdown_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.countdown_label.setStyleSheet("color: #787774; font-weight: 500;")
        countdown_layout.addWidget(self.countdown_label)

        toolbar_layout.addWidget(countdown_container)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(30)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #E9E9E7; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #37352F; border-radius: 3px; }
        """)
        toolbar_layout.addWidget(self.progress_bar, 1)

        # Batch toolbar
        self.batch_toolbar = QWidget()
        batch_layout = QHBoxLayout(self.batch_toolbar)
        batch_layout.setContentsMargins(15, 0, 0, 0)
        batch_layout.setSpacing(8)

        self.selected_label = QLabel("")
        self.selected_label.setStyleSheet("color: #6366F1; font-weight: bold;")
        batch_layout.addWidget(self.selected_label)

        self.btn_batch_add_group = self._create_mini_btn(
            self.tr('batch_add_group'), "#10B981",
            self._batch_add_to_group, create_folder_icon(14, '#FFFFFF')
        )
        batch_layout.addWidget(self.btn_batch_add_group)

        self.btn_batch_remove_group = self._create_mini_btn(
            self.tr('batch_remove_group'), "#F59E0B",
            self._batch_remove_from_group, create_minus_icon(14, '#FFFFFF')
        )
        batch_layout.addWidget(self.btn_batch_remove_group)

        self.btn_batch_delete = self._create_mini_btn(
            self.tr('batch_delete'), "#EF4444",
            self._batch_delete, create_trash_icon(14, '#FFFFFF')
        )
        batch_layout.addWidget(self.btn_batch_delete)

        self.batch_toolbar.hide()
        toolbar_layout.addWidget(self.batch_toolbar)

        layout.addWidget(toolbar)

    def _create_mini_btn(self, text: str, color: str, func, icon_pixmap=None) -> QPushButton:
        """Create a mini button for the toolbar."""
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_pixmap:
            btn.setIcon(QIcon(icon_pixmap))
            btn.setIconSize(QSize(14, 14))

        hover_colors = {
            "#10B981": "#059669",
            "#F59E0B": "#D97706",
            "#EF4444": "#DC2626",
        }
        hover_color = hover_colors.get(color, color)

        btn.setStyleSheet(f"""
            QPushButton {{ background-color: {color}; color: white; font-size: 12px;
                          font-weight: 600; border: none; border-radius: 6px; padding: 0 10px; }}
            QPushButton:hover {{ background-color: {hover_color}; }}
        """)
        btn.clicked.connect(func)
        return btn

    def _create_table(self, layout: QVBoxLayout) -> None:
        """Create the accounts table."""
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            '', self.tr('id'), self.tr('email'), self.tr('password'),
            self.tr('secondary_email'), self.tr('2fa_key'), self.tr('2fa_code'),
            self.tr('import_time'), self.tr('groups'), self.tr('notes')
        ])

        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)

        self.table.setStyleSheet("""
            QTableWidget { background-color: #FFFFFF; gridline-color: transparent; }
            QHeaderView::section {
                background-color: #FAFAFA; color: #5F6368; padding: 10px 8px;
                border: none; border-bottom: 1px solid #E0E0E0;
                font-size: 12px;
            }
        """)

        # Column configuration
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Column widths
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 45)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 40)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 120)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 100)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 80)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 115)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 80)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

        # Create header checkbox for select all (same as main.py)
        self.header_checkbox_widget = QWidget(self.table.horizontalHeader())
        self.header_checkbox_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        header_checkbox_layout = QHBoxLayout(self.header_checkbox_widget)
        header_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        header_checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_checkbox = QCheckBox()
        self.header_checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid #CBD5E1;
                border-radius: 4px;
                background-color: #FFFFFF;
            }}
            QCheckBox::indicator:hover {{
                border-color: #3B82F6;
                background-color: #EFF6FF;
            }}
            QCheckBox::indicator:checked {{
                background-color: #3B82F6;
                border-color: #3B82F6;
                image: url({CHECK_SVG_PATH});
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: #2563EB;
                border-color: #2563EB;
            }}
        """)
        header_checkbox_layout.addWidget(self.header_checkbox)
        self.header_checkbox.stateChanged.connect(self._on_header_checkbox_changed)
        self._update_header_checkbox_position()

    def _create_footer(self, layout: QVBoxLayout) -> None:
        """Create the footer with status info."""
        footer = QWidget()
        footer.setStyleSheet("background-color: transparent; border-top: 1px solid #F3F4F6;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 8, 15, 8)

        self.count_label = QLabel(f"{self.tr('accounts')}: 0")
        self.count_label.setStyleSheet("color: #6B7280; font-weight: 600; font-size: 12px;")
        footer_layout.addWidget(self.count_label)

        footer_layout.addSpacing(20)

        self.copy_hint_label = QLabel(self.tr('click_to_copy'))
        self.copy_hint_label.setStyleSheet("color: #9CA3AF; font-size: 12px; font-style: italic;")
        footer_layout.addWidget(self.copy_hint_label)

        footer_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        footer_layout.addWidget(self.status_label)

        layout.addWidget(footer)

    # ========== Event Handlers ==========

    def _switch_language(self) -> None:
        """Toggle between English and Chinese."""
        self.state.language = 'zh' if self.state.language == 'en' else 'en'
        self._update_ui_language()
        self._save_data()

    def _update_language_button(self) -> None:
        """Update language button text."""
        if self.state.language == 'en':
            self.btn_language.setText("EN → 中")
            self.btn_language.setToolTip("Click to switch to Chinese")
        else:
            self.btn_language.setText("中 → EN")
            self.btn_language.setToolTip("点击切换到英文")

    def _update_ui_language(self) -> None:
        """Update all UI elements with current language."""
        self.setWindowTitle(self.tr('window_title'))
        suffix = self.tr('window_title').replace('G-Account Manager', 'Account Manager').replace('谷歌账号管家', '账号管家')
        self.title_label.setText(" " + suffix)
        self.format_hint.setText(self.tr('format_hint'))
        self.btn_toggle_import.setText(
            "▼ " + self.tr('collapse_import') if self.import_content.isVisible()
            else "▶ " + self.tr('expand_import')
        )
        self.text_input.setPlaceholderText(self.tr('paste_placeholder'))
        self.btn_add_line.setText(self.tr('add_account'))
        self.btn_import.setText(self.tr('import_file'))
        self.btn_clear.setText(self.tr('clear_all'))
        self._update_language_button()
        self.btn_add_group.setToolTip(self.tr('add_group'))
        self.table.setHorizontalHeaderLabels([
            '', self.tr('id'), self.tr('email'), self.tr('password'),
            self.tr('secondary_email'), self.tr('2fa_key'), self.tr('2fa_code'),
            self.tr('import_time'), self.tr('groups'), self.tr('notes')
        ])
        self.count_label.setText(f"{self.tr('accounts')}: {self.table.rowCount()}")
        self.copy_hint_label.setText(self.tr('click_to_copy'))
        self.btn_batch_add_group.setText(self.tr('batch_add_group'))
        self.btn_batch_remove_group.setText(self.tr('batch_remove_group'))
        self.btn_batch_delete.setText(self.tr('batch_delete'))
        self.group_label.setText(self.tr('groups'))
        self._refresh_group_list()

    def _toggle_import_section(self) -> None:
        """Toggle import section visibility."""
        if self.import_content.isVisible():
            self.import_content.hide()
            self.btn_toggle_import.setText("▶ " + self.tr('expand_import'))
        else:
            self.import_content.show()
            self.btn_toggle_import.setText("▼ " + self.tr('collapse_import'))

    def _toggle_sidebar(self) -> None:
        """Toggle sidebar collapsed state."""
        self.sidebar_collapsed = not self.sidebar_collapsed

        if self.sidebar_collapsed:
            self.content_splitter.setSizes([36, 900])
            self.btn_collapse_sidebar.setIcon(QIcon(create_arrow_icon('right', 16, '#787774')))
            self.btn_collapse_sidebar.setToolTip(self.tr('expand_sidebar'))
            self.group_label.hide()
            self.btn_add_group.hide()
        else:
            self.content_splitter.setSizes([180, 900])
            self.btn_collapse_sidebar.setIcon(QIcon(create_arrow_icon('left', 16, '#787774')))
            self.btn_collapse_sidebar.setToolTip(self.tr('collapse_sidebar'))
            self.group_label.show()
            self.btn_add_group.show()

        self._refresh_group_list()

    def _toggle_info_display(self) -> None:
        """Toggle between masked and full info display."""
        self.show_full_info = not self.show_full_info
        if self.show_full_info:
            self.btn_toggle_info.setText(self.tr('hide_full'))
            self.btn_toggle_info.setIcon(QIcon(create_lock_icon(True, 16)))
        else:
            self.btn_toggle_info.setText(self.tr('show_full'))
            self.btn_toggle_info.setIcon(QIcon(create_lock_icon(False, 16)))
        self._refresh_table_display()

    # ========== Data Operations ==========

    def _save_data(self) -> None:
        """Save current state to file."""
        self.data_service.save(self.state)

    def _add_from_text_input(self) -> None:
        """Add accounts from text input."""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, self.tr('empty_input'), self.tr('empty_input_msg'))
            return

        accounts = self.import_service.parse_text(text)
        self._process_import(accounts)
        self.text_input.clear()

    def _import_from_file(self) -> None:
        """Import accounts from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr('import_file'), "",
            "Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return

        try:
            accounts = self.import_service.parse_file(file_path)
            self._process_import(accounts)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import: {e}")

    def _process_import(self, new_accounts: list[Account]) -> None:
        """Process imported accounts, handling duplicates."""
        if not new_accounts:
            return

        # Create backup
        self.backup_service.create_backup()

        # Find duplicates
        duplicates = self.account_service.find_duplicates(new_accounts)

        # Handle conflicts
        replace_indices = set()
        if duplicates:
            # Convert to dict format for dialog
            conflicts = [
                (new_acc.to_dict(), existing.to_dict(), idx)
                for new_acc, existing, idx in duplicates
            ]
            dialog = DuplicateConflictDialog(conflicts, self.state.language, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                choices = dialog.get_choices()
                for i, choice in choices.items():
                    if choice == 'replace':
                        replace_indices.add(i)

        # Process accounts
        added = 0
        replaced = 0
        duplicate_emails = {d[0].email_normalized for d in duplicates}

        for account in new_accounts:
            if account.email_normalized in duplicate_emails:
                # Check if we should replace
                for i, (new_acc, existing, idx) in enumerate(duplicates):
                    if new_acc.email_normalized == account.email_normalized:
                        if i in replace_indices:
                            # Replace existing
                            account.id = existing.id
                            self.state.accounts[idx] = account
                            replaced += 1
                        break
            else:
                # Add new account
                self.account_service.add(account)
                added += 1

        self._save_data()
        self._load_accounts_to_table()
        self._refresh_group_list()

        # Show result
        msg_parts = []
        if added > 0:
            msg_parts.append(self.tr('added_new').format(added))
        if replaced > 0:
            msg_parts.append(self.tr('replaced_existing').format(replaced))
        if msg_parts:
            self.toast.show_message(", ".join(msg_parts), self)

    def _clear_accounts(self) -> None:
        """Clear all accounts (move to trash)."""
        if not self.state.accounts:
            return

        count = len(self.state.accounts)
        reply = QMessageBox.question(
            self, self.tr('confirm_clear'),
            self.tr('confirm_clear_msg').format(count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.backup_service.create_backup()
            self.account_service.clear_all(move_to_trash=True)
            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()

    # ========== Table Operations ==========

    def _load_accounts_to_table(self) -> None:
        """Load all accounts into the table."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for i, account in enumerate(self.state.accounts):
            self._add_account_row(account, i)

        self.table.blockSignals(False)
        self._calculate_column_widths()
        self._filter_table()

    def _add_account_row(self, account: Account, index: int) -> None:
        """Add a single account row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Checkbox
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = QCheckBox()
        checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid #CBD5E1;
                border-radius: 4px;
                background-color: #FFFFFF;
            }}
            QCheckBox::indicator:hover {{
                border-color: #3B82F6;
                background-color: #EFF6FF;
            }}
            QCheckBox::indicator:checked {{
                background-color: #3B82F6;
                border-color: #3B82F6;
                image: url({CHECK_SVG_PATH});
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: #2563EB;
                border-color: #2563EB;
            }}
        """)
        checkbox.clicked.connect(lambda checked, r=row: self._on_checkbox_clicked(r, checked))
        checkbox_layout.addWidget(checkbox)
        self.table.setCellWidget(row, 0, checkbox_widget)

        # ID
        id_item = QTableWidgetItem(str(account.id or ""))
        id_item.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        id_item.setData(Qt.ItemDataRole.UserRole + 1, index)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, id_item)

        # Email (not editable)
        email_display = account.email if self.show_full_info else self._mask_text(account.email, 4)
        email_item = QTableWidgetItem(email_display)
        email_item.setData(Qt.ItemDataRole.UserRole, account.email)
        email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 2, email_item)

        # Password (not editable)
        pwd_display = account.password if self.show_full_info else self._mask_text(account.password, 2)
        pwd_item = QTableWidgetItem(pwd_display)
        pwd_item.setData(Qt.ItemDataRole.UserRole, account.password)
        pwd_item.setFlags(pwd_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 3, pwd_item)

        # Backup email (not editable)
        backup_display = account.backup if self.show_full_info else self._mask_text(account.backup, 4)
        backup_item = QTableWidgetItem(backup_display)
        backup_item.setData(Qt.ItemDataRole.UserRole, account.backup)
        backup_item.setFlags(backup_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 4, backup_item)

        # 2FA Key (not editable)
        if self.show_full_info:
            secret_display = account.secret if account.secret else "(none)"
        else:
            if account.secret:
                s = account.secret
                secret_display = s[:6] + "..." + s[-4:] if len(s) > 10 else s
            else:
                secret_display = "(none)"
        secret_item = QTableWidgetItem(secret_display)
        secret_item.setData(Qt.ItemDataRole.UserRole, account.secret)
        secret_item.setFlags(secret_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 5, secret_item)

        # 2FA Code
        if account.secret:
            code = self.totp_service.generate_code_safe(account.secret)
            if code:
                code_item = QTableWidgetItem(code)
                code_item.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                code_item.setForeground(QColor("#2563EB"))
            else:
                code_item = QTableWidgetItem("ERROR")
                code_item.setForeground(QColor("#EF4444"))
        else:
            code_item = QTableWidgetItem("-")
            code_item.setForeground(QColor("#9CA3AF"))
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 6, code_item)

        # Import time (not editable)
        time_item = QTableWidgetItem(account.import_time)
        time_item.setForeground(QColor("#6B7280"))
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 7, time_item)

        # Groups (as tags widget)
        self._update_tags_cell(row, index)

        # Notes (editable)
        notes_item = QTableWidgetItem(account.notes)
        notes_item.setForeground(QColor("#6B7280"))
        notes_item.setFlags(notes_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 9, notes_item)

    def _mask_text(self, text: str, visible_chars: int = 2) -> str:
        """Mask text for privacy, showing first visible_chars characters."""
        if not text:
            return ""
        if len(text) <= visible_chars:
            return "*" * len(text)
        return text[:visible_chars] + "*" * (len(text) - visible_chars)

    def _update_tags_cell(self, row: int, account_idx: int) -> None:
        """Update the tags cell for a row."""
        if account_idx >= len(self.state.accounts):
            return

        account = self.state.accounts[account_idx]
        tags_widget = QWidget()
        tags_widget.setStyleSheet("background-color: #FFFFFF;")
        tags_layout = QHBoxLayout(tags_widget)
        tags_layout.setContentsMargins(4, 0, 4, 0)
        tags_layout.setSpacing(2)
        tags_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tooltip_parts = []
        for group_name in account.groups:
            group = self.state.get_group_by_name(group_name)
            if group:
                color_hex = group.color_hex
                pastel_fill = get_pastel_color(color_hex)
                dot_label = QLabel()
                dot_label.setFixedSize(14, 14)
                dot_label.setStyleSheet(f"background-color: {pastel_fill}; border: 1px solid #9CA3AF; border-radius: 3px;")
                tags_layout.addWidget(dot_label)
                tooltip_parts.append(f"■ {group_name}")

        if tooltip_parts:
            tags_widget.setToolTip('\n'.join(tooltip_parts))
        self.table.setCellWidget(row, 8, tags_widget)

    def _calculate_column_widths(self) -> None:
        """Calculate email and password column widths."""
        if not self.state.accounts:
            self.table.setColumnWidth(2, 200)
            self.table.setColumnWidth(3, 120)
            return

        fm = QFontMetrics(self.table.font())
        max_email = max(fm.horizontalAdvance(acc.email) for acc in self.state.accounts)
        max_pwd = max(fm.horizontalAdvance(acc.password) for acc in self.state.accounts)

        self.table.setColumnWidth(2, max(max_email + 25, 150))
        self.table.setColumnWidth(3, max(max_pwd + 25, 100))

    def _refresh_table_display(self) -> None:
        """Refresh table display (for mask/unmask toggle)."""
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 1)
            if not id_item:
                continue
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is None or account_idx >= len(self.state.accounts):
                continue
            account = self.state.accounts[account_idx]

            # Update display
            email_item = self.table.item(row, 2)
            if email_item:
                display = account.email if self.show_full_info else self._mask_text(account.email, 4)
                email_item.setText(display)

            pwd_item = self.table.item(row, 3)
            if pwd_item:
                display = account.password if self.show_full_info else self._mask_text(account.password)
                pwd_item.setText(display)

            backup_item = self.table.item(row, 4)
            if backup_item:
                display = account.backup if self.show_full_info else self._mask_text(account.backup)
                backup_item.setText(display)

            secret_item = self.table.item(row, 5)
            if secret_item:
                display = account.secret if self.show_full_info else self._mask_text(account.secret)
                secret_item.setText(display)

        self.table.blockSignals(False)

    def _filter_table(self) -> None:
        """Filter table based on selected group."""
        current_filter = self.state.current_filter
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 1)
            if not id_item:
                continue
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is None or account_idx >= len(self.state.accounts):
                continue
            account = self.state.accounts[account_idx]

            show = False
            if current_filter == 'all':
                show = True
            elif current_filter == 'ungrouped':
                show = account.is_ungrouped
            elif current_filter == 'trash':
                show = False
            else:
                show = account.is_in_group(current_filter)

            self.table.setRowHidden(row, not show)

        visible = sum(1 for row in range(self.table.rowCount()) if not self.table.isRowHidden(row))
        self.count_label.setText(f"{self.tr('accounts')}: {visible}")

    def _refresh_group_list(self) -> None:
        """Refresh the sidebar group list."""
        self.group_list.clear()

        all_count = len(self.state.accounts)
        ungrouped_count = len(self.state.get_ungrouped_accounts())
        trash_count = len(self.state.trash)
        collapsed = self.sidebar_collapsed

        # All accounts
        all_item = QListWidgetItem() if collapsed else QListWidgetItem(f"  {self.tr('all_accounts')} ({all_count})")
        all_item.setIcon(QIcon(create_list_icon(16)))
        all_item.setData(Qt.ItemDataRole.UserRole, 'all')
        self.group_list.addItem(all_item)

        # Ungrouped
        ungrouped_item = QListWidgetItem() if collapsed else QListWidgetItem(f"  {self.tr('ungrouped')} ({ungrouped_count})")
        ungrouped_item.setIcon(QIcon(create_folder_icon(16)))
        ungrouped_item.setData(Qt.ItemDataRole.UserRole, 'ungrouped')
        self.group_list.addItem(ungrouped_item)

        # Custom groups
        for group in self.state.groups:
            count = len(self.state.get_accounts_in_group(group.name))
            item = QListWidgetItem() if collapsed else QListWidgetItem(f"  {group.name} ({count})")
            item.setIcon(QIcon(create_dot_icon(group.color_hex, 10)))
            item.setData(Qt.ItemDataRole.UserRole, group.name)
            self.group_list.addItem(item)

        # Trash
        trash_item = QListWidgetItem() if collapsed else QListWidgetItem(f"  {self.tr('trash_bin')} ({trash_count})")
        trash_item.setIcon(QIcon(create_trash_icon(16)))
        trash_item.setData(Qt.ItemDataRole.UserRole, 'trash')
        self.group_list.addItem(trash_item)

        # Select current filter
        for i in range(self.group_list.count()):
            item = self.group_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self.state.current_filter:
                self.group_list.setCurrentItem(item)
                break

    def _on_group_selected(self, item: QListWidgetItem) -> None:
        """Handle group selection."""
        selected = item.data(Qt.ItemDataRole.UserRole)
        if selected == 'trash':
            self._show_trash()
            # Re-select current filter
            for i in range(self.group_list.count()):
                it = self.group_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self.state.current_filter:
                    self.group_list.setCurrentItem(it)
                    break
        else:
            self.state.current_filter = selected
            self._filter_table()

    def _update_display(self) -> None:
        """Update countdown and 2FA codes."""
        remaining = self.totp_service.get_remaining_seconds()
        self.countdown_label.setText(f"{self.tr('code_expires')} {remaining}s")
        self.progress_bar.setValue(remaining)

        # Update color based on time
        if remaining <= 5:
            color = "#EF4444"  # Red
        elif remaining <= 10:
            color = "#F59E0B"  # Orange
        else:
            color = "#10B981"  # Green

        self.countdown_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #E5E7EB; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}
        """)
        self.clock_icon_label.setPixmap(create_clock_icon(14, color))

        # Refresh codes when needed
        if remaining >= 29:
            self._refresh_codes()

    def _refresh_codes(self) -> None:
        """Refresh all 2FA codes in the table."""
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 1)
            if not id_item:
                continue
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is None or account_idx >= len(self.state.accounts):
                continue
            account = self.state.accounts[account_idx]

            code_item = self.table.item(row, 6)
            if code_item and account.secret:
                code = self.totp_service.generate_code_safe(account.secret) or ""
                code_item.setText(code)
        self.table.blockSignals(False)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Handle cell click to copy content, or edit notes/tags."""
        # Don't copy: Checkbox(0), ID(1), Import Time(7)
        if col in [0, 1, 7]:
            return

        # Show tag popup (column 8)
        if col == 8:
            self._show_tag_popup(row)
            return

        # Edit notes directly in cell on click (column 9)
        if col == 9:
            item = self.table.item(row, col)
            if item:
                self.table.editItem(item)
            return

        item = self.table.item(row, col)
        if item:
            # Get original (unmasked) value from UserRole for columns 2-5
            if col in [2, 3, 4, 5]:
                text = item.data(Qt.ItemDataRole.UserRole)
            else:
                text = item.text()

            if text and text not in ["(none)", "-", "ERROR"]:
                QApplication.clipboard().setText(str(text))

                # Visual feedback - highlight the copied cell yellow
                original_bg = item.background()
                item.setBackground(QColor("#FEF08A"))  # Yellow highlight

                # Reset background after 500ms
                QTimer.singleShot(500, lambda: item.setBackground(original_bg))

                # Show which column was copied
                column_keys = ['', 'id', 'email', 'password', 'secondary_email', '2fa_key', '2fa_code', 'import_time', 'tags', 'notes', '']
                col_name = self.tr(column_keys[col]) if col < len(column_keys) else "Text"
                self.toast.show_message(f"{self.tr('copied')}: {col_name}", self, 1000)

    def _show_tag_popup(self, row: int) -> None:
        """Show a popup to manage tags for an account."""
        id_item = self.table.item(row, 1)
        if not id_item:
            return

        account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
        if account_idx is None or account_idx >= len(self.state.accounts):
            return

        account = self.state.accounts[account_idx]
        account_groups = account.groups

        if not account_groups:
            # No groups, show option to add
            self._show_add_group_popup(row, account_idx)
            return

        # Create popup menu at cursor position - Notion style
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E9E9E7;
                border-radius: 6px;
                padding: 6px;
            }
            QMenu::item { padding: 8px 16px 8px 10px; border-radius: 4px; color: #37352F; }
            QMenu::item:selected { background-color: #EFEFEF; }
            QMenu::separator { height: 1px; background: #E9E9E7; margin: 4px 8px; }
        """)

        # Current groups with remove option
        for group_name in account_groups:
            for g in self.state.groups:
                if g.name == group_name:
                    action = menu.addAction(f"✕  {group_name}")
                    action.setIcon(QIcon(create_dot_icon(get_color_hex(g.color), 10)))
                    action.triggered.connect(lambda checked, gn=group_name, r=row: self._remove_row_from_group(r, gn))
                    break

        menu.addSeparator()

        # Add to other groups
        available_groups = [g for g in self.state.groups if g.name not in account_groups]
        if available_groups:
            for group in available_groups:
                action = menu.addAction(f"+  {group.name}")
                action.setIcon(QIcon(create_dot_icon(get_color_hex(group.color), 10)))
                action.triggered.connect(lambda checked, gn=group.name, r=row: self._add_row_to_group(r, gn))

        menu.exec(self.table.viewport().mapToGlobal(self.table.visualRect(self.table.model().index(row, 8)).bottomLeft()))

    def _show_add_group_popup(self, row: int, account_idx: int) -> None:
        """Show popup to add account to a group when it has no groups."""
        if not self.state.groups:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E9E9E7;
                border-radius: 6px;
                padding: 6px;
            }
            QMenu::item { padding: 8px 16px 8px 10px; border-radius: 4px; color: #37352F; }
            QMenu::item:selected { background-color: #EFEFEF; }
        """)

        for group in self.state.groups:
            action = menu.addAction(group.name)
            action.setIcon(QIcon(create_dot_icon(get_color_hex(group.color), 10)))
            action.triggered.connect(lambda checked, gn=group.name, r=row: self._add_row_to_group(r, gn))

        menu.exec(self.table.viewport().mapToGlobal(self.table.visualRect(self.table.model().index(row, 8)).bottomLeft()))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle item edit - only notes column (9) is editable."""
        if item is None:
            return

        col = item.column()
        row = item.row()

        # Only handle notes column (9)
        if col != 9:
            return

        id_item = self.table.item(row, 1)
        if not id_item:
            return
        account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
        if account_idx is None or account_idx >= len(self.state.accounts):
            return

        account = self.state.accounts[account_idx]
        new_value = item.text()

        if account.notes != new_value:
            account.notes = new_value
            self._save_data()

    def _on_checkbox_clicked(self, row: int, checked: bool) -> None:
        """Handle checkbox click."""
        if checked:
            self.selected_rows.add(row)
            self._highlight_row(row, True)
        else:
            self.selected_rows.discard(row)
            self._highlight_row(row, False)
        self._update_batch_toolbar()
        self._update_select_all_button()

    def _on_checkbox_changed(self, row: int, state: int) -> None:
        """Handle checkbox state change (legacy fallback)."""
        if state == Qt.CheckState.Checked.value:
            self.selected_rows.add(row)
            self._highlight_row(row, True)
        else:
            self.selected_rows.discard(row)
            self._highlight_row(row, False)
        self._update_batch_toolbar()
        self._update_select_all_button()

    def _on_header_checkbox_changed(self, state: int) -> None:
        """Handle header checkbox state change for select all."""
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
                    self.selected_rows.add(row)
                    self._highlight_row(row, True)
            self.table.viewport().update()
            self._update_batch_toolbar()
        else:
            self._clear_selection()

    def _update_select_all_button(self) -> None:
        """Update header checkbox based on current selection."""
        visible_rows = [row for row in range(self.table.rowCount()) if not self.table.isRowHidden(row)]
        all_selected = len(self.selected_rows) >= len(visible_rows) and len(visible_rows) > 0

        self.header_checkbox.blockSignals(True)
        self.header_checkbox.setChecked(all_selected)
        self.header_checkbox.blockSignals(False)

    def _update_header_checkbox_position(self) -> None:
        """Position the header checkbox to fill first column header."""
        header = self.table.horizontalHeader()
        col_x = header.sectionViewportPosition(0)
        col_width = header.sectionSize(0)
        header_height = header.height()
        self.header_checkbox_widget.setGeometry(col_x, 0, col_width, header_height)

    def resizeEvent(self, event) -> None:
        """Handle resize to reposition header checkbox."""
        super().resizeEvent(event)
        if hasattr(self, 'header_checkbox_widget'):
            self._update_header_checkbox_position()

    def showEvent(self, event) -> None:
        """Handle show event to position header checkbox."""
        super().showEvent(event)
        if hasattr(self, 'header_checkbox_widget'):
            self._update_header_checkbox_position()

    def _highlight_row(self, row: int, selected: bool) -> None:
        """Highlight or unhighlight a row."""
        bg_color = QColor("#E0E7FF") if selected else QColor("#FFFFFF")

        for col in [0, 8]:
            widget = self.table.cellWidget(row, col)
            if widget:
                widget.setStyleSheet(f"background-color: {bg_color.name()};")

        for col in [1, 2, 3, 4, 5, 6, 7, 9]:
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg_color)

    def _update_batch_toolbar(self) -> None:
        """Update batch toolbar visibility."""
        if self.selected_rows:
            self.selected_label.setText(self.tr('selected_count').format(len(self.selected_rows)))
            self.batch_toolbar.show()
        else:
            self.batch_toolbar.hide()

    def _show_context_menu(self, pos) -> None:
        """Show context menu for table."""
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #FFFFFF; border: 1px solid #E9E9E7; border-radius: 6px; padding: 6px; }
            QMenu::item { padding: 8px 12px; border-radius: 4px; color: #37352F; }
            QMenu::item:selected { background-color: #EFEFEF; }
            QMenu::separator { height: 1px; background: #E9E9E7; margin: 4px 8px; }
        """)

        # Add to group submenu
        if self.state.groups:
            add_menu = menu.addMenu(self.tr('add_to_group'))
            add_menu.setIcon(QIcon(create_folder_icon(14)))
            for group in self.state.groups:
                action = add_menu.addAction(group.name)
                action.setIcon(QIcon(create_dot_icon(get_color_hex(group.color), 10)))
                action.triggered.connect(lambda checked, g=group.name, r=row: self._add_row_to_group(r, g))

        # Remove from group submenu
        id_item = self.table.item(row, 1)
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.state.accounts):
                account_groups = self.state.accounts[account_idx].groups
                if account_groups:
                    remove_menu = menu.addMenu(self.tr('remove_from_group'))
                    remove_menu.setIcon(QIcon(create_minus_icon(14, '#6B7280')))
                    for group_name in account_groups:
                        for g in self.state.groups:
                            if g.name == group_name:
                                action = remove_menu.addAction(g.name)
                                action.setIcon(QIcon(create_dot_icon(get_color_hex(g.color), 10)))
                                action.triggered.connect(lambda checked, gn=group_name, r=row: self._remove_row_from_group(r, gn))
                                break

        menu.addSeparator()

        # Edit notes action
        notes_action = menu.addAction(self.tr('edit_notes'))
        notes_action.setIcon(QIcon(create_edit_icon(14, '#6B7280')))
        notes_action.triggered.connect(lambda: self._edit_notes(row))

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction(self.tr('delete'))
        delete_action.setIcon(QIcon(create_trash_icon(14, '#6B7280')))
        delete_action.triggered.connect(lambda: self._delete_row(row))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _add_row_to_group(self, row: int, group_name: str) -> None:
        """Add a single row to a group."""
        id_item = self.table.item(row, 1)
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.state.accounts):
                self.state.accounts[account_idx].add_to_group(group_name)
                self._update_tags_cell(row, account_idx)
                self._save_data()
                self._refresh_group_list()

    def _remove_row_from_group(self, row: int, group_name: str) -> None:
        """Remove a single row from a group."""
        id_item = self.table.item(row, 1)
        if id_item:
            account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
            if account_idx is not None and account_idx < len(self.state.accounts):
                self.state.accounts[account_idx].remove_from_group(group_name)
                self._update_tags_cell(row, account_idx)
                self._save_data()
                self._refresh_group_list()

    def _edit_notes(self, row: int) -> None:
        """Edit notes for a row."""
        notes_item = self.table.item(row, 9)
        if notes_item:
            self.table.editItem(notes_item)

    def _delete_row(self, row: int) -> None:
        """Delete a single row."""
        id_item = self.table.item(row, 1)
        if not id_item:
            return
        account_idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
        if account_idx is None or account_idx >= len(self.state.accounts):
            return

        account = self.state.accounts[account_idx]
        reply = QMessageBox.question(
            self, self.tr('confirm_delete'),
            self.tr('confirm_delete_msg').format(account.email),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.account_service.delete(account.id, move_to_trash=True)
            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()

    # ========== Batch Operations ==========

    def _batch_add_to_group(self) -> None:
        """Add selected accounts to a group."""
        if not self.selected_rows or not self.state.groups:
            return

        groups = [g.name for g in self.state.groups]
        choice, ok = QInputDialog.getItem(
            self, self.tr('batch_add_group'),
            self.tr('add_to_group'), groups, 0, False
        )
        if ok and choice:
            for row in self.selected_rows:
                id_item = self.table.item(row, 1)
                if id_item:
                    idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                    if idx is not None and idx < len(self.state.accounts):
                        self.state.accounts[idx].add_to_group(choice)
                        self._update_tags_cell(row, idx)

            self._save_data()
            self._refresh_group_list()
            self._clear_selection()

    def _batch_remove_from_group(self) -> None:
        """Remove selected accounts from a group."""
        if not self.selected_rows:
            return

        # Find groups used by selected accounts
        groups_used = set()
        for row in self.selected_rows:
            id_item = self.table.item(row, 1)
            if id_item:
                idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                if idx is not None and idx < len(self.state.accounts):
                    groups_used.update(self.state.accounts[idx].groups)

        if not groups_used:
            return

        choice, ok = QInputDialog.getItem(
            self, self.tr('batch_remove_group'),
            self.tr('remove_from_group'), list(groups_used), 0, False
        )
        if ok and choice:
            for row in self.selected_rows:
                id_item = self.table.item(row, 1)
                if id_item:
                    idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                    if idx is not None and idx < len(self.state.accounts):
                        self.state.accounts[idx].remove_from_group(choice)
                        self._update_tags_cell(row, idx)

            self._save_data()
            self._refresh_group_list()
            self._clear_selection()

    def _batch_delete(self) -> None:
        """Delete selected accounts."""
        if not self.selected_rows:
            return

        count = len(self.selected_rows)
        reply = QMessageBox.question(
            self, self.tr('confirm_delete'),
            self.tr('confirm_clear_msg').format(count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Get account IDs to delete
            ids_to_delete = []
            for row in sorted(self.selected_rows, reverse=True):
                id_item = self.table.item(row, 1)
                if id_item:
                    idx = id_item.data(Qt.ItemDataRole.UserRole + 1)
                    if idx is not None and idx < len(self.state.accounts):
                        ids_to_delete.append(self.state.accounts[idx].id)

            for acc_id in ids_to_delete:
                self.account_service.delete(acc_id, move_to_trash=True)

            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()
            self._clear_selection()

    def _clear_selection(self) -> None:
        """Clear all selected rows."""
        for row in list(self.selected_rows):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
            self._highlight_row(row, False)
        self.selected_rows.clear()
        self._update_batch_toolbar()

    # ========== Group Management ==========

    def _show_manage_groups(self, open_add: bool = False) -> None:
        """Show group management dialog with full functionality."""
        # If dialog already open, bring to front
        if self.group_dialog is not None:
            self.group_dialog.raise_()
            self.group_dialog.activateWindow()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr('manage_groups'))
        dialog.resize(420, 450)
        dialog.setStyleSheet("QDialog { background-color: white; }")

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        dialog.setLayout(layout)

        # Title row with add button
        title_row = QHBoxLayout()
        title = QLabel(self.tr('manage_groups'))
        title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #37352F;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Add new group button
        btn_show_add = QToolButton()
        btn_show_add.setFixedSize(32, 32)
        btn_show_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_show_add.setIcon(QIcon(create_plus_icon(18)))
        btn_show_add.setIconSize(QSize(18, 18))
        btn_show_add.setStyleSheet("""
            QToolButton { background: transparent; border: none; }
            QToolButton:hover { background-color: #F3F4F6; border-radius: 8px; }
        """)
        title_row.addWidget(btn_show_add)
        layout.addLayout(title_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #E9E9E7;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # Add new group section - Notion style
        add_section = QFrame()
        add_section.setStyleSheet("""
            QFrame {
                background-color: #FBFBFA;
                border: 1px solid #E9E9E7;
                border-radius: 8px;
            }
        """)

        add_layout = QHBoxLayout(add_section)
        add_layout.setContentsMargins(12, 12, 12, 12)
        add_layout.setSpacing(10)

        # Color selector button
        color_names = list(GROUP_COLORS.keys())
        self._selected_color_index = 0

        color_btn = QPushButton()
        color_btn.setFixedSize(36, 36)
        color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_color_btn = color_btn
        self._update_add_color_button_style()

        # Create color menu - Notion style
        color_menu = QMenu(dialog)
        color_menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #E9E9E7;
                border-radius: 6px;
                padding: 8px;
            }
            QMenu::item { padding: 0px; background: transparent; }
        """)
        self._build_add_color_menu(color_menu, dialog)
        color_btn.setMenu(color_menu)
        add_layout.addWidget(color_btn)

        # Name input
        group_name_input = QLineEdit()
        group_name_input.setFixedHeight(36)
        group_name_input.setPlaceholderText(self.tr('group_name'))
        group_name_input.setStyleSheet("""
            QLineEdit {
                font-size: 13px;
                padding: 6px 10px;
                border: 1px solid #E9E9E7;
                border-radius: 6px;
                background-color: white;
                color: #37352F;
            }
            QLineEdit:focus { border-color: #37352F; }
            QLineEdit::placeholder { color: #9CA3AF; }
        """)
        add_layout.addWidget(group_name_input, 1)
        self._group_name_input = group_name_input

        # Confirm add button
        btn_add = QToolButton()
        btn_add.setFixedSize(32, 32)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setIcon(QIcon(create_check_icon(18, '#10B981')))
        btn_add.setIconSize(QSize(18, 18))
        btn_add.setStyleSheet("""
            QToolButton { background: transparent; border: none; }
            QToolButton:hover { background-color: #ECFDF5; border-radius: 8px; }
        """)
        add_layout.addWidget(btn_add)

        # Cancel button
        btn_cancel_add = QToolButton()
        btn_cancel_add.setFixedSize(32, 32)
        btn_cancel_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel_add.setIcon(QIcon(create_close_icon(18, '#EF4444')))
        btn_cancel_add.setIconSize(QSize(18, 18))
        btn_cancel_add.setStyleSheet("""
            QToolButton { background: transparent; border: none; }
            QToolButton:hover { background-color: #FEF2F2; border-radius: 8px; }
        """)
        add_layout.addWidget(btn_cancel_add)

        layout.addWidget(add_section)

        def toggle_add_section():
            if add_section.isVisible():
                add_section.hide()
            else:
                add_section.show()
                group_name_input.clear()
                group_name_input.setFocus()

        btn_show_add.clicked.connect(toggle_add_section)
        btn_cancel_add.clicked.connect(lambda: add_section.hide())

        # Group list with drag & drop support - Notion style
        self._groups_list_widget = DraggableGroupList(self._on_groups_reordered)
        self._groups_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._groups_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._groups_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._groups_list_widget.setSpacing(4)
        self._groups_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #FBFBFA;
                border: 1px solid #E9E9E7;
                border-radius: 8px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item { background: transparent; border: none; padding: 0px; }
            QListWidget::item:selected { background: transparent; }
            QScrollBar:vertical {
                width: 6px; background: transparent; margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #D1D5DB; border-radius: 3px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #9CA3AF; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)

        # Store dialog reference BEFORE populating
        self.group_dialog = dialog

        # Populate groups
        self._refresh_group_items()

        layout.addWidget(self._groups_list_widget, 1)

        def add_new_group():
            name = group_name_input.text().strip()
            if not name:
                return
            # Get selected preset color
            color = color_names[self._selected_color_index % len(color_names)]
            self.group_service.create(name, color)
            self._save_data()
            self._refresh_group_list()
            self._refresh_group_items()
            group_name_input.clear()
            # Reset to first color
            self._selected_color_index = 0
            self._update_add_color_button_style()

        btn_add.clicked.connect(add_new_group)

        # Use non-modal dialog so undo toast can be clicked
        dialog.setModal(False)
        dialog.finished.connect(lambda: setattr(self, 'group_dialog', None))

        # Show add section initially if open_add is True
        if not open_add:
            add_section.hide()
        else:
            group_name_input.setFocus()

        dialog.show()

    def _update_add_color_button_style(self) -> None:
        """Update add color button to show current selected color."""
        color_names = list(GROUP_COLORS.keys())
        color_hex = get_color_hex(color_names[self._selected_color_index % len(color_names)])
        pastel_fill = get_pastel_color(color_hex)

        self._add_color_btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: none; }}
            QPushButton::menu-indicator {{ image: none; width: 0px; }}
        """)

        # Clear existing layout
        if self._add_color_btn.layout():
            while self._add_color_btn.layout().count():
                item = self._add_color_btn.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            btn_layout = QHBoxLayout(self._add_color_btn)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Rounded square color indicator
        dot = QLabel()
        dot.setFixedSize(20, 20)
        dot.setStyleSheet(f"""
            background-color: {pastel_fill};
            border: 1px solid #9CA3AF;
            border-radius: 4px;
        """)
        self._add_color_btn.layout().addWidget(dot)

    def _build_add_color_menu(self, menu: QMenu, dialog: QDialog) -> None:
        """Build color selection menu with grid of color circles."""
        menu.clear()
        color_names = list(GROUP_COLORS.keys())

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(4, 4, 4, 4)

        def make_color_selector(idx):
            def select():
                self._selected_color_index = idx
                self._update_add_color_button_style()
                menu.close()
            return select

        for i, color_name in enumerate(color_names):
            color_hex = get_color_hex(color_name)
            pastel_fill = get_pastel_color(color_hex)
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {pastel_fill};
                    border: 2px solid #9CA3AF;
                    border-radius: 6px;
                }}
                QPushButton:hover {{ border-color: #6366F1; border-width: 3px; }}
            """)
            btn.clicked.connect(make_color_selector(i))
            grid_layout.addWidget(btn, i // 4, i % 4)

        action = QWidgetAction(menu)
        action.setDefaultWidget(grid_widget)
        menu.addAction(action)

    def _refresh_group_items(self) -> None:
        """Refresh the group items in the manage dialog."""
        if not hasattr(self, '_groups_list_widget') or self._groups_list_widget is None:
            return
        if self.group_dialog is None:
            return

        self._groups_list_widget.clear()

        for i, group in enumerate(self.state.groups):
            self._add_group_item_widget(group, i)

        if not self.state.groups:
            empty_item = QListWidgetItem()
            empty_text = "暂无分组" if self.state.language == 'zh' else "No groups yet"
            empty_widget = QLabel(empty_text)
            empty_widget.setStyleSheet("color: #9CA3AF; padding: 30px; font-size: 14px;")
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setSizeHint(empty_widget.sizeHint())
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._groups_list_widget.addItem(empty_item)
            self._groups_list_widget.setItemWidget(empty_item, empty_widget)

    def _add_group_item_widget(self, group: Group, index: int) -> None:
        """Add a single group item widget."""
        color_names = list(GROUP_COLORS.keys())

        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 52))
        list_item.setData(Qt.ItemDataRole.UserRole, index)

        item_widget = QWidget()
        item_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #E9E9E7;
                border-radius: 6px;
            }
            QWidget:hover {
                border-color: #37352F;
                background-color: #FAFAFA;
            }
        """)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(8, 8, 12, 8)
        item_layout.setSpacing(8)

        # Drag handle
        drag_handle = DragHandle(self._groups_list_widget, list_item)
        item_layout.addWidget(drag_handle)

        # Color selector button
        color_btn = QPushButton()
        color_btn.setFixedSize(32, 32)
        color_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        current_color = group.color
        color_hex = get_color_hex(current_color)
        pastel_fill = get_pastel_color(color_hex)

        color_btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: none; }}
            QPushButton::menu-indicator {{ image: none; width: 0px; }}
        """)

        btn_layout = QHBoxLayout(color_btn)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot = QLabel()
        dot.setFixedSize(18, 18)
        dot.setStyleSheet(f"""
            background-color: {pastel_fill};
            border: 1px solid #9CA3AF;
            border-radius: 4px;
        """)
        btn_layout.addWidget(dot)

        # Create color menu for this button - Notion style
        color_menu = QMenu(self)
        color_menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #E9E9E7;
                border-radius: 6px;
                padding: 8px;
            }
        """)

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(4)
        grid_layout.setContentsMargins(2, 2, 2, 2)

        def update_edit_color_btn(new_color_hex, btn=color_btn):
            while btn.layout().count():
                item = btn.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            pastel = get_pastel_color(new_color_hex)
            new_dot = QLabel()
            new_dot.setFixedSize(18, 18)
            new_dot.setStyleSheet(f"background-color: {pastel}; border: 1px solid #9CA3AF; border-radius: 4px;")
            btn.layout().addWidget(new_dot)

        def make_preset_handler(idx, g_idx, menu_ref):
            def handler():
                c = get_color_hex(color_names[idx])
                self._update_group_color(g_idx, color_names[idx])
                update_edit_color_btn(c)
                menu_ref.close()
            return handler

        for i, cn in enumerate(color_names):
            ch = get_color_hex(cn)
            pastel = get_pastel_color(ch)
            b = QPushButton()
            b.setFixedSize(24, 24)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background-color: {pastel}; border: 2px solid #9CA3AF; border-radius: 5px; }}
                QPushButton:hover {{ border-color: #6366F1; }}
            """)
            b.clicked.connect(make_preset_handler(i, index, color_menu))
            grid_layout.addWidget(b, i // 4, i % 4)

        action = QWidgetAction(color_menu)
        action.setDefaultWidget(grid_widget)
        color_menu.addAction(action)

        color_btn.setMenu(color_menu)
        item_layout.addWidget(color_btn)

        # Name input - Notion style
        name_input = QLineEdit()
        name_input.setText(group.name)
        name_input.setFixedHeight(32)
        name_input.setStyleSheet("""
            QLineEdit {
                font-size: 13px;
                border: 1px solid #E9E9E7;
                border-radius: 4px;
                background-color: #FBFBFA;
                padding: 4px 8px;
                color: #37352F;
            }
            QLineEdit:focus { border-color: #37352F; background-color: white; }
        """)
        name_input.textChanged.connect(lambda text, idx=index: self._update_group_name(idx, text.strip()))
        item_layout.addWidget(name_input, 1)

        # Delete button
        btn_delete = QPushButton()
        btn_delete.setFixedSize(28, 28)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setIcon(QIcon(create_trash_icon(16, '#EF4444')))
        btn_delete.setIconSize(QSize(16, 16))
        btn_delete.setStyleSheet("""
            QPushButton { background: transparent; border: none; }
            QPushButton:hover { background-color: #FEF2F2; border-radius: 6px; }
        """)
        btn_delete.clicked.connect(lambda checked, idx=index: self._delete_group_at(idx))
        item_layout.addWidget(btn_delete)

        self._groups_list_widget.addItem(list_item)
        self._groups_list_widget.setItemWidget(list_item, item_widget)

    def _update_group_color(self, index: int, new_color: str) -> None:
        """Update group color."""
        if index < len(self.state.groups):
            self.state.groups[index].color = new_color
            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()

    def _update_group_name(self, index: int, new_name: str) -> None:
        """Update group name."""
        if index < len(self.state.groups) and new_name:
            old_name = self.state.groups[index].name
            if old_name != new_name:
                # Update accounts with this group
                for acc in self.state.accounts:
                    if old_name in acc.groups:
                        acc.groups.remove(old_name)
                        acc.groups.append(new_name)
                self.state.groups[index].name = new_name
                self._save_data()
                self._load_accounts_to_table()
                self._refresh_group_list()

    def _delete_group_at(self, index: int) -> None:
        """Delete group at index with confirmation and undo support."""
        if index < len(self.state.groups):
            group = self.state.groups[index]

            reply = QMessageBox.question(
                self,
                self.tr('confirm_delete_group'),
                self.tr('confirm_delete_group_msg').format(group.name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Backup for undo - store affected accounts
            affected_accounts = []
            for acc in self.state.accounts:
                if group.name in acc.groups:
                    affected_accounts.append(acc.id or acc.email)
                    acc.groups.remove(group.name)

            # Store backup (make a copy of the group)
            self.deleted_group_backup = {
                'group': Group(name=group.name, color=group.color),
                'index': index,
                'affected_accounts': affected_accounts
            }

            # Remove group
            self.state.groups.pop(index)
            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()
            self._refresh_group_items()

            # Show undo toast
            self._show_undo_toast(group.name)

    def _show_undo_toast(self, group_name: str) -> None:
        """Show toast with undo button for deleted group."""
        # Hide any existing undo toast first
        self._hide_undo_toast()

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
        undo_btn.clicked.connect(self._undo_delete_group)
        container_layout.addWidget(undo_btn)

        layout.addWidget(container)

        # Position at bottom center of main window
        self.undo_toast.adjustSize()
        parent_rect = self.geometry()
        toast_x = parent_rect.x() + (parent_rect.width() - self.undo_toast.width()) // 2
        toast_y = parent_rect.y() + parent_rect.height() - self.undo_toast.height() - 80
        self.undo_toast.move(toast_x, toast_y)
        self.undo_toast.show()
        self.undo_toast.raise_()

        # Auto-hide after 5 seconds
        QTimer.singleShot(5000, self._hide_undo_toast)

    def _hide_undo_toast(self) -> None:
        """Hide the undo toast."""
        if self.undo_toast:
            self.undo_toast.hide()
            self.undo_toast.deleteLater()
            self.undo_toast = None

    def _undo_delete_group(self) -> None:
        """Restore the last deleted group."""
        try:
            if not self.deleted_group_backup:
                return

            backup = self.deleted_group_backup

            # Restore group at original position
            index = min(backup['index'], len(self.state.groups))
            self.state.groups.insert(index, backup['group'])

            # Restore group to affected accounts
            group_name = backup['group'].name
            for acc in self.state.accounts:
                acc_id = acc.id or acc.email
                if acc_id in backup['affected_accounts']:
                    if group_name not in acc.groups:
                        acc.groups.append(group_name)

            # Clear backup
            self.deleted_group_backup = None

            # Save and refresh
            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()

            # Only refresh group items if dialog is still open and valid
            try:
                if self.group_dialog is not None and self.group_dialog.isVisible():
                    self._refresh_group_items()
            except RuntimeError:
                pass  # Widget was deleted

            # Hide undo toast
            self._hide_undo_toast()

            # Show confirmation
            self.toast.show_message(f"✓ {group_name}", self)
        except Exception as e:
            logger.error(f"Undo error: {e}")

    def _on_groups_reordered(self) -> None:
        """Handle group reordering after drag and drop."""
        if not hasattr(self, '_groups_list_widget'):
            return

        new_order = []
        for i in range(self._groups_list_widget.count()):
            item = self._groups_list_widget.item(i)
            if item:
                original_index = item.data(Qt.ItemDataRole.UserRole)
                if original_index is not None and original_index < len(self.state.groups):
                    new_order.append(self.state.groups[original_index])

        if len(new_order) == len(self.state.groups):
            self.state.groups = new_order
            self._save_data()
            self._refresh_group_list()
            self._refresh_group_items()

    def _show_trash(self) -> None:
        """Show trash dialog with table and checkboxes."""
        if not self.state.trash:
            QMessageBox.information(
                self, self.tr('trash_empty'), self.tr('trash_empty_msg')
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr('trash_title').format(len(self.state.trash)))
        dialog.resize(800, 400)
        layout = QVBoxLayout(dialog)

        # Create table for trash items
        trash_table = QTableWidget()
        trash_table.setColumnCount(6)
        trash_table.setHorizontalHeaderLabels([
            "", self.tr('email'), self.tr('password'), self.tr('secondary_email'),
            self.tr('2fa_key'), self.tr('import_time')
        ])
        trash_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        trash_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        trash_table.setColumnWidth(0, 45)
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

        # Header checkbox for select all
        header_checkbox_widget = QWidget(trash_table.horizontalHeader())
        header_checkbox_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        header_checkbox_layout = QHBoxLayout(header_checkbox_widget)
        header_checkbox_layout.setContentsMargins(0, 0, 0, 0)
        header_checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_checkbox = QCheckBox()
        header_checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid #CBD5E1;
                border-radius: 4px;
                background-color: #FFFFFF;
            }}
            QCheckBox::indicator:hover {{
                border-color: #3B82F6;
                background-color: #EFF6FF;
            }}
            QCheckBox::indicator:checked {{
                background-color: #3B82F6;
                border-color: #3B82F6;
                image: url({CHECK_SVG_PATH});
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: #2563EB;
                border-color: #2563EB;
            }}
        """)
        header_checkbox_layout.addWidget(header_checkbox)

        def update_header_checkbox_position():
            header = trash_table.horizontalHeader()
            col_width = header.sectionSize(0)
            header_height = header.height()
            # First column always starts at x=0
            header_checkbox_widget.setGeometry(0, 0, col_width, header_height)

        def on_header_checkbox_changed(state):
            is_checked = state == Qt.CheckState.Checked.value
            for row in range(trash_table.rowCount()):
                widget = trash_table.cellWidget(row, 0)
                if widget:
                    cb = widget.findChild(QCheckBox)
                    if cb:
                        cb.blockSignals(True)
                        cb.setChecked(is_checked)
                        cb.blockSignals(False)

        header_checkbox.stateChanged.connect(on_header_checkbox_changed)

        # Fill table with trash items
        for i, acc in enumerate(self.state.trash):
            trash_table.insertRow(i)

            # Checkbox
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox = QCheckBox()
            checkbox.setStyleSheet(f"""
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid #CBD5E1;
                    border-radius: 4px;
                    background-color: #FFFFFF;
                }}
                QCheckBox::indicator:hover {{
                    border-color: #3B82F6;
                    background-color: #EFF6FF;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #3B82F6;
                    border-color: #3B82F6;
                    image: url({CHECK_SVG_PATH});
                }}
                QCheckBox::indicator:checked:hover {{
                    background-color: #2563EB;
                    border-color: #2563EB;
                }}
            """)
            checkbox_layout.addWidget(checkbox)
            trash_table.setCellWidget(i, 0, checkbox_widget)

            trash_table.setItem(i, 1, QTableWidgetItem(acc.email or ''))
            trash_table.setItem(i, 2, QTableWidgetItem(acc.password or ''))
            trash_table.setItem(i, 3, QTableWidgetItem(acc.backup or ''))
            secret = acc.secret or ''
            display_secret = secret[:6] + "..." + secret[-4:] if len(secret) > 10 else secret
            secret_item = QTableWidgetItem(display_secret)
            secret_item.setData(Qt.ItemDataRole.UserRole, secret)
            trash_table.setItem(i, 4, secret_item)
            trash_table.setItem(i, 5, QTableWidgetItem(acc.import_time or ''))

        layout.addWidget(trash_table)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_restore = QPushButton(self.tr('restore'))
        btn_restore.setFixedHeight(36)
        btn_restore.setIcon(QIcon(create_restore_icon(18, '#FFFFFF')))
        btn_restore.setIconSize(QSize(18, 18))
        btn_restore.setStyleSheet("""
            QPushButton {
                background-color: #10B981; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 15px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_layout.addWidget(btn_restore)

        btn_delete = QPushButton(self.tr('delete_permanent') if 'delete_permanent' in TRANSLATIONS.get('en', {}) else "永久删除")
        btn_delete.setFixedHeight(36)
        btn_delete.setIcon(QIcon(create_close_icon(18, '#FFFFFF')))
        btn_delete.setIconSize(QSize(18, 18))
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 15px;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn_layout.addWidget(btn_delete)

        btn_clear = QPushButton(self.tr('clear_trash'))
        btn_clear.setFixedHeight(36)
        btn_clear.setIcon(QIcon(create_trash_icon(18, '#FFFFFF')))
        btn_clear.setIconSize(QSize(18, 18))
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #6B7280; color: white; font-weight: bold;
                border: none; border-radius: 6px; padding: 0 15px;
            }
            QPushButton:hover { background-color: #4B5563; }
        """)
        btn_layout.addWidget(btn_clear)

        layout.addLayout(btn_layout)

        def get_checked_rows():
            """Get list of checked row indices."""
            checked = []
            for row in range(trash_table.rowCount()):
                widget = trash_table.cellWidget(row, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        checked.append(row)
            return checked

        def restore_selected():
            rows = get_checked_rows()
            if not rows:
                return
            for row in sorted(rows, reverse=True):
                if row < len(self.state.trash):
                    acc = self.state.trash[row]
                    self.account_service.restore_from_trash(acc.id)
                    trash_table.removeRow(row)
            self._save_data()
            self._load_accounts_to_table()
            self._refresh_group_list()
            if not self.state.trash:
                dialog.close()
            else:
                dialog.setWindowTitle(self.tr('trash_title').format(len(self.state.trash)))

        def delete_selected():
            rows = get_checked_rows()
            if not rows:
                return
            for row in sorted(rows, reverse=True):
                if row < len(self.state.trash):
                    self.state.trash.pop(row)
                    trash_table.removeRow(row)
            self._save_data()
            self._refresh_group_list()
            if not self.state.trash:
                dialog.close()
            else:
                dialog.setWindowTitle(self.tr('trash_title').format(len(self.state.trash)))

        def clear_all_trash():
            reply = QMessageBox.question(
                dialog, self.tr('confirm_empty_trash'),
                self.tr('confirm_empty_trash_msg').format(len(self.state.trash)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.account_service.empty_trash()
                self._save_data()
                self._refresh_group_list()
                dialog.accept()

        btn_restore.clicked.connect(restore_selected)
        btn_delete.clicked.connect(delete_selected)
        btn_clear.clicked.connect(clear_all_trash)

        # Show dialog and position header checkbox
        dialog.show()
        QApplication.processEvents()
        update_header_checkbox_position()
        dialog.exec()


def run_app():
    """Run the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
