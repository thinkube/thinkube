# Thinkube Backup Strategy

## Overview

This document outlines the backup strategy for the Thinkube platform, designed for a mobile ML workstation that may operate in airgapped environments.

**Key Insight:** Backup the *mounted filesystem content*, not the storage backend infrastructure (PostgreSQL + SeaweedFS). This preserves filenames, directory structure, and permissions - essential for actual restoration.

## Lessons Learned from December 2024 Incident

During cluster failure and recovery:
- ✅ **PostgreSQL metadata** was backed up → Database structure preserved
- ✅ **SeaweedFS volumes** were intact → Raw chunk data available
- ❌ **But:** Could only recover file *content*, not *names* or *paths*
- ❌ Notebooks became `notebook_12299.ipynb` instead of `transformer-training.ipynb`
- ❌ All directory structure was lost
- ❌ Had to grep for `"cells"` keyword to identify Jupyter notebooks

**Conclusion:** Backing up PostgreSQL + SeaweedFS gives you the data but loses the context. You need the mounted filesystem.

## Two-Tier Backup Strategy

### Tier 1: Critical Data (Daily) 💎

**What:** Application-level backup of irreplaceable data with full filesystem metadata

**Priority Items:**
1. Jupyter notebooks with original paths
2. Trained ML models
3. Unique datasets (skip publicly available ones)
4. Custom configurations

**Method:** Backup via mounted filesystem (PVC access through k8s pods)

```bash
#!/bin/bash
# backup-critical-data.sh

BACKUP_ROOT="/backup/thinkube-critical"
DATE=$(date +%Y%m%d-%H%M%S)

# 1. Backup Jupyter notebooks (HIGHEST PRIORITY)
kubectl exec -n jupyter deployment/jupyterhub -- \
    tar czf - /home/jovyan/ | \
    cat > "$BACKUP_ROOT/notebooks-$DATE.tar.gz"

# 2. Backup ML models
kubectl exec -n ml-workspace deployment/model-server -- \
    tar czf - /models/ | \
    cat > "$BACKUP_ROOT/models-$DATE.tar.gz"

# 3. Backup unique datasets
kubectl exec -n ml-workspace deployment/data-pod -- \
    tar czf - /data/unique/ | \
    cat > "$BACKUP_ROOT/datasets-$DATE.tar.gz"

# Keep last 14 days
find "$BACKUP_ROOT" -name "*.tar.gz" -mtime +14 -delete

echo "Critical data backed up to: $BACKUP_ROOT"
```

**Restore:** Simple tar extraction - all filenames and paths intact.

### Tier 2: Full JuiceFS Content (Weekly) 📦

**What:** Complete snapshot of the shared storage filesystem

**Method:** rsync or tar of the entire JuiceFS mount point

```bash
#!/bin/bash
# backup-juicefs-content.sh

BACKUP_ROOT="/backup/thinkube-full"
DATE=$(date +%Y%m%d)

# Find a pod with JuiceFS mounted
POD=$(kubectl get pods -A -o jsonpath='{.items[?(@.spec.volumes[*].persistentVolumeClaim)].metadata.name}' | head -1)
NAMESPACE=$(kubectl get pods -A -o jsonpath='{.items[?(@.spec.volumes[*].persistentVolumeClaim)].metadata.namespace}' | head -1)

# Backup entire JuiceFS content with rsync (incremental)
mkdir -p "$BACKUP_ROOT/current"
kubectl exec -n "$NAMESPACE" "$POD" -- \
    tar cf - /path/to/juicefs/mount | \
    tar xf - -C "$BACKUP_ROOT/current/"

# Or use rsync for incremental backups
# kubectl exec -n "$NAMESPACE" "$POD" -- tar cf - /data/ | \
#     tar xf - -C "$BACKUP_ROOT/incremental-$DATE/"

echo "Full backup completed: $BACKUP_ROOT"
```

**Restore:**
1. Rebuild cluster with ansible playbooks
2. Deploy JuiceFS CSI driver
3. Create PVC
4. Copy data back: `tar cf backup.tar.gz | kubectl exec -i pod -- tar xzf - -C /mount/`

### Tier 3: Infrastructure State (On-demand) 🔧

**What:** K8s cluster state for faster rebuild

**When:** Before major changes, monthly, or after significant configuration updates

```bash
#!/bin/bash
# backup-k8s-state.sh

BACKUP_ROOT="/backup/thinkube-infra"
DATE=$(date +%Y%m%d)

# 1. Export all k8s resources
kubectl get all,pvc,pv,sc,ingress,secret,configmap,ingressclass \
    --all-namespaces -o yaml | \
    gzip > "$BACKUP_ROOT/k8s-resources-$DATE.yaml.gz"

# 2. Export Helm releases
helm list --all-namespaces -o yaml | \
    gzip > "$BACKUP_ROOT/helm-releases-$DATE.yaml.gz"

# 3. Backup critical configs
cp -r ~/.kube/ "$BACKUP_ROOT/kube-config-$DATE/"
cp /etc/hosts "$BACKUP_ROOT/etc-hosts-$DATE"

# 4. Export ansible inventory
cp -r ~/shared-code/thinkube-platform/thinkube/inventory/ \
    "$BACKUP_ROOT/ansible-inventory-$DATE/"

echo "Infrastructure state backed up: $BACKUP_ROOT"
```

## Backup Locations

### Primary: Local External Drive (Airgap-Safe)
- **Path:** `/media/external-ssd/thinkube-backups/`
- **Why:** Always available, even airgapped
- **Capacity:** 1TB+ recommended
- **Schedule:** Daily automated backups

