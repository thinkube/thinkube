# OpenSearch Deployment

This directory contains Ansible playbooks for deploying OpenSearch and OpenSearch Dashboards with Keycloak OIDC integration on MicroK8s.

## Overview

OpenSearch is an open-source search and analytics engine used for log aggregation, full-text search, and data analysis. This deployment includes:

- OpenSearch cluster (single node configuration)
- OpenSearch Dashboards for visualization
- Keycloak OIDC integration for single sign-on
- TLS encryption for all communications
- Persistent storage for data retention

## Prerequisites

- MicroK8s cluster deployed and running
- Keycloak deployed (CORE-003)
- TLS certificates available
- Helm installed on control plane
- Environment variables set:
  - `ADMIN_PASSWORD`: Admin password for OpenSearch and all other applications (including Keycloak)

## Components

### Playbooks

1. **10_deploy.yaml** - Main deployment playbook
   - Configures Keycloak client and roles
   - Deploys OpenSearch via Helm
   - Deploys OpenSearch Dashboards
   - Configures ingress for external access

2. **16_deploy_fluent_bit.yaml** - Continuous log collection
   - Deploys Fluent Bit as a DaemonSet
   - Continuously collects logs from all containers
   - Ships logs to OpenSearch in real-time
   - Provides ongoing log aggregation

4. **18_test.yaml** - Test playbook
   - Verifies pods are running
   - Tests authentication
   - Checks Keycloak integration
   - Validates external connectivity

5. **19_rollback.yaml** - Rollback playbook
   - Removes all OpenSearch resources
   - Cleans up Keycloak configuration
   - Deletes persistent volumes
   - Removes Fluent Bit if deployed

### Configuration Details

- **Namespace**: `opensearch`
- **Storage**: 30Gi for OpenSearch data
- **Resources**:
  - OpenSearch: 1-2 CPU, 2-4Gi memory
  - Dashboards: Default Helm chart resources
- **Authentication**:
  - Basic auth: admin user with configurable password
  - OIDC: Integration with Keycloak realm

### URLs

After deployment, services are available at:
- OpenSearch API: `https://opensearch.<domain_name>`
- OpenSearch Dashboards: `https://osd.<domain_name>`

## Usage

### Deploy OpenSearch

```bash
cd ~/thinkube

# Set required password
export ADMIN_PASSWORD='your-secure-password'

# Deploy OpenSearch
./scripts/run_ansible.sh ansible/40_thinkube/optional/opensearch/10_deploy.yaml

# Deploy continuous log collection (recommended)
./scripts/run_ansible.sh ansible/40_thinkube/optional/opensearch/16_deploy_fluent_bit.yaml
```

### Test Deployment

```bash
# Run tests
./scripts/run_ansible.sh ansible/40_thinkube/optional/opensearch/18_test.yaml
```

### Rollback Deployment

```bash
# Remove OpenSearch
./scripts/run_ansible.sh ansible/40_thinkube/optional/opensearch/19_rollback.yaml
```

## Security Configuration

The deployment includes comprehensive security configuration:

1. **TLS Encryption**:
   - HTTPS for all API endpoints
   - TLS for inter-node communication
   - Certificate validation

2. **Authentication**:
   - Internal users with bcrypt-hashed passwords
   - OIDC integration with Keycloak
   - Role-based access control

3. **Keycloak Integration**:
   - Client ID: `opensearch`
   - Scope: `opensearch-authorization`
   - Roles: `opensearch_admin`, `opensearch_editor`, `opensearch_viewer`

## Accessing OpenSearch

### Using Basic Authentication

```bash
# API access
curl -u admin:$ADMIN_PASSWORD https://opensearch.<domain_name>/_cluster/health

# Dashboard access
# Navigate to https://osd.<domain_name>
# Login with admin / $ADMIN_PASSWORD
```

### Using Keycloak SSO

1. Navigate to `https://osd.<domain_name>`
2. Click on "Login via Keycloak" (if configured)
3. Login with your Keycloak credentials

