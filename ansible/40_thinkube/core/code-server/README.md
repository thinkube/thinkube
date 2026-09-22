# Code Server Deployment

VS Code in the browser for cloud-based development, integrated with Thinkube platform.

## Installation

Code Server is a core component. The Thinkube installer installs it by
running `00_install.yaml`, which runs `10_deploy.yaml`,
`13_clone_repositories.yaml`, `14_configure_shell.yaml`,
`15_configure_environment.yaml`, `16_configure_gitea_integration.yaml` and
`17_configure_discovery.yaml` in that order. It is not installed on its own.

`20_redeploy.yaml` rebuilds the image and redeploys code-server on a running
installation. It runs the same playbooks except `13_clone_repositories.yaml`,
so the repositories in the workspace are left untouched. It restarts the
code-server pod, so it must not run from inside code-server; thinkube-control
runs it (`redeploy_code_server`).

## Overview

Code Server provides a full VS Code experience in the browser, allowing developers to:
- Write and edit code from any device
- Access the shared code directory used by AI applications
- Integrate with Git repositories (GitHub and Gitea)
- Trigger CI/CD pipelines through Argo Workflows

## Architecture

```
User → Browser → Code Server → OAuth2 Proxy → Keycloak
                      ↓
              Shared Code Directory ← JupyterHub
                      ↓
                Git Push → Gitea/GitHub
                      ↓
                Argo Workflows → Container Build → Deployment
```

## Components

1. **Code Server** - VS Code in the browser
2. **OAuth2 Proxy** - Authentication layer
3. **Valkey** - Redis-compatible session storage (BSD licensed)
4. **Keycloak Integration** - SSO authentication
5. **Development Tools** - Node.js, Claude Code, Python, Ansible
6. **Gitea Integration** - CI/CD with Gitea Actions

## Deployment

### Prerequisites

1. Keycloak must be deployed
2. The wildcard TLS certificate must be in the default namespace
3. Harbor registry must be available
4. Set environment variable:
   ```bash
   export ADMIN_PASSWORD='your-admin-password'
   ```

### Deploy Code Server

```bash
cd ~/thinkube

# Option 1: Full installation (recommended)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/00_install.yaml

# Option 2: Individual steps
# Deploy Code Server with OAuth2 authentication
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/10_deploy.yaml

# Clone the platform and template repositories into the workspace.
# Resets existing clones to origin: uncommitted work in them is lost.
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/13_clone_repositories.yaml

# Configure the shells (bash, zsh, fish) in the container
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/14_configure_shell.yaml

# Configure environment (Node.js, Claude, Python, Ansible)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/15_configure_environment.yaml

# Configure Gitea integration (git config, example workflows, SSH key)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/16_configure_gitea_integration.yaml

# Quick refresh of the configuration without a redeploy
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/16_refresh_config.yaml

# Configure service discovery
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/17_configure_discovery.yaml

# Test the deployment
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/18_test.yaml
```

### Rollback

```bash
# Remove Code Server and all resources
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/19_rollback.yaml
```

## Configuration

### Shared Code Directory

The deployment uses a shared code directory that is accessible from:
- Code Server (for development)
- JupyterHub (for AI notebooks)

Default location: `/home/{{ system_username }}/shared-code`

### Authentication

- Uses Keycloak for SSO
- OAuth2 Proxy handles the authentication flow
- Users need the `code-server-admin` or `code-server-user` role
- Admin user is automatically granted access during deployment

### Resource Limits

Default resource allocation:
- CPU: 100m request, 4 CPU limit
- Memory: 512Mi request, 8Gi limit
- Adjust in the deployment playbook if needed

## CI/CD Integration

### Gitea Integration

`15_configure_environment.yaml` writes the Argo CLI configuration in the
container (`~/.config/argo/config`).

`16_configure_gitea_integration.yaml` sets up:
1. A `.gitconfig` with the Gitea admin token
2. Example Gitea Actions workflows (Python, Node.js) and an Argo Workflow example
3. Scripts to create Gitea repositories and set up workflows
4. The code-server SSH public key in `authorized_keys` on the control plane nodes

### Recommended Approach (Gitea Runner)

For better CI/CD integration, consider deploying Gitea Runner:
1. Native Gitea Actions support
2. GitHub Actions compatible workflows
3. No file monitoring needed
4. Direct webhook triggers

To implement Gitea Runner:
```yaml
# In your repository: .gitea/workflows/build.yaml
name: Build and Deploy
on: [push]
jobs:
  build:
    runs-on: gitea-runner
    steps:
      - uses: actions/checkout@v3
      - name: Trigger Argo Workflow
        run: |
          argo submit --from workflowtemplate/build-template
```

## Access

Once deployed, Code Server is available at:
- URL: `https://ide.<domain_name>` (`code_server_hostname` in `10_deploy.yaml`)
- Login: Via Keycloak SSO
- Users: Any user with assigned roles

## Troubleshooting

### Check Pod Status
```bash
kubectl -n code-server get pods
kubectl -n code-server logs deployment/code-server
```

### OAuth2 Proxy Issues
```bash
kubectl -n code-server logs deployment/oauth2-proxy
kubectl -n code-server get secret code-server-oauth-secret -o yaml
```

## Next Steps

1. **Deploy Gitea Runner** for better CI/CD integration
2. **Configure Git** repositories in the shared code directory
3. **Install Extensions** in Code Server for your development needs
4. **Set up Templates** for common project types

## Related Components

- **Gitea** - Git repository hosting
- **Argo Workflows** - CI/CD pipeline execution
- **Harbor** - Container registry
- **ArgoCD** - GitOps deployment