#!/usr/bin/env python3
"""
Simple Test Suite for FritzBox Watchdog
Run with: python3 tests/tests.py
"""

from watchdog.watchdog import FritzBoxWatchdog
from watchdog.router import FritzBoxTR064
from watchdog.netstat import ping_test, check_internet
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBasicFunctionality(unittest.TestCase):
    """Essential tests for core functionality"""

    def test_router_init(self):
        """Test router can be initialized"""
        router = FritzBoxTR064("192.168.1.1", 49000, "admin", "pass")
        self.assertEqual(router.host, "192.168.1.1")
        self.assertEqual(router.port, 49000)

    @patch('socket.socket')
    def test_connection_check(self, mock_socket):
        """Test connection checking works"""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        mock_sock.connect_ex.return_value = 0

        router = FritzBoxTR064()
        result = router.check_connection()
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_ping_works(self, mock_run):
        """Test ping functionality"""
        mock_run.return_value = MagicMock(returncode=0)
        result = ping_test("8.8.8.8")
        self.assertTrue(result)

    @patch('watchdog.netstat.ping_test')
    def test_internet_check_works(self, mock_ping):
        """Test internet check logic"""
        # Mock 3 out of 4 hosts working (majority = success)
        # 3/4 success = connected
        mock_ping.side_effect = [True, True, True, False]
        result = check_internet()
        self.assertTrue(result)


if __name__ == '__main__':
    print("FritzBox Watchdog - Tests")
    print("=" * 25)

    # Run tests
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 25)
    print("✅ Tests completed!")
