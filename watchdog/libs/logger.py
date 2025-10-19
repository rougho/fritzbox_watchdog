#!/usr/bin/env python3
"""
Professional Logging Module for FritzBox Watchdog
Replaces raw print() statements with proper logging
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


class FlushingRotatingFileHandler(RotatingFileHandler):
    """Custom handler that flushes immediately after each log entry"""

    def _open(self):
        """Open the file with unbuffered mode for immediate writes"""
        # Open file with line buffering (1) for immediate writes
        return open(self.baseFilename, self.mode, buffering=1, encoding=self.encoding)

    def emit(self, record):
        super().emit(record)
        self.flush()  # Force immediate write to disk
        # Force OS-level sync to disk
        if hasattr(self.stream, 'fileno'):
            try:
                os.fsync(self.stream.fileno())
            except (OSError, AttributeError):
                pass  # Ignore if fsync is not available


# Add custom SUCCESS log level
SUCCESS = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(SUCCESS, 'SUCCESS')


class WatchdogLogger:
    """Professional logger for the watchdog application"""

    def __init__(self, name="fritzbox-watchdog", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Always ensure we have both console and file handlers
        self._ensure_console_handler()
        self._ensure_file_handler()

    def _ensure_console_handler(self):
        """Ensure console handler exists"""
        # Check if console handler already exists
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not hasattr(handler, 'baseFilename'):
                return  # Console handler already exists

        # Add console handler
        self._setup_console_handler()

    def _ensure_file_handler(self):
        """Ensure file handler exists"""
        # Check if file handler already exists
        for handler in self.logger.handlers:
            if hasattr(handler, 'baseFilename'):
                return  # File handler already exists

        # Add file handler
        self._setup_file_handler()

    def _get_log_file_path(self):
        """Determine the best location for log files"""
        # Try different locations in order of preference
        possible_paths = [
            # System-wide (preferred)
            "/var/log/fritzbox-watchdog/watchdog.log",
            "/opt/fritzbox-watchdog/logs/watchdog.log",  # Application directory
            os.path.expanduser(
                "~/.local/share/fritzbox-watchdog/watchdog.log"),  # User-specific
            "/tmp/fritzbox-watchdog.log"  # Fallback temporary location
        ]

        for log_path in possible_paths:
            try:
                # Create directory if it doesn't exist
                log_dir = os.path.dirname(log_path)
                Path(log_dir).mkdir(parents=True, exist_ok=True)

                # Test if we can write to this location
                test_file = log_path + ".test"
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)

                return log_path
            except (PermissionError, OSError):
                continue

        # If all else fails, use current directory
        return "./fritzbox-watchdog.log"

    def _setup_console_handler(self):
        """Setup console output with professional formatting"""
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _setup_file_handler(self):
        """Setup file logging with rotation"""
        log_file = self._get_log_file_path()

        try:
            # Use custom FlushingRotatingFileHandler for immediate writes
            handler = FlushingRotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,  # Keep 5 backup files
                encoding='utf-8'
            )
            # Force immediate write to file (disable buffering)
            handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            # Test that logging actually works by writing a test message
            self.logger.info(
                f"Logging initialized successfully to: {log_file}")

            # Verify the file was actually created and written to
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                # Silent success - file logging is working
                pass
            else:
                print(f"✗ Warning: Log file not found or empty at: {log_file}")

        except Exception as e:
            # If file logging fails, at least log to console
            error_msg = f"Failed to setup file logging: {e}"
            # Print to console since logger might not work
            print(f"✗ {error_msg}")
            self.logger.error(error_msg)

    def get_log_file_path(self):
        """Get the current log file path for informational purposes"""
        for handler in self.logger.handlers:
            if hasattr(handler, 'baseFilename'):
                return handler.baseFilename
        return "No file logging configured"

    def _force_immediate_write(self):
        """Force immediate write to all file handlers"""
        for handler in self.logger.handlers:
            if hasattr(handler, 'baseFilename'):  # File handler
                try:
                    handler.flush()
                    if hasattr(handler.stream, 'fileno'):
                        os.fsync(handler.stream.fileno())
                except (OSError, AttributeError):
                    pass  # Ignore if fsync is not available

    def info(self, message):
        """Log info message"""
        self.logger.info(message)
        self._force_immediate_write()

    def error(self, message):
        """Log error message"""
        self.logger.error(message)
        self._force_immediate_write()

    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
        self._force_immediate_write()

    def success(self, message):
        """Log success message with custom SUCCESS level"""
        self.logger.log(SUCCESS, message)
        self._force_immediate_write()

    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
        self._force_immediate_write()


# Global logger instance - initialized lazily
_logger = None


def _get_logger():
    """Get or create the global logger instance"""
    global _logger
    if _logger is None:
        _logger = WatchdogLogger()
        # Force a test write to ensure logging is working
        _logger.info("Logger initialized and ready")
    return _logger


# Convenience functions


def log_info(message):
    _get_logger().info(message)


def log_error(message):
    _get_logger().error(message)


def log_warning(message):
    _get_logger().warning(message)


def log_success(message):
    _get_logger().success(message)


def log_debug(message):
    _get_logger().debug(message)


def get_log_file_location():
    """Get the current log file path"""
    return _get_logger().get_log_file_path()


def initialize_logger():
    """Explicitly initialize the logger - call this at application startup"""
    logger = _get_logger()
    return logger


def test_logging():
    """Test that logging is working by writing test messages"""
    print("Testing logging system...")

    logger = _get_logger()
    log_file = logger.get_log_file_path()

    print(f"Log file location: {log_file}")

    # Get current file size
    initial_size = 0
    if os.path.exists(log_file):
        initial_size = os.path.getsize(log_file)
        print(f"Initial log file size: {initial_size} bytes")

    # Write test messages
    log_info("TEST: Info message from test_logging()")
    log_warning("TEST: Warning message from test_logging()")
    log_error("TEST: Error message from test_logging()")

    # Check if file size increased
    if os.path.exists(log_file):
        new_size = os.path.getsize(log_file)
        print(f"New log file size: {new_size} bytes")
        if new_size > initial_size:
            print("✓ Logging is working - file size increased")
            return True
        else:
            print("✗ Logging may not be working - file size unchanged")
            return False
    else:
        print("✗ Log file was not created")
        return False
