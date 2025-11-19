# Perses Observability Platform

Component #40 in the Thinkube Platform stack.

## Overview

Perses is a modern, open-source observability visualization platform designed as a cloud-native alternative to Grafana. It provides native support for Prometheus metrics (PromQL), Tempo distributed tracing, Loki log aggregation, and Pyroscope continuous profiling. Perses features Dashboard-as-Code capabilities using Kubernetes CRDs, making dashboards versionable and deployable alongside applications.

This component deploys Perses with Keycloak SSO authentication, persistent storage for dashboards, and automatically imports a curated collection of 25+ monitoring dashboards for Kubernetes, node metrics, Prometheus, AlertManager, NGINX Ingress, and GPU monitoring.

## Dependencies

This component depends on the following Thinkube components:

- **Kubernetes (#6)** - Provides the container orchestration platform
- **ACME Certificates (#12)** - Secures HTTPS connections
- **Ingress (#13)** - Routes external traffic to Perses web interface
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
kubectl_bin: "/snap/bin/kubectl"
helm_bin: "/snap/bin/helm"

# Namespace
perses_namespace: "perses"
prometheus_namespace: "monitoring"

# Keycloak configuration
keycloak_url: "https://keycloak.example.com"
keycloak_realm: "thinkube"
admin_username: "admin"

# Ingress
primary_ingress_class: "nginx"

# Environment variables
ADMIN_PASSWORD: "your-admin-password"  # Required for deployment
```

## Playbooks

### **00_install.yaml** - Main Orchestrator

Coordinates the complete Perses deployment by executing all component playbooks in the correct sequence.

**Tasks:**
1. Imports `10_configure_keycloak.yaml` to create OIDC client
2. Imports `11_deploy.yaml` to deploy Perses with Helm
3. Imports `14_import_dashboards_percli.yaml` to import monitoring dashboards
4. Imports `17_configure_discovery.yaml` to register service endpoints

### **10_configure_keycloak.yaml** - Keycloak OIDC Configuration

Configures Keycloak authentication for Perses with role-based access control.

**Configuration Steps:**

**Step 1: Create Perses Realm Roles**
- Creates `perses-admin` role for full administrative access
- Creates `perses-user` role for standard user access
- Uses `keycloak/keycloak_bulk_roles` role for role creation

**Step 2: Setup Keycloak OIDC Client**
- Creates OIDC client with client ID `perses`
- Configures redirect URIs: `https://perses.example.com/api/auth/providers/oidc/keycloak/callback`
- Enables standard OpenID Connect flow
- Disables implicit flow for security
- Enables direct access grants for API authentication
- Configures as confidential client (not public)
- Sets access token lifespan to 3600 seconds
- Includes default scopes: email, profile, roles, openid, offline_access
- Configures web origins with wildcard support

**Step 3: Configure Protocol Mappers**
- **perses-realm-role-mapper**: Maps realm roles to `realm_access.roles` claim
- **perses-audience-mapper**: Adds `perses` audience to access tokens
- **perses-client-role-mapper**: Maps client roles to `resource_access.perses.roles` claim
- All mappers include claims in ID token, access token, and userinfo endpoint
- Enables multivalued role arrays in JWT

**Step 4: Assign Admin Role**
- Assigns `perses-admin` role to the admin user specified in inventory
- Grants full administrative access to Perses dashboards and configuration

### **11_deploy.yaml** - Perses Helm Deployment

Deploys Perses observability platform using the official Helm chart with Thinkube-specific configuration.

**Configuration Steps:**

**Step 1: Namespace and TLS Setup**
- Creates `perses` namespace for component isolation
- Retrieves wildcard TLS certificate from `default` namespace
- Copies certificate to `perses` namespace as `perses-tls-secret`

**Step 2: Retrieve Keycloak Client Secret**
- Obtains Keycloak admin token from master realm
- Queries Keycloak API for Perses client UUID
- Retrieves client secret for OIDC authentication
- Stores secret as Ansible fact for template processing

**Step 3: Process Helm Values Template**
- Creates temporary directory for Helm values
- Templates `values-thinkube.yaml` with configuration:
  - **Authentication**: Enables both native and OIDC authentication
  - **OIDC Provider**: Keycloak with slug_id "keycloak"
  - **Security**: Guest permissions set to full admin (allows initial setup)
  - **Frontend**: Explorer mode enabled
  - **Ingress**: NGINX ingress with SSL redirect
  - **Resources**: 100m CPU / 128Mi memory requests, 500m CPU / 512Mi limits
  - **Persistence**: 1Gi PVC for dashboard storage
  - **Sidecar**: Enabled to load dashboards from ConfigMaps with label `perses.dev/resource: true`
  - **Environment Variables**: OIDC configuration via `PERSES_*` variables

**Step 4: Deploy Perses with Helm**
- Adds Perses Helm repository: `https://perses.github.io/helm-charts`
- Updates Helm repositories
- Deploys Perses chart version 0.17.1 (app version 0.52.0)
- Waits for deployment completion (10 minute timeout)
- Monitors pod readiness

**Step 5: Create Native Admin User**
- Creates native Perses user with admin username
- Uses ADMIN_PASSWORD from environment for authentication
- Enables fallback authentication when Keycloak is unavailable
- Returns HTTP 200/201 on success, 409 if user exists

**Step 6: Deployment Verification**
- Waits for Perses pod to reach Running state
- Verifies container readiness
- Displays deployment summary with URL and authentication details
- Lists supported datasources: Prometheus, Tempo, Loki, Pyroscope

### **14_import_dashboards_percli.yaml** - Dashboard Import

Imports a curated collection of monitoring dashboards from the thinkube-monitor repository using percli.

**Import Process:**

**Step 1: Preparation**
- Retrieves ADMIN_PASSWORD from environment
- Cleans and creates work directory at `/tmp/perses-dashboards`

**Step 2: Clone thinkube-monitor Repository**
- Clones https://github.com/thinkube/thinkube-monitor
- Uses main branch for latest dashboards
- Depth 1 for faster clone
- Verifies cloned commit hash

**Step 3: percli Authentication**
- Logs in to Perses using native authentication
- Username: admin (from inventory)
- Password: ADMIN_PASSWORD from environment

**Step 4: Create Perses Projects**
- Creates 6 projects for dashboard organization:
  - **kubernetes**: Kubernetes cluster monitoring (18 dashboards)
  - **node-exporter**: System metrics (2 dashboards)
  - **prometheus**: Prometheus server monitoring (2 dashboards)
  - **alertmanager**: Alert management (1 dashboard)
  - **applications**: Application monitoring - NGINX Ingress (1 dashboard)
  - **gpu**: GPU monitoring - NVIDIA DCGM (1 dashboard)

**Step 5: Create Prometheus Datasources**
- Creates Prometheus datasource for each project
- URL: `http://prometheus-k8s.monitoring.svc.cluster.local:9090`
- Configures allowed endpoints for PromQL queries:
  - `/api/v1/labels` (POST)
  - `/api/v1/series` (POST)
  - `/api/v1/metadata` (GET)
  - `/api/v1/query` (POST)
  - `/api/v1/query_range` (POST)
  - `/api/v1/label/{label}/values` (GET)
- Sets as default datasource for each project

**Step 6: Import thinkube-monitor Dashboards**
- Imports dashboards by category using percli
- Dashboard modifications:
  - Adapted for single-cluster deployments (no cluster variable)
  - Simplified PromQL queries (no cluster filters)
  - Custom NGINX dashboard with essential metrics
  - Migrated NVIDIA DCGM dashboard to Perses format
- Total dashboard count: 25+ monitoring dashboards

**Step 7: Import Summary**
- Lists all imported dashboards by project
- Displays comprehensive summary with dashboard categories
- Provides access URL for Perses UI

### **17_configure_discovery.yaml** - Service Discovery Configuration

Registers Perses endpoints and metadata with the Thinkube service discovery system for integration with the control plane.

**Tasks:**
1. Reads component version from `VERSION` file (0.1.0)
2. Creates `thinkube-service-config` ConfigMap with:
   - Service metadata: name, display name, description, type (optional), category (observability)
   - Component version: 0.1.0
   - Icon: `/icons/tk_monitoring.svg`
   - Endpoint: Web interface at `https://perses.example.com` with health check at `/api/health`
   - Dependencies: prometheus, keycloak
   - Scaling configuration: Deployment `perses` in `perses` namespace, min 1 replica, can be disabled
   - Features: PromQL native support, Tempo tracing, Loki logs, Dashboard-as-Code (CRD), Keycloak SSO
3. Updates code-server environment variables via `code_server_env_update` role
4. Displays service registration summary

## Deployment

Perses is automatically deployed via the **thinkube-control Optional Components** interface at `https://thinkube.example.com/optional-components`.

To deploy manually:

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/perses/00_install.yaml
```

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

### Export to Grafana

While Perses is independent, you can export metrics queries to Grafana if needed:

```bash
# Extract PromQL queries from Perses dashboard
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

# Check ingress
kubectl get ingress -n perses
kubectl describe ingress -n perses perses
```

### Authentication Issues

**Problem**: Cannot log in with Keycloak SSO

```bash
# Verify Keycloak client configuration
# (requires keycloak admin credentials)

# Check OIDC environment variables
kubectl get deployment -n perses perses -o jsonpath='{.spec.template.spec.containers[0].env}' | jq

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
kubectl exec -n perses deployment/perses -- \
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

2. **Increase resources** if needed:
   ```bash
   # Edit values and re-deploy
   cat > /tmp/perses-values.yaml <<EOF
   resources:
     requests:
       cpu: 200m
       memory: 256Mi
     limits:
       cpu: 1000m
       memory: 1Gi
   EOF

   helm upgrade perses perses/perses -n perses -f /tmp/perses-values.yaml
   ```

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
kubectl exec -n perses deployment/perses -- \
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

To rollback or remove the Perses deployment:

```bash
# Uninstall Perses Helm release
helm uninstall perses -n perses

# Delete Keycloak client
# (requires manual deletion via Keycloak admin UI or API)

# Delete ConfigMaps and Secrets
kubectl delete configmap -n perses thinkube-service-config
kubectl delete secret -n perses perses-tls-secret

# Optional: Delete persistent data (WARNING: This deletes all dashboards)
kubectl delete pvc -n perses perses

# Optional: Delete namespace
kubectl delete namespace perses
```

**Note**: Deleting the PVC will permanently remove all custom dashboards. Export important dashboards before proceeding.

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
