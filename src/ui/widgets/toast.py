"""
Toast notification widget for showing temporary messages.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from ..styles import TOAST_STYLE
from ...config.settings import Settings


class ToastNotification(QWidget):
    """
    Small popup notification that disappears after a timeout.

    This widget displays a brief message to the user and automatically
    hides after a configurable duration.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the toast notification.

        Args:
            parent: Parent widget (optional).
        """
        super().__init__(parent)

        # Window flags for floating notification
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label for message
        self.label = QLabel()
        self.label.setStyleSheet(TOAST_STYLE)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # Start hidden
        self.hide()

    def show_message(
        self,
        message: str,
        parent_widget: Optional[QWidget] = None,
        duration: int = Settings.TOAST_DURATION
    ) -> None:
        """
        Show toast message near the center of parent widget.

        Args:
            message: The message to display.
            parent_widget: Widget to center the toast on (optional).
            duration: How long to show the toast in milliseconds.
        """
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

    def show_at_position(
        self,
        message: str,
        x: int,
        y: int,
        duration: int = Settings.TOAST_DURATION
    ) -> None:
        """
        Show toast message at a specific position.

        Args:
            message: The message to display.
            x: X coordinate.
            y: Y coordinate.
            duration: How long to show the toast in milliseconds.
        """
        self.label.setText(message)
        self.label.adjustSize()
        self.adjustSize()
        self.move(x, y)
        self.show()
        QTimer.singleShot(duration, self.hide)
