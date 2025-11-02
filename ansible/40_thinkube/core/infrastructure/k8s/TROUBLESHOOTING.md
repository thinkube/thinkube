# Troubleshooting: k8s-snap Installation Issues

This document covers common issues encountered during Canonical Kubernetes (k8s-snap) installation and removal.

## Table of Contents

1. [Playbook Execution Failures](#playbook-execution-failures)
2. [Snap Removal Issues](#snap-removal-issues)
3. [CSI Driver Pod Issues](#csi-driver-pod-issues)
4. [General Debugging Tips](#general-debugging-tips)

---

## Playbook Execution Failures

### Issue: `/home/alexmc/.local/bin/kubectl: not found`

**Symptom:**
```
TASK [Patch rawfile CSI node daemonset to use correct kubelet paths]
fatal: [tkspark]: FAILED! => {"rc": 127, "stderr": "/bin/sh: 1: /home/alexmc/.local/bin/kubectl: not found"}
```

**Root Cause:**
The playbook tried to use the `kubectl_bin` variable (which points to `~/.local/bin/kubectl`) before the kubectl wrapper script was created. The wrapper is created later in the playbook at line ~334.

**Solution:**
Tasks that run before the kubectl wrapper is created must use `k8s kubectl` directly, not `{{ kubectl_bin }}`. This was fixed in commit `4a8af1b`.

**Fixed in:** ansible/40_thinkube/core/infrastructure/k8s/10_install_k8s.yaml:293, 320

**Example of correct usage:**
```yaml
- name: Patch rawfile CSI node daemonset to use correct kubelet paths
  ansible.builtin.shell: |
    k8s kubectl patch daemonset ck-storage-rawfile-csi-node -n kube-system --type='json' -p='[...]'
  register: csi_patch_result
```

**Wrong (before fix):**
```yaml
- name: Patch rawfile CSI node daemonset to use correct kubelet paths
  ansible.builtin.shell: |
    {{ kubectl_bin }} patch daemonset ck-storage-rawfile-csi-node -n kube-system --type='json' -p='[...]'
  environment:
    KUBECONFIG: "{{ kubeconfig }}"  # Also unnecessary with k8s kubectl
```

---

## Snap Removal Issues

### Issue: Snap Removal Stuck in "Undo" State

**Symptom:**
```bash
$ sudo snap remove k8s --purge
# Hangs for 10+ minutes
# Shows: "INFO Waiting for snap.k8s.etcd.service to stop"
# Eventually times out or gets stuck

$ snap changes
10   Undo    today at 20:16 CET  -                   Remove "k8s" snap
```

**Root Cause:**
Kubelet pod volume mounts under `/var/snap/k8s/common/var/lib/kubelet/pods/` are still mounted when snapd tries to remove data. This causes:
1. `unlinkat` fails with "device or resource busy"
2. Snapd enters "Undo" state trying to roll back
3. Change remains stuck indefinitely

**Verification:**
```bash
# Check if snap removal is stuck
snap changes | tail -10

# Check for stuck change
snap change 10  # Replace 10 with actual change ID

# Look for errors like:
# ERROR unlinkat /var/snap/k8s/common/var/lib/kubelet/pods/.../volumes/kubernetes.io~projected/...: device or resource busy
```

**Solution: Clean Removal Without Reboot**

This procedure safely removes the stuck snap by editing snapd's internal state.

#### Step 1: Install jq (if not already installed)
```bash
sudo apt install -y jq
```

#### Step 2: Backup snapd state
```bash
sudo cp /var/lib/snapd/state.json /var/lib/snapd/state.json.bak-$(date +%Y%m%d-%H%M%S)
ls -lh /var/lib/snapd/state.json*
```

#### Step 3: Unmount any lingering kubelet pod volumes
```bash
# List any remaining mounts
mount | grep "/var/snap/k8s/common/var/lib/kubelet/pods"

# Force lazy unmount all of them
mount | grep "/var/snap/k8s/common/var/lib/kubelet/pods" | awk '{print $3}' | xargs -I {} sudo umount -l {}

# Verify all cleared
mount | grep "/var/snap/k8s" | wc -l  # Should be 0
```

#### Step 4: Stop snapd service
```bash
sudo systemctl stop snapd.service snapd.socket

# Verify stopped
systemctl is-active snapd.service snapd.socket  # Should show "inactive"
```

#### Step 5: Remove stuck change from state.json
```bash
# Get the change ID from 'snap changes' output
CHANGE_ID=10  # Replace with your actual change ID

# Remove the stuck change using jq
sudo jq "del(.changes.\"${CHANGE_ID}\")" /var/lib/snapd/state.json > /tmp/state.json.new
sudo mv /tmp/state.json.new /var/lib/snapd/state.json

echo "Change #${CHANGE_ID} removed successfully"
```

#### Step 6: Manually clean up k8s snap files
```bash
# Remove /var/snap/k8s directory
sudo rm -rf /var/snap/k8s

# Unmount /snap/k8s if still mounted
mount | grep "/snap/k8s"
sudo umount /snap/k8s/4234  # Replace 4234 with actual revision

# Remove /snap/k8s directory
sudo rm -rf /snap/k8s

# Remove snap file
sudo rm /var/lib/snapd/snaps/k8s_*.snap

# Verify all cleaned up
ls -la /var/snap/ | grep k8s  # Should be empty
ls -la /snap/ | grep k8s      # Should be empty
```

#### Step 7: Remove k8s snap entry from state.json
```bash
# Still with snapd stopped
sudo jq 'del(.data.snaps.k8s)' /var/lib/snapd/state.json > /tmp/state.json.new
sudo mv /tmp/state.json.new /var/lib/snapd/state.json

echo "k8s snap entry removed from state.json"
```

#### Step 8: Restart snapd and verify
```bash
sudo systemctl start snapd.service snapd.socket

# Wait a moment for snapd to initialize
sleep 3

# Verify k8s snap is gone
snap list | grep k8s  # Should return nothing

# Verify stuck change is gone
snap changes | tail -10  # Change should not appear
```

**Success Criteria:**
- `snap list` does not show k8s snap
- `snap changes` does not show stuck change
- `/var/snap/k8s` and `/snap/k8s` directories do not exist
- snapd service is active and healthy

**Important Notes:**
- **ALWAYS backup state.json before editing** - A corrupted state.json can break snapd entirely
- **Use jq for editing** - Manual text editing risks JSON syntax errors
- **Keep the backup** for at least one reboot cycle
- This issue is **NOT caused by playbook configuration** - It's a timing issue with snapd and kubelet pod cleanup

**References:**
- Launchpad Bug #1899614: Multiple problems with undo for 'snap remove'
- Kubernetes Issue #37546: device or resource busy on pod cleanup
- Snapcraft Forum: remove-snap change stuck

---

## CSI Driver Pod Issues

### Issue: CSI Driver Pods Stuck in ContainerCreating

**Symptom:**
```bash
$ kubectl get pods -n kube-system -l app.kubernetes.io/name=rawfile-csi
NAME                                      READY   STATUS              RESTARTS   AGE
ck-storage-rawfile-csi-node-xxxxx         3/4     ContainerCreating   0          5m

$ kubectl describe pod -n kube-system ck-storage-rawfile-csi-node-xxxxx
# Shows error: "hostPath type check failed: /var/lib/kubelet/plugins_registry is not a directory"
```

**Root Cause:**
k8s-snap's built-in rawfile CSI driver uses default `/var/lib/kubelet` paths, but Thinkube configures kubelet with custom root-dir `/var/snap/k8s/common/var/lib/kubelet` for Docker coexistence on DGX Spark machines.

**Solution:**
The playbook includes a patch (lines 288-329) to update the CSI driver daemonset with correct kubelet paths. This patch was added in commit `40bc18f`.

**Verification:**
```bash
# Check CSI driver pods are all running (4/4 containers)
kubectl get pods -n kube-system -l app.kubernetes.io/name=rawfile-csi

# Should show:
# ck-storage-rawfile-csi-controller-0   2/2     Running
# ck-storage-rawfile-csi-node-*         4/4     Running

# Test PVC provisioning
kubectl get pvc -n postgresql  # Should show Bound status, not Pending
```

**If patch fails to apply:**
1. Check that `k8s kubectl` is accessible (not `{{ kubectl_bin }}`)
2. Verify cluster is fully ready before patching
3. Check that the daemonset exists: `k8s kubectl get daemonset -n kube-system ck-storage-rawfile-csi-node`

---

## General Debugging Tips

### Check k8s Cluster Status
```bash
# Overall cluster health
k8s status

# Detailed cluster status with wait
k8s status --wait-ready

# Check node status
k8s kubectl get nodes

# Check all pods
k8s kubectl get pods -A
```

### Check Snap Service Logs
```bash
# View k8s snap logs (if services are running)
journalctl -u snap.k8s.kube-apiserver.service -f
journalctl -u snap.k8s.etcd.service -f
journalctl -u snap.k8s.kube-scheduler.service -f

# Check snap changes history
snap changes

# View specific change details
snap change 10  # Replace 10 with actual change ID
```

### Check Kubelet Pod Mounts
```bash
# List all kubelet pod mounts
mount | grep "/var/snap/k8s/common/var/lib/kubelet/pods"

# Check systemd mount units
systemctl list-units --all | grep "var-snap-k8s"

# Force unmount stuck volumes
mount | grep "/var/snap/k8s/common/var/lib/kubelet/pods" | awk '{print $3}' | xargs -I {} sudo umount -l {}
```

### Check Snapd State
```bash
# View snapd state.json (very large file - use jq)
sudo jq '.changes | keys' /var/lib/snapd/state.json  # List all change IDs

# View specific change
sudo jq '.changes."10"' /var/lib/snapd/state.json  # Replace 10 with change ID

# View installed snaps in state
sudo jq '.data.snaps | keys' /var/lib/snapd/state.json
```

### UFW Firewall Rules
```bash
# Check UFW status and rules
sudo ufw status verbose

# Verify k8s ports are allowed
# 6443/tcp  - k8s API server
# 6400/tcp  - k8s cluster daemon
# 10250/tcp - kubelet
# 4240/tcp  - Cilium health
# 8472/udp  - Cilium VXLAN
```

### Storage Class Verification
```bash
# Check storage classes
k8s kubectl get storageclass

# Should show:
# csi-rawfile-default (default)   rawfile.csi.openebs.io

# Test PVC creation
cat <<EOF | k8s kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: csi-rawfile-default
EOF

# Check PVC status
k8s kubectl get pvc test-pvc -n default

# Clean up
k8s kubectl delete pvc test-pvc -n default
```

---

## Known Issues

### Snapd Auto-Refresh During Deployment

**Issue:** Snap auto-refresh can interrupt cluster operations.

**Mitigation:** The playbook installs k8s snap with specific channel (`1.34-classic/stable`) to ensure version consistency.

**Workaround if needed:**
```bash
# Hold snap refresh during deployment
sudo snap refresh --hold=24h k8s

# Resume refresh after deployment
sudo snap refresh --unhold k8s
```

### Docker Coexistence Requirement

**Context:** NVIDIA DGX Spark machines come with Docker-based educational playbooks. Removing Docker breaks compatibility.

**Solution:** Thinkube configures k8s-snap with custom containerd base directory and kubelet root-dir to avoid conflicts:
```yaml
containerd-base-dir: /var/snap/k8s/common/var/lib/containerd
kubelet-root-dir: /var/snap/k8s/common/var/lib/kubelet
```

This configuration is applied during bootstrap (lines 171-180).

---

## Recovery Procedures

### Full Cluster Reset

If the cluster is unrecoverable, perform a clean reset:

```bash
# 1. Remove k8s snap (use troubleshooting steps if stuck)
sudo snap remove k8s --purge

# 2. Clean up any remaining mounts
mount | grep "/var/snap/k8s" | awk '{print $3}' | xargs -I {} sudo umount -l {}

# 3. Remove directories
sudo rm -rf /var/snap/k8s
sudo rm -rf /snap/k8s

# 4. Clear kubectl config
rm -rf ~/.kube/config

# 5. Verify UFW rules (should persist, but check)
sudo ufw status verbose

# 6. Re-run installer or playbook
cd ~/thinkube
./scripts/run_ansible.sh ansible/40_thinkube/core/infrastructure/k8s/10_install_k8s.yaml
```

### Backup Before Troubleshooting

Always backup critical files before manual intervention:

```bash
# Backup snapd state
sudo cp /var/lib/snapd/state.json /var/lib/snapd/state.json.bak-$(date +%Y%m%d-%H%M%S)

# Backup kubeconfig
cp ~/.kube/config ~/.kube/config.bak-$(date +%Y%m%d-%H%M%S)

# Backup inventory
cp ~/.thinkube-installer/inventory.yaml ~/.thinkube-installer/inventory.yaml.bak-$(date +%Y%m%d-%H%M%S)
```

---

## Getting Help

If you encounter an issue not covered here:

1. **Check playbook logs** - Ansible provides detailed error messages
2. **Check snapd logs** - `snap change <ID>` shows detailed task output
3. **Check Kubernetes logs** - `kubectl describe pod <name>` shows container issues
4. **Search GitHub issues** - kubernetes/kubernetes and canonical/k8s-snap
5. **Update this document** - Add your findings to help others

---

**Last Updated:** 2025-11-02
**Maintainer:** Thinkube Team
**Related Files:**
- `10_install_k8s.yaml` - Main installation playbook
- `~/thinkube/CURRENT_STATUS.md` - Deployment status documentation (in backup)
- `~/thinkube/CLAUDE.md` - Project documentation
