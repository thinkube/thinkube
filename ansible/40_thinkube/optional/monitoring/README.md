# Monitoring Stack (Prometheus + Grafana)

## Overview

This directory contains the deployment configuration for the Thinkube monitoring stack, consisting of:
- **Prometheus**: Time-series metrics collection and storage
- **Grafana**: Visualization and dashboarding with Keycloak SSO integration

Both components share the `monitoring` namespace and are designed to work together seamlessly.

## Architecture

### Prometheus
- **Type**: StatefulSet with persistent storage
- **Storage**: 20Gi persistent volume for metrics retention
- **Service**: ClusterIP on port 9090
- **Ingress**: HTTPS access at `prometheus.thinkube.com`
- **RBAC**: ServiceAccount with cluster-wide read access for metrics
- **Authentication**: None (as per reference implementation)

### Grafana
- **Type**: Deployment with persistent storage
- **Storage**: 5Gi persistent volume for dashboards and settings
- **Service**: ClusterIP on port 3000
- **Ingress**: HTTPS access at `grafana.thinkube.com`
- **Authentication**: Keycloak OAuth2 integration with role mapping
- **Datasource**: Prometheus pre-configured

## Features

### Prometheus Features
- Automatic service discovery for Kubernetes components
- Pre-configured scrape configs for:
  - Kubernetes API server
  - Kubernetes nodes
  - Kubernetes pods (with prometheus.io annotations)
  - Kubernetes service endpoints
- Web UI for querying and visualization
- API endpoints for programmatic access

### Grafana Features
- Keycloak SSO integration with role-based access:
  - `grafana-admin`: Full administrative access
  - `grafana-editor`: Edit dashboards and data sources
  - `grafana-viewer`: View-only access
- Pre-configured Prometheus datasource
- Persistent storage for dashboards
- Basic auth fallback for admin access

## Prerequisites

- MicroK8s cluster deployed
- Ingress controller configured
- TLS wildcard certificate in default namespace
- Harbor registry with Prometheus and Grafana images
- Keycloak deployed and accessible (for Grafana OAuth)

## Deployment

### 1. Deploy Prometheus

```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/10_deploy_prometheus.yaml
```

### 2. Configure Prometheus Metrics Collection

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/11_configure_prometheus_scraping.yaml
```

### 3. Configure Grafana Keycloak Integration

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/12_configure_grafana_keycloak.yaml
```

### 4. Deploy Grafana

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/13_deploy_grafana.yaml
```

### 5. Import Dashboards

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/14_import_grafana_dashboards.yaml
```

### Verify Deployment

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/18_test_monitoring.yaml
```

### Rollback (if needed)

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/monitoring/19_rollback_monitoring.yaml
```

## Configuration

### Variables (from inventory)

- `monitoring_namespace`: Shared namespace (default: `monitoring`)
- `prometheus_hostname`: Prometheus external hostname
- `prometheus_storage_size`: Prometheus storage size (default: `20Gi`)
- `prometheus_storage_class`: Storage class (default: `microk8s-hostpath`)
- `grafana_hostname`: Grafana external hostname
- `grafana_storage_size`: Grafana storage size (default: `5Gi`)
- `grafana_storage_class`: Storage class (default: `microk8s-hostpath`)
- `admin_username`: Admin username for all applications
- `keycloak_url`: Keycloak URL for OAuth integration
- `keycloak_realm`: Keycloak realm name

### Prometheus Scrape Configuration

To expose metrics from your application:

1. Add annotations to your pod/service:
   ```yaml
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8080"
     prometheus.io/path: "/metrics"
   ```

2. Prometheus will automatically discover and scrape the endpoint

### Grafana OAuth Configuration

The OAuth integration is automatically configured with:
- Client ID: `grafana`
- Redirect URI: `https://grafana.thinkube.com/login/generic_oauth`
- Role mapping based on Keycloak realm roles
- Automatic admin assignment for users with `grafana-admin` role

