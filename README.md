# FritzBox Router Watchdog

Automated network monitoring tool that restarts your FritzBox router when internet connectivity fails. Runs as a system service for 24/7 monitoring.

## Features

- **Automatic internet monitoring** - Tests connectivity every minute using multiple DNS servers
- **Smart restart logic** - Only restarts router after consecutive failures (default: 2 failures)
- **Cooldown protection** - Prevents excessive restarts (default: max 3 restarts, then 12-hour cooldown)
- **Secure operation** - Runs as dedicated system user with minimal privileges
- **Complete logging** - All actions logged to `/var/log/fritzbox-watchdog/`
- **Easy management** - Simple commands for status, testing, and configuration

## Requirements

- **System**: Ubuntu/Debian Linux
- **Python**: 3.6+ (uses only standard library)
- **Router**: AVM FritzBox with TR-064 enabled
- **Permissions**: User with sudo access for installation

## Installation

### 1. Download and Install
```bash
git clone https://github.com/yourusername/fritzbox-watchdog.git
cd fritzbox-watchdog
chmod +x install.sh
./install.sh
```

### 2. Installation Process
The installer will:
1. **Test router credentials** - Validates connection before installation
2. **Install system dependencies** - Python packages and ping utility
3. **Create system user** - `fritzbox-watchdog` user for security
4. **Setup service** - Systemd service for automatic startup
5. **Configure logging** - Log directory with proper permissions

### 3. What Gets Created
```
/opt/fritzbox-watchdog/           # Application files
/etc/fritzbox-watchdog/.env       # Configuration file
/var/log/fritzbox-watchdog/       # Log files
/usr/local/bin/fritzbox-watchdog  # Command-line tool
/usr/local/bin/fwd                # Short alias command
```

## Configuration

### Router Settings (Required)
```bash
# Edit configuration
nano /opt/fritzbox-watchdog/.env
```

```properties
# FritzBox Router Configuration
FRITZBOX_HOST=192.168.1.1
FRITZBOX_PORT=49000
FRITZBOX_USERNAME=your_username
FRITZBOX_PASSWORD=your_password

# Monitoring Settings
CHECK_INTERVAL_MINUTES=1
MAX_FAILURES=2
RESTART_WAIT_MINUTES=3
MAX_RESTARTS_BEFORE_COOLDOWN=3
COOLDOWN_HOURS=12
```

### Enable TR-064 on FritzBox
1. Open FritzBox web interface (`http://192.168.1.1`)
2. Go to **Home Network** → **Network** → **Network Settings**
3. Enable **Allow access for applications** (TR-064 protocol)
4. Create admin user with **Smart Home** permissions

## Usage

### Service Management
```bash
# Start/stop service
sudo systemctl start fritzbox-watchdog
sudo systemctl stop fritzbox-watchdog

# Enable/disable auto-start
sudo systemctl enable fritzbox-watchdog
sudo systemctl disable fritzbox-watchdog

# Check service status
sudo systemctl status fritzbox-watchdog
```

### Command Line Tools

Both `fritzbox-watchdog` and `fwd` commands work identically - use whichever you prefer:

```bash
# Test configuration
fritzbox-watchdog --validate-config
# or shorter:
fwd --validate-config

# Run single check (no restart)
fwd --once

# Check current status
fwd --status

# Show version
fwd --version

# Show help
fwd --help
```

### Monitoring Logs
```bash
# View service logs
sudo journalctl -u fritzbox-watchdog -f

# View log file
sudo tail -f /var/log/fritzbox-watchdog/watchdog.log

# Check recent activity
sudo journalctl -u fritzbox-watchdog --since "1 hour ago"
```

## How It Works

1. **Internet Test**: Pings 4 DNS servers (Google, Cloudflare, OpenDNS) every minute
2. **Failure Detection**: If 3+ servers fail, counts as connectivity failure
3. **Router Restart**: After MAX_FAILURES consecutive failures, restarts router via TR-064
4. **Cooldown Protection**: After MAX_RESTARTS, enters cooldown period to protect equipment
5. **Recovery**: Continues monitoring during cooldown, resumes restarts when connectivity returns

## Troubleshooting

### Common Issues

**Service fails to start:**
```bash
# Check logs for errors
sudo journalctl -u fritzbox-watchdog -n 20

# Test configuration manually
fritzbox-watchdog --validate-config
```

**Router connection fails:**
- Verify TR-064 is enabled in FritzBox
- Check username/password are correct
- Ensure user has admin privileges
- Test router web interface access

**Permission denied errors:**
```bash
# Fix log directory permissions
sudo chown -R fritzbox-watchdog:fritzbox-watchdog /var/log/fritzbox-watchdog
```

### Testing
```bash
# Test without making changes
fritzbox-watchdog --once --dry-run

# Validate router connection
fritzbox-watchdog --test-connection

# Check if in cooldown
fritzbox-watchdog --status
```

## Uninstallation

```bash
# Run uninstall script
./uninstall.sh

# Or manual removal:
sudo systemctl stop fritzbox-watchdog
sudo systemctl disable fritzbox-watchdog
sudo rm -rf /opt/fritzbox-watchdog
sudo rm -rf /etc/fritzbox-watchdog
sudo rm -rf /var/log/fritzbox-watchdog
sudo rm /etc/systemd/system/fritzbox-watchdog.service
sudo rm /usr/local/bin/fritzbox-watchdog /usr/local/bin/fwd
sudo userdel fritzbox-watchdog
sudo systemctl daemon-reload
```

## Security

- **Dedicated user**: Runs as `fritzbox-watchdog` system user
- **Minimal permissions**: Only network access and log writing
- **Secure storage**: Credentials in protected environment file
- **No external dependencies**: Uses only Python standard library

## License

MIT License - see LICENSE file for details.
