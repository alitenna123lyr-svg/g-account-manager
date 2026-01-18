"""
Theme system for the application.
Supports light and dark themes with consistent color variables.
"""

from dataclasses import dataclass
from typing import Dict
from enum import Enum


class ThemeMode(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Theme:
    """Theme color definitions."""
    # Backgrounds
    bg_primary: str       # Main background
    bg_secondary: str     # Secondary background (sidebar)
    bg_tertiary: str      # Tertiary background (cards, inputs)
    bg_hover: str         # Hover state
    bg_selected: str      # Selected state
    bg_accent: str        # Accent background

    # Text
    text_primary: str     # Primary text
    text_secondary: str   # Secondary text
    text_tertiary: str    # Tertiary/muted text
    text_inverse: str     # Inverse text (on accent bg)

    # Borders
    border: str           # Default border
    border_light: str     # Light border
    border_focus: str     # Focus state border

    # Accent colors
    accent: str           # Primary accent
    accent_hover: str     # Accent hover
    accent_light: str     # Light accent (for backgrounds)

    # Semantic colors
    success: str          # Success/green
    warning: str          # Warning/orange
    error: str            # Error/red
    info: str             # Info/blue

    # Special
    shadow: str           # Shadow color (with alpha)
    overlay: str          # Overlay color (with alpha)

    # iOS Frosted Glass
    glass_bg: str         # Frosted glass background
    glass_bg_hover: str   # Frosted glass hover
    glass_bg_pressed: str # Frosted glass pressed
    glass_border: str     # Frosted glass border
    glass_primary_bg: str       # Primary action glass background
    glass_primary_bg_hover: str # Primary action glass hover
    glass_primary_text: str     # Primary action text color (iOS blue)


# Light Theme
LIGHT_THEME = Theme(
    # Backgrounds
    bg_primary="#FFFFFF",
    bg_secondary="#F9FAFB",
    bg_tertiary="#F3F4F6",
    bg_hover="#F3F4F6",
    bg_selected="#EEF2FF",
    bg_accent="#6366F1",

    # Text
    text_primary="#1F2937",
    text_secondary="#6B7280",
    text_tertiary="#9CA3AF",
    text_inverse="#FFFFFF",

    # Borders
    border="#E5E7EB",
    border_light="#F3F4F6",
    border_focus="#6366F1",

    # Accent
    accent="#6366F1",
    accent_hover="#4F46E5",
    accent_light="#EEF2FF",

    # Semantic
    success="#10B981",
    warning="#F59E0B",
    error="#EF4444",
    info="#3B82F6",

    # Special
    shadow="rgba(0, 0, 0, 0.08)",
    overlay="rgba(0, 0, 0, 0.5)",

    # iOS Frosted Glass (Light mode)
    glass_bg="rgba(120, 120, 128, 0.12)",
    glass_bg_hover="rgba(120, 120, 128, 0.18)",
    glass_bg_pressed="rgba(120, 120, 128, 0.24)",
    glass_border="rgba(0, 0, 0, 0.04)",
    # iOS Primary Glass (for primary actions - light mode)
    glass_primary_bg="rgba(0, 122, 255, 0.12)",
    glass_primary_bg_hover="rgba(0, 122, 255, 0.18)",
    glass_primary_text="#007AFF",
)


# Dark Theme
DARK_THEME = Theme(
    # Backgrounds
    bg_primary="#111827",
    bg_secondary="#1F2937",
    bg_tertiary="#374151",
    bg_hover="#374151",
    bg_selected="#312E81",
    bg_accent="#6366F1",

    # Text
    text_primary="#F9FAFB",
    text_secondary="#D1D5DB",
    text_tertiary="#9CA3AF",
    text_inverse="#FFFFFF",

    # Borders
    border="#4B5563",
    border_light="#6B7280",
    border_focus="#818CF8",

    # Accent
    accent="#818CF8",
    accent_hover="#6366F1",
    accent_light="#312E81",

    # Semantic
    success="#34D399",
    warning="#FBBF24",
    error="#F87171",
    info="#60A5FA",

    # Special
    shadow="rgba(0, 0, 0, 0.3)",
    overlay="rgba(0, 0, 0, 0.7)",

    # iOS Frosted Glass (Dark mode)
    glass_bg="rgba(118, 118, 128, 0.24)",
    glass_bg_hover="rgba(118, 118, 128, 0.32)",
    glass_bg_pressed="rgba(118, 118, 128, 0.40)",
    glass_border="rgba(255, 255, 255, 0.08)",
    # iOS Primary Glass (for primary actions - dark mode)
    glass_primary_bg="rgba(10, 132, 255, 0.24)",
    glass_primary_bg_hover="rgba(10, 132, 255, 0.32)",
    glass_primary_text="#0A84FF",
)


class ThemeManager:
    """Manages the application theme."""

    _instance = None
    _theme_mode: ThemeMode = ThemeMode.LIGHT
    _theme: Theme = LIGHT_THEME
    _listeners: list = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = []
        return cls._instance

    @property
    def mode(self) -> ThemeMode:
        return self._theme_mode

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def is_dark(self) -> bool:
        return self._theme_mode == ThemeMode.DARK

    def set_theme(self, mode: ThemeMode) -> None:
        """Set the theme mode."""
        self._theme_mode = mode
        self._theme = DARK_THEME if mode == ThemeMode.DARK else LIGHT_THEME
        self._notify_listeners()

    def toggle_theme(self) -> None:
        """Toggle between light and dark theme."""
        new_mode = ThemeMode.LIGHT if self._theme_mode == ThemeMode.DARK else ThemeMode.DARK
        self.set_theme(new_mode)

    def add_listener(self, callback) -> None:
        """Add a theme change listener."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback) -> None:
        """Remove a theme change listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all listeners of theme change."""
        for callback in self._listeners:
            try:
                callback(self._theme)
            except Exception:
                pass

    def get_stylesheet(self) -> str:
        """Generate the global stylesheet for the current theme."""
        t = self._theme
        return f"""
            /* Global */
            QWidget {{
                background-color: {t.bg_primary};
                color: {t.text_primary};
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            }}

            /* Main Window */
            QMainWindow {{
                background-color: {t.bg_primary};
            }}

            /* Labels */
            QLabel {{
                background: transparent;
                color: {t.text_primary};
            }}

            /* Buttons - iOS Frosted Glass style */
            QPushButton {{
                background-color: {t.glass_bg};
                color: {t.text_primary};
                border: 1px solid {t.glass_border};
                border-radius: 10px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {t.glass_bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {t.glass_bg_pressed};
            }}

            /* Line Edit / Search */
            QLineEdit {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 8px;
                padding: 8px 12px;
                selection-background-color: {t.accent};
            }}
            QLineEdit:focus {{
                border-color: {t.border_focus};
                background-color: {t.bg_primary};
            }}
            QLineEdit::placeholder {{
                color: {t.text_tertiary};
            }}

            /* Scroll Area */
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}

            /* Scrollbars */
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

            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {t.text_tertiary};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t.text_secondary};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}

            /* Splitter */
            QSplitter {{
                background: {t.bg_primary};
            }}
            QSplitter::handle {{
                background: {t.border};
            }}
            QSplitter::handle:horizontal {{
                width: 1px;
            }}
            QSplitter::handle:vertical {{
                height: 1px;
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
            }}
            QMenu::item:selected {{
                background-color: {t.bg_hover};
            }}
            QMenu::separator {{
                height: 1px;
                background: {t.border};
                margin: 4px 8px;
            }}

            /* ToolTip */
            QToolTip {{
                background-color: {t.bg_tertiary};
                color: {t.text_primary};
                border: 1px solid {t.border};
                border-radius: 4px;
                padding: 4px 8px;
            }}

            /* Frame */
            QFrame {{
                background-color: transparent;
            }}
        """


# Global theme manager instance
def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return ThemeManager()


def get_theme() -> Theme:
    """Get the current theme."""
    return get_theme_manager().theme


def get_glass_button_style(
    accent_color: str = None,
    text_color: str = None,
    border_radius: int = 10,
    padding: str = "8px 16px"
) -> str:
    """
    Generate iOS-style frosted glass button stylesheet.

    Args:
        accent_color: Optional accent color for tinted glass effect (e.g., "#6366F1")
        text_color: Text color (defaults to theme text color or white for accent buttons)
        border_radius: Border radius in pixels
        padding: CSS padding value

    Returns:
        Complete stylesheet string for QPushButton
    """
    tm = get_theme_manager()
    t = tm.theme

    if accent_color:
        # Tinted glass effect with accent color
        # Convert hex to rgba with transparency
        r = int(accent_color[1:3], 16)
        g = int(accent_color[3:5], 16)
        b = int(accent_color[5:7], 16)

        bg = f"rgba({r}, {g}, {b}, 0.75)"
        bg_hover = f"rgba({r}, {g}, {b}, 0.85)"
        bg_pressed = f"rgba({r}, {g}, {b}, 0.95)"
        border = f"rgba({min(r+30, 255)}, {min(g+30, 255)}, {min(b+30, 255)}, 0.5)"
        text = text_color or "#FFFFFF"
    else:
        # Default glass effect from theme
        bg = t.glass_bg
        bg_hover = t.glass_bg_hover
        bg_pressed = t.glass_bg_pressed
        border = t.glass_border
        text = text_color or t.text_primary

    return f"""
        QPushButton {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            border-radius: {border_radius}px;
            padding: {padding};
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
        }}
        QPushButton:pressed {{
            background-color: {bg_pressed};
        }}
    """


def get_glass_toolbutton_style(accent_color: str = None) -> str:
    """Generate iOS-style frosted glass QToolButton stylesheet."""
    tm = get_theme_manager()
    t = tm.theme

    if accent_color:
        r = int(accent_color[1:3], 16)
        g = int(accent_color[3:5], 16)
        b = int(accent_color[5:7], 16)
        bg_hover = f"rgba({r}, {g}, {b}, 0.2)"
    else:
        bg_hover = t.glass_bg

    return f"""
        QToolButton {{
            background: transparent;
            border: none;
            border-radius: 8px;
        }}
        QToolButton:hover {{
            background-color: {bg_hover};
        }}
    """


def get_glass_menu_style() -> str:
    """Generate iOS-style frosted glass QMenu stylesheet."""
    t = get_theme_manager().theme
    return f"""
        QMenu {{
            background: {t.glass_bg};
            border: 1px solid {t.glass_border};
            border-radius: 12px;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 10px 18px;
            border-radius: 8px;
            color: {t.text_primary};
        }}
        QMenu::item:selected {{
            background: {t.glass_bg_hover};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t.border};
            margin: 4px 8px;
        }}
    """
