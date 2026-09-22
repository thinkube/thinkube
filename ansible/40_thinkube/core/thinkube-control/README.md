# Thinkube Control

Thinkube Control is the central management interface for the Thinkube platform. It provides an API, a web interface and an MCP (Model Context Protocol) server for platform management.

## Installation

Thinkube Control is a core component. The Thinkube installer installs it by
running `00_install.yaml`, which runs the playbooks listed under Deployment
Order. It is not installed on its own.

## Architecture

The control system consists of:
- **Frontend**: React application
- **Backend**: FastAPI application with Keycloak integration and an MCP server
- **Authentication**: OAuth2 Proxy with Keycloak OIDC
- **Session Management**: Redis for OAuth2 session storage
- **Build System**: Argo Workflows with Kaniko
- **Deployment**: GitOps via ArgoCD, synced from Gitea on request: harbor-webhook-adapter commits a build's image tags and calls argocd-sync-webhook

## GitOps Workflow

Thinkube Control demonstrates the platform's GitOps pattern:

1. **Source Code**: Stored in GitHub with `.jinja` templates
2. **Templates**: Use variables like `{{ domain_name }}` for portability
3. **Processing**: Ansible processes templates during deployment
4. **Gitea Repository**: Hosts processed manifests with actual domain values
5. **ArgoCD**: Deploys from Gitea, not GitHub

This enables domain-specific deployments while maintaining upstream compatibility.

## Prerequisites

Before deploying the control system, ensure the following components are deployed:
- CORE-004: SSL/TLS Certificates (wildcard certificate in default namespace)
- CORE-006: Keycloak (authentication provider)
- CORE-007: MLflow (model registry with OIDC authentication)
- CORE-008: JupyterHub (notebook environment)
- CORE-010: Argo Workflows (for container builds)
- CORE-011: ArgoCD (for GitOps deployment)
- CORE-014: Gitea (for hosting processed manifests)
- GitHub token configured in inventory or environment

**Note**: Thinkube Control must be deployed AFTER MLflow and JupyterHub because it requires the MLflow OAuth2 client secret for model mirroring workflows.

## Deployment

Deploy the control system using the orchestrator:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/thinkube-control/00_install.yaml
```

### Deployment Order

The orchestrator runs playbooks in this sequence:

1. `10_deploy_sync_webhook.yaml` - Deploy ArgoCD sync webhook
2. `11_deploy_webhook_adapter.yaml` - Deploy Harbor webhook adapter (bootstrap mode)
3. `12_deploy.yaml` - Main thinkube-control deployment
4. `13_configure_code_server.yaml` - Configure code-server with the API token and the Claude Code MCP integration
5. `14_deploy_tk_package_version.yaml` - Deploy the tk-package-version MCP server
6. `16_publish_packages.yaml` - Build the thinkube Python packages and publish them to DevPI

Other playbooks in this folder are not run by the installer:
`12_deploy_dev.yaml` and `12_deploy_dev_test.yaml` (development helpers),
`15_update_manifests.yaml` (update manifests only), `18_test.yaml` and
`19_rollback.yaml`.

Note: The webhook adapters deploy first to enable the GitOps workflow for thinkube-control itself.

The deployment process:
1. Deploy webhook infrastructure (Harbor adapter and ArgoCD sync webhook)
2. Create the `thinkube-control` namespace
3. Copy TLS certificates from the default namespace
4. Deploy Redis for session storage
5. Configure Keycloak client for OIDC authentication
6. Deploy OAuth2 Proxy for authentication
7. Create MLflow authentication config secret in argo namespace (for model mirroring)
8. Clone source from GitHub repository
9. Process `.jinja` templates with domain values
10. Push to Gitea (triggers Argo Workflow via webhook)
11. Wait for container images to be built
12. Deploy frontend and backend via ArgoCD from Gitea
13. Configure code-server integration

## Testing

Verify the deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/thinkube-control/18_test.yaml
```

Tests include:
- Namespace and resource verification
- Service connectivity checks
- ArgoCD application status
- OAuth2 Proxy health
- DNS resolution
- HTTPS endpoint accessibility

## Access

Once deployed, the control interface is accessible at:
- URL: `https://control.<domain_name>`
- Authentication: Via Keycloak SSO
- Authorized users: Admin user configured during deployment

## Components

### OAuth2 Proxy
- Handles authentication with Keycloak
- Manages user sessions in Redis
- Protects control endpoints

### Redis
- Ephemeral Redis deployment
- Stores OAuth2 session data
- No persistence required

### MLflow Authentication

