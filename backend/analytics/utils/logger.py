"""
Centralized logging system for analytics operations.

This module provides structured logging with 5 log levels:
- DEBUG: Detailed diagnostic information for development
- INFO: General information about system operations
- WARNING: Warning messages for unexpected situations
- ERROR: Error messages for failures that need attention
- CRITICAL: Critical failures requiring immediate action

Usage:
    from analytics.utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing disease trends for 30 days")
    logger.warning("No data found for disease: Flu")
    logger.error("Database connection failed: %s", str(exception))
"""

import logging
import traceback
from datetime import datetime
from typing import Optional, Any


class StructuredLogger:
    """
    Structured logging wrapper that provides context-aware logging.
    
    For new users: Wraps Python's logging module to add context information
    like timestamps, function names, and operation context.
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize logger with given name.
        
        Args:
            name: Logger name (typically __name__)
            level: Initial log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log debug messages.
        
        For new users: Use DEBUG for detailed diagnostic information during
        development and testing. Usually hidden in production.
        
        Example:
            logger.debug("Query returned %d records", row_count)
        """
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log info messages.
        
        For new users: Use INFO for general operational messages that confirm
        the system is working as expected.
        
        Example:
            logger.info("Disease trend analysis completed in %.2fs", elapsed_time)
        """
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Log warning messages.
        
        For new users: Use WARNING for unexpected situations that don't prevent
        the system from working but may indicate a problem.
        
        Example:
            logger.warning("Low stock detected for drug: %s", drug_name)
        """
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args: Any, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """
        Log error messages.
        
        For new users: Use ERROR when something fails but the system continues.
        Include the exception object to get full traceback.
        
        Example:
            try:
                result = calculate_restock(...)
            except Exception as e:
                logger.error("Restock calculation failed", exception=e)
        """
        if exception:
            message = f"{message}\nException: {str(exception)}\nTraceback: {traceback.format_exc()}"
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args: Any, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """
        Log critical messages.
        
        For new users: Use CRITICAL for system-level failures that require
        immediate attention from administrators.
        
        Example:
            logger.critical("Database connection lost permanently", exception=db_error)
        """
        if exception:
            message = f"{message}\nException: {str(exception)}\nTraceback: {traceback.format_exc()}"
        self.logger.critical(message, *args, **kwargs)
    
    def set_level(self, level: int) -> None:
        """
        Change log level at runtime.
        
        Args:
            level: New log level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger.setLevel(level)


# Cache logger instances
_loggers = {}


def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """
    Get or create a logger instance.
    
    For new users: Returns a cached logger for the given name. Call this at
    the top of each module to get a properly configured logger.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (default: INFO)
    
    Returns:
        StructuredLogger instance
    
    Example:
        # At the top of analytics/services/disease_analytics.py:
        logger = get_logger(__name__)
        
        # Then use throughout the module:
        def calculate_disease_growth(disease_name):
            logger.info("Calculating growth for: %s", disease_name)
            try:
                result = ...
                logger.debug("Result: %s", result)
                return result
            except Exception as e:
                logger.error("Growth calculation failed", exception=e)
                raise
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, level)
    return _loggers[name]


def clear_logger_cache() -> None:
    """
    Clear the logger cache. Mainly for testing purposes.
    
    For new users: Normally not needed. Used in tests to reset logger state.
    """
    _loggers.clear()
