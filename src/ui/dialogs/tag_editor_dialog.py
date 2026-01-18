"""
Tag editor dialog for managing account tags with color picker.
"""

from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ...models.group import Group
from ...config.constants import GROUP_COLORS, GROUP_COLOR_NAMES
from ..theme import get_theme


class ColorButton(QPushButton):
    """A button that displays a color and can be selected."""

    def __init__(self, color_name: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.color_hex = color_hex
        self.selected = False
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def set_selected(self, selected: bool):
        """Set the selection state."""
        self.selected = selected
        self._update_style()

    def _update_style(self):
        """Update button style based on selection state."""
        border = "2px solid #000" if self.selected else "1px solid rgba(0,0,0,0.1)"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                border: {border};
                border-radius: 14px;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(0,0,0,0.3);
            }}
        """)


class TagChip(QFrame):
    """A tag chip that can be removed."""

    removed = pyqtSignal(str)  # Emits tag name when removed
    edit_requested = pyqtSignal(str)  # Emits tag name when edit is requested

    def __init__(self, name: str, color_hex: str, removable: bool = True, parent=None):
        super().__init__(parent)
        self.tag_name = name
        self.color_hex = color_hex

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Color indicator
        color_dot = QLabel()
        color_dot.setFixedSize(8, 8)
        color_dot.setStyleSheet(f"""
            background-color: {color_hex};
            border-radius: 4px;
        """)
        layout.addWidget(color_dot)

        # Tag name
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 12px; font-weight: 500;")
        layout.addWidget(name_label)

        if removable:
            # Remove button
            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(16, 16)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                    color: #666;
                    padding: 0;
                }
                QPushButton:hover {
                    color: #ef4444;
                }
            """)
            remove_btn.clicked.connect(lambda: self.removed.emit(self.tag_name))
            layout.addWidget(remove_btn)

        t = get_theme()
        self.setStyleSheet(f"""
            TagChip {{
                background-color: {self._get_bg_color()};
                border: 1px solid {color_hex}40;
                border-radius: 4px;
            }}
        """)

    def _get_bg_color(self) -> str:
        """Get background color (lighter version of tag color)."""
        return f"{self.color_hex}20"


