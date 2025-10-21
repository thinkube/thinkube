# DevPi Deployment

DevPi is a private Python package index server used for hosting internal Python packages and caching PyPI packages in the Thinkube platform.

## Overview

This deployment provides:
- Private Python package repository
- PyPI package caching
- Web UI with Keycloak authentication
- Unauthenticated API access for pip/CLI tools
- Automated container builds via Argo Workflows
- GitOps deployment through ArgoCD
- Fish shell integration for developers

## Architecture

### Components
- **DevPi Server**: The main package index server
- **OAuth2 Proxy**: Provides Keycloak authentication for web UI
- **Redis**: Session storage for OAuth2 Proxy
- **Ingress**: Dual ingress configuration
  - Protected dashboard: `devpi.{{ domain_name }}`
  - Open API endpoint: `devpi-api.{{ domain_name }}`

### Container Build Pipeline
1. GitHub repository stores Dockerfile and Kubernetes manifests
2. Argo Workflows builds containers using Kaniko
3. Images pushed to Harbor registry
4. ArgoCD syncs deployments from GitHub

## Prerequisites

- MicroK8s cluster (CORE-001, CORE-002)
- Cert-Manager (CORE-003)
- Keycloak (CORE-004)
- Harbor Registry (CORE-005)
- Argo Workflows (CORE-008)
- ArgoCD (CORE-009)

## Environment Variables

Required environment variables:
- `ADMIN_PASSWORD`: Admin password for Keycloak and Harbor access
- `DEVPI_ADMIN_PASSWORD`: Password for DevPi admin user

## Deployment

### 1. Set Environment Variables
```bash
export ADMIN_PASSWORD='your-admin-password'
export DEVPI_ADMIN_PASSWORD='your-devpi-password'
```

### 2. Deploy DevPi
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/devpi/10_deploy.yaml
```

### 3. Configure CLI Tools
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/devpi/15_configure_cli.yaml
```

### 4. Initialize DevPi
After deployment, initialize the admin user and default index:
```bash
fish -c "devpi-init-admin"
```

Or using bash:
```bash
~/devpi-scripts/devpi-init-admin.sh
```

## Usage

### Web Interface
Access the web interface at: https://devpi.{{ domain_name }}
- Protected by Keycloak authentication
- Browse packages and indices
- View package documentation

### API Access
The API endpoint at https://devpi-api.{{ domain_name }} is unauthenticated for pip access.

### CLI Commands

#### Configure pip to use DevPi
```bash
pip config set global.index-url https://devpi-api.{{ domain_name }}/{{ admin_username }}/prod/+simple/
```

#### Upload a package
```bash
cd your-package-directory
devpi upload
```

#### Install from DevPi
```bash
pip install your-package
```

### Fish Shell Functions

The following functions are available in fish shell:

- `devpi-env`: Display current DevPi configuration
- `devpi-init-admin`: Initialize admin user and create default index
- `devpi-upload-pkg`: Upload a package file

## Testing

Run the test playbook to verify deployment:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/devpi/18_test.yaml
```

## Rollback

To completely remove DevPi:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/devpi/19_rollback.yaml
```

## Inventory Variables

The following variables must be defined in inventory:

| Variable | Description | Example |
|----------|-------------|---------|
| `devpi_namespace` | Kubernetes namespace | `devpi` |
| `devpi_dashboard_hostname` | Dashboard hostname | `devpi.thinkube.com` |
| `devpi_api_hostname` | API endpoint hostname | `devpi-api.thinkube.com` |
| `devpi_index_name` | Default index name | `prod` |
| `github_org` | GitHub organization | `thinkube` |
| `harbor_registry` | Harbor registry domain | `registry.thinkube.com` |
| `harbor_project` | Harbor project name | `thinkube` |

## Security Considerations

- Web UI protected by Keycloak OIDC authentication
- API endpoint is intentionally unauthenticated for pip compatibility
- All traffic uses HTTPS with valid certificates
- OAuth2 sessions stored in Redis
- Container images stored in private Harbor registry

## Troubleshooting

### Check pod status
```bash
kubectl get pods -n devpi
```

### View logs
```bash
kubectl logs -n devpi deploy/devpi
kubectl logs -n devpi deploy/oauth2-proxy
```

### Verify ingress
```bash
kubectl get ingress -n devpi
```

### Test API connectivity
```bash
curl -I https://devpi-api.{{ domain_name }}/+api
```

## Notes

- The dual ingress configuration is critical for pip functionality
- DevPi data is persisted in a 5Gi PVC
- Resource limits are set to 4Gi memory and 2 CPU cores
- Session cookies use SameSite=none for cross-origin requests