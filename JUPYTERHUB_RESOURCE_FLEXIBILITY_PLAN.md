# JupyterHub Resource Flexibility Implementation Plan

## Overview
Enable flexible resource selection in JupyterHub with real-time availability information and GPU details for a single-user homelab environment.

## Implementation Phases

### Phase 1: Thinkube-Control API Implementation

#### Files to Create/Modify

##### 1. Create Cluster Resources API
**File**: `/home/thinkube/thinkube/thinkube-control/backend/app/api/cluster_resources.py`

```python
"""Cluster resources API for real-time resource availability"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from kubernetes import client, config
from kubernetes.stream import stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cluster", tags=["cluster-resources"])

def parse_memory(memory_str: str) -> int:
    """Parse Kubernetes memory string to bytes"""
    if memory_str.endswith('Ki'):
        return int(memory_str[:-2]) * 1024
    elif memory_str.endswith('Mi'):
        return int(memory_str[:-2]) * 1024 * 1024
    elif memory_str.endswith('Gi'):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024
    return int(memory_str)

def format_memory(bytes_val: int) -> str:
    """Format bytes to human readable string"""
    if bytes_val >= 1024 * 1024 * 1024:
        return f"{bytes_val // (1024 * 1024 * 1024)}Gi"
    elif bytes_val >= 1024 * 1024:
        return f"{bytes_val // (1024 * 1024)}Mi"
    elif bytes_val >= 1024:
        return f"{bytes_val // 1024}Ki"
    return str(bytes_val)

@router.get("/resources", response_model=List[Dict[str, Any]])
async def get_cluster_resources():
    """Get real-time cluster resource availability including GPU details"""

    try:
        # Load kubernetes config
        config.load_incluster_config()
        v1 = client.CoreV1Api()

        # Get all nodes
        nodes = v1.list_node()

        result = []
        for node in nodes.items:
            node_name = node.metadata.name

            # Get node capacity
            capacity = {
                "cpu": int(node.status.capacity.get("cpu", 0)),
                "memory": parse_memory(node.status.capacity.get("memory", "0")),
                "gpu": int(node.status.capacity.get("nvidia.com/gpu", 0))
            }

            # Calculate allocated resources from pods
            pods = v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )

            allocated_cpu = 0
            allocated_memory = 0
            allocated_gpu = 0

            for pod in pods.items:
                # Skip terminated pods
                if pod.status.phase in ["Succeeded", "Failed"]:
                    continue

                for container in pod.spec.containers:
                    if container.resources:
                        if container.resources.limits:
                            # CPU
                            cpu_limit = container.resources.limits.get("cpu", "0")
                            if cpu_limit.endswith('m'):
                                allocated_cpu += int(cpu_limit[:-1]) / 1000
                            else:
                                allocated_cpu += float(cpu_limit)

                            # Memory
                            mem_limit = container.resources.limits.get("memory", "0")
                            if mem_limit != "0":
                                allocated_memory += parse_memory(mem_limit)

                            # GPU
                            gpu_limit = container.resources.limits.get("nvidia.com/gpu", "0")
                            allocated_gpu += int(gpu_limit)

            # Get GPU details if node has GPUs
            gpu_details = []
            if capacity["gpu"] > 0:
                try:
                    gpu_details = await get_gpu_details(node_name, v1)
                except Exception as e:
                    logger.warning(f"Could not get GPU details for {node_name}: {e}")
                    # Create basic GPU info without nvidia-smi details
                    for i in range(capacity["gpu"]):
                        gpu_details.append({
                            "index": i,
                            "model": "Unknown GPU",
                            "memory_total": "Unknown",
                            "memory_used": "Unknown",
                            "memory_free": "Unknown",
                            "available": i >= allocated_gpu
                        })

            # Calculate available resources
            available = {
                "cpu": capacity["cpu"] - allocated_cpu,
                "memory": capacity["memory"] - allocated_memory,
                "gpu": capacity["gpu"] - allocated_gpu
            }

            result.append({
                "name": node_name,
                "capacity": {
                    "cpu": capacity["cpu"],
                    "memory": format_memory(capacity["memory"]),
                    "gpu": capacity["gpu"]
                },
                "allocated": {
                    "cpu": round(allocated_cpu, 2),
                    "memory": format_memory(allocated_memory),
                    "gpu": allocated_gpu
                },
                "available": {
                    "cpu": round(available["cpu"], 2),
                    "memory": format_memory(available["memory"]),
                    "gpu": available["gpu"]
                },
                "gpu_details": gpu_details
            })

        return result

    except Exception as e:
        logger.error(f"Failed to get cluster resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_gpu_details(node_name: str, v1: client.CoreV1Api) -> List[Dict[str, Any]]:
    """Get detailed GPU information from nvidia-smi via gpu-operator pod"""

    # Find nvidia driver pod on this node
    pods = v1.list_namespaced_pod(
        namespace="gpu-operator",
        field_selector=f"spec.nodeName={node_name}"
    )

    driver_pod = None
    for pod in pods.items:
        if "nvidia-driver" in pod.metadata.name and pod.status.phase == "Running":
            driver_pod = pod
            break

    if not driver_pod:
        raise Exception(f"No running nvidia-driver pod found on node {node_name}")

    # Execute nvidia-smi to get GPU details
    exec_command = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader"
    ]

    response = stream(
        v1.connect_get_namespaced_pod_exec,
        driver_pod.metadata.name,
        "gpu-operator",
        command=exec_command,
        stderr=False,
        stdin=False,
        stdout=True,
        tty=False
    )

    gpus = []
    for line in response.strip().split('\n'):
        if line:
            parts = [p.strip() for p in line.split(',')]

            # Check if GPU is available (low utilization and low memory usage)
            memory_used = parts[3]
            memory_used_val = int(memory_used.split()[0]) if ' ' in memory_used else 0
            utilization = int(parts[5].split()[0]) if ' ' in parts[5] else 0

            gpus.append({
                "index": int(parts[0]),
                "model": parts[1],
                "memory_total": parts[2],
                "memory_used": parts[3],
                "memory_free": parts[4],
                "utilization": utilization,
                "available": memory_used_val < 100 and utilization < 5
            })

    return gpus
```

