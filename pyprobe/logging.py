"""
Centralized logging configuration for PyProbe.

Usage:
    from pyprobe.logging import setup_logging, get_logger
    
    # In __main__.py (once at startup)
    setup_logging(level='DEBUG', log_file='/tmp/pyprobe_debug.log')
    
    # In any module
    logger = get_logger(__name__)
    logger.debug("Some debug message")
"""

import logging
import sys
from typing import Optional

# Default log file path
DEFAULT_LOG_FILE = '/tmp/pyprobe_debug.log'

# Global flag to track if logging has been configured
_logging_configured = False


def setup_logging(
    level: str = 'WARNING',
    log_file: Optional[str] = None,
    console: bool = False
) -> None:
    """
    Configure logging for PyProbe.
    
    Args:
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: Path to log file (only used if level is DEBUG or INFO)
        console: If True, also log to console (stderr)
    """
    global _logging_configured
    
    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    
    # Configure root logger for pyprobe
    logger = logging.getLogger('pyprobe')
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Format string
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    
    # Add file handler for DEBUG/INFO levels
    if numeric_level <= logging.INFO and log_file:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add null handler if no handlers (prevents "no handler" warnings)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    
    _logging_configured = True
    
    # Log startup message at DEBUG level
    logger.debug(f"Logging configured: level={level}, log_file={log_file}, console={console}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    # Ensure all pyprobe loggers are children of 'pyprobe'
    if name.startswith('pyprobe'):
        return logging.getLogger(name)
    return logging.getLogger(f'pyprobe.{name}')
