#!/usr/bin/env python3
"""
G-Account Manager - Application Entry Point

Usage:
    python main.py        # Run the application
    python main.py --help # Show help
"""

import sys
import argparse
import logging

# Add src to path for imports
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

from src.utils.logger import setup_logging, get_logger


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="G-Account Manager - Google Account & 2FA Code Manager"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log to file instead of console"
    )
    return parser.parse_args()


def main():
    """Application entry point."""
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    logger = get_logger(__name__)
    logger.info("Starting G-Account Manager v2.0.0")

    # Import PyQt6 and run application
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont, QFontDatabase

        logger.info("Loading application...")

        from src.ui.main_window import MainWindowV2 as MainWindow

        app = QApplication(sys.argv)
        app.setStyle('Fusion')

        # Set elegant global font with CJK support
        # Priority: Microsoft YaHei UI (best for Windows Chinese UI)
        available_fonts = QFontDatabase.families()

        # Font priority for Chinese + English mixed content
        font_priorities = [
            "Microsoft YaHei UI",   # Windows 10+ optimized for UI
            "Microsoft YaHei",      # Windows Vista+
            "PingFang SC",          # macOS Chinese
            "Segoe UI",             # Windows fallback
            "Noto Sans CJK SC",     # Cross-platform Chinese
            "Source Han Sans CN",   # Adobe Chinese
        ]

        selected_font = "Microsoft YaHei"  # Default
        for font in font_priorities:
            if font in available_fonts:
                selected_font = font
                break

        app_font = QFont(selected_font)
        app_font.setPointSize(10)
        app_font.setWeight(QFont.Weight.Normal)
        app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(app_font)

        logger.info(f"Using font: {selected_font}")

        window = MainWindow()
        window.show()

        logger.info("Application started successfully")
        sys.exit(app.exec())

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Please ensure PyQt6 is installed: pip install PyQt6")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
