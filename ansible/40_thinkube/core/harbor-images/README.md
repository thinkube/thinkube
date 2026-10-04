# Harbor Images

This directory contains playbooks that build and mirror container images for the Thinkube platform. These playbooks populate Harbor with essential images after Harbor deployment.

**Note**: This is NOT a deployable component - these are image build and mirror operations that run after Harbor is deployed.

## Installation

These playbooks are part of the core install. There is no `00_install.yaml`.
The Thinkube installer runs `13_mirror_public_images.yaml`,
`14_build_base_images.yaml`, `15_build_jupyter_images.yaml` and
`16_build_codeserver_image.yaml` in that order, right after
`harbor/00_install.yaml`. They are not run on their own.

## Overview

The harbor-images playbooks serve two purposes:
1. **Mirror public images** from external registries to Harbor to avoid rate limits and ensure availability
2. **Build custom images** optimized for Thinkube with pre-installed dependencies and service integrations

All images are stored in Harbor's `library` project which is publicly accessible within the cluster.

## Playbooks

### 13_mirror_public_images.yaml

Mirrors public images to Harbor's `library` project.

**What it configures**:
- Reads the image list from `mirror_images.json` in https://github.com/thinkube/thinkube-metadata (58 images today)
- Pushes with the Harbor robot token (`HARBOR_ROBOT_TOKEN` in `~/.env`)
- Mirrors multi-arch images with podman pull/push and `crane` manifests
- Creates ConfigMap `harbor-system-images` in `registry` namespace for thinkube-control discovery

To mirror a single image, pass `mirror_images` with `-e`. The playbook header shows the form.

### 14_build_base_images.yaml

Builds custom base images with pre-installed dependencies for faster application builds.

**What it configures**:
- Builds each architecture natively on a node of that architecture (no QEMU), then creates a manifest list
- Architectures come from `container_build_platforms` in the inventory
- Pushes images to Harbor's `library` project
- Creates ConfigMap `harbor-system-images` in `registry` namespace for discovery

**Built images**:

**Application Bases**:
- `python-base:3.12-slim` - FastAPI, SQLAlchemy, MLflow, pytest
- `node-base:18-alpine` and `node-base:22-alpine` - Express, TypeScript, Jest, ESLint
- `test-runner:latest` - pytest, jest, tox, coverage
- `ci-utils:latest` - curl, jq, git, bash for CI/CD

**Platform Tools**:
- `tk-service-discovery:latest` - kubectl, jq, yq, bash for Argo Workflows

**AI Bases**:
- `ai-inference-base:cuda13.0-torch2.9-py3.12` - CUDA 13.0 + PyTorch 2.9 + transformers for Stable Diffusion
- `vllm-base:<vllm_version>-cuda13.0-py3.12` (today `0.23.0-cuda13.0-py3.12`) - vLLM base image; `vllm_version` is set in `14_build_base_images.yaml`
- `tensorrt-llm-base:1.3.0rc13` - TensorRT-LLM base image
- `text-embeddings-base:latest` - Text Embeddings Inference base image
- `mlflow-custom:latest` - MLflow with OIDC auth, PostgreSQL, S3 support
- `model-mirror:latest` - HuggingFace to MLflow mirroring tool

**Storage**:
- `valkey:8.1.0` - Valkey 8.1.0 Alpine (Redis OSS alternative)

**MCP Servers**:
- `tk-package-version:latest` - MCP server for package version checking (from GitHub)

### 15_build_jupyter_images.yaml

Builds one Jupyter image, `tk-jupyter-base:latest`.

**What it configures**:
- Base: NVIDIA PyTorch from NGC, mirrored to Harbor (`jupyter_base_pytorch_tag`, `26.03-py3`)
- Includes JupyterLab, JupyterHub and the Claude Code CLI
- Templates `.thinkube_env` (service endpoints) and `startup.sh` into the build context
- ML packages are not in the image. They live in persistent venvs on JuiceFS (see `../jupyterhub/99_build_venvs.yaml`). Users pick a venv as the kernel in JupyterLab.
- Builds each architecture natively, like 14
- Creates ConfigMap `harbor-user-images` in `registry` namespace for discovery

