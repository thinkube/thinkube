# NVIDIA GPU Operator

This component deploys the NVIDIA GPU Operator in the k8s-snap cluster, enabling GPU support for containerized workloads.

## Description

The NVIDIA GPU Operator is a Kubernetes operator that automates the management of NVIDIA GPUs in Kubernetes clusters. It manages the installation and lifecycle of several components:

- NVIDIA drivers
- NVIDIA container toolkit
- NVIDIA Kubernetes device plugin
- NVIDIA MIG manager (if applicable)

## Requirements

- k8s-snap cluster with at least one GPU-equipped node
- NVIDIA drivers installed on the host systems
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

The following inventory variables can be used to configure the GPU Operator:

| Variable | Description | Default |
|----------|-------------|---------|
| gpu_operator_version | Version of the GPU Operator to install | Latest |

### Automatic Docker GPU Configuration

The deployment playbook automatically configures Docker with NVIDIA runtime support for DGX Spark systems. This enables GPU access for Docker containers, which is required for:

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

### k8s-snap Containerd Runtime Fix

The deployment playbook works in conjunction with the k8s-snap installation playbook to ensure proper GPU runtime configuration. The k8s-snap playbook creates `/etc/containerd/conf.d/00-k8s-runc.toml` which prevents the GPU operator's nvidia-container-toolkit from breaking containerd.

**How it works**:
1. k8s-snap installation creates `00-k8s-runc.toml` with base runc runtime configuration
2. GPU operator's nvidia-container-toolkit DaemonSet creates `99-nvidia.toml` with nvidia runtime
3. Both configurations coexist, providing both `runc` (default) and `nvidia` (for GPU pods) runtimes

This configuration supports automatic scaling - new GPU nodes joining the cluster will automatically receive both configurations without manual intervention.

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

**Root Cause**: Missing runc runtime configuration in containerd.

**Solution**: Verify that `/etc/containerd/conf.d/00-k8s-runc.toml` exists. This file should have been created during k8s-snap installation. If missing, create it manually:

```bash
sudo tee /etc/containerd/conf.d/00-k8s-runc.toml > /dev/null <<'EOF'
version = 2

[plugins]
  [plugins."io.containerd.grpc.v1.cri"]
    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "runc"

      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
          runtime_type = "io.containerd.runc.v2"
          [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
            SystemdCgroup = true
EOF

# Restart k8s-snap containerd
sudo snap restart k8s.containerd
```

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

3. **Verify both runtime configs exist**:
   ```bash
   ls -la /etc/containerd/conf.d/
   # Should show:
   # 00-k8s-runc.toml
   # 99-nvidia.toml
   ```

4. **Check containerd is using configs**:
   ```bash
   sudo k8s kubectl get nodes -o json | jq '.items[].status.allocatable'
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

Check k8s-snap containerd configuration paths:
```bash
# Verify custom containerd paths (for Docker coexistence)
sudo k8s config get containerd-base-dir
# Should output: /var/lib/k8s-containerd

# Check containerd socket
ls -la /var/lib/k8s-containerd/k8s-containerd/run/containerd/containerd.sock
```