import logging
import sys
import os
import site
import re
import inspect
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional
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
        'location': Fore.MAGENTA,
        'reset': Style.RESET_ALL,
    }
except ImportError:
    COLORAMA_AVAILABLE = False

PROJECT_NAME = 'app' # Adjust as needed for your project structure
# logging method names to detect in code context
LOGGING_LEVELS = ["debug", "info", "warning", "error", "critical"]

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


class LocationBuilder:
    """Helper class to build location strings for log records."""

    @staticmethod
    def find_caller_frame():
        frame = inspect.currentframe()

        if frame is None:
            return None

        outer_frames = inspect.getouterframes(frame)

        # --- Identify paths to exclude ---
        site_paths = set()
        if hasattr(site, "getsitepackages"):
            site_paths.update(site.getsitepackages())
        if hasattr(site, "getusersitepackages"):
            site_paths.add(site.getusersitepackages())

        stdlib_dir = os.path.dirname(os.__file__)
        venv_dir = os.getenv("VIRTUAL_ENV")

        skip_roots = {os.path.realpath(p) for p in site_paths if os.path.exists(p)}
        if stdlib_dir:
            skip_roots.add(os.path.realpath(stdlib_dir))
        if venv_dir:
            skip_roots.add(os.path.realpath(venv_dir))

        filter_frames = []
        for f in outer_frames:
            file_path = os.path.realpath(f.filename)

            # --- Exclusions ---
            if file_path.endswith("logging/__init__.py"):
                continue
            elif not Path(file_path).exists():
                continue
            elif __file__ == file_path:
                continue
            elif ".vscode/extensions" in file_path:
                continue
            elif "site-packages" in file_path or "dist-packages" in file_path:
                continue
            elif any(file_path.startswith(root) for root in skip_roots):
                continue
            else:
                # ✅ Accept first frame not matching any skip rule
                code_context = f.code_context
                if code_context:
                    line = "".join(code_context).strip().lower()
                    if any(f".{lvl}(" in line for lvl in LOGGING_LEVELS):
                        filter_frames.append(f)
                    else:
                        continue

        total_filtered = len(filter_frames)
        if total_filtered == 1:
            return filter_frames[0]
        else:
            return None

    @staticmethod
    def build_callerpath(frame_info):
        # Convert file path to a module-style path for location.
        file_path = frame_info.filename
        frame = frame_info.frame
        try:

            path_obj = Path(file_path)
            
            # Determine the root for module path calculation.
            # We assume 'app' is a root for application code.
            parts = list(path_obj.parts)
            if PROJECT_NAME in parts:
                app_index = parts.index(PROJECT_NAME)
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

        return location
    