class TagEditorDialog(QDialog):
    """Dialog for editing account tags with color picker."""

    tags_changed = pyqtSignal(list)  # Emits list of tag names

    def __init__(self, parent=None, current_tags: List[str] = None,
                 available_groups: List[Group] = None, language: str = 'zh'):
        super().__init__(parent)
        self.language = language
        self.current_tags = list(current_tags) if current_tags else []
        self.available_groups = available_groups or []
        self.new_tag_color = 'blue'  # Default color for new tags

        self._init_ui()
        self._apply_theme()
        self._update_display()

    def _init_ui(self):
        """Initialize the dialog UI."""
        zh = self.language == 'zh'

        self.setWindowTitle("编辑标签" if zh else "Edit Tags")
        self.setMinimumSize(400, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("编辑标签" if zh else "Edit Tags")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # Current tags section
        current_section = QWidget()
        current_layout = QVBoxLayout(current_section)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.setSpacing(8)

        current_label = QLabel("当前标签" if zh else "Current Tags")
        current_label.setObjectName("sectionLabel")
        current_layout.addWidget(current_label)

        self.current_tags_container = QWidget()
        self.current_tags_layout = QHBoxLayout(self.current_tags_container)
        self.current_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.current_tags_layout.setSpacing(8)
        self.current_tags_layout.addStretch()
        current_layout.addWidget(self.current_tags_container)

        layout.addWidget(current_section)

        # Separator
        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setObjectName("separator")
        layout.addWidget(sep1)

        # Available tags section
        available_section = QWidget()
        available_layout = QVBoxLayout(available_section)
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.setSpacing(8)

        available_label = QLabel("可用标签（点击添加）" if zh else "Available Tags (click to add)")
        available_label.setObjectName("sectionLabel")
        available_layout.addWidget(available_label)

        self.available_tags_container = QWidget()
        self.available_tags_layout = QHBoxLayout(self.available_tags_container)
        self.available_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.available_tags_layout.setSpacing(8)
        self.available_tags_layout.addStretch()
        available_layout.addWidget(self.available_tags_container)

        layout.addWidget(available_section)

        # Separator
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setObjectName("separator")
        layout.addWidget(sep2)

        # Create new tag section
        new_tag_section = QWidget()
        new_tag_layout = QVBoxLayout(new_tag_section)
        new_tag_layout.setContentsMargins(0, 0, 0, 0)
        new_tag_layout.setSpacing(12)

        new_tag_label = QLabel("创建新标签" if zh else "Create New Tag")
        new_tag_label.setObjectName("sectionLabel")
        new_tag_layout.addWidget(new_tag_label)

        # Tag name input
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("输入标签名称..." if zh else "Enter tag name...")
        self.new_tag_input.setObjectName("tagInput")
        self.new_tag_input.returnPressed.connect(self._create_tag)
        input_row.addWidget(self.new_tag_input, 1)

        self.btn_create = QPushButton("创建" if zh else "Create")
        self.btn_create.setObjectName("createBtn")
        self.btn_create.clicked.connect(self._create_tag)
        input_row.addWidget(self.btn_create)

        new_tag_layout.addLayout(input_row)

        # Color picker
        color_label = QLabel("选择颜色" if zh else "Select Color")
        color_label.setObjectName("colorLabel")
        new_tag_layout.addWidget(color_label)

        self.color_grid = QWidget()
        color_grid_layout = QGridLayout(self.color_grid)
        color_grid_layout.setContentsMargins(0, 0, 0, 0)
        color_grid_layout.setSpacing(8)

        self.color_buttons: dict[str, ColorButton] = {}
        for i, color_name in enumerate(GROUP_COLOR_NAMES):
            color_hex = GROUP_COLORS[color_name]
            btn = ColorButton(color_name, color_hex)
            btn.clicked.connect(lambda checked, cn=color_name: self._select_color(cn))
            color_grid_layout.addWidget(btn, i // 6, i % 6)
            self.color_buttons[color_name] = btn

        # Select default color
        if 'blue' in self.color_buttons:
            self.color_buttons['blue'].set_selected(True)

        new_tag_layout.addWidget(self.color_grid)

        layout.addWidget(new_tag_section)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消" if zh else "Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("保存" if zh else "Save")
        self.btn_save.setObjectName("saveBtn")
        self.btn_save.clicked.connect(self._save)
        btn_layout.addWidget(self.btn_save)

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

            #sectionLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {t.text_secondary};
            }}

            #colorLabel {{
                font-size: 12px;
                color: {t.text_tertiary};
            }}

            #separator {{
                background-color: {t.border};
            }}

            #tagInput {{
                background-color: {t.bg_tertiary};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: {t.text_primary};
            }}
            #tagInput:focus {{
                border-color: {t.accent};
            }}

            #createBtn {{
                background-color: {t.accent};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                color: white;
            }}
            #createBtn:hover {{
                background-color: {t.accent};
            }}

            #cancelBtn {{
                background-color: transparent;
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                color: {t.text_primary};
            }}
            #cancelBtn:hover {{
                background-color: {t.bg_hover};
            }}

            #saveBtn {{
                background-color: {t.accent};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
                color: white;
            }}
            #saveBtn:hover {{
                background-color: {t.accent};
            }}
        """)

    def _update_display(self):
        """Update the display of current and available tags."""
        # Clear current tags
        while self.current_tags_layout.count() > 1:
            item = self.current_tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add current tags
        for tag_name in self.current_tags:
            group = self._get_group_by_name(tag_name)
            color_hex = group.color_hex if group else GROUP_COLORS.get('gray', '#6B7280')
            chip = TagChip(tag_name, color_hex, removable=True)
            chip.removed.connect(self._remove_tag)
            self.current_tags_layout.insertWidget(self.current_tags_layout.count() - 1, chip)

        # Clear available tags
        while self.available_tags_layout.count() > 1:
            item = self.available_tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add available tags (groups not in current tags)
        for group in self.available_groups:
            if group.name not in self.current_tags:
                chip = self._create_available_chip(group)
                self.available_tags_layout.insertWidget(self.available_tags_layout.count() - 1, chip)

    def _create_available_chip(self, group: Group) -> QPushButton:
        """Create a clickable chip for an available tag."""
        t = get_theme()
        chip = QPushButton()
        chip.setCursor(Qt.CursorShape.PointingHandCursor)

        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(8, 4, 8, 4)
        chip_layout.setSpacing(6)

        # Color indicator
        color_dot = QLabel()
        color_dot.setFixedSize(8, 8)
        color_dot.setStyleSheet(f"""
            background-color: {group.color_hex};
            border-radius: 4px;
        """)
        chip_layout.addWidget(color_dot)

        # Tag name
        name_label = QLabel(group.name)
        name_label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {t.text_primary};")
        chip_layout.addWidget(name_label)

        bg_color = f"{group.color_hex}20"
        chip.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {group.color_hex}40;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {group.color_hex}40;
            }}
        """)

        chip.clicked.connect(lambda: self._add_tag(group.name))
        return chip

    def _get_group_by_name(self, name: str) -> Optional[Group]:
        """Get a group by its name."""
        for group in self.available_groups:
            if group.name == name:
                return group
        return None

    def _select_color(self, color_name: str):
        """Select a color for new tag."""
        self.new_tag_color = color_name
        for name, btn in self.color_buttons.items():
            btn.set_selected(name == color_name)

    def _add_tag(self, tag_name: str):
        """Add a tag to current tags."""
        if tag_name not in self.current_tags:
            self.current_tags.append(tag_name)
            self._update_display()

    def _remove_tag(self, tag_name: str):
        """Remove a tag from current tags."""
        if tag_name in self.current_tags:
            self.current_tags.remove(tag_name)
            self._update_display()

    def _create_tag(self):
        """Create a new tag."""
        tag_name = self.new_tag_input.text().strip()
        if not tag_name:
            return

        # Check if group already exists
        existing = self._get_group_by_name(tag_name)
        if existing:
            # Just add to current tags
            self._add_tag(tag_name)
        else:
            # Create new group and add to available groups
            new_group = Group(name=tag_name, color=self.new_tag_color)
            self.available_groups.append(new_group)
            self._add_tag(tag_name)

        self.new_tag_input.clear()

    def _save(self):
        """Save and close the dialog."""
        self.tags_changed.emit(self.current_tags)
        self.accept()

    def get_tags(self) -> List[str]:
        """Get the current list of tags."""
        return self.current_tags.copy()

    def get_new_groups(self) -> List[Group]:
        """Get any newly created groups."""
        return self.available_groups
