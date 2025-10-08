"""Logging configuration for the Growatt Weather Based Charger."""

import os
import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

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

def setup_logging(
    log_dir: str,
    log_file: str,
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    add_console_handler: bool = True,
    additional_fields: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """
    Set up application logging with file rotation and optional console output.
    
    Args:
        log_dir: Directory to store log files
        log_file: Name of the log file
        level: Logging level
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        add_console_handler: Whether to add a console handler
        additional_fields: Additional fields to include in every log entry
        
    Returns:
        Configured logger instance
    """
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('growatt-charger')
    logger.setLevel(level)
    
    # Create JSON formatter
    formatter = JSONFormatter(**(additional_fields or {}))
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add console handler if requested
    if add_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

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
        kwargs.setdefault('extra', {}).update(self.extra)
        return msg, kwargs

def get_logger(
    name: str,
    context: Optional[Dict[str, Any]] = None
) -> LoggerAdapter:
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