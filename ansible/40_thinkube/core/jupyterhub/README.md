# JupyterHub with Dynamic Image Discovery

Fast-deploying Jupyter notebook environment with GPU flexibility, SeaweedFS storage, and dynamic image discovery from thinkube-control.

## Overview

JupyterHub deployment features:
- **Fast Deployment**: 2 minutes (images built separately)
- **GPU Flexibility**: Notebooks run on any GPU node
- **Mandatory Dependencies**: Keycloak, SeaweedFS, thinkube-control (no fallbacks)
- **Dynamic Discovery**: Images queried from thinkube-control at runtime
- **Hybrid Storage**: SeaweedFS persistence + local scratch performance
- **No Conditionals**: Fails fast if dependencies unavailable

## Architecture

### Volume Mount Strategy

The JupyterHub deployment uses a specific volume mount architecture to preserve Python packages installed in Docker images while providing persistent storage:

```
/home/jovyan/                    # User home (NOT mounted - preserves .local/bin/)
├── .local/                      # Python packages from image (preserved)
│   └── bin/                     # Contains jupyterhub-singleuser binary
├── .thinkube_env                # Environment variables (from image)
└── thinkube/                    # Mount point for persistent volumes
    └── notebooks/               # User's persistent storage
        ├── templates/           # Read-only examples (symlink to /opt/thinkube/examples)
        ├── examples/            # Editable copies of examples
        │   ├── tk-jupyter-ml-cpu/     # CPU image examples
        │   ├── tk-jupyter-ml-gpu/     # GPU image examples
        │   └── tk-jupyter-scipy/      # SciPy image examples
        ├── datasets/            # Shared datasets (500GB)
        └── models/              # Shared models (200GB)
```

**Key Design Decisions:**
- Volumes mount at `/home/jovyan/thinkube/` subdirectories, NOT at `/home/jovyan/`
- This preserves the `.local/` directory containing Python packages
- No separate home PVC - simplifies architecture
- Each image type gets its own examples folder to prevent conflicts

### Why This Architecture?

The critical issue: Docker's overlay filesystem behavior when mounting volumes:
- If we mount at `/home/jovyan/`, it hides everything in that directory from the image
- This includes `/home/jovyan/.local/bin/` where `jupyterhub-singleuser` is installed
- Result: "jupyterhub-singleuser: not found" errors and pod startup failures

The solution: Mount at subdirectories under `/home/jovyan/thinkube/`:
- Preserves all image-installed packages in `.local/`
- Provides persistent storage for user work
- Maintains clean separation between image content and user data

## Docker Images

All images use `--user` installation to install packages in `/home/jovyan/.local/`:

1. **tk-jupyter-scipy** - Scientific Python computing
   - Base: jupyter/scipy-notebook:latest
   - Python: 3.12
   - Includes: NumPy, Pandas, Matplotlib, Seaborn, Scikit-learn
   - All Thinkube service clients

2. **tk-jupyter-ml-cpu** - Machine Learning without GPU
   - Base: Ubuntu 24.04 (built from scratch)
   - Python: 3.12
   - PyTorch CPU: 2.5.1+cpu with CPU-optimized binaries
   - Includes: Transformers, Datasets, Accelerate
   - All Thinkube service clients (PostgreSQL, Redis, Qdrant, OpenSearch, MLflow, etc.)

3. **tk-jupyter-ml-gpu** - Machine Learning with CUDA
   - Base: NVIDIA CUDA 12.6 with cuDNN
   - Python: 3.12
   - PyTorch: 2.5.1 with CUDA 12.6 support
   - Includes: Transformers, Datasets, Accelerate
   - All Thinkube service clients

### Package Management

All packages are pinned to specific versions for reproducibility:
- JupyterLab: 4.4.9
- JupyterHub: 5.3.0 (required for jupyterhub-singleuser command)
- PyTorch: 2.5.1 (GPU) / 2.5.1+cpu (CPU)
- Transformers: 4.56.2
- See Dockerfiles for complete version list

## Prerequisites

1. **Core Components**:
   - CORE-001: Kubernetes (k8s-snap) cluster with GPU operator (if using GPUs)
   - CORE-002: Keycloak deployed (mandatory for authentication)
   - CORE-004: Harbor registry deployed
   - SeaweedFS deployed with CSI driver
   - TLS certificates configured

2. **Environment Variables**:
   - `HARBOR_ROBOT_TOKEN`: Harbor robot account token
   - `KEYCLOAK_ADMIN_PASSWORD`: Keycloak admin password

3. **Required Variables** (from inventory):
   - `harbor_registry`: Registry domain
   - `domain_name`: Base domain
   - `admin_username`: Admin username
   - `system_username`: System user

## Examples Repository

