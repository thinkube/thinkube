#!/bin/sh

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# install-tools.sh - Install Ansible and configure shell environments

set -e  # Exit on error

echo "Installing Ansible and configuring shell environments..."
echo "[INSTALLER_STATUS] PROGRESS:0"
echo "[INSTALLER_STATUS] Starting thinkube tools installation"

# Check if SUDO_ASKPASS is set and use it
if [ -n "$SUDO_ASKPASS" ]; then
    export SUDO_FLAGS="-A"
else
    export SUDO_FLAGS=""
fi

# Install dependencies
echo "[INSTALLER_STATUS] PROGRESS:10"
echo "[INSTALLER_STATUS] Updating package lists..."
sudo $SUDO_FLAGS apt-get update || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to update package lists"; exit 1; }

echo "[INSTALLER_STATUS] PROGRESS:20"
echo "[INSTALLER_STATUS] Installing Python and system dependencies..."
sudo $SUDO_FLAGS apt-get install -y python3-venv python3-full curl gnupg apt-transport-https ca-certificates software-properties-common git sshpass expect nmap || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to install dependencies"; exit 1; }

# Fix ping permissions (common issue on Ubuntu 24.04, especially on Raspberry Pi)
echo "[INSTALLER_STATUS] PROGRESS:25"
echo "[INSTALLER_STATUS] Fixing ping permissions..."
sudo $SUDO_FLAGS setcap cap_net_raw+ep /usr/bin/ping 2>/dev/null || echo "Note: Could not set ping capabilities (may already be set)"

# Install micro editor
echo "[INSTALLER_STATUS] PROGRESS:30"
echo "[INSTALLER_STATUS] Installing micro editor..."
if ! command -v micro >/dev/null 2>&1; then
    echo "Installing micro editor..."
    sudo $SUDO_FLAGS apt-get install -y micro || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to install micro editor"; exit 1; }
    echo "micro editor installed successfully"
else
    echo "micro editor is already installed"
fi

# Set environment variables for editors
EDITOR_MARKER="# Editor configuration"

# Install Zsh if not already installed
echo "[INSTALLER_STATUS] PROGRESS:40"
echo "[INSTALLER_STATUS] Installing shell environments..."
if ! command -v zsh >/dev/null 2>&1; then
    echo "Installing Zsh..."
    sudo $SUDO_FLAGS apt-get install -y zsh || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to install Zsh"; exit 1; }
fi

# Install Fish if not already installed
echo "[INSTALLER_STATUS] PROGRESS:50"
if ! command -v fish >/dev/null 2>&1; then
    echo "Installing Fish..."
    sudo $SUDO_FLAGS apt-get install -y fish || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to install Fish"; exit 1; }
fi

# Set up Python virtual environment
VENV_DIR="$HOME/.venv"
echo "[INSTALLER_STATUS] PROGRESS:60"
echo "[INSTALLER_STATUS] Creating Python virtual environment..."
echo "Creating Python virtual environment at $VENV_DIR..."

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR" || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to create virtual environment"; exit 1; }
fi

# Activate the environment for the current session
. "$VENV_DIR/bin/activate" || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to activate virtual environment"; exit 1; }

# Install Ansible in the virtual environment
echo "[INSTALLER_STATUS] PROGRESS:70"
echo "[INSTALLER_STATUS] Upgrading pip..."
echo "Installing Ansible in the virtual environment..."
pip install --upgrade pip || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to upgrade pip"; exit 1; }

echo "[INSTALLER_STATUS] PROGRESS:80"
echo "[INSTALLER_STATUS] Installing Ansible..."
pip install ansible ansible-lint || { echo "[INSTALLER_STATUS] COMPLETED:FAILED"; echo "[INSTALLER_STATUS] Failed to install Ansible"; exit 1; }

# Create a unique marker that includes the venv path to check for existing configuration
VENV_MARKER="# Ansible venv auto-activation for: ${VENV_DIR}"
ENV_MARKER="# .env auto-loading configuration"

