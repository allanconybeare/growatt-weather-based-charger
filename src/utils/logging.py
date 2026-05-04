"""Logging configuration for the Growatt Weather Based Charger."""

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after gathering all the attributes from the LogRecord.
    """

    def __init__(self, **kwargs):
        """Initialize formatter with optional additional fields."""
        self.additional_fields = kwargs
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format LogRecord in standard format.

        Args:
            record: LogRecord instance

        Returns:
            Formatted log string
        """
        # Get the standard message
        if isinstance(record.msg, dict):
            message = json.dumps(record.msg)
        else:
            message = str(record.msg)

        # Format: timestamp level: message
        return f"{self.formatTime(record)} {record.levelname}: {message}"


# def setup_logging(
#     log_dir: str,
#     log_file: str,
#     level: int = logging.INFO,
#     max_bytes: int = 10 * 1024 * 1024,  # 10MB
#     backup_count: int = 5,
#     add_console_handler: bool = True,
#     additional_fields: Optional[Dict[str, Any]] = None,
# ) -> logging.Logger:
#     """
#     Set up application logging with file rotation and optional console output.

#     Args:
#         log_dir: Directory to store log files
#         log_file: Name of the log file
#         level: Logging level
#         max_bytes: Maximum size of each log file
#         backup_count: Number of backup files to keep
#         add_console_handler: Whether to add a console handler
#         additional_fields: Additional fields to include in every log entry

#     Returns:
#         Configured logger instance
#     """
#     # Create log directory if it doesn't exist
#     os.makedirs(log_dir, exist_ok=True)

#     # Create logger
#     logger = logging.getLogger("growatt-charger")
#     logger.setLevel(level)

#     # Create JSON formatter
#     formatter = JSONFormatter(**(additional_fields or {}))

#     # Create rotating file handler
#     file_handler = RotatingFileHandler(
#         os.path.join(log_dir, log_file), maxBytes=max_bytes, backupCount=backup_count
#     )
#     file_handler.setFormatter(formatter)
#     logger.addHandler(file_handler)

#     # Add console handler if requested
#     if add_console_handler:
#         console_handler = logging.StreamHandler()
#         console_handler.setFormatter(formatter)
#         logger.addHandler(console_handler)

#     return logger


def setup_logging(
    log_dir: str,
    log_file: str,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    add_console_handler: bool = True,
    additional_fields: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
) -> logging.Logger:
    """
    Set up application logging with file rotation and optional console output.

    The effective log level is resolved in this order (highest priority first):
      1. LOG_LEVEL environment variable (e.g. LOG_LEVEL=DEBUG)
      2. [logging] level in the INI config file (if config_path is provided)
      3. ``level`` argument passed by the caller
      4. Default: logging.INFO

    Args:
        log_dir: Directory to store log files
        log_file: Name of the log file
        level: Logging level (overridden by config file or LOG_LEVEL env var)
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        add_console_handler: Whether to add a console handler
        additional_fields: Additional fields to include in every log entry
        config_path: Optional path to growatt-charger.ini to read [logging] level

    Returns:
        Configured logger instance
    """
    # Priority 2: read level from [logging] section of the INI file
    if config_path and os.path.exists(config_path):
        import configparser

        _cfg = configparser.ConfigParser()
        _cfg.read(config_path)
        ini_level = _cfg.get("logging", "level", fallback="").upper()
        if ini_level:
            numeric = getattr(logging, ini_level, None)
            if isinstance(numeric, int):
                level = numeric

    # Priority 1: LOG_LEVEL env var overrides everything
    env_level = os.getenv("LOG_LEVEL", "").upper()
    if env_level:
        numeric = getattr(logging, env_level, None)
        if isinstance(numeric, int):
            level = numeric
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Configure ROOT logger so all child loggers inherit handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create JSON formatter
    formatter = JSONFormatter(**(additional_fields or {}))

    # Create rotating file handler with UTF-8 encoding
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)  # Add to ROOT logger

    # Add console handler if requested
    if add_console_handler:
        import io
        import sys

        # Wrap stdout with UTF-8 encoding
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        console_handler = logging.StreamHandler(utf8_stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)  # Add to ROOT logger

        # Return named logger for the app (inherits from root)
        app_name = (
            additional_fields.get("app", "growatt-charger")
            if additional_fields
            else "growatt-charger"
        )
        return logging.getLogger(app_name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that allows adding context to log messages.
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process the logging message and keyword arguments.

        Args:
            msg: Log message
            kwargs: Keyword arguments

        Returns:
            Tuple of (modified message, modified kwargs)
        """
        # Add extra fields to the log record
        kwargs.setdefault("extra", {}).update(self.extra)
        return msg, kwargs


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> LoggerAdapter:
    """
    Get a logger with optional context information.

    Args:
        name: Logger name
        context: Additional context to include in log entries

    Returns:
        Logger adapter instance
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context or {})
