"""
Stylesheet definitions for the application UI.

Typography Scale (based on modern UI best practices):
- xs: 11px  - hints, badges
- sm: 12px  - secondary text, captions
- base: 13px - body text, buttons
- lg: 14px  - emphasized body
- xl: 16px  - section titles
- 2xl: 18px - dialog titles
- 3xl: 20px - main title
"""

# Main window background
MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #F3F4F6;
    }
"""

# Primary button (blue)
PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #3B82F6;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #2563EB;
    }
    QPushButton:pressed {
        background-color: #1D4ED8;
    }
    QPushButton:disabled {
        background-color: #9CA3AF;
    }
"""

# Success button (green)
SUCCESS_BUTTON_STYLE = """
    QPushButton {
        background-color: #10B981;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #059669;
    }
    QPushButton:pressed {
        background-color: #047857;
    }
"""

# Danger button (red)
DANGER_BUTTON_STYLE = """
    QPushButton {
        background-color: #EF4444;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #DC2626;
    }
    QPushButton:pressed {
        background-color: #B91C1C;
    }
"""

# Secondary button (gray)
SECONDARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #6B7280;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #4B5563;
    }
    QPushButton:pressed {
        background-color: #374151;
    }
"""

# Text button (no background)
TEXT_BUTTON_STYLE = """
    QPushButton {
        background-color: transparent;
        color: #6B7280;
        border: none;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 13px;
    }
    QPushButton:hover {
        color: #374151;
        background-color: #F3F4F6;
        border-radius: 6px;
    }
"""

# Icon button (small, square)
ICON_BUTTON_STYLE = """
    QPushButton {
        background-color: transparent;
        border: none;
        padding: 4px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #E5E7EB;
    }
    QPushButton:pressed {
        background-color: #D1D5DB;
    }
"""

# Toggle button style
TOGGLE_BUTTON_STYLE = """
    QPushButton {
        background-color: #F3F4F6;
        color: #4B5563;
        border: 1px solid #D1D5DB;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #E5E7EB;
    }
    QPushButton:checked {
        background-color: #3B82F6;
        color: white;
        border: 1px solid #3B82F6;
    }
"""

# Table widget style
TABLE_STYLE = """
    QTableWidget {
        background-color: white;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        gridline-color: #F3F4F6;
        selection-background-color: #DBEAFE;
        selection-color: #1E40AF;
        font-size: 13px;
    }
    QTableWidget::item {
        padding: 8px;
        border-bottom: 1px solid #F3F4F6;
    }
    QTableWidget::item:selected {
        background-color: #DBEAFE;
        color: #1E40AF;
    }
    QTableWidget::item:hover {
        background-color: #F9FAFB;
    }
    QHeaderView::section {
        background-color: #F9FAFB;
        color: #374151;
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid #E5E7EB;
        font-weight: 600;
        font-size: 12px;
    }
    QHeaderView::section:hover {
        background-color: #F3F4F6;
    }
"""

# Sidebar style
SIDEBAR_STYLE = """
    QFrame {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }
"""

# Sidebar list style
SIDEBAR_LIST_STYLE = """
    QListWidget {
        background-color: transparent;
        border: none;
        outline: none;
        font-size: 13px;
    }
    QListWidget::item {
        padding: 8px 12px;
        border-radius: 6px;
        margin: 2px 8px;
    }
    QListWidget::item:selected {
        background-color: #DBEAFE;
        color: #1E40AF;
        font-weight: 500;
    }
    QListWidget::item:hover {
        background-color: #F3F4F6;
    }
"""

# Group box style
GROUP_BOX_STYLE = """
    QGroupBox {
        font-weight: 600;
        font-size: 14px;
        color: #374151;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        background-color: white;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        background-color: white;
    }
"""

# Text input style
TEXT_INPUT_STYLE = """
    QPlainTextEdit {
        background-color: white;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 8px;
        font-size: 13px;
    }
    QPlainTextEdit:focus {
        border: 2px solid #3B82F6;
    }
"""

# Line edit style
LINE_EDIT_STYLE = """
    QLineEdit {
        background-color: white;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }
    QLineEdit:focus {
        border: 2px solid #3B82F6;
    }
"""

# Combo box style
COMBO_BOX_STYLE = """
    QComboBox {
        background-color: white;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
        min-width: 100px;
    }
    QComboBox:hover {
        border: 1px solid #9CA3AF;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    QComboBox::down-arrow {
        width: 12px;
        height: 12px;
    }
    QComboBox QAbstractItemView {
        background-color: white;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        selection-background-color: #DBEAFE;
        font-size: 13px;
    }
"""

# Progress bar style
PROGRESS_BAR_STYLE = """
    QProgressBar {
        background-color: #E5E7EB;
        border: none;
        border-radius: 4px;
        text-align: center;
        font-size: 12px;
        color: #374151;
    }
    QProgressBar::chunk {
        background-color: #3B82F6;
        border-radius: 4px;
    }
"""

# Toast notification style
TOAST_STYLE = """
    QLabel {
        background-color: #1F2937;
        color: white;
        padding: 12px 24px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
    }
"""

# Label styles
TITLE_LABEL_STYLE = """
    QLabel {
        font-size: 20px;
        font-weight: 600;
        color: #1F2937;
    }
"""

SUBTITLE_LABEL_STYLE = """
    QLabel {
        font-size: 14px;
        font-weight: 500;
        color: #4B5563;
    }
"""

HINT_LABEL_STYLE = """
    QLabel {
        font-size: 12px;
        color: #6B7280;
    }
"""

# Checkbox style
CHECKBOX_STYLE = """
    QCheckBox {
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #D1D5DB;
        border-radius: 4px;
        background-color: white;
    }
    QCheckBox::indicator:hover {
        border-color: #9CA3AF;
    }
    QCheckBox::indicator:checked {
        background-color: #3B82F6;
        border-color: #3B82F6;
        image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
    }
"""

# Dialog style
DIALOG_STYLE = """
    QDialog {
        background-color: #F9FAFB;
    }
"""

# Scroll area style
SCROLL_AREA_STYLE = """
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    QScrollBar:vertical {
        background-color: #F3F4F6;
        width: 8px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background-color: #D1D5DB;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #9CA3AF;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar:horizontal {
        background-color: #F3F4F6;
        height: 8px;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background-color: #D1D5DB;
        border-radius: 4px;
        min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #9CA3AF;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }
"""

# Menu style
MENU_STYLE = """
    QMenu {
        background-color: white;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 4px;
        font-size: 13px;
    }
    QMenu::item {
        padding: 8px 16px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #F3F4F6;
    }
    QMenu::separator {
        height: 1px;
        background-color: #E5E7EB;
        margin: 4px 8px;
    }
"""
