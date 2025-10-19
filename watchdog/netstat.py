#!/usr/bin/env python3
"""
Production Network Monitoring Module
Robust functions for checking internet connectivity with error handling
"""

import subprocess
import time
import os
from datetime import datetime
from .libs.colors import Colors
from .libs.logger import log_info, log_error, log_warning


def ping_test(host="8.8.8.8", count=3, timeout=10):
    """
    Ping a host and return True if successful

    Args:
        host: Host to ping
        count: Number of ping packets
        timeout: Timeout in seconds

    Returns:
        bool: True if ping successful, False otherwise
    """
    try:
        # Use timeout parameter for both ping timeout and subprocess timeout
        ping_timeout = min(timeout, 30)  # Cap at 30 seconds for safety

        result = subprocess.run(
            ['ping', '-c', str(count), '-W', str(ping_timeout), host],
            capture_output=True,
            timeout=timeout + 5,  # Add 5 seconds buffer for subprocess
            text=True
        )

        # Log detailed results in debug mode
        if result.returncode != 0 and result.stderr:
            log_error(f"Ping to {host} failed: {result.stderr.strip()}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        log_warning(f"Ping to {host} timed out after {timeout}s")
        return False
    except FileNotFoundError:
        log_error("ping command not found - please install iputils-ping")
        return False
    except Exception as e:
        log_error(f"Ping test failed for {host}: {e}")
        return False


def check_internet(timeout=10):
    """
    Check internet connectivity by pinging multiple reliable hosts

    Args:
        timeout: Timeout for each ping test

    Returns:
        bool: True if internet is available, False otherwise
    """
    # Use geographically distributed, highly reliable DNS servers
    hosts = [
        "8.8.8.8",      # Google DNS (Primary)
        "1.1.1.1",      # Cloudflare DNS
        "8.8.4.4",      # Google DNS (Secondary)
        "208.67.222.222"  # OpenDNS
    ]

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_info(f"[{timestamp}] Testing internet connectivity...")

    working = 0
    total_hosts = len(hosts)

    # Get ping configuration from environment
    ping_count = int(os.environ.get('PING_COUNT', '3'))
    ping_timeout = int(os.environ.get('PING_TIMEOUT', str(timeout)))

    for host in hosts:
        try:
            if ping_test(host, count=ping_count, timeout=ping_timeout):
                working += 1
                log_info(f"  {Colors.GREEN}✓{Colors.NC} {host} - OK")
            else:
                log_info(f"  {Colors.RED}✗{Colors.NC} {host} - Failed")
        except Exception as e:
            log_error(f"  {Colors.RED}✗{Colors.NC} {host} - Error: {e}")

    # Require majority of hosts to be working (more robust than 2/3)
    required_working = (total_hosts // 2) + 1  # Majority
    connected = working >= required_working

    if connected:
        status = f"  {Colors.GREEN}[CONNECTED]{Colors.NC} ({working}/{total_hosts} hosts reachable)"
    else:
        status = f"  {Colors.RED}[DISCONNECTED]{Colors.NC} ({working}/{total_hosts} hosts reachable)"
        log_warning(
            f"Only {working}/{total_hosts} hosts reachable, need at least {required_working}")

    log_info(status)
    return connected


def network_diagnostics():
    """
    Run comprehensive network diagnostics for troubleshooting

    Returns:
        dict: Dictionary with diagnostic results
    """
    log_info("Running network diagnostics...")

    results = {
        'timestamp': datetime.now().isoformat(),
        'local_connectivity': False,
        'dns_resolution': False,
        'internet_connectivity': False,
        'gateway_reachable': False
    }

    # Test local connectivity (ping localhost)
    try:
        if ping_test('127.0.0.1', count=2, timeout=5):
            results['local_connectivity'] = True
            log_info("✅ Local connectivity: OK")
        else:
            log_error("❌ Local connectivity: Failed")
    except Exception as e:
        log_error(f"❌ Local connectivity test error: {e}")

    # Test gateway connectivity
    try:
        # Try to get default gateway
        result = subprocess.run(['ip', 'route', 'show', 'default'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'via' in line:
                    gateway = line.split('via')[1].split()[0]
                    if ping_test(gateway, count=2, timeout=5):
                        results['gateway_reachable'] = True
                        log_info(f"✅ Gateway {gateway}: OK")
                        break
                    else:
                        log_error(f"❌ Gateway {gateway}: Not reachable")
    except Exception as e:
        log_warning(f"Gateway test failed: {e}")

    # Test DNS resolution
    try:
        result = subprocess.run(['nslookup', 'google.com', '8.8.8.8'],
                                capture_output=True, timeout=10)
        if result.returncode == 0:
            results['dns_resolution'] = True
            log_info("✅ DNS resolution: OK")
        else:
            log_error("❌ DNS resolution: Failed")
    except Exception as e:
        log_warning(f"DNS test failed: {e}")

    # Test internet connectivity
    results['internet_connectivity'] = check_internet()

    return results
