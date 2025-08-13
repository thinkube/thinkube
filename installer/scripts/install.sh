#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# thinkube Installer Script
# This script downloads and launches the thinkube installer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    log_error "This installer only supports Ubuntu Linux"
    exit 1
fi

# Detect architecture
ARCH=$(dpkg --print-architecture)
case $ARCH in
    amd64|arm64)
        log_info "Detected architecture: $ARCH"
        ;;
    *)
        log_error "Unsupported architecture: $ARCH"
        log_error "Only amd64 and arm64 are supported"
        exit 1
        ;;
esac

# Check for required commands
for cmd in wget dpkg apt-get; do
    if ! command -v $cmd &> /dev/null; then
        log_error "$cmd is required but not installed"
        exit 1
    fi
done

# GitHub release URL
GITHUB_REPO="thinkube/thinkube"
RELEASE_URL="https://github.com/${GITHUB_REPO}/releases/latest/download"
DEB_FILE="thinkube-installer_${ARCH}.deb"
DOWNLOAD_URL="${RELEASE_URL}/${DEB_FILE}"

# Create temporary directory
TMP_DIR=$(mktemp -d -t thinkube-installer-XXXXXXXXXX)
cd "$TMP_DIR"

log_info "Downloading thinkube installer..."
if ! wget -q --show-progress "$DOWNLOAD_URL" -O "$DEB_FILE"; then
    log_error "Failed to download installer from $DOWNLOAD_URL"
    log_error "Please check your internet connection and try again"
    rm -rf "$TMP_DIR"
    exit 1
fi

log_info "Installing thinkube installer..."
if ! sudo dpkg -i "$DEB_FILE" 2>/dev/null; then
    log_warning "Fixing missing dependencies..."
    sudo apt-get install -f -y
fi

# Clean up download
rm -rf "$TMP_DIR"

log_info "Launching thinkube installer..."

# Check if running in a graphical environment
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    log_error "No graphical display detected"
    log_error "The thinkube installer requires a graphical environment"
    log_error "Please run this from a desktop Ubuntu installation"
    exit 1
fi

# Launch the installer
if command -v thinkube-installer &> /dev/null; then
    thinkube-installer
    
    # Offer to uninstall after completion
    echo
    read -p "Would you like to remove the installer? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing thinkube installer..."
        sudo apt-get remove -y thinkube-installer
        sudo apt-get autoremove -y
    fi
else
    log_error "Failed to launch thinkube installer"
    log_error "The package may not have installed correctly"
    exit 1
fi

log_info "Installation complete!"