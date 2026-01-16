"""
Constants used throughout the application.
"""

from typing import Final

# Available color icons for custom groups (12 distinct colors)
GROUP_COLORS: Final[dict[str, str]] = {
    'red': '#EF4444',
    'orange': '#F97316',
    'yellow': '#EAB308',
    'lime': '#84CC16',
    'green': '#22C55E',
    'teal': '#14B8A6',
    'cyan': '#06B6D4',
    'blue': '#3B82F6',
    'indigo': '#6366F1',
    'purple': '#8B5CF6',
    'pink': '#EC4899',
    'gray': '#6B7280',
}

# Pastel fill colors for icons (Tailwind 300 level - soft but visible)
GROUP_COLORS_PASTEL: Final[dict[str, str]] = {
    '#EF4444': '#fca5a5',  # red
    '#F97316': '#fdba74',  # orange
    '#EAB308': '#fde047',  # yellow
    '#84CC16': '#bef264',  # lime
    '#22C55E': '#86efac',  # green
    '#14B8A6': '#5eead4',  # teal
    '#06B6D4': '#67e8f9',  # cyan
    '#3B82F6': '#93c5fd',  # blue
    '#6366F1': '#a5b4fc',  # indigo
    '#8B5CF6': '#c4b5fd',  # purple
    '#EC4899': '#f9a8d4',  # pink
    '#6B7280': '#d1d5db',  # gray
}

GROUP_COLOR_NAMES: Final[list[str]] = list(GROUP_COLORS.keys())

# Emoji to color name mapping for migration
EMOJI_TO_COLOR_NAME: Final[dict[str, str]] = {
    '\U0001F534': 'red',      # 🔴
    '\U0001F7E0': 'orange',   # 🟠
    '\U0001F7E1': 'yellow',   # 🟡
    '\U0001F7E2': 'green',    # 🟢
    '\U0001F535': 'blue',     # 🔵
    '\U0001F7E3': 'purple',   # 🟣
    '\U000026AB': 'gray',     # ⚫
    '\U0001F7E4': 'brown',    # 🟤
}

# TOTP settings
TOTP_PERIOD: Final[int] = 30  # seconds
TOTP_DIGITS: Final[int] = 6

# UI settings
TOAST_DURATION: Final[int] = 2000  # milliseconds
MAX_BACKUPS: Final[int] = 10

# Table column indices
class TableColumns:
    CHECKBOX = 0
    ID = 1
    EMAIL = 2
    PASSWORD = 3
    BACKUP_EMAIL = 4
    SECRET = 5
    CODE = 6
    IMPORT_TIME = 7
    GROUPS = 8
    NOTES = 9


def get_color_hex(color_value: str) -> str:
    """Get hex color code - supports both preset names and custom hex colors."""
    if color_value.startswith('#'):
        return color_value
    return GROUP_COLORS.get(color_value, '#808080')
