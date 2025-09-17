# JupyterHub GPU Flexibility Implementation Plan

## Executive Summary

This plan enables JupyterHub to run on any GPU node in the Thinkube cluster while maintaining notebook persistence. Uses dynamic runtime image discovery from thinkube-control and separates image building from deployment for rapid iteration.

## Key Decisions

1. **GPU flexibility is priority** - JupyterHub must run on any GPU node
2. **SeaweedFS is mandatory** - Core component, always installed, no fallbacks
3. **Hybrid storage approach** - SeaweedFS for persistence, local for performance
4. **Keycloak authentication only** - No fallbacks, fails if unavailable
5. **Dynamic image discovery** - Runtime queries to thinkube-control API
6. **Separated concerns** - Image building in custom-images module, not JupyterHub
7. **Fast deployment** - 2 minutes, not 20+ minutes

## Architecture

### Component Separation

```
┌─────────────────────────────────────────────────────┐
│                 custom-images module                  │
│  - Builds Docker images (20+ minutes)                │
│  - Pushes to Harbor registry                         │
│  - Updates thinkube-control database                 │
│  - Independent of JupyterHub deployment              │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│               thinkube-control API                   │
│  - Provides /api/v1/images/jupyter endpoint          │
│  - Returns available images with metadata            │
│  - Dynamic runtime queries (not deployment-time)     │
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│              JupyterHub Deployment                   │
│  - Queries thinkube-control at runtime               │
│  - Generates profiles dynamically                    │
│  - Deploys in 2 minutes (no image building)         │
│  - Fails if dependencies unavailable (no fallbacks)  │
└─────────────────────────────────────────────────────┘
```

### Storage Architecture

```
GPU Nodes (node2, node3, etc)
├── JupyterHub pods (can run on any GPU node)
├── SeaweedFS CSI Mounts (mandatory)
│   ├── /home/jovyan/notebooks   # Persistent, shared
│   ├── /home/jovyan/datasets    # Large data, shared
│   └── /home/jovyan/models      # Trained models, shared
└── Local Storage
    └── /home/jovyan/scratch     # emptyDir, fast temp storage
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

### Phase 2: JupyterHub Configuration Update

#### 2.1 Update jupyterhub-values.yaml.j2
```yaml
# File: ansible/40_thinkube/optional/jupyterhub/templates/jupyterhub-values.yaml.j2
hub:
  config:
    JupyterHub:
      # MANDATORY: Keycloak authentication only
      authenticator_class: generic-oauth

    GenericOAuthenticator:
      client_id: jupyterhub
      client_secret: {{ jupyterhub_client_secret }}
      authorize_url: https://keycloak.{{ domain_name }}/realms/{{ keycloak_realm }}/protocol/openid-connect/auth
      token_url: https://keycloak.{{ domain_name }}/realms/{{ keycloak_realm }}/protocol/openid-connect/token
      userdata_url: https://keycloak.{{ domain_name }}/realms/{{ keycloak_realm }}/protocol/openid-connect/userinfo
      scope: ['openid', 'profile', 'email']
      username_key: preferred_username
      admin_users: ['{{ admin_username }}']

    # Dynamic profile generation from thinkube-control
    KubeSpawner:
      profile_list: |
        import requests
        import sys

        def get_profile_list(spawner):
            """Dynamically query thinkube-control for available images"""
            try:
                # Query thinkube-control API - NO FALLBACKS
                response = requests.get(
                    'http://thinkube-control-api.thinkube-control:8000/api/v1/images/jupyter',
                    headers={'Accept': 'application/json'},
                    timeout=10
                )

                if response.status_code != 200:
                    print(f"FATAL: thinkube-control API returned {response.status_code}")
                    sys.exit(1)  # Fail immediately - no fallbacks

                images = response.json()
                profiles = []

                for img in images:
                    profile = {
                        'display_name': img.get('display_name', img['name']),
                        'description': img.get('description', ''),
                        'kubespawner_override': {
                            'image': f"{{ harbor_registry }}/library/{img['name']}:latest"
                        }
                    }

                    # Add GPU requirements if specified
                    if img.get('metadata', {}).get('gpu_required'):
                        profile['kubespawner_override']['node_selector'] = {'nvidia.com/gpu': 'true'}
                        profile['kubespawner_override']['extra_resource_limits'] = {'nvidia.com/gpu': '1'}

                    # Add resource recommendations
                    if 'cpu_limit' in img.get('metadata', {}):
                        profile['kubespawner_override']['cpu_limit'] = img['metadata']['cpu_limit']
                    if 'mem_limit' in img.get('metadata', {}):
                        profile['kubespawner_override']['mem_limit'] = img['metadata']['mem_limit']

                    profiles.append(profile)

                if not profiles:
                    print("FATAL: No Jupyter images available from thinkube-control")
                    sys.exit(1)  # Fail immediately - no images available

                return profiles

            except Exception as e:
                print(f"FATAL: Failed to query thinkube-control: {e}")
                sys.exit(1)  # Fail immediately on any error

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

