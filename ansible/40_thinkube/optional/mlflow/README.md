# MLflow Component

MLflow is an open-source platform for managing the ML lifecycle, including experimentation, reproducibility, deployment, and a central model registry. This deployment provides a fully-featured MLflow tracking server with PostgreSQL backend, SeaweedFS S3-compatible artifact storage (Apache 2.0 licensed), and Keycloak OIDC authentication.

## Overview

- **Component Type**: Optional
- **Namespace**: `mlflow`
- **Default Access**: https://mlflow.{{ domain_name }}
- **Authentication**: Built-in OIDC with Keycloak (single sign-on)

## Deployment Structure

```
00_install.yaml              # Orchestrator playbook
10_configure_keycloak.yaml   # Create Keycloak client for MLflow
11_deploy.yaml               # Deploy MLflow with OIDC authentication
17_configure_discovery.yaml  # Register service in thinkube-control
18_test.yaml                 # Validate deployment and configuration
19_rollback.yaml             # Remove MLflow and cleanup resources
```

## Requirements

- MicroK8s cluster with ingress controller
- Cert-manager with wildcard certificate
- PostgreSQL database (core component)
- SeaweedFS object storage (core component, Apache 2.0 licensed)
- Keycloak instance running and accessible
- Custom MLflow image built and available in Harbor registry
- ADMIN_PASSWORD environment variable set
- MLFLOW_DB_PASSWORD environment variable (optional, auto-generated if not set)

## Image Requirements

MLflow requires a custom Docker image with OIDC support and additional dependencies. The image should be built separately in the custom-images module and pushed to Harbor registry before deployment.

Expected image location:
```
{{ harbor_registry }}/{{ harbor_project }}/mlflow-custom:latest
```

## Deployment

Deploy MLflow with OIDC authentication:

```bash
cd ~/thinkube
# Set required passwords
export ADMIN_PASSWORD='your-admin-password'
export MLFLOW_DB_PASSWORD='your-mlflow-db-password'  # Optional

# Run orchestrator (recommended)
./scripts/run_ansible.sh ansible/40_thinkube/optional/mlflow/00_install.yaml

# Or run individually:
# Step 1: Create Keycloak client
./scripts/run_ansible.sh ansible/40_thinkube/optional/mlflow/10_configure_keycloak.yaml

# Step 2: Deploy MLflow
./scripts/run_ansible.sh ansible/40_thinkube/optional/mlflow/11_deploy.yaml

# Step 3: Configure service discovery
./scripts/run_ansible.sh ansible/40_thinkube/optional/mlflow/17_configure_discovery.yaml
```

## Database Configuration

MLflow automatically creates:
- PostgreSQL database: `mlflow`
- Database user: `mlflow`
- All necessary schemas and permissions

The database is created in the existing PostgreSQL instance deployed as a core component.

## Storage Configuration

MLflow artifact storage:
- **Backend**: SeaweedFS (Apache 2.0 licensed S3-compatible storage)
- **Bucket**: `mlflow`
- **Endpoint**: Internal cluster endpoint for performance
- **Location**: Automatically created during deployment
- **Local artifacts**: PersistentVolume for temporary storage

## Authentication

MLflow uses built-in OIDC authentication with Keycloak:

### Roles
- **mlflow-admin**: Full administrative access
- **mlflow-user**: Standard user access

### User Management
- Admin user (from inventory `admin_username`) automatically assigned mlflow-admin role
- Additional users can be assigned roles in Keycloak
- Automatic user group detection from Keycloak realm roles

### OIDC Configuration
- **Client ID**: `mlflow`
- **Provider**: Keycloak
- **Scopes**: openid, profile, email
- **Custom plugin**: Keycloak group detection for role mapping

## Testing

