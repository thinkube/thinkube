# JupyterHub with GPU Flexibility

Multi-user Jupyter notebook environment with GPU flexibility, persistent storage via SeaweedFS, and specialized ML/AI images.

## Overview

JupyterHub provides a complete AI/ML development platform with:
- **GPU Flexibility**: Notebooks can run on ANY node (control plane or GPU nodes)
- **Persistent Storage**: SeaweedFS-backed storage accessible from all nodes
- **Hybrid Storage Strategy**: Combines SeaweedFS persistence with local scratch for performance
- **Custom ML/AI Images**: Four specialized environments for different workloads
- **Dynamic Profiles**: Auto-detection of GPU nodes and resources
- **Authentication**: Keycloak SSO (mandatory)

## Architecture

### Storage Strategy (Hybrid Approach)

```yaml
# Persistent (SeaweedFS) - Available on ALL nodes
/home/jovyan/notebooks     # Jupyter notebooks (.ipynb files)
/home/jovyan/datasets      # Shared datasets
/home/jovyan/models        # Trained models

# Local Fast Storage - Per pod
/home/jovyan/scratch       # emptyDir - fast temporary workspace

# Optional Reference - Only on control plane (read-only)
/home/jovyan/shared-code-reference  # Fails gracefully on GPU nodes
```

This hybrid approach provides:
- ✅ GPU flexibility (no node affinity constraints)
- ✅ Persistent notebook storage via SeaweedFS
- ✅ Fast local scratch space for temporary work
- ✅ Optional shared-code access when on control plane

## Custom Images

Four specialized Docker images are built and available:

1. **jupyter-ml-cpu** - Standard ML/AI development
   - Pandas, scikit-learn, matplotlib, transformers
   - LiteLLM, MLflow integration
   - 8GB RAM recommended

2. **jupyter-ml-gpu** - GPU-accelerated deep learning
   - PyTorch with CUDA support
   - Transformers, Accelerate
   - GPU monitoring tools (nvitop, gpustat)
   - 16GB RAM recommended

3. **jupyter-fine-tuning** - LLM fine-tuning environment
   - Unsloth with QLoRA support
   - DeepSpeed, TRL, PEFT
   - Optimized for 4-bit quantization
   - 32GB RAM recommended

4. **jupyter-agent-dev** - Agent development
   - LangChain, CrewAI, AutoGen
   - Vector stores (ChromaDB, Qdrant, FAISS)
   - Agent tools and frameworks
   - 8GB RAM recommended

## Prerequisites

1. **Core Components**:
   - CORE-001: MicroK8s cluster with GPU operator (if using GPUs)
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

## Deployment Process

### 1. Build Custom ML/AI Images

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/10_build_images.yaml
```

This builds and pushes all four custom images to Harbor registry.

### 2. Configure Keycloak Authentication (Required)

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/11_configure_keycloak.yaml
```

This creates:
- Keycloak client for JupyterHub
- OIDC secret in Kubernetes

**Note**: This step is mandatory. JupyterHub will not deploy without Keycloak configuration.

### 3. Deploy JupyterHub

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/12_deploy.yaml
```

This will:
- Create SeaweedFS volumes for persistent storage
- Deploy JupyterHub with GPU flexibility
- Configure hybrid storage approach
- Set up dynamic profile generation

### 4. Verify Deployment

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/18_test.yaml
```

This verifies:
- SeaweedFS volume accessibility
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

When spawning a notebook, users can choose from:

- 📚 **Standard Environment (CPU)** - General ML/AI development
- 🚀 **GPU Environment (Auto-select)** - Automatically finds available GPU
- 🔧 **Fine-tuning (Unsloth + QLoRA)** - Optimized for LLM fine-tuning
- 🤖 **Agent Development (LangChain)** - For building AI agents
- 💻 **GPU on [specific-node]** - Run on a specific GPU node (dynamically generated)

### Working with Storage

#### Persistent Directories (SeaweedFS)
- `/home/jovyan/notebooks` - Save notebooks here for persistence
- `/home/jovyan/datasets` - Store and share datasets
- `/home/jovyan/models` - Save trained models

#### Temporary Fast Storage
- `/home/jovyan/scratch` - Use for temporary work requiring fast I/O
- **Note**: Cleared when pod restarts

#### Optional Shared Code
- `/home/jovyan/shared-code-reference` - Read-only, only available on control plane

### Example Workflows

1. **GPU Training**:
   - Select "GPU Environment (Auto-select)" profile
   - Work in `/home/jovyan/notebooks/projects/`
   - Use `/home/jovyan/scratch/` for temporary datasets
   - Save models to `/home/jovyan/models/`

2. **Fine-tuning LLMs**:
   - Select "Fine-tuning (Unsloth + QLoRA)" profile
   - Load base models to `/home/jovyan/scratch/`
   - Save checkpoints to `/home/jovyan/models/checkpoints/`
   - Final models go to `/home/jovyan/models/fine-tuned/`

3. **Agent Development**:
   - Select "Agent Development (LangChain)" profile
   - Develop in `/home/jovyan/notebooks/agents/`
   - Store vector databases in `/home/jovyan/datasets/embeddings/`

## Maintenance

### Rebuild Images

To update the custom images:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/10_build_images.yaml
```

### Configure Service Discovery

Register JupyterHub with the discovery service:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/17_configure_discovery.yaml
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

# User pod logs
microk8s.kubectl logs -n jupyterhub jupyter-<username>
```

### Common Issues

1. **Notebook Won't Start**:
   - Check SeaweedFS PVCs: `kubectl get pvc -n jupyterhub`
   - Verify profile resources match available capacity
   - Check node selectors for GPU profiles

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
   - Check image exists: `podman search registry.<domain>/library/jupyter`
   - Verify robot token is set correctly

5. **Authentication Issues**:
   - Check Keycloak is running: `kubectl get pods -n keycloak`
   - Verify OIDC secret exists: `kubectl get secret -n jupyterhub jupyterhub-oidc-secret`
   - If secret is missing, run `11_configure_keycloak.yaml`
   - Check Keycloak client configuration in Keycloak admin console

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

The hybrid storage approach provides the best of all worlds:

1. **Flexibility**: Notebooks can run on any node without constraints
2. **Performance**: Local scratch for fast I/O operations
3. **Persistence**: SeaweedFS ensures notebooks survive pod restarts and node changes
4. **Convenience**: Optional shared-code access when on control plane
5. **Simplicity**: Single deployment path with no conditional logic

## License

Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
SPDX-License-Identifier: Apache-2.0