#!/usr/bin/env python3
"""
ASCII Color Codes for Terminal Output in Python
"""

import os
import sys

# Check if we should use colors (interactive terminal and not in systemd)


def should_use_colors():
    """Determine if colors should be used based on environment"""
    # Disable colors if not a TTY or if running under systemd
    if not sys.stdout.isatty():
        return False

    # Check if we're running under systemd
    if os.environ.get('JOURNAL_STREAM') or os.environ.get('INVOCATION_ID'):
        return False

    # Check TERM variable
    term = os.environ.get('TERM', '')
    if term in ['dumb', '']:
        return False

    return True


USE_COLORS = should_use_colors()

# Text Colors


class Colors:
    if USE_COLORS:
        RED = '\033[0;31m'
        GREEN = '\033[0;32m'
        YELLOW = '\033[1;33m'
        BLUE = '\033[0;34m'
        PURPLE = '\033[0;35m'
        CYAN = '\033[0;36m'
        WHITE = '\033[1;37m'
        GRAY = '\033[0;37m'

        # Background Colors
        BG_RED = '\033[41m'
        BG_GREEN = '\033[42m'
        BG_YELLOW = '\033[43m'
        BG_BLUE = '\033[44m'
        BG_PURPLE = '\033[45m'
        BG_CYAN = '\033[46m'

        # Text Styles
        BOLD = '\033[1m'
        DIM = '\033[2m'
        UNDERLINE = '\033[4m'
        BLINK = '\033[5m'
        REVERSE = '\033[7m'

        # Reset
        NC = '\033[0m'  # No Color / Reset
    else:
        # No colors - all empty strings
        RED = GREEN = YELLOW = BLUE = PURPLE = CYAN = WHITE = GRAY = ''
        BG_RED = BG_GREEN = BG_YELLOW = BG_BLUE = BG_PURPLE = BG_CYAN = ''
        BOLD = DIM = UNDERLINE = BLINK = REVERSE = NC = ''

# Status Labels with Colors


class Status:
    ERROR = f"{Colors.RED}[ERROR]{Colors.NC}"
    SUCCESS = f"{Colors.GREEN}[SUCCESS]{Colors.NC}"
    WARNING = f"{Colors.YELLOW}[WARNING]{Colors.NC}"
    INFO = f"{Colors.CYAN}[INFO]{Colors.NC}"
    DEBUG = f"{Colors.GRAY}[DEBUG]{Colors.NC}"
    CONFIG = f"{Colors.BLUE}[CONFIG]{Colors.NC}"
    CHECK = f"{Colors.YELLOW}[CHECK]{Colors.NC}"
    RESTART = f"{Colors.RED}[RESTART]{Colors.NC}"
    MONITOR = f"{Colors.CYAN}[MONITOR]{Colors.NC}"
    CONNECT = f"{Colors.GREEN}[CONNECT]{Colors.NC}"
    DISCONNECT = f"{Colors.RED}[DISCONNECT]{Colors.NC}"
    PASS = f"{Colors.GREEN}[PASS]{Colors.NC}"
    FAIL = f"{Colors.RED}[FAIL]{Colors.NC}"
    STOP = f"{Colors.RED}[STOP]{Colors.NC}"

# Helper functions


def colorize(text, color):
    """Add color to text"""
    return f"{color}{text}{Colors.NC}"


def success(text):
    """Print success message"""
    return f"{Status.SUCCESS} {text}"


def error(text):
    """Print error message"""
    return f"{Status.ERROR} {text}"


def warning(text):
    """Print warning message"""
    return f"{Status.WARNING} {text}"


def info(text):
    """Print info message"""
    return f"{Status.INFO} {text}"


def check(text):
    """Print check message"""
    return f"{Status.CHECK} {text}"
