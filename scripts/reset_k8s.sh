#!/bin/bash
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Script to completely remove k8s-snap and clean up Kubernetes configuration
# This prepares the system for a fresh k8s installation

set -e

# Check for required dependencies and install if missing
if ! command -v jq &> /dev/null; then
  echo "jq not found, installing..."
  sudo apt update -qq
  sudo apt install -y jq
  echo "✅ jq installed"
fi

echo "=================================================="
echo "K8s-snap Reset Script"
echo "=================================================="
echo ""
echo "This script will:"
echo "  1. Unmount all kubelet pod volumes"
echo "  2. Unmount CSI loop device mounts"
echo "  3. Unmount remaining k8s mounts"
echo "  4. Stop k8s snap services"
echo "  5. Kill remaining k8s and containerd processes"
echo "  6. Detach loop devices"
echo "  7. Remove k8s-snap with --purge (with 2-minute timeout)"
echo "  8. Delete ~/.kube/config"
echo "  9. Remove all k8s-related directories"
echo " 10. Remove SeaweedFS and JuiceFS storage directories"
echo " 11. Remove pip configuration (devpi)"
echo " 12. Remove Python virtual environment (~/.venv)"
echo " 13. Remove thinkube installer state (~/.thinkube-installer)"
echo " 14. Remove temporary thinkube files"
echo " 15. Clear Tauri installer localStorage (deployment state)"
echo " 16. Ensure snapd is running and healthy"
echo " 17. Restart snapd to clear state"
echo ""
echo "Step 0: Deleting all PVCs and PVs to allow clean CSI teardown..."
KUBECTL="$HOME/.local/bin/kubectl"
KUBECONFIG="$HOME/.kube/config"
if [ -f "$KUBECTL" ] && [ -f "$KUBECONFIG" ]; then
  export KUBECONFIG

  # Remove finalizers and delete all PVs (including Retain-policy ones)
  PVS=$("$KUBECTL" get pv -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)
  if [ -n "$PVS" ]; then
    for PV in $PVS; do
      "$KUBECTL" patch pv "$PV" -p '{"metadata":{"finalizers":null}}' --ignore-not-found=true 2>/dev/null || true
    done
    echo "Finalizers removed from PVs"
  fi

  "$KUBECTL" delete pvc --all -A --wait=false --ignore-not-found=true 2>/dev/null || true
  "$KUBECTL" delete pv --all --wait=false --ignore-not-found=true 2>/dev/null || true
  echo "PVCs and PVs deleted"
  sleep 10
else
  echo "kubectl or kubeconfig not found, skipping PVC/PV deletion"
fi

echo ""
echo "Step 1a: Unmounting all k8s mounts (loop until clean)..."
for attempt in $(seq 1 10); do
  K8S_MOUNTS=$(mount | grep '/var/snap/k8s' | awk '{print $3}' || true)
  if [ -z "$K8S_MOUNTS" ]; then
    echo "All k8s mounts cleared"
    break
  fi
  COUNT=$(echo "$K8S_MOUNTS" | wc -l)
  echo "Attempt $attempt: found $COUNT k8s mounts, force-unmounting..."
  echo "$K8S_MOUNTS" | xargs -I {} sudo umount -f -l {} 2>/dev/null || true
  sleep 1
done
# Final check
if mount | grep -q '/var/snap/k8s'; then
  echo "WARNING: some k8s mounts could not be cleared:"
  mount | grep '/var/snap/k8s'
fi

echo ""
echo "Step 1d: Stopping k8s snap services..."
sudo snap stop k8s 2>/dev/null || true
sleep 2
echo "k8s snap services stopped"

echo ""
echo "Step 1e: Killing remaining k8s and containerd processes..."
# Kill containerd-shim processes
sudo pkill -9 -f containerd-shim 2>/dev/null || true
# Kill containerd processes
sudo pkill -9 -f '/containerd' 2>/dev/null || true
# Kill any k8s processes
sudo pkill -9 -f '/snap/k8s' 2>/dev/null || true
echo "Processes killed"

