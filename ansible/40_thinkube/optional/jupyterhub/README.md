# JupyterHub

Multi-user Jupyter notebook environment for data science and development work.

## Overview

JupyterHub provides:
- Multi-user Jupyter notebook environments
- Keycloak OIDC authentication
- Custom Docker image with pre-installed packages
- Persistent storage for user data
- Shared notebook directory
- Multiple environment profiles (Default, TensorFlow, Minimal)

## Prerequisites

1. **Core Components**:
   - CORE-001: MicroK8s cluster deployed
   - CORE-002: Keycloak deployed and accessible
   - CORE-004: Harbor registry deployed

2. **Environment Variables**:
   - `HARBOR_ROBOT_TOKEN`: Harbor robot account token
   - `KEYCLOAK_ADMIN_PASSWORD`: Keycloak admin password

3. **Required Variables** (from inventory):
   - `harbor_registry`: Registry domain
   - `harbor_project`: Harbor project name
   - `domain_name`: Base domain
   - `admin_username`: Admin username
   - TLS certificate paths

## Deployment Process

### 1. Build Custom Image

Build the custom JupyterHub image with pre-installed packages:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/10_build_image.yaml
```

This creates:
- Custom JupyterHub image with data science packages
- Package management system
- Rebuild script at `~/jupyterhub-packages/rebuild_image.sh`

### 2. Configure Keycloak (Optional)

Set up Keycloak OIDC authentication:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/11_configure_keycloak.yaml
```

This creates:
- Keycloak client for JupyterHub
- OIDC secret in Kubernetes

### 3. Deploy JupyterHub

Deploy JupyterHub using Helm:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/12_deploy.yaml
```

### 4. Verify Deployment

Run tests to verify the deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/18_test.yaml
```

## Access Information

- **URL**: `https://jupyter.<domain_name>`
- **Authentication**: 
  - Keycloak OIDC (if configured)
  - Dummy authentication (fallback)

## Features

### Custom Image
The custom image includes:
- Data science libraries (pandas, scikit-learn, torch)
- AI/ML tools (transformers, spacy, openai, anthropic)
- Database connectors (minio, opensearch, postgresql)
- Development tools (black, jupyterlab-git)

### Storage
- **User notebooks**: Persistent storage per user
- **Shared notebooks**: `/home/thinkube/shared-code/notebooks` (mounted at `/home/jovyan/work`)
- **Pip cache**: Shared cache for faster package installation
- **Shared with code-server**: Both services share the same `/home/thinkube/shared-code` directory

### Environment Profiles
Users can choose from:
1. **Default Environment**: Custom image with pre-installed packages
2. **TensorFlow Environment**: Optimized for TensorFlow with GPU support
3. **Minimal Environment**: Lightweight for basic tasks

### Package Management
Users can manage their own packages:
```bash
# In JupyterLab terminal
user-package-manager.sh add pandas==2.0.0
user-package-manager.sh install
```

## Maintenance

### Rebuild Custom Image
To update the custom image:
```bash
cd ~/jupyterhub-packages
./rebuild_image.sh
```

### Rollback
To remove JupyterHub completely:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/19_rollback.yaml
```

## Troubleshooting

### Check Pod Status
```bash
microk8s.kubectl get pods -n jupyterhub
```

### View Logs
```bash
# Hub logs
microk8s.kubectl logs -n jupyterhub deployment/hub

# Proxy logs  
microk8s.kubectl logs -n jupyterhub deployment/proxy
```

### Common Issues

1. **Authentication Issues**:
   - Verify Keycloak client is configured
   - Check OIDC secret exists: `kubectl get secret -n jupyterhub jupyterhub-oidc-secret`

2. **Image Pull Errors**:
   - Verify Harbor credentials: `kubectl get secret -n jupyterhub harbor-registry-credentials`
   - Check HARBOR_ROBOT_TOKEN is set

3. **Storage Issues**:
   - Check PVC status: `kubectl get pvc -n jupyterhub`
   - Verify directory permissions on host

## Notes

- Network policies are removed to allow unrestricted connectivity
- WebSocket support is configured for notebook interactions
- Node affinity ensures pods run on same node as code-server for shared directory access
- Both JupyterHub and code-server share `/home/thinkube/shared-code` directory
- Custom image is rebuilt separately from deployment