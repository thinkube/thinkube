# DevPi Deployment

DevPi is a private Python package index server used for hosting internal Python packages and caching PyPI packages in the Thinkube platform.

## Installation

DevPi is a core component. The Thinkube installer installs it by running
`00_install.yaml`, which runs `10_deploy.yaml`, `15_configure_cli.yaml` and
`17_configure_discovery.yaml` in that order. It is not installed on its own.

## Overview

This deployment provides:
- Private Python package repository
- PyPI package caching
- Web UI with Keycloak authentication
- Unauthenticated API access for pip/CLI tools
- Image built with podman from https://github.com/thinkube/thinkube-devpi and pushed to Harbor
- Fish shell integration for developers

## Architecture

### Components
- **DevPi Server**: The main package index server
- **OAuth2 Proxy**: Provides Keycloak authentication for web UI
- **Valkey** (`ephemeral-redis`): Session storage for OAuth2 Proxy
- **HTTPRoutes**: Two routes
  - Protected dashboard: `packages.{{ domain_name }}` (`devpi_dashboard_hostname`)
  - Open API endpoint: `packages-api.{{ domain_name }}` (`devpi_api_hostname`)

### Container Build
`10_deploy.yaml` does not use Argo Workflows or ArgoCD:
1. Clones https://github.com/thinkube/thinkube-devpi to `/tmp/thinkube-devpi` on the control plane
2. Builds the image with podman from `dockerfile/Dockerfile`
3. Pushes it to `{{ harbor_registry }}/library/devpi:latest`
4. Applies the Kubernetes manifests with kubectl

## Prerequisites

- Kubernetes (kubeadm) cluster
- Wildcard TLS certificate (`infrastructure/acme-certificates`)
- Keycloak
- Harbor Registry, and podman on the control plane (`harbor/11_install_podman.yaml`)

## Environment Variables

Required environment variables:
- `ADMIN_PASSWORD`: Admin password for Keycloak and Harbor access

## Deployment

### 1. Set Environment Variables
```bash
export ADMIN_PASSWORD='your-admin-password'
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
Access the web interface at: https://packages.{{ domain_name }}
- Protected by Keycloak authentication
- Browse packages and indices
- View package documentation

### API Access
The API endpoint at https://packages-api.{{ domain_name }} is unauthenticated for pip access.

### CLI Commands

#### Configure pip to use DevPi
```bash
pip config set global.index-url https://packages-api.{{ domain_name }}/{{ admin_username }}/stable/+simple/
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

These are set in `inventory/group_vars/k8s.yml`:

| Variable | Description | Value |
|----------|-------------|---------|
| `devpi_namespace` | Kubernetes namespace | `devpi` |
| `devpi_dashboard_hostname` | Dashboard hostname | `packages.{{ domain_name }}` |
| `devpi_api_hostname` | API endpoint hostname | `packages-api.{{ domain_name }}` |
| `devpi_index_name` | Default index name | `stable` |
| `harbor_registry` | Harbor registry domain | `registry.{{ domain_name }}` |

The image goes to the Harbor `library` project; `10_deploy.yaml` sets
`harbor_project: library` itself.

## Security Considerations

- Web UI protected by Keycloak OIDC authentication
- API endpoint is intentionally unauthenticated for pip compatibility
- All traffic uses HTTPS with valid certificates
- OAuth2 sessions stored in Valkey
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

### Verify routes
```bash
kubectl get httproute -n devpi
```

### Test API connectivity
```bash
curl -I https://packages-api.{{ domain_name }}/+api
```

## Notes

- The two routes are critical for pip functionality: pip uses the open API hostname
- DevPi data is persisted in a 50Gi PVC (`devpi-data-pvc`)
- Resource limits are set to 4Gi memory and 2 CPU cores