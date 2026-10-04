# JupyterHub

Fast-deploying Jupyter notebook environment with GPU flexibility, JuiceFS storage, and runtime configuration from thinkube-control.

## Installation

JupyterHub is a core component. The Thinkube installer installs it by running
`00_install.yaml`, which runs `10_configure_keycloak.yaml`, `11_deploy.yaml`,
`16_configure_code_server_storage.yaml` and `17_configure_discovery.yaml` in
that order. It is not installed on its own. `99_build_venvs.yaml` is not part
of the install: maintainers run it to build new venv releases.

## Overview

JupyterHub deployment features:
- **Fast Deployment**: 2 minutes (images built separately)
- **GPU Flexibility**: Notebooks run on any GPU node
- **Mandatory Dependencies**: Keycloak, JuiceFS, thinkube-control (no fallbacks)
- **Dynamic Discovery**: Cluster resources and JupyterHub configuration queried from thinkube-control at spawn time
- **Hybrid Storage**: JuiceFS persistence + local scratch and venvs for performance
- **No Conditionals**: Fails fast if dependencies unavailable

## Architecture

### Volume Mount Strategy

The notebook image runs as user `thinkube` (UID 1000) with home
`/home/thinkube/`. Volumes mount at subdirectories. The home folder itself is
never mounted over:

```
/home/thinkube/                  # User home (NOT mounted - keeps image content)
├── .local/  .config/  .cache/   # Created in the image, owned by the user; ~/.local/bin is on PATH
├── .config/thinkube/            # Service discovery env file (emptyDir, written by an init container)
├── venvs/                       # Python venvs (hostPath /var/lib/jupyterhub-venvs on each node)
├── scratch/                     # Local scratch (emptyDir, 100Gi limit)
└── thinkube/
    ├── notebooks/               # User's persistent storage (JuiceFS, 100Gi)
    │   └── examples/            # Editable copies of examples (copied once)
    ├── templates/               # Examples repository (emptyDir, re-cloned on every start)
    ├── datasets/                # Shared datasets (JuiceFS, 500Gi)
    ├── models/                  # Shared models (JuiceFS, 200Gi)
    └── mlflow/                  # MLflow artifacts (same JuiceFS volume MLflow writes to)
```

**Key Design Decisions:**
- Volumes mount at `/home/thinkube/thinkube/` subdirectories (and `venvs/`, `scratch/`), NOT at `/home/thinkube/`
- This preserves what the image puts in the home folder
- No separate home PVC - simplifies architecture. User settings in the home folder last only until the server stops.

### Why This Architecture?

A volume mounted over a directory hides everything the image put in that
directory:
- If a volume is mounted at the home folder, it hides `~/.local/`, `~/.config/` and `~/.cache/` from the image
- Anything installed there is lost; a command installed in `~/.local/bin/` is no longer found
- In older images `jupyterhub-singleuser` was installed in `~/.local/bin/`. Mounting over the home folder then gave "jupyterhub-singleuser: not found" errors and pod startup failures
- `tk-jupyter-base` installs JupyterLab and JupyterHub in the system Python. The home rule still holds for the rest of the home folder
- Kubernetes creates any missing parent of a mount as root. So the image creates `~/.config`, `~/.cache` and `~/.local/share` owned by the user before anything mounts beneath them

The solution: Mount at subdirectories under `/home/thinkube/thinkube/`:
- Preserves all image content in the home folder
- Provides persistent storage for user work
- Maintains clean separation between image content and user data

## Notebook Image and Venvs

JupyterHub uses one image, `tk-jupyter-base`, built by
`../harbor-images/15_build_jupyter_images.yaml`:
- Base: NVIDIA PyTorch from NGC
- JupyterLab 4.5.0 and JupyterHub 5.3.0 (required for the jupyterhub-singleuser command), installed in the system Python

ML packages are not in the image. They live in Python venvs:
- An init container, `setup-venvs`, downloads the `fine-tuning` and `agent-dev` venvs for the node's architecture from https://github.com/thinkube/thinkube-venvs/releases (version `jupyter_venvs_version`, set in `vars/venvs.yaml`) and registers them as Jupyter kernels
- The venvs are kept on each node at `/var/lib/jupyterhub-venvs` and mounted at `/home/thinkube/venvs`
- `99_build_venvs.yaml` builds new venv tarballs for every GPU architecture in the cluster and uploads them to a GitHub release (needs `gh` authenticated). The package list is `venv-packages.txt`

## Prerequisites

