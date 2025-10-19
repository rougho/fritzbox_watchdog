#!/bin/bash
# FritzBox Watchdog Installation Script for Ubuntu

set -e

# Define directories - get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"
INSTALL_DIR="/opt/fritzbox-watchdog"

# Import color codes
source "$SCRIPT_DIR/colors.sh"

echo -e "${BLUE}FritzBox Router Watchdog - Interactive Installation${NC}"
echo "====================================================="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${ERROR} This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

# Function to read input with default value
read_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    echo -n "$prompt [$default]: "
    read input
    if [[ -z "$input" ]]; then
        eval "$var_name=\"$default\""
    else
        eval "$var_name=\"$input\""
    fi
}

# Function to read password
read_password() {
    local prompt="$1"
    local var_name="$2"
    
    echo -n "$prompt: "
    read -s password
    echo ""
    eval "$var_name=\"$password\""
}

# Function to test router connection
test_router_connection() {
    local host="$1"
    local port="$2"
    local username="$3"
    local password="$4"
    
    echo -e "${INFO} Testing router connection..."
    
    # Test basic connectivity first
    if ! ping -c 2 -W 3 "$host" >/dev/null 2>&1; then
        echo -e "${ERROR} Cannot reach router at $host"
        echo -e "${INFO} Please check:"
        echo "  • Router IP address is correct"
        echo "  • Router is powered on and connected"
        echo "  • Network connectivity is working"
        return 1
    fi
    
    # Test TR-064 port
    if ! timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${ERROR} Cannot connect to TR-064 service at $host:$port"
        echo -e "${INFO} Please check:"
        echo "  • TR-064 is enabled in router settings"
        echo "  • Port $port is correct (usually 49000)"
        return 1
    fi
    
    # Create temporary test config
    local temp_config=$(mktemp)
    cat > "$temp_config" << EOF
FRITZBOX_HOST=$host
FRITZBOX_PORT=$port
FRITZBOX_USERNAME=$username
FRITZBOX_PASSWORD=$password
EOF

    # Test actual credentials by trying to get device info
    export FRITZBOX_HOST="$host"
    export FRITZBOX_PORT="$port"
    export FRITZBOX_USERNAME="$username"
    export FRITZBOX_PASSWORD="$password"
    
    if python3 -c "
import sys
import os
sys.path.insert(0, '.')
from watchdog.router import FritzBoxTR064

router = FritzBoxTR064('$host', $port, '$username', '$password')
if router.check_connection():
    if router.get_device_info():
        print('SUCCESS')
        sys.exit(0)
    else:
        print('AUTH_FAILED')
        sys.exit(1)
else:
    print('CONNECTION_FAILED')
    sys.exit(1)
" 2>/dev/null | grep -q "SUCCESS"; then
        rm -f "$temp_config"
        echo -e "${SUCCESS} Router connection and authentication successful!"
        return 0
    else
        rm -f "$temp_config"
        echo -e "${ERROR} Authentication failed"
        echo -e "${INFO} Please check:"
        echo "  • Username and password are correct"
        echo "  • User has admin privileges"
        echo "  • TR-064 access is enabled for this user"
        return 1
    fi
}

# Function to get and validate router credentials
get_router_credentials() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo ""
        if [ $attempt -gt 1 ]; then
            echo -e "${WARNING} Attempt $attempt of $max_attempts"
        fi
        echo -e "${INFO} Please provide your FritzBox configuration:"
        echo ""

        # Get router connection details
        read_with_default "Router IP address" "192.168.1.1" "ROUTER_IP"
        read_with_default "Router port" "49000" "ROUTER_PORT"

        echo ""
        echo -n "Router username: "
        read ROUTER_USER

        if [[ -z "$ROUTER_USER" ]]; then
            echo -e "${ERROR} Username cannot be empty!"
            ((attempt++))
            continue
        fi

        read_password "Router password" "ROUTER_PASS"

        if [[ -z "$ROUTER_PASS" ]]; then
            echo -e "${ERROR} Password cannot be empty!"
            ((attempt++))
            continue
        fi

        # Test the credentials
        if test_router_connection "$ROUTER_IP" "$ROUTER_PORT" "$ROUTER_USER" "$ROUTER_PASS"; then
            return 0
        else
            echo ""
            echo -e "${ERROR} Router connection failed"
            if [ $attempt -lt $max_attempts ]; then
                echo -e "${INFO} Please try again with correct credentials"
            fi
            ((attempt++))
        fi
    done
    
    echo ""
    echo -e "${ERROR} Failed to connect to router after $max_attempts attempts"
    echo "Please verify your router settings and try again"
    exit 1
}

