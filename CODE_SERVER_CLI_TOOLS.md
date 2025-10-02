# code-server CLI Tools Inventory

This document lists all CLI tools that should be available in the code-server environment to enable complete Thinkube platform development.

## Status: 🚧 In Progress

Last Updated: September 28, 2025

---

## Platform Core Tools

### 1. kubectl - Kubernetes Cluster Management
**Status**: ✅ Available (via MicroK8s)
**Purpose**: Manage Kubernetes resources
**Installation**: Already available as `microk8s.kubectl`
**Configuration**:
```bash
# Create alias or symlink
alias kubectl='microk8s.kubectl'
# Or configure kubeconfig for standard kubectl
```

### 2. helm - Kubernetes Package Manager
**Status**: ❌ Needs Installation
**Purpose**: Deploy and manage Helm charts
**Installation**:
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```
**Configuration**: Uses same kubeconfig as kubectl

### 3. k9s - Terminal UI for Kubernetes
**Status**: ❌ Needs Installation
**Purpose**: Interactive cluster management
**Installation**:
```bash
# Install from GitHub releases
curl -sS https://webinstall.dev/k9s | bash
```
**Usage**: Run `k9s` in terminal for full cluster visualization

### 4. podman - Podman CLI
**Status**: ❌ Needs Installation
**Purpose**: Build and manage container images (daemonless, more secure than Docker)
**Installation**:
```bash
# Install Podman, buildah, and skopeo (Thinkube standard)
apt-get install -y podman buildah skopeo
```
**Configuration**:
```bash
# No daemon needed - Podman runs daemonless
# Configure for rootless operation
mkdir -p ~/.config/containers
```
**Why Podman?**: Thinkube uses Podman (not Docker) for security and rootless operation

### 5. git - Version Control
**Status**: ✅ Available
**Purpose**: Source code management
**Configuration**: SSH keys already configured in deployment

---

## Ansible and Configuration Management

### 6. ansible - Infrastructure Automation (via Host Virtualenv)
**Status**: ✅ Available (via mounted virtualenv)
**Purpose**: Infrastructure automation and configuration management
**How It Works**: code-server uses the **host's virtualenv** at `/home/thinkube/.venv`
- Same Ansible installation as thinkube-control
- Same collections (kubernetes.core, community.general, etc.)
- Same versions, no duplication
- Wrapper functions automatically activate the venv

**Available Commands** (all via wrapper functions):
- `ansible` - Ad-hoc command execution
- `ansible-playbook` - Run playbooks
- `ansible-galaxy` - Manage collections and roles
- `ansible-vault` - Encrypt sensitive data

**Usage**:
```bash
# Just use ansible commands normally - wrappers handle activation
ansible --version
ansible-playbook path/to/playbook.yaml
ansible-galaxy collection list
```

**Configuration**:
```ini
# ~/.ansible.cfg (already configured)
[defaults]
inventory = /workspace/thinkube/inventory/inventory.yaml
host_key_checking = False
remote_user = thinkube

[ssh_connection]
ssh_args = -o ForwardAgent=yes
pipelining = True
```

---

## Thinkube Platform Services

### 10. argo - Argo Workflows CLI
**Status**: ❌ Needs Installation
**Purpose**: Manage CI/CD workflows
**Installation**:
```bash
# Download from GitHub releases
curl -sLO https://github.com/argoproj/argo-workflows/releases/download/v3.5.5/argo-linux-amd64.gz
gunzip argo-linux-amd64.gz
chmod +x argo-linux-amd64
mv argo-linux-amd64 /usr/local/bin/argo
```
**Configuration**:
```bash
# Set ARGO_SERVER environment variable
export ARGO_SERVER=argo-workflows.argo-workflows.svc.cluster.local:2746
export ARGO_NAMESPACE=argo-workflows
```

### 11. argocd - ArgoCD CLI
**Status**: ❌ Needs Installation
**Purpose**: Manage GitOps deployments
**Installation**:
```bash
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd
```
**Configuration**:
```bash
# Login to ArgoCD server
argocd login argocd.{{ domain_name }} --username admin --password $ADMIN_PASSWORD
```

### 12. gh - GitHub CLI
**Status**: ❌ Needs Installation
**Purpose**: Interact with GitHub repositories and APIs
**Installation**:
```bash
# From official apt repository
type -p curl >/dev/null || (apt update && apt install curl -y)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt update
apt install gh -y
```
**Configuration**:
```bash
# Authenticate with token
echo $GITHUB_TOKEN | gh auth login --with-token
```

### 13. nats - NATS CLI
**Status**: ❌ Needs Installation
**Purpose**: Interact with NATS messaging system
**Installation**:
```bash
# Download from GitHub releases
curl -sf https://binaries.nats.dev/nats-io/natscli/nats@latest | sh
mv nats /usr/local/bin/
```
**Configuration**:
```bash
# Create context for Thinkube NATS cluster
nats context save thinkube \
  --server=nats://nats.nats.svc.cluster.local:4222 \
  --description="Thinkube NATS Server"
