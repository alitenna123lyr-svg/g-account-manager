"""
G-Account Manager - Main Window v2
Modern minimal design with library management and archive features.
"""

import logging
from typing import Optional, List, Dict, Set
import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QMenu, QApplication, QProgressBar,
    QDialog, QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QCheckBox,
    QWidgetAction, QGraphicsDropShadowEffect, QToolButton, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QCursor, QBrush, QPalette

from ..models.app_state import AppState
from ..models.account import Account
from ..models.group import Group
from ..services.totp_service import get_totp_service
from ..services.time_service import get_time_service
from ..services.library_service import LibraryService, LibraryInfo
from ..services.archive_service import get_archive_service, ArchiveInfo
from ..config.translations import get_translation

from .dialogs.tag_editor_dialog import TagEditorDialog
from .theme import get_theme_manager, get_theme
from .icons import (
    icon_key, icon_search, icon_sun, icon_moon, icon_settings,
    icon_plus, icon_copy, icon_eye, icon_eye_off, icon_edit, icon_trash,
    icon_user, icon_briefcase, icon_users, icon_wallet, icon_check,
    icon_chevron_down, icon_archive, icon_library, icon_import, icon_export,
    icon_checkbox, icon_checkbox_empty, icon_list, icon_grid, icon_square_plus, icon_square_minus,
    icon_library_move, icon_arrow_up, icon_arrow_down,
    icon_mail, icon_refresh, icon_close
)

logger = logging.getLogger(__name__)


class SelectionManager:
    """Unified multi-selection logic manager.

    Uses object id for selection tracking to handle Account objects that
    may have __eq__ based on content (e.g., same email = equal).

    Selection behavior:
    - Normal click: Toggle current item (add/remove), update anchor
    - Shift+Click: Add range from anchor to current
    """

    def __init__(self):
        # Use dict with id(account) -> account to track by object identity
        self._selected: Dict[int, Account] = {}
        self._anchor_index: Optional[int] = None

    @property
    def count(self) -> int:
        """Get the count of selected accounts."""
        return len(self._selected)

    @property
    def items(self) -> List[Account]:
        """Get selected accounts as a list."""
        return list(self._selected.values())

    @property
    def anchor_index(self) -> Optional[int]:
        """Get the current anchor index for range selection."""
        return self._anchor_index

    def is_selected(self, account: Account) -> bool:
        """Check if an account is selected (by object identity)."""
        if account is None:
            return False
        return id(account) in self._selected

    def clear(self) -> None:
        """Clear all selections and reset anchor."""
        self._selected.clear()
        self._anchor_index = None

    def toggle(self, account: Account, index: int) -> None:
        """Toggle current item selection, update anchor."""
        acc_id = id(account)
        if acc_id in self._selected:
            del self._selected[acc_id]
        else:
            self._selected[acc_id] = account
        self._anchor_index = index

    def select_range(self, accounts_list: List[Account], target_index: int) -> None:
        """Shift+Click: Add range from anchor to target (inclusive)."""
        if self._anchor_index is None:
            # No anchor - just toggle single
            if target_index < len(accounts_list):
                self.toggle(accounts_list[target_index], target_index)
            return

        # Add range from anchor to target (don't clear existing)
        start = min(self._anchor_index, target_index)
        end = max(self._anchor_index, target_index)

        for i in range(start, end + 1):
            if i < len(accounts_list):
                acc = accounts_list[i]
                self._selected[id(acc)] = acc

        # Don't update anchor on Shift+click (keep original anchor)

    def handle_click(self, account: Account, index: int, accounts_list: List[Account],
                     shift_held: bool) -> None:
        """Handle a click.

        Args:
            account: The clicked account
            index: The index of the clicked account
            accounts_list: The full ordered list of accounts
            shift_held: Whether Shift key was held
        """
        if shift_held:
            self.select_range(accounts_list, index)
        else:
            self.toggle(account, index)

    def set_all(self, accounts: List[Account]) -> None:
        """Select all accounts from a list."""
        self._selected = {id(acc): acc for acc in accounts}
        self._anchor_index = None


class FlowLayout(QVBoxLayout):
    """A simple flow layout that wraps widgets to new lines."""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._spacing = spacing
        self._rows = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addWidget(self, widget):
        """Add widget - will be arranged in flow on next layout."""
        if not self._rows:
            self._rows.append([])
        self._rows[-1].append(widget)

    def apply_layout(self, max_width: int):
        """Apply the flow layout with given max width."""
        # Clear existing layouts
        while self.count():
            item = self.takeAt(0)
            if item.layout():
                while item.layout().count():
                    item.layout().takeAt(0)

        # Rebuild rows based on width
        all_widgets = []
        for row in self._rows:
            all_widgets.extend(row)

        self._rows = []
        current_row = []
        current_width = 0

        for widget in all_widgets:
            widget_width = widget.sizeHint().width()
            if current_width + widget_width + self._spacing > max_width and current_row:
                self._rows.append(current_row)
                current_row = [widget]
                current_width = widget_width
            else:
                current_row.append(widget)
                current_width += widget_width + self._spacing

        if current_row:
            self._rows.append(current_row)

        # Create row layouts
        for row in self._rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(self._spacing)
            row_layout.setContentsMargins(0, 0, 0, 0)
            for widget in row:
                row_layout.addWidget(widget)
            row_layout.addStretch()
            super().addLayout(row_layout)


class ClickableFrame(QFrame):
    """A QFrame that emits signals when clicked."""
    clicked = pyqtSignal()  # Simple click signal
    rightClicked = pyqtSignal(object)  # Passes the global position

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        # Don't call super() to avoid issues with widget deletion during signal handling


class ToastWidget(QFrame):
    """Toast notification widget with optional action button and iOS-style frosted glass effect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setVisible(False)
        self.setFixedHeight(44)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(20, 0, 20, 0)
        self._layout.setSpacing(12)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._label, 1)

        self._action_btn = QPushButton()
        self._action_btn.setVisible(False)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._layout.addWidget(self._action_btn)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._on_timeout)

        self._action_callback = None

    def show_message(self, message: str, duration: int = 2000, action_text: str = None, action_callback=None, center: bool = False):
        """Show a toast message with optional action button.

        Args:
            message: The message to display
            duration: How long to show the message (ms)
            action_text: Optional action button text
            action_callback: Optional callback when action is clicked
            center: If True, show in center; if False, show at bottom
        """
        self._label.setText(message)
        self._action_callback = action_callback

        # Show/hide action button
        if action_text and action_callback:
            self._action_btn.setText(action_text)
            self._action_btn.setVisible(True)
            try:
                self._action_btn.clicked.disconnect()
            except:
                pass
            self._action_btn.clicked.connect(self._on_action_clicked)
        else:
            self._action_btn.setVisible(False)

        self.setVisible(True)
        self.adjustSize()

        # Position toast
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            if center:
                y = (parent_rect.height() - self.height()) // 2
            else:
                y = parent_rect.height() - self.height() - 40  # 40px from bottom
            self.move(x, y)

        # Auto hide
        self._hide_timer.stop()
        self._hide_timer.start(duration)

    def _on_action_clicked(self):
        """Handle action button click."""
        self._hide_timer.stop()
        self.hide()
        if self._action_callback:
            self._action_callback()

    def _on_timeout(self):
        """Handle timeout - clear undo data."""
        self.hide()
        self._action_callback = None


class BounceScrollArea(QScrollArea):
    """QScrollArea with iOS-style elastic rubber band effect.

    Uses Apple's rubber band formula with smooth interpolation
    to decouple visual smoothness from mouse input frequency.
    """

    RUBBER_BAND_CONSTANT = 0.55  # Apple's constant
    LERP_FACTOR = 0.3  # Interpolation speed (balanced)
    MAX_STRETCH = 75  # Maximum visual stretch in pixels

    def __init__(self, parent=None, bottom_only: bool = False):
        super().__init__(parent)
        self._base_bottom_margin = 0
        self._visual_offset = 0.0  # Current displayed offset
        self._target_offset = 0.0  # Target offset (from rubber band formula)
        self._raw_scroll = 0.0  # Accumulated scroll beyond edge
        self._is_stretching = False  # Whether user is actively stretching
        self._bottom_only = bottom_only  # Only bounce at bottom, not top

        # Smooth interpolation timer (60fps)
        self._lerp_timer = QTimer(self)
        self._lerp_timer.setInterval(16)  # ~60fps
        self._lerp_timer.timeout.connect(self._update_lerp)

        # Timer to detect when user stops scrolling
        self._scroll_stop_timer = QTimer(self)
        self._scroll_stop_timer.setSingleShot(True)
        self._scroll_stop_timer.timeout.connect(self._start_bounce_back)

    def _rubber_band(self, x: float, d: float) -> float:
        """Apply Apple's rubber band formula."""
        c = self.RUBBER_BAND_CONSTANT
        if d == 0:
            return 0
        return (1.0 - (1.0 / ((abs(x) * c / d) + 1.0))) * d

    def _update_lerp(self):
        """Smoothly interpolate visual offset towards target."""
        diff = self._target_offset - self._visual_offset

        if abs(diff) < 0.5:
            # Close enough, snap to target
            self._visual_offset = self._target_offset
            self._apply_offset()
            # Stop timer if we've settled at 0
            if abs(self._target_offset) < 0.5 and not self._is_stretching:
                self._lerp_timer.stop()
            return

        # Smooth interpolation
        self._visual_offset += diff * self.LERP_FACTOR
        self._apply_offset()

    def _apply_offset(self):
        """Apply the current visual offset to the widget margins."""
        widget = self.widget()
        if widget:
            offset = int(self._visual_offset)
            if offset >= 0:
                widget.setContentsMargins(0, offset, 0, self._base_bottom_margin)
            else:
                widget.setContentsMargins(0, 0, 0, self._base_bottom_margin - offset)

    def _start_bounce_back(self):
        """Start bounce back by setting target to 0."""
        self._is_stretching = False
        self._target_offset = 0.0
        self._raw_scroll = 0.0
        # Ensure lerp timer is running
        if not self._lerp_timer.isActive():
            self._lerp_timer.start()

    def wheelEvent(self, event):
        """Handle wheel events with iOS-style rubber band effect."""
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()

        at_top = scrollbar.value() <= scrollbar.minimum()
        at_bottom = scrollbar.value() >= scrollbar.maximum()

        # Check if at boundary and scrolling beyond
        # If bottom_only, skip top bounce
        should_bounce_top = at_top and delta > 0 and not self._bottom_only
        should_bounce_bottom = at_bottom and delta < 0

        if should_bounce_top or should_bounce_bottom:
            self._is_stretching = True

            # Get viewport dimension for the formula
            d = self.viewport().height()

            # Accumulate raw scroll distance
            self._raw_scroll += delta * 0.4
            # Limit raw scroll to reasonable range
            max_raw = d  # Reasonable limit
            self._raw_scroll = max(-max_raw, min(max_raw, self._raw_scroll))

            # Apply rubber band formula to get target offset
            target = self._rubber_band(self._raw_scroll, d)

            # Clamp to maximum stretch
            target = min(target, self.MAX_STRETCH)

            # Apply sign based on direction
            if self._raw_scroll < 0:
                target = -target

            self._target_offset = target

            # Start lerp timer if not running
            if not self._lerp_timer.isActive():
                self._lerp_timer.start()

            # When close to max stretch, bounce back faster to avoid "stuck" feeling
            stretch_ratio = abs(target) / self.MAX_STRETCH
            if stretch_ratio > 0.85:
                # Near max - quick bounce back
                self._scroll_stop_timer.start(50)
            else:
                self._scroll_stop_timer.start(120)

            event.accept()
            return

        # If returning to normal scrolling, trigger bounce back
        if abs(self._visual_offset) > 0.5:
            self._scroll_stop_timer.start(50)

        super().wheelEvent(event)


class BounceTableWidget(QTableWidget):
    """QTableWidget with iOS-style elastic rubber band effect.

    Uses viewport geometry manipulation to create the bounce effect.
    """

    RUBBER_BAND_CONSTANT = 0.55  # Apple's constant
    LERP_FACTOR = 0.25  # Interpolation speed (smoother)
    MAX_STRETCH = 80  # Maximum visual stretch in pixels

    def __init__(self, parent=None):
        super().__init__(parent)
        self._visual_offset = 0.0
        self._target_offset = 0.0
        self._raw_scroll = 0.0
        self._is_stretching = False
        self._base_viewport_y = 0

        # Enable pixel-based scrolling for smoother effect
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Smooth interpolation timer (60fps)
        self._lerp_timer = QTimer(self)
        self._lerp_timer.setInterval(16)
        self._lerp_timer.timeout.connect(self._update_lerp)

        # Timer to detect when user stops scrolling
        self._scroll_stop_timer = QTimer(self)
        self._scroll_stop_timer.setSingleShot(True)
        self._scroll_stop_timer.timeout.connect(self._start_bounce_back)

    def showEvent(self, event):
        """Capture base viewport position on show."""
        super().showEvent(event)
        self._base_viewport_y = self.viewport().y()

    def _rubber_band(self, x: float, d: float) -> float:
        """Apply Apple's rubber band formula."""
        c = self.RUBBER_BAND_CONSTANT
        if d == 0:
            return 0
        return (1.0 - (1.0 / ((abs(x) * c / d) + 1.0))) * d

    def _update_lerp(self):
        """Smoothly interpolate visual offset towards target."""
        diff = self._target_offset - self._visual_offset

        if abs(diff) < 0.5:
            self._visual_offset = self._target_offset
            self._apply_visual_offset()
            if abs(self._target_offset) < 0.5 and not self._is_stretching:
                self._lerp_timer.stop()
            return

        self._visual_offset += diff * self.LERP_FACTOR
        self._apply_visual_offset()

    def _apply_visual_offset(self):
        """Apply the current visual offset by moving viewport."""
        offset = int(self._visual_offset)
        viewport = self.viewport()
        # Move viewport position to create visual offset effect
        current_geo = viewport.geometry()
        new_y = self._base_viewport_y + offset
        viewport.setGeometry(current_geo.x(), new_y, current_geo.width(), current_geo.height())

    def _start_bounce_back(self):
        """Start bounce back by setting target to 0."""
        self._is_stretching = False
        self._target_offset = 0.0
        self._raw_scroll = 0.0
        if not self._lerp_timer.isActive():
            self._lerp_timer.start()

    def resizeEvent(self, event):
        """Update base viewport position on resize."""
        super().resizeEvent(event)
        if self._visual_offset == 0:
            self._base_viewport_y = self.viewport().y()

    def wheelEvent(self, event):
        """Handle wheel events with iOS-style rubber band effect."""
        scrollbar = self.verticalScrollBar()
        delta = event.angleDelta().y()

        at_top = scrollbar.value() <= scrollbar.minimum()
        at_bottom = scrollbar.value() >= scrollbar.maximum()

        # Check if at boundary and scrolling beyond
        if (at_top and delta > 0) or (at_bottom and delta < 0):
            self._is_stretching = True

            d = self.viewport().height()

            self._raw_scroll += delta * 0.5
            max_raw = d
            self._raw_scroll = max(-max_raw, min(max_raw, self._raw_scroll))

            target = self._rubber_band(self._raw_scroll, d)
            target = min(target, self.MAX_STRETCH)

            if self._raw_scroll < 0:
                target = -target

            self._target_offset = target

            if not self._lerp_timer.isActive():
                self._lerp_timer.start()

            stretch_ratio = abs(target) / self.MAX_STRETCH
            if stretch_ratio > 0.85:
                self._scroll_stop_timer.start(50)
            else:
                self._scroll_stop_timer.start(150)

            event.accept()
            return

        if abs(self._visual_offset) > 0.5:
            self._scroll_stop_timer.start(50)

        super().wheelEvent(event)


class GroupButton(QFrame):
    """A clickable group button with colored dot indicator."""

    clicked = pyqtSignal()
    rightClicked = pyqtSignal(object)  # Emits the global position

    def __init__(self, name: str, count: int, color_hex: str = None, is_all: bool = False, parent=None):
        super().__init__(parent)
        self.group_name = name
        self.color_hex = color_hex
        self.is_all = is_all  # "All Accounts" uses icon instead of dot
        self._selected = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # Color dot or icon
        if is_all:
            # Use key icon for "All Accounts"
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(16, 16)
            layout.addWidget(self.icon_label)
            self.dot_label = None
        else:
            # Use colored dot for groups
            self.dot_label = QLabel()
            self.dot_label.setFixedSize(10, 10)
            layout.addWidget(self.dot_label)
            self.icon_label = None

        # Name label
        self.name_label = QLabel(name)
        self.name_label.setObjectName("groupName")
        layout.addWidget(self.name_label, 1)

        # Count label
        self.count_label = QLabel(f"({count})")
        self.count_label.setObjectName("groupCount")
        layout.addWidget(self.count_label)

        self._apply_style()

    def set_selected(self, selected: bool):
        """Set selection state."""
        self._selected = selected
        self._apply_style()

    def set_count(self, count: int):
        """Update the count."""
        self.count_label.setText(f"({count})")

    def _apply_style(self):
        """Apply current theme style."""
        t = get_theme()

        # Small square dot for all groups
        # Light mode: pure black, Dark mode: softer gray
        is_dark = get_theme_manager().is_dark
        dot_color = "#6B7280" if is_dark else t.text_primary  # Gray-500 for dark mode
        if self.dot_label:
            self.dot_label.setStyleSheet(f"""
                background-color: {dot_color};
                border-radius: 2px;
            """)

        # Icon for "All Accounts"
        if self.icon_label:
            pixmap = QIcon(icon_key(16, t.text_secondary if not self._selected else t.text_primary)).pixmap(16, 16)
            self.icon_label.setPixmap(pixmap)

        # Frame style
        if self._selected:
            self.setStyleSheet(f"""
                GroupButton {{
                    background-color: {t.bg_hover};
                    border: none;
                    border-radius: 6px;
                }}
            """)
            self.name_label.setStyleSheet(f"""
                font-size: 13px;
                font-weight: 500;
                color: {t.text_primary};
                background: transparent;
            """)
        else:
            self.setStyleSheet(f"""
                GroupButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                }}
                GroupButton:hover {{
                    background-color: {t.bg_hover};
                }}
            """)
            self.name_label.setStyleSheet(f"""
                font-size: 13px;
                color: {t.text_secondary};
                background: transparent;
            """)

        self.count_label.setStyleSheet(f"""
            font-size: 12px;
            color: {t.text_tertiary};
            background: transparent;
        """)

    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        if not self._selected:
            t = get_theme()
            self.setStyleSheet(f"""
                GroupButton {{
                    background-color: {t.bg_hover};
                    border: none;
                    border-radius: 6px;
                }}
            """)
            self.name_label.setStyleSheet(f"""
                font-size: 13px;
                color: {t.text_primary};
                background: transparent;
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._apply_style()
        super().leaveEvent(event)


class EditableGroupItem(QFrame):
    """An editable group item for inline editing with drag support."""

    deleted = pyqtSignal(str)  # Emits group name when deleted
    name_changed = pyqtSignal(str, str)  # Emits (old_name, new_name)
    drag_started = pyqtSignal(object)  # Emits self when drag starts
    dropped = pyqtSignal(object, object)  # Emits (dragged_item, target_item)

    def __init__(self, group: Group, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.group = group
        self.is_dark = is_dark
        self._drag_start_pos = None
        self._is_dragging = False
        self._drop_at_top = False

        self.setFixedHeight(36)
        self.setAcceptDrops(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # Drag handle (6-dot grip)
        self.drag_handle = QLabel("⋮⋮")
        self.drag_handle.setFixedWidth(16)
        self.drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
        self.drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drag_handle)

        # Black dot
        self.dot_label = QLabel()
        self.dot_label.setFixedSize(8, 8)
        layout.addWidget(self.dot_label)

        # Name input - seamless editing
        self.name_input = QLineEdit(group.name)
        self.name_input.setObjectName("groupNameInput")
        self.name_input.editingFinished.connect(self._on_name_changed)
        self.name_input.returnPressed.connect(self._on_enter_pressed)
        layout.addWidget(self.name_input, 1)

        # Delete button
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(20, 20)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.group.name))
        layout.addWidget(self.delete_btn)

        self._apply_style()

    def _on_name_changed(self):
        """Handle name change."""
        new_name = self.name_input.text().strip()
        if new_name and new_name != self.group.name:
            old_name = self.group.name
            self.name_changed.emit(old_name, new_name)

    def _on_enter_pressed(self):
        """Handle Enter key - confirm and clear focus."""
        self.name_input.clearFocus()

    def _apply_style(self):
        """Apply styles."""
        t = get_theme()
        # Drag handle style
        self.drag_handle.setStyleSheet(f"""
            font-size: 12px;
            color: {t.text_tertiary};
            letter-spacing: -2px;
        """)
        # Small square dot
        # Light mode: pure black, Dark mode: softer gray
        is_dark = get_theme_manager().is_dark
        dot_color = "#6B7280" if is_dark else t.text_primary  # Gray-500 for dark mode
        self.dot_label.setStyleSheet(f"""
            background-color: {dot_color};
            border-radius: 2px;
        """)
        # Frame style
        self.setStyleSheet(f"""
            EditableGroupItem {{
                background-color: transparent;
                border-radius: 6px;
            }}
            EditableGroupItem:hover {{
                background-color: {t.bg_hover};
            }}
        """)
        # Seamless text input - no shift on focus
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 13px;
                color: {t.text_primary};
                padding: 4px 6px;
                margin: 0;
            }}
            QLineEdit:focus {{
                border: 1px solid {t.border};
                background-color: {t.bg_primary};
            }}
        """)
        # Delete button
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                color: {t.text_tertiary};
            }}
            QPushButton:hover {{
                background-color: {t.text_primary};
                color: {t.bg_primary};
            }}
        """)

    def mousePressEvent(self, event):
        """Start drag on handle area."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is in drag handle area
            handle_rect = self.drag_handle.geometry()
            if handle_rect.contains(event.pos()):
                self._drag_start_pos = event.pos()
                self.drag_handle.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle drag movement."""
        if self._drag_start_pos is not None:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance > 10:  # Minimum drag distance
                self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End drag."""
        self._drag_start_pos = None
        self.drag_handle.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        """Initiate drag operation."""
        from PyQt6.QtGui import QDrag, QPixmap, QPainter
        from PyQt6.QtCore import QMimeData

        self._is_dragging = True
        self.drag_started.emit(self)

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.group.name)
        drag.setMimeData(mime_data)

        # Create semi-transparent pixmap of this widget
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self._drag_start_pos)

        # Make source widget semi-transparent during drag
        self.setGraphicsEffect(self._create_opacity_effect(0.3))

        drag.exec(Qt.DropAction.MoveAction)
        self._is_dragging = False
        self._drag_start_pos = None
        self.setGraphicsEffect(None)
        self._apply_style()

    def _create_opacity_effect(self, opacity: float):
        """Create an opacity graphics effect."""
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(opacity)
        return effect

    def dragEnterEvent(self, event):
        """Accept drag if it's from another EditableGroupItem."""
        if event.mimeData().hasText() and not self._is_dragging:
            event.acceptProposedAction()
            self._update_drop_indicator(event.position().y())

    def dragMoveEvent(self, event):
        """Update drop indicator position during drag."""
        if event.mimeData().hasText() and not self._is_dragging:
            event.acceptProposedAction()
            self._update_drop_indicator(event.position().y())

    def _update_drop_indicator(self, y_pos: float):
        """Show drop indicator line at top or bottom based on mouse position."""
        is_dark = get_theme_manager().is_dark
        is_top_half = y_pos < self.height() / 2
        self._drop_at_top = is_top_half

        # Simple dark gray horizontal line
        indicator_color = "#6B7280" if is_dark else "#374151"

        if is_top_half:
            # Show line at top
            self.setStyleSheet(f"""
                EditableGroupItem {{
                    background-color: transparent;
                    border-top: 2px solid {indicator_color};
                }}
            """)
        else:
            # Show line at bottom
            self.setStyleSheet(f"""
                EditableGroupItem {{
                    background-color: transparent;
                    border-bottom: 2px solid {indicator_color};
                }}
            """)

    def dragLeaveEvent(self, event):
        """Reset style when drag leaves."""
        self._apply_style()

    def dropEvent(self, event):
        """Handle drop."""
        source_name = event.mimeData().text()
        if source_name != self.group.name:
            # Find source widget and emit signal
            parent = self.parent()
            if parent:
                for child in parent.children():
                    if isinstance(child, EditableGroupItem) and child.group.name == source_name:
                        # Pass drop position info
                        self._drop_at_top = event.position().y() < self.height() / 2
                        self.dropped.emit(child, self)
                        break
        self._apply_style()
        event.acceptProposedAction()


