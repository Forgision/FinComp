"""
Universal logger for the FinAlgo platform.

This module provides a centralized logging system for the entire platform,
with a consistent format and the ability to track module.class.method locations.

Format: datetime - module.class.method - line number - level - message
"""

import inspect
import logging
import os
import sys
import re
from functools import cache
from pathlib import Path
from datetime import timedelta
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, MutableMapping, Optional, Tuple
from ..core.config import settings

try:
    from colorama import Fore as ColoramaFore, Back as ColoramaBack, Style as ColoramaStyle, init as colorama_init  # type: ignore #(Library stubs not installed for "colorama")
    colorama_init(autoreset=True)
    Fore = ColoramaFore
    Back = ColoramaBack
    Style = ColoramaStyle
    COLORAMA_AVAILABLE = True
    LOG_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    # Additional colors for components
    COMPONENT_COLORS = {
        'timestamp': Fore.BLUE,
        'module': Fore.MAGENTA,
        'reset': Style.RESET_ALL,
    }
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


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from log messages."""
    
    def filter(self, record):
        try:
            # Filter the main message
            for pattern, replacement in SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, str(record.msg), flags=re.IGNORECASE)
            
            # Filter args if present
            if hasattr(record, 'args') and record.args:
                filtered_args = []
                for arg in record.args:
                    filtered_arg = str(arg)
                    for pattern, replacement in SENSITIVE_PATTERNS:
                        filtered_arg = re.sub(pattern, replacement, filtered_arg, flags=re.IGNORECASE)
                    filtered_args.append(filtered_arg)
                record.args = tuple(filtered_args)
        except Exception:
            # If filtering fails, don't block the log message
            pass
            
        return True


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels and components for console output."""
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.enable_colors = settings.LOGS_COLORS_ENABLE and COLORAMA_AVAILABLE and self._supports_color()
    
    def _supports_color(self):
        """Check if the terminal supports color output."""
        # Check if we're in a terminal that supports colors
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Check environment variables
            term = os.environ.get('TERM', '')
            if 'color' in term.lower() or term in ['xterm', 'xterm-256color', 'screen', 'screen-256color']:
                return True
                
            # Check for common CI environments that support colors
            ci_envs = ['GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL', 'BUILDKITE']
            if any(env in os.environ for env in ci_envs):
                return True
        
        # For Windows Command Prompt or PowerShell, check if ANSI support is available
        if os.name == 'nt':
            try:
                # Try to enable ANSI escape sequences on Windows
                import subprocess
                result = subprocess.run(['reg', 'query', 'HKCU\\Console', '/v', 'VirtualTerminalLevel'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and 'VirtualTerminalLevel' in result.stdout:
                    return True
            except:
                pass
            
            # Check if running in Windows Terminal, VS Code, or similar
            wt_session = os.environ.get('WT_SESSION')
            vscode_term = os.environ.get('VSCODE_INJECTION')
            if wt_session or vscode_term:
                return True
                
        return False
    
    def format(self, record):
        if not self.enable_colors:
            return super().format(record)

        # Get the original formatted message
        # Wrap in try-except to handle format string mismatches from external libraries
        try:
            original_format = super().format(record)
        except (TypeError, ValueError) as e:
            # Handle cases where external libraries (like hpack) pass wrong types
            # Example: hpack passes strings like '2' to %d format specifier
            # Fallback to basic formatting without the problematic args
            try:
                record.message = str(record.msg)  # Convert message to string
                record.args = None  # Clear args to avoid format issues
                original_format = super().format(record)
            except Exception:
                # Last resort: return raw message
                return f"[{record.levelname}] {record.msg}"
        
        # Apply colors to different components
        level_color = LOG_COLORS.get(record.levelname, '')
        reset = COMPONENT_COLORS.get('reset', '')
        timestamp_color = COMPONENT_COLORS.get('timestamp', '')
        module_color = COMPONENT_COLORS.get('module', '')
        
        # Parse the format to identify components
        # This assumes the default format: [timestamp] LEVEL in module: message
        if '[' in original_format and ']' in original_format:
            # Color the timestamp
            original_format = re.sub(
                r'(\[.*?\])', 
                f'{timestamp_color}\\1{reset}', 
                original_format
            )
        
        # Color the log level
        if record.levelname in original_format:
            original_format = original_format.replace(
                record.levelname,
                f'{level_color}{record.levelname}{reset}'
            )
        
        # Color the module name
        if hasattr(record, 'module') and record.module in original_format:
            original_format = original_format.replace(
                f' in {record.module}:',
                f' in {module_color}{record.module}{reset}:'
            )
        
        return original_format


def cleanup_old_logs(log_dir: Path, retention_days: int):
    """Remove log files older than retention_days."""
    if not log_dir.exists():
        return
        
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    for log_file in log_dir.glob("*.log*"):
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                log_file.unlink()
        except Exception:
            # Skip files that can't be processed
            pass


class LocationAdapter(logging.LoggerAdapter):
    """
    Adapter to add detailed location information (file, line, method) to log records.
    """

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> Tuple[str, MutableMapping[str, Any]]:
        """
        Process the log record to add location details.

        This method expects 'location' in kwargs to be either a dictionary
        containing detailed location info or a string for backward compatibility.
        """
        location_details = kwargs.pop("location", None)
        extra = kwargs.get("extra", {})

        if isinstance(location_details, dict):
            # Caller provided detailed location info
            extra["location"] = location_details.get("location_str", "unknown")
            extra["pathname"] = location_details.get("file_path", "unknown")
            extra["lineno"] = location_details.get("line_number", 0)
        elif location_details:
            # Backward compatibility for string-based location
            extra["location"] = self._to_string(location_details)
            extra.setdefault("pathname", "unknown")
            extra.setdefault("lineno", 0)
        else:
            # Ensure keys exist for the formatter even if no location is provided
            extra.setdefault("location", "unknown")
            extra.setdefault("pathname", "unknown")
            extra.setdefault("lineno", 0)

        kwargs["extra"] = extra
        return msg, kwargs

    @staticmethod
    @cache
    def _to_string(location: Any) -> str:
        """
        Converts a file path to a module-style path string.
        """
        if location == "unknown" or not location:
            return "unknown"

        if not isinstance(location, (str, Path)):
            location = str(location)

        location_path = Path(location)

        location_parts = list(location_path.parts)

        if location_path.suffix and location_path.suffix in location_parts[-1]:
            location_parts[-1] = location_parts[-1].replace(location_path.suffix, "")

        if "app" in location_parts:
            try:
                root_index = location_parts.index("app")
                location_parts = location_parts[root_index:]
            except ValueError:
                pass

        return ".".join(location_parts)


class UniversalLogger:
    """Universal logger for the FinAlgo platform."""

    def __init__(self, name: str = "finalgo", log_level: Optional[int] = None):
        """Initialize the universal logger.

        Args:
            name: Name of the logger
            log_level: Logging level (if None, uses global config)
        """
        self.name = name

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(settings.LOG_LEVEL or logging.INFO)

        # Remove existing handlers if any
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Create formatter
        log_format = '[%(asctime)s] %(levelname)-8s [%(location)s:%(lineno)d] %(message)s'
        formatter = logging.Formatter(log_format)
        colored_formatter = ColoredFormatter(log_format)

        # Add sensitive data filter
        sensitive_filter = SensitiveDataFilter()

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.addFilter(sensitive_filter)
        console_handler.setFormatter(colored_formatter)
        self.logger.addHandler(console_handler)

        # Create file handler
        # Create log directory if it doesn't exist
        if settings.LOG_TO_FILE and settings.LOG_DIR:
            if not os.path.exists(settings.LOG_DIR):
                os.makedirs(settings.LOG_DIR)

            log_file = os.path.join(settings.LOG_DIR, f"{name}.log")
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=settings.LOG_MAX_FILE_SIZE,
                backupCount=settings.LOG_BACKUP_COUNT,
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Create adapter for location information
        self.adapter = LocationAdapter(self.logger, {})


    def _get_caller_location_info(self) -> Tuple[str, int, str]:
        """Get information about the caller's location.

        Returns:
            Tuple[str, int, str]: File path, line number, and module.class.method
        """
        # Get the caller's frame
        frame = inspect.currentframe().f_back
        code = frame.f_code if frame else None
        class_or_method = code.co_qualname if code else "unknown"

        if frame is None:
            return "unknown", 0, "unknown"

        # Go up 3 frames to get the caller of the logging method
        # (1 for this method, 1 for the logging method, 1 for the caller)
        frame = frame.f_back
        if frame is None:
            return "unknown", 0, "unknown"
        frame = frame.f_back
        if frame is None:
            return "unknown", 0, "unknown"
        frame = frame.f_back
        if frame is None:
            return "unknown", 0, "unknown"

        # Get file path and line number
        file_path = frame.f_code.co_filename
        line_number = frame.f_lineno

        # Convert file path to a module-style path for location.
        try:
            path_obj = Path(file_path)
            
            # Determine the root for module path calculation.
            # We assume 'app' is a root for application code.
            parts = list(path_obj.parts)
            if "app" in parts:
                app_index = parts.index("app")
                module_parts = parts[app_index:]
            else:
                # Fallback for files outside 'app' (e.g., scripts, tests)
                module_parts = [path_obj.stem]

            # Remove file extension from the last part.
            if module_parts:
                module_parts[-1] = Path(module_parts[-1]).stem

            module_path = ".".join(module_parts)
            
            # For __init__.py files, the location is the package name.
            if module_path.endswith(".__init__"):
                module_path = module_path.rsplit(".__init__", 1)[0]
                
        except Exception:
            # Fallback to Python's __name__ if path parsing fails.
            module_path = frame.f_globals.get("__name__", "unknown")

        # Try to get the class name from 'self' (instance methods) or 'cls' (class methods).
        try:
            class_name = ""
            if 'self' in frame.f_locals:
                class_name = frame.f_locals['self'].__class__.__name__
            elif 'cls' in frame.f_locals:
                cls_arg = frame.f_locals['cls']
                if inspect.isclass(cls_arg):
                    class_name = cls_arg.__name__
        except (AttributeError, KeyError):
            class_name = ""

        # Get the function/method name.
        function_name = frame.f_code.co_name

        # Construct the final location string: module.class.function
        location_parts = [module_path]
        if class_name:
            location_parts.append(class_name)
        
        # Add function name, but ignore for top-level module code.
        if function_name != "<module>":
            location_parts.append(function_name)
        
        location = ".".join(part for part in location_parts if part)

        return file_path, line_number, location


    def log_debug(self, message: str, location: Optional[Any] = None) -> None:
        """Log debug information with detailed caller location."""
        if location:
            self.adapter.debug(message, location={"location_str": self.adapter._to_string(location)})
        else:
            file_path, line_number, location_str = self._get_caller_location_info()
            self.adapter.debug(message, location={
                "file_path": file_path,
                "line_number": line_number,
                "location_str": location_str,
            })

    def log_info(self, message: str, location: Optional[Any] = None) -> None:
        """Log information with detailed caller location."""
        if location:
            self.adapter.info(message, location={"location_str": self.adapter._to_string(location)})
        else:
            file_path, line_number, location_str = self._get_caller_location_info()
            self.adapter.info(message, location={
                "file_path": file_path,
                "line_number": line_number,
                "location_str": location_str,
            })

    def log_warning(self, message: str, location: Optional[Any] = None) -> None:
        """Log warning information with detailed caller location."""
        if location:
            self.adapter.warning(message, location={"location_str": self.adapter._to_string(location)})
        else:
            file_path, line_number, location_str = self._get_caller_location_info()
            self.adapter.warning(message, location={
                "file_path": file_path,
                "line_number": line_number,
                "location_str": location_str,
            })

    def log_error(
        self,
        message: str,
        error: Optional[Exception] = None,
        location: Optional[Any] = None,
    ) -> None:
        """Log error information with detailed caller location."""
        if location:
            location_details = {"location_str": self.adapter._to_string(location)}
        else:
            file_path, line_number, location_str = self._get_caller_location_info()
            location_details = {
                "file_path": file_path,
                "line_number": str(line_number),
                "location_str": location_str,
            }

        if error:
            self.adapter.error(
                f"{message} - {str(error)}", exc_info=True, location=location_details
            )
        else:
            self.adapter.error(message, location=location_details)

    def log_exception(self, message: str, location: Optional[Any] = None, exc_info=True) -> None:
        """Log exception information with detailed caller location."""
        if location:
            self.adapter.exception(message, location={"location_str": self.adapter._to_string(location)}, exc_info=exc_info)
        else:
            file_path, line_number, location_str = self._get_caller_location_info()
            self.adapter.exception(message, location={
                "file_path": file_path,
                "line_number": line_number,
                "location_str": location_str,
            }, exc_info=exc_info)

    def log_critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        location: Optional[Any] = None,
    ) -> None:
        """Log critical information with detailed caller location."""
        if location:
            location_details = {"location_str": self.adapter._to_string(location)}
        else:
            file_path, line_number, location_str = self._get_caller_location_info()
            location_details = {
                "file_path": file_path,
                "line_number": str(line_number),
                "location_str": location_str,
            }

        if error:
            self.adapter.critical(
                f"{message} - {str(error)}", exc_info=True, location=location_details
            )
        else:
            self.adapter.critical(message, location=location_details)
            
    def set_level(self, level: int) -> None:
        """Set the logging level.

        Args:
            level: Logging level
        """
        self.logger.setLevel(level)


# # Create default logger instance
logger = UniversalLogger()


def log_startup_banner(l, title: str, url: str, separator_char: str = "=", width: int = 60):
    """
    Log a highlighted startup banner with URL.
    
    Args:
        title: Main title text
        url: URL to highlight
        separator_char: Character for separator lines
        width: Width of the banner
    """
    if not COLORAMA_AVAILABLE:
        # Fallback without colors
        logger.log_info(separator_char * width)
        logger.log_info(title)
        logger.log_info(f"Access the application at: {url}")
        logger.log_info(separator_char * width)
        return
    
    # Check if colors are enabled
    log_colors = os.getenv('LOG_COLORS', 'True').lower() == 'true'
    force_color = os.getenv('FORCE_COLOR', '').lower() in ['1', 'true', 'yes', 'on']
    
    if not log_colors and not force_color:
        # Fallback without colors
        logger.log_info(separator_char * width)
        logger.log_info(title)
        logger.log_info(f"Access the application at: {url}")
        logger.log_info(separator_char * width)
        return
    
    # Create colorful banner
    bright_green = Fore.GREEN + Style.BRIGHT
    bright_yellow = Fore.YELLOW + Style.BRIGHT
    bright_cyan = Fore.CYAN + Style.BRIGHT
    reset = Style.RESET_ALL
    
    # Log colored banner
    separator_line = f"{bright_yellow}{separator_char * width}{reset}"
    title_line = f"{bright_green}{title}{reset}"
    url_line = f"Access the application at: {bright_cyan}{url}{reset}"
    
    logger.log_info(separator_line)
    logger.log_info(title_line)
    logger.log_info(url_line)
    logger.log_info(separator_line)



# Suppress noisy third-party loggers
if True:
    logging.getLogger('werkzeug').setLevel(logging.WARNING) # Flask specific, might be removed
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    # Suppress hpack DEBUG logs - they have format string bugs and are not useful
    logging.getLogger('hpack.hpack').setLevel(logging.INFO)
    logging.getLogger('hpack').setLevel(logging.INFO)

