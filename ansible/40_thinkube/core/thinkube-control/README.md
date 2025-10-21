# Thinkube Control

Thinkube Control is the central management interface for the Thinkube platform. It provides a unified API and web interface for platform management, with plans to evolve into an MCP (Model Context Protocol) server for LLM-based management.

## Architecture

The control system consists of:
- **Frontend**: Vue.js application with DaisyUI components
- **Backend**: FastAPI application with Keycloak integration (evolving to MCP server)
- **Authentication**: OAuth2 Proxy with Keycloak OIDC
- **Session Management**: Redis for OAuth2 session storage
- **Build System**: Argo Workflows with Kaniko
- **Deployment**: GitOps via ArgoCD watching Gitea repositories

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
- CORE-010: Argo Workflows (for container builds)
- CORE-011: ArgoCD (for GitOps deployment)
- CORE-014: Gitea (for hosting processed manifests)
- GitHub token configured in inventory or environment

## Deployment

Deploy the control system using the orchestrator:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/thinkube-control/00_install.yaml
```

### Deployment Order

The orchestrator runs playbooks in this sequence:

1. `10_deploy_webhook_adapter.yaml` - Deploy Harbor webhook adapter (bootstrap mode)
2. `11_deploy_sync_webhook.yaml` - Deploy ArgoCD sync webhook
3. `12_deploy.yaml` - Main thinkube-control deployment
4. `13_configure_code_server.yaml` - Configure code-server integration

Note: The webhook adapters deploy first to enable the GitOps workflow for thinkube-control itself. 
The webhook adapter starts in bootstrap mode and automatically enables full CI/CD monitoring once 
thinkube-control creates the required token.

The deployment process:
1. Deploy webhook infrastructure (Harbor adapter and ArgoCD sync webhook)
2. Create the `thinkube-control` namespace
3. Copy TLS certificates from the default namespace
4. Deploy Redis for session storage
5. Configure Keycloak client for OIDC authentication
6. Deploy OAuth2 Proxy for authentication
7. Clone source from GitHub repository
8. Process `.jinja` templates with domain values
9. Push to Gitea (triggers Argo Workflow via webhook)
10. Wait for container images to be built
11. Deploy frontend and backend via ArgoCD from Gitea
12. Create CI/CD monitoring token for full pipeline visibility
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
- URL: `https://control.thinkube.com`
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
- Check OAuth2 Proxy logs: `kubectl logs -n control-hub -l app.kubernetes.io/name=oauth2-proxy`
- Ensure user has `control-user` role in Keycloak

### Build Issues
- Check Argo Workflows: `kubectl -n argo get workflows`
- Verify GitHub token is valid
- Check Kaniko service account permissions

### Deployment Issues
- Verify ArgoCD applications: `kubectl -n argocd get applications`
- Check application sync status in ArgoCD UI
- Review pod logs in control-hub namespace

## Future Development

This application is designed to evolve into an MCP server that will:
- Provide LLM-friendly APIs for platform management
- Enable natural language control of Thinkube services
- Offer structured tool interfaces following the MCP specification
- Support autonomous platform operations

## Development Workflow

After deployment, the thinkube-control code is available in Gitea:

1. **Clone from Gitea**:
   ```bash
   git clone https://git.thinkube.com/thinkube-deployments/thinkube-control-deployment.git
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
- `{{ github_org }}` - GitHub organization/user

## Notes

- Source code stored in GitHub at `thinkube-control/` (local subtree)
- Processed manifests pushed to Gitea for ArgoCD deployment
- Images built automatically by Argo Workflows
- Frontend and backend deployed as separate ArgoCD applications
- OAuth2 Proxy provides authentication for all access
- Git hooks ensure templates and manifests stay synchronized