Thinkube Control integrates with MLflow for AI model mirroring. The authentication flow is:

**Initial Setup (First-Time User Experience)**:
1. User navigates to AI Models page in Thinkube Control
2. Backend checks MLflow status via `/api/models/mlflow/status` endpoint
3. If user hasn't initialized MLflow, frontend displays initialization banner
4. User clicks "Initialize MLflow" button to open MLflow in browser
5. User logs in via Keycloak OAuth2 (creates user in MLflow database)
6. Frontend auto-rechecks status after 3 seconds
7. Once initialized, banner disappears and model mirroring is available

**Programmatic Authentication (Model Download Workflows)**:
1. Argo Workflow reads credentials from the `mlflow-auth-config` secret (argo namespace)
2. Workflow fetches OAuth2 access token from Keycloak using Resource Owner Password Credentials flow:
   - `grant_type: password`
   - `client_id: mlflow`
   - `client_secret: <from secret>`
   - `username: <realm username>`
   - `password: <admin password>`
3. Sets `MLFLOW_TRACKING_TOKEN` environment variable with access token
4. MLflow Python SDK uses token for authenticated API calls

**Secret Creation**:
`12_deploy.yaml` creates the `mlflow-auth-config` secret in two namespaces,
`argo` and `thinkube-control` (step 7 above). It contains:
- `keycloak-token-url`: Keycloak OAuth2 token endpoint (`{{ keycloak_url }}/realms/{{ auth_realm_username }}/protocol/openid-connect/token`)
- `client-id`: MLflow OAuth2 client ID (`mlflow`)
- `client-secret`: MLflow OAuth2 client secret (copied from the `oauth2-proxy-secret` secret in the mlflow namespace)
- `username`: the realm user (`auth_realm_username`)
- `password`: Admin password from the `ADMIN_PASSWORD` environment variable

This approach provides seamless single-user authentication while maintaining OAuth2 security standards.

### Container Builds
- Argo Workflows builds frontend and backend images
- Kaniko used for rootless container builds
- Images pushed to Harbor registry

### GitOps Deployment
- ArgoCD manages application deployment
- Monitors Gitea repository (not GitHub) for changes
- Automatic sync and rollout
- Repository includes processed manifests with actual domain values

## Configuration

Key configuration variables:
- `domain_name`: Base domain for the platform
- `admin_username`: Admin user granted access
- `github_token`: For repository access
- `kubeconfig`: Kubernetes configuration path

## Rollback

To remove the control deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/thinkube-control/19_rollback.yaml
```

This removes all control resources including:
- ArgoCD applications
- OAuth2 Proxy and Redis
- Namespace and secrets

## Troubleshooting

### Authentication Issues
- Verify Keycloak client configuration
- Check OAuth2 Proxy logs: `kubectl logs -n thinkube-control -l app.kubernetes.io/name=oauth2-proxy`
- Ensure user has `control-user` role in Keycloak

### Build Issues
- Check Argo Workflows: `kubectl -n argo get workflows`
- Verify GitHub token is valid
- Check Kaniko service account permissions

### Deployment Issues
- Verify ArgoCD applications: `kubectl -n argocd get applications`
- Check application sync status in ArgoCD UI
- Review pod logs in the thinkube-control namespace

## Development Workflow

After deployment, the thinkube-control code is available in Gitea:

1. **Clone from Gitea**:
   ```bash
   git clone https://git.<domain_name>/thinkube-deployments/thinkube-control.git
   ```

2. **Make changes**:
   - Edit `.jinja` templates (not processed `.yaml` files)
   - Commit changes (git hook auto-processes)
   - Push to Gitea

3. **Contribute upstream**:
   - Run `./prepare-for-github.sh`
   - Push to GitHub (templates only)

## Template Structure

The deployment processes these templates:
- `k8s/*.yaml.jinja` - Kubernetes manifests
- `workflows/*.yaml.jinja` - Argo Workflow definitions

Variables replaced during processing:
- `{{ domain_name }}` - Your configured domain
- `{{ registry_subdomain }}.{{ domain_name }}` - Harbor registry URL
- `{{ namespace }}` - Kubernetes namespace
- `{{ github_username }}` - GitHub account that owns the token

## Notes

- Source code stored in GitHub at `thinkube-control/` (local subtree)
- Processed manifests pushed to Gitea for ArgoCD deployment
- Images built automatically by Argo Workflows
- Frontend and backend deployed as separate ArgoCD applications
- OAuth2 Proxy provides authentication for all access
- Git hooks ensure templates and manifests stay synchronized