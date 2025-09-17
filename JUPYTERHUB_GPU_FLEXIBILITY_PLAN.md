# JupyterHub GPU Flexibility Implementation Plan

## Executive Summary

This plan enables JupyterHub to run on any GPU node in the Thinkube cluster while maintaining notebook persistence and avoiding complex shared-code migrations. Designed for single-user deployment to avoid multi-tenancy complexity.

## Key Decisions

1. **GPU flexibility is priority** - JupyterHub must run on any GPU node
2. **No shared-code migration** - Keep shared-code as hostPath for CI/CD integrity
3. **SeaweedFS for notebooks** - Enables true portability between nodes
4. **Single-user focus** - Simplifies configuration and security
5. **License compliance** - Only Apache 2.0 compatible components

## Architecture

```
Control Plane (node1)                    GPU Nodes (node2, node3, etc)
├── shared-code (hostPath)               ├── JupyterHub pods can run here
│   ├── code-server ✓                    ├── Full GPU access
│   ├── thinkube-control ✓               └── Mount notebooks via SeaweedFS
│   └── CI/CD pipeline ✓
└── [Stays unchanged]

SeaweedFS (existing)
├── /notebooks        # Persistent notebook storage (small files, portable)
├── /datasets         # Large datasets
└── /models          # Trained models
```

## Implementation Phases

### Phase 1: SeaweedFS Volume Setup (Day 1-2)

#### 1.1 Create SeaweedFS Volume for Notebooks
```yaml
# File: ansible/40_thinkube/optional/jupyterhub/manifests/seaweedfs-volumes.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: jupyter-notebooks-pv
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  csi:
    driver: seaweedfs-csi
    volumeHandle: jupyter-notebooks
    volumeAttributes:
      collection: "jupyter"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jupyter-notebooks-pvc
  namespace: jupyterhub
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  volumeName: jupyter-notebooks-pv
```

#### 1.2 Create Local Scratch Space Configuration
```yaml
# Incorporated into jupyterhub-values.yaml.j2 (see Phase 2)
# Uses emptyDir for fast local temporary storage
```

### Phase 2: JupyterHub Configuration Update (Day 3-4)

#### 2.1 Update jupyterhub-values.yaml.j2
```yaml
# File: ansible/40_thinkube/optional/jupyterhub/templates/jupyterhub-values.yaml.j2
hub:
  config:
    JupyterHub:
      # Single-user configuration
      authenticator_class: nullauthenticator.NullAuthenticator
      # Or keep Keycloak with single admin user:
      # authenticator_class: generic-oauth

    # Dynamic profile generation
    KubeSpawner:
      profile_list: |
        def get_profile_list(spawner):
            # This function dynamically generates profiles based on available nodes
            profiles = []

            # CPU-only profile (can run anywhere)
            profiles.append({
                'display_name': 'Development (CPU only)',
                'description': 'General development and exploration',
                'default': True,
                'kubespawner_override': {
                    'image': '{{ harbor_registry }}/library/jupyter-ml-cpu:latest',
                    'cpu_limit': 4,
                    'mem_limit': '8G'
                }
            })

            # GPU profile (auto-selects available GPU node)
            profiles.append({
                'display_name': 'GPU Training - Auto-select',
                'description': 'Automatically selects available GPU node',
                'kubespawner_override': {
                    'image': '{{ harbor_registry }}/library/jupyter-ml-gpu:latest',
                    'node_selector': {'nvidia.com/gpu': 'true'},
                    'extra_resource_limits': {'nvidia.com/gpu': '1'}
                }
            })

            # Fine-tuning profile
            profiles.append({
                'display_name': 'Fine-tuning (Unsloth)',
                'description': 'Unsloth environment for model fine-tuning',
                'kubespawner_override': {
                    'image': '{{ harbor_registry }}/library/jupyter-unsloth:latest',
                    'node_selector': {'nvidia.com/gpu': 'true'},
                    'extra_resource_limits': {'nvidia.com/gpu': '1'},
                    'cpu_limit': 8,
                    'mem_limit': '32G'
                }
            })

            return profiles

        c.KubeSpawner.profile_list = get_profile_list

singleuser:
  # Remove old shared-code mount, use SeaweedFS + scratch
  storage:
    type: none  # We'll define volumes manually

  extraVolumes:
    # SeaweedFS for persistent notebooks
    - name: notebooks
      persistentVolumeClaim:
        claimName: jupyter-notebooks-pvc

    # Local scratch space (fast temporary storage)
    - name: scratch
      emptyDir:
        sizeLimit: 100Gi

    # Optional: Read-only reference to shared-code for copying
    - name: shared-code-ref
      hostPath:
        path: {{ code_source_path }}
        type: Directory

  extraVolumeMounts:
    # Notebooks directory (SeaweedFS - persistent across nodes)
    - name: notebooks
      mountPath: /home/jovyan/notebooks

    # Scratch directory (local - fast but temporary)
    - name: scratch
      mountPath: /home/jovyan/scratch

    # Reference to shared-code (read-only, only on control plane)
    - name: shared-code-ref
      mountPath: /home/jovyan/shared-code-reference
      readOnly: true

  # Remove node selector to allow scheduling on any node
  nodeSelector: {}

  # Remove node affinity constraints
  extraNodeAffinity: {}
```

