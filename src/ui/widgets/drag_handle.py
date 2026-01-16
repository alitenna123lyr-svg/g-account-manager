"""
Drag handle widget for initiating drag operations.
"""

from typing import Optional

from PyQt6.QtCore import Qt, QMimeData, QPoint
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QWidget


class DragHandle(QLabel):
    """
    Custom drag handle that initiates drag on the parent QListWidget.

    This widget displays a drag icon and handles mouse events to start
    drag-and-drop operations for reordering list items.
    """

    # Minimum distance in pixels to trigger drag
    DRAG_THRESHOLD = 10

    def __init__(
        self,
        list_widget: QListWidget,
        list_item: QListWidgetItem,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the drag handle.

        Args:
            list_widget: The parent list widget.
            list_item: The list item this handle belongs to.
            parent: Parent widget (optional).
        """
        super().__init__("\u22ee\u22ee", parent)  # ⋮⋮ vertical ellipsis

        self.list_widget = list_widget
        self.list_item = list_item
        self.drag_start_pos: Optional[QPoint] = None

        # Styling
        self.setFixedWidth(20)
        self.setStyleSheet(
            "color: #9CA3AF; "
            "font-size: 14px; "
            "font-weight: bold; "
            "background: transparent; "
            "border: none;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event) -> None:
        """
        Handle mouse press to start tracking drag.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            # Select the item in the list
            self.list_widget.setCurrentItem(self.list_item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """
        Handle mouse move to initiate drag if threshold exceeded.

        Args:
            event: The mouse event.
        """
        if self.drag_start_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            # Calculate distance from start position
            distance = (event.pos() - self.drag_start_pos).manhattanLength()

            if distance >= self.DRAG_THRESHOLD:
                # Start drag operation
                self.list_widget.setCurrentItem(self.list_item)

                drag = QDrag(self.list_widget)
                mime_data = QMimeData()

                # Store row index in mime data
                row = self.list_widget.row(self.list_item)
                mime_data.setData("application/x-qabstractitemmodeldatalist", b"")
                mime_data.setText(str(row))

                drag.setMimeData(mime_data)
                drag.exec(Qt.DropAction.MoveAction)

                # Reset drag start position
                self.drag_start_pos = None

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """
        Handle mouse release to reset drag state.

        Args:
            event: The mouse event.
        """
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)