1. **Core Components**:
   - Kubernetes (kubeadm) cluster with GPU operator (if using GPUs)
   - Keycloak deployed (mandatory for authentication)
   - Harbor registry deployed, with `tk-jupyter-base` built
   - JuiceFS deployed (`juicefs-rwx` StorageClass and the MLflow volume)
   - thinkube-control running
   - TLS certificates configured

2. **Environment Variables**:
   - `ADMIN_PASSWORD`: Keycloak admin password

3. **Required Variables** (from inventory):
   - `harbor_registry`: Registry domain
   - `domain_name`: Base domain
   - `admin_username`: Admin username
   - `system_username`: System user

## Examples Repository

JupyterHub uses a public GitHub repository for example notebooks:
- **Repository**: https://github.com/thinkube/thinkube-notebooks-examples
- **Auto-sync**: Cloned again on every pod start by the `clone-templates` init container
- **Fail-fast**: Deployment fails if examples repository unavailable

### Examples Architecture

```
/home/thinkube/thinkube/
├── templates/             # Repository contents (emptyDir, re-cloned on every start)
│   └── examples/
└── notebooks/
    └── examples/          # Editable copies, made once (guarded by .copied)
```

### Managing Examples

**For maintainers updating examples**:
1. Clone repository: `git clone https://github.com/thinkube/thinkube-notebooks-examples.git`
2. Edit notebooks (outputs must be stripped)
3. Clean notebooks: `nbstripout notebook.ipynb`
4. Validate: `./scripts/validate_notebooks.sh`
5. Commit and push to GitHub
6. Push to GitHub. Every notebook server picks the change up the next time it
   starts: the `clone-templates` init container re-clones the repository into
   `~/thinkube/templates/`, which is an emptyDir and therefore always current.

   Note what this does **not** do. `~/thinkube/notebooks/examples/` is copied
   from the templates once, on first setup, and guarded by a `.copied` marker
   after that. A user's working notebooks are never overwritten — which keeps
   their edits safe, and also means an existing installation does not receive
   updated examples. To take a new version, copy the file across from
   `~/thinkube/templates/examples/`.

**Cleaning tools (required before commit)**:
```bash
# Install tools
pip install nbstripout pre-commit

# Install pre-commit hooks (auto-cleans on commit)
cd thinkube-notebooks-examples
pre-commit install

# Manual cleaning
nbstripout notebook.ipynb

# Validate all notebooks are clean
./scripts/validate_notebooks.sh
```

## Deployment Process

### 1. Build the Notebook Image

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor-images/15_build_jupyter_images.yaml
```

This builds and pushes `tk-jupyter-base` to Harbor registry.

### 2. Deploy JupyterHub

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/jupyterhub/10_configure_keycloak.yaml
./scripts/run_ansible.sh ansible/40_thinkube/core/jupyterhub/11_deploy.yaml
```

`11_deploy.yaml` will:
- Read the OIDC secret `jupyterhub-oidc-secret` created by `10_configure_keycloak.yaml`
- Create JuiceFS PVCs for persistent storage (notebooks 100Gi, datasets 500Gi, models 200Gi) and a static PV for the MLflow artifacts volume
- Deploy JupyterHub (Helm) with the spawn form that queries thinkube-control
- Configure volume mounts at `/home/thinkube/thinkube/` to preserve the home folder
- Create the HTTPRoute `jupyterhub-httproute` for `notebooks.<domain_name>`

`16_configure_code_server_storage.yaml` then mounts the same JuiceFS paths in
code-server, through static PVs.

### 3. Examples

No step is needed. The `clone-templates` init container clones
`thinkube-notebooks-examples` into `~/thinkube/templates/` on every pod start, so the
templates track the repository without a scheduled job.

### 4. Verify Deployment

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/jupyterhub/18_test.yaml
```

This verifies:
- JuiceFS volume accessibility
- Examples repository availability
- Custom image availability
- GPU detection (if available)
- Service health
- Authentication configuration

## Access Information

- **URL**: `https://notebooks.<domain_name>`
- **Authentication**: Keycloak SSO (mandatory)
- **Admin User**: `<admin_username>` from inventory

## Usage

### Profile Selection

The image is fixed to `tk-jupyter-base`. Users choose the node, CPU and
memory in the spawn form, and pick a venv as the kernel in JupyterLab.

### Working with Storage

#### Persistent Storage (JuiceFS)
- `/home/thinkube/thinkube/notebooks` - Your notebooks and work (100Gi)
- `/home/thinkube/thinkube/datasets` - Shared datasets across all pods (500Gi)
- `/home/thinkube/thinkube/models` - Saved models accessible from any pod (200Gi)
- `/home/thinkube/thinkube/mlflow` - MLflow artifacts, the same files MLflow stores

