# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thinkube is a collection of Ansible playbooks for deploying a complete Kubernetes homelab platform on Ubuntu servers. The playbooks provision bare-metal hosts, install Canonical k8s-snap, and deploy 17 core services plus 17+ optional services (AI/ML tools, databases, monitoring).

**Version**: 0.1.0 (under active development)

## Running Playbooks

Playbooks are designed to be run by the **thinkube-installer**, a Tauri desktop app (separate repo at `../thinkube-installer/`). The installer:

1. Clones this repo to `/tmp/thinkube-installer-<random>/`
2. Generates inventory (minimal for SSH setup, full for deployment)
3. Executes playbooks via its FastAPI backend with real-time WebSocket streaming
4. Cleans up the temp clone after deployment

### Manual Execution (Development)

For development and testing, use `scripts/tk_ansible` from code-server:

```bash
./scripts/tk_ansible ansible/40_thinkube/core/keycloak/00_install.yaml
./scripts/tk_ansible ansible/40_thinkube/core/harbor/10_deploy.yaml
./scripts/tk_ansible ansible/40_thinkube/core/postgresql/18_test.yaml -v
```

`tk_ansible` loads `$HOME/.env` (requires `ANSIBLE_BECOME_PASSWORD`), activates `$HOME/.venv`, and runs against shared inventory at `/home/thinkube/.ansible/inventory/`.

For running from outside the cluster network (via ZeroTier), use `scripts/run_ansible.sh` instead - it auto-detects network and rewrites inventory IPs to ZeroTier addresses.

### Environment Variables

Required in `~/.env`:
- `ANSIBLE_BECOME_PASSWORD` - Sudo password for remote hosts
- `ANSIBLE_SSH_PASS` - SSH password (falls back to ANSIBLE_BECOME_PASSWORD)

Optional:
- `ADMIN_PASSWORD`, `ADMIN_USERNAME` (default: tkadmin) - Service admin credentials
- `GITHUB_TOKEN`, `GITHUB_ORG` - GitHub integration
- `CLOUDFLARE_TOKEN` - DNS management
- `ZEROTIER_NETWORK_ID` - Network overlay
- `CLUSTER_NAME` - Kubernetes cluster name
- `DOMAIN_NAME` - Domain name for services

## Testing

Each component has an `18_test.yaml` that validates the deployment:
```bash
./scripts/tk_ansible ansible/40_thinkube/core/keycloak/18_test.yaml
```

Basic connectivity test:
```bash
./scripts/tk_ansible ansible/test/hello-world.yaml
```

## Architecture

### Deployment Phases

Playbooks are organized into numbered phases reflecting deployment order:

```
ansible/
  00_initial_setup/     # SSH keys, environment, GPU reservation, GitHub CLI
  10_baremetal_infra/   # Network bridges, server restarts
  30_networking/        # ZeroTier/Tailscale VPN overlay
  40_thinkube/          # Main platform
    core/               # Required services
    optional/           # Add-on services
  misc/                 # Shell/dev environment setup (fish, tmux, claude)
  roles/                # Reusable Ansible roles
  test/                 # Test playbooks
```

### Playbook Numbering Convention

Every component follows a standardized lifecycle:

| Prefix | Purpose |
|--------|---------|
| `00_install.yaml` | Orchestrator - calls subsequent playbooks in order |
| `10_deploy.yaml` | Primary deployment (Helm chart, k8s resources) |
| `10_configure_keycloak.yaml` | SSO/OIDC client setup (services needing auth) |
| `11-16_*.yaml` | Additional config steps (tokens, CLI, SSH keys, etc.) |
| `17_configure_discovery.yaml` | Service discovery registration |
| `18_test.yaml` | Validation and health checks |
| `19_rollback.yaml` | Clean removal (terminates connections, drops DBs, deletes namespace) |

Use `19_rollback.yaml` when a deployment failed and you need a clean slate, or when a database has active connections preventing a drop.

### Core Components (ansible/40_thinkube/core/)

Deployed in dependency order:

