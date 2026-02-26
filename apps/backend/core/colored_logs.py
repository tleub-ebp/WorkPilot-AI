#!/usr/bin/env python3
"""
Colored Logs Utility
====================

Utility for differentiating backend and frontend logs in the console.
Provides distinct color schemes for each component to avoid log confusion.

Usage:
    from colored_logs import get_backend_colors, get_frontend_colors
    
    backend_colors = get_backend_colors()
    frontend_colors = get_frontend_colors()
    
    # Backend logs
    print(f"{backend_colors.DEBUG}[BACKEND DEBUG]{backend_colors.RESET} Message")
    
    # Frontend logs  
    print(f"{frontend_colors.DEBUG}[FRONTEND DEBUG]{frontend_colors.RESET} Message")
"""

import os
import sys
from typing import Dict


class LogColors:
    """Base class for log color schemes."""
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Common colors
    TIMESTAMP = "\033[90m"  # Gray
    MODULE = "\033[33m"     # Yellow  
    KEY = "\033[35m"        # Magenta
    VALUE = "\033[37m"     # White
    
    # Default level colors (can be overridden by subclasses)
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[94m"       # Bright blue
    SUCCESS = "\033[92m"   # Green
    WARNING = "\033[93m"   # Yellow
    ERROR = "\033[91m"     # Red
    
    # Prefix for component identification
    PREFIX = "\033[94m"     # Bright blue (default)
    DEBUG_DIM = "\033[96m"  # Light cyan


class BackendColors(LogColors):
    """Color scheme for backend logs - Blue/Cyan theme."""
    
    PREFIX = "\033[94m"    # Bright blue
    DEBUG = "\033[36m"     # Cyan
    DEBUG_DIM = "\033[96m" # Light cyan
    INFO = "\033[94m"      # Bright blue
    SUCCESS = "\033[92m"   # Green
    WARNING = "\033[93m"   # Yellow
    ERROR = "\033[91m"     # Red


class FrontendColors(LogColors):
    """Color scheme for frontend logs - Purple/Pink theme."""
    
    PREFIX = "\033[95m"    # Magenta
    DEBUG = "\033[95m"     # Magenta
    DEBUG_DIM = "\033[38;5;183m"  # Light magenta
    INFO = "\033[38;5;147m"  # Light purple
    SUCCESS = "\033[38;5;120m"  # Teal green
    WARNING = "\033[38;5;221m"  # Light yellow
    ERROR = "\033[38;5;196m"    # Red


def _supports_color() -> bool:
    """Check if the terminal supports ANSI colors."""
    # Check for common environment variables
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    
    # Check if we're in a terminal
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    
    # Check TERM environment variable
    term = os.environ.get("TERM", "")
    if term in ("dumb", "unknown", "unknown"):
        return False
    
    # Check for common color-supporting terminals
    if any(color_term in term for color_term in ["color", "256", "xterm", "screen", "tmux"]):
        return True
    
    return False


def get_backend_colors() -> LogColors:
    """Get the backend color scheme."""
    if _supports_color():
        return BackendColors()
    else:
        # Return a colorless version for non-color terminals
        return LogColors()


def get_frontend_colors() -> LogColors:
    """Get the frontend color scheme."""
    if _supports_color():
        return FrontendColors()
    else:
        # Return a colorless version for non-color terminals
        return LogColors()


def format_backend_log(
    message: str,
    level: str = "DEBUG",
    module: str = "backend",
    timestamp: str = None,
    **kwargs
) -> str:
    """
    Format a backend log message with appropriate colors and model info.
    
    Args:
        message: The log message
        level: Log level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
        module: Source module name
        timestamp: Optional timestamp (will generate if not provided)
        **kwargs: Additional key-value pairs to include
    
    Returns:
        Formatted colored log message
    """
    colors = get_backend_colors()
    
    if timestamp is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # Get model information for logging
    try:
        from .model_info import get_model_info_for_logs
        model_info = get_model_info_for_logs()
        model_info_string = f"{colors.RESET}[{model_info['provider']}:{model_info['model_label']}]{colors.RESET}"
    except Exception:
        # Fallback if model info is not available
        model_info_string = f"{colors.RESET}[unknown:unknown]{colors.RESET}"
    
    # Get the appropriate color for the level
    level_colors = {
        "DEBUG": colors.DEBUG,
        "INFO": colors.INFO,
        "SUCCESS": colors.SUCCESS,
        "WARNING": colors.WARNING,
        "ERROR": colors.ERROR,
    }
    level_color = level_colors.get(level.upper(), colors.DEBUG)
    
    # Build the log line
    parts = [
        f"{colors.TIMESTAMP}[{timestamp}]{colors.RESET}",
        f"{colors.PREFIX}[BACKEND]{colors.RESET}",
        f"{level_color}[{level}]{colors.RESET}",
        f"{colors.MODULE}[{module}]{colors.RESET}",
        model_info_string,
        f"{colors.DEBUG_DIM}{message}{colors.RESET}",
    ]
    
    log_line = " ".join(parts)
    
    # Add kwargs on separate lines if present
    if kwargs:
        for key, value in kwargs.items():
            formatted_value = _format_value(value)
            if "\n" in formatted_value:
                # Multi-line value
                log_line += f"\n  {colors.KEY}{key}{colors.RESET}:"
                for line in formatted_value.split("\n"):
                    log_line += f"\n    {colors.VALUE}{line}{colors.RESET}"
            else:
                log_line += f"\n  {colors.KEY}{key}{colors.RESET}: {colors.VALUE}{formatted_value}{colors.RESET}"
    
    return log_line


def format_frontend_log(
    message: str,
    level: str = "DEBUG",
    module: str = "frontend",
    timestamp: str = None,
    **kwargs
) -> str:
    """
    Format a frontend log message with appropriate colors.
    
    Args:
        message: The log message
        level: Log level (DEBUG, INFO, SUCCESS, WARNING, ERROR)
        module: Source module name
        timestamp: Optional timestamp (will generate if not provided)
        **kwargs: Additional key-value pairs to include
    
    Returns:
        Formatted colored log message
    """
    colors = get_frontend_colors()
    
    if timestamp is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # Get the appropriate color for the level
    level_colors = {
        "DEBUG": colors.DEBUG,
        "INFO": colors.INFO,
        "SUCCESS": colors.SUCCESS,
        "WARNING": colors.WARNING,
        "ERROR": colors.ERROR,
    }
    level_color = level_colors.get(level.upper(), colors.DEBUG)
    
    # Build the log line
    parts = [
        f"{colors.TIMESTAMP}[{timestamp}]{colors.RESET}",
        f"{colors.PREFIX}[FRONTEND]{colors.RESET}",
        f"{level_color}[{level}]{colors.RESET}",
        f"{colors.MODULE}[{module}]{colors.RESET}",
        f"{colors.DEBUG_DIM}{message}{colors.RESET}",
    ]
    
    log_line = " ".join(parts)
    
    # Add kwargs on separate lines if present
    if kwargs:
        for key, value in kwargs.items():
            formatted_value = _format_value(value)
            if "\n" in formatted_value:
                # Multi-line value
                log_line += f"\n  {colors.KEY}{key}{colors.RESET}:"
                for line in formatted_value.split("\n"):
                    log_line += f"\n    {colors.VALUE}{line}{colors.RESET}"
            else:
                log_line += f"\n  {colors.KEY}{key}{colors.RESET}: {colors.VALUE}{formatted_value}{colors.RESET}"
    
    return log_line


def _format_value(value, max_length: int = 200) -> str:
    """Format a value for debug output, truncating if necessary."""
    import json
    
    if value is None:
        return "None"
    
    if isinstance(value, (dict, list)):
        try:
            formatted = json.dumps(value, indent=2, default=str)
            if len(formatted) > max_length:
                formatted = formatted[:max_length] + "..."
            return formatted
        except (TypeError, ValueError):
            return str(value)[:max_length]
    
    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[:max_length] + "..."
    return str_value


def write_backend_log(message: str, level: str = "DEBUG", **kwargs) -> None:
    """Write a backend log message to stderr."""
    formatted = format_backend_log(message, level, **kwargs)
    print(formatted, file=sys.stderr)


def write_frontend_log(message: str, level: str = "DEBUG", **kwargs) -> None:
    """Write a frontend log message to stderr."""
    formatted = format_frontend_log(message, level, **kwargs)
    print(formatted, file=sys.stderr)


# Convenience functions
def backend_debug(message: str, **kwargs) -> None:
    """Log a backend debug message."""
    write_backend_log(message, "DEBUG", **kwargs)


def backend_info(message: str, **kwargs) -> None:
    """Log a backend info message."""
    write_backend_log(message, "INFO", **kwargs)


def backend_success(message: str, **kwargs) -> None:
    """Log a backend success message."""
    write_backend_log(message, "SUCCESS", **kwargs)


def backend_warning(message: str, **kwargs) -> None:
    """Log a backend warning message."""
    write_backend_log(message, "WARNING", **kwargs)


def backend_error(message: str, **kwargs) -> None:
    """Log a backend error message."""
    write_backend_log(message, "ERROR", **kwargs)


def frontend_debug(message: str, **kwargs) -> None:
    """Log a frontend debug message."""
    write_frontend_log(message, "DEBUG", **kwargs)


def frontend_info(message: str, **kwargs) -> None:
    """Log a frontend info message."""
    write_frontend_log(message, "INFO", **kwargs)


def frontend_success(message: str, **kwargs) -> None:
    """Log a frontend success message."""
    write_frontend_log(message, "SUCCESS", **kwargs)


def frontend_warning(message: str, **kwargs) -> None:
    """Log a frontend warning message."""
    write_frontend_log(message, "WARNING", **kwargs)


def frontend_error(message: str, **kwargs) -> None:
    """Log a frontend error message."""
    write_frontend_log(message, "ERROR", **kwargs)
