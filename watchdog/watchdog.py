#!/usr/bin/env python3
"""
FritzBox Router Watchdog - Core Class
Main watchdog functionality separated from CLI
"""

import sys
import os
import time
import signal
from datetime import datetime, timedelta
from .router import FritzBoxTR064
from .libs.utils import load_env_file
from .netstat import check_internet, network_diagnostics
from .libs.colors import Status, info, error, success, warning
from .libs.logger import log_info, log_error, log_warning, log_success


class FritzBoxWatchdog:
    """FritzBox Router Watchdog with configurable monitoring"""

    def __init__(self, check_interval_minutes=1, max_failures=2, restart_wait_minutes=3):
        """
        Initialize the watchdog

        Args:
            check_interval_minutes: Minutes between connectivity checks
            max_failures: Number of consecutive failures before restart
            restart_wait_minutes: Minutes to wait after router restart
        """
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.max_failures = max_failures
        self.restart_wait = restart_wait_minutes * 60  # Convert to seconds
        self.consecutive_failures = 0
        self.check_count = 0
        self.total_successful_checks = 0
        self.total_failed_checks = 0

        # Timing and statistics
        self.start_time = time.time()
        self.last_success_time = 0
        self.last_failure_time = 0

        # Restart cooldown management
        self.restart_count = 0
        self.max_restarts_before_cooldown = 3
        self.cooldown_hours = 12
        self.last_restart_time = 0
        self.in_cooldown = False
        self.total_restarts_attempted = 0
        self.successful_restarts = 0

        # Signal handling for graceful shutdown
        self._setup_signal_handlers()

        # Load configuration
        self._load_config()

        # Initialize router connection
        self.fritz = FritzBoxTR064(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )

        # Log startup
        log_info(f"FritzBoxWatchdog initialized - version 1.0.0")
        log_info(f"Process ID: {os.getpid()}")

    def _load_config(self):
        """Load configuration from environment files"""
        config_paths = [
            '/opt/fritzbox-watchdog/.env',  # Local config (preferred)
            '/etc/fritzbox-watchdog/.env',  # System config
            './.env'                        # Current directory config
        ]

        config_loaded = False
        for config_path in config_paths:
            if os.path.exists(config_path):
                load_env_file(config_path)
                config_loaded = True
                log_info(f"Using configuration from: {config_path}")
                break

        if not config_loaded:
            load_env_file()  # Try default

        # Get router configuration
        self.host = os.environ.get('FRITZBOX_HOST', '192.168.1.1')
        self.port = int(os.environ.get('FRITZBOX_PORT', '49000'))
        self.username = os.environ.get('FRITZBOX_USERNAME', '')
        self.password = os.environ.get('FRITZBOX_PASSWORD', '')

        # Override monitoring settings from environment if available
        env_check_interval = os.environ.get('CHECK_INTERVAL_MINUTES')
        env_max_failures = os.environ.get('MAX_FAILURES')
        env_restart_wait = os.environ.get('RESTART_WAIT_MINUTES')

        if env_check_interval:
            self.check_interval = int(
                env_check_interval) * 60  # Convert to seconds
        if env_max_failures:
            self.max_failures = int(env_max_failures)
        if env_restart_wait:
            self.restart_wait = int(env_restart_wait) * \
                60  # Convert to seconds

        # Get cooldown configuration from environment
        env_max_restarts = os.environ.get('MAX_RESTARTS_BEFORE_COOLDOWN')
        env_cooldown_hours = os.environ.get('COOLDOWN_HOURS')

        if env_max_restarts:
            self.max_restarts_before_cooldown = int(env_max_restarts)
        if env_cooldown_hours:
            self.cooldown_hours = int(env_cooldown_hours)

        # Validate critical settings
        if not self.username or not self.password:
            log_error(
                "FRITZBOX_USERNAME and FRITZBOX_PASSWORD must be set in configuration file")
            log_info(
                "Please create a configuration file at one of these locations:")
            for path in config_paths:
                log_info(f"   {path}")
            log_info("Example configuration:")
            log_info("   FRITZBOX_HOST=192.168.1.1")
            log_info("   FRITZBOX_PORT=49000")
            log_info("   FRITZBOX_USERNAME=your_username")
            log_info("   FRITZBOX_PASSWORD=your_password")
            sys.exit(1)

    def check_connectivity(self):
        """Check internet connectivity with enhanced logging"""
        self.check_count += 1
        log_info(f"Check #{self.check_count}")

        # Perform health check periodically
        if self.check_count % 100 == 0:  # Every 100 checks
            self._health_check()
            self._log_statistics()

        try:
            if check_internet():
                self.total_successful_checks += 1
                self.last_success_time = time.time()

                if self.consecutive_failures > 0:
                    log_success(
                        f"Internet restored after {self.consecutive_failures} failed attempts")
                    # Reset restart count on successful internet connection
                    if self.restart_count > 0:
                        log_info("Internet stable - resetting restart counter")
                        self.restart_count = 0
                        self.in_cooldown = False
                else:
                    log_success("Internet working")
                self.consecutive_failures = 0
                return True
            else:
                self.consecutive_failures += 1
                self.total_failed_checks += 1
                self.last_failure_time = time.time()

                log_error(
                    f"Internet failed ({self.consecutive_failures}/{self.max_failures})")

                # Run diagnostics on repeated failures
                if self.consecutive_failures >= self.max_failures:
                    log_info("Running network diagnostics...")
                    diagnostics = network_diagnostics()
                    log_info(
                        f"Diagnostics completed at {diagnostics['timestamp']}")

                return False

        except Exception as e:
            log_error(f"Connectivity check failed with error: {e}")
            self.total_failed_checks += 1
            self.consecutive_failures += 1
            return False

    def _is_in_cooldown(self):
        """Check if we're in cooldown period after 3 restarts"""
        if self.restart_count < self.max_restarts_before_cooldown:
            return False

        # Check if cooldown period has passed
        current_time = time.time()
        cooldown_seconds = self.cooldown_hours * 3600
        time_since_last_restart = current_time - self.last_restart_time

        if time_since_last_restart < cooldown_seconds:
            remaining_hours = (cooldown_seconds -
                               time_since_last_restart) / 3600
            return True, remaining_hours
        else:
            # Cooldown period has passed, reset counters
            self.restart_count = 0
            self.in_cooldown = False
            return False

    def restart_router(self):
        """Restart the FritzBox router with enhanced error handling and cooldown protection"""
        self.total_restarts_attempted += 1

        # Check if we're in cooldown period
        cooldown_result = self._is_in_cooldown()
        if cooldown_result and isinstance(cooldown_result, tuple):
            remaining_hours = cooldown_result[1]
            log_warning(
                f"Restart cooldown active - {self.restart_count} restarts completed")
            log_warning(f"Next restart allowed in {remaining_hours:.1f} hours")
            log_info("Continuing monitoring without restart attempts")
            return False

        self.restart_count += 1
        log_warning(
            f"{self.max_failures} consecutive failures - restarting router...")
        log_info(f"Target: {self.host}:{self.port}")
        log_info(
            f"Restart attempt: {self.restart_count}/{self.max_restarts_before_cooldown}")

        # Show cooldown warning if this is the last allowed restart
        if self.restart_count >= self.max_restarts_before_cooldown:
            log_warning(
                f"This is the final restart attempt before {self.cooldown_hours}h cooldown")

        # Check if router is reachable
        log_info("Checking connection to FritzBox...")
        try:
            if not self.fritz.check_connection():
                log_error(f"Cannot reach FritzBox at {self.host}:{self.port}")
                log_info("Attempting network diagnostics...")
                network_diagnostics()
                return False
        except Exception as e:
            log_error(f"Router connection check failed: {e}")
            return False

        log_info("Connection to router successful!")

        # Restart router
        try:
            success_result = self.fritz.restart_router()
        except Exception as e:
            log_error(f"Router restart command failed: {e}")
            # Don't count failed restart attempts towards the cooldown limit
            self.restart_count -= 1
            self.total_restarts_attempted -= 1
            return False

        if success_result:
            self.successful_restarts += 1
            self.last_restart_time = time.time()
            log_success("Router restart initiated!")

            # Show cooldown activation message if we've reached the limit
            if self.restart_count >= self.max_restarts_before_cooldown:
                self.in_cooldown = True
                log_warning(
                    f"Cooldown activated - no more restarts for {self.cooldown_hours} hours")

            log_info(
                f"Waiting {self.restart_wait // 60} minutes for router to come back online...")

            # Wait with periodic status updates
            wait_start = time.time()
            while time.time() - wait_start < self.restart_wait:
                remaining = self.restart_wait - (time.time() - wait_start)
                if remaining > 60:
                    log_info(
                        f"Restart wait: {remaining/60:.1f} minutes remaining...")
                time.sleep(min(30, remaining))  # Update every 30 seconds

            # Check if internet is back
            log_info("Checking if internet is restored...")
            try:
                if check_internet():
                    log_success("Internet restored successfully!")
                    self.consecutive_failures = 0
                    return True
                else:
                    log_warning("Internet still not working after restart")
                    return False
            except Exception as e:
                log_error(f"Post-restart connectivity check failed: {e}")
                return False
        else:
            log_error("Router restart failed")
            # Don't count failed restart attempts towards the cooldown limit
            self.restart_count -= 1
            return False

    def check_once(self):
        """Perform single connectivity check and restart if needed"""
        log_info("FritzBox Router Watchdog - Single Check")
        log_info(f"Target: {self.host}:{self.port}")

        if self.check_connectivity():
            log_success("Internet is working - no restart needed")
            return True
        else:
            log_error("Internet connection failed - initiating router restart...")
            return self.restart_router()

    def start_monitoring(self):
        """Start continuous monitoring with enhanced error handling"""
        log_info("Starting FritzBox Router Watchdog")
        log_info("Configuration:")
        log_info(f"   Router: {self.host}:{self.port}")
        log_info(f"   Check interval: {self.check_interval // 60} minutes")
        log_info(f"   Max failures: {self.max_failures}")
        log_info(f"   Restart wait: {self.restart_wait // 60} minutes")
        log_info(
            f"   Restart limit: {self.max_restarts_before_cooldown} attempts")
        log_info(f"   Cooldown period: {self.cooldown_hours} hours")
        log_info("Press Ctrl+C to stop")

        try:
            while True:
                cycle_start = time.time()

                try:
                    if self.check_connectivity():
                        next_check_min = self.check_interval // 60
                        log_info(f"Next check in {next_check_min} minutes...")
                    else:
                        if self.consecutive_failures >= self.max_failures:
                            # Check if we can restart or if we're in cooldown
                            cooldown_result = self._is_in_cooldown()
                            if cooldown_result and isinstance(cooldown_result, tuple):
                                remaining_hours = cooldown_result[1]
                                log_warning(
                                    f"Restart needed but in cooldown ({remaining_hours:.1f}h remaining)")
                                log_info(
                                    "Continuing monitoring without restart attempts")
                                next_check_min = self.check_interval // 60
                                log_info(
                                    f"Next check in {next_check_min} minutes...")
                            else:
                                restart_success = False
                                try:
                                    restart_success = self.restart_router()
                                except Exception as e:
                                    log_error(
                                        f"Router restart failed with error: {e}")

                                if restart_success:
                                    next_check_min = self.check_interval // 60
                                    log_info(
                                        f"Next check in {next_check_min} minutes...")
                                else:
                                    log_info("Retrying in 5 minutes...")
                                    # Wait 5 minutes before retry
                                    time.sleep(5 * 60)
                                    continue
                        else:
                            next_check_min = self.check_interval // 60
                            log_info(
                                f"Next check in {next_check_min} minutes...")

                    # Calculate actual sleep time (compensate for processing time)
                    cycle_duration = time.time() - cycle_start
                    sleep_time = max(0, self.check_interval - cycle_duration)

                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    else:
                        log_warning(
                            f"Check cycle took {cycle_duration:.1f}s, longer than interval")

                except Exception as e:
                    log_error(f"Error in monitoring cycle: {e}")
                    log_info("Continuing monitoring after error...")
                    time.sleep(60)  # Wait 1 minute before retrying

        except KeyboardInterrupt:
            log_info("Monitoring stopped by user.")
            self._log_statistics()
        except Exception as e:
            log_error(f"Monitoring failed with error: {e}")
            self._log_statistics()
            raise

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            log_info(f"Received signal {signum}, shutting down gracefully...")
            self._log_statistics()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _log_statistics(self):
        """Log runtime statistics"""
        uptime = time.time() - self.start_time
        uptime_str = str(timedelta(seconds=int(uptime)))

        log_info("=== Watchdog Statistics ===")
        log_info(f"Uptime: {uptime_str}")
        log_info(f"Total checks: {self.check_count}")
        log_info(f"Successful checks: {self.total_successful_checks}")
        log_info(f"Failed checks: {self.total_failed_checks}")
        log_info(f"Restart attempts: {self.total_restarts_attempted}")
        log_info(f"Successful restarts: {self.successful_restarts}")
        if self.check_count > 0:
            success_rate = (self.total_successful_checks /
                            self.check_count) * 100
            log_info(f"Success rate: {success_rate:.1f}%")

    def _health_check(self):
        """Perform internal health check"""
        issues = []

        # Check if we're stuck in cooldown for too long
        if self.in_cooldown:
            cooldown_duration = time.time() - self.last_restart_time
            max_cooldown = self.cooldown_hours * 3600 * 2  # 2x normal cooldown
            if cooldown_duration > max_cooldown:
                issues.append(
                    f"Stuck in cooldown for {cooldown_duration/3600:.1f} hours")

        # Check for excessive failures
        if self.check_count > 10:
            failure_rate = (self.total_failed_checks / self.check_count) * 100
            if failure_rate > 50:
                issues.append(f"High failure rate: {failure_rate:.1f}%")

        # Log health status
        if issues:
            log_warning(f"Health check issues: {', '.join(issues)}")

        return len(issues) == 0

    def get_status(self):
        """Get comprehensive current watchdog status"""
        uptime = time.time() - self.start_time

        status = {
            'version': '1.0.0',
            'pid': os.getpid(),
            'uptime_seconds': int(uptime),
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'check_count': self.check_count,
            'total_successful_checks': self.total_successful_checks,
            'total_failed_checks': self.total_failed_checks,
            'consecutive_failures': self.consecutive_failures,
            'max_failures': self.max_failures,
            'check_interval_minutes': self.check_interval // 60,
            'host': self.host,
            'port': self.port,
            'restart_count': self.restart_count,
            'total_restarts_attempted': self.total_restarts_attempted,
            'successful_restarts': self.successful_restarts,
            'max_restarts_before_cooldown': self.max_restarts_before_cooldown,
            'cooldown_hours': self.cooldown_hours,
            'in_cooldown': self.in_cooldown,
            'last_success_time': self.last_success_time,
            'last_failure_time': self.last_failure_time,
            'last_restart_time': self.last_restart_time
        }

        # Calculate success rate
        if self.check_count > 0:
            status['success_rate'] = (
                self.total_successful_checks / self.check_count) * 100
        else:
            status['success_rate'] = 0.0

        # Add cooldown remaining time if in cooldown
        if self.in_cooldown and self.last_restart_time > 0:
            current_time = time.time()
            cooldown_seconds = self.cooldown_hours * 3600
            time_since_last_restart = current_time - self.last_restart_time
            remaining_seconds = cooldown_seconds - time_since_last_restart
            if remaining_seconds > 0:
                status['cooldown_remaining_hours'] = remaining_seconds / 3600
                status['cooldown_remaining_formatted'] = str(
                    timedelta(seconds=int(remaining_seconds)))
            else:
                status['cooldown_remaining_hours'] = 0
                status['cooldown_remaining_formatted'] = "0:00:00"

        # Add health status
        status['health_status'] = 'healthy' if self._health_check() else 'warning'

        # Add time since last events
        current_time = time.time()
        if self.last_success_time > 0:
            status['time_since_last_success'] = current_time - \
                self.last_success_time
        if self.last_failure_time > 0:
            status['time_since_last_failure'] = current_time - \
                self.last_failure_time

        return status
