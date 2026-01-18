"""
Constants used throughout the application.
"""

from typing import Final

# Available colors for groups - Light mode (Tailwind 600 - deeper, more mature)
GROUP_COLORS: Final[dict[str, str]] = {
    'red': '#DC2626',
    'orange': '#EA580C',
    'amber': '#D97706',
    'yellow': '#CA8A04',
    'lime': '#65A30D',
    'green': '#16A34A',
    'teal': '#0D9488',
    'cyan': '#0891B2',
    'blue': '#2563EB',
    'indigo': '#4F46E5',
    'purple': '#9333EA',
    'pink': '#DB2777',
}

# Dark mode colors (Tailwind 400 - brighter for dark backgrounds)
GROUP_COLORS_DARK: Final[dict[str, str]] = {
    'red': '#F87171',
    'orange': '#FB923C',
    'amber': '#FBBF24',
    'yellow': '#FACC15',
    'lime': '#A3E635',
    'green': '#4ADE80',
    'teal': '#2DD4BF',
    'cyan': '#22D3EE',
    'blue': '#60A5FA',
    'indigo': '#818CF8',
    'purple': '#C084FC',
    'pink': '#F472B6',
}

# Pastel fill colors for icons (Tailwind 200 level - soft but visible)
# Maps from 600-level colors to 200-level pastels
GROUP_COLORS_PASTEL: Final[dict[str, str]] = {
    '#DC2626': '#FECACA',  # red
    '#EA580C': '#FED7AA',  # orange
    '#D97706': '#FDE68A',  # amber
    '#CA8A04': '#FEF08A',  # yellow
    '#65A30D': '#D9F99D',  # lime
    '#16A34A': '#BBF7D0',  # green
    '#0D9488': '#99F6E4',  # teal
    '#0891B2': '#A5F3FC',  # cyan
    '#2563EB': '#BFDBFE',  # blue
    '#4F46E5': '#C7D2FE',  # indigo
    '#9333EA': '#E9D5FF',  # purple
    '#DB2777': '#FBCFE8',  # pink
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
