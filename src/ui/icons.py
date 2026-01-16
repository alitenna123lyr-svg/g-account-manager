"""
SVG icon generation functions for crisp rendering at any scale.
"""

from PyQt6.QtCore import Qt, QByteArray, QRectF
from PyQt6.QtGui import QPixmap, QColor, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

from ..config.constants import GROUP_COLORS_PASTEL


def _get_dpr() -> float:
    """Get device pixel ratio for HiDPI support."""
    screen = QApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def _render_svg(svg_data: str, size: int) -> QPixmap:
    """Render SVG data to a high-DPI pixmap."""
    dpr = _get_dpr()
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    real_size = int(size * dpr)
    pixmap = QPixmap(real_size, real_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, real_size, real_size))
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def get_pastel_color(color_hex: str) -> str:
    """Get pastel version of a color from Tailwind palette or calculate dynamically."""
    # Normalize hex to uppercase for lookup
    normalized = color_hex.upper()
    for key, pastel in GROUP_COLORS_PASTEL.items():
        if key.upper() == normalized:
            return pastel

    # Dynamic calculation for custom colors
    base_color = QColor(color_hex)
    if not base_color.isValid():
        return '#e5e7eb'

    # Convert to HSL and create pastel: reduce saturation, increase lightness
    h, s, l, a = base_color.getHslF()
    # Target: saturation ~35%, lightness ~85% (similar to Tailwind 300)
    pastel = QColor.fromHslF(h, min(s * 0.5, 0.4), 0.85, a)
    return pastel.name()