Validate the deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/mlflow/18_test.yaml
```

Tests verify:
- Namespace and resources exist
- Pods are running
- Services and ingress configured
- TLS certificate present
- Database secrets configured
- Storage secrets configured
- OIDC secrets present
- Service discovery registered
- HTTP connectivity working

## Configuration Variables

Required inventory variables:
- `domain_name`: Base domain for the cluster
- `mlflow_hostname`: Hostname for MLflow access (e.g., mlflow.{{ domain_name }})
- `admin_username`: Admin username for role assignments
- `kubeconfig`: Path to kubeconfig file
- `postgres_hostname`: PostgreSQL server hostname
- `seaweedfs_s3_hostname`: SeaweedFS S3 API hostname
- `keycloak_url`: Keycloak server URL
- `keycloak_realm`: Keycloak realm name
- `harbor_registry`: Harbor registry domain
- `harbor_project`: Harbor project name
- `primary_ingress_class`: Ingress class to use

Environment variables:
- `ADMIN_PASSWORD`: Admin password (required)
- `MLFLOW_DB_PASSWORD`: Database password (optional)

## Features

### Experiment Tracking
- Log parameters, metrics, and tags
- Compare experiment runs
- Search and filter experiments
- Visualize metrics and parameters

### Model Registry
- Register models from experiments
- Version control for models
- Stage transitions (Staging, Production, Archived)
- Model lineage tracking

### Artifact Storage
- Store models, datasets, and files
- S3-compatible SeaweedFS backend (Apache 2.0 licensed)
- Automatic artifact logging
- Download artifacts via CLI or UI

### Authentication & Authorization
- Single sign-on with Keycloak
- Role-based access control
- Admin and user groups
- Session management

### Integration
- Python client library
- REST API
- R client library
- Java client library

## Usage Example

After deployment, you can use MLflow from your Python code:

```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("https://mlflow.{{ domain_name }}")

# Create experiment
mlflow.create_experiment("my-experiment")
mlflow.set_experiment("my-experiment")

# Start a run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("learning_rate", 0.01)

    # Log metrics
    mlflow.log_metric("accuracy", 0.95)

    # Log model
    mlflow.sklearn.log_model(model, "model")
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n mlflow
kubectl logs -n mlflow -l app=mlflow
```

### Verify Ingress
```bash
kubectl get ingress -n mlflow
kubectl describe ingress mlflow -n mlflow
```

### Database Connection Issues
```bash
# Check database secret
kubectl get secret mlflow-db-secret -n mlflow -o yaml

# Test database connection
kubectl run -it --rm psql --image=postgres:15 --restart=Never -- \
  psql -h {{ postgres_hostname }} -U mlflow -d mlflow
```

### Storage Issues
```bash
# Check SeaweedFS S3 secret
kubectl get secret mlflow-s3-secret -n mlflow -o yaml

# Test SeaweedFS connectivity
s3cmd --config=/dev/null \
  --access_key="<access-key>" \
  --secret_key="<secret-key>" \
  --host="https://{{ seaweedfs_s3_hostname }}" \
  --no-ssl-certificate-check \
  --signature-v2 \
  ls s3://mlflow/
```

### OIDC Issues
- Verify Keycloak is accessible
- Check client configuration in Keycloak
- Review pod logs for authentication errors
- Ensure redirect URIs are correct in Keycloak client
- Verify role mappings are configured

## Rollback

Remove MLflow deployment:

```bash
./scripts/run_ansible.sh ansible/40_thinkube/optional/mlflow/19_rollback.yaml
```

This will:
- Delete all MLflow resources
- Remove the namespace
- Drop the database and user
- Remove SeaweedFS S3 bucket
- Clean up all secrets and ConfigMaps
- Preserve Keycloak client configuration
- Preserve custom images in Harbor

## Notes

- Database credentials are stored in Kubernetes secrets
- Artifact storage uses SeaweedFS with S3-compatible protocol (Apache 2.0 licensed)
- Custom image is required for OIDC support
- Built-in OIDC replaces OAuth2 Proxy approach
- All communication uses TLS encryption
- Service is automatically registered in thinkube-control dashboard
- Consider persistent volumes for production use
- Database is backed up with PostgreSQL backup procedures
- **License compliance**: SeaweedFS is Apache 2.0 licensed, ensuring compatibility with Thinkube's Apache license and public cloud integrations

## Dependencies

This component depends on:
- **PostgreSQL** (CORE-XXX): Database backend
- **SeaweedFS** (CORE-XXX): S3-compatible artifact storage (Apache 2.0 licensed)
- **Keycloak** (CORE-XXX): Authentication provider

## License

See project LICENSE file for details.

## Contributing

When modifying this component:
1. Follow the standardized playbook structure
2. Update tests in 18_test.yaml
3. Update this README with any configuration changes
4. Test deployment and rollback procedures
5. Update service discovery if endpoints change