echo -e "${INFO} Please provide your FritzBox configuration:"
echo ""

# Get and validate router credentials first
get_router_credentials

echo ""
echo -e "${INFO} Monitoring configuration (optional):"
read_with_default "Check interval in minutes" "1" "CHECK_INTERVAL"
read_with_default "Max failures before restart" "2" "MAX_FAILURES"
read_with_default "Wait time after restart (minutes)" "3" "RESTART_WAIT"
read_with_default "Max restarts before cooldown" "3" "MAX_RESTARTS"
read_with_default "Cooldown period (hours)" "12" "COOLDOWN_HOURS"

echo ""
echo -e "${CONFIG} Configuration Summary:"
echo "========================"
echo "Router IP: $ROUTER_IP"
echo "Router Port: $ROUTER_PORT"
echo "Username: $ROUTER_USER"
echo "Password: [HIDDEN]"
echo "Check Interval: $CHECK_INTERVAL minutes"
echo "Max Failures: $MAX_FAILURES"
echo "Restart Wait: $RESTART_WAIT minutes"
echo "Max Restarts: $MAX_RESTARTS"
echo "Cooldown Period: $COOLDOWN_HOURS hours"
echo ""

echo -n "Do you want to proceed with installation? (y/N): "
read confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo -e "${START} Starting installation..."

# Update package list
echo -e "${PACKAGE} Updating package list..."
sudo apt update

# Install required packages
echo -e "${PACKAGE} Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-setuptools iputils-ping

# Create installation directory
echo -e "${CYAN}[DIR]${NC} Creating installation directory..."
sudo mkdir -p $INSTALL_DIR

# Copy source files
echo -e "${CYAN}[DIR]${NC} Copying source files..."
sudo cp -r . $INSTALL_DIR/
sudo chown -R root:root $INSTALL_DIR

# Create virtual environment
echo -e "${BLUE}[PYTHON]${NC} Creating virtual environment..."
sudo python3 -m venv $INSTALL_DIR/venv
sudo $INSTALL_DIR/venv/bin/pip install --upgrade pip setuptools

# Install the package in virtual environment
echo -e "${PACKAGE} Installing FritzBox Watchdog..."
# Use regular install instead of editable install to avoid permission issues
sudo $INSTALL_DIR/venv/bin/pip install "$SOURCE_DIR"

# Verify installation
if sudo $INSTALL_DIR/venv/bin/python -c "import watchdog.main" 2>/dev/null; then
    echo -e "${SUCCESS} Package installed successfully"
else
    echo -e "${ERROR} Package installation failed"
    exit 1
fi

# Create system directories
echo -e "${CYAN}[DIR]${NC} Creating system directories..."
sudo mkdir -p /etc/fritzbox-watchdog
sudo mkdir -p /var/log/fritzbox-watchdog

# Create system user
echo -e "${CYAN}[USER]${NC} Creating system user..."
if ! id "fritzbox-watchdog" &>/dev/null; then
    sudo useradd --system --shell /bin/false --home-dir /etc/fritzbox-watchdog fritzbox-watchdog 2>/dev/null || {
        # If user creation fails due to existing group, try with -g flag
        sudo useradd --system --shell /bin/false --home-dir /etc/fritzbox-watchdog -g fritzbox-watchdog fritzbox-watchdog 2>/dev/null || true
    }
    echo -e "${SUCCESS} System user created"
else
    echo -e "${INFO} System user already exists"
fi

# Set proper permissions for log directory
echo -e "${YELLOW}[SECURITY]${NC} Setting log directory permissions..."
sudo chown fritzbox-watchdog:fritzbox-watchdog /var/log/fritzbox-watchdog
sudo chmod 755 /var/log/fritzbox-watchdog

# Copy configuration template
echo -e "${CONFIG} Setting up configuration..."
if [ -f $INSTALL_DIR/.env.template ]; then
    sudo cp $INSTALL_DIR/.env.template /etc/fritzbox-watchdog/.env.template
else
    echo -e "${WARNING} No .env.template found, creating basic template"
    sudo tee /etc/fritzbox-watchdog/.env.template > /dev/null << 'EOF'
# FritzBox Router Configuration
FRITZBOX_HOST=192.168.1.1
FRITZBOX_PORT=49000
FRITZBOX_USERNAME=your_username
FRITZBOX_PASSWORD=your_password

# Monitoring Settings
CHECK_INTERVAL_MINUTES=1
MAX_FAILURES=2
RESTART_WAIT_MINUTES=3

# Cooldown Settings (prevents excessive restarts)
MAX_RESTARTS_BEFORE_COOLDOWN=3
COOLDOWN_HOURS=12
EOF
fi