nats context select thinkube
```
**Usage Examples**:
```bash
# Publish message
nats pub test.subject "Hello World"

# Subscribe to subject
nats sub test.subject

# Create stream
nats stream add EVENTS

# View stream info
nats stream info EVENTS
```

### 14. harbor-cli / Podman for Harbor
**Status**: ❌ Needs Configuration
**Purpose**: Interact with Harbor registry
**Method**: Use Podman CLI or curl for Harbor API
**Configuration**:
```bash
# Login to Harbor registry with Podman
podman login registry.{{ domain_name }} -u admin -p $ADMIN_PASSWORD

# Or use Harbor API via curl
export HARBOR_URL=https://registry.{{ domain_name }}
export HARBOR_TOKEN=$(curl -X POST "$HARBOR_URL/c/login" \
  -d "principal=admin&password=$ADMIN_PASSWORD" | jq -r .token)
```

### 15. mlflow - MLflow CLI
**Status**: ❌ Needs Installation
**Purpose**: Manage ML experiments and models
**Installation**:
```bash
pip3 install mlflow
```
**Configuration**:
```bash
# Set tracking URI
export MLFLOW_TRACKING_URI=https://mlflow.{{ domain_name }}
```
**Usage Examples**:
```bash
# List experiments
mlflow experiments list

# Search runs
mlflow runs list --experiment-id 0

# Download artifacts
mlflow artifacts download --run-id <run_id>
```

### 16. devpi - DevPi CLI
**Status**: ❌ Needs Installation
**Purpose**: Interact with private Python package index
**Installation**:
```bash
pip3 install devpi-client
```
**Configuration**:
```bash
# Configure devpi server
devpi use https://devpi-api.{{ domain_name }}
devpi login root --password $DEVPI_ADMIN_PASSWORD

# Set as default index
devpi use root/pypi
```
**Usage Examples**:
```bash
# Upload package
devpi upload

# List packages
devpi list <package-name>

# Install from devpi
pip install --index-url https://devpi-api.{{ domain_name }}/root/pypi/+simple/ <package>
```

---

## Development Tools

### 17. python3 - Python Runtime
**Status**: ✅ Available
**Purpose**: Python development and scripting

### 18. pip - Python Package Installer
**Status**: ✅ Available
**Purpose**: Install Python packages

### 19. node - Node.js Runtime
**Status**: ✅ Available (v20)
**Purpose**: JavaScript/TypeScript development

### 20. npm - Node Package Manager
**Status**: ✅ Available
**Purpose**: Install Node packages

### 21. pnpm - Fast Node Package Manager (Optional)
**Status**: ❌ Needs Installation
**Purpose**: Alternative to npm with better disk usage
**Installation**:
```bash
npm install -g pnpm
```

### 22. jq - JSON Processor
**Status**: ❌ Needs Installation
**Purpose**: Parse and manipulate JSON in shell scripts
**Installation**:
```bash
apt-get install -y jq
```

### 23. yq - YAML Processor
**Status**: ❌ Needs Installation
**Purpose**: Parse and manipulate YAML files
**Installation**:
```bash
# Install mikefarah/yq (v4)
wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/local/bin/yq
chmod +x /usr/local/bin/yq
```

### 24. curl - HTTP Client
**Status**: ✅ Available
**Purpose**: Make HTTP requests

---

## Database and Data Tools

### 25. psql - PostgreSQL CLI Client
**Status**: ❌ Needs Installation
**Purpose**: Connect to PostgreSQL databases
**Installation**:
```bash
apt-get install -y postgresql-client
```
**Configuration**:
```bash
# Add connection alias to ~/.bashrc
alias psql-thinkube="psql -h postgresql.postgresql.svc.cluster.local -U postgres"
```
**Usage Examples**:
```bash
# Connect to database
psql -h postgresql.postgresql.svc.cluster.local -U postgres -d mlflow