JupyterHub uses a public GitHub repository for example notebooks:
- **Repository**: https://github.com/thinkube/thinkube-ai-examples
- **Structure**: Organized by image type (common, ml-cpu, ml-gpu, fine-tuning, agent-dev)
- **Auto-sync**: Examples updated daily via CronJob
- **Fail-fast**: Deployment fails if examples repository unavailable

### Examples Architecture

```
/home/jovyan/thinkube/
├── examples-repo/          # Read-only mount of cloned repository
│   └── thinkube-ai-examples/
│       ├── common/         # Examples for all images
│       ├── ml-cpu/        # CPU-specific examples
│       ├── ml-gpu/        # GPU-specific examples
│       ├── fine-tuning/   # Fine-tuning examples
│       └── agent-dev/     # Agent development examples
├── notebooks/
│   ├── templates/         # Symlink to examples-repo (read-only)
│   └── examples/          # Editable copies per image type
└── ...
```

### Managing Examples

**For maintainers updating examples**:
1. Clone repository: `git clone https://github.com/thinkube/thinkube-ai-examples.git`
2. Edit notebooks (outputs must be stripped)
3. Clean notebooks: `nbstripout notebook.ipynb`
4. Validate: `./scripts/validate_notebooks.sh`
5. Commit and push to GitHub
6. Examples auto-sync daily, or trigger manually:
   ```bash
   kubectl create job --from=cronjob/thinkube-ai-examples-sync manual-sync -n jupyterhub
   ```

**Cleaning tools (required before commit)**:
```bash
# Install tools
pip install nbstripout pre-commit

# Install pre-commit hooks (auto-cleans on commit)
cd thinkube-ai-examples
pre-commit install

# Manual cleaning
nbstripout notebook.ipynb

# Validate all notebooks are clean
./scripts/validate_notebooks.sh
```

## Deployment Process

### 1. Build Custom ML/AI Images

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/14_build_base_images.yaml
```

This builds and pushes all Jupyter images to Harbor registry.

### 2. Deploy JupyterHub

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/11_deploy.yaml
```

This will:
- Retrieve OIDC secret from existing Keycloak configuration
- Create SeaweedFS volumes for persistent storage (notebooks, datasets, models)
- Deploy JupyterHub with dynamic image discovery
- Configure volume mounts at `/home/jovyan/thinkube/` to preserve packages
- Set up Ingress for external access

**Note**: Keycloak must already be configured with the JupyterHub client. The deployment retrieves the existing OIDC secret.

### 3. Configure Examples Auto-Sync

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/12_configure_examples_sync.yaml
```

This creates:
- CronJob for daily sync of examples repository
- Manual trigger capability for immediate updates

### 4. Verify Deployment

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/18_test.yaml
```

This verifies:
- SeaweedFS volume accessibility
- Examples repository availability
- Custom image availability
- GPU detection (if available)
- Service health
- Authentication configuration

## Access Information

- **URL**: `https://jupyter.<domain_name>`
- **Authentication**: Keycloak SSO (mandatory)
- **Admin User**: `<admin_username>` from inventory

## Usage

### Profile Selection

JupyterHub dynamically discovers available images from thinkube-control. Users can choose from:

- **tk-jupyter-scipy** - Scientific computing with SciPy stack
- **tk-jupyter-ml-cpu** - Machine learning development (CPU-optimized PyTorch)
- **tk-jupyter-ml-gpu** - Deep learning with GPU acceleration (CUDA PyTorch)

### Working with Storage

#### Directory Structure
```
/home/jovyan/thinkube/
├── examples-repo/              # Read-only cloned repository
│   └── thinkube-ai-examples/
│       ├── common/             # Examples for all images
│       ├── ml-cpu/
│       ├── ml-gpu/
│       ├── fine-tuning/
│       └── agent-dev/
├── notebooks/
│   ├── templates/              # Symlink to examples-repo (read-only)
│   ├── examples/               # Your editable copies (per image type)
│   │   ├── tk-jupyter-ml-cpu/
│   │   ├── tk-jupyter-ml-gpu/
│   │   ├── tk-jupyter-fine-tuning/
│   │   └── tk-jupyter-agent-dev/
│   ├── projects/               # Your project notebooks
│   └── experiments/            # Experimental work
├── datasets/                   # Shared datasets (500GB SeaweedFS)
└── models/                     # Trained models (200GB SeaweedFS)
```

#### Persistent Storage (SeaweedFS)
- `/home/jovyan/thinkube/notebooks` - Your notebooks and work (100GB)
- `/home/jovyan/thinkube/datasets` - Shared datasets across all pods
- `/home/jovyan/thinkube/models` - Saved models accessible from any pod

#### Environment Variables
- `.thinkube_env` - Automatically sourced, contains service endpoints

### Example Workflows

1. **GPU Training with PyTorch**:
   - Select `tk-jupyter-ml-gpu` image
   - Work in `/home/jovyan/thinkube/notebooks/`
   - Load datasets from `/home/jovyan/thinkube/datasets/`
   - Save models to `/home/jovyan/thinkube/models/`
   - Example notebooks in `/home/jovyan/thinkube/notebooks/templates/`

