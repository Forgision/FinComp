import logging
import os
import re
import sys
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from fastapi_app.core.config import settings

try:
    from colorama import Fore, Back, Style, init
    # Initialize colorama for Windows compatibility
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Sensitive patterns to filter out
SENSITIVE_PATTERNS = [
    (r'(api[_-]?key[\s]*[=:]\s*)[\w\-]+', r'\1[REDACTED]'),
    (r'(password[\s]*[=:]\s*)[\w\-]+', r'\1[REDACTED]'),
    (r'(token[\s]*[=:]\s*)[\w\-]+', r'\1[REDACTED]'),
    (r'(secret[\s]*[=:]\s*)[\w\-]+', r'\1[REDACTED]'),
    (r'(authorization[\s]*[=:]\s*)[\w\-]+', r'\1[REDACTED]'),
    (r'(Bearer\s+)[\w\-\.]+', r'\1[REDACTED]'),
]

# Color mappings for different log levels
if COLORAMA_AVAILABLE:
    LOG_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    COMPONENT_COLORS = {
        'timestamp': Fore.BLUE,
        'module': Fore.MAGENTA,
        'reset': Style.RESET_ALL,
    }
else:
    LOG_COLORS = {}
    COMPONENT_COLORS = {}


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from log messages."""
    def filter(self, record):
        try:
            record.msg = str(record.msg)
            for pattern, replacement in SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)

            if record.args:
                record.args = tuple(re.sub(pattern, replacement, str(arg), flags=re.IGNORECASE)
                                    for arg in record.args for pattern, replacement in SENSITIVE_PATTERNS)
        except Exception:
            pass
        return True


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels and components."""
    def __init__(self, fmt=None, datefmt=None, enable_colors=True):
        super().__init__(fmt, datefmt)
        self.enable_colors = enable_colors and COLORAMA_AVAILABLE and self._supports_color()

    def _supports_color(self):
        if os.environ.get('NO_COLOR'):
            return False
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            return True
        return False

    def format(self, record):
        if not self.enable_colors:
            return super().format(record)

        original_format = super().format(record)

        level_color = LOG_COLORS.get(record.levelname, '')
        reset = COMPONENT_COLORS.get('reset', '')
        timestamp_color = COMPONENT_COLORS.get('timestamp', '')
        module_color = COMPONENT_COLORS.get('module', '')

        if '[' in original_format and ']' in original_format:
            original_format = re.sub(r'(\[.*?\])', f'{timestamp_color}\\1{reset}', original_format)

        if record.levelname in original_format:
            original_format = original_format.replace(record.levelname, f'{level_color}{record.levelname}{reset}')

        if hasattr(record, 'module') and record.module in original_format:
            original_format = original_format.replace(f' in {record.module}:', f' in {module_color}{record.module}{reset}:')

        return original_format


def cleanup_old_logs(log_dir: Path, retention_days: int):
    """Remove log files older than retention_days."""
    if not log_dir.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=retention_days)

    for log_file in log_dir.glob("*.log*"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                log_file.unlink()
        except Exception:
            pass


def setup_logging():
    """Initialize the logging configuration from the settings object."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    root_logger.handlers = []

    console_formatter = ColoredFormatter(settings.LOG_FORMAT)
    file_formatter = logging.Formatter(settings.LOG_FORMAT)

    sensitive_filter = SensitiveDataFilter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(sensitive_filter)
    root_logger.addHandler(console_handler)

    if settings.LOG_TO_FILE:
        log_path = Path(settings.LOG_DIR)
        log_path.mkdir(exist_ok=True)

        cleanup_old_logs(log_path, settings.LOG_RETENTION)

        log_file = log_path / f"fastapi_openalgo_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=settings.LOG_RETENTION,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('starlette').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)

# Initialize logging on import
setup_logging()
