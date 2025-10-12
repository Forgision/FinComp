import logging
import inspect
import os
import sys
import site
from pathlib import Path

PROJECT_NAME = 'app' # Adjust as needed for your project structure

class CallerLoggerAdapter(logging.LoggerAdapter):
    """
    A LoggerAdapter that automatically injects caller information:
    project.module.Class.method
    """

    def _find_caller_frame(self):
        frame = inspect.currentframe()
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
            if __file__ == file_path:
                continue
            if ".vscode/extensions" in file_path:
                continue
            if "site-packages" in file_path or "dist-packages" in file_path:
                continue
            if any(file_path.startswith(root) for root in skip_roots):
                continue

            # ✅ Accept first frame not matching any skip rule
            filter_frames.append(f)

        total_filtered = len(filter_frames)
        if total_filtered == 1:
            return filter_frames[0]
        else:
            return None
    
    def _build_called_path(self, frame_info):
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
        # Inspect the stack to find the caller (skip logging internals)
        frame = inspect.currentframe()
        
        if frame is None:
            return msg, kwargs
        
        frame_1 = frame.f_back
        
        outer_frames = inspect.getouterframes(frame)
        c_frame = self._find_caller_frame()
        filter_frames = [f for f in outer_frames if not f.filename.endswith("logging/__init__.py") and 'site-packages' not in f.filename and __file__ != f.filename]
        caller_frame_info = None
        for f in outer_frames:
            f_index = outer_frames.index(f)
            prev_f = outer_frames[f_index - 1] if f_index > 0 else None
            if (prev_f is not None and
                prev_f.filename.endswith("logging/__init__.py") and
                not f.filename.endswith("logging/__init__.py")):
                caller_frame_info = f
                break

        module_name = "<unknown_module>"
        class_name = None
        func_name = "<unknown_func>"
        caller_frame = caller_frame_info.frame if caller_frame_info else None

        # Inject `caller` into the log record's extra fields
        extra = kwargs.get("extra", {})
        extra["caller"] = self._build_called_path(caller_frame_info)

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name=None):
    """Create a logger wrapped with CallerLoggerAdapter."""
    base_logger = logging.getLogger(name)
    if not base_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            # "%(asctime)s [%(levelname)s] [caller=%(caller)s] %(message)s"
            '%(asctime)s | %(levelname)s | %(caller)s:%(lineno)d | %(message)s'
        )
        handler.setFormatter(formatter)
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)
    return CallerLoggerAdapter(base_logger, {})