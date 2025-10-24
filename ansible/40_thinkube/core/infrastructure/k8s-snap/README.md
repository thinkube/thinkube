# Canonical Kubernetes (k8s-snap) Installation Guide

## Overview

Canonical Kubernetes deployed via snap on Ubuntu systems.

**Tested on**: DGX Spark (ARM64) with Ubuntu 24.04.3 LTS, NVIDIA Blackwell GB10 GPU, driver 580.95.05

## Critical Prerequisites

### 1. UFW Firewall Configuration

**CRITICAL**: This is MANDATORY or CoreDNS will fail with 503 errors.

#### Enable IP Forwarding

`/etc/sysctl.conf`:
```
net.ipv4.ip_forward=1
```

Apply:
```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

#### Set UFW Forward Policy

`/etc/default/ufw`:
```
DEFAULT_FORWARD_POLICY="ACCEPT"
```

**Without this setting, pods cannot reach the Kubernetes API server.**

#### Required Ports

```bash
# Kubernetes API server
sudo ufw allow 6443/tcp comment 'k8s API server'

# Kubelet
sudo ufw allow 10250/tcp comment 'k8s kubelet'

# k8s-snap cluster daemon
sudo ufw allow 6400/tcp comment 'k8s cluster daemon'

# Cilium CNI
sudo ufw allow 4240/tcp comment 'Cilium networking'
sudo ufw allow 8472/udp comment 'Cilium VXLAN'

# Cilium interfaces
sudo ufw allow in on cilium_host
sudo ufw allow out on cilium_host

# Reload
sudo ufw reload
```

#### Port Reference

| Port | Protocol | Service | Notes |
|------|----------|---------|-------|
| 6443 | TCP | kube-apiserver | All nodes |
| 6400 | TCP | k8sd | All nodes |
| 10250 | TCP | kubelet | All nodes |
| 4240 | TCP | cilium-agent | All nodes |
| 8472 | UDP | cilium-agent | All nodes (VXLAN) |
| 2379 | TCP | etcd | Control plane only |
| 2380 | TCP | etcd peer | Control plane only |

### 2. Conflicting Software

Check and stop Docker if running:
```bash
sudo systemctl stop docker 2>/dev/null || true
sudo systemctl disable docker 2>/dev/null || true
```

k8s-snap manages its own containerd instance and will conflict with system containerd/docker.

### 3. System Requirements

- **OS**: Ubuntu 24.04 LTS
- **CPU**: 16 cores minimum
- **Memory**: 64GB minimum
- **Disk**: 1TB minimum

## Installation

### 1. Install k8s-snap

```bash
sudo snap install k8s --classic --channel=1.34-classic/stable
```

**Tested version**: 1.34.0 (from 1.34-classic/stable channel)

### 2. Bootstrap Cluster

```bash
sudo k8s bootstrap
```

Enables by default:
- Cilium CNI
- CoreDNS
- Local storage

### 3. Verify

```bash
sudo k8s status --wait-ready
```

Expected output:
```
cluster status:           ready
network:                  enabled
dns:                      enabled at 10.152.183.X
```

Check pods:
```bash
sudo k8s kubectl get pods -n kube-system
```

All should be Running:
- `cilium-*`: 1/1
- `cilium-operator-*`: 1/1
- `coredns-*`: 1/1
- `metrics-server-*`: 1/1
- `ck-storage-*`: 2/2 (controller), 4/4 (node)

## GPU Operator Installation

### Prerequisites

- NVIDIA drivers installed on host
- Verify: `nvidia-smi`

### Installation

```bash
sudo k8s helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
sudo k8s helm repo update

sudo k8s helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --version v25.3.4 \
  --set driver.enabled=false \
  --wait --timeout 10m
```

### Verification

```bash
# Check pods
sudo k8s kubectl get pods -n gpu-operator

# Verify GPU advertised
sudo k8s kubectl describe node | grep nvidia.com/gpu
```

Expected output:
```
  nvidia.com/gpu:     1
  nvidia.com/gpu:     1