##### 2. Update Main Router
**File**: `/home/thinkube/thinkube/thinkube-control/backend/app/main.py`

Add this import and router inclusion:
```python
from app.api import cluster_resources

# Add after other router inclusions
app.include_router(cluster_resources.router, prefix="/api/v1")
```

#### Testing Phase 1

After implementing the API:
1. Deploy thinkube-control changes
2. Test the API endpoint:
   ```bash
   curl -s https://control.thinkube.com/api/v1/cluster/resources | jq
   ```
3. Verify response includes:
   - Node names and resources
   - GPU details with model and memory
   - Accurate available resources

Expected response format:
```json
[
  {
    "name": "vilanova1",
    "capacity": {"cpu": 16, "memory": "64Gi", "gpu": 1},
    "allocated": {"cpu": 4.5, "memory": "10Gi", "gpu": 0},
    "available": {"cpu": 11.5, "memory": "54Gi", "gpu": 1},
    "gpu_details": [
      {
        "index": 0,
        "model": "NVIDIA GeForce RTX 4090",
        "memory_total": "24576 MiB",
        "memory_used": "0 MiB",
        "memory_free": "24576 MiB",
        "utilization": 0,
        "available": true
      }
    ]
  }
]
```

---

### Phase 2: JupyterHub Implementation

#### Files to Modify

##### Update JupyterHub Values Template
**File**: `/home/thinkube/thinkube/ansible/40_thinkube/optional/jupyterhub/templates/jupyterhub-values.yaml.j2`

Replace the current `get_profile_list` function with:

