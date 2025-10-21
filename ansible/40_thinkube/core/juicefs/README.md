# JuiceFS Distributed Filesystem

This component deploys JuiceFS distributed filesystem providing true ReadWriteMany (RWX) storage capabilities for the Kubernetes cluster. JuiceFS separates metadata and data storage, using PostgreSQL for metadata and SeaweedFS S3 for data storage.

## Features

- **True ReadWriteMany (RWX)** storage across multiple nodes
- **Metadata Engine**: PostgreSQL for filesystem metadata
- **Data Storage**: SeaweedFS S3 API for object storage
- **CSI Driver**: Kubernetes CSI driver for dynamic provisioning
- **POSIX Compatible**: Full POSIX filesystem semantics
- **Multi-node Consistency**: Files written on one node are immediately visible on all nodes
- **Production Ready**: Used in production AI/ML workloads
- **Apache 2.0 License**: Fully compatible with platform licensing

## Architecture

```
JuiceFS CSI Driver (Kubernetes)
├── Metadata → PostgreSQL (existing core component)
└── Data → SeaweedFS S3 API (existing core component)
```

## Why JuiceFS?

JuiceFS solves the multi-node RWX storage problem that SeaweedFS CSI driver cannot reliably provide:

- **SeaweedFS CSI Issue**: FUSE cache causes multi-node inconsistency
- **JuiceFS Solution**: Uses SeaweedFS via S3 API (no FUSE), with PostgreSQL metadata engine
- **Result**: True shared filesystem across all GPU nodes for JupyterHub, AI models, datasets, etc.

## Deployment

```bash
# Deploy JuiceFS
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/juicefs/10_deploy.yaml

# Test the deployment
./scripts/run_ansible.sh ansible/40_thinkube/core/juicefs/18_test.yaml

# Rollback if needed
./scripts/run_ansible.sh ansible/40_thinkube/core/juicefs/19_rollback.yaml
```

## Configuration

JuiceFS is configured via inventory variables:

- `juicefs_namespace`: Namespace for JuiceFS CSI driver (default: `juicefs`)
- `postgres_namespace`: PostgreSQL namespace (for metadata storage)
- `seaweedfs_namespace`: SeaweedFS namespace (for S3 object storage)
- `admin_username`: PostgreSQL admin username
- `admin_password`: PostgreSQL admin password (via ADMIN_PASSWORD env var)

## Using JuiceFS in Your Applications

### StorageClass

JuiceFS provides a `juicefs-rwx` StorageClass for RWX volumes:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-data
  namespace: my-app
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: juicefs-rwx
  resources:
    requests:
      storage: 10Gi
```

### Use Cases

1. **JupyterHub**: Shared notebooks and examples across GPU nodes
2. **AI/ML Models**: Centralized model storage accessible from any node
3. **Training Datasets**: Shared datasets for distributed training
4. **Collaborative Development**: Shared code workspaces
5. **CI/CD**: Shared build cache and artifacts

### Example: Multi-node Shared Volume

```yaml
---
# PVC with RWX access
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-models
  namespace: ai-workloads
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: juicefs-rwx
  resources:
    requests:
      storage: 50Gi
---
# Pod 1 on node A
apiVersion: v1
kind: Pod
metadata:
  name: trainer-gpu1
  namespace: ai-workloads
spec:
  nodeSelector:
    gpu: "rtx-3090"
  containers:
    - name: trainer
      image: pytorch/pytorch:latest
      volumeMounts:
        - name: models
          mountPath: /models
  volumes:
    - name: models
      persistentVolumeClaim:
        claimName: ml-models
---
# Pod 2 on node B (accessing same data)
apiVersion: v1
kind: Pod
metadata:
  name: trainer-gpu2
  namespace: ai-workloads
spec:
  nodeSelector:
    gpu: "gtx-1080ti"
  containers:
    - name: trainer
      image: pytorch/pytorch:latest
      volumeMounts:
        - name: models
          mountPath: /models
  volumes:
    - name: models
      persistentVolumeClaim:
        claimName: ml-models
```

## Data Storage

### Metadata

Metadata is stored in PostgreSQL database `juicefs` in the existing PostgreSQL instance:

```bash
# Connect to PostgreSQL
PGPASSWORD='{{ admin_password }}' psql -h postgres.{{ domain_name }} -U {{ admin_username }} -d juicefs
```

### Data

Data is stored in SeaweedFS S3 bucket `juicefs-data`:

```bash
# List bucket contents
s3cmd --access_key={{ s3_access_key }} --secret_key={{ s3_secret_key }} \
  --host=s3.{{ domain_name }} ls s3://juicefs-data/
