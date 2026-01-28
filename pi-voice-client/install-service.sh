#!/bin/bash
# Installation script for WillAIam Voice Client systemd service
# This script sets up the application to run automatically on boot

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}WillAIam Voice Client - Service Installation${NC}"
echo "=============================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo -e "${RED}Error: This script must be run on a Raspberry Pi${NC}"
    exit 1
fi

# Check if running as root (we need sudo for systemd)
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}Error: Please run this script without sudo${NC}"
    echo "The script will prompt for sudo password when needed"
    exit 1
fi

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "Project directory: ${YELLOW}$PROJECT_DIR${NC}"
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file before installing the service"
    echo "Run: cp .env.example .env && nano .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Please create virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Detect current user
CURRENT_USER="$USER"
echo -e "Installing service for user: ${YELLOW}$CURRENT_USER${NC}"
echo ""

# Create temporary service file with correct paths
SERVICE_FILE="/tmp/willAIam-voice.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=WillAIam Voice Client
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Load environment variables from .env file
EnvironmentFile=$PROJECT_DIR/.env

# Run the application
ExecStart=$PROJECT_DIR/venv/bin/python -m src.main

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=willAIam-voice

# Security settings
NoNewPrivileges=false
PrivateTmp=true

# Allow access to GPIO
SupplementaryGroups=gpio

[Install]
WantedBy=multi-user.target
EOF

echo "Installing systemd service..."
echo ""

# Copy service file to systemd directory
sudo cp "$SERVICE_FILE" /etc/systemd/system/willAIam-voice.service
sudo chmod 644 /etc/systemd/system/willAIam-voice.service

# Add user to gpio group (if not already added)
if ! groups "$CURRENT_USER" | grep -q "\bgpio\b"; then
    echo "Adding user to gpio group..."
    sudo usermod -a -G gpio "$CURRENT_USER"
    echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"
    echo ""
fi

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service (start on boot)
echo "Enabling service to start on boot..."
sudo systemctl enable willAIam-voice.service

echo ""
echo -e "${GREEN}✓ Service installed successfully!${NC}"
echo ""
echo "Available commands:"
echo "  Start service:   ${YELLOW}sudo systemctl start willAIam-voice${NC}"
echo "  Stop service:    ${YELLOW}sudo systemctl stop willAIam-voice${NC}"
echo "  Restart service: ${YELLOW}sudo systemctl restart willAIam-voice${NC}"
echo "  View status:     ${YELLOW}sudo systemctl status willAIam-voice${NC}"
echo "  View logs:       ${YELLOW}journalctl -u willAIam-voice -f${NC}"
echo "  Disable startup: ${YELLOW}sudo systemctl disable willAIam-voice${NC}"
echo ""
echo -e "${YELLOW}To start the service now, run:${NC}"
echo -e "  ${YELLOW}sudo systemctl start willAIam-voice${NC}"
echo ""
