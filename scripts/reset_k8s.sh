#!/bin/bash
# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Script to completely remove k8s-snap and clean up Kubernetes configuration
# This prepares the system for a fresh k8s installation

set -e

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
echo "Step 1: Removing k8s-snap with --purge..."
sudo snap remove k8s --purge || echo "k8s-snap not installed or already removed"

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