### Phase 3: Custom Image Building (Day 5-6)

#### 3.1 Base CPU Image
```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-ml-cpu.Dockerfile.j2
FROM {{ harbor_registry }}/library/jupyter-datascience-notebook:latest

RUN pip install --no-cache-dir \
    pandas==2.1.4 \
    scikit-learn==1.3.2 \
    matplotlib==3.8.2 \
    seaborn==0.13.0 \
    jupyterlab-git==0.50.0 \
    black==23.12.0 \
    pytest==7.4.3 \
    mlflow==2.9.2 \
    boto3==1.34.0  # For SeaweedFS S3 API

WORKDIR /home/jovyan
```

#### 3.2 GPU-Enabled Image
```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-ml-gpu.Dockerfile.j2
FROM {{ harbor_registry }}/library/cuda:12.6.0-base-ubuntu24.04

# Install Python and Jupyter
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install JupyterLab and ML packages
RUN pip install --no-cache-dir --break-system-packages \
    jupyterlab==4.0.9 \
    torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121 \
    transformers==4.36.2 \
    accelerate==0.25.0 \
    datasets==2.16.1 \
    tensorboard==2.15.1 \
    mlflow==2.9.2 \
    boto3==1.34.0

# Create jovyan user (JupyterHub convention)
RUN useradd -m -s /bin/bash jovyan
USER jovyan
WORKDIR /home/jovyan
```

#### 3.3 Fine-tuning Image (Unsloth)
```dockerfile
# File: ansible/40_thinkube/core/harbor/base-images/jupyter-unsloth.Dockerfile.j2
FROM {{ harbor_registry }}/library/jupyter-ml-gpu:latest

USER root
# Install Unsloth and fine-tuning tools
RUN pip install --no-cache-dir --break-system-packages \
    "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" \
    trl==0.7.7 \
    peft==0.7.1 \
    bitsandbytes==0.41.3 \
    mlflow==2.9.2 \
    aim==3.17.5  # Apache 2.0 alternative to wandb

USER jovyan
```

### Phase 4: Integration with Thinkube-Control (Day 7-8)

#### 4.1 Add Image Metadata
```python
# File: thinkube-control/backend/app/db/seed_jupyter_images.py
jupyter_images = [
    {
        "name": "jupyter-ml-cpu",
        "category": "custom",
        "tags": ["jupyter-compatible", "cpu-only"],
        "description": "JupyterLab for CPU-based ML development",
        "metadata": {
            "jupyter_compatible": True,
            "gpu_required": False,
            "packages": ["scikit-learn", "pandas", "matplotlib"]
        }
    },
    {
        "name": "jupyter-ml-gpu",
        "category": "custom",
        "tags": ["jupyter-compatible", "gpu-required"],
        "description": "JupyterLab with GPU support for deep learning",
        "metadata": {
            "jupyter_compatible": True,
            "gpu_required": True,
            "packages": ["torch", "transformers", "accelerate"]
        }
    },
    {
        "name": "jupyter-unsloth",
        "category": "custom",
        "tags": ["jupyter-compatible", "gpu-required", "fine-tuning"],
        "description": "JupyterLab with Unsloth for model fine-tuning",
        "metadata": {
            "jupyter_compatible": True,
            "gpu_required": True,
            "memory_recommended": "32G",
            "packages": ["unsloth", "trl", "peft", "bitsandbytes"]
        }
    }
]
```