echo ""
echo "Step 1f: Detaching loop devices..."
LOOP_DEVICES=$(losetup -a | grep '/var/snap/k8s' | cut -d: -f1 || true)
if [ -n "$LOOP_DEVICES" ]; then
  LOOP_COUNT=$(echo "$LOOP_DEVICES" | wc -l)
  echo "Found $LOOP_COUNT loop devices to detach"
  echo "$LOOP_DEVICES" | xargs -I {} sudo losetup -d {} 2>/dev/null || true
  echo "Loop devices detached"
else
  echo "No loop devices found"
fi

echo ""
echo "Step 1g: Removing k8s-snap with --purge..."
# Use timeout to prevent hanging indefinitely
timeout 120 sudo snap remove k8s --purge || {
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 124 ]; then
    echo "⚠️  Snap removal timed out after 2 minutes"
    echo "This usually means snapd got stuck. Using manual cleanup..."

    # Stop snapd
    sudo systemctl stop snapd.service snapd.socket
    sleep 1

    # More aggressive process killing
    echo "Killing any remaining processes..."
    sudo pkill -9 -f containerd-shim 2>/dev/null || true
    sudo pkill -9 -f containerd 2>/dev/null || true
    sudo pkill -9 -f '/snap/k8s' 2>/dev/null || true
    sleep 1

    # More aggressive unmounting (force unmount everything)
    echo "Force unmounting all k8s-related mounts..."
    while mount | grep -q '/var/snap/k8s'; do
      mount | grep '/var/snap/k8s' | awk '{print $3}' | xargs -I {} sudo umount -f -l {} 2>/dev/null || true
      sleep 1
    done
    echo "All k8s mounts cleared"

    # Detach all loop devices again (with timeout to prevent hanging)
    echo "Detaching loop devices..."
    timeout 10 bash -c 'losetup -a 2>/dev/null | grep "/var/snap/k8s" | cut -d: -f1 | xargs -I {} sudo losetup -d {} 2>/dev/null' || true

    # Find and remove ALL k8s-related changes (not just stuck ones)
    echo "Removing all k8s-related changes from state.json..."
    ALL_K8S_CHANGES=$(sudo jq -r '.changes | to_entries[] | select(.value.summary | contains("k8s")) | .key' /var/lib/snapd/state.json 2>/dev/null || true)
    if [ -n "$ALL_K8S_CHANGES" ]; then
      CHANGE_COUNT=$(echo "$ALL_K8S_CHANGES" | wc -l)
      echo "Found $CHANGE_COUNT k8s-related changes to remove"
      for CHANGE_ID in $ALL_K8S_CHANGES; do
        sudo jq "del(.changes.\"$CHANGE_ID\")" /var/lib/snapd/state.json > /tmp/state.json.new
        sudo mv /tmp/state.json.new /var/lib/snapd/state.json
      done
      echo "All k8s changes removed"
    else
      echo "No k8s changes found in state.json"
    fi

    # Unmount snap if still mounted
    if mount | grep -q "/snap/k8s"; then
      echo "Unmounting /snap/k8s mounts..."
      mount | grep "/snap/k8s" | awk '{print $3}' | xargs -I {} sudo umount -f -l {} 2>/dev/null || true
    fi

    # Remove snap directories
    echo "Removing snap directories..."
    sudo rm -rf /var/snap/k8s
    sudo rm -rf /snap/k8s
    sudo rm -f /var/lib/snapd/snaps/k8s_*.snap

    # Remove k8s snap entry from state.json
    echo "Removing k8s snap from snapd state..."
    sudo jq 'del(.data.snaps.k8s)' /var/lib/snapd/state.json > /tmp/state.json.new
    sudo mv /tmp/state.json.new /var/lib/snapd/state.json

    # Restart snapd
    echo "Restarting snapd..."
    sudo systemctl start snapd.service snapd.socket
    sleep 2

    echo "✅ Manual cleanup complete"
  elif [ $EXIT_CODE -ne 0 ]; then
    echo "⚠️  snap remove failed (exit $EXIT_CODE), attempting manual cleanup..."

    # Stop snapd
    sudo systemctl stop snapd.service snapd.socket
    sleep 1

    # Force unmount any remaining k8s mounts
    for attempt in $(seq 1 10); do
      K8S_MOUNTS=$(mount | grep '/var/snap/k8s' | awk '{print $3}' || true)
      [ -z "$K8S_MOUNTS" ] && break
      echo "$K8S_MOUNTS" | xargs -I {} sudo umount -f -l {} 2>/dev/null || true
      sleep 1
    done

    # Detach all loop devices again
    timeout 10 bash -c 'losetup -a 2>/dev/null | grep "/var/snap/k8s" | cut -d: -f1 | xargs -I {} sudo losetup -d {} 2>/dev/null' || true

    # Remove all k8s-related changes from snapd state
    ALL_K8S_CHANGES=$(sudo jq -r '.changes | to_entries[] | select(.value.summary | contains("k8s")) | .key' /var/lib/snapd/state.json 2>/dev/null || true)
    if [ -n "$ALL_K8S_CHANGES" ]; then
      for CHANGE_ID in $ALL_K8S_CHANGES; do
        sudo jq "del(.changes.\"$CHANGE_ID\")" /var/lib/snapd/state.json > /tmp/state.json.new
        sudo mv /tmp/state.json.new /var/lib/snapd/state.json
      done
      echo "k8s changes removed from snapd state"
    fi

    # Unmount /snap/k8s if still mounted
    mount | grep "/snap/k8s" | awk '{print $3}' | xargs -I {} sudo umount -f -l {} 2>/dev/null || true

    # Remove snap directories and state
    sudo rm -rf /var/snap/k8s /snap/k8s
    sudo rm -f /var/lib/snapd/snaps/k8s_*.snap
    sudo jq 'del(.data.snaps.k8s)' /var/lib/snapd/state.json > /tmp/state.json.new
    sudo mv /tmp/state.json.new /var/lib/snapd/state.json

    # Restart snapd
    sudo systemctl start snapd.service snapd.socket
    sleep 2
    echo "✅ Manual cleanup complete"
  else
    echo "k8s-snap not installed, skipping"
  fi
}

