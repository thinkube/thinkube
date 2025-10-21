# SeaweedFS Deployment

SeaweedFS is a distributed file storage system with S3-compatible API, deployed as a MinIO alternative.

## Overview

SeaweedFS provides:
- S3-compatible API for artifact storage
- Distributed file storage with replication
- Web UI with file browser
- WebDAV support
- POSIX-compatible FUSE mount

## Components

1. **Master Server**: Manages cluster topology and metadata
2. **Volume Server**: Stores actual file data
3. **Filer**: Provides S3 API, WebDAV, and web UI
4. **OAuth2 Proxy**: Keycloak integration for web UI authentication

## Implementation Details

### Secure S3 Authentication

The deployment implements a secure approach to S3 authentication that addresses the security concern of credentials being stored in plaintext in SeaweedFS's persistent storage:

1. **Helm Chart Limitation**: The SeaweedFS Helm chart v4.0.0 doesn't support passing the `-s3.config` parameter
2. **Post-Deployment Patching**: After Helm deployment, the playbook patches the StatefulSet to:
   - Add the `-s3.config=/etc/seaweedfs/s3-config.json` parameter to the filer command
   - Mount the S3 configuration from a Kubernetes secret as a volume
   - Check for existing volumes/mounts to avoid duplicates during re-runs
3. **Fallback Mechanism**: The configuration playbook checks if the config file is mounted and only uses `s3.configure` command as a fallback

This implementation ensures that S3 credentials are managed by Kubernetes RBAC and not stored in the filer's persistent volume.

## Deployment

### 1. Deploy SeaweedFS
```bash
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/seaweedfs/10_deploy.yaml
```

This creates:
- SeaweedFS namespace
- Master, Volume, and Filer servers
- OAuth2 proxy for UI authentication
- Ingresses for UI and S3 API

### 2. Configure S3 Access
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/seaweedfs/15_configure.yaml
```

This:
- Sets up S3 credentials
- Creates initial buckets (argo-artifacts, harbor-storage, etc.)
- Configures Argo Workflows to use SeaweedFS

### 3. Test Deployment
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/seaweedfs/18_test.yaml
```

### 4. Rollback (if needed)
```bash
./scripts/run_ansible.sh ansible/40_thinkube/core/seaweedfs/19_rollback.yaml
```

## Access Points

- **Web UI**: https://seaweedfs.{{ domain_name }} (Keycloak protected)
- **S3 API**: https://s3.{{ domain_name }} (API key required)
- **WebDAV**: https://webdav.{{ domain_name }} (if enabled)

## S3 Configuration

### Security Implementation

SeaweedFS S3 credentials are securely managed through Kubernetes secrets:

1. **Credentials Storage**: S3 access credentials are stored in the `seaweedfs-s3-config` secret
2. **Config File Mount**: The S3 configuration is mounted as `/etc/seaweedfs/s3-config.json` in the filer pod
3. **No Persistent Storage**: Unlike the default `s3.configure` command approach, credentials are NOT stored in `/etc/iam/identity.json` in the persistent volume
4. **Post-Deployment Patching**: The deployment playbook patches the SeaweedFS StatefulSet after Helm deployment to add the `-s3.config` parameter

This approach ensures credentials remain in Kubernetes secrets and are not exposed in persistent storage.

### For Applications

Use the internal endpoint for better performance:
```yaml
endpoint: http://seaweedfs-filer.seaweedfs.svc.cluster.local:8333
access_key: <from seaweedfs-s3-config secret>
secret_key: <from seaweedfs-s3-config secret>
```

### For External Access

```bash
# Get credentials from Kubernetes secret
kubectl get secret -n seaweedfs seaweedfs-s3-config -o jsonpath='{.data.access_key}' | base64 -d
kubectl get secret -n seaweedfs seaweedfs-s3-config -o jsonpath='{.data.secret_key}' | base64 -d

# Configure s3cmd
cat > ~/.s3cfg << EOF
[default]
access_key = <access_key>
secret_key = <secret_key>
host_base = s3.{{ domain_name }}
host_bucket = s3.{{ domain_name }}/%(bucket)s
use_https = True
check_ssl_certificate = False
signature_v2 = True
use_path_style = True
EOF

# List buckets
s3cmd ls

# Upload file
s3cmd put file.txt s3://bucket-name/
```

## Integration Examples

### Argo Workflows
The configuration playbook automatically sets up Argo to use SeaweedFS for artifacts. The `13_setup_artifacts.yaml` playbook in the Argo Workflows component:
- Retrieves S3 credentials from the SeaweedFS secret
- Creates the `argo-artifacts` bucket
- Configures the artifact repository with path-style URLs
- Updates the Argo ConfigMap with SeaweedFS endpoints

### Harbor Registry
```yaml
storage:
  s3:
    accesskey: <access_key>
    secretkey: <secret_key>
    region: us-east-1
    endpoint: http://seaweedfs-filer.seaweedfs.svc.cluster.local:8333
    bucket: harbor-storage
    secure: false
    v4auth: true
```

### Backup Scripts
```bash
#!/bin/bash
# Backup to SeaweedFS
s3cmd sync /data/ s3://backup/$(date +%Y%m%d)/
```

## Monitoring

Check component health:
```bash
# Master status
curl http://seaweedfs-master.seaweedfs.svc.cluster.local:9333/cluster/status

# Volume status  
curl http://seaweedfs-volume.seaweedfs.svc.cluster.local:8080/status

# Filer metrics
curl http://seaweedfs-filer.seaweedfs.svc.cluster.local:8888/metrics
```

## Scaling

To add more volume servers:
1. Edit `volume_replicas` in the deployment playbook
2. Re-run the deployment
3. SeaweedFS automatically rebalances data

## Troubleshooting

### Check logs
```bash
# Master logs
kubectl logs -n seaweedfs sts/seaweedfs-master

# Volume logs
kubectl logs -n seaweedfs sts/seaweedfs-volume

# Filer logs (Note: filer is also a StatefulSet after patching)
kubectl logs -n seaweedfs sts/seaweedfs-filer
```

### Verify S3 Config Mount
```bash
# Check if config file is mounted
kubectl exec -n seaweedfs seaweedfs-filer-0 -- ls -la /etc/seaweedfs/s3-config.json

# Verify S3 config parameter in running process
kubectl exec -n seaweedfs seaweedfs-filer-0 -- ps aux | grep s3.config

# Check that NO identity.json exists in persistent storage
kubectl exec -n seaweedfs seaweedfs-filer-0 -- ls -la /etc/iam/
# Should return: No such file or directory
```

### S3 API issues
- Ensure bucket exists
- Check credentials in secret: `kubectl get secret -n seaweedfs seaweedfs-s3-config -o yaml`
- Verify endpoint URL (internal vs external)
- Use `signature_v2 = True` and `use_path_style = True` for s3cmd
- For signature errors, ensure the secret key matches what's in the mounted config

### Storage issues
- Check PVC status: `kubectl get pvc -n seaweedfs`
- Verify volume server has space
- Check replication settings

### Patching Issues
If the StatefulSet patching fails:
1. Check for duplicate volumes/mounts
2. Verify the original command format
3. Check rollout status: `kubectl rollout status sts/seaweedfs-filer -n seaweedfs`

## License

SeaweedFS is Apache 2.0 licensed, making it suitable for commercial use without concerns about AGPL requirements.