```python
    01-dynamic-profile-generator: |
      # Dynamic profile generation with flexible resource selection
      import requests
      import sys
      import logging

      def get_profile_list(spawner):
          """Generate profiles with flexible resource selection forms"""
          logging.basicConfig(level=logging.INFO)
          logger = logging.getLogger(__name__)

          try:
              # Query thinkube-control for available resources
              logger.info("Querying thinkube-control for cluster resources...")
              resources_response = requests.get(
                  'http://backend.thinkube-control:8000/api/v1/cluster/resources',
                  headers={'Accept': 'application/json'},
                  timeout=10
              )

              if resources_response.status_code != 200:
                  logger.error(f"Failed to get cluster resources: {resources_response.status_code}")
                  sys.exit(1)

              resources = resources_response.json()

              # Query for available images
              logger.info("Querying thinkube-control for available images...")
              images_response = requests.get(
                  'http://backend.thinkube-control:8000/api/v1/images/jupyter',
                  headers={'Accept': 'application/json'},
                  timeout=10
              )

              if images_response.status_code != 200:
                  logger.error(f"Failed to get images: {images_response.status_code}")
                  sys.exit(1)

              images = images_response.json()
              profiles = []

              for img in images:
                  # Build node choices with resource info
                  node_choices = {}
                  for node in resources:
                      node_label = (f"{node['name']} "
                                  f"({node['available']['cpu']}/{node['capacity']['cpu']} CPUs, "
                                  f"{node['available']['memory']}/{node['capacity']['memory']}")

                      # Add GPU info if available
                      if node['gpu_details']:
                          available_gpus = [g for g in node['gpu_details'] if g['available']]
                          if available_gpus:
                              gpu = available_gpus[0]
                              node_label += f", GPU: {gpu['model']} {gpu['memory_total']}"
                          else:
                              node_label += ", GPU: In use"
                      else:
                          node_label += ", No GPU"

                      node_label += ")"
                      node_choices[node['name']] = node_label

                  # Create profile with options form
                  profile = {
                      'display_name': img.get('display_name', img['name']),
                      'description': f"{img.get('description', '')} - Select your resources below",
                      'default': img.get('default', False),
                      'profile_options': {
                          'image': {
                              'display_name': 'Hidden Image',
                              'choices': {img['name']: img['name']},
                              'default': img['name']
                          },
                          'node': {
                              'display_name': 'Select Node',
                              'choices': node_choices,
                              'default': list(node_choices.keys())[0] if node_choices else 'vilanova1'
                          },
                          'cpu': {
                              'display_name': 'CPU Cores',
                              'choices': {
                                  '1': '1 core',
                                  '2': '2 cores',
                                  '4': '4 cores',
                                  '6': '6 cores',
                                  '8': '8 cores',
                                  '12': '12 cores',
                                  '16': '16 cores',
                                  '24': '24 cores',
                                  '32': '32 cores'
                              },
                              'default': '4'
                          },
                          'memory': {
                              'display_name': 'Memory',
                              'choices': {
                                  '2Gi': '2 GB',
                                  '4Gi': '4 GB',
                                  '8Gi': '8 GB',
                                  '16Gi': '16 GB',
                                  '32Gi': '32 GB',
                                  '48Gi': '48 GB',
                                  '64Gi': '64 GB',
                                  '96Gi': '96 GB',
                                  '128Gi': '128 GB'
                              },
                              'default': '8Gi'
                          },
                          'enable_gpu': {
                              'display_name': 'Enable GPU',
                              'choices': {
                                  '0': 'No GPU',
                                  '1': 'Use GPU (if available)'
                              },
                              'default': '0'
                          }
                      },
                      'kubespawner_override': {
                          'image': f"{{ harbor_registry }}/library/{img['name']}:latest",
                          'image_pull_policy': 'Always'
                      }
                  }
                  profiles.append(profile)

              if not profiles:
                  logger.error("No profiles could be generated")
                  sys.exit(1)

              logger.info(f"Successfully generated {len(profiles)} profiles with resource options")
              return profiles

          except Exception as e:
              logger.error(f"Failed to generate profiles: {e}")
              sys.exit(1)

      def apply_profile_options(spawner, user_options):
          """Apply the selected options to the spawner"""
          import logging
          logger = logging.getLogger(__name__)

          # Get selected options
          profile = user_options.get('profile', {})
          image = profile.get('image')
          node = profile.get('node')
          cpu = profile.get('cpu', '4')
          memory = profile.get('memory', '8Gi')
          enable_gpu = profile.get('enable_gpu', '0')

          logger.info(f"Applying options: node={node}, cpu={cpu}, memory={memory}, gpu={enable_gpu}")

          # Apply to spawner
          if node:
              spawner.node_selector = {"kubernetes.io/hostname": node}

          spawner.cpu_limit = float(cpu)
          spawner.cpu_guarantee = float(cpu) * 0.5  # 50% guarantee
          spawner.mem_limit = memory
          spawner.mem_guarantee = memory

          if enable_gpu == '1':
              spawner.extra_resource_limits = {"nvidia.com/gpu": "1"}
              spawner.extra_resource_guarantees = {"nvidia.com/gpu": "1"}
              logger.info("GPU enabled for this session")

          return spawner

      # Set the configurations
      c.KubeSpawner.profile_list = get_profile_list
      c.JupyterHub.spawner_class = 'kubespawner.KubeSpawner'

      # Enable profile options
      from kubespawner import KubeSpawner

      class CustomKubeSpawner(KubeSpawner):
          def load_user_options(self):
              """Load user options and apply them"""
              super().load_user_options()
              if self.user_options:
                  apply_profile_options(self, self.user_options)

      c.JupyterHub.spawner_class = CustomKubeSpawner
```

#### Testing Phase 2

After implementing JupyterHub changes:
1. Deploy JupyterHub with updated configuration
2. Access JupyterHub UI
3. Verify when spawning:
   - Form shows with resource selection options
   - Node dropdown shows real-time availability
   - GPU information is visible
   - Can select exact CPU and memory
4. Test spawning with different resource combinations

## Success Criteria

### Phase 1 Success:
- [ ] API endpoint `/api/v1/cluster/resources` returns 200
- [ ] Response includes accurate CPU/memory availability
- [ ] GPU details include model and memory size
- [ ] Real-time data reflects actual cluster state

### Phase 2 Success:
- [ ] JupyterHub shows resource selection form
- [ ] Can select specific node, CPU, memory, GPU
- [ ] Spawned notebooks have requested resources
- [ ] GPU allocation works when selected

## Rollback Plan

If issues occur:

### Phase 1 Rollback:
```bash
cd /home/thinkube/thinkube/thinkube-control
git revert HEAD
git push
# Redeploy thinkube-control
```

### Phase 2 Rollback:
```bash
cd /home/thinkube/thinkube
git revert HEAD
./scripts/run_ansible.sh ansible/40_thinkube/optional/jupyterhub/11_deploy.yaml
```

## Notes

- This implementation is optimized for single-user homelab use
- No reservation system needed (single user)
- Real-time queries are fast enough without caching
- GPU availability is checked via nvidia-smi for consumer GPUs