echo "[INSTALLER_STATUS] PROGRESS:90"
echo "[INSTALLER_STATUS] Configuring shell environments..."

# Set up automatic activation in Bash and .env loading
if [ -f "$HOME/.bashrc" ]; then
    echo "Setting up configuration in .bashrc..."
    
    # Check for and add venv activation if not present
    if ! grep -q "${VENV_MARKER}" "$HOME/.bashrc"; then
        cat >> "$HOME/.bashrc" << EOF

${VENV_MARKER}
if [ -f "${VENV_DIR}/bin/activate" ]; then
    . "${VENV_DIR}/bin/activate"
fi
EOF
    fi
    
    # Check for and add .env loading if not present
    if ! grep -q "${ENV_MARKER}" "$HOME/.bashrc"; then
        cat >> "$HOME/.bashrc" << EOF

${ENV_MARKER}
if [ -f "$HOME/.env" ]; then
    set -a
    . "$HOME/.env"
    set +a
    
    # Export all variables for Ansible
    for var in \$(grep -v '^#' "$HOME/.env" | cut -d= -f1); do
        export "\$var"
    done
fi
EOF
    fi
    
    # Add editor configuration if not present
    if ! grep -q "${EDITOR_MARKER}" "$HOME/.bashrc"; then
        cat >> "$HOME/.bashrc" << EOF

${EDITOR_MARKER}
export EDITOR=micro
export VISUAL=code
EOF
    fi
fi

# Set up automatic activation in Zsh and .env loading
if [ -f "$HOME/.zshrc" ]; then
    echo "Setting up configuration in .zshrc..."
    
    # Check for and add venv activation if not present
    if ! grep -q "${VENV_MARKER}" "$HOME/.zshrc"; then
        cat >> "$HOME/.zshrc" << EOF

${VENV_MARKER}
if [ -f "${VENV_DIR}/bin/activate" ]; then
    . "${VENV_DIR}/bin/activate"
fi
EOF
    fi
    
    # Check for and add .env loading if not present
    if ! grep -q "${ENV_MARKER}" "$HOME/.zshrc"; then
        cat >> "$HOME/.zshrc" << EOF

${ENV_MARKER}
if [ -f "$HOME/.env" ]; then
    set -a
    . "$HOME/.env"
    set +a
    
    # Export all variables for Ansible
    for var in \$(grep -v '^#' "$HOME/.env" | cut -d= -f1); do
        export "\$var"
    done
fi
EOF
    fi
    
    # Add editor configuration if not present
    if ! grep -q "${EDITOR_MARKER}" "$HOME/.zshrc"; then
        cat >> "$HOME/.zshrc" << EOF

${EDITOR_MARKER}
export EDITOR=micro
export VISUAL=code
EOF
    fi
else
    # Create .zshrc if it doesn't exist
    echo "Creating .zshrc with configuration..."
    cat > "$HOME/.zshrc" << EOF
${VENV_MARKER}
if [ -f "${VENV_DIR}/bin/activate" ]; then
    . "${VENV_DIR}/bin/activate"
fi

${ENV_MARKER}
if [ -f "$HOME/.env" ]; then
    set -a
    . "$HOME/.env"
    set +a
    
    # Export all variables for Ansible
    for var in \$(grep -v '^#' "$HOME/.env" | cut -d= -f1); do
        export "\$var"
    done
fi

${EDITOR_MARKER}
export EDITOR=micro
export VISUAL=code
EOF
fi

# Set up automatic activation in Fish shell and .env loading
FISH_CONFIG_DIR="$HOME/.config/fish"
FISH_CONFIG_FILE="$FISH_CONFIG_DIR/config.fish"

# Create fish config directory if it doesn't exist
mkdir -p "$FISH_CONFIG_DIR"

# Create config.fish if it doesn't exist
touch "$FISH_CONFIG_FILE"

echo "Setting up configuration in Fish shell..."