class AddGroupButton(QFrame):
    """Button to add a new group with custom dotted border."""

    clicked = pyqtSignal()

    def __init__(self, language: str = 'zh', parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self._hovered = False
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Plus icon
        self.plus_label = QLabel("+")
        self.plus_label.setObjectName("addGroupPlus")
        layout.addWidget(self.plus_label)

        # Text
        text = "添加分组" if language == 'zh' else "Add Group"
        self.text_label = QLabel(text)
        self.text_label.setObjectName("addGroupText")
        layout.addWidget(self.text_label)

        layout.addStretch()

        self._apply_style()

    def _apply_style(self):
        """Apply styles."""
        t = get_theme()
        # No border in CSS - we draw it manually
        self.setStyleSheet(f"""
            AddGroupButton {{
                background-color: transparent;
                border: none;
            }}
            #addGroupPlus {{
                font-size: 16px;
                font-weight: bold;
                color: {t.text_tertiary};
                background: transparent;
            }}
            #addGroupText {{
                font-size: 13px;
                color: {t.text_tertiary};
                background: transparent;
            }}
        """)

    def paintEvent(self, event):
        """Custom paint for dotted border."""
        from PyQt6.QtGui import QPainter, QPen, QColor
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = get_theme()
        border_color = QColor(t.text_tertiary if self._hovered else t.border)

        # Draw background on hover
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(t.bg_hover))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

        # Draw dotted border with consistent dots
        pen = QPen(border_color)
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DotLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ArchiveDialog(QDialog):
    """Dialog for viewing and restoring archives."""

    def __init__(self, parent=None, language='zh'):
        super().__init__(parent)
        self.language = language
        self.archive_service = get_archive_service()
        self.selected_archive: Optional[ArchiveInfo] = None

        self._init_ui()
        self._apply_theme()
        self._load_archives()

    def _init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("存档历史" if self.language == 'zh' else "Archive History")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("存档历史" if self.language == 'zh' else "Archive History")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # Archive list
        self.archive_list = QListWidget()
        self.archive_list.setObjectName("archiveList")
        self.archive_list.itemClicked.connect(self._on_archive_selected)
        self.archive_list.itemDoubleClicked.connect(self._restore_selected)
        layout.addWidget(self.archive_list, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.btn_restore = QPushButton("恢复所选" if self.language == 'zh' else "Restore")
        self.btn_restore.setObjectName("primaryBtn")
        self.btn_restore.setEnabled(False)
        self.btn_restore.clicked.connect(self._restore_selected)
        btn_layout.addWidget(self.btn_restore)

        self.btn_delete = QPushButton("删除" if self.language == 'zh' else "Delete")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)

    def _apply_theme(self):
        """Apply current theme to dialog."""
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
            #archiveList {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px;
            }}
            #archiveList::item {{
                padding: 12px;
                border-radius: 6px;
                margin: 2px 0;
                color: {t.text_primary};
            }}
            #archiveList::item:hover {{
                background-color: {t.bg_hover};
            }}
            #archiveList::item:selected {{
                background-color: {t.bg_selected};
            }}
            #primaryBtn {{
                background-color: {t.accent};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: 500;
            }}
            #primaryBtn:hover {{
                background-color: {t.accent};
                opacity: 0.9;
            }}
            #primaryBtn:disabled {{
                background-color: {t.bg_tertiary};
                color: {t.text_tertiary};
            }}
            #dangerBtn {{
                background-color: transparent;
                border: 1px solid {t.error};
                border-radius: 6px;
                padding: 10px 20px;
                color: {t.error};
                font-weight: 500;
            }}
            #dangerBtn:hover {{
                background-color: {t.error};
                color: white;
            }}
            #dangerBtn:disabled {{
                border-color: {t.text_tertiary};
                color: {t.text_tertiary};
            }}
        """)

    def _load_archives(self):
        """Load archives into the list."""
        self.archive_list.clear()
        archives = self.archive_service.list_archives()

        for archive in archives:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, archive)
            text = f"{archive.display_time}\n{archive.account_count} 账户 · {archive.group_count} 分组"
            item.setText(text)
            self.archive_list.addItem(item)

        if not archives:
            item = QListWidgetItem("暂无存档" if self.language == 'zh' else "No archives")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.archive_list.addItem(item)

    def _on_archive_selected(self, item: QListWidgetItem):
        """Handle archive selection."""
        self.selected_archive = item.data(Qt.ItemDataRole.UserRole)
        self.btn_restore.setEnabled(self.selected_archive is not None)
        self.btn_delete.setEnabled(self.selected_archive is not None)

    def _restore_selected(self):
        """Restore the selected archive."""
        if not self.selected_archive:
            return

        msg = "确定要恢复到此存档吗？当前数据将被替换。" if self.language == 'zh' else "Restore to this archive? Current data will be replaced."
        reply = QMessageBox.question(self, "确认" if self.language == 'zh' else "Confirm", msg)

        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def _delete_selected(self):
        """Delete the selected archive."""
        if not self.selected_archive:
            return

        msg = "确定要删除此存档吗？" if self.language == 'zh' else "Delete this archive?"
        reply = QMessageBox.question(self, "确认" if self.language == 'zh' else "Confirm", msg)

        if reply == QMessageBox.StandardButton.Yes:
            self.archive_service.delete_archive(self.selected_archive)
            self._load_archives()
            self.selected_archive = None
            self.btn_restore.setEnabled(False)
            self.btn_delete.setEnabled(False)

    def get_selected_archive(self) -> Optional[ArchiveInfo]:
        """Get the selected archive for restoration."""
        return self.selected_archive


class TrashItemWidget(QFrame):
    """Custom widget for trash list item with checkbox."""

    checked_changed = None  # Will be set by dialog

    def __init__(self, account: Account, language: str = 'zh', parent=None):
        super().__init__(parent)
        self.account = account
        self.language = language
        self._checked = False
        self._init_ui()

    def _init_ui(self):
        zh = self.language == 'zh'
        t = get_theme()

        self.setObjectName("trashItemWidget")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 12, 8)
        layout.setSpacing(10)

        # Checkbox icon (clickable label)
        self.checkbox_label = QLabel()
        self.checkbox_label.setFixedSize(22, 22)
        self._update_checkbox_icon()
        layout.addWidget(self.checkbox_label)

        # Email icon
        icon_label = QLabel()
        icon_label.setPixmap(icon_mail(18, t.text_secondary))
        icon_label.setFixedSize(20, 20)
        layout.addWidget(icon_label)

        # Info container
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Email
        email_label = QLabel(self.account.email)
        email_label.setObjectName("emailLabel")
        info_layout.addWidget(email_label)

        # Groups
        groups = ", ".join(self.account.groups) if self.account.groups else ("无分组" if zh else "No group")
        meta_label = QLabel(groups)
        meta_label.setObjectName("metaLabel")
        info_layout.addWidget(meta_label)

        layout.addLayout(info_layout, 1)

    def _update_checkbox_icon(self):
        t = get_theme()
        if self._checked:
            self.checkbox_label.setPixmap(icon_checkbox(20, t.success))
        else:
            self.checkbox_label.setPixmap(icon_checkbox_empty(20, t.text_tertiary))

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool):
        self._checked = checked
        self._update_checkbox_icon()

    def toggle_checked(self):
        self._checked = not self._checked
        self._update_checkbox_icon()
        if self.checked_changed:
            self.checked_changed()


class TrashDialog(QDialog):
    """Dialog for viewing and restoring deleted accounts from trash."""

    def __init__(self, parent=None, state=None, language='zh'):
        super().__init__(parent)
        self.language = language
        self.state = state
        self.selected_accounts: list[Account] = []
        self._changed = False
        self._item_widgets: dict[Account, TrashItemWidget] = {}

        self._init_ui()
        self._apply_theme()
        self._load_trash()

    def _init_ui(self):
        """Initialize the dialog UI."""
        zh = self.language == 'zh'
        self.setWindowTitle("回收站" if zh else "Trash")
        self.setMinimumSize(520, 480)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        header_icon = QLabel()
        t = get_theme()
        header_icon.setPixmap(icon_trash(24, t.text_secondary))
        header_layout.addWidget(header_icon)

        title = QLabel("回收站" if zh else "Trash")
        title.setObjectName("dialogTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Trash count badge
        self.count_badge = QLabel()
        self.count_badge.setObjectName("countBadge")
        header_layout.addWidget(self.count_badge)

        layout.addLayout(header_layout)

        # Selection info row
        select_row = QHBoxLayout()
        select_row.setSpacing(8)

        self.select_info = QLabel()
        self.select_info.setObjectName("selectInfo")
        select_row.addWidget(self.select_info)

        select_row.addStretch()

        # Select all / Deselect all
        self.btn_select_all = QPushButton("全选" if zh else "Select All")
        self.btn_select_all.setObjectName("linkBtn")
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.clicked.connect(self._select_all)
        select_row.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("取消全选" if zh else "Deselect")
        self.btn_deselect_all.setObjectName("linkBtn")
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        select_row.addWidget(self.btn_deselect_all)

        layout.addLayout(select_row)

        # Empty state container
        self.empty_container = QFrame()
        self.empty_container.setObjectName("emptyContainer")
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel()
        empty_icon.setPixmap(icon_trash(64, t.text_tertiary))
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)

        empty_title = QLabel("回收站为空" if zh else "Trash is Empty")
        empty_title.setObjectName("emptyTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel("删除的账户会显示在这里" if zh else "Deleted accounts will appear here")
        empty_desc.setObjectName("emptyDesc")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_desc)

        self.empty_container.hide()
        layout.addWidget(self.empty_container, 1)

        # Trash list
        self.trash_list = QListWidget()
        self.trash_list.setObjectName("trashList")
        self.trash_list.itemClicked.connect(self._on_item_clicked)
        self.trash_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.trash_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.trash_list, 1)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_clear_all = QPushButton("清空回收站" if zh else "Empty Trash")
        self.btn_clear_all.setObjectName("dangerGlassBtn")
        self.btn_clear_all.setIcon(QIcon(icon_trash(14, t.error)))
        self.btn_clear_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_all.clicked.connect(self._clear_all)
        btn_row.addWidget(self.btn_clear_all)

        btn_row.addStretch()

        self.btn_restore = QPushButton("恢复所选" if zh else "Restore Selected")
        self.btn_restore.setObjectName("primaryBtn")
        self.btn_restore.setIcon(QIcon(icon_refresh(14, "#FFFFFF")))
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.setEnabled(False)
        self.btn_restore.clicked.connect(self._restore_selected)
        btn_row.addWidget(self.btn_restore)

        self.btn_delete = QPushButton("永久删除" if zh else "Delete Forever")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.setIcon(QIcon(icon_close(14, t.error)))
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_row.addWidget(self.btn_delete)

        layout.addLayout(btn_row)

    def _apply_theme(self):
        """Apply current theme to dialog."""
        t = get_theme()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}
            #dialogTitle {{
                font-size: 20px;
                font-weight: 600;
                color: {t.text_primary};
            }}
            #countBadge {{
                background-color: rgba(16, 185, 129, 0.15);
                color: {t.success};
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            #selectInfo {{
                font-size: 13px;
                color: {t.text_secondary};
            }}
            #linkBtn {{
                background: transparent;
                border: none;
                color: {t.success};
                font-size: 13px;
                font-weight: 500;
                padding: 4px 8px;
            }}
            #linkBtn:hover {{
                color: #059669;
            }}
            #emptyContainer {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 12px;
            }}
            #emptyTitle {{
                font-size: 16px;
                font-weight: 600;
                color: {t.text_secondary};
                margin-top: 12px;
            }}
            #emptyDesc {{
                font-size: 13px;
                color: {t.text_tertiary};
            }}
            #trashList {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 12px;
                padding: 6px;
                outline: none;
            }}
            #trashList::item {{
                padding: 0px;
                margin: 2px 0;
                border-radius: 8px;
                background-color: transparent;
            }}
            #trashList::item:hover {{
                background-color: {t.bg_hover};
            }}
            #trashItemWidget {{
                background-color: transparent;
                border-radius: 8px;
            }}
            #emailLabel {{
                font-size: 14px;
                font-weight: 500;
                color: {t.text_primary};
            }}
            #metaLabel {{
                font-size: 12px;
                color: {t.text_tertiary};
            }}
            #dangerGlassBtn {{
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: 10px;
                padding: 10px 16px;
                color: {t.error};
                font-weight: 500;
            }}
            #dangerGlassBtn:hover {{
                background-color: rgba(239, 68, 68, 0.2);
            }}
            #dangerGlassBtn:disabled {{
                color: {t.text_tertiary};
                background-color: {t.glass_bg};
                border-color: {t.glass_border};
            }}
            #primaryBtn {{
                background-color: {t.success};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                color: white;
                font-weight: 500;
            }}
            #primaryBtn:hover {{
                background-color: #059669;
            }}
            #primaryBtn:disabled {{
                background-color: {t.bg_tertiary};
                color: {t.text_tertiary};
            }}
            #dangerBtn {{
                background-color: transparent;
                border: 1px solid {t.error};
                border-radius: 10px;
                padding: 10px 20px;
                color: {t.error};
                font-weight: 500;
            }}
            #dangerBtn:hover {{
                background-color: {t.error};
                color: white;
            }}
            #dangerBtn:disabled {{
                border-color: {t.text_tertiary};
                color: {t.text_tertiary};
            }}
        """)
        # Update button icons with theme colors
        self.btn_clear_all.setIcon(QIcon(icon_trash(14, t.error)))
        self.btn_delete.setIcon(QIcon(icon_close(14, t.error)))

    def _load_trash(self):
        """Load trash items into the list."""
        self.trash_list.clear()
        self._item_widgets.clear()
        self.selected_accounts.clear()
        zh = self.language == 'zh'

        trash_count = len(self.state.trash) if hasattr(self.state, 'trash') and self.state.trash else 0

        # Update count badge
        self.count_badge.setText(f"{trash_count} {'项' if zh else 'items'}" if trash_count > 0 else "")
        self.count_badge.setVisible(trash_count > 0)

        # Update selection info
        self._update_selection_info()

        if trash_count == 0:
            self.trash_list.hide()
            self.empty_container.show()
            self.btn_clear_all.setEnabled(False)
            self.btn_select_all.setVisible(False)
            self.btn_deselect_all.setVisible(False)
            self.select_info.setVisible(False)
            return

        self.empty_container.hide()
        self.trash_list.show()
        self.btn_clear_all.setEnabled(True)
        self.btn_select_all.setVisible(True)
        self.btn_deselect_all.setVisible(True)
        self.select_info.setVisible(True)

        for account in self.state.trash:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, account)

            # Create custom widget
            widget = TrashItemWidget(account, self.language)
            widget.checked_changed = self._on_selection_changed
            item.setSizeHint(widget.sizeHint())

            self._item_widgets[account] = widget
            self.trash_list.addItem(item)
            self.trash_list.setItemWidget(item, widget)

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click - toggle checkbox."""
        account = item.data(Qt.ItemDataRole.UserRole)
        if account and account in self._item_widgets:
            widget = self._item_widgets[account]
            widget.toggle_checked()

    def _on_selection_changed(self):
        """Update selected accounts list based on checkboxes."""
        self.selected_accounts = [
            acc for acc, widget in self._item_widgets.items()
            if widget.is_checked()
        ]
        self._update_selection_info()
        has_selection = len(self.selected_accounts) > 0
        self.btn_restore.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _update_selection_info(self):
        """Update the selection info label."""
        zh = self.language == 'zh'
        count = len(self.selected_accounts)
        if count > 0:
            self.select_info.setText(f"已选 {count} 项" if zh else f"{count} selected")
        else:
            self.select_info.setText("点击选择账户" if zh else "Click to select")

    def _select_all(self):
        """Select all items."""
        for widget in self._item_widgets.values():
            widget.set_checked(True)
        self._on_selection_changed()

    def _deselect_all(self):
        """Deselect all items."""
        for widget in self._item_widgets.values():
            widget.set_checked(False)
        self._on_selection_changed()

    def _restore_selected(self):
        """Restore all selected accounts."""
        if not self.selected_accounts:
            return

        # Move selected from trash back to accounts
        for account in self.selected_accounts:
            if account in self.state.trash:
                self.state.trash.remove(account)
                self.state.accounts.append(account)

        self._changed = True
        self._load_trash()

    def _delete_selected(self):
        """Permanently delete selected accounts."""
        if not self.selected_accounts:
            return

        zh = self.language == 'zh'
        count = len(self.selected_accounts)
        msg = f"确定要永久删除 {count} 个账户吗？此操作无法撤销。" if zh else f"Permanently delete {count} account(s)? This cannot be undone."
        reply = QMessageBox.question(self, "确认" if zh else "Confirm", msg)

        if reply == QMessageBox.StandardButton.Yes:
            for account in self.selected_accounts:
                if account in self.state.trash:
                    self.state.trash.remove(account)
            self._changed = True
            self._load_trash()

    def _clear_all(self):
        """Clear all items from trash."""
        zh = self.language == 'zh'
        if not hasattr(self.state, 'trash') or not self.state.trash:
            return

        msg = f"确定要清空回收站吗？将永久删除 {len(self.state.trash)} 个账户。" if zh else f"Empty trash? {len(self.state.trash)} accounts will be permanently deleted."
        reply = QMessageBox.question(self, "确认" if zh else "Confirm", msg)

        if reply == QMessageBox.StandardButton.Yes:
            self.state.trash.clear()
            self._changed = True
            self._load_trash()

    def has_changes(self) -> bool:
        """Check if any changes were made."""
        return self._changed

    def accept(self):
        """Accept the dialog."""
        super().accept()

    def reject(self):
        """Reject the dialog - still save changes if any."""
        if self._changed:
            super().accept()  # Use accept to trigger save
        else:
            super().reject()


class MainWindowV2(QMainWindow):
    """Main application window with modern minimal design."""

    def __init__(self):
        super().__init__()

        # Services
        self.totp_service = get_totp_service()
        self.time_service = get_time_service()
        self.theme_manager = get_theme_manager()
        self.library_service = LibraryService()
        self.archive_service = get_archive_service()

        # State
        self.state = self._load_state()
        self.selected_account: Optional[Account] = None
        self.selected_group: Optional[str] = None
        self.account_widgets: List[QFrame] = []
        self.group_buttons: List[QWidget] = []
        self.copied_toast_timer: Optional[QTimer] = None
        self.codes_visible: bool = True  # Batch show/hide state
        self.multi_select_mode: bool = False  # Multi-select mode
        self.selection_manager = SelectionManager()  # Unified selection management
        self.list_view_mode: bool = False  # False=card view, True=list view
        self.group_edit_mode: bool = False  # Group editing mode
        self.detail_edit_mode: bool = False  # Detail panel inline edit mode
        self.editable_fields: Dict[str, QLineEdit] = {}  # Editable field references
        self._pending_delete_backup: Optional[dict] = None  # For library delete undo
        self._menu_close_times: Dict[str, float] = {}  # Track menu close times

        # Setup
        self._init_window()
        self._init_ui()
        self._apply_theme()

        # Load data
        self._refresh_groups()
        self._refresh_account_list()
        if self.state.accounts:
            self.selected_account = self.state.accounts[0]
            self._update_detail_panel()

        self._start_timer()

        # Install global event filter to detect clicks outside group edit area
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

        logger.info("MainWindowV2 initialized")

    def eventFilter(self, obj, event) -> bool:
        """Handle events for click-outside detection."""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QLineEdit

        # Track library panel hide event
        if obj == self.library_panel and event.type() == QEvent.Type.Hide:
            self._menu_close_times["library_panel"] = time.time()

        # Handle click outside library panel to close it (since it's now a Tool window)
        if event.type() == QEvent.Type.MouseButtonPress and hasattr(self, 'library_panel') and self.library_panel.isVisible():
            click_pos = event.globalPosition().toPoint()
            panel_rect = self.library_panel.geometry()

            # Check if click is inside the panel
            if not panel_rect.contains(click_pos):
                # Also check if clicking on the library button itself
                if hasattr(self, 'library_btn'):
                    lib_btn_rect = self.library_btn.rect()
                    lib_btn_global = self.library_btn.mapToGlobal(lib_btn_rect.topLeft())
                    lib_btn_rect.moveTopLeft(lib_btn_global)
                    if lib_btn_rect.contains(click_pos):
                        return super().eventFilter(obj, event)

                # Click outside panel and button - close panel
                self.library_panel.hide()
                self._editing_library_id = None

        # Notes edit event handling (check both widget and viewport)
        if hasattr(self, 'notes_edit'):
            is_notes_widget = obj == self.notes_edit or obj == self.notes_edit.viewport()
            if is_notes_widget and event.type() == QEvent.Type.MouseButtonPress:
                # Schedule the click handler to run after event processing
                QTimer.singleShot(10, self._handle_notes_click)
            elif obj == self.notes_edit and event.type() == QEvent.Type.FocusOut:
                self._handle_notes_focus_out()

        # Table notes inline edit - detect click outside
        if event.type() == QEvent.Type.MouseButtonPress:
            if hasattr(self, '_table_notes_editing') and self._table_notes_editing:
                if hasattr(self, '_table_notes_edit') and self._table_notes_edit:
                    # Check if click is outside the edit widget
                    if obj != self._table_notes_edit:
                        QTimer.singleShot(0, self._finish_table_notes_edit)

        if event.type() == QEvent.Type.MouseButtonPress and self.group_edit_mode:
            # Get the widget that was clicked
            click_pos = event.globalPosition().toPoint()

            # Check if click is within groups_scroll area
            groups_rect = self.groups_scroll.rect()
            groups_global = self.groups_scroll.mapToGlobal(groups_rect.topLeft())
            groups_rect.moveTopLeft(groups_global)

            # Check if click is within edit button
            edit_btn_rect = self.btn_edit_groups.rect()
            edit_btn_global = self.btn_edit_groups.mapToGlobal(edit_btn_rect.topLeft())
            edit_btn_rect.moveTopLeft(edit_btn_global)

            # Check if currently focused widget is a QLineEdit in groups area (editing group name)
            focused = self.focusWidget()
            is_editing_name = isinstance(focused, QLineEdit) and self.groups_scroll.isAncestorOf(focused)

            if not groups_rect.contains(click_pos) and not edit_btn_rect.contains(click_pos):
                if not is_editing_name:
                    # Click is outside and not editing - exit edit mode
                    self.group_edit_mode = False
                    zh = self.state.language == 'zh'
                    self.btn_edit_groups.setText("编辑" if zh else "Edit")
                    self._save_data()
                    self._refresh_groups()

        return super().eventFilter(obj, event)

    def _load_state(self) -> AppState:
        """Load application state from current library."""
        self.library_service.initialize()
        current_library = self.library_service.get_current_library()
        state = self.library_service.load_library_state(current_library)
        logger.info(f"Loaded library: {current_library.name} ({len(state.accounts)} accounts)")
        return state

    def _init_window(self) -> None:
        """Initialize window properties."""
        self.setWindowTitle("G-Account Manager")
        self.setMinimumSize(1000, 650)
        self.resize(1200, 750)

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self._create_sidebar(main_layout)

        # Main content
        self._create_main_content(main_layout)

        # Toast
        self.toast = ToastWidget(central)

    def _create_sidebar(self, layout: QHBoxLayout) -> None:
        """Create sidebar with library selector, groups, and archive entry."""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Library selector (top)
        library_container = QWidget()
        library_container_layout = QVBoxLayout(library_container)
        library_container_layout.setContentsMargins(0, 0, 0, 0)
        library_container_layout.setSpacing(0)

        library_frame = QFrame()
        library_frame.setObjectName("libraryFrame")
        library_frame.setFixedHeight(56)  # Match header height
        library_layout = QHBoxLayout(library_frame)
        library_layout.setContentsMargins(12, 8, 12, 8)
        library_layout.setSpacing(0)

        self.btn_library = QPushButton()
        self.btn_library.setObjectName("libraryBtn")
        self.btn_library.setFixedHeight(36)
        self.btn_library.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_library.clicked.connect(self._toggle_library_panel)
        library_layout.addWidget(self.btn_library)

        library_container_layout.addWidget(library_frame)
        sidebar_layout.addWidget(library_container)

        # Floating library panel (dropdown style - fully transparent, no shadow)
        self.library_panel = QFrame(self)
        self.library_panel.setObjectName("libraryPanel")
        self.library_panel.setVisible(False)
        # Use Tool window type instead of Popup to allow proper input method switching
        self.library_panel.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.library_panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.library_panel.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)  # Allow activation for input method
        self.library_panel.setStyleSheet("QFrame#libraryPanel { background: transparent; border: none; }")
        self.library_panel.installEventFilter(self)  # Track hide events
        self.library_panel_layout = QVBoxLayout(self.library_panel)
        self.library_panel_layout.setContentsMargins(0, 4, 0, 4)
        self.library_panel_layout.setSpacing(2)

        # Groups header with title and edit button
        groups_header = QFrame()
        groups_header.setObjectName("groupsHeader")
        groups_header_layout = QHBoxLayout(groups_header)
        groups_header_layout.setContentsMargins(12, 8, 8, 4)
        groups_header_layout.setSpacing(0)

        zh = self.state.language == 'zh'
        groups_title = QLabel("分组" if zh else "Groups")
        groups_title.setObjectName("groupsTitle")
        groups_header_layout.addWidget(groups_title)

        groups_header_layout.addStretch()

        self.btn_edit_groups = QPushButton("编辑" if zh else "Edit")
        self.btn_edit_groups.setObjectName("editGroupsBtn")
        self.btn_edit_groups.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit_groups.clicked.connect(self._toggle_group_edit_mode)
        groups_header_layout.addWidget(self.btn_edit_groups)

        sidebar_layout.addWidget(groups_header)

        # Groups navigation
        self.groups_scroll = QScrollArea()
        self.groups_scroll.setObjectName("groupsScroll")
        self.groups_scroll.setWidgetResizable(True)
        self.groups_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.groups_widget = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_widget)
        self.groups_layout.setContentsMargins(8, 8, 8, 8)
        self.groups_layout.setSpacing(2)
        self.groups_layout.addStretch()

        self.groups_scroll.setWidget(self.groups_widget)
        sidebar_layout.addWidget(self.groups_scroll, 1)

        # Bottom section (trash + archive + import + add account)
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(8)

        # Import button
        self.btn_import = QPushButton()
        self.btn_import.setObjectName("importBtn")
        self.btn_import.setFixedHeight(36)
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.clicked.connect(self._show_import_dialog)
        bottom_layout.addWidget(self.btn_import)

        # Add account button
        self.btn_add_account = QPushButton()
        self.btn_add_account.setObjectName("addAccountBtn")
        self.btn_add_account.setFixedHeight(36)
        self.btn_add_account.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_account.clicked.connect(self._show_add_account)
        bottom_layout.addWidget(self.btn_add_account)

        sidebar_layout.addWidget(bottom_frame)

        layout.addWidget(self.sidebar)

    def _create_main_content(self, layout: QHBoxLayout) -> None:
        """Create main content area."""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self._create_header(main_layout)

        # Content area (account list + detail)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._create_account_list(content_layout)
        self._create_detail_panel(content_layout)

        main_layout.addWidget(content, 1)
        layout.addWidget(main_widget, 1)

    def _create_header(self, layout: QVBoxLayout) -> None:
        """Create header with search and tools."""
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(56)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)

        # Search bar - expand to fill available space
        search_container = QFrame()
        search_container.setObjectName("searchContainer")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 0, 12, 0)
        search_layout.setSpacing(8)

        self.search_icon = QLabel()
        search_layout.addWidget(self.search_icon)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)

        header_layout.addWidget(search_container, 1)  # stretch factor 1 to fill space

        # Toggle codes visibility button
        self.btn_toggle_codes = QPushButton()
        self.btn_toggle_codes.setObjectName("toolBtn")
        self.btn_toggle_codes.setFixedSize(36, 36)
        self.btn_toggle_codes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_codes.clicked.connect(self._toggle_codes_visibility)
        header_layout.addWidget(self.btn_toggle_codes)

        # Tools
        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("toolBtn")
        self.btn_theme.setFixedSize(36, 36)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.btn_theme)

        self.btn_language = QPushButton()
        self.btn_language.setObjectName("toolBtn")
        self.btn_language.setFixedSize(36, 36)
        self.btn_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_language.clicked.connect(self._toggle_language)
        header_layout.addWidget(self.btn_language)

        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("toolBtn")
        self.btn_settings.setFixedSize(36, 36)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self._show_settings_menu)
        header_layout.addWidget(self.btn_settings)

        layout.addWidget(header)

    def _create_account_list(self, layout: QHBoxLayout) -> None:
        """Create account list panel."""
        self.list_panel = QFrame()
        self.list_panel.setObjectName("accountListPanel")
        self.list_panel.setFixedWidth(320)
        self.list_panel.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.list_panel.mousePressEvent = self._on_detail_panel_click

        list_layout = QVBoxLayout(self.list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # Header with title and action buttons
        list_header = QFrame()
        list_header.setObjectName("listHeader")
        list_header.setFixedHeight(44)
        header_layout = QHBoxLayout(list_header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        header_layout.setSpacing(4)

        self.list_title = QLabel()
        self.list_title.setObjectName("listTitle")
        header_layout.addWidget(self.list_title)

        header_layout.addStretch()

        # Multi-select toggle button
        self.btn_multi_select = QPushButton()
        self.btn_multi_select.setObjectName("listToolBtn")
        self.btn_multi_select.setFixedSize(28, 28)
        self.btn_multi_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_multi_select.clicked.connect(self._toggle_multi_select)
        header_layout.addWidget(self.btn_multi_select)

        # View toggle button (list/card)
        self.btn_view_toggle = QPushButton()
        self.btn_view_toggle.setObjectName("listToolBtn")
        self.btn_view_toggle.setFixedSize(28, 28)
        self.btn_view_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_toggle.clicked.connect(self._toggle_view_mode)
        header_layout.addWidget(self.btn_view_toggle)

        list_layout.addWidget(list_header)

        # Batch action bar (shown when multi-select mode is active) - placed at top
        self.batch_action_bar = QFrame()
        self.batch_action_bar.setObjectName("batchActionBar")
        self.batch_action_bar.setFixedHeight(44)
        self.batch_action_bar.setVisible(False)

        batch_layout = QHBoxLayout(self.batch_action_bar)
        batch_layout.setContentsMargins(12, 0, 12, 0)  # Match list item margins
        batch_layout.setSpacing(6)  # Match list item spacing

        # Select all icon button
        self.select_all_btn = QToolButton()
        self.select_all_btn.setObjectName("selectAllBtn")
        self.select_all_btn.setFixedSize(20, 20)
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.setStyleSheet("QToolButton { background: transparent; border: none; }")
        self.select_all_btn.clicked.connect(self._on_select_all_btn_clicked)
        batch_layout.addWidget(self.select_all_btn)

        self.batch_select_label = QLabel()
        self.batch_select_label.setObjectName("batchSelectLabel")
        batch_layout.addWidget(self.batch_select_label)

        batch_layout.addStretch()

        # Batch add to group button
        self.btn_batch_add_group = QPushButton()
        self.btn_batch_add_group.setObjectName("batchAddGroupBtn")
        self.btn_batch_add_group.setFixedSize(28, 28)
        self.btn_batch_add_group.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_add_group.clicked.connect(self._show_batch_add_group_menu)
        batch_layout.addWidget(self.btn_batch_add_group)

        # Batch remove from group button
        self.btn_batch_remove_group = QPushButton()
        self.btn_batch_remove_group.setObjectName("batchRemoveGroupBtn")
        self.btn_batch_remove_group.setFixedSize(28, 28)
        self.btn_batch_remove_group.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_remove_group.clicked.connect(self._show_batch_remove_group_menu)
        batch_layout.addWidget(self.btn_batch_remove_group)

        # Batch copy button
        self.btn_batch_copy = QPushButton()
        self.btn_batch_copy.setObjectName("batchCopyBtn")
        self.btn_batch_copy.setFixedSize(28, 28)
        self.btn_batch_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_copy.clicked.connect(self._batch_copy)
        batch_layout.addWidget(self.btn_batch_copy)

        # Batch move to library button
        self.btn_batch_move_library = QPushButton()
        self.btn_batch_move_library.setObjectName("batchMoveLibraryBtn")
        self.btn_batch_move_library.setFixedSize(28, 28)
        self.btn_batch_move_library.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_move_library.clicked.connect(self._show_batch_move_library_menu)
        batch_layout.addWidget(self.btn_batch_move_library)

        # Batch delete button
        self.btn_batch_delete = QPushButton()
        self.btn_batch_delete.setObjectName("batchDeleteBtn")
        self.btn_batch_delete.setFixedSize(28, 28)
        self.btn_batch_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_delete.clicked.connect(self._batch_delete)
        batch_layout.addWidget(self.btn_batch_delete)

        list_layout.addWidget(self.batch_action_bar)

        # Scroll area with bounce effect on wheel (Card View)
        self.card_view_scroll = BounceScrollArea()
        self.card_view_scroll.setObjectName("accountScroll")
        self.card_view_scroll.setWidgetResizable(True)
        self.card_view_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.account_list_widget = QWidget()
        self.account_list_layout = QVBoxLayout(self.account_list_widget)
        self.account_list_layout.setContentsMargins(0, 0, 0, 0)
        self.account_list_layout.setSpacing(0)
        self.account_list_layout.addStretch()

        self.card_view_scroll.setWidget(self.account_list_widget)
        list_layout.addWidget(self.card_view_scroll, 1)

        # Table view (List View) with bounce effect
        self.table_view = BounceTableWidget()
        self.table_view.setObjectName("accountTable")
        self.table_view.setColumnCount(8)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setFrameShape(QFrame.Shape.NoFrame)
        self.table_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(36)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.cellClicked.connect(self._on_table_cell_clicked)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_table_context_menu)
        self.selected_table_row = -1  # Track selected row in table view

        # Configure table header
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID/Checkbox
        self.table_view.setColumnWidth(0, 50)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Email
        self.table_view.setColumnWidth(1, 200)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Password
        self.table_view.setColumnWidth(2, 120)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Backup
        self.table_view.setColumnWidth(3, 140)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # 2FA Key
        self.table_view.setColumnWidth(4, 100)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Code
        self.table_view.setColumnWidth(5, 80)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Groups - stretch to fill
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Notes
        self.table_view.setColumnWidth(7, 120)

        # Set row height
        self.table_view.verticalHeader().setDefaultSectionSize(36)

        self.table_view.hide()  # Initially hidden (card view is default)
        list_layout.addWidget(self.table_view, 1)

        layout.addWidget(self.list_panel)

    def _create_detail_panel(self, layout: QHBoxLayout) -> None:
        """Create detail panel."""
        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("detailPanel")
        self.detail_panel.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.detail_panel.mousePressEvent = self._on_detail_panel_click

        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(0)

        # Empty state - centered in the entire detail panel
        self.empty_state = QLabel()
        self.empty_state.setObjectName("emptyState")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Scrollable area for detail content (bottom bounce only)
        self.detail_scroll = BounceScrollArea(bottom_only=True)
        self.detail_scroll.setObjectName("detailScroll")
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Scroll area background will be set in _apply_theme for proper dark mode support

        # Scroll container widget - transparent to inherit parent background
        scroll_container = QWidget()
        scroll_container.setObjectName("detailScrollContainer")
        scroll_container.setStyleSheet("background: transparent;")
        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(24, 24, 24, 24)
        scroll_container_layout.setSpacing(0)

        # Content wrapper for detail content
        self.content_wrapper = QWidget()
        self.content_wrapper.setObjectName("contentWrapper")
        self.content_wrapper.setStyleSheet("background: transparent;")
        self.content_wrapper.setMaximumWidth(520)
        content_layout = QVBoxLayout(self.content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Detail content
        self.detail_content = QWidget()
        self.detail_content.setStyleSheet("background: transparent;")
        self.detail_content.setVisible(False)
        detail_content_layout = QVBoxLayout(self.detail_content)
        detail_content_layout.setContentsMargins(0, 0, 0, 0)
        detail_content_layout.setSpacing(24)

        # Account header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        self.detail_name = QLabel()
        self.detail_name.setObjectName("detailName")
        header_text.addWidget(self.detail_name)
        self.detail_email = QLabel()
        self.detail_email.setObjectName("detailEmail")
        header_text.addWidget(self.detail_email)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName("iconBtn")
        self.btn_edit.setFixedSize(32, 32)
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.clicked.connect(self._edit_account)
        header_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton()
        self.btn_delete.setObjectName("deleteBtn")
        self.btn_delete.setFixedSize(32, 32)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.clicked.connect(self._delete_account)
        header_layout.addWidget(self.btn_delete)

        detail_content_layout.addWidget(header_widget)

        # Separator
        sep1 = QFrame()
        sep1.setObjectName("separator")
        sep1.setFixedHeight(1)
        detail_content_layout.addWidget(sep1)

        # Fields container (email, password, secret, groups, notes)
        self.fields_container = QWidget()
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(16)
        detail_content_layout.addWidget(self.fields_container)

        # TOTP Section (at the bottom)
        self.totp_section = QWidget()
        totp_layout = QVBoxLayout(self.totp_section)
        totp_layout.setContentsMargins(0, 0, 0, 0)
        totp_layout.setSpacing(8)

        self.totp_label = QLabel()
        self.totp_label.setObjectName("fieldLabel")
        totp_layout.addWidget(self.totp_label)

        totp_row = QHBoxLayout()
        totp_row.setSpacing(12)

        self.totp_display = QLabel("--- ---")
        self.totp_display.setObjectName("totpDisplay")
        self.totp_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        totp_row.addWidget(self.totp_display, 1)

        self.btn_copy_totp = QPushButton()
        self.btn_copy_totp.setObjectName("copyBtn")
        self.btn_copy_totp.setFixedSize(36, 36)
        self.btn_copy_totp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_totp.clicked.connect(self._copy_totp_code)
        totp_row.addWidget(self.btn_copy_totp)

        totp_layout.addLayout(totp_row)

        # Progress bar
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        self.totp_progress = QProgressBar()
        self.totp_progress.setObjectName("totpProgress")
        self.totp_progress.setTextVisible(False)
        self.totp_progress.setFixedHeight(4)
        self.totp_progress.setRange(0, 30)
        progress_row.addWidget(self.totp_progress, 1)

        self.totp_timer = QLabel("30s")
        self.totp_timer.setObjectName("totpTimer")
        self.totp_timer.setFixedWidth(32)
        self.totp_timer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.totp_timer)

        totp_layout.addLayout(progress_row)
        detail_content_layout.addWidget(self.totp_section)

        # Notes section (below TOTP)
        self.notes_section = QWidget()
        notes_layout = QVBoxLayout(self.notes_section)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        notes_layout.setSpacing(6)

        self.notes_label = QLabel()
        self.notes_label.setObjectName("fieldLabel")
        notes_layout.addWidget(self.notes_label)

        self.notes_edit = QTextEdit()
        self.notes_edit.setObjectName("notesEdit")
        self.notes_edit.setReadOnly(True)
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setMaximumHeight(300)
        self.notes_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        # Use event filter on viewport for click handling
        self.notes_edit.viewport().installEventFilter(self)
        self.notes_edit.installEventFilter(self)
        notes_layout.addWidget(self.notes_edit)

        detail_content_layout.addWidget(self.notes_section)

        detail_content_layout.addStretch()
        content_layout.addWidget(self.detail_content)

        # Add content_wrapper to scroll container
        scroll_container_layout.addWidget(self.content_wrapper)
        scroll_container_layout.addStretch()

        # Set scroll container as scroll area widget
        self.detail_scroll.setWidget(scroll_container)

        # Empty state container - centered vertically
        self.empty_container = QWidget()
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_state, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()

        # Add both containers to detail layout (mutually exclusive)
        detail_layout.addWidget(self.empty_container)
        detail_layout.addWidget(self.detail_scroll)

        layout.addWidget(self.detail_panel, 1)

    def _apply_theme(self) -> None:
        """Apply current theme."""
        t = get_theme()
        is_dark = get_theme_manager().is_dark

        # Library button colors: light mode = pure black, dark mode = softer gray
        lib_btn_bg = "#9CA3AF" if is_dark else t.text_primary
        lib_btn_hover = "#D1D5DB" if is_dark else t.text_secondary

        # Bottom buttons colors: dark mode = visible background, light mode = transparent
        bottom_btn_bg = t.bg_tertiary if is_dark else t.bg_primary
        bottom_btn_hover = "#4B5563" if is_dark else t.bg_hover

        # Green selection color
        selection_bg = "#065F46" if is_dark else "#10B981"
        selection_color = "#FFFFFF"

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {t.bg_primary};
            }}

            /* Global text selection color (green) */
            QLineEdit {{
                selection-background-color: {selection_bg};
                selection-color: {selection_color};
            }}
            QTextEdit {{
                selection-background-color: {selection_bg};
                selection-color: {selection_color};
            }}
            QPlainTextEdit {{
                selection-background-color: {selection_bg};
                selection-color: {selection_color};
            }}

            /* Sidebar */
            #sidebar {{
                background-color: {t.bg_secondary};
                border-right: 1px solid {t.border};
            }}

            #libraryFrame {{
                background-color: {t.bg_secondary};
                border-bottom: 1px solid {t.border};
            }}

            #libraryBtn {{
                background-color: {lib_btn_bg};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
                color: {t.bg_primary};
            }}
            #libraryBtn:hover {{
                background-color: {lib_btn_hover};
            }}

            #libraryPanel {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
            }}

            .libraryCard {{
                background-color: {t.bg_secondary};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
                color: {lib_btn_bg};
            }}
            .libraryCard:hover {{
                background-color: {t.bg_hover};
            }}

            .libraryCardInactive {{
                background-color: {lib_btn_bg};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
                color: {t.bg_primary};
            }}
            .libraryCardInactive:hover {{
                background-color: {lib_btn_hover};
            }}

            #groupsScroll {{
                background-color: {t.bg_secondary};
                border: none;
            }}
            #groupsScroll > QWidget > QWidget {{
                background-color: {t.bg_secondary};
            }}

            #groupsHeader {{
                background-color: {t.bg_secondary};
            }}

            #groupsTitle {{
                font-size: 11px;
                font-weight: 600;
                color: {t.text_secondary};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            #editGroupsBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
                color: {t.text_secondary};
            }}
            #editGroupsBtn:hover {{
                background-color: {t.bg_hover};
                color: {t.text_primary};
            }}

            #bottomFrame {{
                background-color: {t.bg_secondary};
                border-top: 1px solid {t.border};
            }}

            #importBtn {{
                background-color: {bottom_btn_bg};
                border: 1px solid {t.border};
                border-radius: 6px;
                color: {t.text_secondary};
                font-size: 13px;
            }}
            #importBtn:hover {{
                background-color: {bottom_btn_hover};
                border-color: {t.text_tertiary};
                color: {t.text_primary};
            }}

            #addAccountBtn {{
                background-color: {bottom_btn_bg};
                border: 1px solid {t.border};
                border-radius: 6px;
                color: {t.text_secondary};
                font-weight: 500;
                font-size: 13px;
            }}
            #addAccountBtn:hover {{
                background-color: {bottom_btn_hover};
                border-color: {t.text_tertiary};
                color: {t.text_primary};
            }}

            /* Header */
            #header {{
                background-color: {t.bg_primary};
                border-bottom: 1px solid {t.border};
            }}

            #searchContainer {{
                background-color: {t.bg_secondary};
                border: none;
                border-bottom: 1px solid {t.border};
                border-radius: 0px;
                height: 36px;
            }}
            #searchContainer:hover {{
                background-color: {t.bg_tertiary};
            }}
            #searchContainer:focus-within {{
                background-color: {t.bg_tertiary};
            }}

            #searchInput {{
                background: transparent;
                border: none;
                font-size: 13px;
                color: {t.text_primary};
            }}

            #listToolBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            #listToolBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #batchActionBar {{
                background-color: {t.bg_secondary};
                border-top: 1px solid {t.border};
            }}
            #batchSelectLabel {{
                font-size: 12px;
                color: {t.text_secondary};
            }}
            #batchAddGroupBtn, #batchRemoveGroupBtn, #batchCopyBtn, #batchMoveLibraryBtn, #batchDeleteBtn {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            #batchAddGroupBtn:hover, #batchRemoveGroupBtn:hover, #batchCopyBtn:hover, #batchMoveLibraryBtn:hover {{
                background-color: {t.bg_hover};
            }}
            #batchDeleteBtn:hover {{
                background-color: {t.error}15;
            }}

            #toolBtn {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            #toolBtn:hover {{
                background-color: {t.bg_hover};
            }}

            /* Account List */
            #accountListPanel {{
                background-color: {t.bg_primary};
                border-right: 1px solid {t.border};
            }}

            #listHeader {{
                background-color: {t.bg_primary};
                border-bottom: 1px solid {t.border};
            }}

            #listTitle {{
                font-size: 11px;
                font-weight: 500;
                color: {t.text_tertiary};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            #accountScroll {{
                background-color: {t.bg_primary};
                border: none;
            }}
            #accountScroll > QWidget > QWidget {{
                background-color: {t.bg_primary};
            }}

            /* Table View */
            #accountTable {{
                background-color: {t.bg_primary};
                border: none;
                gridline-color: transparent;
                outline: none;
            }}
            #accountTable QHeaderView::section {{
                background-color: {t.bg_primary};
                color: {t.text_tertiary};
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid {t.border};
                font-weight: 600;
                font-size: 11px;
            }}

            /* Detail Panel */
            #detailPanel {{
                background-color: {t.bg_primary};
            }}

            #emptyState {{
                font-size: 14px;
                color: {t.text_tertiary};
            }}

            #detailName {{
                font-size: 20px;
                font-weight: 600;
                color: {t.text_primary};
            }}

            #detailEmail {{
                font-size: 13px;
                color: {t.text_secondary};
            }}

            #iconBtn {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            #iconBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #deleteBtn {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            #deleteBtn:hover {{
                background-color: {t.error}20;
            }}

            #separator {{
                background-color: {t.border};
            }}

            #fieldLabel {{
                font-size: 11px;
                font-weight: 500;
                color: {t.text_tertiary};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            #totpDisplay {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 20px;
                font-weight: 600;
                color: {t.success};
                letter-spacing: 3px;
            }}

            #copyBtn {{
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }}
            #copyBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #totpProgress {{
                background-color: {t.bg_tertiary};
                border: none;
                border-radius: 2px;
            }}
            #totpProgress::chunk {{
                background-color: {t.success};
                border-radius: 2px;
            }}

            #totpTimer {{
                font-size: 11px;
                color: {t.text_tertiary};
            }}

            #notesEdit {{
                background-color: transparent;
                border: none;
                color: {t.text_secondary};
                font-size: 13px;
                padding: 4px 0;
            }}
            #notesEdit:focus {{
                background-color: transparent;
                border: none;
            }}

            /* Toast - iOS-style glassmorphism */
            /* Light mode: dark glass with white text, Dark mode: light glass with dark text */
            #toast {{
                background-color: {"rgba(250, 250, 250, 0.82)" if is_dark else "rgba(30, 30, 30, 0.82)"};
                padding: 10px 20px;
                border-radius: 12px;
                border: 1px solid {"rgba(255, 255, 255, 0.25)" if is_dark else "rgba(255, 255, 255, 0.08)"};
                font-size: 13px;
            }}
            #toast QLabel {{
                background: transparent;
                color: {"#1F2937" if is_dark else "#FFFFFF"};
                font-weight: 500;
            }}
            #toast QPushButton {{
                background: transparent;
                border: none;
                color: {"#10B981" if is_dark else "#6EE7B7"};
                font-weight: 600;
                padding: 0 4px;
            }}
            #toast QPushButton:hover {{
                color: {"#059669" if is_dark else "#A7F3D0"};
            }}

            /* Scrollbar */
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t.text_tertiary};
                border-radius: 3px;
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

            QLineEdit {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: {t.text_primary};
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
            }}

            /* Menu */
            QMenu {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t.border};
                margin: 4px 8px;
            }}
        """)

        # Ensure detail scroll area uses theme background color for dark mode
        self.detail_scroll.setStyleSheet(f"QScrollArea {{ background-color: {t.bg_primary}; border: none; }}")
        self.detail_scroll.viewport().setStyleSheet(f"background-color: {t.bg_primary};")

        self._update_icons()
        self._update_ui_text()

    def _update_icons(self) -> None:
        """Update all icons for current theme."""
        t = get_theme()
        ic = t.text_secondary

        # Library button - just show library name
        current = self.library_service.get_current_library()
        self.btn_library.setIcon(QIcon(icon_library(16, t.bg_primary)))
        self.btn_library.setText(f"  {current.name}  ")

        # Search
        self.search_icon.setPixmap(icon_search(16, t.text_tertiary))

        # Multi-select button (in list header) - green when active
        self.btn_multi_select.setIcon(QIcon(icon_checkbox(14, t.success if self.multi_select_mode else ic)))

        # View toggle button (in list header)
        if self.list_view_mode:
            self.btn_view_toggle.setIcon(QIcon(icon_grid(14, ic)))
        else:
            self.btn_view_toggle.setIcon(QIcon(icon_list(14, ic)))

        # Toggle codes button
        if self.codes_visible:
            self.btn_toggle_codes.setIcon(QIcon(icon_eye(18, ic)))
        else:
            self.btn_toggle_codes.setIcon(QIcon(icon_eye_off(18, ic)))

        # Theme button
        if self.theme_manager.is_dark:
            self.btn_theme.setIcon(QIcon(icon_sun(18, ic)))
        else:
            self.btn_theme.setIcon(QIcon(icon_moon(18, ic)))

        # Language & Settings
        from .icons import icon_globe
        self.btn_language.setIcon(QIcon(icon_globe(18, ic)))
        self.btn_settings.setIcon(QIcon(icon_settings(18, ic)))

        # Import button
        self.btn_import.setIcon(QIcon(icon_import(16, ic)))

        # Add account - icon color matches text color
        self.btn_add_account.setIcon(QIcon(icon_plus(16, t.text_secondary)))

        # Detail panel
        self.btn_edit.setIcon(QIcon(icon_edit(16, ic)))
        self.btn_delete.setIcon(QIcon(icon_trash(16, t.error)))
        self.btn_copy_totp.setIcon(QIcon(icon_copy(18, ic)))

        # Batch action buttons
        self.btn_batch_add_group.setIcon(QIcon(icon_square_plus(14, ic)))
        self.btn_batch_remove_group.setIcon(QIcon(icon_square_minus(14, ic)))
        self.btn_batch_copy.setIcon(QIcon(icon_copy(14, ic)))
        self.btn_batch_move_library.setIcon(QIcon(icon_library_move(14, ic)))
        self.btn_batch_delete.setIcon(QIcon(icon_trash(14, t.error)))

    def _update_ui_text(self) -> None:
        """Update all UI text for current language."""
        lang = self.state.language
        zh = lang == 'zh'

        self.search_input.setPlaceholderText("搜索账户..." if zh else "Search accounts...")
        self.btn_import.setText("  批量导入" if zh else "  Batch Import")
        self.btn_add_account.setText("  添加账户" if zh else "  Add Account")
        self.empty_state.setText("选择一个账户查看详情" if zh else "Select an account to view details")
        self.totp_label.setText("验证码" if zh else "Verification Code")

    def _toggle_library_panel(self) -> None:
        """Toggle library panel visibility."""
        # Check if panel was just closed (prevents re-open when clicking to close)
        if not self._should_show_menu("library_panel"):
            return

        if self.library_panel.isVisible():
            self.library_panel.hide()
            self._editing_library_id = None
            return

        self._editing_library_id = None
        self._refresh_library_panel()

        # Position below the library button, aligned with sidebar
        btn_pos = self.btn_library.mapToGlobal(self.btn_library.rect().bottomLeft())
        self.library_panel.move(btn_pos)
        self.library_panel.show()

    def _refresh_library_panel(self) -> None:
        """Refresh library panel with cards."""
        # Clear existing
        while self.library_panel_layout.count():
            item = self.library_panel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t = get_theme()
        zh = self.state.language == 'zh'
        libraries = self.library_service.list_libraries()
        current = self.library_service.get_current_library()

        # Calculate width based on whether we're in edit mode
        card_width = self.btn_library.width()
        editing_id = getattr(self, '_editing_library_id', None)

        for idx, lib in enumerate(libraries):
            is_current = lib.id == current.id
            is_editing = lib.id == editing_id
            row = self._create_library_row(lib, is_current, is_editing, idx, len(libraries), card_width)
            self.library_panel_layout.addWidget(row)

        # Add new library button or show new card if in create mode
        if hasattr(self, '_creating_new_library') and self._creating_new_library:
            new_row = self._create_new_library_row(card_width)
            self.library_panel_layout.addWidget(new_row)
            self._creating_new_library = False
        else:
            add_btn = QPushButton("+ " + ("新建账号库" if zh else "New Library"))
            add_btn.setFixedWidth(card_width)
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_dark = get_theme_manager().is_dark
            # Green colors: darker for dark mode, brighter for light mode
            green_bg = "#065F46" if is_dark else "#10B981"
            green_hover = "#047857" if is_dark else "#059669"
            add_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {green_bg};
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 13px;
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {green_hover};
                }}
            """)
            add_btn.clicked.connect(self._start_new_library)
            self.library_panel_layout.addWidget(add_btn)

    def _create_library_row(self, lib, is_current: bool, is_editing: bool, idx: int, total: int, card_width: int) -> QFrame:
        """Create a library row with card and floating buttons."""
        from .icons import icon_library, icon_edit
        t = get_theme()
        is_dark = get_theme_manager().is_dark
        zh = self.state.language == 'zh'

        # Button colors: light mode = pure black, dark mode = softer gray
        btn_bg = "#9CA3AF" if is_dark else t.text_primary
        btn_hover = "#D1D5DB" if is_dark else t.text_secondary

        # Edit mode colors: darker for dark mode to avoid being too bright
        success_color = "#059669" if is_dark else t.success
        success_hover = "#047857" if is_dark else "#059669"
        error_color = "#DC2626" if is_dark else t.error
        error_hover = "#B91C1C" if is_dark else "#DC2626"
        selection_color = "#047857" if is_dark else t.success

        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Main card - all cards are black, only selected one is white
        card = QFrame()
        card.setFixedWidth(card_width)
        card.setFixedHeight(36)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 0, 12, 0)
        card_layout.setSpacing(10)

        # Card style: selected = slightly different from bg for visibility
        if is_current:
            # Selected: darker in dark mode, deeper gray in light mode
            selected_bg = "#4B5563" if is_dark else "#D1D5DB"
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {selected_bg};
                    border: none;
                    border-radius: 6px;
                }}
            """)
            text_color = t.text_primary
            icon_color = t.text_secondary
        else:
            # Not selected: same color as library button
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {btn_bg};
                    border: none;
                    border-radius: 6px;
                }}
                QFrame:hover {{
                    background-color: {btn_hover};
                }}
            """)
            text_color = t.bg_primary
            icon_color = t.bg_secondary

        # Library icon - transparent background
        icon_label = QLabel()
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setPixmap(icon_library(16, text_color))
        card_layout.addWidget(icon_label)

        if is_editing:
            # Edit mode: show input field with green selection highlight
            name_input = QLineEdit(lib.name)
            name_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: transparent;
                    border: none;
                    font-size: 13px;
                    font-weight: 500;
                    color: {text_color};
                    selection-background-color: {selection_color};
                    selection-color: white;
                }}
            """)
            name_input.selectAll()
            card_layout.addWidget(name_input, 1)
            # Store for later use
            row.name_input = name_input
        else:
            # Normal mode: show label - transparent background
            name_label = QLabel(lib.name)
            name_label.setStyleSheet(f"""
                background: transparent;
                font-size: 13px;
                font-weight: 500;
                color: {text_color};
            """)
            card_layout.addWidget(name_label, 1)

        # Click on card = switch library (only in non-edit mode)
        if not is_editing:
            card.mousePressEvent = lambda e: self._on_library_card_click(lib)
        row_layout.addWidget(card)

        # Edit/Confirm button - black when not editing, green when editing
        edit_btn = QPushButton()
        edit_btn.setFixedSize(36, 36)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if is_editing:
            # Green confirm button
            edit_btn.setText("✓")
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {success_color};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {success_hover};
                }}
            """)
        else:
            # Edit button - use softer color in dark mode
            edit_btn.setIcon(QIcon(icon_edit(14, t.bg_primary)))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
            """)

        edit_btn.clicked.connect(lambda: self._toggle_library_edit(lib.id))
        row_layout.addWidget(edit_btn)

        # Action buttons (only visible when editing)
        if is_editing:
            # Up button - softer color in dark mode
            up_btn = QPushButton()
            up_btn.setFixedSize(36, 36)
            up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            up_btn.setText("↑")
            up_btn.setEnabled(idx > 0)
            up_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                    color: {t.bg_primary if idx > 0 else t.bg_secondary};
                }}
                QPushButton:hover:enabled {{
                    background-color: {btn_hover};
                }}
            """)
            up_btn.clicked.connect(lambda: self._reorder_library(lib.id, -1))
            row_layout.addWidget(up_btn)

            # Down button - softer color in dark mode
            down_btn = QPushButton()
            down_btn.setFixedSize(36, 36)
            down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            down_btn.setText("↓")
            down_btn.setEnabled(idx < total - 1)
            down_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: bold;
                    color: {t.bg_primary if idx < total - 1 else t.bg_secondary};
                }}
                QPushButton:hover:enabled {{
                    background-color: {btn_hover};
                }}
            """)
            down_btn.clicked.connect(lambda: self._reorder_library(lib.id, 1))
            row_layout.addWidget(down_btn)

            # Delete button - red, square (only if more than one library)
            if total > 1:
                del_btn = QPushButton()
                del_btn.setFixedSize(36, 36)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setText("×")
                del_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {error_color};
                        border: none;
                        border-radius: 6px;
                        font-size: 16px;
                        font-weight: bold;
                        color: white;
                    }}
                    QPushButton:hover {{
                        background-color: {error_hover};
                    }}
                """)
                del_btn.clicked.connect(lambda: self._confirm_delete_library(lib))
                row_layout.addWidget(del_btn)

            # Store input reference and focus it
            self._editing_input = name_input
            QTimer.singleShot(50, name_input.setFocus)

        return row

    def _confirm_library_rename(self, lib, row) -> None:
        """Confirm renaming a library."""
        if hasattr(row, 'name_input'):
            new_name = row.name_input.text().strip()
            if new_name and new_name != lib.name:
                self.library_service.rename_library(lib.id, new_name)
                self._update_icons()
        self._editing_library_id = None
        self._refresh_library_panel()

    def _create_new_library_row(self, card_width: int) -> QFrame:
        """Create a row for new library input."""
        from .icons import icon_library
        t = get_theme()
        is_dark = get_theme_manager().is_dark
        zh = self.state.language == 'zh'

        # Button colors: light mode = pure black, dark mode = softer gray
        btn_bg = "#9CA3AF" if is_dark else t.text_primary
        btn_hover = "#D1D5DB" if is_dark else t.text_secondary

        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Main card with input - softer color in dark mode
        card = QFrame()
        card.setFixedWidth(card_width)
        card.setFixedHeight(36)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {btn_bg};
                border: none;
                border-radius: 6px;
            }}
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 0, 12, 0)
        card_layout.setSpacing(10)

        # Library icon - white for black background
        icon_label = QLabel()
        icon_label.setPixmap(icon_library(16, t.bg_primary))
        card_layout.addWidget(icon_label)

        # Name input - white text for black background
        name_input = QLineEdit()
        name_input.setPlaceholderText("输入名称..." if zh else "Enter name...")
        name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                border: none;
                font-size: 13px;
                font-weight: 500;
                color: {t.bg_primary};
            }}
            QLineEdit::placeholder {{
                color: {t.bg_secondary};
            }}
        """)
        card_layout.addWidget(name_input, 1)
        row_layout.addWidget(card)

        # Confirm button - softer color in dark mode
        confirm_btn = QPushButton()
        confirm_btn.setFixedSize(36, 36)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setText("✓")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: {t.bg_primary};
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        confirm_btn.clicked.connect(lambda: self._confirm_new_library(name_input))
        name_input.returnPressed.connect(lambda: self._confirm_new_library(name_input))
        row_layout.addWidget(confirm_btn)

        # Cancel button - softer color in dark mode
        cancel_btn = QPushButton()
        cancel_btn.setFixedSize(36, 36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setText("×")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                border: none;
                border-radius: 6px;
                font-size: 16px;
                color: {t.bg_secondary};
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {t.bg_primary};
            }}
        """)
        cancel_btn.clicked.connect(self._refresh_library_panel)
        row_layout.addWidget(cancel_btn)

        # Focus input after display
        QTimer.singleShot(100, name_input.setFocus)

        return row

    def _on_library_card_click(self, lib) -> None:
        """Handle click on library card."""
        self._switch_library(lib.id)
        self.library_panel.hide()

    def _toggle_library_edit(self, library_id: str) -> None:
        """Toggle edit mode for a library."""
        # If closing edit mode, save any rename first
        if getattr(self, '_editing_library_id', None) == library_id:
            # Save rename if there's an input with changes
            if hasattr(self, '_editing_input') and self._editing_input:
                new_name = self._editing_input.text().strip()
                lib = self.library_service.get_library_by_id(library_id)
                if lib and new_name and new_name != lib.name:
                    self.library_service.rename_library(library_id, new_name)
                    self._update_icons()
            self._editing_library_id = None
            self._editing_input = None
        else:
            self._editing_library_id = library_id
        self._refresh_library_panel()

    def _confirm_new_library(self, name_input: QLineEdit) -> None:
        """Confirm creating a new library."""
        name = name_input.text().strip()
        zh = self.state.language == 'zh'

        # Use default name if empty
        if not name:
            base_name = "新建账号库" if zh else "New Library"
            name = base_name
            counter = 1
            libraries = self.library_service.list_libraries()
            existing_names = {lib.name for lib in libraries}
            while name in existing_names:
                counter += 1
                name = f"{base_name} ({counter})"
        else:
            # Check for duplicate name
            libraries = self.library_service.list_libraries()
            if any(lib.name == name for lib in libraries):
                self.toast.show_message("账号库名称已存在" if zh else "Library name already exists")
                return

        new_lib = self.library_service.create_library(name)
        self._refresh_library_panel()
        self.toast.show_message(f"已创建「{name}」" if zh else f"Created '{name}'")

    def _show_delete_confirmation(self, message: str) -> bool:
        """Show styled delete confirmation dialog matching library panel colors.

        Returns True if user confirms, False otherwise.
        """
        t = get_theme()
        is_dark = get_theme_manager().is_dark
        zh = self.state.language == 'zh'

        # Dark mode: use colors matching library panel (softer grays)
        # Light mode: use standard theme colors
        dialog_bg = "#374151" if is_dark else t.bg_primary
        text_color = "#F3F4F6" if is_dark else t.text_primary
        cancel_bg = "#4B5563" if is_dark else t.bg_tertiary
        cancel_hover = "#6B7280" if is_dark else t.bg_hover
        error_color = "#DC2626" if is_dark else t.error
        error_hover = "#B91C1C" if is_dark else "#DC2626"

        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除" if zh else "Confirm Delete")
        dialog.setFixedWidth(320)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {dialog_bg};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
                font-size: 13px;
            }}
            QPushButton {{
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("取消" if zh else "Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cancel_bg};
                border: none;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {cancel_hover};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("删除" if zh else "Delete")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {error_color};
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {error_hover};
            }}
        """)
        delete_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _confirm_delete_library(self, lib) -> None:
        """Show styled delete confirmation."""
        t = get_theme()
        is_dark = get_theme_manager().is_dark
        zh = self.state.language == 'zh'

        # Get account count for this library
        if lib.id == self.library_service.get_current_library().id:
            account_count = len(self.state.accounts)
        else:
            state = self.library_service.load_library_state(lib)
            account_count = len(state.accounts)

        # Dark mode: use colors matching library panel (softer grays)
        # Light mode: use standard theme colors
        dialog_bg = "#374151" if is_dark else t.bg_primary
        text_color = "#F3F4F6" if is_dark else t.text_primary
        cancel_bg = "#4B5563" if is_dark else t.bg_tertiary
        cancel_hover = "#6B7280" if is_dark else t.bg_hover
        error_color = "#DC2626" if is_dark else t.error
        error_hover = "#B91C1C" if is_dark else "#DC2626"

        # Create styled dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除" if zh else "Confirm Delete")
        dialog.setFixedWidth(320)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {dialog_bg};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
                font-size: 13px;
            }}
            QPushButton {{
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Message
        msg = f"确定要删除账号库「{lib.name}」吗？" if zh else f"Delete library '{lib.name}'?"
        if account_count > 0:
            msg += f"\n\n{account_count} 个账户将被永久删除" if zh else f"\n\n{account_count} accounts will be permanently deleted"

        label = QLabel(msg)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("取消" if zh else "Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cancel_bg};
                border: none;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {cancel_hover};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("删除" if zh else "Delete")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {error_color};
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {error_hover};
            }}
        """)
        delete_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._delete_library(lib)

    def _switch_library(self, library_id: str) -> None:
        """Switch to a different library."""
        # Exit multi-select mode when switching libraries
        self._exit_multi_select_mode()

        self._save_data()
        new_lib = self.library_service.switch_library(library_id)
        self.state = self.library_service.load_library_state(new_lib)
        self._update_icons()
        self._refresh_groups()
        self._refresh_account_list()
        self.selected_account = None
        self._update_detail_panel()

    def _create_new_library_direct(self) -> None:
        """Create a new library with default name."""
        zh = self.state.language == 'zh'
        # Generate default name like "新建账号库", "新建账号库 (2)", etc.
        base_name = "新建账号库" if zh else "New Library"
        libraries = self.library_service.list_libraries()
        existing_names = [lib.name for lib in libraries]

        name = base_name
        counter = 2
        while name in existing_names:
            name = f"{base_name} ({counter})"
            counter += 1

        new_lib = self.library_service.create_library(name)
        self._switch_library(new_lib.id)

        self.toast.show_message(f"已创建「{name}」" if zh else f"Created '{name}'")

    def _delete_library(self, lib) -> None:
        """Delete a library with undo support."""
        zh = self.state.language == 'zh'
        libraries = self.library_service.list_libraries()
        current = self.library_service.get_current_library()

        # If deleting current library, switch first
        if lib.id == current.id:
            other_lib = next(l for l in libraries if l.id != lib.id)
            self._switch_library(other_lib.id)

        # Delete but keep file for undo
        backup_data = self.library_service.delete_library(lib.id, keep_file=True)
        self._refresh_library_panel()

        # Store backup for permanent deletion on timeout
        self._pending_delete_backup = backup_data
        lib_name = lib.name

        def undo_delete():
            """Undo the library deletion."""
            if self._pending_delete_backup:
                restored = self.library_service.restore_library(self._pending_delete_backup)
                self._pending_delete_backup = None
                self._refresh_library_panel()
                self.toast.show_message(f"已恢复「{lib_name}」" if zh else f"Restored '{lib_name}'")

        def on_timeout():
            """Permanently delete after timeout."""
            if self._pending_delete_backup:
                self.library_service.permanently_delete_library_file(self._pending_delete_backup)
                self._pending_delete_backup = None

        # Override toast timeout handler
        original_timeout = self.toast._on_timeout
        def custom_timeout():
            on_timeout()
            original_timeout()
        self.toast._on_timeout = custom_timeout

        # Show toast with undo option
        self.toast.show_message(
            f"已删除「{lib_name}」" if zh else f"Deleted '{lib_name}'",
            duration=5000,
            action_text="撤销" if zh else "Undo",
            action_callback=undo_delete
        )

    def _start_new_library(self) -> None:
        """Start creating a new library - show editable card."""
        self._creating_new_library = True
        self._refresh_library_panel()

    def _reorder_library(self, library_id: str, direction: int) -> None:
        """Reorder a library up or down."""
        self.library_service.reorder_library(library_id, direction)
        self._refresh_library_panel()

    def _show_trash_dialog(self) -> None:
        """Show trash management dialog."""
        dialog = TrashDialog(self, self.state, self.state.language)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh if any changes were made
            self._save_data()
            self._refresh_groups()
            self._refresh_account_list()
            self._update_ui_text()  # Update trash count

    def _show_archive_dialog(self) -> None:
        """Show archive management dialog."""
        dialog = ArchiveDialog(self, self.state.language)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            archive = dialog.get_selected_archive()
            if archive:
                self._restore_archive(archive)

    def _restore_archive(self, archive: ArchiveInfo) -> None:
        """Restore application state from archive."""
        try:
            self.state = self.archive_service.restore_archive(archive)
            current = self.library_service.get_current_library()
            self.library_service.save_library_state(current, self.state)
            self._refresh_groups()
            self._refresh_account_list()
            self.selected_account = None
            self._update_detail_panel()

            zh = self.state.language == 'zh'
            self.toast.show_message("已恢复存档" if zh else "Archive restored")
        except Exception as e:
            logger.error(f"Failed to restore archive: {e}")

    def _toggle_group_edit_mode(self) -> None:
        """Toggle group editing mode."""
        self.group_edit_mode = not self.group_edit_mode
        zh = self.state.language == 'zh'

        if self.group_edit_mode:
            self.btn_edit_groups.setText("完成" if zh else "Done")
        else:
            self.btn_edit_groups.setText("编辑" if zh else "Edit")
            self._save_data()  # Save changes when exiting edit mode

        self._refresh_groups()

    def _refresh_groups(self) -> None:
        """Refresh groups list with colored dot indicators or editable items."""
        for btn in self.group_buttons:
            btn.deleteLater()
        self.group_buttons.clear()

        zh = self.state.language == 'zh'
        is_dark = get_theme_manager().is_dark

        if self.group_edit_mode:
            # Edit mode - keep "All Accounts" visible but non-editable
            all_count = len(self.state.accounts)
            all_label = "全部账户" if zh else "All Accounts"
            all_btn = GroupButton(all_label, all_count, is_all=True)
            all_btn.setEnabled(False)  # Disabled in edit mode
            self.groups_layout.insertWidget(0, all_btn)
            self.group_buttons.append(all_btn)

            # Editable group items
            for i, group in enumerate(self.state.groups):
                item = EditableGroupItem(group, is_dark=is_dark)
                item.deleted.connect(self._on_group_deleted)
                item.name_changed.connect(self._on_group_renamed)
                item.dropped.connect(self._on_group_reorder)
                self.groups_layout.insertWidget(i + 1, item)
                self.group_buttons.append(item)

            # Add "Add Group" button at the end
            add_btn = AddGroupButton(self.state.language)
            add_btn.clicked.connect(self._on_add_group)
            self.groups_layout.insertWidget(len(self.state.groups) + 1, add_btn)
            self.group_buttons.append(add_btn)
        else:
            # Normal mode - show navigation buttons
            # All accounts button (with icon)
            all_count = len(self.state.accounts)
            all_label = "全部账户" if zh else "All Accounts"
            all_btn = GroupButton(all_label, all_count, is_all=True)
            all_btn.setProperty("group_id", None)
            all_btn.clicked.connect(lambda: self._on_group_clicked(None))
            self.groups_layout.insertWidget(0, all_btn)
            self.group_buttons.append(all_btn)

            # User groups (with colored dots)
            for i, group in enumerate(self.state.groups):
                count = len([a for a in self.state.accounts if group.name in a.groups])
                color = group.get_color_for_theme(is_dark)
                btn = GroupButton(group.name, count, color_hex=color)
                btn.setProperty("group_id", group.name)
                btn.clicked.connect(lambda gid=group.name: self._on_group_clicked(gid))
                btn.rightClicked.connect(lambda pos, gname=group.name: self._on_group_right_clicked(gname, pos))
                self.groups_layout.insertWidget(i + 1, btn)
                self.group_buttons.append(btn)

            self._highlight_selected_group()

    def _on_group_deleted(self, group_name: str) -> None:
        """Handle group deletion with confirmation and undo."""
        zh = self.state.language == 'zh'
        t = get_theme()
        is_dark = get_theme_manager().is_dark

        # Count accounts using this group
        count = sum(1 for acc in self.state.accounts if group_name in acc.groups)

        # Create styled confirmation dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除" if zh else "Confirm Delete")
        dialog.setFixedWidth(320)

        # Darker colors for dark mode
        error_color = "#DC2626" if is_dark else t.error
        error_hover = "#B91C1C" if is_dark else "#DC2626"

        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {t.bg_primary};
            }}
            QLabel {{
                color: {t.text_primary};
                font-size: 13px;
            }}
            QPushButton {{
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Message
        msg = f"确定要删除分组「{group_name}」吗？" if zh else f"Delete group '{group_name}'?"
        if count > 0:
            msg += f"\n\n⚠ {count} 个账户正在使用此分组" if zh else f"\n\n⚠ {count} accounts use this group"

        label = QLabel(msg)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("取消" if zh else "Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.bg_tertiary};
                border: none;
                color: {t.text_primary};
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("删除" if zh else "Delete")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {error_color};
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {error_hover};
            }}
        """)
        delete_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Backup for undo
        deleted_group = next((g for g in self.state.groups if g.name == group_name), None)
        affected_accounts = [(acc.id, list(acc.groups)) for acc in self.state.accounts if group_name in acc.groups]
        group_index = next((i for i, g in enumerate(self.state.groups) if g.name == group_name), 0)

        # Remove group from state
        self.state.groups = [g for g in self.state.groups if g.name != group_name]
        # Remove group from all accounts
        for account in self.state.accounts:
            if group_name in account.groups:
                account.groups.remove(group_name)
        # Reset selection if deleted group was selected
        if self.selected_group == group_name:
            self.selected_group = None
        self._refresh_groups()
        self._refresh_account_list()

        def undo_delete():
            """Undo the group deletion."""
            if deleted_group:
                # Restore group at original position
                self.state.groups.insert(group_index, deleted_group)
                # Restore group to affected accounts
                for acc_id, original_groups in affected_accounts:
                    acc = next((a for a in self.state.accounts if a.id == acc_id), None)
                    if acc:
                        acc.groups = original_groups
                self._refresh_groups()
                self._refresh_account_list()
                self._update_detail_panel()
                self.toast.show_message(f"已恢复「{group_name}」" if zh else f"Restored '{group_name}'")

        # Show toast with undo option
        self.toast.show_message(
            f"已删除「{group_name}」" if zh else f"Deleted '{group_name}'",
            duration=5000,
            action_text="撤销" if zh else "Undo",
            action_callback=undo_delete
        )

    def _on_group_renamed(self, old_name: str, new_name: str) -> None:
        """Handle group rename."""
        # Check if new name already exists
        if any(g.name == new_name for g in self.state.groups):
            return  # Name already exists, don't rename

        # Update group name
        for group in self.state.groups:
            if group.name == old_name:
                group.name = new_name
                break

        # Update all accounts
        for account in self.state.accounts:
            if old_name in account.groups:
                account.groups.remove(old_name)
                account.groups.append(new_name)

        # Update selection if renamed group was selected
        if self.selected_group == old_name:
            self.selected_group = new_name

    def _on_group_reorder(self, dragged_item: 'EditableGroupItem', target_item: 'EditableGroupItem') -> None:
        """Handle group reordering via drag and drop."""
        dragged_name = dragged_item.group.name
        target_name = target_item.group.name

        # Find indices
        dragged_idx = next((i for i, g in enumerate(self.state.groups) if g.name == dragged_name), None)
        target_idx = next((i for i, g in enumerate(self.state.groups) if g.name == target_name), None)

        if dragged_idx is not None and target_idx is not None and dragged_idx != target_idx:
            # Remove from old position
            group = self.state.groups.pop(dragged_idx)

            # Adjust target index after removal
            if dragged_idx < target_idx:
                target_idx -= 1

            # Insert at correct position based on drop indicator
            drop_at_top = getattr(target_item, '_drop_at_top', False)
            if drop_at_top:
                insert_idx = target_idx
            else:
                insert_idx = target_idx + 1

            self.state.groups.insert(insert_idx, group)
            self._refresh_groups()

    def _on_add_group(self) -> None:
        """Add a new group with inline editing."""
        zh = self.state.language == 'zh'

        # Create group with empty name placeholder
        new_group = Group(name="", color="blue")
        self.state.groups.append(new_group)
        self._refresh_groups()

        # Find the new group's input and focus it after a short delay
        def focus_new_input():
            for btn in self.group_buttons:
                if isinstance(btn, EditableGroupItem) and btn.group.name == "":
                    btn.name_input.setPlaceholderText("新分组" if zh else "New Group")
                    btn.name_input.setFocus()
                    btn.name_input.selectAll()
                    # Handle empty name on focus lost
                    def on_editing_done(item=btn):
                        name = item.name_input.text().strip()
                        if not name:
                            # Use default name if empty
                            base_name = "新分组" if self.state.language == 'zh' else "New Group"
                            name = base_name
                            counter = 1
                            existing_names = {g.name for g in self.state.groups if g != item.group}
                            while name in existing_names:
                                counter += 1
                                name = f"{base_name} {counter}"
                            item.group.name = name
                            item.name_input.setText(name)
                        elif item.group.name == "":
                            item.group.name = name
                        self._save_data()
                    try:
                        btn.name_input.editingFinished.disconnect()
                    except:
                        pass
                    btn.name_input.editingFinished.connect(on_editing_done)
                    break

        QTimer.singleShot(50, focus_new_input)

    def _highlight_selected_group(self) -> None:
        """Highlight selected group button."""
        for btn in self.group_buttons:
            group_id = btn.property("group_id")
            btn.set_selected(group_id == self.selected_group)

    def _on_group_clicked(self, group_id: Optional[str]) -> None:
        """Handle group selection."""
        self.selected_group = group_id
        self._highlight_selected_group()
        self._refresh_account_list()

    def _on_group_right_clicked(self, group_name: str, pos) -> None:
        """Handle right-click on group button - show context menu."""
        t = get_theme()
        zh = self.state.language == 'zh'
        is_dark = get_theme_manager().is_dark
        ic = t.text_secondary

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """)

        # Rename action
        rename_action = menu.addAction(QIcon(icon_edit(14, ic)), "重命名" if zh else "Rename")
        rename_action.triggered.connect(lambda: self._rename_group(group_name))

        # Move up action
        group_index = next((i for i, g in enumerate(self.state.groups) if g.name == group_name), -1)
        if group_index > 0:
            move_up_action = menu.addAction(QIcon(icon_arrow_up(14, ic)), "上移" if zh else "Move up")
            move_up_action.triggered.connect(lambda: self._move_group(group_name, -1))

        # Move down action
        if group_index < len(self.state.groups) - 1:
            move_down_action = menu.addAction(QIcon(icon_arrow_down(14, ic)), "下移" if zh else "Move down")
            move_down_action.triggered.connect(lambda: self._move_group(group_name, 1))

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction(QIcon(icon_trash(14, t.error)), "删除" if zh else "Delete")
        delete_action.triggered.connect(lambda: self._on_group_deleted(group_name))

        menu.exec(pos)

    def _rename_group(self, old_name: str) -> None:
        """Rename a group."""
        zh = self.state.language == 'zh'

        new_name, ok = QInputDialog.getText(
            self,
            "重命名分组" if zh else "Rename Group",
            "新名称:" if zh else "New name:",
            text=old_name
        )

        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()

            # Check if name already exists
            if any(g.name == new_name for g in self.state.groups):
                self.toast.show_message(f"分组「{new_name}」已存在" if zh else f"Group '{new_name}' already exists")
                return

            # Update group name
            for group in self.state.groups:
                if group.name == old_name:
                    group.name = new_name
                    break

            # Update accounts that use this group
            for account in self.state.accounts:
                if old_name in account.groups:
                    account.groups.remove(old_name)
                    account.groups.append(new_name)

            # Update selected group if needed
            if self.selected_group == old_name:
                self.selected_group = new_name

            self._save_data()
            self._refresh_groups()
            self._refresh_account_list()
            self._update_detail_panel()
            self.toast.show_message(f"已重命名为「{new_name}」" if zh else f"Renamed to '{new_name}'")

    def _move_group(self, group_name: str, direction: int) -> None:
        """Move a group up or down in the list."""
        group_index = next((i for i, g in enumerate(self.state.groups) if g.name == group_name), -1)
        if group_index == -1:
            return

        new_index = group_index + direction
        if 0 <= new_index < len(self.state.groups):
            # Swap groups
            self.state.groups[group_index], self.state.groups[new_index] = \
                self.state.groups[new_index], self.state.groups[group_index]
            self._save_data()
            self._refresh_groups()

    def _get_filtered_accounts(self) -> List[Account]:
        """Get accounts filtered by current group and search."""
        accounts = self.state.accounts
        if self.selected_group:
            accounts = [a for a in accounts if self.selected_group in a.groups]

        # Apply search filter
        search_text = self.search_input.text().strip() if hasattr(self, 'search_input') else ""
        if search_text:
            s = search_text.lower()
            def match_account(a):
                # Search in email
                if s in a.email.lower():
                    return True
                # Search in password
                if a.password and s in a.password.lower():
                    return True
                # Search in backup email
                backup = getattr(a, 'backup', '') or getattr(a, 'backup_email', '') or ''
                if backup and s in backup.lower():
                    return True
                # Search in 2FA secret
                if a.secret and s in a.secret.lower():
                    return True
                # Search in notes
                if a.notes and s in a.notes.lower():
                    return True
                # Search in groups
                for group in a.groups:
                    if s in group.lower():
                        return True
                return False
            accounts = [a for a in accounts if match_account(a)]

        return accounts

    def _refresh_account_list(self, search_text: str = "") -> None:
        """Refresh account list."""
        # If in list view mode, refresh the table instead
        if self.list_view_mode:
            self._refresh_table_view()
            return

        # Clear old widgets
        self.account_widgets.clear()
        while self.account_list_layout.count() > 1:
            child = self.account_list_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        accounts = self.state.accounts
        if self.selected_group:
            accounts = [a for a in accounts if self.selected_group in a.groups]
        if search_text:
            s = search_text.lower()
            def match_account(a):
                # Search in email
                if s in a.email.lower():
                    return True
                # Search in password
                if a.password and s in a.password.lower():
                    return True
                # Search in backup email
                backup = getattr(a, 'backup', '') or getattr(a, 'backup_email', '') or ''
                if backup and s in backup.lower():
                    return True
                # Search in 2FA secret
                if a.secret and s in a.secret.lower():
                    return True
                # Search in notes
                if a.notes and s in a.notes.lower():
                    return True
                # Search in groups
                for group in a.groups:
                    if s in group.lower():
                        return True
                return False
            accounts = [a for a in accounts if match_account(a)]

        # Clear selection if list is empty (empty category)
        if not accounts:
            self.selected_account = None
            self._update_detail_panel()

        zh = self.state.language == 'zh'
        group_name = self.selected_group or ("全部账户" if zh else "All Accounts")
        count_text = "个账户" if zh else " accounts"
        self.list_title.setText(f"{group_name} · {len(accounts)}{count_text}")

        t = get_theme()
        for i, account in enumerate(accounts):
            # Add separator before item (except first)
            if i > 0:
                separator = QFrame()
                separator.setFixedHeight(1)
                separator.setStyleSheet(f"background-color: {t.border};")
                self.account_list_layout.insertWidget(self.account_list_layout.count() - 1, separator)

            item = self._create_account_item(account, t, i)
            self.account_widgets.append(item)
            self.account_list_layout.insertWidget(self.account_list_layout.count() - 1, item)

        self._highlight_selected_account()

    def _create_account_item(self, account: Account, t, index: int) -> ClickableFrame:
        """Create account list item widget."""
        item = ClickableFrame()
        item.setProperty("account", account)
        item.setProperty("account_index", index)
        item.setCursor(Qt.CursorShape.PointingHandCursor)

        # Connect signals with lambda using default args to capture values
        item.clicked.connect(lambda acc=account, idx=index: self._on_account_clicked(acc, idx))
        item.rightClicked.connect(lambda pos, acc=account: self._show_account_context_menu(pos, acc))

        if self.list_view_mode:
            # List view: compact single row - just checkbox, ID, email
            layout = QHBoxLayout(item)
            layout.setContentsMargins(12, 6, 12, 6)
            layout.setSpacing(6)

            # Checkbox icon button for multi-select
            if self.multi_select_mode:
                is_checked = self.selection_manager.is_selected(account)
                check_label = QLabel()
                check_label.setFixedSize(20, 20)
                check_label.setPixmap(icon_checkbox(16, t.text_secondary) if is_checked else icon_checkbox_empty(16, t.text_tertiary))
                check_label.setStyleSheet("QLabel { background: transparent; }")
                check_label.setProperty("account", account)
                check_label.setProperty("is_checkbox", True)
                layout.addWidget(check_label)

            # ID number
            id_label = QLabel(f"#{index + 1}")
            id_label.setFixedWidth(32)
            id_label.setStyleSheet(f"font-size: 11px; color: {t.text_tertiary};")
            layout.addWidget(id_label)

            # Email only
            if self.codes_visible:
                email_text = account.email
            else:
                if '@' in account.email:
                    local, domain = account.email.split('@', 1)
                    email_text = f"{local[:3]}***@{domain}" if len(local) > 3 else f"{local}***@{domain}"
                else:
                    email_text = f"{account.email[:3]}***" if len(account.email) > 3 else account.email

            email_label = QLabel(email_text)
            email_label.setStyleSheet(f"font-size: 12px; color: {t.text_primary};")
            layout.addWidget(email_label, 1)

        else:
            # Card view: multi-line with ID, checkbox, email, group, notes
            layout = QVBoxLayout(item)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)

            # Top row: checkbox + ID + email
            top_row = QHBoxLayout()
            top_row.setSpacing(8)

            # Checkbox icon for multi-select (visual only, click handled by card)
            checkbox_width = 0
            if self.multi_select_mode:
                is_checked = self.selection_manager.is_selected(account)
                check_label = QLabel()
                check_label.setFixedSize(20, 20)
                check_label.setPixmap(icon_checkbox(16, t.text_secondary) if is_checked else icon_checkbox_empty(16, t.text_tertiary))
                check_label.setStyleSheet("QLabel { background: transparent; }")
                check_label.setProperty("account", account)
                check_label.setProperty("is_checkbox", True)
                top_row.addWidget(check_label)
                checkbox_width = 28  # checkbox label width + spacing

            # ID number - fixed width for consistent tag alignment
            id_label = QLabel(f"#{index + 1}")
            id_label.setFixedWidth(28)
            id_label.setStyleSheet(f"font-size: 11px; color: {t.text_tertiary};")
            top_row.addWidget(id_label)

            # Email
            if self.codes_visible:
                email_text = account.email
            else:
                if '@' in account.email:
                    local, domain = account.email.split('@', 1)
                    email_text = f"{local[:3]}***@{domain}" if len(local) > 3 else f"{local}***@{domain}"
                else:
                    email_text = f"{account.email[:3]}***" if len(account.email) > 3 else account.email

            email_label = QLabel(email_text)
            email_label.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {t.text_primary};")
            top_row.addWidget(email_label, 1)

            layout.addLayout(top_row)

            # Tags row with flow layout - aligned with email (ID width 28 + spacing 8 = 36 + checkbox if multi-select)
            if account.groups:
                tags_wrapper = QHBoxLayout()
                tags_left_margin = 36 + checkbox_width  # Align with email position
                tags_wrapper.setContentsMargins(tags_left_margin, 0, 0, 0)
                tags_wrapper.setSpacing(0)

                tags_container = QWidget()
                is_dark = get_theme_manager().is_dark
                tags_flow = FlowLayout(spacing=4)

                # Tags with inset effect in dark mode
                tag_fg = t.text_primary

                for group_name in account.groups:
                    tag = QLabel(group_name)
                    if is_dark:
                        # Same gray color as library button
                        tag.setStyleSheet(f"""
                            background-color: #9CA3AF;
                            color: {t.bg_primary};
                            padding: 2px 6px;
                            border: none;
                            border-radius: 4px;
                            font-size: 10px;
                            font-weight: 500;
                        """)
                    else:
                        tag.setStyleSheet(f"""
                            background-color: rgba(120, 120, 128, 0.16);
                            color: {tag_fg};
                            padding: 2px 6px;
                            border: none;
                            border-radius: 4px;
                            font-size: 10px;
                            font-weight: 500;
                        """)
                    tags_flow.addWidget(tag)

                tags_flow.apply_layout(250)  # 320 - 24 margins - 36 tag indent - scrollbar
                tags_container.setLayout(tags_flow)
                tags_wrapper.addWidget(tags_container)
                tags_wrapper.addStretch()
                layout.addLayout(tags_wrapper)

        # Apply selection style in multi-select mode
        is_selected = self.multi_select_mode and self.selection_manager.is_selected(account)
        if is_selected:
            # Selected style - more visible gray background
            item.setStyleSheet(f"""
                QFrame {{
                    background-color: {t.border};
                }}
            """)
        else:
            # Normal style
            item.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                }}
                QFrame:hover {{
                    background-color: {t.bg_hover};
                }}
            """)

        return item

    def _on_account_clicked(self, account: Account, index: int = -1) -> None:
        """Handle account selection with Excel-style modifier key support."""
        if self.multi_select_mode:
            # Detect Shift key at click time
            modifiers = QApplication.keyboardModifiers()
            shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

            # Get filtered accounts list for range selection
            filtered = self._get_filtered_accounts()

            # Use SelectionManager to handle the click
            self.selection_manager.handle_click(account, index, filtered, shift_held)

            # Update visual state without recreating widgets
            self._update_selection_visuals()
            self._update_batch_bar()
            return

        # Normal mode: select account
        # Reset edit mode if switching accounts
        if self.detail_edit_mode and self.selected_account != account:
            self.detail_edit_mode = False
            t = get_theme()
            self.btn_edit.setIcon(QIcon(icon_edit(14, t.text_secondary)))

        self.selected_account = account
        self._highlight_selected_account()
        self._update_detail_panel()

    def _show_account_context_menu(self, pos: 'QPoint', account: Account) -> None:
        """Show context menu for account card."""
        t = get_theme()
        zh = self.state.language == 'zh'

        menu_style = f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """

        menu = QMenu(self)
        menu.setStyleSheet(menu_style)
        ic = t.text_secondary

        # If in multi-select mode and account is in selection, use batch operations
        if self.multi_select_mode and self.selection_manager.is_selected(account):
            # "Add to group" submenu
            add_menu = menu.addMenu(QIcon(icon_square_plus(14, ic)), "添加到分组" if zh else "Add to group")
            add_menu.setStyleSheet(menu_style)

            for group in self.state.groups:
                action = add_menu.addAction(f"■ {group.name}")
                action.triggered.connect(lambda checked, g=group.name: self._batch_add_to_group(g))

            if self.state.groups:
                add_menu.addSeparator()

            new_action = add_menu.addAction("+ " + ("新建分组" if zh else "New group"))
            new_action.triggered.connect(self._batch_add_to_new_group)

            # "Remove from group" submenu
            groups_in_selection = set()
            for acc in self.selection_manager.items:
                for g in acc.groups:
                    groups_in_selection.add(g)

            if groups_in_selection:
                remove_menu = menu.addMenu(QIcon(icon_square_minus(14, ic)), "从分组中移除" if zh else "Remove from group")
                remove_menu.setStyleSheet(menu_style)

                for group_name in sorted(groups_in_selection):
                    action = remove_menu.addAction(f"■ {group_name}")
                    action.triggered.connect(lambda checked, g=group_name: self._batch_remove_from_group(g))

            menu.addSeparator()

            # Batch copy
            copy_action = menu.addAction(QIcon(icon_copy(14, ic)), "批量复制" if zh else "Batch copy")
            copy_action.triggered.connect(self._batch_copy)

            # Move to library submenu
            from ..services.library_service import get_library_service
            library_service = get_library_service()
            libraries = library_service.list_libraries()
            current_library = library_service.get_current_library()
            other_libraries = [lib for lib in libraries if lib.id != current_library.id]

            if other_libraries:
                move_lib_menu = menu.addMenu(QIcon(icon_library_move(14, ic)), "移动到库" if zh else "Move to library")
                move_lib_menu.setStyleSheet(menu_style)

                for lib in other_libraries:
                    lib_submenu = move_lib_menu.addMenu(QIcon(icon_library(14, ic)), lib.name)
                    lib_submenu.setStyleSheet(menu_style)
                    move_action = lib_submenu.addAction("移动" if zh else "Move")
                    move_action.triggered.connect(lambda checked, l=lib: self._batch_move_to_library(l, remove_from_current=True))
                    copy_action = lib_submenu.addAction("复制" if zh else "Copy")
                    copy_action.triggered.connect(lambda checked, l=lib: self._batch_move_to_library(l, remove_from_current=False))

            menu.addSeparator()

            # Batch delete
            delete_action = menu.addAction(QIcon(icon_trash(14, t.error)), "删除" if zh else "Delete")
            delete_action.triggered.connect(self._batch_delete)

        else:
            # Single account operations
            # Copy options
            copy_email = menu.addAction(QIcon(icon_copy(14, ic)), "复制邮箱" if zh else "Copy email")
            copy_email.triggered.connect(lambda: self._copy_field(account.email, "邮箱" if zh else "Email"))

            if account.password:
                copy_pwd = menu.addAction(QIcon(icon_key(14, ic)), "复制密码" if zh else "Copy password")
                copy_pwd.triggered.connect(lambda: self._copy_field(account.password, "密码" if zh else "Password"))

            if account.secret:
                copy_code = menu.addAction(QIcon(icon_copy(14, ic)), "复制验证码" if zh else "Copy code")
                copy_code.triggered.connect(lambda: self._copy_totp_for_account(account))

            menu.addSeparator()

            # Add to group submenu
            add_menu = menu.addMenu(QIcon(icon_square_plus(14, ic)), "添加到分组" if zh else "Add to group")
            add_menu.setStyleSheet(menu_style)

            for group in self.state.groups:
                action = add_menu.addAction(f"■ {group.name}")
                action.triggered.connect(lambda checked, g=group.name, a=account: self._add_account_to_group(a, g))

            if self.state.groups:
                add_menu.addSeparator()

            new_action = add_menu.addAction("+ " + ("新建分组" if zh else "New group"))
            new_action.triggered.connect(lambda: self._add_account_to_new_group(account))

            # Remove from group submenu
            if account.groups:
                remove_menu = menu.addMenu(QIcon(icon_square_minus(14, ic)), "从分组中移除" if zh else "Remove from group")
                remove_menu.setStyleSheet(menu_style)

                for group_name in account.groups:
                    action = remove_menu.addAction(f"■ {group_name}")
                    action.triggered.connect(lambda checked, g=group_name, a=account: self._remove_account_from_group(a, g))

            # Move to library submenu
            from ..services.library_service import get_library_service
            library_service = get_library_service()
            libraries = library_service.list_libraries()
            current_library = library_service.get_current_library()
            other_libraries = [lib for lib in libraries if lib.id != current_library.id]

            if other_libraries:
                move_lib_menu = menu.addMenu(QIcon(icon_library_move(14, ic)), "移动到库" if zh else "Move to library")
                move_lib_menu.setStyleSheet(menu_style)

                for lib in other_libraries:
                    lib_submenu = move_lib_menu.addMenu(QIcon(icon_library(14, ic)), lib.name)
                    lib_submenu.setStyleSheet(menu_style)
                    move_action = lib_submenu.addAction("移动" if zh else "Move")
                    move_action.triggered.connect(lambda checked, l=lib, a=account: self._move_account_to_library(a, l, remove_from_current=True))
                    copy_action = lib_submenu.addAction("复制" if zh else "Copy")
                    copy_action.triggered.connect(lambda checked, l=lib, a=account: self._move_account_to_library(a, l, remove_from_current=False))

            menu.addSeparator()

            # Delete
            delete_action = menu.addAction(QIcon(icon_trash(14, t.error)), "删除" if zh else "Delete")
            delete_action.triggered.connect(lambda: self._delete_single_account(account))

        menu.exec(pos)

    def _copy_field(self, value: str, label: str) -> None:
        """Copy a field value to clipboard."""
        QApplication.clipboard().setText(value)
        zh = self.state.language == 'zh'
        self.toast.show_message(f"已复制：{label}" if zh else f"Copied: {label}", center=True)

    def _copy_totp_for_account(self, account: Account) -> None:
        """Copy TOTP code for a specific account."""
        from ..services.totp_service import TOTPService
        code = TOTPService.generate_totp(account.secret)
        if code:
            QApplication.clipboard().setText(code)
            zh = self.state.language == 'zh'
            self.toast.show_message("已复制：验证码" if zh else "Copied: Verification Code", center=True)

    def _add_account_to_group(self, account: Account, group_name: str) -> None:
        """Add single account to a group."""
        if group_name not in account.groups:
            account.groups.append(group_name)
            self._save_data()
            self._refresh_account_list()
            self._update_detail_panel()
            self._refresh_groups()
            zh = self.state.language == 'zh'
            self.toast.show_message(f"已添加到「{group_name}」" if zh else f"Added to '{group_name}'")

    def _add_account_to_new_group(self, account: Account) -> None:
        """Create a new group and add single account to it."""
        zh = self.state.language == 'zh'
        name, ok = QInputDialog.getText(
            self,
            "新建分组" if zh else "New Group",
            "分组名称:" if zh else "Group name:"
        )

        if ok and name.strip():
            name = name.strip()
            if not any(g.name == name for g in self.state.groups):
                new_group = Group(name=name, color="blue")
                self.state.groups.append(new_group)
            self._add_account_to_group(account, name)

    def _remove_account_from_group(self, account: Account, group_name: str) -> None:
        """Remove single account from a group."""
        if group_name in account.groups:
            account.groups.remove(group_name)
            self._save_data()
            self._refresh_account_list()
            self._update_detail_panel()
            self._refresh_groups()
            zh = self.state.language == 'zh'
            self.toast.show_message(f"已从「{group_name}」移除" if zh else f"Removed from '{group_name}'")

    def _delete_single_account(self, account: Account) -> None:
        """Delete a single account with undo support."""
        zh = self.state.language == 'zh'

        if not self._show_delete_confirmation(
            f"确定要删除账户 {account.email} 吗？" if zh else f"Delete account {account.email}?"
        ):
            return

        # Store for undo
        deleted_account = account
        was_selected = self.selected_account == account

        # Move to trash
        if hasattr(self.state, 'trash'):
            self.state.trash.append(account)
        if account in self.state.accounts:
            self.state.accounts.remove(account)

        if was_selected:
            self.selected_account = None

        self._save_data()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()

        # Undo callback
        def undo_delete():
            # Restore from trash
            if hasattr(self.state, 'trash') and deleted_account in self.state.trash:
                self.state.trash.remove(deleted_account)
            self.state.accounts.append(deleted_account)
            if was_selected:
                self.selected_account = deleted_account
            self._save_data()
            self._refresh_groups()
            self._refresh_account_list()
            self._update_detail_panel()
            self.toast.show_message("已恢复" if zh else "Restored")

        # Show toast with undo
        self.toast.show_message(
            "已删除账户" if zh else "Account deleted",
            duration=4000,
            action_text="撤回" if zh else "Undo",
            action_callback=undo_delete
        )

    def _on_checkbox_changed(self, account: Account, state: int) -> None:
        """Handle checkbox state change in multi-select mode."""
        acc_id = id(account)
        if state == 2:  # Checked
            if not self.selection_manager.is_selected(account):
                self.selection_manager._selected[acc_id] = account
        else:  # Unchecked
            if self.selection_manager.is_selected(account):
                del self.selection_manager._selected[acc_id]
        self._update_batch_bar()

    def _update_selection_visuals(self) -> None:
        """Update visual state of account cards for multi-select mode without recreating widgets."""
        t = get_theme()
        for widget in self.account_widgets:
            account = widget.property("account")
            is_selected = self.selection_manager.is_selected(account)

            # Update background style
            if is_selected:
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: {t.border};
                    }}
                """)
            else:
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                    }}
                    QFrame:hover {{
                        background-color: {t.bg_hover};
                    }}
                """)

            # Update checkbox icon
            for child in widget.findChildren(QLabel):
                if child.property("is_checkbox"):
                    if is_selected:
                        child.setPixmap(icon_checkbox(16, t.text_secondary))
                    else:
                        child.setPixmap(icon_checkbox_empty(16, t.text_tertiary))
                    break

    def _highlight_selected_account(self) -> None:
        """Highlight selected account item."""
        t = get_theme()
        for widget in self.account_widgets:
            account = widget.property("account")
            # Check multi-select mode first
            if self.multi_select_mode and self.selection_manager.is_selected(account):
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: {t.bg_hover};
                    }}
                """)
            elif account == self.selected_account:
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: {t.bg_hover};
                    }}
                """)
            else:
                widget.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                    }}
                    QFrame:hover {{
                        background-color: {t.bg_hover};
                    }}
                """)

    def _update_detail_panel(self) -> None:
        """Update detail panel with selected account."""
        t = get_theme()

        if not self.selected_account:
            self.empty_container.show()
            self.detail_scroll.hide()
            self.detail_content.hide()
            # Use primary background when empty
            self.detail_panel.setStyleSheet(f"#detailPanel {{ background-color: {t.bg_primary}; }}")
            return

        self.empty_container.hide()
        self.detail_scroll.show()
        self.detail_content.show()
        # Use primary background for cleaner look
        self.detail_panel.setStyleSheet(f"#detailPanel {{ background-color: {t.bg_primary}; }}")

        # Handle visibility for header
        if self.codes_visible:
            name = self.selected_account.email.split('@')[0] if '@' in self.selected_account.email else self.selected_account.email
            email = self.selected_account.email
        else:
            name = self.selected_account.email.split('@')[0][:3] + "***" if '@' in self.selected_account.email else self.selected_account.email[:3] + "***"
            local, domain = self.selected_account.email.split('@', 1) if '@' in self.selected_account.email else (self.selected_account.email, "")
            email = f"{local[:3]}***@{domain}" if domain else f"{local[:3]}***"

        self.detail_name.setText(name)
        self.detail_email.setText(email)

        self._update_detail_fields()

        # Show/hide TOTP section based on whether account has secret
        if self.selected_account.secret:
            self.totp_section.setVisible(True)
            self._update_totp_display()
        else:
            self.totp_section.setVisible(False)

        # Notes section - always show
        zh = self.state.language == 'zh'
        self.notes_label.setText("备注" if zh else "Notes")
        notes = self.selected_account.notes or ""
        placeholder = "点击添加备注..." if zh else "Click to add notes..."
        if notes:
            self.notes_edit.setPlainText(notes)
            self.notes_edit.setStyleSheet(f"color: {t.text_secondary};")
        else:
            self.notes_edit.setPlainText(placeholder)
            self.notes_edit.setStyleSheet(f"color: {t.text_tertiary};")

    def _update_totp_display(self) -> None:
        """Update TOTP code display."""
        if not self.selected_account or not self.selected_account.secret:
            return

        if not self.codes_visible:
            self.totp_display.setText("*** ***")
            return

        code = self.totp_service.generate_code_safe(self.selected_account.secret)
        if code and len(code) == 6:
            self.totp_display.setText(f"{code[:3]} {code[3:]}")
        else:
            self.totp_display.setText("--- ---")

    def _update_detail_fields(self) -> None:
        """Update detail fields with copy buttons."""
        while self.fields_layout.count():
            child = self.fields_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Clear editable fields references
        self.editable_fields.clear()

        if not self.selected_account:
            return

        t = get_theme()
        zh = self.state.language == 'zh'

        # Email field with copy button
        self._add_copyable_field(
            "邮箱" if zh else "Email",
            self.selected_account.email,
            is_sensitive=True,
            field_key='email'
        )

        # Password field with copy button (always show in edit mode, or if has password)
        if self.selected_account.password or self.detail_edit_mode:
            self._add_copyable_field(
                "密码" if zh else "Password",
                self.selected_account.password or "",
                is_password=True,
                is_sensitive=True,
                field_key='password'
            )

        # Backup email field with copy button
        backup_email = getattr(self.selected_account, 'backup', '') or getattr(self.selected_account, 'backup_email', '') or ''
        if backup_email or self.detail_edit_mode:
            self._add_copyable_field(
                "辅助邮箱" if zh else "Backup Email",
                backup_email,
                is_sensitive=True,
                field_key='backup'
            )

        # 2FA Secret key with copy button (always show in edit mode, or if has secret)
        if self.selected_account.secret or self.detail_edit_mode:
            self._add_copyable_field(
                "2FA密钥" if zh else "2FA Secret",
                self.selected_account.secret or "",
                is_password=True,
                is_sensitive=True,
                field_key='secret'
            )

        # Group tags (always show, with edit button)
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(6)

        # Label row with edit button
        label_row = QHBoxLayout()
        label_row.setSpacing(8)
        group_label = QLabel("分组" if zh else "Group")
        group_label.setStyleSheet(f"font-size: 11px; font-weight: 500; color: {t.text_tertiary}; text-transform: uppercase; letter-spacing: 0.5px;")
        label_row.addWidget(group_label)
        label_row.addStretch()
        group_layout.addLayout(label_row)

        # Show ALL groups with word wrap - active ones are filled, inactive are outlined
        # Use a container widget with flow layout behavior
        tags_container = QWidget()
        tags_flow = FlowLayout(spacing=6)

        # Tag style - inset effect in dark mode
        is_dark = get_theme_manager().is_dark
        inactive_bg = t.bg_primary
        inactive_hover = t.bg_hover

        for group in self.state.groups:
            is_active = group.name in self.selected_account.groups

            tag = QPushButton(group.name)
            tag.setCursor(Qt.CursorShape.PointingHandCursor)
            tag.setFixedHeight(24)

            if is_active:
                if is_dark:
                    # Active tag in dark mode - same gray as library button
                    tag.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #9CA3AF;
                            color: {t.bg_primary};
                            padding: 0px 10px;
                            border: none;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 500;
                        }}
                        QPushButton:hover {{
                            background-color: #D1D5DB;
                        }}
                    """)
                else:
                    # Active tag in light mode
                    tag.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(120, 120, 128, 0.16);
                            color: {t.text_primary};
                            padding: 0px 10px;
                            border: none;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 500;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(120, 120, 128, 0.22);
                        }}
                    """)
            else:
                # Inactive tag
                tag.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {inactive_bg};
                        color: {t.text_tertiary};
                        padding: 0px 10px;
                        border: 1px solid {t.border};
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: {inactive_hover};
                        color: {t.text_secondary};
                    }}
                """)

            tag.clicked.connect(lambda checked, g=group.name: self._toggle_account_tag(g, g not in self.selected_account.groups))
            tag.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tag.customContextMenuRequested.connect(lambda pos, g=group.name, btn=tag: self._show_tag_context_menu(pos, g, btn))
            tags_flow.addWidget(tag)

        # Add inline input for new group - compact, auto-expand, match tag height
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("+")
        self.new_tag_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_tag_input.setFixedWidth(36)
        self.new_tag_input.setFixedHeight(24)
        self.new_tag_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.bg_tertiary};
                color: {t.text_secondary};
                border: 1px solid {t.border};
                border-radius: 4px;
                font-size: 11px;
                padding: 0px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t.text_tertiary};
                background-color: {t.bg_primary};
                color: {t.text_primary};
            }}
        """)
        self.new_tag_input.returnPressed.connect(self._create_inline_tag)
        self.new_tag_input.editingFinished.connect(self._on_tag_input_finished)
        self.new_tag_input.textChanged.connect(self._on_tag_input_text_changed)
        tags_flow.addWidget(self.new_tag_input)

        # Apply flow layout - use content wrapper max width (450) to align with copy button
        tags_flow.apply_layout(450)
        tags_container.setLayout(tags_flow)
        group_layout.addWidget(tags_container)

        self.fields_layout.addWidget(group_widget)

    def _add_copyable_field(self, label: str, value: str, is_password: bool = False, is_sensitive: bool = False, display_value: str = None, field_key: str = None) -> None:
        """Add a field with copy button and optional visibility toggle."""
        t = get_theme()

        field_widget = QWidget()
        field_layout = QVBoxLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(6)

        field_label = QLabel(label)
        field_label.setStyleSheet(f"font-size: 11px; font-weight: 500; color: {t.text_tertiary}; text-transform: uppercase; letter-spacing: 0.5px;")
        field_layout.addWidget(field_label)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        # In edit mode, show actual value for editing
        if self.detail_edit_mode:
            display_val = value
        elif display_value is not None:
            display_val = display_value
        elif is_sensitive and not self.codes_visible:
            if '@' in value:
                local, domain = value.split('@', 1)
                display_val = f"{local[:3]}***@{domain}" if len(local) > 3 else f"{local}***@{domain}"
            else:
                display_val = "******"
        else:
            display_val = value

        field_input = QLineEdit()
        field_input.setText(display_val)

        # In edit mode: editable with main background color
        if self.detail_edit_mode:
            field_input.setReadOnly(False)
            field_input.setStyleSheet(f"""
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px 10px;
                color: {t.text_primary};
            """)
            if is_password:
                field_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            field_input.setReadOnly(True)
            if is_password and self.codes_visible:
                field_input.setEchoMode(QLineEdit.EchoMode.Password)
            field_input.setStyleSheet(f"""
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px 10px;
                color: {t.text_primary};
            """)

        # Store reference for editing
        if field_key:
            self.editable_fields[field_key] = field_input

        input_row.addWidget(field_input, 1)

        # Toggle visibility button (only for password fields when visible)
        if is_password and self.codes_visible:
            toggle_btn = QPushButton()
            toggle_btn.setFixedSize(32, 32)
            toggle_btn.setIcon(QIcon(icon_eye(14, t.text_secondary)))
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {t.bg_hover};
                }}
            """)

            def toggle_visibility():
                if field_input.echoMode() == QLineEdit.EchoMode.Password:
                    field_input.setEchoMode(QLineEdit.EchoMode.Normal)
                    toggle_btn.setIcon(QIcon(icon_eye_off(14, t.text_secondary)))
                else:
                    field_input.setEchoMode(QLineEdit.EchoMode.Password)
                    toggle_btn.setIcon(QIcon(icon_eye(14, t.text_secondary)))

            toggle_btn.clicked.connect(toggle_visibility)
            input_row.addWidget(toggle_btn)

        # Copy button
        copy_btn = QPushButton()
        copy_btn.setFixedSize(32, 32)
        copy_btn.setIcon(QIcon(icon_copy(14, t.text_secondary)))
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
        """)

        def copy_value():
            QApplication.clipboard().setText(value)
            copy_btn.setIcon(QIcon(icon_check(14, t.success)))
            QTimer.singleShot(1500, lambda: copy_btn.setIcon(QIcon(icon_copy(14, t.text_secondary))))
            zh = self.state.language == 'zh'
            self.toast.show_message(f"已复制：{label}" if zh else f"Copied: {label}", center=True)

        copy_btn.clicked.connect(copy_value)
        input_row.addWidget(copy_btn)

        field_layout.addLayout(input_row)
        self.fields_layout.addWidget(field_widget)

    def _start_timer(self) -> None:
        """Start TOTP timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.timer.start(1000)

    def _update_timer(self) -> None:
        """Update TOTP timer."""
        try:
            remaining = self.time_service.get_remaining_seconds()
            self.totp_progress.setValue(remaining)
            self.totp_timer.setText(f"{remaining}s")

            if remaining >= 29:
                self._update_totp_display()
                self._refresh_account_list_codes()

            if self.selected_account and self.selected_account.secret:
                self._update_totp_display()

        except Exception as e:
            logger.error(f"Timer error: {e}")

    def _refresh_account_list_codes(self) -> None:
        """Refresh account list display (handles visibility toggle)."""
        # Since we removed TOTP from cards, just refresh the list on visibility change
        pass

    # === Event Handlers ===

    def _on_search_changed(self, text: str) -> None:
        """Handle search input."""
        self._refresh_account_list(text)

    def _toggle_theme(self) -> None:
        """Toggle light/dark theme."""
        self.theme_manager.toggle_theme()
        self._apply_theme()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()
        self._save_data()

    def _toggle_language(self) -> None:
        """Toggle language."""
        self.state.language = 'en' if self.state.language == 'zh' else 'zh'
        self._apply_theme()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()
        self._save_data()

    def _toggle_codes_visibility(self) -> None:
        """Toggle batch show/hide for all data."""
        self.codes_visible = not self.codes_visible
        self._update_icons()

        if self.list_view_mode:
            self._refresh_table_view()
        else:
            self._refresh_account_list()
            self._update_detail_panel()

        zh = self.state.language == 'zh'
        if self.codes_visible:
            self.toast.show_message("已显示数据" if zh else "Data visible")
        else:
            self.toast.show_message("已隐藏数据" if zh else "Data hidden")

    def _toggle_multi_select(self) -> None:
        """Toggle multi-select mode."""
        self.multi_select_mode = not self.multi_select_mode
        self.selection_manager.clear()  # Clears selection and resets anchor

        # Clear single selection when entering multi-select mode
        if self.multi_select_mode:
            self.selected_account = None
            self.selected_table_row = -1  # Clear table row selection

        self._update_icons()
        self._refresh_account_list()
        self._update_batch_bar()
        self._update_detail_panel()

        zh = self.state.language == 'zh'
        if self.multi_select_mode:
            self.toast.show_message("已开启多选" if zh else "Multi-select on")
        else:
            self.toast.show_message("已关闭多选" if zh else "Multi-select off")

    def _exit_multi_select_mode(self) -> None:
        """Exit multi-select mode silently (without toast)."""
        if not self.multi_select_mode:
            return
        self.multi_select_mode = False
        self.selection_manager.clear()
        self._update_icons()
        self._refresh_account_list()
        self._update_batch_bar()
        self._update_detail_panel()

    def _update_batch_bar(self) -> None:
        """Update batch action bar visibility and label."""
        self.batch_action_bar.setVisible(self.multi_select_mode)
        if self.multi_select_mode:
            t = get_theme()
            zh = self.state.language == 'zh'
            count = self.selection_manager.count
            total = len(self._get_filtered_accounts())

            # Update select all icon button
            if count == total and total > 0:
                # All selected - show checked icon
                self.select_all_btn.setIcon(QIcon(icon_checkbox(16, t.text_secondary)))
            else:
                # Not all selected - show empty icon
                self.select_all_btn.setIcon(QIcon(icon_checkbox_empty(16, t.text_tertiary)))

            if count > 0:
                self.batch_select_label.setText(f"已选择 {count}/{total} 项" if zh else f"{count}/{total} selected")
            else:
                self.batch_select_label.setText(f"全选 ({total})" if zh else f"Select all ({total})")

    def _on_select_all_changed(self, state: int) -> None:
        """Handle select all checkbox state change (legacy, kept for compatibility)."""
        filtered = self._get_filtered_accounts()
        if state == 2:  # Checked - select all
            self.selection_manager.set_all(filtered)
        else:  # Unchecked - deselect all
            self.selection_manager.clear()
        self._refresh_account_list()
        self._update_batch_bar()

    def _on_select_all_btn_clicked(self) -> None:
        """Handle select all icon button click."""
        filtered = self._get_filtered_accounts()
        count = self.selection_manager.count
        total = len(filtered)

        if count == total and total > 0:
            # All selected - deselect all
            self.selection_manager.clear()
        else:
            # Not all selected - select all
            self.selection_manager.set_all(filtered)

        self._refresh_account_list()
        self._update_batch_bar()

    def _handle_notes_click(self) -> None:
        """Handle notes field click to enable editing."""
        try:
            if not hasattr(self, 'notes_edit') or not self.notes_edit:
                return

            t = get_theme()
            zh = self.state.language == 'zh'
            placeholder = "点击添加备注..." if zh else "Click to add notes..."

            # Clear placeholder text when clicking
            if self.notes_edit.toPlainText() == placeholder:
                self.notes_edit.clear()
                self.notes_edit.setStyleSheet(f"color: {t.text_secondary};")

            self.notes_edit.setReadOnly(False)
            self.notes_edit.setCursor(Qt.CursorShape.IBeamCursor)
        except RuntimeError:
            pass
        except Exception as e:
            logger.error(f"Error in notes click: {e}")

    def _handle_notes_focus_out(self) -> None:
        """Handle notes field focus out to save changes."""
        try:
            # Check if widget still exists
            if not hasattr(self, 'notes_edit') or not self.notes_edit:
                return

            t = get_theme()
            zh = self.state.language == 'zh'
            placeholder = "点击添加备注..." if zh else "Click to add notes..."

            if self.selected_account:
                new_notes = self.notes_edit.toPlainText().strip()
                # Don't save placeholder as notes
                if new_notes == placeholder:
                    new_notes = ""
                if new_notes != self.selected_account.notes:
                    self.selected_account.notes = new_notes
                    self._save_data()

                # Restore placeholder if empty
                if not new_notes:
                    self.notes_edit.setPlainText(placeholder)
                    self.notes_edit.setStyleSheet(f"color: {t.text_tertiary};")

            self.notes_edit.setReadOnly(True)
            self.notes_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        except RuntimeError:
            # Widget was deleted
            pass
        except Exception as e:
            logger.error(f"Error in notes focus out: {e}")

    def _batch_delete(self) -> None:
        """Delete selected accounts with undo support."""
        if self.selection_manager.count == 0:
            return

        zh = self.state.language == 'zh'
        count = self.selection_manager.count
        msg = f"确定要删除 {count} 个账户吗？" if zh else f"Delete {count} accounts?"

        if not self._show_delete_confirmation(msg):
            return

        # Store deleted accounts for undo
        deleted_accounts = list(self.selection_manager.items)
        was_selected = self.selected_account
        selected_was_deleted = self.selection_manager.is_selected(self.selected_account)

        for account in deleted_accounts:
            if hasattr(self.state, 'trash'):
                self.state.trash.append(account)
            if account in self.state.accounts:
                self.state.accounts.remove(account)

        # Clear selected account if it was deleted
        if selected_was_deleted:
            self.selected_account = None

        self.selection_manager.clear()
        self._save_data()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_batch_bar()
        self._update_detail_panel()

        # Undo callback
        def undo_delete():
            for account in deleted_accounts:
                if hasattr(self.state, 'trash') and account in self.state.trash:
                    self.state.trash.remove(account)
                self.state.accounts.append(account)
            if selected_was_deleted and was_selected:
                self.selected_account = was_selected
            self._save_data()
            self._refresh_groups()
            self._refresh_account_list()
            self._update_detail_panel()
            self.toast.show_message(f"已恢复 {count} 个账户" if zh else f"Restored {count} accounts")

        # Exit multi-select mode
        self._exit_multi_select_mode()

        # Show toast with undo
        self.toast.show_message(
            f"已删除 {count} 个账户" if zh else f"Deleted {count} accounts",
            duration=4000,
            action_text="撤回" if zh else "Undo",
            action_callback=undo_delete
        )

    def _batch_export(self) -> None:
        """Export selected accounts."""
        if self.selection_manager.count == 0:
            return

        zh = self.state.language == 'zh'

        # Build export text
        lines = []
        for account in self.selection_manager.items:
            parts = [account.email]
            if account.password:
                parts.append(account.password)
            if hasattr(account, 'backup_email') and account.backup_email:
                parts.append(account.backup_email)
            if account.secret:
                parts.append(account.secret)
            lines.append("----".join(parts))

        export_text = "\n".join(lines)
        QApplication.clipboard().setText(export_text)

        count = self.selection_manager.count

        # Exit multi-select mode
        self._exit_multi_select_mode()

        self.toast.show_message(f"已复制 {count} 个账户" if zh else f"Copied {count} accounts", center=True)

    def _should_show_menu(self, menu_id: str) -> bool:
        """Check if menu should be shown (prevents re-open when clicking to close)."""
        last_close = self._menu_close_times.get(menu_id, 0)
        return time.time() - last_close > 0.3  # 300ms threshold

    def _track_menu_close(self, menu: QMenu, menu_id: str) -> None:
        """Track when menu closes."""
        menu.aboutToHide.connect(lambda: self._menu_close_times.update({menu_id: time.time()}))

    def _show_batch_add_group_menu(self) -> None:
        """Show menu to add selected accounts to a group."""
        if not self._should_show_menu("batch_add_group"):
            return

        if self.selection_manager.count == 0:
            zh = self.state.language == 'zh'
            self.toast.show_message("请先选择账户" if zh else "Please select accounts first")
            return

        t = get_theme()
        zh = self.state.language == 'zh'

        menu_style = f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """

        menu = QMenu(self)
        menu.setStyleSheet(menu_style)
        self._track_menu_close(menu, "batch_add_group")

        for group in self.state.groups:
            action = menu.addAction(f"■ {group.name}")
            action.triggered.connect(lambda checked, g=group.name: self._batch_add_to_group(g))

        if self.state.groups:
            menu.addSeparator()

        new_action = menu.addAction("+ " + ("新建分组" if zh else "New group"))
        new_action.triggered.connect(self._batch_add_to_new_group)

        # Show menu below button
        menu.exec(self.btn_batch_add_group.mapToGlobal(self.btn_batch_add_group.rect().bottomLeft()))

    def _show_batch_remove_group_menu(self) -> None:
        """Show menu to remove selected accounts from a group."""
        if not self._should_show_menu("batch_remove_group"):
            return

        if self.selection_manager.count == 0:
            zh = self.state.language == 'zh'
            self.toast.show_message("请先选择账户" if zh else "Please select accounts first")
            return

        # Collect groups from selected accounts
        groups_in_selection = set()
        for account in self.selection_manager.items:
            for g in account.groups:
                groups_in_selection.add(g)

        if not groups_in_selection:
            zh = self.state.language == 'zh'
            self.toast.show_message("所选账户不在任何分组中" if zh else "Selected accounts are not in any group")
            return

        t = get_theme()
        zh = self.state.language == 'zh'

        menu_style = f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """

        menu = QMenu(self)
        menu.setStyleSheet(menu_style)
        self._track_menu_close(menu, "batch_remove_group")

        for group_name in sorted(groups_in_selection):
            action = menu.addAction(f"■ {group_name}")
            action.triggered.connect(lambda checked, g=group_name: self._batch_remove_from_group(g))

        # Show menu below button
        menu.exec(self.btn_batch_remove_group.mapToGlobal(self.btn_batch_remove_group.rect().bottomLeft()))

    def _show_batch_move_library_menu(self) -> None:
        """Show menu to move/copy selected accounts to another library."""
        if not self._should_show_menu("batch_move_library"):
            return

        zh = self.state.language == 'zh'

        if self.selection_manager.count == 0:
            self.toast.show_message("请先选择账户" if zh else "Please select accounts first")
            return

        # Get other libraries
        from ..services.library_service import get_library_service
        library_service = get_library_service()
        libraries = library_service.list_libraries()
        current_library = library_service.get_current_library()
        other_libraries = [lib for lib in libraries if lib.id != current_library.id]

        if not other_libraries:
            self.toast.show_message("没有其他库可用" if zh else "No other libraries available")
            return

        t = get_theme()

        menu_style = f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """

        menu = QMenu(self)
        menu.setStyleSheet(menu_style)
        self._track_menu_close(menu, "batch_move_library")

        # Get icon color
        is_dark = get_theme_manager().is_dark
        ic = t.text_secondary

        for lib in other_libraries:
            # Create submenu for each library with library icon
            lib_menu = menu.addMenu(QIcon(icon_library(14, ic)), lib.name)
            lib_menu.setStyleSheet(menu_style)

            # Move option (remove from current library)
            move_action = lib_menu.addAction("移动" if zh else "Move")
            move_action.triggered.connect(lambda checked, l=lib: self._batch_move_to_library(l, remove_from_current=True))

            # Copy option (keep in both libraries)
            copy_action = lib_menu.addAction("复制" if zh else "Copy")
            copy_action.triggered.connect(lambda checked, l=lib: self._batch_move_to_library(l, remove_from_current=False))

        # Show menu below button
        menu.exec(self.btn_batch_move_library.mapToGlobal(self.btn_batch_move_library.rect().bottomLeft()))

    def _batch_move_to_library(self, target_library, remove_from_current: bool = True) -> None:
        """Move or copy selected accounts to another library with undo support."""
        if self.selection_manager.count == 0:
            return

        zh = self.state.language == 'zh'

        try:
            from ..services.library_service import get_library_service
            from ..models.group import Group
            import copy as copy_module

            library_service = get_library_service()

            # Load target library state
            target_state = library_service.load_library_state(target_library)

            # Get existing group names in target library
            target_group_names = {g.name for g in target_state.groups}

            # Store for undo
            moved_accounts = []
            moved_emails = []
            was_selected = self.selected_account
            selected_was_moved = self.selection_manager.is_selected(self.selected_account)

            # Copy accounts to target library
            count = 0
            for account in self.selection_manager.items:
                # Deep copy the account to avoid reference issues
                account_copy = copy_module.deepcopy(account)
                # Check if account already exists in target (by email)
                if not any(a.email == account_copy.email for a in target_state.accounts):
                    target_state.accounts.append(account_copy)
                    moved_accounts.append(account)
                    moved_emails.append(account.email)
                    count += 1

                    # Create missing groups in target library
                    for group_name in account_copy.groups:
                        if group_name not in target_group_names:
                            # Find the group color from source library
                            source_group = next((g for g in self.state.groups if g.name == group_name), None)
                            color = source_group.color if source_group else "red"
                            target_state.groups.append(Group(name=group_name, color=color))
                            target_group_names.add(group_name)

            # Save target library
            library_service.save_library_state(target_library, target_state)

            # Remove from current library if it's a move operation
            if remove_from_current:
                for account in moved_accounts:
                    if account in self.state.accounts:
                        self.state.accounts.remove(account)

                # Clear selection
                if selected_was_moved:
                    self.selected_account = None
                self.selection_manager.clear()

                self._save_data()
                self._refresh_groups()
                self._refresh_account_list()
                self._update_batch_bar()
                self._update_detail_panel()

                action_text = "移动" if zh else "Moved"
            else:
                action_text = "复制" if zh else "Copied"

            # Exit multi-select mode
            self._exit_multi_select_mode()

            # Undo callback
            def undo_move():
                try:
                    # Reload target library state
                    target_state_now = library_service.load_library_state(target_library)
                    # Remove moved accounts from target
                    target_state_now.accounts = [a for a in target_state_now.accounts if a.email not in moved_emails]
                    library_service.save_library_state(target_library, target_state_now)

                    # Restore to current library if it was a move
                    if remove_from_current:
                        for account in moved_accounts:
                            if not any(a.email == account.email for a in self.state.accounts):
                                self.state.accounts.append(account)
                        if selected_was_moved and was_selected:
                            self.selected_account = was_selected
                        self._save_data()
                        self._refresh_groups()
                        self._refresh_account_list()
                        self._update_detail_panel()

                    self.toast.show_message(f"已撤销" if zh else "Undone")
                except Exception as e:
                    logger.error(f"Undo move failed: {e}")
                    self.toast.show_message("撤销失败" if zh else "Undo failed")

            # Show toast with undo
            self.toast.show_message(
                f"已{action_text} {count} 个账户到「{target_library.name}」" if zh else f"{action_text} {count} accounts to '{target_library.name}'",
                duration=4000,
                action_text="撤回" if zh else "Undo",
                action_callback=undo_move
            )

        except Exception as e:
            logger.error(f"Failed to move/copy accounts: {e}")
            self.toast.show_message("操作失败" if zh else "Operation failed")

    def _move_account_to_library(self, account: Account, target_library, remove_from_current: bool = True) -> None:
        """Move or copy a single account to another library."""
        zh = self.state.language == 'zh'
        try:
            from ..services.library_service import get_library_service
            from ..models.group import Group
            import copy

            library_service = get_library_service()

            # Load target library state
            target_state = library_service.load_library_state(target_library)

            # Check if account already exists in target (by email)
            if any(a.email == account.email for a in target_state.accounts):
                self.toast.show_message("账户已存在于目标库" if zh else "Account already exists in target library")
                return

            # Deep copy the account
            account_copy = copy.deepcopy(account)
            target_state.accounts.append(account_copy)

            # Create missing groups in target library
            target_group_names = {g.name for g in target_state.groups}
            for group_name in account_copy.groups:
                if group_name not in target_group_names:
                    # Find the group color from source library
                    source_group = next((g for g in self.state.groups if g.name == group_name), None)
                    color = source_group.color if source_group else "red"
                    target_state.groups.append(Group(name=group_name, color=color))
                    target_group_names.add(group_name)

            # Save target library
            library_service.save_library_state(target_library, target_state)

            # Remove from current library if it's a move operation
            if remove_from_current:
                if account in self.state.accounts:
                    self.state.accounts.remove(account)
                if self.selected_account == account:
                    self.selected_account = None
                self._save_data()
                self._refresh_groups()
                self._refresh_account_list()
                self._update_detail_panel()
                action_text = "移动" if zh else "Moved"
            else:
                action_text = "复制" if zh else "Copied"

            self.toast.show_message(f"已{action_text}到「{target_library.name}」" if zh else f"{action_text} to '{target_library.name}'")

        except Exception as e:
            logger.error(f"Failed to move/copy account: {e}")
            self.toast.show_message("操作失败" if zh else "Operation failed")

    def _batch_add_to_group(self, group_name: str) -> None:
        """Add selected accounts to a group."""
        if self.selection_manager.count == 0:
            return

        count = 0
        for account in self.selection_manager.items:
            if group_name not in account.groups:
                account.groups.append(group_name)
                count += 1

        if count > 0:
            self._save_data()
            self._refresh_account_list()
            self._update_detail_panel()
            self._refresh_groups()

            # Exit multi-select mode
            self._exit_multi_select_mode()

            zh = self.state.language == 'zh'
            self.toast.show_message(f"已添加 {count} 个账户到「{group_name}」" if zh else f"Added {count} accounts to '{group_name}'")

    def _batch_add_to_new_group(self) -> None:
        """Create a new group and add selected accounts to it."""
        zh = self.state.language == 'zh'

        name, ok = QInputDialog.getText(
            self,
            "新建分组" if zh else "New Group",
            "分组名称:" if zh else "Group name:"
        )

        if ok and name.strip():
            name = name.strip()
            # Check if group already exists
            if any(g.name == name for g in self.state.groups):
                self.toast.show_message(f"分组「{name}」已存在" if zh else f"Group '{name}' already exists")
                return

            # Create new group
            new_group = Group(name=name, color="blue")
            self.state.groups.append(new_group)

            # Add selected accounts to this group
            self._batch_add_to_group(name)

    def _batch_remove_from_group(self, group_name: str) -> None:
        """Remove selected accounts from a group with undo support."""
        if self.selection_manager.count == 0:
            return

        zh = self.state.language == 'zh'

        # Store affected accounts for undo
        affected_accounts = []
        for account in self.selection_manager.items:
            if group_name in account.groups:
                affected_accounts.append(account)
                account.groups.remove(group_name)

        count = len(affected_accounts)
        if count > 0:
            self._save_data()
            self._refresh_account_list()
            self._update_detail_panel()
            self._refresh_groups()

            # Exit multi-select mode
            self._exit_multi_select_mode()

            # Undo callback
            def undo_remove():
                for account in affected_accounts:
                    if group_name not in account.groups:
                        account.groups.append(group_name)
                self._save_data()
                self._refresh_account_list()
                self._update_detail_panel()
                self._refresh_groups()
                self.toast.show_message("已撤销" if zh else "Undone")

            # Show toast with undo
            self.toast.show_message(
                f"已从「{group_name}」移除 {count} 个账户" if zh else f"Removed {count} accounts from '{group_name}'",
                duration=4000,
                action_text="撤回" if zh else "Undo",
                action_callback=undo_remove
            )

    def _batch_copy(self) -> None:
        """Copy selected accounts info to clipboard in import format."""
        zh = self.state.language == 'zh'

        if self.selection_manager.count == 0:
            self.toast.show_message("请先选择账户" if zh else "Please select accounts first")
            return

        try:
            # Header line (template format)
            header = "邮箱----密码----辅助邮箱----2FA密钥" if zh else "email----password----backup_email----2fa_secret"

            lines = [header]
            for account in self.selection_manager.items:
                parts = [account.email or ""]
                parts.append(account.password or "")
                parts.append(getattr(account, 'backup_email', '') or "")
                parts.append(account.secret or "")
                lines.append("----".join(parts))

            text = '\n'.join(lines)
            QApplication.clipboard().setText(text)
            count = self.selection_manager.count

            # Exit multi-select mode
            self._exit_multi_select_mode()

            self.toast.show_message(f"已复制 {count} 个账户" if zh else f"Copied {count} accounts", center=True)
        except Exception as e:
            logger.error(f"Batch copy failed: {e}")
            self.toast.show_message("复制失败" if zh else "Copy failed")

    def _toggle_view_mode(self) -> None:
        """Toggle between list and card view."""
        self.list_view_mode = not self.list_view_mode
        self._update_icons()

        zh = self.state.language == 'zh'
        if self.list_view_mode:
            # List view: hide detail panel and card view, show full-width table
            self.selected_account = None
            self.detail_panel.hide()
            self.card_view_scroll.hide()
            self.list_panel.setMinimumWidth(0)
            self.list_panel.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
            self.table_view.show()
            self._refresh_table_view()
            self.toast.show_message("列表视图" if zh else "List view")
        else:
            # Card view: show detail panel and card view, hide table
            self.table_view.hide()
            self.list_panel.setFixedWidth(320)
            self.card_view_scroll.show()
            self.detail_panel.show()
            self._update_detail_panel()
            self._refresh_account_list()
            self.toast.show_message("卡片视图" if zh else "Card view")

    def _refresh_table_view(self) -> None:
        """Refresh the table view with current accounts."""
        t = get_theme()
        zh = self.state.language == 'zh'

        # Clear all existing cell widgets to prevent stale signal connections
        for row in range(self.table_view.rowCount()):
            for col in range(self.table_view.columnCount()):
                widget = self.table_view.cellWidget(row, col)
                if widget:
                    self.table_view.removeCellWidget(row, col)
                    widget.deleteLater()

        # Set headers based on multi-select mode
        first_col = "" if self.multi_select_mode else "#"
        headers = [first_col, "邮箱" if zh else "Email", "密码" if zh else "Password",
                   "辅助邮箱" if zh else "Backup", "2FA密钥" if zh else "2FA Key",
                   "验证码" if zh else "Code", "分组" if zh else "Groups",
                   "备注" if zh else "Notes"]
        self.table_view.setHorizontalHeaderLabels(headers)

        # Get filtered accounts
        accounts = self._get_filtered_accounts()
        self.table_view.setRowCount(len(accounts))

        # Store accounts list for reference
        self._table_accounts = accounts

        # Adjust first column width based on mode
        if self.multi_select_mode:
            self.table_view.setColumnWidth(0, 80)  # Wider for checkbox + ID
        else:
            self.table_view.setColumnWidth(0, 50)  # Just ID

        for row, account in enumerate(accounts):
            # First column: ID (with checkbox in multi-select mode)
            if self.multi_select_mode:
                # Checkbox + ID widget
                first_col_widget = QWidget()
                first_col_layout = QHBoxLayout(first_col_widget)
                first_col_layout.setContentsMargins(8, 0, 4, 0)
                first_col_layout.setSpacing(6)
                first_col_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                check_btn = QToolButton()
                check_btn.setFixedSize(18, 18)
                check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                is_checked = self.selection_manager.is_selected(account)
                check_btn.setIcon(QIcon(icon_checkbox(14, t.text_secondary) if is_checked else icon_checkbox_empty(14, t.text_tertiary)))
                check_btn.setStyleSheet("QToolButton { background: transparent; border: none; }")
                check_btn.clicked.connect(lambda checked, a=account, r=row: self._on_table_checkbox_clicked(a, r))
                first_col_layout.addWidget(check_btn)

                id_label = QLabel(f"#{row + 1}")
                id_label.setStyleSheet(f"color: {t.text_tertiary}; font-size: 12px;")
                first_col_layout.addWidget(id_label)

                self.table_view.setCellWidget(row, 0, first_col_widget)
                # Set empty item for background handling
                id_item = QTableWidgetItem()
                id_item.setData(Qt.ItemDataRole.UserRole + 1, account)
                self.table_view.setItem(row, 0, id_item)
            else:
                # ID number only
                self.table_view.removeCellWidget(row, 0)
                id_item = QTableWidgetItem(f"#{row + 1}")
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setForeground(QColor(t.text_tertiary))
                id_item.setData(Qt.ItemDataRole.UserRole + 1, account)
                self.table_view.setItem(row, 0, id_item)

            # Email column
            email_display = account.email if self.codes_visible else self._mask_email(account.email)
            email_item = QTableWidgetItem(email_display)
            email_item.setData(Qt.ItemDataRole.UserRole, account.email)
            email_item.setData(Qt.ItemDataRole.UserRole + 1, account)
            email_item.setForeground(QColor(t.text_primary))
            self.table_view.setItem(row, 1, email_item)

            # Password column
            pwd_display = account.password if self.codes_visible else ("••••••••" if account.password else "-")
            pwd_item = QTableWidgetItem(pwd_display)
            pwd_item.setData(Qt.ItemDataRole.UserRole, account.password)
            pwd_item.setForeground(QColor(t.text_secondary))
            self.table_view.setItem(row, 2, pwd_item)

            # Backup email column
            backup = getattr(account, 'backup', '') or getattr(account, 'backup_email', '') or ''
            backup_display = backup if self.codes_visible else (self._mask_email(backup) if backup else "-")
            backup_item = QTableWidgetItem(backup_display if backup else "-")
            backup_item.setData(Qt.ItemDataRole.UserRole, backup)
            backup_item.setForeground(QColor(t.text_secondary))
            self.table_view.setItem(row, 3, backup_item)

            # 2FA Key column
            secret_display = account.secret[:8] + "..." if account.secret and self.codes_visible else ("••••••••" if account.secret else "-")
            secret_item = QTableWidgetItem(secret_display)
            secret_item.setData(Qt.ItemDataRole.UserRole, account.secret)
            secret_item.setForeground(QColor(t.text_secondary))
            self.table_view.setItem(row, 4, secret_item)

            # Code column
            if account.secret:
                code = self.totp_service.generate_code_safe(account.secret)
                code_display = f"{code[:3]} {code[3:]}" if code and len(code) == 6 and self.codes_visible else "*** ***"
            else:
                code_display = "-"
                code = ""
            code_item = QTableWidgetItem(code_display)
            code_item.setData(Qt.ItemDataRole.UserRole, code)
            code_item.setForeground(QColor(t.success if account.secret else t.text_tertiary))
            self.table_view.setItem(row, 5, code_item)

            # Groups column - display as small tags (same style as card view)
            is_dark = get_theme_manager().is_dark
            groups_widget = QWidget()
            groups_widget.setObjectName(f"groupsWidget_{row}")
            groups_layout = QHBoxLayout(groups_widget)
            groups_layout.setContentsMargins(8, 0, 8, 0)
            groups_layout.setSpacing(4)
            groups_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            if account.groups:
                for group_name in account.groups[:5]:  # Max 5 tags
                    tag_label = QLabel(group_name)
                    tag_label.setFixedHeight(18)
                    if is_dark:
                        tag_label.setStyleSheet("""
                            QLabel {
                                background-color: #9CA3AF;
                                color: #111827;
                                padding: 0px 6px;
                                border: none;
                                border-radius: 3px;
                                font-size: 10px;
                                font-weight: 500;
                            }
                        """)
                    else:
                        tag_label.setStyleSheet(f"""
                            QLabel {{
                                background-color: rgba(120, 120, 128, 0.16);
                                color: {t.text_primary};
                                padding: 0px 6px;
                                border: none;
                                border-radius: 3px;
                                font-size: 10px;
                                font-weight: 500;
                            }}
                        """)
                    groups_layout.addWidget(tag_label)
                if len(account.groups) > 5:
                    more_label = QLabel(f"+{len(account.groups) - 5}")
                    more_label.setFixedHeight(18)
                    more_label.setStyleSheet(f"color: {t.text_tertiary}; font-size: 10px;")
                    groups_layout.addWidget(more_label)
            else:
                empty_label = QLabel("-")
                empty_label.setStyleSheet(f"color: {t.text_tertiary};")
                groups_layout.addWidget(empty_label)

            groups_layout.addStretch()
            self.table_view.setCellWidget(row, 6, groups_widget)
            # Also set an empty item for background handling
            groups_item = QTableWidgetItem()
            groups_item.setData(Qt.ItemDataRole.UserRole + 1, account)
            self.table_view.setItem(row, 6, groups_item)

            # Notes column
            notes_item = QTableWidgetItem(account.notes or "-")
            notes_item.setForeground(QColor(t.text_secondary if account.notes else t.text_tertiary))
            self.table_view.setItem(row, 7, notes_item)

            # Apply row background based on selection state
            is_row_selected = (row == self.selected_table_row)
            is_multi_selected = self.multi_select_mode and self.selection_manager.is_selected(account)

            if is_row_selected or is_multi_selected:
                # Same as card selection: t.bg_hover
                row_color = QColor(t.bg_hover)
            else:
                row_color = QColor(t.bg_primary)

            row_brush = QBrush(row_color)
            for col in range(8):
                item = self.table_view.item(row, col)
                if item:
                    item.setBackground(row_brush)
                # Also update cell widget background (for groups column)
                widget = self.table_view.cellWidget(row, col)
                if widget:
                    widget.setAutoFillBackground(True)
                    pal = widget.palette()
                    pal.setColor(widget.backgroundRole(), row_color)
                    widget.setPalette(pal)

    def _handle_table_selection(self, account: Account, row: int) -> None:
        """Unified table selection handler using SelectionManager.

        Handles multi-select with Shift modifier key for both
        cell clicks and checkbox clicks in table view.
        """
        modifiers = QApplication.keyboardModifiers()
        shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        # Use SelectionManager with table accounts list
        self.selection_manager.handle_click(account, row, self._table_accounts, shift_held)

        self._refresh_table_view()
        self._update_batch_bar()

    def _on_table_cell_clicked(self, row: int, column: int) -> None:
        """Handle table cell click - row selection and copy."""
        t = get_theme()
        zh = self.state.language == 'zh'

        # Get account for this row
        if not hasattr(self, '_table_accounts') or row >= len(self._table_accounts):
            return
        account = self._table_accounts[row]

        # In multi-select mode, skip column 0 (checkbox column) - handled by checkbox click
        if self.multi_select_mode and column == 0:
            return

        # In multi-select mode, use unified selection handler
        if self.multi_select_mode:
            self._handle_table_selection(account, row)
            return

        # Normal mode: Update row selection (highlight entire row in gray)
        old_selected_row = self.selected_table_row
        self.selected_table_row = row

        # Update old row background to default
        if old_selected_row >= 0 and old_selected_row != row:
            default_brush = QBrush(QColor(t.bg_primary))
            for col in range(8):
                old_item = self.table_view.item(old_selected_row, col)
                if old_item:
                    old_item.setBackground(default_brush)
                old_widget = self.table_view.cellWidget(old_selected_row, col)
                if old_widget:
                    old_widget.setAutoFillBackground(True)
                    pal = old_widget.palette()
                    pal.setColor(old_widget.backgroundRole(), QColor(t.bg_primary))
                    old_widget.setPalette(pal)

        # Update new row background (same as card selection: t.bg_hover)
        selected_color = QColor(t.bg_hover)
        selected_brush = QBrush(selected_color)
        for col in range(8):
            new_item = self.table_view.item(row, col)
            if new_item:
                new_item.setBackground(selected_brush)
            new_widget = self.table_view.cellWidget(row, col)
            if new_widget:
                new_widget.setAutoFillBackground(True)
                pal = new_widget.palette()
                pal.setColor(new_widget.backgroundRole(), selected_color)
                new_widget.setPalette(pal)

        # Skip ID/checkbox column for copy
        if column == 0:
            self.table_view.repaint()
            return

        # Handle groups column - no copy, just select row (right-click for edit)
        if column == 6:
            self.table_view.repaint()
            return

        # Notes column - click to start inline editing
        if column == 7:
            self.table_view.repaint()
            self._start_table_notes_edit(account, row)
            return

        # For other columns, copy to clipboard
        item = self.table_view.item(row, column)
        if not item:
            return

        # Get original (unmasked) value for columns 1-5
        if column in [1, 2, 3, 4, 5]:
            text = item.data(Qt.ItemDataRole.UserRole)
        else:
            text = item.text()

        if text and text != "-":
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

            # Visual feedback - use theme-appropriate highlight color
            is_dark = get_theme_manager().is_dark
            highlight_color = "#6B5A20" if is_dark else "#FEF9C3"  # Warm amber for dark mode, light yellow for light
            highlight_brush = QBrush(QColor(highlight_color))
            item.setBackground(highlight_brush)
            self.table_view.repaint()

            def restore_bg():
                # Restore to selected row color (t.bg_hover)
                item.setBackground(QBrush(QColor(t.bg_hover)))
                self.table_view.repaint()

            QTimer.singleShot(500, restore_bg)

            # Show toast
            column_names = ["#", "邮箱" if zh else "Email", "密码" if zh else "Password",
                          "辅助邮箱" if zh else "Backup", "2FA密钥" if zh else "2FA Key",
                          "验证码" if zh else "Code", "分组" if zh else "Groups", "备注" if zh else "Notes"]
            col_name = column_names[column] if column < len(column_names) else ""
            self.toast.show_message(f"已复制 {col_name}" if zh else f"Copied {col_name}")
        else:
            self.table_view.repaint()

    def _on_table_context_menu(self, pos) -> None:
        """Handle right-click context menu on table."""
        t = get_theme()
        zh = self.state.language == 'zh'
        ic = t.text_secondary

        # Get the item at click position
        item = self.table_view.itemAt(pos)
        if not item:
            return

        row = item.row()
        column = self.table_view.columnAt(pos.x())

        # Get account for this row
        if not hasattr(self, '_table_accounts') or row >= len(self._table_accounts):
            return
        account = self._table_accounts[row]

        # Column 6 is groups column - show groups edit menu
        if column == 6:
            self._show_table_groups_edit_menu(account, pos)
            return

        # For other columns, show edit/delete menu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """)

        # Column mapping: 0=checkbox/#, 1=email, 2=password, 3=backup, 4=secret, 5=code, 6=groups, 7=notes
        # Note: column 5 (verification code) is not editable - it's auto-generated from secret
        editable_columns = {
            1: ("email", "邮箱" if zh else "Email"),
            2: ("password", "密码" if zh else "Password"),
            3: ("backup", "辅助邮箱" if zh else "Backup Email"),
            4: ("secret", "2FA密钥" if zh else "2FA Secret"),
            7: ("notes", "备注" if zh else "Notes"),
        }

        # Edit action for editable columns
        if column in editable_columns:
            field_name, field_label = editable_columns[column]
            edit_action = menu.addAction(QIcon(icon_edit(14, ic)), f"编辑{field_label}" if zh else f"Edit {field_label}")
            edit_action.triggered.connect(lambda: self._start_table_cell_edit(account, row, column, field_name))

        # Copy action
        copy_action = menu.addAction(QIcon(icon_copy(14, ic)), "复制" if zh else "Copy")
        copy_action.triggered.connect(lambda: self._copy_table_cell(account, column))

        menu.addSeparator()

        # Delete row action
        delete_action = menu.addAction(QIcon(icon_trash(14, t.error)), "删除账户" if zh else "Delete Account")
        delete_action.triggered.connect(lambda: self._delete_single_account(account))

        menu.exec(self.table_view.mapToGlobal(pos))

    def _start_table_cell_edit(self, account: Account, row: int, column: int, field_name: str) -> None:
        """Start inline editing for a table cell with expandable width."""
        t = get_theme()
        zh = self.state.language == 'zh'
        is_dark = get_theme_manager().is_dark

        # Get current value
        current_value = getattr(account, field_name, '') or ''

        # Get cell geometry
        cell_rect = self.table_view.visualRect(self.table_view.model().index(row, column))

        # Selection color (green)
        selection_bg = "#065F46" if is_dark else "#10B981"
        selection_color = "#FFFFFF"

        # Create floating edit widget
        # Use appropriate background for dark/light mode
        edit_bg = "#374151" if is_dark else "#F3F4F6"
        text_color = "#F9FAFB" if is_dark else "#111827"

        edit = QLineEdit(self.table_view.viewport())
        edit.setObjectName("tableCellEdit")
        edit.setText(current_value)
        edit.setAutoFillBackground(True)

        # Use palette for reliable background color
        from PyQt6.QtGui import QPalette, QColor
        palette = edit.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(edit_bg))
        palette.setColor(QPalette.ColorRole.Text, QColor(text_color))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(selection_bg))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(selection_color))
        edit.setPalette(palette)

        edit.setStyleSheet(f"""
            QLineEdit#tableCellEdit {{
                background-color: {edit_bg};
                color: {text_color};
                border: none;
                padding: 0px 8px;
                selection-background-color: {selection_bg};
                selection-color: {selection_color};
            }}
        """)

        # Calculate width based on content
        font_metrics = edit.fontMetrics()
        text_width = font_metrics.horizontalAdvance(current_value) + 30  # padding
        min_width = max(cell_rect.width(), text_width)
        max_width = self.table_view.viewport().width() - cell_rect.x() - 5

        edit.setFixedHeight(cell_rect.height())
        edit.setMinimumWidth(min(min_width, max_width))
        edit.move(cell_rect.x(), cell_rect.y())
        edit.show()
        edit.setFocus()
        edit.selectAll()

        def finish_edit():
            if edit.isVisible():
                new_value = edit.text().strip()
                setattr(account, field_name, new_value)
                edit.hide()
                edit.deleteLater()
                self._save_data()
                self._refresh_table_view()

        def cancel_edit():
            edit.hide()
            edit.deleteLater()
            self._refresh_table_view()

        edit.returnPressed.connect(finish_edit)

        # Handle focus out
        def on_focus_out(event):
            finish_edit()
        edit.focusOutEvent = on_focus_out

        # Handle escape key
        def key_press(event):
            if event.key() == Qt.Key.Key_Escape:
                cancel_edit()
            else:
                QLineEdit.keyPressEvent(edit, event)
        edit.keyPressEvent = key_press

    def _copy_table_cell(self, account: Account, column: int) -> None:
        """Copy table cell value to clipboard."""
        zh = self.state.language == 'zh'

        # Column mapping: 0=checkbox/#, 1=email, 2=password, 3=backup, 4=secret, 5=code, 6=groups, 7=notes
        if column == 5:
            # Column 5 is verification code - generate it
            code = self.totp_service.generate_code_safe(account.secret) if account.secret else ''
            value = code
        else:
            column_fields = {
                1: account.email,
                2: account.password,
                3: account.backup,
                4: account.secret,
                7: account.notes,
            }
            value = column_fields.get(column, '')

        if value:
            QApplication.clipboard().setText(value)
            self.toast.show_message("已复制" if zh else "Copied", center=True)

    def _show_table_groups_edit_menu(self, account, pos) -> None:
        """Show groups edit menu for table row."""
        t = get_theme()
        zh = self.state.language == 'zh'

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
            QMenu::item:disabled {{
                color: {t.text_tertiary};
            }}
        """)

        # Add to group submenu
        add_menu = menu.addMenu("添加到分组" if zh else "Add to group")
        for group in self.state.groups:
            if group.name not in account.groups:
                action = add_menu.addAction(group.name)
                action.triggered.connect(lambda checked, g=group.name, a=account: self._table_add_to_group(a, g))

        if not any(g.name not in account.groups for g in self.state.groups):
            no_action = add_menu.addAction("无可用分组" if zh else "No available groups")
            no_action.setEnabled(False)

        # Remove from group submenu (only if account has groups)
        if account.groups:
            remove_menu = menu.addMenu("从分组移除" if zh else "Remove from group")
            for group_name in account.groups:
                action = remove_menu.addAction(group_name)
                action.triggered.connect(lambda checked, g=group_name, a=account: self._table_remove_from_group(a, g))

        menu.addSeparator()

        # Delete account action
        delete_action = menu.addAction(QIcon(icon_trash(14, t.error)), "删除账户" if zh else "Delete Account")
        delete_action.triggered.connect(lambda: self._delete_single_account(account))

        # Show at click position
        menu.exec(self.table_view.mapToGlobal(pos))

    def _table_add_to_group(self, account, group_name: str) -> None:
        """Add account to group from table context menu."""
        if group_name not in account.groups:
            account.groups.append(group_name)
            self._save_data()
            self._refresh_table_view()

    def _table_remove_from_group(self, account, group_name: str) -> None:
        """Remove account from group from table context menu."""
        if group_name in account.groups:
            account.groups.remove(group_name)
            self._save_data()
            self._refresh_table_view()

    def _start_table_notes_edit(self, account, row: int) -> None:
        """Start inline editing for notes in table view."""
        t = get_theme()
        zh = self.state.language == 'zh'

        # Create inline edit widget - no border, just color change
        edit = QLineEdit()
        edit.setText(account.notes or "")
        edit.setPlaceholderText("添加备注..." if zh else "Add notes...")
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.bg_hover};
                color: {t.text_primary};
                border: none;
                padding: 0px 8px;
            }}
        """)

        # Store reference for cleanup
        self._table_notes_edit = edit
        self._table_notes_account = account
        self._table_notes_row = row
        self._table_notes_editing = True

        # Connect signals - Enter to save
        edit.returnPressed.connect(self._finish_table_notes_edit)

        # Set as cell widget
        self.table_view.setCellWidget(row, 7, edit)
        edit.setFocus()
        edit.selectAll()

    def _finish_table_notes_edit(self) -> None:
        """Finish inline notes editing and save."""
        if not hasattr(self, '_table_notes_editing') or not self._table_notes_editing:
            return
        if not hasattr(self, '_table_notes_edit') or not self._table_notes_edit:
            return

        # Mark as not editing first to prevent re-entry
        self._table_notes_editing = False

        edit = self._table_notes_edit
        account = self._table_notes_account
        row = self._table_notes_row

        # Get new notes value
        new_notes = edit.text().strip()

        # Update account if changed
        if new_notes != (account.notes or ""):
            account.notes = new_notes if new_notes else None
            self._save_data()

        # Remove the cell widget first
        self.table_view.removeCellWidget(row, 7)

        # Clean up references
        self._table_notes_edit = None
        self._table_notes_account = None
        self._table_notes_row = None

        # Refresh to restore normal cell
        self._refresh_table_view()

        # Also update detail panel if this account is selected
        if self.selected_account == account:
            self._update_detail_panel()

    def _on_table_checkbox_clicked(self, account, row: int) -> None:
        """Handle table checkbox click for multi-select."""
        if not hasattr(self, '_table_accounts'):
            return
        self._handle_table_selection(account, row)

    def _mask_email(self, email: str) -> str:
        """Mask email for privacy display."""
        if not email or '@' not in email:
            return email[:3] + "***" if email else ""
        local, domain = email.split('@', 1)
        return f"{local[:3]}***@{domain}"

    def _show_settings_menu(self) -> None:
        """Show/hide settings dropdown menu."""
        if not self._should_show_menu("settings"):
            return

        t = get_theme()
        zh = self.state.language == 'zh'

        menu = QMenu(self)
        self._settings_menu = menu
        self._track_menu_close(menu, "settings")
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px;
                min-width: 140px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t.border};
                margin: 4px 8px;
            }}
        """)

        # Theme toggle - show what it will switch to
        theme_text = "浅色模式" if self.theme_manager.is_dark else "深色模式"
        if not zh:
            theme_text = "Light Mode" if self.theme_manager.is_dark else "Dark Mode"
        theme_action = menu.addAction(theme_text)
        theme_action.triggered.connect(self._toggle_theme)

        # Language toggle
        lang_text = "切换为 English" if zh else "Switch to 中文"
        lang_action = menu.addAction(lang_text)
        lang_action.triggered.connect(self._toggle_language)

        menu.addSeparator()

        # Archive history
        archive_action = menu.addAction("存档历史" if zh else "Archives")
        archive_action.triggered.connect(self._show_archive_dialog)

        # Trash
        trash_count = len(self.state.trash) if hasattr(self.state, 'trash') else 0
        trash_text = "回收站" if zh else "Trash"
        if trash_count > 0:
            trash_text += f" ({trash_count})"
        trash_action = menu.addAction(trash_text)
        trash_action.triggered.connect(self._show_trash_dialog)

        # Position: bottom-left of button
        btn_rect = self.btn_settings.rect()
        global_pos = self.btn_settings.mapToGlobal(btn_rect.bottomLeft())
        menu_width = 160
        global_pos.setX(global_pos.x() - menu_width + btn_rect.width())

        menu.aboutToHide.connect(lambda: setattr(self, '_settings_menu', None))
        menu.exec(global_pos)

    def _show_import_dialog(self) -> None:
        """Show import dialog for batch importing accounts."""
        from .dialogs.import_dialog import ImportDialog

        dialog = ImportDialog(self, language=self.state.language)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            accounts = dialog.get_accounts()
            if accounts:
                zh = self.state.language == 'zh'

                # Check for duplicates (by email)
                existing_emails = {a.email.lower() for a in self.state.accounts}
                duplicates = [a for a in accounts if a.email.lower() in existing_emails]
                new_accounts = [a for a in accounts if a.email.lower() not in existing_emails]

                accounts_to_import = []
                updated_count = 0

                if duplicates:
                    # Show duplicate handling dialog
                    action = self._show_duplicate_dialog(len(duplicates), len(new_accounts))

                    if action == "cancel":
                        return
                    elif action == "skip":
                        # Only import non-duplicates
                        accounts_to_import = new_accounts
                    elif action == "update":
                        # Update existing accounts with new data, then add new ones
                        for dup_account in duplicates:
                            for existing in self.state.accounts:
                                if existing.email.lower() == dup_account.email.lower():
                                    # Update existing account with new data
                                    existing.password = dup_account.password or existing.password
                                    existing.secret = dup_account.secret or existing.secret
                                    if hasattr(dup_account, 'backup'):
                                        existing.backup = dup_account.backup or getattr(existing, 'backup', '')
                                    break
                        accounts_to_import = new_accounts
                        updated_count = len(duplicates)
                    else:  # "all" - import all including duplicates
                        accounts_to_import = accounts
                else:
                    accounts_to_import = accounts

                if accounts_to_import:
                    # Add imported accounts
                    max_id = max((a.id or 0 for a in self.state.accounts), default=0)
                    for i, account in enumerate(accounts_to_import):
                        account.id = max_id + i + 1
                        self.state.accounts.append(account)

                self._save_data()
                self._refresh_groups()
                self._refresh_account_list()

                # Show result message
                imported_count = len(accounts_to_import)

                if updated_count > 0:
                    msg = f"已导入 {imported_count} 个，更新 {updated_count} 个账户" if zh else f"Imported {imported_count}, updated {updated_count} accounts"
                elif imported_count > 0:
                    msg = f"已导入 {imported_count} 个账户" if zh else f"Imported {imported_count} accounts"
                else:
                    msg = "没有新账户导入" if zh else "No new accounts imported"
                self.toast.show_message(msg)

    def _show_duplicate_dialog(self, dup_count: int, new_count: int) -> str:
        """Show dialog to handle duplicate accounts. Returns: 'skip', 'update', 'all', or 'cancel'."""
        zh = self.state.language == 'zh'
        t = get_theme()

        dialog = QDialog(self)
        dialog.setWindowTitle("检测到重复账户" if zh else "Duplicates Detected")
        dialog.setModal(True)
        dialog.setFixedWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Message
        msg = QLabel(
            f"发现 {dup_count} 个重复账户（邮箱已存在）\n另有 {new_count} 个新账户\n\n请选择处理方式：" if zh else
            f"Found {dup_count} duplicate accounts (email exists)\nand {new_count} new accounts\n\nHow to handle duplicates?"
        )
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 14px; color: {t.text_primary};")
        layout.addWidget(msg)

        result = {"action": "cancel"}

        # Button style
        btn_style = f"""
            QPushButton {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 10px 16px;
                font-size: 13px;
                color: {t.text_primary};
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {t.bg_hover};
            }}
        """

        # Skip button
        btn_skip = QPushButton("跳过重复，只导入新账户" if zh else "Skip duplicates, import new only")
        btn_skip.setStyleSheet(btn_style)
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.clicked.connect(lambda: (result.update({"action": "skip"}), dialog.accept()))
        layout.addWidget(btn_skip)

        # Update button
        btn_update = QPushButton("更新重复项，并导入新账户" if zh else "Update duplicates and import new")
        btn_update.setStyleSheet(btn_style)
        btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_update.clicked.connect(lambda: (result.update({"action": "update"}), dialog.accept()))
        layout.addWidget(btn_update)

        # Import all button
        btn_all = QPushButton("全部导入（允许重复）" if zh else "Import all (allow duplicates)")
        btn_all.setStyleSheet(btn_style)
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.clicked.connect(lambda: (result.update({"action": "all"}), dialog.accept()))
        layout.addWidget(btn_all)

        # Cancel button
        layout.addSpacing(8)
        btn_cancel = QPushButton("取消" if zh else "Cancel")
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 8px;
                font-size: 13px;
                color: {t.text_tertiary};
            }}
            QPushButton:hover {{
                color: {t.text_secondary};
            }}
        """)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        layout.addWidget(btn_cancel, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.setStyleSheet(f"QDialog {{ background-color: {t.bg_primary}; }}")
        dialog.exec()

        return result["action"]

    def _show_add_account(self) -> None:
        """Show add account dialog."""
        from .dialogs.account_dialog import AccountDialog

        dialog = AccountDialog(
            self,
            account=None,
            groups=self.state.groups,
            language=self.state.language
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            account = dialog.get_account()
            if account:
                # Generate ID
                max_id = max((a.id or 0 for a in self.state.accounts), default=0)
                account.id = max_id + 1

                self.state.accounts.append(account)
                self._save_data()
                self._refresh_groups()
                self._refresh_account_list()

                # Select the new account
                self.selected_account = account
                self._highlight_selected_account()
                self._update_detail_panel()

                zh = self.state.language == 'zh'
                self.toast.show_message("已添加账户" if zh else "Account added")

    def _edit_account(self) -> None:
        """Toggle inline edit mode for selected account."""
        if not self.selected_account:
            return

        t = get_theme()
        zh = self.state.language == 'zh'

        if self.detail_edit_mode:
            # Save changes and exit edit mode
            self._save_edited_account()
            self.detail_edit_mode = False
            self.btn_edit.setIcon(QIcon(icon_edit(14, t.text_secondary)))
            self._update_detail_fields()
            self.toast.show_message("已保存" if zh else "Saved")
        else:
            # Enter edit mode
            self.detail_edit_mode = True
            self.btn_edit.setIcon(QIcon(icon_check(14, t.success)))
            self._update_detail_fields()

    def _save_edited_account(self) -> None:
        """Save changes from editable fields to the account."""
        if not self.selected_account or not self.editable_fields:
            return

        changed = False

        if 'email' in self.editable_fields:
            new_email = self.editable_fields['email'].text().strip()
            if new_email and new_email != self.selected_account.email:
                self.selected_account.email = new_email
                changed = True

        if 'password' in self.editable_fields:
            new_pwd = self.editable_fields['password'].text()
            if new_pwd != self.selected_account.password:
                self.selected_account.password = new_pwd
                changed = True

        if 'backup' in self.editable_fields:
            new_backup = self.editable_fields['backup'].text().strip()
            if hasattr(self.selected_account, 'backup'):
                if new_backup != self.selected_account.backup:
                    self.selected_account.backup = new_backup
                    changed = True

        if 'secret' in self.editable_fields:
            new_secret = self.editable_fields['secret'].text().strip()
            if new_secret != self.selected_account.secret:
                self.selected_account.secret = new_secret
                changed = True

        if changed:
            self._save_data()
            self._refresh_account_list()

    def _open_tag_editor(self) -> None:
        """Show inline tag editor menu for the selected account."""
        if not self.selected_account:
            return

        t = get_theme()
        zh = self.state.language == 'zh'

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """)

        # Add existing groups as checkable items
        for group in self.state.groups:
            action = menu.addAction(group.name)
            action.setCheckable(True)
            action.setChecked(group.name in self.selected_account.groups)
            action.toggled.connect(lambda checked, g=group.name: self._toggle_account_tag(g, checked))

        if self.state.groups:
            menu.addSeparator()

        # Add "New group" option
        new_action = menu.addAction("+ " + ("新建分组" if zh else "New group"))
        new_action.triggered.connect(self._add_new_tag_to_account)

        # Show menu at cursor position
        menu.exec(QApplication.instance().activeWindow().cursor().pos())

    def _toggle_account_tag(self, group_name: str, checked: bool) -> None:
        """Toggle a tag on the selected account."""
        if not self.selected_account:
            return

        if checked:
            if group_name not in self.selected_account.groups:
                self.selected_account.groups.append(group_name)
        else:
            if group_name in self.selected_account.groups:
                self.selected_account.groups.remove(group_name)

        self._save_data()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()

    def _create_inline_tag(self) -> None:
        """Create a new group from inline input and add it to the selected account."""
        if not self.selected_account or not hasattr(self, 'new_tag_input'):
            return

        name = self.new_tag_input.text().strip()
        if not name:
            return

        # Check if group already exists
        existing = next((g for g in self.state.groups if g.name == name), None)
        if not existing:
            # Create new group
            new_group = Group(name=name, color="blue")
            self.state.groups.append(new_group)

        # Add to account
        if name not in self.selected_account.groups:
            self.selected_account.groups.append(name)

        self.new_tag_input.clear()
        self._save_data()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()

    def _on_tag_input_finished(self) -> None:
        """Handle when tag input loses focus - save if has content, otherwise cancel."""
        if hasattr(self, 'new_tag_input'):
            if self.new_tag_input.text().strip():
                self._create_inline_tag()
            else:
                self.new_tag_input.clear()
                self.new_tag_input.setFixedWidth(36)

    def _on_tag_input_text_changed(self, text: str) -> None:
        """Auto-expand tag input based on text content."""
        if not hasattr(self, 'new_tag_input'):
            return
        if text:
            # Calculate width based on text with extra padding for visibility
            fm = self.new_tag_input.fontMetrics()
            text_width = fm.horizontalAdvance(text) + 32  # padding + margin
            new_width = max(36, min(text_width, 150))
            self.new_tag_input.setFixedWidth(new_width)
        else:
            self.new_tag_input.setFixedWidth(36)

    def _show_tag_context_menu(self, pos, group_name: str, btn: QPushButton) -> None:
        """Show context menu for tag with delete option."""
        t = get_theme()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t.bg_secondary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
                color: {t.text_primary};
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
        """)

        zh = self.state.language == 'zh'
        delete_action = menu.addAction("删除标签" if zh else "Delete Tag")
        delete_action.triggered.connect(lambda: self._delete_tag(group_name))

        menu.exec(btn.mapToGlobal(pos))

    def _delete_tag(self, group_name: str) -> None:
        """Delete a tag/group from the system with confirmation and undo."""
        zh = self.state.language == 'zh'
        t = get_theme()
        is_dark = get_theme_manager().is_dark

        # Count accounts using this group
        count = sum(1 for acc in self.state.accounts if group_name in acc.groups)

        # Dark mode: use colors matching library panel (softer grays)
        # Light mode: use standard theme colors
        dialog_bg = "#374151" if is_dark else t.bg_primary
        text_color = "#F3F4F6" if is_dark else t.text_primary
        cancel_bg = "#4B5563" if is_dark else t.bg_tertiary
        cancel_hover = "#6B7280" if is_dark else t.bg_hover
        error_color = "#DC2626" if is_dark else t.error
        error_hover = "#B91C1C" if is_dark else "#DC2626"

        # Create styled confirmation dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("确认删除" if zh else "Confirm Delete")
        dialog.setFixedWidth(320)

        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {dialog_bg};
                border-radius: 8px;
            }}
            QLabel {{
                color: {text_color};
                font-size: 13px;
            }}
            QPushButton {{
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Message
        msg = f"确定要删除标签「{group_name}」吗？" if zh else f"Delete tag '{group_name}'?"
        if count > 0:
            msg += f"\n\n{count} 个账户正在使用此标签" if zh else f"\n\n{count} accounts use this tag"

        label = QLabel(msg)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("取消" if zh else "Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cancel_bg};
                border: none;
                color: {text_color};
            }}
            QPushButton:hover {{
                background-color: {cancel_hover};
            }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("删除" if zh else "Delete")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {error_color};
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {error_hover};
            }}
        """)
        delete_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Backup for undo
        deleted_group = next((g for g in self.state.groups if g.name == group_name), None)
        affected_accounts = [(acc.id, list(acc.groups)) for acc in self.state.accounts if group_name in acc.groups]
        group_index = next((i for i, g in enumerate(self.state.groups) if g.name == group_name), 0)

        # Remove from all accounts
        for acc in self.state.accounts:
            if group_name in acc.groups:
                acc.groups.remove(group_name)

        # Remove from groups list
        self.state.groups = [g for g in self.state.groups if g.name != group_name]

        self._save_data()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()

        def undo_delete():
            """Undo the tag deletion."""
            if deleted_group:
                # Restore group at original position
                self.state.groups.insert(group_index, deleted_group)
                # Restore group to affected accounts
                for acc_id, original_groups in affected_accounts:
                    acc = next((a for a in self.state.accounts if a.id == acc_id), None)
                    if acc:
                        acc.groups = original_groups
                self._save_data()
                self._refresh_groups()
                self._refresh_account_list()
                self._update_detail_panel()
                self.toast.show_message(f"已恢复「{group_name}」" if zh else f"Restored '{group_name}'")

        # Show toast with undo option
        self.toast.show_message(
            f"已删除标签「{group_name}」" if zh else f"Deleted tag '{group_name}'",
            duration=5000,
            action_text="撤销" if zh else "Undo",
            action_callback=undo_delete
        )

    def _on_detail_panel_click(self, event) -> None:
        """Clear focus when clicking on detail panel background."""
        focused = self.focusWidget()
        if isinstance(focused, QLineEdit):
            focused.clearFocus()

    def _delete_account(self) -> None:
        """Delete selected account with undo support."""
        if not self.selected_account:
            return

        zh = self.state.language == 'zh'
        msg = f"确定要删除账户 {self.selected_account.email} 吗？" if zh else f"Delete account {self.selected_account.email}?"

        if not self._show_delete_confirmation(msg):
            return

        # Store for undo
        deleted_account = self.selected_account

        # Move to trash instead of permanent delete
        if hasattr(self.state, 'trash'):
            self.state.trash.append(self.selected_account)

        self.state.accounts.remove(self.selected_account)
        self.selected_account = None

        self._save_data()
        self._refresh_groups()
        self._refresh_account_list()
        self._update_detail_panel()

        # Undo callback
        def undo_delete():
            if hasattr(self.state, 'trash') and deleted_account in self.state.trash:
                self.state.trash.remove(deleted_account)
            self.state.accounts.append(deleted_account)
            self.selected_account = deleted_account
            self._save_data()
            self._refresh_groups()
            self._refresh_account_list()
            self._update_detail_panel()
            self.toast.show_message("已恢复" if zh else "Restored")

        # Show toast with undo
        self.toast.show_message(
            "已删除账户" if zh else "Account deleted",
            duration=4000,
            action_text="撤回" if zh else "Undo",
            action_callback=undo_delete
        )

    def _copy_totp_code(self) -> None:
        """Copy TOTP code to clipboard."""
        if not self.selected_account or not self.selected_account.secret:
            return

        zh = self.state.language == 'zh'
        code = self.totp_service.generate_code_safe(self.selected_account.secret)
        if code:
            QApplication.clipboard().setText(code)

            t = get_theme()
            self.btn_copy_totp.setIcon(QIcon(icon_check(18, t.success)))

            # Show toast notification
            self.toast.show_message("已复制：验证码" if zh else "Copied: Verification Code", center=True)

            if self.copied_toast_timer:
                self.copied_toast_timer.stop()

            self.copied_toast_timer = QTimer(self)
            self.copied_toast_timer.setSingleShot(True)
            self.copied_toast_timer.timeout.connect(
                lambda: self.btn_copy_totp.setIcon(QIcon(icon_copy(18, t.text_secondary)))
            )
            self.copied_toast_timer.start(2000)

    def _save_data(self) -> None:
        """Save application data."""
        self.state.theme = self.theme_manager.mode.value
        current = self.library_service.get_current_library()
        self.library_service.save_library_state(current, self.state)

    def mousePressEvent(self, event) -> None:
        """Clear focus from inputs when clicking elsewhere."""
        focused = self.focusWidget()
        if isinstance(focused, QLineEdit):
            focused.clearFocus()
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:
        """Handle window close - auto archive and save."""
        # Save current data
        self._save_data()

        # Create archive
        try:
            self.archive_service.create_archive(self.state)
            logger.info("Auto-archived on exit")
        except Exception as e:
            logger.error(f"Failed to create archive on exit: {e}")

        event.accept()
