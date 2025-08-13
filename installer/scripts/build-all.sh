#!/bin/bash

# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

# Build script for thinkube installer
# Builds both amd64 and arm64 packages

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🏗️  Building thinkube installer..."

# Check dependencies
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed."; exit 1; }

# Build frontend
echo "📦 Building Vue frontend..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build

# Package backend
echo "🐍 Packaging FastAPI backend..."
cd "$PROJECT_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --name thinkube-backend main.py
deactivate

# Build Electron packages
echo "🎯 Building Electron packages..."
cd "$PROJECT_DIR/electron"
npm install

# Build for amd64
echo "🏗️  Building amd64 package..."
npm run build:linux-x64

# Build for arm64
echo "🏗️  Building arm64 package..."
npm run build:linux-arm64

# Check outputs
echo "✅ Build complete!"
echo "📦 Packages created:"
ls -la "$PROJECT_DIR/dist/"*.deb

# Create checksums
cd "$PROJECT_DIR/dist"
sha256sum *.deb > SHA256SUMS

echo "🎉 All builds completed successfully!"