class LocationInfoFilter(logging.Filter):
    """
    Filter to add detailed location information to log records.
    It adds 'location' and 'custom_lineno' attributes.
    """
    def filter(self, record):
        caller_frame = LocationBuilder.find_caller_frame()
        record.location = LocationBuilder.build_callerpath(caller_frame)
        return True


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels and components for console output."""
    
    def __init__(self, fmt=None, datefmt=None, enable_colors=True):
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
        # The filter adds custom_lineno. We use it for the output.
        record.lineno = getattr(record, 'custom_lineno', record.lineno)

        if not self.enable_colors:
            return super().format(record)

        # Get the original formatted message
        try:
            original_format = super().format(record)
        except (TypeError, ValueError):
            try:
                record.message = str(record.msg)
                record.args = None
                original_format = super().format(record)
            except Exception:
                return f"[{record.levelname}] {record.msg}"
        
        # Apply colors
        level_color = LOG_COLORS.get(record.levelname, '')
        reset = COMPONENT_COLORS.get('reset', '')
        timestamp_color = COMPONENT_COLORS.get('timestamp', '')
        location_color = COMPONENT_COLORS.get('location', '')
        
        # Color timestamp (first bracketed group)
        original_format = re.sub(
            r'(\[.*?\])',
            f'{timestamp_color}\\1{reset}',
            original_format,
            count=1
        )
        
        # Color log level
        original_format = original_format.replace(
            record.levelname,
            f'{level_color}{record.levelname}{reset}'
        )
        
        # Color location
        if hasattr(record, 'location'):
            location_str = f"[{record.location}:{record.lineno}]"
            colored_location = f"[{location_color}{record.location}{reset}:{record.lineno}]"
            original_format = original_format.replace(location_str, colored_location)
            
        return original_format


class CallerLoggerAdapter(logging.LoggerAdapter):
    """
    A LoggerAdapter that automatically injects caller information:
    project.module.Class.method
    """

    def _find_caller_frame(self):
        frame = inspect.currentframe()

        if frame is None:
            return None

        outer_frames = inspect.getouterframes(frame)

        # --- Identify paths to exclude ---
        site_paths = set()
        if hasattr(site, "getsitepackages"):
            site_paths.update(site.getsitepackages())
        if hasattr(site, "getusersitepackages"):
            site_paths.add(site.getusersitepackages())

        stdlib_dir = os.path.dirname(os.__file__)
        venv_dir = os.getenv("VIRTUAL_ENV")

        skip_roots = {os.path.realpath(p) for p in site_paths if os.path.exists(p)}
        if stdlib_dir:
            skip_roots.add(os.path.realpath(stdlib_dir))
        if venv_dir:
            skip_roots.add(os.path.realpath(venv_dir))

        filter_frames = []
        for f in outer_frames:
            file_path = os.path.realpath(f.filename)

            # --- Exclusions ---
            if file_path.endswith("logging/__init__.py"):
                continue
            elif not Path(file_path).exists():
                continue
            elif __file__ == file_path:
                continue
            elif ".vscode/extensions" in file_path:
                continue
            elif "site-packages" in file_path or "dist-packages" in file_path:
                continue
            elif any(file_path.startswith(root) for root in skip_roots):
                continue
            else:
                # ✅ Accept first frame not matching any skip rule
                code_context = f.code_context
                if code_context:
                    line = "".join(code_context).strip().lower()
                    if any(f".{lvl}(" in line for lvl in LOGGING_LEVELS):
                        filter_frames.append(f)
                    else:
                        continue

        total_filtered = len(filter_frames)
        if total_filtered == 1:
            return filter_frames[0]
        else:
            return None

    def _build_callerpath(self, frame_info):
        # Convert file path to a module-style path for location.
        file_path = frame_info.filename
        frame = frame_info.frame
        try:

            path_obj = Path(file_path)
            
            # Determine the root for module path calculation.
            # We assume 'app' is a root for application code.
            parts = list(path_obj.parts)
            if PROJECT_NAME in parts:
                app_index = parts.index(PROJECT_NAME)
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

        return location
    
    def process(self, msg, kwargs):
        c_frame = LocationBuilder.find_caller_frame()
        if c_frame is not None:
            # Inject `location` into the log record's extra fields
            extra = kwargs.get("extra", {})
            extra["location"] = LocationBuilder.build_callerpath(c_frame)
            kwargs["extra"] = extra
        return msg, kwargs


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


def setup_logging():
    """Initialize the logging configuration from environment variables."""
    from app.core.config import settings # Import settings here to avoid circular dependency

    # Get configuration from environment
    log_format = '[%(asctime)s] %(levelname)s [%(location)s:%(lineno)d] %(message)s'
    log_retention = int(settings.LOG_RETENTION)
    log_colors = settings.LOG_COLORS
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL or logging.INFO)
    
    # Remove existing handlers
    root_logger.handlers = []

    # Create filters
    sensitive_filter = SensitiveDataFilter()
    location_filter = LocationInfoFilter()

    # Create formatters
    console_formatter = ColoredFormatter(log_format, enable_colors=log_colors)
    file_formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(sensitive_filter)
    console_handler.addFilter(location_filter)
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if settings.LOG_TO_FILE:
        log_path = Path(settings.LOG_DIR)
        log_path.mkdir(exist_ok=True)
        
        # Clean up old logs
        cleanup_old_logs(log_path, log_retention)
        
        # Create file handler with daily rotation
        log_file = log_path / f"fincomp_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=log_retention,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(sensitive_filter)
        file_handler.addFilter(location_filter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING) # Flask specific, might be removed
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    # Suppress hpack DEBUG logs - they have format string bugs and are not useful
    logging.getLogger('hpack.hpack').setLevel(logging.INFO)
    logging.getLogger('hpack').setLevel(logging.INFO)


def highlight_url(url: str, text: str = '') -> str:
    """
    Create a highlighted URL string with bright colors and styling.
    
    Args:
        url: The URL to highlight
        text: Optional text to display instead of the URL
        
    Returns:
        Formatted string with colors (if available) or plain text
    """
    if not COLORAMA_AVAILABLE or not settings.LOGS_COLORS_ENABLE:
        return text or url
    
    # Create bright, attention-grabbing formatting
    bright_cyan = Fore.CYAN + Style.BRIGHT
    bright_white = Fore.WHITE + Style.BRIGHT
    reset = Style.RESET_ALL
        
    # Format: [bright_white]text[reset] -> [bright_cyan]url[reset]
    if text and text != url:
        return f"{bright_white}{text}{reset} -> {bright_cyan}{url}{reset}"
    else:
        return f"{bright_cyan}{url}{reset}"


def log_startup_banner(logger, title: str, url: str, separator_char: str = "=", width: int = 60):
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
        logger.info(separator_char * width)
        logger.info(title)
        logger.info(f"Access the application at: {url}")
        logger.info(separator_char * width)
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
    
    logger.info(separator_line)
    logger.info(title_line)
    logger.info(url_line)
    logger.info(separator_line)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance configured with the module name and color support
    """
    # return CallerLoggerAdapter(logging.getLogger(name), {})
    return logging.getLogger(name)

# Initialize logging on import
setup_logging()
logger = get_logger(__name__)