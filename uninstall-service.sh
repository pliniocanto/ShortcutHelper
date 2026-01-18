#!/bin/bash
# Script to uninstall ShortcutHelper systemd user service

set -e

SERVICE_NAME="shortcut-helper.service"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🗑️  Uninstalling ShortcutHelper service...${NC}"

# Stop the service if running
if systemctl --user is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Stopping service...${NC}"
    systemctl --user stop "$SERVICE_NAME"
fi

# Disable the service
if systemctl --user is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Disabling service...${NC}"
    systemctl --user disable "$SERVICE_NAME"
fi

# Remove service file
if [ -f "$SYSTEMD_USER_DIR/$SERVICE_NAME" ]; then
    echo -e "${YELLOW}Removing service file...${NC}"
    rm "$SYSTEMD_USER_DIR/$SERVICE_NAME"
fi

# Reload systemd daemon
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl --user daemon-reload

echo -e "${GREEN}✅ ShortcutHelper service uninstalled successfully!${NC}"