1. **infrastructure/** - k8s-snap cluster, ingress (nginx), ACME certificates, CoreDNS, GPU operator
2. **postgresql/** - Shared database
3. **seaweedfs/** - S3-compatible object storage
4. **juicefs/** - POSIX filesystem layer + MLflow gateway
5. **keycloak/** - Identity provider (SSO for all services, realm: `thinkube`)
6. **harbor/** - Container registry + **harbor-images/** for building base images
7. **gitea/** - Internal Git server
8. **argo-workflows/** - Workflow engine (triggered by Gitea webhooks)
9. **argocd/** - GitOps continuous deployment
10. **devpi/** - Python package repository
11. **code-server/** - VS Code in browser
12. **jupyterhub/** - Jupyter notebook environment
13. **mlflow/** - ML experiment tracking
14. **thinkube-control/** - Platform control plane (FastAPI + React)

### Optional Components (ansible/40_thinkube/optional/)

AI/ML: ollama, litellm, langfuse, argilla, cvat
Vector DBs: qdrant, chroma, weaviate
Data: clickhouse, opensearch, nats
Monitoring: prometheus, perses
Tools: pgadmin, valkey, knative

### Reusable Roles (ansible/roles/)

- **container_deployment/** - Main deployment framework (Helm, ArgoCD, webhooks, image management)
- **keycloak/** - OIDC client/realm configuration
- **common/** - Shared environment and SSH key utilities
- **gitea/** - Gitea API interactions
- **oauth2_proxy/** - OAuth2 proxy setup
- **valkey/** - Cache deployment
- **waiting_for_image/** - Image availability polling

### Key Variables

Variables are defined in inventory group vars (`/home/thinkube/.ansible/inventory/group_vars/k8s.yml`). Key patterns:

- `domain_name` - Base domain
- `*_hostname` - Service hostnames (e.g., `keycloak_hostname: auth.{{ domain_name }}`)
- `*_namespace` - K8s namespaces per service
- `harbor_registry` - Container registry URL (`registry.{{ domain_name }}`)
- `kubeconfig` - Path to kubeconfig
- `kubectl_bin`, `helm_bin` - Binary paths under `~/.local/bin/`
- `keycloak_realm: thinkube` - Shared SSO realm
- `zerotier_subnet_prefix` - Network prefix for all cluster IPs

### Playbook Patterns

Playbooks target host groups from inventory (e.g., `k8s_control_plane`, `baremetal`). They use the `kubernetes.core` Ansible collection for k8s operations. Sensitive values come from environment variables loaded via `$HOME/.env`.

## Path Safety

This repository is the source of truth. The installer clones it to `/tmp/` for execution. Never edit files in the `/tmp/` clone - changes will be lost. Always edit and commit from this repository.

## thinkube-control Deployment Workflow

When modifying thinkube-control (the platform control plane), follow this exact workflow:

1. Edit files in `/home/thinkube/thinkube-platform/thinkube-control/`
2. Commit and push to GitHub
3. Deploy: `./scripts/tk_ansible ansible/40_thinkube/core/thinkube-control/12_deploy_dev.yaml`

The deployment uses Copier to sync from GitHub to the runtime location (`/home/thinkube/thinkube-control/`), then triggers a build via Gitea webhook + Argo Workflow, and ArgoCD deploys the new image.

- Do NOT edit files in `/home/thinkube/thinkube-control/` directly (overwritten by Copier)
- Do NOT use `12_deploy.yaml` (not idempotent) - always use `12_deploy_dev.yaml`

## Template Deployments (FORBIDDEN)

Never deploy, redeploy, or trigger builds for template deployments (namespaces like `gptoss20`). These are only triggered through the thinkube-control UI. You may modify template source files in `/home/thinkube/thinkube-platform/tkt-*` and build/push base images, but stop after changes and let the user trigger rebuilds.

## Monitoring

```bash
# Check Argo build workflows
kubectl get workflows -n argo --sort-by=.metadata.creationTimestamp | tail -10

# Check a component's pods
kubectl get pods -n <namespace>

# Check thinkube-control backend
kubectl get pods -n thinkube-control -l app=thinkube-control-backend
```

## Troubleshooting

**"database is being accessed by other users"** - Run the component's rollback playbook to terminate active connections and drop databases cleanly:
```bash
./scripts/tk_ansible ansible/40_thinkube/core/SERVICE_NAME/19_rollback.yaml
```

**"ANSIBLE_BECOME_PASSWORD not set"** - Ensure `~/.env` contains `ANSIBLE_BECOME_PASSWORD=<password>` and is loaded before running playbooks. `tk_ansible` loads it automatically; for manual runs, `source ~/.env` first.
