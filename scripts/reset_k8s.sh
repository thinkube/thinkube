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
echo "  4. Remove temporary thinkube files"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

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
sudo rm -rf /etc/cni || true
sudo rm -rf /opt/cni || true
sudo rm -rf /var/lib/cni || true

echo ""
echo "Step 4: Removing temporary thinkube files..."
rm -rf /tmp/think* || true

echo ""
echo "=================================================="
echo "✅ K8s-snap removal complete!"
echo "=================================================="
echo ""
echo "System is ready for fresh k8s installation."
