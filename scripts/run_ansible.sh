#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Smart Ansible runner that detects local vs remote network
# Usage: ./scripts/run_ansible.sh ansible/path/to/playbook.yaml [ansible-args]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THINKUBE_DIR="$(dirname "$SCRIPT_DIR")"

# Source network detection
source "${SCRIPT_DIR}/network_detect.sh"

# Check if playbook argument is provided
if [ -z "$1" ]; then
  echo "ERROR: No playbook specified"
  echo "Usage: $0 ansible/path/to/playbook.yaml [additional options]"
  exit 1
fi

PLAYBOOK="$1"
shift  # Remove first argument

# Source environment variables
if [ -f "$HOME/.env" ]; then
  echo "Loading environment variables from $HOME/.env"
  source "$HOME/.env"
else
  echo "ERROR: $HOME/.env file not found!"
  exit 1
fi

# Activate virtual environment if it exists
if [ -d "$HOME/.venv" ]; then
  echo "Activating Python virtual environment from $HOME/.venv"
  source "$HOME/.venv/bin/activate"
fi

# Check for required environment variables
if [ -z "$ANSIBLE_BECOME_PASSWORD" ]; then
  echo "ERROR: ANSIBLE_BECOME_PASSWORD environment variable not set!"
  exit 1
fi

# Export environment variables for Ansible
export ANSIBLE_BECOME_PASSWORD="$ANSIBLE_BECOME_PASSWORD"
export ADMIN_USERNAME="${ADMIN_USERNAME:-tkadmin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-$ANSIBLE_BECOME_PASSWORD}"

# Set up authentication
if [ -n "$ANSIBLE_SSH_PASS" ]; then
  echo "Using ANSIBLE_SSH_PASS for SSH authentication"
else
  echo "ANSIBLE_SSH_PASS not set, using ANSIBLE_BECOME_PASSWORD for SSH authentication"
  export ANSIBLE_SSH_PASS="$ANSIBLE_BECOME_PASSWORD"
fi

# Make sure we have sshpass installed
if ! command -v sshpass &> /dev/null; then
  echo "Installing sshpass..."
  sudo apt-get update -qq && sudo apt-get install -qq -y sshpass
fi

# Get the system username from inventory
SYSTEM_USERNAME=$(cd "${THINKUBE_DIR}" && python3 -c "import yaml; inv=yaml.safe_load(open('inventory/inventory.yaml')); print(inv['all']['vars']['system_username'])" 2>/dev/null || echo "thinkube")
if [ -z "$SYSTEM_USERNAME" ]; then
  echo "WARNING: Could not determine system_username from inventory, using default 'thinkube'"
  SYSTEM_USERNAME="thinkube"
fi

# Common Ansible settings
export ANSIBLE_HOST_KEY_CHECKING=False

# Check if we're on local or remote network
if is_local_network; then
  echo "Detected local network - using direct connection"
  
  # Create a temporary vars file for authentication
  TEMP_VARS="/tmp/ansible-vars-$$.yml"
  cat > "$TEMP_VARS" << EOF
---
ansible_become_pass: "$ANSIBLE_BECOME_PASSWORD" 
ansible_ssh_pass: "$ANSIBLE_SSH_PASS"
ansible_user: "$SYSTEM_USERNAME"
ansible_python_interpreter: "/home/$SYSTEM_USERNAME/.venv/bin/python3"
EOF
  
  # Execute playbook with extra vars
  echo "Running playbook: $PLAYBOOK"
  ansible-playbook -i inventory/inventory.yaml "$PLAYBOOK" -e "@$TEMP_VARS" "$@"
  RESULT=$?
  
  # Clean up temporary files
  rm -f "$TEMP_VARS"
  
else
  echo "Detected remote network - using ZeroTier connection"
  
  # Create temporary inventory directory with ZeroTier IPs
  echo "Creating temporary inventory with ZeroTier IPs..."
  TEMP_DIR=$(mktemp -d /tmp/zerotier-inventory.XXXXXX)
  TEMP_INVENTORY="${TEMP_DIR}/hosts.yaml"
  
  # Copy group_vars and host_vars to maintain all variable definitions
  if [ -d "${THINKUBE_DIR}/inventory/group_vars" ]; then
    cp -r "${THINKUBE_DIR}/inventory/group_vars" "${TEMP_DIR}/"
  fi
  if [ -d "${THINKUBE_DIR}/inventory/host_vars" ]; then
    cp -r "${THINKUBE_DIR}/inventory/host_vars" "${TEMP_DIR}/"
  fi
  
  # Use Python to modify the inventory
  python3 << EOF
import yaml
import copy

# Load the original inventory
with open('${THINKUBE_DIR}/inventory/inventory.yaml', 'r') as f:
    inventory = yaml.safe_load(f)

# Deep copy to avoid modifying the original
zerotier_inventory = copy.deepcopy(inventory)

# Update baremetal hosts to use zerotier_ip as ansible_host
if 'baremetal' in zerotier_inventory['all']['children']:
    for host, data in zerotier_inventory['all']['children']['baremetal']['hosts'].items():
        if data and 'zerotier_ip' in data:
            print(f"  Updating {host}: {data['ansible_host']} -> {data['zerotier_ip']}")
            data['ansible_host'] = data['zerotier_ip']

# Update LXD containers to use zerotier_ip as ansible_host
if 'lxd_containers' in zerotier_inventory['all']['children']:
    for group_name, group_data in zerotier_inventory['all']['children']['lxd_containers']['children'].items():
        if 'hosts' in group_data:
            for host, data in group_data['hosts'].items():
                if data and 'zerotier_ip' in data:
                    print(f"  Updating {host}: {data.get('ansible_host', 'N/A')} -> {data['zerotier_ip']}")
                    data['ansible_host'] = data['zerotier_ip']

# Write the temporary inventory
with open('${TEMP_INVENTORY}', 'w') as f:
    yaml.dump(zerotier_inventory, f, default_flow_style=False)

print(f"\nTemporary inventory created: ${TEMP_INVENTORY}")
EOF
  
  # Set up environment variables for ZeroTier
  export ANSIBLE_INVENTORY="${TEMP_DIR}"
  export ANSIBLE_SSH_ARGS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
  
  # Create temporary vars file with authentication
  TEMP_VARS="${TEMP_DIR}/extra-vars.yml"
  cat > "$TEMP_VARS" << EOF
---
ansible_become_pass: "$ANSIBLE_BECOME_PASSWORD"
ansible_ssh_pass: "$ANSIBLE_SSH_PASS"
ansible_user: "$SYSTEM_USERNAME"
ansible_python_interpreter: "/home/${SYSTEM_USERNAME}/.venv/bin/python3"
EOF
  
  echo "Running Ansible with ZeroTier connectivity..."
  echo "Command: ansible-playbook $PLAYBOOK $@"
  
  # Run ansible-playbook with all arguments and extra vars
  ansible-playbook -e "@${TEMP_VARS}" "$PLAYBOOK" "$@"
  RESULT=$?
  
  # Clean up
  rm -rf "${TEMP_DIR}"
fi

# Report status
if [ $RESULT -eq 0 ]; then
  echo "Playbook execution completed successfully"
else
  echo "Playbook execution failed with error code $RESULT"
  exit $RESULT
fi