echo ""
echo "Step 2: Deleting ~/.kube/config..."
rm -f ~/.kube/config || true

echo ""
echo "Step 3: Removing k8s-related directories..."
sudo rm -rf /var/snap/k8s || true
sudo rm -rf /root/snap/k8s || true
sudo rm -rf /etc/kubernetes || true
sudo rm -rf /var/lib/kubelet || true
sudo rm -rf /var/lib/k8s-dqlite || true
sudo rm -rf /var/lib/k8s-containerd || true
sudo rm -rf /etc/cni || true
sudo rm -rf /opt/cni || true
sudo rm -rf /var/lib/cni || true
sudo rm -rf /etc/containerd/conf.d || true
sudo rm -rf /usr/local/nvidia || true
# NOTE: do NOT delete /run/nvidia — it contains NVIDIA driver runtime state
# (e.g. /run/nvidia/validations/host-driver-ready) needed by GPU operator.
# /run/ is a tmpfs cleared on reboot; no need to manually clean it.

echo ""
echo "Step 4: Removing SeaweedFS and JuiceFS storage directories..."
sudo rm -rf /storage/logs/seaweedfs || true
sudo rm -rf /storage/filer_store || true
sudo rm -rf /storage/volume_store || true
sudo rm -rf /storage/master_store || true