### Secondary: Cloud Storage (When Network Available)
- **Service:** Backblaze B2 / AWS S3 / Wasabi (cheapest options)
- **Why:** Offsite protection, accessible anywhere with internet
- **Sync:** Automated sync when network detected
- **Cost:** ~$6/TB/month

```bash
# Sync to cloud when network available (via systemd timer)
if ping -c 1 8.8.8.8 &>/dev/null; then
    rclone sync /backup/thinkube-critical/ b2:thinkube-backups/
fi
```

## Backup Schedule

| Backup Type | Frequency | Retention | Priority |
|-------------|-----------|-----------|----------|
| Jupyter notebooks | Daily 2 AM | 30 days | CRITICAL |
| ML models | Daily 3 AM | 14 days | HIGH |
| Full JuiceFS content | Weekly Sunday 4 AM | 4 weeks | MEDIUM |
| K8s infrastructure | Monthly / On-demand | 6 months | LOW |

## Automation

### Option 1: Systemd Timers (Host-Based)

```ini
# /etc/systemd/system/thinkube-backup-critical.timer
[Unit]
Description=Daily backup of critical Thinkube data

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/thinkube-backup-critical.service
[Unit]
Description=Backup critical Thinkube data
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup-critical-data.sh
User=alexmc
```

Enable:
```bash
sudo systemctl enable --now thinkube-backup-critical.timer
```

### Option 2: K8s CronJob (Cluster-Based)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-notebooks
  namespace: jupyter
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: alpine:latest
            command:
            - /bin/sh
            - -c
            - |
              tar czf /backup/notebooks-$(date +%Y%m%d).tar.gz /home/jovyan/
            volumeMounts:
            - name: jupyter-storage
              mountPath: /home/jovyan
            - name: backup-volume
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: jupyter-storage
            persistentVolumeClaim:
              claimName: jupyter-pvc
          - name: backup-volume
            hostPath:
              path: /backup/thinkube-critical
```

## Disaster Recovery Procedures

### Scenario 1: Lost notebooks only
**Recovery Time:** 5 minutes
1. Extract latest notebook backup: `tar xzf notebooks-YYYYMMDD.tar.gz`
2. Copy to new Jupyter pod: `kubectl cp`

### Scenario 2: Complete cluster failure
**Recovery Time:** 1-2 hours
1. Rebuild cluster: `ansible-playbook 40_thinkube/core/infrastructure/k8s/10_install_k8s.yaml`
2. Deploy storage: `ansible-playbook 40_thinkube/core/infrastructure/storage/`
3. Restore data: Extract full JuiceFS backup into mounted PVC
4. Deploy applications: Helm charts redeploy
5. Verify: Check notebooks and models are accessible

### Scenario 3: Catastrophic hardware failure
**Recovery Time:** Days (hardware replacement) + 2 hours (restore)
1. Replace hardware
2. Reinstall OS
3. Clone git repos: `git clone https://...`
4. Run ansible playbooks to rebuild cluster
5. Restore from cloud backup (if available) or external drive
6. Redeploy applications

## Testing Backup Integrity

**Monthly verification:**
```bash
#!/bin/bash
# test-backup-restore.sh

# 1. Extract a random notebook backup
BACKUP=$(ls /backup/thinkube-critical/notebooks-*.tar.gz | shuf -n 1)
tar tzf "$BACKUP" | head -20

# 2. Verify tar integrity
tar tzf "$BACKUP" > /dev/null && echo "✅ Backup integrity OK" || echo "❌ BACKUP CORRUPTED"

# 3. Test extraction
mkdir -p /tmp/backup-test
tar xzf "$BACKUP" -C /tmp/backup-test/
ls -lh /tmp/backup-test/
rm -rf /tmp/backup-test/

# 4. Check cloud sync status (if configured)
rclone check /backup/thinkube-critical/ b2:thinkube-backups/
```

## What NOT to Backup

- ❌ Container images (rebuilable from Dockerfiles/registries)
- ❌ Public datasets (re-downloadable)
- ❌ System logs (ephemeral)
- ❌ Cached data (regeneratable)
- ❌ PostgreSQL/SeaweedFS raw volumes (too complex to restore, backup mounted FS instead)

## Cost Analysis

### Option A: External SSD Only (Airgap-safe)
- Hardware: $100-200 (1-2TB SSD)
- Ongoing: $0/month
- Recovery: Always available

### Option B: External SSD + Cloud
- Hardware: $100-200 (1-2TB SSD)
- Cloud: ~$6/month (assuming 100GB critical data in cloud)
- Recovery: Available anywhere with internet

**Recommendation:** Start with Option A, add cloud sync later if needed.

## Future Enhancements

1. **Velero/k8up:** If backup complexity increases, consider k8s-native backup tools
2. **Incremental backups:** Use restic for deduplicated, incremental backups
3. **Automated testing:** Monthly restore tests in isolated environment
4. **Monitoring:** Alerting when backups fail or become stale
5. **Encryption:** GPG-encrypt backups before cloud sync

## Summary

**Philosophy:** Backup what you can actually restore. Filenames and paths matter as much as content.

**Priorities:**
1. 💎 Jupyter notebooks (daily, irreplaceable)
2. 📦 Full filesystem content (weekly, time-saving)
3. 🔧 Infrastructure state (monthly, convenience)

**Recovery Capability:**
- Critical data: 5 minutes
- Full cluster: 1-2 hours
- Total disaster: Days for hardware + 2 hours for restore

**Next Steps:**
1. Set up external backup drive
2. Deploy daily backup scripts
3. Test restore procedure once
4. Schedule monthly backup verification