2. **CPU-based ML Development**:
   - Select `tk-jupyter-ml-cpu` image (optimized PyTorch CPU binaries)
   - Develop in `/home/jovyan/thinkube/notebooks/`
   - Use transformers and datasets libraries
   - Connect to Thinkube services via environment variables

3. **Scientific Computing**:
   - Select `tk-jupyter-scipy` image
   - Use NumPy, Pandas, Matplotlib for analysis
   - Save results to persistent notebooks directory

## Maintenance

### Rebuild Images

To update the Jupyter images:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor/14_build_base_images.yaml
```

Images are automatically discovered by JupyterHub from thinkube-control.

### Rollback

To remove JupyterHub completely:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/19_rollback.yaml
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n jupyterhub
```

### View Logs
```bash
# Hub logs
kubectl logs -n jupyterhub deployment/hub

# Proxy logs
kubectl logs -n jupyterhub deployment/proxy

# User pod logs
kubectl logs -n jupyterhub jupyter-<username>
```

### Common Issues

1. **"jupyterhub-singleuser: not found" Error**:
   - **Cause**: Volume mounted at `/home/jovyan/` hides `.local/bin/`
   - **Solution**: Ensure volumes mount at `/home/jovyan/thinkube/` subdirectories
   - Verify Dockerfiles use `--user` installation, not system-wide
   - Check that jupyterhub package is installed in the image

2. **Storage Not Accessible**:
   - Verify SeaweedFS is running: `kubectl get pods -n seaweedfs`
   - Check CSI driver: `kubectl get pods -n seaweedfs-csi`
   - Ensure PVCs are bound: `kubectl get pvc -n jupyterhub`

3. **GPU Not Available**:
   - Check GPU operator: `kubectl get pods -n gpu-operator`
   - Verify node labels: `kubectl get nodes --show-labels | grep nvidia`
   - Check resource allocation: `kubectl describe node <gpu-node>`

4. **Image Pull Errors**:
   - Verify Harbor connectivity: `curl -k https://registry.<domain>/api/v2.0/health`
   - Check image exists in Harbor: `registry.<domain>/library/tk-jupyter-*`
   - Verify images are properly pushed during build

5. **Authentication Issues**:
   - Check Keycloak is running: `kubectl get pods -n keycloak`
   - Verify OIDC secret exists: `kubectl get secret -n jupyterhub jupyterhub-oidc-secret`
   - Check Keycloak client configuration in Keycloak admin console

6. **Examples Not Available**:
   - Verify examples repository cloned: `kubectl logs -n jupyterhub job/clone-thinkube-ai-examples`
   - Check examples PVC exists: `kubectl get pvc -n jupyterhub jupyterhub-examples-pvc`
   - Verify sync job: `kubectl get cronjobs -n jupyterhub thinkube-ai-examples-sync`
   - Check pod startup logs for examples copying
   - Manual sync: `kubectl create job --from=cronjob/thinkube-ai-examples-sync manual-sync -n jupyterhub`

7. **Examples Out of Date**:
   - Trigger manual sync: `kubectl create job --from=cronjob/thinkube-ai-examples-sync manual-sync -n jupyterhub`
   - Check sync job logs: `kubectl logs -n jupyterhub job/manual-sync`
   - Verify CronJob schedule: `kubectl get cronjob -n jupyterhub thinkube-ai-examples-sync -o yaml`

## Performance Considerations

- **SeaweedFS**: Optimized for small files (notebooks), may be slower for large datasets
- **Scratch Space**: Use `/home/jovyan/scratch/` for temporary large files requiring fast I/O
- **GPU Scheduling**: Auto-select profile uses Kubernetes scheduler for optimal placement
- **Image Sizes**: GPU images are large (~10GB), initial pull may take time

## Security Notes

- Keycloak provides mandatory SSO authentication
- All traffic is TLS-encrypted via ingress
- Shared-code mount is read-only to prevent accidental modifications
- No fallback authentication - if Keycloak is down, JupyterHub is inaccessible

## Architecture Benefits

The examples repository and volume mount strategy provides:

1. **Decoupled Updates**: Examples updated without rebuilding Docker images
2. **Version Control**: Public GitHub repository enables community contributions
3. **Auto-Sync**: Daily updates keep examples fresh automatically
4. **Fail-Fast**: Deployment fails immediately if dependencies unavailable
5. **Image-Aware**: Each image type gets relevant examples only
6. **Package Preservation**: Python packages in `.local/` remain accessible
7. **Clean Separation**: Image content and user data don't conflict
8. **Multi-Image Support**: Different images can coexist without conflicts
9. **Persistence**: SeaweedFS ensures notebooks survive pod restarts
10. **Dynamic Discovery**: New images automatically available without config changes

## License

Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
SPDX-License-Identifier: Apache-2.0