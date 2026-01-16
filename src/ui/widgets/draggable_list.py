"""
Draggable list widget for reorderable items.
"""

from typing import Optional, Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QListWidget, QWidget


class DraggableGroupList(QListWidget):
    """
    Custom QListWidget that calls a callback after drag-drop reordering.

    This widget enables drag-and-drop reordering of items and notifies
    the parent when the order changes.
    """

    def __init__(
        self,
        reorder_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the draggable list.

        Args:
            reorder_callback: Function to call after items are reordered.
            parent: Parent widget (optional).
        """
        super().__init__(parent)
        self.reorder_callback = reorder_callback

    def dropEvent(self, event) -> None:
        """
        Handle drop event and trigger reorder callback.

        Args:
            event: The drop event.
        """
        super().dropEvent(event)

        # Call the reorder callback after the drop is complete
        # Use QTimer.singleShot to ensure the drop operation is fully processed
        if self.reorder_callback:
            QTimer.singleShot(0, self.reorder_callback)

    def set_reorder_callback(self, callback: Callable[[], None]) -> None:
        """
        Set or update the reorder callback.

        Args:
            callback: Function to call after items are reordered.
        """
        self.reorder_callback = callback
