# Harbor Images

This directory contains playbooks that build and mirror container images for the Thinkube platform. These playbooks populate Harbor with essential images after Harbor deployment.

**Note**: This is NOT a deployable component - these are image build and mirror operations that run after Harbor is deployed (deployment order #16).

## Overview

The harbor-images playbooks serve two purposes:
1. **Mirror public images** from external registries to Harbor to avoid rate limits and ensure availability
2. **Build custom images** optimized for Thinkube with pre-installed dependencies and service integrations

All images are stored in Harbor's `library` project which is publicly accessible within the cluster.

## Playbooks

### 13_mirror_public_images.yaml

Mirrors 50+ essential public images from multiple sources to Harbor's `library` project.

**What it configures**:
- Creates `library` project in Harbor (public access)
- Detects container runtime (podman preferred, docker fallback)
- Mirrors images from GCR, Quay.io, AWS ECR, Docker Hub, GitHub Container Registry, NVIDIA NGC
- Creates ConfigMap `harbor-system-images` in `registry` namespace for thinkube-control discovery

**Mirrored images**:
- **Base**: alpine, busybox, debian:bookworm-slim, ubuntu:24.04, nginx:alpine
- **Languages**: python:3.12-slim, golang:1.25.3-alpine, node:24-alpine, rust:alpine
- **Databases**: postgres:18-alpine, valkey:7.2-alpine, pgadmin4
- **Vector DBs**: qdrant, weaviate, chroma
- **AI/ML**: litellm, argilla, cvat, tensorrt-llm:1.2.0rc2
- **CUDA**: cuda:13.0.0-base, cuda:13.0.0-devel, cuda:13.0.0-cudnn-runtime
- **Build**: kaniko-executor
- **Monitoring**: prometheus, alertmanager, node-exporter, kube-state-metrics
- **Messaging**: nats:2.12.0-alpine
- **JuiceFS**: juicefs-csi-driver and CSI sidecars
- **Knative**: helloworld-go

### 14_build_base_images.yaml

Builds 12+ custom base images with pre-installed dependencies for faster application builds.

**What it configures**:
- Detects container runtime (podman preferred)
- Builds multi-architecture images (AMD64 + ARM64 where applicable)
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

**AI/ML Bases**:
- `ai-inference-base:cuda13.0-torch2.9-py3.12` - CUDA 13.0 + PyTorch 2.9 + transformers for Stable Diffusion
- `tensorrt-llm-base:1.2.0rc2` - TensorRT-LLM 1.2.0rc2 optimized for NVIDIA Blackwell GB10 (DGX Spark)
- `mlflow-custom:latest` - MLflow with OIDC auth, PostgreSQL, S3 support
- `model-mirror:latest` - HuggingFace to MLflow mirroring tool

**Storage**:
- `valkey:8.1.0` - Valkey 8.1.0 Alpine (Redis OSS alternative)

**MCP Servers**:
- `tk-package-version:latest` - MCP server for package version checking (from GitHub)

**Note**: vLLM base is commented out, waiting for sm_121a Blackwell support

### 15_build_jupyter_images.yaml

Builds 3 custom Jupyter Lab images with Thinkube service integrations pre-configured.

**What it configures**:
- Detects container runtime (podman preferred)
- Templates `.thinkube.env` file with service discovery endpoints
- Includes iPython startup script for auto-loading environment
- Includes test notebook for verifying service connectivity
- Creates ConfigMap `harbor-user-images` in `registry` namespace for discovery

**Built images**:

**1. tk-jupyter-ml-gpu:latest** (Default)
- Base: nvidia/cuda:12.6.0-cudnn-runtime-ubuntu22.04
- Purpose: General-purpose ML development with GPU support (works on CPU too)
- Packages: Python 3.12, PyTorch 2.9, transformers, datasets, accelerate, JupyterLab 4.3
- Integrations: PostgreSQL, Valkey, Qdrant, Chroma, Weaviate, OpenSearch, MLflow, SeaweedFS S3, LiteLLM, NATS, ClickHouse

**2. tk-jupyter-fine-tuning:latest**
- Base: nvidia/cuda:12.6.0-cudnn-devel-ubuntu22.04
- Purpose: LLM fine-tuning with Unsloth and QLoRA (**Requires GPU**)
- Packages: unsloth, bitsandbytes, peft, trl, QLoRA + all from ml-gpu
- Integrations: Same as ml-gpu

**3. tk-jupyter-agent-dev:latest**
- Base: python:3.12-slim
- Purpose: AI agent development with LangChain and CrewAI (CPU-only)
- Packages: LangChain, CrewAI, FAISS + all from ml-gpu (except PyTorch)
- Integrations: Same as ml-gpu

**Common features**:
- `.thinkube.env` with endpoints for: PostgreSQL, Valkey, Qdrant, Weaviate, Chroma, OpenSearch, MLflow, SeaweedFS, LiteLLM, NATS, ClickHouse
- iPython startup script auto-loads environment
- Test notebook: `test_thinkube_services.ipynb`
- JupyterLab on port 8888
- Working directory: `/home/jovyan/work`

### 16_build_codeserver_image.yaml

Builds a complete development environment with code-server (VS Code in browser) and all Thinkube CLI tools.

**What it configures**:
- Detects container runtime (podman preferred)
- Builds single-architecture image (matches host architecture)
- Installs comprehensive CLI toolchain for platform operations
- Creates ConfigMap `harbor-user-images` in `registry` namespace for discovery

**Built image**:

**code-server-dev:latest**
- Base: debian:bookworm-slim
- Purpose: Browser-based IDE with complete Thinkube toolchain
- **Platform**: kubectl v1.30.0, helm, k9s v0.32.0, stern v1.28.0, kubectx/kubens
- **Container**: podman, skopeo, podman-compose
- **Ansible**: ansible-core 2.18, kubernetes.core, community.general, community.crypto, ansible.posix, community.docker
- **Services**: argo v3.5.5, argocd v2.10.0, gh (GitHub), tea 0.9.2 (Gitea), nats
- **Dev Tools**: jq, yq v4.40.5, ripgrep, fd, bat, httpie
- **DB Clients**: psql (PostgreSQL 16), redis-tools
- **Python**: mlflow, devpi-client, copier, ansible-lint
- **Code Server**: 4.x on port 8080

## Image Discovery

Each playbook uses the `container_deployment/image_manifest` Ansible role to create ConfigMaps in the `registry` namespace for service discovery by thinkube-control:

- **harbor-system-images** - Contains mirrored and system base images (protected, cannot be deleted)
  - Created by: 13_mirror_public_images.yaml, 14_build_base_images.yaml
  - Category: `system`
  - Protected: Yes

- **harbor-user-images** - Contains user-facing Jupyter and development images (can be managed)
  - Created by: 15_build_jupyter_images.yaml, 16_build_codeserver_image.yaml
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
  - Example: `registry.example.com/library/tk-jupyter-ml-gpu:latest`

## Usage

These images are automatically built during Harbor deployment and are available for:
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
    image: registry.example.com/library/tk-jupyter-ml-gpu:latest
    ports:
    - containerPort: 8888
  imagePullSecrets:
  - name: harbor-pull-secret
```

### Launch Jupyter Lab

```bash
# Using the ML GPU image
kubectl run jupyter --image=registry.example.com/library/tk-jupyter-ml-gpu:latest \
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

Images are built using the host's container runtime (podman preferred, docker fallback):

1. **Mirror playbook** pulls from external registries and pushes to Harbor
2. **Build playbooks** use podman/docker build with Dockerfiles from `files/` directory
3. **Multi-arch builds** use buildx or podman manifest for AMD64+ARM64
4. **Image push** authenticates with Harbor robot credentials from ~/.env
5. **Manifest creation** uses `container_deployment/image_manifest` role to register images in ConfigMaps for thinkube-control discovery

## Notes

- All images stored in Harbor's `library` project (publicly accessible within cluster)
- Harbor robot credentials used for image push operations
- Multi-architecture support varies (some GPU images are AMD64-only)
- CUDA images require NVIDIA GPU on target nodes
- Jupyter images include `.thinkube.env` for automatic service discovery
- Code server includes complete CLI toolchain for platform operations
- TensorRT-LLM optimized for NVIDIA Blackwell GB10 (DGX Spark)
- vLLM support pending Blackwell compute capability (sm_121a)
- ConfigMaps created in `registry` namespace for thinkube-control image discovery

🤖 [AI-assisted]