### Phase 3: Custom Image Module (Separate from JupyterHub)

The custom-images module is completely independent and handles all Docker image building:

```yaml
# File: ansible/40_thinkube/core/custom-images/10_build_jupyter_images.yaml
---
# This playbook is in the custom-images module, NOT in jupyterhub
# Runs independently to build and push images to Harbor
# Updates thinkube-control database after successful builds

- name: Build Jupyter Docker images
  hosts: microk8s_control_plane
  gather_facts: true
  tasks:
    - name: Build and push images to Harbor
      include_tasks: build_single_image.yaml
      loop:
        - jupyter-ml-cpu
        - jupyter-ml-gpu
        - jupyter-agent-dev
        - jupyter-fine-tuning

    - name: Update thinkube-control database
      uri:
        url: "http://thinkube-control-api.thinkube-control:8000/api/v1/images"
        method: POST
        body_format: json
        body:
          name: "{{ item }}"
          category: "jupyter"
          tags: ["jupyter-compatible"]
          metadata:
            gpu_required: "{{ 'gpu' in item }}"
```

Images are built with pinned versions in requirements files:

```python
# File: ansible/40_thinkube/core/custom-images/images/jupyter-ml-gpu/requirements.txt
jupyterlab==4.2.5
torch==2.4.1
torchvision==0.19.1
transformers==4.44.2
accelerate==0.33.0
datasets==2.21.0
tensorboard==2.17.1
mlflow==2.16.0
nvitop==1.3.2
jupyterlab-nvdashboard==0.11.0
```

### Phase 4: Integration with Thinkube-Control

#### 4.1 API Endpoint for Image Discovery
```python
# File: thinkube-control/backend/app/api/v1/images.py
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter()

@router.get("/jupyter", response_model=List[ImageResponse])
async def get_jupyter_images(db: AsyncSession = Depends(get_db)):
    """Get all Jupyter-compatible images for dynamic profile generation"""
    try:
        result = await db.execute(
            select(Image).where(
                Image.tags.contains(["jupyter-compatible"]),
                Image.is_active == True
            )
        )
        images = result.scalars().all()

        if not images:
            # No fallback - fail if no images available
            raise HTTPException(
                status_code=503,
                detail="No Jupyter images available"
            )

        return images
    except Exception as e:
        # No graceful degradation - fail immediately
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve images: {str(e)}"
        )
```

