# Code-Server Shared Resources Map

## Overview

This document maps how resources are shared between code-server, thinkube-control, and the host system.

## Shared Storage Architecture

```
Host: vilanova1 (MicroK8s Control Plane)
├── /home/thinkube/.ssh/                    # SSH keys (READ-ONLY shared)
│   └── Mounted to code-server at /host-ssh
│
├── /home/thinkube/.venv/                   # Host Python venv
│   ├── Created by: infrastructure/00_setup_python_k8s.yaml
│   ├── Used by: Ansible playbooks that execute on vilanova1 via SSH
│   └── Contains: Ansible + copier + kubernetes module
│
└── /home/thinkube/shared-code/             # Main shared workspace (READ-WRITE)
    ├── Mounted to code-server at /home/coder
    ├── Mounted to thinkube-control at /home
    │
    ├── .thinkube_shared_shell/             # Shell functions/aliases
    │   ├── Created by: code-server (14_configure_shell.yaml)
    │   ├── Used by: code-server (bash/zsh/fish shells)
    │   └── Persistent across pod restarts
    │
    ├── workspace/                          # User workspace
    │   └── thinkube/                       # Main repo checkout
    │
    └── .local/share/code-server/           # VS Code settings
        └── Persistent across pod restarts
```

## Python & Tool Installations

### Host venv: `/home/thinkube/.venv` (on vilanova1)
- **Created by**: `ansible/40_thinkube/core/infrastructure/00_setup_python_k8s.yaml`
- **Used by**: Ansible playbooks when tasks execute on vilanova1 (target host)
- **Contains**: Ansible + kubernetes module for infrastructure management
- **Purpose**: When thinkube-control runs playbooks with `hosts: microk8s_control_plane`, tasks execute on vilanova1 via SSH and use this venv

### code-server container: System-wide tools
- **Python**: 3.12 (full, not slim - includes build tools)
- **Node.js**: 20.x LTS
- **Installed system-wide (not in venv)**:
  - ansible
  - ansible-core
  - copier
  - kubernetes module
- **Purpose**: Always available for development, regardless of project-specific venvs
- **Developer workflow**: Can create project venvs without losing access to Ansible/copier

### thinkube-control container: System-wide tools
- **Python**: 3.12-slim
- **Installed system-wide (not in venv)**:
  - ansible
  - copier
- **Purpose**: Ansible controller that SSHs to vilanova1 to run playbooks

## Why No Shared venv Between Containers?

**Original Plan (Failed)**:
- code-server creates `/home/thinkube/shared-code/.venv`
- thinkube-control mounts shared-code and uses the venv

**Why It Failed**:
- thinkube-control invokes `ansible-playbook` as a bare command (subprocess)
- No easy way to activate venv in subprocess calls
- WebSocket streaming made it impractical to source venv activation scripts

**Current Solution**:
- Install Ansible/copier directly in each container
- Simpler, more reliable
- Each container uses its own installation

## Volume Mounts Detail

### code-server Pod
```yaml
volumeMounts:
  - name: host-data                # /home/thinkube/shared-code
    mountPath: /home/coder
  - name: config                   # ConfigMap
    mountPath: /config
  - name: thinkube-ssh             # /home/thinkube/.ssh (READ-ONLY)
    mountPath: /host-ssh
    readOnly: true
```

### thinkube-control Pod
```yaml
volumeMounts:
  - name: shared-code              # /home/thinkube/shared-code
    mountPath: /home               # Maps to /home/ (root mount)
  - name: container-storage        # For buildah/podman
    mountPath: /var/lib/containers
```

## Key Paths Reference

| Resource | Host Path | code-server Path | thinkube-control Path | Purpose |
|----------|-----------|------------------|----------------------|---------|
| Shared workspace | `/home/thinkube/shared-code` | `/home/coder` | `/home` (root mount) | Main workspace |
| Host venv | `/home/thinkube/.venv` | NOT mounted | NOT mounted (accessed via SSH) | For playbooks on vilanova1 |
| Shell config | `/home/thinkube/shared-code/.thinkube_shared_shell` | `/home/coder/.thinkube_shared_shell` | `/home/.thinkube_shared_shell` | Functions/aliases |
| SSH keys | `/home/thinkube/.ssh` | `/host-ssh` (RO) | NOT mounted | Git operations |
| VS Code settings | `/home/thinkube/shared-code/.local/share/code-server` | `/home/coder/.local/share/code-server` | N/A | Editor config |

## Technology Stack

### code-server Container
- **Base Image**: `python:3.12` (full, with build tools)
- **Python Version**: 3.12
- **Node.js Version**: 20.x LTS
- **code-server**: Installed via official installer
- **Why full Python**: Development platform needs build tools for compiling packages

### thinkube-control Container
- **Base Image**: `python:3.12-slim`
- **Python Version**: 3.12
- **Why slim**: Runtime-only service with known dependencies

## Important Notes

1. **Persistence**: Everything under `/home/thinkube/shared-code` persists across pod restarts
2. **No venv conflicts**: Ansible/copier installed system-wide, not in venvs
3. **Developer freedom**: Can create project venvs without losing tools
4. **SSH keys**: Mounted read-only from host to prevent accidental modification
5. **Ansible execution model**:
   - **Ansible controller** runs in thinkube-control container
   - **Ansible tasks** execute on target hosts (vilanova1) via SSH
   - Tasks use the **target host's** venv, not the controller's packages

## Deployment Order

This architecture allows flexible deployment order:

1. **Infrastructure playbook** → Creates host venv at `/home/thinkube/.venv`
2. **code-server** → Mounts shared-code, has own Ansible installation
3. **thinkube-control** → Uses container's Ansible to run playbooks on hosts

No circular dependencies.
