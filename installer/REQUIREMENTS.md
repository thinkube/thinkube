# Thinkube Installer Requirements

## Overview

The Thinkube installer runs on an Ansible control node (your workstation) and deploys to baremetal servers. This document clarifies the requirements for both the control node and the target infrastructure.

## Two-Phase Approach

### Phase 1: Control Node Setup
The installer first prepares the local machine (where you run the installer) with Ansible and required tools.

### Phase 2: Baremetal Discovery
After SSH access is configured, the installer discovers and validates the actual cluster hardware.

## Control Node Requirements (Where Installer Runs)

### Operating System
- **Ubuntu 24.04.x LTS Desktop** (recommended for full experience)
- Fresh installation recommended

### Hard Requirements
1. **Operating System**: Ubuntu 24.04.x LTS only
   - Check: `lsb_release -r` must show 24.04.x
   - Action if failed: Display error and stop

2. **System User**: Non-root user with sudo access
   - Check: User is not root AND can run sudo
   - Action if failed: Display error and stop

3. **Network Connectivity**: Internet access required
   - Check: Can reach Ubuntu package repositories
   - Action if failed: Display error and stop

4. **Disk Space**: Minimum 10GB free space (for tools and logs)
   - Check: Available space in /home
   - Action if failed: Display error and stop

### Tools to be Installed on Control Node
These will be automatically installed if missing:
- Git
- OpenSSH Client
- Python Virtual Environment
- Ansible (in virtualenv)
- kubectl, helm, and other CLI tools

## Baremetal Server Requirements (Target Infrastructure)

### Minimum Cluster Requirements
The cluster requirements can be met by either:
- **Single powerful server** meeting all requirements
- **Multiple servers** whose combined resources meet requirements

### Combined Cluster Resources (Minimum)
- **CPU**: 16+ cores total across all nodes
- **Memory**: 64GB+ total across all nodes  
- **Storage**: 500GB+ total across all nodes
- **Network**: Gigabit Ethernet between nodes

### Individual Server Requirements
- **Operating System**: Ubuntu 24.04.x LTS (Server or Desktop)
- **Architecture**: amd64 or arm64
- **Network**: Fixed IP addresses (must be configured before installation - see below)
- **Access**: Initial SSH access with password (passwordless SSH will be configured by thinkube)

### Network Prerequisites (User Responsibility)
Before running the installer, users must configure fixed IP addresses on each server:

1. **Router Configuration**: 
   - Reserve a range of IP addresses outside DHCP range
   - Example: If DHCP uses 10.0.1.1-100, use 10.0.1.101+ for cluster

2. **Fixed IP Assignment**: 
   - Configure each server with a static IP using netplan
   - The README provides a script to help with this configuration
   - Document these IPs for entry during installation

**What thinkube handles**:
- Network bridges for VM communication
- ZeroTier overlay network
- DNS configuration
- Container networking

**What users must handle**:
- Fixed IP assignment on baremetal servers
- Router/DHCP configuration

### GPU Detection (Optional)
- **NVIDIA GPUs**: Detected after SSH access is established
- Used for GPU-accelerated workloads if available
- Not required for basic cluster operation

## Installation Flow

### Phase 1: Control Node Setup

#### 1. Control Node Requirements Check
```
Control Node Requirements:
✓ Ubuntu 24.04.2 LTS Desktop       [Required - Met]
✓ User 'admin' with sudo access   [Required - Met]
✓ Network connectivity             [Required - Met]
✓ Disk space (15GB available)      [Required - Met]

Tools to be Installed:
ℹ Git                              [Will be installed]
ℹ OpenSSH Client                   [Will be installed]
ℹ Python Virtual Environment       [Will be created]
ℹ Ansible 2.15.x                   [Will be installed]
```

#### 2. Sudo Password Collection
- Request sudo password for control node
- Verify password is correct
- Use for installing tools on control node

#### 3. Tool Installation
- Run `10_install-tools.sh` to install base requirements
- Create Python virtual environment
- Install Ansible in virtual environment

### Phase 2: Baremetal Configuration

#### 4. Baremetal Server Configuration
- Add server IPs/hostnames (user must provide fixed IPs configured earlier)
- Enter SSH password for initial connection
- Thinkube will then configure passwordless SSH via ansible/00_initial_setup/10_setup_ssh_keys.yaml

#### 5. Hardware Discovery
After SSH is configured, discover actual hardware:
```
Cluster Hardware Summary:
Total CPU Cores: 24 (3 servers × 8 cores)
Total Memory: 96GB (3 servers × 32GB)
Total Storage: 1.5TB (3 servers × 500GB)
GPUs Detected: 2 × NVIDIA RTX 3090

✓ Cluster meets minimum requirements
```

#### 6. Cluster Deployment
- Configure network bridges
- Deploy LXD
- Create VMs
- Install Kubernetes
- Deploy thinkube services

## User Experience Guidelines

### Clear Communication
- Don't treat missing tools as errors
- Clearly distinguish between "required" and "will be installed"
- Use informational tone for tools that will be installed

### Fresh System Assumption
- Assume the user is starting with a fresh Ubuntu 24.04 installation
- Don't check for conflicts with existing software
- Provide warnings if non-standard configurations are detected

### Reduced Complexity
- No support for other Ubuntu versions
- No support for other Linux distributions
- No upgrade paths from older versions
- No support for non-standard Python installations

## Technical Implementation

### Backend Checks
The `/check-requirements` endpoint should return:

```json
{
  "requirements": [
    {
      "name": "Ubuntu 24.04.x LTS",
      "category": "system",
      "required": true,
      "status": "pass",
      "details": "Ubuntu 24.04.2 LTS (Noble Numbat)"
    },
    {
      "name": "Git",
      "category": "tools",
      "required": false,
      "status": "missing",
      "details": "Will be installed",
      "action": "install"
    }
  ]
}
```

### Status Values
- `pass`: Requirement is met
- `missing`: Tool is missing but will be installed
- `fail`: Hard requirement not met (stops installation)

### Categories
- `system`: OS, user, network, disk (hard requirements)
- `tools`: Software that will be installed if missing

## Questions for Iteration

1. **Thinkube Detection**: How to detect if thinkube is already installed?
   - Check for running k8s cluster?
   - Check for LXD VMs (tkc, tkw1, etc.)?
   - Check for specific services running?

2. **SSH Configuration**: 
   - Initial connection uses password authentication
   - Thinkube playbook handles key generation and distribution
   - Should installer run the SSH setup playbook automatically?

3. **Network Configuration**:
   - How to validate network bridges are not conflicting?
   - Should we detect existing network configurations?

4. **Baremetal Server Entry**:
   - Manual IP entry (users must provide fixed IPs they configured)
   - No automatic discovery (users know their server IPs)
   - Fixed IPs are prerequisite (no DHCP support)

5. **Failure Recovery**:
   - What if Phase 1 succeeds but Phase 2 fails?
   - How to resume installation?

## Next Steps

1. Refine the requirements based on feedback
2. Update the backend to implement the new check logic
3. Update the frontend to display requirements in a user-friendly way
4. Implement the "Install Tools & Continue" flow