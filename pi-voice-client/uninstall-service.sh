#!/bin/bash
# Uninstallation script for WillAIam Voice Client systemd service

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}WillAIam Voice Client - Service Uninstallation${NC}"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Error: Please run this script without sudo${NC}"
    echo "The script will prompt for sudo password when needed"
    exit 1
fi

# Check if service exists
if [ ! -f /etc/systemd/system/willAIam-voice.service ]; then
    echo -e "${YELLOW}Service not installed${NC}"
    exit 0
fi

echo "Stopping service..."
sudo systemctl stop willAIam-voice.service || true

echo "Disabling service..."
sudo systemctl disable willAIam-voice.service || true

echo "Removing service file..."
sudo rm -f /etc/systemd/system/willAIam-voice.service

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo ""
echo -e "${GREEN}✓ Service uninstalled successfully!${NC}"
echo ""
