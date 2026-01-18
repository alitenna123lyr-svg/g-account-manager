"""
Unified minimal line icon system.
All icons use consistent 1.5px stroke, same style.
"""

from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QByteArray, QRectF
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication


def _render_svg(svg_content: str, size: int, color: str = "#6B7280") -> QPixmap:
    """Render SVG content to a QPixmap with the specified color."""
    # Replace color placeholder
    svg_data = svg_content.replace("{color}", color)

    # Get device pixel ratio for HiDPI
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0

    # Create high-DPI pixmap
    real_size = int(size * dpr)
    pixmap = QPixmap(real_size, real_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(dpr)

    # Render SVG - use logical size since QPainter uses logical coordinates with dpr
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    return pixmap


# ============== Navigation Icons ==============

def icon_menu(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Hamburger menu icon (3 horizontal lines)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 6h16M4 12h16M4 18h16" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_collapse(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Collapse sidebar icon (left arrows)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M11 17l-5-5 5-5M18 17l-5-5 5-5" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_expand(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Expand sidebar icon (right arrows)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M13 7l5 5-5 5M6 7l5 5-5 5" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_chevron_down(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Chevron down icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 9l6 6 6-6" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_chevron_right(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Chevron right icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M9 6l6 6-6 6" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_arrow_up(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Arrow up icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 19V5M5 12l7-7 7 7" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_arrow_down(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Arrow down icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 5v14M5 12l7 7 7-7" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


# ============== Action Icons ==============

def icon_plus(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Plus/Add icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 5v14M5 12h14" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_search(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Search/magnifying glass icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="11" cy="11" r="6" stroke="{color}" stroke-width="1.5"/>
        <path d="M20 20l-4-4" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_edit(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Edit/pencil icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15.5 5.5l3 3M4 20h3l11-11-3-3L4 17v3z" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_trash(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Trash/delete icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 002 2h8a2 2 0 002-2l1-12M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_copy(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Copy icon - two overlapping rectangles."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="8" width="12" height="12" rx="2" stroke="{color}" stroke-width="1.5"/>
        <path d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_check(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Checkmark icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 12l5 5L20 7" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_close(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Close/X icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 6l12 12M6 18L18 6" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


# ============== UI Icons ==============

def icon_sun(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Sun icon (light mode)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="4" stroke="{color}" stroke-width="1.5"/>
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_moon(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Moon icon (dark mode)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_globe(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Globe icon (language)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="9" stroke="{color}" stroke-width="1.5"/>
        <path d="M3 12h18M12 3c2.5 2.5 4 5.5 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.5-4-9s1.5-6.5 4-9z" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_settings(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Settings/gear icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="3" stroke="{color}" stroke-width="1.5"/>
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


# ============== Content Icons ==============

def icon_folder(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Folder icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_folder_open(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Open folder icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H5v9z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_file(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """File/document icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M14 2v6h6" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_library(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Library/book icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 19.5A2.5 2.5 0 016.5 17H20M4 4.5A2.5 2.5 0 016.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15z" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_user(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """User/account icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="8" r="4" stroke="{color}" stroke-width="1.5"/>
        <path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_key(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Key/password icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="15" r="4" stroke="{color}" stroke-width="1.5"/>
        <path d="M11 12l9-9M17 6l3-3M14 9l3-3" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_shield(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Shield/2FA icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 3l8 4v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V7l8-4z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_mail(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Mail/email icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="5" width="18" height="14" rx="2" stroke="{color}" stroke-width="1.5"/>
        <path d="M3 7l9 6 9-6" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_eye(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Eye/show icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" stroke="{color}" stroke-width="1.5"/>
        <circle cx="12" cy="12" r="3" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_eye_off(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Eye off/hide icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M17.94 17.94A10.07 10.07 0 0112 19c-7 0-10-7-10-7a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 10 7 10 7a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M3 3l18 18" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_clock(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Clock/time icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="9" stroke="{color}" stroke-width="1.5"/>
        <path d="M12 6v6l4 2" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_import(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Import/download icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 3v12M12 15l-4-4M12 15l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_export(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Export/upload icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 15V3M12 3l-4 4M12 3l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_drag(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Drag handle icon (6 dots)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="9" cy="6" r="1.5" fill="{color}"/>
        <circle cx="15" cy="6" r="1.5" fill="{color}"/>
        <circle cx="9" cy="12" r="1.5" fill="{color}"/>
        <circle cx="15" cy="12" r="1.5" fill="{color}"/>
        <circle cx="9" cy="18" r="1.5" fill="{color}"/>
        <circle cx="15" cy="18" r="1.5" fill="{color}"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_more(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """More options icon (3 dots vertical)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="6" r="1.5" fill="{color}"/>
        <circle cx="12" cy="12" r="1.5" fill="{color}"/>
        <circle cx="12" cy="18" r="1.5" fill="{color}"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_more_horizontal(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """More options icon (3 dots horizontal)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="12" r="1.5" fill="{color}"/>
        <circle cx="12" cy="12" r="1.5" fill="{color}"/>
        <circle cx="18" cy="12" r="1.5" fill="{color}"/>
    </svg>'''
    return _render_svg(svg, size, color)


# ============== Category/Group Icons ==============

def icon_all(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """All items icon (grid)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="{color}" stroke-width="1.5"/>
        <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="{color}" stroke-width="1.5"/>
        <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="{color}" stroke-width="1.5"/>
        <rect x="14" y="14" width="7" height="7" rx="1.5" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_google(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Google G icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 11v2.4h3.97c-.16 1.03-1.2 3.02-3.97 3.02-2.39 0-4.34-1.98-4.34-4.42S9.61 7.58 12 7.58c1.36 0 2.27.58 2.79 1.08l1.9-1.83C15.47 5.69 13.89 5 12 5c-3.87 0-7 3.13-7 7s3.13 7 7 7c4.04 0 6.72-2.84 6.72-6.84 0-.46-.05-.81-.11-1.16H12z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_social(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Social/chat icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_work(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Work/briefcase icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="7" width="18" height="12" rx="2" stroke="{color}" stroke-width="1.5"/>
        <path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_star(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Star/favorite icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_archive(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Archive icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 5a2 2 0 012-2h14a2 2 0 012 2v2H3V5zM3 9h18v10a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" stroke="{color}" stroke-width="1.5"/>
        <path d="M10 13h4" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_refresh(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Refresh icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 12a9 9 0 019-9 9.75 9.75 0 016.74 2.74L21 8M21 12a9 9 0 01-9 9 9.75 9.75 0 01-6.74-2.74L3 16" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M21 3v5h-5M3 21v-5h5" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_briefcase(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Briefcase/work icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="7" width="20" height="13" rx="2" stroke="{color}" stroke-width="1.5"/>
        <path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" stroke="{color}" stroke-width="1.5"/>
        <path d="M2 12h20" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_users(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Users/people icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="9" cy="7" r="3" stroke="{color}" stroke-width="1.5"/>
        <path d="M3 19c0-3 2.5-5 6-5s6 2 6 5" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="17" cy="8" r="2.5" stroke="{color}" stroke-width="1.5"/>
        <path d="M17 13c2.5 0 4.5 1.5 4.5 4" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_square_plus(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Square with plus icon (add to group)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="3" stroke="{color}" stroke-width="1.5"/>
        <path d="M12 8v8M8 12h8" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_square_minus(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Square with minus icon (remove from group)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="3" stroke="{color}" stroke-width="1.5"/>
        <path d="M8 12h8" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_folder_plus(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Folder with plus icon (add to group)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M12 10v6M9 13h6" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_folder_minus(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Folder with minus icon (remove from group)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M9 13h6" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_library_move(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Move to library icon - open bracket with arrow."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M9 4H6a2 2 0 00-2 2v12a2 2 0 002 2h3" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 12h9M21 12l-4-4M21 12l-4 4" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_wallet(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Wallet/finance icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="5" width="20" height="14" rx="2" stroke="{color}" stroke-width="1.5"/>
        <path d="M2 10h20" stroke="{color}" stroke-width="1.5"/>
        <circle cx="17" cy="14" r="1.5" fill="{color}"/>
    </svg>'''
    return _render_svg(svg, size, color)


# ============== Colored Circle Icons (for groups) ==============

def icon_circle(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Simple filled circle icon."""
    svg = f'''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="6" fill="{color}"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_circle_outline(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Circle outline icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="6" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_checkbox(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Checkbox with check mark (selected state)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="{color}" stroke-width="1.5"/>
        <path d="M9 12l2 2 4-4" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_checkbox_empty(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Empty checkbox (unselected state)."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_list(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """List view icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return _render_svg(svg, size, color)


def icon_grid(size: int = 20, color: str = "#6B7280") -> QPixmap:
    """Grid/card view icon."""
    svg = '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="7" height="7" rx="1" stroke="{color}" stroke-width="1.5"/>
        <rect x="14" y="3" width="7" height="7" rx="1" stroke="{color}" stroke-width="1.5"/>
        <rect x="3" y="14" width="7" height="7" rx="1" stroke="{color}" stroke-width="1.5"/>
        <rect x="14" y="14" width="7" height="7" rx="1" stroke="{color}" stroke-width="1.5"/>
    </svg>'''
    return _render_svg(svg, size, color)


# Predefined group colors
GROUP_COLORS = {
    'gray': '#6B7280',
    'red': '#EF4444',
    'orange': '#F97316',
    'amber': '#F59E0B',
    'yellow': '#EAB308',
    'lime': '#84CC16',
    'green': '#22C55E',
    'emerald': '#10B981',
    'teal': '#14B8A6',
    'cyan': '#06B6D4',
    'sky': '#0EA5E9',
    'blue': '#3B82F6',
    'indigo': '#6366F1',
    'violet': '#8B5CF6',
    'purple': '#A855F7',
    'fuchsia': '#D946EF',
    'pink': '#EC4899',
    'rose': '#F43F5E',
}
