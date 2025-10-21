# PostgreSQL Database

This component deploys a PostgreSQL database server in Kubernetes, providing a centralized data store for platform services including Keycloak, Harbor, MLflow, and other components.

## Features

- Uses official PostgreSQL container image (14.5-alpine)
- Persistent storage via StatefulSet
- TLS secured connections
- TCP passthrough enabled with Ingress controller
- Database persistence across pod restarts
- Configurable resource limits
- Comprehensive tests for functionality verification
- Clean rollback procedure

## Deployment

```bash
# Deploy PostgreSQL
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/postgresql/10_deploy.yaml

# Test the deployment
./scripts/run_ansible.sh ansible/40_thinkube/core/postgresql/18_test.yaml

# Rollback if needed
./scripts/run_ansible.sh ansible/40_thinkube/core/postgresql/19_rollback.yaml
```

## Configuration

PostgreSQL is configured via inventory variables:

- `postgres_hostname`: DNS name for PostgreSQL access
- `admin_username`: Admin user for PostgreSQL (follows standard variable naming)
- `admin_password`: Admin password for PostgreSQL access

## Accessing PostgreSQL

### From within the cluster

Applications can access PostgreSQL using the service name:

```
Host: postgresql-official.postgres
Port: 5432
User: {{ admin_username }}
Password: {{ admin_password }}
Database: mydatabase
```

### From outside the cluster

External access is available via the ingress TCP passthrough:

```
Host: {{ postgres_hostname }}
Port: 5432
User: {{ admin_username }}
Password: {{ admin_password }}
Database: mydatabase
```

### Sample connection command

```bash
PGPASSWORD='{{ admin_password }}' psql -h {{ postgres_hostname }} -p 5432 -U {{ admin_username }} -d mydatabase
```

## Data Persistence

Data is stored in a persistent volume claim named `postgres-data` in the `postgres` namespace. This ensures data survives pod restarts and redeployments.

For complete data protection, consider implementing a backup strategy using:

1. pg_dump for logical backups
2. Container volume snapshots for physical backups
3. Replication for high availability

## Backup Strategy

### Logical Backups

```bash
# Create a backup
kubectl exec -n postgres postgresql-official-0 -- \
  pg_dump -U {{ admin_username }} -d mydatabase > backup.sql

# Restore from backup
cat backup.sql | kubectl exec -i -n postgres postgresql-official-0 -- \
  psql -U {{ admin_username }} -d mydatabase
```

### Volume Snapshots

If your storage class supports snapshots:

```bash
# Create a snapshot of the PostgreSQL PVC
kubectl create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-data-snapshot
  namespace: postgres
spec:
  volumeSnapshotClassName: csi-hostpath-snapclass
  source:
    persistentVolumeClaimName: postgres-data
EOF
```

## Resource Limits

The deployment includes the following resource limits:

- CPU: 250m request, 1000m limit
- Memory: 256Mi request, 1Gi limit
- Storage: 10Gi (configurable)

## Security Notes

- PostgreSQL admin credentials use the standard `admin_username` and `admin_password` variables
- TLS is configured with certificates from the platform's default certificate store
- Access is restricted to the specific PostgreSQL port (5432)
- Security context sets correct PostgreSQL UID (999)