#### 4.2 Image Management Interface
```vue
<!-- File: thinkube-control/frontend/src/views/CustomImages.vue -->
<template>
  <div class="custom-images">
    <div class="tabs">
      <button
        @click="activeTab = 'jupyter'"
        :class="{ active: activeTab === 'jupyter' }"
      >
        Jupyter Images
      </button>
      <button
        @click="activeTab = 'other'"
        :class="{ active: activeTab === 'other' }"
      >
        Other Images
      </button>
    </div>

    <div v-if="activeTab === 'jupyter'" class="jupyter-images">
      <div v-for="image in jupyterImages" :key="image.id" class="image-card">
        <h3>{{ image.display_name }}</h3>
        <p>{{ image.description }}</p>
        <div class="metadata">
          <span v-if="image.metadata.gpu_required" class="gpu-badge">
            GPU Required
          </span>
          <span class="last-built">
            Built: {{ formatDate(image.last_built) }}
          </span>
        </div>
        <button
          @click="rebuildImage(image.name)"
          class="btn btn-secondary"
        >
          Rebuild
        </button>
      </div>
    </div>

    <div class="build-status" v-if="buildStatus">
      <h4>Build Status: {{ buildStatus.status }}</h4>
      <pre>{{ buildStatus.logs }}</pre>
    </div>
  </div>
</template>

<script setup>
const rebuildImage = async (imageName) => {
  // Trigger rebuild via custom-images module
  const response = await api.post('/api/v1/images/rebuild', {
    image: imageName
  })
  // WebSocket will stream build logs
  connectToBuildLogs(response.data.build_id)
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

### Component Testing

1. **Deployment Speed Testing**
   - JupyterHub deployment must complete in < 2 minutes
   - No image building during deployment
   - Verify all dependencies available (fail if not)

2. **Dynamic Discovery Testing**
   - Verify thinkube-control API returns images
   - Test profile generation from API response
   - Confirm no hardcoded image lists

3. **Storage Testing**
   - SeaweedFS must be available (no fallback to hostPath)
   - Verify notebook persistence across pod restarts
   - Test hybrid storage (SeaweedFS + local scratch)

4. **Authentication Testing**
   - Keycloak must authenticate users (no NullAuthenticator)
   - Test failure when Keycloak unavailable
   - Verify no fallback mechanisms

5. **GPU Scheduling Testing**
   - Launch notebooks on different GPU nodes
   - Verify no node affinity constraints
   - Test GPU resource allocation

## Implementation Checklist

### Custom Images Module (Separate Task)
- [ ] Create ansible/40_thinkube/core/custom-images/ structure
- [ ] Move Docker image definitions from JupyterHub
- [ ] Create requirements.txt files with pinned versions
- [ ] Implement build playbooks (20+ minute execution)
- [ ] Add thinkube-control database update after builds

### JupyterHub Deployment Module
- [ ] Remove all image building tasks
- [ ] Update values template with dynamic discovery
- [ ] Implement Keycloak authentication (no fallbacks)
- [ ] Configure SeaweedFS volumes (mandatory)
- [ ] Test 2-minute deployment time

### Thinkube-Control Integration
- [ ] Create /api/v1/images/jupyter endpoint
- [ ] Add image management UI
- [ ] Implement rebuild triggers
- [ ] Add WebSocket support for build logs

## Critical Requirements

1. **No Fallbacks**: System must fail if dependencies unavailable
2. **Fast Iteration**: 2-minute deployment, not 20+ minutes
3. **Dynamic Configuration**: Runtime queries, not deployment-time
4. **Separation of Concerns**: Images separate from deployment
5. **Pinned Versions**: Requirements files for reproducibility

## Success Criteria

1. ✅ JupyterHub deployment completes in 2 minutes
2. ✅ Images discovered dynamically from thinkube-control
3. ✅ No fallback mechanisms - fails when dependencies unavailable
4. ✅ Notebooks persist via SeaweedFS (mandatory)
5. ✅ Hybrid storage working (SeaweedFS + local scratch)
6. ✅ GPU pods schedulable on any GPU node
7. ✅ Keycloak authentication mandatory

## Architecture Benefits

### Separation of Concerns
- **custom-images**: Handles all Docker builds (slow, 20+ min)
- **jupyterhub**: Only deploys, no building (fast, 2 min)
- **thinkube-control**: Central image registry and management

### Dynamic Runtime Configuration
- No static image lists in deployment
- Profiles generated from API at runtime
- Images can be added/removed without redeployment

### Fast Development Cycle
- Deploy JupyterHub in 2 minutes
- Build images separately when needed
- Update images without touching JupyterHub

## Summary

This architecture achieves all goals:
- **Fast iteration**: 2-minute deployments
- **No overengineering**: Simple, direct solutions
- **No fallbacks**: Fails fast when dependencies unavailable
- **Dynamic configuration**: Runtime discovery from thinkube-control
- **Pinned versions**: Reproducible builds with requirements.txt
- **GPU flexibility**: Runs on any GPU node
- **Persistent storage**: SeaweedFS mandatory, no conditionals