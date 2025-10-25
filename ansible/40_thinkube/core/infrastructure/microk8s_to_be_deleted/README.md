# MicroK8s Infrastructure

This directory contains playbooks for installing and managing MicroK8s control and worker nodes as part of the Thinkube platform.

## Overview

MicroK8s is the lightweight Kubernetes distribution used by Thinkube. This component:
- Installs MicroK8s via snap package
- Configures the control node with proper networking
- Enables required addons (DNS, storage, Helm)
- Sets up kubectl and helm wrapper scripts
- Integrates with the Thinkube alias system

## Playbooks

### Control Node Playbooks

#### 10_install_microk8s.yaml
Main installation playbook that:
- Installs MicroK8s (classic snap)
- Configures node IP
- Adds user to microk8s group
- Enables required and optional addons
- Creates kubectl/helm wrappers
- Integrates with Thinkube alias system

#### 18_test_control.yaml
Test playbook that verifies:
- MicroK8s installation status
- Node readiness
- Addon status
- kubectl/helm functionality
- Alias system integration

#### 19_rollback_control.yaml
Rollback playbook that:
- Removes MicroK8s snap
- Cleans up configuration directories
- Removes kubectl/helm wrappers
- Removes aliases from Thinkube system
- Removes user from microk8s group

### Worker Node Playbooks

#### 20_join_workers.yaml
Worker installation playbook that:
- Installs MicroK8s on worker nodes
- Configures node IP
- Adds user to microk8s group
- Gets join token from control node
- Joins worker to cluster with --worker flag
- Enables required addons (dns, storage)

#### 28_test_worker.yaml
Worker test playbook that verifies:
- MicroK8s installation status
- Node joined to cluster
- Node is in Ready state
- Pod scheduling works
- Required addons enabled

#### 29_rollback_workers.yaml
Worker rollback playbook that:
- Drains and removes node from cluster
- Removes MicroK8s snap
- Cleans up configuration
- Removes user from microk8s group

## Usage

### Control Node Installation
```bash
# Install MicroK8s on control node
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/infrastructure/microk8s/10_install_microk8s.yaml

# Verify control node installation
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/infrastructure/microk8s/18_test_control.yaml
```

### Worker Node Installation
```bash
# Join worker nodes to cluster (requires control node to be running)
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/infrastructure/microk8s/20_join_workers.yaml

# Verify worker nodes
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/infrastructure/microk8s/28_test_worker.yaml
```

### Rollback
```bash
# Remove MicroK8s from control node
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/infrastructure/microk8s/19_rollback_control.yaml

# Remove MicroK8s from worker nodes
ansible-playbook -i inventory/inventory.yaml ansible/40_thinkube/core/infrastructure/microk8s/29_rollback_workers.yaml
```

## Requirements

- Ubuntu 22.04+ or compatible OS
- Snapd installed and running
- User account with sudo privileges
- Thinkube shell environment already configured

## Configuration

The playbooks use variables from the inventory:
- `control_node_ip`: IP address for the control node
- `system_username`: System user to configure (was admin_username)
- `lan_ip`: LAN IP (br0) for cluster communication
- `kubectl_bin`: Path to kubectl command
- `helm_bin`: Path to helm command

### Worker Nodes
- `tkw1`: VM on bcn1 with RTX 3090 passthrough
- `bcn1`: Baremetal server with direct GPU access

## Alias Integration

This component integrates with the Thinkube common alias system by creating:
- `kubectl_aliases.json`: kubectl shortcuts (k, kgp, kgs, etc.)
- `helm_aliases.json`: helm shortcuts (h, hl, hi, etc.)

Aliases are automatically loaded by the Thinkube shell environment.

## Notes

- User needs to log out/in after installation for group membership to take effect
- MicroK8s runs as a snap with strict confinement
- The control node IP is configured specifically to avoid issues with multi-homed systems
- Dashboard addon is optional and disabled by default

## Troubleshooting

### MicroK8s not starting
```bash
# Check snap status
snap list microk8s
sudo microk8s inspect

# Check logs
journalctl -u snap.microk8s.daemon-kubelite -f
```

### kubectl not working
```bash
# Verify wrapper script
ls -la ~/.local/bin/kubectl

# Check direct access
/snap/bin/microk8s.kubectl get nodes
```

### Aliases not working
```bash
# Regenerate aliases
~/.thinkube_shared_shell/scripts/regenerate_aliases.sh

# Source shell config
source ~/.bashrc  # or ~/.zshrc, config.fish
```

## Migration Notes

This component was migrated from thinkube-core with the following changes:
- Control node from `20_install_microk8s_planner.yaml`
- Worker nodes from `30_install_microk8s_worker.yaml`
- Updated to use FQCN for all modules
- Integrated with Thinkube common alias system
- Removed custom shell configuration in favor of centralized system
- Enhanced test coverage
- Added comprehensive rollback functionality
- Fixed privilege escalation issues in ansible.cfg
- Changed admin_username to system_username for consistency
- Added --worker flag to join command as per requirements
- Reduced token TTL from 3600 to 300 seconds for security
- Changed node IP configuration from zerotier_ip to lan_ip (br0) for proper cluster communication