# JuiceFS uses FUSE mounts — must unmount before removing
for attempt in $(seq 1 10); do
  JUICEFS_MOUNTS=$(mount | grep '/var/lib/juicefs' | awk '{print $3}' || true)
  [ -z "$JUICEFS_MOUNTS" ] && break
  COUNT=$(echo "$JUICEFS_MOUNTS" | wc -l)
  echo "Attempt $attempt: found $COUNT JuiceFS mounts, unmounting..."
  echo "$JUICEFS_MOUNTS" | xargs -I {} sudo umount -f -l {} 2>/dev/null || true
  sleep 1
done
sudo rm -rf /var/lib/juicefs || true
echo "SeaweedFS and JuiceFS storage removed"

echo ""
echo "Step 5: Removing pip configuration (devpi)..."
rm -f ~/.pip/pip.conf || true
rm -f ~/.config/pip/pip.conf || true
echo "Pip configuration removed"

echo ""
echo "Step 6: Removing Python virtual environment..."
sudo rm -rf $HOME/.venv || true
echo "Python venv removed"

echo ""
echo "Step 7: Removing thinkube installer state..."
rm -rf ~/.thinkube-installer || true
echo "Thinkube installer state removed"

echo ""
echo "Step 8: Removing temporary thinkube files..."
rm -rf /tmp/think* || true

echo ""
echo "Step 9: Clearing Tauri installer localStorage (deployment state)..."
LOCALSTORAGE_DB="$HOME/.local/share/org.thinkube.installer/localstorage/tauri_localhost_0.localstorage"
if [ -f "$LOCALSTORAGE_DB" ]; then
  sqlite3 "$LOCALSTORAGE_DB" "DELETE FROM ItemTable WHERE key IN ('thinkube-deployment-state-v2', 'thinkubeInstaller', 'thinkube-session-backup');" 2>/dev/null || true
  echo "Cleared stale deployment state from localStorage"
else
  echo "No localStorage database found (installer not yet run)"
fi

echo ""
echo "Step 9b: Recreating NVIDIA host driver validation marker..."
# The reset script does NOT delete /run/nvidia, but restart the service
# to ensure the marker exists in case it was lost for any other reason.
if systemctl is-enabled --quiet nvidia-host-driver-validation.service 2>/dev/null; then
  sudo systemctl restart nvidia-host-driver-validation.service
  if [ -f /run/nvidia/validations/host-driver-ready ]; then
    echo "✅ NVIDIA validation marker recreated"
  else
    echo "⚠️  NVIDIA validation marker missing — GPU operator may fail"
  fi
else
  echo "nvidia-host-driver-validation.service not found, skipping"
fi

echo ""
echo "Step 10: Ensuring snapd is running..."
# Ensure snapd is running after all cleanup
if ! systemctl is-active --quiet snapd.service; then
  echo "Snapd is not running, starting it..."
  sudo systemctl start snapd.service snapd.socket
  sleep 3
  echo "Snapd started"
else
  echo "Snapd is already running"
fi

# Verify snapd is responding
if snap list &>/dev/null; then
  echo "✅ Snapd is healthy and responding"
else
  echo "⚠️  Snapd is running but not responding yet, waiting..."
  sleep 5
  if snap list &>/dev/null; then
    echo "✅ Snapd is now responding"
  else
    echo "❌ Warning: Snapd may need manual attention"
  fi
fi

echo ""
echo "Step 11: Restarting snapd to clear state..."
# Restart snapd to ensure any corrupted state from failed operations is cleared
# This prevents "expected snap to be mounted but is not" errors on next install
sudo systemctl restart snapd.service snapd.socket
sleep 3
echo "Snapd restarted"

# Verify snapd is responding after restart
if snap list &>/dev/null; then
  echo "✅ Snapd is healthy after restart"
else
  echo "⚠️  Waiting for snapd to become ready..."
  sleep 5
  if snap list &>/dev/null; then
    echo "✅ Snapd is now ready"
  else
    echo "❌ Warning: Snapd may need manual attention"
  fi
fi

echo ""
echo "=================================================="
echo "✅ K8s-snap removal complete!"
echo "=================================================="
echo ""
echo "System is ready for fresh k8s installation."