#### 4.2 Add JupyterHub Launch Button
```vue
<!-- File: thinkube-control/frontend/src/components/ImageActions.vue -->
<template>
  <div class="image-actions">
    <button
      v-if="image.metadata?.jupyter_compatible"
      @click="launchInJupyter"
      class="btn btn-primary"
    >
      <Icon icon="mdi:jupyter" />
      Launch in JupyterHub
    </button>
  </div>
</template>

<script setup>
const launchInJupyter = () => {
  // Redirect to JupyterHub with image parameter
  const jupyterUrl = `https://jupyter.${domain}/hub/spawn?image=${image.name}`
  window.open(jupyterUrl, '_blank')
}
</script>
```

### Phase 5: Data Synchronization Workflows (Day 9-10)

#### 5.1 Git Sync Helper Script
```bash
#!/bin/bash
# File: ansible/40_thinkube/optional/jupyterhub/scripts/sync-from-code-server.sh
# Helper script to sync code from code-server to JupyterHub

REPO_NAME=$1
if [ -z "$REPO_NAME" ]; then
    echo "Usage: sync-from-code-server.sh <repo-name>"
    exit 1
fi

cd /home/jovyan/notebooks
if [ ! -d "$REPO_NAME" ]; then
    git clone https://gitea.{{ domain_name }}/${USER}/${REPO_NAME}.git
else
    cd $REPO_NAME
    git pull origin main
fi

echo "Repository $REPO_NAME synced successfully"
```

#### 5.2 SeaweedFS Integration Examples
```python
# File: ansible/40_thinkube/optional/jupyterhub/notebooks/seaweedfs-examples.ipynb
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# SeaweedFS Integration Examples\n",
    "How to work with datasets and models in SeaweedFS"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import boto3\n",
    "import pandas as pd\n",
    "from pathlib import Path\n",
    "\n",
    "# Configure S3 client for SeaweedFS\n",
    "s3 = boto3.client(\n",
    "    's3',\n",
    "    endpoint_url='http://seaweedfs.{{ domain_name }}:8333',\n",
    "    aws_access_key_id='your-key',\n",
    "    aws_secret_access_key='your-secret'\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Download dataset from SeaweedFS\n",
    "s3.download_file('datasets', 'train.csv', '/home/jovyan/scratch/train.csv')\n",
    "df = pd.read_csv('/home/jovyan/scratch/train.csv')\n",
    "print(f\"Dataset shape: {df.shape}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Upload trained model to SeaweedFS\n",
    "model_path = '/home/jovyan/scratch/model.pt'\n",
    "s3.upload_file(model_path, 'models', 'fine-tuned-model-v1.pt')\n",
    "print(\"Model uploaded successfully\")"
   ]
  }
 ]
}
```

## Testing Plan

### Week 3: Testing & Validation

1. **Storage Testing**
   - Verify notebook persistence across node restarts
   - Test SeaweedFS performance for notebook operations
   - Validate scratch space cleanup

2. **GPU Scheduling Testing**
   - Launch notebooks on different GPU nodes
   - Verify GPU allocation and limits
   - Test node selector functionality

3. **Image Testing**
   - Test each custom image (CPU, GPU, Unsloth)
   - Verify package installations
   - Run sample ML workloads

4. **Integration Testing**
   - Test launch from thinkube-control
   - Verify Git synchronization workflow
   - Test SeaweedFS data access

## Migration Checklist

- [ ] Backup existing JupyterHub notebooks (if any)
- [ ] Create SeaweedFS volumes
- [ ] Build and push custom images to Harbor
- [ ] Update JupyterHub Helm values
- [ ] Deploy updated JupyterHub
- [ ] Test GPU node scheduling
- [ ] Test notebook persistence
- [ ] Update documentation
- [ ] Create example notebooks

## Risk Mitigation

### Risk 1: SeaweedFS Performance
**Mitigation**: Monitor notebook save/load times. If too slow, consider NFS as alternative.

### Risk 2: Node Scheduling Issues
**Mitigation**: Start with manual node selection, add auto-scheduling after testing.

### Risk 3: Storage Compatibility
**Mitigation**: Test SeaweedFS CSI driver thoroughly before migration.

## Success Criteria

1. ✅ JupyterHub pods can run on any GPU node
2. ✅ Notebooks persist across node changes
3. ✅ GPU resources properly allocated
4. ✅ Custom images with ML frameworks working
5. ✅ Integration with thinkube-control functional
6. ✅ Data sync workflows documented and tested

## Notes

- All components are Apache 2.0 compatible
- Single-user focus simplifies configuration
- SeaweedFS provides the best balance of persistence and flexibility
- Git remains the primary code synchronization method
- Shared-code remains unchanged for CI/CD stability

## Next Steps

After this plan is implemented, consider:
1. Adding more specialized images (JAX, specific model architectures)
2. Implementing notebook templates for common workflows
3. Adding resource monitoring for GPU utilization
4. Creating automated backup of notebooks to Git