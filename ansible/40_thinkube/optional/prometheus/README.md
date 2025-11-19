# Prometheus

Component #31 in the Thinkube Platform stack.

## Overview

Prometheus is a complete metrics collection and monitoring system deployed via the [kube-prometheus](https://github.com/prometheus-operator/kube-prometheus) stack. It provides comprehensive observability for the entire Thinkube platform with recording rules optimized for Kubernetes workloads.

**Key Features**:
- **Prometheus Operator**: Manages Prometheus, Alertmanager, and related monitoring components
- **Recording Rules**: Pre-configured kubernetes-mixin rules for efficient metric aggregation
- **Multi-component Exporters**: kube-state-metrics, node-exporter, blackbox-exporter, prometheus-adapter
- **GPU Monitoring**: NVIDIA DCGM exporter integration for ML workload metrics
- **Ingress Monitoring**: NGINX Ingress Controller metrics collection
- **Perses Integration**: Recording rules compatible with Perses community dashboards

## Dependencies

This component depends on the following Thinkube components:

- **Kubernetes (#6)** - Provides the container orchestration platform

## Prerequisites

```yaml
requirements:
  kubernetes:
    version: "1.34.0"
    provider: "k8s-snap"

  resources:
    prometheus:
      replicas: 2
      persistence: true
    alertmanager:
      replicas: 3
      persistence: true

  network:
    namespace: monitoring
    access: port-forward

  tools:
    - go: "1.23.5"
    - jsonnet: latest
    - jsonnet-bundler: latest
    - gojsontoyaml: latest
    - percli: "0.52.0"
```

## Playbooks

### **Tool Installation**
**File**: [10_install_tools.yaml](10_install_tools.yaml)

Installs required tooling on the control plane for kube-prometheus deployment:

- **Go Programming Language** (1.23.5)
  - Installed to `/usr/local/go`
  - Added to PATH via `/etc/profile.d/go.sh`
  - Required for jsonnet tooling

- **jsonnet Compiler**
  - Compiles jsonnet to JSON for manifest generation
  - Installed via `go install github.com/google/go-jsonnet/cmd/jsonnet@latest`
  - Symlinked to `/usr/local/bin/jsonnet`

- **jsonnet-bundler (jb)**
  - Manages jsonnet dependencies
  - Installed via `go install github.com/jsonnet-bundler/jsonnet-bundler/cmd/jb@latest`

- **gojsontoyaml**
  - Converts JSON manifests to YAML format
  - Required for kube-prometheus manifest generation

- **percli** (Perses CLI 0.52.0)
  - Downloads from GitHub releases (ARM64 and AMD64 support)
  - Extracts and installs to `/usr/local/bin/percli`
  - Used for automated dashboard deployment to Perses

### **Main Deployment**
**File**: [11_deploy.yaml](11_deploy.yaml)

Deploys Prometheus Operator with kube-prometheus stack following the official quickstart:

- **kube-prometheus Release** (v0.14.0)
  - Downloads and extracts pre-built manifests
  - Includes all recording rules from kubernetes-mixin

- **Setup Phase**
  - Creates `monitoring` namespace
  - Deploys CustomResourceDefinitions (CRDs)
  - Waits for CRDs to be established (300s timeout)

- **Main Deployment Phase**
  - Patches Prometheus manifest to add `cluster: ""` external label
  - Deploys Prometheus Operator
  - Deploys Prometheus (StatefulSet with 2 replicas)
  - Deploys Alertmanager (StatefulSet with 3 replicas)
  - Deploys kube-state-metrics
  - Deploys node-exporter (DaemonSet on all nodes)
  - Deploys blackbox-exporter
  - Deploys prometheus-adapter

- **Recording Rules Verification**
  - Lists all deployed PrometheusRule resources
  - Verifies kubernetes-mixin recording rules exist
  - Checks for `node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate`

- **Network Policy Configuration**
  - Patches `prometheus-k8s` NetworkPolicy to allow Perses namespace access
  - Opens port 9090/TCP for cross-namespace queries

- **ServiceMonitor Configuration**
  - Creates ServiceMonitor for NVIDIA DCGM Exporter (gpu-operator namespace)
  - Creates ServiceMonitor for NGINX Ingress Controller (ingress namespace)
  - Configures 30s scrape interval for both

### **Service Discovery**
**File**: [17_service_discovery.yaml](17_service_discovery.yaml)

Registers Prometheus with Thinkube service discovery system:

- **ConfigMap Creation** (`thinkube-service-config` in `monitoring` namespace)
  - Service type: `optional`
  - Category: `monitoring`
  - Icon: `/icons/tk_monitoring.svg`

- **Endpoints Registered**:
  - Primary: Prometheus server at `https://prometheus.example.com` (health: `/-/healthy`)
  - Secondary: Alertmanager at `https://alertmanager.example.com` (health: `/-/healthy`)

- **Metadata**:
  - Authentication: `none` (port-forward access)
  - Persistence: `true` (StatefulSet with PVCs)
  - License: `Apache-2.0`

- **Environment Variables**:
  - `PROMETHEUS_URL`: `https://prometheus.example.com`
  - `ALERTMANAGER_URL`: `https://alertmanager.example.com`

## Deployment

This component is automatically deployed via the **thinkube-control Optional Components interface**:

1. Navigate to https://thinkube.example.com/optional-components
2. Locate the **Prometheus** card in the **Monitoring** section
3. Click **Install** to deploy the component
4. Monitor real-time deployment progress via WebSocket streaming
5. Verify deployment status in the dashboard

The deployment executes the orchestrator playbook at `/ansible/40_thinkube/optional/prometheus/00_install.yaml`.

**Deployment Sequence**:
1. Install tooling (Go, jsonnet, jb, gojsontoyaml, percli)
2. Download kube-prometheus v0.14.0 release
3. Apply setup manifests (namespace, CRDs)
4. Apply main manifests (Prometheus, Alertmanager, exporters, recording rules)
5. Configure network policies for Perses integration
6. Create ServiceMonitors for GPU and Ingress metrics
7. Register with service discovery

## Access Points

Prometheus does not have ingress configured by default. Access is via port-forward:

### Prometheus Server

```bash
kubectl port-forward -n monitoring svc/prometheus-k8s 9090:9090
```

Then access at: http://localhost:9090

### Alertmanager

```bash
kubectl port-forward -n monitoring svc/alertmanager-main 9093:9093
```

Then access at: http://localhost:9093

### Grafana (from kube-prometheus)

```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

Then access at: http://localhost:3000
- Default credentials: `admin` / `admin`

## Configuration

### Recording Rules

The kubernetes-mixin recording rules are automatically deployed with kube-prometheus. These rules are required for Perses community dashboards.

**Key Recording Rules**:
- `node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate` - CPU usage aggregation
- `node_namespace_pod_container:container_memory_working_set_bytes` - Memory usage aggregation
- `namespace_workload_pod:kube_pod_owner:relabel` - Pod ownership mapping
- Many others for efficient dashboard queries

To view all recording rules:

```bash
kubectl get prometheusrule -n monitoring -o yaml
```

### External Labels

Prometheus is configured with a `cluster` external label (defaults to empty string). This can be customized in the [11_deploy.yaml](11_deploy.yaml:109) manifest patching step.

### ServiceMonitor Configuration

Prometheus automatically discovers metrics endpoints via ServiceMonitor resources:

**Included ServiceMonitors**:
- All kube-prometheus built-in monitors (kubelet, apiserver, kube-state-metrics, node-exporter)
- NVIDIA DCGM Exporter (GPU metrics from `gpu-operator` namespace)
- NGINX Ingress Controller (HTTP metrics from `ingress` namespace)

To add additional ServiceMonitors, create them in the `monitoring` namespace with appropriate selectors.

### Resource Scaling

Prometheus and Alertmanager are deployed as StatefulSets:

**Prometheus**:
- Replicas: 2 (HA configuration)
- Resource type: StatefulSet `prometheus-k8s`
- Namespace: `monitoring`

**Alertmanager**:
- Replicas: 3 (quorum-based HA)
- Resource type: StatefulSet `alertmanager-main`
- Namespace: `monitoring`

To scale Prometheus:

```bash
kubectl scale statefulset prometheus-k8s -n monitoring --replicas=3
```

## Integration

### Perses Dashboard Platform

Prometheus is designed to integrate with Perses for dashboard visualization:

- **Network Policy**: Configured to allow Perses namespace access to port 9090
- **Recording Rules**: kubernetes-mixin rules are compatible with Perses community dashboards
- **Query Endpoint**: `http://prometheus-k8s.monitoring.svc.cluster.local:9090`

### GPU Monitoring (NVIDIA DCGM)

ServiceMonitor automatically discovers NVIDIA DCGM Exporter metrics:

- **Namespace**: `gpu-operator`
- **Service Label**: `app: nvidia-dcgm-exporter`
- **Port**: `gpu-metrics`
- **Scrape Interval**: 30s

Metrics include GPU utilization, memory usage, temperature, power consumption, etc.

### Ingress Monitoring

ServiceMonitor collects NGINX Ingress Controller metrics:

- **Namespace**: `ingress`
- **Service Labels**: `app.kubernetes.io/name: ingress-nginx`, `app.kubernetes.io/component: controller`
- **Port**: `metrics`
- **Scrape Interval**: 30s

Metrics include request rates, latencies, upstream response times, etc.

## Troubleshooting

### Verify Deployment Status

Check Prometheus Operator:

```bash
kubectl get deployment prometheus-operator -n monitoring
```

Check Prometheus StatefulSet:

```bash
kubectl get statefulset prometheus-k8s -n monitoring
kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus
```

Check Alertmanager StatefulSet:

```bash
kubectl get statefulset alertmanager-main -n monitoring
kubectl get pods -n monitoring -l app.kubernetes.io/name=alertmanager
```

### Verify Recording Rules

List all PrometheusRule resources:

```bash
kubectl get prometheusrule -n monitoring
```

Check specific kubernetes-mixin recording rule:

```bash
kubectl get prometheusrule -n monitoring -o yaml | grep "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate"
```

### Check Prometheus Logs

```bash
kubectl logs -n monitoring prometheus-k8s-0 -c prometheus
```

### Verify ServiceMonitors

List all ServiceMonitors:

```bash
kubectl get servicemonitor -n monitoring
```

Check if Prometheus is scraping targets:

```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-k8s 9090:9090

# Then visit http://localhost:9090/targets in browser
```

### Network Policy Issues

If Perses cannot query Prometheus, verify network policy:

```bash
kubectl get networkpolicy prometheus-k8s -n monitoring -o yaml
```

Should include ingress rule for `perses` namespace.

### Common Issues

**Issue**: CRDs not established within timeout
- **Solution**: Wait longer or check API server logs. CRDs can take time on slower systems.

**Issue**: Prometheus pods stuck in Pending
- **Solution**: Check PVC status. Prometheus requires persistent storage.

```bash
kubectl get pvc -n monitoring
```

**Issue**: Recording rules not loading
- **Solution**: Check PrometheusRule resources and Prometheus logs for syntax errors.

**Issue**: ServiceMonitors not discovering targets
- **Solution**: Verify service label selectors match the target service labels exactly.

## Testing

The test playbook [18_test.yaml](18_test.yaml) verifies:
- Prometheus Operator deployment is running
- Prometheus StatefulSet has ready replicas
- Alertmanager StatefulSet has ready replicas
- PrometheusRule resources exist
- Recording rules are loaded
- ServiceMonitors are configured

## Rollback

To uninstall Prometheus:

```bash
cd ~/thinkube
./scripts/tk_ansible ansible/40_thinkube/optional/prometheus/19_rollback.yaml
```

**Warning**: This will delete all Prometheus data and configurations. Backup any important data before uninstalling.

## References

- [Prometheus Official Documentation](https://prometheus.io/docs/)
- [kube-prometheus GitHub](https://github.com/prometheus-operator/kube-prometheus)
- [Prometheus Operator Documentation](https://prometheus-operator.dev/)
- [kubernetes-mixin Recording Rules](https://github.com/kubernetes-monitoring/kubernetes-mixin)
- [Perses Integration Guide](../perses/README.md)

🤖 [AI-assisted]
