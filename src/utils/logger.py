"""
Logging configuration for the application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> None:
    """
    Configure application logging.

    Args:
        log_file: Optional path to log file. If None, logs only to console.
        level: Logging level (default: INFO).
        format_string: Custom format string. If None, uses default format.
    """
    if format_string is None:
        format_string = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout)
    ]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.FileHandler(log_file, encoding='utf-8')
        )

    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Set specific loggers to WARNING to reduce noise
    logging.getLogger('PyQt6').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
