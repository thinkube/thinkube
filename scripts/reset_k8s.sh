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
echo "  1. Remove k8s-snap with --purge"
echo "  2. Delete ~/.kube/config"
echo "  3. Remove all k8s-related directories"
echo "  4. Remove pip configuration (devpi)"
echo "  5. Remove Python virtual environment (~/.venv)"
echo "  6. Remove thinkube installer state (~/.thinkube-installer)"
echo "  7. Remove temporary thinkube files"
echo "  8. Clear Tauri installer localStorage (deployment state)"
echo ""
echo "Step 1a: Unmounting kubelet pod volumes..."
KUBELET_MOUNTS=$(mount | grep '/var/snap/k8s/common/var/lib/kubelet/pods' | awk '{print $3}' || true)
if [ -n "$KUBELET_MOUNTS" ]; then
  MOUNT_COUNT=$(echo "$KUBELET_MOUNTS" | wc -l)
  echo "Found $MOUNT_COUNT kubelet pod volume mounts to unmount"
  echo "$KUBELET_MOUNTS" | xargs -I {} sudo umount -l {} 2>/dev/null || true
  echo "Kubelet pod volumes unmounted"
else
  echo "No kubelet pod volumes to unmount"
fi

echo ""
echo "Step 1b: Unmounting CSI loop device mounts..."
CSI_MOUNTS=$(mount | grep '/var/snap/k8s/common/var/lib/kubelet/plugins/kubernetes.io/csi' | awk '{print $3}' || true)
if [ -n "$CSI_MOUNTS" ]; then
  CSI_COUNT=$(echo "$CSI_MOUNTS" | wc -l)
  echo "Found $CSI_COUNT CSI loop device mounts to unmount"
  echo "$CSI_MOUNTS" | xargs -I {} sudo umount -l {} 2>/dev/null || true
  echo "CSI mounts unmounted"
else
  echo "No CSI mounts to unmount"
fi

echo ""
echo "Step 1c: Unmounting any remaining k8s mounts..."
K8S_MOUNTS=$(mount | grep '/var/snap/k8s' | awk '{print $3}' || true)
if [ -n "$K8S_MOUNTS" ]; then
  REMAINING_COUNT=$(echo "$K8S_MOUNTS" | wc -l)
  echo "Found $REMAINING_COUNT remaining k8s mounts to unmount"
  echo "$K8S_MOUNTS" | xargs -I {} sudo umount -l {} 2>/dev/null || true
  echo "Remaining k8s mounts unmounted"
else
  echo "No remaining k8s mounts"
fi

echo ""
echo "Step 1d: Removing k8s-snap with --purge..."
# Use timeout to prevent hanging indefinitely
timeout 120 sudo snap remove k8s --purge || {
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 124 ]; then
    echo "⚠️  Snap removal timed out after 2 minutes"
    echo "This usually means snapd got stuck. Using manual cleanup..."

    # Stop snapd
    sudo systemctl stop snapd.service snapd.socket

    # Find and remove stuck changes
    STUCK_CHANGES=$(snap changes 2>/dev/null | grep -E "Undo.*Remove.*k8s" | awk '{print $1}' || true)
    if [ -n "$STUCK_CHANGES" ]; then
      echo "Removing stuck snap changes from state.json: $STUCK_CHANGES"
      for CHANGE_ID in $STUCK_CHANGES; do
        sudo jq "del(.changes.\"$CHANGE_ID\")" /var/lib/snapd/state.json > /tmp/state.json.new
        sudo mv /tmp/state.json.new /var/lib/snapd/state.json
      done
    fi

    # Unmount snap if still mounted
    if mount | grep -q "/snap/k8s"; then
      SNAP_MOUNT=$(mount | grep "/snap/k8s" | awk '{print $3}' | head -1)
      sudo umount "$SNAP_MOUNT" 2>/dev/null || true
    fi

    # Remove snap directories
    sudo rm -rf /var/snap/k8s
    sudo rm -rf /snap/k8s
    sudo rm -f /var/lib/snapd/snaps/k8s_*.snap

    # Remove k8s snap entry from state.json
    sudo jq 'del(.data.snaps.k8s)' /var/lib/snapd/state.json > /tmp/state.json.new
    sudo mv /tmp/state.json.new /var/lib/snapd/state.json

    # Restart snapd
    sudo systemctl start snapd.service snapd.socket
    sleep 2

    echo "✅ Manual cleanup complete"
  else
    echo "k8s-snap not installed or already removed"
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
sudo rm -rf /run/nvidia || true

echo ""
echo "Step 4: Removing pip configuration (devpi)..."
rm -f ~/.pip/pip.conf || true
rm -f ~/.config/pip/pip.conf || true
echo "Pip configuration removed"

echo ""
echo "Step 5: Removing Python virtual environment..."
rm -rf ~/.venv || true
echo "Python venv removed"

echo ""
echo "Step 6: Removing thinkube installer state..."
rm -rf ~/.thinkube-installer || true
echo "Thinkube installer state removed"

echo ""
echo "Step 7: Removing temporary thinkube files..."
rm -rf /tmp/think* || true

echo ""
echo "Step 8: Clearing Tauri installer localStorage (deployment state)..."
LOCALSTORAGE_DB="$HOME/.local/share/org.thinkube.installer/localstorage/tauri_localhost_0.localstorage"
if [ -f "$LOCALSTORAGE_DB" ]; then
  sqlite3 "$LOCALSTORAGE_DB" "DELETE FROM ItemTable WHERE key IN ('thinkube-deployment-state-v2', 'thinkubeInstaller', 'thinkube-session-backup');" 2>/dev/null || true
  echo "Cleared stale deployment state from localStorage"
else
  echo "No localStorage database found (installer not yet run)"
fi

echo ""
echo "=================================================="
echo "✅ K8s-snap removal complete!"
echo "=================================================="
echo ""
echo "System is ready for fresh k8s installation."
