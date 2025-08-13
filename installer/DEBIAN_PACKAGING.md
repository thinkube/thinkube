# Debian Package Implementation for Thinkube Installer

## Overview
This document describes the implementation of Debian packaging for the Thinkube installer, supporting both AMD64 and ARM64 architectures.

## Architecture Decision: Embedded Repository

### Why Embedded?
- **Offline Installation**: No internet required after downloading the .deb
- **Version Consistency**: Installer and playbooks are always in sync  
- **Predictable Behavior**: No surprises from repository changes
- **Professional Experience**: Self-contained like commercial software

### Package Size
- Estimated: ~50MB per architecture
- Includes: GUI app, backend service, all Ansible playbooks
- Acceptable for modern systems and networks

## Package Structure

```
thinkube-installer_1.0.0_amd64.deb/
├── DEBIAN/
│   ├── control                           # Package metadata
│   ├── postinst                         # Post-installation script
│   ├── prerm                            # Pre-removal script
│   └── postrm                           # Post-removal script
├── usr/
│   ├── bin/
│   │   └── thinkube-installer           # Main executable (Tauri app)
│   ├── lib/
│   │   └── thinkube-installer/
│   │       └── backend                  # Python backend binary
│   └── share/
│       ├── thinkube-installer/
│       │   ├── ansible/                 # All playbooks (3.4MB)
│       │   ├── scripts/                 # Shell scripts
│       │   ├── inventory/               # Templates
│       │   └── ansible.cfg              # Configuration
│       ├── applications/
│       │   └── thinkube-installer.desktop
│       └── icons/
│           └── hicolor/
│               ├── 32x32/apps/thinkube-installer.png
│               ├── 128x128/apps/thinkube-installer.png
│               └── 256x256/apps/thinkube-installer.png
└── lib/
    └── systemd/
        └── system/
            └── thinkube-backend.service # Backend service unit
```

## Build Process

### Prerequisites
```bash
# Install build dependencies
sudo apt-get install -y \
    build-essential \
    cargo \
    rustc \
    nodejs \
    npm \
    python3-pip \
    python3-venv \
    dpkg-dev \
    crossbuild-essential-arm64  # For cross-compilation
```

### Multi-Architecture Build

#### Option 1: Native Build (Recommended)
Build on native hardware for each architecture:
- AMD64: Build on x86_64 machine
- ARM64: Build on ARM64 machine (Raspberry Pi 4/5)

#### Option 2: Cross-Compilation
Use Docker with QEMU for cross-platform builds:

```dockerfile
# Dockerfile.build-arm64
FROM rust:latest
RUN apt-get update && apt-get install -y \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    nodejs npm python3-pip
ENV CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
```

### Build Script Implementation

Create `installer/scripts/build-deb.sh`:

```bash
#!/bin/bash
set -e

ARCH=${1:-$(dpkg --print-architecture)}
VERSION=${2:-1.0.0}
BUILD_DIR="build/debian-$ARCH"

# 1. Prepare build directory
mkdir -p $BUILD_DIR/usr/share/thinkube-installer
cp -r ../ansible ../scripts ../inventory ../ansible.cfg \
    $BUILD_DIR/usr/share/thinkube-installer/

# 2. Build Python backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --name thinkube-backend main.py
cp dist/thinkube-backend ../$BUILD_DIR/usr/lib/thinkube-installer/
deactivate
cd ..

# 3. Build Tauri frontend
cd frontend
npm install
npm run build

# Set target for Rust
if [ "$ARCH" = "arm64" ]; then
    export CARGO_TARGET="aarch64-unknown-linux-gnu"
else
    export CARGO_TARGET="x86_64-unknown-linux-gnu"
fi

npm run tauri build -- --target $CARGO_TARGET --bundles deb
cd ..

# 4. Extract and enhance Tauri's .deb
dpkg-deb -x frontend/src-tauri/target/$CARGO_TARGET/release/bundle/deb/*.deb $BUILD_DIR
dpkg-deb -e frontend/src-tauri/target/$CARGO_TARGET/release/bundle/deb/*.deb $BUILD_DIR/DEBIAN

# 5. Add our components
# ... (add backend, playbooks, service file)

# 6. Build final package
dpkg-deb --build $BUILD_DIR thinkube-installer_${VERSION}_${ARCH}.deb
```

## Backend Modifications

Update `backend/app/services/ansible_executor.py`:

```python
import os
from pathlib import Path

def get_thinkube_root():
    """Get the thinkube root directory, checking multiple locations."""
    
    # 1. Environment variable (for development)
    if env_root := os.environ.get('THINKUBE_ROOT'):
        return Path(env_root)
    
    # 2. Packaged location (production)
    packaged = Path('/usr/share/thinkube-installer')
    if packaged.exists():
        return packaged
    
    # 3. User's home directory (fallback/development)
    home = Path.home() / "thinkube"
    if home.exists():
        return home
    
    # 4. Create directory if none exist
    # In production, use packaged location
    if Path('/usr/share/thinkube-installer').parent.exists():
        raise FileNotFoundError(
            "Thinkube installation not found. "
            "Please reinstall the package."
        )
    
    # In development, create in home
    home.mkdir(parents=True, exist_ok=True)
    return home
```

