#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Network detection helper - to be sourced by other scripts

# Function to check if we're on the cluster's local network
is_local_network() {
  # Get script directory to find inventory
  local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local thinkube_dir="$(dirname "$script_dir")"
  
  # Allow override via environment variable
  if [[ -n "$THINKUBE_NETWORK_MODE" ]]; then
    case "$THINKUBE_NETWORK_MODE" in
      local) return 0 ;;
      remote) return 1 ;;
    esac
  fi
  
  # Extract a cluster node's local IP from inventory
  if [[ -f "${thinkube_dir}/inventory/inventory.yaml" ]]; then
    # Get the first node's ansible_host (local IP) and remove quotes
    local node_ip=$(grep -A1 "vilanova1:" "${thinkube_dir}/inventory/inventory.yaml" | grep "ansible_host:" | awk '{print $2}' | head -1 | tr -d '"')
    
    if [[ -n "$node_ip" ]]; then
      # Try to ping the cluster node on its local IP
      if ping -c 1 -W 1 "$node_ip" &> /dev/null; then
        return 0  # We can reach cluster nodes directly - local network
      fi
    fi
  fi
  
  # No need for additional checks - if we reached this point, 
  # it means we couldn't ping the local IP from inventory
  
  return 1  # Default to remote (safer)
}