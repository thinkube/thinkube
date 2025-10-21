#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Smart SSH command runner that detects local vs remote network
# Usage: ./scripts/run_ssh_command.sh <host> <command>

set -e  # Exit on error

# Check for required arguments
if [ $# -lt 2 ]; then
  echo "ERROR: Missing required arguments"
  echo "Usage: $0 <host> <command>"
  echo "Example: $0 vilanova1 'microk8s.kubectl get pods'"
  exit 1
fi

HOST="$1"
shift
COMMAND="$@"  # All remaining arguments

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THINKUBE_DIR="$(dirname "$SCRIPT_DIR")"

# Source network detection
source "${SCRIPT_DIR}/network_detect.sh"

# Source environment variables
if [ -f "$HOME/.env" ]; then
  echo "Loading environment variables from $HOME/.env"
  source "$HOME/.env"
else
  echo "ERROR: $HOME/.env file not found!"
  exit 1
fi

# Check for required environment variables
if [ -z "$ANSIBLE_BECOME_PASSWORD" ]; then
  echo "ERROR: ANSIBLE_BECOME_PASSWORD environment variable not set!"
  exit 1
fi

# Get the system username from inventory
SYSTEM_USERNAME=$(cd "${THINKUBE_DIR}" && python3 -c "import yaml; inv=yaml.safe_load(open('inventory/inventory.yaml')); print(inv['all']['vars']['system_username'])" 2>/dev/null)
if [ -z "$SYSTEM_USERNAME" ]; then
  echo "ERROR: Could not determine system_username from inventory!"
  exit 1
fi

# If ANSIBLE_SSH_PASS is not set, use ANSIBLE_BECOME_PASSWORD
if [ -z "$ANSIBLE_SSH_PASS" ]; then
  echo "ANSIBLE_SSH_PASS not set, using ANSIBLE_BECOME_PASSWORD for SSH authentication"
  export ANSIBLE_SSH_PASS="$ANSIBLE_BECOME_PASSWORD"
fi

# Install sshpass if needed
if ! command -v sshpass &> /dev/null; then
  echo "Installing sshpass..."
  sudo apt-get update -qq && sudo apt-get install -qq -y sshpass
fi

# Determine target IP based on network
if is_local_network; then
  echo "Detected local network - using direct connection"
  TARGET_IP="$HOST"
else
  echo "Detected remote network - using ZeroTier connection"
  
  # Get ZeroTier IP from inventory
  echo "Looking up ZeroTier IP for $HOST..."
  HOST_INFO=$(cd "${THINKUBE_DIR}" && python3 << EOF
import yaml
import sys

# Load the original inventory
with open('inventory/inventory.yaml', 'r') as f:
    inventory = yaml.safe_load(f)

# Find the host and get its zerotier_ip
zerotier_ip = None
hostname = '$HOST'

# Search in baremetal hosts
if 'baremetal' in inventory['all']['children']:
    for host, data in inventory['all']['children']['baremetal']['hosts'].items():
        if host == hostname and data and 'zerotier_ip' in data:
            zerotier_ip = data['zerotier_ip']
            break

# Search in LXD containers if not found
if not zerotier_ip and 'lxd_containers' in inventory['all']['children']:
    for group_name, group_data in inventory['all']['children']['lxd_containers']['children'].items():
        if 'hosts' in group_data:
            for host, data in group_data['hosts'].items():
                if host == hostname and data and 'zerotier_ip' in data:
                    zerotier_ip = data['zerotier_ip']
                    break

if zerotier_ip:
    print(zerotier_ip)
else:
    print(f"ERROR:Host {hostname} not found or has no zerotier_ip")
    sys.exit(1)
EOF
)
  
  # Check if we got an error
  if [[ "$HOST_INFO" == ERROR:* ]]; then
    echo "$HOST_INFO"
    exit 1
  fi
  
  TARGET_IP="$HOST_INFO"
  echo "Connecting to ZeroTier IP: $TARGET_IP"
fi

echo "Using SSH username: $SYSTEM_USERNAME"

# Determine if the command needs sudo
needs_sudo=false
if [[ "$COMMAND" == "sudo "* || "$COMMAND" == *"reboot"* || "$COMMAND" == *"shutdown"* || "$COMMAND" == *"apt"* || "$COMMAND" == *"systemctl"* ]]; then
  needs_sudo=true
  # If command already has sudo, remove it as we'll add it with proper options
  if [[ "$COMMAND" == "sudo "* ]]; then
    COMMAND="${COMMAND#sudo }"
  fi
  echo "Command requires sudo privileges"
fi

# Execute command
echo "Executing command on $HOST ($TARGET_IP)..."

if $needs_sudo; then
  # Prepare a command that pipes the sudo password to sudo
  SUDO_COMMAND="echo '$ANSIBLE_BECOME_PASSWORD' | sudo -S $COMMAND"
  
  # Use sshpass to handle the SSH password
  sshpass -p "$ANSIBLE_SSH_PASS" ssh -o StrictHostKeyChecking=no "$SYSTEM_USERNAME@$TARGET_IP" "$SUDO_COMMAND"
else
  # Run command without sudo
  sshpass -p "$ANSIBLE_SSH_PASS" ssh -o StrictHostKeyChecking=no "$SYSTEM_USERNAME@$TARGET_IP" "$COMMAND"
fi

# Capture the exit code
EXIT_CODE=$?

echo "Command completed with exit code: $EXIT_CODE"

exit $EXIT_CODE