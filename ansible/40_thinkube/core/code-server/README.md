# Code Server Deployment

VS Code in the browser for cloud-based development, integrated with Thinkube platform.

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

1. Keycloak must be deployed (CORE-006)
2. TLS certificates must be configured (CORE-004)
3. Harbor registry must be available (CORE-005)
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

# Configure environment (Node.js, Claude, Python, Ansible)
./scripts/run_ansible.sh ansible/40_thinkube/core/code-server/15_configure_environment.yaml

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
- Repository monitor service

Default location: `/home/thinkube/shared-code`

### Authentication

- Uses Keycloak for SSO
- OAuth2 Proxy handles the authentication flow
- Users need the `code-server-admin` or `code-server-user` role
- Admin user is automatically granted access during deployment

### Resource Limits

Default resource allocation:
- CPU: 500m request, 2 CPU limit
- Memory: 2Gi request, 4Gi limit
- Adjust in the deployment playbook if needed

## CI/CD Integration

### Current Approach (File Monitoring)

The `15_configure.yaml` playbook sets up:
1. Argo CLI in Code Server
2. Repository monitor service that watches for commit files
3. Automatic workflow submission to Argo Workflows

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
- URL: `https://code.thinkube.com`
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

### Repository Monitor
```bash
sudo systemctl status repo-monitor
sudo journalctl -u repo-monitor -f
```

## Next Steps

1. **Deploy Gitea Runner** for better CI/CD integration
2. **Configure Git** repositories in the shared code directory
3. **Install Extensions** in Code Server for your development needs
4. **Set up Templates** for common project types

## Related Components

- **Gitea** (CORE-008) - Git repository hosting
- **Argo Workflows** (CORE-010) - CI/CD pipeline execution
- **Harbor** (CORE-005) - Container registry
- **ArgoCD** (CORE-011) - GitOps deployment

---
*Component of the Thinkube Platform - Optional Services*