# Check for and add venv activation if not present
if ! grep -q "${VENV_MARKER}" "$FISH_CONFIG_FILE"; then
    cat >> "$FISH_CONFIG_FILE" << EOF

# ${VENV_MARKER}
if test -f "${VENV_DIR}/bin/activate.fish"
    source "${VENV_DIR}/bin/activate.fish"
end
EOF
fi

# Check for and add .env loading if not present
if ! grep -q "${ENV_MARKER}" "$FISH_CONFIG_FILE"; then
    cat >> "$FISH_CONFIG_FILE" << EOF

# ${ENV_MARKER}
if test -f "$HOME/.env"
    # Parse .env file and set variables
    for line in (grep -v '^#' "$HOME/.env")
        set item (string split -m 1 '=' \$line)
        if test -n "\$item[1]" -a -n "\$item[2]"
            set -gx \$item[1] \$item[2]
            
            # Set variables for Ansible use
            set -gx \$item[1] \$item[2]
        end
    end
end
EOF
fi

# Check for and add editor configuration if not present
if ! grep -q "${EDITOR_MARKER}" "$FISH_CONFIG_FILE"; then
    cat >> "$FISH_CONFIG_FILE" << EOF

# ${EDITOR_MARKER}
set -gx EDITOR micro
set -gx VISUAL code
EOF
fi

# Verify Ansible installation
echo "Verifying Ansible installation..."
ansible --version | head -n1

# Install Ansible Galaxy collections and roles
echo "Installing Ansible Galaxy collections..."
ansible-galaxy collection install community.general
ansible-galaxy collection install ansible.posix
ansible-galaxy collection install community.docker

echo "Ansible Galaxy collections installed successfully."

# Activate the environment for immediate use
. "$VENV_DIR/bin/activate"

# Create a sample .env file if it doesn't exist
if [ ! -f "$HOME/.env" ]; then
    echo "Creating a sample .env file at $HOME/.env..."
    cat > "$HOME/.env" << EOF
# Thinkube Environment Variables
# Add your environment variables below in KEY=value format (no quotes)

# Network Configuration
DOMAIN_NAME=thinkube.com
NETWORK_CIDR=192.0.2.0/24
ZEROTIER_NETWORK_ID=your_zerotier_network_id

# Authentication
ANSIBLE_BECOME_PASSWORD=your_sudo_password
# GITHUB_TOKEN=your_github_token  # Uncomment and set if needed

# Server Configuration
BCN1_IP=192.0.2.101  # Desktop
BCN2_IP=192.0.2.102  # Headless Server
EOF
    chmod 600 "$HOME/.env"
    echo "Created $HOME/.env with sample content and secure permissions (600)"
fi

# Summary of installed shells
SHELLS_CONFIGURED=""
if [ -f "$HOME/.bashrc" ]; then SHELLS_CONFIGURED="${SHELLS_CONFIGURED} Bash"; fi
if [ -f "$HOME/.zshrc" ]; then SHELLS_CONFIGURED="${SHELLS_CONFIGURED} Zsh"; fi
if command -v fish >/dev/null 2>&1; then SHELLS_CONFIGURED="${SHELLS_CONFIGURED} Fish"; fi

echo "============================================================"
echo "Tools installation completed successfully!"
echo "============================================================"
echo "Ansible is installed in: $VENV_DIR"
echo "Virtual environment auto-activation configured for:${SHELLS_CONFIGURED}"
echo ""
echo ".env auto-loading configured for all shells - file location: $HOME/.env"
echo "For this session, the virtual environment is already activated."
echo "Use 'ansible --version' to verify Ansible."
echo ""
echo "IMPORTANT: You'll need to restart your shell sessions or source"
echo "your shell configuration files for the changes to take effect."
echo "============================================================"

# Add clear completion markers for the installer
echo "[INSTALLER_STATUS] PROGRESS:100"
echo "[INSTALLER_STATUS] COMPLETED:SUCCESS"
echo "[INSTALLER_STATUS] Thinkube tools installation finished successfully"

# Exit with success code
exit 0