#### Environment Variables
- `~/.config/thinkube/service-env-jh.sh` - Written at pod start by the service-discovery init container and sourced, contains service endpoints

### Example Workflow

- Pick the `fine-tuning` or `agent-dev` kernel
- Work in `/home/thinkube/thinkube/notebooks/`
- Load datasets from `/home/thinkube/thinkube/datasets/`
- Save models to `/home/thinkube/thinkube/models/`
- Example notebooks in `/home/thinkube/thinkube/templates/`

## Maintenance

### Rebuild Images

To update the Jupyter image:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/harbor-images/15_build_jupyter_images.yaml
```

The Helm values set `pullPolicy: Always`, so new servers pull the new image.

### Rollback

To remove JupyterHub completely:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/jupyterhub/19_rollback.yaml
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
   - **Cause**: the jupyterhub package is missing from the image, or a volume mounted over the folder that holds the command hides it (for example a volume at `/home/thinkube/` hides `~/.local/bin/`)
   - **Solution**: Ensure volumes mount at `/home/thinkube/thinkube/` subdirectories, never at the home folder
   - Check that the jupyterhub package is installed in the image (`tk-jupyter-base` installs it in the system Python)

2. **Storage Not Accessible**:
   - Verify JuiceFS CSI driver: `kubectl get pods -n kube-system -l app.kubernetes.io/name=juicefs-csi-driver`
   - Verify PostgreSQL and SeaweedFS (JuiceFS metadata and data) are running
   - Ensure PVCs are bound: `kubectl get pvc -n jupyterhub`

3. **GPU Not Available**:
   - Check GPU operator: `kubectl get pods -n gpu-operator`
   - Verify node labels: `kubectl get nodes --show-labels | grep nvidia`
   - Check resource allocation: `kubectl describe node <gpu-node>`

4. **Image Pull Errors**:
   - Verify Harbor connectivity: `curl -k https://registry.<domain>/api/v2.0/health`
   - Check image exists in Harbor: `registry.<domain>/library/tk-jupyter-base`
   - Verify images are properly pushed during build

5. **Authentication Issues**:
   - Check Keycloak is running: `kubectl get pods -n keycloak`
   - Verify OIDC secret exists: `kubectl get secret -n jupyterhub jupyterhub-oidc-secret`
   - Check Keycloak client configuration in Keycloak admin console

6. **Examples Not Available**:
   - Check the clone step: `kubectl logs -n jupyterhub jupyter-<user> -c clone-templates`
   - Confirm the templates arrived: `ls ~/thinkube/templates/examples/`
   - Confirm the first-run copy happened: `ls -a ~/thinkube/notebooks/examples/.copied`

7. **Examples Out of Date**:
   The working copies in `~/thinkube/notebooks/examples/` are deliberately never
   refreshed, so that a user's own edits survive. `~/thinkube/templates/examples/`
   is re-cloned on every pod start and always holds the current repository —
   copy the file you want from there.

## Performance Considerations

- **Venvs**: Kept on local node disk, because JuiceFS is slow with many small files
- **Scratch Space**: Use `/home/thinkube/scratch/` for temporary large files requiring fast I/O
- **GPU Scheduling**: Auto-select profile uses Kubernetes scheduler for optimal placement
- **Image Sizes**: GPU images are large (~10GB), initial pull may take time

## Security Notes

- Keycloak provides mandatory SSO authentication
- All traffic is TLS-encrypted; the gateway terminates TLS
- Shared-code mount is read-only to prevent accidental modifications
- No fallback authentication - if Keycloak is down, JupyterHub is inaccessible

## Architecture Benefits

The examples repository and volume mount strategy provides:

1. **Decoupled Updates**: Examples updated without rebuilding Docker images
2. **Version Control**: Public GitHub repository enables community contributions
3. **Auto-Sync**: Templates are cloned again on every pod start
4. **Fail-Fast**: Deployment fails immediately if dependencies unavailable
5. **Home Preservation**: Image content in the home folder remains accessible
6. **Clean Separation**: Image content and user data don't conflict
7. **Persistence**: JuiceFS ensures notebooks survive pod restarts and are visible on every node
8. **Dynamic Discovery**: The spawn form reads cluster resources from thinkube-control

## License

Copyright Alejandro Martínez Corriá and the Thinkube contributors
SPDX-License-Identifier: Apache-2.0