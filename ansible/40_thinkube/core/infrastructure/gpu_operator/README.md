# NVIDIA GPU Operator

This component deploys the NVIDIA GPU Operator in the MicroK8s cluster, enabling GPU support for containerized workloads.

## Description

The NVIDIA GPU Operator is a Kubernetes operator that automates the management of NVIDIA GPUs in Kubernetes clusters. It manages the installation and lifecycle of several components:

- NVIDIA drivers
- NVIDIA container toolkit
- NVIDIA Kubernetes device plugin
- NVIDIA MIG manager (if applicable)

## Requirements

- MicroK8s cluster with at least one GPU-equipped node
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

## Testing

The 18_test.yaml playbook tests all aspects of the GPU Operator:

1. Checks if all components are installed and running
2. Verifies that GPU resources are available on the nodes
3. Runs a CUDA workload on each GPU node to validate functionality

## Troubleshooting

If the deployment fails, check the following:

1. Ensure NVIDIA drivers are correctly installed on the host system
2. Check for errors in the GPU operator pods: 
   ```
   microk8s kubectl get pods -n gpu-operator
   ```
3. Examine logs of any pods in error state:
   ```
   microk8s kubectl logs -n gpu-operator <pod-name>
   ```
4. Verify containerd configuration in MicroK8s:
   ```
   cat /var/snap/microk8s/current/args/containerd-template.toml
   ```