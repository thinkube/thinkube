# Perses Observability Platform

Component #40 in the Thinkube Platform stack.

## Installation

Perses is an optional component. It is installed and removed from the Optional Components page in thinkube-control, not on its own. thinkube-control runs `00_install.yaml` to install, `18_test.yaml` to test and `19_rollback.yaml` to remove it.

## Overview

Perses is a modern, open-source observability visualization platform designed as a cloud-native alternative to Grafana. It provides native support for Prometheus metrics (PromQL), Tempo distributed tracing, Loki log aggregation, and Pyroscope continuous profiling. Perses features Dashboard-as-Code capabilities using Kubernetes CRDs, making dashboards versionable and deployable alongside applications.

This component deploys Perses with Keycloak SSO authentication, persistent storage for dashboards, and automatically imports a curated collection of 25+ monitoring dashboards for Kubernetes, node metrics, Prometheus, AlertManager, NGINX Ingress, and GPU monitoring.

## Dependencies

This component depends on the following Thinkube components:

- **Kubernetes (#6)** - Provides the container orchestration platform
- **ACME Certificates (#12)** - Secures HTTPS connections
- **Gateway API** - Routes external traffic to Perses web interface (HTTPRoute `perses`)
- **Keycloak (#15)** - Provides SSO authentication for Perses
- **Prometheus (#31)** - Provides metrics datasource (required dependency)

## Prerequisites

To deploy this component, ensure the following variables are configured in your Ansible inventory:

```yaml
# Domain configuration
domain_name: "example.com"
perses_hostname: "perses.example.com"

# Kubernetes configuration
kubeconfig: "/path/to/kubeconfig"
kubectl_bin: "/home/<system_username>/.local/bin/kubectl"
helm_bin: "/home/<system_username>/.local/bin/helm"

# Namespace
perses_namespace: "perses"
prometheus_namespace: "monitoring"

# Keycloak configuration
keycloak_url: "https://keycloak.example.com"
keycloak_realm: "thinkube"
admin_username: "admin"

# Gateway (defaults used by 11_deploy.yaml)
gateway_name: "thinkube-gateway"
gateway_namespace: "gateway-system"

# Environment variables
ADMIN_PASSWORD: "your-admin-password"  # Required for deployment
```

## Playbooks

| Playbook | What it does |
|---|---|
| [00_install.yaml](00_install.yaml) | Runs `10_configure_keycloak.yaml`, `11_deploy.yaml`, `14_import_dashboards_percli.yaml` and `17_configure_discovery.yaml` in that order. |
| [10_configure_keycloak.yaml](10_configure_keycloak.yaml) | Creates the realm roles `perses-admin` and `perses-user`, the confidential OIDC client `perses` with its role and audience mappers, and gives the admin user `perses-admin`. |
| [11_deploy.yaml](11_deploy.yaml) | Creates the `perses` namespace, copies the wildcard certificate, reads the Keycloak client secret, deploys Helm chart 0.17.1 (Perses 0.52.0) with `values-thinkube.yaml`, sets priority class `thinkube-workload` on the `perses` StatefulSet, creates the HTTPRoute `perses`, and creates the native admin user. |
| [14_import_dashboards_percli.yaml](14_import_dashboards_percli.yaml) | Clones [thinkube-monitor](https://github.com/thinkube/thinkube-monitor), logs in with percli, creates six projects and a Prometheus datasource (`http://prometheus-k8s.monitoring.svc.cluster.local:9090`) in each, and imports the dashboards. |
| [17_configure_discovery.yaml](17_configure_discovery.yaml) | Creates the `thinkube-service-config` ConfigMap for thinkube-control (web endpoint, health check `/api/health`, dependencies `prometheus` and `keycloak`, variables `PERSES_URL`, `PERSES_USER`, `PERSES_PASSWORD`) and updates the code-server environment. |
| [18_test.yaml](18_test.yaml) | Checks the namespace, the running pod, the service, the HTTPRoute, the HTTPS endpoint and the service discovery ConfigMap. |
| [19_rollback.yaml](19_rollback.yaml) | Uninstalls the Helm release, deletes the `perses` namespace, and deletes the Keycloak client and the Perses realm roles. |

## Deployment

Perses is automatically deployed via the **thinkube-control Optional Components** interface at `https://thinkube.example.com/optional-components`.

The deployment process typically takes 5-7 minutes and includes:
1. Keycloak OIDC client configuration with role mappings
2. Perses Helm deployment with persistent storage
3. Native admin user creation
4. Project and datasource creation
5. Import of 25+ monitoring dashboards from thinkube-monitor repository
6. Service discovery registration with the Thinkube control plane

## Access Points

After deployment, Perses is accessible via:

- **Web Interface**: `https://perses.example.com`
- **Health Check**: `https://perses.example.com/api/health`
- **API Endpoint**: `https://perses.example.com/api/v1`

### Authentication

Perses supports two authentication methods:

**1. Keycloak SSO (Primary)**
- Click "Sign in with Keycloak SSO" on login page
- Redirects to Keycloak for authentication
- Users with `perses-admin` role have full access

**2. Native Authentication (Fallback)**
- Username: admin
- Password: Value of ADMIN_PASSWORD environment variable
- Used for API access and when Keycloak is unavailable

## Configuration

### Authentication Configuration

Perses authentication is configured via Helm values and environment variables:

```yaml
# values-thinkube.yaml
config:
  security:
    enable_auth: true
    cookie:
      same_site: lax
      secure: true
    authentication:
      providers:
        enable_native: true
    authorization:
      guest_permissions:
        - actions: ["*"]
          scopes: ["*"]

# OIDC via environment variables
envVars:
  - name: PERSES_SECURITY_AUTHENTICATION_PROVIDERS_OIDC_0_SLUG_ID
    value: "keycloak"
  - name: PERSES_SECURITY_AUTHENTICATION_PROVIDERS_OIDC_0_CLIENT_ID
    value: "perses"
  # ... additional OIDC configuration
```

### Persistence Configuration

Perses uses a 1Gi PersistentVolumeClaim for dashboard storage:

```yaml
persistence:
  enabled: true
  size: 1Gi
  accessModes:
    - ReadWriteOnce
```

### Resource Configuration

Default resource allocation:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### Dashboard Sidecar Configuration

Perses sidecar automatically loads dashboards from ConfigMaps:

```yaml
sidecar:
  enabled: true
  label: "perses.dev/resource"
  labelValue: "true"
  extraEnvVars:
    - name: SKIP_TLS_VERIFY
      value: "true"
```

## Usage

### Accessing Dashboards

1. **Navigate to Perses**: Open `https://perses.example.com`
2. **Sign In**: Use Keycloak SSO or native authentication
3. **Browse Projects**: Select from kubernetes, node-exporter, prometheus, alertmanager, applications, or gpu
4. **View Dashboards**: Click on any dashboard to visualize metrics

### Dashboard Organization

Dashboards are organized into 6 projects:

**Kubernetes Project (18 dashboards)**
- Cluster overview, namespace, node, pod monitoring
- Workload resources (deployments, statefulsets, daemonsets)
- Networking, persistent volumes
- Control plane: API server, controller manager, scheduler, kubelet, kube-proxy

**Node Exporter Project (2 dashboards)**
- Cluster USE method (Utilization, Saturation, Errors)
- Detailed node metrics

**Prometheus Project (2 dashboards)**
- Prometheus server overview
- Remote write monitoring

**AlertManager Project (1 dashboard)**
- AlertManager overview

**Applications Project (1 dashboard)**
- NGINX Ingress Controller metrics

**GPU Project (1 dashboard)**
- NVIDIA DCGM Exporter metrics

### Creating Custom Dashboards

**Via Web UI:**

```bash
1. Navigate to a project in Perses UI
2. Click "Create Dashboard"
3. Add panels with PromQL queries
4. Configure visualization (time series, gauge, table, etc.)
5. Save dashboard
```

**Via Dashboard-as-Code (YAML):**

```yaml
kind: Dashboard
apiVersion: perses.dev/v1alpha1
metadata:
  name: my-custom-dashboard
  namespace: perses
  labels:
    perses.dev/resource: "true"
    perses.dev/project: kubernetes
spec:
  display:
    name: "My Custom Dashboard"
  datasources:
    prometheus:
      kind: PrometheusDatasource
      name: prometheus-datasource
  panels:
    - kind: Panel
      spec:
        display:
          name: "CPU Usage"
        queries:
          - kind: TimeSeriesQuery
            spec:
              datasource:
                kind: PrometheusDatasource
                name: prometheus-datasource
              query: "rate(container_cpu_usage_seconds_total[5m])"
        plugin:
          kind: TimeSeriesChart
          spec:
            legend:
              position: bottom
```

Apply the dashboard:

```bash
kubectl apply -f my-custom-dashboard.yaml
```

The sidecar will automatically detect and load the dashboard.

### Using percli

**Login:**

```bash
percli login https://perses.example.com \
  --username admin \
  --password $ADMIN_PASSWORD
```

**List Projects:**

```bash
percli get projects
```

**List Dashboards:**

```bash
# All dashboards
percli get dashboards --all-projects

# Specific project
percli get dashboards --project kubernetes
```

**Export Dashboard:**

```bash
percli get dashboard my-dashboard --project kubernetes -o yaml > dashboard.yaml
```

**Import Dashboard:**

```bash
percli apply --file dashboard.yaml --project kubernetes
```

**Create Datasource:**

```bash
cat << EOF | percli apply --file -
kind: Datasource
metadata:
  name: tempo-datasource
  project: kubernetes
spec:
  default: false
  plugin:
    kind: TempoDatasource
    spec:
      proxy:
        kind: HTTPProxy
        spec:
          url: http://tempo.monitoring.svc.cluster.local:3100
EOF
```

### Querying Prometheus Metrics

Perses uses native PromQL for metric queries. Example queries:

**CPU Usage:**
```promql
rate(container_cpu_usage_seconds_total{namespace="default"}[5m])
```

**Memory Usage:**
```promql
container_memory_working_set_bytes{namespace="default"}
```

**Pod Count:**
```promql
count(kube_pod_info{namespace="default"})
```

**NGINX Request Rate:**
```promql
rate(nginx_ingress_controller_requests[5m])
```

**GPU Utilization:**
```promql
DCGM_FI_DEV_GPU_UTIL
```

## Integration

### Integration with Prometheus (#31)

Perses datasources are automatically configured to query Prometheus:

```yaml
kind: Datasource
metadata:
  name: prometheus-datasource
  project: kubernetes
spec:
  default: true
  plugin:
    kind: PrometheusDatasource
    spec:
      proxy:
        kind: HTTPProxy
        spec:
          url: http://prometheus-k8s.monitoring.svc.cluster.local:9090
```

### Integration with Keycloak (#6)

Perses integrates with Keycloak for SSO:

**Role Mapping:**
- Users with `perses-admin` role: Full access
- Users with `perses-user` role: Read-only access

**OIDC Configuration:**
- Issuer: `https://keycloak.example.com/realms/thinkube`
- Client ID: `perses`
- Scopes: openid, profile, email, roles

### Dashboard-as-Code with GitOps

Deploy dashboards via Kubernetes manifests:

```yaml
# Apply dashboard
kubectl apply -f dashboards/

# Label for auto-discovery
kubectl label dashboard my-dashboard perses.dev/resource=true -n perses
```

Integrate with ArgoCD or Flux for GitOps:

```yaml
# ArgoCD Application
apiVersion: argoprocd.io/v1alpha1
kind: Application
metadata:
  name: perses-dashboards
spec:
  source:
    repoURL: https://github.com/myorg/perses-dashboards
    path: dashboards
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: perses
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Extract the queries of a dashboard

```bash
# The PromQL queries of a Perses dashboard
percli get dashboard my-dashboard --project kubernetes -o json | \
  jq '.spec.panels[].spec.queries[].spec.query'
```

## Monitoring

### Health Checks

Perses provides a health endpoint:

```bash
# Check Perses health
curl https://perses.example.com/api/health

# Expected response
{"status":"ok"}
```

### Kubernetes Resources

Monitor Perses pod status:

```bash
# Check pod status
kubectl get pods -n perses

# View pod logs
kubectl logs -n perses -l app.kubernetes.io/name=perses --tail=100 -f

# Check resource usage
kubectl top pod -n perses

# Check PVC status
kubectl get pvc -n perses
```

### Dashboard Metrics

Monitor dashboard performance in Perses itself:

```promql
# Dashboard query count
increase(perses_dashboard_queries_total[5m])

# Query duration
perses_dashboard_query_duration_seconds
```

### Integration with Prometheus (#31)

Perses itself can be monitored by Prometheus using a ServiceMonitor:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: perses
  namespace: perses
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: perses
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

## Troubleshooting

### Connection Issues

**Problem**: Cannot access Perses UI

```bash
# Check pod status
kubectl get pods -n perses

# Check pod logs
kubectl logs -n perses -l app.kubernetes.io/name=perses

# Verify service
kubectl get svc -n perses

# Check the HTTPRoute
kubectl get httproute -n perses
kubectl describe httproute -n perses perses
```

### Authentication Issues

**Problem**: Cannot log in with Keycloak SSO

```bash
# Verify Keycloak client configuration
# (requires keycloak admin credentials)

# Check OIDC environment variables
kubectl get statefulset -n perses perses -o jsonpath='{.spec.template.spec.containers[0].env}' | jq

# Test native authentication fallback
curl -X POST https://perses.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"YOUR_PASSWORD"}'
```

**Problem**: "401 Unauthorized" when using percli

```bash
# Re-login with percli
percli login https://perses.example.com \
  --username admin \
  --password $ADMIN_PASSWORD

# Verify percli config
cat ~/.config/perses/config.yaml
```

### Dashboard Issues

**Problem**: Dashboards not appearing after import

```bash
# Check if sidecar is running
kubectl get pods -n perses -o jsonpath='{.items[*].spec.containers[*].name}'

# Verify dashboard ConfigMap labels
kubectl get configmaps -n perses -l perses.dev/resource=true

# Check sidecar logs
kubectl logs -n perses -l app.kubernetes.io/name=perses -c sidecar
```

**Problem**: "No data" in dashboard panels

```bash
# Verify Prometheus datasource
percli get datasources --project kubernetes

# Test Prometheus connectivity from Perses pod
kubectl exec -n perses statefulset/perses -- \
  wget -qO- http://prometheus-k8s.monitoring.svc.cluster.local:9090/api/v1/query?query=up

# Check Prometheus is running
kubectl get pods -n monitoring -l app.kubernetes.io/name=prometheus
```

### Storage Issues

**Problem**: Dashboards not persisting

```bash
# Check PVC status
kubectl get pvc -n perses

# Describe PVC for events
kubectl describe pvc -n perses perses

# Verify PVC is bound
kubectl get pvc -n perses perses -o jsonpath='{.status.phase}'
```

### Performance Issues

**Problem**: Slow dashboard loading

1. **Check resource usage**:
   ```bash
   kubectl top pod -n perses
   ```

2. **Increase resources** if needed: change `resources` in `values-thinkube.yaml`, then remove and reinstall Perses from the Optional Components page.

3. **Optimize PromQL queries**: Use recording rules in Prometheus for complex calculations

## Testing

### UI Access Test

```bash
# Test HTTPS access
curl -I https://perses.example.com

# Expected: HTTP 200 or 302 (redirect to login)
```

### API Authentication Test

```bash
# Get authentication token
TOKEN=$(curl -X POST https://perses.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"login\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}" \
  | jq -r '.access_token')

# Test authenticated API access
curl -H "Authorization: Bearer $TOKEN" \
  https://perses.example.com/api/v1/projects | jq
```

### Dashboard Query Test

```bash
# Test Prometheus datasource
percli login https://perses.example.com --username admin --password $ADMIN_PASSWORD

# List all dashboards
percli get dashboards --all-projects

# Expected: List of imported dashboards from thinkube-monitor
```

### Prometheus Connectivity Test

```bash
# Test Prometheus query from Perses pod
kubectl exec -n perses statefulset/perses -- \
  wget -qO- "http://prometheus-k8s.monitoring.svc.cluster.local:9090/api/v1/query?query=up" | jq

# Expected: JSON response with metric data
```

### Dashboard Import Test

```bash
# Create test dashboard
cat > /tmp/test-dashboard.yaml <<EOF
kind: Dashboard
apiVersion: perses.dev/v1alpha1
metadata:
  name: test-dashboard
  namespace: perses
  labels:
    perses.dev/resource: "true"
    perses.dev/project: kubernetes
spec:
  display:
    name: "Test Dashboard"
  datasources:
    prometheus:
      kind: PrometheusDatasource
      name: prometheus-datasource
  panels:
    - kind: Panel
      spec:
        display:
          name: "Cluster Pods"
        queries:
          - kind: TimeSeriesQuery
            spec:
              datasource:
                kind: PrometheusDatasource
                name: prometheus-datasource
              query: "sum(kube_pod_info)"
        plugin:
          kind: TimeSeriesChart
EOF

# Apply dashboard
kubectl apply -f /tmp/test-dashboard.yaml

# Wait for sidecar to detect (30 seconds)
sleep 30

# Verify dashboard appears in UI or via percli
percli get dashboard test-dashboard --project kubernetes
```

## Rollback

Remove Perses from the Optional Components page in thinkube-control. This
runs `19_rollback.yaml`, which uninstalls the Perses Helm release, deletes
the `perses` namespace with everything in it, and removes the Perses client
from Keycloak.

**Note**: Deleting the namespace deletes the data volume, which permanently removes all custom dashboards. Export important dashboards before proceeding.

To export all dashboards before rollback:

```bash
# Export all dashboards
mkdir -p /tmp/perses-backup
for project in kubernetes node-exporter prometheus alertmanager applications gpu; do
  percli get dashboards --project $project -o yaml > /tmp/perses-backup/$project-dashboards.yaml
done
```

## References

- [Perses Documentation](https://perses.dev/docs)
- [Perses GitHub Repository](https://github.com/perses/perses)
- [Perses Helm Chart](https://github.com/perses/helm-charts)
- [percli Documentation](https://perses.dev/docs/user-guides/cli)
- [thinkube-monitor Dashboards](https://github.com/thinkube/thinkube-monitor)
- [PromQL Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Perses CRD Specification](https://perses.dev/docs/api)
- [Dashboard-as-Code Guide](https://perses.dev/docs/user-guides/dashboard-as-code)

---

🤖 [AI-assisted]