## Access

### Prometheus
- **URL**: `https://prometheus.thinkube.com`
- **Authentication**: None (consider adding for production)
- **API**: `https://prometheus.thinkube.com/api/v1/`

### Grafana
- **URL**: `https://grafana.thinkube.com`
- **Authentication Options**:
  1. **OAuth**: Click "Sign in with Keycloak-OAuth"
  2. **Basic Auth**: Username `{{ admin_username }}` with `ADMIN_PASSWORD`
- **Default Admin**: `{{ admin_username }}` has `grafana-admin` role

## Usage

### Prometheus Queries

Example queries in Prometheus:

```promql
# Check which targets are up
up

# Memory available on nodes
node_memory_MemAvailable_bytes

# CPU usage by container
rate(container_cpu_usage_seconds_total[5m])

# Pod memory usage
container_memory_usage_bytes{pod!=""}

# HTTP request rate (if exposed)
rate(http_requests_total[5m])
```

### Grafana Dashboards

1. **Import Dashboards**:
   - Go to Dashboards → Import
   - Use dashboard ID from Grafana.com or paste JSON
   - Popular IDs: 1860 (Node Exporter), 315 (Kubernetes)

2. **Create Custom Dashboards**:
   - Click "+" → Dashboard
   - Add panels with Prometheus queries
   - Save with meaningful names

3. **Manage Access**:
   - Users with `grafana-admin` role can manage all settings
   - Users with `grafana-editor` role can create/edit dashboards
   - Users with `grafana-viewer` role have read-only access

## Troubleshooting

### Prometheus Issues

```bash
# Check Prometheus pod
kubectl -n monitoring get pods -l app=prometheus
kubectl -n monitoring logs statefulset/prometheus

# Verify targets
curl https://prometheus.thinkube.com/api/v1/targets | jq .

# Check persistent volume
kubectl -n monitoring get pvc
```

### Grafana Issues

```bash
# Check Grafana pod
kubectl -n monitoring get pods -l app=grafana
kubectl -n monitoring logs deployment/grafana

# Test datasource connection
kubectl -n monitoring exec -it deployment/grafana -- curl http://prometheus:9090/api/v1/query?query=up

# Check OAuth secret
kubectl -n monitoring get secret grafana-oauth-secret -o yaml
```

### OAuth Login Issues

1. **Verify Keycloak client**:
   ```bash
   # Check if Grafana client exists in Keycloak
   curl -s https://auth.thinkube.com/admin/realms/thinkube/clients | jq '.[] | select(.clientId=="grafana")'
   ```

2. **Check user roles**:
   - Login to Keycloak admin console
   - Navigate to Users → View all users
   - Select user → Role mappings
   - Ensure `grafana-admin` role is assigned

3. **Debug OAuth flow**:
   - Check Grafana logs for OAuth errors
   - Verify redirect URI matches configuration
   - Ensure client secret in Kubernetes matches Keycloak

## Integration with Other Components

- **Applications**: Expose metrics on `/metrics` endpoint with proper annotations
- **AlertManager**: Can be configured to receive alerts from Prometheus
- **Additional Datasources**: Can be added to Grafana (Loki, Elasticsearch, etc.)

## Security Considerations

### Prometheus
- No authentication by default (following reference)
- Consider adding OAuth2 Proxy for production
- Restrict network access if not using authentication

### Grafana
- OAuth integration provides role-based access
- Basic auth available as fallback
- Secure cookie settings enabled
- Client credentials stored as Kubernetes secrets

## Migration Notes

This deployment was migrated from thinkube-core with the following changes:
- Updated to use inventory variables instead of hardcoded values
- Uses wildcard certificate from default namespace
- Targets `microk8s_control_plane` host group
- Uses Harbor registry for images
- Keycloak integration uses standard `admin_username` variable

🤖 [AI-assisted]