# Create configuration file with user input
echo -e "${CONFIG} Creating configuration file with your settings..."

# Create both system and local config files
sudo tee /etc/fritzbox-watchdog/.env > /dev/null << EOF
# FritzBox Router Configuration
FRITZBOX_HOST=$ROUTER_IP
FRITZBOX_PORT=$ROUTER_PORT
FRITZBOX_USERNAME=$ROUTER_USER
FRITZBOX_PASSWORD=$ROUTER_PASS

# Monitoring Settings
CHECK_INTERVAL_MINUTES=$CHECK_INTERVAL
MAX_FAILURES=$MAX_FAILURES
RESTART_WAIT_MINUTES=$RESTART_WAIT

# Cooldown Settings
MAX_RESTARTS_BEFORE_COOLDOWN=$MAX_RESTARTS
COOLDOWN_HOURS=$COOLDOWN_HOURS
EOF

# Also create a local config file for easy access
sudo tee $INSTALL_DIR/.env > /dev/null << EOF
# FritzBox Router Configuration
FRITZBOX_HOST=$ROUTER_IP
FRITZBOX_PORT=$ROUTER_PORT
FRITZBOX_USERNAME=$ROUTER_USER
FRITZBOX_PASSWORD=$ROUTER_PASS

# Monitoring Settings
CHECK_INTERVAL_MINUTES=$CHECK_INTERVAL
MAX_FAILURES=$MAX_FAILURES
RESTART_WAIT_MINUTES=$RESTART_WAIT

# Cooldown Settings
MAX_RESTARTS_BEFORE_COOLDOWN=$MAX_RESTARTS
COOLDOWN_HOURS=$COOLDOWN_HOURS
EOF

# Set permissions
echo -e "${YELLOW}[SECURITY]${NC} Setting permissions..."
sudo chown -R fritzbox-watchdog:fritzbox-watchdog /etc/fritzbox-watchdog
sudo chmod 644 /etc/fritzbox-watchdog/.env  # Make readable by all for easier access
sudo chmod 644 /etc/fritzbox-watchdog/.env.template

# Set permissions for local config (accessible by installation user)
sudo chown root:root $INSTALL_DIR/.env
sudo chmod 644 $INSTALL_DIR/.env

# Create wrapper scripts
echo -e "${BLUE} Creating system commands...${NC}"

# Create main command wrapper
sudo tee /usr/local/bin/fritzbox-watchdog > /dev/null << 'EOF'
#!/bin/bash
cd /opt/fritzbox-watchdog
source venv/bin/activate
export PYTHONUNBUFFERED=1
# Run as fritzbox-watchdog user if we're root, otherwise run normally
if [ "$EUID" -eq 0 ]; then
    exec sudo -u fritzbox-watchdog python -u -m watchdog.main "$@"
else
    exec python -u -m watchdog.main "$@"
fi
EOF
sudo chmod +x /usr/local/bin/fritzbox-watchdog

# Create short alias command wrapper
sudo tee /usr/local/bin/fwd > /dev/null << 'EOF'
#!/bin/bash
cd /opt/fritzbox-watchdog
source venv/bin/activate
export PYTHONUNBUFFERED=1
# Run as fritzbox-watchdog user if we're root, otherwise run normally
if [ "$EUID" -eq 0 ]; then
    exec sudo -u fritzbox-watchdog python -u -m watchdog.main "$@"
else
    exec python -u -m watchdog.main "$@"
fi
EOF
sudo chmod +x /usr/local/bin/fwd

# Verify the executables were created
if [ -f /usr/local/bin/fritzbox-watchdog ] && [ -f /usr/local/bin/fwd ]; then
    echo -e "${GREEN} Command executables created successfully${NC}"
    echo -e "${INFO} Available commands: fritzbox-watchdog, fwd${NC}"
else
    echo -e "${RED} Failed to create command executables${NC}"
    exit 1
fi

# Update systemd service to use virtual environment
sudo tee /etc/systemd/system/fritzbox-watchdog.service > /dev/null << 'EOF'
[Unit]
Description=FritzBox Router Watchdog
Documentation=https://github.com/yourusername/fritzbox-watchdog
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=fritzbox-watchdog
Group=fritzbox-watchdog
ExecStart=/opt/fritzbox-watchdog/venv/bin/python -u -m watchdog.main
WorkingDirectory=/etc/fritzbox-watchdog
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Network capabilities for ping
AmbientCapabilities=CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_RAW

# Security settings (relaxed for network access)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/etc/fritzbox-watchdog /var/log/fritzbox-watchdog

[Install]
WantedBy=multi-user.target
EOF

