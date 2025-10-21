#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Script to set up symbolic link to ~/.env in the project root

set -e  # Exit on error

# Determine project root (directory containing this script's parent)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure ~/.env file exists
if [ ! -f "$HOME/.env" ]; then
    echo "Creating empty ~/.env file..."
    touch "$HOME/.env"
    chmod 600 "$HOME/.env"  # Secure permissions
fi

# Create symbolic link
echo "Creating symbolic link from ~/.env to $PROJECT_ROOT/.env"
ln -sf "$HOME/.env" "$PROJECT_ROOT/.env"

# Verify the link was created
if [ -L "$PROJECT_ROOT/.env" ]; then
    echo "✅ Symbolic link created successfully"
    echo "Now you can edit your environment variables at $PROJECT_ROOT/.env"
    echo "This file will not be tracked by git (it's in .gitignore)"
else
    echo "❌ Failed to create symbolic link"
    exit 1
fi

# Make sure .env is in .gitignore
if ! grep -q "^\.env$" "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
    echo "Adding .env to .gitignore..."
    echo ".env" >> "$PROJECT_ROOT/.gitignore"
fi

echo ""
echo "To add environment variables, edit $PROJECT_ROOT/.env file:"
echo "Example: echo 'ANSIBLE_BECOME_PASSWORD=your_password' >> $PROJECT_ROOT/.env"