#!/usr/bin/env python3
"""
FritzBox Router Watchdog - Main Entry Point
Simple entry point that delegates to CLI
"""

from .cli import main

if __name__ == "__main__":
    main()
