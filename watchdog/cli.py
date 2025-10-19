#!/usr/bin/env python3
"""
FritzBox Router Watchdog - Command Line Interface
Command line tool for the FritzBox Watchdog
"""

import sys
import argparse
import os
from .watchdog import FritzBoxWatchdog
from .libs.logger import log_info, log_error, get_log_file_location, initialize_logger, test_logging
from .libs.colors import Colors, Status, error



def show_status():
    """Show current watchdog status"""
    try:
        # Try to create a watchdog instance to check configuration
        watchdog = FritzBoxWatchdog()
        status = watchdog.get_status()

        print("FritzBox Watchdog Status")
        print("=" * 30)
        print(f"Host:                    {status['host']}:{status['port']}")
        print(
            f"Check Interval:          {status['check_interval_minutes']} minutes")
        print(f"Max Failures:            {status['max_failures']}")
        print(f"Checks Performed:        {status['check_count']}")
        print(f"Consecutive Failures:    {status['consecutive_failures']}")
        print(f"Restart Count:           {status['restart_count']}")
        print(
            f"Max Restarts:            {status['max_restarts_before_cooldown']}")
        print(f"Cooldown Period:         {status['cooldown_hours']} hours")
        print(
            f"In Cooldown:             {'Yes' if status['in_cooldown'] else 'No'}")

        if status.get('cooldown_remaining_hours'):
            print(
                f"Cooldown Remaining:      {status['cooldown_remaining_hours']:.1f} hours")

        print(f"Log File:                {get_log_file_location()}")

    except Exception as e:
        log_error(f"Failed to get status: {e}")
        sys.exit(1)


def validate_configuration():
    """Validate current configuration"""
    
    print("Validating Configuration...")
    print("-" * 40)

    try:
        # Try to create watchdog instance - this will validate config
        watchdog = FritzBoxWatchdog()

        print(f"{Colors.GREEN}[OK]{Colors.NC} Configuration loaded successfully")
        print(f"{Colors.GREEN}[OK]{Colors.NC} Router: {watchdog.host}:{watchdog.port}")
        print(f"{Colors.GREEN}[OK]{Colors.NC} Credentials: {'Configured' if watchdog.username and watchdog.password else 'Missing'}")

        # Test router connection
        print("Testing router connection...")
        if watchdog.fritz.check_connection():
            print(f"{Colors.GREEN}[OK]{Colors.NC} Router is reachable")
        else:
            print(f"{Status.FAIL} Router is not reachable")
            sys.exit(1)

        print(f"\n{Status.SUCCESS} Configuration is valid and ready for use")

    except Exception as e:
        print(error(f"Configuration validation failed: {e}"))
        print(f"\n{Colors.YELLOW}Please check:{Colors.NC}")
        print("1. Configuration file exists and is readable")
        print("2. All required settings are present")
        print("3. Router is accessible")
        sys.exit(1)


def main():
    """Command line interface for FritzBox Watchdog"""
    # Initialize logger first to ensure file logging works
    initialize_logger()

    # Get current log file location for help text
    from .libs.logger import get_log_file_location
    log_file = get_log_file_location()

    # Create custom help text with better formatting
    epilog_text = f"""
Configuration:
  Set your router credentials in one of these files:
    /opt/fritzbox-watchdog/.env  (preferred - easy access)
    /etc/fritzbox-watchdog/.env  (system-wide)
    ./.env                       (current directory)

  Example .env file:
    FRITZBOX_HOST=192.168.1.1
    FRITZBOX_PORT=49000
    FRITZBOX_USERNAME=your_username
    FRITZBOX_PASSWORD=your_password
    MAX_RESTARTS_BEFORE_COOLDOWN=3
    COOLDOWN_HOURS=12

Cooldown Feature:
  After 3 restart attempts, the system enters a 12-hour cooldown
  period to prevent excessive router restarts. The cooldown resets
  when internet connectivity is successfully restored.

Log Files:
  Service logs:     /var/log/fritzbox-watchdog/watchdog.log  (systemd service)
  Manual run logs:  ~/.local/share/fritzbox-watchdog/watchdog.log  (user testing)
  Current session:  {log_file}

Useful Commands:
  View service logs:   sudo journalctl -u fritzbox-watchdog -f
  View log file:       sudo tail -f /var/log/fritzbox-watchdog/watchdog.log
  Stop service:        sudo systemctl stop fritzbox-watchdog
  Restart service:     sudo systemctl restart fritzbox-watchdog
  Test manually:       fritzbox-watchdog --once
"""

    parser = argparse.ArgumentParser(
        description='FritzBox Router Watchdog - Network connectivity monitor',
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--interval', '-i', type=int, default=1,
                        help='Check interval in minutes (default: %(default)s)')
    parser.add_argument('--failures', '-f', type=int, default=2,
                        help='Max consecutive failures before restart (default: %(default)s)')
    parser.add_argument('--wait', '-w', type=int, default=3,
                        help='Minutes to wait after router restart (default: %(default)s)')
    parser.add_argument('--once', action='store_true',
                        help='Check connectivity once and restart if needed, then exit')
    parser.add_argument('--monitor', action='store_true',
                        help='Start continuous monitoring (default behavior)')
    parser.add_argument('--log-location', action='store_true',
                        help='Show current log file location and exit')
    parser.add_argument('--test-logging', action='store_true',
                        help='Test the logging system and exit')
    parser.add_argument('--status', action='store_true',
                        help='Show current watchdog status and exit')
    parser.add_argument('--validate-config', action='store_true',
                        help='Validate configuration and exit')
    parser.add_argument('--version', action='version', version='FritzBox Watchdog 1.0.0',
                        help='Show version information')

    args = parser.parse_args()

    # Handle version query (already handled by argparse)

    # Handle log location query
    if args.log_location:
        print(f"Log file location: {get_log_file_location()}")
        return

    # Handle logging test
    if args.test_logging:
        test_logging()
        return

    # Handle status query
    if args.status:
        show_status()
        return

    # Handle config validation
    if args.validate_config:
        validate_configuration()
        return

    # Create watchdog instance with custom settings
    try:
        watchdog = FritzBoxWatchdog(
            check_interval_minutes=args.interval,
            max_failures=args.failures,
            restart_wait_minutes=args.wait
        )
    except Exception as e:
        log_error(f"Failed to initialize watchdog: {e}")
        log_error("Please check your configuration and try again")
        sys.exit(1)

    try:
        if args.once:
            result = watchdog.check_once()
            sys.exit(0 if result else 1)
        else:
            watchdog.start_monitoring()
    except Exception as e:
        log_error(f"Watchdog operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_info("Operation cancelled by user.")
        sys.exit(0)
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes
        raise
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        log_error("Please check logs and configuration")
        sys.exit(1)
