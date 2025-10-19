#!/bin/bash
# FritzBox Watchdog - Professional Uninstall Script

set -e

# Import color codes
source "$(dirname "$0")/colors.sh"

echo -e "${BLUE}FritzBox Router Watchdog - Uninstall${NC}"
echo "====================================="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${ERROR} This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

echo -e "${WARNING} This will completely remove FritzBox Watchdog from your system."
echo ""
echo "The following will be removed:"
echo "  • Service and systemd configuration"
echo "  • Installation directory (/opt/fritzbox-watchdog)"
echo "  • System configuration (/etc/fritzbox-watchdog)"
echo "  • Log files (/var/log/fritzbox-watchdog)"
echo "  • System user and group"
echo "  • Command executables (/usr/local/bin/fritzbox-watchdog, /usr/local/bin/fwd)"
echo ""

echo -n "Are you sure you want to proceed? (y/N): "
read confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo -e "${START} Starting uninstall process..."

# Stop and disable service
echo -e "${PURPLE}[SERVICE]${NC} Stopping and disabling service..."
if systemctl is-active --quiet fritzbox-watchdog 2>/dev/null; then
    sudo systemctl stop fritzbox-watchdog
    echo -e "${SUCCESS} Service stopped"
else
    echo -e "${INFO} Service was not running"
fi

if systemctl is-enabled --quiet fritzbox-watchdog 2>/dev/null; then
    sudo systemctl disable fritzbox-watchdog
    echo -e "${SUCCESS} Service disabled"
else
    echo -e "${INFO} Service was not enabled"
fi

# Remove systemd service file
echo -e "${PURPLE}[SERVICE]${NC} Removing systemd service file..."
if [ -f /etc/systemd/system/fritzbox-watchdog.service ]; then
    sudo rm -f /etc/systemd/system/fritzbox-watchdog.service
    sudo systemctl daemon-reload
    echo -e "${SUCCESS} Service file removed"
else
    echo -e "${INFO} Service file not found"
fi

# Remove command executables
echo -e "${BLUE}[COMMAND]${NC} Removing command executables..."
sudo rm -f /usr/local/bin/fritzbox-watchdog /usr/local/bin/fwd
echo -e "${SUCCESS} Command executables removed (fritzbox-watchdog, fwd)"

# Remove installation directory
echo -e "${CYAN}[DIR]${NC} Removing installation directory..."
if [ -d /opt/fritzbox-watchdog ]; then
    sudo rm -rf /opt/fritzbox-watchdog
    echo -e "${SUCCESS} Installation directory removed"
else
    echo -e "${INFO} Installation directory not found"
fi

# Remove system configuration (ask user)
if [ -d /etc/fritzbox-watchdog ]; then
    echo ""
    echo -n "Remove system configuration directory (/etc/fritzbox-watchdog)? This contains your settings. (y/N): "
    read remove_config
    if [[ "$remove_config" =~ ^[Yy]$ ]]; then
        sudo rm -rf /etc/fritzbox-watchdog
        echo -e "${SUCCESS} System configuration removed"
    else
        echo -e "${INFO} System configuration preserved"
    fi
else
    echo -e "${INFO} System configuration directory not found"
fi

# Remove log directory (ask user)
if [ -d /var/log/fritzbox-watchdog ]; then
    echo ""
    echo -n "Remove log directory (/var/log/fritzbox-watchdog)? This contains historical logs. (y/N): "
    read remove_logs
    if [[ "$remove_logs" =~ ^[Yy]$ ]]; then
        sudo rm -rf /var/log/fritzbox-watchdog
        echo -e "${SUCCESS} Log directory removed"
    else
        echo -e "${INFO} Log directory preserved"
    fi
else
    echo -e "${INFO} Log directory not found"
fi

# Remove system user
echo -e "${CYAN}[USER]${NC} Removing system user..."
if id "fritzbox-watchdog" &>/dev/null; then
    sudo userdel fritzbox-watchdog 2>/dev/null || true
    echo -e "${SUCCESS} System user removed"
else
    echo -e "${INFO} System user not found"
fi

# Remove system group if it exists and is empty
if getent group fritzbox-watchdog &>/dev/null; then
    sudo groupdel fritzbox-watchdog 2>/dev/null || true
    echo -e "${SUCCESS} System group removed"
else
    echo -e "${INFO} System group not found"
fi

# Clean up user-specific log files
echo -e "${CYAN}[CLEANUP]${NC} Cleaning user-specific files..."
if [ -d "$HOME/.local/share/fritzbox-watchdog" ]; then
    echo -n "Remove user log directory ($HOME/.local/share/fritzbox-watchdog)? (y/N): "
    read remove_user_logs
    if [[ "$remove_user_logs" =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.local/share/fritzbox-watchdog"
        echo -e "${SUCCESS} User log directory removed"
    else
        echo -e "${INFO} User log directory preserved"
    fi
fi

echo ""
echo -e "${GREEN} Uninstall completed successfully!${NC}"
echo ""

# Final status check
echo -e "${CYAN} Final status check:${NC}"
if command -v fritzbox-watchdog >/dev/null 2>&1; then
    echo -e "${WARNING} Command 'fritzbox-watchdog' still found in PATH"
else
    echo -e "${SUCCESS} Command 'fritzbox-watchdog' removed from PATH"
fi

if systemctl list-unit-files | grep -q fritzbox-watchdog; then
    echo -e "${WARNING} Service file still present"
else
    echo -e "${SUCCESS} Service file removed"
fi

if [ -d /opt/fritzbox-watchdog ]; then
    echo -e "${WARNING} Installation directory still exists"
else
    echo -e "${SUCCESS} Installation directory removed"
fi

echo ""
echo -e "${INFO} If you preserved configuration or log files, they can be manually removed later."
echo -e "${INFO} Thank you for using FritzBox Watchdog!"