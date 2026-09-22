# MLflow Component

MLflow is an open-source platform for managing the ML lifecycle, including experimentation, reproducibility, deployment, and a central model registry. This deployment provides a fully-featured MLflow tracking server with PostgreSQL backend, SeaweedFS S3-compatible artifact storage (Apache 2.0 licensed), and Keycloak OIDC authentication.

## Installation

MLflow is a core component. The Thinkube installer installs it by running
`00_install.yaml`, which runs `10_configure_keycloak.yaml`, `11_deploy.yaml`
and `17_configure_discovery.yaml` in that order. It is not installed on its own.

## Overview

- **Component Type**: Core
- **Namespace**: `mlflow`
- **Default Access**: https://experiments.{{ domain_name }}
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

- Kubernetes (kubeadm) cluster with the Gateway API gateway
- Wildcard certificate (`infrastructure/acme-certificates`)
- PostgreSQL database (core component)
- SeaweedFS object storage (core component, Apache 2.0 licensed)
- JuiceFS with the MLflow volume and S3 gateway (`juicefs/11_create_mlflow_volume.yaml`, `juicefs/12_deploy_mlflow_gateway.yaml`)
- Keycloak instance running and accessible
- Harbor registry configured (core component)
- Custom MLflow image built and available in Harbor registry
- ADMIN_PASSWORD environment variable set
- HARBOR_ROBOT_TOKEN in ~/.env (created during Harbor setup)

## Image Requirements

MLflow requires a custom Docker image with OIDC support and additional dependencies. The image is built by `harbor-images/14_build_base_images.yaml` and pushed to Harbor registry before deployment.

Expected image location:
```
{{ harbor_registry }}/library/mlflow-custom:latest
```

## Deployment

Deploy MLflow with OIDC authentication:

```bash
cd ~/thinkube
# Set required passwords
export ADMIN_PASSWORD='your-admin-password'

# Run orchestrator (recommended)
./scripts/run_ansible.sh ansible/40_thinkube/core/mlflow/00_install.yaml

# Or run individually:
# Step 1: Create Keycloak client
./scripts/run_ansible.sh ansible/40_thinkube/core/mlflow/10_configure_keycloak.yaml

# Step 2: Deploy MLflow
./scripts/run_ansible.sh ansible/40_thinkube/core/mlflow/11_deploy.yaml

# Step 3: Configure service discovery
./scripts/run_ansible.sh ansible/40_thinkube/core/mlflow/17_configure_discovery.yaml
```

## Database Configuration

MLflow automatically creates:
- PostgreSQL database: `mlflow`
- Database access as the admin user (`admin_username`), with `ADMIN_PASSWORD` as the password
- All necessary schemas and permissions

The database is created in the existing PostgreSQL instance deployed as a core component.

## Storage Configuration

MLflow artifact storage:
- **Endpoint**: The JuiceFS S3 gateway, `http://juicefs-mlflow-gateway.juicefs.svc.cluster.local:9001` (`MLFLOW_S3_ENDPOINT_URL`)
- **Backend**: The JuiceFS `mlflow` volume, whose data lives in the SeaweedFS (Apache 2.0 licensed) bucket `mlflow`
- **Why**: MLflow writes through S3; inference workloads and JupyterHub read the same files through a POSIX mount, without a second copy
- **Location**: The bucket is created during deployment
- **Local artifacts**: PVC `mlflow-storage` for temporary storage

## Authentication

MLflow uses built-in OIDC authentication with Keycloak:

### Roles
- **mlflow-admin**: Full administrative access
- **mlflow-user**: Standard user access

### User Management
- SSO user (from inventory `auth_realm_username`) automatically assigned mlflow-admin role
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
./scripts/run_ansible.sh ansible/40_thinkube/core/mlflow/18_test.yaml
```

Tests verify:
- Namespace and resources exist
- Pods are running
- Services and HTTPRoute configured
- TLS certificate present
- Database secrets configured
- Storage secrets configured
- OIDC secrets present
- Service discovery registered
- HTTP connectivity working

## Configuration Variables

Required inventory variables:
- `domain_name`: Base domain for the cluster
- `mlflow_hostname`: Hostname for MLflow access; `11_deploy.yaml` sets it to `experiments.{{ domain_name }}`
- `admin_username`: Keycloak admin username (for API access)
- `auth_realm_username`: SSO user for role assignments (typically 'thinkube')
- `kubeconfig`: Path to kubeconfig file
- `postgres_hostname`: PostgreSQL server hostname
- `object_storage_s3_hostname`: SeaweedFS S3 API hostname
- `keycloak_url`: Keycloak server URL
- `keycloak_realm`: Keycloak realm name
- `harbor_registry`: Harbor registry domain
- `harbor_project`: Harbor project name
- `gateway_name`, `gateway_namespace`: Gateway the HTTPRoute attaches to

Environment variables:
- `ADMIN_PASSWORD`: Admin password (required)
- `HARBOR_ROBOT_TOKEN`: Harbor robot account token (required, stored in ~/.env)

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
- S3 API through the JuiceFS gateway, data in SeaweedFS (Apache 2.0 licensed)
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
mlflow.set_tracking_uri("https://experiments.{{ domain_name }}")

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

### Verify Route
```bash
kubectl get httproute -n mlflow
kubectl describe httproute mlflow -n mlflow
```

### Database Connection Issues
```bash
# Check database secret
kubectl get secret mlflow-db-secret -n mlflow -o yaml

# Test database connection
kubectl run -it --rm psql --image=postgres:15 --restart=Never -- \
  psql -h {{ postgres_hostname }} -U {{ admin_username }} -d mlflow
```

### Storage Issues
```bash
# Check SeaweedFS S3 secret
kubectl get secret mlflow-s3-secret -n mlflow -o yaml

# Test SeaweedFS connectivity
s3cmd --config=/dev/null \
  --access_key="<access-key>" \
  --secret_key="<secret-key>" \
  --host="https://{{ object_storage_s3_hostname }}" \
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
./scripts/run_ansible.sh ansible/40_thinkube/core/mlflow/19_rollback.yaml
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
- Artifact storage uses the JuiceFS S3 gateway over SeaweedFS (Apache 2.0 licensed)
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