def create_color_icon(color_hex: str, size: int = 16) -> QPixmap:
    """Create a rounded square icon with gray border and soft pastel fill."""
    pastel_fill = get_pastel_color(color_hex)
    border_color = '#9CA3AF'  # Consistent gray, matches other line icons

    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect x="8" y="8" width="84" height="84" rx="16"
              fill="{pastel_fill}" stroke="{border_color}" stroke-width="5"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_dot_icon(color_hex: str, size: int = 10) -> QPixmap:
    """Create a rounded square icon with gray border and soft pastel fill."""
    pastel_fill = get_pastel_color(color_hex)
    border_color = '#9CA3AF'  # Consistent gray border

    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect x="8" y="8" width="84" height="84" rx="16"
              fill="{pastel_fill}" stroke="{border_color}" stroke-width="5"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_tag_icon(color_hex: str, size: int = 16) -> QPixmap:
    """Create a colored tag/label icon."""
    fill_color = QColor(color_hex)
    border_color = fill_color.darker(140).name()

    # Tag shape: rounded rectangle with pointed left side and a small hole
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M15 50 L35 20 L85 20 Q95 20 95 30 L95 70 Q95 80 85 80 L35 80 Z"
              fill="{color_hex}" stroke="{border_color}" stroke-width="4" stroke-linejoin="round"/>
        <circle cx="42" cy="50" r="8" fill="white" opacity="0.9"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_custom_color_icon(size: int = 16) -> QPixmap:
    """Create an icon for custom color option (empty circle with plus sign)."""
    svg_data = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="#9CA3AF" stroke-width="5" stroke-dasharray="12,8"/>
        <line x1="50" y1="30" x2="50" y2="70" stroke="#6B7280" stroke-width="6" stroke-linecap="round"/>
        <line x1="30" y1="50" x2="70" y2="50" stroke="#6B7280" stroke-width="6" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_arrow_icon(direction: str = 'left', size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create an arrow icon for sidebar collapse/expand button."""
    if direction == 'left':
        svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <path d="M65 20 L35 50 L65 80" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
    else:
        svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <path d="M35 20 L65 50 L35 80" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''

    return _render_svg(svg_data, size)


def create_list_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create a list icon (three horizontal lines) for 'All Accounts'."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <line x1="20" y1="30" x2="80" y2="30" stroke="{color}" stroke-width="10" stroke-linecap="round"/>
        <line x1="20" y1="50" x2="80" y2="50" stroke="{color}" stroke-width="10" stroke-linecap="round"/>
        <line x1="20" y1="70" x2="80" y2="70" stroke="{color}" stroke-width="10" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_folder_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create a folder icon for 'Ungrouped'."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M10 30 L10 80 L90 80 L90 35 L50 35 L45 25 L10 25 Z"
              fill="none" stroke="{color}" stroke-width="6" stroke-linejoin="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_trash_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create a trash bin icon for 'Trash'."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect x="25" y="30" width="50" height="55" rx="5" fill="none" stroke="{color}" stroke-width="6"/>
        <line x1="15" y1="30" x2="85" y2="30" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
        <path d="M35 30 L35 20 L65 20 L65 30" fill="none" stroke="{color}" stroke-width="6" stroke-linejoin="round"/>
        <line x1="40" y1="45" x2="40" y2="70" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
        <line x1="50" y1="45" x2="50" y2="70" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
        <line x1="60" y1="45" x2="60" y2="70" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_plus_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create a plus icon for add buttons."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <line x1="50" y1="20" x2="50" y2="80" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
        <line x1="20" y1="50" x2="80" y2="50" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_import_icon(size: int = 16, color: str = '#FFFFFF') -> QPixmap:
    """Create a folder with arrow icon for import."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M10 30 L10 80 L90 80 L90 35 L50 35 L45 25 L10 25 Z"
              fill="none" stroke="{color}" stroke-width="6" stroke-linejoin="round"/>
        <path d="M50 45 L50 70" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
        <path d="M38 57 L50 45 L62 57" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_clear_icon(size: int = 16, color: str = '#FFFFFF') -> QPixmap:
    """Create a broom/clear icon."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M25 75 L40 30 L60 30 L75 75 Z" fill="none" stroke="{color}" stroke-width="6" stroke-linejoin="round"/>
        <line x1="40" y1="30" x2="45" y2="15" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
        <line x1="50" y1="30" x2="50" y2="12" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
        <line x1="60" y1="30" x2="55" y2="15" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
        <line x1="35" y1="50" x2="65" y2="50" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
        <line x1="30" y1="65" x2="70" y2="65" stroke="{color}" stroke-width="5" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_close_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create an X close icon."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <line x1="25" y1="25" x2="75" y2="75" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
        <line x1="75" y1="25" x2="25" y2="75" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_check_icon(size: int = 16, color: str = '#10B981') -> QPixmap:
    """Create a checkmark icon."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M20 55 L40 75 L80 25" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_minus_icon(size: int = 16, color: str = '#FFFFFF') -> QPixmap:
    """Create a minus icon for remove buttons."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <line x1="20" y1="50" x2="80" y2="50" stroke="{color}" stroke-width="12" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_edit_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create an edit/pencil icon."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M75 15 L85 25 L35 75 L20 80 L25 65 Z" fill="none" stroke="{color}" stroke-width="8" stroke-linejoin="round"/>
        <line x1="60" y1="30" x2="70" y2="40" stroke="{color}" stroke-width="8"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_restore_icon(size: int = 16, color: str = '#FFFFFF') -> QPixmap:
    """Create a restore/undo icon (circular arrow)."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M50 20 A30 30 0 1 1 20 50" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"/>
        <path d="M50 20 L35 35 L50 35 Z" fill="{color}"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_lock_icon(locked: bool = True, size: int = 16, color: str = '#8B5CF6') -> QPixmap:
    """Create a lock icon (locked or unlocked)."""
    if locked:
        svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="20" y="45" width="60" height="45" rx="8" fill="none" stroke="{color}" stroke-width="8"/>
            <path d="M30 45 V35 Q30 15 50 15 Q70 15 70 35 V45" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round"/>
            <circle cx="50" cy="67" r="6" fill="{color}"/>
        </svg>'''
    else:
        svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect x="20" y="45" width="60" height="45" rx="8" fill="none" stroke="{color}" stroke-width="8"/>
            <path d="M30 45 V35 Q30 15 50 15 Q70 15 70 35 V30" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round"/>
            <circle cx="50" cy="67" r="6" fill="{color}"/>
        </svg>'''

    return _render_svg(svg_data, size)


def create_edit_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create an edit/pencil icon."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <path d="M75 15 L85 25 L35 75 L20 80 L25 65 Z" fill="none" stroke="{color}" stroke-width="8" stroke-linejoin="round"/>
        <line x1="60" y1="30" x2="70" y2="40" stroke="{color}" stroke-width="8"/>
    </svg>'''

    return _render_svg(svg_data, size)


def create_clock_icon(size: int = 16, color: str = '#6B7280') -> QPixmap:
    """Create a clock icon for countdown timer."""
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="8"/>
        <line x1="50" y1="50" x2="50" y2="28" stroke="{color}" stroke-width="8" stroke-linecap="round"/>
        <line x1="50" y1="50" x2="68" y2="50" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
    </svg>'''

    return _render_svg(svg_data, size)
