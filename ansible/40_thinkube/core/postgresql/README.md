# PostgreSQL Database

This component deploys a PostgreSQL database server in Kubernetes, providing a centralized data store for platform services including Keycloak, Harbor, MLflow, and other components.

## Installation

PostgreSQL is a core component. The Thinkube installer installs it by running
`00_install.yaml`, which runs `10_deploy.yaml` and `17_configure_discovery.yaml`
in that order. It is not installed on its own.

## Features

- Uses official PostgreSQL container image (`postgres:18-alpine`, pulled from `public.ecr.aws/docker/library`)
- Persistent storage via StatefulSet
- TLS secured connections
- External TCP access on port 5432 through a Gateway API TCPRoute (created in `infrastructure/gateway-api/10_deploy.yaml`)
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

External access is available via the gateway TCPRoute:

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

Data is stored in the StatefulSet's volume claim `data-postgresql-official-0` in the `postgres` namespace, mounted at `/var/lib/postgresql`. The storage class is `k8s-hostpath`. This ensures data survives pod restarts and redeployments.

`10_deploy.yaml` also creates a PVC named `postgres-data`, but the StatefulSet does not mount it.

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
    persistentVolumeClaimName: data-postgresql-official-0
EOF
```

## Resource Limits

The deployment includes the following resource limits:

- CPU: 250m request, 1000m limit
- Memory: 256Mi request, 1Gi limit
- Storage: 10Gi (`postgres_persistence_size` in `10_deploy.yaml`)

## Security Notes

- PostgreSQL admin credentials use the standard `admin_username` and `admin_password` variables
- TLS uses the wildcard certificate, copied from the default namespace into the `postgres-tls-secret` secret
- Access is restricted to the specific PostgreSQL port (5432)
- Security context sets correct PostgreSQL UID (999)