# Install systemd service
echo -e "${PURPLE}[SERVICE]${NC} Installing systemd service..."
sudo systemctl daemon-reload

# Final validation
echo -e "${CYAN}[VALIDATE]${NC} Validating installation..."
if command -v fritzbox-watchdog >/dev/null 2>&1; then
    echo -e "${GREEN} Command 'fritzbox-watchdog' is available${NC}"
else
    echo -e "${RED} Command 'fritzbox-watchdog' not found in PATH${NC}"
    echo -e "${BLUE}[TOOL]${NC} Adding /usr/local/bin to PATH for this session"
    export PATH="/usr/local/bin:$PATH"
fi

# Test help command
if fritzbox-watchdog --help >/dev/null 2>&1; then
    echo -e "${GREEN} Command execution test passed${NC}"
else
    echo -e "${RED} Command execution test failed${NC}"
    echo -e "${YELLOW} Please check the installation manually${NC}"
fi

echo ""
echo -e "${GREEN} Installation completed!${NC}"
echo ""

# Test the installation with user's settings
echo -e "${CYAN} Testing the installation...${NC}"
if fritzbox-watchdog --validate-config; then
    echo ""
    echo -e "${GREEN} Configuration test successful!${NC}"
    echo ""
    
    echo -n "Do you want to start the service now? (Y/n): "
    read start_service
    if [[ ! "$start_service" =~ ^[Nn]$ ]]; then
        echo ""
        echo -e "${BLUE} Starting and enabling the service...${NC}"
        
        # Start and enable the service
        sudo systemctl start fritzbox-watchdog
        sudo systemctl enable fritzbox-watchdog
        
        # Check status
        if sudo systemctl is-active --quiet fritzbox-watchdog; then
            echo -e "${GREEN} Service started successfully!${NC}"
            echo ""
            echo -e "${BLUE}[STATUS]${NC} Service status:"
            sudo systemctl status fritzbox-watchdog --no-pager -l
            echo ""
            echo -e "${CYAN} Useful commands:${NC}"
            echo "  View service logs:  sudo journalctl -u fritzbox-watchdog -f"
            echo "  View log file:      sudo tail -f /var/log/fritzbox-watchdog/watchdog.log"
            echo "  Stop service:       sudo systemctl stop fritzbox-watchdog"
            echo "  Restart service:    sudo systemctl restart fritzbox-watchdog"
            echo "  Test manually:      fritzbox-watchdog --once"
            echo ""
            echo -e "${CYAN} Log file locations:${NC}"
            echo "  Service logs:       /var/log/fritzbox-watchdog/watchdog.log"
            echo "  Manual test logs:   ~/.local/share/fritzbox-watchdog/watchdog.log"
        else
            echo -e "${RED} Service failed to start. Check logs with:${NC}"
            echo "  sudo journalctl -u fritzbox-watchdog -n 20"
        fi
    else
        echo ""
        echo -e "${CYAN} Service not started. You can start it later with:${NC}"
        echo "  sudo systemctl start fritzbox-watchdog"
        echo "  sudo systemctl enable fritzbox-watchdog"
        echo ""
        echo -e "${CYAN} When service runs, logs will be saved to:${NC}"
        echo "  /var/log/fritzbox-watchdog/watchdog.log"
    fi
else
    echo ""
    echo -e "${RED} Test failed. Please check your configuration.${NC}"
    echo "You can edit the configuration with:"
    echo "  nano /opt/fritzbox-watchdog/.env  (easy access)"
    echo "  sudo nano /etc/fritzbox-watchdog/.env  (system config)"
    echo "And test again with:"
    echo "  fritzbox-watchdog --once"
fi
echo ""
echo -e "${GREEN} Setup completed!${NC}"
echo ""
echo -e "${CYAN} Configuration files:${NC}"
echo "  Primary: /opt/fritzbox-watchdog/.env  (easy to edit)"
echo "  System:  /etc/fritzbox-watchdog/.env  (used by service)"
echo -e "${CYAN} Service name:${NC} fritzbox-watchdog"
echo -e "${CYAN} Command:${NC} fritzbox-watchdog"
echo ""
echo -e "${CYAN} Log files:${NC}"
echo "  Service logs:       /var/log/fritzbox-watchdog/watchdog.log"
echo "  Manual test logs:   ~/.local/share/fritzbox-watchdog/watchdog.log"
echo ""
echo -e "${YELLOW}[TIP]${NC} To edit configuration: nano /opt/fritzbox-watchdog/.env"
echo -e "${YELLOW}[TIP]${NC} To view service logs: sudo tail -f /var/log/fritzbox-watchdog/watchdog.log"