## Debian Control Files

### control
```
Package: thinkube-installer
Version: 1.0.0
Architecture: amd64
Maintainer: Alejandro Martínez Corriá <your-email@example.com>
Depends: python3 (>= 3.10), ansible (>= 2.9), git, curl, libwebkit2gtk-4.1-0, libgtk-3-0
Recommends: sshpass, python3-netaddr
Section: admin
Priority: optional
Homepage: https://github.com/thinkube/thinkube
Description: Professional installer for Thinkube Kubernetes platform
 Thinkube is a home-based development platform built on Kubernetes,
 designed specifically for AI applications and agents. This installer
 provides a graphical interface for setting up and configuring your
 Thinkube cluster.
```

### postinst
```bash
#!/bin/bash
set -e

# Create necessary directories
mkdir -p /var/lib/thinkube-installer
mkdir -p /var/log/thinkube-installer

# Enable and start backend service
systemctl daemon-reload
systemctl enable thinkube-backend.service
systemctl start thinkube-backend.service

# Set permissions
chmod +x /usr/bin/thinkube-installer
chmod +x /usr/lib/thinkube-installer/backend

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
fi

echo "Thinkube installer has been successfully installed."
echo "Run 'thinkube-installer' to start the installation wizard."
```

### prerm
```bash
#!/bin/bash
set -e

# Stop and disable the backend service
if systemctl is-active thinkube-backend.service >/dev/null 2>&1; then
    systemctl stop thinkube-backend.service
fi

if systemctl is-enabled thinkube-backend.service >/dev/null 2>&1; then
    systemctl disable thinkube-backend.service
fi
```

### systemd Service File

`thinkube-backend.service`:
```ini
[Unit]
Description=Thinkube Installer Backend Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/lib/thinkube-installer/backend
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment="THINKUBE_ROOT=/usr/share/thinkube-installer"

[Install]
WantedBy=multi-user.target
```

## Tauri Configuration

Update `frontend/src-tauri/tauri.conf.json`:

```json
{
  "bundle": {
    "active": true,
    "targets": ["deb"],
    "identifier": "org.thinkube.installer",
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/256x256.png"],
    "deb": {
      "depends": ["libwebkit2gtk-4.1-0", "libgtk-3-0"],
      "files": {
        "/usr/share/thinkube-installer/": "../../../ansible/",
        "/usr/lib/thinkube-installer/backend": "../../../backend/dist/backend"
      }
    }
  }
}
```

## GitHub Actions Workflow

`.github/workflows/build-release.yml`:

```yaml
name: Build Release Packages

on:
  push:
    tags:
      - 'v*'

jobs:
  build-amd64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
      - name: Build AMD64 package
        run: |
          cd installer
          ./scripts/build-deb.sh amd64 ${{ github.ref_name }}
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: debian-packages
          path: installer/*.deb

  build-arm64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v2
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Build ARM64 package
        run: |
          cd installer
          docker buildx build --platform linux/arm64 \
            -f Dockerfile.build-arm64 \
            --output type=local,dest=. .
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: debian-packages
          path: installer/*.deb

  release:
    needs: [build-amd64, build-arm64]
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v3
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: debian-packages/*.deb
          generate_release_notes: true
```

## Testing

### Local Testing
```bash
# Build the package
cd installer
./scripts/build-deb.sh

# Install locally
sudo dpkg -i thinkube-installer_1.0.0_amd64.deb
sudo apt-get install -f

# Test the installation
thinkube-installer --version
systemctl status thinkube-backend

# Uninstall
sudo apt remove thinkube-installer
```

### Cross-Architecture Testing
- Use QEMU to test ARM64 packages on AMD64
- Use real hardware when possible
- Test on Ubuntu 22.04 and 24.04

## Release Process

1. **Version Tagging**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

2. **GitHub Actions** automatically:
   - Builds both architectures
   - Creates GitHub release
   - Uploads .deb files

3. **User Installation**
   ```bash
   # Download appropriate architecture
   wget https://github.com/thinkube/thinkube/releases/download/v1.0.0/thinkube-installer_1.0.0_amd64.deb
   
   # Install
   sudo dpkg -i thinkube-installer_1.0.0_amd64.deb
   sudo apt-get install -f
   
   # Run
   thinkube-installer
   ```

## Future Enhancements

1. **APT Repository**
   - Host our own APT repository
   - Allow `apt-get install thinkube-installer`
   - Automatic updates

2. **Snap Package**
   - Better sandboxing
   - Automatic updates
   - Broader distribution

3. **AppImage**
   - Single file, no installation
   - Works on any Linux distribution
   - Good for testing

4. **Package Signing**
   - GPG sign packages
   - Establish trust chain
   - Prevent tampering

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   sudo apt-get install -f
   ```

2. **Service Won't Start**
   ```bash
   journalctl -u thinkube-backend -f
   ```

3. **Permission Errors**
   ```bash
   sudo chown -R $USER:$USER ~/.thinkube-installer
   ```

### Debug Mode
Set environment variable for verbose logging:
```bash
THINKUBE_DEBUG=1 thinkube-installer
```

---
*Last updated: January 2025*