# NVIDIA GPU Operator

This component deploys the NVIDIA GPU Operator in the kubeadm cluster, enabling GPU support for containerized workloads.

## Installation

The GPU Operator is a core component. The Thinkube installer installs it by
running `00_install.yaml` in this folder
(`core/infrastructure/gpu_operator`), which runs these playbooks in order:

| Playbook | What it does |
|---|---|
| `10_deploy.yaml` | Host setup on every `baremetal_gpus` node (NVIDIA driver on non-DGX nodes, Docker NVIDIA runtime on DGX Spark), then the GPU Operator Helm install |
| `12_cap_gb10_clock.yaml` | Caps the GPU clock of GB10 (DGX Spark) nodes on every boot, to stop sudden power-offs under load |
| `15_configure_time_slicing.yaml` | GPU time-slicing: 4 virtual GPUs per GPU on DGX Spark, 2 on discrete GPUs |
| `17_configure_discovery.yaml` | Service-discovery ConfigMap |

`16_apply_node_profile.yaml` (the `dedicated-ai` node profile) is not part of
`00_install.yaml`. The component is not installed on its own.

## Description

The NVIDIA GPU Operator is a Kubernetes operator that automates the management of NVIDIA GPUs in Kubernetes clusters. It manages the installation and lifecycle of several components:

- NVIDIA drivers
- NVIDIA container toolkit
- NVIDIA Kubernetes device plugin
- NVIDIA MIG manager (if applicable)

## Requirements

- Kubernetes (kubeadm) cluster with at least one GPU-equipped node (Volta or newer)
- NVIDIA driver on the host: `10_deploy.yaml` installs the recommended driver on
  non-DGX nodes when `nvidia-smi` fails. The operator runs with
  `driver.enabled=false`.
- Helm 3.x installed
- kubernetes.core collection >= 2.3.0

## Usage

Deploy the GPU Operator:
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/gpu_operator/10_deploy.yaml
```

Test the GPU Operator:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/gpu_operator/18_test.yaml
```

Rollback the GPU Operator:
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/gpu_operator/19_rollback.yaml
```

## Configuration

The GPU Operator chart version is pinned in `10_deploy.yaml`
(`--version v26.3.1`). There is no inventory variable for it.

### Automatic Docker GPU Configuration

The deployment playbook configures Docker with NVIDIA runtime support on DGX Spark (GB10) nodes only. This enables GPU access for Docker containers, which is required for:

- NVIDIA NIM (NVIDIA Inference Microservices) containers
- NVIDIA educational materials and examples
- Docker-based GPU development workflows

**Configuration created**: `/etc/docker/daemon.json`
```json
{
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
```

**Usage**:
```bash
# Run a GPU-enabled container with Docker
docker run --runtime=nvidia --gpus all nvidia/cuda:12.5.0-base-ubuntu22.04 nvidia-smi
```

### Containerd Runtime Configuration

Containerd uses the standard paths under kubeadm:

1. The `containerd_install` role (`ansible/roles/containerd_install/`) writes
   `/etc/containerd/config.toml`. It configures `runc` with
   `SystemdCgroup = true` and imports `/etc/containerd/conf.d/*.toml`.
2. The GPU operator's nvidia-container-toolkit DaemonSet writes the drop-in
   `/etc/containerd/conf.d/99-nvidia.toml` with the `nvidia` runtime.
   `10_deploy.yaml` passes the toolkit these settings:
   - `CONTAINERD_CONFIG=/etc/containerd/config.toml`
   - `CONTAINERD_SOCKET=/run/containerd/containerd.sock`
   - `CONTAINERD_SET_AS_DEFAULT=true`
   - `RUNTIME_DROP_IN_CONFIG_HOST_PATH=/etc/containerd/conf.d/99-nvidia.toml`
3. Both configurations coexist. GPU pods can also ask for the `nvidia`
   RuntimeClass (`runtimeClassName: nvidia`).

New GPU nodes joining the cluster get both configurations without manual
steps: the join playbook runs the same `containerd_install` role, and the
toolkit DaemonSet runs on every GPU node.

## Testing

The 18_test.yaml playbook tests all aspects of the GPU Operator:

1. Checks if all components are installed and running
2. Verifies that GPU resources are available on the nodes
3. Runs a CUDA workload on each GPU node to validate functionality

## Troubleshooting

### GPU Operator Pods Not Running

If the deployment fails, check the following:

1. **Ensure NVIDIA drivers are correctly installed** on the host system:
   ```bash
   nvidia-smi
   # Should show GPU information and driver version
   ```

2. **Check GPU operator pod status**:
   ```bash
   kubectl get pods -n gpu-operator
   ```

   Expected pods:
   - `nvidia-device-plugin-daemonset-*`: Running (critical for GPU discovery)
   - `nvidia-container-toolkit-daemonset-*`: Running (critical for runtime config)
   - `nvidia-dcgm-exporter-*`: Running
   - `nvidia-operator-validator-*`: Completed or Running
   - `gpu-operator-*`: Running

3. **Examine logs of any pods in error state**:
   ```bash
   kubectl logs -n gpu-operator <pod-name>
   kubectl describe pod -n gpu-operator <pod-name>
   ```

### Node Becomes NotReady After GPU Operator Install

**Symptom**: Node shows `NotReady` status after GPU operator deploys.

**Check**: the base containerd configuration and its import line.

```bash
sudo containerd config dump | grep -n SystemdCgroup
grep imports /etc/containerd/config.toml
# Should show: imports = ["/etc/containerd/conf.d/*.toml"]
```

`/etc/containerd/config.toml` is written by the `containerd_install` role,
from `ansible/roles/containerd_install/templates/config.toml.j2`.

### GPUs Not Detected in Cluster

**Symptom**: `kubectl describe node` shows no `nvidia.com/gpu` resources.

**Check**:
1. **Verify nvidia-device-plugin-daemonset is running**:
   ```bash
   kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset
   ```

2. **Check nvidia-container-toolkit-daemonset created runtime config**:
   ```bash
   cat /etc/containerd/conf.d/99-nvidia.toml
   # Should contain nvidia runtime configuration
   ```

3. **Verify the drop-in is imported**:
   ```bash
   ls -la /etc/containerd/conf.d/
   # Should show: 99-nvidia.toml
   grep imports /etc/containerd/config.toml
   ```

4. **Check containerd is using configs**:
   ```bash
   kubectl get nodes -o json | jq '.items[].status.allocatable'
   # Should show "nvidia.com/gpu": "1" or higher
   ```

### Docker GPU Access Not Working

**Symptom**: `docker run --runtime=nvidia` fails with "unknown runtime" error.

**Solution**:
1. **Verify daemon.json exists**:
   ```bash
   cat /etc/docker/daemon.json
   ```

2. **Restart Docker**:
   ```bash
   sudo systemctl restart docker
   ```

3. **Test GPU access**:
   ```bash
   docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.5.0-base-ubuntu22.04 nvidia-smi
   ```

### DGX Spark Specific Issues

**Expected Warning** (this is normal):
```
Ignoring error getting device memory: Not Supported
```

This warning appears in nvidia-dcgm-exporter logs on DGX Spark due to its Unified Memory Architecture (UMA). GPU functionality is not affected.

**Reference**: [DGX Spark Known Issues](https://docs.nvidia.com/dgx/dgx-spark/known-issues.html)

### Additional Verification

Check the containerd socket the toolkit uses:
```bash
ls -la /run/containerd/containerd.sock
```