## Troubleshooting

### Common Issues

1. **Pods not starting**:
   ```bash
   kubectl describe pod -n opensearch <pod-name>
   kubectl logs -n opensearch <pod-name>
   ```

2. **Authentication failures**:
   - Verify password is set correctly
   - Check security configuration was applied
   - Review OpenSearch logs

3. **Keycloak integration issues**:
   - Verify client secret is correct
   - Check redirect URIs match
   - Ensure scope mappers are configured

### Debug Commands

```bash
# Check pod status
./scripts/run_ssh_command.sh vm-2 "microk8s.kubectl get pods -n opensearch"

# View OpenSearch logs
./scripts/run_ssh_command.sh vm-2 "microk8s.kubectl logs -n opensearch deploy/opensearch-cluster-master"

# Test internal connectivity
./scripts/run_ssh_command.sh vm-2 "microk8s.kubectl exec -n opensearch opensearch-cluster-master-0 -- curl -ks https://localhost:9200"
```

## Data Persistence

OpenSearch data is stored in persistent volumes:
- PVC: `opensearch-cluster-master-opensearch-cluster-master-0`
- Size: 30Gi
- Access Mode: ReadWriteOnce

Data persists across pod restarts but is deleted during rollback.

## Dependencies

- MicroK8s cluster
- Keycloak (for OIDC)
- Ingress controller
- Cert-manager (for TLS)
- Persistent storage provisioner

## Notes

- Single node deployment suitable for development/small deployments
- For production, consider multi-node configuration
- Resource limits can be adjusted in Helm values
- PKCE is explicitly disabled for Keycloak compatibility

## What's Next

After deploying OpenSearch, you can leverage it for various use cases in your Thinkube environment:

### 1. **Set Up Log Aggregation**
Configure your applications to send logs to OpenSearch:
```bash
# Example: Configure a Python app to send logs
pip install python-elasticsearch
```

### 2. **Enable Vector Search**
Install and configure the k-NN plugin for semantic search:
```bash
# Check if k-NN plugin is installed
curl -u admin:$ADMIN_PASSWORD https://opensearch.<domain_name>/_cat/plugins?v
```

### 3. **Create Index Templates**
Set up index patterns for different data types:
```bash
# Create an index template for application logs
curl -u admin:$ADMIN_PASSWORD -X PUT https://opensearch.<domain_name>/_index_template/app-logs \
  -H 'Content-Type: application/json' \
  -d '{"index_patterns": ["app-logs-*"], "template": {"settings": {"number_of_shards": 1}}}'
```

### 4. **Configure Data Streams**
Set up data streams for time-series data:
- Application metrics
- AI model performance data
- System monitoring data

### 5. **Build Dashboards**
Create visualizations in OpenSearch Dashboards:
- Log analysis dashboards
- Performance monitoring
- AI metrics tracking
- Cost analysis reports

### 6. **Integrate with Other Services**
- **Argo Workflows**: Index workflow execution logs
- **Harbor**: Track container image usage
- **Gitea**: Analyze code repository activity
- **SeaweedFS**: Index object storage metadata

### 7. **Implement Security Policies**
- Set up fine-grained access control
- Configure audit logging
- Enable field-level security
- Set up document-level security

### 8. **Explore AI/ML Features**
- Set up anomaly detection
- Configure ML commons
- Implement semantic search
- Build recommendation systems

### 9. **Connect Applications**
Example integrations:
```python
# Python client example
from elasticsearch import Elasticsearch

es = Elasticsearch(
    ['https://opensearch.thinkube.com'],
    http_auth=('admin', 'your-password'),
    verify_certs=True
)
```

### 10. **Monitor and Optimize**
- Set up index lifecycle management
- Configure snapshot policies
- Monitor cluster health
- Optimize query performance

For detailed guides on these topics, refer to the [OpenSearch documentation](https://opensearch.org/docs/latest/).