```

### DGX Spark Specific

Expected warning (this is normal):
```
Ignoring error getting device memory: Not Supported
```

This is documented behavior for DGX Spark's Unified Memory Architecture (UMA).
See: https://docs.nvidia.com/dgx/dgx-spark/known-issues.html

## Key Paths

```
Containerd socket:     /run/containerd/containerd.sock
Containerd config:     /etc/containerd/config.toml
Kubeconfig:           /etc/kubernetes/admin.conf
kubectl:              sudo k8s kubectl
helm:                 sudo k8s helm
Local storage:        /var/snap/k8s/common/rawfile-storage
```

## Troubleshooting

### CoreDNS Readiness Probe Failed (503)

**Root cause**: UFW forward policy is DROP or ports blocked

**Fix**:
1. Verify `/etc/default/ufw` has `DEFAULT_FORWARD_POLICY="ACCEPT"`
2. Verify all ports listed above are open
3. `sudo ufw reload`
4. Delete CoreDNS pod: `sudo k8s kubectl delete pod -n kube-system coredns-*`
5. Wait 60 seconds, verify: `sudo k8s kubectl get pods -n kube-system`

### GPU Operator Pod Warnings

**Warning about nvidia runtime not configured**: Normal during initialization. Pods should reach Running state within 5 minutes.

## Testing

### DNS Resolution
```bash
sudo k8s kubectl run test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -k https://kubernetes.default.svc.cluster.local:443/version
```
Expected: `401 Unauthorized` (means DNS and API connectivity work)

### External Connectivity
```bash
sudo k8s kubectl run test --image=busybox --rm -it --restart=Never -- ping -c 2 8.8.8.8
```

## Worker Node Joining

k8s-snap uses a simpler token-based join process compared to MicroK8s.

### Process

**1. Generate join token (on control plane)**:
```bash
sudo k8s get-join-token <worker-hostname> --worker
```

This outputs a base64 token.

**2. Join worker to cluster (on worker node)**:
```bash
sudo k8s join-cluster <token>
```

**3. Verify**:
```bash
sudo k8s kubectl get nodes
```

### Prerequisites for Workers
- k8s-snap installed: `sudo snap install k8s --classic --channel=1.34-classic/stable`
- Same UFW configuration as control plane
- Docker stopped/disabled if present
- Network connectivity to control plane (port 6400)

## Playbook Requirements

The Ansible playbooks must handle:

### Control Plane (10_install_k8s.yaml)
1. **UFW Configuration** (critical)
   - Set IP forwarding in sysctl
   - Set forward policy to ACCEPT
   - Add all required port rules
   - Reload UFW

2. **DGX Spark Specific**
   - Stop and disable pre-installed Docker

3. **Installation**
   - Install k8s snap from 1.34-classic/stable channel
   - Bootstrap cluster
   - Wait for ready state

4. **Validation**
   - Check all system pods are Running
   - Verify CoreDNS is 1/1 Ready
   - Test pod connectivity

5. **GPU Operator** (if GPU present)
   - Verify nvidia-smi works
   - Install GPU Operator v25.3.4
   - Wait for all pods Running
   - Verify GPU resources advertised

### Worker Nodes (20_join_workers.yaml)
1. **UFW Configuration** (same as control plane)

2. **DGX Spark Specific**
   - Stop and disable Docker if present

3. **Installation**
   - Install k8s snap
   - Do NOT bootstrap (workers don't bootstrap)

4. **Join Cluster**
   - Get join token from control plane
   - Execute join-cluster command
   - Wait for node to be Ready

5. **Validation**
   - Verify node appears in cluster
   - Check node is Ready
   - Verify system pods running on worker

## References

- [Canonical Kubernetes Docs](https://documentation.ubuntu.com/canonical-kubernetes/latest/)
- [UFW Configuration](https://documentation.ubuntu.com/canonical-kubernetes/latest/snap/howto/networking/ufw/)
- [Ports Reference](https://documentation.ubuntu.com/canonical-kubernetes/latest/snap/reference/ports-and-services/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/)
- [DGX Spark Known Issues](https://docs.nvidia.com/dgx/dgx-spark/known-issues.html)