```

## Performance Characteristics

- **Latency**: Metadata operations via PostgreSQL (low latency)
- **Throughput**: Data operations via SeaweedFS S3 (high throughput)
- **Consistency**: Strong consistency via PostgreSQL metadata
- **Scalability**: Horizontal scaling via SeaweedFS object storage

## Troubleshooting

### Check CSI Driver Status

```bash
# Check controller pod
kubectl get statefulset -n kube-system juicefs-csi-controller

# Check node pods (should be on each node)
kubectl get daemonset -n kube-system juicefs-csi-node

# View CSI driver logs
kubectl logs -n kube-system -l app.kubernetes.io/name=juicefs-csi-driver
```

### Check Volume Mount Status

```bash
# List mount pods for a volume
kubectl get pods -n kube-system -l app.kubernetes.io/name=juicefs-mount

# Check mount pod logs
kubectl logs -n kube-system <mount-pod-name>
```

### Common Issues

#### PVC stuck in Pending

**Cause**: JuiceFS secret missing or PostgreSQL/SeaweedFS not accessible

**Solution**:
```bash
# Check secret exists
kubectl get secret juicefs-secret -n juicefs

# Test PostgreSQL connection
kubectl exec -n postgres statefulset/postgresql-official -- \
  psql -U {{ admin_username }} -d juicefs -c "SELECT 1"

# Test SeaweedFS S3 API
kubectl get secret seaweedfs-s3-credentials -n seaweedfs
```

#### Mount fails with "connection refused"

**Cause**: PostgreSQL or SeaweedFS not accessible from mount pod

**Solution**:
```bash
# Check PostgreSQL service
kubectl get svc -n postgres postgresql-official

# Check SeaweedFS filer service
kubectl get svc -n seaweedfs seaweedfs-filer

# Verify DNS resolution from mount pod
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup postgresql-official.postgres.svc.cluster.local
```

## Backup and Recovery

### Metadata Backup

Metadata is stored in PostgreSQL and can be backed up using standard PostgreSQL tools:

```bash
# Backup JuiceFS metadata
kubectl exec -n postgres statefulset/postgresql-official -- \
  pg_dump -U {{ admin_username }} juicefs > juicefs-metadata-backup.sql

# Restore JuiceFS metadata
cat juicefs-metadata-backup.sql | kubectl exec -i -n postgres statefulset/postgresql-official -- \
  psql -U {{ admin_username }} juicefs
```

### Data Backup

Data is stored in SeaweedFS and can be backed up using S3 tools:

```bash
# Sync JuiceFS data to external backup
s3cmd sync s3://juicefs-data/ /backup/juicefs-data/
```

## Migration from SeaweedFS CSI

If you have existing volumes using SeaweedFS CSI driver with RWX issues:

1. **Stop applications** using the broken RWX volumes
2. **Copy data** from SeaweedFS CSI volumes to JuiceFS volumes:
   ```bash
   kubectl run -it --rm data-migration --image=busybox --restart=Never -- \
     sh -c "cp -r /old-volume/* /new-volume/"
   ```
3. **Update applications** to use new JuiceFS PVCs
4. **Verify** multi-node access works correctly
5. **Clean up** old SeaweedFS CSI volumes

## Security

- JuiceFS uses PostgreSQL for metadata (secured with admin credentials)
- SeaweedFS S3 API uses access keys (stored in Kubernetes secrets)
- All credentials stored in Kubernetes secrets (not in code)
- CSI driver runs with minimal permissions

## License

JuiceFS: Apache License 2.0
Compatible with Thinkube platform licensing requirements

## Dependencies

- **PostgreSQL**: Required for metadata storage
- **SeaweedFS**: Required for S3 object storage
- **Helm**: Required for CSI driver installation

## Additional Resources

- [JuiceFS Documentation](https://juicefs.com/docs/community/)
- [JuiceFS CSI Driver](https://github.com/juicedata/juicefs-csi-driver)
- [JuiceFS Architecture](https://juicefs.com/docs/community/architecture/)

---

🤖 This component was designed and implemented with AI assistance to solve the multi-node RWX storage challenge in Thinkube's GPU cluster.