# List databases
psql -h postgresql.postgresql.svc.cluster.local -U postgres -c '\l'
```

### 26. valkey-cli - Valkey/Redis CLI
**Status**: ❌ Needs Installation
**Purpose**: Interact with Valkey/Redis databases
**Installation**:
```bash
apt-get install -y redis-tools
# valkey-cli is compatible with redis-cli
```
**Configuration**:
```bash
alias valkey-cli='redis-cli'
```

### 27. clickhouse-client - ClickHouse CLI
**Status**: ❌ Needs Installation
**Purpose**: Query ClickHouse database (used by Langfuse)
**Installation**:
```bash
curl https://clickhouse.com/ | sh
mv clickhouse /usr/local/bin/clickhouse-client
```
**Configuration**:
```bash
# Connect to ClickHouse cluster
clickhouse-client --host=clickhouse.clickhouse.svc.cluster.local --port=9000
```

---

## Optional but Useful Tools

### 28. stern - Multi-pod Log Tailing
**Status**: ❌ Needs Installation
**Purpose**: Tail logs from multiple pods simultaneously
**Installation**:
```bash
curl -sL https://github.com/stern/stern/releases/download/v1.28.0/stern_1.28.0_linux_amd64.tar.gz | tar xz
mv stern /usr/local/bin/
```
**Usage**:
```bash
# Tail logs from all pods in namespace
stern -n mlflow .

# Tail logs matching pattern
stern -n default "mlflow.*"
```

### 29. kubectx / kubens - Context/Namespace Switcher
**Status**: ❌ Needs Installation
**Purpose**: Quickly switch Kubernetes contexts and namespaces
**Installation**:
```bash
# Install kubectx and kubens
git clone https://github.com/ahmetb/kubectx /opt/kubectx
ln -s /opt/kubectx/kubectx /usr/local/bin/kubectx
ln -s /opt/kubectx/kubens /usr/local/bin/kubens
```

### 30. copier - Template Tool
**Status**: ❌ Needs Installation
**Purpose**: Generate projects from templates (for thinkube-control development)
**Installation**:
```bash
pip3 install copier
```

### 31. just - Command Runner (Optional)
**Status**: ❌ Needs Installation
**Purpose**: Modern alternative to make for running commands
**Installation**:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

---

## Installation Priority

### High Priority (Essential for Thinkube development)
- ✅ kubectl, git, python3, node, npm, curl (already available)
- ❌ ansible + collections
- ❌ helm
- ❌ podman (+ buildah, skopeo)
- ❌ argo
- ❌ argocd
- ❌ gh
- ❌ jq, yq
- ❌ psql

### Medium Priority (Very useful)
- ❌ k9s
- ❌ nats
- ❌ mlflow
- ❌ devpi
- ❌ stern
- ❌ valkey-cli

### Low Priority (Optional enhancements)
- ❌ clickhouse-client
- ❌ ansible-lint
- ❌ pnpm
- ❌ kubectx/kubens
- ❌ copier
- ❌ just

---

## Next Steps

1. Build custom code-server image with all High Priority tools preinstalled
2. Create installation script for Medium Priority tools (if needed)
3. Add VS Code extensions for key tools (Ansible, Kubernetes, Podman)
4. Create wrapper scripts for common operations
5. Document usage patterns for each tool

**Note**: Tools are now preinstalled in custom image `code-server-dev:latest` (see Dockerfile at `ansible/40_thinkube/core/harbor/base-images/code-server-dev.Dockerfile.j2`)

---

## See Also

- [code-server Enhancement Plan](CODE_SERVER_ENHANCEMENT_PLAN.md) - Implementation details
- [Phase 4.5 Timeline](PHASE_4_5_TIMELINE.md) - Overall schedule