### 16_build_codeserver_image.yaml

Builds `code-server-dev:latest` with podman on the control plane. The image
matches the host architecture.

**What it configures**:
- Ensures the `library` project exists in Harbor
- Base: `ubuntu:24.04` from Harbor
- Contents, from the Containerfile header: code-server; kubectl, helm, k9s, podman, skopeo; Ansible and copier; argo, argocd, gh, tea (Gitea), nats; jq, yq, ripgrep, fd, bat, httpie; psql, redis-tools; mlflow, devpi-client, ansible-lint
- Adds the image to ConfigMap `harbor-system-images` in `registry` namespace for discovery

## Image Discovery

Each playbook uses the `container_deployment/image_manifest` Ansible role to create ConfigMaps in the `registry` namespace for service discovery by thinkube-control:

- **harbor-system-images** - Contains mirrored and system base images (protected, cannot be deleted)
  - Created by: 13_mirror_public_images.yaml, 14_build_base_images.yaml, 16_build_codeserver_image.yaml
  - Category: `system`
  - Protected: Yes

- **harbor-user-images** - Contains user-facing Jupyter images (can be managed)
  - Created by: 15_build_jupyter_images.yaml
  - Category: `user`
  - Protected: No

The ConfigMaps contain `manifest.json` data with metadata for each image:
- Image name, registry, repository, tag
- Source URL and destination URL
- Description and purpose
- Build/mirror timestamp
- Custom metadata (packages, services, display names, etc.)

## Image Naming Convention

- **Mirrored images**: Use original upstream names in `library/` project
  - Example: `registry.example.com/library/alpine:latest`
- **Custom images**: Descriptive names, `tk-` prefix for platform tools
  - Example: `registry.example.com/library/python-base:3.12-slim`
  - Example: `registry.example.com/library/tk-jupyter-base:latest`

## Usage

These images are built during the core install, after Harbor, and are available for:
- Kubernetes pod specifications
- Argo Workflows tasks
- JupyterHub spawner configurations
- Development environments
- CI/CD pipelines

### Pull an Image

```bash
# Using podman
podman pull registry.example.com/library/python-base:3.12-slim
```

### Use in Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ml-workload
spec:
  containers:
  - name: jupyter
    image: registry.example.com/library/tk-jupyter-base:latest
    ports:
    - containerPort: 8888
  imagePullSecrets:
  - name: harbor-pull-secret
```

### Launch Jupyter Lab

```bash
kubectl run jupyter --image=registry.example.com/library/tk-jupyter-base:latest \
  --port=8888 -- jupyter lab --ip=0.0.0.0 --allow-root --no-browser

# Port forward to access
kubectl port-forward jupyter 8888:8888
# Access at http://localhost:8888
```

### Launch Code Server

```bash
kubectl run code-server --image=registry.example.com/library/code-server-dev:latest \
  --port=8080 -- code-server --bind-addr=0.0.0.0:8080 --auth=none

kubectl port-forward code-server 8080:8080
# Access at http://localhost:8080
```

## Build Process

Images are built with podman:

1. **Mirror playbook** pulls from external registries and pushes to Harbor
2. **Build playbooks** use podman build with Containerfile templates from the `base-images/` directory
3. **Multi-arch builds** (14, 15) build each architecture on a node of that architecture through `_build_native_image.yaml`, push per-arch tags, then create a manifest list
4. **Image push**: 13 uses the Harbor robot token from ~/.env; 14, 15 and 16 log in as the Harbor admin
5. **Manifest creation** uses `container_deployment/image_manifest` role to register images in ConfigMaps for thinkube-control discovery

## Notes

- All images stored in Harbor's `library` project (publicly accessible within cluster)
- Harbor robot credentials used for image push operations
- Multi-architecture support varies (some GPU images are AMD64-only)
- CUDA images require NVIDIA GPU on target nodes
- Code server includes complete CLI toolchain for platform operations
- ConfigMaps created in `registry` namespace for thinkube-control image discovery

🤖 [AI-assisted]
